#!/usr/bin/env python3
"""
Generate executable replay-test scaffolds from Stage-04 verification replay evidence.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import re
from pathlib import Path

from phase3.phase3_behavior_card_consumption import render_behavior_step_test_mapping
from phase3.contract_tools import (
    camel_and_word_tokens,
    endpoint_rows_from_openapi_spec,
    parse_api_endpoint_rows,
    parse_replay_rows,
    parse_scenario_rows,
    replay_test_filename,
)


PERSISTENCE_ROUNDTRIP_OPERATION_PREFIXES = ("Create", "List", "Update", "Start", "Complete", "Generate", "Launch", "Export", "Record", "Refresh")
WRITE_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


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


def extract_scenario_refs(raw: str) -> list[str]:
    return [match.group(1).upper() for match in re.finditer(r"\b(SCN-[A-Z0-9][A-Z0-9-]*)\b", raw, flags=re.IGNORECASE)]


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def explicit_operation_mentions(raw: str, endpoint_names: set[str]) -> list[str]:
    cleaned = raw.strip()
    if not cleaned:
        return []
    hits: list[tuple[int, int, str]] = []
    for endpoint_name in endpoint_names:
        for match in re.finditer(re.escape(endpoint_name), cleaned, flags=re.IGNORECASE):
            hits.append((match.start(), match.end(), endpoint_name))
    hits.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2]))
    filtered_hits: list[tuple[int, int, str]] = []
    for start, end, endpoint_name in hits:
        shadowed = any(
            other_name != endpoint_name
            and (other_end - other_start) > (end - start)
            and other_start <= start
            and other_end >= end
            for other_start, other_end, other_name in hits
        )
        if not shadowed:
            filtered_hits.append((start, end, endpoint_name))
    return dedupe_preserve_order([endpoint_name for _, _, endpoint_name in filtered_hits])


def operation_runtime_order_rank(operation_id: str) -> int:
    for prefix, rank in (
        ("Create", 10),
        ("Start", 20),
        ("Complete", 30),
        ("Update", 40),
        ("Record", 50),
        ("Generate", 60),
        ("List", 70),
        ("Get", 80),
    ):
        if operation_id.startswith(prefix):
            return rank
    return 90


def order_operation_ids_for_runtime(operation_ids: list[str]) -> list[str]:
    indexed = {operation_id: index for index, operation_id in enumerate(dedupe_preserve_order(operation_ids))}
    return sorted(
        indexed,
        key=lambda operation_id: (operation_runtime_order_rank(operation_id), indexed[operation_id]),
    )


def endpoint_index(endpoint_rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(row["endpoint_name"]).strip(): row for row in endpoint_rows}


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


def collect_failure_codes(endpoint_rows: list[dict[str, object]], operation_ids: list[str]) -> list[str]:
    by_name = endpoint_index(endpoint_rows)
    failure_codes: list[str] = []
    for operation_id in operation_ids:
        for failure in by_name.get(operation_id, {}).get("failure_codes", []):
            code = str(failure.get("error_code", "")).strip()
            if code:
                failure_codes.append(code)
    return list(dict.fromkeys(failure_codes))


def first_matching_failure_code(failure_codes: list[str], pattern: str) -> str:
    regex = re.compile(pattern)
    for code in failure_codes:
        if regex.search(code):
            return code
    return ""


def infer_operation_ids(
    row: dict[str, object],
    *,
    endpoint_rows: list[dict[str, object]],
    scenario_operation_map: dict[str, list[str]],
) -> list[str]:
    source_artifacts = str(row.get("source_artifacts", ""))
    operation_ids: list[str] = []
    endpoint_names = {str(item["endpoint_name"]).strip() for item in endpoint_rows}
    for scenario_id in extract_scenario_refs(source_artifacts):
        operation_ids.extend(scenario_operation_map.get(scenario_id, []))
    if operation_ids:
        return dedupe_preserve_order(operation_ids)

    query = " ".join(
        [
            str(row.get("replay_id", "")),
            str(row.get("scenario_or_contract", "")),
            str(row.get("semantic_bridge_note", "")),
            source_artifacts,
            str(row.get("expected_outcome", "")),
        ]
    )
    explicit = explicit_operation_mentions(query, endpoint_names)
    if explicit:
        return order_operation_ids_for_runtime(explicit)
    query_tokens = camel_and_word_tokens(query)
    scored: list[tuple[int, str]] = []
    for endpoint in endpoint_rows:
        endpoint_name = str(endpoint["endpoint_name"]).strip()
        haystack = " ".join(
            [
                endpoint_name,
                str(endpoint.get("path", "")),
                str(endpoint.get("purpose", "")),
                " ".join(str(item.get("error_code", "")) for item in endpoint.get("failure_codes", [])),
            ]
        )
        score = len(query_tokens & camel_and_word_tokens(haystack))
        lowered_query = query.lower()
        lowered_haystack = haystack.lower()
        if endpoint_name.lower() in lowered_query:
            score += 5
        if "tenant" in lowered_query and "tenant_forbidden" in lowered_haystack:
            score += 3
        if "audit" in lowered_query and "audit" in lowered_haystack:
            score += 3
        if score > 0:
            scored.append((score, endpoint_name))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = [name for _, name in scored[:4]]
    return order_operation_ids_for_runtime(selected)


def response_data_for_operation(endpoint_rows: list[dict[str, object]], operation_id: str) -> object:
    row = endpoint_index(endpoint_rows).get(operation_id, {})
    response = row.get("response_body_example", {})
    if isinstance(response, dict):
        return response.get("data", {})
    return {}


def response_id_fields(endpoint_rows: list[dict[str, object]], operation_id: str) -> list[str]:
    data = response_data_for_operation(endpoint_rows, operation_id)
    if isinstance(data, dict):
        return [key for key in data if key.endswith("_id")]
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return [key for key in data[0] if key.endswith("_id")]
    return []


def response_data_fields(endpoint_rows: list[dict[str, object]], operation_id: str) -> list[str]:
    data = response_data_for_operation(endpoint_rows, operation_id)
    if isinstance(data, dict):
        return list(data.keys())
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return list(data[0].keys())
    return []


def response_is_array(endpoint_rows: list[dict[str, object]], operation_id: str) -> bool:
    return isinstance(response_data_for_operation(endpoint_rows, operation_id), list)


def response_data_example_record(endpoint_rows: list[dict[str, object]], operation_id: str) -> dict[str, object]:
    data = response_data_for_operation(endpoint_rows, operation_id)
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return {}


def ts_property_access(field: str) -> str:
    return f".{field}" if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", field) else f"[{json.dumps(field, ensure_ascii=False)}]"


def literal_ts_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def scalar_business_value_fields(endpoint_rows: list[dict[str, object]], operation_id: str) -> dict[str, object]:
    record = response_data_example_record(endpoint_rows, operation_id)
    values: dict[str, object] = {}
    for field, value in record.items():
        normalized = normalize_field_token(field)
        if normalized in {"traceid", "createdat", "updatedat"} or normalized.endswith("id"):
            continue
        if isinstance(value, (str, int, float, bool)) and value is not None:
            values[field] = value
    return values


def shared_response_business_fields(endpoint_rows: list[dict[str, object]], first_operation_id: str, final_operation_id: str) -> list[str]:
    first_fields = set(response_data_example_record(endpoint_rows, first_operation_id).keys())
    final_fields = set(response_data_example_record(endpoint_rows, final_operation_id).keys())
    return [
        field
        for field in response_data_fields(endpoint_rows, final_operation_id)
        if field in first_fields and (field.endswith("Id") or field.endswith("_id"))
    ]


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


def choose_semantic_review_operation(endpoint_rows: list[dict[str, object]], operation_ids: list[str]) -> str:
    explicit = next((operation for operation in operation_ids if operation == "GetReviewReportDetail"), "")
    if explicit:
        return explicit
    for operation_id in operation_ids:
        if resolve_response_field(
            endpoint_rows,
            [operation_id],
            ["uncertainty_level", "uncertaintyLevel", "uncertainty_note", "uncertaintyNote"],
            preferred_operation_id=operation_id,
        ):
            return operation_id
    return next((operation for operation in operation_ids if "review" in operation.lower()), operation_ids[0] if operation_ids else "")


def semantic_assertion_lines(
    row: dict[str, object],
    *,
    endpoint_rows: list[dict[str, object]],
    operation_ids: list[str],
    preferred_operation_id: str,
    data_expr: str,
) -> list[str]:
    lowered = " ".join(
        [
            str(row.get("scenario_or_contract", "")).lower(),
            str(row.get("expected_outcome", "")).lower(),
            str(row.get("semantic_bridge_note", "")).lower(),
        ]
    )
    lines: list[str] = []
    uncertainty_level_field = resolve_response_field(
        endpoint_rows,
        operation_ids,
        ["uncertainty_level", "uncertaintyLevel"],
        preferred_operation_id=preferred_operation_id,
    )
    if uncertainty_level_field and ("uncertainty" in lowered or "review" in lowered):
        lines.append(
            f'    expect(["low", "medium", "high", "critical", "review_bound"]).toContain(String({data_expr}.{uncertainty_level_field}));'
        )
    uncertainty_note_field = resolve_response_field(
        endpoint_rows,
        operation_ids,
        ["uncertainty_note", "uncertaintyNote"],
        preferred_operation_id=preferred_operation_id,
    )
    if uncertainty_note_field and ("uncertainty" in lowered or "review" in lowered):
        lines.append(f"    expect(String({data_expr}.{uncertainty_note_field} ?? '')).not.toHaveLength(0);")
    decision_posture_field = resolve_response_field(
        endpoint_rows,
        operation_ids,
        ["decision_posture", "decisionPosture", "closure_recommendation", "closureRecommendation", "continue_or_revise", "continueOrRevise"],
        preferred_operation_id=preferred_operation_id,
    )
    if decision_posture_field and ("closure" in lowered or "review" in lowered or "revise" in lowered or "continue" in lowered):
        lines.extend(
            [
                f"    expect(String({data_expr}.{decision_posture_field} ?? '')).not.toHaveLength(0);",
                f"    expect(String({data_expr}.{decision_posture_field} ?? '').toLowerCase()).toMatch(/continue|revise|collect/);",
            ]
        )
    threshold_rationale_field = resolve_response_field(
        endpoint_rows,
        operation_ids,
        ["threshold_rationale", "thresholdRationale"],
        preferred_operation_id=preferred_operation_id,
    )
    if threshold_rationale_field and ("threshold" in lowered or "rationale" in lowered or "review" in lowered):
        lines.append(f"    expect(String({data_expr}.{threshold_rationale_field} ?? '')).not.toHaveLength(0);")
    return lines


def primary_id_field(endpoint_rows: list[dict[str, object]], operation_id: str) -> str:
    fields = response_id_fields(endpoint_rows, operation_id)
    return fields[0] if fields else ""


def record_key_for_operation(endpoint_rows: list[dict[str, object]], operation_id: str) -> str:
    return primary_id_field(endpoint_rows, operation_id)


def operation_supports_failure(endpoint_rows: list[dict[str, object]], operation_id: str, failure_code: str) -> bool:
    if not failure_code:
        return False
    row = endpoint_index(endpoint_rows).get(operation_id, {})
    return any(str(item.get("error_code", "")).strip() == failure_code for item in row.get("failure_codes", []))


def choose_failure_operation(operation_ids: list[str], endpoint_rows: list[dict[str, object]], failure_code: str) -> str:
    for operation_id in operation_ids:
        if operation_supports_failure(endpoint_rows, operation_id, failure_code):
            return operation_id
    return operation_ids[0] if operation_ids else ""


def expected_context_fields(endpoint_rows: list[dict[str, object]], operation_ids: list[str]) -> list[str]:
    fields: list[str] = []
    for operation_id in operation_ids:
        fields.extend(response_id_fields(endpoint_rows, operation_id))
    return sorted(dict.fromkeys(field for field in fields if field))


def preferred_failure_code(
    row: dict[str, object],
    *,
    endpoint_rows: list[dict[str, object]],
    operation_ids: list[str],
) -> str:
    lowered = " ".join(
        [
            str(row.get("scenario_or_contract", "")).lower(),
            str(row.get("expected_outcome", "")).lower(),
        ]
    )
    failure_codes = collect_failure_codes(endpoint_rows, operation_ids)
    deny_intent = any(term in lowered for term in ("cross-tenant", "tenant deny", "tenant_forbidden", "forbidden", "deny"))
    if deny_intent:
        return (
            first_matching_failure_code(failure_codes, r"tenant_forbidden")
            or first_matching_failure_code(failure_codes, r"forbidden")
        )
    if "conflict" in lowered or "stale" in lowered:
        return first_matching_failure_code(failure_codes, r"(conflict|stale|already|in_flight|version)")
    return ""


def replay_profile(
    row: dict[str, object],
    *,
    operation_ids: list[str],
    failure_code: str,
) -> str:
    lowered = " ".join(
        [
            str(row.get("scenario_or_contract", "")).lower(),
            str(row.get("expected_outcome", "")).lower(),
            str(row.get("semantic_bridge_note", "")).lower(),
        ]
    )
    if failure_code == "tenant_forbidden":
        return "tenant_deny"
    if failure_code and re.search(r"forbidden", failure_code):
        return "forbidden_deny"
    if "uncertainty" in lowered and "conflict" in lowered:
        return "uncertainty_and_conflict"
    if "review report" in lowered and "task outcome" in lowered:
        return "review_binding"
    if "scope" in lowered and "recommendation" in lowered and "task" in lowered:
        return "full_chain"
    if "boundary" in lowered or "carryover" in lowered or "attribution" in lowered:
        return "boundary_visibility"
    return "generic_chain"


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


def render_tenant_deny_body(failure_operation_id: str) -> tuple[list[str], list[str]]:
    return [
        f'const failureOperationId = "{failure_operation_id}";',
    ], [
        "    const error = await captureApiError(",
        "      invokeHttpOperation(runtime, failureOperationId, buildFailurePayload(failureOperationId, failureCode)),",
        "    );",
        "    expect(error.status).toBe(403);",
        "    expect(error.envelope.error_code).toBe(failureCode);",
    ]


def render_forbidden_deny_body(failure_operation_id: str) -> tuple[list[str], list[str]]:
    return [
        f'const failureOperationId = "{failure_operation_id}";',
    ], [
        "    const error = await captureApiError(",
        "      invokeHttpOperation(runtime, failureOperationId, buildFailurePayload(failureOperationId, failureCode)),",
        "    );",
        "    expect(error.status).toBe(403);",
        "    expect(error.envelope.error_code).toBe(failureCode);",
    ]


def render_full_chain_body(operation_ids: list[str], endpoint_rows: list[dict[str, object]]) -> tuple[list[str], list[str]]:
    final_operation_id = operation_ids[-1] if operation_ids else ""
    final_record_key = record_key_for_operation(endpoint_rows, final_operation_id)
    final_id_field = primary_id_field(endpoint_rows, final_operation_id)
    return [
        f"const expectedContextFields = {json.dumps(expected_context_fields(endpoint_rows, operation_ids), ensure_ascii=False)};",
        f'const finalRecordKey = "{final_record_key}";',
        f'const finalIdField = "{final_id_field}";',
    ], [
        "    const context: Record<string, unknown> = {};",
        "    const results: unknown[] = [];",
        "    for (const operationId of operationIds) {",
        "      const payload = applyRuntimeContext(buildOperationPayload(operationId), context);",
        "      const result = await invokeHttpOperation(runtime, operationId, payload);",
        "      results.push(result);",
        "      absorbEnvelopeContext(result, context);",
        "    }",
        "    expect(results).toHaveLength(operationIds.length);",
        "    for (const field of expectedContextFields) {",
        "      expect(String(context[field] ?? '')).not.toHaveLength(0);",
        "    }",
        "    const finalData = extractEnvelopeData<Record<string, unknown>>(results.at(-1));",
        "    expect(String(finalData[finalIdField] ?? '')).not.toHaveLength(0);",
    ]


def render_review_binding_body() -> tuple[list[str], list[str]]:
    return [
        'const detailOperationId = "GetReviewReportDetail";',
        'const decisionOperationId = "RecordReviewDecision";',
    ], [
        "    const context: Record<string, unknown> = {};",
        "    const detail = await invokeHttpOperation(runtime, detailOperationId, applyRuntimeContext(buildOperationPayload(detailOperationId), context));",
        "    absorbEnvelopeContext(detail, context);",
        "    const detailData = extractEnvelopeData<Record<string, unknown>>(detail);",
        "    expect(String(detailData.review_report_id ?? '')).not.toHaveLength(0);",
        "    expect(String(detailData.current_run_id ?? '')).not.toHaveLength(0);",
        "    expect(String(detailData.prior_run_id ?? '')).not.toHaveLength(0);",
        "    const decision = await invokeHttpOperation(",
        "      runtime,",
        "      decisionOperationId,",
        "      applyRuntimeContext(buildOperationPayload(decisionOperationId), context),",
        "    );",
        "    const decisionData = extractEnvelopeData<Record<string, unknown>>(decision);",
        *persistence_roundtrip_assertion_lines("decisionOperationId", "decision"),
        "    expect(decisionData.review_report_id).toBe(detailData.review_report_id);",
        "    expect(decisionData.saved).toBe(true);",
    ]


def render_uncertainty_and_conflict_body(
    row: dict[str, object],
    operation_ids: list[str],
    endpoint_rows: list[dict[str, object]],
    failure_code: str,
) -> tuple[list[str], list[str]]:
    failure_operation_id = choose_failure_operation(operation_ids, endpoint_rows, failure_code)
    review_operation_id = choose_semantic_review_operation(endpoint_rows, operation_ids)
    return [
        f'const reviewOperationId = "{review_operation_id}";',
        f'const failureOperationId = "{failure_operation_id}";',
    ], [
        "    const review = await invokeHttpOperation(runtime, reviewOperationId, buildOperationPayload(reviewOperationId));",
        "    const reviewData = extractEnvelopeData<Record<string, unknown>>(review);",
        *(
            persistence_roundtrip_assertion_lines("reviewOperationId", "review")
            if operation_supports_persistence_roundtrip(review_operation_id, endpoint_rows)
            else []
        ),
        *semantic_assertion_lines(
            row,
            endpoint_rows=endpoint_rows,
            operation_ids=operation_ids,
            preferred_operation_id=review_operation_id,
            data_expr="reviewData",
        ),
        "    expect(JSON.stringify(reviewData).toLowerCase()).toContain('uncertainty');",
        "    const committed = await invokeHttpOperation(runtime, failureOperationId, buildOperationPayload(failureOperationId));",
        "    const committedData = extractEnvelopeData<Record<string, unknown>>(committed);",
        *(
            persistence_roundtrip_assertion_lines("failureOperationId", "committed")
            if operation_supports_persistence_roundtrip(failure_operation_id, endpoint_rows)
            else []
        ),
        "    expect(Object.keys(committedData).length).toBeGreaterThan(0);",
        "    const error = await captureApiError(",
        "      invokeHttpOperation(runtime, failureOperationId, buildFailurePayload(failureOperationId, failureCode)),",
        "    );",
        "    expect(error.envelope.error_code).toBe(failureCode);",
    ]


def render_boundary_visibility_body(operation_ids: list[str], endpoint_rows: list[dict[str, object]]) -> tuple[list[str], list[str]]:
    return render_semantic_chain_body(operation_ids, endpoint_rows)


def render_semantic_chain_body(operation_ids: list[str], endpoint_rows: list[dict[str, object]]) -> tuple[list[str], list[str]]:
    first_operation_id = operation_ids[0] if operation_ids else ""
    final_operation_id = operation_ids[-1] if operation_ids else ""
    final_is_array = response_is_array(endpoint_rows, final_operation_id)
    final_fields = response_data_fields(endpoint_rows, final_operation_id)
    shared_fields = shared_response_business_fields(endpoint_rows, first_operation_id, final_operation_id)
    literal_fields = scalar_business_value_fields(endpoint_rows, final_operation_id)
    context_fields = dedupe_preserve_order([*expected_context_fields(endpoint_rows, operation_ids), *shared_fields])
    const_lines = [
        f"const expectedContextFields = {json.dumps(context_fields, ensure_ascii=False)};",
        f"const finalDataFields = {json.dumps(final_fields, ensure_ascii=False)};",
    ]
    if not shared_fields and not literal_fields:
        const_lines.append('const reviewBoundReason = "business_assertions_not_inferred";')

    lines = [
        "    const context: Record<string, unknown> = {};",
        "    const results: unknown[] = [];",
        "    let persistenceEvidenceCount = 0;",
        "    let requiresPersistenceRoundTripEvidenceObserved = false;",
        "    for (const operationId of operationIds) {",
        "      const result = await invokeHttpOperation(runtime, operationId, applyRuntimeContext(buildOperationPayload(operationId), context));",
        "      results.push(result);",
        "      absorbEnvelopeContext(result, context);",
        "      const persistenceEvidence = await collectPersistenceRoundTripEvidence(runtime, operationId, result);",
        "      if (await requiresPersistenceRoundTripEvidence(runtime, operationId)) {",
        "        requiresPersistenceRoundTripEvidenceObserved = true;",
        "        persistenceEvidenceCount += persistenceEvidence.filter((entry) => entry.mismatchedFieldNames.length === 0).length;",
        "      }",
        "    }",
        "    expect(results).toHaveLength(operationIds.length);",
        "    for (const field of expectedContextFields) {",
        "      expect(String(context[field] ?? '')).not.toHaveLength(0);",
        "    }",
        "    const firstData = extractEnvelopeData<Record<string, unknown>>(results[0]);",
        *(
            [
                "    const finalData = extractEnvelopeData<unknown>(results.at(-1));",
                "    expect(Array.isArray(finalData)).toBe(true);",
            ]
            if final_is_array
            else [
                "    const finalData = extractEnvelopeData<Record<string, unknown>>(results.at(-1));",
                "    expect(Array.isArray(finalData)).toBe(false);",
            ]
        ),
        "    if (requiresPersistenceRoundTripEvidenceObserved) {",
        "      expect(persistenceEvidenceCount).toBeGreaterThan(0);",
        "    }",
    ]
    if final_is_array:
        lines.extend([
            "    const finalRows = finalData as Array<Record<string, unknown>>;",
            "    expect(finalRows.length).toBeGreaterThan(0);",
            "    const finalRecord = finalRows[0];",
        ])
    else:
        lines.append("    const finalRecord = finalData;")
    lines.extend([
        "    for (const field of finalDataFields) {",
        "      expect(finalRecord).toHaveProperty(field);",
        "      expect(String(finalRecord[field] ?? '')).not.toHaveLength(0);",
        "    }",
    ])
    for field in shared_fields:
        access = ts_property_access(field)
        target_expr = "finalRecord" if final_is_array else "finalData"
        lines.append(f"    expect({target_expr}{access}).toBe(firstData{access});")
    for field, value in literal_fields.items():
        access = ts_property_access(field)
        target_expr = "finalRecord" if final_is_array else "finalData"
        lines.append(f"    expect({target_expr}{access}).toBe({literal_ts_value(value)});")
    if not shared_fields and not literal_fields:
        lines.append("    expect(reviewBoundReason).toBe('business_assertions_not_inferred');")
    return const_lines, lines


def render_generic_chain_body(operation_ids: list[str], endpoint_rows: list[dict[str, object]]) -> tuple[list[str], list[str]]:
    return render_semantic_chain_body(operation_ids, endpoint_rows)


def render_body(
    row: dict[str, object],
    *,
    endpoint_rows: list[dict[str, object]],
    operation_ids: list[str],
    failure_code: str,
) -> tuple[list[str], list[str]]:
    profile = replay_profile(row, operation_ids=operation_ids, failure_code=failure_code)
    if profile == "tenant_deny":
        return render_tenant_deny_body(choose_failure_operation(operation_ids, endpoint_rows, failure_code))
    if profile == "forbidden_deny":
        return render_forbidden_deny_body(choose_failure_operation(operation_ids, endpoint_rows, failure_code))
    if profile == "full_chain":
        return render_full_chain_body(operation_ids, endpoint_rows)
    if profile == "review_binding":
        return render_review_binding_body()
    if profile == "uncertainty_and_conflict":
        return render_uncertainty_and_conflict_body(row, operation_ids, endpoint_rows, failure_code)
    if profile == "boundary_visibility":
        return render_boundary_visibility_body(operation_ids, endpoint_rows)
    return render_generic_chain_body(operation_ids, endpoint_rows)


def replay_idempotency_stress_lines() -> list[str]:
    return [
        "    const secondReplayContext: Record<string, unknown> = {};",
        "    const secondReplayResults: unknown[] = [];",
        "    let secondReplayStoppedByDuplicateGuard = false;",
        "    for (const operationId of operationIds) {",
        "      if (secondReplayStoppedByDuplicateGuard) {",
        "        break;",
        "      }",
        "      const secondPayload = applyRuntimeContext(buildOperationPayload(operationId), secondReplayContext);",
        "      try {",
        "        const secondResult = await invokeHttpOperation(runtime, operationId, secondPayload);",
        "        secondReplayResults.push(secondResult);",
        "        absorbEnvelopeContext(secondResult, secondReplayContext);",
        "      } catch (error) {",
        "        const status = (error as { status?: number }).status;",
        "        const envelope = ((error as { envelope?: Record<string, unknown> }).envelope ?? {}) as Record<string, unknown>;",
        "        expect(status).toBe(409);",
        "        expect(String(envelope.error_code ?? '')).toMatch(/conflict|duplicate|idempot/i);",
        "        secondReplayResults.push(envelope);",
        "        secondReplayStoppedByDuplicateGuard = true;",
        "      }",
        "    }",
        "    expect(secondReplayResults.length).toBeGreaterThan(0);",
        "    expect(secondReplayResults.length).toBeLessThanOrEqual(operationIds.length);",
    ]


def render_replay_test(
    row: dict[str, object],
    *,
    endpoint_rows: list[dict[str, object]] | None = None,
    scenario_operation_map: dict[str, list[str]] | None = None,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> str:
    replay_id = str(row["replay_id"])
    label = str(row["scenario_or_contract"])
    upstream = json.dumps(row.get("upstream_trace_ids", []), ensure_ascii=False)
    linked = json.dumps(row.get("linked_rbi_or_wp", []), ensure_ascii=False)
    endpoint_rows = endpoint_rows or []
    scenario_operation_map = scenario_operation_map or {}
    if "_resolved_operation_ids" in row:
        resolved_operation_ids = row.get("_resolved_operation_ids", [])
        if isinstance(resolved_operation_ids, list):
            operation_ids = [str(item).strip() for item in resolved_operation_ids if str(item).strip()]
        else:
            operation_ids = []
    else:
        operation_ids = []
    if not operation_ids and "_resolved_operation_ids" not in row:
        operation_ids = infer_operation_ids(
            row,
            endpoint_rows=endpoint_rows,
            scenario_operation_map=scenario_operation_map,
        )
    failure_code = preferred_failure_code(row, endpoint_rows=endpoint_rows, operation_ids=operation_ids)
    expected_outcome = str(row.get("expected_outcome", "")).strip()
    if not operation_ids:
        unresolved_operation_ids = row.get("_unresolved_operation_ids", [])
        if not isinstance(unresolved_operation_ids, list):
            unresolved_operation_ids = []
        unresolved_suffix = f": {', '.join(str(item) for item in unresolved_operation_ids if str(item).strip())}"
        return "\n".join(
            [
                'import { describe, it } from "vitest";',
                "",
                f'describe("Replay: {replay_id} {label}", () => {{',
                '  it.skip("remains review-bound until the compiled OpenAPI contract exposes executable operations'
                f'{unresolved_suffix}", () => {{}});',
                "});",
                "",
            ]
        )
    behavior_mapping_lines = []
    for operation_id in operation_ids:
        model = (behavior_card_models or {}).get(operation_id)
        if model:
            behavior_mapping_lines.extend(render_behavior_step_test_mapping(model)["replay"].splitlines())
    const_lines, body_lines = render_body(
        row,
        endpoint_rows=endpoint_rows,
        operation_ids=operation_ids,
        failure_code=failure_code,
    )
    include_failure_code = any("failureCode" in line for line in const_lines + body_lines)
    generated_body_text = "\n".join([*behavior_mapping_lines, *const_lines, *body_lines])
    return "\n".join(
        [
            'import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";',
            *render_harness_import(generated_body_text),
            "",
            "let runtime: BackendRuntime;",
            "",
            f'const upstreamTraceIds = {upstream};',
            f'const linkedRbiOrWp = {linked};',
            f"const operationIds = {json.dumps(operation_ids, ensure_ascii=False)};",
            f'const expectedOutcome = {json.dumps(expected_outcome, ensure_ascii=False)};',
            *([f'const failureCode = "{failure_code}";'] if include_failure_code else []),
            *behavior_mapping_lines,
            *const_lines,
            "",
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
            "  await runtime.restoreScenario();",
            "});",
            "",
            f'describe("Replay: {replay_id} {label}", () => {{',
            f'  it("replays the preserved semantics for {replay_id}", async () => {{',
            "    expect(upstreamTraceIds.length).toBeGreaterThan(0);",
            "    expect(linkedRbiOrWp.length).toBeGreaterThan(0);",
            "    expect(expectedOutcome.length).toBeGreaterThan(0);",
            "    expect(operationIds.length).toBeGreaterThan(0);",
            *body_lines,
            *replay_idempotency_stress_lines(),
            "  });",
            "});",
            "",
        ]
    )


def scaffold_replay_tests(
    stage_04_text: str,
    output_dir: Path,
    *,
    esp_text: str = "",
    stage_03_text: str = "",
    openapi_spec: dict[str, object] | None = None,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    rows = parse_replay_rows(stage_04_text)
    source_endpoint_rows = parse_api_endpoint_rows(esp_text) if esp_text.strip() else []
    runtime_endpoint_rows = endpoint_rows_from_openapi_spec(openapi_spec or {}) if openapi_spec else []
    inference_endpoint_rows = source_endpoint_rows or runtime_endpoint_rows
    render_endpoint_rows = runtime_endpoint_rows or source_endpoint_rows
    scenario_operation_map: dict[str, list[str]] = {}
    if stage_03_text.strip():
        scenario_rows = parse_scenario_rows(stage_03_text)
        inference_endpoint_names = {str(item.get("endpoint_name", "")).strip() for item in inference_endpoint_rows}
        for scenario_row in scenario_rows:
            raw = str(scenario_row.get("contracts / endpoints", "")).strip()
            operations = []
            if raw and "any tenant-scoped get" not in raw.lower():
                operations = [part.strip() for part in raw.split(",") if part.strip() in inference_endpoint_names]
            if not operations:
                operations = infer_operation_ids(
                    {
                        "replay_id": str(scenario_row.get("scenario", "")),
                        "scenario_or_contract": raw,
                        "semantic_bridge_note": str(scenario_row.get("failure_note", "")),
                        "source_artifacts": str(scenario_row.get("scenario", "")),
                        "expected_outcome": str(scenario_row.get("acceptance_criteria", "")),
                    },
                    endpoint_rows=inference_endpoint_rows,
                    scenario_operation_map={},
                )
            if runtime_endpoint_rows and source_endpoint_rows and operations:
                operations = remap_operation_ids_to_runtime_contract(
                    operations,
                    source_endpoint_rows=source_endpoint_rows,
                    runtime_endpoint_rows=runtime_endpoint_rows,
                )
            elif runtime_endpoint_rows and not operations:
                operations = infer_operation_ids(
                    {
                        "replay_id": str(scenario_row.get("scenario", "")),
                        "scenario_or_contract": str(scenario_row.get("contracts / endpoints", "")),
                        "semantic_bridge_note": str(scenario_row.get("failure_note", "")),
                        "source_artifacts": str(scenario_row.get("scenario", "")),
                        "expected_outcome": str(scenario_row.get("acceptance_criteria", "")),
                    },
                    endpoint_rows=runtime_endpoint_rows,
                    scenario_operation_map={},
                )
            scenario_id = str(scenario_row.get("scenario", "")).split(" ", 1)[0].upper()
            if scenario_id:
                scenario_operation_map[scenario_id] = operations
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for row in rows:
        operation_ids = infer_operation_ids(
            row,
            endpoint_rows=inference_endpoint_rows,
            scenario_operation_map=scenario_operation_map,
        )
        unresolved_operation_ids: list[str] = []
        if runtime_endpoint_rows and source_endpoint_rows and operation_ids:
            mapped_operation_ids = remap_operation_ids_to_runtime_contract(
                operation_ids,
                source_endpoint_rows=source_endpoint_rows,
                runtime_endpoint_rows=runtime_endpoint_rows,
            )
            if mapped_operation_ids:
                operation_ids = mapped_operation_ids
            else:
                unresolved_operation_ids = operation_ids
                operation_ids = []
        if runtime_endpoint_rows and not operation_ids and not unresolved_operation_ids:
            operation_ids = infer_operation_ids(
                row,
                endpoint_rows=runtime_endpoint_rows,
                scenario_operation_map=scenario_operation_map,
            )
        target = output_dir / replay_test_filename(str(row["replay_id"]), str(row["scenario_or_contract"]))
        target.write_text(
            render_replay_test(
                {
                    **row,
                    "_resolved_operation_ids": operation_ids,
                    "_unresolved_operation_ids": unresolved_operation_ids,
                },
                endpoint_rows=render_endpoint_rows,
                scenario_operation_map=scenario_operation_map,
                behavior_card_models=behavior_card_models,
            ),
            encoding="utf-8",
        )
        files.append(str(target))
    return {"output_dir": str(output_dir), "files_created": files, "count": len(files)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate executable replay tests from Stage-04")
    parser.add_argument("--stage-04", required=True, help="Path to Stage-04 markdown")
    parser.add_argument("--esp", help="Optional ESP path for endpoint inference")
    parser.add_argument("--stage-03", help="Optional Stage-03 path for scenario linkage")
    parser.add_argument("--openapi", help="Optional final OpenAPI path for runtime operation remapping")
    parser.add_argument("--output-dir", required=True, help="Target directory for *.replay.test.ts files")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    text = Path(args.stage_04).resolve().read_text(encoding="utf-8")
    esp_text = Path(args.esp).resolve().read_text(encoding="utf-8") if args.esp else ""
    stage_03_text = Path(args.stage_03).resolve().read_text(encoding="utf-8") if args.stage_03 else ""
    openapi_spec = json.loads(Path(args.openapi).resolve().read_text(encoding="utf-8")) if args.openapi else None
    summary = scaffold_replay_tests(
        text,
        Path(args.output_dir).resolve(),
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        openapi_spec=openapi_spec,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
