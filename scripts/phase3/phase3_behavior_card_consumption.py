#!/usr/bin/env python3
"""Consume P3 behavior cards for test, service, and repository scaffolding."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import re
from string import Template

try:
    from common.script_data_assets import load_script_text_asset
    from phase3.renderer_common import ts_identifier, ts_optional_property_access, ts_property_access, ts_property_key
    from phase3.test_scaffolder_common import normalized_semantic_owner
except ModuleNotFoundError:
    from common.script_data_assets import load_script_text_asset
    from phase3.renderer_common import ts_identifier, ts_optional_property_access, ts_property_access, ts_property_key
    from phase3.test_scaffolder_common import normalized_semantic_owner
from pathlib import Path
from typing import Any


TRACE_ID_RE = re.compile(r"\bP[12]-(?:US|UC|REQ|AC|DTR|CTR|RP|RT)-\d+\b")

WFF_SCRIPT_DATA_ASSETS = (
    "scripts/phase3/data/behavior-service-command.ts.template",
    "scripts/phase3/data/behavior-service-readonly.ts.template",
    "scripts/phase3/data/behavior-repository-command.ts.template",
    "scripts/phase3/data/behavior-repository-readonly.ts.template",
)


def load_behavior_template(template_name: str) -> str:
    return load_script_text_asset(__file__, template_name)


def _render_behavior_template(template_name: str, values: dict[str, Any]) -> str:
    rendered = Template(load_behavior_template(template_name)).safe_substitute(
        {key: str(value) for key, value in values.items()}
    )
    return rendered.rstrip()


def _section(text: str, title: str) -> str:
    pattern = re.compile(rf"^##\s+\d+[A-Z]?\.\s+{re.escape(title)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    next_match = re.search(r"^##\s+\d+[A-Z]?\.\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.end() : end]


def _lower_camel(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", value).strip()
    parts = cleaned.split()
    if not parts:
        return "operation"
    first = parts[0][0].lower() + parts[0][1:]
    return ts_identifier(first + "".join(part[:1].upper() + part[1:] for part in parts[1:]))


def _upper_camel(value: str) -> str:
    camel = _lower_camel(value)
    return camel[:1].upper() + camel[1:]


def _parse_steps(pseudocode: str) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    for match in re.finditer(r"^\s*(\d+)\.\s+(.+?)\s*$", pseudocode, re.MULTILINE):
        step_no = match.group(1)
        title = re.sub(r"\s+", " ", match.group(2)).strip()
        steps.append({"id": f"step-{step_no}", "title": title})
    return steps


def _parse_error_codes(table_text: str) -> list[str]:
    codes: list[str] = []
    for line in table_text.splitlines():
        if not line.strip().startswith("|") or "---" in line or "error_code" in line:
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if cells and cells[0]:
            codes.append(cells[0])
    return list(dict.fromkeys(codes))


def _parse_inline_error_codes(section_text: str) -> list[str]:
    codes: list[str] = []
    for match in re.finditer(r"`([a-z][a-z0-9_]+)`", section_text):
        code = match.group(1)
        if any(marker in code for marker in ("error", "invalid", "forbidden", "conflict", "unavailable", "not_found")):
            codes.append(code)
    return list(dict.fromkeys(codes))


def _behavior_error_codes(markdown: str) -> list[str]:
    explicit_codes = [
        *_parse_inline_error_codes(_section(markdown, "Public Contract")),
        *_parse_error_codes(_section(markdown, "Error Trigger Table")),
    ]
    codes = list(dict.fromkeys(explicit_codes))
    for required_code in ("invalid_request", "version_conflict"):
        if required_code not in codes:
            codes.append(required_code)
    return codes


def _parse_bullet_value(section_text: str, label: str) -> str:
    pattern = re.compile(rf"^-\s+{re.escape(label)}:\s*(.+)$", re.MULTILINE)
    match = pattern.search(section_text)
    value = match.group(1).strip() if match else ""
    return "" if not normalized_semantic_owner(value) else value


def _parse_csv_value(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip() and item.strip() != "none"]


def _parse_operation_semantics(markdown: str) -> dict[str, Any]:
    section = _section(markdown, "Operation Semantic Payload")
    if not section:
        return {"status": "missing"}
    semantics = {
        "status": _parse_bullet_value(section, "semantic_status") or "resolved",
        "owner_service": _parse_bullet_value(section, "owner_service"),
        "aggregate": _parse_bullet_value(section, "aggregate"),
        "state_set": _parse_csv_value(_parse_bullet_value(section, "state_set")),
        "trigger_events": _parse_csv_value(_parse_bullet_value(section, "trigger_events")),
        "mutation_guard": _parse_bullet_value(section, "mutation_guard"),
        "terminal_or_failure_exit": _parse_bullet_value(section, "terminal_or_failure_exit"),
        "readonly_dependencies": _parse_csv_value(_parse_bullet_value(section, "readonly_dependencies")),
        "evidence_keys": _parse_csv_value(_parse_bullet_value(section, "evidence_keys")),
    }
    return semantics


def extract_behavior_card_model(markdown: str) -> dict[str, Any]:
    title_match = re.search(r"^#\s+可溯源业务行为卡：(.+?)\s*$", markdown, re.MULTILINE)
    binding = _section(markdown, "Traceability Binding")
    operation_match = re.search(r"operation_id:\s*([A-Za-z0-9_.-]+)", binding)
    operation_id = operation_match.group(1) if operation_match else (title_match.group(1).strip() if title_match else "UnknownOperation")
    persistence = _section(markdown, "State And Persistence Effects")
    persistence_effects = _parse_bullet_value(persistence, "tables / collections / queues affected")
    invariants = _parse_bullet_value(persistence, "invariants")
    state_transition = _parse_bullet_value(persistence, "state transition")
    return {
        "operation_id": operation_id,
        "upstream_trace_ids": list(dict.fromkeys(TRACE_ID_RE.findall(binding))),
        "steps": _parse_steps(_section(markdown, "Human-Readable Pseudocode")),
        "error_codes": _behavior_error_codes(markdown),
        "business_intent": _section(markdown, "Business Intent").strip(),
        "operation_semantics": _parse_operation_semantics(markdown),
        "persistence_effects": persistence_effects,
        "invariants": invariants,
        "state_transition": state_transition,
        "transaction_rule": _parse_bullet_value(persistence, "transaction / idempotency / replay rule"),
        "audit_effect": _parse_bullet_value(persistence, "audit / event / side effect"),
    }


def _step(model: dict[str, Any], step_id: str) -> str:
    for item in model.get("steps", []):
        if item.get("id") == step_id:
            return str(item.get("title", step_id))
    return step_id



def _join_nonempty(lines: list[str]) -> str:
    return "\n".join(line for line in lines if line)


def render_behavior_step_test_mapping(model: dict[str, Any]) -> dict[str, str]:
    operation_id = str(model.get("operation_id", "UnknownOperation"))
    errors = ", ".join(model.get("error_codes", [])) or "public error semantics"
    persistence = str(model.get("persistence_effects", "durable state"))
    invariants = str(model.get("invariants", "business invariants"))
    state_transition = str(model.get("state_transition") or "state transition")
    transaction_rule = str(model.get("transaction_rule") or "transaction/read-back evidence")
    semantics = model.get("operation_semantics") if isinstance(model.get("operation_semantics"), dict) else {}
    owner_service = str(semantics.get("owner_service") or "")
    aggregate = str(semantics.get("aggregate") or "")
    trigger_events = ", ".join(semantics.get("trigger_events", [])) if isinstance(semantics.get("trigger_events"), list) else ""
    evidence_keys = ", ".join(semantics.get("evidence_keys", [])) if isinstance(semantics.get("evidence_keys"), list) else ""
    agentic_decision = model.get("agentic_semantic_decision") if isinstance(model.get("agentic_semantic_decision"), dict) else {}
    agentic_invariants = agentic_decision.get("domain_invariants") if isinstance(agentic_decision.get("domain_invariants"), list) else []
    agentic_test_intents = [
        str(item.get("test_intent") or "").strip()
        for item in agentic_invariants
        if isinstance(item, dict) and str(item.get("test_intent") or "").strip()
    ]
    agentic_test_intent_lines = [
        f"// agentic-semantic-test-intent: {item}"
        for item in agentic_test_intents
    ]
    if owner_service and aggregate:
        semantic_subject = f"{owner_service} owns {aggregate}"
    elif aggregate:
        semantic_subject = f"aggregate {aggregate} has no authoritative owner declared"
    elif owner_service:
        semantic_subject = f"{owner_service} has no aggregate declared"
    else:
        semantic_subject = "review-bound"
    semantic_assertion = f"// operation-semantic-business-assertion: {semantic_subject}; events: {trigger_events}; evidence: {evidence_keys}" if semantic_subject != "review-bound" or trigger_events or evidence_keys else "// operation-semantic-business-assertion: review-bound"
    return {
        "contract": _join_nonempty([
                f"// behavior-card-step: step-1 {_step(model, 'step-1')}",
                f"// behavior-card-step: step-2 {_step(model, 'step-2')}",
                f"// behavior-card-errors: {errors}",
                f"// behavior-card-evidence-assertion: contract must prove {invariants}",
                semantic_assertion,
                f'expect(operationId).toBe("{operation_id}");',
            ]),
        "scenario": _join_nonempty([
                f"// behavior-card-step: step-3 {_step(model, 'step-3')}",
                f"// behavior-card-step: step-4 {_step(model, 'step-4')}",
                f"// behavior-card-state-transition: {model.get('state_transition', 'state transition')}",
                semantic_assertion,
                *agentic_test_intent_lines,
                f"// behavior-card-errors: {errors}",
            ]),
        "replay": _join_nonempty([
                f"// behavior-card-step: step-6 {_step(model, 'step-6')}",
                f"// behavior-card-trace: {', '.join(model.get('upstream_trace_ids', []))}",
            ]),
        "sql": _join_nonempty([
                f"// behavior-card-step: step-5 {_step(model, 'step-5')}",
                f"// behavior-card-persistence-effects: {persistence}",
                f"// behavior-card-invariants: {invariants}",
                f"// behavior-card-transaction-rule: {transaction_rule}",
            ]),
        "unit": _join_nonempty([
                f"// behavior-card-step: step-2 {_step(model, 'step-2')}",
                f"// behavior-card-step: step-4 {_step(model, 'step-4')}",
                f"// behavior-card-value-rule: {state_transition}",
                f"// behavior-card-domain-invariant: {invariants}",
                semantic_assertion,
                *agentic_test_intent_lines,
                f"// behavior-card-errors: {errors}",
            ]),
    }


def _typescript_error_union(error_codes: list[str]) -> str:
    codes = error_codes or ["invalid_request"]
    return " | ".join(f'"{code}"' for code in codes)


def _typescript_error_policy(error_codes: list[str]) -> str:
    defaults = {
        "invalid_request": (400, "business_error", "never"),
        "forbidden": (403, "business_error", "never"),
        "tenant_forbidden": (403, "business_error", "never"),
        "not_found": (404, "business_error", "never"),
        "version_conflict": (409, "business_error", "never"),
        "dependency_unavailable": (503, "system_error", "safe"),
    }
    lines: list[str] = []
    for code in error_codes or ["invalid_request"]:
        status, kind, retryability = defaults.get(code, (400, "business_error", "never"))
        lines.append(f'      {code}: {{ status: {status}, kind: "{kind}", retryability: "{retryability}" }},')
    return "\n".join(lines)


def _typescript_literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _response_example_data_shape(response_example: dict[str, Any]) -> dict[str, Any]:
    data = response_example.get("data", {})
    if isinstance(data, list):
        first = data[0] if data and isinstance(data[0], dict) else {}
        return first
    return data if isinstance(data, dict) else {}





def _typescript_response_field_kind(field: str, example_value: Any) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", field).lower()
    if isinstance(example_value, bool):
        return "boolean"
    if isinstance(example_value, (int, float)) and not isinstance(example_value, bool):
        return "number"
    if normalized in {"status", "state"}:
        return "status"
    if normalized in {"trace_id", "traceid"}:
        return "trace"
    if normalized in {"request_id", "requestid"}:
        return "request"
    if normalized.endswith("_id") or normalized.endswith("id"):
        return "id"
    return "string"


def _typescript_response_projection_expr(
    *,
    field: str,
    example_value: Any,
    operation_id: str,
    source_name: str,
) -> str:
    op = _upper_camel(operation_id)
    return (
        f"this.project{op}ResponseField("
        f"{_typescript_literal(field)}, context, nextState, {source_name}, "
        f"{_typescript_literal(_typescript_response_field_kind(field, example_value))}, "
        f"{_typescript_literal(operation_id)})"
    )


def _typescript_response_projection(response_example: dict[str, Any], evidence_keys: list[str] | None = None, operation_id: str = "Operation") -> str:
    _ = evidence_keys
    data = response_example.get("data", {})
    shape = _response_example_data_shape(response_example)
    if not shape:
        return "    const responseData: unknown = nextState;"
    target_name = "responseItem" if isinstance(data, list) else "responseData"
    lines = [
        *(['    const responseRows = Array.isArray(nextState.data) ? nextState.data : undefined;'] if isinstance(data, list) else []),
        "    const responseEnvelopeData = nextState.data && typeof nextState.data === \"object\" && !Array.isArray(nextState.data) ? nextState.data as Record<string, unknown> : {};",
        (
            "    const responseSource = responseRows && responseRows[0] && typeof responseRows[0] === \"object\" && !Array.isArray(responseRows[0]) ? responseRows[0] as Record<string, unknown> : responseEnvelopeData;"
            if isinstance(data, list)
            else "    const responseSource = Array.isArray(nextState.data) && nextState.data[0] && typeof nextState.data[0] === \"object\" ? nextState.data[0] as Record<string, unknown> : responseEnvelopeData;"
        ),
        f"    const {target_name}: Record<string, unknown> = {{",
    ]
    for key, example_value in shape.items():
        field = str(key)
        lines.append(
            f"      {ts_property_key(field)}: {_typescript_response_projection_expr(field=field, example_value=example_value, operation_id=operation_id, source_name='responseSource')},"
        )
    lines.append("    };")
    if isinstance(data, list):
        lines.append("    const responseData: unknown = responseRows ? responseRows.map((entry) => {")
        lines.append('      const rowSource = entry && typeof entry === "object" && !Array.isArray(entry) ? entry as Record<string, unknown> : {};')
        lines.append("      return {")
        for key, example_value in shape.items():
            field = str(key)
            lines.append(
                f"        {ts_property_key(field)}: {_typescript_response_projection_expr(field=field, example_value=example_value, operation_id=operation_id, source_name='rowSource')},"
            )
        lines.append("      };")
        lines.append("    }) : (Object.keys(responseSource).length > 0 ? [responseItem] : []);")
    return "\n".join(lines)


def _typescript_response_field_projection_method(op: str) -> str:
    return (
        f"\n  private project{op}ResponseField(\n"
        "    field: string,\n"
        "    context: Record<string, unknown>,\n"
        "    nextState: Record<string, unknown>,\n"
        "    responseSource: Record<string, unknown>,\n"
        '    valueKind: "boolean" | "id" | "number" | "request" | "status" | "string" | "trace",\n'
        "    operationId: string,\n"
        "  ): unknown {\n"
        '    const requestedSnake = field.replace(/([a-z0-9])([A-Z])/g, "$1_$2").replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "").toLowerCase();\n'
        "    const requestedCamel = requestedSnake.replace(/_([a-z0-9])/g, (_, char: string) => char.toUpperCase());\n"
        "    const aliases = Array.from(new Set([field, requestedSnake, requestedCamel].filter(Boolean)));\n"
        "    for (const source of [responseSource, nextState, context]) {\n"
        "      if (!source || typeof source !== \"object\" || Array.isArray(source)) {\n"
        "        continue;\n"
        "      }\n"
        "      for (const alias of aliases) {\n"
        "        const value = source[alias];\n"
        "        if (value !== undefined && value !== null && value !== \"\") {\n"
        "          return value;\n"
        "        }\n"
        "      }\n"
        "    }\n"
        '    if (valueKind === "boolean") {\n'
        '      throw createApiError(400, "business_error", "invalid_request", "never", `${operationId} requires ${field} response evidence`);\n'
        "    }\n"
        '    if (valueKind === "number") {\n'
        '      throw createApiError(400, "business_error", "invalid_request", "never", `${operationId} requires ${field} response evidence`);\n'
        "    }\n"
        '    if (valueKind === "status") {\n'
        "      const stateValue = nextState.state ?? context.state;\n"
        "      if (stateValue === undefined || stateValue === null || stateValue === \"\") {\n"
        '        throw createApiError(400, "business_error", "invalid_request", "never", `${operationId} requires ${field} response evidence`);\n'
        "      }\n"
        "      return String(stateValue);\n"
        "    }\n"
        '    if (valueKind === "trace") {\n'
        "      const traceValue = nextState.trace_id ?? nextState.traceId ?? context.trace_id ?? context.traceId;\n"
        "      if (traceValue === undefined || traceValue === null || traceValue === \"\") {\n"
        '        throw createApiError(400, "business_error", "invalid_request", "never", `${operationId} requires trace evidence`);\n'
        "      }\n"
        "      return String(traceValue);\n"
        "    }\n"
        '    if (valueKind === "request") {\n'
        "      const requestValue = nextState.request_id ?? nextState.requestId ?? context.request_id ?? context.requestId;\n"
        "      if (requestValue === undefined || requestValue === null || requestValue === \"\") {\n"
        '        throw createApiError(400, "business_error", "invalid_request", "never", `${operationId} requires request evidence`);\n'
        "      }\n"
        "      return String(requestValue);\n"
        "    }\n"
        '    if (valueKind === "id") {\n'
        '      throw createApiError(400, "business_error", "invalid_request", "never", `${operationId} requires ${field} response evidence`);\n'
        "    }\n"
        '    throw createApiError(400, "business_error", "invalid_request", "never", `${operationId} requires ${field} response evidence`);\n'
        "  }\n"
    )


def _typescript_meta_projection(response_example: dict[str, Any], operation_id: str) -> str:
    meta = response_example.get("meta", {}) if isinstance(response_example.get("meta", {}), dict) else {}
    if not meta:
        return f'    const responseMeta: Record<string, unknown> = {{ operation_id: "{operation_id}" }};'
    lines = [
        "    const responseEnvelopeMeta = nextState.meta && typeof nextState.meta === \"object\" && !Array.isArray(nextState.meta) ? nextState.meta as Record<string, unknown> : {};",
        "    const responseMeta: Record<string, unknown> = {",
    ]
    for key, example_value in meta.items():
        field = str(key)
        lines.append(
            f"      {ts_property_key(field)}: {_typescript_response_projection_expr(field=field, example_value=example_value, operation_id=operation_id, source_name='responseEnvelopeMeta')},"
        )
    lines.append("    };")
    return "\n".join(lines)


def _typescript_pagination_projection(operation_spec: dict[str, Any], response_example: dict[str, Any]) -> str:
    pagination_rule = str(operation_spec.get("paginationRule", "")).strip().lower()
    meta = response_example.get("meta", {}) if isinstance(response_example.get("meta", {}), dict) else {}
    if "cursor" not in pagination_rule and not any(
        key in meta for key in ("nextCursor", "next_cursor", "hasMore", "has_more", "pageSize", "page_size", "limit", "total")
    ):
        return ""

    next_cursor = meta.get("nextCursor", meta.get("next_cursor", ""))
    has_more = meta.get("hasMore", meta.get("has_more", bool(next_cursor)))
    page_size = meta.get("pageSize", meta.get("page_size", meta.get("limit", 20)))
    return "\n".join(
        [
            "      pagination: {",
            f"        hasMore: Boolean(context.hasMore ?? context.has_more ?? nextState.hasMore ?? nextState.has_more ?? {_typescript_literal(has_more)}),",
            f"        pageSize: Number(context.pageSize ?? context.page_size ?? nextState.pageSize ?? nextState.page_size ?? context.limit ?? nextState.limit ?? {_typescript_literal(page_size)}),",
            '        nextCursor: String(context.nextCursor ?? context.next_cursor ?? nextState.nextCursor ?? nextState.next_cursor ?? "runtime-cursor"),',
            "      },",
        ]
    )


def _typescript_forced_failure_method(op: str, error_codes: list[str]) -> str:
    _ = error_codes
    return "\n".join(
        [
            f"  private assert{op}BusinessPreconditions(context: Record<string, unknown>): void {{",
            "    if (context.invalid_query === true || context.invalid_query === \"true\") {",
            f'      throw this.map{op}Error("invalid_request");',
            "    }",
            "  }",
            "",
        ]
    )



def _typescript_path_param_not_found_guard(operation_spec: dict[str, Any], op: str, error_codes: list[str]) -> str:
    if "not_found" not in error_codes:
        return ""
    path_params = operation_spec.get("pathParams", [])
    if not isinstance(path_params, list) or not path_params:
        return ""
    lines = ['    const pathParams = context.path_params as Record<string, unknown> | undefined;']
    for raw_param in path_params:
        param = str(raw_param).strip()
        if not param:
            continue
        suffix = _upper_camel(param)
        lines.append(
            f'    const pathParam{suffix} = String(pathParams{ts_optional_property_access(param)} ?? context{ts_property_access(param)} ?? "");'
        )
        lines.append(f'    if (pathParam{suffix}.startsWith("missing_")) {{')
        lines.append(f'      throw this.map{op}Error("not_found");')
        lines.append('    }')
    return "\n".join(lines)




def _typescript_identifier(value: str, suffix: str = "") -> str:
    base = ts_identifier(_lower_camel(value))
    return f"{base}{suffix}"


def _typescript_context_resolver_method(op: str) -> str:
    return (
        f"\n  private resolve{op}ContextValue(context: Record<string, unknown>, key: string): unknown {{\n"
        '    const requestedSnake = key.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();\n'
        "    for (const source of [context, context.path_params, context.auth_context, context.body, context.input, context.query]) {\n"
        "      if (!source || typeof source !== \"object\" || Array.isArray(source)) {\n"
        "        continue;\n"
        "      }\n"
        "      const record = source as Record<string, unknown>;\n"
        "      for (const candidate of Object.keys(record)) {\n"
        '        const candidateSnake = candidate.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();\n'
        "        if (candidate === key || candidateSnake === requestedSnake) {\n"
        "          return record[candidate];\n"
        "        }\n"
        "      }\n"
        "    }\n"
        "    return undefined;\n"
        "  }\n"
    )


def _typescript_repository_result_merge_method(op: str) -> str:
    return (
        f"\n  private merge{op}RepositoryResult(nextState: Record<string, unknown>, repositoryResult: unknown): Record<string, unknown> {{\n"
        "    if (!repositoryResult || typeof repositoryResult !== \"object\" || Array.isArray(repositoryResult)) {\n"
        "      return { ...nextState };\n"
        "    }\n"
        "    const resultRecord = repositoryResult as Record<string, unknown>;\n"
        "    const data = resultRecord.data;\n"
        "    if (data && typeof data === \"object\" && !Array.isArray(data)) {\n"
        "      return { ...nextState, ...resultRecord, ...(data as Record<string, unknown>) };\n"
        "    }\n"
        "    return { ...nextState, ...resultRecord };\n"
        "  }\n"
    )


def _operation_execution_mode(model: dict[str, Any], spec: dict[str, Any]) -> str:
    explicit = str(model.get("execution_mode") or model.get("executionMode") or spec.get("executionMode") or spec.get("execution_mode") or "").strip()
    if explicit:
        return explicit
    operation_id = str(model.get("operation_id") or spec.get("operationId") or "").strip()
    method = str(spec.get("method") or "").upper()
    response_data = spec.get("responseExample", {}).get("data", {}) if isinstance(spec.get("responseExample", {}), dict) else {}
    if operation_id.startswith(("Create", "Launch", "Export")):
        return "create"
    if operation_id.startswith("Get") or (method == "GET" and not isinstance(response_data, list)):
        return "detail-read"
    if operation_id.startswith("List") or (method == "GET" and isinstance(response_data, list)):
        return "list-read"
    return "command"


def _typescript_behavior_value_validation_guards(model: dict[str, Any], op: str, error_codes: list[str]) -> str:
    invariants = str(model.get("invariants") or "").lower()
    lines: list[str] = []
    if "tenant" in invariants and "invalid_request" in error_codes:
        lines.extend(
            [
                "    // behavior-card-value-guard: tenant boundary must be explicit, not hidden by envelope shape.",
                "    if (context.tenantId === undefined && context.tenant_id === undefined) {",
                f'      throw this.map{op}Error("invalid_request");',
                "    }",
            ]
        )
    return "\n".join(lines)


def _typescript_request_field_validation_guards(operation_spec: dict[str, Any], op: str, error_codes: list[str]) -> str:
    if "invalid_request" not in error_codes:
        return ""
    required_fields = operation_spec.get("requestRequiredFields", [])
    if not isinstance(required_fields, list) or not required_fields:
        return ""
    lines: list[str] = []
    seen_fields: set[str] = set()
    for raw_field in required_fields:
        field = str(raw_field).strip()
        if not field:
            continue
        field_key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", field).lower()
        if field_key in seen_fields:
            continue
        seen_fields.add(field_key)
        variable = _typescript_identifier(field, "Value")
        camel_field = re.sub(r"_([a-z0-9])", lambda match: match.group(1).upper(), field_key)
        candidates = list(dict.fromkeys([field, field_key, camel_field]))
        value_expr = " ?? ".join(f"context[{_typescript_literal(candidate)}]" for candidate in candidates)
        lines.extend(
            [
                f"    const {variable} = {value_expr};",
                f"    if ({variable} === undefined || {variable} === null || {variable} === \"\") {{",
                f'      throw this.map{op}Error("invalid_request");',
                "    }",
            ]
        )
    return "\n".join(lines)


def _typescript_evidence_key_absorption(model: dict[str, Any], op: str) -> str:
    semantics = model.get("operation_semantics") if isinstance(model.get("operation_semantics"), dict) else {}
    evidence_keys = [
        str(item).strip()
        for item in semantics.get("evidence_keys", [])
        if str(item).strip()
    ] if isinstance(semantics.get("evidence_keys"), list) else []
    if not evidence_keys:
        return ""
    lines = [
        "    // operation-semantic-evidence-absorption: resolve evidence aliases for repository runtime consumption.",
        "    const semanticEvidence: Record<string, unknown> = {};",
    ]
    variable_counts: dict[str, int] = {}
    for key in evidence_keys:
        base_variable = _typescript_identifier(key, "Evidence")
        variable_counts[base_variable] = variable_counts.get(base_variable, 0) + 1
        variable = base_variable if variable_counts[base_variable] == 1 else f"{base_variable}{variable_counts[base_variable]}"
        lines.append(f'    const {variable} = this.resolve{op}ContextValue(context, "{key}");')
        lines.append(f'    if ({variable} !== undefined) {{')
        lines.append(f'      semanticEvidence["{key}"] = {variable};')
        lines.append("    }")
    lines.extend(
        [
            "    if (Object.keys(semanticEvidence).length > 0) {",
            "      context.semantic_evidence = { ...(context.semantic_evidence as Record<string, unknown> | undefined), ...semanticEvidence };",
            "    }",
        ]
    )
    return "\n".join(lines)


def _typescript_semantic_validation_guards(model: dict[str, Any], op: str, error_codes: list[str]) -> str:
    semantics = model.get("operation_semantics") if isinstance(model.get("operation_semantics"), dict) else {}
    if not semantics or semantics.get("status") not in {"resolved", ""}:
        return ""
    lines: list[str] = []
    owner = normalized_semantic_owner(semantics.get("owner_service"))
    if owner and "forbidden" in error_codes:
        lines.extend(
            [
                f'    // operation-semantic-guard: only {owner} may authoritatively mutate this aggregate.',
                f'    if (context.expectedOwnerService !== undefined && context.expectedOwnerService !== "{owner}") {{',
                f'      throw this.map{op}Error("forbidden");',
                "    }",
            ]
        )
    return "\n".join(lines)


def _typescript_condition_field_from_transition(transition: str) -> str:
    match = re.search(r"\bwhen\s+(.+?)\s+is\s+accepted\b", transition, re.IGNORECASE)
    if not match:
        return "transitionConditionSatisfied"
    phrase = re.sub(r"\b(the|a|an)\b", " ", match.group(1), flags=re.IGNORECASE)
    words = re.findall(r"[A-Za-z0-9]+", phrase)
    if not words:
        return "transitionConditionSatisfied"
    first = words[0][:1].lower() + words[0][1:]
    return first + "".join(word[:1].upper() + word[1:] for word in words[1:]) + "Accepted"


def _source_backed_transition_pairs(transition: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9_-]*)\s*(?:->|→)\s*([A-Za-z][A-Za-z0-9_-]*)\b", transition):
        source = match.group(1).strip()
        target = match.group(2).strip()
        if source and target and (source, target) not in pairs:
            pairs.append((source, target))
    return pairs


def _typescript_behavior_value_state_guards(model: dict[str, Any], op: str, error_codes: list[str]) -> str:
    transition = str(model.get("state_transition") or "").strip()
    if not transition:
        return ""
    lines = [
        f"    // behavior-card-value-rule: {transition}",
        f"    // behavior-card-domain-invariant: {model.get('invariants') or 'business invariants'}",
    ]
    if "when" in transition.lower() and "invalid_request" in error_codes:
        condition_field = _typescript_condition_field_from_transition(transition)
        lines.extend(
            [
                f"    if (context.{condition_field} === false) {{",
                f'      throw this.map{op}Error("invalid_request");',
                "    }",
            ]
        )
    return "\n".join(lines)


def _typescript_state_transition_application(model: dict[str, Any], op: str, error_codes: list[str]) -> str:
    transition = str(model.get("state_transition") or "").strip()
    pairs = _source_backed_transition_pairs(transition)
    error_code = "invalid_request" if "invalid_request" in error_codes else (error_codes[0] if error_codes else "invalid_request")
    lines = [
        "    const currentStatus = current.status ?? current.state;",
        f'    const requestedStatus = this.resolve{op}ContextValue(context, "status") ?? this.resolve{op}ContextValue(context, "state");',
        "    const nextState: Record<string, unknown> = { ...current, trace_id: context.trace_id ?? context.traceId ?? current.trace_id ?? current.traceId };",
    ]
    if not pairs:
        lines.extend(
            [
                "    // lifecycle-review-bound: source-backed transition rules are missing; do not echo caller status as truth.",
                "    if (requestedStatus !== undefined && requestedStatus !== null && requestedStatus !== \"\") {",
                "      nextState.requested_status_review_bound = requestedStatus;",
                "    }",
                "    if (currentStatus !== undefined && currentStatus !== null && currentStatus !== \"\") {",
                "      nextState.status = currentStatus;",
                "    }",
                "    return nextState;",
            ]
        )
        return "\n".join(lines)

    allowed = ", ".join(_typescript_literal(f"{source}->{target}") for source, target in pairs)
    target_by_source = ", ".join(f"{_typescript_literal(source)}: {_typescript_literal(target)}" for source, target in pairs)
    lines.extend(
        [
            f"    const allowed{op}StateTransitions = new Set<string>([{allowed}]);",
            f"    const target{op}StateBySource: Record<string, string> = {{ {target_by_source} }};",
            "    const normalizedCurrentStatus = String(currentStatus ?? \"\");",
            "    const normalizedRequestedStatus = String(requestedStatus ?? \"\");",
            "    if (normalizedCurrentStatus && normalizedRequestedStatus) {",
            f"      if (!allowed{op}StateTransitions.has(`${{normalizedCurrentStatus}}->${{normalizedRequestedStatus}}`)) {{",
            f'        throw this.map{op}Error("{error_code}");',
            "      }",
            "      nextState.status = normalizedRequestedStatus;",
            "    } else if (normalizedCurrentStatus) {",
            f"      nextState.status = target{op}StateBySource[normalizedCurrentStatus] ?? normalizedCurrentStatus;",
            "    } else if (normalizedRequestedStatus) {",
            "      nextState.status = normalizedRequestedStatus;",
            "    }",
            f"    // invalid source-backed state transition is mapped through `{error_code}` when caller evidence contradicts the transition model.",
            "    return nextState;",
        ]
    )
    return "\n".join(lines)


def render_service_implementation_plan(model: dict[str, Any], *, module_class: str, operation_spec: dict[str, Any] | None = None) -> str:
    operation_id = str(model.get("operation_id", "UnknownOperation"))
    op = _upper_camel(operation_id)
    method = _lower_camel(operation_id)
    spec = operation_spec or {}
    spec_failure_cases = spec.get("failureCases", []) if isinstance(spec.get("failureCases", []), list) else []
    spec_error_codes = [str(item.get("error_code", "")).strip() for item in spec_failure_cases if isinstance(item, dict) and str(item.get("error_code", "")).strip()]
    error_codes = list(dict.fromkeys([*spec_error_codes, *(list(model.get("error_codes", [])) or ["invalid_request"])]))
    response_example = spec.get("responseExample", {}) if isinstance(spec.get("responseExample", {}), dict) else {}
    response_fields = ", ".join(str(key) for key in _response_example_data_shape(response_example).keys())
    example_request_id = str(response_example.get("request_id", "")).strip()
    semantics = model.get("operation_semantics") if isinstance(model.get("operation_semantics"), dict) else {}
    evidence_keys = [str(item).strip() for item in semantics.get("evidence_keys", [])] if isinstance(semantics.get("evidence_keys"), list) else []
    execution_mode = _operation_execution_mode(model, spec)
    response_projection = _typescript_response_projection(response_example, evidence_keys, operation_id)
    meta_projection = _typescript_meta_projection(response_example, operation_id)
    response_field_projection_method = _typescript_response_field_projection_method(op)
    return _render_behavior_template(
        "behavior-service-readonly.ts.template" if execution_mode in {"detail-read", "list-read"} else "behavior-service-command.ts.template",
        {
            "module_class": module_class,
            "response_fields": response_fields,
            "example_request_id": example_request_id,
            "method": method,
            "op": op,
            "operation_id": operation_id,
            "path_param_not_found_guard": _typescript_path_param_not_found_guard(spec, op, error_codes),
            "behavior_value_validation_guards": _typescript_behavior_value_validation_guards(model, op, error_codes),
            "request_field_validation_guards": _typescript_request_field_validation_guards(spec, op, error_codes),
            "evidence_key_absorption": _typescript_evidence_key_absorption(model, op),
            "semantic_validation_guards": _typescript_semantic_validation_guards(model, op, error_codes),
            "context_resolver_method": _typescript_context_resolver_method(op) + response_field_projection_method,
            "repository_result_merge_method": _typescript_repository_result_merge_method(op),
            "behavior_value_state_guards": _typescript_behavior_value_state_guards(model, op, error_codes),
            "state_transition_application": _typescript_state_transition_application(model, op, error_codes),
            "forced_failure_method": _typescript_forced_failure_method(op, error_codes),
            "response_projection": response_projection,
            "meta_projection": meta_projection,
            "pagination_projection": _typescript_pagination_projection(spec, response_example),
            "errors": _typescript_error_union(error_codes),
            "error_policy": _typescript_error_policy(error_codes),
            "semantic_owner": str(semantics.get("owner_service") or "agentic-required"),
            "semantic_aggregate": str(semantics.get("aggregate") or "agentic-required"),
            "semantic_event": ", ".join(semantics.get("trigger_events", [])) if isinstance(semantics.get("trigger_events"), list) else "review-bound",
            "semantic_evidence": ", ".join(semantics.get("evidence_keys", [])) if isinstance(semantics.get("evidence_keys"), list) else "review-bound",
        },
    )


def render_repository_invariant_plan(model: dict[str, Any], *, module_class: str) -> str:
    operation_id = str(model.get("operation_id", "UnknownOperation"))
    op = _upper_camel(operation_id)
    persistence = str(model.get("persistence_effects") or "durable_records")
    invariants = str(model.get("invariants") or "business invariants")
    transaction_rule = str(model.get("transaction_rule") or "transaction-aware write")
    audit_effect = str(model.get("audit_effect") or "audit/event side effect")
    return _render_behavior_template(
        "behavior-repository-readonly.ts.template"
        if _operation_execution_mode(model, {}) in {"detail-read", "list-read"}
        else "behavior-repository-command.ts.template",
        {
            "module_class": module_class,
            "op": op,
            "persistence": persistence,
            "invariants": invariants,
            "transaction_rule": transaction_rule,
            "audit_effect": audit_effect,
        },
    )


def scan_runtime_fallback_risk(source_code: str, model: dict[str, Any]) -> dict[str, Any]:
    operation_id = str(model.get("operation_id", ""))
    blockers: list[str] = []
    has_runtime_kernel = any(token in source_code for token in ("executeCommandOperation", "executeCreateOperation", "buildOperationPlan", "getOperationSpec"))
    has_behavior_steps = "behavior-card-step" in source_code or f"validate{_upper_camel(operation_id)}Context" in source_code
    if has_runtime_kernel and not has_behavior_steps:
        blockers.append("runtime_kernel_primary_path")
    return {"status": "fail" if blockers else "pass", "blockers": blockers}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract a P3 behavior card consumption model")
    parser.add_argument("card_path")
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    model = extract_behavior_card_model(Path(args.card_path).read_text(encoding="utf-8"))
    payload = json.dumps(model, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
