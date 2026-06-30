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
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import signal
import shutil
import subprocess
import shlex
import time
from pathlib import Path
from typing import Any

from common.host_port_allocator import host_port_in_use
from phase3.execution_dispatch_state import (
    analyze_execution_dispatch,
    emit_execution_dispatch_artifacts,
    initial_packet_state,
    manifest_markdown,
    parse_runtime_environment_rows,
    parse_worker_run_report,
    parse_wp_gate_rows,
    row_reaches_unlock_ceiling,
    runtime_markdown,
    sorted_dispatchable_packets,
    wave_reaches_unlock_ceiling,
)
from phase3.execution_packet_access import (
    current_runtime_row,
    execution_loop_row,
    load_json,
    load_json_if_exists,
    load_worker_packet_document,
    resolve_wp_gate_report_path,
)
import phase3.execution_runtime_preflight as runtime_preflight
from phase3.review_support import write_json_and_markdown_report
import phase3.action_card_slice_orchestration as action_card_slice_orchestration
import phase3.runtime_cycle as runtime_cycle
import phase3.action_card_slice_run_manifest as action_card_slice_run_manifest
import phase3.verification_execution as verification_execution
import phase3.verification_ledger as verification_ledger
import phase3.worker_packet_artifacts as worker_packet_artifacts
import phase3.worker_run_report as worker_run_report


RUN_MODES = {
    "plan-only": [],
    "execute-batch": [],
    "execute-slices": [],
    "simulate-started": ["started"],
    "simulate-success": ["started", "implemented"],
    "simulate-blocked": ["started", "blocked"],
    "simulate-failed": ["started", "failed"],
    "execute-verification": ["started"],
    "execute-and-apply-gate": ["started"],
}

VALID_WORKER_RUN_STATUSES = {"started", "implemented", "blocked", "failed"}
LEGACY_TARGETED_STEP = verification_execution.LEGACY_TARGETED_STEP
CRITICAL_TARGETED_STEP = verification_execution.CRITICAL_TARGETED_STEP
FULL_TARGETED_STEP = verification_execution.FULL_TARGETED_STEP
VERIFICATION_STEP_NAMES = verification_execution.VERIFICATION_STEP_NAMES
REPORT_FILENAMES = verification_execution.REPORT_FILENAMES


def _env_positive_int(name: str, *, default: int) -> int:
    raw_value = str(os.environ.get(name) or "").strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(1, parsed)


def _env_bounded_int(name: str, *, default: int, minimum: int = 0, maximum: int = 3) -> int:
    raw_value = str(os.environ.get(name) or "").strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None or str(raw_value).strip() == "":
        return default
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


def default_action_card_runner_timeout_seconds() -> int:
    agent_timeout = _env_positive_int(
        "PHASE3_ACTION_CARD_AGENT_TIMEOUT_SECONDS",
        default=DEFAULT_ACTION_CARD_AGENT_TIMEOUT_SECONDS,
    )
    liveness_timeout = _env_positive_int(
        "PHASE3_ACTION_CARD_AGENT_LIVENESS_TIMEOUT_SECONDS",
        default=DEFAULT_ACTION_CARD_AGENT_LIVENESS_TIMEOUT_SECONDS,
    )
    command_timeout = _env_positive_int(
        "PHASE3_ACTION_CARD_COMMAND_TIMEOUT_SECONDS",
        default=DEFAULT_ACTION_CARD_COMMAND_TIMEOUT_SECONDS,
    )
    first_output_timeout = _env_positive_int(
        "PHASE3_ACTION_CARD_AGENT_FIRST_OUTPUT_TIMEOUT_SECONDS",
        default=DEFAULT_ACTION_CARD_AGENT_FIRST_OUTPUT_TIMEOUT_SECONDS,
    )
    first_progress_timeout = _env_positive_int(
        "PHASE3_ACTION_CARD_AGENT_FIRST_PROGRESS_TIMEOUT_SECONDS",
        default=DEFAULT_ACTION_CARD_AGENT_FIRST_PROGRESS_TIMEOUT_SECONDS,
    )
    repair_attempts = _env_bounded_int(
        "PHASE3_ACTION_CARD_REPAIR_MAX_ATTEMPTS",
        default=DEFAULT_ACTION_CARD_REPAIR_MAX_ATTEMPTS,
        minimum=0,
        maximum=3,
    )
    attempts = repair_attempts + 1
    fallback_models = [
        value.strip()
        for value in str(os.environ.get("PHASE3_ACTION_CARD_AGENT_FALLBACK_MODELS") or "").replace("\n", ",").split(",")
        if value.strip()
    ]
    liveness_attempts = 1 + len(dict.fromkeys(fallback_models))
    fallback_no_response_attempts = max(liveness_attempts - 1, 0)
    no_response_retry_attempts = liveness_attempts
    no_response_timeout = min(agent_timeout, max(first_output_timeout, first_progress_timeout))
    command_count = 2 if _env_flag("PHASE3_ACTION_CARD_RUN_PACKET_COMMANDS", default=False) else 1
    return (
        liveness_attempts * liveness_timeout
        + (fallback_no_response_attempts + no_response_retry_attempts) * no_response_timeout
        + attempts * (agent_timeout + command_count * command_timeout)
        + ACTION_CARD_RUNNER_TIMEOUT_OVERHEAD_SECONDS
    )


def resolve_action_card_runner_timeout_seconds() -> int:
    raw_value = str(os.environ.get("PHASE3_ACTION_CARD_RUNNER_TIMEOUT_SECONDS") or "").strip()
    if not raw_value:
        return default_action_card_runner_timeout_seconds()
    try:
        parsed = int(raw_value)
    except ValueError:
        return default_action_card_runner_timeout_seconds()
    return max(1, parsed)


def shell_executable() -> str:
    return shutil.which("zsh") or shutil.which("bash") or shutil.which("sh") or "/bin/sh"


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
DEFAULT_ACTION_CARD_AUTHORING_MAX_WORKERS = 3
MAX_ACTION_CARD_AUTHORING_MAX_WORKERS = 8
DEFAULT_ACTION_CARD_AGENT_TIMEOUT_SECONDS = 900
DEFAULT_ACTION_CARD_COMMAND_TIMEOUT_SECONDS = 900
DEFAULT_ACTION_CARD_AGENT_LIVENESS_TIMEOUT_SECONDS = 30
DEFAULT_ACTION_CARD_AGENT_FIRST_OUTPUT_TIMEOUT_SECONDS = 10
DEFAULT_ACTION_CARD_AGENT_FIRST_PROGRESS_TIMEOUT_SECONDS = 120
DEFAULT_ACTION_CARD_REPAIR_MAX_ATTEMPTS = 1
ACTION_CARD_RUNNER_TIMEOUT_OVERHEAD_SECONDS = 300
ACTION_CARD_RUNNER_PROTOCOL_VERSION = "action-card-runner/v1"
DEFAULT_ACTION_CARD_RUNNER_KIND = "generic"
ACTION_CARD_RUNNER_BOOTSTRAP_DIRNAME = "action-card-runner-bootstrap"
ACTION_CARD_RUNNER_BOOTSTRAP_CLAIM_CEILING = "bootstrap guidance only; not execution evidence"
ACTION_CARD_RUNNER_BOOTSTRAP_FILENAMES = (
    "runner-protocol.md",
    "capability-probe.md",
    "adapter-instructions.md",
    "result-schema.json",
)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def packet_slug(packet_id: str) -> str:
    return worker_packet_artifacts.packet_slug(packet_id)


def packet_id(*, wave: int | None = None, lane: str | None = None, packet: str | None = None) -> str:
    if packet:
        return packet.strip()
    if wave is None or lane is None or not str(lane).strip():
        raise ValueError("packet or wave+lane is required")
    return f"wave-{int(wave):02d}:{str(lane).strip()}"


def vitest_step_expected_tests(
    *,
    packet_document: dict[str, Any],
    step_name: str,
    step_reporting: dict[str, Any],
) -> list[str]:
    return verification_execution.vitest_step_expected_tests(
        packet_document=packet_document,
        step_name=step_name,
        step_reporting=step_reporting,
    )


def expand_env_tokens(value: str, env: dict[str, str]) -> str:
    return verification_execution.expand_env_tokens(value, env)


def resolve_path(raw_path: str, *, env: dict[str, str], workspace_root: Path) -> Path:
    return verification_execution.resolve_path(raw_path, env=env, workspace_root=workspace_root)


def looks_like_placeholder_command(command: str) -> bool:
    return verification_execution.looks_like_placeholder_command(command)


def extract_vitest_suite_paths(payload: dict[str, Any], *, workspace_root: Path) -> tuple[list[str], list[str], bool]:
    return verification_execution.extract_vitest_suite_paths(payload, workspace_root=workspace_root)


def evaluate_vitest_step(
    *,
    completed: subprocess.CompletedProcess[str],
    packet_tests: list[str],
    reporting: dict[str, Any],
    execution_env: dict[str, str],
    workspace_root: Path,
) -> dict[str, Any]:
    return verification_execution.evaluate_vitest_step(
        completed=completed,
        packet_tests=packet_tests,
        reporting=reporting,
        execution_env=execution_env,
        workspace_root=workspace_root,
    )


def build_verification_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    return verification_execution.build_verification_markdown(report, output_locale)


def build_execution_env(*, workspace_root: Path, run_dir: Path) -> dict[str, str]:
    return runtime_preflight.build_execution_env(workspace_root=workspace_root, run_dir=run_dir)


def clamp_step_timeout_seconds(value: int) -> int:
    return verification_execution.clamp_step_timeout_seconds(value)


def resolve_step_timeout_seconds() -> int:
    return verification_execution.resolve_step_timeout_seconds()


def command_tokens(command: str) -> list[str]:
    return verification_execution.command_tokens(command)


def command_option_int(tokens: list[str], option_name: str, default: int) -> int:
    return verification_execution.command_option_int(tokens, option_name, default)


def command_option_count(tokens: list[str], option_name: str) -> int:
    return verification_execution.command_option_count(tokens, option_name)


def resolve_effective_step_timeout_seconds(
    *,
    step_name: str,
    command: str,
    base_timeout_seconds: int,
) -> int:
    return verification_execution.resolve_effective_step_timeout_seconds(
        step_name=step_name,
        command=command,
        base_timeout_seconds=base_timeout_seconds,
    )


def timeout_output(value: Any) -> str:
    return verification_execution.timeout_output(value)


def run_shell_command(
    *,
    command: str,
    workspace_root: Path,
    execution_env: dict[str, str],
    timeout_seconds: int,
) -> tuple[subprocess.CompletedProcess[str], bool]:
    return verification_execution.run_shell_command(
        command=command,
        workspace_root=workspace_root,
        execution_env=execution_env,
        timeout_seconds=timeout_seconds,
        subprocess_run=subprocess.run,
        shell_resolver=shell_executable,
    )


def parse_env_file(path: Path) -> dict[str, str]:
    return runtime_preflight.parse_env_file(path)


def choose_postgres_host_port(
    *,
    workspace_root: Path,
    packet_id_value: str,
    starting_port: int | None = None,
    exclude_ports: set[int] | None = None,
) -> int:
    return runtime_preflight.choose_postgres_host_port(
        workspace_root=workspace_root,
        packet_id_value=packet_id_value,
        starting_port=starting_port,
        exclude_ports=exclude_ports,
        port_in_use_probe=host_port_in_use,
    )


def compose_project_name(*, workspace_root: Path, run_dir: Path | None = None) -> str:
    return runtime_preflight.compose_project_name(workspace_root=workspace_root, run_dir=run_dir)


def validate_runtime_compose_template(compose_path: Path) -> dict[str, Any]:
    return runtime_preflight.validate_runtime_compose_template(compose_path)


def backend_runtime_preflight_required(*, packet_document: dict[str, Any], workspace_root: Path) -> bool:
    return runtime_preflight.backend_runtime_preflight_required(
        packet_document=packet_document,
        workspace_root=workspace_root,
    )


def is_port_bind_conflict(stderr: str) -> bool:
    return runtime_preflight.is_port_bind_conflict(stderr)


def ensure_backend_runtime_preflight(
    *,
    packet_document: dict[str, Any],
    workspace_root: Path,
    execution_env: dict[str, str],
    run_dir: Path,
) -> dict[str, Any]:
    return runtime_preflight.ensure_backend_runtime_preflight(
        packet_document=packet_document,
        workspace_root=workspace_root,
        execution_env=execution_env,
        run_dir=run_dir,
        port_in_use_probe=host_port_in_use,
        subprocess_run=subprocess.run,
        shell_resolver=shell_executable,
        sleep_seconds=runtime_preflight.time.sleep,
    )


def teardown_backend_runtime_preflight(*, workspace_root: Path, execution_env: dict[str, str]) -> None:
    runtime_preflight.teardown_backend_runtime_preflight(
        workspace_root=workspace_root,
        execution_env=execution_env,
        subprocess_run=subprocess.run,
        shell_resolver=shell_executable,
    )


def build_step_duration_summary(step_reports: list[dict[str, Any]]) -> dict[str, Any]:
    return verification_execution.build_step_duration_summary(step_reports)


def resolve_verification_max_workers() -> int:
    return verification_execution.resolve_verification_max_workers()


def collect_verification_step_inputs(sequence: list[Any], commands: dict[str, Any]) -> list[dict[str, str]]:
    return verification_execution.collect_verification_step_inputs(sequence, commands)


def can_parallelize_verification_steps(step_inputs: list[dict[str, str]], max_workers: int) -> bool:
    return verification_execution.can_parallelize_verification_steps(step_inputs, max_workers)


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
    return verification_execution.execute_verification_step(
        step_name=step_name,
        command=command,
        packet_document=packet_document,
        reporting=reporting,
        workspace_root=workspace_root,
        run_dir=run_dir,
        execution_env=execution_env,
        step_timeout_seconds=step_timeout_seconds,
        subprocess_run=subprocess.run,
        shell_resolver=shell_executable,
    )


def run_verification_commands(
    *,
    packet_document: dict[str, Any],
    workspace_root: Path,
    run_dir: Path,
) -> dict[str, Any]:
    return verification_execution.run_verification_commands(
        packet_document=packet_document,
        workspace_root=workspace_root,
        run_dir=run_dir,
        shell_resolver=shell_executable,
        subprocess_run=subprocess.run,
        runtime_preflight_starter=ensure_backend_runtime_preflight,
        runtime_preflight_teardown=teardown_backend_runtime_preflight,
    )


def empty_worker_run_report() -> dict[str, Any]:
    return worker_run_report.empty_worker_run_report()


def ensure_worker_run_report(report_path: Path) -> dict[str, Any]:
    return worker_run_report.ensure_worker_run_report(report_path)


def build_worker_run_report_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    return worker_run_report.build_worker_run_report_markdown(report, output_locale)


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
    return worker_run_report.update_worker_run_report(
        report=report,
        packet=packet,
        status=status,
        note=note,
        evidence_ref=evidence_ref,
        actor=actor,
        at=at,
    )


def record_worker_run_event(
    *,
    report_path: Path,
    packet: str,
    status: str,
    note: str = "",
    evidence_ref: str = "",
    actor: str = "",
) -> dict[str, Any]:
    return worker_run_report.record_worker_run_event(
        report_path=report_path,
        packet=packet,
        status=status,
        note=note,
        evidence_ref=evidence_ref,
        actor=actor,
    )


def initialize_worker_run_report(report_path: Path) -> dict[str, Any]:
    return worker_run_report.initialize_worker_run_report(report_path)


def build_runtime_cycle_markdown(summary: dict[str, Any], output_locale: str | None = None) -> str:
    return runtime_cycle.build_runtime_cycle_markdown(summary, output_locale)


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
    return runtime_cycle.run_runtime_cycle(
        execution_loop_plan_path=execution_loop_plan_path,
        output_dir=output_dir,
        worker_run_report_path=worker_run_report_path,
        wp_gate_report_path=wp_gate_report_path,
        runtime_environment_ledger_path=runtime_environment_ledger_path,
        record_packet=record_packet,
        record_status=record_status,
        note=note,
        evidence_ref=evidence_ref,
        actor=actor,
    )



def empty_verification_ledger() -> dict[str, Any]:
    return verification_ledger.empty_verification_ledger()


def build_verification_ledger_markdown(ledger: dict[str, Any], output_locale: str | None = None) -> str:
    return verification_ledger.build_verification_ledger_markdown(ledger, output_locale)


def extract_step_verdicts(verification_report: dict[str, Any]) -> dict[str, str]:
    return verification_ledger.extract_step_verdicts(verification_report)


def extract_step_durations(verification_report: dict[str, Any]) -> dict[str, int]:
    return verification_ledger.extract_step_durations(verification_report)


def verification_entry_from_report(
    *,
    verification_report: dict[str, Any],
    verification_report_path: Path | None = None,
) -> dict[str, Any]:
    return verification_ledger.verification_entry_from_report(
        verification_report=verification_report,
        verification_report_path=verification_report_path,
    )


def update_verification_ledger(
    *,
    ledger: dict[str, Any],
    verification_report: dict[str, Any],
    verification_report_path: Path | None = None,
) -> dict[str, Any]:
    return verification_ledger.update_verification_ledger(
        ledger=ledger,
        verification_report=verification_report,
        verification_report_path=verification_report_path,
    )


def record_verification_report(
    *,
    ledger_path: Path,
    verification_report_path: Path,
) -> dict[str, Any]:
    return verification_ledger.record_verification_report(
        ledger_path=ledger_path,
        verification_report_path=verification_report_path,
    )


def synthesize_gate_inputs_from_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    return verification_ledger.synthesize_gate_inputs_from_ledger(ledger)


def resolve_runtime_environment_ledger_path(output_dir: Path, runtime_environment_ledger_path: Path | None) -> Path | None:
    if runtime_environment_ledger_path is not None:
        return runtime_environment_ledger_path.resolve()
    candidate = output_dir / "runtime-environment-ledger.json"
    return candidate if candidate.exists() else None


def next_run_directory(output_dir: Path, packet: str) -> Path:
    return worker_packet_artifacts.next_run_directory(output_dir, packet)


def build_done_criteria(packet_document: dict[str, Any]) -> list[str]:
    return worker_packet_artifacts.build_done_criteria(packet_document)


def build_verification_script(packet_document: dict[str, Any]) -> str:
    return worker_packet_artifacts.build_verification_script(packet_document)


def build_runbook(
    packet_document: dict[str, Any],
    runtime_row: dict[str, Any] | None,
    mode: str,
    output_locale: str | None = None,
) -> str:
    return worker_packet_artifacts.build_runbook(
        packet_document,
        runtime_row,
        mode,
        output_locale,
    )


def build_packet_summary_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    return worker_packet_artifacts.build_packet_summary_markdown(report, output_locale)


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


def resolve_action_card_authoring_max_workers() -> int:
    raw_value = str(
        os.environ.get("PHASE3_ACTION_CARD_AUTHORING_MAX_WORKERS")
        or os.environ.get("PHASE3_ACTION_CARD_SLICE_MAX_WORKERS")
        or ""
    ).strip()
    if not raw_value:
        return DEFAULT_ACTION_CARD_AUTHORING_MAX_WORKERS
    try:
        parsed = int(raw_value)
    except ValueError:
        return DEFAULT_ACTION_CARD_AUTHORING_MAX_WORKERS
    return max(1, min(parsed, MAX_ACTION_CARD_AUTHORING_MAX_WORKERS))


def resolve_action_card_slice_max_workers() -> int:
    return resolve_action_card_authoring_max_workers()


def resolve_action_card_runner_command() -> list[str]:
    command = str(
        os.environ.get("PHASE3_ACTION_CARD_RUNNER_CMD")
        or os.environ.get("PHASE3_ACTION_CARD_SLICE_RUNNER_CMD")
        or ""
    ).strip()
    if command:
        return shlex.split(command)
    if str(os.environ.get("PHASE3_ACTION_CARD_RUNNER_AUTO_DISCOVERY") or "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return []
    runner_path = Path(__file__).with_name("action_card_agent_runner.py")
    if runner_path.exists():
        return [sys.executable, str(runner_path)]
    return []


def resolve_action_card_batch_runner_command() -> list[str]:
    command = str(os.environ.get("PHASE3_ACTION_CARD_BATCH_RUNNER_CMD") or "").strip()
    return shlex.split(command) if command else []


def resolve_action_card_runner_kind() -> str:
    value = str(os.environ.get("PHASE3_ACTION_CARD_RUNNER_KIND") or DEFAULT_ACTION_CARD_RUNNER_KIND).strip()
    return value or DEFAULT_ACTION_CARD_RUNNER_KIND


def resolve_action_card_runner_protocol_version() -> str:
    return ACTION_CARD_RUNNER_PROTOCOL_VERSION


def resolve_action_card_slice_runner_command() -> list[str]:
    return resolve_action_card_runner_command()


def build_action_card_runner_result_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Action Card Runner Result",
        "type": "object",
        "required": [
            "slice_id",
            "status",
            "changed_files",
            "commands_run",
            "evidence_summary",
            "blockers",
            "claim_ceiling",
        ],
        "properties": {
            "slice_id": {
                "type": "string",
                "description": "Must match the slice packet slice_id.",
            },
            "status": {
                "type": "string",
                "enum": [
                    "implemented",
                    "blocked",
                    "failed",
                    "reviewed",
                    "read-only-reviewed",
                    "pass",
                    "passed",
                    "success",
                    "done",
                ],
            },
            "changed_files": {
                "type": "array",
                "items": {"type": "string"},
            },
            "commands_run": {
                "type": "array",
                "items": {"type": "string"},
            },
            "evidence_summary": {
                "type": "string",
            },
            "blockers": {
                "type": "array",
                "items": {"type": "string"},
            },
            "claim_ceiling": {
                "type": "string",
            },
        },
        "additionalProperties": True,
    }


def build_action_card_runner_protocol_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}
    slice_count = summary.get("slice_count", len(manifest.get("slice_runs", []) or []))
    return "\n".join(
        [
            "# Action Card Runner Protocol",
            "",
            f"- protocol_version: {resolve_action_card_runner_protocol_version()}",
            f"- preferred_batch_runner_command_env: PHASE3_ACTION_CARD_BATCH_RUNNER_CMD",
            f"- explicit_per_slice_runner_command_env: PHASE3_ACTION_CARD_RUNNER_CMD",
            f"- legacy_per_slice_runner_command_env: PHASE3_ACTION_CARD_SLICE_RUNNER_CMD",
            f"- optional_runner_kind_env: PHASE3_ACTION_CARD_RUNNER_KIND",
            f"- slice_count: {slice_count}",
            f"- claim_ceiling: {ACTION_CARD_RUNNER_BOOTSTRAP_CLAIM_CEILING}",
            "",
            "The preferred batch runner is invoked once per worker packet with these arguments:",
            "",
            "```text",
            "<batch-runner> --slice-manifest <path> --result-dir <path> --workspace-root <path> --run-dir <path> --max-workers <n>",
            "```",
            "",
            "If no batch runner is configured, WFF keeps the existing main-thread generation path authoritative and",
            "records packet-only fallback evidence rather than starting multiple per-slice CLI cold starts.",
            "",
            "For explicit compatibility or diagnostics, a per-slice runner may be invoked once per ready slice with",
            "these arguments:",
            "",
            "```text",
            "<runner> --slice-packet <path> --result <path> --workspace-root <path> --run-dir <path>",
            "```",
            "",
            "The runner owns implementation judgment inside the slice contract. WFF owns packet order, allowed edit",
            "boundaries, evidence capture, and claim ceilings.",
            "",
        ]
    )


def build_action_card_runner_capability_probe_markdown() -> str:
    return "\n".join(
        [
            "# Action Card Runner Capability Probe",
            "",
            "Before running slices, inspect the current agent/runtime capabilities:",
            "",
            "- Can this environment write files in the generated workspace?",
            "- Can it launch independent write-capable workers or subagents?",
            "- Can it create isolated worktrees or per-slice temporary copies when files might overlap?",
            "- Can it run the slice's red/green commands and capture command output?",
            "- Can it write the required result JSON to the provided `--result` path?",
            "",
            "Choose the strongest safe execution mode that the environment actually supports. If no mode can satisfy",
            "the protocol and evidence contract, return blocked rather than pretending execution happened.",
            "",
        ]
    )


def build_action_card_runner_adapter_instructions_markdown() -> str:
    return "\n".join(
        [
            "# Action Card Runner Adapter Instructions",
            "",
            f"Target protocol: {resolve_action_card_runner_protocol_version()}",
            "",
            "Set `PHASE3_ACTION_CARD_BATCH_RUNNER_CMD` to any executable adapter that accepts the batch protocol",
            "arguments and writes one standard result JSON per ready slice. `PHASE3_ACTION_CARD_RUNNER_KIND` is",
            "optional metadata only; WFF core must not depend on a specific Code Agent brand.",
            "",
            "If no batch runner command is supplied, WFF falls back to main-thread generation and records that no",
            "write-capable Action Card runner executed. The per-slice `PHASE3_ACTION_CARD_RUNNER_CMD` surface remains",
            "available only for explicit compatibility or diagnostics; it must not be auto-selected by the P3 mainline.",
            "",
            "For the bundled adapter, set `PHASE3_ACTION_CARD_AGENT_CMD` to the current environment's code-agent",
            "command. If unset, the adapter may auto-discover `codex exec` when available; disable that with",
            "`PHASE3_ACTION_CARD_AGENT_AUTO_DISCOVERY=0`. `PHASE3_ACTION_CARD_AGENT_MODEL` is an optional model hint.",
            "Codex auto-discovery preserves user config and user/project exec rules by default so SubAgent",
            "execution uses the same provider/auth/rule environment as the parent process. Set",
            "`PHASE3_ACTION_CARD_AGENT_IGNORE_USER_CONFIG=1` or `PHASE3_ACTION_CARD_AGENT_IGNORE_RULES=1`",
            "only for hermetic diagnostics.",
            "",
            "Supported capability modes:",
            "",
            "- direct-write: one write-capable agent executes the slice directly.",
            "- subagent-parallel: the adapter dispatches multiple independent write-capable workers for non-conflicting slices.",
            "- worktree-parallel: the adapter creates isolated worktrees or workspace copies, then merges compatible changes.",
            "- sequential: the adapter runs slices one at a time when parallel execution is unsafe.",
            "- manual-handoff: the adapter writes packets for a human or external tool and returns blocked until results exist.",
            "",
            "Hard rules:",
            "",
            "- Do not modify the protocol, slice packet boundaries, allowed edit files, or result schema to make a run look green.",
            "- Stay inside `allowed_edit_files` and packet-local test/evidence boundaries.",
            "- Run the listed red/green commands when available, and report commands that could not run.",
            "- If the environment cannot write, cannot isolate safely, or cannot produce evidence, return blocked.",
            "- Treat this bootstrap as guidance only; it is not execution evidence.",
            "",
        ]
    )


def write_action_card_runner_bootstrap(*, run_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    bootstrap_dir = run_dir / ACTION_CARD_RUNNER_BOOTSTRAP_DIRNAME
    files = {
        "runner-protocol.md": bootstrap_dir / "runner-protocol.md",
        "capability-probe.md": bootstrap_dir / "capability-probe.md",
        "adapter-instructions.md": bootstrap_dir / "adapter-instructions.md",
        "result-schema.json": bootstrap_dir / "result-schema.json",
    }
    write_text(files["runner-protocol.md"], build_action_card_runner_protocol_markdown(manifest))
    write_text(files["capability-probe.md"], build_action_card_runner_capability_probe_markdown())
    write_text(files["adapter-instructions.md"], build_action_card_runner_adapter_instructions_markdown())
    write_text(
        files["result-schema.json"],
        json.dumps(build_action_card_runner_result_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return {
        "protocol_version": resolve_action_card_runner_protocol_version(),
        "path": str(bootstrap_dir),
        "files": {name: str(path) for name, path in files.items()},
        "claim_ceiling": ACTION_CARD_RUNNER_BOOTSTRAP_CLAIM_CEILING,
    }


def build_blocked_slice_runner_result(*, slice_id: str, evidence_summary: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "slice_id": slice_id,
        "status": "blocked",
        "changed_files": [],
        "commands_run": [],
        "evidence_summary": evidence_summary,
        "blockers": blockers,
        "claim_ceiling": ACTION_CARD_RUNNER_BOOTSTRAP_CLAIM_CEILING,
    }


def execute_action_card_slice_runner(
    *,
    runner_command: list[str],
    slice_run: dict[str, Any],
    workspace_root: Path,
    run_dir: Path,
) -> dict[str, Any]:
    started_monotonic = time.monotonic()
    slice_id = str(slice_run.get("slice_id") or "slice").strip() or "slice"
    result_dir = run_dir / "slice-results"
    packet_dir = run_dir / "slice-packets"
    result_dir.mkdir(parents=True, exist_ok=True)
    packet_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", slice_id).strip("-") or "slice"
    packet_path = packet_dir / f"{safe_name}.json"
    result_path = result_dir / f"{safe_name}.result.json"
    packet_path.write_text(json.dumps(slice_run, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    command = [
        *runner_command,
        "--slice-packet",
        str(packet_path),
        "--result",
        str(result_path),
        "--workspace-root",
        str(workspace_root),
        "--run-dir",
        str(run_dir),
    ]
    timeout_seconds = resolve_action_card_runner_timeout_seconds()
    proc = subprocess.Popen(
        command,
        cwd=str(workspace_root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        returncode: int | str = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
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
        returncode = "timeout"
    result_payload: dict[str, Any] = {}
    malformed_result = False
    if result_path.exists():
        try:
            loaded = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            malformed_result = True
        else:
            if isinstance(loaded, dict):
                result_payload = loaded
            else:
                malformed_result = True
    if malformed_result and not timed_out:
        result_payload = build_blocked_slice_runner_result(
            slice_id=slice_id,
            evidence_summary="slice runner wrote malformed result JSON",
            blockers=["slice_runner_result_malformed"],
        )
        result_path.write_text(
            json.dumps(result_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if timed_out:
        timeout_blocker = f"slice_runner_timeout:{timeout_seconds}"
        if result_payload:
            blockers = list(result_payload.get("blockers") or [])
            if timeout_blocker not in blockers:
                blockers.append(timeout_blocker)
            result_payload = {
                **result_payload,
                "status": "blocked",
                "evidence_summary": (
                    f"{str(result_payload.get('evidence_summary') or '').strip()}; "
                    f"slice runner timed out after {timeout_seconds} seconds"
                ).strip("; "),
                "blockers": blockers,
                "claim_ceiling": ACTION_CARD_RUNNER_BOOTSTRAP_CLAIM_CEILING,
            }
        else:
            result_payload = build_blocked_slice_runner_result(
                slice_id=slice_id,
                evidence_summary=f"slice runner timed out after {timeout_seconds} seconds",
                blockers=[timeout_blocker],
            )
        result_path.write_text(
            json.dumps(result_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    status = str(result_payload.get("status") or "").strip().lower()
    if returncode == 0 and status in {"implemented", "pass", "passed", "success", "done"}:
        execution_state = "write-runner-executed"
    elif returncode == 0 and status in {"reviewed", "read-only-reviewed"}:
        execution_state = "read-only-reviewed"
    else:
        execution_state = "failed"
    duration_seconds = round(max(0.0, time.monotonic() - started_monotonic), 3)
    return {
        "slice_id": slice_id,
        "execution_state": execution_state,
        "result_path": str(result_path),
        "packet_path": str(packet_path),
        "returncode": returncode,
        "duration_seconds": duration_seconds,
        "stdout": (stdout or "")[-4000:],
        "stderr": (stderr or "")[-4000:],
        "result": result_payload,
    }


def _safe_slice_result_name(slice_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", slice_id).strip("-") or "slice"


def load_action_card_batch_result(
    *,
    result_path: Path,
    slice_id: str,
) -> dict[str, Any]:
    if not result_path.exists():
        return build_blocked_slice_runner_result(
            slice_id=slice_id,
            evidence_summary="batch runner did not write a result JSON for this slice",
            blockers=["batch_runner_result_missing"],
        )
    try:
        loaded = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return build_blocked_slice_runner_result(
            slice_id=slice_id,
            evidence_summary="batch runner wrote malformed result JSON for this slice",
            blockers=["batch_runner_result_malformed"],
        )
    if isinstance(loaded, dict):
        return loaded
    return build_blocked_slice_runner_result(
        slice_id=slice_id,
        evidence_summary="batch runner result JSON must be an object",
        blockers=["batch_runner_result_malformed"],
    )


def apply_batch_runner_process_failure(
    *,
    result_payload: dict[str, Any],
    slice_id: str,
    blocker: str,
    evidence_summary: str,
) -> dict[str, Any]:
    blockers = list(result_payload.get("blockers") or [])
    if blocker not in blockers:
        blockers.append(blocker)
    existing_summary = str(result_payload.get("evidence_summary") or "").strip()
    return {
        **result_payload,
        "slice_id": str(result_payload.get("slice_id") or slice_id),
        "status": "blocked",
        "evidence_summary": (
            f"{existing_summary}; {evidence_summary}" if existing_summary else evidence_summary
        ),
        "blockers": blockers,
        "claim_ceiling": ACTION_CARD_RUNNER_BOOTSTRAP_CLAIM_CEILING,
    }


def execute_action_card_batch_runner(
    *,
    runner_command: list[str],
    manifest: dict[str, Any],
    workspace_root: Path,
    run_dir: Path,
    active_authoring_max_workers: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started_monotonic = time.monotonic()
    result_dir = run_dir / "batch-slice-results"
    result_dir.mkdir(parents=True, exist_ok=True)
    batch_manifest_path = run_dir / "batch-slice-run-manifest.json"
    batch_manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    command = [
        *runner_command,
        "--slice-manifest",
        str(batch_manifest_path),
        "--result-dir",
        str(result_dir),
        "--workspace-root",
        str(workspace_root),
        "--run-dir",
        str(run_dir),
        "--max-workers",
        str(active_authoring_max_workers),
    ]
    timeout_seconds = resolve_action_card_runner_timeout_seconds()
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(workspace_root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        duration_seconds = round(max(0.0, time.monotonic() - started_monotonic), 3)
        return [], {
            "status": "fallback-to-main-thread",
            "command": command,
            "returncode": "startup-error",
            "duration_seconds": duration_seconds,
            "timeout_seconds": None,
            "manifest_path": str(batch_manifest_path),
            "result_dir": str(result_dir),
            "stdout": "",
            "stderr": str(exc),
            "reason": f"batch runner could not start: {type(exc).__name__}: {exc}",
        }
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        returncode: int | str = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
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
        returncode = "timeout"
    duration_seconds = round(max(0.0, time.monotonic() - started_monotonic), 3)
    batch_runner = {
        "status": "executed" if returncode == 0 and not timed_out else "failed",
        "command": command,
        "returncode": returncode,
        "duration_seconds": duration_seconds,
        "timeout_seconds": timeout_seconds if timed_out else None,
        "manifest_path": str(batch_manifest_path),
        "result_dir": str(result_dir),
        "stdout": (stdout or "")[-4000:],
        "stderr": (stderr or "")[-4000:],
    }
    execution_results: list[dict[str, Any]] = []
    ready_slices = [
        row
        for row in manifest.get("slice_runs", []) or []
        if isinstance(row, dict) and str(row.get("slice_status") or "").strip() == "ready"
    ]
    for slice_run in ready_slices:
        slice_id = str(slice_run.get("slice_id") or "slice").strip() or "slice"
        result_path = result_dir / f"{_safe_slice_result_name(slice_id)}.result.json"
        if result_path.exists():
            result_payload = load_action_card_batch_result(result_path=result_path, slice_id=slice_id)
        else:
            result_payload = build_blocked_slice_runner_result(
                slice_id=slice_id,
                evidence_summary=(
                    f"batch runner timed out after {timeout_seconds} seconds"
                    if timed_out
                    else f"batch runner failed with returncode {returncode}"
                    if returncode != 0
                    else "batch runner did not write a result JSON for this slice"
                ),
                blockers=[
                    f"batch_runner_timeout:{timeout_seconds}"
                    if timed_out
                    else f"batch_runner_failed:{returncode}"
                    if returncode != 0
                    else "batch_runner_result_missing"
                ],
            )
        if timed_out:
            result_payload = apply_batch_runner_process_failure(
                result_payload=result_payload,
                slice_id=slice_id,
                blocker=f"batch_runner_timeout:{timeout_seconds}",
                evidence_summary=f"batch runner timed out after {timeout_seconds} seconds",
            )
        elif returncode != 0:
            result_payload = apply_batch_runner_process_failure(
                result_payload=result_payload,
                slice_id=slice_id,
                blocker=f"batch_runner_failed:{returncode}",
                evidence_summary=f"batch runner failed with returncode {returncode}",
            )
        status = str(result_payload.get("status") or "").strip().lower()
        if returncode == 0 and not timed_out and status in {"implemented", "pass", "passed", "success", "done"}:
            execution_state = "write-runner-executed"
        elif returncode == 0 and not timed_out and status in {"reviewed", "read-only-reviewed"}:
            execution_state = "read-only-reviewed"
        else:
            execution_state = "failed"
        execution_results.append(
            {
                "slice_id": slice_id,
                "execution_state": execution_state,
                "result_path": str(result_path),
                "packet_path": str(batch_manifest_path),
                "returncode": returncode,
                "duration_seconds": duration_seconds,
                "stdout": (stdout or "")[-4000:],
                "stderr": (stderr or "")[-4000:],
                "result": result_payload,
            }
        )
    return execution_results, batch_runner


def apply_slice_execution_results(
    *,
    manifest: dict[str, Any],
    execution_results: list[dict[str, Any]],
    run_dir: Path,
    mode: str,
    runner_supported: bool,
    configured_authoring_max_workers: int | None = None,
    active_authoring_max_workers: int = 0,
) -> dict[str, Any]:
    if configured_authoring_max_workers is None:
        configured_authoring_max_workers = resolve_action_card_authoring_max_workers()
    configured_verification_max_workers = resolve_verification_max_workers()
    runner_kind = resolve_action_card_runner_kind()
    runner_protocol_version = resolve_action_card_runner_protocol_version()
    batch_runner_supported = mode == "execute-batch" and runner_supported
    slice_runner_supported = mode == "execute-slices" and runner_supported
    results_by_slice = {str(row.get("slice_id") or ""): row for row in execution_results}
    updated_slice_runs: list[dict[str, Any]] = []
    for slice_run in manifest.get("slice_runs", []) or []:
        if not isinstance(slice_run, dict):
            continue
        updated = dict(slice_run)
        result = results_by_slice.get(str(updated.get("slice_id") or ""))
        if result:
            updated["execution_state"] = result["execution_state"]
            result_path = Path(str(result.get("result_path") or ""))
            if result_path.exists() and result_path.is_relative_to(run_dir):
                updated["evidence_ref"] = str(result_path.relative_to(run_dir))
            else:
                updated["evidence_ref"] = str(result_path)
            updated["runner_returncode"] = result.get("returncode")
            if result["execution_state"] == "failed":
                reasons = list(updated.get("blocking_reasons") or [])
                reasons.append("slice_runner_failed")
                updated["blocking_reasons"] = reasons
                updated["slice_status"] = "blocked"
            result_payload = result.get("result", {}) if isinstance(result.get("result"), dict) else {}
            updated["runner_result"] = {
                "status": result_payload.get("status", ""),
                "changed_files": result_payload.get("changed_files", []),
                "commands_run": result_payload.get("commands_run", []),
                "evidence_summary": result_payload.get("evidence_summary", ""),
                "blockers": result_payload.get("blockers", []),
                "claim_ceiling": result_payload.get("claim_ceiling", ""),
            }
        updated_slice_runs.append(updated)
    ready_count = sum(1 for row in updated_slice_runs if row.get("slice_status") == "ready")
    blocked_count = sum(1 for row in updated_slice_runs if row.get("slice_status") == "blocked")
    actual_count = sum(
        1
        for row in updated_slice_runs
        if str(row.get("execution_state") or "not-started").strip() not in {"", "not-started"}
    )
    write_count = sum(1 for row in updated_slice_runs if row.get("execution_state") == "write-runner-executed")
    review_count = sum(1 for row in updated_slice_runs if row.get("execution_state") == "read-only-reviewed")
    batch_count = 1 if mode == "execute-batch" and runner_supported and execution_results else 0
    slice_durations = [
        float(row.get("duration_seconds") or 0.0)
        for row in execution_results
        if isinstance(row.get("duration_seconds"), (int, float))
    ]
    slowest_result = max(
        execution_results,
        key=lambda row: float(row.get("duration_seconds") or 0.0),
        default={},
    )
    summary = dict(manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {})
    packet_claim_ceiling = (
        action_card_slice_run_manifest.BLOCKED_PACKET_CLAIM_CEILING
        if blocked_count
        else action_card_slice_run_manifest.RUNNER_EXECUTED_PACKET_CLAIM_CEILING
        if write_count
        else action_card_slice_run_manifest.READY_PACKET_CLAIM_CEILING
        if updated_slice_runs
        else action_card_slice_run_manifest.empty_slice_run_summary()["packet_claim_ceiling"]
    )
    summary.update(
        {
            "ready_slice_count": ready_count,
            "blocked_slice_count": blocked_count,
            "actual_subagent_execution_count": actual_count,
            "write_runner_execution_count": write_count,
            "read_only_review_count": review_count,
            "slice_execution_mode": mode,
            "slice_runner_supported": slice_runner_supported,
            "action_card_runner_supported": runner_supported,
            "batch_runner_supported": batch_runner_supported,
            "batch_runner_execution_count": batch_count,
            "runner_protocol_version": runner_protocol_version,
            "runner_kind": runner_kind,
            "configured_authoring_max_workers": configured_authoring_max_workers,
            "active_authoring_max_workers": active_authoring_max_workers,
            "configured_verification_max_workers": configured_verification_max_workers,
            "slice_runner_duration_seconds": round(max(slice_durations), 3) if slice_durations else 0.0,
            "slice_runner_cumulative_duration_seconds": round(sum(slice_durations), 3),
            "slowest_slice_duration_seconds": round(float(slowest_result.get("duration_seconds") or 0.0), 3),
            "slowest_slice_id": str(slowest_result.get("slice_id") or ""),
            "overall_slice_run_status": "blocked" if blocked_count else ("ready" if updated_slice_runs else "not-applicable"),
            "packet_claim_ceiling": packet_claim_ceiling,
        }
    )
    manifest["slice_runs"] = updated_slice_runs
    manifest["summary"] = summary
    manifest["overall_slice_run_status"] = summary["overall_slice_run_status"]
    manifest["packet_claim_ceiling"] = packet_claim_ceiling
    manifest["slice_execution_results"] = execution_results
    return manifest


def annotate_slice_runner_configuration(
    *,
    manifest: dict[str, Any],
    mode: str,
    status: str,
    configured_authoring_max_workers: int | None = None,
    active_authoring_max_workers: int = 0,
    runner_supported: bool = False,
    reason: str = "",
    command: list[str] | None = None,
    selected_slice_count: int = 0,
) -> dict[str, Any]:
    if configured_authoring_max_workers is None:
        configured_authoring_max_workers = resolve_action_card_authoring_max_workers()
    configured_verification_max_workers = resolve_verification_max_workers()
    runner_kind = resolve_action_card_runner_kind()
    runner_protocol_version = resolve_action_card_runner_protocol_version()
    summary = dict(manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {})
    summary.update(
        {
            "slice_execution_mode": mode,
            "slice_runner_supported": mode == "execute-slices" and runner_supported,
            "action_card_runner_supported": runner_supported,
            "batch_runner_supported": mode == "execute-batch" and runner_supported,
            "batch_runner_execution_count": 0,
            "runner_protocol_version": runner_protocol_version,
            "runner_kind": runner_kind,
            "configured_authoring_max_workers": configured_authoring_max_workers,
            "active_authoring_max_workers": active_authoring_max_workers,
            "configured_verification_max_workers": configured_verification_max_workers,
        }
    )
    manifest["summary"] = summary
    runner: dict[str, Any] = {
        "status": status,
        "runner_protocol_version": runner_protocol_version,
        "runner_kind": runner_kind,
        "configured_authoring_max_workers": configured_authoring_max_workers,
        "active_authoring_max_workers": active_authoring_max_workers,
        "configured_verification_max_workers": configured_verification_max_workers,
        "selected_slice_count": selected_slice_count,
    }
    if reason:
        runner["reason"] = reason
    if command:
        runner["command"] = command
    manifest["action_card_runner"] = runner
    manifest["slice_runner"] = dict(runner)
    manifest["batch_runner"] = dict(runner)
    return manifest


def maybe_execute_action_card_slices(
    *,
    manifest: dict[str, Any],
    output_dir: Path,
    run_dir: Path,
    mode: str,
) -> dict[str, Any]:
    configured_authoring_max_workers = resolve_action_card_authoring_max_workers()
    if mode == "execute-batch":
        batch_runner_command = resolve_action_card_batch_runner_command()
        slice_runs = [
            row
            for row in manifest.get("slice_runs", []) or []
            if isinstance(row, dict) and str(row.get("slice_status") or "").strip() == "ready"
        ]
        if not batch_runner_command:
            annotate_slice_runner_configuration(
                manifest=manifest,
                mode=mode,
                status="fallback-to-main-thread",
                configured_authoring_max_workers=configured_authoring_max_workers,
                active_authoring_max_workers=0,
                runner_supported=False,
                reason="PHASE3_ACTION_CARD_BATCH_RUNNER_CMD is not set; main thread generation remains authoritative",
                selected_slice_count=len(slice_runs),
            )
            return apply_slice_execution_results(
                manifest=manifest,
                execution_results=[],
                run_dir=run_dir,
                mode=mode,
                runner_supported=False,
                configured_authoring_max_workers=configured_authoring_max_workers,
                active_authoring_max_workers=0,
            )
        if not slice_runs:
            annotate_slice_runner_configuration(
                manifest=manifest,
                mode=mode,
                status="no-ready-slices",
                configured_authoring_max_workers=configured_authoring_max_workers,
                active_authoring_max_workers=0,
                runner_supported=True,
                command=batch_runner_command,
                selected_slice_count=0,
            )
            return apply_slice_execution_results(
                manifest=manifest,
                execution_results=[],
                run_dir=run_dir,
                mode=mode,
                runner_supported=True,
                configured_authoring_max_workers=configured_authoring_max_workers,
                active_authoring_max_workers=0,
            )
        max_workers = min(configured_authoring_max_workers, max(1, len(slice_runs)))
        execution_results, batch_runner = execute_action_card_batch_runner(
            runner_command=batch_runner_command,
            manifest=manifest,
            workspace_root=output_dir,
            run_dir=run_dir,
            active_authoring_max_workers=max_workers,
        )
        runner_supported = batch_runner.get("status") != "fallback-to-main-thread"
        annotate_slice_runner_configuration(
            manifest=manifest,
            mode=mode,
            status=batch_runner["status"],
            configured_authoring_max_workers=configured_authoring_max_workers,
            active_authoring_max_workers=max_workers if runner_supported else 0,
            runner_supported=runner_supported,
            command=batch_runner_command,
            selected_slice_count=len(slice_runs),
        )
        manifest = apply_slice_execution_results(
            manifest=manifest,
            execution_results=execution_results,
            run_dir=run_dir,
            mode=mode,
            runner_supported=runner_supported,
            configured_authoring_max_workers=configured_authoring_max_workers,
            active_authoring_max_workers=max_workers if runner_supported else 0,
        )
        manifest["batch_runner"] = {
            **dict(manifest.get("batch_runner", {}) if isinstance(manifest.get("batch_runner"), dict) else {}),
            **batch_runner,
        }
        summary = dict(manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {})
        summary["slice_runner_duration_seconds"] = batch_runner["duration_seconds"]
        manifest["summary"] = summary
        return manifest
    if mode != "execute-slices":
        return annotate_slice_runner_configuration(
            manifest=manifest,
            mode=mode,
            status="not-requested",
            configured_authoring_max_workers=configured_authoring_max_workers,
        )
    runner_command = resolve_action_card_runner_command()
    if not runner_command:
        annotate_slice_runner_configuration(
            manifest=manifest,
            mode=mode,
            status="unsupported",
            configured_authoring_max_workers=configured_authoring_max_workers,
            reason="PHASE3_ACTION_CARD_RUNNER_CMD is not set",
        )
        return apply_slice_execution_results(
            manifest=manifest,
            execution_results=[],
            run_dir=run_dir,
            mode=mode,
            runner_supported=False,
            configured_authoring_max_workers=configured_authoring_max_workers,
            active_authoring_max_workers=0,
        )
    slice_runs = [
        row
        for row in manifest.get("slice_runs", []) or []
        if isinstance(row, dict) and str(row.get("slice_status") or "").strip() == "ready"
    ]
    if not slice_runs:
        annotate_slice_runner_configuration(
            manifest=manifest,
            mode=mode,
            status="no-ready-slices",
            configured_authoring_max_workers=configured_authoring_max_workers,
            active_authoring_max_workers=0,
            runner_supported=True,
            command=runner_command,
            selected_slice_count=0,
        )
        return apply_slice_execution_results(
            manifest=manifest,
            execution_results=[],
            run_dir=run_dir,
            mode=mode,
            runner_supported=True,
            configured_authoring_max_workers=configured_authoring_max_workers,
            active_authoring_max_workers=0,
        )
    max_workers = min(configured_authoring_max_workers, max(1, len(slice_runs)))
    execution_started_monotonic = time.monotonic()
    execution_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                execute_action_card_slice_runner,
                runner_command=runner_command,
                slice_run=slice_run,
                workspace_root=output_dir,
                run_dir=run_dir,
            )
            for slice_run in slice_runs
        ]
        for future in as_completed(futures):
            execution_results.append(future.result())
    annotate_slice_runner_configuration(
        manifest=manifest,
        mode=mode,
        status="executed",
        configured_authoring_max_workers=configured_authoring_max_workers,
        active_authoring_max_workers=max_workers,
        runner_supported=True,
        command=runner_command,
        selected_slice_count=len(slice_runs),
    )
    manifest = apply_slice_execution_results(
        manifest=manifest,
        execution_results=execution_results,
        run_dir=run_dir,
        mode=mode,
        runner_supported=True,
        configured_authoring_max_workers=configured_authoring_max_workers,
        active_authoring_max_workers=max_workers,
    )
    duration_seconds = round(max(0.0, time.monotonic() - execution_started_monotonic), 3)
    summary = dict(manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {})
    summary["slice_runner_duration_seconds"] = duration_seconds
    manifest["summary"] = summary
    if isinstance(manifest.get("action_card_runner"), dict):
        manifest["action_card_runner"]["duration_seconds"] = duration_seconds
    if isinstance(manifest.get("slice_runner"), dict):
        manifest["slice_runner"]["duration_seconds"] = duration_seconds
    return manifest


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
    slice_run_manifest_path = run_dir / "subagent-slice-run-manifest.json"
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
    slice_run_manifest_paths: dict[str, str] = {}
    slice_run_summary = action_card_slice_run_manifest.empty_slice_run_summary()
    action_card_runner_bootstrap: dict[str, Any] = {}
    slice_orchestration_report_paths: dict[str, str] = {}
    slice_orchestration_summary = {
        "packet_count": 0,
        "slice_count": 0,
        "ready_slice_count": 0,
        "blocked_slice_count": 0,
        "conflict_count": 0,
        "missing_evidence_count": 0,
        "overall_orchestration_gate": "not-applicable",
    }
    slice_packets = packet_document.get("subagent_slice_packets", [])
    if packet_document.get("lane") == "backend" and isinstance(slice_packets, list) and slice_packets:
        slice_run_manifest = action_card_slice_run_manifest.build_slice_run_manifest(
            packet_document=packet_document,
            packet_id=selected_packet,
            run_dir=run_dir,
            mode=mode,
        )
        action_card_runner_bootstrap = write_action_card_runner_bootstrap(
            run_dir=run_dir,
            manifest=slice_run_manifest,
        )
        slice_run_manifest["action_card_runner_bootstrap"] = action_card_runner_bootstrap
        slice_run_manifest = maybe_execute_action_card_slices(
            manifest=slice_run_manifest,
            output_dir=output_dir,
            run_dir=run_dir,
            mode=mode,
        )
        slice_run_manifest_paths = action_card_slice_run_manifest.write_slice_run_manifest(
            json_path=slice_run_manifest_path,
            manifest=slice_run_manifest,
        )
        slice_run_summary = dict(slice_run_manifest.get("summary", {}))

    if slice_run_manifest_paths or action_card_slice_orchestration.discover_slice_run_manifests(output_dir):
        slice_orchestration_report = action_card_slice_orchestration.build_slice_orchestration_report(output_dir)
        slice_orchestration_report_paths = action_card_slice_orchestration.write_slice_orchestration_report(output_dir)
        slice_orchestration_summary = dict(slice_orchestration_report.get("summary", {}))

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
        "subagent_slice_run_manifest_path": slice_run_manifest_paths.get("json_path", ""),
        "subagent_slice_run_manifest_markdown_path": slice_run_manifest_paths.get("markdown_path", ""),
        "subagent_slice_run_summary": slice_run_summary,
        "action_card_runner_bootstrap_path": action_card_runner_bootstrap.get("path", ""),
        "action_card_runner_bootstrap": action_card_runner_bootstrap,
        "subagent_slice_orchestration_report_path": slice_orchestration_report_paths.get("json_path", ""),
        "subagent_slice_orchestration_report_markdown_path": slice_orchestration_report_paths.get("markdown_path", ""),
        "subagent_slice_orchestration_summary": slice_orchestration_summary,
        "worker_run_report_path": str(worker_run_report_path),
        "runtime_state_path": str(output_dir / "execution-runtime-state.json"),
        "dispatch_manifest_path": str(output_dir / "dispatch-manifest.json"),
    }
    write_json_and_markdown_report(
        json_path=run_report_path,
        report=report,
        markdown=build_packet_summary_markdown(report),
        markdown_path=run_report_md_path,
    )
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
