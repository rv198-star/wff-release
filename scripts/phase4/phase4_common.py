#!/usr/bin/env python3
"""
Shared helpers for Phase-4 testing-validation scripts.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from common.markdown_table_tools import (
    render_markdown_table as render_common_markdown_table,
    sanitize_markdown_table_cell,
)


VISUAL_EVIDENCE_SUFFIXES = {
    ".gif",
    ".jpeg",
    ".jpg",
    ".mp4",
    ".png",
    ".webm",
    ".webp",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def stable_suffix(raw: str) -> str:
    text = raw.strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "UNKNOWN"


def compact_token(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", raw.lower())


def api_id_for_operation(operation_id: str) -> str:
    return f"API-{stable_suffix(operation_id)}"


def prefixed_id(prefix: str, raw: str) -> str:
    return f"{prefix}-{stable_suffix(raw)}"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def load_phase3_runtime_environment_summary(phase3_root: Path) -> dict[str, Any]:
    ledger_path = phase3_root / "runtime-environment-ledger.json"
    ledger = load_json_if_exists(ledger_path) or {}
    rows = [row for row in ensure_list(ledger.get("rows")) if isinstance(row, dict)]
    rows_by_packet: dict[str, dict[str, Any]] = {}
    lane_summary: dict[str, dict[str, Any]] = {}

    for row in rows:
        packet_id = str(row.get("packet_id") or "").strip()
        if packet_id:
            rows_by_packet[packet_id] = row
        lane = str(row.get("lane") or "unknown").strip().lower() or "unknown"
        lane_row = lane_summary.setdefault(
            lane,
            {
                "lane": lane,
                "packet_count": 0,
                "available_packet_count": 0,
                "missing_packet_count": 0,
                "required_runtime_environments": [],
                "blocked_capabilities": [],
                "allowed_progress_ceilings": [],
            },
        )
        lane_row["packet_count"] += 1
        required_runtime = str(row.get("required_runtime_environment") or "").strip()
        if required_runtime:
            lane_row["required_runtime_environments"] = dedupe_preserve_order(
                [*lane_row["required_runtime_environments"], required_runtime]
            )
        blocked_capabilities = [str(value) for value in ensure_list(row.get("blocked_capabilities")) if str(value).strip()]
        if blocked_capabilities:
            lane_row["blocked_capabilities"] = dedupe_preserve_order(
                [*lane_row["blocked_capabilities"], *blocked_capabilities]
            )
        allowed_progress_ceiling = str(row.get("allowed_progress_ceiling") or "").strip()
        if allowed_progress_ceiling:
            lane_row["allowed_progress_ceilings"] = dedupe_preserve_order(
                [*lane_row["allowed_progress_ceilings"], allowed_progress_ceiling]
            )
        if str(row.get("current_availability") or "").strip().lower() == "available":
            lane_row["available_packet_count"] += 1
        else:
            lane_row["missing_packet_count"] += 1

    for lane_row in lane_summary.values():
        lane_row["all_runtime_available"] = lane_row["packet_count"] > 0 and lane_row["missing_packet_count"] == 0

    missing_runtime_lanes = sorted(
        lane for lane, lane_row in lane_summary.items() if int(lane_row.get("missing_packet_count", 0) or 0) > 0
    )
    return {
        "present": bool(ledger),
        "path": relative_to_root(ledger_path, phase3_root) if ledger_path.exists() else "",
        "available_runtime_environments": [
            str(value) for value in ensure_list(ledger.get("available_runtime_environments")) if str(value).strip()
        ],
        "packet_count": len(rows),
        "packets_with_available_runtime": len(
            [row for row in rows if str(row.get("current_availability") or "").strip().lower() == "available"]
        ),
        "packets_missing_runtime": len(
            [row for row in rows if str(row.get("current_availability") or "").strip().lower() != "available"]
        ),
        "missing_runtime_lanes": missing_runtime_lanes,
        "lanes": lane_summary,
        "rows": rows,
        "rows_by_packet": rows_by_packet,
    }


def load_phase3_mainline_summary(phase3_root: Path) -> dict[str, Any]:
    metadata = load_json_if_exists(phase3_root / "phase3-run-metadata.json") or {}
    metadata_summary = metadata.get("mainline_assessment_summary")
    metadata_artifacts = metadata.get("mainline_assessment_artifacts")
    verdict = load_json_if_exists(phase3_root / "phase-verdict.json") or {}

    if not isinstance(metadata_summary, dict):
        metadata_summary = {}
    if not isinstance(metadata_artifacts, dict):
        metadata_artifacts = {}

    return {
        "present": bool(verdict) or bool(metadata_summary),
        "source": "phase-verdict.json" if verdict else ("phase3-run-metadata.json" if metadata_summary else ""),
        "phase": str(verdict.get("phase") or metadata_summary.get("phase") or "P3").strip() or "P3",
        "mainline_profile": str(
            verdict.get("mainline_profile") or metadata_summary.get("mainline_profile") or "backend-first"
        ).strip()
        or "backend-first",
        "recommended_formal_state": str(
            verdict.get("recommended_formal_state") or metadata_summary.get("recommended_formal_state") or ""
        ).strip(),
        "phase_verdict": str(verdict.get("verdict") or metadata_summary.get("phase_verdict") or "").strip(),
        "phase_total_score": verdict.get("total_score", metadata_summary.get("phase_total_score")),
        "review_bound_items_count": int(
            verdict.get("review_bound_items_count", metadata_summary.get("review_bound_items_count", 0)) or 0
        ),
        "blockers_count": int(verdict.get("blockers_count", metadata_summary.get("blockers_count", 0)) or 0),
        "warning_count": int(verdict.get("warning_count", metadata_summary.get("warning_count", 0)) or 0),
        "failure_count": int(verdict.get("failure_count", metadata_summary.get("failure_count", 0)) or 0),
        "phase_complete": bool(verdict.get("phase_complete", metadata_summary.get("phase_complete", False))),
        "implementation_complete": bool(
            verdict.get("implementation_complete", metadata_summary.get("implementation_complete", False))
        ),
        "phase_verdict_path": str(
            metadata.get("phase_verdict_path")
            or metadata_summary.get("phase_verdict_path")
            or metadata_artifacts.get("verdict_path")
            or (relative_to_root(phase3_root / "phase-verdict.json", phase3_root) if verdict else "")
        ).strip(),
        "phase_scorecard_path": str(
            metadata_summary.get("phase_scorecard_path")
            or metadata_artifacts.get("scorecard_path")
            or (
                relative_to_root(phase3_root / "phase-mainline-scorecard.md", phase3_root)
                if (phase3_root / "phase-mainline-scorecard.md").exists()
                else ""
            )
        ).strip(),
        "phase_acceptance_matrix_path": str(
            metadata_summary.get("phase_acceptance_matrix_path")
            or metadata_artifacts.get("acceptance_matrix_path")
            or (
                relative_to_root(phase3_root / "phase-acceptance-matrix.md", phase3_root)
                if (phase3_root / "phase-acceptance-matrix.md").exists()
                else ""
            )
        ).strip(),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_openapi_spec(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def discover_openapi_path(phase3_root: Path) -> Path:
    direct = phase3_root / "openapi-final.yaml"
    if direct.exists():
        return direct
    fallback = phase3_root / "contracts" / "openapi.yaml"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"no Phase-3 OpenAPI artifact found under {phase3_root}")


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def markdown_cell(value: Any) -> str:
    return sanitize_markdown_table_cell(
        value,
        pipe_escape="backslash",
        none_replacement="",
        list_separator=", ",
    )


def render_markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    return render_common_markdown_table(
        headers,
        rows,
        pipe_escape="backslash",
        none_replacement="",
        list_separator=", ",
    )


def clamp_assessment_dimension(score: int) -> int:
    return max(0, min(5, score))


def render_phase4_scorecard_markdown(assessment: dict[str, Any]) -> str:
    lines = [
        "# Phase-4 Mainline Scorecard",
        "",
        f"- total_score: `{assessment['total_score']}` / 100",
        f"- verdict: `{assessment['verdict']}`",
        f"- closure_decision: `{assessment['closure_decision']}`",
        "",
        "| Dimension | Weight | Score | Notes |",
        "|---|---:|---:|---|",
    ]
    for row in assessment["dimension_scores"]:
        notes = "; ".join(str(item) for item in row.get("notes", [])) or "-"
        lines.append(f"| {row['label']} | {row['weight']} | {row['score']} / 5 | {notes} |")
    return "\n".join(lines).rstrip() + "\n"


def render_phase4_acceptance_matrix_markdown(assessment: dict[str, Any]) -> str:
    lines = [
        "# Phase-4 Acceptance Matrix",
        "",
        f"- verdict: `{assessment['verdict']}`",
        f"- closure_decision: `{assessment['closure_decision']}`",
        "",
        "| Acceptance Item | Status | Why |",
        "|---|---|---|",
    ]
    for row in assessment["acceptance_rows"]:
        lines.append(f"| {row['label']} | `{row['status']}` | {row['why']} |")
    return "\n".join(lines).rstrip() + "\n"


def build_phase4_mainline_assessment(
    *,
    stage1_summary: dict[str, Any],
    stage2_summary: dict[str, Any],
    stage3_summary: dict[str, Any],
) -> dict[str, Any]:
    phase3_mainline_summary_present = bool(stage1_summary.get("phase3_mainline_summary_present"))
    trace_mapping_complete = bool(stage1_summary.get("trace_mapping_complete"))
    functional_api_mapping_complete = bool(stage1_summary.get("functional_api_mapping_complete"))
    decision_alignment_complete = bool(stage1_summary.get("decision_alignment_complete"))
    high_priority_unmapped_count = int(stage1_summary.get("high_priority_unmapped_count") or 0)

    functional_non_pass_count = int(stage2_summary.get("functional_non_pass_count") or 0)
    functional_conditional_pass_count = int(stage2_summary.get("functional_conditional_pass_count") or 0)
    data_fidelity_non_pass_count = int(stage2_summary.get("data_fidelity_non_pass_count") or 0)
    data_fidelity_conditional_pass_count = int(stage2_summary.get("data_fidelity_conditional_pass_count") or 0)
    ui_review_non_pass_count = int(stage2_summary.get("ui_review_non_pass_count") or 0)
    visual_review_bound_count = int(stage2_summary.get("visual_review_bound_count") or 0)
    review_bound_count = int(stage2_summary.get("review_bound_count") or 0)
    signoff_pending_count = int(stage2_summary.get("signoff_pending_count") or 0)
    signoff_not_ready_count = int(
        stage2_summary.get("signoff_not_ready_count", stage3_summary.get("signoff_not_ready_count", 0)) or 0
    )

    closure_decision = str(stage3_summary.get("closure_decision", "")).strip() or "return"
    blocking_count = int(stage3_summary.get("blocking_count") or 0)
    mock_dependency_present = functional_conditional_pass_count > 0 or data_fidelity_conditional_pass_count > 0
    review_pending = (
        ui_review_non_pass_count > 0
        or visual_review_bound_count > 0
        or signoff_pending_count > 0
        or signoff_not_ready_count > 0
        or review_bound_count > 0
    )

    dimension_rows = [
        {
            "key": "planning_and_traceability",
            "label": "测试规划与追踪完整度",
            "weight": 25,
            "score": clamp_assessment_dimension(
                int(phase3_mainline_summary_present)
                + int(trace_mapping_complete)
                + int(functional_api_mapping_complete)
                + int(decision_alignment_complete)
                + int(high_priority_unmapped_count == 0)
            ),
            "notes": [
                f"trace_mapping_complete={str(trace_mapping_complete).lower()}",
                f"functional_api_mapping_complete={str(functional_api_mapping_complete).lower()}",
                f"decision_alignment_complete={str(decision_alignment_complete).lower()}",
                f"high_priority_unmapped_count={high_priority_unmapped_count}",
            ],
        },
        {
            "key": "execution_truth",
            "label": "执行证据真实性",
            "weight": 25,
            "score": clamp_assessment_dimension(
                int(functional_non_pass_count == 0)
                + int(data_fidelity_non_pass_count == 0)
                + int(functional_conditional_pass_count == 0)
                + int(data_fidelity_conditional_pass_count == 0)
                + int(phase3_mainline_summary_present)
            ),
            "notes": [
                f"functional_non_pass_count={functional_non_pass_count}",
                f"data_fidelity_non_pass_count={data_fidelity_non_pass_count}",
                f"functional_conditional_pass_count={functional_conditional_pass_count}",
                f"data_fidelity_conditional_pass_count={data_fidelity_conditional_pass_count}",
            ],
        },
        {
            "key": "closure_boundary_quality",
            "label": "收口边界质量",
            "weight": 20,
            "score": clamp_assessment_dimension(
                int(closure_decision in {"pass", "pass-with-review-bound-items", "pass-with-mock-dependency"})
                + int(blocking_count == 0)
                + int(trace_mapping_complete)
                + int(decision_alignment_complete)
                + int(phase3_mainline_summary_present)
            ),
            "notes": [
                f"closure_decision={closure_decision}",
                f"blocking_count={blocking_count}",
                f"signoff_pending_count={signoff_pending_count}",
                f"signoff_not_ready_count={signoff_not_ready_count}",
            ],
        },
        {
            "key": "review_bound_honesty",
            "label": "review-bound / signoff 诚实度",
            "weight": 15,
            "score": clamp_assessment_dimension(
                int(phase3_mainline_summary_present)
                + int(bool(closure_decision))
                + int((not mock_dependency_present) or closure_decision == "pass-with-mock-dependency")
                + int((not review_pending) or closure_decision in {"pass-with-review-bound-items", "return"})
                + int((blocking_count == 0) or closure_decision == "return")
            ),
            "notes": [
                f"mock_dependency_present={str(mock_dependency_present).lower()}",
                f"review_pending={str(review_pending).lower()}",
                f"review_bound_count={review_bound_count}",
                f"signoff_pending_count={signoff_pending_count}",
                f"signoff_not_ready_count={signoff_not_ready_count}",
            ],
        },
        {
            "key": "downstream_decision_readiness",
            "label": "下游决策可用度",
            "weight": 15,
            "score": clamp_assessment_dimension(
                int(closure_decision != "return")
                + int(blocking_count == 0)
                + int(signoff_pending_count == 0)
                + int(signoff_not_ready_count == 0)
                + int(review_bound_count == 0)
                + int(high_priority_unmapped_count == 0)
            ),
            "notes": [
                f"closure_decision={closure_decision}",
                f"review_bound_count={review_bound_count}",
                f"signoff_pending_count={signoff_pending_count}",
                f"signoff_not_ready_count={signoff_not_ready_count}",
            ],
        },
    ]

    planning_status = (
        "PASS"
        if trace_mapping_complete and functional_api_mapping_complete and decision_alignment_complete and high_priority_unmapped_count == 0
        else "REVIEW-BOUND"
        if trace_mapping_complete and decision_alignment_complete
        else "BLOCKED"
    )
    planning_why = (
        "acceptance planning is trace-complete and key Phase-2 decisions are covered"
        if planning_status == "PASS"
        else "planning is mostly usable, but some higher-priority decision coverage remains review-bound"
        if planning_status == "REVIEW-BOUND"
        else "acceptance planning still leaves trace or decision-coverage gaps that weaken closure"
    )
    mandatory_status = (
        "PASS"
        if functional_non_pass_count == 0
        and data_fidelity_non_pass_count == 0
        and not mock_dependency_present
        else "REVIEW-BOUND"
        if functional_non_pass_count == 0 and data_fidelity_non_pass_count == 0
        else "BLOCKED"
    )
    mandatory_why = (
        "functional and data-fidelity items both passed with non-conditional evidence"
        if mandatory_status == "PASS"
        else "mandatory evidence passed, but runtime truth still carries conditional/mock-dependency posture"
        if mandatory_status == "REVIEW-BOUND"
        else "mandatory functional or data-fidelity evidence still contains blocking failures"
    )
    nonfunctional_status = (
        "PASS"
        if not review_pending and blocking_count == 0
        else "REVIEW-BOUND"
        if blocking_count == 0 and closure_decision in {"pass-with-review-bound-items", "pass-with-mock-dependency"}
        else "BLOCKED"
    )
    nonfunctional_why = (
        "UI/visual/manual signoff surfaces are closed without residual review-bound items"
        if nonfunctional_status == "PASS"
        else "UI/visual/manual signoff gaps remain, but they are explicitly preserved in the closure posture"
        if nonfunctional_status == "REVIEW-BOUND"
        else "non-functional evidence still contains structural blockers or hidden unresolved truth"
    )
    closure_status = (
        "PASS"
        if closure_decision == "pass"
        else "REVIEW-BOUND"
        if closure_decision in {"pass-with-review-bound-items", "pass-with-mock-dependency"}
        else "BLOCKED"
    )
    closure_why = (
        "closure package gives a clear downstream decision boundary without residual review-bound items"
        if closure_status == "PASS"
        else "closure package is usable, but downstream must keep the explicit review-bound boundary visible"
        if closure_status == "REVIEW-BOUND"
        else "closure decision is return and still requires remediation before downstream adoption"
    )

    acceptance_rows = [
        {
            "key": "phase3_mainline_truth_present",
            "label": "Phase-3 主线结论已被 P4 显式消费",
            "status": "PASS" if phase3_mainline_summary_present else "BLOCKED",
            "why": (
                "Phase-4 consumed explicit Phase-3 mainline truth"
                if phase3_mainline_summary_present
                else "Phase-4 is missing the upstream Phase-3 mainline truth anchor"
            ),
        },
        {
            "key": "acceptance_planning_trace_complete",
            "label": "测试规划与决策覆盖完整",
            "status": planning_status,
            "why": planning_why,
        },
        {
            "key": "mandatory_execution_evidence_passed",
            "label": "功能/数据保真主证据已通过",
            "status": mandatory_status,
            "why": mandatory_why,
        },
        {
            "key": "nonfunctional_gaps_explicit",
            "label": "非功能 review-bound 与签核缺口显式外露",
            "status": nonfunctional_status,
            "why": nonfunctional_why,
        },
        {
            "key": "downstream_decision_boundary_clear",
            "label": "下游不需要猜测收口边界",
            "status": closure_status,
            "why": closure_why,
        },
    ]

    total_score = round(sum((row["score"] / 5) * row["weight"] for row in dimension_rows), 1)
    blockers_count = sum(1 for row in acceptance_rows if row["status"] == "BLOCKED")
    review_bound_items_count = sum(1 for row in acceptance_rows if row["status"] == "REVIEW-BOUND")
    min_dimension_score = min((row["score"] for row in dimension_rows), default=0)

    if closure_decision == "return" or blockers_count > 0 or total_score < 70:
        verdict = "RETURN-REMEDIATE"
    elif total_score >= 85 and min_dimension_score >= 3 and review_bound_items_count == 0 and closure_decision == "pass":
        verdict = "PASS"
    else:
        verdict = "PASS with review-bound items"

    return {
        "phase": "P4",
        "closure_decision": closure_decision,
        "dimension_scores": dimension_rows,
        "acceptance_rows": acceptance_rows,
        "total_score": total_score,
        "verdict": verdict,
        "review_bound_items_count": review_bound_items_count,
        "blockers_count": blockers_count,
        "signoff_pending_count": signoff_pending_count,
        "signoff_not_ready_count": signoff_not_ready_count,
        "phase3_mainline_summary_present": phase3_mainline_summary_present,
        "functional_non_pass_count": functional_non_pass_count,
        "data_fidelity_non_pass_count": data_fidelity_non_pass_count,
    }


def write_phase4_mainline_assessment_artifacts(
    *,
    output_dir: Path,
    assessment: dict[str, Any],
) -> dict[str, str]:
    scorecard_path = output_dir / "phase-mainline-scorecard.md"
    acceptance_matrix_path = output_dir / "phase-acceptance-matrix.md"
    verdict_path = output_dir / "phase-verdict.json"
    write_text(scorecard_path, render_phase4_scorecard_markdown(assessment))
    write_text(acceptance_matrix_path, render_phase4_acceptance_matrix_markdown(assessment))
    write_json(verdict_path, assessment)
    return {
        "scorecard_path": str(scorecard_path),
        "acceptance_matrix_path": str(acceptance_matrix_path),
        "verdict_path": str(verdict_path),
    }


def build_phase4_metadata_payload(
    *,
    case_name: str,
    version: str,
    phase3_root: Path,
    artifact_kind: str,
    generation_entrypoint: str,
    generation_purity: str,
    external_evidence_manifest: Path | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "generated_at": utc_now_iso(),
        "case_name": case_name,
        "version": version,
        "phase3_root": str(phase3_root),
        "artifact_kind": artifact_kind,
        "generation_entrypoint": generation_entrypoint,
        "generation_purity": generation_purity,
        "external_evidence_manifest": str(external_evidence_manifest) if external_evidence_manifest else "",
    }
    if extra_fields:
        payload.update(extra_fields)
    return payload


def build_phase4_quality_check_payload(
    *,
    stage1_summary: dict[str, Any],
    stage2_summary: dict[str, Any],
    stage3_summary: dict[str, Any],
    extra_checks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks = {
        "stage01_trace_mapping_complete": stage1_summary["trace_mapping_complete"],
        "stage01_functional_api_mapping_complete": stage1_summary["functional_api_mapping_complete"],
        "stage01_functional_api_optional_count": stage1_summary["functional_api_optional_count"],
        "stage01_data_fidelity_count": stage1_summary.get("data_fidelity_count", 0),
        "stage01_decision_alignment_complete": stage1_summary["decision_alignment_complete"],
        "stage01_high_priority_unmapped_count": stage1_summary["high_priority_unmapped_count"],
        "stage01_human_signoff_required_count": stage1_summary["human_signoff_required_count"],
        "stage02_functional_non_pass_count": stage2_summary["functional_non_pass_count"],
        "stage02_functional_conditional_pass_count": stage2_summary.get("functional_conditional_pass_count", 0),
        "stage02_data_fidelity_non_pass_count": stage2_summary.get("data_fidelity_non_pass_count", 0),
        "stage02_data_fidelity_conditional_pass_count": stage2_summary.get("data_fidelity_conditional_pass_count", 0),
        "stage02_ui_review_non_pass_count": stage2_summary["ui_review_non_pass_count"],
        "stage02_visual_review_bound_count": stage2_summary["visual_review_bound_count"],
        "stage02_signoff_pending_count": stage2_summary["signoff_pending_count"],
        "stage02_signoff_not_ready_count": stage2_summary.get("signoff_not_ready_count", 0),
        "stage03_closure_decision": stage3_summary["closure_decision"],
        "stage03_signoff_pending_count": stage3_summary["signoff_pending_count"],
        "stage03_signoff_not_ready_count": stage3_summary.get("signoff_not_ready_count", 0),
    }
    if extra_checks:
        checks = {**extra_checks, **checks}
    return {
        "generated_at": utc_now_iso(),
        "overall_quality_gate": stage3_summary["closure_decision"],
        "checks": checks,
        "summaries": {
            "stage01": stage1_summary,
            "stage02": stage2_summary,
            "stage03": stage3_summary,
        },
    }


def build_phase4_mainline_assessment_summary(
    *,
    assessment: dict[str, Any],
    artifact_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    artifact_paths = artifact_paths or {}
    return {
        "phase": str(assessment.get("phase", "P4")).strip() or "P4",
        "phase_verdict": str(assessment.get("verdict", "")).strip(),
        "phase_total_score": assessment.get("total_score"),
        "review_bound_items_count": int(assessment.get("review_bound_items_count", 0) or 0),
        "blockers_count": int(assessment.get("blockers_count", 0) or 0),
        "signoff_pending_count": int(assessment.get("signoff_pending_count", 0) or 0),
        "signoff_not_ready_count": int(assessment.get("signoff_not_ready_count", 0) or 0),
        "closure_decision": str(assessment.get("closure_decision", "")).strip(),
        "phase_scorecard_path": str(artifact_paths.get("scorecard_path", "")).strip(),
        "phase_acceptance_matrix_path": str(artifact_paths.get("acceptance_matrix_path", "")).strip(),
        "phase_verdict_path": str(artifact_paths.get("verdict_path", "")).strip(),
    }


def _test_bucket(index: dict[str, dict[str, Any]], test_id: str) -> dict[str, Any]:
    return index.setdefault(
        test_id,
        {
            "report_paths": [],
            "pass_count": 0,
            "fail_count": 0,
            "verdict": "not-run",
            "latest_verdict": "not-run",
            "latest_report_path": "",
        },
    )


def _record_test_verdict(
    index: dict[str, dict[str, Any]],
    *,
    test_id: str,
    verdict: str,
    report_ref: str,
) -> None:
    normalized_test_id = str(test_id).strip()
    normalized_verdict = str(verdict).strip().lower()
    if not normalized_test_id or normalized_verdict not in {"pass", "fail"}:
        return
    bucket = _test_bucket(index, normalized_test_id)
    if normalized_verdict == "pass":
        bucket["pass_count"] += 1
    else:
        bucket["fail_count"] += 1
    bucket["report_paths"] = dedupe_preserve_order([*bucket["report_paths"], report_ref])
    bucket["latest_verdict"] = normalized_verdict
    bucket["latest_report_path"] = report_ref


def _ingest_test_report_payload(
    index: dict[str, dict[str, Any]],
    *,
    payload: dict[str, Any],
    report_ref: str,
) -> None:
    for passed_test in ensure_list(payload.get("passed_tests") or payload.get("observed_passed_tests")):
        _record_test_verdict(index, test_id=str(passed_test), verdict="pass", report_ref=report_ref)
    for failed_test in ensure_list(
        payload.get("failed_tests") or payload.get("observed_failed_tests") or payload.get("missing_expected_tests")
    ):
        _record_test_verdict(index, test_id=str(failed_test), verdict="fail", report_ref=report_ref)


def _ingest_phase3_verification_ledger(
    index: dict[str, dict[str, Any]],
    *,
    ledger: dict[str, Any],
    report_ref: str,
) -> None:
    aggregated = ledger.get("aggregated", {}) if isinstance(ledger.get("aggregated"), dict) else {}
    _ingest_test_report_payload(index, payload=aggregated, report_ref=report_ref)

    latest_by_packet = ledger.get("latest_by_packet", {}) if isinstance(ledger.get("latest_by_packet"), dict) else {}
    for packet_row in latest_by_packet.values():
        if isinstance(packet_row, dict):
            _ingest_test_report_payload(index, payload=packet_row, report_ref=report_ref)


def collect_test_evidence(phase3_root: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    report_patterns = [
        "worker-runs/**/test-report.json",
        ".phase3-mainline-execution/backend-runs/**/test-report.json",
        ".phase3-mainline-execution/backend-runs/**/unit-test-report.json",
        ".phase3-mainline-execution/backend-runs/**/full-test-report.json",
        ".phase3-mainline-execution/backend-runs/**/verification-report.json",
        "test-report.json",
        "unit-test-report.json",
        "full-test-report.json",
    ]
    report_paths: list[Path] = []
    for pattern in report_patterns:
        report_paths.extend(sorted(phase3_root.glob(pattern)))
    for report_path in dedupe_preserve_order(str(path) for path in report_paths):
        path = Path(report_path)
        report = load_json(path)
        _ingest_test_report_payload(index, payload=report, report_ref=relative_to_root(path, phase3_root))

    ledger_path = phase3_root / "phase3-verification-ledger.json"
    if ledger_path.exists():
        _ingest_phase3_verification_ledger(
            index,
            ledger=load_json(ledger_path),
            report_ref=relative_to_root(ledger_path, phase3_root),
        )

    for bucket in index.values():
        if bucket["latest_verdict"] in {"pass", "fail"}:
            bucket["verdict"] = bucket["latest_verdict"]
        elif bucket["pass_count"] > 0:
            bucket["verdict"] = "pass"
        else:
            bucket["verdict"] = "not-run"
    return index


def collect_visual_evidence_paths(phase3_root: Path) -> list[str]:
    search_roots = [
        phase3_root,
        phase3_root / "apps",
        phase3_root / "docs",
        phase3_root / "evidence",
        phase3_root / "screenshots",
        phase3_root / "worker-runs",
    ]
    results: list[str] = []
    seen_paths: set[Path] = set()
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for path in search_root.rglob("*"):
            if path in seen_paths or not path.is_file():
                continue
            if "node_modules" in path.parts:
                continue
            if path.suffix.lower() not in VISUAL_EVIDENCE_SUFFIXES:
                continue
            seen_paths.add(path)
            results.append(relative_to_root(path, phase3_root))
    return dedupe_preserve_order(results)


def load_frontend_packets(phase3_root: Path) -> list[dict[str, Any]]:
    return load_worker_packets(phase3_root, lane="frontend")


def load_worker_packets(phase3_root: Path, lane: str | None = None) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    pattern = "worker-input-packets/wave-*/*-worker-input-packet.json"
    for packet_path in sorted(phase3_root.glob(pattern)):
        packet = load_json(packet_path)
        packet_lane = str(packet.get("lane") or packet_path.name.split("-worker-input-packet.json")[0] or "")
        if lane is not None and packet_lane != lane:
            continue
        packet["packet_path"] = relative_to_root(packet_path, phase3_root)
        packet["lane"] = packet_lane
        packets.append(packet)
    return packets


def extract_operation_ids_from_text(text: str) -> list[str]:
    return dedupe_preserve_order(re.findall(r'operationId"\s*:\s*"([A-Za-z0-9_]+)"', text))


def extract_operation_ids_from_file(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    return extract_operation_ids_from_text(path.read_text(encoding="utf-8"))


def _alias_tuple(value: str, aliases: Iterable[str] | None = None) -> tuple[str, ...]:
    resolved = tuple(str(item) for item in (aliases or ()) if str(item))
    return resolved or (value,)


def normalize_text(value: str) -> str:
    return " ".join(str(value).replace(" ", " ").split())


def block_lines(text: str, block_name: str) -> list[str]:
    lines = text.splitlines()
    start = None
    marker = f"- {block_name}:"
    for idx, line in enumerate(lines):
        if line.startswith(marker):
            start = idx
            break
    if start is None:
        return []
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("- ") and not line.startswith("  - "):
            break
        collected.append(line)
    return collected


def block_text(text: str, block_name: str) -> str:
    return "\n".join(block_lines(text, block_name)).strip()


def heading_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    prefix = f"## {heading}"
    start = None
    for idx, line in enumerate(lines):
        if line.startswith(prefix):
            start = idx
            break
    if start is None:
        return ""
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def markdown_heading_section(text: str, heading: str, *, aliases: Iterable[str] | None = None) -> str:
    for candidate in _alias_tuple(heading, aliases):
        pattern = re.compile(rf"^(#+)\s+{re.escape(candidate)}\s*$", re.MULTILINE)
        match = pattern.search(text)
        if not match:
            continue
        level = len(match.group(1))
        start = match.start()
        end = len(text)
        for next_match in pattern.finditer(text):
            if next_match.start() == match.start():
                continue
            if len(next_match.group(1)) <= level:
                end = next_match.start()
                break
        general_heading_re = re.compile(r"^(#+)\s+.+$", re.MULTILINE)
        for next_match in general_heading_re.finditer(text, match.end()):
            if len(next_match.group(1)) <= level:
                end = next_match.start()
                break
        return text[start:end].strip()
    return ""


def extract_structured_field(
    entry: str,
    field_name: str,
    *,
    indent: int = 4,
    aliases: Iterable[str] | None = None,
) -> str:
    field_names = _alias_tuple(field_name, aliases)
    candidate_indents = [indent]
    candidate_indents.extend(
        indent_value
        for indent_value in (
            len(match.group(1))
            for alias in field_names
            for match in re.finditer(rf"^( *)- {re.escape(alias)}:", entry, flags=re.MULTILINE)
        )
        if indent_value not in candidate_indents
    )
    for current_indent in candidate_indents:
        value = extract_structured_field_at_indent(
            entry,
            field_name,
            indent=current_indent,
            aliases=field_names,
        )
        if value:
            return value
    return ""


def extract_structured_field_at_indent(
    entry: str,
    field_name: str,
    *,
    indent: int = 4,
    aliases: Iterable[str] | None = None,
) -> str:
    del field_name
    field_names = _alias_tuple("", aliases)
    lines = entry.splitlines()
    collected: list[str] = []
    capturing = False
    for line in lines:
        for alias in field_names:
            prefix = " " * indent + f"- {alias}:"
            if line.startswith(prefix):
                capturing = True
                remainder = line[len(prefix) :].strip()
                if remainder:
                    collected.append(remainder.strip("`"))
                break
        else:
            prefix = ""
        if prefix:
            continue
        if not capturing:
            continue
        if line.startswith(" " * indent + "- ") and not line.startswith(" " * (indent + 2) + "- "):
            break
        stripped = line.strip()
        if stripped:
            collected.append(stripped.strip("`"))
    return normalize_text(" ".join(collected))


def extract_structured_block(
    entry: str,
    field_name: str,
    *,
    indent: int = 4,
    aliases: Iterable[str] | None = None,
) -> str:
    field_names = _alias_tuple(field_name, aliases)
    candidate_indents = [indent]
    candidate_indents.extend(
        indent_value
        for indent_value in (
            len(match.group(1))
            for alias in field_names
            for match in re.finditer(rf"^( *)- {re.escape(alias)}:", entry, flags=re.MULTILINE)
        )
        if indent_value not in candidate_indents
    )
    for current_indent in candidate_indents:
        value = extract_structured_block_at_indent(
            entry,
            field_name,
            indent=current_indent,
            aliases=field_names,
        )
        if value:
            return value
    return ""


def extract_structured_block_at_indent(
    entry: str,
    field_name: str,
    *,
    indent: int = 4,
    aliases: Iterable[str] | None = None,
) -> str:
    del field_name
    field_names = _alias_tuple("", aliases)
    lines = entry.splitlines()
    collected: list[str] = []
    capturing = False
    for line in lines:
        for alias in field_names:
            prefix = " " * indent + f"- {alias}:"
            if line.startswith(prefix):
                capturing = True
                remainder = line[len(prefix) :].rstrip()
                if remainder.strip():
                    collected.append(remainder.strip())
                break
        else:
            prefix = ""
        if prefix:
            continue
        if not capturing:
            continue
        if line.startswith(" " * indent + "- ") and not line.startswith(" " * (indent + 2) + "- "):
            break
        collected.append(line.rstrip())
    return "\n".join(collected).strip()
