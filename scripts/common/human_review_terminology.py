#!/usr/bin/env python3
"""Chinese display terminology for the Human Review reader surface.

Machine values remain unchanged. These helpers are only for reader-facing
Markdown, HTML, and audit prose.
"""

from __future__ import annotations

import re
from typing import Any


REVIEW_BOUND_MACHINE_VALUE = "review-bound"
REVIEW_BOUND_DISPLAY = "待审阅确认"
HUMAN_REVIEWER_DISPLAY = "审阅人"
EXPLICIT_MANUAL_REVIEWER_DISPLAY = "人工审阅者"

_MACHINE_KEYS = {
    "id",
    "type",
    "state",
    "status",
    "kind",
    "namespace",
    "source_ref",
    "source_refs",
    "identity",
    "from",
    "to",
    "path",
    "route",
    "schema_version",
    "projection_kind",
}


def review_status_label(value: object) -> str:
    """Return the Chinese reader label without changing the machine value."""

    text = str(value or "").strip()
    return REVIEW_BOUND_DISPLAY if text.lower() == REVIEW_BOUND_MACHINE_VALUE else text


def reviewer_label(value: object, *, explicit_non_ai: bool = False) -> str:
    """Return the agreed Chinese role label for a human reviewer value."""

    text = str(value or "").strip()
    normalized = text.lower().replace("_", " ")
    if normalized == "human reviewer" or text in {
        "人类审阅者",
        "人工审阅者",
        "审阅人",
    }:
        return (
            EXPLICIT_MANUAL_REVIEWER_DISPLAY
            if explicit_non_ai
            else HUMAN_REVIEWER_DISPLAY
        )
    return localize_review_terms(text)


def localize_review_terms(value: object) -> str:
    """Localize Human Review terms in reader-facing prose.

    Replacement is intentionally one-way. Structured artifacts retain their
    original machine values and field names.
    """

    text = str(value or "")
    text = re.sub(r"\bhuman[ _-]+reviewer\b", HUMAN_REVIEWER_DISPLAY, text, flags=re.IGNORECASE)
    text = text.replace("人类审阅者", HUMAN_REVIEWER_DISPLAY)
    text = text.replace("受评审约束", REVIEW_BOUND_DISPLAY)
    text = text.replace("受审阅约束", REVIEW_BOUND_DISPLAY)
    text = re.sub(r"\breview-bound\b", REVIEW_BOUND_DISPLAY, text, flags=re.IGNORECASE)
    text = text.replace("人类审阅行动卡", "人工审阅行动卡")
    text = text.replace("人类 Action Card", "人工审阅行动卡")
    text = text.replace("人类审阅投影", "人工审阅投影")
    text = text.replace("人类审阅文档", "人工审阅文档")
    text = text.replace("人类审阅", "人工审阅")
    return text


def localize_review_payload(value: Any, *, key: str = "") -> Any:
    """Recursively localize visible bundle text while preserving machine keys."""

    if isinstance(value, dict):
        return {
            item_key: localize_review_payload(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        if key in _MACHINE_KEYS:
            return list(value)
        return [localize_review_payload(item, key=key) for item in value]
    if isinstance(value, str):
        return value if key in _MACHINE_KEYS else localize_review_terms(value)
    return value
