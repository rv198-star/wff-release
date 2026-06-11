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
from phase1.phase1_emit_depth_runtime_artifacts import DEPTH_RUNTIME_SUMMARY_FILENAME, DEPTH_RUNTIME_TEXT_ARTIFACTS
from phase1.phase1_runtime_metadata import build_runtime_metadata_lines
from phase1.phase1_version_contract import normalize_version_identifier


def run(command: list[str]) -> None:
    proc = subprocess.run(command, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def run_allow_returncodes(command: list[str], allowed: tuple[int, ...]) -> int:
    proc = subprocess.run(command, text=True)
    if proc.returncode not in allowed:
        raise SystemExit(proc.returncode)
    return proc.returncode


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    proc = subprocess.run(command, text=True)
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
    proc = subprocess.run(command, text=True)
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
    proc = subprocess.run(command, capture_output=True, text=True)
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
    output_locale: str | None = None,
    case_name: str = "phase-1-case",
) -> None:
    metadata_lines = "\n".join(build_runtime_metadata_lines(depth_mode, thinking_value_gain_mode=thinking_value_gain_mode))
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
        owner=str(args.owner),
        document_name=str(args.document_name),
        output_locale=output_locale,
        canonical_output_locale="en",
        skip_stage_02b=bool(args.skip_stage_02b),
        max_rounds=max(1, int(args.max_rounds)),
        no_auto_remediate=bool(args.no_auto_remediate),
        emit_legacy_zh_cn_mirror=bool(args.emit_legacy_zh_cn_mirror),
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
    )


def print_phase1_full_trial_start(context: Phase1FullTrialContext) -> None:
    print("== Phase-1 Full Trial ==")
    print(f"source: {context.source}")
    print(f"output_dir: {context.output_dir}")
    print(f"version: {context.version}")
    print(f"profile: {context.profile}")
    print(f"depth_mode: {context.depth_mode}")
    print(f"thinking_value_gain_mode: {context.thinking_value_gain_mode}")
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
    return subprocess.run(command, capture_output=True, text=True)


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
    print(f"convergence_json: {context.gate_json_final}")
    emit_phase1_gate_summary(load_phase1_gate_payload(context))
    print(f"skill_family_audit: {context.family_audit}")
    print(f"material_library_audit: {context.material_audit_md}")
    print(f"prd_excellence_regression: {context.excellence_md}")
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
