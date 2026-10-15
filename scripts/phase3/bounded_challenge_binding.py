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
        "admitted_context": _context_rows(candidate) + [
            {"identity": "p3-t2:" + row["id"], "sha256": canonical_digest(row)}
            for row in decision_subject.get("semantic_payload", {}).get("authority_delta_records", [])
            if row.get("gap_decision_contract") == "p3-gap-decisions-v1" and row.get("level") == "T2"
        ],
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


def p3_gap_review_scope(*, implementation_subject, frozen_facts, records):
    """Extend the original OMR/SQR subject; both reviewers get identical source data.

    No review output is an input here, and no additional review call is scheduled.
    """
    from copy import deepcopy
    from common.agentic_decision_authority import canonical_digest
    from common.p3_gap_records import CONTRACT, validate_gap_record
    rows = [validate_gap_record(row, frozen_facts=frozen_facts) for row in records
            if row.get("gap_decision_contract") == CONTRACT and row.get("level") == "T2"]
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate T2 review identity")
    scope = {"implementation_subject": deepcopy(implementation_subject), "t2_decisions": rows,
             "frozen_basis": {key: deepcopy(frozen_facts[key]) for row in rows for key in
                              (source["id"] for source in row["basis"])},
             "review_rule": "Review T2 reasoning, exact provenance, rule use, new facts and claim ceilings within the existing implementation review. SQR receives the original subject, never OMR findings/results."}
    scope["content_digest"] = canonical_digest(scope)
    return scope


def p3_t2_sqr_metrics(*, scope, receipt):
    """Report observed rejection and missing coverage without treating absence as acceptance."""
    from common.agentic_decision_authority import canonical_digest
    if scope.get("content_digest") != canonical_digest({k:v for k,v in scope.items() if k != "content_digest"}):
        raise ValueError("Review scope digest mismatch")
    expected = {row["id"]: canonical_digest(row) for row in scope["t2_decisions"]}
    reviewed = {}; call_ids = []
    if receipt is not None:
        if (receipt.get("role") != "sqr" or receipt.get("scope_digest") != scope["content_digest"]
                or not receipt.get("call_ids") or not all(isinstance(c,str) and c for c in receipt["call_ids"])):
            raise ValueError("SQR receipt must bind the original scope and actual call identities")
        call_ids = list(receipt["call_ids"])
        for result in receipt.get("decisions", []):
            key = result.get("id")
            if (key not in expected or key in reviewed or result.get("digest") != expected[key]
                    or result.get("verdict") not in {"accepted", "rejected", "review-bound"}
                    or not isinstance(result.get("findings"),list)):
                raise ValueError("SQR decision result identity/digest/verdict is invalid")
            reviewed[key] = result
    rejected = sorted(k for k,v in reviewed.items() if v["verdict"] == "rejected")
    model_new = {row["id"] for row in scope["t2_decisions"]
                 if row.get("rule") == "none" or row.get("new_facts")}
    model_reviewed = sorted(model_new & set(reviewed))
    model_rejected = sorted(model_new & set(rejected))
    model_metrics = {"ids": sorted(model_new), "count": len(model_new),
        "reviewed_count": len(model_reviewed), "rejected_count": len(model_rejected),
        "rejection_rate": len(model_rejected) / len(model_reviewed) if model_reviewed else None,
        "rejected_ids": model_rejected,
        "review_bound_ids": sorted(k for k in model_reviewed if reviewed[k]["verdict"] == "review-bound"),
        "missing_ids": sorted(model_new - set(reviewed))}
    return {"scope_digest": scope["content_digest"], "model_new_t2": model_metrics, "t2_count": len(expected),
            "reviewed_count": len(reviewed), "rejected_count": len(rejected),
            "rejection_rate": len(rejected)/len(reviewed) if reviewed else None,
            "rejected_ids": rejected, "missing_ids": sorted(set(expected)-set(reviewed)),
            "review_bound_ids": sorted(k for k,v in reviewed.items() if v["verdict"] == "review-bound"),
            "decision_results": list(reviewed.values()), "call_ids": call_ids,
            "claim_ceiling": "Observed isolated SQR results only; missing coverage is not accepted, and no automatic role meeting or extra review is authorized."}


def apply_p3_t2_sqr_results(*, records, scope, receipt, applied_surfaces):
    """Bind the existing isolated SQR receipt in the existing decision records.

    The host reports actual already-applied surfaces; no code is applied/reverted
    here, no new decision is issued, and no additional review is scheduled.
    """
    from copy import deepcopy
    from common.agentic_decision_authority import canonical_digest
    from common.p3_gap_records import validate_gap_record
    metrics = p3_t2_sqr_metrics(scope=scope, receipt=receipt)
    originals = {row["id"]: row for row in scope["t2_decisions"]}
    results = {row["id"]: row for row in metrics["decision_results"]}
    if (not isinstance(applied_surfaces, dict) or set(applied_surfaces) != set(originals)
            or any(not isinstance(v, list) or any(not isinstance(s, str) or not s for s in v)
                   for v in applied_surfaces.values())):
        raise ValueError("Report applied surfaces explicitly for every reviewed T2 identity")
    annotated = []; seen = set()
    for row in records:
        value = deepcopy(row); key = row.get("id")
        if key in originals:
            original = {k: v for k, v in row.items() if k != "sqr_review"}
            if key in seen or canonical_digest(original) != canonical_digest(originals[key]):
                raise ValueError("SQR annotation cannot replace or rebind its original decision")
            result = results.get(key)
            review = {"status": result["verdict"] if result else "not-reviewed",
                "scope_digest": scope["content_digest"], "record_digest": canonical_digest(original),
                "call_ids": deepcopy(metrics["call_ids"]),
                "findings": deepcopy(result["findings"]) if result else [],
                "already_applied_surfaces": deepcopy(applied_surfaces[key])}
            if row.get("sqr_review") is not None and row["sqr_review"] != review:
                raise ValueError("A retained SQR annotation is immutable")
            value["sqr_review"] = review
            validate_gap_record(value)
            seen.add(key)
        annotated.append(value)
    if seen != set(originals):
        raise ValueError("SQR scope includes decisions absent from the canonical records")
    return annotated
