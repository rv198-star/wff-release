#!/usr/bin/env python3
"""
Record Phase-3 worker packet run events and report current packet status.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.output_language import localize_phase3_worker_run_report
from phase3.execution_packet_access import load_json
from phase3.review_support import write_json_and_markdown_report


VALID_WORKER_RUN_STATUSES = {"started", "implemented", "blocked", "failed"}


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
                f"- {row['packet_id']} [{row['latest_status']}] "
                f"last_event_at={row['last_event_at'] or 'n/a'} evidence={row['evidence_ref'] or 'none'}"
            )
    lines.extend(["", "## Recent Events"])
    recent_events = report.get("events", [])[-10:]
    for event in recent_events or [{"packet_id": "none", "status": "", "at": ""}]:
        if event["packet_id"] == "none":
            lines.append("- none")
        else:
            lines.append(
                f"- {event['at']} {event['packet_id']} -> {event['status']} "
                f"actor={event.get('actor', '') or 'n/a'} note={event.get('note', '') or 'none'}"
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
    paths = write_json_and_markdown_report(
        json_path=report_path,
        report=updated,
        markdown=build_worker_run_report_markdown(updated),
    )
    return {
        "output_path": paths["json_path"],
        "markdown_path": paths["markdown_path"],
        **updated["summary"],
    }


def initialize_worker_run_report(report_path: Path) -> dict[str, Any]:
    report = empty_worker_run_report()
    paths = write_json_and_markdown_report(
        json_path=report_path,
        report=report,
        markdown=build_worker_run_report_markdown(report),
    )
    return {
        "output_path": paths["json_path"],
        "markdown_path": paths["markdown_path"],
        **report["summary"],
    }
