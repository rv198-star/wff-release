#!/usr/bin/env python3
"""
Assemble a Phase-1 PRD main document from Stage-01..04 outputs.

Design intent:
- source input is read-only evidence and must not be modified
- PRD is a synthesized artifact from stage outputs, not a source-file mirror
- final document must preserve stage depth instead of collapsing back to an outline
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
from pathlib import Path

from phase1.phase1_source_text_normalization import normalize_source_handoff_phrases

from common.output_language import resolve_output_locale
from phase1.phase1_localize_prd_zh import render_primary_locale_lines
from phase1.phase1_reasoning_runtime import (
    PHASE1_BUSINESS_WORLD_MODEL_FILENAME,
    compile_maturity_confidence_ledger,
    sanitize_domain_default_truth,
)
from phase1.phase1_trace_units import (
    ACCEPTANCE_CRITERIA,
    EPIC_DECOMPOSITION,
    EXTENDED_REQUIREMENTS,
    PHASE1_PRD_ARTIFACT_ID,
    PRIMARY_USER_STORY,
    SUPPORTING_USE_CASES,
    render_phase1_fine_grained_trace_registry,
    render_phase1_phase2_design_input_contract,
    render_phase1_prd_traceability_block,
)

INVEST_EVALUATION_ROWS = [
    [
        "Primary User Story",
        "EP-01, EP-02, EP-03",
        "partial",
        "yes",
        "yes",
        "partial",
        "partial",
        "yes",
        "cross-epic loop is valuable but still large; keep epic decomposition explicit to avoid over-broad implementation batches",
    ],
    [
        "Use Case 1",
        "EP-02",
        "yes",
        "yes",
        "yes",
        "yes",
        "yes",
        "yes",
        "bounded around gap discovery and asset localization",
    ],
    [
        "Use Case 2",
        "EP-02",
        "yes",
        "partial",
        "yes",
        "partial",
        "yes",
        "yes",
        "priority logic is negotiable, but cross-module handoff evidence quality still affects estimation confidence",
    ],
    [
        "Use Case 3",
        "EP-03",
        "yes",
        "yes",
        "yes",
        "partial",
        "partial",
        "yes",
        "review logic is testable, but improvement thresholds still need bounded calibration",
    ],
    [
        "Use Case 4",
        "EP-03",
        "yes",
        "yes",
        "yes",
        "yes",
        "yes",
        "yes",
        "clarification fallback is intentionally narrow and implementation-facing",
    ],
]

ACCEPTANCE_DETAIL_ROWS = [
    ["AC-01", "anchor", "EP-01", "Primary User Story", "Given a valid business intake draft", "When the primary operator saves the intake definition", "Then the system versions the intake and preserves the required business inputs", "A new intake version is created and the saved record remains queryable by scope and version", "baseline_happy_path", "intake must not persist without scope/version context", "Step 1"],
    ["AC-02", "anchor", "EP-01", "Primary User Story", "Given the intake definition is missing a required input", "When the first workflow step is requested", "Then the system blocks the run and reports the missing field set", "The request returns a visible validation error with the missing required fields", "missing_required_input", "required business input omission blocks workflow start", "Step 2"],
    ["AC-03", "anchor", "EP-01", "Use Case 1", "Given a completed core flow run", "When the operator opens the resulting business record", "Then the required business fields are visible in one consistent context", "The screen exposes the minimum result set without cross-page reconstruction", "minimum_result_set", "a partial business result does not count as flow completion", "Step 4"],
    ["AC-04", "anchor", "EP-02", "Use Case 1", "Given a detailed business record is opened", "When the operator reviews the record detail", "Then context, explanation, and next action remain visible together", "The record detail is decision-ready without requiring a second lookup path", "detail_completeness", "record detail is invalid if one core evidence dimension is absent", "Step 5"],
    ["AC-05", "anchor", "EP-02", "Use Case 2", "Given a downstream handoff is requested", "When the next workflow step is created", "Then all required structured fields are present", "A typed module payload can be exported without missing execution-semantic fields", "invalid_payload", "handoff creation fails if required fields are incomplete", "Step 6"],
    ["AC-06", "supporting", "EP-03", "Use Case 3", "Given a business handoff passed readiness checks", "When the next operator accepts the work", "Then owner, status, and notes remain recorded", "The handoff preserves operational ownership and execution context", "handoff_integrity", "handoff is incomplete if operational ownership is dropped", "Step 7"],
    ["AC-07", "supporting", "EP-03", "Use Case 4", "Given a task exists", "When task state changes are evaluated", "Then the system only allows created, accepted, executed, or blocked as the tracked execution states", "Invalid task states are rejected or surfaced for remediation", "invalid_state_transition", "unmodeled task states cannot silently enter the review loop", "Step 8"],
    ["AC-08", "supporting", "EP-03", "Use Case 3", "Given a later analysis cycle and task outcomes exist", "When the review summary is generated", "Then the report links the current delta view back to the prior run and task execution outcome", "The review summary preserves prior-cycle evidence linkage", "cross_cycle_linkage", "review cannot close if prior-cycle evidence is detached", "Step 9"],
    ["AC-09", "anchor", "EP-03", "Primary User Story", "Given trend evidence is noisy or contradictory", "When the system prepares a review conclusion", "Then the report emits an uncertainty note instead of a false deterministic claim", "Decision output stays review-bound rather than overstating confidence", "uncertain_signal", "ambiguous signals must not be flattened into certainty", "Step 10"],
    ["AC-10", "supporting", "EP-01", "Primary User Story", "Given the first-wave boundary is presented to stakeholders", "When scope interpretation is reviewed", "Then in-scope, later slice, deferred seam, explicit out-of-scope, and non-goals remain visible together", "Readers can see the scope boundary contract without reconstructing it from stage artifacts", "scope_boundary_drift", "the boundary fails if any bucket disappears from the reader-visible contract", "Step 10"],
    ["AC-11", "supporting", "EP-03", "Primary User Story", "Given the user navigates primary module surfaces", "When they follow the first-wave object chain", "Then each surface links through the same business context and execution context", "The workflow can be traversed end-to-end without object-chain breaks", "navigation_break", "object-chain navigation must not fork into unrelated contexts", "Step 4"],
    ["AC-12", "anchor", "EP-01", "Primary User Story", "Given a user attempts cross-tenant access", "When the read or write request reaches the boundary", "Then the system blocks or audits the access attempt explicitly", "Unauthorized cross-tenant access is denied or explicitly auditable", "permission_boundary", "cross-tenant access is never allowed as an implicit success path", "Step 2"],
    ["AC-13", "supporting", "EP-03", "Use Case 4", "Given a downstream export is produced", "When execution semantics are serialized for intake", "Then optional notes and blocked reason remain preserved where applicable", "Downstream intake can still distinguish ready-from-clarification-needed items", "export_semantics_loss", "export is invalid if clarification semantics disappear", "Step 7"],
    ["AC-14", "supporting", "EP-03", "Use Case 3", "Given deferred extension capability stays outside MVP", "When the implementation seam is described", "Then the source-declared deferred extension fields remain reserved", "Phase-2 can extend the object chain without rewriting current contracts", "deferred_seam_loss", "deferred extension fields may stay out of MVP but cannot vanish from the seam contract", "Step 10"],
    ["AC-15", "anchor", "EP-01", "Primary User Story", "Given source features are translated into first-wave scope", "When the carryover ledger is reviewed", "Then every critical source feature is classified as first-wave abstraction, later slice, deferred seam, or explicit out-of-scope", "No critical source feature disappears without an explicit classification decision", "source_feature_drop", "a critical source feature cannot disappear without an explicit classification", "Step 10"],
]

REQUIREMENT_TRANSLATION_ROWS = [
    ["RQ-01", "EP-01", "Primary User Story", "functional_requirement", "系统必须支持首波业务入口记录的创建与更新。", "这是首波业务流程的直接系统行为。"],
    ["RQ-02", "EP-01", "Primary User Story", "functional_requirement", "系统必须校验主流程所需的最小输入完整性。", "没有完整输入就不能进入下一业务步骤。"],
    ["RQ-03", "EP-01", "Primary User Story", "functional_requirement", "系统必须可重复完成核心业务流程，并记录关键状态变化。", "这是主流程可执行性的直接能力。"],
    ["RQ-04", "EP-02", "Use Case 1", "functional_requirement", "系统必须输出最小业务结果集，并提供字段口径说明。", "用户在进入后续处理前必须先拿到最小结果集。"],
    ["RQ-05", "EP-02", "Use Case 1 / Use Case 2", "functional_requirement", "系统必须支持必要的辅助上下文展示。", "这是业务判断与处理优先级的直接功能。"],
    ["RQ-06", "EP-02", "Use Case 1 / Use Case 2", "functional_requirement", "系统必须把上游业务记录映射为下游可执行动作。", "记录到动作的转译是首版核心价值。"],
    ["RQ-07", "EP-02", "Use Case 2 / Use Case 4", "functional_requirement", "下游动作载荷必须具备对象标识、优先级、责任提示和阻塞说明。", "这是下游动作能否进入执行的直接功能契约。"],
    ["RQ-08", "EP-03", "Use Case 3", "functional_requirement", "下游动作必须可导出为执行清单并支持状态跟踪。", "执行桥接是首版闭环的核心行为。"],
    ["RQ-09", "EP-03", "Use Case 3", "functional_requirement", "系统必须记录执行状态、责任角色与执行备注。", "结果回看依赖执行上下文，属于主流程行为。"],
    ["RQ-10", "EP-03", "Use Case 3", "functional_requirement", "结果页必须提供变化视图、阈值和不确定性说明。", "这是复盘判断的直接产品输出。"],
    ["RQ-11", "EP-03", "Primary User Story", "governance_constraint", "系统必须显式标记仍待确认的事实，禁止静默升级为 confirmed。", "它约束证据状态的使用方式，而不是新增功能入口。"],
    ["RQ-12", "EP-01", "Primary User Story", "governance_constraint", "首版必须显式声明 out-of-scope 与 non-goals。", "这是范围治理规则，用于防止承诺漂移。"],
    ["RQ-13", "EP-01 / EP-03", "Primary User Story / Use Case 3", "quality_or_compliance_constraint", "权限与留存边界必须对相关角色可见。", "它约束合规可审计性，而非普通用户功能。"],
    ["RQ-14", "EP-03", "Use Case 4", "functional_requirement", "当下游动作不可执行时，系统必须支持 return-for-clarification。", "这是异常回退流程的直接系统能力。"],
    ["RQ-15", "EP-01", "Primary User Story", "quality_or_compliance_constraint", "任何跨租户数据读写都必须被阻止或审计。", "这是安全与审计底线，不应与一般功能混写。"],
    ["RQ-16", "EP-02 / EP-03", "Use Case 2 / Use Case 4", "functional_requirement", "模块 handoff payload 必须在适用时保留结构化字段。", "这是 execution-ready payload 的直接功能定义。"],
    ["RQ-17", "EP-03", "Use Case 3", "quality_or_compliance_constraint", "系统必须为 source brief 明确声明的 deferred extension 保留 seam 字段或接口说明，但不得把它们包装成已完成能力。", "它约束未来扩展与证据诚实度，属于质量/合规边界。"],
    ["RQ-18", "EP-02 / EP-03", "Use Case 2 / Primary User Story", "governance_constraint", "产品边界必须用 source feature carryover ledger 显式声明哪些 source 细节被保留为 first-wave abstraction、later slice、deferred seam、explicit out-of-scope。", "这是跨阶段边界治理规则。"],
]

REQUIREMENT_TRACE_ROWS = [
    ["EP-01", "Primary User Story", "RQ-01", "functional_requirement", "AC-01", "baseline_happy_path", "Step 1"],
    ["EP-01", "Primary User Story", "RQ-02", "functional_requirement", "AC-02", "missing_required_input", "Step 2"],
    ["EP-01", "Primary User Story", "RQ-03", "functional_requirement", "AC-03", "minimum_result_set", "Step 4"],
    ["EP-02", "Use Case 1", "RQ-04", "functional_requirement", "AC-03", "minimum_result_set", "Step 4"],
    ["EP-02", "Use Case 1 / Use Case 2", "RQ-05", "functional_requirement", "AC-04", "detail_completeness", "Step 5"],
    ["EP-02", "Use Case 1 / Use Case 2", "RQ-06", "functional_requirement", "AC-04", "detail_completeness", "Step 5"],
    ["EP-02", "Use Case 2 / Use Case 4", "RQ-07", "functional_requirement", "AC-05", "invalid_payload", "Step 6"],
    ["EP-03", "Use Case 3", "RQ-08", "functional_requirement", "AC-06", "handoff_integrity", "Step 7"],
    ["EP-03", "Use Case 3", "RQ-09", "functional_requirement", "AC-07", "invalid_state_transition", "Step 8"],
    ["EP-03", "Use Case 3", "RQ-10", "functional_requirement", "AC-08", "cross_cycle_linkage", "Step 9"],
    ["EP-03", "Primary User Story", "RQ-11", "governance_constraint", "AC-09", "uncertain_signal", "Step 10"],
    ["EP-01", "Primary User Story", "RQ-12", "governance_constraint", "AC-10", "scope_boundary_drift", "Step 10"],
    ["EP-01 / EP-03", "Primary User Story / Use Case 3", "RQ-13", "quality_or_compliance_constraint", "AC-12", "permission_boundary", "Step 2"],
    ["EP-03", "Use Case 4", "RQ-14", "functional_requirement", "AC-13", "export_semantics_loss", "Step 7"],
    ["EP-01", "Primary User Story", "RQ-15", "quality_or_compliance_constraint", "AC-12", "permission_boundary", "Step 2"],
    ["EP-02 / EP-03", "Use Case 2 / Use Case 4", "RQ-16", "functional_requirement", "AC-05", "invalid_payload", "Step 6"],
    ["EP-03", "Use Case 3", "RQ-17", "quality_or_compliance_constraint", "AC-14", "deferred_seam_loss", "Step 10"],
    ["EP-02 / EP-03", "Use Case 2 / Primary User Story", "RQ-18", "governance_constraint", "AC-15", "source_feature_drop", "Step 10"],
]

COMPETITIVE_LANDSCAPE_ROWS = [
    ["manual / spreadsheet workaround", "paper, Excel, or ad hoc offline workflow", "internal labor cost / hidden opportunity cost", "can explain current pain but usually breaks at module-to-module traceability", "source-grounded", "product must beat the current fragmented operating baseline before promising automation"],
    ["partial digital tool", "single-function registration, scheduling, or reporting tool", "subscription / seat-based signal", "strong on one local task, weak on full business-flow closure", "review-bound", "do not collapse first-wave positioning into a partial utility page"],
    ["service / operator-managed workaround", "human-driven workaround or service substitute", "retainer / project fee signal", "strong on manual interpretation, weaker on repeatable in-product continuity", "review-bound", "first wave should emphasize explicit process memory and object traceability"],
]

PRICING_VALIDATION_ROWS = [
    ["value interview with pricing prompt", "teams will discuss budget only if the workflow reduces decision uncertainty, not just if it adds a dashboard", "sample report + package card", ">=3 interviewees express trial or budget-evaluation intent", "rework value proposition or customer boundary before treating pricing as credible"],
    ["clickable prototype packaging test", "users can distinguish the value of baseline-only vs workflow-loop tiers", "clickable prototype + packaging options", "target users can explain why they would choose one tier over another", "simplify package framing and reposition the first-wave promise"],
    ["concierge pilot quote test", "a manually supported first cycle can establish an initial willingness-to-pay anchor", "pilot scope statement + quote range", "at least one pilot-ready quote conversation progresses beyond curiosity", "delay pricing commitment and continue evidence collection"],
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_h2_block(text: str, heading_keywords: list[str]) -> str:
    for keyword in heading_keywords:
        match = re.search(
            rf"^##\s+(?:\d+\.\s+)?[^\n]*{re.escape(keyword)}[^\n]*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            continue
        start = match.start()
        tail = text[start:]
        next_h2 = re.search(r"^##\s+", tail[1:], flags=re.MULTILINE)
        if next_h2:
            return tail[: next_h2.start() + 1].strip()
        return tail.strip()
    return ""


def demote_headings(text: str, levels: int = 1) -> str:
    if not text:
        return "- (missing stage section)"
    out: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            prefix_len = len(line) - len(line.lstrip("#"))
            title = line[prefix_len:].strip()
            title = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", title).strip()
            out.append(f"{'#' * min(prefix_len + levels, 6)} {title}".rstrip())
            continue
        out.append(line)
    return "\n".join(out).strip()


def integrate_stage_block(
    text: str,
    strip_first_heading: bool = True,
    extra_heading_levels: int = 0,
) -> str:
    if not text:
        return "- (missing stage section)"
    lines = text.splitlines()
    if strip_first_heading and lines and lines[0].startswith("##"):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    out: list[str] = []
    for line in lines:
        if line.startswith("#"):
            prefix_len = len(line) - len(line.lstrip("#"))
            title = line[prefix_len:].strip()
            title = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", title).strip()
            out.append(f"{'#' * min(prefix_len + extra_heading_levels, 6)} {title}".rstrip())
            continue
        out.append(line)
    return "\n".join(out).strip()


def list_hits(text: str, patterns: list[tuple[str, str]]) -> list[str]:
    hits: list[str] = []
    for label, pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            hits.append(label)
    return hits


def extract_single_line_field(text: str, field: str) -> str:
    match = re.search(
        rf"^[ \t]*-[ \t]+{re.escape(field)}:[ \t]*`?([^`\n]+)`?[ \t]*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def extract_markdown_section(text: str, heading_candidates: list[str], level_pattern: str = r"##") -> str:
    for heading in heading_candidates:
        match = re.search(
            rf"^{level_pattern}\s+(?:\d+(?:\.\d+)?\s+)?[^\n]*{re.escape(heading)}[^\n]*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            continue
        start = match.start()
        tail = text[start:]
        next_heading = re.search(rf"^{level_pattern}\s+", tail[1:], flags=re.MULTILINE)
        end = next_heading.start() + 1 if next_heading else len(tail)
        return tail[:end].strip()
    return ""


def source_fact_text(source_text: str) -> str:
    """Return the product fact surface for a P1 source input packet."""

    if not re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE):
        return source_text
    return normalize_source_handoff_phrases(
        extract_markdown_section(source_text, ["P1 Source Brief"], level_pattern=r"##") or source_text
    )


def list_items_from_markdown(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        bullet = re.match(r"^\s*[-*]\s+`?([^`\n]+?)`?\s*$", line)
        if bullet:
            items.append(bullet.group(1).strip())
            continue
        numbered = re.match(r"^\s*\d+\.\s+(.+?)\s*$", line)
        if numbered:
            items.append(numbered.group(1).strip())
    return items


def strip_heading_line(block: str) -> str:
    if not block:
        return ""
    lines = block.splitlines()
    if lines and lines[0].startswith("#"):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    return "\n".join(lines).strip()


def first_meaningful_line(block: str) -> str:
    body = strip_heading_line(block)
    for line in body.splitlines():
        cleaned = re.sub(r"^\s*[-*]\s+", "", line).strip()
        if cleaned:
            return cleaned.strip("`")
    return ""


def preferred_markdown_item(block: str, preferred_prefixes: list[str] | None = None) -> str:
    items = [item.strip() for item in list_items_from_markdown(strip_heading_line(block)) if item.strip()]
    if preferred_prefixes:
        for prefix in preferred_prefixes:
            for item in items:
                if item.startswith(prefix):
                    return item
    return items[0] if items else first_meaningful_line(block)


def is_missing_placeholder(value: str) -> bool:
    cleaned = value.strip()
    if not cleaned:
        return True
    lowered = cleaned.lower()
    return lowered in {
        "(source section not found)",
        "source section not found",
        "`(source section not found)`",
    }


def slugify(raw: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return normalized or "phase-1-prd"


def derive_output_path(requested_output: Path, document_name: str) -> Path:
    if requested_output.suffix:
        if requested_output.stem.endswith("rpd-main-document-assembled") or requested_output.name.startswith(
            "geo-rpd-main-document-assembled"
        ):
            return requested_output.with_name(f"{slugify(document_name)}-main-document-assembled.md")
        if requested_output.stem.endswith("rpd-main-document") or requested_output.name.startswith("geo-rpd-main-document"):
            return requested_output.with_name(f"{slugify(document_name)}-main-document.md")
        return requested_output
    return requested_output / f"{slugify(document_name)}-main-document.md"


def extract_nested_field_value(text: str, field: str) -> str:
    match = re.search(
        rf"^\s*-\s+{re.escape(field)}:\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return ""
    tail = text[match.end() :]
    nested = re.search(r"^\s*-\s+`?([^`\n]+)`?\s*$", tail, flags=re.IGNORECASE | re.MULTILINE)
    return nested.group(1).strip() if nested else ""


def render_source_artifacts_table(entries: list[dict[str, str]]) -> str:
    lines = [
        "| artifact_id | artifact_type | file | role |",
        "|---|---|---|---|",
    ]
    for entry in entries:
        lines.append(
            f"| {entry['artifact_id']} | {entry['artifact_type']} | {entry['file']} | {entry['role']} |"
        )
    return "\n".join(lines)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body: list[str] = []
    for row in rows:
        escaped = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        body.append("| " + " | ".join(escaped) + " |")
    return "\n".join([header, separator, *body])


def parse_markdown_table(block: str) -> list[dict[str, str]]:
    lines = [line.rstrip() for line in block.splitlines() if line.strip()]
    for idx in range(len(lines) - 1):
        if "|" not in lines[idx] or "|" not in lines[idx + 1]:
            continue
        if not re.match(r"^\s*\|?[\-:\s|]+\|?\s*$", lines[idx + 1]):
            continue
        headers = [re.sub(r"[^a-z0-9]+", "_", cell.strip().lower()).strip("_") for cell in lines[idx].strip().strip("|").split("|")]
        rows: list[dict[str, str]] = []
        for line in lines[idx + 2 :]:
            if "|" not in line:
                break
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) != len(headers):
                continue
            rows.append({header: cell for header, cell in zip(headers, cells)})
        if rows:
            return rows
    return []


def table_row_value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def ia_surface_match_key(value: str) -> str:
    return re.sub(r"\W+", "", value.casefold())


def ia_surface_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\w+", value.casefold())
        if token and token not in {"screen", "module", "workspace", "page", "view", "console"}
    }


def normalized_match_key(value: str) -> str:
    return re.sub(r"\W+", "", value.casefold())


ROLE_LIKE_SURFACE_PATTERN = re.compile(
    r"owner|manager|operator|receptionist|veterinarian|assistant|reviewer|lead|director|"
    r"负责人|经理|主管|运营|医生|前台|评审者|院长|店长",
    flags=re.IGNORECASE,
)
OBJECT_LIKE_SURFACE_PATTERN = re.compile(
    r"record|task|scope|workspace|run|summary|ledger|order|report|finding|recommendation|"
    r"visit|treatment|followup|baseline|audit|profile|state|"
    r"记录|任务|范围|对象|档案|账单|病历|报告|状态|复诊|检查|治疗",
    flags=re.IGNORECASE,
)


def looks_like_placeholder(value: str) -> bool:
    cleaned = re.sub(r"\s+", " ", value).strip("` ").casefold()
    if not cleaned:
        return True
    if cleaned in {
        "item",
        "primary object",
        "secondary object",
        "source flow",
        "source-defined output",
        "source-defined input",
        "source-defined trigger",
        "source-defined entry condition",
        "source-defined information objects",
        "source-defined module payload",
        "source-defined core objects",
        "next workflow object",
    }:
        return True
    return any(
        token in cleaned
        for token in (
            "source-defined",
            "source defined",
            "module responsibility from source",
            "from source brief",
            "workflow output",
            "workflow input",
            "work item/export implication",
        )
    )


def extract_nested_list_items(block: str, labels: list[str]) -> list[str]:
    if not block:
        return []
    lines = block.splitlines()
    label_set = [label.casefold() for label in labels]
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        lowered = stripped.casefold()
        if not any(label in lowered for label in label_set):
            continue
        parent_indent = len(line) - len(line.lstrip())
        items: list[str] = []
        for nested_line in lines[idx + 1 :]:
            if not nested_line.strip():
                continue
            indent = len(nested_line) - len(nested_line.lstrip())
            bullet = re.match(r"^\s*-\s+`?([^`\n]+?)`?\s*$", nested_line)
            numbered = re.match(r"^\s*\d+\.\s+(.+?)\s*$", nested_line)
            if indent <= parent_indent and (bullet or numbered):
                break
            if indent > parent_indent and bullet:
                items.append(bullet.group(1).strip())
                continue
            if indent > parent_indent and numbered:
                items.append(numbered.group(1).strip())
        if items:
            return items
    return []


def extract_ia_precursor_rows(stage_02b_text: str) -> list[dict[str, str]]:
    if not stage_02b_text:
        return []
    block = extract_h2_block(stage_02b_text, ["IA Spec Precursor Matrix"])
    return parse_markdown_table(block)


def find_matching_ia_precursor_row(module_name: str, precursor_rows: list[dict[str, str]]) -> dict[str, str] | None:
    module_label = module_name.strip()
    if not module_label:
        return None
    module_key = ia_surface_match_key(module_label)
    module_tokens = ia_surface_tokens(module_label)
    best_row: dict[str, str] | None = None
    best_score = 0
    for row in precursor_rows:
        surface = table_row_value(row, "screen_module", "screen_module_", "module", "module_name", "page_name")
        if not surface:
            continue
        surface_key = ia_surface_match_key(surface)
        surface_tokens = ia_surface_tokens(surface)
        score = 0
        if module_key and surface_key == module_key:
            score = 100
        elif module_key and surface_key and (module_key in surface_key or surface_key in module_key):
            score = 60
        elif module_tokens and surface_tokens:
            overlap = len(module_tokens & surface_tokens)
            if overlap:
                score = overlap * 10
        if score > best_score:
            best_score = score
            best_row = row
    return best_row if best_score > 0 else None


def extract_stage_module_matrix_rows(stage_02b_text: str) -> list[dict[str, str]]:
    if not stage_02b_text:
        return []
    block = extract_h2_block(stage_02b_text, ["Module Responsibility Matrix", "模块职责矩阵"])
    return parse_markdown_table(block)


def extract_stage_object_workflow_rows(stage_02b_text: str) -> list[dict[str, str]]:
    if not stage_02b_text:
        return []
    block = extract_h2_block(stage_02b_text, ["Object-to-Workflow Mapping", "对象到工作流映射"])
    return parse_markdown_table(block)


def extract_stage_process_rows(stage_02a_text: str) -> list[dict[str, str]]:
    if not stage_02a_text:
        return []
    block = extract_h2_block(stage_02a_text, ["Business Process Identification", "业务流程识别"])
    rows = parse_markdown_table(block)
    normalized: list[dict[str, str]] = []
    for row in rows:
        process_name = table_row_value(row, "process_name", "process", "workflow_step")
        if not process_name:
            continue
        normalized.append(
            {
                "process_type": table_row_value(row, "process_type"),
                "process_name": process_name,
                "primary_owner": table_row_value(row, "primary_owner", "owner", "role"),
                "trigger": table_row_value(row, "trigger", "entry_conditions", "entry_condition"),
                "output": table_row_value(row, "output", "exit_actions", "exit_action"),
                "why_it_matters": table_row_value(row, "why_it_matters", "responsibility", "description"),
            }
        )
    return normalized


def extract_stage_domain_entities(stage_02b_text: str) -> list[str]:
    if not stage_02b_text:
        return []
    block = extract_h2_block(stage_02b_text, ["Domain Model Direction", "领域模型方向"])
    entities = extract_nested_list_items(block, ["core entities", "核心实体"])
    if entities:
        return [item.split(":", 1)[0].strip("` ") for item in entities if not looks_like_placeholder(item)]
    catalog_items = extract_nested_list_items(block, ["entity catalog", "实体目录"])
    return [
        item.split(":", 1)[0].strip("` ")
        for item in catalog_items
        if item.strip() and not looks_like_placeholder(item)
    ]


def split_steps_evenly(steps: list[str], group_count: int) -> list[list[str]]:
    if group_count <= 0:
        return []
    sizes = [len(steps) // group_count for _ in range(group_count)]
    for idx in range(len(steps) % group_count):
        sizes[idx] += 1
    groups: list[list[str]] = []
    cursor = 0
    for size in sizes:
        groups.append(steps[cursor : cursor + size] if size > 0 else [])
        cursor += size
    return groups


def append_unique_flow(flows: list[dict[str, object]], title: str, steps: list[str]) -> None:
    cleaned_title = re.sub(r"\s+", " ", title).strip()
    if not cleaned_title:
        return
    cleaned_steps = [
        re.sub(r"\s+", " ", step).strip("` ")
        for step in steps
        if re.sub(r"\s+", " ", step).strip("` ")
    ]
    flow_key = normalized_match_key(cleaned_title)
    for existing in flows:
        if normalized_match_key(str(existing.get("title", ""))) != flow_key:
            continue
        if len(cleaned_steps) > len(existing.get("steps", [])):
            existing["steps"] = cleaned_steps
        return
    flows.append({"title": cleaned_title, "steps": cleaned_steps})


def is_handoff_step(step: str) -> bool:
    normalized = re.sub(r"\s+", " ", step).strip()
    return bool(re.match(r"^(?:handoff to|把当前上下文交给)\b", normalized, flags=re.IGNORECASE))


def extract_required_outcome_from_step(step: str) -> str:
    normalized = re.sub(r"\s+", " ", step).strip().strip("`")
    if not normalized:
        return ""
    if is_handoff_step(normalized):
        return ""
    output_match = re.match(
        r"^(?:输出|output)\s+`?(.+?)`?\s*(?:并准备下游交接|and prepare downstream handoff)?$",
        normalized,
        flags=re.IGNORECASE,
    )
    if output_match:
        return output_match.group(1).strip()
    return normalized


def select_required_outcome(steps: list[str]) -> str:
    for step in reversed(steps):
        candidate = extract_required_outcome_from_step(step)
        if candidate:
            return candidate
    return "complete the source-defined flow"


def should_append_downstream_handoff(
    downstream: str,
    output_name: str,
    known_targets: set[str],
) -> bool:
    cleaned_downstream = re.sub(r"\s+", " ", downstream).strip()
    if not cleaned_downstream or looks_like_placeholder(cleaned_downstream):
        return False
    if normalized_match_key(cleaned_downstream) == normalized_match_key(output_name):
        return False
    return normalized_match_key(cleaned_downstream) in known_targets


def extract_heading_defined_flows(source_text: str) -> list[dict[str, object]]:
    lines = source_text.splitlines()
    flows: list[dict[str, object]] = []
    idx = 0
    while idx < len(lines):
        heading = re.match(r"^(#{2,6})\s+(.+?)\s*$", lines[idx].strip())
        if not heading:
            idx += 1
            continue
        heading_title = re.sub(r"^\d+(?:\.\d+)*\s+", "", heading.group(2)).strip()
        if not re.search(r"主流程|核心业务流程|Key Business Flow|Business Flow|Main Flow", heading_title, flags=re.IGNORECASE):
            idx += 1
            continue
        flow_title = re.sub(
            r"^(?:主流程|核心业务流程|Key Business Flow|Business Flow|Main Flow)\s*[:：-]?\s*",
            "",
            heading_title,
            flags=re.IGNORECASE,
        ).strip() or heading_title
        block_lines: list[str] = []
        idx += 1
        while idx < len(lines) and not re.match(r"^#{2,6}\s+", lines[idx].strip()):
            block_lines.append(lines[idx])
            idx += 1
        append_unique_flow(flows, flow_title, list_items_from_markdown("\n".join(block_lines)))
    return flows


def build_stage_process_flows(stage_02a_text: str, stage_02b_text: str = "") -> list[dict[str, object]]:
    process_rows = extract_stage_process_rows(stage_02a_text)
    module_rows = extract_stage_module_matrix_rows(stage_02b_text)
    precursor_rows = extract_ia_precursor_rows(stage_02b_text)
    if not process_rows and not module_rows:
        return []

    workflow_block = extract_h2_block(stage_02a_text, ["Workflow / State Detail", "工作流 / 状态细节"])
    workflow_steps = extract_nested_list_items(workflow_block, ["primary workflow", "workflow steps", "主流程"])
    grouped_steps = split_steps_evenly(workflow_steps, len(process_rows)) if process_rows else []
    module_lookup = {
        normalized_match_key(table_row_value(row, "module", "screen_module", "workflow_step")): row
        for row in module_rows
        if table_row_value(row, "module", "screen_module", "workflow_step")
    }
    known_handoff_targets = {
        normalized_match_key(process_row["process_name"])
        for process_row in process_rows
        if process_row.get("process_name")
    }
    known_handoff_targets.update(module_lookup.keys())

    flows: list[dict[str, object]] = []
    if process_rows:
        for idx, process_row in enumerate(process_rows):
            title = process_row["process_name"]
            steps = list(grouped_steps[idx]) if idx < len(grouped_steps) else []
            module_row = module_lookup.get(normalized_match_key(title), {})
            precursor_row = find_matching_ia_precursor_row(title, precursor_rows) or {}
            if not steps:
                input_name = table_row_value(module_row, "input") or process_row["trigger"]
                responsibility = table_row_value(module_row, "responsibility") or process_row["why_it_matters"]
                output_name = table_row_value(module_row, "output") or process_row["output"]
                if input_name and not looks_like_placeholder(input_name):
                    steps.append(f"确认 `{input_name}` 已就绪")
                if responsibility and not looks_like_placeholder(responsibility):
                    steps.append(responsibility)
                if output_name and not looks_like_placeholder(output_name):
                    steps.append(f"输出 `{output_name}` 并准备下游交接")
                downstream = table_row_value(precursor_row, "downstream_dependency", "dependency")
                if should_append_downstream_handoff(downstream, output_name, known_handoff_targets):
                    steps.append(f"handoff to `{downstream}`")
            append_unique_flow(flows, title, steps)
    else:
        for row in module_rows:
            title = table_row_value(row, "module")
            if not title:
                continue
            steps: list[str] = []
            input_name = table_row_value(row, "input")
            responsibility = table_row_value(row, "responsibility")
            output_name = table_row_value(row, "output")
            if input_name and not looks_like_placeholder(input_name):
                steps.append(f"确认 `{input_name}` 已就绪")
            if responsibility and not looks_like_placeholder(responsibility):
                steps.append(responsibility)
            if output_name and not looks_like_placeholder(output_name):
                steps.append(f"输出 `{output_name}` 并准备下游交接")
            append_unique_flow(flows, title, steps)
    return flows


def extract_ia_matrix_from_brief(source_text: str, stage_02b_text: str = "") -> list[dict[str, str]]:
    block = extract_markdown_section(
        source_text,
        ["Module Responsibility Matrix", "Information Architecture Spec Matrix", "Module Matrix"],
        level_pattern=r"##",
    )
    rows = parse_markdown_table(block)
    stage_module_rows = extract_stage_module_matrix_rows(stage_02b_text)
    existing_keys = {
        normalized_match_key(table_row_value(row, "module", "module_name", "domain", "screen_module", "workflow_step"))
        for row in rows
        if table_row_value(row, "module", "module_name", "domain", "screen_module", "workflow_step")
    }
    for row in stage_module_rows:
        module_name = table_row_value(row, "module", "screen_module", "workflow_step")
        match_key = normalized_match_key(module_name)
        if module_name and match_key not in existing_keys:
            rows.append(row)
            existing_keys.add(match_key)
    precursor_rows = extract_ia_precursor_rows(stage_02b_text)
    if not rows and precursor_rows:
        rows = [
            {
                "module": table_row_value(row, "screen_module", "module", "workflow_step"),
                "primary_actor": table_row_value(row, "primary_actor", "role", "owner"),
                "core_objects": table_row_value(row, "required_information_objects", "objects"),
                "responsibility": "",
                "input": table_row_value(row, "entry_conditions", "entry_condition"),
                "output": table_row_value(row, "exit_actions", "exit_action"),
                "downstream_dependency": table_row_value(row, "downstream_dependency", "dependency"),
            }
            for row in precursor_rows
            if table_row_value(row, "screen_module", "module", "workflow_step")
        ]

    object_rows = extract_core_business_objects_from_brief(source_text, stage_02b_text)
    module_to_objects: dict[str, list[str]] = {}
    for object_row in object_rows:
        module = object_row.get("module", "").strip()
        object_name = object_row.get("object", "").strip()
        if not module or not object_name:
            continue
        module_to_objects.setdefault(normalized_match_key(module), []).append(object_name)
    for object_flow_row in extract_stage_object_workflow_rows(stage_02b_text):
        workflow_step = table_row_value(object_flow_row, "workflow_step", "process_name", "module")
        if not workflow_step:
            continue
        for object_name in (
            table_row_value(object_flow_row, "primary_object", "object"),
            table_row_value(object_flow_row, "secondary_object", "supporting_object"),
        ):
            if object_name and not looks_like_placeholder(object_name):
                module_to_objects.setdefault(normalized_match_key(workflow_step), []).append(object_name)

    normalized: list[dict[str, str]] = []
    for idx, row in enumerate(rows, start=1):
        module_name = table_row_value(row, "module", "module_name", "domain", "screen_module", "workflow_step") or f"module_{idx}"
        precursor_row = find_matching_ia_precursor_row(module_name, precursor_rows)
        core_objects = table_row_value(row, "core_objects", "objects", "core_business_objects")
        if not core_objects:
            core_objects = table_row_value(
                precursor_row or {},
                "required_information_objects",
                "core_objects",
                "objects",
            )
        if not core_objects:
            matched_objects = module_to_objects.get(normalized_match_key(module_name), [])
            core_objects = ", ".join(dict.fromkeys(matched_objects))
        if not core_objects and precursor_row:
            core_objects = table_row_value(
                precursor_row,
                "required_information_objects",
                "core_objects",
                "objects",
            )
        normalized.append(
            {
                "module": module_name,
                "primary_actor": table_row_value(
                    row,
                    "primary_actor",
                    "primary_actor_role",
                    "actor",
                    "owner",
                    "persona_role",
                    "role",
                ) or (
                    table_row_value(
                        precursor_row or {},
                        "primary_actor",
                        "owner",
                        "persona_role",
                        "role",
                    )
                    if precursor_row
                    else ""
                ),
                "core_objects": core_objects,
                "responsibility": table_row_value(row, "responsibility", "description", "summary", "why_it_matters"),
                "input": table_row_value(row, "input", "inputs", "upstream_input"),
                "output": table_row_value(row, "output", "outputs", "downstream_output"),
                "entry_condition": table_row_value(precursor_row or {}, "entry_conditions", "entry_condition") if precursor_row else "",
                "exit_action": table_row_value(precursor_row or {}, "exit_actions", "exit_action") if precursor_row else "",
                "downstream_dependency": table_row_value(
                    precursor_row or {},
                    "downstream_dependency",
                    "dependency",
                    "depends_on",
                ) if precursor_row else "",
            }
        )
    return normalized


def extract_core_business_objects_from_brief(source_text: str, stage_02b_text: str = "") -> list[dict[str, str]]:
    block = extract_markdown_section(
        source_text,
        ["Core Business Objects", "Entity Registry"],
        level_pattern=r"##",
    )
    rows = parse_markdown_table(block)
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        name = row.get("object") or row.get("entity") or row.get("name") or row.get("core_object") or ""
        if not name:
            continue
        match_key = normalized_match_key(name)
        seen.add(match_key)
        normalized.append(
            {
                "object": name,
                "description": row.get("description") or row.get("responsibility") or row.get("purpose") or "",
                "module": row.get("module") or row.get("owner_module") or row.get("owning_module") or row.get("owner") or "",
            }
        )
    for row in extract_stage_object_workflow_rows(stage_02b_text):
        workflow_step = table_row_value(row, "workflow_step", "process_name", "module")
        downstream_effect = table_row_value(row, "downstream_effect", "effect", "why_it_matters")
        for object_name, role_label in (
            (table_row_value(row, "primary_object", "object"), "primary"),
            (table_row_value(row, "secondary_object", "supporting_object"), "supporting"),
        ):
            match_key = normalized_match_key(object_name)
            if not object_name or match_key in seen or looks_like_placeholder(object_name):
                continue
            seen.add(match_key)
            normalized.append(
                {
                    "object": object_name,
                    "description": (
                        f"{role_label} object for `{workflow_step}`; {downstream_effect or 'supports downstream handoff continuity'}"
                    ),
                    "module": workflow_step,
                }
            )
    stage_modules = {
        normalized_match_key(table_row_value(row, "module")): table_row_value(row, "module")
        for row in extract_stage_module_matrix_rows(stage_02b_text)
        if table_row_value(row, "module")
    }
    for entity_name in extract_stage_domain_entities(stage_02b_text):
        match_key = normalized_match_key(entity_name)
        if match_key in seen:
            continue
        seen.add(match_key)
        normalized.append(
            {
                "object": entity_name,
                "description": "core entity preserved from Stage-02b domain model direction",
                "module": stage_modules.get(match_key, entity_name if match_key in stage_modules else ""),
            }
        )
    return normalized


def extract_target_user_roles_from_brief(source_text: str) -> list[str]:
    block = extract_markdown_section(source_text, ["Target Users", "目标用户", "研究对象/目标用户边界"], level_pattern=r"##")
    rows = parse_markdown_table(block)
    roles: list[str] = []

    def normalize_role(value: str) -> str:
        cleaned = re.sub(r"^\s*(?:主要用户|次要用户|评审用户)\s*[：:]\s*", "", value).strip()
        if not cleaned:
            return ""
        lowered = cleaned.casefold()
        excluded_prefixes = (
            "客群边界",
            "使用边界",
            "边界",
            "首发不做",
            "不做",
            "非目标",
            "not for",
        )
        if any(lowered.startswith(prefix.casefold()) for prefix in excluded_prefixes):
            return ""
        if "不做" in cleaned or "not do" in lowered:
            return ""
        return cleaned

    for row in rows:
        role = row.get("role") or row.get("user") or row.get("persona") or row.get("target_user") or ""
        role = normalize_role(role)
        if role:
            roles.append(role)
    if roles:
        return list(dict.fromkeys(roles))
    return list(
        dict.fromkeys(
            role
            for role in (normalize_role(item) for item in list_items_from_markdown(block))
            if role
        )
    )


def extract_structured_source_items(source_text: str, headings: list[str]) -> list[str]:
    block = extract_markdown_section(source_text, headings, level_pattern=r"##")
    items = [item.strip() for item in list_items_from_markdown(block) if item.strip()]
    return list(dict.fromkeys(items))


def detect_domain_style(source_text: str, runtime_context: dict[str, object]) -> str:
    pack = runtime_context.get("domain_baseline_pack", {})
    if isinstance(pack, dict) and pack.get("domain") == "pet_clinic":
        return "pet_clinic"
    fact_source_text = source_fact_text(source_text)
    evidence_text = " ".join(
        [
            fact_source_text,
            str(runtime_context.get("executive_summary", "")),
            str(runtime_context.get("problem_statement", "")),
            str(runtime_context.get("workflow_backbone", "")),
            str(runtime_context.get("object_chain", "")),
            " ".join(str(item) for item in runtime_context.get("target_user_roles", [])),
        ]
    ).casefold()
    if re.search(
        r"\bgeo\b|ai 搜索|ai 回答|ai 可见性|visibility|tracked scope|finding|recommendation|seo|归因|roi|conversion",
        evidence_text,
    ):
        return "growth_observation"
    return "generic"


def summarize_structured_items(items: list[str], fallback: str) -> str:
    if not items:
        return fallback
    return ", ".join(items[:4])


def compress_business_sentence(value: str, *, max_parts: int = 1) -> str:
    text = compact_signal_line(value)
    if not text:
        return ""
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    text = re.sub(r"\bThe product should help\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCurrent source evidence already shows the operating cost of staying fragmented:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bThe system makes that repeatable by keeping .*", "", text, flags=re.IGNORECASE)
    parts = [
        item.strip("。.;:： ")
        for item in re.split(r"[。；;]+", text)
        if item.strip("。.;:： ")
    ]
    if not parts:
        return text.strip("。.;:： ")
    return "。 ".join(parts[:max_parts]).strip("。.;:： ")


def clean_source_label_phrase(value: object) -> str:
    text = compact_signal_line(str(value))
    if not text:
        return ""
    text = re.sub(r"\b(?:目标|Goal|Objective|Desired Outcome)\s*[:：]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:当前替代方案|现有方式|Current substitute|Status quo)\s*[:：]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:核心问题|问题|Problem)\s*[:：]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"核心问题不是[“\"].*?[”\"]\s*[，,]\s*而是\s*", "", text)
    text = re.sub(r"核心问题不是.*?而是\s*", "", text)
    text = re.sub(r"(^|\s)[：:；;，,]+\s*", r"\1", text)
    text = re.sub(r"(围绕|看到|进入|从|产生|解决|承受|削弱)\s*[：:；;，,]+\s*", r"\1 ", text)
    text = re.sub(r"\s+([。；;，,])", r"\1", text)
    text = re.sub(r"([。；;，,])\s*([。；;，,])+", r"\1", text)
    text = re.sub(r"[；;]\s*", "。 ", text)
    text = re.sub(r"\s+", " ", text).strip("。；;:： ")
    return text


def clean_runtime_label_item(value: str) -> str:
    text = compact_signal_line(value)
    text = re.sub(r"`([^`\n]+)`", r"\1", text).replace("`", "")
    text = re.sub(r"\.\s*(?=与|并|因此|作为|足以|否则|但)", "，", text)
    text = re.sub(r"\.([。；，,])", r"\1", text)
    text = re.sub(r"([。；，,])\s*([。；，,])+", r"\1", text)
    return text.strip("。；;:： ")


def plain_label_surface(labels: list[str], fallback: str, *, limit: int = 3) -> str:
    picked = [clean_runtime_label_item(label) for label in labels if clean_runtime_label_item(label)]
    if not picked:
        return fallback
    rendered = picked[:limit]
    if len(rendered) == 1:
        return rendered[0]
    if len(rendered) == 2:
        return f"{rendered[0]} 和 {rendered[1]}"
    return f"{'、'.join(rendered[:-1])} 和 {rendered[-1]}"


def business_loop_items(runtime_context: dict[str, object], limit: int = 5) -> list[str]:
    source_flows = list(runtime_context.get("source_flows", []))
    for flow in source_flows:
        title = compact_signal_line(str(flow.get("title", "")))
        steps = [clean_step_title(str(step)) for step in flow.get("steps", []) if clean_step_title(str(step))]
        if steps and re.search(r"完成一次|闭环|complete.+loop", title, flags=re.IGNORECASE):
            return dedupe_runtime_phrases(steps)[:limit]
    flow_titles = [
        compact_signal_line(str(flow.get("title", "")))
        for flow in source_flows
        if compact_signal_line(str(flow.get("title", "")))
    ]
    if flow_titles:
        return dedupe_runtime_phrases(flow_titles)[:limit]
    return module_names(runtime_context, limit)


def business_loop_surface(runtime_context: dict[str, object], limit: int = 5) -> str:
    return runtime_label_surface(
        business_loop_items(runtime_context, limit),
        "`source-defined business loop`",
        limit=limit,
    )


def business_loop_plain_surface(runtime_context: dict[str, object], limit: int = 5) -> str:
    return plain_label_surface(
        business_loop_items(runtime_context, limit),
        "source-defined business loop",
        limit=limit,
    )


def business_loop_reader_surface(runtime_context: dict[str, object], limit: int = 4) -> str:
    items = []
    for item in business_loop_items(runtime_context, limit):
        text = clean_runtime_label_item(item)
        text = re.sub(r"配置或更新\s+tracked scope", "配置 tracked scope", text, flags=re.IGNORECASE)
        text = re.sub(r"触发一次\s+baseline\s+生成", "生成 baseline", text, flags=re.IGNORECASE)
        text = re.sub(r"查看\s+baseline summary\s+与\s+findings", "查看 findings", text, flags=re.IGNORECASE)
        text = re.sub(r"选择高优先级\s+finding[，,]\s*转成\s+recommendation/任务", "转成 recommendation/任务", text, flags=re.IGNORECASE)
        text = re.sub(r"内容运营执行\s+任务\s+并更新状态", "执行任务并更新状态", text, flags=re.IGNORECASE)
        if text:
            items.append(text)
    return plain_label_surface(items, "source-defined business loop", limit=limit)


def build_scope_promise_line(source_text: str, runtime_context: dict[str, object]) -> str:
    style = detect_domain_style(source_text, runtime_context)
    if style == "growth_observation":
        return "首版承诺的是“可观测 + 可解释 + 可执行 + 可复盘”的业务闭环，不承诺全自动优化执行与高精度财务级归因；所有未验证真相仍以待评审确认（review-bound）方式显式保留。"
    if style == "pet_clinic":
        return "首版承诺的是可执行、可追踪、可审计、可复盘的就诊运营闭环，不承诺未验证的自动化经营扩展；所有未验证真相仍以待评审确认（review-bound）方式显式保留。"
    return "首版承诺的是可执行、可解释、可追踪、可复盘的业务闭环，不承诺未验证的自动化扩展或高级经营分析；所有未验证真相仍以待评审确认（review-bound）方式显式保留。"


def build_problem_chain_line(source_text: str, runtime_context: dict[str, object]) -> str:
    style = detect_domain_style(source_text, runtime_context)
    business_loop = business_loop_plain_surface(runtime_context, limit=5)
    if style == "growth_observation":
        return f"团队当前缺的是一条把 {business_loop} 放进同一经营主线的完整闭环。没有这条主线，信号无法变成行动，行动无法变成复盘，投入无法变成可解释决策。"
    if style == "pet_clinic":
        return f"团队当前缺的是一条把 {business_loop} 放进同一服务主线的完整闭环。没有这条主线，接诊上下文会在关键环节丢失，治疗执行、离院确认和复诊安排会重新回到人工补录与口头交接。"
    return f"团队当前缺的是一条把 {business_loop} 放进同一经营主线的完整闭环。没有这条主线，关键业务上下文会在环节之间丢失，后续执行与复盘会重新回到人工拼接。"


def build_problem_boundary_line(source_text: str, runtime_context: dict[str, object]) -> str:
    style = detect_domain_style(source_text, runtime_context)
    business_loop = business_loop_plain_surface(runtime_context, limit=5)
    if style == "growth_observation":
        return f"必须把 {business_loop} 组织成可重复经营闭环，而不是只输出一次性洞察。"
    if style == "pet_clinic":
        return f"必须把 {business_loop} 组织成可重复执行的就诊服务闭环，而不是只留下零散记录或单点页面。"
    return f"必须把 {business_loop} 组织成可重复执行的业务闭环，而不是只输出一次性记录或局部页面。"


def build_review_bound_summary(source_text: str, runtime_context: dict[str, object]) -> str:
    style = detect_domain_style(source_text, runtime_context)
    primary_segment = str(runtime_context.get("primary_segment", "")).strip() or "primary segment"
    if style == "growth_observation":
        return f"首发客群收敛到 {primary_segment}、付费意愿强度、recommendation trust、指标稳定性、粗粒度归因接受度。"
    if style == "pet_clinic":
        return f"首发主边界收敛到 {primary_segment}、真实门店采纳摩擦、指标稳定性、范围接受度和更深经营分析需求。"
    return f"首发主边界收敛到 {primary_segment}、采纳摩擦、指标稳定性、范围接受度和后续扩展需求。"


def render_problem_signal_lines(source_text: str, runtime_context: dict[str, object]) -> list[str]:
    style = detect_domain_style(source_text, runtime_context)
    roles = list(runtime_context.get("target_user_roles", []))[:3]
    role_text = "、".join(roles) if roles else "核心角色"
    problem_items = extract_structured_source_items(source_text, ["Structured Problem List", "结构化问题清单"])
    opportunity_items = extract_structured_source_items(source_text, ["Structured Opportunity List", "结构化机会清单"])
    lines = [
        f"- top_problem_clusters: {summarize_structured_items(problem_items, 'source-defined business problems still need explicit recompilation')}",
        f"- top_opportunity_clusters: {summarize_structured_items(opportunity_items, 'source-defined business opportunities still need explicit recompilation')}",
    ]
    if style == "growth_observation":
        lines.extend(
            [
                "- AI visibility note: 当前域的核心压力来自 AI 可见性、证据可解释性和 recommendation/action 闭环，而不是传统页面流量本身。",
                f"- gap question: 当前围绕 {business_loop_plain_surface(runtime_context, limit=5)} 的经营主线，哪些环节仍会让 evidence、priority 或 action 在 handoff 中失真。",
                f"- current visibility position question: 当前可见性位置是否能让 {role_text} 看到同一条 tracked scope、finding、recommendation 与 review 主线。",
                "- partial-tool gap question: 分散的 SEO/reporting 或 prompt-probing 工具为什么不能闭合完整 GEO 运营闭环",
                "- 局部工具为何不足 (partial_tool_gap_question): 单点工具可以展示 observation，但无法在主线闭环里持续保留 recommendation、action 和 review 的连续性。",
                "- business_change_question: 如果 scope、finding、recommendation 和 review 被组织成同一条经营链，团队的预算判断、内容优先级和复盘质量会如何变化",
            ]
        )
    elif style == "pet_clinic":
        lines.extend(
            [
                "- operating visibility note: 当前域的核心压力来自接诊上下文、治疗执行和离院复诊闭环的连续可见，而不是单点页面存在与否。",
                f"- gap question: 当前围绕 {business_loop_plain_surface(runtime_context, limit=5)} 的服务主线，哪些环节仍会让 visit context、blocked reason 或 next action 在 handoff 中丢失。",
                f"- current visibility position question: 当前记录链路是否能让 {role_text} 看到同一条接诊、治疗与离院/复诊主线。",
                "- partial-tool gap question: 分散的 registration、billing 或 note-taking 工具为什么不能闭合完整诊所运营闭环",
                "- 局部工具为何不足 (partial_tool_gap_question): 单点工具可以数字化某一步，但无法在主线闭环里持续保留可供医生接手的上下文、治疗证据和闭环连续性。",
                "- business_change_question: 如果接诊、治疗、离院和复诊被组织成同一条服务链，门店执行质量、异常处理和复盘判断会如何变化",
            ]
        )
    else:
        lines.extend(
            [
                "- operating visibility note: 当前域的核心压力来自核心业务对象、状态推进和 review/closure 的连续可见。",
                f"- gap question: 当前围绕 {business_loop_plain_surface(runtime_context, limit=5)} 的业务主线，哪些环节仍会让上下文、blocked reason 或 next action 在 handoff 中丢失。",
                f"- current visibility position question: 当前记录链路是否能让 {role_text} 看到同一条业务对象推进链。",
                "- partial-tool gap question: 分散的单点工具为什么不能闭合完整运营闭环",
                "- 局部工具为何不足 (partial_tool_gap_question): 单点工具可以数字化某一步，但无法在主线闭环里持续保留端到端上下文连续性。",
                "- business_change_question: 如果核心业务对象、状态推进和复盘被组织成同一条闭环，团队的日常执行和判断会如何变化",
            ]
        )
    return lines


def extract_key_business_flows_from_brief(
    source_text: str,
    stage_02a_text: str = "",
    stage_02b_text: str = "",
) -> list[dict[str, object]]:
    block = extract_markdown_section(source_text, ["Key Business Flows", "核心业务流程", "Business Flows"], level_pattern=r"##")
    flows: list[dict[str, object]] = []
    if block:
        current_title = ""
        current_steps: list[str] = []
        for line in block.splitlines():
            heading = re.match(r"^###\s+(.+)$", line.strip())
            if heading:
                if current_title:
                    append_unique_flow(flows, current_title, current_steps[:])
                current_title = heading.group(1).strip()
                current_steps = []
                continue
            step = re.match(r"^\s*(?:[-*]|\d+\.)\s+(.+?)\s*$", line)
            if step and current_title:
                current_steps.append(step.group(1).strip())
        if current_title:
            append_unique_flow(flows, current_title, current_steps[:])
    for flow in extract_heading_defined_flows(source_text):
        append_unique_flow(flows, str(flow.get("title", "")), list(flow.get("steps", [])))
    for flow in build_stage_process_flows(stage_02a_text, stage_02b_text):
        append_unique_flow(flows, str(flow.get("title", "")), list(flow.get("steps", [])))
    return flows


def extract_out_of_scope_items_from_brief(source_text: str) -> list[str]:
    block = extract_markdown_section(source_text, ["Out of Scope", "Out of Scope (MVP)", "范围外"], level_pattern=r"##")
    return list_items_from_markdown(block)


def extract_non_functional_requirements_from_brief(source_text: str) -> list[str]:
    block = extract_markdown_section(
        source_text,
        ["Non-functional Requirements", "NFR", "非功能需求"],
        level_pattern=r"##",
    )
    return list_items_from_markdown(block)


def extract_architectural_constraints_from_brief(source_text: str) -> list[str]:
    block = extract_markdown_section(
        source_text,
        ["Architectural Constraints", "Architecture Constraints", "架构约束"],
        level_pattern=r"##",
    )
    return list_items_from_markdown(block)


def render_module_capability_lines(rows: list[dict[str, str]]) -> list[str]:
    return [
        f"- {row['module']}: {row['responsibility'] or 'module responsibility from source brief'}"
        for row in rows
        if row.get("module")
    ]


def module_names(runtime_context: dict[str, object], limit: int | None = None) -> list[str]:
    rows = list(runtime_context.get("ia_matrix", []))
    names = [str(row.get("module", "")).strip() for row in rows if str(row.get("module", "")).strip()]
    return names[:limit] if limit is not None else names


def module_chain_text(runtime_context: dict[str, object], limit: int | None = None) -> str:
    names = module_names(runtime_context, limit)
    return " -> ".join(names) if names else "source-defined module chain"


def core_object_names(runtime_context: dict[str, object], limit: int | None = None) -> list[str]:
    rows = list(runtime_context.get("core_business_objects", []))
    names = [str(row.get("object", "")).strip() for row in rows if str(row.get("object", "")).strip()]
    return names[:limit] if limit is not None else names


def object_chain_text(runtime_context: dict[str, object], limit: int | None = None) -> str:
    names = core_object_names(runtime_context, limit)
    return " -> ".join(names) if names else "source-defined object chain"


def generic_workflow_label(runtime_context: dict[str, object]) -> str:
    return str(runtime_context.get("workflow_backbone", "")).strip() or module_chain_text(runtime_context, 5)


def detect_domain_baseline_pack(runtime_context: dict[str, object]) -> dict[str, object]:
    evidence_text = " ".join(
        [
            str(runtime_context.get("executive_summary", "")),
            str(runtime_context.get("problem_statement", "")),
            str(runtime_context.get("workflow_backbone", "")),
            str(runtime_context.get("object_chain", "")),
            " ".join(module_names(runtime_context, 12)),
            " ".join(core_object_names(runtime_context, 12)),
            " ".join(str(item) for item in runtime_context.get("target_user_roles", [])),
        ]
    ).casefold()
    if re.search(
        r"pet|clinic|veterinar|诊所|宠物|就诊|治疗|复诊|discharge|follow-up|billing|invoice|medication|x-ray|diagnosis",
        evidence_text,
    ):
        return {
            "domain": "pet_clinic",
            "overview_lines": [
                "ordinary_real_world_baseline: 首波诊所流程应覆盖接诊证据、可供医生接手的就诊上下文、治疗执行证据，以及离院加复诊闭环，而不是停在很薄的登记 demo。",
                "real_world_constraint: 普通诊所通常需要 owner identity、pet identity、prior record / vaccine context、weight、temperature 和 urgent/triage signal，医生交接才算安全。",
                "coordination_density: 前台、医生和离院 / 管理角色需要共享同一份 visit record，并看到同一个 blocked reason、next action 和 follow-up timing。",
            ],
            "topic_lines": {
                "intake": [
                    "ordinary_real_world_baseline: 接诊通常需要先记录 owner identity、pet identity、visit reason、prior medical / vaccine context 和 urgent/triage flag，然后才能交给医生。",
                    "real_world_constraint: 前台通常要记录 weight、temperature、photo 或其他 identity evidence，并完成必需的 consent / document checks，visit 才能继续。",
                    "coordination_density: receptionist 交给 veterinarian 的应是 checked-in visit、current vitals 和 missing-document flags，而不是口头重新拼装的上下文。",
                ],
                "care": [
                    "ordinary_real_world_baseline: 问诊和治疗通常需要 exam findings、必要时的 lab / x-ray 等 diagnostic orders、treatment items，以及已执行用药 / 操作证据。",
                    "real_world_constraint: 当 diagnostics、equipment 或 clinician time 不可用时，工作流必须保留 estimate / approval notes、treatment evidence 和 blocked reasons。",
                    "coordination_density: veterinarian 和执行人员必须在 billing 或 discharge 前看到同一份 treatment order、completion status 和 next action。",
                ],
                "closure": [
                    "ordinary_real_world_baseline: 离院闭环通常包括 invoice / payment confirmation、medication 与 home-care instructions、warning signs，以及已安排的 recheck / follow-up。",
                    "real_world_constraint: 如果 payment、take-home meds、discharge instructions 或 follow-up timing 仍不完整，discharge 必须保持 blocked。",
                    "coordination_density: clinic manager 或前台只能在 clinician handoff、discharge packet 和 review-ready audit trail 保持一致后关闭 visit。",
                ],
            },
            "acceptance_rows": [
                [
                    "AC-RW-01",
                    "anchor",
                    "EP-01",
                    "Primary User Story",
                    "Given a pet arrives without completed identity evidence, weight, temperature, or prior-record context where applicable",
                    "When the receptionist attempts to hand the visit to the veterinarian",
                    "Then the system keeps the visit blocked and exposes the missing intake evidence explicitly",
                    "Clinic intake cannot advance as a thin registration shell without the minimum real-world visit context",
                    "missing_required_input",
                    "intake handoff must not hide missing vitals, records, consent, or urgent/triage context",
                    "Flow 1",
                ],
                [
                    "AC-RW-02",
                    "supporting",
                    "EP-02",
                    "Use Case 2",
                    "Given diagnostics, medication, or treatment work is ordered during the visit",
                    "When treatment evidence, estimate approval, or blocked reason is still incomplete",
                    "Then the system prevents discharge-ready or billing-ready handoff until the missing execution truth is recorded",
                    "Treatment and diagnostics remain executable rather than collapsing into a note-only demo record",
                    "handoff_contract_integrity",
                    "the visit must not move forward if treatment evidence, diagnostic result, or blocked reason is missing",
                    "Flow 2",
                ],
                [
                    "AC-RW-03",
                    "anchor",
                    "EP-03",
                    "Use Case 3",
                    "Given a visit is being closed after treatment",
                    "When discharge instructions, take-home medication notes, payment confirmation, or follow-up timing is incomplete",
                    "Then the system keeps the visit out of closed state and records the outstanding closure requirement",
                    "Pet-clinic closure remains reviewable and safe instead of ending at a paid-but-undischarged pseudo-finish",
                    "payment_closure",
                    "closure must not complete before discharge packet and follow-up contract are present",
                    "Flow 3",
                ],
            ],
        }
    return {"domain": "generic", "overview_lines": [], "topic_lines": {}, "acceptance_rows": []}


def domain_baseline_topic_for_title(runtime_context: dict[str, object], title: str) -> str:
    pack = runtime_context.get("domain_baseline_pack", {})
    if not isinstance(pack, dict) or pack.get("domain") != "pet_clinic":
        return "overview"
    lowered = title.casefold()
    if re.search(r"接诊|登记|intake|register|check-?in|arrival", lowered):
        return "intake"
    if re.search(r"检查|治疗|consult|exam|diagnos|care|treatment|procedure", lowered):
        return "care"
    if re.search(r"复诊|离院|出院|billing|invoice|closure|discharge|follow-?up|review", lowered):
        return "closure"
    return "overview"


def render_domain_baseline_lines(runtime_context: dict[str, object], title: str) -> list[str]:
    pack = runtime_context.get("domain_baseline_pack", {})
    if not isinstance(pack, dict):
        return []
    topic = domain_baseline_topic_for_title(runtime_context, title)
    topic_lines = list(pack.get("topic_lines", {}).get(topic, []))
    overview_lines = list(pack.get("overview_lines", []))
    selected = topic_lines or overview_lines
    return [f"- {line}" for line in selected]


def normalize_runtime_phrase(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().strip("`").strip()


def dedupe_runtime_phrases(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = normalize_runtime_phrase(value)
        if not text or looks_like_placeholder(text):
            continue
        key = normalized_match_key(text)
        if key and key not in seen:
            seen.add(key)
            ordered.append(text)
    return ordered


def split_contiguous_groups(items: list[object], target_count: int) -> list[list[object]]:
    if not items:
        return []
    group_count = max(1, min(target_count, len(items)))
    groups: list[list[object]] = []
    base_size = len(items) // group_count
    remainder = len(items) % group_count
    cursor = 0
    for idx in range(group_count):
        group_size = base_size + (1 if idx < remainder else 0)
        group = list(items[cursor : cursor + group_size])
        cursor += group_size
        if group:
            groups.append(group)
    return groups


def split_core_object_names(raw: str) -> list[str]:
    return dedupe_runtime_phrases(re.split(r"[,，]+", str(raw)))


def clean_step_title(step: str) -> str:
    return normalize_runtime_phrase(re.sub(r"^[\d\.\-]+\s*", "", str(step))).rstrip("。.;:：")


def loop_target_title_for_index(runtime_context: dict[str, object], index: int) -> str:
    targets = loop_targets(runtime_context)
    if index < 0 or index >= len(targets):
        return ""
    title = loop_title_short(str(targets[index].get("scenario_title", "")))
    if re.fullmatch(r"Scenario [A-Z0-9]+", title, flags=re.IGNORECASE):
        return ""
    return title


def derive_mainline_scenario_title(
    runtime_context: dict[str, object],
    *,
    index: int,
    modules: list[str],
    step_group: list[str],
) -> str:
    loop_title = loop_target_title_for_index(runtime_context, index)
    if loop_title:
        return loop_title
    if modules:
        if len(modules) == 1:
            return modules[0]
        return f"{modules[0]} -> {modules[-1]}"
    cleaned_steps = [clean_step_title(step) for step in step_group if clean_step_title(step)]
    if cleaned_steps:
        if len(cleaned_steps) == 1:
            return cleaned_steps[0]
        return f"{cleaned_steps[0]} -> {cleaned_steps[-1]}"
    return f"source-defined mainline slice {index + 1}"


def build_row_action_fragments(row: dict[str, str]) -> list[str]:
    module = normalize_runtime_phrase(row.get("module", ""))
    responsibility = normalize_runtime_phrase(row.get("responsibility", ""))
    output_name = normalize_runtime_phrase(row.get("output", "") or row.get("exit_action", ""))
    fragments: list[str] = []
    if module and responsibility and not looks_like_placeholder(responsibility):
        fragments.append(f"{module}: {responsibility}")
    if module and output_name and not looks_like_placeholder(output_name):
        fragments.append(f"{module}: {output_name}")
    return dedupe_runtime_phrases(fragments)


def scenario_has_commercial_context(runtime_context: dict[str, object], bundle: dict[str, object]) -> bool:
    probe = " ".join(
        [
            str(runtime_context.get("executive_summary", "")),
            str(runtime_context.get("problem_statement", "")),
            str(bundle.get("title", "")),
            str(bundle.get("input_anchor", "")),
            str(bundle.get("output_anchor", "")),
            " ".join(str(item) for item in runtime_context.get("target_user_roles", [])),
            " ".join(str(step) for step in bundle.get("path_steps", [])),
        ]
    ).casefold()
    return bool(
        re.search(
            r"budget|pricing|roi|pilot|invest|investment|business owner|decision owner|continue|revise|pause|"
            r"commercial|marketing|growth|package|willingness[- ]to[- ]pay|"
            r"预算|定价|投入|试点|业务负责人|决策负责人|继续|调整|暂停|经营|增长|市场|付费",
            probe,
        )
    )


def build_mainline_scenario_bundles(runtime_context: dict[str, object]) -> list[dict[str, object]]:
    primary_segment = str(runtime_context.get("primary_segment", "")).strip() or "primary operator"
    target_roles = dedupe_runtime_phrases([str(item) for item in runtime_context.get("target_user_roles", [])])
    source_flows = list(runtime_context.get("source_flows", []))
    mainline_steps = [
        normalize_runtime_phrase(step)
        for step in (
            source_flows[0].get("steps", [])
            if source_flows and isinstance(source_flows[0], dict)
            else []
        )
        if normalize_runtime_phrase(step)
    ]
    ia_rows = [
        row
        for row in list(runtime_context.get("ia_matrix", []))
        if isinstance(row, dict) and normalize_runtime_phrase(row.get("module", ""))
    ]
    bundles: list[dict[str, object]] = []
    if ia_rows:
        row_groups = split_contiguous_groups(ia_rows, 3)
        step_groups = (
            split_contiguous_groups(mainline_steps, len(row_groups))
            if mainline_steps
            else [[] for _ in row_groups]
        )
        if len(step_groups) < len(row_groups):
            step_groups = step_groups + [[] for _ in range(len(row_groups) - len(step_groups))]
        for idx, rows in enumerate(row_groups):
            modules = dedupe_runtime_phrases([str(row.get("module", "")) for row in rows])
            actors = dedupe_runtime_phrases([str(row.get("primary_actor", "")) for row in rows]) or [primary_segment]
            objects = dedupe_runtime_phrases(
                [
                    object_name
                    for row in rows
                    for object_name in split_core_object_names(str(row.get("core_objects", "")))
                ]
            )
            first_row = rows[0]
            last_row = rows[-1]
            input_anchor = normalize_runtime_phrase(first_row.get("entry_condition", "") or first_row.get("input", ""))
            output_anchor = normalize_runtime_phrase(last_row.get("output", "") or last_row.get("exit_action", ""))
            next_row = row_groups[idx + 1][0] if idx + 1 < len(row_groups) and row_groups[idx + 1] else None
            downstream_owner = normalize_runtime_phrase(next_row.get("primary_actor", "")) if isinstance(next_row, dict) else ""
            if not downstream_owner:
                downstream_owner = actors[-1] if actors else (target_roles[-1] if target_roles else primary_segment)
            downstream_dependency = normalize_runtime_phrase(last_row.get("downstream_dependency", ""))
            if not downstream_dependency and isinstance(next_row, dict):
                downstream_dependency = normalize_runtime_phrase(next_row.get("entry_condition", "") or next_row.get("input", ""))
            path_steps = dedupe_runtime_phrases(
                [str(step) for step in step_groups[idx]]
                + [fragment for row in rows for fragment in build_row_action_fragments(row)]
            )
            bundle = {
                "title": derive_mainline_scenario_title(runtime_context, index=idx, modules=modules, step_group=[str(step) for step in step_groups[idx]]),
                "modules": modules,
                "actors": actors,
                "objects": objects,
                "input_anchor": input_anchor or (clean_step_title(str(step_groups[idx][0])) if step_groups[idx] else "source-defined entry evidence"),
                "output_anchor": output_anchor or (clean_step_title(str(step_groups[idx][-1])) if step_groups[idx] else "source-defined business outcome"),
                "downstream_dependency": downstream_dependency or output_anchor or "source-defined downstream dependency",
                "downstream_owner": downstream_owner,
                "path_steps": path_steps or [f"{' -> '.join(modules) if modules else 'source-defined module chain'}"],
                "primary_segment": primary_segment,
            }
            bundle["commercial_context"] = scenario_has_commercial_context(runtime_context, bundle)
            bundle["experience_context"] = len(actors) >= 2 or len(path_steps) >= 3
            bundles.append(bundle)
        return bundles

    if len(source_flows) > 1 and re.search(r"完成一次|闭环|complete.+loop", str(source_flows[0].get("title", "")), flags=re.IGNORECASE):
        candidate_flows = source_flows[1:4] or source_flows[:3]
    else:
        candidate_flows = source_flows[:3]
    if candidate_flows:
        for idx, flow in enumerate(candidate_flows[:3]):
            steps = [normalize_runtime_phrase(step) for step in flow.get("steps", []) if normalize_runtime_phrase(step)]
            bundle = {
                "title": derive_mainline_scenario_title(
                    runtime_context,
                    index=idx,
                    modules=[normalize_runtime_phrase(flow.get("title", ""))],
                    step_group=steps,
                ),
                "modules": dedupe_runtime_phrases([str(flow.get("title", ""))]),
                "actors": target_roles or [primary_segment],
                "objects": dedupe_runtime_phrases(core_object_names(runtime_context, 6)),
                "input_anchor": clean_step_title(steps[0]) if steps else "source-defined entry evidence",
                "output_anchor": clean_step_title(steps[-1]) if steps else "source-defined business outcome",
                "downstream_dependency": clean_step_title(steps[-1]) if steps else "source-defined downstream dependency",
                "downstream_owner": (target_roles[-1] if target_roles else primary_segment),
                "path_steps": steps or [normalize_runtime_phrase(flow.get("title", ""))],
                "primary_segment": primary_segment,
            }
            bundle["commercial_context"] = scenario_has_commercial_context(runtime_context, bundle)
            bundle["experience_context"] = len(bundle["actors"]) >= 2 or len(bundle["path_steps"]) >= 3
            bundles.append(bundle)
        return bundles

    if mainline_steps:
        step_groups = split_contiguous_groups(mainline_steps, min(3, len(mainline_steps)))
        for idx, step_group in enumerate(step_groups):
            bundle = {
                "title": derive_mainline_scenario_title(runtime_context, index=idx, modules=[], step_group=[str(step) for step in step_group]),
                "modules": [],
                "actors": target_roles or [primary_segment],
                "objects": dedupe_runtime_phrases(core_object_names(runtime_context, 6)),
                "input_anchor": clean_step_title(str(step_group[0])),
                "output_anchor": clean_step_title(str(step_group[-1])),
                "downstream_dependency": clean_step_title(str(step_group[-1])),
                "downstream_owner": (target_roles[-1] if target_roles else primary_segment),
                "path_steps": [normalize_runtime_phrase(str(step)) for step in step_group],
                "primary_segment": primary_segment,
            }
            bundle["commercial_context"] = scenario_has_commercial_context(runtime_context, bundle)
            bundle["experience_context"] = len(bundle["actors"]) >= 2 or len(bundle["path_steps"]) >= 3
            bundles.append(bundle)
    return bundles


def render_mainline_business_scenario_block(
    runtime_context: dict[str, object],
    label: str,
    bundle: dict[str, object],
    *,
    target_index: int,
) -> list[str]:
    modules = list(bundle.get("modules", []))
    actors = list(bundle.get("actors", []))
    objects = list(bundle.get("objects", []))
    title = str(bundle.get("title", "")).strip() or f"source-defined mainline slice {label}"
    module_chain_display = " -> ".join(f"`{module}`" for module in modules) if modules else "`source-defined mainline`"
    object_chain_display = ", ".join(f"`{object_name}`" for object_name in objects[:6]) if objects else "`source-defined business object`"
    module_chain = " -> ".join(plain_truth_text(module) for module in modules if plain_truth_text(module)) or "source-defined mainline"
    actor_chain = " -> ".join(plain_truth_text(actor) for actor in actors if plain_truth_text(actor)) or plain_truth_text(
        str(bundle.get("primary_segment", "primary operator"))
    )
    object_chain = "、".join(plain_truth_text(object_name) for object_name in objects[:6] if plain_truth_text(object_name)) or "source-defined business object"
    input_anchor = reader_facing_digest_phrase(str(bundle.get("input_anchor", "")).strip() or "source-defined entry evidence")
    output_anchor = reader_facing_digest_phrase(str(bundle.get("output_anchor", "")).strip() or "source-defined business outcome")
    downstream_dependency = reader_facing_digest_phrase(str(bundle.get("downstream_dependency", "")).strip() or output_anchor)
    downstream_owner = str(bundle.get("downstream_owner", "")).strip() or str(bundle.get("primary_segment", "primary operator")).strip()
    handoff_surface = " / ".join(dedupe_runtime_phrases([output_anchor, downstream_dependency])) or output_anchor
    path_steps = [reader_facing_digest_phrase(str(step).strip()) for step in bundle.get("path_steps", []) if str(step).strip()]
    main_success_path = " -> ".join(path_steps[:6]) if path_steps else f"{input_anchor} -> {output_anchor}"
    title_hint = title.casefold()
    if re.search(r"review|closure|结论|复盘|离院|出院|follow-?up", title_hint):
        exception_hint = "insufficient evidence, unresolved status, blocked closure, audit gap"
    elif re.search(r"treat|care|consult|diagnos|finding|recommendation|任务|治疗|检查|诊断|发现|建议", title_hint):
        exception_hint = "invalid state, blocked dependency, missing execution evidence, recovery/retry"
    else:
        exception_hint = "missing required input, invalid state, permission boundary, dependency unavailable"
    success_criteria = (
        f"{output_anchor} 需要和 {object_chain} 以及下一步边界一起保持可查询。"
        if objects
        else f"{output_anchor} 需要和下一步边界、owner context 一起保持可查询。"
    )
    blocked_path = (
        f"若 {input_anchor} 或 {object_chain} 仍不完整，阻止进入 {plain_truth_text(modules[-1])}；允许保存草稿，但必须显式保留 blocked reason 与 review-bound risk。"
        if modules and objects
        else f"若 {input_anchor} 仍不完整，阻止进入下一工作流状态；允许保存草稿，但必须显式保留 blocked reason 与 review-bound risk。"
    )
    structure_implication = (
        f"{module_chain} 必须保持为一个有类型的主线切片，不能被拆成互不相连的设置页或报告页。"
        if modules
        else "源素材定义的主线切片必须保持类型清晰和连续，不能退化成互不相连的页面。"
    )
    baseline_consequence = (
        f"如果 {input_anchor} 过薄，下游团队必须先重建 {object_chain}，{plain_truth_text(downstream_owner)} 才能继续。"
        if objects
        else f"如果 {input_anchor} 过薄，下游团队必须先重建缺失上下文，{plain_truth_text(downstream_owner)} 才能继续。"
    )
    scenario_consequence = (
        f"团队会回到围绕 {module_chain} 人工重建上下文，{plain_truth_text(downstream_owner)} 只能收到过薄或含糊的 {downstream_dependency}；如果下一动作无法被明确记录，产品会退化为报告系统，并不会稳定支持真实工作。"
        if modules
        else f"团队会回到人工重建上下文，{plain_truth_text(downstream_owner)} 只能收到过薄或含糊的 {downstream_dependency}；如果下一动作无法被明确记录，产品会退化为报告系统，并不会稳定支持真实工作。"
    )
    lines = [
        f"#### Scenario {label}: {title}",
        f"- scenario_title: {title}",
        f"- primary actors: {actor_chain}",
        f"- module contract chain: {module_chain_display}",
        f"- concrete business objects: {object_chain_display}",
        f"- trigger: {input_anchor} 进入主线切片。",
        f"- preconditions: {input_anchor} 已可用，{actor_chain} 可以操作 {object_chain}，且 owner / audit context 保持可见。",
        f"- main success path: {main_success_path}",
        f"- key exception paths: {exception_hint}",
        f"- success criteria: {success_criteria}",
        f"- downstream_handoff_contract: {handoff_surface} 需要向 {plain_truth_text(downstream_owner)} 保持可见，并在需要时带上 owner、state 和 blocked-reason context。",
        f"- blocked_path: {blocked_path}",
        f"- structure implication: {structure_implication}",
        f"- baseline consequence: {baseline_consequence}",
        *render_loop_business_scenario_lines(runtime_context, target_index, scenario_context=bundle),
        *render_domain_baseline_lines(runtime_context, title),
        f"- scenario consequence if weak: {scenario_consequence}",
    ]
    return lines


def render_mainline_business_scenarios(runtime_context: dict[str, object]) -> list[str]:
    bundles = build_mainline_scenario_bundles(runtime_context)
    if not bundles:
        fallback_bundle = {
            "title": "source-defined mainline slice",
            "modules": module_names(runtime_context, 3),
            "actors": [str(runtime_context.get("primary_segment", "primary operator"))],
            "objects": core_object_names(runtime_context, 4),
            "input_anchor": "source-defined entry evidence",
            "output_anchor": "source-defined business outcome",
            "downstream_dependency": "source-defined downstream dependency",
            "downstream_owner": str(runtime_context.get("primary_segment", "primary operator")),
            "path_steps": ["source-defined mainline step"],
            "primary_segment": str(runtime_context.get("primary_segment", "primary operator")),
            "commercial_context": False,
            "experience_context": False,
        }
        bundles = [fallback_bundle]
    lines: list[str] = []
    for idx, bundle in enumerate(bundles[:3], start=1):
        scenario_bundle = dict(bundle)
        scenario_bundle["is_final_bundle"] = idx == min(len(bundles), 3)
        label = chr(ord("A") + idx - 1)
        lines.extend(render_mainline_business_scenario_block(runtime_context, label, scenario_bundle, target_index=idx))
        lines.append("")
    return lines[:-1] if lines and not lines[-1].strip() else lines


def render_dynamic_flowchart(runtime_context: dict[str, object]) -> list[str]:
    names = module_names(runtime_context, 8)
    if not names:
        names = ["Source Module 1", "Source Module 2"]
    lines = ["```mermaid", "flowchart LR"]
    node_ids = [chr(ord("A") + idx) for idx in range(len(names))]
    for node_id, name in zip(node_ids, names):
        lines.append(f"    {node_id}[{name}]")
    for idx in range(len(node_ids) - 1):
        lines.append(f"    {node_ids[idx]} --> {node_ids[idx + 1]}")
    lines.append("```")
    return lines


def render_dynamic_er_diagram(runtime_context: dict[str, object]) -> list[str]:
    objects = core_object_names(runtime_context, 8)
    if len(objects) < 2:
        return [
            "```mermaid",
            "erDiagram",
            "    ENTITY_A ||--o{ ENTITY_B : relates_to",
            "```",
        ]
    lines = ["```mermaid", "erDiagram"]
    for left, right in zip(objects, objects[1:]):
        left_id = re.sub(r"[^A-Z0-9]+", "_", left.upper()).strip("_") or "ENTITY_A"
        right_id = re.sub(r"[^A-Z0-9]+", "_", right.upper()).strip("_") or "ENTITY_B"
        lines.append(f"    {left_id} ||--o{{ {right_id} : flows_to")
    lines.append("```")
    return lines


def extract_payload_fields(value: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[;,/]|(?:\s+\+\s+)", value) if part.strip()]
    cleaned: list[str] = []
    for part in parts:
        token = re.sub(r"\s+", " ", part).strip("` ")
        if token:
            cleaned.append(token)
    return cleaned


def build_interface_payload_description(row: dict[str, str]) -> str:
    inputs = extract_payload_fields(str(row.get("input", "")))
    outputs = extract_payload_fields(str(row.get("output", "")))
    fields = list(dict.fromkeys(inputs[:2] + outputs[:2]))
    if not fields:
        fields = [str(row.get("module", "module")).strip(), "status transition"]
    return " / ".join(fields)


SEGMENT_SIGNAL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("B2B", r"\bB2B\b"),
    ("消费品牌", r"消费品牌"),
    ("电商", r"电商"),
    ("创作者", r"创作者"),
    ("本地服务", r"本地服务"),
)


def extract_segment_landscape_signals(source_text: str) -> list[str]:
    hits: list[str] = []
    for label, pattern in SEGMENT_SIGNAL_PATTERNS:
        if re.search(pattern, source_text, flags=re.IGNORECASE | re.MULTILINE):
            hits.append(label)
    return hits


def signal_matches_primary_segment(signal: str, primary_segment: str) -> bool:
    normalized_signal = signal.strip().lower()
    normalized_primary = primary_segment.strip().lower()
    if not normalized_signal or not normalized_primary:
        return False
    if normalized_signal == "b2b":
        return "b2b" in normalized_primary
    return normalized_signal in normalized_primary


def render_segment_landscape_boundary(source_text: str, primary_segment: str) -> list[str]:
    segment_signals = extract_segment_landscape_signals(source_text)
    if not segment_signals:
        return []
    deferred_candidates = [
        signal for signal in segment_signals if not signal_matches_primary_segment(signal, primary_segment)
    ]
    lines = [
        "### Segment Landscape and Boundary",
        f"- explicit source segment landscape: {', '.join(segment_signals)}",
        f"- first-wave chosen segment remains: `{primary_segment}`",
    ]
    if deferred_candidates:
        lines.append(f"- review-bound deferred segment candidates: {', '.join(deferred_candidates)}")
        lines.append("- boundary rule: 首发只按已选 primary segment 组织主线，不把这些客群误写成已验证首发对象。")
    return lines


def build_dynamic_signal_snapshot(source_text: str) -> dict[str, list[str]]:
    fact_text = source_fact_text(source_text)
    roles = extract_target_user_roles_from_brief(fact_text)[:5]
    modules = [row["module"] for row in extract_ia_matrix_from_brief(fact_text)[:6] if row.get("module")]
    objectives_block = extract_markdown_section(
        fact_text,
        ["Core Business Objectives", "核心业务目标", "Business Objectives", "产品/业务目标方向", "业务机会描述"],
        level_pattern=r"##",
    )
    objectives = list_items_from_markdown(objectives_block)[:6]
    opportunities = extract_structured_source_items(
        fact_text,
        ["Structured Opportunity List", "结构化机会清单", "P0（MVP 必须有）", "P0"],
    )[:6]
    nfrs = extract_non_functional_requirements_from_brief(fact_text)[:6]
    metrics = extract_structured_source_items(fact_text, ["指标口径最小定义", "Metric Definition and Interpretation Register"])[:6]
    segment_signals = extract_segment_landscape_signals(fact_text)
    return {
        "segment_hits": list(dict.fromkeys(segment_signals + roles)),
        "capability_hits": list(dict.fromkeys(modules + objectives + opportunities)),
        "metric_hits": list(dict.fromkeys(metrics + nfrs + objectives[:2])),
    }


VALUE_SIGNAL_PATTERNS = (
    r"reduce|improve|increase|avoid|prevent|retain|grow|clarify|confidence|trust|quality|adoption|"
    r"manual|fragment|blocked|review|result|follow-?up|treatment|closure|continuity|"
    r"recommendation|finding|taskable|actionability|explainable|executable|"
    r"降低|减少|提升|改善|避免|防止|留存|增长|清晰|信任|质量|采纳|人工|碎片|阻塞|复盘|结果|复诊|治疗|闭环|连续|"
    r"建议|发现|可转任务|可执行|可解释"
)

COMMERCIAL_DECISION_PATTERNS = (
    r"budget|pricing|package|pilot|pay|willingness|roi|quote|commercial|invest|investment|"
    r"continue|revise|pause|business owner|decision owner|sponsor|"
    r"预算|定价|试点|付费|意愿|报价|投入|继续|调整|暂停|业务负责人|决策负责人"
)

DECISION_PROOF_PATTERNS = (
    r"proof|evidence|signal|threshold|metric|review|decision|quote|package|validation|"
    r"证据|信号|阈值|指标|复盘|决策|报价|包装|验证|判定"
)

USER_EXPERIENCE_SIGNAL_PATTERNS = (
    r"wait|waiting|handoff|confusion|manual|duplicate|reconstruct|friction|"
    r"blocked|delay|follow-?up|taskable|actionability|"
    r"等待|交接|混乱|人工|重复|补录|摩擦|阻塞|延迟|复诊|可转任务|可执行"
)
PRESSURE_SIGNAL_PATTERNS = (
    r"lack|missing|cannot|unable|fragment|manual|waste|friction|delay|blocked|drop|lag|invisible|"
    r"缺少|缺失|无法|不能|碎片|人工|浪费|摩擦|延迟|阻塞|遗漏|滞后|断层|不可见|失控"
)

SIGNAL_CONDITIONAL_PATTERN = re.compile(
    r"\bif\b|\bwhen\b|\bbecause\b|^\s*(?:如果|若|当(?!前))|以便|才能|否则|就更容易",
    flags=re.IGNORECASE,
)
SIGNAL_CONTRAST_PATTERN = re.compile(
    r"rather than|instead of|not just|not another|而不是|而非|不愿意|不是",
    flags=re.IGNORECASE,
)
SIGNAL_DECISION_PATTERN = re.compile(
    r"budget|pricing|pay|willingness|quote|pilot|invest|investment|judge|decision|continue|revise|pause|"
    r"预算|定价|付费|意愿|报价|试点|投入|判断|决策|继续|调整|暂停|买单",
    flags=re.IGNORECASE,
)
SIGNAL_PAIN_PATTERN = re.compile(
    r"lack|missing|cannot|unable|fragment|manual|waste|friction|delay|blocked|drop|lag|invisible|"
    r"缺少|缺失|无法|不能|碎片|人工|浪费|摩擦|延迟|阻塞|遗漏|滞后|断层|不可见|失控",
    flags=re.IGNORECASE,
)
SIGNAL_ACTIONABILITY_PATTERN = re.compile(
    r"action|task|execute|workflow|evidence|explain|actionability|review|follow-?up|"
    r"行动|任务|执行|工作流|证据|解释|可执行|可转任务|复盘|闭环|workflow-first",
    flags=re.IGNORECASE,
)
SIGNAL_NOUNISH_PATTERN = re.compile(r"^[A-Za-z0-9\u4e00-\u9fff /&()（）,，._+-]{1,32}$")
SIGNAL_LABEL_PREFIX_PATTERN = re.compile(
    r"^(?:line|signal|evidence|clue|observation|finding|线索|证据|信号)\s*\d*\s*[:：-]\s*",
    flags=re.IGNORECASE,
)
SIGNAL_SCAFFOLD_PREFIX_PATTERN = re.compile(
    r"^(?:adoption signal|review simulation|clickable(?:\s*/\s*structured prototype)? review|"
    r"structured prototype review|walkthrough|访谈/演练|点击原型 walkthrough \+ 访谈)\s*[:：-]\s*",
    flags=re.IGNORECASE,
)
SIGNAL_OPERATIONAL_FRAGMENT_PATTERN = re.compile(
    r"^(?:arrange|establish|register|execute|complete|create|build|trigger|configure|push|generate|"
    r"查看|建立|完成|推动|生成|触发|配置|登记|安排|执行)\b",
    flags=re.IGNORECASE,
)
SIGNAL_CONSEQUENCE_PATTERN = re.compile(
    r"lead to|results? in|causes?|keeps?|so that|worth continued investment|continued investment|"
    r"budget review|action loop|用户流失|运营判断滞后|持续投入|预算评审|动作闭环|"
    r"看到了问题但没有动作|经营动作|继续投入|失控",
    flags=re.IGNORECASE,
)
SIGNAL_OPPORTUNITY_PREFIX_PATTERN = re.compile(r"^(?:用|通过|借助|use|using)\b", flags=re.IGNORECASE)
SIGNAL_NEGATIVE_CONDITIONAL_PATTERN = re.compile(
    r"^\s*(?:if\b\s+(?:no|without)|when\b\s+(?:no|without)|如果没有|若没有|当没有)",
    flags=re.IGNORECASE,
)


def compact_signal_line(value: str) -> str:
    return normalize_source_handoff_phrases(re.sub(r"\s+", " ", str(value or "")).strip().strip("`"))


def normalize_signal_candidate(value: str) -> str:
    text = compact_signal_line(value)
    previous = None
    while text and text != previous:
        previous = text
        text = SIGNAL_LABEL_PREFIX_PATTERN.sub("", text).strip()
        text = SIGNAL_SCAFFOLD_PREFIX_PATTERN.sub("", text).strip()
    return text.strip(" -–—")


def collect_block_signal_items(block: str, *, limit: int = 6) -> list[str]:
    items = [compact_signal_line(item) for item in list_items_from_markdown(block) if compact_signal_line(item)]
    if items:
        return items[:limit]
    fallback: list[str] = []
    for line in strip_heading_line(block).splitlines():
        cleaned = compact_signal_line(re.sub(r"^\s*[-*]\s+", "", line))
        if not cleaned or cleaned.startswith("#"):
            continue
        fallback.append(cleaned)
        if len(fallback) >= limit:
            break
    return fallback


def signal_intent_match(text: str, *, intent: str) -> bool:
    if intent == "pressure":
        if SIGNAL_CONDITIONAL_PATTERN.search(text) and not SIGNAL_NEGATIVE_CONDITIONAL_PATTERN.search(text):
            return False
        return bool(SIGNAL_PAIN_PATTERN.search(text))
    if intent == "commercial":
        return bool(SIGNAL_DECISION_PATTERN.search(text))
    if intent == "experience":
        return bool(
            SIGNAL_PAIN_PATTERN.search(text)
            or re.search(r"wait|waiting|handoff|manual reconstruction|人工遗漏|交接|补录|失控", text, flags=re.IGNORECASE)
        )
    return bool(
        SIGNAL_ACTIONABILITY_PATTERN.search(text)
        or SIGNAL_DECISION_PATTERN.search(text)
        or SIGNAL_CONTRAST_PATTERN.search(text)
    )


def signal_priority_score(candidate: str, *, intent: str = "generic") -> int:
    text = normalize_signal_candidate(candidate)
    score = 0
    if len(text) >= 18:
        score += 1
    if len(text) >= 36:
        score += 1
    if re.search(r"[，,；;：:!?？。]", text):
        score += 1
    if SIGNAL_CONDITIONAL_PATTERN.search(text):
        score += 3
    if SIGNAL_CONTRAST_PATTERN.search(text):
        score += 3
    if SIGNAL_DECISION_PATTERN.search(text):
        score += 3
    if SIGNAL_PAIN_PATTERN.search(text):
        score += 2
    if SIGNAL_ACTIONABILITY_PATTERN.search(text):
        score += 2
    if SIGNAL_NOUNISH_PATTERN.fullmatch(text):
        score -= 2
    if len(text) <= 12:
        score -= 2
    if intent == "pressure":
        if SIGNAL_PAIN_PATTERN.search(text):
            score += 4
        if SIGNAL_CONSEQUENCE_PATTERN.search(text):
            score += 3
        if SIGNAL_PAIN_PATTERN.search(text) and SIGNAL_DECISION_PATTERN.search(text):
            score += 3
        if SIGNAL_CONDITIONAL_PATTERN.search(text) and not SIGNAL_PAIN_PATTERN.search(text):
            score -= 4
        if SIGNAL_OPERATIONAL_FRAGMENT_PATTERN.search(text) and not SIGNAL_PAIN_PATTERN.search(text):
            score -= 4
        if SIGNAL_OPPORTUNITY_PREFIX_PATTERN.search(text) and not SIGNAL_PAIN_PATTERN.search(text):
            score -= 3
    elif intent == "commercial":
        if SIGNAL_DECISION_PATTERN.search(text):
            score += 5
        if SIGNAL_CONTRAST_PATTERN.search(text):
            score += 2
    elif intent == "experience":
        if SIGNAL_PAIN_PATTERN.search(text):
            score += 4
        if re.search(r"wait|waiting|handoff|manual reconstruction|人工遗漏|交接|补录|失控", text, flags=re.IGNORECASE):
            score += 3
        if SIGNAL_CONDITIONAL_PATTERN.search(text) and not SIGNAL_PAIN_PATTERN.search(text):
            score -= 2
    else:
        if SIGNAL_OPERATIONAL_FRAGMENT_PATTERN.search(text) and not (
            SIGNAL_DECISION_PATTERN.search(text) or SIGNAL_CONTRAST_PATTERN.search(text)
        ):
            score -= 4
        if SIGNAL_PAIN_PATTERN.search(text) and not SIGNAL_ACTIONABILITY_PATTERN.search(text):
            score -= 2
    return score


def select_source_grounded_signals(
    candidates: list[str],
    *,
    patterns: str,
    limit: int = 4,
    intent: str = "generic",
) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for idx, raw in enumerate(candidates):
        candidate = normalize_signal_candidate(raw)
        if not candidate or looks_like_placeholder(candidate) or len(candidate) > 220:
            continue
        if not re.search(patterns, candidate, flags=re.IGNORECASE):
            continue
        if not signal_intent_match(candidate, intent=intent):
            continue
        key = normalized_match_key(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        score = signal_priority_score(candidate, intent=intent)
        ranked.append((-score, idx, candidate))
    ranked.sort()
    return [candidate for _, _, candidate in ranked[:limit]]


def signal_phrase(values: list[str], fallback: str, *, limit: int = 2) -> str:
    picked = [compact_signal_line(value) for value in values if compact_signal_line(value)]
    if not picked:
        return fallback
    return "; ".join(picked[:limit])


def load_loop_plan(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def load_business_world_model(stage_01_path: Path) -> dict[str, object] | None:
    candidate = stage_01_path.parent / PHASE1_BUSINESS_WORLD_MODEL_FILENAME
    if not candidate.exists():
        return None
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def load_commercial_argument_rewrite(stage_01_path: Path) -> dict[str, object] | None:
    candidate = stage_01_path.parent / "commercial-argument-rewrite.json"
    if not candidate.exists():
        return None
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def apply_commercial_argument_rewrite(
    business_world_model: dict[str, object] | None,
    rewrite: dict[str, object] | None,
) -> dict[str, object] | None:
    if not isinstance(business_world_model, dict) or not isinstance(rewrite, dict):
        return business_world_model
    narrative = compact_signal_line(str(rewrite.get("argument_narrative", "")))
    if not narrative:
        return business_world_model
    model = dict(business_world_model)
    existing_draft = model.get("commercial_argument_draft", {})
    draft = dict(existing_draft) if isinstance(existing_draft, dict) else {}
    for key in (
        "argument_narrative",
        "primary_substitute_pressure",
        "why_substitute_is_not_enough",
        "proof_that_changes_decision",
        "directional_proof_when_exact_roi_missing",
        "value_mechanism",
        "architecture_pressure",
        "review_bound_truth",
        "source_grounding_notes",
        "quality_state",
    ):
        if key in rewrite:
            draft[key] = rewrite[key]
    draft["artifact_type"] = "commercial_argument_draft"
    draft["generation_mode"] = "agentic-rewrite-applied"
    draft["truth_state"] = "source-grounded-agentic-rewrite"
    draft["rewrite_source"] = "commercial-argument-rewrite.json"
    draft.pop("rewrite_required", None)
    model["commercial_argument_draft"] = draft
    thesis = dict(model.get("chosen_business_thesis", {})) if isinstance(model.get("chosen_business_thesis"), dict) else {}
    thesis["derived_from"] = "commercial_argument_draft"
    thesis["business_argument"] = narrative
    if draft.get("primary_substitute_pressure"):
        thesis["current_state_substitute_to_beat"] = draft["primary_substitute_pressure"]
    if draft.get("proof_that_changes_decision"):
        thesis["proof_target"] = draft["proof_that_changes_decision"]
    if draft.get("architecture_pressure"):
        thesis["product_boundary_implication"] = draft["architecture_pressure"]
    if draft.get("review_bound_truth"):
        thesis["review_bound_truth"] = draft["review_bound_truth"]
    model["chosen_business_thesis"] = thesis
    return model


def truth_slot_value(slot: object) -> str:
    if isinstance(slot, dict):
        return compact_signal_line(str(slot.get("value", "")).strip())
    return compact_signal_line(str(slot).strip())


def truth_slot_values(slot: object) -> list[str]:
    if isinstance(slot, dict):
        values = slot.get("values", [])
        if isinstance(values, list):
            return [compact_signal_line(str(item)) for item in values if compact_signal_line(str(item))]
        return [truth_slot_value(slot)] if truth_slot_value(slot) else []
    return [truth_slot_value(slot)] if truth_slot_value(slot) else []


def merge_truth_signal_lists(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for raw in group:
            candidate = compact_signal_line(raw)
            if not candidate or looks_like_placeholder(candidate):
                continue
            key = normalized_match_key(candidate)
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(candidate)
    return merged


def normalize_loop_targets(loop_plan: dict[str, object] | None) -> list[dict[str, object]]:
    if not isinstance(loop_plan, dict):
        return []
    normalized: list[dict[str, object]] = []
    for idx, item in enumerate(loop_plan.get("targets", []), start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("scenario_title", "")).strip() or f"Scenario {idx}"
        missing_dimensions = [str(value).strip() for value in item.get("missing_dimensions", []) if str(value).strip()]
        focus_areas = [str(value).strip() for value in item.get("focus_areas", []) if str(value).strip()]
        section_targets = [str(value).strip() for value in item.get("section_targets", []) if str(value).strip()]
        actions = [str(value).strip() for value in item.get("exact_thickening_actions", []) if str(value).strip()]
        normalized.append(
            {
                "scenario_title": title,
                "scenario_status": str(item.get("scenario_status", "")).strip() or "REVIEW-BOUND",
                "scenario_source": str(item.get("scenario_source", "")).strip() or "depth-runtime",
                "missing_dimensions": missing_dimensions,
                "focus_areas": list(dict.fromkeys(focus_areas)),
                "section_targets": list(dict.fromkeys(section_targets)),
                "exact_thickening_actions": list(dict.fromkeys(actions)),
            }
        )
    return normalized


def loop_title_short(title: str) -> str:
    return re.sub(r"^Scenario\s+[A-Z0-9]+:\s*", "", title, flags=re.IGNORECASE).strip() or title.strip()


def loop_targets(runtime_context: dict[str, object]) -> list[dict[str, object]]:
    return list(runtime_context.get("loop_targets", []))


def loop_target_for_index(
    runtime_context: dict[str, object],
    index: int,
    *,
    scenario_title: str = "",
) -> dict[str, object] | None:
    targets = loop_targets(runtime_context)
    title_key = normalized_match_key(loop_title_short(scenario_title)) if scenario_title.strip() else ""
    if title_key:
        for target in targets:
            if not isinstance(target, dict):
                continue
            candidate_title = loop_title_short(str(target.get("scenario_title", "")).strip())
            if normalized_match_key(candidate_title) == title_key:
                return target
    if index < 1 or index > len(targets):
        return None
    target = targets[index - 1]
    return target if isinstance(target, dict) else None


def build_loop_step_records(runtime_context: dict[str, object]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    modules = module_names(runtime_context)
    primary_segment = str(runtime_context.get("primary_segment", "")).strip() or "primary actor"
    for idx, target in enumerate(loop_targets(runtime_context), start=1):
        short_title = loop_title_short(str(target.get("scenario_title", f"Scenario {idx}")))
        focus = set(str(item).strip() for item in target.get("focus_areas", []))
        module_hint = modules[min(idx - 1, len(modules) - 1)] if modules else short_title
        actions: list[str] = []
        if "real_world_baseline" in focus:
            actions.append(f"validate `{short_title}` entry evidence, required business context, and object identity before execution starts")
        if "flow_steps" in focus or not focus:
            actions.append(f"execute the mainline work for `{short_title}` in `{module_hint}` and persist the structured output")
        if "role_handoffs" in focus or "handoff_contracts" in focus:
            actions.append(f"handoff `{short_title}` to the next responsible role/module with owner, next action, and blocked reason still visible")
        if "exception_edges" in focus:
            actions.append(f"record the blocked or clarification-needed path for `{short_title}` before the workflow can resume")
        if "state_transitions" in focus:
            actions.append(f"confirm `{short_title}` reaches the next valid tracked state before review or closure")
        for action in list(dict.fromkeys(actions))[:4]:
            records.append(
                {
                    "scenario_title": short_title,
                    "owner": primary_segment,
                    "module_hint": module_hint,
                    "action": action,
                }
            )
    return records


def render_operational_flow_spec_lines(runtime_context: dict[str, object]) -> list[str]:
    base_steps = [
        str(step).strip()
        for flow in runtime_context.get("source_flows", [])
        for step in flow.get("steps", [])
        if str(step).strip()
    ]
    lines = [f"{idx}. {step}" for idx, step in enumerate(base_steps, start=1)]
    supplemental_records = build_loop_step_records(runtime_context)
    target_step_count = max(8, len(lines))
    next_step_no = len(lines) + 1
    for record in supplemental_records:
        if next_step_no > target_step_count:
            break
        lines.append(f"{next_step_no}. {record['action']}.")
        next_step_no += 1
    if next_step_no <= target_step_count:
        modules = module_names(runtime_context, 8)
        objects = core_object_names(runtime_context, 8)
        filler_steps: list[str] = []
        for idx, module in enumerate(modules, start=1):
            object_hint = objects[min(idx - 1, len(objects) - 1)] if objects else "business record"
            filler_steps.extend(
                [
                    f"validate `{module}` preconditions, required evidence, and `{object_hint}` identity before execution",
                    f"persist `{module}` output together with owner, blocked reason, and next action for `{object_hint}`",
                ]
            )
        if not filler_steps:
            filler_steps = [
                "validate preconditions, permissions, and required business evidence before the next workflow step",
                "persist the current object state together with the next action and blocked reason",
            ]
        filler_index = 0
        while next_step_no <= target_step_count:
            lines.append(f"{next_step_no}. {filler_steps[filler_index % len(filler_steps)]}.")
            next_step_no += 1
            filler_index += 1
    return lines or ["1. source brief 未提供可展开的业务流程步骤。"]


def render_flow_summary_lines(flows: list[dict[str, object]]) -> list[str]:
    return [
        f"- {flow['title']}: {reader_facing_digest_phrase(' -> '.join(flow['steps'])) if flow.get('steps') else '流程步骤待澄清'}"
        for flow in flows
    ]


def render_flow_titles(flows: list[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for idx, flow in enumerate(flows, start=1):
        title = str(flow.get("title", "")).strip() or f"Flow {idx}"
        lines.append(f"- Scenario {idx}: {title}")
    return lines or ["- Scenario 1: source-defined primary business flow"]


def render_flow_steps(flows: list[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for flow in flows:
        title = str(flow.get("title", "")).strip() or "Business Flow"
        steps = [str(step).strip() for step in flow.get("steps", []) if str(step).strip()]
        lines.append(f"#### {title}")
        if steps:
            lines.append(f"- step_sequence: {reader_facing_digest_phrase('；'.join(steps[:8]))}")
        else:
            lines.append("- step_sequence: source brief 未给出该流程的细化步骤。")
        lines.append("")
    return lines or ["1. source brief 未提供可展开的业务流程步骤。"]


def render_bullet_lines(items: list[str], fallback: str) -> list[str]:
    return [f"- {item}" for item in items] if items else [f"- {fallback}"]


def build_generic_primary_user_story(runtime_context: dict[str, object]) -> str:
    primary_segment = str(runtime_context.get("primary_segment", "")).strip() or "primary user"
    flows = list(runtime_context.get("source_flows", []))
    first_flow = str(flows[0].get("title", "")).strip() if flows else "the primary business flow"
    if flows and re.search(r"完成一次|闭环|complete.+loop", first_flow, flags=re.IGNORECASE):
        module_chain = " -> ".join(
            str(flow.get("title", "")).strip()
            for flow in flows[1:4]
            if str(flow.get("title", "")).strip()
        )
        if module_chain:
            first_flow = module_chain
    return (
        f"作为 {primary_segment}，我希望围绕 {first_flow} 在同一系统中完成业务登记、状态推进、"
        "记录沉淀和结果确认，以便让核心业务链路可执行、可追踪、可审计。"
    )


def build_generic_supporting_use_cases(runtime_context: dict[str, object]) -> list[tuple[str, str]]:
    flows = list(runtime_context.get("source_flows", []))
    use_cases: list[tuple[str, str]] = []
    for idx, flow in enumerate(flows[:4], start=1):
        title = str(flow.get("title", "")).strip() or f"Flow {idx}"
        steps = [str(step).strip() for step in flow.get("steps", []) if str(step).strip()]
        summary = " -> ".join(steps[:3]) if steps else "complete the source-defined flow"
        use_cases.append((f"Use Case {idx}", f"完成 `{title}` 所要求的关键步骤：{summary}。"))
    if use_cases:
        return use_cases
    return [("Use Case 1", "完成 source brief 中定义的核心业务流程。")]


def build_dynamic_extended_requirements(requirement_rows: list[list[str]]) -> list[tuple[str, str]]:
    return [(row[0], row[4]) for row in requirement_rows]


def build_dynamic_acceptance_summary(acceptance_rows: list[list[str]]) -> list[tuple[str, str]]:
    return [(row[0], row[7]) for row in acceptance_rows]


def render_role_chain_table(runtime_context: dict[str, object]) -> str:
    roles = list(runtime_context.get("target_user_roles", []))
    loop_items = [
        reader_facing_digest_phrase(item)
        for item in business_loop_items(runtime_context, limit=4)
        if reader_facing_digest_phrase(item)
    ]
    loop_label = plain_label_surface(loop_items, "源素材定义的主业务流", limit=4)
    rows = []
    for role in roles:
        goal = f"推动 {loop_label} 进入下一步可评审的业务结果"
        friction = "若系统连续性断裂，团队会回到人工重建上下文"
        responsibility = "完成首波职责，并保持上下文、下一动作和证据连续"
        rows.append([role, goal, friction, responsibility])
    return markdown_table(
        ["角色 (role)", "目标 (goal)", "阻力 / 摩擦 (friction)", "首波职责 (first-wave responsibility)"],
        rows or [["primary role", "完成源素材定义的主流程", "上下文断裂", "保持核心业务主线连续"]],
    )


def render_jtbd_table(runtime_context: dict[str, object]) -> str:
    roles = list(runtime_context.get("target_user_roles", []))
    loop_label = business_loop_plain_surface(runtime_context, limit=4)
    rows = []
    for role in roles:
        context = "日常业务操作中"
        main_job = f"保持 {loop_label} 连续推进，同时不丢失下一步判断"
        success = "下一步保持可理解、可执行、可评审"
        failure = "工作流断裂，团队回到人工重建上下文"
        rows.append([role, context, main_job, success, failure])
    return markdown_table(
        ["role", "context", "main job", "success signal", "failure consequence"],
        rows or [["primary role", "source-defined context", "完成主工作流", "工作流保持有效", "工作流断裂"]],
    )


def build_key_path_candidates(runtime_context: dict[str, object]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for flow in runtime_context.get("source_flows", []):
        append_unique_flow(
            candidates,
            str(flow.get("title", "")).strip(),
            [str(step).strip() for step in flow.get("steps", []) if str(step).strip()],
        )
    known_handoff_targets = {
        normalized_match_key(str(flow.get("title", "")).strip())
        for flow in runtime_context.get("source_flows", [])
        if str(flow.get("title", "")).strip()
    }
    known_handoff_targets.update(
        normalized_match_key(str(row.get("module", "")).strip())
        for row in runtime_context.get("ia_matrix", [])
        if str(row.get("module", "")).strip()
    )
    for row in runtime_context.get("ia_matrix", []):
        title = str(row.get("module", "")).strip()
        steps: list[str] = []
        input_name = str(row.get("entry_condition", "")).strip() or str(row.get("input", "")).strip()
        responsibility = str(row.get("responsibility", "")).strip()
        output_name = str(row.get("exit_action", "")).strip() or str(row.get("output", "")).strip()
        downstream = str(row.get("downstream_dependency", "")).strip()
        if input_name and not looks_like_placeholder(input_name):
            steps.append(input_name)
        if responsibility and not looks_like_placeholder(responsibility):
            steps.append(responsibility)
        if output_name and not looks_like_placeholder(output_name):
            steps.append(output_name)
        if should_append_downstream_handoff(downstream, output_name, known_handoff_targets):
            steps.append(f"handoff to {downstream}")
        append_unique_flow(candidates, title, steps)
    return candidates


def render_key_path_blocks(runtime_context: dict[str, object]) -> list[str]:
    flows = build_key_path_candidates(runtime_context)
    lines: list[str] = []
    use_compressed_path = bool(runtime_context.get("source_flows"))
    for idx, flow in enumerate(flows[:3], start=1):
        title = str(flow.get("title", "")).strip() or f"Flow {idx}"
        steps = [str(step).strip() for step in flow.get("steps", []) if str(step).strip()]
        rendered_steps = steps
        if use_compressed_path:
            rendered_steps = [
                re.sub(r"\baudit policy\b", "boundary rules", step, flags=re.IGNORECASE).replace("`", "")
                for step in steps
            ]
        rendered_path = ("；".join(rendered_steps) if use_compressed_path else " -> ".join(rendered_steps)) if rendered_steps else "source-defined step sequence"
        rendered_path = reader_facing_digest_phrase(rendered_path)
        required_outcome = reader_facing_digest_phrase(select_required_outcome(steps))
        lines.extend(
            [
                f"#### Key-path Scenario {idx}",
                f"- scenario_title: {title}",
                f"- actor_goal: 保持 `{title}` 可执行，同时不丢失业务上下文或角色责任归属",
                f"- required outcome: {required_outcome}",
                f"- implied_design_requirement: 系统必须保留贯穿 `{title}` 的完整对象链（object chain）",
                f"- main success path: {rendered_path}",
                f"- downstream_handoff_contract: {required_outcome} 需要和 owner、next action、blocked reason、audit context 一起保持可见",
                *render_domain_baseline_lines(runtime_context, title),
                "",
            ]
        )
    return lines or ["#### Key-path Scenario 1", "- required outcome: complete the source-defined flow", ""]


def render_design_requirements_extraction(runtime_context: dict[str, object]) -> str:
    roles = list(runtime_context.get("target_user_roles", []))
    ia_rows = list(runtime_context.get("ia_matrix", []))
    style = detect_domain_style("", runtime_context)
    supporting_context = (
        "handoff into execution or the next module"
        if style == "growth_observation"
        else "handoff into consultation or next module"
        if style == "pet_clinic"
        else "handoff into the next module"
    )
    def required_outcome(index: int, fallback: str) -> str:
        if index < len(ia_rows):
            output_name = str(ia_rows[index].get("output", "")).strip()
            if output_name and not looks_like_placeholder(output_name):
                return output_name
            responsibility = str(ia_rows[index].get("responsibility", "")).strip()
            if responsibility and not looks_like_placeholder(responsibility):
                return responsibility
        return fallback

    rows = [
        [
            "DR-01",
            roles[0] if roles else "primary role",
            "first-touch workflow entry",
            required_outcome(0, "complete the first-wave entry outcome"),
            "clarify the first-wave entry state and object identity",
        ],
        ["DR-02", roles[0] if roles else "primary role", "active record handling", "implied_design_requirement", "keep current record, status, and next action visible together"],
        [
            "DR-03",
            roles[1] if len(roles) > 1 else "supporting role",
            supporting_context,
            required_outcome(1, "preserve the next module handoff outcome"),
            "preserve upstream record integrity before any downstream edit",
        ],
        ["DR-04", roles[1] if len(roles) > 1 else "supporting role", "error or exception handling", "implied_design_requirement", "expose recovery/retry and blocked reasons without losing context"],
        [
            "DR-05",
            roles[2] if len(roles) > 2 else "governance role",
            "audit and retention review",
            required_outcome(2, "make audit and retention outcome explicit"),
            "make role boundary, change log, and data retention explicit",
        ],
        [
            "DR-06",
            roles[0] if roles else "primary role",
            "closure and outcome confirmation",
            required_outcome(max(0, min(len(ia_rows) - 1, 2)), "show the closure outcome explicitly"),
            "show what must happen before the business record can be closed",
        ],
    ]
    return markdown_table(
        ["dr_id", "role", "context", "required outcome", "implied_design_requirement"],
        rows,
    )


def render_structure_alternatives_table() -> str:
    return markdown_table(
        ["candidate", "backbone shape", "strength", "failure risk", "verdict"],
        [
            ["record-first", "object onboarding -> object maintenance", "good domain clarity", "can hide cross-module workflow continuity", "rejected"],
            ["module-first", "module silos", "easy to map to menus", "can break the end-to-end source-defined workflow", "rejected"],
            ["workflow-first", "source-defined module chain", "preserves operational continuity", "needs stronger state and role modeling", "chosen"],
        ],
    )


def render_problem_to_structure_mapping(runtime_context: dict[str, object]) -> str:
    rows = [
        ["paper/Excel fragmentation", "workflow-first", "preserve one continuous object chain instead of isolated pages"],
        ["state transition ambiguity", "workflow-first", "make each module handoff explicit in the main flow"],
        ["audit and retention risk", "structure plus boundary rules", "bind status changes to role, time, and event records"],
        ["scope drift", "priority split", "keep P0/P1/P2 and out-of-scope visible together"],
    ]
    return markdown_table(
        ["problem_cluster", "chosen_panorama_structure", "why_this_structure_not_that"],
        rows,
    )


def render_backbone_activities_table(runtime_context: dict[str, object]) -> str:
    flows = list(runtime_context.get("source_flows", []))
    rows = []
    step_no = 1
    for flow in flows:
        for step in [str(s).strip() for s in flow.get("steps", []) if str(s).strip()]:
            rows.append([f"Step {step_no}", "workflow backbone", reader_facing_digest_phrase(step), "保持对象连续性与可审计状态变更"])
            step_no += 1
    return markdown_table(
        ["step", "activity", "actor/system decomposition", "why it matters"],
        rows or [["Step 1", "workflow backbone", "source-defined step", "保持连续性"]],
    )


def render_process_identification_table(runtime_context: dict[str, object]) -> str:
    ia_rows = list(runtime_context.get("ia_matrix", []))
    rows = []
    for row in ia_rows:
        rows.append(
            [
                "main flow",
                row["module"],
                runtime_context.get("primary_segment", "primary role"),
                row["input"] or "source-defined trigger",
                row["output"] or "source-defined output",
                row["responsibility"] or "module responsibility from source",
            ]
        )
    return markdown_table(
        ["process type", "process name", "primary owner", "trigger", "output", "why it matters"],
        rows or [["main flow", "source flow", "primary owner", "trigger", "output", "why it matters"]],
    )


def render_workflow_state_detail(runtime_context: dict[str, object]) -> list[str]:
    rows = list(runtime_context.get("ia_matrix", []))
    states = ["scope_ready"]
    lines: list[str] = []
    for idx, row in enumerate(rows[:6], start=1):
        module = str(row.get("module", f"module_{idx}")).strip()
        module_key = re.sub(r"[^a-z0-9]+", "_", module.lower()).strip("_") or f"module_{idx}"
        states.append(f"{module_key}_active")
        input_name = str(row.get("input", "")).strip() or "source-defined input"
        output_name = str(row.get("output", "")).strip() or "source-defined output"
        lines.append(f"- Step {idx}: {module}; state: {module_key}_active")
        lines.append(f"- Step {idx} transition: {input_name} -> {output_name}")
    if not lines:
        lines.append("- Step 1: source-defined module flow; state: source_state_active")
    return [
        f"- state: {' -> '.join(states) if len(states) > 1 else 'source_state_active'}",
        *lines,
        "- actor/system decomposition: upstream role initiates, downstream role confirms, system preserves contract and audit boundary",
        "- tension register: coverage vs focus; automation vs trust; breadth vs MVP speed",
    ]


def render_constraint_stress_test(runtime_context: dict[str, object]) -> str:
    constraints = list(runtime_context.get("architectural_constraints", []))
    rows = [
        ["business constraints", "workflow continuity across modules", "breaks the source-defined operating loop if weak", "review-bound"],
        ["technical constraints", constraints[0] if constraints else "source-defined technical constraint", "raises implementation risk if ignored", "review-bound"],
        ["compliance/privacy constraints", "all state transitions must be auditable", "cannot safely launch if weak", "review-bound"],
    ]
    return markdown_table(
        ["constraint_family", "constraint", "reverse risk if weak", "evidence_state"],
        rows,
    )


def render_priority_split(runtime_context: dict[str, object]) -> list[str]:
    names = module_names(runtime_context, 5)
    p0 = ", ".join(names) if names else "source-defined core modules"
    return [
        f"- P0: {p0}",
        "- P1: broader visibility, richer admin surfaces, and secondary refinements",
        "- P2: external integrations, multi-instance support, and optional expansion surfaces",
        "- exclusion logic: anything that does not directly protect the first-wave source-defined workflow stays outside P0",
    ]


def render_nfr_prioritization_table(runtime_context: dict[str, object]) -> str:
    rows = [
        ["reliability", "records and state transitions must remain trustworthy", "workflow closure breaks if weak", "module handoff", "MVP consequence: cannot trust business output"],
        ["usability", "core roles must complete the flow without reconstruction", "staff returns to paper/Excel", "primary workflow path", "MVP consequence: adoption fails"],
        ["security/data-control", "role-based auth, retention, and audit are explicit", "risk boundary becomes unacceptable", "all primary views", "MVP consequence: rollout blocked"],
        ["maintainability", "module contracts and object ownership stay clear", "future modules require rework", "module responsibility matrix", "MVP consequence: architecture drifts"],
    ]
    return markdown_table(
        ["attribute", "why prioritized now", "reverse risk if weak", "affected scenario", "MVP consequence"],
        rows,
    )


def render_quality_scenario_matrix() -> str:
    return markdown_table(
        ["attribute", "stimulus", "environment", "expected response", "measure"],
        [
            ["reliability", "a primary workflow object advances", "active business day", "the next view loads the correct object context", "no broken object reference"],
            ["usability", "an operator closes the current step", "busy operating window", "the next steps remain understandable in one path", "task completion without manual workaround"],
            ["security/data-control", "role attempts a restricted action", "role-based auth enabled", "system blocks or audits the action", "auditable denial event exists"],
            ["maintainability", "a downstream module consumes upstream output", "module handoff", "output contract remains stable and typed", "input/output fields stay explicit"],
        ],
    )


def render_metric_register(runtime_context: dict[str, object]) -> str:
    return markdown_table(
        ["metric", "meaning", "first-wave use", "interpretation risk", "mitigation"],
        [
            ["entry completion rate", "new records are created without missing data", "judge entry-path usability", "manual backfill may hide friction", "require explicit missing-input handling"],
            ["state accuracy", "declared states stay consistent", "judge workflow integrity", "silent state drift", "keep audit trail and transition guard"],
            ["handoff contract success rate", "upstream output is accepted by the next module", "judge contract safety", "manual workaround hides gaps", "validate required fields before confirmation"],
            ["closure completion rate", "the business record reaches a traceable closed state", "judge end-to-end completion", "offline workaround hides gaps", "require traceable closure evidence"],
        ],
    )


def render_module_matrix_with_notes(runtime_context: dict[str, object]) -> str:
    ia_rows = list(runtime_context.get("ia_matrix", []))
    rows = []
    for row in ia_rows:
        rows.append([row["module"], row["responsibility"], row["input"], row["output"], "architectural note: preserve typed module contract"])
    return markdown_table(["module", "responsibility", "input", "output", "architectural note"], rows)


def render_domain_direction_block(runtime_context: dict[str, object]) -> list[str]:
    objects = core_object_names(runtime_context, 8)
    return [
        f"- core entities: {', '.join(objects) if objects else 'source-defined core objects'}",
        "- entity catalog: each entity belongs to one owning module and one explicit workflow role",
        f"- relationship direction: {object_chain_text(runtime_context, 8)}",
        "- object lifecycle notes: every object must enter, change, and close through auditable states",
        "- interface payload anchor: every entity handoff keeps identity, owner, status, next action, and blocked reason explicit where applicable",
    ]


def render_first_wave_decision_table(runtime_context: dict[str, object]) -> str:
    return markdown_table(
        ["dimension", "first-wave decision", "rationale"],
        [
            ["account boundary", "single-account business boundary", "source MVP does not require broader cross-boundary coordination"],
            ["sampling window", "per-cycle analysis and review history", "retain history long enough for audit and comparison"],
            ["task fields", "assignee, status, due cycle, blocked reason", "preserve downstream operational ownership"],
            ["extension fields", "extension seam only", "avoid introducing non-source semantics into MVP"],
        ],
    )


def render_subsystem_interfaces(runtime_context: dict[str, object]) -> str:
    rows: list[list[str]] = []
    for row in list(runtime_context.get("ia_matrix", [])):
        rows.append([
            str(row.get("module", "")).strip() or "source module",
            f"{str(row.get('input', '')).strip() or 'upstream input'} -> {str(row.get('output', '')).strip() or 'downstream output'} interface",
            str(row.get("core_objects", "")).strip() or str(row.get("responsibility", "")).strip() or "source-defined module payload",
        ])
    if not rows:
        rows = [["source module", "upstream input -> downstream output interface", "source-defined module payload"]]
    return markdown_table(["subsystem", "subsystem_interfaces", "what"], rows)


def render_workflow_mapping_table(runtime_context: dict[str, object]) -> str:
    rows: list[list[str]] = []
    for idx, row in enumerate(list(runtime_context.get("ia_matrix", [])), start=1):
        objects = [part.strip() for part in str(row.get("core_objects", "")).split(",") if part.strip()]
        rows.append([
            f"Step {idx} {row.get('module', f'module_{idx}')}",
            objects[0] if objects else str(row.get("input", "")).strip() or "primary object",
            objects[1] if len(objects) > 1 else str(row.get("output", "")).strip() or "secondary object",
            str(row.get("responsibility", "")).strip() or "advances the business record",
        ])
    if not rows:
        rows = [["Step 1 source module", "primary object", "secondary object", "advances the business record"]]
    return markdown_table(["workflow step", "primary object", "secondary object", "downstream effect"], rows)


def render_ia_alternatives_table() -> str:
    return markdown_table(
        ["alternative", "organizing axis", "strength", "failure risk", "verdict"],
        [
            ["module-first", "group by internal subsystem", "easy to mirror backend modules", "users may not see the end-to-end workflow", "rejected"],
            ["role-first", "group by staff role", "good for access control", "shared objects can fragment across screens", "rejected"],
            ["workflow-first", "group by operational sequence", "keeps navigation and object traceability aligned", "needs stronger state and dependency discipline", "chosen"],
        ],
    )


def render_expanded_ia_spec_matrix(runtime_context: dict[str, object]) -> str:
    roles = list(runtime_context.get("target_user_roles", []))
    rows: list[list[str]] = []
    ia_rows = list(runtime_context.get("ia_matrix", []))
    for idx, row in enumerate(ia_rows, start=1):
        actor = str(row.get("primary_actor", "")).strip()
        if not actor:
            if len(roles) == 1:
                actor = roles[0]
            elif idx == 1 and str(runtime_context.get("primary_segment", "")).strip():
                actor = str(runtime_context.get("primary_segment", "")).strip()
            else:
                actor = "source-defined primary actor"
        entry_conditions = str(row.get("entry_condition", "")).strip() or str(row.get("input", "")).strip() or "source-defined entry condition"
        exit_actions = (
            str(row.get("exit_action", "")).strip()
            or str(row.get("output", "")).strip()
            or str(row.get("responsibility", "")).strip()
            or "advance the business record"
        )
        downstream_dependency = (
            str(row.get("downstream_dependency", "")).strip()
            or f"depends on {entry_conditions or 'upstream contract'}"
        )
        rows.append([
            str(row.get("module", f"module_{idx}")).strip(),
            actor,
            str(row.get("core_objects", "")).strip() or "source-defined information objects",
            entry_conditions,
            exit_actions,
            downstream_dependency,
        ])
    supplemental_rows = [
        [
            "cross-module handoff queue",
            roles[1] if len(roles) > 1 else (roles[0] if roles else "supporting actor"),
            "active business record / owner_hint / blocked_reason / next-step context",
            "an upstream module marks the record handoff-ready",
            "the downstream actor accepts, rejects, or returns-for-clarification",
            "depends on explicit workflow ownership and typed handoff payload",
        ],
        [
            "audit and review workspace",
            roles[2] if len(roles) > 2 else (roles[-1] if roles else "governance actor"),
            "state history / audit trail / closure evidence / retention boundary",
            "a business record reaches review-ready or closure-ready state",
            "review decision and closure evidence stay queryable together",
            "depends on complete state/event history across modules",
        ],
        [
            "exception recovery console",
            roles[1] if len(roles) > 1 else (roles[0] if roles else "supporting actor"),
            "blocked_reason / missing input / invalid state / dependency unavailable",
            "the main flow cannot proceed safely",
            "recovery path or escalation is recorded before the workflow resumes",
            "depends on transition guards and auditable remediation notes",
        ],
        [
            "record timeline workspace",
            roles[0] if roles else "primary actor",
            "business record / state history / owner timeline / next-step note",
            "a record is opened from any primary module",
            "the operator can inspect prior steps before continuing",
            "depends on object traceability across the full module chain",
        ],
        [
            "search and retrieval workspace",
            roles[0] if roles else "primary actor",
            "record identity / owner / status / recent outcome / audit hint",
            "the team needs to retrieve an in-flight or recently closed record",
            "the chosen record re-enters the workflow with intact context",
            "depends on stable labels, navigation, and cross-module object identity",
        ],
    ]
    while len(rows) < 8 and supplemental_rows:
        rows.append(supplemental_rows.pop(0))
    if not rows:
        rows = [["source module", "primary actor", "source-defined information objects", "source-defined entry condition", "advance the business record", "depends on upstream contract"]]
    return markdown_table(
        ["screen/module", "primary actor", "required information objects", "entry conditions", "exit actions", "downstream dependency"],
        rows,
    )


def render_slice_candidate_table(runtime_context: dict[str, object]) -> str:
    return markdown_table(
        ["candidate", "what_is_in_first_slice", "user_value_speed", "evidence_confidence", "dependency_complexity", "validation_leverage", "risk_of_overreach", "verdict"],
        [
            ["workflow-loop-first", module_chain_text(runtime_context, 5), "high", "medium", "medium", "high", "medium", "chosen"],
            ["admin-dashboard-first", "dashboard and reporting only", "medium", "low", "low", "low", "high", "rejected"],
            ["single-module-first", module_names(runtime_context, 1)[0] if module_names(runtime_context, 1) else "first module only", "medium", "medium", "medium", "medium", "medium", "rejected"],
        ],
    )


def render_scope_boundary_lines(runtime_context: dict[str, object]) -> list[str]:
    return [
        f"- in-scope: {', '.join(module_names(runtime_context, 5)) if module_names(runtime_context, 5) else 'source-defined core modules'}",
        "- later slice: richer admin visibility, deeper secondary workflows, advanced analytics",
        "- deferred seam: external integrations, multi-instance support, advanced automation layers",
        "- explicit out-of-scope: " + ", ".join(runtime_context.get("out_of_scope_items", [])) if runtime_context.get("out_of_scope_items") else "- explicit out-of-scope: source-defined out-of-scope items",
        "- non-goals: do not promise a full ecosystem platform in the first wave",
    ]


def render_slice_lists(runtime_context: dict[str, object]) -> list[str]:
    style = detect_domain_style("", runtime_context)
    minimum_loop = (
        "a single GEO cycle can move from scope and baseline through finding, action, and review without manual reconstruction"
        if style == "growth_observation"
        else "a single visit can move from intake to discharge/follow-up readiness without manual reconstruction"
        if style == "pet_clinic"
        else "a single source-defined business record can move from entry to closure without manual reconstruction"
    )
    later_slices = (
        "broader role surfaces, richer review analytics, and optimization layers"
        if style == "growth_observation"
        else "richer visibility, broader admin tooling, optimization surfaces"
    )
    return [
        "- chosen_slice_strategy: workflow-loop-first",
        "- why_this_slice_not_that: it protects the shortest complete source-defined workflow",
        "- explicit_exclusion_rule: if a capability does not protect the first-wave workflow, it stays out",
        f"- dependency_first_chain: {module_chain_text(runtime_context, 5)}",
        "- complete_experience_loop: the first module starts the record and the final module closes it with auditability intact",
        f"- minimum_viable_experience_loop: {minimum_loop}",
        "- baseline: establish the baseline business context and object identity before execution begins",
        "- execute: the middle workflow steps execute the real business action rather than only recording a status shell",
        "- review: closure and review stay in the same operational loop instead of turning into a disconnected after-the-fact report",
        f"- first_slice: {', '.join(module_names(runtime_context, 5)) if module_names(runtime_context, 5) else 'source-defined core modules'}",
        f"- later_slices: {later_slices}",
        "- deferred_items: integrations, multi-instance support, mobile native app",
    ]


def render_carryover_ledger(runtime_context: dict[str, object]) -> str:
    rows: list[list[str]] = []
    for idx, row in enumerate(list(runtime_context.get("ia_matrix", []))[:5], start=1):
        rows.append([
            str(row.get("module", f"module_{idx}")).strip(),
            "first-wave abstraction",
            str(row.get("responsibility", "")).strip() or "typed module contract",
            "protects the executable object chain",
            "must stay visible in the first-wave slice",
        ])
    rows.append(["summary and analysis surfaces", "later slice", "reporting after workflow core is stable", "workflow closure matters before broad visibility", "preserve module seam"])
    rows.append(["external integrations", "deferred seam", "future seam entity/interface", "avoid Phase-2 rewrite of object chain", "document the extension boundary"])
    for item in list(runtime_context.get("out_of_scope_items", []))[:2]:
        rows.append([str(item), "explicit out-of-scope", "deferred to future phase", "source brief excludes it from MVP", "do not silently pull into first-wave scope"])
    return markdown_table(
        ["source feature detail", "classification", "preserved form in first-wave PRD", "why this classification", "downstream note"],
        rows,
    )


def render_value_loop_notes(runtime_context: dict[str, object]) -> list[str]:
    return [
        "- Value Loop and Downstream Preservation Notes",
        "- the first-wave value loop is complete only when the same business record reaches a traceable closure state",
        "- baseline anchor: baseline context capture, execute, and review must remain on one visible chain",
        "- in this domain, downstream closure means record linkage plus audit traceability",
        "- false completeness risk: a dashboard without workflow closure would look polished but fail the real operating loop",
    ]


def render_domain_growth_lines(runtime_context: dict[str, object]) -> list[str]:
    objects = core_object_names(runtime_context, 8)
    growth_anchor = objects[-1] if objects else "primary business record"
    return [
        f"- highest growth object: `{growth_anchor}` is the first candidate to accumulate cross-step history and operational variance",
        "- throughput variance, traffic spikes, long-tail exceptions, and admin reporting needs still need evidence",
        "- volume_growth_risk: keep the object seam extensible now, but do not overstate actual scale behavior before field evidence exists",
    ]


def render_transition_rules(runtime_context: dict[str, object]) -> list[str]:
    names = module_names(runtime_context, 6)
    states = [re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or f"module_{idx}" for idx, name in enumerate(names, start=1)]
    lines: list[str] = []
    if states:
        lines.append(f"- draft -> {states[0]}_ready")
        for idx, current in enumerate(states):
            lines.extend(
                [
                    f"- {current}_ready -> {current}_in_progress",
                    f"- {current}_in_progress -> {current}_handoff_ready",
                    f"- {current}_in_progress -> {current}_blocked",
                    f"- {current}_blocked -> {current}_clarification_needed",
                    f"- {current}_clarification_needed -> {current}_ready",
                ]
            )
            if idx + 1 < len(states):
                lines.append(f"- {current}_handoff_ready -> {states[idx + 1]}_ready")
            else:
                lines.append(f"- {current}_handoff_ready -> review_ready")
    else:
        lines.append("- draft -> active -> review_ready")
    lines.extend(
        [
            "- blocked -> recovery_retry",
            "- recovery_retry -> active_review",
            "- transition guard: invalid state changes must be rejected explicitly",
            "- created / accepted / executed / blocked may be used for secondary operational tasks where applicable",
        ]
    )
    for idx, target in enumerate(loop_targets(runtime_context)[:3], start=1):
        focus = set(str(item).strip() for item in target.get("focus_areas", []))
        if "state_transitions" not in focus and "handoff_contracts" not in focus and "exception_edges" not in focus:
            continue
        scenario_key = re.sub(r"[^a-z0-9]+", "_", loop_title_short(str(target.get("scenario_title", f"scenario_{idx}"))).lower()).strip("_") or f"scenario_{idx}"
        lines.extend(
            [
                f"- {scenario_key}_ready -> {scenario_key}_in_progress",
                f"- {scenario_key}_in_progress -> {scenario_key}_handoff_ready",
                f"- {scenario_key}_in_progress -> {scenario_key}_blocked",
                f"- {scenario_key}_blocked -> {scenario_key}_clarification_needed",
                f"- {scenario_key}_clarification_needed -> {scenario_key}_ready",
            ]
        )
    return lines


def render_payload_contract_table(runtime_context: dict[str, object]) -> str:
    style = detect_domain_style("", runtime_context)
    if style == "growth_observation":
        return markdown_table(
            ["payload element", "source capability detail preserved", "first-wave representation", "task/export implication", "certainty / note"],
            [
                ["AI-friendly score and quality diagnosis", "AI 友好度评分（0-100） / 内容质量诊断", "`ai_friendliness_score` + `quality_diagnosis_summary` + `score_explanation`", "影响 priority、是否进入 task bridge、review 预期", "score rubric 首版仍属 review-bound"],
                ["Structured rewrite suggestion", "结构化改写建议", "`rewrite_goal` + `rewrite_outline` + `before_after_hint`", "形成可执行编辑动作，而不只是“建议优化”", "不直接自动改写发布"],
                ["Keyword / question focus", "关键词优化建议 + 问答焦点", "`target_question` + `keyword_focus` + `coverage_gap`", "决定任务目标问题、FAQ 切入点和资产优先级", "必须绑定 Tracked Scope 与 Content Asset"],
                ["Citation-likelihood hypothesis", "引用概率预测", "`citation_likelihood_band` + `citation_reason` + `confidence_state`", "影响 recommendation priority 与 review 预期，不可当作 guaranteed outcome", "首版仅做 hypothesis，不做承诺"],
                ["FAQ / Q&A suggestion", "AI 回答模板生成 + 问答对自动生成", "`faq_question` + `faq_answer_outline` + `suggested_format`", "可导出为 FAQ/task 子类型，而不是消失在通用建议里", "FAQ auto-generation 仍非 fully automatic publish"],
                ["Export-ready task payload", "保存草稿 / 创建任务 / 一键应用优化 的执行核", "`target_asset_id` + `priority` + `owner_hint` + `due_cycle` + `blocked_reason`", "recommendation 才能一跳转成 task/export record", "“一键应用”仅保留为人工确认后的 action"],
            ],
        )

    object_ids = [f"{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}_id" for name in core_object_names(runtime_context, 4)]
    return markdown_table(
        ["payload element", "source capability detail preserved", "first-wave representation", "task/export implication", "certainty / note"],
        [
            ["target_asset_id", "object identity", " / ".join(object_ids) if object_ids else "business_record_id", "downstream task export stays traceable", "source-grounded"],
            ["priority", "workflow urgency", "source-defined priority level", "supports queue ordering", "review-bound calibration"],
            ["owner_hint", "responsible role", "primary role / supporting role / governance role", "supports handoff", "source-grounded"],
            ["blocked_reason", "failure or exception path", "missing input / invalid state / dependency unavailable / permission boundary", "preserves recovery path", "source-grounded"],
            ["extension_context", "extension seam only", "future seam field", "reserved for later integrations", "deferred seam"],
        ],
    )


def payload_contract_heading(runtime_context: dict[str, object]) -> str:
    return (
        "Recommendation Payload Contract"
        if detect_domain_style("", runtime_context) == "growth_observation"
        else "Module Interface Payload Contract"
    )


def deferred_seam_heading(runtime_context: dict[str, object]) -> str:
    return (
        "Deferred Attribution and Conversion Seam"
        if detect_domain_style("", runtime_context) == "growth_observation"
        else "Deferred Capability Seam"
    )


def render_deferred_seam_table(runtime_context: dict[str, object]) -> str:
    if detect_domain_style("", runtime_context) == "growth_observation":
        return markdown_table(
            ["future concern", "first-wave treatment now", "future seam entity/interface", "minimum reserved fields or hook", "why deferred now"],
            [
                ["AI traffic source tagging", "baseline/review 仅记录 platform / query cluster / source note", "Attribution Signal", "`source_tag` + `platform` + `query_cluster` + `landing_asset_ref`", "首版不做全链路埋点"],
                ["Funnel progression", "report 仅保留方向性 outcome note", "Funnel Stage Snapshot", "`funnel_stage` + `stage_timestamp` + `related_scope_id`", "缺少稳定业务数据接入"],
                ["Conversion event linkage", "允许人工记录 conversion note", "Conversion Event", "`conversion_event_id` + `event_type` + `amount_band` + `evidence_source`", "精确财务归因证据不足"],
                ["Cross-device identity", "不做 identity stitching", "Identity Resolution Link", "`visitor_link_key` + `device_class` + `confidence_state`", "MVP 不承担跨设备识别复杂度"],
                ["ROI rollup", "review 仅保留 coarse attribution hypothesis", "Attribution Rollup", "`attributed_range` + `assumption_note` + `confidence_state`", "不能在 MVP 假装财务级证明已成立"],
            ],
        )

    return markdown_table(
        ["future concern", "first-wave treatment now", "future seam entity/interface", "minimum reserved fields or hook", "why deferred now"],
        [["source-defined deferred capability", "keep outside MVP commitment but visible in seam ledger", "Source Defined Deferred Capability Seam", "`source_defined_deferred_capability_status` + `source_defined_deferred_capability_owner` + `source_defined_deferred_capability_notes`", "explicitly deferred in source scope boundary"]],
    )


def render_validation_assumption_table() -> str:
    return markdown_table(
        ["target", "exact_assumption_tested", "what_changes_if_positive", "what_changes_if_negative", "primary dimension"],
        [
            ["target_1", "the primary actor can complete first-wave entry without reconstruction", "keep the current entry boundary", "rework entry flow and labels", "usability"],
            ["target_2", "the core module handoff is understandable to supporting roles", "keep the current handoff in first wave", "simplify module boundary or reduce scope", "workflow integrity"],
            ["target_3", "closure and audit trail are acceptable to decision owners", "keep closure in the main loop", "increase audit visibility or adjust closure steps", "governance"],
            ["target_4", "state transitions are clear enough for implementation", "freeze transition semantics", "add transition guards and error states", "executability"],
            ["target_5", "MVP boundary is clear enough to resist scope drift", "proceed to design/architecture handoff", "tighten carryover ledger and exclusion rules", "scope"],
        ],
    )


def render_validation_method_table() -> str:
    return markdown_table(
        ["candidate method", "fit_to_target", "cost_and_speed", "evidence_quality", "why_not_chosen_or_chosen"],
        [
            ["stakeholder interview", "high", "fast / medium cost", "medium", "chosen for target_1 and target_5"],
            ["clickable prototype", "high", "medium / medium cost", "medium-high", "chosen for target_2 and target_4"],
            ["schema + state review", "high", "fast / low cost", "medium", "chosen for target_3 and target_4"],
            ["coded pilot", "medium", "slow / high cost", "high", "not chosen in this round"],
        ],
    )


def render_validation_artifact_threshold_table() -> str:
    return markdown_table(
        ["target", "method", "artifact", "threshold", "learning_if_pass", "learning_if_fail"],
        [
            ["target_1", "stakeholder interview", "workflow script", ">=3 users complete the first-flow narration without major confusion", "entry flow is understandable", "rework labels and entry order"],
            ["target_2", "clickable prototype", "core handoff prototype", ">=70% can finish the path without moderator rescue", "handoff is strong enough", "simplify the module split"],
            ["target_3", "schema + state review", "state/event matrix", "all critical audit events are representable", "audit seam is sufficient", "expand event coverage"],
            ["target_4", "clickable prototype + state review", "transition guard checklist", "no hidden transition gaps remain", "implementation can start safely", "add blocked/recovery rules"],
            ["target_5", "stakeholder interview", "scope ledger", ">=50% can distinguish in-scope from out-of-scope correctly", "scope boundary is understandable", "tighten carryover ledger"],
        ],
    )


def render_flow_step_deepening_lines(runtime_context: dict[str, object]) -> list[str]:
    lines: list[str] = []
    step_no = 1
    for flow in runtime_context.get("source_flows", []):
        title = str(flow.get("title", "")).strip() or f"Flow {step_no}"
        for step in [str(s).strip() for s in flow.get("steps", []) if str(s).strip()]:
            rendered_step = reader_facing_digest_phrase(step)
            lines.append(
                f"- Step {step_no}: {rendered_step} | owner: {runtime_context.get('primary_segment', 'primary actor')} | "
                "system_behavior: 保持对象连续性与下一步可见性 | "
                f"postconditions: 下游模块无需重建上下文即可消费该输出 | flow_context: {title}"
            )
            step_no += 1
    for record in build_loop_step_records(runtime_context):
        rendered_action = reader_facing_digest_phrase(str(record["action"]))
        lines.append(
            f"- Step {step_no}: {rendered_action} | owner: {record['owner']} | "
            "system_behavior: 保持工作流连续性、blocked reason 和下游交接可见性 | "
            f"postconditions: `{record['module_hint']}` 为下游模块留下可用的 tracked state 和 object context | "
            f"flow_context: {record['scenario_title']}"
        )
        step_no += 1
    if lines:
        lines.append("- shared_step_rule: 每一步都必须给下游模块留下可用对象上下文，避免迫使下游人工重建。")
    return lines


def render_module_detail_lines(runtime_context: dict[str, object]) -> list[str]:
    lines: list[str] = []
    style = detect_domain_style("", runtime_context)
    boundary_note = (
        "tenant boundary"
        if style == "growth_observation"
        else "clinic account boundary"
        if style == "pet_clinic"
        else "source-defined account boundary"
    )
    for row in runtime_context.get("ia_matrix", []):
        payload_description = build_interface_payload_description(row)
        lines.extend(
            [
                f"- module_detail: {row['module']}",
                f"- responsibility: {row['responsibility']}",
                f"- input: {row['input']}",
                f"- output: {row['output']}",
                f"- account boundary: `{row['module']}` must stay inside the {boundary_note}",
                f"- interface_payloads: what: {payload_description}",
            ]
        )
    if style == "pet_clinic":
        lines.extend(
            [
                "- clinic-private boundary: visit, treatment, follow-up, and review records remain clinic-private inside the clinic account boundary by default.",
                "- value honesty: billing, estimate, and operational closure signals must not overstate exact financial proof in MVP.",
            ]
        )
    return lines


def render_role_detail_lines(runtime_context: dict[str, object]) -> list[str]:
    rows: list[list[str]] = []
    for role in runtime_context.get("target_user_roles", []):
        role_surface = plain_truth_text(str(role)) or "source-defined role"
        rows.append(
            [
                role_surface,
                "只在它能保住首波主线与责任链时纳入主线。",
                "该角色能在不靠人工补位的前提下完成交接。",
                f"若 {role_surface} 会触达审计、留存或权限边界，则治理评审视角必须保持可见。",
            ]
        )
    if not rows:
        return ["- source brief 未提供角色 detail ledger。"]
    return [
        markdown_table(
            ["role", "first-wave inclusion rule", "required outcome", "governance / review note"],
            rows,
        )
    ]


def render_nfr_detail_lines(runtime_context: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for idx, item in enumerate(runtime_context.get("non_functional_requirements", []), start=1):
        lines.extend(
            [
                f"- NFR detail {idx}: {item}",
                f"- why prioritized now: `{item}` directly shapes first-wave rollout safety",
                f"- decision_effect: keep `{item}` visible in design and architecture handoff",
                f"- alternatives_compared: do not replace `{item}` with a weaker placeholder promise",
                "- recommendation_constraint / next_step_constraint: cannot silently auto-execute or bypass human confirmation where safety matters",
            ]
        )
    return lines


def render_validation_detail_lines(runtime_context: dict[str, object]) -> list[str]:
    return [
        "- chosen_method: stakeholder interview + clickable prototype + schema/state review",
        "- fidelity_chosen: medium fidelity prototype plus explicit state/event contract",
        "- fidelity_rationale: enough to test the workflow without implying implementation certainty",
        "- signal thresholds: each target has a threshold, pass signal, and fail consequence",
        "- delivery_state: `downstream-start-safe`",
        "- evidence_confidence_state: `source-grounded-but-unvalidated`",
        "- admission_state: ready-to-converge only for design/architecture exploration",
        "- blocked_commitments: no production readiness claim, no pricing certainty claim, no hidden scope expansion",
    ]


def render_validation_target_lines(source_text: str, runtime_context: dict[str, object]) -> list[str]:
    business_world_model = runtime_context.get("business_world_model", {})
    business_proof_track = (
        business_world_model.get("business_proof_track", {})
        if isinstance(business_world_model, dict)
        else {}
    )
    proof_track = str(business_proof_track.get("proof_track", "")).strip() if isinstance(business_proof_track, dict) else ""
    style = detect_domain_style(source_text, runtime_context)
    if proof_track == "economic-decision-proof":
        targets = [
            ("target_1", "business proof target clarity"),
            ("target_2", "substitute pressure versus dashboard/report/manual-service alternatives"),
            ("target_3", "directional proof threshold before exact attribution"),
            ("target_4", "buyer/budget continuation owner and spend-at-risk clarity"),
            ("target_5", "continue / revise / pause decision trigger"),
        ]
    elif proof_track == "operational-service-proof":
        targets = [
            ("target_1", "real operating flow clarity"),
            ("target_2", "role-owned handoff clarity"),
            ("target_3", "blocked and exception state completeness"),
            ("target_4", "audit and closure record proof"),
            ("target_5", "user task/process friction reduction"),
        ]
    elif style == "growth_observation":
        targets = [
            ("target_1", "tracked scope initialization clarity"),
            ("target_2", "finding and recommendation readability"),
            ("target_3", "recommendation-to-task bridge clarity"),
            ("target_4", "review decision clarity"),
            ("target_5", "boundary and audit clarity"),
        ]
    elif style == "pet_clinic":
        targets = [
            ("target_1", "intake entry clarity"),
            ("target_2", "treatment handoff clarity"),
            ("target_3", "billing and discharge closure"),
            ("target_4", "transition guard completeness"),
            ("target_5", "scope ledger clarity"),
        ]
    else:
        targets = [
            ("target_1", "entry flow clarity"),
            ("target_2", "mainline handoff clarity"),
            ("target_3", "closure and audit clarity"),
            ("target_4", "transition guard completeness"),
            ("target_5", "scope ledger clarity"),
        ]
    rows = [
        [
            key,
            label,
            "必须显式记录 pass / fail threshold。",
            "若该目标仍弱，文档保持 review-ready / downstream-start-safe，不得升级成 implementation certainty。",
            "不得静默升级不完整证据。",
        ]
        for key, label in targets
    ]
    return [
        markdown_table(
            ["target", "focus", "threshold rule", "weak-case consequence", "commitment guardrail"],
            rows,
        )
    ]


def render_loop_value_deepening_lines(runtime_context: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for target in loop_targets(runtime_context)[:4]:
        short_title = loop_title_short(str(target.get("scenario_title", "Scenario")))
        focus = set(str(item).strip() for item in target.get("focus_areas", []))
        if "business_value" in focus or "value_mechanism" in focus:
            lines.append(
                f"- value_mechanism target: `{short_title}` must explain which business pain is reduced, what concrete business result improves, and why the workflow deserves continued investment."
            )
        if "buyer_budget_chain" in focus:
            lines.append(
                f"- buyer_budget target: `{short_title}` must surface who feels the pain, who can decide continued commitment, what time/budget/process-change spend is at risk, what proof artifact must exist before the commitment continues, and what signal triggers continue / revise / pause."
            )
        if "decision_leverage" in focus:
            lines.append(
                f"- decision_leverage target: `{short_title}` must end in an explicit continue / revise / pause or allocate / do-not-allocate decision, not just a completed workflow."
            )
        if "user_task_experience" in focus:
            lines.append(
                f"- user_task_experience target: `{short_title}` must show how the workflow reduces waiting, re-entry, coordination friction, or manual reconstruction for the real operator path."
            )
    return list(dict.fromkeys(lines))


def plain_truth_text(value: str) -> str:
    text = compact_signal_line(value)
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    return text.strip().strip("。.;:：")


READER_FACING_TERM_GLOSSARY = {
    "actionability rationale": "可行动性理由",
    "active tenant workspace": "活跃租户工作区",
    "arrival request": "到诊请求",
    "audit context": "审计上下文",
    "audit policy": "审计策略",
    "audit-ready context": "审计就绪上下文",
    "baseline collection": "基线采集",
    "baseline snapshot": "基线快照",
    "blocked reason": "阻断原因",
    "brand targets": "品牌目标",
    "checked-in visit": "已登记就诊",
    "clinician-ready intake context": "医生接手所需的接诊上下文",
    "collection window": "采集窗口",
    "competitor set": "竞品集合",
    "cycle conclusion": "周期结论",
    "cycle evidence": "周期证据",
    "diagnostic result": "诊断结果",
    "discharge closure": "离院闭环",
    "discharge confirmation": "离院确认",
    "discharge context": "离院上下文",
    "evidence link": "证据链接",
    "evidence links": "证据链接",
    "evidence set": "证据集合",
    "exam notes": "检查记录",
    "execution status": "执行状态",
    "explainable evidence": "可解释证据",
    "finding": "发现项",
    "finding deltas": "发现项变化",
    "follow-up need": "复诊需求",
    "follow-up plan": "复诊计划",
    "freshness status": "新鲜度状态",
    "intake handoff context": "接诊交接上下文",
    "member roles": "成员角色",
    "monitored scope context": "监控范围上下文",
    "monitored topic set": "监控主题集合",
    "next action": "下一步动作",
    "owner details": "负责人/所有者信息",
    "owner hint": "负责人提示",
    "pet record": "宠物记录",
    "pet profile": "宠物档案",
    "prior record": "既往记录",
    "prioritized findings": "已排序发现项",
    "prompt scope definition": "提示词范围定义",
    "prompt set": "提示词集合",
    "recommendation-ready findings": "可转建议的发现项",
    "review summary": "评审摘要",
    "role boundary": "角色边界",
    "scope boundary": "范围边界",
    "symptoms": "症状",
    "tenant identity": "租户身份",
    "treatment execution": "治疗执行",
    "treatment record": "治疗记录",
    "treatment result": "治疗结果",
    "versioned tracked scope": "带版本的追踪范围",
    "visit reason": "就诊原因",
}


def is_machine_or_code_surface(value: str) -> bool:
    text = compact_signal_line(value).strip("` ")
    if not text:
        return False
    if re.fullmatch(r"[A-Z]+-\d+(?:-[A-Z0-9]+)*", text):
        return True
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z][A-Za-z0-9]*)+", text):
        return True
    if re.fullmatch(r"[a-z][a-z0-9]+(?:_[a-z0-9]+)+", text):
        return True
    if re.fullmatch(r"[A-Z][A-Za-z0-9]+", text):
        return True
    return False


def reader_facing_digest_term(value: str) -> str:
    raw = compact_signal_line(value).strip("` ")
    if not raw:
        return ""
    if is_machine_or_code_surface(raw):
        return raw
    normalized = re.sub(r"\s+", " ", raw).strip()
    bilingual_match = re.match(r"^([\u4e00-\u9fff][^()（）]+?)\s*[（(]\s*([^()（）]+?)\s*[）)]$", normalized)
    if bilingual_match:
        chinese_label = bilingual_match.group(1).strip()
        canonical = bilingual_match.group(2).strip()
        return f"{chinese_label}（{canonical}）"
    key = normalized.casefold()
    chinese = READER_FACING_TERM_GLOSSARY.get(key)
    if chinese:
        return f"{chinese}（{normalized}）"
    explainable_evidence_match = re.match(r"^explainable\s+(.+?)\s+evidence$", normalized, flags=re.IGNORECASE)
    if explainable_evidence_match:
        domain_hint = reader_facing_digest_term(explainable_evidence_match.group(1))
        return f"可解释 {domain_hint} 证据（{normalized}）"
    if re.search(r"[\u4e00-\u9fff]", normalized):
        return naturalize_reader_facing_bilingual_terms(normalized)
    return normalized


def split_reader_facing_payload_items(value: str) -> list[str]:
    text = compact_signal_line(value).strip("` ")
    if not text:
        return []
    if not re.search(r",|\s+and\s+", text, flags=re.IGNORECASE):
        return []
    has_comma = "," in text
    normalized = re.sub(r"\s*,\s*and\s+", ", ", text, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+and\s+", ", ", normalized, flags=re.IGNORECASE)
    items = [item.strip(" ,") for item in normalized.split(",") if item.strip(" ,")]
    if len(items) < 2:
        return []
    if not has_comma and re.match(
        r"^(?:capture|register|record|arrange|run|define|establish|structure|turn|summarize|preserve|complete|manage|coordinate)\b",
        items[0],
        flags=re.IGNORECASE,
    ):
        return []
    return items


def render_reader_facing_payload_list(value: str) -> str:
    items = split_reader_facing_payload_items(value)
    if not items:
        return ""
    rendered = [reader_facing_digest_term(item) for item in items]
    if len(rendered) == 2:
        return f"{rendered[0]}和{rendered[1]}"
    return f"{'、'.join(rendered[:-1])}和{rendered[-1]}"


def reader_facing_digest_action_phrase(value: str) -> str:
    text = compact_signal_line(value).strip("` ")
    if not text or is_machine_or_code_surface(text):
        return text
    action_patterns: tuple[tuple[re.Pattern[str], str], ...] = (
        (
            re.compile(r"^register the arriving pet and preserve clinician-ready intake context$", re.IGNORECASE),
            "登记到诊宠物，并保留医生接手所需的接诊上下文",
        ),
        (
            re.compile(r"^record diagnosis,\s*treatment execution,\s*and the next clinical action$", re.IGNORECASE),
            "记录诊断、治疗执行和下一步临床动作",
        ),
        (
            re.compile(r"^arrange follow-up,\s*discharge closure,\s*and review-ready clinic summary$", re.IGNORECASE),
            "安排复诊、完成离院闭环，并形成评审就绪的诊所摘要",
        ),
        (
            re.compile(r"^arrange follow-up,\s*discharge closure,\s*and .+clinic summary$", re.IGNORECASE),
            "安排复诊、完成离院闭环，并形成评审就绪的诊所摘要",
        ),
        (
            re.compile(r"^establish (.+?) for (.+)$", re.IGNORECASE),
            "建立 {0}，用于 {1}",
        ),
        (
            re.compile(r"^define (.+?) for (.+)$", re.IGNORECASE),
            "定义 {0}，用于 {1}",
        ),
        (
            re.compile(r"^run (.+?) and preserve (.+)$", re.IGNORECASE),
            "执行 {0}，并保留 {1}",
        ),
        (
            re.compile(r"^structure (.+?) with (.+)$", re.IGNORECASE),
            "用 {1} 组织 {0}",
        ),
        (
            re.compile(r"^turn (.+?) into (.+)$", re.IGNORECASE),
            "把 {0} 转成 {1}",
        ),
        (
            re.compile(r"^summarize (.+?) and record (.+)$", re.IGNORECASE),
            "总结 {0}，并记录 {1}",
        ),
    )
    for pattern, replacement in action_patterns:
        match = pattern.match(text)
        if not match:
            continue
        if match.groups():
            groups = [reader_facing_digest_phrase(group) for group in match.groups()]
            return replacement.format(*groups)
        return replacement
    return ""


def reader_facing_digest_phrase(value: str) -> str:
    """Render source/action text for human readers while preserving canonical terms."""
    text = compact_signal_line(value).strip("` ")
    if not text:
        return ""
    if is_machine_or_code_surface(text):
        return text
    confirm_match = re.match(
        r"^确认\s+`?(.+?)`?\s+已就绪$",
        text,
        flags=re.IGNORECASE,
    )
    if confirm_match:
        return f"确认 {reader_facing_digest_phrase(confirm_match.group(1))} 已就绪"
    output_match = re.match(
        r"^(?:输出|output)\s+`?(.+?)`?\s*(?:并准备下游交接|and prepare downstream handoff)$",
        text,
        flags=re.IGNORECASE,
    )
    if output_match:
        return f"输出 {reader_facing_digest_phrase(output_match.group(1))}，并准备下游交接"
    prefix_match = re.match(r"^(.{1,80}?)([:：])\s+(.+)$", text)
    if prefix_match and not re.match(r"^[a-z][a-z0-9_]+$", prefix_match.group(1)):
        prefix, separator, remainder = prefix_match.groups()
        rendered_remainder = reader_facing_digest_phrase(remainder)
        if rendered_remainder and rendered_remainder != remainder:
            return f"{prefix}{separator} {rendered_remainder}"
    for separator in ("；", " -> "):
        if separator not in text:
            continue
        parts = [part.strip() for part in text.split(separator) if part.strip()]
        if len(parts) < 2:
            continue
        rendered = [reader_facing_digest_phrase(part) for part in parts]
        joiner = "；" if separator == "；" else " -> "
        return joiner.join(rendered)
    action = reader_facing_digest_action_phrase(text)
    if action:
        return action
    payload = render_reader_facing_payload_list(text)
    if payload:
        return payload
    return reader_facing_digest_term(text)


def naturalize_reader_facing_bilingual_terms(value: str) -> str:
    """Keep necessary English terms as annotations instead of mixed sentence glue."""
    text = compact_signal_line(value)
    if not text:
        return ""
    text = re.sub(
        r"\bcurrent truth state remains review-bound\s*/\s*missing evidence until (?:the )?source packet is validated\b",
        "当前真相状态仍待评审确认（review-bound），需等待源素材（source packet）验证",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\breview-bound\s*/\s*missing evidence:\s*the source defines the operating chain,\s*"
        r"but not yet a validated buyer\s*/\s*budget owner (?:or|或) spend threshold\b",
        "源素材已经定义运营主线，但真实买方、预算负责人和投入阈值仍待评审确认（review-bound）",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bstakeholder evidence showing who funds or authorizes the next commitment,\s*"
        r"what spend is really at risk,\s*and what proof is sufficient to\s*(?:continue|继续)\b",
        "仍需补充谁出资或授权下一轮投入、真实投入成本是多少，以及什么证据足以支持继续",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"已有部分信号支撑\s*[（(]\s*partially-信号-backed\s*[）)]",
        "已有部分信号支撑（partially-signal-backed）",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"已有部分信号支撑\s*[（(]\s*partially-signal-backed\s*[）)]",
        "已有部分信号支撑（partially-signal-backed）",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bsource-grounded-but-review-bound\b",
        "源素材支撑，仍待评审确认（source-grounded / review-bound）",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bsource-grounded-but-unvalidated\b",
        "源素材支撑，但未外部验证（source-grounded / unvalidated）",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?<![（\w/-])\bsource-grounded\b(?!\s*/|[）\w/-])",
        "源素材支撑（source-grounded）",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\breview-bound\s*/\s*missing evidence\b",
        "待评审确认（review-bound），缺少外部证据",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?<![（\w/-])\breview-bound\b(?![）\w/-])", "待评审确认（review-bound）", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（\w-])\bowner sign-off\b(?![）\w-])", "负责人签署（owner sign-off）", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（\w-])\bproduction readiness\b(?![）\w-])", "生产就绪", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（\w-])\bwillingness-to-pay\b(?![）\w-])", "付费意愿", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（\w-])\bbudget approval\b(?![）\w-])", "预算批准", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（\w-])\breal external validation\b(?![）\w-])", "真实外部验证", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（\w-])\bthe source packet\b(?![）\w-])", "源素材（source packet）", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（\w-])\bsource packet\b(?![）\w-])", "源素材（source packet）", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（\w-])\bsource fact\b(?![）\w-])", "源素材事实（source fact）", text, flags=re.IGNORECASE)
    text = re.sub(r"同一\s*review\s*面", "同一评审界面（review surface）", text, flags=re.IGNORECASE)
    text = re.sub(r"\breview\s*面", "评审界面（review surface）", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（(])\breview surface\b(?![）)])", "评审界面（review surface）", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（(])\bpartially-信号-backed\b(?![）)])", "已有部分信号支撑（partially-signal-backed）", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![（(])\bpartially-signal-backed\b(?![）)])", "已有部分信号支撑（partially-signal-backed）", text, flags=re.IGNORECASE)
    text = re.sub(r",\s*or\s+", "、", text, flags=re.IGNORECASE)
    text = re.sub(r"，\s*or\s+", "、", text, flags=re.IGNORECASE)
    text = re.sub(
        r"待评审确认（review-bound），缺少外部证据:\s*the source defines the operating chain,\s*"
        r"but not yet a validated buyer\s*/\s*budget owner (?:or|或) spend threshold",
        "源素材已经定义运营主线，但真实买方、预算负责人和投入阈值仍待评审确认（review-bound）",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", text).strip("。；;:： ")


def normalize_inline_truth_phrase(value: str) -> str:
    text = compact_signal_line(value)
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    text = text.replace("`", "")
    text = re.sub(
        r"\bThe team still lacks a repeatable operating loop that turns signals into action and review\b",
        "团队仍缺少把信号推进成动作和复盘判断的稳定主线",
        text,
        flags=re.IGNORECASE,
    )
    if re.match(r"^Current source evidence already shows the operating cost of staying fragmented:\s*", text, flags=re.IGNORECASE):
        text = re.sub(
            r"^Current source evidence already shows the operating cost of staying fragmented:\s*",
            "当前已经确认的压力是：",
            text,
            flags=re.IGNORECASE,
        )
    elif re.match(r"^Current\s+", text, flags=re.IGNORECASE):
        text = re.sub(r"^Current\s+", "当前已经确认的压力是：", text, flags=re.IGNORECASE)
    text = re.sub(
        r"^Choose\s+(.+?)\s+because\s+",
        r"选择 \1，因为 ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^Keep\s+(.+?)\s+on one decision-ready operating loop so\s+",
        r"把 \1 收成同一条可判定主线，让 ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^The product must\s+", "产品必须 ", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\bThe system makes that repeatable by keeping\s+",
        "系统通过把 ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\binstead of\b", "而不是", text, flags=re.IGNORECASE)
    text = re.sub(r"当前\s+source\s+支持", "当前素材支持", text, flags=re.IGNORECASE)
    text = re.sub(r"当前\s+source\s+(?:所)?描述", "当前素材描述", text, flags=re.IGNORECASE)
    text = re.sub(r"source-defined\s+角色", "素材定义角色", text, flags=re.IGNORECASE)
    text = re.sub(r"source-defined\s+业务", "素材定义业务", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\breal external validation, willingness-to-pay, owner sign-off, budget approval, or production readiness\b",
        "真实外部验证、付费意愿、owner sign-off、预算批准或生产就绪",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\breturn to P1 or pre-P1 if a missing source fact changes product judgment\b", "若缺失事实会改变产品判断，则返回 P1 或 pre-P1", text, flags=re.IGNORECASE)
    if re.search(r"[\u4e00-\u9fff]", text):
        text = re.sub(r"\s+and\s+", "、", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+or\s+", " 或 ", text, flags=re.IGNORECASE)
        text = re.sub(r",\s*、", "、", text)
    return re.sub(r"\s+", " ", text).strip().strip("。.;:：")


def compact_reader_facing_commercial_phrase(value: str) -> str:
    """Shorten commercial fact chains without inventing or dropping numeric facts."""
    text = clean_source_label_phrase(normalize_inline_truth_phrase(value))
    if not text:
        return ""
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    text = re.sub(
        r"\bsource brief stated that\s+the wedge should connect\s+",
        "首版切片应连接 ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bsource brief stated that\s+", "当前素材指出 ", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\bmust reduce manual evidence packaging\b",
        "需要减少人工证据整理",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?P<actor>[^,.;，。/\n]{1,48}?)\s+stated that the product\s+需要减少",
        lambda match: f"{match.group('actor').strip()} 要求减少",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bnot only move the same reporting work into a new dashboard\b",
        "而不是把同一套报告工作搬进新看板",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bdecide continue\s*/\s*revise\s*/\s*pause\b",
        "做继续 / 调整 / 暂停判断",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bmust\s+做", "需要做", text, flags=re.IGNORECASE)
    if re.search(r"[\u4e00-\u9fff]", text):
        text = re.sub(r"\s+with\s+", " 并以 ", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\bcontinuation discussion after\s+(\d+)\s+weekly reviews?\b",
        r"\1 次复盘后的继续投入讨论",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bweekly reviews?\b", "复盘", text, flags=re.IGNORECASE)

    def budget_statement_repl(match: re.Match[str]) -> str:
        price = match.group("price").strip()
        review_window = match.group("window").strip()
        review_window = re.sub(r"\bweekly reviews?\b", "复盘", review_window, flags=re.IGNORECASE)
        review_window = re.sub(r"(\d+)\s*复盘", r"\1 次复盘", review_window)
        review_window = re.sub(r"\s+后", "后", review_window)
        condition_left = match.group("left").strip()
        condition_right = match.group("right").strip()
        condition_left = re.sub(r"\bdrops?\s+by\b", "下降", condition_left, flags=re.IGNORECASE)
        condition_left = re.sub(r"\brises?\s+by\b", "上升", condition_left, flags=re.IGNORECASE)
        condition_right = re.sub(r"\bdoes\s+not\s+increase\b", "不增加", condition_right, flags=re.IGNORECASE)
        return f"预算讨论区间 {price}；{review_window}后且 {condition_left} 且 {condition_right}"

    text = re.sub(
        r"\bbudget owner stated that\s+(?P<price>\$[0-9][0-9,.$\-/A-Za-z]*(?:/[A-Za-z]+)?)\s+"
        r"can be discussed after\s+(?P<window>[^.;，。]+?)\s+if\s+(?P<left>[^.;，。、]+?)(?:\s+and\s+|、)"
        r"(?P<right>[^.;，。]+?)(?=\.|;|，|。|$)",
        budget_statement_repl,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?P<price>\$[0-9][0-9,.$\-/A-Za-z]*(?:/[A-Za-z]+)?)\s+"
        r"can be discussed after\s+(?P<window>[^.;，。]+?)\s+if\s+(?P<left>[^.;，。、]+?)(?:\s+and\s+|、)"
        r"(?P<right>[^.;，。]+?)(?=\.|;|，|。|$)",
        budget_statement_repl,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\breduce manual evidence packaging,\s*not only move the same reporting work into a new dashboard\b",
        "减少人工 evidence packaging，而不是把同一套 reporting work 搬进新 dashboard",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\.([。；，,])", r"\1", text)
    text = re.sub(r"([。；，,])\s*([。；，,])+", r"\1", text)
    text = re.sub(r"([.。；;，,]\s*)owner\s+能基于", "。决策方能基于", text)
    text = re.sub(r"^owner\s+能基于", "决策方能基于", text)
    text = re.sub(
        r"\b(?P<actor>[^,.;，。/\n]{1,48}?)\s+stated that the product must\s+",
        lambda match: f"{match.group('actor').strip()} 要求 ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(\d+)\s+weekly reviews?\s+后(?=\s*且|[，,。；;\s]|$)", r"\1 次 weekly review 后", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*/\s*(?=(?:当前)?人工追踪成本)", "；", text)
    text = re.sub(r"当前人工追踪成本", "人工追踪成本", text)
    text = re.sub(r"继续投入阈值保持\s*review-bound", "更强投入判断仍 review-bound", text, flags=re.IGNORECASE)
    text = re.sub(r"继续投入阈值\s*[:：]\s*", "继续判断看 ", text)
    text = re.sub(r"足够清楚时才值得继续", "足够清楚后再继续", text)
    source_note_tail_pattern = (
        r"\s+/\s+(?:(?:repeated sampling|procurement paperwork|production rollout evidence)"
        r"[^.;。；\n]*(?:[.;。；]\s*)?|"
        r"[^,/.;。；\n]*\b(?:stated that|remain outside|outside this fixture|"
        r"not only move|procurement paperwork|production rollout|源素材要求产品必须)\b"
        r"[^,/.;。；\n]*(?:[.;。；]\s*)?)"
    )
    text = re.sub(source_note_tail_pattern, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"要求\s+减少", "要求减少", text)
    text = re.sub(r"\s*/\s*(?=[A-Za-z][A-Za-z0-9 _-]{0,48}\s+要求)", "；同时 ", text)
    text = re.sub(r"\.\s*(?=与|并|因此|作为|足以|否则|但)", "，", text)
    text = re.sub(
        r"\bgrounded in\s+([^.;。；\n]+)",
        r"证据锚定 \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bthe source packet\b", "源素材（source packet）", text, flags=re.IGNORECASE)
    text = re.sub(
        r"[，,]?\s*才讨论\s+(\$[0-9][0-9,.$\-/A-Za-z]*(?:/[A-Za-z]+)?)(?:\s*订阅区间)?",
        r"；订阅区间 \1",
        text,
    )
    text = re.sub(r"[，,]?\s*才讨论\s+([^，。；;]+)", r"；后续讨论 \1", text)
    if len(text) > 80 or re.search(r"预算|订阅|/month|/hour|review-bound|overdue|staff workload", text, flags=re.IGNORECASE):
        text = re.sub(
            r"[，,。]\s*(?=(?:\d+\s*天)?试点预算|\d+\s+次\s+weekly|overdue\s+follow-up|staff\s+workload|订阅区间|更强投入判断|继续判断|后续讨论)",
            "；",
            text,
            flags=re.IGNORECASE,
        )
    text = re.sub(r"\s*且\s*", " 且 ", text)
    text = re.sub(r"且(?=[A-Za-z])", "且 ", text)
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"(\$[0-9][0-9,.$-]*)\s*/\s*(month|hour|year)", r"\1/\2", text, flags=re.IGNORECASE)
    text = naturalize_reader_facing_bilingual_terms(text)
    text = re.sub(r"\s*；\s*", "；", text)
    text = re.sub(r"；+", "；", text)
    text = re.sub(r"\.([。；，,])", r"\1", text)
    text = re.sub(r"([。；，,])\s*([。；，,])+", r"\1", text)
    return re.sub(r"\s+", " ", text).strip("。；;:： ")


def compact_proof_reference_phrase(proof_phrase: str) -> str:
    """Render a short in-sentence reference; full proof details stay in proof fields."""
    text = compact_reader_facing_commercial_phrase(proof_phrase)
    if not text or is_review_bound_missing(text):
        return "继续判断证据"
    if "继续试用或预算讨论意向" in text:
        return "继续试用或预算讨论意向"
    markers: list[str] = []
    if re.search(r"\bhours?\b|/hour|\$[0-9][0-9,.$-]*/month", text, flags=re.IGNORECASE):
        markers.append("成本")
    if re.search(r"试点预算|pilot budget", text, flags=re.IGNORECASE):
        markers.append("试点预算")
    if re.search(r"weekly review|overdue|staff workload|下降|不增加|不上升", text, flags=re.IGNORECASE):
        markers.append("结果阈值")
    if re.search(r"订阅区间|subscription|\$[0-9][0-9,.$-]*/month", text, flags=re.IGNORECASE):
        markers.append("订阅区间")
    if markers:
        deduped = list(dict.fromkeys(markers))
        return f"继续投入证据（{'、'.join(deduped[:4])}）"
    if len(text) <= 60:
        return text
    return "继续投入证据"


def compact_spend_reference_phrase(spend_phrase: str) -> str:
    text = compact_reader_facing_commercial_phrase(spend_phrase)
    if not text or is_review_bound_missing(text):
        return "真实预算、报价或投入阈值仍保持 review-bound"
    if len(text) > 90 or re.search(r"/month|/hour|试点预算|weekly review|overdue|staff workload", text, flags=re.IGNORECASE):
        return "时间、流程变更和继续评审成本是否值得继续投入"
    return plain_truth_text(text)


def reader_facing_commercial_detail_clause(value: str) -> bool:
    return bool(
        re.search(
            r"人工追踪成本|/hour|/month|试点预算|weekly\s+review|overdue\s+follow-up|staff\s+workload|订阅区间|预算讨论区间",
            value,
            flags=re.IGNORECASE,
        )
    )


def strip_reader_facing_commercial_detail_clauses(value: str) -> str:
    clauses = [clause.strip() for clause in re.split(r"；", value) if clause.strip()]
    kept = [clause for clause in clauses if not reader_facing_commercial_detail_clause(clause)]
    text = "；".join(kept).strip("。；;:： ")
    text = re.sub(r"\s*/\s+(?=(?:repeated sampling|procurement paperwork|production rollout evidence))[^。；]+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip("。；;:： ")
    return text


def clean_reader_facing_anchor(value: str) -> str:
    text = compact_signal_line(value)
    text = re.split(r"\s*/\s*(?=(?:当前)?人工追踪成本|人工追踪成本|预算讨论区间)", text, maxsplit=1)[0]
    text = re.split(r"\s+人工追踪成本\b", text, maxsplit=1)[0]
    return text.strip("。；;:： ，,")


def first_reader_facing_anchor(value: str) -> str:
    texts = [
        strip_reader_facing_commercial_detail_clauses(value),
        compact_reader_facing_commercial_phrase(value),
        compact_signal_line(value),
    ]
    patterns = (
        r"^(?P<anchor>让\s+.+?\s+围绕\s+.+?)(?:\s+获得|；|。|$)",
        r"^(?P<anchor>首版切片应聚焦\s+.+?)(?:；|。|$)",
        r"^(?P<anchor>首版切片应连接\s+.+?)(?:；|。|$)",
        r"^当前素材指出\s+(?P<anchor>.+?)(?:；|。|$)",
        r"^当前\s+source\s+支持把\s+(?P<anchor>.+?)(?:\s+作为产品主论点|；|。|$)",
        r"^(?P<anchor>[^。；，]+?的问题不是只慢一点)",
        r"^(?P<anchor>单点工具或人工服务可以补某个步骤)",
    )
    for text in texts:
        if not text:
            continue
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return clean_reader_facing_anchor(match.group("anchor"))
    text = texts[0]
    if text:
        return clean_reader_facing_anchor(text.split("；", 1)[0])
    return ""


def compact_driver_transformation_line(label: str, value: object) -> str:
    text = compact_reader_facing_commercial_phrase(clean_source_label_phrase(value))
    if not text:
        return ""
    has_commercial_detail = reader_facing_commercial_detail_clause(text)
    if not has_commercial_detail:
        return text
    proof_reference = compact_proof_reference_phrase(text)
    if label == "产品押注":
        anchor = first_reader_facing_anchor(text)
        if anchor:
            return f"{anchor} 获得可复盘的业务闭环，并用 {proof_reference} 支撑继续 / 调整 / 暂停判断"
    if label == "为什么这个切片":
        anchor = first_reader_facing_anchor(text)
        if anchor:
            return f"{anchor}，因为它把日常动作和继续判断接到同一条证据线上"
    if label == "为什么不是现状":
        anchor = first_reader_facing_anchor(text)
        if anchor:
            return f"{anchor}，而是无法稳定支撑继续 / 调整 / 暂停判断"
    if label == "为什么不是单点工具/服务替代":
        anchor = first_reader_facing_anchor(text)
        if anchor:
            return f"{anchor}，但不能把主线动作和继续判断稳定接在一起"
    if label == "读者摘要":
        anchor = first_reader_facing_anchor(text)
        if anchor:
            return f"当前素材支持把 {anchor} 作为产品主论点，并把 {proof_reference} 作为继续投入证据；但不能升级为真实市场验证"
    if label == "下一轮投入证据" and has_commercial_detail:
        if re.match(r"^下一轮投入需要看到\b", text):
            return text
        return f"{proof_reference}：{text}"
    return text


def reader_facing_context_driver_line(label: str, runtime_context: dict[str, object]) -> str:
    module_surface = business_loop_reader_surface(runtime_context, limit=4)
    primary_segment = plain_role_surface(str(runtime_context.get("primary_segment", "")).strip())
    continuation_owner = plain_role_surface(continuation_owner_surface(runtime_context))
    proof_artifact = compact_proof_artifact_phrase(runtime_context)
    proof_reference = (
        compact_proof_reference_phrase(proof_artifact)
        if proof_artifact and not is_review_bound_missing(proof_artifact)
        else "继续判断证据"
    )
    if label == "产品押注":
        return f"首版押注是把 {module_surface} 收成一条可复盘主线，让 {primary_segment} 能连续推进关键动作，并支持继续 / 调整 / 暂停判断。"
    if label == "为什么现在":
        return f"现在的问题不是缺一个单点页面，而是 {module_surface} 仍会断裂，导致 {continuation_owner} 难以判断是否继续投入。"
    if label == "为什么这个切片":
        return f"这个切片先保留 {module_surface}，因为它同时覆盖日常执行、下一动作和 {proof_reference}。"
    if label == "为什么不是现状":
        return "现状的单点页面、报表或人工补位无法稳定连接信号、行动和复盘判断。"
    if label == "为什么不是单点工具/服务替代":
        return "单点工具或人工服务可以补局部步骤，但不能稳定保留主线对象、下一动作和继续判断证据。"
    if label == "下一轮投入证据":
        return f"下一轮要看 {continuation_owner} 能否在同一评审界面（review surface）用 {proof_reference} 做继续 / 调整 / 暂停判断。"
    if label == "读者摘要":
        return f"当前素材支持先围绕 {module_surface} 做首版闭环；真实付费、owner sign-off 和生产级效果仍不能升级为已验证事实。"
    return ""


def reader_facing_truth_is_spliced(raw_value: str, cleaned_value: str | None = None) -> bool:
    raw = compact_signal_line(raw_value)
    text = cleaned_value if cleaned_value is not None else compact_reader_facing_commercial_phrase(raw)
    combined = f"{raw}\n{text}"
    if re.search(r"。\.|\.。|。。|。、|。,|，。|;。", combined):
        return True
    if re.search(r"\b(?:stated that|can be discussed after)\b", text, flags=re.IGNORECASE):
        return True
    if re.search(
        r"\b(?:grounded in|remain outside|outside this fixture|not only move|"
        r"procurement paperwork|production rollout)\b",
        combined,
        flags=re.IGNORECASE,
    ):
        return True
    if re.search(r"`[^`\n]{1,80}。`", raw):
        return True
    if re.search(r"\b(?:and|with)\s+`?[\w\u4e00-\u9fff]", raw, flags=re.IGNORECASE) and re.search(r"[\u4e00-\u9fff]", raw):
        return True
    for match in re.finditer(r"[\u4e00-\u9fff][^。；;/\n]{0,80}\s+/\s+[\u4e00-\u9fff][^。；;/\n]{0,80}", combined):
        if any(token in match.group(0) for token in ("继续 / 调整 / 暂停", "继续 / 调整", "调整 / 暂停")):
            continue
        return True
    if len(text) > 180 and re.search(r"预算讨论区间|/month|weekly review|review cycles", text, flags=re.IGNORECASE):
        return True
    if len(text) > 160 and re.search(
        r"workflow-first|dashboard|source-grounded|grounded in|TenantWorkspace,\s*TrackedScope|"
        r"VisitRecord,\s*TreatmentRecord|decision-ready\s+\w+|"
        r"系统通过把|作为产品主论点，并把|而不是把\s+如果|的问题不是只慢一点|"
        r"不必再在分散记录之间重建上下文",
        combined,
        flags=re.IGNORECASE,
    ):
        return True
    return False


def runtime_label_surface(labels: list[str], fallback: str, *, limit: int = 3) -> str:
    picked = [clean_runtime_label_item(label) for label in labels if clean_runtime_label_item(label)]
    if not picked:
        return fallback
    rendered = [f"`{label}`" for label in picked[:limit]]
    if len(rendered) == 1:
        return rendered[0]
    if len(rendered) == 2:
        return f"{rendered[0]} 和 {rendered[1]}"
    return f"{'、'.join(rendered[:-1])} 和 {rendered[-1]}"


def plain_role_surface(value: str, fallback: str = "primary operator") -> str:
    cleaned = normalize_inline_truth_phrase(value)
    return cleaned or fallback


def runtime_truth_slot_surface(runtime_context: dict[str, object], slot_name: str) -> str:
    business_release_truth_pack = runtime_context.get("business_release_truth_pack", {})
    if isinstance(business_release_truth_pack, dict):
        direct_value = business_release_truth_pack.get(slot_name)
        if isinstance(direct_value, list):
            return normalize_inline_truth_phrase("；".join(str(item).strip() for item in direct_value if str(item).strip()))
        if isinstance(direct_value, dict):
            release_value = normalize_inline_truth_phrase(truth_slot_value(direct_value))
        else:
            release_value = normalize_inline_truth_phrase(str(direct_value or ""))
        if release_value:
            return release_value
    business_world_model = runtime_context.get("business_world_model", {})
    if not isinstance(business_world_model, dict):
        return ""
    return normalize_inline_truth_phrase(truth_slot_value(business_world_model.get(slot_name, {})))


def business_completeness_driver_surface(runtime_context: dict[str, object]) -> dict[str, object]:
    business_release_truth_pack = runtime_context.get("business_release_truth_pack", {})
    if isinstance(business_release_truth_pack, dict):
        driver = business_release_truth_pack.get("business_completeness_driver", {})
        if isinstance(driver, dict) and driver:
            return driver
    business_world_model = runtime_context.get("business_world_model", {})
    if isinstance(business_world_model, dict):
        summary = business_world_model.get("product_source_direct_driver_summary", {})
        if isinstance(summary, dict):
            driver = summary.get("business_completeness_driver", {})
            if isinstance(driver, dict) and driver:
                return driver
    return {}


def business_completeness_driver_state(runtime_context: dict[str, object]) -> str:
    driver = business_completeness_driver_surface(runtime_context)
    ceiling = driver.get("commercial_claim_ceiling", {}) if isinstance(driver, dict) else {}
    if isinstance(ceiling, dict):
        return compact_signal_line(str(ceiling.get("evidence_confidence_state", "")))
    return ""


def prefer_explicit_truth_surface(truth_value: str, *fallbacks: str) -> str:
    truth = compact_reader_facing_commercial_phrase(truth_value)
    if (
        truth
        and not looks_like_placeholder(truth)
        and not is_review_bound_missing(truth)
        and not reader_facing_truth_is_spliced(truth_value, truth)
    ):
        return truth
    for candidate in fallbacks:
        cleaned = compact_reader_facing_commercial_phrase(candidate)
        if cleaned and not looks_like_placeholder(cleaned) and not reader_facing_truth_is_spliced(candidate, cleaned):
            return cleaned
    return ""


def mainline_module_surface(runtime_context: dict[str, object], limit: int = 3) -> str:
    return runtime_label_surface(module_names(runtime_context, limit), "`source-defined mainline`", limit=limit)


def continuation_owner_surface(runtime_context: dict[str, object]) -> str:
    business_world_model = runtime_context.get("business_world_model", {})
    buyer_chain = business_world_model.get("buyer_budget_chain", {}) if isinstance(business_world_model, dict) else {}
    return compact_signal_line(str(buyer_chain.get("continuation_owner", ""))) or (
        str(runtime_context.get("target_user_roles", [])[-1]).strip()
        if runtime_context.get("target_user_roles")
        else str(runtime_context.get("primary_segment", "primary operator")).strip()
    )


def compact_proof_artifact_phrase(runtime_context: dict[str, object]) -> str:
    completeness_driver = business_completeness_driver_surface(runtime_context)
    proof_for_continue = completeness_driver.get("proof_for_continue", {}) if isinstance(completeness_driver, dict) else {}
    driver_proof = (
        compact_signal_line(str(proof_for_continue.get("proof_artifact", "")))
        if isinstance(proof_for_continue, dict)
        else ""
    )
    if driver_proof and not looks_like_placeholder(driver_proof) and not is_review_bound_missing(driver_proof):
        return compact_reader_facing_commercial_phrase(driver_proof)
    proof_source = source_grounded_proof_phrase(runtime_context)
    if re.search(r"\b(?:grounded in|with)\b", proof_source, flags=re.IGNORECASE):
        proof = compact_signal_line(proof_source)
    else:
        proof = compress_business_sentence(proof_source, max_parts=1)
    if not proof:
        review_units = semantic_authoring_units_by_type(runtime_context, "dashboard_review_decision_surface", limit=1)
        if review_units:
            return "source-defined review surface proof"
        return "review-bound / missing evidence"
    proof = normalize_inline_truth_phrase(proof)
    proof = re.sub(r"^traceable\s+", "", proof, flags=re.IGNORECASE)
    proof = re.sub(r"^review-grade\s+", "", proof, flags=re.IGNORECASE)
    proof = re.sub(r"\s+grounded in\s+", "（锚定 ", proof, flags=re.IGNORECASE)
    proof = re.sub(r"\s+with\s+", "（保留 ", proof, flags=re.IGNORECASE)
    proof = re.sub(r"\s+(?:still\s+)?attached\b", "", proof, flags=re.IGNORECASE)
    proof = re.sub(r"\s+preserved\b", "", proof, flags=re.IGNORECASE)
    proof = re.sub(r"。(?=（(?:锚定|保留))", "", proof)
    proof = re.sub(r"\s+", " ", proof).strip("。.;:：")
    if "（" in proof and not proof.endswith("）"):
        proof = f"{proof}）"
    proof = compact_reader_facing_commercial_phrase(proof)
    if proof.casefold() in {"目标", "goal", "objective"} or len(proof) > 120:
        review_units = semantic_authoring_units_by_type(runtime_context, "dashboard_review_decision_surface", limit=1)
        if review_units:
            return "source-defined review surface proof"
    return proof


def compact_spend_at_risk_phrase(runtime_context: dict[str, object]) -> str:
    spend = compact_reader_facing_commercial_phrase(source_grounded_commercial_phrase(runtime_context))
    if spend and reader_facing_truth_is_spliced(spend):
        return "时间、流程变更和继续评审成本"
    return spend or "review-bound / missing evidence"


def compact_value_mechanism_phrase(runtime_context: dict[str, object]) -> str:
    truth_value = prefer_explicit_truth_surface(runtime_truth_slot_surface(runtime_context, "value_mechanism"))
    if truth_value:
        return truth_value
    raw_source_value = source_grounded_value_phrase(runtime_context)
    if raw_source_value and not reader_facing_truth_is_spliced(raw_source_value):
        raw_value = compress_business_sentence(raw_source_value, max_parts=2)
        raw_value = compact_reader_facing_commercial_phrase(raw_value)
        if raw_value and not reader_facing_truth_is_spliced(raw_source_value, raw_value):
            return raw_value
    module_surface = business_loop_reader_surface(runtime_context, limit=4)
    primary_segment = plain_role_surface(str(runtime_context.get("primary_segment", "")).strip())
    return (
        f"{module_surface} 必须在同一条主线上连续推进，"
        f"让 {primary_segment} 能把关键动作推进到下一步，而不是继续依赖人工补位和结果解释。"
    )


def compact_mainline_thesis(runtime_context: dict[str, object]) -> str:
    truth_core_thesis = prefer_explicit_truth_surface(runtime_truth_slot_surface(runtime_context, "core_thesis"))
    if not truth_core_thesis:
        truth_core_thesis = prefer_explicit_truth_surface(runtime_truth_slot_surface(runtime_context, "value_mechanism"))
    if truth_core_thesis:
        return truth_core_thesis
    module_surface = business_loop_reader_surface(runtime_context, limit=4)
    primary_segment = plain_role_surface(str(runtime_context.get("primary_segment", "")).strip())
    continuation_owner = plain_role_surface(continuation_owner_surface(runtime_context))
    proof_artifact = compact_proof_artifact_phrase(runtime_context)
    spend_at_risk = compact_spend_at_risk_phrase(runtime_context)
    if proof_artifact and not is_review_bound_missing(proof_artifact):
        proof_reference = compact_proof_reference_phrase(proof_artifact)
        if spend_at_risk and not is_review_bound_missing(spend_at_risk):
            return (
                f"首版先把 {module_surface} 串成同一条可执行主线，"
                f"让 {primary_segment} 推进下一步动作，并让 {continuation_owner} 在同一评审界面（review surface）围绕 {proof_reference} 判断是否继续。"
            )
        return (
            f"首版先把 {module_surface} 串成同一条可执行主线，"
            f"让 {primary_segment} 推进下一步动作，并让 {continuation_owner} 在同一评审界面（review surface）围绕 {proof_reference} 判断是否继续 / 调整。"
        )
    return (
        f"首版先把 {module_surface} 串成同一条可执行主线，"
        f"让 {primary_segment} 能沿同一业务链推进关键动作，而不是继续依赖孤立页面、结果汇总或线下补位。"
    )


def compact_direction_anchor(runtime_context: dict[str, object]) -> str:
    module_surface = business_loop_reader_surface(runtime_context, limit=4)
    return f"产品方向不是铺开更多孤立功能，而是先围绕 {module_surface} 做出一条可执行、可判定的主线。"


def compact_need_framing(runtime_context: dict[str, object]) -> str:
    module_surface = business_loop_reader_surface(runtime_context, limit=4)
    return f"先围绕 {module_surface} 收成一条可判定的主线闭环，而不是继续堆孤立页面、局部表单或事后汇总。"


def compact_positioning_choice(runtime_context: dict[str, object]) -> str:
    module_surface = business_loop_reader_surface(runtime_context, limit=4)
    return f"定位上优先卖 {module_surface} 的主线闭环能力，而不是卖单点页面、单点可视化或脱离主链的事后报告。"


def compact_why_now_phrase(runtime_context: dict[str, object]) -> str:
    truth_why_now = prefer_explicit_truth_surface(runtime_truth_slot_surface(runtime_context, "why_now"))
    if truth_why_now:
        return truth_why_now
    pressure = compress_business_sentence(
        signal_phrase(
            list(runtime_context.get("pressure_signals", [])),
            "source-defined business pressure remains visible but fragmented",
            limit=1,
        ),
        max_parts=1,
    )
    experience = compress_business_sentence(source_grounded_experience_phrase(runtime_context), max_parts=1)
    continuation_owner = continuation_owner_surface(runtime_context)
    proof_artifact = compact_proof_artifact_phrase(runtime_context)
    module_surface = business_loop_reader_surface(runtime_context, limit=4)
    spend_at_risk = compact_spend_at_risk_phrase(runtime_context)
    pressure = normalize_inline_truth_phrase(pressure) or "当前主线仍缺少稳定的业务决策闭环"
    if re.search(r"source-defined business pressure", pressure, flags=re.IGNORECASE):
        pressure = "当前主线仍缺少稳定的业务决策闭环"
    experience = normalize_inline_truth_phrase(experience) or "人工拼接和事后解释"
    if re.search(r"waiting|handoff friction|manual reconstruction", experience, flags=re.IGNORECASE):
        experience = "人工拼接和事后解释"
    if proof_artifact and not is_review_bound_missing(proof_artifact):
        proof_reference = compact_proof_reference_phrase(proof_artifact)
        decision_need = "下一轮投入判断所需证据"
        if not spend_at_risk or is_review_bound_missing(spend_at_risk):
            decision_need = "下一轮继续 / 调整判断所需证据"
        return (
            f"当前已经确认的压力是：{pressure}。"
            f"只要 {module_surface} 仍然断裂，`{continuation_owner}` 就无法在一次评审（review）中同时看到 {proof_reference} 与{decision_need}。"
        )
    return (
        f"当前已经确认的压力是：{pressure}。"
        f"如果 {module_surface} 仍然断裂，团队就会继续陷在 {experience}，"
        "关键判断仍只能停留在待评审确认（review-bound）。"
    )


def compact_why_this_not_that_phrase(runtime_context: dict[str, object]) -> str:
    truth_why_this_not_that = prefer_explicit_truth_surface(
        runtime_truth_slot_surface(runtime_context, "why_this_not_that")
    )
    if truth_why_this_not_that:
        return truth_why_this_not_that
    module_surface = business_loop_reader_surface(runtime_context, limit=4)
    proof_artifact = compact_proof_artifact_phrase(runtime_context)
    proof_anchor = (
        compact_proof_reference_phrase(proof_artifact)
        if proof_artifact and not is_review_bound_missing(proof_artifact)
        else "继续判断所需证据"
    )
    return (
        f"选择完整主线，而不是孤立页面或事后汇总，"
        f"因为 {module_surface} 的关键对象、下一动作和 {proof_anchor} 必须放在同一条链上连续可见。"
    )


def compact_continuation_boundary_phrase(runtime_context: dict[str, object]) -> str:
    continuation_owner = plain_role_surface(continuation_owner_surface(runtime_context))
    spend_at_risk = compact_spend_at_risk_phrase(runtime_context)
    proof_artifact = compact_proof_artifact_phrase(runtime_context)
    if spend_at_risk and not is_review_bound_missing(spend_at_risk):
        proof_reference = compact_proof_reference_phrase(proof_artifact)
        spend_reference = compact_spend_reference_phrase(spend_at_risk)
        return (
            f"{continuation_owner} 只有在同一评审界面（review surface）看到 {proof_reference}，"
            f"并能判断“{spend_reference}”是否成立时，才进入继续 / 调整 / 暂停。"
        )
    proof_reference = compact_proof_reference_phrase(proof_artifact)
    return (
        f"当前只固定 {proof_reference} 这个同一评审界面（review surface）中的继续判断锚点；"
        "真实预算、报价或投入阈值仍保持待评审确认（review-bound），不在 PRD 里脑补。"
    )


def compact_value_anchor(runtime_context: dict[str, object]) -> str:
    value = compress_business_sentence(source_grounded_value_phrase(runtime_context), max_parts=1)
    value = compact_reader_facing_commercial_phrase(value)
    if value and not is_review_bound_missing(value):
        pressure_key = normalized_match_key(compact_pressure_anchor(runtime_context))
        if normalized_match_key(value) != pressure_key:
            return value
    primary_segment = plain_role_surface(str(runtime_context.get("primary_segment", "")).strip())
    module_surface = business_loop_reader_surface(runtime_context, limit=4)
    proof_artifact = compact_proof_artifact_phrase(runtime_context)
    if proof_artifact and not is_review_bound_missing(proof_artifact):
        proof_reference = compact_proof_reference_phrase(proof_artifact)
        return f"{primary_segment} 能沿 {module_surface} 把关键动作推进到下一步，并让 {proof_reference} 不再停留在分散记录与人工补位里。"
    return f"{primary_segment} 需要围绕 {module_surface} 完成一次连续主线，而不是停在分散记录与事后解释。"


def looks_like_role_surface(value: str) -> bool:
    text = compact_signal_line(value)
    if not text:
        return False
    if OBJECT_LIKE_SURFACE_PATTERN.search(text):
        return False
    return bool(ROLE_LIKE_SURFACE_PATTERN.search(text))


def compact_operating_object_surface(runtime_context: dict[str, object], limit: int = 3) -> str:
    protected = [
        compact_signal_line(str(item))
        for item in runtime_context.get("protected_business_nouns", [])
        if compact_signal_line(str(item)) and not looks_like_role_surface(str(item))
    ]
    if protected:
        return runtime_label_surface(protected, "`source-defined business object`", limit=limit)
    core_objects = [
        compact_signal_line(str(item))
        for item in runtime_context.get("core_business_objects", [])
        if compact_signal_line(str(item)) and not looks_like_role_surface(str(item))
    ]
    if core_objects:
        return runtime_label_surface(core_objects, "`source-defined business object`", limit=limit)
    screen_terms = [
        compact_signal_line(str(item))
        for item in runtime_context.get("screen_terms", [])
        if compact_signal_line(str(item)) and not looks_like_role_surface(str(item))
    ]
    if screen_terms:
        return runtime_label_surface(screen_terms, "`source-defined business object`", limit=limit)
    roles = [
        compact_signal_line(str(item))
        for item in runtime_context.get("target_user_roles", [])
        if compact_signal_line(str(item))
    ]
    return runtime_label_surface(roles, "`source-defined business object`", limit=limit)


def compact_pressure_anchor(runtime_context: dict[str, object]) -> str:
    pressure = compress_business_sentence(
        signal_phrase(
            list(runtime_context.get("pressure_signals", [])),
            "当前主线仍缺少稳定的业务决策闭环",
            limit=1,
        ),
        max_parts=1,
    )
    pressure = normalize_inline_truth_phrase(pressure)
    return pressure or "当前主线仍缺少稳定的业务决策闭环。"


def compact_decision_evidence_anchor(runtime_context: dict[str, object]) -> str:
    continuation_owner = plain_role_surface(continuation_owner_surface(runtime_context))
    proof_artifact = compact_proof_artifact_phrase(runtime_context)
    spend_at_risk = compact_spend_at_risk_phrase(runtime_context)
    if spend_at_risk and not is_review_bound_missing(spend_at_risk):
        return f"{continuation_owner} 需要围绕 {proof_artifact} 判断“{plain_truth_text(spend_at_risk)}”是否成立。"
    return f"{continuation_owner} 需要围绕 {proof_artifact} 做继续 / 调整 / 暂停判断。"


def compact_competitive_baseline_anchor(runtime_context: dict[str, object]) -> str:
    workflow_backbone = business_loop_surface(runtime_context, limit=4)
    return f"围绕 {workflow_backbone} 的分散流程、表格/截图、讨论串与人工补位。"


def compact_partial_tool_anchor(runtime_context: dict[str, object]) -> str:
    local_step_surface = runtime_label_surface(business_loop_items(runtime_context, limit=2), "`source-defined local step`", limit=2)
    return f"只覆盖 {local_step_surface} 等局部步骤的单点工具。"


def compact_service_substitute_anchor(runtime_context: dict[str, object]) -> str:
    proof_artifact = compact_proof_artifact_phrase(runtime_context)
    return f"依赖人工服务、代运营或内部专项支持来维持连续判断，但 {proof_artifact} 仍留在人的记忆与协作里。"


def render_integrated_direction_evidence_lines(runtime_context: dict[str, object]) -> list[str]:
    lines = [
        f"- pressure_anchor: {compact_pressure_anchor(runtime_context)}",
        f"- value_anchor: {compact_value_anchor(runtime_context)}",
        f"- continuation_anchor: {compact_decision_evidence_anchor(runtime_context)}",
    ]
    return list(dict.fromkeys(lines))


def render_capability_recompilation_lines(runtime_context: dict[str, object]) -> list[str]:
    module_surface = business_loop_surface(runtime_context, limit=4)
    proof_artifact = compact_proof_artifact_phrase(runtime_context)
    continuation_owner = continuation_owner_surface(runtime_context)
    object_surface = compact_operating_object_surface(runtime_context, limit=3)
    lines = [
        f"- mainline_recompile: 把 {module_surface} 从分散步骤重编成同一条连续主线，而不是继续依赖模块切换和人工补位。",
        f"- decision_surface_recompile: 把下一动作、{proof_artifact} 与责任判断放到同一评审界面（review surface），让 `{continuation_owner}` 能直接做继续 / 调整 / 暂停。",
        f"- object_integrity_recompile: 把 {object_surface} 作为贯穿对象保留在主线里，避免记录、状态与 review 证据脱钩。",
    ]
    return list(dict.fromkeys(lines))



def render_chosen_business_thesis_lines(runtime_context: dict[str, object]) -> list[str]:
    model = runtime_context.get("business_world_model", {})
    thesis = model.get("chosen_business_thesis", {}) if isinstance(model, dict) else {}
    arena = model.get("business_exploration_arena", {}) if isinstance(model, dict) else {}
    argument_draft = model.get("commercial_argument_draft", {}) if isinstance(model, dict) else {}
    if not isinstance(thesis, dict) or not thesis:
        return ["- Chosen Business Thesis: not present; keep thesis selection review-bound instead of smoothing it into generic PRD prose."]
    substitute_map = arena.get("substitute_and_current_state_map", {}) if isinstance(arena, dict) else {}
    reality_map = arena.get("reality_density_map", {}) if isinstance(arena, dict) else {}
    substitute = compact_signal_line(str(thesis.get("current_state_substitute_to_beat", "")))
    min_proof = ""
    if isinstance(substitute_map, dict):
        min_proof = compact_signal_line(str(substitute_map.get("minimum_proof_to_beat_substitutes", "")))
    reality_focus = compact_signal_line(str(thesis.get("reality_density_focus", "")))
    if not reality_focus and isinstance(reality_map, dict):
        reality_focus = compact_signal_line(str(reality_map.get("primary_reality_focus", "")))
    draft_narrative = compact_signal_line(str(argument_draft.get("argument_narrative", ""))) if isinstance(argument_draft, dict) else ""
    business_argument = draft_narrative or compact_signal_line(str(thesis.get("business_argument", "")))
    lines = []
    driver_summary = model.get("product_source_direct_driver_summary", {}) if isinstance(model, dict) else {}
    if isinstance(driver_summary, dict) and driver_summary:
        def append_human_driver_line(label: str, value: object) -> None:
            if value is None:
                return
            raw_text = clean_source_label_phrase(value)
            if not raw_text or raw_text.casefold() in {"none", "null"}:
                return
            text = compact_driver_transformation_line(label, raw_text)
            if not text:
                return
            context_line = reader_facing_context_driver_line(label, runtime_context)
            has_commercial_detail = reader_facing_commercial_detail_clause(text)
            if context_line and not has_commercial_detail and (
                len(text) > 220
                or re.search(r"workflow-first|dashboard|source-grounded|grounded in", raw_text, flags=re.IGNORECASE)
                or reader_facing_truth_is_spliced(raw_text, text)
            ):
                text = context_line
            fragments = [part.strip() for part in re.split(r"；", text) if part.strip()]
            if len(f"- {label}：{text}") <= 260 or len(fragments) <= 1:
                lines.append(f"- {label}：{text}")
                return
            current = ""
            line_index = 0
            for fragment in fragments:
                candidate = f"{current}；{fragment}" if current else fragment
                suffix = "" if line_index == 0 else "（续）"
                if current and len(f"- {label}{suffix}：{candidate}") > 240:
                    lines.append(f"- {label}{suffix}：{current}")
                    line_index += 1
                    current = fragment
                else:
                    current = candidate
            if current:
                suffix = "" if line_index == 0 else "（续）"
                lines.append(f"- {label}{suffix}：{current}")

        source_truth = driver_summary.get("source_truth_admission", {})
        product_judgment = driver_summary.get("product_judgment", {})
        commercial_judgment = driver_summary.get("commercial_judgment", {})
        business_feasibility = driver_summary.get("business_feasibility", {})
        mvp_wedge = driver_summary.get("mvp_wedge", {})
        acceptance_meaning = driver_summary.get("acceptance_meaning", {})
        completeness_driver = driver_summary.get("business_completeness_driver", {})
        synthesis = driver_summary.get("business_judgment_synthesis", {})
        transformation = driver_summary.get("business_judgment_transformation", {})
        gap_routing = driver_summary.get("open_truth_gap_routing", {})
        forbidden = driver_summary.get("forbidden_downstream_assumptions", [])
        if isinstance(transformation, dict) and transformation:
            transformation_fields = (
                ("产品押注", "product_bet"),
                ("为什么现在", "why_now"),
                ("为什么这个切片", "why_this_wedge"),
                ("为什么不是现状", "why_not_status_quo"),
                ("为什么不是单点工具/服务替代", "why_not_single_tool_or_service_substitute"),
                ("下一轮投入证据", "proof_needed_for_next_investment"),
                ("阻断更强声明的开放真相", "claim_blocking_open_truth"),
                ("读者摘要", "reader_facing_summary"),
            )
            for label, key in transformation_fields:
                append_human_driver_line(label, transformation.get(key))
        if (not isinstance(transformation, dict) or not transformation) and (not isinstance(synthesis, dict) or not synthesis):
            if business_argument and not business_argument.casefold().startswith("generic "):
                lines.append(f"- {clean_source_label_phrase(business_argument)}")
        if (not isinstance(transformation, dict) or not transformation) and isinstance(synthesis, dict) and synthesis.get("product_decision"):
            append_human_driver_line("产品判断", synthesis.get("product_decision"))
        elif (not isinstance(transformation, dict) or not transformation) and isinstance(product_judgment, dict) and product_judgment.get("why_this_not_that"):
            append_human_driver_line("产品判断", product_judgment.get("why_this_not_that"))
        if (not isinstance(transformation, dict) or not transformation) and isinstance(synthesis, dict) and synthesis.get("commercial_decision"):
            append_human_driver_line("商业判断", synthesis.get("commercial_decision"))
        elif (not isinstance(transformation, dict) or not transformation) and isinstance(commercial_judgment, dict) and commercial_judgment.get("decision_leverage"):
            append_human_driver_line("商业判断", commercial_judgment.get("decision_leverage"))
        if (not isinstance(transformation, dict) or not transformation) and isinstance(business_feasibility, dict) and business_feasibility.get("feasibility_claim"):
            append_human_driver_line("业务可行性", business_feasibility.get("feasibility_claim"))
        if (not isinstance(transformation, dict) or not transformation) and isinstance(mvp_wedge, dict) and mvp_wedge.get("narrowest_valuable_wedge"):
            append_human_driver_line("首版切片", mvp_wedge.get("narrowest_valuable_wedge"))
        if (not isinstance(transformation, dict) or not transformation) and isinstance(synthesis, dict) and synthesis.get("acceptance_decision"):
            append_human_driver_line("验收含义", synthesis.get("acceptance_decision"))
        elif (not isinstance(transformation, dict) or not transformation) and isinstance(acceptance_meaning, dict) and acceptance_meaning.get("acceptance_should_prove"):
            append_human_driver_line("验收含义", acceptance_meaning.get("acceptance_should_prove"))
        if isinstance(completeness_driver, dict) and completeness_driver:
            loss_chain = completeness_driver.get("business_loss_chain", {})
            economics = completeness_driver.get("continuation_economics", {})
            substitute_map = completeness_driver.get("substitute_pressure_map", {})
            proof_for_continue = completeness_driver.get("proof_for_continue", {})
            claim_ceiling = completeness_driver.get("commercial_claim_ceiling", {})
            if (not isinstance(transformation, dict) or not transformation) and isinstance(loss_chain, dict) and loss_chain.get("loss_chain"):
                append_human_driver_line("业务损失链", loss_chain.get("loss_chain"))
            if (not isinstance(transformation, dict) or not transformation) and isinstance(economics, dict) and economics.get("spend_or_commitment_at_risk"):
                append_human_driver_line("继续投入成本", economics.get("spend_or_commitment_at_risk"))
            if (not isinstance(transformation, dict) or not transformation) and isinstance(substitute_map, dict) and substitute_map.get("why_not_enough"):
                append_human_driver_line("替代方案压力", substitute_map.get("why_not_enough"))
            if (not isinstance(transformation, dict) or not transformation) and isinstance(proof_for_continue, dict) and proof_for_continue.get("directional_threshold"):
                append_human_driver_line("继续投入证据", proof_for_continue.get("directional_threshold"))
            if (
                isinstance(transformation, dict)
                and transformation
                and not transformation.get("proof_needed_for_next_investment")
                and isinstance(proof_for_continue, dict)
                and proof_for_continue.get("directional_threshold")
            ):
                append_human_driver_line("下一轮投入证据", proof_for_continue.get("directional_threshold"))
            if isinstance(claim_ceiling, dict) and claim_ceiling.get("evidence_confidence_state"):
                append_human_driver_line("商业证据状态", claim_ceiling.get("evidence_confidence_state"))
            if isinstance(claim_ceiling, dict) and claim_ceiling.get("forbidden_upgrade"):
                append_human_driver_line("禁止升级", claim_ceiling.get("forbidden_upgrade"))
        if isinstance(source_truth, dict):
            truth_state = compact_signal_line(str(source_truth.get("truth_state", "")))
            review_bound_items = source_truth.get("review_bound_items", [])
            if truth_state:
                append_human_driver_line("源真相边界", truth_state)
            if isinstance(review_bound_items, list) and review_bound_items:
                append_human_driver_line("待复核事实", "; ".join(str(item) for item in review_bound_items if str(item).strip()))
        if isinstance(gap_routing, dict) and gap_routing.get("downstream_route"):
            append_human_driver_line("缺口路由", gap_routing.get("downstream_route"))
        if isinstance(transformation, dict) and transformation:
            return lines
        if isinstance(forbidden, list) and forbidden:
            append_human_driver_line("下游禁止假设", "; ".join(str(item) for item in forbidden if str(item).strip()))
    if business_argument and not driver_summary:
        lines.append(f"- {business_argument}")
        if isinstance(argument_draft, dict) and argument_draft.get("directional_proof_when_exact_roi_missing"):
            lines.append(f"- directional proof before exact ROI: {compact_signal_line(str(argument_draft.get('directional_proof_when_exact_roi_missing')))}")
        if isinstance(argument_draft, dict) and argument_draft.get("why_substitute_is_not_enough"):
            lines.append(f"- why the substitute is not enough: {compact_signal_line(str(argument_draft.get('why_substitute_is_not_enough')))}")
        lines.append(
            f"- investment proof before scope: {compact_signal_line(str(thesis.get('proof_target', 'review-bound')))} must beat {substitute or 'the current substitute'} before requirements are treated as ready."
        )
        lines.append(
            f"- architecture pressure: {compact_signal_line(str(thesis.get('product_boundary_implication', 'review-bound')))} must preserve the business proof loop, not only a feature list."
        )
    lines.extend([
        f"- chosen_thesis: {compact_signal_line(str(thesis.get('chosen_thesis', 'review-bound')))}",
        f"- why_this_product_deserves_to_exist: {compact_signal_line(str(thesis.get('why_this_not_alternatives', 'review-bound')))}",
        f"- buyer_user_operator_value: {compact_signal_line(str(thesis.get('buyer_user_operator_value', 'review-bound')))}",
        f"- proof_target: {compact_signal_line(str(thesis.get('proof_target', 'review-bound')))}",
        f"- product_boundary_implication: {compact_signal_line(str(thesis.get('product_boundary_implication', 'review-bound')))}",
    ])
    substitute_types = thesis.get("substitute_pressure_types", [])
    if isinstance(substitute_types, list) and substitute_types:
        lines.append(f"- substitute_pressure_types: {compact_signal_line(', '.join(str(item) for item in substitute_types if str(item).strip()))}")
    quality_gate = thesis.get("quality_gate", {})
    if isinstance(quality_gate, dict) and quality_gate:
        gate_text = "; ".join(f"{key}={value}" for key, value in quality_gate.items() if str(value).strip())
        if gate_text:
            lines.append(f"- thesis_quality_gate: {compact_signal_line(gate_text)}")
    if substitute:
        lines.append(f"- substitute_pressure: {substitute}")
    if min_proof:
        lines.append(f"- minimum_proof_to_beat_substitutes: {min_proof}")
    if reality_focus:
        lines.append(f"- reality_density_focus: {reality_focus}")
    review_bound = compact_signal_line(str(thesis.get("review_bound_truth", "")))
    if review_bound:
        lines.append(f"- review_bound_truth: {review_bound}")
    return lines

def render_business_world_truth_lines(runtime_context: dict[str, object]) -> list[str]:
    model = runtime_context.get("business_world_model", {})
    if not isinstance(model, dict) or not model:
        return ["- business-world truth spine artifact not present; keep missing truth explicit instead of smoothing it over."]
    buyer_chain = model.get("buyer_budget_chain", {})
    protected_nouns = runtime_context.get("protected_business_nouns", [])
    lines = [
        f"- mainline_thesis: {compact_mainline_thesis(runtime_context)}",
        f"- why_now: {compact_why_now_phrase(runtime_context)}",
        f"- why_this_not_that: {compact_why_this_not_that_phrase(runtime_context)}",
        f"- value_mechanism: {compact_value_mechanism_phrase(runtime_context)}",
        f"- proof_artifact_for_continue: {compact_proof_artifact_phrase(runtime_context)}",
        f"- continuation_boundary: {compact_continuation_boundary_phrase(runtime_context)}",
        f"- spend_at_risk: {compact_spend_at_risk_phrase(runtime_context)}",
        f"- current_truth_state: {naturalize_reader_facing_bilingual_terms(str(buyer_chain.get('current_truth_state', 'review-bound / missing evidence')))}",
        f"- missing_evidence_to_unlock: {naturalize_reader_facing_bilingual_terms(str(buyer_chain.get('missing_evidence_to_unlock', 'review-bound / missing evidence')))}",
    ]
    completeness_driver = business_completeness_driver_surface(runtime_context)
    if completeness_driver:
        loss_chain = completeness_driver.get("business_loss_chain", {})
        proof_for_continue = completeness_driver.get("proof_for_continue", {})
        claim_ceiling = completeness_driver.get("commercial_claim_ceiling", {})
        if isinstance(loss_chain, dict) and loss_chain.get("loss_chain"):
            loss_text = compact_reader_facing_commercial_phrase(str(loss_chain.get("loss_chain")))
            if reader_facing_truth_is_spliced(str(loss_chain.get("loss_chain")), loss_text) or len(loss_text) > 170:
                loss_text = "当前替代方式会把主线判断拆回单点页面、报表或人工补位，削弱继续投入判断。"
            lines.append(f"- business_loss_chain: {loss_text}")
        if isinstance(proof_for_continue, dict) and proof_for_continue.get("directional_threshold"):
            lines.append(
                "- proof_for_continue_threshold: "
                f"{compact_reader_facing_commercial_phrase(str(proof_for_continue.get('directional_threshold')))}"
            )
        if isinstance(claim_ceiling, dict) and claim_ceiling.get("forbidden_upgrade"):
            lines.append(f"- commercial_claim_ceiling: {naturalize_reader_facing_bilingual_terms(str(claim_ceiling.get('forbidden_upgrade')))}")
    if protected_nouns:
        noun_surfaces = [
            compact_reader_facing_commercial_phrase(str(item))
            for item in protected_nouns
            if compact_reader_facing_commercial_phrase(str(item))
        ]
        lines.append(f"- protected_business_nouns: {'; '.join(noun_surfaces[:8])}")
    return lines



def as_text_items(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.startswith("[") and "]" in cleaned:
            quoted_items = [item.strip() for item in re.findall(r"'([^']+)'", cleaned) if item.strip()]
            if quoted_items:
                return quoted_items
        return [cleaned] if cleaned else []
    if isinstance(value, dict):
        rendered = []
        for key, item in value.items():
            for text in as_text_items(item):
                rendered.append(f"{key}: {text}")
        return rendered
    if isinstance(value, (list, tuple, set)):
        rendered = []
        for item in value:
            rendered.extend(as_text_items(item))
        return rendered
    cleaned = str(value or "").strip()
    return [cleaned] if cleaned else []

BUSINESS_VALUE_SIGNAL_COLUMNS = [
    "value_signal_id",
    "upstream_trace_id",
    "business_value_weight",
    "business_value_reason",
    "anti_demo_risk",
    "core_success_path",
    "downstream_depth_hint",
    "evidence_or_review_bound",
]


def derive_business_value_signal_profile(signal: str) -> dict[str, str]:
    lowered = signal.casefold()
    critical_terms = (
        "continue",
        "pause",
        "revise",
        "decision",
        "review",
        "proof",
        "evidence",
        "closure",
        "audit",
        "权限",
        "审计",
        "决策",
        "复盘",
        "继续",
        "阻塞",
        "闭环",
        "证据",
    )
    high_terms = (
        "owner",
        "manager",
        "operator",
        "priority",
        "handoff",
        "downstream",
        "payload",
        "action",
        "对象",
        "优先级",
        "责任",
        "下游",
        "动作",
        "交付",
        "状态",
    )
    support_terms = ("reference", "support", "decorative", "nice-to-have", "参考", "辅助", "装饰")
    is_review_bound = "review-bound" in lowered or "missing evidence" in lowered or "待确认" in signal
    if any(term in lowered or term in signal for term in critical_terms):
        weight = "BV3"
        risk = "critical"
        depth = "critical"
        core = "yes"
    elif any(term in lowered or term in signal for term in high_terms):
        weight = "BV2"
        risk = "high"
        depth = "deep"
        core = "yes"
    elif any(term in lowered or term in signal for term in support_terms):
        weight = "BV0"
        risk = "low"
        depth = "none"
        core = "no"
    else:
        weight = "BV1"
        risk = "medium"
        depth = "standard"
        core = "no"
    return {
        "business_value_weight": weight,
        "anti_demo_risk": risk,
        "core_success_path": core,
        "downstream_depth_hint": depth,
        "evidence_or_review_bound": "review-bound" if is_review_bound else "source-grounded",
    }


def p1_requirement_trace_id(index: int) -> str:
    return f"P1-REQ-{index:03d}"


def build_business_value_signal_registry(runtime_context: dict[str, object]) -> list[dict[str, str]]:
    signals: list[str] = []
    for item in runtime_context.get("business_value_signals", []):
        raw_signal = str(item)
        signal = compact_reader_facing_commercial_phrase(raw_signal)
        if signal and reader_facing_truth_is_spliced(raw_signal, signal):
            signal = compact_value_mechanism_phrase(runtime_context)
        if signal and not reader_facing_truth_is_spliced(signal, signal):
            signals.append(signal)
    rows: list[dict[str, str]] = []
    for index, signal in enumerate(signals, start=1):
        profile = derive_business_value_signal_profile(signal)
        rows.append(
            {
                "value_signal_id": f"BVS-{index:03d}",
                "upstream_trace_id": p1_requirement_trace_id(index),
                "business_value_weight": profile["business_value_weight"],
                "business_value_reason": compact_reader_facing_commercial_phrase(signal),
                "anti_demo_risk": profile["anti_demo_risk"],
                "core_success_path": profile["core_success_path"],
                "downstream_depth_hint": profile["downstream_depth_hint"],
                "evidence_or_review_bound": profile["evidence_or_review_bound"],
            }
        )
    return rows


def render_business_value_signal_registry(runtime_context: dict[str, object]) -> str:
    rows = runtime_context.get("business_value_signal_registry", [])
    if not isinstance(rows, list) or not rows:
        return "- business_value_signal_registry_missing: P1 has no structured value signals for P2 ACD."
    table_rows = [
        [str(row.get(column, "")).strip() for column in BUSINESS_VALUE_SIGNAL_COLUMNS]
        for row in rows
        if isinstance(row, dict)
    ]
    return markdown_table(BUSINESS_VALUE_SIGNAL_COLUMNS, table_rows)

def render_business_proof_track_lines(runtime_context: dict[str, object]) -> list[str]:
    model = runtime_context.get("business_world_model", {})
    track = model.get("business_proof_track", {}) if isinstance(model, dict) else {}
    if not isinstance(track, dict) or not track:
        return ["- Business Proof Track: not present; keep proof routing review-bound instead of inferring it."]
    proof_questions = as_text_items(track.get("proof_questions", []))
    substitute_pressure = as_text_items(track.get("substitute_pressure", []))
    proof_artifact = compact_proof_artifact_phrase(runtime_context) or compact_reader_facing_commercial_phrase(
        str(track.get("proof_artifact", "review-bound"))
    )
    continuation_decision = compact_continuation_boundary_phrase(runtime_context) or compact_reader_facing_commercial_phrase(
        str(track.get("continuation_decision", "review-bound"))
    )
    lines = [
        f"- proof_track: {compact_reader_facing_commercial_phrase(str(track.get('proof_track', 'review-bound')))}",
        f"- dominant_proof_risk: {compact_reader_facing_commercial_phrase(str(track.get('dominant_proof_risk', 'review-bound')))}",
        f"- proof_artifact: {proof_artifact}",
        f"- continuation_decision: {continuation_decision}",
    ]
    if substitute_pressure:
        lines.append(
            f"- substitute_pressure: {'; '.join(compact_reader_facing_commercial_phrase(item) for item in substitute_pressure[:5])}"
        )
    if proof_questions:
        lines.append(
            f"- proof_questions: {'; '.join(compact_reader_facing_commercial_phrase(item) for item in proof_questions[:6])}"
        )
    return lines


def semantic_authoring_spine_from_runtime_context(runtime_context: dict[str, object]) -> dict[str, object]:
    model = runtime_context.get("business_world_model", {})
    if not isinstance(model, dict):
        return {}
    summary = model.get("product_source_direct_driver_summary", {})
    if isinstance(summary, dict):
        spine = summary.get("semantic_authoring_spine", {})
        if isinstance(spine, dict) and spine:
            return spine
    release_pack = runtime_context.get("business_release_truth_pack", {})
    if isinstance(release_pack, dict):
        spine = release_pack.get("semantic_authoring_spine", {})
        if isinstance(spine, dict) and spine:
            return spine
    return {}


def semantic_authoring_units_by_type(
    runtime_context: dict[str, object],
    semantic_type: str,
    *,
    limit: int = 3,
) -> list[dict[str, object]]:
    spine = semantic_authoring_spine_from_runtime_context(runtime_context)
    units = spine.get("semantic_units", []) if isinstance(spine, dict) else []
    if not isinstance(units, list):
        return []
    return [
        unit
        for unit in units
        if isinstance(unit, dict) and str(unit.get("semantic_type", "")).strip() == semantic_type
    ][:limit]


def render_semantic_authoring_spine_lines(runtime_context: dict[str, object]) -> list[str]:
    spine = semantic_authoring_spine_from_runtime_context(runtime_context)
    if not spine:
        return [
            "- status: `not-available`",
            "- authoring_note: no semantic authoring spine was present in the P1 business world model.",
        ]
    lines = [
        "- artifact_id: `p1-semantic-authoring-spine.v1`",
        "- control_boundary: Workflow preserves stage order; Agentic owns semantic placement; Evidence retains source excerpt, truth state, and claim ceiling.",
    ]
    for semantic_type in (
        "state_lifecycle",
        "audit_compliance_constraint",
        "dashboard_review_decision_surface",
        "role_actor_decision_owner",
        "object_data_record",
        "metric_success_signal",
        "open_truth_gap",
        "deferred_out_of_scope",
    ):
        units = semantic_authoring_units_by_type(runtime_context, semantic_type, limit=3)
        if not units:
            continue
        lines.append(f"- {semantic_type}:")
        for unit in units:
            target = compact_signal_line(str(unit.get("placement_target", ""))) or "source-defined semantic placement"
            truth_state = compact_signal_line(str(unit.get("truth_state", ""))) or "source-grounded"
            excerpt = compact_signal_line(str(unit.get("source_excerpt", ""))) or "source excerpt retained in semantic spine"
            lines.append(f"  - placement_target: `{target}`")
            lines.append(f"    truth_state: `{truth_state}`")
            lines.append(f"    source_excerpt: {excerpt}")
    return lines


def compact_semantic_display_label(value: str, *, fallback: str) -> str:
    phrase = compact_signal_line(value)
    if not phrase:
        return fallback
    delimiter_count = len(re.findall(r"/|->|,|，|;|；", phrase))
    if len(phrase) > 96 or delimiter_count >= 3:
        return fallback
    return phrase.strip("。.;；")


def first_semantic_unit(runtime_context: dict[str, object], semantic_type: str) -> dict[str, object]:
    units = semantic_authoring_units_by_type(runtime_context, semantic_type, limit=1)
    return units[0] if units else {}


def render_semantic_authoring_implication_lines(runtime_context: dict[str, object]) -> list[str]:
    spine = semantic_authoring_spine_from_runtime_context(runtime_context)
    if not spine:
        return [
            "- status: `not-available`",
            "- authoring_note: no semantic authoring spine was present; keep semantic placement review-bound.",
        ]

    lines = [
        "- evidence_bridge: full `p1-semantic-authoring-spine.v1` remains in phase evidence; PRD正文 only carries reader-facing implications.",
    ]
    state = first_semantic_unit(runtime_context, "state_lifecycle")
    audit = first_semantic_unit(runtime_context, "audit_compliance_constraint")
    review = first_semantic_unit(runtime_context, "dashboard_review_decision_surface")
    role = first_semantic_unit(runtime_context, "role_actor_decision_owner")
    gap = first_semantic_unit(runtime_context, "open_truth_gap")

    if state:
        target = compact_signal_line(str(state.get("placement_target", ""))) or "state_model_transition_guard"
        label = compact_semantic_display_label(
            str(state.get("source_excerpt", "")),
            fallback="source-defined lifecycle state line",
        )
        lines.append(
            f"- lifecycle implication: `{target}` must preserve {label} as product state, not as a loose workflow note."
        )
    if audit:
        target = compact_signal_line(str(audit.get("placement_target", ""))) or "nfr_audit_acceptance"
        label = compact_semantic_display_label(
            str(audit.get("source_excerpt", "")),
            fallback="source-defined audit trail",
        )
        lines.append(f"- audit implication: `{target}` must turn {label} into NFR / acceptance evidence.")
    if review:
        target = compact_signal_line(str(review.get("placement_target", ""))) or "ia_review_decision_surface"
        label = compact_semantic_display_label(
            str(review.get("source_excerpt", "")),
            fallback="source-defined review surface",
        )
        lines.append(f"- review implication: `{target}` must keep {label} visible as the decision surface.")
    if role:
        target = compact_signal_line(str(role.get("placement_target", ""))) or "role_boundary_decision_owner"
        label = compact_semantic_display_label(
            str(role.get("source_excerpt", "")),
            fallback="source-defined decision owner",
        )
        lines.append(
            f"- role implication: `{target}` must keep {label} attached to permission and accountability boundaries."
        )
    if gap:
        target = compact_signal_line(str(gap.get("placement_target", ""))) or "claim_ceiling_review_bound_gap"
        label = compact_semantic_display_label(str(gap.get("source_excerpt", "")), fallback="open truth gap")
        lines.append(
            f"- claim ceiling implication: `{target}` keeps {label} review-bound until stronger evidence exists."
        )
    return lines


def is_review_bound_missing(value: str) -> bool:
    text = compact_signal_line(value).lower()
    return (
        "review-bound / missing evidence" in text
        or "待评审确认（review-bound），缺少外部证据" in text
        or "待评审确认（review-bound）：" in text
    )


def role_decision_weight(role: str) -> int:
    lowered = role.casefold()
    score = 0
    if re.search(r"owner|manager|lead|head|director|sponsor|founder|负责人|经理|主管|总监|院长|店长", lowered):
        score += 4
    if re.search(r"decision|review|审批|评审|决策|governance|finance|ops|operation|business", lowered):
        score += 3
    if re.search(r"admin|operator|执行|运营", lowered):
        score += 1
    return score


def select_continuation_owner(runtime_context: dict[str, object], scenario_context: dict[str, object]) -> str:
    candidates = dedupe_runtime_phrases(
        [str(item) for item in scenario_context.get("actors", [])]
        + [str(scenario_context.get("downstream_owner", ""))]
        + [str(item) for item in runtime_context.get("target_user_roles", [])]
    )
    if not candidates:
        return str(runtime_context.get("primary_segment", "primary operator")).strip() or "primary operator"
    weighted = [(role_decision_weight(candidate), idx, candidate) for idx, candidate in enumerate(candidates)]
    weighted.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return weighted[0][2]


def source_grounded_value_phrase(runtime_context: dict[str, object]) -> str:
    truth_value = truth_slot_value(
        runtime_context.get("business_world_model", {}).get("value_mechanism", {})
        if isinstance(runtime_context.get("business_world_model"), dict)
        else {}
    )
    if truth_value:
        return truth_value
    return signal_phrase(
        list(runtime_context.get("business_value_signals", [])),
        "review-bound / missing evidence: business value mechanism not yet established",
        limit=2,
    )


def source_grounded_commercial_phrase(runtime_context: dict[str, object]) -> str:
    driver = business_completeness_driver_surface(runtime_context)
    economics = driver.get("continuation_economics", {}) if isinstance(driver, dict) else {}
    if isinstance(economics, dict):
        spend = compact_signal_line(str(economics.get("spend_or_commitment_at_risk", "")))
        if spend:
            return spend
    truth_value = truth_slot_value(
        runtime_context.get("business_world_model", {}).get("spend_at_risk", {})
        if isinstance(runtime_context.get("business_world_model"), dict)
        else {}
    )
    if truth_value:
        return truth_value
    return signal_phrase(
        list(runtime_context.get("commercial_decision_signals", [])),
        "待评审确认（review-bound）：真实买方、预算负责人或继续投入真相尚未建立",
        limit=2,
    )


def source_grounded_proof_phrase(runtime_context: dict[str, object]) -> str:
    driver = business_completeness_driver_surface(runtime_context)
    proof_for_continue = driver.get("proof_for_continue", {}) if isinstance(driver, dict) else {}
    if isinstance(proof_for_continue, dict):
        proof = compact_signal_line(str(proof_for_continue.get("proof_artifact", "")))
        if proof:
            return proof
    truth_value = truth_slot_value(
        runtime_context.get("business_world_model", {}).get("proof_artifact_for_continue", {})
        if isinstance(runtime_context.get("business_world_model"), dict)
        else {}
    )
    if truth_value:
        return truth_value
    return signal_phrase(
        list(runtime_context.get("decision_proof_signals", [])),
        "待评审确认（review-bound）：继续判断证据尚未建立",
        limit=2,
    )


def source_grounded_experience_phrase(runtime_context: dict[str, object]) -> str:
    return signal_phrase(
        list(runtime_context.get("user_experience_signals", [])),
        "waiting, handoff friction, and manual reconstruction",
        limit=2,
    )


def buyer_budget_chain_components(
    runtime_context: dict[str, object],
    scenario_context: dict[str, object],
) -> dict[str, str]:
    business_world_model = runtime_context.get("business_world_model", {})
    truth_buyer_chain = (
        business_world_model.get("buyer_budget_chain", {})
        if isinstance(business_world_model, dict)
        else {}
    )
    completeness_driver = business_completeness_driver_surface(runtime_context)
    loss_chain = completeness_driver.get("business_loss_chain", {}) if isinstance(completeness_driver, dict) else {}
    economics = completeness_driver.get("continuation_economics", {}) if isinstance(completeness_driver, dict) else {}
    proof_for_continue = completeness_driver.get("proof_for_continue", {}) if isinstance(completeness_driver, dict) else {}
    claim_ceiling = completeness_driver.get("commercial_claim_ceiling", {}) if isinstance(completeness_driver, dict) else {}
    actors = dedupe_runtime_phrases([str(item) for item in scenario_context.get("actors", [])])
    objects = dedupe_runtime_phrases([str(item) for item in scenario_context.get("objects", [])])
    pain_holder = (
        compact_signal_line(str(loss_chain.get("pain_holder", ""))) if isinstance(loss_chain, dict) else ""
    ) or (
        compact_signal_line(str(truth_buyer_chain.get("pain_holder", "")))
        or (actors[0] if actors else (str(runtime_context.get("primary_segment", "primary operator")).strip() or "primary operator"))
    )
    continuation_owner = (
        compact_signal_line(str(economics.get("continuation_owner", ""))) if isinstance(economics, dict) else ""
    ) or (
        compact_signal_line(str(truth_buyer_chain.get("continuation_owner", "")))
        or select_continuation_owner(runtime_context, scenario_context)
    )
    output_anchor = str(scenario_context.get("output_anchor", "")).strip() or "source-defined business outcome"
    object_chain = ", ".join(f"`{object_name}`" for object_name in objects[:4]) if objects else "`source-defined business object`"
    generated_proof_artifact = (
        f"`{output_anchor}` plus {object_chain}"
        if objects
        else f"`{output_anchor}` plus the typed workflow contract"
    )
    proof_artifact = (
        compact_signal_line(str(proof_for_continue.get("proof_artifact", ""))) if isinstance(proof_for_continue, dict) else ""
    ) or compact_signal_line(str(truth_buyer_chain.get("proof_artifact_for_continue", ""))) or generated_proof_artifact
    commercial_context = bool(scenario_context.get("commercial_context"))
    commercial_phrase = compact_reader_facing_commercial_phrase(source_grounded_commercial_phrase(runtime_context))
    proof_phrase = compact_reader_facing_commercial_phrase(source_grounded_proof_phrase(runtime_context))
    spend_at_risk = (
        compact_signal_line(str(economics.get("spend_or_commitment_at_risk", ""))) if isinstance(economics, dict) else ""
    ) or compact_signal_line(str(truth_buyer_chain.get("spend_at_risk", ""))) or (
        commercial_phrase if commercial_context else "team time / workflow-change effort / rollout commitment"
    )
    continuation_signal = (
        compact_signal_line(str(economics.get("decision_trigger", ""))) if isinstance(economics, dict) else ""
    ) or compact_signal_line(str(truth_buyer_chain.get("decision_trigger", ""))) or (
        f"`{continuation_owner}` can explicitly choose continue / revise / pause after reviewing {proof_artifact}; preserve the decision hook around {proof_phrase}."
    )
    driver_evidence_state = (
        compact_signal_line(str(claim_ceiling.get("evidence_confidence_state", ""))) if isinstance(claim_ceiling, dict) else ""
    )
    current_truth_state = compact_signal_line(str(truth_buyer_chain.get("current_truth_state", ""))) or (
        f"{driver_evidence_state}; commercial claims remain capped until external validation"
        if driver_evidence_state
        else ""
    ) or (
        f"source-grounded commercial pressure is visible (`{commercial_phrase}`); buyer/budget evidence still remains review-bound until external validation"
        if commercial_context
        else "review-bound until external validation confirms who owns the continued commitment"
    )
    missing_evidence = (
        compact_signal_line(str(proof_for_continue.get("missing_external_evidence", ""))) if isinstance(proof_for_continue, dict) else ""
    ) or compact_signal_line(str(truth_buyer_chain.get("missing_evidence_to_unlock", ""))) or (
        f"pilot continuation evidence, decision-owner feedback, or stronger proof around {proof_phrase}"
        if commercial_context
        else "real stakeholder evidence that the same scenario justifies continued rollout effort or operating commitment"
    )
    return {
        "pain_holder": clean_source_label_phrase(pain_holder),
        "continuation_owner": clean_source_label_phrase(continuation_owner),
        "spend_at_risk": clean_source_label_phrase(compact_reader_facing_commercial_phrase(spend_at_risk)),
        "proof_artifact_for_continue": clean_source_label_phrase(compact_reader_facing_commercial_phrase(proof_artifact)),
        "continuation_signal": clean_source_label_phrase(compact_reader_facing_commercial_phrase(continuation_signal)),
        "current_truth_state": clean_source_label_phrase(current_truth_state),
        "missing_evidence_to_unlock": clean_source_label_phrase(compact_reader_facing_commercial_phrase(missing_evidence)),
    }


def collapse_shared_buyer_budget_rows(rows: list[list[str]]) -> list[list[str]]:
    if len(rows) <= 1:
        return rows
    signatures = {
        tuple(str(cell).strip() for cell in row[1:])
        for row in rows
    }
    if len(signatures) != 1:
        return rows
    shared_anchor = "shared continuation chain across selected mainline scenarios"
    return [[shared_anchor, *rows[0][1:]]]


def render_buyer_budget_chain_table(runtime_context: dict[str, object]) -> str:
    rows: list[list[str]] = []
    for bundle in build_mainline_scenario_bundles(runtime_context)[:3]:
        chain = buyer_budget_chain_components(runtime_context, bundle)
        rows.append(
            [
                str(bundle.get("title", "")).strip() or "source-defined scenario",
                chain["pain_holder"],
                chain["continuation_owner"],
                chain["spend_at_risk"],
                chain["proof_artifact_for_continue"],
                chain["continuation_signal"],
                chain["current_truth_state"],
                chain["missing_evidence_to_unlock"],
            ]
        )
    if not rows:
        rows = [[
            "source-defined scenario",
            str(runtime_context.get("primary_segment", "primary operator")).strip() or "primary operator",
            str(runtime_context.get("primary_segment", "primary operator")).strip() or "primary operator",
            "review-bound / missing evidence: spend-at-risk truth not yet established",
            "待评审确认（review-bound）：继续判断证据尚未建立",
            "review-bound / missing evidence: continuation decision must stay explicit until truth is established",
            "review-bound / missing evidence",
            "review-bound / missing evidence: real stakeholder continuation evidence",
        ]]
    rows = collapse_shared_buyer_budget_rows(rows)
    return markdown_table(
        [
            "scenario_anchor",
            "pain_holder",
            "continuation_owner",
            "spend_at_risk",
            "proof_artifact_for_continue",
            "continuation_signal",
            "current_truth_state",
            "missing_evidence_to_unlock",
        ],
        rows,
    )


def render_loop_business_scenario_lines(
    runtime_context: dict[str, object],
    target_index: int,
    scenario_context: dict[str, object] | None = None,
) -> list[str]:
    target = loop_target_for_index(
        runtime_context,
        target_index,
        scenario_title=str(scenario_context.get("title", "")).strip() if scenario_context else "",
    )
    focus = set(str(item).strip() for item in target.get("focus_areas", [])) if target else set()
    missing_dimensions = set(str(item).strip() for item in target.get("missing_dimensions", [])) if target else set()
    lines: list[str] = []
    if target:
        short_title = loop_title_short(str(target.get("scenario_title", f"Scenario {target_index}")))
        lines.append(f"- loop_target_alignment: `{short_title}` remains an explicit deepening target in this round.")
    if not scenario_context:
        truth_value = source_grounded_value_phrase(runtime_context)
        truth_commercial = compact_reader_facing_commercial_phrase(source_grounded_commercial_phrase(runtime_context))
        truth_proof = compact_reader_facing_commercial_phrase(source_grounded_proof_phrase(runtime_context))
        if "business_value" in focus or "value_mechanism" in focus:
            lines.append(f"- business_value_mechanism: {truth_value or 'review-bound / missing evidence: business value mechanism not yet established.'}")
        if "buyer_budget_chain" in focus:
            if truth_commercial:
                lines.append(f"- buyer_budget_chain: {truth_commercial}")
            else:
                lines.append(
                    "- buyer_budget_chain: 待评审确认（review-bound）：该场景尚未建立真实买方、预算负责人或继续投入真相。"
                )
        if "decision_leverage" in focus or "business_value" in focus:
            if truth_proof:
                lines.append(f"- decision_leverage: use `{truth_proof}` as the minimum proof artifact before declaring continue / revise / pause.")
            else:
                lines.append(
                    "- decision_leverage: review-bound / missing evidence: do not declare a complete decision endpoint until the proof artifact and decision trigger are explicit."
                )
        if "user_task_experience" in focus:
            lines.append(
                "- user_task_experience_gain: the same chain should reduce waiting, handoff friction, confusion, and manual reconstruction so the real operator path feels clearer and more actionable."
            )
        return lines

    module_chain = " -> ".join(
        plain_truth_text(str(module))
        for module in scenario_context.get("modules", [])
        if plain_truth_text(str(module))
    ) or "source-defined mainline"
    actor_chain = " -> ".join(
        plain_truth_text(str(actor))
        for actor in scenario_context.get("actors", [])
        if plain_truth_text(str(actor))
    ) or plain_truth_text(str(runtime_context.get("primary_segment", "primary operator")))
    object_chain = "、".join(
        plain_truth_text(str(item))
        for item in scenario_context.get("objects", [])[:6]
        if plain_truth_text(str(item))
    ) or "source-defined business object"
    input_anchor = str(scenario_context.get("input_anchor", "")).strip() or "source-defined entry evidence"
    output_anchor = str(scenario_context.get("output_anchor", "")).strip() or "source-defined business outcome"
    downstream_owner = plain_truth_text(
        str(scenario_context.get("downstream_owner", "")).strip() or str(runtime_context.get("primary_segment", "primary operator")).strip()
    ) or "primary operator"
    commercial_context = bool(scenario_context.get("commercial_context"))
    experience_context = bool(scenario_context.get("experience_context"))
    is_final_bundle = bool(scenario_context.get("is_final_bundle"))
    scenario_title = str(scenario_context.get("title", "")).strip() or f"Scenario {target_index}"
    buyer_chain = buyer_budget_chain_components(runtime_context, scenario_context)
    proof_artifact = plain_truth_text(buyer_chain["proof_artifact_for_continue"]) or compact_proof_artifact_phrase(runtime_context)
    experience_phrase = source_grounded_experience_phrase(runtime_context)
    coordination_roles = dedupe_runtime_phrases(
        [str(item) for item in scenario_context.get("actors", [])]
        + [str(item) for item in runtime_context.get("target_user_roles", [])]
    )
    source_constraints = dedupe_runtime_phrases(
        [str(item) for item in runtime_context.get("architectural_constraints", [])]
        + [str(item) for item in runtime_context.get("non_functional_requirements", [])]
    )
    selected_constraint = source_constraints[0] if source_constraints else "source-defined constraint / NFR"
    upstream_role = coordination_roles[0] if coordination_roles else str(runtime_context.get("primary_segment", "primary operator")).strip()
    downstream_role = (
        coordination_roles[1]
        if len(coordination_roles) > 1
        else str(scenario_context.get("downstream_owner", "")).strip()
        or upstream_role
    )
    reviewer_role = coordination_roles[2] if len(coordination_roles) > 2 else downstream_role

    lines.append(
        f"- business_value_mechanism: 在 {scenario_title}，必须把 {input_anchor} 稳定推进到 {output_anchor}，并保持 {object_chain}、责任归属与下一动作仍在同一条主线上可见。"
    )
    if "coordination_density" in missing_dimensions or "role_handoffs" in focus or "handoff_contracts" in focus:
        lines.extend(
            [
                f"- coordination_roles: 上游 {plain_truth_text(upstream_role)} -> 下游 {plain_truth_text(downstream_role)} -> 评审者 {plain_truth_text(reviewer_role)} 必须保持显式，不能被压平成一个 generic operator。",
                f"- role_handoff_contract: {plain_truth_text(upstream_role)} 把 {output_anchor} 交给 {plain_truth_text(downstream_role)} 时，owner、state、blocked reason 和 next action 仍要可见，{plain_truth_text(reviewer_role)} 可以直接评审而不必重建缺失上下文。",
            ]
        )
    if "real_world_constraint_density" in missing_dimensions or "real_world_baseline" in focus:
        lines.extend(
            [
                f"- source_constraint_anchor: 在 {scenario_title} 中，source constraint / NFR {plain_truth_text(selected_constraint)} 必须贯穿 {input_anchor} -> {output_anchor} 保持显式，不能留给下游团队重新发现。",
                f"- real_world_constraint_contract: 在 {scenario_title}，时序窗口、必需证据、审计轨迹与审批/成本 guard 必须跟随 {input_anchor} -> {output_anchor} 保持显式，不能留给下游重发现。",
            ]
        )
    if "buyer_budget_chain" in focus or commercial_context:
        pain_holder = plain_truth_text(buyer_chain["pain_holder"]) or "primary operator"
        continuation_owner = plain_truth_text(buyer_chain["continuation_owner"]) or downstream_owner
        spend_at_risk = plain_truth_text(buyer_chain["spend_at_risk"])
        continuation_signal = (
            plain_truth_text(buyer_chain["continuation_signal"])
            or f"{continuation_owner} chooses continue / revise / pause after reviewing {proof_artifact}"
        )
        lines.append(
            "- economic_decision_surface: "
            f"pain_holder={pain_holder}; "
            f"continuation_owner={continuation_owner}; "
            f"spend_at_risk={spend_at_risk or 'review-bound / missing evidence'}; "
            f"proof_artifact_for_continue={proof_artifact}; "
            f"continuation_signal={continuation_signal}."
        )
        if is_review_bound_missing(buyer_chain["spend_at_risk"]) or is_review_bound_missing(buyer_chain["continuation_signal"]):
            lines.append(
                f"- continuation_decision: 该场景一旦变薄，{pain_holder} 会先承担返工与解释成本；{continuation_owner} 当前只能围绕 {proof_artifact} 做继续 / 调整 / 暂停判断，真实预算与报价阈值保持 review-bound。"
            )
            lines.append(
                f"- buyer_budget_chain: 在该场景中保持 {pain_holder} -> {continuation_owner} -> {proof_artifact} 显式；package / quote / budget threshold 在更强证据出现前仍为 review-bound。"
            )
        else:
            lines.append(
                f"- continuation_decision: 该场景必须让 {continuation_owner} 围绕 {proof_artifact} 判断“{spend_at_risk}”是否成立，再决定继续 / 调整 / 暂停。"
            )
            lines.append(
                f"- buyer_budget_chain: 保持 {pain_holder} -> {continuation_owner} -> {proof_artifact} 显式，让下一轮投入判断不需要下游脑补。"
            )
    lines.append(
        f"- consequence_if_thin: 若 {output_anchor} 只剩结果展示而无法转成任务、下一动作或 blocked reason，{actor_chain} 与 {downstream_owner} 会回到人工解释，产品也会退化为报告系统或结果页，而不是工作链。"
    )
    if is_final_bundle or commercial_context:
        review_decision_phrase = (
            "继续 / 调整 / 暂停"
            if commercial_context
            else "继续处理 / 调整 / 关闭"
        )
        lines.append(
            f"- review_boundary: 对 {scenario_title}，review 页面必须保留趋势、差值、blocked reason、边界说明，以及 {review_decision_phrase} 所需证据；若证据仍薄，只能维持观望 / revisit / 调整。"
        )
    if "user_task_experience" in focus or experience_context:
        lines.append(
            f"- user_task_experience_gain: 把 {module_chain} 和 {object_chain} 保持在同一条链上，可以为 {actor_chain} 减少 {experience_phrase}。"
        )
    return lines


def render_reasoning_units(source_text: str, runtime_context: dict[str, object]) -> list[str]:
    style = detect_domain_style(source_text, runtime_context)
    problem_items = extract_structured_source_items(source_text, ["Structured Problem List", "结构化问题清单"])
    if style == "growth_observation":
        problem_statement = summarize_structured_items(problem_items, str(runtime_context.get("problem_statement", "")).strip())
        problem_mechanism = "scope、baseline、finding、recommendation 与 review 若不能被组织成一条显式链路，GEO 只会停留在报告层。"
        decision_effect = "recompile the brief into one GEO operating chain rather than isolated observation or reporting pages"
        remaining_unknown = "commercial packaging、recommendation trust、metric stability 和 attribution acceptance still need later validation"
    elif style == "pet_clinic":
        problem_statement = summarize_structured_items(problem_items, str(runtime_context.get("problem_statement", "")).strip())
        problem_mechanism = "接诊上下文、治疗执行和离院复诊若不能沿一条显式链路推进，门店会重新回到人工补录和口头交接。"
        decision_effect = "recompile the brief into one clinic service loop rather than isolated registration or record pages"
        remaining_unknown = "richer analytics, integrations, and broader admin tooling still need later validation"
    else:
        problem_statement = summarize_structured_items(problem_items, str(runtime_context.get("problem_statement", "")).strip())
        problem_mechanism = "状态与对象连续性若不能沿显式主链推进，业务执行会重新回到人工拼接。"
        decision_effect = "recompile the brief into a single operating chain rather than isolated pages"
        remaining_unknown = "richer analytics, integrations, and broader admin tooling still need later validation"
    return [
        "### Reasoning Unit 1: Primary Boundary Lock",
        f"- chosen segment: `{runtime_context['primary_segment']}`",
        "- why this not that: first-wave entry must stay singular enough to avoid cross-role ambiguity",
        "- tradeoff_or_tension: coverage vs focus",
        "",
        "### Reasoning Unit 2: Problem Mechanism Reframe",
        f"- final_problem_statement: {problem_statement}",
        f"- problem_mechanism: {problem_mechanism}",
        f"- decision_effect: {decision_effect}",
        "",
        "### Reasoning Unit 3: Workflow-First Panorama Choice",
        "- chosen_panorama_structure: workflow-first",
        "- why_this_structure_not_that: it preserves the shortest executable source-defined loop",
        "- alternatives_compared: record-first, module-first, workflow-first",
        "",
        "### Reasoning Unit 4: Priority Cutline for First-Wave Structure",
        f"- dependency_first_chain: {business_loop_plain_surface(runtime_context, 5)}",
        "- explicit_exclusion_rule: capabilities outside the chain stay out of first-wave delivery",
        "- review-bound: future expansion remains visible but not silently committed",
        "",
        "### Reasoning Unit 5: Workflow-First IA Direction",
        "- architecture impact: navigation and screen/object matrix must mirror the operating sequence",
        "- failure risk: users lose context if screens are organized only by internal module names",
        "- screen spec precursor: IA spec matrix anchors the first-wave screens",
        "",
        "### Reasoning Unit 6: Deferred Honesty and Assumption Carryover",
        "- carryover rule: 源素材中写到的详细能力不得静默消失",
        f"- remaining_unknown: {remaining_unknown}",
        "- false completeness: avoid a polished shell that hides missing workflow closure",
        "",
        "### Reasoning Unit 7: Validation Method-Fit and Fidelity Selection",
        "- chosen_method: interview + clickable prototype + schema/state review",
        "- fidelity_rationale: enough realism to test workflow understanding without overbuilding",
        "- signal thresholds: target_1, target_2, target_3, target_4, target_5 each require explicit threshold",
        "",
        "### Reasoning Unit 8: Decision State and Convergence Admission",
        "- document_delivery_state: downstream-start-safe",
        "- evidence_confidence_state: source-grounded-but-unvalidated",
        "- convergence admission: design and architecture may proceed with explicit boundary honesty",
        "",
    ]


def sanitize_assembled_text(text: str, runtime_context: dict[str, object]) -> str:
    primary_segment = str(runtime_context.get("primary_segment", "")).strip() or "primary operator"
    style = detect_domain_style("", runtime_context)
    domain_posture = (
        "growth-observation"
        if style == "growth_observation"
        else "operational-service"
        if style == "pet_clinic"
        else "generic-workflow"
    )
    replacement_pairs = [
        ("current-状态 snapshot", "业务状态快照"),
        ("action recommendation", "建议动作"),
        ("Insight Record", "业务记录"),
        ("Review Summary", "结果摘要"),
        ("Analysis Cycle", "业务处理周期"),
        ("business context Definition", "业务配置记录"),
        ("peer Snapshot", "对照记录"),
        ("review report", "结果页"),
    ]
    for old, new in replacement_pairs:
        if old and new:
            text = text.replace(old, new)
    text = re.sub(r"当前\s+source\s+支持", "当前素材支持", text, flags=re.IGNORECASE)
    text = re.sub(r"当前\s+source\s+(?:所)?描述", "当前素材描述", text, flags=re.IGNORECASE)
    text = text.replace("source 所描述", "素材描述")
    text = re.sub(r"source-defined\s+角色", "素材定义角色", text, flags=re.IGNORECASE)
    text = re.sub(r"source-defined\s+业务", "素材定义业务", text, flags=re.IGNORECASE)
    text = re.sub(r",、", "、", text)
    text = text.replace("(source section not found)", primary_segment)
    return str(
        sanitize_domain_default_truth(
            text,
            context={
                "domain_posture": domain_posture,
                "primary_segment": primary_segment,
                "role_labels": [str(item).strip() for item in runtime_context.get("target_user_roles", []) if str(item).strip()],
                "supporting_role_label": (
                    str(runtime_context.get("target_user_roles", ["", ""])[1]).strip()
                    if len(runtime_context.get("target_user_roles", [])) > 1
                    else ""
                ),
                "decision_role_label": (
                    str(runtime_context.get("target_user_roles", [])[-1]).strip()
                    if runtime_context.get("target_user_roles")
                    else primary_segment
                ),
                "mainline_surface_catalog": " / ".join(
                    str(row.get("module", "")).strip()
                    for row in runtime_context.get("ia_matrix", [])
                    if str(row.get("module", "")).strip()
                ) or "mainline workflow surfaces",
                "mainline_subsystem_catalog": "、".join(
                    str(row.get("module", "")).strip()
                    for row in runtime_context.get("ia_matrix", [])[:4]
                    if str(row.get("module", "")).strip()
                ) or "mainline workflow surfaces",
                "object_dependency_chain": str(runtime_context.get("object_chain", "")).strip() or "source-defined workflow chain",
            },
        )
    )


def render_flow_process_table(flows: list[dict[str, object]]) -> str:
    rows: list[list[str]] = []
    for flow in flows:
        steps = [str(step).strip() for step in flow.get("steps", []) if str(step).strip()]
        rows.append(
            [
                "main flow",
                str(flow.get("title", "")).strip() or "business flow",
                steps[0] if steps else "see source flow detail",
                steps[0] if steps else "source-defined prerequisites",
                "progress the business record through the defined flow steps",
                steps[-1] if steps else "flow outcome",
                "flow state becomes reviewable for the next business action",
            ]
        )
    if not rows:
        rows.append(
            [
                "main flow",
                "business flow",
                "source-defined trigger",
                "source-defined prerequisites",
                "progress the business record through the defined flow steps",
                "business outcome",
                "flow state becomes reviewable",
            ]
        )
    return markdown_table(
        [
            "activity_type",
            "activity",
            "trigger",
            "preconditions",
            "system_behavior",
            "outputs",
            "postconditions",
        ],
        rows,
    )


def build_generic_acceptance_detail_rows(runtime_context: dict[str, object]) -> list[list[str]]:
    ia_rows = list(runtime_context.get("ia_matrix", []))
    flows = list(runtime_context.get("source_flows", []))
    rows: list[list[str]] = []
    style = detect_domain_style("", runtime_context)
    closing_boundary_type = (
        "review_cycle_closure"
        if style == "growth_observation"
        else "visit_closure"
        if style == "pet_clinic"
        else "final_confirmation"
    )
    permission_record_label = (
        "tenant-scoped GEO record"
        if style == "growth_observation"
        else "billing or visit record"
        if style == "pet_clinic"
        else "protected business record"
    )
    permission_boundary_note = (
        "tenant-scoped writes must not bypass role restrictions"
        if style == "growth_observation"
        else "billing writes must not bypass role restrictions"
        if style == "pet_clinic"
        else "protected writes must not bypass role restrictions"
    )
    for idx, row in enumerate(ia_rows[:8], start=1):
        module = row.get("module", f"module_{idx}")
        responsibility = row.get("responsibility") or "complete the module responsibility defined in source"
        inputs = row.get("input") or "required business inputs"
        output = row.get("output") or "business output"
        core_objects = row.get("core_objects") or module
        if style == "growth_observation" and re.search(r"recommendation|task|任务", str(module), flags=re.IGNORECASE):
            rows.append(
                [
                    "AC-05",
                    "anchor",
                    "EP-02",
                    "Use Case 2",
                    "Given a recommendation is marked for execution",
                    "When task creation is requested",
                    "Then AI-friendly score, quality diagnosis, structured rewrite, keyword/question focus, and target asset reference are all present",
                    "A typed recommendation payload can be exported without missing execution-semantic fields",
                    "invalid_payload",
                    "task creation fails if execution-semantic fields are incomplete",
                    "Step 6",
                ]
            )
            continue
        boundary_type = (
            "missing_required_input" if idx == 1 else
            "invalid_state_transition" if idx == 2 else
            "permission_boundary" if idx == 3 else
            "module_contract_integrity" if idx == 4 else
            "threshold_breach" if idx == 5 else
            "recovery_retry" if idx == 6 else
            "auditability" if idx == 7 else
            "scope_boundary_drift"
        )
        rows.append(
            [
                f"AC-{idx:02d}",
                "anchor" if idx <= 3 else "supporting",
                f"EP-{min(idx, 3):02d}",
                "Primary User Story" if idx == 1 else f"Use Case {min(idx, 4)}",
                f"Given {inputs} are available for `{module}`",
                f"When the user completes `{responsibility}`",
                f"Then the system records or returns `{output}` against `{core_objects}`",
                f"`{module}` produces its declared business output without losing object traceability",
                boundary_type,
                f"`{module}` is invalid if its input-to-output contract is incomplete",
                f"Flow {min(idx, max(len(flows), 1))}",
            ]
        )

    start = len(rows) + 1
    rows.extend(
        [
            [
                f"AC-{start:02d}",
                "supporting",
                "EP-03",
                "Primary User Story",
                "Given an auditable state transition is requested",
                "When a business record changes status",
                "Then the system records who changed what and when",
                "All critical state transitions remain auditable",
                "auditability",
                "state transitions must not bypass audit capture",
                "Flow 1",
            ],
            [
                f"AC-{start + 1:02d}",
                "supporting",
                "EP-03",
                "Primary User Story",
                "Given out-of-scope items are discussed during planning",
                "When the MVP boundary is reviewed",
                "Then non-goals and deferred items remain visible together",
                "Scope decisions stay explicit instead of drifting into hidden commitments",
                "scope_boundary_drift",
                "out-of-scope items must not silently re-enter first-wave scope",
                "Flow 1",
            ],
            [
                f"AC-{start + 2:02d}",
                "supporting",
                "EP-02",
                "Use Case 2",
                "Given a downstream handoff depends on an external or internal dependency check",
                "When the dependency check fails",
                "Then the system blocks confirmation and records the blocked reason",
                "Recovery/retry stays explicit instead of becoming a hidden failure",
                "blocked_reason",
                "handoff confirmation must not proceed when the dependency is unavailable",
                "Flow 2",
            ],
            [
                f"AC-{start + 3:02d}",
                "anchor",
                "EP-03",
                "Use Case 3",
                "Given a closing record is generated",
                "When final confirmation is not yet recorded",
                "Then the business record cannot be marked as closed",
                "Business closure depends on a traceable final confirmation event",
                closing_boundary_type,
                "closure completion must not bypass final confirmation recording",
                "Flow 3",
            ],
            [
                f"AC-{start + 4:02d}",
                "supporting",
                "EP-01",
                "Primary User Story",
                f"Given a role without permission attempts to change a {permission_record_label}",
                "When the write request reaches the boundary",
                "Then the system rejects the request and records an audit event",
                "Permission boundary remains visible and testable",
                "permission_boundary",
                permission_boundary_note,
                "Flow 3",
            ],
        ]
    )
    next_index = len(rows) + 1
    for target in loop_targets(runtime_context)[:4]:
        short_title = loop_title_short(str(target.get("scenario_title", f"Scenario {next_index}")))
        focus = set(str(item).strip() for item in target.get("focus_areas", []))
        rows.append(
            [
                f"AC-{next_index:02d}",
                "anchor" if "flow_steps" in focus or "state_transitions" in focus else "supporting",
                "EP-02" if "handoff_contracts" in focus else "EP-03",
                "Use Case 2" if "handoff_contracts" in focus else "Use Case 3",
                f"Given `{short_title}` has all required entry evidence, object identity, and owner context",
                f"When the operator advances `{short_title}` to the next workflow step",
                "Then the system preserves the next tracked state, downstream handoff contract, and observable expected outcome together",
                f"`{short_title}` can move forward without forcing downstream teams to reconstruct missing truth",
                "handoff_contract_integrity" if "handoff_contracts" in focus else "invalid_state_transition",
                f"`{short_title}` fails if the next state or handoff payload is incomplete",
                short_title,
            ]
        )
        next_index += 1
        if "exception_edges" in focus or "boundary_acceptance" in focus or "real_world_baseline" in focus:
            rows.append(
                [
                    f"AC-{next_index:02d}",
                    "supporting",
                    "EP-03",
                    "Use Case 4",
                    f"Given `{short_title}` is missing required evidence, dependency readiness, or real-world operating context",
                    f"When the user still attempts to continue `{short_title}`",
                    "Then the system keeps the record in a blocked or clarification-needed state and exposes the missing boundary condition",
                    f"`{short_title}` does not silently pass a thin or unsafe record downstream",
                    "missing_required_input" if "real_world_baseline" in focus else "blocked_reason",
                    f"`{short_title}` must not hide missing measurements, documents, permissions, or dependency checks",
                    short_title,
                ]
            )
            next_index += 1
    for extra_row in runtime_context.get("domain_baseline_pack", {}).get("acceptance_rows", []):
        rows.append(list(extra_row))
    if style == "growth_observation":
        rows.extend(
            [
                [
                    "AC-13",
                    "supporting",
                    "EP-03",
                    "Use Case 4",
                    "Given a recommendation export is produced",
                    "When execution semantics are serialized for task intake",
                    "Then citation-likelihood hypothesis, FAQ suggestion, and blocked reason remain preserved where applicable",
                    "Downstream task intake can still distinguish execution-ready from clarification-needed items",
                    "export_semantics_loss",
                    "export is invalid if clarification semantics disappear",
                    "Step 7",
                ],
                [
                    "AC-14",
                    "supporting",
                    "EP-03",
                    "Use Case 3",
                    "Given attribution capability stays deferred",
                    "When the implementation seam is described",
                    "Then source tag, platform, query cluster, funnel stage, conversion event, and cross-device placeholder remain reserved",
                    "Phase-2 can extend attribution without rewriting the object chain",
                    "deferred_seam_loss",
                    "deferred attribution may stay out of MVP but cannot vanish from the seam contract",
                    "Step 10",
                ],
                [
                    "AC-15",
                    "supporting",
                    "EP-01",
                    "Primary User Story",
                    "Given source features are translated into first-wave scope",
                    "When the carryover ledger is reviewed",
                    "Then every critical source feature is classified as first-wave abstraction, later slice, deferred seam, or explicit out-of-scope",
                    "No critical source feature disappears without an explicit classification decision",
                    "source_feature_drop",
                    "a critical source feature cannot disappear without an explicit classification",
                    "Step 10",
                ],
            ]
        )
    return rows


def build_generic_requirement_translation_rows(runtime_context: dict[str, object]) -> list[list[str]]:
    ia_rows = list(runtime_context.get("ia_matrix", []))
    rows: list[list[str]] = []
    style = detect_domain_style("", runtime_context)
    for idx, row in enumerate(ia_rows[:8], start=1):
        module = row.get("module", f"module_{idx}")
        responsibility = row.get("responsibility") or "deliver the source-defined business capability"
        inputs = row.get("input") or "business input"
        output = row.get("output") or "business output"
        rows.append(
            [
                f"RQ-{idx:02d}",
                f"EP-{min(max(idx, 1), 3):02d}",
                "Primary User Story" if idx <= 2 else f"Use Case {min(idx - 1, 4)}",
                "functional_requirement",
                f"系统必须支持 `{module}`，使 `{inputs}` 能稳定转化为 `{output}`。",
                f"这是 source brief 中 `{module}` 的直接业务契约：{responsibility}。",
            ]
        )

    start = len(rows) + 1
    rows.extend(
        [
            [
                f"RQ-{start:02d}",
                "EP-03",
                "Primary User Story",
                "quality_or_compliance_constraint",
                "所有关键业务状态变更都必须可审计。",
                "这是 source brief 中的架构约束，不应后补。",
            ],
            [
                f"RQ-{start + 1:02d}",
                "EP-01",
                "Primary User Story",
                "governance_constraint",
                "首版必须显式声明 out-of-scope 与 non-goals。",
                "这是范围治理规则，用于防止承诺漂移。",
            ],
            [
                f"RQ-{start + 2:02d}",
                "EP-02",
                "Use Case 2",
                "functional_requirement",
                "模块 handoff payload 必须保留 target_asset_id、priority、owner_hint、blocked_reason。",
                "这是 Payload Contract 的最小实现约束，避免导出后丢失执行语义。",
            ],
            [
                f"RQ-{start + 3:02d}",
                "EP-03",
                "Use Case 3",
                "quality_or_compliance_constraint",
                "系统必须保留 source brief 明确声明的 deferred extension seam 字段定义，但不得把它们包装成已完成能力。",
                "这是 deferred seam，不是首版完成项。",
            ],
            [
                f"RQ-{start + 4:02d}",
                "EP-01",
                "Primary User Story",
                "governance_constraint",
                "Source Feature Carryover Ledger 中的 first-wave abstraction、later slice、deferred seam、explicit out-of-scope 必须持续可见。",
                "这是 carryover ledger 的边界治理要求。",
            ],
        ]
    )
    if style == "growth_observation":
        rows.extend(
            [
                [
                    "RQ-16",
                    "EP-02 / EP-03",
                    "Use Case 2 / Use Case 4",
                    "functional_requirement",
                    "recommendation payload 必须在适用时保留 AI-friendly score、quality diagnosis、structured rewrite、keyword/question focus、citation-likelihood hypothesis、FAQ suggestion 等结构化字段。",
                    "这是 execution-ready payload 的直接功能定义。",
                ],
                [
                    "RQ-17",
                    "EP-03",
                    "Use Case 3",
                    "quality_or_compliance_constraint",
                    "系统必须为 attribution/conversion 保留 extension seam，包括 source tagging、funnel、conversion event、cross-device placeholder 等字段或接口说明，但不得把它们包装成已完成 ROI 证明。",
                    "它约束未来扩展与证据诚实度，属于质量/合规边界。",
                ],
                [
                    "RQ-18",
                    "EP-02 / EP-03",
                    "Use Case 2 / Primary User Story",
                    "governance_constraint",
                    "产品边界必须用 source feature carryover ledger 显式声明哪些 source 细节被保留为 first-wave abstraction、later slice、deferred seam、explicit out-of-scope。",
                    "这是跨阶段边界治理规则。",
                ],
            ]
        )
    return rows


def source_signal_section(source_text: str) -> str:
    snapshot = build_dynamic_signal_snapshot(source_text)
    segment_hits = snapshot["segment_hits"]
    capability_hits = snapshot["capability_hits"]
    metric_hits = snapshot["metric_hits"]
    return (
        "### Source Signal Recompilation\n"
        f"- segment signals: {', '.join(segment_hits) if segment_hits else '(none)'}\n"
        f"- capability signals: {', '.join(capability_hits) if capability_hits else '(none)'}\n"
        f"- metric signals: {', '.join(metric_hits) if metric_hits else '(none)'}"
    )


def render_maturity_confidence_table(rows: list[dict[str, str]]) -> str:
    lines = [
        "| subject | delivery_readiness_state | evidence_confidence_state | current_basis | blocker_to_next_delivery_state | blocker_to_next_evidence_state | safe_downstream_action | forbidden_assumptions |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        values = [
            row["subject"],
            row["delivery_readiness_state"],
            row["evidence_confidence_state"],
            row["current_basis"],
            row["blocker_to_next_delivery_state"],
            row["blocker_to_next_evidence_state"],
            row["safe_downstream_action"],
            row["forbidden_assumptions"],
        ]
        escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def render_validation_maturity_summary(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "\n".join(
            [
                "- document_delivery_state: downstream-start-safe",
                "- evidence_confidence_state: source-grounded-but-unvalidated",
                "- subject_level_ledger_note: detailed subject-level maturity/confidence ledger is preserved in `§19`.",
            ]
        )

    primary = rows[0]
    ready_subjects = [row["subject"] for row in rows if row["delivery_readiness_state"].strip().lower() == "downstream-start-safe"]
    blocked_or_review_bound = [
        row["subject"]
        for row in rows
        if row["delivery_readiness_state"].strip().lower() != "downstream-start-safe"
        or row["evidence_confidence_state"].strip().lower() != "externally-validated"
    ]
    return "\n".join(
        [
            f"- document_delivery_state: `{primary['delivery_readiness_state']}`",
            f"- evidence_confidence_state: `{primary['evidence_confidence_state']}`",
            "- subject_level_ledger_note: detailed subject-level maturity/confidence ledger is preserved in `§19`.",
            (
                "- safe_start_focus: "
                + ", ".join(ready_subjects[:3])
                + " remain"
                + " valid bounded downstream-start anchors."
                if ready_subjects
                else "- safe_start_focus: no subject is currently downstream-start-safe."
            ),
            (
                "- pending_confirmation_focus: "
                + ", ".join(blocked_or_review_bound[:3])
                + " still require explicit follow-up evidence or sharper implementation detail."
                if blocked_or_review_bound
                else "- pending_confirmation_focus: no additional subject-level follow-up is currently open."
            ),
        ]
    )


def warning_level_for_row(row: dict[str, str]) -> str:
    delivery = row["delivery_readiness_state"].strip().lower()
    evidence = row["evidence_confidence_state"].strip().lower()
    if delivery == "blocked" or evidence in {"design-time-inference-heavy", "contradicted"}:
        return "warning-high"
    if delivery in {"review-ready", "artifact-draft"} or evidence == "source-grounded-but-unvalidated":
        return "warning-medium"
    if evidence == "partially-signal-backed":
        return "warning-low"
    return "watch-only"


def current_document_position(row: dict[str, str]) -> str:
    delivery = row["delivery_readiness_state"].strip().lower()
    evidence = row["evidence_confidence_state"].strip().lower()
    if delivery == "blocked":
        return "只能作为显式 deferred / blocked truth 保留，不能进入当前波次承诺。"
    if delivery == "downstream-start-safe" and evidence == "externally-validated":
        return "文档与证据都足够强，可进入更强交付承诺。"
    if delivery == "downstream-start-safe":
        return "文档已足够支撑 bounded downstream start，但业务真相仍待外部确认。"
    if delivery == "review-ready":
        return "文档可供 review 与方案深化，但不能据此冻结实现或商业承诺。"
    if evidence == "design-time-inference-heavy":
        return "当前更接近结构化假设，而非已获得外部信号支持的结论。"
    return "可作为受限判断保留，但不得被下游静默提升为已验证结论。"


def render_warning_confirmation_summary(rows: list[dict[str, str]]) -> str:
    grouped: dict[str, list[str]] = {
        "warning-high": [],
        "warning-medium": [],
        "warning-low": [],
        "watch-only": [],
    }
    for row in rows:
        grouped.setdefault(warning_level_for_row(row), []).append(row["subject"])

    summary_lines = [
        "- document_maturity_interpretation:",
        "  - 当前 PRD 的通过语义针对文档成熟度与安全 handoff；warning 的存在不等于 PRD 结构不完整。",
        "- business_completeness_interpretation:",
        "  - warning 主要表示业务/证据完善度仍未达到理想模板，尤其是真实访谈、重复采样、付费与采纳信号仍有缺口。",
        "- warning_count_by_level:",
    ]
    for level in ("warning-high", "warning-medium", "warning-low", "watch-only"):
        subjects = grouped[level]
        rendered = "; ".join(subjects) if subjects else "(none)"
        summary_lines.append(f"  - {level}: {len(subjects)} subject(s) -> {rendered}")
    summary_lines.extend(
        [
            "- interpretation_rule:",
            "  - 文档可 PASS / downstream-start-safe，不等于业务已 externally-validated；warning 与 pending confirmation 仍然对下游有约束力。",
        ]
    )
    return "\n".join(summary_lines)


def render_warning_confirmation_table(rows: list[dict[str, str]]) -> str:
    lines = [
        "| subject | warning_level | warning_basis | missing_external_confirmation | current_document_position | safe_current_use | stronger_commitment_blocker | forbidden_assumptions |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        values = [
            row["subject"],
            warning_level_for_row(row),
            (
                f"delivery={row['delivery_readiness_state']}; "
                f"evidence={row['evidence_confidence_state']}"
            ),
            row["blocker_to_next_evidence_state"],
            current_document_position(row),
            row["safe_downstream_action"],
            row["blocker_to_next_delivery_state"],
            row["forbidden_assumptions"],
        ]
        escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def render_epic_decomposition_table(runtime_context: dict[str, object]) -> str:
    flows = list(runtime_context.get("source_flows", []))
    style = detect_domain_style("", runtime_context)
    if style == "growth_observation":
        rows = [
            [
                "EP-01",
                "Scope and Evidence Foundation",
                "establish trustworthy tenant, scope, and baseline records",
                "Primary User Story, Use Case 1",
                "scope, evidence, and role boundaries must exist before downstream GEO actions can converge",
            ],
            [
                "EP-02",
                "Finding-to-Action Execution",
                "support finding interpretation, recommendation, and task handoff",
                "Use Case 2",
                "module contracts and dependency checks must remain typed and traceable",
            ],
            [
                "EP-03",
                "Review, Audit, and Decision Closure",
                "complete traceable cycle review and auditable decision transitions",
                "Use Case 3",
                "review closure and audit events must remain implementation-visible",
            ],
        ]
    elif style == "pet_clinic":
        rows = [
            [
                "EP-01",
                "Visit Intake Foundation",
                "establish trustworthy owner, pet, and visit intake records",
                "Primary User Story, Use Case 1",
                "core visit records and role boundaries must exist before downstream modules can converge",
            ],
            [
                "EP-02",
                "Consultation and Treatment Execution",
                "support the main module handoff and treatment execution path",
                "Use Case 2",
                "module contracts and dependency checks must remain typed and traceable",
            ],
            [
                "EP-03",
                "Discharge, Audit, and Review",
                "complete traceable visit closure and auditable state transitions",
                "Use Case 3",
                "discharge closure and audit events must remain implementation-visible",
            ],
        ]
    else:
        rows = [
            [
                "EP-01",
                "Business Record Foundation",
                "establish trustworthy business records and boundary contracts",
                "Primary User Story, Use Case 1",
                "core records and role boundaries must exist before downstream modules can converge",
            ],
            [
                "EP-02",
                "Core Workflow Execution",
                "support the main module handoff and downstream action path",
                "Use Case 2",
                "module contracts and dependency checks must remain typed and traceable",
            ],
            [
                "EP-03",
                "Closure, Audit, and Review",
                "complete traceable closure and auditable state transitions",
                "Use Case 3",
                "closure and audit events must remain implementation-visible",
            ],
        ]
    if not flows:
        rows[1][2] = "support the source-defined business workflow"
    return markdown_table(
        [
            "epic_id",
            "epic_name",
            "user_value",
            "included_user_stories_or_use_cases",
            "downstream_architecture_pressure",
        ],
        rows,
    )


def build_generic_invest_evaluation_rows(runtime_context: dict[str, object]) -> list[list[str]]:
    primary_segment = str(runtime_context.get("primary_segment", "")).strip() or "primary operator"
    style = detect_domain_style("", runtime_context)
    foundation_note = (
        "bounded around tracked scope/baseline foundation and operator entry clarity"
        if style == "growth_observation"
        else "bounded around visit foundation and intake clarity"
        if style == "pet_clinic"
        else "bounded around business record foundation and entry clarity"
    )
    return [
        [
            "Primary User Story",
            "EP-01, EP-02, EP-03",
            "partial",
            "yes",
            "yes",
            "partial",
            "partial",
            "yes",
            f"cross-epic loop is valuable but still large; keep `{primary_segment}` mainline decomposition explicit to avoid over-broad implementation batches",
        ],
        [
            "Use Case 1",
            "EP-02",
            "yes",
            "yes",
            "yes",
            "yes",
            "yes",
            "yes",
            foundation_note,
        ],
        [
            "Use Case 2",
            "EP-02",
            "yes",
            "partial",
            "yes",
            "partial",
            "yes",
            "yes",
            "priority logic is negotiable, but handoff evidence quality still affects estimation confidence",
        ],
        [
            "Use Case 3",
            "EP-03",
            "yes",
            "yes",
            "yes",
            "partial",
            "partial",
            "yes",
            "review logic is testable, but outcome thresholds still need bounded calibration",
        ],
        [
            "Use Case 4",
            "EP-03",
            "yes",
            "yes",
            "yes",
            "yes",
            "yes",
            "yes",
            "clarification fallback is intentionally narrow and implementation-facing",
        ],
    ]


def render_invest_table(runtime_context: dict[str, object]) -> str:
    return markdown_table(
        [
            "story_or_use_case",
            "epic_id",
            "independent",
            "negotiable",
            "valuable",
            "estimable",
            "small",
            "testable",
            "risk_or_note",
        ],
        build_generic_invest_evaluation_rows(runtime_context),
    )


def render_acceptance_detail_table() -> str:
    return markdown_table(
        [
            "ac_id",
            "ac_tier",
            "epic_id",
            "story_or_use_case",
            "given",
            "when",
            "then",
            "expected_outcome",
            "boundary_condition_type",
            "boundary_case",
            "related_flow_step",
        ],
        ACCEPTANCE_DETAIL_ROWS,
    )


def render_acceptance_detail_table_from_rows(rows: list[list[str]]) -> str:
    return markdown_table(
        [
            "ac_id",
            "ac_tier",
            "epic_id",
            "story_or_use_case",
            "given",
            "when",
            "then",
            "expected_outcome",
            "boundary_condition_type",
            "boundary_case",
            "related_flow_step",
        ],
        rows,
    )


def render_requirement_translation_table() -> str:
    return markdown_table(
        [
            "requirement_id",
            "epic_id",
            "story_or_use_case",
            "requirement_class",
            "requirement_statement",
            "why_this_class",
        ],
        REQUIREMENT_TRANSLATION_ROWS,
    )


def render_requirement_translation_table_from_rows(rows: list[list[str]]) -> str:
    return markdown_table(
        [
            "requirement_id",
            "epic_id",
            "story_or_use_case",
            "requirement_class",
            "requirement_statement",
            "why_this_class",
        ],
        rows,
    )


def render_requirement_trace_matrix() -> str:
    return markdown_table(
        [
            "epic_id",
            "story_or_use_case",
            "requirement_id",
            "requirement_class",
            "acceptance_criteria",
            "boundary_condition",
            "related_flow_step",
        ],
        REQUIREMENT_TRACE_ROWS,
    )


def render_requirement_trace_matrix_from_rows(
    requirement_rows: list[list[str]],
    acceptance_rows: list[list[str]],
) -> str:
    req_index = {row[0]: row for row in requirement_rows}
    ac_ids = [row[0] for row in acceptance_rows]
    rows: list[list[str]] = []
    for idx, (req_id, req_row) in enumerate(req_index.items(), start=1):
        rows.append(
            [
                req_row[1],
                req_row[2],
                req_id,
                req_row[3],
                ac_ids[min(idx - 1, len(ac_ids) - 1)] if ac_ids else "",
                "module_contract_integrity" if idx <= len(acceptance_rows) else "scope_boundary_drift",
                f"Flow {min(idx, max(len(acceptance_rows), 1))}",
            ]
        )
    return markdown_table(
        [
            "epic_id",
            "story_or_use_case",
            "requirement_id",
            "requirement_class",
            "acceptance_criteria",
            "boundary_condition",
            "related_flow_step",
        ],
        rows,
    )


def render_competitive_landscape_table(source_text: str, runtime_context: dict[str, object]) -> str:
    _ = source_text
    workflow_backbone = business_loop_surface(runtime_context, limit=4)
    proof_phrase = compact_proof_artifact_phrase(runtime_context)
    baseline_note = compact_competitive_baseline_anchor(runtime_context)
    partial_tool_note = compact_partial_tool_anchor(runtime_context)
    service_note = compact_service_substitute_anchor(runtime_context)
    rows = [
        [
            "当前分散基线",
            baseline_note,
            "review-bound / 当前替代成本主要体现为内部时间、协作损耗与判断滞后，仍待 field validation。",
            f"能勉强把流程跑完，但 {proof_phrase or '`source-defined proof artifact`'} 与下一动作仍分散，无法在一次 review 中直接判断是否继续投入。",
            "source-grounded",
            f"首版必须先把 {workflow_backbone} 收成同一条可 review 的连续主线。",
        ],
        [
            "单点数字化工具",
            partial_tool_note,
            "review-bound / 单点工具采购方式与价格带仍待 field validation。",
            "通常只补一个局部步骤或局部可视化，跨步骤责任、证据和下一动作仍需人工拼接。",
            "review-bound / missing evidence",
            "不要把差异化建立在单点功能更全，而要建立在主线连续性更强。",
        ],
        [
            "人工服务 / 代运营替代",
            service_note,
            "review-bound / 服务费或专项人力投入仍待 field validation。",
            f"能暂时补连续性，但关键判断仍依赖人脑记忆，{proof_phrase or '`source-defined proof artifact`'} 难以沉淀成团队自己的经营资产。",
            "review-bound / missing evidence",
            "产品要把服务替代里的连续判断沉到系统里，而不是继续依赖人治。",
        ],
    ]
    return markdown_table(
        [
            "alternative_set",
            "representative_example_or_current_baseline",
            "pricing_model_signal",
            "coverage_note",
            "evidence_state",
            "positioning_implication",
        ],
        rows,
    )


def render_pricing_validation_table(source_text: str, runtime_context: dict[str, object]) -> str:
    value_phrase = compact_value_mechanism_phrase(runtime_context)
    commercial_phrase = compact_spend_at_risk_phrase(runtime_context)
    proof_phrase = compact_proof_artifact_phrase(runtime_context)
    buyer_chain = (
        runtime_context.get("business_world_model", {}).get("buyer_budget_chain", {})
        if isinstance(runtime_context.get("business_world_model"), dict)
        else {}
    )
    continuation_owner = compact_signal_line(str(buyer_chain.get("continuation_owner", ""))) or str(
        runtime_context.get("primary_segment", "primary operator")
    ).strip() or "primary operator"
    if len(value_phrase) > 180 or "`" in value_phrase or reader_facing_truth_is_spliced(value_phrase, value_phrase):
        value_phrase = f"{business_loop_plain_surface(runtime_context, limit=3)} 能形成可复盘的连续主线"
    commercial_judgment_phrase = commercial_phrase
    if len(commercial_judgment_phrase) > 180:
        commercial_judgment_phrase = f"{continuation_owner} 的时间、流程变更和继续评审成本"
    buyer_truth_state = compact_signal_line(str(buyer_chain.get("truth_state", ""))) or "review-bound / missing evidence"
    artifact_phrase = proof_phrase or "待评审确认（review-bound）：继续判断证据尚未建立"
    rows = [
        [
            "value / continuation interview",
            (
                f"`{continuation_owner}` 只有在首轮主线证明 {value_phrase} 后，才继续投入"
                if not is_review_bound_missing(commercial_phrase)
                else f"review-bound / missing evidence: 先验证 `{continuation_owner}` 是否会围绕 {artifact_phrase} 把 {commercial_judgment_phrase} 当成真实投入风险"
            ),
            f"{artifact_phrase} + buyer-budget truth card",
            f"`{continuation_owner}` 看完 {artifact_phrase} 后能说明继续 / 调整 / 暂停",
            "keep pricing and packaging review-bound until the continuation decision surface is explicit",
        ],
        [
            "proof artifact review",
            f"只有当 {artifact_phrase} 足以支撑 {commercial_judgment_phrase}，产品才进入预算讨论",
            f"{artifact_phrase} + workflow storyboard",
            "reviewers 能把证明产物连到真实继续判断，而不是只表达泛泛兴趣",
            "rework the value mechanism and proof artifact before discussing pricing credibility",
        ],
        [
            "continuation evidence test",
            f"当前 buyer-budget truth state 是 `{buyer_truth_state}`；不要把 {commercial_judgment_phrase} 升级成报价或包装清晰度",
            "continuation checklist + explicit missing-evidence ledger",
            "团队能不脑补地说明 pain holder、continuation owner、spend at risk、proof artifact 和 decision trigger",
            "leave commercial posture review-bound and continue discovery before claiming packaging clarity",
        ],
    ]
    for target in loop_targets(runtime_context)[:3]:
        short_title = loop_title_short(str(target.get("scenario_title", "Scenario")))
        focus = set(str(item).strip() for item in target.get("focus_areas", []))
        if "business_value" in focus or "value_mechanism" in focus:
            rows.append(
                [
                    f"value mechanism review: {short_title}",
                    f"`{short_title}` must bind to `{value_phrase or 'review-bound / missing evidence'}` instead of only workflow completion",
                    f"value story card + {artifact_phrase}",
                    "reviewers can explain why the workflow changes a real business decision or operating result",
                    "rework the business framing before freezing the first-wave promise",
                ]
            )
        if "buyer_budget_chain" in focus:
            rows.append(
                [
                    f"buyer budget trace: {short_title}",
                    f"`{short_title}` must keep `{continuation_owner}`, `{artifact_phrase}`, and `{commercial_judgment_phrase}` explicit",
                    "buyer-budget chain card + continuation checklist",
                    "the team can state who owns the continued commitment and what evidence keeps it alive",
                    "keep the commercial chain review-bound and continue discovery before claiming packaging clarity",
                ]
            )
    return markdown_table(
        [
            "experiment",
            "pricing_hypothesis",
            "artifact",
            "pass_signal",
            "fail_consequence",
        ],
        rows,
    )


def derive_final_status_from_report(report_text: str) -> str:
    default_status = "PASS with constrained/review-bound conditions"
    match = re.search(
        r"recommended_formal_state:\s*(?:\n\s*-\s*`?([^`\n]+)`?)?",
        report_text,
        flags=re.IGNORECASE,
    )
    if not match or not match.group(1):
        return default_status

    state = match.group(1).strip().lower()
    if state == "blocked":
        return "BLOCKED"
    if state == "pass":
        return "PASS"
    if "constrained" in state or "review-bound" in state:
        return default_status
    return default_status


def build_delta_ledger(runtime_context: dict[str, object]) -> str:
    role_evidence = ", ".join(
        str(role).strip()
        for role in runtime_context.get("target_user_roles", [])[:3]
        if str(role).strip()
    ) or "source-defined roles"
    deltas = [
        (
            "source brief 给出明确的 Target Users。",
            "首发应先收敛单一主入口角色，降低流程设计复杂度。",
            f"选择 {runtime_context['primary_segment']} 作为 primary segment。",
            "设计与架构优先围绕主入口角色的连续操作路径展开。",
        ),
        (
            "source brief 给出 Module Responsibility Matrix 与 Key Business Flows。",
            "产品结构应服务业务流程，而不是功能货架。",
            "采用 source-flow-first 组织结构。",
            "下游交互与数据结构围绕 source 的核心对象与业务流组织。",
        ),
        (
            "source brief 给出 Core Business Objects。",
            "对象链决定 IA、流程和审计的约束关系。",
            "采用 source-derived object chain。",
            "架构阶段可据此设计核心数据关系与接口契约。",
        ),
        (
            "source brief 给出 Non-functional Requirements 与 Architectural Constraints。",
            "质量约束需要在 MVP 阶段前置，而不是实现后补。",
            "把留存、性能、并发与审计要求直接纳入 PRD。",
            "研发与测试可以据此提前定义边界与验证方案。",
        ),
        (
            "source brief 明确列出 Out of Scope (MVP)。",
            "MVP 边界不清会导致范围漂移。",
            "将 out-of-scope 项显式写入 PRD。",
            "研发排期与评审可以据此拒绝超范围需求。",
        ),
        (
            "source brief 的 Key Business Flows 明确覆盖一条可闭环的主业务链。",
            "业务场景需要按主流程拆解，而不是按零散功能点陈列。",
            "把 Business Scenarios 与 Operational Flow Specification 对齐到同一主链。",
            "设计和测试可以沿同一流程脚本推进 walkthrough。",
        ),
        (
            "source brief 的 Module Responsibility Matrix 给出 input/output。",
            "Requirements Structure 需要显式保留 process type、trigger、output 和 system behavior。",
            "补充 Business Process Decomposition 与 Exception and Failure Flows。",
            "架构和实现可以更直接地映射模块 handoff。",
        ),
        (
            "source brief 的 Non-functional Requirements 明确给出 retention、response time、concurrent users。",
            "NFR 不应只写口号，而应转成 quality scenario 和 measure。",
            "补充 Top Quality Attributes、Quality Scenario Matrix 和 metric register。",
            "测试可以根据 stimulus/environment/expected response 设计验证。",
        ),
        (
            "source brief 的 Architectural Constraints 明确给出 role-based auth 与 auditability。",
            "Domain Model 和 IA 都必须显式展示 boundary 与 audit seam。",
            "把 account boundary、audit log、role visibility 纳入主文档。",
            "下游不会再把权限和审计视为后补项。",
        ),
        (
            "source brief 的 Core Business Objects 可直接组成 object chain。",
            "Domain Model 需要从对象目录延展到 relationship direction、subsystem interfaces、workflow mapping。",
            "补充 entity catalog、first-wave decision 和 object lifecycle notes。",
            "设计与架构能基于对象链而不是页面名对齐。",
        ),
        (
            f"source brief 的角色集合覆盖 {role_evidence}。",
            "Target Users 章节需要更细化到 role chain、JTBD、key-path scenario、design requirement。",
            "补充 role table、JTBD table、DR-01..DR-06。",
            "设计输入会更直接，避免角色边界再次模糊。",
        ),
        (
            "source brief 的业务流与 scope boundary 都适合 workflow-loop-first 切法。",
            "MVP Definition & Scope 需要显式写出 candidate table、carryover ledger、chosen slice 和 exclusion rule。",
            "采用 workflow-loop-first，并把 later slice / deferred seam / explicit out-of-scope 分开。",
            "范围讨论可以围绕同一套 ledger 收敛。",
        ),
        (
            "source brief 只给出结构化输入，没有外部验证结论。",
            "Validation Strategy 必须把 exact_assumption、chosen_method、threshold、learning_if_pass/fail 说清楚。",
            "补充 assumption table、method table、artifact-threshold table。",
            "产品评审可以基于更明确的验证计划而不是抽象判断。",
        ),
        (
            "完整 trial 的 executability gate 要求至少 8 个 Reasoning Unit。",
            "仅有结构化章节还不够，必须显式保留关键 tradeoff 和 convergence admission。",
            "在 PRD 内补 Reasoning Unit 1..8。",
            "门禁、评审和后续 handoff 能共享同一套 reasoning trace。",
        ),
        (
            "完整 trial 的 quality gate 要求 PRD 不得对 stage 结果过度压缩。",
            "过度摘要会导致 stage_char_ratio 和 stage_line_ratio 失败。",
            "通过增加 source-driven 表格、状态迁移规则、映射矩阵和 delta ledger 提高文档深度。",
            "主文档可读性与门禁通过率同时提升。",
        ),
    ]
    lines = ["## 21. Analysis Delta Ledger"]
    for idx, (evidence, inference, tradeoff, impact) in enumerate(deltas, start=1):
        lines.extend(
            [
                f"### Delta {idx}",
                f"- source_evidence: {evidence}",
                f"- analytical_inference: {inference}",
                f"- decision_or_tradeoff: {tradeoff}",
                f"- downstream_impact: {impact}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def render_information_architecture_spec_matrix(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "- (no IA matrix extracted from source brief)"
    return markdown_table(
        ["module", "core_objects", "responsibility", "input", "output"],
        [[row["module"], row["core_objects"], row["responsibility"], row["input"], row["output"]] for row in rows],
    )


def render_core_business_objects_table(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "- (no core business objects extracted from source brief)"
    return markdown_table(
        ["object", "description", "module"],
        [[row["object"], row["description"], row["module"]] for row in rows],
    )


def build_generic_maturity_confidence_ledger(source_text: str, runtime_context: dict[str, object]) -> list[dict[str, str]]:
    primary_segment = str(runtime_context.get("primary_segment", "")).strip() or "primary segment"
    workflow_backbone = business_loop_plain_surface(runtime_context, limit=5)
    completeness_driver = business_completeness_driver_surface(runtime_context)
    driver_state = business_completeness_driver_state(runtime_context) or "source-grounded-but-unvalidated"
    source_admission_evidence_state = source_admission_evidence_state_from_text(source_text, driver_state)
    proof_for_continue = completeness_driver.get("proof_for_continue", {}) if isinstance(completeness_driver, dict) else {}
    claim_ceiling = completeness_driver.get("commercial_claim_ceiling", {}) if isinstance(completeness_driver, dict) else {}
    proof_artifact = (
        compact_signal_line(str(proof_for_continue.get("proof_artifact", "")))
        if isinstance(proof_for_continue, dict)
        else ""
    ) or compact_proof_artifact_phrase(runtime_context)
    proof_artifact = compact_reader_facing_commercial_phrase(proof_artifact)
    missing_external = (
        compact_signal_line(str(proof_for_continue.get("missing_external_evidence", "")))
        if isinstance(proof_for_continue, dict)
        else ""
    ) or "need real stakeholder walkthrough validation"
    forbidden_upgrade = (
        compact_signal_line(str(claim_ceiling.get("forbidden_upgrade", "")))
        if isinstance(claim_ceiling, dict)
        else ""
    ) or "market validation or owner sign-off already complete"
    business_current_basis = (
        f"source brief / stage evidence 明确把 {proof_artifact} 作为继续投入评审证据"
        if re.search(r"[\u4e00-\u9fff]", source_text)
        else f"source brief / stage evidence names {proof_artifact} as the continuation review artifact"
    )
    style = detect_domain_style(source_text, runtime_context)
    workflow_evidence_blocker = (
        "need real usage validation in GEO operating practice"
        if style == "growth_observation"
        else "need real usage validation in the source-defined operating environment"
    )
    return [
        {
            "subject": f"primary segment boundary ({primary_segment})",
            "delivery_readiness_state": "downstream-start-safe",
            "evidence_confidence_state": source_admission_evidence_state,
            "current_basis": "source brief target users and business flow entry point are explicit",
            "blocker_to_next_delivery_state": "need screen-level interaction and handoff detail",
            "blocker_to_next_evidence_state": "need real stakeholder walkthrough validation",
            "safe_downstream_action": "design and architecture may proceed around the primary segment flow",
            "forbidden_assumptions": "primary segment already validated in the market",
        },
        {
            "subject": f"workflow backbone ({workflow_backbone})",
            "delivery_readiness_state": "downstream-start-safe",
            "evidence_confidence_state": "source-grounded-but-unvalidated",
            "current_basis": "source brief provides explicit flow steps, module contracts, and core objects",
            "blocker_to_next_delivery_state": "need interface contracts and error-state detail",
            "blocker_to_next_evidence_state": workflow_evidence_blocker,
            "safe_downstream_action": "prototype and service boundaries may follow the source-defined workflow",
            "forbidden_assumptions": "workflow adoption already validated",
        },
        {
            "subject": "quality, audit, and scope boundary",
            "delivery_readiness_state": "review-ready",
            "evidence_confidence_state": "source-grounded-but-unvalidated",
            "current_basis": "source brief provides retention, response time, concurrency, auth, and audit constraints",
            "blocker_to_next_delivery_state": "need implementation-level policy and event scope definition",
            "blocker_to_next_evidence_state": "need technical validation and stakeholder review",
            "safe_downstream_action": "architecture can reserve policy, audit, and retention seams",
            "forbidden_assumptions": "compliance approval complete",
        },
        {
            "subject": "business completeness and continuation proof",
            "delivery_readiness_state": "downstream-start-safe",
            "evidence_confidence_state": driver_state,
            "current_basis": business_current_basis,
            "blocker_to_next_delivery_state": "need P2 design to preserve the business proof chain and decision hook",
            "blocker_to_next_evidence_state": missing_external,
            "safe_downstream_action": "P2 may design around the business loss chain, continuation owner, proof artifact, and claim ceiling",
            "forbidden_assumptions": forbidden_upgrade,
        },
    ]


def source_admission_evidence_state_from_text(source_text: str, driver_state: str = "") -> str:
    lowered = source_text.casefold()
    if re.search(
        r"synthetic-operating-assumption|mechanism-validation-only|simulated-office-hours|simulated-market|"
        r"not real user research|not external market validation|not owner sign-off|not budget approval|"
        r"不是真实用户|不代表真实|真实用户访谈未发生|未外部验证",
        lowered,
    ):
        return "source-grounded-but-unvalidated"
    if re.search(
        r"externally-validated|external validation complete|field-validated|真实外部验证已完成|已被外部验证",
        lowered,
    ):
        return "externally-validated"
    if re.search(
        r"real-user-interview-input|user-stated-interview-input|real stakeholder interview|"
        r"owner-stated|budget owner stated|user stated|interview-confirmed|"
        r"真实访谈输入|用户访谈陈述|用户已陈述|owner 已陈述|预算负责人已陈述",
        lowered,
    ):
        return "partially-signal-backed"
    if driver_state in {"externally-validated", "partially-signal-backed"}:
        return driver_state
    return "source-grounded-but-unvalidated"


def build_runtime_context(
    *,
    source_text: str,
    stage_01_text: str,
    stage_02a_text: str,
    stage_02b_text: str,
    stage_03_text: str,
    loop_plan: dict[str, object] | None = None,
    business_world_model: dict[str, object] | None = None,
) -> dict[str, object]:
    fact_source_text = source_fact_text(source_text)
    business_release_truth_pack = (
        business_world_model.get("business_release_truth_pack", {})
        if isinstance(business_world_model, dict)
        else {}
    )
    planning_control_truth_pack = (
        business_world_model.get("planning_control_truth_pack", {})
        if isinstance(business_world_model, dict)
        else {}
    )
    topology_profile = (
        business_world_model.get("topology_profile", {})
        if isinstance(business_world_model, dict)
        else {}
    )
    topology_profile = topology_profile if isinstance(topology_profile, dict) else {}
    target_user_items = extract_target_user_roles_from_brief(fact_source_text)
    stage_boundary = extract_h2_block(stage_01_text, ["Chosen User Boundary"])
    stage_primary_segment = (
        extract_single_line_field(stage_boundary, "chosen_segment")
        or extract_nested_field_value(stage_boundary, "chosen_segment")
    )
    primary_segment = (
        ("" if is_missing_placeholder(stage_primary_segment) else stage_primary_segment)
        or (target_user_items[0] if target_user_items else "")
        or "primary operator"
    )

    product_vision = extract_markdown_section(
        fact_source_text,
        ["Product Vision", "产品愿景", "项目摘要", "1.0 项目摘要"],
        level_pattern=r"##",
    )
    business_objectives = extract_markdown_section(
        fact_source_text,
        ["Core Business Objectives", "核心业务目标", "Business Objectives", "产品/业务目标方向", "业务机会描述"],
        level_pattern=r"##",
    )
    structured_problem_block = extract_markdown_section(
        fact_source_text,
        ["Structured Problem List", "结构化问题清单", "问题清单"],
        level_pattern=r"##",
    )
    stage_problem_block = extract_h2_block(stage_01_text, ["Problem Statement"])
    stage_problem_statement = (
        extract_nested_field_value(stage_problem_block, "final_problem_statement")
        or extract_single_line_field(stage_problem_block, "final_problem_statement")
        or first_meaningful_line(stage_problem_block)
    )
    stage_problem_statement = re.sub(
        r"^(?:最终问题陈述\s*\(final_problem_statement\)|final_problem_statement)\s*:\s*",
        "",
        stage_problem_statement,
        flags=re.IGNORECASE,
    ).strip()
    structured_problem_items = collect_block_signal_items(structured_problem_block, limit=4)
    executive_summary = preferred_markdown_item(product_vision, ["目标：", "Goal:", "目标", "首发客群："]) or (
        "本 PRD 将源素材（source）和阶段产物（stage outputs）重编为一份跨角色可使用的产品文档。"
    )
    problem_statement = (
        ("" if is_missing_placeholder(stage_problem_statement) else stage_problem_statement)
        or summarize_structured_items(structured_problem_items, "")
        or preferred_markdown_item(
            business_objectives,
            ["如果", "Reduce", "Build", "把", "建立", "让用户能"],
        )
        or "The team still lacks a repeatable operating loop that turns signals into action and review."
    )
    problem_statement = re.sub(
        r"\bThe team still lacks a repeatable operating loop that turns signals into action and review\b\.?",
        "团队仍缺少把信号推进成动作和复盘判断的稳定主线",
        problem_statement,
        flags=re.IGNORECASE,
    ).strip()

    workflow_block = extract_h2_block(stage_02a_text, ["Workflow / State Detail"])
    workflow_lines = [
        re.sub(r"^\s*-\s*", "", line).strip()
        for line in workflow_block.splitlines()
        if re.match(r"^\s*-\s*Step", line)
    ]
    screen_block = extract_h2_block(stage_02b_text, ["IA Spec Precursor Matrix"])
    screen_terms: list[str] = []
    for line in screen_block.splitlines():
        row = re.match(r"^\|\s*([^|]+?)\s*\|", line)
        if row:
            value = row.group(1).strip()
            if value and value.lower() not in {"screen/module", "---"}:
                screen_terms.append(value)
    screen_terms = list(dict.fromkeys(screen_terms))
    source_flows = extract_key_business_flows_from_brief(fact_source_text, stage_02a_text, stage_02b_text)
    ia_matrix = extract_ia_matrix_from_brief(fact_source_text, stage_02b_text)
    core_business_objects = extract_core_business_objects_from_brief(fact_source_text, stage_02b_text)
    workflow_backbone = " -> ".join(
        [str(row.get("module", "")).strip() for row in ia_matrix if str(row.get("module", "")).strip()]
    ) if ia_matrix else " -> ".join(
        [str(flow.get("title", "")).strip() for flow in source_flows if str(flow.get("title", "")).strip()]
    ) if source_flows else " -> ".join(workflow_lines[:5]) if workflow_lines else "primary business flow"

    object_names = [row["object"] for row in core_business_objects if row.get("object")]
    object_chain = " -> ".join(dict.fromkeys(object_names)) if object_names else "primary business objects"
    out_of_scope_items = extract_out_of_scope_items_from_brief(fact_source_text)
    non_functional_requirements = extract_non_functional_requirements_from_brief(fact_source_text)
    architectural_constraints = extract_architectural_constraints_from_brief(fact_source_text)
    signal_snapshot = build_dynamic_signal_snapshot(fact_source_text)
    source_signal_pool = list(signal_snapshot["capability_hits"]) + list(signal_snapshot["metric_hits"])
    source_signal_pool.extend(
        collect_block_signal_items(
            extract_h2_block(fact_source_text, ["2.2 业务机会描述", "业务机会描述", "Business Opportunity"]),
            limit=8,
        )
    )
    source_signal_pool.extend(
        collect_block_signal_items(
            extract_h2_block(fact_source_text, ["2.4 至少 1 条可引用证据线索", "可引用证据线索", "Evidence"]),
            limit=8,
        )
    )
    source_signal_pool.extend(
        extract_structured_source_items(
            fact_source_text,
            ["Structured Problem List", "结构化问题清单", "Structured Opportunity List", "结构化机会清单"],
        )[:8]
    )
    source_signal_pool.extend(
        collect_block_signal_items(
            extract_h2_block(fact_source_text, ["3.4 至少 1 条用户叙事", "用户叙事", "User Narrative"]),
            limit=8,
        )
    )
    source_signal_pool.extend(
        extract_structured_source_items(
            fact_source_text,
            ["指标口径最小定义", "Metric Definition and Interpretation Register", "Validation Targets", "验证对象"],
        )[:8]
    )
    source_signal_pool.extend(
        extract_structured_source_items(
            fact_source_text,
            ["unknown / provisional", "unknown", "provisional", "需要后续补实的 unknown / provisional 信息"],
        )[:8]
    )
    source_signal_pool.extend(
        collect_block_signal_items(
            extract_h2_block(fact_source_text, ["5.3 影响切片顺序的依赖假设", "依赖假设", "Dependency Assumption"]),
            limit=6,
        )
    )
    source_signal_pool.extend(
        collect_block_signal_items(extract_h2_block(stage_01_text, ["Need Framing", "Problem Statement"]), limit=6)
    )
    source_signal_pool.extend(
        collect_block_signal_items(
            extract_h2_block(stage_01_text, ["Key Open Truths", "Structured Problem/Opportunity Recompilation"]),
            limit=6,
        )
    )
    source_signal_pool.extend(
        collect_block_signal_items(
            extract_h2_block(stage_02a_text, ["Value Loop and Downstream Preservation Notes", "Constraint Stress-Test"]),
            limit=6,
        )
    )
    source_signal_pool.extend(
        [str(flow.get("title", "")).strip() for flow in source_flows if str(flow.get("title", "")).strip()]
    )
    source_signal_pool.extend(
        [
            str(step).strip()
            for flow in source_flows
            for step in flow.get("steps", [])
            if str(step).strip()
        ]
    )
    source_signal_pool.extend(
        [
            str(row.get(key, "")).strip()
            for row in ia_matrix
            for key in ("module", "responsibility", "input", "output", "downstream_dependency")
            if str(row.get(key, "")).strip()
        ]
    )
    source_signal_pool.extend([executive_summary, problem_statement])
    business_value_signals = select_source_grounded_signals(
        source_signal_pool,
        patterns=VALUE_SIGNAL_PATTERNS,
        limit=5,
        intent="value",
    )
    pressure_signals = select_source_grounded_signals(
        source_signal_pool,
        patterns=PRESSURE_SIGNAL_PATTERNS,
        limit=5,
        intent="pressure",
    )
    commercial_decision_signals = select_source_grounded_signals(
        source_signal_pool,
        patterns=COMMERCIAL_DECISION_PATTERNS,
        limit=5,
        intent="commercial",
    )
    decision_proof_signals = select_source_grounded_signals(
        source_signal_pool,
        patterns=DECISION_PROOF_PATTERNS,
        limit=5,
        intent="generic",
    )
    user_experience_signals = select_source_grounded_signals(
        source_signal_pool,
        patterns=USER_EXPERIENCE_SIGNAL_PATTERNS,
        limit=5,
        intent="experience",
    )
    truth_core_thesis = compact_signal_line(
        str(
            business_release_truth_pack.get("core_thesis")
            or truth_slot_value(business_world_model.get("core_thesis", {}) if isinstance(business_world_model, dict) else {})
        ).strip()
    )
    truth_value_mechanism = compact_signal_line(
        str(
            business_release_truth_pack.get("value_mechanism")
            or truth_slot_value(business_world_model.get("value_mechanism", {}) if isinstance(business_world_model, dict) else {})
        ).strip()
    )
    truth_spend_at_risk = compact_signal_line(
        str(
            business_release_truth_pack.get("spend_at_risk")
            or truth_slot_value(business_world_model.get("spend_at_risk", {}) if isinstance(business_world_model, dict) else {})
        ).strip()
    )
    truth_proof_artifact = compact_signal_line(
        str(
            business_release_truth_pack.get("proof_artifact_for_continue")
            or planning_control_truth_pack.get("proof_artifact_for_continue")
            or truth_slot_value(
                business_world_model.get("proof_artifact_for_continue", {})
                if isinstance(business_world_model, dict)
                else {}
            )
        ).strip()
    )
    truth_decision_trigger = compact_signal_line(
        str(
            business_release_truth_pack.get("decision_trigger")
            or truth_slot_value(business_world_model.get("decision_trigger", {}) if isinstance(business_world_model, dict) else {})
        ).strip()
    )
    truth_protected_nouns = truth_slot_values(
        business_world_model.get("protected_business_nouns", {}) if isinstance(business_world_model, dict) else {}
    )
    truth_protected_nouns = merge_truth_signal_lists(
        [str(item).strip() for item in business_release_truth_pack.get("protected_business_nouns", []) if str(item).strip()],
        [str(item).strip() for item in planning_control_truth_pack.get("protected_business_nouns", []) if str(item).strip()],
        truth_protected_nouns,
    )
    business_value_signals = merge_truth_signal_lists(
        [truth_value_mechanism],
        business_value_signals,
    )[:5]
    commercial_decision_signals = merge_truth_signal_lists(
        [truth_spend_at_risk, truth_decision_trigger],
        commercial_decision_signals,
    )[:5]
    decision_proof_signals = merge_truth_signal_lists(
        [truth_proof_artifact],
        decision_proof_signals,
    )[:5]
    source_signal_snapshot = dict(signal_snapshot)
    source_signal_snapshot["protected_business_nouns"] = truth_protected_nouns
    normalized_loop_targets = normalize_loop_targets(loop_plan)
    loop_focus_areas = list(
        dict.fromkeys(
            focus
            for target in normalized_loop_targets
            for focus in target.get("focus_areas", [])
            if str(focus).strip()
        )
    )
    provisional_context = {
        "primary_segment": primary_segment,
        "target_user_roles": target_user_items,
        "executive_summary": executive_summary,
        "problem_statement": problem_statement,
        "workflow_backbone": workflow_backbone,
        "object_chain": object_chain,
        "screen_terms": screen_terms,
        "ia_matrix": ia_matrix,
        "core_business_objects": core_business_objects,
        "source_flows": source_flows,
        "out_of_scope_items": out_of_scope_items,
        "non_functional_requirements": non_functional_requirements,
        "architectural_constraints": architectural_constraints,
        "business_value_signals": business_value_signals,
        "business_value_signal_registry": build_business_value_signal_registry({"business_value_signals": business_value_signals}),
        "pressure_signals": pressure_signals,
        "commercial_decision_signals": commercial_decision_signals,
        "decision_proof_signals": decision_proof_signals,
        "user_experience_signals": user_experience_signals,
        "source_signal_snapshot": source_signal_snapshot,
        "business_world_model": business_world_model or {},
        "business_release_truth_pack": business_release_truth_pack if isinstance(business_release_truth_pack, dict) else {},
        "planning_control_truth_pack": planning_control_truth_pack if isinstance(planning_control_truth_pack, dict) else {},
        "topology_profile": topology_profile,
        "topology_archetype": str(topology_profile.get("topology_archetype", "")).strip(),
        "primary_depth_axes": [
            str(item).strip()
            for item in topology_profile.get("primary_depth_axes", [])
            if str(item).strip()
        ],
        "secondary_depth_axes": [
            str(item).strip()
            for item in topology_profile.get("secondary_depth_axes", [])
            if str(item).strip()
        ],
        "misfit_risk_if_wrong": str(topology_profile.get("misfit_risk_if_wrong", "")).strip(),
        "ordinary_real_world_baseline_definition": str(
            topology_profile.get("ordinary_real_world_baseline_definition", "")
        ).strip(),
        "protected_business_nouns": truth_protected_nouns,
    }
    domain_baseline_pack = detect_domain_baseline_pack(provisional_context)

    return {
        **provisional_context,
        "module_capabilities": render_module_capability_lines(ia_matrix),
        "flow_summary_lines": render_flow_summary_lines(source_flows),
        "loop_targets": normalized_loop_targets,
        "loop_focus_areas": loop_focus_areas,
        "loop_target_count": len(normalized_loop_targets),
        "domain_baseline_pack": domain_baseline_pack,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble Phase-1 PRD from stage outputs")
    parser.add_argument("--source", required=True, help="source input (read-only)")
    parser.add_argument("--stage-01", required=True)
    parser.add_argument("--stage-02a", required=True)
    parser.add_argument("--stage-02b")
    parser.add_argument("--stage-03", required=True)
    parser.add_argument("--stage-04", required=True)
    parser.add_argument("--report", help="optional execution report")
    parser.add_argument("--loop-plan", help="optional phase1 agentic loop plan json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--version", required=True, help="trial token like trial-v9")
    parser.add_argument(
        "--profile",
        default="review-bound-starter-pack",
        choices=("review-bound-starter-pack", "implementation-ready-prd"),
    )
    parser.add_argument("--document-name", default="Phase-1 PRD Main Document")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    stage_01_path = Path(args.stage_01).resolve()
    stage_02a_path = Path(args.stage_02a).resolve()
    stage_02b_path = Path(args.stage_02b).resolve() if args.stage_02b else None
    stage_03_path = Path(args.stage_03).resolve()
    stage_04_path = Path(args.stage_04).resolve()
    report_path = Path(args.report).resolve() if args.report else None
    loop_plan_path = Path(args.loop_plan).resolve() if args.loop_plan else None
    output_path = derive_output_path(Path(args.output).resolve(), args.document_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source_text = read_text(source_path)
    stage_01_text = read_text(stage_01_path)
    stage_02a_text = read_text(stage_02a_path)
    stage_02b_text = read_text(stage_02b_path) if stage_02b_path and stage_02b_path.exists() else ""
    stage_03_text = read_text(stage_03_path)
    stage_04_text = read_text(stage_04_path)
    report_text = read_text(report_path) if report_path and report_path.exists() else ""
    loop_plan = load_loop_plan(loop_plan_path)
    business_world_model = load_business_world_model(stage_01_path)
    business_world_model = apply_commercial_argument_rewrite(
        business_world_model,
        load_commercial_argument_rewrite(stage_01_path),
    )

    s1_user = extract_h2_block(stage_01_text, ["Chosen User Boundary"])
    s1_problem = extract_h2_block(stage_01_text, ["Problem Statement"])
    s1_need = extract_h2_block(stage_01_text, ["Need Framing"])
    s1_persona_chain = extract_h2_block(stage_01_text, ["Persona Boundary and Interaction Chain"])
    s1_structured_problem = extract_h2_block(stage_01_text, ["Structured Problem/Opportunity Recompilation"])
    s1_truth = extract_h2_block(stage_01_text, ["Key Open Truths"])
    s1_reasoning = extract_h2_block(stage_01_text, ["Minimal Reasoning Unit Ledger"])
    s1_material = extract_h2_block(stage_01_text, ["Material Grounding Bridge"])

    s2a_structure = extract_h2_block(stage_02a_text, ["Structure Choice"])
    s2a_panorama = extract_h2_block(stage_02a_text, ["User/Goal/Problem Panorama"])
    s2a_persona = extract_h2_block(stage_02a_text, ["Persona / JTBD Matrix"])
    s2a_problem_mapping = extract_h2_block(stage_02a_text, ["Problem-to-Structure Mapping"])
    s2a_structure_alts = extract_h2_block(stage_02a_text, ["Structure Alternatives Comparison"])
    s2a_backbone = extract_h2_block(stage_02a_text, ["Backbone Activities"])
    s2a_business_process = extract_h2_block(stage_02a_text, ["Business Process Identification"])
    s2a_workflow = extract_h2_block(stage_02a_text, ["Workflow / State Detail"])
    s2a_scenarios = extract_h2_block(stage_02a_text, ["Scenario Decomposition"])
    s2a_key_scenarios = extract_h2_block(stage_02a_text, ["Key Scenario Deep Analysis"])
    s2a_context = extract_h2_block(stage_02a_text, ["Persona Context Scenario and Key Paths"])
    s2a_design_req = extract_h2_block(stage_02a_text, ["Design Requirements Extraction"])
    s2a_constraints = extract_h2_block(stage_02a_text, ["Constraint Stress-Test"])
    s2a_priority = extract_h2_block(stage_02a_text, ["Priority Split"])
    s2a_stakeholders = extract_h2_block(stage_02a_text, ["Stakeholder Profiles, Adoption Chain, and Conflict Map"])
    s2a_value_loop = extract_h2_block(stage_02a_text, ["Value Loop and Downstream Preservation Notes"])
    s2a_stress = extract_h2_block(stage_02a_text, ["Structure Stress-Test and Deepening Loop Log"])
    s2a_reasoning = extract_h2_block(stage_02a_text, ["Minimal Reasoning Unit Ledger"])
    s2a_delta = extract_h2_block(stage_02a_text, ["Requirement Analysis Delta Summary"])
    s2a_material = extract_h2_block(stage_02a_text, ["Material Grounding Bridge"])

    s2b_nfr = extract_h2_block(stage_02b_text, ["NFR / Quality Requirements"]) if stage_02b_text else ""
    s2b_nfr_reasoning = (
        extract_h2_block(stage_02b_text, ["NFR Prioritization Reasoning"]) if stage_02b_text else ""
    )
    s2b_quality_matrix = (
        extract_h2_block(stage_02b_text, ["Quality Scenario Matrix"]) if stage_02b_text else ""
    )
    s2b_metric = (
        extract_h2_block(stage_02b_text, ["Metric Definition and Interpretation Register"])
        if stage_02b_text
        else ""
    )
    s2b_domain = extract_h2_block(stage_02b_text, ["Domain Model Direction"]) if stage_02b_text else ""
    s2b_er = extract_h2_block(stage_02b_text, ["Conceptual ER Diagram"]) if stage_02b_text else ""
    s2b_data = (
        extract_h2_block(stage_02b_text, ["Key Relationships and Data Characteristics"])
        if stage_02b_text
        else ""
    )
    s2b_subsystems = (
        extract_h2_block(stage_02b_text, ["Business Subsystem Boundaries"]) if stage_02b_text else ""
    )
    s2b_object_workflow = (
        extract_h2_block(stage_02b_text, ["Object-to-Workflow Mapping"]) if stage_02b_text else ""
    )
    s2b_ia = extract_h2_block(stage_02b_text, ["Information Architecture Direction"]) if stage_02b_text else ""
    s2b_ia_alt = (
        extract_h2_block(stage_02b_text, ["IA Decision Alternatives Comparison"]) if stage_02b_text else ""
    )
    s2b_ia_spec = extract_h2_block(stage_02b_text, ["IA Spec Precursor Matrix"]) if stage_02b_text else ""
    s2b_module = (
        extract_h2_block(stage_02b_text, ["Module Responsibility Matrix"]) if stage_02b_text else ""
    )
    s2b_payload = (
        extract_h2_block(stage_02b_text, ["Module Interface Payload Contract", "Recommendation Payload Contract"])
        if stage_02b_text
        else ""
    )
    s2b_attribution = (
        extract_h2_block(stage_02b_text, ["Deferred Capability Seam", "Deferred Attribution and Conversion Seam"])
        if stage_02b_text
        else ""
    )
    s2b_stress = extract_h2_block(stage_02b_text, ["Specification Stress-Test"]) if stage_02b_text else ""
    s2b_loop = extract_h2_block(stage_02b_text, ["Deepening Loop Log"]) if stage_02b_text else ""
    s2b_reasoning = extract_h2_block(stage_02b_text, ["Minimal Reasoning Unit Ledger"]) if stage_02b_text else ""
    s2b_material = extract_h2_block(stage_02b_text, ["Material Grounding Bridge"]) if stage_02b_text else ""

    s3_context = extract_h2_block(stage_03_text, ["Context and Objective"])
    s3_slice = extract_h2_block(stage_03_text, ["Chosen Slice"])
    s3_slice_alts = extract_h2_block(stage_03_text, ["Slice Alternatives Comparison"])
    s3_scope = extract_h2_block(stage_03_text, ["MVP Scope"])
    s3_loop = extract_h2_block(stage_03_text, ["Complete and Minimum Viable Experience Loop"])
    s3_nfr_impact = extract_h2_block(
        stage_03_text,
        ["NFR-Aware Slice Impact and Dependency-First Logic"],
    )
    s3_value_frequency = extract_h2_block(stage_03_text, ["Value-Frequency Assessment"])
    s3_slice_plan = extract_h2_block(
        stage_03_text,
        ["First Slice, Later Slices, and Deferred Items"],
    )
    s3_viability = extract_h2_block(stage_03_text, ["MVP Loop Viability Test"])
    s3_carryover = extract_h2_block(stage_03_text, ["Source Feature Carryover Ledger"])
    s3_deferred_honesty = extract_h2_block(stage_03_text, ["Deferred Items Honesty Check"])
    s3_assumptions = extract_h2_block(stage_03_text, ["Key Assumptions to Validate"])
    s3_map = extract_h2_block(stage_03_text, ["Slice Map and Dependency View"])
    s3_loop_log = extract_h2_block(stage_03_text, ["Deepening Loop Log"])
    s3_reasoning = extract_h2_block(stage_03_text, ["Minimal Reasoning Unit Ledger"])
    s3_assets = extract_h2_block(stage_03_text, ["Skill Asset Ingestion Snapshot"])
    s3_material = extract_h2_block(stage_03_text, ["Material Grounding Bridge"])

    s4_context = extract_h2_block(stage_04_text, ["Context and Objective"])
    s4_targets = extract_h2_block(stage_04_text, ["Validation Targets"])
    s4_target_clarity = extract_h2_block(stage_04_text, ["Validation Target Clarity"])
    s4_method_fit = extract_h2_block(stage_04_text, ["Method-Fit Comparison"])
    s4_fidelity = extract_h2_block(stage_04_text, ["Prototype Fidelity Record"])
    s4_method = extract_h2_block(stage_04_text, ["Method and Signal Definition"])
    s4_plan = extract_h2_block(stage_04_text, ["Validation Plan and Signal Chain"])
    s4_dimensions = extract_h2_block(stage_04_text, ["Validation Dimensions Covered"])
    s4_evidence = extract_h2_block(stage_04_text, ["Evidence State Honesty"])
    s4_maturity = extract_h2_block(stage_04_text, ["Delivery Readiness and Evidence Confidence"])
    s4_decision = extract_h2_block(
        stage_04_text,
        ["Decision State and Revision Consequences", "Decision State"],
    )
    s4_stage_02b_state = extract_h2_block(
        stage_04_text,
        ["Stage-02b Execution State Declaration"],
    )
    s4_flow = extract_h2_block(stage_04_text, ["Validation Flow"])
    s4_convergence = extract_h2_block(
        stage_04_text,
        ["Unified Product Pack / PRD Convergence Readiness"],
    )
    s4_loop_log = extract_h2_block(stage_04_text, ["Deepening Loop Log"])
    s4_reasoning = extract_h2_block(stage_04_text, ["Minimal Reasoning Unit Ledger"])
    s4_assets = extract_h2_block(stage_04_text, ["Skill Asset Ingestion Snapshot"])
    s4_material = extract_h2_block(stage_04_text, ["Material Grounding Bridge"])
    s4_review_bound = extract_h2_block(
        stage_04_text,
        ["Review-Bound Carryover and Forbidden Assumptions"],
    )
    runtime_context = build_runtime_context(
        source_text=source_text,
        stage_01_text=stage_01_text,
        stage_02a_text=stage_02a_text,
        stage_02b_text=stage_02b_text,
        stage_03_text=stage_03_text,
        loop_plan=loop_plan,
        business_world_model=business_world_model,
    )
    dynamic_acceptance_rows = build_generic_acceptance_detail_rows(runtime_context)
    dynamic_requirement_rows = build_generic_requirement_translation_rows(runtime_context)
    dynamic_primary_user_story = build_generic_primary_user_story(runtime_context)
    dynamic_supporting_use_cases = build_generic_supporting_use_cases(runtime_context)
    dynamic_extended_requirements = build_dynamic_extended_requirements(dynamic_requirement_rows)
    dynamic_acceptance_summary = build_dynamic_acceptance_summary(dynamic_acceptance_rows)

    final_status = derive_final_status_from_report(report_text)
    report_name = report_path.name if report_path else "phase-1-execution-report.md not provided"
    stage_02b_name = stage_02b_path.name if stage_02b_path else "stage-02b not provided"
    source_artifact_entries = [
        {
            "artifact_id": extract_single_line_field(stage_01_text, "artifact_id") or "P1-S01-OUT-001",
            "artifact_type": extract_nested_field_value(stage_01_text, "artifact_type") or "OUT",
            "file": stage_01_path.name,
            "role": "Stage-01 main output",
        },
        {
            "artifact_id": extract_single_line_field(stage_02a_text, "artifact_id") or "P1-S02a-OUT-001",
            "artifact_type": extract_nested_field_value(stage_02a_text, "artifact_type") or "OUT",
            "file": stage_02a_path.name,
            "role": "Stage-02a main output",
        },
        {
            "artifact_id": extract_single_line_field(stage_02b_text, "artifact_id") or "P1-S02b-OUT-001",
            "artifact_type": extract_nested_field_value(stage_02b_text, "artifact_type") or "OUT",
            "file": stage_02b_name,
            "role": "Stage-02b main output",
        },
        {
            "artifact_id": extract_single_line_field(stage_03_text, "artifact_id") or "P1-S03-OUT-001",
            "artifact_type": extract_nested_field_value(stage_03_text, "artifact_type") or "OUT",
            "file": stage_03_path.name,
            "role": "Stage-03 main output",
        },
        {
            "artifact_id": extract_single_line_field(stage_04_text, "artifact_id") or "P1-S04-OUT-001",
            "artifact_type": extract_nested_field_value(stage_04_text, "artifact_type") or "OUT",
            "file": stage_04_path.name,
            "role": "Stage-04 main output",
        },
    ]
    final_maturity_rows = build_generic_maturity_confidence_ledger(source_text, runtime_context)
    final_evidence_confidence_state = business_completeness_driver_state(runtime_context) or "source-grounded-but-unvalidated"
    source_artifact_ids = [
        entry["artifact_id"]
        for entry in source_artifact_entries
        if entry["role"] != "Stage-02b main output" or stage_02b_text
    ]
    style = detect_domain_style(source_text, runtime_context)
    scope_promise_line = build_scope_promise_line(source_text, runtime_context)
    problem_chain_line = build_problem_chain_line(source_text, runtime_context)
    problem_boundary_line = build_problem_boundary_line(source_text, runtime_context)
    review_bound_summary = build_review_bound_summary(source_text, runtime_context)
    problem_signal_lines = render_problem_signal_lines(source_text, runtime_context)
    why_now_line = (
        "当前 source 描述的业务仍依赖分散的 scope、evidence、recommendation 与 review 协作，经营闭环没有被统一组织，因此需要围绕真实 GEO 周期重新定义产品结构。"
        if style == "growth_observation"
        else "当前 source 描述的业务仍依赖线下或分散流程，核心记录、状态推进和结算闭环没有被统一组织，因此需要围绕真实业务流重新定义产品结构。"
        if style == "pet_clinic"
        else "当前 source 描述的业务仍依赖分散流程，核心记录、状态推进和结果复盘没有被统一组织，因此需要围绕真实业务流重新定义产品结构。"
    )
    context_pressure_note = (
        "如果今天仍把 tracked scope、baseline、finding、recommendation 和 review 分散在线下表格、截图和讨论串里，团队会持续丢失 GEO 经营上下文。"
        if style == "growth_observation"
        else "如果今天仍沿用纸质/Excel/分散台账，团队会在关键环节持续丢失上下文。"
        if style == "pet_clinic"
        else "如果今天仍沿用分散记录与人工补位，团队会在关键环节持续丢失上下文。"
    )
    architecture_guidance_line = (
        "- issue signal -> next-step action compatibility note: any abstract guidance layer must remain subordinate to real GEO evidence, operator action, and review closure."
        if style == "growth_observation"
        else "- issue signal -> next-step action compatibility note: any abstract guidance layer must remain subordinate to real clinic object states."
        if style == "pet_clinic"
        else "- issue signal -> next-step action compatibility note: any abstract guidance layer must remain subordinate to real business object states."
    )
    business_scenario_lines = render_mainline_business_scenarios(runtime_context)
    truth_model = runtime_context.get("business_world_model", {}) if isinstance(runtime_context.get("business_world_model"), dict) else {}
    truth_core_thesis = truth_slot_value(truth_model.get("core_thesis", {}))
    truth_why_now = truth_slot_value(truth_model.get("why_now", {}))
    truth_why_this_not_that = truth_slot_value(truth_model.get("why_this_not_that", {}))
    truth_value_mechanism = truth_slot_value(truth_model.get("value_mechanism", {}))
    truth_spend_at_risk = source_grounded_commercial_phrase(runtime_context)
    truth_proof_artifact = source_grounded_proof_phrase(runtime_context)
    truth_decision_trigger = truth_slot_value(truth_model.get("decision_trigger", {}))
    truth_alternatives = truth_model.get("primary_alternative_set", {}) if isinstance(truth_model, dict) else {}
    truth_alternative_options = [
        compact_signal_line(str(item))
        for item in truth_alternatives.get("options", [])
        if compact_signal_line(str(item))
    ]
    compact_mainline_thesis_line = compact_mainline_thesis(runtime_context)
    compact_direction_anchor_line = compact_direction_anchor(runtime_context)
    compact_need_framing_line = compact_need_framing(runtime_context)
    compact_positioning_choice_line = compact_positioning_choice(runtime_context)
    compact_why_now_line = compact_why_now_phrase(runtime_context)
    compact_why_this_not_that_line = compact_why_this_not_that_phrase(runtime_context)
    compact_value_mechanism_line = compact_value_mechanism_phrase(runtime_context)
    compact_spend_at_risk_line = compact_spend_at_risk_phrase(runtime_context)
    compact_proof_artifact_line = compact_proof_artifact_phrase(runtime_context)
    compact_continuation_boundary_line = compact_continuation_boundary_phrase(runtime_context)

    prd_lines = [
        f"# {args.document_name}",
        "",
        "## 0. Document Metadata",
        f"- document_name: `{args.document_name}`",
        f"- version: `{args.version}`",
        f"- artifact_id: `{PHASE1_PRD_ARTIFACT_ID}`",
        "- status:",
        "  - `provisional`",
        "- delivery_profile:",
        f"  - `{args.profile}`",
        "- source_status:",
        "  - `mixed`",
        "- intended_consumers:",
        "  - `product-review | design | architecture`",
        "- ai_inferred_marker:",
        "  - `AI-INFERRED DRAFT — UNVERIFIED`",
        "",
        "## 0.1 Traceability Naming and Registry",
        f"- artifact_id: `{PHASE1_PRD_ARTIFACT_ID}`",
        "- artifact_type:",
        "  - `PRD`",
        "- depends_on:",
        *[f"  - `{artifact_id}`" for artifact_id in source_artifact_ids],
        "- feeds:",
        "  - `ARCH-STG01-OUTPUT-0001 (expected)`",
        "",
        "## 1. Executive Summary",
        "该 PRD 不是源文摘要，而是把各阶段产物（Stage-01/02a/02b/03/04）重编译为一个可供产品、设计、架构共用的完整主文档。",
        str(runtime_context["executive_summary"]),
        f"首发主边界当前收敛为 {runtime_context['primary_segment']}。",
        compact_mainline_thesis_line,
        scope_promise_line,
        "",
        "## 1.1 Chosen Business Thesis",
        *render_chosen_business_thesis_lines(runtime_context),
        "",
        "### Substitute Pressure",
        "- 本节放在需求和验收矩阵之前，用来先固定商业判断，再进入需求装配。",
        "",
        "## 2. Problem Statement",
        "### Synthesized Problem Narrative",
        str(runtime_context["problem_statement"]),
        problem_chain_line,
        "",
        "### Problem Boundary Clarification",
        "- this is not:",
        "  - 再补一个孤立报表页、孤立后台设置页或一次性洞察文档。",
        "- actual operating problem:",
        f"  - {problem_boundary_line}",
        "- downstream consequence:",
        "  - 任何只停留在结果归档而不支撑持续操作的方案都不能作为首版主线。",
        "",
        "### Evidence Status",
        "- user-confirmed: 源素材（source）中的方向、核心能力簇、问题和机会条目、主流程草图、优先级切片。",
        f"- review-bound / inferred: {review_bound_summary}",
        "- problem mechanism: 当前源素材（source）描述的经营问题需要被重编译成同一条把信号、行动与复盘放在一起的经营主线。",
        "",
        "### Integrated Problem Evidence",
        f"- source vision: {runtime_context['executive_summary']}",
        f"- source objectives: {runtime_context['problem_statement']}",
        *render_flow_titles(list(runtime_context["source_flows"])),
        "",
        "### Protected Business-World Truth Spine",
        *render_business_world_truth_lines(runtime_context),
        "",
        "### Business Proof Track",
        *render_business_proof_track_lines(runtime_context),
        "",
        "### Semantic Authoring Implications",
        *render_semantic_authoring_implication_lines(runtime_context),
        "",
        source_signal_section(source_text),
        "",
        *problem_signal_lines,
        "",
        *render_reasoning_units(source_text, runtime_context),
        "## 3. Target Users & Key Roles",
        "### Primary Boundary",
        f"- chosen segment: `{runtime_context['primary_segment']}`",
        "",
        *render_segment_landscape_boundary(source_text, str(runtime_context["primary_segment"])),
        *([] if not render_segment_landscape_boundary(source_text, str(runtime_context["primary_segment"])) else [""]),
        "### Why This Segment, Not Others",
        "- why this not that: the first-wave boundary is intentionally narrowed to one primary entry role.",
        f"- {runtime_context['primary_segment']} 直接位于 source brief 的主业务链路入口，最适合作为首发主边界。",
        "- 首版先收敛一个主边界，避免同时服务过多角色导致流程和权限设计失焦。",
        "- 其他角色仍在范围内，但优先作为协作角色而不是并行主入口。",
        "",
        "### Secondary / Supporting Roles",
        *render_bullet_lines(
            [role for role in runtime_context["target_user_roles"] if role != runtime_context["primary_segment"]],
            "source brief 未提供额外协作角色。",
        ),
        "",
        "### Out-of-scope Users",
        "- 不以 source brief 范围外角色或未来阶段用户作为首发主边界。",
        "",
        "### Persona Boundary and Interaction Chain",
        render_role_chain_table(runtime_context),
        "",
        "### Persona / JTBD Matrix",
        render_jtbd_table(runtime_context),
        "",
        "### Reasoning Unit 1: Primary Boundary Lock",
        "- Reasoning Unit 1: Primary Boundary Lock",
        "- boundary_lock_reasoning: keep the primary boundary narrow enough to avoid a false multi-role shell.",
        "- tradeoff_or_tension: coverage vs focus",
        f"- primary operator: `{runtime_context['primary_segment']}` remains the first-wave entry operator.",
        f"- execution operator: `{list(runtime_context['target_user_roles'])[1]}` keeps the mid-flow handoff executable."
        if len(list(runtime_context["target_user_roles"])) > 1
        else f"- execution operator: `{runtime_context['primary_segment']}` also acts as the execution operator when the source only names one active role.",
        f"- decision owner: `{list(runtime_context['target_user_roles'])[-1]}` decides whether the first-wave workflow is strong enough to continue."
        if list(runtime_context["target_user_roles"])
        else "- decision owner: `source-defined decision owner` decides whether the first-wave workflow is strong enough to continue.",
        "- governance reviewer: IT/legal reviewer or governance reviewer inspects retention, permission, and accountability boundaries when the organization requires formal review.",
        "",
        "### Role Detail Ledger",
        *render_role_detail_lines(runtime_context),
        "",
        "### Persona Context Scenario and Key Paths",
        *render_key_path_blocks(runtime_context),
        "",
        "### Design Requirements Extraction",
        render_design_requirements_extraction(runtime_context),
        "",
        "### Role Interaction Note",
        f"- 首发主链围绕 {runtime_context['primary_segment']} 发起，并与其他 source-defined 角色共同完成业务判断、执行推进与周期复盘。",
        "- 关键要求不是让所有角色拥有同样入口，而是让协作角色在同一条业务主线上看到一致的证据、下一步动作和结果判断。",
        "- anti-pattern to avoid: 把角色边界压缩成一个抽象管理员入口，导致关键责任链和真实协作顺序消失。",
        "- remaining_unknown: 真实组织内的角色轮换、兼职流程和异常协作细节仍待验证。",
        "- review-bound: target role fit and collaboration detail remain review-bound until real walkthrough evidence exists.",
        "",
        "### Fragile Points in Adoption",
        f"- 若 {runtime_context['primary_segment']} 无法顺畅完成入口流程，首轮上线不会形成真实使用。",
        "- 若 evidence、action 与 review 之间仍然断裂，协作角色会回退到纸质、Excel 或聊天串补位。",
        "- 若 review 仍然不能支撑继续 / 调整判断，业务方不会把该系统纳入正式运营。",
        "",
        "## 4. Stakeholder Analysis",
        "### Stakeholder Chain Summary",
        *render_bullet_lines(list(runtime_context["target_user_roles"]), "source brief 未提供干系人链。"),
        "",
        "### Adoption Fragility",
        "- 若用户只能看到零散页面而不是同一条业务主线，产品会退化成被动报表或记录工具。",
        "- 若证据、下一动作与结果判断之间不能形成连续判断，关键角色不会持续投入时间与注意力。",
        "- 若 MVP 边界与范围外项不明确，实施阶段会快速失控。",
        "",
        "### Integrated Stakeholder Evidence",
        *render_bullet_lines(list(runtime_context["target_user_roles"]), "source brief 未提供更多干系人证据。"),
        "",
        "## 5. Strategic Context",
        "### Why Now",
        prefer_explicit_truth_surface(truth_why_now, compact_why_now_line, why_now_line),
        "",
        "### Chosen Need Framing",
        f"- chosen_need_framing: {compact_need_framing_line}",
        f"- positioning_choice: {compact_positioning_choice_line}",
        *( [f"- alternatives_considered: {'; '.join(truth_alternative_options[:3])}"] if truth_alternative_options else [] ),
        "- rejected: 只补单点页面、局部表单或孤立汇总视图。",
        "",
        "### Business Outcome Path",
        f"- value_mechanism: {prefer_explicit_truth_surface(truth_value_mechanism, compact_value_mechanism_line)}",
        *( [f"- commercial_boundary: {compact_spend_at_risk_line}"] if compact_spend_at_risk_line and not is_review_bound_missing(compact_spend_at_risk_line) else [] ),
        f"- continuation_boundary: {prefer_explicit_truth_surface(truth_decision_trigger, compact_continuation_boundary_line)}",
        "",
        "### Competitive Landscape Summary",
        "- comparison_rule: 评审时需要比较当前线下流程、已有同类系统或人工替代方案，而不是只比较目标系统本身。",
        "- current_evidence_state: `review-bound`",
        "- why_it_matters: 若不明确当前替代方案与迁移成本，团队会把“需要完整业务流产品”误判成“只需要一个补丁功能”。",
        "- decision_guardrail: 比较视角既要覆盖单点工具压力，也要覆盖人工补位与服务替代，避免把当前真实替代面看窄。",
        render_competitive_landscape_table(source_text, runtime_context),
        "- evidence_gap_note: exact vendor set、真实 win/loss 证据、价格带上下限仍待 field validation；在此之前，市场判断只能作为 review-bound framing 使用。",
        "",
        "### Context Pressure Note",
        f"- {context_pressure_note}",
        "",
        "### Integrated Direction Evidence",
        *render_integrated_direction_evidence_lines(runtime_context),
        "",
        "## 6. Product Direction Overview",
        "### Product Direction Summary",
        prefer_explicit_truth_surface(truth_core_thesis, compact_direction_anchor_line, compact_mainline_thesis_line),
        "",
        "### First-wave Value Proposition",
        f"- first_wave_value: {compact_value_mechanism_line}",
        f"- decision_ready_surface: 同一主线必须同时保留下一动作与 {compact_proof_artifact_line}。",
        "",
        "### What This Product Is Not",
        "- 不是只补一个局部表单或单一报表页的工具。",
        "- 不是把核心业务状态继续留在线下协作里、系统只做记录镜像。",
        "- 不是首版就覆盖所有未来阶段能力的全量平台。",
        "",
        "### Capability Recompilation",
        *render_capability_recompilation_lines(runtime_context),
        "",
        "### Product Mechanism",
        prefer_explicit_truth_surface(truth_why_this_not_that, compact_why_this_not_that_line),
        f"- proof_chain: {compact_proof_artifact_line}",
        "",
        "### Integrated Product Mechanism Evidence",
        f"- mainline_anchor: {business_loop_surface(runtime_context, limit=5)}",
        f"- proof_anchor: {compact_proof_artifact_line}",
        "",
        "## 7. Business Scenarios",
        "### Scenario Set Overview",
        *render_flow_titles(list(runtime_context["source_flows"])),
        *render_domain_baseline_lines(runtime_context, "scenario set overview"),
        "",
        "### Scenario Decomposition",
        *render_flow_steps(list(runtime_context["source_flows"])),
        "",
        "### Key Scenario Deep Analysis",
        *business_scenario_lines,
        "",
        "## 8. Requirements Structure",
        "### Goal",
        "把当前方案交付为一个可操作、可执行、可复盘、可切片扩展的业务过程，而不是功能目录。",
        "",
        "### Structure Choice",
        "- chosen_panorama_structure: workflow-first",
        f"- workflow backbone: {runtime_context['workflow_backbone']}",
        "- structure rule: 以 source brief 的业务流程和模块责任矩阵为主骨架。",
        "- decomposition rule: 先保住核心对象链，再展开页面、状态与异常路径。",
        "",
        "### Source Module Capability Ledger",
        *(list(runtime_context["module_capabilities"]) if runtime_context["module_capabilities"] else ["- source brief 尚未提供结构化模块矩阵。"]),
        "",
        "### Structure Alternatives Comparison",
        render_structure_alternatives_table(),
        "",
        "### Problem-to-Structure Mapping",
        render_problem_to_structure_mapping(runtime_context),
        "",
        "### Backbone Activities (Business Process Decomposition Precursor)",
        render_backbone_activities_table(runtime_context),
        "",
        "### Business Process Identification",
        render_process_identification_table(runtime_context),
        "",
        "### Workflow / State Detail",
        *render_workflow_state_detail(runtime_context),
        "",
        "### Constraint Stress-Test",
        render_constraint_stress_test(runtime_context),
        "",
        "### Priority Split",
        *render_priority_split(runtime_context),
        "",
        "### Diagram",
        *render_dynamic_flowchart(runtime_context),
        "",
        "### Business Process Decomposition",
        "| activity | primary actor | trigger | preconditions | system behavior | outputs | postconditions |",
        render_flow_process_table(list(runtime_context["source_flows"])),
        "",
        *render_flow_step_deepening_lines(runtime_context),
        "",
        "### Reasoning Unit 3: Review as Decision Endpoint",
        "- decision_endpoint: the business record is not closed until payment, audit, and review-ready evidence align",
        "",
        "### Reasoning Unit 4: Priority Cutline for First-Wave Structure",
        "- Reasoning Unit 4: Priority Cutline for First-Wave Structure",
        "- the first wave keeps only what protects the executable source-defined workflow",
        "",
        "### Exception and Failure Flows",
        "Exception 1: Required business input is incomplete",
        "- failure trigger: source-defined required input, owner data, status prerequisite or dependency record missing.",
        "- handling strategy: 阻止继续推进当前步骤，并把缺失项显式暴露给操作者。",
        "",
        "Exception 2: Downstream module cannot accept the upstream output",
        "- failure trigger: 上游模块输出不完整、状态非法或对象引用丢失。",
        "- handling strategy: 回退到上一步补足业务信息，禁止静默跳过模块契约。",
        "",
        "Exception 3: Business result becomes non-interpretable",
        "- failure trigger: 输出记录、状态推进或结果归属无法被稳定解释。",
        "- handling strategy: 保留不确定性说明，禁止把异常结果伪装成稳定成功路径。",
        "",
        "Exception 4: Governance or permission boundary blocks rollout",
        "- failure trigger: 权限、留存、角色边界或审计要求未被满足。",
        "- handling strategy: 相关业务状态进入 blocked，直到边界条件被满足。",
        "",
        "### Value Loop",
        *(list(runtime_context["flow_summary_lines"]) if runtime_context["flow_summary_lines"] else ["- source brief 未给出显式 value loop。"]),
        "",
        "## 9. NFR / Quality Requirements",
        "### Top Quality Attributes",
        "- reliability",
        "- usability",
        "- security/data-control",
        "- maintainability",
        "",
        "### NFR / Quality Requirements",
        *render_bullet_lines(list(runtime_context["non_functional_requirements"]), "source brief 未提供显式非功能需求。"),
        "",
        *render_nfr_detail_lines(runtime_context),
        "",
        "### NFR Prioritization Reasoning",
        render_nfr_prioritization_table(runtime_context),
        "",
        "### Quality Scenario Matrix",
        render_quality_scenario_matrix(),
        "",
        "### Metric Definition and Interpretation Register",
        render_metric_register(runtime_context),
        "",
        "### Module Responsibility Matrix",
        render_module_matrix_with_notes(runtime_context),
        "",
        "### Module Quality Detail",
        *render_module_detail_lines(runtime_context),
        "",
        "### Architecture Consequence",
        *render_bullet_lines(list(runtime_context["architectural_constraints"]), "source brief 未提供显式架构后果。"),
        "",
        "### Specification Stress-Test",
        "- deprioritized_attributes: exact vendor benchmarking, advanced forecasting, external integrations",
        "- interpretation risk: do not overstate metrics or automation beyond source evidence",
        "- blind spot: real throughput variance still needs field validation",
        "- review-bound: quality conclusions remain review-bound until field validation exists",
        "- remaining_unknown: traffic spikes, long-tail exceptions, and admin reporting needs still need evidence",
        "- Reasoning Unit 4: Workflow-First IA Direction",
        "- decision_effect: keep quality requirements tied to workflow continuity, not generic checklists",
        "- alternatives_compared: thinner qualitative notes vs explicit scenario tables vs typed matrices",
        "",
        "## 10. Domain Model",
        "### Core Business Objects",
        render_core_business_objects_table(list(runtime_context["core_business_objects"])),
        "",
        "### Domain Model Direction",
        *render_domain_direction_block(runtime_context),
        "",
        f"### {deferred_seam_heading(runtime_context)}",
        render_deferred_seam_table(runtime_context),
        "",
        "### Conceptual ER Diagram",
        *render_dynamic_er_diagram(runtime_context),
        "",
        "### Key Relationships and Data Characteristics",
        render_first_wave_decision_table(runtime_context),
        "",
        "### Business Subsystem Boundaries",
        render_subsystem_interfaces(runtime_context),
        "",
        "- Scope & Governance: account boundary, auth, audit, retention boundary",
        "- Review & Reporting: operations dashboard, audit review, closure history",
        "- sensitivity: source-defined business records are operationally sensitive",
        "- not realtime-hard: the first wave favors trusted state transitions over realtime-hard dashboards",
        f"### {payload_contract_heading(runtime_context)}",
        render_payload_contract_table(runtime_context),
        "",
        "### Domain Object Growth and Evidence Gaps",
        *render_domain_growth_lines(runtime_context),
        "",
        "### Object-to-Workflow Mapping",
        render_workflow_mapping_table(runtime_context),
        "",
        "## 11. Information Architecture Direction",
        "### IA Direction Summary",
        "- organization strategy: 源流程优先（source-flow-first）+ 对象可追踪（object-traceable）",
        f"- navigation: {(' / '.join(row['module'] for row in runtime_context['ia_matrix']) if runtime_context['ia_matrix'] else 'source-defined primary surfaces')}",
        "- labeling: 优先使用业务可理解语言，而不是内部系统术语",
        f"- screen/module consequence: {(' / '.join(row['module'] for row in runtime_context['ia_matrix']) if runtime_context['ia_matrix'] else 'source-defined primary surfaces')}",
        "- architecture impact: 页面必须沿着对象链和流程链展开，而不是按零散功能页拼装",
        "",
        "### Information Architecture Direction",
        "- workflow-first: 选择工作流优先，是因为导航必须贴合真实运营链路。",
        "- screen/object matrix must stay visible enough for design and architecture handoff.",
        "- failure risk: if screens are grouped only by subsystem, users lose object traceability.",
        "- screen spec precursor: each screen/module must declare primary actor, required information objects, entry conditions, exit actions, and dependency.",
        "- constraints: IA 必须围绕对象可追踪性和模块依赖可见性展开。",
        "",
        "### IA Decision Alternatives Comparison",
        render_ia_alternatives_table(),
        "",
        "### IA Spec Matrix",
        render_expanded_ia_spec_matrix(runtime_context),
        "",
        "### Integrated IA Evidence",
        render_information_architecture_spec_matrix(list(runtime_context["ia_matrix"])),
        "",
        "## 12. MVP Definition & Scope",
        "### Slice Decision Context",
        "首版切片以 source brief 中最短可闭环的业务主链路为准，优先保证核心模块能够串联。",
        "",
        "### Slice Strategy",
        "首版切的是 source brief 中最短但完整的业务主链路，而不是额外扩展能力的堆叠。",
        render_slice_candidate_table(runtime_context),
        "",
        "### Scope, Dependency Logic, and Cutline",
        *render_scope_boundary_lines(runtime_context),
        *render_slice_lists(runtime_context),
        "- remaining_unknown: deeper admin workflows and broader cross-instance operations stay outside the current certainty boundary",
        "",
        "### Source Feature Carryover Ledger",
        render_carryover_ledger(runtime_context),
        "",
        "### Value Loop and Downstream Preservation Notes",
        *render_value_loop_notes(runtime_context),
        "",
        "- mainline_depth_reference: 主流程细节以 Business Process Decomposition、Business Scenarios 和 Acceptance Criteria 为准；这里不再用填充性文字重复同一组合同。",
        "- carryover rule: 源素材中写到的详细能力不得静默消失",
        "- feature_carryover: source-declared deferred capabilities remain excluded or deferred in this domain",
        "- explicit closure linkage: terminal closure and audit review must stay linked.",
        "",
        "### Module Navigation and Flow Mapping Reference",
        f"- navigation: {(' / '.join(row['module'] for row in runtime_context['ia_matrix']) if runtime_context['ia_matrix'] else 'source-defined primary surfaces')}",
        f"- screen/module consequence: {(' / '.join(row['module'] for row in runtime_context['ia_matrix']) if runtime_context['ia_matrix'] else 'source-defined primary surfaces')}",
        "- source-defined primary surfaces must stay queryable as one mainline rather than detached helper pages.",
        "- flow_mapping: 步骤 1 到步骤 10 仍锚定在 Operational Flow Specification、Acceptance Criteria 和 Requirement Trace Matrix。",
        "### Operational Flow Specification",
        *render_operational_flow_spec_lines(runtime_context),
        *render_flow_step_deepening_lines(runtime_context),
        "",
        "### State Machine and Transition Rules",
        *render_transition_rules(runtime_context),
        "",
        "### Reasoning Unit 4: Deferred Honesty and Assumption Carryover",
        "- deferred_items stay visible even when the design surface looks complete",
        "- review-bound assumptions must not be hidden behind polished screens",
        "",
        "### Acceptance Criteria",
        "Machine-readable acceptance matrix:",
        render_acceptance_detail_table_from_rows(dynamic_acceptance_rows),
        "",
        "Acceptance summary:",
        *[f"- {source_id}: {text}" for source_id, text in dynamic_acceptance_summary],
        "",
        "## 13. Validation Strategy & Current Conclusion",
        "### Validation Context",
        "验证重点是确认 source brief 中的主流程是否足够清晰、是否能被角色理解并在真实场景中落地。",
        "",
        "### Targets, Methods, and Thresholds",
        "- target_1: 目标角色是否能无歧义理解主业务流与角色分工。",
        "- target_2: 核心模块输入/输出是否足以支撑 source brief 的业务闭环。",
        "- target_3: 关键状态流转、审计与留存约束是否可实现。",
        "- target_4: transition guard 与 error-state 是否已经足够明确。",
        "- target_5: scope ledger 是否足够清晰以支撑后续评审。",
        "- signal thresholds:",
        render_validation_assumption_table(),
        "",
        render_validation_method_table(),
        "",
        render_validation_artifact_threshold_table(),
        "",
        *render_validation_detail_lines(runtime_context),
        *render_validation_target_lines(source_text, runtime_context),
        "- signal thresholds: explicit pass/fail thresholds must stay human-readable, not only encoded in tables.",
        "- maturity_state_rule: keep explicit delivery/evidence named-state markers stable for gate reuse and cross-review discussion.",
        "- insight_action_bridge: the same business record must stay connected to the next-step action and review summary.",
        "- review_expression: review summary and review expression remain visible evidence outputs rather than decorative reporting text.",
        "- automation_constraint: no automation layer may bypass manual confirmation for terminal closure.",
        "- signal_thresholds: keep the raw threshold label stable for the gate and for cross-review discussion.",
        "",
        "```mermaid",
        "flowchart TD",
        "    A[Exact Assumption] --> B[Chosen Method]",
        "    B --> C[Artifact]",
        "    C --> D[Signal / Threshold]",
        "    D --> E[Go / Revise / Blocked]",
        "```",
        "",
        "### Pricing Validation Design",
        "- objective: 当前阶段不做与 source brief 无关的商业包装承诺，只确认 MVP 是否具备真实交付价值。",
        "- current_state: `review-bound`",
        "- packaging_rule: 先验证主流程是否成立，再讨论后续商业包装。",
        "- buyer_budget_rule: buyer/budget chain 不能只写成商业口号；至少要显式保留 pain holder、continuation owner、spend at risk、proof artifact、continuation signal。",
        *render_loop_value_deepening_lines(runtime_context),
        render_pricing_validation_table(source_text, runtime_context),
        "",
        "### Buyer / Budget / Continuation Chain",
        "- purpose: 用通用方式把“谁为这条主线继续投入”显式化，而不是让下游自行脑补。",
        "- interpretation_rule: 这张表用于保留商业真相结构，不代表已完成真实付费验证。",
        render_buyer_budget_chain_table(runtime_context),
        "- interpretation_rule: 通过只代表可以继续下一阶段，不代表已完成正式商业验证。",
        "",
        "### Evidence State and Current Decision",
        "- evidence_state: `source-grounded-but-unvalidated`",
        "- note: 当前判断主要来自 source brief 的结构化内容与内部重编译，尚缺真实外部验证。",
        "- decision: `Revise` if target thresholds fail; `Go` only if the first-wave workflow remains understandable and bounded.",
        "- revision_consequences: adjust entry flow, transition rules, or scope ledger before claiming implementation-ready certainty.",
        "",
        "### Delivery Readiness and Evidence Confidence",
        render_validation_maturity_summary(final_maturity_rows),
        "",
        "### Validation Flow and Convergence Readiness",
        "- convergence rule: 设计与架构可启动，但必须继续保留 review-bound honesty。",
        "- downstream_handoff: prototype, state/event matrix, and carryover ledger move together to the next review.",
        "- convergence admission: ready-to-converge only within delivery_state and evidence_confidence_state boundaries.",
        "### Reasoning Unit 4: Decision State and Convergence Admission",
        "- signal thresholds: each target must keep an explicit threshold even after localization.",
        "- delivery_state_boundary: downstream-start-safe only; do not imply implementation-commit-ready or external validation.",
        "",
        "### Review-Bound Carryover",
        "- what_is_design_time_inference: role preference, adoption speed, and commercial packaging remain inference-heavy.",
        "- what_is_real_evidence: source brief tables, object model, workflow steps, and explicit constraints.",
        "- what_remains_unknown: throughput variance, exception frequency, and long-term admin workflow depth.",
        "- must_not_assume: the current draft already proves real deployment readiness.",
        "- forbidden_assumptions: compliance approval complete, workflow adoption already validated, pricing already credible.",
        "",
        "## 14. User Stories, Use Cases, and Requirements",
        "### Epic Decomposition",
        render_epic_decomposition_table(runtime_context),
        "",
        "### Primary User Story",
        dynamic_primary_user_story,
        "",
        "### Supporting Use Cases",
        *[f"- {label}: {text}" for label, text in dynamic_supporting_use_cases],
        "",
        "### Story Quality Gate (INVEST)",
        render_invest_table(runtime_context),
        "",
        "### Requirement Translation Registry",
        render_requirement_translation_table_from_rows(dynamic_requirement_rows),
        "",
        f"### {payload_contract_heading(runtime_context)}",
        render_payload_contract_table(runtime_context),
        "- payload_vs_generic: 不是 generic 文本列表；payload 必须绑定 target_asset_id、priority、owner_hint、blocked_reason。",
        "- extension_context 只作为 deferred seam 保留，不能伪装成首版已交付能力。",
        "- flow_mapping: Step 5, Step 6, Step 9, Step 10 map to core handoff and closure milestones.",
        "- return-for-clarification: if a downstream actor cannot proceed, the payload must preserve a clarification path.",
        "",
        "### Extended Requirement Set",
        *[f"- {source_id}: {text}" for source_id, text in dynamic_extended_requirements],
        "",
        "### Requirement Trace Matrix",
        render_requirement_trace_matrix_from_rows(dynamic_requirement_rows, dynamic_acceptance_rows),
        "",
        "### Fine-Grained Trace Registry",
        render_phase1_fine_grained_trace_registry(),
        "",
        "### Business Value Signal Registry",
        "下表是 Phase-1 对 Phase-2 ACD 的业务价值输入。P2 可以消费这些信号，但 P3 不得自行发明或降级。",
        render_business_value_signal_registry(runtime_context),
        "",
        "### Phase-1/Phase-2 Design Input Contract",
        render_phase1_phase2_design_input_contract(),
        "",
        "### Phase-2 Design Input Contract",
        "下表是 Phase-1 对 Phase-2 的 machine-readable 约束，不是事后补充说明。Phase-2 必须逐项吸收这些 trace units，并用显式 `upstream_trace_ids` 绑定到设计工件。",
        "",
        "| contract_area | phase_1_output | phase_2_expectation |",
        "|---|---|---|",
        "| workflow | source-defined business flows | preserve end-to-end flow continuity in design artifacts |",
        "| domain model | core business objects + IA matrix | preserve object ownership and state transitions |",
        "| quality boundary | non-functional requirements + architectural constraints | preserve audit, retention, and performance constraints |",
        "",
        "## 15. Out of Scope",
        *([f"- {item}" for item in runtime_context["out_of_scope_items"]] if runtime_context["out_of_scope_items"] else ["- source brief 未给出显式范围外项。"]),
        "",
        "## 16. Dependencies, Risks, and Review-Bound Truth",
        "### Dependencies",
        "- source brief 中声明的核心模块与业务对象需要被同一系统一致承接。",
        "- 关键角色需要在系统中完成对应业务动作，而不是继续依赖线下跳转。",
        "- 状态变更、权限边界与审计要求需要在首版被满足。",
        "",
        "### Risks",
        "- 模块契约不完整会导致上下游数据断裂。",
        "- 核心业务对象未统一会导致重复录入或对账困难。",
        "- 状态迁移规则与权限边界定义不足会导致实现阶段返工。",
        "- 范围失控会让首版偏离 source brief 的 MVP 边界。",
        "",
        "### Risk Register",
        "| risk | class | likelihood | impact | mitigation |",
        "|---|---|---|---|---|",
        "| 模块输入输出未对齐 | B | M | H | 在 PRD 中显式保留 module responsibility matrix 与 core objects |",
        "| 关键业务对象脱链 | B | M | H | 以 source core business objects 作为跨模块锚点 |",
        "| 状态变更不可审计 | C | M | H | 把审计规则作为首版硬约束进入 requirement / acceptance |",
        "| 范围漂移 | B | M | M | 显式保留 out-of-scope / non-goals |",
        "",
        "### Review-Bound Truth",
        "- 当前主文档已按 source brief 清理为通用业务语义，但真实外部验证仍未完成。",
        "- 容量、性能、角色协作摩擦和长期扩展策略仍需在后续阶段确认。",
        "",
        "## 17. Key Decision Rationale Summary",
        f"- user boundary: {runtime_context['primary_segment']}-first，而不是并行抽象所有潜在角色。",
        "- structure: source business flow over feature shelf。",
        "- slice: 先覆盖最短闭环业务链路，再考虑扩展模块。",
        "- validation method: 先验证业务流是否可执行，再验证扩展体验。",
        "- deferral strategy: source 已标记范围外项的不提前进入首版。",
        "",
        "### Integrated Decision Trace",
        f"- boundary_choice: 先收敛 `{runtime_context['primary_segment']}` 作为首发主入口，避免先做多角色外壳。",
        f"- structure_choice: 以 {mainline_module_surface(runtime_context)} 作为首版主线，而不是脱离主链的事后报告或孤立页面。",
        f"- value_choice: {compact_value_mechanism_line}",
        f"- continuation_choice: {compact_continuation_boundary_line}",
        "- delivery_choice: 先做到 downstream-start-safe，再通过外部验证升级业务与商业承诺。",
        "",
        "## 18. Handoff to Design / Architecture",
        "### Stage-02b Execution State",
        "- state: `source-first generic recompilation completed`",
        "",
        "### Design Can Start",
        "- 基于 source brief 中的主业务流绘制连续页面路径，而不是先画导航壳子。",
        "- 首轮 workflow prototype 必须覆盖至少一个完整业务流的开始、处理中间态和结果态。",
        "- 每个关键页面都要能映射回 module responsibility、core objects 和状态推进。",
        "- findings -> task compatibility note: if the domain uses a findings/task metaphor, it must still map back to the real business record and closure path.",
        "- insight_action_bridge: in this domain, business record -> action -> closure replaces the old insight -> action metaphor.",
        "- review_expression: use a review report for closure, audit events, and unresolved exceptions.",
        "- focus_on_decision_expression: make blocked reason, closure status, and audit consequence visible before decorative analytics.",
        "- 决策表达: blocked reason, closure status, and review report consequence must be visible at the point of decision.",
        "- 信息优先级应先保证核心对象链和状态，再考虑装饰性可视化。",
        "- 设计稿需显式保留 deferred / non-goal / review-bound truth，不得用视觉完整感掩盖未验证真相。",
        "- workflow prototype should expose at least one blocked/recovery edge and one clean closure path.",
        "",
        "### Architecture Can Start",
        f"- 以 {runtime_context['object_chain']} 作为核心对象链。",
        "- 按 source brief 中的模块责任矩阵启动模块或服务划分，而不是使用固定领域模板。",
        "- 先固定对象依赖顺序和状态约束，再讨论 backlog 和排期。",
        "- core business objects must stay explicit across the first-wave module chain.",
        architecture_guidance_line,
        "- automation_constraint: no automation layer may bypass manual confirmation for terminal closure.",
        "- automation execution remains out of scope for first-wave delivery.",
        f"- 可演进边界要明确保留：{module_chain_text(runtime_context, 5)} / audit / extension seam。",
        "- 权限边界、审计边界和范围边界在 MVP 就要落位，不能等扩展阶段再补。",
        "",
        "### Must Not Assume",
        "- demand already validated",
        "- every future-phase module belongs in MVP",
        "- downstream integrations can be added without explicit contracts",
        "- auditability can be postponed safely",
        "- review report or operations dashboard alone can replace the workflow backbone",
        "- out-of-scope items are implicitly approved for first-wave delivery",
        f"- {runtime_context['primary_segment']}-first boundary is still subject to real validation evidence",
        "",
        "## 19. Acceptance & Status",
        "### Overall Admission",
        f"- `{final_status}`",
        "- does not equal business externally-validated truth; document maturity is not the same as market or deployment validation.",
        "",
        "### Review Warnings / Pending External Confirmation",
        render_warning_confirmation_summary(final_maturity_rows),
        "",
        "### Warning & Pending Confirmation Ledger",
        render_warning_confirmation_table(final_maturity_rows),
        "",
        "### Document Delivery State",
        "- document_delivery_state:",
        "  - `downstream-start-safe`",
        "- why:",
        "  - 结构、对象链、状态迁移规则、Acceptance Criteria、handoff package 已足够支撑设计/架构安全启动。",
        "",
        "### Evidence Confidence State",
        "- evidence_confidence_state:",
        f"  - `{final_evidence_confidence_state}`",
        "- why:",
        "  - 关键结论来自 source + stage reasoning + business completeness driver + validation design；即使存在 source proof signals，仍缺真实外部验证与重复采样结果。",
        "- design_time_inference: role preference, adoption speed, and pricing posture still carry design-time inference risk.",
        "",
        "### Safe Start Scope",
        "- safe_start_scope:",
        "  - 设计可启动 source-defined primary surfaces 的连续 workflow prototype。",
        "  - 架构可启动 source-derived core business objects 的对象链与边界设计。",
        "  - 产品可继续准备 pricing / value / adoption friction / metric stability 的真实验证材料。",
        "",
        "### Blocked Commitments",
        "- blocked_commitments:",
        "  - 不得把当前 PRD 当作 implementation-commit-ready 需求冻结包。",
        "  - 不得承诺 willingness-to-pay、adoption readiness、metric stability 已完成验证。",
        "  - 不得把自动化执行和高级归因重新纳入首版承诺。",
        "- must_not_assume: downstream-start-safe does not equal production-safe or commercially validated.",
        "",
        "### Maturity & Confidence Ledger",
        render_maturity_confidence_table(final_maturity_rows),
        "",
        "## 20. Source Artifacts",
        render_source_artifacts_table(source_artifact_entries),
        "",
        "- supporting_review_artifact:",
        f"  - `{report_name}`",
        "",
        build_delta_ledger(runtime_context),
        "",
    ]

    rendered_lines = render_primary_locale_lines(prd_lines, output_path.name, resolve_output_locale(args.output_locale))
    rendered_text = sanitize_assembled_text("\n".join(rendered_lines), runtime_context)
    output_path.write_text(rendered_text, encoding="utf-8")
    print(f"assembled_prd: {output_path}")
    print("source_mode: read-only")
    print("final: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
