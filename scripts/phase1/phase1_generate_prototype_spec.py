#!/usr/bin/env python3
"""
Generate a Stage-05 prototype-spec artifact from Phase-1 PRD and stage outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import re
from pathlib import Path

from common.output_language import resolve_output_locale
from phase1.phase1_generation_kernel import parse_markdown_table_padded as parse_markdown_table
from phase1.phase1_localize_prd_zh import INLINE_PHRASE_MAP, render_primary_locale_lines, replace_phrases


CURRENT_OUTPUT_LOCALE = resolve_output_locale()


@dataclass(frozen=True)
class PrototypeSpecPaths:
    prd_path: Path
    stage_02a_path: Path
    stage_02b_path: Path | None
    stage_03_path: Path
    stage_04_path: Path
    output_path: Path
    prompt_pack_output_path: Path


@dataclass(frozen=True)
class PrototypeSpecSourceTexts:
    prd_text: str
    stage_02a_text: str
    stage_02b_text: str
    stage_03_text: str
    stage_04_text: str


@dataclass(frozen=True)
class PrototypeSpecSourceSections:
    executive_summary: str
    out_of_scope_block: str
    review_bound_block: str
    business_flow_block: str
    state_machine_block: str
    acceptance_block: str
    design_start_block: str
    carryover_block: str
    deferred_block: str
    assumptions_block: str
    persona_context_block: str
    design_requirements_block: str
    ia_alternatives_block: str
    core_objects_block: str
    use_cases_block: str


PROTOTYPE_PAGE_MAP_HEADERS = [
    "page_id",
    "page_name",
    "route",
    "page_blueprint_type",
    "primary_actor",
    "allowed_roles",
    "primary_user_goal",
    "bound_use_case_ids",
    "business_objects",
    "must_show_together",
    "required_regions",
    "entry_conditions",
    "exit_conditions",
    "next_route_candidates",
    "denied_behavior",
    "readiness_status",
    "blocked_reason",
    "primary_action",
    "route_pattern",
    "parent_page",
    "canonical_page_id",
    "surface_variant",
    "audience_mode",
    "session_role_source",
    "auth_entry_route",
    "auth_entry_label",
    "workspace_entry_roles",
    "route_reachability_mode",
    "navigation_scope",
    "handoff_visibility",
    "forbidden_exposure",
]

SECTION_ALIASES = {
    "executive_summary": ["Executive Summary"],
    "out_of_scope": ["Out of Scope"],
    "review_bound": ["Review-Bound Carryover and Forbidden Assumptions"],
    "module_matrix": [
        "Information Architecture Spec Matrix",
        "IA Spec Matrix",
        "IA Spec Precursor Matrix",
        "Integrated IA Evidence",
        "Module Responsibility Matrix",
    ],
    "business_flows": ["Key Business Flows", "Operational Flow Specification"],
    "state_machine": ["State Machine and Transition Rules"],
    "acceptance": ["Acceptance Criteria"],
    "design_start": ["Design Can Start"],
    "carryover": ["Source Feature Carryover Ledger"],
    "deferred": ["Deferred Items Honesty Check"],
    "assumptions": ["Key Assumptions to Validate"],
    "persona_context": ["Persona Context Scenario and Key Paths"],
    "design_requirements": ["Design Requirements Extraction"],
    "ia_alternatives": ["IA Decision Alternatives Comparison"],
    "core_objects": ["Core Business Objects", "Entity Registry", "Domain Model", "核心业务对象", "领域模型"],
    "use_cases": ["User Stories, Use Cases, and Requirements"],
}

USE_CASE_STOPWORDS = {
    "use",
    "case",
    "primary",
    "user",
    "story",
    "the",
    "and",
    "for",
    "with",
    "into",
    "from",
    "this",
    "that",
    "step",
}

FLOW_BLUEPRINTS = {
    "dashboard": {
        "page_blueprint_type": "dashboard",
        "dominant_interaction_pattern": "summary-cards",
        "primary_work_region": "a status-rich workspace where summary context and the next action stay visible together",
        "secondary_support_regions": [
            "summary indicators for progress, freshness, and operational health",
            "support rail for alerts, pending work, or related records",
        ],
        "dominant_component_pattern": "summary strip paired with a prioritized worklist and adjacent next-action area",
        "action_model": "review current status, choose the next item, and move into the next business step without losing context",
        "forbidden_layout_patterns": [
            "do not collapse the page into generic KPI tiles without a real worklist",
            "do not separate the live summary from the action that advances the workflow",
        ],
        "render_blocks_in_order": [
            "workflow header with active business context",
            "summary band with the most important status signals",
            "prioritized worklist or record table",
            "next-action area that routes into the next core page",
        ],
        "field_groups": [
            "active business context",
            "prioritization and routing controls",
        ],
        "input_controls": [
            "`active_context_selector` | control: `select` | required: `yes` | purpose: `choose the record, segment, or period currently under review`",
            "`priority_focus` | control: `select` | required: `no` | purpose: `narrow the visible items before taking action`",
        ],
        "summary_cards": [
            "current status",
            "freshness or recency",
            "queue size or pending count",
            "next recommended action",
        ],
        "detail_fields_in_order": [
            "active record or period label",
            "top status signals",
            "highest-priority rows",
            "recommended next route",
        ],
        "table_columns": [
            "item",
            "status",
            "priority",
            "next action",
        ],
        "filters_and_selectors": [
            "context selector",
            "priority filter",
        ],
        "required_status_messages": [
            "loading: summary data or worklist data is being refreshed",
            "empty: there is no active data set ready for review yet",
            "error: the page could not load the current summary or worklist",
            "blocked: an upstream prerequisite is incomplete, so the next action cannot proceed",
        ],
        "primary_cta_label": "Open next item",
        "secondary_ctas": ["Refresh summary", "Open related list"],
        "submission_feedback": [
            "success: the selected context remains visible as the user moves into the next page",
            "blocked: explain which prerequisite still prevents progression",
        ],
    },
    "setup-flow": {
        "page_blueprint_type": "setup-flow",
        "dominant_interaction_pattern": "form",
        "primary_work_region": "a structured setup workspace centered on required inputs and readiness confirmation",
        "secondary_support_regions": [
            "readiness summary that makes missing prerequisites explicit",
            "support panel for policy notes, ownership boundaries, or follow-up guidance",
        ],
        "dominant_component_pattern": "structured form paired with a readiness checklist and activation area",
        "action_model": "enter required setup data, validate readiness, and activate the next business step honestly",
        "forbidden_layout_patterns": [
            "do not reduce the page to a bare input list without readiness context",
            "do not use a decorative wizard shell as a substitute for operational setup",
        ],
        "render_blocks_in_order": [
            "page header with setup scope and ownership context",
            "primary form for required records and configuration",
            "readiness checklist or validation panel",
            "activation or continue area",
        ],
        "field_groups": [
            "core setup fields",
            "readiness confirmation",
            "ownership or access confirmation",
        ],
        "input_controls": [
            "`primary_record_name` | control: `input` | required: `yes` | purpose: `capture the primary business record or configuration label`",
            "`required_seed_data` | control: `textarea` | required: `yes` | purpose: `capture the minimum data needed before the workflow can continue`",
            "`readiness_confirmation` | control: `checkbox` | required: `yes` | purpose: `make the activation decision explicit`",
        ],
        "summary_cards": [
            "setup scope",
            "readiness status",
            "activation status",
        ],
        "detail_fields_in_order": [
            "primary record label",
            "required setup inputs",
            "readiness gaps",
            "activation result",
        ],
        "table_columns": [
            "field",
            "status",
            "owner",
            "last updated",
        ],
        "filters_and_selectors": [
            "record type selector",
            "owner or workspace selector",
        ],
        "required_status_messages": [
            "loading: setup context is loading",
            "empty: no primary record has been configured yet",
            "error: the setup action failed",
            "blocked: minimum required fields remain incomplete",
        ],
        "primary_cta_label": "Save and continue",
        "secondary_ctas": ["Save draft", "Review prerequisites"],
        "submission_feedback": [
            "success: the activated context is preserved for the next workflow step",
            "blocked: explain which setup field or confirmation is still missing",
        ],
    },
    "record-workbench": {
        "page_blueprint_type": "record-workbench",
        "dominant_interaction_pattern": "master-detail",
        "primary_work_region": "a workbench where one record can be inspected and advanced without leaving the page",
        "secondary_support_regions": [
            "support panel for related records or history",
            "handoff area that clarifies what changes after the primary decision is made",
        ],
        "dominant_component_pattern": "record detail panel paired with an editable decision or update form",
        "action_model": "inspect one business record, update its state or decision, and carry the result into the next workflow step",
        "forbidden_layout_patterns": [
            "do not split the primary record context and the decision form across unrelated shells",
            "do not render only read-only details when the page is meant to move the workflow forward",
        ],
        "render_blocks_in_order": [
            "record identity header",
            "detail panel with the most important current data",
            "decision or update form",
            "handoff and downstream consequence panel",
        ],
        "field_groups": [
            "record selection or identity",
            "state update or decision controls",
        ],
        "input_controls": [
            "`record_selector` | control: `select` | required: `yes` | purpose: `make the acted-on record explicit`",
            "`decision_or_state_update` | control: `radio` | required: `yes` | purpose: `apply the page's primary state change honestly`",
            "`supporting_note` | control: `textarea` | required: `no` | purpose: `capture rationale or handoff context`",
        ],
        "summary_cards": [
            "record status",
            "owner or accountable role",
            "next route",
        ],
        "detail_fields_in_order": [
            "record summary",
            "supporting context",
            "current status",
            "decision rationale",
        ],
        "table_columns": [
            "record",
            "status",
            "owner",
            "updated_at",
        ],
        "filters_and_selectors": [
            "record selector",
            "status filter",
        ],
        "required_status_messages": [
            "loading: the selected record is loading",
            "empty: no record has been selected yet",
            "error: the record could not be loaded or updated",
            "blocked: the record cannot advance until a prerequisite is met",
        ],
        "primary_cta_label": "Save decision",
        "secondary_ctas": ["Save draft", "Return to previous page"],
        "submission_feedback": [
            "success: the updated record state remains visible on arrival to the next page",
            "blocked: explain what still prevents this record from moving forward",
        ],
    },
    "execution-workbench": {
        "page_blueprint_type": "execution-workbench",
        "dominant_interaction_pattern": "table-view",
        "primary_work_region": "an execution workspace where the queue and the update action stay visible together",
        "secondary_support_regions": [
            "support panel for related records, ownership context, or notes",
            "status area for downstream readiness and recent updates",
        ],
        "dominant_component_pattern": "work queue paired with an inline mutation form and progress context",
        "action_model": "select a queued item, update its execution state, and confirm the result before proceeding",
        "forbidden_layout_patterns": [
            "do not show a status update form without the related queue or item context",
            "do not treat the page as a passive report if the user must complete work here",
        ],
        "render_blocks_in_order": [
            "queue header with active work context",
            "tabular queue or grouped task list",
            "inline update panel",
            "recent history or consequence panel",
        ],
        "field_groups": [
            "queue filters and ownership selection",
            "state update and notes",
        ],
        "input_controls": [
            "`work_item_selector` | control: `select` | required: `yes` | purpose: `choose the item being advanced`",
            "`assignee` | control: `select` | required: `no` | purpose: `record who is accountable for the next move`",
            "`state_update` | control: `radio` | required: `yes` | purpose: `apply the next execution state`",
            "`execution_note` | control: `textarea` | required: `no` | purpose: `capture the outcome, blocker, or handoff note`",
        ],
        "summary_cards": [
            "queue count",
            "current work state",
            "owner",
        ],
        "detail_fields_in_order": [
            "item summary",
            "assignee",
            "state history",
            "latest note",
        ],
        "table_columns": [
            "item",
            "owner",
            "state",
            "updated_at",
        ],
        "filters_and_selectors": [
            "owner filter",
            "state filter",
        ],
        "required_status_messages": [
            "loading: queue data is loading",
            "empty: no work item is ready yet",
            "error: the update failed",
            "blocked: the item cannot advance because a dependency or owner is missing",
        ],
        "primary_cta_label": "Update work item",
        "secondary_ctas": ["Save draft", "Open related record"],
        "submission_feedback": [
            "success: the new state and note remain visible across downstream pages",
            "blocked: explain whether the issue is ownership, dependency, or validation related",
        ],
    },
    "review-decision": {
        "page_blueprint_type": "review-decision",
        "dominant_interaction_pattern": "summary-cards",
        "primary_work_region": "a review surface where evidence and the business decision stay visible together",
        "secondary_support_regions": [
            "status area for confidence, exceptions, or unresolved dependencies",
            "follow-up panel that keeps the next-cycle implication explicit",
        ],
        "dominant_component_pattern": "review summary with a visible decision area and supporting evidence list",
        "action_model": "review the outcome, judge the result, and record the next posture without hiding uncertainty",
        "forbidden_layout_patterns": [
            "do not treat the page as a download stub without an explicit decision area",
            "do not hide contradictory or incomplete evidence behind visual polish",
        ],
        "render_blocks_in_order": [
            "review header with cycle or period context",
            "result summary and supporting evidence",
            "decision controls",
            "follow-up implication panel",
        ],
        "field_groups": [
            "review selector",
            "decision capture",
        ],
        "input_controls": [
            "`review_scope_selector` | control: `select` | required: `yes` | purpose: `choose the period, batch, or record set currently under review`",
            "`review_decision` | control: `radio` | required: `yes` | purpose: `capture the business decision after reading the evidence`",
            "`decision_note` | control: `textarea` | required: `no` | purpose: `record the rationale that must remain visible downstream`",
        ],
        "summary_cards": [
            "review scope",
            "result status",
            "current decision",
        ],
        "detail_fields_in_order": [
            "review period or scope",
            "result comparison or outcome summary",
            "exceptions and uncertainty",
            "decision rationale",
        ],
        "table_columns": [
            "signal",
            "previous",
            "current",
            "delta",
        ],
        "filters_and_selectors": [
            "review scope selector",
            "status filter",
        ],
        "required_status_messages": [
            "loading: review data is being compiled",
            "empty: there is no completed cycle ready for review yet",
            "error: the review result could not be produced",
            "blocked: the final decision is missing required evidence",
        ],
        "primary_cta_label": "Record decision",
        "secondary_ctas": ["Refresh review", "Open supporting records"],
        "submission_feedback": [
            "success: the recorded decision and rationale remain visible to the next cycle",
            "blocked: explain which required evidence is still missing",
        ],
    },
    "detail-view": {
        "page_blueprint_type": "detail-view",
        "dominant_interaction_pattern": "form",
        "primary_work_region": "a focused record-detail area centered on one business object and its next change",
        "secondary_support_regions": [
            "related-records panel",
            "return path area that keeps the upstream workflow visible",
        ],
        "dominant_component_pattern": "entity detail with a compact edit form and related-context panel",
        "action_model": "inspect the selected object, make the necessary update, and return with context preserved",
        "forbidden_layout_patterns": [
            "do not present the page as a raw schema dump",
            "do not hide the return path to the upstream workflow",
        ],
        "render_blocks_in_order": [
            "record header",
            "core detail block",
            "editable fields",
            "return and downstream action area",
        ],
        "field_groups": [
            "record identity",
            "editable details",
        ],
        "input_controls": [
            "`record_id` | control: `input` | required: `yes` | purpose: `anchor the detail view to a specific record`",
            "`update_note` | control: `textarea` | required: `no` | purpose: `store the important change note or rationale`",
        ],
        "summary_cards": [
            "record identity",
            "current status",
        ],
        "detail_fields_in_order": [
            "record summary",
            "linked records",
            "latest change note",
        ],
        "table_columns": [
            "field",
            "value",
            "updated_at",
        ],
        "filters_and_selectors": [
            "record selector",
        ],
        "required_status_messages": [
            "loading: record detail is loading",
            "empty: no record has been selected yet",
            "error: the detail view could not be loaded",
            "blocked: the record cannot be edited yet",
        ],
        "primary_cta_label": "Save updates",
        "secondary_ctas": ["Return to previous page", "Open linked record"],
        "submission_feedback": [
            "success: saved updates remain visible when returning to the upstream workflow",
            "blocked: explain which validation issue prevented saving",
        ],
    },
}


def locale_fragment(text: str) -> str:
    if CURRENT_OUTPUT_LOCALE != "zh-CN":
        return text
    return replace_phrases(text, INLINE_PHRASE_MAP)


def locale_fragments(items: list[str]) -> list[str]:
    if CURRENT_OUTPUT_LOCALE != "zh-CN":
        return list(items)
    return [replace_phrases(item, INLINE_PHRASE_MAP) for item in items]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_heading_block(text: str, heading_keywords: list[str]) -> str:
    for keyword in heading_keywords:
        match = re.search(
            rf"^(##+)\s+(?:\d+(?:\.\d+)?\s+)?[^\n]*{re.escape(keyword)}[^\n]*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            continue
        start = match.start()
        heading_level = len(match.group(1))
        next_heading = re.search(
            rf"^#{{1,{heading_level}}}\s+",
            text[match.end() :],
            flags=re.MULTILINE,
        )
        if next_heading:
            end = match.end() + next_heading.start()
            return text[start:end].strip()
        return text[start:].strip()
    return ""


def section(text: str, key: str) -> str:
    return extract_heading_block(text, SECTION_ALIASES[key])


def strip_first_heading(block: str) -> str:
    if not block:
        return ""
    lines = block.splitlines()
    if lines and lines[0].startswith("##"):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip()


def extract_single_line_field(text: str, field: str) -> str:
    match = re.search(
        rf"^\s*-\s+{re.escape(field)}:\s*`?([^`\n]+)`?\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def resolve_prototype_spec_paths(args: argparse.Namespace) -> PrototypeSpecPaths:
    output_path = Path(args.output).resolve()
    return PrototypeSpecPaths(
        prd_path=Path(args.prd).resolve(),
        stage_02a_path=Path(args.stage_02a).resolve(),
        stage_02b_path=Path(args.stage_02b).resolve() if args.stage_02b else None,
        stage_03_path=Path(args.stage_03).resolve(),
        stage_04_path=Path(args.stage_04).resolve(),
        output_path=output_path,
        prompt_pack_output_path=(
            Path(args.prompt_pack_output).resolve()
            if args.prompt_pack_output
            else output_path.with_name("prototype-prompt-pack.md")
        ),
    )


def read_prototype_spec_source_texts(paths: PrototypeSpecPaths) -> PrototypeSpecSourceTexts:
    return PrototypeSpecSourceTexts(
        prd_text=read_text(paths.prd_path),
        stage_02a_text=read_text(paths.stage_02a_path),
        stage_02b_text=read_text(paths.stage_02b_path) if paths.stage_02b_path and paths.stage_02b_path.exists() else "",
        stage_03_text=read_text(paths.stage_03_path),
        stage_04_text=read_text(paths.stage_04_path),
    )


def extract_prototype_spec_source_sections(texts: PrototypeSpecSourceTexts) -> PrototypeSpecSourceSections:
    return PrototypeSpecSourceSections(
        executive_summary=section(texts.prd_text, "executive_summary"),
        out_of_scope_block=section(texts.prd_text, "out_of_scope"),
        review_bound_block=section(texts.stage_04_text, "review_bound"),
        business_flow_block=section(texts.prd_text, "business_flows"),
        state_machine_block=section(texts.prd_text, "state_machine"),
        acceptance_block=section(texts.prd_text, "acceptance"),
        design_start_block=section(texts.prd_text, "design_start"),
        carryover_block=section(texts.stage_03_text, "carryover"),
        deferred_block=section(texts.stage_03_text, "deferred"),
        assumptions_block=section(texts.stage_03_text, "assumptions"),
        persona_context_block=section(texts.stage_02a_text, "persona_context"),
        design_requirements_block=section(texts.stage_02a_text, "design_requirements"),
        ia_alternatives_block=section(texts.prd_text, "ia_alternatives"),
        core_objects_block=section(texts.prd_text, "core_objects"),
        use_cases_block=section(texts.prd_text, "use_cases"),
    )


def extract_prototype_spec_artifact_ids(texts: PrototypeSpecSourceTexts) -> dict[str, str]:
    return {
        "stage_02a": extract_single_line_field(texts.stage_02a_text, "artifact_id") or "P1-S02a-OUT-001",
        "stage_02b": extract_single_line_field(texts.stage_02b_text, "artifact_id") or "P1-S02b-OUT-001",
        "stage_03": extract_single_line_field(texts.stage_03_text, "artifact_id") or "P1-S03-OUT-001",
        "stage_04": extract_single_line_field(texts.stage_04_text, "artifact_id") or "P1-S04-OUT-001",
    }


def first_nonempty_lines(block: str, count: int) -> list[str]:
    lines: list[str] = []
    for line in strip_first_heading(block).splitlines():
        value = line.strip()
        if not value or value.startswith("#") or value.startswith("|"):
            continue
        value = re.sub(r"^\s*-\s+", "", value)
        if re.match(r"^[A-Za-z0-9_-]+:\s*$", value):
            continue
        lines.append(value)
        if len(lines) >= count:
            break
    return lines



def extract_markdown_table_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            current.append(line.rstrip())
            continue
        if len(current) >= 3:
            blocks.append("\n".join(current))
        current = []
    if len(current) >= 3:
        blocks.append("\n".join(current))
    return blocks


def normalized_key_variants(key: str) -> set[str]:
    candidate = re.sub(r"\s+", " ", str(key or "").strip().strip("`")).lower().replace("_", " ")
    if not candidate:
        return set()
    variants = {candidate.strip(" :-")}
    without_parens = re.sub(r"\([^)]*\)", " ", candidate)
    variants.add(re.sub(r"\s+", " ", without_parens).strip(" :-"))
    for match in re.findall(r"\(([^)]*)\)", candidate):
        inner = re.sub(r"\s+", " ", match.replace("_", " ")).strip(" :-")
        if inner:
            variants.add(inner)
    expanded = set(variants)
    for value in list(variants):
        for part in re.split(r"[／/|]", value):
            cleaned = re.sub(r"\s+", " ", part).strip(" :-")
            if cleaned:
                expanded.add(cleaned)
    return {value for value in expanded if value}


def row_value(row: dict[str, str], *keys: str) -> str:
    lowered: dict[str, str] = {}
    for row_key, value in row.items():
        for variant in normalized_key_variants(row_key):
            lowered.setdefault(variant, value)
    for key in keys:
        for variant in normalized_key_variants(key):
            value = lowered.get(variant, "")
            if value.strip():
                return value.strip()
    return ""


def parse_numbered_steps(block: str) -> list[str]:
    steps: list[str] = []
    for line in strip_first_heading(block).splitlines():
        match = re.match(r"^\d+\.\s+(.+?)\s*$", line.strip())
        if match:
            steps.append(match.group(1).strip())
    return steps


def parse_state_machine(block: str) -> dict[str, dict[str, object]]:
    state_map: dict[str, dict[str, object]] = {}
    for line in strip_first_heading(block).splitlines():
        value = line.strip()
        if not value.startswith("- "):
            continue
        body = value[2:].strip()
        if ":" not in body:
            continue
        subject, detail = body.split(":", 1)
        subject = subject.strip().strip("`")
        detail = detail.strip()
        if "->" in detail:
            state_map.setdefault(subject, {})["states"] = [part.strip() for part in detail.split("->")]
        else:
            state_map.setdefault(subject, {})["note"] = detail
    return state_map


def parse_bullets(block: str) -> list[str]:
    items: list[str] = []
    for line in strip_first_heading(block).splitlines():
        match = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if match:
            items.append(match.group(1).strip().strip("`"))
    return items


def parse_named_list(block: str, field: str) -> list[str]:
    match = re.search(
        rf"^\s*-\s+{re.escape(field)}:\s*$",
        block,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return []
    tail = block[match.end() :]
    items: list[str] = []
    for line in tail.splitlines():
        if re.match(r"^##\s+", line):
            break
        if re.match(r"^-\s+[A-Za-z0-9_]+:\s*$", line.strip()):
            break
        nested = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if nested:
            items.append(nested.group(1).strip().strip("`"))
            continue
        if line.strip() and not line.startswith(" "):
            break
    return items


def parse_assumption_statements(block: str) -> list[str]:
    items: list[str] = []
    capture_next_value = False
    for line in strip_first_heading(block).splitlines():
        stripped = line.strip()
        if re.match(r"^\s*-\s+assumption_\d+:\s*$", stripped):
            capture_next_value = True
            continue
        nested = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if not nested:
            continue
        value = nested.group(1).strip().strip("`")
        if re.match(r"^what_changes_if_", value):
            continue
        if capture_next_value:
            items.append(value)
            capture_next_value = False
    return items


def parse_bullet_values(block: str, count: int) -> list[str]:
    items: list[str] = []
    for line in strip_first_heading(block).splitlines():
        nested = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if not nested:
            continue
        value = nested.group(1).strip().strip("`")
        if value.endswith(":"):
            continue
        items.append(value)
        if len(items) >= count:
            break
    return items


def parse_design_requirement_summaries(block: str, count: int) -> list[str]:
    rows = parse_markdown_table(block)
    items: list[str] = []
    for row in rows[:count]:
        requirement_id = row_value(row, "id")
        role = row_value(row, "persona / role")
        trigger = row_value(row, "trigger")
        outcome = row_value(row, "required outcome")
        if requirement_id and outcome:
            items.append(f"{requirement_id} {role}: {trigger} -> {outcome}")
    return items


def supporting_use_case_id(label: str, description: str) -> str:
    use_case_number = re.search(r"(?:use case|用例)\s*(\d+)", label, flags=re.IGNORECASE)
    if use_case_number:
        return f"uc.use-case-{use_case_number.group(1)}"
    candidate = slugify(label or description or "use-case")
    return f"uc.{candidate}"


def parse_supporting_use_cases(block: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    lines = strip_first_heading(block).splitlines()
    in_supporting_section = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if re.match(r"^###\s+.*(Supporting Use Cases|Supporting user scenarios|支撑用例).*$", stripped, flags=re.IGNORECASE):
            in_supporting_section = True
            continue
        if in_supporting_section and re.match(r"^###\s+", stripped):
            break
        if not in_supporting_section:
            continue
        match = re.match(
            r"^\s*-\s*((?:用例|Use Case)\s*\d+(?:\s*\((?:Use Case|用例)\s*\d+\))?)\s*:\s*(.+?)\s*$",
            raw_line,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        label = match.group(1).strip()
        description = match.group(2).strip()
        entries.append(
            {
                "label": label,
                "description": description,
                "use_case_id": supporting_use_case_id(label, description),
            }
        )
    if entries:
        return entries

    for raw_line in lines:
        match = re.match(
            r"^\s*-\s*((?:用例|Use Case)\s*\d+(?:\s*\((?:Use Case|用例)\s*\d+\))?)\s*:\s*(.+?)\s*$",
            raw_line,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        label = match.group(1).strip()
        description = match.group(2).strip()
        entries.append(
            {
                "label": label,
                "description": description,
                "use_case_id": supporting_use_case_id(label, description),
            }
        )
    return entries


def use_case_number(use_case: dict[str, str]) -> int | None:
    label = str(use_case.get("label") or "").strip()
    match = re.search(r"(?:use case|用例)\s*(\d+)", label, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def parse_flow_step_numbers(value: str) -> list[int]:
    step_numbers = [int(match) for match in re.findall(r"(?:step|步骤)\s*(\d+)", value, flags=re.IGNORECASE)]
    return list(dict.fromkeys(step_numbers))


def row_references_use_case(row_blob: str, use_case: dict[str, str]) -> bool:
    lowered = row_blob.lower()
    number = use_case_number(use_case)
    if number is not None:
        if re.search(rf"(?:use case|用例)\s*0*{number}(?!\d)", lowered, flags=re.IGNORECASE):
            return True
        for alias in (
            f"uc.use-case-{number}",
            f"use-case-{number}",
            f"use-case-{number:02d}",
            f"p1-uc-{number:03d}",
        ):
            if alias in lowered:
                return True
    use_case_id = str(use_case.get("use_case_id") or "").strip().lower()
    if use_case_id and use_case_id in lowered:
        return True
    return False


def build_use_case_evidence_map(
    use_cases_block: str,
    use_cases: list[dict[str, str]],
    flow_steps: list[str],
) -> dict[str, dict[str, object]]:
    evidence_map: dict[str, dict[str, object]] = {}
    for use_case in use_cases:
        use_case_id = str(use_case.get("use_case_id") or "").strip()
        if not use_case_id:
            continue
        evidence_map[use_case_id] = {
            "texts": [
                str(use_case.get("label") or "").strip(),
                str(use_case.get("description") or "").strip(),
            ],
            "flow_steps": [],
        }

    for table_block in extract_markdown_table_blocks(use_cases_block):
        for row in parse_markdown_table(table_block):
            row_blob = " ".join(str(value).strip() for value in row.values() if str(value).strip())
            if not row_blob:
                continue
            step_numbers = parse_flow_step_numbers(
                row_value(
                    row,
                    "related_flow_step",
                    "related flow step",
                    "workflow_step",
                    "workflow step",
                )
            )
            evidence_fields = [
                row_value(row, "story_or_use_case", "story or use case"),
                row_value(row, "summary"),
                row_value(row, "requirement_statement", "requirement statement"),
                row_value(row, "acceptance_criteria", "acceptance criteria"),
                row_value(row, "why_this_class", "why this class"),
                row_value(row, "why_first_wave", "why first wave"),
                row_value(row, "boundary_condition", "boundary condition"),
                row_value(row, "risk_or_note", "risk or note"),
                row_value(row, "first-wave representation", "first wave representation"),
                row_value(row, "task/export implication", "task / export implication"),
                row_value(row, "certainty / note", "certainty / note"),
            ]
            for use_case in use_cases:
                if not row_references_use_case(row_blob, use_case):
                    continue
                use_case_id = str(use_case.get("use_case_id") or "").strip()
                if not use_case_id:
                    continue
                entry = evidence_map.setdefault(use_case_id, {"texts": [], "flow_steps": []})
                row_texts = [value for value in evidence_fields if value]
                if not row_texts:
                    row_texts = [row_blob]
                entry["texts"].extend(row_texts)
                entry["flow_steps"].extend(step_numbers)
                for step_number in step_numbers:
                    if 1 <= step_number <= len(flow_steps):
                        entry["texts"].append(flow_steps[step_number - 1])

    for entry in evidence_map.values():
        texts = [str(value).strip() for value in entry.get("texts", []) if str(value).strip()]
        entry["texts"] = list(dict.fromkeys(texts))
        flow_step_numbers = [int(value) for value in entry.get("flow_steps", []) if str(value).strip()]
        entry["flow_steps"] = list(dict.fromkeys(flow_step_numbers))
    return evidence_map


def semantic_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        if token in USE_CASE_STOPWORDS or len(token) <= 1:
            continue
        tokens.add(token)
        if token.endswith("ies") and len(token) > 4:
            tokens.add(token[:-3] + "y")
        elif token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "us", "is")):
            tokens.add(token[:-1])
    return tokens


def parse_deferred_honesty_summaries(block: str, count: int) -> list[str]:
    rows = parse_markdown_table(block)
    items: list[str] = []
    for row in rows[:count]:
        item = row_value(row, "item")
        reason = row_value(row, "why_not_in_mvp")
        consequence = row_value(row, "impact_of_deferral")
        if item and reason:
            items.append(f"{item}: {reason}; consequence: {consequence}")
    return items


def parse_carryover_summaries(block: str, count: int) -> list[str]:
    rows = parse_markdown_table(block)
    items = first_nonempty_lines(block, 2)
    for row in rows[:count]:
        detail = row_value(row, "source feature detail")
        classification = row_value(row, "classification")
        preserved = row_value(row, "preserved form in first-wave PRD")
        if detail and classification:
            items.append(f"{detail} -> {classification}; preserved as {preserved}")
    return items[: count + 2]


def format_bullet_list(items: list[str], indent: int = 2) -> list[str]:
    prefix = " " * indent + "- "
    return [prefix + item for item in items]


def slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-") or "page"


def split_objects(value: str) -> list[str]:
    parts = re.split(r"\s*/\s*|,|;|\|", value)
    return [part.strip().strip("`") for part in parts if part.strip().strip("`")]


def split_actions(value: str) -> list[str]:
    actions: list[str] = []
    for item in re.split(r"\s+/\s+|,|;", value):
        cleaned = item.strip()
        if cleaned:
            actions.append(cleaned)
    return actions


def split_roles(value: str) -> list[str]:
    roles: list[str] = []
    for item in re.split(r"\s*/\s*|,|;|\band\b", value, flags=re.IGNORECASE):
        cleaned = item.strip().strip("`")
        if cleaned:
            roles.append(cleaned)
    return roles


def contains_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", str(value or "")))


def normalize_inline_locale_variants(value: str) -> str:
    candidate = str(value or "").strip().strip("`")
    if not candidate:
        return ""

    def choose_side(match: re.Match[str]) -> str:
        left = match.group(1).strip()
        right = match.group(2).strip()
        left_has_cjk = contains_cjk(left)
        right_has_cjk = contains_cjk(right)
        if left_has_cjk == right_has_cjk:
            return match.group(0)
        if CURRENT_OUTPUT_LOCALE == "zh-CN":
            return left if left_has_cjk else right
        return right if left_has_cjk else left

    normalized = re.sub(r"([^()]{1,48})\s*\(([^()]{1,48})\)", choose_side, candidate)
    return re.sub(r"\s+", " ", normalized).strip()


def humanize_display_label(value: str) -> str:
    candidate = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or "")).replace("_", " ").replace("-", " ")
    tokens = [token for token in candidate.split() if token]
    normalized: list[str] = []
    for token in tokens:
        lowered = token.lower()
        if lowered in {"id", "api", "cta", "roi"}:
            normalized.append(lowered.upper())
        elif lowered == "and":
            normalized.append("and")
        else:
            normalized.append(lowered.capitalize())
    return " ".join(normalized).strip()


def normalize_display_label(value: str) -> str:
    candidate = normalize_inline_locale_variants(value)
    candidate = re.sub(r"\bworkspace\b\s*$", "", candidate, flags=re.IGNORECASE).strip(" -/")
    if not candidate:
        return ""
    if re.fullmatch(r"[A-Za-z0-9 &/_\-]+", candidate) and (
        candidate.lower() == candidate or "_" in candidate or "-" in candidate
    ):
        candidate = humanize_display_label(candidate.replace("&", " ").replace("/", " "))
    return re.sub(r"\s+", " ", candidate).strip()


def normalize_role_display_label(value: str) -> str:
    candidate = normalize_inline_locale_variants(value)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    if not candidate:
        return ""
    if re.fullmatch(r"[a-z0-9 _/\-]+", candidate):
        return re.sub(r"\s+", " ", candidate.replace("_", " ").replace("/", " ")).strip()
    return normalize_display_label(candidate)


def normalize_page_name_label(value: str) -> str:
    candidate = str(value or "").strip().strip("`")
    candidate = re.sub(r"\s+", " ", candidate).strip()
    if not candidate:
        return ""
    if "_" in candidate:
        candidate = re.sub(r"\s+", " ", candidate.replace("_", " ")).strip()
    return candidate


def looks_like_low_information_goal(value: str) -> bool:
    candidate = normalize_inline_locale_variants(str(value or "").strip())
    if not candidate or is_dependency_note(candidate):
        return True
    lowered = candidate.casefold()
    words = re.findall(r"[A-Za-z0-9]+", candidate)
    action_signals = (
        "create",
        "update",
        "record",
        "review",
        "complete",
        "capture",
        "confirm",
        "schedule",
        "register",
        "collect",
        "pay",
        "submit",
        "close",
        "advance",
        "inspect",
        "open",
        "start",
        "save",
        "登记",
        "创建",
        "更新",
        "记录",
        "审核",
        "评审",
        "接受",
        "提交",
        "确认",
        "排班",
        "支付",
        "关闭",
        "推进",
        "打开",
        "开始",
        "保存",
    )
    meta_patterns = (
        "selected object",
        "context preserved",
        "return with context",
        "necessary update",
        "downstream actor",
        "queryable together",
        "decision-support",
        "role/status summary",
        "without hiding uncertainty",
    )
    if any(pattern in lowered for pattern in meta_patterns):
        return True
    english_action_signals = [signal for signal in action_signals if re.fullmatch(r"[A-Za-z ]+", signal)]
    non_latin_action_signals = [signal for signal in action_signals if not re.fullmatch(r"[A-Za-z ]+", signal)]
    starts_with_action = any(lowered.startswith(f"{signal} ") or lowered == signal for signal in english_action_signals)
    if not starts_with_action:
        starts_with_action = any(candidate.startswith(signal) for signal in non_latin_action_signals)
    generic_goal_nouns = ("record", "records", "detail", "details", "summary", "queue", "workspace", "report")
    if len(words) <= 3 and any(lowered.endswith(f" {noun}") or lowered == noun for noun in generic_goal_nouns) and not starts_with_action:
        return True
    return len(words) <= 3 and not starts_with_action


def fallback_surface_goal(page: dict[str, object]) -> str:
    objects = [normalize_display_label(str(item)) for item in page.get("required_information_objects", []) if normalize_display_label(str(item))][:2]
    object_phrase = " and ".join(objects) if objects else normalize_display_label(str(page.get("page_name") or "record")) or "record"
    if re.search(r"[A-Za-z]", object_phrase):
        object_phrase = object_phrase.lower()
    page_blueprint_type = str(page.get("page_blueprint_type") or "").strip()
    if page_blueprint_type == "setup-flow":
        return locale_fragment(f"capture the required {object_phrase} details and continue")
    if page_blueprint_type == "execution-workbench":
        return locale_fragment(f"process the next {object_phrase} item and keep its status current")
    if page_blueprint_type == "review-decision":
        return locale_fragment(f"review the current {object_phrase} outcome and record the decision")
    if page_blueprint_type == "detail-view":
        return locale_fragment(f"review the current {object_phrase} details and complete the next update")
    if page_blueprint_type == "dashboard":
        return locale_fragment(f"review the current {object_phrase} status and continue")
    return locale_fragment(f"work on the current {object_phrase} and continue")


def required_value(value: str, fallback: str = "TBD") -> str:
    cleaned = str(value or "").strip()
    return cleaned or fallback


def normalize_product_name(document_title: str, fallback: str) -> str:
    candidate = document_title.strip() or fallback.strip()
    candidate = re.sub(
        r"\s+(Product Requirements Document|PRD|prototype-spec|产品需求文档)\s*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip()
    return candidate or fallback.strip() or "Current product"


def extract_document_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def choose_product_value_promise(current_product_context_lines: list[str]) -> str:
    ranked_candidates: list[tuple[int, str]] = []
    for line in current_product_context_lines:
        candidate = str(line).strip()
        if not candidate:
            continue
        lowered = candidate.lower()
        if any(
            blocked in lowered
            for blocked in (
                "该 prd 不是",
                "重编译",
                "recompile",
                "source summary",
                "main document",
            )
        ):
            continue
        score = 0
        if any(token in lowered for token in ("helps", "enable", "supports", "promise", "value", "承诺", "闭环", "operable")):
            score += 2
        if any(token in lowered for token in ("workflow-first", "step 1", "step 2", "step 3", "step 4", "step 5")):
            score -= 1
        ranked_candidates.append((score, candidate))
    if ranked_candidates:
        ranked_candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
        return ranked_candidates[0][1]
    return "Express the first-wave business workflow honestly and operably."


def parse_core_business_objects(block: str) -> list[str]:
    values: list[str] = []
    for row in parse_markdown_table(block):
        for key in ("object", "entity", "name", "core_object", "core object"):
            value = row_value(row, key)
            if value:
                values.append(value.strip().strip("`"))
                break
    if values:
        return list(dict.fromkeys(values))
    lines = strip_first_heading(block).splitlines()
    in_core_entity_list = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if re.match(r"^\s*-\s+(?:core entities|core objects|entity registry)\s*:\s*$", stripped, flags=re.IGNORECASE):
            in_core_entity_list = True
            continue
        if in_core_entity_list and re.match(r"^\s*-\s+.+?:", stripped):
            break
        if in_core_entity_list:
            nested = re.match(r"^\s*-\s+(.+?)\s*$", stripped)
            if nested:
                value = nested.group(1).strip().strip("`")
                if value and not value.endswith(":"):
                    values.append(value)
    if values:
        return list(dict.fromkeys(values))
    for line in lines:
        nested = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if nested:
            value = nested.group(1).strip().strip("`")
            if value.endswith(":"):
                continue
            values.append(value)
    return list(dict.fromkeys(values))


def extract_first_module_rows(text: str, aliases: list[str]) -> list[dict[str, str]]:
    for alias in aliases:
        rows = parse_markdown_table(extract_heading_block(text, [alias]))
        if rows:
            return rows
    return []


def module_row_identity(row: dict[str, str]) -> str:
    candidate = row_value(
        row,
        "page_name",
        "screen/module",
        "screen / module",
        "module_name",
        "module",
        "domain_name",
        "domain",
    )
    if not candidate.strip():
        return ""
    return slugify(normalize_page_name_label(candidate))


def merge_module_rows(
    authoritative_rows: list[dict[str, str]],
    supplemental_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    supplemental_by_identity: dict[str, dict[str, str]] = {}
    for row in supplemental_rows:
        identity = module_row_identity(row)
        if identity and identity not in supplemental_by_identity:
            supplemental_by_identity[identity] = row

    merged_rows: list[dict[str, str]] = []
    for row in authoritative_rows:
        merged_row = dict(row)
        supplemental = supplemental_by_identity.get(module_row_identity(row), {})
        for key, value in supplemental.items():
            if key not in merged_row or not str(merged_row.get(key) or "").strip():
                merged_row[key] = value
        merged_rows.append(merged_row)
    return merged_rows


def extract_module_rows_from_text(prd_text: str, stage_02b_text: str) -> list[dict[str, str]]:
    stage_authority_rows = extract_first_module_rows(
        stage_02b_text,
        [
            "IA Spec Precursor Matrix",
            "Information Architecture Spec Matrix",
            "IA Spec Matrix",
            "Integrated IA Evidence",
        ],
    )
    if stage_authority_rows:
        prd_rows = extract_first_module_rows(prd_text, SECTION_ALIASES["module_matrix"])
        return merge_module_rows(stage_authority_rows, prd_rows)

    for source_text in (prd_text, stage_02b_text):
        rows = extract_first_module_rows(source_text, SECTION_ALIASES["module_matrix"])
        if rows:
            return rows
    return []


def infer_page_name(row: dict[str, str], index: int) -> str:
    candidate = (
        row_value(row, "page_name", "screen/module", "screen / module", "module_name", "module", "domain_name", "domain")
        or f"Module {index}"
    )
    if " / " in candidate:
        parts = [part.strip() for part in candidate.split(" / ") if part.strip()]
        english_like = [part for part in parts if re.search(r"[A-Za-z]", part)]
        if english_like:
            candidate = english_like[-1]
        elif parts:
            candidate = parts[-1]
    normalized = normalize_page_name_label(candidate)
    lowered = normalized.casefold()
    raw_objects = split_objects(
        row_value(
            row,
            "required_information_objects",
            "required information objects",
            "core_objects",
            "core objects",
            "key_objects",
            "key objects",
        )
    )
    if any(token in lowered for token in ("cross-module", "handoff")) and raw_objects:
        object_label = normalize_display_label(raw_objects[0])
        if object_label:
            if "queue" in lowered:
                return f"{object_label} Queue" if CURRENT_OUTPUT_LOCALE != "zh-CN" else f"{object_label}队列"
            return f"{object_label} Handoff" if CURRENT_OUTPUT_LOCALE != "zh-CN" else f"{object_label}交接"
    return normalized or f"Module {index}"


def infer_primary_actor(row: dict[str, str]) -> str:
    candidate = row_value(row, "primary_actor", "primary actor", "owner", "persona / role", "role") or "primary workflow operator"
    roles = [normalize_role_display_label(role) for role in split_roles(candidate) if normalize_role_display_label(role)]
    if roles:
        return roles[0]
    return normalize_role_display_label(candidate) or "primary workflow operator"


def infer_required_objects(row: dict[str, str], core_objects: list[str]) -> list[str]:
    values = split_objects(
        row_value(
            row,
            "required_information_objects",
            "required information objects",
            "core_objects",
            "core objects",
            "key_objects",
            "key objects",
        )
    )
    if values:
        resolved_values: list[str] = []
        for value in values:
            value_tokens = semantic_tokens(value)
            lowered_value = value.lower()
            scored_matches: list[tuple[int, int, str]] = []
            for index, obj in enumerate(core_objects):
                object_tokens = semantic_tokens(obj)
                score = len(value_tokens & object_tokens)
                if obj.lower() in lowered_value or lowered_value in obj.lower():
                    score += 4
                if score > 0:
                    scored_matches.append((score, index, obj))
            if scored_matches:
                scored_matches.sort(key=lambda item: (-item[0], item[1], item[2]))
                resolved_values.append(scored_matches[0][2])
            else:
                resolved_values.append(value)
        return list(dict.fromkeys(resolved_values))
    row_blob = " ".join(str(value) for value in row.values())
    row_tokens = semantic_tokens(row_blob)
    scored_matches: list[tuple[int, int, str]] = []
    lowered_blob = row_blob.lower()
    for index, obj in enumerate(core_objects):
        object_tokens = semantic_tokens(obj)
        score = len(row_tokens & object_tokens)
        if obj.lower() in lowered_blob:
            score += 4
        if score > 0:
            scored_matches.append((score, index, obj))
    scored_matches.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [obj for _, _, obj in scored_matches[:4]]


def infer_primary_action(row: dict[str, str]) -> str:
    actions = split_actions(row_value(row, "exit_actions", "exit actions", "primary_action", "primary action", "responsibility"))
    if actions:
        return normalize_display_label(actions[0]) or normalize_inline_locale_variants(actions[0]) or actions[0]
    responsibility = row_value(row, "responsibility", "required outcome", "purpose")
    if responsibility:
        return normalize_display_label(responsibility) or normalize_inline_locale_variants(responsibility) or responsibility
    return "continue"


def _is_low_signal_entry_condition(value: str) -> bool:
    cleaned = str(value or '').strip().lower()
    if not cleaned or cleaned in {'—', '-', 'none', 'n/a', 'tbd'}:
        return True
    return cleaned.startswith('source workflow enters') or cleaned == 'route from prior workflow step'


def _is_low_signal_downstream_dependency(value: str) -> bool:
    cleaned = str(value or '').strip().lower()
    if not cleaned or cleaned in {'—', '-', 'none', 'n/a', 'tbd'}:
        return True
    return cleaned in {
        'depends on prior module output',
        'depends on prior workflow step',
        'depends on upstream contract',
        'advance the business record',
    }


def infer_entry_condition(row: dict[str, str]) -> str:
    candidate = row_value(row, "entry_conditions", "entry conditions", "entry", "trigger")
    if _is_low_signal_entry_condition(candidate):
        candidate = row_value(row, 'input', 'inputs', 'upstream_input') or candidate
    return normalize_inline_locale_variants(candidate) or 'route from prior workflow step'


def infer_downstream_dependency(row: dict[str, str]) -> str:
    candidate = row_value(row, "downstream_dependency", "downstream dependency", "dependency", "required outcome")
    if _is_low_signal_downstream_dependency(candidate):
        candidate = row_value(row, 'output', 'outputs', 'downstream_output', 'required outcome') or candidate
    return normalize_inline_locale_variants(candidate)


def infer_responsibility_text(row: dict[str, str]) -> str:
    candidate = row_value(row, "responsibility", "required outcome", "purpose", "description", "design implication")
    return normalize_inline_locale_variants(candidate)


def classify_page_blueprint(page_name: str, responsibility: str, action: str) -> str:
    blob = " ".join([page_name, responsibility, action]).lower()
    if any(token in blob for token in ("dashboard", "overview", "home", "monitor", "summary", "board", "center", "hub")):
        return "dashboard"
    if any(token in blob for token in ("setup", "configure", "config", "onboarding", "intake", "register", "create", "edit", "manage")):
        return "setup-flow"
    if any(token in blob for token in ("task", "queue", "dispatch", "assignment", "schedule", "fulfillment", "workbench", "processing", "execution")):
        return "execution-workbench"
    if any(token in blob for token in ("review", "report", "approval", "decision", "summary close", "retrospective")):
        return "review-decision"
    if any(token in blob for token in ("detail", "profile", "record", "history", "chart", "document")):
        return "detail-view"
    return "record-workbench"


def route_pattern_for_slug(slug: str, parent_slug: str) -> str:
    if not parent_slug:
        return f"/{slug}"
    return f"/{slug}"


def required_regions_for_blueprint(page_blueprint_type: str) -> list[str]:
    regions = ["context_header", "data_view", "work_area", "status_feedback", "next_steps"]
    if page_blueprint_type == "review-decision":
        regions.append("audit_strip")
    return regions


def denied_behavior_for_blueprint(page_blueprint_type: str) -> str:
    if page_blueprint_type in {"dashboard", "review-decision"}:
        return "show-inline-denied-banner"
    return "hide-primary-action-and-show-denied-hint"


APP_SURFACE_DEFAULT_FORBIDDEN_EXPOSURE = [
    "role_switcher",
    "review_copy",
    "contract_metadata",
    "cross_role_cta",
]


def default_navigation_scope_for_blueprint(page_blueprint_type: str) -> str:
    if page_blueprint_type in {"setup-flow", "review-decision"}:
        return "flow"
    return "workspace"


def infer_canonical_page_id(page: dict[str, object]) -> str:
    page_name = str(page.get("page_name") or "").strip()
    page_id = str(page.get("page_id") or "").strip()
    return slugify(page_name) or slugify(page_id) or "page"


def infer_surface_audience_mode(page: dict[str, object]) -> str:
    return "app"


def infer_surface_variant(page: dict[str, object]) -> str:
    audience_mode = infer_surface_audience_mode(page)
    if audience_mode == "review":
        allowed_roles = [str(item).strip() for item in page.get("allowed_roles", []) if str(item).strip()]
        role_slug = slugify(allowed_roles[0]) if allowed_roles else infer_canonical_page_id(page)
        return f"{role_slug}-review"
    if audience_mode == "preview":
        return f"{infer_canonical_page_id(page)}-preview"
    allowed_roles = [str(item).strip() for item in page.get("allowed_roles", []) if str(item).strip()]
    if len(allowed_roles) == 1:
        role_slug = slugify(allowed_roles[0])
        if role_slug:
            return f"{role_slug}-workspace"
    return f"{infer_canonical_page_id(page)}-workspace"


def infer_session_role_source(page: dict[str, object]) -> str:
    audience_mode = infer_surface_audience_mode(page)
    if audience_mode == "app":
        return "login_session"
    if audience_mode == "review":
        return "reviewer_override"
    return ""


def infer_auth_entry_route(page: dict[str, object]) -> str:
    if infer_surface_audience_mode(page) == "app" and infer_session_role_source(page) == "login_session":
        return "/auth/login"
    return ""


def infer_auth_entry_label(page: dict[str, object]) -> str:
    if not infer_auth_entry_route(page):
        return ""
    return "登录" if CURRENT_OUTPUT_LOCALE == "zh-CN" else "Sign in"


def assign_workspace_entry_roles(pages: list[dict[str, object]]) -> None:
    first_page_by_role: dict[str, str] = {}
    for page in pages:
        if infer_surface_audience_mode(page) != "app":
            page["workspace_entry_roles"] = []
            continue
        page_id = str(page.get("page_id") or "").strip()
        allowed_roles = [str(item).strip() for item in page.get("allowed_roles", []) if str(item).strip()]
        for role in allowed_roles:
            first_page_by_role.setdefault(role, page_id)
    for page in pages:
        page_id = str(page.get("page_id") or "").strip()
        allowed_roles = [str(item).strip() for item in page.get("allowed_roles", []) if str(item).strip()]
        page["workspace_entry_roles"] = [role for role in allowed_roles if first_page_by_role.get(role) == page_id]


def infer_route_reachability_mode(page: dict[str, object]) -> str:
    audience_mode = infer_surface_audience_mode(page)
    if audience_mode != "app":
        return "hidden"
    workspace_entry_roles = [str(item).strip() for item in page.get("workspace_entry_roles", []) if str(item).strip()]
    if workspace_entry_roles:
        return "direct"
    navigation_scope = str(page.get("navigation_scope") or "").strip().lower()
    if navigation_scope == "flow":
        return "flow"
    return "direct"


def infer_navigation_scope(page: dict[str, object]) -> str:
    audience_mode = infer_surface_audience_mode(page)
    if audience_mode != "app":
        return "hidden"
    return default_navigation_scope_for_blueprint(str(page.get("page_blueprint_type") or "").strip())


def infer_handoff_visibility(page: dict[str, object]) -> str:
    audience_mode = infer_surface_audience_mode(page)
    next_routes = [
        str(item).strip()
        for item in page.get("next_route_candidates", [])
        if str(item).strip() and str(item).strip() != "—"
    ]
    if not next_routes:
        return ""
    if audience_mode == "app":
        return "implicit_context"
    return "review_only"


def infer_forbidden_exposure(page: dict[str, object]) -> list[str]:
    if infer_surface_audience_mode(page) != "app":
        return []
    return list(APP_SURFACE_DEFAULT_FORBIDDEN_EXPOSURE)


def infer_allowed_roles(row: dict[str, str], primary_actor: str) -> list[str]:
    explicit = row_value(row, "allowed_roles", "allowed roles", "roles", "role", "actors", "primary_actor", "primary actor")
    roles = [normalize_role_display_label(role) for role in split_roles(explicit or primary_actor) if normalize_role_display_label(role)]
    if not roles and primary_actor.strip():
        roles = [normalize_role_display_label(primary_actor) or primary_actor.strip()]
    return list(dict.fromkeys(roles))


def infer_use_case_ids(page: dict[str, object]) -> list[str]:
    return [str(item).strip() for item in page.get("bound_use_case_ids", []) if str(item).strip()]


def infer_must_show_together(page: dict[str, object]) -> list[str]:
    objects = [str(item) for item in page["required_information_objects"][:3]]
    items: list[str] = []
    if objects:
        items.append(" + ".join(objects))
    items.append(f"next action readiness: {page['primary_action']}")
    return items


def infer_exit_conditions(page: dict[str, object]) -> list[str]:
    conditions = [f"{action} completed" for action in page["exit_actions"][:3]]
    downstream_dependency = str(page["downstream_dependency"]).strip()
    if downstream_dependency:
        conditions.append(downstream_dependency)
    return list(dict.fromkeys(conditions))


def page_use_case_match_blob(page: dict[str, object]) -> str:
    return " ".join(
        [
            str(page.get("page_name") or ""),
            str(page.get("route") or ""),
            str(page.get("page_blueprint_type") or ""),
            str(page.get("primary_actor") or ""),
            " ".join(str(item) for item in page.get("allowed_roles", [])),
            str(page.get("primary_action") or ""),
            str(page.get("responsibility") or ""),
            str(page.get("downstream_dependency") or ""),
            str(page.get("entry_condition") or ""),
            " ".join(str(item) for item in page.get("required_information_objects", [])),
        ]
    )


def use_case_overlap_score(page: dict[str, object], use_case: dict[str, str]) -> int:
    page_blob = page_use_case_match_blob(page)
    page_tokens = semantic_tokens(page_blob)
    use_case_tokens = semantic_tokens(" ".join([use_case.get("label", ""), use_case.get("description", "")]))
    return len(page_tokens & use_case_tokens)


def use_case_evidence_overlap_score(page: dict[str, object], evidence_texts: list[str]) -> int:
    if not evidence_texts:
        return 0
    page_blob = page_use_case_match_blob(page)
    page_tokens = semantic_tokens(page_blob)
    evidence_blob = " ".join(str(value).strip() for value in evidence_texts if str(value).strip())
    evidence_tokens = semantic_tokens(evidence_blob)
    score = len(page_tokens & evidence_tokens)
    lowered_evidence = evidence_blob.lower()
    page_name = str(page.get("page_name") or "").strip().lower()
    if page_name and page_name in lowered_evidence:
        score += 2
    for obj in page.get("required_information_objects", [])[:4]:
        obj_value = str(obj).strip().lower()
        if obj_value and obj_value in lowered_evidence:
            score += 2
    for role in page.get("allowed_roles", [])[:3]:
        role_value = str(role).strip().lower()
        if role_value and role_value in lowered_evidence:
            score += 1
    return score


def build_page_step_numbers(flow_pages: list[dict[str, object]]) -> dict[str, list[int]]:
    page_step_numbers: dict[str, list[int]] = {}
    for step_index, page in enumerate(flow_pages, start=1):
        page_id = str(page.get("page_id") or "").strip()
        if not page_id:
            continue
        page_step_numbers.setdefault(page_id, []).append(step_index)
    for page_id, step_numbers in list(page_step_numbers.items()):
        page_step_numbers[page_id] = list(dict.fromkeys(step_numbers))
    return page_step_numbers


def bind_supporting_use_cases_to_pages(
    pages: list[dict[str, object]],
    use_cases: list[dict[str, str]],
    use_case_evidence_map: dict[str, dict[str, object]] | None = None,
    page_step_numbers: dict[str, list[int]] | None = None,
) -> None:
    use_case_evidence_map = use_case_evidence_map or {}
    page_step_numbers = page_step_numbers or {}
    for page in pages:
        if not use_cases:
            page["bound_use_case_ids"] = ["TBD"]
            page["readiness_status"] = "review-bound"
            page["blocked_reason"] = "explicit supporting use cases are missing from upstream PRD §14"
            continue

        scored_use_cases: list[tuple[int, int, int, int, dict[str, str]]] = []
        assigned_steps = set(page_step_numbers.get(str(page.get("page_id") or "").strip(), []))
        for use_case in use_cases:
            use_case_id = str(use_case.get("use_case_id") or "").strip()
            evidence_entry = use_case_evidence_map.get(use_case_id, {})
            evidence_texts = [str(value) for value in evidence_entry.get("texts", [])]
            evidence_steps = {int(value) for value in evidence_entry.get("flow_steps", [])}
            direct_score = use_case_overlap_score(page, use_case)
            evidence_score = use_case_evidence_overlap_score(page, evidence_texts)
            step_bonus = len(assigned_steps & evidence_steps) * 2
            total_score = direct_score + evidence_score + step_bonus
            if total_score > 0:
                scored_use_cases.append((total_score, evidence_score, step_bonus, direct_score, use_case))
        if not scored_use_cases:
            page["bound_use_case_ids"] = ["TBD"]
            page["readiness_status"] = "review-bound"
            page["blocked_reason"] = "page could not be explicitly bound to any upstream supporting use case"
            continue

        scored_use_cases.sort(
            key=lambda item: (-item[0], -item[1], -item[2], -item[3], str(item[4].get("use_case_id") or "")),
        )
        top_score = scored_use_cases[0][0]
        selected = [
            use_case
            for score, _, _, _, use_case in scored_use_cases
            if score == top_score
        ][:2]
        page["bound_use_case_ids"] = [
            str(use_case["use_case_id"]).strip()
            for use_case in selected
            if str(use_case.get("use_case_id") or "").strip()
        ] or ["TBD"]
        page["readiness_status"] = "ready"
        page["blocked_reason"] = ""


def finalize_surface_readiness(page: dict[str, object]) -> None:
    blocking_reasons: list[str] = []
    if not str(page.get("page_id") or "").strip():
        blocking_reasons.append("missing page_id")
    if not str(page.get("route") or "").strip():
        blocking_reasons.append("missing route")
    if not str(page.get("page_blueprint_type") or "").strip():
        blocking_reasons.append("missing page_blueprint_type")
    if not str(page.get("primary_actor") or "").strip():
        blocking_reasons.append("missing primary_actor")
    if not str(page.get("primary_user_goal") or "").strip():
        blocking_reasons.append("missing primary_user_goal")
    if not page.get("business_objects"):
        blocking_reasons.append("missing business_objects")
    if not page.get("required_regions"):
        blocking_reasons.append("missing required_regions")

    if blocking_reasons:
        page["readiness_status"] = "blocked"
        prior_reason = str(page.get("blocked_reason") or "").strip()
        page["blocked_reason"] = "; ".join(blocking_reasons + ([prior_reason] if prior_reason else []))
        return

    page["readiness_status"] = str(page.get("readiness_status") or "review-bound").strip() or "review-bound"
    page["blocked_reason"] = str(page.get("blocked_reason") or "").strip()


def inline_table_value(values: list[str], fallback: str = "—") -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return ", ".join(cleaned) if cleaned else fallback


def prototype_page_map_row_values(page: dict[str, object]) -> list[str]:
    return [
        required_value(str(page["page_id"])),
        required_value(str(page["page_name"])),
        required_value(str(page["route"])),
        required_value(str(page["page_blueprint_type"])),
        required_value(str(page["primary_actor"])),
        required_value(inline_table_value(list(page["allowed_roles"]))),
        required_value(str(page["primary_user_goal"])),
        required_value(inline_table_value(list(page["bound_use_case_ids"]))),
        required_value(inline_table_value(list(page["business_objects"]))),
        required_value(inline_table_value(list(page["must_show_together"]))),
        required_value(inline_table_value(list(page["required_regions"]))),
        required_value(inline_table_value(list(page["entry_conditions"]))),
        required_value(inline_table_value(list(page["exit_conditions"]))),
        required_value(inline_table_value(list(page["next_route_candidates"]))),
        required_value(str(page["denied_behavior"])),
        required_value(str(page["readiness_status"])),
        required_value(str(page.get("blocked_reason") or ""), "—"),
        required_value(str(page["primary_action"])),
        required_value(str(page["route_pattern"])),
        required_value(str(page["parent_page"]), "—"),
        required_value(str(page["canonical_page_id"])),
        required_value(str(page["surface_variant"])),
        required_value(str(page["audience_mode"])),
        required_value(str(page["session_role_source"]), "—"),
        required_value(str(page.get("auth_entry_route") or ""), "—"),
        required_value(str(page.get("auth_entry_label") or ""), "—"),
        required_value(inline_table_value(list(page["workspace_entry_roles"])), "—"),
        required_value(str(page["route_reachability_mode"]), "—"),
        required_value(str(page["navigation_scope"]), "—"),
        required_value(str(page["handoff_visibility"]), "—"),
        required_value(inline_table_value(list(page["forbidden_exposure"]))),
    ]


def render_prototype_page_map_lines(pages: list[dict[str, object]]) -> list[str]:
    lines = [
        "",
        "## 4. Page Map",
        "- surface_matrix_authority_note:",
        "  - The table below is the authoritative page-level Surface Matrix for Stage-05.",
        "  - `route` is the authority field; `route_pattern` is retained as a compatibility mirror for existing downstream parsers.",
        "  - `primary_action` and `parent_page` remain compatibility columns and do not replace the page-level contract fields.",
        "  - `canonical_page_id / surface_variant / audience_mode / session_role_source / auth_entry_route / auth_entry_label / workspace_entry_roles / route_reachability_mode / navigation_scope / handoff_visibility / forbidden_exposure` freeze the audience-aware surface contract for downstream phases.",
        "  - If `readiness_status` is not `ready`, `blocked_reason` must explain why the page-level contract is still constrained.",
        "",
        "| " + " | ".join(PROTOTYPE_PAGE_MAP_HEADERS) + " |",
        "| " + " | ".join("---" for _ in PROTOTYPE_PAGE_MAP_HEADERS) + " |",
    ]
    for page in pages:
        lines.append("| " + " | ".join(prototype_page_map_row_values(page)) + " |")
    lines.extend(
        [
            "- navigation_structure_note:",
            "  - Workflow-first organization remains primary; support pages stay secondary to the main operating backbone.",
        ]
    )
    return lines


def render_prototype_main_flow_lines(route_entries: list[dict[str, str]], pages: list[dict[str, object]]) -> list[str]:
    lines = [
        "",
        "## 5. Main Flow and Key Transitions",
        "- main_flow:",
    ]
    for index, entry in enumerate(route_entries, start=1):
        lines.extend(
            [
                f"  - step_{index}:",
                f"    - from_page: `{entry['from_page']}`",
                f"    - user_goal: {entry['user_goal']}",
                f"    - system_response: {entry['system_response']}",
                f"    - to_page: `{entry['to_page']}`",
                f"    - context_that_must_survive_navigation: {entry['context_that_must_survive_navigation']}",
            ]
        )
    lines.extend(
        [
            "- alternate_paths:",
            "  - path_1:",
            "    - trigger: `an upstream prerequisite is incomplete`",
            "    - consequence: prototype must surface validation and blocked states instead of pretending the happy path always succeeds",
            "    - visible_pages:",
        ]
    )
    if pages:
        lines.append(f"      - `{pages[0]['page_name']}`")
    if len(pages) > 1:
        lines.append(f"      - `{pages[1]['page_name']}`")
    lines.extend(
        [
            "  - path_2:",
            "    - trigger: `the current record set is empty, stale, or non-interpretable`",
            "    - consequence: prototype must show failure, uncertainty, and recovery guidance instead of silently routing to a happy path",
            "    - visible_pages:",
        ]
    )
    for page in pages[:2]:
        lines.append(f"      - `{page['page_name']}`")
    lines.extend(
        [
            "  - path_3:",
            "    - trigger: `a downstream action is returned for clarification before it can continue`",
            "    - consequence: prototype must keep the handoff reversible and preserve the reason for the interruption",
            "    - visible_pages:",
        ]
    )
    for page in pages[1:3]:
        lines.append(f"      - `{page['page_name']}`")
    lines.extend(
        [
            "- route_graph_note:",
            "  - The prototype should keep the mainline route walkable while preserving blocked or exception paths so review honesty is visible, not implied.",
        ]
    )
    return lines


def render_prototype_page_brief_lines(
    pages: list[dict[str, object]],
    state_machine: dict[str, dict[str, object]],
    global_design_rules: list[str],
) -> list[str]:
    page_by_id = {str(page["page_id"]): page for page in pages}
    lines = [
        "",
        "## 6. Page Briefs",
    ]
    for page in pages:
        parent_page = page_by_id.get(str(page["parent_page"])) if str(page["parent_page"]) != "—" else None
        next_page = None
        for candidate in pages:
            if str(candidate["parent_page"]) == str(page["page_id"]):
                next_page = candidate
                break
        lines.extend(
            [
                f"  - page_{str(page['page_id']).replace('P', '').lstrip('0') or '1'}:",
                f"    - page_name: `{page['page_name']}`",
                f"    - page_role: `{page['page_role']}`",
                f"    - why_it_exists: {required_value(synthesize_page_goal(page))}",
                f"    - dominant_interaction_pattern: `{page['dominant_interaction_pattern']}`",
                f"    - key_data_objects: {required_value(', '.join(str(item) for item in page['required_information_objects']))}",
                f"    - business_state_transitions: {required_value(infer_business_state_transitions(page, state_machine))}",
                f"    - entry_condition: {required_value(str(page['entry_condition']))}",
                f"    - page_blueprint_type: `{page['page_blueprint_type']}`",
                f"    - primary_work_region: {page['primary_work_region']}",
                "    - secondary_support_regions:",
            ]
        )
        lines.extend(format_bullet_list(list(page["secondary_support_regions"]), 6))
        lines.extend(
            [
                f"    - dominant_component_pattern: {page['dominant_component_pattern']}",
                f"    - action_model: {page['action_model']}",
                "    - forbidden_layout_patterns:",
            ]
        )
        lines.extend(format_bullet_list(list(page["forbidden_layout_patterns"]), 6))
        lines.extend(["    - page_specific_design_rules:"])
        lines.extend(format_bullet_list(global_design_rules or ["preserve workflow continuity and required outcome honesty"], 6))
        lines.extend(["    - must_show_together:"])
        lines.extend(format_bullet_list(synthesize_context_contract(page), 6))
        lines.extend(["    - core_information_blocks:"])
        lines.extend(format_bullet_list([f"`{item}`" for item in page["required_information_objects"]] or ["workflow context"], 6))
        lines.extend(["    - core_actions:"])
        lines.extend(format_bullet_list([f"`{item}`" for item in page["exit_actions"]], 6))
        lines.extend(["    - required_user_inputs_or_confirmations:"])
        lines.extend(format_bullet_list(synthesize_required_inputs(page), 6))
        lines.extend(["    - render_blocks_in_order:"])
        lines.extend(format_bullet_list(list(page["render_blocks_in_order"]), 6))
        lines.extend(["    - field_groups:"])
        lines.extend(format_bullet_list(list(page["field_groups"]), 6))
        lines.extend(["    - input_controls:"])
        lines.extend(format_bullet_list(list(page["input_controls"]), 6))
        lines.extend(["    - summary_cards:"])
        lines.extend(format_bullet_list(list(page["summary_cards"]), 6))
        lines.extend(["    - detail_fields_in_order:"])
        lines.extend(format_bullet_list(list(page["detail_fields_in_order"]), 6))
        lines.extend(["    - table_columns:"])
        lines.extend(format_bullet_list(list(page["table_columns"]), 6))
        lines.extend(["    - filters_and_selectors:"])
        lines.extend(format_bullet_list(list(page["filters_and_selectors"]), 6))
        lines.extend(["    - required_status_messages:"])
        lines.extend(format_bullet_list(list(page["required_status_messages"]), 6))
        lines.extend(["    - important_state_variants:"])
        state_variants = ["normal", "loading", "empty", "error", "blocked"]
        lines.extend(format_bullet_list([f"`{item}`" for item in state_variants], 6))
        lines.extend(
            [
                f"    - primary_cta_label: `{page['primary_cta_label']}`",
                "    - secondary_ctas:",
            ]
        )
        lines.extend(format_bullet_list(list(page["secondary_ctas"]), 6))
        lines.extend(["    - submission_feedback:"])
        lines.extend(format_bullet_list(list(page["submission_feedback"]), 6))
        lines.extend(
            [
                f"    - context_arrives_from: {synthesize_context_bridge(parent_page, page)}",
                f"    - context_must_continue_to: {synthesize_context_bridge(page, next_page)}",
                "    - executor_brief:",
            ]
        )
        lines.extend(format_bullet_list(page_executor_brief(page, global_design_rules), 6))
    return lines


def build_object_pages_index(pages: list[dict[str, object]]) -> dict[str, list[str]]:
    object_pages: dict[str, list[str]] = {}
    for page in pages:
        for obj in page["required_information_objects"]:
            object_pages.setdefault(str(obj), []).append(str(page["page_name"]))
    return object_pages


def render_prototype_object_state_matrix_lines(
    core_objects: list[str],
    pages: list[dict[str, object]],
    state_machine: dict[str, dict[str, object]],
) -> list[str]:
    object_pages = build_object_pages_index(pages)
    ordered_objects = list(dict.fromkeys(core_objects + sorted(object_pages.keys())))
    lines = ["", "## 7. Core Objects and State Matrix", "- object_state_matrix:"]
    for index, obj in enumerate(ordered_objects, start=1):
        states = state_machine.get(obj, {}).get("states", ["visible", "selected"])
        lines.extend(
            [
                f"  - object_{index}:",
                f"    - object_name: `{obj}`",
                "    - visible_in_pages:",
            ]
        )
        lines.extend(format_bullet_list(sorted(dict.fromkeys(object_pages.get(obj, []))) or ["(not directly named in a page contract)"], 6))
        lines.extend(["    - required_states:"])
        lines.extend(format_bullet_list([str(item) for item in states], 6))
        lines.extend(["    - state_changing_actions:"])
        action_candidates: list[str] = []
        for page in pages:
            if obj in page["required_information_objects"]:
                action_candidates.extend(str(item) for item in page["exit_actions"])
        lines.extend(format_bullet_list(sorted(dict.fromkeys(action_candidates)) or ["visible through workflow transitions"], 6))
        lines.extend(["    - blocked_or_exception_notes: preserve blocked or exception context where the workflow can stop or degrade."])
    lines.extend(
        [
            "- object_matrix_compilation_note:",
            "  - Supporting detail blocks are folded into their parent workflow objects instead of being modeled as standalone state machines.",
        ]
    )
    return lines


def render_prototype_state_and_generation_constraint_lines(product_name: str) -> list[str]:
    return [
        "",
        "## 8. Key State Coverage",
        "- key_state_coverage:",
        "  - loading_state:",
        "    - where_visible: `core workflow pages`",
        "    - why_required: data loading, generated views, or downstream dependencies must remain honest in the prototype.",
        "  - empty_state:",
        "    - where_visible: `record-centric and list-centric pages`",
        "    - why_required: the prototype must show no-data and not-yet-generated states honestly.",
        "  - error_state:",
        "    - where_visible: `setup, dashboard, and execution pages`",
        "    - why_required: failed retrieval or invalid submission paths must remain visible.",
        "  - permission_state:",
        "    - where_visible: `setup and decision pages`",
        "    - why_required: ownership and governance boundaries are first-wave constraints, not late add-ons.",
        "  - disabled_or_blocked_state:",
        "    - where_visible: `pages with state-changing actions`",
        "    - why_required: operations must show blocked behavior before they can be reviewed safely.",
        "- state_gap_note:",
        "  - Some secondary edge states may still need finer-grained treatment during HTML execution.",
        "",
        "## 9. Prototype Generation Constraints",
        "- prototype_generation_constraints:",
        "  - must_preserve_main_flow: `yes`",
        "  - must_not_add_features_outside_scope: `yes`",
        "  - must_cover_key_states: `yes`",
        "  - must_keep_deferred_items_out_of_mainline_ui: `yes`",
        "  - must_mark_inferred_content: `yes`",
        "  - may_use_static_html_css_js_only: `yes`",
        "  - must_render_page_specific_data_contracts: `yes`",
        "  - must_render_real_input_controls_for_required_user_inputs: `yes`",
        "  - must_preserve_context_carry_forward_between_pages: `yes`",
        "  - must_use_upstream_page_names_or_domain_nouns: `yes`",
        "  - must_present_as_business_product_not_demo_shell: `yes`",
        "  - must_not_render_demo_console_or_api_explorer: `yes`",
        "  - must_not_center_home_on_stepper_or_debug_cards: `yes`",
        "  - must_not_replace_page_intent_with_generic_workspace_labels: `yes`",
        "  - preferred_output_shape:",
        "    - `small-multi-file`",
        "- execution_handoff_note:",
        "  - Any derived prototype executor may choose layout and styling, but must not invent new product capabilities, hidden states, or automation claims outside the first-wave boundary.",
        "- external_executor_brief:",
        f"  - treat the site as a business application named `{product_name}`, not as a demo artifact or acceptance harness",
        "  - the first screen must explain what workflow the product supports, who it serves, and where the operator should start",
        "  - every workflow page must expose the information needed to decide and the controls needed to continue, not just explanatory copy",
        "  - when a later page depends on earlier context, show the carried-forward context on arrival instead of resetting to an empty shell",
        "  - never use labels such as `API Explorer`, `Runtime Console`, `Acceptance Dashboard`, or `Demo Steps` as the dominant UX framing",
        "  - treat `prototype-prompt-pack.md` as supplementary guidance only; `prototype-spec.md` remains the authority",
    ]


def render_prototype_reasoning_evidence_lines(
    *,
    ia_alternatives_block: str,
    mainline_pages: list[dict[str, object]],
    state_machine: dict[str, dict[str, object]],
    deferred_items: list[str],
    non_goals: list[str],
) -> list[str]:
    lines = [
        "",
        "## 11. Reasoning Evidence",
        "",
        "This section is REQUIRED, not optional.",
        "",
        "### Page-Map Construction Reasoning",
        "- page_candidates_considered:",
    ]
    ia_alternatives = parse_markdown_table(ia_alternatives_block)
    if ia_alternatives:
        for index, row in enumerate(ia_alternatives[:3], start=1):
            lines.extend(
                [
                    f"  - candidate_{index}:",
                    f"    - name: `{row_value(row, 'alternative')}`",
                    f"    - why_considered: {row_value(row, 'strength') or row_value(row, 'organizing axis')}",
                    f"    - why_rejected_or_kept: {row_value(row, 'verdict')} / {row_value(row, 'failure risk')}",
                ]
            )
    else:
        lines.extend(
            [
                "  - candidate_1:",
                "    - name: `workflow-first`",
                "    - why_considered: closest to the first-wave operating loop",
                "    - why_rejected_or_kept: kept",
            ]
        )
    lines.extend(
        [
            "- chosen_page_map_logic: workflow-first page grouping remains primary because it preserves the main operating sequence without hiding the object model.",
            "- why_this_page_map_not_that: entity-first is clearer for pure domain review but weaker for first-wave route comprehension; role-first fragments the loop.",
            "",
            "### Flow Preservation Reasoning",
            "- workflow_backbone_used:",
        ]
    )
    for page in mainline_pages:
        lines.append(f"  - `{page['page_name']}`")
    lines.extend(
        [
            "- what_must_not_break_across_pages:",
            "  - dependent records must carry forward without a blind reset",
            "  - the next action must remain operable on every primary page",
            "  - object continuity must stay visible across the mainline route",
            "- where_route_simplification_was_allowed:",
            "  - secondary support pages may stay outside the mainline route",
            "- where_route_simplification_was_forbidden:",
            "  - prerequisite setup cannot be skipped",
            "  - a downstream action cannot skip the page that provides its required context",
            "  - final review cannot detach from the records and states it is judging",
            "",
            "### State Coverage Honesty",
            "- explicit_states_preserved_from_upstream:",
        ]
    )
    for subject, meta in state_machine.items():
        if "states" in meta:
            lines.append(f"  - `{subject}: {' -> '.join(str(item) for item in meta['states'])}`")
    lines.extend(
        [
            "- states_inferred_for_prototype_usability:",
            "  - page-level loading surfaces",
            "  - permission-limited variants",
            "  - disabled action treatments where operations are blocked",
            "- states_still_missing:",
            "  - some secondary edge variants may still need deeper HTML treatment",
            "- downstream_risk_if_missing:",
            "  - HTML execution may over-polish the prototype and hide the operational friction that the product actually depends on.",
            "",
            "### Deferred / Non-Goal Preservation",
            "- deferred_items_that_must_remain_hidden_from_mainline:",
        ]
    )
    for item in deferred_items:
        lines.append(f"  - `{item}`")
    lines.extend(["- non_goals_that_must_not_reappear_as_ui:"])
    for item in non_goals:
        lines.append(f"  - `{item}`")
    lines.extend(
        [
            "- prototype_risk_if_boundary_is_blurred:",
            "  - reviewers may mistake a high-fidelity shell for a stronger product commitment than the PRD actually allows.",
            "",
            "### Deepening Loop Log",
            "- loop_state:",
            "  - `S-review-bound-freeze`",
            "- rounds_executed:",
            "  - 1",
            "- round_log:",
            "  - round_1:",
            "    - trigger: `recompile PRD and late-stage outputs into page-level Surface Matrix authority`",
            "    - artifact_unit_improved: `surface matrix + route graph + state coverage`",
            "    - what_was_refined: `workflow-first page grouping and downstream prototype guardrails`",
            "    - outcome:",
            "      - `freeze`",
            "- freeze_rationale:",
            "  - Stage-05 is a page-level authority artifact; deeper interaction and binding detail should move into later stages, not back into informal page-map prose.",
            "",
            "### Method-Family Usage Evidence",
            "- method_family_1:",
            "  - name: `workflow-to-page-map recompilation`",
            "  - visible_effect: `mainline route stays anchored in the primary operating loop rather than page-shell sprawl`",
            "- method_family_2:",
            "  - name: `module-driven page grouping`",
            "  - visible_effect: `each module contributes at least one concrete page contract`",
            "- method_family_3:",
            "  - name: `object and state context discipline`",
            "  - visible_effect: `core business objects remain explicit across pages and state coverage`",
            "- method_family_4:",
            "  - name: `deferred and non-goal preservation`",
            "  - visible_effect: `deferred items remain outside the prototype mainline with explicit boundary notes`",
        ]
    )
    return lines


def render_prototype_diagram_and_acceptance_lines(mainline_pages: list[dict[str, object]]) -> list[str]:
    lines = [
        "",
        "## 12. Diagram / Structured Representation",
        "- requires_uml_or_mermaid:",
        "  - `yes`",
        "- diagram_type:",
        "  - `page-map-and-route-graph`",
        "- diagram_obligation:",
        "  - `required`",
        "- diagram_minimum_elements:",
        "  - major pages",
        "  - main flow transitions",
        "  - at least one alternate or exception path",
        "  - explicit start and end points",
        "- fail_action:",
        "  - return to page-map and route clarification if no coherent route graph exists",
        "- route_graph_mermaid:",
    ]
    lines.extend(build_mermaid_route_graph(mainline_pages))
    lines.extend(
        [
            "",
            "## 13. Acceptance and Flow",
            "- minimum_acceptance:",
            "  - page-level Surface Matrix authority exists",
            "  - page map compatibility view exists",
            "  - main flow exists",
            "  - page briefs exist",
            "  - object / state matrix exists",
            "  - key state coverage exists",
            "  - prototype generation constraints exist",
            "  - derived supplementary prompt guidance exists",
            "- handoff_to:",
            "  - `Phase-2 engineering alignment`",
            "  - `derived prototype prompt-pack generation`",
            "- handoff_package:",
            "  - `prototype-spec.md`",
            "  - authoritative surface matrix / page map",
            "  - route graph",
            "  - page briefs",
            "  - object / state matrix",
            "  - key state coverage",
            "  - deferred / non-goal boundary note",
            "  - prototype generation constraints",
            "- downstream_usage_rule:",
            "  - downstream may consume provisional content only as explicitly marked prototype inference",
            "  - downstream must not treat inferred UI detail as confirmed product truth",
            "  - `prototype-prompt-pack.md` may supplement visual generation, but it must not add or mutate page authority fields",
        ]
    )
    return lines


def render_prototype_reference_and_source_note_lines(
    *,
    paths: PrototypeSpecPaths,
    persona_lines: list[str],
    design_requirement_lines: list[str],
    carryover_lines: list[str],
    deferred_lines: list[str],
    acceptance_lines: list[str],
) -> list[str]:
    lines = [
        "",
        "## 14. Referenced Upstream Artifacts",
        f"- referenced_prd: `{paths.prd_path.name}`",
        "- referenced_stage_outputs:",
        f"  - Stage-02a: `{paths.stage_02a_path.name}`",
    ]
    if paths.stage_02b_path and paths.stage_02b_path.exists():
        lines.append(f"  - Stage-02b: `{paths.stage_02b_path.name}`")
    else:
        lines.append("  - Stage-02b: `(not provided)`")
    lines.extend(
        [
            f"  - Stage-03: `{paths.stage_03_path.name}`",
            f"  - Stage-04: `{paths.stage_04_path.name}`",
            "- referenced_sections:",
            "  - `PRD Executive Summary`",
            "  - `PRD Module Responsibility Matrix`",
            "  - `PRD Key Business Flows`",
            "  - `PRD State Machine and Transition Rules`",
            "  - `Stage-03 Source Feature Carryover Ledger`",
            "  - `Stage-03 Deferred Items Honesty Check`",
            "  - `Stage-04 Review-Bound Carryover and Forbidden Assumptions`",
            "",
            "## 15. Surface Authority Downstream Mapping",
            "- this_artifact_feeds:",
            "  - surface_matrix / page_map -> downstream page-level authority alignment",
            "  - main_flow -> route and handoff planning",
            "  - page_briefs -> page content / module scaffolding",
            "  - object_state_matrix -> stateful UI representation",
            "  - key_state_coverage -> empty / error / loading / permission page variants",
            "  - prototype_generation_constraints -> supplementary prototype guardrails",
            "",
            "## 16. Source Notes",
            "- persona_context_signal:",
        ]
    )
    lines.extend(format_bullet_list(persona_lines or ["Primary persona context still centers on the business workflow operator."]))
    lines.extend(["- design_requirement_signal:"])
    lines.extend(format_bullet_list(design_requirement_lines or ["Design requirements remain workflow-first and action-chain preserving."]))
    lines.extend(["- carryover_signal:"])
    lines.extend(format_bullet_list(carryover_lines or ["Deferred and non-goal boundaries remain explicit and must not be hidden in the prototype."]))
    lines.extend(["- deferred_honesty_signal:"])
    lines.extend(format_bullet_list(deferred_lines or ["Deferred items remain review-bound rather than silently promoted into the first-wave UI."]))
    lines.extend(["- acceptance_signal:"])
    lines.extend(format_bullet_list(acceptance_lines or ["Acceptance criteria already require workflow continuity and explicit state honesty."]))
    return lines


def build_pages(module_rows: list[dict[str, str]], core_objects: list[str]) -> list[dict[str, object]]:
    pages: list[dict[str, object]] = []
    for index, row in enumerate(module_rows, start=1):
        page_name = infer_page_name(row, index)
        primary_actor = infer_primary_actor(row)
        required_objects = infer_required_objects(row, core_objects)
        entry_condition = infer_entry_condition(row)
        downstream_dependency = infer_downstream_dependency(row)
        responsibility = infer_responsibility_text(row)
        primary_action = infer_primary_action(row)
        slug = slugify(page_name)
        blueprint_family = classify_page_blueprint(page_name, responsibility, primary_action)
        template = FLOW_BLUEPRINTS[blueprint_family]
        pages.append(
            {
                "page_id": f"P{index:02d}",
                "page_name": page_name,
                "slug": slug,
                "primary_actor": primary_actor,
                "allowed_roles": infer_allowed_roles(row, primary_actor),
                "required_information_objects": required_objects,
                "entry_condition": entry_condition,
                "primary_action": primary_action,
                "exit_actions": split_actions(row_value(row, "exit_actions", "exit actions", "primary_action", "primary action")) or [primary_action],
                "downstream_dependency": downstream_dependency,
                "responsibility": responsibility,
                "page_blueprint_type": template["page_blueprint_type"],
                "dominant_interaction_pattern": template["dominant_interaction_pattern"],
                "primary_work_region": locale_fragment(str(template["primary_work_region"])),
                "secondary_support_regions": locale_fragments(list(template["secondary_support_regions"])),
                "dominant_component_pattern": locale_fragment(str(template["dominant_component_pattern"])),
                "action_model": locale_fragment(str(template["action_model"])),
                "forbidden_layout_patterns": locale_fragments(list(template["forbidden_layout_patterns"])),
                "render_blocks_in_order": locale_fragments(list(template["render_blocks_in_order"])),
                "field_groups": locale_fragments(list(template["field_groups"])),
                "input_controls": locale_fragments(list(template["input_controls"])),
                "summary_cards": locale_fragments(list(template["summary_cards"])),
                "detail_fields_in_order": locale_fragments(list(template["detail_fields_in_order"])),
                "table_columns": locale_fragments(list(template["table_columns"])),
                "filters_and_selectors": locale_fragments(list(template["filters_and_selectors"])),
                "required_status_messages": locale_fragments(list(template["required_status_messages"])),
                "primary_cta_label": locale_fragment(str(template["primary_cta_label"])),
                "secondary_ctas": locale_fragments(list(template["secondary_ctas"])),
                "submission_feedback": locale_fragments(list(template["submission_feedback"])),
                "required_regions": required_regions_for_blueprint(str(template["page_blueprint_type"])),
                "denied_behavior": denied_behavior_for_blueprint(str(template["page_blueprint_type"])),
                "readiness_status": "ready",
            }
        )
    return pages


def overlap_score(step: str, page: dict[str, object]) -> int:
    step_tokens = set(re.findall(r"[a-z0-9]+", step.lower()))
    haystack = " ".join(
        [
            str(page["page_name"]),
            str(page["primary_action"]),
            str(page["responsibility"]),
            " ".join(str(item) for item in page["required_information_objects"]),
        ]
    ).lower()
    score = 0
    for token in step_tokens:
        if token and token in haystack:
            score += 1
    return score


def assign_flow_pages(flow_steps: list[str], pages: list[dict[str, object]]) -> list[dict[str, object]]:
    if not pages:
        return []
    assignments: list[dict[str, object]] = []
    last_index = 0
    for step in flow_steps:
        best_index = last_index
        best_score = -1
        for index, page in enumerate(pages):
            score = overlap_score(step, page)
            if score > best_score:
                best_index = index
                best_score = score
        if best_score <= 0 and last_index < len(pages):
            best_index = min(last_index, len(pages) - 1)
        assignments.append(pages[best_index])
        last_index = min(best_index + 1, len(pages) - 1)
    return assignments


def ensure_mainline_pages(flow_pages: list[dict[str, object]], pages: list[dict[str, object]]) -> list[dict[str, object]]:
    ordered: list[dict[str, object]] = []
    for page in flow_pages or pages:
        if page not in ordered:
            ordered.append(page)
    for page in pages:
        if page not in ordered:
            ordered.append(page)
    return ordered


def apply_prototype_page_authority_contracts(
    pages: list[dict[str, object]],
    flow_pages: list[dict[str, object]],
) -> list[dict[str, object]]:
    mainline_pages = ensure_mainline_pages(flow_pages, pages)
    for index, page in enumerate(mainline_pages):
        parent_page = mainline_pages[index - 1] if index > 0 else None
        page["parent_page"] = str(parent_page["page_id"]) if parent_page else "—"
        page["route_pattern"] = route_pattern_for_slug(str(page["slug"]), str(parent_page["slug"]) if parent_page else "")
        page["page_role"] = "mainline" if page in flow_pages else "support"
    for page in pages:
        if "parent_page" not in page:
            page["parent_page"] = "—"
        if "route_pattern" not in page:
            page["route_pattern"] = route_pattern_for_slug(str(page["slug"]), "")
        if "page_role" not in page:
            page["page_role"] = "support"
        page["route"] = str(page["route_pattern"])
        page["primary_user_goal"] = synthesize_page_goal(page)
        page["bound_use_case_ids"] = infer_use_case_ids(page)
        page["business_objects"] = [str(item) for item in page["required_information_objects"]]
        page["must_show_together"] = infer_must_show_together(page)
        page["entry_conditions"] = [str(page["entry_condition"]).strip()] if str(page["entry_condition"]).strip() else ["TBD"]
        page["exit_conditions"] = infer_exit_conditions(page)

    children_by_parent: dict[str, list[dict[str, object]]] = {}
    for page in pages:
        parent_page_id = str(page.get("parent_page") or "").strip()
        if parent_page_id and parent_page_id != "—":
            children_by_parent.setdefault(parent_page_id, []).append(page)
    for page in pages:
        children = children_by_parent.get(str(page["page_id"]), [])
        page["next_route_candidates"] = [str(child["route"]) for child in children] or ["—"]
        page["canonical_page_id"] = infer_canonical_page_id(page)
        page["surface_variant"] = infer_surface_variant(page)
        page["audience_mode"] = infer_surface_audience_mode(page)
        page["session_role_source"] = infer_session_role_source(page)
        page["auth_entry_route"] = infer_auth_entry_route(page)
        page["auth_entry_label"] = infer_auth_entry_label(page)
        page["navigation_scope"] = infer_navigation_scope(page)
        page["handoff_visibility"] = infer_handoff_visibility(page)
        page["forbidden_exposure"] = infer_forbidden_exposure(page)
    assign_workspace_entry_roles(pages)
    for page in pages:
        page["route_reachability_mode"] = infer_route_reachability_mode(page)
        finalize_surface_readiness(page)
    return mainline_pages


def relevant_state_transitions(page: dict[str, object], state_machine: dict[str, dict[str, object]]) -> list[str]:
    transitions: list[str] = []
    page_objects = [str(item) for item in page["required_information_objects"]]
    for obj in page_objects:
        if obj in state_machine and "states" in state_machine[obj]:
            states = state_machine[obj]["states"]
            if isinstance(states, list) and states:
                transitions.append(f"{obj}: {' -> '.join(str(state) for state in states)}")
    return transitions[:3]


def infer_business_state_transitions(page: dict[str, object], state_machine: dict[str, dict[str, object]]) -> str:
    transitions = relevant_state_transitions(page, state_machine)
    if transitions:
        return "; ".join(transitions)
    action_blob = "_then_".join(slugify(action).replace("-", "_") for action in page["exit_actions"][:3])
    return action_blob or "workflow_state_updated"


def is_dependency_note(value: str) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return False
    lowered = normalized.casefold()
    return (
        lowered.startswith("depends on ")
        or lowered.startswith("dependent on ")
        or " depends on " in lowered
        or "依赖" in normalized
    )


def synthesize_page_goal(page: dict[str, object]) -> str:
    responsibility = normalize_inline_locale_variants(str(page.get("responsibility") or "").strip())
    if responsibility and not looks_like_low_information_goal(responsibility):
        return responsibility
    primary_action = normalize_inline_locale_variants(str(page.get("primary_action") or "").strip())
    if primary_action and not looks_like_low_information_goal(primary_action):
        return primary_action
    downstream_dependency = normalize_inline_locale_variants(str(page.get("downstream_dependency") or "").strip())
    if downstream_dependency and not looks_like_low_information_goal(downstream_dependency):
        return downstream_dependency
    return fallback_surface_goal(page)


def synthesize_context_contract(page: dict[str, object]) -> list[str]:
    objects = [f"`{item}`" for item in page["required_information_objects"][:4]]
    lines = []
    if objects:
        lines.append(
            locale_fragment("keep the upstream information objects explicit on the page: ") + ", ".join(objects)
        )
    lines.append(
        locale_fragment("the primary business context and the next action must stay together on the page")
    )
    return lines


def synthesize_required_inputs(page: dict[str, object]) -> list[str]:
    items = [
        locale_fragment("the page must expose enough inputs or selections to complete the intended next action"),
    ]
    for action in page["exit_actions"][:3]:
        items.append(locale_fragment(f"support the action directly: `{action}`"))
    return items


def synthesize_context_bridge(source_page: dict[str, object] | None, target_page: dict[str, object] | None) -> str:
    if not source_page or not target_page:
        return locale_fragment("derive visible context from the prior workflow step")
    source_objects = set(str(item) for item in source_page["required_information_objects"])
    target_objects = set(str(item) for item in target_page["required_information_objects"])
    shared = sorted(source_objects & target_objects)
    if shared:
        return locale_fragment("carry forward the active business context: ") + ", ".join(f"`{item}`" for item in shared[:4])
    return locale_fragment("carry the active selection and the last completed decision into the next page")


def synthesize_user_goal(step: str) -> str:
    cleaned = re.sub(r"^Step\s+\d+:\s*", "", step).strip()
    return locale_fragment(cleaned)


def synthesize_system_response(step: str) -> str:
    cleaned = re.sub(r"^Step\s+\d+:\s*", "", step).strip()
    return locale_fragment(f"support the user in completing: {cleaned}")


def build_mermaid_route_graph(mainline_pages: list[dict[str, object]]) -> list[str]:
    lines = [
        "```mermaid",
        "flowchart LR",
        "    start([Start])",
        "    end([End])",
        "    blocked{{Blocked / validation path}}",
    ]
    for page in mainline_pages:
        node_id = str(page["page_id"]).lower()
        lines.append(f'    {node_id}["{page["page_name"]}"]')
    if mainline_pages:
        lines.append(f"    start --> {str(mainline_pages[0]['page_id']).lower()}")
        for source_page, target_page in zip(mainline_pages, mainline_pages[1:]):
            lines.append(f"    {str(source_page['page_id']).lower()} --> {str(target_page['page_id']).lower()}")
        lines.append(f"    {str(mainline_pages[-1]['page_id']).lower()} --> end")
        lines.append(f"    {str(mainline_pages[0]['page_id']).lower()} -. missing prerequisites .-> blocked")
        lines.append(f"    {str(mainline_pages[-1]['page_id']).lower()} -. missing evidence .-> blocked")
    lines.append("```")
    return lines


def page_executor_brief(page: dict[str, object], design_rules: list[str]) -> list[str]:
    brief = [
        locale_fragment(f"use `{page['page_name']}` as a business-facing surface, not as a generic placeholder screen"),
        locale_fragment("page headings, labels, and CTAs should keep upstream domain nouns visible instead of collapsing into generic debug vocabulary"),
        locale_fragment("the primary action on this page must be operable, not merely described"),
    ]
    if design_rules:
        brief.append(locale_fragment(f"page-specific rule to preserve: {design_rules[0]}"))
    return list(dict.fromkeys(brief))


def build_route_entries(flow_steps: list[str], flow_pages: list[dict[str, object]]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    if not flow_steps:
        for source_page, target_page in zip(flow_pages, flow_pages[1:]):
            entries.append(
                {
                    "from_page": str(source_page["page_name"]),
                    "user_goal": synthesize_page_goal(source_page),
                    "system_response": locale_fragment("preserve visible business context while routing into the next step"),
                    "to_page": str(target_page["page_name"]),
                    "context_that_must_survive_navigation": synthesize_context_bridge(source_page, target_page),
                }
            )
        return entries
    for index, step in enumerate(flow_steps):
        source_page = flow_pages[index] if index < len(flow_pages) else flow_pages[-1]
        target_page = flow_pages[min(index + 1, len(flow_pages) - 1)] if flow_pages else source_page
        entries.append(
            {
                "from_page": str(source_page["page_name"]),
                "user_goal": synthesize_user_goal(step),
                "system_response": synthesize_system_response(step),
                "to_page": str(target_page["page_name"]),
                "context_that_must_survive_navigation": synthesize_context_bridge(source_page, target_page),
            }
        )
    return entries


def render_prototype_prompt_page_contract_lines(pages: list[dict[str, object]]) -> list[str]:
    lines = ["", "Page contracts:"]
    for index, page in enumerate(pages, start=1):
        lines.extend(
            [
                f"- Page {index}: {page['page_name']}",
                f"  - Product purpose: {synthesize_page_goal(page)}",
                f"  - Primary actor: {page['primary_actor']}",
                f"  - Entry condition: {page['entry_condition']}",
                f"  - Page blueprint type: {page['page_blueprint_type']}",
                f"  - Primary work region: {page['primary_work_region']}",
                f"  - Dominant component pattern: {page['dominant_component_pattern']}",
                f"  - Action model: {page['action_model']}",
                "  - Secondary support regions:",
            ]
        )
        for item in page["secondary_support_regions"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Forbidden layout patterns:"])
        for item in page["forbidden_layout_patterns"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Must visibly show together:"])
        for item in synthesize_context_contract(page):
            lines.append(f"    - {item}")
        lines.extend(["  - Required information blocks:"])
        for item in page["required_information_objects"] or ["workflow context"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Render blocks in order:"])
        for item in page["render_blocks_in_order"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Field groups that must exist on the page:"])
        for item in page["field_groups"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Input controls to materialize:"])
        for item in page["input_controls"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Summary cards or top-line badges to show:"])
        for item in page["summary_cards"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Detail fields in reading order:"])
        for item in page["detail_fields_in_order"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Table or list columns when tabular presentation is used:"])
        for item in page["table_columns"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Filters and selectors to expose:"])
        for item in page["filters_and_selectors"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Required user inputs / confirmations:"])
        for item in synthesize_required_inputs(page):
            lines.append(f"    - {item}")
        lines.extend(
            [
                f"  - Primary CTA label: {page['primary_cta_label']}",
                "  - Secondary CTAs:",
            ]
        )
        for item in page["secondary_ctas"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Primary actions the UI must make operable:"])
        for action in page["exit_actions"]:
            lines.append(f"    - {action}")
        lines.extend(["  - Required status messages:"])
        for item in page["required_status_messages"]:
            lines.append(f"    - {item}")
        lines.extend(["  - Submission feedback the UI must make explicit:"])
        for item in page["submission_feedback"]:
            lines.append(f"    - {item}")
    return lines


def render_prototype_prompt_product_truth_lines(
    first_wave_scope: list[str],
    deferred_items: list[str],
    non_goals: list[str],
    review_bound_lines: list[str],
) -> list[str]:
    lines = ["", "Non-negotiable product truths:"]
    for item in first_wave_scope or ["first-wave workflow continuity"]:
        lines.append(f"- In scope: {item}")
    for item in deferred_items:
        lines.append(f"- Deferred and must not appear as active product capability: {item}")
    for item in non_goals:
        lines.append(f"- Non-goal and must not be implied as supported: {item}")
    for item in review_bound_lines[:5]:
        lines.append(f"- Forbidden assumption: {item}")
    return lines


def render_prototype_prompt_workflow_backbone_lines(route_entries: list[dict[str, str]]) -> list[str]:
    lines = ["", "Workflow backbone that must remain operable:"]
    for index, entry in enumerate(route_entries, start=1):
        lines.extend(
            [
                f"- Step {index}:",
                f"  - From page: {entry['from_page']}",
                f"  - User goal: {entry['user_goal']}",
                f"  - System response: {entry['system_response']}",
                f"  - To page: {entry['to_page']}",
                f"  - Context continuity: {entry['context_that_must_survive_navigation']}",
            ]
        )
    return lines


def render_prototype_prompt_delivery_review_lines(
    *,
    product_name: str,
    acceptance_lines: list[str],
    output_contract_name: str,
    persona_lines: list[str],
    design_requirement_lines: list[str],
    global_design_rules: list[str],
    assumption_lines: list[str],
) -> list[str]:
    lines = [
        "",
        "Homepage / first screen requirements:",
        f"- Present the product explicitly as `{product_name}`.",
        "- Explain what workflow the product supports, who it serves, and where the operator should start.",
        "- The first screen must expose a real entry into the workflow, not only explanatory copy.",
        "- The first screen must feel like a product workbench or governed setup/dashboard, not a slideshow or demo launcher.",
        "",
        "Language and terminology:",
        "- Keep upstream page names and domain nouns recognizable.",
        "- Prefer business-facing copy over engineering copy.",
        "- Do not replace product nouns with generic labels such as workspace, module, panel, console, playground, or explorer.",
        "",
        "Required deliverables from the external AI run:",
        "- A clickable multi-page prototype or a small multi-file HTML site.",
        "- One homepage / entry page plus the full first-wave workflow pages.",
        "- Real form controls for the required inputs or confirmations.",
        "- Empty, loading, blocked, and error states on the pages where those states matter.",
        "- Visible carry-forward context when moving between dependent pages.",
        "",
        "Acceptance checklist before you stop:",
    ]
    for item in acceptance_lines or ["Acceptance criteria remain visible through the workflow pages."]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "- Confirm that the output reads like a business product for operators, not a framework demo.",
            "- Confirm that each workflow page exposes both required data and the next user action.",
            "- Confirm that deferred and non-goal items are not silently promoted into the visible product.",
            "```",
            "",
            "## 3. Human Review Notes",
            "- Reviewers may iterate visual styling, hierarchy, and microcopy with the external AI.",
            f"- Reviewers must not break the contract in `{output_contract_name}` while refining high-fidelity output.",
            "- If external exploration reveals missing product truths, update the Phase-1/Phase-2 source artifacts rather than silently patching the prototype only.",
            "",
            "## 4. Upstream Signals Preserved",
            "- persona_context_signal:",
        ]
    )
    lines.extend(format_bullet_list(persona_lines or ["Primary persona context still centers on the business workflow operator."]))
    lines.extend(["- design_requirement_signal:"])
    lines.extend(format_bullet_list(design_requirement_lines or global_design_rules or ["Design remains workflow-first and action-chain preserving."]))
    lines.extend(["- assumptions_to_watch:"])
    lines.extend(format_bullet_list(assumption_lines or ["The first-wave workflow still depends on an honest handoff between pages."]))
    return lines


def build_prototype_prompt_pack_lines(
    *,
    version: str,
    owner: str,
    product_name: str,
    product_promise: str,
    primary_operator: str,
    pages: list[dict[str, object]],
    route_entries: list[dict[str, str]],
    current_product_context_lines: list[str],
    first_wave_scope: list[str],
    deferred_items: list[str],
    non_goals: list[str],
    review_bound_lines: list[str],
    global_design_rules: list[str],
    assumption_lines: list[str],
    persona_lines: list[str],
    design_requirement_lines: list[str],
    acceptance_lines: list[str],
    output_contract_name: str,
) -> list[str]:
    lines: list[str] = [
        "# Prototype Prompt Pack",
        "",
        "## 1. Metadata",
        "- document_name: `prototype-prompt-pack.md`",
        "- artifact_id: `P1-S05-PROMPT-001`",
        f"- version: `{version}`",
        "- status:",
        "  - `review`",
        f"- owner: `{owner}`",
        "- derived_from_contract:",
        f"  - `{output_contract_name}`",
        "  - `P1-S05-SPEC-001`",
        "- artifact_role:",
        "  - `derived supplementary prompt guidance`",
        "- authority_status:",
        "  - `non-authoritative / must not override page-level contract`",
        "- intended_user:",
        "  - `human designer / PM working with external AI`",
        "- downstream_usage_rule:",
        "  - This pack is for high-fidelity prototype generation outside the framework runtime.",
        "  - Treat it as supplementary only.",
        "  - Do not treat it as a substitute for the implementation-facing contract.",
        "  - Do not add, replace, or mutate page authority fields already frozen in `prototype-spec.md`.",
        "",
        "## 2. External AI Prompt",
        "Copy the prompt below into the external design / HTML generation system. Keep the non-negotiable contract intact.",
        "",
        "```text",
        f"You are designing a high-fidelity prototype for the product `{product_name}`.",
        "",
        "Product framing:",
        f"- Product value promise: {product_promise}",
        f"- Primary operator: {primary_operator}",
    ]
    if current_product_context_lines:
        lines.append("- Product context:")
        for item in current_product_context_lines[:3]:
            lines.append(f"  - {item}")
    lines.extend(
        [
            "",
            "Design objective:",
            "- Create a terminal-user-facing business application prototype, not a demo shell, API explorer, runtime console, acceptance dashboard, or stepper-driven showcase.",
            "- The prototype must feel like a usable product for the named operator on day one, even if styling remains MVP-level.",
            "- Every primary page must let the user see the required business context and take the next workflow action directly on the page.",
            "- This prompt pack is derived supplementary guidance; when it conflicts with `prototype-spec.md`, the spec wins.",
        ]
    )
    lines.extend(
        render_prototype_prompt_product_truth_lines(
            first_wave_scope,
            deferred_items,
            non_goals,
            review_bound_lines,
        )
    )
    lines.extend(
        [
            "",
            "Allowed design exploration:",
            "- You may choose visual hierarchy, spacing, component styling, typography, and layout treatment.",
            "- You may simplify the visual system for MVP delivery, but the output must still look and behave like a real product surface for business operators.",
            "",
            "Forbidden output patterns:",
            "- No API explorer framing.",
            "- No debug console framing.",
            "- No acceptance harness framing.",
            "- No homepage dominated by step cards, generic walkthrough cards, or engineering scaffolding language.",
            "- No page that only dumps contracts or instructions without giving the user an operable surface.",
        ]
    )
    lines.extend(render_prototype_prompt_workflow_backbone_lines(route_entries))
    lines.extend(render_prototype_prompt_page_contract_lines(pages))
    lines.extend(
        render_prototype_prompt_delivery_review_lines(
            product_name=product_name,
            acceptance_lines=acceptance_lines,
            output_contract_name=output_contract_name,
            persona_lines=persona_lines,
            design_requirement_lines=design_requirement_lines,
            global_design_rules=global_design_rules,
            assumption_lines=assumption_lines,
        )
    )
    return lines


def main() -> int:
    global CURRENT_OUTPUT_LOCALE

    parser = argparse.ArgumentParser(description="Generate a Stage-05 prototype-spec artifact")
    parser.add_argument("--prd", required=True)
    parser.add_argument("--stage-02a", required=True)
    parser.add_argument("--stage-03", required=True)
    parser.add_argument("--stage-04", required=True)
    parser.add_argument("--stage-02b")
    parser.add_argument("--output", required=True)
    parser.add_argument("--prompt-pack-output")
    parser.add_argument("--version", required=True)
    parser.add_argument("--owner", default="Codex Stage-05 prototype-spec generator")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    args = parser.parse_args()

    CURRENT_OUTPUT_LOCALE = resolve_output_locale(args.output_locale)

    paths = resolve_prototype_spec_paths(args)
    source_texts = read_prototype_spec_source_texts(paths)
    source_sections = extract_prototype_spec_source_sections(source_texts)
    artifact_ids = extract_prototype_spec_artifact_ids(source_texts)

    module_matrix_rows = extract_module_rows_from_text(source_texts.prd_text, source_texts.stage_02b_text)
    current_product_context_lines = first_nonempty_lines(source_sections.executive_summary, 3)
    non_goals = parse_bullets(source_sections.out_of_scope_block)
    review_bound_lines = parse_named_list(source_sections.review_bound_block, "must_not_assume") or first_nonempty_lines(
        source_sections.review_bound_block,
        6,
    )
    flow_steps = parse_numbered_steps(source_sections.business_flow_block)
    state_machine = parse_state_machine(source_sections.state_machine_block)
    acceptance_lines = parse_bullets(source_sections.acceptance_block)[:5]
    design_start_rules = parse_bullets(source_sections.design_start_block)
    carryover_lines = parse_carryover_summaries(source_sections.carryover_block, 3)
    deferred_lines = parse_deferred_honesty_summaries(source_sections.deferred_block, 3)
    assumption_lines = parse_assumption_statements(source_sections.assumptions_block)
    persona_lines = parse_bullet_values(source_sections.persona_context_block, 3)
    design_requirement_lines = parse_design_requirement_summaries(source_sections.design_requirements_block, 4)
    supporting_use_cases = parse_supporting_use_cases(source_sections.use_cases_block)
    use_case_evidence_map = build_use_case_evidence_map(source_sections.use_cases_block, supporting_use_cases, flow_steps)
    deferred_items = parse_named_list(source_texts.stage_03_text, "deferred_items")
    first_wave_scope = parse_named_list(source_texts.stage_03_text, "first_slice")
    later_slices = parse_named_list(source_texts.stage_03_text, "later_slices")
    global_design_rules = design_start_rules[:4]
    core_objects = parse_core_business_objects(source_sections.core_objects_block)

    if not module_matrix_rows:
        raise SystemExit("Prototype spec generation requires a Module Responsibility Matrix or equivalent Phase-1 module table")

    pages = build_pages(module_matrix_rows, core_objects)
    flow_pages = assign_flow_pages(flow_steps, pages)
    page_step_numbers = build_page_step_numbers(flow_pages)
    bind_supporting_use_cases_to_pages(
        pages,
        supporting_use_cases,
        use_case_evidence_map=use_case_evidence_map,
        page_step_numbers=page_step_numbers,
    )
    mainline_pages = apply_prototype_page_authority_contracts(pages, flow_pages)

    route_entries = build_route_entries(flow_steps, flow_pages or mainline_pages)

    product_name = normalize_product_name(extract_document_title(source_texts.prd_text), paths.prd_path.stem)
    product_promise = choose_product_value_promise(current_product_context_lines)
    primary_operator = persona_lines[0] if persona_lines else "primary workflow operator"

    prototype_scope_note = (
        "Stage-05 keeps the first-wave workflow bounded to the primary operating loop. "
        "Deferred and explicit out-of-scope items remain visible so the prototype does not create false completeness."
    )

    lines: list[str] = [
        "# Prototype Spec",
        "",
        "## 1. Document Metadata",
        "- document_name: `prototype-spec.md`",
        "- stage:",
        "  - `prototype-spec-bridging`",
        f"- version: `{args.version}`",
        "- status:",
        "  - `review`",
        f"- owner: `{args.owner}`",
        "- source_status:",
        "  - `mixed`",
        "",
        "## 1.1 Traceability Naming and Registry",
        "- artifact_id: `P1-S05-SPEC-001`",
        "- artifact_type:",
        "  - `SPEC`",
        "- depends_on:",
        f"  - `{artifact_ids['stage_02a']}`",
        f"  - `{artifact_ids['stage_03']}`",
        f"  - `{artifact_ids['stage_04']}`",
    ]
    if source_texts.stage_02b_text:
        lines.append(f"  - `{artifact_ids['stage_02b']}`")
    lines.extend(
        [
            f"  - `{paths.prd_path.name}`",
            "- feeds:",
            "  - `P1-S05-SURFACE-MATRIX-001 (expected)`",
            "  - `P2-DESIGN-INPUT-001 (expected)`",
            "  - `P1-S05-PROMPT-001 (derived supplementary)`",
            "- traceability_managed_by:",
            "  - `wff-base-traceability-management`",
            "- trace_binding_note:",
            "  - Stage-05 freezes the page-level Surface Matrix authority derived from the converged PRD and late-stage outputs; it does not modify the PRD mainline.",
            "",
            "## 2. Context and Objective",
            "- current_product_context:",
        ]
    )
    lines.extend(format_bullet_list(current_product_context_lines or ["Prototype should express the first-wave business workflow without broadening product scope."]))
    lines.extend(
        [
            "- product_identity_contract:",
            f"  - product_name: `{product_name}`",
            f"  - primary_operator: `{primary_operator}`",
            f"  - first_wave_value_promise: {product_promise}",
            "- prototype_goal:",
            "  - Freeze the page-level Surface Matrix authority so downstream Phase-1, Phase-2, and derived prototype guidance can consume one stable page contract.",
            "- authority_role:",
            "  - `P1 Surface Matrix authority`",
            "- intended_consumers:",
            "  - `Phase-1 downstream authoring`",
            "  - `Phase-2 engineering alignment`",
            "  - `derived prototype prompt-pack generator`",
            "  - `design review`",
            "  - `architecture review`",
            "- supplementary_artifacts:",
            "  - `prototype-prompt-pack.md` is derived supplementary guidance only; it must not replace page-level authority",
            "- upstream_design_guardrails:",
        ]
    )
    lines.extend(format_bullet_list(global_design_rules or ["Do not let visual completeness hide deferred, blocked, or review-bound truth."]))
    lines.extend(["- assumptions:"])
    lines.extend(format_bullet_list(assumption_lines or ["The first-wave handoff between pages remains the key proof point."]))
    lines.extend(
        [
            "- open_questions:",
            "  - How much visual hierarchy and guidance is needed before onboarding friction becomes too high?",
            "  - Which state surfaces need the strongest emphasis in the prototype review round?",
            "",
            "## 3. Prototype Scope and Boundary",
            "- prototype_scope:",
            "  - first_wave_in_scope:",
        ]
    )
    lines.extend(format_bullet_list(first_wave_scope, 4))
    lines.extend(["  - later_slices:"])
    lines.extend(format_bullet_list(later_slices, 4))
    lines.extend(["  - deferred_items:"])
    lines.extend(format_bullet_list(deferred_items, 4))
    lines.extend(["  - non_goals:"])
    lines.extend(format_bullet_list(non_goals, 4))
    lines.extend(
        [
            "- scope_boundary_note:",
            f"  - {prototype_scope_note}",
            "- forbidden_assumptions:",
        ]
    )
    lines.extend(format_bullet_list(review_bound_lines or ["Do not treat inferred UI detail as confirmed product truth."], 2))
    lines.extend(render_prototype_page_map_lines(pages))
    lines.extend(render_prototype_main_flow_lines(route_entries, pages))
    lines.extend(render_prototype_page_brief_lines(pages, state_machine, global_design_rules))
    lines.extend(render_prototype_object_state_matrix_lines(core_objects, pages, state_machine))
    lines.extend(render_prototype_state_and_generation_constraint_lines(product_name))
    lines.extend(
        [
            "",
            "## 10. Provenance / Confidence / Verification",
            "- source:",
            "  - `mixed`",
            "- confidence:",
            "  - `medium`",
            "- verification:",
            "  - `required`",
            "- prototype_inference_log:",
            "  - inference_1:",
            "    - inferred_item: `page-level grouping and route simplification details`",
            "    - why_needed: Stage-05 must convert workflow and IA direction into executable page structure.",
            "    - why_safe_enough: core object chain, state machine, and first-wave scope are already explicit upstream.",
            "    - what_breaks_if_wrong: HTML prototype may mislead reviewers about action order or page emphasis.",
            "  - inference_2:",
            "    - inferred_item: `state surface emphasis per page`",
            "    - why_needed: upstream defines core states, but prototype execution still needs page-level state surfacing decisions.",
            "    - why_safe_enough: state-machine and acceptance-criteria signals bound the allowable variants.",
            "    - what_breaks_if_wrong: empty, error, or blocked review may look cleaner than the product truth.",
            "- ai_inferred_marker:",
            "  - `AI-INFERRED DRAFT -- UNVERIFIED`",
        ]
    )
    lines.extend(
        render_prototype_reasoning_evidence_lines(
            ia_alternatives_block=source_sections.ia_alternatives_block,
            mainline_pages=mainline_pages,
            state_machine=state_machine,
            deferred_items=deferred_items,
            non_goals=non_goals,
        )
    )
    lines.extend(render_prototype_diagram_and_acceptance_lines(mainline_pages))
    lines.extend(
        render_prototype_reference_and_source_note_lines(
            paths=paths,
            persona_lines=persona_lines,
            design_requirement_lines=design_requirement_lines,
            carryover_lines=carryover_lines,
            deferred_lines=deferred_lines,
            acceptance_lines=acceptance_lines,
        )
    )

    prompt_pack_lines = build_prototype_prompt_pack_lines(
        version=args.version,
        owner=args.owner,
        product_name=product_name,
        product_promise=product_promise,
        primary_operator=primary_operator,
        pages=pages,
        route_entries=route_entries,
        current_product_context_lines=current_product_context_lines,
        first_wave_scope=first_wave_scope,
        deferred_items=deferred_items,
        non_goals=non_goals,
        review_bound_lines=review_bound_lines,
        global_design_rules=global_design_rules,
        assumption_lines=assumption_lines,
        persona_lines=persona_lines,
        design_requirement_lines=design_requirement_lines,
        acceptance_lines=acceptance_lines,
        output_contract_name=paths.output_path.name,
    )

    spec_lines = render_primary_locale_lines(
        lines,
        paths.output_path.name,
        CURRENT_OUTPUT_LOCALE,
        preserve_table_body_literals=True,
    )
    prompt_pack_lines = render_primary_locale_lines(
        prompt_pack_lines,
        paths.prompt_pack_output_path.name,
        CURRENT_OUTPUT_LOCALE,
    )

    paths.output_path.write_text("\n".join(spec_lines).rstrip() + "\n", encoding="utf-8")
    paths.prompt_pack_output_path.write_text("\n".join(prompt_pack_lines).rstrip() + "\n", encoding="utf-8")
    print(f"prototype_spec: {paths.output_path}")
    print(f"prototype_prompt_pack: {paths.prompt_pack_output_path}")
    print(f"prd: {paths.prd_path}")
    print("FINAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
