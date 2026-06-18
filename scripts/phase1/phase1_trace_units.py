#!/usr/bin/env python3
"""
Phase-1 PRD trace-unit helpers.

This module gives Phase-1 a stable, machine-readable fine-grained numbering layer
that downstream Phase-2 artifacts can reference directly.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence, Union

from common.markdown_table_tools import (
    markdown_tables,
    normalize_table_header,
    table_rows_with_required_headers,
)


def sanitize_domain_default_truth(value: Any, context: dict[str, Any] | None = None) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_domain_default_truth(item, context=context) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_domain_default_truth(item, context=context) for item in value]
    return value


PHASE1_PRD_ARTIFACT_ID = "P1-PRD-MAIN-0001"

EPIC_DECOMPOSITION: list[tuple[str, str]] = [
    ("EP-01", "Business Context and Intake Foundation"),
    ("EP-02", "Source Evidence and Next-Action Decisioning"),
    ("EP-03", "Execution and Review Closure"),
]

PRIMARY_USER_STORY = (
    "作为核心业务操作者，我希望在一个连续周期内完成源事实登记、状态推进、下一步动作和结果评审，以便判断该方案是否值得持续投入。"
)

SUPPORTING_USE_CASES: list[tuple[str, str]] = [
    ("Use Case 1", "识别关键缺口并定位到待处理的目标记录或资产。"),
    ("Use Case 2", "结合源事实和当前状态决定本周期优先推进的对象或环节。"),
    ("Use Case 3", "在结果评审中判断下一步动作执行后是否出现方向性改善。"),
    ("Use Case 4", "当下一步动作无法执行时，能把异常作为正式输入带回下一轮决策。"),
]

EXTENDED_REQUIREMENTS: list[tuple[str, str]] = [
    ("RQ-01", "系统必须支持业务上下文配置与版本记录。"),
    ("RQ-02", "系统必须校验当前状态分析所需的最小输入完整性。"),
    ("RQ-03", "系统必须可重复生成源事实状态快照，并记录处理窗口。"),
    ("RQ-04", "系统必须输出源定义的核心结果，并提供口径说明。"),
    ("RQ-05", "系统必须在源素材存在时支持相关对象、证据或参照信息的可追踪视图。"),
    ("RQ-06", "系统必须把源证据和评审结论映射为 structured next action。"),
    ("RQ-07", "structured next action 必须具备动作描述、优先级、目标对象指向和执行阻塞说明。"),
    ("RQ-08", "structured next action 必须可导出为 action record 清单并支持状态跟踪。"),
    ("RQ-09", "系统必须记录 action record 执行状态、责任角色与执行备注。"),
    ("RQ-10", "review record 必须提供变化说明、阈值和 uncertainty note。"),
    ("RQ-11", "系统必须显式标记 review-bound truths，禁止静默升级为 confirmed。"),
    ("RQ-12", "首版必须显式声明 out-of-scope 与 non-goals。"),
    ("RQ-13", "governance reviewer 必须能看到权限与留存边界。"),
    ("RQ-14", "当 structured next action 不可执行时，系统必须支持 return-for-clarification。"),
    ("RQ-15", "任何跨边界数据读写都必须被阻止或审计。"),
    (
        "RQ-16",
        "structured action payload 必须在适用时保留评分、诊断、结构化建议、对象指向、blocked_reason 等结构化字段。",
    ),
    (
        "RQ-17",
        "系统必须为 deferred extension 保留 extension seam，包括 source reference、platform、stage placeholder、outcome event、multi-entry placeholder 等字段或接口说明，但不得把它们包装成已完成 outcome 证明。",
    ),
    (
        "RQ-18",
        "产品边界必须用 source feature carryover ledger 显式声明哪些 source 细节被保留为 first-wave abstraction、later slice、deferred seam、explicit out-of-scope。",
    ),
]

ACCEPTANCE_CRITERIA: list[tuple[str, str]] = [
    ("AC-01", "用户可以创建 versioned business context，并保留最小对象集合。"),
    ("AC-02", "当 business context 缺少最小必填项时，系统阻止当前状态分析并提示缺失字段。"),
    ("AC-03", "source-grounded status report 至少展示三类核心结果，并保留解释口径。"),
    ("AC-04", "evidence detail 必须同时展示 gap explanation、source context 和 structured next action。"),
    ("AC-05", "structured next action 必须包含评分/诊断、结构化建议、焦点提示，以及目标对象指向，才能生成 action record。"),
    ("AC-06", "execution operator 可以把 structured next action 导出或创建为 action record，并记录责任人和状态。"),
    ("AC-07", "action record 状态至少支持 created / accepted / executed / blocked 四种状态。"),
    ("AC-08", "review record 必须关联上一周期分析与 action record 执行结果，形成 delta interpretation。"),
    ("AC-09", "当指标趋势不可解释时，系统必须显式标记 uncertainty note，而不是输出确定性结论。"),
    ("AC-10", "系统必须保留 in-scope / later slice / deferred seam / explicit out-of-scope / non-goals 的边界说明。"),
    ("AC-11", "核心页面必须沿着同一对象链可跳转。"),
    ("AC-12", "任何跨边界数据访问都必须被禁止或显式审计。"),
    (
        "AC-13",
        "structured action export 必须在适用时保留关键结构化字段和 blocked_reason，避免导出后丢失执行语义。",
    ),
    (
        "AC-14",
        "延后扩展能力即使 deferred，也必须保留 `source_reference` / `platform` / `stage_placeholder` / `outcome_event` / `multi-entry placeholder` 等 seam 字段或接口说明。",
    ),
    ("AC-15", "source feature carryover ledger 必须把关键 source features 分类为 first-wave abstraction / later slice / deferred seam / explicit out-of-scope，禁止静默丢失。"),
]

PHASE1_TRACE_UNIT_TYPE_MAP = {
    "epic_trace_units": "EPIC",
    "use_case_trace_units": "USECASE",
    "requirement_trace_units": "REQ",
    "acceptance_trace_units": "AC",
}

PHASE1_TRACE_UNIT_GROUP_ORDER = (
    "epic_trace_units",
    "use_case_trace_units",
    "requirement_trace_units",
    "acceptance_trace_units",
)


def phase2_design_contract_defaults(unit_type: str) -> dict[str, str]:
    if unit_type == "epic":
        return {
            "expected_phase2_surfaces": "stage_01_decision_trace_registry, stage_03_scenario_matrix, stage_04_verification_replay",
            "coverage_expectation": "explicit-decision-or-scenario-or-replay-binding-required",
            "binding_guidance": "bind this unit via `upstream_trace_ids` in Stage-01 decision rows, Stage-03 scenario rows, and/or Stage-04 replay rows",
        }
    if unit_type in {"primary-user-story", "use-case"}:
        return {
            "expected_phase2_surfaces": "stage_03_scenario_matrix, stage_04_verification_replay",
            "coverage_expectation": "explicit-scenario-or-replay-binding-required",
            "binding_guidance": "bind this unit via `upstream_trace_ids` in Stage-03 scenario rows and/or Stage-04 replay rows",
        }
    if unit_type == "requirement":
        return {
            "expected_phase2_surfaces": "stage_01_decision_trace_registry, stage_03_contract_trace_registry, stage_04_rbi_trace_registry",
            "coverage_expectation": "explicit-decision-or-contract-or-rbi-binding-required",
            "binding_guidance": "bind this unit via `upstream_trace_ids` in Stage-01 decisions and preserve it through contract/RBI traces",
        }
    if unit_type == "acceptance-criteria":
        return {
            "expected_phase2_surfaces": "stage_03_scenario_matrix, stage_04_verification_replay, stage_03_contract_trace_registry",
            "coverage_expectation": "explicit-scenario-or-replay-or-contract-binding-required",
            "binding_guidance": "bind this unit via `upstream_trace_ids` in quantified scenarios, contracts, and replay evidence",
        }
    return {
        "expected_phase2_surfaces": "phase_2_structured_artifact",
        "coverage_expectation": "explicit-binding-required",
        "binding_guidance": "bind this unit explicitly from the Phase-2 structured artifact that consumes it",
    }


def _trace_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index:03d}"


def build_epic_trace_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for idx, (source_id, text) in enumerate(EPIC_DECOMPOSITION, start=1):
        rows.append(
            enrich_phase1_trace_row(
                {
                    "trace_id": _trace_id("P1-EP", idx),
                    "source_id": source_id,
                    "unit_type": "epic",
                    "summary": text,
                    "source_anchor": source_id.lower(),
                }
            )
        )
    return rows


def build_use_case_trace_rows() -> list[dict[str, str]]:
    rows = [
        enrich_phase1_trace_row(
            {
                "trace_id": _trace_id("P1-US", 1),
                "source_id": "Primary User Story",
                "unit_type": "primary-user-story",
                "summary": PRIMARY_USER_STORY,
                "source_anchor": "primary-user-story",
            }
        )
    ]
    for idx, (label, text) in enumerate(SUPPORTING_USE_CASES, start=1):
        rows.append(
            enrich_phase1_trace_row(
                {
                "trace_id": _trace_id("P1-UC", idx),
                "source_id": label,
                "unit_type": "use-case",
                "summary": text,
                "source_anchor": f"use-case-{idx:02d}",
                }
            )
        )
    return rows


def build_requirement_trace_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for idx, (source_id, text) in enumerate(EXTENDED_REQUIREMENTS, start=1):
        rows.append(
            enrich_phase1_trace_row(
                {
                "trace_id": _trace_id("P1-REQ", idx),
                "source_id": source_id,
                "unit_type": "requirement",
                "summary": text,
                "source_anchor": source_id.lower(),
                }
            )
        )
    return rows


AcceptanceSummaryInput = Union[Sequence[tuple[str, str]], Mapping[str, str], None]


def ordered_acceptance_trace_summaries(acceptance_summaries: AcceptanceSummaryInput = None) -> list[tuple[str, str]]:
    if acceptance_summaries is None:
        return list(ACCEPTANCE_CRITERIA)
    if isinstance(acceptance_summaries, Mapping):
        return [
            (source_id, str(acceptance_summaries[source_id]))
            for source_id, _default_summary in ACCEPTANCE_CRITERIA
            if source_id in acceptance_summaries
        ]
    return [
        (str(source_id).strip(), str(summary).strip())
        for source_id, summary in acceptance_summaries
        if str(source_id).strip()
    ]


def build_acceptance_trace_rows(acceptance_summaries: AcceptanceSummaryInput = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for idx, (source_id, text) in enumerate(ordered_acceptance_trace_summaries(acceptance_summaries), start=1):
        rows.append(
            enrich_phase1_trace_row(
                {
                    "trace_id": _trace_id("P1-AC", idx),
                    "source_id": source_id,
                    "unit_type": "acceptance-criteria",
                    "summary": text,
                    "source_anchor": source_id.lower(),
                }
            )
        )
    return rows


def build_phase1_trace_units(acceptance_summaries: AcceptanceSummaryInput = None) -> dict[str, list[dict[str, str]]]:
    return {
        "epic_trace_units": build_epic_trace_rows(),
        "use_case_trace_units": build_use_case_trace_rows(),
        "requirement_trace_units": build_requirement_trace_rows(),
        "acceptance_trace_units": build_acceptance_trace_rows(acceptance_summaries),
    }


def phase1_trace_unit_counts() -> dict[str, int]:
    units = build_phase1_trace_units()
    return {
        "epic_units": len(units["epic_trace_units"]),
        "use_case_units": len(units["use_case_trace_units"]),
        "requirement_units": len(units["requirement_trace_units"]),
        "acceptance_units": len(units["acceptance_trace_units"]),
    }


def _escape_table_value(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def enrich_phase1_trace_row(row: dict[str, str]) -> dict[str, str]:
    enriched = dict(row)
    defaults = phase2_design_contract_defaults(enriched.get("unit_type", ""))
    for key, value in defaults.items():
        enriched[key] = str(enriched.get(key, "") or value)
    return {
        key: str(sanitize_domain_default_truth(value)) if isinstance(value, str) else value
        for key, value in enriched.items()
    }


def _compact_reader_table_value(value: str, *, max_chars: int) -> str:
    text = _escape_table_value(value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip(" ,;:") + "..."


def _reader_table_cell_limit(header: str, column_count: int, index: int) -> int:
    normalized = re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")
    if normalized in {"trace_id", "source_id", "unit_type"} or normalized.endswith("_id") or index <= 1:
        return 42
    if column_count >= 8:
        return 20
    if column_count >= 6:
        return 30
    return 48


def render_table(headers: Sequence[str], rows: Sequence[dict[str, str]], *, compact_reader: bool = False) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        cells = []
        for index, header in enumerate(headers):
            value = str(row.get(header, ""))
            if compact_reader:
                cells.append(
                    _compact_reader_table_value(
                        value,
                        max_chars=_reader_table_cell_limit(header, len(headers), index),
                    )
                )
            else:
                cells.append(_escape_table_value(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def phase1_phase2_design_contract_rows(units: dict[str, list[dict[str, str]]] | None = None) -> list[dict[str, str]]:
    if units is None:
        units = build_phase1_trace_units()
    rows: list[dict[str, str]] = []
    for group in PHASE1_TRACE_UNIT_GROUP_ORDER:
        for row in units.get(group, []):
            enriched = enrich_phase1_trace_row(row)
            rows.append(
                {
                    "phase1_trace_id": enriched["trace_id"],
                    "source_id": enriched.get("source_id", ""),
                    "unit_type": enriched.get("unit_type", ""),
                    "summary": enriched.get("summary", ""),
                    "expected_phase2_surfaces": enriched.get("expected_phase2_surfaces", ""),
                    "coverage_expectation": enriched.get("coverage_expectation", ""),
                    "binding_guidance": enriched.get("binding_guidance", ""),
                }
            )
    return rows


def render_phase1_phase2_design_input_contract(units: dict[str, list[dict[str, str]]] | None = None) -> str:
    return render_table(
        [
            "phase1_trace_id",
            "source_id",
            "unit_type",
            "summary",
            "expected_phase2_surfaces",
            "coverage_expectation",
            "binding_guidance",
        ],
        phase1_phase2_design_contract_rows(units),
        compact_reader=True,
    )


def render_phase1_prd_traceability_block(source_artifact_ids: Sequence[str]) -> str:
    counts = phase1_trace_unit_counts()
    lines = [
        "## 0.1 Traceability Naming and Registry",
        f"- artifact_id: `{PHASE1_PRD_ARTIFACT_ID}`",
        "- artifact_type:",
        "  - `PRD`",
        "- depends_on:",
    ]
    if source_artifact_ids:
        lines.extend(f"  - `{artifact_id}`" for artifact_id in source_artifact_ids)
    else:
        lines.append("  - `(none)`")
    lines.extend(
        [
            "- feeds:",
            "  - `ARCH-STG01-OUTPUT-0001 (expected)`",
            "- traceability_managed_by:",
            "  - `wff-base-traceability-management`",
            "- fine_grained_trace_units:",
            f"  - `epic_units={counts['epic_units']}`",
            f"  - `use_case_units={counts['use_case_units']}`",
            f"  - `requirement_units={counts['requirement_units']}`",
            f"  - `acceptance_units={counts['acceptance_units']}`",
        ]
    )
    return "\n".join(lines)


def render_phase1_fine_grained_trace_registry(overrides: dict[str, list[dict[str, str]]] | None = None) -> str:
    overrides = overrides or {}
    sections = [
        "- epic_trace_registry:",
        render_table(
            [
                "trace_id",
                "source_id",
                "unit_type",
                "summary",
                "source_anchor",
                "expected_phase2_surfaces",
                "coverage_expectation",
                "binding_guidance",
            ],
            overrides.get("epic_trace_units") or build_epic_trace_rows(),
            compact_reader=True,
        ),
        "",
        "- use_case_trace_registry:",
        render_table(
            [
                "trace_id",
                "source_id",
                "unit_type",
                "summary",
                "source_anchor",
                "expected_phase2_surfaces",
                "coverage_expectation",
                "binding_guidance",
            ],
            overrides.get("use_case_trace_units") or build_use_case_trace_rows(),
            compact_reader=True,
        ),
        "",
        "- requirement_trace_registry:",
        render_table(
            [
                "trace_id",
                "source_id",
                "unit_type",
                "summary",
                "source_anchor",
                "expected_phase2_surfaces",
                "coverage_expectation",
                "binding_guidance",
            ],
            overrides.get("requirement_trace_units") or build_requirement_trace_rows(),
            compact_reader=True,
        ),
        "",
        "- acceptance_trace_registry:",
        render_table(
            [
                "trace_id",
                "source_id",
                "unit_type",
                "summary",
                "source_anchor",
                "expected_phase2_surfaces",
                "coverage_expectation",
                "binding_guidance",
            ],
            overrides.get("acceptance_trace_units") or build_acceptance_trace_rows(),
            compact_reader=True,
        ),
    ]
    return "\n".join(sections)


def heading_section(text: str, heading: str, aliases: Sequence[str] | None = None) -> str:
    lines = text.splitlines()
    heading_candidates = [heading]
    if aliases:
        heading_candidates.extend(alias for alias in aliases if alias and alias not in heading_candidates)
    start = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        for candidate in heading_candidates:
            if stripped.startswith("### ") and candidate in stripped[4:]:
                start = idx
                break
        if start is not None:
            break
    if start is None:
        return ""
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("### ") or line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def parse_bulleted_labeled_items(block: str, label_prefix: str) -> list[tuple[str, str]]:
    pattern = re.compile(rf"^[ \t]*-[ \t]*({re.escape(label_prefix)}-[0-9]+):[ \t]*(.+?)\s*$", flags=re.MULTILINE)
    return [(match.group(1).strip(), match.group(2).strip()) for match in pattern.finditer(block)]


def parse_supporting_use_cases_from_prd(text: str) -> list[dict[str, str]]:
    block = heading_section(text, "Supporting Use Cases", aliases=["支撑用例"])
    rows: list[dict[str, str]] = []
    for idx, match in enumerate(re.finditer(r"^[ \t]*-[ \t]*(Use Case [0-9]+):[ \t]*(.+?)\s*$", block, flags=re.MULTILINE), start=1):
        rows.append(
            {
                "trace_id": _trace_id("P1-UC", idx),
                "source_id": match.group(1).strip(),
                "unit_type": "use-case",
                "summary": match.group(2).strip(),
                "source_anchor": f"use-case-{idx:02d}",
            }
        )
    return rows


def parse_epics_from_prd(text: str) -> list[dict[str, str]]:
    block = heading_section(text, "Epic Decomposition", aliases=["史诗分解"])
    rows: list[dict[str, str]] = []
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not {"epic_id", "epic_name"}.issubset(headers):
            continue
        for idx, row in enumerate(table["rows"], start=1):
            epic_id = row.get("epic_id", "").strip()
            epic_name = row.get("epic_name", "").strip()
            if not epic_id or not epic_name:
                continue
            rows.append(
                enrich_phase1_trace_row(
                    {
                        "trace_id": _trace_id("P1-EP", idx),
                        "source_id": epic_id,
                        "unit_type": "epic",
                        "summary": epic_name,
                        "source_anchor": epic_id.lower(),
                    }
                )
            )
        if rows:
            return rows
    for idx, match in enumerate(re.finditer(r"^[ \t]*-[ \t]*(EP-[0-9]+):[ \t]*(.+?)\s*$", block, flags=re.MULTILINE), start=1):
        rows.append(
            enrich_phase1_trace_row(
                {
                    "trace_id": _trace_id("P1-EP", idx),
                    "source_id": match.group(1).strip(),
                    "unit_type": "epic",
                    "summary": match.group(2).strip(),
                    "source_anchor": match.group(1).strip().lower(),
                }
            )
        )
    return rows


def fallback_phase1_trace_units(text: str) -> dict[str, list[dict[str, str]]]:
    epic_rows = parse_epics_from_prd(text)
    use_case_rows: list[dict[str, str]] = []
    primary_block = heading_section(text, "Primary User Story", aliases=["核心用户故事"])
    primary_story = ""
    for line in primary_block.splitlines()[1:]:
        if line.strip():
            primary_story = line.strip()
            break
    if primary_story:
        use_case_rows.append(
            enrich_phase1_trace_row(
                {
                "trace_id": _trace_id("P1-US", 1),
                "source_id": "Primary User Story",
                "unit_type": "primary-user-story",
                "summary": primary_story,
                "source_anchor": "primary-user-story",
                }
            )
        )
    use_case_rows.extend(parse_supporting_use_cases_from_prd(text))

    requirement_rows = [
        enrich_phase1_trace_row(
            {
            "trace_id": _trace_id("P1-REQ", idx),
            "source_id": source_id,
            "unit_type": "requirement",
            "summary": summary,
            "source_anchor": source_id.lower(),
            }
        )
        for idx, (source_id, summary) in enumerate(
            parse_bulleted_labeled_items(
                heading_section(text, "Extended Requirement Set", aliases=["扩展需求集"]),
                "RQ",
            ),
            start=1,
        )
    ]
    acceptance_rows = [
        enrich_phase1_trace_row(
            {
            "trace_id": _trace_id("P1-AC", idx),
            "source_id": source_id,
            "unit_type": "acceptance-criteria",
            "summary": summary,
            "source_anchor": source_id.lower(),
            }
        )
        for idx, (source_id, summary) in enumerate(
            parse_bulleted_labeled_items(
                heading_section(text, "Acceptance Criteria", aliases=["验收标准"]),
                "AC",
            ),
            start=1,
        )
    ]
    return {
        "epic_trace_units": epic_rows,
        "use_case_trace_units": use_case_rows,
        "requirement_trace_units": requirement_rows,
        "acceptance_trace_units": acceptance_rows,
    }


def block_lines(text: str, block_name: str) -> list[str]:
    lines = text.splitlines()
    start = None
    marker = f"- {block_name}:"
    for idx, line in enumerate(lines):
        if line.startswith(marker):
            start = idx
            break
    if start is None:
        return []
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("- ") and not line.startswith("  - "):
            break
        collected.append(line)
    return collected


def block_text(text: str, block_name: str) -> str:
    return "\n".join(block_lines(text, block_name)).strip()


def table_rows_from_block(text: str, block_name: str, required_headers: set[str]) -> list[dict[str, str]]:
    return table_rows_with_required_headers(block_text(text, block_name), required_headers)


def extract_phase1_trace_units(text: str) -> dict[str, list[dict[str, str]]]:
    extracted = {
        "epic_trace_units": table_rows_from_block(
            text,
            "epic_trace_registry",
            {"trace_id", "source_id", "unit_type", "summary", "source_anchor"},
        ),
        "use_case_trace_units": table_rows_from_block(
            text,
            "use_case_trace_registry",
            {"trace_id", "source_id", "unit_type", "summary", "source_anchor"},
        ),
        "requirement_trace_units": table_rows_from_block(
            text,
            "requirement_trace_registry",
            {"trace_id", "source_id", "unit_type", "summary", "source_anchor"},
        ),
        "acceptance_trace_units": table_rows_from_block(
            text,
            "acceptance_trace_registry",
            {"trace_id", "source_id", "unit_type", "summary", "source_anchor"},
        ),
    }
    if any(extracted.values()):
        return {
            group: [enrich_phase1_trace_row(row) for row in rows]
            for group, rows in extracted.items()
        }
    fallback = fallback_phase1_trace_units(text)
    return {
        group: [enrich_phase1_trace_row(row) for row in rows]
        for group, rows in fallback.items()
    }
