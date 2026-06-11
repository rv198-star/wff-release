#!/usr/bin/env python3
"""
Validate and summarize one completed P1 -> P4 mainline run.

This wrapper is intentionally a closure collector, not a generation pipeline.
It expects each phase root to already exist and emits one repo-level report.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.output_language import localize_p1_p4_mainline_closure_summary
from phase4.phase4_common import load_phase3_mainline_summary


@dataclass(frozen=True)
class P1P4MainlineClosureContext:
    phase1_root: Path
    phase2_root: Path
    phase3_root: Path
    phase4_root: Path
    output_dir: Path
    case_name: str
    version: str
    closure_mode: str
    report_path: Path
    summary_path: Path


def read_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def first_existing(root: Path, *relative_paths: str) -> Path | None:
    for relative in relative_paths:
        candidate = root / relative
        if candidate.exists():
            return candidate
    return None


def detect_phase1_prd(root: Path) -> Path | None:
    candidates = sorted(
        path
        for path in root.glob("*main-document.md")
        if "assembled" not in path.name and ".zh-CN." not in path.name
    )
    return candidates[0] if candidates else None


def detect_phase1_convergence_evidence(root: Path, prd: Path | None) -> Path | None:
    if prd is not None:
        candidate = prd.with_name(f"{prd.stem}-convergence-evidence.md")
        if candidate.exists():
            return candidate
    legacy = root / "geo-rpd-main-document-convergence-evidence.md"
    if legacy.exists():
        return legacy
    candidates = sorted(root.glob("*main-document-convergence-evidence.md"))
    return candidates[0] if candidates else None


def load_phase_mainline_assessment(
    root: Path,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata if isinstance(metadata, dict) else {}
    verdict = load_json(first_existing(root, "phase-verdict.json"))
    metadata_summary = metadata.get("mainline_assessment_summary")
    metadata_artifacts = metadata.get("mainline_assessment_artifacts")

    if not isinstance(metadata_summary, dict):
        metadata_summary = {}
    if not isinstance(metadata_artifacts, dict):
        metadata_artifacts = {}

    if isinstance(verdict, dict) and verdict:
        return {
            "present": True,
            "source": "phase-verdict.json",
            "phase_verdict": str(verdict.get("verdict") or "").strip(),
            "phase_total_score": verdict.get("total_score"),
            "review_bound_items_count": int(verdict.get("review_bound_items_count", 0) or 0),
            "blockers_count": int(verdict.get("blockers_count", 0) or 0),
            "phase_verdict_path": str(root / "phase-verdict.json"),
            "phase_scorecard_path": str(root / "phase-mainline-scorecard.md")
            if (root / "phase-mainline-scorecard.md").exists()
            else "",
            "phase_acceptance_matrix_path": str(root / "phase-acceptance-matrix.md")
            if (root / "phase-acceptance-matrix.md").exists()
            else "",
        }

    if metadata_summary:
        return {
            "present": True,
            "source": "metadata.mainline_assessment_summary",
            "phase_verdict": str(metadata_summary.get("phase_verdict") or "").strip(),
            "phase_total_score": metadata_summary.get("phase_total_score"),
            "review_bound_items_count": int(metadata_summary.get("review_bound_items_count", 0) or 0),
            "blockers_count": int(metadata_summary.get("blockers_count", 0) or 0),
            "phase_verdict_path": str(
                metadata_summary.get("phase_verdict_path") or metadata_artifacts.get("verdict_path") or ""
            ).strip(),
            "phase_scorecard_path": str(
                metadata_summary.get("phase_scorecard_path") or metadata_artifacts.get("scorecard_path") or ""
            ).strip(),
            "phase_acceptance_matrix_path": str(
                metadata_summary.get("phase_acceptance_matrix_path")
                or metadata_artifacts.get("acceptance_matrix_path")
                or ""
            ).strip(),
        }

    metadata_phase_verdict = str(metadata.get("phase_verdict") or "").strip()
    if metadata_phase_verdict:
        return {
            "present": True,
            "source": "metadata.phase_verdict",
            "phase_verdict": metadata_phase_verdict,
            "phase_total_score": metadata.get("phase_total_score"),
            "review_bound_items_count": int(metadata.get("phase_review_bound_items_count", 0) or 0),
            "blockers_count": int(metadata.get("phase_blockers_count", 0) or 0),
            "phase_verdict_path": str(metadata.get("phase_verdict_path") or "").strip(),
            "phase_scorecard_path": str(metadata.get("phase_scorecard_path") or "").strip(),
            "phase_acceptance_matrix_path": str(metadata.get("phase_acceptance_matrix_path") or "").strip(),
        }

    return {
        "present": False,
        "source": "",
        "phase_verdict": "",
        "phase_total_score": None,
        "review_bound_items_count": 0,
        "blockers_count": 0,
        "phase_verdict_path": "",
        "phase_scorecard_path": "",
        "phase_acceptance_matrix_path": "",
    }


def phase3_surface_contract_summary(gate: dict[str, Any]) -> dict[str, Any]:
    checks = gate.get("checks", {}) if isinstance(gate, dict) else {}
    surface_contract_checks = checks.get("surface_contract_checks", {})
    role_surface_alignment = checks.get("role_surface_alignment", {})
    present = any(
        key in checks
        for key in (
            "surface_contract_gate",
            "surface_contract_checks",
            "core_interaction_guess_count",
            "operable_cross_page_flow_count",
            "core_surface_pass_count",
            "role_surface_alignment",
        )
    )
    return {
        "present": present,
        "gate": bool(checks.get("surface_contract_gate")) if present else False,
        "source": str(checks.get("surface_contract_gate_source") or "").strip(),
        "checks": surface_contract_checks if isinstance(surface_contract_checks, dict) else {},
        "core_interaction_guess_count": int(checks.get("core_interaction_guess_count", 0) or 0),
        "operable_cross_page_flow_count": int(checks.get("operable_cross_page_flow_count", 0) or 0),
        "core_surface_pass_count": int(checks.get("core_surface_pass_count", 0) or 0),
        "core_surface_count": int(checks.get("core_surface_count", 0) or 0),
        "role_surface_alignment": role_surface_alignment if isinstance(role_surface_alignment, dict) else {},
    }


def nested_bullet_value(text: str, *keys: str) -> str:
    for key in keys:
        pattern = rf"^- {re.escape(key)}:\s*$\n(?:  - `?([^\n`]+)`?\s*$)"
        match = re.search(pattern, text, flags=re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def resolve_retained_proof_mode(gate: dict[str, Any], closure_mode: str) -> bool:
    if closure_mode == "retained-proof":
        return True
    checks = gate.get("checks", {}) if isinstance(gate, dict) else {}
    return bool(checks.get("retained_proof_mode"))


def phase1_summary(root: Path) -> dict[str, Any]:
    report = first_existing(root, "phase-1-execution-report.md")
    prd = detect_phase1_prd(root)
    evidence = detect_phase1_convergence_evidence(root, prd)
    report_text = read_text(report)
    mainline_assessment = load_phase_mainline_assessment(root)
    return {
        "root": str(root),
        "status": nested_bullet_value(report_text, "current_overall_status", "当前总体状态") or "unknown",
        "artifacts": {
            "execution_report": str(report) if report else "",
            "prd_main_document": str(prd) if prd else "",
            "convergence_evidence": str(evidence) if evidence else "",
            "phase_verdict": str(mainline_assessment.get("phase_verdict_path") or ""),
            "phase_mainline_scorecard": str(mainline_assessment.get("phase_scorecard_path") or ""),
            "phase_acceptance_matrix": str(mainline_assessment.get("phase_acceptance_matrix_path") or ""),
        },
        "checks": {
            "execution_report_present": bool(report),
            "prd_main_document_present": bool(prd),
            "convergence_evidence_present": bool(evidence),
            "phase_verdict_present": bool(mainline_assessment.get("present")),
        },
        "required_artifact_checks": {
            "execution_report_present": bool(report),
            "prd_main_document_present": bool(prd),
            "convergence_evidence_present": bool(evidence),
        },
        "mainline_assessment": mainline_assessment,
    }


def phase2_summary(root: Path, phase1_prd: Path | None) -> dict[str, Any]:
    report = first_existing(root, "phase-2-execution-report.md")
    esp = first_existing(root, "engineering-spec-pack.md")
    entry = first_existing(root, "phase-3-implementation-entry.md")
    report_text = read_text(report)
    phase1_name = phase1_prd.name if phase1_prd else ""
    mainline_assessment = load_phase_mainline_assessment(root)
    return {
        "root": str(root),
        "status": nested_bullet_value(report_text, "current_overall_status", "当前总体状态") or "unknown",
        "artifacts": {
            "execution_report": str(report) if report else "",
            "engineering_spec_pack": str(esp) if esp else "",
            "phase3_implementation_entry": str(entry) if entry else "",
            "phase_verdict": str(mainline_assessment.get("phase_verdict_path") or ""),
            "phase_mainline_scorecard": str(mainline_assessment.get("phase_scorecard_path") or ""),
            "phase_acceptance_matrix": str(mainline_assessment.get("phase_acceptance_matrix_path") or ""),
        },
        "checks": {
            "execution_report_present": bool(report),
            "engineering_spec_pack_present": bool(esp),
            "phase3_implementation_entry_present": bool(entry),
            "phase1_prd_reference_visible": bool(phase1_name and phase1_name in report_text),
            "phase_verdict_present": bool(mainline_assessment.get("present")),
        },
        "required_artifact_checks": {
            "execution_report_present": bool(report),
            "engineering_spec_pack_present": bool(esp),
            "phase3_implementation_entry_present": bool(entry),
        },
        "mainline_assessment": mainline_assessment,
    }


def phase3_summary(root: Path, phase2_root: Path, *, closure_mode: str = "runtime-closure") -> dict[str, Any]:
    metadata = load_json(first_existing(root, "phase3-run-metadata.json"))
    gate = load_json(first_existing(root, "phase3-delivery-gate.json"))
    retained_proof_mode = resolve_retained_proof_mode(gate, closure_mode)
    runtime_delivery_artifacts_required = not retained_proof_mode
    mainline_summary = load_phase3_mainline_summary(root)
    surface_contract = phase3_surface_contract_summary(gate)
    execution_report = first_existing(root, "phase-3-execution-report.md")
    acceptance_report = first_existing(root, "phase-3-acceptance-report.md")
    openapi = first_existing(root, "openapi-final.yaml", "contracts/openapi.yaml")
    dockerfile = first_existing(root, "Dockerfile")
    runbook = first_existing(root, "deploy-runbook.md")
    metadata_phase2_root = str(metadata.get("phase2_root", "")).strip()
    phase2_root_matches = metadata_phase2_root == str(phase2_root.resolve())
    warnings = gate.get("warnings", [])
    phase_verdict = str(mainline_summary.get("phase_verdict") or metadata.get("phase_verdict") or "").strip()
    phase_total_score = mainline_summary.get("phase_total_score", metadata.get("phase_total_score"))
    blockers_count = int(mainline_summary.get("blockers_count", metadata.get("phase_blockers_count", 0)) or 0)
    review_bound_items_count = int(
        mainline_summary.get("review_bound_items_count", metadata.get("phase_review_bound_items_count", 0)) or 0
    )
    return {
        "root": str(root),
        "status": str(
            mainline_summary.get("recommended_formal_state") or gate.get("recommended_formal_state") or "unknown"
        ),
        "closure_mode": "retained-proof" if retained_proof_mode else "runtime-closure",
        "artifacts": {
            "delivery_gate": str(root / "phase3-delivery-gate.json"),
            "phase_verdict": str(mainline_summary.get("phase_verdict_path") or ""),
            "execution_report": str(execution_report) if execution_report else "",
            "acceptance_report": str(acceptance_report) if acceptance_report else "",
            "openapi": str(openapi) if openapi else "",
            "dockerfile": str(dockerfile) if dockerfile else "",
            "deploy_runbook": str(runbook) if runbook else "",
        },
        "checks": {
            "delivery_gate_present": bool(gate),
            "phase_verdict_present": bool(mainline_summary.get("present")) and bool(phase_verdict),
            "execution_report_present": bool(execution_report),
            "acceptance_report_present": bool(acceptance_report),
            "openapi_present": bool(openapi),
            "dockerfile_present": bool(dockerfile),
            "deploy_runbook_present": bool(runbook),
            "runtime_delivery_artifacts_required": runtime_delivery_artifacts_required,
            "retained_proof_mode": retained_proof_mode,
            "phase2_root_matches": phase2_root_matches,
            "phase2_root_linkage_satisfied": phase2_root_matches or retained_proof_mode,
            "frontend_contract_required": bool(gate.get("checks", {}).get("frontend_contract_required", False)),
            "surface_contract_evidence_present": surface_contract["present"],
            "surface_contract_gate": surface_contract["gate"] if surface_contract["present"] else False,
            "core_interaction_guess_gate": surface_contract["core_interaction_guess_count"] == 0,
            "operable_cross_page_flow_gate": (
                not bool(surface_contract["checks"].get("operable_cross_page_flow_required"))
                or surface_contract["operable_cross_page_flow_count"] > 0
            )
            if surface_contract["present"]
            else False,
            "core_surface_pass_gate": (
                surface_contract["core_surface_count"] > 0
                and surface_contract["core_surface_pass_count"] == surface_contract["core_surface_count"]
            )
            if surface_contract["present"]
            else False,
            "role_surface_alignment_gate": bool(surface_contract["role_surface_alignment"].get("all_core_surfaces_aligned"))
            if surface_contract["present"]
            else False,
        },
        "required_artifact_checks": {
            "delivery_gate_present": bool(gate),
            "phase_verdict_present": bool(mainline_summary.get("present")) and bool(phase_verdict),
            "execution_report_present": bool(execution_report),
            "acceptance_report_present": bool(acceptance_report),
            "openapi_present": bool(openapi),
            "dockerfile_present": bool(dockerfile) if runtime_delivery_artifacts_required else True,
            "deploy_runbook_present": bool(runbook) if runtime_delivery_artifacts_required else True,
        },
        "mainline_assessment": {
            "phase_verdict": phase_verdict,
            "phase_total_score": phase_total_score,
            "blockers_count": blockers_count,
            "review_bound_items_count": review_bound_items_count,
            "phase_verdict_path": str(mainline_summary.get("phase_verdict_path") or ""),
            "phase_scorecard_path": str(mainline_summary.get("phase_scorecard_path") or ""),
            "phase_acceptance_matrix_path": str(mainline_summary.get("phase_acceptance_matrix_path") or ""),
        },
        "surface_contract": surface_contract,
        "warnings": warnings,
    }


def phase4_summary(root: Path, phase3_root: Path, *, closure_mode: str = "runtime-closure") -> dict[str, Any]:
    metadata = load_json(first_existing(root, "phase4-run-metadata.json"))
    quality = load_json(first_existing(root, "phase4-quality-check.json"))
    gate = load_json(first_existing(root, "phase4-delivery-gate.json"))
    retained_proof_mode = closure_mode == "retained-proof"
    stage3_summary = first_existing(root, "stage-03-validation-closure-and-delivery-readiness-judgment/stage-03-summary.json")
    metadata_phase3_root = str(metadata.get("phase3_root", "")).strip()
    phase3_root_matches = metadata_phase3_root == str(phase3_root.resolve())
    warnings = gate.get("warnings", [])
    mainline_assessment = load_phase_mainline_assessment(root, metadata=metadata)
    return {
        "root": str(root),
        "status": str(gate.get("recommended_formal_state") or quality.get("overall_quality_gate") or "unknown"),
        "closure_decision": str(gate.get("closure_decision") or quality.get("overall_quality_gate") or "unknown"),
        "closure_mode": "retained-proof" if retained_proof_mode else "runtime-closure",
        "artifacts": {
            "quality_check": str(root / "phase4-quality-check.json"),
            "delivery_gate": str(root / "phase4-delivery-gate.json"),
            "stage3_summary": str(stage3_summary) if stage3_summary else "",
            "phase_verdict": str(mainline_assessment.get("phase_verdict_path") or ""),
            "phase_mainline_scorecard": str(mainline_assessment.get("phase_scorecard_path") or ""),
            "phase_acceptance_matrix": str(mainline_assessment.get("phase_acceptance_matrix_path") or ""),
        },
        "checks": {
            "quality_check_present": bool(quality),
            "delivery_gate_present": bool(gate),
            "stage3_summary_present": bool(stage3_summary),
            "retained_proof_mode": retained_proof_mode,
            "phase3_root_matches": phase3_root_matches,
            "phase3_root_linkage_satisfied": phase3_root_matches or retained_proof_mode,
            "phase_verdict_present": bool(mainline_assessment.get("present")),
        },
        "required_artifact_checks": {
            "quality_check_present": bool(quality),
            "delivery_gate_present": bool(gate),
            "stage3_summary_present": bool(stage3_summary),
        },
        "mainline_assessment": mainline_assessment,
        "warnings": warnings,
    }


def bool_icon(value: bool) -> str:
    return "yes" if value else "no"


def classify_mainline_verdict(
    phase1: dict[str, Any],
    phase2: dict[str, Any],
    phase3: dict[str, Any],
    phase4: dict[str, Any],
) -> tuple[str, list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    for phase_name, phase in (
        ("phase1", phase1),
        ("phase2", phase2),
        ("phase3", phase3),
        ("phase4", phase4),
    ):
        required_artifact_checks = phase.get("required_artifact_checks")
        if isinstance(required_artifact_checks, dict):
            missing = [name for name, passed in required_artifact_checks.items() if not passed]
        else:
            missing = [name for name, passed in phase.get("checks", {}).items() if not passed and name.endswith("_present")]
        if missing:
            failures.append(f"{phase_name} missing required artifacts: {', '.join(missing)}")

    phase1_mainline_verdict = str(phase1.get("mainline_assessment", {}).get("phase_verdict") or "").strip()
    if phase1_mainline_verdict:
        if phase1_mainline_verdict in {"BLOCKED", "RETURN-REMEDIATE"}:
            failures.append(f"phase1 mainline verdict is `{phase1_mainline_verdict}`")
        elif phase1_mainline_verdict == "PASS with review-bound items":
            warnings.append("phase1 mainline verdict is `PASS with review-bound items`")
    elif phase1["status"] == "blocked":
        failures.append("phase1 remains blocked")
    elif phase1["status"] in {"review-bound-but-not-ready", "unknown"}:
        warnings.append(f"phase1 status is `{phase1['status']}`")

    phase2_mainline_verdict = str(phase2.get("mainline_assessment", {}).get("phase_verdict") or "").strip()
    if phase2_mainline_verdict:
        if phase2_mainline_verdict in {"BLOCKED", "RETURN-REMEDIATE"}:
            failures.append(f"phase2 mainline verdict is `{phase2_mainline_verdict}`")
        elif phase2_mainline_verdict == "PASS with review-bound items":
            warnings.append("phase2 mainline verdict is `PASS with review-bound items`")
    elif phase2["status"] == "blocked":
        failures.append("phase2 remains blocked")
    elif phase2["status"] in {"pass-with-review-bound-items", "unknown"}:
        warnings.append(f"phase2 status is `{phase2['status']}`")

    if phase3["status"] == "blocked":
        failures.append("phase3 remains blocked")
    elif phase3["status"] != "delivery-ready":
        warnings.append(f"phase3 status is `{phase3['status']}`")
    phase3_mainline_verdict = str(phase3.get("mainline_assessment", {}).get("phase_verdict") or "").strip()
    if phase3_mainline_verdict in {"BLOCKED", "RETURN-REMEDIATE"}:
        failures.append(f"phase3 mainline verdict is `{phase3_mainline_verdict}`")
    elif phase3_mainline_verdict == "PASS with review-bound items":
        warnings.append("phase3 mainline verdict is `PASS with review-bound items`")
    if phase3["checks"].get("frontend_contract_required"):
        if not phase3["checks"].get("surface_contract_evidence_present"):
            failures.append("phase3 surface-contract evidence is missing from the delivery gate")
        elif not phase3["checks"].get("surface_contract_gate"):
            failures.append("phase3 surface-contract gate is not green")
    elif phase3["checks"].get("surface_contract_evidence_present") and not phase3["checks"].get("surface_contract_gate"):
        warnings.append("phase3 optional frontend surface-contract lane is present but not green")

    phase4_mainline_verdict = str(phase4.get("mainline_assessment", {}).get("phase_verdict") or "").strip()
    if phase4_mainline_verdict in {"BLOCKED", "RETURN-REMEDIATE"}:
        failures.append(f"phase4 mainline verdict is `{phase4_mainline_verdict}`")
    elif phase4["closure_decision"] in {"return", "testing-validation-return-required"}:
        failures.append("phase4 closure requires return")
    elif phase4["closure_decision"] in {"pass-with-review-bound-items", "pass-with-mock-dependency", "unknown"}:
        warnings.append(f"phase4 closure is `{phase4['closure_decision']}`")

    cross_phase_checks = {
        "phase2_references_phase1_prd": bool(phase2["checks"].get("phase1_prd_reference_visible")),
        "phase3_links_to_phase2_root": bool(phase3["checks"].get("phase2_root_linkage_satisfied")),
        "phase4_links_to_phase3_root": bool(phase4["checks"].get("phase3_root_linkage_satisfied")),
    }
    if not cross_phase_checks["phase2_references_phase1_prd"]:
        if not phase2_mainline_verdict:
            failures.append("cross-phase linkage failed: phase2_references_phase1_prd")
    for key in ("phase3_links_to_phase2_root", "phase4_links_to_phase3_root"):
        if not cross_phase_checks[key]:
            failures.append(f"cross-phase linkage failed: {key}")

    warnings.extend(str(item) for item in phase3.get("warnings", []))
    warnings.extend(str(item) for item in phase4.get("warnings", []))

    if failures:
        return "blocked", failures, warnings
    if warnings:
        return "pass-with-known-gaps", failures, warnings
    return "pass", failures, warnings


def build_markdown(
    *,
    case_name: str,
    version: str,
    verdict: str,
    failures: list[str],
    warnings: list[str],
    phase1: dict[str, Any],
    phase2: dict[str, Any],
    phase3: dict[str, Any],
    phase4: dict[str, Any],
) -> str:
    def phase_section(title: str, phase: dict[str, Any]) -> list[str]:
        lines = [
            f"## {title}",
            f"- root: `{phase['root']}`",
            f"- status: `{phase.get('status', 'unknown')}`",
        ]
        if phase.get("closure_mode"):
            lines.append(f"- closure_mode: `{phase['closure_mode']}`")
        if phase.get("closure_decision"):
            lines.append(f"- closure_decision: `{phase['closure_decision']}`")
        mainline_assessment = phase.get("mainline_assessment")
        if isinstance(mainline_assessment, dict) and mainline_assessment.get("phase_verdict"):
            lines.append(f"- phase_verdict: `{mainline_assessment['phase_verdict']}`")
            if mainline_assessment.get("phase_total_score") is not None:
                lines.append(f"- phase_total_score: `{mainline_assessment['phase_total_score']}`")
            lines.append(f"- phase_blockers_count: `{mainline_assessment.get('blockers_count', 0)}`")
            lines.append(f"- phase_review_bound_items_count: `{mainline_assessment.get('review_bound_items_count', 0)}`")
        lines.append("- checks:")
        for key, value in phase.get("checks", {}).items():
            lines.append(f"  - {key}: `{bool_icon(bool(value))}`")
        surface_contract = phase.get("surface_contract")
        if isinstance(surface_contract, dict) and surface_contract.get("present"):
            lines.append("- surface_contract:")
            lines.append(f"  - source: `{surface_contract.get('source') or 'unknown'}`")
            lines.append(f"  - gate: `{bool_icon(bool(surface_contract.get('gate')))}`")
            lines.append(
                f"  - core_interaction_guess_count: `{int(surface_contract.get('core_interaction_guess_count', 0) or 0)}`"
            )
            lines.append(
                f"  - operable_cross_page_flow_count: `{int(surface_contract.get('operable_cross_page_flow_count', 0) or 0)}`"
            )
            lines.append(
                f"  - core_surface_pass_count: `{int(surface_contract.get('core_surface_pass_count', 0) or 0)}`"
            )
            lines.append(
                f"  - core_surface_count: `{int(surface_contract.get('core_surface_count', 0) or 0)}`"
            )
            role_alignment = surface_contract.get("role_surface_alignment", {})
            if isinstance(role_alignment, dict):
                lines.append(f"  - role_surface_alignment: `{bool_icon(bool(role_alignment.get('all_core_surfaces_aligned')))}`")
        lines.append("- artifacts:")
        for key, value in phase.get("artifacts", {}).items():
            lines.append(f"  - {key}: `{value or 'missing'}`")
        return lines

    lines = [
        "# P1-P4 Mainline Closure Summary",
        "",
        "## Run Metadata",
        f"- case_name: `{case_name}`",
        f"- version: `{version}`",
        f"- overall_verdict: `{verdict}`",
        "",
        "## Failures",
    ]
    lines.extend([f"- {item}" for item in failures] or ["- none"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {item}" for item in warnings] or ["- none"])
    lines.extend([""])
    lines.extend(phase_section("Phase-1", phase1))
    lines.extend([""])
    lines.extend(phase_section("Phase-2", phase2))
    lines.extend([""])
    lines.extend(phase_section("Phase-3", phase3))
    lines.extend([""])
    lines.extend(phase_section("Phase-4", phase4))
    lines.append("")
    return localize_p1_p4_mainline_closure_summary("\n".join(lines) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Emit one repo-level closure summary for a completed P1 -> P4 mainline run")
    parser.add_argument("--phase1-root", required=True)
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--phase3-root", required=True)
    parser.add_argument("--phase4-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--case-name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--closure-mode", choices=("runtime-closure", "retained-proof"), default="runtime-closure")
    return parser


def parse_p1_p4_mainline_closure_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def build_p1_p4_mainline_closure_context(args: argparse.Namespace) -> P1P4MainlineClosureContext:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return P1P4MainlineClosureContext(
        phase1_root=Path(args.phase1_root).resolve(),
        phase2_root=Path(args.phase2_root).resolve(),
        phase3_root=Path(args.phase3_root).resolve(),
        phase4_root=Path(args.phase4_root).resolve(),
        output_dir=output_dir,
        case_name=str(args.case_name).strip(),
        version=str(args.version).strip(),
        closure_mode=str(args.closure_mode).strip() or "runtime-closure",
        report_path=output_dir / "p1-p4-mainline-closure-report.json",
        summary_path=output_dir / "p1-p4-mainline-closure-summary.md",
    )


def build_p1_p4_mainline_closure_report(context: P1P4MainlineClosureContext) -> dict[str, Any]:
    phase1 = phase1_summary(context.phase1_root)
    phase1_prd = Path(phase1["artifacts"]["prd_main_document"]) if phase1["artifacts"]["prd_main_document"] else None
    phase2 = phase2_summary(context.phase2_root, phase1_prd)
    phase3 = phase3_summary(context.phase3_root, context.phase2_root, closure_mode=context.closure_mode)
    phase4 = phase4_summary(context.phase4_root, context.phase3_root, closure_mode=context.closure_mode)
    verdict, failures, warnings = classify_mainline_verdict(phase1, phase2, phase3, phase4)
    return {
        "case_name": context.case_name,
        "version": context.version,
        "closure_mode": context.closure_mode,
        "overall_verdict": verdict,
        "failures": failures,
        "warnings": warnings,
        "phases": {
            "phase1": phase1,
            "phase2": phase2,
            "phase3": phase3,
            "phase4": phase4,
        },
    }


def write_p1_p4_mainline_closure_outputs(context: P1P4MainlineClosureContext, report: dict[str, Any]) -> dict[str, str]:
    context.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    context.summary_path.write_text(
        build_markdown(
            case_name=context.case_name,
            version=context.version,
            verdict=str(report["overall_verdict"]),
            failures=[str(item) for item in report.get("failures", [])],
            warnings=[str(item) for item in report.get("warnings", [])],
            phase1=dict(report["phases"]["phase1"]),
            phase2=dict(report["phases"]["phase2"]),
            phase3=dict(report["phases"]["phase3"]),
            phase4=dict(report["phases"]["phase4"]),
        ),
        encoding="utf-8",
    )
    return {
        "report": str(context.report_path),
        "summary": str(context.summary_path),
    }


def emit_p1_p4_mainline_closure_summary(report: dict[str, Any], artifact_paths: dict[str, str]) -> int:
    print(
        json.dumps(
            {
                "overall_verdict": report["overall_verdict"],
                "report": artifact_paths["report"],
                "summary": artifact_paths["summary"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["overall_verdict"] != "blocked" else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_p1_p4_mainline_closure_args(argv)
    context = build_p1_p4_mainline_closure_context(args)
    report = build_p1_p4_mainline_closure_report(context)
    artifact_paths = write_p1_p4_mainline_closure_outputs(context, report)
    return emit_p1_p4_mainline_closure_summary(report, artifact_paths)


if __name__ == "__main__":
    raise SystemExit(main())
