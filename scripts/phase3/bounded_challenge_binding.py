"""P3 adapter binding bounded challenge evidence to the exact implementation decision."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from common.bounded_agentic_challenge import canonical_digest
from common.bounded_agentic_challenge_binding import (
    build_decision_challenge_binding,
    decision_subject_payload,
    validate_decision_challenge_binding,
)


PHASE_ID = "P3"
DECISION_KIND = "p3-implementation-authority"
CONTRACT_ID = "p3-implementation-realization-authority-contract.v1"
CONTRACT_DIGEST = canonical_digest(
    {
        "contract_id": CONTRACT_ID,
        "authority_schema": "wff.p3-agentic-implementation-authority.v1",
        "required_triggers": [
            "exact-realization",
            "implementation-invariant",
            "irreversible-migration",
        ],
        "truth_boundary": "code/test shape and Trace occurrence cannot create implementation meaning",
    }
)


def _context_rows(candidate: Mapping[str, Any]) -> list[dict[str, str]]:
    snapshot = candidate.get("input_snapshot")
    inputs = snapshot.get("inputs") if isinstance(snapshot, Mapping) else []
    rows = [
        {
            "identity": f"{str(row.get('role') or '')}:{str(row.get('name') or '')}",
            "sha256": str(row.get("sha256") or ""),
        }
        for row in inputs
        if isinstance(row, Mapping)
    ]
    rows.append(
        {
            "identity": "p3-agentic-implementation-candidate",
            "sha256": str(candidate.get("content_digest") or ""),
        }
    )
    p2 = candidate.get("p2_authority")
    if isinstance(p2, Mapping):
        rows.append(
            {
                "identity": "accepted-p2-authority",
                "sha256": str(p2.get("authority_digest") or ""),
            }
        )
    return rows


def p3_decision_subject(
    *,
    candidate: Mapping[str, Any],
    decision_id: str,
    semantic_payload: Mapping[str, Any],
    decision_status: str,
    unresolved_items: Iterable[Mapping[str, Any]],
    claim_ceiling: str,
) -> dict[str, Any]:
    snapshot = candidate.get("input_snapshot")
    return decision_subject_payload(
        phase_id=PHASE_ID,
        decision_kind=DECISION_KIND,
        decision_id=decision_id,
        input_snapshot_digest=str(
            snapshot.get("snapshot_digest") if isinstance(snapshot, Mapping) else ""
        ),
        semantic_payload=semantic_payload,
        decision_status=decision_status,
        unresolved_items=unresolved_items,
        claim_ceiling=claim_ceiling,
    )


def p3_review_subject(
    *,
    candidate: Mapping[str, Any],
    decision_subject: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "artifact": {
            "identity": f"p3-decision-subject:{decision_subject.get('decision_id')}",
            "sha256": canonical_digest(dict(decision_subject)),
        },
        "contract": {"identity": CONTRACT_ID, "sha256": CONTRACT_DIGEST},
        "admitted_context": _context_rows(candidate),
    }


def build_p3_decision_challenge_binding(
    *,
    candidate: Mapping[str, Any],
    decision_subject: Mapping[str, Any],
    challenge: Mapping[str, Any],
) -> dict[str, Any]:
    return build_decision_challenge_binding(
        decision_subject=decision_subject,
        challenge=challenge,
        review_subject=p3_review_subject(candidate=candidate, decision_subject=decision_subject),
    )


def validate_p3_decision_challenge_binding(
    *,
    decision: Mapping[str, Any],
    candidate: Mapping[str, Any],
    required_trigger_ids: Iterable[str],
) -> dict[str, Any]:
    subject = p3_decision_subject(
        candidate=candidate,
        decision_id=str(decision.get("decision_id") or ""),
        semantic_payload=(decision.get("semantic_payload") if isinstance(decision.get("semantic_payload"), Mapping) else {}),
        decision_status=str(decision.get("decision_status") or ""),
        unresolved_items=(decision.get("unresolved_items") if isinstance(decision.get("unresolved_items"), list) else ()),
        claim_ceiling=str(decision.get("claim_ceiling") or ""),
    )
    return validate_decision_challenge_binding(
        decision=decision,
        expected_review_subject=p3_review_subject(candidate=candidate, decision_subject=subject),
        required_trigger_ids=required_trigger_ids,
    )
