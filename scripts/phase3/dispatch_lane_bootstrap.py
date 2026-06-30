from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase3.execution_loop_builder import build_execution_loop, build_work_package_packets, build_work_package_wave_plan
from phase3.runtime_cycle import run_runtime_cycle
from phase3.runtime_environment import detect_current_available_runtime_environments, generate_runtime_environment_ledger
from phase3.worker_run_report import initialize_worker_run_report
from phase3.worker_packet_runner import (
    emit_execution_dispatch_artifacts,
    resolve_action_card_batch_runner_command,
    run_worker_packet,
)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_not_requested_summary() -> dict[str, object]:
    return {"mode": "not-requested"}


def subagent_execution_summary(
    *,
    request: str,
    enabled: bool,
    subagent_slice_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    if not enabled:
        return {
            "request": request,
            "mode": "centralized-fallback",
            "status": "disabled",
            "runner_supported": False,
            "claim_ceiling": (
                "centralized mainline evidence only; no per-Action-Card implementation claim"
            ),
        }
    slice_summary = subagent_slice_summary if isinstance(subagent_slice_summary, dict) else {}
    runner_supported = bool(
        slice_summary.get("action_card_runner_supported", False)
        or slice_summary.get("slice_runner_supported", False)
    )
    actual_execution_count = int(slice_summary.get("actual_subagent_execution_count", 0) or 0)
    write_runner_execution_count = int(slice_summary.get("write_runner_execution_count", 0) or 0)
    blocked_slice_count = int(slice_summary.get("blocked_slice_count", 0) or 0)
    overall_slice_run_status = str(slice_summary.get("overall_slice_run_status", "") or "").strip()
    slice_execution_mode = str(slice_summary.get("slice_execution_mode", "") or "").strip()
    if runner_supported and blocked_slice_count:
        return {
            "request": request,
            "mode": "write-runner" if write_runner_execution_count else "runner-attempted",
            "status": "runner-executed-with-blocked-slices",
            "runner_supported": True,
            "blocked_slice_count": blocked_slice_count,
            "overall_slice_run_status": overall_slice_run_status or "blocked",
            "claim_ceiling": (
                "Action Card runner execution recorded at least one blocked Action Card slice; "
                "do not claim full per-Action-Card implementation completion until blocked slices are resolved"
            ),
        }
    if runner_supported and write_runner_execution_count:
        return {
            "request": request,
            "mode": "write-runner",
            "status": "runner-executed",
            "runner_supported": True,
            "blocked_slice_count": blocked_slice_count,
            "overall_slice_run_status": overall_slice_run_status or "ready",
            "claim_ceiling": (
                "Action Card slice runner execution evidence is recorded; claim remains bounded to "
                "slice-level implementation artifacts and does not replace full P3 runtime verification"
            ),
        }
    if runner_supported and actual_execution_count:
        return {
            "request": request,
            "mode": "runner-attempted",
            "status": "runner-attempted-no-write-success",
            "runner_supported": True,
            "blocked_slice_count": blocked_slice_count,
            "overall_slice_run_status": overall_slice_run_status or "unknown",
            "claim_ceiling": (
                "Action Card runner attempts were recorded, but no successful write-runner execution evidence exists"
            ),
        }
    if runner_supported:
        return {
            "request": request,
            "mode": "write-runner",
            "status": "runner-supported-no-ready-slices",
            "runner_supported": True,
            "blocked_slice_count": blocked_slice_count,
            "overall_slice_run_status": overall_slice_run_status or "not-applicable",
            "claim_ceiling": (
                "Action Card runner is configured, but no ready slice execution evidence was recorded"
            ),
        }
    if slice_execution_mode == "execute-slices":
        return {
            "request": request,
            "mode": "runner-requested",
            "status": "runner-unsupported",
            "runner_supported": False,
            "claim_ceiling": (
                "Action Card slice execution was requested, but no write-capable runner recorded execution evidence"
            ),
        }
    return {
        "request": request,
        "mode": "packet-only-fallback",
        "status": "runner-unsupported",
        "runner_supported": False,
        "claim_ceiling": (
            "dispatch packets and Action Card slice manifests are prepared; "
            "no per-Action-Card implementation claim until a write-capable Action Card runner records execution evidence"
        ),
    }


def select_bootstrap_worker_packet_run_mode() -> str:
    return "execute-batch" if resolve_action_card_batch_runner_command() else "plan-only"


def empty_subagent_slice_summary() -> dict[str, object]:
    return {
        "slice_count": 0,
        "ready_slice_count": 0,
        "blocked_slice_count": 0,
        "actual_subagent_execution_count": 0,
        "write_runner_execution_count": 0,
        "read_only_review_count": 0,
        "slice_execution_mode": "not-applicable",
        "slice_runner_supported": False,
        "action_card_runner_supported": False,
        "batch_runner_supported": False,
        "batch_runner_execution_count": 0,
        "runner_protocol_version": "action-card-runner/v1",
        "runner_kind": "generic",
        "configured_authoring_max_workers": 0,
        "active_authoring_max_workers": 0,
        "configured_verification_max_workers": 0,
    }


def select_bootstrap_worker_packet(execution_loop_plan: dict[str, object]) -> tuple[int, str]:
    candidates: list[tuple[int, int, int, int, str]] = []
    for wave_row in execution_loop_plan.get("waves", []):
        if not isinstance(wave_row, dict):
            continue
        wave = int(wave_row.get("wave", 0) or 0)
        for packet in wave_row.get("worker_packets", []):
            if not isinstance(packet, dict):
                continue
            lane = str(packet.get("lane", "")).strip()
            if not lane:
                continue
            status = str(packet.get("worker_packet_status", "")).strip()
            dispatch_state = str(packet.get("dispatch_state", "")).strip()
            candidates.append(
                (
                    0 if status == "ready" else 1,
                    0 if dispatch_state == "ready-now" else 1,
                    wave,
                    0 if lane == "backend" else 1,
                    lane,
                )
            )
    if not candidates:
        raise ValueError("no bootstrap worker packets available")
    _, _, wave, _, lane = sorted(candidates)[0]
    return wave, lane


def initialize_optional_dispatch_lane(
    *,
    enabled: bool,
    esp_text: str,
    stage_03_text: str,
    stage_04_text: str,
    spec: dict[str, object],
    implementation_bindings: dict[str, object],
    output_dir: Path,
    toolchain_bootstrap_path: Path,
    dispatch_lane_mode: str = "auto",
) -> dict[str, object]:
    request = "disabled" if not enabled else ("enabled" if dispatch_lane_mode == "enabled" else "auto")
    lane_state = {
        "wp_packet_summary": make_not_requested_summary(),
        "wp_wave_summary": make_not_requested_summary(),
        "execution_loop_summary": make_not_requested_summary(),
        "execution_dispatch_summary": make_not_requested_summary(),
        "worker_run_report_summary": make_not_requested_summary(),
        "bootstrap_worker_run_report_summary": make_not_requested_summary(),
        "worker_packet_run_summary": make_not_requested_summary(),
        "runtime_cycle_summary": make_not_requested_summary(),
        "runtime_environment_ledger_summary": make_not_requested_summary(),
        "worker_run_report_path": output_dir / "worker-run-report.json",
        "bootstrap_worker_run_report_path": output_dir / "bootstrap-worker-run-report.json",
        "runtime_environment_ledger_path": output_dir / "runtime-environment-ledger.json",
        "subagent_execution_summary": subagent_execution_summary(request=request, enabled=enabled),
        "subagent_slice_summary": empty_subagent_slice_summary(),
    }
    if not enabled:
        return lane_state

    worker_run_report_path = lane_state["worker_run_report_path"]
    bootstrap_worker_run_report_path = lane_state["bootstrap_worker_run_report_path"]
    runtime_environment_ledger_path = lane_state["runtime_environment_ledger_path"]
    bootstrap_report = json.loads(toolchain_bootstrap_path.read_text(encoding="utf-8"))

    wp_packet_summary = build_work_package_packets(
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        openapi_spec=spec,
        implementation_bindings=implementation_bindings,
        output_dir=output_dir,
    )
    wp_wave_summary = build_work_package_wave_plan(
        esp_text=esp_text,
        packet_index=json.loads((output_dir / "work-package-packets" / "index.json").read_text(encoding="utf-8")),
        output_dir=output_dir,
    )
    execution_loop_summary = build_execution_loop(
        wave_plan=json.loads((output_dir / "work-package-wave-plan.json").read_text(encoding="utf-8")),
        output_dir=output_dir,
    )
    execution_loop_plan = json.loads((output_dir / "execution-loop-plan.json").read_text(encoding="utf-8"))
    runtime_environment_ledger = generate_runtime_environment_ledger(
        execution_loop_plan=execution_loop_plan,
        output_dir=output_dir,
        available_runtime_environments=detect_current_available_runtime_environments(
            bootstrap_report=bootstrap_report,
        ),
    )
    write_json(runtime_environment_ledger_path, runtime_environment_ledger)
    execution_dispatch_summary = emit_execution_dispatch_artifacts(
        execution_loop_plan=execution_loop_plan,
        output_dir=output_dir,
        runtime_environment_ledger=runtime_environment_ledger,
    )
    worker_run_report_summary = initialize_worker_run_report(worker_run_report_path)
    runtime_cycle_summary = run_runtime_cycle(
        execution_loop_plan_path=output_dir / "execution-loop-plan.json",
        output_dir=output_dir,
        worker_run_report_path=worker_run_report_path,
        runtime_environment_ledger_path=runtime_environment_ledger_path,
    )
    bootstrap_wave, bootstrap_lane = select_bootstrap_worker_packet(execution_loop_plan)
    worker_packet_mode = select_bootstrap_worker_packet_run_mode()
    worker_packet_run_summary = run_worker_packet(
        output_dir=output_dir,
        wave=bootstrap_wave,
        lane=bootstrap_lane,
        mode=worker_packet_mode,
        actor="run_phase3_first_version",
        note=(
            "execute ready Action Card slices with the configured runner"
            if worker_packet_mode in {"execute-batch", "execute-slices"}
            else "prepare the first worker packet and Action Card slice manifest; real SubAgent execution is runner-bound"
        ),
        runtime_environment_ledger_path=runtime_environment_ledger_path,
    )
    subagent_slice_summary = empty_subagent_slice_summary()
    worker_packet_run_report_path = Path(str(worker_packet_run_summary.get("run_report_path", "")))
    if worker_packet_run_report_path.exists():
        worker_packet_run_report = json.loads(worker_packet_run_report_path.read_text(encoding="utf-8"))
        if isinstance(worker_packet_run_report.get("subagent_slice_run_summary"), dict):
            subagent_slice_summary = worker_packet_run_report["subagent_slice_run_summary"]
    worker_run_report_md_path = worker_run_report_path.with_suffix(".md")
    bootstrap_worker_run_report_path.write_text(worker_run_report_path.read_text(encoding="utf-8"), encoding="utf-8")
    bootstrap_worker_run_report_path.with_suffix(".md").write_text(
        worker_run_report_md_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    bootstrap_worker_run_report_summary = json.loads(bootstrap_worker_run_report_path.read_text(encoding="utf-8")).get(
        "summary",
        worker_run_report_summary,
    )
    worker_run_report_summary = initialize_worker_run_report(worker_run_report_path)
    runtime_cycle_summary = run_runtime_cycle(
        execution_loop_plan_path=output_dir / "execution-loop-plan.json",
        output_dir=output_dir,
        worker_run_report_path=worker_run_report_path,
        runtime_environment_ledger_path=runtime_environment_ledger_path,
    )

    lane_state.update(
        {
            "wp_packet_summary": wp_packet_summary,
            "wp_wave_summary": wp_wave_summary,
            "execution_loop_summary": execution_loop_summary,
            "execution_dispatch_summary": execution_dispatch_summary,
            "worker_run_report_summary": worker_run_report_summary,
            "bootstrap_worker_run_report_summary": bootstrap_worker_run_report_summary,
            "worker_packet_run_summary": worker_packet_run_summary,
            "runtime_cycle_summary": runtime_cycle_summary,
            "runtime_environment_ledger_summary": runtime_environment_ledger,
            "subagent_execution_summary": subagent_execution_summary(
                request=request,
                enabled=True,
                subagent_slice_summary=subagent_slice_summary,
            ),
            "subagent_slice_summary": subagent_slice_summary,
        }
    )
    return lane_state
