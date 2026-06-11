#!/usr/bin/env python3
"""
Shared deterministic helpers for Phase-3 renderers.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from phase3.ui_locale import normalize_role_display_name


UUID_LIKE_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

UI_ROLE_POLICY_SKIP_TOKENS = {
    "role",
    "roles",
    "in",
    "is",
    "are",
    "allow",
    "allows",
    "allowed",
    "require",
    "requires",
    "required",
    "policy",
    "only",
    "any",
    "of",
    "with",
    "for",
    "current",
    "user",
    "actor",
    "visible",
    "visibility",
}


def camel_case(value: str) -> str:
    words = [part for part in re.split(r"[^A-Za-z0-9]+", value) if part]
    if not words:
        return "Generated"
    return "".join(word[:1].upper() + word[1:] for word in words)


def lower_camel(value: str) -> str:
    class_name = camel_case(value)
    if not class_name:
        return "handle"
    return class_name[:1].lower() + class_name[1:]


def snake_case(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized)
    normalized = normalized.strip("_")
    return normalized.lower()


def ascii_slug(value: str, *, fallback: str = "") -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-") or fallback


def normalize_ui_route(value: Any, *, slugger: Callable[[str], str] | None = None) -> str:
    candidate = str(value or "").replace("`", "").strip()
    if not candidate or candidate.lower() in {"—", "-", "none", "n/a"}:
        return ""
    slug = (slugger or ascii_slug)(candidate)
    return candidate if candidate.startswith("/") else f"/{slug}"


def ordered_ui_routes(values: list[Any], *, slugger: Callable[[str], str] | None = None) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        route = normalize_ui_route(value, slugger=slugger)
        if not route:
            continue
        key = route.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(route)
    return ordered


def runtime_spec_for_operation(
    operation: dict[str, str],
    operation_specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
    return operation_specs.get(operation_id, {})


def normalize_ui_role_name(value: Any, locale: str | None = None) -> str:
    candidate = re.sub(r"\s+", " ", str(value or "").strip().strip("`")).strip()
    if not candidate or locale is None:
        return candidate
    return normalize_role_display_name(candidate, locale) or candidate


def ordered_ui_roles(*groups: Any, locale: str | None = None) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in groups:
        items = group if isinstance(group, list) else [group]
        for item in items:
            role = normalize_ui_role_name(item, locale=locale)
            if not role:
                continue
            key = role.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(role)
    return ordered


def split_ui_role_candidates(raw: Any, locale: str | None = None) -> list[str]:
    text = normalize_ui_role_name(raw, locale=locale).strip("[]")
    if not text or text.lower() in {"—", "-", "none", "n/a", "not_applicable"}:
        return []
    candidates = [
        part.strip()
        for part in re.split(r"\s*(?:,|/|;|\||、|，|\band\b|\bor\b)\s*", text, flags=re.IGNORECASE)
        if part.strip()
    ]
    roles: list[str] = []
    for candidate in candidates or [text]:
        normalized = normalize_ui_role_name(candidate, locale=locale).strip("[]")
        if not normalized:
            continue
        if normalized.casefold() in UI_ROLE_POLICY_SKIP_TOKENS:
            continue
        roles.append(normalized)
    return ordered_ui_roles(roles, locale=locale)


def extract_ui_policy_roles(raw: Any, locale: str | None = None) -> list[str]:
    text = normalize_ui_role_name(raw, locale=locale)
    if not text or text.lower() in {"—", "-", "none", "n/a", "not_applicable"}:
        return []
    bracketed: list[str] = []
    for match in re.findall(r"\[([^\]]+)\]", text):
        bracketed.extend(split_ui_role_candidates(match, locale=locale))
    if bracketed:
        return ordered_ui_roles(bracketed, locale=locale)
    simplified = re.sub(
        r"\b(?:role|roles|allow|allows|allowed|require|requires|required|policy|visible|visibility)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    simplified = re.sub(
        r"\b(?:in|is|are|only|any|of|with|for|current|user|actor)\b",
        " ",
        simplified,
        flags=re.IGNORECASE,
    )
    simplified = re.sub(r"\s+", " ", simplified).strip(" -:")
    return split_ui_role_candidates(simplified, locale=locale)


def stable_uuid_seed(seed: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", str(seed).lower())
    alphabet = "abcdef0123456789"
    mapped = "".join(alphabet[ord(char) % len(alphabet)] for char in normalized)
    padded = (mapped + ("0" * 32))[:32]
    return f"{padded[:8]}-{padded[8:12]}-{padded[12:16]}-{padded[16:20]}-{padded[20:32]}"


def normalize_default_tenant_id(value: str) -> str:
    tenant = str(value).strip()
    if not tenant:
        return ""
    if UUID_LIKE_RE.fullmatch(tenant):
        return tenant.lower()
    return stable_uuid_seed(f"tenant_id:{tenant}")


def json_clone(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False))
