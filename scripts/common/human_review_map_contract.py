"""Shared structured contract for P1/P2 human-review map projections."""

from __future__ import annotations

from typing import Any


REVIEW_MAP_SCHEMA_BY_KIND = {
    "prd-core": "wff.p1-human-review-map-bundle.v1",
    "esp-core": "wff.p2-human-review-map-bundle.v1",
}
REVIEW_MAP_ROLE_BY_KIND = {
    "prd-core": "product-diagram",
    "esp-core": "architecture-diagram",
}
ROLE_EXPECTED_REVIEW_BUNDLE = {
    "product-diagram": REVIEW_MAP_SCHEMA_BY_KIND["prd-core"],
    "architecture-diagram": REVIEW_MAP_SCHEMA_BY_KIND["esp-core"],
}
ROLE_EXPECTED_REVIEW_VIEWS = {
    "product-diagram": ("business-landscape", "business-scenarios"),
    "architecture-diagram": (
        "technical-architecture",
        "service-modules",
        "critical-sequences",
    ),
}
RESPONSIBILITY_STATES = {"primary", "support", "review", "none"}
ARCHITECTURE_NODE_STATES = {"standard", "domain", "review-bound"}
SCENARIO_STEP_TONES = {"business", "architecture", "signal", "review"}
SERVICE_OPERATION_KINDS = {"C", "Q", "E"}
SEQUENCE_STEP_KINDS = {"sync", "async", "return"}


def _string() -> dict[str, Any]:
    return {"type": "string", "minLength": 1}


def _string_array(*, allow_empty: bool = False) -> dict[str, Any]:
    return {
        "type": "array",
        "items": _string(),
        **({} if allow_empty else {"minItems": 1}),
    }


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def _array(item: dict[str, Any], *, allow_empty: bool = False) -> dict[str, Any]:
    return {
        "type": "array",
        "items": item,
        **({} if allow_empty else {"minItems": 1}),
    }


def _common_view(view_type: str, extra: dict[str, Any]) -> dict[str, Any]:
    return _object(
        {
            "type": {"const": view_type},
            "id": _string(),
            "title": _string(),
            "summary": _string(),
            "tag": _string(),
            "diagram_title": _string(),
            "diagram_note": _string(),
            "caption": _string(),
            "source_refs": _string_array(),
            **extra,
        }
    )


def _prd_views() -> list[dict[str, Any]]:
    role = _object({"id": _string(), "label": _string(), "description": _string()})
    use_case = _object(
        {
            "id": _string(),
            "name": _string(),
            "goal": _string(),
            "responsibilities": {
                "type": "object",
                "minProperties": 1,
                "propertyNames": {"type": "string", "minLength": 1},
                "additionalProperties": {
                    "type": "string",
                    "enum": sorted(RESPONSIBILITY_STATES),
                },
            },
            "features": _string_array(),
        }
    )
    lane = _object({"id": _string(), "label": _string(), "description": _string()})
    step = _object(
        {
            "id": _string(),
            "lane_id": _string(),
            "title": _string(),
            "detail": _string(),
            "tone": {"type": "string", "enum": sorted(SCENARIO_STEP_TONES)},
        }
    )
    scenario = _object(
        {
            "id": _string(),
            "label": _string(),
            "title": _string(),
            "summary": _string(),
            "lanes": _array(lane),
            "steps": _array(step),
            "context": _string_array(allow_empty=True),
            "object_chain": _string_array(allow_empty=True),
            "caption": _string(),
        }
    )
    return [
        _common_view(
            "business-landscape",
            {"roles": _array(role), "use_cases": _array(use_case)},
        ),
        _common_view("business-scenarios", {"scenarios": _array(scenario)}),
    ]


def _esp_views() -> list[dict[str, Any]]:
    node = _object(
        {
            "name": _string(),
            "detail": _string(),
            "state": {"type": "string", "enum": sorted(ARCHITECTURE_NODE_STATES)},
        }
    )
    layer = _object(
        {
            "id": _string(),
            "name": _string(),
            "namespace": _string(),
            "nodes": _array(node),
        }
    )
    named_detail = _object({"name": _string(), "detail": _string()})
    operation = _object(
        {
            "name": _string(),
            "kind": {"type": "string", "enum": sorted(SERVICE_OPERATION_KINDS)},
            "description": _string(),
            "output": _string(),
        }
    )
    service = _object(
        {
            "name": _string(),
            "responsibility": _string(),
            "operations": _array(operation),
        }
    )
    module = _object(
        {
            "id": _string(),
            "index": _string(),
            "category": _string(),
            "name": _string(),
            "summary": _string(),
            "description": _string(),
            "namespace": _string(),
            "services": _array(service),
            "contract_note": _string(),
        }
    )
    participant = _object({"id": _string(), "label": _string(), "detail": _string()})
    sequence_step = _object(
        {
            "from": _string(),
            "to": _string(),
            "kind": {"type": "string", "enum": sorted(SEQUENCE_STEP_KINDS)},
            "label": _string(),
            "detail": _string(),
        }
    )
    sequence = _object(
        {
            "id": _string(),
            "label": _string(),
            "title": _string(),
            "summary": _string(),
            "participants": _array(participant),
            "steps": _array(sequence_step),
            "caption": _string(),
        }
    )
    return [
        _common_view(
            "technical-architecture",
            {
                "system_label": _string(),
                "external_nodes": _array(node, allow_empty=True),
                "layers": _array(layer),
                "crosscutting": _array(named_detail),
            },
        ),
        _common_view(
            "service-modules",
            {"crosscutting": _string_array(), "modules": _array(module)},
        ),
        _common_view("critical-sequences", {"sequences": _array(sequence)}),
    ]


def review_map_bundle_schema(projection_kind: str) -> dict[str, Any]:
    if projection_kind not in REVIEW_MAP_SCHEMA_BY_KIND:
        raise ValueError(f"unsupported review map projection kind: {projection_kind}")
    views = _prd_views() if projection_kind == "prd-core" else _esp_views()
    return _object(
        {
            "schema_version": {"const": REVIEW_MAP_SCHEMA_BY_KIND[projection_kind]},
            "views": {
                "type": "array",
                "prefixItems": views,
                "items": False,
                "minItems": len(views),
                "maxItems": len(views),
            },
        }
    )
