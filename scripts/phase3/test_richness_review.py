from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from phase3.surface_policy import write_phase3_profiled_surface


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_test_texts(root: Path, relative: str) -> list[str]:
    directory = root / relative
    if not directory.exists():
        return []
    return [path.read_text(encoding="utf-8", errors="ignore") for path in sorted(directory.rglob("*.ts"))]


def _count_token(texts: list[str], token: str) -> int:
    return sum(text.count(token) for text in texts)


def _test_family_evidence(unit_texts: list[str], obligation_audit: dict[str, Any]) -> dict[str, int]:
    summary = obligation_audit.get("summary", {}) if isinstance(obligation_audit.get("summary"), dict) else {}
    isolated_from_audit = int(summary.get("isolated_unit_evidence_count", 0) or 0)
    module_from_audit = int(summary.get("module_evidence_count", 0) or 0)
    combined = "\n".join(unit_texts).lower()
    isolated_from_text = 1 if any(token in combined for token in ("vi.fn", "spyon", "tohavebeencalled")) else 0
    module_from_text = 1 if any(
        token in combined
        for token in ("resetgeneratedruntime", "invokehttpoperation", "buildoperationpayload", "generated runtime module")
    ) else 0
    return {
        "isolated_unit_evidence_count": max(isolated_from_audit, isolated_from_text),
        "module_evidence_count": max(module_from_audit, module_from_text),
    }


def _construction_review_bound_reasons(obligation_audit: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for key in ("warnings", "failures"):
        values = obligation_audit.get(key, [])
        if isinstance(values, list):
            reasons.extend(
                str(value).strip()
                for value in values
                if str(value).strip().endswith("_condition_not_derivable")
            )
    return sorted(set(reasons))


def _workflow_risk_signals(workspace_root: Path, obligation_audit: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    audit_gate = str(obligation_audit.get("overall_quality_gate", "")).strip()
    if audit_gate and audit_gate != "pass":
        risks.append("test_obligation_workflow_gate_failed")
    for key in ("failures", "warnings"):
        values = obligation_audit.get(key, [])
        if isinstance(values, list):
            risks.extend(str(value).strip() for value in values if str(value).strip())

    hardening = obligation_audit.get("hardening", {}) if isinstance(obligation_audit.get("hardening"), dict) else {}
    hardening_families = hardening.get("families", {}) if isinstance(hardening.get("families"), dict) else {}
    for family, payload in hardening_families.items():
        if not isinstance(payload, dict):
            continue
        if str(payload.get("status", "")) in {"missing", "review-bound"} and int(payload.get("missing_count", 0) or 0) > 0:
            risks.append(f"hardening_{family}_missing")

    unit_texts = _read_test_texts(workspace_root, "tests/unit/api/modules")
    unit_combined = "\n".join(unit_texts)
    if unit_texts and not any(token in unit_combined for token in ("vi.fn", "spyOn", "toHaveBeenCalled")):
        risks.append("unit_service_isolation_missing")
        risks.append("unit_repository_call_proof_missing")

    contract_texts = _read_test_texts(workspace_root, "tests/contracts")
    contract_combined = "\n".join(contract_texts)
    if "buildFailurePayload(operationId" in contract_combined and "expectedOwnerService" not in contract_combined:
        risks.append("contract_error_condition_may_be_virtual")

    scenario_texts = _read_test_texts(workspace_root, "tests/scenarios")
    scenario_combined = "\n".join(scenario_texts)
    scenario_lowered = scenario_combined.lower()
    if "buildFailurePayload(" in scenario_combined and not any(
        token in scenario_lowered
        for token in ("collectscenariostate", "beforerows", "afterrows", "state invariance", "toequal(beforerows")
    ):
        risks.append("scenario_failure_variant_state_invariance_unproven")

    replay_texts = _read_test_texts(workspace_root, "tests/replays")
    replay_combined = "\n".join(replay_texts).lower()
    if replay_texts and not any(token in replay_combined for token in ("idempot", "second", "duplicate", "rerun")):
        risks.append("replay_idempotency_stress_unproven")

    sql_texts = _read_test_texts(workspace_root, "tests/sql")
    sql_combined = "\n".join(sql_texts)
    if re.search(r"['\"]foreign_key['\"]\s*:\s*\[\s*\]", sql_combined):
        risks.append("sql_foreign_key_probe_review_bound")
    if sql_texts and "state update" in sql_combined.lower() and "update " not in sql_combined.lower():
        risks.append("sql_state_update_probe_weak")

    return sorted(set(risks))


def build_test_richness_review(
    *,
    output_dir: Path,
    test_obligation_audit_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    obligation_audit = _read_json(test_obligation_audit_path)
    unit_texts = _read_test_texts(output_dir, "tests/unit/api/modules")
    contract_texts = _read_test_texts(output_dir, "tests/contracts")
    scenario_texts = _read_test_texts(output_dir, "tests/scenarios")
    replay_texts = _read_test_texts(output_dir, "tests/replays")
    sql_texts = _read_test_texts(output_dir, "tests/sql")
    risk_signals = _workflow_risk_signals(output_dir, obligation_audit)
    test_family_evidence = _test_family_evidence(unit_texts, obligation_audit)
    construction_review_bound_reasons = _construction_review_bound_reasons(obligation_audit)
    hardening = obligation_audit.get("hardening", {}) if isinstance(obligation_audit.get("hardening"), dict) else {}
    formal_state_ceiling = str(hardening.get("formal_state_ceiling", "not-capped-by-hardening-gate"))

    workflow_status = "pass" if str(obligation_audit.get("overall_quality_gate", "pass")) == "pass" else "fail"
    agentic_status = "required"
    claim_ceiling = "review-bound"
    return {
        "artifact_kind": "phase3-test-richness-review",
        "control_boundary": {
            "workflow": "generate structure, collect signals, and enforce hard evidence floors",
            "agentic": "judge business assertion value and classify virtual assertions",
            "evidence": "cap release claims at the weakest verified proof surface",
        },
        "workflow_preflight": {
            "status": workflow_status,
            "source": str(test_obligation_audit_path) if test_obligation_audit_path else "",
            "risk_signals": risk_signals,
            "hardening": hardening,
            "test_family_evidence": test_family_evidence,
            "construction_review_bound_reasons": construction_review_bound_reasons,
            "signal_counts": {
                "unit_test_files": len(unit_texts),
                "contract_test_files": len(contract_texts),
                "scenario_test_files": len(scenario_texts),
                "replay_test_files": len(replay_texts),
                "sql_test_files": len(sql_texts),
                "unit_vi_fn_count": _count_token(unit_texts, "vi.fn"),
                "unit_spy_on_count": _count_token(unit_texts, "spyOn"),
                "unit_call_assertion_count": _count_token(unit_texts, "toHaveBeenCalled"),
                "contract_failure_payload_count": _count_token(contract_texts, "buildFailurePayload"),
            },
        },
        "agentic_review": {
            "status": agentic_status,
            "verdict": "review-bound",
            "required_classifications": [
                "real-business",
                "structural-only",
                "self-fulfilling",
                "missing",
            ],
            "required_questions": [
                "Does each sampled assertion prove a P1/P2 business rule or only generated shape?",
                "Are permission/conflict/replay branches caused by real state rather than forced errors?",
                "Can the claim be reviewed from behavior-card, OpenAPI, scenario, SQL, and runtime evidence links?",
            ],
        },
        "evidence_bridge": {
            "claim_ceiling": claim_ceiling,
            "claim_boundary": "workflow-preflight-only until agentic richness review is completed",
            "formal_state_ceiling": formal_state_ceiling,
            "required_sources": [
                "behavior-cards",
                "contracts/openapi.yaml",
                "test-obligation-audit.json",
                "tests/contracts",
                "tests/scenarios",
                "tests/replays",
                "tests/sql",
                "tests/unit/api/modules",
            ],
        },
        "summary": {
            "workflow_status": workflow_status,
            "agentic_review_status": agentic_status,
            "evidence_claim_ceiling": claim_ceiling,
            "formal_state_ceiling": formal_state_ceiling,
            "risk_signal_count": len(risk_signals),
        },
    }


def render_test_richness_review_markdown(review: dict[str, Any]) -> str:
    summary = review.get("summary", {}) if isinstance(review.get("summary"), dict) else {}
    workflow = review.get("workflow_preflight", {}) if isinstance(review.get("workflow_preflight"), dict) else {}
    agentic = review.get("agentic_review", {}) if isinstance(review.get("agentic_review"), dict) else {}
    evidence = review.get("evidence_bridge", {}) if isinstance(review.get("evidence_bridge"), dict) else {}
    hardening = workflow.get("hardening", {}) if isinstance(workflow.get("hardening"), dict) else {}
    hardening_families = hardening.get("families", {}) if isinstance(hardening.get("families"), dict) else {}
    risks = workflow.get("risk_signals", []) if isinstance(workflow.get("risk_signals"), list) else []
    questions = agentic.get("required_questions", []) if isinstance(agentic.get("required_questions"), list) else []
    lines = [
        "# P3 Test Richness Review Packet",
        "",
        "## Boundary",
        "- Workflow: generate structure, collect signals, and enforce hard evidence floors",
        "- Agentic: judge business assertion value and classify virtual assertions",
        "- Evidence: cap release claims at the weakest verified proof surface",
        "",
        "## Summary",
        f"- workflow_status: `{summary.get('workflow_status', 'unknown')}`",
        f"- agentic_review_status: `{summary.get('agentic_review_status', 'required')}`",
        f"- evidence_claim_ceiling: `{summary.get('evidence_claim_ceiling', 'review-bound')}`",
        f"- formal_state_ceiling: `{summary.get('formal_state_ceiling', 'not-capped-by-hardening-gate')}`",
        "",
        "## Hardening Gate",
        f"- overall_gate: `{hardening.get('overall_gate', 'unknown')}`",
        f"- formal_state_ceiling: `{hardening.get('formal_state_ceiling', 'not-capped-by-hardening-gate')}`",
        *[
            f"- `{family}`: `{payload.get('status', 'unknown') if isinstance(payload, dict) else 'unknown'}`"
            for family, payload in sorted(hardening_families.items())
        ],
        "",
        "## Workflow Risk Signals",
    ]
    lines.extend([f"- `{risk}`" for risk in risks] or ["- none"])
    lines.extend(
        [
            "",
            "## Agentic Review Questions",
            *[f"- {question}" for question in questions],
            "",
            "## Claim Boundary",
            f"- `{evidence.get('claim_boundary', 'workflow-preflight-only')}`",
            f"- formal_state_ceiling: `{evidence.get('formal_state_ceiling', 'not-capped-by-hardening-gate')}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_test_richness_review_artifacts(
    *,
    output_dir: Path,
    test_obligation_audit_path: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    review = build_test_richness_review(output_dir=output_dir, test_obligation_audit_path=test_obligation_audit_path)
    json_path = output_dir / "test-richness-review.json"
    markdown_path = write_phase3_profiled_surface(
        output_dir,
        "test-richness-review.md",
        render_test_richness_review_markdown(review),
    )
    json_path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = review.get("summary", {}) if isinstance(review.get("summary"), dict) else {}
    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "workflow_status": str(summary.get("workflow_status", "unknown")),
        "agentic_review_status": str(summary.get("agentic_review_status", "required")),
        "evidence_claim_ceiling": str(summary.get("evidence_claim_ceiling", "review-bound")),
        "risk_signal_count": int(summary.get("risk_signal_count", 0) or 0),
    }
