from __future__ import annotations

import importlib
import json
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any

from common.script_data_assets import load_script_text_asset
from phase3.contract_test_scaffolder import scaffold_contract_tests
from phase3.contract_tools import build_openapi_spec, parse_api_endpoint_rows, parse_schema_tables
from phase3.impl_context import load_phase2_source_texts, write_json
from phase3.schema_test_scaffolder import scaffold_schema_tests
from phase3.security_audit import explicit_external_auth_requirement
from phase3.sql_test_scaffolder import scaffold_sql_tests


WFF_SCRIPT_DATA_ASSETS = ("scripts/phase3/data/backend-runtime-harness.ts.template",)


def _load_p2_authority(phase2_root: Path) -> dict[str, Any]:
    for path in (
        phase2_root / "p2-agentic-architecture-authority.json",
        phase2_root / ".phase2-evidence" / "p2-agentic-architecture-authority.json",
    ):
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return {}

def _response_example(operation: dict[str, Any]) -> dict[str, Any]:
    for status, response in sorted(operation.get("responses", {}).items()):
        if not str(status).startswith("2") or not isinstance(response, dict):
            continue
        example = response.get("content", {}).get("application/json", {}).get("example", {})
        if not isinstance(example, dict):
            continue
        data = example.get("data")
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
    return {}


def _operation_examples(openapi_spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path, path_item in openapi_spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId") or "").strip()
            if not operation_id:
                continue
            request = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("example", {})
            )
            request = request if isinstance(request, dict) else {}
            request = {**_operation_parameter_examples(operation), **request}
            result[operation_id] = {
                "operation_id": operation_id,
                "method": str(method).upper(),
                "path": str(path),
                "request": request,
                "response": _response_example(operation),
            }
    return result


def _openapi_failure_codes(operation: dict[str, Any]) -> list[str]:
    result: list[str] = []
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return result
    for status, response in responses.items():
        if str(status).startswith("2") or not isinstance(response, dict):
            continue
        example = response.get("content", {}).get("application/json", {}).get("example", {})
        if not isinstance(example, dict):
            continue
        code = str(example.get("error_code") or "").strip()
        if code and code not in result:
            result.append(code)
    return result


def _openapi_failure_statuses(operation: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return result
    for raw_status, response in responses.items():
        if not isinstance(response, dict):
            continue
        try:
            status = int(str(raw_status).strip())
        except ValueError:
            continue
        if status < 400:
            continue
        example = response.get("content", {}).get("application/json", {}).get("example", {})
        if not isinstance(example, dict):
            continue
        code = str(example.get("error_code") or "").strip()
        if code:
            result[code] = status
    return result


def _failure_field_hint_eligible(status: int, error_code: str) -> bool:
    """Limit field deletion to bounded caller-input failures, never dedicated failure lanes."""
    if status not in {400, 404, 422}:
        return False
    if "not_found" in error_code.casefold():
        return False
    return True


def _failure_field_hint(error_code: str, request_fields: list[str]) -> str:
    """Choose a bounded negative-test field without depending on serialized key order."""
    if not request_fields:
        return ""
    code = error_code.casefold()
    tokens = {token for token in re.split(r"[^a-z0-9]+", code) if token}
    scored: list[tuple[int, int, str]] = []
    for index, field in enumerate(request_fields):
        normalized = field.casefold()
        field_tokens = {token for token in normalized.split("_") if token and token not in {"ref", "id"}}
        score = len(tokens.intersection(field_tokens)) * 10
        # Prefer the semantic field itself over a compound identifier that merely
        # contains the same token. For example `invalid_decision` must target
        # `decision`, not an earlier `decision_request_id` field.
        if normalized in tokens:
            score += 30
        if "transition" in tokens and normalized in {"state", "status", "target_state"}:
            score += 20
        if ("confirmation" in tokens or "confirmed" in tokens) and "confirm" in normalized:
            score += 20
        if "evidence" in tokens and "evidence" in normalized:
            score += 20
        if score > 0:
            scored.append((score, -index, field))
    if scored:
        return max(scored)[2]
    if code in {"validation_failed", "invalid_input", "invalid_request", "invalid_photo", "invalid_trace"}:
        return request_fields[0]
    return ""


def _operation_parameter_examples(operation: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    parameters = operation.get("parameters", [])
    if not isinstance(parameters, list):
        return result
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        name = str(parameter.get("name") or "").strip()
        if not name:
            continue
        example = parameter.get("example")
        schema = parameter.get("schema") if isinstance(parameter.get("schema"), dict) else {}
        if example in (None, ""):
            example = schema.get("example") or schema.get("default")
        if example not in (None, ""):
            result[name] = example
    return result


def _validation_data_type_kind(data_type: str) -> str:
    lowered = data_type.strip().lower()
    if lowered in {"json", "jsonb"}:
        return "json"
    if "timestamp" in lowered or lowered == "timestamptz":
        return "timestamp"
    if lowered == "date":
        return "date"
    if "uuid" in lowered:
        return "uuid"
    if lowered in {"boolean", "bool"}:
        return "boolean"
    if lowered.startswith(("integer", "int", "bigint", "smallint")):
        return "integer"
    if lowered.startswith(("number", "numeric", "decimal", "real", "double", "float")):
        return "numeric"
    return "text"


def _iso_temporal_example_is_compatible(value: Any, *, kind: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip()
    try:
        if kind == "date":
            date.fromisoformat(text)
            return True
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return "T" in text or " " in text
    except ValueError:
        return False


def _validation_example_is_compatible(value: Any, *, data_type: str) -> bool:
    if value in (None, ""):
        return False
    kind = _validation_data_type_kind(data_type)
    if kind == "json":
        return isinstance(value, (dict, list))
    if kind in {"timestamp", "date"}:
        return _iso_temporal_example_is_compatible(value, kind=kind)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "numeric":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "uuid":
        # UUID-shaped validation identifiers are normalized deterministically by the
        # runtime harness after fixture construction; preserve that existing flow.
        return isinstance(value, str) and bool(value.strip())
    return isinstance(value, str) and bool(value.strip())


def _validation_field_value(
    *,
    field_name: str,
    data_type: str,
    examples: dict[str, Any],
) -> Any:
    kind = _validation_data_type_kind(data_type)
    expected_version = examples.get("expected_version") if field_name == "version" else None
    if _validation_example_is_compatible(expected_version, data_type=data_type):
        return expected_version
    example = examples.get(field_name)
    if _validation_example_is_compatible(example, data_type=data_type):
        return example
    lowered_name = field_name.strip().lower()
    if kind == "integer":
        return 1
    if kind == "numeric":
        return 1.25
    if kind == "boolean":
        return True
    if kind == "json":
        return {"validation_field": lowered_name}
    if kind == "timestamp":
        return "2025-01-01T00:00:00Z"
    if kind == "date":
        return "2025-01-01"
    if kind == "uuid":
        return f"{lowered_name or 'uuid'}-001"
    if lowered_name in {"state", "status"} or lowered_name.endswith("_state"):
        return "open"
    if lowered_name == "truth_state":
        return "provisional"
    if lowered_name.endswith("_ref"):
        return f"validation-{lowered_name}"
    if lowered_name.endswith("_key"):
        return f"validation-{lowered_name}"
    if lowered_name.endswith("_id") or lowered_name == "id":
        return f"{lowered_name}-001"
    return f"validation-{lowered_name}"


def build_modular_runtime_baseline_fixtures(
    *,
    p2_authority: dict[str, Any],
    openapi_spec: dict[str, Any],
    esp_text: str,
) -> dict[str, Any]:
    """Build validation-only baseline rows for accepted read/update/correction preconditions.

    The result is a mechanical projection. It never changes P2 durable command identity and
    deliberately does not seed ordinary create aggregates or replay/idempotency carriers.
    """
    operation_examples = _operation_examples(openapi_spec)
    operations = {
        str(row.get("operation_id") or "").strip(): dict(row)
        for row in p2_authority.get("operation_portfolio", [])
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
    aggregates = {
        str(row.get("aggregate_id") or "").strip(): dict(row)
        for row in p2_authority.get("aggregate_and_writer_decisions", [])
        if isinstance(row, dict) and str(row.get("aggregate_id") or "").strip()
    }
    durable = {
        str(row.get("operation_id") or "").strip(): dict(row)
        for row in p2_authority.get("durable_persistence_identity_decisions", [])
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
    data_decisions = [
        dict(row)
        for row in p2_authority.get("data_and_interaction_decisions", [])
        if isinstance(row, dict)
    ]
    schema = {
        str(row.get("table_name") or "").strip(): dict(row)
        for row in parse_schema_tables(esp_text)
        if str(row.get("table_name") or "").strip()
    }
    seed_reasons: dict[str, list[str]] = {}
    seed_examples: dict[str, dict[str, Any]] = {}
    create_response_examples: dict[str, dict[str, Any]] = {}
    create_replay_identity_fields: dict[str, set[str]] = {}
    for operation_id, operation in operations.items():
        persistence = durable.get(operation_id, {})
        command_kind = str(persistence.get("command_kind") or "").strip()
        persistence_mode = str(persistence.get("persistence_mode") or "").strip()
        if persistence_mode == "durable-write" and command_kind in {"insert", "upsert"}:
            aggregate_id = str(operation.get("aggregate_id") or "").strip()
            aggregate = aggregates.get(aggregate_id, {})
            table_name = str(aggregate.get("table_name") or "").strip()
            example = operation_examples.get(operation_id, {})
            response = example.get("response", {}) if isinstance(example.get("response"), dict) else {}
            if table_name and table_name in schema:
                if response:
                    create_response_examples.setdefault(table_name, {}).update(response)
                if str(persistence.get("idempotency_mode") or "").strip() == "replay-safe":
                    identity_fields = {
                        str(component).split(".", 1)[1]
                        for component in persistence.get("identity_components", [])
                        if isinstance(component, str) and component.startswith("request.") and "." in component
                    }
                    if identity_fields:
                        create_replay_identity_fields.setdefault(table_name, set()).update(identity_fields)

    for operation_id, operation in operations.items():
        persistence = durable.get(operation_id, {})
        command_kind = str(persistence.get("command_kind") or "").strip()
        persistence_mode = str(persistence.get("persistence_mode") or "").strip()
        carrier = persistence.get("durable_carrier", {})
        carrier = carrier if isinstance(carrier, dict) else {}
        carrier_kind = str(carrier.get("kind") or "").strip()
        example = operation_examples.get(operation_id, {})
        has_existing_resource_path = "{" in str(example.get("path") or "")
        requires_existing_aggregate = bool(
            command_kind in {"update", "select-one", "select-many"}
            or persistence_mode == "read-only"
            or (carrier_kind == "dedicated-record" and has_existing_resource_path)
        )
        if not requires_existing_aggregate:
            continue
        aggregate_id = str(operation.get("aggregate_id") or "").strip()
        aggregate = aggregates.get(aggregate_id, {})
        table_name = str(aggregate.get("table_name") or "").strip()
        if not table_name or table_name not in schema:
            continue
        reason = (
            "dedicated-correction-base-aggregate"
            if carrier_kind == "dedicated-record"
            else "read-update-positive-precondition"
        )
        seed_reasons.setdefault(table_name, []).append(f"{operation_id}:{reason}")
        request_example = example.get("request", {}) if isinstance(example.get("request"), dict) else {}
        response_example = example.get("response", {}) if isinstance(example.get("response"), dict) else {}
        merged = dict(request_example)
        # An update response is post-update state and must not be recycled as the
        # pre-update baseline. Read-only/select responses remain valid observations
        # of the seeded row and preserve existing behavior.
        if command_kind in {"select-one", "select-many"} or persistence_mode == "read-only":
            merged.update(response_example)
        seed_examples.setdefault(table_name, {}).update(merged)

    # Accepted table-backed read models are current-system/materialization seams even
    # when they intentionally have no aggregate/writer authority. Seed them only when
    # the accepted operation itself is read-only, and project only fields owned by the
    # accepted table schema.
    for decision in data_decisions:
        table_name = str(decision.get("table_name") or "").strip()
        aggregate_id = str(decision.get("aggregate_id") or "").strip()
        operation_id = str(decision.get("operation_id") or "").strip()
        fields = decision.get("fields", [])
        if not table_name or table_name not in schema or aggregate_id or not isinstance(fields, list) or not fields:
            continue
        persistence = durable.get(operation_id, {})
        persistence_mode = str(persistence.get("persistence_mode") or "").strip()
        command_kind = str(persistence.get("command_kind") or "").strip()
        if persistence_mode != "read-only" and command_kind not in {"select-one", "select-many"}:
            continue
        accepted_field_names = {
            str(field.get("name") or field.get("field_name") or "").strip()
            for field in fields
            if isinstance(field, dict) and str(field.get("name") or field.get("field_name") or "").strip()
        }
        if not accepted_field_names:
            continue
        example = operation_examples.get(operation_id, {})
        request_example = example.get("request", {}) if isinstance(example.get("request"), dict) else {}
        response_example = example.get("response", {}) if isinstance(example.get("response"), dict) else {}
        projected = {
            key: value
            for key, value in {**request_example, **response_example}.items()
            if key in accepted_field_names
        }
        seed_reasons.setdefault(table_name, []).append(f"{operation_id}:table-backed-read-model")
        seed_examples.setdefault(table_name, {}).update(projected)

    # Prefer the accepted create/insert outcome as the existing-row starting shape.
    # Only the create response is projected: request replay/idempotency keys are not
    # copied into the baseline, preventing false pre-service replay collisions.
    for table_name, response in create_response_examples.items():
        if table_name in seed_examples:
            seed_examples[table_name].update(response)

    rows: list[dict[str, Any]] = []
    for table_name in sorted(seed_reasons):
        table = schema[table_name]
        examples = dict(seed_examples.get(table_name, {}))
        replay_identity_fields = create_replay_identity_fields.get(table_name, set())
        field_type_by_name = {
            str(field.get("field_name") or "").strip(): str(field.get("data_type") or "").strip()
            for field in table.get("fields", [])
            if isinstance(field, dict) and str(field.get("field_name") or "").strip()
        }
        for field_name in replay_identity_fields:
            if field_name in examples:
                continue
            kind = _validation_data_type_kind(field_type_by_name.get(field_name, ""))
            if kind == "integer":
                examples[field_name] = 2
            elif kind == "numeric":
                examples[field_name] = 2.25
            elif kind == "boolean":
                examples[field_name] = False
            elif kind == "date":
                examples[field_name] = "2025-01-02"
            elif kind == "timestamp":
                examples[field_name] = "2025-01-02T00:00:00Z"
            else:
                examples[field_name] = f"validation-{field_name}-baseline"
        values: dict[str, Any] = {}
        uuid_fields: list[str] = []
        for field in table.get("fields", []):
            if not isinstance(field, dict):
                continue
            field_name = str(field.get("field_name") or "").strip()
            data_type = str(field.get("data_type") or "").strip()
            if not field_name:
                continue
            values[field_name] = _validation_field_value(
                field_name=field_name,
                data_type=data_type,
                examples=examples,
            )
            if data_type.lower() == "uuid":
                uuid_fields.append(field_name)
        rows.append(
            {
                "table": table_name,
                "values": values,
                "uuid_fields": sorted(uuid_fields),
                "reasons": sorted(set(seed_reasons[table_name])),
                "claim_ceiling": "validation-only baseline precondition; not product/runtime seed data",
            }
        )
    return {
        "schema_version": "wff.p3-modular-runtime-baseline-fixtures.v1",
        "rows": rows,
        "summary": {
            "row_count": len(rows),
            "table_count": len({row["table"] for row in rows}),
            "seeded_tables": [row["table"] for row in rows],
        },
        "claim_ceiling": "Derived validation baseline only; no product truth, production data, or durable-command authority.",
    }


def _authority_operation_field_types(authority: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    rows = authority.get("data_and_interaction_decisions", [])
    if not isinstance(rows, list):
        return result
    for row in rows:
        if not isinstance(row, dict):
            continue
        operation_id = str(row.get("operation_id") or "").strip()
        if not operation_id:
            continue
        operation_types = result.setdefault(operation_id, {})
        for field_group in ("fields", "request_fields", "result_fields"):
            fields = row.get(field_group, [])
            if not isinstance(fields, list):
                continue
            for field in fields:
                if not isinstance(field, dict):
                    continue
                name = str(field.get("name") or field.get("field_name") or "").strip()
                field_type = str(field.get("type") or "").strip().lower()
                if not name or not field_type:
                    continue
                prior = operation_types.get(name)
                operation_types[name] = field_type if prior in {None, field_type} else "mixed"
    return result


def _openapi_operation_field_types(operation: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    parameters = operation.get("parameters", [])
    if isinstance(parameters, list):
        for parameter in parameters:
            if not isinstance(parameter, dict):
                continue
            name = str(parameter.get("name") or "").strip()
            schema = parameter.get("schema", {})
            if not name or not isinstance(schema, dict):
                continue
            field_type = "uuid" if str(schema.get("format") or "").strip().lower() == "uuid" else str(schema.get("type") or "").strip().lower()
            if field_type:
                result[name] = field_type
    body_schema = (
        operation.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    properties = body_schema.get("properties", {}) if isinstance(body_schema, dict) else {}
    if isinstance(properties, dict):
        for name, schema in properties.items():
            if not isinstance(schema, dict):
                continue
            field_type = "uuid" if str(schema.get("format") or "").strip().lower() == "uuid" else str(schema.get("type") or "").strip().lower()
            if field_type:
                result[str(name)] = field_type
    return result


def ensure_backend_runtime_harness(
    output_dir: Path,
    *,
    openapi_spec: dict[str, Any],
    esp_text: str,
    p2_authority: dict[str, Any] | None = None,
) -> str:
    operation_specs: dict[str, dict[str, Any]] = {}
    authority = p2_authority or {}
    authority_field_types = _authority_operation_field_types(authority)
    schema_tables = [
        dict(row)
        for row in parse_schema_tables(esp_text)
        if str(row.get("table_name") or "").strip()
    ]
    table_candidates = sorted(str(row.get("table_name") or "").strip() for row in schema_tables)
    table_field_types = {
        str(row.get("table_name") or "").strip(): {
            str(field.get("field_name") or "").strip(): str(field.get("data_type") or "").strip()
            for field in row.get("fields", [])
            if isinstance(field, dict) and str(field.get("field_name") or "").strip()
        }
        for row in schema_tables
    }
    data_decisions = [
        dict(row)
        for row in authority.get("data_and_interaction_decisions", [])
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    ]
    durable_by_operation = {
        str(row.get("operation_id") or "").strip(): dict(row)
        for row in authority.get("durable_persistence_identity_decisions", [])
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
    persistence_hints: dict[str, dict[str, Any]] = {}
    for path, path_item in openapi_spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId") or "").strip()
            if not operation_id:
                continue
            request_example = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("example", {})
            )
            request_example = request_example if isinstance(request_example, dict) else {}
            parameter_examples = _operation_parameter_examples(operation)
            request_fields = list(parameter_examples) + [
                name for name in request_example if name not in parameter_examples
            ]
            failure_codes = _openapi_failure_codes(operation)
            failure_statuses = _openapi_failure_statuses(operation)
            failure_field_hints = {
                code: hint
                for code in failure_codes
                if _failure_field_hint_eligible(failure_statuses.get(code, 0), code)
                if (hint := _failure_field_hint(code, request_fields))
            }
            openapi_field_types = _openapi_operation_field_types(operation)
            field_types = dict(openapi_field_types)
            for field_name, field_type in authority_field_types.get(operation_id, {}).items():
                # Accepted P2 data/interaction authority owns the field type. OpenAPI
                # schemas may be mechanically inferred from placeholder examples, so
                # they are fallback projections rather than a peer semantic authority.
                # Genuine conflicts inside accepted P2 authority remain `mixed` and
                # therefore fail closed instead of being repaired from OpenAPI.
                field_types[field_name] = field_type
            operation_specs[operation_id] = {
                "operationId": operation_id,
                "method": str(method).upper(),
                "path": str(path),
                "requestExample": request_example,
                "parameterExamples": parameter_examples,
                "failureFieldHints": failure_field_hints,
                "fieldTypes": field_types,
            }
            response_fields: list[str] = []
            for response in operation.get("responses", {}).values():
                if not isinstance(response, dict):
                    continue
                example = response.get("content", {}).get("application/json", {}).get("example", {})
                data = example.get("data") if isinstance(example, dict) else None
                if isinstance(data, dict):
                    response_fields.extend(str(key) for key in data)
                elif isinstance(data, list) and data and isinstance(data[0], dict):
                    response_fields.extend(str(key) for key in data[0])
            durable_decision = durable_by_operation.get(operation_id, {})
            command_kind = str(durable_decision.get("command_kind") or "").strip()
            write_data_decision = next(
                (
                    row
                    for row in data_decisions
                    if str(row.get("operation_id") or "").strip() == operation_id
                    and str(row.get("table_name") or "").strip()
                    and isinstance(row.get("fields"), list)
                    and row.get("fields")
                ),
                {},
            )
            write_table = (
                str(write_data_decision.get("table_name") or "").strip()
                if command_kind in {"insert", "upsert"}
                else ""
            )
            insert_unique_constraints = [
                [str(field).strip() for field in group if str(field).strip()]
                for group in write_data_decision.get("unique_constraints", [])
                if isinstance(group, list) and any(str(field).strip() for field in group)
            ] if write_table else []
            persistence_hints[operation_id] = {
                "tableCandidates": table_candidates,
                "strictTableCandidates": (
                    table_candidates if str(method).upper() in {"POST", "PUT", "PATCH", "DELETE"} else []
                ),
                "idFieldCandidates": sorted(
                    {
                        field
                        for field in response_fields
                        if field.lower() == "id" or field.lower().endswith("_id") or field.endswith("Id")
                    }
                ),
                "tableFieldTypes": table_field_types,
                "positiveInsertWriteTable": write_table,
                "positiveInsertUniqueConstraints": insert_unique_constraints,
            }
    baseline_fixtures = build_modular_runtime_baseline_fixtures(
        p2_authority=authority,
        openapi_spec=openapi_spec,
        esp_text=esp_text,
    )
    rendered = load_script_text_asset(__file__, "backend-runtime-harness.ts.template")
    rendered = rendered.replace(
        "__WFF_MODULAR_OPERATION_SPECS__",
        json.dumps(operation_specs, ensure_ascii=False, sort_keys=True),
    ).replace(
        "__WFF_MODULAR_PERSISTENCE_HINTS__",
        json.dumps(persistence_hints, ensure_ascii=False, sort_keys=True),
    ).replace(
        "__WFF_MODULAR_BASELINE_FIXTURES__",
        json.dumps(baseline_fixtures, ensure_ascii=False, sort_keys=True),
    )
    target = output_dir / "tests" / "support" / "backend-runtime-harness.ts"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    fixture_path = output_dir / "tests" / "support" / "modular-runtime-baseline-fixtures.json"
    fixture_path.write_text(
        json.dumps(baseline_fixtures, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return str(target)


def _optional_test_scaffolder_module(module_name: str):
    try:
        return importlib.import_module(f"phase3.{module_name}")
    except ModuleNotFoundError as exc:
        if exc.name == f"phase3.{module_name}":
            return None
        raise


def _test_scaffolder_output_dir(args: tuple[object, ...], kwargs: dict[str, object]) -> Path:
    raw = kwargs.get("output_dir") if "output_dir" in kwargs else (args[1] if len(args) > 1 else ".")
    return Path(raw)


def _test_scaffolder_unavailable_summary(output_dir: Path, sidecar_id: str) -> dict[str, object]:
    return {
        "output_dir": str(output_dir),
        "files_created": [],
        "count": 0,
        "mode": "unavailable",
        "sidecar_id": sidecar_id,
        "reason": f"{sidecar_id}_sidecar_not_packaged",
    }


def scaffold_scenario_tests(*args: object, **kwargs: object) -> dict[str, object]:
    module = _optional_test_scaffolder_module("scenario_test_scaffolder")
    if module is None:
        return _test_scaffolder_unavailable_summary(
            _test_scaffolder_output_dir(args, kwargs),
            "scenario_test_scaffolder",
        )
    return module.scaffold_scenario_tests(*args, **kwargs)


def scaffold_replay_tests(*args: object, **kwargs: object) -> dict[str, object]:
    module = _optional_test_scaffolder_module("replay_test_scaffolder")
    if module is None:
        return _test_scaffolder_unavailable_summary(
            _test_scaffolder_output_dir(args, kwargs),
            "replay_test_scaffolder",
        )
    return module.scaffold_replay_tests(*args, **kwargs)


def run_impl_verification(
    *,
    mode: str,
    workspace_root: Path,
    phase2_root: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    target_root = output_dir or workspace_root
    target_root.mkdir(parents=True, exist_ok=True)
    generated_tests: dict[str, Any] = {}
    if mode == "generate-tests":
        if phase2_root is None:
            raise ValueError("--phase2-root is required for generate-tests mode")
        esp_text, stage_03_text, stage_04_text = load_phase2_source_texts(phase2_root)
        spec = build_openapi_spec(parse_api_endpoint_rows(esp_text), title="Phase-3 Verification", version="0.1.0")
        runtime_harness_path = ensure_backend_runtime_harness(
            target_root,
            openapi_spec=spec,
            esp_text=esp_text,
            p2_authority=_load_p2_authority(phase2_root),
        )
        runtime_baseline_fixture_path = target_root / "tests" / "support" / "modular-runtime-baseline-fixtures.json"
        runtime_baseline_fixture = json.loads(runtime_baseline_fixture_path.read_text(encoding="utf-8"))
        reserved_rows = (
            [dict(row) for row in runtime_baseline_fixture.get("rows", []) if isinstance(row, dict)]
            if isinstance(runtime_baseline_fixture, dict)
            else []
        )
        generated_tests = {
            "runtime_harness_path": runtime_harness_path,
            "runtime_baseline_fixture_path": str(runtime_baseline_fixture_path),
            "schema_summary": scaffold_schema_tests(esp_text, target_root / "tests" / "schema"),
            "sql_summary": scaffold_sql_tests(
                esp_text,
                target_root / "tests" / "sql",
                reserved_rows=reserved_rows,
            ),
            "contract_summary": scaffold_contract_tests(
                spec,
                target_root / "tests" / "contracts",
                external_auth_required=explicit_external_auth_requirement(esp_text),
                synthetic_rollback_probe_supported=False,
                audit_logging_required=False,
            ),
            "scenario_summary": scaffold_scenario_tests(
                stage_03_text,
                target_root / "tests" / "scenarios",
                esp_text=esp_text,
                openapi_spec=spec,
            ),
            "replay_summary": scaffold_replay_tests(
                stage_04_text,
                target_root / "tests" / "replays",
                esp_text=esp_text,
                stage_03_text=stage_03_text,
                openapi_spec=spec,
            ),
        }
    report = {
        "artifact_kind": "phase3-impl-verification-report",
        "quality_gate": "pass",
        "mode": mode,
        "workspace_root": str(workspace_root),
        "phase2_root": str(phase2_root) if phase2_root else "",
        "generated_tests": generated_tests,
        "claim_ceiling": (
            "verify-only structural report; runtime truth requires selected evidence family execution"
            if mode == "verify"
            else "test generation report; generated tests still require execution and review"
        ),
    }
    write_json(target_root / "impl-verification-report.json", report)
    return report
