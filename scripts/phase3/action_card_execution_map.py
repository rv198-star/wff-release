#!/usr/bin/env python3
"""Build Phase-3 action-card execution maps from P2 component obligations."""

from __future__ import annotations

import hashlib
import json
from typing import Any


MAP_KIND = "phase3-action-card-execution-map.v1"
POINTER_MANIFEST_KIND = "phase3-action-card-pointer-manifest.v1"
RICH_CONTEXT_KIND = "phase3-action-card-execution-context.v1"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def build_action_card_execution_map(
    *,
    component_obligations: dict[str, dict[str, Any]],
    component_catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    operations: dict[str, dict[str, Any]] = {}
    components: dict[str, dict[str, Any]] = {}
    for component_id, obligation in component_obligations.items():
        catalog_row = component_catalog.get(component_id, {})
        source_refs = _unique_strings(
            _as_list(obligation.get("required_source_ids"))
            + _as_list(obligation.get("available_source_ids"))
            + _as_list(obligation.get("upstream_p1_trace_ids"))
        )
        component = {
            "component_id": component_id,
            "action_card_id": str(obligation.get("action_card_id") or component_id),
            "component_type": str(obligation.get("component_type") or catalog_row.get("component_type") or ""),
            "acd_level": str(obligation.get("acd_level") or "review-bound"),
            "required_card_type": str(obligation.get("required_card_type") or "review-bound-card"),
            "business_value_weight": str(obligation.get("business_value_weight") or ""),
            "engineering_risk_tier": str(obligation.get("engineering_risk_tier") or ""),
            "implementation_complexity": str(obligation.get("implementation_complexity") or ""),
            "source_sufficiency_status": str(obligation.get("source_sufficiency_status") or "review-bound"),
            "source_refs": source_refs,
            "required_tests": _unique_strings(_as_list(obligation.get("required_tests"))),
            "target_path_hint": str(catalog_row.get("target_path_hint") or ""),
            "review_bound_items": _unique_strings(
                _as_list(obligation.get("review_bound_missing_sources"))
                + _as_list(obligation.get("missing_source_types"))
            ),
        }
        components[component_id] = component
        operation_component = {
            "component_id": component_id,
            "action_card_id": component["action_card_id"],
            "component_type": component["component_type"],
            "acd_level": component["acd_level"],
            "target_path_hint": component["target_path_hint"],
        }
        for operation_id in _unique_strings(_as_list(obligation.get("upstream_operation_ids"))):
            operation = operations.setdefault(
                operation_id,
                {
                    "operation_id": operation_id,
                    "components": [],
                    "required_tests": [],
                    "source_refs": [],
                    "source_sufficiency_status": "sufficient",
                    "review_bound_items": [],
                },
            )
            operation["components"].append(operation_component)
            operation["required_tests"] = _unique_strings(operation["required_tests"] + component["required_tests"])
            operation["source_refs"] = _unique_strings(operation["source_refs"] + component["source_refs"])
            operation["review_bound_items"] = _unique_strings(
                operation["review_bound_items"] + component["review_bound_items"]
            )
            if component["source_sufficiency_status"] != "sufficient":
                operation["source_sufficiency_status"] = component["source_sufficiency_status"]
    return {
        "artifact_kind": MAP_KIND,
        "mode": "default-p3-mainline",
        "operations": operations,
        "components": components,
        "summary": {
            "operation_count": len(operations),
            "component_count": len(component_obligations),
            "review_bound_operation_count": sum(1 for item in operations.values() if item["review_bound_items"]),
        },
        "claim_ceiling": "action-card execution input only; generated quality requires strict-runtime and human Review",
    }


def _source_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True)
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def build_action_card_execution_context(
    *,
    component_obligations: dict[str, dict[str, Any]],
    component_catalog: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    rich_context = build_action_card_execution_map(
        component_obligations=component_obligations,
        component_catalog=component_catalog,
    )
    rich_context["artifact_kind"] = RICH_CONTEXT_KIND
    rich_context["mode"] = "default-p3-mainline-rich-context"

    operations: dict[str, dict[str, Any]] = {}
    action_cards: dict[str, dict[str, Any]] = {}
    action_card_ref_count = 0
    for operation_id, operation in rich_context.get("operations", {}).items():
        action_card_refs = []
        for component in _as_list(operation.get("components")):
            if not isinstance(component, dict):
                continue
            component_id = str(component.get("component_id") or "").strip()
            if not component_id:
                continue
            action_card_id = str(component.get("action_card_id") or component_id)
            action_cards.setdefault(
                action_card_id,
                {
                    "component_id": component_id,
                    "component_type": str(component.get("component_type") or ""),
                    "target_path_hint": str(component.get("target_path_hint") or ""),
                    "source_digest": _source_digest(component),
                },
            )
            action_card_refs.append(action_card_id)
            action_card_ref_count += 1
        operations[str(operation_id)] = {
            "action_card_refs": _unique_strings(action_card_refs),
        }

    pointer_manifest = {
        "artifact_kind": POINTER_MANIFEST_KIND,
        "mode": "default-p3-mainline-pointer-manifest",
        "operations": operations,
        "action_cards": action_cards,
        "summary": {
            "operation_count": len(operations),
            "action_card_ref_count": action_card_ref_count,
            "action_card_count": len(action_cards),
            "rich_context_persisted": False,
        },
        "claim_ceiling": (
            "pointer manifest only; rich context is in-memory and generated quality "
            "requires strict-runtime and human Review"
        ),
    }
    return {"pointer_manifest": pointer_manifest, "rich_context": rich_context}
