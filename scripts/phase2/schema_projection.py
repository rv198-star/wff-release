#!/usr/bin/env python3
"""Deterministic schema projection helpers for Phase-2 generated contracts."""

from __future__ import annotations

from phase2.projection_utils import unique_preserve


NULLABLE_SCHEMA_FIELD_TYPES = {
    "blockedReason": "string|null",
    "blocked_reason": "string|null",
    "nextCursor": "string|null",
    "next_cursor": "string|null",
}


def infer_schema_field_type(field_name: str, value: object) -> str:
    if field_name in NULLABLE_SCHEMA_FIELD_TYPES:
        return NULLABLE_SCHEMA_FIELD_TYPES[field_name]
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    if isinstance(value, list):
        if not value:
            return "array<unknown>"
        first = value[0]
        if isinstance(first, dict):
            return "array<object>"
        return f"array<{infer_schema_field_type(field_name, first)}>"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def flatten_schema_fields(value: object, *, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        fields: list[str] = []
        for key, subvalue in value.items():
            field_name = f"{prefix}.{key}" if prefix else key
            if isinstance(subvalue, dict):
                fields.append(f"{field_name}: object")
                fields.extend(flatten_schema_fields(subvalue, prefix=field_name))
            elif isinstance(subvalue, list) and subvalue and isinstance(subvalue[0], dict):
                fields.append(f"{field_name}: array<object>")
                fields.extend(flatten_schema_fields(subvalue[0], prefix=f"{field_name}[]"))
            else:
                fields.append(f"{field_name}: {infer_schema_field_type(key, subvalue)}")
        return unique_preserve(fields)
    if isinstance(value, list):
        if not value:
            return [f"{prefix}[]: array<unknown>"] if prefix else []
        first = value[0]
        if isinstance(first, dict):
            fields: list[str] = []
            for key, subvalue in first.items():
                item_prefix = f"{prefix}[].{key}" if prefix else f"[].{key}"
                if isinstance(subvalue, dict):
                    fields.append(f"{item_prefix}: object")
                    fields.extend(flatten_schema_fields(subvalue, prefix=item_prefix))
                else:
                    fields.append(f"{item_prefix}: {infer_schema_field_type(key, subvalue)}")
            return unique_preserve(fields)
        return [f"{prefix}[]: {infer_schema_field_type(prefix, first)}"] if prefix else []
    return [f"{prefix}: {infer_schema_field_type(prefix, value)}"] if prefix else []
