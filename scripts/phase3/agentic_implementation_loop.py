from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in _as_list(value) if str(item).strip()]


def _source_priority(source_type: str) -> int:
    normalized = source_type.strip().lower()
    if normalized in {"contract", "interface", "api"}:
        return 40
    if normalized in {"scenario", "flow"}:
        return 35
    if normalized in {"replay", "idempotency"}:
        return 30
    if normalized in {"sql", "persistence", "data"}:
        return 25
    return 10


def _rank_binding_row(row: dict[str, Any]) -> int:
    return (
        _source_priority(str(row.get("source_type", "")))
        + (len(_string_list(row.get("implementation_targets"))) * 4)
        + (len(_string_list(row.get("test_targets"))) * 3)
        + (len(_string_list(row.get("runtime_evidence_refs"))) * 2)
        + (len(_string_list(row.get("work_packages"))) * 2)
    )


def _selected_slices(implementation_bindings: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    rows = [row for row in _as_list(implementation_bindings.get("rows")) if isinstance(row, dict)]
    candidates: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        implementation_targets = _string_list(row.get("implementation_targets"))
        test_targets = _string_list(row.get("test_targets"))
        if not implementation_targets and not test_targets:
            continue
        candidates.append(
            {
                "source_id": str(row.get("source_id", "")).strip(),
                "source_type": str(row.get("source_type", "")).strip(),
                "source_subject": str(row.get("source_subject", "")).strip(),
                "work_packages": _string_list(row.get("work_packages")),
                "implementation_targets": implementation_targets,
                "test_targets": test_targets,
                "runtime_evidence_refs": _string_list(row.get("runtime_evidence_refs")),
                "selection_reason": "highest value/risk implementation slice with concrete implementation and evidence bindings",
                "_rank": _rank_binding_row(row),
                "_source_order": index,
            }
        )
    candidates.sort(key=lambda item: (-int(item["_rank"]), int(item["_source_order"])))
    selected = candidates[:limit]
    for item in selected:
        item.pop("_rank", None)
        item.pop("_source_order", None)
    return selected


def _risk_signals(test_richness_review: dict[str, Any]) -> list[str]:
    workflow = test_richness_review.get("workflow_preflight", {})
    if not isinstance(workflow, dict):
        return []
    return _string_list(workflow.get("risk_signals"))


def _summary_value(test_richness_review: dict[str, Any], key: str, default: str) -> str:
    summary = test_richness_review.get("summary", {})
    if not isinstance(summary, dict):
        return default
    return str(summary.get(key, default)).strip() or default


def build_agentic_implementation_loop(
    *,
    case_name: str,
    version: str,
    implementation_bindings: dict[str, Any],
    test_richness_review: dict[str, Any],
    mainline_verification_mode: str,
    dispatch_lane_enabled: bool,
    output_locale: str = "zh-CN",
) -> dict[str, Any]:
    selected = _selected_slices(implementation_bindings)
    strict_mode = str(mainline_verification_mode).strip() == "strict-runtime"
    risk_signals = _risk_signals(test_richness_review)
    claim_ceiling = _summary_value(test_richness_review, "evidence_claim_ceiling", "review-bound")
    agentic_review_status = _summary_value(test_richness_review, "agentic_review_status", "required")
    workflow_status = _summary_value(test_richness_review, "workflow_status", "unknown")

    return {
        "artifact_kind": "phase3-agentic-implementation-loop",
        "case_name": str(case_name).strip(),
        "version": str(version).strip(),
        "output_locale": str(output_locale).strip() or "zh-CN",
        "loop_mode": "default-mainline-agentic-loop",
        "control_boundary": {
            "workflow": "preserve P2-to-P3 order, artifact contract, bounded loop steps, and evidence handoff",
            "agentic": "select value/risk slices, judge implementation meaning, deepen weak tests, and route unresolved truth",
            "evidence": "cap delivery claims until strict runtime and reviewable runtime evidence close",
        },
        "dispatch_lane": {
            "enabled": bool(dispatch_lane_enabled),
            "required_for_mainline_loop": False,
            "role": "optional worker/packet support lane; it may execute slices, but the mainline Agentic loop artifact is always emitted",
        },
        "strict_proof_gate": {
            "mode": str(mainline_verification_mode).strip() or "disabled",
            "required_for_delivery_ready": True,
            "current_profile_is_release_ready": strict_mode,
            "required_evidence": [
                "toolchain install",
                "mainline backend verification",
                "full targeted SQL / contract / scenario / replay evidence",
                "runtime smoke",
                "started-service smoke",
                "P4 claim-ceiling validation",
            ],
        },
        "selected_implementation_slices": selected,
        "execution_loop": {
            "entry": "consume accepted P2 contracts, trace rows, behavior cards, action cards, and implementation bindings",
            "steps": [
                "select the highest value/risk implementation slices",
                "implement or inspect the concrete service/repository/API boundary for each selected slice",
                "run the bound contract, scenario, replay, SQL, and unit evidence families",
                "review whether assertions prove business behavior rather than generated shape",
                "repair implementation or route upstream before raising formal state",
            ],
            "stop_conditions": [
                "strict-runtime evidence is green and Agentic review has no blocking runtime-value gap",
                "a concrete P1/P2/P3 owner defect is identified with rerun boundary",
                "runtime environment is unavailable and the claim ceiling is capped",
            ],
        },
        "tvg_checkpoints": [
            {
                "checkpoint_id": "service-boundary-value",
                "question": "Does the selected service/API slice carry real P1/P2 value, or only a generated runtime shell?",
                "exit": "continue only while another bounded round improves runnable business value",
            },
            {
                "checkpoint_id": "test-meaning-value",
                "question": "Do the tests prove state, permission, error, persistence, replay, and boundary effects?",
                "exit": "stop when another assertion-deepening round no longer adds practical evidence value",
            },
            {
                "checkpoint_id": "runtime-evidence-value",
                "question": "Does runtime proof execute the intended service boundary rather than wrapper or packaging evidence?",
                "exit": "cap claims if runtime proof is absent or weaker than the delivery claim",
            },
        ],
        "agentic_review": {
            "status": agentic_review_status,
            "workflow_preflight_status": workflow_status,
            "risk_signals": risk_signals,
            "required_verdicts": [
                "real-business",
                "structural-only",
                "self-fulfilling",
                "missing",
            ],
        },
        "evidence_bridge": {
            "claim_ceiling_before_strict_proof": claim_ceiling,
            "value_to_runtime_sources": [
                "implementation-bindings.json",
                "test-richness-review.json",
                "phase3-toolchain-bootstrap.json",
                "phase3-verification-ledger.json",
                "runtime-smoke-report.json",
                "started-service-smoke-report.json",
            ],
        },
        "summary": {
            "selected_slice_count": len(selected),
            "risk_signal_count": len(risk_signals),
            "has_tvg_checkpoints": True,
            "strict_proof_required": True,
            "dispatch_lane_required": False,
        },
    }


def render_agentic_implementation_loop_markdown(loop: dict[str, Any], *, output_locale: str = "zh-CN") -> str:
    zh = str(output_locale).strip().lower() in {"zh-cn", "zh", "cn"}
    title = "# P3 Agentic 实现循环" if zh else "# P3 Agentic Implementation Loop"
    summary_title = "## 摘要" if zh else "## Summary"
    slices_title = "## 实现切片" if zh else "## Implementation Slices"
    tvg_title = "## TVG 检查点" if zh else "## TVG Checkpoints"
    evidence_title = "## 证据边界" if zh else "## Evidence Boundary"
    no_slices = "未选择具体实现切片；必须保持 review-bound。" if zh else "No concrete implementation slice selected; keep review-bound."
    lines = [
        title,
        "",
        summary_title,
        f"- loop_mode: `{loop.get('loop_mode', '')}`",
        f"- strict_proof_mode: `{loop.get('strict_proof_gate', {}).get('mode', '')}`",
        f"- selected_slice_count: `{loop.get('summary', {}).get('selected_slice_count', 0)}`",
        f"- dispatch_lane_required: `{str(loop.get('summary', {}).get('dispatch_lane_required', False)).lower()}`",
        "",
        slices_title,
    ]
    slices = _as_list(loop.get("selected_implementation_slices"))
    if not slices:
        lines.append(f"- {no_slices}")
    for item in slices:
        if not isinstance(item, dict):
            continue
        lines.extend(
            [
                f"- `{item.get('source_id', '')}` {item.get('source_subject', '')}",
                f"  - implementation_targets: `{', '.join(_string_list(item.get('implementation_targets')))}`",
                f"  - test_targets: `{', '.join(_string_list(item.get('test_targets')))}`",
                f"  - runtime_evidence_refs: `{', '.join(_string_list(item.get('runtime_evidence_refs')))}`",
            ]
        )
    lines.extend(["", tvg_title])
    for checkpoint in _as_list(loop.get("tvg_checkpoints")):
        if not isinstance(checkpoint, dict):
            continue
        lines.append(f"- `{checkpoint.get('checkpoint_id', '')}`: {checkpoint.get('question', '')}")
    evidence = loop.get("evidence_bridge", {}) if isinstance(loop.get("evidence_bridge"), dict) else {}
    lines.extend(
        [
            "",
            evidence_title,
            f"- claim_ceiling_before_strict_proof: `{evidence.get('claim_ceiling_before_strict_proof', 'review-bound')}`",
            "- strict-runtime gates delivery-ready; Agentic review gates implementation value.",
            "",
        ]
    )
    return "\n".join(lines)


def write_agentic_implementation_loop_artifacts(
    *,
    output_dir: Path,
    case_name: str,
    version: str,
    implementation_bindings: dict[str, Any],
    test_richness_review: dict[str, Any],
    mainline_verification_mode: str,
    dispatch_lane_enabled: bool,
    output_locale: str = "zh-CN",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    loop = build_agentic_implementation_loop(
        case_name=case_name,
        version=version,
        implementation_bindings=implementation_bindings,
        test_richness_review=test_richness_review,
        mainline_verification_mode=mainline_verification_mode,
        dispatch_lane_enabled=dispatch_lane_enabled,
        output_locale=output_locale,
    )
    json_path = output_dir / "agentic-implementation-loop.json"
    markdown_path = output_dir / "agentic-implementation-loop.md"
    json_path.write_text(json.dumps(loop, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(
        render_agentic_implementation_loop_markdown(loop, output_locale=output_locale),
        encoding="utf-8",
    )
    return {
        **loop["summary"],
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }
