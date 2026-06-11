#!/usr/bin/env python3
"""Deterministic technical naming helpers for Phase-2 artifacts."""

from __future__ import annotations

import hashlib
import re

REVIEW_BOUND_TECHNICAL_PASCAL_PREFIX = "ReviewBoundTechnicalName"
REVIEW_BOUND_TECHNICAL_SNAKE_PREFIX = "review_bound_technical_name"
REVIEW_BOUND_TECHNICAL_SLUG_PREFIX = "review-bound-technical-name"
STRUCTURAL_ASCII_ONLY_WORDS = {
    "archive",
    "archived",
    "audit",
    "change",
    "changed",
    "changes",
    "data",
    "detail",
    "details",
    "entity",
    "event",
    "events",
    "history",
    "id",
    "identifier",
    "info",
    "information",
    "item",
    "items",
    "object",
    "objects",
    "payload",
    "record",
    "records",
    "revision",
    "revisions",
    "snapshot",
    "state",
    "status",
    "summary",
    "version",
    "versions",
}


def short_stable_suffix(raw: str) -> str:
    return hashlib.sha1(str(raw).encode("utf-8")).hexdigest()[:6]


def ascii_words(raw: str) -> list[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(raw or ""))
    return [word for word in re.findall(r"[A-Za-z0-9]+", expanded) if word]


def ascii_pascal(raw: str) -> str:
    return "".join(word[:1].upper() + word[1:] for word in ascii_words(raw))


def ascii_snake(raw: str) -> str:
    return "_".join(word.lower() for word in ascii_words(raw))


def ascii_slug(raw: str) -> str:
    return "-".join(word.lower() for word in ascii_words(raw))


def looks_like_generic_object_descriptor(raw: str) -> bool:
    lowered = str(raw or "").strip().lower()
    if not lowered:
        return False
    return bool(re.search(r"\b(?:primary|supporting)\b.*\bobject\b.*\bfor\b", lowered))


def has_non_ascii_text(raw: str) -> bool:
    return any(ord(char) > 127 for char in str(raw or ""))


def raw_ascii_words_are_only_structural_suffix(raw: str) -> bool:
    if not has_non_ascii_text(raw):
        return False
    words = [word.lower() for word in ascii_words(raw)]
    return bool(words) and all(word in STRUCTURAL_ASCII_ONLY_WORDS for word in words)


def technical_candidate_order(raw: str, alias_candidates: tuple[str, ...]) -> list[str]:
    raw_text = str(raw or "").strip()
    filtered_aliases = [
        str(candidate).strip()
        for candidate in alias_candidates
        if str(candidate).strip() and not looks_like_generic_object_descriptor(str(candidate))
    ]
    if raw_ascii_words_are_only_structural_suffix(raw_text):
        return filtered_aliases
    if ascii_words(raw_text):
        return [raw_text, *filtered_aliases]
    return [*filtered_aliases, raw_text]


def unresolved_technical_pascal(raw: str) -> str:
    return f"{REVIEW_BOUND_TECHNICAL_PASCAL_PREFIX}{short_stable_suffix(raw).upper()}"


def unresolved_technical_snake(raw: str) -> str:
    return f"{REVIEW_BOUND_TECHNICAL_SNAKE_PREFIX}_{short_stable_suffix(raw)}"


def unresolved_technical_slug(raw: str) -> str:
    return f"{REVIEW_BOUND_TECHNICAL_SLUG_PREFIX}-{short_stable_suffix(raw)}"


def technical_name_is_review_bound(value: str) -> bool:
    cleaned = str(value or "").strip()
    return bool(
        cleaned.startswith(REVIEW_BOUND_TECHNICAL_PASCAL_PREFIX)
        or cleaned.startswith(REVIEW_BOUND_TECHNICAL_SNAKE_PREFIX)
        or cleaned.startswith(REVIEW_BOUND_TECHNICAL_SLUG_PREFIX)
    )


def synthetic_technical_name_report(raw: str, *alias_candidates: str, prefix: str = "Entity") -> dict[str, str]:
    pascal = choose_technical_pascal(raw, *alias_candidates, prefix=prefix)
    snake = choose_technical_snake(raw, *alias_candidates, prefix=prefix.lower())
    slug = choose_technical_slug(raw, *alias_candidates, prefix=prefix.lower())
    status = "review_bound" if any(technical_name_is_review_bound(value) for value in (pascal, snake, slug)) else "resolved"
    return {
        "source_label": str(raw or "").strip(),
        "status": status,
        "reason": "no-usable-ascii-technical-name" if status == "review_bound" else "resolved-from-source-or-alias",
        "pascal": pascal,
        "snake": snake,
        "slug": slug,
    }


def choose_technical_pascal(raw: str, *alias_candidates: str, prefix: str = "Entity") -> str:
    for candidate in technical_candidate_order(raw, alias_candidates):
        identifier = ascii_pascal(candidate)
        if identifier:
            return identifier
    return unresolved_technical_pascal(raw)


def choose_technical_snake(raw: str, *alias_candidates: str, prefix: str = "entity") -> str:
    for candidate in technical_candidate_order(raw, alias_candidates):
        identifier = ascii_snake(candidate)
        if identifier:
            return identifier
    return unresolved_technical_snake(raw)


def choose_technical_slug(raw: str, *alias_candidates: str, prefix: str = "entity") -> str:
    for candidate in technical_candidate_order(raw, alias_candidates):
        identifier = ascii_slug(candidate)
        if identifier:
            return identifier
    return unresolved_technical_slug(raw)
