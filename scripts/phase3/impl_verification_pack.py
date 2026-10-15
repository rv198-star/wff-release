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


def _failure_field_hint(
    error_code: str,
    request_fields: list[str],
    *,
    preferred_user_input_fields: list[str] | None = None,
) -> str:
    """Choose a bounded negative-test field without depending on serialized key order.

    Explicit P2 interaction authority may identify user-entered fields separately
    from auth/session or workflow-context inputs. Generic validation negatives
    should prefer those user fields when no stronger semantic match exists.
    """
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
        if "transition" in tokens and normalized in {"state", "status", "target_state", "target_status"}:
            score += 40
        if ("confirmation" in tokens or "confirmed" in tokens) and "confirm" in normalized:
            score += 20
        if "evidence" in tokens and "evidence" in normalized:
            score += 20
        if score > 0:
            scored.append((score, -index, field))
    if scored:
        return max(scored)[2]
    if code in {"validation_failed", "invalid_input", "invalid_request", "invalid_photo", "invalid_trace"}:
        preferred = [field for field in (preferred_user_input_fields or []) if field in request_fields]
        if preferred:
            return preferred[0]
        implicit_context_fields = {"tenant_id", "actor_id", "subject_id", "session_id", "trace_id", "request_id"}
        business_fields = [field for field in request_fields if field.casefold() not in implicit_context_fields]
        return business_fields[0] if business_fields else request_fields[0]
    return ""


def _operation_required_request_fields(operation: dict[str, Any]) -> list[str]:
    result: list[str] = []
    parameters = operation.get("parameters", [])
    if isinstance(parameters, list):
        for parameter in parameters:
            if not isinstance(parameter, dict) or parameter.get("required") is not True:
                continue
            name = str(parameter.get("name") or "").strip()
            if name and name not in result:
                result.append(name)
    body_schema = (
        operation.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    required = body_schema.get("required", []) if isinstance(body_schema, dict) else []
    if isinstance(required, list):
        for raw in required:
            name = str(raw).strip()
            if name and name not in result:
                result.append(name)
    return result


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
    if lowered == "array" or lowered.endswith("[]"):
        return "array"
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
    if kind == "array":
        return isinstance(value, list)
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
    if kind == "array":
        return [f"validation-{lowered_name}-item"]
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


def _accepted_p3_runtime_schema_fields(p3_authority: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    """Collect accepted P3-only schema fields used by runtime validation."""
    result: dict[str, dict[str, str]] = {}
    plan = (p3_authority or {}).get("exact_realization_plan", [])
    if not isinstance(plan, list):
        return result
    for realization in plan:
        if not isinstance(realization, dict):
            continue
        runtime = realization.get("runtime_realization")
        if not isinstance(runtime, dict):
            continue
        additions = runtime.get("schema_field_additions", {})
        if isinstance(additions, dict):
            for raw_table, raw_fields in additions.items():
                table = str(raw_table or "").strip()
                if not table or not isinstance(raw_fields, list):
                    continue
                target = result.setdefault(table, {})
                for raw_field in raw_fields:
                    if not isinstance(raw_field, dict):
                        continue
                    field_name = str(raw_field.get("field_name") or "").strip()
                    data_type = str(raw_field.get("data_type") or "").strip()
                    if field_name and data_type:
                        target[field_name] = data_type
        migration_sql = str(runtime.get("migration_sql") or "")
        for alter in re.finditer(
            r"\bALTER\s+TABLE\s+[\"`]?([A-Za-z_][A-Za-z0-9_]*)[\"`]?\s+(.*?);",
            migration_sql,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            table = alter.group(1)
            target = result.setdefault(table, {})
            for column in re.finditer(
                r"\bADD\s+COLUMN(?:\s+IF\s+NOT\s+EXISTS)?\s+[\"`]?([A-Za-z_][A-Za-z0-9_]*)[\"`]?\s+([A-Za-z][A-Za-z0-9_]*(?:\s*\([^)]*\))?)",
                alter.group(2),
                flags=re.IGNORECASE,
            ):
                target[column.group(1)] = column.group(2).strip()
    return result


def build_modular_runtime_baseline_fixtures(
    *,
    p2_authority: dict[str, Any],
    openapi_spec: dict[str, Any],
    esp_text: str,
    p3_authority: dict[str, Any] | None = None,
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
    for table_name, fields in _accepted_p3_runtime_schema_fields(p3_authority).items():
        table = schema.get(table_name)
        if not isinstance(table, dict):
            continue
        table_fields = table.setdefault("fields", [])
        if not isinstance(table_fields, list):
            continue
        known = {
            str(field.get("field_name") or "").strip()
            for field in table_fields
            if isinstance(field, dict) and str(field.get("field_name") or "").strip()
        }
        for field_name, data_type in fields.items():
            if field_name not in known:
                table_fields.append({"field_name": field_name, "data_type": data_type, "constraints": "P3-runtime-authority"})
                known.add(field_name)
    states_by_aggregate = {
        str(row.get("aggregate_id") or "").strip(): [str(item).strip() for item in row.get("states", []) if str(item).strip()]
        for row in p2_authority.get("state_invariant_policy_failure_decisions", [])
        if isinstance(row, dict) and str(row.get("aggregate_id") or "").strip()
    }
    aggregate_id_by_table = {
        str(row.get("table_name") or "").strip(): str(row.get("aggregate_id") or "").strip()
        for row in p2_authority.get("aggregate_and_writer_decisions", [])
        if isinstance(row, dict) and str(row.get("table_name") or "").strip()
    }
    accepted_literals_by_aggregate: dict[str, dict[str, list[str]]] = {}
    failure_codes_by_operation: dict[str, str] = {}
    for decision in data_decisions:
        operation_id = str(decision.get("operation_id") or "").strip()
        if operation_id and decision.get("failure_codes"):
            failure_codes_by_operation[operation_id] = str(decision.get("failure_codes") or "")
        aggregate_id = str(decision.get("aggregate_id") or "").strip()
        if not aggregate_id:
            continue
        fields = decision.get("fields", [])
        if not isinstance(fields, list):
            continue
        target = accepted_literals_by_aggregate.setdefault(aggregate_id, {})
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_name = str(field.get("name") or field.get("field_name") or "").strip()
            literals = _constraint_literal_values(field.get("constraint") or field.get("constraints"))
            if field_name and literals:
                target[field_name] = literals

    seed_reasons: dict[str, list[str]] = {}
    seed_examples: dict[str, dict[str, Any]] = {}
    create_response_examples: dict[str, dict[str, Any]] = {}
    create_replay_identity_fields: dict[str, set[str]] = {}
    create_replay_identity_examples: dict[str, dict[str, Any]] = {}
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
                        if "dependency_unavailable" not in failure_codes_by_operation.get(operation_id, ""):
                            request = example.get("request", {}) if isinstance(example.get("request"), dict) else {}
                            selected = {field: request[field] for field in identity_fields if field in request}
                            if selected:
                                create_replay_identity_examples.setdefault(table_name, {}).update(selected)

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

    # Durable-write validation may depend on an existing aggregate whose identity
    # is carried as a request `*_id` rather than an explicit SQL FK. When that
    # request identity exactly matches another accepted table primary key, seed the
    # dependency row if the field is required or explicitly present in the accepted
    # positive request example. This remains validation-only dependency closure and
    # does not invent product seed data or a business-operation ordering edge.
    request_fields_by_operation: dict[str, dict[str, bool]] = {}
    for decision in data_decisions:
        operation_id = str(decision.get("operation_id") or "").strip()
        request_fields = decision.get("request_fields", [])
        if not operation_id or not isinstance(request_fields, list):
            continue
        request_fields_by_operation[operation_id] = {
            str(field.get("name") or "").strip(): field.get("nullable") is not False
            for field in request_fields
            if isinstance(field, dict) and str(field.get("name") or "").strip()
        }
    primary_table_by_field: dict[str, str] = {}
    for table_name, table in schema.items():
        for field in table.get("fields", []):
            if not isinstance(field, dict):
                continue
            field_name = str(field.get("field_name") or "").strip()
            constraints = str(field.get("constraints") or field.get("constraint") or "")
            if field_name and "pk" in constraints.casefold():
                primary_table_by_field.setdefault(field_name, table_name)

    for operation_id, operation in operations.items():
        persistence = durable.get(operation_id, {})
        if str(persistence.get("persistence_mode") or "").strip() != "durable-write":
            continue
        aggregate = aggregates.get(str(operation.get("aggregate_id") or "").strip(), {})
        own_table = str(aggregate.get("table_name") or "").strip()
        example = operation_examples.get(operation_id, {})
        request_example = example.get("request", {}) if isinstance(example.get("request"), dict) else {}
        for field_name, nullable in request_fields_by_operation.get(operation_id, {}).items():
            dependency_table = primary_table_by_field.get(field_name, "")
            if not dependency_table or dependency_table == own_table:
                continue
            if nullable and field_name not in request_example:
                continue
            seed_reasons.setdefault(dependency_table, []).append(
                f"{operation_id}:{field_name}-request-identity-positive-precondition"
            )
            if field_name in request_example:
                seed_examples.setdefault(dependency_table, {})[field_name] = request_example[field_name]

    # A seeded validation row must not point at an absent FK parent. Expand the
    # baseline seed set through schema-declared FK parents before materializing
    # rows. This is validation-only dependency closure: it does not seed product
    # data or invent an execution edge between business operations.
    changed = True
    while changed:
        changed = False
        for table_name in list(seed_reasons):
            table = schema.get(table_name, {})
            for field in table.get("fields", []):
                if not isinstance(field, dict):
                    continue
                constraints = str(field.get("constraints") or field.get("constraint") or "")
                match = re.search(r"\bfk\s+([A-Za-z0-9_]+)(?:\.([A-Za-z0-9_]+))?", constraints, re.IGNORECASE)
                if not match:
                    continue
                parent_table = match.group(1)
                if parent_table not in schema or parent_table in seed_reasons:
                    continue
                seed_reasons[parent_table] = [f"{table_name}:fk-parent-positive-precondition"]
                changed = True

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
        aggregate_id = aggregate_id_by_table.get(table_name, "")
        aggregate_states = states_by_aggregate.get(aggregate_id, [])
        accepted_literals = accepted_literals_by_aggregate.get(aggregate_id, {})
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
            elif kind == "array":
                examples[field_name] = [f"validation-{field_name}-baseline-item"]
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
            constraints = str(field.get("constraints") or field.get("constraint") or "")
            if field_name in accepted_literals:
                examples[field_name] = accepted_literals[field_name][0]
            elif "accepted-state-set" in constraints.casefold() and aggregate_states:
                examples[field_name] = _preferred_validation_state(aggregate_states, field_name=field_name)
            elif "actionability" in field_name.casefold() and aggregate_states:
                examples[field_name] = _preferred_validation_state(aggregate_states, field_name=field_name)
            if "provisional" in field_name.casefold() and _validation_data_type_kind(data_type) == "boolean":
                examples[field_name] = False
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

    rows_by_table = {str(row["table"]): row for row in rows}
    for table_name, row in rows_by_table.items():
        table = schema.get(table_name, {})
        for field in table.get("fields", []):
            if not isinstance(field, dict):
                continue
            field_name = str(field.get("field_name") or "").strip()
            constraints = str(field.get("constraints") or field.get("constraint") or "")
            match = re.search(r"\bfk\s+([A-Za-z0-9_]+)(?:\.([A-Za-z0-9_]+))?", constraints, re.IGNORECASE)
            if not field_name or not match:
                continue
            parent_table = match.group(1)
            parent_row = rows_by_table.get(parent_table)
            parent_schema = schema.get(parent_table, {})
            if not parent_row or not isinstance(parent_row.get("values"), dict):
                continue
            parent_field = match.group(2) or field_name
            if parent_field not in parent_row["values"]:
                parent_field = next(
                    (
                        str(candidate.get("field_name") or "").strip()
                        for candidate in parent_schema.get("fields", [])
                        if isinstance(candidate, dict) and "pk" in str(candidate.get("constraints") or "").casefold()
                    ),
                    "",
                )
            if parent_field and parent_field in parent_row["values"]:
                row["values"][field_name] = parent_row["values"][parent_field]
    operation_validation_values: dict[str, dict[str, Any]] = {}
    p3_rows = (
        [dict(row) for row in (p3_authority or {}).get("exact_realization_plan", []) if isinstance(row, dict)]
        if isinstance((p3_authority or {}).get("exact_realization_plan", []), list)
        else []
    )
    primary_row_by_table = {str(row["table"]): row for row in rows if isinstance(row.get("values"), dict)}
    for realization in p3_rows:
        operation_id = str(realization.get("operation_id") or "").strip()
        runtime_realization = realization.get("runtime_realization")
        runtime_realization = runtime_realization if isinstance(runtime_realization, dict) else {}
        preconditions = runtime_realization.get("validation_preconditions", [])
        preconditions = list(preconditions) if isinstance(preconditions, list) else []
        persistence = runtime_realization.get("persistence_realization")
        persistence = persistence if isinstance(persistence, dict) else {}
        steps = persistence.get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, dict) or not isinstance(step.get("validation_precondition_values"), dict):
                    continue
                values = dict(step.get("validation_precondition_values") or {})
                if not values:
                    continue
                preconditions.append(
                    {
                        "precondition_id": f"persistence-step:{str(step.get('step_id') or '').strip() or 'unnamed'}",
                        "table": str(step.get("table") or "").strip(),
                        "values": values,
                    }
                )
        if not operation_id:
            continue
        for index, precondition in enumerate(preconditions, start=1):
            if not isinstance(precondition, dict):
                continue
            precondition_id = str(precondition.get("precondition_id") or "").strip()
            table_name = str(precondition.get("table") or "").strip()
            explicit_values = precondition.get("values")
            if not precondition_id or table_name not in schema or not isinstance(explicit_values, dict) or not explicit_values:
                continue
            table = schema[table_name]
            known_fields = {
                str(field.get("field_name") or "").strip(): str(field.get("data_type") or "").strip()
                for field in table.get("fields", [])
                if isinstance(field, dict) and str(field.get("field_name") or "").strip()
            }
            unknown_fields = sorted(set(explicit_values) - set(known_fields))
            if unknown_fields:
                raise ValueError(
                    f"P3 validation precondition {operation_id}:{precondition_id} references unknown fields: {', '.join(unknown_fields)}"
                )
            incompatible_fields = sorted(
                field_name
                for field_name, value in explicit_values.items()
                if not _validation_example_is_compatible(value, data_type=known_fields[field_name])
            )
            if incompatible_fields:
                raise ValueError(
                    f"P3 validation precondition {operation_id}:{precondition_id} has schema-incompatible values: {', '.join(incompatible_fields)}"
                )
            base = primary_row_by_table.get(table_name, {})
            values = dict(base.get("values", {})) if isinstance(base.get("values"), dict) else {}
            if not values:
                values = {
                    field_name: _validation_field_value(field_name=field_name, data_type=data_type, examples={})
                    for field_name, data_type in known_fields.items()
                }
            values.update(explicit_values)
            pk_fields = [
                str(field.get("field_name") or "").strip()
                for field in table.get("fields", [])
                if isinstance(field, dict)
                and str(field.get("field_name") or "").strip()
                and "pk" in str(field.get("constraints") or field.get("constraint") or "").casefold()
            ]
            for pk_field in pk_fields:
                if pk_field not in explicit_values:
                    values[pk_field] = f"{pk_field}-{operation_id}-{index}"
            for field in table.get("fields", []):
                if not isinstance(field, dict):
                    continue
                field_name = str(field.get("field_name") or "").strip()
                constraints = str(field.get("constraints") or field.get("constraint") or "")
                match = re.search(r"\bfk\s+([A-Za-z0-9_]+)(?:\.([A-Za-z0-9_]+))?", constraints, re.IGNORECASE)
                if not field_name or not match or field_name in explicit_values:
                    continue
                parent_table = match.group(1)
                parent_row = primary_row_by_table.get(parent_table, {})
                parent_schema = schema.get(parent_table, {})
                parent_values = parent_row.get("values", {}) if isinstance(parent_row.get("values"), dict) else {}
                parent_field = match.group(2) or field_name
                if parent_field not in parent_values:
                    parent_field = next(
                        (
                            str(candidate.get("field_name") or "").strip()
                            for candidate in parent_schema.get("fields", [])
                            if isinstance(candidate, dict) and "pk" in str(candidate.get("constraints") or "").casefold()
                        ),
                        "",
                    )
                if parent_field and parent_field in parent_values:
                    values[field_name] = parent_values[parent_field]
            uuid_fields = sorted(
                field_name for field_name, data_type in known_fields.items() if data_type.casefold() == "uuid"
            )
            rows.append(
                {
                    "table": table_name,
                    "values": values,
                    "uuid_fields": uuid_fields,
                    "reasons": [f"{operation_id}:p3-validation-precondition:{precondition_id}"],
                    "bypass_triggers": True,
                    "claim_ceiling": "P3-authority-bound validation precondition only; not product/runtime seed data",
                }
            )
            validation_values = operation_validation_values.setdefault(operation_id, {})
            for field_name in pk_fields:
                if field_name in values:
                    validation_values[field_name] = values[field_name]
            for field_name, value in explicit_values.items():
                validation_values.setdefault(field_name, value)

    default_tenant_id = next(
        (
            row.get("values", {}).get("tenant_id")
            for row in rows
            if isinstance(row.get("values"), dict) and row.get("values", {}).get("tenant_id") not in {None, ""}
        ),
        "",
    )
    return {
        "schema_version": "wff.p3-modular-runtime-baseline-fixtures.v1",
        "rows": rows,
        "operation_validation_values": operation_validation_values,
        "default_tenant_id": default_tenant_id,
        "summary": {
            "row_count": len(rows),
            "table_count": len({row["table"] for row in rows}),
            "seeded_tables": [row["table"] for row in rows],
            **(
                {"p3_validation_precondition_row_count": sum(1 for row in rows if row.get("bypass_triggers") is True)}
                if any(row.get("bypass_triggers") is True for row in rows)
                else {}
            ),
        },
        "claim_ceiling": "Derived validation baseline only; no product truth, production data, or durable-command authority.",
    }


def _constraint_literal_values(value: Any) -> list[str]:
    text = str(value or "").strip()
    if "|" in text:
        values = [item.strip() for item in text.split("|") if item.strip()]
    elif re.fullmatch(r"[A-Za-z0-9._-]+(?:\s+or\s+[A-Za-z0-9._-]+)+", text, flags=re.IGNORECASE):
        values = [item.strip() for item in re.split(r"\s+or\s+", text, flags=re.IGNORECASE) if item.strip()]
    else:
        return []
    if len(values) < 2:
        return []
    if any(len(item) > 64 or not re.fullmatch(r"[A-Za-z0-9._-]+", item) for item in values):
        return []
    return values


def _preferred_validation_state(states: list[str], *, field_name: str) -> str:
    clean = [str(item).strip() for item in states if str(item).strip()]
    if not clean:
        return ""
    lowered_name = field_name.strip().lower()
    if "actionability" in lowered_name:
        match = next((item for item in clean if item.casefold() == "actionable"), "")
        if match:
            return match
    if "registration" in lowered_name:
        match = next((item for item in clean if item.casefold() == "registered"), "")
        if match:
            return match
    undesirable = ("fail", "error", "invalid", "blocked", "review-bound", "paused")
    return next((item for item in clean if not any(token in item.casefold() for token in undesirable)), clean[0])


def _authority_operation_validation_values(authority: dict[str, Any]) -> dict[str, dict[str, Any]]:
    operation_types = _authority_operation_field_types(authority)
    operations = {
        str(row.get("operation_id") or "").strip(): dict(row)
        for row in authority.get("operation_portfolio", [])
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
    states_by_aggregate = {
        str(row.get("aggregate_id") or "").strip(): [str(item).strip() for item in row.get("states", []) if str(item).strip()]
        for row in authority.get("state_invariant_policy_failure_decisions", [])
        if isinstance(row, dict) and str(row.get("aggregate_id") or "").strip()
    }
    data_rows = [row for row in authority.get("data_and_interaction_decisions", []) if isinstance(row, dict)]
    constraints_by_aggregate: dict[str, dict[str, list[str]]] = {}
    for row in data_rows:
        aggregate_id = str(row.get("aggregate_id") or "").strip()
        if not aggregate_id:
            continue
        fields = row.get("fields", [])
        if not isinstance(fields, list):
            continue
        target = constraints_by_aggregate.setdefault(aggregate_id, {})
        for field in fields:
            if not isinstance(field, dict):
                continue
            name = str(field.get("name") or field.get("field_name") or "").strip()
            literals = _constraint_literal_values(field.get("constraint") or field.get("constraints"))
            if name and literals:
                target[name] = literals

    result: dict[str, dict[str, Any]] = {}
    for operation_id, operation in operations.items():
        aggregate_id = str(operation.get("aggregate_id") or "").strip()
        field_types = operation_types.get(operation_id, {})
        values: dict[str, Any] = {}
        for field_name, literals in constraints_by_aggregate.get(aggregate_id, {}).items():
            if field_name in field_types and literals:
                values[field_name] = literals[0]
        states = states_by_aggregate.get(aggregate_id, [])
        for field_name in field_types:
            lowered = field_name.casefold()
            if lowered in {"target_status", "target_state"} and states:
                values[field_name] = states[1] if len(states) > 1 else states[0]
        if values:
            result[operation_id] = values
    return result


def _authority_operation_field_types(authority: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Project accepted operation-boundary types without conflating storage representation.

    ``request_fields`` / ``result_fields`` describe the contract boundary consumed by the
    runtime harness. ``fields`` may describe the durable aggregate representation and can
    legitimately differ (for example an API string identifier backed by a UUID column).
    Boundary types therefore win when present; durable fields remain a fallback only.
    Conflicts inside the same boundary authority still fail closed as ``mixed``.
    """

    boundary_types: dict[str, dict[str, str]] = {}
    storage_fallback_types: dict[str, dict[str, str]] = {}
    rows = authority.get("data_and_interaction_decisions", [])
    if not isinstance(rows, list):
        return {}

    def merge_field(target: dict[str, str], field: dict[str, Any]) -> None:
        name = str(field.get("name") or field.get("field_name") or "").strip()
        field_type = str(field.get("type") or "").strip().lower()
        if name and field_type:
            prior = target.get(name)
            target[name] = field_type if prior in {None, field_type} else "mixed"
        item_fields = field.get("item_fields", [])
        if not isinstance(item_fields, list):
            return
        for item_field in item_fields:
            if not isinstance(item_field, dict):
                continue
            item_name = str(item_field.get("name") or item_field.get("field_name") or "").strip()
            item_type = str(item_field.get("type") or "").strip().lower()
            if not item_name or not item_type:
                continue
            item_prior = target.get(item_name)
            target[item_name] = item_type if item_prior in {None, item_type} else "mixed"

    for row in rows:
        if not isinstance(row, dict):
            continue
        operation_id = str(row.get("operation_id") or "").strip()
        if not operation_id:
            continue
        boundary = boundary_types.setdefault(operation_id, {})
        storage = storage_fallback_types.setdefault(operation_id, {})
        for field_group in ("request_fields", "result_fields"):
            fields = row.get(field_group, [])
            if isinstance(fields, list):
                for field in fields:
                    if isinstance(field, dict):
                        merge_field(boundary, field)
        fields = row.get("fields", [])
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, dict):
                    merge_field(storage, field)

    result: dict[str, dict[str, str]] = {}
    for operation_id in set(boundary_types) | set(storage_fallback_types):
        result[operation_id] = {
            **storage_fallback_types.get(operation_id, {}),
            **boundary_types.get(operation_id, {}),
        }
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
    p3_authority: dict[str, Any] | None = None,
) -> str:
    operation_specs: dict[str, dict[str, Any]] = {}
    authority = p2_authority or {}
    authority_field_types = _authority_operation_field_types(authority)
    authority_validation_values = _authority_operation_validation_values(authority)
    terminal_access_exposure_by_operation = {
        str(row.get("operation_id") or "").strip(): str((row.get("terminal_access") or {}).get("exposure") or "").strip()
        for row in authority.get("operation_portfolio", [])
        if isinstance(row, dict)
        and str(row.get("operation_id") or "").strip()
        and isinstance(row.get("terminal_access"), dict)
    }
    terminal_roles_by_operation = {
        str(row.get("operation_id") or "").strip(): [
            str(role).strip()
            for role in ((row.get("terminal_access") or {}).get("allowed_roles", []) if isinstance(row.get("terminal_access"), dict) else [])
            if str(role).strip()
        ]
        for row in authority.get("operation_portfolio", [])
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
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
    all_data_decisions = [
        dict(row)
        for row in authority.get("data_and_interaction_decisions", [])
        if isinstance(row, dict)
    ]
    data_decisions = [
        row for row in all_data_decisions if str(row.get("operation_id") or "").strip()
    ]
    durable_by_operation = {
        str(row.get("operation_id") or "").strip(): dict(row)
        for row in authority.get("durable_persistence_identity_decisions", [])
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
    operation_authority_by_id = {
        str(row.get("operation_id") or "").strip(): dict(row)
        for row in authority.get("operation_portfolio", [])
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
    aggregate_authority_by_id = {
        str(row.get("aggregate_id") or "").strip(): dict(row)
        for row in authority.get("aggregate_and_writer_decisions", [])
        if isinstance(row, dict) and str(row.get("aggregate_id") or "").strip()
    }
    explicit_user_input_fields_by_operation: dict[str, list[str]] = {}
    authority_request_fields_by_operation: dict[str, list[str]] = {}
    authority_required_fields_by_operation: dict[str, list[str]] = {}
    for row in data_decisions:
        operation_id = str(row.get("operation_id") or "").strip()
        if not operation_id:
            continue
        request_fields = row.get("request_fields", [])
        if isinstance(request_fields, list):
            accepted_fields = [
                str(field.get("name") or "").strip()
                for field in request_fields
                if isinstance(field, dict) and str(field.get("name") or "").strip()
            ]
            if accepted_fields:
                authority_request_fields_by_operation[operation_id] = accepted_fields
            required_fields = [
                str(field.get("name") or "").strip()
                for field in request_fields
                if isinstance(field, dict)
                and str(field.get("name") or "").strip()
                and field.get("nullable") is False
            ]
            if required_fields:
                authority_required_fields_by_operation[operation_id] = required_fields
        fields: list[str] = []
        bindings = row.get("interaction_bindings", [])
        if not isinstance(bindings, list):
            continue
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            mappings = binding.get("request_field_mapping", [])
            if not isinstance(mappings, list):
                continue
            for mapping in mappings:
                if not isinstance(mapping, dict) or str(mapping.get("source") or "").strip() != "user-input":
                    continue
                field = str(mapping.get("contract_field") or "").strip()
                if field and field not in fields:
                    fields.append(field)
        explicit_user_input_fields_by_operation[operation_id] = fields
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
            required_request_fields = authority_required_fields_by_operation.get(operation_id) or _operation_required_request_fields(operation)
            accepted_request_fields = authority_request_fields_by_operation.get(operation_id, [])
            hint_request_fields = (
                [field for field in request_fields if field in accepted_request_fields]
                or [field for field in request_fields if field in required_request_fields]
                or request_fields
            )
            failure_codes = _openapi_failure_codes(operation)
            failure_statuses = _openapi_failure_statuses(operation)
            failure_field_hints = {
                code: hint
                for code in failure_codes
                if _failure_field_hint_eligible(failure_statuses.get(code, 0), code)
                if (
                    hint := _failure_field_hint(
                        code,
                        hint_request_fields,
                        preferred_user_input_fields=explicit_user_input_fields_by_operation.get(operation_id, []),
                    )
                )
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
                "validationFieldValues": authority_validation_values.get(operation_id, {}),
                "terminalRoles": terminal_roles_by_operation.get(operation_id, []),
                "terminalAccessExposure": terminal_access_exposure_by_operation.get(operation_id, ""),
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
            operation_authority = operation_authority_by_id.get(operation_id, {})
            aggregate_id = str(operation_authority.get("aggregate_id") or "").strip()
            aggregate_authority = aggregate_authority_by_id.get(aggregate_id, {})
            aggregate_table = str(aggregate_authority.get("table_name") or "").strip()
            write_data_decision = next(
                (
                    row
                    for row in all_data_decisions
                    if str(row.get("aggregate_id") or "").strip() == aggregate_id
                    and isinstance(row.get("fields"), list)
                    and row.get("fields")
                ),
                {},
            )
            if not write_data_decision:
                write_data_decision = next(
                    (
                        row
                        for row in all_data_decisions
                        if str(row.get("operation_id") or "").strip() == operation_id
                        and str(row.get("table_name") or "").strip()
                        and isinstance(row.get("fields"), list)
                        and row.get("fields")
                    ),
                    {},
                )
            write_table = aggregate_table if command_kind in {"insert", "upsert"} and aggregate_table in table_field_types else ""
            if not write_table and command_kind in {"insert", "upsert"}:
                write_table = str(write_data_decision.get("table_name") or "").strip()
            insert_unique_constraints = [
                [str(field).strip() for field in group if str(field).strip()]
                for group in write_data_decision.get("unique_constraints", [])
                if isinstance(group, list) and any(str(field).strip() for field in group)
            ] if write_table else []
            schema_row = next((row for row in schema_tables if str(row.get("table_name") or "").strip() == write_table), {})
            pk_fields = [
                str(field.get("field_name") or "").strip()
                for field in schema_row.get("fields", [])
                if isinstance(field, dict) and "pk" in str(field.get("constraints") or "").casefold()
            ]
            positive_insert_identity_constraints = list(insert_unique_constraints)
            for pk_field in pk_fields:
                if pk_field and [pk_field] not in positive_insert_identity_constraints:
                    positive_insert_identity_constraints.append([pk_field])
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
                "positiveInsertIdentityConstraints": positive_insert_identity_constraints,
            }
    baseline_fixtures = build_modular_runtime_baseline_fixtures(
        p2_authority=authority,
        openapi_spec=openapi_spec,
        esp_text=esp_text,
        p3_authority=p3_authority,
    )
    p3_validation_values = baseline_fixtures.get("operation_validation_values", {})
    if isinstance(p3_validation_values, dict):
        for operation_id, values in p3_validation_values.items():
            if operation_id not in operation_specs or not isinstance(values, dict):
                continue
            merged_values = dict(operation_specs[operation_id].get("validationFieldValues", {}))
            merged_values.update(values)
            operation_specs[operation_id]["validationFieldValues"] = merged_values
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
    p3_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target_root = output_dir or workspace_root
    target_root.mkdir(parents=True, exist_ok=True)
    generated_tests: dict[str, Any] = {}
    if mode == "generate-tests":
        if phase2_root is None:
            raise ValueError("--phase2-root is required for generate-tests mode")
        esp_text, stage_03_text, stage_04_text = load_phase2_source_texts(phase2_root)
        spec = build_openapi_spec(parse_api_endpoint_rows(esp_text), title="Phase-3 Verification", version="0.1.0")
        p2_authority = _load_p2_authority(phase2_root)
        runtime_harness_path = ensure_backend_runtime_harness(
            target_root,
            openapi_spec=spec,
            esp_text=esp_text,
            p2_authority=p2_authority,
            p3_authority=p3_authority,
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
                p2_authority=p2_authority,
            ),
            "replay_summary": scaffold_replay_tests(
                stage_04_text,
                target_root / "tests" / "replays",
                esp_text=esp_text,
                stage_03_text=stage_03_text,
                openapi_spec=spec,
                p2_authority=p2_authority,
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
