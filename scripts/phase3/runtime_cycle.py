#!/usr/bin/env python3
"""
Refresh Phase-3 runtime dispatch state after worker packet events.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.output_language import localize_phase3_runtime_cycle_summary
from phase3.execution_dispatch_state import emit_execution_dispatch_artifacts
from phase3.execution_packet_access import load_json
from phase3.review_support import write_json_and_markdown_report
from phase3.worker_run_report import initialize_worker_run_report, record_worker_run_event


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
    paths = write_json_and_markdown_report(
        json_path=output_dir / "runtime-cycle-summary.json",
        report=summary,
        markdown=build_runtime_cycle_markdown(summary),
        markdown_path=output_dir / "runtime-cycle-summary.md",
    )
    return {
        "summary_path": paths["json_path"],
        "summary_markdown_path": paths["markdown_path"],
        **dispatch_summary,
    }
