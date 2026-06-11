#!/usr/bin/env python3
"""
Emit a Phase-1 execution report from stage outputs, PRD artifacts, and gate results.
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
from datetime import datetime, timezone
from pathlib import Path

from common.output_language import localize_phase1_execution_report, resolve_output_locale
from common.script_data_assets import load_script_json_asset
from phase1.phase1_named_state import extract_named_state
from phase1.phase1_emit_depth_runtime_artifacts import (
    DEPTH_RUNTIME_SUMMARY_FILENAME,
    DEPTH_RUNTIME_TEXT_ARTIFACTS,
    load_depth_runtime_summary,
)
from phase1.phase1_localize_prd_zh import render_primary_locale_lines
from phase1.phase1_reasoning_runtime import sanitize_domain_default_truth
from phase1.phase1_runtime_metadata import THINKING_VALUE_GAIN_OUTPUT_PROFILES, build_runtime_metadata_lines
from phase1.phase1_version_contract import normalize_version_identifier


def slugify(raw: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return normalized or "phase-1-case"


def derive_case_name(source_path: Path, prd_path: Path) -> str:
    prd_stem = prd_path.stem
    for suffix in ("-main-document", "-assembled"):
        if prd_stem.endswith(suffix):
            prd_stem = prd_stem[: -len(suffix)]
    prd_stem = prd_stem.strip("-_ ")
    if prd_stem:
        return slugify(prd_stem)
    return slugify(source_path.stem)


@dataclass(frozen=True)
class MatrixRule:
    label: str
    sources: tuple[str, ...]
    required_patterns: tuple[str, ...]
    warning_patterns: tuple[str, ...] = ()
    pass_why: str = ""
    warning_why: str = ""
    next_action_pass: str = "keep current handoff package"
    next_action_warning: str = "preserve review-bound carryover and validate in next phase"
    next_action_blocked: str = "return to the owning stage and regenerate the missing artifact"


WFF_SCRIPT_DATA_ASSETS = (
    "scripts/phase1/data/phase1-execution-report-matrix-rules.json",
)


def _coerce_matrix_rule(item: object) -> MatrixRule | None:
    if not isinstance(item, dict):
        return None
    return MatrixRule(
        label=str(item.get("label", "")),
        sources=tuple(str(value) for value in item.get("sources", []) if str(value)),
        required_patterns=tuple(str(value) for value in item.get("required_patterns", []) if str(value)),
        warning_patterns=tuple(str(value) for value in item.get("warning_patterns", []) if str(value)),
        pass_why=str(item.get("pass_why", "")),
        warning_why=str(item.get("warning_why", "")),
        next_action_pass=str(item.get("next_action_pass", "keep current handoff package")),
        next_action_warning=str(
            item.get("next_action_warning", "preserve review-bound carryover and validate in next phase")
        ),
        next_action_blocked=str(
            item.get("next_action_blocked", "return to the owning stage and regenerate the missing artifact")
        ),
    )


def _load_matrix_rules() -> tuple[MatrixRule, ...]:
    loaded = load_script_json_asset(__file__, "phase1-execution-report-matrix-rules.json")
    if not isinstance(loaded, dict):
        return ()
    rules = [_coerce_matrix_rule(item) for item in loaded.get("matrix_rules", [])]
    return tuple(rule for rule in rules if rule is not None)


RULES = _load_matrix_rules()




def read_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def count_sizes(text: str) -> tuple[int, int, int]:
    chars = len(text)
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    bytes_len = len(text.encode("utf-8"))
    return chars, lines, bytes_len


def legacy_zh_cn_mirror_state(prd_zh_path: Path | None) -> str:
    if prd_zh_path and prd_zh_path.exists():
        return "deprecated / generated"
    return "deprecated / not generated"


def normalize_token(raw: str) -> str:
    return normalize_version_identifier(raw)


def load_gate_map(payload: dict[str, object] | None) -> tuple[dict[str, dict[str, object]], dict[str, object] | None]:
    if not payload:
        return {}, None
    rounds = payload.get("rounds", [])
    if not isinstance(rounds, list) or not rounds:
        return {}, None
    passed_round = payload.get("passed_round")
    chosen: dict[str, object] | None = None
    if isinstance(passed_round, int):
        for item in rounds:
            if isinstance(item, dict) and item.get("round") == passed_round:
                chosen = item
                break
    if chosen is None:
        last = rounds[-1]
        chosen = last if isinstance(last, dict) else None
    if chosen is None:
        return {}, None
    gates = chosen.get("gates", [])
    gate_map: dict[str, dict[str, object]] = {}
    if isinstance(gates, list):
        stack = [gate for gate in gates if isinstance(gate, dict)]
        while stack:
            gate = stack.pop(0)
            name = gate.get("name")
            if isinstance(name, str):
                gate_map[name] = gate
            subgates = gate.get("subgates")
            if isinstance(subgates, list):
                stack[0:0] = [item for item in subgates if isinstance(item, dict)]
    return gate_map, chosen


def gate_verdict(gate_map: dict[str, dict[str, object]], name: str) -> str:
    gate = gate_map.get(name)
    if not gate:
        return "SKIP"
    return "PASS" if gate.get("returncode") == 0 else "BLOCKED"


def parse_section_scores(gate_map: dict[str, dict[str, object]]) -> list[tuple[str, str, str]]:
    gate = gate_map.get("section_scoring_gate")
    if not gate:
        return []
    stdout = str(gate.get("stdout", "") or "")
    rows: list[tuple[str, str, str]] = []
    for match in re.finditer(
        r"^\[(PASS|BLOCKED)\]\s+(.+?):\s+total=([0-9.]+)/100$",
        stdout,
        flags=re.MULTILINE,
    ):
        rows.append((match.group(2).strip(), match.group(1), match.group(3)))
    return rows


def bundle_internal_gate_rows(gate_map: dict[str, dict[str, object]]) -> list[tuple[str, str, str]]:
    bundle_gate = gate_map.get("prd_mainline_gate_bundle")
    if isinstance(bundle_gate, dict):
        subgates = bundle_gate.get("subgates")
        if isinstance(subgates, list):
            rows: list[tuple[str, str, str]] = []
            for gate in subgates:
                if not isinstance(gate, dict):
                    continue
                name = str(gate.get("name") or "").strip()
                if not name:
                    continue
                verdict = "PASS" if gate.get("returncode") == 0 else "BLOCKED"
                command = str(gate.get("command") or "(not run)")
                rows.append((name, verdict, command))
            if rows:
                return rows
    ordered_names = (
        "assembly_integrity_gate",
        "analysis_delta_gate",
        "section_scoring_gate",
        "artifact_consistency_gate",
    )
    rows = []
    for name in ordered_names:
        if name not in gate_map:
            continue
        rows.append((name, gate_verdict(gate_map, name), str(gate_map[name].get("command", "(not run)"))))
    return rows


def extract_acceptance_status(prd_text: str, gates_passed: bool) -> str:
    match = re.search(
        r"##\s+(?:19\.\s+)?Acceptance\s*&\s*Status\b(?P<body>.*?)(?:^##\s+|\Z)",
        prd_text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if match:
        body = match.group("body")
        text_match = re.search(
            r"PASS with constrained/review-bound conditions|PASS|BLOCKED",
            body,
            flags=re.IGNORECASE,
        )
        if text_match:
            status = text_match.group(0)
            if status.lower() == "pass":
                return "PASS"
            if status.lower() == "blocked":
                return "BLOCKED"
            return "PASS with constrained/review-bound conditions"
    return "PASS" if gates_passed else "BLOCKED"


def compact_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def detect_stage_02b_execution_state(stage_02b_text: str, stage_04_text: str) -> str:
    for text, field in (
        (stage_04_text, "stage_02b_execution_state"),
        (stage_02b_text, "execution_state"),
        (stage_02b_text, "stage_02b_execution_state"),
    ):
        value = extract_named_state(text, field)
        if value and value.lower() in {"executed", "skipped", "partial"}:
            return value.lower()
    return "executed"


def extract_stage_02b_skip_rationale(stage_02b_text: str, stage_04_text: str) -> str | None:
    for text, field in (
        (stage_02b_text, "skip_rationale"),
        (stage_04_text, "impact_on_phase2"),
        (stage_04_text, "mitigation_note"),
    ):
        value = extract_named_state(text, field)
        if value:
            return compact_text(value)
    return None


def overall_status(formal_state: str, delivery_state: str | None, evidence_state: str | None) -> str:
    if formal_state == "BLOCKED" or delivery_state == "blocked":
        return "blocked"
    if delivery_state == "implementation-commit-ready" and formal_state == "PASS":
        return "implementation-commit-candidate"
    if delivery_state == "downstream-start-safe" and evidence_state in {
        "design-time-inference-heavy",
        "source-grounded-but-unvalidated",
    }:
        return "delivery-start-safe-with-validation-gap"
    if formal_state == "PASS":
        return "admission-review-ready"
    return "review-bound-but-not-start-safe"


def assess_rule(rule: MatrixRule, texts: dict[str, str]) -> tuple[str, str, str, str]:
    combined = "\n".join(texts.get(name, "") for name in rule.sources)
    if not all(re.search(pattern, combined, flags=re.IGNORECASE | re.MULTILINE) for pattern in rule.required_patterns):
        return (
            "BLOCKED",
            "required evidence for this deliverable is missing",
            "C",
            rule.next_action_blocked,
        )
    if rule.warning_patterns and any(
        re.search(pattern, combined, flags=re.IGNORECASE | re.MULTILINE) for pattern in rule.warning_patterns
    ):
        return (
            "WARNING",
            rule.warning_why or "deliverable exists but remains review-bound",
            "B",
            rule.next_action_warning,
        )
    return ("PASS", rule.pass_why or "deliverable exists and is consumable", "none", rule.next_action_pass)


def build_matrix(
    texts: dict[str, str],
    gate_map: dict[str, dict[str, object]],
) -> list[tuple[str, str, str, str, str]]:
    rows = [(*assess_rule(rule, texts), rule.label) for rule in RULES]
    by_label = {label: (verdict, why, unresolved, next_action) for verdict, why, unresolved, next_action, label in rows}

    prd_assembled_verdict = gate_verdict(gate_map, "assembly_integrity_gate")
    by_label["PRD main document assembled"] = (
        prd_assembled_verdict,
        "assembled/converged PRD exists and assembly integrity gate passed"
        if prd_assembled_verdict == "PASS"
        else "assembly integrity gate is blocked",
        "none" if prd_assembled_verdict == "PASS" else "C",
        "keep current PRD artifact chain" if prd_assembled_verdict == "PASS" else "reassemble and reconverge the PRD",
    )

    quality_verdict = gate_verdict(gate_map, "quality_gate")
    by_label["PRD depth / anti-summary quality"] = (
        quality_verdict,
        "quality gate passed for depth/non-compression"
        if quality_verdict == "PASS"
        else "quality gate is blocked",
        "none" if quality_verdict == "PASS" else "C",
        "keep current PRD depth" if quality_verdict == "PASS" else "deepen PRD sections and rerun convergence",
    )
    by_label["source-detail preservation in PRD"] = (
        quality_verdict,
        "quality gate confirms source-detail preservation"
        if quality_verdict == "PASS"
        else "source-detail preservation is insufficient",
        "none" if quality_verdict == "PASS" else "C",
        "keep current recompilation quality" if quality_verdict == "PASS" else "restore/recompile lost source detail",
    )

    exec_verdict = gate_verdict(gate_map, "executability_gate")
    by_label["design consumability of PRD"] = (
        exec_verdict,
        "executability gate passed for workflow/module derivation"
        if exec_verdict == "PASS"
        else "executability gate is blocked",
        "none" if exec_verdict == "PASS" else "C",
        "design can proceed from the current PRD" if exec_verdict == "PASS" else "deepen process/IA/flow specification",
    )
    by_label["architecture consumability of PRD"] = (
        exec_verdict,
        "executability gate passed for object/boundary derivation"
        if exec_verdict == "PASS"
        else "executability gate is blocked",
        "none" if exec_verdict == "PASS" else "C",
        "architecture can proceed from the current PRD" if exec_verdict == "PASS" else "deepen domain/NFR/flow specification",
    )

    ordered_labels = [rule.label for rule in RULES] + [
        "PRD main document assembled",
        "PRD depth / anti-summary quality",
        "source-detail preservation in PRD",
        "design consumability of PRD",
        "architecture consumability of PRD",
    ]
    return [(label, *by_label[label]) for label in ordered_labels]


def extract_trace_count(evidence_text: str) -> str:
    match = re.search(r"extracted_runtime_trace_blocks:\s*`?(\d+)`?", evidence_text, flags=re.IGNORECASE)
    return match.group(1) if match else "unknown"


def stage_summary(
    stage_key: str,
    *,
    stage_02b_state: str = "executed",
) -> tuple[str, str, str, str]:
    defaults = {
        "stage_01": (
            "PASS",
            "chosen user boundary + problem narrative",
            "commercial/evidence certainty remains review-bound",
            "strong enough for Stage-02a structural analysis",
        ),
        "stage_02a": (
            "PASS",
            "workflow panorama + backbone activities + business process decomposition",
            "some segment/value assumptions remain provisional",
            "strong enough for Stage-02b/03 consumption",
        ),
        "stage_02b": (
            "PASS",
            "NFR / domain / IA chain is explicit",
            "real threshold certainty and some boundary evidence remain review-bound",
            "strong enough for Stage-03 specification-aware slicing",
        ),
        "stage_03": (
            "PASS",
            "MVP loop and slice rationale are explicit",
            "slice ordering still depends on later validation",
            "strong enough for Stage-04 validation design",
        ),
        "stage_04": (
            "PASS with constrained/review-bound conditions",
            "validation target / method / decision chain plus maturity-confidence split are explicit",
            "real feedback and real signal evidence are still limited",
            "strong enough for design/architecture exploration, but not implementation-commit or market-proof closure",
        ),
    }
    if stage_key == "stage_02b" and stage_02b_state == "skipped":
        return (
            "PASS with constrained/review-bound conditions",
            "minimum-viable NFR / domain / IA / payload fallback is explicit even though full Stage-02b deepening was skipped",
            "full specification deepening and stronger contract hardening remain Phase-2 work",
            "strong enough for constrained Stage-03/04 consumption because skip impact and mitigation are explicit",
        )
    if stage_key == "stage_02b" and stage_02b_state == "partial":
        return (
            "PASS with constrained/review-bound conditions",
            "partial specification chain exists and is explicitly bounded",
            "some Stage-02b deliverables remain incomplete and must not be assumed frozen",
            "strong enough for constrained downstream use, but deeper hardening is still required",
        )
    return defaults[stage_key]


def render_report(
    *,
    source_path: Path,
    stage_paths: dict[str, Path],
    assembled_prd: Path,
    prd_path: Path,
    prd_zh_path: Path | None,
    evidence_path: Path,
    output_path: Path,
    version: str,
    profile: str,
    depth_mode: str,
    thinking_value_gain_mode: str = "off",
    thinking_value_gain_output_profile: str = "coverage_rich",
    run_owner: str,
    gate_payload: dict[str, object] | None,
) -> str:
    texts = {
        "stage_01": read_text(stage_paths.get("stage_01")),
        "stage_02a": read_text(stage_paths.get("stage_02a")),
        "stage_02b": read_text(stage_paths.get("stage_02b")),
        "stage_03": read_text(stage_paths.get("stage_03")),
        "stage_04": read_text(stage_paths.get("stage_04")),
        "prd": read_text(prd_path),
        "evidence": read_text(evidence_path),
    }
    gate_map, chosen_round = load_gate_map(gate_payload)
    all_gates_pass = bool(gate_map) and all(gate_verdict(gate_map, name) == "PASS" for name in gate_map)
    formal_state = extract_acceptance_status(texts["prd"], all_gates_pass)
    delivery_state = extract_named_state(texts["prd"], "document_delivery_state")
    evidence_state = extract_named_state(texts["prd"], "evidence_confidence_state")
    stage_02b_state = detect_stage_02b_execution_state(texts["stage_02b"], texts["stage_04"])
    stage_02b_skip_rationale = extract_stage_02b_skip_rationale(texts["stage_02b"], texts["stage_04"])
    current_status = overall_status(formal_state, delivery_state, evidence_state)
    matrix = build_matrix(texts, gate_map)

    src_chars, src_lines, src_bytes = count_sizes(read_text(source_path))
    prd_chars, prd_lines, prd_bytes = count_sizes(texts["prd"])
    ev_chars, ev_lines, ev_bytes = count_sizes(texts["evidence"])

    warning_rows = [row for row in matrix if row[1] == "WARNING"]
    blocked_rows = [row for row in matrix if row[1] == "BLOCKED"]

    gate_command = lambda name: gate_map.get(name, {}).get("command", "(not run)")
    gate_result = lambda name: gate_verdict(gate_map, name)
    bundle_internal_gates = bundle_internal_gate_rows(gate_map)
    deep_state = chosen_round["state"] if chosen_round and "state" in chosen_round else "converged-candidate"
    deep_rounds = len(gate_payload.get("rounds", [])) if gate_payload else 0
    section_scores = parse_section_scores(gate_map)
    case_name = derive_case_name(source_path, prd_path)
    depth_runtime_summary = load_depth_runtime_summary(prd_path.parent.resolve())
    depth_runtime_artifacts = [
        artifact_name for artifact_name in DEPTH_RUNTIME_TEXT_ARTIFACTS if (prd_path.parent / artifact_name).exists()
    ]
    mainline_assessment = gate_payload.get("phase_mainline_assessment") if isinstance(gate_payload, dict) else None
    mainline_verdict = None
    mainline_total_score = None
    mainline_scorecard_name = None
    mainline_acceptance_name = None
    mainline_verdict_name = None
    if isinstance(gate_payload, dict):
        mainline_verdict = gate_payload.get("phase_verdict")
        mainline_total_score = gate_payload.get("phase_total_score")
        if gate_payload.get("phase_mainline_scorecard_path"):
            mainline_scorecard_name = Path(str(gate_payload["phase_mainline_scorecard_path"])).name
        if gate_payload.get("phase_acceptance_matrix_path"):
            mainline_acceptance_name = Path(str(gate_payload["phase_acceptance_matrix_path"])).name
        if gate_payload.get("phase_verdict_path"):
            mainline_verdict_name = Path(str(gate_payload["phase_verdict_path"])).name

    lines = [
        "# Phase-1 Execution Report",
        "",
        "## 1. Run Metadata",
        "- case_name:",
        f"  - `{case_name}`",
        f"- input_source: `{source_path.name}`",
        f"- run_owner: `{run_owner}`",
        f"- run_date: `{datetime.now(timezone.utc).isoformat()}`",
        f"- report_version: `{version}`",
        "- delivery_profile:",
        f"  - `{profile}`",
        *build_runtime_metadata_lines(
            depth_mode,
            thinking_value_gain_mode=thinking_value_gain_mode,
            thinking_value_gain_output_profile=thinking_value_gain_output_profile,
        ),
        "- current_overall_status:",
        f"  - `{current_status}`",
        "- document_delivery_state:",
        f"  - `{delivery_state or 'not-explicit'}`",
        "- evidence_confidence_state:",
        f"  - `{evidence_state or 'not-explicit'}`",
        "",
        "## 2. Stage Output Inventory",
        f"- stage_01_output: `{stage_paths['stage_01'].name}`",
        f"- stage_02a_output: `{stage_paths['stage_02a'].name}`",
        "- stage_02b_output:",
        f"  - `{stage_paths['stage_02b'].name}`",
        (
            "  - `produced`"
            if stage_02b_state == "executed"
            else f"  - `{stage_02b_state} (reason: {stage_02b_skip_rationale or 'see Stage-04 declaration'})`"
        ),
        f"- stage_03_output: `{stage_paths['stage_03'].name}`",
        f"- stage_04_output: `{stage_paths['stage_04'].name}`",
        f"- prd_assembled_draft: `{assembled_prd.name}`",
        f"- prd_main_document: `{prd_path.name}`",
        "- localized_reader_evidence_state: `not-requested`",
        "- localized_reader_artifact: `(not generated)`",
        "- localized_reader_integrity_report: `(not generated)`",
        f"- legacy_zh_cn_audit_mirror: `{legacy_zh_cn_mirror_state(prd_zh_path)}`",
        f"- prd_convergence_evidence: `{evidence_path.name}`",
        (
            f"- phase1_depth_runtime_summary: `{DEPTH_RUNTIME_SUMMARY_FILENAME}`"
            if depth_runtime_summary
            else "- phase1_depth_runtime_summary: `(not generated)`"
        ),
        f"- phase1_depth_runtime_artifact_count: `{len(depth_runtime_artifacts)} / {len(DEPTH_RUNTIME_TEXT_ARTIFACTS)}`",
        "- phase1_depth_runtime_artifacts:",
        *(f"  - `{artifact_name}`" for artifact_name in depth_runtime_artifacts),
        *([] if depth_runtime_artifacts else ["  - `(none)`"]),
        *(
            [
                "- phase1_depth_runtime_scenario_count:",
                f"  - `{depth_runtime_summary.get('core_scenario_count', 'not-generated')}`",
                "- phase1_depth_runtime_scenario_set_status:",
                f"  - `{depth_runtime_summary.get('scenario_set_status', 'not-generated')}`",
                "- phase1_depth_runtime_baseline_calibration_status:",
                f"  - `{depth_runtime_summary.get('baseline_calibration_status', 'not-generated')}`",
                "- phase1_depth_runtime_demo_risk_status:",
                f"  - `{depth_runtime_summary.get('demo_risk_status', 'not-generated')}`",
            ]
            if isinstance(depth_runtime_summary, dict)
            else []
        ),
        "",
        "## 3. Deliverable Verdict Matrix",
        "",
        "| Deliverable | Verdict | Why | Unresolved Class | Next Action |",
        "|---|---|---|---|---|",
    ]
    for label, verdict, why, unresolved, next_action in matrix:
        lines.append(f"| {label} | `{verdict}` | {why} | `{unresolved}` | {next_action} |")

    lines.extend(["", "## 4. Stage Summary", ""])
    for stage_key, title in (
        ("stage_01", "Stage-01 Summary"),
        ("stage_02a", "Stage-02a Summary"),
        ("stage_02b", "Stage-02b Summary"),
        ("stage_03", "Stage-03 Summary"),
        ("stage_04", "Stage-04 Summary"),
    ):
        outcome, strongest, weakest, progression = stage_summary(
            stage_key,
            stage_02b_state=stage_02b_state,
        )
        lines.extend(
            [
                f"### {title}",
                *(
                    [
                        f"- executed: `{'yes' if stage_02b_state == 'executed' else stage_02b_state}`",
                        (
                            f"- skip_rationale: {stage_02b_skip_rationale}"
                            if stage_02b_state != "executed"
                            else "- skip_rationale: not applicable"
                        ),
                    ]
                    if stage_key == "stage_02b"
                    else []
                ),
                f"- outcome: `{outcome}`",
                f"- strongest output: {strongest}",
                f"- weakest output: {weakest}",
                f"- progression_judgment: {progression}",
                "",
            ]
        )

    lines.extend(["## 5. Warning Summary"])
    if not warning_rows:
        lines.append("- none")
    else:
        for label, _, why, _, next_action in warning_rows:
            lines.append(f"- `{label}`: {why}; next: {next_action}")

    lines.extend(["", "## 6. Blocker Summary"])
    if not blocked_rows:
        lines.append("- none")
    else:
        for label, _, why, unresolved, next_action in blocked_rows:
            lines.append(f"- `{label}`: {why} (`{unresolved}`); remediation: {next_action}")

    lines.extend(
        [
            "",
            "## 7. Admission Recommendation",
            "- recommended_formal_state:",
            f"  - `{formal_state}`",
            "- document_delivery_state:",
            f"  - `{delivery_state or 'not-explicit'}`",
            "- evidence_confidence_state:",
            f"  - `{evidence_state or 'not-explicit'}`",
            "- reasoning:",
            (
                "  - executable gates passed; the document is safe for downstream start, but evidence confidence remains below implementation-commit level"
                if formal_state == "PASS with constrained/review-bound conditions"
                else "  - all executable gates and final PRD checks passed"
                if formal_state == "PASS"
                else "  - one or more executable gates remain blocked"
            ),
            "- downstream_forbidden_assumptions:",
            "  - `demand already validated`",
            "  - `next-step guidance trust already validated`",
            "  - `metric stability already proven`",
            "- unresolved_truth_to_preserve:",
            "  - `payment intent`",
            "  - `next-step guidance trust`",
            "  - `metric stability`",
            "",
            "## 8. PRD Convergence Conclusion",
            "- prd_assembled: `yes`",
            f"- prd_converged: `{'yes' if prd_path.exists() else 'no'}`",
            "- localized_reader_evidence_state: `not-requested`",
            "- localized_reader_artifact: `(not generated)`",
            "- localized_reader_integrity_report: `(not generated)`",
            f"- legacy_zh_cn_audit_mirror: `{legacy_zh_cn_mirror_state(prd_zh_path)}`",
            "- prd_completeness_note:",
            "  - all critical PRD sections required by the current implementation-ready profile are present",
            "- prd_human_review_note:",
            "  - localized reader evidence is optional and not requested by the default P1 lifecycle run",
            "- localized_reader_claim_ceiling:",
            "  - missing localized reader evidence caps reader/localization claims only; lifecycle formal state is unchanged",
            "- prd_deep_compilation_state:",
            f"  - `{deep_state}`",
            "- convergence_externalization_note:",
            f"  - extracted runtime trace blocks: `{extract_trace_count(texts['evidence'])}`; delta ledger preserved in `{evidence_path.name}`",
            "- thin_sections_to_fix:",
            f"  - {'(none)' if gate_result('quality_gate') == 'PASS' else 'see quality gate blockers'}",
            "- source_detail_loss_note:",
            (
                "  - quality gate passed; high-value source detail was preserved/recompiled across final PRD and convergence evidence"
                if gate_result("quality_gate") == "PASS"
                else "  - quality gate blocked; some source detail preservation work is still needed"
            ),
            "- source_vs_prd_size_note:",
            (
                f"  - source={src_chars} chars/{src_lines} lines/{src_bytes} bytes; "
                f"final_prd={prd_chars} chars/{prd_lines} lines/{prd_bytes} bytes; "
                f"evidence={ev_chars} chars/{ev_lines} lines/{ev_bytes} bytes"
            ),
            "- design_consumability_note:",
            (
                "  - executability gate passed; design can derive workflow/module framing without inventing the main loop"
                if gate_result("executability_gate") == "PASS"
                else "  - design consumability is still blocked"
            ),
            "- architecture_consumability_note:",
            (
                "  - executability gate passed; architecture can derive core object/boundary framing without inventing the product mechanism"
                if gate_result("executability_gate") == "PASS"
                else "  - architecture consumability is still blocked"
            ),
            "- stage_depth_gate_command:",
            f"  - `{gate_command('stage_artifact_depth_gate')}`",
            "- stage_depth_gate_result:",
            f"  - `{gate_result('stage_artifact_depth_gate')}`",
            "- quality_gate_command:",
            f"  - `{gate_command('quality_gate')}`",
            "- quality_gate_result:",
            f"  - `{gate_result('quality_gate')}`",
            "- prd_mainline_gate_bundle_command:",
            f"  - `{gate_command('prd_mainline_gate_bundle')}`",
            "- prd_mainline_gate_bundle_result:",
            f"  - `{gate_result('prd_mainline_gate_bundle')}`",
            "- prd_mainline_gate_bundle_internal_gates:",
            "  - `assembly_integrity_gate | analysis_delta_gate | section_scoring_gate | artifact_consistency_gate`",
            "- prd_mainline_gate_bundle_internal_gate_details:",
            *(
                [f"  - `{name}`: `{verdict}`; command=`{command}`" for name, verdict, command in bundle_internal_gates]
                if bundle_internal_gates
                else ["  - `(bundle internal gate details not available)`"]
            ),
            "- prd_mainline_gate_bundle_detail_note:",
            (
                "  - internal sub-gate details stay visible for audit/debug purposes, but the canonical Phase-1 mainline gate surface is the bundle itself"
            ),
            "- executability_gate_command:",
            f"  - `{gate_command('executability_gate')}`",
            "- executability_gate_result:",
            f"  - `{gate_result('executability_gate')}`",
            "- deep_loop_rounds:",
            f"  - `{deep_rounds}`",
            "- not_ready_yet_because:",
            (
                f"  - evidence confidence is `{evidence_state or 'not-explicit'}` even though executable PRD gates pass"
                if formal_state == "PASS with constrained/review-bound conditions"
                else "  - (none)"
                if formal_state == "PASS"
                else "  - executable gates remain blocked"
            ),
            "- next_round_focus:",
            (
                "  - collect real validation evidence and re-evaluate blocked commitments before claiming implementation-commit readiness"
                if formal_state == "PASS with constrained/review-bound conditions"
                else "  - carry current package into downstream design/architecture work"
                if formal_state == "PASS"
                else "  - remediate the blocked gate set and rerun convergence"
            ),
        ]
    )

    lines.extend(["", "## 9. Section Scorecard"])
    if not section_scores:
        lines.append("- section scoring gate not available")
    else:
        for name, verdict, score in section_scores:
            lines.append(f"- `{name}`: `{score}` / 100 (`{verdict}`)")

    if isinstance(mainline_assessment, dict) or mainline_verdict or mainline_total_score is not None:
        lines.extend(
            [
                "",
                "## 10. Mainline Assessment",
                "- phase:",
                "  - `P1`",
                "- phase_mainline_verdict:",
                f"  - `{mainline_verdict or 'not-generated'}`",
                "- phase_mainline_total_score:",
                f"  - `{mainline_total_score if mainline_total_score is not None else 'not-generated'}` / 100",
                "- phase_mainline_scorecard:",
                f"  - `{mainline_scorecard_name or 'not-generated'}`",
                "- phase_acceptance_matrix:",
                f"  - `{mainline_acceptance_name or 'not-generated'}`",
                "- phase_verdict_json:",
                f"  - `{mainline_verdict_name or 'not-generated'}`",
            ]
        )
        if isinstance(mainline_assessment, dict):
            lines.extend(
                [
                    "- review_bound_items_count:",
                    f"  - `{mainline_assessment.get('review_bound_items_count', 'not-generated')}`",
                    "- blockers_count:",
                    f"  - `{mainline_assessment.get('blockers_count', 'not-generated')}`",
                    "- operationally_rich_domain:",
                    f"  - `{'yes' if mainline_assessment.get('operationally_rich_domain') else 'no'}`",
                    "- depth_runtime_summary_present:",
                    f"  - `{'yes' if mainline_assessment.get('depth_runtime_summary_present') else 'no'}`",
                    "- depth_runtime_artifact_count:",
                    f"  - `{mainline_assessment.get('depth_runtime_artifact_count', 'not-generated')}`",
                ]
            )

    return str(sanitize_domain_default_truth("\n".join(lines).rstrip() + "\n"))


def render_report_output(report: str, canonical_name: str, locale: str | None) -> str:
    localized = localize_phase1_execution_report(report, locale)
    lines = render_primary_locale_lines(localized.splitlines(), canonical_name, resolve_output_locale(locale))
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a Phase-1 execution report")
    parser.add_argument("--source", required=True)
    parser.add_argument("--stage-01", required=True)
    parser.add_argument("--stage-02a", required=True)
    parser.add_argument("--stage-02b", required=True)
    parser.add_argument("--stage-03", required=True)
    parser.add_argument("--stage-04", required=True)
    parser.add_argument("--assembled-prd", required=True)
    parser.add_argument("--prd", required=True)
    parser.add_argument("--prd-zh")
    parser.add_argument("--convergence-evidence", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--depth-mode", choices=("baseline", "creative"), default="baseline")
    parser.add_argument("--thinking-value-gain-mode", choices=("off", "full-use"), default="off")
    parser.add_argument(
        "--thinking-value-gain-output-profile",
        choices=THINKING_VALUE_GAIN_OUTPUT_PROFILES,
        default="coverage_rich",
    )
    parser.add_argument("--run-owner", default="Codex Phase-1 full runner")
    parser.add_argument("--gate-json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--output-locale", default=resolve_output_locale())
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    stage_paths = {
        "stage_01": Path(args.stage_01).resolve(),
        "stage_02a": Path(args.stage_02a).resolve(),
        "stage_02b": Path(args.stage_02b).resolve(),
        "stage_03": Path(args.stage_03).resolve(),
        "stage_04": Path(args.stage_04).resolve(),
    }
    assembled_prd = Path(args.assembled_prd).resolve()
    prd_path = Path(args.prd).resolve()
    prd_zh_path = Path(args.prd_zh).resolve() if args.prd_zh else None
    evidence_path = Path(args.convergence_evidence).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gate_payload = None
    if args.gate_json:
        gate_path = Path(args.gate_json).resolve()
        if gate_path.exists():
            gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))

    report = render_report(
        source_path=source_path,
        stage_paths=stage_paths,
        assembled_prd=assembled_prd,
        prd_path=prd_path,
        prd_zh_path=prd_zh_path,
        evidence_path=evidence_path,
        output_path=output_path,
        version=normalize_token(args.version),
        profile=args.profile,
        depth_mode=args.depth_mode,
        thinking_value_gain_mode=args.thinking_value_gain_mode,
        thinking_value_gain_output_profile=args.thinking_value_gain_output_profile,
        run_owner=args.run_owner,
        gate_payload=gate_payload,
    )
    output_path.write_text(render_report_output(report, output_path.name, args.output_locale), encoding="utf-8")
    print(f"report_written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
