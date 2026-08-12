#!/usr/bin/env python3
"""Snapshot-bound host-Agent implementation authority for Phase 3.

Workflow builds and binds the candidate snapshot. A host Agent supplies the
implementation judgment. This module verifies and projects that decision; it
does not invent implementation meaning from filenames, operation names, tests,
or Trace occurrence.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys
from typing import Any, Mapping

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.action_card_authority_projection import build_s2_authority_extensions, build_s2_decision_template_row, load_s2_action_card_binding, s2_decision_binding_errors
from common.agentic_decision_authority import (
    AgenticDecisionAuthorityError,
    build_application_receipt,
    build_decision_envelope,
    build_input_snapshot,
    canonical_digest,
    load_json_object,
    validate_application_receipt,
    validate_decision_envelope,
    write_json_atomic,
)
from common.bounded_agentic_challenge import (
    build_bounded_challenge_template,
    challenge_summary,
)
from common.bounded_agentic_challenge_binding import BoundedChallengeBindingError
from common.bounded_agentic_challenge_compat import (
    DecisionIntegrityCompatibilityError,
    require_current_integrity_pair,
)
from common.cross_phase_surface_policy import find_cross_phase_surface_path
from phase2.agentic_architecture_authority import p2_agentic_architecture_authority_is_valid
from phase3.bounded_challenge_binding import validate_p3_decision_challenge_binding


CANDIDATE_SCHEMA = "wff.p3-agentic-implementation-candidate.v1"
DECISION_KIND = "p3-implementation-authority"
AUTHORITY_SCHEMA = "wff.p3-agentic-implementation-authority.v1"
BINDING_LEDGER_SCHEMA = "wff.p3-exact-realization-binding-ledger.v1"
APPLICATION_WRITER_ID = "phase3-canonical-implementation-writer.v1"
ALLOWED_DISPOSITIONS = {"implement", "reject", "return-p2", "review-bound"}


class P3AgenticImplementationAuthorityError(ValueError):
    pass


AUTHORITY_DELTA_LEDGER_SCHEMA = "wff.p3-authority-delta-ledger.v1"
_DELTA_AUTHORITIES = {"P1", "P2"}
_DELTA_CLASSES = {"realization-detail", "authority-precision-candidate", "product-ambiguity"}
_DELTA_LOCAL_APPLICATIONS = {"p3-local-resolution", "record-only"}


def validate_authority_delta_records(records: Any, *, known_slice_ids: set[str]) -> list[dict[str, Any]]:
    if records is None:
        return []
    if not isinstance(records, list):
        raise P3AgenticImplementationAuthorityError("P3 authority_delta_records must be a list")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in records:
        if not isinstance(raw, Mapping):
            raise P3AgenticImplementationAuthorityError("P3 authority delta must be an object")
        row = dict(raw)
        delta_id = str(row.get("delta_id") or "").strip()
        slice_id = str(row.get("source_slice_id") or "").strip()
        classification = str(row.get("classification") or "").strip()
        local_application = str(row.get("local_application") or "").strip()
        if not delta_id or delta_id in seen:
            raise P3AgenticImplementationAuthorityError("P3 authority delta identity is missing or duplicated")
        seen.add(delta_id)
        if row.get("detected_phase") != "P3" or slice_id not in known_slice_ids:
            raise P3AgenticImplementationAuthorityError(f"P3 authority delta references unknown slice or phase: {delta_id}:{slice_id}")
        if str(row.get("affected_authority") or "") not in _DELTA_AUTHORITIES or classification not in _DELTA_CLASSES:
            raise P3AgenticImplementationAuthorityError(f"P3 authority delta has invalid owner/classification: {delta_id}")
        if local_application not in _DELTA_LOCAL_APPLICATIONS or row.get("applied_upstream") is not False:
            raise P3AgenticImplementationAuthorityError(f"P3 authority delta must not mutate frozen upstream authority: {delta_id}")
        if row.get("reconciliation_status") != "deferred-post-p3":
            raise P3AgenticImplementationAuthorityError(f"P3 authority delta must defer reconciliation until post-P3: {delta_id}")
        if any(not str(row.get(field) or "").strip() for field in ("finding", "decision_statement", "claim_ceiling")) or not _strings(row.get("evidence_refs")):
            raise P3AgenticImplementationAuthorityError(f"P3 authority delta is incomplete: {delta_id}")
        if classification == "product-ambiguity" and local_application != "record-only":
            raise P3AgenticImplementationAuthorityError(f"P3 product ambiguity cannot become local implementation truth: {delta_id}")
        resolution = row.get("resolution_payload")
        if resolution is not None and not isinstance(resolution, Mapping):
            raise P3AgenticImplementationAuthorityError(f"P3 authority delta resolution_payload must be an object: {delta_id}")
        overrides = resolution.get("schema_type_overrides", {}) if isinstance(resolution, Mapping) else {}
        if not isinstance(overrides, Mapping) or any(not str(key).strip() or not str(value).strip() or len(str(value)) > 64 or any(not (char.isalnum() or char in "_[](), ") for char in str(value)) for key, value in overrides.items()):
            raise P3AgenticImplementationAuthorityError(f"P3 authority delta has invalid schema_type_overrides: {delta_id}")
        additions = resolution.get("schema_field_additions", {}) if isinstance(resolution, Mapping) else {}
        if not isinstance(additions, Mapping) or any(not str(table).strip() or not isinstance(fields, list) or any(not isinstance(field, Mapping) or not str(field.get("field_name") or "").strip() or not str(field.get("data_type") or "").strip() for field in fields) for table, fields in additions.items()):
            raise P3AgenticImplementationAuthorityError(f"P3 authority delta has invalid schema_field_additions: {delta_id}")
        result.append(row)
    return result


def validate_authority_delta_ledger(ledger: Mapping[str, Any], *, authority: Mapping[str, Any]) -> list[dict[str, Any]]:
    body = {key: value for key, value in ledger.items() if key != "content_digest"}
    if ledger.get("schema_version") != AUTHORITY_DELTA_LEDGER_SCHEMA or ledger.get("content_digest") != canonical_digest(body):
        raise P3AgenticImplementationAuthorityError("P3 authority delta ledger is invalid")
    if ledger.get("decision_id") != authority.get("decision_id") or ledger.get("decision_digest") != authority.get("decision_digest"):
        raise P3AgenticImplementationAuthorityError("P3 authority delta ledger is bound to another implementation decision")
    if ledger.get("upstream_mutation_performed") is not False or ledger.get("reconciliation_status") != "deferred-post-p3":
        raise P3AgenticImplementationAuthorityError("P3 authority delta ledger violates deferred reconciliation")
    return validate_authority_delta_records(ledger.get("records", []), known_slice_ids=set((authority.get("slice_decisions") or {}).keys()))


def p3_schema_type_overrides(authority: Mapping[str, Any], delta_records: list[dict[str, Any]] | None = None) -> dict[str, str]:
    rows = delta_records if delta_records is not None else validate_authority_delta_records(
        authority.get("authority_delta_records", []), known_slice_ids=set((authority.get("slice_decisions") or {}).keys())
    )
    result: dict[str, str] = {}
    for row in rows:
        if row.get("local_application") != "p3-local-resolution":
            continue
        payload = row.get("resolution_payload") if isinstance(row.get("resolution_payload"), Mapping) else {}
        for key, value in payload.get("schema_type_overrides", {}).items() if isinstance(payload.get("schema_type_overrides"), Mapping) else []:
            name, data_type = str(key).strip(), str(value).strip().lower()
            if name in result and result[name] != data_type:
                raise P3AgenticImplementationAuthorityError(f"conflicting P3 schema type override: {name}")
            result[name] = data_type
    return result


def build_authority_delta_ledger(*, decision_id: str, decision_digest: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    ledger = {
        "schema_version": AUTHORITY_DELTA_LEDGER_SCHEMA,
        "status": "recorded" if records else "none-recorded",
        "phase_id": "P3",
        "decision_id": decision_id,
        "decision_digest": decision_digest,
        "upstream_mutation_performed": False,
        "reconciliation_status": "deferred-post-p3",
        "records": records,
        "summary": {
            "count": len(records),
            "p1_candidate_count": sum(row.get("affected_authority") == "P1" for row in records),
            "p2_candidate_count": sum(row.get("affected_authority") == "P2" for row in records),
            "locally_applied_count": sum(row.get("local_application") == "p3-local-resolution" for row in records),
            "record_only_count": sum(row.get("local_application") == "record-only" for row in records),
        },
        "claim_ceiling": "P3-local refinement evidence only; frozen P1/P2 authority is unchanged and reconciliation is post-P3.",
    }
    ledger["content_digest"] = canonical_digest(ledger)
    return ledger


def content_digest_is_valid(payload: Mapping[str, Any], *, schema_version: str) -> bool:
    if not isinstance(payload, dict) or payload.get("schema_version") != schema_version:
        return False
    expected = str(payload.get("content_digest") or "")
    body = {key: value for key, value in payload.items() if key != "content_digest"}
    return bool(expected and expected == canonical_digest(body))


def _surface(root: Path, name: str) -> Path:
    return find_cross_phase_surface_path(root, "phase2", name)


def _required_p2_paths(phase2_root: Path) -> dict[str, Path]:
    return {
        "architecture_authority": phase2_root / "p2-agentic-architecture-authority.json",
        "architecture_application": phase2_root / "p2-agentic-architecture-application-receipt.json",
        "disposition_ledger": phase2_root / "p2-commitment-disposition-ledger.json",
        "semantic_union": phase2_root / "semantic-commitment-union.json",
        "operation_sources": _surface(phase2_root, "operation-source-obligation-matrix.json"),
        "operation_semantics": _surface(phase2_root, "operation-behavior-semantics.json"),
        "component_catalog": _surface(phase2_root, "implementation-component-catalog.json"),
        "component_obligations": _surface(phase2_root, "component-action-card-obligation-matrix.json"),
        "p2_decision": _surface(phase2_root, "p2-agentic-architecture-decision.json"),
    }


def _require_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = load_json_object(path)
    except (OSError, ValueError):
        payload = {}
    if not payload:
        raise P3AgenticImplementationAuthorityError(f"required P2 authority is missing or unreadable: {label}")
    return payload


def _validate_p2_authority_chain(phase2_root: Path) -> tuple[dict[str, Path], dict[str, dict[str, Any]]]:
    paths = _required_p2_paths(phase2_root)
    payloads = {key: _require_object(path, key) for key, path in paths.items()}
    authority = payloads["architecture_authority"]
    if not p2_agentic_architecture_authority_is_valid(authority):
        raise P3AgenticImplementationAuthorityError("P2 Agentic architecture authority is invalid")
    application = payloads["architecture_application"]
    try:
        validate_application_receipt(
            application,
            decision=payloads["p2_decision"],
        )
    except (OSError, ValueError) as exc:
        raise P3AgenticImplementationAuthorityError("P2 architecture application receipt is invalid") from exc
    if str(application.get("decision_digest") or "") != str(authority.get("decision_digest") or ""):
        raise P3AgenticImplementationAuthorityError("P2 authority/application decision digest mismatch")
    try:
        require_current_integrity_pair(
            decision=payloads["p2_decision"],
            authority=authority,
            label="P2 Agentic authority",
        )
    except DecisionIntegrityCompatibilityError as exc:
        raise P3AgenticImplementationAuthorityError(str(exc)) from exc
    union = payloads["semantic_union"]
    if not content_digest_is_valid(union, schema_version="wff.semantic-commitment-union.v1"):
        raise P3AgenticImplementationAuthorityError("P2 semantic commitment union is invalid")
    if union.get("status") != "commitment-union-built":
        raise P3AgenticImplementationAuthorityError("P2 semantic commitment union is not evaluable")
    operation_rows = payloads["operation_sources"].get("operations")
    if not isinstance(operation_rows, list):
        raise P3AgenticImplementationAuthorityError("P2 operation authority rows are missing")
    if not isinstance(payloads["component_catalog"].get("components"), list) or not isinstance(payloads["component_obligations"].get("components"), list):
        raise P3AgenticImplementationAuthorityError("P2 Action Card component/obligation denominator is missing")
    return paths, payloads


def _required_slices(payloads: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    union = payloads["semantic_union"]
    operation_rows = payloads["operation_sources"].get("operations", [])
    operations = {
        str(row.get("operation_id") or "").strip(): dict(row)
        for row in operation_rows
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
    slices: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for commitment in union.get("commitments", []):
        if not isinstance(commitment, dict):
            continue
        if str(commitment.get("p3_realization_requirement") or "") != "exact-realization-required":
            continue
        operation_contracts = commitment.get("p2_operation_contracts")
        if isinstance(operation_contracts, dict):
            for operation_id, contract_id in operation_contracts.items():
                operation_id = str(operation_id).strip()
                contract_id = str(contract_id).strip()
                if not operation_id or not contract_id or (contract_id, operation_id) in seen:
                    continue
                seen.add((contract_id, operation_id))
                source = operations.get(operation_id, {})
                slices.append(
                    {
                        "slice_id": f"P3-SLICE-{len(slices) + 1:03d}",
                        "commitment_id": str(commitment.get("commitment_id") or ""),
                        "contract_id": contract_id,
                        "operation_id": operation_id,
                        "source_refs": list(commitment.get("source_refs", [])),
                        "api_endpoint": str(source.get("api_endpoint") or ""),
                        "http_method": str(source.get("http_method") or ""),
                        "candidate_authority": "p2-exact-operation-contract",
                    }
                )
        non_operation = commitment.get("p2_non_operation_realizations")
        if isinstance(non_operation, dict):
            for realization_id, row in non_operation.items():
                slices.append(
                    {
                        "slice_id": f"P3-SLICE-{len(slices) + 1:03d}",
                        "commitment_id": str(commitment.get("commitment_id") or ""),
                        "contract_id": "",
                        "operation_id": "",
                        "non_operation_realization_id": str(realization_id),
                        "non_operation_realization": dict(row) if isinstance(row, dict) else {},
                        "source_refs": list(commitment.get("source_refs", [])),
                        "candidate_authority": "p2-exact-non-operation-realization",
                    }
                )
    if not slices:
        raise P3AgenticImplementationAuthorityError("P2 authority contains no exact P3 realization slices")
    return slices


def build_p3_agentic_implementation_candidate(phase2_root: Path, *, action_card_root: Path | None = None, s1b_manifest_path: Path | None = None) -> dict[str, Any]:
    root = phase2_root.resolve()
    action_card_root = action_card_root or (root / ".phase3-s1b")
    paths, payloads = _validate_p2_authority_chain(root)
    try:
        operation_sources = {
            str(row.get("operation_id") or "").strip(): row
            for row in payloads["operation_sources"]["operations"]
            if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
        }
        binding = load_s2_action_card_binding(
            action_card_root=action_card_root,
            required_slices=_required_slices(payloads),
            component_catalog_rows=payloads["component_catalog"]["components"],
            component_obligation_rows=payloads["component_obligations"]["components"],
            operation_source_rows=operation_sources,
            authority=payloads["architecture_authority"],
        )
    except ValueError as exc:
        raise P3AgenticImplementationAuthorityError(str(exc)) from exc
    manifest_path = (s1b_manifest_path or (action_card_root / ".phase3-review" / "p3-s1b-action-card-content-manifest.json")).resolve()
    write_json_atomic(manifest_path, binding["card_content_manifest"])
    snapshot_inputs = list(sorted(paths.items())) + [("action-card-semantic-convergence.json", binding["convergence_path"]), ("p3-s1b-action-card-content-manifest.json", manifest_path)]
    input_snapshot = build_input_snapshot(phase_id="P3", inputs=tuple(snapshot_inputs))
    admission = {key: value for key, value in binding["admission"].items() if key != "readiness_by_component"}
    candidate = {
        "schema_version": CANDIDATE_SCHEMA,
        "status": "agentic-decision-required",
        "phase_id": "P3",
        "input_snapshot": input_snapshot,
        "input_snapshot_digest": input_snapshot["snapshot_digest"],
        "p2_authority": {
            "decision_id": payloads["architecture_authority"].get("decision_id"),
            "decision_digest": payloads["architecture_authority"].get("decision_digest"),
            "authority_digest": payloads["architecture_authority"].get("content_digest"),
            "application_receipt_digest": payloads["architecture_application"].get("content_digest"),
            "semantic_union_digest": payloads["semantic_union"].get("content_digest"),
        },
        "s1b_admission": admission,
        "component_coverage": binding["component_coverage"],
        "required_slices": binding["required_slices"],
        "decision_contract": {
            "allowed_dispositions": sorted(ALLOWED_DISPOSITIONS),
            "implement_requires": ["semantic_owner", "aggregate", "domain_invariants", "state_mutation", "authorization", "failure_behavior", "persistence_effects", "integration_behavior", "implementation_targets", "test_targets", "runtime_evidence_intents", "preserved_constraint_ids", "reason", "claim_ceiling"],
            "boundary": "S1B-verified Action Card/P2 bindings are immutable; the host Agent owns only implementation judgment",
        },
        "claim_ceiling": (
            "This candidate binds exact accepted P2 realization slices to S1B-verified Action Cards. It is not an "
            "implementation decision, does not authorize code generation, and cannot make P3 implementation-ready."
        ),
    }
    candidate["content_digest"] = canonical_digest(candidate)
    return candidate


def build_p3_agentic_implementation_decision_template(candidate: Mapping[str, Any]) -> dict[str, Any]:
    semantic_payload = {
        "implementation_slices": [
            build_s2_decision_template_row(row)
            for row in candidate.get("required_slices", [])
            if isinstance(row, dict)
        ],
        "authority_delta_records": [],
        "overall_handoff": {
            "status": "return-required",
            "minimum_rerun": "P3",
            "claim_ceiling": "No accepted implementation decision yet.",
        },
    }
    return build_decision_envelope(
        phase_id="P3",
        decision_kind=DECISION_KIND,
        decision_id="P3-DECISION-REQUIRED",
        owner_id="host-agent-required",
        input_snapshot=candidate["input_snapshot"],
        semantic_payload=semantic_payload,
        decision_status="agentic-decision-required",
        unresolved_items=tuple(
            {
                "item_id": str(row.get("slice_id") or ""),
                "owner": "P3 host Agent",
                "reason": "implementation judgment not supplied",
                "minimum_rerun": "P3",
                "claim_ceiling": "no implementation-authority claim",
            }
            for row in candidate.get("required_slices", [])
            if isinstance(row, dict)
        ),
        claim_ceiling="Draft template only; no implementation authority.",
        bounded_challenge=build_bounded_challenge_template(
            phase_id="P3",
            trigger_ids=("exact-realization", "implementation-invariant"),
            owner_id="host-agent-required",
        ),
    )


def _strings(value: Any) -> list[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def validate_p3_agentic_implementation_decision(
    decision: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        validate_decision_envelope(
            decision,
            expected_phase_id="P3",
            expected_decision_kind=DECISION_KIND,
            expected_input_snapshot_digest=str(candidate["input_snapshot_digest"]),
            accepted_required=True,
        )
    except (OSError, ValueError) as exc:
        raise P3AgenticImplementationAuthorityError(
            f"P3 Agentic implementation decision is invalid: {exc}"
        ) from exc
    payload = decision.get("semantic_payload")
    if not isinstance(payload, dict):
        raise P3AgenticImplementationAuthorityError("P3 implementation semantic payload is missing")
    rows = payload.get("implementation_slices")
    if not isinstance(rows, list):
        raise P3AgenticImplementationAuthorityError("P3 implementation slices are missing")
    indexed: dict[str, dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        slice_id = str(raw.get("slice_id") or "").strip()
        if not slice_id or slice_id in indexed:
            raise P3AgenticImplementationAuthorityError("P3 implementation slice IDs must be unique and non-empty")
        indexed[slice_id] = dict(raw)
    required = {
        str(row.get("slice_id") or ""): dict(row)
        for row in candidate.get("required_slices", [])
        if isinstance(row, dict) and str(row.get("slice_id") or "")
    }
    if set(indexed) != set(required):
        raise P3AgenticImplementationAuthorityError("P3 decision must disposition every required slice exactly once")
    authority_deltas = validate_authority_delta_records(
        payload.get("authority_delta_records", []),
        known_slice_ids=set(required),
    )
    delta_by_id = {str(row["delta_id"]): row for row in authority_deltas}
    for slice_id, row in indexed.items():
        expected = required[slice_id]
        for field in ("commitment_id", "contract_id", "operation_id", "non_operation_realization_id"):
            if str(row.get(field) or "") != str(expected.get(field) or ""):
                raise P3AgenticImplementationAuthorityError(f"P3 slice {slice_id} changes accepted {field}")
        disposition = str(row.get("disposition") or "").strip()
        binding_errors = s2_decision_binding_errors(row, expected, implemented=disposition == "implement")
        if binding_errors:
            raise P3AgenticImplementationAuthorityError(f"P3 slice {slice_id} {binding_errors[0]}")
        if disposition not in ALLOWED_DISPOSITIONS:
            raise P3AgenticImplementationAuthorityError(f"P3 slice {slice_id} has unsupported disposition")
        delta_refs = _strings(row.get("authority_delta_refs"))
        if len(delta_refs) != len(set(delta_refs)):
            raise P3AgenticImplementationAuthorityError(f"P3 slice {slice_id} duplicates authority_delta_refs")
        for delta_id in delta_refs:
            delta = delta_by_id.get(delta_id)
            if delta is None:
                raise P3AgenticImplementationAuthorityError(f"P3 slice {slice_id} references unknown authority delta: {delta_id}")
            if str(delta.get("source_slice_id") or "") != slice_id:
                raise P3AgenticImplementationAuthorityError(f"P3 slice {slice_id} references authority delta owned by another slice: {delta_id}")
        if disposition == "implement":
            scalar_fields = (
                "state_mutation",
                "authorization",
                "failure_behavior",
                "persistence_effects",
                "integration_behavior",
                "reason",
                "claim_ceiling",
            )
            if any(not str(row.get(field) or "").strip() for field in scalar_fields):
                raise P3AgenticImplementationAuthorityError(f"P3 implemented slice {slice_id} is semantically incomplete")
            for field in ("domain_invariants", "implementation_targets", "test_targets", "runtime_evidence_intents"):
                if not _strings(row.get(field)):
                    raise P3AgenticImplementationAuthorityError(f"P3 implemented slice {slice_id} is missing {field}")
            if row.get("irreversible_migration") is True:
                if any(
                    not str(row.get(field) or "").strip()
                    for field in ("migration_plan", "rollback_plan")
                ) or not _strings(row.get("migration_test_targets")):
                    raise P3AgenticImplementationAuthorityError(
                        f"P3 irreversible migration slice {slice_id} lacks migration/rollback/test authority"
                    )
        else:
            if not str(row.get("reason") or "").strip() or not str(row.get("claim_ceiling") or "").strip():
                raise P3AgenticImplementationAuthorityError(f"P3 non-implemented slice {slice_id} needs reason and ceiling")
    handoff = payload.get("overall_handoff")
    if not isinstance(handoff, dict) or str(handoff.get("status") or "") not in {
        "ready",
        "bounded",
        "return-required",
    }:
        raise P3AgenticImplementationAuthorityError("P3 overall handoff is invalid")
    if any(str(row.get("disposition") or "") in {"return-p2", "reject"} for row in indexed.values()):
        if handoff.get("status") != "return-required":
            raise P3AgenticImplementationAuthorityError("P3 return/reject slices require return-required overall handoff")
    required_triggers = {"exact-realization"}
    if any(str(row.get("disposition") or "") == "implement" for row in indexed.values()):
        required_triggers.add("implementation-invariant")
    if any(row.get("irreversible_migration") is True for row in indexed.values()):
        required_triggers.add("irreversible-migration")
    try:
        validate_p3_decision_challenge_binding(
            decision=decision,
            candidate=candidate,
            required_trigger_ids=required_triggers,
        )
    except BoundedChallengeBindingError as exc:
        raise P3AgenticImplementationAuthorityError(str(exc)) from exc
    return dict(decision)


def build_p3_agentic_implementation_authority(
    decision: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    accepted = validate_p3_agentic_implementation_decision(decision, candidate=candidate)
    payload = accepted["semantic_payload"]
    rows = [dict(row) for row in payload["implementation_slices"]]
    authority_delta_records = validate_authority_delta_records(
        payload.get("authority_delta_records", []),
        known_slice_ids={str(row.get("slice_id") or "") for row in rows if str(row.get("slice_id") or "")},
    )
    decisions: dict[str, dict[str, Any]] = {}
    exact_realization_plan: list[dict[str, Any]] = []
    for row in rows:
        operation_id = str(row.get("operation_id") or "").strip()
        if operation_id and row.get("disposition") == "implement":
            invariants = [
                {"invariant": value, "test_intent": f"prove invariant for {operation_id}"}
                for value in _strings(row.get("domain_invariants"))
            ]
            decisions[operation_id] = {
                "operation_id": operation_id,
                "contract_id": str(row.get("contract_id") or ""),
                "implementation_decision_id": accepted["decision_id"],
                "implementation_decision_digest": accepted["content_digest"],
                "disposition": "implement",
                "semantic_owner": str(row.get("semantic_owner") or ""),
                "aggregate": str(row.get("aggregate") or ""),
                "operation_semantics": {
                    "semantic_owner": str(row.get("semantic_owner") or ""),
                    "aggregate": str(row.get("aggregate") or ""),
                    "state_mutation": str(row.get("state_mutation") or ""),
                    "authorization": str(row.get("authorization") or ""),
                    "failure_behavior": str(row.get("failure_behavior") or ""),
                    "persistence_effects": str(row.get("persistence_effects") or ""),
                    "integration_behavior": str(row.get("integration_behavior") or ""),
                    "source": "accepted-host-agent-implementation-decision",
                },
                "domain_invariants": invariants,
                "value_rule": {
                    "rule": str(row.get("state_mutation") or ""),
                    "test_intent": f"prove accepted state/mutation behavior for {operation_id}",
                },
                "implementation_targets": _strings(row.get("implementation_targets")),
                "test_targets": _strings(row.get("test_targets")),
                "runtime_evidence_intents": _strings(row.get("runtime_evidence_intents")),
                "authority_delta_refs": _strings(row.get("authority_delta_refs")),
                "irreversible_migration": bool(row.get("irreversible_migration")),
                "migration_plan": str(row.get("migration_plan") or ""),
                "rollback_plan": str(row.get("rollback_plan") or ""),
                "migration_test_targets": _strings(row.get("migration_test_targets")),
                "reason": str(row.get("reason") or ""),
                "claim_ceiling": str(row.get("claim_ceiling") or ""),
            }
        exact_realization_plan.append(
            {
                "slice_id": row.get("slice_id"),
                "commitment_id": row.get("commitment_id"),
                "contract_id": row.get("contract_id", ""),
                "operation_id": row.get("operation_id", ""),
                "non_operation_realization_id": row.get("non_operation_realization_id", ""),
                "component_ids": _strings(row.get("component_ids")),
                "action_card_refs": _strings(row.get("action_card_refs")),
                "preserved_constraint_ids": _strings(row.get("preserved_constraint_ids")),
                "disposition": row.get("disposition"),
                "implementation_decision_id": accepted["decision_id"],
                "implementation_decision_digest": accepted["content_digest"],
                "declared_implementation_targets": _strings(row.get("implementation_targets")),
                "declared_test_targets": _strings(row.get("test_targets")),
                "runtime_evidence_intents": _strings(row.get("runtime_evidence_intents")),
                "authority_delta_refs": _strings(row.get("authority_delta_refs")),
                "irreversible_migration": bool(row.get("irreversible_migration")),
                "migration_plan": str(row.get("migration_plan") or ""),
                "rollback_plan": str(row.get("rollback_plan") or ""),
                "migration_test_targets": _strings(row.get("migration_test_targets")),
                "reason": row.get("reason"),
                "owner": row.get("owner"),
                "minimum_rerun": row.get("minimum_rerun"),
                "claim_ceiling": row.get("claim_ceiling"),
            }
        )
    extensions = build_s2_authority_extensions(
        implementation_rows=rows,
        decision_id=accepted["decision_id"],
        decision_digest=accepted["content_digest"],
    )
    authority = {
        "schema_version": AUTHORITY_SCHEMA,
        "status": "accepted-p3-agentic-implementation-authority",
        "phase_id": "P3",
        "decision_id": accepted["decision_id"],
        "decision_digest": accepted["content_digest"],
        "input_snapshot_digest": accepted["input_snapshot_digest"],
        "p2_authority": candidate["p2_authority"],
        "s1b_admission": candidate["s1b_admission"],
        "component_coverage": candidate["component_coverage"],
        "decisions": decisions,
        **extensions,
        "exact_realization_plan": exact_realization_plan,
        "authority_delta_records": authority_delta_records,
        "overall_handoff": payload["overall_handoff"],
        "decision_integrity_contract": str(accepted.get("decision_integrity_contract") or ""),
        "challenge_binding_digest": str((accepted.get("challenge_binding") or {}).get("content_digest") or ""),
        "bounded_challenge": challenge_summary(accepted["bounded_challenge"]),
        "agentic_semantic_decisions": {
            "artifact_kind": "phase3-agentic-semantic-decision-set.v1",
            "mode": "accepted-host-agent-implementation-authority",
            "decisions": decisions,
            "summary": {
                "agentic_semantic_decision_count": len(decisions),
                "implemented_slice_count": len(
                    [row for row in exact_realization_plan if row["disposition"] == "implement"]
                ),
                "review_bound_slice_count": len(
                    [row for row in exact_realization_plan if row["disposition"] == "review-bound"]
                ),
                "default_heavy_artifact_count": 0,
            },
        },
        "claim_ceiling": str(accepted.get("claim_ceiling") or ""),
    }
    authority["content_digest"] = canonical_digest(authority)
    return authority


def p3_agentic_implementation_authority_is_valid(authority: Mapping[str, Any]) -> bool:
    if authority.get("schema_version") != AUTHORITY_SCHEMA:
        return False
    if authority.get("status") != "accepted-p3-agentic-implementation-authority":
        return False
    expected = str(authority.get("content_digest") or "")
    body = dict(authority)
    body.pop("content_digest", None)
    if expected != canonical_digest(body):
        return False
    decisions = authority.get("decisions")
    return bool(isinstance(decisions, dict) and isinstance(authority.get("slice_decisions"), dict) and isinstance(authority.get("component_realization_plan"), dict) and authority.get("component_coverage", {}).get("status") == "complete" and authority.get("decision_digest"))


def write_candidate_and_template(phase2_root: Path, output_dir: Path, *, action_card_root: Path | None = None) -> tuple[Path, Path, dict[str, Any]]:
    evidence_root = action_card_root or output_dir
    if action_card_root is None:
        from phase3.impl_action_cards import run_impl_action_cards
        report = run_impl_action_cards(phase2_root=phase2_root, output_dir=evidence_root)
        if report.get("quality_gate") != "pass":
            raise P3AgenticImplementationAuthorityError("P3 S1B Action Card admission must pass before S2 prepare")
    evidence = output_dir / ".phase3-evidence"
    candidate = build_p3_agentic_implementation_candidate(
        phase2_root,
        action_card_root=evidence_root,
        s1b_manifest_path=evidence / "p3-s1b-action-card-content-manifest.json",
    )
    template = build_p3_agentic_implementation_decision_template(candidate)
    candidate_path = evidence / "p3-agentic-implementation-candidate.json"
    template_path = evidence / "p3-agentic-implementation-decision.template.json"
    write_json_atomic(candidate_path, candidate)
    write_json_atomic(template_path, template)
    return candidate_path, template_path, candidate


def prepare_and_accept_p3_implementation_authority(
    *,
    phase2_root: Path,
    output_dir: Path,
    decision_path: Path | None,
    action_card_root: Path | None = None,
) -> dict[str, Any]:
    candidate_path, template_path, candidate = write_candidate_and_template(
        phase2_root, output_dir, action_card_root=action_card_root
    )
    if decision_path is None:
        raise P3AgenticImplementationAuthorityError(
            f"current-snapshot P3 Agentic implementation decision is required; "
            f"candidate={candidate_path}; template={template_path}"
        )
    decision = _require_object(decision_path.resolve(), "P3 implementation decision")
    authority = build_p3_agentic_implementation_authority(decision, candidate=candidate)
    evidence = output_dir / ".phase3-evidence"
    write_json_atomic(evidence / "p3-agentic-implementation-decision.json", decision)
    write_json_atomic(output_dir / "p3-agentic-implementation-authority.json", authority)
    write_json_atomic(
        evidence / "p3-authority-delta-ledger.json",
        build_authority_delta_ledger(
            decision_id=str(authority.get("decision_id") or ""),
            decision_digest=str(authority.get("decision_digest") or ""),
            records=[dict(row) for row in authority.get("authority_delta_records", []) if isinstance(row, dict)],
        ),
    )
    return authority


def apply_p3_agentic_implementation_authority_to_workspace(
    *,
    output_dir: Path,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Compatibility entrypoint for the S3 generation-only realizer."""
    from phase3.s3_code_realization import S3CodeRealizationError, realize_s3_code_and_tests

    try:
        return realize_s3_code_and_tests(output_dir=output_dir, authority=authority)
    except S3CodeRealizationError as exc:
        raise P3AgenticImplementationAuthorityError(str(exc)) from exc


def _optional_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_object(path)
    except (OSError, ValueError):
        return {}


def finalize_p3_agentic_implementation_application(
    *,
    output_dir: Path,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    if not p3_agentic_implementation_authority_is_valid(authority):
        raise P3AgenticImplementationAuthorityError("P3 implementation authority is invalid during application")
    persisted_decision_path = output_dir / ".phase3-evidence" / "p3-agentic-implementation-decision.json"
    try:
        persisted_decision = _require_object(persisted_decision_path, "persisted P3 implementation decision")
        validate_decision_envelope(
            persisted_decision,
            expected_phase_id="P3",
            expected_decision_kind=DECISION_KIND,
            expected_input_snapshot_digest=str(authority.get("input_snapshot_digest") or ""),
            accepted_required=True,
        )
    except (AgenticDecisionAuthorityError, P3AgenticImplementationAuthorityError) as exc:
        raise P3AgenticImplementationAuthorityError(
            f"persisted accepted P3 implementation decision is invalid: {exc}"
        ) from exc
    if (
        str(persisted_decision.get("decision_id") or "") != str(authority.get("decision_id") or "")
        or str(persisted_decision.get("content_digest") or "") != str(authority.get("decision_digest") or "")
    ):
        raise P3AgenticImplementationAuthorityError(
            "persisted P3 implementation decision and accepted authority diverge"
        )
    bindings = _optional_json(output_dir / "implementation-bindings.json")
    trace = _optional_json(output_dir / "trace-registry-final.json")
    if not trace:
        trace = _optional_json(output_dir / "phase-3-trace-registry-final.json")
    if not trace:
        trace = _optional_json(output_dir / "phase3-trace-registry-final.json")
    if not trace:
        trace = _optional_json(output_dir / ".phase3-evidence" / "phase3-trace-registry-final.json")
    binding_rows = bindings.get("rows", []) if isinstance(bindings.get("rows"), list) else []
    trace_rows = trace.get("rows", []) if isinstance(trace.get("rows"), list) else []
    exact_rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for plan in authority.get("exact_realization_plan", []):
        if not isinstance(plan, dict) or plan.get("disposition") != "implement":
            continue
        contract_id = str(plan.get("contract_id") or "").strip().upper()
        operation_id = str(plan.get("operation_id") or "").strip()
        if not contract_id or not operation_id:
            continue
        matches = [
            row
            for row in binding_rows
            if isinstance(row, dict)
            and str(row.get("contract_id") or row.get("source_id") or "").strip().upper() == contract_id
            and str(row.get("operation_id") or "").strip() == operation_id
            and str(row.get("implementation_decision_digest") or "") == str(authority.get("decision_digest") or "")
        ]
        trace_matches = []
        for row in trace_rows:
            if not isinstance(row, dict):
                continue
            trace_operation_id = str(
                row.get("operation_id")
                or (row.get("trace_link_evidence") or {}).get("operation_id")
                or ""
            ).strip()
            trace_contract_id = str(row.get("contract_id") or row.get("source_id") or "").strip().upper()
            confirmed = bool(
                str(row.get("status") or row.get("trace_status") or "").lower()
                in {"confirmed", "pass", "verified"}
                or str(row.get("binding_status") or "").lower() == "confirmed"
                or str(row.get("final_resolution") or "").lower() == "confirmed"
                or bool((row.get("trace_link_evidence") or {}).get("confirmed"))
            )
            if trace_contract_id == contract_id and trace_operation_id == operation_id and confirmed:
                trace_matches.append(row)
        if len(matches) != 1:
            missing.append(f"binding:{contract_id}:{operation_id}")
            continue
        binding = matches[0]
        targets = _strings(binding.get("implementation_targets"))
        tests = _strings(binding.get("test_targets"))
        if not targets or not tests:
            missing.append(f"implementation-or-test-evidence:{contract_id}:{operation_id}")
            continue
        if not trace_matches:
            missing.append(f"trace:{contract_id}:{operation_id}")
        exact_rows.append(
            {
                "contract_id": contract_id,
                "operation_id": operation_id,
                "implementation_decision_id": authority.get("decision_id"),
                "implementation_decision_digest": authority.get("decision_digest"),
                "implementation_targets": targets,
                "test_targets": tests,
                "runtime_evidence_refs": _strings(binding.get("runtime_evidence_refs")),
                "trace_confirmed": bool(trace_matches),
                "binding_status": "exact" if trace_matches else "blocking",
            }
        )
    ledger = {
        "schema_version": BINDING_LEDGER_SCHEMA,
        "status": "exact-realization-bindings-complete" if not missing else "exact-realization-bindings-blocked",
        "decision_id": authority.get("decision_id"),
        "decision_digest": authority.get("decision_digest"),
        "rows": exact_rows,
        "missing_bindings": sorted(set(missing)),
        "counts": {
            "exact": len([row for row in exact_rows if row["binding_status"] == "exact"]),
            "blocking": len(set(missing)),
        },
        "claim_ceiling": (
            "This ledger binds accepted P2 contract-operation identity to one P3 implementation decision, "
            "generated targets/tests, and confirmed Trace. It does not prove domain correctness or production readiness."
        ),
    }
    ledger["content_digest"] = canonical_digest(ledger)
    ledger_path = output_dir / "p3-exact-realization-binding-ledger.json"
    write_json_atomic(ledger_path, ledger)
    output_paths = [
        output_dir / "p3-agentic-implementation-authority.json",
        output_dir / "implementation-bindings.json",
        ledger_path,
    ]
    for name in (
        "trace-registry-final.json",
        "phase3-delivery-gate.json",
        "phase-verdict.json",
        "semantic-realization-ledger.json",
    ):
        path = output_dir / name
        if path.exists():
            output_paths.append(path)
    application = build_application_receipt(
        decision=persisted_decision,
        writer_id=APPLICATION_WRITER_ID,
        output_paths=tuple(output_paths),
        application_status="complete" if not missing else "blocked",
        missing_applications=tuple(sorted(set(missing))),
        unused_decisions=(),
        claim_ceiling=str(authority.get("claim_ceiling") or ""),
    )
    write_json_atomic(output_dir / "p3-agentic-implementation-application-receipt.json", application)
    return {"ledger": ledger, "application": application}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or validate P3 Agentic implementation authority")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--phase2-root", required=True)
    prepare.add_argument("--output-dir", required=True)
    prepare.add_argument("--action-card-root")
    validate = sub.add_parser("validate")
    validate.add_argument("--phase2-root", required=True)
    validate.add_argument("--decision", required=True)
    validate.add_argument("--authority-output", required=True)
    validate.add_argument("--action-card-root", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        candidate_path, template_path, _ = write_candidate_and_template(
            Path(args.phase2_root).resolve(),
            Path(args.output_dir).resolve(),
            action_card_root=Path(args.action_card_root).resolve() if args.action_card_root else None,
        )
        print(json.dumps({"status": "agentic-decision-required", "candidate": str(candidate_path), "template": str(template_path)}))
        return 0
    candidate = build_p3_agentic_implementation_candidate(
        Path(args.phase2_root).resolve(), action_card_root=Path(args.action_card_root).resolve()
    )
    decision = _require_object(Path(args.decision).resolve(), "P3 implementation decision")
    authority = build_p3_agentic_implementation_authority(decision, candidate=candidate)
    write_json_atomic(Path(args.authority_output).resolve(), authority)
    print(json.dumps({"status": authority["status"], "decision_id": authority["decision_id"], "slices": len(authority["exact_realization_plan"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
