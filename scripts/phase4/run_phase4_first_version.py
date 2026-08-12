#!/usr/bin/env python3
"""
Generate the first complete Phase-4 validation package from a completed Phase-3 root.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.contamination_boundary import build_contamination_report
from common.contamination_boundary import build_output_contamination_report_for_paths
from common.contamination_boundary import collect_text_output_paths
from common.cross_phase_surface_policy import resolve_cross_phase_surface_path
from common.human_review_surface import emit_human_review_surface
from common.output_language import resolve_output_locale
from common.source_admission import build_source_admission_report_for_paths
from common.wff_core_runtime import WFFCoreConsumerError, require_capability_binding
from phase4.phase4_common import (
    build_phase4_metadata_payload,
    build_phase4_mainline_assessment,
    build_phase4_mainline_assessment_summary,
    build_phase4_quality_check_payload,
    discover_phase3_trace_registry_path,
    load_phase3_current_closure_summary,
    utc_now_iso,
    write_json,
    write_phase4_mainline_assessment_artifacts,
)
from phase4.phase4_claim_control import emit_phase4_claim_control_report
from phase4.phase4_stage1_planning import build_phase4_stage1_planning
from phase4.phase4_stage2_execution import build_phase4_stage2_execution
from phase4.phase4_stage3_closure import build_phase4_stage3_closure
from phase4.phase4_output_contract import validate_phase4_output_contract, write_report
from phase4.phase4_stage4_release_readiness import build_phase4_stage4_release_readiness


@dataclass(frozen=True)
class Phase4RunnerContext:
    phase3_root: Path
    output_dir: Path
    title: str
    version: str
    output_locale: str
    external_evidence_manifest: Path | None
    external_evidence_dir: Path | None
    enable_stage4: bool
    release_signoff_manifest: Path | None
    metadata_path: Path
    quality_path: Path


@dataclass(frozen=True)
class Phase4RunnerResult:
    stage1_summary: dict[str, Any]
    stage2_summary: dict[str, Any]
    stage3_summary: dict[str, Any]
    mainline_assessment: dict[str, Any]
    mainline_artifacts: dict[str, str]
    mainline_summary: dict[str, Any]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the first complete Phase-4 package")
    parser.add_argument("--phase3-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--title", default="Phase-4 First Version")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--external-evidence-manifest")
    parser.add_argument("--external-evidence-dir")
    parser.add_argument("--enable-stage4", action="store_true", help="Generate optional Stage-04 release-readiness artifacts")
    parser.add_argument("--release-signoff-manifest", help="Optional Stage-04 release sign-off / risk acceptance manifest")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    return parser


def parse_phase4_first_version_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def validate_phase4_runner_args(args: argparse.Namespace) -> None:
    if args.external_evidence_dir and not args.external_evidence_manifest:
        raise ValueError("--external-evidence-dir requires --external-evidence-manifest")


class Phase4ContaminationBoundaryError(RuntimeError):
    """Raised when the P3-to-P4 handoff contains configured contamination residue."""


class Phase4SourceAdmissionError(RuntimeError):
    """Raised when the P3-to-P4 handoff is empty or placeholder-only."""


class Phase4GeneratedOutputContaminationError(RuntimeError):
    """Raised when generated Phase-4 output contains configured contamination residue."""


def build_phase4_runner_context(args: argparse.Namespace) -> Phase4RunnerContext:
    phase3_root = Path(args.phase3_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return Phase4RunnerContext(
        phase3_root=phase3_root,
        output_dir=output_dir,
        title=str(args.title).strip() or "Phase-4 First Version",
        version=str(args.version).strip() or "0.1.0",
        output_locale=resolve_output_locale(args.output_locale),
        external_evidence_manifest=Path(args.external_evidence_manifest).resolve() if args.external_evidence_manifest else None,
        external_evidence_dir=Path(args.external_evidence_dir).resolve() if args.external_evidence_dir else None,
        enable_stage4=bool(getattr(args, "enable_stage4", False)),
        release_signoff_manifest=Path(args.release_signoff_manifest).resolve() if getattr(args, "release_signoff_manifest", None) else None,
        metadata_path=output_dir / "phase4-run-metadata.json",
        quality_path=output_dir / "phase4-quality-check.json",
    )


def phase4_handoff_source_paths(phase3_root: Path) -> list[Path]:
    current = load_phase3_current_closure_summary(phase3_root)
    runtime_paths = [phase3_root / str(path) for path in current.get("runtime_evidence_refs", [])]
    return [
        phase3_root / "phase-3-acceptance-report.md",
        phase3_root / "phase-3-execution-report.md",
        phase3_root / "phase3-delivery-gate.json",
        phase3_root / "phase-verdict.json",
        phase3_root / "phase-mainline-scorecard.md",
        phase3_root / "phase-acceptance-matrix.md",
        phase3_root / "contracts" / "openapi.yaml",
        phase3_root / "openapi-final.yaml",
        discover_phase3_trace_registry_path(phase3_root),
        phase3_root / "implementation-bindings.json",
        phase3_root / "p3-agentic-implementation-authority.json",
        phase3_root / "p3-agentic-implementation-application-receipt.json",
        phase3_root / "p3-exact-realization-binding-ledger.json",
        phase3_root / ".phase3-evidence" / "p3-authority-delta-ledger.json",
        *runtime_paths,
    ]


def phase4_required_handoff_source_paths(phase3_root: Path) -> list[Path]:
    return [
        phase3_root / "phase-3-acceptance-report.md",
        phase3_root / "phase-3-execution-report.md",
        phase3_root / "phase3-delivery-gate.json",
        phase3_root / "phase-verdict.json",
        phase3_root / "phase-mainline-scorecard.md",
        phase3_root / "phase-acceptance-matrix.md",
        phase3_root / "phase-3-trace-registry-final.json",
        phase3_root / "implementation-bindings.json",
    ]


def phase4_current_handoff_source_paths(phase3_root: Path) -> list[Path]:
    current = load_phase3_current_closure_summary(phase3_root)
    return [
        phase3_root / "p3-agentic-implementation-authority.json",
        phase3_root / "p3-agentic-implementation-application-receipt.json",
        phase3_root / "p3-exact-realization-binding-ledger.json",
        discover_phase3_trace_registry_path(phase3_root),
        phase3_root / "implementation-bindings.json",
        phase3_root / ".phase3-evidence" / "p3-authority-delta-ledger.json",
        *[phase3_root / str(path) for path in current.get("runtime_evidence_refs", [])],
    ]


def phase4_openapi_handoff_source_group(phase3_root: Path) -> list[Path]:
    return [
        phase3_root / "contracts" / "openapi.yaml",
        phase3_root / "openapi-final.yaml",
    ]


def read_existing_phase4_handoff_source_text(phase3_root: Path) -> str:
    phase3_text_parts: list[str] = []
    for path in phase4_handoff_source_paths(phase3_root):
        if path.exists():
            phase3_text_parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(phase3_text_parts)


def run_phase4_source_admission_preflight(context: Phase4RunnerContext) -> dict[str, Any]:
    current = load_phase3_current_closure_summary(context.phase3_root)
    required_paths = (
        phase4_current_handoff_source_paths(context.phase3_root)
        if current.get("present")
        else phase4_required_handoff_source_paths(context.phase3_root)
    )
    return build_source_admission_report_for_paths(
        required_paths,
        boundary="p3-to-p4",
        source_label=str(context.phase3_root),
        output_path=resolve_cross_phase_surface_path(
            context.output_dir,
            "phase4",
            "p3-to-p4-source-admission-report.json",
        ),
        alternative_path_groups=[phase4_openapi_handoff_source_group(context.phase3_root)],
    )


def run_phase4_handoff_contamination_preflight(context: Phase4RunnerContext) -> dict[str, Any]:
    contamination_report = build_contamination_report(
        read_existing_phase4_handoff_source_text(context.phase3_root),
        source_label=str(context.phase3_root),
        boundary="p3-to-p4",
        output_path=resolve_cross_phase_surface_path(
            context.output_dir,
            "phase4",
            "p3-to-p4-contamination-report.json",
        ),
    )
    return contamination_report


def phase4_generated_output_contamination_paths(context: Phase4RunnerContext) -> list[Path]:
    expected_paths = [
        context.metadata_path,
        context.quality_path,
        context.output_dir / "phase4-delivery-gate.json",
        context.output_dir / "phase-verdict.json",
        context.output_dir / "phase-mainline-scorecard.md",
        context.output_dir / "phase-acceptance-matrix.md",
        resolve_cross_phase_surface_path(context.output_dir, "phase4", "phase4-output-contract-report.json"),
        resolve_cross_phase_surface_path(context.output_dir, "phase4", "phase4-output-contract-report.md"),
        resolve_cross_phase_surface_path(context.output_dir, "phase4", "phase4-claim-control-report.json"),
        resolve_cross_phase_surface_path(context.output_dir, "phase4", "phase4-claim-control-report.md"),
        context.output_dir / "stage-01-acceptance-coverage-planning" / "stage-01-summary.json",
        context.output_dir / "stage-02-evidence-execution-and-defect-identification" / "stage-02-summary.json",
        context.output_dir / "stage-03-validation-closure-and-delivery-readiness-judgment" / "stage-03-summary.json",
    ]
    return collect_text_output_paths(context.output_dir, expected_paths=expected_paths)


def run_phase4_generated_output_contamination_gate(
    context: Phase4RunnerContext,
    *,
    source_fingerprint_text: str | None = None,
) -> dict[str, Any]:
    return build_output_contamination_report_for_paths(
        phase4_generated_output_contamination_paths(context),
        source_fingerprint_text=source_fingerprint_text
        if source_fingerprint_text is not None
        else read_existing_phase4_handoff_source_text(context.phase3_root),
        source_label=str(context.phase3_root),
        boundary="phase-4-generated-output",
        output_path=resolve_cross_phase_surface_path(
            context.output_dir,
            "phase4",
            "phase-4-output-contamination-report.json",
        ),
    )


def run_phase4_mainline(context: Phase4RunnerContext) -> Phase4RunnerResult:
    source_admission_report = run_phase4_source_admission_preflight(context)
    if source_admission_report["overall_status"] == "blocked":
        raise Phase4SourceAdmissionError(
            "p3-to-p4 source admission failed: "
            f"{resolve_cross_phase_surface_path(context.output_dir, 'phase4', 'p3-to-p4-source-admission-report.json')}"
        )
    contamination_report = run_phase4_handoff_contamination_preflight(context)
    if contamination_report["overall_status"] == "blocked":
        raise Phase4ContaminationBoundaryError(
            "p3-to-p4 contamination boundary failed: "
            f"{resolve_cross_phase_surface_path(context.output_dir, 'phase4', 'p3-to-p4-contamination-report.json')}"
        )
    stage1_summary = build_phase4_stage1_planning(
        phase3_root=context.phase3_root,
        output_dir=context.output_dir,
        title=context.title,
        version=context.version,
        output_locale=context.output_locale,
    )
    stage2_summary = build_phase4_stage2_execution(
        phase3_root=context.phase3_root,
        output_dir=context.output_dir,
        title=context.title,
        version=context.version,
        external_evidence_manifest=context.external_evidence_manifest,
        external_evidence_dir=context.external_evidence_dir,
        output_locale=context.output_locale,
    )
    stage3_summary = build_phase4_stage3_closure(
        phase3_root=context.phase3_root,
        output_dir=context.output_dir,
        title=context.title,
        version=context.version,
        output_locale=context.output_locale,
    )
    mainline_assessment = build_phase4_mainline_assessment(
        stage1_summary=stage1_summary,
        stage2_summary=stage2_summary,
        stage3_summary=stage3_summary,
    )
    mainline_artifacts = write_phase4_mainline_assessment_artifacts(
        output_dir=context.output_dir,
        assessment=mainline_assessment,
    )
    mainline_summary = build_phase4_mainline_assessment_summary(
        assessment=mainline_assessment,
        artifact_paths=mainline_artifacts,
    )
    return Phase4RunnerResult(
        stage1_summary=stage1_summary,
        stage2_summary=stage2_summary,
        stage3_summary=stage3_summary,
        mainline_assessment=mainline_assessment,
        mainline_artifacts=mainline_artifacts,
        mainline_summary=mainline_summary,
    )


def build_phase4_runner_metadata(context: Phase4RunnerContext, result: Phase4RunnerResult) -> dict[str, Any]:
    return build_phase4_metadata_payload(
        case_name=context.title,
        version=context.version,
        phase3_root=context.phase3_root,
        artifact_kind="fresh-full-phase4-run",
        generation_entrypoint="scripts/phase4/run_phase4_first_version.py",
        generation_purity="fresh-from-phase3-root",
        external_evidence_manifest=context.external_evidence_manifest,
        extra_fields={
            "mainline_assessment_artifacts": result.mainline_artifacts,
            "mainline_assessment_summary": result.mainline_summary,
            "phase_verdict_path": result.mainline_summary["phase_verdict_path"],
            "phase_verdict": result.mainline_summary["phase_verdict"],
            "phase_total_score": result.mainline_summary["phase_total_score"],
            "phase_review_bound_items_count": result.mainline_summary["review_bound_items_count"],
            "phase_blockers_count": result.mainline_summary["blockers_count"],
            "phase4_remediation": result.stage3_summary.get("remediation", {}),
            "phase4_remediation_packet_json": result.stage3_summary.get("artifacts", {}).get("remediation_packet_json", ""),
            "phase4_remediation_packet_md": result.stage3_summary.get("artifacts", {}).get("remediation_packet_md", ""),
            "stage4_enabled": context.enable_stage4,
            "stage4_release_readiness_decision": "",
            "stage4_output_contract_status": "",
        },
    )


def build_phase4_runner_quality_check(result: Phase4RunnerResult) -> dict[str, Any]:
    return build_phase4_quality_check_payload(
        stage1_summary=result.stage1_summary,
        stage2_summary=result.stage2_summary,
        stage3_summary=result.stage3_summary,
    )


def update_phase4_runner_metadata_with_claim_control(context: Phase4RunnerContext) -> dict[str, Any]:
    claim_control = emit_phase4_claim_control_report(
        phase3_root=context.phase3_root,
        output_dir=context.output_dir,
    )
    metadata = json.loads(context.metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "phase4_claim_control_report_path": claim_control["report_path"],
            "phase4_claim_control_report_md": claim_control["markdown_path"],
            "phase4_claim_control_status": claim_control["report"]["overall_status"],
            "phase4_claim_control_ceiling": claim_control["report"]["claim_ceiling"],
        }
    )
    write_json(context.metadata_path, metadata)
    return claim_control


def write_phase4_runner_support_artifacts(context: Phase4RunnerContext, result: Phase4RunnerResult) -> dict[str, Any]:
    write_json(context.metadata_path, build_phase4_runner_metadata(context, result))
    write_json(context.quality_path, build_phase4_runner_quality_check(result))
    update_phase4_runner_metadata_with_claim_control(context)
    contract_report = validate_phase4_output_contract(context.output_dir)
    write_report(
        contract_report,
        resolve_cross_phase_surface_path(context.output_dir, "phase4", "phase4-output-contract-report.json"),
        resolve_cross_phase_surface_path(context.output_dir, "phase4", "phase4-output-contract-report.md"),
    )
    return contract_report


def phase4_stage_summary_paths(output_dir: Path) -> dict[str, str]:
    return {
        "stage01_summary": str(output_dir / "stage-01-acceptance-coverage-planning" / "stage-01-summary.json"),
        "stage02_summary": str(
            output_dir / "stage-02-evidence-execution-and-defect-identification" / "stage-02-summary.json"
        ),
        "stage03_summary": str(output_dir / "stage-03-validation-closure-and-delivery-readiness-judgment" / "stage-03-summary.json"),
    }


def update_phase4_runner_metadata_with_stage4(context: Phase4RunnerContext, stage4_summary: dict[str, Any]) -> None:
    metadata = json.loads(context.metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "stage4_enabled": True,
            "stage4_release_readiness_decision": stage4_summary.get("release_readiness_decision", ""),
            "stage4_output_contract_status": stage4_summary.get("stage4_output_contract_status", ""),
            "stage4_summary_json": stage4_summary.get("artifacts", {}).get("stage04_summary_json", ""),
        }
    )
    write_json(context.metadata_path, metadata)


def build_phase4_runner_summary(
    context: Phase4RunnerContext,
    result: Phase4RunnerResult,
    contract_report: dict[str, Any] | None = None,
    stage4_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage_summary_paths = phase4_stage_summary_paths(context.output_dir)
    summary = {
        "output_dir": str(context.output_dir),
        **stage_summary_paths,
        "metadata": str(context.metadata_path),
        "quality_check": str(context.quality_path),
        "delivery_gate": str(context.output_dir / "phase4-delivery-gate.json"),
        "output_contract_report": str(
            resolve_cross_phase_surface_path(context.output_dir, "phase4", "phase4-output-contract-report.json")
        ),
        "output_contract_status": (contract_report or {}).get("status", ""),
        "closure_decision": result.stage3_summary["closure_decision"],
        "phase_verdict_path": result.mainline_artifacts["verdict_path"],
        "phase_verdict": result.mainline_assessment["verdict"],
        "phase_total_score": result.mainline_assessment["total_score"],
        "remediation": result.stage3_summary.get("remediation", {}),
        "stage4_enabled": context.enable_stage4,
        "stage4_summary": stage4_summary or {},
        "stage4_release_readiness_decision": (stage4_summary or {}).get("release_readiness_decision", ""),
        "stage4_output_contract_status": (stage4_summary or {}).get("stage4_output_contract_status", ""),
    }
    return summary


def emit_phase4_runner_summary(summary: dict[str, Any]) -> int:
    print(json.dumps(summary, ensure_ascii=False))
    if summary.get("output_contract_status") != "pass":
        return 2
    if summary.get("stage4_enabled") and summary.get("stage4_output_contract_status") != "pass":
        return 2
    return 0 if summary["closure_decision"] != "return" else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_phase4_first_version_args(argv)
    try:
        require_capability_binding(
            "validation-closure",
            phase_id="P4",
            route_key="phase-4",
            required_contracts=(
                "phase-contract",
                "handoff-contract",
                "evidence-contract",
                "claim-state-contract",
                "reentry-return-contract",
            ),
        )
        validate_phase4_runner_args(args)
    except (ValueError, WFFCoreConsumerError) as exc:
        print(f"[BLOCKED] {exc}")
        return 2

    context = build_phase4_runner_context(args)
    try:
        result = run_phase4_mainline(context)
    except (Phase4SourceAdmissionError, Phase4ContaminationBoundaryError) as exc:
        print(f"[BLOCKED] {exc}")
        return 2
    contract_report = write_phase4_runner_support_artifacts(context, result)
    stage4_summary: dict[str, Any] | None = None
    if context.enable_stage4:
        stage4_summary = build_phase4_stage4_release_readiness(
            phase3_root=context.phase3_root,
            output_dir=context.output_dir,
            title=context.title,
            version=context.version,
            s1_s3_contract_report=contract_report,
            release_signoff_manifest=context.release_signoff_manifest,
            output_locale=context.output_locale,
        )
        update_phase4_runner_metadata_with_stage4(context, stage4_summary)
        update_phase4_runner_metadata_with_claim_control(context)
    emit_human_review_surface(context.output_dir, "phase4")
    output_contamination_report = run_phase4_generated_output_contamination_gate(context)
    if output_contamination_report["overall_status"] == "blocked":
        print(
            "[BLOCKED] Phase-4 generated output contamination failed: "
            f"{resolve_cross_phase_surface_path(context.output_dir, 'phase4', 'phase-4-output-contamination-report.json')}"
        )
        print(f"classifications: {', '.join(output_contamination_report['classifications'])}")
        return 2
    return emit_phase4_runner_summary(build_phase4_runner_summary(context, result, contract_report, stage4_summary))


if __name__ == "__main__":
    raise SystemExit(main())
