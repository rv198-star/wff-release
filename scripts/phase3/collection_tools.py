#!/usr/bin/env python3
"""
Shared deterministic collection helpers for Phase-3 planning artifacts.
"""

from __future__ import annotations

from typing import Any


def dedupe_dict_rows(rows: list[dict[str, Any]], key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    kept: list[dict[str, Any]] = []
    for row in rows:
        key = tuple(str(row.get(field, "")).strip() for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept


def dedupe_strings_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    kept: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        kept.append(normalized)
    return kept
