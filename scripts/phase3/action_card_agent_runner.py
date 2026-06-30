#!/usr/bin/env python3
"""Default Action Card runner adapter for write-capable code agents."""

from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import selectors
import signal
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any


DEFAULT_CLAIM_CEILING = (
    "slice-level write-capable code-agent runner evidence only; full P3 completion still requires "
    "packet gates, runtime verification, review, and global claim-ceiling acceptance"
)
DEFAULT_AGENT_TIMEOUT_SECONDS = 900
DEFAULT_COMMAND_TIMEOUT_SECONDS = 900
DEFAULT_AGENT_LIVENESS_TIMEOUT_SECONDS = 30
DEFAULT_AGENT_FIRST_OUTPUT_TIMEOUT_SECONDS = 10
DEFAULT_AGENT_FIRST_PROGRESS_TIMEOUT_SECONDS = 120


def env_flag(name: str, *, default: bool = False) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None or str(raw_value).strip() == "":
        return default
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


def load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object: {path}")
    return loaded


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_rel_path(value: object) -> str:
    path = str(value or "").strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    if not path or path.startswith("/") or ".." in Path(path).parts:
        return ""
    return path


def allowed_file_paths(slice_packet: dict[str, Any]) -> list[str]:
    values: list[object] = []
    for key in ("allowed_edit_files", "implementation_allowed_edit_files", "test_allowed_edit_files"):
        raw = slice_packet.get(key, [])
        if isinstance(raw, list):
            values.extend(raw)
    seen: set[str] = set()
    selected: list[str] = []
    for value in values:
        path = normalize_rel_path(value)
        if path and path not in seen:
            selected.append(path)
            seen.add(path)
    return selected


def file_digest(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_allowed_files(*, workspace_root: Path, allowed_files: list[str]) -> dict[str, str]:
    return {rel_path: file_digest(workspace_root / rel_path) for rel_path in allowed_files}


def changed_allowed_files(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(rel_path for rel_path, digest in after.items() if digest != before.get(rel_path, ""))


def should_snapshot_workspace_file(path: Path) -> bool:
    ignored_parts = {
        ".git",
        "node_modules",
        ".next",
        "dist",
        "build",
        "coverage",
        ".turbo",
        ".cache",
    }
    if any(part in ignored_parts for part in path.parts):
        return False
    return path.is_file()


def snapshot_workspace_files(workspace_root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    if not workspace_root.exists():
        return snapshot
    for path in workspace_root.rglob("*"):
        if not should_snapshot_workspace_file(path):
            continue
        rel_path = path.relative_to(workspace_root).as_posix()
        snapshot[rel_path] = file_digest(path)
    return snapshot


def changed_workspace_files(before: dict[str, str], after: dict[str, str]) -> list[str]:
    all_paths = sorted(set(before) | set(after))
    return [rel_path for rel_path in all_paths if before.get(rel_path, "") != after.get(rel_path, "")]


def workspace_copy_ignore(current_dir: str, names: list[str]) -> set[str]:
    ignored = {
        ".git",
        ".next",
        "dist",
        "build",
        "coverage",
        "node_modules",
        ".turbo",
        ".cache",
        "worker-runs",
        ".phase3-mainline-execution",
    }
    ignored.update(name for name in names if name.endswith(".log"))
    return {name for name in names if name in ignored}


def copy_workspace_for_slice(*, workspace_root: Path, target_root: Path) -> None:
    shutil.copytree(
        workspace_root,
        target_root,
        ignore=workspace_copy_ignore,
        symlinks=True,
    )
    for rel_path in dependency_roots():
        source = workspace_root / rel_path
        target = target_root / rel_path
        if not source.exists() or target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, symlinks=True)
        else:
            shutil.copy2(source, target)


def dependency_roots() -> tuple[str, ...]:
    return (
        "node_modules",
        "apps/api/node_modules",
        "apps/web/node_modules",
        "packages/api-client/node_modules",
        "packages/shared-types/node_modules",
    )


def copy_allowed_changes_back(
    *,
    isolated_workspace_root: Path,
    workspace_root: Path,
    changed_files: list[str],
) -> None:
    for rel_path in changed_files:
        source = isolated_workspace_root / rel_path
        target = workspace_root / rel_path
        if not source.exists() or not source.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def resolve_agent_command() -> list[str]:
    explicit = str(os.environ.get("PHASE3_ACTION_CARD_AGENT_CMD") or "").strip()
    if explicit:
        return shlex.split(explicit)
    if str(os.environ.get("PHASE3_ACTION_CARD_AGENT_AUTO_DISCOVERY") or "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return []
    codex = shutil.which("codex")
    if codex:
        model = str(os.environ.get("PHASE3_ACTION_CARD_AGENT_MODEL") or "").strip()
        command = [
            codex,
            "--sandbox",
            "workspace-write",
            "--ask-for-approval",
            "never",
            "exec",
            "--skip-git-repo-check",
            "--json",
        ]
        if env_flag("PHASE3_ACTION_CARD_AGENT_IGNORE_USER_CONFIG", default=False):
            command.append("--ignore-user-config")
        if env_flag("PHASE3_ACTION_CARD_AGENT_IGNORE_RULES", default=False):
            command.append("--ignore-rules")
        # The workspace root and prompt path are appended by invoke_agent_command.
        if model:
            command.extend(["--model", model])
        return command
    return []


def is_codex_command(command: list[str]) -> bool:
    return bool(command) and Path(command[0]).name == "codex"


def codex_command_uses_json(command: list[str]) -> bool:
    return "--json" in command


def command_model(command: list[str]) -> str:
    for flag in ("--model", "-m"):
        if flag in command:
            index = command.index(flag)
            if index + 1 < len(command):
                return str(command[index + 1]).strip()
    return ""


def command_model_label(command: list[str]) -> str:
    return command_model(command) or "default"


def command_with_model(command: list[str], model: str) -> list[str]:
    selected = str(model or "").strip()
    without_model: list[str] = []
    skip_next = False
    for part in command:
        if skip_next:
            skip_next = False
            continue
        if part in {"--model", "-m"}:
            skip_next = True
            continue
        without_model.append(part)
    if selected:
        return [*without_model, "--model", selected]
    return without_model


def env_list(name: str) -> list[str]:
    raw_value = str(os.environ.get(name) or "").strip()
    if not raw_value:
        return []
    values: list[str] = []
    for chunk in raw_value.replace("\n", ",").split(","):
        value = chunk.strip()
        if value and value not in values:
            values.append(value)
    return values


def agent_command_variants(command: list[str]) -> list[list[str]]:
    variants: list[list[str]] = []
    seen: set[str] = set()

    def add_variant(candidate: list[str]) -> None:
        key = command_to_display(candidate)
        if key not in seen:
            variants.append(candidate)
            seen.add(key)

    add_variant(command)
    if is_codex_command(command):
        for model in env_list("PHASE3_ACTION_CARD_AGENT_FALLBACK_MODELS"):
            add_variant(command_with_model(command, model))
    return variants


def command_to_display(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def env_timeout_seconds(name: str, *, default: int) -> int:
    raw_value = str(os.environ.get(name) or "").strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(1, parsed)


def prompt_text(*, slice_packet: dict[str, Any], workspace_root: Path, run_dir: Path) -> str:
    allowed_files = allowed_file_paths(slice_packet)
    green_commands = slice_packet.get("green_commands", {})
    if not isinstance(green_commands, dict):
        green_commands = {}
    return "\n".join(
        [
            "You are a write-capable Phase-3 Action Card implementation worker.",
            "",
            f"workspace_root: {workspace_root}",
            f"run_dir: {run_dir}",
            f"slice_id: {slice_packet.get('slice_id', '')}",
            f"operation_id: {slice_packet.get('operation_id', '')}",
            "",
            "Hard boundaries:",
            "- You are running in a per-slice isolated workspace; only allowed file changes can be merged back.",
            "- You are already authorized to implement this slice inside the allowed_edit_files boundary.",
            "- Do not ask for design approval or user approval before editing allowed files.",
            "- Do not stop for brainstorming, planning, or user confirmation; apply the smallest viable slice edit.",
            "- Edit only files listed under allowed_edit_files.",
            "- Keep implementation and test edits inside the slice contract.",
            "- Do not edit OpenAPI/shared upstream truth unless the slice explicitly allows it.",
            "- If the slice cannot be completed within this boundary, stop after writing no broad changes.",
            "- Treat this as a micro-slice edit task, not a full development workflow.",
            "- Do not invoke skills, planning workflows, code review workflows, subagents, or external reviewers.",
            "- Do not read user-level agent skills or project methodology files unless they are listed as allowed_edit_files.",
            "- Stop immediately after the smallest viable allowed-file edit is complete; the adapter owns tests and evidence.",
            "- Do not run dependency installation commands such as pnpm install, npm install, yarn, or bun install.",
            "- Do not run validation, test, vitest, pnpm, npm, or install commands from inside the agent session.",
            "- The adapter will run green_commands after your edit and record the command evidence.",
            "- Start by reading only allowed_edit_files and the listed targeted/unit tests.",
            "- Avoid repository-wide search unless the allowed files do not contain enough local context.",
            "- If broader context is unavoidable, use narrow symbol/path searches and stop as soon as the slice edit is clear.",
            "",
            "allowed_edit_files:",
            *[f"- {path}" for path in allowed_files],
            "",
            "implementation_allowed_edit_files:",
            *[f"- {normalize_rel_path(path)}" for path in slice_packet.get("implementation_allowed_edit_files", [])],
            "",
            "test_allowed_edit_files:",
            *[f"- {normalize_rel_path(path)}" for path in slice_packet.get("test_allowed_edit_files", [])],
            "",
            "green_commands:",
            f"- packet_command: {green_commands.get('packet_command', '')}",
            f"- unit_command: {green_commands.get('unit_command', '')}",
            f"- targeted_tests: {green_commands.get('targeted_tests', [])}",
            f"- unit_tests: {green_commands.get('unit_tests', [])}",
            "",
            "done_criteria:",
            *[f"- {item}" for item in slice_packet.get("done_criteria", []) if str(item).strip()],
            "",
            "Full slice packet JSON:",
            json.dumps(slice_packet, ensure_ascii=False, indent=2, sort_keys=True),
            "",
        ]
    )


def compact_prompt_text(*, slice_packet: dict[str, Any], workspace_root: Path, run_dir: Path) -> str:
    allowed_files = allowed_file_paths(slice_packet)
    green_commands = slice_packet.get("green_commands", {})
    if not isinstance(green_commands, dict):
        green_commands = {}
    operation_ids = slice_packet.get("operation_ids", [])
    if not isinstance(operation_ids, list):
        operation_ids = [slice_packet.get("operation_id", "")]
    source_refs = slice_packet.get("source_refs", [])
    if not isinstance(source_refs, list):
        source_refs = []
    return "\n".join(
        [
            "You are a write-capable Phase-3 Action Card micro-slice worker.",
            "",
            f"workspace_root: {workspace_root}",
            f"run_dir: {run_dir}",
            f"slice_id: {slice_packet.get('slice_id', '')}",
            f"operation_id: {slice_packet.get('operation_id', '')}",
            f"operation_ids: {operation_ids}",
            "",
            "Do only the smallest viable implementation/test edit for this slice.",
            "Edit only allowed_edit_files. Do not run tests or install commands.",
            "Return after the edit; the adapter runs validation and records evidence.",
            "",
            "allowed_edit_files:",
            *[f"- {path}" for path in allowed_files],
            "",
            "owned_files:",
            *[f"- {normalize_rel_path(path)}" for path in slice_packet.get("owned_files", [])],
            "",
            "green_commands:",
            f"- unit_command: {green_commands.get('unit_command', '')}",
            f"- packet_command: {green_commands.get('packet_command', '')}",
            "",
            "done_criteria:",
            *[f"- {item}" for item in slice_packet.get("done_criteria", []) if str(item).strip()],
            "",
            "source_refs:",
            *[f"- {item}" for item in source_refs[:12] if str(item).strip()],
            "",
        ]
    )


def repair_prompt_text(
    *,
    slice_packet: dict[str, Any],
    workspace_root: Path,
    run_dir: Path,
    attempt_index: int,
    previous_blockers: list[str],
    commands_run: list[str],
    changed_files: list[str],
    forbidden_changes: list[str],
    stdout_tail: str = "",
    stderr_tail: str = "",
) -> str:
    return "\n".join(
        [
            f"Repair attempt {attempt_index} for the same Phase-3 Action Card slice.",
            "",
            "Stay inside the original allowed_edit_files boundary.",
            "Do not broaden scope, do not edit upstream truth, and do not run tests or install commands.",
            "Fix only the failure shown below. The adapter will rerun green_commands after this repair.",
            "",
            f"workspace_root: {workspace_root}",
            f"run_dir: {run_dir}",
            f"slice_id: {slice_packet.get('slice_id', '')}",
            f"operation_id: {slice_packet.get('operation_id', '')}",
            "",
            "previous_blockers:",
            *[f"- {blocker}" for blocker in previous_blockers],
            "",
            "commands_run:",
            *[f"- {command}" for command in commands_run],
            "",
            "changed_files_so_far:",
            *[f"- {path}" for path in changed_files],
            "",
            "forbidden_changes_detected:",
            *[f"- {path}" for path in forbidden_changes],
            "",
            "stdout_tail:",
            stdout_tail[-3000:],
            "",
            "stderr_tail:",
            stderr_tail[-3000:],
            "",
            "Full slice packet JSON:",
            json.dumps(slice_packet, ensure_ascii=False, indent=2, sort_keys=True),
            "",
        ]
    )


def invoke_agent_command(
    *,
    command: list[str],
    prompt_path: Path,
    workspace_root: Path,
    run_dir: Path,
    timeout_seconds: int | None = None,
    first_output_timeout_seconds: int | None = None,
    first_progress_timeout_seconds: int | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PHASE3_ACTION_CARD_AGENT_WORKSPACE_ROOT"] = str(workspace_root)
    env["PHASE3_ACTION_CARD_AGENT_RUN_DIR"] = str(run_dir)
    if command and Path(command[0]).name == "codex":
        final_command = [*command, "--cd", str(workspace_root), "-"]
        stdin_text = prompt_path.read_text(encoding="utf-8")
    else:
        final_command = [*command, str(prompt_path)]
        stdin_text = None
    timeout = timeout_seconds or env_timeout_seconds(
        "PHASE3_ACTION_CARD_AGENT_TIMEOUT_SECONDS",
        default=DEFAULT_AGENT_TIMEOUT_SECONDS,
    )
    if first_output_timeout_seconds is not None:
        return invoke_agent_command_with_first_output_timeout(
            final_command=final_command,
            stdin_text=stdin_text,
            workspace_root=workspace_root,
            env=env,
            timeout_seconds=timeout,
            first_output_timeout_seconds=first_output_timeout_seconds,
            first_progress_timeout_seconds=first_progress_timeout_seconds,
        )
    proc = subprocess.Popen(
        final_command,
        cwd=str(workspace_root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        stdin=subprocess.PIPE if stdin_text is not None else None,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(input=stdin_text, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
        raise subprocess.TimeoutExpired(
            cmd=final_command,
            timeout=timeout,
            output=stdout or exc.output,
            stderr=stderr or exc.stderr,
        ) from exc
    return subprocess.CompletedProcess(final_command, proc.returncode, stdout, stderr)


def invoke_agent_command_with_first_output_timeout(
    *,
    final_command: list[str],
    stdin_text: str | None,
    workspace_root: Path,
    env: dict[str, str],
    timeout_seconds: int,
    first_output_timeout_seconds: int,
    first_progress_timeout_seconds: int | None = None,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.Popen(
        final_command,
        cwd=str(workspace_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        stdin=subprocess.PIPE if stdin_text is not None else None,
        start_new_session=True,
    )
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []

    def kill_and_raise(timeout_value: int) -> None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
        raise subprocess.TimeoutExpired(
            cmd=final_command,
            timeout=timeout_value,
            output=b"".join([*stdout_chunks, stdout or b""]).decode(errors="replace"),
            stderr=b"".join([*stderr_chunks, stderr or b""]).decode(errors="replace"),
        )

    if proc.stdin and stdin_text is not None:
        proc.stdin.write(stdin_text.encode("utf-8"))
        proc.stdin.close()
        proc.stdin = None

    selector = selectors.DefaultSelector()
    if proc.stdout:
        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
    if proc.stderr:
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")

    command_uses_json = "--json" in final_command
    first_output_deadline = time.monotonic() + first_output_timeout_seconds
    first_progress_deadline = time.monotonic() + (first_progress_timeout_seconds or first_output_timeout_seconds)
    overall_deadline = time.monotonic() + timeout_seconds
    saw_output = False
    saw_progress = False
    while selector.get_map():
        now = time.monotonic()
        if not saw_output and now >= first_output_deadline:
            kill_and_raise(first_output_timeout_seconds)
        if command_uses_json and not saw_progress and now >= first_progress_deadline:
            kill_and_raise(first_progress_timeout_seconds or first_output_timeout_seconds)
        if now >= overall_deadline:
            kill_and_raise(timeout_seconds)
        if not saw_output:
            deadline = min(first_output_deadline, overall_deadline)
        elif command_uses_json and not saw_progress:
            deadline = min(first_progress_deadline, overall_deadline)
        else:
            deadline = overall_deadline
        events = selector.select(timeout=max(0.0, deadline - now))
        if not events:
            continue
        for key, _ in events:
            chunk = os.read(key.fileobj.fileno(), 65536)
            if not chunk:
                selector.unregister(key.fileobj)
                continue
            if chunk.strip():
                saw_output = True
            if is_progress_output(chunk, command_uses_json=command_uses_json):
                saw_progress = True
            if key.data == "stdout":
                stdout_chunks.append(chunk)
            else:
                stderr_chunks.append(chunk)
    return subprocess.CompletedProcess(
        final_command,
        proc.wait(),
        b"".join(stdout_chunks).decode(errors="replace"),
        b"".join(stderr_chunks).decode(errors="replace"),
    )


def is_progress_output(chunk: bytes, *, command_uses_json: bool) -> bool:
    text = chunk.decode(errors="replace")
    if not command_uses_json:
        return bool(text.strip())
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            return True
        if not isinstance(event, dict):
            return True
        event_type = str(event.get("type") or "")
        if event_type in {"thread.started", "turn.started"}:
            continue
        return True
    return False


def agent_timeout_blocker(*, command: list[str], timeout_seconds: int, changed_files: list[str]) -> str:
    if is_codex_command(command) and not changed_files:
        return f"agent_no_response_timeout:{timeout_seconds}:model={command_model_label(command)}"
    return f"agent_command_timeout:{timeout_seconds}"


def liveness_timeout_blocker(*, command: list[str], timeout_seconds: int) -> str:
    return f"agent_liveness_probe_timeout:{timeout_seconds}:model={command_model_label(command)}"


def decode_process_output(value: str | bytes | None) -> str:
    if isinstance(value, str):
        return value
    return (value or b"").decode(errors="replace")


def has_liveness_ok_response(*, stdout: str, stderr: str) -> bool:
    for line in [*stdout.splitlines(), *stderr.splitlines()]:
        if line.strip() == "OK":
            return True
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        item = event.get("item")
        if isinstance(item, dict) and str(item.get("text") or "").strip() == "OK":
            return True
    return False


def run_codex_liveness_probe(
    *,
    command: list[str],
    workspace_root: Path,
    run_dir: Path,
    adapter_dir: Path,
    slice_id: str,
) -> tuple[bool, dict[str, Any]]:
    prompt_path = adapter_dir / f"{slice_id.replace(':', '-')}.liveness-{command_model_label(command)}.prompt.md"
    prompt_path.write_text("Reply OK only.", encoding="utf-8")
    timeout_seconds = env_timeout_seconds(
        "PHASE3_ACTION_CARD_AGENT_LIVENESS_TIMEOUT_SECONDS",
        default=DEFAULT_AGENT_LIVENESS_TIMEOUT_SECONDS,
    )
    try:
        completed = invoke_agent_command(
            command=command,
            prompt_path=prompt_path,
            workspace_root=workspace_root,
            run_dir=run_dir,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = decode_process_output(exc.output)
        stderr = decode_process_output(exc.stderr)
        if has_liveness_ok_response(stdout=stdout, stderr=stderr):
            return True, {
                "model": command_model_label(command),
                "command": command_to_display(command),
                "prompt_path": str(prompt_path),
                "returncode": "timeout_after_live_response",
                "timeout_seconds": timeout_seconds,
                "stdout_tail": stdout[-4000:],
                "stderr_tail": stderr[-4000:],
                "blockers": [],
            }
        blocker = liveness_timeout_blocker(command=command, timeout_seconds=timeout_seconds)
        return False, {
            "model": command_model_label(command),
            "command": command_to_display(command),
            "prompt_path": str(prompt_path),
            "returncode": "timeout",
            "timeout_seconds": timeout_seconds,
            "stdout_tail": stdout[-4000:],
            "stderr_tail": stderr[-4000:],
            "blockers": [blocker],
        }
    blockers: list[str] = []
    if completed.returncode != 0:
        blockers.append(f"agent_liveness_probe_failed:{completed.returncode}:model={command_model_label(command)}")
    return completed.returncode == 0, {
        "model": command_model_label(command),
        "command": command_to_display(command),
        "prompt_path": str(prompt_path),
        "returncode": completed.returncode,
        "timeout_seconds": None,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "blockers": blockers,
    }


def command_candidates(slice_packet: dict[str, Any]) -> list[str]:
    green_commands = slice_packet.get("green_commands", {})
    if not isinstance(green_commands, dict):
        return []
    commands: list[str] = []
    keys = ["unit_command"]
    if env_flag("PHASE3_ACTION_CARD_RUN_PACKET_COMMANDS", default=False):
        keys.append("packet_command")
    for key in keys:
        value = str(green_commands.get(key) or "").strip()
        if value and value not in commands:
            commands.append(value)
    return commands


def deferred_command_candidates(slice_packet: dict[str, Any]) -> list[str]:
    if env_flag("PHASE3_ACTION_CARD_RUN_PACKET_COMMANDS", default=False):
        return []
    green_commands = slice_packet.get("green_commands", {})
    if not isinstance(green_commands, dict):
        return []
    packet_command = str(green_commands.get("packet_command") or "").strip()
    return [packet_command] if packet_command else []


def env_int(name: str, *, default: int, minimum: int = 0, maximum: int = 3) -> int:
    raw_value = str(os.environ.get(name) or "").strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))


def run_green_commands(
    *,
    workspace_root: Path,
    slice_packet: dict[str, Any],
    run_dir: Path,
) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    commands_run: list[str] = []
    blockers: list[str] = []
    reports: list[dict[str, Any]] = []
    env = os.environ.copy()
    env["PHASE3_RUN_DIR"] = str(run_dir)
    timeout_seconds = env_timeout_seconds(
        "PHASE3_ACTION_CARD_COMMAND_TIMEOUT_SECONDS",
        default=DEFAULT_COMMAND_TIMEOUT_SECONDS,
    )
    for command in command_candidates(slice_packet):
        try:
            completed = subprocess.run(
                command,
                cwd=str(workspace_root),
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.output if isinstance(exc.output, str) else (exc.output or b"").decode(errors="replace")
            stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace")
            commands_run.append(command)
            reports.append(
                {
                    "command": command,
                    "returncode": "timeout",
                    "timeout_seconds": timeout_seconds,
                    "stdout_tail": stdout[-4000:],
                    "stderr_tail": stderr[-4000:],
                }
            )
            blockers.append(f"command_timeout:{timeout_seconds}:{command}")
            continue
        commands_run.append(command)
        reports.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout_tail": (completed.stdout or "")[-4000:],
                "stderr_tail": (completed.stderr or "")[-4000:],
            }
        )
        if completed.returncode != 0:
            blockers.append(f"command_failed:{command}")
    return commands_run, blockers, reports


def build_blocked_result(*, slice_id: str, blockers: list[str], commands_run: list[str] | None = None) -> dict[str, Any]:
    return {
        "slice_id": slice_id,
        "status": "blocked",
        "changed_files": [],
        "commands_run": commands_run or [],
        "evidence_summary": "; ".join(blockers) or "blocked",
        "blockers": blockers,
        "claim_ceiling": DEFAULT_CLAIM_CEILING,
    }


def safe_slice_result_name(slice_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", slice_id).strip("-") or "slice"


def run_adapter(*, slice_packet_path: Path, result_path: Path, workspace_root: Path, run_dir: Path) -> int:
    slice_packet = load_json(slice_packet_path)
    slice_id = str(slice_packet.get("slice_id") or "").strip() or "slice"
    allowed_files = allowed_file_paths(slice_packet)
    if not allowed_files:
        write_json(
            result_path,
            build_blocked_result(slice_id=slice_id, blockers=["no_allowed_edit_files"]),
        )
        return 2
    command = resolve_agent_command()
    if not command:
        write_json(
            result_path,
            build_blocked_result(slice_id=slice_id, blockers=["no_write_capable_code_agent_command"]),
        )
        return 2

    adapter_dir = run_dir / "action-card-agent-adapter"
    prompt_path = adapter_dir / f"{slice_id.replace(':', '-')}.prompt.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path = adapter_dir / f"{slice_id.replace(':', '-')}.agent-output.json"
    with tempfile.TemporaryDirectory(prefix="action-card-slice-") as tmp_dir:
        isolated_workspace_root = Path(tmp_dir) / "workspace"
        copy_workspace_for_slice(workspace_root=workspace_root, target_root=isolated_workspace_root)
        isolated_before = snapshot_workspace_files(isolated_workspace_root)
        before = {rel_path: isolated_before.get(rel_path, "") for rel_path in allowed_files}
        prompt_path.write_text(
            prompt_text(slice_packet=slice_packet, workspace_root=isolated_workspace_root, run_dir=run_dir),
            encoding="utf-8",
        )
        agent_timeout_seconds = env_timeout_seconds(
            "PHASE3_ACTION_CARD_AGENT_TIMEOUT_SECONDS",
            default=DEFAULT_AGENT_TIMEOUT_SECONDS,
        )
        agent_first_output_timeout_seconds = env_timeout_seconds(
            "PHASE3_ACTION_CARD_AGENT_FIRST_OUTPUT_TIMEOUT_SECONDS",
            default=DEFAULT_AGENT_FIRST_OUTPUT_TIMEOUT_SECONDS,
        )
        agent_first_progress_timeout_seconds = env_timeout_seconds(
            "PHASE3_ACTION_CARD_AGENT_FIRST_PROGRESS_TIMEOUT_SECONDS",
            default=DEFAULT_AGENT_FIRST_PROGRESS_TIMEOUT_SECONDS,
        )
        max_repair_attempts = env_int("PHASE3_ACTION_CARD_REPAIR_MAX_ATTEMPTS", default=1, minimum=0, maximum=3)
        command_variants = agent_command_variants(command)
        liveness_reports: list[dict[str, Any]] = []
        live_command_variants: list[list[str]] = []
        liveness_blockers: list[str] = []
        if is_codex_command(command):
            for candidate in command_variants:
                liveness_ok, liveness_report = run_codex_liveness_probe(
                    command=candidate,
                    workspace_root=isolated_workspace_root,
                    run_dir=run_dir,
                    adapter_dir=adapter_dir,
                    slice_id=slice_id,
                )
                liveness_reports.append(liveness_report)
                if liveness_ok:
                    live_command_variants.append(candidate)
                else:
                    liveness_blockers.extend(str(blocker) for blocker in liveness_report.get("blockers", []))
        else:
            live_command_variants = command_variants
        attempts: list[dict[str, Any]] = []
        deferred_commands = deferred_command_candidates(slice_packet)
        commands_run: list[str] = []
        command_reports: list[dict[str, Any]] = []
        blockers: list[str] = []
        changed_files: list[str] = []
        forbidden_changes: list[str] = []
        status = "blocked"
        completed = subprocess.CompletedProcess(command, 2, "", "")
        agent_timeout = False
        observed_agent_timeout_seconds = agent_timeout_seconds
        current_prompt_path = prompt_path
        repair_attempt_count = 0
        if not live_command_variants:
            blockers = ["no_live_agent_command_variant", *liveness_blockers]
        for variant_index, active_command in enumerate(live_command_variants):
            base_prompt_path = prompt_path
            if variant_index > 0:
                base_prompt_path = adapter_dir / f"{slice_id.replace(':', '-')}.fallback-{variant_index}.compact.prompt.md"
                base_prompt_path.write_text(
                    compact_prompt_text(
                        slice_packet=slice_packet,
                        workspace_root=isolated_workspace_root,
                        run_dir=run_dir,
                    ),
                    encoding="utf-8",
                )
            current_prompt_path = base_prompt_path
            compact_no_response_retry_used = False
            attempt_index = 0
            while attempt_index <= max_repair_attempts:
                if attempt_index > 0:
                    repair_attempt_count += 1
                    current_prompt_path = (
                        adapter_dir
                        / f"{slice_id.replace(':', '-')}.fallback-{variant_index}.repair-{attempt_index}.prompt.md"
                    )
                    last_report = command_reports[-1] if command_reports else {}
                    current_prompt_path.write_text(
                        repair_prompt_text(
                            slice_packet=slice_packet,
                            workspace_root=isolated_workspace_root,
                            run_dir=run_dir,
                            attempt_index=repair_attempt_count,
                            previous_blockers=blockers,
                            commands_run=commands_run,
                            changed_files=changed_files,
                            forbidden_changes=forbidden_changes,
                            stdout_tail=str(last_report.get("stdout_tail") or ""),
                            stderr_tail=str(last_report.get("stderr_tail") or ""),
                        ),
                        encoding="utf-8",
                    )
                agent_timeout = False
                observed_agent_timeout_seconds = agent_timeout_seconds
                attempt_started_monotonic = time.monotonic()
                try:
                    completed = invoke_agent_command(
                        command=active_command,
                        prompt_path=current_prompt_path,
                        workspace_root=isolated_workspace_root,
                        run_dir=run_dir,
                        timeout_seconds=agent_timeout_seconds,
                        first_output_timeout_seconds=(
                            agent_first_output_timeout_seconds
                            if is_codex_command(active_command) and codex_command_uses_json(active_command)
                            else None
                        ),
                        first_progress_timeout_seconds=agent_first_progress_timeout_seconds,
                    )
                except subprocess.TimeoutExpired as exc:
                    agent_timeout = True
                    observed_agent_timeout_seconds = int(exc.timeout or agent_timeout_seconds)
                    completed = subprocess.CompletedProcess(
                        exc.cmd if isinstance(exc.cmd, list) else active_command,
                        "timeout",
                        (exc.output or "") if isinstance(exc.output, str) else (exc.output or b"").decode(errors="replace"),
                        (exc.stderr or "") if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace"),
                    )
                attempt_duration_seconds = round(max(0.0, time.monotonic() - attempt_started_monotonic), 3)
                isolated_after = snapshot_workspace_files(isolated_workspace_root)
                after = {rel_path: isolated_after.get(rel_path, "") for rel_path in allowed_files}
                changed_files = changed_allowed_files(before, after)
                if agent_timeout:
                    current_commands_run, command_blockers, current_command_reports = [], [], []
                else:
                    current_commands_run, command_blockers, current_command_reports = run_green_commands(
                        workspace_root=isolated_workspace_root,
                        slice_packet=slice_packet,
                        run_dir=run_dir,
                    )
                isolated_after_commands = snapshot_workspace_files(isolated_workspace_root)
                after = {rel_path: isolated_after_commands.get(rel_path, "") for rel_path in allowed_files}
                changed_files = changed_allowed_files(before, after)
                forbidden_changes = sorted(
                    set(changed_workspace_files(isolated_before, isolated_after_commands)) - set(allowed_files)
                )
                commands_run.extend(current_commands_run)
                command_reports.extend(current_command_reports)
                blockers = []
                if agent_timeout:
                    blockers.append(
                        agent_timeout_blocker(
                            command=active_command,
                            timeout_seconds=observed_agent_timeout_seconds,
                            changed_files=changed_files,
                        )
                    )
                elif completed.returncode != 0:
                    blockers.append(f"agent_command_failed:{completed.returncode}")
                blockers.extend(command_blockers)
                blockers.extend(f"forbidden_file_changes_detected:{rel_path}" for rel_path in forbidden_changes)
                status = "implemented" if changed_files else "done"
                if blockers:
                    status = "blocked"
                attempts.append(
                    {
                        "attempt": len(attempts),
                        "variant_index": variant_index,
                        "model": command_model_label(active_command),
                        "command": command_to_display(active_command),
                        "prompt_path": str(current_prompt_path),
                        "returncode": completed.returncode,
                        "duration_seconds": attempt_duration_seconds,
                        "timeout_seconds": observed_agent_timeout_seconds if agent_timeout else None,
                        "stdout_tail": completed.stdout[-4000:],
                        "stderr_tail": completed.stderr[-4000:],
                        "changed_files": changed_files,
                        "forbidden_changes": forbidden_changes,
                        "commands_run": current_commands_run,
                        "command_reports": current_command_reports,
                        "blockers": blockers,
                        "status": status,
                    }
                )
                if status in {"implemented", "done"}:
                    break
                if agent_timeout and not changed_files and variant_index + 1 < len(live_command_variants):
                    break
                if agent_timeout and not changed_files and is_codex_command(active_command) and not compact_no_response_retry_used:
                    compact_no_response_retry_used = True
                    current_prompt_path = (
                        adapter_dir / f"{slice_id.replace(':', '-')}.fallback-{variant_index}.no-response-compact.prompt.md"
                    )
                    current_prompt_path.write_text(
                        compact_prompt_text(
                            slice_packet=slice_packet,
                            workspace_root=isolated_workspace_root,
                            run_dir=run_dir,
                        ),
                        encoding="utf-8",
                    )
                    continue
                if agent_timeout or any(blocker.startswith("forbidden_file_changes_detected:") for blocker in blockers):
                    break
                attempt_index += 1
            if status in {"implemented", "done"}:
                break
        write_json(
            transcript_path,
            {
                "command": command_to_display(command),
                "selected_command": command_to_display(active_command) if live_command_variants else "",
                "returncode": completed.returncode,
                "timeout_seconds": observed_agent_timeout_seconds if agent_timeout else None,
                "stdout_tail": completed.stdout[-8000:],
                "stderr_tail": completed.stderr[-8000:],
                "prompt_path": str(current_prompt_path),
                "workspace_root": str(isolated_workspace_root),
                "liveness_reports": liveness_reports,
                "attempts": attempts,
            },
        )
        if status == "implemented":
            copy_allowed_changes_back(
                isolated_workspace_root=isolated_workspace_root,
                workspace_root=workspace_root,
                changed_files=changed_files,
            )
    result = {
        "slice_id": slice_id,
        "status": status,
        "changed_files": changed_files,
        "commands_run": commands_run,
        "deferred_commands": deferred_commands,
        "repair_attempt_count": repair_attempt_count,
        "evidence_summary": (
            f"{command_to_display(command)} updated {len(changed_files)} allowed files"
            if status == "implemented"
            else f"{command_to_display(command)} completed with no allowed file changes required"
            if status == "done"
            else "; ".join(blockers)
        ),
        "blockers": blockers,
        "claim_ceiling": DEFAULT_CLAIM_CEILING,
        "adapter": {
            "kind": str(os.environ.get("PHASE3_ACTION_CARD_RUNNER_KIND") or "generic").strip() or "generic",
            "prompt_path": str(prompt_path),
            "transcript_path": str(transcript_path),
        },
    }
    write_json(result_path, result)
    return 0 if status in {"implemented", "done"} else 2


def run_batch_adapter(
    *,
    slice_manifest_path: Path,
    result_dir: Path,
    workspace_root: Path,
    run_dir: Path,
    max_workers: int,
) -> int:
    manifest = load_json(slice_manifest_path)
    ready_slices = [
        row
        for row in manifest.get("slice_runs", []) or []
        if isinstance(row, dict) and str(row.get("slice_status") or "").strip() == "ready"
    ]
    adapter_dir = run_dir / "action-card-agent-adapter"
    packet_dir = adapter_dir / "batch-slice-packets"
    result_dir.mkdir(parents=True, exist_ok=True)
    packet_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    started_monotonic = time.monotonic()
    for slice_run in ready_slices:
        slice_id = str(slice_run.get("slice_id") or "slice").strip() or "slice"
        safe_name = safe_slice_result_name(slice_id)
        packet_path = packet_dir / f"{safe_name}.json"
        result_path = result_dir / f"{safe_name}.result.json"
        write_json(packet_path, slice_run)
        slice_started_monotonic = time.monotonic()
        returncode = run_adapter(
            slice_packet_path=packet_path,
            result_path=result_path,
            workspace_root=workspace_root,
            run_dir=run_dir,
        )
        duration_seconds = round(max(0.0, time.monotonic() - slice_started_monotonic), 3)
        result_payload = load_json(result_path) if result_path.exists() else build_blocked_result(
            slice_id=slice_id,
            blockers=["batch_adapter_result_missing"],
        )
        adapter_payload = result_payload.get("adapter", {}) if isinstance(result_payload.get("adapter"), dict) else {}
        result_payload["adapter"] = {
            **adapter_payload,
            "batch_mode": "sequential",
            "batch_packet_path": str(packet_path),
            "batch_max_workers": max_workers,
        }
        write_json(result_path, result_payload)
        results.append(
            {
                "slice_id": slice_id,
                "status": result_payload.get("status", ""),
                "returncode": returncode,
                "duration_seconds": duration_seconds,
                "result_path": str(result_path),
                "changed_files": result_payload.get("changed_files", []),
                "blockers": result_payload.get("blockers", []),
            }
        )
    report = {
        "mode": "sequential",
        "slice_manifest_path": str(slice_manifest_path),
        "result_dir": str(result_dir),
        "workspace_root": str(workspace_root),
        "run_dir": str(run_dir),
        "max_workers": max_workers,
        "ready_slice_count": len(ready_slices),
        "result_count": len(results),
        "implemented_count": sum(1 for row in results if row.get("status") in {"implemented", "done"}),
        "blocked_count": sum(1 for row in results if row.get("status") not in {"implemented", "done"}),
        "duration_seconds": round(max(0.0, time.monotonic() - started_monotonic), 3),
        "results": results,
    }
    write_json(adapter_dir / "batch-runner-report.json", report)
    return 0 if report["blocked_count"] == 0 else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase-3 Action Card slices through a code-agent adapter")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--slice-packet")
    mode.add_argument("--slice-manifest")
    parser.add_argument("--result")
    parser.add_argument("--result-dir")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--max-workers", type=int, default=1)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.slice_manifest:
        if not args.result_dir:
            raise SystemExit("--result-dir is required with --slice-manifest")
        return run_batch_adapter(
            slice_manifest_path=Path(args.slice_manifest).resolve(),
            result_dir=Path(args.result_dir).resolve(),
            workspace_root=Path(args.workspace_root).resolve(),
            run_dir=Path(args.run_dir).resolve(),
            max_workers=max(1, int(args.max_workers or 1)),
        )
    if not args.result:
        raise SystemExit("--result is required with --slice-packet")
    return run_adapter(
        slice_packet_path=Path(args.slice_packet).resolve(),
        result_path=Path(args.result).resolve(),
        workspace_root=Path(args.workspace_root).resolve(),
        run_dir=Path(args.run_dir).resolve(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
