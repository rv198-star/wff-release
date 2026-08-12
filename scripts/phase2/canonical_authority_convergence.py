"""P2 accepted-authority generation model for existing Stage/ESP renderers.

This module does not author a second ESP. It binds the existing Phase-2
renderers to the accepted P2 architecture authority so generic generation
helpers cannot create parallel service/operation/aggregate truth.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from common.agentic_decision_authority import write_json_atomic


P2_CANONICAL_CONVERGENCE_SCHEMA = "wff.p2-canonical-authority-convergence.v1"
P2_CANONICAL_WRITER_ID = "phase2-existing-renderer-authority-bound.v1"


class P2CanonicalAuthorityConvergenceError(ValueError):
    """Raised when accepted P2 authority cannot safely drive canonical generation."""


def _text(value: object) -> str:
    return str(value or "").strip()


def _rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _canonical_digest(value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + sha256(body).hexdigest()


def _projection_pascal(raw: str, *, fallback: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", raw)
    value = "".join(part[:1].upper() + part[1:] for part in parts)
    return value or fallback


def _projection_slug(raw: str, *, fallback: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", raw.casefold())
    return "-".join(parts) or fallback


def build_p2_authority_generation_model(authority: Mapping[str, Any]) -> dict[str, Any]:
    if authority.get("schema_version") != "wff.p2-agentic-architecture-authority.v1":
        raise P2CanonicalAuthorityConvergenceError("P2 authority schema is invalid")
    if authority.get("status") != "accepted-p2-agentic-architecture-authority":
        raise P2CanonicalAuthorityConvergenceError("P2 authority is not accepted")

    services = _rows(authority.get("service_portfolio"))
    operations = _rows(authority.get("operation_portfolio"))
    if not services:
        raise P2CanonicalAuthorityConvergenceError("accepted P2 authority has no service portfolio")
    if not operations:
        raise P2CanonicalAuthorityConvergenceError("accepted P2 authority has no operation portfolio")

    service_by_id = {
        _text(row.get("service_id")): row
        for row in services
        if _text(row.get("service_id"))
    }
    if len(service_by_id) != len(services):
        raise P2CanonicalAuthorityConvergenceError("P2 service identity is missing or duplicated")

    operation_rows: list[dict[str, Any]] = []
    seen_operation_ids: set[str] = set()
    for row in operations:
        operation_id = _text(row.get("operation_id"))
        contract_id = _text(row.get("contract_id"))
        service_id = _text(row.get("service_id"))
        if not operation_id or operation_id in seen_operation_ids or not contract_id or service_id not in service_by_id:
            raise P2CanonicalAuthorityConvergenceError(
                f"P2 operation identity/service/contract binding is invalid: {operation_id or 'missing-operation'}"
            )
        seen_operation_ids.add(operation_id)
        technical_name = _text(row.get("technical_name")) or _projection_pascal(operation_id, fallback="Operation")
        technical_slug = _text(row.get("technical_slug")) or _projection_slug(operation_id, fallback="operation")
        explicit_event_id = _text(row.get("event_id"))
        operation_rows.append(
            {
                **row,
                "operation_id": operation_id,
                "contract_id": contract_id,
                "service_id": service_id,
                "aggregate_id": _text(row.get("aggregate_id")),
                "technical_name": technical_name,
                "technical_slug": technical_slug,
                # HTTP method/path are renderer projections when the accepted authority
                # does not specify them. They must not create a new operation identity.
                "method": _text(row.get("method")) or "POST",
                "path": _text(row.get("path")) or f"/api/v1/{technical_slug}",
                "event_id": explicit_event_id,
                "event_id_explicit": bool(explicit_event_id),
                "service_statement": _text(service_by_id[service_id].get("statement")),
                "service_boundary": _text(service_by_id[service_id].get("boundary")),
            }
        )

    raw_aggregates = _rows(authority.get("aggregate_and_writer_decisions"))
    raw_state_policy = _rows(authority.get("state_invariant_policy_failure_decisions"))
    raw_data_decisions = _rows(authority.get("data_and_interaction_decisions"))
    raw_durable_persistence = _rows(authority.get("durable_persistence_identity_decisions"))
    aggregate_rows: list[dict[str, Any]] = []
    aggregate_ids: set[str] = set()
    for row in raw_aggregates:
        aggregate_id = _text(row.get("aggregate_id"))
        if not aggregate_id or aggregate_id in aggregate_ids:
            raise P2CanonicalAuthorityConvergenceError(
                f"P2 aggregate identity is missing or duplicated: {aggregate_id or 'missing-aggregate'}"
            )
        aggregate_ids.add(aggregate_id)
        owner_service_id = _text(row.get("owner_service_id") or row.get("owner"))
        writer_service_id = _text(row.get("writer_service_id") or row.get("writer"))
        if owner_service_id and owner_service_id not in service_by_id:
            raise P2CanonicalAuthorityConvergenceError(f"P2 aggregate owner is unknown: {aggregate_id}")
        if writer_service_id and writer_service_id not in service_by_id:
            raise P2CanonicalAuthorityConvergenceError(f"P2 aggregate writer is unknown: {aggregate_id}")
        technical_name = _text(row.get("technical_name")) or _projection_pascal(aggregate_id, fallback="Aggregate")
        technical_slug = _text(row.get("technical_slug")) or _projection_slug(aggregate_id, fallback="aggregate")
        matching_state = [
            dict(item)
            for item in raw_state_policy
            if _text(item.get("aggregate_id")) == aggregate_id
        ]
        matching_data = [
            dict(item)
            for item in raw_data_decisions
            if _text(item.get("aggregate_id")) == aggregate_id
        ]
        aggregate_rows.append(
            {
                **row,
                "aggregate_id": aggregate_id,
                "aggregate_name": _text(row.get("aggregate_name")) or aggregate_id,
                "owner_service_id": owner_service_id,
                "writer_service_id": writer_service_id,
                "technical_name": technical_name,
                "technical_slug": technical_slug,
                "table_name": _text(row.get("table_name")) or technical_slug.replace("-", "_"),
                "state_decisions": matching_state,
                "data_decisions": matching_data,
            }
        )

    operation_aggregate_ids = {
        _text(row.get("aggregate_id"))
        for row in operation_rows
        if _text(row.get("aggregate_id"))
    }
    if aggregate_rows and not operation_aggregate_ids.issubset(aggregate_ids):
        missing_aggregates = sorted(operation_aggregate_ids - aggregate_ids)
        raise P2CanonicalAuthorityConvergenceError(
            "P2 operations reference aggregates without accepted aggregate/writer decisions: "
            + ", ".join(missing_aggregates)
        )

    model = {
        "authority_digest": _text(authority.get("content_digest")),
        "decision_id": _text(authority.get("decision_id")),
        "decision_digest": _text(authority.get("decision_digest")),
        "p1_authority": dict(authority.get("p1_authority") or {}),
        "services": services,
        "operations": operation_rows,
        "non_operations": _rows(authority.get("non_operation_realizations")),
        "aggregates": aggregate_rows,
        "state_policy_failure": raw_state_policy,
        "data_decisions": raw_data_decisions,
        "durable_persistence_identity": raw_durable_persistence,
        "commitment_dispositions": _rows(authority.get("commitment_dispositions")),
        "dependency_dispositions": _rows(authority.get("dependency_dispositions")),
        "stage_02_5_route": dict(authority.get("stage_02_5_route") or {}),
        "handoff": dict(authority.get("handoff") or {}),
        "claim_ceiling": _text(authority.get("claim_ceiling")),
    }
    model["projection_digest"] = _canonical_digest(model)
    return model


def apply_p2_authority_to_parsed_context(
    context: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    model = build_p2_authority_generation_model(authority)
    result = dict(context)
    result["agentic_architecture_model"] = model
    result["agentic_architecture_authority"] = dict(authority)
    result["architecture_authority_mode"] = "accepted-snapshot-bound-agentic-architecture-authority"

    service_operation_aggregates: dict[str, list[str]] = {}
    for row in model["operations"]:
        aggregate_id = _text(row.get("aggregate_id"))
        if aggregate_id:
            service_operation_aggregates.setdefault(_text(row.get("service_id")), []).append(aggregate_id)
    for row in model["aggregates"]:
        aggregate_id = _text(row.get("aggregate_id"))
        for service_id in {
            _text(row.get("owner_service_id")),
            _text(row.get("writer_service_id")),
        }:
            if aggregate_id and service_id:
                service_operation_aggregates.setdefault(service_id, []).append(aggregate_id)

    modules: list[dict[str, Any]] = []
    for service in model["services"]:
        service_id = _text(service.get("service_id"))
        aggregates = list(dict.fromkeys(service_operation_aggregates.get(service_id, [])))
        primary = aggregates[0] if aggregates else service_id
        modules.append(
            {
                "module_name": service_id,
                "core_objects": aggregates or [service_id],
                "primary_object": primary,
                "technical_module_name": _projection_pascal(service_id, fallback="Service"),
                "technical_module_slug": _projection_slug(service_id, fallback="service"),
                "technical_primary_object": _projection_pascal(primary, fallback="Aggregate"),
                "technical_primary_slug": _projection_slug(primary, fallback="aggregate"),
                "service_type": "authority-bound",
                "home_namespace": service_id,
            }
        )
    result["modules"] = modules
    result["module_matrix_names"] = [_text(row.get("service_id")) for row in model["services"]]

    aggregate_ids = [
        _text(row.get("aggregate_id"))
        for row in model["aggregates"]
        if _text(row.get("aggregate_id"))
    ] or list(
        dict.fromkeys(
            [_text(row.get("aggregate_id")) for row in model["operations"] if _text(row.get("aggregate_id"))]
        )
    )
    if aggregate_ids:
        result["objects"] = aggregate_ids
        result["core_objects"] = aggregate_ids
    result["architecture_operations"] = model["operations"]
    result["architecture_aggregates"] = model["aggregates"]
    result["architecture_non_operations"] = model["non_operations"]
    result["architecture_state_policy_failure"] = model["state_policy_failure"]
    result["architecture_data_decisions"] = model["data_decisions"]
    result["architecture_durable_persistence_identity"] = model["durable_persistence_identity"]
    result["architecture_commitment_dispositions"] = model["commitment_dispositions"]
    return result


def _markdown_table_rows_after_marker(text: str, marker: str) -> list[list[str]]:
    lines = text.splitlines()
    start = next((idx for idx, line in enumerate(lines) if line.strip() == marker), None)
    if start is None:
        return []
    table_lines: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            if table_lines:
                break
            continue
        if stripped.startswith("|"):
            table_lines.append(stripped)
            continue
        if table_lines:
            break
    if len(table_lines) < 2:
        return []
    rows: list[list[str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if cells:
            rows.append(cells)
    return rows


def validate_p2_canonical_authority_application(
    *,
    authority: Mapping[str, Any],
    artifact_texts: Mapping[str, str],
) -> dict[str, Any]:
    model = build_p2_authority_generation_model(authority)
    combined = "\n\n".join(artifact_texts.values())
    conflicts: list[dict[str, str]] = []

    def require_identity(kind: str, identity: str) -> None:
        if identity and identity not in combined:
            conflicts.append({"kind": f"missing-{kind}-identity", "item": identity})

    for row in model["services"]:
        require_identity("service", _text(row.get("service_id")))
    for row in model["operations"]:
        require_identity("operation", _text(row.get("operation_id")))
        require_identity("contract", _text(row.get("contract_id")))
    for row in model["aggregates"]:
        aggregate_id = _text(row.get("aggregate_id"))
        aggregate_name = _text(row.get("aggregate_name")) or aggregate_id
        writer_id = _text(row.get("writer_service_id"))
        require_identity("aggregate", aggregate_id)
        if writer_id:
            writer_projection = any(
                writer_id in line and (aggregate_id in line or aggregate_name in line)
                for line in combined.splitlines()
            )
            if not writer_projection:
                conflicts.append({"kind": "aggregate-writer-not-applied", "item": aggregate_id})
    for row in model["non_operations"]:
        require_identity("non-operation", _text(row.get("realization_id")))
    for row in model["commitment_dispositions"]:
        require_identity("commitment-disposition", _text(row.get("commitment_id")))

    stage_03 = artifact_texts.get("stage-03-data-storage-and-interface-design.md", "")
    endpoint_rows = _markdown_table_rows_after_marker(stage_03, "- api_endpoint_draft:")
    rendered_endpoint_ids = [row[0] for row in endpoint_rows if row]
    accepted_operation_ids = [_text(row.get("operation_id")) for row in model["operations"]]
    if rendered_endpoint_ids:
        extras = sorted(set(rendered_endpoint_ids) - set(accepted_operation_ids))
        missing = sorted(set(accepted_operation_ids) - set(rendered_endpoint_ids))
        for item in extras:
            conflicts.append({"kind": "unaccepted-operation-rendered", "item": item})
        for item in missing:
            conflicts.append({"kind": "accepted-operation-not-rendered", "item": item})
    elif accepted_operation_ids:
        conflicts.append({"kind": "api-endpoint-denominator-not-reviewable", "item": "stage-03 api_endpoint_draft"})

    durable_rows = _markdown_table_rows_after_marker(stage_03, "- durable_persistence_identity:")
    rendered_durable_ids = [row[0] for row in durable_rows if row]
    accepted_durable = [row for row in model["durable_persistence_identity"] if isinstance(row, Mapping)]
    accepted_durable_ids = [_text(row.get("operation_id")) for row in accepted_durable]
    if rendered_durable_ids:
        extras = sorted(set(rendered_durable_ids) - set(accepted_durable_ids))
        missing = sorted(set(accepted_durable_ids) - set(rendered_durable_ids))
        for item in extras:
            conflicts.append({"kind": "unaccepted-durable-persistence-rendered", "item": item})
        for item in missing:
            conflicts.append({"kind": "accepted-durable-persistence-not-rendered", "item": item})
    elif accepted_durable_ids:
        conflicts.append({"kind": "durable-persistence-denominator-not-reviewable", "item": "stage-03 durable_persistence_identity"})
    operation_by_id = {
        _text(row.get("operation_id")): row
        for row in model["operations"]
        if _text(row.get("operation_id"))
    }
    ownership_rows = _markdown_table_rows_after_marker(stage_03, "- data_ownership_map:")
    ownership_by_object = {row[0]: row for row in ownership_rows if len(row) >= 8 and row[0]}
    for row in accepted_durable:
        operation_id = _text(row.get("operation_id"))
        carrier = row.get("durable_carrier") if isinstance(row.get("durable_carrier"), Mapping) else {}
        carrier_id = _text(carrier.get("carrier_id"))
        if carrier_id and carrier_id not in stage_03:
            conflicts.append({"kind": "durable-carrier-not-applied", "item": f"{operation_id}:{carrier_id}"})
        if _text(carrier.get("kind")) == "dedicated-record" and carrier_id:
            ownership = ownership_by_object.get(carrier_id)
            writer_service_id = _text(row.get("writer_service_id"))
            operation = operation_by_id.get(operation_id, {})
            contract_id = _text(operation.get("contract_id"))
            expected_write_authority = f"{writer_service_id}.{operation_id}" if writer_service_id and operation_id else writer_service_id or operation_id
            if ownership is None:
                conflicts.append({"kind": "durable-carrier-ownership-not-rendered", "item": f"{operation_id}:{carrier_id}"})
            else:
                if ownership[1] != writer_service_id:
                    conflicts.append({"kind": "durable-carrier-owner-not-applied", "item": f"{operation_id}:{carrier_id}:{ownership[1]}"})
                if ownership[2] != expected_write_authority:
                    conflicts.append({"kind": "durable-carrier-write-operation-not-applied", "item": f"{operation_id}:{carrier_id}:{ownership[2]}"})
                if contract_id and ownership[4] != contract_id:
                    conflicts.append({"kind": "durable-carrier-contract-not-applied", "item": f"{operation_id}:{carrier_id}:{ownership[4]}"})
        for component in row.get("identity_components", []) if isinstance(row.get("identity_components"), list) else []:
            component_text = _text(component)
            if component_text and component_text not in stage_03:
                conflicts.append({"kind": "durable-identity-component-not-applied", "item": f"{operation_id}:{component_text}"})
        for binding in carrier.get("field_bindings", []) if isinstance(carrier.get("field_bindings"), list) else []:
            if not isinstance(binding, Mapping):
                continue
            carrier_field = _text(binding.get("carrier_field"))
            if carrier_field and carrier_field not in stage_03:
                conflicts.append({"kind": "durable-carrier-field-not-applied", "item": f"{operation_id}:{carrier_field}"})

    for row in model["data_decisions"]:
        aggregate_id = _text(row.get("aggregate_id"))
        decision_id = _text(row.get("decision_id"))
        table_name = _text(row.get("table_name"))
        fields = row.get("fields")
        if table_name and isinstance(fields, list) and fields and table_name not in stage_03:
            conflicts.append({"kind": "accepted-data-table-not-rendered", "item": f"{decision_id}:{table_name}"})
        if isinstance(fields, list) and (aggregate_id or table_name):
            identity = aggregate_id or decision_id or table_name
            for field in fields:
                if not isinstance(field, Mapping):
                    continue
                field_name = _text(field.get("name") or field.get("field_name"))
                if field_name and field_name not in stage_03:
                    conflicts.append({"kind": "accepted-data-field-not-rendered", "item": f"{identity}:{field_name}"})

    forbidden_generic_crud = any(
        re.search(
            r"no[-_ ]generic[-_ ]crud|generic crud|通用\s*crud",
            _text(row.get("realization_id")) + " " + _text(row.get("statement")),
            flags=re.IGNORECASE,
        )
        for row in model["non_operations"] + model["state_policy_failure"]
    )
    if forbidden_generic_crud:
        for match in re.finditer(
            r"\b(?:Create|List|UpdateStatus|Delete)(?:Record|Item|Entity|Resource)\b|/api/v1/(?:records|items|entities|resources)\b",
            combined,
            flags=re.IGNORECASE,
        ):
            if match.group(0) not in accepted_operation_ids:
                conflicts.append({"kind": "generic-crud-conflicts-with-authority", "item": match.group(0)})

    p1 = model.get("p1_authority", {})
    p1_world = p1.get("product_world_decision", {}) if isinstance(p1, Mapping) else {}
    topology = p1_world.get("topology", {}) if isinstance(p1_world, Mapping) else {}
    topology_mode = _text(topology.get("mode")) if isinstance(topology, Mapping) else ""
    if topology_mode and topology_mode not in combined:
        conflicts.append({"kind": "p1-product-topology-not-preserved", "item": topology_mode})

    operation_group_by_id = {
        _text(row.get("operation_id")): _text(row.get("topology_group"))
        for row in model["operations"]
        if _text(row.get("operation_id"))
    }
    if topology_mode == "independent-outcomes":
        operation_ids = sorted(operation_group_by_id, key=len, reverse=True)
        operation_pattern = "|".join(re.escape(item) for item in operation_ids)
        if operation_pattern:
            topology_relation_patterns = (
                rf"\b(?P<left>{operation_pattern})\b\s*(?:->|→)\s*\b(?P<right>{operation_pattern})\b",
                rf"\b(?P<left>{operation_pattern})\b[^\n|]{{0,120}}(?:交接给|hand\s+off\s+to|handoff\s+to)[^\n|]{{0,80}}\b(?P<right>{operation_pattern})\b",
            )
            seen_topology_conflicts: set[tuple[str, str]] = set()
            for relation_pattern in topology_relation_patterns:
                for match in re.finditer(relation_pattern, combined, flags=re.IGNORECASE):
                    left = match.group("left")
                    right = match.group("right")
                    left_group = operation_group_by_id.get(left, "")
                    right_group = operation_group_by_id.get(right, "")
                    if left_group and right_group and left_group != right_group:
                        key = (left, right)
                        if key in seen_topology_conflicts:
                            continue
                        seen_topology_conflicts.add(key)
                        conflicts.append(
                            {
                                "kind": "cross-topology-operation-prerequisite",
                                "item": f"{left}[{left_group}] -> {right}[{right_group}]",
                            }
                        )

    route = model.get("stage_02_5_route", {})
    route = route if isinstance(route, Mapping) else {}
    route_decision = _text(route.get("decision"))
    route_dependency_ids = [
        _text(item)
        for item in route.get("dependency_ids", [])
        if _text(item)
    ] if isinstance(route.get("dependency_ids"), list) else []
    stage_02_5 = artifact_texts.get("stage-02.5-third-party-integration-architecture-design.md", "")
    if route_decision == "activate":
        if not stage_02_5:
            conflicts.append({"kind": "activated-dependency-stage-missing", "item": "stage-02.5"})
        else:
            lowered_stage = stage_02_5.casefold()
            if re.search(r"stage_status:\s*`?skipped`?", lowered_stage):
                conflicts.append({"kind": "activated-dependency-rendered-skipped", "item": "stage-02.5"})
            for dependency_id in route_dependency_ids:
                if dependency_id not in stage_02_5:
                    conflicts.append({"kind": "activated-dependency-not-rendered", "item": dependency_id})

    projection = {
        "authority_digest": model["authority_digest"],
        "operation_ids": accepted_operation_ids,
        "contract_ids": [_text(row.get("contract_id")) for row in model["operations"]],
        "aggregate_ids": [_text(row.get("aggregate_id")) for row in model["aggregates"]],
        "non_operation_ids": [_text(row.get("realization_id")) for row in model["non_operations"]],
        "durable_persistence_operation_ids": accepted_durable_ids,
        "p1_topology_mode": topology_mode,
    }
    return {
        "schema_version": P2_CANONICAL_CONVERGENCE_SCHEMA,
        "status": "pass" if not conflicts else "blocked",
        "writer_id": P2_CANONICAL_WRITER_ID,
        "authority_digest": model["authority_digest"],
        "projection_digest": _canonical_digest(projection),
        "artifact_digests": {
            name: "sha256:" + sha256(text.encode("utf-8")).hexdigest()
            for name, text in sorted(artifact_texts.items())
        },
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "checked_service_count": len(model["services"]),
        "checked_operation_count": len(model["operations"]),
        "checked_aggregate_count": len(model["aggregates"]),
        "checked_non_operation_count": len(model["non_operations"]),
        "checked_durable_persistence_count": len(accepted_durable),
        "p1_topology_mode": topology_mode,
        "claim_ceiling": (
            "This report proves bounded canonical application checks over accepted P2 architecture authority. "
            "It does not prove implementation realization, provider availability, UAT, release readiness, or production readiness."
        ),
    }


def verify_p2_canonical_artifacts(
    *,
    output_dir: Path,
    authority: Mapping[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    names = (
        "stage-01-architecture-definition-and-boundary-setting.md",
        "stage-02-domain-module-service-decomposition.md",
        "stage-02.5-third-party-integration-architecture-design.md",
        "stage-03-data-storage-and-interface-design.md",
        "stage-04-design-convergence-and-delivery-prototype.md",
        "engineering-spec-pack.md",
        "phase-3-implementation-entry.md",
    )
    artifact_texts = {
        name: path.read_text(encoding="utf-8")
        for name in names
        if (path := output_dir / name).exists()
    }
    report = validate_p2_canonical_authority_application(authority=authority, artifact_texts=artifact_texts)
    write_json_atomic(report_path, report)
    if report["status"] != "pass":
        kinds = sorted({row["kind"] for row in report["conflicts"]})
        raise P2CanonicalAuthorityConvergenceError(
            "P2 existing renderer did not converge to accepted authority: " + ", ".join(kinds)
        )
    return report
