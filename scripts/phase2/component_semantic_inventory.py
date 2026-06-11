from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from common.claim_control_runtime import (
    CanonicalName,
    ClaimRecord,
    ClaimRelation,
    claims_from_sidecar,
    emit_path_b_claim_control_sidecar,
)
from common.cross_phase_surface_policy import resolve_cross_phase_surface_path


def emit_component_semantic_inventory(
    *,
    output_dir: Path,
    phase1_prd: Path,
    phase1_claim_control_sidecar: Path | None,
    component_catalog_rows: list[dict[str, Any]],
    component_obligation_rows: list[dict[str, Any]],
    operation_resolution_rows: list[dict[str, Any]] | None = None,
    operation_source_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Emit the first-class P2 component semantic inventory surface."""

    artifact_path = resolve_cross_phase_surface_path(output_dir, "phase2", "component-semantic-inventory.md")
    sidecar_path = resolve_cross_phase_surface_path(
        output_dir,
        "phase2",
        "component-semantic-inventory.claim-control.json",
    )
    upstream_claims = (
        claims_from_sidecar(phase1_claim_control_sidecar, source_label="phase1-claim-control")
        if phase1_claim_control_sidecar and phase1_claim_control_sidecar.exists()
        else []
    )
    upstream_claim_refs = _declared_upstream_p1_refs(component_obligation_rows)
    source_claim_refs = sorted(upstream_claim_refs & {claim.id for claim in upstream_claims})
    claims = _component_inventory_claims(
        component_catalog_rows,
        component_obligation_rows,
        upstream_claims,
        operation_resolution_rows or [],
        operation_source_rows or [],
    )
    relations = _component_inventory_relations(
        component_catalog_rows,
        component_obligation_rows,
        claims,
        operation_resolution_rows or [],
        operation_source_rows or [],
    )
    canonical_names = _component_inventory_canonical_names(
        component_catalog_rows,
        operation_resolution_rows or [],
        operation_source_rows or [],
        claims,
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(_render_inventory_markdown(claims), encoding="utf-8")
    result = emit_path_b_claim_control_sidecar(
        artifact_path=artifact_path,
        artifact_id="p2:component-semantic-inventory",
        claims=claims,
        view_id="p2:component-semantic-inventory",
        source_count=2 if phase1_claim_control_sidecar else 1,
        upstream_surface_paths=[path for path in [phase1_prd, phase1_claim_control_sidecar] if path],
        sidecar_path=sidecar_path,
        relations=relations,
        canonical_names=canonical_names,
        source_claim_refs=source_claim_refs,
    )
    return {
        "artifact_path": str(artifact_path),
        "sidecar_path": result["sidecar_path"],
        "acceptance": result["acceptance"],
        "claim_count": len(result["surface"]["claim_index"]["claims"]),
    }


def _component_inventory_claims(
    component_catalog_rows: list[dict[str, Any]],
    component_obligation_rows: list[dict[str, Any]],
    upstream_claims: list[ClaimRecord],
    operation_resolution_rows: list[dict[str, Any]],
    operation_source_rows: list[dict[str, Any]],
) -> list[ClaimRecord]:
    obligations_by_component = {
        str(row.get("component_id") or "").strip(): row
        for row in component_obligation_rows
        if str(row.get("component_id") or "").strip()
    }
    claims: list[ClaimRecord] = []
    upstream_claims_by_id = {claim.id: claim for claim in upstream_claims}
    included_p1_claims: set[str] = set()
    operation_rows = _operation_rows_by_id(operation_resolution_rows, operation_source_rows)
    for operation_id, operation in operation_rows.items():
        claims.append(
            ClaimRecord(
                id=p2_operation_claim_id(operation_id),
                kind="implementation_operation",
                text=_operation_claim_text(operation_id, operation),
                source_refs=[
                    "phase2:p1-value-to-p2-operation-resolution-matrix",
                    "phase2:operation-source-obligation-matrix",
                ],
            )
        )
        for p1_claim_id in _operation_p1_trace_ids(operation):
            if p1_claim_id in included_p1_claims:
                continue
            included_p1_claims.add(p1_claim_id)
            upstream_claim = upstream_claims_by_id.get(p1_claim_id)
            if upstream_claim:
                claims.append(upstream_claim)
    for component in component_catalog_rows:
        component_id = str(component.get("component_id") or "").strip()
        if not component_id:
            continue
        obligation = obligations_by_component.get(component_id, {})
        component_type = str(component.get("component_type") or obligation.get("component_type") or "component").strip()
        operations = [str(item).strip() for item in component.get("related_operations", []) if str(item).strip()]
        if not operations:
            operations = [str(item).strip() for item in obligation.get("upstream_operation_ids", []) if str(item).strip()]
        suffix = f" for {', '.join(operations)}" if operations else ""
        claims.append(
            ClaimRecord(
                id=component_id,
                kind="implementation_component",
                text=f"{component_type} implementation component {component_id}{suffix}",
                source_refs=["phase2:implementation-component-catalog", "phase2:component-action-card-obligation-matrix"],
            )
        )
        for p1_claim_id in [str(item).strip() for item in obligation.get("upstream_p1_trace_ids", []) if str(item).strip()]:
            if p1_claim_id in included_p1_claims:
                continue
            included_p1_claims.add(p1_claim_id)
            upstream_claim = upstream_claims_by_id.get(p1_claim_id)
            if upstream_claim:
                claims.append(upstream_claim)
    return claims


def _declared_upstream_p1_refs(component_obligation_rows: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for obligation in component_obligation_rows:
        refs.update(
            str(item).strip()
            for item in obligation.get("upstream_p1_trace_ids", [])
            if str(item).strip()
        )
    return refs


def _component_inventory_relations(
    component_catalog_rows: list[dict[str, Any]],
    component_obligation_rows: list[dict[str, Any]],
    claims: list[ClaimRecord],
    operation_resolution_rows: list[dict[str, Any]],
    operation_source_rows: list[dict[str, Any]],
) -> list[ClaimRelation]:
    accepted_ids = {claim.id for claim in claims}
    component_types = {
        str(row.get("component_id") or "").strip(): str(row.get("component_type") or "").strip().lower()
        for row in component_catalog_rows
        if str(row.get("component_id") or "").strip()
    }
    relations: list[ClaimRelation] = []
    for operation_id, operation in _operation_rows_by_id(operation_resolution_rows, operation_source_rows).items():
        operation_claim_id = p2_operation_claim_id(operation_id)
        if operation_claim_id not in accepted_ids:
            continue
        for p1_claim_id in _operation_p1_trace_ids(operation):
            if p1_claim_id not in accepted_ids:
                continue
            relations.append(
                ClaimRelation(
                    subject=operation_claim_id,
                    predicate="traces_to",
                    object=p1_claim_id,
                )
            )
    for obligation in component_obligation_rows:
        component_id = str(obligation.get("component_id") or "").strip()
        if component_id not in accepted_ids:
            continue
        component_type = str(obligation.get("component_type") or component_types.get(component_id, "")).strip().lower()
        if component_type == "service":
            for operation_id in [str(item).strip() for item in obligation.get("upstream_operation_ids", []) if str(item).strip()]:
                operation_claim_id = p2_operation_claim_id(operation_id)
                if operation_claim_id not in accepted_ids:
                    continue
                relations.append(
                    ClaimRelation(
                        subject=component_id,
                        predicate="implements_operation",
                        object=operation_claim_id,
                    )
                )
        for p1_claim_id in [str(item).strip() for item in obligation.get("upstream_p1_trace_ids", []) if str(item).strip()]:
            if p1_claim_id not in accepted_ids:
                continue
            relations.append(
                ClaimRelation(
                    subject=component_id,
                    predicate="traces_to",
                    object=p1_claim_id,
                )
            )
    return relations


def _component_inventory_canonical_names(
    component_catalog_rows: list[dict[str, Any]],
    operation_resolution_rows: list[dict[str, Any]],
    operation_source_rows: list[dict[str, Any]],
    claims: list[ClaimRecord],
) -> list[CanonicalName]:
    accepted_ids = {claim.id for claim in claims}
    component_alias_counts = _component_alias_counts(component_catalog_rows, accepted_ids)
    reserved_canonical_values = _component_reserved_canonical_values(
        accepted_ids,
        operation_resolution_rows,
        operation_source_rows,
    )
    names: list[CanonicalName] = []
    for component in component_catalog_rows:
        component_id = str(component.get("component_id") or "").strip()
        if component_id not in accepted_ids:
            continue
        aliases = [
            alias
            for alias in _component_alias_candidates(component)
            if alias != component_id and component_alias_counts[alias] == 1
            and alias not in reserved_canonical_values
        ]
        names.append(
            CanonicalName(
                id=component_id,
                canonical=component_id,
                allowed_aliases=aliases,
            )
        )
    for operation_id in _operation_rows_by_id(operation_resolution_rows, operation_source_rows):
        operation_claim_id = p2_operation_claim_id(operation_id)
        if operation_claim_id not in accepted_ids:
            continue
        names.append(
            CanonicalName(
                id=operation_claim_id,
                canonical=operation_id,
            )
        )
    return names


def _component_reserved_canonical_values(
    accepted_ids: set[str],
    operation_resolution_rows: list[dict[str, Any]],
    operation_source_rows: list[dict[str, Any]],
) -> set[str]:
    reserved = set(accepted_ids)
    for operation_id in _operation_rows_by_id(operation_resolution_rows, operation_source_rows):
        if p2_operation_claim_id(operation_id) in accepted_ids:
            reserved.add(operation_id)
    return reserved


def _component_alias_counts(
    component_catalog_rows: list[dict[str, Any]],
    accepted_ids: set[str],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for component in component_catalog_rows:
        component_id = str(component.get("component_id") or "").strip()
        if component_id not in accepted_ids:
            continue
        counts.update(_component_alias_candidates(component))
    return counts


def _component_alias_candidates(component: dict[str, Any]) -> list[str]:
    component_id = str(component.get("component_id") or "").strip()
    return _unique_non_empty(
        [
            str(component.get("owning_module") or "").strip(),
            str(component.get("target_path_hint") or "").strip(),
        ],
        exclude={component_id},
    )


def _unique_non_empty(values: list[str], *, exclude: set[str] | None = None) -> list[str]:
    excluded = exclude or set()
    result: list[str] = []
    for value in values:
        stripped = str(value or "").strip()
        if not stripped or stripped in excluded or stripped in result:
            continue
        result.append(stripped)
    return result


def p2_operation_claim_id(operation_id: str) -> str:
    return f"P2-OP:{str(operation_id).strip()}"


def _operation_rows_by_id(
    operation_resolution_rows: list[dict[str, Any]],
    operation_source_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in [*operation_source_rows, *operation_resolution_rows]:
        operation_id = str(row.get("operation_id") or "").strip()
        if not operation_id:
            continue
        indexed.setdefault(operation_id, {}).update(row)
    return indexed


def _operation_p1_trace_ids(operation: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in ("p1_trace_ids", "upstream_p1_trace_ids"):
        value = operation.get(key, [])
        if isinstance(value, list):
            candidates = value
        else:
            candidates = str(value).replace(";", ",").split(",")
        for item in candidates:
            ref = str(item).strip()
            if ref and ref not in refs:
                refs.append(ref)
    return refs


def _operation_claim_text(operation_id: str, operation: dict[str, Any]) -> str:
    method = str(operation.get("http_method") or "").strip()
    endpoint = str(operation.get("api_endpoint") or "").strip()
    contract = str(operation.get("contract_trace_id") or "").strip()
    risk = str(operation.get("risk_tier") or "").strip()
    endpoint_text = f" {method} {endpoint}".strip()
    parts = [f"Operation {operation_id}"]
    if endpoint_text:
        parts.append(endpoint_text)
    if contract:
        parts.append(f"contract {contract}")
    if risk:
        parts.append(f"risk {risk}")
    return " bound to ".join(parts)


def _render_inventory_markdown(claims: list[ClaimRecord]) -> str:
    lines = ["# Component Semantic Inventory", ""]
    for claim in claims:
        lines.append(f"- {claim.id}: {claim.text}")
    return "\n".join(lines).rstrip() + "\n"
