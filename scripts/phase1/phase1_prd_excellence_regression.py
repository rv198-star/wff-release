#!/usr/bin/env python3
"""
Externalized PRD excellence scoring and historical regression for Phase-1 outputs.

Design goals:
- judge PRDs against a stricter "excellent review-bound PRD" bar
- avoid relying on the current runtime's own gate vocabulary as much as possible
- score historical outputs side-by-side so the improvement curve is visible
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import math
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from phase1.phase1_named_state import extract_named_state as extract_localized_named_state

@dataclass(frozen=True)
class Signal:
    label: str
    regex: str


@dataclass(frozen=True)
class DimensionResult:
    name: str
    score: float
    max_score: float
    matched: list[str]
    missing: list[str]
    notes: list[str]


@dataclass(frozen=True)
class LensResult:
    name: str
    score: float
    notes: list[str]


@dataclass(frozen=True)
class BusinessSemanticProfile:
    keyword_matched: list[str]
    keyword_missing: list[str]
    commercial_sharpness: int
    alternative_specificity: int
    source_semantic_retention: int
    semantic_compression: int
    adversarial_review: int
    assembler_filler_penalty: float
    critical_missing: list[str]
    notes: list[str]


@dataclass(frozen=True)
class ScoreResult:
    version: str
    prd_path: str
    lines: int
    chars: int
    duplicate_line_ratio: float
    dimension_results: list[DimensionResult]
    lens_results: list[LensResult]
    total_score: float
    tier: str


def signal(label: str, regex: str) -> Signal:
    return Signal(label=label, regex=regex)


CORE_H2_PATTERNS = {
    "problem": r"(?:2\.\s+)?Problem Statement",
    "users": r"(?:3\.\s+)?Target Users & Key Roles",
    "scenarios": r"(?:7\.\s+)?Business Scenarios",
    "requirements": r"(?:8\.\s+)?Requirements Structure",
    "nfr": r"(?:9\.\s+)?NFR\s*/\s*Quality Requirements",
    "domain": r"(?:10\.\s+)?Domain Model",
    "ia": r"(?:11\.\s+)?Information Architecture Direction",
    "mvp": r"(?:12\.\s+)?MVP Definition & Scope",
    "validation": r"(?:13\.\s+)?Validation Strategy & Current Conclusion",
    "requirements_translation": r"(?:14\.\s+)?User Stories, Use Cases, and Requirements",
    "risks": r"(?:16\.\s+)?Dependencies, Risks, and Review-Bound Truth",
    "handoff": r"(?:18\.\s+)?Handoff to Design\s*/\s*Architecture",
}


DETAIL_LINE_TARGETS = {
    "problem": 28,
    "users": 80,
    "scenarios": 50,
    "requirements": 160,
    "domain": 70,
    "ia": 55,
    "mvp": 180,
    "validation": 140,
    "handoff": 24,
}


REASONING_SIGNALS = (
    signal("problem_boundary_reframe", r"不是.*dashboard|not just|不等价|what this product is not"),
    signal("alternatives_comparison", r"Alternatives Comparison|candidate \| .* verdict"),
    signal("why_this_not_that", r"why_this|why this|why_chosen|why chosen"),
    signal("tradeoff", r"tradeoff|tension|取舍"),
    signal("decision_trace", r"Integrated Decision Trace|Decision Rationale|Key Decision Rationale"),
    signal("decision_consequence", r"revision_consequences|downstream consequence|what_changes_if_positive|what_changes_if_negative"),
    signal("constraints", r"Constraint Stress-Test|constraints|tension register|限制"),
    signal("deferred_honesty", r"deferred|non-goals|Out of Scope|out-of-scope"),
    signal("decision_state", r"continue / revise|Revise|Blocked|decision"),
    signal("explicit_reasoning_artifact", r"Reasoning Unit|reasoning_operator|decision_effect"),
)


BUSINESS_SIGNALS = (
    signal("why_now", r"Why Now|为什么现在值得做|Current Opportunity"),
    signal("segment_choice_logic", r"Why This Segment, Not Others|why this not that|最佳首发客群|首发聚焦|Why This Segment"),
    signal("value_proposition", r"Value Proposition|value proposition|核心主张|预期价值"),
    signal("business_outcome_path", r"线索|留资|咨询|pipeline|business result|业务结果"),
    signal("roi_or_investment_logic", r"ROI|预算判断|持续投入|continue / revise decision|资源决策"),
    signal("willingness_to_pay", r"付费意愿|willingness-to-pay|payment intent|试用/付费评估"),
    signal("buyer_or_budget_chain", r"budget owner|approver|business owner|预算 owner"),
    signal("competitive_context", r"竞品.*差距|competitor.*gap|竞品为何领先"),
    signal("product_is_not", r"What This Product Is Not|不是.*黑盒|not a black box"),
    signal("commercial_unknowns", r"payment intent|商业化|价格带|price band|真实付费信号"),
    signal("pricing_or_package", r"pricing|package|plan|价格带|\$\d+"),
    signal("scale_gate", r"Phase-2 条件|回归条件|return conditions|续费"),
)


GENERIC_COMMERCIAL_FILLER_PATTERNS = (
    r"improves?\s+business value",
    r"commercial value",
    r"adoption confidence",
    r"decision quality",
    r"workflow shell",
    r"clean workflow",
    r"generic commercial",
    r"better user experience",
    r"stronger value",
    r"business impact",
    r"商业价值",
    r"决策质量",
    r"采纳信心",
    r"用户体验更好",
)


ALTERNATIVE_SPECIFICITY_PATTERNS = (
    r"alternatives comparison",
    r"candidate\s+\|",
    r"rather than",
    r"instead of",
    r"not just",
    r"not merely",
    r"dashboard-only",
    r"detached report",
    r"report shell",
    r"passive reporting",
    r"spreadsheet",
    r"chat thread",
    r"manual reconstruction",
    r"what this product is not",
    r"而不是",
    r"不仅仅",
    r"替代方案",
    r"孤立页面",
    r"事后汇总",
    r"事后报告",
    r"脱离主链的事后报告",
    r"被动报表",
    r"手工重建",
)


PROOF_FOR_CONTINUE_PATTERNS = (
    r"proof_artifact_for_continue",
    r"decision_trigger",
    r"review summary",
    r"decision record",
    r"quote",
    r"pilot",
    r"threshold",
    r"continue / revise / pause",
    r"spend_at_risk",
    r"continuation_owner",
    r"proof artifact",
    r"proof path",
    r"证明物",
    r"决策触发器",
    r"复盘摘要",
    r"报价",
    r"试点",
    r"阈值",
    r"继续 / 调整 / 暂停",
    r"投入风险",
)


CHAIN_LITERALIZATION_PATTERNS = (
    r"`[^`\n]{0,220}(?:->|→)[^`\n]{0,220}(?:->|→)[^`\n]{0,220}`",
    r"(?:\b[\w\u4e00-\u9fff()/ -]{2,}\b\s*(?:->|→)\s*){2,}\b[\w\u4e00-\u9fff()/ -]{2,}\b",
)


CONTRACT_SPILLOVER_PATTERNS = (
    r"payload contract",
    r"typed workflow contract",
    r"traceability",
    r"state machine",
    r"registry",
    r"entity graph",
    r"permission model",
    r"audit policy",
    r"模块接口",
    r"payload",
    r"状态机",
    r"注册表",
    r"实体关系",
    r"权限模型",
    r"审计策略",
    r"可追溯",
)


REVIEW_BOUND_HONESTY_PATTERNS = (
    r"review-bound",
    r"missing evidence",
    r"until .*?(quote|pilot|interview|validation|external|buyer|budget)",
    r"current_truth_state",
    r"must not assume",
    r"forbidden assumptions",
    r"what remains unknown",
    r"review-bound / missing evidence",
    r"explicitly review-bound",
    r"仍未知",
    r"缺失证据",
    r"在 .*?(访谈|报价|试点|验证|外部|买方|预算).*?之前",
    r"禁止假设",
)


NOT_DASHBOARD_PATTERNS = (
    r"not just.*dashboard",
    r"not a black box",
    r"not merely.*report",
    r"detached report",
    r"dashboard-only",
    r"passive reporting",
    r"不是.*dashboard",
    r"不是.*黑盒",
    r"不只是.*报表",
    r"孤立页面",
    r"事后汇总",
    r"事后报告",
    r"脱离主链的事后报告",
    r"被动报表",
)


CONCRETE_ANCHOR_PATTERNS = (
    r"`[^`\n]{2,}`",
    r"\bowner\b",
    r"\bblocked reason\b",
    r"\bnext action\b",
    r"\bstate\b",
    r"\bobject\b",
    r"\bpayload\b",
    r"\btask\b",
    r"\brecord\b",
    r"\breview summary\b",
    r"\bappointment\b",
    r"\btreatment\b",
    r"\binvoice\b",
    r"\bpayment\b",
    r"\bfinding\b",
    r"\brecommendation\b",
    r"\bdecision\b",
    r"\bworkflow\b",
    r"负责人",
    r"阻塞原因",
    r"下一步动作",
    r"状态",
    r"对象",
    r"payload",
    r"任务",
    r"记录",
    r"复盘摘要",
    r"预约",
    r"治疗",
    r"账单",
    r"支付",
    r"发现",
    r"建议",
    r"决策",
    r"工作流",
)


USER_INSIGHT_SIGNALS = (
    signal("persona_profiles", r"Persona Profiles|Persona A|Persona B"),
    signal("jtbd", r"Jobs-to-be-Done|JTBD|user story|用户故事"),
    signal("out_of_scope_users", r"Out-of-Scope Users|Out-of-scope Users"),
    signal("role_interaction", r"Role Interaction Note|interaction chain|协作链"),
    signal("stakeholder_chain", r"Stakeholder Analysis|Adoption Chain|Stakeholder Chain"),
    signal("scenario_deep_dive", r"Scenario Deep Dive|Key Scenario Deep Analysis"),
    signal("success_criteria", r"success criteria|Success Criteria"),
    signal("adoption_fragility", r"Fragile Points in Adoption|Adoption Fragility|conflict|Resistance"),
)


EXECUTABILITY_SIGNALS = (
    signal("business_process", r"Business Process Decomposition|Business Process Identification"),
    signal("workflow_state", r"Workflow / State Detail|Operational Flow Specification"),
    signal("exception_flows", r"Exception and Failure Flows|Exception 1:|失败流程|异常"),
    signal("state_machine", r"State Machine and Transition Rules|transition guard"),
    signal("acceptance_criteria", r"Acceptance Criteria|AC-0[1-9]|AC-1[0-9]"),
    signal("ia_spec", r"IA Spec Matrix|screen/module"),
    signal("domain_model", r"Domain Model Direction|entity catalog|core entities"),
    signal("subsystem_boundaries", r"Business Subsystem Boundaries|Module Responsibility Matrix|subsystem"),
    signal("object_workflow_mapping", r"Object-to-Workflow Mapping|workflow step \| primary object"),
    signal("mermaid_flow", r"```mermaid"),
)


VALIDATION_SIGNALS = (
    signal("validation_targets", r"Validation Targets|target_1|Target 1"),
    signal("exact_assumptions", r"exact_assumption_tested|what_changes_if_positive|what_changes_if_negative"),
    signal("method_comparison", r"Method-Fit Comparison|candidate method"),
    signal("thresholds", r"threshold|70%|50%|至少\s*[0-9]+\s*位"),
    signal("evidence_state", r"Evidence State|what_is_design_time_inference|what_is_real_evidence"),
    signal("unknowns", r"what_remains_unknown|remaining_unknown|仍未知"),
    signal("decision_and_revision", r"Decision State|revision_consequences|Revise|Blocked"),
    signal("must_not_assume", r"must_not_assume|Must Not Assume|forbidden assumptions"),
    signal("risk_register", r"Risk Register|mitigation"),
    signal("review_bound_truth", r"Review-Bound Truth|carryover_truths|review-bound"),
)


HANDOFF_SIGNALS = (
    signal("design_start", r"Design Can Start"),
    signal("architecture_start", r"Architecture Can Start"),
    signal("must_not_assume", r"Must Not Assume"),
    signal("workflow_to_prototype", r"workflow prototype|prototype 首轮必须覆盖"),
    signal("object_and_boundary", r"核心对象链|object chain|边界|boundary"),
    signal("decision_expression", r"决策表达|decision view|信息优先级|可演进边界"),
)


DELIVERY_READINESS_SIGNALS = (
    signal("formal_acceptance", r"Acceptance\s*&\s*Status|PASS|BLOCKED|Revise"),
    signal("document_delivery_state", r"document_delivery_state|Document Delivery State"),
    signal("safe_start_scope", r"safe_start_scope|Safe Start Scope|safe_downstream_action"),
    signal("blocked_commitments", r"blocked_commitments|Blocked Commitments"),
    signal("design_handoff", r"Design Can Start"),
    signal("architecture_handoff", r"Architecture Can Start"),
    signal("acceptance_criteria", r"Acceptance Criteria|AC-0[1-9]|AC-1[0-9]"),
    signal("dependencies", r"Dependencies"),
    signal("risk_register", r"Risk Register|mitigation"),
    signal("must_not_assume", r"Must Not Assume|must_not_assume|forbidden_assumptions"),
)


EVIDENCE_CONFIDENCE_SIGNALS = (
    signal("evidence_confidence_state", r"evidence_confidence_state|Evidence Confidence State"),
    signal("design_time_inference", r"what_is_design_time_inference|design-time inference"),
    signal("real_evidence", r"what_is_real_evidence|real evidence"),
    signal("remaining_unknown", r"what_remains_unknown|remaining_unknown"),
    signal("review_bound_truth", r"Review-Bound Truth|review-bound"),
    signal("must_not_assume", r"Must Not Assume|must_not_assume|forbidden_assumptions"),
    signal("validation_dimensions", r"value_dimension|usability_dimension|feasibility_dimension"),
)


DOCUMENT_MATURITY_DIMENSIONS = (
    "structural_completeness",
    "detail_richness",
    "reasoning_and_tradeoff_depth",
    "business_value_and_commercial_logic",
    "user_and_operating_insight",
    "workflow_and_spec_executability",
    "validation_and_risk_discipline",
    "handoff_readiness",
    "coherence_and_non_template_quality",
)


WARNING_CONFIRMATION_SIGNALS = (
    signal("warning_summary_heading", r"Review Warnings / Pending External Confirmation"),
    signal("warning_ledger_heading", r"Warning & Pending Confirmation Ledger"),
    signal("document_maturity_interpretation", r"document_maturity_interpretation"),
    signal("business_completeness_interpretation", r"business_completeness_interpretation"),
    signal("missing_external_confirmation", r"missing_external_confirmation"),
    signal("stronger_commitment_blocker", r"stronger_commitment_blocker"),
)


DELIVERY_COMPLETENESS_STATES = {
    "implementation-commit-ready": 1.0,
    "downstream-start-safe": 0.88,
    "review-ready": 0.7,
    "artifact-draft": 0.45,
    "blocked": 0.15,
}


EVIDENCE_COMPLETENESS_STATES = {
    "externally-validated": 1.0,
    "partially-signal-backed": 0.82,
    "source-grounded-but-unvalidated": 0.62,
    "design-time-inference-heavy": 0.38,
    "contradicted": 0.05,
}


LOCALIZED_STATE_ALIASES = {
    "可进入实现承诺": "implementation-commit-ready",
    "可安全启动下游": "downstream-start-safe",
    "评审就绪": "review-ready",
    "产物草稿": "artifact-draft",
    "阻塞": "blocked",
    "已阻塞": "blocked",
    "已被外部验证": "externally-validated",
    "已有部分信号支撑": "partially-signal-backed",
    "基于素材但未外部验证": "source-grounded-but-unvalidated",
    "设计期推断占主导": "design-time-inference-heavy",
    "已被证伪": "contradicted",
}


ALL_COMPLETENESS_STATES = set(DELIVERY_COMPLETENESS_STATES) | set(EVIDENCE_COMPLETENESS_STATES)


def normalize_state_token(raw: str | None, allowed: set[str] | None = None) -> str | None:
    if not raw:
        return None

    allowed_tokens = allowed or ALL_COMPLETENESS_STATES
    candidate = str(raw).strip().strip("`").lower()
    if not candidate:
        return None
    if candidate in allowed_tokens:
        return candidate

    inner_match = re.search(r"[（(]\s*([a-z0-9-]+)\s*[)）]", candidate, flags=re.IGNORECASE)
    if inner_match:
        canonical = inner_match.group(1).strip().lower()
        if canonical in allowed_tokens:
            return canonical

    stripped = re.sub(r"\s*[（(][^()（）]+[)）]\s*", "", candidate).strip()
    canonical = LOCALIZED_STATE_ALIASES.get(stripped)
    if canonical and canonical in allowed_tokens:
        return canonical
    return None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_h2_block(text: str, title_pattern: str) -> str:
    match = re.search(
        rf"^##\s+.*(?:{title_pattern})\b.*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return ""
    start = match.end()
    next_h2 = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)
    end = start + next_h2.start() if next_h2 else len(text)
    return text[start:end]


def extract_h3_block(text: str, title_pattern: str) -> str:
    match = re.search(
        rf"^###\s+.*(?:{title_pattern})\b.*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return ""
    start = match.end()
    next_h3 = re.search(r"^###\s+", text[start:], flags=re.MULTILINE)
    next_h2 = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)
    candidates = []
    if next_h3:
        candidates.append(start + next_h3.start())
    if next_h2:
        candidates.append(start + next_h2.start())
    end = min(candidates) if candidates else len(text)
    return text[start:end]


def count_nonempty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def match_labels(text: str, signals: tuple[Signal, ...]) -> tuple[list[str], list[str]]:
    matched = [
        item.label
        for item in signals
        if re.search(item.regex, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    ]
    missing = [item.label for item in signals if item.label not in matched]
    return matched, missing


def has_any_signal(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL) for pattern in patterns)


def count_signal_hits(text: str, patterns: tuple[str, ...]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL))


def count_pattern_occurrences(text: str, patterns: tuple[str, ...]) -> int:
    return sum(len(re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE)) for pattern in patterns)


def ratio_score(numerator: float, denominator: float, max_score: float) -> float:
    if denominator <= 0:
        return max_score
    return round(max_score * min(1.0, numerator / denominator), 1)


def count_markdown_tables(text: str) -> int:
    lines = text.splitlines()
    table_count = 0
    idx = 0
    while idx < len(lines) - 1:
        if lines[idx].lstrip().startswith("|") and re.search(r"\|\s*-{3,}", lines[idx + 1]):
            table_count += 1
            idx += 2
            while idx < len(lines) and lines[idx].lstrip().startswith("|"):
                idx += 1
            continue
        idx += 1
    return table_count


def count_numbered_steps(text: str) -> int:
    return len(re.findall(r"^\s*\d+\.\s+", text, flags=re.MULTILINE))


def count_acceptance_criteria(text: str) -> int:
    return len(re.findall(r"\bAC-\d+\b", text, flags=re.IGNORECASE))


def count_exception_flows(text: str) -> int:
    return len(re.findall(r"Exception\s+\d+|异常\s*\d+|失败场景\s*\d+", text, flags=re.IGNORECASE))


def count_state_transitions(text: str) -> int:
    return len(re.findall(r"->|→", text))


def count_domain_objects(text: str) -> int:
    block = (
        extract_h3_block(text, r"Core Business Objects|Entity Registry")
        or extract_h2_block(text, CORE_H2_PATTERNS["domain"])
    )
    table_rows = parse_markdown_table(block)
    object_names: set[str] = set()
    for row in table_rows:
        for key in ("object", "entity", "name", "core_object"):
            value = row.get(key, "").strip()
            if value:
                object_names.add(value.lower())
    if object_names:
        return len(object_names)
    hits = re.findall(r"\b[A-Z][A-Za-z0-9_]+(?:\s+[A-Z][A-Za-z0-9_]+)*\b", block)
    return len(set(item.lower() for item in hits))


def count_ia_rows(text: str) -> int:
    matches = re.finditer(
        r"###\s+.*(?:IA Spec Matrix|Information Architecture Direction)(?P<body>.*?)(?:^###\s+|^##\s+|\Z)",
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    best = 0
    for match in matches:
        body = match.group("body")
        rows = max(0, sum(1 for line in body.splitlines() if line.lstrip().startswith("|")) - 2)
        best = max(best, rows)
    return best


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    def normalize_table_header(cell: str) -> str:
        candidate = cell.strip()
        inner_match = re.search(r"[（(]\s*([a-z0-9_]+)\s*[)）]", candidate, flags=re.IGNORECASE)
        if inner_match:
            return inner_match.group(1).strip().lower()
        return candidate.strip().lower().replace(" ", "_")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for idx in range(len(lines) - 1):
        if not lines[idx].startswith("|") or not lines[idx + 1].startswith("|"):
            continue
        if "---" not in lines[idx + 1]:
            continue
        headers = [normalize_table_header(cell) for cell in lines[idx].strip("|").split("|")]
        rows: list[dict[str, str]] = []
        probe = idx + 2
        while probe < len(lines) and lines[probe].startswith("|"):
            cells = [cell.strip() for cell in lines[probe].strip("|").split("|")]
            if len(cells) != len(headers):
                probe += 1
                continue
            rows.append(dict(zip(headers, cells)))
            probe += 1
        return rows
    return []


def normalize_line(line: str) -> str:
    value = line.strip().lower()
    value = re.sub(r"`[^`]+`", "`x`", value)
    value = re.sub(r"\btrial-v\d+\b", "trial-vx", value)
    value = re.sub(r"\b\d+(?:\.\d+)?\b", "n", value)
    value = re.sub(r"\s+", " ", value)
    return value


def duplicate_line_ratio(text: str) -> tuple[float, int]:
    candidates: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("|---") or line.startswith("```"):
            continue
        if line.startswith("|"):
            continue
        if len(line) < 20:
            continue
        candidates.append(normalize_line(line))
    if not candidates:
        return 0.0, 0
    counts: dict[str, int] = {}
    for line in candidates:
        counts[line] = counts.get(line, 0) + 1
    duplicate_instances = sum(count - 1 for count in counts.values() if count > 1)
    return duplicate_instances / len(candidates), duplicate_instances


def score_completeness(text: str) -> DimensionResult:
    matched: list[str] = []
    missing: list[str] = []
    for label, pattern in CORE_H2_PATTERNS.items():
        block = extract_h2_block(text, pattern)
        if block.strip():
            matched.append(label)
        else:
            missing.append(label)
    score = ratio_score(len(matched), len(CORE_H2_PATTERNS), 8.0)
    notes = [f"core_sections={len(matched)}/{len(CORE_H2_PATTERNS)}"]
    return DimensionResult("structural_completeness", score, 8.0, matched, missing, notes)


def score_detail_richness(text: str) -> DimensionResult:
    blocks = {name: extract_h2_block(text, pattern) for name, pattern in CORE_H2_PATTERNS.items()}
    line_ratios: list[float] = []
    notes: list[str] = []
    matched: list[str] = []
    missing: list[str] = []
    for name, target in DETAIL_LINE_TARGETS.items():
        lines = count_nonempty_lines(blocks.get(name, ""))
        ratio = min(1.0, lines / target) if target else 1.0
        line_ratios.append(ratio)
        notes.append(f"{name}_lines={lines}/{target}")
        if ratio >= 0.8:
            matched.append(f"{name}_line_depth")
        else:
            missing.append(f"{name}_line_depth")

    line_score = round((sum(line_ratios) / len(line_ratios)) * 6.0, 1)

    artifact_hits = 0
    table_count = count_markdown_tables(text)
    mermaid_count = len(re.findall(r"```mermaid", text))
    step_count = count_numbered_steps(text)
    ac_count = count_acceptance_criteria(text)
    exception_count = count_exception_flows(text)
    state_transition_count = count_state_transitions(text)
    domain_objects = count_domain_objects(text)
    ia_rows = count_ia_rows(text)
    artifact_checks = [
        ("tables>=8", table_count >= 8),
        ("mermaid>=2", mermaid_count >= 2),
        ("steps>=8", step_count >= 8),
        ("acceptance_criteria>=8", ac_count >= 8),
        ("exception_flows>=3", exception_count >= 3),
        ("state_transitions>=8", state_transition_count >= 8),
        ("domain_objects>=7", domain_objects >= 7),
        ("ia_rows>=6", ia_rows >= 6),
    ]
    for label, ok in artifact_checks:
        if ok:
            matched.append(label)
            artifact_hits += 1
        else:
            missing.append(label)
    artifact_score = round((artifact_hits / len(artifact_checks)) * 6.0, 1)
    notes.extend(
        [
            f"tables={table_count}",
            f"mermaid={mermaid_count}",
            f"numbered_steps={step_count}",
            f"acceptance_criteria={ac_count}",
            f"exception_flows={exception_count}",
            f"state_transitions={state_transition_count}",
            f"domain_objects={domain_objects}",
            f"ia_rows={ia_rows}",
        ]
    )
    return DimensionResult(
        "detail_richness",
        round(line_score + artifact_score, 1),
        12.0,
        matched,
        missing,
        notes,
    )


def score_signal_dimension(name: str, text: str, signals: tuple[Signal, ...], max_score: float) -> DimensionResult:
    matched, missing = match_labels(text, signals)
    score = ratio_score(len(matched), len(signals), max_score)
    notes = [f"matched={len(matched)}/{len(signals)}"]
    return DimensionResult(name, score, max_score, matched, missing, notes)


def combined_section_text(text: str, section_keys: tuple[str, ...]) -> str:
    return "\n\n".join(extract_h2_block(text, CORE_H2_PATTERNS[key]) for key in section_keys)


def score_executability(text: str) -> DimensionResult:
    result = score_signal_dimension(
        "workflow_and_spec_executability",
        combined_section_text(text, ("requirements", "nfr", "domain", "ia", "mvp", "validation")),
        EXECUTABILITY_SIGNALS,
        14.0,
    )
    bonus = 0.0
    if count_acceptance_criteria(text) >= 10:
        bonus += 0.5
    if count_exception_flows(text) >= 4:
        bonus += 0.5
    score = min(result.max_score, round(result.score + bonus, 1))
    notes = list(result.notes)
    if bonus:
        notes.append(f"bonus={bonus}")
    return DimensionResult(result.name, min(14.0, score), result.max_score, result.matched, result.missing, notes)


def score_handoff(text: str) -> DimensionResult:
    block = extract_h2_block(text, CORE_H2_PATTERNS["handoff"])
    matched, missing = match_labels(block, HANDOFF_SIGNALS)
    base = ratio_score(len(matched), len(HANDOFF_SIGNALS), 5.0)
    line_score = ratio_score(count_nonempty_lines(block), 24, 2.0)
    notes = [f"handoff_lines={count_nonempty_lines(block)}/24"]
    return DimensionResult("handoff_readiness", round(base + line_score, 1), 7.0, matched, missing, notes)


def score_coherence(text: str) -> DimensionResult:
    matched: list[str] = []
    missing: list[str] = []
    notes: list[str] = []

    summary = extract_h2_block(text, r"(?:1\.\s+)?Executive Summary")
    users = extract_h2_block(text, CORE_H2_PATTERNS["users"])
    validation = extract_h2_block(text, CORE_H2_PATTERNS["validation"])
    requirements = extract_h2_block(text, CORE_H2_PATTERNS["requirements"])
    mvp = extract_h2_block(text, CORE_H2_PATTERNS["mvp"])
    handoff = extract_h2_block(text, CORE_H2_PATTERNS["handoff"])
    domain = extract_h2_block(text, CORE_H2_PATTERNS["domain"])
    acceptance = extract_h2_block(text, r"(?:19\.\s+)?Acceptance\s*&\s*Status")

    if summary and users and validation:
        matched.append("primary_segment_consistency")
    else:
        missing.append("primary_segment_consistency")

    loop_pattern = r"(workflow|business record|module).*?(task|action|closure|review)"
    if re.search(loop_pattern, requirements, flags=re.IGNORECASE | re.DOTALL) and re.search(
        loop_pattern, mvp + "\n" + handoff, flags=re.IGNORECASE | re.DOTALL
    ):
        matched.append("core_loop_consistency")
    else:
        missing.append("core_loop_consistency")

    object_pattern = r"(object chain|core entities|core business objects|entity catalog|object-to-workflow mapping)"
    if re.search(object_pattern, domain + "\n" + handoff, flags=re.IGNORECASE | re.DOTALL):
        matched.append("object_chain_consistency")
    else:
        missing.append("object_chain_consistency")

    if re.search(r"review-bound|Revise|constrained", validation + "\n" + acceptance + "\n" + handoff, flags=re.IGNORECASE):
        matched.append("status_semantics_consistency")
    else:
        missing.append("status_semantics_consistency")

    duplicate_ratio, duplicate_instances = duplicate_line_ratio(text)
    notes.append(f"duplicate_line_ratio={duplicate_ratio:.3f}")
    notes.append(f"duplicate_line_instances={duplicate_instances}")

    base = ratio_score(len(matched), 4, 4.0)
    bonus = 1.0 if duplicate_ratio <= 0.05 else 0.5 if duplicate_ratio <= 0.08 else 0.0
    penalty = 0.0
    if duplicate_ratio > 0.14:
        penalty = 2.0
    elif duplicate_ratio > 0.10:
        penalty = 1.0
    elif duplicate_ratio > 0.08:
        penalty = 0.5
    score = max(0.0, min(5.0, round(base + bonus - penalty, 1)))
    if penalty:
        notes.append(f"duplication_penalty={penalty}")
    if bonus:
        notes.append(f"cohesion_bonus={bonus}")
    return DimensionResult("coherence_and_non_template_quality", score, 5.0, matched, missing, notes)


def concrete_business_anchor_density(text: str) -> int:
    count = 0
    count += int(has_any_signal(text, (CONCRETE_ANCHOR_PATTERNS[0],)))
    count += int(count_signal_hits(text, CONCRETE_ANCHOR_PATTERNS[1:]) >= 3)
    count += int(count_state_transitions(text) >= 2)
    count += int(count_acceptance_criteria(text) >= 3)
    return max(0, min(count, 4))


def score_commercial_sharpness_surface(text: str) -> int:
    if count_pattern_occurrences(text, CHAIN_LITERALIZATION_PATTERNS) >= 1 and count_pattern_occurrences(
        text,
        CONTRACT_SPILLOVER_PATTERNS,
    ) >= 1:
        return 0
    value_signal = has_any_signal(
        text,
        (
            r"value mechanism",
            r"business value",
            r"commercial value",
            r"roi",
            r"continued investment",
            r"manual reconstruction",
            r"detached report",
            r"decision chain",
            r"价值机制",
            r"商业价值",
            r"投入产出",
            r"继续投入",
            r"主线闭环",
            r"可判定的主线闭环",
            r"动作闭环",
            r"手工重建",
            r"决策链",
        ),
    )
    causal_signal = has_any_signal(
        text,
        (
            r"because",
            r"so that",
            r"therefore",
            r"turns?.+into",
            r"reduces?",
            r"improves?",
            r"because this",
            r"因为",
            r"从而",
            r"因此",
            r"让.+变成",
            r"降低",
            r"提升",
        ),
    )
    contrast_signal = has_any_signal(text, ALTERNATIVE_SPECIFICITY_PATTERNS) or has_any_signal(text, NOT_DASHBOARD_PATTERNS)
    proof_signal = has_any_signal(text, PROOF_FOR_CONTINUE_PATTERNS)
    anchor_density = concrete_business_anchor_density(text)
    filler_hits = count_signal_hits(text, GENERIC_COMMERCIAL_FILLER_PATTERNS)
    if value_signal and causal_signal and (contrast_signal or proof_signal) and anchor_density >= 2 and filler_hits <= 2:
        return 3
    if value_signal and causal_signal and anchor_density >= 1:
        return 2 if contrast_signal or proof_signal else 1
    if value_signal and (contrast_signal or proof_signal):
        return 1
    return 0


def score_alternative_specificity_surface(text: str) -> int:
    alternative_signal = has_any_signal(text, ALTERNATIVE_SPECIFICITY_PATTERNS)
    dashboard_signal = has_any_signal(text, NOT_DASHBOARD_PATTERNS)
    consequence_signal = has_any_signal(
        text,
        (
            r"if weak",
            r"otherwise",
            r"degenerates? into",
            r"falls back to",
            r"would still force",
            r"如果薄弱",
            r"否则",
            r"退化为",
            r"回退到",
        ),
    )
    if alternative_signal and (dashboard_signal or consequence_signal):
        return 2
    if alternative_signal or dashboard_signal:
        return 1
    return 0


def score_source_semantic_retention_surface(text: str) -> int:
    anchor_density = concrete_business_anchor_density(text)
    backtick_hits = len(re.findall(r"`[^`\n]{2,}`", text))
    typed_surface_hits = count_signal_hits(
        text,
        (
            r"\bappointment\b",
            r"\btreatment\b",
            r"\binvoice\b",
            r"\bvisit\b",
            r"\breview summary\b",
            r"\bfinding\b",
            r"\brecommendation\b",
            r"\bdecision record\b",
            r"\bowner\b",
            r"\bclinic\b",
            r"\bmarketing owner\b",
            r"\bbusiness owner\b",
            r"预约",
            r"治疗",
            r"账单",
            r"就诊",
            r"复盘摘要",
            r"发现",
            r"建议",
            r"决策记录",
            r"负责人",
            r"诊所",
        ),
    )
    filler_hits = count_signal_hits(text, GENERIC_COMMERCIAL_FILLER_PATTERNS)
    chain_overrender = count_pattern_occurrences(text, CHAIN_LITERALIZATION_PATTERNS)
    contract_overrender = count_pattern_occurrences(text, CONTRACT_SPILLOVER_PATTERNS)
    if chain_overrender >= 1 and contract_overrender >= 2:
        return 0
    if (anchor_density >= 3 and typed_surface_hits >= 3) or backtick_hits >= 4:
        return 2
    if anchor_density >= 2 and typed_surface_hits >= 1 and filler_hits <= 2:
        return 1
    return 0


def score_semantic_compression_surface(text: str) -> int:
    anchor_density = concrete_business_anchor_density(text)
    filler_hits = count_signal_hits(text, GENERIC_COMMERCIAL_FILLER_PATTERNS)
    duplicate_ratio, _ = duplicate_line_ratio(text)
    chain_overrender = count_pattern_occurrences(text, CHAIN_LITERALIZATION_PATTERNS)
    contract_overrender = count_pattern_occurrences(text, CONTRACT_SPILLOVER_PATTERNS)
    proof_repetition = count_pattern_occurrences(
        text,
        (
            r"proof_artifact_for_continue",
            r"decision_trigger",
            r"continuation_signal",
            r"review summary",
            r"决策触发器",
            r"继续信号",
            r"复盘摘要",
        ),
    )
    if chain_overrender >= 1 or contract_overrender >= 2 or proof_repetition >= 6:
        return 0
    if anchor_density >= 3 and filler_hits <= 1 and duplicate_ratio <= 0.08:
        return 2
    if anchor_density >= 2 and filler_hits <= 2 and duplicate_ratio <= 0.12:
        return 1
    return 0


def score_adversarial_review_surface(text: str) -> int:
    answered = 0
    if has_any_signal(text, ALTERNATIVE_SPECIFICITY_PATTERNS):
        answered += 1
    if has_any_signal(text, NOT_DASHBOARD_PATTERNS):
        answered += 1
    if has_any_signal(text, PROOF_FOR_CONTINUE_PATTERNS):
        answered += 1
    if has_any_signal(text, REVIEW_BOUND_HONESTY_PATTERNS):
        answered += 1
    return answered


def score_assembler_filler_penalty(text: str) -> float:
    filler_hits = count_signal_hits(text, GENERIC_COMMERCIAL_FILLER_PATTERNS)
    anchor_density = concrete_business_anchor_density(text)
    chain_overrender = count_pattern_occurrences(text, CHAIN_LITERALIZATION_PATTERNS)
    contract_overrender = count_pattern_occurrences(text, CONTRACT_SPILLOVER_PATTERNS)
    proof_repetition = count_pattern_occurrences(
        text,
        (
            r"proof_artifact_for_continue",
            r"decision_trigger",
            r"continuation_signal",
            r"review summary",
            r"决策触发器",
            r"继续信号",
            r"复盘摘要",
        ),
    )
    penalty = 0.0
    if filler_hits >= 5 and anchor_density <= 1:
        penalty += 2.0
    elif filler_hits >= 3 and anchor_density <= 1:
        penalty += 1.2
    elif filler_hits >= 2 and anchor_density == 0:
        penalty += 0.6
    if chain_overrender >= 2:
        penalty += 1.6
    elif chain_overrender >= 1:
        penalty += 0.8
    if contract_overrender >= 3:
        penalty += 1.0
    elif contract_overrender >= 2:
        penalty += 0.5
    if proof_repetition >= 8:
        penalty += 0.8
    elif proof_repetition >= 6:
        penalty += 0.4
    return penalty


VALUE_SIGNAL_REGISTRY_COLUMNS = (
    "value_signal_id",
    "upstream_trace_id",
    "business_value_weight",
    "business_value_reason",
    "anti_demo_risk",
    "core_success_path",
    "downstream_depth_hint",
    "evidence_or_review_bound",
)


def business_value_signal_registry_findings(text: str) -> tuple[list[str], list[str]]:
    matched: list[str] = []
    missing: list[str] = []
    if not re.search(r"Business Value Signal Registry|business_value_signal_registry", text, flags=re.IGNORECASE):
        return matched, ["business_value_signal_registry"]
    registry_block = extract_h2_block(text, r"(?:14\.\s+)?.*Business Value Signal Registry") or text
    lowered = registry_block.casefold()
    for column in VALUE_SIGNAL_REGISTRY_COLUMNS:
        if column.casefold() in lowered:
            matched.append(column)
        else:
            missing.append(column)
    if re.search(r"\bBVS-\d{3}\b", registry_block):
        matched.append("stable_value_signal_id")
    else:
        missing.append("business_value_signal_id_missing")
    if re.search(r"\bP1-(?:UC|REQ|AC)-\d{3}\b", registry_block):
        matched.append("business_value_signal_trace_binding")
    elif "review-bound" in lowered:
        matched.append("business_value_signal_review_bound")
    else:
        missing.append("business_value_signal_trace_binding_missing")
    if re.search(r"\bBV[0-3]\b", registry_block):
        matched.append("business_value_weight")
    else:
        missing.append("business_value_weight_missing")
    return matched, missing


def product_source_driver_business_findings(text: str) -> tuple[list[str], list[str], list[str]]:
    driver_checks = {
        "driver_backed_product_judgment": r"driver_product_judgment\s*:",
        "driver_backed_commercial_judgment": r"driver_commercial_judgment\s*:",
        "driver_backed_business_feasibility": r"driver_business_feasibility\s*:",
        "driver_backed_mvp_wedge": r"driver_mvp_wedge\s*:",
        "driver_backed_acceptance_meaning": r"driver_acceptance_meaning\s*:",
        "driver_forbidden_downstream_assumptions": r"driver_forbidden_downstream_assumptions\s*:",
    }
    matched: list[str] = []
    missing: list[str] = []
    for label, pattern in driver_checks.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            matched.append(label)
        else:
            missing.append(label)
    notes = ["driver_findings=evidence-only"] if matched else []
    return matched, missing, notes


def driver_source_truth_confidence(text: str) -> str:
    match = re.search(
        r"driver_source_truth_confidence\s*:\s*([A-Za-z0-9/_ -]+)",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip().lower() if match else ""


def fake_driver_confidence_upgrade_risk(text: str) -> bool:
    driver_state = driver_source_truth_confidence(text)
    if not driver_state or "review-bound" not in driver_state:
        return False
    return bool(
        re.search(
            r"validated market truth|real owner approval|owner sign-?off complete|market validation complete|budget confirmation",
            text,
            flags=re.IGNORECASE,
        )
    )


def build_business_semantic_profile(text: str) -> BusinessSemanticProfile:
    keyword_matched, keyword_missing = match_labels(text, BUSINESS_SIGNALS)
    commercial_sharpness = score_commercial_sharpness_surface(text)
    alternative_specificity = score_alternative_specificity_surface(text)
    source_semantic_retention = score_source_semantic_retention_surface(text)
    semantic_compression = score_semantic_compression_surface(text)
    adversarial_review = score_adversarial_review_surface(text)
    assembler_filler_penalty = score_assembler_filler_penalty(text)
    critical_missing: list[str] = []
    if commercial_sharpness < 2:
        critical_missing.append("commercial_sharpness")
    if alternative_specificity < 1:
        critical_missing.append("alternative_specificity")
    if source_semantic_retention < 1:
        critical_missing.append("source_semantic_retention")
    if semantic_compression < 1:
        critical_missing.append("semantic_compression")
    if adversarial_review < 3:
        critical_missing.append("adversarial_review")
    if assembler_filler_penalty > 0:
        critical_missing.append("assembler_filler_penalty")
    notes = [
        f"keyword_signals={len(keyword_matched)}/{len(BUSINESS_SIGNALS)}",
        f"commercial_sharpness={commercial_sharpness}/3",
        f"alternative_specificity={alternative_specificity}/2",
        f"source_semantic_retention={source_semantic_retention}/2",
        f"semantic_compression={semantic_compression}/2",
        f"adversarial_review={adversarial_review}/4",
        f"assembler_filler_penalty={assembler_filler_penalty:.1f}",
    ]
    return BusinessSemanticProfile(
        keyword_matched=keyword_matched,
        keyword_missing=keyword_missing,
        commercial_sharpness=commercial_sharpness,
        alternative_specificity=alternative_specificity,
        source_semantic_retention=source_semantic_retention,
        semantic_compression=semantic_compression,
        adversarial_review=adversarial_review,
        assembler_filler_penalty=assembler_filler_penalty,
        critical_missing=critical_missing,
        notes=notes,
    )


def score_business_value(text: str) -> DimensionResult:
    combined = "\n\n".join(
        [
            extract_h2_block(text, r"(?:1\.\s+)?Executive Summary"),
            extract_h2_block(text, CORE_H2_PATTERNS["problem"]),
            extract_h2_block(text, CORE_H2_PATTERNS["users"]),
            extract_h2_block(text, r"(?:5\.\s+)?Strategic Context"),
            extract_h2_block(text, r"(?:6\.\s+)?Product Direction Overview"),
            extract_h2_block(text, CORE_H2_PATTERNS["validation"]),
            extract_h2_block(text, CORE_H2_PATTERNS["risks"]),
        ]
    )
    profile = build_business_semantic_profile(combined)
    keyword_component = ratio_score(min(len(profile.keyword_matched), 6), 6, 2.5)
    commercial_component = round((profile.commercial_sharpness / 3.0) * 3.0, 1)
    alternative_component = round((profile.alternative_specificity / 2.0) * 2.0, 1)
    retention_component = round((profile.source_semantic_retention / 2.0) * 1.5, 1)
    compression_component = round((profile.semantic_compression / 2.0) * 1.0, 1)
    adversarial_component = round((profile.adversarial_review / 4.0) * 2.0, 1)
    raw_score = (
        keyword_component
        + commercial_component
        + alternative_component
        + retention_component
        + compression_component
        + adversarial_component
    )
    score = max(0.0, min(12.0, round(raw_score - profile.assembler_filler_penalty, 1)))
    matched = list(profile.keyword_matched)
    missing = list(profile.keyword_missing)
    surface_checks = {
        "commercial_sharpness": profile.commercial_sharpness >= 2,
        "alternative_specificity": profile.alternative_specificity >= 1,
        "source_semantic_retention": profile.source_semantic_retention >= 1,
        "semantic_compression": profile.semantic_compression >= 1,
        "adversarial_review": profile.adversarial_review >= 3,
    }
    for label, ok in surface_checks.items():
        if ok:
            matched.append(label)
        else:
            missing.append(label)
    if profile.assembler_filler_penalty > 0:
        missing.append("assembler_filler_penalty")
    else:
        matched.append("assembler_filler_penalty")
    registry_matched, registry_missing = business_value_signal_registry_findings(text)
    matched.extend(registry_matched)
    missing.extend(registry_missing)
    driver_matched, driver_missing, driver_notes = product_source_driver_business_findings(text)
    matched.extend(driver_matched)
    missing.extend(driver_missing)
    notes = list(profile.notes)
    notes.extend(driver_notes)
    notes.extend(
        [
            f"keyword_component={keyword_component:.1f}/2.5",
            f"commercial_component={commercial_component:.1f}/3.0",
            f"alternative_component={alternative_component:.1f}/2.0",
            f"retention_component={retention_component:.1f}/1.5",
            f"compression_component={compression_component:.1f}/1.0",
            f"adversarial_component={adversarial_component:.1f}/2.0",
            f"raw_before_penalty={raw_score:.1f}/12.0",
        ]
    )
    critical_missing = list(profile.critical_missing)
    critical_missing.extend(
        item
        for item in registry_missing
        if item in {
            "business_value_signal_registry",
            "business_value_signal_id_missing",
            "business_value_signal_trace_binding_missing",
            "business_value_weight_missing",
        }
    )
    if critical_missing:
        notes.append(f"critical_missing={', '.join(critical_missing)}")
    return DimensionResult(
        "business_value_and_commercial_logic",
        score,
        12.0,
        matched,
        missing,
        notes,
    )


def score_user_insight(text: str) -> DimensionResult:
    combined = "\n\n".join(
        [
            combined_section_text(text, ("users", "scenarios", "requirements", "requirements_translation")),
            extract_h2_block(text, r"(?:4\.\s+)?Stakeholder Analysis"),
        ]
    )
    return score_signal_dimension(
        "user_and_operating_insight",
        combined,
        USER_INSIGHT_SIGNALS,
        10.0,
    )


def score_validation_discipline(text: str) -> DimensionResult:
    combined = "\n\n".join(
        [
            extract_h2_block(text, CORE_H2_PATTERNS["validation"]),
            extract_h2_block(text, CORE_H2_PATTERNS["risks"]),
            extract_h2_block(text, r"(?:19\.\s+)?Acceptance\s*&\s*Status"),
        ]
    )
    return score_signal_dimension(
        "validation_and_risk_discipline",
        combined,
        VALIDATION_SIGNALS,
        10.0,
    )


def extract_named_state(text: str, field: str) -> str | None:
    localized = extract_localized_named_state(text, field)
    if localized:
        normalized = normalize_state_token(localized)
        if normalized:
            return normalized
        return localized.strip().lower()
    match = re.search(
        rf"{re.escape(field)}:\s*(?:\n\s*-\s*`?([^`\n]+)`?)?",
        text,
        flags=re.IGNORECASE,
    )
    if not match or not match.group(1):
        return None
    normalized = normalize_state_token(match.group(1))
    if normalized:
        return normalized
    return match.group(1).strip().lower()


def extract_named_state_strict(text: str, field: str) -> str | None:
    localized = extract_localized_named_state(text, field)
    if not localized:
        return None
    normalized = normalize_state_token(localized)
    if normalized:
        return normalized
    return localized.strip().lower()


def infer_delivery_state_cap(text: str) -> tuple[float, str]:
    explicit = extract_named_state(text, "document_delivery_state")
    if explicit == "implementation-commit-ready":
        return 6.0, explicit
    if explicit == "downstream-start-safe":
        return 5.2, explicit
    if explicit == "review-ready":
        return 3.8, explicit
    if explicit == "artifact-draft":
        return 1.8, explicit
    if explicit == "blocked":
        return 0.0, explicit
    if re.search(r"Design Can Start", text, flags=re.IGNORECASE) and re.search(
        r"Architecture Can Start", text, flags=re.IGNORECASE
    ):
        return 4.6, "implicit-downstream-start-safe"
    if re.search(r"ready-to-converge|review-ready", text, flags=re.IGNORECASE):
        return 3.4, "implicit-review-ready"
    if re.search(r"review-bound", text, flags=re.IGNORECASE):
        return 2.6, "review-bound-without-explicit-delivery-state"
    return 1.2, "delivery-state-not-explicit"


def infer_evidence_state_cap(text: str) -> tuple[float, str]:
    explicit = extract_named_state_strict(text, "evidence_confidence_state") or extract_named_state(
        text, "evidence_confidence_state"
    )
    if explicit == "externally-validated":
        return 4.0, explicit
    if explicit == "partially-signal-backed":
        return 3.2, explicit
    if explicit == "source-grounded-but-unvalidated":
        return 2.6, explicit
    if explicit == "design-time-inference-heavy":
        return 1.8, explicit
    if explicit == "contradicted":
        return 1.0, explicit
    if re.search(r"externally-validated", text, flags=re.IGNORECASE):
        return 4.0, "implicit-externally-validated"
    if re.search(r"partially-signal-backed|partially-validated", text, flags=re.IGNORECASE):
        return 3.0, "implicit-partially-signal-backed"
    if re.search(r"source-grounded-but-unvalidated|review-bound", text, flags=re.IGNORECASE):
        return 2.4, "implicit-source-grounded-but-unvalidated"
    if re.search(r"design-time inference|not-tested", text, flags=re.IGNORECASE):
        return 1.8, "implicit-design-time-inference-heavy"
    return 1.2, "evidence-state-not-explicit"


def score_delivery_readiness(text: str) -> DimensionResult:
    acceptance = extract_h2_block(text, r"(?:19\.\s+)?Acceptance\s*&\s*Status")
    combined = "\n\n".join(
        [
            extract_h2_block(text, CORE_H2_PATTERNS["mvp"]),
            extract_h2_block(text, CORE_H2_PATTERNS["validation"]),
            extract_h2_block(text, CORE_H2_PATTERNS["risks"]),
            extract_h2_block(text, CORE_H2_PATTERNS["handoff"]),
            acceptance,
        ]
    )
    matched, missing = match_labels(combined, DELIVERY_READINESS_SIGNALS)
    raw_score = ratio_score(len(matched), len(DELIVERY_READINESS_SIGNALS), 6.0)
    explicit_acceptance_state = extract_named_state_strict(acceptance, "document_delivery_state")
    if explicit_acceptance_state == "implementation-commit-ready":
        cap, state = 6.0, "acceptance:implementation-commit-ready"
    elif explicit_acceptance_state == "downstream-start-safe":
        cap, state = 5.2, "acceptance:downstream-start-safe"
    elif explicit_acceptance_state == "review-ready":
        cap, state = 3.8, "acceptance:review-ready"
    elif explicit_acceptance_state == "artifact-draft":
        cap, state = 1.8, "acceptance:artifact-draft"
    elif explicit_acceptance_state == "blocked":
        cap, state = 0.0, "acceptance:blocked"
    else:
        cap, state = infer_delivery_state_cap(combined)
    score = round(min(raw_score, cap), 1)
    notes = [
        f"matched={len(matched)}/{len(DELIVERY_READINESS_SIGNALS)}",
        f"state={state}",
        f"cap={cap}",
        f"raw={raw_score}",
    ]
    return DimensionResult("delivery_readiness_maturity", score, 6.0, matched, missing, notes)


def score_evidence_confidence(text: str) -> DimensionResult:
    combined = "\n\n".join(
        [
            extract_h2_block(text, CORE_H2_PATTERNS["validation"]),
            extract_h2_block(text, CORE_H2_PATTERNS["risks"]),
            extract_h2_block(text, r"(?:19\.\s+)?Acceptance\s*&\s*Status"),
        ]
    )
    matched, missing = match_labels(combined, EVIDENCE_CONFIDENCE_SIGNALS)
    raw_score = ratio_score(len(matched), len(EVIDENCE_CONFIDENCE_SIGNALS), 4.0)
    cap, state = infer_evidence_state_cap(combined)
    score = round(min(raw_score, cap), 1)
    driver_state = driver_source_truth_confidence(text)
    if driver_state:
        notes_driver_state = f"driver_source_truth_confidence={driver_state}"
    else:
        notes_driver_state = ""
    if fake_driver_confidence_upgrade_risk(text):
        missing.append("fake_confidence_upgrade_risk")
    notes = [
        f"matched={len(matched)}/{len(EVIDENCE_CONFIDENCE_SIGNALS)}",
        f"state={state}",
        f"cap={cap}",
        f"raw={raw_score}",
    ]
    if notes_driver_state:
        notes.append(notes_driver_state)
    return DimensionResult("evidence_confidence_posture", score, 4.0, matched, missing, notes)


def score_document_maturity_lens(text: str, dimension_results: list[DimensionResult]) -> LensResult:
    selected = [item for item in dimension_results if item.name in DOCUMENT_MATURITY_DIMENSIONS]
    achieved = sum(item.score for item in selected)
    maximum = sum(item.max_score for item in selected)
    base = 0.0 if maximum <= 0 else (achieved / maximum) * 96.0
    warning_block = extract_h2_block(text, r"(?:19\.\s+)?Acceptance\s*&\s*Status")
    matched, missing = match_labels(warning_block, WARNING_CONFIRMATION_SIGNALS)
    warning_bonus = ratio_score(len(matched), len(WARNING_CONFIRMATION_SIGNALS), 4.0)
    notes = [
        f"base_dimension_score={achieved:.1f}/{maximum:.1f}",
        f"warning_signals={len(matched)}/{len(WARNING_CONFIRMATION_SIGNALS)}",
    ]
    return LensResult(
        "document_maturity_score",
        round(base + warning_bonus, 1),
        notes + ([f"missing_warning_signals={', '.join(missing)}"] if missing else []),
    )


def ledger_business_completeness_ratio(text: str) -> tuple[float, list[str]]:
    block = extract_h3_block(text, r"Maturity\s*&\s*Confidence Ledger")
    rows = parse_markdown_table(block)
    if not rows:
        return 0.0, ["maturity_ledger=missing"]

    weighted_total = 0.0
    total_weight = 0.0
    notes = [f"maturity_ledger_rows={len(rows)}"]
    for row in rows:
        raw_delivery_state = row.get("delivery_readiness_state", "")
        raw_evidence_state = row.get("evidence_confidence_state", "")
        delivery_state = (
            normalize_state_token(raw_delivery_state, set(DELIVERY_COMPLETENESS_STATES))
            or str(raw_delivery_state).strip().lower()
        )
        evidence_state = (
            normalize_state_token(raw_evidence_state, set(EVIDENCE_COMPLETENESS_STATES))
            or str(raw_evidence_state).strip().lower()
        )
        delivery_ratio = DELIVERY_COMPLETENESS_STATES.get(delivery_state, 0.35)
        evidence_ratio = EVIDENCE_COMPLETENESS_STATES.get(evidence_state, 0.35)
        row_ratio = 0.45 * delivery_ratio + 0.55 * evidence_ratio
        weight = 0.7 if delivery_state == "blocked" else 1.0
        weighted_total += row_ratio * weight
        total_weight += weight

    if total_weight <= 0:
        return 0.0, notes + ["maturity_ledger_weight=0"]
    return weighted_total / total_weight, notes


def score_business_completeness_lens(text: str, dimension_results: list[DimensionResult]) -> LensResult:
    dimension_map = {item.name: item for item in dimension_results}
    delivery = dimension_map["delivery_readiness_maturity"]
    evidence = dimension_map["evidence_confidence_posture"]
    business = dimension_map["business_value_and_commercial_logic"]
    reasoning = dimension_map["reasoning_and_tradeoff_depth"]
    validation = dimension_map["validation_and_risk_discipline"]
    handoff = dimension_map["handoff_readiness"]
    coherence = dimension_map["coherence_and_non_template_quality"]

    delivery_component = (delivery.score / delivery.max_score) * 16.0 if delivery.max_score else 0.0
    evidence_component = (evidence.score / evidence.max_score) * 12.0 if evidence.max_score else 0.0
    ledger_ratio, ledger_notes = ledger_business_completeness_ratio(text)
    ledger_component = ledger_ratio * 10.0
    reasoning_component = (reasoning.score / reasoning.max_score) * 18.0 if reasoning.max_score else 0.0
    business_component = (business.score / business.max_score) * 30.0 if business.max_score else 0.0
    validation_component = (validation.score / validation.max_score) * 8.0 if validation.max_score else 0.0
    handoff_component = (handoff.score / handoff.max_score) * 3.0 if handoff.max_score else 0.0
    coherence_component = (coherence.score / coherence.max_score) * 3.0 if coherence.max_score else 0.0
    score = round(
        delivery_component
        + evidence_component
        + ledger_component
        + reasoning_component
        + business_component
        + validation_component
        + handoff_component
        + coherence_component,
        1,
    )
    notes = [
        f"delivery_component={delivery_component:.1f}/16.0",
        f"evidence_component={evidence_component:.1f}/12.0",
        f"ledger_component={ledger_component:.1f}/10.0",
        f"reasoning_component={reasoning_component:.1f}/18.0",
        f"business_component={business_component:.1f}/30.0",
        f"validation_component={validation_component:.1f}/8.0",
        f"handoff_component={handoff_component:.1f}/3.0",
        f"coherence_component={coherence_component:.1f}/3.0",
        *ledger_notes,
    ]
    if any("critical_missing=" in note for note in business.notes):
        notes.extend(note for note in business.notes if note.startswith("critical_missing="))
    return LensResult("business_completeness_score", score, notes)


def build_lens_results(text: str, dimension_results: list[DimensionResult]) -> list[LensResult]:
    return [
        score_document_maturity_lens(text, dimension_results),
        score_business_completeness_lens(text, dimension_results),
    ]


def infer_version(path: Path) -> str:
    match = re.search(r"(trial-v\d+|v\d+)", str(path), flags=re.IGNORECASE)
    if not match:
        return path.parent.name
    value = match.group(1).lower()
    return value if value.startswith("trial-") else f"trial-{value}"


def tier_for_score(score: float) -> str:
    if score < 45:
        return "thin-draft"
    if score < 60:
        return "structured-but-thin"
    if score < 75:
        return "starter-prd"
    if score < 85:
        return "strong-review-bound-prd"
    if score < 92:
        return "high-quality-review-bound-prd"
    return "excellent-prd-candidate"


def score_prd(path: Path) -> ScoreResult:
    text = read_text(path)
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    chars = len(text)
    duplicate_ratio, _ = duplicate_line_ratio(text)

    dimension_results = [
        score_completeness(text),
        score_detail_richness(text),
        score_signal_dimension(
            "reasoning_and_tradeoff_depth",
            "\n\n".join(
                [
                    extract_h2_block(text, CORE_H2_PATTERNS["problem"]),
                    extract_h2_block(text, CORE_H2_PATTERNS["requirements"]),
                    extract_h2_block(text, CORE_H2_PATTERNS["mvp"]),
                    extract_h2_block(text, CORE_H2_PATTERNS["validation"]),
                    extract_h2_block(text, r"(?:17\.\s+)?Key Decision Rationale Summary"),
                ]
            ),
            REASONING_SIGNALS,
            12.0,
        ),
        score_business_value(text),
        score_user_insight(text),
        score_executability(text),
        score_validation_discipline(text),
        score_handoff(text),
        score_coherence(text),
        score_delivery_readiness(text),
        score_evidence_confidence(text),
    ]
    lens_results = build_lens_results(text, dimension_results)
    total = round(sum(item.score for item in dimension_results), 1)
    return ScoreResult(
        version=infer_version(path),
        prd_path=str(path),
        lines=lines,
        chars=chars,
        duplicate_line_ratio=duplicate_ratio,
        dimension_results=dimension_results,
        lens_results=lens_results,
        total_score=total,
        tier=tier_for_score(total),
    )


def version_sort_key(result: ScoreResult) -> tuple[int, str]:
    match = re.search(r"v(\d+)", result.version, flags=re.IGNORECASE)
    return (int(match.group(1)) if match else math.inf, result.version)


def build_summary(results: list[ScoreResult]) -> dict[str, object]:
    if not results:
        return {
            "best_versions": [],
            "worst_version": None,
            "most_improved_pair": None,
            "latest_version": None,
            "persistent_low_dimensions": [],
            "persistent_low_lenses": [],
        }

    sorted_results = sorted(results, key=version_sort_key)
    best_score = max(item.total_score for item in sorted_results)
    best_versions = [item.version for item in sorted_results if item.total_score == best_score]
    worst = min(sorted_results, key=lambda item: item.total_score)
    deltas = []
    for prev, curr in zip(sorted_results, sorted_results[1:]):
        deltas.append(
            {
                "from": prev.version,
                "to": curr.version,
                "delta": round(curr.total_score - prev.total_score, 1),
            }
        )
    most_improved = max(deltas, key=lambda item: item["delta"]) if deltas else None

    latest = sorted_results[-1]
    dimension_history: dict[str, list[float]] = {}
    dimension_max: dict[str, float] = {}
    for result in sorted_results:
        for item in result.dimension_results:
            dimension_history.setdefault(item.name, []).append(item.score)
            dimension_max[item.name] = item.max_score

    persistent_low = [
        {
            "dimension": name,
            "avg_score": round(statistics.mean(values), 1),
            "latest_score": round(next(item.score for item in latest.dimension_results if item.name == name), 1),
        }
        for name, values in dimension_history.items()
        if statistics.mean(values) < dimension_max[name] * 0.65
        or next(item.score for item in latest.dimension_results if item.name == name) < dimension_max[name] * 0.8
    ]
    persistent_low.sort(key=lambda item: (item["latest_score"], item["avg_score"]))

    lens_history: dict[str, list[float]] = {}
    for result in sorted_results:
        for item in result.lens_results:
            lens_history.setdefault(item.name, []).append(item.score)

    persistent_low_lenses = [
        {
            "lens": name,
            "avg_score": round(statistics.mean(values), 1),
            "latest_score": round(next(item.score for item in latest.lens_results if item.name == name), 1),
        }
        for name, values in lens_history.items()
        if statistics.mean(values) < 85.0
        or next(item.score for item in latest.lens_results if item.name == name) < 90.0
    ]
    persistent_low_lenses.sort(key=lambda item: (item["latest_score"], item["avg_score"]))

    latest_lenses = {
        item.name: item.score
        for item in latest.lens_results
    }

    return {
        "best_versions": {"versions": best_versions, "score": best_score},
        "worst_version": {"version": worst.version, "score": worst.total_score},
        "most_improved_pair": most_improved,
        "latest_version": {
            "version": latest.version,
            "score": latest.total_score,
            "tier": latest.tier,
            "document_maturity_score": latest_lenses.get("document_maturity_score"),
            "business_completeness_score": latest_lenses.get("business_completeness_score"),
        },
        "persistent_low_dimensions": persistent_low[:5],
        "persistent_low_lenses": persistent_low_lenses[:3],
    }


def markdown_report(results: list[ScoreResult], summary: dict[str, object]) -> str:
    lines = [
        "# Phase-1 PRD Excellence Regression",
        "",
        "## 1. Scoring Standard",
        "- target bar: excellent, complete, downstream-usable PRD rather than internal gate-only pass/fail",
        "- scoring stance: intentionally stricter and more externalized than current convergence gates",
        "- semantic guardrail: commercial keywords alone do not count as sharp business judgment",
        "- adversarial guardrail: scorer now checks whether the PRD explicitly answers competitor/substitute pressure, why-not-dashboard, proof-for-continue, and why unresolved truth remains review-bound",
        "- dual reading lenses:",
        "  - `document_maturity_score`: under current inputs, how complete/mature the PRD artifact itself is",
        "  - `business_completeness_score`: against an ideal business-case template, how much truth/evidence/commercial completeness is still missing",
        "- dimensions:",
        "  - structural completeness /8",
        "  - detail richness /12",
        "  - reasoning and trade-off depth /12",
        "  - business value and commercial logic /12",
        "  - user and operating insight /10",
        "  - workflow and specification executability /14",
        "  - validation and risk discipline /10",
        "  - handoff readiness /7",
        "  - coherence and non-template quality /5",
        "  - delivery readiness maturity /6",
        "  - evidence confidence posture /4",
        "",
        "## 2. Historical Score Table",
        "",
        "| Version | Total | Tier | Doc Maturity | Business Completeness | Lines | structural | detail | reasoning | business | user | executability | validation | handoff | coherence | delivery | evidence |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in sorted(results, key=version_sort_key):
        scores = {item.name: item.score for item in result.dimension_results}
        lenses = {item.name: item.score for item in result.lens_results}
        lines.append(
            f"| {result.version} | {result.total_score:.1f} | {result.tier} | "
            f"{lenses.get('document_maturity_score', 0.0):.1f} | "
            f"{lenses.get('business_completeness_score', 0.0):.1f} | "
            f"{result.lines} | "
            f"{scores['structural_completeness']:.1f} | "
            f"{scores['detail_richness']:.1f} | "
            f"{scores['reasoning_and_tradeoff_depth']:.1f} | "
            f"{scores['business_value_and_commercial_logic']:.1f} | "
            f"{scores['user_and_operating_insight']:.1f} | "
            f"{scores['workflow_and_spec_executability']:.1f} | "
            f"{scores['validation_and_risk_discipline']:.1f} | "
            f"{scores['handoff_readiness']:.1f} | "
            f"{scores['coherence_and_non_template_quality']:.1f} | "
            f"{scores['delivery_readiness_maturity']:.1f} | "
            f"{scores['evidence_confidence_posture']:.1f} |"
        )

    lines.extend(["", "## 3. Summary"])
    best = summary.get("best_versions")
    worst = summary.get("worst_version")
    improved = summary.get("most_improved_pair")
    latest = summary.get("latest_version")
    if best:
        versions = ", ".join(f"`{item}`" for item in best["versions"])
        lines.append(f"- best version(s): {versions} at `{best['score']}`")
    if worst:
        lines.append(f"- weakest version: `{worst['version']}` at `{worst['score']}`")
    if improved:
        lines.append(f"- biggest jump: `{improved['from']}` -> `{improved['to']}` (`+{improved['delta']}`)")
    if latest:
        lines.append(
            f"- latest benchmark: `{latest['version']}` = `{latest['score']}` (`{latest['tier']}`)"
        )
        lines.append(
            "- latest dual-lens read: "
            f"`document_maturity_score={latest.get('document_maturity_score')}`; "
            f"`business_completeness_score={latest.get('business_completeness_score')}`"
        )

    lines.extend(["", "## 4. Persistent Weak Dimensions"])
    low_dimensions = summary.get("persistent_low_dimensions", [])
    if not low_dimensions:
        lines.append("- none")
    else:
        for item in low_dimensions:
            lines.append(
                f"- `{item['dimension']}`: avg=`{item['avg_score']}`, latest=`{item['latest_score']}`"
            )

    lines.extend(["", "## 5. Persistent Weak Lenses"])
    low_lenses = summary.get("persistent_low_lenses", [])
    if not low_lenses:
        lines.append("- none")
    else:
        for item in low_lenses:
            lines.append(
                f"- `{item['lens']}`: avg=`{item['avg_score']}`, latest=`{item['latest_score']}`"
            )

    lines.extend(["", "## 6. Latest Version Gaps"])
    latest_result = sorted(results, key=version_sort_key)[-1]
    for dimension in latest_result.dimension_results:
        if dimension.missing:
            lines.append(
                f"- `{dimension.name}` missing signals: {', '.join(dimension.missing[:6])}"
            )
        if dimension.name == "business_value_and_commercial_logic":
            critical_notes = [note for note in dimension.notes if note.startswith("critical_missing=")]
            if critical_notes:
                lines.append(f"- `{dimension.name}` critical gaps: {critical_notes[0].split('=', 1)[1]}")
    for lens in latest_result.lens_results:
        if lens.notes:
            lines.append(f"- `{lens.name}` notes: {'; '.join(lens.notes[:3])}")

    lines.extend(["", "## 7. Version Notes"])
    for result in sorted(results, key=version_sort_key):
        weakest = sorted(result.dimension_results, key=lambda item: item.score / item.max_score)[:3]
        strongest = sorted(result.dimension_results, key=lambda item: item.score / item.max_score, reverse=True)[:2]
        lens_map = {item.name: item.score for item in result.lens_results}
        lines.append(f"### {result.version}")
        lines.append(f"- total: `{result.total_score}` / 100")
        lines.append(f"- tier: `{result.tier}`")
        lines.append(
            f"- dual-lens: `document_maturity_score={lens_map.get('document_maturity_score')}`; "
            f"`business_completeness_score={lens_map.get('business_completeness_score')}`"
        )
        lines.append(
            "- strongest dimensions: "
            + ", ".join(f"`{item.name}` ({item.score}/{item.max_score})" for item in strongest)
        )
        lines.append(
            "- weakest dimensions: "
            + ", ".join(f"`{item.name}` ({item.score}/{item.max_score})" for item in weakest)
        )
        lines.append(f"- duplicate_line_ratio: `{result.duplicate_line_ratio:.3f}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Externalized PRD excellence regression")
    parser.add_argument("--prd", action="append", default=[])
    parser.add_argument("--trial-root")
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    args = parser.parse_args()

    prd_paths: list[Path] = []
    if args.trial_root:
        trial_root = Path(args.trial_root).resolve()
        prd_paths.extend(sorted(trial_root.glob("*/geo-rpd-main-document.md")))
    prd_paths.extend(Path(item).resolve() for item in args.prd)

    seen: set[Path] = set()
    unique_paths: list[Path] = []
    for path in prd_paths:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        unique_paths.append(path)

    if not unique_paths:
        print("[BLOCKED] no PRD files found")
        return 2

    results = [score_prd(path) for path in unique_paths]
    results.sort(key=version_sort_key)
    summary = build_summary(results)

    payload = {
        "summary": summary,
        "results": [
            {
                "version": result.version,
                "prd_path": result.prd_path,
                "lines": result.lines,
                "chars": result.chars,
                "duplicate_line_ratio": round(result.duplicate_line_ratio, 4),
                "total_score": result.total_score,
                "tier": result.tier,
                "lenses": [
                    {
                        "name": item.name,
                        "score": item.score,
                        "notes": item.notes,
                    }
                    for item in result.lens_results
                ],
                "dimensions": [
                    {
                        "name": item.name,
                        "score": item.score,
                        "max_score": item.max_score,
                        "matched": item.matched,
                        "missing": item.missing,
                        "notes": item.notes,
                    }
                    for item in result.dimension_results
                ],
            }
            for result in results
        ],
    }

    if args.output_json:
        output_json = Path(args.output_json).resolve()
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.output_md:
        output_md = Path(args.output_md).resolve()
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(markdown_report(results, summary), encoding="utf-8")

    print("== Phase-1 PRD Excellence Regression ==")
    for result in results:
        print(f"{result.version}: total={result.total_score} tier={result.tier}")
        for lens in result.lens_results:
            print(f"  - {lens.name}: {lens.score}/100")
        for item in result.dimension_results:
            print(f"  - {item.name}: {item.score}/{item.max_score}")
    if summary.get("most_improved_pair"):
        improved = summary["most_improved_pair"]
        print(f"largest_jump: {improved['from']} -> {improved['to']} (+{improved['delta']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
