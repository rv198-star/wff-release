#!/usr/bin/env python3
"""Derive lightweight Phase-2 project-language handoff inputs for Phase-3."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


HANDOFF_KIND = "phase2-project-language-handoff.v1"


def _listish(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return [part for part in re.split(r"[^A-Za-z0-9]+", spaced) if part]


def _upper_camel(value: str) -> str:
    return "".join(word[:1].upper() + word[1:].lower() for word in _words(value))


def _singularize_word(word: str) -> str:
    if len(word) > 3 and word.endswith("ies"):
        return f"{word[:-3]}y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _strip_operation_prefix(value: str) -> str:
    candidate = _text(value)
    for prefix in (
        "Create",
        "Update",
        "Patch",
        "Manage",
        "Record",
        "Submit",
        "Approve",
        "Reject",
        "Delete",
        "Archive",
        "Launch",
        "Export",
        "Get",
        "List",
        "Search",
    ):
        if candidate.startswith(prefix) and len(candidate) > len(prefix):
            return candidate[len(prefix) :]
    return candidate


def _normalize_domain_candidate(value: str) -> str:
    words = _words(_strip_operation_prefix(value))
    while len(words) > 1 and words[-1].lower() in {
        "status",
        "state",
        "detail",
        "details",
        "summary",
        "summaries",
        "list",
        "view",
        "history",
        "report",
        "result",
        "results",
    }:
        words = words[:-1]
    return _upper_camel(" ".join(_singularize_word(word.lower()) for word in words))


def _domain_name_from_target_path_hint(value: str) -> str:
    match = re.search(r"modules/([^/]+)/", value)
    if match:
        words = [_singularize_word(word.lower()) for word in _words(match.group(1))]
        return _upper_camel(" ".join(words))
    filename = Path(value).name if value else ""
    if filename:
        stem = re.sub(r"\.(service|repository|controller|module|spec|test)$", "", Path(filename).stem)
        return _normalize_domain_candidate(stem)
    return ""


def _component_numeric_id(component_id: str) -> str:
    match = re.search(r"P2-CMP-0*([0-9]+)", component_id, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).zfill(3)


def _forbidden_names(component_id: str) -> list[str]:
    numeric = _component_numeric_id(component_id)
    if not numeric:
        return []
    return [f"P2CMP{numeric}Service", f"P2CMP{numeric}"]


def _components_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    components = payload.get("components") if isinstance(payload, dict) else []
    if isinstance(payload, dict) and not isinstance(components, list):
        if all(isinstance(value, dict) for value in payload.values()):
            return {
                _text(key): dict(value)
                for key, value in payload.items()
                if _text(key) and isinstance(value, dict)
            }
    result: dict[str, dict[str, Any]] = {}
    for item in _listish(components):
        if not isinstance(item, dict):
            continue
        component_id = _text(item.get("component_id"))
        if component_id:
            result[component_id] = item
    return result


def _preferred_domain_name(component: dict[str, Any]) -> str:
    explicit = _text(component.get("preferred_domain_name") or component.get("domain_name"))
    if explicit and not re.fullmatch(r"P2[-_]?CMP[-_]?[0-9]+", explicit, flags=re.IGNORECASE):
        return _upper_camel(explicit)
    for key in ("owning_module", "component_name", "name", "responsibility", "summary"):
        candidate = _text(component.get(key))
        if not candidate:
            continue
        if re.fullmatch(r"P2[-_]?CMP[-_]?[0-9]+", candidate, flags=re.IGNORECASE):
            continue
        if key == "responsibility":
            words = _words(candidate)
            return _upper_camel(" ".join(words[:3]))
        return _normalize_domain_candidate(candidate)
    target_path_hint = _text(component.get("target_path_hint"))
    if target_path_hint:
        return _domain_name_from_target_path_hint(target_path_hint)
    return ""


def _domain_glossary(entries: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        term = _text(entry.get("term") or entry.get("name"))
        if not term or term in seen:
            continue
        result.append(
            {
                "term": term,
                "meaning": _text(entry.get("meaning") or entry.get("working_definition") or entry.get("definition")),
                "source_refs": [_text(item) for item in _listish(entry.get("source_refs")) if _text(item)],
            }
        )
        seen.add(term)
    return result


def build_project_language_handoff(
    *,
    component_catalog: dict[str, Any] | None = None,
    component_obligations: dict[str, Any] | None = None,
    domain_glossary: list[Any] | None = None,
    ui_surface_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog_by_id = _components_by_id(component_catalog or {})
    obligations_by_id = _components_by_id(component_obligations or {})
    component_ids = sorted({*catalog_by_id.keys(), *obligations_by_id.keys()})
    responsibilities: list[dict[str, Any]] = []
    missing_language_gaps: list[dict[str, Any]] = []
    bounded_contexts: list[dict[str, Any]] = []

    for component_id in component_ids:
        catalog_entry = catalog_by_id.get(component_id, {})
        obligation_entry = obligations_by_id.get(component_id, {})
        merged = {**obligation_entry, **catalog_entry}
        preferred_name = _preferred_domain_name(merged)
        source_refs = [
            _text(item)
            for item in [*_listish(merged.get("source_refs")), *_listish(merged.get("required_source_ids"))]
            if _text(item)
        ]
        responsibility = _text(merged.get("responsibility") or merged.get("summary") or merged.get("component_name"))
        responsibilities.append(
            {
                "component_id": component_id,
                "preferred_domain_name": preferred_name,
                "responsibility": responsibility,
                "operation_ids": [
                    _text(item)
                    for item in [*_listish(merged.get("operation_ids")), *_listish(merged.get("upstream_operation_ids"))]
                    if _text(item)
                ],
                "source_refs": sorted(set(source_refs)),
                "forbidden_names": _forbidden_names(component_id),
            }
        )
        if not preferred_name:
            missing_language_gaps.append(
                {
                    "component_id": component_id,
                    "gap_type": "missing-source-backed-project-language",
                    "reason": "component has no source-backed domain name, responsibility, or glossary term",
                }
            )
        else:
            bounded_contexts.append(
                {
                    "context": preferred_name,
                    "aggregate_candidates": [preferred_name],
                    "component_refs": [component_id],
                }
            )

    ui_context = ui_surface_context if isinstance(ui_surface_context, dict) else {}
    ui_ux_intent = {
        "applicable": bool(ui_context.get("applicable", False)),
        "reason": _text(ui_context.get("reason") or ("frontend/UI surface declared" if ui_context.get("applicable") else "no frontend/UI surface declared")),
        "surface_posture": _text(ui_context.get("surface_posture")),
        "interaction_principles": [_text(item) for item in _listish(ui_context.get("interaction_principles")) if _text(item)],
    }

    return {
        "artifact_kind": HANDOFF_KIND,
        "domain_glossary": _domain_glossary(domain_glossary or []),
        "bounded_contexts": bounded_contexts,
        "component_responsibilities": responsibilities,
        "ui_ux_intent": ui_ux_intent,
        "missing_language_gaps": missing_language_gaps,
        "claim_ceiling": "P2 language handoff informs implementation conventions; P3 still owns stack-specific realization",
    }
