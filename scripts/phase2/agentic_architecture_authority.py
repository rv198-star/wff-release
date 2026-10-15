#!/usr/bin/env python3
"""Snapshot-bound P2 Agentic architecture authority and exact P1 disposition contract."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.agentic_decision_authority import (
    AgenticDecisionAuthorityError,
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
from common.complexity_classifier import count_external_integrations
from common.product_interaction_semantics import (
    ProductInteractionSemanticsContractError,
    validate_p2_product_interaction_semantics,
)
from phase2.bounded_challenge_binding import validate_p2_decision_challenge_binding


PHASE_ID = "P2"
DECISION_KIND = "p2-architecture-and-commitment-disposition-authority"
CANDIDATE_SCHEMA = "wff.p2-agentic-architecture-candidate.v1"
AUTHORITY_SCHEMA = "wff.p2-agentic-architecture-authority.v1"
DISPOSITION_SCHEMA = "wff.p2-commitment-disposition-ledger.v1"
DEPENDENCY_SCHEMA = "wff.p2-dependency-routing-receipt.v1"

DISPOSITIONS = {
    "exact-operation",
    "exact-operation-set",
    "non-operation-realization",
    "return-p1",
    "p2-local-repair",
    "deferred",
    "excluded",
    "review-bound",
}
DEPENDENCY_DISPOSITIONS = {
    "activate",
    "internal-local",
    "defer",
    "exclude",
    "return",
    "review-bound",
}
PERSISTENCE_MODES = {"durable-write", "read-only", "no-durable-state"}
PERSISTENCE_COMMAND_KINDS = {"insert", "update", "append", "upsert", "select-one", "select-many", "select-projection", "none"}
IDEMPOTENCY_MODES = {"replay-safe", "not-applicable"}
DURABLE_CARRIER_KINDS = {"aggregate", "dedicated-record", "not-applicable"}
DURABLE_ENFORCEMENT_MODES = {"unique-constraint", "primary-key", "application-transaction", "not-applicable"}
REPLAY_BEHAVIORS = {"return-existing", "reject-conflict", "idempotent-update", "new-write-per-request", "read-only", "no-durable-state"}
INTERACTION_BINDING_MODES = {"read", "write", "read_write"}
INTERACTION_VALUE_SOURCES = {"user-input", "workflow-context", "response-binding", "auth-session"}
INTERACTION_CANDIDATE_SOURCE_STATUSES = {"accepted", "absent", "review-bound", "not-applicable"}
INTERACTION_DISCOVERY_REQUIREMENTS = {"required", "not-required", "review-bound"}
INTERACTION_CARDINALITIES = {"one", "optional-one", "many", "one-or-more", "review-bound"}
INTERACTION_CANDIDATE_SOURCE_KINDS = {
    "workflow-context",
    "existing-business-data",
    "operation",
    "accepted-vocabulary",
    "user-defined",
    "review-bound",
    "not-applicable",
}

NON_OPERATION_TYPES = {
    "boundary",
    "invariant",
    "policy",
    "state-rule",
    "data-rule",
    "ownership-rule",
    "authorization-rule",
    "failure-rule",
    "test-obligation",
    "scope-decision",
}


class P2AgenticArchitectureAuthorityError(ValueError):
    """Raised when P2 architecture authority is absent, stale, or incomplete."""


def p1_agentic_product_authority_is_valid(authority: Mapping[str, Any]) -> bool:
    if not isinstance(authority, dict) or authority.get("schema_version") != "wff.p1-agentic-product-authority.v1":
        return False
    if authority.get("status") != "accepted-p1-agentic-product-authority":
        return False
    if authority.get("world_knowledge_contract") != "p1-world-knowledge-backfill-v1":
        return False
    if not isinstance(authority.get("world_knowledge_backfill"), list) or not isinstance(authority.get("product_world_decision"), dict):
        return False
    expected = str(authority.get("content_digest") or "")
    body = {key: value for key, value in authority.items() if key != "content_digest"}
    if not expected or expected != canonical_digest(body):
        return False
    interaction_contract = str(authority.get("interaction_semantics_contract") or "").strip()
    if interaction_contract and (
        interaction_contract != "product-interaction-semantics-v1"
        or not isinstance(authority.get("interaction_relevant_product_context"), Mapping)
    ):
        return False
    commitments = authority.get("commitments")
    return bool(
        authority.get("decision_digest")
        and isinstance(commitments, list)
        and commitments
        and all(isinstance(row, dict) and str(row.get("commitment_id") or "") for row in commitments)
    )


def _with_digest(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["content_digest"] = canonical_digest(result)
    return result


def _authority_paths(phase1_prd: Path) -> dict[str, Path]:
    root = phase1_prd.resolve().parent
    return {
        "authority": root / "p1-agentic-product-authority.json",
        "application_receipt": root / "p1-agentic-product-application-receipt.json",
        "decision": root / ".phase1-evidence" / "p1-agentic-product-decision.json",
        "claim_control": root / f"{phase1_prd.stem}.claim-control.json",
    }


def _validated_p1_inputs(phase1_prd: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Path]]:
    paths = _authority_paths(phase1_prd)
    authority = load_json_object(paths["authority"])
    if not p1_agentic_product_authority_is_valid(authority):
        raise P2AgenticArchitectureAuthorityError("accepted P1 Agentic product authority is missing or invalid")
    decision = load_json_object(paths["decision"])
    receipt = load_json_object(paths["application_receipt"])
    try:
        validate_application_receipt(
            receipt,
            decision=decision,
            required_output_names=(phase1_prd.name, paths["authority"].name),
        )
    except AgenticDecisionAuthorityError as exc:
        raise P2AgenticArchitectureAuthorityError(f"P1 Agentic application receipt is invalid: {exc}") from exc
    if authority.get("decision_digest") != decision.get("content_digest"):
        raise P2AgenticArchitectureAuthorityError("P1 authority and decision digest diverge")
    try:
        require_current_integrity_pair(
            decision=decision,
            authority=authority,
            label="P1 Agentic authority",
        )
    except DecisionIntegrityCompatibilityError as exc:
        raise P2AgenticArchitectureAuthorityError(str(exc)) from exc
    claim_control = load_json_object(paths["claim_control"])
    return authority, decision, receipt, claim_control, paths


def build_p2_agentic_architecture_candidate(phase1_prd: Path) -> dict[str, Any]:
    prd = phase1_prd.resolve()
    authority, decision, receipt, claim_control, paths = _validated_p1_inputs(prd)
    snapshot = build_input_snapshot(
        phase_id=PHASE_ID,
        inputs=(
            ("p1-prd", prd),
            ("p1-agentic-authority", paths["authority"]),
            ("p1-agentic-application", paths["application_receipt"]),
            ("p1-agentic-decision", paths["decision"]),
            ("p1-claim-control", paths["claim_control"]),
        ),
        context={
            "p1_authority_digest": authority["content_digest"],
            "p1_decision_digest": decision["content_digest"],
            "p1_application_digest": receipt["content_digest"],
        },
    )
    accepted_commitments = [
        dict(row)
        for row in authority.get("commitments", [])
        if isinstance(row, dict) and row.get("status") == "accepted"
    ]
    if not accepted_commitments:
        raise P2AgenticArchitectureAuthorityError("P1 authority contains no accepted portable commitments")
    prd_text = prd.read_text(encoding="utf-8")
    candidate_dependency_count = count_external_integrations(prd_text)
    feature_dispositions = [
        dict(row) for row in authority.get("feature_dispositions", []) if isinstance(row, dict)
    ]
    dependency_hints = [
        {
            "candidate_id": f"P2-DEP-CAND-{index:03d}",
            "statement": str(row.get("statement") or ""),
            "source_refs": list(row.get("source_refs", [])),
            "feature_id": str(row.get("feature_id") or ""),
            "p1_disposition": str(row.get("disposition") or ""),
            "authority": "candidate-hint-only",
        }
        for index, row in enumerate(feature_dispositions, start=1)
        if any(
            token in str(row.get("statement") or "").casefold()
            for token in ("external", "provider", "service", "adapter", "integration", "model", "speech", "vision", "ocr")
        )
    ]
    payload = {
        "schema_version": CANDIDATE_SCHEMA,
        "status": "agentic-decision-required",
        "phase_id": PHASE_ID,
        "decision_kind": DECISION_KIND,
        "input_snapshot": snapshot,
        "p1_authority": {
            "decision_id": authority["decision_id"],
            "decision_digest": authority["decision_digest"],
            "authority_digest": authority["content_digest"],
            "application_digest": receipt["content_digest"],
            "accepted_commitments": accepted_commitments,
            "feature_dispositions": feature_dispositions,
            "world_knowledge_contract": authority.get("world_knowledge_contract", ""),
            "world_knowledge_backfill": [
                dict(row) for row in authority.get("world_knowledge_backfill", []) if isinstance(row, dict)
            ],
            "product_world_decision": dict(authority.get("product_world_decision") or {}),
            "interaction_relevant_product_context": (
                deepcopy(authority.get("interaction_relevant_product_context"))
                if isinstance(authority.get("interaction_relevant_product_context"), Mapping)
                else None
            ),
            "interaction_semantics_contract": str(authority.get("interaction_semantics_contract") or ""),
            "claim_ceiling": authority.get("claim_ceiling", ""),
        },
        "candidate_context": {
            "prd_name": prd.name,
            "mechanical_external_integration_count": candidate_dependency_count,
            "dependency_hints": dependency_hints,
            "hint_authority": "non-authoritative-candidate-only",
        },
        "required_decision_surfaces": [
            "context_sufficiency",
            "service_portfolio",
            "operation_portfolio",
            "non_operation_realizations",
            "aggregate_and_writer_decisions",
            "state_invariant_policy_failure_decisions",
            "data_and_interaction_decisions",
            "product_interaction_semantics",
            "durable_persistence_identity_decisions",
            "commitment_dispositions",
            "dependency_dispositions",
            "stage_02_5_route",
            "handoff_claim_ceiling",
        ],
        "claim_ceiling": (
            "This packet enumerates accepted P1 authority and mechanical architecture hints. "
            "It is not architecture truth and cannot activate/skip Stage-02.5 or authorize P3."
        ),
    }
    return _with_digest(payload)


def candidate_is_valid(candidate: Mapping[str, Any]) -> bool:
    if candidate.get("schema_version") != CANDIDATE_SCHEMA:
        return False
    body = {key: value for key, value in candidate.items() if key != "content_digest"}
    return bool(candidate.get("content_digest") == canonical_digest(body) and isinstance(candidate.get("input_snapshot"), dict))


def build_decision_template(candidate: Mapping[str, Any], *, owner_id: str = "host-agent-required") -> dict[str, Any]:
    if not candidate_is_valid(candidate):
        raise P2AgenticArchitectureAuthorityError("P2 architecture candidate is invalid")
    commitments = candidate["p1_authority"]["accepted_commitments"]
    semantic_payload = {
        "context_sufficiency": {
            "status": "review-bound",
            "supports_architecture_claim": False,
            "rationale": "Host Agent architecture decision required.",
            "return_route": "P1-or-context-completion",
        },
        "service_portfolio": [],
        "operation_portfolio": [],
        "non_operation_realizations": [],
        "aggregate_and_writer_decisions": [],
        "state_invariant_policy_failure_decisions": [],
        "data_and_interaction_decisions": [],
        "product_interaction_semantics": [],
        "durable_persistence_identity_decisions": [],
        "commitment_dispositions": [
            {
                "commitment_id": row["commitment_id"],
                "disposition": "p2-local-repair",
                "realization_ids": [],
                "interaction_context_coverage": [
                    {
                        "context_id": str(context.get("context_id") or "").strip(),
                        "role": str(context.get("user_role_or_actor") or "").strip(),
                        "operation_ids": [],
                        "reentry_required": False,
                        "reentry_operation_ids": [],
                        "reason": "Host Agent must decide exact task-context and re-entry realization from accepted P1 semantics.",
                    }
                    for context in _p1_interaction_context_rows(candidate).values()
                    if row["commitment_id"] in {
                        str(value).strip() for value in context.get("commitment_ids", []) if str(value).strip()
                    }
                ],
                "reason": "Host Agent disposition required.",
                "owner": "P2 host Agent",
                "evidence_refs": [row["commitment_id"]],
                "minimum_rerun": "P2",
                "claim_ceiling": "No implementation handoff until exact architecture disposition exists.",
            }
            for row in commitments
        ],
        "dependency_dispositions": [],
        "stage_02_5_route": {
            "decision": "return",
            "dependency_ids": [],
            "reason": "Host Agent dependency decision required.",
            "claim_ceiling": "No silent activation or skip.",
        },
        "handoff": {
            "status": "return-required",
            "allowed_slices": [],
            "blocked_slices": [row["commitment_id"] for row in commitments],
            "minimum_rerun": "P2",
            "claim_ceiling": "Architecture decision required.",
        },
    }
    return build_decision_envelope(
        phase_id=PHASE_ID,
        decision_kind=DECISION_KIND,
        decision_id="P2-AGENTIC-DECISION-REQUIRED",
        input_snapshot=dict(candidate["input_snapshot"]),
        owner_id=owner_id,
        semantic_payload=semantic_payload,
        decision_status="agentic-decision-required",
        claim_ceiling="No accepted architecture authority exists until a host Agent decides every admitted P1 commitment and material dependency.",
        bounded_challenge=build_bounded_challenge_template(
            phase_id=PHASE_ID,
            trigger_ids=(
                "architecture-ownership",
                "contract-operation-identity",
                "dependency-compatibility",
                "cross-phase-disposition",
            ),
            owner_id=owner_id,
        ),
    )


def _rows(value: Any, *, field: str, non_empty: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise P2AgenticArchitectureAuthorityError(f"{field} must be a list")
    result = [dict(row) for row in value if isinstance(row, dict)]
    if non_empty and not result:
        raise P2AgenticArchitectureAuthorityError(f"{field} must not be empty")
    return result


def _strings(value: Any, *, field: str, non_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise P2AgenticArchitectureAuthorityError(f"{field} must be a list")
    result = [str(item).strip() for item in value if str(item).strip()]
    if non_empty and not result:
        raise P2AgenticArchitectureAuthorityError(f"{field} must not be empty")
    return result


def _fresh_interaction_semantics_required(candidate: Mapping[str, Any]) -> bool:
    p1_authority = candidate.get("p1_authority")
    if not isinstance(p1_authority, Mapping):
        return False
    return bool(
        str(p1_authority.get("interaction_semantics_contract") or "").strip()
        == "product-interaction-semantics-v1"
        and isinstance(p1_authority.get("interaction_relevant_product_context"), Mapping)
    )


def _p1_interaction_context_rows(candidate: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    p1_authority = candidate.get("p1_authority")
    if not isinstance(p1_authority, Mapping):
        return {}
    context = p1_authority.get("interaction_relevant_product_context")
    if not isinstance(context, Mapping):
        return {}
    rows = context.get("task_contexts", [])
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("context_id") or "").strip(): dict(row)
        for row in rows
        if isinstance(row, Mapping) and str(row.get("context_id") or "").strip()
    }


def _p1_interaction_context_ids(candidate: Mapping[str, Any]) -> set[str]:
    return set(_p1_interaction_context_rows(candidate))


def _validate_interaction_candidate_source(
    semantics: Mapping[str, Any],
    *,
    semantic_id: str,
    p1_commitments: set[str],
    operation_ids: set[str],
    p1_context_refs: list[str],
    p1_vocabulary_context_ids: set[str],
) -> bool:
    source = semantics.get("candidate_source")
    if not isinstance(source, Mapping):
        raise P2AgenticArchitectureAuthorityError(
            f"fresh P2 Product Interaction Semantics candidate_source must be structured: {semantic_id}"
        )
    status = str(source.get("status") or "").strip()
    source_kind = str(source.get("source_kind") or "").strip()
    if status not in INTERACTION_CANDIDATE_SOURCE_STATUSES:
        raise P2AgenticArchitectureAuthorityError(
            f"unsupported Product Interaction Semantics candidate-source status: {semantic_id}:{status or 'missing'}"
        )
    if source_kind not in INTERACTION_CANDIDATE_SOURCE_KINDS:
        raise P2AgenticArchitectureAuthorityError(
            f"unsupported Product Interaction Semantics candidate-source kind: {semantic_id}:{source_kind or 'missing'}"
        )
    authority_refs = _strings(
        source.get("authority_refs", []),
        field=f"{semantic_id}.candidate_source.authority_refs",
    )
    unknown_authority_refs = sorted(set(authority_refs) - p1_commitments)
    if unknown_authority_refs:
        raise P2AgenticArchitectureAuthorityError(
            f"Product Interaction Semantics candidate source references unknown P1 authority: {semantic_id}:{','.join(unknown_authority_refs)}"
        )
    source_operation_ids = _strings(
        source.get("operation_ids", []),
        field=f"{semantic_id}.candidate_source.operation_ids",
    )
    unknown_operations = sorted(set(source_operation_ids) - operation_ids)
    if unknown_operations:
        raise P2AgenticArchitectureAuthorityError(
            f"Product Interaction Semantics candidate source references unknown operation: {semantic_id}:{','.join(unknown_operations)}"
        )
    if status == "accepted" and source_kind in {"review-bound", "not-applicable"}:
        raise P2AgenticArchitectureAuthorityError(
            f"accepted Product Interaction Semantics candidate source has non-accepted kind: {semantic_id}:{source_kind}"
        )
    if status == "accepted" and source_kind == "operation" and not source_operation_ids:
        raise P2AgenticArchitectureAuthorityError(
            f"accepted operation-backed Product Interaction Semantics candidate source requires operation_ids: {semantic_id}"
        )
    if status == "accepted" and source_kind == "accepted-vocabulary" and not (
        authority_refs or set(p1_context_refs).intersection(p1_vocabulary_context_ids)
    ):
        raise P2AgenticArchitectureAuthorityError(
            f"accepted vocabulary Product Interaction Semantics candidate source requires P1 authority or vocabulary-bearing interaction context: {semantic_id}"
        )
    if status == "accepted" and source_kind == "existing-business-data" and not (
        authority_refs or source_operation_ids or p1_context_refs
    ):
        raise P2AgenticArchitectureAuthorityError(
            f"existing-business-data Product Interaction Semantics candidate source requires accepted authority, context, or operation: {semantic_id}"
        )
    if status == "accepted" and source_kind == "workflow-context" and not (p1_context_refs or authority_refs):
        raise P2AgenticArchitectureAuthorityError(
            f"workflow-context Product Interaction Semantics candidate source requires accepted context authority: {semantic_id}"
        )
    if status == "accepted" and source_kind == "user-defined" and not (p1_context_refs or authority_refs):
        raise P2AgenticArchitectureAuthorityError(
            f"user-defined Product Interaction Semantics candidate source requires accepted P1 authority or context: {semantic_id}"
        )
    discovery_requirement = str(semantics.get("discovery_requirement") or "").strip().casefold()
    if discovery_requirement not in INTERACTION_DISCOVERY_REQUIREMENTS:
        raise P2AgenticArchitectureAuthorityError(
            f"unsupported Product Interaction Semantics discovery requirement: {semantic_id}:{discovery_requirement or 'missing'}"
        )
    discovery_required = discovery_requirement == "required"
    gaps = semantics.get("unresolved_interaction_gaps", [])
    unresolved_gaps = [str(item).strip() for item in gaps if str(item).strip()] if isinstance(gaps, list) else []
    if discovery_required and status != "accepted" and not unresolved_gaps:
        raise P2AgenticArchitectureAuthorityError(
            f"Product Interaction Semantics discovery gap must remain explicit when candidate source is unavailable: {semantic_id}"
        )
    if discovery_requirement == "review-bound" and not unresolved_gaps:
        raise P2AgenticArchitectureAuthorityError(
            f"review-bound Product Interaction Semantics discovery requirement must name an unresolved gap: {semantic_id}"
        )
    if discovery_required and status == "accepted" and source_kind == "not-applicable":
        raise P2AgenticArchitectureAuthorityError(
            f"required discovery cannot use not-applicable candidate source: {semantic_id}"
        )
    return bool(
        unresolved_gaps
        or status in {"absent", "review-bound"}
        or str(semantics.get("truth_state") or "").strip().casefold() in {"review-bound", "unresolved"}
    )


def _validate_product_interaction_semantics_rows(
    payload: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
    p1_commitments: set[str],
    operation_ids: set[str],
    request_mapping_index: Mapping[tuple[str, str], str],
    interaction_operation_index: Mapping[str, str],
    request_field_type_index: Mapping[tuple[str, str], str],
) -> bool:
    fresh_required = _fresh_interaction_semantics_required(candidate)
    raw_rows = payload.get("product_interaction_semantics")
    if raw_rows is None:
        if fresh_required:
            raise P2AgenticArchitectureAuthorityError(
                "fresh P2 decision requires Product Interaction Semantics authority"
            )
        return False
    rows = _rows(raw_rows, field="product_interaction_semantics")
    p1_context_rows = _p1_interaction_context_rows(candidate)
    p1_context_ids = set(p1_context_rows)
    p1_vocabulary_context_ids = {
        context_id
        for context_id, row in p1_context_rows.items()
        if isinstance(row.get("business_vocabulary"), list)
        and any(str(item).strip() for item in row.get("business_vocabulary", []))
    }
    seen_ids: set[str] = set()
    seen_bindings: set[tuple[str, str]] = set()
    unresolved = False
    for row in rows:
        semantic_id = str(row.get("semantic_id") or "").strip()
        if not semantic_id or semantic_id in seen_ids:
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics identity is missing or duplicated: {semantic_id or 'missing-semantic'}"
            )
        seen_ids.add(semantic_id)
        operation_id = str(row.get("operation_id") or "").strip()
        interaction_id = str(row.get("interaction_id") or "").strip()
        contract_field = str(row.get("contract_field") or "").strip()
        binding_source = str(row.get("binding_source") or "").strip()
        if operation_id not in operation_ids:
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics references unknown operation: {semantic_id}:{operation_id or 'missing-operation'}"
            )
        expected_operation_id = str(interaction_operation_index.get(interaction_id) or "")
        if expected_operation_id and operation_id != expected_operation_id:
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics operation diverges from accepted interaction binding: {semantic_id}:{operation_id}!={expected_operation_id}"
            )
        mapping_key = (interaction_id, contract_field)
        expected_source = str(request_mapping_index.get(mapping_key) or "")
        if not interaction_id or not contract_field or not expected_source:
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics does not bind an accepted interaction request field: {semantic_id}"
            )
        if mapping_key in seen_bindings:
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics duplicates interaction-field binding: {interaction_id}:{contract_field}"
            )
        seen_bindings.add(mapping_key)
        if binding_source != expected_source:
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics binding source diverges from accepted interaction mapping: {semantic_id}"
            )
        p1_context_refs = _strings(
            row.get("p1_context_refs", []),
            field=f"{semantic_id}.p1_context_refs",
        )
        unknown_context_refs = sorted(set(p1_context_refs) - p1_context_ids)
        if unknown_context_refs:
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics references unknown P1 interaction context: {semantic_id}:{','.join(unknown_context_refs)}"
            )
        semantics = row.get("semantics")
        if not isinstance(semantics, Mapping):
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics payload is missing: {semantic_id}"
            )
        try:
            validate_p2_product_interaction_semantics(semantics)
        except ProductInteractionSemanticsContractError as exc:
            raise P2AgenticArchitectureAuthorityError(str(exc)) from exc
        cardinality = str(semantics.get("cardinality") or "").strip().casefold()
        if cardinality not in INTERACTION_CARDINALITIES:
            raise P2AgenticArchitectureAuthorityError(
                f"unsupported Product Interaction Semantics cardinality: {semantic_id}:{cardinality or 'missing'}"
            )
        request_type = str(request_field_type_index.get((operation_id, contract_field)) or "").strip().casefold()
        is_collection = any(token in request_type for token in ("array", "list", "set", "[]"))
        if is_collection and cardinality not in {"many", "one-or-more", "review-bound"}:
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics cardinality flattens accepted collection field: {semantic_id}:{contract_field}"
            )
        if request_type and not is_collection and cardinality in {"many", "one-or-more"}:
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics cardinality exceeds accepted scalar field: {semantic_id}:{contract_field}"
            )
        unresolved = (
            _validate_interaction_candidate_source(
                semantics,
                semantic_id=semantic_id,
                p1_commitments=p1_commitments,
                operation_ids=operation_ids,
                p1_context_refs=p1_context_refs,
                p1_vocabulary_context_ids=p1_vocabulary_context_ids,
            )
            or unresolved
        )
    if fresh_required:
        expected_bindings = set(request_mapping_index)
        if seen_bindings != expected_bindings:
            missing = sorted(expected_bindings - seen_bindings)
            extra = sorted(seen_bindings - expected_bindings)
            detail = ", ".join(f"{interaction}:{field}" for interaction, field in (missing or extra))
            raise P2AgenticArchitectureAuthorityError(
                f"Product Interaction Semantics coverage does not match accepted request-field mappings: {detail or 'empty mismatch'}"
            )
    return unresolved


def validate_p2_agentic_architecture_decision(
    decision: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
    accepted_required: bool = True,
) -> None:
    if not candidate_is_valid(candidate):
        raise P2AgenticArchitectureAuthorityError("P2 architecture candidate is invalid")
    try:
        validate_decision_envelope(
            decision,
            expected_phase_id=PHASE_ID,
            expected_decision_kind=DECISION_KIND,
            expected_input_snapshot_digest=str(candidate["input_snapshot"]["snapshot_digest"]),
            accepted_required=accepted_required,
        )
    except AgenticDecisionAuthorityError as exc:
        raise P2AgenticArchitectureAuthorityError(str(exc)) from exc
    payload = decision.get("semantic_payload")
    if not isinstance(payload, dict):
        raise P2AgenticArchitectureAuthorityError("P2 architecture semantic payload is missing")
    final_review = decision.get("decision_integrity_contract") == "p2-omr-sqr-integrity-v1"
    if (payload.get("review_contract") == "p2-omr-sqr.v1") != final_review:
        raise P2AgenticArchitectureAuthorityError("P2 payload and final-review acceptance contracts must agree")
    if final_review:
        if "context_sufficiency" in payload:
            raise P2AgenticArchitectureAuthorityError("Final-review P2 has no duplicate sufficiency self-assessment")
        if decision["final_review"]["bindings"].get("candidate_digest") != candidate["content_digest"]:
            raise P2AgenticArchitectureAuthorityError("Final review belongs to a different P2 candidate")
    else:
        sufficiency = payload.get("context_sufficiency")
        if not isinstance(sufficiency, dict) or sufficiency.get("status") not in {"sufficient", "insufficient", "review-bound"}:
            raise P2AgenticArchitectureAuthorityError("P2 context sufficiency decision is invalid")
        if decision.get("decision_status") == "accepted" and (
            sufficiency.get("status") != "sufficient" or sufficiency.get("supports_architecture_claim") is not True
        ):
            raise P2AgenticArchitectureAuthorityError("accepted P2 decision requires sufficient architecture context for its bounded claim")

    p1_commitments = {
        str(row.get("commitment_id") or "")
        for row in candidate["p1_authority"]["accepted_commitments"]
        if isinstance(row, dict)
    }
    services = _rows(payload.get("service_portfolio"), field="service_portfolio")
    service_ids = {str(row.get("service_id") or "").strip() for row in services}
    if "" in service_ids or len(service_ids) != len(services):
        raise P2AgenticArchitectureAuthorityError("P2 service identity is missing or duplicated")

    operations = _rows(payload.get("operation_portfolio"), field="operation_portfolio")
    operation_ids: set[str] = set()
    contract_ids: set[str] = set()
    for row in operations:
        operation_id = str(row.get("operation_id") or "").strip()
        contract_id = str(row.get("contract_id") or "").strip()
        if not operation_id or operation_id in operation_ids or not contract_id:
            raise P2AgenticArchitectureAuthorityError("P2 operation/contract identity is missing or duplicated")
        operation_ids.add(operation_id)
        contract_ids.add(contract_id)
        for field in ("service_id", "statement", "owner", "claim_ceiling"):
            if not str(row.get(field) or "").strip():
                raise P2AgenticArchitectureAuthorityError(f"P2 operation misses {field}: {operation_id}")
        if str(row.get("service_id") or "").strip() not in service_ids:
            raise P2AgenticArchitectureAuthorityError(f"P2 operation references unknown service: {operation_id}")
        terminal_access = row.get("terminal_access")
        if terminal_access is not None:
            if not isinstance(terminal_access, dict):
                raise P2AgenticArchitectureAuthorityError(f"P2 terminal access must be an object: {operation_id}")
            exposure = str(terminal_access.get("exposure") or "").strip()
            if exposure not in {"terminal-direct", "system-continuation", "review-bound"}:
                raise P2AgenticArchitectureAuthorityError(f"P2 terminal access exposure is invalid: {operation_id}")
            allowed_roles = _strings(terminal_access.get("allowed_roles", []), field=f"terminal_access.allowed_roles:{operation_id}")
            visible_objects = _strings(
                terminal_access.get("visible_business_objects", []),
                field=f"terminal_access.visible_business_objects:{operation_id}",
            )
            authority_refs = _strings(
                terminal_access.get("authority_refs", []),
                field=f"terminal_access.authority_refs:{operation_id}",
            )
            if len(set(allowed_roles)) != len(allowed_roles):
                raise P2AgenticArchitectureAuthorityError(f"P2 terminal access duplicates allowed roles: {operation_id}")
            unknown_authority_refs = sorted(set(authority_refs) - p1_commitments)
            if unknown_authority_refs:
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 terminal access references unknown P1 authority: {operation_id}: {','.join(unknown_authority_refs)}"
                )
            for field in ("denied_behavior", "reason", "claim_ceiling"):
                if not str(terminal_access.get(field) or "").strip():
                    raise P2AgenticArchitectureAuthorityError(f"P2 terminal access misses {field}: {operation_id}")
            if exposure == "terminal-direct":
                if not allowed_roles:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 terminal-direct access requires at least one allowed role: {operation_id}"
                    )
                if not authority_refs:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 terminal-direct access requires accepted P1 authority refs: {operation_id}"
                    )
                if not visible_objects:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 terminal-direct access requires bounded visible business objects: {operation_id}"
                    )
            elif exposure == "system-continuation" and allowed_roles:
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 system-continuation access must not declare allowed roles: {operation_id}"
                )
            elif exposure == "review-bound" and allowed_roles:
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 review-bound terminal access must not declare allowed roles: {operation_id}"
                )

    aggregates = _rows(payload.get("aggregate_and_writer_decisions"), field="aggregate_and_writer_decisions")
    aggregate_by_id = {
        str(row.get("aggregate_id") or "").strip(): row
        for row in aggregates
        if str(row.get("aggregate_id") or "").strip()
    }
    data_decisions = _rows(payload.get("data_and_interaction_decisions"), field="data_and_interaction_decisions")
    data_by_id = {
        str(row.get("decision_id") or "").strip(): row
        for row in data_decisions
        if str(row.get("decision_id") or "").strip()
    }

    def decision_fields(row: Mapping[str, Any]) -> set[str]:
        raw_fields = row.get("fields", [])
        if not isinstance(raw_fields, list):
            return set()
        return {
            str(field.get("name") or field.get("field_name") or "").strip()
            for field in raw_fields
            if isinstance(field, dict) and str(field.get("name") or field.get("field_name") or "").strip()
        }

    def data_field_constraints(row: Mapping[str, Any]) -> dict[str, str]:
        raw_fields = row.get("fields", [])
        if not isinstance(raw_fields, list):
            return {}
        return {
            str(field.get("name") or field.get("field_name") or "").strip(): str(field.get("constraint") or field.get("constraints") or "").strip()
            for field in raw_fields
            if isinstance(field, dict) and str(field.get("name") or field.get("field_name") or "").strip()
        }

    def declared_unique_sets(rows: list[dict[str, Any]]) -> list[set[str]]:
        result: list[set[str]] = []
        for row in rows:
            raw = row.get("unique_constraints", [])
            if not isinstance(raw, list):
                continue
            for item in raw:
                if isinstance(item, list):
                    fields = {str(value).strip() for value in item if str(value).strip()}
                elif isinstance(item, str):
                    fields = {part.strip() for part in re.split(r"[+,]", item) if part.strip()}
                else:
                    fields = set()
                if fields:
                    result.append(fields)
        return result

    def operation_request_fields(operation_id: str) -> set[str]:
        result: set[str] = set()
        for row in data_decisions:
            if str(row.get("operation_id") or "").strip() != operation_id:
                continue
            raw_fields = row.get("request_fields", [])
            if isinstance(raw_fields, list):
                result.update(
                    str(field.get("name") or "").strip()
                    for field in raw_fields
                    if isinstance(field, dict) and str(field.get("name") or "").strip()
                )
        return result

    def operation_result_fields(operation_id: str) -> set[str]:
        result: set[str] = set()
        for row in data_decisions:
            if str(row.get("operation_id") or "").strip() != operation_id:
                continue
            raw_fields = row.get("result_fields", [])
            if isinstance(raw_fields, list):
                result.update(
                    str(field.get("name") or "").strip()
                    for field in raw_fields
                    if isinstance(field, dict) and str(field.get("name") or "").strip()
                )
        return result

    request_field_type_index: dict[tuple[str, str], str] = {}
    for data_row in data_decisions:
        operation_id = str(data_row.get("operation_id") or "").strip()
        raw_request_fields = data_row.get("request_fields", [])
        if isinstance(raw_request_fields, list):
            for field in raw_request_fields:
                if not isinstance(field, Mapping):
                    continue
                field_name = str(field.get("name") or "").strip()
                if field_name:
                    request_field_type_index[(operation_id, field_name)] = str(field.get("type") or "").strip()
        result_rows = data_row.get("result_fields", [])
        if not isinstance(result_rows, list):
            continue
        for field in result_rows:
            if not isinstance(field, Mapping):
                continue
            field_name = str(field.get("name") or "").strip()
            field_type = str(field.get("type") or "string").strip().casefold()
            nested_key = (
                "item_fields"
                if any(token in field_type for token in ("array", "list"))
                else "fields"
                if any(token in field_type for token in ("object", "map"))
                else ""
            )
            if not nested_key:
                continue
            nested_rows = field.get(nested_key)
            if not isinstance(nested_rows, list) or not nested_rows:
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 structured result field requires {nested_key}: {operation_id}:{field_name or 'missing-field'}"
                )
            nested_names: set[str] = set()
            for nested in nested_rows:
                if not isinstance(nested, Mapping):
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 structured result field contains invalid nested field: {operation_id}:{field_name}"
                    )
                nested_name = str(nested.get("name") or "").strip()
                nested_type = str(nested.get("type") or "").strip()
                if not nested_name or not nested_type or nested_name in nested_names:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 structured result field nested identity/type is missing or duplicated: {operation_id}:{field_name}"
                    )
                nested_names.add(nested_name)

    operation_by_id = {
        str(row.get("operation_id") or "").strip(): row
        for row in operations
        if str(row.get("operation_id") or "").strip()
    }
    interaction_binding_ids: set[str] = set()
    interaction_operation_index: dict[str, str] = {}
    request_mapping_index: dict[tuple[str, str], str] = {}
    for data_row in data_decisions:
        raw_bindings = data_row.get("interaction_bindings", [])
        if raw_bindings in (None, []):
            continue
        operation_id = str(data_row.get("operation_id") or "").strip()
        if operation_id not in operation_ids:
            raise P2AgenticArchitectureAuthorityError(
                f"P2 interaction binding parent operation is unknown: {operation_id or 'missing-operation'}"
            )
        bindings = _rows(raw_bindings, field=f"{operation_id}.interaction_bindings", non_empty=True)
        request_denominator = operation_request_fields(operation_id)
        result_denominator = operation_result_fields(operation_id)
        operation_method = str(operation_by_id[operation_id].get("method") or "POST").strip().upper()
        for binding in bindings:
            interaction_id = str(binding.get("interaction_id") or "").strip()
            if not interaction_id or interaction_id in interaction_binding_ids:
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 interaction binding identity is duplicated or missing: {interaction_id or 'missing-interaction'}"
                )
            interaction_binding_ids.add(interaction_id)
            interaction_operation_index[interaction_id] = operation_id
            mode = str(binding.get("binding_mode") or "").strip()
            if mode not in INTERACTION_BINDING_MODES:
                raise P2AgenticArchitectureAuthorityError(
                    f"unsupported P2 interaction binding mode: {interaction_id}"
                )
            if mode == "read" and operation_method not in {"GET", "HEAD"}:
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 read interaction is bound to a non-read operation: {interaction_id}:{operation_id}"
                )
            if mode in {"write", "read_write"} and operation_method in {"GET", "HEAD"}:
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 write interaction is bound to a read operation: {interaction_id}:{operation_id}"
                )
            for field_name in ("reason", "claim_ceiling"):
                if not str(binding.get(field_name) or "").strip():
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction binding misses {field_name}: {interaction_id}"
                    )

            request_mappings = _rows(
                binding.get("request_field_mapping", []),
                field=f"{interaction_id}.request_field_mapping",
            )
            mapped_request_fields: set[str] = set()
            mapped_ui_fields: set[str] = set()
            for mapping in request_mappings:
                ui_field = str(mapping.get("ui_field") or "").strip()
                contract_field = str(mapping.get("contract_field") or "").strip()
                source = str(mapping.get("source") or "").strip()
                if not ui_field or not contract_field:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction request mapping is incomplete: {interaction_id}"
                    )
                if contract_field not in request_denominator:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction mapping references undeclared request field: {interaction_id}:{contract_field}"
                    )
                if source not in INTERACTION_VALUE_SOURCES:
                    raise P2AgenticArchitectureAuthorityError(
                        f"unsupported interaction value source: {interaction_id}:{source or 'missing-source'}"
                    )
                if contract_field in mapped_request_fields or ui_field in mapped_ui_fields:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction request mapping duplicates field identity: {interaction_id}"
                    )
                mapped_request_fields.add(contract_field)
                mapped_ui_fields.add(ui_field)
                request_mapping_index[(interaction_id, contract_field)] = source
            if request_denominator and mapped_request_fields != request_denominator:
                missing_fields = sorted(request_denominator - mapped_request_fields)
                extra_fields = sorted(mapped_request_fields - request_denominator)
                detail = ", ".join(missing_fields or extra_fields)
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 interaction request mapping does not cover the accepted request denominator: {interaction_id}: {detail}"
                )

            response_mappings = _rows(
                binding.get("response_field_mapping", []),
                field=f"{interaction_id}.response_field_mapping",
                non_empty=True,
            )
            mapped_response_fields: set[str] = set()
            mapped_response_ui_fields: set[str] = set()
            for mapping in response_mappings:
                contract_field = str(mapping.get("contract_field") or "").strip()
                ui_field = str(mapping.get("ui_field") or "").strip()
                if not contract_field or not ui_field:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction response mapping is incomplete: {interaction_id}"
                    )
                if contract_field not in result_denominator:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction mapping references undeclared result field: {interaction_id}:{contract_field}"
                    )
                if contract_field in mapped_response_fields or ui_field in mapped_response_ui_fields:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction response mapping duplicates field identity: {interaction_id}"
                    )
                mapped_response_fields.add(contract_field)
                mapped_response_ui_fields.add(ui_field)

    unresolved_interaction_semantics = _validate_product_interaction_semantics_rows(
        payload,
        candidate=candidate,
        p1_commitments=p1_commitments,
        operation_ids=operation_ids,
        request_mapping_index=request_mapping_index,
        interaction_operation_index=interaction_operation_index,
        request_field_type_index=request_field_type_index,
    )

    pre_non_operations = _rows(payload.get("non_operation_realizations"), field="non_operation_realizations")
    pre_non_operation_ids = {
        str(row.get("realization_id") or "").strip()
        for row in pre_non_operations
        if str(row.get("realization_id") or "").strip()
    }
    durable_rows = _rows(
        payload.get("durable_persistence_identity_decisions"),
        field="durable_persistence_identity_decisions",
    )
    durable_by_operation: dict[str, dict[str, Any]] = {}
    durable_by_non_operation: dict[str, dict[str, Any]] = {}
    for row in durable_rows:
        operation_id = str(row.get("operation_id") or "").strip()
        non_operation_id = str(row.get("non_operation_realization_id") or "").strip()
        if bool(operation_id) == bool(non_operation_id):
            raise P2AgenticArchitectureAuthorityError(
                "P2 durable persistence identity must bind exactly one operation_id or non_operation_realization_id"
            )
        if operation_id:
            if operation_id not in operation_ids or operation_id in durable_by_operation:
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 durable persistence operation identity is unknown or duplicated: {operation_id}"
                )
        else:
            if non_operation_id not in pre_non_operation_ids or non_operation_id in durable_by_non_operation:
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 durable persistence non-operation identity is unknown or duplicated: {non_operation_id or 'missing-non-operation'}"
                )
        durable_subject_id = operation_id or non_operation_id
        mode = str(row.get("persistence_mode") or "").strip()
        command_kind = str(row.get("command_kind") or "").strip()
        idempotency_mode = str(row.get("idempotency_mode") or "").strip()
        replay_behavior = str(row.get("replay_behavior") or "").strip()
        if mode not in PERSISTENCE_MODES:
            raise P2AgenticArchitectureAuthorityError(f"unsupported P2 persistence mode: {durable_subject_id}")
        if command_kind not in PERSISTENCE_COMMAND_KINDS:
            raise P2AgenticArchitectureAuthorityError(f"unsupported P2 persistence command kind: {durable_subject_id}")
        expected_command_kinds = {
            "durable-write": {"insert", "update", "append", "upsert"},
            "read-only": {"select-one", "select-many", "select-projection"},
            "no-durable-state": {"none"},
        }[mode]
        if command_kind not in expected_command_kinds:
            raise P2AgenticArchitectureAuthorityError(
                f"P2 persistence command kind diverges from persistence mode: {durable_subject_id}"
            )
        if idempotency_mode not in IDEMPOTENCY_MODES:
            raise P2AgenticArchitectureAuthorityError(f"unsupported P2 idempotency mode: {durable_subject_id}")
        if replay_behavior not in REPLAY_BEHAVIORS:
            raise P2AgenticArchitectureAuthorityError(f"unsupported P2 replay behavior: {durable_subject_id}")
        for field in ("reason", "claim_ceiling"):
            if not str(row.get(field) or "").strip():
                raise P2AgenticArchitectureAuthorityError(f"P2 durable persistence decision misses {field}: {durable_subject_id}")

        identity_components = _strings(
            row.get("identity_components", []),
            field=f"{operation_id}.identity_components",
        )
        carrier = row.get("durable_carrier")
        if not isinstance(carrier, dict):
            raise P2AgenticArchitectureAuthorityError(f"P2 durable carrier is missing: {durable_subject_id}")
        carrier_kind = str(carrier.get("kind") or "").strip()
        carrier_id = str(carrier.get("carrier_id") or "").strip()
        if carrier_kind not in DURABLE_CARRIER_KINDS:
            raise P2AgenticArchitectureAuthorityError(f"unsupported P2 durable carrier kind: {durable_subject_id}")
        bindings = _rows(carrier.get("field_bindings", []), field=f"{operation_id}.durable_carrier.field_bindings")
        enforcement = carrier.get("enforcement")
        if not isinstance(enforcement, dict):
            raise P2AgenticArchitectureAuthorityError(f"P2 durable carrier enforcement is missing: {operation_id}")
        enforcement_mode = str(enforcement.get("mode") or "").strip()
        if enforcement_mode not in DURABLE_ENFORCEMENT_MODES:
            raise P2AgenticArchitectureAuthorityError(f"unsupported P2 durable enforcement mode: {operation_id}")
        enforcement_fields = _strings(
            enforcement.get("fields", []),
            field=f"{operation_id}.durable_carrier.enforcement.fields",
        )

        writer_service_id = str(row.get("writer_service_id") or "").strip()
        carrier_fields: set[str] = set()
        carrier_data_rows: list[dict[str, Any]] = []
        if carrier_kind == "aggregate":
            aggregate = aggregate_by_id.get(carrier_id)
            if aggregate is None:
                raise P2AgenticArchitectureAuthorityError(f"P2 durable carrier references unknown aggregate: {durable_subject_id}")
            carrier_data_rows = [
                item for item in data_decisions
                if str(item.get("aggregate_id") or "").strip() == carrier_id
            ]
            carrier_fields = set().union(*(decision_fields(item) for item in carrier_data_rows)) if carrier_data_rows else set()
            accepted_writer = str(aggregate.get("writer_service_id") or aggregate.get("writer") or "").strip()
            if accepted_writer and writer_service_id != accepted_writer:
                raise P2AgenticArchitectureAuthorityError(f"P2 durable writer diverges from aggregate writer: {durable_subject_id}")
        elif carrier_kind == "dedicated-record":
            carrier_decision = data_by_id.get(carrier_id)
            if carrier_decision is None or not str(carrier_decision.get("table_name") or "").strip():
                raise P2AgenticArchitectureAuthorityError(f"P2 dedicated durable carrier is not declared as a data record: {durable_subject_id}")
            carrier_data_rows = [carrier_decision]
            carrier_fields = decision_fields(carrier_decision)
        else:
            if carrier_id or bindings or enforcement_mode != "not-applicable" or enforcement_fields:
                raise P2AgenticArchitectureAuthorityError(f"not-applicable durable carrier cannot bind fields or enforcement: {durable_subject_id}")

        if mode == "durable-write":
            if not writer_service_id or writer_service_id not in service_ids:
                raise P2AgenticArchitectureAuthorityError(f"P2 durable write requires a known writer service: {durable_subject_id}")
            if carrier_kind == "not-applicable" or not carrier_fields:
                raise P2AgenticArchitectureAuthorityError(f"P2 durable write requires a concrete durable carrier: {durable_subject_id}")
            if enforcement_mode == "not-applicable":
                raise P2AgenticArchitectureAuthorityError(f"P2 durable write requires an explicit persistence enforcement mode: {durable_subject_id}")
        else:
            expected_behavior = "read-only" if mode == "read-only" else "no-durable-state"
            if carrier_kind != "not-applicable" or writer_service_id or replay_behavior != expected_behavior:
                raise P2AgenticArchitectureAuthorityError(f"non-write P2 persistence subject has an invalid durable persistence posture: {durable_subject_id}")

        if enforcement_fields and not set(enforcement_fields).issubset(carrier_fields):
            unknown = sorted(set(enforcement_fields) - carrier_fields)
            raise P2AgenticArchitectureAuthorityError(
                f"P2 persistence enforcement references undeclared carrier fields for {durable_subject_id}: " + ", ".join(unknown)
            )
        if enforcement_mode == "primary-key":
            constraints = {}
            for item in carrier_data_rows:
                constraints.update(data_field_constraints(item))
            if not enforcement_fields or any("pk" not in constraints.get(field, "").casefold() for field in enforcement_fields):
                raise P2AgenticArchitectureAuthorityError(f"P2 primary-key replay enforcement is not backed by declared PK fields: {durable_subject_id}")
        if enforcement_mode == "unique-constraint":
            if not enforcement_fields or set(enforcement_fields) not in declared_unique_sets(carrier_data_rows):
                raise P2AgenticArchitectureAuthorityError(f"P2 unique replay enforcement is not backed by an exact declared unique constraint: {durable_subject_id}")

        if idempotency_mode == "replay-safe":
            if mode != "durable-write" or not identity_components:
                raise P2AgenticArchitectureAuthorityError(f"replay-safe P2 persistence subject requires durable-write identity components: {durable_subject_id}")
            binding_by_component = {
                str(binding.get("identity_component") or "").strip(): str(binding.get("carrier_field") or "").strip()
                for binding in bindings
                if str(binding.get("identity_component") or "").strip()
            }
            if set(identity_components) != set(binding_by_component):
                raise P2AgenticArchitectureAuthorityError(f"P2 replay identity is not fully bound to durable fields: {durable_subject_id}")
            unknown_fields = sorted(set(binding_by_component.values()) - carrier_fields)
            if unknown_fields:
                raise P2AgenticArchitectureAuthorityError(
                    f"P2 replay identity binds undeclared durable fields for {durable_subject_id}: " + ", ".join(unknown_fields)
                )
            request_fields = operation_request_fields(operation_id) if operation_id else set()
            for component in identity_components:
                prefix, _, field_name = component.partition(".")
                if prefix in {"request", "path", "query"} and field_name not in request_fields:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 replay identity references undeclared request field for {durable_subject_id}: {component}"
                    )
        elif identity_components or bindings:
            raise P2AgenticArchitectureAuthorityError(f"non-replay-safe P2 persistence subject cannot claim replay identity bindings: {durable_subject_id}")
        if operation_id:
            durable_by_operation[operation_id] = row
        else:
            durable_by_non_operation[non_operation_id] = row

    missing_durable = sorted(operation_ids - set(durable_by_operation))
    if missing_durable:
        raise P2AgenticArchitectureAuthorityError(
            "P2 misses durable persistence identity decisions: " + ", ".join(missing_durable)
        )

    non_operations = _rows(payload.get("non_operation_realizations"), field="non_operation_realizations")
    non_operation_ids: set[str] = set()
    for row in non_operations:
        realization_id = str(row.get("realization_id") or "").strip()
        if not realization_id or realization_id in non_operation_ids:
            raise P2AgenticArchitectureAuthorityError("P2 non-operation identity is missing or duplicated")
        if row.get("realization_type") not in NON_OPERATION_TYPES:
            raise P2AgenticArchitectureAuthorityError(f"unsupported P2 non-operation type: {realization_id}")
        non_operation_ids.add(realization_id)

    p1_context_rows = _p1_interaction_context_rows(candidate)
    contexts_by_commitment: dict[str, dict[str, dict[str, Any]]] = {}
    for context_id, context_row in p1_context_rows.items():
        for context_commitment_id in _strings(
            context_row.get("commitment_ids", []),
            field=f"{context_id}.commitment_ids",
        ):
            contexts_by_commitment.setdefault(context_commitment_id, {})[context_id] = context_row

    dispositions = _rows(payload.get("commitment_dispositions"), field="commitment_dispositions", non_empty=True)
    disposition_by_commitment: dict[str, dict[str, Any]] = {}
    for row in dispositions:
        commitment_id = str(row.get("commitment_id") or "").strip()
        if commitment_id not in p1_commitments or commitment_id in disposition_by_commitment:
            raise P2AgenticArchitectureAuthorityError(f"P2 commitment disposition identity is unknown or duplicated: {commitment_id}")
        disposition = str(row.get("disposition") or "")
        if disposition not in DISPOSITIONS:
            raise P2AgenticArchitectureAuthorityError(f"unsupported P2 commitment disposition: {commitment_id}")
        ids = _strings(row.get("realization_ids", []), field=f"{commitment_id}.realization_ids")
        if disposition == "exact-operation" and (len(ids) != 1 or ids[0] not in operation_ids):
            raise P2AgenticArchitectureAuthorityError(f"exact-operation disposition is invalid: {commitment_id}")
        if disposition == "exact-operation-set" and (not ids or not set(ids).issubset(operation_ids)):
            raise P2AgenticArchitectureAuthorityError(f"exact-operation-set disposition is invalid: {commitment_id}")
        relevant_contexts = contexts_by_commitment.get(commitment_id, {})
        coverage_rows = _rows(
            row.get("interaction_context_coverage", []),
            field=f"{commitment_id}.interaction_context_coverage",
        )
        if disposition == "exact-operation-set" and len(relevant_contexts) > 1:
            if not coverage_rows:
                raise P2AgenticArchitectureAuthorityError(
                    f"multi-context exact-operation-set requires interaction context coverage: {commitment_id}"
                )
            coverage_by_context: dict[str, dict[str, Any]] = {}
            for coverage in coverage_rows:
                context_id = str(coverage.get("context_id") or "").strip()
                if context_id not in relevant_contexts or context_id in coverage_by_context:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction context coverage identity is unknown or duplicated: {commitment_id}:{context_id or 'missing-context'}"
                    )
                context_row = relevant_contexts[context_id]
                role = str(coverage.get("role") or "").strip()
                expected_role = str(context_row.get("user_role_or_actor") or "").strip()
                if not role or role != expected_role:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction context coverage role mismatch: {commitment_id}:{context_id}"
                    )
                context_operation_ids = _strings(
                    coverage.get("operation_ids", []),
                    field=f"{commitment_id}.{context_id}.operation_ids",
                    non_empty=True,
                )
                if not set(context_operation_ids).issubset(set(ids)):
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction context coverage escapes disposition operations: {commitment_id}:{context_id}"
                    )
                for context_operation_id in context_operation_ids:
                    operation_row = operation_by_id[context_operation_id]
                    terminal_access = operation_row.get("terminal_access")
                    allowed_roles = (
                        _strings(
                            terminal_access.get("allowed_roles", []),
                            field=f"terminal_access.allowed_roles:{context_operation_id}",
                        )
                        if isinstance(terminal_access, Mapping)
                        else []
                    )
                    if role not in allowed_roles:
                        raise P2AgenticArchitectureAuthorityError(
                            f"P2 interaction context operation is not visible to its accepted role: {commitment_id}:{context_id}:{context_operation_id}"
                        )
                reentry_required = coverage.get("reentry_required")
                if not isinstance(reentry_required, bool):
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction context coverage must decide reentry_required: {commitment_id}:{context_id}"
                    )
                reentry_operation_ids = _strings(
                    coverage.get("reentry_operation_ids", []),
                    field=f"{commitment_id}.{context_id}.reentry_operation_ids",
                )
                if reentry_required:
                    if not reentry_operation_ids or not set(reentry_operation_ids).issubset(set(context_operation_ids)):
                        raise P2AgenticArchitectureAuthorityError(
                            f"P2 re-entry coverage requires bounded context operations: {commitment_id}:{context_id}"
                        )
                    for reentry_operation_id in reentry_operation_ids:
                        operation_row = operation_by_id[reentry_operation_id]
                        method = str(operation_row.get("method") or "").strip().upper()
                        if method not in {"GET", "HEAD"}:
                            raise P2AgenticArchitectureAuthorityError(
                                f"P2 re-entry coverage must use a read operation: {commitment_id}:{context_id}:{reentry_operation_id}"
                            )
                        terminal_access = operation_row.get("terminal_access")
                        authority_refs = (
                            _strings(
                                terminal_access.get("authority_refs", []),
                                field=f"terminal_access.authority_refs:{reentry_operation_id}",
                            )
                            if isinstance(terminal_access, Mapping)
                            else []
                        )
                        if commitment_id not in authority_refs:
                            raise P2AgenticArchitectureAuthorityError(
                                f"P2 re-entry operation lacks exact commitment authority: {commitment_id}:{context_id}:{reentry_operation_id}"
                            )
                elif reentry_operation_ids:
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 non-reentry context cannot claim reentry operations: {commitment_id}:{context_id}"
                    )
                if not str(coverage.get("reason") or "").strip():
                    raise P2AgenticArchitectureAuthorityError(
                        f"P2 interaction context coverage misses reason: {commitment_id}:{context_id}"
                    )
                coverage_by_context[context_id] = coverage
            if set(coverage_by_context) != set(relevant_contexts):
                missing_contexts = sorted(set(relevant_contexts) - set(coverage_by_context))
                raise P2AgenticArchitectureAuthorityError(
                    "P2 multi-context exact-operation-set misses task-context coverage: " + ", ".join(missing_contexts)
                )
        if disposition == "non-operation-realization" and (not ids or not set(ids).issubset(non_operation_ids)):
            raise P2AgenticArchitectureAuthorityError(f"non-operation disposition is invalid: {commitment_id}")
        if disposition in {"return-p1", "p2-local-repair", "deferred", "excluded", "review-bound"} and ids:
            raise P2AgenticArchitectureAuthorityError(f"non-realized disposition cannot claim realization ids: {commitment_id}")
        for field in ("reason", "owner", "claim_ceiling"):
            if not str(row.get(field) or "").strip():
                raise P2AgenticArchitectureAuthorityError(f"P2 disposition misses {field}: {commitment_id}")
        _strings(row.get("evidence_refs", []), field=f"{commitment_id}.evidence_refs", non_empty=True)
        disposition_by_commitment[commitment_id] = row
    missing = sorted(p1_commitments - set(disposition_by_commitment))
    if missing:
        raise P2AgenticArchitectureAuthorityError("P2 misses exact dispositions: " + ", ".join(missing))

    dependencies = _rows(payload.get("dependency_dispositions"), field="dependency_dispositions")
    dependency_ids: set[str] = set()
    for row in dependencies:
        dependency_id = str(row.get("dependency_id") or "").strip()
        if not dependency_id or dependency_id in dependency_ids:
            raise P2AgenticArchitectureAuthorityError("P2 dependency identity is missing or duplicated")
        dependency_ids.add(dependency_id)
        if row.get("disposition") not in DEPENDENCY_DISPOSITIONS:
            raise P2AgenticArchitectureAuthorityError(f"unsupported dependency disposition: {dependency_id}")
        _strings(row.get("commitment_ids", []), field=f"{dependency_id}.commitment_ids", non_empty=True)
        if not set(row["commitment_ids"]).issubset(p1_commitments):
            raise P2AgenticArchitectureAuthorityError(f"dependency references unknown P1 commitment: {dependency_id}")
        for field in ("statement", "reason", "owner", "claim_ceiling"):
            if not str(row.get(field) or "").strip():
                raise P2AgenticArchitectureAuthorityError(f"P2 dependency misses {field}: {dependency_id}")

    route = payload.get("stage_02_5_route")
    if not isinstance(route, dict) or route.get("decision") not in DEPENDENCY_DISPOSITIONS:
        raise P2AgenticArchitectureAuthorityError("P2 Stage-02.5 route decision is invalid")
    route_ids = _strings(route.get("dependency_ids", []), field="stage_02_5_route.dependency_ids")
    if not set(route_ids).issubset(dependency_ids):
        raise P2AgenticArchitectureAuthorityError("P2 Stage-02.5 route references unknown dependencies")
    if route.get("decision") == "activate" and not route_ids:
        raise P2AgenticArchitectureAuthorityError("P2 Stage-02.5 activation requires dependency ids")
    for field in ("reason", "claim_ceiling"):
        if not str(route.get(field) or "").strip():
            raise P2AgenticArchitectureAuthorityError(f"P2 Stage-02.5 route misses {field}")

    handoff = payload.get("handoff")
    if not isinstance(handoff, dict) or handoff.get("status") not in {"ready", "bounded", "return-required"}:
        raise P2AgenticArchitectureAuthorityError("P2 handoff status is invalid")
    blockers = [
        row for row in dispositions if row.get("disposition") in {"return-p1", "p2-local-repair"}
    ]
    if blockers and handoff.get("status") != "return-required":
        raise P2AgenticArchitectureAuthorityError("P2 return/local-repair dispositions require return-required handoff")
    if route.get("decision") == "return" and handoff.get("status") != "return-required":
        raise P2AgenticArchitectureAuthorityError("P2 dependency return requires return-required handoff")
    if handoff.get("status") == "ready" and any(
        row.get("disposition") in {"deferred", "review-bound"} for row in dispositions
    ):
        raise P2AgenticArchitectureAuthorityError("P2 ready handoff cannot hide deferred/review-bound commitment dispositions")
    if handoff.get("status") == "ready" and unresolved_interaction_semantics:
        raise P2AgenticArchitectureAuthorityError(
            "P2 ready handoff cannot hide unresolved Product Interaction Semantics"
        )
    if final_review:
        return
    try:
        validate_p2_decision_challenge_binding(
            decision=decision,
            candidate=candidate,
            required_trigger_ids=(
                "architecture-ownership",
                "contract-operation-identity",
                "dependency-compatibility",
                "cross-phase-disposition",
            ),
        )
    except BoundedChallengeBindingError as exc:
        raise P2AgenticArchitectureAuthorityError(str(exc)) from exc


def build_p2_agentic_architecture_authority(
    candidate: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    validate_p2_agentic_architecture_decision(decision, candidate=candidate)
    semantic = deepcopy(decision["semantic_payload"])
    payload = {
        "schema_version": AUTHORITY_SCHEMA,
        "status": "accepted-p2-agentic-architecture-authority",
        "phase_id": PHASE_ID,
        "decision_id": decision["decision_id"],
        "decision_digest": decision["content_digest"],
        "input_snapshot_digest": decision["input_snapshot_digest"],
        "p1_authority": candidate["p1_authority"],
        **semantic,
        "claim_ceiling": decision.get("claim_ceiling", ""),
        "decision_integrity_contract": str(decision.get("decision_integrity_contract") or ""),
        "challenge_binding_digest": str((decision.get("challenge_binding") or {}).get("content_digest") or ""),
        **({"final_review_digest": decision["final_review"]["content_digest"]} if decision.get("final_review")
           else {"bounded_challenge": challenge_summary(decision["bounded_challenge"])}),
    }
    if _fresh_interaction_semantics_required(candidate):
        payload["interaction_semantics_contract"] = "product-interaction-semantics-v1"
    return _with_digest(payload)


def p2_agentic_architecture_authority_is_valid(authority: Mapping[str, Any]) -> bool:
    if authority.get("schema_version") != AUTHORITY_SCHEMA or authority.get("status") != "accepted-p2-agentic-architecture-authority":
        return False
    body = {key: value for key, value in authority.items() if key != "content_digest"}
    if authority.get("content_digest") != canonical_digest(body) or not authority.get("decision_digest"):
        return False
    interaction_contract = str(authority.get("interaction_semantics_contract") or "").strip()
    if interaction_contract and (
        interaction_contract != "product-interaction-semantics-v1"
        or not isinstance(authority.get("product_interaction_semantics"), list)
    ):
        return False
    return True


def build_disposition_ledger(authority: Mapping[str, Any]) -> dict[str, Any]:
    if not p2_agentic_architecture_authority_is_valid(authority):
        raise P2AgenticArchitectureAuthorityError("P2 architecture authority is invalid")
    rows = [dict(row) for row in authority.get("commitment_dispositions", []) if isinstance(row, dict)]
    counts = {name: sum(1 for row in rows if row.get("disposition") == name) for name in sorted(DISPOSITIONS)}
    return _with_digest(
        {
            "schema_version": DISPOSITION_SCHEMA,
            "status": "p1-commitment-dispositions-complete",
            "decision_id": authority["decision_id"],
            "decision_digest": authority["decision_digest"],
            "p1_authority_digest": authority["p1_authority"]["authority_digest"],
            "rows": rows,
            "counts": counts,
            "operation_portfolio": authority.get("operation_portfolio", []),
            "non_operation_realizations": authority.get("non_operation_realizations", []),
            "handoff": authority.get("handoff", {}),
            "claim_ceiling": authority.get("claim_ceiling", ""),
        }
    )


def build_dependency_routing_receipt(authority: Mapping[str, Any]) -> dict[str, Any]:
    if not p2_agentic_architecture_authority_is_valid(authority):
        raise P2AgenticArchitectureAuthorityError("P2 architecture authority is invalid")
    return _with_digest(
        {
            "schema_version": DEPENDENCY_SCHEMA,
            "status": "dependency-routing-decision-recorded",
            "decision_id": authority["decision_id"],
            "decision_digest": authority["decision_digest"],
            "dependencies": authority.get("dependency_dispositions", []),
            "stage_02_5_route": authority.get("stage_02_5_route", {}),
            "claim_ceiling": authority.get("claim_ceiling", ""),
            "truth_boundary": "Agentic architecture decision; vocabulary matches are candidate hints only.",
        }
    )


def architecture_authority_markdown(authority: Mapping[str, Any], *, surface: str) -> str:
    lines = [
        "",
        "## Snapshot-Bound Agentic Architecture Authority",
        "",
        f"- surface: `{surface}`",
        f"- decision_id: `{authority.get('decision_id', '')}`",
        f"- decision_digest: `{authority.get('decision_digest', '')}`",
        f"- authority_digest: `{authority.get('content_digest', '')}`",
        f"- p1_authority_digest: `{authority.get('p1_authority', {}).get('authority_digest', '')}`",
        f"- handoff_status: `{authority.get('handoff', {}).get('status', '')}`",
        f"- claim_ceiling: {authority.get('claim_ceiling', '')}",
        "",
        "### Exact P1 Commitment Dispositions",
        "",
        "| Commitment | Disposition | Realization IDs | Owner | Reason | Minimum Rerun | Ceiling |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in authority.get("commitment_dispositions", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            "| {cid} | `{disp}` | {ids} | {owner} | {reason} | `{rerun}` | {ceiling} |".format(
                cid=str(row.get("commitment_id") or ""),
                disp=str(row.get("disposition") or ""),
                ids=", ".join(f"`{item}`" for item in row.get("realization_ids", [])) or "-",
                owner=str(row.get("owner") or "").replace("|", "\\|"),
                reason=str(row.get("reason") or "").replace("|", "\\|"),
                rerun=str(row.get("minimum_rerun") or ""),
                ceiling=str(row.get("claim_ceiling") or "").replace("|", "\\|"),
            )
        )
    interaction_rows = authority.get("product_interaction_semantics", [])
    if isinstance(interaction_rows, list):
        lines.extend(
            [
                "",
                "### Product Interaction Semantics",
                "",
                "| Semantic ID | Interaction / Field | Binding Source | Meaning | Cardinality | Candidate Source | Discovery | Context / Default | Frequency | Free Form | Truth State | Gaps |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for row in interaction_rows:
            if not isinstance(row, Mapping):
                continue
            semantics = row.get("semantics") if isinstance(row.get("semantics"), Mapping) else {}
            candidate_source = semantics.get("candidate_source") if isinstance(semantics.get("candidate_source"), Mapping) else {}
            candidate_label = "/".join(
                part
                for part in (
                    str(candidate_source.get("status") or "").strip(),
                    str(candidate_source.get("source_kind") or "").strip(),
                )
                if part
            ) or "-"
            lines.append(
                "| {semantic_id} | `{interaction_id}` / `{field}` | `{binding_source}` | {meaning} | {cardinality} | {candidate} | {discovery} | {context}; {default} | {frequency} | `{free_form}` | `{truth_state}` | {gaps} |".format(
                    semantic_id=str(row.get("semantic_id") or ""),
                    interaction_id=str(row.get("interaction_id") or ""),
                    field=str(row.get("contract_field") or ""),
                    binding_source=str(row.get("binding_source") or ""),
                    meaning=str(semantics.get("user_meaning") or "").replace("|", "\\|"),
                    cardinality=str(semantics.get("cardinality") or "").replace("|", "\\|"),
                    candidate=candidate_label.replace("|", "\\|"),
                    discovery=str(semantics.get("discovery_requirement") or "").replace("|", "\\|"),
                    context=str(semantics.get("context_carryover") or "").replace("|", "\\|"),
                    default=str(semantics.get("default_or_recent_semantics") or "").replace("|", "\\|"),
                    frequency=str(semantics.get("usage_frequency") or "").replace("|", "\\|"),
                    free_form=str(bool(semantics.get("free_form_allowed"))).lower(),
                    truth_state=str(semantics.get("truth_state") or ""),
                    gaps=", ".join(str(item).replace("|", "\\|") for item in semantics.get("unresolved_interaction_gaps", []) if str(item).strip()) or "-",
                )
            )
    lines.extend(
        [
            "",
            "### Dependency and Optional-Lane Decision",
            "",
            f"- stage_02_5_route: `{authority.get('stage_02_5_route', {}).get('decision', '')}`",
            f"- dependency_ids: {', '.join(f'`{item}`' for item in authority.get('stage_02_5_route', {}).get('dependency_ids', [])) or '-'}",
            f"- route_reason: {authority.get('stage_02_5_route', {}).get('reason', '')}",
            "",
            "> Generated service/operation names, Trace-id occurrence, lifecycle rows, and vocabulary hints are not architecture disposition evidence. The accepted decision above is the authority.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or validate P2 snapshot-bound Agentic architecture authority")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--phase1-prd", required=True)
    prepare.add_argument("--candidate-output", required=True)
    prepare.add_argument("--decision-template-output")
    validate = sub.add_parser("validate")
    validate.add_argument("--phase1-prd", required=True)
    validate.add_argument("--decision", required=True)
    validate.add_argument("--authority-output")
    args = parser.parse_args(argv)
    candidate = build_p2_agentic_architecture_candidate(Path(args.phase1_prd))
    if args.command == "prepare":
        write_json_atomic(Path(args.candidate_output).resolve(), candidate)
        if args.decision_template_output:
            write_json_atomic(Path(args.decision_template_output).resolve(), build_decision_template(candidate))
        print(json.dumps({"status": "agentic-decision-required", "candidate_digest": candidate["content_digest"]}))
        return 0
    decision = load_json_object(Path(args.decision).resolve())
    validate_p2_agentic_architecture_decision(decision, candidate=candidate)
    authority = build_p2_agentic_architecture_authority(candidate, decision)
    if args.authority_output:
        write_json_atomic(Path(args.authority_output).resolve(), authority)
    print(json.dumps({"status": "accepted", "authority_digest": authority["content_digest"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
