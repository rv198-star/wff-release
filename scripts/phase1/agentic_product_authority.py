#!/usr/bin/env python3
"""Snapshot-bound P1 Agentic product/world authority and canonical application."""

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
    validate_decision_envelope,
    write_json_atomic,
)
from common.bounded_agentic_challenge import (
    build_bounded_challenge_template,
    challenge_summary,
)
from common.bounded_agentic_challenge_binding import BoundedChallengeBindingError
from phase1.bounded_challenge_binding import validate_p1_decision_challenge_binding
from phase1.phase1_generation_kernel import source_fact_text
from phase1.phase1_product_source_direct_driver import build_product_source_direct_driver


CANDIDATE_SCHEMA = "wff.p1-agentic-product-candidate.v1"
AUTHORITY_SCHEMA = "wff.p1-agentic-product-authority.v1"
WORLD_KNOWLEDGE_CONTRACT = "p1-world-knowledge-backfill-v1"
DECISION_KIND = "p1-product-world-and-commitment-authority"
PHASE_ID = "P1"
FEATURE_DISPOSITIONS = {
    "first-wave-commitment",
    "later-slice",
    "deferred-seam",
    "explicit-exclusion",
    "unresolved-review-bound",
    "context-completion",
}
TRUTH_STATES = {
    "source-established",
    "agentic-world-knowledge",
    "agentic-candidate",
    "agentic-hypothesis",
    "owner-confirmed",
    "unresolved",
    "review-bound",
}
WORLD_BACKFILL_STATUSES = {"accepted", "review-bound", "deferred", "rejected"}
WORLD_BACKFILL_COMPATIBILITY = {"consistent", "uncertain", "conflicts"}
WORLD_TOPOLOGY_MODES = {"ordered-flow", "independent-outcomes", "mixed", "review-bound"}
WORLD_DECISION_BASES = {"source-established", "agentic-world-knowledge", "mixed", "review-bound"}
WORLD_OWNERSHIP_POSTURES = {"source-defined", "agentic-world-knowledge", "mixed", "review-bound"}
OWNERSHIP_ASSIGNMENT_BASES = {"source-established", "agentic-world-knowledge", "mixed"}
WORLD_OBJECT_BASES = {"source-established", "agentic-world-knowledge", "mixed"}
COMMITMENT_KINDS = {
    "workflow_step",
    "acceptance_criterion",
    "epic",
    "requirement",
    "use_case",
    "user_story",
    "policy",
    "constraint",
}
COMMITMENT_ID_RE = re.compile(r"^(?:P1-(?:AC|EP|REQ|UC|US|POL|CON)-[A-Za-z0-9_.:-]+|FLOW-[A-Za-z0-9_.:-]+)$")


class P1AgenticProductAuthorityError(ValueError):
    """Raised when P1 Agentic product authority is absent, stale, or unsafe."""


def _with_content_digest(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["content_digest"] = canonical_digest(result)
    return result


def _normalize_line(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _source_evidence(source_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    heading = ""
    for number, raw in enumerate(source_text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            continue
        text = _normalize_line(re.sub(r"^(?:[-*]|\d+[.)])\s+", "", stripped))
        if not text or re.fullmatch(r"\|?\s*:?-{3,}.*", text):
            continue
        rows.append(
            {
                "evidence_ref": f"SRC-L{number:04d}",
                "line": number,
                "section": heading,
                "text": text,
                "sha256": canonical_digest(text),
                "truth_state": "source-established",
            }
        )
    return rows


def _match_source_refs(excerpt: str, evidence: list[dict[str, Any]]) -> list[str]:
    needle = _normalize_line(excerpt).casefold()
    if not needle:
        return []
    exact = [row["evidence_ref"] for row in evidence if _normalize_line(str(row["text"])).casefold() == needle]
    if exact:
        return exact[:3]
    contained = [
        row["evidence_ref"]
        for row in evidence
        if needle in _normalize_line(str(row["text"])).casefold()
        or _normalize_line(str(row["text"])).casefold() in needle
    ]
    return contained[:3]


def build_p1_agentic_product_candidate(source_path: Path) -> dict[str, Any]:
    source = source_path.resolve()
    source_text = source.read_text(encoding="utf-8")
    facts = source_fact_text(source_text)
    snapshot = build_input_snapshot(
        phase_id=PHASE_ID,
        inputs=(("admitted-source", source),),
        context={"source_fact_sha256": canonical_digest(facts)},
    )
    evidence = _source_evidence(facts)
    mechanical_driver = build_product_source_direct_driver(source_text)
    spine = mechanical_driver.get("semantic_authoring_spine")
    semantic_units = spine.get("semantic_units", []) if isinstance(spine, dict) else []
    feature_hints: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for index, raw in enumerate(semantic_units if isinstance(semantic_units, list) else [], start=1):
        if not isinstance(raw, dict):
            continue
        statement = str(raw.get("source_excerpt") or "").strip()
        source_refs = _match_source_refs(statement, evidence)
        key = (statement.casefold(), tuple(source_refs))
        if not statement or key in seen:
            continue
        seen.add(key)
        feature_hints.append(
            {
                "candidate_id": f"CAND-FTR-{index:03d}",
                "statement": statement,
                "source_refs": source_refs,
                "candidate_semantic_type": str(raw.get("semantic_type") or "unclassified"),
                "source_truth_state": "source-established" if source_refs else "unresolved",
                "candidate_interpretation_state": "agentic-candidate",
                "authority": "candidate-hint-only",
            }
        )
    payload = {
        "schema_version": CANDIDATE_SCHEMA,
        "status": "agentic-decision-required",
        "phase_id": PHASE_ID,
        "decision_kind": DECISION_KIND,
        "input_snapshot": snapshot,
        "source_evidence": evidence,
        "candidate_feature_hints": feature_hints,
        "mechanical_candidate_driver": mechanical_driver,
        "required_decision_surfaces": [
            "context_sufficiency",
            "world_alignment",
            "material_feature_review",
            "feature_dispositions",
            "commitments",
            "product_judgment",
        ],
        "truth_boundary": {
            "source_evidence": "source-established",
            "mechanical_interpretation": "agentic-candidate-only",
            "owner_confirmation": "absent-unless-explicitly-evidenced",
        },
        "claim_ceiling": (
            "This packet admits source evidence and prepares candidate interpretations. "
            "It is not an accepted product/world decision and cannot make P1 downstream-start-safe."
        ),
    }
    return _with_content_digest(payload)


def candidate_is_valid(candidate: Mapping[str, Any]) -> bool:
    if candidate.get("schema_version") != CANDIDATE_SCHEMA:
        return False
    body = {key: value for key, value in candidate.items() if key != "content_digest"}
    if candidate.get("content_digest") != canonical_digest(body):
        return False
    snapshot = candidate.get("input_snapshot")
    return bool(isinstance(snapshot, dict) and snapshot.get("snapshot_digest"))


def build_decision_template(candidate: Mapping[str, Any], *, owner_id: str = "host-agent-required") -> dict[str, Any]:
    if not candidate_is_valid(candidate):
        raise P1AgenticProductAuthorityError("P1 Agentic candidate is invalid")
    semantic_payload = {
        "context_sufficiency": {
            "status": "review-bound",
            "supports_downstream_claim": False,
            "rationale": "Host Agent decision required.",
            "missing_facts": [],
            "route": "context-completion",
        },
        "world_alignment": {
            "source_established_world": [],
            "candidate_worlds": [],
            "world_knowledge_backfill": [],
            "product_world_decision": {
                "summary": "",
                "accepted_backfill_refs": [],
                "review_bound_backfill_refs": [],
                "topology": {
                    "mode": "review-bound",
                    "statement": "",
                    "basis": "review-bound",
                    "source_refs": [],
                    "backfill_refs": [],
                },
                "ownership": {
                    "posture": "review-bound",
                    "statement": "",
                    "source_refs": [],
                    "backfill_refs": [],
                },
            },
            "accepted_world": {
                "model": "",
                "truth_state": "review-bound",
                "source_refs": [],
                "rationale": "",
            },
        },
        "material_feature_review": {
            "status": "incomplete",
            "reviewed_candidate_ids": [],
            "rationale": "Host Agent must identify material features without treating candidate hints as truth.",
        },
        "feature_dispositions": [],
        "commitments": [],
        "product_judgment": {
            "primary_user_or_buyer": "",
            "product_goal": "",
            "status_quo_to_beat": "",
            "why_this_not_that": "",
            "continuation_owner": "",
            "proof_that_changes_decision": "",
            "mvp_wedge": "",
            "acceptance_should_prove": "",
        },
    }
    return build_decision_envelope(
        phase_id=PHASE_ID,
        decision_kind=DECISION_KIND,
        decision_id="P1-AGENTIC-DECISION-REQUIRED",
        input_snapshot=dict(candidate["input_snapshot"]),
        owner_id=owner_id,
        semantic_payload=semantic_payload,
        decision_status="agentic-decision-required",
        unresolved_items=(),
        claim_ceiling="No product/world or portable commitment authority exists until a host Agent accepts a current-snapshot decision.",
        bounded_challenge=build_bounded_challenge_template(
            phase_id=PHASE_ID,
            trigger_ids=("product-world-sufficiency", "cross-phase-commitment"),
            owner_id=owner_id,
        ),
    )


def _string_list(value: Any, *, field: str, non_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise P1AgenticProductAuthorityError(f"{field} must be a list")
    result = [str(item).strip() for item in value if str(item).strip()]
    if non_empty and not result:
        raise P1AgenticProductAuthorityError(f"{field} must not be empty")
    return result


def _validate_world_knowledge_contract(
    world: Mapping[str, Any],
    *,
    source_ref_ids: set[str],
    decision_is_accepted: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_backfill = world.get("world_knowledge_backfill")
    if not isinstance(raw_backfill, list):
        raise P1AgenticProductAuthorityError("P1 world_knowledge_backfill must be a list")
    backfill_rows: list[dict[str, Any]] = []
    backfill_by_id: dict[str, dict[str, Any]] = {}
    for raw in raw_backfill:
        if not isinstance(raw, dict):
            raise P1AgenticProductAuthorityError("P1 world-knowledge backfill row is invalid")
        row = dict(raw)
        backfill_id = str(row.get("backfill_id") or "").strip()
        if not backfill_id or backfill_id in backfill_by_id:
            raise P1AgenticProductAuthorityError("P1 world-knowledge backfill identity is missing or duplicated")
        truth_state = str(row.get("truth_state") or "").strip()
        status = str(row.get("status") or "").strip()
        compatibility = str(row.get("source_compatibility") or "").strip()
        if truth_state not in {"agentic-world-knowledge", "review-bound"}:
            raise P1AgenticProductAuthorityError(f"unsupported P1 world-knowledge truth state: {backfill_id}")
        if status not in WORLD_BACKFILL_STATUSES:
            raise P1AgenticProductAuthorityError(f"unsupported P1 world-knowledge status: {backfill_id}")
        if compatibility not in WORLD_BACKFILL_COMPATIBILITY:
            raise P1AgenticProductAuthorityError(f"unsupported P1 world-knowledge source compatibility: {backfill_id}")
        refs = _string_list(row.get("source_refs", []), field=f"{backfill_id}.source_refs")
        if not set(refs).issubset(source_ref_ids):
            raise P1AgenticProductAuthorityError(f"P1 world-knowledge backfill references unknown source evidence: {backfill_id}")
        _string_list(row.get("affected_dimensions", []), field=f"{backfill_id}.affected_dimensions", non_empty=True)
        for required in ("statement", "rationale", "claim_ceiling"):
            if not str(row.get(required) or "").strip():
                raise P1AgenticProductAuthorityError(f"P1 world-knowledge backfill misses {required}: {backfill_id}")
        if status == "accepted" and (
            truth_state != "agentic-world-knowledge" or compatibility != "consistent"
        ):
            raise P1AgenticProductAuthorityError(
                f"accepted P1 world-knowledge backfill must be consistent agentic-world-knowledge: {backfill_id}"
            )
        if status == "review-bound" and truth_state != "review-bound":
            raise P1AgenticProductAuthorityError(
                f"review-bound P1 world-knowledge backfill must remain review-bound: {backfill_id}"
            )
        backfill_rows.append(row)
        backfill_by_id[backfill_id] = row

    product_world = world.get("product_world_decision")
    if not isinstance(product_world, dict):
        raise P1AgenticProductAuthorityError("P1 product_world_decision is missing")
    product_world = dict(product_world)
    if decision_is_accepted and not str(product_world.get("summary") or "").strip():
        raise P1AgenticProductAuthorityError("accepted P1 product_world_decision requires a summary")
    accepted_refs = _string_list(
        product_world.get("accepted_backfill_refs", []),
        field="product_world_decision.accepted_backfill_refs",
    )
    review_bound_refs = _string_list(
        product_world.get("review_bound_backfill_refs", []),
        field="product_world_decision.review_bound_backfill_refs",
    )
    if not set(accepted_refs).issubset(backfill_by_id):
        raise P1AgenticProductAuthorityError("P1 product_world_decision references unknown accepted backfill")
    if not set(review_bound_refs).issubset(backfill_by_id):
        raise P1AgenticProductAuthorityError("P1 product_world_decision references unknown review-bound backfill")
    accepted_row_ids = {backfill_id for backfill_id, row in backfill_by_id.items() if row.get("status") == "accepted"}
    review_bound_row_ids = {backfill_id for backfill_id, row in backfill_by_id.items() if row.get("status") == "review-bound"}
    if set(accepted_refs) != accepted_row_ids:
        raise P1AgenticProductAuthorityError("P1 product_world_decision must reference every accepted world-knowledge backfill")
    if set(review_bound_refs) != review_bound_row_ids:
        raise P1AgenticProductAuthorityError("P1 product_world_decision must reference every review-bound world-knowledge backfill")
    for ref in accepted_refs:
        if backfill_by_id[ref].get("status") != "accepted":
            raise P1AgenticProductAuthorityError(f"P1 product_world_decision promotes non-accepted backfill: {ref}")
    for ref in review_bound_refs:
        if backfill_by_id[ref].get("status") != "review-bound":
            raise P1AgenticProductAuthorityError(f"P1 product_world_decision misclassifies review-bound backfill: {ref}")

    topology = product_world.get("topology")
    if not isinstance(topology, dict):
        raise P1AgenticProductAuthorityError("P1 product-world topology decision is missing")
    topology_mode = str(topology.get("mode") or "").strip()
    topology_basis = str(topology.get("basis") or "").strip()
    if topology_mode not in WORLD_TOPOLOGY_MODES:
        raise P1AgenticProductAuthorityError("P1 product-world topology mode is invalid")
    if topology_basis not in WORLD_DECISION_BASES:
        raise P1AgenticProductAuthorityError("P1 product-world topology basis is invalid")
    if decision_is_accepted and not str(topology.get("statement") or "").strip():
        raise P1AgenticProductAuthorityError("accepted P1 product-world topology requires a statement")
    topology_source_refs = _string_list(topology.get("source_refs", []), field="product_world_decision.topology.source_refs")
    topology_backfill_refs = _string_list(topology.get("backfill_refs", []), field="product_world_decision.topology.backfill_refs")
    if not set(topology_source_refs).issubset(source_ref_ids):
        raise P1AgenticProductAuthorityError("P1 product-world topology references unknown source evidence")
    if not set(topology_backfill_refs).issubset(backfill_by_id):
        raise P1AgenticProductAuthorityError("P1 product-world topology references unknown backfill")
    if topology_basis == "source-established" and decision_is_accepted and not topology_source_refs:
        raise P1AgenticProductAuthorityError("source-established P1 topology requires source evidence")
    if topology_basis == "agentic-world-knowledge" and decision_is_accepted and not topology_backfill_refs:
        raise P1AgenticProductAuthorityError("world-knowledge P1 topology requires accepted backfill")
    if topology_basis == "mixed" and decision_is_accepted and (not topology_source_refs or not topology_backfill_refs):
        raise P1AgenticProductAuthorityError("mixed P1 topology requires source and backfill evidence")
    if topology_basis in {"agentic-world-knowledge", "mixed"}:
        for ref in topology_backfill_refs:
            if backfill_by_id[ref].get("status") != "accepted":
                raise P1AgenticProductAuthorityError(f"P1 topology cannot consume non-accepted backfill: {ref}")
    if topology_basis == "review-bound" and topology_mode != "review-bound":
        raise P1AgenticProductAuthorityError("review-bound P1 topology cannot publish a concrete topology mode")

    ownership = product_world.get("ownership")
    if not isinstance(ownership, dict):
        raise P1AgenticProductAuthorityError("P1 product-world ownership decision is missing")
    ownership_posture = str(ownership.get("posture") or "").strip()
    if ownership_posture not in WORLD_OWNERSHIP_POSTURES:
        raise P1AgenticProductAuthorityError("P1 product-world ownership posture is invalid")
    if decision_is_accepted and not str(ownership.get("statement") or "").strip():
        raise P1AgenticProductAuthorityError("accepted P1 product-world ownership requires a statement")
    ownership_source_refs = _string_list(ownership.get("source_refs", []), field="product_world_decision.ownership.source_refs")
    ownership_backfill_refs = _string_list(ownership.get("backfill_refs", []), field="product_world_decision.ownership.backfill_refs")
    if not set(ownership_source_refs).issubset(source_ref_ids):
        raise P1AgenticProductAuthorityError("P1 product-world ownership references unknown source evidence")
    if not set(ownership_backfill_refs).issubset(backfill_by_id):
        raise P1AgenticProductAuthorityError("P1 product-world ownership references unknown backfill")
    if ownership_posture == "source-defined" and decision_is_accepted and not ownership_source_refs:
        raise P1AgenticProductAuthorityError("source-defined P1 ownership requires source evidence")
    if ownership_posture == "agentic-world-knowledge" and decision_is_accepted and not ownership_backfill_refs:
        raise P1AgenticProductAuthorityError("world-knowledge P1 ownership requires accepted backfill")
    if ownership_posture == "mixed" and decision_is_accepted and (not ownership_source_refs or not ownership_backfill_refs):
        raise P1AgenticProductAuthorityError("mixed P1 ownership requires source and backfill evidence")
    if ownership_posture in {"agentic-world-knowledge", "mixed"}:
        for ref in ownership_backfill_refs:
            if backfill_by_id[ref].get("status") != "accepted":
                raise P1AgenticProductAuthorityError(f"P1 ownership cannot consume non-accepted backfill: {ref}")

    objects = product_world.get("objects", [])
    if not isinstance(objects, list):
        raise P1AgenticProductAuthorityError("P1 product-world objects must be a list")
    seen_object_ids: set[str] = set()
    for index, row in enumerate(objects, start=1):
        if not isinstance(row, dict):
            raise P1AgenticProductAuthorityError("P1 product-world object is invalid")
        object_id = str(row.get("object_id") or "").strip()
        name = str(row.get("name") or "").strip()
        basis = str(row.get("basis") or "").strip()
        if not object_id or object_id in seen_object_ids:
            raise P1AgenticProductAuthorityError(f"P1 product-world object {index} identity is missing or duplicated")
        seen_object_ids.add(object_id)
        if not name:
            raise P1AgenticProductAuthorityError(f"P1 product-world object {index} misses name")
        if basis not in WORLD_OBJECT_BASES:
            raise P1AgenticProductAuthorityError(f"P1 product-world object {index} basis is invalid")
        commitment_refs = _string_list(
            row.get("commitment_ids", []),
            field=f"product_world_decision.objects[{index}].commitment_ids",
            non_empty=True,
        )
        object_source_refs = _string_list(
            row.get("source_refs", []),
            field=f"product_world_decision.objects[{index}].source_refs",
        )
        object_backfill_refs = _string_list(
            row.get("backfill_refs", []),
            field=f"product_world_decision.objects[{index}].backfill_refs",
        )
        if not set(object_source_refs).issubset(source_ref_ids):
            raise P1AgenticProductAuthorityError(f"P1 product-world object {index} references unknown source evidence")
        if not set(object_backfill_refs).issubset(backfill_by_id):
            raise P1AgenticProductAuthorityError(f"P1 product-world object {index} references unknown backfill")
        if basis == "source-established" and not object_source_refs:
            raise P1AgenticProductAuthorityError(f"source-established P1 product-world object {index} requires source evidence")
        if basis == "agentic-world-knowledge" and not object_backfill_refs:
            raise P1AgenticProductAuthorityError(f"world-knowledge P1 product-world object {index} requires accepted backfill")
        if basis == "mixed" and (not object_source_refs or not object_backfill_refs):
            raise P1AgenticProductAuthorityError(f"mixed P1 product-world object {index} requires source and backfill evidence")
        for ref in object_backfill_refs:
            if backfill_by_id[ref].get("status") != "accepted":
                raise P1AgenticProductAuthorityError(f"P1 product-world object {index} cannot consume non-accepted backfill: {ref}")
        if not str(row.get("claim_ceiling") or "").strip():
            raise P1AgenticProductAuthorityError(f"P1 product-world object {index} misses claim_ceiling")
        row["commitment_ids"] = commitment_refs
        row["source_refs"] = object_source_refs
        row["backfill_refs"] = object_backfill_refs

    assignments = ownership.get("assignments", [])
    if not isinstance(assignments, list):
        raise P1AgenticProductAuthorityError("P1 product-world ownership assignments must be a list")
    if ownership_posture == "review-bound" and assignments:
        raise P1AgenticProductAuthorityError("review-bound P1 ownership cannot publish accepted role assignments")
    for index, row in enumerate(assignments, start=1):
        if not isinstance(row, dict):
            raise P1AgenticProductAuthorityError("P1 ownership assignment is invalid")
        role = str(row.get("role") or "").strip()
        basis = str(row.get("basis") or "").strip()
        if not role:
            raise P1AgenticProductAuthorityError(f"P1 ownership assignment {index} misses role")
        if basis not in OWNERSHIP_ASSIGNMENT_BASES:
            raise P1AgenticProductAuthorityError(f"P1 ownership assignment {index} basis is invalid")
        commitment_refs = _string_list(
            row.get("commitment_ids", []),
            field=f"product_world_decision.ownership.assignments[{index}].commitment_ids",
            non_empty=True,
        )
        assignment_source_refs = _string_list(
            row.get("source_refs", []),
            field=f"product_world_decision.ownership.assignments[{index}].source_refs",
        )
        assignment_backfill_refs = _string_list(
            row.get("backfill_refs", []),
            field=f"product_world_decision.ownership.assignments[{index}].backfill_refs",
        )
        if not set(assignment_source_refs).issubset(source_ref_ids):
            raise P1AgenticProductAuthorityError(f"P1 ownership assignment {index} references unknown source evidence")
        if not set(assignment_backfill_refs).issubset(backfill_by_id):
            raise P1AgenticProductAuthorityError(f"P1 ownership assignment {index} references unknown backfill")
        if basis == "source-established" and not assignment_source_refs:
            raise P1AgenticProductAuthorityError(f"source-established P1 ownership assignment {index} requires source evidence")
        if basis == "agentic-world-knowledge" and not assignment_backfill_refs:
            raise P1AgenticProductAuthorityError(f"world-knowledge P1 ownership assignment {index} requires accepted backfill")
        if basis == "mixed" and (not assignment_source_refs or not assignment_backfill_refs):
            raise P1AgenticProductAuthorityError(f"mixed P1 ownership assignment {index} requires source and backfill evidence")
        for ref in assignment_backfill_refs:
            if backfill_by_id[ref].get("status") != "accepted":
                raise P1AgenticProductAuthorityError(f"P1 ownership assignment {index} cannot consume non-accepted backfill: {ref}")
        if not str(row.get("claim_ceiling") or "").strip():
            raise P1AgenticProductAuthorityError(f"P1 ownership assignment {index} misses claim_ceiling")
        row["commitment_ids"] = commitment_refs
        row["source_refs"] = assignment_source_refs
        row["backfill_refs"] = assignment_backfill_refs

    return backfill_rows, product_world


def validate_p1_agentic_product_decision(
    decision: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
    accepted_required: bool = True,
) -> None:
    if not candidate_is_valid(candidate):
        raise P1AgenticProductAuthorityError("P1 Agentic candidate is invalid")
    try:
        validate_decision_envelope(
            decision,
            expected_phase_id=PHASE_ID,
            expected_decision_kind=DECISION_KIND,
            expected_input_snapshot_digest=str(candidate["input_snapshot"]["snapshot_digest"]),
            accepted_required=accepted_required,
        )
    except AgenticDecisionAuthorityError as exc:
        raise P1AgenticProductAuthorityError(str(exc)) from exc
    payload = decision.get("semantic_payload")
    if not isinstance(payload, dict):
        raise P1AgenticProductAuthorityError("P1 Agentic semantic payload is missing")
    source_ref_ids = {
        str(row.get("evidence_ref") or "")
        for row in candidate.get("source_evidence", [])
        if isinstance(row, dict)
    }
    candidate_ids = {
        str(row.get("candidate_id") or "")
        for row in candidate.get("candidate_feature_hints", [])
        if isinstance(row, dict)
    }
    sufficiency = payload.get("context_sufficiency")
    if not isinstance(sufficiency, dict) or sufficiency.get("status") not in {"sufficient", "review-bound", "insufficient"}:
        raise P1AgenticProductAuthorityError("P1 context sufficiency decision is invalid")
    if decision.get("decision_status") == "accepted" and (
        sufficiency.get("status") != "sufficient" or sufficiency.get("supports_downstream_claim") is not True
    ):
        raise P1AgenticProductAuthorityError("accepted P1 decision requires sufficient context for its bounded downstream claim")
    world = payload.get("world_alignment")
    if not isinstance(world, dict) or not isinstance(world.get("accepted_world"), dict):
        raise P1AgenticProductAuthorityError("P1 world alignment decision is missing")
    backfill_rows, product_world_decision = _validate_world_knowledge_contract(
        world,
        source_ref_ids=source_ref_ids,
        decision_is_accepted=decision.get("decision_status") == "accepted",
    )
    accepted_world = world["accepted_world"]
    world_state = str(accepted_world.get("truth_state") or "")
    if world_state not in TRUTH_STATES or not str(accepted_world.get("model") or "").strip():
        raise P1AgenticProductAuthorityError("P1 accepted world identity/truth state is invalid")
    world_refs = _string_list(accepted_world.get("source_refs", []), field="accepted_world.source_refs")
    if not set(world_refs).issubset(source_ref_ids):
        raise P1AgenticProductAuthorityError("P1 accepted world references unknown source evidence")
    if world_state in {"source-established", "owner-confirmed"} and not world_refs:
        raise P1AgenticProductAuthorityError("source/owner truth requires source evidence")
    review = payload.get("material_feature_review")
    if not isinstance(review, dict) or review.get("status") != "complete":
        raise P1AgenticProductAuthorityError("P1 material feature review is incomplete")
    reviewed_candidates = _string_list(review.get("reviewed_candidate_ids", []), field="reviewed_candidate_ids")
    if not set(reviewed_candidates).issubset(candidate_ids):
        raise P1AgenticProductAuthorityError("P1 material feature review references unknown candidates")
    features = payload.get("feature_dispositions")
    if not isinstance(features, list) or not features:
        raise P1AgenticProductAuthorityError("P1 feature dispositions are missing")
    feature_ids: set[str] = set()
    for row in features:
        if not isinstance(row, dict):
            raise P1AgenticProductAuthorityError("P1 feature disposition is invalid")
        feature_id = str(row.get("feature_id") or "").strip()
        if not feature_id or feature_id in feature_ids:
            raise P1AgenticProductAuthorityError("P1 feature identity is missing or duplicated")
        feature_ids.add(feature_id)
        if row.get("disposition") not in FEATURE_DISPOSITIONS:
            raise P1AgenticProductAuthorityError(f"unsupported P1 feature disposition: {feature_id}")
        if row.get("truth_state") not in TRUTH_STATES:
            raise P1AgenticProductAuthorityError(f"unsupported P1 feature truth state: {feature_id}")
        refs = _string_list(row.get("source_refs", []), field=f"{feature_id}.source_refs")
        if not set(refs).issubset(source_ref_ids):
            raise P1AgenticProductAuthorityError(f"P1 feature references unknown source evidence: {feature_id}")
        if row.get("truth_state") in {"source-established", "owner-confirmed"} and not refs:
            raise P1AgenticProductAuthorityError(f"P1 source/owner feature requires evidence: {feature_id}")
        for required in ("statement", "rationale", "owner", "claim_ceiling"):
            if not str(row.get(required) or "").strip():
                raise P1AgenticProductAuthorityError(f"P1 feature misses {required}: {feature_id}")
    commitments = payload.get("commitments")
    if not isinstance(commitments, list) or not commitments:
        raise P1AgenticProductAuthorityError("P1 portable commitments are missing")
    commitment_ids: set[str] = set()
    for row in commitments:
        if not isinstance(row, dict):
            raise P1AgenticProductAuthorityError("P1 commitment is invalid")
        commitment_id = str(row.get("commitment_id") or "").strip()
        if not COMMITMENT_ID_RE.fullmatch(commitment_id) or commitment_id in commitment_ids:
            raise P1AgenticProductAuthorityError(f"P1 commitment identity is invalid or duplicated: {commitment_id}")
        commitment_ids.add(commitment_id)
        if row.get("kind") not in COMMITMENT_KINDS:
            raise P1AgenticProductAuthorityError(f"P1 commitment kind is invalid: {commitment_id}")
        if row.get("truth_state") not in TRUTH_STATES:
            raise P1AgenticProductAuthorityError(f"P1 commitment truth state is invalid: {commitment_id}")
        refs = _string_list(row.get("source_refs", []), field=f"{commitment_id}.source_refs", non_empty=True)
        if not set(refs).issubset(source_ref_ids):
            raise P1AgenticProductAuthorityError(f"P1 commitment references unknown source evidence: {commitment_id}")
        linked_features = _string_list(row.get("feature_ids", []), field=f"{commitment_id}.feature_ids", non_empty=True)
        if not set(linked_features).issubset(feature_ids):
            raise P1AgenticProductAuthorityError(f"P1 commitment references unknown feature: {commitment_id}")
        if row.get("status") not in {"accepted", "review-bound"}:
            raise P1AgenticProductAuthorityError(f"P1 commitment status is invalid: {commitment_id}")
        for required in ("statement", "owner", "claim_ceiling"):
            if not str(row.get(required) or "").strip():
                raise P1AgenticProductAuthorityError(f"P1 commitment misses {required}: {commitment_id}")

    commitment_status_by_id = {
        str(row.get("commitment_id") or "").strip(): str(row.get("status") or "").strip()
        for row in commitments
        if isinstance(row, dict) and str(row.get("commitment_id") or "").strip()
    }
    for index, row in enumerate(
        product_world_decision.get("objects", []) if isinstance(product_world_decision.get("objects"), list) else [],
        start=1,
    ):
        if not isinstance(row, dict):
            continue
        for commitment_ref in row.get("commitment_ids", []):
            commitment_id = str(commitment_ref or "").strip()
            if commitment_id not in commitment_status_by_id:
                raise P1AgenticProductAuthorityError(
                    f"P1 product-world object {index} references unknown commitment: {commitment_id}"
                )
    ownership = product_world_decision.get("ownership", {}) if isinstance(product_world_decision, dict) else {}
    assignments = ownership.get("assignments", []) if isinstance(ownership, dict) else []
    assignment_owner_by_commitment: dict[str, str] = {}
    for index, row in enumerate(assignments if isinstance(assignments, list) else [], start=1):
        if not isinstance(row, dict):
            continue
        role = str(row.get("role") or "").strip()
        for commitment_ref in row.get("commitment_ids", []):
            commitment_id = str(commitment_ref or "").strip()
            if commitment_id not in commitment_status_by_id:
                raise P1AgenticProductAuthorityError(
                    f"P1 ownership assignment {index} references unknown commitment: {commitment_id}"
                )
            if commitment_status_by_id[commitment_id] != "accepted":
                raise P1AgenticProductAuthorityError(
                    f"P1 ownership assignment {index} cannot promote review-bound commitment: {commitment_id}"
                )
            prior = assignment_owner_by_commitment.get(commitment_id)
            if prior and prior != role:
                raise P1AgenticProductAuthorityError(
                    f"P1 ownership assignment is ambiguous for {commitment_id}: {prior} vs {role}"
                )
            assignment_owner_by_commitment[commitment_id] = role
    judgment = payload.get("product_judgment")
    if not isinstance(judgment, dict):
        raise P1AgenticProductAuthorityError("P1 product judgment is missing")
    required_challenge_triggers = {
        "product-world-sufficiency",
        "cross-phase-commitment",
    }
    if world_state in {"agentic-world-knowledge", "agentic-candidate", "agentic-hypothesis"} or any(
        str(row.get("status") or "") in {"accepted", "review-bound"}
        for row in backfill_rows
    ):
        required_challenge_triggers.add("candidate-world-semantics")
    try:
        validate_p1_decision_challenge_binding(
            decision=decision,
            candidate=candidate,
            required_trigger_ids=required_challenge_triggers,
        )
    except BoundedChallengeBindingError as exc:
        raise P1AgenticProductAuthorityError(str(exc)) from exc

    if product_world_decision.get("accepted_backfill_refs") and world_state not in {
        "agentic-world-knowledge",
        "agentic-candidate",
        "agentic-hypothesis",
        "review-bound",
    }:
        raise P1AgenticProductAuthorityError(
            "P1 accepted world cannot label adopted world knowledge as source/owner truth"
        )

    for field in (
        "primary_user_or_buyer",
        "product_goal",
        "status_quo_to_beat",
        "why_this_not_that",
        "continuation_owner",
        "proof_that_changes_decision",
        "mvp_wedge",
        "acceptance_should_prove",
    ):
        if not str(judgment.get(field) or "").strip():
            raise P1AgenticProductAuthorityError(f"P1 product judgment misses {field}")


def _authority_semantic_type(row: Mapping[str, Any], *, item_kind: str) -> str:
    status = str(row.get("status") or row.get("disposition") or "").strip()
    statement = str(row.get("statement") or "").casefold()
    if status in {"review-bound", "unresolved-review-bound", "context-completion"}:
        return "open_truth_gap"
    if status in {"later-slice", "deferred-seam", "explicit-exclusion"}:
        return "deferred_out_of_scope"
    if item_kind in {"policy", "constraint"}:
        return "audit_compliance_constraint"
    if item_kind == "acceptance_criterion":
        return "metric_success_signal"
    if re.search(r"\b(role|actor|owner|buyer|user)\b|角色|用户|家长|孩子|经理|接待|兽医", statement):
        return "role_actor_decision_owner"
    if re.search(r"\b(record|profile|summary|card|event|data|object)\b|记录|档案|摘要|卡片|数据|对象", statement):
        return "object_data_record"
    return "state_lifecycle"


def _authority_semantic_units(
    *,
    features: list[dict[str, Any]],
    commitments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for row in features:
        item_id = str(row.get("feature_id") or "").strip()
        if not item_id:
            continue
        units.append(
            {
                "semantic_unit_id": item_id,
                "semantic_type": _authority_semantic_type(row, item_kind="feature"),
                "source_excerpt": str(row.get("statement") or "").strip(),
                "source_refs": [str(item).strip() for item in row.get("source_refs", []) if str(item).strip()],
                "truth_state": str(row.get("truth_state") or "review-bound").strip(),
                "placement_target": "authority-governed canonical PRD and P2 handoff",
                "forbidden_flattening": str(row.get("claim_ceiling") or "").strip(),
                "authority": "accepted-snapshot-bound-agentic-product-decision",
                "status_or_disposition": str(row.get("disposition") or "").strip(),
            }
        )
    for row in commitments:
        item_id = str(row.get("commitment_id") or "").strip()
        if not item_id:
            continue
        units.append(
            {
                "semantic_unit_id": item_id,
                "semantic_type": _authority_semantic_type(row, item_kind=str(row.get("kind") or "commitment")),
                "source_excerpt": str(row.get("statement") or "").strip(),
                "source_refs": [str(item).strip() for item in row.get("source_refs", []) if str(item).strip()],
                "truth_state": str(row.get("truth_state") or "review-bound").strip(),
                "placement_target": "authority-governed canonical PRD and exact P2 disposition",
                "forbidden_flattening": str(row.get("claim_ceiling") or "").strip(),
                "authority": "accepted-snapshot-bound-agentic-product-decision",
                "status_or_disposition": str(row.get("status") or "").strip(),
            }
        )
    return units


def _authority_canonical_context(
    *,
    judgment: Mapping[str, Any],
    sufficiency: Mapping[str, Any],
    features: list[dict[str, Any]],
    commitments: list[dict[str, Any]],
    world_knowledge_backfill: list[dict[str, Any]],
    product_world_decision: Mapping[str, Any],
) -> dict[str, Any]:
    feature_by_id = {
        str(row.get("feature_id") or "").strip(): row
        for row in features
        if str(row.get("feature_id") or "").strip()
    }
    topology = product_world_decision.get("topology") if isinstance(product_world_decision.get("topology"), Mapping) else {}
    ownership = product_world_decision.get("ownership") if isinstance(product_world_decision.get("ownership"), Mapping) else {}
    workflow_topology = str(topology.get("statement") or "").strip()
    workflow_topology_mode = str(topology.get("mode") or "review-bound").strip()
    ownership_posture = str(ownership.get("posture") or "review-bound").strip()
    assignment_by_commitment: dict[str, dict[str, Any]] = {}
    for assignment in ownership.get("assignments", []) if isinstance(ownership.get("assignments"), list) else []:
        if not isinstance(assignment, dict):
            continue
        for commitment_ref in assignment.get("commitment_ids", []):
            commitment_id = str(commitment_ref or "").strip()
            if commitment_id:
                assignment_by_commitment[commitment_id] = dict(assignment)
    scenario_kinds = {"epic", "use_case", "user_story", "workflow_step"}
    scenario_rows = [
        row
        for row in commitments
        if str(row.get("kind") or "") in scenario_kinds
        or str(row.get("commitment_id") or "").strip() in assignment_by_commitment
    ]
    accepted_scenarios = [row for row in scenario_rows if str(row.get("status") or "") == "accepted"]
    if not accepted_scenarios:
        accepted_scenarios = scenario_rows
    object_by_commitment: dict[str, list[dict[str, Any]]] = {}
    product_world_objects = [
        dict(row)
        for row in product_world_decision.get("objects", [])
        if isinstance(row, dict)
    ] if isinstance(product_world_decision.get("objects"), list) else []
    for world_object in product_world_objects:
        for commitment_ref in world_object.get("commitment_ids", []):
            commitment_id = str(commitment_ref or "").strip()
            if commitment_id:
                object_by_commitment.setdefault(commitment_id, []).append(world_object)
    visible_backfill = [
        dict(row)
        for row in world_knowledge_backfill
        if str(row.get("status") or "") in {"accepted", "review-bound"}
    ]
    modules: list[dict[str, str]] = []
    flows: list[dict[str, Any]] = []
    for row in accepted_scenarios:
        commitment_id = str(row.get("commitment_id") or "").strip()
        statement = str(row.get("statement") or "").strip()
        linked_features = [
            feature_by_id[item]
            for item in row.get("feature_ids", [])
            if str(item) in feature_by_id
        ]
        steps = [str(item.get("statement") or "").strip() for item in linked_features if str(item.get("statement") or "").strip()]
        if not steps:
            steps = [statement]
        assignment = assignment_by_commitment.get(commitment_id, {})
        primary_actor = str(assignment.get("role") or "").strip() or "review-bound unless explicitly named by accepted authority"
        world_objects = object_by_commitment.get(commitment_id, [])
        core_object_names = [str(item.get("name") or "").strip() for item in world_objects if str(item.get("name") or "").strip()]
        core_objects = ", ".join(core_object_names) or ", ".join(str(item) for item in row.get("feature_ids", []) if str(item).strip())
        modules.append(
            {
                "module": commitment_id,
                "primary_actor": primary_actor,
                "core_objects": core_objects,
                "responsibility": statement,
                "input": f"accepted authority item {commitment_id} with exact source refs and status",
                "output": f"exact downstream disposition for {commitment_id}",
                "exit_action": "preserve identity, truth state, scope state, and claim ceiling",
                "architectural note": str(row.get("claim_ceiling") or "").strip(),
                "actor_basis": str(assignment.get("basis") or "review-bound").strip(),
                "actor_claim_ceiling": str(assignment.get("claim_ceiling") or "").strip(),
            }
        )
        flows.append({"name": commitment_id, "steps": steps, "topology": "authority-governed-local-flow"})
    first_wave = [
        str(row.get("feature_id") or "").strip()
        for row in features
        if str(row.get("disposition") or "") == "first-wave-commitment"
    ]
    deferred = [
        str(row.get("statement") or "").strip()
        for row in features
        if str(row.get("disposition") or "") in {"later-slice", "deferred-seam", "explicit-exclusion"}
        and str(row.get("statement") or "").strip()
    ]
    constraints = [
        str(row.get("statement") or "").strip()
        for row in commitments
        if str(row.get("kind") or "") in {"policy", "constraint"}
        and str(row.get("statement") or "").strip()
    ]
    review_bound = [str(item).strip() for item in sufficiency.get("missing_facts", []) if str(item).strip()]
    return {
        "primary_segment": str(judgment.get("primary_user_or_buyer") or "").strip(),
        "objectives": [str(judgment.get("product_goal") or "").strip()],
        "modules": modules,
        "flows": flows,
        "first_slice_modules": [str(row.get("commitment_id") or "").strip() for row in accepted_scenarios],
        "workflow_topology": workflow_topology,
        "workflow_topology_mode": workflow_topology_mode,
        "ownership_posture": ownership_posture,
        "world_knowledge_backfill": visible_backfill,
        "product_world_objects": product_world_objects,
        "product_world_decision": dict(product_world_decision),
        "constraints": constraints,
        "nfrs": constraints,
        "out_of_scope": deferred,
        "p0": first_wave,
        "p1": deferred,
        "p2": deferred,
        "business_value_signals": [str(judgment.get("product_goal") or "").strip()],
        "pressure_signals": [str(judgment.get("status_quo_to_beat") or "").strip()],
        "commercial_decision_signals": [
            str(judgment.get("proof_that_changes_decision") or "").strip(),
            str(judgment.get("continuation_owner") or "").strip(),
        ],
        "user_experience_signals": [str(judgment.get("mvp_wedge") or "").strip()],
        "review_bound_items": review_bound,
    }


def build_decision_bound_direct_driver(
    candidate: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    validate_p1_agentic_product_decision(decision, candidate=candidate)
    payload = dict(decision["semantic_payload"])
    judgment = dict(payload["product_judgment"])
    sufficiency = dict(payload["context_sufficiency"])
    world = dict(payload["world_alignment"])
    accepted_world = dict(world["accepted_world"])
    world_knowledge_backfill = [
        dict(row) for row in world.get("world_knowledge_backfill", []) if isinstance(row, dict)
    ]
    product_world_decision = dict(world.get("product_world_decision") or {})
    features = [dict(row) for row in payload["feature_dispositions"]]
    commitments = [dict(row) for row in payload["commitments"]]
    driver = deepcopy(candidate["mechanical_candidate_driver"])
    driver["driver_id"] = "p1-agentic-product-authority-driver.v1"
    driver["source_truth_admission"] = {
        "truth_state": "decision-bound-mixed-truth",
        "source_native_terms": sorted(
            {
                str(item).strip()
                for row in candidate["source_evidence"]
                for item in [row.get("text")]
                if str(item).strip()
            }
        )[:24],
        "review_bound_items": list(sufficiency.get("missing_facts", [])),
        "claim_ceiling": str(decision.get("claim_ceiling") or ""),
        "decision_id": decision["decision_id"],
        "decision_digest": decision["content_digest"],
    }
    driver["product_judgment"] = {
        "primary_user_or_buyer": judgment["primary_user_or_buyer"],
        "product_goal": judgment["product_goal"],
        "status_quo_to_beat": judgment["status_quo_to_beat"],
        "why_this_not_that": judgment["why_this_not_that"],
        "accepted_world": accepted_world,
        "product_world_decision": product_world_decision,
        "world_knowledge_backfill": world_knowledge_backfill,
        "truth_basis": "snapshot-bound-agentic-decision",
    }
    driver["commercial_judgment"] = {
        "continuation_owner": judgment["continuation_owner"],
        "proof_that_changes_decision": judgment["proof_that_changes_decision"],
        "decision_leverage": judgment["why_this_not_that"],
        "commercial_truth_state": accepted_world["truth_state"],
    }
    driver["business_feasibility"] = {
        "feasible_wedge": judgment["mvp_wedge"],
        "business_reality": judgment["product_goal"],
        "feasibility_claim": str(decision.get("claim_ceiling") or ""),
    }
    driver["mvp_wedge"] = {
        "narrowest_valuable_wedge": judgment["mvp_wedge"],
        "must_protect": [row["feature_id"] for row in features if row["disposition"] == "first-wave-commitment"],
        "defer_or_review_bound": [
            row["feature_id"]
            for row in features
            if row["disposition"] in {"later-slice", "deferred-seam", "unresolved-review-bound", "context-completion"}
        ],
    }
    driver["acceptance_meaning"] = {
        "acceptance_should_prove": judgment["acceptance_should_prove"],
        "not_just": "field presence, template completion, lexical density, or clean generic workflow labels",
    }
    review_bound_items = [str(item).strip() for item in sufficiency.get("missing_facts", []) if str(item).strip()]
    claim_ceiling = str(decision.get("claim_ceiling") or "").strip()
    driver["business_judgment_synthesis"] = {
        "product_decision": judgment["product_goal"],
        "problem_label": judgment["status_quo_to_beat"],
        "goal_label": judgment["product_goal"],
        "substitute_label": judgment["status_quo_to_beat"],
        "proof_label": judgment["proof_that_changes_decision"],
        "commercial_decision": (
            f"{judgment['continuation_owner']} decides continue / revise / pause from "
            f"{judgment['proof_that_changes_decision']}."
        ),
        "acceptance_decision": judgment["acceptance_should_prove"],
        "review_bound_items": review_bound_items,
        "claim_ceiling": claim_ceiling,
    }
    driver["business_judgment_transformation"] = {
        "product_bet": judgment["product_goal"],
        "why_now": judgment["status_quo_to_beat"],
        "why_this_wedge": judgment["mvp_wedge"],
        "why_not_status_quo": judgment["why_this_not_that"],
        "why_not_single_tool_or_service_substitute": judgment["why_this_not_that"],
        "proof_needed_for_next_investment": judgment["proof_that_changes_decision"],
        "reader_facing_summary": judgment["product_goal"],
        "claim_blocking_open_truth": "; ".join(review_bound_items),
        "review_bound_items": review_bound_items,
        "claim_ceiling": claim_ceiling,
    }
    driver["business_completeness_driver"] = {
        "driver_id": "p1-agentic-authority-business-completeness-driver.v1",
        "business_loss_chain": {
            "pain_holder": judgment["primary_user_or_buyer"],
            "status_quo_to_beat": judgment["status_quo_to_beat"],
            "business_pressure": judgment["status_quo_to_beat"],
            "business_outcome_at_risk": judgment["product_goal"],
            "loss_chain": judgment["why_this_not_that"],
        },
        "continuation_economics": {
            "continuation_owner": judgment["continuation_owner"],
            "continuation_decision": "continue / revise / pause",
            "decision_trigger": judgment["proof_that_changes_decision"],
            "spend_or_commitment_at_risk": claim_ceiling,
        },
        "proof_for_continue": {
            "proof_artifact": judgment["proof_that_changes_decision"],
            "directional_threshold": judgment["acceptance_should_prove"],
            "missing_external_evidence": "; ".join(review_bound_items),
            "source_signal_state": accepted_world["truth_state"],
        },
        "commercial_claim_ceiling": {
            "truth_state": accepted_world["truth_state"],
            "allowed_claim": claim_ceiling,
            "forbidden_upgrade": "owner confirmation, external validation, UAT, release readiness, or production readiness",
            "evidence_confidence_state": "authority-bounded",
        },
        "downstream_business_contract": {
            "p2_must_preserve": [
                "accepted world",
                "product-world topology and ownership posture",
                "world-knowledge backfill provenance",
                "portable commitment identity",
                "truth state",
                "review-bound status",
                "claim ceiling",
            ],
            "p2_must_not_invent": [
                "serial workflow order",
                "step ownership",
                "buyer confirmation",
                "scope outside accepted dispositions",
            ],
            "review_bound_gaps": review_bound_items,
        },
    }
    driver["open_truth_gap_routing"] = {
        "pre_p1_or_p1": review_bound_items,
        "downstream_route": str(sufficiency.get("route") or "return to P1/context completion"),
        "p2_must_not_invent": [
            "product goal",
            "scenario topology",
            "role or step ownership",
            "MVP scope",
            "acceptance meaning",
        ],
    }
    driver["forbidden_downstream_assumptions"] = [
        "Do not replace a source-defined product structure with a generic world-knowledge or workflow preference.",
        "Do not infer product topology from natural-language keywords, heading order, or generic workflow defaults.",
        "Do not infer role, actor, owner, buyer, permission, or only-writer truth that the accepted authority does not state.",
        "Do not label accepted world-knowledge backfill as source-established or owner-confirmed truth.",
        "Do not promote review-bound or unresolved items to confirmed canonical truth.",
        "Do not move deferred or excluded feature dispositions into the first wave.",
        f"Do not exceed the accepted claim ceiling: {claim_ceiling}",
    ]
    driver["canonical_context"] = _authority_canonical_context(
        judgment=judgment,
        sufficiency=sufficiency,
        features=features,
        commitments=commitments,
        world_knowledge_backfill=world_knowledge_backfill,
        product_world_decision=product_world_decision,
    )
    driver["semantic_authoring_spine"] = {
        "authority": "snapshot-bound-agentic-product-decision",
        "decision_id": decision["decision_id"],
        "decision_digest": decision["content_digest"],
        "semantic_units": _authority_semantic_units(features=features, commitments=commitments),
        "feature_dispositions": features,
        "portable_commitments": commitments,
    }
    driver["semantic_authoring_summary"] = {
        "mode": "accepted-snapshot-bound-agentic-product-authority",
        "decision_id": decision["decision_id"],
        "feature_disposition_count": len(features),
        "portable_commitment_count": len(commitments),
        "first_wave_commitment_count": len([row for row in features if row["disposition"] == "first-wave-commitment"]),
        "review_bound_count": len([row for row in features if row["disposition"] in {"unresolved-review-bound", "context-completion"}]),
    }
    driver["agentic_product_authority"] = {
        "decision_id": decision["decision_id"],
        "decision_digest": decision["content_digest"],
        "input_snapshot_digest": decision["input_snapshot_digest"],
        "accepted_world": accepted_world,
        "world_knowledge_contract": WORLD_KNOWLEDGE_CONTRACT,
        "world_knowledge_backfill": world_knowledge_backfill,
        "product_world_decision": product_world_decision,
        "context_sufficiency": sufficiency,
        "product_judgment": judgment,
        "feature_dispositions": features,
        "commitments": commitments,
        "claim_ceiling": decision["claim_ceiling"],
    }
    driver["claim_ceiling"] = {
        "state": "accepted-with-explicit-truth-boundaries",
        "allowed": str(decision.get("claim_ceiling") or ""),
        "forbidden": "owner confirmation, domain-expert correctness, market validation, architecture quality, implementation readiness, or production readiness",
    }
    return driver


def build_p1_agentic_product_authority(
    candidate: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    validate_p1_agentic_product_decision(decision, candidate=candidate)
    semantic = dict(decision["semantic_payload"])
    payload = {
        "schema_version": AUTHORITY_SCHEMA,
        "status": "accepted-p1-agentic-product-authority",
        "phase_id": PHASE_ID,
        "decision_id": decision["decision_id"],
        "decision_digest": decision["content_digest"],
        "input_snapshot_digest": decision["input_snapshot_digest"],
        "world_alignment": semantic["world_alignment"],
        "world_knowledge_contract": WORLD_KNOWLEDGE_CONTRACT,
        "world_knowledge_backfill": semantic["world_alignment"]["world_knowledge_backfill"],
        "product_world_decision": semantic["world_alignment"]["product_world_decision"],
        "context_sufficiency": semantic["context_sufficiency"],
        "material_feature_review": semantic["material_feature_review"],
        "feature_dispositions": semantic["feature_dispositions"],
        "commitments": semantic["commitments"],
        "product_judgment": semantic["product_judgment"],
        "truth_boundary": {
            "source_established": "requires exact admitted source refs and cannot be overwritten by backfill",
            "agentic_world_knowledge": "accepted non-source world enrichment; must remain provenance-distinct and source-consistent",
            "agentic_candidate": "accepted decision assumption, not confirmed domain truth",
            "owner_confirmed": "requires explicit source evidence naming that confirmation",
            "unresolved": "must remain review-bound or route to context completion",
        },
        "claim_ceiling": str(decision.get("claim_ceiling") or ""),
        "decision_integrity_contract": str(decision.get("decision_integrity_contract") or ""),
        "challenge_binding_digest": str((decision.get("challenge_binding") or {}).get("content_digest") or ""),
        "bounded_challenge": challenge_summary(decision["bounded_challenge"]),
    }
    return _with_content_digest(payload)


def p1_agentic_product_authority_is_valid(authority: Mapping[str, Any]) -> bool:
    if authority.get("schema_version") != AUTHORITY_SCHEMA or authority.get("status") != "accepted-p1-agentic-product-authority":
        return False
    if authority.get("world_knowledge_contract") != WORLD_KNOWLEDGE_CONTRACT:
        return False
    if not isinstance(authority.get("world_knowledge_backfill"), list) or not isinstance(authority.get("product_world_decision"), dict):
        return False
    body = {key: value for key, value in authority.items() if key != "content_digest"}
    if authority.get("content_digest") != canonical_digest(body):
        return False
    return bool(authority.get("decision_digest") and isinstance(authority.get("commitments"), list) and authority.get("commitments"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or validate P1 snapshot-bound Agentic product authority")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--source", required=True)
    prepare.add_argument("--candidate-output", required=True)
    prepare.add_argument("--decision-template-output")
    prepare.add_argument("--owner-id", default="host-agent-required")
    validate = subparsers.add_parser("validate")
    validate.add_argument("--source", required=True)
    validate.add_argument("--decision", required=True)
    validate.add_argument("--authority-output")
    args = parser.parse_args(argv)
    source = Path(args.source).resolve()
    candidate = build_p1_agentic_product_candidate(source)
    if args.command == "prepare":
        write_json_atomic(Path(args.candidate_output).resolve(), candidate)
        if args.decision_template_output:
            write_json_atomic(
                Path(args.decision_template_output).resolve(),
                build_decision_template(candidate, owner_id=args.owner_id),
            )
        print(json.dumps({"status": "agentic-decision-required", "candidate_digest": candidate["content_digest"]}))
        return 0
    decision = load_json_object(Path(args.decision).resolve())
    validate_p1_agentic_product_decision(decision, candidate=candidate)
    authority = build_p1_agentic_product_authority(candidate, decision)
    if args.authority_output:
        write_json_atomic(Path(args.authority_output).resolve(), authority)
    print(json.dumps({"status": "accepted", "authority_digest": authority["content_digest"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
