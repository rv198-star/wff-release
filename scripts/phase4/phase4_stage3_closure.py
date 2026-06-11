#!/usr/bin/env python3
"""
Close Phase-4 testing-validation from Stage-02 evidence.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from pathlib import Path
import re
from typing import Any

from common.claim_ceiling_surface import claim_ceiling_allows_phase4_validation_entry, claim_ceiling_blocks_ready
from common.output_language import localize_phase4_stage3_closure_markdown
from phase4.phase4_common import (
    build_phase4_claim_ceiling_report,
    ensure_list,
    load_json,
    relative_to_root,
    render_markdown_table,
    utc_now_iso,
    write_json,
    write_text,
)
from phase4.phase4_stage1_planning import STAGE_DIRNAME as STAGE01_DIRNAME
from phase4.phase4_stage2_execution import STAGE_DIRNAME as STAGE02_DIRNAME, item_has_residual_review


STAGE_DIRNAME = "stage-03-validation-closure-and-delivery-readiness-judgment"


def decide_closure(items: list[dict[str, Any]]) -> tuple[str, str]:
    functional_items = [item for item in items if item["acceptance_type"] == "functional"]
    data_fidelity_items = [item for item in items if item["acceptance_type"] == "data-fidelity"]
    ui_items = [item for item in items if item["acceptance_type"] == "ui-review"]
    visual_items = [item for item in items if item["acceptance_type"] == "visual-evidence"]
    non_functional_items = [item for item in items if item["acceptance_type"] != "functional"]
    signoff_pending_items = [
        item
        for item in items
        if item.get("human_signoff_required") and item.get("human_signoff_status") == "review-bound"
    ]
    signoff_not_ready_items = [
        item
        for item in items
        if item.get("human_signoff_required") and item.get("human_signoff_status") == "not-ready"
    ]
    ui_blocked_items = [item for item in ui_items if item["status"] in {"blocked", "not-run"}]
    visual_blocked_items = [item for item in visual_items if item["status"] in {"blocked", "not-run"}]

    if any(item["status"] not in {"pass", "conditional-pass"} for item in functional_items):
        return "return", "One or more mandatory functional acceptance items did not pass."
    if any(item["status"] not in {"pass", "conditional-pass"} for item in data_fidelity_items):
        return "return", "One or more mandatory data-fidelity acceptance items did not pass."
    if any(item["status"] == "fail" for item in non_functional_items):
        return "return", "A non-functional UI/visual acceptance item failed explicitly."
    if ui_blocked_items or visual_blocked_items:
        reasons: list[str] = []
        if ui_blocked_items:
            reasons.append("one or more UI review items are structurally blocked")
        if visual_blocked_items:
            reasons.append("one or more visual-evidence items are structurally blocked")
        return "return", "Phase-4 non-functional evidence is incomplete because " + " and ".join(reasons) + "."
    if any(item["status"] == "conditional-pass" for item in [*functional_items, *data_fidelity_items]):
        return (
            "pass-with-mock-dependency",
            "Functional acceptance is only conditionally green because Phase-3 runtime truth still depends on mock or unresolved runtime-environment evidence.",
        )
    ui_pending = any(item["status"] in {"review-bound", "blocked", "not-run"} for item in ui_items)
    visual_pending = any(item["status"] in {"review-bound", "blocked", "not-run"} for item in visual_items)
    signoff_pending = bool(signoff_pending_items)
    signoff_not_ready = bool(signoff_not_ready_items)
    if ui_pending or visual_pending or signoff_pending or signoff_not_ready:
        reasons: list[str] = []
        if ui_pending:
            reasons.append("some UI review items remain unresolved")
        if visual_pending:
            reasons.append("visual-evidence capture remains review-bound")
        if signoff_pending:
            reasons.append("critical-path human signoff is still pending")
        if signoff_not_ready:
            reasons.append("some critical-path items have not yet reached the human signoff boundary")
        return "pass-with-review-bound-items", "Functional items passed, but " + "; ".join(reasons) + "."
    return "pass", "All acceptance item types passed with explicit evidence."


def stage1_closure_blocker(stage1_summary: dict[str, Any]) -> str:
    claim_ceiling_report = (
        stage1_summary.get("phase3_claim_ceiling_report")
        if isinstance(stage1_summary.get("phase3_claim_ceiling_report"), dict)
        else {}
    )
    if claim_ceiling_blocks_ready(claim_ceiling_report) and not claim_ceiling_allows_phase4_validation_entry(claim_ceiling_report):
        resolved_state = str(claim_ceiling_report.get("resolved_formal_state") or "unknown").strip()
        return (
            "Phase-3 claim ceiling is "
            f"`{resolved_state}`; Phase-4 cannot promote capped upstream evidence to testing-validation-complete."
        )
    if not bool(stage1_summary.get("trace_mapping_complete")):
        return "Phase-4 Stage-01 trace mapping is incomplete; validation closure must return to the upstream contract boundary."
    high_priority_unmapped_count = int(stage1_summary.get("high_priority_unmapped_count") or 0)
    if high_priority_unmapped_count > 0:
        return (
            "Phase-4 Stage-01 found "
            f"{high_priority_unmapped_count} high-priority Phase-2 decision(s) without explicit acceptance coverage."
        )
    return ""


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def strip_markdown_scalar(value: str) -> str:
    cleaned = str(value or "").strip()
    if len(cleaned) >= 2 and cleaned.startswith("`") and cleaned.endswith("`"):
        return cleaned[1:-1].strip()
    return cleaned


def unique_strings(values: list[str], *, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = re.sub(r"\s+", " ", strip_markdown_scalar(value)).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def extract_esp_case_signals(esp_text: str) -> dict[str, list[str]]:
    adr_titles = unique_strings(
        re.findall(r"-\s+title:\s+`?([^`\n]+)`?", esp_text),
        limit=5,
    )
    tradeoff_signals: list[str] = []
    for line in esp_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| TD-"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 4:
            tradeoff_signals.append(" / ".join(cell for cell in cells[1:4] if cell))
    return {
        "architecture_decisions": adr_titles,
        "tradeoff_signals": unique_strings(tradeoff_signals, limit=5),
    }


def extract_openapi_operation_ids(phase3_root: Path) -> list[str]:
    for candidate in ("openapi-final.json", "openapi-final.yaml", "openapi.yaml", "openapi.json"):
        spec_path = phase3_root / candidate
        if not spec_path.exists():
            continue
        text = spec_path.read_text(encoding="utf-8")
        payload = load_json_if_exists(spec_path)
        operation_ids: list[str] = []
        if payload:
            paths = payload.get("paths", {})
            if isinstance(paths, dict):
                for path_item in paths.values():
                    if not isinstance(path_item, dict):
                        continue
                    for operation in path_item.values():
                        if isinstance(operation, dict) and str(operation.get("operationId") or "").strip():
                            operation_ids.append(str(operation["operationId"]))
        if not operation_ids:
            operation_ids = re.findall(r"\boperationId:\s*([A-Za-z0-9_-]+)", text)
        return unique_strings(operation_ids, limit=8)
    return []


def build_upstream_case_context(phase3_root: Path, stage1_summary: dict[str, Any]) -> dict[str, Any]:
    phase2_root_raw = str(stage1_summary.get("phase2_root") or "").strip()
    phase2_root = Path(phase2_root_raw) if phase2_root_raw else None
    esp_text = read_text_if_exists(phase2_root / "engineering-spec-pack.md") if phase2_root else ""
    esp_signals = extract_esp_case_signals(esp_text)
    operation_ids = extract_openapi_operation_ids(phase3_root)
    return {
        "phase2_root": phase2_root_raw,
        "phase3_verdict": str(stage1_summary.get("phase3_mainline_verdict") or ""),
        "phase3_total_score": str(stage1_summary.get("phase3_mainline_total_score") or ""),
        "architecture_decisions": esp_signals["architecture_decisions"],
        "tradeoff_signals": esp_signals["tradeoff_signals"],
        "operation_ids": operation_ids,
    }


def render_upstream_case_context_markdown(context: dict[str, Any] | None) -> list[str]:
    if not context:
        return []
    lines = [
        "## Upstream Case Context",
        "- purpose: Bind this closure judgment to the concrete upstream case instead of emitting a generic validation template.",
        "- claim_ceiling: context summary only; it does not create release approval or new upstream truth.",
        f"- phase3_mainline_verdict: `{context.get('phase3_verdict') or 'unknown'}`",
        f"- phase3_mainline_total_score: `{context.get('phase3_total_score') or 'unknown'}`",
        "- key_architecture_decisions:",
    ]
    decisions = [str(value) for value in ensure_list(context.get("architecture_decisions")) if str(value).strip()]
    if decisions:
        lines.extend(f"  - {decision}" for decision in decisions)
    else:
        lines.append("  - review-bound: no Phase-2 decision title was available to Stage-03 closure")
    lines.append("- operation_scope:")
    operations = [str(value) for value in ensure_list(context.get("operation_ids")) if str(value).strip()]
    if operations:
        lines.extend(f"  - {operation}" for operation in operations)
    else:
        lines.append("  - review-bound: no Phase-3 operation id was available to Stage-03 closure")
    lines.append("- tradeoff_signals:")
    tradeoffs = [str(value) for value in ensure_list(context.get("tradeoff_signals")) if str(value).strip()]
    if tradeoffs:
        lines.extend(f"  - {tradeoff}" for tradeoff in tradeoffs)
    else:
        lines.append("  - review-bound: no Phase-2 tradeoff signal was available to Stage-03 closure")
    lines.append("")
    return lines


def build_closure_markdown(
    decision: str,
    rationale: str,
    items: list[dict[str, Any]],
    upstream_context: dict[str, Any] | None = None,
) -> str:
    review_bound_rows = [
        [
            item["test_id"],
            item["acceptance_type"],
            item["status"],
            item.get("risk_weight", ""),
            str(bool(item.get("critical_path"))).lower(),
            item.get("human_signoff_status", "not-required"),
            item["acceptance_item"],
            item["actual_result"],
        ]
        for item in items
        if item["status"] in {"conditional-pass", "review-bound", "blocked", "fail"} or item_has_residual_review(item)
    ]
    return "\n".join(
        [
            "# Test Closure Judgment",
            "",
            "## Closure Verdict",
            f"- closure_decision: `{decision}`",
            f"- rationale: {rationale}",
            "- phase_boundary_rule: Phase-4 closes testing-validation only; it does not declare final release approval.",
            "",
            *render_upstream_case_context_markdown(upstream_context),
            "## Residual Review-Bound / Returned Items",
            render_markdown_table(
                ["test_id", "acceptance_type", "status", "risk_weight", "critical_path", "human_signoff_status", "acceptance_item", "actual_result"],
                review_bound_rows,
            ),
            "",
            "## Downstream May Assume",
            "- mandatory functional acceptance stayed bound to explicit `TEST-* -> API-* -> REQ-*` evidence.",
            "- inherited Phase-3 contract/runtime evidence was used as the primary execution basis.",
            "- any `conditional-pass` runtime-truth result stays explicit in the closure decision instead of being flattened into `pass`.",
            "",
            "## Downstream Must Not Assume",
            "- screenshot-backed visual sign-off exists unless Stage-02 recorded real visual assets.",
            "- critical-path human review sign-off exists unless Stage-02 recorded it explicitly.",
            "- runtime truth is fully real when the closure decision is `pass-with-mock-dependency`.",
            "- Phase-4 has granted release approval.",
        ]
    ) + "\n"


def build_downstream_boundary_markdown(decision: str) -> str:
    return "\n".join(
        [
            "# Downstream Boundary Note",
            "",
            f"- closure_decision: `{decision}`",
            "- Phase-4 provides validation judgment only.",
            "- Optional Phase-4 Stage-04 release-readiness handling, or equivalent downstream governance, must still decide go/no-go, manual sign-off, and deployment approval.",
            "- Any `ui-review` / `visual-evidence` item that remains review-bound, any critical-path item still pending sign-off, or any item that has not yet reached the sign-off boundary, must stay visible downstream; it cannot be silently reclassified as passed.",
        ]
    ) + "\n"


def classify_remediation_target(
    stage1_summary: dict[str, Any],
    items: list[dict[str, Any]],
    phase3_runtime_truth: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    phase3_runtime_truth = phase3_runtime_truth or {}
    if not bool(stage1_summary.get("trace_mapping_complete")) or int(stage1_summary.get("high_priority_unmapped_count") or 0) > 0:
        return (
            "P2",
            "phase2-validation-contract-gap",
            "Phase-4 could not map validation coverage back to the accepted Phase-2 contract strongly enough.",
        )

    returned_items = [item for item in items if item.get("status") in {"fail", "blocked", "not-run"}]
    functional_or_data = [
        item for item in returned_items if item.get("acceptance_type") in {"functional", "data-fidelity"}
    ]
    if functional_or_data:
        reason_text = " ".join(str(item.get("actual_result") or "") for item in functional_or_data).lower()
        if "no linked automated test targets" in reason_text or "no recorded evidence" in reason_text:
            if bool(phase3_runtime_truth.get("mainline_backend_verification_present")) and not bool(
                phase3_runtime_truth.get("full_targeted_evidence_present")
            ):
                return (
                    "P3",
                    "missing-phase3-full-targeted-evidence",
                    "Phase-3 mainline evidence is present but does not include full targeted SQL / contract / scenario / replay evidence; rerun P3 strict-runtime with full targeted evidence before P4 closure.",
                )
            return (
                "P3",
                "missing-phase3-evidence",
                "Mandatory functional/data-fidelity acceptance could not find enough Phase-3 execution evidence.",
            )
        return (
            "P3",
            "phase3-implementation-or-runtime-evidence-failure",
            "Mandatory functional/data-fidelity acceptance failed against Phase-3 implementation or runtime evidence.",
        )

    non_functional_failures = [
        item for item in returned_items if item.get("acceptance_type") in {"ui-review", "visual-evidence"}
    ]
    if non_functional_failures:
        return (
            "P3",
            "phase3-ui-or-visual-validation-failure",
            "A UI/visual validation item failed explicitly or is structurally blocked.",
        )

    if not bool(stage1_summary.get("phase3_mainline_summary_present")):
        return (
            "P3",
            "missing-phase3-mainline-anchor",
            "Phase-4 is missing the upstream Phase-3 mainline truth anchor required for validation closure.",
        )

    return (
        "P4",
        "phase4-closure-classification-gap",
        "Phase-4 returned but no upstream remediation class was identified from the recorded item statuses.",
    )


def suggested_commands_for_target(return_target: str, *, phase3_root: Path, phase2_root: str, output_dir: Path) -> list[str]:
    if return_target == "P4":
        return [
            "python3 scripts/phase4/run_phase4_first_version.py "
            f"--phase3-root {phase3_root} "
            f"--output-dir {output_dir.parent / 'phase4-rerun'} "
            "--version <next-version> --output-locale zh-CN"
        ]
    if return_target == "P3":
        commands = []
        commands.append(
            "rerun P3 with the implementation-delivery profile/source tree "
            f"--phase2-root {phase2_root or '<phase2-root>'} "
            f"--output-dir {phase3_root.parent / 'phase3-rerun'} "
            "--version <next-version-p3> --output-locale zh-CN --full-targeted-evidence"
        )
        commands.append(
            "python3 scripts/phase4/run_phase4_first_version.py "
            f"--phase3-root {phase3_root.parent / 'phase3-rerun'} "
            f"--output-dir {output_dir.parent / 'phase4-rerun'} "
            "--version <next-version-p4> --output-locale zh-CN"
        )
        return commands
    if return_target == "P2":
        return [
            "python3 scripts/phase2/run_phase2_fresh_generation.py "
            "--phase1-prd <phase1-prd> --output-dir <new-phase2-root> "
            "--version <next-version-p2> --output-locale zh-CN --run-wrapper",
            "rerun P3 with the implementation-delivery profile/source tree "
            "--phase2-root <new-phase2-root> --output-dir <new-phase3-root> "
            "--version <next-version-p3> --output-locale zh-CN --full-targeted-evidence",
            "python3 scripts/phase4/run_phase4_first_version.py "
            "--phase3-root <new-phase3-root> --output-dir <new-phase4-root> "
            "--version <next-version-p4> --output-locale zh-CN",
        ]
    return [
        "Return to the owning upstream phase identified in `return_target`, then rerun each downstream phase from that boundary."
    ]


def build_remediation_packet(
    *,
    decision: str,
    rationale: str,
    stage1_summary: dict[str, Any],
    items: list[dict[str, Any]],
    phase3_runtime_truth: dict[str, Any] | None = None,
    phase3_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    returned_items = [
        item
        for item in items
        if item.get("status") in {"fail", "blocked", "not-run"}
        or (
            item.get("acceptance_type") in {"functional", "data-fidelity"}
            and item.get("status") not in {"pass", "conditional-pass"}
        )
    ]
    phase3_runtime_truth = phase3_runtime_truth or {}
    return_target, reason_class, required_action = classify_remediation_target(stage1_summary, items, phase3_runtime_truth)
    phase2_root = str(stage1_summary.get("phase2_root") or "").strip()
    minimum_rerun_from = {
        "P4": "phase4",
        "P3": "phase3",
        "P2": "phase2",
        "P1/P2": "phase1",
    }.get(return_target, "phase4")
    evidence_refs = []
    for item in returned_items:
        evidence_refs.extend(str(path) for path in ensure_list(item.get("evidence_path")) if str(path).strip())
    evidence_refs.extend(
        [
            "stage-01-acceptance-coverage-planning/acceptance-catalog.json",
            "stage-01-acceptance-coverage-planning/decision-coverage-alignment.json",
            "stage-02-evidence-execution-and-defect-identification/test-execution-results.json",
        ]
    )
    evidence_refs.extend(
        str(path)
        for path in ensure_list(phase3_runtime_truth.get("mainline_backend_verification_report_paths"))
        if str(path).strip()
    )
    evidence_refs.extend(
        str(path)
        for path in ensure_list(phase3_runtime_truth.get("full_targeted_report_paths"))
        if str(path).strip()
    )
    if stage1_summary.get("phase3_mainline_verdict"):
        evidence_refs.append(str(stage1_summary.get("phase3_mainline_verdict")))
    return {
        "generated_at": utc_now_iso(),
        "closure_decision": decision,
        "closure_rationale": rationale,
        "return_target": return_target,
        "reason_class": reason_class,
        "required_action": required_action,
        "minimum_rerun_from": minimum_rerun_from,
        "downstream_validation_required": ["phase4"] if return_target == "P4" else [minimum_rerun_from, "phase4"],
        "phase3_root": str(phase3_root),
        "phase2_root": phase2_root,
        "affected_item_count": len(returned_items),
        "affected_items": [
            {
                "test_id": str(item.get("test_id") or ""),
                "acceptance_type": str(item.get("acceptance_type") or ""),
                "status": str(item.get("status") or ""),
                "actual_result": str(item.get("actual_result") or ""),
                "evidence_path": [str(path) for path in ensure_list(item.get("evidence_path")) if str(path).strip()],
            }
            for item in returned_items
        ],
        "evidence_refs": list(dict.fromkeys(evidence_refs)),
        "suggested_commands": suggested_commands_for_target(
            return_target,
            phase3_root=phase3_root,
            phase2_root=phase2_root,
            output_dir=output_dir,
        ),
    }


def build_remediation_markdown(packet: dict[str, Any]) -> str:
    rows = [
        [
            item["test_id"],
            item["acceptance_type"],
            item["status"],
            item["actual_result"],
            item["evidence_path"],
        ]
        for item in ensure_list(packet.get("affected_items"))
        if isinstance(item, dict)
    ]
    return "\n".join(
        [
            "# Phase-4 Remediation Packet",
            "",
            f"- closure_decision: `{packet['closure_decision']}`",
            f"- return_target: `{packet['return_target']}`",
            f"- reason_class: `{packet['reason_class']}`",
            f"- minimum_rerun_from: `{packet['minimum_rerun_from']}`",
            f"- required_action: {packet['required_action']}",
            "",
            "## Affected Items",
            render_markdown_table(["test_id", "acceptance_type", "status", "actual_result", "evidence_path"], rows),
            "",
            "## Suggested Commands",
            *[f"- `{command}`" for command in ensure_list(packet.get("suggested_commands"))],
        ]
    ) + "\n"


def build_phase4_stage3_closure(
    *,
    phase3_root: Path,
    output_dir: Path,
    title: str,
    version: str,
    output_locale: str | None = None,
) -> dict[str, Any]:
    stage01_dir = output_dir / STAGE01_DIRNAME
    stage02_dir = output_dir / STAGE02_DIRNAME
    stage03_dir = output_dir / STAGE_DIRNAME
    stage03_dir.mkdir(parents=True, exist_ok=True)

    stage1_summary = load_json(stage01_dir / "stage-01-summary.json")
    upstream_claim_ceiling_report = (
        stage1_summary.get("phase3_claim_ceiling_report")
        if isinstance(stage1_summary.get("phase3_claim_ceiling_report"), dict)
        else {}
    )
    stage2_results = load_json(stage02_dir / "test-execution-results.json")
    phase3_runtime_truth = stage2_results.get("phase3_runtime_truth", {})
    if not isinstance(phase3_runtime_truth, dict):
        phase3_runtime_truth = {}
    items = [dict(item) for item in ensure_list(stage2_results.get("items"))]
    stage1_blocker = stage1_closure_blocker(stage1_summary)
    if stage1_blocker:
        decision, rationale = "return", stage1_blocker
    else:
        decision, rationale = decide_closure(items)
        if (
            decision == "pass"
            and claim_ceiling_blocks_ready(upstream_claim_ceiling_report)
            and claim_ceiling_allows_phase4_validation_entry(upstream_claim_ceiling_report)
        ):
            upstream_state = str(upstream_claim_ceiling_report.get("resolved_formal_state") or "unknown").strip()
            decision = "pass-with-review-bound-items"
            rationale = (
                "Functional items passed, but upstream Phase-3 claim ceiling is "
                f"`{upstream_state}` and caps validation closure to review-bound."
            )
    upstream_context = build_upstream_case_context(phase3_root, stage1_summary)

    closure_md_path = stage03_dir / "test-closure-judgment.md"
    boundary_md_path = stage03_dir / "downstream-boundary-note.md"
    remediation_json_path = stage03_dir / "remediation-packet.json"
    remediation_md_path = stage03_dir / "remediation-packet.md"
    summary_path = stage03_dir / "stage-03-summary.json"
    gate_path = output_dir / "phase4-delivery-gate.json"

    write_text(
        closure_md_path,
        localize_phase4_stage3_closure_markdown(
            build_closure_markdown(decision, rationale, items, upstream_context),
            output_locale,
        ),
    )
    write_text(
        boundary_md_path,
        localize_phase4_stage3_closure_markdown(build_downstream_boundary_markdown(decision), output_locale),
    )
    remediation_packet: dict[str, Any] | None = None
    if decision == "return":
        remediation_packet = build_remediation_packet(
            decision=decision,
            rationale=rationale,
            stage1_summary=stage1_summary,
            items=items,
            phase3_runtime_truth=phase3_runtime_truth,
            phase3_root=phase3_root,
            output_dir=output_dir,
        )
        write_json(remediation_json_path, remediation_packet)
        write_text(
            remediation_md_path,
            localize_phase4_stage3_closure_markdown(build_remediation_markdown(remediation_packet), output_locale),
        )

    requested_formal_state = {
        "pass": "testing-validation-complete",
        "pass-with-mock-dependency": "testing-validation-complete-with-mock-dependency",
        "pass-with-review-bound-items": "testing-validation-complete-with-review-bound-items",
        "return": "testing-validation-return-required",
    }[decision]
    summary_gate_checks = {
        "review_bound_count": len([item for item in items if item["status"] == "review-bound"]),
        "signoff_pending_count": len(
            [item for item in items if item.get("human_signoff_required") and item.get("human_signoff_status") == "review-bound"]
        ),
        "signoff_not_ready_count": len(
            [item for item in items if item.get("human_signoff_required") and item.get("human_signoff_status") == "not-ready"]
        ),
        "blocking_count": len([item for item in items if item["status"] in {"fail", "blocked"}]),
    }
    claim_ceiling_report = build_phase4_claim_ceiling_report(
        requested_formal_state=requested_formal_state,
        closure_decision=decision,
        checks=summary_gate_checks,
        upstream_claim_ceiling_report=upstream_claim_ceiling_report,
    )

    summary = {
        "stage": "validation-closure-and-delivery-readiness-judgment",
        "title": title,
        "version": version,
        "generated_at": utc_now_iso(),
        "phase3_root": str(phase3_root),
        "output_dir": str(stage03_dir),
        "phase3_mainline_summary_present": bool(stage1_summary.get("phase3_mainline_summary_present")),
        "phase3_mainline_verdict": str(stage1_summary.get("phase3_mainline_verdict") or ""),
        "phase3_mainline_total_score": stage1_summary.get("phase3_mainline_total_score"),
        "phase3_mainline_backend_verification_present": bool(
            phase3_runtime_truth.get("mainline_backend_verification_present")
        ),
        "phase3_full_targeted_evidence_present": bool(phase3_runtime_truth.get("full_targeted_evidence_present")),
        "phase3_full_targeted_evidence_status": str(
            phase3_runtime_truth.get("full_targeted_evidence_status") or "unknown"
        ),
        "upstream_claim_ceiling_report": upstream_claim_ceiling_report,
        "upstream_claim_ceiling_resolved_formal_state": str(
            upstream_claim_ceiling_report.get("resolved_formal_state") or "unknown"
        ),
        "upstream_claim_ceiling_blocks_ready": claim_ceiling_blocks_ready(upstream_claim_ceiling_report),
        "recommended_formal_state": str(claim_ceiling_report["resolved_formal_state"]),
        "claim_ceiling_report": claim_ceiling_report,
        "upstream_case_context": upstream_context,
        "closure_decision": decision,
        "closure_rationale": rationale,
        "functional_pass": all(
            item["status"] == "pass" for item in items if item["acceptance_type"] == "functional"
        ),
        "review_bound_count": len([item for item in items if item["status"] == "review-bound"]),
        "signoff_pending_count": len(
            [item for item in items if item.get("human_signoff_required") and item.get("human_signoff_status") == "review-bound"]
        ),
        "signoff_not_ready_count": len(
            [item for item in items if item.get("human_signoff_required") and item.get("human_signoff_status") == "not-ready"]
        ),
        "blocking_count": len([item for item in items if item["status"] in {"fail", "blocked"}]),
        "artifacts": {
            "closure_md": relative_to_root(closure_md_path, output_dir),
            "boundary_md": relative_to_root(boundary_md_path, output_dir),
            "remediation_packet_json": relative_to_root(remediation_json_path, output_dir) if remediation_packet else "",
            "remediation_packet_md": relative_to_root(remediation_md_path, output_dir) if remediation_packet else "",
        },
        "remediation": remediation_packet or {},
        "stage01_trace_mapping_complete": bool(stage1_summary.get("trace_mapping_complete")),
        "stage01_decision_alignment_complete": bool(stage1_summary.get("decision_alignment_complete")),
        "stage01_high_priority_unmapped_count": int(stage1_summary.get("high_priority_unmapped_count") or 0),
    }
    write_json(summary_path, summary)

    gate_checks = {
        "phase3_mainline_summary_present": bool(stage1_summary.get("phase3_mainline_summary_present")),
        "phase3_mainline_backend_verification_present": bool(
            phase3_runtime_truth.get("mainline_backend_verification_present")
        ),
        "phase3_full_targeted_evidence_present": bool(phase3_runtime_truth.get("full_targeted_evidence_present")),
        "phase3_full_targeted_evidence_status": str(
            phase3_runtime_truth.get("full_targeted_evidence_status") or "unknown"
        ),
        "upstream_claim_ceiling_resolved_formal_state": str(
            upstream_claim_ceiling_report.get("resolved_formal_state") or "unknown"
        ),
        "upstream_claim_ceiling_blocks_ready": claim_ceiling_blocks_ready(upstream_claim_ceiling_report),
        "functional_items_all_pass": summary["functional_pass"],
        "trace_mapping_complete": bool(stage1_summary.get("trace_mapping_complete")),
        "decision_alignment_complete": bool(stage1_summary.get("decision_alignment_complete")),
        "visual_review_items_explicit": True,
        "review_bound_count": summary["review_bound_count"],
        "signoff_pending_count": summary["signoff_pending_count"],
        "signoff_not_ready_count": summary["signoff_not_ready_count"],
        "blocking_count": summary["blocking_count"],
    }
    gate = {
        "generated_at": utc_now_iso(),
        "phase3_root": str(phase3_root),
        "recommended_formal_state": str(claim_ceiling_report["resolved_formal_state"]),
        "closure_decision": decision,
        "overall_quality_gate": decision,
        "claim_ceiling_report": claim_ceiling_report,
        "checks": gate_checks,
        "warnings": [
            message
            for message in [
                "Visual/manual acceptance remains review-bound and must stay explicit downstream."
                if decision == "pass-with-review-bound-items"
                else "",
                "Critical-path human signoff is still pending."
                if summary["signoff_pending_count"] > 0
                else "",
                "Some critical-path items have not yet reached the human-signoff boundary."
                if summary["signoff_not_ready_count"] > 0
                else "",
                "Some high-priority Phase-2 decisions are not covered by explicit Phase-4 acceptance items."
                if int(stage1_summary.get("high_priority_unmapped_count") or 0) > 0
                else "",
                "Upstream Phase-3 claim ceiling caps testing-validation-complete."
                if claim_ceiling_blocks_ready(upstream_claim_ceiling_report)
                and claim_ceiling_allows_phase4_validation_entry(upstream_claim_ceiling_report)
                else "Upstream Phase-3 claim ceiling blocks testing-validation-complete."
                if claim_ceiling_blocks_ready(upstream_claim_ceiling_report)
                else "",
            ]
            if message
        ],
        "failures": [rationale] if decision == "return" else [],
        "artifacts": {
            "closure_md": relative_to_root(closure_md_path, output_dir),
            "boundary_md": relative_to_root(boundary_md_path, output_dir),
            "remediation_packet_json": relative_to_root(remediation_json_path, output_dir) if remediation_packet else "",
            "remediation_packet_md": relative_to_root(remediation_md_path, output_dir) if remediation_packet else "",
            "stage03_summary_json": relative_to_root(summary_path, output_dir),
        },
        "remediation": remediation_packet or {},
    }
    write_json(gate_path, gate)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Close Phase-4 testing-validation")
    parser.add_argument("--phase3-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--title", default="Phase-4 Testing Validation")
    parser.add_argument("--version", default="0.1.0")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = build_phase4_stage3_closure(
        phase3_root=Path(args.phase3_root).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        title=args.title,
        version=args.version,
    )
    print(summary["closure_decision"])
    return 0 if summary["closure_decision"] != "return" else 1


if __name__ == "__main__":
    raise SystemExit(main())
