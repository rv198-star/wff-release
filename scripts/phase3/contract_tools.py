#!/usr/bin/env python3
"""
Helpers for turning a Phase-2 Engineering Spec Pack into Phase-3 contract assets.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from common.gwt_format_checker import first_table_with_headers, markdown_tables


API_HEADINGS = (
    "6.2 API Endpoint Draft",
    "6.2 API Endpoint 草案",
)
SCHEMA_HEADINGS = (
    "5.2 Schema Draft",
    "5.2 Schema 草案",
)

CONTRACT_MATCH_STOPWORDS = {
    "api",
    "and",
    "boundary",
    "bound",
    "carry",
    "carries",
    "contract",
    "contracts",
    "evidence",
    "explicit",
    "for",
    "geo",
    "handoff",
    "implementation",
    "input",
    "intake",
    "output",
    "preserve",
    "preserved",
    "replay",
    "remains",
    "review",
    "stable",
    "stage",
    "stays",
    "the",
    "trace",
    "v1",
    "v2",
    "visible",
    "with",
}

ENDPOINT_ACTION_VERBS = {
    "archive",
    "attach",
    "authorize",
    "complete",
    "create",
    "generate",
    "get",
    "list",
    "record",
    "refresh",
    "start",
    "update",
}
POSTGRES_IDENTIFIER_MAX_LEN = 63
POSTGRES_UNSAFE_IDENTIFIER_WORDS = {
    "alter",
    "case",
    "constraint",
    "create",
    "delete",
    "drop",
    "else",
    "end",
    "foreign",
    "from",
    "group",
    "having",
    "index",
    "insert",
    "join",
    "limit",
    "offset",
    "order",
    "primary",
    "references",
    "select",
    "table",
    "then",
    "union",
    "update",
    "user",
    "when",
}


def strip_ticks(value: str) -> str:
    text = value.strip()
    if text.startswith("`") and text.endswith("`") and len(text) >= 2:
        return text[1:-1].strip()
    return text.strip("`").strip()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _safe_db_identifier(value: str) -> str:
    normalized = _snake_case_token(value)
    if normalized in POSTGRES_UNSAFE_IDENTIFIER_WORDS:
        normalized = f"{normalized}_record"
    if len(normalized) <= POSTGRES_IDENTIFIER_MAX_LEN:
        return normalized
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
    head_len = POSTGRES_IDENTIFIER_MAX_LEN - len(digest) - 1
    head = normalized[:head_len].rstrip("_")
    if not head:
        head = normalized[:head_len]
    return f"{head}_{digest}"


def _sql_identifier(value: str) -> str:
    identifier = _safe_db_identifier(value)
    if re.fullmatch(r"[a-z_][a-z0-9_]*", identifier) and identifier not in POSTGRES_UNSAFE_IDENTIFIER_WORDS:
        return identifier
    return f'"{identifier.replace(chr(34), chr(34) + chr(34))}"'


def parse_list_cell(raw: str) -> list[str]:
    cleaned = strip_ticks(raw)
    if not cleaned or cleaned.lower() in {"none", "n/a"}:
        return []
    return [strip_ticks(part) for part in re.split(r"\s*,\s*", cleaned) if strip_ticks(part)]


def parse_reference_cell(raw: str) -> list[str]:
    cleaned = strip_ticks(raw)
    if not cleaned or cleaned.lower() in {"none", "n/a"}:
        return []
    return [strip_ticks(part) for part in re.split(r"\s*(?:,|/|;|\band\b)\s*", cleaned, flags=re.IGNORECASE) if strip_ticks(part)]


def camel_and_word_tokens(text: str) -> set[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return {
        token.lower()
        for token in re.split(r"[^A-Za-z0-9]+", expanded)
        if token and token.lower() not in {"v1", "v2", "api"}
    }


def contract_match_tokens(text: str) -> set[str]:
    return {
        token
        for token in camel_and_word_tokens(text)
        if token not in CONTRACT_MATCH_STOPWORDS
    }


def endpoint_action_token(operation_id: str) -> str:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", operation_id)
    parts = [part.lower() for part in re.split(r"[^A-Za-z0-9]+", expanded) if part]
    if parts and parts[0] in ENDPOINT_ACTION_VERBS:
        return parts[0]
    return ""


def explicit_operation_mentions(text: str) -> list[str]:
    mentions: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"\b([A-Z][A-Za-z0-9]*)\b", text):
        candidate = match.group(1).strip()
        if not candidate:
            continue
        action = endpoint_action_token(candidate)
        if not action or candidate.lower() == action:
            continue
        if candidate not in seen:
            seen.add(candidate)
            mentions.append(candidate)
    return mentions


def extract_heading_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start: int | None = None
    level = 0
    for idx, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if not match:
            continue
        if match.group(2).strip() == heading:
            start = idx + 1
            level = len(match.group(1))
            break
    if start is None:
        raise ValueError(f"heading not found: {heading}")

    end = len(lines)
    for idx in range(start, len(lines)):
        match = re.match(r"^(#{1,6})\s+(.*)$", lines[idx].strip())
        if match and len(match.group(1)) <= level:
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def extract_heading_section_any(text: str, headings: tuple[str, ...]) -> str:
    last_error: ValueError | None = None
    for heading in headings:
        try:
            return extract_heading_section(text, heading)
        except ValueError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ValueError("heading not found")


def extract_nested_bullet_items(text: str, label: str) -> list[str]:
    lines = text.splitlines()
    anchor_index: int | None = None
    anchor_indent = 0
    pattern = re.compile(rf"^(\s*)-\s+{re.escape(label)}:\s*$")
    for idx, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            anchor_index = idx
            anchor_indent = len(match.group(1))
            break
    if anchor_index is None:
        return []

    items: list[str] = []
    for idx in range(anchor_index + 1, len(lines)):
        line = lines[idx]
        stripped = line.strip()
        if not stripped:
            continue
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent <= anchor_indent:
            break
        bullet_match = re.match(r"^\s*-\s+(.*)$", line)
        if bullet_match:
            items.append(strip_ticks(bullet_match.group(1)))
    return items


def extract_inline_bullet_value(text: str, label: str) -> str:
    pattern = re.compile(rf"^\s*-\s+{re.escape(label)}:\s*(.+?)\s*$", flags=re.MULTILINE)
    match = pattern.search(text)
    return strip_ticks(match.group(1)) if match else ""


def parse_json_example(raw: str) -> object:
    normalized = strip_ticks(raw)
    if not normalized or normalized.lower() in {"none", "n/a"}:
        return {}
    return json.loads(normalized)


def infer_json_schema(value: object) -> dict[str, object]:
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        item_schema = infer_json_schema(value[0]) if value else {}
        return {"type": "array", "items": item_schema}
    if isinstance(value, dict):
        properties = {key: infer_json_schema(subvalue) for key, subvalue in value.items()}
        required = sorted(key for key in value.keys())
        schema: dict[str, object] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        return schema
    if value is None:
        return {"type": "null"}
    return {}


ENUM_LIKE_CONTRACT_FIELDS = {
    "status",
    "state",
    "severity",
    "priority",
    "decisionPosture",
    "uncertaintyLevel",
    "riskLevel",
}


def _is_enum_like_contract_field(field_name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", field_name.lower())
    return any(re.sub(r"[^a-z0-9]+", "", item.lower()) == normalized for item in ENUM_LIKE_CONTRACT_FIELDS)


def infer_contract_json_schema(value: object, field_name: str = "") -> dict[str, object]:
    schema = infer_json_schema(value)
    if isinstance(value, str) and field_name and _is_enum_like_contract_field(field_name):
        schema["enum"] = [value]
        schema["x-enum-source"] = "example-literal-contract"
    elif isinstance(value, list):
        schema["items"] = infer_contract_json_schema(value[0], field_name) if value else {}
    elif isinstance(value, dict):
        schema["properties"] = {key: infer_contract_json_schema(subvalue, str(key)) for key, subvalue in value.items()}
    return schema


def add_pagination_contract(schema: dict[str, object], pagination_rule: object) -> dict[str, object]:
    if str(pagination_rule or "").strip().lower() in {"", "none", "not_applicable", "n/a"}:
        return schema
    if schema.get("type") != "object":
        return schema
    properties = schema.setdefault("properties", {})
    if not isinstance(properties, dict):
        return schema
    data_schema = properties.get("data")
    if not isinstance(data_schema, dict):
        return schema
    properties.setdefault(
        "pagination",
        {
            "type": "object",
            "properties": {
                "nextCursor": {"type": ["string", "null"]},
                "pageSize": {"type": "integer"},
                "hasMore": {"type": "boolean"},
            },
            "required": ["hasMore", "nextCursor", "pageSize"],
            "additionalProperties": False,
            "x-pagination-rule": str(pagination_rule),
        },
    )
    required = list(schema.get("required", [])) if isinstance(schema.get("required"), list) else []
    if "pagination" not in required:
        required.append("pagination")
    schema["required"] = sorted(required)
    return schema


def error_envelope_schema(*, kind: str, code: str, retryability: str) -> dict[str, object]:
    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "error_kind": {"type": "string", "enum": [kind] if kind else []},
            "error_code": {"type": "string", "enum": [code] if code else []},
            "retryability": {"type": "string", "enum": [retryability] if retryability else []},
        },
        "required": ["error_kind", "error_code", "retryability"],
        "additionalProperties": False,
        "x-schema-source": "standard-error-envelope",
    }
    for property_schema in schema["properties"].values():
        if isinstance(property_schema, dict) and property_schema.get("enum") == []:
            property_schema.pop("enum", None)
    return schema


def parse_failure_codes(raw: str) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    cleaned = strip_ticks(raw).replace("&#124;", "|")
    if not cleaned:
        return failures
    active_error_kind = ""
    for part in cleaned.split(";"):
        chunk = part.strip()
        if not chunk:
            continue
        if chunk.startswith("error_type split:"):
            continue
        left, arrow, right = chunk.partition("->")
        retryability = right.strip() if arrow else ""
        left_tokens = left.strip()
        grouped_kind = re.match(r"^(business_error|system_error)\s*:\s*(.+)$", left_tokens)
        if grouped_kind:
            active_error_kind = grouped_kind.group(1)
            left_tokens = grouped_kind.group(2).strip()
        tokens = left_tokens.split()
        if not tokens or not re.match(r"^\d{3}$", tokens[0]):
            raise ValueError(f"unparseable failure code chunk: {chunk}")
        if len(tokens) >= 2 and re.match(r"^(business_error|system_error)(?:\.[A-Za-z0-9_.-]+)?$", tokens[1]):
            error_kind = tokens[1]
            error_code = " ".join(tokens[2:]).strip()
        elif active_error_kind:
            error_kind = active_error_kind
            error_code = " ".join(tokens[1:]).strip()
        elif len(tokens) >= 2:
            error_kind = "business_error"
            error_code = " ".join(tokens[1:]).strip()
        else:
            raise ValueError(f"unparseable failure code chunk: {chunk}")
        payload = {
            "status": tokens[0],
            "error_kind": error_kind,
            "error_code": error_code,
            "retryability": retryability,
        }
        if not payload["error_code"] and "." in payload["error_kind"]:
            kind, code = payload["error_kind"].split(".", 1)
            payload["error_kind"] = kind
            payload["error_code"] = code
        failures.append(payload)
    return failures


def parse_api_endpoint_rows(text: str) -> list[dict[str, object]]:
    section = extract_heading_section_any(text, API_HEADINGS)
    table = first_table_with_headers(
        section,
        {
            "endpoint_name",
            "method",
            "path",
            "purpose",
            "request_body_example",
            "response_body_example",
            "failure_codes",
        },
        id_headers=("endpoint_name",),
    )
    if table is None:
        raise ValueError("api_endpoint_draft table not found")

    rows: list[dict[str, object]] = []
    for row in table["rows"]:
        record = {key: strip_ticks(str(value)) for key, value in row.items()}
        request_example = parse_json_example(str(row.get("request_body_example", "")))
        response_example = parse_json_example(str(row.get("response_body_example", "")))
        request_example, response_example = _merge_seed_example_fields(
            str(record.get("path", "")),
            request_example,
            response_example,
        )
        record["request_body_example"] = request_example
        record["response_body_example"] = response_example
        record["failure_codes"] = parse_failure_codes(str(row.get("failure_codes", "")))
        rows.append(record)
    return rows


def _extract_openapi_content_example(payload: Any) -> object:
    if not isinstance(payload, dict):
        return {}
    content = payload.get("content", {})
    if not isinstance(content, dict):
        return {}
    app_json = content.get("application/json", {})
    if not isinstance(app_json, dict):
        return {}
    return json.loads(json.dumps(app_json.get("example", {}), ensure_ascii=False))


def endpoint_rows_from_openapi_spec(payload: dict[str, Any]) -> list[dict[str, object]]:
    paths = payload.get("paths", {})
    if not isinstance(paths, dict):
        return []
    rows: list[dict[str, object]] = []
    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            method_upper = str(method).strip().upper()
            if method_upper not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            if not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId", "")).strip()
            if not operation_id:
                continue
            request_example = _extract_openapi_content_example(operation.get("requestBody", {}))
            if not isinstance(request_example, dict):
                request_example = {}
            parameters = operation.get("parameters", [])
            if isinstance(parameters, list):
                for parameter in parameters:
                    if not isinstance(parameter, dict):
                        continue
                    name = str(parameter.get("name", "")).strip()
                    if not name or name in request_example:
                        continue
                    example = parameter.get("example")
                    schema = parameter.get("schema", {})
                    if example is None and isinstance(schema, dict):
                        example = schema.get("example")
                    request_example[name] = example

            response_example: object = {}
            failure_codes: list[dict[str, object]] = []
            responses = operation.get("responses", {})
            if isinstance(responses, dict):
                for status, response in responses.items():
                    status_text = str(status).strip()
                    if not re.match(r"^\d{3}$", status_text):
                        continue
                    example = _extract_openapi_content_example(response)
                    if status_text.startswith("2"):
                        if not response_example and isinstance(example, (dict, list)):
                            response_example = example
                        continue
                    if not isinstance(example, dict):
                        continue
                    error_code = str(example.get("error_code", "")).strip()
                    if not error_code:
                        continue
                    failure_codes.append(
                        {
                            "status": status_text,
                            "error_kind": str(example.get("error_kind", "")).strip() or "business_error",
                            "error_code": error_code,
                            "retryability": str(example.get("retryability", "")).strip(),
                        }
                    )

            request_example, response_example = _merge_seed_example_fields(path, request_example, response_example)
            rows.append(
                {
                    "endpoint_name": operation_id,
                    "method": method_upper,
                    "path": path,
                    "purpose": str(operation.get("summary", "")).strip() or operation_id,
                    "request_body_example": request_example,
                    "response_body_example": response_example,
                    "failure_codes": failure_codes,
                }
            )
    return rows


def parse_contract_trace_rows(text: str) -> list[dict[str, object]]:
    table = first_table_with_headers(
        text,
        {"trace_id", "trace_subject", "subject_type", "upstream_trace_ids", "verification_hook"},
        id_headers=("trace_id",),
    )
    if table is None:
        raise ValueError("contract_trace_registry table not found")
    rows: list[dict[str, object]] = []
    for row in table["rows"]:
        normalized = {key: strip_ticks(str(value)) for key, value in row.items()}
        normalized["upstream_trace_ids"] = parse_list_cell(str(row.get("upstream_trace_ids", "")))
        rows.append(normalized)
    return rows


def parse_scenario_rows(text: str) -> list[dict[str, object]]:
    table = first_table_with_headers(
        text,
        {"scenario", "upstream_trace_ids", "acceptance_criteria", "measurement_hook", "given", "when", "then"},
        id_headers=("scenario",),
    )
    if table is None:
        raise ValueError("scenario_coverage_matrix table not found")
    rows: list[dict[str, object]] = []
    for row in table["rows"]:
        normalized = {key: strip_ticks(str(value)) for key, value in row.items()}
        normalized["upstream_trace_ids"] = parse_list_cell(str(row.get("upstream_trace_ids", "")))
        rows.append(normalized)
    return rows


def parse_replay_rows(text: str) -> list[dict[str, object]]:
    table = first_table_with_headers(
        text,
        {
            "replay_id",
            "scenario_or_contract",
            "upstream_trace_ids",
            "expected_outcome",
            "observed_outcome",
            "verdict",
            "linked_rbi_or_wp",
        },
        id_headers=("replay_id",),
    )
    if table is None:
        raise ValueError("verification_replay_evidence table not found")
    rows: list[dict[str, object]] = []
    for row in table["rows"]:
        normalized = {key: strip_ticks(str(value)) for key, value in row.items()}
        normalized["upstream_trace_ids"] = parse_list_cell(str(row.get("upstream_trace_ids", "")))
        normalized["linked_rbi_or_wp"] = parse_list_cell(str(row.get("linked_rbi_or_wp", "")))
        rows.append(normalized)
    return rows


def parse_work_package_rows(text: str) -> list[dict[str, object]]:
    table = first_table_with_headers(
        text,
        {"wp_id", "scope", "acceptance_criteria", "estimated_effort", "depends_on", "linked_rbi_or_slice"},
        id_headers=("wp_id",),
    )
    if table is None:
        raise ValueError("work_package_registry table not found")
    rows: list[dict[str, object]] = []
    for row in table["rows"]:
        normalized = {key: strip_ticks(str(value)) for key, value in row.items()}
        normalized["depends_on"] = parse_reference_cell(str(row.get("depends_on", "")))
        normalized["linked_rbi_or_slice"] = parse_reference_cell(str(row.get("linked_rbi_or_slice", "")))
        rows.append(normalized)
    return rows


def parse_implementation_start_order_rows(text: str) -> list[dict[str, object]]:
    table = first_table_with_headers(
        text,
        {"wp_id", "depends_on", "implementation_scope", "acceptance_criteria", "linked_rbi_or_slice"},
        id_headers=("wp_id",),
    )
    if table is None:
        raise ValueError("implementation start order table not found")
    rows: list[dict[str, object]] = []
    for row in table["rows"]:
        normalized = {key: strip_ticks(str(value)) for key, value in row.items()}
        normalized["depends_on"] = parse_reference_cell(str(row.get("depends_on", "")))
        normalized["linked_rbi_or_slice"] = parse_reference_cell(str(row.get("linked_rbi_or_slice", "")))
        rows.append(normalized)
    return rows


def parse_technology_selection_rows(text: str) -> list[dict[str, object]]:
    table = first_table_with_headers(
        text,
        {"candidate_name", "final_decision", "rejection_reason"},
        id_headers=("candidate_name",),
    )
    if table is None:
        raise ValueError("technology selection evaluation matrix not found")
    return [{key: strip_ticks(str(value)) for key, value in row.items()} for row in table["rows"]]


def parse_auth_vendor_rows(text: str) -> list[dict[str, object]]:
    table = first_table_with_headers(
        text,
        {"candidate", "fit_for_case", "constraints_or_risk", "decision_status"},
        id_headers=("candidate",),
    )
    if table is not None:
        return [{key: strip_ticks(str(value)) for key, value in row.items()} for row in table["rows"]]

    try:
        section = extract_heading_section_any(
            text,
            (
                "10.9 Identity, Auth Vendor, and Key Lifecycle",
                "10.9 身份、认证供应商与密钥生命周期",
                "10.10 Identity, Auth Vendor, and Key Lifecycle",
                "10.10 身份、认证供应商与密钥生命周期",
            ),
        )
    except ValueError as exc:
        raise ValueError("auth vendor slot table not found") from exc

    recommended = extract_nested_bullet_items(section, "recommended_approach")
    auth_vendor_slot = extract_inline_bullet_value(section, "auth_vendor_slot")
    key_posture = extract_inline_bullet_value(section, "key_posture")

    if not (recommended or auth_vendor_slot or key_posture):
        raise ValueError("auth vendor slot table not found")

    return [
        {
            "candidate": "real session-or-token auth boundary",
            "fit_for_case": auth_vendor_slot
            or "keeps tenant policy and role claims enforceable without freezing an external provider too early",
            "constraints_or_risk": key_posture
            or "provider/runtime contract remains replaceable until Phase-2 explicitly freezes an external identity dependency",
            "decision_status": "provisional-front-runner",
        },
        {
            "candidate": "managed OIDC/OAuth2 provider",
            "fit_for_case": recommended[0]
            if recommended
            else "activate once external federation, SSO, or named IdP integration becomes delivery-critical",
            "constraints_or_risk": "requires explicit provider contract, callback/session posture, secret rotation plan, and runtime validation",
            "decision_status": "deferred-alternative",
        },
    ]


def auth_vendor_contract_source(text: str) -> str:
    table = first_table_with_headers(
        text,
        {"candidate", "fit_for_case", "constraints_or_risk", "decision_status"},
        id_headers=("candidate",),
    )
    return "explicit-table" if table is not None else "fallback-derived"


def scenario_identifier(value: str) -> tuple[str, str]:
    cleaned = strip_ticks(value)
    match = re.match(r"^(SCN-[A-Za-z0-9_-]+)\s*(.*)$", cleaned, flags=re.IGNORECASE)
    if not match:
        return f"SCN-{slugify(cleaned).upper()}", ""
    return match.group(1).upper(), match.group(2).strip()


def scenario_test_filename(scenario_name: str) -> str:
    scenario_id, label = scenario_identifier(scenario_name)
    tail = slugify(label) or slugify(scenario_id)
    if tail == slugify(scenario_id):
        return f"{slugify(scenario_id)}.scenario.test.ts"
    return f"{scenario_id.lower()}-{tail}.scenario.test.ts"


def replay_test_filename(replay_id: str, scenario_or_contract: str) -> str:
    return f"{replay_id.lower()}-{slugify(scenario_or_contract)}.replay.test.ts"


def build_contract_trace_matches(
    contract_rows: list[dict[str, object]],
    endpoint_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    endpoint_candidates = []
    endpoint_names = {str(endpoint.get("endpoint_name", "")).strip() for endpoint in endpoint_rows}
    for idx, endpoint in enumerate(endpoint_rows):
        operation_id = str(endpoint["endpoint_name"])
        aliases = [str(item).strip() for item in endpoint.get("aliases", []) if str(item).strip()]
        path = str(endpoint["path"])
        purpose = str(endpoint.get("purpose", ""))
        action_token = endpoint_action_token(operation_id)
        tokens = contract_match_tokens(operation_id) | contract_match_tokens(path) | contract_match_tokens(purpose)
        for alias in aliases:
            tokens.update(contract_match_tokens(alias))
        endpoint_candidates.append(
            {
                "order": idx,
                "endpoint_name": operation_id,
                "path": path,
                "purpose": purpose,
                "compact_operation": re.sub(r"[^a-z0-9]+", "", operation_id.lower()),
                "compact_aliases": [re.sub(r"[^a-z0-9]+", "", alias.lower()) for alias in aliases if alias],
                "action_token": action_token,
                "anchor_tokens": {token for token in tokens if token != action_token},
                "tokens": tokens,
            }
        )

    rows: list[dict[str, object]] = []
    for idx, contract_row in enumerate(contract_rows):
        haystack = " ".join(
            [
                str(contract_row.get("trace_subject", "")),
                str(contract_row.get("semantic_bridge_note", "")),
                str(contract_row.get("verification_hook", "")),
                str(contract_row.get("owning_module", "")),
            ]
        )
        compact_haystack = re.sub(r"[^a-z0-9]+", "", haystack.lower())
        haystack_tokens = contract_match_tokens(haystack)
        explicit_matches = [
            str(candidate["endpoint_name"])
            for candidate in endpoint_candidates
            if (
                (candidate["compact_operation"] and candidate["compact_operation"] in compact_haystack)
                or any(alias and alias in compact_haystack for alias in candidate.get("compact_aliases", []))
            )
        ]
        explicit_missing_mentions = [
            operation_id
            for operation_id in explicit_operation_mentions(str(contract_row.get("verification_hook", "")))
            if operation_id not in endpoint_names
        ]
        matched_endpoints: list[str] = sorted(set(explicit_matches))
        if not matched_endpoints and not explicit_missing_mentions:
            scored_candidates: list[tuple[int, int, int, str]] = []
            for candidate in endpoint_candidates:
                anchor_overlap = haystack_tokens & set(candidate["anchor_tokens"])
                overlap = haystack_tokens & set(candidate["tokens"])
                if not overlap and not anchor_overlap:
                    continue
                score = len(anchor_overlap) * 3 + len(overlap)
                if candidate["action_token"] and str(candidate["action_token"]) in haystack_tokens:
                    score += 4
                order_proximity = -abs(int(candidate["order"]) - idx)
                scored_candidates.append(
                    (
                        score,
                        len(anchor_overlap),
                        order_proximity,
                        str(candidate["endpoint_name"]),
                    )
                )
            scored_candidates.sort(reverse=True)
            if scored_candidates:
                best_score, best_anchor_overlap, _, best_endpoint = scored_candidates[0]
                if best_score >= 4 and best_anchor_overlap >= 1:
                    matched_endpoints = [best_endpoint]
                elif len(scored_candidates) == 1 and best_score >= 3:
                    matched_endpoints = [best_endpoint]
            if not matched_endpoints and len(contract_rows) == len(endpoint_candidates) and idx < len(endpoint_candidates):
                matched_endpoints = [str(endpoint_candidates[idx]["endpoint_name"])]
        rows.append(
            {
                **contract_row,
                "matched_endpoints": sorted(set(matched_endpoints)),
            }
        )
    return rows


def split_specs(raw: str) -> list[str]:
    cleaned = strip_ticks(raw)
    if not cleaned or cleaned.lower() == "none":
        return []
    return [strip_ticks(part) for part in cleaned.split(";") if strip_ticks(part)]


def normalize_index_spec(raw: str) -> str:
    normalized = re.sub(r"\s*\+\s*", ", ", strip_ticks(raw))
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for part in parts:
        lowered = part.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(part)
    return ", ".join(deduped)


def _normalize_boolean_flag(value: str) -> bool:
    return strip_ticks(value).strip().lower() in {"no", "false", "0"}


def _snake_case_token(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", normalized)
    return normalized.strip("_").lower()


def _camel_case_token(value: str) -> str:
    parts = [part for part in _snake_case_token(value).split("_") if part]
    if not parts:
        return ""
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def _plural_path_candidates(table_name: str) -> set[str]:
    dashed = table_name.replace("_", "-")
    if dashed.endswith("y"):
        return {f"{dashed[:-1]}ies", f"{dashed}s"}
    if dashed.endswith("s"):
        return {f"{dashed}es", dashed}
    return {f"{dashed}s"}


def _unwrap_contract_example(value: object) -> list[dict[str, object]]:
    if isinstance(value, dict):
        data = value.get("data")
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _infer_iso_temporal_literal_type(sample_value: str) -> str | None:
    value = sample_value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return "date"
    if re.fullmatch(
        r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?",
        value,
    ):
        return "timestamptz"
    return None


def _infer_sql_type(field_name: str, sample_value: object) -> str:
    normalized = _snake_case_token(field_name)
    if isinstance(sample_value, bool):
        return "boolean"
    if isinstance(sample_value, int) and not isinstance(sample_value, bool):
        return "int4"
    if isinstance(sample_value, float):
        return "numeric(12,2)"
    if isinstance(sample_value, str):
        literal_type = _infer_iso_temporal_literal_type(sample_value)
        if literal_type is not None:
            return literal_type
        if normalized.endswith("_at") or normalized in {"scheduled_at", "visit_date", "paid_at", "issued_at", "reviewed_at", "changed_at", "prescribed_at", "observed_at"}:
            return "timestamptz"
        if normalized.endswith("_date") or normalized == "birth_date":
            return "date"
        if normalized.endswith("_id"):
            return "uuid"
        if "amount" in normalized:
            return "numeric(12,2)"
        if normalized in {"phone", "payment_method", "species", "review_outcome", "action_name", "entity_type", "subject_type", "module"}:
            return "varchar(64)"
        if normalized.endswith("_number"):
            return "varchar(64)"
        if normalized.endswith("_name") or normalized in {"email", "dosage", "frequency"}:
            return "varchar(128)"
    if isinstance(sample_value, (dict, list)):
        return "jsonb"
    return "text"


def _business_seed_fields(table_name: str) -> list[dict[str, str]]:
    seeds: dict[str, list[dict[str, str]]] = {
        "owner": [
            {"field_name": "owner_name", "data_type": "varchar(128)", "nullable": "yes", "constraints": ""},
            {"field_name": "phone", "data_type": "varchar(32)", "nullable": "yes", "constraints": ""},
            {"field_name": "email", "data_type": "varchar(128)", "nullable": "yes", "constraints": ""},
        ],
        "pet": [
            {"field_name": "owner_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk owner.owner_id"},
            {"field_name": "pet_name", "data_type": "varchar(128)", "nullable": "yes", "constraints": ""},
            {"field_name": "species", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
            {"field_name": "birth_date", "data_type": "date", "nullable": "yes", "constraints": ""},
        ],
        "appointment": [
            {"field_name": "pet_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk pet.pet_id"},
            {"field_name": "owner_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk owner.owner_id"},
            {"field_name": "vet_name", "data_type": "varchar(128)", "nullable": "yes", "constraints": ""},
            {"field_name": "appointment_date", "data_type": "timestamptz", "nullable": "yes", "constraints": ""},
            {"field_name": "appointment_type", "data_type": "varchar(32)", "nullable": "yes", "constraints": ""},
            {"field_name": "reason", "data_type": "text", "nullable": "yes", "constraints": ""},
        ],
        "visit_record": [
            {"field_name": "owner_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk owner.owner_id"},
            {"field_name": "pet_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk pet.pet_id"},
            {"field_name": "vet_name", "data_type": "varchar(128)", "nullable": "yes", "constraints": ""},
            {"field_name": "visit_date", "data_type": "timestamptz", "nullable": "yes", "constraints": ""},
            {"field_name": "chief_complaint", "data_type": "text", "nullable": "yes", "constraints": ""},
            {"field_name": "diagnosis", "data_type": "text", "nullable": "yes", "constraints": ""},
            {"field_name": "treatment_plan", "data_type": "text", "nullable": "yes", "constraints": ""},
        ],
        "prescription": [
            {"field_name": "visit_record_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk visit_record.visit_record_id"},
            {"field_name": "prescribed_at", "data_type": "timestamptz", "nullable": "yes", "constraints": ""},
            {"field_name": "diagnosis_summary", "data_type": "text", "nullable": "yes", "constraints": ""},
            {"field_name": "notes", "data_type": "text", "nullable": "yes", "constraints": ""},
        ],
        "drug": [
            {"field_name": "drug_name", "data_type": "varchar(128)", "nullable": "yes", "constraints": ""},
            {"field_name": "dosage_form", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
            {"field_name": "unit", "data_type": "varchar(32)", "nullable": "yes", "constraints": ""},
            {"field_name": "stock_qty", "data_type": "int4", "nullable": "yes", "constraints": "check >= 0"},
            {"field_name": "unit_price", "data_type": "numeric(10,2)", "nullable": "yes", "constraints": "check >= 0"},
        ],
        "invoice": [
            {"field_name": "visit_record_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk visit_record.visit_record_id"},
            {"field_name": "invoice_number", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
            {"field_name": "total_amount", "data_type": "numeric(12,2)", "nullable": "yes", "constraints": "positive"},
            {"field_name": "issued_at", "data_type": "timestamptz", "nullable": "yes", "constraints": ""},
        ],
        "payment": [
            {"field_name": "invoice_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk invoice.invoice_id"},
            {"field_name": "payment_method", "data_type": "varchar(32)", "nullable": "yes", "constraints": ""},
            {"field_name": "amount", "data_type": "numeric(12,2)", "nullable": "yes", "constraints": "positive"},
            {"field_name": "paid_at", "data_type": "timestamptz", "nullable": "yes", "constraints": ""},
            {"field_name": "reference_no", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
        ],
        "workflow_audit_record": [
            {"field_name": "subject_id", "data_type": "uuid", "nullable": "yes", "constraints": ""},
            {"field_name": "subject_type", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
            {"field_name": "action", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
            {"field_name": "actor", "data_type": "varchar(128)", "nullable": "yes", "constraints": ""},
            {"field_name": "performed_at", "data_type": "timestamptz", "nullable": "yes", "constraints": ""},
            {"field_name": "detail", "data_type": "text", "nullable": "yes", "constraints": ""},
        ],
        "workflow_review_summary": [
            {"field_name": "subject_id", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
            {"field_name": "reviewer", "data_type": "varchar(128)", "nullable": "yes", "constraints": ""},
            {"field_name": "review_date", "data_type": "timestamptz", "nullable": "yes", "constraints": ""},
            {"field_name": "outcome", "data_type": "varchar(32)", "nullable": "yes", "constraints": ""},
            {"field_name": "summary", "data_type": "text", "nullable": "yes", "constraints": ""},
        ],
        "visit_record_revision": [
            {"field_name": "visit_record_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk visit_record.visit_record_id"},
            {"field_name": "visit_record_revision_parent_id", "data_type": "uuid", "nullable": "no", "constraints": "fk visit_record.visit_record_id"},
            {"field_name": "revision_no", "data_type": "int4", "nullable": "no", "constraints": "positive"},
            {"field_name": "change_summary", "data_type": "text", "nullable": "yes", "constraints": ""},
            {"field_name": "changed_at", "data_type": "timestamptz", "nullable": "yes", "constraints": "default now()"},
            {"field_name": "changed_by", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
        ],
        "appointment_revision": [
            {"field_name": "appointment_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk appointment.appointment_id"},
            {"field_name": "appointment_revision_parent_id", "data_type": "uuid", "nullable": "no", "constraints": "fk appointment.appointment_id"},
            {"field_name": "revision_no", "data_type": "int4", "nullable": "no", "constraints": "positive"},
            {"field_name": "change_summary", "data_type": "text", "nullable": "yes", "constraints": ""},
            {"field_name": "changed_at", "data_type": "timestamptz", "nullable": "yes", "constraints": "default now()"},
            {"field_name": "changed_by", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
        ],
        "drug_revision": [
            {"field_name": "drug_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk drug.drug_id"},
            {"field_name": "drug_revision_parent_id", "data_type": "uuid", "nullable": "no", "constraints": "fk drug.drug_id"},
            {"field_name": "revision_no", "data_type": "int4", "nullable": "no", "constraints": "positive"},
            {"field_name": "change_summary", "data_type": "text", "nullable": "yes", "constraints": ""},
            {"field_name": "changed_at", "data_type": "timestamptz", "nullable": "yes", "constraints": "default now()"},
            {"field_name": "changed_by", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
        ],
        "payment_revision": [
            {"field_name": "payment_id", "data_type": "uuid", "nullable": "yes", "constraints": "fk payment.payment_id"},
            {"field_name": "payment_revision_parent_id", "data_type": "uuid", "nullable": "no", "constraints": "fk payment.payment_id"},
            {"field_name": "revision_no", "data_type": "int4", "nullable": "no", "constraints": "positive"},
            {"field_name": "change_summary", "data_type": "text", "nullable": "yes", "constraints": ""},
            {"field_name": "changed_at", "data_type": "timestamptz", "nullable": "yes", "constraints": "default now()"},
            {"field_name": "changed_by", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
        ],
    }
    if table_name in seeds:
        return [
            {
                **dict(field),
                "field_name": _safe_db_identifier(str(field["field_name"])),
            }
            for field in seeds[table_name]
        ]
    if table_name.endswith("_revision"):
        parent_name = table_name.removesuffix("_revision")
        parent_pk = _safe_db_identifier(f"{parent_name}_id")
        return [
            {"field_name": parent_pk, "data_type": "uuid", "nullable": "yes", "constraints": f"fk {parent_name}.{parent_pk}"},
            {
                "field_name": _safe_db_identifier(f"{table_name}_parent_id"),
                "data_type": "uuid",
                "nullable": "no",
                "constraints": f"fk {parent_name}.{parent_pk}",
            },
            {"field_name": "revision_no", "data_type": "int4", "nullable": "no", "constraints": "positive"},
            {"field_name": "change_summary", "data_type": "text", "nullable": "yes", "constraints": ""},
            {"field_name": "changed_at", "data_type": "timestamptz", "nullable": "yes", "constraints": "default now()"},
            {"field_name": "changed_by", "data_type": "varchar(64)", "nullable": "yes", "constraints": ""},
        ]
    return []


def _referenced_constraint_fields(summary: dict[str, str]) -> list[str]:
    seen: set[str] = set()
    fields: list[str] = []

    def add(name: str) -> None:
        normalized = _safe_db_identifier(name)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        fields.append(normalized)

    spec_sources = [
        *split_specs(summary.get("unique_constraints", "")),
        *split_specs(summary.get("composite_indexes", "")),
    ]
    reserved = {"and", "or", "not", "true", "false", "null", "is", "in"}
    for raw_spec in spec_sources:
        normalized_spec = normalize_index_spec(raw_spec)
        if not normalized_spec or normalized_spec.lower() == "none":
            continue
        parts = re.split(r"\bwhere\b", normalized_spec, maxsplit=1, flags=re.IGNORECASE)
        column_part = parts[0]
        predicate_part = parts[1] if len(parts) > 1 else ""
        for part in column_part.split(","):
            add(re.sub(r"\s+(asc|desc)$", "", part, flags=re.IGNORECASE))
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", predicate_part):
            if token.lower() in reserved:
                continue
            add(token)
    return fields


def _constraint_field_fallback(table_name: str, field_name: str) -> dict[str, str]:
    field_name = _safe_db_identifier(field_name)
    base_name = table_name.removesuffix("_revision") if table_name.endswith("_revision") else table_name
    base_table_name = _safe_db_identifier(base_name)
    base_pk = _safe_db_identifier(f"{base_name}_id")
    revision_parent_key = _safe_db_identifier(f"{table_name}_parent_id")
    if field_name == "revision_no":
        return {"field_name": field_name, "data_type": "int4", "nullable": "no", "constraints": "positive"}
    if field_name == "is_active":
        return {"field_name": field_name, "data_type": "boolean", "nullable": "no", "constraints": "default false"}
    if field_name.endswith("_id"):
        constraints = ""
        if field_name == "tenant_id":
            constraints = "fk tenant.tenant_id"
        elif field_name in {base_pk, revision_parent_key}:
            constraints = f"fk {base_table_name}.{base_pk}"
        return {
            "field_name": field_name,
            "data_type": "uuid",
            "nullable": "no",
            "constraints": constraints,
        }
    if field_name.endswith("_at"):
        return {"field_name": field_name, "data_type": "timestamptz", "nullable": "yes", "constraints": ""}
    return {"field_name": field_name, "data_type": "text", "nullable": "yes", "constraints": ""}


def _table_seed_example_fields(table_name: str) -> dict[str, object]:
    seeds: dict[str, dict[str, object]] = {
        "appointment": {
            "petId": "pet-001",
            "ownerId": "owner-001",
            "vetName": "Dr. Lin",
            "appointmentDate": "2026-04-15T09:30:00Z",
            "appointmentType": "follow_up",
            "reason": "Annual vaccination review",
        },
        "visit_record": {
            "petId": "pet-001",
            "ownerId": "owner-001",
            "vetName": "Dr. Lin",
            "visitDate": "2026-04-10T10:00:00Z",
            "chiefComplaint": "Loss of appetite for two days",
            "diagnosis": "Mild gastritis",
            "treatmentPlan": "Medication and dietary observation",
        },
        "drug": {
            "drugName": "Amoxicillin",
            "dosageForm": "tablet",
            "unit": "box",
            "stockQty": 24,
            "unitPrice": 39.5,
        },
        "payment": {
            "invoiceId": "invoice-001",
            "paymentMethod": "card",
            "amount": 128.0,
            "paidAt": "2026-04-10T11:15:00Z",
            "referenceNo": "PAY-20260410-001",
        },
        "workflow_audit_record": {
            "subjectId": "visit_record-001",
            "subjectType": "visit_record",
            "action": "status_changed",
            "actor": "front_desk_operator",
            "performedAt": "2026-04-10T11:20:00Z",
            "detail": "Status moved from draft to active",
        },
        "workflow_review_summary": {
            "subjectId": "visit_record-001",
            "reviewer": "Dr. Lin",
            "reviewDate": "2026-04-10T11:30:00Z",
            "outcome": "approved",
            "summary": "Clinical record complete and ready for billing",
        },
    }
    return dict(seeds.get(table_name, {}))


def _path_table_name(path: str) -> str:
    normalized = path.strip("/")
    if normalized.startswith("api/"):
        normalized = normalized[4:]
    parts = [part for part in normalized.split("/") if part]
    resource = ""
    for part in parts:
        if part.startswith("v") and part[1:].isdigit():
            continue
        if part.startswith("{"):
            continue
        resource = part
        break
    mapping = {
        "appointments": "appointment",
        "visit-records": "visit_record",
        "drugs": "drug",
        "payments": "payment",
        "workflow-audits": "workflow_audit_record",
        "workflow-audit-records": "workflow_audit_record",
        "workflow-review-summaries": "workflow_review_summary",
    }
    return _safe_db_identifier(mapping.get(resource, _snake_case_token(resource.rstrip("s"))))


def _has_non_empty_example_value(value: object) -> bool:
    if isinstance(value, dict):
        return any(_has_non_empty_example_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_non_empty_example_value(item) for item in value)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _request_example_has_business_content(value: object) -> bool:
    if not isinstance(value, dict):
        return _has_non_empty_example_value(value)
    for key, entry in value.items():
        normalized = _snake_case_token(key)
        if normalized in {"tenant_id", "status", "module", "cursor", "page_size", "expected_version"}:
            continue
        if normalized.endswith("_id") or normalized == "id":
            continue
        if normalized in {"input", "payload", "body"} and isinstance(entry, dict):
            for nested_key, nested_value in entry.items():
                nested_normalized = _snake_case_token(nested_key)
                if nested_normalized in {"summary", "notes", "payload", "input"}:
                    continue
                if nested_normalized.endswith("_id") or nested_normalized == "id":
                    continue
                if _has_non_empty_example_value(nested_value):
                    return True
            continue
        if _has_non_empty_example_value(entry):
            return True
    return False


def _merge_seed_example_fields(path: str, request_example: object, response_example: object) -> tuple[object, object]:
    table_name = _path_table_name(path)
    seed_fields = _table_seed_example_fields(table_name)
    if not seed_fields:
        return request_example, response_example
    remove_module = table_name in {
        "appointment",
        "visit_record",
        "drug",
        "payment",
        "workflow_audit_record",
        "workflow_review_summary",
    }

    if isinstance(request_example, dict) and not _request_example_has_business_content(request_example):
        enriched_request = dict(request_example)
        for key, value in seed_fields.items():
            enriched_request.setdefault(key, value)
        if remove_module:
            enriched_request.pop("module", None)
        request_example = enriched_request

    if isinstance(response_example, dict):
        enriched_response = dict(response_example)
        data = enriched_response.get("data")
        if isinstance(data, dict) and not _has_non_empty_example_value(data):
            merged_data = dict(data)
            for key, value in seed_fields.items():
                merged_data.setdefault(key, value)
            if remove_module:
                merged_data.pop("module", None)
            enriched_response["data"] = merged_data
        elif isinstance(data, list):
            merged_rows: list[object] = []
            for item in data:
                if isinstance(item, dict) and not _has_non_empty_example_value(item):
                    merged_item = dict(item)
                    for key, value in seed_fields.items():
                        merged_item.setdefault(key, value)
                    if remove_module:
                        merged_item.pop("module", None)
                    merged_rows.append(merged_item)
                else:
                    merged_rows.append(item)
            enriched_response["data"] = merged_rows
        response_example = enriched_response
    return request_example, response_example


def _derived_fields_from_endpoints(
    table_name: str,
    pk_name: str,
    endpoint_rows: list[dict[str, object]],
) -> list[dict[str, str]]:
    seen: dict[str, dict[str, str]] = {}
    singular_name = table_name.removesuffix("_revision")
    path_candidates = _plural_path_candidates(singular_name)
    table_tokens = {singular_name, singular_name.replace("_", ""), singular_name.replace("_", "-")}

    def register(field_name: str, sample_value: object) -> None:
        normalized = _snake_case_token(field_name)
        if not normalized or normalized in {
            pk_name,
            "tenant_id",
            "status",
            "created_at",
            "updated_at",
            "cursor",
            "page_size",
            "trace_id",
            "next_cursor",
            "id",
            "module",
            "expected_version",
            "workflow_input_summary",
        }:
            return
        if normalized.endswith("_id") and normalized == pk_name:
            return
        if normalized in seen:
            return
        seen[normalized] = {
            "field_name": normalized,
            "data_type": _infer_sql_type(normalized, sample_value),
            "nullable": "yes",
            "constraints": "check >= 0" if normalized == "expected_version" else "",
        }

    for row in endpoint_rows:
        path = str(row.get("path", ""))
        operation_name = str(row.get("endpoint_name", ""))
        request_example = row.get("request_body_example")
        response_example = row.get("response_body_example")
        normalized_operation = _snake_case_token(operation_name)
        row_relevant = any(candidate in path for candidate in path_candidates) or any(
            token in normalized_operation for token in table_tokens
        )

        for payload in _unwrap_contract_example(request_example):
            if not row_relevant:
                continue
            for key, value in payload.items():
                if key == "input" and isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        register(f"workflow_input_{nested_key}", nested_value)
                    continue
                register(key, value)

        for payload in _unwrap_contract_example(response_example):
            if not row_relevant:
                continue
            for key, value in payload.items():
                register(key, value)

    return list(seen.values())


def _expand_payload_shell_fields(
    table_name: str,
    summary: dict[str, str],
    fields: list[dict[str, str]],
    endpoint_rows: list[dict[str, object]],
) -> list[dict[str, str]]:
    payload_fields = [field for field in fields if _snake_case_token(str(field.get("field_name", ""))) == "payload"]
    if not payload_fields:
        return fields

    base_fields = [dict(field) for field in fields if _snake_case_token(str(field.get("field_name", ""))) != "payload"]
    pk_name = next(
        (
            _snake_case_token(str(field.get("field_name", "")))
            for field in base_fields
            if "pk" in str(field.get("constraints", "")).lower()
        ),
        _snake_case_token(summary.get("pk", "")),
    )
    derived_fields = [] if table_name.endswith("_revision") else _derived_fields_from_endpoints(table_name, pk_name, endpoint_rows)
    seed_fields = _business_seed_fields(table_name)
    required_constraint_fields = _referenced_constraint_fields(summary)
    by_name: dict[str, dict[str, str]] = {
        _snake_case_token(str(field["field_name"])): dict(field)
        for field in base_fields
    }
    for candidate in derived_fields:
        normalized = _snake_case_token(str(candidate["field_name"]))
        if not normalized or normalized in by_name:
            continue
        by_name[normalized] = dict(candidate)

    seed_by_name = {
        _snake_case_token(str(field["field_name"])): dict(field)
        for field in seed_fields
        if _snake_case_token(str(field["field_name"]))
    }
    for field_name in required_constraint_fields:
        fallback = _constraint_field_fallback(table_name, field_name)
        if field_name not in by_name:
            by_name[field_name] = dict(seed_by_name.get(field_name, fallback))
        if str(fallback.get("nullable", "")).lower() == "no":
            by_name[field_name]["nullable"] = "no"
        if not str(by_name[field_name].get("constraints", "")).strip() and str(fallback.get("constraints", "")).strip():
            by_name[field_name]["constraints"] = str(fallback["constraints"])

    business_column_names = {
        name
        for name in by_name
        if name not in {pk_name, "tenant_id", "status", "created_at", "updated_at"}
    }
    if len(business_column_names) < 3:
        for candidate in seed_fields:
            normalized = _snake_case_token(str(candidate["field_name"]))
            if not normalized or normalized in by_name:
                continue
            by_name[normalized] = dict(candidate)
            if normalized not in {pk_name, "tenant_id", "status", "created_at", "updated_at"}:
                business_column_names.add(normalized)
            if len(business_column_names) >= 3:
                break

    if len(business_column_names) < 3:
        for candidate in seed_fields:
            normalized = _snake_case_token(str(candidate["field_name"]))
            if not normalized or normalized in by_name:
                continue
            by_name[normalized] = dict(candidate)
            business_column_names.add(normalized)

    business_column_count = len(
        [
            name
            for name in by_name
            if name not in {pk_name, "tenant_id", "status", "created_at", "updated_at"}
        ]
    )
    if business_column_count < 3:
        by_name["metadata"] = {
            "field_name": "metadata",
            "data_type": "jsonb",
            "nullable": "yes",
            "constraints": "schema-validated",
        }

    ordered_names = [str(field["field_name"]) for field in base_fields]
    payload_index = next(
        idx for idx, field in enumerate(fields) if _snake_case_token(str(field.get("field_name", ""))) == "payload"
    )
    ordered_names[payload_index:payload_index] = [
        str(field["field_name"])
        for field in derived_fields + seed_fields
        if _snake_case_token(str(field["field_name"])) in by_name and str(field["field_name"]) not in ordered_names
    ]
    for field_name in required_constraint_fields:
        if field_name in by_name and field_name not in ordered_names:
            ordered_names.append(field_name)
    if "metadata" in by_name and "metadata" not in ordered_names:
        ordered_names.append("metadata")
    deduped_order: list[str] = []
    seen_names: set[str] = set()
    for name in ordered_names:
        normalized = _snake_case_token(name)
        if not normalized or normalized in seen_names or normalized not in by_name:
            continue
        seen_names.add(normalized)
        deduped_order.append(normalized)
    return [by_name[name] for name in deduped_order]


def _schema_summary_fields(summary: dict[str, str]) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_field(
        field_name: str,
        *,
        data_type: str,
        nullable: str,
        constraints: str,
    ) -> None:
        normalized_name = _safe_db_identifier(strip_ticks(field_name))
        if not normalized_name or normalized_name in seen:
            return
        seen.add(normalized_name)
        fields.append(
            {
                "field_name": normalized_name,
                "data_type": data_type,
                "nullable": nullable,
                "constraints": constraints,
            }
        )

    pk_name = strip_ticks(summary.get("pk", ""))
    if pk_name and pk_name.lower() != "none":
        add_field(pk_name, data_type="TEXT", nullable="no", constraints="pk")

    fk_specs = split_specs(summary.get("fk", ""))
    for fk_spec in fk_specs:
        left, arrow, right = fk_spec.partition("->")
        field_name = strip_ticks(left)
        target = strip_ticks(right)
        if not field_name or not arrow or "." not in target:
            continue
        add_field(field_name, data_type="TEXT", nullable="no", constraints=f"fk {target}")

    for index_spec in split_specs(summary.get("composite_indexes", "")):
        normalized = normalize_index_spec(index_spec)
        parts = [strip_ticks(part) for part in normalized.split(",")]
        for part in parts:
            field_name = strip_ticks(re.sub(r"\s+(asc|desc)$", "", part, flags=re.IGNORECASE))
            if not field_name or field_name.lower() == "none":
                continue
            data_type = "TIMESTAMPTZ" if field_name.endswith("_at") else "TEXT"
            add_field(field_name, data_type=data_type, nullable="yes", constraints="")

    if not fields:
        fallback_name = strip_ticks(summary.get("table_name", "")) or "id"
        add_field(f"{fallback_name}_id", data_type="TEXT", nullable="no", constraints="pk")
    return fields


def _normalize_schema_constraint_refs(constraint_text: str) -> str:
    return re.sub(
        r"\bfk\s+([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)",
        lambda match: f"fk {_safe_db_identifier(match.group(1))}.{_safe_db_identifier(match.group(2))}",
        constraint_text,
        flags=re.IGNORECASE,
    )


def _normalize_schema_field_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        normalized = dict(row)
        normalized["field_name"] = _safe_db_identifier(str(normalized.get("field_name", "")))
        normalized["constraints"] = _normalize_schema_constraint_refs(str(normalized.get("constraints", "")))
        normalized_rows.append(normalized)
    return normalized_rows


def parse_schema_tables(text: str) -> list[dict[str, object]]:
    try:
        endpoint_rows = parse_api_endpoint_rows(text)
    except ValueError:
        endpoint_rows = []
    section = extract_heading_section_any(text, SCHEMA_HEADINGS)
    summary_table = first_table_with_headers(
        section,
        {"table_name", "ownership", "pk", "fk", "unique_constraints", "composite_indexes"},
        id_headers=("table_name",),
    )
    summary_by_table: dict[str, dict[str, str]] = {}
    if summary_table is not None:
        for row in summary_table["rows"]:
            raw_table_name = strip_ticks(str(row["table_name"]))
            normalized_table_name = _safe_db_identifier(raw_table_name)
            summary = {key: strip_ticks(str(value)) for key, value in row.items()}
            summary["table_name"] = normalized_table_name
            summary_by_table[raw_table_name] = summary
            summary_by_table[normalized_table_name] = summary

    tables: list[dict[str, object]] = []
    lines = section.splitlines()
    idx = 0
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped.startswith("- table_name:"):
            idx += 1
            continue

        raw_table_name = strip_ticks(stripped.split(":", 1)[1])
        table_name = _safe_db_identifier(raw_table_name)
        unique_raw = ""
        indexes_raw = ""
        idx += 1
        while idx < len(lines):
            current = lines[idx].strip()
            if current.startswith("- unique_constraints:"):
                unique_raw = current.split(":", 1)[1].strip()
            elif current.startswith("- composite_indexes:"):
                indexes_raw = current.split(":", 1)[1].strip()
            elif "field_matrix:" in lines[idx] or "field_registry:" in lines[idx]:
                idx += 1
                break
            if current.startswith("|"):
                break
            if current.startswith("- table_name:"):
                raise ValueError(f"field matrix marker not found for table: {raw_table_name}")
            idx += 1
        if idx >= len(lines):
            raise ValueError(f"field matrix marker not found for table: {raw_table_name}")

        table_lines: list[str] = []
        while idx < len(lines) and lines[idx].lstrip().startswith("|"):
            table_lines.append(lines[idx].strip())
            idx += 1
        field_tables = markdown_tables("\n".join(table_lines))
        if not field_tables:
            raise ValueError(f"field matrix not found for table: {raw_table_name}")

        while idx < len(lines):
            current = lines[idx].strip()
            if current.startswith("- table_name:"):
                break
            if current.startswith("- unique_constraints:"):
                unique_raw = current.split(":", 1)[1].strip()
            elif current.startswith("- composite_indexes:"):
                indexes_raw = current.split(":", 1)[1].strip()
            idx += 1

        field_rows = [
            {key: strip_ticks(str(value)) for key, value in row.items()}
            for row in field_tables[0]["rows"]
        ]
        summary = summary_by_table.get(raw_table_name, summary_by_table.get(table_name, {}))
        field_rows = _expand_payload_shell_fields(raw_table_name, summary, field_rows, endpoint_rows)
        field_rows = _normalize_schema_field_rows(field_rows)
        tables.append(
            {
                "table_name": table_name,
                "ownership": summary.get("ownership", ""),
                "fields": field_rows,
                "unique_constraints": [
                    normalize_index_spec(spec)
                    for spec in split_specs(unique_raw or summary.get("unique_constraints", ""))
                ],
                "composite_indexes": [
                    normalize_index_spec(spec)
                    for spec in split_specs(indexes_raw or summary.get("composite_indexes", ""))
                ],
            }
        )
    if not tables:
        for table_name, summary in summary_by_table.items():
            if table_name != _safe_db_identifier(table_name):
                continue
            tables.append(
                {
                    "table_name": table_name,
                    "ownership": summary.get("ownership", ""),
                    "fields": _normalize_schema_field_rows(_schema_summary_fields(summary)),
                    "unique_constraints": [
                        normalize_index_spec(spec) for spec in split_specs(summary.get("unique_constraints", ""))
                    ],
                    "composite_indexes": [
                        normalize_index_spec(spec) for spec in split_specs(summary.get("composite_indexes", ""))
                    ],
                }
            )
    if not tables:
        raise ValueError("schema field registry blocks not found")
    return tables


def _tag_from_path(path: str) -> str:
    parts = [part for part in path.split("/") if part and not part.startswith("{")]
    if not parts:
        return "default"
    if parts[0] == "api":
        if len(parts) > 2 and parts[1].startswith("v"):
            return parts[2]
        if len(parts) > 1:
            return parts[1]
    if parts[0].startswith("v") and len(parts) > 1:
        return parts[1]
    return parts[0]


def _success_status(method: str, endpoint_name: str) -> str:
    lowered_name = endpoint_name.lower()
    lowered_method = method.lower()
    if lowered_method == "post":
        if lowered_name.startswith("launch"):
            return "202"
        if lowered_name.startswith(("create", "export")):
            return "201"
    return "200"


def _behavior_evidence_keys_from_row(row: dict[str, object]) -> list[str]:
    raw_keys = row.get("behavior_evidence_keys") or row.get("evidence_keys") or []
    if isinstance(raw_keys, str):
        raw_keys = parse_list_cell(raw_keys)
    if not isinstance(raw_keys, list):
        return []
    keys: list[str] = []
    for key in raw_keys:
        text = str(key).strip()
        if text and text not in keys:
            keys.append(text)
    return keys


def _default_behavior_evidence_value(key: str) -> object:
    lowered = key.strip().lower()
    if lowered in {"trace_id", "traceid"}:
        return "trace-001"
    if lowered in {"tenant_id", "tenantid"}:
        return "tenant-001"
    if lowered in {"version", "expectedversion", "expected_version"}:
        return 1
    if lowered.endswith("_id") or lowered.endswith("id"):
        slug = re.sub(r"[_\s]+", "-", key.strip())
        slug = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", slug).lower()
        slug = re.sub(r"-?id$", "", slug).strip("-") or "record"
        return f"{slug}-001"
    return f"{key.strip()}-sample"


def _merge_behavior_evidence_into_example(example: object, evidence_keys: list[str]) -> dict[str, object]:
    merged: dict[str, object] = dict(example) if isinstance(example, dict) else {}
    normalized_existing = {
        re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key).lower(): key
        for key in merged
        if isinstance(key, str)
    }
    for key in evidence_keys:
        normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key).lower()
        if key in merged or normalized in normalized_existing:
            continue
        merged[key] = _default_behavior_evidence_value(key)
    return merged


def _parameter_names(parameters: list[object]) -> set[str]:
    names: set[str] = set()
    for parameter in parameters:
        if isinstance(parameter, dict):
            name = str(parameter.get("name", "")).strip()
            if name:
                names.add(name)
    return names


def _behavior_evidence_keys_from_model(model: object) -> list[str]:
    if not isinstance(model, dict):
        return []
    semantics = model.get("operation_semantics") if isinstance(model.get("operation_semantics"), dict) else {}
    keys = semantics.get("evidence_keys") if isinstance(semantics.get("evidence_keys"), list) else []
    return [str(key).strip() for key in keys if str(key).strip()]


def _normalized_contract_key(value: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower()


def _ensure_schema_property(schema: dict[str, object], key: str, value: object) -> None:
    properties = schema.setdefault("properties", {})
    if not isinstance(properties, dict):
        properties = {}
        schema["properties"] = properties
    normalized_existing = {_normalized_contract_key(str(existing)): str(existing) for existing in properties}
    if _normalized_contract_key(key) not in normalized_existing:
        properties[key] = infer_json_schema(value)
    required = schema.setdefault("required", [])
    if not isinstance(required, list):
        required = []
        schema["required"] = required
    if key not in required:
        required.append(key)
    schema["type"] = schema.get("type") or "object"
    schema["additionalProperties"] = schema.get("additionalProperties", False)
    schema["x-schema-source"] = "inferred-from-example+behavior-evidence"


def _ensure_required_query_parameter(operation: dict[str, object], key: str) -> None:
    parameters = operation.setdefault("parameters", [])
    if not isinstance(parameters, list):
        parameters = []
        operation["parameters"] = parameters
    normalized_key = _normalized_contract_key(key)
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        if str(parameter.get("in", "")).strip() != "query":
            continue
        if _normalized_contract_key(str(parameter.get("name", "")).strip()) == normalized_key:
            parameter["required"] = True
            parameter.setdefault("schema", infer_json_schema(_default_behavior_evidence_value(key)))
            parameter.setdefault("example", _default_behavior_evidence_value(key))
            return
    parameters.append(
        {
            "name": key,
            "in": "query",
            "required": True,
            "schema": infer_json_schema(_default_behavior_evidence_value(key)),
            "example": _default_behavior_evidence_value(key),
        }
    )


def _ensure_required_body_field(operation: dict[str, object], key: str) -> None:
    request_body = operation.setdefault("requestBody", {"required": True, "content": {"application/json": {}}})
    if not isinstance(request_body, dict):
        request_body = {"required": True, "content": {"application/json": {}}}
        operation["requestBody"] = request_body
    request_body["required"] = True
    content = request_body.setdefault("content", {})
    if not isinstance(content, dict):
        content = {}
        request_body["content"] = content
    app_json = content.setdefault("application/json", {})
    if not isinstance(app_json, dict):
        app_json = {}
        content["application/json"] = app_json
    example = app_json.setdefault("example", {})
    if not isinstance(example, dict):
        example = {}
        app_json["example"] = example
    normalized_existing = {_normalized_contract_key(str(existing)): str(existing) for existing in example}
    if _normalized_contract_key(key) not in normalized_existing:
        example[key] = _default_behavior_evidence_value(key)
    schema = app_json.setdefault("schema", infer_contract_json_schema(example))
    if not isinstance(schema, dict):
        schema = infer_contract_json_schema(example)
        app_json["schema"] = schema
    _ensure_schema_property(schema, key, example.get(key, _default_behavior_evidence_value(key)))


def enrich_openapi_spec_with_behavior_evidence(
    spec: dict[str, object],
    behavior_card_models: dict[str, dict[str, object]] | None,
) -> dict[str, object]:
    """Expose behavior-card evidence requirements on the public OpenAPI surface.

    Service/test scaffolds consume behavior-card payloads. API Docs must expose
    the same required evidence keys so an external API consumer can execute the
    documented contract without knowing internal test helpers.
    """

    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return spec
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            method_text = str(method).lower()
            if method_text not in {"get", "post", "put", "patch", "delete"} or not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId", "")).strip()
            evidence_keys = _behavior_evidence_keys_from_model((behavior_card_models or {}).get(operation_id))
            if not evidence_keys:
                continue
            operation["x-behavior-evidence-required"] = evidence_keys
            if method_text == "get":
                for key in evidence_keys:
                    _ensure_required_query_parameter(operation, key)
            else:
                for key in evidence_keys:
                    _ensure_required_body_field(operation, key)
    return spec


def build_openapi_spec(
    endpoint_rows: list[dict[str, object]],
    *,
    title: str = "Phase-3 Contract Pack",
    version: str = "0.1.0",
) -> dict[str, object]:
    spec: dict[str, object] = {
        "openapi": "3.1.0",
        "info": {"title": title, "version": version},
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "paths": {},
    }
    paths: dict[str, object] = spec["paths"]  # type: ignore[assignment]

    for row in endpoint_rows:
        path = str(row["path"])
        method = str(row["method"]).lower()
        endpoint_name = str(row["endpoint_name"])
        behavior_evidence_keys = _behavior_evidence_keys_from_row(row)
        request_example = _merge_behavior_evidence_into_example(row["request_body_example"], behavior_evidence_keys)
        response_example = row["response_body_example"]
        failures = row["failure_codes"]
        resolved_path = resolve_openapi_operation_path(
            path=path,
            method=method,
            endpoint_name=endpoint_name,
            request_example=request_example,
            response_example=response_example,
        )

        resolved_path = _unique_operation_path(
            paths,
            resolved_path=resolved_path,
            method=method,
            endpoint_name=endpoint_name,
        )

        operation: dict[str, object] = {
            "operationId": endpoint_name,
            "summary": str(row["purpose"]),
            "tags": [_tag_from_path(resolved_path)],
            "responses": {},
            "x-rate-limit-policy": row.get("rate_limit_policy", ""),
            "x-pagination-rule": row.get("pagination_rule", ""),
            "x-retryability-policy": row.get("retryability_policy", ""),
            "x-idempotency-rule": row.get("idempotency_rule", ""),
        }

        path_parameters = re.findall(r"{([^}]+)}", resolved_path)
        if path_parameters:
            operation["parameters"] = [
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
                for name in path_parameters
            ]

        if method == "get":
            query_params = []
            if isinstance(request_example, dict):
                for key, value in request_example.items():
                    if key in path_parameters:
                        continue
                    query_params.append(
                        {
                            "name": key,
                            "in": "query",
                            "required": key in behavior_evidence_keys,
                            "schema": infer_json_schema(value),
                            "example": value,
                        }
                    )
            if behavior_evidence_keys:
                existing_query_param_names = _parameter_names(query_params)
                for key in behavior_evidence_keys:
                    if key in path_parameters or key in existing_query_param_names:
                        continue
                    query_params.append(
                        {
                            "name": key,
                            "in": "query",
                            "required": True,
                            "schema": infer_json_schema(_default_behavior_evidence_value(key)),
                            "example": _default_behavior_evidence_value(key),
                        }
                    )
            if query_params:
                existing = operation.setdefault("parameters", [])
                assert isinstance(existing, list)
                existing.extend(query_params)
        elif request_example not in ({}, None):
            request_schema = infer_contract_json_schema(request_example)
            if isinstance(request_schema, dict):
                request_schema["x-schema-source"] = "inferred-from-example"
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": request_schema,
                        "example": request_example,
                    }
                },
            }

        success_status = _success_status(str(row["method"]), endpoint_name)
        operation["responses"][success_status] = {
            "description": "Success",
            "content": {
                "application/json": {
                    "schema": add_pagination_contract(infer_contract_json_schema(response_example), row.get("pagination_rule", "")),
                    "example": response_example,
                }
            },
        }

        for failure in failures:  # type: ignore[assignment]
            status = failure["status"]
            kind = failure["error_kind"]
            code = failure["error_code"]
            retryability = failure["retryability"]
            operation["responses"][status] = {
                "description": f"{kind} {code}".strip(),
                "content": {
                    "application/json": {
                        "schema": error_envelope_schema(kind=kind, code=code, retryability=retryability),
                        "example": {
                            "error_kind": kind,
                            "error_code": code,
                            "retryability": retryability,
                        },
                    }
                },
            }

        path_item = paths.setdefault(resolved_path, {})
        assert isinstance(path_item, dict)
        path_item[method] = operation
    return spec


DETAIL_OPERATION_PREFIXES = ("get", "fetch", "load", "read")
NON_RESOURCE_ID_KEYS = {
    "cursor",
    "page_size",
    "pagesize",
    "request_id",
    "requestid",
    "tenant_id",
    "tenantid",
    "trace_id",
    "traceid",
}


def _identity_query_keys(request_example: object) -> list[str]:
    if not isinstance(request_example, dict):
        return []
    keys: list[str] = []
    for key in request_example:
        if not isinstance(key, str):
            continue
        lowered = key.strip().lower()
        if lowered in NON_RESOURCE_ID_KEYS:
            continue
        if lowered.endswith("_id") or lowered.endswith("id"):
            keys.append(key.strip())
    return keys


def _identity_response_keys(response_example: object) -> list[str]:
    if not isinstance(response_example, dict):
        return []
    data = response_example.get("data")
    if isinstance(data, list):
        data = next((item for item in data if isinstance(item, dict)), {})
    if not isinstance(data, dict):
        data = response_example
    return _identity_query_keys(data)


def _rank_identity_keys(endpoint_name: str, candidates: list[str]) -> list[str]:
    if not candidates:
        return []
    normalized_endpoint = re.sub(r"[^a-z0-9]+", "", endpoint_name.lower())
    return sorted(
        candidates,
        key=lambda key: (
            0
            if re.sub(r"(?:_id|id)$", "", re.sub(r"[^a-z0-9]+", "", key.lower())) in normalized_endpoint
            else 1,
            len(key),
            key,
        ),
    )


def _choose_detail_path_param(endpoint_name: str, request_example: object, response_example: object | None = None) -> str:
    request_candidates = _rank_identity_keys(endpoint_name, _identity_query_keys(request_example))
    if request_candidates:
        return request_candidates[0]
    response_candidates = _rank_identity_keys(endpoint_name, _identity_response_keys(response_example or {}))
    return response_candidates[0] if response_candidates else ""


def resolve_openapi_operation_path(
    *,
    path: str,
    method: str,
    endpoint_name: str,
    request_example: object,
    response_example: object,
) -> str:
    normalized_path = str(path).strip()
    if method.lower() != "get":
        return normalized_path
    if re.search(r"{[^}]+}", normalized_path):
        return normalized_path
    lowered_name = endpoint_name.strip().lower()
    if lowered_name.startswith("list"):
        return normalized_path
    if not lowered_name.startswith(DETAIL_OPERATION_PREFIXES):
        return normalized_path
    response_payload = response_example if isinstance(response_example, dict) else {}
    response_data = response_payload.get("data") if isinstance(response_payload, dict) else None
    if isinstance(response_data, list):
        return normalized_path
    path_param = _choose_detail_path_param(endpoint_name, request_example, response_example)
    if not path_param:
        return normalized_path
    return f"{normalized_path.rstrip('/')}/{{{path_param}}}"


def _operation_collision_slug(endpoint_name: str) -> str:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", endpoint_name)
    slug = slugify(expanded)
    return slug or "operation"


def _unique_operation_path(
    paths: dict[str, object],
    *,
    resolved_path: str,
    method: str,
    endpoint_name: str,
) -> str:
    path_item = paths.get(resolved_path, {})
    if not isinstance(path_item, dict) or method not in path_item:
        return resolved_path
    existing_operation = path_item.get(method, {})
    if isinstance(existing_operation, dict) and str(existing_operation.get("operationId", "")).strip() == endpoint_name:
        return resolved_path

    slug = _operation_collision_slug(endpoint_name)
    base = resolved_path.rstrip("/")
    candidate = f"{base}/{slug}"
    if not isinstance(paths.get(candidate, {}), dict) or method not in paths.get(candidate, {}):
        return candidate
    for index in range(2, 100):
        candidate = f"{base}/{slug}-{index}"
        candidate_item = paths.get(candidate, {})
        if not isinstance(candidate_item, dict) or method not in candidate_item:
            return candidate
    raise ValueError(f"unable to allocate unique OpenAPI path for operation: {endpoint_name}")


def _foreign_key_target(constraint_text: str) -> tuple[str, str] | None:
    fk_match = re.search(r"fk\s+([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)", constraint_text)
    if not fk_match:
        return None
    return _safe_db_identifier(fk_match.group(1)), _safe_db_identifier(fk_match.group(2))


def _column_constraint_sql(field_name: str, constraint_text: str, *, include_references: bool = True) -> list[str]:
    clauses: list[str] = []
    lowered = constraint_text.lower()
    if "pk" in lowered:
        clauses.append("PRIMARY KEY")
    if "unique" in lowered and "partial unique" not in lowered and "pk" not in lowered:
        clauses.append("UNIQUE")

    fk_target = _foreign_key_target(constraint_text)
    if include_references and fk_target:
        clauses.append(f"REFERENCES {_sql_identifier(fk_target[0])} ({_sql_identifier(fk_target[1])})")

    default_match = re.search(r"default\s+(.+)", constraint_text, flags=re.IGNORECASE)
    if default_match:
        default_value = default_match.group(1).strip()
        clauses.append(f"DEFAULT {default_value}")

    if "positive" in lowered:
        clauses.append(f"CHECK ({field_name} > 0)")

    check_in_match = re.search(r"check in\s*(\(.+\))", constraint_text, flags=re.IGNORECASE)
    if check_in_match:
        clauses.append(f"CHECK ({field_name} IN {check_in_match.group(1)})")

    check_cmp_match = re.search(r"check\s*(>=|<=|>|<)\s*([0-9.]+)", constraint_text, flags=re.IGNORECASE)
    if check_cmp_match:
        clauses.append(f"CHECK ({field_name} {check_cmp_match.group(1)} {check_cmp_match.group(2)})")
    return clauses


def _index_name(prefix: str, table_name: str, spec: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", spec.lower()).strip("_")
    return _safe_db_identifier(f"{prefix}_{table_name}_{slug}")


def _foreign_key_constraint_name(table_name: str, field_name: str, referenced_table: str, referenced_column: str) -> str:
    return _index_name("fk", table_name, f"{field_name}_{referenced_table}_{referenced_column}")


def _render_index_column_spec(raw: str) -> str:
    text = strip_ticks(raw)
    if not text:
        return ""
    match = re.match(r"^([A-Za-z0-9_]+)(\s+(?:asc|desc))?$", text, flags=re.IGNORECASE)
    if match:
        direction = str(match.group(2) or "").lower()
        return f"{_sql_identifier(match.group(1))}{direction}"

    def replace_token(token_match: re.Match[str]) -> str:
        token = token_match.group(0)
        if token.isdigit() or token.lower() in {"asc", "desc", "nulls", "first", "last"}:
            return token
        return _sql_identifier(token)

    return re.sub(r"[A-Za-z0-9_]+", replace_token, text)


def _render_column_list(raw_columns: str) -> str:
    rendered = [
        _render_index_column_spec(part.strip())
        for part in raw_columns.split(",")
        if part.strip()
    ]
    return ", ".join(part for part in rendered if part)


def _render_predicate_expression(raw: str, known_identifiers: set[str]) -> str:
    rendered = raw
    for identifier in sorted(known_identifiers, key=len, reverse=True):
        if not identifier:
            continue
        rendered = re.sub(
            rf"(?<![A-Za-z0-9_]){re.escape(identifier)}(?![A-Za-z0-9_])",
            _sql_identifier(identifier),
            rendered,
        )
    return rendered


def generate_migration_sql(tables: list[dict[str, object]]) -> str:
    lines = [
        "-- Generated by esp_to_migration.py",
        "BEGIN;",
        "",
    ]
    deferred_foreign_keys: list[str] = []
    deferred_indexes: list[str] = []

    for table in tables:
        table_name = _safe_db_identifier(str(table["table_name"]))
        table_sql = _sql_identifier(table_name)
        field_names = {
            _safe_db_identifier(str(field.get("field_name", "")))
            for field in table["fields"]  # type: ignore[index]
        }
        lines.append(f"CREATE TABLE IF NOT EXISTS {table_sql} (")
        column_lines: list[str] = []
        table_constraints: list[str] = []
        notes: list[str] = []

        for field in table["fields"]:  # type: ignore[index]
            field_name = _safe_db_identifier(str(field["field_name"]))
            field_sql = _sql_identifier(field_name)
            data_type = str(field["data_type"])
            nullable = str(field["nullable"]).lower()
            constraint_text = str(field["constraints"])
            parts = [field_sql, data_type]
            parts.extend(_column_constraint_sql(field_sql, constraint_text, include_references=False))
            if nullable == "no" and "PRIMARY KEY" not in parts:
                parts.append("NOT NULL")
            column_lines.append("  " + " ".join(parts))

            fk_target = _foreign_key_target(constraint_text)
            if fk_target:
                referenced_table, referenced_column = fk_target
                constraint_name = _foreign_key_constraint_name(
                    table_name, field_name, referenced_table, referenced_column
                )
                constraint_sql = _sql_identifier(constraint_name)
                referenced_table_sql = _sql_identifier(referenced_table)
                referenced_column_sql = _sql_identifier(referenced_column)
                deferred_foreign_keys.extend(
                    [
                        "DO $$",
                        "BEGIN",
                        "  IF EXISTS (SELECT 1 FROM pg_class WHERE relname = "
                        f"'{referenced_table}') AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{constraint_name}') THEN",
                        "    ALTER TABLE "
                        f"{table_sql} ADD CONSTRAINT {constraint_sql} FOREIGN KEY ({field_sql}) "
                        f"REFERENCES {referenced_table_sql} ({referenced_column_sql});",
                        "  END IF;",
                        "END $$;",
                        "",
                    ]
                )

            lowered = constraint_text.lower()
            if "schema-validated" in lowered:
                notes.append(f"-- note: {table_name}.{field_name} expects external JSON schema validation")
            if "retention-controlled" in lowered:
                notes.append(f"-- note: {table_name}.{field_name} is retention controlled")

        for unique_spec in table["unique_constraints"]:  # type: ignore[index]
            lowered = unique_spec.lower()
            if lowered == "none":
                continue
            if " where " in lowered:
                column_part, where_part = re.split(r"\bwhere\b", unique_spec, maxsplit=1, flags=re.IGNORECASE)
                column_part = _render_column_list(column_part)
                rendered_where_part = _render_predicate_expression(where_part.strip(), field_names)
                deferred_indexes.append(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    f"{_sql_identifier(_index_name('uidx', table_name, unique_spec))} ON {table_sql} "
                    f"({column_part.strip()}) WHERE {rendered_where_part};"
                )
                continue
            columns = [
                _render_index_column_spec(part.strip())
                for part in unique_spec.split(",")
                if part.strip()
            ]
            table_constraints.append(f"  UNIQUE ({', '.join(columns)})")

        lines.extend(",\n".join(column_lines + table_constraints).splitlines())
        lines.append(");")

        for index_spec in table["composite_indexes"]:  # type: ignore[index]
            lowered = index_spec.lower()
            if lowered == "none":
                continue
            normalized_index_spec = _render_column_list(index_spec)
            deferred_indexes.append(
                "CREATE INDEX IF NOT EXISTS "
                f"{_sql_identifier(_index_name('idx', table_name, index_spec))} ON {table_sql} ({normalized_index_spec});"
            )

        if notes:
            lines.extend(notes)
        lines.append("")

    lines.extend(deferred_foreign_keys)
    lines.extend(deferred_indexes)
    lines.extend(["", "COMMIT;", ""])
    return "\n".join(lines)


def load_openapi_document(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_compiled_bindings_document(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return []
    raw_rows = payload.get("compiled_bindings", [])
    if not isinstance(raw_rows, list):
        return []
    return [row for row in raw_rows if isinstance(row, dict)]


def _operation_key(method: str, path: str) -> tuple[str, str]:
    return str(method).upper().strip(), str(path).strip()


def compiled_binding_operation_index(
    compiled_bindings: list[dict[str, object]] | None,
) -> dict[tuple[str, str], list[dict[str, object]]]:
    index: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in compiled_bindings or []:
        if not isinstance(row, dict):
            continue
        method = str(row.get("http_method") or "").strip().upper()
        path = str(row.get("api_endpoint") or "").strip()
        if not method or not path:
            continue
        index.setdefault(_operation_key(method, path), []).append(row)
    return index


def derived_openapi_from_compiled_bindings(
    spec: dict[str, object],
    compiled_bindings: list[dict[str, object]] | None,
) -> dict[str, object]:
    derived = json.loads(json.dumps(spec))
    if not isinstance(derived, dict):
        return {}
    binding_index = compiled_binding_operation_index(compiled_bindings)
    if not binding_index:
        derived["x-derived-artifact-kind"] = "blocked-derived-openapi"
        derived["x-derived-authority"] = "missing-compiled-bindings"
        derived["x-derived-blocker"] = "compiled_bindings_required_for_wo15j"
        return derived

    derived["x-derived-artifact-kind"] = "compiled-binding-derived-openapi"
    derived["x-derived-authority"] = "compiled-bindings"

    raw_paths = derived.get("paths", {})
    if not isinstance(raw_paths, dict):
        derived["paths"] = {}
        return derived

    filtered_paths: dict[str, object] = {}
    for path, path_item in raw_paths.items():
        if not isinstance(path_item, dict):
            continue
        next_path_item: dict[str, object] = {}
        for method, operation in path_item.items():
            key = _operation_key(str(method), str(path))
            matching_bindings = binding_index.get(key, [])
            if not matching_bindings:
                continue
            if not isinstance(operation, dict):
                continue
            operation_copy = json.loads(json.dumps(operation))
            operation_copy["x-derived-from-compiled-bindings"] = [
                str(row.get("service_binding_id") or "").strip()
                for row in matching_bindings
                if str(row.get("service_binding_id") or "").strip()
            ]
            operation_copy["x-binding-mode"] = sorted(
                {
                    str(row.get("binding_mode") or "").strip()
                    for row in matching_bindings
                    if str(row.get("binding_mode") or "").strip()
                }
            )
            operation_copy["x-domain-services"] = sorted(
                {
                    str(row.get("domain_service") or "").strip()
                    for row in matching_bindings
                    if str(row.get("domain_service") or "").strip()
                }
            )
            operation_copy["x-rbac-policies"] = sorted(
                {
                    str(row.get("rbac_policy") or "").strip()
                    for row in matching_bindings
                    if str(row.get("rbac_policy") or "").strip()
                }
            )
            operation_copy["x-audit-events"] = sorted(
                {
                    str(row.get("audit_event") or "").strip()
                    for row in matching_bindings
                    if str(row.get("audit_event") or "").strip()
                }
            )
            operation_copy["x-failure-semantics"] = sorted(
                {
                    str(row.get("failure_codes") or "").strip()
                    for row in matching_bindings
                    if str(row.get("failure_codes") or "").strip()
                }
            )
            next_path_item[str(method)] = operation_copy
        if next_path_item:
            filtered_paths[str(path)] = next_path_item
    derived["paths"] = filtered_paths
    return derived


def compiled_binding_metadata_by_operation(
    compiled_bindings: list[dict[str, object]] | None,
) -> dict[str, dict[str, object]]:
    metadata: dict[str, dict[str, object]] = {}
    for rows in compiled_binding_operation_index(compiled_bindings).values():
        if not rows:
            continue
        operation_id = ""
        for row in rows:
            operation_id = str(row.get("operation_id") or "").strip()
            if operation_id:
                break
        if not operation_id:
            continue
        metadata[operation_id] = {
            "service_binding_ids": [
                str(row.get("service_binding_id") or "").strip()
                for row in rows
                if str(row.get("service_binding_id") or "").strip()
            ],
            "binding_modes": sorted(
                {
                    str(row.get("binding_mode") or "").strip()
                    for row in rows
                    if str(row.get("binding_mode") or "").strip()
                }
            ),
            "rbac_policies": sorted(
                {
                    str(row.get("rbac_policy") or "").strip()
                    for row in rows
                    if str(row.get("rbac_policy") or "").strip()
                }
            ),
            "failure_codes": sorted(
                {
                    str(row.get("failure_codes") or "").strip()
                    for row in rows
                    if str(row.get("failure_codes") or "").strip()
                }
            ),
        }
    return metadata
