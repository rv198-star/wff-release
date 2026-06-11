#!/usr/bin/env python3
"""Shared Markdown table parsing and rendering helpers."""

from __future__ import annotations

import re
from typing import Any


def normalize_table_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("`").lower())


def normalize_snake_table_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().strip("`").lower()).strip("_")


def split_markdown_table_row(line: str, *, strip_backticks: bool = True) -> list[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if strip_backticks:
        return [cell.strip("`") for cell in cells]
    return cells


def coerce_markdown_table_cells(
    cells: list[str],
    header_count: int,
    *,
    extra_cell_policy: str = "middle",
) -> list[str]:
    if len(cells) == header_count:
        return cells
    if len(cells) < header_count:
        return [*cells, *([""] * (header_count - len(cells)))]
    if header_count <= 1:
        return cells[:header_count]
    if extra_cell_policy == "last":
        return [*cells[: header_count - 1], " | ".join(cells[header_count - 1 :])]
    if extra_cell_policy != "middle":
        raise ValueError(f"unsupported extra_cell_policy: {extra_cell_policy}")
    collapsed = [cells[0]]
    middle_source = cells[1:-1]
    middle_header_count = header_count - 2
    if middle_header_count == 1:
        collapsed.append(" | ".join(middle_source))
    else:
        collapsed.extend(middle_source[: middle_header_count - 1])
        collapsed.append(" | ".join(middle_source[middle_header_count - 1 :]))
    collapsed.append(cells[-1])
    return collapsed if len(collapsed) == header_count else cells[:header_count]


def parse_markdown_table(
    block: str,
    *,
    header_style: str = "normalized",
    strip_backticks: bool = True,
    merge_extra_cells: bool = False,
    extra_cell_policy: str = "middle",
    pad_short_rows: bool = True,
) -> list[dict[str, str]]:
    lines = [line.rstrip() for line in block.splitlines() if line.strip()]
    for idx in range(len(lines) - 1):
        if "|" not in lines[idx] or "|" not in lines[idx + 1]:
            continue
        if not re.match(r"^\s*\|?[\-:\s|]+\|?\s*$", lines[idx + 1]):
            continue
        raw_headers = split_markdown_table_row(lines[idx], strip_backticks=strip_backticks)
        if header_style == "snake":
            headers = [normalize_snake_table_header(cell) for cell in raw_headers]
        elif header_style == "raw":
            headers = raw_headers
        elif header_style == "normalized":
            headers = [normalize_table_header(cell) for cell in raw_headers]
        else:
            raise ValueError(f"unsupported header_style: {header_style}")
        rows: list[dict[str, str]] = []
        for line in lines[idx + 2 :]:
            if "|" not in line:
                break
            cells = split_markdown_table_row(line, strip_backticks=strip_backticks)
            if len(cells) > len(headers) and merge_extra_cells:
                cells = coerce_markdown_table_cells(cells, len(headers), extra_cell_policy=extra_cell_policy)
            elif len(cells) < len(headers) and pad_short_rows:
                cells = [*cells, *([""] * (len(headers) - len(cells)))]
            if len(cells) != len(headers):
                continue
            rows.append({header: cell for header, cell in zip(headers, cells)})
        if rows:
            return rows
    return []


def markdown_tables(text: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
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
        rows = parse_markdown_table("\n".join(group))
        headers = list(rows[0].keys()) if rows else [normalize_table_header(part) for part in group[0].strip("|").split("|")]
        tables.append({"headers": headers, "rows": rows})
    return tables


def table_rows_with_required_headers(block: str, required_headers: set[str]) -> list[dict[str, str]]:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return [row for row in table["rows"] if all(str(row.get(header, "")).strip() for header in required_headers)]
    return []


def count_markdown_table_rows(text: str, *, require_separator: bool = False) -> int:
    lines = text.splitlines()
    total = 0
    idx = 0
    while idx < len(lines):
        if not lines[idx].lstrip().startswith("|"):
            idx += 1
            continue
        group: list[str] = []
        while idx < len(lines) and lines[idx].lstrip().startswith("|"):
            group.append(lines[idx].strip())
            idx += 1
        if len(group) < 2:
            continue
        if require_separator and "---" not in group[1]:
            continue
        total += max(len(group) - 2, 0)
    return total


def sanitize_markdown_table_cell(
    value: object,
    *,
    pipe_escape: str = "html",
    newline_replacement: str = "<br>",
    escape_ampersand: bool = False,
    none_replacement: str | None = None,
    list_separator: str | None = None,
) -> str:
    if value is None and none_replacement is not None:
        text = none_replacement
    elif isinstance(value, list) and list_separator is not None:
        text = list_separator.join(str(item) for item in value)
    else:
        text = str(value)
    if escape_ampersand:
        text = text.replace("&", "&amp;")
    if pipe_escape == "html":
        text = text.replace("|", "&#124;")
    elif pipe_escape == "backslash":
        text = text.replace("|", "\\|")
    elif pipe_escape != "none":
        raise ValueError(f"unsupported pipe_escape: {pipe_escape}")
    return text.replace("\n", newline_replacement).strip()


def render_markdown_table(
    headers: list[str],
    rows: list[list[object]],
    *,
    pipe_escape: str = "html",
    newline_replacement: str = "<br>",
    escape_ampersand: bool = False,
    none_replacement: str | None = None,
    list_separator: str | None = None,
) -> str:
    def cell(value: object) -> str:
        return sanitize_markdown_table_cell(
            value,
            pipe_escape=pipe_escape,
            newline_replacement=newline_replacement,
            escape_ampersand=escape_ampersand,
            none_replacement=none_replacement,
            list_separator=list_separator,
        )

    header = "| " + " | ".join(cell(value) for value in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]
    return "\n".join([header, separator, *body])
