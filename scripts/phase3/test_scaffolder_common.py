#!/usr/bin/env python3
"""Shared deterministic helpers for Phase-3 test scaffolders."""

from __future__ import annotations

import re
from typing import Any


PERSISTENCE_ROUNDTRIP_OPERATION_PREFIXES = (
    "Create",
    "List",
    "Update",
    "Start",
    "Complete",
    "Generate",
    "Launch",
    "Export",
    "Record",
    "Refresh",
)
WRITE_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def unique_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def endpoint_index(endpoint_rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(row["endpoint_name"]).strip(): row for row in endpoint_rows}


def response_data_for_operation(endpoint_rows: list[dict[str, object]], operation_id: str) -> object:
    row = endpoint_index(endpoint_rows).get(operation_id, {})
    response = row.get("response_body_example", {})
    if isinstance(response, dict):
        return response.get("data", {})
    return {}


def response_data_fields(endpoint_rows: list[dict[str, object]], operation_id: str) -> list[str]:
    data = response_data_for_operation(endpoint_rows, operation_id)
    if isinstance(data, dict):
        return list(data.keys())
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return list(data[0].keys())
    return []


def normalize_field_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def resolve_response_field(
    endpoint_rows: list[dict[str, object]],
    operation_ids: list[str],
    candidates: list[str],
    *,
    preferred_operation_id: str = "",
) -> str:
    ordered_operations = [preferred_operation_id, *operation_ids] if preferred_operation_id else list(operation_ids)
    seen_operations: set[str] = set()
    normalized_candidates = [normalize_field_token(candidate) for candidate in candidates]
    for operation_id in ordered_operations:
        if not operation_id or operation_id in seen_operations:
            continue
        seen_operations.add(operation_id)
        fields = response_data_fields(endpoint_rows, operation_id)
        by_token = {normalize_field_token(field): field for field in fields}
        for candidate in normalized_candidates:
            if candidate in by_token:
                return by_token[candidate]
    return ""


def operation_supports_persistence_roundtrip(operation_id: str, endpoint_rows: list[dict[str, object]]) -> bool:
    endpoint_row = next(
        (row for row in endpoint_rows if str(row.get("endpoint_name", "")).strip() == operation_id),
        {},
    )
    response_example = endpoint_row.get("response_body_example", {}) if isinstance(endpoint_row, dict) else {}
    data = response_example.get("data", {}) if isinstance(response_example, dict) else {}
    has_roundtrip_record = (isinstance(data, list) and bool(data)) or (isinstance(data, dict) and bool(data))
    if not has_roundtrip_record:
        return False
    method = str((endpoint_row or {}).get("method", "")).strip().upper()
    return method in WRITE_HTTP_METHODS or operation_id.startswith(PERSISTENCE_ROUNDTRIP_OPERATION_PREFIXES)


def persistence_roundtrip_assertion_lines(operation_id_expr: str, result_expr: str) -> list[str]:
    return [
        f"    const persistenceEvidence = await collectPersistenceRoundTripEvidence(runtime, {operation_id_expr}, {result_expr});",
        f"    if (await requiresPersistenceRoundTripEvidence(runtime, {operation_id_expr})) {{",
        "      expect(persistenceEvidence.length).toBeGreaterThan(0);",
        "      const fullyMatchedEvidence = persistenceEvidence.filter((entry) => entry.mismatchedFieldNames.length === 0);",
        "      expect(fullyMatchedEvidence.length).toBeGreaterThan(0);",
        "      const evidenceWithValueFields = persistenceEvidence.filter((entry) => entry.checkedValueFieldNames.length > 0);",
        "      if (evidenceWithValueFields.length > 0) {",
        "        expect(fullyMatchedEvidence.some((entry) => entry.checkedValueFieldNames.length > 0)).toBe(true);",
        "      } else {",
        "        expect(fullyMatchedEvidence.some((entry) => entry.checkedFieldNames.length > 0)).toBe(true);",
        "      }",
        "    }",
    ]


def failure_condition_signal_lines(error_code: str, payload_name: str = "payload") -> list[str]:
    normalized = error_code.lower()
    if "tenant_forbidden" in normalized:
        return [
            f"    const existingAuthContext = {payload_name}.auth_context && typeof {payload_name}.auth_context === 'object'",
            f"      ? {payload_name}.auth_context as Record<string, unknown>",
            "      : {};",
            f"    {payload_name}.auth_context = {{",
            "      ...existingAuthContext,",
            '      tenant_id: "wrong-tenant",',
            '      subject_id: String(existingAuthContext.subject_id ?? "user_forbidden"),',
            '      session_id: String(existingAuthContext.session_id ?? "sess_forbidden"),',
            "      roles: Array.isArray(existingAuthContext.roles) && existingAuthContext.roles.length > 0",
            "        ? existingAuthContext.roles",
            '        : ["authenticated"],',
            "    };",
            f'    {payload_name}.expectedOwnerService = "OtherService";',
        ]
    if "rbac_forbidden" in normalized:
        return [
            f"    const existingAuthContext = {payload_name}.auth_context && typeof {payload_name}.auth_context === 'object'",
            f"      ? {payload_name}.auth_context as Record<string, unknown>",
            "      : {};",
            f"    {payload_name}.auth_context = {{",
            "      ...existingAuthContext,",
            '      subject_id: "user_forbidden",',
            '      session_id: "sess_forbidden",',
            '      roles: ["phase3_forbidden_role"],',
            "    };",
        ]
    if "forbidden" in normalized:
        return [
            f"    const existingAuthContext = {payload_name}.auth_context && typeof {payload_name}.auth_context === 'object'",
            f"      ? {payload_name}.auth_context as Record<string, unknown>",
            "      : {};",
            f"    {payload_name}.auth_context = {{",
            "      ...existingAuthContext,",
            '      subject_id: "user_forbidden",',
            '      session_id: "sess_forbidden",',
            "      roles: Array.isArray(existingAuthContext.roles) && existingAuthContext.roles.length > 0",
            "        ? existingAuthContext.roles",
            '        : ["authenticated"],',
            "    };",
            f'    {payload_name}.expectedOwnerService = "OtherService";',
        ]
    if any(token in normalized for token in ("conflict", "stale", "version", "duplicate")):
        return [
            f"    {payload_name}.expectedVersion = 0;",
            f"    {payload_name}.currentVersion = 1;",
        ]
    if "not_found" in normalized or "missing" in normalized:
        return [
            f"    {payload_name}.path_params = {{ ...(({payload_name}.path_params ?? {{}}) as Record<string, unknown>), id: \"missing_id\" }};",
            f'    {payload_name}.not_found_id = "missing_record";',
        ]
    if "dependency" in normalized or "unavailable" in normalized:
        return [
            f"    {payload_name}.simulateDependencyFailure = true;",
        ]
    return []


def remap_operation_ids_to_runtime_contract(
    operation_ids: list[str],
    *,
    source_endpoint_rows: list[dict[str, object]],
    runtime_endpoint_rows: list[dict[str, object]],
) -> list[str]:
    runtime_names = {str(row.get("endpoint_name", "")).strip() for row in runtime_endpoint_rows}
    source_by_name = {str(row.get("endpoint_name", "")).strip(): row for row in source_endpoint_rows}
    runtime_by_signature = {
        (
            str(row.get("method", "")).strip().upper(),
            str(row.get("path", "")).strip(),
        ): str(row.get("endpoint_name", "")).strip()
        for row in runtime_endpoint_rows
        if str(row.get("endpoint_name", "")).strip()
    }
    mapped: list[str] = []
    for operation_id in operation_ids:
        if operation_id in runtime_names:
            mapped.append(operation_id)
            continue
        source_row = source_by_name.get(operation_id)
        if not source_row:
            continue
        signature = (
            str(source_row.get("method", "")).strip().upper(),
            str(source_row.get("path", "")).strip(),
        )
        runtime_operation_id = runtime_by_signature.get(signature, "")
        if runtime_operation_id:
            mapped.append(runtime_operation_id)
    return dedupe_preserve_order(mapped)


def render_harness_import(generated_text: str) -> list[str]:
    always = [
        "  extractEnvelopeData,",
        "  invokeHttpOperation,",
        "  startBackendRuntime,",
        "  type BackendRuntime,",
    ]
    conditional = [
        ("absorbEnvelopeContext", "  absorbEnvelopeContext,"),
        ("applyRuntimeContext", "  applyRuntimeContext,"),
        ("buildFailurePayload", "  buildFailurePayload,"),
        ("buildOperationPayload", "  buildOperationPayload,"),
        ("collectPersistenceRoundTripEvidence", "  collectPersistenceRoundTripEvidence,"),
        ("captureApiError", "  captureApiError,"),
        ("normalizeRuntimeIdentifierValue", "  normalizeRuntimeIdentifierValue,"),
        ("requiresPersistenceRoundTripEvidence", "  requiresPersistenceRoundTripEvidence,"),
    ]
    imports = [line for token, line in conditional if token in generated_text]
    return [
        'import {',
        *sorted(set(imports)),
        *always,
        '} from "../support/backend-runtime-harness";',
    ]
