"""Bounded fresh-context challenge contract for selected Agentic decisions.

The protocol protects decision integrity without creating product, architecture,
implementation, or closure truth. Workflow selects an explicit phase trigger and
supplies a bounded review unit. A reviewer produces challenge evidence only. The
phase Agentic owner reconciles each material finding and remains the decision
owner.
"""

from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Iterable, Mapping

from common.bounded_agentic_challenge_lineage import (
    FindingLineageError,
    normalize_findings,
    validate_cycle_findings,
)
from common.bounded_agentic_challenge_limits import (
    BoundedChallengeLimitError,
    validate_cycle_limits,
    validate_record_limits,
    validate_review_packet_limits,
)
from common.bounded_agentic_challenge_policy import (
    DEFAULT_EXCLUSIONS,
    PHASE_TRIGGER_MATRIX,
    BoundedChallengePolicyError,
    challenge_required as _policy_challenge_required,
)


BOUNDED_CHALLENGE_SCHEMA = "wff.bounded-agentic-challenge.v1"
PROTOCOL_ID = "claim-extract-challenge-reconcile-stop"
MAX_CHALLENGE_CYCLES = 3

CHALLENGE_MODES = frozenset({
    "fresh-context-isolated",
    "human-independent",
    "cross-model-authorized",
    "tdd-red",
})
FRESH_CONTEXT_BOUNDARIES = {
    "fresh-context-isolated": "no-author-reasoning-context",
    "human-independent": "bounded-human-context",
    "cross-model-authorized": "read-only-external-context",
    "tdd-red": "direct-disproof-test",
}
REVIEWER_KINDS = {
    "fresh-context-isolated": "isolated-reviewer",
    "human-independent": "human-reviewer",
    "cross-model-authorized": "external-read-only-reviewer",
    "tdd-red": "direct-disproof-test",
}
STOP_CONDITIONS = frozenset({
    "no-material-findings",
    "material-findings-resolved",
    "review-bound-explicit",
    "tdd-red-satisfied",
    "max-cycles-escalated",
    "user-override",
})
RESULTING_STATUSES = frozenset({
    "accepted",
    "review-bound",
    "agentic-decision-required",
    "rejected",
})
CROSS_MODEL_STATUSES = frozenset({
    "not-requested",
    "skipped",
    "authorized-complete",
    "failed-visible",
})
class BoundedAgenticChallengeError(ValueError):
    """Raised when the bounded challenge record is missing or dishonest."""


def challenge_required(*, phase_id: str, trigger_id: str, exclusion_id: str = "") -> bool:
    """Compatibility facade over the small explicit policy module."""

    try:
        return _policy_challenge_required(
            phase_id=phase_id,
            trigger_id=trigger_id,
            exclusion_id=exclusion_id,
        )
    except BoundedChallengePolicyError as exc:
        raise BoundedAgenticChallengeError(str(exc)) from exc


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_digest(value: Any) -> str:
    return "sha256:" + sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _digest_valid(value: object) -> bool:
    return bool(re.fullmatch(r"sha256:[0-9a-f]{64}", str(value or "")))


def _content_digest_is_valid(payload: Mapping[str, Any]) -> bool:
    expected = str(payload.get("content_digest") or "")
    body = {key: value for key, value in payload.items() if key != "content_digest"}
    return bool(expected and expected == canonical_digest(body))


def _identity_row(value: Mapping[str, Any], *, label: str) -> dict[str, str]:
    if set(value) != {"identity", "sha256"}:
        raise BoundedAgenticChallengeError(f"{label} identity shape is invalid")
    identity = str(value.get("identity") or "").strip()
    digest = str(value.get("sha256") or "").strip()
    if not identity or not _digest_valid(digest):
        raise BoundedAgenticChallengeError(f"{label} identity or digest is invalid")
    return {"identity": identity, "sha256": digest}


def build_review_packet(
    *,
    artifact_identity: str,
    artifact_digest: str,
    contract_identity: str,
    contract_digest: str,
    admitted_context: Iterable[Mapping[str, Any]],
    unknowns: Iterable[str] = (),
) -> dict[str, Any]:
    packet = {
        "artifact": _identity_row(
            {"identity": artifact_identity, "sha256": artifact_digest}, label="artifact"
        ),
        "contract": _identity_row(
            {"identity": contract_identity, "sha256": contract_digest}, label="contract"
        ),
        "admitted_context": [
            _identity_row(row, label="admitted context") for row in admitted_context
        ],
        "unknowns": sorted({str(item).strip() for item in unknowns if str(item).strip()}),
        "review_instruction": "issues-first-contract-challenge",
    }
    if not packet["admitted_context"]:
        raise BoundedAgenticChallengeError("review packet has no admitted context identities")
    try:
        validate_review_packet_limits(packet)
    except BoundedChallengeLimitError as exc:
        raise BoundedAgenticChallengeError(str(exc)) from exc
    return packet


def build_challenge_cycle(
    *,
    cycle_number: int,
    review_packet: Mapping[str, Any],
    challenge_mode: str,
    reviewer_id: str,
    findings: Iterable[Mapping[str, Any]],
    previous_review_unit_digest: str = "",
    tdd_red_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = dict(review_packet)
    packet_digest = canonical_digest(packet)
    mode = str(challenge_mode or "").strip()
    reviewer = {
        "kind": REVIEWER_KINDS.get(mode, ""),
        "id": str(reviewer_id or "").strip(),
    }
    finding_rows = normalize_findings(
        findings,
        cycle_number=int(cycle_number),
    )
    findings_digest = canonical_digest(finding_rows)
    payload: dict[str, Any] = {
        "cycle_number": int(cycle_number),
        "review_unit_digest": packet_digest,
        "previous_review_unit_digest": str(previous_review_unit_digest or ""),
        "challenge_mode": mode,
        "fresh_context_boundary": FRESH_CONTEXT_BOUNDARIES.get(mode, ""),
        "reviewer": reviewer,
        "review_packet": packet,
        "review_packet_digest": packet_digest,
        "findings": finding_rows,
        "findings_digest": findings_digest,
    }
    if tdd_red_evidence:
        payload["tdd_red_evidence"] = dict(tdd_red_evidence)
    payload["challenge_receipt_digest"] = canonical_digest(
        {
            "review_unit_digest": packet_digest,
            "challenge_mode": mode,
            "fresh_context_boundary": payload["fresh_context_boundary"],
            "reviewer": reviewer,
            "findings_digest": findings_digest,
            "tdd_red_evidence": payload.get("tdd_red_evidence", {}),
        }
    )
    try:
        validate_cycle_limits(payload)
    except BoundedChallengeLimitError as exc:
        raise BoundedAgenticChallengeError(str(exc)) from exc
    return payload


def build_bounded_challenge_record(
    *,
    phase_id: str,
    trigger_ids: Iterable[str],
    owner_id: str,
    claim: str,
    why_it_matters: str,
    cycles: Iterable[Mapping[str, Any]],
    stop_condition: str,
    resulting_decision_status: str,
    remaining_review_bound_items: Iterable[Mapping[str, Any]] = (),
    claim_ceiling: str,
    cross_model: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": BOUNDED_CHALLENGE_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "phase_id": str(phase_id or "").strip().upper(),
        "trigger_ids": sorted({str(item).strip() for item in trigger_ids if str(item).strip()}),
        "claim": {
            "statement": str(claim or "").strip(),
            "why_it_matters": str(why_it_matters or "").strip(),
        },
        "owner": {"kind": "phase-agentic-owner", "id": str(owner_id or "").strip()},
        "reviewer_authority": "challenge-evidence-only",
        "cycles": [dict(row) for row in cycles],
        "stop_condition": str(stop_condition or "").strip(),
        "remaining_review_bound_items": [
            dict(row) for row in remaining_review_bound_items
        ],
        "resulting_decision_status": str(resulting_decision_status or "").strip(),
        "claim_ceiling": str(claim_ceiling or "").strip(),
        "cross_model": dict(cross_model or {"status": "not-requested"}),
    }
    payload["content_digest"] = canonical_digest(payload)
    try:
        validate_record_limits(payload)
    except BoundedChallengeLimitError as exc:
        raise BoundedAgenticChallengeError(str(exc)) from exc
    validate_bounded_challenge(
        payload,
        expected_phase_id=payload["phase_id"],
        expected_owner_id=payload["owner"]["id"],
        accepted_decision=payload["resulting_decision_status"] == "accepted",
    )
    return payload


def build_bounded_challenge_template(
    *,
    phase_id: str,
    trigger_ids: Iterable[str],
    owner_id: str = "host-agent-required",
) -> dict[str, Any]:
    return {
        "schema_version": BOUNDED_CHALLENGE_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "phase_id": str(phase_id or "").strip().upper(),
        "trigger_ids": sorted({str(item).strip() for item in trigger_ids if str(item).strip()}),
        "claim": {
            "statement": "<compact claim about to stand>",
            "why_it_matters": "<downstream failure cost>",
        },
        "owner": {"kind": "phase-agentic-owner", "id": owner_id},
        "reviewer_authority": "challenge-evidence-only",
        "cycles": [
            {
                "cycle_number": 1,
                "review_unit_digest": "<sha256 of bounded reviewer packet>",
                "previous_review_unit_digest": "",
                "challenge_mode": "fresh-context-isolated | human-independent | cross-model-authorized | tdd-red",
                "fresh_context_boundary": "<mode-specific boundary>",
                "reviewer": {"kind": "<mode-specific reviewer kind>", "id": "<reviewer identity>"},
                "review_packet": {
                    "artifact": {"identity": "<artifact>", "sha256": "<sha256>"},
                    "contract": {"identity": "<contract>", "sha256": "<sha256>"},
                    "admitted_context": [{"identity": "<context>", "sha256": "<sha256>"}],
                    "unknowns": [],
                    "review_instruction": "issues-first-contract-challenge",
                },
                "review_packet_digest": "<sha256>",
                "findings": [],
                "findings_digest": "<sha256>",
                "challenge_receipt_digest": "<sha256>",
            }
        ],
        "stop_condition": "<bounded stop condition>",
        "remaining_review_bound_items": [],
        "resulting_decision_status": "agentic-decision-required",
        "claim_ceiling": "<resulting ceiling>",
        "cross_model": {"status": "not-requested"},
    }


def _validate_cross_model(value: Mapping[str, Any]) -> None:
    status = str(value.get("status") or "").strip()
    if status not in CROSS_MODEL_STATUSES:
        raise BoundedAgenticChallengeError("cross-model status is invalid")
    if status == "authorized-complete":
        if not all(
            str(value.get(key) or "").strip()
            for key in ("authorization_ref", "tool", "invocation_digest")
        ):
            raise BoundedAgenticChallengeError(
                "authorized cross-model challenge lacks authorization/tool/invocation identity"
            )
        if not _digest_valid(value.get("invocation_digest")) or value.get("read_only") is not True:
            raise BoundedAgenticChallengeError(
                "authorized cross-model challenge must be digest-bound and read-only"
            )
    if status == "failed-visible" and not str(value.get("failure") or "").strip():
        raise BoundedAgenticChallengeError("cross-model failure must remain visible")


def validate_bounded_challenge(
    record: Mapping[str, Any],
    *,
    expected_phase_id: str,
    expected_trigger_ids: Iterable[str] = (),
    expected_owner_id: str = "",
    accepted_decision: bool = True,
) -> None:
    if not isinstance(record, Mapping):
        raise BoundedAgenticChallengeError("bounded challenge record is missing")
    try:
        validate_record_limits(record)
    except BoundedChallengeLimitError as exc:
        raise BoundedAgenticChallengeError(str(exc)) from exc
    if record.get("schema_version") != BOUNDED_CHALLENGE_SCHEMA:
        raise BoundedAgenticChallengeError("bounded challenge schema is invalid")
    if record.get("protocol_id") != PROTOCOL_ID or not _content_digest_is_valid(record):
        raise BoundedAgenticChallengeError("bounded challenge digest or protocol identity is invalid")
    phase = str(record.get("phase_id") or "").strip().upper()
    if phase != str(expected_phase_id or "").strip().upper():
        raise BoundedAgenticChallengeError("bounded challenge phase is invalid")
    trigger_ids = record.get("trigger_ids")
    if not isinstance(trigger_ids, list) or not trigger_ids:
        raise BoundedAgenticChallengeError("bounded challenge has no explicit trigger")
    normalized_triggers = {str(item).strip() for item in trigger_ids if str(item).strip()}
    for trigger in normalized_triggers:
        challenge_required(phase_id=phase, trigger_id=trigger)
    expected = {str(item).strip() for item in expected_trigger_ids if str(item).strip()}
    if expected and not expected.issubset(normalized_triggers):
        raise BoundedAgenticChallengeError(
            "bounded challenge misses required phase triggers: " + ", ".join(sorted(expected - normalized_triggers))
        )
    claim = record.get("claim")
    if not isinstance(claim, Mapping) or not all(
        str(claim.get(key) or "").strip() for key in ("statement", "why_it_matters")
    ):
        raise BoundedAgenticChallengeError("CLAIM or WHY IT MATTERS is missing")
    owner = record.get("owner")
    if not isinstance(owner, Mapping) or owner.get("kind") != "phase-agentic-owner" or not str(owner.get("id") or "").strip():
        raise BoundedAgenticChallengeError("bounded challenge owner is invalid")
    if expected_owner_id and str(owner.get("id") or "") != expected_owner_id:
        raise BoundedAgenticChallengeError("bounded challenge owner differs from decision owner")
    if record.get("reviewer_authority") != "challenge-evidence-only":
        raise BoundedAgenticChallengeError("reviewer cannot become phase decision authority")

    cycles = record.get("cycles")
    if not isinstance(cycles, list) or not 1 <= len(cycles) <= MAX_CHALLENGE_CYCLES:
        raise BoundedAgenticChallengeError("bounded challenge cycle count must be 1..3")
    previous_digest = ""
    final_material_rows: list[dict[str, str]] = []
    lineage_origins: dict[str, int] = {}
    unresolved_lineage: dict[str, str] = {}
    any_tdd_red = False
    for expected_number, raw_cycle in enumerate(cycles, start=1):
        if not isinstance(raw_cycle, Mapping) or raw_cycle.get("cycle_number") != expected_number:
            raise BoundedAgenticChallengeError("bounded challenge cycle numbering is invalid")
        mode = str(raw_cycle.get("challenge_mode") or "").strip()
        if mode not in CHALLENGE_MODES:
            raise BoundedAgenticChallengeError("bounded challenge mode is invalid")
        if raw_cycle.get("fresh_context_boundary") != FRESH_CONTEXT_BOUNDARIES[mode]:
            raise BoundedAgenticChallengeError("fresh-context boundary does not match challenge mode")
        reviewer = raw_cycle.get("reviewer")
        if (
            not isinstance(reviewer, Mapping)
            or reviewer.get("kind") != REVIEWER_KINDS[mode]
            or not str(reviewer.get("id") or "").strip()
        ):
            raise BoundedAgenticChallengeError("challenge reviewer identity is invalid")
        packet = raw_cycle.get("review_packet")
        if not isinstance(packet, Mapping):
            raise BoundedAgenticChallengeError("review packet is invalid")
        try:
            validate_review_packet_limits(packet)
        except BoundedChallengeLimitError as exc:
            raise BoundedAgenticChallengeError(str(exc)) from exc
        _identity_row(packet.get("artifact", {}), label="artifact")
        _identity_row(packet.get("contract", {}), label="contract")
        contexts = packet.get("admitted_context")
        if not isinstance(contexts, list) or not contexts:
            raise BoundedAgenticChallengeError("review packet has no admitted context")
        for row in contexts:
            if not isinstance(row, Mapping):
                raise BoundedAgenticChallengeError("review packet context row is invalid")
            _identity_row(row, label="admitted context")
        if packet.get("review_instruction") != "issues-first-contract-challenge":
            raise BoundedAgenticChallengeError("reviewer prompt is not issues-first")
        digest = canonical_digest(packet)
        if raw_cycle.get("review_packet_digest") != digest or raw_cycle.get("review_unit_digest") != digest:
            raise BoundedAgenticChallengeError("review packet digest is invalid")
        declared_previous = str(raw_cycle.get("previous_review_unit_digest") or "")
        if expected_number == 1:
            if declared_previous:
                raise BoundedAgenticChallengeError("first challenge cycle cannot declare a previous unit")
        else:
            if declared_previous != previous_digest:
                raise BoundedAgenticChallengeError("challenge cycle does not bind the previous review unit")
            if digest == previous_digest:
                raise BoundedAgenticChallengeError("unchanged artifact/contract/context cannot be re-reviewed")
        previous_digest = digest
        findings = raw_cycle.get("findings")
        if not isinstance(findings, list):
            raise BoundedAgenticChallengeError("challenge findings must be a list")
        findings_digest = canonical_digest(findings)
        if raw_cycle.get("findings_digest") != findings_digest:
            raise BoundedAgenticChallengeError("challenge findings digest is invalid")
        expected_receipt_digest = canonical_digest(
            {
                "review_unit_digest": digest,
                "challenge_mode": mode,
                "fresh_context_boundary": raw_cycle.get("fresh_context_boundary"),
                "reviewer": dict(reviewer),
                "findings_digest": findings_digest,
                "tdd_red_evidence": raw_cycle.get("tdd_red_evidence", {}),
            }
        )
        if raw_cycle.get("challenge_receipt_digest") != expected_receipt_digest:
            raise BoundedAgenticChallengeError("challenge receipt digest is invalid")
        try:
            material_rows, unresolved_lineage = validate_cycle_findings(
                findings=findings,
                cycle_number=expected_number,
                lineage_origins=lineage_origins,
                unresolved_lineage=unresolved_lineage,
            )
        except FindingLineageError as exc:
            raise BoundedAgenticChallengeError(str(exc)) from exc
        if expected_number == len(cycles):
            final_material_rows = material_rows
        if mode == "tdd-red":
            any_tdd_red = True
            evidence = raw_cycle.get("tdd_red_evidence")
            if not isinstance(evidence, Mapping) or not all(
                str(evidence.get(key) or "").strip()
                for key in ("test_identity", "failing_evidence_digest", "behavioral_claim")
            ):
                raise BoundedAgenticChallengeError("TDD RED challenge lacks direct disproof evidence")
            if not _digest_valid(evidence.get("failing_evidence_digest")):
                raise BoundedAgenticChallengeError("TDD RED evidence digest is invalid")

    stop = str(record.get("stop_condition") or "").strip()
    status = str(record.get("resulting_decision_status") or "").strip()
    if stop not in STOP_CONDITIONS or status not in RESULTING_STATUSES:
        raise BoundedAgenticChallengeError("bounded challenge stop or resulting status is invalid")
    remaining = record.get("remaining_review_bound_items")
    if not isinstance(remaining, list):
        raise BoundedAgenticChallengeError("remaining review-bound items must be a list")
    remaining_ids: set[str] = set()
    for row in remaining:
        if not isinstance(row, Mapping) or not all(
            str(row.get(key) or "").strip()
            for key in ("finding_id", "reason", "owner", "claim_ceiling")
        ):
            raise BoundedAgenticChallengeError("remaining review-bound item is incomplete")
        remaining_ids.add(str(row.get("finding_id")))
    final_unresolved_ids = {
        row["finding_id"]
        for row in final_material_rows
        if row["lineage_status"] in {"opened", "carried", "review-bound"}
    }
    if any(
        row["disposition"] == "valid-actionable"
        and row["lineage_status"] in {"opened", "carried"}
        for row in final_material_rows
    ):
        raise BoundedAgenticChallengeError("a changed artifact must be re-challenged before the decision stands")
    if any(
        row["disposition"] == "contract-or-context-insufficient"
        for row in final_material_rows
    ) and status == "accepted":
        raise BoundedAgenticChallengeError("insufficient contract/context cannot produce an accepted decision")
    review_bound_ids = {
        row["finding_id"]
        for row in final_material_rows
        if row["lineage_status"] == "review-bound"
    }
    if review_bound_ids and not review_bound_ids.issubset(remaining_ids):
        raise BoundedAgenticChallengeError("review-bound findings are hidden from the final decision")
    if final_unresolved_ids - remaining_ids:
        raise BoundedAgenticChallengeError("unresolved findings are missing from the final decision surface")
    if stop == "no-material-findings" and final_material_rows:
        raise BoundedAgenticChallengeError("no-material-findings stop contradicts material findings")
    if stop == "material-findings-resolved" and final_unresolved_ids:
        raise BoundedAgenticChallengeError("material findings are not fully resolved")
    if stop == "review-bound-explicit" and not remaining:
        raise BoundedAgenticChallengeError("review-bound stop has no visible remaining item")
    if stop == "tdd-red-satisfied" and not any_tdd_red:
        raise BoundedAgenticChallengeError("TDD RED stop has no RED challenge cycle")
    if stop == "max-cycles-escalated":
        if len(cycles) != MAX_CHALLENGE_CYCLES or status == "accepted":
            raise BoundedAgenticChallengeError("max-cycle escalation cannot silently accept the decision")
    if accepted_decision and status != "accepted":
        raise BoundedAgenticChallengeError("accepted phase decision lacks an accepted challenge result")
    if not str(record.get("claim_ceiling") or "").strip():
        raise BoundedAgenticChallengeError("bounded challenge claim ceiling is missing")
    cross_model = record.get("cross_model")
    if not isinstance(cross_model, Mapping):
        raise BoundedAgenticChallengeError("cross-model policy record is missing")
    _validate_cross_model(cross_model)
    if any(cycle.get("challenge_mode") == "cross-model-authorized" for cycle in cycles):
        if cross_model.get("status") != "authorized-complete":
            raise BoundedAgenticChallengeError("cross-model cycle lacks explicit authorized completion")


def require_bounded_challenge(
    decision: Mapping[str, Any],
    *,
    expected_phase_id: str,
    required_trigger_ids: Iterable[str],
) -> dict[str, Any]:
    owner = decision.get("decision_owner")
    owner_id = str(owner.get("id") or "") if isinstance(owner, Mapping) else ""
    record = decision.get("bounded_challenge")
    if not isinstance(record, Mapping):
        raise BoundedAgenticChallengeError("high-risk Agentic decision lacks bounded challenge evidence")
    validate_bounded_challenge(
        record,
        expected_phase_id=expected_phase_id,
        expected_trigger_ids=required_trigger_ids,
        expected_owner_id=owner_id,
        accepted_decision=str(decision.get("decision_status") or "") == "accepted",
    )
    return dict(record)


def challenge_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    cycles = record.get("cycles") if isinstance(record.get("cycles"), list) else []
    return {
        "protocol_id": str(record.get("protocol_id") or ""),
        "trigger_ids": list(record.get("trigger_ids") or []),
        "cycle_count": len(cycles),
        "challenge_modes": sorted(
            {str(row.get("challenge_mode") or "") for row in cycles if isinstance(row, Mapping)}
        ),
        "stop_condition": str(record.get("stop_condition") or ""),
        "remaining_review_bound_count": len(record.get("remaining_review_bound_items") or []),
        "resulting_decision_status": str(record.get("resulting_decision_status") or ""),
        "claim_ceiling": str(record.get("claim_ceiling") or ""),
        "cross_model_status": str((record.get("cross_model") or {}).get("status") or ""),
        "content_digest": str(record.get("content_digest") or ""),
    }
