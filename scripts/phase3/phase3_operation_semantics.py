"""Extract operation-bound semantics from existing Phase-2 artifacts.

This module is a Phase-3 bridge. It does not create new business truth; it
extracts concrete owner/aggregate/event/guard/evidence semantics already present
in Phase-2 markdown tables or diagrams so behavior cards do not collapse to
source-reference-only placeholders.
"""

from __future__ import annotations

import re
from typing import Any


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if cells and all(re.fullmatch(r"[-: ]+", cell) for cell in cells):
        return []
    return cells


def _normalize_operation(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _operation_tokens(operation_id: str) -> list[str]:
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", operation_id)
    tokens = [operation_id, *words]
    if words and words[0].lower() in {"manage", "create", "update", "get", "list", "record", "start"}:
        subject = "".join(words[1:])
        tokens.append(subject)
        if words[0].lower() == "list":
            tokens.append(_singularize_pascal(subject))
    return [token for token in dict.fromkeys(tokens) if token]


def _singularize_pascal(value: str) -> str:
    if value.endswith("ies") and len(value) > 3:
        return f"{value[:-3]}y"
    if value.endswith("s") and not value.endswith("ss") and len(value) > 1:
        return value[:-1]
    return value


def _preferred_aggregate_token(operation_id: str) -> str:
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", operation_id)
    if words and words[0].lower() in {"manage", "create", "update", "get", "list", "record", "start"}:
        subject = "".join(words[1:])
        if words[0].lower() == "list":
            return _singularize_pascal(subject)
        return subject
    return operation_id


def _state_set(value: str) -> list[str]:
    return [item.strip().lower() for item in re.split(r"\s*/\s*", value) if item.strip()]


def _evidence_keys_from_text(text: str) -> list[str]:
    keys: list[str] = []
    for token in re.findall(r"\b[a-z][a-z0-9_]*_id\b|\bversion\b|\btrace_id\b", text):
        if token not in keys:
            keys.append(token)
    return keys


def _find_lifecycle_row(operation_id: str, lines: list[str]) -> dict[str, Any] | None:
    preferred = _normalize_operation(_preferred_aggregate_token(operation_id))
    tokens = [token for token in _operation_tokens(operation_id) if len(token) > 4]
    headers: list[str] = []
    for index, line in enumerate(lines):
        cells = _split_table_row(line)
        if not cells:
            continue
        lowered = [cell.lower() for cell in cells]
        if "aggregate_name" in lowered and "owner_writer" in lowered:
            headers = lowered
            continue
        if any(cell.endswith("_id") or cell in {"operation_id", "method", "path", "trace_id", "event_name", "upstream_module"} for cell in lowered):
            headers = []
            continue
        if not headers or len(cells) < len(headers):
            continue
        row = dict(zip(headers, cells))
        aggregate = row.get("aggregate_name", "")
        owner = row.get("owner_writer", "")
        trigger_events = row.get("trigger_events", "")
        haystack = " ".join([aggregate, owner, trigger_events, row.get("closure_note", ""), row.get("mutation_guard", "")])
        aggregate_norm = _normalize_operation(aggregate)
        if preferred and (preferred == aggregate_norm or preferred in _normalize_operation(haystack)):
            return row
        if any(_normalize_operation(token) and _normalize_operation(token) == aggregate_norm for token in tokens):
            return row
    return None


def _find_collaboration_rows(operation_id: str, lines: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    normalized_operation = _normalize_operation(operation_id)
    for line in lines:
        cells = _split_table_row(line)
        if not cells:
            continue
        lowered = [cell.lower() for cell in cells]
        if "allowed_interaction" in lowered and "required_artifact" in lowered:
            headers = lowered
            continue
        if any(cell in {"aggregate_name", "operation_id", "method", "path", "trace_id", "event_name"} for cell in lowered):
            headers = []
            continue
        if not headers or len(cells) < len(headers):
            continue
        row = dict(zip(headers, cells))
        if normalized_operation in _normalize_operation(" ".join(cells)):
            rows.append(row)
    return rows


def _find_event_rows(operation_id: str, lines: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    normalized_operation = _normalize_operation(operation_id)
    for line in lines:
        cells = _split_table_row(line)
        if not cells:
            continue
        lowered = [cell.lower() for cell in cells]
        if "event_name" in lowered and "trigger" in lowered and "payload" in lowered:
            headers = lowered
            continue
        if any(cell in {"aggregate_name", "operation_id", "method", "path", "trace_id", "upstream_module"} for cell in lowered):
            headers = []
            continue
        if not headers or len(cells) < len(headers):
            continue
        row = dict(zip(headers, cells))
        if normalized_operation in _normalize_operation(" ".join(cells)):
            rows.append(row)
    return rows


def extract_operation_semantics(operation_id: str, source_texts: list[str]) -> dict[str, Any]:
    """Extract operation-specific semantics from P2 source text.

    Returns review-bound status when no operation-specific semantic row can be
    found. The function intentionally uses generic table/identifier heuristics,
    not scenario-specific branches.
    """

    text = "\n".join(source_texts)
    lines = text.splitlines()
    lifecycle = _find_lifecycle_row(operation_id, lines)
    collaborations = _find_collaboration_rows(operation_id, lines)
    events = _find_event_rows(operation_id, lines)

    if not lifecycle and not collaborations and not events:
        return {
            "operation_id": operation_id,
            "status": "review_bound",
            "review_bound_reasons": ["operation_semantics_not_found"],
        }

    evidence_blob = "\n".join(
        [
            " | ".join((lifecycle or {}).values()),
            *[" | ".join(row.values()) for row in collaborations],
            *[" | ".join(row.values()) for row in events],
        ]
    )
    event_names = [row.get("event_name", "") for row in events if row.get("event_name", "")]
    if lifecycle and lifecycle.get("trigger_events") and lifecycle.get("trigger_events") not in event_names:
        event_names.append(lifecycle["trigger_events"])

    readonly_dependencies = []
    for row in collaborations:
        for key in _evidence_keys_from_text(row.get("required_artifact", "")):
            if key and key not in readonly_dependencies:
                readonly_dependencies.append(key)

    return {
        "operation_id": operation_id,
        "status": "resolved",
        "owner_service": (lifecycle or {}).get("owner_writer", ""),
        "aggregate": (lifecycle or {}).get("aggregate_name", ""),
        "state_set": _state_set((lifecycle or {}).get("state_set", "")),
        "trigger_events": event_names,
        "mutation_guard": (lifecycle or {}).get("mutation_guard", ""),
        "terminal_or_failure_exit": (lifecycle or {}).get("terminal_or_failure_exit", ""),
        "readonly_dependencies": readonly_dependencies,
        "evidence_keys": _evidence_keys_from_text(evidence_blob),
        "source_evidence": [item for item in [evidence_blob.strip()] if item],
    }
