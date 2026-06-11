#!/usr/bin/env python3
"""
Build optional Phase-4 Stage-04 release-readiness and final-handoff artifacts.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
from typing import Any

from common.cross_phase_surface_policy import find_cross_phase_surface_path
from phase4.phase4_common import ensure_list, load_json, load_json_if_exists, relative_to_root, render_markdown_table, utc_now_iso, write_json, write_text
from phase4.phase4_stage3_closure import STAGE_DIRNAME as STAGE03_DIRNAME


STAGE_DIRNAME = "stage-04-release-readiness-and-final-handoff"

REQUIRED_STAGE4_ARTIFACTS = [
    f"{STAGE_DIRNAME}/release-readiness-gate.json",
    f"{STAGE_DIRNAME}/go-no-go-closure.json",
    f"{STAGE_DIRNAME}/go-no-go-closure.md",
    f"{STAGE_DIRNAME}/residual-risk-acceptance.json",
    f"{STAGE_DIRNAME}/final-handoff-package.md",
    f"{STAGE_DIRNAME}/stage-04-summary.json",
]

FORBIDDEN_APPROVAL_MARKERS = [
    "release-approved",
    "final release approved",
    "release approval granted",
    "正式发布已批准",
]


def load_stage4_release_manifest(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    return load_json(path)


def normalize_signoff_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw_signoffs = manifest.get("signoffs", {})
    rows: list[dict[str, Any]] = []
    if isinstance(raw_signoffs, dict):
        for role, value in raw_signoffs.items():
            if isinstance(value, dict):
                status = str(value.get("status") or "").strip() or "pending"
                signer = str(value.get("signer") or value.get("signed_by") or "").strip()
                evidence = str(value.get("evidence") or value.get("evidence_path") or "").strip()
            else:
                status = str(value or "").strip() or "pending"
                signer = ""
                evidence = ""
            rows.append({"role": str(role), "status": status, "signer": signer, "evidence": evidence})
    for item in ensure_list(manifest.get("release_signoffs")):
        if isinstance(item, dict):
            rows.append(
                {
                    "role": str(item.get("role") or ""),
                    "status": str(item.get("status") or "pending"),
                    "signer": str(item.get("signer") or item.get("signed_by") or ""),
                    "evidence": str(item.get("evidence") or item.get("evidence_path") or ""),
                }
            )
    return [row for row in rows if row["role"].strip()]


def build_release_signoff_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    rows = normalize_signoff_rows(manifest)
    required_roles = [
        str(role)
        for role in ensure_list(manifest.get("required_signoff_roles") or ["engineering", "product", "operations"])
        if str(role).strip()
    ]
    by_role = {row["role"]: row for row in rows}
    normalized_required_rows = [
        by_role.get(role, {"role": role, "status": "pending", "signer": "", "evidence": ""}) for role in required_roles
    ]
    complete = bool(manifest) and all(row["status"] == "signed-off" and row["signer"].strip() for row in normalized_required_rows)
    return {
        "manifest_present": bool(manifest),
        "required_roles": required_roles,
        "required_rows": normalized_required_rows,
        "release_signoffs_complete": complete,
        "pending_roles": [row["role"] for row in normalized_required_rows if row["status"] != "signed-off" or not row["signer"].strip()],
    }


def build_residual_risks(stage3_summary: dict[str, Any], release_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    accepted_review_bound = bool(
        release_manifest.get("accepted_review_bound_items") or release_manifest.get("accept_residual_risk")
    )
    accepted_mock_dependency = bool(release_manifest.get("accepted_mock_dependency") or release_manifest.get("accept_residual_risk"))
    accepted_signoff_pending = bool(release_manifest.get("accepted_pending_signoffs") or release_manifest.get("accept_residual_risk"))
    risks: list[dict[str, Any]] = []
    if int(stage3_summary.get("review_bound_count") or 0) > 0:
        risks.append(
            {
                "risk_id": "stage03-review-bound-items",
                "severity": "medium",
                "source": "stage-03",
                "description": "Stage-03 left review-bound validation items visible for downstream handling.",
                "accepted": accepted_review_bound,
                "accepted_by": str(release_manifest.get("risk_accepted_by") or ""),
            }
        )
    if str(stage3_summary.get("closure_decision") or "") == "pass-with-mock-dependency":
        risks.append(
            {
                "risk_id": "stage03-mock-dependency",
                "severity": "high",
                "source": "stage-03",
                "description": "Stage-03 closure depends on explicit mock or conditional runtime truth.",
                "accepted": accepted_mock_dependency,
                "accepted_by": str(release_manifest.get("risk_accepted_by") or ""),
            }
        )
    if int(stage3_summary.get("signoff_pending_count") or 0) > 0 or int(stage3_summary.get("signoff_not_ready_count") or 0) > 0:
        risks.append(
            {
                "risk_id": "stage03-critical-path-signoff",
                "severity": "medium",
                "source": "stage-03",
                "description": "Critical-path UI/visual sign-off is pending or not ready in Stage-03 evidence.",
                "accepted": accepted_signoff_pending,
                "accepted_by": str(release_manifest.get("risk_accepted_by") or ""),
            }
        )
    for index, item in enumerate(ensure_list(release_manifest.get("risk_acceptance")), start=1):
        if isinstance(item, dict):
            risks.append(
                {
                    "risk_id": str(item.get("risk_id") or f"release-manifest-risk-{index:02d}"),
                    "severity": str(item.get("severity") or "medium"),
                    "source": "release-manifest",
                    "description": str(item.get("risk") or item.get("description") or ""),
                    "accepted": bool(item.get("accepted") or item.get("accepted_by")),
                    "accepted_by": str(item.get("accepted_by") or ""),
                }
            )
    return risks


def decide_release_readiness(
    *,
    stage3_summary: dict[str, Any],
    s1_s3_contract_report: dict[str, Any],
    signoff_summary: dict[str, Any],
    residual_risks: list[dict[str, Any]],
    release_manifest: dict[str, Any],
) -> tuple[str, list[str], list[str], list[str]]:
    source_closure = str(stage3_summary.get("closure_decision") or "").strip()
    contract_status = str(s1_s3_contract_report.get("status") or "").strip()
    blocking_reasons: list[str] = []
    conditions: list[str] = []
    warnings: list[str] = []

    if source_closure == "return":
        blocking_reasons.append("stage03-return")
    if contract_status != "pass":
        blocking_reasons.append("s1-s3-contract-not-pass")
    if str(release_manifest.get("decision") or "").strip() == "no-go":
        blocking_reasons.append("release-manifest-no-go")

    if blocking_reasons:
        return "no-go", blocking_reasons, conditions, warnings

    if source_closure != "pass":
        conditions.append(f"source-closure-{source_closure}")
    if int(stage3_summary.get("review_bound_count") or 0) > 0:
        conditions.append("stage03-review-bound-items")
    if int(stage3_summary.get("signoff_pending_count") or 0) > 0:
        conditions.append("stage03-signoff-pending")
    if int(stage3_summary.get("signoff_not_ready_count") or 0) > 0:
        conditions.append("stage03-signoff-not-ready")
    if not bool(signoff_summary.get("release_signoffs_complete")):
        conditions.append("release-signoff-pending")
    unaccepted_risks = [risk for risk in residual_risks if not bool(risk.get("accepted"))]
    if unaccepted_risks:
        conditions.append("residual-risk-acceptance-pending")

    if not bool(signoff_summary.get("manifest_present")):
        warnings.append("No release sign-off manifest was supplied; Stage-04 must not claim owner approval.")
    if conditions:
        return "go-with-conditions", blocking_reasons, conditions, warnings
    return "go", blocking_reasons, conditions, warnings


def render_go_no_go_markdown(payload: dict[str, Any]) -> str:
    signoff_rows = [
        [row["role"], row["status"], row.get("signer", ""), row.get("evidence", "")]
        for row in ensure_list(payload.get("release_signoffs", {}).get("required_rows"))
        if isinstance(row, dict)
    ]
    risk_rows = [
        [risk["risk_id"], risk["severity"], str(bool(risk["accepted"])).lower(), risk.get("accepted_by", "")]
        for risk in ensure_list(payload.get("residual_risks"))
        if isinstance(risk, dict)
    ]
    return "\n".join(
        [
            "# Stage-04 Go / No-Go Closure",
            "",
            f"- release_readiness_decision: `{payload['release_readiness_decision']}`",
            f"- source_closure_decision: `{payload['source_closure_decision']}`",
            "- boundary: Stage-04 packages release-readiness posture; it does not execute deployment or fabricate owner approval.",
            "",
            "## Conditions",
            *[f"- `{condition}`" for condition in ensure_list(payload.get("conditions"))],
            "",
            "## Blocking Reasons",
            *[f"- `{reason}`" for reason in ensure_list(payload.get("blocking_reasons"))],
            "",
            "## Release Sign-Offs",
            render_markdown_table(["role", "status", "signer", "evidence"], signoff_rows),
            "",
            "## Residual Risks",
            render_markdown_table(["risk_id", "severity", "accepted", "accepted_by"], risk_rows),
        ]
    ).rstrip() + "\n"


def render_final_handoff_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Stage-04 Final Handoff Package",
            "",
            f"- release_readiness_decision: `{summary['release_readiness_decision']}`",
            f"- source_closure_decision: `{summary['source_closure_decision']}`",
            f"- s1_s3_output_contract_status: `{summary['s1_s3_output_contract_status']}`",
            "",
            "## Downstream May Use",
            "- Phase-4 Stage-01..03 validation closure artifacts as the testing-validation evidence boundary.",
            "- This Stage-04 package as a release-readiness coordination surface.",
            "",
            "## Downstream Must Not Assume",
            "- Release owner approval exists unless release sign-off rows are explicitly `signed-off` with a signer.",
            "- Deployment, rollback, cutover, or production go-live has been executed.",
            "- Review-bound Stage-03 items disappeared merely because a handoff package exists.",
            "",
            "## Required Follow-Up",
            *[f"- `{condition}`" for condition in ensure_list(summary.get("conditions"))],
            *[f"- `{reason}`" for reason in ensure_list(summary.get("blocking_reasons"))],
        ]
    ).rstrip() + "\n"


def build_phase4_stage4_release_readiness(
    *,
    phase3_root: Path,
    output_dir: Path,
    title: str,
    version: str,
    s1_s3_contract_report: dict[str, Any] | None = None,
    release_signoff_manifest: Path | None = None,
    output_locale: str | None = None,
) -> dict[str, Any]:
    del output_locale
    stage04_dir = output_dir / STAGE_DIRNAME
    stage04_dir.mkdir(parents=True, exist_ok=True)
    stage3_summary = load_json(output_dir / STAGE03_DIRNAME / "stage-03-summary.json")
    s1_s3_contract_report_path = find_cross_phase_surface_path(output_dir, "phase4", "phase4-output-contract-report.json")
    s1_s3_contract_report = s1_s3_contract_report or load_json_if_exists(s1_s3_contract_report_path) or {}
    release_manifest = load_stage4_release_manifest(release_signoff_manifest)
    signoff_summary = build_release_signoff_summary(release_manifest)
    residual_risks = build_residual_risks(stage3_summary, release_manifest)
    decision, blocking_reasons, conditions, warnings = decide_release_readiness(
        stage3_summary=stage3_summary,
        s1_s3_contract_report=s1_s3_contract_report,
        signoff_summary=signoff_summary,
        residual_risks=residual_risks,
        release_manifest=release_manifest,
    )

    gate_path = stage04_dir / "release-readiness-gate.json"
    closure_json_path = stage04_dir / "go-no-go-closure.json"
    closure_md_path = stage04_dir / "go-no-go-closure.md"
    risk_path = stage04_dir / "residual-risk-acceptance.json"
    handoff_path = stage04_dir / "final-handoff-package.md"
    summary_path = stage04_dir / "stage-04-summary.json"

    generated_at = utc_now_iso()
    summary = {
        "stage": "release-readiness-and-final-handoff",
        "title": title,
        "version": version,
        "generated_at": generated_at,
        "phase3_root": str(phase3_root),
        "output_dir": str(stage04_dir),
        "release_readiness_decision": decision,
        "source_closure_decision": str(stage3_summary.get("closure_decision") or ""),
        "s1_s3_output_contract_status": str(s1_s3_contract_report.get("status") or ""),
        "release_signoffs_complete": bool(signoff_summary.get("release_signoffs_complete")),
        "residual_risk_count": len(residual_risks),
        "unaccepted_residual_risk_count": len([risk for risk in residual_risks if not bool(risk.get("accepted"))]),
        "blocking_reasons": blocking_reasons,
        "conditions": conditions,
        "warnings": warnings,
        "artifacts": {
            "release_readiness_gate_json": relative_to_root(gate_path, output_dir),
            "go_no_go_closure_json": relative_to_root(closure_json_path, output_dir),
            "go_no_go_closure_md": relative_to_root(closure_md_path, output_dir),
            "residual_risk_acceptance_json": relative_to_root(risk_path, output_dir),
            "final_handoff_package_md": relative_to_root(handoff_path, output_dir),
            "stage04_summary_json": relative_to_root(summary_path, output_dir),
        },
    }
    gate = {
        "generated_at": generated_at,
        "release_readiness_decision": decision,
        "source_closure_decision": summary["source_closure_decision"],
        "checks": {
            "stage03_not_return": summary["source_closure_decision"] != "return",
            "s1_s3_contract_pass": summary["s1_s3_output_contract_status"] == "pass",
            "release_signoffs_complete": summary["release_signoffs_complete"],
            "residual_risks_all_accepted": summary["unaccepted_residual_risk_count"] == 0,
        },
        "blocking_reasons": blocking_reasons,
        "conditions": conditions,
        "warnings": warnings,
        "artifacts": summary["artifacts"],
    }
    closure_payload = {
        "generated_at": generated_at,
        "release_readiness_decision": decision,
        "source_closure_decision": summary["source_closure_decision"],
        "conditions": conditions,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "release_signoffs": signoff_summary,
        "residual_risks": residual_risks,
        "stage03_summary": relative_to_root(output_dir / STAGE03_DIRNAME / "stage-03-summary.json", output_dir),
        "phase4_delivery_gate": relative_to_root(output_dir / "phase4-delivery-gate.json", output_dir),
        "phase4_output_contract_report": relative_to_root(s1_s3_contract_report_path, output_dir),
    }
    risk_payload = {
        "generated_at": generated_at,
        "source": "phase4-stage04",
        "residual_risks": residual_risks,
        "unaccepted_residual_risk_count": summary["unaccepted_residual_risk_count"],
    }

    write_json(gate_path, gate)
    write_json(closure_json_path, closure_payload)
    write_text(closure_md_path, render_go_no_go_markdown(closure_payload))
    write_json(risk_path, risk_payload)
    write_text(handoff_path, render_final_handoff_markdown(summary))
    write_json(summary_path, summary)
    contract_report = validate_stage4_release_readiness_contract(output_dir)
    write_stage4_contract_report(
        contract_report,
        output_dir / "stage4-release-readiness-contract-report.json",
        output_dir / "stage4-release-readiness-contract-report.md",
    )
    summary["stage4_output_contract_status"] = contract_report["status"]
    write_json(summary_path, summary)
    return summary


def validate_stage4_release_readiness_contract(output_dir: Path) -> dict[str, Any]:
    missing_required_artifacts = [relative for relative in REQUIRED_STAGE4_ARTIFACTS if not (output_dir / relative).exists()]
    semantic_failures: list[str] = []
    gate = load_json_if_exists(output_dir / STAGE_DIRNAME / "release-readiness-gate.json") or {}
    summary = load_json_if_exists(output_dir / STAGE_DIRNAME / "stage-04-summary.json") or {}

    decision = str(gate.get("release_readiness_decision") or summary.get("release_readiness_decision") or "").strip()
    source_closure = str(gate.get("source_closure_decision") or summary.get("source_closure_decision") or "").strip()
    checks = gate.get("checks", {}) if isinstance(gate.get("checks"), dict) else {}
    if decision == "go" and not bool(checks.get("release_signoffs_complete")):
        semantic_failures.append("go-without-release-signoff")
    if source_closure == "return" and decision != "no-go":
        semantic_failures.append("stage03-return-not-no-go")

    for relative in [
        f"{STAGE_DIRNAME}/go-no-go-closure.md",
        f"{STAGE_DIRNAME}/final-handoff-package.md",
    ]:
        path = output_dir / relative
        if path.exists():
            text = path.read_text(encoding="utf-8").lower()
            if any(marker in text for marker in FORBIDDEN_APPROVAL_MARKERS):
                semantic_failures.append("stage4-claims-release-approval")
                break

    status = "pass" if not missing_required_artifacts and not semantic_failures else "fail"
    return {
        "status": status,
        "validated_at": utc_now_iso(),
        "output_dir": str(output_dir),
        "required_artifacts_count": len(REQUIRED_STAGE4_ARTIFACTS),
        "missing_required_artifacts": missing_required_artifacts,
        "semantic_failures": semantic_failures,
    }


def render_stage4_contract_report_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Stage-04 Release Readiness Contract Report",
            "",
            f"- status: `{report['status']}`",
            f"- required_artifacts_count: `{report['required_artifacts_count']}`",
            "",
            "## Missing Required Artifacts",
            *[f"- `{item}`" for item in ensure_list(report.get("missing_required_artifacts"))],
            "",
            "## Semantic Failures",
            *[f"- `{item}`" for item in ensure_list(report.get("semantic_failures"))],
        ]
    ).rstrip() + "\n"


def write_stage4_contract_report(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    write_json(json_path, report)
    write_text(markdown_path, render_stage4_contract_report_markdown(report))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build optional Phase-4 Stage-04 release-readiness artifacts")
    parser.add_argument("--phase3-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--title", default="Phase-4 Release Readiness")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--release-signoff-manifest")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = build_phase4_stage4_release_readiness(
        phase3_root=Path(args.phase3_root).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        title=args.title,
        version=args.version,
        release_signoff_manifest=Path(args.release_signoff_manifest).resolve() if args.release_signoff_manifest else None,
    )
    print(summary["release_readiness_decision"])
    return 0 if summary["stage4_output_contract_status"] == "pass" and summary["release_readiness_decision"] != "no-go" else 1


if __name__ == "__main__":
    raise SystemExit(main())
