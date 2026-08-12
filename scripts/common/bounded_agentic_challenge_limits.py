"""Exact shape and practical size budgets for bounded challenge records."""

from __future__ import annotations

import json
from typing import Any, Mapping


MAX_REVIEW_PACKET_BYTES = 64 * 1024
MAX_RECORD_BYTES = 256 * 1024
MAX_CONTEXT_ITEMS = 20
MAX_UNKNOWNS = 50
MAX_FINDINGS_PER_CYCLE = 100
MAX_REMAINING_ITEMS = 100
MAX_TRIGGER_IDS = 8
MAX_IDENTITY_CHARS = 512
MAX_SHORT_TEXT_CHARS = 1024
MAX_LONG_TEXT_CHARS = 4096

REVIEW_PACKET_KEYS = frozenset(
    {"artifact", "contract", "admitted_context", "unknowns", "review_instruction"}
)
IDENTITY_KEYS = frozenset({"identity", "sha256"})
REVIEWER_KEYS = frozenset({"kind", "id"})
CLAIM_KEYS = frozenset({"statement", "why_it_matters"})
OWNER_KEYS = frozenset({"kind", "id"})
FINDING_REQUIRED_KEYS = frozenset(
    {
        "finding_id",
        "materiality",
        "statement",
        "disposition",
        "owner_rationale",
        "artifact_changed",
        "origin_cycle",
        "prior_finding_id",
        "lineage_status",
    }
)
FINDING_OPTIONAL_KEYS = frozenset({"resolution_evidence_digest"})
CYCLE_REQUIRED_KEYS = frozenset(
    {
        "cycle_number",
        "review_unit_digest",
        "previous_review_unit_digest",
        "challenge_mode",
        "fresh_context_boundary",
        "reviewer",
        "review_packet",
        "review_packet_digest",
        "findings",
        "findings_digest",
        "challenge_receipt_digest",
    }
)
CYCLE_OPTIONAL_KEYS = frozenset({"tdd_red_evidence"})
TDD_RED_KEYS = frozenset(
    {"test_identity", "failing_evidence_digest", "behavioral_claim"}
)
REMAINING_ITEM_KEYS = frozenset(
    {"finding_id", "reason", "owner", "claim_ceiling"}
)
RECORD_KEYS = frozenset(
    {
        "schema_version",
        "protocol_id",
        "phase_id",
        "trigger_ids",
        "claim",
        "owner",
        "reviewer_authority",
        "cycles",
        "stop_condition",
        "remaining_review_bound_items",
        "resulting_decision_status",
        "claim_ceiling",
        "cross_model",
        "content_digest",
    }
)


class BoundedChallengeLimitError(ValueError):
    """Raised when a review unit is not actually bounded."""


def canonical_size(value: Any) -> int:
    return len(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def require_exact_keys(
    value: Mapping[str, Any],
    *,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
    label: str,
) -> None:
    actual = set(value)
    missing = required - actual
    unknown = actual - required - optional
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unknown:
            details.append("unknown=" + ",".join(sorted(unknown)))
        raise BoundedChallengeLimitError(
            f"{label} shape is invalid: " + "; ".join(details)
        )


def require_text(
    value: object,
    *,
    label: str,
    maximum: int,
    allow_empty: bool = False,
    single_line: bool = False,
) -> str:
    text = str(value or "")
    if not allow_empty and not text.strip():
        raise BoundedChallengeLimitError(f"{label} is empty")
    if len(text) > maximum:
        raise BoundedChallengeLimitError(
            f"{label} exceeds {maximum} characters"
        )
    if single_line and ("\n" in text or "\r" in text):
        raise BoundedChallengeLimitError(f"{label} must be single-line")
    return text


def validate_identity_shape(value: Mapping[str, Any], *, label: str) -> None:
    require_exact_keys(value, required=IDENTITY_KEYS, label=label)
    require_text(
        value.get("identity"),
        label=f"{label}.identity",
        maximum=MAX_IDENTITY_CHARS,
        single_line=True,
    )
    digest = require_text(
        value.get("sha256"),
        label=f"{label}.sha256",
        maximum=71,
        single_line=True,
    )
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise BoundedChallengeLimitError(f"{label}.sha256 is invalid")


def validate_review_packet_limits(packet: Mapping[str, Any]) -> None:
    require_exact_keys(packet, required=REVIEW_PACKET_KEYS, label="review packet")
    validate_identity_shape(packet.get("artifact", {}), label="review packet artifact")
    validate_identity_shape(packet.get("contract", {}), label="review packet contract")
    contexts = packet.get("admitted_context")
    if not isinstance(contexts, list) or not contexts:
        raise BoundedChallengeLimitError("review packet has no admitted context")
    if len(contexts) > MAX_CONTEXT_ITEMS:
        raise BoundedChallengeLimitError(
            f"review packet exceeds {MAX_CONTEXT_ITEMS} context identities"
        )
    for index, row in enumerate(contexts):
        if not isinstance(row, Mapping):
            raise BoundedChallengeLimitError(
                "review packet context row is invalid"
            )
        validate_identity_shape(row, label=f"review packet context[{index}]")
    unknowns = packet.get("unknowns")
    if not isinstance(unknowns, list):
        raise BoundedChallengeLimitError("review packet unknowns must be a list")
    if len(unknowns) > MAX_UNKNOWNS:
        raise BoundedChallengeLimitError(
            f"review packet exceeds {MAX_UNKNOWNS} unknowns"
        )
    for index, item in enumerate(unknowns):
        require_text(
            item,
            label=f"review packet unknowns[{index}]",
            maximum=MAX_SHORT_TEXT_CHARS,
        )
    instruction = require_text(
        packet.get("review_instruction"),
        label="review packet instruction",
        maximum=MAX_IDENTITY_CHARS,
        single_line=True,
    )
    if instruction != "issues-first-contract-challenge":
        raise BoundedChallengeLimitError(
            "review packet instruction is not the bounded issues-first contract"
        )
    if canonical_size(packet) > MAX_REVIEW_PACKET_BYTES:
        raise BoundedChallengeLimitError(
            f"review packet exceeds {MAX_REVIEW_PACKET_BYTES} bytes"
        )


def validate_finding_limits(finding: Mapping[str, Any], *, index: int) -> None:
    require_exact_keys(
        finding,
        required=FINDING_REQUIRED_KEYS,
        optional=FINDING_OPTIONAL_KEYS,
        label=f"finding[{index}]",
    )
    for key in ("finding_id", "materiality", "disposition", "lineage_status"):
        require_text(
            finding.get(key),
            label=f"finding[{index}].{key}",
            maximum=MAX_IDENTITY_CHARS,
            single_line=True,
        )
    require_text(
        finding.get("prior_finding_id"),
        label=f"finding[{index}].prior_finding_id",
        maximum=MAX_IDENTITY_CHARS,
        allow_empty=True,
        single_line=True,
    )
    require_text(
        finding.get("statement"),
        label=f"finding[{index}].statement",
        maximum=MAX_LONG_TEXT_CHARS,
    )
    require_text(
        finding.get("owner_rationale"),
        label=f"finding[{index}].owner_rationale",
        maximum=MAX_LONG_TEXT_CHARS,
    )
    if not isinstance(finding.get("artifact_changed"), bool):
        raise BoundedChallengeLimitError(
            f"finding[{index}].artifact_changed must be boolean"
        )
    if not isinstance(finding.get("origin_cycle"), int):
        raise BoundedChallengeLimitError(
            f"finding[{index}].origin_cycle must be integer"
        )
    if "resolution_evidence_digest" in finding:
        digest = require_text(
            finding.get("resolution_evidence_digest"),
            label=f"finding[{index}].resolution_evidence_digest",
            maximum=71,
            single_line=True,
        )
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise BoundedChallengeLimitError(
                f"finding[{index}].resolution_evidence_digest is invalid"
            )


def validate_cycle_limits(cycle: Mapping[str, Any]) -> None:
    require_exact_keys(
        cycle,
        required=CYCLE_REQUIRED_KEYS,
        optional=CYCLE_OPTIONAL_KEYS,
        label="challenge cycle",
    )
    reviewer = cycle.get("reviewer")
    if not isinstance(reviewer, Mapping):
        raise BoundedChallengeLimitError("challenge reviewer is invalid")
    require_exact_keys(reviewer, required=REVIEWER_KEYS, label="challenge reviewer")
    for key in ("kind", "id"):
        require_text(
            reviewer.get(key),
            label=f"challenge reviewer.{key}",
            maximum=MAX_IDENTITY_CHARS,
            single_line=True,
        )
    packet = cycle.get("review_packet")
    if not isinstance(packet, Mapping):
        raise BoundedChallengeLimitError("challenge review packet is invalid")
    validate_review_packet_limits(packet)
    findings = cycle.get("findings")
    if not isinstance(findings, list):
        raise BoundedChallengeLimitError("challenge findings must be a list")
    if len(findings) > MAX_FINDINGS_PER_CYCLE:
        raise BoundedChallengeLimitError(
            f"challenge cycle exceeds {MAX_FINDINGS_PER_CYCLE} findings"
        )
    for index, finding in enumerate(findings):
        if not isinstance(finding, Mapping):
            raise BoundedChallengeLimitError(f"finding[{index}] is invalid")
        validate_finding_limits(finding, index=index)
    if "tdd_red_evidence" in cycle:
        evidence = cycle.get("tdd_red_evidence")
        if not isinstance(evidence, Mapping):
            raise BoundedChallengeLimitError("TDD RED evidence is invalid")
        require_exact_keys(evidence, required=TDD_RED_KEYS, label="TDD RED evidence")
        require_text(
            evidence.get("test_identity"),
            label="TDD RED test identity",
            maximum=MAX_IDENTITY_CHARS,
            single_line=True,
        )
        require_text(
            evidence.get("behavioral_claim"),
            label="TDD RED behavioral claim",
            maximum=MAX_LONG_TEXT_CHARS,
        )


def validate_cross_model_limits(value: Mapping[str, Any]) -> None:
    status = str(value.get("status") or "")
    allowed_by_status = {
        "not-requested": frozenset({"status"}),
        "skipped": frozenset({"status", "reason"}),
        "authorized-complete": frozenset(
            {"status", "authorization_ref", "tool", "invocation_digest", "read_only"}
        ),
        "failed-visible": frozenset({"status", "failure"}),
    }
    allowed = allowed_by_status.get(status)
    if allowed is None:
        raise BoundedChallengeLimitError("cross-model status is invalid")
    require_exact_keys(value, required=allowed, label="cross-model record")
    for key, item in value.items():
        if key == "read_only":
            if not isinstance(item, bool):
                raise BoundedChallengeLimitError(
                    "cross-model read_only must be boolean"
                )
            continue
        require_text(
            item,
            label=f"cross-model.{key}",
            maximum=(
                MAX_LONG_TEXT_CHARS if key == "failure" else MAX_IDENTITY_CHARS
            ),
            allow_empty=key == "reason",
            single_line=key != "failure",
        )


def validate_record_limits(record: Mapping[str, Any]) -> None:
    require_exact_keys(record, required=RECORD_KEYS, label="bounded challenge record")
    claim = record.get("claim")
    if not isinstance(claim, Mapping):
        raise BoundedChallengeLimitError("bounded challenge CLAIM is invalid")
    require_exact_keys(claim, required=CLAIM_KEYS, label="bounded challenge CLAIM")
    require_text(
        claim.get("statement"),
        label="CLAIM statement",
        maximum=MAX_LONG_TEXT_CHARS,
    )
    require_text(
        claim.get("why_it_matters"),
        label="WHY IT MATTERS",
        maximum=MAX_LONG_TEXT_CHARS,
    )
    owner = record.get("owner")
    if not isinstance(owner, Mapping):
        raise BoundedChallengeLimitError("bounded challenge owner is invalid")
    require_exact_keys(owner, required=OWNER_KEYS, label="bounded challenge owner")
    for key in ("kind", "id"):
        require_text(
            owner.get(key),
            label=f"bounded challenge owner.{key}",
            maximum=MAX_IDENTITY_CHARS,
            single_line=True,
        )
    triggers = record.get("trigger_ids")
    if not isinstance(triggers, list) or not triggers:
        raise BoundedChallengeLimitError("bounded challenge trigger_ids are invalid")
    if len(triggers) > MAX_TRIGGER_IDS:
        raise BoundedChallengeLimitError(
            f"bounded challenge exceeds {MAX_TRIGGER_IDS} triggers"
        )
    for index, trigger in enumerate(triggers):
        require_text(
            trigger,
            label=f"trigger_ids[{index}]",
            maximum=MAX_IDENTITY_CHARS,
            single_line=True,
        )
    cycles = record.get("cycles")
    if not isinstance(cycles, list):
        raise BoundedChallengeLimitError("bounded challenge cycles are invalid")
    for cycle in cycles:
        if not isinstance(cycle, Mapping):
            raise BoundedChallengeLimitError("bounded challenge cycle is invalid")
        validate_cycle_limits(cycle)
    remaining = record.get("remaining_review_bound_items")
    if not isinstance(remaining, list):
        raise BoundedChallengeLimitError(
            "remaining review-bound items must be a list"
        )
    if len(remaining) > MAX_REMAINING_ITEMS:
        raise BoundedChallengeLimitError(
            f"bounded challenge exceeds {MAX_REMAINING_ITEMS} remaining items"
        )
    for index, item in enumerate(remaining):
        if not isinstance(item, Mapping):
            raise BoundedChallengeLimitError(
                f"remaining item[{index}] is invalid"
            )
        require_exact_keys(
            item,
            required=REMAINING_ITEM_KEYS,
            label=f"remaining item[{index}]",
        )
        for key in REMAINING_ITEM_KEYS:
            require_text(
                item.get(key),
                label=f"remaining item[{index}].{key}",
                maximum=(
                    MAX_LONG_TEXT_CHARS
                    if key in {"reason", "claim_ceiling"}
                    else MAX_IDENTITY_CHARS
                ),
                single_line=key not in {"reason", "claim_ceiling"},
            )
    cross_model = record.get("cross_model")
    if not isinstance(cross_model, Mapping):
        raise BoundedChallengeLimitError("cross-model record is invalid")
    validate_cross_model_limits(cross_model)
    if canonical_size(record) > MAX_RECORD_BYTES:
        raise BoundedChallengeLimitError(
            f"bounded challenge record exceeds {MAX_RECORD_BYTES} bytes"
        )
