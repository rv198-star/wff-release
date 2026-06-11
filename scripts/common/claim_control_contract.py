#!/usr/bin/env python3
"""Lightweight claim-control helpers for AI-generated artifact consistency.

The module defines the first small generic contract for issue #41.  WFF phases
use it as an adapter/profile layer, but the claim, writing-plan, proposed-claim,
and evidence-ledger rules are intentionally not phase-specific.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


SIMPLE_ARTIFACT_MAX_CLAIMS = 8
SIMPLE_ARTIFACT_MAX_VIEWS = 1
FORBIDDEN_EVIDENCE_TRUTH_FIELDS = {
    "accepted_claim",
    "accepted_claims",
    "backfilled_claims",
    "canonical_claim_index",
    "canonical_claims",
    "canonical_truth",
    "claim_index",
    "claims",
    "corrected_claims",
    "derived_accepted_claims",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _non_empty_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _claim_rows(surface: dict[str, Any]) -> list[dict[str, Any]]:
    claim_index = _as_dict(surface.get("claim_index"))
    return [row for row in _as_list(claim_index.get("claims")) if isinstance(row, dict)]


def _proposed_claim_rows(surface: dict[str, Any]) -> list[dict[str, Any]]:
    proposed_claims = _as_dict(surface.get("proposed_claims"))
    return [row for row in _as_list(proposed_claims.get("claims")) if isinstance(row, dict)]


def _claim_id(row: dict[str, Any]) -> str:
    return str(row.get("id") or "").strip()


def _view_rows(surface: dict[str, Any]) -> list[dict[str, Any]]:
    writing_plan = _as_dict(surface.get("writing_plan"))
    return [row for row in _as_list(writing_plan.get("views")) if isinstance(row, dict)]


def _render_ref_rows(surface: dict[str, Any]) -> list[dict[str, Any]]:
    render_refs = _as_dict(surface.get("render_refs"))
    return [row for row in _as_list(render_refs.get("refs")) if isinstance(row, dict)]


def _render_refs_surface(surface: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(surface.get("render_refs"))


def _writing_plan_rendered_claim_refs(surface: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for view in _view_rows(surface):
        refs.extend(_non_empty_strings(view.get("rendered_claim_refs")))
    return sorted(set(refs))


def _evidence_rendered_claim_refs(surface: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for row in _render_ref_rows(surface):
        refs.extend(_non_empty_strings(row.get("rendered_claim_refs")))
        refs.extend(_non_empty_strings(row.get("claim_refs")))
    return sorted(set(refs))


def _evidence_source_claim_refs(surface: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for row in _render_ref_rows(surface):
        refs.extend(_non_empty_strings(row.get("source_claim_refs")))
    return sorted(set(refs))


def _evidence_ledger_entries(surface: dict[str, Any]) -> list[dict[str, Any]]:
    render_refs = _render_refs_surface(surface)
    artifact_id = str(render_refs.get("artifact_id") or "").strip()
    artifact_version = str(render_refs.get("artifact_version") or "").strip()
    artifact_hash = str(render_refs.get("artifact_hash") or "").strip()
    claim_surface_version = str(render_refs.get("claim_surface_version") or "").strip()
    claim_surface_hash = str(render_refs.get("claim_surface_hash") or "").strip()

    entries: list[dict[str, Any]] = []
    for row in _render_ref_rows(surface):
        rendered_claim_refs = _non_empty_strings(row.get("rendered_claim_refs")) or _non_empty_strings(
            row.get("claim_refs")
        )
        entries.append(
            {
                "artifact_id": str(row.get("artifact_id") or artifact_id).strip(),
                "artifact_version": str(row.get("artifact_version") or artifact_version).strip(),
                "artifact_hash": str(row.get("artifact_hash") or artifact_hash).strip(),
                "block_id": str(row.get("block_id") or "").strip(),
                "view_id": str(row.get("view_id") or "").strip(),
                "rendered_claim_refs": rendered_claim_refs,
                "source_claim_refs": _non_empty_strings(row.get("source_claim_refs")),
                "proposed_claim_refs": _non_empty_strings(row.get("proposed_claim_refs")),
                "audit_status": str(row.get("audit_status") or "").strip(),
                "claim_surface_version": str(row.get("claim_surface_version") or claim_surface_version).strip(),
                "claim_surface_hash": str(row.get("claim_surface_hash") or claim_surface_hash).strip(),
            }
        )
    return entries


def _forbidden_evidence_truth_fields(surface: dict[str, Any]) -> list[str]:
    render_refs = _render_refs_surface(surface)
    fields: list[str] = []
    for key in sorted(FORBIDDEN_EVIDENCE_TRUTH_FIELDS):
        if key in render_refs:
            fields.append(f"render_refs.{key}")
    for index, row in enumerate(_render_ref_rows(surface)):
        for key in sorted(FORBIDDEN_EVIDENCE_TRUTH_FIELDS):
            if key in row:
                fields.append(f"render_refs.refs[{index}].{key}")
    return fields


def _required_claim_refs(surface: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for view in _view_rows(surface):
        refs.extend(_non_empty_strings(view.get("required_claim_refs")))
    return sorted(set(refs))


def _writing_plan_view_ids(surface: dict[str, Any]) -> list[str]:
    return sorted(set(str(view.get("view_id") or "").strip() for view in _view_rows(surface) if view.get("view_id")))


def _render_ref_view_ids(surface: dict[str, Any]) -> list[str]:
    return sorted(
        set(str(row.get("view_id") or "").strip() for row in _render_ref_rows(surface) if row.get("view_id"))
    )


def validate_claim_control_surface(surface: dict[str, Any]) -> dict[str, Any]:
    """Validate a minimal claim index + writing plan surface.

    The validator enforces only the issue #41 contract: accepted claims live in
    the claim index, proposed claims are separate deltas, and rendered refs must
    resolve to accepted claim ids.
    """

    claim_rows = _claim_rows(surface)
    proposed_rows = _proposed_claim_rows(surface)
    accepted_claim_ids = [_claim_id(row) for row in claim_rows if _claim_id(row)]
    proposed_claim_ids = [_claim_id(row) for row in proposed_rows if _claim_id(row)]
    duplicate_claim_ids = sorted(claim_id for claim_id, count in Counter(accepted_claim_ids).items() if count > 1)
    accepted_claim_id_set = set(accepted_claim_ids)
    proposed_claim_id_set = set(proposed_claim_ids)
    writing_plan_rendered_refs = _writing_plan_rendered_claim_refs(surface)
    evidence_rendered_refs = _evidence_rendered_claim_refs(surface)
    evidence_source_refs = _evidence_source_claim_refs(surface)
    rendered_refs = sorted(set(writing_plan_rendered_refs + evidence_rendered_refs))
    evidence_ledger_claim_refs = sorted(set(evidence_rendered_refs + evidence_source_refs))
    required_refs = _required_claim_refs(surface)

    unknown_claim_refs = sorted(
        ref
        for ref in sorted(set(rendered_refs + evidence_source_refs))
        if ref not in accepted_claim_id_set and ref not in proposed_claim_id_set
    )
    rendered_proposed_claim_refs = sorted(ref for ref in rendered_refs if ref in proposed_claim_id_set)
    missing_required_claim_refs = sorted(ref for ref in required_refs if ref not in writing_plan_rendered_refs)
    forbidden_alias_claim_ids = sorted(
        _claim_id(row) for row in claim_rows if _claim_id(row) and _non_empty_strings(row.get("aliases"))
    )
    forbidden_registry_truth_fields = _forbidden_evidence_truth_fields(surface)

    classifications: list[str] = []
    if duplicate_claim_ids:
        classifications.append("duplicate_claim_id")
    if unknown_claim_refs:
        classifications.append("unknown_claim_ref")
    if rendered_proposed_claim_refs:
        classifications.append("proposed_claim_rendered_as_accepted")
    if missing_required_claim_refs:
        classifications.append("missing_required_claim_coverage")
    if forbidden_alias_claim_ids:
        classifications.append("forbidden_alias_usage")
    if forbidden_registry_truth_fields:
        classifications.append("forbidden_registry_truth_field")

    render_refs = _render_refs_surface(surface)

    return {
        "artifact_kind": "claim-control-contract-audit",
        "overall_status": "pass" if not classifications else "blocked",
        "classifications": classifications,
        "checks": {
            "accepted_claim_count": len(accepted_claim_ids),
            "proposed_claim_count": len(proposed_claim_ids),
            "writing_plan_rendered_claim_refs": writing_plan_rendered_refs,
            "evidence_rendered_claim_refs": evidence_rendered_refs,
            "evidence_source_claim_refs": evidence_source_refs,
            "evidence_ledger_claim_refs": evidence_ledger_claim_refs,
            "evidence_ledger_entries": _evidence_ledger_entries(surface),
            "evidence_claim_surface": {
                "version": str(render_refs.get("claim_surface_version") or "").strip(),
                "hash": str(render_refs.get("claim_surface_hash") or "").strip(),
            },
            "rendered_claim_refs": rendered_refs,
            "required_claim_refs": required_refs,
            "duplicate_claim_ids": duplicate_claim_ids,
            "unknown_claim_refs": unknown_claim_refs,
            "rendered_proposed_claim_refs": rendered_proposed_claim_refs,
            "missing_required_claim_refs": missing_required_claim_refs,
            "forbidden_alias_claim_ids": forbidden_alias_claim_ids,
            "forbidden_registry_truth_fields": forbidden_registry_truth_fields,
            "registry_policy": "evidence-ledger-only",
            "proposed_claim_policy": "proposal-delta-not-accepted-truth",
        },
    }


def build_path_a_evidence_entries(surface: dict[str, Any]) -> list[dict[str, Any]]:
    """Return evidence-ledger rows for a simple Path A artifact.

    Path A emits evidence rows for rendered/source refs, but the rows remain an
    evidence surface only. They do not create or correct accepted claims.
    """

    return _evidence_ledger_entries(surface)


def validate_path_a_surface(surface: dict[str, Any]) -> dict[str, Any]:
    """Validate the lightweight Path A contract for simple local artifacts."""

    report = validate_claim_control_surface(surface)
    checks = dict(report["checks"])
    classifications = list(report["classifications"])
    proposed_claim_ids = {_claim_id(row) for row in _proposed_claim_rows(surface) if _claim_id(row)}
    source_proposed_claim_refs = sorted(ref for ref in checks["evidence_source_claim_refs"] if ref in proposed_claim_ids)

    if not checks["accepted_claim_count"]:
        classifications.append("path_a_missing_local_claim_index")
    if not _render_ref_rows(surface):
        classifications.append("path_a_missing_render_refs")
    if not checks["evidence_rendered_claim_refs"]:
        classifications.append("path_a_missing_rendered_claim_refs")
    if source_proposed_claim_refs:
        classifications.append("proposed_claim_used_as_source_ref")

    checks.update(
        {
            "path": "path_a",
            "requires_writing_plan": False,
            "path_a_policy": "local-claim-index-generation-time-refs-evidence-ledger",
            "source_proposed_claim_refs": source_proposed_claim_refs,
            "evidence_ledger_entries": build_path_a_evidence_entries(surface),
        }
    )

    return {
        "artifact_kind": "path-a-claim-control-audit",
        "overall_status": "pass" if not classifications else "blocked",
        "classifications": classifications,
        "checks": checks,
    }


def validate_path_b_surface(surface: dict[str, Any]) -> dict[str, Any]:
    """Validate Path B claim control for complex multi-view artifacts.

    Path B requires the generic claim-control checks plus an explicit writing
    plan, required coverage obligations, and block/view render refs. It remains
    evidence-only: audit output may be registered downstream, but this function
    never creates accepted claims.
    """

    report = validate_claim_control_surface(surface)
    checks = dict(report["checks"])
    classifications = list(report["classifications"])
    writing_plan = _as_dict(surface.get("writing_plan"))
    render_refs = _render_refs_surface(surface)
    writing_plan_view_ids = _writing_plan_view_ids(surface)
    render_ref_view_ids = _render_ref_view_ids(surface)
    required_refs = checks["required_claim_refs"]
    evidence_ledger_entries = checks["evidence_ledger_entries"]

    if not writing_plan:
        classifications.append("missing_writing_plan")
    if not writing_plan_view_ids:
        classifications.append("missing_writing_plan_views")
    if not required_refs:
        classifications.append("missing_required_claim_obligations")
    if not render_refs:
        classifications.append("missing_render_refs")
    if not evidence_ledger_entries:
        classifications.append("missing_evidence_ledger_entries")
    if evidence_ledger_entries and any(not entry["block_id"] for entry in evidence_ledger_entries):
        classifications.append("missing_render_ref_block_id")
    if evidence_ledger_entries and any(not entry["view_id"] for entry in evidence_ledger_entries):
        classifications.append("missing_render_ref_view_id")
    missing_render_ref_view_ids = sorted(set(writing_plan_view_ids) - set(render_ref_view_ids))
    if missing_render_ref_view_ids:
        classifications.append("missing_render_ref_view_coverage")

    classifications = sorted(set(classifications))
    checks.update(
        {
            "writing_plan_artifact_id": str(writing_plan.get("artifact_id") or "").strip(),
            "writing_plan_route": str(writing_plan.get("route") or "").strip(),
            "writing_plan_view_ids": writing_plan_view_ids,
            "render_ref_view_ids": render_ref_view_ids,
            "missing_render_ref_view_ids": missing_render_ref_view_ids,
            "path_b_policy": "compiled-claim-index-plus-writing-plan-required",
            "creates_accepted_claims": False,
            "can_register_as_evidence": not classifications,
        }
    )

    return {
        "artifact_kind": "path-b-claim-control-audit",
        "overall_status": "pass" if not classifications else "blocked",
        "classifications": classifications,
        "checks": checks,
    }


def build_path_b_audit_summary(surface: dict[str, Any]) -> dict[str, Any]:
    """Build an evidence-only summary for Path B registry/audit handoff."""

    report = validate_path_b_surface(surface)
    checks = report["checks"]
    return {
        "artifact_kind": "path-b-audit-summary",
        "overall_status": report["overall_status"],
        "classifications": report["classifications"],
        "can_register_as_evidence": report["overall_status"] == "pass",
        "creates_accepted_claims": False,
        "claim_surface": checks["evidence_claim_surface"],
        "coverage": {
            "required_claim_count": len(checks["required_claim_refs"]),
            "rendered_claim_count": len(checks["rendered_claim_refs"]),
            "missing_required_claim_refs": checks["missing_required_claim_refs"],
        },
        "evidence_ledger_entries": checks["evidence_ledger_entries"],
    }


def classify_artifact_route(metadata: dict[str, Any]) -> dict[str, Any]:
    """Classify an artifact for Path A or Path B claim control."""

    source_count = int(metadata.get("source_count") or 0)
    view_count = int(metadata.get("view_count") or 0)
    claim_count = int(metadata.get("claim_count") or 0)
    has_rich_view = any(bool(metadata.get(key)) for key in ("has_mermaid", "has_tables", "has_prose_sections"))

    if (
        source_count <= 1
        and view_count <= SIMPLE_ARTIFACT_MAX_VIEWS
        and claim_count <= SIMPLE_ARTIFACT_MAX_CLAIMS
        and not has_rich_view
    ):
        route = "path_a"
        reason = "single-source-small-local-artifact"
    else:
        route = "path_b"
        reason_parts = []
        if source_count > 1 or view_count > SIMPLE_ARTIFACT_MAX_VIEWS:
            reason_parts.append("multi-source-or-multi-view-artifact")
        if claim_count > SIMPLE_ARTIFACT_MAX_CLAIMS:
            reason_parts.append("large-claim-surface")
        if has_rich_view:
            reason_parts.append("rich-rendered-view-surface")
        route = "path_b"
        reason = ";".join(reason_parts) or "complex-artifact"

    return {
        "artifact_id": str(metadata.get("artifact_id") or "").strip(),
        "route": route,
        "reason": reason,
        "metadata": {
            "source_count": source_count,
            "view_count": view_count,
            "claim_count": claim_count,
            "has_rich_view": has_rich_view,
        },
    }


def resolve_claim_control_route(
    metadata: dict[str, Any], profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Resolve the shared Path A/B route without running validators.

    The route decision is policy metadata only. It selects the required
    mechanism contract but does not create claims, validate surfaces, or emit
    evidence rows.
    """

    profile = _as_dict(profile)
    artifact_id = str(metadata.get("artifact_id") or "").strip()
    base_route = classify_artifact_route(metadata)
    route = str(base_route["route"])
    reasons = [part for part in str(base_route["reason"]).split(";") if part]
    override_applied = False
    force_path_b_artifact_ids = set(_non_empty_strings(profile.get("force_path_b_artifact_ids")))
    high_downstream_trust = bool(metadata.get("high_downstream_trust") or metadata.get("downstream_consumed"))

    if high_downstream_trust:
        route = "path_b"
        reasons.append("high-downstream-trust")
        override_applied = True
    if artifact_id and artifact_id in force_path_b_artifact_ids:
        route = "path_b"
        reasons.append("profile-forced-path-b")
        override_applied = True

    reasons = sorted(set(reasons))
    required_mechanism = "validate_path_a_surface" if route == "path_a" else "validate_path_b_surface"
    required_contract = "path-a-simple-artifact" if route == "path_a" else "path-b-complex-artifact"

    return {
        "artifact_kind": "claim-control-route-decision",
        "artifact_id": artifact_id,
        "route": route,
        "reasons": reasons,
        "reason": ";".join(reasons),
        "required_mechanism": required_mechanism,
        "required_contract": required_contract,
        "profile": str(profile.get("profile_id") or "generic").strip() or "generic",
        "override_applied": override_applied,
        "creates_claims": False,
        "creates_evidence_rows": False,
        "metadata": base_route["metadata"],
    }
