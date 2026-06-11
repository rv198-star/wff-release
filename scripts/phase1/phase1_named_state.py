#!/usr/bin/env python3
"""
Shared helpers for extracting explicit named-state markers from localized markdown.
"""

from __future__ import annotations

import re


def extract_named_state(text: str, field: str) -> str | None:
    lines = text.splitlines()
    field_pattern = re.compile(
        rf"^\s*-\s*(?=[^:\n]*{re.escape(field)}[^:\n]*)[^:\n]+:\s*(.*?)\s*$",
        flags=re.IGNORECASE,
    )
    inline_value_pattern = re.compile(r"^`?([^`\n]+)`?$")
    child_value_pattern = re.compile(r"^\s*-\s+`?([^`\n]+)`?\s*$")

    for idx, line in enumerate(lines):
        match = field_pattern.match(line)
        if not match:
            continue
        inline_value = match.group(1).strip()
        if inline_value:
            inline_match = inline_value_pattern.match(inline_value)
            if inline_match:
                return inline_match.group(1).strip() or None
        for follow in lines[idx + 1 :]:
            if not follow.strip():
                continue
            if follow.startswith("#"):
                break
            child_match = child_value_pattern.match(follow)
            if child_match:
                return child_match.group(1).strip() or None
            break
    return None
