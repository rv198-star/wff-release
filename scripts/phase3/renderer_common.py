#!/usr/bin/env python3
"""
Shared deterministic helpers for Phase-3 renderers.
"""

from __future__ import annotations

import json
import hashlib
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
    identifier = "".join(word[:1].upper() + word[1:] for word in words)
    return ts_identifier(identifier, prefix="Generated")


def lower_camel(value: str) -> str:
    class_name = camel_case(value)
    if not class_name:
        return "handle"
    candidate = class_name[:1].lower() + class_name[1:]
    return ts_identifier(candidate, prefix="generated")


def snake_case(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized)
    normalized = normalized.strip("_")
    return normalized.lower()


def ts_identifier(value: str, *, prefix: str = "generated") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_$]+", "", str(value or ""))
    if not cleaned:
        cleaned = prefix
    if not re.match(r"^[A-Za-z_$]", cleaned):
        cleaned = f"{prefix or 'generated'}{cleaned[:1].upper()}{cleaned[1:]}"
    return cleaned


def ts_property_key(field_name: str) -> str:
    return field_name if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", field_name) else json.dumps(field_name, ensure_ascii=False)


def ts_property_access(field_name: str) -> str:
    return f".{field_name}" if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", field_name) else f"[{json.dumps(field_name, ensure_ascii=False)}]"


def ts_optional_property_access(field_name: str) -> str:
    return f"?.{field_name}" if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", field_name) else f"?.[{json.dumps(field_name, ensure_ascii=False)}]"


def ascii_slug(value: str, *, fallback: str = "") -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-") or fallback


def unicode_slug(value: str, *, fallback: str = "") -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", str(value or ""))
    normalized = normalized.replace("_", "-")
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", "-", normalized, flags=re.UNICODE)
    normalized = re.sub(r"-+", "-", normalized).strip("-").lower()
    return normalized or fallback


def normalize_ui_route(value: Any, *, slugger: Callable[[str], str] | None = None) -> str:
    candidate = str(value or "").replace("`", "").strip()
    if not candidate or candidate.lower() in {"—", "-", "none", "n/a"}:
        return ""
    slug = (slugger or unicode_slug)(candidate)
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


def unique_ui_page_routes(
    pages: list[dict[str, Any]],
    *,
    route_value: Callable[[dict[str, Any], int], Any],
    identity_value: Callable[[dict[str, Any], int], Any],
    page_id_value: Callable[[dict[str, Any], int], Any] | None = None,
    slugger: Callable[[str], str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """Project page routes to stable, non-colliding paths.

    The first list is the normalized raw route per page, the second list is the
    final route per page, and the third list is the page id per page.
    """
    raw_routes: list[str] = []
    page_ids: list[str] = []
    counts: dict[str, int] = {}
    for index, page in enumerate(pages):
        identity = str(identity_value(page, index) or f"surface-{index + 1}").strip() or f"surface-{index + 1}"
        raw_route = normalize_ui_route(route_value(page, index), slugger=slugger) or normalize_ui_route(identity, slugger=slugger)
        raw_routes.append(raw_route)
        page_id = str(page_id_value(page, index) if page_id_value is not None else "").strip()
        page_ids.append(page_id)
        if raw_route:
            key = raw_route.casefold()
            counts[key] = counts.get(key, 0) + 1

    final_routes: list[str] = []
    used: set[str] = set()
    for index, page in enumerate(pages):
        identity = str(identity_value(page, index) or page_ids[index] or f"surface-{index + 1}").strip() or f"surface-{index + 1}"
        raw_route = raw_routes[index]
        needs_projection = not raw_route or counts.get(raw_route.casefold(), 0) > 1
        candidate = normalize_ui_route(identity if needs_projection else raw_route, slugger=slugger)
        if not candidate:
            candidate = f"/surface-{index + 1}"
        base = candidate.rstrip("/") or candidate
        candidate_key = candidate.casefold()
        if candidate_key in used:
            suffix_seed = page_ids[index] or f"surface-{index + 1}"
            suffix = (slugger or ascii_slug)(suffix_seed)
            candidate = f"{base}-{suffix}".replace("//", "/")
            candidate_key = candidate.casefold()
        ordinal = 2
        while candidate_key in used:
            candidate = f"{base}-{ordinal}".replace("//", "/")
            candidate_key = candidate.casefold()
            ordinal += 1
        used.add(candidate_key)
        final_routes.append(candidate)
    return raw_routes, final_routes, page_ids


def rewrite_ui_route_reference(
    value: Any,
    *,
    raw_routes: list[str],
    final_routes: list[str],
    page_ids: list[str] | None = None,
    target_page_id: Any = "",
    current_index: int | None = None,
    duplicate_strategy: str = "next",
    slugger: Callable[[str], str] | None = None,
) -> str:
    if target_page_id and page_ids:
        target_key = str(target_page_id).strip().casefold()
        for index, page_id in enumerate(page_ids):
            if page_id.casefold() == target_key and index < len(final_routes):
                return final_routes[index]

    route = normalize_ui_route(value, slugger=slugger)
    if not route:
        return ""
    final_key_set = {item.casefold() for item in final_routes if item}
    if route.casefold() in final_key_set:
        return route

    matches = [
        index
        for index, raw_route in enumerate(raw_routes)
        if raw_route and raw_route.casefold() == route.casefold() and index < len(final_routes)
    ]
    if len(matches) == 1:
        return final_routes[matches[0]]
    if not matches:
        return route

    if duplicate_strategy == "current" and current_index is not None and current_index in matches:
        return final_routes[current_index]
    if duplicate_strategy == "previous" and current_index is not None:
        previous_matches = [index for index in matches if index < current_index]
        if previous_matches:
            return final_routes[previous_matches[-1]]
    if duplicate_strategy == "next" and current_index is not None:
        next_matches = [index for index in matches if index > current_index]
        if next_matches:
            return final_routes[next_matches[0]]
    if current_index is not None:
        non_current_matches = [index for index in matches if index != current_index]
        if non_current_matches:
            return final_routes[non_current_matches[0]]
        if current_index in matches:
            return final_routes[current_index]
    return final_routes[matches[0]]


def rewrite_ui_route_references(
    values: list[Any],
    *,
    raw_routes: list[str],
    final_routes: list[str],
    page_ids: list[str] | None = None,
    current_index: int | None = None,
    duplicate_strategy: str = "next",
    slugger: Callable[[str], str] | None = None,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        route = rewrite_ui_route_reference(
            value,
            raw_routes=raw_routes,
            final_routes=final_routes,
            page_ids=page_ids,
            current_index=current_index,
            duplicate_strategy=duplicate_strategy,
            slugger=slugger,
        )
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
    digest = hashlib.sha256(str(seed).lower().encode("utf-8")).hexdigest()[:32]
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def normalize_default_tenant_id(value: str) -> str:
    tenant = str(value).strip()
    if not tenant:
        return ""
    if UUID_LIKE_RE.fullmatch(tenant):
        return tenant.lower()
    return stable_uuid_seed(f"tenant_id:{tenant}")


def json_clone(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False))
