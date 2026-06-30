#!/usr/bin/env python3
"""
Render deterministic Phase-3 execution loop artifacts.
"""

from __future__ import annotations

from typing import Any

from common.output_language import localize_phase3_execution_loop_plan


def execution_loop_plan_markdown(plan: dict[str, Any], output_locale: str | None = None) -> str:
    summary = plan.get("summary", {})
    lines = [
        "# Phase-3 Execution Loop Plan",
        "",
        "## Summary",
        f"- overall_status: {plan.get('overall_status', 'unknown')}",
        f"- wave_count: {summary.get('wave_count', 0)}",
        f"- worker_packet_count: {summary.get('worker_packet_count', 0)}",
        f"- ready_now_wave_count: {summary.get('ready_now_wave_count', 0)}",
        f"- queued_wave_count: {summary.get('queued_wave_count', 0)}",
        f"- blocked_wave_count: {summary.get('blocked_wave_count', 0)}",
        f"- unassigned_contract_test_count: {summary.get('unassigned_contract_test_count', 0)}",
        "",
        "## Waves",
    ]
    for wave in plan.get("waves", []):
        lines.extend(
            [
                f"### Wave {wave['wave']}",
                f"- structural_status: {wave['structural_status']}",
                f"- dispatch_state: {wave['dispatch_state']}",
                f"- worker_packet_count: {wave['worker_packet_count']}",
            ]
        )
        for packet in wave.get("worker_packets", []):
            lines.append(
                f"- {packet['lane']} [{packet['worker_packet_status']}] dispatch={packet['dispatch_state']} "
                f"wps={', '.join(packet['work_package_ids'])}"
            )
        lines.append("")
    if plan.get("unscheduled_rows"):
        lines.extend(["## Unscheduled"])
        for row in plan["unscheduled_rows"]:
            lines.append(f"- {row['wp_id']}: {', '.join(row.get('blocking_reasons', [])) or 'none'}")
        lines.append("")
    return localize_phase3_execution_loop_plan("\n".join(lines) + "\n", output_locale)
