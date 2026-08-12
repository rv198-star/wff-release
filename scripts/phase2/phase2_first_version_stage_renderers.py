#!/usr/bin/env python3
"""Phase-2 first-version runtime slice: phase2_first_version_stage_renderers.py."""

from __future__ import annotations

from phase2.phase2_first_version_design_model import *  # noqa: F401,F403


def architecture_authority_model(context: dict[str, object]) -> dict[str, object]:
    model = context.get("agentic_architecture_model")
    return model if isinstance(model, dict) else {}


def contract_trace_identity(context: dict[str, object], service: ServiceSpec, index: int) -> str:
    """Preserve accepted contract identity; synthesize trace identity only outside authority mode."""
    if architecture_authority_model(context):
        contract_id = str(service.public_contract or "").strip()
        if not contract_id:
            raise ValueError("accepted architecture operation is missing public contract identity")
        return contract_id
    return f"P2-CTR-{index:02d}"


def authority_aggregate_by_id(context: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(row.get("aggregate_id") or "").strip(): row
        for row in architecture_authority_model(context).get("aggregates", [])
        if isinstance(row, dict) and str(row.get("aggregate_id") or "").strip()
    }


def authority_operations_for_aggregate(context: dict[str, object], aggregate_id: str) -> list[dict[str, object]]:
    return [
        row
        for row in architecture_authority_model(context).get("operations", [])
        if isinstance(row, dict) and str(row.get("aggregate_id") or "").strip() == aggregate_id
    ]


def authority_state_surface(aggregate: dict[str, object]) -> dict[str, str]:
    state_rows = [row for row in aggregate.get("state_decisions", []) if isinstance(row, dict)]
    states: list[str] = []
    events: list[str] = []
    mutation_guards: list[str] = []
    failure_exits: list[str] = []
    for row in state_rows:
        for key in ("states", "state_set"):
            value = row.get(key)
            if isinstance(value, list):
                states.extend(str(item).strip() for item in value if str(item).strip())
            elif isinstance(value, str) and value.strip():
                states.extend(part.strip() for part in re.split(r"[,|/]", value) if part.strip())
        for key in ("event_ids", "trigger_events", "events"):
            value = row.get(key)
            if isinstance(value, list):
                events.extend(str(item).strip() for item in value if str(item).strip())
            elif isinstance(value, str) and value.strip():
                events.extend(part.strip() for part in re.split(r"[,|/]", value) if part.strip())
        for key in ("mutation_guard", "invariant", "policy", "statement"):
            value = str(row.get(key) or "").strip()
            if value:
                mutation_guards.append(value)
        for key in ("terminal_or_failure_exit", "failure_guardrail", "failure_rule"):
            value = str(row.get(key) or "").strip()
            if value:
                failure_exits.append(value)
    return {
        "states": " / ".join(unique_preserve(states)) or "authority-bound; no inferred lifecycle states",
        "events": ", ".join(unique_preserve(events)) or "none accepted",
        "mutation_guard": " ; ".join(unique_preserve(mutation_guards)) or "accepted operations only; no inferred mutation rule",
        "failure_exit": " ; ".join(unique_preserve(failure_exits)) or "review-bound; no inferred terminal/failure rule",
    }


def authority_event_driver_rows(
    context: dict[str, object],
    aggregate_objects: list[str],
) -> tuple[list[list[str]], list[list[str]], list[list[str]], list[list[str]]]:
    aggregate_map = authority_aggregate_by_id(context)
    events: list[list[str]] = []
    vocabulary_rows: list[list[str]] = []
    model_rows: list[list[str]] = []
    carry_rows: list[list[str]] = []
    seen: set[str] = set()
    for aggregate_id in aggregate_objects:
        aggregate = aggregate_map.get(aggregate_id)
        if not aggregate:
            continue
        producer = str(aggregate.get("writer_service_id") or aggregate.get("owner_service_id") or "authority-bound").strip()
        for state_row in [row for row in aggregate.get("state_decisions", []) if isinstance(row, dict)]:
            raw_events = state_row.get("event_ids", state_row.get("trigger_events", state_row.get("events", [])))
            event_ids = (
                [str(item).strip() for item in raw_events if str(item).strip()]
                if isinstance(raw_events, list)
                else [part.strip() for part in re.split(r"[,|/]", str(raw_events)) if part.strip()]
            )
            for event_id in event_ids:
                if event_id in seen:
                    continue
                seen.add(event_id)
                trigger = str(state_row.get("trigger") or state_row.get("statement") or "accepted authority transition").strip()
                payload = str(state_row.get("event_payload") or f"{aggregate_id} identity + accepted transition context").strip()
                ordering = str(state_row.get("ordering_semantics") or "after accepted authoritative write").strip()
                idempotency = str(state_row.get("idempotency_rule") or "authority-bound; do not invent stronger semantics").strip()
                consumer = str(state_row.get("consumer") or "accepted downstream consumers").strip()
                events.append([event_id, producer, consumer, trigger, payload, ordering, idempotency])
                vocabulary_rows.append([event_id, trigger, producer, consumer, payload, ordering, idempotency, "consume read-only unless separately authorized"])
                model_rows.append([
                    str(state_row.get("decision_id") or event_id).strip(),
                    event_id,
                    trigger,
                    f"{producer} -> {consumer}",
                    str(state_row.get("effect") or "accepted state/evidence transition").strip(),
                    str(state_row.get("claim_ceiling") or "bounded by accepted P2 authority").strip(),
                    str(state_row.get("p3_handoff") or "preserve event identity and accepted semantics").strip(),
                    "accepted-authority",
                ])
                carry_rows.append([event_id, str(state_row.get("p3_handoff") or "preserve accepted event identity").strip(), event_id, "accepted P2 event identity carried forward without renaming"])
    return events, vocabulary_rows, model_rows, carry_rows


def p1_product_topology_mode(context: dict[str, object]) -> str:
    p1 = architecture_authority_model(context).get("p1_authority", {})
    if not isinstance(p1, dict):
        return ""
    decision = p1.get("product_world_decision", {})
    if not isinstance(decision, dict):
        return ""
    topology = decision.get("topology", {})
    return str(topology.get("mode") or "").strip() if isinstance(topology, dict) else ""


def authority_operation_topology_group(context: dict[str, object], operation_id: str) -> str:
    for row in architecture_authority_model(context).get("operations", []):
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip() == operation_id:
            return str(row.get("topology_group") or "").strip()
    return ""


def authority_service_read_only(context: dict[str, object], service: ServiceSpec) -> bool:
    if service.service_type != "authority-operation":
        return not service_exposes_persistent_object(service)
    aggregate = authority_aggregate_by_id(context).get(service.owns_or_coordinates, {})
    writer_id = str(aggregate.get("writer_service_id") or aggregate.get("owner_service_id") or "").strip()
    return service.method.upper() in {"GET", "HEAD"} or bool(writer_id and writer_id != service.domain)


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


def _authority_constraint_example(field_name: str, field_type: str, constraint: str) -> tuple[bool, object]:
    """Project only explicit machine-readable positive-example constraints.

    Unknown prose constraints remain descriptive authority and fall back to the
    existing type-aware example. Recognized constraint syntax is intentionally
    small so the renderer never guesses business truth from free text.
    """
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


def _authority_example_value(field_name: str, field_type: str, constraint: str = "") -> object:
    constrained, value = _authority_constraint_example(field_name, field_type, constraint)
    if constrained:
        return value
    lowered_type = field_type.casefold()
    lowered_name = field_name.casefold()
    if "bool" in lowered_type:
        return False
    if any(token in lowered_type for token in ("int", "number", "decimal", "float")):
        return 1
    if "uuid" in lowered_type or lowered_name.endswith("_id"):
        return f"{field_name}-001"
    return f"example-{field_name}"


def authority_contract_material(
    context: dict[str, object],
    service: ServiceSpec,
) -> tuple[dict[str, object], dict[str, object], list[str], dict[str, str]] | None:
    if service.service_type != "authority-operation":
        return None
    decision = authority_operation_data_decision(context, service.endpoint_name)
    if not decision:
        return ({}, {"data": {}, "meta": {"traceId": "trace-001"}}, ["review-bound: explicit request/result fields not declared by accepted P2 authority"], {})
    request_fields = [row for row in decision.get("request_fields", []) if isinstance(row, dict)] if isinstance(decision.get("request_fields"), list) else []
    result_fields = [row for row in decision.get("result_fields", []) if isinstance(row, dict)] if isinstance(decision.get("result_fields"), list) else []
    request_example = {
        str(row.get("name") or "").strip(): _authority_example_value(
            str(row.get("name") or "").strip(),
            str(row.get("type") or "string").strip(),
            str(row.get("constraint") or "").strip(),
        )
        for row in request_fields
        if str(row.get("name") or "").strip()
    }
    result_example = {
        str(row.get("name") or "").strip(): _authority_example_value(
            str(row.get("name") or "").strip(),
            str(row.get("type") or "string").strip(),
            str(row.get("constraint") or "").strip(),
        )
        for row in result_fields
        if str(row.get("name") or "").strip()
    }
    schema_fields = [
        f"request.{str(row.get('name') or '').strip()}: {str(row.get('type') or 'string').strip()}"
        for row in request_fields
        if str(row.get("name") or "").strip()
    ] + [
        f"response.data.{str(row.get('name') or '').strip()}: {str(row.get('type') or 'string').strip()}"
        for row in result_fields
        if str(row.get("name") or "").strip()
    ] + ["response.meta.traceId: string"]
    persistence_decision = authority_operation_persistence_decision(context, service.endpoint_name)
    policies = {
        "failure_codes": str(decision.get("failure_codes") or "authority-bound").strip(),
        "idempotency_rule": render_authority_idempotency_rule(persistence_decision),
        "retryability_policy": str(decision.get("retryability_policy") or "retry only where accepted failure semantics allow").strip(),
        "pagination_rule": str(decision.get("pagination_rule") or "none").strip(),
        "rate_limit_policy": str(decision.get("rate_limit_policy") or "review-bound; no numeric rate limit accepted").strip(),
    }
    return request_example, {"data": result_example, "meta": {"traceId": "trace-001"}}, schema_fields, policies


def reconcile_authority_binding_rows(
    context: dict[str, object],
    endpoint_specs: list[ServiceSpec],
    rows: list[list[str]],
) -> list[list[str]]:
    if not rows or not endpoint_specs or not all(service.service_type == "authority-operation" for service in endpoint_specs):
        return rows
    by_service_name = {service.service_name: service for service in endpoint_specs}
    reconciled: list[list[str]] = []
    for raw in rows:
        row = list(raw)
        if len(row) < 19:
            reconciled.append(row)
            continue
        service = by_service_name.get(str(row[5]).strip())
        if service is None:
            reconciled.append(row)
            continue
        binding_mode = str(row[4]).strip().casefold()
        method = service.method.upper()
        if binding_mode == "read" and method not in {"GET", "HEAD"}:
            row[5] = "UNRESOLVED_SERVICE_BINDING"
            row[6] = "—"
            row[7] = "—"
            row[8] = "review-bound / accepted-operation-method-mismatch"
            row[9] = "review-bound / accepted-operation-method-mismatch"
            row[10] = "—"
            row[13] = "—"
            row[17] = "review-bound"
            row[18] = "no accepted read operation matches this interaction; renderer must not reuse a write operation"
            reconciled.append(row)
            continue
        decision = authority_operation_data_decision(context, service.endpoint_name)
        request_fields = [
            f"request.{str(item.get('name') or '').strip()}"
            for item in decision.get("request_fields", [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ] if isinstance(decision.get("request_fields"), list) else []
        result_fields = [
            f"response.data.{str(item.get('name') or '').strip()}"
            for item in decision.get("result_fields", [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ] if isinstance(decision.get("result_fields"), list) else []
        row[8] = (
            "accepted contract fields: " + ", ".join(request_fields) + "; UI-field mapping remains review-bound"
            if request_fields
            else "review-bound / accepted request fields not explicitly mapped to this UI interaction"
        )
        row[9] = (
            "accepted contract fields: " + ", ".join(result_fields) + "; UI projection mapping remains review-bound"
            if result_fields
            else "review-bound / accepted result fields not explicitly mapped to this UI interaction"
        )
        row[13] = str(decision.get("failure_codes") or row[13]).strip()
        row[17] = "review-bound"
        row[18] = "endpoint/contract is accepted; exact UI-to-contract field mapping requires explicit reconciliation"
        reconciled.append(row)
    return reconciled


def reconcile_authority_enrichment_rows(
    context: dict[str, object],
    binding_rows: list[list[str]],
    enrichment_rows: list[list[str]],
) -> list[list[str]]:
    if not enrichment_rows or not architecture_authority_model(context):
        return enrichment_rows
    binding_by_interaction = {
        str(row[1]).strip(): row
        for row in binding_rows
        if len(row) >= 19 and str(row[1]).strip()
    }
    reconciled: list[list[str]] = []
    for raw in enrichment_rows:
        row = list(raw)
        if len(row) < 11:
            reconciled.append(row)
            continue
        interaction_id = str(row[0]).strip()
        binding = binding_by_interaction.get(interaction_id)
        if binding is None:
            reconciled.append(row)
            continue
        unresolved = str(binding[5]).strip() == "UNRESOLVED_SERVICE_BINDING"
        row[6] = (
            "review-bound / no accepted P2 operation is bound to this interaction"
            if unresolved
            else "accepted P2 contract is authoritative; exact P1 UI-field-to-contract mapping remains review-bound"
        )
        row[9] = "review-bound"
        row[10] = str(binding[18]).strip() or "UI-to-contract mapping requires explicit reconciliation"
        reconciled.append(row)
    return reconciled


def render_p1_product_world_handoff_block(context: dict[str, object]) -> str:
    p1 = architecture_authority_model(context).get("p1_authority", {})
    if not isinstance(p1, dict):
        return ""
    decision = p1.get("product_world_decision", {})
    if not isinstance(decision, dict) or not decision:
        return ""
    topology = decision.get("topology", {}) if isinstance(decision.get("topology"), dict) else {}
    ownership = decision.get("ownership", {}) if isinstance(decision.get("ownership"), dict) else {}
    objects = [row for row in decision.get("objects", []) if isinstance(row, dict)] if isinstance(decision.get("objects"), list) else []
    object_surface = "; ".join(
        f"{str(row.get('object_id') or '').strip()}: {str(row.get('name') or '').strip()} [{str(row.get('basis') or 'review-bound').strip()}]"
        for row in objects
        if str(row.get("object_id") or "").strip()
    )
    return "\n".join(
        [
            "## Preserved P1 Product-World Handoff",
            "",
            f"- world_knowledge_contract: `{str(p1.get('world_knowledge_contract') or '').strip()}`",
            f"- product_world_summary: {str(decision.get('summary') or 'review-bound').strip()}",
            f"- topology: `{str(topology.get('mode') or 'review-bound').strip()}` / {str(topology.get('statement') or 'review-bound').strip()}",
            f"- ownership_posture: `{str(ownership.get('posture') or 'review-bound').strip()}` / {str(ownership.get('statement') or 'review-bound').strip()}",
            f"- canonical_product_objects: {object_surface or 'review-bound'}",
            "- rule: P2 may realize this product world architecturally but must not merge, serialize, rename away, or reconstruct its accepted product semantics.",
        ]
    )


def render_authority_non_operation_block(context: dict[str, object]) -> str:
    rows = [row for row in architecture_authority_model(context).get("non_operations", []) if isinstance(row, dict)]
    if not rows:
        return ""
    table_rows = [
        [
            str(row.get("realization_id") or "").strip(),
            str(row.get("realization_type") or "").strip(),
            str(row.get("statement") or "").strip(),
            str(row.get("owner") or "").strip(),
            str(row.get("claim_ceiling") or "").strip(),
        ]
        for row in rows
    ]
    return "\n".join(
        [
            "## Accepted Non-Operation Architecture Realizations",
            "",
            make_markdown_table(
                ["realization_id", "type", "canonical rule", "owner", "claim ceiling"],
                table_rows,
            ),
            "",
            "> These are architecture rules, not endpoints. The renderer must not convert them into CRUD operations or implementation obligations beyond their accepted ceiling.",
        ]
    )


def authority_architecture_decision_rows(context: dict[str, object]) -> list[dict[str, object]]:
    model = architecture_authority_model(context)
    rows: list[dict[str, object]] = []
    seen: set[str] = set()

    def append(row: dict[str, object]) -> None:
        decision_id = str(row.get("decision_id") or row.get("realization_id") or "").strip()
        statement = str(row.get("statement") or row.get("mutation_guard") or "").strip()
        if not decision_id or not statement or decision_id in seen:
            return
        seen.add(decision_id)
        rows.append({**row, "decision_id": decision_id, "statement": statement})

    for row in model.get("data_decisions", []):
        if isinstance(row, dict) and str(row.get("decision_type") or "").strip() == "architecture-decision":
            append(row)
    for row in model.get("non_operations", []):
        if isinstance(row, dict):
            append(
                {
                    **row,
                    "decision_id": str(row.get("realization_id") or "").strip(),
                    "title": str(row.get("realization_type") or "architecture rule").strip(),
                }
            )
    for row in model.get("state_policy_failure", []):
        if isinstance(row, dict):
            append(row)
    return rows


def authority_architecture_posture(context: dict[str, object]) -> dict[str, object]:
    for row in architecture_authority_model(context).get("data_decisions", []):
        if isinstance(row, dict) and str(row.get("decision_type") or "").strip() == "architecture-posture":
            return row
    return {}


def authority_adr_surfaces(
    context: dict[str, object],
    *,
    limit: int,
) -> tuple[list[str], list[list[str]]]:
    entries: list[str] = []
    traces: list[list[str]] = []
    for idx, row in enumerate(authority_architecture_decision_rows(context)[:limit], start=1):
        decision_id = str(row.get("decision_id") or "").strip()
        title = str(row.get("title") or decision_id).strip()
        statement = str(row.get("statement") or "").strip()
        context_text = str(row.get("context") or "Accepted by the current snapshot-bound P2 architecture authority.").strip()
        raw_refs = row.get("evidence_refs", [])
        refs = [str(item).strip() for item in raw_refs if str(item).strip()] if isinstance(raw_refs, list) else []
        raw_alternatives = row.get("alternatives_considered", row.get("alternatives", []))
        alternatives: list[tuple[str, str]] = []
        if isinstance(raw_alternatives, list):
            for item in raw_alternatives:
                if isinstance(item, dict):
                    name = str(item.get("alternative_name") or item.get("name") or "").strip()
                    reason = str(item.get("rejected_because") or item.get("reason") or "not accepted by current P2 authority").strip()
                    if name:
                        alternatives.append((name, reason))
                elif str(item).strip():
                    alternatives.append((str(item).strip(), "not accepted by current P2 authority"))
        alternative_lines: list[str] = []
        if alternatives:
            for name, reason in alternatives:
                alternative_lines.extend(
                    [
                        f"      - alternative_name: {name}",
                        f"      - rejected_because: {reason}",
                    ]
                )
        else:
            alternative_lines.extend(
                [
                    "      - alternative_name: `not-expanded-by-renderer`",
                    "      - rejected_because: alternatives were not accepted in the P2 authority; the renderer does not invent them",
                ]
            )
        positive = str(row.get("positive_consequence") or "preserves the accepted architecture boundary without renderer reinterpretation").strip()
        negative = str(row.get("negative_consequence") or "trade-off detail remains bounded to what the P2 authority explicitly accepted").strip()
        risks = str(row.get("risk") or row.get("claim_ceiling") or "stronger claims remain review-bound").strip()
        evidence = ", ".join(refs) if refs else f"accepted P2 decision `{decision_id}`"
        entries.append(
            "\n".join(
                [
                    f"  - adr_{idx:02d}:",
                    f"    - ad_id: `{decision_id}`",
                    f"    - title: {title}",
                    "    - status:",
                    "      - `Accepted`",
                    f"    - context: {context_text}",
                    f"    - decision: {statement}",
                    "    - alternatives_considered:",
                    *alternative_lines,
                    "    - consequences:",
                    f"      - positive: {positive}",
                    f"      - negative: {negative}",
                    f"      - risks: {risks}",
                    f"    - evidence: {evidence}",
                ]
            )
        )
        traces.append(
            [
                f"P2-DTR-{idx:02d}",
                decision_id,
                title,
                f"authority_evidence={evidence}",
                "ARCH-STG03-OUTPUT-0001",
                "canonical Stage/ESP must preserve this accepted decision and may not replace it with a template default",
                ", ".join(refs) or decision_id,
            ]
        )
    return entries, traces


def render_stage_01(
    *,
    case_name: str,
    phase1_prd: Path,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
) -> str:
    root_namespace = str(context["root_namespace"])
    boundary_scope = str(context.get("boundary_scope", "tenant"))
    boundary_term = boundary_phrase(boundary_scope)
    boundary_subject_name = boundary_subject(boundary_scope)
    workflow_scope = workflow_scope_summary(context)
    async_completion_pack = async_completion_runtime_pack_for_context(context)
    primary_owner_label = "Workspace Owner"
    operator_label = "Execution Operator"
    reviewer_label = "Decision Reviewer"
    quality_attributes = [str(item) for item in context["quality_attributes"]][: max(profile_minimum(complexity_profile, "stage_01_quality_attributes"), 4)]
    trace_rows = list(context["all_trace_rows"])
    req_ac_ids = [
        row["trace_id"]
        for row in trace_rows
        if row.get("unit_type") in {"requirement", "acceptance-criteria"}
    ] or [row["trace_id"] for row in trace_rows]
    adr_count = max(profile_minimum(complexity_profile, "stage_01_architecture_decisions"), 4)
    decision_trace_groups = distribute_phase1_ids(req_ac_ids, adr_count)
    capability_target = max(profile_minimum(complexity_profile, "stage_01_capability_groups"), 4)
    capability_domain_names = unique_preserve(
        [str(item) for item in list(context.get("domains", []))]
        + [service.domain for service in services]
    )[:4]
    while len(capability_domain_names) < 4:
        capability_domain_names.append(f"domain-{len(capability_domain_names) + 1}")
    capability_groups = [
        {
            "name": f"{capability_domain_names[0]} Scope and Governance",
            "priority": "P0",
            "maturity": "core",
            "rationale": "Minimum valid boundary, access, and workflow guardrails must remain stable before downstream design deepening and review.",
            "covers": f"{capability_domain_names[0]} ownership, {boundary_subject_name} access, workflow boundary validation, version freeze",
        },
        {
            "name": f"{capability_domain_names[1]} Workflow Context and Signals",
            "priority": "P0",
            "maturity": "core",
            "rationale": "Current-state evidence, handoff context, and operator-visible signals must remain reproducible and explainable.",
            "covers": f"{capability_domain_names[1]} current-state snapshot, signal versioning, handoff context",
        },
        {
            "name": f"{capability_domain_names[2]} Action Handoff and Execution",
            "priority": "P0",
            "maturity": "core",
            "rationale": "The product loses business value if upstream business context cannot become bounded execution work.",
            "covers": f"{capability_domain_names[2]} typed handoff payload, work-item bridge, target object linkage",
        },
        {
            "name": f"{capability_domain_names[3]} Review and Closure",
            "priority": "P0",
            "maturity": "guided",
            "rationale": "Downstream delivery must preserve review-bound truths instead of narrative certainty.",
            "covers": f"{capability_domain_names[3]} review summaries, uncertainty notes, continue-or-revise posture",
        },
    ][:capability_target]
    supports_deferred_extension_seam = context_supports_deferred_extension_seam(context)
    business_proof_constraints = business_proof_constraint_block(context, indent=4)
    business_architecture_pressure = business_architecture_pressure_block(context, indent=4)
    deferred_constraint_lines = (
        [
            "advanced attribution seams remain reserved but not promised as MVP-complete",
            "external connector hardening remains PhaseX / later-wave work",
        ]
        if supports_deferred_extension_seam
        else [
            "deferred extension seams stay explicit only when Phase-1 truth actually declares them",
            "provider-specific hardening remains later-wave work until a real dependency commitment exists",
        ]
    )

    adr_entries: list[str] = []
    decision_trace_table_rows: list[list[str]] = []
    if architecture_authority_model(context):
        adr_entries, decision_trace_table_rows = authority_adr_surfaces(context, limit=adr_count)
    else:
        adr_titles = [str(item) for item in context.get("adr_titles", [])][:adr_count]
        for idx, title in enumerate(adr_titles, start=1):
            ad_id = f"AD-{idx:02d}"
            ids = decision_trace_groups[idx - 1]
            service = select_adr_anchor_service(title, services)
            adr_content = adr_content_for(
                title=title,
                service=service,
                case_name=case_name,
                upstream_ids=ids,
                root_namespace=root_namespace,
            )
            hook = (
                f"{title} stays visible in `{service.public_contract}` / `{service.endpoint_name}` handoff evidence "
                f"for {summarize_list(ids, max_items=3)}."
            )
            alternative_lines: list[str] = []
            for alternative_name, rejected_because in adr_content["alternatives"]:
                alternative_lines.extend(
                    [
                        f"      - alternative_name: {alternative_name}",
                        f"      - rejected_because: {rejected_because}",
                    ]
                )
            adr_entries.append(
                "\n".join(
                    [
                        f"  - adr_{idx:02d}:",
                        f"    - ad_id: `{ad_id}`",
                        f"    - title: {title}",
                        "    - status:",
                        "      - `Accepted`",
                        f"    - context: {adr_content['context']}",
                        f"    - decision: {adr_content['decision']}",
                        "    - alternatives_considered:",
                        *alternative_lines,
                        "    - consequences:",
                        f"      - positive: {adr_content['consequences']['positive']}",
                        f"      - negative: {adr_content['consequences']['negative']}",
                        f"      - risks: {adr_content['consequences']['risks']}",
                        f"    - evidence: {adr_content['evidence']}",
                    ]
                )
            )
            decision_trace_table_rows.append(
                [
                    f"P2-DTR-{idx:02d}",
                    ad_id,
                    title,
                    f"upstream_trace_ids={', '.join(ids)}",
                    "ARCH-STG03-OUTPUT-0001",
                    hook,
                    ", ".join(ids),
                ]
            )

    forbidden_count = max(profile_minimum(complexity_profile, "stage_01_forbidden_assumptions"), 5)
    forbidden_entries = []
    forbidden_templates = forbidden_templates_for_context(context)
    for idx in range(forbidden_count):
        code, text = forbidden_templates[idx % len(forbidden_templates)]
        forbidden_entries.append(
            "\n".join(
                [
                    f"  - fa_{idx + 1:02d}:",
                    f"    - original_text: {text}",
                    "    - source: Phase-1 `Must Not Assume` and trust-bound workflow posture",
                    "    - architecture_constraint_mapping: enforce explicit contracts, RBI carry-forward, or boundary checks",
                    "    - compliance_status: `must-preserve`",
                    "    - evidence_reference: PRD requirement / acceptance registry remains explicit",
                    "    - evidence_strength: `strong`",
                ]
            )
        )

    quality_entries = []
    for attr in quality_attributes:
        quality_entries.append(
            "\n".join(
                [
                    f"    - {to_snake(attr)}:",
                    f"      - quantified_target: keep `{attr}` visible in every Stage-03 or Stage-04 acceptance surface",
                    "      - metric_name: first-pass traceable design surfaces",
                    "      - target_value: >= 1 direct structured binding per critical flow",
                    "      - measurement_window: per design revision",
                    "      - design_implication: 把该属性前置到 contract、replay 或 verification note",
                    "      - evidence_or_source: Phase-1 NFR and quality scenario matrix",
                ]
            )
        )

    primary_object_list = ", ".join(f"`{item}`" for item in list(context["objects"])[:7])
    deferred_constraint_block = "\n".join(f"    - {line}" for line in deferred_constraint_lines)
    quality_entries_block = "\n".join(quality_entries)
    capability_map_block = "\n".join(
        [
            "\n".join(
                [
                    f"  - capability_group_{idx:02d}:",
                    f"    - name: {group['name']}",
                    "    - priority:",
                    f"      - `{group['priority']}`",
                    "    - maturity:",
                    f"      - `{group['maturity']}`",
                    f"    - rationale: {group['rationale']}",
                    "    - covers:",
                    f"      - {group['covers']}",
                ]
            )
            for idx, group in enumerate(capability_groups, start=1)
        ]
    )

    authority_model = architecture_authority_model(context)
    posture = authority_architecture_posture(context)
    if authority_model:
        architecture_direction_block = "\n".join(
            [
                f"  - selected_shape: `{str(posture.get('selected_shape') or 'review-bound; no deployment shape accepted').strip()}`",
                f"  - why_selected: {str(posture.get('why_selected') or 'renderer does not select a shape beyond accepted P2 authority').strip()}",
                "  - boundary_rule: accepted service, operation, aggregate, writer, contract, NOR, dependency, and topology boundaries remain authoritative even if implementation internals change",
            ]
        )
        accepted_security_rules = [
            str(row.get("statement") or "").strip()
            for row in authority_model.get("non_operations", [])
            if isinstance(row, dict)
            and str(row.get("realization_type") or "").strip() in {"authorization-rule", "policy", "failure-rule"}
            and str(row.get("statement") or "").strip()
        ]
        security_architecture_block = "\n".join(
            [
                "  - trust_boundaries:",
                "    - accepted P2 service/aggregate writer boundaries and explicit authorization/privacy NORs",
                f"  - identity_and_access_posture: {str(posture.get('security_posture') or 'review-bound; no identity provider, token lifetime, key product, or break-glass mechanism accepted').strip()}",
                "  - accepted_security_rules:",
                *([f"    - {line}" for line in accepted_security_rules[:6]] or ["    - review-bound; no additional security rule accepted"]),
                "  - authentication_sequence: review-bound unless explicitly accepted by P2 authority; renderer does not invent API-gateway/token/KMS choreography",
                "  - key_management_posture: review-bound unless explicitly accepted by P2 authority",
                "  - audit_sensitive_edges: preserve only accepted audit/permission/visibility evidence and writer boundaries",
            ]
        )
        capacity_estimation_block = "\n".join(
            [
                f"  - throughput: {str(posture.get('performance_posture') or 'review-bound; no numeric throughput target accepted').strip()}",
                f"  - latency: {str(posture.get('performance_posture') or 'review-bound; no numeric latency target accepted').strip()}",
                "  - growth: review-bound until runtime volume evidence exists",
                f"  - retention: {str(posture.get('retention_posture') or 'review-bound; no retention duration accepted').strip()}",
                "  - volume: review-bound until runtime usage evidence exists",
                f"  - storage: {str(posture.get('primary_storage') or 'review-bound; no storage technology accepted').strip()}",
            ]
        )
    else:
        architecture_direction_block = "\n".join(
            [
                "  - selected_shape: `modular monolith`",
                "  - why_selected: preserve strong object-chain traceability and keep public contracts explicit before any later physical split",
                "  - boundary_rule: module contracts stay stable even if Phase-3 implementation reorganizes internals",
            ]
        )
        security_architecture_block = "\n".join(
            [
                "  - trust_boundaries:",
                f"    - {boundary_subject_name} boundary around every authoritative business object and review surface",
                "    - internal service boundary around typed handoff payload and closure evidence",
                "  - identity_and_access_posture: enforce role-scoped access checks with break-glass audit logging for privileged reads",
                "  - auth_sequence_direction: user -> API gateway -> policy enforcement -> domain module -> audit trail",
                "  - authentication_sequence: short-lived access token + role/boundary claims; access token 15m, refresh token 8h rolling",
                "  - key_management_posture: KMS-backed secret storage with 90-day scheduled rotation or incident-driven rotation",
                "  - audit_sensitive_edges: boundary policy change; work-item export/cross-module handoff; review decision issuance",
            ]
        )
        capacity_estimation_block = "\n".join(
            [
                "  - throughput: 120 run-related requests / min at first-wave steady state",
                f"  - latency: p95 <= 600 ms for synchronous API reads and p95 <= 5 min for {async_completion_pack['latency_target_label']}",
                f"  - growth: {async_completion_pack['growth_target_label']}",
                "  - retention: 365d hot evidence + 730d cold archive for audit-critical data",
                f"  - volume: {async_completion_pack['volume_target_label']}",
                "  - storage: start with PostgreSQL + object-store export seam, not multi-engine sprawl",
            ]
        )

    stage = render_phase2_template(
        "stage-01-architecture-definition.md.template",
        {
            "case_name": case_name,
            "phase1_prd": phase1_prd,
            "complexity_profile": complexity_profile,
            "root_namespace": root_namespace,
            "workflow_scope": workflow_scope,
            "primary_object_list": primary_object_list,
            "boundary_term": boundary_term,
            "boundary_subject_name": boundary_subject_name,
            "deferred_constraint_block": deferred_constraint_block,
            "business_proof_constraints": business_proof_constraints,
            "business_architecture_pressure": business_architecture_pressure,
            "quality_entries_block": quality_entries_block,
            "capability_map_block": capability_map_block,
            "architecture_direction_block": architecture_direction_block,
            "security_architecture_block": security_architecture_block,
            "capacity_estimation_block": capacity_estimation_block,
            "adr_entries_block": "\n".join(adr_entries),
            "decision_trace_registry_table": make_markdown_table(
                [
                    "trace_id",
                    "adr_id",
                    "decision_title",
                    "upstream_reference",
                    "downstream_artifact_id",
                    "verification_hook",
                    "upstream_trace_ids",
                ],
                decision_trace_table_rows,
            ),
            "latency_target_label": async_completion_pack["latency_target_label"],
            "growth_target_label": async_completion_pack["growth_target_label"],
            "volume_target_label": async_completion_pack["volume_target_label"],
            "forbidden_entries_block": "\n".join(forbidden_entries),
            "primary_owner_label": primary_owner_label,
            "operator_label": operator_label,
            "reviewer_label": reviewer_label,
        },
    )
    return stage.rstrip() + "\n"



def render_stage_02(
    *,
    phase1_prd: Path,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
    table_specs: list[dict[str, object]],
) -> str:
    root_namespace = str(context["root_namespace"])
    modules = require_context_modules(context)
    authority_model = architecture_authority_model(context)
    accepted_aggregate_ids = [
        str(row.get("aggregate_id") or "").strip()
        for row in authority_model.get("aggregates", [])
        if isinstance(row, dict) and str(row.get("aggregate_id") or "").strip()
    ]
    accepted_service_ids = [
        str(row.get("service_id") or "").strip()
        for row in authority_model.get("services", [])
        if isinstance(row, dict) and str(row.get("service_id") or "").strip()
    ]
    domains = (
        accepted_service_ids
        if accepted_service_ids
        else unique_preserve(
            [str(item) for item in context.get("domains", [])]
            + [service.domain for service in services]
        ) or unique_preserve([service.domain for service in services])
    )
    aggregate_seed = (
        accepted_aggregate_ids
        if accepted_aggregate_ids
        else unique_semantic_objects(
            [str(spec["object_name"]) for spec in table_specs]
            + [
                str(item)
                for item in context.get("core_objects", [])
                if str(item).strip() and object_requires_persistent_table(str(item))
            ]
            + [
                str(item)
                for item in context.get("supplemental_objects", [])
                if str(item).strip() and object_requires_persistent_table(str(item))
            ]
            + [service.owns_or_coordinates for service in services if object_requires_persistent_table(service.owns_or_coordinates)]
        )
    )
    aggregate_seed = phase3_surface_safe_labels(aggregate_seed)
    aggregate_target = max(
        profile_minimum(complexity_profile, "stage_02_aggregate_catalog"),
        min(len(aggregate_seed), len(services) + 3),
        len(table_specs),
    )
    aggregate_objects = aggregate_seed[:aggregate_target] if aggregate_seed else [service.owns_or_coordinates for service in services]
    table_binding_map = {str(spec["object_name"]): str(spec["table_name"]) for spec in table_specs}

    domain_rows = []
    module_rows = []
    service_rows = []
    aggregate_rows = []
    responsibility_rows = []
    canonical_rows = []
    service_endpoint_rows = []
    lifecycle_rows = []

    rendered_domains = domains[: max(profile_minimum(complexity_profile, "stage_02_domains"), 3)] or [services[0].domain]
    accepted_aggregate_map = authority_aggregate_by_id(context)
    for domain in rendered_domains:
        related_services = [service for service in services if service.domain == domain]
        if accepted_service_ids:
            owned_aggregate_rows = [
                row
                for row in accepted_aggregate_map.values()
                if str(row.get("owner_service_id") or "").strip() == domain
            ]
            domain_objects = [str(row.get("aggregate_name") or row.get("aggregate_id") or "").strip() for row in owned_aggregate_rows]
            state_surfaces = [authority_state_surface(row)["states"] for row in owned_aggregate_rows]
            primary_states = " ; ".join(state_surfaces) or "authority-bound; no inferred lifecycle states"
            service_statements = [
                str(row.get("statement") or "").strip()
                for row in authority_model.get("services", [])
                if isinstance(row, dict) and str(row.get("service_id") or "").strip() == domain
            ]
            domain_rows.append([
                domain,
                "accepted P2 service boundary",
                summarize_list(service_statements, max_items=2),
                summarize_list(domain_objects, max_items=4),
                primary_states,
                "must not acquire aggregates or operations outside accepted P2 authority",
                "handoff only through accepted contracts and read-only evidence",
            ])
            continue
        domain_objects = unique_preserve([service.owns_or_coordinates for service in related_services]) or aggregate_objects[:2]
        primary_states = build_object_profile(related_services[0], domain_objects[0])["primary_states"] if related_services and domain_objects else "draft / active / archived"
        source_contract_only_domain = bool(related_services) and all(not service_exposes_persistent_object(service) for service in related_services)
        domain_rows.append([
            domain,
            release_domain_role_surface([service.service_type for service in related_services]),
            summarize_list([service.purpose for service in related_services], max_items=2),
            summarize_list(domain_objects, max_items=4),
            primary_states,
            release_slice_guardrail(),
            release_handoff_rule(source_contract_only_domain),
        ])

    module_objects = {}
    for module in modules:
        name = module_name(module)
        module_objects[name] = unique_preserve(module_core_objects(module) + [str(item) for item in module.get("supplemental_objects", [])])
    for service in services:
        module_objects.setdefault(service.home_module, [])
        if service.owns_or_coordinates not in module_objects[service.home_module]:
            module_objects[service.home_module].append(service.owns_or_coordinates)

    seen_modules = set()
    accepted_aggregate_map_for_services = authority_aggregate_by_id(context)
    for service in services:
        if service.service_type == "authority-operation":
            aggregate = accepted_aggregate_map_for_services.get(service.owns_or_coordinates, {})
            writer_id = str(aggregate.get("writer_service_id") or aggregate.get("owner_service_id") or "").strip()
            read_only = service.method.upper() in {"GET", "HEAD"} or bool(writer_id and writer_id != service.domain)
            consistency_boundary = (
                f"read-only operation; accepted writer remains `{writer_id or 'authority-bound'}`"
                if read_only
                else f"accepted write operation; writer remains `{writer_id or service.domain}`"
            )
        else:
            source_contract_read_only = not service_exposes_persistent_object(service)
            consistency_boundary = release_consistency_boundary(service.home_module, service.owns_or_coordinates, source_contract_read_only)
        service_rows.append([
            service.service_name,
            service.domain,
            service.home_module,
            service.service_type,
            service.owns_or_coordinates,
            service.primary_inbound,
            service.primary_outbound,
            service.purpose,
            consistency_boundary,
        ])
        if service.home_module in seen_modules:
            continue
        seen_modules.add(service.home_module)
        owned = unique_preserve(module_objects.get(service.home_module, []) + [item.owns_or_coordinates for item in services if item.home_module == service.home_module])
        module_services = [item for item in services if item.home_module == service.home_module]
        if all(item.service_type == "authority-operation" for item in module_services):
            change_note = (
                "accepted operations may mutate only aggregates whose writer_service_id matches this module; "
                "all other accepted aggregates are read-only context"
            )
        else:
            source_contract_only_module = bool(module_services) and all(not service_exposes_persistent_object(item) for item in module_services)
            change_note = release_change_propagation_note(service.service_name, service.endpoint_name, source_contract_only_module)
        module_rows.append([
            service.home_module,
            service.domain,
            release_module_role_surface(),
            service.service_name,
            summarize_list(owned, max_items=5),
            ", ".join(item.public_contract for item in module_services) or "none",
            "上下游权威对象不得被本模块接管",
            change_note,
            service.purpose,
        ])

    lifecycle_bindings = max(len(aggregate_objects), profile_minimum(complexity_profile, "stage_02_lifecycle_mermaid_bindings"), 3)
    accepted_aggregates = authority_aggregate_by_id(context)
    accepted_service_ids = [
        str(row.get("service_id") or "").strip()
        for row in architecture_authority_model(context).get("services", [])
        if isinstance(row, dict) and str(row.get("service_id") or "").strip()
    ]
    for idx, obj in enumerate(aggregate_objects, start=1):
        accepted_aggregate = accepted_aggregates.get(obj)
        if accepted_aggregate:
            owner_service_id = str(accepted_aggregate.get("owner_service_id") or "").strip()
            writer_service_id = str(accepted_aggregate.get("writer_service_id") or owner_service_id).strip()
            aggregate_name = str(accepted_aggregate.get("aggregate_name") or obj).strip()
            operations = authority_operations_for_aggregate(context, obj)
            operation_ids = [str(row.get("operation_id") or "").strip() for row in operations if str(row.get("operation_id") or "").strip()]
            contract_ids = [str(row.get("contract_id") or "").strip() for row in operations if str(row.get("contract_id") or "").strip()]
            state_surface = authority_state_surface(accepted_aggregate)
            backing_schema = table_binding_map.get(obj, str(accepted_aggregate.get("table_name") or "authority-bound").strip())
            collaborators = [service_id for service_id in accepted_service_ids if service_id and service_id != owner_service_id]
            forbidden_writers = [service_id for service_id in accepted_service_ids if service_id and service_id != writer_service_id]
            aggregate_rows.append([
                aggregate_name,
                str(accepted_aggregate.get("aggregate_kind") or "aggregate-root").strip(),
                owner_service_id or "authority-bound",
                owner_service_id or "authority-bound",
                owner_service_id or "authority-bound",
                ", ".join(operation_ids) or "no accepted mutation operation",
                state_surface["states"],
                state_surface["events"],
                f"stateDiagram-v2 / diagram-{idx:02d}" if state_surface["states"].startswith("authority-bound") is False else "authority-bound / no inferred lifecycle diagram",
                state_surface["failure_exit"],
                str(accepted_aggregate.get("claim_ceiling") or "bounded by accepted P2 authority").strip(),
            ])
            responsibility_rows.append([
                owner_service_id or "authority-bound",
                aggregate_name,
                owner_service_id or "authority-bound",
                ", ".join(collaborators) or "none declared",
                ", ".join(contract_ids) or "accepted contracts only",
                ", ".join(forbidden_writers) or "none declared",
                f"only `{writer_service_id or owner_service_id}` may perform accepted writes",
                str(accepted_aggregate.get("statement") or accepted_aggregate.get("claim_ceiling") or "bounded by accepted P2 authority").strip(),
            ])
            table_spec = next((spec for spec in table_specs if str(spec.get("object_name") or "").strip() == obj), None)
            primary_identifiers = str(table_spec.get("pk") if table_spec else "authority-bound").strip()
            canonical_rows.append([
                aggregate_name,
                obj,
                owner_service_id or "authority-bound",
                primary_identifiers,
                state_surface["states"],
                backing_schema,
                ", ".join(operation_ids + contract_ids) or "no accepted operation surface",
                f"{aggregate_name} remains owned by `{owner_service_id or 'authority-bound'}` and written by `{writer_service_id or owner_service_id or 'authority-bound'}`.",
            ])
            for operation in operations:
                service_endpoint_rows.append([
                    str(operation.get("service_id") or "").strip(),
                    str(operation.get("service_id") or "").strip(),
                    str(operation.get("operation_id") or "").strip(),
                    str(operation.get("contract_id") or "").strip(),
                    aggregate_name,
                    "accepted P2 authority operation/contract mapping",
                ])
            lifecycle_rows.append([
                aggregate_name,
                "authority-declared lifecycle" if not state_surface["states"].startswith("authority-bound") else "authority-bound",
                writer_service_id or owner_service_id or "authority-bound",
                state_surface["states"],
                state_surface["events"],
                state_surface["mutation_guard"],
                state_surface["failure_exit"],
                f"diagram-{idx:02d}" if not state_surface["states"].startswith("authority-bound") else "no inferred diagram",
                f"writer remains `{writer_service_id or owner_service_id or 'authority-bound'}`; consumers do not acquire write authority",
            ])
            continue

        owner = owning_service_for_object(obj, services)
        object_profile = build_object_profile(owner, obj)
        ownership_profile = build_ownership_profile(obj, services, owner)
        backing_schema = table_binding_map.get(obj, to_snake(obj))
        aggregate_rows.append([
            obj,
            object_profile["aggregate_kind"],
            owner.domain,
            owner.home_module,
            owner.service_name,
            object_profile["authoritative_mutations"],
            object_profile["primary_states"],
            object_profile["emitted_events"],
            f"stateDiagram-v2 / diagram-{idx:02d}" if idx <= lifecycle_bindings else "stateDiagram-v2 / shared coverage",
            object_profile["failure_guardrail"],
            object_profile["public_boundary_status"],
        ])
        responsibility_rows.append([
            owner.domain,
            obj,
            owner.home_module,
            object_profile["collaborators"],
            object_profile["read_only_refs"],
            object_profile["must_not_write"],
            object_profile["conflict_rule"],
            ownership_profile["closure_note"],
        ])
        canonical_rows.append([
            obj,
            obj,
            owner.service_name,
            f"{to_snake(obj)}_id + tenant_id",
            "status + version + updated_at",
            backing_schema,
            f"{owner.public_contract}, {owner.endpoint_name}",
            f"{obj} 持续锚定在 {owner.service_name} 及其契约表面上，不再由下游自行发明。",
        ])
        service_endpoint_rows.append([
            owner.service_name,
            owner.home_module,
            owner.endpoint_name,
            owner.public_contract,
            obj,
            "主 owner 到 Stage-03 接口的直接映射",
        ])
        lifecycle_rows.append([
            obj,
            "stateDiagram-v2",
            owner.service_name,
            object_profile["primary_states"],
            object_profile["emitted_events"],
            object_profile["mutation_guard"],
            object_profile["failure_guardrail"],
            f"diagram-{idx:02d}" if idx <= lifecycle_bindings else "shared-diagram",
            ownership_profile["change_propagation_path"],
        ])

    mapped_services = {row[0] for row in service_endpoint_rows}
    for service in services:
        if service.service_name in mapped_services:
            continue
        service_endpoint_rows.append([
            service.service_name,
            service.home_module,
            service.endpoint_name,
            service.public_contract,
            service.owns_or_coordinates,
            "补充服务到接口的映射",
        ])

    dependency_rows = []
    if p1_product_topology_mode(context) == "independent-outcomes":
        grouped_services: dict[str, list[ServiceSpec]] = {}
        for service in services:
            group = authority_operation_topology_group(context, service.endpoint_name) or "review-bound-group"
            grouped_services.setdefault(group, []).append(service)
        for group, group_services in grouped_services.items():
            pairs = grouped_service_pairs(group_services)
            if pairs:
                for upstream, downstream in pairs:
                    dependency_rows.append([
                        upstream.home_module,
                        downstream.home_module,
                        f"{upstream.endpoint_name} 仅在 topology_group={group} 内以 accepted contract context 交接给 {downstream.endpoint_name}",
                        "accepted operation contract fields / aggregate identity",
                        f"{downstream.service_name} 只能消费该组内允许的上下文，不得取得 {upstream.owns_or_coordinates} 的额外写权限",
                        "组内所有权漂移则冻结该契约并抬升为 review-bound；不得影响其他 independent outcome",
                        "accepted group-local evidence may propagate forward; no cross-group execution prerequisite is created",
                    ])
            elif group_services:
                service = group_services[0]
                dependency_rows.append([
                    service.home_module,
                    service.home_module,
                    f"{service.endpoint_name} 在 topology_group={group} 内独立闭合，不依赖其他 accepted topology group",
                    "accepted operation contract fields / aggregate identity",
                    "无跨组写入或执行依赖",
                    "本组失败保持本组 blocked/review-bound，不阻断另一 independent outcome",
                    "shared trace/visibility may reference completed evidence but does not create prerequisite order",
                ])
        dependency_rows.append([
            "independent outcome evidence producers",
            "shared trace / visibility boundaries",
            "child-loop 或 parent-loop 完成后的 accepted evidence 可被 shared trace/visibility 读取；这不是 source loop 之间的执行交接",
            "accepted source_event_ref / privacy_marker / child_action_ref where applicable",
            "shared services consume bounded evidence only and do not write the source-loop aggregate",
            "任一 source outcome 未运行不得阻止另一 source outcome 独立完成",
            "evidence connection preserves P1 independent-outcomes topology",
        ])
    else:
        for upstream, downstream in grouped_service_pairs(services):
            dependency_rows.append([
                upstream.home_module,
                downstream.home_module,
                f"{upstream.endpoint_name} 以只读上下文交接给 {downstream.endpoint_name}",
                f"{to_snake(service_technical_name(upstream))}_id + trace_id",
                f"{downstream.service_name} 可以消费，但不得原地改写 {upstream.owns_or_coordinates}",
                "若所有权漂移，冻结该契约并把问题抬升为 review-bound 证据",
                f"{service_event_name(upstream)} 的新版本只能向前传播，不能回写下游已冻结事实",
            ])
        if not dependency_rows and services:
            service = services[0]
            dependency_rows.append([
                service.home_module,
                service.home_module,
                f"{service.endpoint_name} 在本模块内闭合自身状态边界",
                f"{to_snake(service_technical_name(service))}_id",
                "不得走表耦合回写捷径",
                "一旦所有权模糊，立即抬升为 review-bound 证据",
                "只允许追加式修订向前传播",
            ])

    event_target = max(profile_minimum(complexity_profile, "stage_02_domain_events"), min(len(aggregate_objects), max(len(services), 6)))
    if accepted_aggregates:
        events, event_vocabulary_rows, event_model_rows, event_rows = authority_event_driver_rows(
            context,
            aggregate_objects,
        )
    else:
        events, event_vocabulary_rows, event_model_rows, event_rows = event_driver_rows(
            services=services,
            aggregate_objects=aggregate_objects,
            event_target=event_target,
        )

    er_entities = unique_preserve([to_upper_entity(spec["object_name"]) for spec in table_specs] + [to_upper_entity(obj) for obj in aggregate_objects])
    er_entities = er_entities[: max(profile_minimum(complexity_profile, "stage_02_er_entities"), min(len(er_entities), 10))]
    if len(er_entities) < 2:
        er_entities = unique_preserve(er_entities + [to_upper_entity(service.owns_or_coordinates) for service in services[:2]])
    er_relationship_lines = [
        f"    {er_entities[idx]} ||--o{{ {er_entities[idx + 1]} : propagates_to"
        for idx in range(len(er_entities) - 1)
    ] or ["    ENTITY_A ||--o{ ENTITY_B : supports"]

    flow_modules = unique_preserve([service.home_module for service in services])
    flow_lines = []
    if flow_modules:
        for idx, module in enumerate(flow_modules):
            current = f'M{idx + 1}["{module}"]'
            if idx == 0:
                flow_lines.append(f"    {current}")
            if idx + 1 < len(flow_modules):
                nxt = f'M{idx + 2}["{flow_modules[idx + 1]}"]'
                flow_lines.append(f"    {current} --> {nxt}")
    else:
        flow_lines.append('    M1["core-module"] --> M2["delivery-module"]')

    narrative_objects = summarize_list(aggregate_objects, max_items=4)
    narrative_modules = summarize_list(flow_modules, max_items=4)
    narrative_event_names = summarize_list([str(row[0]) for row in event_vocabulary_rows], max_items=4)
    er_entities_block = ", ".join(er_entities)
    if accepted_aggregates:
        state_diagram_entries: list[str] = []
        for obj in aggregate_objects:
            aggregate = accepted_aggregates.get(obj)
            if not aggregate:
                continue
            state_surface = authority_state_surface(aggregate)
            states = [part.strip() for part in state_surface["states"].split("/") if part.strip() and not part.strip().startswith("authority-bound")]
            if not states:
                state_diagram_entries.append(
                    "\n".join(
                        [
                            "```text",
                            f"{obj}: no lifecycle states declared by accepted P2 authority; renderer does not infer one.",
                            "```",
                        ]
                    )
                )
                continue
            diagram_lines = ["```mermaid", "stateDiagram-v2", f"    [*] --> {to_pascal(states[0])}"]
            for left, right in zip(states, states[1:]):
                diagram_lines.append(f"    {to_pascal(left)} --> {to_pascal(right)}: accepted transition")
            diagram_lines.append("```")
            state_diagram_entries.append("\n".join(diagram_lines))
        state_diagrams_block = "\n".join(state_diagram_entries)
    else:
        state_diagrams_block = "\n".join(
            [
                "\n".join(
                    [
                        "```mermaid",
                        "stateDiagram-v2",
                        "    [*] --> Draft",
                        f"    Draft --> Active: validate {obj}",
                        f"    Active --> Revised: publish {to_snake(obj)} update",
                        "    Revised --> Active: accept additive change",
                        f"    Active --> Archived: retire {obj}",
                        "```",
                    ]
                )
                for obj in aggregate_objects
            ]
        )
    er_relationship_block = "\n".join(er_relationship_lines)
    flow_lines_block = "\n".join(flow_lines)

    stage = render_phase2_template(
        "stage-02-domain-decomposition.md.template",
        {
            "phase1_prd": phase1_prd,
            "complexity_profile": complexity_profile,
            "narrative_objects": narrative_objects,
            "narrative_modules": narrative_modules,
            "narrative_event_names": narrative_event_names,
            "business_proof_track_carryover_block": business_proof_constraint_block(context, indent=2),
            "domain_map_table": make_markdown_table(
                ["domain_name", "domain_role", "mission", "primary_objects", "primary_states", "must_not_own", "handoff_rule"],
                domain_rows,
            ),
            "module_map_table": make_markdown_table(
                ["module_name", "domain_name", "module_role", "primary_service", "owned_objects", "read_only_refs", "must_not_own", "change_propagation_path", "module_purpose"],
                module_rows,
            ),
            "service_candidates_table": make_markdown_table(
                ["service_name", "domain", "home_module", "service_type", "owns_or_coordinates", "primary_inbound", "primary_outbound", "purpose", "consistency_boundary"],
                service_rows,
            ),
            "canonical_object_structure_table": make_markdown_table(
                ["object_name", "authoritative_aggregate", "authoritative_service", "primary_identifiers", "state_or_version_anchor", "backing_schema_or_projection", "stage_03_contract_or_endpoint", "closure_note"],
                canonical_rows,
            ),
            "aggregate_catalog_table": make_markdown_table(
                ["aggregate_name", "aggregate_kind", "owning_domain", "owning_module", "authoritative_service", "authoritative_mutations", "primary_states", "emitted_events", "lifecycle_diagram", "failure_or_guardrail", "public_boundary_status"],
                aggregate_rows,
            ),
            "responsibility_matrix_table": make_markdown_table(
                ["domain", "aggregate / object", "authoritative owner", "collaborators", "read_only_refs", "must_not_write", "conflict_rule", "public-boundary note"],
                responsibility_rows,
            ),
            "service_endpoint_mapping_table": make_markdown_table(
                ["service_name", "home_module", "stage_03_endpoint_names", "public_contracts", "primary_owned_object", "mapping_note"],
                service_endpoint_rows,
            ),
            "aggregate_lifecycle_coverage_table": make_markdown_table(
                ["aggregate_name", "lifecycle_expression_type", "owner_writer", "state_set", "trigger_events", "mutation_guard", "terminal_or_failure_exit", "mermaid_binding", "closure_note"],
                lifecycle_rows,
            ),
            "dependency_collaboration_map_table": make_markdown_table(
                ["upstream_module", "downstream_module", "allowed_interaction", "required_artifact", "forbidden_backedge", "violation_penalty", "change_propagation_rule"],
                dependency_rows,
            ),
            "er_entities_block": er_entities_block,
            "domain_event_catalog_table": make_markdown_table(
                ["event_name", "producer", "consumer", "trigger_condition", "payload_shape", "ordering_semantics", "idempotency_rule"],
                events,
            ),
            "domain_event_vocabulary_table": make_markdown_table(
                ["event_name", "business_meaning", "producer", "consumer", "payload_contract", "timing", "idempotency", "downstream_usage_rule"],
                event_vocabulary_rows,
            ),
            "domain_event_model_catalog_table": make_markdown_table(
                ["event_model_id", "event_name", "trigger", "producer_consumer", "mutation_or_read_effect", "event_versioning_and_schema_posture", "p3_event_handoff", "review_bound_status"],
                event_model_rows,
            ),
            "root_namespace": root_namespace,
            "state_diagrams_block": state_diagrams_block,
            "er_relationship_block": er_relationship_block,
            "flow_lines_block": flow_lines_block,
        },
    )
    p1_handoff_block = render_p1_product_world_handoff_block(context)
    if p1_handoff_block:
        stage = stage.rstrip() + "\n\n" + p1_handoff_block
    non_operation_block = render_authority_non_operation_block(context)
    if non_operation_block:
        stage = stage.rstrip() + "\n\n" + non_operation_block
    return stage.rstrip() + "\n"


def render_stage_03(
    *,
    phase1_prd: Path,
    phase1_prototype_spec: Path | None,
    phase1_interaction_flow_contract: Path | None,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
    endpoint_specs: list[ServiceSpec],
    table_specs: list[dict[str, object]],
) -> str:
    root_namespace = str(context["root_namespace"])
    boundary_scope = str(context.get("boundary_scope", "tenant"))
    boundary_term = boundary_phrase(boundary_scope)
    async_completion_pack = async_completion_runtime_pack_for_context(context)
    schema_min = max(profile_minimum(complexity_profile, "stage_03_schema_tables"), 5)
    api_min = max(profile_minimum(complexity_profile, "stage_03_api_endpoints"), 5)
    tech_min = max(profile_minimum(complexity_profile, "stage_03_tech_selection_candidates"), 3)
    scenario_min = max(profile_minimum(complexity_profile, "stage_03_scenarios"), 5)
    contract_min = max(profile_minimum(complexity_profile, "stage_03_contract_trace_registry"), 3)
    phase1_page_map = _extract_page_map_from_prototype_spec(phase1_prototype_spec)
    phase1_interactions = _extract_interaction_rows_from_phase1_contract(phase1_interaction_flow_contract)
    phase1_flow_rows = _extract_flow_rows_from_phase1_contract(phase1_interaction_flow_contract)
    stage_03_design_defaults = load_stage_03_design_defaults()

    objects = unique_preserve(
        [str(spec["object_name"]) for spec in table_specs]
        + [service.owns_or_coordinates for service in services]
        + [str(item) for item in context.get("objects", [])]
    )
    objects = phase3_surface_safe_labels(objects)
    rendered_table_specs = table_specs[: max(schema_min, len(table_specs))]
    schema_summary_rows = [
        [
            str(spec["table_name"]),
            f"`{spec['owner']}`",
            str(spec["pk"]),
            str(spec["fk"]),
            str(spec["unique_constraints"]),
            str(spec["composite_indexes"]),
        ]
        for spec in rendered_table_specs
    ]

    data_ownership_rows: list[list[str]] = []
    accepted_aggregate_map = authority_aggregate_by_id(context)
    authority_model = architecture_authority_model(context)
    accepted_service_ids = [
        str(row.get("service_id") or "").strip()
        for row in authority_model.get("services", [])
        if isinstance(row, dict) and str(row.get("service_id") or "").strip()
    ]
    authority_operation_by_id = {
        str(row.get("operation_id") or "").strip(): row
        for row in authority_model.get("operations", [])
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
    authority_data_by_id = {
        str(row.get("decision_id") or "").strip(): row
        for row in authority_model.get("data_decisions", [])
        if isinstance(row, dict) and str(row.get("decision_id") or "").strip()
    }
    dedicated_carrier_by_id: dict[str, dict[str, object]] = {}
    for row in authority_model.get("durable_persistence_identity", []):
        if not isinstance(row, dict):
            continue
        carrier = row.get("durable_carrier") if isinstance(row.get("durable_carrier"), dict) else {}
        if str(carrier.get("kind") or "").strip() != "dedicated-record":
            continue
        carrier_id = str(carrier.get("carrier_id") or "").strip()
        if carrier_id:
            dedicated_carrier_by_id[carrier_id] = row
    for obj in objects[: max(schema_min, len(services) + 2)]:
        accepted_aggregate = accepted_aggregate_map.get(obj)
        if accepted_aggregate:
            owner_service_id = str(accepted_aggregate.get("owner_service_id") or "").strip()
            writer_service_id = str(accepted_aggregate.get("writer_service_id") or owner_service_id).strip()
            operations = authority_operations_for_aggregate(context, obj)
            contracts = [str(row.get("contract_id") or "").strip() for row in operations if str(row.get("contract_id") or "").strip()]
            operation_ids = [str(row.get("operation_id") or "").strip() for row in operations if str(row.get("operation_id") or "").strip()]
            read_consumers = [service_id for service_id in accepted_service_ids if service_id and service_id != writer_service_id]
            data_ownership_rows.append(
                [
                    obj,
                    f"`{owner_service_id or 'authority-bound'}`",
                    writer_service_id or "authority-bound",
                    ", ".join(read_consumers) or "none declared",
                    ", ".join(contracts) or "no accepted operation contract touches this aggregate",
                    ", ".join(operation_ids) or "accepted aggregate writer rule only",
                    f"no operation/service other than accepted writer `{writer_service_id or owner_service_id or 'authority-bound'}` may acquire write authority",
                    str(accepted_aggregate.get("statement") or accepted_aggregate.get("claim_ceiling") or "bounded by accepted P2 authority").strip(),
                ]
            )
            continue
        dedicated = dedicated_carrier_by_id.get(obj)
        if dedicated:
            operation_id = str(dedicated.get("operation_id") or "").strip()
            writer_service_id = str(dedicated.get("writer_service_id") or "").strip()
            operation = authority_operation_by_id.get(operation_id, {})
            contract_id = str(operation.get("contract_id") or "").strip()
            read_consumers = [service_id for service_id in accepted_service_ids if service_id and service_id != writer_service_id]
            data_decision = authority_data_by_id.get(obj, {})
            write_authority = f"{writer_service_id}.{operation_id}" if writer_service_id and operation_id else writer_service_id or operation_id or "authority-bound"
            data_ownership_rows.append(
                [
                    obj,
                    f"`{writer_service_id or 'authority-bound'}`",
                    write_authority,
                    ", ".join(read_consumers) or "none declared",
                    contract_id or "no accepted public contract",
                    f"{write_authority} -> {obj} -> downstream read/review surfaces",
                    f"only accepted writer `{write_authority}` may mutate `{obj}` directly",
                    str(
                        data_decision.get("statement")
                        or dedicated.get("reason")
                        or dedicated.get("claim_ceiling")
                        or "bounded by accepted P2 durable persistence authority"
                    ).strip(),
                ]
            )
            continue
        owner = owning_service_for_object(obj, services)
        profile = build_ownership_profile(obj, services, owner)
        data_ownership_rows.append(
            [
                obj,
                f"`{owner.home_module}`",
                owner.service_name,
                profile["read_consumers"],
                owner.public_contract,
                profile["change_propagation_path"],
                profile["forbidden_shortcut"],
                profile["closure_note"],
            ]
        )

    authority_mode = bool(architecture_authority_model(context))
    posture = authority_architecture_posture(context)
    if authority_mode:
        primary_storage = str(posture.get("primary_storage") or "review-bound; no storage technology accepted").strip()
        cache_posture = str(posture.get("cache_posture") or "review-bound; no cache posture accepted").strip()
        queue_posture = str(posture.get("queue_posture") or "review-bound; no queue/background-work posture accepted").strip()
        deployment_posture = str(posture.get("deployment_posture") or "review-bound; no deployment posture accepted").strip()
        security_posture = str(posture.get("security_posture") or "review-bound; no auth/provider/token/key-management posture accepted").strip()
        performance_posture = str(posture.get("performance_posture") or "review-bound; no numeric performance target accepted").strip()
        retention_posture = str(posture.get("retention_posture") or "review-bound; no retention duration accepted").strip()
        selected_shape = str(posture.get("selected_shape") or "review-bound; no application shape accepted").strip()
        why_selected = str(posture.get("why_selected") or "renderer does not select a technology posture beyond accepted P2 authority").strip()
        storage_layer_rows = [
            [
                primary_storage,
                "accepted authoritative first-wave metadata store posture",
                primary_storage,
                "review-bound; scale plan requires runtime evidence",
                "review-bound; long-term storage topology requires runtime evidence",
                "review-bound; no partition/shard strategy accepted",
                retention_posture,
                why_selected,
            ]
        ]
        data_model_posture_block = "\n".join(
            [
                f"  - primary_storage_shape: {primary_storage}",
                "  - storage_focus: only accepted aggregate fields, writers, contract evidence, and privacy/audit markers become canonical schema truth",
                "  - schema_freeze_rule: renderer may not add payload/status/tenant/trace fields unless accepted by P2 authority",
            ]
        )
        storage_strategy_posture_block = "\n".join(
            [
                f"  - initial: {primary_storage}",
                "  - one_year: review-bound; capacity evolution requires runtime evidence",
                "  - three_year: review-bound; physical decomposition/archive strategy is not accepted yet",
                "  - partition_strategy: review-bound; no tenant/time sharding assumption is promoted",
                f"  - archival_rule: {retention_posture}",
                f"  - throughput: {performance_posture}",
                f"  - latency: {performance_posture}",
                "  - growth: review-bound until measured volume exists",
                f"  - retention: {retention_posture}",
                "  - consistency_rule: only accepted writer-service and state/invariant decisions define mutation consistency; cache/fan-out ordering is not inferred",
            ]
        )
        stage03_security_posture_block = "\n".join(
            [
                "  - trust_boundaries: accepted service/writer boundaries plus accepted authorization/privacy/failure NORs",
                f"  - authn_authz_posture: {security_posture}",
                "  - auth_sequence_direction: review-bound unless explicitly accepted by P2 authority",
                "  - identity_session_mechanics: review-bound; no session credential type/lifetime/refresh mechanism is accepted by default",
                "  - audit_logging_hooks: preserve accepted audit/permission evidence only; no generic privileged-read taxonomy is promoted",
                "  - sensitive_data_handling: follow accepted aggregate data decisions and privacy/visibility NORs",
                "  - key_management_posture: review-bound unless explicitly accepted by P2 authority",
                "  - isolation_controls: derive only from accepted product/security boundary; renderer does not inject tenant isolation semantics",
            ]
        )
        technology_stack_posture_block = "\n".join(
            [
                "  - api_runtime: implementation language/runtime remains review-bound unless separately accepted",
                f"  - application_shape: {selected_shape}",
                f"  - primary_storage: {primary_storage}",
                f"  - cache: {cache_posture}",
                f"  - queue_posture: {queue_posture}",
                f"  - deployment_posture: {deployment_posture}",
            ]
        )
        bottleneck_posture_block = "\n".join(
            [
                "  - bottleneck: review-bound until runtime evidence identifies a dominant constraint",
                "  - measurement_plan: benchmark accepted operation contracts and dependency seams independently",
                f"  - threshold: {performance_posture}",
                "  - spike_scope: target only an accepted operation/aggregate/dependency whose evidence shows material risk",
            ]
        )
        optimum_posture_block = "\n".join(
            [
                f"  - optimum_under_current_constraints: {selected_shape}; {why_selected}",
                "  - claim_ceiling: first-wave accepted architecture posture only; no production sizing or physical-decomposition proof",
            ]
        )
        stage03_capacity_posture_block = "\n".join(
            [
                f"  - throughput: {performance_posture}",
                f"  - latency: {performance_posture}",
                "  - growth: review-bound until runtime volume evidence exists",
                f"  - retention: {retention_posture}",
                f"  - storage: {primary_storage}",
            ]
        )
    else:
        storage_layer_rows = list(stage_03_design_defaults["storage_layer_rows"])
        data_model_posture_block = "\n".join(
            [
                "  - primary_storage_shape: relational core with explicit payload JSON seams where contracts need flexibility",
                "  - storage_focus: workflow evidence, linkage, review closure, and audit-sensitive events",
                "  - schema_freeze_rule: public contracts evolve additively while identifiers and envelopes stay stable",
            ]
        )
        storage_strategy_posture_block = "\n".join(
            [
                "  - initial: PostgreSQL primary + Redis cache for bounded read acceleration",
                "  - one_year: retain hot-path indexes under 3x growth",
                "  - three_year: export immutable bundles and cold evidence without renaming contracts",
                "  - partition_strategy: tenant + time window on high-growth tables",
                "  - archival_rule: keep replay integrity while moving immutable bundles cold",
                "  - throughput: 120 request/min steady state and 4x burst during review windows",
                "  - latency: p95 <= 600 ms reads, p95 <= 5 min async workflows",
                "  - growth: 3x one-year, 5x three-year",
                "  - retention: 365d hot + 730d cold for audit-critical surfaces",
                "  - consistency_rule: authoritative command writes commit before cache refresh or async fan-out",
            ]
        )
        stage03_security_posture_block = "\n".join(
            [
                "  - trust_boundaries: API edge / policy check / domain module / audit evidence",
                f"  - authn_authz_posture: {boundary_term}-scoped RBAC with explicit mutation checks, privileged read review, and trace-linked operator accountability",
                "  - auth_sequence_direction: request enters API policy gate, resolves role/boundary claims, executes domain write, then records audit evidence before response",
                "  - token_posture: short-lived access tokens carry boundary, role, and traceable session claims",
                "  - audit_logging_hooks: mutating endpoints, privileged reads, review closure",
                "  - sensitive_data_handling: mask logs, encrypt at rest where required, preserve boundary-private evidence separation",
                "  - key_management_posture: scheduled rotation and secret-store isolation",
                "  - isolation_controls: enforce boundary_id on authoritative writes and cache namespaces when deployment requires it",
            ]
        )
        technology_stack_posture_block = "\n".join(
            [
                "  - api_runtime: TypeScript / service-layer runtime kept contract-first",
                "  - application_shape: modular monolith",
                "  - primary_storage: PostgreSQL",
                "  - cache: Redis only where bounded read amplification helps",
                f"  - queue_posture: {async_completion_pack['queue_posture_label']}",
                "  - deployment_posture: start simple and preserve module boundaries before physical decomposition",
            ]
        )
        bottleneck_posture_block = "\n".join(
            [
                "  - bottleneck: contract-heavy write paths plus replay-safe read refresh under burst",
                "  - measurement_plan: benchmark persistence, read-model refresh, and review query latency separately",
                "  - threshold: trigger design reconsideration if p95 review generation exceeds 2s or async completion exceeds 5 min at 4x burst",
                "  - spike_scope: benchmark high-growth tables with index plans and replay-friendly writes",
            ]
        )
        optimum_posture_block = "  - optimum_under_current_constraints: modular-monolith with explicit public contracts, indexed relational storage, and serialized conflict handling on shared surfaces"
        stage03_capacity_posture_block = "\n".join(
            [
                "  - throughput: 120 request/min steady state, 4x burst during review windows",
                "  - latency: p95 <= 600 ms synchronous reads",
                "  - growth: 3x one-year, 5x three-year evidence volume",
                "  - retention: 365d hot, 730d cold",
                "  - storage: workflow evidence dominates size and index pressure",
            ]
        )

    access_pattern_rows: list[list[str]] = []
    for spec in rendered_table_specs[: max(4, min(len(rendered_table_specs), 6))]:
        if spec.get("authority_bound"):
            indexed_fields = [
                str(row[0])
                for row in spec.get("field_rows", [])
                if isinstance(row, list) and len(row) >= 5 and str(row[4]).strip().casefold() not in {"", "none", "authority-defined"}
            ]
            access_pattern_rows.append(
                [
                    f"accepted lookup surface for `{spec['table_name']}`",
                    str(spec["table_name"]),
                    " + ".join(indexed_fields) or str(spec.get("pk") or "authority-bound"),
                    "authority-bound; measure before optimization",
                    str(spec["composite_indexes"]),
                    "do not add undeclared index keys merely to satisfy a generic access-pattern template",
                    f"benchmark only accepted access paths for `{spec['table_name']}` before adding indexes",
                ]
            )
            continue
        access_pattern_rows.append(
            [
                f"lookup `{spec['table_name']}` by ownership and recency",
                str(spec["table_name"]),
                f"tenant_id + {spec['pk']} + updated_at",
                "medium to high",
                str(spec["composite_indexes"]),
                "pay additive write cost to preserve stable read latency",
                f"benchmark `{spec['table_name']}` list and detail queries before widening rollout",
            ]
        )

    schema_entries: list[str] = []
    for idx, spec in enumerate(rendered_table_specs, start=1):
        field_table = make_markdown_table(
            ["field_name", "data_type", "nullable", "constraints", "index_hint"],
            [[str(a), str(b), str(c), str(d), str(e)] for a, b, c, d, e in spec["field_rows"]],
        )
        indented_field_table = "\n".join(f"        {line}" if line else "" for line in field_table.splitlines())
        schema_entries.append(
            "\n".join(
                [
                    f"    - table_{idx:02d}:",
                    f"      - table_name: `{spec['table_name']}`",
                    f"      - owner: `{spec['owner']}`",
                    f"      - object_name: `{spec['object_name']}`",
                    f"      - unique_constraints: `{spec['unique_constraints']}`",
                    f"      - composite_indexes: `{spec['composite_indexes']}`",
                    "      - write_rule: only the accepted writer mutates this table directly" if spec.get("authority_bound") else "      - write_rule: only the owning module mutates this table directly",
                    "      - trace_rule: preserve accepted primary identity and only declared trace/evidence fields" if spec.get("authority_bound") else "      - trace_rule: every row remains addressable by primary id and trace_id",
                    "      - field_registry:",
                    indented_field_table,
                ]
            )
        )

    sensitivity_rows: list[list[str]] = []
    for spec in rendered_table_specs:
        table_name = str(spec["table_name"])
        if spec.get("authority_bound"):
            sensitivity_rows.append(
                [
                    table_name,
                    str(spec.get("pii_level") or "authority-bound"),
                    str(spec.get("sensitive_fields") or "authority-bound"),
                    str(spec.get("masking_or_encryption") or "authority-bound"),
                    str(spec.get("retention_rule") or "authority-bound"),
                    str(spec.get("audit_access_rule") or "authority-bound"),
                    str(spec.get("compliance_note") or "bounded by accepted P2 authority"),
                ]
            )
            continue
        pii_level = "restricted" if any(token in table_name for token in ("tenant", "identity", "audit")) else "internal"
        sensitivity_rows.append(
            [
                table_name,
                pii_level,
                "tenant keys, actor ids, trace anchors",
                "mask in logs and encrypt at rest where required",
                "retain per review/audit posture",
                "privileged reads require explicit reason and traceability",
                "sensitivity posture follows object ownership and replay needs",
            ]
        )

    binding_preview_rows = build_binding_and_trace_rows(
        phase1_page_map=phase1_page_map,
        phase1_interactions=phase1_interactions,
        endpoint_specs=endpoint_specs,
        trace_rows=[],
        object_alias_hints=context.get("object_alias_hints", {}),
    )[0] if phase1_interactions else []
    request_mapping_lookup = build_request_mapping_lookup(binding_preview_rows)

    contract_entries: list[str] = []
    api_rows: list[list[str]] = []
    for idx, service in enumerate(endpoint_specs[: max(api_min, len(endpoint_specs))], start=1):
        authority_material = authority_contract_material(context, service)
        if authority_material is not None:
            request_example, response_example, schema_fields, authority_policies = authority_material
            rate_limit, pagination, response_profile, retryability, idempotency, failure_codes = generic_endpoint_policy(service)
            rate_limit = authority_policies.get("rate_limit_policy", "review-bound; no numeric rate limit accepted by current P2 authority")
            pagination = authority_policies.get("pagination_rule", pagination)
            retryability = authority_policies.get("retryability_policy", retryability)
            idempotency = authority_policies.get("idempotency_rule", idempotency)
            failure_codes = authority_policies.get("failure_codes", failure_codes)
        else:
            request_example = stage_03_request_example(service, request_mapping_lookup=request_mapping_lookup)
            response_example = stage_03_response_example(service)
            schema_fields = stage_03_contract_schema_fields(service, request_mapping_lookup=request_mapping_lookup)
            rate_limit, pagination, response_profile, retryability, idempotency, failure_codes = generic_endpoint_policy(service)
        schema_preview = make_markdown_table(
            ["field_name", "data_type", "nullable", "constraints", "index_hint"],
            [
                [
                    field.split(": ", 1)[0],
                    field.split(": ", 1)[1] if ": " in field else "string",
                    "false" if "|null" not in field and "null" not in field else "true",
                    "typed contract field",
                    "contract schema",
                ]
                for field in schema_fields[:16]
            ],
        )
        contract_entries.append(
            "\n".join(
                [
                    f"  - contract_{idx:02d}:",
                    f"    - contract_name: `{service.public_contract}`",
                    f"    - producer: `{service.service_name}`",
                    f"    - consumer: `{service.home_module}`",
                    "    - schema_form: `typed-request-response-envelope`",
                    f"    - failure_semantics: `{failure_codes}`",
                    "    - compatibility_rule: additive-only changes; identifiers and envelope fields stay stable",
                    "    - schema_fields:",
                    *[f"      - `{field}`" for field in schema_fields[:16]],
                    "    - json_schema:",
                    schema_preview,
                    "    - ts_interface:",
                    f"      - request_contract: `{service.endpoint_name}Request`",
                    f"      - response_contract: `{service.endpoint_name}Response`",
                ]
            )
        )
        api_rows.append(
            [
                service.endpoint_name,
                service.method,
                service.path,
                service.purpose,
                json.dumps(request_example, ensure_ascii=False),
                json.dumps(response_example, ensure_ascii=False),
                rate_limit,
                pagination,
                response_profile,
                retryability,
                idempotency,
                f"{failure_codes}; error_type split: business_error | system_error",
            ]
        )
    durable_persistence_rows: list[list[str]] = []
    for decision in architecture_authority_model(context).get("durable_persistence_identity", []):
        if not isinstance(decision, dict):
            continue
        carrier = decision.get("durable_carrier") if isinstance(decision.get("durable_carrier"), dict) else {}
        bindings = carrier.get("field_bindings", []) if isinstance(carrier.get("field_bindings"), list) else []
        binding_text = ", ".join(
            f"{str(row.get('identity_component') or '').strip()} -> {str(row.get('carrier_field') or '').strip()}"
            for row in bindings
            if isinstance(row, dict) and str(row.get("identity_component") or "").strip()
        ) or "none"
        enforcement = carrier.get("enforcement") if isinstance(carrier.get("enforcement"), dict) else {}
        enforcement_fields = enforcement.get("fields", []) if isinstance(enforcement.get("fields"), list) else []
        enforcement_text = f"{str(enforcement.get('mode') or '').strip()}({', '.join(str(item).strip() for item in enforcement_fields if str(item).strip())})"
        identity_components = decision.get("identity_components", []) if isinstance(decision.get("identity_components"), list) else []
        durable_persistence_rows.append(
            [
                str(decision.get("operation_id") or "").strip(),
                str(decision.get("persistence_mode") or "").strip(),
                str(decision.get("command_kind") or "").strip(),
                str(decision.get("idempotency_mode") or "").strip(),
                " + ".join(str(item).strip() for item in identity_components if str(item).strip()) or "none",
                str(carrier.get("kind") or "").strip(),
                str(carrier.get("carrier_id") or "").strip() or "none",
                binding_text,
                enforcement_text,
                str(decision.get("writer_service_id") or "").strip() or "none",
                str(decision.get("replay_behavior") or "").strip(),
                str(decision.get("reason") or "").strip(),
            ]
        )
    if authority_aggregate_by_id(context):
        _, _, event_model_rows, event_rows = authority_event_driver_rows(context, objects)
    else:
        _, _, event_model_rows, event_rows = event_driver_rows(
            services=services,
            aggregate_objects=objects,
            event_target=max(profile_minimum(complexity_profile, "stage_02_domain_events"), min(len(objects), max(len(services), 6))),
        )
    event_consumption_rows = [
        [
            row[1],
            row[6].replace("bind ", "").replace(" service/repository/unit intent", ""),
            row[4],
            row[5],
            row[6],
            "implementation claim remains capped until P3 runtime/test evidence exists",
        ]
        for row in event_model_rows
    ]

    all_trace_rows = list(context["all_trace_rows"])
    all_trace_ids = [row["trace_id"] for row in all_trace_rows]
    req_ac_ids = [row["trace_id"] for row in all_trace_rows if row.get("unit_type") in {"requirement", "acceptance-criteria"}] or all_trace_ids
    contract_id_groups = distribute_phase1_ids(req_ac_ids, max(contract_min, len(endpoint_specs)))
    contract_trace_rows: list[list[str]] = []
    for idx, service in enumerate(endpoint_specs[: max(contract_min, len(endpoint_specs))], start=1):
        upstream_ids = contract_id_groups[idx - 1] if idx - 1 < len(contract_id_groups) else contract_id_groups[-1]
        contract_trace_rows.append(
            [
                contract_trace_identity(context, service, idx),
                service.public_contract,
                "public-contract",
                f"`{service.home_module}`",
                "HANDOFF-0001",
                f"{service.endpoint_name} / {service.public_contract} remains visible in Stage-04 replay and implementation handoff",
                ", ".join(upstream_ids),
            ]
        )

    binding_rows, enrichment_rows, traceability_rows = build_binding_and_trace_rows(
        phase1_page_map=phase1_page_map,
        phase1_interactions=phase1_interactions,
        phase1_flow_rows=phase1_flow_rows,
        endpoint_specs=endpoint_specs,
        trace_rows=all_trace_rows,
        object_alias_hints=context.get("object_alias_hints", {}),
    ) if phase1_interactions else ([], [], [])
    binding_rows = reconcile_authority_binding_rows(context, endpoint_specs, binding_rows)
    enrichment_rows = reconcile_authority_enrichment_rows(context, binding_rows, enrichment_rows)

    interaction_flow_rows: list[list[str]] = []
    if p1_product_topology_mode(context) == "independent-outcomes":
        grouped_specs: dict[str, list[ServiceSpec]] = {}
        for spec in endpoint_specs:
            group = authority_operation_topology_group(context, spec.endpoint_name) or "review-bound-group"
            grouped_specs.setdefault(group, []).append(spec)
        flow_index = 1
        for group, group_specs in grouped_specs.items():
            if len(group_specs) == 1:
                current = group_specs[0]
                interaction_flow_rows.append(
                    [
                        f"flow_{flow_index:02d}",
                        f"{current.endpoint_name} -> local closure",
                        f"`{current.home_module}` remains inside topology group `{group}`",
                        current.owns_or_coordinates,
                        "local failure blocks only this topology group; it does not gate another independent outcome",
                        "retry/review within the same accepted topology group",
                        "preserves independent closure; shared evidence does not become a prerequisite",
                    ]
                )
                flow_index += 1
                continue
            for current, nxt in zip(group_specs, group_specs[1:]):
                interaction_flow_rows.append(
                    [
                        f"flow_{flow_index:02d}",
                        f"{current.endpoint_name} -> {nxt.endpoint_name}",
                        f"`{current.home_module}` and `{nxt.home_module}` stay inside topology group `{group}`",
                        f"{current.owns_or_coordinates} + {nxt.owns_or_coordinates}",
                        "failure remains local to this topology group and cannot activate/block a different independent outcome",
                        "refresh/replay inside the same accepted group",
                        "group-local composition only; no cross-group prerequisite is created",
                    ]
                )
                flow_index += 1
    else:
        endpoint_chain = endpoint_specs[: max(4, min(len(endpoint_specs), 6))]
        if endpoint_chain:
            for idx in range(max(1, len(endpoint_chain) - 1)):
                current = endpoint_chain[idx]
                nxt = endpoint_chain[idx + 1] if idx + 1 < len(endpoint_chain) else endpoint_chain[idx]
                interaction_flow_rows.append(
                    [
                        f"flow_{idx + 1:02d}",
                        f"{current.endpoint_name} -> {nxt.endpoint_name}",
                        f"`{current.home_module}` writes, `{nxt.home_module}` consumes read-only context",
                        f"{current.owns_or_coordinates} + {nxt.owns_or_coordinates}",
                        f"version mismatch or missing `{to_snake(service_technical_name(current))}_id` blocks the handoff",
                        "refresh state and replay with the same contract boundary",
                        "keeps ownership explicit while still allowing downstream composition",
                    ]
                )

    scenario_groups = distribute_phase1_ids(all_trace_ids or req_ac_ids, scenario_min)
    scenario_rows: list[list[str]] = []
    scenario_services = services[: max(scenario_min, min(len(services), 6))] or services[:1]
    independent_topology = p1_product_topology_mode(context) == "independent-outcomes"
    scenario_acceptance_suffix = (
        "the contract preserves ids, version anchors, and replay context; numeric performance acceptance follows the accepted P2 architecture posture and remains review-bound when no threshold is accepted"
        if authority_mode
        else "the contract must preserve ids, version anchors, and replay context within <= 600 ms for the synchronous path"
    )
    scenario_response_expectation = (
        "the response remains stable and additive; numeric performance acceptance follows the accepted P2 architecture posture"
        if authority_mode
        else "the response remains stable, additive, and <= 600 ms on the synchronous path"
    )
    scenario_category = "positive_path / authority-bounded" if authority_mode else "positive_path / quantified"
    for idx, service in enumerate(scenario_services, start=1):
        if independent_topology:
            group = authority_operation_topology_group(context, service.endpoint_name)
            same_group = [
                candidate
                for candidate in services
                if authority_operation_topology_group(context, candidate.endpoint_name) == group
            ]
            position = same_group.index(service) if service in same_group else 0
            peer = same_group[position + 1] if position + 1 < len(same_group) else service
        else:
            peer = services[idx] if idx < len(services) else service
        source_contract_read_only = authority_service_read_only(context, service)
        scenario_rows.append(
            [
                f"scenario_{idx:02d}",
                "domain operator",
                service.owns_or_coordinates,
                f"`{service.home_module}`, `{peer.home_module}`",
                f"{service.endpoint_name}, {peer.endpoint_name}",
                (
                    f"`{service.service_name}` exposes read-only source contract context for `{service.owns_or_coordinates}`"
                    if source_contract_read_only
                    else f"`{service.service_name}` remains the only writer for `{service.owns_or_coordinates}`"
                ),
                f"Given `{service.owns_or_coordinates}` exists, When `{service.endpoint_name}` runs, Then {scenario_acceptance_suffix}.",
                f"contract response diff for `{service.endpoint_name}`",
                scenario_category,
                f"`{service.owns_or_coordinates}` is available",
                f"`{service.endpoint_name}` is invoked",
                "the output remains contract-valid, replay-safe, and latency-bounded",
                "versioned ownership handoff",
                service.owns_or_coordinates,
                ", ".join(scenario_groups[idx - 1]) if idx - 1 < len(scenario_groups) else ", ".join(scenario_groups[-1]),
            ]
        )
    while len(scenario_rows) < scenario_min and services:
        service = services[len(scenario_rows) % len(services)]
        scenario_group_index = min(len(scenario_rows), len(scenario_groups) - 1)
        scenario_rows.append(
            [
                f"scenario_{len(scenario_rows) + 1:02d}",
                "domain operator",
                service.owns_or_coordinates,
                f"`{service.home_module}`",
                service.endpoint_name,
                "ownership remains explicit under replay",
                f"Given a valid request, When `{service.endpoint_name}` runs, Then the response must preserve the contract envelope and trace id.",
                f"response envelope check for `{service.endpoint_name}`",
                scenario_category,
                "a valid request exists",
                f"`{service.endpoint_name}` is invoked",
                scenario_response_expectation,
                "single-writer discipline",
                service.owns_or_coordinates,
                ", ".join(scenario_groups[scenario_group_index]),
            ]
        )
    authority_operation_mode = bool(services) and all(service.service_type == "authority-operation" for service in services)
    conflict_services = (
        [service for service in services if authority_operation_supports_concurrent_conflict(context, service.endpoint_name)][:2]
        if authority_operation_mode
        else services[:2]
    )
    for idx, service in enumerate(conflict_services, start=1):
        scenario_rows.append(
            [
                f"scenario_{len(scenario_rows) + 1:02d}",
                "parallel operators",
                service.owns_or_coordinates,
                f"`{service.home_module}`",
                service.endpoint_name if authority_operation_mode else f"{service.endpoint_name}, Update{service_technical_name(service)}Status",
                "concurrent writes must surface version conflict explicitly",
                f"Given two actors invoke `{service.endpoint_name}` for `{service.owns_or_coordinates}` concurrently, When stale version input is submitted, Then the system returns `409 version_conflict` and preserves the last committed record.",
                f"conflict replay and 409 assertion for `{service.endpoint_name}`",
                "concurrent_conflict / quantified",
                "two competing updates exist",
                "the stale update is submitted second",
                "the stale write is rejected with explicit conflict semantics",
                "retry on version conflict with versioned write guard",
                service.owns_or_coordinates,
                ", ".join(scenario_groups[min(idx - 1, len(scenario_groups) - 1)]),
            ]
        )

    if authority_mode:
        posture_id = str(posture.get("decision_id") or "P2-ARCH-POSTURE-REVIEW-BOUND").strip()
        selected_candidate = f"{selected_shape} / {primary_storage}"
        tech_rows = [
            [
                selected_candidate,
                "bounded by accepted writer/state decisions",
                performance_posture,
                "review-bound until runtime evidence",
                "high: explicit accepted boundaries",
                "bounded first-wave complexity",
                "bounded first-wave operations",
                "review-bound; ecosystem claims not required for current authority",
                security_posture,
                deployment_posture,
                "provider/internal seams only where accepted",
                "fits accepted operation/aggregate/dependency truth",
                "observability thresholds review-bound; accepted error/dependency signals remain visible",
                "reversible through stable accepted contracts",
                "no vendor selected unless explicitly named",
                "implementation learning remains review-bound",
                "stronger scaling/provider/runtime assumptions remain unproven",
                f"accepted P2 architecture posture `{posture_id}`",
                "selected-by-authority",
                str(posture.get("why_selected") or "accepted by P2 architecture authority").strip(),
            ],
            [
                "review-bound physical decomposition alternative",
                "not evaluated as accepted truth",
                "review-bound",
                "review-bound",
                "review-bound",
                "higher complexity than current accepted posture",
                "higher operational burden",
                "not evaluated",
                "must preserve accepted security boundaries",
                "not selected",
                "not selected",
                "not needed to realize current accepted architecture",
                "not evaluated",
                "contracts preserve future option",
                "review-bound",
                "review-bound",
                "would add unproven distributed-runtime assumptions",
                "no accepted P2 evidence",
                "not-selected-by-authority",
                "renderer does not invent a distributed alternative design",
            ],
            [
                "review-bound cache/queue expansion alternative",
                "not evaluated as accepted truth",
                "review-bound",
                "review-bound",
                "review-bound",
                "adds infrastructure before evidence",
                "adds operational dependencies",
                "not evaluated",
                "must preserve accepted privacy/permission boundaries",
                "not selected",
                "not selected",
                "current first-wave authority does not require it unless explicitly stated",
                "not evaluated",
                "ports/contracts preserve future option",
                "review-bound",
                "review-bound",
                "could turn optional infrastructure into hidden architecture truth",
                "no accepted P2 evidence",
                "not-selected-by-authority",
                "cache/queue choice stays bounded to the explicit architecture posture",
            ],
        ][:tech_min]
        alternative_candidates = [
            "\n".join(
                [
                    "  - candidate_01:",
                    f"    - candidate_name: {selected_candidate}",
                    "    - pros: explicitly accepted first-wave posture",
                    f"    - cons: {str(posture.get('claim_ceiling') or 'stronger runtime claims remain review-bound').strip()}",
                    "    - cost_burden: bounded first-wave complexity",
                    "    - fit_scenario: exact accepted operation/aggregate/dependency contract",
                    "    - reversibility: stable contracts preserve later physical/technology change",
                ]
            ),
            "\n".join(
                [
                    "  - candidate_02:",
                    "    - candidate_name: alternatives not accepted by current P2 authority",
                    "    - pros: keeps future option space explicit without pretending evaluation occurred",
                    "    - cons: cannot be implemented as canonical truth in P3",
                    "    - cost_burden: review-bound",
                    "    - fit_scenario: not selected",
                    "    - reversibility: revisit through a new P2 architecture decision",
                ]
            ),
        ]
        tradeoff_rows = [
            [
                str(row.get("decision_id") or row.get("realization_id") or f"P2-AUTH-{idx:02d}").strip(),
                str(row.get("statement") or row.get("mutation_guard") or "accepted authority rule").strip(),
                "renderer-generated alternative is not canonical",
                "accepted by current snapshot-bound P2 authority",
                str(row.get("negative_consequence") or row.get("claim_ceiling") or "stronger claim remains bounded").strip(),
                "revisit through P2 authority when inputs/evidence change",
                "input snapshot or runtime evidence changes materially",
            ]
            for idx, row in enumerate(authority_architecture_decision_rows(context)[: max(3, min(8, len(authority_architecture_decision_rows(context))))], start=1)
        ]
    else:
        tech_rows = list(stage_03_design_defaults["technology_selection_rows"])[:tech_min]
        alternative_candidates = [
            "\n".join(
                [
                    f"  - candidate_{idx:02d}:",
                    f"    - candidate_name: {candidate['candidate_name']}",
                    f"    - pros: {candidate['pros']}",
                    f"    - cons: {candidate['cons']}",
                    f"    - cost_burden: {candidate['cost_burden']}",
                    f"    - fit_scenario: {candidate['fit_scenario']}",
                    f"    - reversibility: {candidate['reversibility']}",
                ]
            )
            for idx, candidate in enumerate(
                stage_03_design_defaults["alternative_candidates"][
                    : max(profile_minimum(complexity_profile, "stage_03_alt_candidate_structure"), 4)
                ],
                start=1,
            )
        ]
        tradeoff_rows = list(stage_03_design_defaults["tradeoff_rows"])

    public_boundary_rows: list[list[str]] = []
    seen_contracts: set[str] = set()
    for spec in endpoint_specs:
        if spec.public_contract in seen_contracts:
            continue
        if spec.public_contract.rsplit(".", 1)[-1].endswith("List"):
            continue
        seen_contracts.add(spec.public_contract)
        namespace, _, public_name = spec.public_contract.rpartition(".")
        public_boundary_rows.append(
            [
                public_name or spec.public_contract,
                namespace or root_namespace,
                "active",
                spec.home_module,
                "contract",
                f"Stage-03 contract surface via {spec.endpoint_name}",
                f"stable boundary for {spec.purpose.lower()}",
            ]
        )

    mermaid_entities = unique_preserve([str(spec["table_name"]) for spec in rendered_table_specs[:14]])
    mermaid_nodes = [f'    T{idx + 1}["{name}"]' for idx, name in enumerate(mermaid_entities)]
    mermaid_edges = [
        f"    T{idx + 1} --> T{idx + 2}"
        for idx in range(len(mermaid_entities) - 1)
    ] or ["    T1 --> T2"]
    service_chain = unique_preserve([service.service_name for service in services[:6]])
    service_nodes = [f'    S{idx + 1}["{service_name}"]' for idx, service_name in enumerate(service_chain)]
    service_edges = [
        f"    S{idx + 1} --> S{idx + 2}"
        for idx in range(len(service_chain) - 1)
    ] or ["    S1 --> S2"]

    stage = render_phase2_template(
        "stage-03-data-interface-design.md.template",
        {
            "phase1_prd": phase1_prd,
            "complexity_profile": complexity_profile,
            "data_model_posture_block": data_model_posture_block,
            "data_ownership_map_table": make_markdown_table(
                ["object", "owning module", "write authority", "read_only_consumers", "public_contract", "change_propagation_path", "forbidden_shortcut", "closure note"],
                data_ownership_rows,
            ),
            "storage_strategy_table": make_markdown_table(
                ["storage_layer", "first_wave_role", "initial_plan", "one_year_plan", "three_year_plan", "partition_or_shard_rule", "archive_or_cleanup_rule", "why_selected"],
                storage_layer_rows,
            ),
            "storage_strategy_posture_block": storage_strategy_posture_block,
            "access_pattern_and_index_strategy_table": make_markdown_table(
                ["access_pattern", "touched_tables", "predicate_sort_join_keys", "expected_selectivity", "proposed_index", "write_cost_note", "validation_hook"],
                access_pattern_rows,
            ),
            "schema_summary_table": make_markdown_table(
                ["table_name", "ownership", "pk", "fk", "unique_constraints", "composite_indexes"],
                schema_summary_rows,
            ),
            "schema_entries_block": "\n".join(schema_entries),
            "durable_persistence_identity_table": make_markdown_table(
                ["operation_id", "persistence_mode", "command_kind", "idempotency_mode", "identity_components", "carrier_kind", "carrier_id", "field_bindings", "enforcement", "writer_service_id", "replay_behavior", "reason"],
                durable_persistence_rows,
            ) if durable_persistence_rows else "- no accepted durable persistence identity decisions",
            "data_sensitivity_and_compliance_matrix_table": make_markdown_table(
                ["table_name", "pii_level", "sensitive_fields", "masking_or_encryption", "retention_rule", "audit_access_rule", "compliance_note"],
                sensitivity_rows,
            ),
            "contract_entries_block": "\n".join(contract_entries),
            "api_endpoint_draft_table": make_markdown_table(
                ["endpoint_name", "method", "path", "purpose", "request_body_example", "response_body_example", "rate_limit_policy", "pagination_rule", "response_profile", "retryability_policy", "idempotency_rule", "failure_codes"],
                api_rows,
            ),
            "stage_02_event_name_carry_forward_table": make_markdown_table(
                ["stage_02_event_name", "stage_03_touchpoints", "preserved_name_or_alias", "mapping_note"],
                event_rows,
            ),
            "event_model_direct_consumption_table": make_markdown_table(
                ["event_name", "contract_touchpoint", "mutation_or_read_effect", "versioning_and_schema_posture", "p3_event_handoff", "claim_ceiling"],
                event_consumption_rows,
            ),
            "contract_trace_registry_table": make_markdown_table(
                ["trace_id", "trace_subject", "subject_type", "owning_module", "downstream_artifact_id", "verification_hook", "upstream_trace_ids"],
                contract_trace_rows,
            ),
            "interaction_matrix_p2_enrichment_block": make_markdown_table(
                ["interaction_id", "page_id", "input_schema_ref", "display_field_set", "validation_rules", "enabled_rule", "value_source", "internal_exposure", "error_state", "readiness_status", "blocked_reason"],
                enrichment_rows,
            ) if enrichment_rows else "- no Phase-1 interaction-flow contract was available, so P2-owned interaction enrichment could not be compiled",
            "data_service_binding_matrix_block": make_markdown_table(
                ["service_binding_id", "interaction_id", "use_case_id", "transaction_group_id", "binding_mode", "domain_service", "api_endpoint", "http_method", "request_field_mapping", "response_field_mapping", "db_entities", "rbac_policy", "audit_event", "failure_codes", "server_generated_fields", "ui_refresh_targets", "handoff_materialization", "readiness_status", "blocked_reason"],
                binding_rows,
            ) if binding_rows else "- no Phase-1 interaction-flow contract was available, so binding matrix generation remained blocked",
            "traceability_matrix_block": make_markdown_table(
                ["trace_row_id", "req_id", "use_case_id", "page_id", "interaction_id", "service_binding_id", "api_endpoint", "test_ids", "closure_gate", "canonical_page_id", "audience_mode", "exposure_scope", "staleness_marker", "upstream_trace_ids"],
                traceability_rows,
            ) if traceability_rows else "- no interaction-level binding chain was available, so traceability remained API/test-skewed",
            "interaction_flow_table": make_markdown_table(
                ["flow_name", "producer_consumer_chain", "write_boundary", "primary_data_surfaces", "failure_detection", "rollback_or_compensation", "closure_note"],
                interaction_flow_rows,
            ),
            "boundary_term": boundary_term,
            "stage03_security_posture_block": stage03_security_posture_block,
            "technology_stack_posture_block": technology_stack_posture_block,
            "bottleneck_posture_block": bottleneck_posture_block,
            "optimum_posture_block": optimum_posture_block,
            "stage03_capacity_posture_block": stage03_capacity_posture_block,
            "queue_posture_label": async_completion_pack["queue_posture_label"],
            "technology_selection_evaluation_matrix_table": make_markdown_table(
                ["candidate_name", "reliability", "performance_capacity", "scalability", "maintainability", "development_cost", "operations_cost", "ecosystem_maturity", "security_compliance_posture", "deployment_complexity", "integration_cost", "integration_fit", "observability", "migration_path", "vendor_risk", "learning_curve", "failure_mode", "evidence_sources", "final_decision", "rejection_reason"],
                tech_rows,
            ),
            "alternative_candidates_block": "\n".join(alternative_candidates),
            "scenario_coverage_matrix_table": make_markdown_table(
                ["scenario", "actors", "entities", "modules", "contracts / endpoints", "failure_note", "acceptance_criteria", "measurement_hook", "scenario_category", "given", "when", "then", "coordination_strategy", "shared_resource", "upstream_trace_ids"],
                scenario_rows,
            ),
            "key_tradeoff_decisions_table": make_markdown_table(
                ["decision_id", "chosen_posture", "rejected_alternative", "why_selected", "cost_paid_now", "reversibility", "revisit_trigger"],
                tradeoff_rows,
            ),
            "root_namespace": root_namespace,
            "public_boundary_registry_table": make_markdown_table(
                ["public_name", "namespace", "status", "owner_module", "artifact_type", "origin", "closure_note"],
                public_boundary_rows,
            ),
            "data_mermaid_flowchart_block": "\n".join(mermaid_nodes + mermaid_edges),
            "service_mermaid_flowchart_block": "\n".join(service_nodes + service_edges),
        },
    )
    p1_handoff_block = render_p1_product_world_handoff_block(context)
    if p1_handoff_block:
        stage = stage.rstrip() + "\n\n" + p1_handoff_block
    non_operation_block = render_authority_non_operation_block(context)
    if non_operation_block:
        stage = stage.rstrip() + "\n\n" + non_operation_block
    return stage.rstrip() + "\n"



def render_stage_04(
    *,
    phase1_prd: Path,
    phase1_prototype_spec: Path | None = None,
    phase1_prototype_prompt_pack: Path | None = None,
    phase1_interaction_flow_contract: Path | None = None,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
    contract_names: list[str],
    endpoint_names: list[str],
    stage_03_text: str,
    stage_02_5_text: str,
) -> str:
    supports_deferred_extension_seam = context_supports_deferred_extension_seam(context)
    business_proof_handoff = business_proof_constraint_block(context, indent=4)
    thesis_architecture_handoff = business_architecture_pressure_block(context, indent=4)
    deferred_seam_heading = "deferred_attribution_seam" if supports_deferred_extension_seam else "deferred_extension_seam"
    deferred_seam_line = (
        "attribution remains deferred / placeholder-backed and is not upgraded into MVP-complete proof by Stage-04"
        if supports_deferred_extension_seam
        else "deferred extension remains placeholder-backed and is not upgraded into MVP-complete proof by Stage-04"
    )
    sequence_target = max(profile_minimum(complexity_profile, "stage_04_sequence_diagrams"), 2)
    service_count = len(services)
    wp_target = max(profile_minimum(complexity_profile, "stage_04_work_packages"), 6 if service_count >= 9 else 5 if service_count >= 7 else 4)
    rbi_target = max(profile_minimum(complexity_profile, "stage_04_rbi_items"), 3)
    verification_target = max(profile_minimum(complexity_profile, "stage_04_design_verification"), 3)
    replay_target = max(profile_minimum(complexity_profile, "stage_04_verification_replay"), 2)
    observability_target = max(profile_minimum(complexity_profile, "stage_04_observability"), 3)
    rbi_trace_target = max(profile_minimum(complexity_profile, "stage_04_rbi_trace_registry"), 3)
    unresolved_technical_names = [
        item
        for item in context.get("unresolved_technical_names", [])
        if isinstance(item, dict) and str(item.get("source_label", "")).strip()
    ]
    if unresolved_technical_names:
        rbi_trace_target = max(rbi_trace_target, rbi_target + len(unresolved_technical_names))
    prototype_spec_path = _resolve_phase1_prototype_asset_path(
        phase1_prd,
        explicit_path=phase1_prototype_spec,
        candidate_names=("prototype-spec.md", "prototype_spec.md"),
    )
    prototype_prompt_pack_path = _resolve_phase1_prototype_asset_path(
        phase1_prd,
        explicit_path=phase1_prototype_prompt_pack,
        candidate_names=("prototype-prompt-pack.md", "prototype_prompt_pack.md"),
    )
    interaction_flow_contract_path = _resolve_phase1_interaction_flow_contract_path(
        phase1_prd,
        explicit_path=phase1_interaction_flow_contract,
    )
    phase1_page_map = _extract_page_map_from_prototype_spec(prototype_spec_path)
    page_blueprint_rows: list[list[str]] = []
    if phase1_page_map:
        primary_surfaces = [page["page_name"] for page in phase1_page_map if str(page.get("page_name") or "").strip()]
        primary_surface_lines: list[str] = []
        for page in phase1_page_map:
            page_name = str(page.get("page_name") or "").strip()
            if not page_name:
                continue
            suffix_parts: list[str] = []
            page_role = str(page.get("page_role") or "").strip()
            blueprint_type = str(page.get("page_blueprint_type") or "").strip()
            surface_variant = str(page.get("surface_variant") or "").strip()
            audience_mode = str(page.get("audience_mode") or "").strip()
            if page_role:
                suffix_parts.append(f"role: {page_role}")
            if blueprint_type:
                suffix_parts.append(f"blueprint: {blueprint_type}")
            if audience_mode:
                suffix_parts.append(f"audience: {audience_mode}")
            if surface_variant:
                suffix_parts.append(f"variant: {surface_variant}")
            if blueprint_type:
                page_blueprint_rows.append(
                    [
                        page_name,
                        blueprint_type,
                        page_role or "not-stated",
                        str(page.get("canonical_page_id") or "").strip() or "not-stated",
                        surface_variant or "not-stated",
                        audience_mode or "not-stated",
                        str(page.get("session_role_source") or "").strip() or "not-stated",
                        str(page.get("auth_entry_route") or "").strip() or "not-stated",
                        str(page.get("auth_entry_label") or "").strip() or "not-stated",
                        str(page.get("workspace_entry_roles") or "").strip() or "not-stated",
                        str(page.get("route_reachability_mode") or "").strip() or "not-stated",
                        str(page.get("navigation_scope") or "").strip() or "not-stated",
                        str(page.get("handoff_visibility") or "").strip() or "not-stated",
                        str(page.get("forbidden_exposure") or "").strip() or "not-stated",
                    ]
                )
            primary_surface_lines.append(f"    - `{page_name}`" + (f" ({'; '.join(suffix_parts)})" if suffix_parts else ""))
        primary_surface_block = "\n".join(primary_surface_lines)
        surface_provenance = "phase1-prototype-spec"
    else:
        primary_surfaces = semantic_primary_surfaces(context) or extract_dynamic_primary_surfaces(str(context.get("text", "")), phase1_page_map)
        primary_surface_block = "\n".join(f"    - `{surface}`" for surface in primary_surfaces)
        surface_provenance = "phase1-ia-inferred"
    prototype_spec_ref = str(prototype_spec_path) if prototype_spec_path else ""
    prototype_prompt_pack_ref = str(prototype_prompt_pack_path) if prototype_prompt_pack_path else ""
    interaction_flow_contract_ref = str(interaction_flow_contract_path) if interaction_flow_contract_path else ""
    page_blueprint_block = (
        make_markdown_table(
            [
                "surface",
                "page_blueprint_type",
                "page_role",
                "canonical_page_id",
                "surface_variant",
                "audience_mode",
                "session_role_source",
                "auth_entry_route",
                "auth_entry_label",
                "workspace_entry_roles",
                "route_reachability_mode",
                "navigation_scope",
                "handoff_visibility",
                "forbidden_exposure",
            ],
            page_blueprint_rows,
        )
        if page_blueprint_rows
        else "not available; fallback surface inference is active"
    )

    all_trace_rows = list(context["all_trace_rows"])
    all_trace_ids = [row["trace_id"] for row in all_trace_rows]
    req_ac_ids = [row["trace_id"] for row in all_trace_rows if row.get("unit_type") in {"requirement", "acceptance-criteria"}] or all_trace_ids
    rbi_id_groups = distribute_phase1_ids(req_ac_ids, rbi_trace_target)

    work_package_rows: list[list[str]] = []
    independent_topology = p1_product_topology_mode(context) == "independent-outcomes"
    if independent_topology and services:
        wp_ids = [f"WP-A{idx}" for idx in range(1, max(len(services), wp_target) + 1)]
        previous_wp_by_group: dict[str, str] = {}
        for idx, service in enumerate(services):
            wp_id = wp_ids[idx]
            group = authority_operation_topology_group(context, service.endpoint_name) or "review-bound-group"
            depends_on = previous_wp_by_group.get(group, "none")
            previous_wp_by_group[group] = wp_id
            service_scope = f"`{service.service_name}` / topology_group=`{group}`"
            linked_rbi = f"RBI-{min(idx + 1, rbi_target):02d}"
            work_package_rows.append(
                [
                    wp_id,
                    f"stabilize {service_scope} contract, group-local replay, and implementation handoff",
                    f"the slice preserves `{group}` closure without creating a dependency on another independent topology group",
                    f"{4 + (idx % 3)}d",
                    depends_on,
                    linked_rbi,
                ]
            )
        while len(work_package_rows) < wp_target:
            idx = len(work_package_rows)
            work_package_rows.append(
                [
                    wp_ids[idx],
                    "cross-cutting authority verification without product-flow sequencing",
                    "verify accepted privacy, trace, dependency, and claim ceilings without adding execution prerequisites",
                    "4d",
                    "none",
                    f"RBI-{min(idx + 1, rbi_target):02d}",
                ]
            )
    else:
        service_chunks = round_robin_chunks([service.service_name for service in services], wp_target)
        wp_ids = [f"WP-A{idx}" for idx in range(1, wp_target + 1)]
        for idx, wp_id in enumerate(wp_ids):
            owned_services = service_chunks[idx] if idx < len(service_chunks) else []
            service_scope = ", ".join(f"`{name}`" for name in owned_services[:3]) or "`cross-cutting`"
            depends_on = "none" if idx == 0 else wp_ids[idx - 1]
            linked_rbi = f"RBI-{min(idx + 1, rbi_target):02d}"
            work_package_rows.append(
                [
                    wp_id,
                    f"stabilize {service_scope} contracts, replay paths, and implementation handoff",
                    f"the slice preserves ownership, contract naming, and replay evidence for {service_scope}",
                    f"{4 + (idx % 3)}d",
                    depends_on,
                    linked_rbi,
                ]
            )

    nested_wp_entries = [
        "\n".join(
            [
                f"    - `{row[0]}`:",
                f"      - completion_signal: {row[2]}",
                f"      - acceptance_criteria: Given the design slice is implemented, When verification replay is run, Then {row[2]}.",
            ]
        )
        for row in work_package_rows[: max(profile_minimum(complexity_profile, "stage_04_slice_acceptance"), 2)]
    ]

    deadlines = ["2026-04-15", "2026-04-18", "2026-04-20", "2026-04-22", "2026-04-25", "2026-04-28"]
    rbi_rows: list[list[str]] = []
    for idx in range(rbi_target):
        owner_service = services[idx % len(services)] if services else None
        wp = work_package_rows[min(idx, len(work_package_rows) - 1)][0]
        blocks = work_package_rows[min(idx + 1, len(work_package_rows) - 1)][0]
        label = owner_service.service_name if owner_service else "cross-cutting slice"
        rbi_rows.append(
            [
                f"RBI-{idx + 1:02d}",
                f"runtime proof is still required for `{label}` contract and replay posture",
                "H" if idx < 2 else "M" if idx < 4 else "L",
                wp,
                "platform owner" if idx % 2 == 0 else "workflow owner",
                blocks,
                deadlines[idx % len(deadlines)],
                f"RBI-{idx + 1:02d} -> {wp}",
            ]
        )
    for item in unresolved_technical_names:
        rbi_id = f"RBI-{len(rbi_rows) + 1:02d}"
        source_label = str(item.get("source_label", "")).strip()
        technical_name = str(item.get("technical_name", "")).strip()
        technical_slug = str(item.get("technical_slug", "")).strip()
        wp = work_package_rows[0][0] if work_package_rows else "WP-A1"
        rbi_rows.append(
            [
                rbi_id,
                (
                    f"`{source_label}` lacks a usable ASCII technical name; generated placeholder "
                    f"`{technical_name}` / `{technical_slug}` must remain review-bound until a source-backed "
                    "semantic alias is supplied"
                ),
                "H",
                wp,
                "architecture owner",
                wp,
                "before P3 implementation closure",
                f"{rbi_id} -> {wp}",
            ]
        )

    design_verification_rows: list[list[str]] = []
    for idx, service in enumerate(services[:verification_target], start=1):
        source_contract_read_only = authority_service_read_only(context, service)
        design_verification_rows.append(
            [
                f"`{service.service_name}` boundary preserved",
                "pass",
                "contract review + replay walkthrough",
                f"{service.endpoint_name} contract and ownership table",
                (
                    f"`{service.service_name}` remains read-only/source-contract-bound for `{service.owns_or_coordinates}`"
                    if source_contract_read_only
                    else f"`{service.service_name}` remains the only writer for `{service.owns_or_coordinates}`"
                ),
                "runtime proof pending",
                f"RBI-{min(idx, len(rbi_rows)):02d} / {work_package_rows[min(idx - 1, len(work_package_rows) - 1)][0]}",
            ]
        )
    while len(design_verification_rows) < verification_target:
        design_verification_rows.append(
            [
                f"cross-module handoff {len(design_verification_rows) + 1:02d}",
                "pass",
                "replay walkthrough",
                "handoff package",
                "ownership, ids, and trace anchors survive the handoff",
                "runtime proof pending",
                f"RBI-{min(len(design_verification_rows) + 1, len(rbi_rows)):02d}",
            ]
        )

    replay_rows: list[list[str]] = []
    replay_count = max(replay_target, 2)
    replay_id_groups = distribute_phase1_ids(all_trace_ids or req_ac_ids, replay_count)
    for idx in range(replay_count):
        current = services[idx % len(services)] if services else None
        if current is not None and independent_topology:
            group = authority_operation_topology_group(context, current.endpoint_name)
            same_group = [
                candidate
                for candidate in services
                if authority_operation_topology_group(context, candidate.endpoint_name) == group
            ]
            position = same_group.index(current) if current in same_group else 0
            nxt = same_group[position + 1] if position + 1 < len(same_group) else current
        else:
            nxt = services[(idx + 1) % len(services)] if services else None
        artifact = f"{current.owns_or_coordinates if current else 'core_object'} + {nxt.owns_or_coordinates if nxt else 'downstream_object'}"
        replay_rows.append(
            [
                f"P2-RP-{idx + 1:02d}",
                f"{current.endpoint_name if current else 'contract'} handoff replay",
                "scenario-replay" if idx % 2 else "contract-walkthrough",
                artifact,
                "ownership, contract ids, and replay anchors stay explicit",
                "implementation intake keeps the same closure rules visible",
                "pass",
                design_verification_rows[min(idx, len(design_verification_rows) - 1)][0],
                "IMPL-STG00-INPUT-0001",
                f"{work_package_rows[min(idx, len(work_package_rows) - 1)][0]}, {rbi_rows[min(idx, len(rbi_rows) - 1)][0]}",
                ", ".join(replay_id_groups[min(idx, len(replay_id_groups) - 1)]),
            ]
        )

    rbi_trace_rows: list[list[str]] = []
    for idx, rbi in enumerate(rbi_rows[:rbi_trace_target], start=1):
        ids = rbi_id_groups[idx - 1] if idx - 1 < len(rbi_id_groups) else rbi_id_groups[-1]
        rbi_trace_rows.append(
            [
                f"P2-RT-{idx:02d}",
                rbi[0],
                rbi[3],
                "IMPL-STG00-INPUT-0001",
                f"{rbi[0]} remains linked to `{rbi[3]}` until replay or runtime evidence closes the risk",
                "implementation intake must preserve RBI owner, blocker, and closure rule",
                ", ".join(ids),
            ]
        )

    metric_map = {
        "transactional": "write_latency, version_conflict_rate",
        "orchestration": "handoff_latency, replay_dedupe_rate",
        "read-assembly": "cache_hit_rate, refresh_latency",
        "policy": "deny_rate, policy_check_latency",
        "domain": "contract_validation_failures, publish_latency",
        "support": "append_latency, evidence_gap_rate",
    }
    observability_rows: list[list[str]] = []
    authority_mode = bool(architecture_authority_model(context))
    for idx, service in enumerate(services[:observability_target], start=1):
        if authority_mode:
            structured_logs = f"operation_id={service.endpoint_name} + aggregate_id={service.owns_or_coordinates} + accepted trace/error context when declared"
            threshold = "review-bound; no numeric SLO is promoted without accepted P2 evidence"
            alert_rule = f"alert on accepted failure codes/dependency-unavailable signals for `{service.endpoint_name}`; numeric thresholds remain review-bound"
            owner = service.domain
        else:
            structured_logs = f"tenant_id + {to_snake(service_technical_name(service))}_id + trace_id"
            threshold = "p95 <= 600ms for sync paths; async queues remain bounded"
            alert_rule = f"alert when `{service.endpoint_name}` error rate or latency exceeds threshold"
            owner = "platform owner" if idx % 2 else "workflow owner"
        observability_rows.append(
            [
                f"surface-{idx:02d}",
                service.service_name,
                metric_map.get(service.service_type, "request_latency, error_rate"),
                structured_logs,
                alert_rule,
                threshold,
                owner,
                f"do not widen rollout until `{service.service_name}` evidence matches its accepted claim ceiling",
            ]
        )

    environment_prerequisites = format_nested_bullets(derive_environment_dependency_prerequisites(stage_03_text, stage_02_5_text), indent=4)
    if authority_mode:
        adr_rows = authority_architecture_decision_rows(context)
        adr_list = "\n".join(
            f"    - `{str(row.get('decision_id') or '').strip()}` {str(row.get('title') or row.get('statement') or '').strip()}"
            for row in adr_rows[:10]
        )
    else:
        adr_titles_for_list = [str(item) for item in context.get("adr_titles", [])]
        adr_list = "\n".join(f"    - `AD-{idx:02d}` {title}" for idx, title in enumerate(adr_titles_for_list[:10], start=1))
    contract_list = "\n".join(f"    - `{name}`" for name in unique_preserve(contract_names))

    posture = authority_architecture_posture(context)
    if authority_mode:
        selected_shape = str(posture.get("selected_shape") or "review-bound; no application shape accepted").strip()
        primary_storage = str(posture.get("primary_storage") or "review-bound; no primary storage accepted").strip()
        queue_posture = str(posture.get("queue_posture") or "review-bound; no queue/background-work posture accepted").strip()
        deployment_posture = str(posture.get("deployment_posture") or "review-bound; no deployment posture accepted").strip()
        security_posture = str(posture.get("security_posture") or "review-bound; no identity/key-management posture accepted").strip()
        convergence_direction = f"{selected_shape}; preserve exact accepted contracts, writer boundaries, P1 topology, and review-bound claim ceilings"
        optimality_review_block = "\n".join(
            [
                "  - acceptable_baseline:",
                f"    - {selected_shape} / {primary_storage}",
                "  - optimal_candidate:",
                "    - current snapshot-bound P2 architecture posture; renderer does not substitute a template technology stack",
                "  - acceptable_vs_optimal_verdict:",
                "    - bounded implementation-planning posture only; production optimality remains unproven",
                "  - why_optimal_not_just_acceptable:",
                f"    - {str(posture.get('why_selected') or 'accepted by current P2 architecture authority').strip()}",
                "  - reversibility_posture:",
                f"    - stable accepted contracts keep later technology changes reviewable; queue posture now: {queue_posture}",
                "  - strongest_supported_readiness_label:",
                "    - `implementation-planning-bounded`",
                "  - realizability_judgment:",
                f"    - realizable for bounded implementation planning under deployment posture: {deployment_posture}",
            ]
        )
        implementation_must_preserve_block = "\n".join(
            [
                "    - exact accepted operation and contract identifiers",
                "    - accepted aggregate owner/writer boundaries and typed fields",
                "    - P1 product topology and accepted NOR/privacy/authorization rules",
                "    - accepted dependency dispositions and provider-neutral seams",
                "    - RBI/review-bound claim ceilings; P3 must not promote missing SLO/provider/retention/auth details",
            ]
        )
        identity_key_posture_block = "\n".join(
            [
                f"  - security_posture: {security_posture}",
                "  - auth_vendor_slot: review-bound unless P2 authority names a provider",
                "  - identity_session_lifecycle: review-bound unless P2 authority accepts exact lifetime/refresh/revocation mechanics",
                "  - key_posture: review-bound unless P2 authority accepts exact key storage/rotation mechanics; no hard-coded runtime secrets",
            ]
        )
        workflow_spine_posture = (
            "independent topology-group closure + shared evidence/visibility without cross-group prerequisite -> implementation intake"
            if independent_topology
            else "accepted operation/contract progression -> replay verification -> implementation intake"
        )
    else:
        convergence_direction = "modular monolith with explicit public boundary and replay-ready handoff"
        optimality_review_block = "\n".join(
            [
                "  - acceptable_baseline:",
                "    - modular monolith + relational core + typed public contracts",
                "  - optimal_candidate:",
                "    - keep the current baseline and delay physical decomposition until runtime proof demands it",
                "  - acceptable_vs_optimal_verdict:",
                "    - acceptable now and optimal under first-wave certainty / staffing / runtime constraints",
                "  - why_optimal_not_just_acceptable:",
                "    - preserves traceability, replay, and design honesty without overcommitting operations complexity",
                "  - reversibility_posture:",
                "    - later queue/storage/provider changes remain reversible because contract names and ownership stay stable",
                "  - strongest_supported_readiness_label:",
                "    - `implementation-planning-ready`",
                "  - realizability_judgment:",
                "    - realizable as designed for implementation planning, with explicit RBI chain preserved for unresolved runtime proofs",
            ]
        )
        implementation_must_preserve_block = "\n".join(
            [
                "    - public-boundary names",
                "    - tenant policy and audit edges",
                "    - typed contract identifiers and replay evidence references",
                "    - RBI ownership and blockers",
            ]
        )
        identity_key_posture_block = "\n".join(
            [
                "  - auth_vendor_slot: keep policy provider replaceable behind the contract boundary",
                "  - key_posture: scheduled rotation, break-glass audit, no hard-coded runtime secrets",
            ]
        )
        workflow_spine_posture = "ownership handoff -> replay verification -> implementation intake"

    gantt_lines = [
        "```mermaid",
        "gantt",
        "    title First-Wave Implementation Handoff",
        "    dateFormat  YYYY-MM-DD",
        "    section Work Packages",
    ]
    wp_task_ids = {row[0]: f"a{idx + 1}" for idx, row in enumerate(work_package_rows)}
    for idx, row in enumerate(work_package_rows[:8]):
        wp_id = row[0]
        task_id = wp_task_ids[wp_id]
        duration_match = re.search(r"\d+d", str(row[3]))
        duration = duration_match.group(0) if duration_match else "4d"
        dependency = str(row[4]).strip()
        if dependency != "none" and dependency in wp_task_ids:
            schedule = f"after {wp_task_ids[dependency]}"
        else:
            schedule = "2026-04-08"
        gantt_lines.append(f"    {wp_id} :{task_id}, {schedule}, {duration}")
    gantt_lines.append("```")
    gantt_block = "\n".join(gantt_lines)

    mermaid_sequences: list[str] = []
    if services:
        if independent_topology:
            grouped_sequence_services: list[list[ServiceSpec]] = []
            seen_groups: set[str] = set()
            for service in services:
                group = authority_operation_topology_group(context, service.endpoint_name) or "review-bound-group"
                if group in seen_groups:
                    continue
                seen_groups.add(group)
                grouped_sequence_services.append(
                    [candidate for candidate in services if authority_operation_topology_group(context, candidate.endpoint_name) == group]
                )
            sequence_sources = [group[0] for group in grouped_sequence_services if group]
            sequence_count = min(max(sequence_target, len(sequence_sources)), len(sequence_sources))
        else:
            sequence_sources = services
            sequence_count = min(sequence_target, max(1, len(services) - 1))
        for idx in range(sequence_count):
            current = sequence_sources[idx]
            if independent_topology:
                group = authority_operation_topology_group(context, current.endpoint_name)
                same_group = [
                    candidate
                    for candidate in services
                    if authority_operation_topology_group(context, candidate.endpoint_name) == group
                ]
                nxt = same_group[1] if len(same_group) > 1 else current
            else:
                nxt = services[idx + 1] if idx + 1 < len(services) else services[idx]
            mermaid_sequences.append(
                "\n".join(
                    [
                        "```mermaid",
                        "sequenceDiagram",
                        "    participant U as Operator",
                        f"    participant S{idx + 1} as {current.service_name}",
                        f"    participant S{idx + 2} as {nxt.service_name}",
                        "    participant A as AuditTrail",
                        f"    U->>S{idx + 1}: invoke {current.endpoint_name}",
                        f"    S{idx + 1}->>S{idx + 2}: hand off {current.owns_or_coordinates} context",
                        f"    S{idx + 2}->>A: record replay-safe audit evidence",
                        f"    A-->>S{idx + 2}: audit persistence confirmed",
                        f"    S{idx + 2}-->>U: return versioned acknowledgement for {nxt.owns_or_coordinates}",
                        "```",
                    ]
                )
            )
    if not mermaid_sequences:
        mermaid_sequences.append(
            "\n".join(
                [
                    "```mermaid",
                    "sequenceDiagram",
                    "    participant U as Operator",
                    "    participant A as CoreService",
                    "    participant B as ReviewService",
                    "    participant T as AuditTrail",
                    "    U->>A: submit workflow request",
                    "    A->>B: contract-bound handoff",
                    "    B->>T: record audit event",
                    "    T-->>B: persistence confirmed",
                    "    B-->>U: replay-safe acknowledgement",
                    "```",
                ]
            )
        )

    stage = render_phase2_template(
        "stage-04-design-convergence.md.template",
        {
            "phase1_prd": phase1_prd,
            "complexity_profile": complexity_profile,
            "architecture_convergence_adr_list": adr_list,
            "contract_list": contract_list,
            "convergence_direction": convergence_direction,
            "optimality_review_block": optimality_review_block,
            "implementation_must_preserve_block": implementation_must_preserve_block,
            "identity_key_posture_block": identity_key_posture_block,
            "workflow_spine_posture": workflow_spine_posture,
            "gantt_block": gantt_block,
            "deferred_seam_heading": deferred_seam_heading,
            "deferred_seam_line": deferred_seam_line,
            "business_proof_handoff": business_proof_handoff,
            "thesis_architecture_handoff": thesis_architecture_handoff,
            "surface_provenance": surface_provenance,
            "primary_surface_block": primary_surface_block,
            "prototype_spec_ref": prototype_spec_ref,
            "prototype_prompt_pack_ref": prototype_prompt_pack_ref,
            "interaction_flow_contract_ref": interaction_flow_contract_ref,
            "page_blueprint_block": page_blueprint_block,
            "design_verification_notes_table": make_markdown_table(
                ["check_item", "result", "verification_method", "evidence", "acceptance_rule", "residual_gap", "linked_rbi_or_wp"],
                design_verification_rows,
            ),
            "verification_replay_evidence_table": make_markdown_table(
                ["replay_id", "scenario_or_contract", "replay_type", "source_artifacts", "expected_outcome", "observed_outcome", "verdict", "evidence_ref", "downstream_artifact_id", "linked_rbi_or_wp", "upstream_trace_ids"],
                replay_rows,
            ),
            "unresolved_risks_table": make_markdown_table(
                ["rbi_id", "item", "risk_level", "spike_wp", "responsible_party", "blocks_which_wp", "resolution_deadline", "rbi_matrix"],
                rbi_rows,
            ),
            "rbi_trace_registry_table": make_markdown_table(
                ["trace_id", "rbi_id", "bound_wp", "downstream_artifact_id", "verification_hook", "handoff_rule", "upstream_trace_ids"],
                rbi_trace_rows,
            ),
            "observability_readiness_table": make_markdown_table(
                ["surface", "service_or_flow", "key_metrics", "structured_logs", "alert_rule", "slo_or_threshold", "owner", "rollout_guardrail"],
                observability_rows,
            ),
            "implementation_task_sketch_table": make_markdown_table(
                ["wp_id", "scope", "acceptance_criteria", "estimated_effort", "depends_on", "linked_rbi_or_slice"],
                work_package_rows,
            ),
            "nested_wp_entries_block": "\n".join(nested_wp_entries),
            "environment_prerequisites": environment_prerequisites,
            "mermaid_sequences_block": "\n".join(mermaid_sequences),
        },
    )
    return stage.rstrip() + "\n"


def write_generation_sidecars(
    *,
    output_dir: Path,
    phase1_prd: Path,
    case_name: str,
    version: str,
    complexity_profile: str,
    complexity_report: dict[str, object],
    owner: str,
    existing_system_architecture_change_intake: Path | None = None,
) -> None:
    generation_report = {
        "case_name": case_name,
        "version": version,
        "phase1_prd": str(phase1_prd),
        "existing_system_architecture_change_intake": (
            str(existing_system_architecture_change_intake)
            if existing_system_architecture_change_intake
            else ""
        ),
        "complexity_profile": complexity_profile,
        "complexity_report": complexity_report,
        "owner": owner,
        "generator": "scripts/phase2/run_phase2_fresh_generation.py",
    }
    write_cross_phase_profiled_surface(
        output_dir,
        "phase2",
        "phase-2-first-version-generation-report.json",
        json.dumps(generation_report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    audit = inspect_case(output_dir)
    write_cross_phase_profiled_surface(
        output_dir,
        "phase2",
        "phase-2-first-pass-audit.json",
        json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )


def _phase1_claims_for_phase2(phase1_prd: Path) -> tuple[list[Any], str, Path | None]:
    return phase1_claims_for_phase2(phase1_prd)


__all__ = [name for name in globals() if not name.startswith("__")]
