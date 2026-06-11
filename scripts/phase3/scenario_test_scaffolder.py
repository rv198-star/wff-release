#!/usr/bin/env python3
"""
Generate executable scenario-test scaffolds from Stage-03 scenario coverage.
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
from phase3.test_scaffolder_common import (
    WRITE_HTTP_METHODS,
    dedupe_preserve_order,
    endpoint_index,
    failure_condition_signal_lines,
    failure_has_runtime_signal,
    normalize_field_token,
    operation_supports_persistence_roundtrip,
    persistence_roundtrip_assertion_lines,
    remap_operation_ids_to_runtime_contract,
    render_harness_import,
    resolve_response_field,
)
try:
    from phase3.behavior_contract import (
        behavior_evidence_key_map,
        behavior_evidence_key_map,
        behavior_evidence_keys,
        typescript_behavior_card_payload_helper_lines,
        typescript_behavior_payload_expr,
    )
except ModuleNotFoundError:
    from phase3.behavior_contract import (
        behavior_evidence_key_map,
        behavior_evidence_key_map,
        behavior_evidence_keys,
        typescript_behavior_card_payload_helper_lines,
        typescript_behavior_payload_expr,
    )
from phase3.contract_tools import (
    camel_and_word_tokens,
    endpoint_rows_from_openapi_spec,
    parse_api_endpoint_rows,
    parse_scenario_rows,
    scenario_identifier,
    scenario_test_filename,
)

def explicit_operation_ids(raw: str, endpoint_names: set[str]) -> list[str]:
    cleaned = raw.strip()
    if not cleaned or "any tenant-scoped get" in cleaned.lower():
        return []
    matches: list[str] = []
    for part in cleaned.split(","):
        candidate = part.strip()
        if candidate in endpoint_names:
            matches.append(candidate)
    return matches


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
    ordered: list[str] = []
    seen: set[str] = set()
    for _, _, endpoint_name in filtered_hits:
        if endpoint_name in seen:
            continue
        seen.add(endpoint_name)
        ordered.append(endpoint_name)
    return ordered


def infer_operation_ids(row: dict[str, object], endpoint_rows: list[dict[str, object]]) -> list[str]:
    if not endpoint_rows:
        return []
    endpoint_names = {str(item["endpoint_name"]).strip() for item in endpoint_rows}
    direct = explicit_operation_ids(str(row.get("contracts / endpoints", "")), endpoint_names)
    if direct:
        return direct

    query = " ".join(
        str(row.get(key, ""))
        for key in (
            "scenario",
            "actors",
            "entities",
            "modules",
            "contracts / endpoints",
            "failure_note",
            "acceptance_criteria",
            "measurement_hook",
        )
    )
    explicit = explicit_operation_mentions(query, endpoint_names)
    if explicit:
        return explicit
    query_tokens = camel_and_word_tokens(query)
    scored: list[tuple[int, str]] = []
    for endpoint in endpoint_rows:
        endpoint_name = str(endpoint["endpoint_name"]).strip()
        haystack = " ".join(
            [
                endpoint_name,
                str(endpoint.get("path", "")),
                str(endpoint.get("purpose", "")),
                str(endpoint.get("idempotency_rule", "")),
                str(endpoint.get("pagination_rule", "")),
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
    return [name for _, name in scored[:3]]

def collect_failure_codes(endpoint_rows: list[dict[str, object]], operation_ids: list[str]) -> list[str]:
    by_name = endpoint_index(endpoint_rows)
    failure_codes: list[str] = []
    for operation_id in operation_ids:
        row = by_name.get(operation_id, {})
        for failure in row.get("failure_codes", []):
            code = str(failure.get("error_code", "")).strip()
            if code:
                failure_codes.append(code)
    return list(dict.fromkeys(failure_codes))


def failure_has_runtime_signal_for_endpoint(
    row: dict[str, object],
    failure: dict[str, object],
    *,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> bool:
    code = str(failure.get("error_code", "")).strip()
    if not code:
        return False
    operation_id = str(row.get("endpoint_name", "")).strip()
    return failure_has_runtime_signal(
        code,
        status=str(failure.get("status", "")).strip(),
        method=str(row.get("method", "")).strip(),
        path=str(row.get("path", "")).strip(),
        operation_id=operation_id,
        behavior_card_model=(behavior_card_models or {}).get(operation_id),
    )


def collect_runtime_failure_codes(
    endpoint_rows: list[dict[str, object]],
    operation_ids: list[str],
    *,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> list[str]:
    by_name = endpoint_index(endpoint_rows)
    failure_codes: list[str] = []
    for operation_id in operation_ids:
        row = by_name.get(operation_id, {})
        for failure in row.get("failure_codes", []):
            if not isinstance(failure, dict) or not failure_has_runtime_signal_for_endpoint(
                row,
                failure,
                behavior_card_models=behavior_card_models,
            ):
                continue
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


def preferred_failure_code(
    row: dict[str, object],
    endpoint_rows: list[dict[str, object]],
    operation_ids: list[str],
    *,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> str:
    lowered = " ".join(
        [
            str(row.get("scenario", "")).lower(),
            str(row.get("failure_note", "")).lower(),
            str(row.get("acceptance_criteria", "")).lower(),
        ]
    )
    scenario_type = str(row.get("scenario_type", "")).strip().lower()
    failure_codes = collect_runtime_failure_codes(endpoint_rows, operation_ids, behavior_card_models=behavior_card_models)

    deny_intent = any(term in lowered for term in ("cross-tenant", "tenant deny", "tenant_forbidden", "forbidden", "deny"))
    if deny_intent:
        return (
            first_matching_failure_code(failure_codes, r"tenant_forbidden")
            or first_matching_failure_code(failure_codes, r"forbidden")
        )
    if "validation" in lowered or "missing" in lowered:
        return (
            first_matching_failure_code(failure_codes, r"(validation|invalid|required|missing)")
            or first_matching_failure_code(failure_codes, r"bad_request")
        )
    if "concurrent" in lowered or "stale" in lowered or "conflict" in lowered:
        return first_matching_failure_code(failure_codes, r"(conflict|stale|already|in_flight|version)")
    if scenario_type == "failure_path":
        return failure_codes[0] if failure_codes else ""
    return ""


def scenario_failure_variants(
    endpoint_rows: list[dict[str, object]],
    operation_ids: list[str],
    *,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> list[dict[str, str]]:
    variant_specs = [
        ("invalid request", ("400",), re.compile(r"(invalid|validation|required|missing)")),
        ("permission", ("403",), re.compile(r"(forbidden|permission|tenant)")),
        ("conflict", ("409",), re.compile(r"(conflict|stale|duplicate|version)")),
        ("dependency", ("5",), re.compile(r"(db|database|dependency|unavailable|timeout)")),
    ]
    variants: list[dict[str, str]] = []
    by_name = endpoint_index(endpoint_rows)
    for label, status_prefixes, code_pattern in variant_specs:
        for operation_id in operation_ids:
            row = by_name.get(operation_id, {})
            for failure in row.get("failure_codes", []):
                status = str(failure.get("status", "")).strip()
                code = str(failure.get("error_code", "")).strip()
                if not code:
                    continue
                if not failure_has_runtime_signal_for_endpoint(row, failure, behavior_card_models=behavior_card_models):
                    continue
                if status.startswith(status_prefixes) or code_pattern.search(code):
                    variants.append(
                        {
                            "label": label,
                            "operation_id": operation_id,
                            "status": status or status_prefixes[0],
                            "error_code": code,
                        }
                    )
                    break
            if variants and variants[-1].get("label") == label:
                break
    return variants


def render_supplemental_failure_variant_tests(variants: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    seen_labels: set[str] = set()
    for variant in variants:
        label = str(variant.get("label", "")).strip()
        operation_id = str(variant.get("operation_id", "")).strip()
        status = str(variant.get("status", "")).strip() or "400"
        error_code = str(variant.get("error_code", "")).strip()
        if not label or not operation_id or not error_code or label in seen_labels:
            continue
        seen_labels.add(label)
        lines.extend(
            [
                "",
                f'  it("{label} variant rejects with documented error", async () => {{',
                f'    const variantOperationId = "{operation_id}";',
                "    const beforeRows = await collectScenarioState(runtime);",
                f'    const payload = buildFailurePayload(variantOperationId, "{error_code}");',
                *failure_condition_signal_lines(error_code),
                "    const error = await captureApiError(",
                "      invokeHttpOperation(runtime, variantOperationId, payload),",
                "    );",
                "    const afterRows = await collectScenarioState(runtime);",
                "    expect(afterRows).toEqual(beforeRows);",
                f"    expect(error.status).toBe({status});",
                f'    expect(error.envelope.error_code).toBe("{error_code}");',
                "  });",
            ]
        )
    return lines

def scenario_state_collector_lines() -> list[str]:
    return [
        "async function collectScenarioState(runtime: BackendRuntime): Promise<Record<string, number>> {",
        "  const tables = await runtime.query<{ tablename: string }>(",
        "    `SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename`,",
        "  );",
        "  const entries: Array<[string, number]> = [];",
        "  for (const row of tables) {",
        "    const countRows = await runtime.query<{ count: number }>(`SELECT COUNT(*)::int AS count FROM \"${row.tablename}\"`);",
        "    entries.push([row.tablename, Number(countRows[0]?.count ?? 0)]);",
        "  }",
        "  return Object.fromEntries(entries);",
        "}",
        "",
    ]


def snake_case(value: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower()


def strip_id_suffix(value: str) -> str:
    return value[:-3] if value.endswith("_id") else value


def token_parts(value: str) -> list[str]:
    return [part for part in value.split("_") if part]


def score_id_field_candidate(param_key: str, field: str) -> int:
    if not field.endswith("_id"):
        return -1
    if field == param_key:
        return 100
    param_core = strip_id_suffix(param_key)
    field_core = strip_id_suffix(field)
    if field_core == param_core:
        return 90
    if field_core.endswith(param_core) or param_core.endswith(field_core):
        return 80
    overlap = len(set(token_parts(param_core)) & set(token_parts(field_core)))
    return overlap * 10 if overlap else -1


def response_data_for_operation(endpoint_rows: list[dict[str, object]], operation_id: str) -> object:
    row = endpoint_index(endpoint_rows).get(operation_id, {})
    response = row.get("response_body_example", {})
    if isinstance(response, dict):
        return response.get("data", {})
    return {}


def response_id_fields(endpoint_rows: list[dict[str, object]], operation_id: str) -> list[str]:
    def is_id_field(key: object) -> bool:
        value = str(key)
        return value.endswith("_id") or value.endswith("Id")

    data = response_data_for_operation(endpoint_rows, operation_id)
    if isinstance(data, dict):
        return [key for key in data if is_id_field(key)]
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return [key for key in data[0] if is_id_field(key)]
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


def endpoint_row_for_operation(endpoint_rows: list[dict[str, object]], operation_id: str) -> dict[str, object]:
    normalized = str(operation_id or "").strip()
    return next((row for row in endpoint_rows if str(row.get("endpoint_name", "")).strip() == normalized), {})


def operation_is_list_like(endpoint_rows: list[dict[str, object]], operation_id: str) -> bool:
    row = endpoint_row_for_operation(endpoint_rows, operation_id)
    endpoint_name = str(row.get("endpoint_name", operation_id) or "").strip().lower()
    pagination_rule = str(row.get("pagination_rule", "") or "").strip().lower()
    if endpoint_name.startswith("list"):
        return True
    return pagination_rule not in {"", "none", "not_applicable", "n/a"}


def shared_response_business_fields(endpoint_rows: list[dict[str, object]], first_operation_id: str, final_operation_id: str) -> list[str]:
    if operation_is_list_like(endpoint_rows, first_operation_id):
        return []
    if operation_is_list_like(endpoint_rows, final_operation_id):
        return []
    first_fields = set(response_data_example_record(endpoint_rows, first_operation_id).keys())
    final_fields = set(response_data_example_record(endpoint_rows, final_operation_id).keys())
    shared = [field for field in response_data_fields(endpoint_rows, final_operation_id) if field in first_fields and (field.endswith("Id") or field.endswith("_id"))]
    return shared

def primary_id_field(endpoint_rows: list[dict[str, object]], operation_id: str) -> str:
    by_name = endpoint_index(endpoint_rows)
    row = by_name.get(operation_id, {})
    path = str(row.get("path", ""))
    path_params = re.findall(r"{([^}]+)}", path)
    id_fields = response_id_fields(endpoint_rows, operation_id)
    if not id_fields:
        return ""
    best_field = id_fields[0]
    best_score = -1
    for param in path_params:
        param_key = snake_case(param)
        for field in id_fields:
            score = score_id_field_candidate(param_key, field)
            if score > best_score:
                best_field = field
                best_score = score
    return best_field


def primary_record_key(endpoint_rows: list[dict[str, object]], operation_id: str) -> str:
    return primary_id_field(endpoint_rows, operation_id)


def operation_supports_failure(
    endpoint_rows: list[dict[str, object]],
    operation_id: str,
    failure_code: str,
    *,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> bool:
    if not failure_code:
        return False
    row = endpoint_index(endpoint_rows).get(operation_id, {})
    return any(
        str(item.get("error_code", "")).strip() == failure_code
        and failure_has_runtime_signal_for_endpoint(row, item, behavior_card_models=behavior_card_models)
        for item in row.get("failure_codes", [])
        if isinstance(item, dict)
    )


def choose_failure_operation(
    operation_ids: list[str],
    endpoint_rows: list[dict[str, object]],
    failure_code: str,
    *,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> str:
    for operation_id in operation_ids:
        if operation_supports_failure(endpoint_rows, operation_id, failure_code, behavior_card_models=behavior_card_models):
            return operation_id
    return operation_ids[0] if operation_ids else ""


def expected_context_fields(endpoint_rows: list[dict[str, object]], operation_ids: list[str]) -> list[str]:
    fields: list[str] = []
    for operation_id in operation_ids:
        fields.extend(response_id_fields(endpoint_rows, operation_id))
    return sorted(dict.fromkeys(field for field in fields if field))


def operation_runtime_context_inputs(endpoint_rows: list[dict[str, object]], operation_id: str) -> set[str]:
    row = endpoint_row_for_operation(endpoint_rows, operation_id)
    request = row.get("request_body_example", {}) if isinstance(row, dict) else {}
    fields: set[str] = set()
    if isinstance(request, dict):
        fields.update(str(key) for key in request.keys() if str(key).strip())
    path = str(row.get("path", "") if isinstance(row, dict) else "")
    fields.update(re.findall(r"{([^}]+)}", path))
    return {normalize_field_token(field) for field in fields if normalize_field_token(field)}


def operation_context_outputs(endpoint_rows: list[dict[str, object]], operation_id: str) -> set[str]:
    fields = set(response_data_fields(endpoint_rows, operation_id))
    row = endpoint_row_for_operation(endpoint_rows, operation_id)
    request = row.get("request_body_example", {}) if isinstance(row, dict) else {}
    if isinstance(request, dict):
        for key in ("tenantId", "tenant_id", "traceId", "trace_id"):
            if key in request:
                fields.add(key)
    return {normalize_field_token(field) for field in fields if normalize_field_token(field)}


def operation_can_follow_context(
    endpoint_rows: list[dict[str, object]],
    previous_operation_id: str,
    next_operation_id: str,
) -> bool:
    if not previous_operation_id or not next_operation_id:
        return False
    if operation_is_list_like(endpoint_rows, next_operation_id):
        return True
    next_inputs = {
        field
        for field in operation_runtime_context_inputs(endpoint_rows, next_operation_id)
        if field not in {"tenantid", "tenant_id", "traceid", "trace_id", "cursor", "pagesize", "page_size"}
    }
    if not next_inputs:
        return True
    previous_outputs = operation_context_outputs(endpoint_rows, previous_operation_id)
    return bool(next_inputs & previous_outputs)


def filter_context_compatible_operation_chain(
    row: dict[str, object],
    endpoint_rows: list[dict[str, object]],
    operation_ids: list[str],
) -> list[str]:
    if len(operation_ids) < 2:
        return operation_ids
    filtered = [operation_ids[0]]
    for operation_id in operation_ids[1:]:
        if operation_can_follow_context(endpoint_rows, filtered[-1], operation_id):
            filtered.append(operation_id)
    if len(filtered) == 1 and str(row.get("contracts / endpoints", "")).strip():
        return filtered
    return filtered if filtered else operation_ids[:1]


def any_operation_has_field(endpoint_rows: list[dict[str, object]], operation_ids: list[str], field_name: str) -> bool:
    return any(field_name in response_data_fields(endpoint_rows, operation_id) for operation_id in operation_ids)

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
            str(row.get("scenario", "")).lower(),
            str(row.get("acceptance_criteria", "")).lower(),
            str(row.get("measurement_hook", "")).lower(),
            str(row.get("failure_note", "")).lower(),
            str(row.get("then", "")).lower(),
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


def scenario_profile(
    row: dict[str, object],
    *,
    operation_ids: list[str],
    endpoint_rows: list[dict[str, object]],
    failure_code: str,
) -> str:
    lowered = " ".join(
        [
            str(row.get("scenario", "")).lower(),
            str(row.get("acceptance_criteria", "")).lower(),
            str(row.get("measurement_hook", "")).lower(),
            str(row.get("failure_note", "")).lower(),
        ]
    )
    scenario_type = str(row.get("scenario_type", "")).strip().lower()
    if failure_code == "tenant_forbidden":
        return "tenant_deny"
    if failure_code and re.search(r"forbidden", failure_code):
        return "forbidden_deny"
    if "uncertainty" in lowered and resolve_response_field(endpoint_rows, operation_ids, ["uncertainty_level", "uncertaintyLevel"]):
        return "uncertainty_detail"
    if scenario_type == "failure_path" and failure_code and re.search(r"(validation|invalid|required|missing)", failure_code):
        return "validation_failure"
    if scenario_type == "concurrent_conflict" or (failure_code and re.search(r"(stale|conflict|competing|concurrent)", lowered)):
        return "concurrent_conflict"
    if "row_version" in lowered or "updateoptimizationtask" in lowered:
        return "versioned_update"
    if {"GetReviewReportDetail", "RecordReviewDecision"}.issubset(set(operation_ids)):
        return "review_binding"
    if "export" in lowered or "semantic completeness" in lowered or "ExportRecommendationToTask" in operation_ids:
        return "export_semantics"
    if "launchobservationrun" in " ".join(operation_ids).lower() and len(operation_ids) >= 2:
        return "operation_chain"
    if len(operation_ids) >= 2:
        return "read_bundle"
    return "generic_success"

def render_validation_failure_body(failure_operation_id: str, record_key: str) -> tuple[list[str], list[str]]:
    const_lines = [f'const failureOperationId = "{failure_operation_id}";']
    lines = []
    lines.extend(
        [
            "    const beforeRows = await collectScenarioState(runtime);",
            "    const payload = buildFailurePayload(failureOperationId, failureCode);",
            "    const error = await captureApiError(",
            "      invokeHttpOperation(runtime, failureOperationId, buildBehaviorCardPayload(failureOperationId, payload, behaviorEvidenceKeysByOperation)),",
            "    );",
            "    const afterRows = await collectScenarioState(runtime);",
            "    expect(afterRows).toEqual(beforeRows);",
            "    expect(error.status).toBe(400);",
            "    expect(error.envelope.error_code).toBe(failureCode);",
        ]
    )
    return const_lines, lines


def render_tenant_deny_body(failure_operation_id: str) -> tuple[list[str], list[str]]:
    return [
        f'const failureOperationId = "{failure_operation_id}";',
    ], [
        "    const beforeRows = await collectScenarioState(runtime);",
        "    const payload = buildFailurePayload(failureOperationId, failureCode);",
        *failure_condition_signal_lines("tenant_forbidden"),
        "    const error = await captureApiError(",
        "      invokeHttpOperation(runtime, failureOperationId, buildBehaviorCardPayload(failureOperationId, payload, behaviorEvidenceKeysByOperation)),",
        "    );",
        "    const afterRows = await collectScenarioState(runtime);",
        "    expect(afterRows).toEqual(beforeRows);",
        "    expect(error.status).toBe(403);",
        '    expect(error.envelope.error_code).toBe("tenant_forbidden");',
    ]


def render_forbidden_deny_body(failure_operation_id: str) -> tuple[list[str], list[str]]:
    return [
        f'const failureOperationId = "{failure_operation_id}";',
    ], [
        "    const beforeRows = await collectScenarioState(runtime);",
        "    const payload = buildFailurePayload(failureOperationId, failureCode);",
        *failure_condition_signal_lines("forbidden"),
        "    const error = await captureApiError(",
        "      invokeHttpOperation(runtime, failureOperationId, buildBehaviorCardPayload(failureOperationId, payload, behaviorEvidenceKeysByOperation)),",
        "    );",
        "    const afterRows = await collectScenarioState(runtime);",
        "    expect(afterRows).toEqual(beforeRows);",
        "    expect(error.status).toBe(403);",
        "    expect(error.envelope.error_code).toBe(failureCode);",
    ]


def render_uncertainty_body(
    row: dict[str, object],
    *,
    primary_operation_id: str,
    operation_ids: list[str],
    endpoint_rows: list[dict[str, object]],
    record_key: str,
    id_field: str,
) -> tuple[list[str], list[str]]:
    const_lines = [f'const primaryOperationId = "{primary_operation_id}";']
    lines = [
        "    const context: Record<string, unknown> = {};",
        "    const payload = applyRuntimeContext(buildBehaviorCardPayload(primaryOperationId, buildOperationPayload(primaryOperationId), behaviorEvidenceKeysByOperation), context);",
        "    const result = await invokeHttpOperation(runtime, primaryOperationId, payload);",
        "    absorbEnvelopeContext(result, context);",
        "    const data = extractEnvelopeData<Record<string, unknown>>(result);",
        *(
            persistence_roundtrip_assertion_lines("primaryOperationId", "result")
            if operation_supports_persistence_roundtrip(primary_operation_id, endpoint_rows)
            else []
        ),
        *semantic_assertion_lines(
            row,
            endpoint_rows=endpoint_rows,
            operation_ids=operation_ids,
            preferred_operation_id=primary_operation_id,
            data_expr="data",
        ),
        "    expect(JSON.stringify(data).toLowerCase()).toContain('uncertainty');",
    ]
    return const_lines, lines


def render_versioned_update_body(primary_operation_id: str, record_key: str, id_field: str) -> tuple[list[str], list[str]]:
    return [
        f'const primaryOperationId = "{primary_operation_id}";',
    ], [
        "    const context: Record<string, unknown> = {};",
        "    const payload = applyRuntimeContext(buildBehaviorCardPayload(primaryOperationId, buildOperationPayload(primaryOperationId), behaviorEvidenceKeysByOperation), context);",
        "    const expectedBeforeVersion = Number(payload.row_version ?? 0);",
        "    const result = await invokeHttpOperation(runtime, primaryOperationId, payload);",
        "    absorbEnvelopeContext(result, context);",
        "    const data = extractEnvelopeData<Record<string, unknown>>(result);",
        *persistence_roundtrip_assertion_lines("primaryOperationId", "result"),
        '    expect(String(data.state)).toBe("executed");',
        "    expect(Number(data.row_version)).toBe(expectedBeforeVersion + 1);",
    ]


def render_concurrent_conflict_body(
    primary_operation_id: str,
    failure_operation_id: str,
    record_key: str,
    id_field: str,
    response_fields: list[str],
) -> tuple[list[str], list[str]]:
    const_lines = [
        f'const primaryOperationId = "{primary_operation_id}";',
        f'const failureOperationId = "{failure_operation_id}";',
    ]
    lines = [
        "    const context: Record<string, unknown> = {};",
        "    const successPayload = applyRuntimeContext(buildBehaviorCardPayload(primaryOperationId, buildOperationPayload(primaryOperationId), behaviorEvidenceKeysByOperation), context);",
        "    const committed = await invokeHttpOperation(runtime, primaryOperationId, successPayload);",
        "    absorbEnvelopeContext(committed, context);",
        "    const committedData = extractEnvelopeData<Record<string, unknown>>(committed);",
        *persistence_roundtrip_assertion_lines("primaryOperationId", "committed"),
    ]
    if "row_version" in response_fields:
        lines.append("    expect(Number(committedData.row_version)).toBe(Number(successPayload.row_version ?? 0) + 1);")
    else:
        lines.append("    expect(Object.keys(committedData).length).toBeGreaterThan(0);")
    lines.extend(
        [
            "    const beforeRows = await collectScenarioState(runtime);",
            "    const payload = buildFailurePayload(failureOperationId, failureCode);",
            *failure_condition_signal_lines("version_conflict"),
            "    const error = await captureApiError(",
            "      invokeHttpOperation(runtime, failureOperationId, buildBehaviorCardPayload(failureOperationId, payload, behaviorEvidenceKeysByOperation)),",
            "    );",
            "    const afterRows = await collectScenarioState(runtime);",
            "    expect(afterRows).toEqual(beforeRows);",
            "    expect(error.envelope.error_code).toBe(failureCode);",
        ]
    )
    return const_lines, lines


def render_review_binding_body(detail_operation_id: str, decision_operation_id: str) -> tuple[list[str], list[str]]:
    return [
        f'const detailOperationId = "{detail_operation_id}";',
        f'const decisionOperationId = "{decision_operation_id}";',
    ], [
        "    const context: Record<string, unknown> = {};",
        "    const detail = await invokeHttpOperation(runtime, detailOperationId, applyRuntimeContext(buildBehaviorCardPayload(detailOperationId, buildOperationPayload(detailOperationId), behaviorEvidenceKeysByOperation), context));",
        "    absorbEnvelopeContext(detail, context);",
        "    const detailData = extractEnvelopeData<Record<string, unknown>>(detail);",
        "    expect(String(detailData.review_report_id ?? '')).not.toHaveLength(0);",
        "    expect(String(detailData.current_run_id ?? '')).not.toHaveLength(0);",
        "    expect(String(detailData.prior_run_id ?? '')).not.toHaveLength(0);",
        "    const decision = await invokeHttpOperation(",
        "      runtime,",
        "      decisionOperationId,",
        "      applyRuntimeContext(buildBehaviorCardPayload(decisionOperationId, buildOperationPayload(decisionOperationId), behaviorEvidenceKeysByOperation), context),",
        "    );",
        "    absorbEnvelopeContext(decision, context);",
        "    const decisionData = extractEnvelopeData<Record<string, unknown>>(decision);",
        *(
            persistence_roundtrip_assertion_lines("decisionOperationId", "decision")
            if operation_supports_persistence_roundtrip(decision_operation_id, endpoint_rows)
            else []
        ),
        "    expect(decisionData.review_report_id).toBe(detailData.review_report_id);",
        "    expect(decisionData.saved).toBe(true);",
    ]


def render_export_semantics_body(primary_operation_id: str) -> tuple[list[str], list[str]]:
    return [
        f'const primaryOperationId = "{primary_operation_id}";',
    ], [
        "    const context: Record<string, unknown> = {};",
        "    const payload = applyRuntimeContext(buildBehaviorCardPayload(primaryOperationId, buildOperationPayload(primaryOperationId), behaviorEvidenceKeysByOperation), context);",
        "    const result = await invokeHttpOperation(runtime, primaryOperationId, payload);",
        "    absorbEnvelopeContext(result, context);",
        "    const data = extractEnvelopeData<Record<string, unknown>>(result);",
        *persistence_roundtrip_assertion_lines("primaryOperationId", "result"),
        "    expect(String(data.task_id ?? '')).not.toHaveLength(0);",
        '    expect(String(data.state ?? "")).toBe("created");',
    ]


def render_read_bundle_body(
    operation_ids: list[str],
    context_fields: list[str],
    final_fields: list[str],
    *,
    final_is_array: bool,
    endpoint_rows: list[dict[str, object]],
) -> tuple[list[str], list[str]]:
    first_operation_id = operation_ids[0] if operation_ids else ""
    final_operation_id = operation_ids[-1] if operation_ids else ""
    shared_fields = shared_response_business_fields(endpoint_rows, first_operation_id, final_operation_id)
    literal_fields = scalar_business_value_fields(endpoint_rows, final_operation_id)
    enriched_context_fields = dedupe_preserve_order([*context_fields, *shared_fields])
    const_lines = [
        f"const expectedContextFields = {json.dumps(enriched_context_fields, ensure_ascii=False)};",
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
        "      const payload = applyRuntimeContext(buildBehaviorCardPayload(operationId, buildOperationPayload(operationId), behaviorEvidenceKeysByOperation), context);",
        "      const result = await invokeHttpOperation(runtime, operationId, payload);",
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
        *(["    const firstData = extractEnvelopeData<Record<string, unknown>>(results[0]);"] if shared_fields else []),
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
        field_literal = json.dumps(field, ensure_ascii=False)
        lines.append(f"    expect(normalizeRuntimeIdentifierValue({field_literal}, String({target_expr}{access}))).toBe(normalizeRuntimeIdentifierValue({field_literal}, String(firstData{access})));" )
    for field, value in literal_fields.items():
        access = ts_property_access(field)
        target_expr = "finalRecord" if final_is_array else "finalData"
        lines.append(f"    expect({target_expr}{access}).toEqual({literal_ts_value(value)});")
    if not shared_fields and not literal_fields:
        lines.append("    expect(reviewBoundReason).toBe('business_assertions_not_inferred');")
    return const_lines, lines


def render_operation_chain_body(
    operation_ids: list[str],
    *,
    context_fields: list[str],
    final_fields: list[str],
    final_record_key: str,
    final_id_field: str,
    endpoint_rows: list[dict[str, object]],
) -> tuple[list[str], list[str]]:
    const_lines = [
        f"const expectedContextFields = {json.dumps(context_fields, ensure_ascii=False)};",
        f"const finalDataFields = {json.dumps(final_fields, ensure_ascii=False)};",
        f'const finalRecordKey = "{final_record_key}";',
        f'const finalIdField = "{final_id_field}";',
    ]
    lines = [
        "    const context: Record<string, unknown> = {};",
        "    const results: unknown[] = [];",
        "    let persistenceEvidenceCount = 0;",
        "    let requiresPersistenceRoundTripEvidenceObserved = false;",
        "    for (const operationId of operationIds) {",
        "      const payload = applyRuntimeContext(buildBehaviorCardPayload(operationId, buildOperationPayload(operationId), behaviorEvidenceKeysByOperation), context);",
        "      const result = await invokeHttpOperation(runtime, operationId, payload);",
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
        "    const finalData = extractEnvelopeData<Record<string, unknown>>(results.at(-1));",
        "    if (requiresPersistenceRoundTripEvidenceObserved) {",
        "      expect(persistenceEvidenceCount).toBeGreaterThan(0);",
        "    }",
        *[
            f"    expect(finalData).toHaveProperty({json.dumps(field, ensure_ascii=False)});"
            for field in final_fields
        ],
        *[
            f"    expect(String(finalData{ts_property_access(field)} ?? '')).not.toHaveLength(0);"
            for field in final_fields
        ],
        *[
            f"    expect(finalData{ts_property_access(field)}).toEqual(expect.any(String));"
            for field in final_fields
            if field.endswith("Id") or field.endswith("_id")
        ],
        *[
            f"    expect(finalData{ts_property_access(field)}).toEqual({literal_ts_value(value)});"
            for field, value in scalar_business_value_fields(endpoint_rows, operation_ids[-1] if operation_ids else "").items()
        ],
    ]
    return const_lines, lines


def render_generic_success_body(
    primary_operation_id: str,
    record_key: str,
    id_field: str,
    final_fields: list[str],
    *,
    final_is_array: bool,
    endpoint_rows: list[dict[str, object]],
) -> tuple[list[str], list[str]]:
    const_lines = [f'const primaryOperationId = "{primary_operation_id}";', f"const finalDataFields = {json.dumps(final_fields, ensure_ascii=False)};"]
    lines = [
        "    const context: Record<string, unknown> = {};",
        "    const result = await invokeHttpOperation(runtime, primaryOperationId, applyRuntimeContext(buildBehaviorCardPayload(primaryOperationId, buildOperationPayload(primaryOperationId), behaviorEvidenceKeysByOperation), context));",
        "    absorbEnvelopeContext(result, context);",
        *(
            [
                "    const data = extractEnvelopeData<unknown>(result);",
                "    expect(Array.isArray(data)).toBe(true);",
                "    const finalRows = data as Array<Record<string, unknown>>;",
                "    expect(finalRows.length).toBeGreaterThan(0);",
                "    const finalRecord = finalRows[0];",
            ]
            if final_is_array
            else [
                "    const data = extractEnvelopeData<Record<string, unknown>>(result);",
                "    expect(Array.isArray(data)).toBe(false);",
                "    const finalRecord = data;",
            ]
        ),
        *(
            persistence_roundtrip_assertion_lines("primaryOperationId", "result")
            if operation_supports_persistence_roundtrip(primary_operation_id, endpoint_rows)
            else []
        ),
        *[
            f"    expect(finalRecord).toHaveProperty({json.dumps(field, ensure_ascii=False)});"
            for field in final_fields
        ],
        *[
            f"    expect(String(finalRecord{ts_property_access(field)} ?? '')).not.toHaveLength(0);"
            for field in final_fields
        ],
        "    expect(Boolean(finalRecord[finalDataFields[0]])).toBe(true);",
        *[
            f"    expect(finalRecord{ts_property_access(field)}).toEqual(expect.any(String));"
            for field in final_fields
            if field.endswith("Id") or field.endswith("_id")
        ],
        *[
            f"    expect({'finalRecord' if final_is_array else 'data'}{ts_property_access(field)}).toEqual({literal_ts_value(value)});"
            for field, value in scalar_business_value_fields(endpoint_rows, primary_operation_id).items()
        ],
    ]
    return const_lines, lines


def render_body(
    row: dict[str, object],
    *,
    operation_ids: list[str],
    endpoint_rows: list[dict[str, object]],
    failure_code: str,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> tuple[list[str], list[str]]:
    profile = scenario_profile(row, operation_ids=operation_ids, endpoint_rows=endpoint_rows, failure_code=failure_code)
    primary_operation_id = operation_ids[0] if operation_ids else ""
    failure_operation_id = choose_failure_operation(
        operation_ids,
        endpoint_rows,
        failure_code,
        behavior_card_models=behavior_card_models,
    )
    primary_record = primary_record_key(endpoint_rows, primary_operation_id)
    primary_id = primary_id_field(endpoint_rows, primary_operation_id)
    final_operation_id = operation_ids[-1] if operation_ids else ""
    final_record = primary_record_key(endpoint_rows, final_operation_id)
    final_id = primary_id_field(endpoint_rows, final_operation_id)
    final_fields = [field for field in response_data_fields(endpoint_rows, final_operation_id) if field]
    context_fields = expected_context_fields(endpoint_rows, operation_ids)

    if profile == "validation_failure":
        return render_validation_failure_body(failure_operation_id, primary_record)
    if profile == "tenant_deny":
        return render_tenant_deny_body(failure_operation_id)
    if profile == "forbidden_deny":
        return render_forbidden_deny_body(failure_operation_id)
    if profile == "uncertainty_detail":
        return render_uncertainty_body(
            row,
            primary_operation_id=primary_operation_id,
            operation_ids=operation_ids,
            endpoint_rows=endpoint_rows,
            record_key=primary_record,
            id_field=primary_id,
        )
    if profile == "versioned_update":
        return render_versioned_update_body(primary_operation_id, primary_record, primary_id)
    if profile == "concurrent_conflict":
        return render_concurrent_conflict_body(
            primary_operation_id,
            failure_operation_id,
            primary_record,
            primary_id,
            response_data_fields(endpoint_rows, primary_operation_id),
        )
    if profile == "review_binding":
        return render_review_binding_body(
            detail_operation_id=next((operation for operation in operation_ids if operation == "GetReviewReportDetail"), primary_operation_id),
            decision_operation_id=next((operation for operation in operation_ids if operation == "RecordReviewDecision"), operation_ids[-1] if operation_ids else ""),
        )
    if profile == "export_semantics":
        return render_export_semantics_body(primary_operation_id)
    if profile == "read_bundle":
        return render_read_bundle_body(
            operation_ids,
            context_fields,
            final_fields,
            final_is_array=response_is_array(endpoint_rows, final_operation_id),
            endpoint_rows=endpoint_rows,
        )
    if profile == "operation_chain":
        return render_operation_chain_body(
            operation_ids,
            context_fields=context_fields,
            final_fields=final_fields,
            final_record_key=final_record,
            final_id_field=final_id,
            endpoint_rows=endpoint_rows,
        )
    return render_generic_success_body(
        primary_operation_id,
        primary_record,
        primary_id,
        final_fields,
        final_is_array=response_is_array(endpoint_rows, final_operation_id),
        endpoint_rows=endpoint_rows,
    )


def render_scenario_skip_test(row: dict[str, object], *, unresolved_operation_ids: list[str]) -> str:
    scenario_name = str(row["scenario"])
    scenario_id, label = scenario_identifier(scenario_name)
    unresolved_suffix = f": {', '.join(unresolved_operation_ids)}" if unresolved_operation_ids else ""
    return "\n".join(
        [
            'import { describe, it } from "vitest";',
            "",
            f'describe("Scenario: {scenario_id} {label}", () => {{',
            '  it.skip("remains review-bound until the compiled OpenAPI contract exposes executable operations'
            f'{unresolved_suffix}", () => {{}});',
            "});",
            "",
        ]
    )


def render_scenario_test(
    row: dict[str, object],
    *,
    endpoint_rows: list[dict[str, object]] | None = None,
    unresolved_operation_ids: list[str] | None = None,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> str:
    scenario_name = str(row["scenario"])
    scenario_id, label = scenario_identifier(scenario_name)
    upstream = json.dumps(row.get("upstream_trace_ids", []), ensure_ascii=False)
    endpoint_rows = endpoint_rows or []
    if "_resolved_operation_ids" in row:
        resolved_operation_ids = row.get("_resolved_operation_ids", [])
        if isinstance(resolved_operation_ids, list):
            operation_ids = [str(item).strip() for item in resolved_operation_ids if str(item).strip()]
        else:
            operation_ids = []
    else:
        operation_ids = []
    if not operation_ids and "_resolved_operation_ids" not in row:
        operation_ids = dedupe_preserve_order(infer_operation_ids(row, endpoint_rows))
    if not operation_ids:
        return render_scenario_skip_test(row, unresolved_operation_ids=unresolved_operation_ids or [])
    failure_code = preferred_failure_code(row, endpoint_rows, operation_ids, behavior_card_models=behavior_card_models)
    behavior_mapping_lines = []
    for operation_id in operation_ids:
        model = (behavior_card_models or {}).get(operation_id)
        if model:
            behavior_mapping_lines.extend(render_behavior_step_test_mapping(model)["scenario"].splitlines())
    const_lines, body_lines = render_body(
        row,
        operation_ids=operation_ids,
        endpoint_rows=endpoint_rows,
        failure_code=failure_code,
        behavior_card_models=behavior_card_models,
    )
    supplemental_failure_lines = render_supplemental_failure_variant_tests(
        scenario_failure_variants(endpoint_rows, operation_ids, behavior_card_models=behavior_card_models)
    )
    include_failure_code = any("failureCode" in line for line in const_lines + body_lines)
    generated_body_text = "\n".join([*behavior_mapping_lines, *const_lines, *body_lines, *supplemental_failure_lines])
    return "\n".join(
        [
            'import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";',
            *render_harness_import(generated_body_text),
            "",
            "let runtime: BackendRuntime;",
            "",
            f'const upstreamTraceIds = {upstream};',
            f'const acceptanceCriteria = {json.dumps(str(row.get("acceptance_criteria", "")), ensure_ascii=False)};',
            f'const measurementHook = {json.dumps(str(row.get("measurement_hook", "")), ensure_ascii=False)};',
            f"const operationIds = {json.dumps(operation_ids, ensure_ascii=False)};",
            f"const behaviorEvidenceKeysByOperation = {json.dumps(behavior_evidence_key_map(operation_ids, behavior_card_models), ensure_ascii=False)};",
            *([f'const failureCode = "{failure_code}";'] if include_failure_code else []),
            *typescript_behavior_card_payload_helper_lines(map_name="behaviorEvidenceKeysByOperation"),
            *(scenario_state_collector_lines() if "buildFailurePayload" in generated_body_text else []),
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
            f'describe("Scenario: {scenario_id} {label}", () => {{',
            f'  it("Given {str(row.get("given", ""))}, When {str(row.get("when", ""))}, Then {str(row.get("then", ""))}", async () => {{',
            "    expect(upstreamTraceIds.length).toBeGreaterThan(0);",
            "    expect(acceptanceCriteria.length).toBeGreaterThan(0);",
            "    expect(measurementHook.length).toBeGreaterThan(0);",
            "    expect(operationIds.length).toBeGreaterThan(0);",
            *body_lines,
            "  });",
            *supplemental_failure_lines,
            "});",
            "",
        ]
    )


def scaffold_scenario_tests(
    stage_03_text: str,
    output_dir: Path,
    *,
    esp_text: str = "",
    openapi_spec: dict[str, object] | None = None,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    rows = parse_scenario_rows(stage_03_text)
    source_endpoint_rows = parse_api_endpoint_rows(esp_text) if esp_text.strip() else []
    runtime_endpoint_rows = endpoint_rows_from_openapi_spec(openapi_spec or {}) if openapi_spec else []
    inference_endpoint_rows = source_endpoint_rows or runtime_endpoint_rows
    render_endpoint_rows = runtime_endpoint_rows or source_endpoint_rows
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for row in rows:
        operation_ids = dedupe_preserve_order(infer_operation_ids(row, inference_endpoint_rows))
        operation_ids = filter_context_compatible_operation_chain(row, inference_endpoint_rows, operation_ids)
        unresolved_operation_ids: list[str] = []
        if runtime_endpoint_rows and source_endpoint_rows:
            if operation_ids:
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
            else:
                operation_ids = dedupe_preserve_order(infer_operation_ids(row, runtime_endpoint_rows))
                operation_ids = filter_context_compatible_operation_chain(row, runtime_endpoint_rows, operation_ids)
        target = output_dir / scenario_test_filename(str(row["scenario"]))
        target.write_text(
            render_scenario_test(
                {**row, "_resolved_operation_ids": operation_ids},
                endpoint_rows=render_endpoint_rows,
                unresolved_operation_ids=unresolved_operation_ids,
                behavior_card_models=behavior_card_models,
            ),
            encoding="utf-8",
        )
        files.append(str(target))
    return {"output_dir": str(output_dir), "files_created": files, "count": len(files)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate executable scenario tests from Stage-03")
    parser.add_argument("--stage-03", required=True, help="Path to Stage-03 markdown")
    parser.add_argument("--esp", help="Optional ESP path for endpoint inference")
    parser.add_argument("--openapi", help="Optional final OpenAPI path for runtime operation remapping")
    parser.add_argument("--output-dir", required=True, help="Target directory for *.scenario.test.ts files")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    text = Path(args.stage_03).resolve().read_text(encoding="utf-8")
    esp_text = Path(args.esp).resolve().read_text(encoding="utf-8") if args.esp else ""
    openapi_spec = json.loads(Path(args.openapi).resolve().read_text(encoding="utf-8")) if args.openapi else None
    summary = scaffold_scenario_tests(
        text,
        Path(args.output_dir).resolve(),
        esp_text=esp_text,
        openapi_spec=openapi_spec,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
