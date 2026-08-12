"""Mechanical P2 authority projection helpers for the P2 -> P3 Action Card bridge.

These helpers do not decide architecture or implementation truth. They only map
accepted structured P2 identities onto implementation-component/action-card
surfaces so P2 can publish the projection and P3 can recompute the expected
projection for convergence checks.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


def authority_rows(authority: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    return [dict(row) for row in authority.get(key, []) if isinstance(row, dict)]


def _strings(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in values if item))


def _unique_structured_rows(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            continue
        key = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if key in seen:
            continue
        seen.add(key)
        result.append(dict(item))
    return result


def _structured_rows_equal(left: Any, right: Any) -> bool:
    left_rows = sorted(
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for item in _unique_structured_rows(left)
    )
    right_rows = sorted(
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for item in _unique_structured_rows(right)
    )
    return left_rows == right_rows


def project_s3_durable_persistence_decisions(value: Any) -> list[dict[str, Any]]:
    """Mechanically convert accepted P2/S2 durable rows into S3 binding shape."""
    result: list[dict[str, Any]] = []
    for raw in _unique_structured_rows(value):
        carrier = raw.get("durable_carrier") if isinstance(raw.get("durable_carrier"), Mapping) else {}
        enforcement = carrier.get("enforcement") if isinstance(carrier.get("enforcement"), Mapping) else {}
        bindings = carrier.get("field_bindings") if isinstance(carrier.get("field_bindings"), list) else []
        result.append({
            "operationId": str(raw.get("operation_id") or ""),
            "persistenceMode": str(raw.get("persistence_mode") or ""),
            "commandKind": str(raw.get("command_kind") or ""),
            "idempotencyMode": str(raw.get("idempotency_mode") or ""),
            "identityComponents": _strings(raw.get("identity_components")),
            "durableCarrier": {
                "kind": str(carrier.get("kind") or ""),
                "carrierId": str(carrier.get("carrier_id") or ""),
                "fieldBindings": [
                    {"identityComponent": str(row.get("identity_component") or ""), "carrierField": str(row.get("carrier_field") or "")}
                    for row in bindings if isinstance(row, Mapping)
                ],
                "enforcement": {"mode": str(enforcement.get("mode") or ""), "fields": _strings(enforcement.get("fields"))},
            },
            "writerServiceId": str(raw.get("writer_service_id") or ""),
            "replayBehavior": str(raw.get("replay_behavior") or ""),
            "reason": str(raw.get("reason") or ""),
            "claimCeiling": str(raw.get("claim_ceiling") or ""),
        })
    return result


def render_durable_persistence_action_card_lines(value: Any) -> list[str]:
    """Render accepted durable rows without adding implementation judgment."""
    rows = _unique_structured_rows(value)
    if not rows:
        return []
    lines = ["", "### Durable Persistence Authority"]
    for row in rows:
        carrier = row.get("durable_carrier") if isinstance(row.get("durable_carrier"), Mapping) else {}
        enforcement = carrier.get("enforcement") if isinstance(carrier.get("enforcement"), Mapping) else {}
        bindings = carrier.get("field_bindings") if isinstance(carrier.get("field_bindings"), list) else []
        identity = ", ".join(_strings(row.get("identity_components"))) or "none"
        binding_text = ", ".join(
            f"{item.get('identity_component', 'review-bound')} -> {item.get('carrier_field', 'review-bound')}"
            for item in bindings if isinstance(item, Mapping)
        ) or "none"
        fields = ", ".join(_strings(enforcement.get("fields"))) or "none"
        lines += [
            f"- operation_id: `{row.get('operation_id', 'review-bound')}`",
            f"  - persistence_mode: `{row.get('persistence_mode', 'review-bound')}`",
            f"  - command_kind: `{row.get('command_kind', 'review-bound')}`",
            f"  - idempotency_mode: `{row.get('idempotency_mode', 'review-bound')}`",
            f"  - identity_components: {identity}",
            f"  - durable_carrier: `{carrier.get('kind', 'review-bound')}:{carrier.get('carrier_id', 'review-bound') or 'none'}`",
            f"  - field_bindings: {binding_text}",
            f"  - enforcement: `{enforcement.get('mode', 'review-bound')}` on {fields}",
            f"  - writer_service_id: `{row.get('writer_service_id', '') or 'none'}`",
            f"  - replay_behavior: `{row.get('replay_behavior', 'review-bound')}`",
            f"  - reason: {row.get('reason', 'review-bound')}",
            f"  - ceiling: {row.get('claim_ceiling', 'review-bound')}",
        ]
    return lines


def project_component_authority(
    component: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach exact accepted operation/aggregate/writer/topology identities."""
    projected = dict(component)
    operations = authority_rows(authority, "operation_portfolio")
    aggregates = authority_rows(authority, "aggregate_and_writer_decisions")
    operation_by_id = {
        str(row.get("operation_id") or "").strip(): row
        for row in operations
        if str(row.get("operation_id") or "").strip()
    }
    aggregate_by_table = {
        str(row.get("table_name") or "").strip(): row
        for row in aggregates
        if str(row.get("table_name") or "").strip()
    }
    aggregate_by_id = {
        str(row.get("aggregate_id") or "").strip(): row
        for row in aggregates
        if str(row.get("aggregate_id") or "").strip()
    }
    data_decisions = authority_rows(authority, "data_and_interaction_decisions")
    data_by_id = {
        str(row.get("decision_id") or "").strip(): row
        for row in data_decisions
        if str(row.get("decision_id") or "").strip()
    }
    durable_decisions = authority_rows(authority, "durable_persistence_identity_decisions")

    component_type = str(projected.get("component_type") or "").strip()
    aggregate_ids: list[str] = []
    aggregate_names: list[str] = []
    service_ids: list[str] = []
    owner_service_ids: list[str] = []
    writer_service_ids: list[str] = []
    contract_ids: list[str] = []
    topology_groups: list[str] = []

    if component_type == "Service":
        related_operations = [
            operation_id
            for operation_id in _strings(projected.get("related_operations", []))
            if operation_id in operation_by_id
        ]
        projected["related_operations"] = related_operations
        for operation_id in related_operations:
            operation = operation_by_id[operation_id]
            aggregate_id = str(operation.get("aggregate_id") or "").strip()
            service_id = str(operation.get("service_id") or "").strip()
            contract_id = str(operation.get("contract_id") or "").strip()
            topology_group = str(operation.get("topology_group") or "").strip()
            if aggregate_id:
                aggregate_ids.append(aggregate_id)
                aggregate = aggregate_by_id.get(aggregate_id, {})
                aggregate_names.append(str(aggregate.get("aggregate_name") or "").strip())
                owner_service_ids.append(str(aggregate.get("owner_service_id") or "").strip())
                writer_service_ids.append(str(aggregate.get("writer_service_id") or "").strip())
            service_ids.append(service_id)
            contract_ids.append(contract_id)
            topology_groups.append(topology_group)
        projected["authority_projection_status"] = "authority-bound" if related_operations else "review-bound-unmatched"

    elif component_type == "Repository":
        table_names = _strings(projected.get("related_schema_or_domain_objects", []))
        matched_aggregates = [aggregate_by_table[name] for name in table_names if name in aggregate_by_table]
        for aggregate in matched_aggregates:
            aggregate_ids.append(str(aggregate.get("aggregate_id") or "").strip())
            aggregate_names.append(str(aggregate.get("aggregate_name") or "").strip())
            owner = str(aggregate.get("owner_service_id") or "").strip()
            writer = str(aggregate.get("writer_service_id") or "").strip()
            owner_service_ids.append(owner)
            writer_service_ids.append(writer)
            service_ids.append(owner)
        aggregate_set = set(_unique(aggregate_ids))
        related_operations = [
            str(operation.get("operation_id") or "").strip()
            for operation in operations
            if str(operation.get("aggregate_id") or "").strip() in aggregate_set
            and str(operation.get("operation_id") or "").strip()
        ]

        matched_dedicated: list[tuple[dict[str, Any], dict[str, Any]]] = []
        table_name_set = set(table_names)
        matched_table_data = [
            row
            for row in data_decisions
            if str(row.get("table_name") or "").strip() in table_name_set
            and str(row.get("operation_id") or "").strip() in operation_by_id
        ]
        for data_row in matched_table_data:
            operation_id = str(data_row.get("operation_id") or "").strip()
            decision_id = str(data_row.get("decision_id") or "").strip()
            if operation_id:
                related_operations.append(operation_id)
            if decision_id:
                projected["source_ids"] = _unique(_strings(projected.get("source_ids", [])) + [decision_id])
        for durable in durable_decisions:
            carrier = durable.get("durable_carrier") if isinstance(durable.get("durable_carrier"), dict) else {}
            if str(carrier.get("kind") or "").strip() != "dedicated-record":
                continue
            carrier_id = str(carrier.get("carrier_id") or "").strip()
            data_row = data_by_id.get(carrier_id)
            if data_row is None or str(data_row.get("table_name") or "").strip() not in table_name_set:
                continue
            matched_dedicated.append((durable, data_row))
            operation_id = str(durable.get("operation_id") or "").strip()
            writer = str(durable.get("writer_service_id") or "").strip()
            if operation_id:
                related_operations.append(operation_id)
            if writer:
                service_ids.append(writer)
                writer_service_ids.append(writer)
            if carrier_id:
                projected["source_ids"] = _unique(_strings(projected.get("source_ids", [])) + [carrier_id])

        projected["related_operations"] = _unique(related_operations)
        for operation_id in projected["related_operations"]:
            operation = operation_by_id.get(operation_id, {})
            contract_ids.append(str(operation.get("contract_id") or "").strip())
            topology_groups.append(str(operation.get("topology_group") or "").strip())
            service_ids.append(str(operation.get("service_id") or "").strip())
        projected["authority_projection_status"] = "authority-bound" if matched_aggregates or matched_dedicated or matched_table_data else "review-bound-unmatched"
        if matched_aggregates:
            projected["source_ids"] = _unique(
                _strings(projected.get("source_ids", [])) + _unique(aggregate_ids)
            )

    projected["aggregate_ids"] = _unique(aggregate_ids)
    projected["aggregate_names"] = _unique(aggregate_names)
    projected["service_ids"] = _unique(service_ids)
    projected["owner_service_ids"] = _unique(owner_service_ids)
    projected["writer_service_ids"] = _unique(writer_service_ids)
    projected["contract_ids"] = _unique(contract_ids)
    projected["topology_groups"] = _unique(topology_groups)
    return projected


def project_component_semantics(
    component: Mapping[str, Any],
    authority: Mapping[str, Any],
    base_p1_trace_ids: list[str],
) -> dict[str, Any]:
    """Project accepted semantic guardrails relevant to one component."""
    related_operations = set(_strings(component.get("related_operations", [])))
    aggregate_ids = set(_strings(component.get("aggregate_ids", [])))
    service_ids = {
        item
        for field in ("service_ids", "owner_service_ids", "writer_service_ids")
        for item in _strings(component.get(field, []))
    }
    operation_contracts = [
        row
        for row in authority_rows(authority, "operation_portfolio")
        if str(row.get("operation_id") or "").strip() in related_operations
    ]
    aggregate_boundaries = [
        row
        for row in authority_rows(authority, "aggregate_and_writer_decisions")
        if str(row.get("aggregate_id") or "").strip() in aggregate_ids
    ]
    all_non_operations = authority_rows(authority, "non_operation_realizations")
    component_non_operations = [
        row for row in all_non_operations if str(row.get("owner") or "").strip() in service_ids
    ]
    project_guardrails = [
        row for row in all_non_operations if str(row.get("owner") or "").strip() == "P2 host Agent"
    ]
    component_non_operation_ids = {
        str(row.get("realization_id") or "").strip() for row in component_non_operations
    }
    project_guardrail_ids = {
        str(row.get("realization_id") or "").strip() for row in project_guardrails
    }
    p1_trace_ids = list(base_p1_trace_ids)
    project_guardrail_p1_trace_ids: list[str] = []
    for disposition in authority_rows(authority, "commitment_dispositions"):
        if str(disposition.get("disposition") or "") != "non-operation-realization":
            continue
        realization_ids = set(_strings(disposition.get("realization_ids", [])))
        commitment_id = str(disposition.get("commitment_id") or "").strip()
        if commitment_id and realization_ids.intersection(component_non_operation_ids):
            p1_trace_ids.append(commitment_id)
        if commitment_id and realization_ids.intersection(project_guardrail_ids):
            project_guardrail_p1_trace_ids.append(commitment_id)
    p1_trace_ids = _unique(p1_trace_ids)
    project_guardrail_p1_trace_ids = _unique(project_guardrail_p1_trace_ids)

    state_constraints = [
        row
        for row in authority_rows(authority, "state_invariant_policy_failure_decisions")
        if str(row.get("aggregate_id") or "").strip() in aggregate_ids
    ]
    dependency_constraints = [
        row
        for row in authority_rows(authority, "dependency_dispositions")
        if set(_strings(row.get("commitment_ids", []))).intersection(p1_trace_ids)
    ]
    durable_persistence_decisions = [
        row
        for row in authority_rows(authority, "durable_persistence_identity_decisions")
        if str(row.get("operation_id") or "").strip() in related_operations
    ]
    architecture_decisions: list[dict[str, Any]] = []
    evidence_scope = set(p1_trace_ids) | set(project_guardrail_p1_trace_ids)
    for row in authority_rows(authority, "data_and_interaction_decisions"):
        if (
            str(row.get("operation_id") or "").strip() in related_operations
            or str(row.get("aggregate_id") or "").strip() in aggregate_ids
            or str(row.get("decision_type") or "") == "architecture-posture"
            or set(_strings(row.get("evidence_refs", []))).intersection(evidence_scope)
        ):
            architecture_decisions.append(row)

    semantic_rows = (
        operation_contracts
        + aggregate_boundaries
        + component_non_operations
        + project_guardrails
        + state_constraints
        + dependency_constraints
        + durable_persistence_decisions
        + architecture_decisions
    )
    semantic_claim_ceilings = _unique(
        [str(row.get("claim_ceiling") or "").strip() for row in semantic_rows]
    )
    semantic_source_ids = _unique(
        [str(authority.get("decision_id") or "").strip()]
        + [str(row.get("contract_id") or "").strip() for row in operation_contracts]
        + [str(row.get("aggregate_id") or "").strip() for row in aggregate_boundaries]
        + [str(row.get("realization_id") or "").strip() for row in component_non_operations]
        + [str(row.get("realization_id") or "").strip() for row in project_guardrails]
        + project_guardrail_p1_trace_ids
        + [str(row.get("decision_id") or "").strip() for row in state_constraints]
        + [str(row.get("dependency_id") or "").strip() for row in dependency_constraints]
        + [str(row.get("operation_id") or "").strip() for row in durable_persistence_decisions]
        + [str(row.get("decision_id") or "").strip() for row in architecture_decisions]
    )
    return {
        "p1_trace_ids": p1_trace_ids,
        "operation_contracts": operation_contracts,
        "aggregate_boundaries": aggregate_boundaries,
        "non_operation_realizations": component_non_operations,
        "project_guardrails": project_guardrails,
        "project_guardrail_p1_trace_ids": project_guardrail_p1_trace_ids,
        "state_constraints": state_constraints,
        "dependency_constraints": dependency_constraints,
        "durable_persistence_decisions": durable_persistence_decisions,
        "architecture_decisions": architecture_decisions,
        "semantic_claim_ceilings": semantic_claim_ceilings,
        "semantic_source_ids": semantic_source_ids,
    }


def _acd_rank(value: object) -> int:
    return {"ACD-3": 3, "ACD-2": 2, "ACD-1": 1, "ACD-0": 0}.get(str(value or "").strip().upper(), -1)


def build_component_action_card_obligation_projection(
    *,
    catalog_rows: list[dict[str, Any]],
    depth_rows: list[dict[str, Any]],
    authority: Mapping[str, Any],
    authority_bound: bool,
) -> list[dict[str, Any]]:
    """Mechanically combine component/depth rows with accepted authority."""
    depth_by_operation = {str(row.get("operation_id") or "").strip(): row for row in depth_rows}
    result: list[dict[str, Any]] = []
    for component in catalog_rows:
        related_operations = _strings(component.get("related_operations", []))
        related_depth = [depth_by_operation[item] for item in related_operations if item in depth_by_operation]
        if related_depth:
            selected = max(related_depth, key=lambda row: _acd_rank(row.get("acd_level")))
            missing = _unique([item for row in related_depth for item in _strings(row.get("review_bound_missing_sources", []))])
            operation_sources = _unique([item for row in related_depth for item in _strings(row.get("bound_source_ids", []))])
            base_p1 = _unique([item for row in related_depth for item in _strings(row.get("upstream_p1_trace_ids", []))])
            required_tests = _unique([item for row in related_depth for item in _strings(row.get("required_tests", []))])
        else:
            selected = {
                "business_value_weight": "review-bound",
                "engineering_risk_tier": "review-bound",
                "implementation_complexity": "review-bound",
                "acd_level": "review-bound",
                "required_card_type": "review-bound-card",
                "required_reason": "accepted aggregate/state/non-operation component requires P3 implementation-authority judgment before depth/test selection",
            }
            missing, operation_sources, base_p1, required_tests = [], [], [], []
        semantic = (
            project_component_semantics(component, authority, base_p1)
            if authority_bound
            else {
                "p1_trace_ids": base_p1,
                "operation_contracts": [],
                "aggregate_boundaries": [],
                "non_operation_realizations": [],
                "project_guardrails": [],
                "project_guardrail_p1_trace_ids": [],
                "state_constraints": [],
                "dependency_constraints": [],
                "durable_persistence_decisions": [],
                "architecture_decisions": [],
                "semantic_claim_ceilings": [],
                "semantic_source_ids": [],
            }
        )
        p1_trace_ids = list(semantic["p1_trace_ids"])
        component_sources = _strings(component.get("source_ids", []))
        available = _unique(component_sources + operation_sources + p1_trace_ids + list(semantic["semantic_source_ids"]))
        required_sources = _unique(available + missing)
        projected = str(component.get("authority_projection_status") or "") == "authority-bound"
        status = "sufficient" if not missing and available and p1_trace_ids and (projected or not authority_bound) else "partial" if available else "review-bound"
        result.append(
            {
                "component_id": str(component.get("component_id") or ""),
                "component_type": str(component.get("component_type") or ""),
                "upstream_operation_ids": related_operations,
                "upstream_p1_trace_ids": p1_trace_ids,
                "business_value_weight": str(selected.get("business_value_weight") or "review-bound"),
                "engineering_risk_tier": str(selected.get("engineering_risk_tier") or "review-bound"),
                "implementation_complexity": str(selected.get("implementation_complexity") or "review-bound"),
                "acd_level": str(selected.get("acd_level") or "review-bound"),
                "required_card_type": str(selected.get("required_card_type") or "review-bound-card"),
                "required_reason": str(selected.get("required_reason") or "component obligation derived from P2 depth row"),
                "required_tests": required_tests,
                "required_source_ids": required_sources,
                "available_source_ids": available,
                "missing_source_types": missing,
                "source_sufficiency_status": status,
                "review_bound_missing_sources": missing,
                "semantic_projection_status": "authority-bound" if authority_bound else "not-authority-bound",
                **{key: list(component.get(key, [])) for key in ("aggregate_ids", "aggregate_names", "service_ids", "owner_service_ids", "writer_service_ids", "contract_ids", "topology_groups")},
                **{key: semantic[key] for key in ("operation_contracts", "aggregate_boundaries", "non_operation_realizations", "project_guardrails", "project_guardrail_p1_trace_ids", "state_constraints", "dependency_constraints", "durable_persistence_decisions", "architecture_decisions", "semantic_claim_ceilings")},
            }
        )
    return result


def expected_action_card_projection(
    catalog_component: Mapping[str, Any],
    authority: Mapping[str, Any],
    operation_source_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Recompute the expected authority-bound Action Card denominator."""
    component = project_component_authority(catalog_component, authority)
    base_p1 = _unique(
        [
            str(item).strip()
            for operation_id in _strings(component.get("related_operations", []))
            for item in operation_source_rows.get(operation_id, {}).get("upstream_p1_trace_ids", [])
            if str(item).strip()
        ]
    )
    return {**component, **project_component_semantics(component, authority, base_p1)}


def _value_set(row: Mapping[str, Any], key: str) -> set[str]:
    return set(_strings(row.get(key, [])))


def _row_id_set(row: Mapping[str, Any], key: str, id_key: str) -> set[str]:
    values = row.get(key, [])
    if not isinstance(values, list):
        return set()
    return {
        str(item.get(id_key) or "").strip()
        for item in values
        if isinstance(item, dict) and str(item.get(id_key) or "").strip()
    }


def _rendered_semantic_tokens(obligation: Mapping[str, Any]) -> list[str]:
    tokens = _strings(obligation.get("upstream_p1_trace_ids", []))
    for key in ("contract_ids", "aggregate_ids", "aggregate_names", "service_ids", "owner_service_ids", "writer_service_ids", "topology_groups", "semantic_claim_ceilings"):
        tokens.extend(_strings(obligation.get(key, [])))
    for key, id_key, text_keys in (
        ("non_operation_realizations", "realization_id", ("statement", "claim_ceiling")),
        ("project_guardrails", "realization_id", ("statement", "claim_ceiling")),
        ("state_constraints", "decision_id", ("mutation_guard", "terminal_or_failure_exit", "claim_ceiling")),
        ("dependency_constraints", "dependency_id", ("statement", "claim_ceiling")),
    ):
        for row in obligation.get(key, []):
            if not isinstance(row, dict):
                continue
            tokens.append(str(row.get(id_key) or "").strip())
            tokens.extend(str(row.get(text_key) or "").strip() for text_key in text_keys)
    for row in obligation.get("durable_persistence_decisions", []):
        if not isinstance(row, dict):
            continue
        carrier = row.get("durable_carrier") if isinstance(row.get("durable_carrier"), dict) else {}
        enforcement = carrier.get("enforcement") if isinstance(carrier.get("enforcement"), dict) else {}
        tokens.extend(
            [
                str(row.get("operation_id") or "").strip(),
                str(row.get("persistence_mode") or "").strip(),
                str(row.get("command_kind") or "").strip(),
                str(row.get("idempotency_mode") or "").strip(),
                str(carrier.get("kind") or "").strip(),
                str(carrier.get("carrier_id") or "").strip(),
                str(enforcement.get("mode") or "").strip(),
                str(row.get("writer_service_id") or "").strip(),
                str(row.get("replay_behavior") or "").strip(),
                str(row.get("reason") or "").strip(),
                str(row.get("claim_ceiling") or "").strip(),
            ]
        )
        tokens.extend(_strings(row.get("identity_components", [])))
        tokens.extend(_strings(enforcement.get("fields", [])))
        for binding in carrier.get("field_bindings", []) if isinstance(carrier.get("field_bindings"), list) else []:
            if isinstance(binding, dict):
                tokens.extend(
                    [
                        str(binding.get("identity_component") or "").strip(),
                        str(binding.get("carrier_field") or "").strip(),
                    ]
                )
    for row in obligation.get("architecture_decisions", []):
        if not isinstance(row, dict):
            continue
        tokens.extend(
            [
                str(row.get("decision_id") or "").strip(),
                str(row.get("title") or row.get("statement") or row.get("operation_id") or row.get("aggregate_id") or "accepted decision").strip(),
                str(row.get("claim_ceiling") or "").strip(),
            ]
        )
    return _unique(tokens)


def apply_rendered_action_card_convergence(
    report: Mapping[str, Any],
    *,
    component_obligations: Mapping[str, Mapping[str, Any]],
    rendered_cards: Mapping[str, str],
) -> dict[str, Any]:
    """Verify that accepted obligation semantics are visible in rendered cards."""
    conflicts = [dict(row) for row in report.get("conflicts", []) if isinstance(row, dict)]
    rendered_conflicts: list[dict[str, str]] = []
    for component_id, obligation in component_obligations.items():
        if str(obligation.get("semantic_projection_status") or "") != "authority-bound":
            continue
        text = rendered_cards.get(component_id, "")
        missing = [token for token in _rendered_semantic_tokens(obligation) if token not in text]
        if missing:
            rendered_conflicts.append({"code": "action_card_rendered_semantic_content_missing", "component_id": component_id, "detail": ", ".join(missing)})
        if "review-bound gaps: none" in text:
            rendered_conflicts.append({"code": "action_card_rendered_false_review_bound_none", "component_id": component_id, "detail": "source sufficiency was rendered as semantic completeness"})
        if not _strings(obligation.get("upstream_operation_ids", [])) and "none; non-operation component" not in text:
            rendered_conflicts.append({"code": "action_card_rendered_non_operation_mislabeled", "component_id": component_id, "detail": "non-operation component lacks explicit no-public-operation wording"})
    conflicts.extend(rendered_conflicts)
    result = dict(report)
    result.update({
        "status": "pass" if not conflicts else "blocked",
        "passed": not conflicts,
        "conflict_count": len(conflicts),
        "rendered_conflict_count": len(rendered_conflicts),
        "conflicts": conflicts,
    })
    return result


def validate_s1b_action_card_admission(
    *,
    report: Mapping[str, Any],
    convergence: Mapping[str, Any],
    component_obligations: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate the persisted S1B result before P3 implementation authority."""
    embedded = report.get("semantic_convergence") if isinstance(report.get("semantic_convergence"), dict) else {}
    errors: list[str] = []
    if report.get("quality_gate") != "pass":
        errors.append("action_card_quality_gate_not_pass")
    if convergence.get("passed") is not True or str(convergence.get("status") or "") != "pass":
        errors.append("action_card_semantic_convergence_not_pass")
    if int(convergence.get("conflict_count", 0) or 0) != 0:
        errors.append("action_card_semantic_conflicts_present")
    if embedded != convergence:
        errors.append("action_card_report_convergence_mismatch")
    expected_count = len(component_obligations)
    if int(report.get("action_card_count", 0) or 0) != expected_count:
        errors.append("action_card_count_mismatch")
    readiness = report.get("readiness_summary") if isinstance(report.get("readiness_summary"), dict) else {}
    readiness_rows = [row for row in readiness.get("components", []) if isinstance(row, dict)]
    readiness_by_component = {
        str(row.get("component_id") or "").strip(): dict(row)
        for row in readiness_rows
        if str(row.get("component_id") or "").strip()
    }
    if set(readiness_by_component) != set(component_obligations):
        errors.append("action_card_readiness_denominator_mismatch")
    return {
        "passed": not errors,
        "errors": errors,
        "action_card_count": expected_count,
        "direct_ready_count": int(readiness.get("direct_implementation_ready_count", 0) or 0),
        "review_bound_count": int(readiness.get("review_bound_count", 0) or 0),
        "split_required_count": int(readiness.get("split_required_parent_count", 0) or 0),
        "readiness_by_component": readiness_by_component,
    }


def bind_s2_slices_to_action_cards(
    *,
    required_slices: list[dict[str, Any]],
    component_catalog: Mapping[str, Mapping[str, Any]],
    component_obligations: Mapping[str, Mapping[str, Any]],
    action_card_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind exact-realization slices to S1B-verified Action Card semantics."""
    readiness_rows = (
        action_card_report.get("readiness_summary", {}).get("components", [])
        if isinstance(action_card_report.get("readiness_summary"), dict)
        else []
    )
    readiness_by_component = {
        str(row.get("component_id") or "").strip(): dict(row)
        for row in readiness_rows
        if isinstance(row, dict) and str(row.get("component_id") or "").strip()
    }
    enriched: list[dict[str, Any]] = []
    covered_components: set[str] = set()
    slices_without_cards: list[str] = []
    for raw_slice in required_slices:
        row = dict(raw_slice)
        operation_id = str(row.get("operation_id") or "").strip()
        realization_id = str(row.get("non_operation_realization_id") or "").strip()
        direct_matched: list[tuple[str, Mapping[str, Any]]] = []
        context_matched: list[tuple[str, Mapping[str, Any]]] = []
        for component_id, obligation in component_obligations.items():
            operation_match = bool(operation_id and operation_id in _strings(obligation.get("upstream_operation_ids", [])))
            direct_realization_match = bool(realization_id) and any(
                isinstance(item, dict) and str(item.get("realization_id") or "").strip() == realization_id
                for item in obligation.get("non_operation_realizations", [])
            )
            context_realization_match = bool(realization_id) and any(
                isinstance(item, dict) and str(item.get("realization_id") or "").strip() == realization_id
                for item in obligation.get("project_guardrails", [])
            )
            if operation_match or direct_realization_match:
                direct_matched.append((component_id, obligation))
            elif context_realization_match:
                context_matched.append((component_id, obligation))
        if not direct_matched and not context_matched:
            slices_without_cards.append(str(row.get("slice_id") or ""))
        component_ids = [component_id for component_id, _ in direct_matched]
        context_action_card_refs = [component_id for component_id, _ in context_matched]
        covered_components.update(component_ids)
        component_bindings = []
        for component_id, obligation in direct_matched:
            catalog = component_catalog.get(component_id, {})
            component_bindings.append(
                {
                    "component_id": component_id,
                    "action_card_ref": component_id,
                    "component_type": str(obligation.get("component_type") or catalog.get("component_type") or ""),
                    "target_path_hint": str(catalog.get("target_path_hint") or ""),
                    "readiness": str(readiness_by_component.get(component_id, {}).get("readiness") or "review-bound"),
                    "aggregate_ids": _strings(obligation.get("aggregate_ids", [])),
                    "service_ids": _strings(obligation.get("service_ids", [])),
                    "owner_service_ids": _strings(obligation.get("owner_service_ids", [])),
                    "writer_service_ids": _strings(obligation.get("writer_service_ids", [])),
                    "topology_groups": _strings(obligation.get("topology_groups", [])),
                }
            )
        semantic_rows = [obligation for _, obligation in direct_matched]
        durable_persistence_decisions = _unique_structured_rows(
            [
                dict(item)
                for obligation in semantic_rows
                for item in obligation.get("durable_persistence_decisions", [])
                if operation_id
                and isinstance(item, dict)
                and str(item.get("operation_id") or "").strip() == operation_id
            ]
        )
        if semantic_rows:
            constraint_ids = _unique(
                [
                    str(item.get(id_key) or "").strip()
                    for obligation in semantic_rows
                    for key, id_key in (
                        ("non_operation_realizations", "realization_id"),
                        ("project_guardrails", "realization_id"),
                        ("state_constraints", "decision_id"),
                        ("dependency_constraints", "dependency_id"),
                        ("architecture_decisions", "decision_id"),
                    )
                    for item in obligation.get(key, [])
                    if isinstance(item, dict) and str(item.get(id_key) or "").strip()
                ]
            )
            claim_ceilings = _unique([item for obligation in semantic_rows for item in _strings(obligation.get("semantic_claim_ceilings", []))])
        else:
            constraint_ids = [realization_id] if realization_id else []
            claim_ceilings = _unique(
                [
                    str(item.get("claim_ceiling") or "").strip()
                    for _, obligation in context_matched
                    for item in obligation.get("project_guardrails", [])
                    if isinstance(item, dict) and str(item.get("realization_id") or "").strip() == realization_id
                ]
            )
        row.update(
            {
                "component_ids": component_ids,
                "action_card_refs": _unique(component_ids + context_action_card_refs),
                "context_action_card_refs": context_action_card_refs,
                "component_bindings": component_bindings,
                "accepted_aggregate_ids": _unique([item for obligation in semantic_rows for item in _strings(obligation.get("aggregate_ids", []))]),
                "accepted_service_ids": _unique([item for obligation in semantic_rows for item in _strings(obligation.get("service_ids", []))]),
                "accepted_owner_service_ids": _unique([item for obligation in semantic_rows for item in _strings(obligation.get("owner_service_ids", []))]),
                "accepted_writer_service_ids": _unique([item for obligation in semantic_rows for item in _strings(obligation.get("writer_service_ids", []))]),
                "accepted_topology_groups": _unique([item for obligation in semantic_rows for item in _strings(obligation.get("topology_groups", []))]),
                "durable_persistence_decisions": durable_persistence_decisions,
                "required_constraint_ids": constraint_ids,
                "semantic_claim_ceilings": claim_ceilings,
            }
        )
        enriched.append(row)
    all_components = set(component_obligations)
    uncovered = sorted(all_components - covered_components)
    return {
        "required_slices": enriched,
        "coverage": {
            "action_card_component_count": len(all_components),
            "covered_component_count": len(covered_components),
            "uncovered_component_ids": uncovered,
            "slice_without_action_card_ids": sorted(item for item in slices_without_cards if item),
            "status": "complete" if not uncovered and not slices_without_cards else "blocked",
        },
    }


def build_s1b_action_card_content_manifest(
    *,
    card_paths: list[Path],
    admission: Mapping[str, Any],
    convergence: Mapping[str, Any],
) -> dict[str, Any]:
    readiness = admission.get("readiness_by_component") if isinstance(admission.get("readiness_by_component"), dict) else {}
    cards = []
    for path in card_paths:
        component_id = path.stem.removesuffix("-action-card").upper()
        # Canonical component IDs use upper-case P2-CMP-NNN; derive without trusting report paths as identity.
        component_id = component_id.replace("P2-CMP-", "P2-CMP-")
        cards.append(
            {
                "component_id": component_id,
                "name": path.name,
                "sha256": "sha256:" + sha256(path.read_bytes()).hexdigest(),
                "readiness": str(readiness.get(component_id, {}).get("readiness") or "review-bound"),
            }
        )
    cards.sort(key=lambda row: row["component_id"])
    body = {
        "schema_version": "wff.p3-s1b-action-card-content-manifest.v1",
        "action_card_count": len(cards),
        "direct_ready_count": int(admission.get("direct_ready_count", 0) or 0),
        "review_bound_count": int(admission.get("review_bound_count", 0) or 0),
        "split_required_count": int(admission.get("split_required_count", 0) or 0),
        "semantic_convergence_digest": "sha256:" + sha256(
            json.dumps(convergence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "cards": cards,
        "claim_ceiling": "S1B Action Card content/readiness identity only; no implementation authority.",
    }
    return {**body, "content_digest": "sha256:" + sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()}


def load_s2_action_card_binding(
    *,
    action_card_root: Path,
    required_slices: list[dict[str, Any]],
    component_catalog_rows: list[dict[str, Any]],
    component_obligation_rows: list[dict[str, Any]],
    operation_source_rows: Mapping[str, Mapping[str, Any]],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Load and bind the exact persisted S1B artifacts required by S2."""
    root = action_card_root.resolve()
    report_path = root / "action-card-report.json"
    convergence_path = root / ".phase3-review" / "action-card-semantic-convergence.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        convergence = json.loads(convergence_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("P3 S2 requires persisted S1B Action Card report/convergence") from exc
    if not isinstance(report, dict) or not isinstance(convergence, dict):
        raise ValueError("P3 S1B Action Card evidence must be JSON objects")
    catalog = {
        str(row.get("component_id") or "").strip(): dict(row)
        for row in component_catalog_rows
        if isinstance(row, dict) and str(row.get("component_id") or "").strip()
    }
    obligations = {
        str(row.get("component_id") or "").strip(): dict(row)
        for row in component_obligation_rows
        if isinstance(row, dict) and str(row.get("component_id") or "").strip()
    }
    admission = validate_s1b_action_card_admission(
        report=report,
        convergence=convergence,
        component_obligations=obligations,
    )
    if not admission["passed"]:
        raise ValueError("P3 S1B Action Card admission failed: " + ", ".join(admission["errors"]))
    binding = bind_s2_slices_to_action_cards(
        required_slices=required_slices,
        component_catalog=catalog,
        component_obligations=obligations,
        action_card_report=report,
    )
    if binding["coverage"]["status"] != "complete":
        raise ValueError("P3 S2 Action Card slice coverage is incomplete")
    card_paths: list[Path] = []
    for raw in report.get("cards", []):
        path = Path(str(raw)).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("P3 S1B Action Card path escapes the S2 evidence root") from exc
        if not path.is_file() or path.is_symlink():
            raise ValueError("P3 S1B Action Card artifact is missing or unsafe")
        card_paths.append(path)
    if len(card_paths) != admission["action_card_count"]:
        raise ValueError("P3 S1B Action Card artifact count does not match the admitted denominator")
    fresh = build_action_card_semantic_convergence(
        component_catalog=catalog,
        component_obligations=obligations,
        operation_source_rows=operation_source_rows,
        authority=authority,
    )
    fresh = apply_rendered_action_card_convergence(
        fresh,
        component_obligations=obligations,
        rendered_cards={
            component_id: (root / "action-cards" / f"{component_id.lower()}-action-card.md").read_text(encoding="utf-8")
            for component_id in obligations
        },
    )
    if fresh != convergence:
        raise ValueError("P3 S2 recomputed S1B convergence does not match the persisted admitted result")
    return {
        "report_path": report_path,
        "convergence_path": convergence_path,
        "card_paths": card_paths,
        "card_content_manifest": build_s1b_action_card_content_manifest(
            card_paths=card_paths,
            admission=admission,
            convergence=convergence,
        ),
        "admission": admission,
        "required_slices": binding["required_slices"],
        "component_coverage": binding["coverage"],
    }


def build_s2_decision_template_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Copy immutable S1B context into one review-bound S2 decision row."""
    return {
        "slice_id": row.get("slice_id"),
        "commitment_id": row.get("commitment_id"),
        "contract_id": row.get("contract_id", ""),
        "operation_id": row.get("operation_id", ""),
        "non_operation_realization_id": row.get("non_operation_realization_id", ""),
        **{key: list(row.get(key, [])) for key in (
            "component_ids", "action_card_refs", "context_action_card_refs", "accepted_aggregate_ids", "accepted_service_ids",
            "accepted_owner_service_ids", "accepted_writer_service_ids", "accepted_topology_groups",
            "required_constraint_ids",
        )},
        "durable_persistence_decisions": _unique_structured_rows(row.get("durable_persistence_decisions", [])),
        "authority_delta_refs": [],
        "disposition": "review-bound",
        "semantic_owner": "",
        "aggregate": "",
        "domain_invariants": [],
        "state_mutation": "",
        "authorization": "",
        "failure_behavior": "",
        "persistence_effects": "",
        "integration_behavior": "",
        "irreversible_migration": False,
        "migration_plan": "",
        "rollback_plan": "",
        "migration_test_targets": [],
        "implementation_targets": [],
        "test_targets": [],
        "runtime_evidence_intents": [],
        "preserved_constraint_ids": [],
        "reason": "",
        "owner": "P3 host Agent",
        "minimum_rerun": "P3",
        "claim_ceiling": "",
    }


def s2_decision_binding_errors(
    row: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    implemented: bool,
) -> list[str]:
    errors: list[str] = []
    for field in (
        "component_ids", "action_card_refs", "context_action_card_refs", "accepted_aggregate_ids", "accepted_service_ids",
        "accepted_owner_service_ids", "accepted_writer_service_ids", "accepted_topology_groups",
        "required_constraint_ids",
    ):
        if _strings(row.get(field)) != _strings(expected.get(field)):
            errors.append(f"changes S1B-bound {field}")
    if not _structured_rows_equal(
        row.get("durable_persistence_decisions", []),
        expected.get("durable_persistence_decisions", []),
    ):
        errors.append("changes S1B-bound durable_persistence_decisions")
    if not implemented:
        return errors
    if set(_strings(row.get("preserved_constraint_ids"))) != set(_strings(expected.get("required_constraint_ids"))):
        errors.append("does not preserve the S1B constraint denominator")
    accepted_services = _strings(expected.get("accepted_service_ids"))
    accepted_aggregates = _strings(expected.get("accepted_aggregate_ids"))
    chosen_owner = str(row.get("semantic_owner") or "").strip()
    chosen_aggregate = str(row.get("aggregate") or "").strip()
    if (not accepted_services and chosen_owner) or (accepted_services and chosen_owner and chosen_owner not in accepted_services) or (len(accepted_services) == 1 and chosen_owner != accepted_services[0]):
        errors.append("changes accepted semantic owner")
    if (not accepted_aggregates and chosen_aggregate) or (accepted_aggregates and chosen_aggregate and chosen_aggregate not in accepted_aggregates) or (len(accepted_aggregates) == 1 and chosen_aggregate != accepted_aggregates[0]):
        errors.append("changes accepted aggregate")
    return errors


def build_s2_authority_extensions(
    *,
    implementation_rows: list[dict[str, Any]],
    decision_id: str,
    decision_digest: str,
) -> dict[str, Any]:
    """Build additive non-operation/slice/component authority projections from accepted S2 rows."""
    slice_decisions: dict[str, dict[str, Any]] = {}
    non_operation_decisions: dict[str, dict[str, Any]] = {}
    component_plan: dict[str, dict[str, Any]] = {}
    for row in implementation_rows:
        if str(row.get("disposition") or "") != "implement":
            continue
        slice_id = str(row.get("slice_id") or "").strip()
        projection = {
            "slice_id": slice_id,
            "operation_id": str(row.get("operation_id") or ""),
            "contract_id": str(row.get("contract_id") or ""),
            "non_operation_realization_id": str(row.get("non_operation_realization_id") or ""),
            "component_ids": _strings(row.get("component_ids", [])),
            "action_card_refs": _strings(row.get("action_card_refs", [])),
            "context_action_card_refs": _strings(row.get("context_action_card_refs", [])),
            "semantic_owner": str(row.get("semantic_owner") or ""),
            "aggregate": str(row.get("aggregate") or ""),
            "domain_invariants": _strings(row.get("domain_invariants", [])),
            "state_mutation": str(row.get("state_mutation") or ""),
            "authorization": str(row.get("authorization") or ""),
            "failure_behavior": str(row.get("failure_behavior") or ""),
            "persistence_effects": str(row.get("persistence_effects") or ""),
            "integration_behavior": str(row.get("integration_behavior") or ""),
            "implementation_targets": _strings(row.get("implementation_targets", [])),
            "test_targets": _strings(row.get("test_targets", [])),
            "runtime_evidence_intents": _strings(row.get("runtime_evidence_intents", [])),
            "preserved_constraint_ids": _strings(row.get("preserved_constraint_ids", [])),
            "durable_persistence_decisions": _unique_structured_rows(row.get("durable_persistence_decisions", [])),
            "authority_delta_refs": _strings(row.get("authority_delta_refs")),
            "implementation_decision_id": decision_id,
            "implementation_decision_digest": decision_digest,
            "claim_ceiling": str(row.get("claim_ceiling") or ""),
        }
        slice_decisions[slice_id] = projection
        realization_id = projection["non_operation_realization_id"]
        if realization_id:
            non_operation_decisions[realization_id] = projection
        for component_id in projection["component_ids"]:
            item = component_plan.setdefault(
                component_id,
                {
                    "component_id": component_id,
                    "slice_ids": [],
                    "operation_ids": [],
                    "non_operation_realization_ids": [],
                    "implementation_targets": [],
                    "test_targets": [],
                    "constraint_ids": [],
                    "implementation_decision_id": decision_id,
                    "implementation_decision_digest": decision_digest,
                },
            )
            item["slice_ids"] = _unique(item["slice_ids"] + [slice_id])
            item["operation_ids"] = _unique(item["operation_ids"] + ([projection["operation_id"]] if projection["operation_id"] else []))
            item["non_operation_realization_ids"] = _unique(item["non_operation_realization_ids"] + ([realization_id] if realization_id else []))
            item["implementation_targets"] = _unique(item["implementation_targets"] + projection["implementation_targets"])
            item["test_targets"] = _unique(item["test_targets"] + projection["test_targets"])
            item["constraint_ids"] = _unique(item["constraint_ids"] + projection["preserved_constraint_ids"])
    return {
        "slice_decisions": slice_decisions,
        "non_operation_decisions": non_operation_decisions,
        "component_realization_plan": component_plan,
    }


def action_card_report_allows_implementation(report: Mapping[str, Any]) -> bool:
    semantic = report.get("semantic_convergence") if isinstance(report.get("semantic_convergence"), dict) else {}
    return bool(
        report.get("quality_gate") == "pass"
        and semantic.get("passed") is True
        and int(semantic.get("conflict_count", 0) or 0) == 0
    )


def build_action_card_semantic_convergence(
    *,
    component_catalog: Mapping[str, Mapping[str, Any]],
    component_obligations: Mapping[str, Mapping[str, Any]],
    operation_source_rows: Mapping[str, Mapping[str, Any]],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare actual Action Card obligations with a fresh authority projection."""
    conflicts: list[dict[str, str]] = []
    defined_ids = {
        component_id
        for component_id, row in component_catalog.items()
        if str(row.get("catalog_status") or "defined") == "defined"
    }
    for component_id in sorted(defined_ids - set(component_obligations)):
        conflicts.append({"code": "action_card_component_omitted", "component_id": component_id, "detail": "defined P2 implementation component has no Action Card obligation"})
    value_checks = (
        ("contract_ids", "contract_ids", "action_card_contract_denominator_shrunk"),
        ("aggregate_ids", "aggregate_ids", "action_card_aggregate_authority_missing"),
        ("service_ids", "service_ids", "action_card_service_authority_missing"),
        ("owner_service_ids", "owner_service_ids", "action_card_owner_authority_missing"),
        ("writer_service_ids", "writer_service_ids", "action_card_writer_authority_missing"),
        ("topology_groups", "topology_groups", "action_card_topology_missing"),
        ("p1_trace_ids", "upstream_p1_trace_ids", "action_card_p1_trace_denominator_shrunk"),
        ("project_guardrail_p1_trace_ids", "project_guardrail_p1_trace_ids", "action_card_project_guardrail_p1_trace_missing"),
        ("semantic_claim_ceilings", "semantic_claim_ceilings", "action_card_claim_ceiling_missing"),
        ("semantic_source_ids", "required_source_ids", "action_card_semantic_source_missing"),
    )
    row_checks = (
        ("non_operation_realizations", "realization_id", "action_card_non_operation_truth_missing"),
        ("project_guardrails", "realization_id", "action_card_project_guardrail_missing"),
        ("state_constraints", "decision_id", "action_card_state_failure_truth_missing"),
        ("dependency_constraints", "dependency_id", "action_card_dependency_truth_missing"),
        ("architecture_decisions", "decision_id", "action_card_architecture_decision_missing"),
    )
    for component_id, row in sorted(component_obligations.items()):
        expected = expected_action_card_projection(component_catalog.get(component_id, {}), authority, operation_source_rows)
        for expected_key, actual_key, code in value_checks:
            missing = sorted(_value_set(expected, expected_key) - _value_set(row, actual_key))
            if missing:
                conflicts.append({"code": code, "component_id": component_id, "detail": ", ".join(missing)})
        for key, id_key, code in row_checks:
            missing = sorted(_row_id_set(expected, key, id_key) - _row_id_set(row, key, id_key))
            if missing:
                conflicts.append({"code": code, "component_id": component_id, "detail": ", ".join(missing)})
        expected_durable = {
            str(item.get("operation_id") or "").strip(): item
            for item in expected.get("durable_persistence_decisions", [])
            if isinstance(item, dict) and str(item.get("operation_id") or "").strip()
        }
        actual_durable = {
            str(item.get("operation_id") or "").strip(): item
            for item in row.get("durable_persistence_decisions", [])
            if isinstance(item, dict) and str(item.get("operation_id") or "").strip()
        }
        for operation_id, expected_row in expected_durable.items():
            actual_row = actual_durable.get(operation_id)
            if actual_row is None:
                conflicts.append({"code": "action_card_durable_persistence_truth_missing", "component_id": component_id, "detail": operation_id})
                continue
            if json.dumps(expected_row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) != json.dumps(actual_row, ensure_ascii=False, sort_keys=True, separators=(",", ":")):
                conflicts.append({"code": "action_card_durable_persistence_truth_changed", "component_id": component_id, "detail": operation_id})
    return {
        "artifact_kind": "phase3-action-card-semantic-convergence.v1",
        "status": "pass" if not conflicts else "blocked",
        "passed": not conflicts,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "component_count": len(component_obligations),
        "defined_component_count": len(defined_ids),
        "claim_ceiling": "This report verifies P1/P2 semantic preservation into Action Card obligations. It does not authorize implementation or prove generated code.",
    }
