#!/usr/bin/env python3
"""Shared mechanical helpers for Phase-3 scenario/replay test scaffolders."""

from __future__ import annotations

import json
import re

from phase3.test_scaffolder_common import normalize_field_token, response_data_for_operation


def response_is_array(endpoint_rows: list[dict[str, object]], operation_id: str) -> bool:
    return isinstance(response_data_for_operation(endpoint_rows, operation_id), list)


def response_data_example_record(endpoint_rows: list[dict[str, object]], operation_id: str) -> dict[str, object]:
    data = response_data_for_operation(endpoint_rows, operation_id)
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return {}


def ts_property_access(field: str) -> str:
    return f".{field}" if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", field) else f"[{json.dumps(field, ensure_ascii=False)}]"


def literal_ts_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _endpoint_row(endpoint_rows: list[dict[str, object]], operation_id: str) -> dict[str, object]:
    for row in endpoint_rows:
        if str(row.get("endpoint_name") or row.get("operation_id") or "").strip() == operation_id:
            return row
    return {}


def _mechanical_authority_example(row: dict[str, object]) -> bool:
    """Return True when the P2 authority renderer, not semantic authority, owns example values."""
    explicit = str(row.get("response_example_authority") or "").strip().casefold()
    if explicit:
        return explicit == "mechanical-shape-only"
    profile = str(row.get("response_profile") or "").casefold()
    return "contract-bound response for" in profile


def scalar_business_value_fields(endpoint_rows: list[dict[str, object]], operation_id: str) -> dict[str, object]:
    row = _endpoint_row(endpoint_rows, operation_id)
    record = response_data_example_record(endpoint_rows, operation_id)
    explicit_literals = {
        str(item).strip()
        for item in row.get("semantic_literal_fields", [])
        if str(item).strip()
    } if isinstance(row.get("semantic_literal_fields"), list) else set()
    mechanical_example = _mechanical_authority_example(row)
    values: dict[str, object] = {}
    for field, value in record.items():
        normalized = normalize_field_token(field)
        if normalized in {"traceid", "createdat", "updatedat"} or normalized.endswith("id"):
            continue
        if mechanical_example and field not in explicit_literals:
            # Authority-mode response examples are mechanically generated shape/sample
            # material. They cannot become business-value assertions without an
            # explicit authority-bearing literal marker.
            continue
        if isinstance(value, (str, int, float, bool)) and value is not None:
            values[field] = value
    return values


def first_matching_failure_code(failure_codes: list[str], pattern: str) -> str:
    regex = re.compile(pattern)
    for code in failure_codes:
        if regex.search(code):
            return code
    return ""
