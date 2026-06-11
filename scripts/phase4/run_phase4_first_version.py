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
from common.cross_phase_surface_policy import resolve_cross_phase_surface_path
from common.human_review_surface import emit_human_review_surface
from common.output_language import resolve_output_locale
from phase4.phase4_common import (
    build_phase4_metadata_payload,
    build_phase4_mainline_assessment,
    build_phase4_mainline_assessment_summary,
    build_phase4_quality_check_payload,
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


def run_phase4_mainline(context: Phase4RunnerContext) -> Phase4RunnerResult:
    phase3_text_parts: list[str] = []
    for name in ("phase-3-acceptance-report.md", "phase-3-execution-report.md", "phase3-delivery-gate.json"):
        path = context.phase3_root / name
        if path.exists():
            phase3_text_parts.append(path.read_text(encoding="utf-8"))
    contamination_report = build_contamination_report(
        "\n\n".join(phase3_text_parts),
        source_label=str(context.phase3_root),
        boundary="p3-to-p4",
        output_path=resolve_cross_phase_surface_path(
            context.output_dir,
            "phase4",
            "p3-to-p4-contamination-report.json",
        ),
    )
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
        validate_phase4_runner_args(args)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}")
        return 2

    context = build_phase4_runner_context(args)
    try:
        result = run_phase4_mainline(context)
    except Phase4ContaminationBoundaryError as exc:
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
    return emit_phase4_runner_summary(build_phase4_runner_summary(context, result, contract_report, stage4_summary))


if __name__ == "__main__":
    raise SystemExit(main())
