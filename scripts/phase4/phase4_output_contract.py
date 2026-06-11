from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_ARTIFACTS = [
    "phase-verdict.json",
    "phase4-delivery-gate.json",
    "phase4-quality-check.json",
    "phase4-run-metadata.json",
    "phase-acceptance-matrix.md",
    "phase-mainline-scorecard.md",
    "stage-01-acceptance-coverage-planning/acceptance-catalog.json",
    "stage-01-acceptance-coverage-planning/contract-registry.json",
    "stage-01-acceptance-coverage-planning/decision-coverage-alignment.json",
    "stage-01-acceptance-coverage-planning/runtime-environment-readiness.json",
    "stage-01-acceptance-coverage-planning/stage-01-summary.json",
    "stage-01-acceptance-coverage-planning/testing-validation-planning-package.md",
    "stage-01-acceptance-coverage-planning/acceptance-checklist.md",
    "stage-01-acceptance-coverage-planning/test-coverage-explanation.md",
    "stage-01-acceptance-coverage-planning/test-entry-exit-gate-checklist.md",
    "stage-01-acceptance-coverage-planning/test-execution-control.md",
    "stage-02-evidence-execution-and-defect-identification/test-evidence-index.json",
    "stage-02-evidence-execution-and-defect-identification/test-execution-results.json",
    "stage-02-evidence-execution-and-defect-identification/test-execution-evidence.md",
    "stage-02-evidence-execution-and-defect-identification/defect-record.json",
    "stage-02-evidence-execution-and-defect-identification/review-bound-record.json",
    "stage-02-evidence-execution-and-defect-identification/external-evidence-consumption.json",
    "stage-02-evidence-execution-and-defect-identification/frontend-surface-audit.json",
    "stage-02-evidence-execution-and-defect-identification/critical-path-signoff-record.json",
    "stage-02-evidence-execution-and-defect-identification/stage-02-summary.json",
    "stage-03-validation-closure-and-delivery-readiness-judgment/test-closure-judgment.md",
    "stage-03-validation-closure-and-delivery-readiness-judgment/downstream-boundary-note.md",
    "stage-03-validation-closure-and-delivery-readiness-judgment/stage-03-summary.json",
]


STAGE03_RELEASE_APPROVAL_PHRASES = (
    "release-approved",
    "release approved",
)

STAGE03_PRODUCTION_AUTHORIZATION_PHRASES = (
    "production go-live approved",
    "production release approved",
    "production deployment approved",
    "go-live approved",
    "owner sign-off complete",
    "real owner approval",
    "risk accepted",
    "production risk accepted",
)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def int_field(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def validate_phase4_output_contract(phase4_root: Path) -> dict[str, Any]:
    root = Path(phase4_root)
    missing = [relative for relative in REQUIRED_ARTIFACTS if not (root / relative).exists()]
    semantic_failures: list[str] = []

    delivery_gate = read_json(root / "phase4-delivery-gate.json")
    phase_verdict = read_json(root / "phase-verdict.json")
    raw_checks = delivery_gate.get("checks")
    checks = raw_checks if isinstance(raw_checks, dict) else {}
    closure_decision = str(delivery_gate.get("closure_decision", ""))
    recommended_state = str(delivery_gate.get("recommended_formal_state", ""))
    verdict = str(phase_verdict.get("verdict", ""))

    if not closure_decision:
        semantic_failures.append("missing-closure-decision")
    if closure_decision == "pass" and verdict not in {"PASS", "pass"}:
        semantic_failures.append("pass-closure-without-pass-verdict")
    if closure_decision == "return" and verdict not in {"RETURN-REMEDIATE", "return"}:
        semantic_failures.append("return-closure-without-return-verdict")
    if closure_decision == "pass" and recommended_state != "testing-validation-complete":
        semantic_failures.append("pass-without-testing-validation-complete")
    if closure_decision == "pass" and int_field(checks, "blocking_count") > 0:
        semantic_failures.append("plain-pass-with-blocking-items")
    if closure_decision == "pass" and int_field(checks, "review_bound_count") > 0:
        semantic_failures.append("plain-pass-with-review-bound-items")
    if closure_decision == "pass" and int_field(checks, "signoff_pending_count") > 0:
        semantic_failures.append("plain-pass-with-pending-signoff")

    stage03_text = ""
    for relative in (
        "stage-03-validation-closure-and-delivery-readiness-judgment/test-closure-judgment.md",
        "stage-03-validation-closure-and-delivery-readiness-judgment/downstream-boundary-note.md",
    ):
        path = root / relative
        if path.exists():
            stage03_text += path.read_text(encoding="utf-8", errors="ignore").lower()
    if any(phrase in stage03_text for phrase in STAGE03_RELEASE_APPROVAL_PHRASES):
        semantic_failures.append("stage03-claims-release-approval")
    if any(phrase in stage03_text for phrase in STAGE03_PRODUCTION_AUTHORIZATION_PHRASES):
        semantic_failures.append("stage03-claims-production-authorization")

    status = "pass" if not missing and not semantic_failures else "fail"
    return {
        "artifact_kind": "phase4-output-contract-report",
        "status": status,
        "phase4_root": str(root),
        "required_artifact_count": len(REQUIRED_ARTIFACTS),
        "missing_required_artifacts": missing,
        "semantic_failures": semantic_failures,
    }


def write_report(report: dict[str, Any], output_json: Path, output_md: Path | None = None) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if output_md is None:
        return
    output_md.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Phase-4 Output Contract Report",
        "",
        f"- status: `{report['status']}`",
        f"- required_artifact_count: `{report['required_artifact_count']}`",
        f"- missing_required_artifacts: `{len(report['missing_required_artifacts'])}`",
        f"- semantic_failures: `{len(report['semantic_failures'])}`",
        "",
    ]
    output_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Phase-4 output contract")
    parser.add_argument("--phase4-root", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    args = parser.parse_args(argv)

    report = validate_phase4_output_contract(Path(args.phase4_root))
    if args.output_json:
        write_report(report, Path(args.output_json), Path(args.output_md) if args.output_md else None)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
