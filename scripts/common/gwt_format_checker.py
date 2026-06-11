#!/usr/bin/env python3
"""
Reusable Given/When/Then checker utilities.

This module exists so Phase-1 and Phase-2 quality gates can share the same
Markdown-table parsing and GWT-structure checks instead of reimplementing them
in multiple places.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import json
import re
import sys
from pathlib import Path


GIVEN_PATTERN = re.compile(r"\bgiven\b|给定", flags=re.IGNORECASE)
WHEN_PATTERN = re.compile(r"\bwhen\b|当", flags=re.IGNORECASE)
THEN_PATTERN = re.compile(r"\bthen\b|则|那么", flags=re.IGNORECASE)


def normalize_table_header(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip().strip("`"))
    aliases = re.findall(r"\(([^()]+)\)", cleaned)
    for alias in reversed(aliases):
        normalized_alias = re.sub(r"\s+", " ", alias.strip().strip("`").lower())
        if normalized_alias:
            return normalized_alias
    return cleaned.lower()


def markdown_tables(text: str) -> list[dict[str, list[dict[str, str]] | list[str]]]:
    tables: list[dict[str, list[dict[str, str]] | list[str]]] = []
    lines = text.splitlines()
    idx = 0
    while idx < len(lines):
        if not lines[idx].lstrip().startswith("|"):
            idx += 1
            continue
        group: list[str] = []
        while idx < len(lines) and lines[idx].lstrip().startswith("|"):
            group.append(lines[idx].strip())
            idx += 1
        if len(group) < 2 or "---" not in group[1]:
            continue
        headers = [normalize_table_header(part) for part in group[0].strip("|").split("|")]
        rows: list[dict[str, str]] = []
        for row_line in group[2:]:
            parts = [part.strip().strip("`") for part in row_line.strip("|").split("|")]
            if len(parts) < len(headers):
                parts.extend([""] * (len(headers) - len(parts)))
            rows.append(dict(zip(headers, parts)))
        tables.append({"headers": headers, "rows": rows})
    return tables


def first_table_with_headers(
    text: str,
    required_headers: set[str],
    *,
    id_headers: tuple[str, ...] = (),
) -> dict[str, list[dict[str, str]] | list[str]] | None:
    fallback: dict[str, list[dict[str, str]] | list[str]] | None = None
    for table in markdown_tables(text):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        if id_headers and any(candidate in headers for candidate in id_headers):
            return table
        if fallback is None:
            fallback = table
    return fallback


def count_complete_rows(
    table: dict[str, list[dict[str, str]] | list[str]] | None,
    required_headers: set[str],
) -> int:
    if table is None:
        return 0
    return sum(
        1 for row in table["rows"] if all(str(row.get(header, "")).strip() for header in required_headers)
    )


def unique_non_empty_values(
    table: dict[str, list[dict[str, str]] | list[str]] | None,
    header: str,
) -> list[str]:
    if table is None:
        return []
    values = {
        str(row.get(header, "")).strip().lower()
        for row in table["rows"]
        if str(row.get(header, "")).strip()
    }
    return sorted(values)


def gwt_keyword_rows(text: str) -> int:
    hits = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|"):
            continue
        if GIVEN_PATTERN.search(stripped) and WHEN_PATTERN.search(stripped) and THEN_PATTERN.search(stripped):
            hits += 1
    return hits


def analyze_gwt_block(
    text: str,
    *,
    id_headers: tuple[str, ...] = ("ac_id", "scenario_id", "story_id"),
    gwt_headers: tuple[str, ...] = ("given", "when", "then"),
    boundary_headers: tuple[str, ...] = ("boundary_condition_type", "boundary_case"),
) -> dict[str, object]:
    gwt_required = set(gwt_headers)
    boundary_required = set(boundary_headers)
    gwt_table = first_table_with_headers(text, gwt_required, id_headers=id_headers)
    boundary_table = first_table_with_headers(text, boundary_required, id_headers=id_headers)
    boundary_types = unique_non_empty_values(boundary_table, boundary_headers[0])
    return {
        "gwt_table_found": gwt_table is not None,
        "gwt_headers": list(gwt_table["headers"]) if gwt_table is not None else [],
        "gwt_rows": count_complete_rows(gwt_table, gwt_required),
        "keyword_rows": gwt_keyword_rows(text),
        "boundary_table_found": boundary_table is not None,
        "boundary_headers": list(boundary_table["headers"]) if boundary_table is not None else [],
        "boundary_rows": count_complete_rows(boundary_table, boundary_required),
        "boundary_types": boundary_types,
        "boundary_variety": len(boundary_types),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: gwt_format_checker.py <markdown-file>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1]).resolve()
    result = analyze_gwt_block(path.read_text(encoding="utf-8"))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
