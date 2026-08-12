"""P4 adapter binding challenge evidence to exact evidence dispositions."""

from __future__ import annotations

from typing import Any, Mapping

from common.bounded_agentic_challenge import canonical_digest
from common.bounded_agentic_challenge_binding import (
    build_evidence_challenge_binding,
    evidence_subject_payload,
    validate_evidence_challenge_binding,
)


PHASE_ID = "P4"
CONTRACT_ID = "p4-evidence-disposition-claim-ceiling-contract.v1"
CONTRACT_DIGEST = canonical_digest(
    {
        "contract_id": CONTRACT_ID,
        "allowed_classifications": ["environment-only", "transient-only"],
        "rule": "a disposition may lower failure impact only when bound to exact evidence and an accepted bounded challenge",
        "truth_boundary": "P4 records caller classification and does not independently prove environment causality",
    }
)


def p4_evidence_subject(*, row: Mapping[str, Any]) -> dict[str, Any]:
    return evidence_subject_payload(
        phase_id=PHASE_ID,
        evidence_identity=str(row.get("evidence_path") or ""),
        evidence_digest=str(row.get("evidence_digest") or ""),
        classification=str(row.get("classification") or ""),
        decision_reference=str(row.get("decision_reference") or ""),
        owner=str(row.get("owner") or ""),
        reason=str(row.get("reason") or ""),
        retry_route=str(row.get("retry_route") or ""),
        claim_ceiling=str(row.get("claim_ceiling") or ""),
    )


def p4_review_subject(*, row: Mapping[str, Any]) -> dict[str, Any]:
    subject = p4_evidence_subject(row=row)
    return {
        "artifact": {
            "identity": str(subject["evidence_identity"]),
            "sha256": str(subject["evidence_digest"]),
        },
        "contract": {"identity": CONTRACT_ID, "sha256": CONTRACT_DIGEST},
        "admitted_context": [
            {
                "identity": "p4-evidence-disposition-subject",
                "sha256": canonical_digest(subject),
            }
        ],
    }


def build_p4_evidence_challenge_binding(
    *,
    row: Mapping[str, Any],
    challenge: Mapping[str, Any],
) -> dict[str, Any]:
    return build_evidence_challenge_binding(
        evidence_subject=p4_evidence_subject(row=row),
        challenge=challenge,
        review_subject=p4_review_subject(row=row),
    )


def validate_p4_evidence_challenge_binding(*, row: Mapping[str, Any]) -> dict[str, Any]:
    challenge = row.get("bounded_challenge")
    binding = row.get("evidence_challenge_binding")
    if not isinstance(challenge, Mapping) or not isinstance(binding, Mapping):
        raise ValueError("P4 evidence disposition lacks bounded challenge or exact evidence binding")
    return validate_evidence_challenge_binding(
        evidence_subject=p4_evidence_subject(row=row),
        challenge=challenge,
        binding=binding,
        expected_review_subject=p4_review_subject(row=row),
        required_trigger_ids=("agentic-claim-ceiling", "unresolved-risk-closure"),
    )
