#!/usr/bin/env python3
"""
Generate executable contract-test scaffolds from an OpenAPI document.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
from collections import Counter
import json
import re
from pathlib import Path

from phase3.phase3_behavior_card_consumption import render_behavior_step_test_mapping
try:
    from phase3.behavior_contract import (
        behavior_evidence_keys,
        typescript_array_literal,
        typescript_behavior_card_payload_helper_lines,
    )
except ModuleNotFoundError:
    from phase3.behavior_contract import (
        behavior_evidence_keys,
        typescript_array_literal,
        typescript_behavior_card_payload_helper_lines,
    )
from phase3.contract_tools import load_openapi_document


def sanitize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def contract_test_filename(operation_id: str, method: str, path: str) -> str:
    base = sanitize_name(operation_id) or sanitize_name(f"{method}-{path}")
    return f"{base}.contract.test.ts"


def _contract_operation_identity(operation: dict[str, object]) -> tuple[str, str, str]:
    method = str(operation.get("method", "")).upper()
    path = str(operation.get("path", "")).strip()
    operation_id = str(operation.get("operation_id") or operation.get("operationId") or f"{method}-{path}").strip()
    return operation_id, method, path


def build_contract_test_target_lookup(operations: list[dict[str, object]]) -> dict[tuple[str, str, str], str]:
    normalized = [_contract_operation_identity(operation) for operation in operations]
    base_counts = Counter(contract_test_filename(operation_id, method, path) for operation_id, method, path in normalized)
    lookup: dict[tuple[str, str, str], str] = {}
    used_targets: set[str] = set()

    for operation_id, method, path in normalized:
        base = contract_test_filename(operation_id, method, path)
        target = base
        if base_counts[base] > 1:
            stem = base.removesuffix(".contract.test.ts")
            path_suffix = sanitize_name(f"{method}-{path}") or sanitize_name(path) or sanitize_name(method) or "operation"
            target = f"{stem}--{path_suffix}.contract.test.ts"

        if target in used_targets:
            stem = target.removesuffix(".contract.test.ts")
            collision_suffix = sanitize_name(f"{operation_id}-{method}-{path}") or "operation"
            target = f"{stem}--{collision_suffix}.contract.test.ts"

        used_targets.add(target)
        lookup[(operation_id, method, path)] = target

    return lookup


def _snake_case(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", normalized)
    return normalized.strip("_").lower()


def _create_like_persistence_hint(operation_id: str, response_example: object) -> tuple[str, str] | None:
    if not operation_id.startswith(("Create", "Launch", "Export")):
        return None
    response = response_example if isinstance(response_example, dict) else {}
    data = response.get("data", {}) if isinstance(response, dict) else {}
    if not isinstance(data, dict):
        return None
    id_keys = [key for key in data.keys() if isinstance(key, str) and (key.endswith("_id") or key.endswith("Id"))]
    if not id_keys:
        return None
    pk = _snake_case(id_keys[0])
    if not pk.endswith("_id"):
        return None
    table_name = _snake_case(operation_id.removeprefix("Create").removeprefix("Launch").removeprefix("Export"))
    if not table_name:
        return None
    return table_name, pk


CREATE_LIKE_OPERATION_PREFIXES = ("Create", "Launch", "Export")
ROUNDTRIP_OPERATION_PREFIXES = (*CREATE_LIKE_OPERATION_PREFIXES, "List", "Update", "Start", "Complete", "Generate", "Record", "Refresh")
WRITE_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _response_has_roundtrip_record(response_example: object) -> bool:
    response = response_example if isinstance(response_example, dict) else {}
    data = response.get("data", {}) if isinstance(response, dict) else {}
    if isinstance(data, list):
        return bool(data)
    return isinstance(data, dict) and bool(data)


def _requires_persistence_roundtrip(operation_id: str, method: str, response_example: object) -> bool:
    if not _response_has_roundtrip_record(response_example):
        return False
    if method.upper() in WRITE_HTTP_METHODS:
        return True
    return operation_id.startswith(ROUNDTRIP_OPERATION_PREFIXES)


def _requires_duplicate_submit_contract(
    operation_id: str,
    method: str,
    response_example: object,
    failure_cases: list[dict[str, str]],
    idempotency_rule: str = "",
) -> bool:
    normalized_rule = str(idempotency_rule).strip().lower().replace("-", "_")
    has_duplicate_or_idempotency_rule = any(str(failure.get("status", "")).startswith("409") for failure in failure_cases)
    if normalized_rule and normalized_rule not in {"none", "not_applicable", "not applicable", "read_only", "read-only", "n/a"}:
        has_duplicate_or_idempotency_rule = any(
            token in normalized_rule
            for token in (
                "idempot",
                "unique",
                "dedupe",
                "duplicate",
                "caller token",
                "business key",
                "scope_key",
                "natural key",
            )
        )
    return (
        method.upper() in WRITE_HTTP_METHODS
        and operation_id.startswith(CREATE_LIKE_OPERATION_PREFIXES)
        and _requires_persistence_roundtrip(operation_id, method, response_example)
        and has_duplicate_or_idempotency_rule
    )


def _requires_transaction_rollback_contract(operation_id: str, method: str, response_example: object) -> bool:
    return method.upper() in WRITE_HTTP_METHODS and _requires_persistence_roundtrip(operation_id, method, response_example)


def _data_example_record(response_example: object) -> dict[str, object]:
    response = response_example if isinstance(response_example, dict) else {}
    data = response.get("data", {}) if isinstance(response, dict) else {}
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return {}


def _is_business_literal_field(field_name: str, value: object) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", field_name.lower())
    if normalized in {"traceid", "createdat", "updatedat"} or normalized.endswith("id"):
        return False
    return isinstance(value, (str, int, float, bool)) and value is not None


def _ts_property_access(field_name: str) -> str:
    if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", field_name):
        return f".{field_name}"
    return f"[{json.dumps(field_name, ensure_ascii=False)}]"


def explicit_business_assertion_lines(response_example: object) -> list[str]:
    record = _data_example_record(response_example)
    literal_fields = [(field, value) for field, value in record.items() if _is_business_literal_field(field, value)]
    if not literal_fields:
        return []
    lines = ["    const data = Array.isArray(result.data) ? result.data[0] : result.data as Record<string, unknown>;"]
    for field, value in literal_fields:
        lines.append(f"    expect(data{_ts_property_access(field)}).toBe({json.dumps(value, ensure_ascii=False)});")
    return lines


def schema_has_pagination_contract(success_schema: object) -> bool:
    if not isinstance(success_schema, dict):
        return False
    properties = success_schema.get("properties", {})
    return isinstance(properties, dict) and isinstance(properties.get("pagination"), dict)


def pagination_assertion_lines(success_schema: object) -> list[str]:
    if not schema_has_pagination_contract(success_schema):
        return []
    return [
        "    expect(result).toHaveProperty('pagination');",
        "    expect(result.pagination).toMatchObject({",
        "      hasMore: expect.any(Boolean),",
        "      pageSize: expect.any(Number),",
        "    });",
        "    expect(result.pagination.nextCursor === null || typeof result.pagination.nextCursor === 'string').toBe(true);",
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


def operation_uses_write_database_path(method: str) -> bool:
    return str(method).upper() in WRITE_HTTP_METHODS


def failure_requires_database_restore(failure: dict[str, str], *, method: str) -> bool:
    if not operation_uses_write_database_path(method):
        return False
    status = str(failure.get("status", "")).strip()
    normalized = str(failure.get("error_code", "")).strip().lower()
    if status.startswith("5"):
        return True
    if status == "404" or "not_found" in normalized:
        return True
    if any(token in normalized for token in ("conflict", "stale", "version", "duplicate", "dependency", "unavailable")):
        return True
    return False



def render_contract_test(
    *,
    operation_id: str,
    method: str,
    path: str,
    request_example: object,
    response_example: object,
    success_schema: object | None = None,
    failure_cases: list[dict[str, str]],
    idempotency_rule: str = "",
    behavior_card_model: dict[str, object] | None = None,
) -> str:
    del request_example
    evidence_keys = behavior_evidence_keys(behavior_card_model)
    evidence_keys_literal = typescript_array_literal(evidence_keys)
    success_payload_expr = f"buildBehaviorCardPayload(operationId, buildOperationPayload(operationId), {evidence_keys_literal})"
    requires_roundtrip = _requires_persistence_roundtrip(operation_id, method, response_example)
    requires_duplicate_submit = _requires_duplicate_submit_contract(
        operation_id,
        method,
        response_example,
        failure_cases,
        idempotency_rule,
    )
    requires_transaction_rollback = _requires_transaction_rollback_contract(operation_id, method, response_example)
    uses_write_database_path = operation_uses_write_database_path(method)
    requires_write_audit = method.upper() in WRITE_HTTP_METHODS
    response_blob = json.dumps(response_example, ensure_ascii=False, indent=2)
    top_level_shape_keys = ["trace_id", "request_id", "meta"]
    if schema_has_pagination_contract(success_schema or {}):
        top_level_shape_keys.append("pagination")
    top_level_shape_keys_blob = json.dumps(top_level_shape_keys, ensure_ascii=False)
    support_imports = [
        "buildFailurePayload",
        "buildOperationPayload",
        "captureApiError",
        "invokeHttpOperation",
        "invokeHttpOperationWithAuthHeader",
        "startBackendRuntime",
        "type BackendRuntime",
    ]
    if requires_roundtrip:
        support_imports[2:2] = [
            "collectPersistenceTargetRowCounts",
            "collectPersistenceRoundTripEvidence",
            "requiresPersistenceRoundTripEvidence",
        ]
    lines = [
        'import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";',
        'import {',
        *[f"  {entry}," for entry in support_imports],
        '} from "../support/backend-runtime-harness";',
        "",
        f'const operationId = "{operation_id}";',
        f"const responseExample = {response_blob};",
        "",
        "let runtime: BackendRuntime;",
        "",
    ]
    lines.extend(
        [
            "function isIdentifierField(key: string): boolean {",
            '  return key.endsWith("_id") || key.endsWith("Id");',
            "}",
            "",
            "function expectedObjectKeys(expected: Record<string, unknown>, fieldName: string): string[] {",
            '  if (fieldName === "" && "data" in expected) {',
            f"    return Array.from(new Set([...Object.keys(expected), ...{top_level_shape_keys_blob}])).sort();",
            "  }",
            "  return Object.keys(expected).sort();",
            "}",
            "",
            "function expectContractShape(actual: unknown, expected: unknown, fieldName = \"\"): void {",
            "  if (Array.isArray(expected)) {",
            "    expect(Array.isArray(actual)).toBe(true);",
            "    expect((actual as unknown[]).length).toBe(expected.length);",
            "    expected.forEach((item, index) => expectContractShape((actual as unknown[])[index], item, fieldName));",
            "    return;",
            "  }",
            '  if (expected && typeof expected === "object") {',
            "    expect(actual).toBeTruthy();",
            "    const actualRecord = actual as Record<string, unknown>;",
            "    const expectedRecord = expected as Record<string, unknown>;",
            "    expect(Object.keys(actualRecord).sort()).toEqual(expectedObjectKeys(expectedRecord, fieldName));",
            '    if (fieldName === "" && "data" in expectedRecord) {',
            '      expect(actualRecord.trace_id).toEqual(expect.any(String));',
            '      expect(actualRecord.request_id).toEqual(expect.any(String));',
            '      expect(actualRecord.meta).toEqual(expect.any(Object));',
            "    }",
            "    for (const [key, value] of Object.entries(expectedRecord)) {",
            "      expectContractShape(actualRecord[key], value, key);",
            "    }",
            "    return;",
            "  }",
            '  if (typeof expected === "string" && isIdentifierField(fieldName)) {',
            "    expect(actual).toEqual(expect.any(String));",
            "    return;",
            "  }",
            "  expect(actual).toEqual(expected);",
            "}",
            "",
        ]
    )
    if requires_duplicate_submit:
        lines.extend(
            [
                "function collectEvidenceTableCounts(runtime: BackendRuntime, evidence: Array<{ tableName: string; matchedRows: number }>): Map<string, number> {",
                "  void runtime;",
                "  const counts = new Map<string, number>();",
                "  for (const entry of evidence) {",
                "    counts.set(entry.tableName, (counts.get(entry.tableName) ?? 0) + Number(entry.matchedRows ?? 0));",
                "  }",
                "  return counts;",
                "}",
                "",
                "function expectEvidenceTableCountsUnchanged(beforeCounts: Map<string, number>, afterCounts: Map<string, number>): void {",
                "  expect(Array.from(afterCounts.keys()).sort()).toEqual(Array.from(beforeCounts.keys()).sort());",
                "  for (const [tableName, beforeCount] of beforeCounts.entries()) {",
                "    expect(afterCounts.get(tableName)).toBe(beforeCount);",
                "  }",
                "}",
                "",
            ]
        )
    lines.extend(typescript_behavior_card_payload_helper_lines(map_name=None))
    lines.extend(
        [
        "beforeAll(async () => {",
        "  runtime = await startBackendRuntime();",
        "  await runtime.initializeDatabase();",
        "});",
        "",
        "afterAll(async () => {",
        "  await runtime.close();",
        "});",
        "",
        "let scenarioInitialized = true;",
        "",
        "beforeEach(async () => {",
        "  if (scenarioInitialized) {",
        "    scenarioInitialized = false;",
        "    return;",
        "  }",
        "  await runtime.restoreRuntimeOnly();",
        "});",
        "",
        f'describe("Contract: {method.upper()} {path}", () => {{',
        *(render_behavior_step_test_mapping(behavior_card_model)["contract"].splitlines() if behavior_card_model else []),
        '  it("rejects missing bearer token before business handling", async () => {',
        "    const missingTokenPayload = buildOperationPayload(operationId);",
        "    delete missingTokenPayload.auth_context;",
        "    delete missingTokenPayload.authContext;",
        "    const error = await captureApiError(invokeHttpOperation(runtime, operationId, missingTokenPayload));",
        "    expect(error.status).toBe(401);",
        '    expect(error.envelope.error_kind).toBe("auth_error");',
        '    expect(error.envelope.error_code).toBe("missing_bearer_token");',
        "    const auditRecords = runtime.getAuditRecords();",
        "    expect(auditRecords.some((entry) => entry.operation_id === operationId && entry.outcome === \"denied\" && entry.reason === \"missing_bearer_token\")).toBe(true);",
        "  });",
        "",
        '  it("rejects invalid bearer token before business handling", async () => {',
        "    const error = await captureApiError(",
        '      invokeHttpOperationWithAuthHeader(runtime, operationId, buildOperationPayload(operationId), "Bearer phase3-invalid-token"),',
        "    );",
        "    expect(error.status).toBe(401);",
        '    expect(error.envelope.error_kind).toBe("auth_error");',
        '    expect(error.envelope.error_code).toBe("invalid_auth_token");',
        "    const auditRecords = runtime.getAuditRecords();",
        "    expect(auditRecords.some((entry) => entry.operation_id === operationId && entry.outcome === \"denied\" && entry.reason === \"invalid_auth_token\")).toBe(true);",
        '    expect(JSON.stringify(auditRecords)).not.toContain("phase3-invalid-token");',
        "  });",
        "",
        '  it("rejects valid bearer token with insufficient role", async () => {',
        "    const basePayload = buildOperationPayload(operationId);",
        "    const baseAuthContext = basePayload.auth_context && typeof basePayload.auth_context === 'object'",
        "      ? basePayload.auth_context as Record<string, unknown>",
        "      : {};",
        "    const forbiddenPayload = {",
        "      ...basePayload,",
        "      auth_context: {",
        "        ...baseAuthContext,",
        '        subject_id: "user_forbidden",',
        '        session_id: "sess_forbidden",',
        '        roles: ["phase3_forbidden_role"],',
        "      },",
        "    };",
        "    const error = await captureApiError(invokeHttpOperation(runtime, operationId, forbiddenPayload));",
        "    expect(error.status).toBe(403);",
        '    expect(error.envelope.error_code).toBe("rbac_forbidden");',
        "    const auditRecords = runtime.getAuditRecords();",
        "    expect(auditRecords.some((entry) => entry.operation_id === operationId && entry.outcome === \"denied\" && entry.reason === \"rbac_forbidden\")).toBe(true);",
        "  });",
        "",
        '  it("accepts valid bearer token before business validation", async () => {',
        "    const result = await invokeHttpOperation(runtime, operationId, buildOperationPayload(operationId));",
        "    expectContractShape(result, responseExample);",
        "    expect(result).toHaveProperty('trace_id');",
        "    expect(result).toHaveProperty('data');",
        *(
            [
                "    const auditRecords = runtime.getAuditRecords();",
                "    expect(auditRecords.some((entry) => entry.operation_id === operationId && entry.outcome === \"allowed\")).toBe(true);",
            ]
            if requires_write_audit
            else []
        ),
        "  });",
        "",
        '  it("documented OpenAPI request is directly executable", async () => {',
        *( ["    await runtime.restoreScenario();"] if uses_write_database_path else [] ),
        "    const result = await invokeHttpOperation(runtime, operationId, buildOperationPayload(operationId));",
        "    expectContractShape(result, responseExample);",
        "    expect(result).toHaveProperty('trace_id');",
        "    expect(result).toHaveProperty('data');",
        "  });",
        "",
        '  it("happy path matches the frozen contract", async () => {',
        *( ["    await runtime.restoreScenario();"] if uses_write_database_path else [] ),
        f"    const result = await invokeHttpOperation(runtime, operationId, {success_payload_expr});",
        "    expectContractShape(result, responseExample);",
        "    expect(result).toHaveProperty('trace_id');",
        "    expect(result).toHaveProperty('data');",
        *pagination_assertion_lines(success_schema),
        *explicit_business_assertion_lines(response_example),
        (
            "\n".join(
                [
                    "    const persistenceEvidence = await collectPersistenceRoundTripEvidence(runtime, operationId, result);",
                    "    if (await requiresPersistenceRoundTripEvidence(runtime, operationId)) {",
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
            )
            if requires_roundtrip
            else ""
        ),
        "  });",
        ]
    )
    if requires_duplicate_submit:
        lines.extend(
            [
                "",
                '  it("duplicate submit does not create duplicate durable state", async () => {',
                "    await runtime.restoreScenario();",
                f"    const payload = {success_payload_expr};",
                "    const firstResult = await invokeHttpOperation(runtime, operationId, payload);",
                "    const beforeEvidence = await collectPersistenceRoundTripEvidence(runtime, operationId, firstResult);",
                "    const beforeTableCounts = collectEvidenceTableCounts(runtime, beforeEvidence);",
                "    if (await requiresPersistenceRoundTripEvidence(runtime, operationId)) {",
                "      expect(beforeEvidence.length).toBeGreaterThan(0);",
                "    }",
                "    const beforeAllowedAuditCount = runtime.getAuditRecords()",
                "      .filter((entry) => entry.operation_id === operationId && entry.outcome === \"allowed\").length;",
                "    const duplicatePayload = JSON.parse(JSON.stringify(payload)) as Record<string, unknown>;",
                "    const duplicateError = await captureApiError(invokeHttpOperation(runtime, operationId, duplicatePayload));",
                "    expect(duplicateError.status).toBe(409);",
                "    const afterEvidence = await collectPersistenceRoundTripEvidence(runtime, operationId, firstResult);",
                "    const afterTableCounts = collectEvidenceTableCounts(runtime, afterEvidence);",
                "    expectEvidenceTableCountsUnchanged(beforeTableCounts, afterTableCounts);",
                "    const afterAllowedAuditCount = runtime.getAuditRecords()",
                "      .filter((entry) => entry.operation_id === operationId && entry.outcome === \"allowed\").length;",
                "    expect(afterAllowedAuditCount).toBe(beforeAllowedAuditCount);",
                "    const duplicateAuditRecords = runtime.getAuditRecords()",
                "      .filter((entry) => entry.operation_id === operationId && entry.outcome === \"duplicate\");",
                "    expect(duplicateAuditRecords.length).toBeGreaterThan(0);",
                "  });",
            ]
        )
    if requires_transaction_rollback:
        lines.extend(
            [
                "",
                '  it("transaction rollback probe leaves durable state unchanged", async () => {',
                "    await runtime.restoreScenario();",
                "    if (!(await requiresPersistenceRoundTripEvidence(runtime, operationId))) {",
                "      return;",
                "    }",
                "    const beforeTargetRowCounts = await collectPersistenceTargetRowCounts(runtime, operationId);",
                "    const rollbackPayload = {",
                f"      ...{success_payload_expr},",
                "      force_transaction_rollback_probe: true,",
                "    };",
                "    const rollbackError = await captureApiError(invokeHttpOperation(runtime, operationId, rollbackPayload));",
                '    expect(rollbackError.envelope.error_code).toBe("forced_transaction_rollback_probe");',
                "    const afterTargetRowCounts = await collectPersistenceTargetRowCounts(runtime, operationId);",
                "    expect(afterTargetRowCounts).toEqual(beforeTargetRowCounts);",
                "  });",
            ]
        )
    for failure in failure_cases:
        label = f'{failure["status"]} {failure["error_code"]}'.strip()
        lines.extend(
            [
                "",
                f'  it("failure: {label}", async () => {{',
                *(
                    ["    await runtime.restoreScenario();"]
                    if failure_requires_database_restore(failure, method=method)
                    else []
                ),
                f'    const payload = buildFailurePayload(operationId, "{failure["error_code"] or failure["status"]}");',
                *failure_condition_signal_lines(failure["error_code"] or failure["status"]),
                "    const error = await captureApiError(invokeHttpOperation(runtime, operationId, payload));",
                f'    expect(error.status).toBe({failure["status"]});',
                f'    expect(error.envelope.error_code).toBe("{failure["error_code"]}");',
                "  });",
            ]
        )
    lines.extend(["});", ""])
    return "\n".join(lines)


def scaffold_contract_tests(
    spec: dict[str, object],
    output_dir: Path,
    *,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        raise ValueError("openapi document missing paths object")

    operations: list[dict[str, object]] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operations.append(
                {
                    "operationId": str(operation.get("operationId", f"{method}-{path}")),
                    "method": str(method).upper(),
                    "path": str(path),
                }
            )
    target_lookup = build_contract_test_target_lookup(operations)

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId", f"{method}-{path}"))
            responses = operation.get("responses", {})
            if not isinstance(responses, dict) or not responses:
                raise ValueError(f"operation missing responses: {operation_id}")

            success_status = next((code for code in sorted(responses) if code.startswith("2")), "200")
            success_response = responses.get(success_status, {})
            if not isinstance(success_response, dict):
                success_response = {}
            success_content = success_response.get("content", {})
            success_example = {}
            success_schema: object = {}
            if isinstance(success_content, dict):
                app_json = success_content.get("application/json", {})
                if isinstance(app_json, dict):
                    success_example = app_json.get("example", {})
                    success_schema = app_json.get("schema", {})

            request_example = {}
            request_body = operation.get("requestBody", {})
            if isinstance(request_body, dict):
                request_content = request_body.get("content", {})
                if isinstance(request_content, dict):
                    app_json = request_content.get("application/json", {})
                    if isinstance(app_json, dict):
                        request_example = app_json.get("example", {})

            failure_cases: list[dict[str, str]] = []
            for status, response in responses.items():
                if not str(status).startswith(("4", "5")):
                    continue
                if not isinstance(response, dict):
                    continue
                error_example = {}
                content = response.get("content", {})
                if isinstance(content, dict):
                    app_json = content.get("application/json", {})
                    if isinstance(app_json, dict):
                        error_example = app_json.get("example", {})
                failure_cases.append(
                    {
                        "status": str(status),
                        "error_code": str(error_example.get("error_code", "")).strip(),
                    }
                )

            target_name = target_lookup[(operation_id, str(method).upper(), str(path))]
            target = output_dir / target_name
            target.write_text(
                render_contract_test(
                    operation_id=operation_id,
                    method=method,
                    path=str(path),
                    request_example=request_example,
                    response_example=success_example,
                    success_schema=success_schema,
                    failure_cases=failure_cases,
                    idempotency_rule=str(operation.get("x-idempotency-rule", "")).strip(),
                    behavior_card_model=(behavior_card_models or {}).get(operation_id),
                ),
                encoding="utf-8",
            )
            created.append(str(target))

    return {"output_dir": str(output_dir), "files_created": created, "count": len(created)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate failing contract tests from OpenAPI")
    parser.add_argument("--openapi", required=True, help="Path to openapi.yaml generated for Phase-3")
    parser.add_argument("--output-dir", required=True, help="Target directory for *.contract.test.ts files")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    spec = load_openapi_document(Path(args.openapi).resolve())
    summary = scaffold_contract_tests(spec, Path(args.output_dir).resolve())
    print(json.dumps(summary, ensure_ascii=False))
    return 0


# Backward-compatible alias for older imports; keep it out of pytest collection.
test_filename = contract_test_filename
test_filename.__test__ = False


if __name__ == "__main__":
    raise SystemExit(main())
