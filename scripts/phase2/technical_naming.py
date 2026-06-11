#!/usr/bin/env python3
"""Deterministic technical naming helpers for Phase-2 artifacts."""

from __future__ import annotations

import hashlib
import re


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


def technical_candidate_order(raw: str, alias_candidates: tuple[str, ...]) -> list[str]:
    raw_text = str(raw or "").strip()
    filtered_aliases = [
        str(candidate).strip()
        for candidate in alias_candidates
        if str(candidate).strip() and not looks_like_generic_object_descriptor(str(candidate))
    ]
    if ascii_words(raw_text):
        return [raw_text, *filtered_aliases]
    return [*filtered_aliases, raw_text]


def choose_technical_pascal(raw: str, *alias_candidates: str, prefix: str = "Entity") -> str:
    for candidate in technical_candidate_order(raw, alias_candidates):
        identifier = ascii_pascal(candidate)
        if identifier:
            return identifier
    return f"{prefix}{short_stable_suffix(raw).upper()}"


def choose_technical_snake(raw: str, *alias_candidates: str, prefix: str = "entity") -> str:
    for candidate in technical_candidate_order(raw, alias_candidates):
        identifier = ascii_snake(candidate)
        if identifier:
            return identifier
    return f"{prefix}_{short_stable_suffix(raw)}"


def choose_technical_slug(raw: str, *alias_candidates: str, prefix: str = "entity") -> str:
    for candidate in technical_candidate_order(raw, alias_candidates):
        identifier = ascii_slug(candidate)
        if identifier:
            return identifier
    return f"{prefix}-{short_stable_suffix(raw)}"
