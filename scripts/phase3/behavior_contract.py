"""Shared Phase-3 behavior-card contract helpers.

These helpers keep behavior-card evidence, payload enrichment, and response
aliasing consistent across service, unit, contract, and scenario scaffolds.
"""

from __future__ import annotations

import json
import re
from typing import Any

from phase3.renderer_common import ts_property_access


def snake_case(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized)
    return normalized.strip("_").lower()


def camel_field(value: str) -> str:
    return re.sub(r"_([a-z0-9])", lambda match: match.group(1).upper(), snake_case(value))


def behavior_evidence_keys(model: dict[str, Any] | None) -> list[str]:
    if not isinstance(model, dict):
        return []
    semantics = model.get("operation_semantics") if isinstance(model.get("operation_semantics"), dict) else {}
    keys = semantics.get("evidence_keys") if isinstance(semantics.get("evidence_keys"), list) else []
    return [str(key).strip() for key in keys if str(key).strip()]


def behavior_evidence_key_map(operation_ids: list[str], behavior_card_models: dict[str, dict[str, Any]] | None) -> dict[str, list[str]]:
    return {operation_id: behavior_evidence_keys((behavior_card_models or {}).get(operation_id)) for operation_id in operation_ids}


def typescript_array_literal(values: list[str]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def typescript_behavior_card_payload_helper_lines(*, map_name: str | None = None) -> list[str]:
    evidence_parameter = f"{map_name}: Record<string, string[]>" if map_name else "evidenceKeys: string[]"
    evidence_source = f"{map_name}[operationId] ?? []" if map_name else "evidenceKeys"
    return [
        f"function buildBehaviorCardPayload(operationId: string, payload: Record<string, unknown>, {evidence_parameter}): Record<string, unknown> {{",
        "  const enriched: Record<string, unknown> = { ...payload };",
        "  const authContext = enriched.auth_context && typeof enriched.auth_context === 'object' ? enriched.auth_context as Record<string, unknown> : {};",
        "  const pathParams = enriched.path_params && typeof enriched.path_params === 'object' ? enriched.path_params as Record<string, unknown> : {};",
        "  const isListReadOperation = operationId.startsWith('List');",
        f"  for (const key of {evidence_source}) {{",
        "    const camelKey = key.replace(/_([a-z0-9])/g, (_, char: string) => char.toUpperCase());",
        "    const existingEvidenceValue = enriched[key] ?? enriched[camelKey] ?? pathParams[key] ?? pathParams[camelKey] ?? authContext[key] ?? authContext[camelKey];",
        "    if (existingEvidenceValue !== undefined) {",
        "      if (enriched[key] === undefined && enriched[camelKey] === undefined && pathParams[key] === undefined && pathParams[camelKey] === undefined) {",
        "        enriched[camelKey] = existingEvidenceValue;",
        "      }",
        "      continue;",
        "    }",
        "    if (isListReadOperation && key.endsWith('_id') && key !== 'tenant_id') {",
        "      continue;",
        "    }",
        "    if (key === 'tenant_id') {",
        "      const tenantEvidence = authContext.tenant_id ?? authContext.tenantId ?? enriched.tenantId;",
        "      if (tenantEvidence !== undefined) {",
        "        enriched.tenant_id = tenantEvidence;",
        "      }",
        "    } else if (key === 'version') {",
        "      enriched.version = 1;",
        "      enriched.expectedVersion = enriched.expectedVersion ?? 1;",
        "    }",
        "  }",
        "  return enriched;",
        "}",
        "",
    ]


def typescript_behavior_payload_expr(
    operation_expr: str,
    payload_expr: str,
    *,
    evidence_expr: str,
) -> str:
    return f"buildBehaviorCardPayload({operation_expr}, {payload_expr}, {evidence_expr})"


def response_field_source_expr(field: str, evidence_keys: list[str], *, include_runtime_projection: bool = False) -> str:
    normalized_field = snake_case(field)
    camel = camel_field(normalized_field)
    sources = [f"nextState{ts_property_access(field)}", f"context{ts_property_access(field)}"]
    if include_runtime_projection:
        sources.append(f"responseSource{ts_property_access(field)}")
    for alias in (normalized_field, camel):
        if alias == field:
            continue
        sources.extend([f"nextState{ts_property_access(alias)}", f"context{ts_property_access(alias)}"])
        if include_runtime_projection:
            sources.append(f"responseSource{ts_property_access(alias)}")
    for evidence_key in evidence_keys:
        normalized_evidence = snake_case(evidence_key)
        if normalized_field != normalized_evidence:
            continue
        camel_evidence = camel_field(normalized_evidence)
        for alias in (normalized_evidence, camel_evidence):
            sources.extend([f"nextState{ts_property_access(alias)}", f"context{ts_property_access(alias)}"])
            if include_runtime_projection:
                sources.append(f"responseSource{ts_property_access(alias)}")
    return " ?? ".join(dict.fromkeys(sources))
