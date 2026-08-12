"""Exact binding between bounded challenge evidence and current authority subjects.

This module owns provenance and reconciliation only. It does not decide product,
architecture, implementation, evidence classification, or claim truth.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from common.bounded_agentic_challenge import (
    BoundedAgenticChallengeError,
    canonical_digest,
    validate_bounded_challenge,
)
from common.bounded_agentic_challenge_compat import (
    CURRENT_DECISION_INTEGRITY_CONTRACT,
)


DECISION_CHALLENGE_BINDING_SCHEMA = "wff.decision-challenge-binding.v1"
EVIDENCE_CHALLENGE_BINDING_SCHEMA = "wff.evidence-challenge-binding.v1"


class BoundedChallengeBindingError(ValueError):
    """Raised when challenge evidence is not bound to the current subject."""


def _digest(payload: Mapping[str, Any]) -> str:
    return canonical_digest({key: value for key, value in payload.items() if key != "content_digest"})


def _identity(value: Mapping[str, Any], *, label: str) -> dict[str, str]:
    if set(value) != {"identity", "sha256"}:
        raise BoundedChallengeBindingError(f"{label} identity shape is invalid")
    identity = str(value.get("identity") or "").strip()
    digest = str(value.get("sha256") or "").strip()
    if not identity or not digest.startswith("sha256:") or len(digest) != 71:
        raise BoundedChallengeBindingError(f"{label} identity or digest is invalid")
    return {"identity": identity, "sha256": digest}


def normalized_review_subject(
    *,
    artifact: Mapping[str, Any],
    contract: Mapping[str, Any],
    admitted_context: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    contexts = [_identity(row, label="admitted context") for row in admitted_context]
    if not contexts:
        raise BoundedChallengeBindingError("challenge binding requires admitted context")
    return {
        "artifact": _identity(artifact, label="artifact"),
        "contract": _identity(contract, label="contract"),
        "admitted_context": sorted(contexts, key=lambda row: (row["identity"], row["sha256"])),
    }


def decision_subject_payload(
    *,
    phase_id: str,
    decision_kind: str,
    decision_id: str,
    input_snapshot_digest: str,
    semantic_payload: Mapping[str, Any],
    decision_status: str,
    unresolved_items: Iterable[Mapping[str, Any]],
    claim_ceiling: str,
) -> dict[str, Any]:
    return {
        "phase_id": str(phase_id).strip(),
        "decision_kind": str(decision_kind).strip(),
        "decision_id": str(decision_id).strip(),
        "input_snapshot_digest": str(input_snapshot_digest).strip(),
        "semantic_payload": dict(semantic_payload),
        "decision_status": str(decision_status).strip(),
        "unresolved_items": [dict(row) for row in unresolved_items],
        "claim_ceiling": str(claim_ceiling).strip(),
    }


def decision_subject_digest(**kwargs: Any) -> str:
    return canonical_digest(decision_subject_payload(**kwargs))


def decision_subject_from_envelope(decision: Mapping[str, Any]) -> dict[str, Any]:
    return decision_subject_payload(
        phase_id=str(decision.get("phase_id") or ""),
        decision_kind=str(decision.get("decision_kind") or ""),
        decision_id=str(decision.get("decision_id") or ""),
        input_snapshot_digest=str(decision.get("input_snapshot_digest") or ""),
        semantic_payload=(decision.get("semantic_payload") if isinstance(decision.get("semantic_payload"), Mapping) else {}),
        decision_status=str(decision.get("decision_status") or ""),
        unresolved_items=(decision.get("unresolved_items") if isinstance(decision.get("unresolved_items"), list) else ()),
        claim_ceiling=str(decision.get("claim_ceiling") or ""),
    )


def build_decision_challenge_binding(
    *,
    decision_subject: Mapping[str, Any],
    challenge: Mapping[str, Any],
    review_subject: Mapping[str, Any],
) -> dict[str, Any]:
    cycles = challenge.get("cycles") if isinstance(challenge.get("cycles"), list) else []
    if not cycles or not isinstance(cycles[-1], Mapping):
        raise BoundedChallengeBindingError("challenge has no final review cycle")
    final_packet = cycles[-1].get("review_packet")
    if not isinstance(final_packet, Mapping):
        raise BoundedChallengeBindingError("challenge final review packet is missing")
    normalized = normalized_review_subject(
        artifact=review_subject.get("artifact", {}),
        contract=review_subject.get("contract", {}),
        admitted_context=review_subject.get("admitted_context", ()),
    )
    packet_subject = normalized_review_subject(
        artifact=final_packet.get("artifact", {}),
        contract=final_packet.get("contract", {}),
        admitted_context=final_packet.get("admitted_context", ()),
    )
    if packet_subject != normalized:
        raise BoundedChallengeBindingError("challenge final packet does not match the current decision subject")
    payload = {
        "schema_version": DECISION_CHALLENGE_BINDING_SCHEMA,
        "binding_kind": "decision-publication",
        "decision_integrity_contract": CURRENT_DECISION_INTEGRITY_CONTRACT,
        "phase_id": str(decision_subject.get("phase_id") or ""),
        "decision_id": str(decision_subject.get("decision_id") or ""),
        "input_snapshot_digest": str(decision_subject.get("input_snapshot_digest") or ""),
        "decision_subject_digest": canonical_digest(dict(decision_subject)),
        "challenge_digest": str(challenge.get("content_digest") or ""),
        "final_review_unit_digest": str(cycles[-1].get("review_unit_digest") or ""),
        "review_subject": normalized,
    }
    payload["content_digest"] = _digest(payload)
    return payload


def _remaining_by_id(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for raw in rows:
        finding_id = str(raw.get("finding_id") or raw.get("item_id") or "").strip()
        if not finding_id:
            continue
        result[finding_id] = {
            "reason": str(raw.get("reason") or "").strip(),
            "owner": str(raw.get("owner") or "").strip(),
            "claim_ceiling": str(raw.get("claim_ceiling") or "").strip(),
        }
    return result


def reconcile_challenge_with_decision(
    *,
    decision: Mapping[str, Any],
    challenge: Mapping[str, Any],
) -> None:
    decision_status = str(decision.get("decision_status") or "")
    challenge_status = str(challenge.get("resulting_decision_status") or "")
    if decision_status != challenge_status:
        raise BoundedChallengeBindingError("challenge resulting status differs from the final decision")
    decision_ceiling = str(decision.get("claim_ceiling") or "").strip()
    challenge_ceiling = str(challenge.get("claim_ceiling") or "").strip()
    if decision_ceiling != challenge_ceiling:
        raise BoundedChallengeBindingError("final decision claim ceiling differs from the reconciled challenge ceiling")
    challenge_remaining = _remaining_by_id(
        challenge.get("remaining_review_bound_items", [])
        if isinstance(challenge.get("remaining_review_bound_items"), list)
        else []
    )
    decision_remaining = _remaining_by_id(
        decision.get("unresolved_items", []) if isinstance(decision.get("unresolved_items"), list) else []
    )
    if challenge_remaining != decision_remaining:
        raise BoundedChallengeBindingError(
            "final decision unresolved items do not exactly preserve remaining review-bound findings"
        )


def validate_decision_challenge_binding(
    *,
    decision: Mapping[str, Any],
    expected_review_subject: Mapping[str, Any],
    required_trigger_ids: Iterable[str],
) -> dict[str, Any]:
    if str(decision.get("decision_integrity_contract") or "") != CURRENT_DECISION_INTEGRITY_CONTRACT:
        raise BoundedChallengeBindingError(
            "current authority publication requires bounded-challenge-integrity-v1; legacy decisions remain historical proof only"
        )
    challenge = decision.get("bounded_challenge")
    binding = decision.get("challenge_binding")
    if not isinstance(challenge, Mapping) or not isinstance(binding, Mapping):
        raise BoundedChallengeBindingError("current decision lacks challenge evidence or exact binding")
    owner = decision.get("decision_owner")
    owner_id = str(owner.get("id") or "") if isinstance(owner, Mapping) else ""
    try:
        validate_bounded_challenge(
            challenge,
            expected_phase_id=str(decision.get("phase_id") or ""),
            expected_trigger_ids=required_trigger_ids,
            expected_owner_id=owner_id,
            accepted_decision=str(decision.get("decision_status") or "") == "accepted",
        )
    except BoundedAgenticChallengeError as exc:
        raise BoundedChallengeBindingError(str(exc)) from exc
    if binding.get("schema_version") != DECISION_CHALLENGE_BINDING_SCHEMA or binding.get("content_digest") != _digest(binding):
        raise BoundedChallengeBindingError("decision challenge binding digest or schema is invalid")
    subject = decision_subject_from_envelope(decision)
    expected_binding = build_decision_challenge_binding(
        decision_subject=subject,
        challenge=challenge,
        review_subject=expected_review_subject,
    )
    if dict(binding) != expected_binding:
        raise BoundedChallengeBindingError("decision challenge binding does not match the current decision subject")
    reconcile_challenge_with_decision(decision=decision, challenge=challenge)
    return dict(binding)


def evidence_subject_payload(
    *,
    phase_id: str,
    evidence_identity: str,
    evidence_digest: str,
    classification: str,
    decision_reference: str,
    owner: str,
    reason: str,
    retry_route: str,
    claim_ceiling: str,
) -> dict[str, Any]:
    return {
        "phase_id": str(phase_id).strip(),
        "evidence_identity": str(evidence_identity).strip(),
        "evidence_digest": str(evidence_digest).strip(),
        "classification": str(classification).strip(),
        "decision_reference": str(decision_reference).strip(),
        "owner": str(owner).strip(),
        "reason": str(reason).strip(),
        "retry_route": str(retry_route).strip(),
        "claim_ceiling": str(claim_ceiling).strip(),
    }


def build_evidence_challenge_binding(
    *,
    evidence_subject: Mapping[str, Any],
    challenge: Mapping[str, Any],
    review_subject: Mapping[str, Any],
) -> dict[str, Any]:
    cycles = challenge.get("cycles") if isinstance(challenge.get("cycles"), list) else []
    if not cycles or not isinstance(cycles[-1], Mapping):
        raise BoundedChallengeBindingError("evidence challenge has no final review cycle")
    final_packet = cycles[-1].get("review_packet")
    if not isinstance(final_packet, Mapping):
        raise BoundedChallengeBindingError("evidence challenge final review packet is missing")
    normalized = normalized_review_subject(
        artifact=review_subject.get("artifact", {}),
        contract=review_subject.get("contract", {}),
        admitted_context=review_subject.get("admitted_context", ()),
    )
    packet_subject = normalized_review_subject(
        artifact=final_packet.get("artifact", {}),
        contract=final_packet.get("contract", {}),
        admitted_context=final_packet.get("admitted_context", ()),
    )
    if packet_subject != normalized:
        raise BoundedChallengeBindingError("evidence challenge packet does not match the current evidence subject")
    payload = {
        "schema_version": EVIDENCE_CHALLENGE_BINDING_SCHEMA,
        "binding_kind": "evidence-disposition",
        "phase_id": str(evidence_subject.get("phase_id") or ""),
        "evidence_identity": str(evidence_subject.get("evidence_identity") or ""),
        "evidence_digest": str(evidence_subject.get("evidence_digest") or ""),
        "evidence_subject_digest": canonical_digest(dict(evidence_subject)),
        "challenge_digest": str(challenge.get("content_digest") or ""),
        "final_review_unit_digest": str(cycles[-1].get("review_unit_digest") or ""),
        "review_subject": normalized,
    }
    payload["content_digest"] = _digest(payload)
    return payload


def validate_evidence_challenge_binding(
    *,
    evidence_subject: Mapping[str, Any],
    challenge: Mapping[str, Any],
    binding: Mapping[str, Any],
    expected_review_subject: Mapping[str, Any],
    required_trigger_ids: Iterable[str],
) -> dict[str, Any]:
    try:
        validate_bounded_challenge(
            challenge,
            expected_phase_id=str(evidence_subject.get("phase_id") or ""),
            expected_trigger_ids=required_trigger_ids,
            expected_owner_id=str(evidence_subject.get("owner") or ""),
            accepted_decision=True,
        )
    except BoundedAgenticChallengeError as exc:
        raise BoundedChallengeBindingError(str(exc)) from exc
    if str(challenge.get("resulting_decision_status") or "") != "accepted":
        raise BoundedChallengeBindingError("accepted evidence disposition requires an accepted challenge result")
    if str(challenge.get("claim_ceiling") or "") != str(evidence_subject.get("claim_ceiling") or ""):
        raise BoundedChallengeBindingError("evidence disposition ceiling differs from challenge ceiling")
    if binding.get("schema_version") != EVIDENCE_CHALLENGE_BINDING_SCHEMA or binding.get("content_digest") != _digest(binding):
        raise BoundedChallengeBindingError("evidence challenge binding digest or schema is invalid")
    expected = build_evidence_challenge_binding(
        evidence_subject=evidence_subject,
        challenge=challenge,
        review_subject=expected_review_subject,
    )
    if dict(binding) != expected:
        raise BoundedChallengeBindingError("evidence challenge binding does not match current evidence/disposition")
    return dict(binding)
