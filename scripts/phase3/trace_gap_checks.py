#!/usr/bin/env python3
"""
Trace gap counting helpers for Phase-3 delivery closure.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def first_int(report: dict[str, Any] | None, *paths: tuple[str, ...]) -> int:
    if not report:
        return 0
    for path in paths:
        current: Any = report
        matched = True
        for key in path:
            if not isinstance(current, dict) or key not in current:
                matched = False
                break
            current = current[key]
        if matched and isinstance(current, (int, float)):
            return int(current)
    return 0


def list_gap_count(report: dict[str, Any] | None, keys: set[str]) -> int:
    if not report:
        return 0
    pending: list[Any] = [report]
    count = 0
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key in keys and isinstance(value, list):
                    count += len(value)
                else:
                    pending.append(value)
        elif isinstance(current, list):
            pending.extend(current)
    return count


def is_unexecutable_contract_trace_gap(row: dict[str, Any]) -> bool:
    source_type = str(row.get("source_type") or "").strip().lower()
    if source_type != "contract-trace":
        return False
    if any(str(item).strip() for item in row.get("test_targets", []) if item is not None):
        return False
    final_resolution = str(row.get("final_resolution") or "").strip().lower()
    binding_status = str(row.get("binding_status") or "").strip().lower()
    return binding_status in {"suggested", "unresolved"} and final_resolution not in {"unresolved"}


def trace_row_resolution(row: dict[str, Any]) -> str:
    final_resolution = str(row.get("final_resolution") or "").strip().lower()
    binding_status = str(row.get("binding_status") or row.get("status") or "").strip().lower()
    if binding_status in {"suggested", "review", "unresolved"}:
        return binding_status
    if final_resolution == "confirmed":
        return "confirmed"
    if final_resolution in {"suggested", "review", "unresolved"}:
        return final_resolution
    if binding_status in {"confirmed", "resolved"}:
        return "confirmed"
    if final_resolution == "resolved":
        return "confirmed"
    return "unknown"


def row_trace_ids(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("source_id", "trace_id", "upstream_trace_id"):
        value = str(row.get(key) or "").strip()
        if value:
            values.append(value)
    for key in ("source_ids", "trace_ids", "upstream_trace_ids", "linked_trace_ids"):
        raw = row.get(key)
        if isinstance(raw, list):
            values.extend(str(item).strip() for item in raw if str(item).strip())
    return sorted(set(values))


def trace_sidecar_unavailable(report: dict[str, Any] | None) -> tuple[bool, str]:
    if not isinstance(report, dict):
        return False, ""
    if bool(report.get("sidecar_unavailable")):
        return True, str(report.get("reason") or "").strip()
    for key in ("source_matrix", "test_trace_matrix", "trace_matrix"):
        source = report.get(key)
        if isinstance(source, dict) and bool(source.get("sidecar_unavailable")):
            return True, str(source.get("reason") or "").strip()
    return False, ""


def _operation_kind(row: dict[str, Any]) -> str:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("operation_id", "operation", "method", "binding_mode", "target", "implementation_target")
    ).lower()
    if any(token in text for token in ("post", "put", "patch", "delete", "write", "command", "create", "update", "submit")):
        return "write"
    if any(token in text for token in ("get", "read", "query", "list", "load")):
        return "read"
    return "unknown"


def trace_registry_quality_report(report: dict[str, Any] | None) -> dict[str, Any]:
    rows = report.get("rows", []) if isinstance(report, dict) else []
    trace_db_projection = report.get("trace_db_projection", {}) if isinstance(report, dict) else {}
    trace_db_projection = trace_db_projection if isinstance(trace_db_projection, dict) else {}
    trace_db_present = bool((report or {}).get("trace_db_present")) if isinstance(report, dict) else False
    trace_db_indexed = bool(trace_db_projection.get("p3_indexed"))
    trace_db_projection_status = str(trace_db_projection.get("status") or "").strip()
    sidecar_unavailable, sidecar_unavailable_reason = trace_sidecar_unavailable(report)
    if not isinstance(rows, list):
        blocking_count = list_gap_count(
            report,
            {
                "unbound_trace_ids",
                "unresolved_trace_ids",
                "missing_trace_ids",
                "unmatched_trace_ids",
                "remaining_trace_ids",
            },
        )
        return {
            "artifact_kind": "phase3-trace-quality-report.v1",
            "row_count": 0,
            "confirmed_count": 0,
            "suggested_count": 0,
            "review_count": 0,
            "unresolved_count": blocking_count,
            "unknown_count": 0,
            "blocking_gap_count": blocking_count,
            "abuse_count": 0,
            "abuse_rows": [],
            "chain_coverage_state": "legacy-summary",
            "trace_db_present": trace_db_present,
            "trace_db_indexed": trace_db_indexed,
            "trace_db_projection_status": trace_db_projection_status,
            "sidecar_unavailable": sidecar_unavailable,
            "sidecar_unavailable_reason": sidecar_unavailable_reason,
        }

    status_counts: Counter[str] = Counter()
    blocking_count = 0
    trace_id_rows: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        resolution = trace_row_resolution(row)
        status_counts[resolution] += 1
        if resolution in {"suggested", "review", "unresolved"} and not is_unexecutable_contract_trace_gap(row):
            blocking_count += 1
        for trace_id in row_trace_ids(row):
            trace_id_rows[trace_id].append({"index": index, "operation_kind": _operation_kind(row)})

    abuse_rows: list[dict[str, Any]] = []
    for trace_id, bindings in sorted(trace_id_rows.items()):
        operation_kinds = sorted({binding["operation_kind"] for binding in bindings if binding["operation_kind"] != "unknown"})
        if len(bindings) >= 8 or {"read", "write"}.issubset(set(operation_kinds)):
            abuse_rows.append(
                {
                    "trace_id": trace_id,
                    "binding_count": len(bindings),
                    "operation_kinds": operation_kinds,
                    "reason": "high-frequency trace id reuse"
                    if len(bindings) >= 8
                    else "same trace id spans read and write semantics",
                }
            )

    confirmed_count = status_counts["confirmed"]
    suggested_count = status_counts["suggested"]
    review_count = status_counts["review"]
    unresolved_count = status_counts["unresolved"]
    unknown_count = status_counts["unknown"]
    if unresolved_count > 0:
        chain_state = "unresolved"
    elif suggested_count > 0 or review_count > 0 or unknown_count > 0:
        chain_state = "not-confirmed"
    elif confirmed_count > 0:
        chain_state = "confirmed"
    else:
        chain_state = "empty"
    empty_chain_blocking = isinstance(report, dict) and chain_state == "empty"
    trace_db_projection_blocking = bool(
        isinstance(report, dict)
        and trace_db_present
        and confirmed_count > 0
        and not trace_db_indexed
    )
    blocking_gap_count = (
        blocking_count
        + (1 if empty_chain_blocking else 0)
        + (1 if trace_db_projection_blocking else 0)
    )

    return {
        "artifact_kind": "phase3-trace-quality-report.v1",
        "row_count": sum(status_counts.values()),
        "confirmed_count": confirmed_count,
        "suggested_count": suggested_count,
        "review_count": review_count,
        "unresolved_count": unresolved_count,
        "unknown_count": unknown_count,
        "blocking_gap_count": blocking_gap_count,
        "abuse_count": len(abuse_rows),
        "abuse_rows": abuse_rows,
        "chain_coverage_state": chain_state,
        "trace_db_present": trace_db_present,
        "trace_db_indexed": trace_db_indexed,
        "trace_db_projection_status": trace_db_projection_status,
        "empty_chain_blocking": empty_chain_blocking,
        "trace_db_projection_blocking": trace_db_projection_blocking,
        "sidecar_unavailable": sidecar_unavailable,
        "sidecar_unavailable_reason": sidecar_unavailable_reason,
    }


def trace_registry_blocking_gap_count(report: dict[str, Any] | None) -> int:
    if not report:
        return 0
    rows = report.get("rows", []) if isinstance(report, dict) else []
    if isinstance(rows, list):
        return int(trace_registry_quality_report(report)["blocking_gap_count"])
    return list_gap_count(
        report,
        {
            "unbound_trace_ids",
            "unresolved_trace_ids",
            "missing_trace_ids",
            "unmatched_trace_ids",
            "remaining_trace_ids",
        },
    )
