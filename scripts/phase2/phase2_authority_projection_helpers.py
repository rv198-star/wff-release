"""Focused helpers for projecting accepted P2 Agentic authority into canonical outputs.

This module keeps exact interaction-binding and example-value projection out of the
large canonical stage renderer. It does not create architecture truth; callers must
pass the already accepted architecture model through the Phase-2 runtime context.
"""

from __future__ import annotations


def architecture_authority_model(context: dict[str, object]) -> dict[str, object]:
    model = context.get("agentic_architecture_model")
    return model if isinstance(model, dict) else {}


def authority_operation_data_decision(context: dict[str, object], operation_id: str) -> dict[str, object]:
    for row in architecture_authority_model(context).get("data_decisions", []):
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip() == operation_id:
            return row
    return {}


def authority_operation_persistence_decision(context: dict[str, object], operation_id: str) -> dict[str, object]:
    for row in architecture_authority_model(context).get("durable_persistence_identity", []):
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip() == operation_id:
            return row
    return {}


def authority_operation_supports_concurrent_conflict(context: dict[str, object], operation_id: str) -> bool:
    """Return true only when accepted persistence semantics actually reject a competing write."""
    decision = authority_operation_persistence_decision(context, operation_id)
    if not decision:
        return False
    persistence_mode = str(decision.get("persistence_mode") or "").strip()
    command_kind = str(decision.get("command_kind") or "").strip()
    replay_behavior = str(decision.get("replay_behavior") or "").strip()
    if persistence_mode != "durable-write":
        return False
    if replay_behavior == "reject-conflict":
        return True
    return command_kind == "update" and replay_behavior not in {"return-existing", "read-only", "no-durable-state"}


def render_authority_idempotency_rule(decision: dict[str, object]) -> str:
    if not decision:
        return "authority-bound"
    mode = str(decision.get("idempotency_mode") or "").strip()
    persistence_mode = str(decision.get("persistence_mode") or "").strip()
    replay_behavior = str(decision.get("replay_behavior") or "").strip()
    if mode != "replay-safe":
        return f"{persistence_mode}; idempotency not applicable; replay={replay_behavior}"
    components = [str(item).strip() for item in decision.get("identity_components", []) if str(item).strip()] if isinstance(decision.get("identity_components"), list) else []
    carrier = decision.get("durable_carrier") if isinstance(decision.get("durable_carrier"), dict) else {}
    carrier_kind = str(carrier.get("kind") or "").strip()
    carrier_id = str(carrier.get("carrier_id") or "").strip()
    return f"{' + '.join(components)} is replay-safe via {carrier_kind}:{carrier_id}; replay={replay_behavior}"


def authority_interaction_binding_decision(
    context: dict[str, object], interaction_id: str
) -> tuple[dict[str, object], dict[str, object]]:
    target = str(interaction_id or "").strip()
    if not target:
        return {}, {}
    for data_decision in architecture_authority_model(context).get("data_decisions", []):
        if not isinstance(data_decision, dict):
            continue
        bindings = data_decision.get("interaction_bindings", [])
        if not isinstance(bindings, list):
            continue
        for binding in bindings:
            if isinstance(binding, dict) and str(binding.get("interaction_id") or "").strip() == target:
                return data_decision, binding
    return {}, {}


def interaction_request_mapping_text(binding: dict[str, object]) -> str:
    rows = binding.get("request_field_mapping", [])
    if not isinstance(rows, list):
        return ""
    return "; ".join(
        f"{str(row.get('ui_field') or '').strip()} -> request.{str(row.get('contract_field') or '').strip()}"
        for row in rows
        if isinstance(row, dict)
        and str(row.get("ui_field") or "").strip()
        and str(row.get("contract_field") or "").strip()
    )


def interaction_response_mapping_text(binding: dict[str, object]) -> str:
    rows = binding.get("response_field_mapping", [])
    if not isinstance(rows, list):
        return ""
    return "; ".join(
        f"response.data.{str(row.get('contract_field') or '').strip()} -> ui.{str(row.get('ui_field') or '').strip()}"
        for row in rows
        if isinstance(row, dict)
        and str(row.get("ui_field") or "").strip()
        and str(row.get("contract_field") or "").strip()
    )


def interaction_value_source_text(binding: dict[str, object]) -> str:
    rows = binding.get("request_field_mapping", [])
    if not isinstance(rows, list):
        return ""
    return "; ".join(
        f"{str(row.get('ui_field') or '').strip()}={str(row.get('source') or '').strip().replace('-', '_')}"
        for row in rows
        if isinstance(row, dict)
        and str(row.get("ui_field") or "").strip()
        and str(row.get("source") or "").strip()
    )


def interaction_response_ui_field_text(binding: dict[str, object]) -> str:
    rows = binding.get("response_field_mapping", [])
    if not isinstance(rows, list):
        return ""
    return ", ".join(
        str(row.get("ui_field") or "").strip()
        for row in rows
        if isinstance(row, dict) and str(row.get("ui_field") or "").strip()
    )


def authority_constraint_example(field_name: str, field_type: str, constraint: str) -> tuple[bool, object]:
    """Project only explicit machine-readable positive-example constraints."""
    normalized_constraint = str(constraint or "").strip()
    if not normalized_constraint:
        return False, None

    lowered_type = str(field_type or "").strip().casefold()

    def coerce_scalar(raw_value: str) -> object:
        value = raw_value.strip()
        if "bool" in lowered_type:
            lowered_value = value.casefold()
            if lowered_value == "true":
                return True
            if lowered_value == "false":
                return False
            raise ValueError(f"invalid boolean authority constraint value for {field_name}: {value}")
        if "int" in lowered_type:
            try:
                return int(value)
            except ValueError as exc:
                raise ValueError(f"invalid integer authority constraint value for {field_name}: {value}") from exc
        if any(token in lowered_type for token in ("number", "decimal", "float")):
            try:
                return float(value)
            except ValueError as exc:
                raise ValueError(f"invalid numeric authority constraint value for {field_name}: {value}") from exc
        if any(token in lowered_type for token in ("array", "object", "map", "list")):
            raise ValueError(
                f"scalar authority constraint is not supported for structured field {field_name}: {field_type}"
            )
        return value

    lowered_constraint = normalized_constraint.casefold()
    if lowered_constraint.startswith("const="):
        raw_value = normalized_constraint.split("=", 1)[1].strip()
        if not raw_value:
            raise ValueError(f"empty const authority constraint for {field_name}")
        return True, coerce_scalar(raw_value)

    if lowered_constraint.startswith("allowed-values="):
        raw_values = normalized_constraint.split("=", 1)[1]
        values = [item.strip() for item in raw_values.split("|") if item.strip()]
        if not values:
            raise ValueError(f"empty allowed-values authority constraint for {field_name}")
        return True, coerce_scalar(values[0])

    return False, None


def authority_example_value(
    field_name: str,
    field_type: str,
    constraint: str = "",
    field_spec: dict[str, object] | None = None,
) -> object:
    lowered_type = field_type.casefold()
    spec = field_spec or {}
    structured_type = any(token in lowered_type for token in ("array", "list", "object", "map"))
    structured_allowed_values = spec.get("allowed_values")
    if structured_allowed_values is not None:
        if not isinstance(structured_allowed_values, list) or not structured_allowed_values:
            raise ValueError(f"allowed_values authority constraint must be a non-empty list for {field_name}")
        synthetic_constraint = "allowed-values=" + "|".join(str(value) for value in structured_allowed_values)
        if structured_type:
            authority_constraint_example(field_name, field_type, synthetic_constraint)
        constrained, structured_value = authority_constraint_example(field_name, field_type, synthetic_constraint)
        if constrained:
            return structured_value
    if structured_type and str(constraint or "").strip().casefold().startswith(("const=", "allowed-values=")):
        authority_constraint_example(field_name, field_type, constraint)
    if any(token in lowered_type for token in ("array", "list")):
        item_fields = spec.get("item_fields", [])
        if not isinstance(item_fields, list) or not item_fields:
            return []
        item: dict[str, object] = {}
        for raw in item_fields:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or "").strip()
            if not name:
                continue
            item[name] = authority_example_value(
                name,
                str(raw.get("type") or "string").strip(),
                str(raw.get("constraint") or "").strip(),
                raw,
            )
        return [item] if item else []
    if any(token in lowered_type for token in ("object", "map")):
        object_fields = spec.get("fields", [])
        if not isinstance(object_fields, list):
            return {}
        result: dict[str, object] = {}
        for raw in object_fields:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or "").strip()
            if not name:
                continue
            result[name] = authority_example_value(
                name,
                str(raw.get("type") or "string").strip(),
                str(raw.get("constraint") or "").strip(),
                raw,
            )
        return result

    constrained, value = authority_constraint_example(field_name, field_type, constraint)
    if constrained:
        return value
    lowered_name = field_name.casefold()
    if "bool" in lowered_type:
        return False
    if any(token in lowered_type for token in ("int", "number", "decimal", "float")):
        return 1
    if "uuid" in lowered_type or lowered_name.endswith("_id"):
        return f"{field_name}-001"
    return f"example-{field_name}"
