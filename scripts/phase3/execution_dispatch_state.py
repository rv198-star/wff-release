from __future__ import annotations

from pathlib import Path
from typing import Any

from common.output_language import (
    localize_phase3_dispatch_manifest,
    localize_phase3_execution_runtime_state,
)
from phase3.review_support import write_json_and_markdown_report


def packet_id(*, wave: int | None = None, lane: str | None = None, packet: str | None = None) -> str:
    if packet:
        return packet.strip()
    if wave is None or lane is None or not str(lane).strip():
        raise ValueError("packet or wave+lane is required")
    return f"wave-{int(wave):02d}:{str(lane).strip()}"


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


def wave_is_fully_verified(rows: list[dict[str, Any]], wave: int) -> bool:
    wave_rows = [row for row in rows if int(row.get("wave", 0) or 0) == wave]
    return bool(wave_rows) and all(str(row.get("current_state", "")).strip() == "verified" for row in wave_rows)


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
    write_json_and_markdown_report(
        json_path=state_path,
        report=report,
        markdown=runtime_markdown(report),
        markdown_path=state_md_path,
    )
    write_json_and_markdown_report(
        json_path=manifest_path,
        report={"dispatchable_packets": report["dispatchable_packets"]},
        markdown=manifest_markdown(report),
        markdown_path=manifest_md_path,
    )
    return {
        "output_path": str(state_path),
        "manifest_path": str(manifest_path),
        "state_markdown_path": str(state_md_path),
        "manifest_markdown_path": str(manifest_md_path),
        **report["summary"],
        "overall_status": report["overall_status"],
    }


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
    write_json_and_markdown_report(
        json_path=output_dir / "execution-runtime-state.json",
        report=runtime_state,
        markdown=runtime_markdown(runtime_state),
        markdown_path=output_dir / "execution-runtime-state.md",
    )
    write_json_and_markdown_report(
        json_path=output_dir / "dispatch-manifest.json",
        report={"dispatchable_packets": dispatchable_packets},
        markdown=manifest_markdown(runtime_state),
        markdown_path=output_dir / "dispatch-manifest.md",
    )


def sorted_dispatchable_packets(runtime_state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = runtime_state.get("dispatchable_packets", [])
    if not isinstance(rows, list):
        return []
    return sorted(
        [row for row in rows if isinstance(row, dict)],
        key=lambda row: (int(row.get("wave", 0) or 0), str(row.get("lane", ""))),
    )
