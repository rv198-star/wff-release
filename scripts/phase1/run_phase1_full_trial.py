#!/usr/bin/env python3
"""
One-click Phase-1 full trial runner.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.output_language import localize_phase1_execution_report, resolve_output_locale
from common.cross_phase_surface_policy import resolve_cross_phase_surface_path
from common.human_review_surface import emit_human_review_surface
from common.claim_control_runtime import (
    CanonicalName,
    ClaimRecord,
    ClaimRelation,
    accepted_claims_from_phase1_trace_units,
    emit_path_b_claim_control_sidecar,
)
from phase1.phase1_emit_depth_runtime_artifacts import DEPTH_RUNTIME_SUMMARY_FILENAME, DEPTH_RUNTIME_TEXT_ARTIFACTS
from phase1.phase1_gate_authority import SUPPRESS_COMPATIBILITY_WARNING_ENV
from phase1.phase1_runtime_metadata import THINKING_VALUE_GAIN_OUTPUT_PROFILES, build_runtime_metadata_lines
from phase1.phase1_trace_units import PHASE1_TRACE_UNIT_GROUP_ORDER, extract_phase1_trace_units
from phase1.phase1_version_contract import normalize_version_identifier


def run(command: list[str]) -> None:
    proc = subprocess.run(command, text=True, env=canonical_driver_env())
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def run_allow_returncodes(command: list[str], allowed: tuple[int, ...]) -> int:
    proc = subprocess.run(command, text=True, env=canonical_driver_env())
    if proc.returncode not in allowed:
        raise SystemExit(proc.returncode)
    return proc.returncode


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_driver_env() -> dict[str, str]:
    env = os.environ.copy()
    env[SUPPRESS_COMPATIBILITY_WARNING_ENV] = "1"
    return env


def command_segment_name(command: list[str], fallback: str) -> str:
    if len(command) > 1:
        stem = Path(str(command[1])).stem.strip()
        if stem:
            return stem
    return fallback


def build_phase1_timing_report_payload(
    *,
    started_at: str,
    finished_at: str,
    total_duration_seconds: float,
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_segments: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(segments, start=1):
        name = str(raw.get("name") or f"segment_{index:02d}").strip()
        normalized_segments[name] = dict(raw)
    longest_segments = sorted(
        normalized_segments.values(),
        key=lambda row: float(row.get("duration_seconds") or 0.0),
        reverse=True,
    )
    return {
        "generated_at": utc_now_iso(),
        "started_at": started_at,
        "finished_at": finished_at,
        "total_duration_seconds": round(max(0.0, float(total_duration_seconds)), 3),
        "segments": normalized_segments,
        "longest_segments": longest_segments[:10],
    }


def append_timing_segment(
    segments: list[dict[str, Any]],
    *,
    name: str,
    started_at: str,
    started_monotonic: float,
    status: str,
    command: list[str] | None = None,
    returncode: int | None = None,
) -> None:
    row: dict[str, Any] = {
        "name": name,
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "duration_seconds": round(max(0.0, time.monotonic() - started_monotonic), 3),
        "status": status,
    }
    if command is not None:
        row["command"] = command
    if returncode is not None:
        row["returncode"] = int(returncode)
    segments.append(row)


def write_phase1_timing_report(
    context: "Phase1FullTrialContext",
    *,
    started_at: str,
    started_monotonic: float,
    segments: list[dict[str, Any]],
) -> Path:
    payload = build_phase1_timing_report_payload(
        started_at=started_at,
        finished_at=utc_now_iso(),
        total_duration_seconds=time.monotonic() - started_monotonic,
        segments=segments,
    )
    context.timing_report.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return context.timing_report


def run_timed(command: list[str], *, segments: list[dict[str, Any]], name: str | None = None) -> None:
    started_at = utc_now_iso()
    started_monotonic = time.monotonic()
    proc = subprocess.run(command, text=True, env=canonical_driver_env())
    status = "pass" if proc.returncode == 0 else "fail"
    append_timing_segment(
        segments,
        name=name or command_segment_name(command, "command"),
        started_at=started_at,
        started_monotonic=started_monotonic,
        status=status,
        command=command,
        returncode=proc.returncode,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def run_allow_returncodes_timed(
    command: list[str],
    allowed: tuple[int, ...],
    *,
    segments: list[dict[str, Any]],
    name: str,
) -> int:
    started_at = utc_now_iso()
    started_monotonic = time.monotonic()
    proc = subprocess.run(command, text=True, env=canonical_driver_env())
    status = "pass" if proc.returncode in allowed else "fail"
    append_timing_segment(
        segments,
        name=name,
        started_at=started_at,
        started_monotonic=started_monotonic,
        status=status,
        command=command,
        returncode=proc.returncode,
    )
    if proc.returncode not in allowed:
        raise SystemExit(proc.returncode)
    return proc.returncode


def run_captured_command_timed(
    command: list[str],
    *,
    segments: list[dict[str, Any]],
    name: str,
) -> subprocess.CompletedProcess[str]:
    started_at = utc_now_iso()
    started_monotonic = time.monotonic()
    proc = subprocess.run(command, capture_output=True, text=True, env=canonical_driver_env())
    append_timing_segment(
        segments,
        name=name,
        started_at=started_at,
        started_monotonic=started_monotonic,
        status="pass" if proc.returncode == 0 else "fail",
        command=command,
        returncode=proc.returncode,
    )
    return proc


def normalize_version(raw: str) -> str:
    return normalize_version_identifier(raw)


def slugify(raw: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return normalized or "phase-1-prd"


def write_draft_report(
    *,
    output: Path,
    source: Path,
    version: str,
    profile: str,
    run_owner: str,
    stage_01: Path,
    stage_02a: Path,
    stage_02b: Path,
    stage_03: Path,
    stage_04: Path,
    assembled_prd: Path,
    prd: Path,
    prd_zh: Path | None,
    evidence: Path,
    depth_mode: str,
    thinking_value_gain_mode: str = "off",
    thinking_value_gain_output_profile: str = "coverage_rich",
    output_locale: str | None = None,
    case_name: str = "phase-1-case",
) -> None:
    metadata_lines = "\n".join(
        build_runtime_metadata_lines(
            depth_mode,
            thinking_value_gain_mode=thinking_value_gain_mode,
            thinking_value_gain_output_profile=thinking_value_gain_output_profile,
        )
    )
    text = f"""# Phase-1 Execution Report

## 1. Run Metadata
- case_name:
  - `{case_name}`
- input_source: `{source.name}`
- run_owner: `{run_owner}`
- run_date: `{version}`
- report_version: `{version}`
- delivery_profile:
  - `{profile}`
{metadata_lines}
- current_overall_status:
  - `review-bound-but-not-ready`

## 2. Stage Output Inventory
- stage_01_output: `{stage_01.name}`
- stage_02a_output: `{stage_02a.name}`
- stage_02b_output: `{stage_02b.name}`
- stage_03_output: `{stage_03.name}`
- stage_04_output: `{stage_04.name}`
- prd_assembled_draft: `{assembled_prd.name}`
- prd_main_document: `{prd.name}`
- localized_reader_evidence_state: `not-requested`
- localized_reader_artifact: `(not generated)`
- localized_reader_integrity_report: `(not generated)`
- legacy_zh_cn_audit_mirror: `{'deprecated / generated' if prd_zh and prd_zh.exists() else 'deprecated / not generated'}`
- prd_convergence_evidence: `{evidence.name}`

## 3. Draft Note
- This is a draft execution report written before executable gate evaluation.
- It exists to provide trial-token and artifact inventory consistency for the first gate run.
- Final verdicts will be overwritten after convergence gates complete.
"""
    output.write_text(localize_phase1_execution_report(text.rstrip() + "\n", output_locale), encoding="utf-8")


@dataclass(frozen=True)
class Phase1FullTrialContext:
    script_dir: Path
    repo_root: Path
    python: str
    source: Path
    output_dir: Path
    version: str
    profile: str
    depth_mode: str
    thinking_value_gain_mode: str
    thinking_value_gain_output_profile: str
    owner: str
    document_name: str
    output_locale: str
    canonical_output_locale: str
    skip_stage_02b: bool
    max_rounds: int
    no_auto_remediate: bool
    emit_legacy_zh_cn_mirror: bool
    commercial_argument_rewrite: Path | None
    narrative_compression_rewrite: Path | None
    case_name: str
    prd_stem: str
    stage_01: Path
    stage_02a: Path
    stage_02b: Path
    stage_03: Path
    stage_04: Path
    assembled_prd: Path
    prd: Path
    prd_zh: Path
    evidence: Path
    report: Path
    snapshot: Path
    depth_runtime_summary: Path
    gate_json_draft: Path
    gate_json_final: Path
    family_audit: Path
    material_audit_md: Path
    material_audit_json: Path
    excellence_md: Path
    excellence_json: Path
    timing_report: Path
    prd_claim_input: Path
    prd_claim_surface: Path
    prd_claim_control: Path


@dataclass(frozen=True)
class Phase1FullTrialResult:
    draft_gate_code: int
    final_gate_code: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a complete Phase-1 trial")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--profile", default="implementation-ready-prd")
    parser.add_argument(
        "--depth-mode",
        choices=("baseline", "creative"),
        default="baseline",
        help="Phase-1 v1.2 depth mode; creative requires explicit user intent and still must satisfy baseline first",
    )
    parser.add_argument(
        "--thinking-value-gain-mode",
        choices=("off", "full-use"),
        default="off",
        help="experimental Phase-1 Thinking Value-Gain strategy; full-use applies bounded value-gain to major P1 artifact units",
    )
    parser.add_argument(
        "--thinking-value-gain-output-profile",
        choices=THINKING_VALUE_GAIN_OUTPUT_PROFILES,
        default="coverage_rich",
        help="Mindthus TVG exit-side output profile when --thinking-value-gain-mode=full-use",
    )
    parser.add_argument("--owner", default="Codex Phase-1 full runner")
    parser.add_argument("--document-name", default="Phase-1 Product Requirements Document")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    parser.add_argument(
        "--skip-stage-02b",
        action="store_true",
        help="run the official Phase-1 trial with a rich Stage-02b skip-stub instead of full Stage-02b deepening",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="maximum convergence/remediation rounds to run",
    )
    parser.add_argument(
        "--no-auto-remediate",
        action="store_true",
        help="disable convergence-driver auto-remediation",
    )
    parser.add_argument(
        "--emit-legacy-zh-cn-mirror",
        action="store_true",
        help="emit deprecated deterministic zh-CN audit mirror for compatibility only",
    )
    parser.add_argument(
        "--commercial-argument-rewrite",
        help="optional agent/operator-authored commercial-argument-rewrite.json to apply during PRD assembly",
    )
    parser.add_argument(
        "--narrative-compression-rewrite",
        help="optional agent/operator-authored prd-narrative-compression-rewrite.json to apply during PRD convergence",
    )
    return parser


def parse_phase1_full_trial_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def build_phase1_full_trial_context(args: argparse.Namespace) -> Phase1FullTrialContext:
    script_dir = Path(__file__).resolve().parent
    repo_root = SCRIPTS_ROOT.parent
    python = sys.executable

    source = Path(args.source).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError(f"output directory is not empty: {output_dir}")
    diagnostics_dir = output_dir / ".phase1-diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = output_dir / ".phase1-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    version = normalize_version(args.version)
    output_locale = resolve_output_locale(args.output_locale)
    case_name = slugify(args.document_name)
    prd_stem = f"{case_name}-main-document"
    return Phase1FullTrialContext(
        script_dir=script_dir,
        repo_root=repo_root,
        python=python,
        source=source,
        output_dir=output_dir,
        version=version,
        profile=str(args.profile),
        depth_mode=str(args.depth_mode),
        thinking_value_gain_mode=str(args.thinking_value_gain_mode),
        thinking_value_gain_output_profile=str(args.thinking_value_gain_output_profile),
        owner=str(args.owner),
        document_name=str(args.document_name),
        output_locale=output_locale,
        canonical_output_locale="en",
        skip_stage_02b=bool(args.skip_stage_02b),
        max_rounds=max(1, int(args.max_rounds)),
        no_auto_remediate=bool(args.no_auto_remediate),
        emit_legacy_zh_cn_mirror=bool(getattr(args, "emit_legacy_zh_cn_mirror", False)),
        commercial_argument_rewrite=Path(args.commercial_argument_rewrite).resolve() if args.commercial_argument_rewrite else None,
        narrative_compression_rewrite=Path(args.narrative_compression_rewrite).resolve() if args.narrative_compression_rewrite else None,
        case_name=case_name,
        prd_stem=prd_stem,
        stage_01=output_dir / "stage-01-user-research.md",
        stage_02a=output_dir / "stage-02a-requirements-structural-analysis.md",
        stage_02b=output_dir / "stage-02b-requirements-specification-deepening.md",
        stage_03=output_dir / "stage-03-requirements-decomposition-and-mvp-slicing.md",
        stage_04=output_dir / "stage-04-requirements-validation-and-concept-proof.md",
        assembled_prd=evidence_dir / f"{prd_stem}-assembled.md",
        prd=output_dir / f"{prd_stem}.md",
        prd_zh=output_dir / f"{prd_stem}.zh-CN.md",
        evidence=output_dir / f"{prd_stem}-convergence-evidence.md",
        report=output_dir / "phase-1-execution-report.md",
        snapshot=resolve_cross_phase_surface_path(output_dir, "phase1", "phase1-runtime-snapshot.json"),
        depth_runtime_summary=output_dir / DEPTH_RUNTIME_SUMMARY_FILENAME,
        gate_json_draft=resolve_cross_phase_surface_path(output_dir, "phase1", "phase1-convergence-gates-draft.json"),
        gate_json_final=resolve_cross_phase_surface_path(output_dir, "phase1", "phase1-convergence-gates-final.json"),
        family_audit=resolve_cross_phase_surface_path(output_dir, "phase1", "phase1-skill-family-audit.txt"),
        material_audit_md=resolve_cross_phase_surface_path(output_dir, "phase1", "phase1-material-library-coverage-audit.md"),
        material_audit_json=resolve_cross_phase_surface_path(output_dir, "phase1", "phase1-material-library-coverage-audit.json"),
        excellence_md=output_dir / "phase1-prd-excellence-regression.md",
        excellence_json=output_dir / "phase1-prd-excellence-regression.json",
        timing_report=resolve_cross_phase_surface_path(output_dir, "phase1", "phase1-timing-report.json"),
        prd_claim_input=evidence_dir / f"{prd_stem}.claim-input.json",
        prd_claim_surface=evidence_dir / f"{prd_stem}.claim-surface.json",
        prd_claim_control=output_dir / f"{prd_stem}.claim-control.json",
    )


def print_phase1_full_trial_start(context: Phase1FullTrialContext) -> None:
    print("== Phase-1 Full Trial ==")
    print(f"source: {context.source}")
    print(f"output_dir: {context.output_dir}")
    print(f"version: {context.version}")
    print(f"profile: {context.profile}")
    print(f"depth_mode: {context.depth_mode}")
    print(f"thinking_value_gain_mode: {context.thinking_value_gain_mode}")
    print(f"thinking_value_gain_output_profile: {context.thinking_value_gain_output_profile}")
    print(f"skip_stage_02b: {'yes' if context.skip_stage_02b else 'no'}")


def build_record_phase1_runtime_snapshot_command(context: Phase1FullTrialContext) -> list[str]:
    return [
        context.python,
        str(context.script_dir / "record_phase1_runtime_snapshot.py"),
        "--repo-root",
        str(context.repo_root),
        "--output",
        str(context.snapshot),
    ]


def build_phase1_deep_stage_command(context: Phase1FullTrialContext) -> list[str]:
    command = [
        context.python,
        str(context.script_dir / "phase1_generate_deep_stage_outputs.py"),
        "--source",
        str(context.source),
        "--output-dir",
        str(context.output_dir),
        "--version",
        context.version,
        "--owner",
        context.owner,
        "--output-locale",
        context.canonical_output_locale,
        "--thinking-value-gain-mode",
        context.thinking_value_gain_mode,
        "--thinking-value-gain-output-profile",
        context.thinking_value_gain_output_profile,
    ]
    if context.skip_stage_02b:
        command.append("--skip-stage-02b")
    return command


def build_phase1_stage_artifact_depth_gate_command(context: Phase1FullTrialContext) -> list[str]:
    return [
        context.python,
        str(context.script_dir / "phase1_stage_artifact_depth_gate.py"),
        "--source",
        str(context.source),
        "--stage",
        str(context.stage_01),
        "--stage",
        str(context.stage_02a),
        "--stage",
        str(context.stage_02b),
        "--stage",
        str(context.stage_03),
        "--stage",
        str(context.stage_04),
    ]


def build_phase1_assemble_prd_command(context: Phase1FullTrialContext) -> list[str]:
    return [
        context.python,
        str(context.script_dir / "phase1_assemble_prd.py"),
        "--source",
        str(context.source),
        "--stage-01",
        str(context.stage_01),
        "--stage-02a",
        str(context.stage_02a),
        "--stage-02b",
        str(context.stage_02b),
        "--stage-03",
        str(context.stage_03),
        "--stage-04",
        str(context.stage_04),
        "--output",
        str(context.assembled_prd),
        "--report",
        str(context.report),
        "--version",
        context.version,
        "--profile",
        context.profile,
        "--document-name",
        context.document_name,
        "--output-locale",
        context.canonical_output_locale,
        "--claim-input-output",
        str(context.prd_claim_input),
    ]


def build_phase1_converge_prd_command(context: Phase1FullTrialContext) -> list[str]:
    command = [
        context.python,
        str(context.script_dir / "phase1_converge_prd.py"),
        "--assembled-prd",
        str(context.assembled_prd),
        "--output",
        str(context.prd),
        "--evidence-output",
        str(context.evidence),
        "--output-locale",
        context.canonical_output_locale,
    ]
    rewrite_path = context.output_dir / "prd-narrative-compression-rewrite.json"
    if context.narrative_compression_rewrite and rewrite_path.exists():
        command.extend(["--narrative-compression-rewrite", str(rewrite_path)])
    return command


def build_phase1_localize_prd_command(context: Phase1FullTrialContext) -> list[str]:
    return [
        context.python,
        str(context.script_dir / "phase1_localize_prd_zh.py"),
        "--canonical-prd",
        str(context.prd),
        "--output",
        str(context.prd_zh),
    ]


def build_phase1_emit_depth_runtime_artifacts_command(context: Phase1FullTrialContext) -> list[str]:
    return [
        context.python,
        str(context.script_dir / "phase1_emit_depth_runtime_artifacts.py"),
        "--source",
        str(context.source),
        "--stage-01",
        str(context.stage_01),
        "--stage-02a",
        str(context.stage_02a),
        "--stage-02b",
        str(context.stage_02b),
        "--stage-03",
        str(context.stage_03),
        "--stage-04",
        str(context.stage_04),
        "--prd",
        str(context.prd),
        "--output-dir",
        str(context.output_dir),
        "--version",
        context.version,
        "--owner",
        context.owner,
        "--depth-mode",
        context.depth_mode,
        "--thinking-value-gain-mode",
        context.thinking_value_gain_mode,
        "--thinking-value-gain-output-profile",
        context.thinking_value_gain_output_profile,
        "--output-locale",
        context.canonical_output_locale,
    ]


def build_phase1_gate_command(context: Phase1FullTrialContext, *, output_json_path: Path) -> list[str]:
    command = [
        context.python,
        str(context.script_dir / "run_phase1_convergence.py"),
        "--source",
        str(context.source),
        "--prd",
        str(context.prd),
        "--report",
        str(context.report),
        "--convergence-evidence",
        str(context.evidence),
        "--profile",
        context.profile,
        "--depth-mode",
        context.depth_mode,
        "--thinking-value-gain-mode",
        context.thinking_value_gain_mode,
        "--thinking-value-gain-output-profile",
        context.thinking_value_gain_output_profile,
        "--max-rounds",
        str(context.max_rounds),
        "--require-non-shrinking",
        "--output-json",
        str(output_json_path),
        "--output-locale",
        context.canonical_output_locale,
        "--stage",
        str(context.stage_01),
        "--stage",
        str(context.stage_02a),
        "--stage",
        str(context.stage_02b),
        "--stage",
        str(context.stage_03),
        "--stage",
        str(context.stage_04),
    ]
    if not context.no_auto_remediate:
        command.append("--auto-remediate")
    return command


def build_phase1_execution_report_command(context: Phase1FullTrialContext, *, gate_json_path: Path) -> list[str]:
    command = [
        context.python,
        str(context.script_dir / "phase1_emit_execution_report.py"),
        "--source",
        str(context.source),
        "--stage-01",
        str(context.stage_01),
        "--stage-02a",
        str(context.stage_02a),
        "--stage-02b",
        str(context.stage_02b),
        "--stage-03",
        str(context.stage_03),
        "--stage-04",
        str(context.stage_04),
        "--assembled-prd",
        str(context.assembled_prd),
        "--prd",
        str(context.prd),
        "--convergence-evidence",
        str(context.evidence),
        "--version",
        context.version,
        "--profile",
        context.profile,
        "--depth-mode",
        context.depth_mode,
        "--thinking-value-gain-mode",
        context.thinking_value_gain_mode,
        "--thinking-value-gain-output-profile",
        context.thinking_value_gain_output_profile,
        "--run-owner",
        context.owner,
        "--gate-json",
        str(gate_json_path),
        "--output",
        str(context.report),
        "--output-locale",
        context.output_locale,
    ]
    if context.emit_legacy_zh_cn_mirror:
        command.extend(["--prd-zh", str(context.prd_zh)])
    return command


def build_phase1_skill_family_audit_command(context: Phase1FullTrialContext) -> list[str]:
    command = [
        context.python,
        str(context.script_dir / "phase1_skill_family_audit.py"),
        "--repo-root",
        str(context.repo_root),
        "--prd",
        str(context.prd),
        "--convergence-evidence",
        str(context.evidence),
        "--stage-dir",
        str(context.output_dir),
    ]
    if context.emit_legacy_zh_cn_mirror:
        command.extend(["--prd-zh", str(context.prd_zh)])
    return command


def build_phase1_material_library_audit_command(context: Phase1FullTrialContext) -> list[str]:
    return [
        context.python,
        str(context.script_dir / "phase1_material_library_coverage_audit.py"),
        "--repo-root",
        str(context.repo_root),
        "--stage-dir",
        str(context.output_dir),
        "--output-md",
        str(context.material_audit_md),
        "--output-json",
        str(context.material_audit_json),
    ]


def build_phase1_prd_excellence_regression_command(context: Phase1FullTrialContext) -> list[str]:
    return [
        context.python,
        str(context.script_dir / "phase1_prd_excellence_regression.py"),
        "--prd",
        str(context.prd),
        "--output-md",
        str(context.excellence_md),
        "--output-json",
        str(context.excellence_json),
    ]


def phase1_main_stage_commands(context: Phase1FullTrialContext) -> list[list[str]]:
    if context.commercial_argument_rewrite and context.commercial_argument_rewrite.exists():
        shutil.copyfile(context.commercial_argument_rewrite, context.output_dir / "commercial-argument-rewrite.json")
    if context.narrative_compression_rewrite and context.narrative_compression_rewrite.exists():
        shutil.copyfile(
            context.narrative_compression_rewrite,
            context.output_dir / "prd-narrative-compression-rewrite.json",
        )
    commands = [
        build_record_phase1_runtime_snapshot_command(context),
        build_phase1_deep_stage_command(context),
        build_phase1_stage_artifact_depth_gate_command(context),
        build_phase1_assemble_prd_command(context),
        build_phase1_converge_prd_command(context),
        build_phase1_emit_depth_runtime_artifacts_command(context),
    ]
    if context.emit_legacy_zh_cn_mirror:
        commands.insert(-1, build_phase1_localize_prd_command(context))
    return commands


def write_phase1_draft_report(context: Phase1FullTrialContext) -> None:
    write_draft_report(
        output=context.report,
        source=context.source,
        version=context.version,
        profile=context.profile,
        run_owner=context.owner,
        stage_01=context.stage_01,
        stage_02a=context.stage_02a,
        stage_02b=context.stage_02b,
        stage_03=context.stage_03,
        stage_04=context.stage_04,
        assembled_prd=context.assembled_prd,
        prd=context.prd,
        prd_zh=context.prd_zh if context.emit_legacy_zh_cn_mirror else None,
        evidence=context.evidence,
        depth_mode=context.depth_mode,
        thinking_value_gain_mode=context.thinking_value_gain_mode,
        thinking_value_gain_output_profile=context.thinking_value_gain_output_profile,
        output_locale=context.output_locale,
        case_name=context.case_name,
    )


def run_phase1_gate_and_refresh_report(
    context: Phase1FullTrialContext,
    *,
    output_json_path: Path,
    segments: list[dict[str, Any]] | None = None,
    label_prefix: str = "",
) -> int:
    if segments is None:
        gate_code = run_allow_returncodes(
            build_phase1_gate_command(context, output_json_path=output_json_path),
            allowed=(0, 2),
        )
        run(build_phase1_execution_report_command(context, gate_json_path=output_json_path))
        return gate_code
    gate_code = run_allow_returncodes_timed(
        build_phase1_gate_command(context, output_json_path=output_json_path),
        allowed=(0, 2),
        segments=segments,
        name=f"{label_prefix}gate".strip("_"),
    )
    run_timed(
        build_phase1_execution_report_command(context, gate_json_path=output_json_path),
        segments=segments,
        name=f"{label_prefix}execution_report".strip("_"),
    )
    return gate_code


def run_captured_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, env=canonical_driver_env())


def run_phase1_skill_family_audit(context: Phase1FullTrialContext, *, segments: list[dict[str, Any]] | None = None) -> None:
    audit_proc = (
        run_captured_command_timed(
            build_phase1_skill_family_audit_command(context),
            segments=segments,
            name="skill_family_audit",
        )
        if segments is not None
        else run_captured_command(build_phase1_skill_family_audit_command(context))
    )
    context.family_audit.write_text((audit_proc.stdout or "") + (audit_proc.stderr or ""), encoding="utf-8")
    if audit_proc.returncode != 0:
        print(audit_proc.stdout)
        print(audit_proc.stderr)
        raise SystemExit(audit_proc.returncode)


def run_phase1_material_library_audit(context: Phase1FullTrialContext, *, segments: list[dict[str, Any]] | None = None) -> None:
    material_proc = (
        run_captured_command_timed(
            build_phase1_material_library_audit_command(context),
            segments=segments,
            name="material_library_audit",
        )
        if segments is not None
        else run_captured_command(build_phase1_material_library_audit_command(context))
    )
    if material_proc.stdout:
        print(material_proc.stdout)
    if material_proc.stderr:
        print(material_proc.stderr)
    if material_proc.returncode != 0:
        raise SystemExit(material_proc.returncode)


def run_phase1_postrun_audits(context: Phase1FullTrialContext, *, segments: list[dict[str, Any]] | None = None) -> None:
    run_phase1_skill_family_audit(context, segments=segments)
    run_phase1_material_library_audit(context, segments=segments)
    if segments is None:
        run(build_phase1_prd_excellence_regression_command(context))
    else:
        run_timed(
            build_phase1_prd_excellence_regression_command(context),
            segments=segments,
            name="prd_excellence_regression",
        )


def _phase1_claim_source_candidates(context: Phase1FullTrialContext) -> list[Path]:
    return [
        context.stage_02b,
        context.stage_03,
        context.stage_04,
        context.stage_02a,
        context.stage_01,
        context.source,
    ]


def _read_existing_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _unique_claim_records(claims: list[ClaimRecord]) -> list[ClaimRecord]:
    indexed: dict[str, ClaimRecord] = {}
    for claim in claims:
        claim_id = str(claim.id).strip()
        if claim_id and claim_id not in indexed:
            indexed[claim_id] = claim
    return [indexed[key] for key in sorted(indexed)]


def _phase1_claim_input_payload(context: Phase1FullTrialContext) -> dict[str, Any]:
    if not context.prd_claim_input.exists():
        return {}
    try:
        payload = json.loads(context.prd_claim_input.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _trace_units_from_claim_input(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    trace_units = payload.get("trace_units")
    if not isinstance(trace_units, dict):
        return {}
    normalized: dict[str, list[dict[str, Any]]] = {}
    for group in PHASE1_TRACE_UNIT_GROUP_ORDER:
        rows = trace_units.get(group, [])
        if not isinstance(rows, list):
            continue
        normalized[group] = [row for row in rows if isinstance(row, dict)]
    return normalized


def _claim_records_from_claim_input(
    context: Phase1FullTrialContext,
) -> tuple[list[ClaimRecord], list[dict[str, Any]], set[str]]:
    payload = _phase1_claim_input_payload(context)
    trace_units = _trace_units_from_claim_input(payload)
    if not trace_units:
        return [], [], set()
    claims: list[ClaimRecord] = []
    source_rows: list[dict[str, Any]] = []
    compiled_groups: set[str] = set()
    for group in PHASE1_TRACE_UNIT_GROUP_ORDER:
        rows = trace_units.get(group, [])
        if not rows:
            continue
        claims.extend(
            accepted_claims_from_phase1_trace_units(
                {group: rows},
                source_label=context.prd_claim_input.name,
            )
        )
        compiled_groups.add(group)
        source_rows.append(
            {
                "claim_group": group,
                "source_path": str(context.prd_claim_input),
                "source_name": context.prd_claim_input.name,
                "claim_count": len(rows),
                "source_mode": "phase1-prd-assembly-claim-input",
            }
        )
    return _unique_claim_records(claims), source_rows, compiled_groups


def _claim_records_from_source_contexts(
    context: Phase1FullTrialContext,
    *,
    prd_text: str,
) -> tuple[list[ClaimRecord], list[dict[str, Any]], list[dict[str, Any]]]:
    claims, source_rows, compiled_groups = _claim_records_from_claim_input(context)
    candidates = _phase1_claim_source_candidates(context)
    for group in PHASE1_TRACE_UNIT_GROUP_ORDER:
        if group in compiled_groups:
            continue
        for path in candidates:
            text = _read_existing_text(path)
            if not text:
                continue
            rows = extract_phase1_trace_units(text).get(group, [])
            if not rows:
                continue
            claims.extend(
                accepted_claims_from_phase1_trace_units(
                    {group: rows},
                    source_label=path.name,
                )
            )
            compiled_groups.add(group)
            source_rows.append(
                {
                    "claim_group": group,
                    "source_path": str(path),
                    "source_name": path.name,
                    "claim_count": len(rows),
                    "source_mode": "phase1-source-context",
                }
            )
            break
    compatibility_rows: list[dict[str, Any]] = []
    prd_trace_units = extract_phase1_trace_units(prd_text)
    for group in PHASE1_TRACE_UNIT_GROUP_ORDER:
        if group in compiled_groups:
            continue
        rows = prd_trace_units.get(group, [])
        if not rows:
            continue
        claims.extend(
            accepted_claims_from_phase1_trace_units(
                {group: rows},
                source_label=context.prd.name,
            )
        )
        compatibility_rows.append(
            {
                "claim_group": group,
                "source_path": str(context.prd),
                "source_name": context.prd.name,
                "claim_count": len(rows),
                "source_mode": "compatibility-rendered-prd",
            }
        )
    return _unique_claim_records(claims), source_rows, compatibility_rows


def _flow_claims_from_source_contexts(
    context: Phase1FullTrialContext,
    *,
    prd_text: str,
) -> tuple[list[ClaimRecord], list[dict[str, Any]], list[dict[str, Any]]]:
    payload = _phase1_claim_input_payload(context)
    flow_text = str(payload.get("flow_text") or "").strip() if payload else ""
    if flow_text:
        claims = _phase1_flow_claims(
            f"### Operational Flow Specification\n{flow_text}",
            source_label=context.prd_claim_input.name,
        )
        if claims:
            return (
                claims,
                [
                    {
                        "claim_group": "workflow_flow_claims",
                        "source_path": str(context.prd_claim_input),
                        "source_name": context.prd_claim_input.name,
                        "claim_count": len(claims),
                        "source_mode": "phase1-prd-assembly-claim-input",
                    }
                ],
                [],
            )
    source_rows: list[dict[str, Any]] = []
    for path in _phase1_claim_source_candidates(context):
        text = _read_existing_text(path)
        if not text:
            continue
        claims = _phase1_flow_claims(text, source_label=path.name)
        if claims:
            source_rows.append(
                {
                    "claim_group": "workflow_flow_claims",
                    "source_path": str(path),
                    "source_name": path.name,
                    "claim_count": len(claims),
                    "source_mode": "phase1-source-context",
                }
            )
            return claims, source_rows, []
    claims = _phase1_flow_claims(prd_text, source_label=context.prd.name)
    if not claims:
        return [], [], []
    return (
        claims,
        [],
        [
            {
                "claim_group": "workflow_flow_claims",
                "source_path": str(context.prd),
                "source_name": context.prd.name,
                "claim_count": len(claims),
                "source_mode": "compatibility-rendered-prd",
            }
        ],
    )


def _phase1_prd_claim_surface_payload(context: Phase1FullTrialContext, *, prd_text: str) -> dict[str, Any]:
    trace_claims, trace_source_rows, trace_compatibility_rows = _claim_records_from_source_contexts(
        context,
        prd_text=prd_text,
    )
    flow_claims, flow_source_rows, compatibility_rows = _flow_claims_from_source_contexts(context, prd_text=prd_text)
    claims = _unique_claim_records([*trace_claims, *flow_claims])
    relations = _phase1_flow_transition_relations(flow_claims)
    names = _phase1_flow_canonical_names(flow_claims)
    source_rows = [*trace_source_rows, *flow_source_rows]
    compatibility_rows = [*trace_compatibility_rows, *compatibility_rows]
    compilation_status = "compiled-with-compatibility-fallback" if compatibility_rows else "compiled"
    if not claims:
        compilation_status = "empty"
    return {
        "artifact_kind": "phase1-prd-claim-surface",
        "version": "phase1-prd-claim-surface/v0.1",
        "artifact_id": "p1-prd-main",
        "authority_mode": "phase1-compiled-claim-surface",
        "compilation_status": compilation_status,
        "claim_surface_path": str(context.prd_claim_surface),
        "source_context_paths": sorted({row["source_path"] for row in source_rows}),
        "compatibility_source_paths": sorted({row["source_path"] for row in compatibility_rows}),
        "source_rows": source_rows,
        "compatibility_rows": compatibility_rows,
        "claims": [claim.to_dict() for claim in claims],
        "relations": [relation.to_dict() for relation in relations],
        "names": [name.to_dict() for name in names],
    }


def build_phase1_prd_claim_surface(context: Phase1FullTrialContext, *, prd_text: str) -> dict[str, Any]:
    payload = _phase1_prd_claim_surface_payload(context, prd_text=prd_text)
    context.prd_claim_surface.parent.mkdir(parents=True, exist_ok=True)
    context.prd_claim_surface.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _claims_from_claim_surface(surface: dict[str, Any]) -> list[ClaimRecord]:
    claims: list[ClaimRecord] = []
    for row in surface.get("claims", []):
        if not isinstance(row, dict):
            continue
        claim_id = str(row.get("id") or "").strip()
        if not claim_id:
            continue
        claims.append(
            ClaimRecord(
                id=claim_id,
                kind=str(row.get("kind") or "claim").strip() or "claim",
                text=str(row.get("text") or claim_id).strip() or claim_id,
                source_refs=[str(item).strip() for item in row.get("source_refs", []) if str(item).strip()],
                status=str(row.get("status") or "accepted").strip() or "accepted",
            )
        )
    return claims


def _relations_from_claim_surface(surface: dict[str, Any]) -> list[ClaimRelation]:
    relations: list[ClaimRelation] = []
    for row in surface.get("relations", []):
        if not isinstance(row, dict):
            continue
        subject = str(row.get("subject") or "").strip()
        predicate = str(row.get("predicate") or "").strip()
        object_id = str(row.get("object") or "").strip()
        if not subject or not predicate or not object_id:
            continue
        relations.append(
            ClaimRelation(
                subject=subject,
                predicate=predicate,
                object=object_id,
                source_claim_refs=[str(item).strip() for item in row.get("source_claim_refs", []) if str(item).strip()],
            )
        )
    return relations


def _names_from_claim_surface(surface: dict[str, Any]) -> list[CanonicalName]:
    names: list[CanonicalName] = []
    for row in surface.get("names", []):
        if not isinstance(row, dict):
            continue
        claim_id = str(row.get("id") or "").strip()
        canonical = str(row.get("canonical") or "").strip()
        if not claim_id or not canonical:
            continue
        names.append(
            CanonicalName(
                id=claim_id,
                canonical=canonical,
                allowed_aliases=[str(item).strip() for item in row.get("allowed_aliases", []) if str(item).strip()],
                forbidden_aliases=[str(item).strip() for item in row.get("forbidden_aliases", []) if str(item).strip()],
            )
        )
    return names


def emit_phase1_claim_control_sidecar(context: Phase1FullTrialContext) -> dict[str, Any]:
    """Emit the Path B claim-control sidecar for the generated PRD."""

    prd_text = context.prd.read_text(encoding="utf-8")
    claim_surface = build_phase1_prd_claim_surface(context, prd_text=prd_text)
    claims = _claims_from_claim_surface(claim_surface)
    flow_relations = _relations_from_claim_surface(claim_surface)
    flow_names = _names_from_claim_surface(claim_surface)
    return emit_path_b_claim_control_sidecar(
        artifact_path=context.prd,
        artifact_id="p1-prd-main",
        claims=claims,
        view_id="p1-prd:main-document",
        source_count=2,
        upstream_surface_paths=[context.source, context.prd_claim_surface],
        sidecar_path=context.prd_claim_control,
        relations=flow_relations,
        canonical_names=flow_names,
        claim_authority={
            "authority_mode": claim_surface["authority_mode"],
            "compilation_status": claim_surface["compilation_status"],
            "claim_surface_path": str(context.prd_claim_surface),
            "source_context_paths": claim_surface["source_context_paths"],
            "compatibility_source_paths": claim_surface["compatibility_source_paths"],
            "policy": "P1 sidecar consumes the compiled claim surface first; rendered PRD is a validation target, not the claim source.",
        },
    )


def _phase1_flow_claims(prd_text: str, *, source_label: str) -> list[ClaimRecord]:
    flow_block = _heading_section(
        prd_text,
        ("Operational Flow Specification", "操作流程规格"),
    )
    claims: list[ClaimRecord] = []
    seen: set[str] = set()
    for line in flow_block.splitlines():
        match = re.search(r"\b(FLOW-\d+)\b\s*[:|-]?\s*(.+?)\s*$", line.strip())
        if not match:
            continue
        claim_id = match.group(1).strip()
        if claim_id in seen:
            continue
        seen.add(claim_id)
        text = match.group(2).strip(" .") or claim_id
        claims.append(
            ClaimRecord(
                id=claim_id,
                kind="workflow_step",
                text=text,
                source_refs=[f"{source_label}#operational-flow-specification"],
            )
        )
    return claims


def _phase1_flow_transition_relations(flow_claims: list[ClaimRecord]) -> list[ClaimRelation]:
    return [
        ClaimRelation(subject=left.id, predicate="transitions_to", object=right.id)
        for left, right in zip(flow_claims, flow_claims[1:])
    ]


def _phase1_flow_canonical_names(flow_claims: list[ClaimRecord]) -> list[CanonicalName]:
    return [
        CanonicalName(
            id=claim.id,
            canonical=str(claim.text or claim.id).strip(" .") or claim.id,
        )
        for claim in flow_claims
    ]


def _heading_section(text: str, titles: tuple[str, ...]) -> str:
    title_pattern = "|".join(re.escape(title) for title in titles)
    match = re.search(rf"(?ims)^###\s*(?:{title_pattern}).*?\n(?P<body>.*?)(?=^###\s+|\Z)", text)
    return match.group("body") if match else ""


def load_phase1_gate_payload(context: Phase1FullTrialContext) -> dict[str, Any] | None:
    if not context.gate_json_final.exists():
        return None
    return json.loads(context.gate_json_final.read_text(encoding="utf-8"))


def emit_phase1_gate_summary(gate_payload: dict[str, Any] | None) -> None:
    if not gate_payload:
        return
    phase_verdict = gate_payload.get("phase_verdict")
    phase_total_score = gate_payload.get("phase_total_score")
    phase_scorecard = gate_payload.get("phase_mainline_scorecard_path")
    phase_acceptance = gate_payload.get("phase_acceptance_matrix_path")
    phase_verdict_path = gate_payload.get("phase_verdict_path")
    if phase_scorecard:
        print(f"phase_mainline_scorecard: {phase_scorecard}")
    if phase_acceptance:
        print(f"phase_acceptance_matrix: {phase_acceptance}")
    if phase_verdict_path:
        print(f"phase_verdict_json: {phase_verdict_path}")
    if phase_total_score is not None:
        print(f"phase_total_score: {phase_total_score} / 100")
    if phase_verdict:
        print(f"phase_verdict: {phase_verdict}")


def run_phase1_full_trial(context: Phase1FullTrialContext) -> Phase1FullTrialResult:
    timing_started_at = utc_now_iso()
    timing_started_monotonic = time.monotonic()
    timing_segments: list[dict[str, Any]] = []
    try:
        for command in phase1_main_stage_commands(context):
            run_timed(command, segments=timing_segments, name=command_segment_name(command, "phase1_step"))

        started_at = utc_now_iso()
        started_monotonic = time.monotonic()
        write_phase1_draft_report(context)
        append_timing_segment(
            timing_segments,
            name="draft_report",
            started_at=started_at,
            started_monotonic=started_monotonic,
            status="pass",
        )
        draft_gate_code = run_phase1_gate_and_refresh_report(
            context,
            output_json_path=context.gate_json_draft,
            segments=timing_segments,
            label_prefix="draft_",
        )
        final_gate_code = run_phase1_gate_and_refresh_report(
            context,
            output_json_path=context.gate_json_final,
            segments=timing_segments,
            label_prefix="final_",
        )
        run_phase1_postrun_audits(context, segments=timing_segments)
        started_at = utc_now_iso()
        started_monotonic = time.monotonic()
        emit_phase1_claim_control_sidecar(context)
        append_timing_segment(
            timing_segments,
            name="claim_control_sidecar",
            started_at=started_at,
            started_monotonic=started_monotonic,
            status="pass",
        )
        started_at = utc_now_iso()
        started_monotonic = time.monotonic()
        emit_human_review_surface(context.output_dir, "phase1")
        append_timing_segment(
            timing_segments,
            name="human_review_surface",
            started_at=started_at,
            started_monotonic=started_monotonic,
            status="pass",
        )
        return Phase1FullTrialResult(
            draft_gate_code=draft_gate_code,
            final_gate_code=final_gate_code,
        )
    finally:
        write_phase1_timing_report(
            context,
            started_at=timing_started_at,
            started_monotonic=timing_started_monotonic,
            segments=timing_segments,
        )


def emit_phase1_full_trial_summary(context: Phase1FullTrialContext, result: Phase1FullTrialResult) -> int:
    print(f"final_prd: {context.prd}")
    if context.emit_legacy_zh_cn_mirror:
        print(f"legacy_prd_zh: {context.prd_zh}")
    else:
        print("localized_reader_evidence: not-requested")
        print("legacy_prd_zh: deprecated / not generated")
    print(f"convergence_evidence: {context.evidence}")
    for artifact_name in DEPTH_RUNTIME_TEXT_ARTIFACTS:
        print(f"depth_runtime_artifact: {context.output_dir / artifact_name}")
    print(f"depth_runtime_summary: {context.depth_runtime_summary}")
    print(f"execution_report: {context.report}")
    print(f"human_review_index: {context.output_dir / 'human-review' / 'INDEX.md'}")
    print(f"convergence_json: {context.gate_json_final}")
    emit_phase1_gate_summary(load_phase1_gate_payload(context))
    print(f"skill_family_audit: {context.family_audit}")
    print(f"material_library_audit: {context.material_audit_md}")
    print(f"prd_excellence_regression: {context.excellence_md}")
    print(f"prd_claim_control: {context.prd_claim_control}")
    print(f"timing_report: {context.timing_report}")
    if result.draft_gate_code != 0 or result.final_gate_code != 0:
        print("FINAL: BLOCKED")
        return result.final_gate_code or result.draft_gate_code
    print("FINAL: PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_phase1_full_trial_args(argv)
    try:
        context = build_phase1_full_trial_context(args)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}")
        return 2

    print_phase1_full_trial_start(context)
    result = run_phase1_full_trial(context)
    return emit_phase1_full_trial_summary(context, result)


if __name__ == "__main__":
    raise SystemExit(main())
