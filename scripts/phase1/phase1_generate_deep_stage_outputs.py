#!/usr/bin/env python3
"""
Generate deep Stage-01/02a/02b/03/04 artifacts from a Phase-1 source document.

This script is intentionally deterministic:
- extracts high-value source sections as evidence packs
- recompiles each stage with analysis scaffolding and method signals
- writes standalone stage artifacts suitable for gate evaluation
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import re
from pathlib import Path

from common.output_language import resolve_output_locale
from phase1.phase1_localize_prd_zh import render_primary_locale_lines
from phase1.phase1_product_source_direct_driver import build_product_source_direct_driver
from phase1.phase1_reasoning_runtime import (
    PHASE1_BUSINESS_WORLD_MODEL_FILENAME,
    PHASE1_BUSINESS_RELEASE_TRUTH_PACK_FILENAME,
    PHASE1_OPERATING_BASELINE_MODEL_FILENAME,
    PHASE1_PLANNING_CONTROL_TRUTH_PACK_FILENAME,
    PHASE1_PRODUCT_WORLD_DECISION_FILENAME,
    activated_method_families,
    activated_operator_texts,
    compile_business_world_truth_spine,
    compile_maturity_confidence_ledger,
    compile_stage_reasoning_units,
    sanitize_domain_default_truth,
)
from phase1.phase1_runtime_metadata import THINKING_VALUE_GAIN_OUTPUT_PROFILES
from phase1.phase1_source_text_normalization import normalize_source_handoff_phrases
from phase1.phase1_generation_kernel import (
    SOURCE_PACKET_EVIDENCE_ALIASES,
    HANDOFF_QUALIFIER_PATTERN,
    VALUE_SIGNAL_PATTERNS,
    COMMERCIAL_DECISION_PATTERNS,
    USER_EXPERIENCE_SIGNAL_PATTERNS,
    PRESSURE_SIGNAL_PATTERNS,
    SIGNAL_CONDITIONAL_PATTERN,
    SIGNAL_CONTRAST_PATTERN,
    SIGNAL_DECISION_PATTERN,
    SIGNAL_PAIN_PATTERN,
    SIGNAL_ACTIONABILITY_PATTERN,
    SIGNAL_NOUNISH_PATTERN,
    SIGNAL_LABEL_PREFIX_PATTERN,
    SIGNAL_SCAFFOLD_PREFIX_PATTERN,
    SIGNAL_OPERATIONAL_FRAGMENT_PATTERN,
    SIGNAL_CONSEQUENCE_PATTERN,
    SIGNAL_OPPORTUNITY_PREFIX_PATTERN,
    SIGNAL_NEGATIVE_CONDITIONAL_PATTERN,
    list_items_from_block,
    find_markdown_block,
    find_named_h2_block,
    source_packet_evidence_block,
    flatten_bullets,
    source_fact_text,
    is_handoff_qualifier_label,
    label_block_items,
    find_h2_block,
    demote_headings,
    unique_preserve_order,
    role_label,
    _normalized_label_key,
    preserved_display_label,
    detect_source_segments,
    extract_product_label,
    extract_main_flow_block,
    parse_markdown_table,
    slug_token,
    title_case_token,
    extract_table_rows,
    extract_target_user_rows,
    build_source_semantic_profile,
    _role_name_list,
    _find_role_by_hint,
    infer_fallback_module_contract,
    extract_module_rows,
    extract_object_rows,
    extract_business_objectives,
    extract_non_functional_requirements,
    extract_architectural_constraints,
    extract_out_of_scope_items,
    extract_priority_bucket,
    is_generic_flow_container_title,
    extract_flow_rows,
    derive_navigation_surfaces,
    infer_first_slice_modules,
    compact_signal_line,
    normalize_signal_candidate,
    collect_source_signal_pool,
    signal_intent_match,
    signal_priority_score,
    select_source_grounded_signals,
    extract_domain_context,
)

REVIEW_BOUND_MISSING = "review-bound / missing evidence"


SEMANTIC_POSTURE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "growth-observation",
        (
            "recommendation",
            "attribution",
            "conversion",
            "citation",
            "ai-friendly",
            "ai 友好",
            "引用",
            "转化",
            "归因",
            "竞品",
            "tracked scope",
            "finding",
            "baseline",
        ),
    ),
    (
        "operational-service",
        (
            "appointment",
            "visit",
            "treatment",
            "follow-up",
            "handoff",
            "work item",
            "service loop",
            "接诊",
            "就诊",
            "治疗",
            "复诊",
            "随访",
            "交接",
        ),
    ),
)

SEMANTIC_TOKEN_PATTERNS: tuple[tuple[str, str], ...] = (
    ("ai_friendliness", r"ai[-\s]*friendly|ai\s*友好|AI\s*友好"),
    ("quality_diagnosis", r"quality diagnosis|内容质量|质量诊断"),
    ("citation_likelihood", r"citation|引用概率|引用"),
    ("attribution", r"attribution|归因"),
    ("conversion_event", r"conversion|转化"),
    ("identity_resolution", r"identity|身份|跨设备"),
    ("keyword_focus", r"keyword|关键词"),
    ("question_focus", r"question|问答|问题"),
    ("rewrite_suggestion", r"rewrite|改写"),
    ("recommendation", r"recommendation|建议"),
    ("evidence_link", r"evidence|证据"),
    ("review_cycle", r"review|复盘|评审"),
    ("follow_up", r"follow[-\s]*up|复诊|随访"),
    ("treatment_record", r"treatment|治疗"),
    ("visit_record", r"visit|接诊|就诊"),
    ("appointment", r"appointment|预约"),
)


def nonempty_string_values(items: object) -> list[str]:
    candidates: Iterable[object] = items if not isinstance(items, str) and isinstance(items, Iterable) else [items]
    return [str(item).strip() for item in candidates if str(item).strip()]


def dict_or_empty(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def sequence_item_text(items: list[object], index: int, fallback: str) -> str:
    value = items[index] if -len(items) <= index < len(items) else ""
    text = str(value or "").strip()
    return text or fallback


def dict_sequence_field_text(rows: list[dict[str, object]], index: int, field: str, fallback: str) -> str:
    if not -len(rows) <= index < len(rows) or not isinstance(rows[index], dict):
        return fallback
    text = str(rows[index].get(field, "") or "").strip()
    return text or fallback


def source_semantic_profile_from_context(
    context: dict[str, object],
    *,
    module_name: str = "",
) -> dict[str, object]:
    existing = context.get("source_semantic_profile")
    if isinstance(existing, dict) and existing:
        return existing
    source_text = str(context.get("source_text", ""))
    roles = [
        {"Role": str(row.get("Role", "")).strip()}
        for row in context.get("roles", [])
        if isinstance(row, dict) and str(row.get("Role", "")).strip()
    ]
    module_hint = module_name or dict_sequence_field_text(
        [row for row in context.get("modules", []) if isinstance(row, dict)],
        0,
        "module",
        "",
    )
    return build_source_semantic_profile(source_text, module_name=module_hint, roles=roles)


def _source_semantic_blob(context: dict[str, object], profile: dict[str, object] | None = None) -> str:
    profile = profile or source_semantic_profile_from_context(context)
    values: list[str] = [str(context.get("source_text", ""))]
    for key in (
        "module_name",
        "domain_profile",
        "primary_actor",
        "role_names",
        "core_objects",
        "flow_steps",
        "source_evidence",
        "constraints",
        "outcomes",
    ):
        value = profile.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        else:
            values.append(str(value or ""))
    for key in (
        "objectives",
        "constraints",
        "nfrs",
        "out_of_scope",
        "p0",
        "p1",
        "p2",
        "business_value_signals",
        "pressure_signals",
        "commercial_decision_signals",
        "user_experience_signals",
    ):
        values.extend(str(item) for item in context.get(key, []) if str(item).strip())
    for row in context.get("modules", []):
        if isinstance(row, dict):
            values.extend(str(value) for value in row.values() if str(value).strip())
    return "\n".join(values)


def infer_source_semantic_posture(context: dict[str, object] | None, *, text: str = "") -> str:
    local_context = context if isinstance(context, dict) else {"source_text": text}
    profile = source_semantic_profile_from_context(local_context)
    blob = "\n".join([text, _source_semantic_blob(local_context, profile)]).casefold()
    scores: dict[str, int] = {}
    for posture, patterns in SEMANTIC_POSTURE_PATTERNS:
        scores[posture] = sum(1 for pattern in patterns if pattern.casefold() in blob)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] <= 0:
        return "generic-workflow"
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return "generic-workflow"
    return ranked[0][0]


def source_semantic_guard_context(
    context: dict[str, object] | None = None,
    *,
    text: str = "",
) -> dict[str, object]:
    local_context = context if isinstance(context, dict) else {"source_text": text}
    profile = source_semantic_profile_from_context(local_context)
    role_labels = [
        str(row.get("Role", "")).strip()
        for row in local_context.get("roles", [])
        if isinstance(row, dict) and str(row.get("Role", "")).strip()
    ]
    if not role_labels:
        role_labels = [str(item).strip() for item in profile.get("role_names", []) if str(item).strip()]
    primary_segment = str(profile.get("primary_actor", "")).strip() or sequence_item_text(role_labels, 0, "primary operator")
    return {
        "domain_posture": infer_source_semantic_posture(local_context, text=text),
        "primary_segment": primary_segment,
        "role_labels": role_labels,
        "supporting_role_label": sequence_item_text(role_labels, 1, ""),
        "decision_role_label": sequence_item_text(role_labels, -1, primary_segment),
    }


def render_labeled_markdown_list_lines(
    label: str,
    items: object,
    *,
    fallback: str,
    code: bool = False,
) -> list[str]:
    values = nonempty_string_values(items) or [fallback]
    return [
        f"- {label}:",
        *(f"  - `{item}`" if code else f"  - {item}" for item in values),
    ]


def truth_slot_value(slot: object) -> str:
    return str(slot.get("value", "") if isinstance(slot, dict) else slot or "").strip()


def render_truth_slot_lines(label: str, slot: object) -> list[str]:
    if not isinstance(slot, dict):
        return [f"### {label}", f"- truth_state: `{REVIEW_BOUND_MISSING}`", f"- value: {REVIEW_BOUND_MISSING}"]
    lines = [
        f"### {label}",
        f"- truth_state: `{slot.get('truth_state', 'review-bound')}`",
        f"- value: {slot.get('value', REVIEW_BOUND_MISSING)}",
    ]
    source_signals = nonempty_string_values(slot.get("source_signals", []))
    if source_signals:
        lines.append("- source_signals:")
        lines.extend(f"  - {item}" for item in source_signals)
    return lines


REPO_ROOT = Path(__file__).resolve().parents[2]
STAGE_ASSET_PATHS = {
    "stage_01": {
        "sop": REPO_ROOT / "reference-packages/phase1-product-requirements/stage-01-user-research/stage-sop.md",
        "source_cards": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-01-user-research/source-cards.md",
        "source_register": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-01-user-research/source-register.md",
        "output_template": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-01-user-research/output-template.md",
    },
    "stage_02a": {
        "sop": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-02-requirements-analysis/stage-sop.md",
        "source_cards": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-02-requirements-analysis/source-cards.md",
        "source_register": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-02-requirements-analysis/source-register.md",
        "output_template": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-02-requirements-analysis/output-template.md",
    },
    "stage_02b": {
        "sop": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-02b-requirements-specification/stage-sop.md",
        "source_cards": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-02b-requirements-specification/source-cards.md",
        "source_register": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-02b-requirements-specification/source-register.md",
        "output_template": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-02b-requirements-specification/output-template.md",
    },
    "stage_03": {
        "sop": REPO_ROOT / "reference-packages/phase1-product-requirements/stage-03-requirements-decomposition/stage-sop.md",
        "source_cards": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-03-requirements-decomposition/source-cards.md",
        "source_register": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-03-requirements-decomposition/source-register.md",
        "output_template": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-03-requirements-decomposition/output-template.md",
    },
    "stage_04": {
        "sop": REPO_ROOT / "reference-packages/phase1-product-requirements/stage-04-requirements-validation/stage-sop.md",
        "source_cards": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-04-requirements-validation/source-cards.md",
        "source_register": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-04-requirements-validation/source-register.md",
        "output_template": REPO_ROOT
        / "reference-packages/phase1-product-requirements/stage-04-requirements-validation/output-template.md",
    },
}

REFERENCE_DOC_PRIORITY = (
    "stage-guidance-draft.md",
    "alignment-review.md",
    "index-map.md",
    "source-manifest.md",
)

STAGE_TRACEABILITY = {
    "stage_01": {
        "artifact_id": "P1-S01-OUT-001",
        "artifact_type": "OUT",
        "depends_on": [],
        "feeds": ["P1-S02a-OUT-001 (expected)"],
    },
    "stage_02a": {
        "artifact_id": "P1-S02a-OUT-001",
        "artifact_type": "OUT",
        "depends_on": ["P1-S01-OUT-001"],
        "feeds": ["P1-S02b-OUT-001 (expected)", "P1-S03-OUT-001 (expected)"],
    },
    "stage_02b": {
        "artifact_id": "P1-S02b-OUT-001",
        "artifact_type": "OUT",
        "depends_on": ["P1-S02a-OUT-001"],
        "feeds": ["P1-S03-OUT-001 (expected)", "P1-S04-OUT-001 (expected)"],
    },
    "stage_03": {
        "artifact_id": "P1-S03-OUT-001",
        "artifact_type": "OUT",
        "depends_on": ["P1-S02a-OUT-001", "P1-S02b-OUT-001"],
        "feeds": ["P1-S04-OUT-001 (expected)"],
    },
    "stage_04": {
        "artifact_id": "P1-S04-OUT-001",
        "artifact_type": "OUT",
        "depends_on": ["P1-S03-OUT-001"],
        "feeds": ["P1-S04-HND-001 (expected)", "P1-CNV-PRD-001 (expected)"],
    },
}


@dataclass(frozen=True)
class Phase1SourceSections:
    h21: str
    h22: str
    h23: str
    h24: str
    h31: str
    h32: str
    h33: str
    h34: str
    h41: str
    h42: str
    h43: str
    h51: str
    h52: str
    h53: str
    h61: str
    h62: str
    h7p0: str
    h7p1: str
    h7p2: str
    h8: str
    h_features: str
    h_ui: str
    h_adv: str
    h9: str
    h10: str
    h12: str
    first_part: str


def build_phase1_source_sections(source_text: str) -> Phase1SourceSections:
    return Phase1SourceSections(
        h21=find_h2_block(source_text, r"2\.1\s+项目/产品背景"),
        h22=find_h2_block(source_text, r"2\.2\s+业务机会描述"),
        h23=find_h2_block(source_text, r"2\.3\s+研究对象/目标用户边界"),
        h24=find_h2_block(source_text, r"2\.4\s+至少\s*1\s*条可引用证据线索"),
        h31=find_h2_block(source_text, r"3\.1\s+产品/业务目标方向"),
        h32=find_h2_block(source_text, r"3\.2\s+结构化问题清单"),
        h33=find_h2_block(source_text, r"3\.3\s+结构化机会清单"),
        h34=find_h2_block(source_text, r"3\.4\s+至少\s*1\s*条用户叙事"),
        h41=find_h2_block(source_text, r"4\.1\s+关键约束"),
        h42=find_h2_block(source_text, r"4\.2\s+指标口径最小定义"),
        h43=find_h2_block(source_text, r"4\.3\s+范围边界与非目标"),
        h51=find_h2_block(source_text, r"5\.1\s+MVP 分期"),
        h52=find_h2_block(source_text, r"5\.2\s+最小可用体验闭环"),
        h53=find_h2_block(source_text, r"5\.3\s+影响切片顺序的依赖假设"),
        h61=find_h2_block(source_text, r"6\.1\s+验证对象"),
        h62=find_h2_block(source_text, r"6\.2\s+每条验证的最小方法与判定信号"),
        h7p0=find_h2_block(source_text, r"P0（MVP 必须有）"),
        h7p1=find_h2_block(source_text, r"P1（MVP 后尽快补）"),
        h7p2=find_h2_block(source_text, r"P2（后续阶段）"),
        h8=extract_main_flow_block(source_text),
        h_features=find_h2_block(source_text, r"🛠️\s*产品必须实现的核心功能"),
        h_ui=find_h2_block(source_text, r"📱\s*详细产品功能设计"),
        h_adv=find_h2_block(source_text, r"🚀\s*产品优势"),
        h9=find_h1_block(source_text, r"第九部分：需要后续补实的 unknown / provisional 信息"),
        h10=find_h1_block(source_text, r"第十部分：统一 provenance / provisional 标记表"),
        h12=find_h1_block(source_text, r"第十二部分：结论（供 Phase-1 验收使用）"),
        first_part=find_h1_block(source_text, r"第一部分：原版\s*PRD\s*核心内容"),
    )


@dataclass(frozen=True)
class Phase1SourceSnapshot:
    sections: Phase1SourceSections
    context: dict[str, object]
    business_world_model: dict[str, object]
    product_label: str
    segments: list[str]
    primary_segment: str
    alternative_segments: list[str]
    roles: list[dict[str, str]]
    modules: list[dict[str, str]]
    flows: list[dict[str, object]]
    first_slice_modules: list[str]
    module_names: list[str]
    module_chain: str
    primary_flow_name: str
    main_roles: list[str]


def build_phase1_source_snapshot(source_text: str) -> Phase1SourceSnapshot:
    sections = build_phase1_source_sections(source_text)
    context = extract_domain_context(source_text)
    business_world_model = build_business_world_model(source_text)
    segments = list(context["segments"])
    primary_segment = str(segments[0])
    roles = list(context["roles"])
    modules = list(context["modules"])
    flows = list(context["flows"])
    first_slice_modules = [str(item).strip() for item in context.get("first_slice_modules", []) if str(item).strip()]
    module_names = [str(row.get("module", "")).strip() for row in modules if str(row.get("module", "")).strip()]
    main_roles = [str(role.get("Role", "")).strip() for role in roles if str(role.get("Role", "")).strip()] or [primary_segment]
    return Phase1SourceSnapshot(
        sections=sections,
        context=context,
        business_world_model=business_world_model,
        product_label=str(context["product_label"]),
        segments=segments,
        primary_segment=primary_segment,
        alternative_segments=segments[1:] or ["secondary collaborator", "review stakeholder"],
        roles=roles,
        modules=modules,
        flows=flows,
        first_slice_modules=first_slice_modules,
        module_names=module_names,
        module_chain=" -> ".join(module_names) or "source-defined workflow",
        primary_flow_name=dict_sequence_field_text(flows, 0, "name", "Primary Flow"),
        main_roles=main_roles,
    )


@dataclass(frozen=True)
class Stage01SourceBundle:
    h21: str
    h22: str
    h23: str
    h24: str
    h31: str
    h32: str
    h33: str
    h34: str
    first_part: str
    context: dict[str, object]
    business_world_model: dict[str, object]
    product_label: str
    segments: list[str]
    primary_segment: str
    alternative_segments: list[str]
    objectives: list[str]
    modules: list[dict[str, str]]
    roles: list[dict[str, str]]
    flows: list[dict[str, object]]
    constraints: list[str]
    nfrs: list[str]
    out_of_scope: list[str]
    flow_summary: str
    problem_cluster_lines: str
    opportunity_cluster_lines: str
    deferred_lines: str
    open_truth_lines: str
    persona_chain_rows: str


@dataclass(frozen=True)
class Stage02aSourceBundle:
    h23: str
    h31: str
    h32: str
    h33: str
    h34: str
    h41: str
    h43: str
    h7p0: str
    h7p1: str
    h7p2: str
    h8: str
    h51: str
    h52: str
    h53: str
    h61: str
    h62: str
    context: dict[str, object]
    business_world_model: dict[str, object]
    product_label: str
    segments: list[str]
    primary_segment: str
    modules: list[dict[str, str]]
    objectives: list[str]
    flows: list[dict[str, object]]
    module_names: list[str]
    workflow_chain: str
    roles: list[dict[str, str]]
    constraints: list[str]
    out_of_scope: list[str]
    p0_items: list[str]
    p1_items: list[str]
    p2_items: list[str]


@dataclass(frozen=True)
class Stage02aStructuralMappingContext:
    supporting_role_lines: str
    problem_cluster_lines: str
    opportunity_cluster_lines: str
    backbone_lines: str
    process_rows: str
    first_flow_steps: list[str]
    primary_step_lines: str
    actor_system_lines: str


@dataclass(frozen=True)
class Stage02aStakeholderValueLines:
    profile_rows: str
    adoption_chain_lines: str
    conflict_map_lines: str
    value_loop_lines: str
    chain_line: str
    scenario_set_lines: str


@dataclass(frozen=True)
class Stage02aStakeholderValueContext:
    stress_business: str
    stress_technical: str
    stress_compliance: str
    stress_resource: str
    value_pressure: str
    commercial_pressure: str
    experience_pressure: str
    stakeholder_profile_rows: str
    adoption_chain_lines: str
    conflict_map_lines: str
    value_loop_lines: str
    stakeholder_chain_line: str
    scenario_set_lines: str


@dataclass(frozen=True)
class Stage02aAnalysisBlocks:
    scenario_decomposition: str
    key_scenario_deep_analysis: str
    persona_context: str
    design_requirements: str
    nfr_identification: str


@dataclass(frozen=True)
class Stage02aRenderContext:
    source_bundle: Stage02aSourceBundle
    structural_mapping_context: Stage02aStructuralMappingContext
    analysis_blocks: Stage02aAnalysisBlocks
    stakeholder_value_context: Stage02aStakeholderValueContext
    skill_assets: dict[str, object]
    reasoning_units: list[dict[str, object]]


@dataclass(frozen=True)
class Stage02bSpecificationContext:
    nfr_lines: str
    nfr_reasoning_rows: str
    metric_rows: str
    subsystem_lines: str
    subsystem_interface_lines: str
    screen_precursor_lines: str
    screen_object_lines: str
    payload_heading: str
    deferred_heading: str
    er_rows: str


@dataclass(frozen=True)
class Stage02bRenderContext:
    product_label: str
    domain_context: dict[str, object]
    business_world_model: dict[str, object]
    specification_context: Stage02bSpecificationContext
    primary_actor: str
    module_chain: str
    objects: list[dict[str, str]]
    navigation_surfaces: list[str]
    modules: list[dict[str, str]]
    reasoning_units: list[dict[str, object]]
    skill_assets: dict[str, object]
    source_evidence_blocks: list[str]


@dataclass(frozen=True)
class Stage02bSkipStubContext:
    stage_02a_nfr: str
    stage_02a_value_loop: str


@dataclass(frozen=True)
class Stage03SourceBundle:
    h51: str
    h52: str
    h53: str
    h7p0: str
    h7p1: str
    h7p2: str
    h8: str
    context: dict[str, object]
    business_world_model: dict[str, object]
    product_label: str
    segments: list[str]
    primary_segment: str
    roles: list[dict[str, str]]
    modules: list[dict[str, str]]
    flows: list[dict[str, object]]
    nfrs: list[str]
    constraints: list[str]
    out_of_scope: list[str]
    p0_items: list[str]
    p1_items: list[str]
    p2_items: list[str]
    full_loop: str
    first_slice_loop: str
    minimum_loop: str
    primary_flow_name: str
    main_roles: list[str]


@dataclass(frozen=True)
class Stage04ValidationPlan:
    stage03_assumptions: list[dict[str, str]]
    validation_targets: list[dict[str, str]]
    method_rows: list[str]


@dataclass(frozen=True)
class Stage04SourceBundle:
    h61: str
    h62: str
    h9: str
    h10: str
    h12: str
    context: dict[str, object]
    product_label: str
    segments: list[str]
    primary_segment: str
    roles: list[dict[str, str]]
    modules: list[dict[str, str]]
    flows: list[dict[str, object]]
    objectives: list[str]
    constraints: list[str]
    out_of_scope: list[str]
    module_chain: str
    primary_flow_name: str
    stage03_assumptions: list[dict[str, str]]
    validation_targets: list[dict[str, str]]
    method_rows: list[str]


@dataclass(frozen=True)
class Stage04Stage02bExecutionContext:
    upstream_lines: str
    state_block: str


@dataclass(frozen=True)
class Stage04RenderContext:
    source_bundle: Stage04SourceBundle
    stage_02b_execution_context: Stage04Stage02bExecutionContext
    upstream_evidence_blocks: list[str]
    source_evidence_blocks: list[str]
    skill_assets: dict[str, object]
    reasoning_units: list[dict[str, object]]
    maturity_rows: list[dict[str, str]]


@dataclass(frozen=True)
class Stage03SlicePlanningContext:
    comparison_rows: list[str]
    nfr_force_lines: str
    nfr_relaxed_lines: str
    dependency_impact_lines: str
    value_frequency_rows: str
    deferred_honesty_rows: str
    key_assumption_lines: str
    flow_nodes: list[str]
    slice_map: str


@dataclass(frozen=True)
class Stage03SlicePlanningLines:
    comparison_rows: list[str]
    nfr_force_lines: str
    nfr_relaxed_lines: str
    dependency_impact_lines: str
    value_frequency_rows: str
    deferred_honesty_rows: str


@dataclass(frozen=True)
class Stage03SliceValidationItems:
    first_slice_items: list[str]
    later_slice_items: list[str]
    deferred_items: list[str]
    first_break_item: str
    second_break_item: str


@dataclass(frozen=True)
class Stage03Stage02bCarryoverContext:
    upstream_lines: str
    availability: str
    skip_effect: str


@dataclass(frozen=True)
class Stage03EvidenceContext:
    upstream_value_loop_block: str
    upstream_evidence_blocks: list[str]
    source_evidence_blocks: list[str]


@dataclass(frozen=True)
class Stage03RenderContext:
    source_bundle: Stage03SourceBundle
    slice_planning_context: Stage03SlicePlanningContext
    stage_02b_carryover_context: Stage03Stage02bCarryoverContext
    evidence_context: Stage03EvidenceContext
    skill_assets: dict[str, object]
    reasoning_units: list[dict[str, object]]


@dataclass(frozen=True)
class Phase1DeepStageTexts:
    stage_01_text: str
    stage_02a_text: str
    stage_02b_text: str
    stage_03_text: str
    stage_04_text: str

    def ordered_texts(self) -> list[str]:
        return [
            self.stage_01_text,
            self.stage_02a_text,
            self.stage_02b_text,
            self.stage_03_text,
            self.stage_04_text,
        ]


@dataclass(frozen=True)
class BusinessWorldModelArtifactPaths:
    business_world_model: Path
    semantic_authoring_spine: Path
    operating_baseline_model: Path
    product_world_decision: Path
    business_release_truth_pack: Path
    planning_control_truth_pack: Path
    business_exploration_arena_json: Path
    business_exploration_arena_md: Path
    commercial_argument_draft_json: Path
    commercial_argument_draft_md: Path
    chosen_business_thesis_json: Path
    chosen_business_thesis_md: Path


@dataclass(frozen=True)
class ThinkingValueGainContext:
    output_profile: str
    profile_copy: dict[str, str]
    arena: dict[str, object]
    chosen_name: str
    primary_substitute: str
    primary_pain: str
    proof_target: str
    continuation_owner: str
    boundary: str
    reality_focus: str
    delivery_handoff_items: list[dict[str, str]]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render_demoted_evidence_pack(heading: str, *blocks: str) -> str:
    return f"{heading}\n" + "\n\n".join(demote_headings(block) for block in blocks)


def render_source_evidence_pack(heading: str, *blocks: str) -> str:
    return render_demoted_evidence_pack(heading, *blocks)


def render_evidence_chain_sections(
    *,
    ledger_heading: str,
    material_heading: str,
    snapshot_heading: str,
    method_heading: str,
    source_heading: str,
    reasoning_units: list[dict[str, str | list[str]]],
    context: dict[str, object],
    skill_assets: dict[str, object],
    snapshot_runtime_use_rules: list[str],
    source_evidence_blocks: list[str],
    upstream_heading: str | None = None,
    upstream_evidence_blocks: list[str] | None = None,
    extra_sections_after_ledger: list[str] | None = None,
    snapshot_before_method: bool = True,
) -> str:
    sections = [render_reasoning_unit_ledger(ledger_heading, reasoning_units, context=context)]
    sections.extend(extra_sections_after_ledger or [])
    sections.append(render_material_grounding_bridge(material_heading, skill_assets, context))
    snapshot_section = render_skill_asset_snapshot(snapshot_heading, skill_assets, snapshot_runtime_use_rules, context)
    method_section = render_method_activation_evidence(method_heading, reasoning_units, context=context)
    sections.extend([snapshot_section, method_section] if snapshot_before_method else [method_section, snapshot_section])
    if upstream_heading:
        sections.append(render_demoted_evidence_pack(upstream_heading, *(upstream_evidence_blocks or [])))
    sections.append(render_source_evidence_pack(source_heading, *source_evidence_blocks))
    return "\n\n".join(sections)


def render_stage_document_opening(
    *,
    stage_display: str,
    stage_slug: str,
    document_suffix: str,
    product_label: str,
    version: str,
    owner: str,
    title_state: str = "deep-compiled",
    status: str = "provisional",
    source_status: str = "mixed",
) -> str:
    return f"""# {stage_display} Output — {stage_slug} ({title_state})

## 1. Document Metadata
- document_name: `{product_label} Phase-1 Trial {stage_display} {document_suffix} {version}`
- stage: `{stage_slug}`
- version: `{version}`
- status: `{status}`
- owner: `{owner}`
- source_status: `{source_status}`"""


def render_traceability_block(stage_key: str) -> str:
    trace = STAGE_TRACEABILITY[stage_key]
    lines = [
        "## 1.1 Traceability Naming and Registry",
        f"- artifact_id: `{trace['artifact_id']}`",
        "- artifact_type:",
        f"  - `{trace['artifact_type']}`",
        *render_labeled_markdown_list_lines("depends_on", trace["depends_on"], fallback="(none)", code=True),
        *render_labeled_markdown_list_lines("feeds", trace["feeds"], fallback="(none)", code=True),
    ]
    lines.extend(
        [
            "- traceability_managed_by:",
            "  - `wff-base-traceability-management`",
            "- trace_binding_note:",
            "  - coarse-grained Phase-1 artifact identity follows docs/governance/artifact-traceability-minimum-rules-v0.1.md",
        ]
    )
    return "\n".join(lines)


def packet_open_truth_gap_items(source_text: str) -> list[str]:
    if not re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE):
        return []
    return flatten_bullets(find_markdown_block(source_text, ["Open Truth Gaps"]), 12)


def first_field_value(block: str, label: str) -> str:
    match = re.search(
        rf"^\s*-\s+{re.escape(label)}[:：]\s*(.+?)\s*$",
        block,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def parse_source_register_entries(text: str) -> list[dict[str, str]]:
    matches = list(re.finditer(r"^###\s+\d+\.\s+`([^`]+)`\s*$", text, flags=re.MULTILINE))
    entries: list[dict[str, str]] = []
    for idx, match in enumerate(matches):
        path = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end]
        entries.append(
            {
                "source": path,
                "why": first_field_value(block, "why included"),
                "role": first_field_value(block, "expected role"),
                "authority": first_field_value(block, "hard rule or reference"),
            }
        )
    return entries


def bundle_reference_files(bundle: str) -> list[Path]:
    bundle_dir = REPO_ROOT / "sources/books/extracted" / bundle
    files: list[Path] = []
    for name in REFERENCE_DOC_PRIORITY:
        path = bundle_dir / name
        if path.exists():
            files.append(path)
    return files


def load_bundle_guidance_summary(bundle: str) -> dict[str, object]:
    files = bundle_reference_files(bundle)
    guidance_path = next((path for path in files if path.name == "stage-guidance-draft.md"), None)
    guidance_text = read_text(guidance_path) if guidance_path else ""
    fallback_text = read_text(files[0]) if files else ""
    goal_block = find_markdown_block(guidance_text, ["Goal"]) if guidance_text else ""
    methods_block = find_markdown_block(guidance_text, ["Recommended methods"]) if guidance_text else ""
    rules_block = find_markdown_block(guidance_text, ["Key decision rules"]) if guidance_text else ""
    mistakes_block = find_markdown_block(guidance_text, ["Common mistakes"]) if guidance_text else ""

    goal_parts = flatten_bullets(goal_block, 2)
    if not goal_parts and fallback_text:
        goal_parts = flatten_bullets(fallback_text, 2)

    return {
        "bundle": bundle,
        "goal": "；".join(goal_parts),
        "recommended_methods": flatten_bullets(methods_block, 4),
        "key_decision_rules": flatten_bullets(rules_block, 4),
        "common_mistakes": flatten_bullets(mistakes_block, 3),
        "reference_files": [str(path.relative_to(REPO_ROOT)) for path in files],
    }


def extract_reasoning_titles(text: str) -> list[str]:
    block = find_named_h2_block(text, ["Reasoning Evidence"])
    if not block:
        return []
    titles: list[str] = []
    for match in re.finditer(r"^###\s+(.+)$", block, flags=re.MULTILINE):
        titles.append(re.sub(r"^\d+(?:\.\d+)?\s+", "", match.group(1)).strip())
    return titles


def load_stage_skill_assets(stage_key: str) -> dict[str, object]:
    paths = STAGE_ASSET_PATHS[stage_key]
    sop_text = read_text(paths["sop"])
    source_cards = read_text(paths["source_cards"])
    source_register = read_text(paths["source_register"]) if paths["source_register"].exists() else ""
    output_template = read_text(paths["output_template"])
    execution_steps = list_items_from_block(find_named_h2_block(sop_text, ["Standard Execution Steps"]))
    checkpoints = list_items_from_block(find_named_h2_block(sop_text, ["Process Checkpoints"]))
    handoff = list_items_from_block(find_named_h2_block(sop_text, ["Handoff Rules"]))
    outputs = list_items_from_block(find_named_h2_block(sop_text, ["Output Generation Rules"]))
    bundles = list_items_from_block(find_named_h2_block(source_cards, ["Required Source Bundles"]))
    methods = list_items_from_block(find_named_h2_block(source_cards, ["Required Method Assets"]))
    use_rules = list_items_from_block(find_named_h2_block(source_cards, ["Current Use Rule"]))
    reasoning_titles = extract_reasoning_titles(output_template)
    source_register_entries = parse_source_register_entries(source_register)
    bundle_guidance = [load_bundle_guidance_summary(bundle) for bundle in bundles]
    bundle_reference_files = [
        reference
        for item in bundle_guidance
        for reference in item["reference_files"]
    ]
    return {
        "execution_steps": execution_steps,
        "checkpoints": checkpoints,
        "handoff": handoff,
        "outputs": outputs,
        "bundles": bundles,
        "methods": methods,
        "use_rules": use_rules,
        "reasoning_titles": reasoning_titles,
        "source_register_entries": source_register_entries,
        "bundle_guidance": bundle_guidance,
        "bundle_reference_files": bundle_reference_files,
    }


def bullet_lines(items: list[str], indent: str = "") -> str:
    if not items:
        return f"{indent}- (none)"
    normalized_items = [
        item.replace(
            "When ambiguity exists about the core need, compare at least 2 plausible need framings and select one with rationale",
            "When ambiguity exists about the core need, compare at least 2 plausible need framings and select one with rationale",
        )
        for item in items
    ]
    return "\n".join(f"{indent}- `{item}`" for item in normalized_items)


def skill_asset_sanitizer_context(context: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(context, dict):
        return None
    return source_semantic_guard_context(context)


def sanitized_bullet_lines(
    items: list[str],
    *,
    indent: str = "",
    context: dict[str, object] | None = None,
) -> str:
    sanitizer_context = skill_asset_sanitizer_context(context)
    sanitized_items = [
        str(sanitize_domain_default_truth(item, context=sanitizer_context)).strip()
        for item in items
        if str(item).strip()
    ]
    return bullet_lines(sanitized_items, indent=indent)


def render_skill_asset_snapshot(
    heading: str,
    skill_assets: dict[str, object],
    runtime_use_rules: list[str],
    context: dict[str, object] | None = None,
) -> str:
    register_sources = [
        entry["source"]
        for entry in skill_assets["source_register_entries"][:8]
        if isinstance(entry, dict) and entry.get("source")
    ]
    return f"""{heading}
- sop_execution_steps_compiled:
{sanitized_bullet_lines(skill_assets["execution_steps"], indent="  ", context=context)}
- sop_checkpoints_compiled:
{sanitized_bullet_lines(skill_assets["checkpoints"], indent="  ", context=context)}
- sop_handoff_obligations_compiled:
{sanitized_bullet_lines(skill_assets["handoff"], indent="  ", context=context)}
- sop_output_obligations_compiled:
{sanitized_bullet_lines(skill_assets["outputs"], indent="  ", context=context)}
- source_bundles_loaded:
{sanitized_bullet_lines(skill_assets["bundles"], indent="  ", context=context)}
- required_method_assets_materially_applied:
{sanitized_bullet_lines(skill_assets["methods"], indent="  ", context=context)}
- current_use_rules_compiled:
{sanitized_bullet_lines(skill_assets["use_rules"], indent="  ", context=context)}
- reasoning_template_obligations_compiled:
{sanitized_bullet_lines(skill_assets["reasoning_titles"], indent="  ", context=context)}
- source_register_entries_loaded:
{sanitized_bullet_lines(register_sources, indent="  ", context=context)}
- bundle_reference_files_loaded:
{sanitized_bullet_lines(skill_assets["bundle_reference_files"], indent="  ", context=context)}
- runtime_use_rules_respected:
{sanitized_bullet_lines(runtime_use_rules, indent="  ", context=context)}"""


def render_material_grounding_bridge(
    heading: str,
    skill_assets: dict[str, object],
    context: dict[str, object] | None = None,
) -> str:
    register_authorities = [
        f"{entry['source']}: {entry['role'] or entry['authority'] or entry['why']}"
        for entry in skill_assets["source_register_entries"][:8]
        if isinstance(entry, dict) and entry.get("source")
    ]
    bundle_goals = [
        f"{item['bundle']}: {item['goal']}"
        for item in skill_assets["bundle_guidance"]
        if isinstance(item, dict) and item.get("goal")
    ]
    material_rules = [
        f"{item['bundle']}: {rule}"
        for item in skill_assets["bundle_guidance"]
        if isinstance(item, dict)
        for rule in item.get("key_decision_rules", [])[:2]
    ]
    material_antipatterns = [
        f"{item['bundle']}: {rule}"
        for item in skill_assets["bundle_guidance"]
        if isinstance(item, dict)
        for rule in item.get("common_mistakes", [])[:1]
    ]
    return f"""{heading}
- source_register_authorities:
{sanitized_bullet_lines(register_authorities, indent="  ", context=context)}
- bundle_goals_loaded_from_reference_docs:
{sanitized_bullet_lines(bundle_goals, indent="  ", context=context)}
- material_decision_rules:
{sanitized_bullet_lines(material_rules, indent="  ", context=context)}
- material_antipatterns_to_hold:
{sanitized_bullet_lines(material_antipatterns, indent="  ", context=context)}"""


def render_named_field(
    label: str,
    value: str | list[str],
    *,
    context: dict[str, object] | None = None,
) -> str:
    sanitizer_context = skill_asset_sanitizer_context(context)
    if isinstance(value, list):
        lines = [f"- {label}:"]
        for item in value:
            rendered = (
                str(sanitize_domain_default_truth(item, context=sanitizer_context)).strip()
                if sanitizer_context
                else str(item).strip()
            )
            lines.append(f"  - {rendered}")
        return "\n".join(lines)
    rendered = (
        str(sanitize_domain_default_truth(value, context=sanitizer_context)).strip()
        if sanitizer_context
        else str(value).strip()
    )
    return f"- {label}: `{rendered}`"


def render_reasoning_unit_ledger(
    heading: str,
    units: list[dict[str, str | list[str]]],
    *,
    context: dict[str, object] | None = None,
) -> str:
    field_order = (
        "artifact_unit",
        "loop_round_state",
        "weakness_trigger",
        "method_family",
        "method_assets",
        "reasoning_operator",
        "material_grounding",
        "alternatives_compared",
        "tradeoff_or_tension",
        "decision_effect",
        "evidence_classification",
        "evidence_state",
        "remaining_unknown",
        "downstream_handoff",
        "freeze_rationale",
    )
    lines = [heading]
    for idx, unit in enumerate(units, start=1):
        title = str(unit["title"])
        lines.extend(["", f"### Reasoning Unit {idx}: {title}"])
        for field in field_order:
            if field in unit:
                lines.append(render_named_field(field, unit[field], context=context))
    return "\n".join(lines)


def material_grounding_lines(skill_assets: dict[str, object], limit: int = 4) -> list[str]:
    lines: list[str] = []
    for item in skill_assets["bundle_guidance"]:
        if not isinstance(item, dict):
            continue
        bundle = str(item.get("bundle", "source"))
        for rule in item.get("key_decision_rules", [])[:1]:
            lines.append(f"{bundle}: {rule}")
        if not item.get("key_decision_rules") and item.get("goal"):
            lines.append(f"{bundle}: {item['goal']}")
        if len(lines) >= limit:
            break
    return lines[:limit]


def attach_material_grounding_to_reasoning_units(
    units: list[dict[str, object]],
    material_grounding: list[str],
) -> list[dict[str, object]]:
    return [{**unit, "material_grounding": list(material_grounding)} for unit in units]


def build_reasoning_unit(
    title: str,
    artifact_unit: str,
    loop_round_state: str,
    weakness_trigger: str,
    method: tuple[str, list[str], str],
    comparison: tuple[list[str], str, str],
    evidence: tuple[str, str, str],
    maturity: tuple[str, str, str, str],
) -> dict[str, object]:
    method_family, method_assets, reasoning_operator = method
    alternatives_compared, tradeoff_or_tension, decision_effect = comparison
    observed, interpreted, decision = evidence
    evidence_state, remaining_unknown, downstream_handoff, freeze_rationale = maturity
    return dict(
        title=title,
        artifact_unit=artifact_unit,
        loop_round_state=loop_round_state,
        weakness_trigger=weakness_trigger,
        method_family=method_family,
        method_assets=method_assets,
        reasoning_operator=reasoning_operator,
        alternatives_compared=alternatives_compared,
        tradeoff_or_tension=tradeoff_or_tension,
        decision_effect=decision_effect,
        evidence_classification=[
            f"observed fact: {observed}",
            f"interpreted pattern: {interpreted}",
            f"decision: {decision}",
        ],
        evidence_state=evidence_state,
        remaining_unknown=remaining_unknown,
        downstream_handoff=downstream_handoff,
        freeze_rationale=freeze_rationale,
    )


def build_material_grounded_reasoning_units(
    units: list[dict[str, object]],
    skill_assets: dict[str, object],
) -> list[dict[str, object]]:
    return attach_material_grounding_to_reasoning_units(units, material_grounding_lines(skill_assets))


def render_method_activation_evidence(
    heading: str,
    units: list[dict[str, str | list[str]]],
    *,
    context: dict[str, object] | None = None,
) -> str:
    methods = activated_method_families(units)
    operators = activated_operator_texts(units)
    if not methods:
        methods = unique_preserve_order(
            [str(unit.get("method_family", "")).strip() for unit in units if str(unit.get("method_family", "")).strip()]
        )
    if not operators:
        operators = unique_preserve_order(
            [str(unit.get("reasoning_operator", "")).strip() for unit in units if str(unit.get("reasoning_operator", "")).strip()]
        )
    return f"""{heading}
- activated_method_families:
{sanitized_bullet_lines(methods, indent="  ", context=context)}
- activated_reasoning_operators:
{sanitized_bullet_lines(operators, indent="  ", context=context)}"""


def render_maturity_confidence_section(
    heading: str,
    *,
    document_delivery_state: str,
    evidence_confidence_state: str,
    safe_start_scope: list[str],
    blocked_commitments: list[str],
    rows: list[dict[str, str]],
) -> str:
    lines = [
        heading,
        "- document_delivery_state:",
        f"  - `{document_delivery_state}`",
        "- evidence_confidence_state:",
        f"  - `{evidence_confidence_state}`",
        "- safe_start_scope:",
    ]
    lines.extend(f"  - {item}" for item in safe_start_scope)
    lines.append("- blocked_commitments:")
    lines.extend(f"  - {item}" for item in blocked_commitments)
    lines.extend(
        [
            "",
            "| subject | delivery_readiness_state | evidence_confidence_state | current_basis | blocker_to_next_delivery_state | blocker_to_next_evidence_state | safe_downstream_action | forbidden_assumptions |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
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


def find_h1_block(text: str, heading_pattern: str) -> str:
    match = re.search(
        rf"^#\s+{heading_pattern}.*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return source_packet_evidence_block(text, heading_pattern)
    start = match.start()
    tail = text[start:]
    next_h1 = re.search(r"^#\s+", tail[1:], flags=re.MULTILINE)
    end = next_h1.start() + 1 if next_h1 else len(tail)
    return tail[:end].strip()


def write(path: Path, content: str, locale: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = normalize_domain_terms(content).rstrip() + "\n"
    normalized_locale = resolve_output_locale(locale)
    if normalized_locale == "zh-CN":
        text = "\n".join(render_primary_locale_lines(text.splitlines(), path.name, normalized_locale)).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")


def write_json_artifact(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_domain_terms(text: str) -> str:
    return str(sanitize_domain_default_truth(text, context=source_semantic_guard_context(text=text)))


def _label_variants(label: str) -> list[str]:
    cleaned = str(label or '').strip().strip('`')
    if not cleaned:
        return []
    variants = [cleaned]
    outer = re.sub(r'\([^)]*\)', ' ', cleaned).strip(' /-')
    if outer:
        variants.append(re.sub(r'\s+', ' ', outer).strip())
    variants.extend(inner.strip() for inner in re.findall(r'\(([^)]+)\)', cleaned) if inner.strip())
    return unique_preserve_order(variants)


def _label_match_keys(label: str) -> set[str]:
    keys: set[str] = set()
    for value in _label_variants(label):
        normalized = _normalized_label_key(value)
        if normalized:
            keys.add(normalized)
        token = slug_token(value)
        if token != "item":
            keys.add(f"slug:{token}")
    return keys


def _token_candidate_values(value: str) -> list[str]:
    cleaned = str(value or "").strip().strip("`")
    if not cleaned:
        return []
    candidates = [part.strip(" `") for part in re.split(r"[,/;+]|->", cleaned) if part.strip(" `")]
    candidates.extend(_label_variants(cleaned))
    candidates.append(cleaned)
    return unique_preserve_order(candidates)


def stable_ascii_token(
    label: str,
    *,
    fallback_values: list[str] | None = None,
    prefix: str = "item",
    index: int | None = None,
) -> str:
    for value in [label, *(fallback_values or [])]:
        for candidate in _token_candidate_values(value):
            token = slug_token(candidate)
            if token and token not in {"item", prefix}:
                return token
    return f"{prefix}_{index + 1}" if index is not None else prefix


def source_semantic_token_hits(context: dict[str, object]) -> list[str]:
    blob = _source_semantic_blob(context)
    hits: list[str] = []
    for token, pattern in SEMANTIC_TOKEN_PATTERNS:
        if re.search(pattern, blob, flags=re.IGNORECASE):
            hits.append(token)
    return unique_preserve_order(hits)


def unique_ascii_token(
    label: str,
    *,
    fallback_values: list[str] | None = None,
    prefix: str = "item",
    index: int | None = None,
    existing: set[str] | None = None,
) -> str:
    token = stable_ascii_token(label, fallback_values=fallback_values, prefix=prefix, index=index)
    if existing is None:
        return token
    deduped = token
    suffix = 2
    while deduped in existing:
        deduped = f"{token}_{suffix}"
        suffix += 1
    existing.add(deduped)
    return deduped


def _split_reference_phrases(value: str) -> list[str]:
    cleaned = re.sub(r'`', '', str(value or ''))
    if not cleaned:
        return []
    generic_phrases = {
        'source workflow enters',
        'depends on prior module output',
        'source-defined workflow input',
        'source-defined workflow output',
        'source-defined effect',
        'source-defined output',
        'continue',
        'review',
    }
    phrases: list[str] = []
    for chunk in re.split(r'->|[;,/]|(?:\bwith\b)|(?:\band\b)', cleaned, flags=re.IGNORECASE):
        candidate = re.sub(r'\s+', ' ', chunk).strip(' `.-')
        lowered = candidate.lower()
        if not candidate or lowered in generic_phrases or len(candidate) > 80:
            continue
        phrases.append(candidate)
    return unique_preserve_order(phrases)


def _text_contains_alias(text: str, alias: str) -> bool:
    body = str(text or '').lower()
    needle = str(alias or '').strip().lower()
    if not needle:
        return False
    if re.search(r'[a-z0-9]', needle):
        return re.search(rf'(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])', body) is not None
    return needle in body


def _find_alias_position(text: str, alias: str) -> int | None:
    body = str(text or '').lower()
    needle = str(alias or '').strip().lower()
    if not needle:
        return None
    if re.search(r'[a-z0-9]', needle):
        match = re.search(rf'(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])', body)
        return match.start() if match else None
    position = body.find(needle)
    return position if position >= 0 else None


def _role_aliases(role: str) -> list[str]:
    aliases = _label_variants(role)
    lowered = ' '.join(alias.lower() for alias in aliases)
    if 'veterinarian' in lowered and 'vet' not in {alias.lower() for alias in aliases}:
        aliases.append('vet')
    if 'receptionist' in lowered:
        aliases.extend(['front desk', 'frontdesk'])
    if 'administrator' in lowered or re.search(r'\badmin\b', lowered):
        aliases.append('admin')
    return unique_preserve_order(aliases)


def _module_row_for_surface(surface: str, module_rows: list[dict[str, str]]) -> dict[str, str] | None:
    surface_keys = _label_match_keys(surface)
    for row in module_rows:
        module_name = str(row.get('module', '')).strip()
        if not module_name:
            continue
        module_keys = _label_match_keys(module_name)
        if surface_keys & module_keys:
            return row
    return None


def _surface_reference_phrases(surface: str, module_row: dict[str, str] | None) -> list[str]:
    phrases = list(_label_variants(surface))
    if module_row:
        for key in ('core_objects', 'input', 'output', 'responsibility'):
            phrases.extend(_split_reference_phrases(str(module_row.get(key, ''))))
    return unique_preserve_order(phrases)


def _infer_primary_role_from_line(line: str, roles: list[str]) -> str | None:
    stripped = re.sub(r'^\s*(?:[-*]|\d+[.)])\s*', '', str(line or ''))
    best_match: tuple[int, int, str] | None = None
    for role_index, role in enumerate(roles):
        positions = [
            position
            for alias in _role_aliases(role)
            if (position := _find_alias_position(stripped, alias)) is not None
        ]
        if not positions:
            continue
        candidate = (min(positions), role_index, role)
        if best_match is None or candidate < best_match:
            best_match = candidate
    return best_match[2] if best_match else None


def _score_surface_relevance(line: str, reference_phrases: list[str], surface_aliases: set[str]) -> int:
    relevance = 0
    for phrase in reference_phrases[:12]:
        if _text_contains_alias(line, phrase):
            relevance += 4 if phrase in surface_aliases else 2
    return relevance


def _accumulate_surface_actor_scores(
    score_by_role: dict[str, int],
    lines: list[str],
    roles: list[str],
    reference_phrases: list[str],
    surface_aliases: set[str],
) -> None:
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        relevance = _score_surface_relevance(line, reference_phrases, surface_aliases)
        if relevance <= 0:
            continue
        primary_role = _infer_primary_role_from_line(line, roles)
        if primary_role:
            score_by_role[primary_role] += relevance
            continue
        mentioned_roles = [
            role
            for role in roles
            if any(_text_contains_alias(line, alias) for alias in _role_aliases(role))
        ]
        if len(mentioned_roles) == 1:
            score_by_role[mentioned_roles[0]] += relevance


def infer_surface_primary_actor(surface: str, context: dict[str, object]) -> str:
    roles = [role_label(row) for row in context.get('roles', []) if role_label(row)]
    if not roles:
        return 'primary operator'
    module_row = _module_row_for_surface(surface, context.get('modules', []))
    if module_row and str(module_row.get("primary_actor", "")).strip():
        return str(module_row.get("primary_actor", "")).strip()
    reference_phrases = _surface_reference_phrases(surface, module_row)
    score_by_role = {role: 0 for role in roles}
    role_order = {role: index for index, role in enumerate(roles)}
    surface_aliases = set(_label_variants(surface))
    flow_step_lines = [
        str(step).strip()
        for flow in context.get('flows', [])
        for step in flow.get('steps', [])
        if str(step).strip()
    ]
    _accumulate_surface_actor_scores(score_by_role, flow_step_lines, roles, reference_phrases, surface_aliases)
    if not any(score_by_role.values()):
        source_text = str(context.get('source_text', ''))
        _accumulate_surface_actor_scores(
            score_by_role,
            source_text.splitlines(),
            roles,
            reference_phrases,
            surface_aliases,
        )
    scored = [
        (score, -role_order[role], role)
        for role, score in score_by_role.items()
        if score > 0
    ]
    if scored:
        return max(scored)[2]
    return roles[0]


def signal_phrase(values: list[str], fallback: str, *, limit: int = 2) -> str:
    picked = [compact_signal_line(value) for value in values if compact_signal_line(value)]
    if not picked:
        return fallback
    return "; ".join(picked[:limit])


def build_business_world_model(
    source_text: str,
    *,
    product_source_direct_driver: dict[str, object] | None = None,
) -> dict[str, object]:
    context = extract_domain_context(source_text)
    direct_driver = product_source_direct_driver or build_product_source_direct_driver(source_text, context=context)
    segments = [str(item).strip() for item in context.get("segments", []) if str(item).strip()]
    module_rows = [row for row in context.get("modules", []) if isinstance(row, dict)]
    flow_rows = [row for row in context.get("flows", []) if isinstance(row, dict)]
    flow_summary = " -> ".join(
        str(row.get("module", "")).strip() for row in module_rows if str(row.get("module", "")).strip()
    ) or " -> ".join(
        str(row.get("name", "")).strip() for row in flow_rows if str(row.get("name", "")).strip()
    ) or "source-defined workflow"
    domain_posture = infer_source_semantic_posture(context, text=source_text)
    return compile_business_world_truth_spine(
        {
            "domain_posture": domain_posture,
            "primary_segment": sequence_item_text(segments, 0, "primary operator"),
            "alternative_segments": segments[1:],
            "roles": [str(row.get("Role", "")).strip() for row in context.get("roles", []) if str(row.get("Role", "")).strip()],
            "objectives": list(context.get("objectives", [])),
            "modules": list(context.get("modules", [])),
            "objects": list(context.get("objects", [])),
            "flows": list(context.get("flows", [])),
            "constraints": list(context.get("constraints", [])),
            "nfrs": list(context.get("nfrs", [])),
            "out_of_scope": list(context.get("out_of_scope", [])),
            "business_value_signals": list(context.get("business_value_signals", [])),
            "pressure_signals": list(context.get("pressure_signals", [])),
            "commercial_decision_signals": list(context.get("commercial_decision_signals", [])),
            "user_experience_signals": list(context.get("user_experience_signals", [])),
            "flow_summary": flow_summary,
            "product_source_direct_driver": direct_driver,
        }
    )


def _value_gain_audit(target: str, downstream_value: str, *, output_profile: str = "coverage_rich") -> dict[str, object]:
    return {
        "method": "Thinking Value-Gain",
        "mode": "full-use",
        "output_profile": output_profile,
        "target_module": target,
        "value_axes": ["decision", "action", "evidence", "review", "handoff"],
        "downstream_value": downstream_value,
        "exit_rule": "stop when another round no longer improves decision/action/evidence/review/handoff value",
        "over_design_guard": "do not add structure unless it improves practical value",
    }


def _first_non_empty_text(*values: object, fallback: str = "source-defined truth") -> str:
    for value in values:
        if isinstance(value, list):
            text = "; ".join(str(item).strip() for item in value if str(item).strip())
        elif isinstance(value, dict):
            text = "; ".join(str(item).strip() for item in value.values() if str(item).strip())
        else:
            text = str(value or "").strip()
        if text:
            return text
    return fallback


def _tvg_profile_delivery_copy(output_profile: str) -> dict[str, str]:
    if output_profile == "insight_dense":
        return {
            "boundary": "bounded insight sharpening, not length expansion",
            "delivery_bias": "sharper judgment with less setup",
            "proof_prefix": "Sharp proof",
            "substitute_prefix": "Substitute failure",
            "architecture_prefix": "P2 handoff",
            "decision_gate": "Keep only additions that sharpen a real decision or implementation handoff.",
            "exit_rule": "stop when the next line no longer sharpens a grounded decision",
        }
    if output_profile == "balanced":
        return {
            "boundary": "bounded value-strengthening with compact expression",
            "delivery_bias": "core judgment plus necessary supporting structure",
            "proof_prefix": "Decision-changing proof",
            "substitute_prefix": "Substitute insufficiency",
            "architecture_prefix": "P2 handoff boundary",
            "decision_gate": "Keep additions that improve decision, action, evidence, review, or handoff value without adding synthetic machinery.",
            "exit_rule": "stop when added detail no longer improves proof, handoff, or review value",
        }
    return {
        "boundary": "bounded value-strengthening, not length expansion",
        "delivery_bias": "review and handoff structure with low-value expansion removed",
        "proof_prefix": "Decision-changing proof",
        "substitute_prefix": "Substitute pressure",
        "architecture_prefix": "P2 architecture pressure",
        "decision_gate": "Keep only additions that improve practical decision, action, evidence, review, or handoff value.",
        "exit_rule": "stop when another round no longer improves practical value",
    }


def _tvg_profile_delivery_handoff_items(
    output_profile: str,
    *,
    chosen_name: str,
    primary_substitute: str,
    primary_pain: str,
    proof_target: str,
    continuation_owner: str,
    boundary: str,
    reality_focus: str,
) -> list[dict[str, str]]:
    if output_profile == "insight_dense":
        return [
            {
                "label": "核心判断",
                "text": (
                    f"{chosen_name} is worth carrying forward only if {proof_target} gives {continuation_owner} "
                    f"a clearer continue / revise / pause judgment than {primary_substitute}."
                ),
            }
        ]
    if output_profile == "balanced":
        return [
            {
                "label": "核心判断",
                "text": f"{chosen_name} must beat {primary_substitute} by resolving {primary_pain}.",
            },
            {
                "label": "交付边界",
                "text": f"P2 should preserve {boundary} through {reality_focus} without adding synthetic process machinery.",
            },
            {
                "label": "验收焦点",
                "text": f"{proof_target} must be visible enough for {continuation_owner} to decide continue / revise / pause.",
            },
        ]
    return [
        {
            "label": "决策问题",
            "text": f"Can {continuation_owner} use {proof_target} to decide continue / revise / pause?",
        },
        {
            "label": "判断标准",
            "text": f"The product must make {proof_target} more decision-useful than {primary_substitute}.",
        },
        {
            "label": "替代方案对照",
            "text": f"{primary_substitute} remains insufficient when {primary_pain} still lacks a proof-bearing review path.",
        },
        {
            "label": "采纳风险",
            "text": f"If P2 reduces {boundary} to reporting convenience, it will preserve records but lose the value path.",
        },
        {
            "label": "证据边界",
            "text": f"{proof_target} is required for decision support; exact ROI can remain review-bound until stronger evidence exists.",
        },
        {
            "label": "P2设计含义",
            "text": f"Architecture should carry {reality_focus} through evidence, review, and handoff rather than generic CRUD structure.",
        },
    ]


def build_thinking_value_gain_context(
    business_world_model: dict[str, object],
    *,
    output_profile: str = "coverage_rich",
) -> ThinkingValueGainContext:
    profile_copy = _tvg_profile_delivery_copy(output_profile)
    arena = (
        dict(business_world_model.get("business_exploration_arena", {}))
        if isinstance(business_world_model.get("business_exploration_arena"), dict)
        else {}
    )
    buyer_map = arena.get("buyer_value_proof_map", {}) if isinstance(arena.get("buyer_value_proof_map"), dict) else {}
    substitute_map = (
        arena.get("substitute_and_current_state_map", {})
        if isinstance(arena.get("substitute_and_current_state_map"), dict)
        else {}
    )
    reality_map = arena.get("reality_density_map", {}) if isinstance(arena.get("reality_density_map"), dict) else {}
    candidates = [item for item in arena.get("business_thesis_candidates", []) if isinstance(item, dict)]
    chosen_candidate = candidates[0] if candidates else {}
    primary_substitute = _first_non_empty_text(
        substitute_map.get("substitutes", []),
        fallback="current manual or partial substitute",
    )
    primary_pain = _first_non_empty_text(
        chosen_candidate.get("primary_pain"),
        substitute_map.get("current_state_pressure"),
        fallback="source-defined business pressure",
    )
    proof_target = _first_non_empty_text(
        buyer_map.get("evidence_that_changes_decision"),
        chosen_candidate.get("proof_question"),
        fallback="review-bound proof target",
    )
    continuation_owner = _first_non_empty_text(
        buyer_map.get("continuation_or_approval_owner"),
        chosen_candidate.get("target_user_or_buyer"),
        fallback="decision owner",
    )
    boundary = _first_non_empty_text(
        chosen_candidate.get("likely_first_product_boundary"),
        fallback="source-defined first-version boundary",
    )
    reality_focus = _first_non_empty_text(
        reality_map.get("primary_reality_focus"),
        fallback="source-defined business reality",
    )
    chosen_name = _first_non_empty_text(
        chosen_candidate.get("thesis_name"),
        fallback="source-grounded product thesis",
    )
    return ThinkingValueGainContext(
        output_profile=output_profile,
        profile_copy=profile_copy,
        arena=arena,
        chosen_name=chosen_name,
        primary_substitute=primary_substitute,
        primary_pain=primary_pain,
        proof_target=proof_target,
        continuation_owner=continuation_owner,
        boundary=boundary,
        reality_focus=reality_focus,
        delivery_handoff_items=_tvg_profile_delivery_handoff_items(
            output_profile,
            chosen_name=chosen_name,
            primary_substitute=primary_substitute,
            primary_pain=primary_pain,
            proof_target=proof_target,
            continuation_owner=continuation_owner,
            boundary=boundary,
            reality_focus=reality_focus,
        ),
    )


def build_thinking_value_gain_arena_patch(context: ThinkingValueGainContext) -> dict[str, object]:
    arena = dict(context.arena)
    arena["generation_mode"] = "thinking-value-gain-full-use"
    arena["output_profile"] = context.output_profile
    arena["selected_value_gain_axes"] = ["decision", "action", "evidence", "review", "handoff"]
    arena["value_gain_comparison"] = [
        f"decision: strengthen `{context.chosen_name}` only where it changes {context.continuation_owner}'s continue / revise / pause choice",
        f"evidence: require proof such as {context.proof_target} before claiming the business case is stronger",
        f"handoff: carry {context.reality_focus} and {context.boundary} into P2 instead of adding ornamental analysis",
    ]
    arena["positive_value_exit"] = (
        "Stop TVG expansion when the next round no longer improves decision/action/evidence/review/handoff value "
        "or when added detail cannot be traced to source-grounded P1 truth."
    )
    arena["value_gain_audit"] = _value_gain_audit(
        "Business Exploration Arena",
        "stronger thesis comparison, substitute pressure, buyer/operator value, and continuation proof before PRD freeze",
        output_profile=context.output_profile,
    )
    return arena


def build_thinking_value_gain_commercial_argument_patch(
    original_draft: object,
    context: ThinkingValueGainContext,
) -> dict[str, object]:
    draft = dict(original_draft) if isinstance(original_draft, dict) else {}
    profile_copy = context.profile_copy
    draft["generation_mode"] = "thinking-value-gain-full-use"
    draft["output_profile"] = context.output_profile
    draft["delivery_bias"] = profile_copy["delivery_bias"]
    draft["delivery_handoff_items"] = context.delivery_handoff_items
    draft["truth_state"] = "source-grounded-value-gain-strengthened"
    draft["quality_state"] = "source-grounded-value-gain-strengthened"
    draft["argument_narrative"] = (
        f"{context.chosen_name} deserves P1 commitment because {context.primary_pain}. "
        f"The current substitute pressure is {context.primary_substitute}; the product must beat it by making {context.proof_target} visible enough "
        f"for {context.continuation_owner} to choose continue / revise / pause, not merely by producing a cleaner document or dashboard. "
        f"The value-gain boundary is {context.boundary}: P2 should preserve the proof-bearing action, evidence, review, and handoff path "
        f"that supports {context.reality_focus}, while rejecting extra structure that does not change a real decision or implementation handoff."
    )
    draft["why_substitute_is_not_enough"] = (
        f"{profile_copy['substitute_prefix']}: {context.primary_substitute} is not enough because it can leave the buyer/operator with signals or records but without the proof chain "
        f"needed to decide continue / revise / pause and to hand P2 a designable operating boundary."
    )
    draft["proof_that_changes_decision"] = (
        f"{profile_copy['proof_prefix']}: {context.proof_target}; it must be explicit enough for {context.continuation_owner} to make a continue / revise / pause investment decision."
    )
    draft["directional_proof_when_exact_roi_missing"] = (
        "Before exact ROI exists, directional evidence is acceptable only when it changes a continue / revise / pause decision, "
        "exposes the weakest substitute assumption, and gives P2 a concrete architecture handoff."
    )
    draft["architecture_pressure"] = (
        f"{profile_copy['architecture_prefix']}: P2 must preserve the source-grounded value path from {context.boundary} through evidence, review, and handoff; "
        "do not collapse it into reporting convenience or generic CRUD structure."
    )
    draft["value_gain_decision_gate"] = profile_copy["decision_gate"]
    draft["value_gain_audit"] = _value_gain_audit(
        "Commercial Argument Draft",
        "clearer why-now, why-this-not-substitutes, proof-that-changes-decision, and architecture pressure",
        output_profile=context.output_profile,
    )
    return draft


def build_thinking_value_gain_chosen_thesis_patch(
    original_thesis: object,
    *,
    context: ThinkingValueGainContext,
    arena: dict[str, object],
    draft: dict[str, object],
) -> dict[str, object]:
    thesis = dict(original_thesis) if isinstance(original_thesis, dict) else {}
    thesis["generation_mode"] = "thinking-value-gain-full-use"
    thesis["output_profile"] = context.output_profile
    thesis["delivery_bias"] = context.profile_copy["delivery_bias"]
    thesis["delivery_handoff_items"] = context.delivery_handoff_items
    thesis["truth_state"] = "source-grounded-value-gain-strengthened"
    thesis["business_argument"] = draft["argument_narrative"]
    thesis["proof_target"] = draft["proof_that_changes_decision"]
    thesis["product_boundary_implication"] = draft["architecture_pressure"]
    thesis["value_gain_handoff"] = (
        "P2 and the business_value_signal_registry must consume this thesis as a source-grounded value path: "
        "substitute pressure -> proof target -> continue / revise / pause decision -> implementation boundary."
    )
    thesis["anti_over_design_exit"] = arena["positive_value_exit"]
    thesis["value_gain_audit"] = _value_gain_audit(
        "Chosen Business Thesis",
        "P2 handoff receives explicit business value pressure, proof target, and anti-demo boundary",
        output_profile=context.output_profile,
    )
    return thesis


def build_thinking_value_gain_release_truth_patch(
    original_release_truth: object,
    context: ThinkingValueGainContext,
) -> dict[str, object]:
    release_truth = dict(original_release_truth) if isinstance(original_release_truth, dict) else {}
    release_truth["thinking_value_gain_mode"] = "full-use"
    release_truth["thinking_value_gain_output_profile"] = context.output_profile
    release_truth["thinking_value_gain_exit"] = "positive value gain only; no ornamental expansion"
    return release_truth


def apply_thinking_value_gain_full_use(
    business_world_model: dict[str, object],
    *,
    output_profile: str = "coverage_rich",
) -> dict[str, object]:
    context = build_thinking_value_gain_context(business_world_model, output_profile=output_profile)
    model = dict(business_world_model)
    model["thinking_value_gain"] = {
        "method": "Thinking Value-Gain",
        "mode": "full-use",
        "output_profile": output_profile,
        "scope": "major Phase-1 artifact units",
        "boundary": context.profile_copy["boundary"],
        "exit_rule": context.profile_copy["exit_rule"],
    }

    arena = build_thinking_value_gain_arena_patch(context)
    model["business_exploration_arena"] = arena

    draft = build_thinking_value_gain_commercial_argument_patch(
        model.get("commercial_argument_draft", {}),
        context,
    )
    model["commercial_argument_draft"] = draft

    model["chosen_business_thesis"] = build_thinking_value_gain_chosen_thesis_patch(
        model.get("chosen_business_thesis", {}),
        context=context,
        arena=arena,
        draft=draft,
    )

    model["business_release_truth_pack"] = build_thinking_value_gain_release_truth_patch(
        model.get("business_release_truth_pack", {}),
        context,
    )
    return model

def _render_markdown_value(value: object) -> str:
    if isinstance(value, list):
        return "; ".join(_render_markdown_value(item) for item in value if str(item).strip())
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_render_markdown_value(item)}" for key, item in value.items() if str(item).strip())
    return str(value or "").strip()


def render_business_exploration_arena_markdown(arena: dict[str, object]) -> str:
    candidates = [item for item in arena.get("business_thesis_candidates", []) if isinstance(item, dict)]
    substitute_map = arena.get("substitute_and_current_state_map", {})
    buyer_map = arena.get("buyer_value_proof_map", {})
    reality_map = arena.get("reality_density_map", {})
    exit_questions = arena.get("arena_exit_questions", [])
    lines = [
        "# Business Exploration Arena",
        "",
        "## Business Thesis Candidates",
    ]
    for candidate in candidates:
        lines.extend(
            [
                f"- candidate_id: `{candidate.get('candidate_id', '')}`",
                f"  - thesis_name: {_render_markdown_value(candidate.get('thesis_name', ''))}",
                f"  - target_user_or_buyer: {_render_markdown_value(candidate.get('target_user_or_buyer', ''))}",
                f"  - primary_pain: {_render_markdown_value(candidate.get('primary_pain', ''))}",
                f"  - value_mechanism: {_render_markdown_value(candidate.get('value_mechanism', ''))}",
                f"  - likely_first_product_boundary: {_render_markdown_value(candidate.get('likely_first_product_boundary', ''))}",
                f"  - proof_question: {_render_markdown_value(candidate.get('proof_question', ''))}",
            ]
        )
    lines.extend(["", "## Substitute And Current State"])
    if isinstance(substitute_map, dict):
        for key, value in substitute_map.items():
            lines.append(f"- {key}: {_render_markdown_value(value)}")
    lines.extend(["", "## Buyer Value Proof Map"])
    if isinstance(buyer_map, dict):
        for key, value in buyer_map.items():
            lines.append(f"- {key}: {_render_markdown_value(value)}")
    lines.extend(["", "## Reality Density Map"])
    if isinstance(reality_map, dict):
        for key, value in reality_map.items():
            lines.append(f"- {key}: {_render_markdown_value(value)}")
    lines.extend(["", "## Arena Exit Questions"])
    for question in exit_questions if isinstance(exit_questions, list) else []:
        lines.append(f"- {_render_markdown_value(question)}")
    if "value_gain_audit" in arena:
        lines.extend(["", "## Thinking Value-Gain Audit", f"- {_render_markdown_value(arena.get('value_gain_audit'))}"])
    return "\n".join(lines).rstrip() + "\n"


def render_chosen_business_thesis_markdown(thesis: dict[str, object]) -> str:
    lines = ["# Chosen Business Thesis", ""]
    for key in (
        "chosen_thesis",
        "why_this_not_alternatives",
        "current_state_substitute_to_beat",
        "buyer_user_operator_value",
        "proof_target",
        "review_bound_truth",
        "product_boundary_implication",
        "reality_density_focus",
        "delivery_bias",
        "delivery_handoff_items",
        "value_gain_audit",
    ):
        if key in thesis:
            lines.append(f"- {key}: {_render_markdown_value(thesis.get(key))}")
    rejected = thesis.get("rejected_alternatives", [])
    if rejected:
        lines.append(f"- rejected_alternatives: {_render_markdown_value(rejected)}")
    return "\n".join(lines).rstrip() + "\n"


def render_commercial_argument_draft_markdown(draft: dict[str, object]) -> str:
    lines = ["# Commercial Argument Draft", ""]
    for key in (
        "argument_narrative",
        "primary_substitute_pressure",
        "why_substitute_is_not_enough",
        "proof_that_changes_decision",
        "directional_proof_when_exact_roi_missing",
        "value_mechanism",
        "architecture_pressure",
        "delivery_bias",
        "delivery_handoff_items",
        "quality_state",
        "review_bound_truth",
        "source_grounding_notes",
        "value_gain_audit",
    ):
        if key in draft:
            lines.append(f"- {key}: {_render_markdown_value(draft.get(key))}")
    return "\n".join(lines).rstrip() + "\n"


def load_commercial_argument_rewrite(output_dir: Path) -> dict[str, object] | None:
    candidate = output_dir / "commercial-argument-rewrite.json"
    if not candidate.exists():
        return None
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def apply_commercial_argument_rewrite(
    business_world_model: dict[str, object],
    rewrite: dict[str, object] | None,
) -> dict[str, object]:
    if not isinstance(rewrite, dict):
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

    existing_thesis = model.get("chosen_business_thesis", {})
    thesis = dict(existing_thesis) if isinstance(existing_thesis, dict) else {}
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


def render_business_world_model_section(model: dict[str, object]) -> str:
    alternative_set = dict_or_empty(model.get("primary_alternative_set"))
    buyer_chain = dict_or_empty(model.get("buyer_budget_chain"))
    protected_nouns = dict_or_empty(model.get("protected_business_nouns"))
    buyer_spend = str(buyer_chain.get("spend_at_risk", "")).strip()
    buyer_proof = str(buyer_chain.get("proof_artifact_for_continue", "")).strip()
    buyer_trigger = str(buyer_chain.get("decision_trigger", "")).strip()
    buyer_fields = (
        "pain_holder",
        "continuation_owner",
        "spend_at_risk",
        "proof_artifact_for_continue",
        "decision_trigger",
        "current_truth_state",
        "missing_evidence_to_unlock",
    )
    lines = [
        "## 8. Protected Business-World Truth Spine",
        f"- artifact_file: `{PHASE1_BUSINESS_WORLD_MODEL_FILENAME}`",
        f"- artifact_type: `{model.get('artifact_type', 'business_world_model')}`",
        f"- domain_posture: `{model.get('domain_posture', 'generic-workflow')}`",
        f"- status: `{model.get('status', 'provisional')}`",
        "",
        *render_truth_slot_lines("Core Thesis", model.get("core_thesis")),
        "",
        *render_truth_slot_lines("Why Now", model.get("why_now")),
        "",
        "### Primary Alternative Set",
        f"- truth_state: `{alternative_set.get('truth_state', 'review-bound')}`",
        f"- chosen: {alternative_set.get('chosen', REVIEW_BOUND_MISSING)}",
        *render_labeled_markdown_list_lines(
            "options",
            alternative_set.get("options", []),
            fallback=REVIEW_BOUND_MISSING,
        ),
    ]
    lines.extend(
        [
            "",
            *render_truth_slot_lines("Why This, Not That", model.get("why_this_not_that")),
            "",
            *render_truth_slot_lines("Value Mechanism", model.get("value_mechanism")),
            "",
            "### Buyer / Budget / Continuation Chain",
            f"- truth_state: `{buyer_chain.get('truth_state', 'review-bound')}`",
            *(f"- {field}: {buyer_chain.get(field, REVIEW_BOUND_MISSING)}" for field in buyer_fields),
            "",
            "### Protected Business Nouns",
            f"- truth_state: `{protected_nouns.get('truth_state', 'review-bound')}`",
            "- values:",
        ]
    )
    for label, model_key, buyer_value in (
        ("Spend At Risk", "spend_at_risk", buyer_spend),
        ("Proof Artifact For Continue", "proof_artifact_for_continue", buyer_proof),
        ("Decision Trigger", "decision_trigger", buyer_trigger),
    ):
        value = truth_slot_value(model.get(model_key))
        if value and value != buyer_value:
            lines.extend(["", *render_truth_slot_lines(label, model.get(model_key))])
    lines.extend(
        render_labeled_markdown_list_lines(
            "values",
            protected_nouns.get("values", []),
            fallback=REVIEW_BOUND_MISSING,
        )[1:]
    )
    return "\n".join(lines)


def semantic_authoring_spine_from_model(model: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(model, dict):
        return {}
    summary = model.get("product_source_direct_driver_summary", {})
    if not isinstance(summary, dict):
        return {}
    spine = summary.get("semantic_authoring_spine", {})
    return spine if isinstance(spine, dict) else {}


def semantic_authoring_units_by_type(
    model: dict[str, object] | None,
    semantic_type: str,
    *,
    limit: int = 4,
) -> list[dict[str, object]]:
    spine = semantic_authoring_spine_from_model(model)
    units = spine.get("semantic_units", []) if isinstance(spine, dict) else []
    if not isinstance(units, list):
        return []
    return [
        unit
        for unit in units
        if isinstance(unit, dict) and unit.get("semantic_type") == semantic_type
    ][:limit]


def render_semantic_authoring_spine_section(model: dict[str, object] | None) -> str:
    spine = semantic_authoring_spine_from_model(model)
    if not spine:
        return "## Semantic Authoring Spine\n- status: `not-available`"
    lines = [
        "## Semantic Authoring Spine",
        "- artifact_id: `p1-semantic-authoring-spine.v1`",
        "- control_boundary:",
        "  - Workflow preserves stage order and evidence retention.",
        "  - Agentic owns semantic placement before authoring.",
        "  - Evidence retains source excerpt and claim ceiling.",
    ]
    for semantic_type in (
        "state_lifecycle",
        "audit_compliance_constraint",
        "dashboard_review_decision_surface",
        "role_actor_decision_owner",
        "metric_success_signal",
        "open_truth_gap",
        "deferred_out_of_scope",
    ):
        units = semantic_authoring_units_by_type(model, semantic_type, limit=3)
        if not units:
            continue
        lines.append(f"- {semantic_type}:")
        for unit in units:
            excerpt = str(unit.get("source_excerpt", "")).strip()
            target = str(unit.get("placement_target", "")).strip()
            forbidden = str(unit.get("forbidden_flattening", "")).strip()
            lines.append(f"  - placement_target: `{target}`")
            lines.append(f"    source_excerpt: {excerpt}")
            lines.append(f"    forbidden_flattening: {forbidden}")
    return "\n".join(lines)


def render_topology_profile_record(
    model: dict[str, object],
    *,
    inherited: bool,
) -> str:
    profile = dict_or_empty(model.get("topology_profile")) if isinstance(model, dict) else {}
    prefix = "inherited_" if inherited else ""
    field_specs = [
        (f"{prefix}topology_archetype", [profile.get("topology_archetype", "hybrid")], "hybrid", True),
        (
            f"{prefix}topology_rationale",
            [profile.get("topology_rationale", "source-grounded topology rationale pending")],
            "source-grounded topology rationale pending",
            False,
        ),
        (f"{prefix}primary_depth_axes", profile.get("primary_depth_axes", []), REVIEW_BOUND_MISSING, True),
        (f"{prefix}secondary_depth_axes", profile.get("secondary_depth_axes", []), "none", True),
        ("topology_source_artifact", [PHASE1_BUSINESS_WORLD_MODEL_FILENAME], PHASE1_BUSINESS_WORLD_MODEL_FILENAME, True),
        (
            "ordinary_real_world_baseline_definition",
            [profile.get("ordinary_real_world_baseline_definition", "source-grounded baseline definition pending")],
            "source-grounded baseline definition pending",
            False,
        ),
        ("misfit_risk_if_wrong", [profile.get("misfit_risk_if_wrong", "misfit risk pending")], "misfit risk pending", False),
    ]
    field_specs.extend(
        [
            ("reclassification_status", ["unchanged"], "", True),
            (
                "reclassification_rationale",
                [
                    "Stage-02a inherits the Stage-01 topology profile and should only reroute if later structure pressure disproves the current depth model."
                ],
                "",
                False,
            ),
        ]
        if inherited
        else [
            (
                "reclassification_trigger",
                [profile.get("reclassification_trigger", "reroute before freeze if topology pressure flips")],
                "reroute before freeze if topology pressure flips",
                False,
            ),
            (
                "reclassification_trigger_detail",
                ["Re-route only when later rounds prove the current topology profile is no longer the dominant credibility risk."],
                "",
                False,
            ),
        ]
    )
    lines = ["## 2.1 Inherited Topology Profile Record" if inherited else "## 2.1 Topology Profile Record"]
    for label, values, fallback, code in field_specs:
        lines.extend(render_labeled_markdown_list_lines(label, values, fallback=fallback, code=code))
    return "\n".join(lines)


def render_module_matrix_rows(module_rows: list[dict[str, str]]) -> str:
    lines = ["| module | responsibility | input | output | architectural note |", "|---|---|---|---|---|"]
    for row in module_rows:
        lines.append(
            "| {module} | {responsibility} | {input} | {output} | {note} |".format(
                module=row.get("module", "source-defined module"),
                responsibility=row.get("responsibility", "source-defined responsibility"),
                input=row.get("input", "source-defined input"),
                output=row.get("output", "source-defined output"),
                note=row.get("architectural note", row.get("architectural_note", "preserve source continuity")),
            )
        )
    return "\n".join(lines)


def render_object_workflow_rows(context: dict[str, object]) -> str:
    object_rows = context["objects"]
    module_rows = context["modules"]
    profile = source_semantic_profile_from_context(context)
    profile_objects = [str(item).strip() for item in profile.get("core_objects", []) if str(item).strip()]
    last_output = dict_sequence_field_text(module_rows, -1, "output", "")
    closing_object = (
        profile_objects[-1]
        if profile_objects
        else title_case_token(unique_ascii_token(last_output, prefix="closure"))
    )
    lines = ["| workflow step | primary object | secondary object | downstream effect |", "|---|---|---|---|"]
    for idx, module_row in enumerate(module_rows):
        primary = object_rows[idx]["Object"] if idx < len(object_rows) else title_case_token(str(module_row.get("module", "business object")))
        if idx + 1 < len(module_rows):
            next_objects = [item.strip() for item in str(module_rows[idx + 1].get("core_objects", "")).split(",") if item.strip()]
            secondary = next_objects[0] if next_objects else object_rows[idx + 1]["Object"] if idx + 1 < len(object_rows) else closing_object
        else:
            secondary = closing_object
        lines.append(
            "| {step} | {primary} | {secondary} | {effect} |".format(
                step=module_row.get("module", "workflow step"),
                primary=primary,
                secondary=secondary,
                effect=module_row.get("output", module_row.get("responsibility", "source-defined effect")),
            )
        )
    return "\n".join(lines)


def render_screen_navigation_rows(context: dict[str, object]) -> str:
    module_rows = context["modules"]
    object_rows = context["objects"]
    surfaces = context["navigation_surfaces"]
    lines = [
        "| screen/module | primary actor | required information objects | entry conditions | exit actions | downstream dependency |",
        "|---|---|---|---|---|---|",
    ]
    for idx, surface in enumerate(surfaces):
        module_row = _module_row_for_surface(surface, module_rows)
        required_objects = str(module_row.get('core_objects', '')).strip() if module_row else ''
        if not required_objects:
            fallback_object_row = object_rows[idx % len(object_rows)] if object_rows else {}
            required_objects = str(
                fallback_object_row.get('Object')
                or fallback_object_row.get('object')
                or 'Business Object'
            ).strip()
        next_surface = surfaces[idx + 1] if idx + 1 < len(surfaces) else 'review'
        entry_conditions = str(module_row.get('input', '')).strip() if module_row else ''
        exit_action = str(module_row.get('exit_action', '')).strip() if module_row else ''
        downstream_dependency = (
            str(module_row.get('downstream_dependency', '')).strip()
            or str(module_row.get('output', '')).strip()
            if module_row
            else ''
        )
        lines.append(
            "| {surface} | {actor} | {objects} | {entry} | {exit_action} | {downstream} |".format(
                surface=surface,
                actor=infer_surface_primary_actor(surface, context),
                objects=required_objects or 'Business Object',
                entry=entry_conditions or f"source workflow enters `{surface}`",
                exit_action=exit_action or f"continue to `{next_surface}`",
                downstream=downstream_dependency or 'depends on prior module output',
            )
        )
    return "\n".join(lines)


def payload_contract_heading_from_context(context: dict[str, object]) -> str:
    profile = source_semantic_profile_from_context(context)
    primary_object = sequence_item_text(
        [str(item) for item in profile.get("core_objects", []) if str(item).strip()],
        0,
        "Module",
    )
    return f"{primary_object} Interface Payload Contract"


def deferred_seam_heading_from_context(context: dict[str, object]) -> str:
    return "Source-Defined Deferred Capability Seam"


def render_stage02b_domain_boundary_honesty_lines(context: dict[str, object]) -> str:
    constraints = [str(item).strip() for item in context.get("constraints", []) if str(item).strip()]
    nfrs = [str(item).strip() for item in context.get("nfrs", []) if str(item).strip()]
    signals = constraints[:2] + nfrs[:2]
    if not signals:
        return ""
    lines = ["- source boundary honesty:"]
    lines.extend(f"  - {item}" for item in signals[:4])
    lines.append("- value honesty:")
    lines.append("  - do not overstate MVP proof beyond source evidence, review-bound signals, and first-wave scope.")
    return "\n".join(lines)


def render_interface_payload_rows(context: dict[str, object]) -> str:
    module_rows = context["modules"]
    lines = [
        "| payload element | source capability detail preserved | first-wave representation | task/export implication | certainty / note |",
        "|---|---|---|---|---|",
    ]
    token_hits = source_semantic_token_hits(context)
    if token_hits:
        for token in token_hits[:8]:
            label = title_case_token(token)
            lines.append(
                f"| {label} payload | source explicitly mentions {label.lower().replace('_', ' ')} capability or signal | `{token}_value` + `{token}_evidence_ref` + `{token}_confidence_state` | keeps the capability traceable without claiming external proof | source-derived / review-bound until confirmed |"
            )
    seen_tokens: set[str] = set()
    for idx, row in enumerate(module_rows):
        module = str(row.get("module", "module")).strip()
        token = unique_ascii_token(
            module,
            fallback_values=[
                str(row.get("core_objects", "")),
                str(row.get("output", "")),
                str(row.get("responsibility", "")),
            ],
            prefix="module",
            index=idx,
            existing=seen_tokens,
        )
        lines.append(
            "| {module} interface payload | {responsibility} | `{token}_input` + `{token}_output` | carries `{input_value}` into `{output_value}` without manual reconstruction | source-derived from module matrix |".format(
                module=module,
                responsibility=row.get("responsibility", "source capability detail"),
                token=token,
                input_value=row.get("input", "source input"),
                output_value=row.get("output", "source output"),
            )
        )
    return "\n".join(lines)


def render_deferred_seam_rows(context: dict[str, object]) -> str:
    out_of_scope = list(context.get("out_of_scope", []))
    lines = [
        "| future concern | first-wave treatment now | future seam entity/interface | minimum reserved fields or hook | why deferred now |",
        "|---|---|---|---|---|",
    ]
    for token in source_semantic_token_hits(context):
        if token not in {"attribution", "conversion_event", "identity_resolution"}:
            continue
        lines.append(
            f"| {title_case_token(token)} | keep as review-bound seam unless source and validation evidence prove completion | {title_case_token(token)} Seam | `{token}_status` + `{token}_owner` + `{token}_evidence_state` | source mentions the concern but MVP proof remains bounded |"
        )
    if not out_of_scope:
        out_of_scope = ["future source-defined extension"]
    for item in out_of_scope:
        token = slug_token(item)
        lines.append(
            f"| {item} | keep outside MVP commitment but visible in seam ledger | {title_case_token(token)} Seam | `{token}_status` + `{token}_owner` + `{token}_notes` | explicitly deferred in source scope boundary |"
        )
    return "\n".join(lines)


def render_source_feature_rows(context: dict[str, object]) -> str:
    rows: list[str] = [
        "| source feature detail | classification | preserved form in first-wave PRD | why this classification | downstream note |",
        "|---|---|---|---|---|",
    ]
    first_slice_modules = set(context["first_slice_modules"])
    for row in context["modules"]:
        module = str(row.get("module", "module")).strip()
        classification = "first-wave abstraction" if module in first_slice_modules else "later slice"
        preserved = row.get("output", row.get("responsibility", "source-defined output"))
        reason = "protects the shortest workflow loop directly described in source" if classification == "first-wave abstraction" else "valuable but not required for the first loop"
        note = row.get("architectural note", row.get("architectural_note", "preserve module seam"))
        rows.append(f"| {module} | {classification} | {preserved} | {reason} | {note} |")
    for item in context["out_of_scope"]:
        rows.append(
            f"| {item} | explicit out-of-scope | deferred from first-wave contract | source scope boundary already excludes it from MVP | do not silently reintroduce it in downstream design |"
        )
    return "\n".join(rows)


def render_flow_step_lines(flow_rows: list[dict[str, object]]) -> str:
    lines: list[str] = []
    for flow in flow_rows:
        flow_name = str(flow.get("name", "Primary Flow"))
        for idx, step in enumerate(flow.get("steps", []), start=1):
            lines.append(f"- Step {idx}: {step}")
            lines.append(f"- Step {idx} flow context: {flow_name}")
    return "\n".join(lines) if lines else "- Step 1: source-defined workflow step"


def build_persona_chain_rows(
    roles: list[dict[str, str]],
    modules: list[dict[str, str]],
    objectives: list[str],
) -> str:
    rows = ["| role | goal | friction | first-wave responsibility |", "|---|---|---|---|"]
    module_count = max(1, len(modules))
    objective = sequence_item_text(objectives, 0, "support the source-defined product goal")
    for idx, role in enumerate(roles[:4]):
        role_name = str(role.get("Role", "source-defined role")).strip()
        role_description = str(role.get("Description", "")).strip() or "负责 source 中定义的业务环节"
        module = str(modules[idx % module_count].get("module", "workflow step")).strip() if modules else "workflow step"
        rows.append(
            f"| {role_name} | {objective} | {role_description} 需要与 `{module}` 顺畅衔接 | 围绕 `{module}` 维护主链路连续性 |"
        )
    return "\n".join(rows)


def parse_stage03_assumptions(stage_03_text: str) -> list[dict[str, str]]:
    block = find_named_h2_block(stage_03_text, ["Key Assumptions to Validate"])
    if not block:
        return []
    assumptions: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in block.splitlines()[1:]:
        line = raw.rstrip()
        header = re.match(r"^- assumption_(\d+):\s*$", line.strip())
        if header:
            if current:
                assumptions.append(current)
            current = {"id": f"target_{header.group(1)}"}
            continue
        if current is None:
            continue
        value_line = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if value_line and "what_changes_if_" not in value_line.group(1):
            current["assumption"] = value_line.group(1).strip()
            continue
        positive = re.match(r"^\s*-\s*what_changes_if_positive:\s*(.+?)\s*$", line)
        if positive:
            current["positive"] = positive.group(1).strip()
            continue
        negative = re.match(r"^\s*-\s*what_changes_if_negative:\s*(.+?)\s*$", line)
        if negative:
            current["negative"] = negative.group(1).strip()
    if current:
        assumptions.append(current)
    return [item for item in assumptions if item.get("assumption")]


def infer_validation_dimension(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["约束", "tech stack", "auditable", "state", "inventory", "retention", "response time"]):
        return "feasibility"
    if any(token in lowered for token in ["角色", "边界", "primary boundary", "role", "segment"]):
        return "boundary"
    if any(token in lowered for token in ["流程", "界面", "理解", "可执行", "workflow", "handoff"]):
        return "usability"
    if any(token in lowered for token in ["延后项", "future phase", "out-of-scope", "deferred"]):
        return "scope"
    return "scope"


def infer_validation_method_bundle(assumption: str, flow_name: str, primary_segment: str) -> dict[str, str]:
    lowered = assumption.lower()
    if any(token in lowered for token in ["边界", "role", "segment", "首发"]):
        return {
            "method": "role-comparison interview",
            "artifact": "segment comparison sheet",
            "threshold": "主边界在 3 项以上判断标准中领先",
            "why": "chosen; directly tests first-wave boundary fit",
            "fidelity": "comparison + interview",
        }
    if any(token in lowered for token in ["约束", "tech stack", "auditable", "inventory", "retention", "response"]):
        return {
            "method": "architecture walkthrough + constraint review",
            "artifact": "workflow constraint checklist",
            "threshold": "关键约束均能映射到明确设计或架构措施",
            "why": "chosen; constraint fit needs explicit technical review",
            "fidelity": "structured review",
        }
    if any(token in lowered for token in ["流程", "统一流程", "handoff", "可理解", "可执行", "界面", "workflow"]):
        return {
            "method": "clickable walkthrough + task interview",
            "artifact": f"{flow_name} prototype path",
            "threshold": f">=70% 能说清下一步，>=50% 愿意沿 `{flow_name}` 继续执行",
            "why": "chosen; tests comprehension and handoff quality together",
            "fidelity": "clickable",
        }
    return {
        "method": "interview + scenario prompt",
        "artifact": f"{primary_segment} scenario card",
        "threshold": ">=3 位目标用户给出明确正/负向判断",
        "why": "chosen; fastest way to test value-side uncertainty",
        "fidelity": "interview",
    }


def build_stage_04_validation_plan(
    stage_03_text: str,
    *,
    primary_flow_name: str,
    primary_segment: str,
    module_chain: str,
) -> Stage04ValidationPlan:
    stage03_assumptions = parse_stage03_assumptions(stage_03_text)
    if not stage03_assumptions:
        stage03_assumptions = [
            {
                "id": "target_1",
                "assumption": f"`{primary_segment}` 愿意沿着 `{module_chain}` 使用统一流程",
                "positive": "当前切片可直接进入设计深化",
                "negative": "需要回退调整首个切片的入口与范围",
            }
        ]
    validation_targets: list[dict[str, str]] = []
    for item in stage03_assumptions:
        bundle = infer_validation_method_bundle(item["assumption"], primary_flow_name, primary_segment)
        validation_targets.append(
            {
                **item,
                **bundle,
                "dimension": infer_validation_dimension(item["assumption"]),
            }
        )
    method_rows = [
        "| clickable walkthrough + task interview | high | high-speed / medium-cost | medium | chosen for workflow comprehension and handoff assumptions |",
        "| architecture walkthrough + constraint review | medium-high | medium-speed / medium-cost | medium | chosen for constraint-fit assumptions |",
        "| role-comparison interview | medium | high-speed / low-cost | medium | chosen for primary-boundary assumptions |",
    ]
    return Stage04ValidationPlan(
        stage03_assumptions=list(stage03_assumptions),
        validation_targets=validation_targets,
        method_rows=method_rows,
    )


def build_stage_01_source_bundle(
    source_text: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> Stage01SourceBundle:
    snapshot = source_snapshot or build_phase1_source_snapshot(source_text)
    sections = snapshot.sections
    context = snapshot.context
    product_label = snapshot.product_label
    segments = snapshot.segments
    primary_segment = snapshot.primary_segment
    alternative_segments = snapshot.alternative_segments
    objectives = context["objectives"] or ["establish a source-defined operating loop"]
    modules = snapshot.modules
    roles = snapshot.roles
    flows = snapshot.flows
    constraints = context["constraints"] or ["source-defined constraint"]
    nfrs = context["nfrs"] or ["source-defined non-functional requirement"]
    out_of_scope = context["out_of_scope"] or ["source-defined deferred item"]
    flow_summary = snapshot.module_chain
    business_world_model = snapshot.business_world_model
    problem_cluster_lines = "\n".join(
        f"  - {item}" for item in (flatten_bullets(sections.h32, 6) or [f"{primary_segment} 缺少稳定的流程闭环"])
    )
    opportunity_cluster_lines = "\n".join(f"  - {item}" for item in (flatten_bullets(sections.h33, 6) or objectives[:4]))
    deferred_lines = "\n".join(f"  - {item}" for item in out_of_scope[:4])
    open_truth_lines = "\n".join(
        f"- {item}"
        for item in unique_preserve_order(
            [
                f"{flow.get('name', 'source-defined flow')} handoff readiness"
                for flow in flows[:2]
            ]
            + [f"constraint fit: {item}" for item in constraints[:2]]
            + [f"nfr viability: {item}" for item in nfrs[:2]]
        )
    ) or "- source-defined workflow adoption readiness"
    persona_chain_rows = build_persona_chain_rows(roles, modules, objectives)
    return Stage01SourceBundle(
        h21=sections.h21,
        h22=sections.h22,
        h23=sections.h23,
        h24=sections.h24,
        h31=sections.h31,
        h32=sections.h32,
        h33=sections.h33,
        h34=sections.h34,
        first_part=sections.first_part,
        context=context,
        business_world_model=business_world_model,
        product_label=product_label,
        segments=segments,
        primary_segment=primary_segment,
        alternative_segments=alternative_segments,
        objectives=objectives,
        modules=modules,
        roles=roles,
        flows=flows,
        constraints=constraints,
        nfrs=nfrs,
        out_of_scope=out_of_scope,
        flow_summary=flow_summary,
        problem_cluster_lines=problem_cluster_lines,
        opportunity_cluster_lines=opportunity_cluster_lines,
        deferred_lines=deferred_lines,
        open_truth_lines=open_truth_lines,
        persona_chain_rows=persona_chain_rows,
    )


def build_stage_01_reasoning_units(
    *,
    primary_segment: str,
    alternative_segments: list[str],
    segments: list[str],
    flow_summary: str,
    objectives: list[str],
    constraints: list[str],
    out_of_scope: list[str],
    skill_assets: dict[str, object],
) -> list[dict[str, object]]:
    return build_material_grounded_reasoning_units(
        [
            build_reasoning_unit(
                "Primary Boundary Lock", "chosen user boundary", "structured -> reviewed -> freeze",
                "first-wave boundary was still too broad",
                ("segment comparison + first-loop prioritization", ["direct user research posture", "fast user-group segmentation", "explicit alternative comparison for first-wave user choice"], "compare source-defined roles by workflow ownership, continuity visibility, and first-wave validation leverage"),
                ([primary_segment, *alternative_segments[:2]], "boundary breadth vs first-wave clarity", f"locked `{primary_segment}` as the primary boundary for downstream structure analysis"),
                (f"source explicitly lists roles `{', '.join(segments[:3])}`", f"`{primary_segment}` sits closest to the start of `{flow_summary}`", "keep one primary boundary and treat the rest as supporting roles"),
                ("provisional", "real interview evidence for role preference is still pending", f"Stage-02a must organize the panorama around `{primary_segment}` and the `{flow_summary}` chain", "boundary is specific enough to constrain downstream design without pretending validation is complete"),
            ),
            build_reasoning_unit(
                "Problem Mechanism Reframe", "final problem statement", "structured -> refined -> freeze",
                "initial framing risked collapsing into feature inventory",
                ("problem framing before solutioning", ["opportunity framing before solutioning", "problem-mechanism framing, not just symptom listing"], "separate workflow breakdown, handoff friction, and audit gap before discussing modules"),
                (["feature-gap framing", "workflow-breakdown framing"], "shorter feature language vs accurate workflow diagnosis", f"reframed the problem around the missing `{flow_summary}` operating loop"),
                (f"source objectives stress `{objectives[0]}`", f"disconnected `{flow_summary}` steps create manual coordination overhead", "treat auditability and handoff continuity as the core mechanism"),
                ("provisional", "the hardest real-world handoff still needs user verification", "Stage-02a should prioritize workflow structure over isolated screens", "problem mechanism is now specific enough to guide structural analysis"),
            ),
            build_reasoning_unit(
                "Open Truth Discipline", "key open truths", "structured -> reviewed -> freeze",
                "constraints and deferred scope could be silently promoted into assumed facts",
                ("evidence layering + explicit uncertainty retention", ["research execution and insight synthesis", "evidence layering: observed fact vs interpretation vs inference"], "keep NFRs, constraints, and deferred scope visible as review-bound truths"),
                (["hide uncertainties in narrative", "preserve open truths explicitly"], "clean narrative vs honest uncertainty", "preserved operational constraints and out-of-scope items as explicit open truths"),
                (f"source states constraints such as `{constraints[0]}`", f"source excludes `{out_of_scope[0]}` from MVP", "downstream stages must not silently upgrade these unknowns into commitments"),
                ("review-bound", "which open truth becomes the first blocking risk in validation is still unknown", "later stages must preserve these truths in scope and validation sections", "uncertainty is bounded and explicitly recorded"),
            ),
        ],
        skill_assets,
    )


def render_stage_01_boundary_problem_sections(source_bundle: Stage01SourceBundle) -> str:
    return f"""## 2. Chosen User Boundary
- chosen_segment: `{source_bundle.primary_segment}`
- alternatives_considered:
{chr(10).join(f"  - {item}" for item in source_bundle.alternative_segments)}
- why_this_not_that:
  - 当前 source 对该边界给出了最完整的角色职责、流程动作和结果责任，适合作为首波分析主边界。

## 3. Problem Statement
- final_problem_statement:
  - 当前团队缺少一条可重复的 `{source_bundle.flow_summary}` 业务闭环，导致关键业务步骤仍依赖人工衔接和经验判断。
- problem_mechanism:
  - 问题不只是单个页面或模块缺失，而是登记、流转、执行和结算等动作没有被组织成同一条可审计链路。

## 4. Need Framing
- chosen_framing: `workflow continuity + auditable operations`
- rejected:
  - isolated module delivery
  - role-segment sprawl before first-loop validation

## 5. Persona Boundary and Interaction Chain
{source_bundle.persona_chain_rows}

## 6. Structured Problem/Opportunity Recompilation
- top_problem_clusters:
{source_bundle.problem_cluster_lines}
- top_opportunity_clusters:
{source_bundle.opportunity_cluster_lines}

## 7. Key Open Truths
{source_bundle.open_truth_lines}
- deferred scope boundaries:
{source_bundle.deferred_lines}"""


def render_stage_01_document(
    *,
    source_bundle: Stage01SourceBundle,
    reasoning_units: list[dict[str, object]],
    skill_assets: dict[str, object],
    version: str,
    owner: str,
) -> str:
    return f"""{render_stage_document_opening(
    stage_display="Stage-01",
    stage_slug="requirements-user-research",
    document_suffix="User Research",
    product_label=source_bundle.product_label,
    version=version,
    owner=owner,
)}

{render_traceability_block("stage_01")}

{render_topology_profile_record(source_bundle.business_world_model, inherited=False)}

{render_stage_01_boundary_problem_sections(source_bundle)}

{render_business_world_model_section(source_bundle.business_world_model)}

{render_reasoning_unit_ledger("## 9. Minimal Reasoning Unit Ledger", reasoning_units, context=source_bundle.context)}

{render_method_activation_evidence("## 10. Method Activation Evidence", reasoning_units, context=source_bundle.context)}

{render_material_grounding_bridge("## 11. Material Grounding Bridge", skill_assets, source_bundle.context)}

{render_skill_asset_snapshot(
    "## 12. Skill Asset Ingestion Snapshot",
    skill_assets,
    [
        "one user-segmentation method asset was materially activated",
        "one evidence/insight synthesis method asset was materially activated",
        "one problem-framing method asset was materially activated",
        "chosen user boundary, final problem statement, and need framing retain visible method trace",
    ],
    source_bundle.context,
)}

{render_source_evidence_pack(
    "## 13. Source Evidence Pack",
    source_bundle.h21,
    source_bundle.h22,
    source_bundle.h23,
    source_bundle.h24,
    source_bundle.h31,
    source_bundle.h32,
    source_bundle.h33,
    source_bundle.h34,
    source_bundle.first_part,
)}
"""


def build_stage_01(
    source_text: str,
    version: str,
    owner: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> str:
    source_bundle = build_stage_01_source_bundle(source_text, source_snapshot=source_snapshot)
    skill_assets = load_stage_skill_assets("stage_01")
    return render_stage_01_document(
        source_bundle=source_bundle,
        reasoning_units=build_stage_01_reasoning_units(
            primary_segment=source_bundle.primary_segment,
            alternative_segments=source_bundle.alternative_segments,
            segments=source_bundle.segments,
            flow_summary=source_bundle.flow_summary,
            objectives=source_bundle.objectives,
            constraints=source_bundle.constraints,
            out_of_scope=source_bundle.out_of_scope,
            skill_assets=skill_assets,
        ),
        skill_assets=skill_assets,
        version=version,
        owner=owner,
    )


def build_stage_02a_source_bundle(
    source_text: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> Stage02aSourceBundle:
    snapshot = source_snapshot or build_phase1_source_snapshot(source_text)
    sections = snapshot.sections
    context = snapshot.context
    business_world_model = snapshot.business_world_model
    product_label = snapshot.product_label
    segments = snapshot.segments
    primary_segment = snapshot.primary_segment
    modules = snapshot.modules
    objectives = context["objectives"] or ["preserve the shortest source-defined workflow"]
    flows = snapshot.flows
    module_names = snapshot.module_names
    workflow_chain = snapshot.module_chain
    roles = snapshot.roles
    constraints = context["constraints"] or ["source-defined architectural constraint"]
    out_of_scope = context["out_of_scope"] or ["source-defined future item"]
    p0_items = context["p0"] or module_names[:5]
    p1_items = context["p1"] or out_of_scope[:3]
    p2_items = context["p2"] or out_of_scope[:3]
    return Stage02aSourceBundle(
        h23=sections.h23,
        h31=sections.h31,
        h32=sections.h32,
        h33=sections.h33,
        h34=sections.h34,
        h41=sections.h41,
        h43=sections.h43,
        h7p0=sections.h7p0,
        h7p1=sections.h7p1,
        h7p2=sections.h7p2,
        h8=sections.h8,
        h51=sections.h51,
        h52=sections.h52,
        h53=sections.h53,
        h61=sections.h61,
        h62=sections.h62,
        context=context,
        business_world_model=business_world_model,
        product_label=str(product_label),
        segments=list(segments),
        primary_segment=str(primary_segment),
        modules=list(modules),
        objectives=list(objectives),
        flows=list(flows),
        module_names=module_names,
        workflow_chain=workflow_chain,
        roles=list(roles),
        constraints=list(constraints),
        out_of_scope=list(out_of_scope),
        p0_items=list(p0_items),
        p1_items=list(p1_items),
        p2_items=list(p2_items),
    )


def build_stage_02a_structural_mapping_context(source_bundle: Stage02aSourceBundle) -> Stage02aStructuralMappingContext:
    segments = source_bundle.segments
    primary_segment = source_bundle.primary_segment
    modules = source_bundle.modules
    objectives = source_bundle.objectives
    flows = source_bundle.flows
    module_names = source_bundle.module_names
    workflow_chain = source_bundle.workflow_chain
    supporting_role_lines = "\n".join(f"  - {item}" for item in (segments[1:4] or ["secondary collaborator"]))
    problem_cluster_lines = "\n".join(
        f"  - {item}" for item in (flatten_bullets(source_bundle.h32, 4) or [f"{primary_segment} 需要稳定完成 {workflow_chain}"])
    )
    opportunity_cluster_lines = "\n".join(f"  - {item}" for item in (flatten_bullets(source_bundle.h33, 4) or objectives[:3]))
    backbone_lines = "\n".join(f"{idx}. {name}" for idx, name in enumerate(module_names[:8], start=1))
    process_rows = "\n".join(
        f"| main flow | {row.get('module', 'source step')} | {row.get('primary_actor', primary_segment) or primary_segment} | {row.get('input', 'source-defined trigger')} | {row.get('output', 'source output')} | {row.get('responsibility', 'supports workflow continuity')} |"
        for row in modules[:8]
    )
    first_flow = dict_or_empty(flows[0]) if flows else {}
    first_flow_steps = [str(step).strip() for step in first_flow.get("steps", []) if str(step).strip()]
    primary_step_lines = "\n".join(f"  - {step}" for step in first_flow_steps) or "  - source-defined workflow step"
    actor_system_lines = "\n".join(
        f"  - {row.get('module', 'module')} actor=`{row.get('primary_actor', primary_segment) or primary_segment}` / system=`{row.get('responsibility', 'source-defined system behavior')}`"
        for row in modules[:5]
    )
    return Stage02aStructuralMappingContext(
        supporting_role_lines=supporting_role_lines,
        problem_cluster_lines=problem_cluster_lines,
        opportunity_cluster_lines=opportunity_cluster_lines,
        backbone_lines=backbone_lines,
        process_rows=process_rows,
        first_flow_steps=first_flow_steps,
        primary_step_lines=primary_step_lines,
        actor_system_lines=actor_system_lines,
    )


def build_stage_02a_nfr_identification_block(
    *,
    primary_segment: str,
    workflow_chain: str,
    module_names: list[str],
    roles: list[dict[str, str]],
    constraints: list[str],
) -> str:
    first_module = sequence_item_text(module_names, 0, "source module")
    next_module = sequence_item_text(module_names, 1, "next module")
    last_module = sequence_item_text(module_names, -1, "source completion")
    secondary_role = dict_sequence_field_text(roles, 1, "Role", "secondary collaborator")
    first_constraint = sequence_item_text(constraints, 0, "source-defined constraint")
    last_constraint = sequence_item_text(constraints, -1, "source-defined constraint")
    return f"""- nfr_initial_identification:
  - nfr_dimensions_scan:
    - dimension_1:
      - name: reliability
      - relevance: `relevant`
      - information_state: `identified`
      - basis: 主流程 `{workflow_chain}` 必须稳定可复现，否则 {primary_segment} 无法据此持续运营。
      - known_signals: 关键步骤 `{first_module}` 到 `{last_module}` 不能出现隐式状态跳变。
    - dimension_2:
      - name: usability
      - relevance: `relevant`
      - information_state: `identified`
      - basis: 角色 `{primary_segment}` 与 `{secondary_role}` 必须都能读懂模块输入输出并顺畅交接。
      - known_signals: `{first_module}` -> `{next_module}` 的 handoff 不能依赖口头补充。
    - dimension_3:
      - name: security/data-control
      - relevance: `relevant`
      - information_state: `identified`
      - basis: source 已明确提出约束 `{first_constraint}`，说明权限、审计或边界控制不能后补。
      - known_signals: 关键约束必须在主流程前段显式生效，而不是在最后才暴露。
    - dimension_4:
      - name: maintainability
      - relevance: `suspected-relevant`
      - information_state: `suspected`
      - basis: 模块 `{first_module}` 到 `{last_module}` 的对象链必须保留 seam，后续才能安全扩展。
      - known_signals: Stage-02b 需要在对象链、模块契约和延后项之间保持一致。
    - dimension_5:
      - name: performance
      - relevance: `suspected-relevant`
      - information_state: `unknown`
      - basis: source 没有给出完整容量曲线，但当前约束 `{last_constraint}` 说明响应和并发仍需后续确认。
      - known_signals: 仍需确认实际使用峰值、角色并发与页面响应预算。
  - nfr_scan_completeness:
    - dimensions_considered: `5`
    - dimensions_relevant: `3`
    - dimensions_unknown: `1`
    - scan_confidence: `medium`
    - scan_confidence_note: 当前判断基于 source 的模块、流程和约束，后续仍需在 Stage-02b 深化。
  - stage_02b_dependency_note:
    - stage_02b_planned: `yes`
    - if_skipped_impact: Phase-2 将缺质量场景矩阵、domain model、IA direction 与 payload contract，架构边界会被迫重建。
    - minimum_viable_for_phase2: `yes`
    - minimum_viable_note: 当前 scan 足以提醒 Phase-2 哪些 NFR 维度相关，但不足以替代 Stage-02b 的 specification-grade 深化。"""


def build_stage_02a_design_requirements_block(
    *,
    modules: list[dict[str, str]],
    roles: list[dict[str, str]],
    primary_segment: str,
) -> str:
    rows = []
    for idx, module_row in enumerate(modules[:6], start=1):
        role = str(module_row.get("primary_actor", "")).strip() or (roles[(idx - 1) % len(roles)]["Role"] if roles else primary_segment)
        rows.append(
            "| DR-{idx:02d} | {role} | 进入 `{module}` | 在同一界面中完成 `{responsibility}`，并看到 `{output}` | 让 `{input_value}` 与 `{output}` 脱节或只能靠人工补齐 |".format(
                idx=idx,
                role=role,
                module=module_row.get("module", "source-defined module"),
                responsibility=module_row.get("responsibility", "source-defined responsibility"),
                output=module_row.get("output", "source-defined output"),
                input_value=module_row.get("input", "source-defined input"),
            )
        )
    return "\n".join(
        ["| id | persona / role | trigger | required outcome | anti-pattern to avoid |", "|---|---|---|---|---|", *rows]
    )


def build_stage_02a_persona_context_block(
    *,
    primary_segment: str,
    objectives: list[str],
    first_flow_steps: list[str],
    workflow_chain: str,
    modules: list[dict[str, str]],
) -> str:
    day_in_life = sequence_item_text(objectives, 0, f"{primary_segment} 需要稳定推动 {workflow_chain}")
    desired_experience = " -> ".join(first_flow_steps[:4]) if first_flow_steps else workflow_chain
    key_path_blocks: list[str] = []
    for idx, module_row in enumerate(modules[:3], start=1):
        key_path_blocks.extend(
            [
                f"### Key-path Scenario {idx}",
                "- actor_goal:",
                f"  - 在 `{module_row.get('module', 'source-defined module')}` 环节完成 `{module_row.get('responsibility', 'source-defined responsibility')}`。",
                "- implied_design_requirement:",
                f"  - 界面必须把 `{module_row.get('input', 'source input')}` 和 `{module_row.get('output', 'source output')}` 放在同一条可见链路中。",
                "",
            ]
        )
    return f"""### Primary Persona Context Scenario
- archetype:
  - `{primary_segment}`
- day-in-the-life snapshot:
  - {day_in_life}
- desired experience:
  - 希望能沿着 `{desired_experience}` 直接完成主流程，而不是在多个孤立页面之间手工对齐上下文。

{chr(10).join(key_path_blocks).rstrip()}"""


def build_stage_02a_scenario_decomposition_block(
    *,
    flows: list[dict[str, object]],
    primary_segment: str,
) -> str:
    scenario_blocks: list[str] = []
    for idx, flow in enumerate(flows[:3], start=1):
        steps = [str(step).strip() for step in flow.get("steps", []) if str(step).strip()]
        first_step = sequence_item_text(steps, 0, "source-defined trigger step")
        last_step = sequence_item_text(steps, -1, "source-defined completion step")
        scenario_blocks.extend(
            [
                f"### Scenario {idx}: {flow.get('name', f'Flow {idx}')}",
                "- trigger:",
                f"  - {first_step}",
                "- challenge:",
                f"  - 若 `{flow.get('name', f'Flow {idx}')}` 的前后步骤不能顺畅衔接，{primary_segment} 就必须手工重建上下文。",
                "- structure implication:",
                f"  - 该场景的页面、对象和状态必须围绕 `{last_step}` 的完成条件来设计，而不是拆成孤立功能页。",
                "",
            ]
        )
    return "\n".join(scenario_blocks).rstrip() or """### Scenario 1: Source-defined Primary Flow
- trigger:
  - source-defined trigger
- challenge:
  - 若上下文断裂，主流程将退化为人工拼接。
- structure implication:
  - 设计必须围绕源文档的主流程连续性展开。"""


def build_stage_02a_key_scenario_deep_analysis_block(
    *,
    flows: list[dict[str, object]],
    roles: list[dict[str, str]],
    primary_segment: str,
    constraints: list[str],
) -> str:
    deep_dive_blocks: list[str] = []
    deep_dive_labels = ["A", "B", "C"]
    deep_dive_roles = [row.get("Role", primary_segment) for row in roles[:3]] or [primary_segment]
    for idx, flow in enumerate(flows[:3], start=0):
        steps = [str(step).strip() for step in flow.get("steps", []) if str(step).strip()]
        role = deep_dive_roles[idx % len(deep_dive_roles)]
        first_step = sequence_item_text(steps, 0, "source-defined first action")
        main_path = " -> ".join(steps[:5]) if steps else "source-defined flow progression"
        deep_dive_blocks.extend(
            [
                f"### Scenario Deep Dive {deep_dive_labels[idx]}: [{role}] {flow.get('name', f'Flow {idx + 1}')}",
                "- preconditions:",
                f"  - 上游模块已经提供 `{first_step}` 所需的最小输入，且角色边界清晰可用。",
                "- main success path:",
                f"  - {main_path}",
                "- key exception paths:",
                f"  - 若 `{flow.get('name', f'Flow {idx + 1}')}` 中任一步骤缺少输入/状态，系统必须显式暴露阻塞，而不是让角色猜测下一步。",
                f"  - 若约束 `{constraints[idx % len(constraints)]}` 被触发，流程必须停在可审计状态，而不是静默继续。",
                "- success criteria:",
                f"  - `{role}` 能在同一条流程链里完成该场景，而不需要跨模块手工重建对象关系。",
                "- scenario consequence if weak:",
                f"  - `{flow.get('name', f'Flow {idx + 1}')}` 会退化为人为补锅流程，产品难以形成稳定使用习惯。",
                "",
            ]
        )
    return "\n".join(deep_dive_blocks).rstrip()


def build_stage_02a_stakeholder_value_lines(
    *,
    primary_segment: str,
    supporting_role: str,
    review_role: str,
    workflow_chain: str,
    experience_pressure: str,
    value_pressure: str,
    commercial_pressure: str,
    stress_technical: str,
    stress_compliance: str,
    stress_resource: str,
    first_module: str,
    last_module: str,
    flows: list[dict[str, object]],
) -> Stage02aStakeholderValueLines:
    rows = [
        ("primary_boundary", primary_segment, f"complete `{workflow_chain}` without losing {experience_pressure}", "high"),
        ("supporting_role", supporting_role, f"receive clear upstream state and object handoff while preserving {value_pressure}", "medium"),
        ("supporting_role", review_role, f"see auditable results, stable scope boundary, and `{commercial_pressure}`", "medium"),
    ]
    profile_rows = "\n".join(
        f"| {name} | {goal} | keep `{workflow_chain}` traversable | loses continuity if state and object links break | {influence} |"
        for _, name, goal, influence in rows
    )
    adoption_chain_lines = "\n".join(
        f"{idx}. {name} can enter the flow with clear context, preserve {experience_pressure}, and complete the handoff without diluting {value_pressure}"
        for idx, (_, name, _, _) in enumerate(rows, start=1)
    )
    conflict_map_lines = "\n".join(
        [
            f"- `{primary_segment}` wants fast flow execution and less {experience_pressure}, while constraints require `{stress_technical}` to stay explicit",
            f"- supporting roles want shorter paths, while `{stress_compliance}` forces auditable transitions and keeps `{commercial_pressure}` review-bound",
            f"- scope pressure to include `{stress_resource}` conflicts with keeping P0 focused on `{workflow_chain}`",
        ]
    )
    value_loop_lines = "\n".join(
        [
            f"  - actor enters `{first_module}` with the minimum required input and the source-grounded value pressure `{value_pressure}` still visible",
            f"  - workflow advances through `{workflow_chain}` with explicit state and object transitions instead of reintroducing {experience_pressure}",
            f"  - downstream artifacts must preserve `{last_module}` as an explainable closure point for `{commercial_pressure}`",
        ]
    )
    return Stage02aStakeholderValueLines(
        profile_rows=profile_rows,
        adoption_chain_lines=adoption_chain_lines,
        conflict_map_lines=conflict_map_lines,
        value_loop_lines=value_loop_lines,
        chain_line=" -> ".join(name for _, name, _, _ in rows),
        scenario_set_lines="\n".join(f"  - {flow.get('name', 'Primary Flow')}" for flow in flows[:3]) or "  - source-defined primary flow",
    )


def build_stage_02a_stakeholder_value_context(
    *,
    context: dict[str, object],
    objectives: list[str],
    constraints: list[str],
    out_of_scope: list[str],
    primary_segment: str,
    workflow_chain: str,
    roles: list[dict[str, str]],
    module_names: list[str],
    flows: list[dict[str, object]],
) -> Stage02aStakeholderValueContext:
    stress_business = sequence_item_text(objectives, 0, "source-defined business objective")
    stress_technical = sequence_item_text(constraints, 0, "source-defined architectural constraint")
    stress_compliance = sequence_item_text(constraints, -1, "source-defined audit constraint")
    stress_resource = sequence_item_text(out_of_scope, 0, "source-defined deferred scope")
    supporting_role = dict_sequence_field_text(roles, 1, "Role", "secondary collaborator")
    review_role = dict_sequence_field_text(roles, 2, "Role", "review stakeholder")
    first_module = sequence_item_text(module_names, 0, "source start")
    last_module = sequence_item_text(module_names, -1, "source completion")
    value_pressure = signal_phrase(
        list(context.get("business_value_signals", [])),
        stress_business,
        limit=2,
    )
    commercial_pressure = signal_phrase(
        list(context.get("commercial_decision_signals", [])),
        "continued commitment still needs explicit decision truth",
        limit=2,
    )
    experience_pressure = signal_phrase(
        list(context.get("user_experience_signals", [])),
        "manual reconstruction and handoff friction",
        limit=2,
    )
    stakeholder_lines = build_stage_02a_stakeholder_value_lines(
        primary_segment=primary_segment,
        supporting_role=supporting_role,
        review_role=review_role,
        workflow_chain=workflow_chain,
        experience_pressure=experience_pressure,
        value_pressure=value_pressure,
        commercial_pressure=commercial_pressure,
        stress_technical=stress_technical,
        stress_compliance=stress_compliance,
        stress_resource=stress_resource,
        first_module=first_module,
        last_module=last_module,
        flows=flows,
    )
    return Stage02aStakeholderValueContext(
        stress_business=stress_business,
        stress_technical=stress_technical,
        stress_compliance=stress_compliance,
        stress_resource=stress_resource,
        value_pressure=value_pressure,
        commercial_pressure=commercial_pressure,
        experience_pressure=experience_pressure,
        stakeholder_profile_rows=stakeholder_lines.profile_rows,
        adoption_chain_lines=stakeholder_lines.adoption_chain_lines,
        conflict_map_lines=stakeholder_lines.conflict_map_lines,
        value_loop_lines=stakeholder_lines.value_loop_lines,
        stakeholder_chain_line=stakeholder_lines.chain_line,
        scenario_set_lines=stakeholder_lines.scenario_set_lines,
    )


def render_stage_02a_stakeholder_value_sections(
    *,
    stakeholder_profile_rows: str,
    adoption_chain_lines: str,
    conflict_map_lines: str,
    value_loop_lines: str,
    workflow_chain: str,
) -> str:
    return f"""## 17. Stakeholder Profiles, Adoption Chain, and Conflict Map
### Key Stakeholder Profiles
| stakeholder | interest / concern | success criteria | resistance pattern | influence | engagement approach |
|---|---|---|---|---|---|
{stakeholder_profile_rows}

### Adoption Chain
{adoption_chain_lines}

### Stakeholder Conflict Map
{conflict_map_lines}

## 18. Value Loop and Downstream Preservation Notes
- value_loop:
{value_loop_lines}
- design_should_preserve:
  - 主流程优先于功能目录
  - 对象与状态必须沿 `{workflow_chain}` 连续传递
  - 终点模块必须能给出可解释的完成状态
- architecture_should_preserve:
  - `{workflow_chain}` 的对象链
  - 权限与审计边界不能依赖页面层临时拼接
  - 延后项必须通过 seam 保留，而不是回写进 P0"""


def render_stage_02a_structure_choice_sections(
    *,
    primary_segment: str,
    supporting_role_lines: str,
    objectives: list[str],
    problem_cluster_lines: str,
    opportunity_cluster_lines: str,
    workflow_chain: str,
) -> str:
    return f"""## 2. Structure Choice
- chosen_panorama_structure: `workflow story-map`
- why_this_structure_not_that:
  - 产品价值来自 source 中定义的主业务链路，不是孤立功能堆叠。

## 3. User/Goal/Problem Panorama
- primary_boundary:
  - `{primary_segment}`
- supporting_roles:
{supporting_role_lines}
- goal_direction:
  - {'；'.join(objectives[:3]) if objectives else '建立可解释、可执行、可复盘的首波业务闭环'}
- core_problem_clusters:
{problem_cluster_lines}
- core_opportunity_clusters:
{opportunity_cluster_lines}

## 4. Persona / JTBD Matrix
| role | context | main job | success signal | failure consequence |
|---|---|---|---|---|
| {primary_segment} | 负责当前主目标与结果判断 | 证明该方案值得持续投入 | 主流程可解释且可完成 | 团队会把方案视为概念型项目 |
| execution operator | 负责执行被分配的业务动作 | 把上游结果转成实际处理 | 输入输出清晰可执行 | 建议停留在文档层 |
| decision sponsor | 关注投入产出与节奏 | 判断继续/收缩/调整资源 | 能看到方向性信号 | 预算不会继续支持 |
| governance reviewer | 控制接入与风险 | 确认权限、留存、可审计性 | 权限边界清晰 | 项目推进被阻断 |

## 5. Problem-to-Structure Mapping
| problem cluster | affected actor | structure consequence | why it belongs in Stage-02a |
|---|---|---|---|
| 主流程缺少统一起点 | {primary_segment} | 必须先锁定 source 中的起始模块 | 决定主流程起点 |
| 上下游输入输出断裂 | execution operator | 模块之间必须保留清晰 handoff | 决定 backbone 中间段 |
| 关键约束过晚暴露 | governance reviewer | 约束与权限必须提前进入流程设计 | 决定 scenario 结构 |
| 结果判断无统一出口 | decision sponsor | 终局评审必须保留业务结果解释 | 决定闭环终点 |

## 6. Structure Alternatives Comparison
| candidate | backbone shape | strength | failure risk | verdict |
|---|---|---|---|---|
| screen-first | 按独立页面或功能目录组织 | 容易快速出界面草图 | 会打散 source 主流程 | rejected |
| role-first | 按角色工作台组织 | 突出协作差异 | 会复制模块视图并削弱对象连续性 | rejected |
| workflow-first | {workflow_chain} | 最贴近 source 主链路 | 需要更明确 actor/state 设计，但最适合首版价值闭环 | chosen |
- why_chosen:
  - 依据 `user-story-mapping` 的 whole-picture 要求，首版不能只呈现功能目录，必须呈现可重复运营流程。
- method_bundle_activation:
  - `effective-requirements-analysis`: problem-to-structure 重编译
  - `product-demand-fit`: 证据强弱与边界诚实
  - `user-story-mapping`: 主流程与骨干活动拆解
  - `lean-product-development`: 首版价值环与延后项纪律"""


def render_stage_02a_structure_panorama_sections(
    *,
    primary_segment: str,
    supporting_role_lines: str,
    objectives: list[str],
    problem_cluster_lines: str,
    opportunity_cluster_lines: str,
    workflow_chain: str,
    backbone_lines: str,
    process_rows: str,
    primary_step_lines: str,
    actor_system_lines: str,
) -> str:
    return f"""{render_stage_02a_structure_choice_sections(
    primary_segment=primary_segment,
    supporting_role_lines=supporting_role_lines,
    objectives=objectives,
    problem_cluster_lines=problem_cluster_lines,
    opportunity_cluster_lines=opportunity_cluster_lines,
    workflow_chain=workflow_chain,
)}

## 7. Backbone Activities (Business Process Decomposition Precursor)
{backbone_lines}

## 8. Business Process Identification
| process type | process name | primary owner | trigger | output | why it matters |
|---|---|---|---|---|---|
{process_rows}

## 9. Workflow / State Detail
- primary workflow steps:
{primary_step_lines}
- actor/system decomposition:
{actor_system_lines}"""


def render_stage_02a_analysis_core_sections(
    *,
    scenario_decomposition_block: str,
    key_scenario_deep_analysis_block: str,
    persona_context_block: str,
    design_requirements_block: str,
    nfr_identification_block: str,
) -> str:
    return f"""## 10. Scenario Decomposition
{scenario_decomposition_block}

## 11. Key Scenario Deep Analysis
{key_scenario_deep_analysis_block}

## 12. Persona Context Scenario and Key Paths
{persona_context_block}

## 13. Design Requirements Extraction
{design_requirements_block}

## 14. NFR Initial Identification
{nfr_identification_block}"""


def render_stage_02a_constraint_priority_sections(
    *,
    stress_business: str,
    stress_technical: str,
    stress_compliance: str,
    stress_resource: str,
    workflow_chain: str,
    p0_items: list[str],
    p1_items: list[str],
    p2_items: list[str],
) -> str:
    return f"""## 15. Constraint Stress-Test
- business constraints:
  - {stress_business}
- technical constraints:
  - {stress_technical}
- compliance/privacy constraints:
  - {stress_compliance}
- resource/timeline constraints:
  - {stress_resource}
- tension register:
  - `coverage vs focus`: 想覆盖更多模块，但首版必须先聚焦 `{workflow_chain}`
  - `handoff simplicity vs constraint visibility`: 想缩短路径，但不能隐藏 `{stress_technical}`
  - `delivery speed vs scope honesty`: 想更快扩范围，但 `{stress_resource}` 仍需维持为延后项

## 16. Priority Split
- P0:
{chr(10).join(f"  - {item}" for item in p0_items)}
- P1:
{chr(10).join(f"  - {item}" for item in p1_items)}
- P2:
{chr(10).join(f"  - {item}" for item in p2_items)}
- exclusion logic:
  - 任何不直接服务 `{workflow_chain}` 的能力默认不进 P0"""


def render_stage_02a_structure_stress_test_section(*, workflow_chain: str, stress_resource: str) -> str:
    return f"""## 19. Structure Stress-Test and Deepening Loop Log
### Structure Stress-Test
- if_stage_03_only_received_feature_list:
  - 会丢失 `{workflow_chain}` 的骨干关系，MVP 会被错误切成零散模块集合。
- if_primary_segment_shifted_too_early:
  - 多角色并行主导会让 scenario 与 priority 失焦，导致 first slice 不可验证。
- if_one_provisional_assumption_breaks:
  - 即便部分流程细节需补实，workflow-first 结构仍成立，但 `{stress_resource}` 必须继续后置。
- verdict:
  - `freeze workflow-first backbone, keep review-bound truth visible`

### Deepening Loop Log
- loop_state:
  - `S-review-bound-freeze`
- rounds_executed:
  - 3
- round_log:
  - round_1:
    - refined: `structure alternatives + backbone flow`
    - tradeoff_clarified: `workflow-first vs screen-first`
    - outcome: `continue`
  - round_2:
    - refined: `stakeholder/adoption chain + key scenarios`
    - tradeoff_clarified: `compact flow vs explicit handoff visibility`
    - outcome: `continue`
  - round_3:
    - refined: `design requirements + constraint stress-test`
    - tradeoff_clarified: `coverage vs focus / speed vs scope honesty`
    - outcome: `freeze`"""


def render_stage_02a_evidence_summary_sections(
    *,
    reasoning_units: list[dict[str, str | list[str]]],
    context: dict[str, object],
    stakeholder_chain_line: str,
    scenario_set_lines: str,
    primary_segment: str,
    skill_assets: dict[str, object],
    source_evidence_blocks: list[str],
) -> str:
    stakeholder_section = f"""## 21. Stakeholder and Scenario Set
- stakeholder chain:
  - {stakeholder_chain_line}
- scenario set:
{scenario_set_lines}"""
    delta_section = f"""## 22. Requirement Analysis Delta Summary
- delta_1:
  - source 给出多个角色; analysis 先锁定 `{primary_segment}` 作为主边界
- delta_2:
  - source 列出模块与流程; analysis 把它们重编译为 backbone activities + scenarios
- delta_3:
  - source 给出 P0/P1/P2; analysis 明确 exclusion logic 与闭环优先级
- delta_4:
  - source 给出用户流程; analysis 补上 actor/system/state 关系"""
    return render_evidence_chain_sections(
        ledger_heading="## 20. Minimal Reasoning Unit Ledger",
        material_heading="## 23. Material Grounding Bridge",
        snapshot_heading="## 25. Skill Asset Ingestion Snapshot",
        method_heading="## 24. Method Activation Evidence",
        source_heading="## 26. Source Evidence Pack",
        reasoning_units=reasoning_units,
        context=context,
        skill_assets=skill_assets,
        snapshot_runtime_use_rules=[
            "the value loop was articulated before selecting the panorama structure",
            "at least two structure candidates were compared before freeze",
            "stakeholder, scenario, and persona assets materially shaped the structural panorama",
            "constraint stress-test and priority split remained analytical rather than cosmetic",
        ],
        source_evidence_blocks=source_evidence_blocks,
        extra_sections_after_ledger=[stakeholder_section, delta_section],
        snapshot_before_method=False,
    )


def build_stage_02a_reasoning_units(
    *,
    workflow_chain: str,
    flows: list[dict[str, object]],
    stress_technical: str,
    stress_resource: str,
    value_pressure: str,
    skill_assets: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    stage_skill_assets = skill_assets if skill_assets is not None else load_stage_skill_assets("stage_02a")
    return build_material_grounded_reasoning_units(
        [
            build_reasoning_unit(
                "Structure Choice", "chosen panorama structure", "structured -> compared -> freeze",
                "screen-first or role-first framing could hide the real workflow chain",
                ("structure comparison + workflow panorama selection", ["whole-picture requirements structure", "story-map construction"], "compare screen-first, role-first, and workflow-first views against source-defined business flow"),
                (["screen-first", "role-first", "workflow-first"], f"fast cataloging vs preserving the real business chain and source-grounded value pressure `{value_pressure}`", f"selected `workflow-first` around `{workflow_chain}` so the product can preserve `{value_pressure}` instead of collapsing into detached surfaces"),
                (f"source module matrix forms `{workflow_chain}`", "actor and object continuity matter more than standalone pages", "Stage-02a keeps workflow as the backbone"),
                ("provisional", "some state transitions still need deeper spec work in Stage-02b", "Stage-02b and Stage-03 must preserve the same backbone ordering", "workflow shape is now specific enough to constrain deeper design"),
            ),
            build_reasoning_unit(
                "Scenario and Backbone Decomposition", "backbone activities and scenarios", "structured -> decomposed -> freeze",
                "high-level flow narrative was not enough to drive design requirements",
                ("backbone decomposition + scenario analysis", ["structured analysis note building"], "split the primary workflow into backbone steps, scenarios, and handoff-sensitive paths"),
                ([flow.get("name", "Primary Flow") for flow in flows[:3]] or ["source-defined primary flow"], "compact narrative vs explicit handoff detail", "expanded the source flows into scenarios, key paths, and design requirements"),
                (f"source defines `{len(flows)}` primary business flows", "each flow requires explicit trigger, completion condition, and exception handling", "Stage-02a preserves scenario-level structure instead of only listing modules"),
                ("provisional", "edge-case exceptions still need Stage-02b payload and state modeling", "Stage-02b should deepen the contracts exposed here", "scenario decomposition is sufficient for structural analysis and slicing input"),
            ),
            build_reasoning_unit(
                "Constraint and Priority Discipline", "constraint stress-test and priority split", "structured -> stress-tested -> freeze",
                "scope could drift beyond the first viable workflow loop",
                ("constraint-first analysis + priority discipline", ["evidence-aware requirement framing", "value / adaptation constraint discipline"], "test business, technical, and scope pressure against the chosen workflow backbone and P0 focus"),
                (["keep strict P0/P1/P2 split", "expand P0 with deferred scope"], "broader scope vs first-loop integrity", "kept P0 focused on the shortest viable loop and preserved out-of-scope items explicitly"),
                (f"source constraints include `{stress_technical}`", f"source out-of-scope includes `{stress_resource}`", "preserve explicit exclusion logic and avoid silent scope creep"),
                ("review-bound", "real implementation cost may still force further reprioritization", "Stage-03 must inherit the same cutline and honesty rules", "priority logic is explicit enough for downstream slicing"),
            ),
            build_reasoning_unit(
                "Persona and NFR Carryover Alignment", "persona paths and NFR initial identification", "structured -> aligned -> freeze",
                "persona paths and NFR signals could stay detached from the chosen backbone",
                ("persona path alignment + NFR carryover check", ["whole-picture requirements structure", "structured analysis note building"], "bind role paths, implicit design requirements, and NFR scan signals back to the chosen workflow backbone"),
                (["persona detail as side note", "persona/NFR alignment as structural input"], "lighter structural draft vs explicit downstream design pressure", "kept persona paths and NFR scan as first-class structural consequences of the backbone"),
                (f"source roles must traverse `{workflow_chain}`", "detached persona or NFR notes create false structural completeness", "Stage-02a keeps actor path and NFR alignment visible before deeper specification"),
                ("review-bound", "some role-specific exception paths still need Stage-02b detail", "Stage-02b should preserve both persona path pressure and NFR scan consequences", "persona/NFR alignment is explicit enough for downstream use"),
            ),
        ],
        stage_skill_assets,
    )


def build_stage_02b_specification_context(
    *,
    source_context: dict[str, object],
    h42: str,
    objectives: list[str],
    nfrs: list[str],
    modules: list[dict[str, str]],
    objects: list[dict[str, str]],
    flows: list[dict[str, object]],
    navigation_surfaces: list[str],
    module_chain: str,
) -> Stage02bSpecificationContext:
    nfr_lines = "\n".join(f"- source_nfr: {item}" for item in nfrs[:6])
    primary_flow_name = dict_sequence_field_text(flows, 0, "name", "Primary Flow")
    nfr_reasoning_rows = "\n".join(
        f"| {preserved_display_label(item, fallback='Quality Attribute')} | {item} | weakens source workflow continuity | {primary_flow_name} | must stay visible in first-wave specification |"
        for item in nfrs[:5]
    )
    metric_seed = flatten_bullets(h42, 6) or objectives[:4] or ["source-defined metric or outcome signal"]
    metric_rows = "\n".join(
        f"| metric_{idx} | {item} | support source-side decision and review | wording may still need business calibration | keep metric definition explicit for downstream design |"
        for idx, item in enumerate(metric_seed, start=1)
    )
    subsystem_lines = "\n".join(
        f"  - {preserved_display_label(str(row.get('module', 'module')), fallback='Subsystem')}:\n    - owns {row.get('output', row.get('responsibility', 'source-defined output'))}"
        for row in modules[:8]
    )
    subsystem_interface_lines = "\n".join(
        f"  - {modules[idx].get('module', 'module')} -> {modules[idx + 1].get('module', 'next module')}:\n    - why: source workflow requires continuity\n    - what: {modules[idx].get('output', 'source output')}\n    - constraints: {modules[idx].get('architectural note', modules[idx].get('architectural_note', 'preserve source-defined boundary'))}"
        for idx in range(max(0, min(len(modules) - 1, 5)))
    )
    screen_precursor_lines = "\n".join(
        f"  - {surface}: preserve source-defined object continuity" for surface in navigation_surfaces
    )
    screen_object_lines = "\n".join(
        f"  - {surface} -> {objects[idx % len(objects)]['Object'] if objects else 'Business Object'}"
        for idx, surface in enumerate(navigation_surfaces)
    )
    module_token_seen: set[str] = set()
    object_token_seen: set[str] = set()
    er_rows = "\n".join(
        f"    M_{unique_ascii_token(str(objects[idx]['Owner Module']), fallback_values=[str(objects[idx]['Object'])], prefix='module', index=idx, existing=module_token_seen).upper()} ||--o{{ O_{unique_ascii_token(str(objects[idx]['Object']), fallback_values=[str(objects[idx]['Owner Module'])], prefix='object', index=idx, existing=object_token_seen).upper()} : owns"
        for idx in range(min(len(objects), 6))
    )
    return Stage02bSpecificationContext(
        nfr_lines=nfr_lines,
        nfr_reasoning_rows=nfr_reasoning_rows,
        metric_rows=metric_rows,
        subsystem_lines=subsystem_lines,
        subsystem_interface_lines=subsystem_interface_lines,
        screen_precursor_lines=screen_precursor_lines,
        screen_object_lines=screen_object_lines,
        payload_heading=payload_contract_heading_from_context(source_context),
        deferred_heading=deferred_seam_heading_from_context(source_context),
        er_rows=er_rows,
    )


def render_stage_02b_core_specification_sections(
    *,
    specification_context: Stage02bSpecificationContext,
    domain_context: dict[str, object],
    primary_actor: str,
    module_chain: str,
    objects: list[dict[str, str]],
    navigation_surfaces: list[str],
    modules: list[dict[str, str]],
    skip_stub_context: Stage02bSkipStubContext | None = None,
) -> str:
    return "\n\n".join(
        [
            render_stage_02b_quality_specification_sections(
                specification_context=specification_context,
                primary_actor=primary_actor,
                module_chain=module_chain,
                skip_stub_context=skip_stub_context,
            ),
            render_stage_02b_domain_model_sections(
                specification_context=specification_context,
                domain_context=domain_context,
                module_chain=module_chain,
                objects=objects,
                skip_stub_context=skip_stub_context,
            ),
            render_stage_02b_ia_interface_sections(
                specification_context=specification_context,
                domain_context=domain_context,
                module_chain=module_chain,
                navigation_surfaces=navigation_surfaces,
                modules=modules,
                skip_stub_context=skip_stub_context,
            ),
        ]
    )


def render_stage_02b_execution_state_section() -> str:
    return """## 1.2 Stage Execution State
- execution_state: `skipped`
- execution_mode:
  - `minimum-viable skip stub`
- skip_rationale:
  - Full Stage-02b deepening was intentionally skipped in this run to validate Admission Matrix `02b-skip` handling; this artifact preserves the minimum viable NFR / domain / IA / payload truth needed so Phase-2 is not forced to invent critical structure from scratch.
- safe_use_boundary:
  - Use this artifact as a constrained handoff bridge for Phase-2 safe start and Stage-03/04 continuity, not as proof that Stage-02b deepening has been fully completed.
- non_equivalence_to_full_stage:
  - Full quality-scenario deepening, stronger metric interpretation contracts, deeper object lifecycle hardening, and IA contract freeze remain review-bound and must be re-checked in Phase-2."""


def render_stage_02b_quality_specification_sections(
    *,
    specification_context: Stage02bSpecificationContext,
    primary_actor: str,
    module_chain: str,
    skip_stub_context: Stage02bSkipStubContext | None = None,
) -> str:
    skip_note = (
        """- fallback_origin:
  - `compiled from Stage-02a nfr_initial_identification + source metric / workflow evidence`
- minimum_viable_intent:
  - Preserve just enough NFR truth that Stage-03 slicing and Phase-2 architecture do not start blind.
- honesty_note:
  - This section is a skip-derived fallback, not a claim that Stage-02b quality deepening has been fully executed.
"""
        if skip_stub_context
        else ""
    )
    quality_intro = f"{skip_note}\n" if skip_note else ""
    return f"""## 2. NFR / Quality Requirements
{quality_intro}{specification_context.nfr_lines}

## 3. NFR Prioritization Reasoning
| attribute | why prioritized now | reverse risk if weak | affected scenario | MVP consequence |
|---|---|---|---|---|
{specification_context.nfr_reasoning_rows}
- deprioritized_attributes:
  - low-frequency enhancement work
  - cross-context expansion not required by current source

## 4. Quality Scenario Matrix
| attribute | stimulus | environment | expected response | measure |
|---|---|---|---|---|
| reliability | repeat a source-defined workflow step | current source environment | output stays explainable | no hidden state jump across `{module_chain}` |
| usability | `{primary_actor}` follows the primary module chain | primary business operation | next module can consume current output | no manual reconstruction between modules |
| security/data-control | role-based access hits a sensitive record | source-defined account boundary | access remains auditable | constraints from source stay visible |
| maintainability | later capability extends the current workflow | first-wave implementation baseline | module seams remain extensible | downstream can add later scope without rewriting core objects |

## 5. Metric Definition and Interpretation Register
| metric | meaning | first-wave use | interpretation risk | mitigation |
|---|---|---|---|---|
{specification_context.metric_rows}"""


def render_stage_02b_domain_model_sections(
    *,
    specification_context: Stage02bSpecificationContext,
    domain_context: dict[str, object],
    module_chain: str,
    objects: list[dict[str, str]],
    skip_stub_context: Stage02bSkipStubContext | None = None,
) -> str:
    skip_note = (
        """- domain_model_state:
  - `partial-from-02a-and-source`
- safe_interpretation_rule:
  - The object chain below is preserved so downstream design/architecture can start from explicit entities and relationships, but field-level contracts and lifecycle edge cases remain review-bound.
"""
        if skip_stub_context
        else ""
    )
    domain_intro = f"{skip_note}\n" if skip_note else ""
    return f"""## 6. Domain Model Direction
{domain_intro}- core entities:
{chr(10).join(f"  - {row['Object']}" for row in objects[:10])}
- relationship direction:
  - {module_chain}
- entity catalog:
{chr(10).join(f"  - `{row['Object']}`: {row['Description']}" for row in objects[:10])}
- object lifecycle notes:
{chr(10).join(f"  - {row['Object']}: owned by {row['Owner Module']} and used to preserve `{row['Description']}`" for row in objects[:6])}

## 7. Conceptual ER Diagram
```mermaid
erDiagram
{specification_context.er_rows}
```

## 8. Key Relationships and Data Characteristics
| dimension | first-wave decision | rationale |
|---|---|---|
| primary workflow chain | keep each module output explicit | downstream design depends on stable object transitions |
| role visibility | bind records to source-defined role boundaries | role handoff must stay auditable |
| architectural constraints | preserve source-stated constraints in the first-wave contract | avoid hidden implementation assumptions |
| deferred capability seam | keep future items visible without promoting them into MVP | prevents false completeness |
| business continuity | make primary flow traversable end-to-end | users should not reconstruct the workflow manually |

## 9. Business Subsystem Boundaries
- applicable:
  - `yes`
- subsystems:
{specification_context.subsystem_lines}
- subsystem_interfaces:
{specification_context.subsystem_interface_lines}
{render_stage02b_domain_boundary_honesty_lines(domain_context)}

## 10. Object-to-Workflow Mapping
{render_object_workflow_rows(domain_context)}"""


def render_stage_02b_ia_interface_sections(
    *,
    specification_context: Stage02bSpecificationContext,
    domain_context: dict[str, object],
    module_chain: str,
    navigation_surfaces: list[str],
    modules: list[dict[str, str]],
    skip_stub_context: Stage02bSkipStubContext | None = None,
) -> str:
    ia_note = (
        """- ia_direction_state:
  - `partial-from-02a-and-source`
- safe_interpretation_rule:
  - Workflow-first IA remains the current safe direction, but page-level detail and state completeness should still be treated as constrained and prototype-validated rather than frozen.
"""
        if skip_stub_context
        else ""
    )
    ia_intro = f"{ia_note}\n" if ia_note else ""
    payload_note = (
        """- skip_mode_preservation_rule:
  - Even when Stage-02b is skipped, module interface payload structure cannot disappear; otherwise workflow handoff semantics collapse and Phase-2 would be forced to re-invent core execution semantics.
"""
        if skip_stub_context
        else ""
    )
    payload_intro = f"{payload_note}\n" if payload_note else ""
    return f"""## 11. Information Architecture Direction
{ia_intro}- organization:
  - workflow-first + object-traceable
- navigation:
  - {' / '.join(navigation_surfaces)}
- labeling:
  - 业务可理解术语优先
- IA impact:
  - 页面与模块边界必须围绕 `{module_chain}` 的可执行链路。
- screen spec precursor:
{specification_context.screen_precursor_lines}
- screen/object matrix:
{specification_context.screen_object_lines}

## 12. IA Decision Alternatives Comparison
| alternative | organizing axis | strength | failure risk | verdict |
|---|---|---|---|---|
| entity-first | 按领域对象划分 | 对数据结构清晰 | 新用户难以看出主流程 | rejected |
| role-first | 按角色工作台划分 | 突出协作差异 | 会复制对象视图并打散闭环 | rejected |
| workflow-first | 按 {' -> '.join(navigation_surfaces[:6])} | 最贴近首版闭环认知 | 需要更强对象映射约束 | chosen |

## 13. IA Spec Precursor Matrix
{render_screen_navigation_rows(domain_context)}

## 14. Module Responsibility Matrix
{render_module_matrix_rows(modules)}

## 15. {specification_context.payload_heading}
{payload_intro}- contract_rule:
  - 每个模块都必须把 source 中定义的输入和输出保留为结构化 payload，避免下游模块依赖人工重建上下文。
{render_interface_payload_rows(domain_context)}

## 16. {specification_context.deferred_heading}
- seam_rule:
  - source 已明确声明的未来阶段能力不能写成空白，必须保留 seam 说明，避免后续为了扩展而重写对象链。
{render_deferred_seam_rows(domain_context)}
- downstream_rule:
  - architecture 可以先声明 seam entity/interface，但不得把未来能力写入 MVP acceptance promise。"""


def build_stage_02b_quality_and_domain_reasoning_units(
    *,
    nfrs: list[str],
    module_chain: str,
    primary_flow_name: str,
    module_names: list[str],
) -> list[dict[str, object]]:
    return [
        build_reasoning_unit(
            "Quality Attribute Prioritization", "NFR prioritization reasoning", "structured -> prioritized -> freeze",
            "quality attributes could remain generic and disconnected from the workflow",
            ("NFR prioritization + reverse-risk mapping", ["quality-scenario framing", "reverse-risk thinking for NFR prioritization"], "prioritize attributes by workflow breakage risk rather than by abstract completeness"),
            ([preserved_display_label(item, fallback="Quality Attribute") for item in nfrs[:4]], "broad quality coverage vs first-wave specification focus", f"kept quality reasoning anchored to `{module_chain}` and `{primary_flow_name}`"),
            (f"source declares NFRs `{'; '.join(nfrs[:3])}`", "weak quality attributes break workflow continuity before they break edge-case scale", "Stage-02b prioritizes reverse-risk on the main loop"),
            ("provisional", "deeper quantitative thresholds still need later hardening", "Stage-03 and Stage-04 should reuse the same critical attributes and wording", "quality priorities are explicit enough for specification deepening"),
        ),
        build_reasoning_unit(
            "Domain and Subsystem Boundaries", "domain model + subsystem boundaries", "structured -> modeled -> freeze",
            "modules and objects could remain separate lists without boundary semantics",
            ("domain modeling + subsystem boundary analysis", ["conceptual domain modeling", "business subsystem boundary identification"], "bind objects, modules, and outputs into explicit subsystem seams"),
            (module_names, "simple lists vs durable object and subsystem seams", "modeled object ownership and handoff boundaries directly from the source module chain"),
            (f"source module matrix names `{module_chain}`", "explicit seams prevent later re-invention of ownership and payload contracts", "keep subsystem boundaries visible in Stage-02b"),
            ("provisional", "field-level lifecycle rules still need architecture-level deepening", "payload contract 与 IA 必须保留同一套子系统边界逻辑", "boundary model is sufficient for first-wave specification work"),
        ),
    ]


def build_stage_02b_ia_and_payload_reasoning_units(
    *,
    module_chain: str,
    deferred_scope: str,
) -> list[dict[str, object]]:
    return [
        build_reasoning_unit(
            "IA and Deferred Seam Discipline", "IA direction + deferred capability seam", "structured -> stress-tested -> freeze",
            "IA could drift away from workflow, and deferred scope could disappear from the spec",
            ("IA decision comparison + deferred seam preservation", ["information-architecture direction setting", "deferred seam design for attribution / conversion"], "compare organizing axes, then keep out-of-scope capabilities visible as explicit seams"),
            (["entity-first", "role-first", "workflow-first"], "cleaner navigation vs preserving workflow and future extension honesty", "selected workflow-first IA and preserved future capabilities as deferred seams"),
            (f"source out-of-scope includes `{deferred_scope}`", "hiding deferred items creates false completeness for downstream teams", "IA and seam decisions stay coupled to the workflow backbone"),
            ("review-bound", "some later capabilities may need richer interface reservation", "Stage-03 can slice safely without silently dropping future seams", "IA and seam logic are explicit enough for re-audit"),
        ),
        build_reasoning_unit(
            "Payload and Workflow Mapping Integrity", "workflow mapping + interface payload preservation", "structured -> cross-checked -> freeze",
            "workflow mapping, payloads, and screen surfaces could drift apart under recompile pressure",
            ("contract integrity cross-check", ["source-capability-to-payload recompilation", "specification stress-test against Stage-03 slicing"], "cross-check module outputs, object-to-workflow mapping, and IA precursor surfaces against the same first-wave chain"),
            (["independent tables", "shared contract spine across tables"], "faster isolated sections vs one consistent contract spine", "kept payload, mapping, and IA evidence tied to the same module chain"),
            (f"source outputs must traverse `{module_chain}`", "inconsistent mapping tables cause downstream architecture drift", "Stage-02b preserves one shared contract spine across deep-spec sections"),
            ("review-bound", "field-level validation and export rules still need implementation-facing hardening", "Stage-03 and PRD assembly should preserve the same payload and mapping spine", "cross-table integrity is explicit enough for downstream use"),
        ),
    ]


def build_stage_02b_reasoning_units(
    *,
    nfrs: list[str],
    module_chain: str,
    flows: list[dict[str, object]],
    modules: list[dict[str, str]],
    out_of_scope: list[str],
    skill_assets: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    stage_skill_assets = skill_assets if skill_assets is not None else load_stage_skill_assets("stage_02b")
    primary_flow_name = dict_sequence_field_text(flows, 0, "name", "Primary Flow")
    deferred_scope = sequence_item_text(out_of_scope, 0, "source-defined deferred capability")
    module_names = [str(row.get("module", "module")) for row in modules[:4]]
    return build_material_grounded_reasoning_units(
        [
            *build_stage_02b_quality_and_domain_reasoning_units(
                nfrs=nfrs,
                module_chain=module_chain,
                primary_flow_name=primary_flow_name,
                module_names=module_names,
            ),
            *build_stage_02b_ia_and_payload_reasoning_units(
                module_chain=module_chain,
                deferred_scope=deferred_scope,
            ),
        ],
        stage_skill_assets,
    )


def render_stage_02b_specification_stress_test(skip_stub_context: Stage02bSkipStubContext | None = None) -> str:
    skip_warning = (
        """- skip_specific_warning:
  - Because this run used a skip stub, the stress-test below must be read as a bounded guardrail set, not as proof that all specification tensions were fully exhausted.
"""
        if skip_stub_context
        else ""
    )
    return f"""## 17. Specification Stress-Test
{skip_warning}- blind spot 1:
  - 若缺乏 domain relationship，Stage-03 容易退化为 feature-list 切片。
- blind spot 2:
  - 若缺乏 metric definition，Stage-04 的判定信号会失真。
- blind spot 3:
  - 若 IA 不映射对象链，页面会脱离业务闭环。
- blind spot 4:
  - 若模块输入输出没有单独契约，后续扩展与审计都会困难。
- verdict:
  - `passed with review-bound constraints`"""


def render_stage_02b_deepening_loop_log() -> str:
    return """## 18. Deepening Loop Log
- loop_state:
  - `S-review-bound-freeze`
- rounds_executed:
  - 3
- round_log:
  - round_1:
    - refined: `NFR coverage + reverse-risk mapping`
    - alternatives_compared: `critical vs deferred attributes`
    - outcome: `continue`
  - round_2:
    - refined: `domain entities + subsystem boundaries`
    - alternatives_compared: `thin entity list vs object-chain model`
    - outcome: `continue`
  - round_3:
    - refined: `IA direction + screen/object dependency`
    - alternatives_compared: `workflow-first vs entity-first`
    - outcome: `freeze`"""


def render_stage_02b_requirement_analysis_delta_summary() -> str:
    return """## 20. Requirement Analysis Delta Summary
- delta_1:
  - source列出核心功能; analysis提炼出对象链与模块责任
- delta_2:
  - source给出页面设计; analysis补充 screen/object dependency
- delta_3:
  - source给出指标定义; analysis补充 interpretation risk 与 mitigation
- delta_4:
  - source给出模块输入输出; analysis把它们编译成 interface payload contract
- delta_5:
  - source给出 future/deferred 能力; analysis把它们保留为 deferred capability seam，而不是直接丢失或假装首版可实现"""


def stage_02b_evidence_summary_headings(
    skip_stub_context: Stage02bSkipStubContext | None,
) -> tuple[str, str | None, list[str] | None]:
    if not skip_stub_context:
        return "## 24. Source Evidence Pack", None, None
    return (
        "## 25. Source Evidence Pack",
        "## 24. Stage-02a Carryover Evidence",
        [skip_stub_context.stage_02a_nfr, skip_stub_context.stage_02a_value_loop],
    )


def render_stage_02b_evidence_summary_sections(
    *,
    reasoning_units: list[dict[str, str | list[str]]],
    context: dict[str, object],
    skill_assets: dict[str, object],
    source_evidence_blocks: list[str],
    skip_stub_context: Stage02bSkipStubContext | None = None,
) -> str:
    source_heading, upstream_heading, upstream_evidence_blocks = stage_02b_evidence_summary_headings(skip_stub_context)
    evidence_chain = render_evidence_chain_sections(
        ledger_heading="## 19. Minimal Reasoning Unit Ledger",
        material_heading="## 21. Material Grounding Bridge",
        snapshot_heading="## 23. Skill Asset Ingestion Snapshot",
        method_heading="## 22. Method Activation Evidence",
        source_heading=source_heading,
        reasoning_units=reasoning_units,
        context=context,
        skill_assets=skill_assets,
        snapshot_runtime_use_rules=[
            "at least three material quality attributes were prioritized with reverse-risk reasoning",
            "conceptual domain modeling and subsystem thinking were derived from Stage-02a scenarios",
            "IA direction decisions were treated as architecture-constraining choices rather than page sketches",
            "module input/output details were recompiled into a structured payload contract instead of generic advice",
            "deferred capabilities were preserved as extension seams instead of being silently dropped",
            "the specification stress-test made Stage-03 slicing consequences explicit",
        ],
        source_evidence_blocks=source_evidence_blocks,
        upstream_heading=upstream_heading,
        upstream_evidence_blocks=upstream_evidence_blocks,
        extra_sections_after_ledger=[render_stage_02b_requirement_analysis_delta_summary()],
        snapshot_before_method=False,
    )
    return "\n\n".join(
        [
            render_stage_02b_specification_stress_test(skip_stub_context),
            render_stage_02b_deepening_loop_log(),
            evidence_chain,
        ]
    )


def build_stage_02a_analysis_blocks(
    source_bundle: Stage02aSourceBundle,
    structural_mapping_context: Stage02aStructuralMappingContext,
) -> Stage02aAnalysisBlocks:
    return Stage02aAnalysisBlocks(
        scenario_decomposition=build_stage_02a_scenario_decomposition_block(
            flows=source_bundle.flows,
            primary_segment=source_bundle.primary_segment,
        ),
        key_scenario_deep_analysis=build_stage_02a_key_scenario_deep_analysis_block(
            flows=source_bundle.flows,
            roles=source_bundle.roles,
            primary_segment=source_bundle.primary_segment,
            constraints=source_bundle.constraints,
        ),
        persona_context=build_stage_02a_persona_context_block(
            primary_segment=source_bundle.primary_segment,
            objectives=source_bundle.objectives,
            first_flow_steps=structural_mapping_context.first_flow_steps,
            workflow_chain=source_bundle.workflow_chain,
            modules=source_bundle.modules,
        ),
        design_requirements=build_stage_02a_design_requirements_block(
            modules=source_bundle.modules,
            roles=source_bundle.roles,
            primary_segment=source_bundle.primary_segment,
        ),
        nfr_identification=build_stage_02a_nfr_identification_block(
            primary_segment=source_bundle.primary_segment,
            workflow_chain=source_bundle.workflow_chain,
            module_names=source_bundle.module_names,
            roles=source_bundle.roles,
            constraints=source_bundle.constraints,
        ),
    )


def build_stage_02a_render_context(
    source_text: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> Stage02aRenderContext:
    source_bundle = build_stage_02a_source_bundle(source_text, source_snapshot=source_snapshot)
    structural_mapping_context = build_stage_02a_structural_mapping_context(source_bundle)
    analysis_blocks = build_stage_02a_analysis_blocks(source_bundle, structural_mapping_context)
    stakeholder_value_context = build_stage_02a_stakeholder_value_context(
        context=source_bundle.context,
        objectives=source_bundle.objectives,
        constraints=source_bundle.constraints,
        out_of_scope=source_bundle.out_of_scope,
        primary_segment=source_bundle.primary_segment,
        workflow_chain=source_bundle.workflow_chain,
        roles=source_bundle.roles,
        module_names=source_bundle.module_names,
        flows=source_bundle.flows,
    )
    skill_assets = load_stage_skill_assets("stage_02a")
    reasoning_units = build_stage_02a_reasoning_units(
        workflow_chain=source_bundle.workflow_chain,
        flows=source_bundle.flows,
        stress_technical=stakeholder_value_context.stress_technical,
        stress_resource=stakeholder_value_context.stress_resource,
        value_pressure=stakeholder_value_context.value_pressure,
        skill_assets=skill_assets,
    )
    return Stage02aRenderContext(
        source_bundle=source_bundle,
        structural_mapping_context=structural_mapping_context,
        analysis_blocks=analysis_blocks,
        stakeholder_value_context=stakeholder_value_context,
        skill_assets=skill_assets,
        reasoning_units=reasoning_units,
    )


def render_stage_02a_opening_and_structure_sections(
    render_context: Stage02aRenderContext,
    *,
    version: str,
    owner: str,
) -> str:
    source_bundle = render_context.source_bundle
    business_world_model = source_bundle.business_world_model
    product_label = source_bundle.product_label
    primary_segment = source_bundle.primary_segment
    objectives = source_bundle.objectives
    workflow_chain = source_bundle.workflow_chain
    structural_mapping_context = render_context.structural_mapping_context
    supporting_role_lines = structural_mapping_context.supporting_role_lines
    problem_cluster_lines = structural_mapping_context.problem_cluster_lines
    opportunity_cluster_lines = structural_mapping_context.opportunity_cluster_lines
    backbone_lines = structural_mapping_context.backbone_lines
    process_rows = structural_mapping_context.process_rows
    primary_step_lines = structural_mapping_context.primary_step_lines
    actor_system_lines = structural_mapping_context.actor_system_lines

    return f"""{render_stage_document_opening(
    stage_display="Stage-02a",
    stage_slug="requirements-structural-analysis",
    document_suffix="Structural Analysis",
    product_label=product_label,
    version=version,
    owner=owner,
)}

{render_traceability_block("stage_02a")}

{render_semantic_authoring_spine_section(business_world_model)}

{render_topology_profile_record(business_world_model, inherited=True)}

{render_stage_02a_structure_panorama_sections(
    primary_segment=primary_segment,
    supporting_role_lines=supporting_role_lines,
    objectives=objectives,
    problem_cluster_lines=problem_cluster_lines,
    opportunity_cluster_lines=opportunity_cluster_lines,
    workflow_chain=workflow_chain,
    backbone_lines=backbone_lines,
    process_rows=process_rows,
    primary_step_lines=primary_step_lines,
    actor_system_lines=actor_system_lines,
)}
"""


def render_stage_02a_analysis_and_constraint_sections(render_context: Stage02aRenderContext) -> str:
    source_bundle = render_context.source_bundle
    analysis_blocks = render_context.analysis_blocks
    stakeholder_value_context = render_context.stakeholder_value_context
    return f"""{render_stage_02a_analysis_core_sections(
    scenario_decomposition_block=analysis_blocks.scenario_decomposition,
    key_scenario_deep_analysis_block=analysis_blocks.key_scenario_deep_analysis,
    persona_context_block=analysis_blocks.persona_context,
    design_requirements_block=analysis_blocks.design_requirements,
    nfr_identification_block=analysis_blocks.nfr_identification,
)}

{render_stage_02a_constraint_priority_sections(
    stress_business=stakeholder_value_context.stress_business,
    stress_technical=stakeholder_value_context.stress_technical,
    stress_compliance=stakeholder_value_context.stress_compliance,
    stress_resource=stakeholder_value_context.stress_resource,
    workflow_chain=source_bundle.workflow_chain,
    p0_items=source_bundle.p0_items,
    p1_items=source_bundle.p1_items,
    p2_items=source_bundle.p2_items,
)}
"""


def render_stage_02a_stakeholder_and_evidence_sections(render_context: Stage02aRenderContext) -> str:
    source_bundle = render_context.source_bundle
    stakeholder_value_context = render_context.stakeholder_value_context
    return f"""{render_stage_02a_stakeholder_value_sections(
    stakeholder_profile_rows=stakeholder_value_context.stakeholder_profile_rows,
    adoption_chain_lines=stakeholder_value_context.adoption_chain_lines,
    conflict_map_lines=stakeholder_value_context.conflict_map_lines,
    value_loop_lines=stakeholder_value_context.value_loop_lines,
    workflow_chain=source_bundle.workflow_chain,
)}

{render_stage_02a_structure_stress_test_section(
    workflow_chain=source_bundle.workflow_chain,
    stress_resource=stakeholder_value_context.stress_resource,
)}

{render_stage_02a_evidence_summary_sections(
    reasoning_units=render_context.reasoning_units,
    context=source_bundle.context,
    stakeholder_chain_line=stakeholder_value_context.stakeholder_chain_line,
    scenario_set_lines=stakeholder_value_context.scenario_set_lines,
    primary_segment=source_bundle.primary_segment,
    skill_assets=render_context.skill_assets,
    source_evidence_blocks=[
        source_bundle.h23,
        source_bundle.h31,
        source_bundle.h32,
        source_bundle.h33,
        source_bundle.h34,
        source_bundle.h41,
        source_bundle.h43,
        source_bundle.h7p0,
        source_bundle.h7p1,
        source_bundle.h7p2,
        source_bundle.h8,
        source_bundle.h51,
        source_bundle.h52,
        source_bundle.h53,
        source_bundle.h61,
        source_bundle.h62,
    ],
)}
"""


def render_stage_02a_document(
    render_context: Stage02aRenderContext,
    *,
    version: str,
    owner: str,
) -> str:
    return "\n\n".join(
        [
            render_stage_02a_opening_and_structure_sections(render_context, version=version, owner=owner),
            render_stage_02a_analysis_and_constraint_sections(render_context),
            render_stage_02a_stakeholder_and_evidence_sections(render_context),
        ]
    )


def build_stage_02a(
    source_text: str,
    version: str,
    owner: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> str:
    return render_stage_02a_document(
        build_stage_02a_render_context(source_text, source_snapshot=source_snapshot),
        version=version,
        owner=owner,
    )


def build_stage_02b_render_context(
    source_text: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> Stage02bRenderContext:
    snapshot = source_snapshot or build_phase1_source_snapshot(source_text)
    sections = snapshot.sections
    context = snapshot.context
    business_world_model = snapshot.business_world_model
    product_label = snapshot.product_label
    roles = snapshot.roles
    modules = snapshot.modules
    objects = context["objects"]
    flows = snapshot.flows
    objectives = context["objectives"] or ["preserve the source-defined workflow chain"]
    nfrs = context["nfrs"] or ["source-defined reliability requirement", "source-defined usability requirement"]
    out_of_scope = context["out_of_scope"] or ["source-defined deferred capability"]
    navigation_surfaces = context["navigation_surfaces"]
    primary_actor = dict_sequence_field_text(roles, 0, "Role", "primary operator")
    module_chain = snapshot.module_chain
    specification_context = build_stage_02b_specification_context(
        source_context=context,
        h42=sections.h42,
        objectives=objectives,
        nfrs=nfrs,
        modules=modules,
        objects=objects,
        flows=flows,
        navigation_surfaces=navigation_surfaces,
        module_chain=module_chain,
    )
    skill_assets = load_stage_skill_assets("stage_02b")
    reasoning_units = build_stage_02b_reasoning_units(
        nfrs=nfrs,
        module_chain=module_chain,
        flows=flows,
        modules=modules,
        out_of_scope=out_of_scope,
        skill_assets=skill_assets,
    )
    return Stage02bRenderContext(
        product_label=product_label,
        domain_context=context,
        business_world_model=business_world_model,
        specification_context=specification_context,
        primary_actor=primary_actor,
        module_chain=module_chain,
        objects=objects,
        navigation_surfaces=navigation_surfaces,
        modules=modules,
        reasoning_units=reasoning_units,
        skill_assets=skill_assets,
        source_evidence_blocks=[
            sections.h23,
            sections.h42,
            sections.h_features,
            sections.h_ui,
            sections.h_adv,
        ],
    )


def render_stage_02b_document(
    render_context: Stage02bRenderContext,
    *,
    version: str,
    owner: str,
    skip_stub_context: Stage02bSkipStubContext | None = None,
) -> str:
    is_skip_stub = skip_stub_context is not None
    execution_state_section = f"\n\n{render_stage_02b_execution_state_section()}" if is_skip_stub else ""
    return f"""{render_stage_document_opening(
    stage_display="Stage-02b",
    stage_slug="requirements-specification-deepening",
    document_suffix="Skip-Stub Specification Fallback" if is_skip_stub else "Specification Deepening",
    product_label=render_context.product_label,
    version=version,
    owner=owner,
    title_state="skip-stub / minimum-viable" if is_skip_stub else "deep-compiled",
    status="skip-stub" if is_skip_stub else "provisional",
    source_status="stage_02a-derived-minimum-viable" if is_skip_stub else "mixed",
)}

{render_traceability_block("stage_02b")}{execution_state_section}

{render_semantic_authoring_spine_section(render_context.business_world_model)}

{render_stage_02b_core_specification_sections(
    specification_context=render_context.specification_context,
    domain_context=render_context.domain_context,
    primary_actor=render_context.primary_actor,
    module_chain=render_context.module_chain,
    objects=render_context.objects,
    navigation_surfaces=render_context.navigation_surfaces,
    modules=render_context.modules,
    skip_stub_context=skip_stub_context,
)}

{render_stage_02b_evidence_summary_sections(
    reasoning_units=render_context.reasoning_units,
    context=render_context.domain_context,
    skill_assets=render_context.skill_assets,
    source_evidence_blocks=render_context.source_evidence_blocks,
    skip_stub_context=skip_stub_context,
)}
"""


def build_stage_02b(
    source_text: str,
    version: str,
    owner: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> str:
    return render_stage_02b_document(
        build_stage_02b_render_context(source_text, source_snapshot=source_snapshot),
        version=version,
        owner=owner,
    )


def build_stage_02b_skip_stub_context(
    source_text: str,
    stage_02a_text: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> Stage02bSkipStubContext:
    del source_text, source_snapshot
    return Stage02bSkipStubContext(
        stage_02a_nfr=find_named_h2_block(stage_02a_text, ["NFR Initial Identification"]),
        stage_02a_value_loop=find_named_h2_block(stage_02a_text, ["Value Loop and Downstream Preservation Notes"]),
    )


def build_stage_02b_skip_stub(
    source_text: str,
    stage_02a_text: str,
    version: str,
    owner: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> str:
    snapshot = source_snapshot or build_phase1_source_snapshot(source_text)
    return render_stage_02b_document(
        build_stage_02b_render_context(source_text, source_snapshot=snapshot),
        version=version,
        owner=owner,
        skip_stub_context=build_stage_02b_skip_stub_context(
            source_text,
            stage_02a_text,
            source_snapshot=snapshot,
        ),
    )


def build_stage_03_source_bundle(
    source_text: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> Stage03SourceBundle:
    snapshot = source_snapshot or build_phase1_source_snapshot(source_text)
    sections = snapshot.sections
    context = snapshot.context
    business_world_model = snapshot.business_world_model
    product_label = snapshot.product_label
    segments = snapshot.segments
    primary_segment = snapshot.primary_segment
    roles = snapshot.roles
    modules = snapshot.modules
    flows = snapshot.flows
    nfrs = context["nfrs"] or ["source-defined non-functional requirement"]
    constraints = context["constraints"] or ["source-defined architectural constraint"]
    out_of_scope = context["out_of_scope"] or ["source-defined deferred item"]
    first_slice_modules = snapshot.first_slice_modules
    p0_items = context["p0"] or first_slice_modules or [str(row.get("module", "source-defined module")).strip() for row in modules[:3]]
    p1_items = context["p1"] or [str(row.get("module", "source-defined later slice")).strip() for row in modules[3:5]]
    p2_items = context["p2"] or out_of_scope
    full_loop = " -> ".join(snapshot.module_names) or "source-defined workflow loop"
    first_slice_loop = " -> ".join(first_slice_modules) if first_slice_modules else "source-defined first slice"
    minimum_loop_items = first_slice_modules or p0_items
    minimum_loop = " -> ".join(minimum_loop_items[: max(2, min(len(minimum_loop_items), 5))]) if minimum_loop_items else "source-defined minimum loop"
    primary_flow_name = snapshot.primary_flow_name
    main_roles = snapshot.main_roles
    return Stage03SourceBundle(
        h51=sections.h51,
        h52=sections.h52,
        h53=sections.h53,
        h7p0=sections.h7p0,
        h7p1=sections.h7p1,
        h7p2=sections.h7p2,
        h8=sections.h8,
        context=context,
        business_world_model=business_world_model,
        product_label=str(product_label),
        segments=list(segments),
        primary_segment=str(primary_segment),
        roles=list(roles),
        modules=list(modules),
        flows=list(flows),
        nfrs=list(nfrs),
        constraints=list(constraints),
        out_of_scope=list(out_of_scope),
        p0_items=list(p0_items),
        p1_items=list(p1_items),
        p2_items=list(p2_items),
        full_loop=full_loop,
        first_slice_loop=first_slice_loop,
        minimum_loop=minimum_loop,
        primary_flow_name=primary_flow_name,
        main_roles=main_roles,
    )


def build_stage_03_slice_planning_lines(
    *,
    first_slice_modules: list[str],
    p0_items: list[str],
    p1_items: list[str],
    nfrs: list[str],
    out_of_scope: list[str],
    full_loop: str,
    first_slice_loop: str,
    primary_flow_name: str,
    main_roles: list[str],
) -> Stage03SlicePlanningLines:
    comparison_rows = [
        "| candidate | what_is_in_first_slice | user_value_speed | evidence_confidence | dependency_complexity | validation_leverage | risk_of_overreach | verdict |",
        "|---|---|---|---|---|---|---|---|",
        f"| module-first | {' + '.join(p0_items[:2]) if p0_items[:2] else 'source-defined modules'} | medium | high | low | medium | medium | rejected |",
        f"| role-workbench-first | {' + '.join(main_roles[:2])} workspace | medium | medium | medium | low | high | rejected |",
        f"| workflow-loop-first | {first_slice_loop} | high | high | medium | high | low-medium | chosen |",
    ]
    value_frequency_candidates = unique_preserve_order(p0_items[:3] + p1_items[:3])
    return Stage03SlicePlanningLines(
        comparison_rows=comparison_rows,
        nfr_force_lines="\n".join(f"  - {item}" for item in nfrs[:3]) or "  - source-defined NFR must enter first slice",
        nfr_relaxed_lines="\n".join(f"  - {item}" for item in nfrs[3:5]) or "  - 非首要 NFR 留在后续深化",
        dependency_impact_lines="\n".join(
            [
                f"  - {full_loop}",
                f"  - `{primary_flow_name}` 的对象交接如果被拆散，首个切片就无法验证真实业务闭环。",
                f"  - 角色 `{', '.join(main_roles[:3])}` 之间的 handoff 必须跟着模块链一起进入 MVP，而不是后补。",
            ]
        ),
        value_frequency_rows="\n".join(
            f"| {item} | {'high' if item in p0_items else 'medium'} | {'high' if item in first_slice_modules else 'medium'} | {'keep in first slice' if item in p0_items or item in first_slice_modules else 'move to later slice'} | source-defined capability classification |"
            for item in value_frequency_candidates
        ) or "| source-defined capability | medium | medium | keep in first slice | source-defined capability classification |",
        deferred_honesty_rows="\n".join(
            f"| {item} | source 明确把它放在 MVP 外，当前不应前置承诺 | 把它包装成首版完整能力会掩盖真实 cutline | 接受延后，但需在 seam / backlog 中显式保留 |"
            for item in out_of_scope[:4]
        ) or "| source-defined deferred item | 当前不进 MVP | 冒充已覆盖会造成假完整感 | 需要显式延后 |",
    )


def build_stage_03_slice_planning_context(
    *,
    domain_context: dict[str, object],
    p0_items: list[str],
    p1_items: list[str],
    p2_items: list[str],
    nfrs: list[str],
    out_of_scope: list[str],
    full_loop: str,
    first_slice_loop: str,
    minimum_loop: str,
    primary_flow_name: str,
    primary_segment: str,
    main_roles: list[str],
    constraints: list[str],
) -> Stage03SlicePlanningContext:
    first_slice_modules = list(domain_context.get("first_slice_modules", []))
    planning_lines = build_stage_03_slice_planning_lines(
        first_slice_modules=first_slice_modules,
        p0_items=p0_items,
        p1_items=p1_items,
        nfrs=nfrs,
        out_of_scope=out_of_scope,
        full_loop=full_loop,
        first_slice_loop=first_slice_loop,
        primary_flow_name=primary_flow_name,
        main_roles=main_roles,
    )
    key_assumption_lines = "\n".join(
        [
            "- assumption_1:",
            f"  - `{primary_segment}` 愿意沿着 `{first_slice_loop}` 使用统一流程，而不是继续依赖线下补位",
            "  - what_changes_if_positive: 当前切片可直接进入设计深化",
            "  - what_changes_if_negative: 需要回退调整首个切片的入口与范围",
            "- assumption_2:",
            f"  - 约束 `{constraints[0]}` 不会阻断 `{primary_flow_name}` 的 MVP 落地",
            "  - what_changes_if_positive: 保持现有架构与审计边界",
            "  - what_changes_if_negative: 需重新排序模块优先级或削减切片范围",
            "- assumption_3:",
            f"  - 延后项 `{out_of_scope[0]}` 不影响 `{minimum_loop}` 的最小成立",
            "  - what_changes_if_positive: 继续把它作为明确 deferred seam 处理",
            "  - what_changes_if_negative: 需要把相关接口或对象提前纳入首版",
        ]
    )
    flow_nodes = [item for item in (first_slice_modules or p0_items)[:3] if item]
    if not flow_nodes:
        flow_nodes = ["source-defined slice A", "source-defined slice B", "source-defined slice C"]
    while len(flow_nodes) < 3:
        flow_nodes.append(flow_nodes[-1])
    slice_map = f"""```mermaid
flowchart LR
    A[{flow_nodes[0]}] --> B[{flow_nodes[1]}]
    B --> C[{flow_nodes[2]}]
    D[Deferred<br/>{preserved_display_label(p2_items[0], fallback='Deferred Seam') if p2_items else 'Deferred Seam'}] -.depends on.-> C
```"""
    return Stage03SlicePlanningContext(
        comparison_rows=planning_lines.comparison_rows,
        nfr_force_lines=planning_lines.nfr_force_lines,
        nfr_relaxed_lines=planning_lines.nfr_relaxed_lines,
        dependency_impact_lines=planning_lines.dependency_impact_lines,
        value_frequency_rows=planning_lines.value_frequency_rows,
        deferred_honesty_rows=planning_lines.deferred_honesty_rows,
        key_assumption_lines=key_assumption_lines,
        flow_nodes=flow_nodes,
        slice_map=slice_map,
    )


def build_stage_03_loop_reasoning_units(
    *,
    first_slice_loop: str,
    full_loop: str,
    minimum_loop: str,
    primary_flow_name: str,
) -> list[dict[str, object]]:
    return [
        build_reasoning_unit(
            "Workflow-Loop Slice Selection", "chosen slice strategy", "structured -> compared -> freeze",
            "first slice could drift into partial capability delivery",
            ("slice comparison + loop-first prioritization", ["MVP slicing by story-map", "value-frequency comparison for contested first-slice items"], "compare module-first, role-workbench-first, and workflow-loop-first against the source dependency chain"),
            (["module-first", "role-workbench-first", "workflow-loop-first"], "smaller isolated scope vs complete first-loop validation", f"selected `{first_slice_loop}` as the first slice backbone"),
            (f"source workflow chain is `{full_loop}`", "partial slices hide real handoff risk", "preserve a complete loop rather than a smaller feature bucket"),
            ("provisional", "whether the current minimum loop is still too wide for implementation", "design and validation must use the same slice boundary", "slice comparison is specific enough to constrain downstream PRD assembly"),
        ),
        build_reasoning_unit(
            "Minimum Loop Guard", "minimum viable experience loop", "structured -> tested -> freeze",
            "removing one key module could break loop closure while still looking deliverable",
            ("dependency-first slicing", ["early-value delivery thinking", "dependency-first slicing logic"], "remove steps mentally and reject any cutline that loses object continuity or explainable completion"),
            ([full_loop, minimum_loop], "narrower scope vs intact business closure", f"kept `{minimum_loop}` as the minimum viable loop"),
            (f"`{primary_flow_name}` depends on ordered module handoff", "removing a core handoff step collapses validation value", "treat the selected loop as indivisible for MVP integrity"),
            ("provisional", "some upstream/downstream modules may still need different seam treatment", "Stage-04 validation should test loop viability, not isolated screens", "loop boundary is explicit and testable"),
        ),
    ]


def build_stage_03_scope_and_dependency_reasoning_units(
    *,
    first_slice_loop: str,
    full_loop: str,
    deferred_scope: str,
) -> list[dict[str, object]]:
    return [
        build_reasoning_unit(
            "Deferred Scope Honesty", "deferred items and carryover ledger", "structured -> audited -> freeze",
            "out-of-scope items could disappear or quietly re-enter MVP",
            ("deferred seam discipline + scope honesty", ["deferral honesty and anti-false-completeness discipline", "source-feature carryover classification"], "classify each deferred item explicitly and keep it visible in seam/backlog language"),
            (["silently drop deferred items", "preserve explicit deferred ledger"], "cleaner MVP story vs honest carryover record", "kept source out-of-scope items explicit in slicing and seam sections"),
            (f"source excludes `{deferred_scope}` from MVP", "silent omission causes false completeness in later review", "every deferred item stays visible with a reason"),
            ("review-bound", "some deferred items may need earlier interface reservation than currently assumed", "architecture may reserve seams, but PRD must not promote them into MVP promise", "scope honesty is explicit enough for review and re-audit"),
        ),
        build_reasoning_unit(
            "NFR-Aware Dependency Ordering", "dependency-first ordering and NFR-aware slice impact", "structured -> stress-tested -> freeze",
            "slice order could look clean while still violating quality or dependency pressure",
            ("dependency ordering + NFR impact alignment", ["structured decomposition discipline", "dependency-first slicing logic"], "re-check the chosen slice against dependency-first ordering and the quality constraints inherited from Stage-02a/02b"),
            (["business-only cutline", "dependency-first and NFR-aware cutline"], "simpler slice story vs implementation-safe ordering", "kept dependency-first ordering and NFR impact visible as part of the chosen slice rationale"),
            (f"`{first_slice_loop}` depends on ordered handoff across `{full_loop}`", "ignoring NFR and dependency pressure creates a fragile MVP story", "Stage-03 keeps dependency and NFR impact explicit in the slice package"),
            ("review-bound", "real build cost may still rebalance some sequence edges", "Stage-04 must validate the same dependency-first assumptions", "ordering pressure is explicit enough for validation planning"),
        ),
    ]


def build_stage_03_reasoning_units(
    *,
    first_slice_loop: str,
    full_loop: str,
    minimum_loop: str,
    primary_flow_name: str,
    out_of_scope: list[str],
    skill_assets: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    stage_skill_assets = skill_assets if skill_assets is not None else load_stage_skill_assets("stage_03")
    deferred_scope = sequence_item_text(out_of_scope, 0, "source-defined deferred scope")
    return build_material_grounded_reasoning_units(
        [
            *build_stage_03_loop_reasoning_units(
                first_slice_loop=first_slice_loop,
                full_loop=full_loop,
                minimum_loop=minimum_loop,
                primary_flow_name=primary_flow_name,
            ),
            *build_stage_03_scope_and_dependency_reasoning_units(
                first_slice_loop=first_slice_loop,
                full_loop=full_loop,
                deferred_scope=deferred_scope,
            ),
        ],
        stage_skill_assets,
    )


def build_stage_03_stage_02b_carryover_context(*, stage_02b_executed: bool) -> Stage03Stage02bCarryoverContext:
    if stage_02b_executed:
        return Stage03Stage02bCarryoverContext(
            upstream_lines="\n".join(
                [
                    "  - Stage-02b `NFR Prioritization Reasoning`",
                    "  - Stage-02b `Object-to-Workflow Mapping`",
                    "  - Stage-02b `Information Architecture Direction`",
                    "  - Stage-02b `Module Interface Payload Contract`",
                    "  - Stage-02b `Deferred Capability Seam`",
                ]
            ),
            availability="yes",
            skip_effect="",
        )
    return Stage03Stage02bCarryoverContext(
        upstream_lines="\n".join(
            [
                "  - Stage-02b skip-stub `NFR Prioritization Reasoning`",
                "  - Stage-02b skip-stub `Object-to-Workflow Mapping`",
                "  - Stage-02b skip-stub `Information Architecture Direction`",
                "  - Stage-02b skip-stub `Module Interface Payload Contract`",
                "  - Stage-02b skip-stub `Deferred Capability Seam`",
            ]
        ),
        availability="no",
        skip_effect="""- stage_02b_skip_effect_on_slicing:
  - This slice can still be chosen safely because the skip stub preserves minimum viable NFR / object / IA signals, but downstream must not assume Stage-02b-level specification freeze has already happened.
""",
    )


def render_stage_03_slice_scope_sections(
    *,
    primary_flow_name: str,
    comparison_rows: list[str],
    p0_items: list[str],
    out_of_scope: list[str],
    full_loop: str,
    minimum_loop: str,
) -> str:
    return f"""## 3. Chosen Slice
- chosen_slice_strategy:
  - `workflow-loop-first`
- why_this_slice_not_that:
  - 单独按模块或角色拆开，都会打断 `{primary_flow_name}` 的对象与状态连续性
  - 先做首个完整业务环，比堆更多能力更能验证产品是否成立

## 4. Slice Alternatives Comparison
{chr(10).join(comparison_rows)}
- why_this_slice_not_that:
  - module-first 会造成局部可用但链路不通。
  - role-workbench-first 容易先做工作台外壳，后补对象关系。
  - workflow-loop-first 是最小但完整的业务闭环，能直接暴露产品是否值得继续投入。

## 5. MVP Scope
- in-scope:
{chr(10).join(f"  - {item}" for item in p0_items)}
- out-of-scope:
{chr(10).join(f"  - {item}" for item in out_of_scope)}

## 6. Complete and Minimum Viable Experience Loop
- complete_experience_loop:
  - {full_loop}
- minimum_viable_experience_loop:
  - {minimum_loop}"""


def render_stage_03_slice_validation_sections(
    *,
    domain_context: dict[str, object],
    p0_items: list[str],
    p1_items: list[str],
    p2_items: list[str],
    out_of_scope: list[str],
    nfr_force_lines: str,
    nfr_relaxed_lines: str,
    dependency_impact_lines: str,
    first_slice_loop: str,
    stage_02b_skip_effect: str,
    upstream_value_loop_block: str,
    value_frequency_rows: str,
    minimum_loop: str,
    deferred_honesty_rows: str,
    key_assumption_lines: str,
    slice_map: str,
    flow_nodes: list[str],
) -> str:
    validation_items = build_stage_03_slice_validation_items(
        domain_context,
        p0_items=p0_items,
        p1_items=p1_items,
        p2_items=p2_items,
    )
    return "\n\n".join(
        [
            render_stage_03_nfr_and_value_validation_sections(
                nfr_force_lines=nfr_force_lines,
                nfr_relaxed_lines=nfr_relaxed_lines,
                dependency_impact_lines=dependency_impact_lines,
                first_slice_loop=first_slice_loop,
                stage_02b_skip_effect=stage_02b_skip_effect,
                upstream_value_loop_block=upstream_value_loop_block,
                value_frequency_rows=value_frequency_rows,
            ),
            render_stage_03_scope_carryover_and_viability_sections(
                domain_context=domain_context,
                validation_items=validation_items,
                out_of_scope=out_of_scope,
                minimum_loop=minimum_loop,
            ),
            render_stage_03_deferred_assumption_and_map_sections(
                deferred_honesty_rows=deferred_honesty_rows,
                key_assumption_lines=key_assumption_lines,
                slice_map=slice_map,
                flow_nodes=flow_nodes,
            ),
        ]
    )


def build_stage_03_slice_validation_items(
    domain_context: dict[str, object],
    *,
    p0_items: list[str],
    p1_items: list[str],
    p2_items: list[str],
) -> Stage03SliceValidationItems:
    first_slice_modules = domain_context.get("first_slice_modules", [])
    first_slice_items = list(first_slice_modules) if isinstance(first_slice_modules, list) else []
    first_slice_items = first_slice_items or p0_items or ["source-defined first slice"]
    later_slice_items = p1_items or ["source-defined later slice"]
    deferred_items = p2_items or ["source-defined deferred item"]
    first_break_item = first_slice_items[0]
    second_break_item = (
        first_slice_items[1]
        if len(first_slice_items) > 1
        else p0_items[0]
        if p0_items
        else "source-defined key step"
    )
    return Stage03SliceValidationItems(
        first_slice_items=first_slice_items,
        later_slice_items=later_slice_items,
        deferred_items=deferred_items,
        first_break_item=first_break_item,
        second_break_item=second_break_item,
    )


def render_stage_03_nfr_and_value_validation_sections(
    *,
    nfr_force_lines: str,
    nfr_relaxed_lines: str,
    dependency_impact_lines: str,
    first_slice_loop: str,
    stage_02b_skip_effect: str,
    upstream_value_loop_block: str,
    value_frequency_rows: str,
) -> str:
    return f"""## 7. NFR-Aware Slice Impact and Dependency-First Logic
- nfr_forcing_into_first_slice:
{nfr_force_lines}
- nfr_relaxed_for_mvp:
{nfr_relaxed_lines}
- domain_dependency_impact:
{dependency_impact_lines}
- dependency_first_chain:
  - {first_slice_loop}
{stage_02b_skip_effect}
- upstream_value_loop_carryover:
{demote_headings(upstream_value_loop_block, 1)}

## 8. Value-Frequency Assessment
| contested capability | value | expected frequency | first-slice decision | reason |
|---|---|---|---|---|
{value_frequency_rows}"""


def render_stage_03_scope_carryover_and_viability_sections(
    *,
    domain_context: dict[str, object],
    validation_items: Stage03SliceValidationItems,
    out_of_scope: list[str],
    minimum_loop: str,
) -> str:
    return f"""## 9. First Slice, Later Slices, and Deferred Items
- first_slice:
{chr(10).join(f"  - {item}" for item in validation_items.first_slice_items)}
- later_slices:
{chr(10).join(f"  - {item}" for item in validation_items.later_slice_items)}
- deferred_items:
{chr(10).join(f"  - {item}" for item in validation_items.deferred_items)}
- explicit_exclusion_rule:
  - 任何无法直接服务 source-defined shortest loop 的能力，不得因“看起来高级”而提前进入 first slice。

## 10. Source Feature Carryover Ledger
- carryover_rule:
  - 源素材中写到的详细能力不得静默消失；每个关键 feature 细节都必须被显式分类为 `first-wave abstraction | later slice | deferred seam | explicit out-of-scope` 之一。
- classification_guard:
  - `first-wave abstraction` 表示用更克制但可交付的形式保留下来；
  - `deferred seam` 表示不做 MVP 承诺，但要保留对象或接口扩展点；
  - `explicit out-of-scope` 表示本波次明确不承诺，防止假完整感。
| source feature detail | classification | preserved form in first-wave PRD | why this classification | downstream note |
|---|---|---|---|---|
{chr(10).join(render_source_feature_rows(domain_context).splitlines()[2:])}

## 11. MVP Loop Viability Test
- is_the_mvp_a_complete_loop:
  - `yes`
- why_it_is_still_a_loop:
  - 用户能沿着 `{minimum_loop}` 完成一次最小但完整的业务闭环，并看到明确的状态与结果交接。
- what_makes_it_minimum:
  - 移除了 `{', '.join(out_of_scope[:3])}` 等延后项，但保留了让业务闭环成立的最小链路。
- what_would_break_viability:
  - 移除 `{validation_items.first_break_item}`：首个切片失去起点。
  - 移除 `{validation_items.second_break_item}`：对象交接会断裂。
  - 移除末端状态确认：团队无法判断是否继续投入。"""


def render_stage_03_deferred_assumption_and_map_sections(
    *,
    deferred_honesty_rows: str,
    key_assumption_lines: str,
    slice_map: str,
    flow_nodes: list[str],
) -> str:
    return f"""## 12. Deferred Items Honesty Check
| item | why_not_in_mvp | what_would_falsely_make_mvp_look_complete | impact_of_deferral |
|---|---|---|---|
{deferred_honesty_rows}

## 13. Key Assumptions to Validate
{key_assumption_lines}

## 14. Slice Map and Dependency View
{slice_map}
- acceptance_targets_per_slice:
  - Slice A: 用户能完成 `{flow_nodes[0]}` 并建立后续流程起点
  - Slice B: 用户能从 `{flow_nodes[1]}` 进入下一步而不重建上下文
  - Slice C: 用户能在 `{flow_nodes[2]}` 看到可解释的结果状态

## 15. Deepening Loop Log
- loop_state:
  - `S-review-bound-freeze`
- rounds_executed:
  - 3
  - round_log:
  - round_1:
    - trigger: `need to prove this is a loop, not a reduced backlog`
    - artifact_unit_improved: `slice alternatives comparison`
    - what_was_refined: `workflow-loop-first vs module-first`
    - outcome: `continue`
  - round_2:
    - trigger: `Stage-02b constraints were underused`
    - artifact_unit_improved: `NFR-aware slice impact + dependency-first ordering`
    - what_was_refined: `source NFR / constraints effects on cutline`
    - outcome: `continue`
  - round_3:
    - trigger: `deferred items still looked cosmetic`
    - artifact_unit_improved: `deferred honesty + assumption carryover`
    - what_was_refined: `false-completeness risk of source-defined out-of-scope items`
    - outcome: `freeze`"""


def render_stage_03_evidence_summary_sections(
    *,
    reasoning_units: list[dict[str, str | list[str]]],
    context: dict[str, object],
    skill_assets: dict[str, object],
    upstream_evidence_blocks: list[str],
    source_evidence_blocks: list[str],
) -> str:
    return render_evidence_chain_sections(
        ledger_heading="## 16. Minimal Reasoning Unit Ledger",
        material_heading="## 17. Material Grounding Bridge",
        snapshot_heading="## 18. Skill Asset Ingestion Snapshot",
        method_heading="## 19. Method Activation Evidence",
        upstream_heading="## 20. Upstream Stage Carryover Evidence",
        source_heading="## 21. Source Evidence Pack",
        reasoning_units=reasoning_units,
        context=context,
        skill_assets=skill_assets,
        snapshot_runtime_use_rules=[
            "at least two slice candidates were compared before freeze",
            "deferred honesty remained explicit instead of collapsing into roadmap placeholders",
            "dependency-first and NFR-aware logic materially changed the cutline",
            "source feature details were explicitly classified instead of silently disappearing from the MVP story",
            "upstream structure and specification artifacts were carried into the slicing decision",
        ],
        upstream_evidence_blocks=upstream_evidence_blocks,
        source_evidence_blocks=source_evidence_blocks,
    )


def build_stage_03_evidence_context(
    source_bundle: Stage03SourceBundle,
    stage_02a_text: str,
    stage_02b_text: str,
) -> Stage03EvidenceContext:
    return Stage03EvidenceContext(
        upstream_value_loop_block=find_named_h2_block(stage_02a_text, ["Value Loop and Downstream Preservation Notes"]),
        upstream_evidence_blocks=[
            find_named_h2_block(stage_02a_text, ["Constraint Stress-Test"]),
            find_named_h2_block(stage_02a_text, ["Priority Split"]),
            find_named_h2_block(stage_02a_text, ["Structure Stress-Test and Deepening Loop Log"]),
            find_named_h2_block(stage_02b_text, ["NFR Prioritization Reasoning"]),
            find_named_h2_block(stage_02b_text, ["Object-to-Workflow Mapping"]),
            find_named_h2_block(stage_02b_text, ["Information Architecture Direction"]),
            find_named_h2_block(stage_02b_text, ["Module Interface Payload Contract"]),
            find_named_h2_block(stage_02b_text, ["Deferred Capability Seam"]),
        ],
        source_evidence_blocks=[
            source_bundle.h51,
            source_bundle.h52,
            source_bundle.h53,
            source_bundle.h7p0,
            source_bundle.h7p1,
            source_bundle.h7p2,
            source_bundle.h8,
        ],
    )


def build_stage_03_render_context(
    source_text: str,
    stage_02a_text: str,
    stage_02b_text: str,
    *,
    stage_02b_executed: bool,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> Stage03RenderContext:
    source_bundle = build_stage_03_source_bundle(source_text, source_snapshot=source_snapshot)
    slice_planning_context = build_stage_03_slice_planning_context(
        domain_context=source_bundle.context,
        p0_items=source_bundle.p0_items,
        p1_items=source_bundle.p1_items,
        p2_items=source_bundle.p2_items,
        nfrs=source_bundle.nfrs,
        out_of_scope=source_bundle.out_of_scope,
        full_loop=source_bundle.full_loop,
        first_slice_loop=source_bundle.first_slice_loop,
        minimum_loop=source_bundle.minimum_loop,
        primary_flow_name=source_bundle.primary_flow_name,
        primary_segment=source_bundle.primary_segment,
        main_roles=source_bundle.main_roles,
        constraints=source_bundle.constraints,
    )
    skill_assets = load_stage_skill_assets("stage_03")
    reasoning_units = build_stage_03_reasoning_units(
        first_slice_loop=source_bundle.first_slice_loop,
        full_loop=source_bundle.full_loop,
        minimum_loop=source_bundle.minimum_loop,
        primary_flow_name=source_bundle.primary_flow_name,
        out_of_scope=source_bundle.out_of_scope,
        skill_assets=skill_assets,
    )
    stage_02b_carryover_context = build_stage_03_stage_02b_carryover_context(stage_02b_executed=stage_02b_executed)
    return Stage03RenderContext(
        source_bundle=source_bundle,
        slice_planning_context=slice_planning_context,
        stage_02b_carryover_context=stage_02b_carryover_context,
        evidence_context=build_stage_03_evidence_context(source_bundle, stage_02a_text, stage_02b_text),
        skill_assets=skill_assets,
        reasoning_units=reasoning_units,
    )


def render_stage_03_opening_and_scope_sections(
    render_context: Stage03RenderContext,
    *,
    version: str,
    owner: str,
) -> str:
    source_bundle = render_context.source_bundle
    business_world_model = source_bundle.business_world_model
    product_label = source_bundle.product_label
    out_of_scope = source_bundle.out_of_scope
    p0_items = source_bundle.p0_items
    full_loop = source_bundle.full_loop
    minimum_loop = source_bundle.minimum_loop
    primary_flow_name = source_bundle.primary_flow_name
    slice_planning_context = render_context.slice_planning_context
    comparison_rows = slice_planning_context.comparison_rows
    stage_02b_carryover_context = render_context.stage_02b_carryover_context
    stage_02b_upstream_lines = stage_02b_carryover_context.upstream_lines
    stage_02b_availability = stage_02b_carryover_context.availability

    return f"""{render_stage_document_opening(
    stage_display="Stage-03",
    stage_slug="requirements-decomposition-and-mvp-slicing",
    document_suffix="MVP Slicing",
    product_label=product_label,
    version=version,
    owner=owner,
)}

{render_traceability_block("stage_03")}

{render_semantic_authoring_spine_section(business_world_model)}

## 2. Context and Objective
- current_product_goal:
  - 把 `{full_loop}` 切成一个既能验证业务闭环、又不会因过早承诺而失真的 first slice。
- why_slicing_is_needed:
  - Stage-02 已把产品结构组织成 workflow-first，但仍需把 `{primary_flow_name}` 所在链路切成可验证、可解释、可 handoff 的 MVP。
- upstream_artifacts_materially_used:
  - Stage-02a `Value Loop and Downstream Preservation Notes`
  - Stage-02a `Constraint Stress-Test`
  - Stage-02a `Priority Split`
{stage_02b_upstream_lines}
- stage_02b_available:
  - `{stage_02b_availability}`

{render_stage_03_slice_scope_sections(
    primary_flow_name=primary_flow_name,
    comparison_rows=comparison_rows,
    p0_items=p0_items,
    out_of_scope=out_of_scope,
    full_loop=full_loop,
    minimum_loop=minimum_loop,
)}
"""


def render_stage_03_validation_sections(render_context: Stage03RenderContext) -> str:
    source_bundle = render_context.source_bundle
    slice_planning_context = render_context.slice_planning_context
    return render_stage_03_slice_validation_sections(
        domain_context=source_bundle.context,
        p0_items=source_bundle.p0_items,
        p1_items=source_bundle.p1_items,
        p2_items=source_bundle.p2_items,
        out_of_scope=source_bundle.out_of_scope,
        nfr_force_lines=slice_planning_context.nfr_force_lines,
        nfr_relaxed_lines=slice_planning_context.nfr_relaxed_lines,
        dependency_impact_lines=slice_planning_context.dependency_impact_lines,
        first_slice_loop=source_bundle.first_slice_loop,
        stage_02b_skip_effect=render_context.stage_02b_carryover_context.skip_effect,
        upstream_value_loop_block=render_context.evidence_context.upstream_value_loop_block,
        value_frequency_rows=slice_planning_context.value_frequency_rows,
        minimum_loop=source_bundle.minimum_loop,
        deferred_honesty_rows=slice_planning_context.deferred_honesty_rows,
        key_assumption_lines=slice_planning_context.key_assumption_lines,
        slice_map=slice_planning_context.slice_map,
        flow_nodes=slice_planning_context.flow_nodes,
    )


def render_stage_03_evidence_tail_sections(render_context: Stage03RenderContext) -> str:
    return render_stage_03_evidence_summary_sections(
        reasoning_units=render_context.reasoning_units,
        context=render_context.source_bundle.context,
        skill_assets=render_context.skill_assets,
        upstream_evidence_blocks=render_context.evidence_context.upstream_evidence_blocks,
        source_evidence_blocks=render_context.evidence_context.source_evidence_blocks,
    )


def render_stage_03_document(
    render_context: Stage03RenderContext,
    *,
    version: str,
    owner: str,
) -> str:
    return "\n\n".join(
        [
            render_stage_03_opening_and_scope_sections(render_context, version=version, owner=owner),
            render_stage_03_validation_sections(render_context),
            render_stage_03_evidence_tail_sections(render_context),
        ]
    )


def build_stage_03(
    source_text: str,
    stage_02a_text: str,
    stage_02b_text: str,
    *,
    stage_02b_executed: bool,
    version: str,
    owner: str,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> str:
    return render_stage_03_document(
        build_stage_03_render_context(
            source_text,
            stage_02a_text,
            stage_02b_text,
            stage_02b_executed=stage_02b_executed,
            source_snapshot=source_snapshot,
        ),
        version=version,
        owner=owner,
    )


def build_stage_04_source_bundle(
    source_text: str,
    stage_03_text: str,
    *,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> Stage04SourceBundle:
    snapshot = source_snapshot or build_phase1_source_snapshot(source_text)
    sections = snapshot.sections
    context = snapshot.context
    product_label = snapshot.product_label
    segments = snapshot.segments
    primary_segment = snapshot.primary_segment
    roles = snapshot.roles
    modules = snapshot.modules
    flows = snapshot.flows
    objectives = context["objectives"] or ["validate the source-defined first-wave workflow"]
    constraints = context["constraints"] or ["source-defined architectural constraint"]
    out_of_scope = context["out_of_scope"] or ["source-defined deferred item"]
    module_chain = snapshot.module_chain
    primary_flow_name = snapshot.primary_flow_name
    validation_plan = build_stage_04_validation_plan(
        stage_03_text,
        primary_flow_name=primary_flow_name,
        primary_segment=str(primary_segment),
        module_chain=module_chain,
    )
    return Stage04SourceBundle(
        h61=sections.h61,
        h62=sections.h62,
        h9=sections.h9,
        h10=sections.h10,
        h12=sections.h12,
        context=context,
        product_label=str(product_label),
        segments=list(segments),
        primary_segment=str(primary_segment),
        roles=list(roles),
        modules=list(modules),
        flows=list(flows),
        objectives=list(objectives),
        constraints=list(constraints),
        out_of_scope=list(out_of_scope),
        module_chain=module_chain,
        primary_flow_name=primary_flow_name,
        stage03_assumptions=validation_plan.stage03_assumptions,
        validation_targets=validation_plan.validation_targets,
        method_rows=validation_plan.method_rows,
    )


def build_stage_04_reasoning_units(
    *,
    validation_targets: list[dict[str, str]],
    objectives: list[str],
    skill_assets: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    stage_skill_assets = skill_assets if skill_assets is not None else load_stage_skill_assets("stage_04")
    target_ids = [target["id"] for target in validation_targets[:4] if target.get("id")] or ["target_1"]
    primary_objective = sequence_item_text(objectives, 0, "source-defined validation objective")
    return build_material_grounded_reasoning_units(
        [
            build_reasoning_unit(
                "Exact-Assumption Validation Targeting", "validation targets", "structured -> clarified -> freeze",
                "validation scope could remain generic instead of tied to explicit assumptions",
                ("assumption-first validation targeting", ["validated learning loop", "exact-assumption-first validation targeting"], "derive validation targets directly from Stage-03 assumptions and preserve their positive/negative consequence"),
                (target_ids, "shorter plan vs exact learning target clarity", "validation targets now inherit Stage-03 assumption structure directly"),
                ("Stage-03 already names the assumptions most likely to change the slice decision", "validation is only useful when each target has a concrete downstream consequence", "Stage-04 keeps assumption-first structure instead of inventing new target themes"),
                ("provisional", "real evidence collection has not happened yet", "prototype and interview preparation should follow the same target ids", "validation targets are specific enough to execute without more rewriting"),
            ),
            build_reasoning_unit(
                "Method and Fidelity Fit", "method-fit comparison", "structured -> compared -> freeze",
                "method choice could drift into habit instead of target fit",
                ("method-fit comparison + fidelity choice", ["prototype/validation linkage", "method-fit comparison"], "map each assumption to the lightest method that still exposes pass/fail evidence"),
                (["clickable walkthrough", "architecture review", "role-comparison interview"], "stronger evidence vs lower cost and faster setup", "selected a mixed validation plan driven by assumption type rather than one fixed method for all targets"),
                ("assumptions span workflow comprehension, constraint fit, and role boundary fit", "one validation method cannot answer all target types equally well", "use method bundles matched to the assumption category"),
                ("provisional", "some targets may still need a richer prototype if early signals are ambiguous", "research preparation should keep artifacts aligned with target type", "method-fit is explicit enough for the next execution round"),
            ),
            build_reasoning_unit(
                "Evidence Honesty and Revision Consequence", "decision state and forbidden assumptions", "structured -> bounded -> freeze",
                "downstream teams could misread validation planning as validated truth",
                ("evidence honesty + revision consequence mapping", ["build-measure-learn loop", "evidence-honesty before decision declaration"], "separate source-grounded structure from real validation evidence and attach failure consequences per target"),
                (["treat the pack as validated", "keep revise-state honesty visible"], "cleaner readiness story vs audit-safe honesty", "kept Stage-04 in revise-state while still allowing downstream-safe exploration"),
                (f"source provides validation input through section 6 and `{primary_objective}`", "design and architecture may start before validation finishes, but must not assume proof already exists", "keep forbidden assumptions explicit in the output"),
                ("review-bound", "actual user evidence may still overturn the current slice or boundary choice", "PRD convergence may proceed, but implementation commitment remains blocked", "decision and revision logic are explicit enough for review"),
            ),
            build_reasoning_unit(
                "Convergence Admission and Stage Coupling", "convergence readiness and Stage-02b execution coupling", "structured -> admitted -> freeze",
                "downstream teams could start convergence without checking whether Stage-02b and validation pack stay coupled",
                ("convergence admission + dependency coupling review", ["exact-assumption-first validation targeting", "evidence-honesty before decision declaration"], "check whether validation targets, Stage-02b execution state, and convergence readiness remain mutually consistent"),
                (["treat convergence as automatic", "gate convergence on explicit stage coupling"], "faster PRD convergence vs audit-safe dependency honesty", "allowed ready-to-converge output while preserving explicit Stage-02b coupling and blocked assumptions"),
                ("Stage-04 must declare whether Stage-02b was executed and what that means downstream", "convergence without coupling declarations creates false delivery confidence", "keep convergence admission tied to stage coupling and validation state"),
                ("review-bound", "later evidence may still tighten convergence rules", "PRD assembly and execution report should preserve the same convergence admission language", "stage coupling is explicit enough for downstream convergence"),
            ),
        ],
        stage_skill_assets,
    )


def build_stage_04_maturity_rows(
    *,
    module_chain: str,
    primary_segment: str,
    constraints: list[str],
) -> list[dict[str, str]]:
    primary_constraint = sequence_item_text(constraints, 0, "source-defined constraint")
    return [
        {
            "subject": f"workflow backbone `{module_chain}`",
            "delivery_readiness_state": "downstream-start-safe",
            "evidence_confidence_state": "source-grounded-but-unvalidated",
            "current_basis": f"Stage-02a/03 已将 `{module_chain}` 固化为当前主链路，Stage-04 为其定义了 validation targets 与 pass/fail consequence。",
            "blocker_to_next_delivery_state": "还缺 prototype detail、state coverage 和 interface hardening",
            "blocker_to_next_evidence_state": "还缺真实 walkthrough / interview / constraint review evidence",
            "safe_downstream_action": "设计可围绕主流程继续细化原型；架构可保留对象链与审计边界",
            "forbidden_assumptions": "workflow viability already validated",
        },
        {
            "subject": f"first-wave boundary `{primary_segment}`",
            "delivery_readiness_state": "review-ready",
            "evidence_confidence_state": "design-time-inference-heavy",
            "current_basis": "当前边界来自 Stage-01/03 的 source-driven 选择与 assumption carryover，而非真实对比访谈。",
            "blocker_to_next_delivery_state": "还缺多角色对比与首发边界复核",
            "blocker_to_next_evidence_state": "还缺 role-comparison interview evidence",
            "safe_downstream_action": "可继续按当前主边界推进，但必须保留回退可能",
            "forbidden_assumptions": "primary boundary already validated",
        },
        {
            "subject": "constraint-fit and auditability",
            "delivery_readiness_state": "downstream-start-safe",
            "evidence_confidence_state": "source-grounded-but-unvalidated",
            "current_basis": f"source 已明确给出 `{primary_constraint}` 等约束，Stage-04 已把它们转成显式 validation target。",
            "blocker_to_next_delivery_state": "还缺 architecture review 与 implementation-facing constraint mapping",
            "blocker_to_next_evidence_state": "还缺真实技术评审或 spike evidence",
            "safe_downstream_action": "架构可先做约束映射和审计事件边界设计",
            "forbidden_assumptions": "constraint fit already proven",
        },
        {
            "subject": "deferred scope honesty",
            "delivery_readiness_state": "review-ready",
            "evidence_confidence_state": "review-bound",
            "current_basis": "Stage-03 已明确给出 deferred-items cutline，Stage-04 继续保留同样的延期诚实边界。",
            "blocker_to_next_delivery_state": "还缺 future seam 与 PRD 收口规则的最终确认",
            "blocker_to_next_evidence_state": "还缺真实优先级与实施成本佐证",
            "safe_downstream_action": "仅允许保留 seam/backlog，不允许回写进 MVP promise",
            "forbidden_assumptions": "deferred scope can silently enter MVP",
        },
    ]


def build_stage_04_stage_02b_execution_context(*, stage_02b_executed: bool) -> Stage04Stage02bExecutionContext:
    if stage_02b_executed:
        return Stage04Stage02bExecutionContext(
            upstream_lines="\n".join(
                [
                    "  - Stage-03 `Chosen Slice`",
                    "  - Stage-03 `NFR-Aware Slice Impact and Dependency-First Logic`",
                    "  - Stage-03 `Key Assumptions to Validate`",
                    "  - Stage-03 `Deferred Items Honesty Check`",
                ]
            ),
            state_block="""- stage_02b_execution_state:
  - `executed`
- handoff_nfr_state:
  - `present`
- handoff_nfr_notes:
  - Stage-02b 已提供 quality scenario matrix、metric register、module responsibility 与 payload contract。
- stage_02b_skip_declaration:
  - not required because Stage-02b was executed in full for this run""",
        )
    return Stage04Stage02bExecutionContext(
        upstream_lines="\n".join(
            [
                "  - Stage-02a `NFR Initial Identification`",
                "  - Stage-03 `Chosen Slice`",
                "  - Stage-03 `NFR-Aware Slice Impact and Dependency-First Logic`",
                "  - Stage-03 `Key Assumptions to Validate`",
                "  - Stage-03 `Deferred Items Honesty Check`",
            ]
        ),
        state_block="""- stage_02b_execution_state:
  - `skipped`
- handoff_nfr_state:
  - `stage-02a-initial-identification-only`
- handoff_nfr_notes:
  - 本次未执行完整 Stage-02b deepening；下游当前拿到的是 Stage-02a 的 NFR initial identification + Stage-02b skip stub 中的最小可消费 fallback。
- stage_02b_skip_declaration:
  - nfr_source: `Stage-02a NFR Initial Identification + Stage-02b skip stub`
  - domain_model_state: `partial-from-02a`
  - ia_direction_state: `partial-from-02a`
  - impact_on_phase2: `Phase-2 可以在当前对象链和 workflow-first IA 上安全启动，但必须把 full quality scenario matrix、metric contract hardening、IA state coverage hardening 纳入自己的首波架构发现任务。`
  - minimum_viable_for_phase2: `yes`
  - mitigation_note: `Phase-2 不得假定 Stage-02b 已冻结；它必须把 NFR / domain / IA deepening 作为显式 architecture discovery workstream，而不是隐式补锅。`""",
    )


def render_stage_04_validation_plan_sections(
    *,
    validation_targets: list[dict[str, str]],
    method_rows: list[str],
    primary_flow_name: str,
    module_chain: str,
) -> str:
    validation_target_lines = "\n".join(
        f"- {item['id']}:\n  - Target {idx}: {item['assumption']}"
        for idx, item in enumerate(validation_targets, start=1)
    )
    validation_clarity_rows = "\n".join(
        f"| {item['id']} | {item['assumption']} | {item.get('positive', 'preserve current direction')} | "
        f"{item.get('negative', 'revise the current slice or boundary')} | {item['dimension']} |"
        for item in validation_targets
    )
    method_rows_text = "\n".join(method_rows)
    signal_threshold_lines = "\n".join(
        f"  - {item['id']}: {item['threshold']}" for item in validation_targets[:5]
    )
    validation_plan_rows = "\n".join(
        f"| {item['id']} | {item['method']} | {item['artifact']} | {item['threshold']} | "
        f"{item.get('positive', 'preserve current direction')} | {item.get('negative', 'revise current direction')} |"
        for item in validation_targets
    )
    unknown_lines = "\n".join(f"  - {item['assumption']}" for item in validation_targets[:5])
    return f"""## 3. Validation Targets
{validation_target_lines}

## 4. Validation Target Clarity
| target | exact_assumption_tested | what_changes_if_positive | what_changes_if_negative | primary dimension |
|---|---|---|---|---|
{validation_clarity_rows}

## 5. Method-Fit Comparison
| candidate method | fit_to_target | cost_and_speed | evidence_quality | why_not_chosen_or_chosen |
|---|---|---|---|---|
{method_rows_text}
- chosen_method:
  - mixed method bundle driven by assumption type
- why_this_method_not_that:
  - 当前最关键的是让不同类型的假设各自进入最合适的验证方式，而不是用单一方法覆盖所有未知。

## 6. Prototype Fidelity Record
- fidelity_chosen:
  - `mixed`
- fidelity_rationale:
  - workflow 理解用 clickable，约束适配用 structured review，角色边界用 interview；不同假设不强行绑定同一保真度。
- prototype_or_equivalent_artifact:
  - `{primary_flow_name}` prototype path + workflow constraint checklist + segment comparison sheet

## 7. Method and Signal Definition
- method:
  - mixed method bundle
- signal thresholds:
{signal_threshold_lines}

## 8. Validation Plan and Signal Chain
| target | method | artifact | threshold | learning_if_pass | learning_if_fail |
|---|---|---|---|---|---|
{validation_plan_rows}

## 9. Validation Dimensions Covered
- value_dimension:
  - verdict: `partially-validated`
  - evidence_summary: 目前更多是基于 Stage-03 assumptions 的结构性推断，真实用户信号仍待收集。
- usability_dimension:
  - verdict: `not-tested`
  - evidence_summary: 还没有真实 walkthrough 反馈，只有 source-driven prototype planning。
- feasibility_dimension:
  - verdict: `partially-validated`
  - evidence_summary: 已有 review-bound 技术/流程判断，但尚无正式 architecture review 与实现级 spike。
- dimensions_gap_note:
  - 下游可以开始设计/架构探索，但不能把这些 assumption targets 视为已验证事实。

## 10. Evidence State Honesty
- what_is_design_time_inference:
  - `{module_chain}` 是当前最合理的 first-wave workflow backbone。
  - `{primary_flow_name}` 对应的 prototype path 足以支撑第一轮验证准备。
- what_is_real_evidence:
  - source 已明确给出目标用户、模块链路、关键流程、约束和 section 6 的验证输入。
- what_remains_unknown:
{unknown_lines}"""


def render_stage_04_decision_handoff_sections(
    *,
    validation_targets: list[dict[str, str]],
    stage_02b_state_block: str,
) -> str:
    revision_consequence_lines = "\n".join(
        f"  - 若 `{item['id']}` 失败：{item.get('negative', 'revise current direction')}"
        for item in validation_targets[:5]
    )
    carryover_truth_lines = "\n".join(f"  - {item['assumption']}" for item in validation_targets[:3])
    return f"""## 12. Decision State and Revision Consequences
- decision: `Revise`
- reasoning:
  - 结构和主文档已足够支持设计/架构探索，但 validation chain 仍缺真实 evidence，因此不能给 Go。
- revision_consequences:
{revision_consequence_lines}
- what_downstream_must_not_assume:
  - 需求已验证
  - 主流程已真实跑通
  - 关键约束已被实现验证
  - 延后项可以安全提前进入 MVP

## 13. Review-Bound Carryover and Forbidden Assumptions
- must_not_assume:
  - 需求已验证
  - 主流程已真实跑通
  - 关键约束已被实现验证
- carryover_truths:
{carryover_truth_lines}

## 14. Stage-02b Execution State Declaration
{stage_02b_state_block}

## 15. Validation Flow
```mermaid
flowchart LR
    A[Exact Assumption] --> B[Chosen Method]
    B --> C[Prototype / Artifact]
    C --> D[Signal / Threshold]
    D --> E[Evidence Interpretation]
    E --> F[Decision State]
    F --> G[Revision Consequence]
```

## 16. Unified Product Pack / PRD Convergence Readiness
- unified_product_pack_status:
  - `ready-to-converge`
- rationale:
  - Stage-03 的切片逻辑已足够明确，Stage-04 也已把关键假设、方法、阈值、decision consequence 显式化，因此可进入 PRD convergence；但 readiness 不等于需求已经验证完成。

## 17. Deepening Loop Log
- loop_state:
  - `S-review-bound-freeze`
- rounds_executed:
  - 3
- round_log:
  - round_1:
    - trigger: `validation targets were too slogan-like`
    - artifact_unit_improved: `validation target clarity`
    - what_was_refined: `derive targets directly from Stage-03 assumptions`
    - outcome: `continue`
  - round_2:
    - trigger: `method choice had no real comparison`
    - artifact_unit_improved: `method-fit comparison + prototype fidelity`
    - what_was_refined: `compare method options and chosen signal chain`
    - outcome: `continue`
  - round_3:
    - trigger: `decision consequences were implicit`
    - artifact_unit_improved: `revision consequences + downstream forbidden assumptions`
    - what_was_refined: `explicit pass/fail meaning for downstream planning`
    - outcome: `freeze with review-bound honesty`
"""


def render_stage_04_evidence_summary_sections(
    *,
    reasoning_units: list[dict[str, str | list[str]]],
    context: dict[str, object],
    skill_assets: dict[str, object],
    upstream_evidence_blocks: list[str],
    source_evidence_blocks: list[str],
) -> str:
    return render_evidence_chain_sections(
        ledger_heading="## 18. Minimal Reasoning Unit Ledger",
        material_heading="## 19. Material Grounding Bridge",
        snapshot_heading="## 20. Skill Asset Ingestion Snapshot",
        method_heading="## 21. Method Activation Evidence",
        upstream_heading="## 22. Upstream Stage Carryover Evidence",
        source_heading="## 23. Source Evidence Pack",
        reasoning_units=reasoning_units,
        context=context,
        skill_assets=skill_assets,
        snapshot_runtime_use_rules=[
            "exact assumptions were defined before method selection",
            "method choices were compared rather than assumed",
            "evidence honesty and decision consequence both remained explicit",
            "Stage-03 assumptions and deferred honesty were carried into validation design",
        ],
        upstream_evidence_blocks=upstream_evidence_blocks,
        source_evidence_blocks=source_evidence_blocks,
    )


def build_stage_04_render_context(
    source_text: str,
    stage_02a_text: str,
    stage_03_text: str,
    *,
    stage_02b_executed: bool,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> Stage04RenderContext:
    source_bundle = build_stage_04_source_bundle(source_text, stage_03_text, source_snapshot=source_snapshot)
    skill_assets = load_stage_skill_assets("stage_04")
    reasoning_units = build_stage_04_reasoning_units(
        validation_targets=source_bundle.validation_targets,
        objectives=source_bundle.objectives,
        skill_assets=skill_assets,
    )
    maturity_rows = build_stage_04_maturity_rows(
        module_chain=source_bundle.module_chain,
        primary_segment=source_bundle.primary_segment,
        constraints=source_bundle.constraints,
    )
    stage_02b_execution_context = build_stage_04_stage_02b_execution_context(stage_02b_executed=stage_02b_executed)
    upstream_evidence_blocks = [
        find_named_h2_block(stage_02a_text, ["NFR Initial Identification"]),
        find_named_h2_block(stage_03_text, ["Chosen Slice"]),
        find_named_h2_block(stage_03_text, ["NFR-Aware Slice Impact and Dependency-First Logic"]),
        find_named_h2_block(stage_03_text, ["Key Assumptions to Validate"]),
        find_named_h2_block(stage_03_text, ["Deferred Items Honesty Check"]),
    ]
    source_evidence_blocks = [
        source_bundle.h61,
        source_bundle.h62,
        source_bundle.h9,
        source_bundle.h10,
        source_bundle.h12,
    ]
    return Stage04RenderContext(
        source_bundle=source_bundle,
        stage_02b_execution_context=stage_02b_execution_context,
        upstream_evidence_blocks=upstream_evidence_blocks,
        source_evidence_blocks=source_evidence_blocks,
        skill_assets=skill_assets,
        reasoning_units=reasoning_units,
        maturity_rows=maturity_rows,
    )


def render_stage_04_document(
    render_context: Stage04RenderContext,
    *,
    version: str,
    owner: str,
) -> str:
    source_bundle = render_context.source_bundle

    return f"""{render_stage_document_opening(
    stage_display="Stage-04",
    stage_slug="requirements-validation-and-concept-proof",
    document_suffix="Validation",
    product_label=source_bundle.product_label,
    version=version,
    owner=owner,
)}

{render_traceability_block("stage_04")}

## 2. Context and Objective
- current_validation_target:
  - 验证 Stage-03 选择的 `{source_bundle.module_chain}` 首个切片是否值得继续作为设计/架构主线。
- validation_objective:
  - 把 Stage-03 的关键假设转成可判定的验证链，而不是继续停留在结构性推断。
- upstream_stage_materially_used:
{render_context.stage_02b_execution_context.upstream_lines}

{render_stage_04_validation_plan_sections(
    validation_targets=source_bundle.validation_targets,
    method_rows=source_bundle.method_rows,
    primary_flow_name=source_bundle.primary_flow_name,
    module_chain=source_bundle.module_chain,
)}

{render_maturity_confidence_section(
    "## 11. Delivery Readiness and Evidence Confidence",
    document_delivery_state="downstream-start-safe",
    evidence_confidence_state="source-grounded-but-unvalidated",
    safe_start_scope=[
        f"设计可以启动 `{source_bundle.primary_flow_name}` 的 workflow prototype 与关键页面表达",
        f"架构可以启动 `{source_bundle.module_chain}` 的 object chain / audit boundary 设计",
        "产品可以继续准备 interviews、constraint review 和 comparison artifacts",
    ],
    blocked_commitments=[
        "不得把当前文档当作 implementation-commit-ready 需求冻结包",
        "不得承诺 Stage-03 assumptions 已经被真实证据证明",
        "不得承诺客群、约束适配或流程可理解性已全部验证完成",
    ],
    rows=render_context.maturity_rows,
)}

{render_stage_04_decision_handoff_sections(
    validation_targets=source_bundle.validation_targets,
    stage_02b_state_block=render_context.stage_02b_execution_context.state_block,
)}

{render_stage_04_evidence_summary_sections(
    reasoning_units=render_context.reasoning_units,
    context=source_bundle.context,
    skill_assets=render_context.skill_assets,
    upstream_evidence_blocks=render_context.upstream_evidence_blocks,
    source_evidence_blocks=render_context.source_evidence_blocks,
)}
"""


def build_stage_04(
    source_text: str,
    stage_02a_text: str,
    stage_03_text: str,
    *,
    stage_02b_executed: bool,
    version: str,
    owner: str,
    source_snapshot: Phase1SourceSnapshot | None = None,
) -> str:
    return render_stage_04_document(
        build_stage_04_render_context(
            source_text,
            stage_02a_text,
            stage_03_text,
            stage_02b_executed=stage_02b_executed,
            source_snapshot=source_snapshot,
        ),
        version=version,
        owner=owner,
    )


def build_phase1_deep_stage_texts(
    source_text: str,
    *,
    version: str,
    owner: str,
    skip_stage_02b: bool,
) -> Phase1DeepStageTexts:
    source_snapshot = build_phase1_source_snapshot(source_text)
    stage_01_text = build_stage_01(source_text, version, owner, source_snapshot=source_snapshot)
    stage_02a_text = build_stage_02a(source_text, version, owner, source_snapshot=source_snapshot)
    stage_02b_text = (
        build_stage_02b_skip_stub(source_text, stage_02a_text, version, owner, source_snapshot=source_snapshot)
        if skip_stage_02b
        else build_stage_02b(source_text, version, owner, source_snapshot=source_snapshot)
    )
    stage_03_text = build_stage_03(
        source_text,
        stage_02a_text,
        stage_02b_text,
        stage_02b_executed=not skip_stage_02b,
        version=version,
        owner=owner,
        source_snapshot=source_snapshot,
    )
    stage_04_text = build_stage_04(
        source_text,
        stage_02a_text,
        stage_03_text,
        stage_02b_executed=not skip_stage_02b,
        version=version,
        owner=owner,
        source_snapshot=source_snapshot,
    )
    return Phase1DeepStageTexts(
        stage_01_text=stage_01_text,
        stage_02a_text=stage_02a_text,
        stage_02b_text=stage_02b_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
    )


def write_business_world_model_artifacts(
    output_dir: Path,
    business_world_model: dict[str, object],
) -> BusinessWorldModelArtifactPaths:
    paths = BusinessWorldModelArtifactPaths(
        business_world_model=output_dir / PHASE1_BUSINESS_WORLD_MODEL_FILENAME,
        semantic_authoring_spine=output_dir / ".phase1-evidence" / "p1-semantic-authoring-spine.json",
        operating_baseline_model=output_dir / PHASE1_OPERATING_BASELINE_MODEL_FILENAME,
        product_world_decision=output_dir / PHASE1_PRODUCT_WORLD_DECISION_FILENAME,
        business_release_truth_pack=output_dir / PHASE1_BUSINESS_RELEASE_TRUTH_PACK_FILENAME,
        planning_control_truth_pack=output_dir / PHASE1_PLANNING_CONTROL_TRUTH_PACK_FILENAME,
        business_exploration_arena_json=output_dir / "business-exploration-arena.json",
        business_exploration_arena_md=output_dir / "business-exploration-arena.md",
        commercial_argument_draft_json=output_dir / "commercial-argument-draft.json",
        commercial_argument_draft_md=output_dir / "commercial-argument-draft.md",
        chosen_business_thesis_json=output_dir / "chosen-business-thesis.json",
        chosen_business_thesis_md=output_dir / "chosen-business-thesis.md",
    )
    for path, payload in {
        paths.business_world_model: business_world_model,
        paths.semantic_authoring_spine: semantic_authoring_spine_from_model(business_world_model),
        paths.operating_baseline_model: business_world_model.get("operating_baseline_model", {}),
        paths.product_world_decision: business_world_model.get("product_world_decision", {}),
        paths.business_release_truth_pack: business_world_model.get("business_release_truth_pack", {}),
        paths.planning_control_truth_pack: business_world_model.get("planning_control_truth_pack", {}),
    }.items():
        write_json_artifact(path, payload)

    for json_path, markdown_path, model_key, renderer in [
        (paths.business_exploration_arena_json, paths.business_exploration_arena_md, "business_exploration_arena", render_business_exploration_arena_markdown),
        (paths.commercial_argument_draft_json, paths.commercial_argument_draft_md, "commercial_argument_draft", render_commercial_argument_draft_markdown),
        (paths.chosen_business_thesis_json, paths.chosen_business_thesis_md, "chosen_business_thesis", render_chosen_business_thesis_markdown),
    ]:
        payload = business_world_model.get(model_key, {})
        write_json_artifact(json_path, payload)
        markdown_path.write_text(renderer(payload if isinstance(payload, dict) else {}), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deep Phase-1 stage outputs")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--version", required=True, help="trial token like trial-v9")
    parser.add_argument("--owner", default="Codex deep-stage-compiler")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    parser.add_argument(
        "--thinking-value-gain-mode",
        choices=("off", "full-use"),
        default="off",
        help="experimental bounded Thinking Value-Gain strategy for major P1 artifact units",
    )
    parser.add_argument(
        "--thinking-value-gain-output-profile",
        choices=THINKING_VALUE_GAIN_OUTPUT_PROFILES,
        default="coverage_rich",
        help="Mindthus TVG exit-side output profile when --thinking-value-gain-mode=full-use",
    )
    parser.add_argument(
        "--skip-stage-02b",
        action="store_true",
        help="emit a rich Stage-02b skip-stub instead of the full deepening artifact",
    )
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    output_dir = Path(args.output_dir).resolve()
    source_text = read_text(source_path)
    if args.thinking_value_gain_mode == "full-use":
        (output_dir / "thinking-value-gain-strategy.md").write_text(
            "# Thinking Value-Gain Strategy\n\n"
            "- mode: `full-use`\n"
            f"- output_profile: `{args.thinking_value_gain_output_profile}`\n"
            "- scope: `major Phase-1 artifact units`\n"
            "- boundary: `bounded value-strengthening, not length expansion`\n"
            "- exit: `stop when another round no longer improves practical decision/action/evidence/review/handoff value`\n",
            encoding="utf-8",
        )

    stage_paths = [
        output_dir / "stage-01-user-research.md",
        output_dir / "stage-02a-requirements-structural-analysis.md",
        output_dir / "stage-02b-requirements-specification-deepening.md",
        output_dir / "stage-03-requirements-decomposition-and-mvp-slicing.md",
        output_dir / "stage-04-requirements-validation-and-concept-proof.md",
    ]

    stage_texts = build_phase1_deep_stage_texts(
        source_text,
        version=args.version,
        owner=args.owner,
        skip_stage_02b=args.skip_stage_02b,
    )

    for path, text in zip(stage_paths, stage_texts.ordered_texts()):
        write(path, text, args.output_locale)
    business_world_model = apply_commercial_argument_rewrite(
        build_business_world_model(source_text),
        load_commercial_argument_rewrite(output_dir),
    )
    if args.thinking_value_gain_mode == "full-use":
        business_world_model = apply_thinking_value_gain_full_use(
            business_world_model,
            output_profile=str(args.thinking_value_gain_output_profile),
        )
    business_model_artifact_paths = write_business_world_model_artifacts(output_dir, business_world_model)

    generated_paths = [
        *stage_paths,
        business_model_artifact_paths.business_world_model,
        business_model_artifact_paths.semantic_authoring_spine,
        business_model_artifact_paths.operating_baseline_model,
        business_model_artifact_paths.product_world_decision,
        business_model_artifact_paths.business_release_truth_pack,
        business_model_artifact_paths.planning_control_truth_pack,
    ]
    for path in generated_paths:
        print(f"generated: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
