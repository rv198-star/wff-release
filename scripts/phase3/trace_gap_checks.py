#!/usr/bin/env python3
"""
Trace gap counting helpers for Phase-3 delivery closure.
"""

from __future__ import annotations

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
    if final_resolution:
        return final_resolution == "unresolved"
    return binding_status in {"suggested", "unresolved"}


def trace_registry_blocking_gap_count(report: dict[str, Any] | None) -> int:
    if not report:
        return 0
    rows = report.get("rows", []) if isinstance(report, dict) else []
    if isinstance(rows, list):
        count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            final_resolution = str(row.get("final_resolution") or "").strip().lower()
            binding_status = str(row.get("binding_status") or "").strip().lower()
            if final_resolution:
                if final_resolution != "unresolved":
                    continue
            elif binding_status not in {"suggested", "unresolved"}:
                continue
            if is_unexecutable_contract_trace_gap(row):
                continue
            count += 1
        return count
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
