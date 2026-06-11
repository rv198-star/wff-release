#!/usr/bin/env python3
"""
Materialize and optionally simulate execution for one Phase-3 worker packet.
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
import re
import shlex
import subprocess
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from datetime import datetime, timezone

from common.host_port_allocator import choose_available_host_port, host_port_in_use
from common.output_language import (
    localize_phase3_dispatch_manifest,
    localize_phase3_execution_runtime_state,
    localize_phase3_packet_run_report,
    localize_phase3_runtime_cycle_summary,
    localize_phase3_verification_report,
    localize_phase3_verification_ledger,
    localize_phase3_worker_packet_runbook,
    localize_phase3_worker_run_report,
)


RUN_MODES = {
    "plan-only": [],
    "simulate-started": ["started"],
    "simulate-success": ["started", "implemented"],
    "simulate-blocked": ["started", "blocked"],
    "simulate-failed": ["started", "failed"],
    "execute-verification": ["started"],
    "execute-and-apply-gate": ["started"],
}

VALID_WORKER_RUN_STATUSES = {"started", "implemented", "blocked", "failed"}
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
RUNTIME_PREFLIGHT_PORT_RETRY_LIMIT = 5
DEFAULT_VERIFICATION_MAX_WORKERS = 2
MAX_VERIFICATION_MAX_WORKERS = 4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def epoch_to_utc_iso(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

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

PLACEHOLDER_COMMAND_PATTERNS = (
    re.compile(r"^\s*echo\b", re.IGNORECASE),
    re.compile(r"^\s*/bin/(?:sh|zsh)\s+-c\s+['\"]\s*echo\b", re.IGNORECASE),
)

FAKE_RUNTIME_MARKERS = (
    "invokeOperation(",
    "resetGeneratedRuntime(",
    "runtime-test-kit",
    "generated-runtime",
    "generatedRuntime",
    "invoke_operation(",
)

SERVICE_TRANSPORT_PATTERNS = (
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\baxios\b"),
    re.compile(r"\bundici\b"),
    re.compile(r"\bsupertest\s*\("),
    re.compile(r"\brequest\s*\("),
    re.compile(r"\bcurl\s+"),
    re.compile(r"\bgrpc\b", re.IGNORECASE),
    re.compile(r"\bgraphql-request\b"),
    re.compile(r"\binvokeHttpOperation\s*\("),
)

SERVICE_TARGET_PATTERNS = (
    re.compile(r"https?://"),
    re.compile(r"\b(?:API|SERVICE|TEST)_BASE_URL\b"),
    re.compile(r"\b(?:API|SERVICE)_HOST\b"),
    re.compile(r"\bPORT\b"),
    re.compile(r"/healthz\b"),
    re.compile(r"/readyz\b"),
)

SERVICE_STARTUP_PATTERNS = (
    re.compile(r"\bspawn\s*\("),
    re.compile(r"\bexeca\s*\("),
    re.compile(r"\bexecFile\s*\("),
    re.compile(r"\bdocker compose\b"),
    re.compile(r"\bdocker-compose\b"),
    re.compile(r"\b(?:app|server)\.listen\s*\("),
    re.compile(r"\bstartServer\s*\("),
    re.compile(r"\blaunchServer\s*\("),
    re.compile(r"\bwaitFor(?:Health|Ready)\b"),
    re.compile(r"\bstartBackendRuntime\s*\("),
)

MIGRATION_PATTERNS = (
    re.compile(r"\brunMigrations\s*\("),
    re.compile(r"\binitializeDatabase\s*\("),
    re.compile(r"\brestoreScenario\s*\("),
    re.compile(r"\bapplyMigrations\s*\("),
    re.compile(r"\bresetDatabase\s*\("),
    re.compile(r"\bpnpm\s+(?:--filter\s+\S+\s+)?migrate\b"),
    re.compile(r"\bprisma migrate\b"),
    re.compile(r"\bdbmate\b"),
    re.compile(r"\bnode-pg-migrate\b"),
    re.compile(r"\bmigration\b", re.IGNORECASE),
)

SQL_QUERY_PATTERNS = (
    re.compile(r"\bDATABASE_URL\b"),
    re.compile(r"\bpg\b"),
    re.compile(r"\bpostgres(?:ql)?\b", re.IGNORECASE),
    re.compile(r"\.query\s*\("),
    re.compile(r"\bcollectPersistenceRoundTripEvidence\s*\("),
    re.compile(r"\bSELECT\b"),
    re.compile(r"\bINSERT\s+INTO\b"),
    re.compile(r"\bUPDATE\b"),
    re.compile(r"\bDELETE\s+FROM\b"),
    re.compile(r"\bqueryTableColumns\s*\("),
    re.compile(r"\bqueryTableIndexes\s*\("),
)

PERSISTENCE_PATH_HINTS = ("tests/sql/", "tests/persistence/", "tests/integration/", "tests/db/", "tests/database/")
SCHEMA_ONLY_PATH_HINTS = ("tests/schema/", ".schema.test.")
DB_SURFACE_MARKERS = (
    "database",
    "migrate",
    "migration",
    "postgres",
    "prisma",
    "drizzle",
    "typeorm",
    "sequelize",
    "repository",
    "/db/",
)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def packet_slug(packet_id: str) -> str:
    return packet_id.replace(":", "-")


def packet_id(*, wave: int | None = None, lane: str | None = None, packet: str | None = None) -> str:
    if packet:
        return packet.strip()
    if wave is None or lane is None or not str(lane).strip():
        raise ValueError("packet or wave+lane is required")
    return f"wave-{int(wave):02d}:{str(lane).strip()}"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "step"


def flatten_packet_tests(packet_document: dict[str, Any], categories: tuple[str, ...]) -> list[str]:
    test_targets = packet_document.get("test_targets", {})
    if not isinstance(test_targets, dict):
        return []
    flattened: list[str] = []
    for key in categories:
        for item in test_targets.get(key, []):
            normalized = str(item).strip()
            if normalized:
                flattened.append(normalized)
    return sorted(set(flattened))


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


def normalize_test_target(value: str, *, workspace_root: Path) -> str:
    normalized = str(value).strip()
    if not normalized:
        return ""
    workspace_root_resolved = workspace_root.resolve()
    candidate = Path(normalized)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        try:
            return str(resolved.relative_to(workspace_root_resolved)).replace("\\", "/")
        except ValueError:
            return str(resolved).replace("\\", "/")
    return str(candidate).replace("\\", "/")


def looks_like_placeholder_command(command: str) -> bool:
    normalized = command.strip()
    if not normalized:
        return True
    return any(pattern.match(normalized) for pattern in PLACEHOLDER_COMMAND_PATTERNS)


def requires_toolchain_bootstrap(command: str) -> bool:
    normalized = command.strip()
    return (
        "pnpm " in normalized
        or normalized.startswith("pnpm")
        or "run_vitest_targets_sequentially.py" in normalized
    )


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


def path_text_if_exists(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def packet_lane(packet_document: dict[str, Any]) -> str:
    lane = str(packet_document.get("lane", "")).strip().lower()
    if lane:
        return lane
    packet_id_value = str(packet_document.get("packet_id", "")).strip().lower()
    if ":" in packet_id_value:
        return packet_id_value.rsplit(":", 1)[-1]
    return ""


def regex_matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def text_contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def workspace_requires_persistence_truth(*, packet_document: dict[str, Any], workspace_root: Path) -> bool:
    packet_targets = [
        str(item).strip().lower()
        for item in [
            *packet_document.get("implementation_targets", []),
            *packet_document.get("work_package_ids", []),
        ]
        if str(item).strip()
    ]
    packet_tests = [
        str(item).strip().lower()
        for item in flatten_packet_tests(packet_document, ("contract", "scenario", "replay", "unit"))
        if str(item).strip()
    ]
    commands = packet_document.get("verification_commands", {})
    command_values = []
    if isinstance(commands, dict):
        command_rows = commands.get("commands", {})
        if isinstance(command_rows, dict):
            command_values = [str(value).strip().lower() for value in command_rows.values() if str(value).strip()]

    if any(any(marker in target for marker in DB_SURFACE_MARKERS) for target in [*packet_targets, *packet_tests, *command_values]):
        return True

    db_artifact_candidates = (
        workspace_root / "apps" / "api" / "src" / "runtime" / "database.ts",
        workspace_root / "apps" / "api" / "src" / "runtime" / "migrate.ts",
        workspace_root / "db",
        workspace_root / "prisma",
        workspace_root / "migrations",
    )
    return any(candidate.exists() for candidate in db_artifact_candidates)


def analyze_backend_test_file(test_path: str, *, workspace_root: Path) -> dict[str, Any]:
    normalized_path = normalize_test_target(test_path, workspace_root=workspace_root)
    content = path_text_if_exists(workspace_root / normalized_path)
    lowered_path = normalized_path.lower()
    lowered_content = content.lower()
    fake_runtime = text_contains_any(content, FAKE_RUNTIME_MARKERS)
    transport_client = regex_matches_any(content, SERVICE_TRANSPORT_PATTERNS)
    transport_target = regex_matches_any(content, SERVICE_TARGET_PATTERNS)
    startup_signal = regex_matches_any(content, SERVICE_STARTUP_PATTERNS)
    migration_signal = regex_matches_any(content, MIGRATION_PATTERNS)
    sql_signal = regex_matches_any(content, SQL_QUERY_PATTERNS)
    persistence_path = any(hint in lowered_path for hint in PERSISTENCE_PATH_HINTS)
    schema_only = any(hint in lowered_path for hint in SCHEMA_ONLY_PATH_HINTS)
    harness_database_reset_signal = (
        content
        and "startBackendRuntime(" in content
        and any(token in content for token in ("initializeDatabase(", "restoreScenario(", "resetDatabase("))
    )
    service_boundary_truth = bool(
        content
        and not fake_runtime
        and transport_client
        and (transport_target or startup_signal)
    )
    sql_persistence_truth = bool(
        content
        and not fake_runtime
        and not schema_only
        and sql_signal
        and (persistence_path or migration_signal or "database_url" in lowered_content or ".query(" in lowered_content)
    )
    service_persistence_roundtrip_truth = bool(
        content
        and not fake_runtime
        and service_boundary_truth
        and sql_signal
    )
    migration_execution_truth = bool(
        content
        and not fake_runtime
        and migration_signal
        and (
            persistence_path
            or harness_database_reset_signal
            or "database_url" in lowered_content
            or "migrate" in lowered_path
        )
    )
    return {
        "test_path": normalized_path,
        "file_present": bool(content),
        "fake_runtime_detected": fake_runtime,
        "service_boundary_truth": service_boundary_truth,
        "sql_persistence_truth": sql_persistence_truth,
        "service_persistence_roundtrip_truth": service_persistence_roundtrip_truth,
        "migration_execution_truth": migration_execution_truth,
    }


def analyze_backend_evidence(
    *,
    packet_document: dict[str, Any],
    workspace_root: Path,
    targeted_test_report: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if packet_lane(packet_document) != "backend":
        return None

    requires_persistence_truth = workspace_requires_persistence_truth(
        packet_document=packet_document,
        workspace_root=workspace_root,
    )
    passed_targeted_tests = []
    if isinstance(targeted_test_report, dict):
        passed_targeted_tests = [
            normalize_test_target(str(item).strip(), workspace_root=workspace_root)
            for item in targeted_test_report.get("passed_tests", [])
            if normalize_test_target(str(item).strip(), workspace_root=workspace_root)
        ]
    analyzed_tests = [
        analyze_backend_test_file(test_path, workspace_root=workspace_root)
        for test_path in sorted(set(passed_targeted_tests))
    ]
    service_boundary_truth = any(row["service_boundary_truth"] for row in analyzed_tests)
    sql_persistence_truth = any(row["sql_persistence_truth"] for row in analyzed_tests)
    service_persistence_roundtrip_truth = any(row["service_persistence_roundtrip_truth"] for row in analyzed_tests)
    migration_execution_truth = any(row["migration_execution_truth"] for row in analyzed_tests)

    missing_truths: list[str] = []
    if not service_boundary_truth:
        missing_truths.append("service_boundary_truth")
    if requires_persistence_truth and not sql_persistence_truth:
        missing_truths.append("sql_persistence_truth")
    if requires_persistence_truth and not service_persistence_roundtrip_truth:
        missing_truths.append("service_persistence_roundtrip_truth")
    if requires_persistence_truth and not migration_execution_truth:
        missing_truths.append("migration_execution")

    return {
        "applicable": True,
        "requires_persistence_truth": requires_persistence_truth,
        "service_boundary_truth": service_boundary_truth,
        "sql_persistence_truth": sql_persistence_truth,
        "service_persistence_roundtrip_truth": service_persistence_roundtrip_truth,
        "migration_execution": migration_execution_truth,
        "passed_targeted_test_count": len(analyzed_tests),
        "analyzed_targeted_tests": analyzed_tests,
        "missing_truths": missing_truths,
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


def build_execution_env(*, workspace_root: Path, run_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    home_dir = run_dir / "execution-home"
    corepack_home = run_dir / "corepack-home"
    pnpm_home = run_dir / "pnpm-home"
    xdg_cache_home = run_dir / "xdg-cache"
    npm_cache = run_dir / "npm-cache"
    for path in (home_dir, corepack_home, pnpm_home, xdg_cache_home, npm_cache):
        path.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(home_dir)
    env["COREPACK_HOME"] = str(corepack_home)
    env["PNPM_HOME"] = str(pnpm_home)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)
    env["npm_config_cache"] = str(npm_cache)
    env["npm_config_userconfig"] = str(workspace_root / ".npmrc")
    env["PHASE3_RUN_DIR"] = str(run_dir)
    env["PHASE3_WORKSPACE_ROOT"] = str(workspace_root)
    env.setdefault("CI", "1")
    env.setdefault("FORCE_COLOR", "0")
    current_path = env.get("PATH", "")
    env["PATH"] = f"{pnpm_home}:{current_path}" if current_path else str(pnpm_home)
    return env


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
) -> tuple[subprocess.CompletedProcess[str], bool]:
    try:
        completed = subprocess.run(
            command,
            cwd=workspace_root,
            shell=True,
            executable="/bin/zsh",
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


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists() or not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def choose_postgres_host_port(
    *,
    workspace_root: Path,
    packet_id_value: str,
    starting_port: int | None = None,
    exclude_ports: set[int] | None = None,
) -> int:
    defaults = {
        **parse_env_file(workspace_root / ".env.example"),
        **parse_env_file(workspace_root / ".env"),
    }
    seed = f"{workspace_root}:{packet_id_value}"
    base = 55000 + (zlib.adler32(seed.encode("utf-8")) % 3000)
    raw_requested = str(defaults.get("POSTGRES_HOST_PORT", str(base)) or str(base)).strip()
    try:
        requested = int(raw_requested)
    except (TypeError, ValueError):
        requested = base
    requested = starting_port or requested
    return choose_available_host_port(
        requested_port=requested,
        exclude_ports=exclude_ports,
        host="0.0.0.0",
        min_port=54000,
        max_port=62000,
        fallback_port=base,
        port_in_use=host_port_in_use,
    )


def compose_project_name(*, workspace_root: Path, run_dir: Path | None = None) -> str:
    seed_value = str(workspace_root.resolve())
    if run_dir is not None:
        seed_value = f"{seed_value}:{run_dir.resolve()}"
    seed = seed_value.encode("utf-8", errors="ignore")
    suffix = zlib.adler32(seed) & 0xFFFFFFFF
    return f"phase3-{suffix:08x}"


def validate_runtime_compose_template(compose_path: Path) -> dict[str, Any]:
    findings: list[str] = []
    if not compose_path.exists() or not compose_path.is_file():
        return {
            "valid": False,
            "compose_path": str(compose_path),
            "findings": ["compose_file_missing"],
        }

    content = compose_path.read_text(encoding="utf-8", errors="ignore")
    if "container_name:" in content:
        findings.append("container_name_forbidden")
    if "  postgres:" not in content:
        findings.append("postgres_service_missing")
    if "image: postgres:16" not in content:
        findings.append("postgres_image_must_be_postgres_16")
    for env_key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        if env_key not in content:
            findings.append(f"{env_key.lower()}_missing")
    postgres_loopback_pattern = re.compile(
        r"127\.0\.0\.1:\$\{POSTGRES_HOST_PORT(?::-?[0-9]+)?\}:5432"
    )
    if not postgres_loopback_pattern.search(content):
        findings.append("postgres_port_must_bind_loopback_variable")
    if re.search(r'["\']?5432:5432["\']?', content):
        findings.append("postgres_fixed_host_port_forbidden")
    if "  redis:" in content and not re.search(
        r"127\.0\.0\.1:\$\{REDIS_HOST_PORT(?::-?[0-9]+)?\}:6379",
        content,
    ):
        findings.append("redis_port_must_bind_loopback_variable")
    if "  api:" in content:
        if "${API_HOST_PORT" not in content:
            findings.append("api_host_port_must_be_variable")
        if "/healthz" not in content:
            findings.append("api_healthcheck_missing")
    if "  web:" in content:
        if "${WEB_HOST_PORT" not in content:
            findings.append("web_host_port_must_be_variable")
        if "CONTAINER_HEALTH_PATH: /" not in content:
            findings.append("web_healthcheck_missing")
    return {
        "valid": not findings,
        "compose_path": str(compose_path),
        "findings": findings,
    }


def backend_runtime_preflight_required(*, packet_document: dict[str, Any], workspace_root: Path) -> bool:
    candidate_tests = flatten_packet_tests(packet_document, ("sql", "contract", "scenario", "replay"))
    if not candidate_tests:
        return False
    if packet_lane(packet_document) == "backend":
        return True
    analyzed_tests = [
        analyze_backend_test_file(test_path, workspace_root=workspace_root)
        for test_path in candidate_tests
    ]
    return any(
        bool(item.get("service_boundary_truth"))
        or bool(item.get("sql_persistence_truth"))
        or bool(item.get("service_persistence_roundtrip_truth"))
        or bool(item.get("migration_execution_truth"))
        for item in analyzed_tests
    )


def is_port_bind_conflict(stderr: str) -> bool:
    normalized = str(stderr).lower()
    return "port is already allocated" in normalized or "bind for 0.0.0.0:" in normalized


def ensure_backend_runtime_preflight(
    *,
    packet_document: dict[str, Any],
    workspace_root: Path,
    execution_env: dict[str, str],
    run_dir: Path,
) -> dict[str, Any]:
    result = {
        "required": False,
        "ready": True,
        "started": False,
        "command": "",
        "project_name": "",
        "failure_reason": "",
        "stdout_log_path": "",
        "stderr_log_path": "",
        "attempted_ports": [],
        "template_validation": {},
    }
    compose_path = workspace_root / "docker-compose.dev.yml"
    if not backend_runtime_preflight_required(packet_document=packet_document, workspace_root=workspace_root) or not compose_path.exists():
        return result

    result["required"] = True
    project_name = compose_project_name(workspace_root=workspace_root, run_dir=run_dir)
    execution_env["COMPOSE_PROJECT_NAME"] = project_name
    result["project_name"] = project_name
    stdout_path = run_dir / "verification-logs" / "runtime-preflight.stdout.log"
    stderr_path = run_dir / "verification-logs" / "runtime-preflight.stderr.log"
    result["stdout_log_path"] = str(stdout_path)
    result["stderr_log_path"] = str(stderr_path)
    template_validation = validate_runtime_compose_template(compose_path)
    result["template_validation"] = template_validation
    if not template_validation["valid"]:
        write_text(stdout_path, "")
        write_text(stderr_path, json.dumps(template_validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        result["ready"] = False
        result["failure_reason"] = "runtime_preflight_compose_template_invalid"
        return result
    packet_id_value = str(packet_document.get("packet_id", "")).strip()
    port_seed_value = f"{packet_id_value}:{run_dir.resolve()}"
    attempted_ports: set[int] = set()
    combined_stdout = ""
    combined_stderr = ""
    postgres_port = choose_postgres_host_port(
        workspace_root=workspace_root,
        packet_id_value=port_seed_value,
    )
    command = ""
    for attempt in range(1, RUNTIME_PREFLIGHT_PORT_RETRY_LIMIT + 1):
        attempted_ports.add(postgres_port)
        result["attempted_ports"] = sorted(attempted_ports)
        execution_env["POSTGRES_HOST_PORT"] = str(postgres_port)
        execution_env["DATABASE_URL"] = f"postgresql://postgres:postgres@127.0.0.1:{postgres_port}/app"
        command = f"docker compose -p {project_name} -f {compose_path} --project-directory {workspace_root} up -d postgres"
        result["command"] = command
        up_completed = subprocess.run(
            command,
            cwd=workspace_root,
            shell=True,
            executable="/bin/zsh",
            text=True,
            capture_output=True,
            env=execution_env,
        )
        combined_stdout += f"[attempt {attempt} port {postgres_port}]\n{up_completed.stdout}"
        combined_stderr += f"[attempt {attempt} port {postgres_port}]\n{up_completed.stderr}"
        if up_completed.returncode == 0:
            break
        if attempt < RUNTIME_PREFLIGHT_PORT_RETRY_LIMIT and is_port_bind_conflict(up_completed.stderr):
            postgres_port = choose_postgres_host_port(
                workspace_root=workspace_root,
                packet_id_value=packet_id_value,
                starting_port=postgres_port + 1,
                exclude_ports=attempted_ports,
            )
            continue
        write_text(stdout_path, combined_stdout)
        write_text(stderr_path, combined_stderr)
        result["ready"] = False
        result["failure_reason"] = "runtime_preflight_compose_up_failed"
        return result

    write_text(stdout_path, combined_stdout)
    write_text(stderr_path, combined_stderr)

    result["started"] = True
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        ready_check = subprocess.run(
            f"docker compose -p {project_name} -f {compose_path} --project-directory {workspace_root} exec -T postgres pg_isready -U postgres",
            cwd=workspace_root,
            shell=True,
            executable="/bin/zsh",
            text=True,
            capture_output=True,
            env=execution_env,
        )
        if ready_check.returncode == 0:
            return result
        time.sleep(1)
    result["ready"] = False
    result["failure_reason"] = "runtime_preflight_postgres_not_ready"
    return result


def teardown_backend_runtime_preflight(*, workspace_root: Path, execution_env: dict[str, str]) -> None:
    compose_path = workspace_root / "docker-compose.dev.yml"
    if not compose_path.exists():
        return
    project_name = str(execution_env.get("COMPOSE_PROJECT_NAME", "")).strip()
    if not project_name:
        project_name = compose_project_name(workspace_root=workspace_root)
    subprocess.run(
        f"docker compose -p {project_name} -f {compose_path} --project-directory {workspace_root} down --remove-orphans",
        cwd=workspace_root,
        shell=True,
        executable="/bin/zsh",
        text=True,
        capture_output=True,
        env=execution_env,
    )


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
) -> dict[str, Any]:
    logs_dir = run_dir / "verification-logs"
    step_slug = slugify(step_name)
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

    logs_dir = run_dir / "verification-logs"
    step_reports: list[dict[str, Any]] = []
    structured_step_payloads: dict[str, dict[str, Any]] = {}
    progress_events: list[dict[str, Any]] = []
    write_verification_progress(run_dir=run_dir, events=progress_events, status="started")
    executed_steps = 0
    executed_step_names: list[str] = []
    failed_steps = 0
    execution_env = build_execution_env(workspace_root=workspace_root, run_dir=run_dir)
    step_timeout_seconds = resolve_step_timeout_seconds()
    verification_max_workers = resolve_verification_max_workers()
    verification_execution_mode = "not-run"
    runtime_preflight = ensure_backend_runtime_preflight(
        packet_document=packet_document,
        workspace_root=workspace_root,
        execution_env=execution_env,
        run_dir=run_dir,
    )

    if runtime_preflight["required"] and not runtime_preflight["ready"]:
        verification_execution_mode = "runtime-preflight"
        executed_steps = 1
        failed_steps = 1
        step_reports.append(
            {
                "step": "runtime-preflight",
                "command": str(runtime_preflight["command"]),
                "verdict": "fail",
                "exit_code": 1,
                "duration_ms": 0,
                "started_at_epoch_s": time.time(),
                "stdout_log_path": str(runtime_preflight["stdout_log_path"]),
                "stderr_log_path": str(runtime_preflight["stderr_log_path"]),
                "verification_method": "runtime-preflight",
                "failure_reason": str(runtime_preflight["failure_reason"]),
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
            if runtime_preflight["started"]:
                teardown_backend_runtime_preflight(
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
        "runtime_preflight": runtime_preflight,
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
    write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(report_md_path, build_verification_markdown(report))
    write_verification_progress(run_dir=run_dir, events=progress_events, status="finished", current_step="")
    return {
        **report,
        "report_path": str(report_path),
        "report_markdown_path": str(report_md_path),
    }


def empty_worker_run_report() -> dict[str, Any]:
    return {
        "summary": {
            "event_count": 0,
            "tracked_packet_count": 0,
        },
        "latest_status_by_packet": {},
        "packet_rows": [],
        "started_packets": [],
        "implemented_packets": [],
        "blocked_packets": [],
        "failed_packets": [],
        "events": [],
    }


def ensure_worker_run_report(report_path: Path) -> dict[str, Any]:
    if not report_path.exists():
        return empty_worker_run_report()
    return load_json(report_path)


def build_worker_run_report_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    lines = [
        "# Phase-3 Worker Run Report",
        "",
        "## Summary",
        f"- event_count: {report.get('summary', {}).get('event_count', 0)}",
        f"- tracked_packet_count: {report.get('summary', {}).get('tracked_packet_count', 0)}",
        "",
        "## Latest Status",
    ]
    for row in report.get("packet_rows", []) or [{"packet_id": "none", "latest_status": "", "last_event_at": ""}]:
        if row["packet_id"] == "none":
            lines.append("- none")
        else:
            lines.append(
                f"- {row['packet_id']} [{row['latest_status']}] last_event_at={row['last_event_at'] or 'n/a'} evidence={row['evidence_ref'] or 'none'}"
            )
    lines.extend(["", "## Recent Events"])
    recent_events = report.get("events", [])[-10:]
    for event in recent_events or [{"packet_id": "none", "status": "", "at": ""}]:
        if event["packet_id"] == "none":
            lines.append("- none")
        else:
            lines.append(
                f"- {event['at']} {event['packet_id']} -> {event['status']} actor={event.get('actor', '') or 'n/a'} note={event.get('note', '') or 'none'}"
            )
    return localize_phase3_worker_run_report("\n".join(lines) + "\n", output_locale)


def update_worker_run_report(
    *,
    report: dict[str, Any],
    packet: str,
    status: str,
    note: str = "",
    evidence_ref: str = "",
    actor: str = "",
    at: str | None = None,
) -> dict[str, Any]:
    normalized_status = status.strip().lower()
    if normalized_status not in VALID_WORKER_RUN_STATUSES:
        raise ValueError(f"unsupported status: {status}")

    event_time = at or datetime.now(timezone.utc).isoformat()
    event = {
        "packet_id": packet.strip(),
        "status": normalized_status,
        "note": note.strip(),
        "evidence_ref": evidence_ref.strip(),
        "actor": actor.strip(),
        "at": event_time,
    }

    events = report.get("events", [])
    if not isinstance(events, list):
        events = []
    events.append(event)

    latest_status_by_packet: dict[str, dict[str, str]] = {}
    for item in events:
        if not isinstance(item, dict):
            continue
        packet_id_value = str(item.get("packet_id", "")).strip()
        if not packet_id_value:
            continue
        latest_status_by_packet[packet_id_value] = {
            "status": str(item.get("status", "")).strip(),
            "note": str(item.get("note", "")).strip(),
            "evidence_ref": str(item.get("evidence_ref", "")).strip(),
            "actor": str(item.get("actor", "")).strip(),
            "at": str(item.get("at", "")).strip(),
        }

    packet_rows = [
        {
            "packet_id": packet_id_value,
            "latest_status": payload["status"],
            "note": payload["note"],
            "evidence_ref": payload["evidence_ref"],
            "actor": payload["actor"],
            "last_event_at": payload["at"],
        }
        for packet_id_value, payload in sorted(latest_status_by_packet.items())
    ]

    def packets_for(target_status: str) -> list[str]:
        return sorted(
            packet_id_value
            for packet_id_value, payload in latest_status_by_packet.items()
            if payload["status"] == target_status
        )

    return {
        "summary": {
            "event_count": len(events),
            "tracked_packet_count": len(packet_rows),
        },
        "latest_status_by_packet": latest_status_by_packet,
        "packet_rows": packet_rows,
        "started_packets": packets_for("started"),
        "implemented_packets": packets_for("implemented"),
        "blocked_packets": packets_for("blocked"),
        "failed_packets": packets_for("failed"),
        "events": events,
    }


def record_worker_run_event(
    *,
    report_path: Path,
    packet: str,
    status: str,
    note: str = "",
    evidence_ref: str = "",
    actor: str = "",
) -> dict[str, Any]:
    report = ensure_worker_run_report(report_path)
    updated = update_worker_run_report(
        report=report,
        packet=packet,
        status=status,
        note=note,
        evidence_ref=evidence_ref,
        actor=actor,
    )
    markdown_path = report_path.with_suffix(".md")
    write_text(report_path, json.dumps(updated, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(markdown_path, build_worker_run_report_markdown(updated))
    return {
        "output_path": str(report_path),
        "markdown_path": str(markdown_path),
        **updated["summary"],
    }


def initialize_worker_run_report(report_path: Path) -> dict[str, Any]:
    report = empty_worker_run_report()
    markdown_path = report_path.with_suffix(".md")
    write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(markdown_path, build_worker_run_report_markdown(report))
    return {
        "output_path": str(report_path),
        "markdown_path": str(markdown_path),
        **report["summary"],
    }


def build_runtime_cycle_markdown(summary: dict[str, Any], output_locale: str | None = None) -> str:
    dispatch = summary.get("dispatch_summary", {})
    lines = [
        "# Phase-3 Runtime Cycle Summary",
        "",
        "## Cycle",
        f"- event_recorded: {'yes' if summary.get('recorded_event') else 'no'}",
        f"- current_dispatch_wave: {dispatch.get('current_dispatch_wave', 'none')}",
        f"- dispatchable_packet_count: {dispatch.get('dispatchable_packet_count', 0)}",
        f"- ready_packet_count: {dispatch.get('ready_packet_count', 0)}",
        f"- queued_packet_count: {dispatch.get('queued_packet_count', 0)}",
        f"- in_progress_packet_count: {dispatch.get('in_progress_packet_count', 0)}",
        f"- implemented_packet_count: {dispatch.get('implemented_packet_count', 0)}",
        f"- verified_packet_count: {dispatch.get('verified_packet_count', 0)}",
        "",
        "## Dispatch Outputs",
        f"- runtime_state: {dispatch.get('output_path', 'n/a')}",
        f"- dispatch_manifest: {dispatch.get('manifest_path', 'n/a')}",
    ]
    if summary.get("recorded_event"):
        event = summary["recorded_event"]
        lines.extend(
            [
                "",
                "## Recorded Event",
                f"- packet_id: {event['packet_id']}",
                f"- status: {event['status']}",
                f"- actor: {event.get('actor', '') or 'n/a'}",
                f"- note: {event.get('note', '') or 'none'}",
                f"- evidence_ref: {event.get('evidence_ref', '') or 'none'}",
            ]
        )
    return localize_phase3_runtime_cycle_summary("\n".join(lines) + "\n", output_locale)


def run_runtime_cycle(
    *,
    execution_loop_plan_path: Path,
    output_dir: Path,
    worker_run_report_path: Path | None = None,
    wp_gate_report_path: Path | None = None,
    runtime_environment_ledger_path: Path | None = None,
    record_packet: str | None = None,
    record_status: str | None = None,
    note: str = "",
    evidence_ref: str = "",
    actor: str = "",
) -> dict[str, Any]:
    worker_report_path = worker_run_report_path or (output_dir / "worker-run-report.json")
    if not worker_report_path.exists():
        initialize_worker_run_report(worker_report_path)
    runtime_ledger_path = runtime_environment_ledger_path or (output_dir / "runtime-environment-ledger.json")

    recorded_event: dict[str, Any] | None = None
    if record_status:
        if not record_packet:
            raise ValueError("record_packet is required when record_status is provided")
        record_worker_run_event(
            report_path=worker_report_path,
            packet=record_packet,
            status=record_status,
            note=note,
            evidence_ref=evidence_ref,
            actor=actor,
        )
        recorded_event = {
            "packet_id": record_packet,
            "status": record_status,
            "note": note,
            "evidence_ref": evidence_ref,
            "actor": actor,
        }

    dispatch_summary = emit_execution_dispatch_artifacts(
        execution_loop_plan=load_json(execution_loop_plan_path),
        output_dir=output_dir,
        worker_run_report=load_json(worker_report_path) if worker_report_path.exists() else None,
        wp_gate_report=load_json(wp_gate_report_path) if wp_gate_report_path and wp_gate_report_path.exists() else None,
        runtime_environment_ledger=load_json(runtime_ledger_path) if runtime_ledger_path.exists() else None,
    )
    summary = {
        "execution_loop_plan": str(execution_loop_plan_path),
        "worker_run_report": str(worker_report_path),
        "wp_gate_report": str(wp_gate_report_path) if wp_gate_report_path else "",
        "recorded_event": recorded_event,
        "dispatch_summary": dispatch_summary,
    }
    summary_path = output_dir / "runtime-cycle-summary.json"
    summary_md_path = output_dir / "runtime-cycle-summary.md"
    write_text(summary_path, json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(summary_md_path, build_runtime_cycle_markdown(summary))
    return {
        "summary_path": str(summary_path),
        "summary_markdown_path": str(summary_md_path),
        **dispatch_summary,
    }


def parse_worker_run_report(report: dict[str, Any] | None) -> dict[str, set[str]]:
    statuses = {
        "started": set(),
        "implemented": set(),
        "blocked": set(),
        "failed": set(),
    }
    if not report:
        return statuses
    aliases = {
        "started": ("started_packets", "in_progress_packets"),
        "implemented": ("implemented_packets", "completed_packets"),
        "blocked": ("blocked_packets",),
        "failed": ("failed_packets",),
    }
    for status, keys in aliases.items():
        for key in keys:
            value = report.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        wave = int(item.get("wave", 0) or 0)
                        lane = str(item.get("lane", "")).strip()
                        if wave and lane:
                            statuses[status].add(packet_id(wave=wave, lane=lane))
                    else:
                        normalized = str(item).strip()
                        if normalized:
                            statuses[status].add(normalized)
    return statuses


def parse_wp_gate_rows(report: dict[str, Any] | None) -> dict[str, str]:
    rows: dict[str, str] = {}
    if not report:
        return rows
    for row in report.get("rows", []):
        if not isinstance(row, dict):
            continue
        wp_id = str(row.get("wp_id", "")).strip()
        status = str(row.get("status", "")).strip()
        if wp_id and status:
            rows[wp_id] = status
    return rows


def parse_runtime_environment_rows(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not report:
        return rows
    for row in report.get("rows", []):
        if not isinstance(row, dict):
            continue
        packet = str(row.get("packet_id", "")).strip()
        if packet:
            rows[packet] = row
    return rows


def row_reaches_unlock_ceiling(row: dict[str, Any]) -> bool:
    if row.get("current_state") == "verified":
        return True
    return (
        row.get("current_state") == "implemented"
        and (
            row.get("wp_gate_rollup") == "runtime-blocked"
            or not bool(row.get("runtime_environment_available", True))
        )
    )


def wave_reaches_unlock_ceiling(rows: list[dict[str, Any]], wave: int) -> bool:
    wave_rows = [row for row in rows if int(row.get("wave", 0) or 0) == wave]
    return bool(wave_rows) and all(row_reaches_unlock_ceiling(row) for row in wave_rows)


def initial_packet_state(dispatch_state: str, worker_packet_status: str) -> str:
    if worker_packet_status != "ready":
        return "blocked"
    if dispatch_state == "ready-now":
        return "ready"
    if dispatch_state == "queued-on-prior-wave":
        return "queued"
    return "blocked"


def runtime_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Phase-3 Execution Runtime State",
        "",
        "## Summary",
        f"- overall_status: {report.get('overall_status', 'unknown')}",
        f"- current_dispatch_wave: {summary.get('current_dispatch_wave', 'none')}",
        f"- dispatchable_packet_count: {summary.get('dispatchable_packet_count', 0)}",
        f"- ready_packet_count: {summary.get('ready_packet_count', 0)}",
        f"- queued_packet_count: {summary.get('queued_packet_count', 0)}",
        f"- in_progress_packet_count: {summary.get('in_progress_packet_count', 0)}",
        f"- verified_packet_count: {summary.get('verified_packet_count', 0)}",
        f"- blocked_packet_count: {summary.get('blocked_packet_count', 0)}",
        "",
        "## Dispatchable Packets",
    ]
    for row in report.get("dispatchable_packets", []) or [{"packet_id": "none", "lane": "", "wave": 0, "work_package_ids": []}]:
        if row["packet_id"] == "none":
            lines.append("- none")
        else:
            lines.append(
                f"- {row['packet_id']} lane={row['lane']} wave={row['wave']} wps={', '.join(row['work_package_ids'])}"
            )
    lines.extend(["", "## Packet State"])
    for row in report.get("rows", []):
        lines.append(
            f"- {row['packet_id']} [{row['current_state']}] dispatch={row['dispatch_decision']} gate={row['wp_gate_rollup']} wps={', '.join(row['work_package_ids'])}"
        )
    return localize_phase3_execution_runtime_state("\n".join(lines) + "\n", output_locale)


def manifest_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    lines = [
        "# Phase-3 Dispatch Manifest",
        "",
        "## Current Dispatchable Packets",
    ]
    for row in report.get("dispatchable_packets", []) or [{"packet_id": "none", "lane": "", "wave": 0, "skill_entrypoint_hint": ""}]:
        if row["packet_id"] == "none":
            lines.append("- none")
        else:
            lines.append(
                f"- {row['packet_id']} -> {row['skill_entrypoint_hint']} ({row['lane']})"
            )
    return localize_phase3_dispatch_manifest("\n".join(lines) + "\n", output_locale)


def analyze_execution_dispatch(
    *,
    execution_loop_plan: dict[str, Any],
    worker_run_report: dict[str, Any] | None = None,
    wp_gate_report: dict[str, Any] | None = None,
    runtime_environment_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_statuses = parse_worker_run_report(worker_run_report)
    wp_gate_rows = parse_wp_gate_rows(wp_gate_report)
    runtime_rows = parse_runtime_environment_rows(runtime_environment_ledger)
    waves = execution_loop_plan.get("waves", [])
    if not isinstance(waves, list):
        raise ValueError("execution_loop_plan must contain waves")

    rows: list[dict[str, Any]] = []
    wave_numbers: set[int] = set()
    for wave in waves:
        wave_number = int(wave.get("wave", 0) or 0)
        for packet in wave.get("worker_packets", []):
            if not isinstance(packet, dict):
                continue
            lane = str(packet.get("lane", "")).strip()
            if not wave_number or not lane:
                continue
            pid = packet_id(wave=wave_number, lane=lane)
            base_state = initial_packet_state(
                str(packet.get("dispatch_state", "")).strip(),
                str(packet.get("worker_packet_status", "")).strip(),
            )
            current_state = base_state
            if pid in run_statuses["failed"] or pid in run_statuses["blocked"]:
                current_state = "blocked"
            elif pid in run_statuses["implemented"]:
                current_state = "implemented"
            elif pid in run_statuses["started"]:
                current_state = "in-progress"

            wp_ids = [str(item).strip() for item in packet.get("work_package_ids", []) if str(item).strip()]
            wp_statuses = [wp_gate_rows.get(wp_id, "") for wp_id in wp_ids if wp_gate_rows.get(wp_id, "")]
            runtime_row = runtime_rows.get(pid, {})
            runtime_available = str(runtime_row.get("current_availability", "available")).strip() == "available"
            if wp_ids and wp_statuses and all(status == "pass" for status in wp_statuses):
                wp_gate_rollup = "pass"
                if pid in run_statuses["implemented"] and runtime_available:
                    current_state = "verified"
            elif wp_ids and wp_statuses and all(status in {"pass", "runtime-blocked"} for status in wp_statuses):
                wp_gate_rollup = "runtime-blocked"
                if pid in run_statuses["implemented"] and runtime_available:
                    current_state = "verified"
            elif any(status == "blocked" for status in wp_statuses):
                current_state = "blocked"
                wp_gate_rollup = "blocked"
            elif any(status == "in-progress" for status in wp_statuses):
                wp_gate_rollup = "in-progress"
            else:
                wp_gate_rollup = "unknown"

            row = {
                "packet_id": pid,
                "wave": wave_number,
                "lane": lane,
                "current_state": current_state,
                "base_state": base_state,
                "dispatch_seed": str(packet.get("dispatch_state", "")).strip(),
                "worker_packet_status": str(packet.get("worker_packet_status", "")).strip(),
                "skill_entrypoint_hint": str(packet.get("skill_entrypoint_hint", "")).strip(),
                "work_package_ids": wp_ids,
                "packet_json": str(packet.get("packet_json", "")).strip(),
                "packet_markdown": str(packet.get("packet_markdown", "")).strip(),
                "implementation_target_count": int(packet.get("implementation_target_count", 0) or 0),
                "test_count": int(packet.get("test_count", 0) or 0),
                "wp_gate_rollup": wp_gate_rollup,
                "runtime_environment_available": runtime_available,
                "required_runtime_environment": str(runtime_row.get("required_runtime_environment", "")).strip(),
                "allowed_progress_ceiling": str(runtime_row.get("allowed_progress_ceiling", "")).strip(),
                "dispatch_decision": "hold",
            }
            rows.append(row)
            wave_numbers.add(wave_number)

    for row in rows:
        if row["runtime_environment_available"]:
            continue
        if row["current_state"] in {"ready", "queued"}:
            row["current_state"] = "implemented"
            if row.get("wp_gate_rollup") == "unknown":
                row["wp_gate_rollup"] = "runtime-blocked"
            continue
        if row["current_state"] == "blocked" and row.get("wp_gate_rollup") in {"pass", "runtime-blocked", "unknown"}:
            row["current_state"] = "implemented"
            if row.get("wp_gate_rollup") in {"pass", "unknown"}:
                row["wp_gate_rollup"] = "runtime-blocked"

    for row in rows:
        if row["current_state"] != "queued":
            continue
        prior_waves = sorted(wave for wave in wave_numbers if wave < row["wave"])
        prior_verified = all(wave_reaches_unlock_ceiling(rows, wave) for wave in prior_waves)
        if prior_verified:
            row["current_state"] = "ready"

    dispatchable_packets: list[dict[str, Any]] = []
    for row in rows:
        if row["current_state"] == "ready":
            row["dispatch_decision"] = "dispatch-now"
            dispatchable_packets.append(row)
        elif row["current_state"] == "queued":
            row["dispatch_decision"] = "wait-prior-wave"
        elif row["current_state"] == "in-progress":
            row["dispatch_decision"] = "await-worker-result"
        elif row["current_state"] == "implemented":
            row["dispatch_decision"] = (
                "await-runtime-environment" if not row["runtime_environment_available"] else "await-wp-gate"
            )
        elif row["current_state"] == "verified":
            row["dispatch_decision"] = "done"
        else:
            row["dispatch_decision"] = "blocked"

    current_dispatch_wave = min((row["wave"] for row in dispatchable_packets), default=None)
    return {
        "overall_status": "valid" if str(execution_loop_plan.get("overall_status", "")).strip() == "valid" else "invalid",
        "summary": {
            "packet_count": len(rows),
            "dispatchable_packet_count": len(dispatchable_packets),
            "ready_packet_count": sum(1 for row in rows if row["current_state"] == "ready"),
            "queued_packet_count": sum(1 for row in rows if row["current_state"] == "queued"),
            "in_progress_packet_count": sum(1 for row in rows if row["current_state"] == "in-progress"),
            "implemented_packet_count": sum(1 for row in rows if row["current_state"] == "implemented"),
            "verified_packet_count": sum(1 for row in rows if row["current_state"] == "verified"),
            "blocked_packet_count": sum(1 for row in rows if row["current_state"] == "blocked"),
            "current_dispatch_wave": current_dispatch_wave,
        },
        "dispatchable_packets": dispatchable_packets,
        "rows": rows,
    }


def emit_execution_dispatch_artifacts(
    *,
    execution_loop_plan: dict[str, Any],
    output_dir: Path,
    worker_run_report: dict[str, Any] | None = None,
    wp_gate_report: dict[str, Any] | None = None,
    runtime_environment_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = analyze_execution_dispatch(
        execution_loop_plan=execution_loop_plan,
        worker_run_report=worker_run_report,
        wp_gate_report=wp_gate_report,
        runtime_environment_ledger=runtime_environment_ledger,
    )
    state_path = output_dir / "execution-runtime-state.json"
    manifest_path = output_dir / "dispatch-manifest.json"
    state_md_path = output_dir / "execution-runtime-state.md"
    manifest_md_path = output_dir / "dispatch-manifest.md"
    write_text(state_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(
        manifest_path,
        json.dumps({"dispatchable_packets": report["dispatchable_packets"]}, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
    )
    write_text(state_md_path, runtime_markdown(report))
    write_text(manifest_md_path, manifest_markdown(report))
    return {
        "output_path": str(state_path),
        "manifest_path": str(manifest_path),
        "state_markdown_path": str(state_md_path),
        "manifest_markdown_path": str(manifest_md_path),
        **report["summary"],
        "overall_status": report["overall_status"],
    }


def empty_verification_ledger() -> dict[str, Any]:
    return {
        "summary": {
            "tracked_packet_count": 0,
            "successful_packet_count": 0,
            "failed_packet_count": 0,
            "aggregated_passed_test_count": 0,
            "aggregated_verification_duration_ms": 0,
        },
        "latest_by_packet": {},
        "aggregated": {
            "passed_tests": [],
            "packet_ids_with_green_verification": [],
            "step_status": {step: "unknown" for step in VERIFICATION_STEP_NAMES},
            "backend_truth": {
                "successful_backend_packet_count": 0,
                "packets_requiring_persistence_truth": 0,
                "service_boundary_truth_packet_count": 0,
                "sql_persistence_truth_packet_count": 0,
                "service_persistence_roundtrip_truth_packet_count": 0,
                "migration_execution_packet_count": 0,
                "missing_truths_by_packet": {},
            },
            "verification_timing": {
                "measurement_source": "verification-ledger",
                "packet_duration_ms": {"sample_count": 0, "min": 0, "max": 0, "avg": 0, "total": 0},
                "step_duration_ms": {
                    step: {"sample_count": 0, "min": 0, "max": 0, "avg": 0, "total": 0}
                    for step in VERIFICATION_STEP_NAMES
                },
            },
        },
    }


def build_verification_ledger_markdown(ledger: dict[str, Any], output_locale: str | None = None) -> str:
    summary = ledger.get("summary", {})
    aggregated = ledger.get("aggregated", {})
    step_status = aggregated.get("step_status", {})
    lines = [
        "# Phase-3 Verification Ledger",
        "",
        "## Summary",
        f"- tracked_packet_count: {summary.get('tracked_packet_count', 0)}",
        f"- successful_packet_count: {summary.get('successful_packet_count', 0)}",
        f"- failed_packet_count: {summary.get('failed_packet_count', 0)}",
        f"- aggregated_passed_test_count: {summary.get('aggregated_passed_test_count', 0)}",
        f"- aggregated_verification_duration_ms: {summary.get('aggregated_verification_duration_ms', 0)}",
        "",
        "## Aggregated Step Status",
        f"- lint: {step_status.get('lint', 'unknown')}",
        f"- typecheck: {step_status.get('typecheck', 'unknown')}",
        f"- critical-targeted-tests: {step_status.get('critical-targeted-tests', 'unknown')}",
        f"- targeted-tests: {step_status.get('targeted-tests', 'unknown')}",
        f"- full-targeted-tests: {step_status.get('full-targeted-tests', 'unknown')}",
        f"- unit-tests: {step_status.get('unit-tests', 'unknown')}",
        f"- build: {step_status.get('build', 'unknown')}",
        "",
        "## Packet Entries",
    ]
    latest_by_packet = ledger.get("latest_by_packet", {})
    if not isinstance(latest_by_packet, dict) or not latest_by_packet:
        lines.append("- none")
    else:
        for packet_id in sorted(latest_by_packet):
            row = latest_by_packet[packet_id]
            lines.append(
                f"- {packet_id} [{row.get('overall_verdict', 'unknown')}] passed_tests={len(row.get('passed_tests', []))} run_dir={row.get('run_dir', 'n/a')}"
            )
    return localize_phase3_verification_ledger("\n".join(lines) + "\n", output_locale)


def extract_step_verdicts(verification_report: dict[str, Any]) -> dict[str, str]:
    verdicts: dict[str, str] = {}
    for row in verification_report.get("steps", []):
        if not isinstance(row, dict):
            continue
        step = str(row.get("step", "")).strip()
        verdict = str(row.get("verdict", "")).strip()
        if step and verdict:
            verdicts[step] = verdict
    if CRITICAL_TARGETED_STEP in verdicts and LEGACY_TARGETED_STEP not in verdicts:
        verdicts[LEGACY_TARGETED_STEP] = verdicts[CRITICAL_TARGETED_STEP]
    if FULL_TARGETED_STEP in verdicts and LEGACY_TARGETED_STEP not in verdicts:
        verdicts[LEGACY_TARGETED_STEP] = verdicts[FULL_TARGETED_STEP]
    return verdicts


def extract_step_durations(verification_report: dict[str, Any]) -> dict[str, int]:
    durations: dict[str, int] = {}
    for row in verification_report.get("steps", []):
        if not isinstance(row, dict):
            continue
        step = str(row.get("step", "")).strip()
        value = row.get("duration_ms", 0)
        if step and isinstance(value, (int, float)):
            durations[step] = int(value)
    if CRITICAL_TARGETED_STEP in durations and LEGACY_TARGETED_STEP not in durations:
        durations[LEGACY_TARGETED_STEP] = durations[CRITICAL_TARGETED_STEP]
    if FULL_TARGETED_STEP in durations and LEGACY_TARGETED_STEP not in durations:
        durations[LEGACY_TARGETED_STEP] = durations[FULL_TARGETED_STEP]
    return durations


def verification_entry_from_report(
    *,
    verification_report: dict[str, Any],
    verification_report_path: Path | None = None,
) -> dict[str, Any]:
    packet = str(verification_report.get("packet_id", "")).strip()
    if not packet:
        raise ValueError("verification report missing packet_id")
    step_reports = [
        load_json_if_exists(
            Path(str(verification_report.get(path_key, "")).strip()).resolve()
            if str(verification_report.get(path_key, "")).strip()
            else None
        )
        or {}
        for path_key in ("test_report_path", "unit_test_report_path")
        + (("full_test_report_path",) if str(verification_report.get("full_test_report_path", "")).strip() else ())
    ]
    passed_tests = sorted(
        {
            str(item).strip()
            for step_report in step_reports
            for item in step_report.get("passed_tests", [])
            if str(item).strip()
        }
    )
    failed_tests = sorted(
        {
            str(item).strip()
            for step_report in step_reports
            for item in step_report.get("failed_tests", [])
            if str(item).strip()
        }
    )
    step_duration_ms = extract_step_durations(verification_report)
    return {
        "packet_id": packet,
        "lane": str(verification_report.get("lane", "")).strip(),
        "work_package_ids": [
            str(item).strip()
            for item in verification_report.get("work_package_ids", [])
            if str(item).strip()
        ],
        "overall_verdict": str(verification_report.get("overall_verdict", "")).strip() or "unknown",
        "report_path": str(verification_report_path.resolve()) if verification_report_path else "",
        "workspace_root": str(verification_report.get("workspace_root", "")).strip(),
        "run_dir": str(verification_report.get("run_dir", "")).strip(),
        "test_report_path": str(verification_report.get("test_report_path", "")).strip(),
        "full_test_report_path": str(verification_report.get("full_test_report_path", "")).strip(),
        "unit_test_report_path": str(verification_report.get("unit_test_report_path", "")).strip(),
        "lint_report_path": str(verification_report.get("lint_report_path", "")).strip(),
        "typecheck_report_path": str(verification_report.get("typecheck_report_path", "")).strip(),
        "build_report_path": str(verification_report.get("build_report_path", "")).strip(),
        "step_verdicts": extract_step_verdicts(verification_report),
        "step_duration_ms": step_duration_ms,
        "packet_duration_ms": sum(step_duration_ms.values()),
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "backend_evidence": verification_report.get("backend_evidence")
        if isinstance(verification_report.get("backend_evidence"), dict)
        else None,
    }


def update_verification_ledger(
    *,
    ledger: dict[str, Any],
    verification_report: dict[str, Any],
    verification_report_path: Path | None = None,
) -> dict[str, Any]:
    latest_by_packet = ledger.get("latest_by_packet", {})
    if not isinstance(latest_by_packet, dict):
        latest_by_packet = {}
    else:
        latest_by_packet = dict(latest_by_packet)

    entry = verification_entry_from_report(
        verification_report=verification_report,
        verification_report_path=verification_report_path,
    )
    latest_by_packet[entry["packet_id"]] = entry

    all_entries = [row for row in latest_by_packet.values() if isinstance(row, dict)]
    successful_entries = [
        row
        for row in all_entries
        if str(row.get("overall_verdict", "")).strip() == "pass"
    ]
    passed_tests = sorted(
        {
            str(test).strip()
            for row in all_entries
            for test in row.get("passed_tests", [])
            if str(test).strip()
        }
    )
    step_status = {}
    for step in VERIFICATION_STEP_NAMES:
        verdicts = [
            str(row.get("step_verdicts", {}).get(step, "")).strip()
            for row in all_entries
            if isinstance(row, dict)
            and str(row.get("step_verdicts", {}).get(step, "")).strip()
        ]
        if not verdicts:
            step_status[step] = "unknown"
        elif any(verdict == "fail" for verdict in verdicts):
            step_status[step] = "fail"
        elif all(verdict == "pass" for verdict in verdicts):
            step_status[step] = "pass"
        else:
            step_status[step] = "unknown"

    def summarize(values: list[int]) -> dict[str, int]:
        if not values:
            return {"sample_count": 0, "min": 0, "max": 0, "avg": 0, "total": 0}
        return {
            "sample_count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": round(sum(values) / len(values)),
            "total": sum(values),
        }

    packet_durations = [
        int(row.get("packet_duration_ms", 0) or 0)
        for row in all_entries
        if isinstance(row, dict) and isinstance(row.get("packet_duration_ms", 0), (int, float))
    ]
    step_duration_ms = {}
    for step in VERIFICATION_STEP_NAMES:
        samples = [
            int(row.get("step_duration_ms", {}).get(step, 0) or 0)
            for row in all_entries
            if isinstance(row, dict)
            and isinstance(row.get("step_duration_ms", {}), dict)
            and step in row.get("step_duration_ms", {})
        ]
        step_duration_ms[step] = summarize(samples)

    failed_packet_count = sum(
        1
        for row in latest_by_packet.values()
        if isinstance(row, dict) and str(row.get("overall_verdict", "")).strip() == "fail"
    )
    successful_backend_entries = [
        row
        for row in successful_entries
        if isinstance(row, dict) and str(row.get("lane", "")).strip().lower() == "backend"
    ]
    backend_missing_truths = {
        str(row.get("packet_id", "")).strip(): list(row.get("backend_evidence", {}).get("missing_truths", []))
        for row in successful_backend_entries
        if isinstance(row.get("backend_evidence"), dict) and row.get("backend_evidence", {}).get("missing_truths")
    }
    return {
        "summary": {
            "tracked_packet_count": len(latest_by_packet),
            "successful_packet_count": len(successful_entries),
            "failed_packet_count": failed_packet_count,
            "aggregated_passed_test_count": len(passed_tests),
            "aggregated_verification_duration_ms": sum(packet_durations),
        },
        "latest_by_packet": {
            packet: latest_by_packet[packet]
            for packet in sorted(latest_by_packet)
        },
        "aggregated": {
            "passed_tests": passed_tests,
            "packet_ids_with_green_verification": sorted(
                str(row.get("packet_id", "")).strip()
                for row in successful_entries
                if str(row.get("packet_id", "")).strip()
            ),
            "step_status": step_status,
            "backend_truth": {
                "successful_backend_packet_count": len(successful_backend_entries),
                "packets_requiring_persistence_truth": sum(
                    1
                    for row in successful_backend_entries
                    if isinstance(row.get("backend_evidence"), dict)
                    and bool(row.get("backend_evidence", {}).get("requires_persistence_truth"))
                ),
                "service_boundary_truth_packet_count": sum(
                    1
                    for row in successful_backend_entries
                    if isinstance(row.get("backend_evidence"), dict)
                    and bool(row.get("backend_evidence", {}).get("service_boundary_truth"))
                ),
                "sql_persistence_truth_packet_count": sum(
                    1
                    for row in successful_backend_entries
                    if isinstance(row.get("backend_evidence"), dict)
                    and bool(row.get("backend_evidence", {}).get("sql_persistence_truth"))
                ),
                "service_persistence_roundtrip_truth_packet_count": sum(
                    1
                    for row in successful_backend_entries
                    if isinstance(row.get("backend_evidence"), dict)
                    and bool(row.get("backend_evidence", {}).get("service_persistence_roundtrip_truth"))
                ),
                "migration_execution_packet_count": sum(
                    1
                    for row in successful_backend_entries
                    if isinstance(row.get("backend_evidence"), dict)
                    and bool(row.get("backend_evidence", {}).get("migration_execution"))
                ),
                "missing_truths_by_packet": backend_missing_truths,
            },
            "verification_timing": {
                "measurement_source": "verification-ledger",
                "packet_duration_ms": summarize(packet_durations),
                "step_duration_ms": step_duration_ms,
            },
        },
    }


def record_verification_report(
    *,
    ledger_path: Path,
    verification_report_path: Path,
) -> dict[str, Any]:
    ledger = load_json_if_exists(ledger_path.resolve()) or empty_verification_ledger()
    verification_report = load_json(verification_report_path.resolve())
    updated = update_verification_ledger(
        ledger=ledger,
        verification_report=verification_report,
        verification_report_path=verification_report_path,
    )
    markdown_path = ledger_path.with_suffix(".md")
    write_text(ledger_path, json.dumps(updated, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(markdown_path, build_verification_ledger_markdown(updated))
    return {
        "output_path": str(ledger_path),
        "markdown_path": str(markdown_path),
        **updated["summary"],
    }


def synthesize_gate_inputs_from_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    aggregated = ledger.get("aggregated", {})
    if not isinstance(aggregated, dict):
        aggregated = {}
    step_status = aggregated.get("step_status", {})
    if not isinstance(step_status, dict):
        step_status = {}
    return {
        "test_report": {
            "passed_tests": sorted(
                {
                    str(item).strip()
                    for item in aggregated.get("passed_tests", [])
                    if str(item).strip()
                }
            )
        },
        "lint_report": {"verdict": "pass"} if step_status.get("lint") == "pass" else None,
        "typecheck_report": {"verdict": "pass"} if step_status.get("typecheck") == "pass" else None,
        "build_report": {"verdict": "pass"} if step_status.get("build") == "pass" else None,
    }


def load_json_if_exists(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return load_json(path)


def resolve_wp_gate_report_path(output_dir: Path, wp_gate_report_path: Path | None) -> Path | None:
    if wp_gate_report_path is not None:
        return wp_gate_report_path.resolve()
    candidate = output_dir / "phase3-wp-gate.json"
    return candidate if candidate.exists() else None


def resolve_runtime_environment_ledger_path(output_dir: Path, runtime_environment_ledger_path: Path | None) -> Path | None:
    if runtime_environment_ledger_path is not None:
        return runtime_environment_ledger_path.resolve()
    candidate = output_dir / "runtime-environment-ledger.json"
    return candidate if candidate.exists() else None


def sorted_dispatchable_packets(runtime_state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = runtime_state.get("dispatchable_packets", [])
    if not isinstance(rows, list):
        return []
    return sorted(
        [row for row in rows if isinstance(row, dict)],
        key=lambda row: (int(row.get("wave", 0) or 0), str(row.get("lane", ""))),
    )


def current_runtime_row(runtime_state: dict[str, Any], packet: str) -> dict[str, Any] | None:
    rows = runtime_state.get("rows", [])
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and str(row.get("packet_id", "")).strip() == packet:
            return row
    return None


def execution_loop_row(execution_loop_plan: dict[str, Any], packet: str) -> dict[str, Any]:
    for wave in execution_loop_plan.get("waves", []):
        if not isinstance(wave, dict):
            continue
        wave_number = int(wave.get("wave", 0) or 0)
        for row in wave.get("worker_packets", []):
            if not isinstance(row, dict):
                continue
            candidate = f"wave-{wave_number:02d}:{str(row.get('lane', '')).strip()}"
            if candidate == packet:
                return {"packet_id": candidate, **row}
    raise ValueError(f"unknown packet_id: {packet}")


def load_worker_packet_document(output_dir: Path, loop_row: dict[str, Any]) -> dict[str, Any]:
    packet_ref = str(loop_row.get("packet_json", "")).strip()
    if not packet_ref:
        raise ValueError(f"packet_json missing for {loop_row.get('packet_id', 'unknown')}")
    packet_path = output_dir / packet_ref
    if not packet_path.exists():
        raise ValueError(f"worker packet missing: {packet_path}")
    packet_document = load_json(packet_path)
    packet_document.setdefault("packet_id", str(loop_row.get("packet_id", "")).strip())
    return packet_document


def next_run_directory(output_dir: Path, packet: str) -> Path:
    packet_root = output_dir / "worker-runs" / packet_slug(packet)
    existing = [
        path
        for path in packet_root.iterdir()
        if path.is_dir() and path.name.startswith("run-")
    ] if packet_root.exists() else []
    next_index = len(existing) + 1
    return packet_root / f"run-{next_index:03d}"


def build_done_criteria(packet_document: dict[str, Any]) -> list[str]:
    criteria: list[str] = []
    for row in packet_document.get("work_packages", []):
        if not isinstance(row, dict):
            continue
        acceptance = str(row.get("acceptance_criteria", "")).strip()
        wp_id = str(row.get("wp_id", "")).strip()
        if acceptance:
            prefix = f"{wp_id}: " if wp_id else ""
            criteria.append(f"{prefix}{acceptance}")
    verification = packet_document.get("verification_commands", {})
    if isinstance(verification, dict):
        sequence = verification.get("sequence", [])
        if isinstance(sequence, list) and sequence:
            criteria.append(f"Verification sequence completes: {', '.join(str(item) for item in sequence if str(item).strip())}")
    if packet_document.get("test_targets"):
        criteria.append("Assigned contract/scenario/replay tests remain green for this packet scope.")
        criteria.append("Assigned unit tests are green for the packet-owned implementation targets.")
    criteria.append("Frozen contracts, migrations, and trace IDs remain compatible with Phase-2 truth.")
    return criteria


def build_verification_script(packet_document: dict[str, Any]) -> str:
    verification = packet_document.get("verification_commands", {})
    if not isinstance(verification, dict):
        return "#!/usr/bin/env bash\nset -euo pipefail\n# verification commands unavailable\n"
    commands = verification.get("commands", {})
    sequence = verification.get("sequence", [])
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        f"# packet_id: {packet_document.get('packet_id', 'unknown')}",
        f"# workspace_scope: {verification.get('workspace_scope', 'workspace-root')}",
        "",
    ]
    if isinstance(sequence, list):
        for step in sequence:
            normalized_step = str(step).strip()
            if not normalized_step:
                continue
            command = ""
            if isinstance(commands, dict):
                command = str(commands.get(normalized_step, "")).strip()
            if command:
                lines.append(command)
    return "\n".join(lines) + "\n"


def build_runbook(
    packet_document: dict[str, Any],
    runtime_row: dict[str, Any] | None,
    mode: str,
    output_locale: str | None = None,
) -> str:
    runtime_row = runtime_row or {}
    test_targets = packet_document.get("test_targets", {})
    lines = [
        f"# Worker Packet Runbook: {packet_document.get('packet_id', 'unknown')}",
        "",
        "## Runtime Selection",
        f"- mode: {mode}",
        f"- lane: {packet_document.get('lane', 'unknown')}",
        f"- selected_state: {runtime_row.get('current_state', 'unknown')}",
        f"- dispatch_decision: {runtime_row.get('dispatch_decision', 'unknown')}",
        "",
        "## Owned Targets",
    ]
    for target in packet_document.get("implementation_targets", []) or ["none"]:
        lines.append(f"- {target}")
    lines.extend(["", "## Trace Subjects"])
    for row in packet_document.get("source_rows", []) or [{"source_id": "none", "source_type": "", "source_subject": ""}]:
        if row.get("source_id") == "none":
            lines.append("- none")
        else:
            lines.append(
                f"- {row.get('source_id', '')} [{row.get('source_type', '')}]: {row.get('source_subject', '')}"
            )
    lines.extend(
        [
            "",
            "## Tests",
            f"- contract: {', '.join(test_targets.get('contract', [])) or 'none'}",
            f"- scenario: {', '.join(test_targets.get('scenario', [])) or 'none'}",
            f"- replay: {', '.join(test_targets.get('replay', [])) or 'none'}",
            f"- unit: {', '.join(test_targets.get('unit', [])) or 'none'}",
            "",
            "## Done Criteria",
        ]
    )
    for item in build_done_criteria(packet_document):
        lines.append(f"- {item}")
    verification = packet_document.get("verification_commands", {})
    commands = verification.get("commands", {}) if isinstance(verification, dict) else {}
    lines.extend(
        [
            "",
            "## Environment Bootstrap",
            f"- package_manager: {packet_document.get('environment_bootstrap', {}).get('package_manager', 'pnpm')}",
            f"- bootstrap_command: {packet_document.get('environment_bootstrap', {}).get('bootstrap_command', 'pnpm install --frozen-lockfile=false')}",
            f"- readiness_rule: {packet_document.get('environment_bootstrap', {}).get('readiness_rule', 'Bootstrap workspace dependencies before verification.')}",
            "",
            "## Verification Commands",
            f"- lint: {commands.get('lint', 'n/a')}",
            f"- typecheck: {commands.get('typecheck', 'n/a')}",
            f"- targeted-tests: {commands.get('targeted-tests', 'n/a')}",
            f"- unit-tests: {commands.get('unit-tests', 'n/a')}",
            f"- build: {commands.get('build', 'n/a')}",
            "",
            "## Coordination",
        ]
    )
    for note in packet_document.get("coordination_notes", []) or ["Coordinate on frozen contracts before changing shared files."]:
        lines.append(f"- {note}")
    playbook = packet_document.get("implementation_playbook", {})
    if isinstance(playbook, dict) and playbook:
        lines.extend(["", "## Implementation Playbook"])
        for step in playbook.get("implementation_steps", []) or ["Follow the packet-local implementation sequence."]:
            lines.append(f"- {step}")
        contract_map = playbook.get("contract_to_code_map", [])
        if isinstance(contract_map, list) and contract_map:
            lines.extend(["", "## Contract To Code Map"])
            for row in contract_map:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"- {row.get('operation_id', 'unknown')} -> controller={row.get('controller_target', 'n/a')} service={row.get('service_target', 'n/a')} repository={row.get('repository_target', 'n/a')}"
                )
    return localize_phase3_worker_packet_runbook("\n".join(lines) + "\n", output_locale)


def build_packet_summary_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    lines = [
        f"# Packet Run Report: {report['packet_id']}",
        "",
        "## Summary",
        f"- mode: {report['mode']}",
        f"- actor: {report['actor'] or 'n/a'}",
        f"- dispatchable_when_selected: {'yes' if report['dispatchable_when_selected'] else 'no'}",
        f"- selected_pre_state: {report['pre_runtime_row'].get('current_state', 'unknown')}",
        f"- selected_post_state: {report['post_runtime_row'].get('current_state', 'unknown')}",
        f"- statuses_recorded: {', '.join(report['event_statuses_recorded']) or 'none'}",
        "",
        "## Outputs",
        f"- run_dir: {report['run_dir']}",
        f"- runbook: {report['runbook_path']}",
        f"- verification_script: {report['verification_script_path']}",
    ]
    verification_execution = report.get("verification_execution")
    if isinstance(verification_execution, dict):
        lines.extend(
            [
                "",
                "## Verification Execution",
                f"- overall_verdict: {verification_execution.get('overall_verdict', 'unknown')}",
                f"- report_path: {verification_execution.get('report_path', 'n/a')}",
            ]
        )
    gate_cycle_report = report.get("wp_gate_cycle_report")
    if isinstance(gate_cycle_report, dict):
        lines.extend(
            [
                "",
                "## WP Gate Cycle",
                f"- wp_gate_path: {gate_cycle_report.get('wp_gate_path', 'n/a')}",
                f"- dispatchable_packet_count: {gate_cycle_report.get('runtime_summary', {}).get('dispatchable_packet_count', 0)}",
            ]
        )
    if report.get("note"):
        lines.extend(["", "## Note", f"- {report['note']}"])
    return localize_phase3_packet_run_report("\n".join(lines) + "\n", output_locale)


def resolve_gate_test_report_path(verification_execution: dict[str, Any]) -> Path:
    for key in ("test_report_path", "unit_test_report_path"):
        candidate = str(verification_execution.get(key, "")).strip()
        if candidate and Path(candidate).exists():
            return Path(candidate).resolve()
    for key in ("test_report_path", "unit_test_report_path"):
        candidate = str(verification_execution.get(key, "")).strip()
        if candidate:
            return Path(candidate).resolve()
    raise ValueError("verification execution did not produce a gate-eligible test report")


def record_packet_event(
    *,
    execution_loop_plan_path: Path,
    output_dir: Path,
    worker_run_report_path: Path,
    packet: str,
    status: str,
    actor: str,
    note: str,
    evidence_ref: str,
    wp_gate_report_path: Path | None = None,
    runtime_environment_ledger_path: Path | None = None,
) -> None:
    run_runtime_cycle(
        execution_loop_plan_path=execution_loop_plan_path,
        output_dir=output_dir,
        worker_run_report_path=worker_run_report_path,
        wp_gate_report_path=wp_gate_report_path,
        runtime_environment_ledger_path=runtime_environment_ledger_path,
        record_packet=packet,
        record_status=status,
        note=note,
        evidence_ref=evidence_ref,
        actor=actor,
    )


def refresh_runtime(
    *,
    output_dir: Path,
    execution_loop_plan: dict[str, Any],
    worker_run_report_path: Path,
    wp_gate_report_path: Path | None = None,
    runtime_environment_ledger_path: Path | None = None,
) -> dict[str, Any]:
    emit_execution_dispatch_artifacts(
        execution_loop_plan=execution_loop_plan,
        output_dir=output_dir,
        worker_run_report=load_json_if_exists(worker_run_report_path),
        wp_gate_report=load_json_if_exists(wp_gate_report_path),
        runtime_environment_ledger=load_json_if_exists(runtime_environment_ledger_path),
    )
    return load_json(output_dir / "execution-runtime-state.json")


def run_worker_packet(
    *,
    output_dir: Path,
    packet: str | None = None,
    wave: int | None = None,
    lane: str | None = None,
    mode: str = "plan-only",
    actor: str = "",
    note: str = "",
    wp_gate_report_path: Path | None = None,
    runtime_environment_ledger_path: Path | None = None,
    allow_non_dispatchable: bool = False,
) -> dict[str, Any]:
    if mode not in RUN_MODES:
        raise ValueError(f"unsupported mode: {mode}")

    output_dir = output_dir.resolve()
    resolved_wp_gate_report_path = resolve_wp_gate_report_path(output_dir, wp_gate_report_path)
    resolved_runtime_environment_ledger_path = resolve_runtime_environment_ledger_path(
        output_dir,
        runtime_environment_ledger_path,
    )
    execution_loop_plan_path = output_dir / "execution-loop-plan.json"
    if not execution_loop_plan_path.exists():
        raise ValueError(f"execution loop plan missing: {execution_loop_plan_path}")

    execution_loop_plan = load_json(execution_loop_plan_path)
    worker_run_report_path = output_dir / "worker-run-report.json"
    runtime_state = refresh_runtime(
        output_dir=output_dir,
        execution_loop_plan=execution_loop_plan,
        worker_run_report_path=worker_run_report_path,
        wp_gate_report_path=resolved_wp_gate_report_path,
        runtime_environment_ledger_path=resolved_runtime_environment_ledger_path,
    )

    selected_packet = packet_id(packet=packet, wave=wave, lane=lane) if (packet or wave or lane) else ""
    if not selected_packet:
        dispatchable = sorted_dispatchable_packets(runtime_state)
        if not dispatchable:
            raise ValueError("no dispatchable packets available")
        selected_packet = str(dispatchable[0].get("packet_id", "")).strip()

    pre_runtime_row = current_runtime_row(runtime_state, selected_packet)
    if pre_runtime_row is None:
        raise ValueError(f"packet not found in runtime state: {selected_packet}")
    worker_run_report = load_json_if_exists(worker_run_report_path) or {}
    latest_status_by_packet = worker_run_report.get("latest_status_by_packet", {})
    if not isinstance(latest_status_by_packet, dict):
        latest_status_by_packet = {}
    latest_packet_status = str(latest_status_by_packet.get(selected_packet, {}).get("status", "")).strip()
    dispatchable_when_selected = pre_runtime_row.get("current_state") == "ready"
    if (
        not dispatchable_when_selected
        and pre_runtime_row.get("base_state") == "ready"
        and latest_packet_status not in {"started", "implemented", "blocked", "failed"}
    ):
        dispatchable_when_selected = True
    if not dispatchable_when_selected and not allow_non_dispatchable:
        raise ValueError(f"packet is not dispatchable: {selected_packet}")

    loop_row = execution_loop_row(execution_loop_plan, selected_packet)
    packet_document = load_worker_packet_document(output_dir, loop_row)
    run_dir = next_run_directory(output_dir, selected_packet)
    context_path = run_dir / "packet-context.json"
    runbook_path = run_dir / "execution-runbook.md"
    verification_script_path = run_dir / "verification-commands.sh"
    run_report_path = run_dir / "packet-run-report.json"
    run_report_md_path = run_dir / "packet-run-report.md"

    write_text(
        context_path,
        json.dumps(
            {
                "packet": packet_document,
                "pre_runtime_row": pre_runtime_row,
                "execution_loop_row": loop_row,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    write_text(runbook_path, build_runbook(packet_document, pre_runtime_row, mode))
    write_text(verification_script_path, build_verification_script(packet_document))

    recorded_statuses: list[str] = []
    verification_execution: dict[str, Any] | None = None
    wp_gate_cycle_report: dict[str, Any] | None = None
    actor_name = actor or "phase3-worker-packet-runner"
    evidence_ref = str(run_dir.relative_to(output_dir))

    if mode in {"execute-verification", "execute-and-apply-gate"}:
        record_packet_event(
            execution_loop_plan_path=execution_loop_plan_path,
            output_dir=output_dir,
            worker_run_report_path=worker_run_report_path,
            packet=selected_packet,
            status="started",
            actor=actor_name,
            note=note.strip() or "worker packet execution started",
            evidence_ref=evidence_ref,
            runtime_environment_ledger_path=resolved_runtime_environment_ledger_path,
        )
        recorded_statuses.append("started")
        verification_execution = run_verification_commands(
            packet_document=packet_document,
            workspace_root=output_dir,
            run_dir=run_dir,
        )
        record_verification_report(
            ledger_path=output_dir / "phase3-verification-ledger.json",
            verification_report_path=Path(verification_execution["report_path"]).resolve(),
        )
        if verification_execution["overall_verdict"] == "pass":
            record_packet_event(
                execution_loop_plan_path=execution_loop_plan_path,
                output_dir=output_dir,
                worker_run_report_path=worker_run_report_path,
                packet=selected_packet,
                status="implemented",
                actor=actor_name,
                note=note.strip() or "worker packet verification completed successfully",
                evidence_ref=evidence_ref,
                runtime_environment_ledger_path=resolved_runtime_environment_ledger_path,
            )
            recorded_statuses.append("implemented")
            if mode == "execute-and-apply-gate":
                from phase3.wp_gate_cycle import run_wp_gate_cycle

                wp_gate_cycle_report = run_wp_gate_cycle(
                    output_dir=output_dir,
                    test_report_path=resolve_gate_test_report_path(verification_execution),
                    lint_report_path=Path(verification_execution["lint_report_path"]).resolve(),
                    typecheck_report_path=Path(verification_execution["typecheck_report_path"]).resolve(),
                    build_report_path=Path(verification_execution["build_report_path"]).resolve(),
                    verification_ledger_path=output_dir / "phase3-verification-ledger.json",
                    runtime_environment_ledger_path=resolved_runtime_environment_ledger_path,
                )
                resolved_wp_gate_report_path = Path(wp_gate_cycle_report["wp_gate_path"]).resolve()
        else:
            failed_steps = [
                str(row.get("step", "")).strip()
                for row in verification_execution.get("steps", [])
                if str(row.get("verdict", "")).strip() == "fail"
            ]
            record_packet_event(
                execution_loop_plan_path=execution_loop_plan_path,
                output_dir=output_dir,
                worker_run_report_path=worker_run_report_path,
                packet=selected_packet,
                status="failed",
                actor=actor_name,
                note=note.strip() or f"verification failed: {', '.join(failed_steps) or 'unknown step'}",
                evidence_ref=evidence_ref,
                runtime_environment_ledger_path=resolved_runtime_environment_ledger_path,
            )
            recorded_statuses.append("failed")
    elif mode != "plan-only":
        for index, status in enumerate(RUN_MODES[mode]):
            event_note = note.strip()
            if not event_note:
                if status == "started":
                    event_note = "worker packet execution started"
                elif status == "implemented":
                    event_note = "worker packet reported implementation complete"
                elif status == "blocked":
                    event_note = "worker packet blocked during execution"
                else:
                    event_note = "worker packet execution failed"
            record_packet_event(
                execution_loop_plan_path=execution_loop_plan_path,
                output_dir=output_dir,
                worker_run_report_path=worker_run_report_path,
                packet=selected_packet,
                status=status,
                note=event_note if index == len(RUN_MODES[mode]) - 1 else f"{event_note} ({status})",
                evidence_ref=evidence_ref,
                actor=actor_name,
                wp_gate_report_path=resolved_wp_gate_report_path,
                runtime_environment_ledger_path=resolved_runtime_environment_ledger_path,
            )
            recorded_statuses.append(status)

    post_runtime_state = refresh_runtime(
        output_dir=output_dir,
        execution_loop_plan=execution_loop_plan,
        worker_run_report_path=worker_run_report_path,
        wp_gate_report_path=resolved_wp_gate_report_path,
        runtime_environment_ledger_path=resolved_runtime_environment_ledger_path,
    )
    post_runtime_row = current_runtime_row(post_runtime_state, selected_packet) or {}

    report = {
        "packet_id": selected_packet,
        "mode": mode,
        "actor": actor,
        "note": note,
        "dispatchable_when_selected": dispatchable_when_selected,
        "pre_runtime_row": pre_runtime_row,
        "post_runtime_row": post_runtime_row,
        "event_statuses_recorded": recorded_statuses,
        "verification_execution": verification_execution,
        "wp_gate_cycle_report": wp_gate_cycle_report,
        "run_dir": str(run_dir),
        "context_path": str(context_path),
        "runbook_path": str(runbook_path),
        "verification_script_path": str(verification_script_path),
        "worker_run_report_path": str(worker_run_report_path),
        "runtime_state_path": str(output_dir / "execution-runtime-state.json"),
        "dispatch_manifest_path": str(output_dir / "dispatch-manifest.json"),
    }
    write_text(run_report_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(run_report_md_path, build_packet_summary_markdown(report))
    return {
        "packet_id": selected_packet,
        "mode": mode,
        "dispatchable_when_selected": dispatchable_when_selected,
        "event_statuses_recorded": recorded_statuses,
        "verification_overall_verdict": verification_execution.get("overall_verdict", "") if verification_execution else "",
        "run_dir": str(run_dir),
        "run_report_path": str(run_report_path),
        "run_report_markdown_path": str(run_report_md_path),
        "post_state": post_runtime_row.get("current_state", "unknown"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Materialize or simulate one Phase-3 worker packet run")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--packet")
    parser.add_argument("--wave", type=int)
    parser.add_argument("--lane")
    parser.add_argument("--mode", choices=sorted(RUN_MODES), default="plan-only")
    parser.add_argument("--actor", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--wp-gate-report")
    parser.add_argument("--runtime-environment-ledger")
    parser.add_argument("--allow-non-dispatchable", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = run_worker_packet(
        output_dir=Path(args.output_dir).resolve(),
        packet=args.packet,
        wave=args.wave,
        lane=args.lane,
        mode=args.mode,
        actor=args.actor,
        note=args.note,
        wp_gate_report_path=Path(args.wp_gate_report).resolve() if args.wp_gate_report else None,
        runtime_environment_ledger_path=Path(args.runtime_environment_ledger).resolve()
        if args.runtime_environment_ledger
        else None,
        allow_non_dispatchable=args.allow_non_dispatchable,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
