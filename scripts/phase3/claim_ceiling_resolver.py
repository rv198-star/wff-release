#!/usr/bin/env python3
"""Resolve the Phase-3 formal-state claim ceiling from independent evidence.

This module owns formal-state downgrades only. It does not create business
truth, approve implementations, or replace human review.
"""

from __future__ import annotations

from typing import Any


FORMAL_STATE_RANK = {
    "blocked": 0,
    "foundation-ready": 1,
    "implementation-in-progress": 2,
    "implementation-ready": 3,
    "artifact-quality-review-bound": 3,
    "trace-review-bound": 3,
    "test-independence-review-bound": 3,
    "review-bound": 3,
    "delivery-ready": 4,
}

CANONICAL_STATE_BY_RANK = {
    0: "blocked",
    1: "foundation-ready",
    2: "implementation-in-progress",
    3: "implementation-ready",
    4: "delivery-ready",
}


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _state_rank(state: str) -> int:
    return FORMAL_STATE_RANK.get(str(state or "").strip(), FORMAL_STATE_RANK["implementation-in-progress"])


def _ceiling_label(rank: int) -> str:
    return CANONICAL_STATE_BY_RANK.get(rank, "implementation-in-progress")


def _trace_quality_from_checks(checks: dict[str, Any]) -> dict[str, Any]:
    return {
        "confirmed_count": _as_int(checks.get("trace_registry_confirmed_count")),
        "suggested_count": _as_int(checks.get("trace_registry_suggested_count")),
        "review_count": _as_int(checks.get("trace_registry_review_count")),
        "unresolved_count": _as_int(checks.get("trace_registry_unresolved_count")),
        "blocking_gap_count": _as_int(checks.get("trace_registry_gap_count")),
        "abuse_count": _as_int(checks.get("trace_registry_abuse_count")),
        "chain_coverage_state": str(checks.get("trace_registry_chain_coverage_state") or "unknown").strip(),
        "trace_registry_present": bool(checks.get("trace_registry_final_present", False)),
        "trace_db_present": bool(checks.get("trace_db_present", False)),
        "trace_db_indexed": bool(checks.get("trace_db_indexed", False)),
        "trace_db_projection_status": str(checks.get("trace_db_projection_status") or "").strip(),
    }


def build_phase3_claim_ceiling_report(
    *,
    requested_formal_state: str,
    checks: dict[str, Any],
    failures: list[str] | None = None,
    warnings: list[str] | None = None,
    scope_states: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return a machine-readable formal-state ceiling report.

    The resolver consumes signals produced elsewhere. A green local gate cannot
    override a lower-ranked ceiling reason here.
    """

    checks = checks if isinstance(checks, dict) else {}
    failures = failures or []
    warnings = warnings or []
    scope_states = scope_states or {}
    requested_rank = _state_rank(requested_formal_state)
    ceiling_rank = requested_rank
    reasons: list[dict[str, str]] = []

    def cap(rank: int, reason: str, signal: str, detail: str) -> None:
        nonlocal ceiling_rank
        ceiling_rank = min(ceiling_rank, rank)
        reasons.append(
            {
                "reason": reason,
                "signal": signal,
                "detail": detail,
                "ceiling": _ceiling_label(rank),
            }
        )

    implementation_depth_state = str(scope_states.get("implementation_depth_state") or "").strip()
    if implementation_depth_state == "unknown":
        cap(
            FORMAL_STATE_RANK["implementation-in-progress"],
            "implementation_depth_unknown",
            "implementation_depth_state",
            "Implementation semantic depth is unknown; runtime green signals cannot be promoted to delivery-ready.",
        )
    elif implementation_depth_state == "review-bound":
        cap(
            FORMAL_STATE_RANK["implementation-ready"],
            "implementation_depth_review_bound",
            "implementation_depth_state",
            "Implementation depth remains review-bound; delivery-ready is capped until semantic depth is proven.",
        )

    artifact_quality_state = str(scope_states.get("artifact_quality_state") or "").strip()
    if artifact_quality_state and artifact_quality_state != "pass":
        cap(
            FORMAL_STATE_RANK["implementation-ready"],
            "artifact_quality_review_bound",
            "artifact_quality_state",
            "Artifact quality is not pass; the package can only be implementation-ready at most.",
        )

    trace = _trace_quality_from_checks(checks)
    if trace["unresolved_count"] > 0 or trace["blocking_gap_count"] > 0:
        cap(
            FORMAL_STATE_RANK["implementation-in-progress"],
            "trace_unresolved",
            "trace_quality",
            "Unresolved trace subjects remain; formal state cannot pass implementation-in-progress.",
        )
    elif trace["suggested_count"] > 0 or trace["review_count"] > 0:
        cap(
            FORMAL_STATE_RANK["implementation-ready"],
            "trace_not_confirmed",
            "trace_quality",
            "Suggested or review trace bindings are not confirmed causality evidence.",
        )
    if trace["abuse_count"] > 0:
        cap(
            FORMAL_STATE_RANK["implementation-in-progress"],
            "trace_id_abuse",
            "trace_quality",
            "Trace ID overuse or read/write conflict suggests trace shape is being reused without causal proof.",
        )
    if trace["trace_registry_present"] and not trace["trace_db_present"]:
        cap(
            FORMAL_STATE_RANK["implementation-ready"],
            "trace_identity_source_missing",
            "trace_quality",
            "Trace registry evidence is present, but the project trace identity source `.trace/trace.db` is missing.",
        )
    if trace["trace_registry_present"] and trace["trace_db_present"] and trace["confirmed_count"] > 0 and not trace["trace_db_indexed"]:
        cap(
            FORMAL_STATE_RANK["implementation-in-progress"],
            "trace_identity_source_not_indexed",
            "trace_quality",
            "Trace registry confirms Phase-3 evidence, but `.trace/trace.db` has not indexed the Phase-3 test/code links.",
        )

    same_source_risk_count = _as_int(checks.get("same_source_test_risk_count"))
    anti_cheat_negative_count = _as_int(checks.get("anti_cheat_negative_test_count"))
    empty_or_audit_shaped_count = _as_int(checks.get("empty_or_audit_shaped_service_count"))
    if empty_or_audit_shaped_count > 0:
        cap(
            FORMAL_STATE_RANK["implementation-in-progress"],
            "empty_or_audit_shaped_service",
            "implementation_review",
            "One or more service/repository targets are empty, audit-shaped, or fallback-shaped.",
        )
    if same_source_risk_count > 0 and anti_cheat_negative_count == 0:
        cap(
            FORMAL_STATE_RANK["implementation-ready"],
            "same_source_test_risk",
            "test_independence",
            "Generated tests still look same-source and no independent anti-cheat negative test evidence is present.",
        )

    if any(str(item) == "code_review_has_high_or_critical_findings" for item in failures):
        cap(
            FORMAL_STATE_RANK["implementation-in-progress"],
            "code_review_blocking_findings",
            "code_review",
            "High or critical code-review findings cannot be overridden by downstream delivery gates.",
        )

    resolved_rank = max(0, ceiling_rank)
    resolved_state = _ceiling_label(resolved_rank)
    requested_state = str(requested_formal_state or "").strip() or "implementation-in-progress"
    blocked_delivery_ready = requested_state == "delivery-ready" and resolved_state != "delivery-ready"
    return {
        "artifact_kind": "phase3-claim-ceiling-report.v1",
        "requested_formal_state": requested_state,
        "resolved_formal_state": resolved_state,
        "claim_ceiling": resolved_state,
        "blocking_delivery_ready": blocked_delivery_ready,
        "reasons": reasons,
        "inputs": {
            "implementation_depth_state": implementation_depth_state or "unknown",
            "artifact_quality_state": artifact_quality_state or "unknown",
            "trace_quality": trace,
            "same_source_test_risk_count": same_source_risk_count,
            "anti_cheat_negative_test_count": anti_cheat_negative_count,
            "empty_or_audit_shaped_service_count": empty_or_audit_shaped_count,
            "failure_count": len(failures),
            "warning_count": len(warnings),
        },
        "policy": (
            "Formal state is capped by the weakest unresolved evidence. Human review may confirm or lower this "
            "ceiling, but must not upgrade it."
        ),
    }


def apply_phase3_claim_ceiling(report: dict[str, Any], claim_ceiling_report: dict[str, Any]) -> dict[str, Any]:
    updated = dict(report)
    resolved_state = str(claim_ceiling_report.get("resolved_formal_state") or "").strip()
    if resolved_state:
        updated["recommended_formal_state"] = resolved_state
        if resolved_state != "delivery-ready":
            updated["implementation_complete"] = bool(updated.get("implementation_complete")) and resolved_state in {
                "implementation-ready",
                "artifact-quality-review-bound",
                "trace-review-bound",
                "test-independence-review-bound",
                "review-bound",
            }
        updated["phase_complete"] = bool(updated.get("phase_complete")) and resolved_state == "delivery-ready"
        updated["phase_completion_gate"] = "pass" if updated["phase_complete"] else "fail"
    updated["claim_ceiling_report"] = claim_ceiling_report
    checks = dict(updated.get("checks", {}) if isinstance(updated.get("checks"), dict) else {})
    checks["claim_ceiling_resolved_formal_state"] = resolved_state
    checks["claim_ceiling_reason_count"] = len(claim_ceiling_report.get("reasons", []) or [])
    checks["claim_ceiling_blocks_delivery_ready"] = bool(claim_ceiling_report.get("blocking_delivery_ready"))
    if resolved_state != "delivery-ready":
        checks["delivery_gate"] = False
    if resolved_state not in {
        "implementation-ready",
        "artifact-quality-review-bound",
        "trace-review-bound",
        "test-independence-review-bound",
        "review-bound",
        "delivery-ready",
    }:
        checks["implementation_gate"] = False
    updated["checks"] = checks
    return updated
