from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase3.execution_loop_builder import build_execution_loop, build_work_package_packets, build_work_package_wave_plan
from phase3.runtime_environment import detect_current_available_runtime_environments, generate_runtime_environment_ledger
from phase3.worker_packet_runner import (
    emit_execution_dispatch_artifacts,
    initialize_worker_run_report,
    run_runtime_cycle,
    run_worker_packet,
)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_not_requested_summary() -> dict[str, object]:
    return {"mode": "not-requested"}


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
) -> dict[str, object]:
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
    worker_packet_run_summary = run_worker_packet(
        output_dir=output_dir,
        wave=bootstrap_wave,
        lane=bootstrap_lane,
        mode="simulate-success",
        actor="run_phase3_first_version",
        note="bootstrap one worker packet lifecycle to prove implementation loop closure",
        runtime_environment_ledger_path=runtime_environment_ledger_path,
    )
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
        }
    )
    return lane_state
