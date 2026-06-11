from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase3.worker_packet_runner import (
    emit_execution_dispatch_artifacts,
    execution_loop_row,
    load_json,
    load_json_if_exists,
    load_worker_packet_document,
    manifest_markdown,
    requires_toolchain_bootstrap,
    resolve_wp_gate_report_path,
    runtime_markdown,
    sorted_dispatchable_packets,
)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def resolve_runtime_environment_ledger_path(output_dir: Path, runtime_environment_ledger_path: Path | None) -> Path | None:
    if runtime_environment_ledger_path is not None:
        return runtime_environment_ledger_path.resolve()
    candidate = output_dir / "runtime-environment-ledger.json"
    return candidate if candidate.exists() else None


def refresh_runtime_environment_ledger_if_present(
    output_dir: Path,
    runtime_environment_ledger_path: Path | None,
    *,
    refresh_runtime_environment_ledger_fn,
) -> Path | None:
    if runtime_environment_ledger_path is not None:
        return runtime_environment_ledger_path.resolve()
    resolved_path = resolve_runtime_environment_ledger_path(output_dir, None)
    existing_ledger = load_json_if_exists(resolved_path)
    if resolved_path is not None and isinstance(existing_ledger, dict):
        if "available_runtime_environments" not in existing_ledger and "summary" not in existing_ledger:
            return resolved_path
    if resolved_path is not None:
        execution_loop_plan_path = output_dir / "execution-loop-plan.json"
        if not execution_loop_plan_path.exists():
            return resolved_path
        refresh_runtime_environment_ledger_fn(
            execution_loop_plan_path=execution_loop_plan_path,
            output_dir=output_dir,
            output_path=resolved_path,
        )
        return resolved_path
    return None


def refresh_execution_dispatch_state(
    *,
    output_dir: Path,
    wp_gate_report_path: Path | None,
    runtime_environment_ledger_path: Path | None,
    refresh_runtime_environment_ledger_fn,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path | None]:
    resolved_wp_gate_report_path = resolve_wp_gate_report_path(output_dir, wp_gate_report_path)
    resolved_runtime_environment_ledger_path = refresh_runtime_environment_ledger_if_present(
        output_dir,
        runtime_environment_ledger_path,
        refresh_runtime_environment_ledger_fn=refresh_runtime_environment_ledger_fn,
    )
    execution_loop_plan_path = output_dir / "execution-loop-plan.json"
    if not execution_loop_plan_path.exists():
        raise ValueError(f"execution loop plan missing: {execution_loop_plan_path}")

    execution_loop_plan = load_json(execution_loop_plan_path)
    dispatch_summary = emit_execution_dispatch_artifacts(
        execution_loop_plan=execution_loop_plan,
        output_dir=output_dir,
        worker_run_report=load_json_if_exists(output_dir / "worker-run-report.json"),
        wp_gate_report=load_json_if_exists(resolved_wp_gate_report_path),
        runtime_environment_ledger=load_json_if_exists(resolved_runtime_environment_ledger_path),
    )
    runtime_state = load_json(output_dir / "execution-runtime-state.json")
    return execution_loop_plan, dispatch_summary, runtime_state, resolved_runtime_environment_ledger_path


def packet_requires_toolchain_bootstrap(packet_document: dict[str, Any]) -> bool:
    verification = packet_document.get("verification_commands", {})
    if not isinstance(verification, dict):
        return False
    commands = verification.get("commands", {})
    sequence = verification.get("sequence", [])
    if not isinstance(commands, dict) or not isinstance(sequence, list):
        return False
    for step in sequence:
        step_name = str(step).strip()
        if not step_name:
            continue
        command = str(commands.get(step_name, "")).strip()
        if command and requires_toolchain_bootstrap(command):
            return True
    return False


def evaluate_dispatch_preflight(
    *,
    output_dir: Path,
    execution_loop_plan: dict[str, Any],
    dispatchable_rows: list[dict[str, Any]],
    max_packets: int,
    bootstrap_phase3_toolchain_fn,
) -> dict[str, Any]:
    selected_packet_count = max(0, max_packets)
    if selected_packet_count <= 0:
        return {"status": "not-needed", "selected_packets": []}

    selected_packets: list[str] = []
    for row in dispatchable_rows[:selected_packet_count]:
        packet_id = str(row.get("packet_id", "")).strip()
        if not packet_id:
            continue
        loop_row = execution_loop_row(execution_loop_plan, packet_id)
        packet_document = load_worker_packet_document(output_dir, loop_row)
        if packet_requires_toolchain_bootstrap(packet_document):
            selected_packets.append(packet_id)

    if not selected_packets:
        return {"status": "not-needed", "selected_packets": []}

    bootstrap_report_path = output_dir / "phase3-toolchain-bootstrap.json"
    bootstrap_report = bootstrap_phase3_toolchain_fn(
        workspace_root=output_dir,
        install=False,
        output_path=bootstrap_report_path,
    )
    if bootstrap_report.get("overall_status") == "ready":
        return {
            "status": "ready",
            "selected_packets": selected_packets,
            "bootstrap_report_path": str(bootstrap_report_path),
            "bootstrap_command": str(bootstrap_report.get("bootstrap_command", "")),
        }

    return {
        "status": "blocked",
        "selected_packets": selected_packets,
        "reason": "toolchain_bootstrap_required_before_dispatch",
        "toolchain_status": str(bootstrap_report.get("overall_status", "unknown")),
        "bootstrap_report_path": str(bootstrap_report_path),
        "bootstrap_command": str(bootstrap_report.get("bootstrap_command", "")),
    }


def row_reaches_unlock_ceiling(row: dict[str, Any]) -> bool:
    return str(row.get("current_state", "")).strip() == "verified" or (
        str(row.get("current_state", "")).strip() == "implemented"
        and (
            str(row.get("wp_gate_rollup", "")).strip() == "runtime-blocked"
            or not bool(row.get("runtime_environment_available", True))
        )
    )


def wave_reaches_unlock_ceiling(rows: list[dict[str, Any]], wave: int) -> bool:
    wave_rows = [row for row in rows if int(row.get("wave", 0) or 0) == wave]
    return bool(wave_rows) and all(row_reaches_unlock_ceiling(row) for row in wave_rows)


def wave_is_fully_verified(rows: list[dict[str, Any]], wave: int) -> bool:
    wave_rows = [row for row in rows if int(row.get("wave", 0) or 0) == wave]
    return bool(wave_rows) and all(str(row.get("current_state", "")).strip() == "verified" for row in wave_rows)


def persist_runtime_state(output_dir: Path, runtime_state: dict[str, Any]) -> None:
    rows = [row for row in runtime_state.get("rows", []) if isinstance(row, dict)]
    dispatchable_packets = sorted_dispatchable_packets(runtime_state)
    runtime_state["dispatchable_packets"] = dispatchable_packets
    runtime_state["summary"] = {
        "packet_count": len(rows),
        "dispatchable_packet_count": len(dispatchable_packets),
        "ready_packet_count": sum(1 for row in rows if str(row.get("current_state", "")) == "ready"),
        "queued_packet_count": sum(1 for row in rows if str(row.get("current_state", "")) == "queued"),
        "in_progress_packet_count": sum(1 for row in rows if str(row.get("current_state", "")) == "in-progress"),
        "implemented_packet_count": sum(1 for row in rows if str(row.get("current_state", "")) == "implemented"),
        "verified_packet_count": sum(1 for row in rows if str(row.get("current_state", "")) == "verified"),
        "blocked_packet_count": sum(1 for row in rows if str(row.get("current_state", "")) == "blocked"),
        "current_dispatch_wave": min((int(row.get("wave", 0) or 0) for row in dispatchable_packets), default=None),
    }
    runtime_state_path = output_dir / "execution-runtime-state.json"
    manifest_path = output_dir / "dispatch-manifest.json"
    write_text(runtime_state_path, json.dumps(runtime_state, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(
        manifest_path,
        json.dumps({"dispatchable_packets": dispatchable_packets}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    write_text(output_dir / "execution-runtime-state.md", runtime_markdown(runtime_state))
    write_text(output_dir / "dispatch-manifest.md", manifest_markdown(runtime_state))


def cap_frontend_packet_unlocked_by_runtime_ceiling(
    output_dir: Path,
    runtime_state: dict[str, Any],
    current_row: dict[str, Any],
) -> bool:
    if str(current_row.get("lane", "")).strip() != "frontend":
        return False
    if str(current_row.get("current_state", "")).strip() != "ready":
        return False
    current_wave = int(current_row.get("wave", 0) or 0)
    if current_wave <= 1:
        return False
    rows = [row for row in runtime_state.get("rows", []) if isinstance(row, dict)]
    prior_waves = sorted({int(row.get("wave", 0) or 0) for row in rows if int(row.get("wave", 0) or 0) < current_wave})
    if not prior_waves:
        return False
    if not all(wave_reaches_unlock_ceiling(rows, wave) for wave in prior_waves):
        return False
    if all(wave_is_fully_verified(rows, wave) for wave in prior_waves):
        return False
    current_row["current_state"] = "implemented"
    current_row["wp_gate_rollup"] = "runtime-blocked"
    current_row["dispatch_decision"] = "await-runtime-environment"
    persist_runtime_state(output_dir, runtime_state)
    return True
