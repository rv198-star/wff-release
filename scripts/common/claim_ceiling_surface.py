#!/usr/bin/env python3
"""Shared claim-ceiling readers for cross-phase and human-review surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


NON_READY_STATES = {
    "",
    "unknown",
    "blocked",
    "foundation-ready",
    "implementation-in-progress",
    "implementation-ready",
    "artifact-quality-review-bound",
    "trace-review-bound",
    "test-independence-review-bound",
    "review-bound",
    "testing-validation-complete-with-review-bound-items",
    "testing-validation-complete-with-mock-dependency",
    "testing-validation-return-required",
}

PHASE3_VALIDATION_ENTRY_STATES = {
    "delivery-ready",
    "implementation-ready",
    "artifact-quality-review-bound",
    "trace-review-bound",
    "test-independence-review-bound",
}

PHASE4_REVIEW_BOUND_COMPLETION_STATES = {
    "testing-validation-complete",
    "testing-validation-complete-with-review-bound-items",
    "testing-validation-complete-with-mock-dependency",
}


CLAIM_CEILING_STATE_RANK = {
    "": 0,
    "unknown": 0,
    "blocked": 0,
    "testing-validation-return-required": 0,
    "foundation-ready": 1,
    "implementation-in-progress": 2,
    "implementation-ready": 3,
    "artifact-quality-review-bound": 3,
    "trace-review-bound": 3,
    "test-independence-review-bound": 3,
    "review-bound": 3,
    "testing-validation-complete-with-review-bound-items": 3,
    "testing-validation-complete-with-mock-dependency": 3,
    "delivery-ready": 4,
    "testing-validation-complete": 4,
}

CLAIM_CEILING_SOURCE_PRIORITY = {
    "phase3-delivery-gate.json": 0,
    "phase4-delivery-gate.json": 0,
    "phase-verdict.json": 1,
    "phase4-quality-check.json": 2,
    ".phase4-contract/phase4-claim-control-report.json": 3,
}


READY_CLAIM_CONTROL_TOKENS = {
    "claim-controlled",
}


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def read_claim_ceiling_report(root: str | Path) -> dict[str, Any]:
    """Read the canonical claim ceiling report from a phase output root.

    This function only surfaces an existing machine report. It must not invent
    semantic truth or upgrade a phase verdict.
    """

    root_path = Path(root)
    candidate_payloads: list[tuple[str, dict[str, Any]]] = []
    for relative in (
        "phase-verdict.json",
        "phase3-delivery-gate.json",
        "phase4-delivery-gate.json",
        "phase4-quality-check.json",
    ):
        payload = load_json_object(root_path / relative)
        if payload:
            candidate_payloads.append((relative, payload))

    reports: list[dict[str, Any]] = []
    for source, payload in candidate_payloads:
        report = payload.get("claim_ceiling_report")
        if isinstance(report, dict):
            reports.append(normalize_claim_ceiling_report(report, source=source))

    phase4_control = load_json_object(root_path / ".phase4-contract" / "phase4-claim-control-report.json")
    if phase4_control:
        reports.append(
            normalize_claim_ceiling_report(
                {
                    "artifact_kind": "phase4-claim-control-report",
                    "requested_formal_state": "",
                    "resolved_formal_state": "testing-validation-complete"
                    if phase4_control.get("overall_status") == "pass"
                    else "review-bound",
                    "claim_ceiling": phase4_control.get("claim_ceiling") or "review-bound",
                    "blocking_delivery_ready": phase4_control.get("overall_status") != "pass",
                    "reasons": [
                        {
                            "reason": "phase4_claim_control_not_pass",
                            "signal": "phase4_claim_control",
                            "detail": "Phase-4 claim-control report is not pass.",
                            "ceiling": "review-bound",
                        }
                    ]
                    if phase4_control.get("overall_status") != "pass"
                    else [],
                    "inputs": {"overall_status": phase4_control.get("overall_status") or "unknown"},
                    "policy": "Phase-4 may consume but not upgrade upstream claim ceilings.",
                },
                source=".phase4-contract/phase4-claim-control-report.json",
            )
        )

    if reports:
        return weakest_claim_ceiling_report(reports)

    return {
        "artifact_kind": "claim-ceiling-report.absent",
        "present": False,
        "source": "",
        "requested_formal_state": "",
        "resolved_formal_state": "unknown",
        "claim_ceiling": "unknown",
        "blocking_delivery_ready": True,
        "reasons": [
            {
                "reason": "claim_ceiling_report_missing",
                "signal": "claim_ceiling_report",
                "detail": "No machine-readable claim ceiling report was found.",
                "ceiling": "unknown",
            }
        ],
        "inputs": {},
        "policy": "Missing claim ceiling evidence cannot be upgraded by human or downstream review.",
    }


def normalize_formal_state_token(raw: Any) -> str:
    value = str(raw or "").strip()
    normalized = value.lower()
    if not normalized:
        return ""
    if normalized in CLAIM_CEILING_STATE_RANK:
        return normalized
    if normalized.startswith("blocked"):
        return "blocked"
    if normalized.startswith("review-bound"):
        return "review-bound"
    if normalized.startswith("return-required"):
        return "testing-validation-return-required"
    if normalized.startswith("testing-validation-return-required"):
        return "testing-validation-return-required"
    if normalized.startswith("testing-validation-complete-with-review-bound-items"):
        return "testing-validation-complete-with-review-bound-items"
    if normalized.startswith("testing-validation-complete-with-mock-dependency"):
        return "testing-validation-complete-with-mock-dependency"
    if normalized.startswith("testing-validation-complete"):
        return "testing-validation-complete"
    if normalized.startswith("delivery-ready"):
        return "delivery-ready"
    if normalized.startswith("implementation-ready"):
        return "implementation-ready"
    if normalized.startswith("implementation-in-progress"):
        return "implementation-in-progress"
    if normalized.startswith("foundation-ready"):
        return "foundation-ready"
    if normalized in READY_CLAIM_CONTROL_TOKENS:
        return ""
    return "unknown"


def _state_rank(state: str) -> int:
    return CLAIM_CEILING_STATE_RANK.get(state, 2)


def _report_effective_state(report: dict[str, Any]) -> str:
    resolved_state = normalize_formal_state_token(report.get("resolved_formal_state"))
    claim_state = normalize_formal_state_token(report.get("claim_ceiling"))
    states = [state for state in (resolved_state, claim_state) if state]
    if not states:
        return "unknown"
    return min(states, key=_state_rank)


def _claim_ceiling_rank(report: dict[str, Any]) -> int:
    return _state_rank(_report_effective_state(report))


def weakest_claim_ceiling_report(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the most restrictive visible machine ceiling report.

    Multiple phase artifacts can carry claim-ceiling copies. Downstream readers
    must treat disagreement as a cap, not as permission to pick the best-looking
    source.
    """

    normalized_reports = [report for report in reports if isinstance(report, dict)]
    if not normalized_reports:
        return {}
    return min(
        normalized_reports,
        key=lambda report: (
            _claim_ceiling_rank(report),
            not claim_ceiling_blocks_ready(report),
            CLAIM_CEILING_SOURCE_PRIORITY.get(str(report.get("source") or ""), 9),
        ),
    )


def normalize_claim_ceiling_report(report: dict[str, Any], *, source: str) -> dict[str, Any]:
    raw_resolved = str(report.get("resolved_formal_state") or "").strip()
    raw_claim_ceiling = str(report.get("claim_ceiling") or "").strip()
    resolved_candidate = normalize_formal_state_token(raw_resolved)
    claim_candidate = normalize_formal_state_token(raw_claim_ceiling)
    resolved = _report_effective_state(report)
    requested = str(report.get("requested_formal_state") or "").strip()
    reasons = list(report.get("reasons") if isinstance(report.get("reasons"), list) else [])
    if (
        claim_candidate
        and _state_rank(claim_candidate) < _state_rank(resolved_candidate or "unknown")
        and not any(row.get("reason") == "claim_ceiling_token_blocks_ready" for row in reasons if isinstance(row, dict))
    ):
        reasons.append(
            {
                "reason": "claim_ceiling_token_blocks_ready",
                "signal": "claim_ceiling",
                "detail": f"Claim ceiling token `{raw_claim_ceiling}` is weaker than resolved formal state `{raw_resolved or 'unknown'}`.",
                "ceiling": claim_candidate,
            }
        )
    blocking = bool(report.get("blocking_delivery_ready")) or resolved in NON_READY_STATES
    return {
        **report,
        "present": True,
        "source": source,
        "requested_formal_state": requested,
        "resolved_formal_state": resolved or "unknown",
        "claim_ceiling": raw_claim_ceiling or resolved or "unknown",
        "blocking_delivery_ready": blocking,
        "reasons": reasons,
        "policy": str(
            report.get("policy")
            or "Human/downstream review may confirm or lower this ceiling, but must not upgrade it."
        ),
    }


def claim_ceiling_blocks_ready(report: dict[str, Any]) -> bool:
    if not report:
        return True
    return bool(report.get("blocking_delivery_ready")) or _report_effective_state(report) in NON_READY_STATES


def claim_ceiling_allows_phase4_validation_entry(report: dict[str, Any]) -> bool:
    """Return whether a capped Phase-3 package may still enter bounded Phase-4 validation."""

    if not report:
        return False
    return _report_effective_state(report) in PHASE3_VALIDATION_ENTRY_STATES


def claim_ceiling_allows_review_bound_completion(report: dict[str, Any]) -> bool:
    """Return whether a capped Phase-4 result is a review-bound completion, not a return."""

    if not report:
        return False
    return _report_effective_state(report) in PHASE4_REVIEW_BOUND_COMPLETION_STATES
