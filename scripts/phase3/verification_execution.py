from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from common.output_language import localize_phase3_verification_report
from phase3.execution_packet_access import load_json_if_exists, requires_toolchain_bootstrap
import phase3.execution_runtime_preflight as runtime_preflight
from phase3.renderer_common import ascii_slug
from phase3.review_support import write_json_and_markdown_report
from phase3.verification_backend_evidence import (
    analyze_backend_evidence,
    flatten_packet_tests,
    normalize_test_target,
    packet_lane,
)


ShellResolver = Callable[[], str]
SubprocessRun = Callable[..., subprocess.CompletedProcess[str]]
RunShellCommand = Callable[..., tuple[subprocess.CompletedProcess[str], bool]]
RuntimePreflightStarter = Callable[..., dict[str, Any]]
RuntimePreflightTeardown = Callable[..., None]

LEGACY_TARGETED_STEP = "targeted-tests"
CRITICAL_TARGETED_STEP = "critical-targeted-tests"
FULL_TARGETED_STEP = "full-targeted-tests"
VERIFICATION_STEP_NAMES = (
    "lint",
    "typecheck",
    CRITICAL_TARGETED_STEP,
    LEGACY_TARGETED_STEP,
    FULL_TARGETED_STEP,
    "unit-tests",
    "build",
)

REPORT_FILENAMES = {
    "lint": "lint-report.json",
    "typecheck": "typecheck-report.json",
    "unit-tests": "unit-test-report.json",
    LEGACY_TARGETED_STEP: "test-report.json",
    CRITICAL_TARGETED_STEP: "test-report.json",
    FULL_TARGETED_STEP: "full-test-report.json",
    "build": "build-report.json",
}

VITEST_STEP_CATEGORIES = {
    "unit-tests": ("unit",),
    LEGACY_TARGETED_STEP: ("sql", "contract", "scenario", "replay"),
    CRITICAL_TARGETED_STEP: ("sql", "contract", "scenario", "replay"),
    FULL_TARGETED_STEP: ("sql", "contract", "scenario", "replay"),
}

DEFAULT_STEP_TIMEOUT_SECONDS = 900
MAX_STEP_TIMEOUT_SECONDS = 7200
FULL_TARGETED_SEQUENTIAL_TIMEOUT_OVERHEAD_SECONDS = 300
DEFAULT_VERIFICATION_MAX_WORKERS = 2
MAX_VERIFICATION_MAX_WORKERS = 4

PLACEHOLDER_COMMAND_PATTERNS = (
    re.compile(r"^\s*echo\b", re.IGNORECASE),
    re.compile(r"^\s*/bin/(?:sh|zsh)\s+-c\s+['\"]\s*echo\b", re.IGNORECASE),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def epoch_to_utc_iso(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_verification_progress(
    *,
    run_dir: Path,
    events: list[dict[str, Any]],
    status: str,
    current_step: str = "",
) -> None:
    write_text(
        run_dir / "verification-progress.json",
        json.dumps(
            {
                "status": status,
                "current_step": current_step,
                "updated_at": utc_now_iso(),
                "events": events,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def vitest_step_expected_tests(
    *,
    packet_document: dict[str, Any],
    step_name: str,
    step_reporting: dict[str, Any],
) -> list[str]:
    explicit_targets = step_reporting.get("test_targets", [])
    if isinstance(explicit_targets, list):
        normalized = sorted({str(item).strip() for item in explicit_targets if str(item).strip()})
        if normalized:
            return normalized
    return flatten_packet_tests(packet_document, VITEST_STEP_CATEGORIES[step_name])


def expand_env_tokens(value: str, env: dict[str, str]) -> str:
    expanded = value
    for key, replacement in env.items():
        expanded = expanded.replace(f"${{{key}}}", replacement)
        expanded = expanded.replace(f"${key}", replacement)
    return expanded


def resolve_path(raw_path: str, *, env: dict[str, str], workspace_root: Path) -> Path:
    expanded = expand_env_tokens(raw_path, env).strip()
    path = Path(expanded)
    if not path.is_absolute():
        path = (workspace_root / path).resolve()
    return path


def looks_like_placeholder_command(command: str) -> bool:
    normalized = command.strip()
    if not normalized:
        return True
    return any(pattern.match(normalized) for pattern in PLACEHOLDER_COMMAND_PATTERNS)


def extract_vitest_suite_paths(payload: dict[str, Any], *, workspace_root: Path) -> tuple[list[str], list[str], bool]:
    suites = payload.get("testResults", [])
    if not isinstance(suites, list):
        return [], [], False

    non_failing_assertion_statuses = {"passed", "skipped", "pending", "todo"}
    passed: set[str] = set()
    failed: set[str] = set()
    recognized = False
    for suite in suites:
        if not isinstance(suite, dict):
            continue
        suite_name = normalize_test_target(str(suite.get("name", "")).strip(), workspace_root=workspace_root)
        if not suite_name:
            continue
        suite_status = str(suite.get("status", "")).strip().lower()
        assertion_results = suite.get("assertionResults", [])
        assertion_statuses = [
            str(item.get("status", "")).strip().lower()
            for item in assertion_results
            if isinstance(item, dict) and str(item.get("status", "")).strip()
        ]
        if assertion_statuses:
            recognized = True
            if any(status == "failed" for status in assertion_statuses):
                failed.add(suite_name)
            elif all(status in non_failing_assertion_statuses for status in assertion_statuses):
                passed.add(suite_name)
        elif suite_status in {"passed", "failed"}:
            recognized = True
            if suite_status == "passed":
                passed.add(suite_name)
            else:
                failed.add(suite_name)
    return sorted(passed), sorted(failed), recognized


def evaluate_vitest_step(
    *,
    completed: subprocess.CompletedProcess[str],
    packet_tests: list[str],
    reporting: dict[str, Any],
    execution_env: dict[str, str],
    workspace_root: Path,
) -> dict[str, Any]:
    parser_name = str(reporting.get("parser", "")).strip()
    report_path_raw = str(reporting.get("report_path", "")).strip()
    expected_tests = sorted(
        {
            normalize_test_target(test, workspace_root=workspace_root)
            for test in packet_tests
            if normalize_test_target(test, workspace_root=workspace_root)
        }
    )
    if parser_name != "vitest-json" or not report_path_raw:
        return {
            "verdict": "fail",
            "failure_reason": "unstructured_test_verification",
            "verification_method": "unverified",
            "recognized_framework_output": False,
            "passed_tests": [],
            "failed_tests": expected_tests if completed.returncode else [],
            "missing_expected_tests": expected_tests,
            "framework_report_path": "",
        }

    report_path = resolve_path(report_path_raw, env=execution_env, workspace_root=workspace_root)
    payload = load_json_if_exists(report_path)
    if payload is None:
        return {
            "verdict": "fail",
            "failure_reason": "framework_report_missing",
            "verification_method": "vitest-json",
            "recognized_framework_output": False,
            "passed_tests": [],
            "failed_tests": expected_tests if completed.returncode else [],
            "missing_expected_tests": expected_tests,
            "framework_report_path": str(report_path),
        }

    observed_passed, observed_failed, recognized = extract_vitest_suite_paths(payload, workspace_root=workspace_root)
    expected_set = set(expected_tests)
    observed_passed_set = set(observed_passed)
    observed_failed_set = set(observed_failed)
    missing_expected_tests = sorted(expected_set - observed_passed_set - observed_failed_set)
    relevant_failed_tests = sorted(expected_set & observed_failed_set)

    failure_reason = ""
    verdict = "pass"
    if completed.returncode != 0:
        verdict = "fail"
        failure_reason = "framework_command_failed"
    elif not recognized:
        verdict = "fail"
        failure_reason = "framework_output_unrecognized"
    elif relevant_failed_tests:
        verdict = "fail"
        failure_reason = "reported_test_failures"
    elif missing_expected_tests:
        verdict = "fail"
        failure_reason = "expected_tests_missing_from_report"

    return {
        "verdict": verdict,
        "failure_reason": failure_reason,
        "verification_method": "vitest-json",
        "recognized_framework_output": recognized,
        "passed_tests": sorted(expected_set & observed_passed_set),
        "failed_tests": sorted(set(relevant_failed_tests) | set(missing_expected_tests)),
        "missing_expected_tests": missing_expected_tests,
        "framework_report_path": str(report_path),
        "observed_passed_tests": observed_passed,
        "observed_failed_tests": observed_failed,
    }


def build_verification_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    lines = [
        "# Phase-3 Verification Report",
        "",
        "## Summary",
        f"- packet_id: {report.get('packet_id', 'unknown')}",
        f"- overall_verdict: {report.get('overall_verdict', 'unknown')}",
        f"- executed_step_count: {report.get('summary', {}).get('executed_step_count', 0)}",
        f"- failed_step_count: {report.get('summary', {}).get('failed_step_count', 0)}",
        "",
        "## Steps",
    ]
    for row in report.get("steps", []) or [{"step": "none", "verdict": "", "command": ""}]:
        if row["step"] == "none":
            lines.append("- none")
        else:
            lines.append(
                f"- {row['step']} [{row['verdict']}] exit={row['exit_code']} duration_ms={row['duration_ms']}"
            )
    return localize_phase3_verification_report("\n".join(lines) + "\n", output_locale)


def clamp_step_timeout_seconds(value: int) -> int:
    return max(5, min(int(value), MAX_STEP_TIMEOUT_SECONDS))


def resolve_step_timeout_seconds() -> int:
    raw = str(os.environ.get("PHASE3_VERIFICATION_STEP_TIMEOUT_SECONDS", str(DEFAULT_STEP_TIMEOUT_SECONDS))).strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = DEFAULT_STEP_TIMEOUT_SECONDS
    return clamp_step_timeout_seconds(value)


def command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return str(command).split()


def command_option_int(tokens: list[str], option_name: str, default: int) -> int:
    for index, token in enumerate(tokens):
        if token == option_name and index + 1 < len(tokens):
            try:
                return int(tokens[index + 1])
            except ValueError:
                return default
        prefix = f"{option_name}="
        if token.startswith(prefix):
            try:
                return int(token[len(prefix):])
            except ValueError:
                return default
    return default


def command_option_count(tokens: list[str], option_name: str) -> int:
    count = 0
    for token in tokens:
        if token == option_name or token.startswith(f"{option_name}="):
            count += 1
    return count


def resolve_effective_step_timeout_seconds(
    *,
    step_name: str,
    command: str,
    base_timeout_seconds: int,
) -> int:
    base_timeout = clamp_step_timeout_seconds(base_timeout_seconds)
    if str(step_name).strip() != FULL_TARGETED_STEP:
        return base_timeout
    if "run_vitest_targets_sequentially.py" not in str(command):
        return base_timeout

    tokens = command_tokens(command)
    target_count = command_option_count(tokens, "--target")
    if target_count <= 0:
        return base_timeout
    target_timeout_seconds = max(1, command_option_int(tokens, "--target-timeout-seconds", 120))
    sequential_timeout = (
        target_count * target_timeout_seconds
        + FULL_TARGETED_SEQUENTIAL_TIMEOUT_OVERHEAD_SECONDS
    )
    return clamp_step_timeout_seconds(max(base_timeout, sequential_timeout))


def timeout_output(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return ""


def run_shell_command(
    *,
    command: str,
    workspace_root: Path,
    execution_env: dict[str, str],
    timeout_seconds: int,
    subprocess_run: SubprocessRun | None = None,
    shell_resolver: ShellResolver | None = None,
) -> tuple[subprocess.CompletedProcess[str], bool]:
    run_command = subprocess_run or subprocess.run
    resolve_shell = shell_resolver or (lambda: "/bin/sh")
    try:
        completed = run_command(
            command,
            cwd=workspace_root,
            shell=True,
            executable=resolve_shell(),
            text=True,
            capture_output=True,
            env=execution_env,
            timeout=timeout_seconds,
        )
        return completed, False
    except subprocess.TimeoutExpired as exc:
        stderr = timeout_output(exc.stderr)
        if stderr and not stderr.endswith("\n"):
            stderr += "\n"
        stderr += f"command timed out after {timeout_seconds}s\n"
        completed = subprocess.CompletedProcess(
            command,
            124,
            timeout_output(exc.stdout),
            stderr,
        )
        return completed, True


def build_step_duration_summary(step_reports: list[dict[str, Any]]) -> dict[str, Any]:
    by_step: dict[str, int] = {}
    total = 0
    longest_step = {"step": "", "duration_ms": 0}
    count = 0
    for row in step_reports:
        if not isinstance(row, dict):
            continue
        step = str(row.get("step", "")).strip()
        value = row.get("duration_ms", 0)
        if not step or not isinstance(value, (int, float)):
            continue
        duration_ms = int(value)
        by_step[step] = duration_ms
        total += duration_ms
        count += 1
        if duration_ms > int(longest_step["duration_ms"]):
            longest_step = {"step": step, "duration_ms": duration_ms}
    if CRITICAL_TARGETED_STEP in by_step and LEGACY_TARGETED_STEP not in by_step:
        by_step[LEGACY_TARGETED_STEP] = by_step[CRITICAL_TARGETED_STEP]
    if FULL_TARGETED_STEP in by_step and LEGACY_TARGETED_STEP not in by_step:
        by_step[LEGACY_TARGETED_STEP] = by_step[FULL_TARGETED_STEP]
    return {
        "count": count,
        "total": total,
        "by_step": by_step,
        "longest_step": longest_step,
    }


def resolve_verification_max_workers() -> int:
    raw = os.environ.get("PHASE3_VERIFICATION_MAX_WORKERS", str(DEFAULT_VERIFICATION_MAX_WORKERS)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = DEFAULT_VERIFICATION_MAX_WORKERS
    return max(1, min(MAX_VERIFICATION_MAX_WORKERS, value))


def collect_verification_step_inputs(sequence: list[Any], commands: dict[str, Any]) -> list[dict[str, str]]:
    step_inputs: list[dict[str, str]] = []
    seen: set[str] = set()
    for step in sequence:
        step_name = str(step).strip()
        if not step_name or step_name in seen:
            continue
        command = str(commands.get(step_name, "")).strip()
        if not command:
            continue
        seen.add(step_name)
        step_inputs.append({"step": step_name, "command": command})
    return step_inputs


def can_parallelize_verification_steps(step_inputs: list[dict[str, str]], max_workers: int) -> bool:
    if max_workers <= 1 or len(step_inputs) <= 1:
        return False
    report_filenames = [
        REPORT_FILENAMES.get(str(row.get("step", "")).strip())
        for row in step_inputs
        if REPORT_FILENAMES.get(str(row.get("step", "")).strip())
    ]
    return len(report_filenames) == len(set(report_filenames))


def execute_verification_step(
    *,
    step_name: str,
    command: str,
    packet_document: dict[str, Any],
    reporting: dict[str, Any],
    workspace_root: Path,
    run_dir: Path,
    execution_env: dict[str, str],
    step_timeout_seconds: int,
    subprocess_run: SubprocessRun | None = None,
    shell_resolver: ShellResolver | None = None,
) -> dict[str, Any]:
    logs_dir = run_dir / "verification-logs"
    step_slug = ascii_slug(step_name, fallback="step")
    stdout_path = logs_dir / f"{step_slug}.stdout.log"
    stderr_path = logs_dir / f"{step_slug}.stderr.log"
    effective_step_timeout_seconds = resolve_effective_step_timeout_seconds(
        step_name=step_name,
        command=command,
        base_timeout_seconds=step_timeout_seconds,
    )
    started_at = time.time()
    started_monotonic = time.monotonic()
    if looks_like_placeholder_command(command):
        completed = subprocess.CompletedProcess(command, 1, "", "")
        duration_ms = int((time.monotonic() - started_monotonic) * 1000)
        verdict = "fail"
        step_evidence = {
            "failure_reason": "placeholder_command_detected",
            "verification_method": "placeholder-command",
        }
    elif requires_toolchain_bootstrap(command) and not (workspace_root / "node_modules").exists():
        completed = subprocess.CompletedProcess(command, 1, "", "")
        duration_ms = int((time.monotonic() - started_monotonic) * 1000)
        verdict = "fail"
        step_evidence = {
            "failure_reason": "toolchain_not_bootstrapped",
            "verification_method": "toolchain-preflight",
            "bootstrap_command": f"pnpm install --dir {workspace_root} --frozen-lockfile=false",
        }
    elif step_name in VITEST_STEP_CATEGORIES:
        step_reporting = reporting.get(step_name, {}) if isinstance(reporting, dict) else {}
        if not isinstance(step_reporting, dict):
            step_reporting = {}
        completed, timed_out = run_shell_command(
            command=command,
            workspace_root=workspace_root,
            execution_env=execution_env,
            timeout_seconds=effective_step_timeout_seconds,
            subprocess_run=subprocess_run,
            shell_resolver=shell_resolver,
        )
        duration_ms = int((time.monotonic() - started_monotonic) * 1000)
        if timed_out:
            verdict = "fail"
            step_evidence = {
                "failure_reason": "command_timeout",
                "verification_method": "timeout",
                "timeout_seconds": effective_step_timeout_seconds,
            }
        else:
            step_evidence = evaluate_vitest_step(
                completed=completed,
                packet_tests=vitest_step_expected_tests(
                    packet_document=packet_document,
                    step_name=step_name,
                    step_reporting=step_reporting,
                ),
                reporting=step_reporting,
                execution_env=execution_env,
                workspace_root=workspace_root,
            )
            verdict = str(step_evidence.get("verdict", "fail")).strip() or "fail"
    else:
        completed, timed_out = run_shell_command(
            command=command,
            workspace_root=workspace_root,
            execution_env=execution_env,
            timeout_seconds=effective_step_timeout_seconds,
            subprocess_run=subprocess_run,
            shell_resolver=shell_resolver,
        )
        duration_ms = int((time.monotonic() - started_monotonic) * 1000)
        if timed_out:
            verdict = "fail"
            step_evidence = {
                "failure_reason": "command_timeout",
                "verification_method": "timeout",
                "timeout_seconds": effective_step_timeout_seconds,
            }
        else:
            verdict = "pass" if completed.returncode == 0 else "fail"
            step_evidence = {
                "failure_reason": "" if completed.returncode == 0 else "command_failed",
                "verification_method": "exit-code",
            }

    finished_at = time.time()
    write_text(stdout_path, completed.stdout)
    write_text(stderr_path, completed.stderr)
    step_report = {
        "step": step_name,
        "command": command,
        "verdict": verdict,
        "exit_code": int(completed.returncode),
        "duration_ms": duration_ms,
        "started_at_epoch_s": started_at,
        "finished_at_epoch_s": finished_at,
        "stdout_log_path": str(stdout_path),
        "stderr_log_path": str(stderr_path),
        "verification_method": str(step_evidence.get("verification_method", "")).strip(),
        "failure_reason": str(step_evidence.get("failure_reason", "")).strip(),
    }
    step_payload: dict[str, Any] | None = None
    report_filename = REPORT_FILENAMES.get(step_name)
    if report_filename:
        report_path = run_dir / report_filename
        if step_name in VITEST_STEP_CATEGORIES:
            step_payload = {
                "verdict": verdict,
                "command": command,
                "exit_code": int(completed.returncode),
                "verification_method": step_evidence.get("verification_method", ""),
                "recognized_framework_output": bool(step_evidence.get("recognized_framework_output", False)),
                "framework_report_path": step_evidence.get("framework_report_path", ""),
                "passed_tests": step_evidence.get("passed_tests", []),
                "failed_tests": step_evidence.get("failed_tests", []),
                "missing_expected_tests": step_evidence.get("missing_expected_tests", []),
                "observed_passed_tests": step_evidence.get("observed_passed_tests", []),
                "observed_failed_tests": step_evidence.get("observed_failed_tests", []),
                "failure_reason": step_evidence.get("failure_reason", ""),
                "bootstrap_command": step_evidence.get("bootstrap_command", ""),
                "stdout_log_path": str(stdout_path),
                "stderr_log_path": str(stderr_path),
            }
        else:
            step_payload = {
                "verdict": verdict,
                "command": command,
                "exit_code": int(completed.returncode),
                "verification_method": step_evidence.get("verification_method", ""),
                "failure_reason": step_evidence.get("failure_reason", ""),
                "bootstrap_command": step_evidence.get("bootstrap_command", ""),
                "stdout_log_path": str(stdout_path),
                "stderr_log_path": str(stderr_path),
            }
        write_text(report_path, json.dumps(step_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {
        "step": step_name,
        "command": command,
        "step_report": step_report,
        "step_payload": step_payload,
    }


def run_verification_commands(
    *,
    packet_document: dict[str, Any],
    workspace_root: Path,
    run_dir: Path,
    shell_resolver: ShellResolver | None = None,
    subprocess_run: SubprocessRun | None = None,
    runtime_preflight_starter: RuntimePreflightStarter | None = None,
    runtime_preflight_teardown: RuntimePreflightTeardown | None = None,
) -> dict[str, Any]:
    verification = packet_document.get("verification_commands", {})
    if not isinstance(verification, dict):
        raise ValueError("packet_document missing verification_commands")

    commands = verification.get("commands", {})
    sequence = verification.get("sequence", [])
    reporting = verification.get("reporting", {})
    if not isinstance(commands, dict) or not isinstance(sequence, list):
        raise ValueError("verification_commands must contain commands + sequence")
    if reporting and not isinstance(reporting, dict):
        raise ValueError("verification_commands.reporting must be a mapping when present")

    step_reports: list[dict[str, Any]] = []
    structured_step_payloads: dict[str, dict[str, Any]] = {}
    progress_events: list[dict[str, Any]] = []
    write_verification_progress(run_dir=run_dir, events=progress_events, status="started")
    executed_steps = 0
    executed_step_names: list[str] = []
    failed_steps = 0
    execution_env = runtime_preflight.build_execution_env(workspace_root=workspace_root, run_dir=run_dir)
    step_timeout_seconds = resolve_step_timeout_seconds()
    verification_max_workers = resolve_verification_max_workers()
    verification_execution_mode = "not-run"
    start_runtime_preflight = runtime_preflight_starter or runtime_preflight.ensure_backend_runtime_preflight
    runtime_preflight_report = start_runtime_preflight(
        packet_document=packet_document,
        workspace_root=workspace_root,
        execution_env=execution_env,
        run_dir=run_dir,
    )

    if runtime_preflight_report["required"] and not runtime_preflight_report["ready"]:
        verification_execution_mode = "runtime-preflight"
        executed_steps = 1
        failed_steps = 1
        step_reports.append(
            {
                "step": "runtime-preflight",
                "command": str(runtime_preflight_report["command"]),
                "verdict": "fail",
                "exit_code": 1,
                "duration_ms": 0,
                "started_at_epoch_s": time.time(),
                "stdout_log_path": str(runtime_preflight_report["stdout_log_path"]),
                "stderr_log_path": str(runtime_preflight_report["stderr_log_path"]),
                "verification_method": "runtime-preflight",
                "failure_reason": str(runtime_preflight_report["failure_reason"]),
            }
        )
    else:
        try:
            step_inputs = collect_verification_step_inputs(sequence, commands)
            run_parallel = can_parallelize_verification_steps(step_inputs, verification_max_workers)
            verification_execution_mode = "parallel" if run_parallel else "sequential"
            results_by_step: dict[str, dict[str, Any]] = {}
            if run_parallel:
                write_verification_progress(
                    run_dir=run_dir,
                    events=progress_events,
                    status="running",
                    current_step="parallel",
                )
                with ThreadPoolExecutor(max_workers=min(verification_max_workers, len(step_inputs))) as executor:
                    future_map = {
                        executor.submit(
                            execute_verification_step,
                            step_name=row["step"],
                            command=row["command"],
                            packet_document=packet_document,
                            reporting=reporting,
                            workspace_root=workspace_root,
                            run_dir=run_dir,
                            execution_env=execution_env,
                            step_timeout_seconds=step_timeout_seconds,
                            shell_resolver=shell_resolver,
                            subprocess_run=subprocess_run,
                        ): row["step"]
                        for row in step_inputs
                    }
                    for future in as_completed(future_map):
                        step_name = future_map[future]
                        results_by_step[step_name] = future.result()
                parallel_events: list[dict[str, Any]] = []
                for row in step_inputs:
                    result = results_by_step[row["step"]]
                    step_report = result["step_report"]
                    started_at_epoch = float(step_report["started_at_epoch_s"])
                    finished_at_epoch = float(step_report["finished_at_epoch_s"])
                    parallel_events.append(
                        {
                            "step": row["step"],
                            "status": "started",
                            "at": epoch_to_utc_iso(started_at_epoch),
                            "at_epoch_s": started_at_epoch,
                            "command": row["command"],
                        }
                    )
                    parallel_events.append(
                        {
                            "step": row["step"],
                            "status": "finished",
                            "at": epoch_to_utc_iso(finished_at_epoch),
                            "at_epoch_s": finished_at_epoch,
                            "verdict": step_report["verdict"],
                            "failure_reason": step_report["failure_reason"],
                        }
                    )
                parallel_events.sort(key=lambda event: (float(event.get("at_epoch_s", 0.0)), event["status"] != "started"))
                progress_events.extend(parallel_events)
                write_verification_progress(run_dir=run_dir, events=progress_events, status="running", current_step="")
            else:
                for row in step_inputs:
                    progress_events.append(
                        {
                            "step": row["step"],
                            "status": "started",
                            "at": utc_now_iso(),
                            "command": row["command"],
                        }
                    )
                    write_verification_progress(
                        run_dir=run_dir,
                        events=progress_events,
                        status="running",
                        current_step=row["step"],
                    )
                    result = execute_verification_step(
                        step_name=row["step"],
                        command=row["command"],
                        packet_document=packet_document,
                        reporting=reporting,
                        workspace_root=workspace_root,
                        run_dir=run_dir,
                        execution_env=execution_env,
                        step_timeout_seconds=step_timeout_seconds,
                        shell_resolver=shell_resolver,
                        subprocess_run=subprocess_run,
                    )
                    results_by_step[row["step"]] = result
                    step_report = result["step_report"]
                    progress_events.append(
                        {
                            "step": row["step"],
                            "status": "finished",
                            "at": utc_now_iso(),
                            "verdict": step_report["verdict"],
                            "failure_reason": step_report["failure_reason"],
                        }
                    )
                    write_verification_progress(run_dir=run_dir, events=progress_events, status="running", current_step="")

            for row in step_inputs:
                step_name = row["step"]
                result = results_by_step[step_name]
                step_report = result["step_report"]
                step_reports.append(step_report)
                executed_steps += 1
                executed_step_names.append(step_name)
                if step_report["verdict"] == "fail":
                    failed_steps += 1
                step_payload = result.get("step_payload")
                if isinstance(step_payload, dict):
                    structured_step_payloads[step_name] = step_payload
                    if step_name == CRITICAL_TARGETED_STEP:
                        structured_step_payloads.setdefault(LEGACY_TARGETED_STEP, step_payload)
                    if step_name == FULL_TARGETED_STEP:
                        structured_step_payloads.setdefault(LEGACY_TARGETED_STEP, step_payload)
                        legacy_report_path = run_dir / REPORT_FILENAMES[LEGACY_TARGETED_STEP]
                        if not legacy_report_path.exists():
                            write_text(
                                legacy_report_path,
                                json.dumps(step_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            )
        finally:
            if runtime_preflight_report["started"]:
                stop_runtime_preflight = runtime_preflight_teardown or runtime_preflight.teardown_backend_runtime_preflight
                stop_runtime_preflight(
                    workspace_root=workspace_root,
                    execution_env=execution_env,
                )

    overall_verdict = "pass" if executed_steps > 0 and failed_steps == 0 else "fail"
    backend_evidence = analyze_backend_evidence(
        packet_document=packet_document,
        workspace_root=workspace_root,
        targeted_test_report=(
            structured_step_payloads.get(CRITICAL_TARGETED_STEP)
            or structured_step_payloads.get(LEGACY_TARGETED_STEP)
            or structured_step_payloads.get(FULL_TARGETED_STEP)
        ),
    )
    canonical_targeted_executed = any(
        step in executed_step_names
        for step in (CRITICAL_TARGETED_STEP, LEGACY_TARGETED_STEP, FULL_TARGETED_STEP)
    )
    report = {
        "packet_id": str(packet_document.get("packet_id", "")).strip(),
        "lane": packet_lane(packet_document),
        "work_package_ids": [
            str(item).strip()
            for item in packet_document.get("work_package_ids", [])
            if str(item).strip()
        ],
        "workspace_root": str(workspace_root),
        "run_dir": str(run_dir),
        "overall_verdict": overall_verdict,
        "backend_evidence": backend_evidence,
        "summary": {
            "executed_step_count": executed_steps,
            "failed_step_count": failed_steps,
            "step_duration_ms": build_step_duration_summary(step_reports),
            "verification_execution_mode": verification_execution_mode,
            "verification_max_workers": verification_max_workers,
        },
        "runtime_preflight": runtime_preflight_report,
        "steps": step_reports,
        "unit_test_report_path": str(run_dir / REPORT_FILENAMES["unit-tests"]) if "unit-tests" in executed_step_names else "",
        "test_report_path": str(run_dir / REPORT_FILENAMES[LEGACY_TARGETED_STEP]) if canonical_targeted_executed else "",
        "full_test_report_path": str(run_dir / REPORT_FILENAMES[FULL_TARGETED_STEP]) if FULL_TARGETED_STEP in executed_step_names else "",
        "lint_report_path": str(run_dir / REPORT_FILENAMES["lint"]) if executed_steps else "",
        "typecheck_report_path": str(run_dir / REPORT_FILENAMES["typecheck"]) if executed_steps else "",
        "build_report_path": str(run_dir / REPORT_FILENAMES["build"]) if executed_steps else "",
    }
    report_path = run_dir / "verification-report.json"
    report_md_path = run_dir / "verification-report.md"
    write_json_and_markdown_report(
        json_path=report_path,
        report=report,
        markdown=build_verification_markdown(report),
        markdown_path=report_md_path,
    )
    write_verification_progress(run_dir=run_dir, events=progress_events, status="finished", current_step="")
    return {
        **report,
        "report_path": str(report_path),
        "report_markdown_path": str(report_md_path),
    }
