#!/usr/bin/env python3
"""
Prepare and optionally execute an isolated GEO + PetClinic release-evaluation run.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.output_language import resolve_output_locale


PHASE_SEQUENCE = ("phase1", "phase2", "phase3", "phase4", "closure")
DEFAULT_CASES = ("geo", "petclinic")
DEFAULT_INPUT_ROOT = "release-cases/input-baselines"
DEFAULT_PHASE3_TARGETED_VITEST_BATCH_SIZE = 12
CANONICAL_MAINLINE_LOCALE = "en"
INSTALL_PACK_MANIFEST = "SKILL_INSTALL_PACK_MANIFEST.json"
RELEASE_BUNDLE_MANIFEST = "SKILL_BUNDLE_MANIFEST.json"
PHASE_READY_STATES = {
    "phase2": {"implementation-planning-ready"},
    "phase3": {"delivery-ready"},
    "phase4": {"testing-validation-complete"},
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def reader_preflight(release_root: Path) -> dict[str, Any]:
    """Check reader translation config.  Ask user for credentials if missing."""
    config_path = release_root / "config" / "generated-output-policy.json"
    if not config_path.exists():
        return {"status": "no-config", "skip_reader": True}

    policy = json.loads(config_path.read_text(encoding="utf-8"))
    reader = policy.get("reader_translation", {})
    if not isinstance(reader, dict):
        reader = {}

    api_key_env = reader.get("api_key_env", "OPENAI_API_KEY")
    env_key = os.environ.get(api_key_env, "").strip()
    config_key = str(reader.get("api_key", "")).strip()
    credential = env_key or config_key or ""

    if credential and credential != "__NOT_SET__":
        return {"status": "ready", "skip_reader": False}

    print("\n--- Reader Translation (zh-CN) ---")
    print("No API key found in config or environment.")
    if not sys.stdin.isatty():
        print("Reader translation skipped: no interactive stdin for API key prompt.")
        return {
            "status": "skipped",
            "skip_reader": True,
            "reason": "no-api-key-noninteractive",
        }

    try:
        key = input("Enter API key (or press Enter to skip): ").strip()
    except EOFError:
        print("Reader translation skipped: API key prompt reached EOF.")
        return {
            "status": "skipped",
            "skip_reader": True,
            "reason": "no-api-key-noninteractive",
        }

    if key:
        reader["api_key"] = key
        policy["reader_translation"] = reader
        config_path.write_text(
            json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("Key saved to local config.")
        return {"status": "ready", "skip_reader": False}

    print("Reader translation skipped.")
    return {"status": "skipped", "skip_reader": True}


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return parsed


def normalized_case_count(case_count: int) -> int:
    return max(1, int(case_count))


def resolve_case_workers(requested_case_workers: int | None, *, case_count: int) -> int:
    if requested_case_workers is None:
        return normalized_case_count(case_count)
    return max(1, int(requested_case_workers))


def elapsed_seconds(start_perf: float) -> float:
    return round(time.perf_counter() - start_perf, 3)


def build_case_runtime_env(case_index: int) -> dict[str, str]:
    offset = max(0, int(case_index)) * 100
    return {
        "PHASE3_RUNTIME_SMOKE_API_HOST_PORT": str(3000 + offset),
        "PHASE3_RUNTIME_SMOKE_WEB_HOST_PORT": str(53100 + offset),
        "PHASE3_RUNTIME_SMOKE_POSTGRES_HOST_PORT": str(55432 + offset),
        "PHASE3_RUNTIME_SMOKE_REDIS_HOST_PORT": str(56379 + offset),
    }


def build_phase_verification_env(phase: str, *, case_count: int) -> dict[str, str]:
    phase_key = phase.strip().upper()
    if phase_key not in {"PHASE1", "PHASE2", "PHASE3", "PHASE4", "PHASEX"}:
        return {}
    return {f"{phase_key}_VERIFICATION_MAX_WORKERS": str(normalized_case_count(case_count))}


def build_phase_step_env(
    phase: str,
    *,
    case_index: int,
    case_count: int,
    phase3_targeted_vitest_batch_size: int = DEFAULT_PHASE3_TARGETED_VITEST_BATCH_SIZE,
) -> dict[str, str]:
    env = build_phase_verification_env(phase, case_count=case_count)
    if phase == "phase3":
        env.update(build_case_runtime_env(case_index))
        env["PHASE3_TARGETED_VITEST_BATCH_SIZE"] = str(max(1, int(phase3_targeted_vitest_batch_size)))
    return env


def shell_join(parts: list[str]) -> str:
    try:
        import shlex

        return shlex.join(parts)
    except Exception:
        return " ".join(parts)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def detect_release_manifest(release_root: Path) -> tuple[str, Path]:
    install_pack = release_root / INSTALL_PACK_MANIFEST
    if install_pack.exists():
        return "install-pack", install_pack
    release_bundle = release_root / RELEASE_BUNDLE_MANIFEST
    if release_bundle.exists():
        return "release-bundle", release_bundle
    raise ValueError(
        f"{release_root} is not a built release root; expected {INSTALL_PACK_MANIFEST} or {RELEASE_BUNDLE_MANIFEST}"
    )


def load_release_identity(release_root: Path) -> dict[str, Any]:
    release_type, manifest_path = detect_release_manifest(release_root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "release_type": release_type,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "release_name": str(manifest.get("pack_name") or manifest.get("bundle_name") or release_root.name),
        "source_revision": str(manifest.get("source_revision") or "").strip(),
    }


def copy_release_tree(source_root: Path, target_root: Path) -> None:
    if target_root.exists():
        shutil.rmtree(target_root)

    def ignore_release_root_only(current_dir: str, names: list[str]) -> set[str]:
        ignored = {"__pycache__"}
        ignored.update(name for name in names if name.endswith(".pyc"))
        if Path(current_dir).resolve() == source_root.resolve():
            ignored.add(".git")
        return ignored

    shutil.copytree(
        source_root,
        target_root,
        ignore=ignore_release_root_only,
    )


def prepare_isolated_release_workspace(
    *,
    release_root: Path,
    workspace_root: Path,
    force: bool = False,
) -> dict[str, Any]:
    release_root = release_root.resolve()
    workspace_root = workspace_root.resolve()
    release_identity = load_release_identity(release_root)

    if release_root == workspace_root or is_relative_to(workspace_root, release_root):
        raise ValueError("workspace_root must be outside the source release root")
    if is_relative_to(release_root, workspace_root):
        raise ValueError("source release root must be outside workspace_root")

    if workspace_root.exists() and any(workspace_root.iterdir()) and not force:
        raise ValueError(f"workspace_root already exists and is not empty: {workspace_root}")
    if workspace_root.exists() and force:
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)

    isolated_release_root = workspace_root / "release"
    copy_release_tree(release_root, isolated_release_root)

    isolation_failures: list[str] = []
    if (isolated_release_root / "AGENTS.md").exists():
        isolation_failures.append("repo-level AGENTS.md leaked into isolated release copy")
    if (isolated_release_root / ".git").exists():
        isolation_failures.append("git metadata leaked into isolated release copy")
    if isolation_failures:
        raise ValueError("; ".join(isolation_failures))

    result = {
        "prepared_at": utc_now_iso(),
        "source_release_root": str(release_root),
        "isolated_release_root": str(isolated_release_root),
        "workspace_root": str(workspace_root),
        "release_type": release_identity["release_type"],
        "release_name": release_identity["release_name"],
        "source_revision": release_identity["source_revision"],
        "source_manifest_path": str(release_identity["manifest_path"]),
        "isolated_manifest_path": str(
            isolated_release_root / release_identity["manifest_path"].name
        ),
        "isolation_checks": {
            "agents_absent": not (isolated_release_root / "AGENTS.md").exists(),
            "git_absent": not (isolated_release_root / ".git").exists(),
        },
    }
    manifest_path = workspace_root / "release-eval-workspace.json"
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["workspace_manifest_path"] = str(manifest_path)
    return result


def read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_phase3_runtime_cost_summary(phase3_root: Path) -> dict[str, Any]:
    timing_report = read_json_if_present(phase3_root / ".phase3-diagnostics" / "phase3-timing-report.json")
    backend_run_root = phase3_root / ".phase3-mainline-execution" / "backend-runs" / "run-001"
    verification_report = read_json_if_present(backend_run_root / "verification-report.json")
    full_targeted_report = read_json_if_present(backend_run_root / "full-targeted-tests.vitest.json")
    runtime_smoke_report = read_json_if_present(phase3_root / "runtime-smoke-report.json")

    verification_summary = verification_report.get("summary", {})
    if not isinstance(verification_summary, dict):
        verification_summary = {}
    step_duration = verification_summary.get("step_duration_ms", {})
    if not isinstance(step_duration, dict):
        step_duration = {}
    by_step_duration = step_duration.get("by_step", {})
    if not isinstance(by_step_duration, dict):
        by_step_duration = {}
    longest_step = step_duration.get("longest_step", {})
    if not isinstance(longest_step, dict):
        longest_step = {}

    batch_timing = full_targeted_report.get("phase3_batch_timing", [])
    if not isinstance(batch_timing, list):
        batch_timing = []
    batch_durations = [
        int(batch.get("duration_ms") or 0)
        for batch in batch_timing
        if isinstance(batch, dict)
    ]

    commands = runtime_smoke_report.get("commands", {})
    if not isinstance(commands, dict):
        commands = {}
    command_duration_ms = {
        str(name): int(payload.get("duration_ms") or 0)
        for name, payload in commands.items()
        if isinstance(payload, dict)
    }
    checks = runtime_smoke_report.get("checks", {})
    if not isinstance(checks, dict):
        checks = {}
    selected_host_ports = runtime_smoke_report.get("selected_host_ports", {})
    if not isinstance(selected_host_ports, dict):
        selected_host_ports = {}

    timing_segments = timing_report.get("segments", {})
    if not isinstance(timing_segments, dict):
        timing_segments = {}

    return {
        "timing_segments": timing_segments,
        "verification": {
            "mode": str(verification_summary.get("verification_execution_mode") or "unknown"),
            "max_workers": int(verification_summary.get("verification_max_workers") or 0),
            "by_step_duration_ms": by_step_duration,
            "longest_step": longest_step,
        },
        "full_targeted": {
            "suite_count": int(full_targeted_report.get("numTotalTestSuites") or 0),
            "test_count": int(full_targeted_report.get("numTotalTests") or 0),
            "batch_count": len(batch_durations),
            "total_duration_ms": sum(batch_durations),
            "max_batch_duration_ms": max(batch_durations, default=0),
        },
        "runtime_smoke": {
            "compose_project_name": str(runtime_smoke_report.get("compose_project_name") or ""),
            "selected_host_ports": selected_host_ports,
            "command_duration_ms": command_duration_ms,
            "runtime_smoke_green": bool(checks.get("runtime_smoke_green")),
            "started_service_smoke_green": bool(checks.get("started_service_smoke_green")),
        },
    }


def run_mindthus_bootstrap_if_available(isolated_release_root: Path) -> dict[str, Any]:
    script_path = isolated_release_root / "scripts" / "release" / "bootstrap_mindthus_dependency.py"
    lock_path = isolated_release_root / "runtime-deps" / "mindthus" / "mindthus.lock.json"
    report_path = isolated_release_root / "runtime-deps" / "mindthus" / "bootstrap-report.json"
    command = [sys.executable, str(script_path)]
    if not script_path.exists() or not lock_path.exists():
        return {
            "status": "skipped",
            "reason": "Mindthus bootstrap script or lock file is not present in the release root.",
            "command": command,
            "returncode": None,
            "report_path": str(report_path),
        }

    proc = subprocess.run(command, cwd=isolated_release_root, text=True, capture_output=True, check=False)
    report: dict[str, Any] = {}
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report = {"status": "invalid-report"}

    status = str(report.get("status") or ("ready" if proc.returncode == 0 else "failed"))
    return {
        "status": status,
        "command": command,
        "returncode": proc.returncode,
        "report_path": str(report_path),
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "report": report,
    }


def detect_phase1_prd(phase1_root: Path) -> Path:
    candidates = sorted(
        path
        for path in phase1_root.glob("*main-document.md")
        if "assembled" not in path.name and ".zh-CN." not in path.name
    )
    if not candidates:
        raise FileNotFoundError(f"no Phase-1 main document found under {phase1_root}")
    return candidates[0]


def build_phase_command_plan(
    *,
    isolated_release_root: Path,
    case_name: str,
    case_root: Path,
    source_brief: Path,
    case_index: int = 0,
    case_count: int = len(DEFAULT_CASES),
    version: str,
    owner: str,
    output_locale: str,
    depth_mode: str,
    stop_after: str,
    phase3_mainline_verification_mode: str,
    phase3_install_toolchain: bool,
    phase3_run_runtime_smoke: bool,
    phase3_targeted_vitest_batch_size: int = DEFAULT_PHASE3_TARGETED_VITEST_BATCH_SIZE,
    phase3_module_synthesis_bundle_root: Path | None = None,
) -> list[dict[str, Any]]:
    version_prefix = f"{version}-{case_name}"
    mainline_locale = CANONICAL_MAINLINE_LOCALE
    steps: list[dict[str, Any]] = []

    phase1_root = case_root / "phase-1"
    phase2_root = case_root / "phase-2"
    phase3_root = case_root / "phase-3"
    phase4_root = case_root / "phase-4"
    closure_root = case_root / "closure"

    phase1_command = [
        sys.executable,
        str(isolated_release_root / "scripts" / "phase1" / "run_phase1_full_trial.py"),
        "--source",
        str(source_brief),
        "--output-dir",
        str(phase1_root),
        "--version",
        f"{version_prefix}-p1",
        "--owner",
        owner,
        "--depth-mode",
        depth_mode,
        "--output-locale",
        mainline_locale,
    ]
    rewrite_path = source_brief.parent / "commercial-argument-rewrite.json"
    if rewrite_path.exists():
        phase1_command.extend(["--commercial-argument-rewrite", str(rewrite_path)])
    narrative_rewrite_path = source_brief.parent / "prd-narrative-compression-rewrite.json"
    if narrative_rewrite_path.exists():
        phase1_command.extend(["--narrative-compression-rewrite", str(narrative_rewrite_path)])
    steps.append(
        {
            "phase": "phase1",
            "command": phase1_command,
            "cwd": str(isolated_release_root),
            "output_root": str(phase1_root),
            "env": build_phase_step_env(
                "phase1",
                case_index=case_index,
                case_count=case_count,
                phase3_targeted_vitest_batch_size=phase3_targeted_vitest_batch_size,
            ),
        }
    )

    phase2_command = [
        sys.executable,
        str(isolated_release_root / "scripts" / "phase2" / "run_phase2_first_version.py"),
        "--phase1-prd",
        "__PHASE1_PRD__",
        "--output-dir",
        str(phase2_root),
        "--version",
        f"{version_prefix}-p2",
        "--case-name",
        case_name,
        "--owner",
        owner,
        "--output-locale",
        mainline_locale,
        "--run-wrapper",
    ]
    steps.append(
        {
            "phase": "phase2",
            "command": phase2_command,
            "cwd": str(isolated_release_root),
            "output_root": str(phase2_root),
            "env": build_phase_step_env(
                "phase2",
                case_index=case_index,
                case_count=case_count,
                phase3_targeted_vitest_batch_size=phase3_targeted_vitest_batch_size,
            ),
        }
    )

    phase3_command = [
        sys.executable,
        str(isolated_release_root / "scripts" / "phase3" / "run_phase3_first_version.py"),
        "--phase2-root",
        str(phase2_root),
        "--output-dir",
        str(phase3_root),
        "--version",
        f"{version_prefix}-p3",
        "--output-locale",
        mainline_locale,
        "--mainline-verification-mode",
        phase3_mainline_verification_mode,
    ]
    if phase3_install_toolchain:
        phase3_command.append("--install-toolchain")
    if phase3_run_runtime_smoke:
        phase3_command.append("--run-runtime-smoke")
    if phase3_module_synthesis_bundle_root is not None:
        case_bundle = phase3_module_synthesis_bundle_root / case_name
        if case_bundle.exists():
            phase3_command.extend(["--module-synthesis-bundle", str(case_bundle)])
    steps.append(
        {
            "phase": "phase3",
            "command": phase3_command,
            "cwd": str(isolated_release_root),
            "output_root": str(phase3_root),
            "env": build_phase_step_env(
                "phase3",
                case_index=case_index,
                case_count=case_count,
                phase3_targeted_vitest_batch_size=phase3_targeted_vitest_batch_size,
            ),
        }
    )

    phase4_command = [
        sys.executable,
        str(isolated_release_root / "scripts" / "phase4" / "run_phase4_first_version.py"),
        "--phase3-root",
        str(phase3_root),
        "--output-dir",
        str(phase4_root),
        "--version",
        f"{version_prefix}-p4",
        "--output-locale",
        mainline_locale,
    ]
    steps.append(
        {
            "phase": "phase4",
            "command": phase4_command,
            "cwd": str(isolated_release_root),
            "output_root": str(phase4_root),
            "env": build_phase_step_env(
                "phase4",
                case_index=case_index,
                case_count=case_count,
                phase3_targeted_vitest_batch_size=phase3_targeted_vitest_batch_size,
            ),
        }
    )

    closure_command = [
        sys.executable,
        str(isolated_release_root / "scripts" / "phase4" / "run_p1_p4_mainline_closure.py"),
        "--phase1-root",
        str(phase1_root),
        "--phase2-root",
        str(phase2_root),
        "--phase3-root",
        str(phase3_root),
        "--phase4-root",
        str(phase4_root),
        "--output-dir",
        str(closure_root),
        "--case-name",
        case_name,
        "--version",
        version_prefix,
        "--closure-mode",
        "runtime-closure",
    ]
    steps.append(
        {
            "phase": "closure",
            "command": closure_command,
            "cwd": str(isolated_release_root),
            "output_root": str(closure_root),
        }
    )

    max_index = PHASE_SEQUENCE.index(stop_after)
    return [step for step in steps if PHASE_SEQUENCE.index(step["phase"]) <= max_index]


def write_command_plan(
    *,
    workspace_root: Path,
    plan: dict[str, Any],
) -> tuple[Path, Path]:
    json_path = workspace_root / "release-dual-case-command-plan.json"
    md_path = workspace_root / "release-dual-case-command-plan.md"
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Release Dual-Case Command Plan",
        "",
        f"- workspace_root: `{workspace_root}`",
        f"- isolated_release_root: `{plan['isolated_release_root']}`",
        f"- stop_after: `{plan['stop_after']}`",
        f"- case_workers: `{plan.get('case_workers', 1)}`",
        "",
    ]
    for case in plan["cases"]:
        lines.append(f"## {case['case_name']}")
        lines.append(f"- source_brief: `{case['source_brief']}`")
        for step in case["steps"]:
            lines.append(f"- {step['phase']}:")
            lines.append(f"  - cwd: `{step['cwd']}`")
            lines.append(f"  - output_root: `{step['output_root']}`")
            lines.append(f"  - command: `{shell_join(step['command'])}`")
        lines.append("")
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, md_path


def run_step(
    command: list[str],
    *,
    cwd: Path,
    log_path: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        env.update({str(key): str(value) for key, value in extra_env.items()})
    proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, env=env)
    log_lines = [
        f"$ {shell_join(command)}",
        "",
        proc.stdout,
    ]
    if proc.stderr:
        log_lines.extend(["", "[stderr]", proc.stderr])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(log_lines).rstrip() + "\n", encoding="utf-8")
    return proc


def read_step_phase_verdict(step: dict[str, Any]) -> dict[str, Any]:
    output_root = Path(str(step.get("output_root") or ""))
    verdict_path = output_root / "phase-verdict.json"
    result = {
        "phase_verdict_path": str(verdict_path),
        "phase_verdict_present": verdict_path.exists(),
        "phase_verdict": "",
        "recommended_formal_state": "",
    }
    if not verdict_path.exists():
        return result
    try:
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result["phase_verdict_error"] = f"invalid-json: {exc}"
        return result
    if not isinstance(verdict, dict):
        result["phase_verdict_error"] = "phase verdict is not a JSON object"
        return result
    result["phase_verdict"] = str(verdict.get("verdict") or "").strip()
    result["recommended_formal_state"] = str(verdict.get("recommended_formal_state") or "").strip()
    if not result["recommended_formal_state"] and str(step.get("phase") or "").strip() == "phase4":
        delivery_gate = read_json_if_present(output_root / "phase4-delivery-gate.json")
        result["recommended_formal_state"] = str(delivery_gate.get("recommended_formal_state") or "").strip()
    return result


def step_phase_verdict_failure_reason(step_result: dict[str, Any]) -> str:
    phase = str(step_result.get("phase") or "").strip()
    expected_states = PHASE_READY_STATES.get(phase)
    if not expected_states:
        return ""
    verdict = str(step_result.get("phase_verdict") or "").strip()
    recommended_state = str(step_result.get("recommended_formal_state") or "").strip()
    if verdict != "PASS":
        return f"{phase} phase verdict is not PASS: {verdict or 'missing'}"
    if recommended_state not in expected_states:
        expected = ", ".join(sorted(expected_states))
        return f"{phase} recommended_formal_state is not ready: {recommended_state or 'missing'}; expected {expected}"
    return ""


def execute_case_plan(case_plan: dict[str, Any]) -> dict[str, Any]:
    case_started_perf = time.perf_counter()
    case_result = {
        "case_name": case_plan["case_name"],
        "case_root": case_plan["case_root"],
        "source_brief": case_plan["source_brief"],
        "steps": [],
        "overall_status": "prepared",
        "stopped_after": "",
        "started_at": utc_now_iso(),
        "finished_at": "",
        "duration_seconds": 0.0,
    }

    phase1_prd_path = ""
    for step in case_plan["steps"]:
        command = list(step["command"])
        if step["phase"] == "phase2":
            if not phase1_prd_path:
                phase1_prd_path = str(detect_phase1_prd(Path(case_plan["case_root"]) / "phase-1"))
            command = [phase1_prd_path if item == "__PHASE1_PRD__" else item for item in command]

        log_path = Path(case_plan["case_root"]) / "_logs" / f"{step['phase']}.log"
        step_started_perf = time.perf_counter()
        step_started_at = utc_now_iso()
        proc = run_step(command, cwd=Path(step["cwd"]), log_path=log_path, extra_env=step.get("env"))
        step_finished_at = utc_now_iso()
        step_result = {
            "phase": step["phase"],
            "command": command,
            "cwd": step["cwd"],
            "output_root": step["output_root"],
            "log_path": str(log_path),
            "returncode": proc.returncode,
            "status": "pass" if proc.returncode == 0 else "fail",
            "started_at": step_started_at,
            "finished_at": step_finished_at,
            "duration_seconds": elapsed_seconds(step_started_perf),
            "env": dict(step.get("env") or {}),
        }
        phase_verdict_result = read_step_phase_verdict(step)
        if phase_verdict_result["phase_verdict_present"]:
            step_result.update(phase_verdict_result)
        if step["phase"] == "phase3":
            step_result["runtime_cost_summary"] = read_phase3_runtime_cost_summary(Path(step["output_root"]))
        if proc.returncode == 0:
            phase_failure_reason = step_phase_verdict_failure_reason(step_result)
            if phase_failure_reason:
                step_result["status"] = "fail"
                step_result["failure_reason"] = phase_failure_reason
        case_result["steps"].append(step_result)
        case_result["stopped_after"] = step["phase"]
        if step_result["status"] != "pass":
            case_result["overall_status"] = "failed"
            case_result["finished_at"] = utc_now_iso()
            case_result["duration_seconds"] = elapsed_seconds(case_started_perf)
            return case_result

    case_result["overall_status"] = "completed"
    case_result["finished_at"] = utc_now_iso()
    case_result["duration_seconds"] = elapsed_seconds(case_started_perf)
    return case_result


def build_case_exception_result(case_plan: dict[str, Any], exc: BaseException) -> dict[str, Any]:
    return {
        "case_name": case_plan.get("case_name", "unknown"),
        "source_brief": case_plan.get("source_brief", ""),
        "steps": [],
        "overall_status": "failed",
        "stopped_after": "",
        "started_at": utc_now_iso(),
        "finished_at": utc_now_iso(),
        "duration_seconds": 0.0,
        "error_type": exc.__class__.__name__,
        "error": str(exc),
    }


def execute_case_plan_safely(case_plan: dict[str, Any]) -> dict[str, Any]:
    try:
        return execute_case_plan(case_plan)
    except Exception as exc:
        return build_case_exception_result(case_plan, exc)


def execute_case_plans(case_plans: list[dict[str, Any]], *, case_workers: int) -> list[dict[str, Any]]:
    if not case_plans:
        return []

    worker_count = min(max(1, case_workers), len(case_plans))
    if worker_count == 1:
        return [execute_case_plan_safely(case_plan) for case_plan in case_plans]

    results: list[dict[str, Any] | None] = [None] * len(case_plans)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(execute_case_plan_safely, case_plan): index
            for index, case_plan in enumerate(case_plans)
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    return [result for result in results if result is not None]


def derive_overall_verdict(case_results: list[dict[str, Any]]) -> str:
    if not case_results:
        return "fail"
    for case in case_results:
        if case.get("overall_status") != "completed":
            return "fail"
        for step in case.get("steps", []):
            if isinstance(step, dict) and step.get("status") == "fail":
                return "fail"
    return "pass"


def numeric_duration(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return round(parsed, 3)


def build_execution_timing_breakdown(summary: dict[str, Any]) -> dict[str, Any]:
    total_duration = numeric_duration(summary.get("duration_seconds")) or 0.0
    case_durations: list[float] = []
    phase_durations: dict[str, list[float]] = {}
    longest_steps: list[dict[str, Any]] = []

    for case in summary.get("cases", []):
        if not isinstance(case, dict):
            continue
        case_duration = numeric_duration(case.get("duration_seconds"))
        if case_duration is not None:
            case_durations.append(case_duration)
        case_name = str(case.get("case_name") or "unknown")
        for step in case.get("steps", []):
            if not isinstance(step, dict):
                continue
            duration = numeric_duration(step.get("duration_seconds"))
            phase = str(step.get("phase") or "").strip()
            if duration is None or not phase:
                continue
            phase_durations.setdefault(phase, []).append(duration)
            longest_steps.append(
                {
                    "case_name": case_name,
                    "phase": phase,
                    "status": step.get("status", ""),
                    "duration_seconds": duration,
                    "log_path": step.get("log_path", ""),
                }
            )

    longest_case_duration = max(case_durations, default=0.0)
    case_duration_sum = round(sum(case_durations), 3)
    phase_duration_seconds = {
        phase: {
            "sum": round(sum(values), 3),
            "max": round(max(values), 3),
            "count": len(values),
        }
        for phase, values in sorted(phase_durations.items())
    }
    longest_steps.sort(key=lambda row: float(row["duration_seconds"]), reverse=True)

    return {
        "total_duration_seconds": total_duration,
        "longest_case_duration_seconds": longest_case_duration,
        "case_duration_sum_seconds": case_duration_sum,
        "orchestration_overhead_vs_longest_case_seconds": round(
            max(0.0, total_duration - longest_case_duration),
            3,
        ),
        "phase_duration_seconds": phase_duration_seconds,
        "longest_steps": longest_steps[:8],
    }


def build_performance_profile(summary: dict[str, Any]) -> dict[str, Any]:
    cases = [case for case in summary.get("cases", []) if isinstance(case, dict)]
    try:
        case_workers = int(summary.get("case_workers") or 1)
    except (TypeError, ValueError):
        case_workers = 1
    warnings: list[str] = []
    if len(cases) > 1 and case_workers == 1:
        warnings.append(
            "multi-case run used case_workers=1; this is a serial diagnostic profile, "
            "not the F.9 strict-performance proof profile"
        )
        case_parallelism = "serial-diagnostic"
    elif len(cases) > 1:
        case_parallelism = "parallel"
    else:
        case_parallelism = "single-case"
    return {
        "case_parallelism": case_parallelism,
        "case_count": len(cases),
        "case_workers": case_workers,
        "warnings": warnings,
    }


def write_execution_summary(
    *,
    workspace_root: Path,
    summary: dict[str, Any],
) -> tuple[Path, Path]:
    summary["timing_breakdown"] = build_execution_timing_breakdown(summary)
    summary["performance_profile"] = build_performance_profile(summary)
    json_path = workspace_root / "release-dual-case-eval-summary.json"
    md_path = workspace_root / "release-dual-case-eval-summary.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    timing_breakdown = summary["timing_breakdown"]
    lines = [
        "# Release Dual-Case Evaluation Summary",
        "",
        f"- prepared_at: `{summary['prepared_at']}`",
        f"- started_at: `{summary.get('started_at', '')}`",
        f"- finished_at: `{summary.get('finished_at', '')}`",
        f"- duration_seconds: `{summary.get('duration_seconds', 'unknown')}`",
        f"- release_name: `{summary['release_name']}`",
        f"- release_type: `{summary['release_type']}`",
        f"- source_revision: `{summary['source_revision'] or 'unknown'}`",
        f"- stop_after: `{summary['stop_after']}`",
        f"- case_workers: `{summary.get('case_workers', 1)}`",
        f"- performance_profile: `{summary['performance_profile']['case_parallelism']}`",
        f"- overall_verdict: `{summary['overall_verdict']}`",
        "",
        "## Timing Breakdown",
        f"- total_duration_seconds: `{timing_breakdown['total_duration_seconds']}`",
        f"- longest_case_duration_seconds: `{timing_breakdown['longest_case_duration_seconds']}`",
        f"- case_duration_sum_seconds: `{timing_breakdown['case_duration_sum_seconds']}`",
        f"- orchestration_overhead_vs_longest_case_seconds: `{timing_breakdown['orchestration_overhead_vs_longest_case_seconds']}`",
        "",
        "### Phase Durations",
    ]
    phase_duration_seconds = timing_breakdown.get("phase_duration_seconds", {})
    if phase_duration_seconds:
        for phase, row in phase_duration_seconds.items():
            lines.append(
                f"- {phase}: sum=`{row['sum']}` max=`{row['max']}` count=`{row['count']}`"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "### Longest Steps",
        ]
    )
    longest_steps = timing_breakdown.get("longest_steps", [])
    if longest_steps:
        for step in longest_steps:
            lines.append(
                f"- {step['case_name']} {step['phase']}: `{step['duration_seconds']}` status=`{step['status']}` log=`{step['log_path']}`"
            )
    else:
        lines.append("- none")
    warnings = summary["performance_profile"].get("warnings", [])
    if warnings:
        lines.extend(["", "### Performance Warnings"])
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append("")
    for case in summary["cases"]:
        lines.append(f"## {case['case_name']}")
        lines.append(f"- overall_status: `{case['overall_status']}`")
        lines.append(f"- stopped_after: `{case['stopped_after'] or '(none)'}`")
        if case.get("duration_seconds") is not None:
            lines.append(f"- duration_seconds: `{case['duration_seconds']}`")
        if case.get("error"):
            lines.append(f"- error: `{case['error_type']}: {case['error']}`")
        lines.append(f"- source_brief: `{case['source_brief']}`")
        for step in case["steps"]:
            lines.append(
                f"- {step['phase']}: `{step['status']}` (`returncode={step['returncode']}`, duration_seconds={step.get('duration_seconds', 'unknown')}) log=`{step['log_path']}`"
            )
        lines.append("")
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, md_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and optionally execute an isolated Release SKILLS GEO + PetClinic dual-case evaluation"
    )
    parser.add_argument(
        "--release-root",
        default=".",
        help="Path to a built install-pack or release-bundle root. Defaults to current directory.",
    )
    parser.add_argument("--workspace-root", required=True, help="Isolated evaluation workspace root.")
    parser.add_argument(
        "--case-input-root",
        default=DEFAULT_INPUT_ROOT,
        help="Relative case-input root inside the release root.",
    )
    parser.add_argument("--cases", nargs="+", default=list(DEFAULT_CASES))
    parser.add_argument(
        "--case-workers",
        type=positive_int,
        default=None,
        help="Number of case pipelines to execute concurrently. Defaults to the requested case count. Use 1 to preserve sequential execution.",
    )
    parser.add_argument("--version", default="release-eval")
    parser.add_argument("--owner", default="release-eval")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    parser.add_argument("--depth-mode", choices=("baseline", "creative"), default="baseline")
    parser.add_argument("--stop-after", choices=PHASE_SEQUENCE, default="closure")
    parser.add_argument(
        "--phase3-mainline-verification-mode",
        choices=("disabled", "if-ready", "strict-runtime"),
        default="strict-runtime",
    )
    parser.add_argument(
        "--phase3-install-toolchain",
        dest="phase3_install_toolchain",
        action="store_true",
        default=True,
        help="attempt Phase-3 toolchain install during release proof evaluation; enabled by default",
    )
    parser.add_argument(
        "--phase3-skip-toolchain-install",
        dest="phase3_install_toolchain",
        action="store_false",
        help="diagnostic downgrade: skip Phase-3 toolchain install",
    )
    parser.add_argument(
        "--phase3-run-runtime-smoke",
        dest="phase3_run_runtime_smoke",
        action="store_true",
        default=True,
        help="run Phase-3 runtime smoke during release proof evaluation; enabled by default",
    )
    parser.add_argument(
        "--phase3-skip-runtime-smoke",
        dest="phase3_run_runtime_smoke",
        action="store_false",
        help="diagnostic downgrade: skip Phase-3 runtime smoke",
    )
    parser.add_argument(
        "--phase3-targeted-vitest-batch-size",
        type=positive_int,
        default=DEFAULT_PHASE3_TARGETED_VITEST_BATCH_SIZE,
        help=(
            "Number of full-targeted Vitest targets per Phase-3 batch. "
            "Defaults to 12 for release strict-runtime performance; use 4 as the conservative rollback value."
        ),
    )
    parser.add_argument(
        "--phase3-module-synthesis-bundle-root",
        default="",
        help="optional root containing per-case phase3 module synthesis bundles named by case",
    )
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    run_started_perf = time.perf_counter()
    run_started_at = utc_now_iso()
    args = build_parser().parse_args()
    release_root = Path(args.release_root).resolve()
    workspace_root = Path(args.workspace_root).resolve()
    case_workers = resolve_case_workers(args.case_workers, case_count=len(args.cases))

    workspace = prepare_isolated_release_workspace(
        release_root=release_root,
        workspace_root=workspace_root,
        force=args.force,
    )
    isolated_release_root = Path(workspace["isolated_release_root"])
    mindthus_bootstrap = run_mindthus_bootstrap_if_available(isolated_release_root)
    if mindthus_bootstrap["status"] not in {"ready", "skipped"}:
        raise RuntimeError(
            "Mindthus bootstrap failed before release evaluation: "
            + json.dumps(mindthus_bootstrap, ensure_ascii=False)
        )
    reader_lane = reader_preflight(isolated_release_root)

    case_input_root = isolated_release_root / args.case_input_root

    cases: list[dict[str, Any]] = []
    for case_index, case_name in enumerate(args.cases):
        source_brief = case_input_root / f"{case_name}-source-brief.md"
        if not source_brief.exists():
            raise FileNotFoundError(f"missing source brief for case '{case_name}': {source_brief}")
        case_root = workspace_root / "runs" / case_name
        case_root.mkdir(parents=True, exist_ok=True)
        steps = build_phase_command_plan(
            isolated_release_root=isolated_release_root,
            case_name=case_name,
            case_root=case_root,
            source_brief=source_brief,
            case_index=case_index,
            case_count=case_workers,
            version=args.version,
            owner=args.owner,
            output_locale=args.output_locale,
            depth_mode=args.depth_mode,
            stop_after=args.stop_after,
            phase3_mainline_verification_mode=args.phase3_mainline_verification_mode,
            phase3_install_toolchain=args.phase3_install_toolchain,
            phase3_run_runtime_smoke=args.phase3_run_runtime_smoke,
            phase3_targeted_vitest_batch_size=args.phase3_targeted_vitest_batch_size,
            phase3_module_synthesis_bundle_root=(
                Path(args.phase3_module_synthesis_bundle_root).resolve()
                if str(args.phase3_module_synthesis_bundle_root).strip()
                else None
            ),
        )
        cases.append(
            {
                "case_name": case_name,
                "case_root": str(case_root),
                "source_brief": str(source_brief),
                "steps": steps,
            }
        )

    plan = {
        "prepared_at": workspace["prepared_at"],
        "release_name": workspace["release_name"],
        "release_type": workspace["release_type"],
        "source_revision": workspace["source_revision"],
        "mindthus_bootstrap": mindthus_bootstrap,
        "isolated_release_root": workspace["isolated_release_root"],
        "workspace_root": workspace["workspace_root"],
        "stop_after": args.stop_after,
        "case_workers": case_workers,
        "reader_lane": reader_lane,
        "cases": cases,
    }
    plan_json, plan_md = write_command_plan(workspace_root=workspace_root, plan=plan)

    if args.prepare_only:
        summary = {
            "prepared_at": workspace["prepared_at"],
            "started_at": run_started_at,
            "finished_at": utc_now_iso(),
            "duration_seconds": elapsed_seconds(run_started_perf),
            "release_name": workspace["release_name"],
            "release_type": workspace["release_type"],
            "source_revision": workspace["source_revision"],
            "mindthus_bootstrap": mindthus_bootstrap,
            "stop_after": args.stop_after,
            "case_workers": case_workers,
            "overall_verdict": "prepared",
            "cases": [
                {
                    "case_name": case["case_name"],
                    "overall_status": "prepared",
                    "stopped_after": "",
                    "source_brief": case["source_brief"],
                    "steps": [],
                    "started_at": "",
                    "finished_at": "",
                    "duration_seconds": None,
                }
                for case in cases
            ],
            "command_plan_json": str(plan_json),
            "command_plan_markdown": str(plan_md),
        }
        summary_json, summary_md = write_execution_summary(workspace_root=workspace_root, summary=summary)
        print(
            json.dumps(
                {
                    "workspace_root": str(workspace_root),
                    "isolated_release_root": str(isolated_release_root),
                    "overall_verdict": summary["overall_verdict"],
                    "case_workers": case_workers,
                    "duration_seconds": summary["duration_seconds"],
                    "command_plan_json": str(plan_json),
                    "command_plan_markdown": str(plan_md),
                    "summary_json": str(summary_json),
                    "summary_markdown": str(summary_md),
                },
                ensure_ascii=False,
            )
        )
        return 0

    case_results = execute_case_plans(cases, case_workers=case_workers)

    # Non-blocking reader translation lane (background)
    reader_manifests: dict[str, dict[str, Any]] = {}
    if not reader_lane.get("skip_reader", True):
        lane_script = isolated_release_root / "scripts" / "release" / "run_reader_translation_lane.py"
        for cr in case_results:
            if cr.get("overall_status") != "completed":
                continue
            case_root = Path(cr.get("case_root", ""))
            if not case_root.exists():
                continue
            log_path = case_root / "_logs" / "reader-translation-lane.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_fh = open(log_path, "wb")
            proc = subprocess.Popen(
                [sys.executable, str(lane_script), "--case-root", str(case_root)],
                stdout=log_fh, stderr=subprocess.STDOUT,
                cwd=str(isolated_release_root),
                start_new_session=True,
            )
            log_fh.close()
            reader_manifests[cr["case_name"]] = {
                "status": "launched",
                "pid": proc.pid,
                "log_path": str(log_path),
            }
            cr["reader_manifest"] = reader_manifests[cr["case_name"]]

    overall_verdict = derive_overall_verdict(case_results)
    summary = {
        "prepared_at": workspace["prepared_at"],
        "started_at": run_started_at,
        "finished_at": utc_now_iso(),
        "duration_seconds": elapsed_seconds(run_started_perf),
        "release_name": workspace["release_name"],
        "release_type": workspace["release_type"],
        "source_revision": workspace["source_revision"],
        "mindthus_bootstrap": mindthus_bootstrap,
        "stop_after": args.stop_after,
        "case_workers": case_workers,
        "overall_verdict": overall_verdict,
        "reader_lane": reader_lane,
        "reader_manifests": reader_manifests,
        "cases": case_results,
        "command_plan_json": str(plan_json),
        "command_plan_markdown": str(plan_md),
    }
    summary_json, summary_md = write_execution_summary(workspace_root=workspace_root, summary=summary)
    print(
        json.dumps(
            {
                "workspace_root": str(workspace_root),
                "isolated_release_root": str(isolated_release_root),
                "overall_verdict": overall_verdict,
                "case_workers": case_workers,
                "duration_seconds": summary["duration_seconds"],
                "summary_json": str(summary_json),
                "summary_markdown": str(summary_md),
            },
            ensure_ascii=False,
        )
    )
    return 0 if overall_verdict == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
