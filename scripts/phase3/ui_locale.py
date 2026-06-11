#!/usr/bin/env python3
"""Slim Phase-3 UI locale helpers.

The full fallback/UI copy catalog lives in ``ui_locale_full.py`` and is packaged
only by full-pack/source-tree profiles. Slim implementation profiles only need
role-display normalization through ``renderer_common``.
"""

from __future__ import annotations

import importlib
import re
from typing import Any


_CJK_RE = re.compile(r"[㐀-䶿一-鿿]")
_FULL_MODULE_NAME = "phase3.ui_locale_full"


def _full_module():
    try:
        return importlib.import_module(_FULL_MODULE_NAME)
    except ModuleNotFoundError as exc:
        if exc.name in {_FULL_MODULE_NAME, "phase3"}:
            raise RuntimeError("full UI locale helpers require full-pack/source-tree ui_locale_full.py") from exc
        raise


def _full_call(name: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(_full_module(), name)(*args, **kwargs)


def normalize_ui_locale(locale: str | None) -> str:
    candidate = str(locale or "").strip().lower()
    if candidate.startswith("zh"):
        return "zh-CN"
    return "en"


def is_zh_locale(locale: str | None) -> bool:
    return normalize_ui_locale(locale) == "zh-CN"


def infer_ui_locale(*values: object, preferred: str | None = None) -> str:
    return _full_call("infer_ui_locale", *values, preferred=preferred)


def ui_text(locale: str | None, key: str, **kwargs: object) -> str:
    return _full_call("ui_text", locale, key, **kwargs)


def _fallback_humanize_identifier(value: str) -> str:
    candidate = re.sub(r"([a-z0-9])([A-Z])", r" ", str(value)).replace("_", " ").replace("-", " ")
    tokens = [token for token in candidate.split() if token]
    normalized: list[str] = []
    for token in tokens:
        lowered = token.lower()
        if lowered in {"id", "api", "cta", "roi"}:
            normalized.append(lowered.upper())
        else:
            normalized.append(lowered.capitalize())
    return " ".join(normalized) or "Field"


def normalize_inline_locale_variants(text: str, locale: str | None) -> str:
    candidate = str(text or "").strip()
    if not candidate:
        return ""

    def choose_side(match: re.Match[str]) -> str:
        left = match.group(1).strip()
        right = match.group(2).strip()
        left_has_cjk = bool(_CJK_RE.search(left))
        right_has_cjk = bool(_CJK_RE.search(right))
        if left_has_cjk == right_has_cjk:
            return match.group(0)
        if is_zh_locale(locale):
            return left if left_has_cjk else right
        return right if left_has_cjk else left

    normalized = re.sub(r"([^()]{1,48})\s*\(([^()]{1,48})\)", choose_side, candidate)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_role_display_name(value: str, locale: str | None) -> str:
    candidate = normalize_inline_locale_variants(value, locale).strip().strip("`")
    if not candidate:
        return ""
    if re.fullmatch(r"[a-z0-9 _/\-]+", candidate):
        candidate = candidate.replace("_", " ").replace("/", " ").replace("-", " ")
        return re.sub(r"\s+", " ", candidate).strip()
    if re.fullmatch(r"[A-Za-z0-9 _/\-]+", candidate) and ("_" in candidate or "-" in candidate):
        candidate = _fallback_humanize_identifier(candidate.replace("/", " "))
    return re.sub(r"\s+", " ", candidate).strip()


def normalize_surface_display_title(
    surface: str,
    locale: str | None,
    *,
    page_role: str = "",
    business_objects: list[str] | None = None,
) -> str:
    return _full_call(
        "normalize_surface_display_title",
        surface,
        locale,
        page_role=page_role,
        business_objects=business_objects,
    )


def localize_surface_title(surface: str, locale: str | None) -> str:
    return _full_call("localize_surface_title", surface, locale)


def localize_information_object(value: str, locale: str | None) -> str:
    return _full_call("localize_information_object", value, locale)


def ui_field_label(field: str, locale: str | None) -> str:
    return _full_call("ui_field_label", field, locale)


def page_role_eyebrow(page_role: str, locale: str | None) -> str:
    return _full_call("page_role_eyebrow", page_role, locale)


def page_role_label(page_role: str, locale: str | None) -> str:
    return _full_call("page_role_label", page_role, locale)


def view_label(view: str, locale: str | None) -> str:
    return _full_call("view_label", view, locale)


def surface_shell_copy(surface: str, page_role: str, locale: str | None) -> dict[str, str]:
    return _full_call("surface_shell_copy", surface, page_role, locale)


def surface_success_copy(surface: str, page_role: str, locale: str | None) -> dict[str, str]:
    return _full_call("surface_success_copy", surface, page_role, locale)
