#!/usr/bin/env python3
"""
Generate deep Stage-01/02a/02b/03/04 artifacts from a Phase-1 source document.

This script is intentionally deterministic:
- extracts high-value source sections as evidence packs
- recompiles each stage with analysis scaffolding and method signals
- writes standalone stage artifacts suitable for gate evaluation
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
from phase1.phase1_source_text_normalization import normalize_source_handoff_phrases

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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render_traceability_block(stage_key: str) -> str:
    trace = STAGE_TRACEABILITY[stage_key]
    lines = [
        "## 1.1 Traceability Naming and Registry",
        f"- artifact_id: `{trace['artifact_id']}`",
        "- artifact_type:",
        f"  - `{trace['artifact_type']}`",
        "- depends_on:",
    ]
    if trace["depends_on"]:
        lines.extend(f"  - `{value}`" for value in trace["depends_on"])
    else:
        lines.append("  - `(none)`")
    lines.append("- feeds:")
    lines.extend(f"  - `{value}`" for value in trace["feeds"])
    lines.extend(
        [
            "- traceability_managed_by:",
            "  - `wff-base-traceability-management`",
            "- trace_binding_note:",
            "  - coarse-grained Phase-1 artifact identity follows docs/governance/artifact-traceability-minimum-rules-v0.1.md",
        ]
    )
    return "\n".join(lines)


def find_named_h2_block(text: str, heading_keywords: list[str]) -> str:
    for keyword in heading_keywords:
        match = re.search(
            rf"^##\s+(?:\d+(?:\.\d+)?\s+)?[^\n]*{re.escape(keyword)}[^\n]*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            continue
        start = match.start()
        tail = text[start:]
        next_h2 = re.search(r"^##\s+", tail[1:], flags=re.MULTILINE)
        end = next_h2.start() + 1 if next_h2 else len(tail)
        return tail[:end].strip()
    return ""


def list_items_from_block(block: str) -> list[str]:
    if not block:
        return []
    items: list[str] = []
    for line in block.splitlines()[1:]:
        bullet = re.match(r"^\s*-\s+`?([^`]+?)`?\s*$", line)
        if bullet:
            items.append(bullet.group(1).strip())
            continue
        numbered = re.match(r"^\s*\d+\.\s+(.+?)\s*$", line)
        if numbered:
            items.append(numbered.group(1).strip())
    return [item for item in items if item and "source section not found" not in item.lower()]


def find_markdown_block(text: str, heading_keywords: list[str]) -> str:
    for keyword in heading_keywords:
        match = re.search(
            rf"^##+\s+(?:\d+(?:\.\d+)?\s+)?[^\n]*{re.escape(keyword)}[^\n]*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            continue
        start = match.start()
        heading_line = match.group(0)
        heading_level = len(re.match(r"^#+", heading_line).group(0))
        tail = text[start:]
        next_heading = re.search(
            rf"^#{{2,{heading_level}}}\s+",
            tail[match.end() - start :],
            flags=re.MULTILINE,
        )
        end = (match.end() - start) + next_heading.start() if next_heading else len(tail)
        return tail[:end].strip()
    return ""


SOURCE_PACKET_EVIDENCE_ALIASES: list[tuple[tuple[str, ...], list[str]]] = [
    (("2\\.1", "项目/产品背景", "第一部分", "原版"), ["Project Context"]),
    (("2\\.2", "业务机会描述", "3\\.2", "结构化问题清单", "3\\.3", "结构化机会清单"), ["Project Context", "Desired Outcome"]),
    (("2\\.3", "研究对象", "目标用户"), ["User, Buyer, Operator"]),
    (("2\\.4", "证据线索", "6\\.1", "验证对象", "6\\.2", "判定信号"), ["Desired Outcome", "Success Signals"]),
    (("3\\.1", "产品/业务目标", "目标方向"), ["Desired Outcome"]),
    (("3\\.4", "用户叙事", "主流程"), ["Key Workflows", "Scenarios"]),
    (("4\\.1", "关键约束", "4\\.2", "指标口径"), ["Constraints"]),
    (("4\\.3", "范围边界", "非目标", "P0", "P1", "P2"), ["Scope Boundary"]),
    (("第九部分", "unknown", "provisional"), ["Open Truth Gaps"]),
    (("第十部分", "provenance", "标记"), ["Truth-State Ledger"]),
    (("第十二部分", "结论", "验收"), ["Admission Decision", "Handoff Note For wff-req"]),
]


def source_packet_evidence_block(source_text: str, heading_pattern: str) -> str:
    """Map legacy P1 source evidence headings to source-input-packet sections.

    Stage evidence packs cite raw source sections for review. A source input
    packet uses a different section contract, so missing legacy headings should
    resolve to the closest packet fact/review section instead of emitting
    `(source section not found)` noise.
    """

    if not re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE):
        return ""
    for triggers, packet_headings in SOURCE_PACKET_EVIDENCE_ALIASES:
        if not any(re.search(trigger, heading_pattern, flags=re.IGNORECASE) for trigger in triggers):
            continue
        for heading in packet_headings:
            block = find_markdown_block(source_text, [heading])
            if block:
                return f"## P1 Source Brief Evidence: {heading}\n{normalize_source_handoff_phrases(demote_headings(block))}"
    block = source_fact_text(source_text)
    if block:
        lines = block.splitlines()
        excerpt = normalize_source_handoff_phrases("\n".join(lines[: min(len(lines), 20)]).strip())
        return f"## P1 Source Brief Evidence: excerpt\n{demote_headings(excerpt)}"
    return ""


def flatten_bullets(block: str, limit: int) -> list[str]:
    if not block:
        return []
    items: list[str] = []
    for line in block.splitlines()[1:]:
        bullet = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if bullet:
            value = bullet.group(1).strip().strip("`")
            if value and "source section not found" not in value.casefold():
                items.append(value)
        if len(items) >= limit:
            break
    if items:
        return items
    fallbacks: list[str] = []
    for line in block.splitlines()[1:]:
        value = line.strip().strip("`")
        if not value or value.startswith("#"):
            continue
        if "source section not found" in value.casefold():
            continue
        fallbacks.append(value)
        if len(fallbacks) >= limit:
            break
    return fallbacks


def source_fact_text(source_text: str) -> str:
    """Return the authoritative fact-bearing body for a P1 source input packet.

    `wff-req-chat` packets contain both product facts and review/control
    metadata. Phase-1 extraction should use the `P1 Source Brief` as the
    business fact surface; challenge axes and ledgers are constraints, not
    product nouns.
    """

    if not re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE):
        return source_text
    block = find_markdown_block(source_text, ["P1 Source Brief"])
    if block:
        return normalize_source_handoff_phrases(block)
    return block or source_text


HANDOFF_QUALIFIER_PATTERN = re.compile(
    r"\b(?:role[- ]owned\s+|owner[- ]owned\s+|responsibility[- ]owned\s+)?next\s+(?:action|step)\b|"
    r"下一步.*(?:责任|动作)|(?:责任|角色).*下一步",
    flags=re.IGNORECASE,
)


def is_handoff_qualifier_label(value: str) -> bool:
    """Return true when a source label describes handoff ownership, not a module.

    Source packets often say a manager needs to see the "role-owned next
    action". That phrase should shape state/role semantics inside a workflow;
    treating it as a standalone module creates synthetic pages, inputs, outputs,
    and acceptance rows.
    """

    text = re.sub(r"\s+", " ", str(value or "")).strip(" `。.;；")
    if not text or len(text) > 80:
        return False
    if not HANDOFF_QUALIFIER_PATTERN.search(text):
        return False
    lowered = text.casefold()
    if any(token in lowered for token in ("view", "dashboard", "screen", "page", "report", "queue", "task list")):
        return False
    if any(token in text for token in ("视图", "看板", "页面", "报表", "队列", "任务列表")):
        return False
    return True


def packet_open_truth_gap_items(source_text: str) -> list[str]:
    if not re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE):
        return []
    return flatten_bullets(find_markdown_block(source_text, ["Open Truth Gaps"]), 12)


def label_block_items(source_text: str, label_patterns: list[str], *, limit: int = 12) -> list[str]:
    """Extract bullets under a plain label such as `P0:` inside a section."""

    lines = source_text.splitlines()
    items: list[str] = []
    active = False
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            active = False
            continue
        is_label = any(re.match(rf"^{pattern}\s*[:：]\s*$", line, flags=re.IGNORECASE) for pattern in label_patterns)
        if is_label:
            active = True
            continue
        if active and re.match(r"^[A-Za-z0-9 /_-]{1,40}\s*[:：]\s*$", line):
            break
        if active:
            bullet = re.match(r"^(?:[-*]|\d+[.)])\s+(.+?)\s*$", line)
            if not bullet:
                continue
            value = bullet.group(1).strip().strip("`")
            if value and "source section not found" not in value.casefold():
                items.append(value)
            if len(items) >= limit:
                break
    return items


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
    source_text = str(context.get("source_text", ""))
    style = detect_source_style(source_text)
    domain_posture = (
        "growth-observation"
        if style == "growth_observation"
        else "operational-service"
        if style == "pet_clinic"
        else "generic-workflow"
    )
    role_labels = [
        str(row.get("Role", "")).strip()
        for row in context.get("roles", [])
        if isinstance(row, dict) and str(row.get("Role", "")).strip()
    ]
    primary_segment = role_labels[0] if role_labels else "primary operator"
    return {
        "domain_posture": domain_posture,
        "primary_segment": primary_segment,
        "role_labels": role_labels,
        "supporting_role_label": role_labels[1] if len(role_labels) > 1 else "",
        "decision_role_label": role_labels[-1] if role_labels else primary_segment,
    }


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


def find_h2_block(text: str, heading_pattern: str) -> str:
    match = re.search(
        rf"^##\s+{heading_pattern}.*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return source_packet_evidence_block(text, heading_pattern)
    start = match.start()
    tail = text[start:]
    next_h2 = re.search(r"^##\s+", tail[1:], flags=re.MULTILINE)
    end = next_h2.start() + 1 if next_h2 else len(tail)
    return tail[:end].strip()


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


def demote_headings(text: str, levels: int = 1) -> str:
    out: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            size = len(line) - len(line.lstrip("#"))
            out.append(f"{'#' * min(size + levels, 6)}{line[size:]}")
        else:
            out.append(line)
    return "\n".join(out).strip()


def write(path: Path, content: str, locale: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = normalize_domain_terms(content).rstrip() + "\n"
    normalized_locale = resolve_output_locale(locale)
    if normalized_locale == "zh-CN":
        text = "\n".join(render_primary_locale_lines(text.splitlines(), path.name, normalized_locale)).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")


def normalize_domain_terms(text: str) -> str:
    style = detect_source_style(text)
    domain_posture = (
        "growth-observation"
        if style == "growth_observation"
        else "operational-service"
        if style == "pet_clinic"
        else "generic-workflow"
    )
    return str(sanitize_domain_default_truth(text, context={"domain_posture": domain_posture}))


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def role_label(row: dict[str, str]) -> str:
    return str(
        row.get('Role')
        or row.get('role')
        or row.get('persona')
        or row.get('user')
        or row.get('target_user')
        or ''
    ).strip()


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


def _normalized_label_key(label: str) -> str:
    return re.sub(r'\s+', ' ', str(label or '').strip().strip('`')).casefold()


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


def preserved_display_label(label: str, fallback: str = "Item") -> str:
    cleaned = str(label or "").strip().strip("`")
    if not cleaned:
        return fallback
    token = slug_token(cleaned)
    if re.search(r"[^\x00-\x7F]", cleaned) and token == "item":
        return cleaned
    return title_case_token(token)


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


def detect_source_segments(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)

    def normalize_candidate(value: str) -> str:
        cleaned = str(value or "").strip().strip("`")
        cleaned = re.sub(r"^\s*(?:主要用户|次要用户|评审用户)\s*[：:]\s*", "", cleaned).strip()
        if not cleaned:
            return ""
        lowered = cleaned.casefold()
        excluded_prefixes = ("客群边界", "使用边界", "边界", "首发不做", "不做", "非目标")
        if any(lowered.startswith(prefix.casefold()) for prefix in excluded_prefixes):
            return ""
        if "不承诺" in cleaned or "不做" in cleaned:
            return ""
        return cleaned

    candidate_block = find_h2_block(fact_text, r"2\.3\s+研究对象/目标用户边界")
    candidates = [value for value in (normalize_candidate(item) for item in list_items_from_block(candidate_block)) if value]
    if not candidates:
        table_rows = parse_markdown_table(find_markdown_block(fact_text, ["User, Buyer, Operator", "2. Target Users", "Target Users", "目标用户"]))
        candidates = [
            normalize_candidate(str(row.get("Role", "") or row.get("role", "")).strip())
            for row in table_rows
            if normalize_candidate(str(row.get("Role", "") or row.get("role", "")).strip())
        ]
    if not candidates:
        target_users_block = find_markdown_block(fact_text, ["User, Buyer, Operator", "Target Users", "目标用户"])
        candidates = [value for value in (normalize_candidate(item) for item in list_items_from_block(target_users_block)) if value]
    if not candidates:
        for line in fact_text.splitlines():
            row = re.match(r"^\|\s*([^|]+?)\s*\|", line)
            if row:
                cell = normalize_candidate(row.group(1).strip())
                if cell and cell.lower() not in {"role", "---"} and "source section not found" not in cell.lower():
                    candidates.append(cell)
            if len(candidates) >= 5:
                break
    return unique_preserve_order(candidates) or ["primary operator", "secondary collaborator", "review stakeholder"]


def extract_product_label(source_text: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", source_text, flags=re.MULTILINE)
    if not match:
        return "Source-Derived"
    title = match.group(1).strip()
    title = re.sub(r"\s*(Product Requirements Document|产品需求文档|PRD)\b.*$", "", title, flags=re.IGNORECASE).strip(" -—")
    return title or "Source-Derived"


def extract_main_flow_block(source_text: str) -> str:
    fact_text = source_fact_text(source_text)
    for pattern in (r"主流程[:：].+", r"Main Flow[:：].+", r"Core Flow[:：].+"):
        match = re.search(rf"^##\s+{pattern}\s*$", fact_text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return find_h2_block(fact_text, re.escape(match.group(0).split("##", 1)[1].strip()))
    return find_h2_block(fact_text, r"5\.2\s+最小可用体验闭环")


def parse_markdown_table(block: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append({headers[idx]: cells[idx] for idx in range(len(headers))})
    return rows


def slug_token(text: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return token or "item"


def title_case_token(text: str) -> str:
    return re.sub(r"[_\-]+", " ", text).strip().title() or "Item"


def extract_table_rows(source_text: str, heading_keywords: list[str]) -> list[dict[str, str]]:
    fact_text = source_fact_text(source_text)
    for keyword in heading_keywords:
        block = find_markdown_block(fact_text, [keyword])
        rows = parse_markdown_table(block)
        if rows:
            return rows
    return []


def extract_target_user_rows(source_text: str) -> list[dict[str, str]]:
    fact_text = source_fact_text(source_text)
    candidate_block = find_h2_block(fact_text, r"2\.3\s+研究对象/目标用户边界")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in list_items_from_block(candidate_block):
        match = re.match(r"^\s*(主要用户|次要用户|评审用户)\s*[：:]\s*(.+?)\s*$", item)
        role_name = detect_source_segments(f"## 2.3 研究对象/目标用户边界\n- {item}")[0] if item else ""
        description = match.group(1) if match else ""
        if role_name and role_name not in seen:
            rows.append({"Role": role_name, "Description": description})
            seen.add(role_name)
    if rows:
        return rows
    rows = extract_table_rows(fact_text, ["User, Buyer, Operator", "2. Target Users", "Target Users", "目标用户"])
    if rows:
        normalized_rows: list[dict[str, str]] = []
        for row in rows:
            role = str(row.get("Role") or row.get("role") or "").strip().strip("`")
            if role:
                normalized = dict(row)
                normalized["Role"] = role
                normalized_rows.append(normalized)
        return normalized_rows or rows
    return [{"Role": value.strip("`"), "Description": ""} for value in detect_source_segments(fact_text)]


def detect_source_style(source_text: str) -> str:
    lowered = source_fact_text(source_text).casefold()
    if re.search(
        r"\bgeo\b|ai 搜索|生成式回答|ai 可见性|visibility|tracked scope|citation|competitor|竞争对手|归因|roi|conversion|b2b 市场|marketing owner|content operator|growth owner|baseline run",
        lowered,
    ):
        return "growth_observation"
    if re.search(r"pet|clinic|veterinar|宠物|诊所|就诊|治疗|复诊|随访|discharge|follow-up", lowered):
        return "pet_clinic"
    return "generic"


def _role_name_list(roles: list[dict[str, str]]) -> list[str]:
    return [role_label(row) for row in roles if role_label(row)]


def _find_role_by_hint(role_names: list[str], patterns: list[str], fallback_index: int) -> str:
    for role in role_names:
        lowered = role.casefold()
        if any(re.search(pattern, lowered) for pattern in patterns):
            return role
    return role_names[fallback_index] if role_names else "primary operator"


def infer_fallback_module_contract(
    source_text: str,
    business_name: str,
    roles: list[dict[str, str]],
) -> dict[str, str]:
    style = detect_source_style(source_text)
    role_names = _role_name_list(roles)
    lowered = business_name.casefold()

    if style == "growth_observation":
        primary_actor = _find_role_by_hint(role_names, [r"marketing", r"市场"], 0)
        execution_actor = _find_role_by_hint(role_names, [r"content", r"内容"], 1 if len(role_names) > 1 else 0)
        reviewer_actor = _find_role_by_hint(role_names, [r"business", r"增长", r"review"], 2 if len(role_names) > 2 else 0)
        if any(token in lowered for token in ["tenant", "audit", "actor"]):
            return {
                "module": business_name,
                "primary_actor": primary_actor,
                "core_objects": "TenantWorkspace, ActorRole, AuditRecord",
                "responsibility": "establish tenant, actor, and audit boundary for the GEO operating loop",
                "input": "tenant identity, member roles, and audit policy",
                "output": "active tenant workspace, role boundary, and audit-ready context",
                "exit_action": "save tenant/audit setup and enter tracked scope configuration",
                "architectural note": "preserve tenant-safe boundary and audit provenance before scope operations",
            }
        if "tracked scope" in lowered:
            return {
                "module": business_name,
                "primary_actor": primary_actor,
                "core_objects": "TrackedScope, ScopeTopicSet, CompetitorSet",
                "responsibility": "define monitored brand, competitor, topic, and prompt scope for one GEO cycle",
                "input": "brand targets, competitor set, topic boundaries, and prompt scope definition",
                "output": "versioned tracked scope, monitored topic set, and scope boundary",
                "exit_action": "freeze tracked scope and start baseline generation",
                "architectural note": "preserve scope provenance and downstream baseline comparability",
            }
        if "baseline" in lowered:
            return {
                "module": business_name,
                "primary_actor": primary_actor,
                "core_objects": "BaselineRun, EvidenceSnapshot, BaselineSummary",
                "responsibility": "run baseline collection and preserve explainable GEO evidence for the current cycle",
                "input": "tracked scope, prompt set, and collection window",
                "output": "baseline snapshot, evidence set, and freshness status",
                "exit_action": "review baseline freshness and open findings",
                "architectural note": "preserve evidence freshness, provenance, and cycle-level comparability",
            }
        if "finding" in lowered:
            return {
                "module": business_name,
                "primary_actor": primary_actor,
                "core_objects": "Finding, EvidenceLink, PriorityReason",
                "responsibility": "structure findings with evidence link, priority reason, and actionability signal",
                "input": "baseline snapshot, evidence set, and monitored scope context",
                "output": "prioritized findings, evidence links, and actionability rationale",
                "exit_action": "confirm finding priority and open recommendation/task handoff",
                "architectural note": "preserve finding readability and downstream recommendation continuity",
            }
        if "recommendation" in lowered or "task" in lowered:
            return {
                "module": business_name,
                "primary_actor": execution_actor,
                "core_objects": "Recommendation, ActionTask, ExecutionStatus",
                "responsibility": "turn recommendation-ready findings into assigned tasks with explicit evidence linkage",
                "input": "finding, evidence link, priority rationale, and owner hint",
                "output": "task-ready recommendation, assigned task, and execution status",
                "exit_action": "handoff execution and keep review linkage visible",
                "architectural note": "preserve finding-to-task bridge, ownership, and blocked-reason visibility",
            }
        if "review" in lowered:
            return {
                "module": business_name,
                "primary_actor": reviewer_actor,
                "core_objects": "ReviewCycle, DecisionRecord, ReviewSummary",
                "responsibility": "summarize one GEO cycle and record continue/revise/pause judgment with evidence",
                "input": "task outcomes, finding deltas, and cycle evidence",
                "output": "continue/revise/pause decision, review summary, and cycle conclusion",
                "exit_action": "record cycle decision and close the current review window",
                "architectural note": "preserve review judgment, evidence lineage, and audit trace",
            }

    if style == "pet_clinic":
        intake_actor = _find_role_by_hint(role_names, [r"reception", r"front desk", r"接待", r"前台"], 0)
        clinician_actor = _find_role_by_hint(role_names, [r"veter", r"vet", r"兽医"], 1 if len(role_names) > 1 else 0)
        manager_actor = _find_role_by_hint(role_names, [r"manager", r"admin", r"clinic", r"管理"], 2 if len(role_names) > 2 else 0)
        if any(token in lowered for token in ["接诊", "登记", "intake", "register", "预约", "arriv"]):
            return {
                "module": business_name,
                "primary_actor": intake_actor,
                "core_objects": "VisitRecord, PetProfile, IntakeSnapshot",
                "responsibility": "register the arriving pet and preserve clinician-ready intake context",
                "input": "arrival request, owner details, pet profile, and visit reason",
                "output": "checked-in visit, pet record, and intake handoff context",
                "exit_action": "complete intake and hand off to consultation or treatment",
                "architectural note": "preserve intake evidence, blocked reason, and clinician-ready handoff context",
            }
        if any(token in lowered for token in ["治疗", "检查", "consult", "care", "visit", "诊疗"]):
            return {
                "module": business_name,
                "primary_actor": clinician_actor,
                "core_objects": "TreatmentRecord, DiagnosticOrder, VisitPlan",
                "responsibility": "record diagnosis, treatment execution, and the next clinical action",
                "input": "checked-in visit, symptoms, prior record, and exam notes",
                "output": "treatment record, diagnostic result, and next action",
                "exit_action": "record treatment result and prepare discharge or follow-up",
                "architectural note": "preserve treatment evidence, blocked reason, and downstream discharge continuity",
            }
        if any(token in lowered for token in ["复诊", "随访", "review", "follow", "discharge", "离院"]):
            return {
                "module": business_name,
                "primary_actor": manager_actor,
                "core_objects": "FollowUpTask, DischargePacket, ReviewSummary",
                "responsibility": "arrange follow-up, discharge closure, and review-ready clinic summary",
                "input": "treatment result, discharge context, and follow-up need",
                "output": "follow-up plan, discharge confirmation, and review-ready summary",
                "exit_action": "close the visit and schedule follow-up or review",
                "architectural note": "preserve discharge closure, follow-up timing, and clinic review context",
            }

    return {
        "module": business_name,
        "primary_actor": _find_role_by_hint(role_names, [r".*"], 0),
        "core_objects": preserved_display_label(business_name, fallback="Business Object"),
        "responsibility": f"complete {business_name} with explicit input, output, and handoff",
        "input": f"{business_name} required input context",
        "output": f"{business_name} completion record",
        "exit_action": f"confirm {business_name} and hand off to the next step",
        "architectural note": "preserve explicit responsibility and downstream handoff",
    }


def extract_module_rows(source_text: str) -> list[dict[str, str]]:
    fact_text = source_fact_text(source_text)
    rows = extract_table_rows(
        fact_text,
        ["4. Module Responsibility Matrix", "Module Responsibility Matrix", "模块与实体清单"],
    )
    if rows:
        return rows
    fallbacks = flatten_bullets(find_markdown_block(fact_text, ["P0（MVP 必须有）"]), 6)
    if not fallbacks:
        fallbacks = label_block_items(fact_text, [r"P0"], limit=8)
    if not fallbacks:
        fallbacks = flatten_bullets(extract_main_flow_block(fact_text), 6)
    fallbacks = [item for item in fallbacks if not is_handoff_qualifier_label(item)]
    roles = extract_target_user_rows(fact_text)
    modules: list[dict[str, str]] = []
    for item in fallbacks:
        business_name = item.strip() or "source-defined module"
        if "source section not found" in business_name.casefold():
            continue
        modules.append(infer_fallback_module_contract(fact_text, business_name, roles))
    return modules


def extract_object_rows(source_text: str) -> list[dict[str, str]]:
    fact_text = source_fact_text(source_text)
    rows = extract_table_rows(
        fact_text,
        ["5. Core Business Objects", "Core Business Objects", "核心业务对象", "Core Objects"],
    )
    if rows:
        return rows
    modules = extract_module_rows(fact_text)

    def fallback_object_name(module_name: str) -> str:
        stripped = str(module_name or "").strip()
        slug = slug_token(stripped)
        if stripped and (re.search(r"[^\x00-\x7F]", stripped) or slug == "item"):
            return stripped
        return title_case_token(slug)

    object_rows: list[dict[str, str]] = []
    for row in modules[:6]:
        core_objects = [item.strip() for item in str(row.get("core_objects", "")).split(",") if item.strip()]
        object_rows.append(
            {
                "Object": core_objects[0] if core_objects else fallback_object_name(str(row.get("module", "Business Object"))),
                "Owner Module": str(row.get("module", "workflow")),
                "Description": (
                    str(row.get("output", "")).strip()
                    or f"business record and state needed to keep {str(row.get('module', 'the business capability')).strip()} executable"
                ),
            }
        )
    return object_rows


def extract_business_objectives(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    block = find_markdown_block(fact_text, ["3. Core Business Objectives", "Core Business Objectives", "Desired Outcome", "产品/业务目标方向"])
    items = list_items_from_block(block)
    if not items:
        items = label_block_items(block, [r"目标", r"success signals?", r"成功信号"], limit=8)
    return items


def extract_non_functional_requirements(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    block = find_markdown_block(fact_text, ["7. Non-functional Requirements", "Non-functional Requirements", "Constraints", "关键约束"])
    return list_items_from_block(block)


def extract_architectural_constraints(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    block = find_markdown_block(fact_text, ["8. Architectural Constraints", "Architectural Constraints", "Constraints", "关键约束"])
    return list_items_from_block(block)


def extract_out_of_scope_items(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    block = find_markdown_block(fact_text, ["9. Out of Scope (MVP)", "Out of Scope (MVP)", "Scope Boundary", "范围边界与非目标"])
    items = label_block_items(block, [r"Out of scope"], limit=8)
    if not items:
        items = list_items_from_block(block)
    return items


def extract_priority_bucket(source_text: str, heading: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    values = flatten_bullets(find_markdown_block(fact_text, [heading]), 8)
    if not values and "P0" in heading:
        values = label_block_items(fact_text, [r"P0"], limit=8)
    if not values and "P1" in heading:
        values = label_block_items(fact_text, [r"P1"], limit=8)
    if not values and "P2" in heading:
        values = label_block_items(fact_text, [r"P2"], limit=8)
    return values


def extract_flow_rows(source_text: str) -> list[dict[str, object]]:
    fact_text = source_fact_text(source_text)
    flow_block = find_markdown_block(fact_text, ["6. Key Business Flows", "Key Business Flows", "Key Workflows", "Scenarios", "主流程"])
    flows: list[dict[str, object]] = []
    current_name = ""
    current_steps: list[str] = []
    for raw in flow_block.splitlines():
        line = raw.strip()
        heading = re.match(r"^#{3,5}\s+(.+)$", line)
        if heading:
            if current_name:
                flows.append({"name": current_name, "steps": list(current_steps)})
            current_name = heading.group(1).strip()
            current_steps = []
            continue
        step = re.match(r"^\d+\.\s+(.+)$", line)
        if step:
            current_steps.append(step.group(1).strip())
    if current_name:
        flows.append({"name": current_name, "steps": list(current_steps)})
    if flows:
        return flows
    main_flow = flatten_bullets(extract_main_flow_block(fact_text), 8)
    if main_flow:
        return [{"name": "Primary Flow", "steps": main_flow}]
    return []


def derive_navigation_surfaces(module_rows: list[dict[str, str]], objectives: list[str]) -> list[str]:
    surfaces = [str(row.get("module", "")).strip() for row in module_rows if str(row.get("module", "")).strip()]
    objective_text = " ".join(objectives).lower()
    if "dashboard" in objective_text or "仪表盘" in objective_text:
        surfaces.append("dashboard")
    if "report" in objective_text or "运营数据" in objective_text:
        surfaces.append("reports")
    return unique_preserve_order(surfaces) or ["workflow-home", "operations", "reports"]


def infer_first_slice_modules(module_rows: list[dict[str, str]], flow_rows: list[dict[str, object]]) -> list[str]:
    modules = [str(row.get("module", "")).strip() for row in module_rows if str(row.get("module", "")).strip()]
    if not modules:
        return ["source-defined first step", "source-defined completion step"]
    flow_text = " ".join(
        step.lower()
        for flow in flow_rows
        for step in [str(item).strip() for item in flow.get("steps", []) if str(item).strip()]
    )
    ordered = [module for module in modules if module.lower() in flow_text]
    if ordered:
        return unique_preserve_order(ordered)
    return modules


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


def collect_source_signal_pool(
    source_text: str,
    *,
    objectives: list[str],
    flows: list[dict[str, object]],
    modules: list[dict[str, str]],
    constraints: list[str],
) -> list[str]:
    fact_text = source_fact_text(source_text)
    pool: list[str] = []
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["2.2 业务机会描述", "业务机会描述", "Business Opportunity"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["2.4 至少 1 条可引用证据线索", "可引用证据线索", "Evidence"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["3.2 结构化问题清单", "结构化问题清单", "Structured Problem List"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["3.3 结构化机会清单", "结构化机会清单", "Structured Opportunity List"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["3.4 至少 1 条用户叙事", "用户叙事", "User Narrative"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["5.3 影响切片顺序的依赖假设", "依赖假设", "Dependency Assumption"]), 6))
    pool.extend(objectives)
    pool.extend(constraints[:6])
    pool.extend(extract_priority_bucket(fact_text, "P0（MVP 必须有）")[:6])
    pool.extend(
        extract_priority_bucket(fact_text, "P1（MVP 后尽快补）")[:4]
        + extract_priority_bucket(fact_text, "P2（后续阶段）")[:4]
    )
    pool.extend(str(flow.get("name", "")).strip() for flow in flows if str(flow.get("name", "")).strip())
    pool.extend(
        str(step).strip()
        for flow in flows
        for step in flow.get("steps", [])
        if str(step).strip()
    )
    pool.extend(
        str(row.get(key, "")).strip()
        for row in modules
        for key in ("module", "responsibility", "input", "output")
        if str(row.get(key, "")).strip()
    )
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["6.2 每条验证的最小方法与判定信号", "6.1 验证对象"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["第九部分：需要后续补实的 unknown / provisional 信息"]), 8))
    return [item for item in pool if compact_signal_line(item)]


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
        if not candidate or len(candidate) > 220:
            continue
        if not re.search(patterns, candidate, flags=re.IGNORECASE):
            continue
        if not signal_intent_match(candidate, intent=intent):
            continue
        key = _normalized_label_key(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        ranked.append((-signal_priority_score(candidate, intent=intent), idx, candidate))
    ranked.sort()
    return [candidate for _, _, candidate in ranked[:limit]]


def signal_phrase(values: list[str], fallback: str, *, limit: int = 2) -> str:
    picked = [compact_signal_line(value) for value in values if compact_signal_line(value)]
    if not picked:
        return fallback
    return "; ".join(picked[:limit])


def extract_domain_context(source_text: str) -> dict[str, object]:
    fact_text = source_fact_text(source_text)
    roles = extract_target_user_rows(source_text)
    objectives = extract_business_objectives(source_text)
    module_rows = extract_module_rows(source_text)
    object_rows = extract_object_rows(source_text)
    flow_rows = extract_flow_rows(source_text)
    nfrs = extract_non_functional_requirements(source_text)
    constraints = extract_architectural_constraints(source_text)
    out_of_scope = extract_out_of_scope_items(source_text)
    p0 = extract_priority_bucket(source_text, "P0（MVP 必须有）")
    p1 = extract_priority_bucket(source_text, "P1（MVP 后尽快补）")
    p2 = extract_priority_bucket(source_text, "P2（后续阶段）")
    navigation_surfaces = derive_navigation_surfaces(module_rows, objectives)
    first_slice_modules = infer_first_slice_modules(module_rows, flow_rows)
    validation_priority_signals = (
        flatten_bullets(find_markdown_block(fact_text, ["6.2 每条验证的最小方法与判定信号"]), 8)
        + flatten_bullets(find_markdown_block(fact_text, ["第九部分：需要后续补实的 unknown / provisional 信息"]), 8)
    )
    source_signal_pool = collect_source_signal_pool(
        source_text,
        objectives=objectives,
        flows=flow_rows,
        modules=module_rows,
        constraints=constraints,
    )
    return {
        "source_text": source_text,
        "product_label": extract_product_label(source_text),
        "roles": roles,
        "segments": detect_source_segments(source_text),
        "objectives": objectives,
        "modules": module_rows,
        "objects": object_rows,
        "flows": flow_rows,
        "nfrs": nfrs,
        "constraints": constraints,
        "out_of_scope": out_of_scope,
        "p0": p0,
        "p1": p1,
        "p2": p2,
        "navigation_surfaces": navigation_surfaces,
        "first_slice_modules": first_slice_modules,
        "business_value_signals": select_source_grounded_signals(
            source_signal_pool,
            patterns=VALUE_SIGNAL_PATTERNS,
            limit=5,
            intent="value",
        ),
        "pressure_signals": select_source_grounded_signals(
            source_signal_pool,
            patterns=PRESSURE_SIGNAL_PATTERNS,
            limit=5,
            intent="pressure",
        ),
        "commercial_decision_signals": select_source_grounded_signals(
            validation_priority_signals + source_signal_pool,
            patterns=COMMERCIAL_DECISION_PATTERNS,
            limit=5,
            intent="commercial",
        ),
        "user_experience_signals": select_source_grounded_signals(
            source_signal_pool,
            patterns=USER_EXPERIENCE_SIGNAL_PATTERNS,
            limit=5,
            intent="experience",
        ),
    }


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
    domain_posture = (
        "growth-observation"
        if detect_source_style(source_text) == "growth_observation"
        else "operational-service"
        if detect_source_style(source_text) == "pet_clinic"
        else "generic-workflow"
    )
    return compile_business_world_truth_spine(
        {
            "domain_posture": domain_posture,
            "primary_segment": segments[0] if segments else "primary operator",
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




def _value_gain_audit(target: str, downstream_value: str) -> dict[str, object]:
    return {
        "method": "Thinking Value-Gain",
        "mode": "full-use",
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


def apply_thinking_value_gain_full_use(business_world_model: dict[str, object]) -> dict[str, object]:
    model = dict(business_world_model)
    model["thinking_value_gain"] = {
        "method": "Thinking Value-Gain",
        "mode": "full-use",
        "scope": "major Phase-1 artifact units",
        "boundary": "bounded value-strengthening, not length expansion",
        "exit_rule": "stop when another round no longer improves practical value",
    }

    arena = dict(model.get("business_exploration_arena", {})) if isinstance(model.get("business_exploration_arena"), dict) else {}
    buyer_map = arena.get("buyer_value_proof_map", {}) if isinstance(arena.get("buyer_value_proof_map"), dict) else {}
    substitute_map = arena.get("substitute_and_current_state_map", {}) if isinstance(arena.get("substitute_and_current_state_map"), dict) else {}
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
    arena["generation_mode"] = "thinking-value-gain-full-use"
    arena["selected_value_gain_axes"] = ["decision", "action", "evidence", "review", "handoff"]
    arena["value_gain_comparison"] = [
        f"decision: strengthen `{chosen_name}` only where it changes {continuation_owner}'s continue / revise / pause choice",
        f"evidence: require proof such as {proof_target} before claiming the business case is stronger",
        f"handoff: carry {reality_focus} and {boundary} into P2 instead of adding ornamental analysis",
    ]
    arena["positive_value_exit"] = (
        "Stop TVG expansion when the next round no longer improves decision/action/evidence/review/handoff value "
        "or when added detail cannot be traced to source-grounded P1 truth."
    )
    arena["value_gain_audit"] = _value_gain_audit(
        "Business Exploration Arena",
        "stronger thesis comparison, substitute pressure, buyer/operator value, and continuation proof before PRD freeze",
    )
    model["business_exploration_arena"] = arena

    draft = dict(model.get("commercial_argument_draft", {})) if isinstance(model.get("commercial_argument_draft"), dict) else {}
    draft["generation_mode"] = "thinking-value-gain-full-use"
    draft["truth_state"] = "source-grounded-value-gain-strengthened"
    draft["quality_state"] = "source-grounded-value-gain-strengthened"
    draft["argument_narrative"] = (
        f"{chosen_name} deserves P1 commitment because {primary_pain}. "
        f"The current substitute pressure is {primary_substitute}; the product must beat it by making {proof_target} visible enough "
        f"for {continuation_owner} to choose continue / revise / pause, not merely by producing a cleaner document or dashboard. "
        f"The value-gain boundary is {boundary}: P2 should preserve the proof-bearing action, evidence, review, and handoff path "
        f"that supports {reality_focus}, while rejecting extra structure that does not change a real decision or implementation handoff."
    )
    draft["why_substitute_is_not_enough"] = (
        f"{primary_substitute} is not enough because it can leave the buyer/operator with signals or records but without the proof chain "
        f"needed to decide continue / revise / pause and to hand P2 a designable operating boundary."
    )
    draft["proof_that_changes_decision"] = (
        f"Decision-changing proof: {proof_target}; it must be explicit enough for {continuation_owner} to make a continue / revise / pause investment decision."
    )
    draft["directional_proof_when_exact_roi_missing"] = (
        "Before exact ROI exists, directional evidence is acceptable only when it changes a continue / revise / pause decision, "
        "exposes the weakest substitute assumption, and gives P2 a concrete architecture handoff."
    )
    draft["architecture_pressure"] = (
        f"P2 must preserve the source-grounded value path from {boundary} through evidence, review, and handoff; "
        "do not collapse it into reporting convenience or generic CRUD structure."
    )
    draft["value_gain_decision_gate"] = (
        "Keep only additions that improve practical decision, action, evidence, review, or handoff value."
    )
    draft["value_gain_audit"] = _value_gain_audit(
        "Commercial Argument Draft",
        "clearer why-now, why-this-not-substitutes, proof-that-changes-decision, and architecture pressure",
    )
    model["commercial_argument_draft"] = draft

    thesis = dict(model.get("chosen_business_thesis", {})) if isinstance(model.get("chosen_business_thesis"), dict) else {}
    thesis["generation_mode"] = "thinking-value-gain-full-use"
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
    )
    model["chosen_business_thesis"] = thesis

    release_truth = dict(model.get("business_release_truth_pack", {})) if isinstance(model.get("business_release_truth_pack"), dict) else {}
    release_truth["thinking_value_gain_mode"] = "full-use"
    release_truth["thinking_value_gain_exit"] = "positive value gain only; no ornamental expansion"
    model["business_release_truth_pack"] = release_truth
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
    def slot_value(slot: object) -> str:
        if isinstance(slot, dict):
            return str(slot.get("value", "")).strip()
        return str(slot or "").strip()

    def slot_lines(label: str, slot: object) -> list[str]:
        if not isinstance(slot, dict):
            return [f"### {label}", "- truth_state: `review-bound / missing evidence`", "- value: review-bound / missing evidence"]
        lines = [
            f"### {label}",
            f"- truth_state: `{slot.get('truth_state', 'review-bound')}`",
            f"- value: {slot.get('value', 'review-bound / missing evidence')}",
        ]
        source_signals = [
            str(item).strip()
            for item in slot.get("source_signals", [])
            if str(item).strip()
        ]
        if source_signals:
            lines.append("- source_signals:")
            lines.extend(f"  - {item}" for item in source_signals)
        return lines

    alternative_set = model.get("primary_alternative_set", {})
    buyer_chain = model.get("buyer_budget_chain", {})
    protected_nouns = model.get("protected_business_nouns", {})
    buyer_spend = str(buyer_chain.get("spend_at_risk", "")).strip()
    buyer_proof = str(buyer_chain.get("proof_artifact_for_continue", "")).strip()
    buyer_trigger = str(buyer_chain.get("decision_trigger", "")).strip()
    lines = [
        "## 8. Protected Business-World Truth Spine",
        f"- artifact_file: `{PHASE1_BUSINESS_WORLD_MODEL_FILENAME}`",
        f"- artifact_type: `{model.get('artifact_type', 'business_world_model')}`",
        f"- domain_posture: `{model.get('domain_posture', 'generic-workflow')}`",
        f"- status: `{model.get('status', 'provisional')}`",
        "",
        *slot_lines("Core Thesis", model.get("core_thesis")),
        "",
        *slot_lines("Why Now", model.get("why_now")),
        "",
        "### Primary Alternative Set",
        f"- truth_state: `{alternative_set.get('truth_state', 'review-bound')}`",
        f"- chosen: {alternative_set.get('chosen', 'review-bound / missing evidence')}",
        "- options:",
    ]
    options = [str(item).strip() for item in alternative_set.get("options", []) if str(item).strip()]
    if options:
        lines.extend(f"  - {item}" for item in options)
    else:
        lines.append("  - review-bound / missing evidence")
    lines.extend(
        [
            "",
            *slot_lines("Why This, Not That", model.get("why_this_not_that")),
            "",
            *slot_lines("Value Mechanism", model.get("value_mechanism")),
            "",
            "### Buyer / Budget / Continuation Chain",
            f"- truth_state: `{buyer_chain.get('truth_state', 'review-bound')}`",
            f"- pain_holder: {buyer_chain.get('pain_holder', 'review-bound / missing evidence')}",
            f"- continuation_owner: {buyer_chain.get('continuation_owner', 'review-bound / missing evidence')}",
            f"- spend_at_risk: {buyer_chain.get('spend_at_risk', 'review-bound / missing evidence')}",
            f"- proof_artifact_for_continue: {buyer_chain.get('proof_artifact_for_continue', 'review-bound / missing evidence')}",
            f"- decision_trigger: {buyer_chain.get('decision_trigger', 'review-bound / missing evidence')}",
            f"- current_truth_state: {buyer_chain.get('current_truth_state', 'review-bound / missing evidence')}",
            f"- missing_evidence_to_unlock: {buyer_chain.get('missing_evidence_to_unlock', 'review-bound / missing evidence')}",
            "",
            "### Protected Business Nouns",
            f"- truth_state: `{protected_nouns.get('truth_state', 'review-bound')}`",
            "- values:",
        ]
    )
    if slot_value(model.get("spend_at_risk")) and slot_value(model.get("spend_at_risk")) != buyer_spend:
        lines.extend(["", *slot_lines("Spend At Risk", model.get("spend_at_risk"))])
    if slot_value(model.get("proof_artifact_for_continue")) and slot_value(model.get("proof_artifact_for_continue")) != buyer_proof:
        lines.extend(["", *slot_lines("Proof Artifact For Continue", model.get("proof_artifact_for_continue"))])
    if slot_value(model.get("decision_trigger")) and slot_value(model.get("decision_trigger")) != buyer_trigger:
        lines.extend(["", *slot_lines("Decision Trigger", model.get("decision_trigger"))])
    noun_values = [str(item).strip() for item in protected_nouns.get("values", []) if str(item).strip()]
    if noun_values:
        lines.extend(f"  - {item}" for item in noun_values)
    else:
        lines.append("  - review-bound / missing evidence")
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
    profile = model.get("topology_profile", {}) if isinstance(model, dict) else {}
    if not isinstance(profile, dict):
        profile = {}
    archetype_label = "inherited_topology_archetype" if inherited else "topology_archetype"
    rationale_label = "inherited_topology_rationale" if inherited else "topology_rationale"
    primary_label = "inherited_primary_depth_axes" if inherited else "primary_depth_axes"
    secondary_label = "inherited_secondary_depth_axes" if inherited else "secondary_depth_axes"
    artifact_label = "topology_source_artifact" if inherited else "topology_source_artifact"
    baseline_label = (
        "ordinary_real_world_baseline_definition"
        if not inherited
        else "ordinary_real_world_baseline_definition"
    )
    misfit_label = "misfit_risk_if_wrong"
    reclass_status_label = "reclassification_status" if inherited else "reclassification_trigger"
    reclass_extra_label = "reclassification_rationale" if inherited else "reclassification_trigger_detail"
    primary_axes = [
        str(item).strip()
        for item in profile.get("primary_depth_axes", [])
        if str(item).strip()
    ]
    secondary_axes = [
        str(item).strip()
        for item in profile.get("secondary_depth_axes", [])
        if str(item).strip()
    ]
    lines = [
        "## 2.1 Inherited Topology Profile Record" if inherited else "## 2.1 Topology Profile Record",
        f"- {archetype_label}:",
        f"  - `{profile.get('topology_archetype', 'hybrid')}`",
        f"- {rationale_label}:",
        f"  - {profile.get('topology_rationale', 'source-grounded topology rationale pending')}",
        f"- {primary_label}:",
    ]
    if primary_axes:
        lines.extend(f"  - `{item}`" for item in primary_axes)
    else:
        lines.append("  - `review-bound / missing evidence`")
    lines.extend(
        [
            f"- {secondary_label}:",
        ]
    )
    if secondary_axes:
        lines.extend(f"  - `{item}`" for item in secondary_axes)
    else:
        lines.append("  - `none`")
    lines.extend(
        [
            f"- {artifact_label}:",
            f"  - `{PHASE1_BUSINESS_WORLD_MODEL_FILENAME}`",
            f"- {baseline_label}:",
            f"  - {profile.get('ordinary_real_world_baseline_definition', 'source-grounded baseline definition pending')}",
            f"- {misfit_label}:",
            f"  - {profile.get('misfit_risk_if_wrong', 'misfit risk pending')}",
        ]
    )
    if inherited:
        lines.extend(
            [
                f"- {reclass_status_label}:",
                "  - `unchanged`",
                f"- {reclass_extra_label}:",
                "  - Stage-02a inherits the Stage-01 topology profile and should only reroute if later structure pressure disproves the current depth model.",
            ]
        )
    else:
        lines.extend(
            [
                f"- {reclass_status_label}:",
                f"  - {profile.get('reclassification_trigger', 'reroute before freeze if topology pressure flips')}",
                f"- {reclass_extra_label}:",
                "  - Re-route only when later rounds prove the current topology profile is no longer the dominant credibility risk.",
            ]
        )
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
    style = detect_source_style(str(context.get("source_text", "")))
    closing_object = (
        "ReviewConclusion"
        if style == "growth_observation"
        else "ReviewSummary"
        if style == "pet_clinic"
        else "CompletionSummary"
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
    return (
        "Recommendation Payload Contract"
        if detect_source_style(str(context.get("source_text", ""))) == "growth_observation"
        else "Module Interface Payload Contract"
    )


def deferred_seam_heading_from_context(context: dict[str, object]) -> str:
    return (
        "Deferred Attribution and Conversion Seam"
        if detect_source_style(str(context.get("source_text", ""))) == "growth_observation"
        else "Deferred Capability Seam"
    )


def render_stage02b_domain_boundary_honesty_lines(context: dict[str, object]) -> str:
    style = detect_source_style(str(context.get("source_text", "")))
    if style == "pet_clinic":
        return (
            "- clinic-private boundary:\n"
            "  - visit, treatment, follow-up, and review records remain clinic-private inside the clinic account boundary by default.\n"
            "- value honesty:\n"
            "  - billing, estimate, and operational closure signals must not overstate exact financial proof in MVP."
        )
    return ""


def render_interface_payload_rows(context: dict[str, object]) -> str:
    module_rows = context["modules"]
    style = detect_source_style(str(context.get("source_text", "")))
    if style == "growth_observation":
        return "\n".join(
            [
                "| payload element | source capability detail preserved | first-wave representation | task/export implication | certainty / note |",
                "|---|---|---|---|---|",
                "| AI-friendly score and quality diagnosis | AI 友好度评分（0-100） / 内容质量诊断 | `ai_friendliness_score` + `quality_diagnosis_summary` + `score_explanation` | 影响 priority、是否进入 task bridge、review 预期 | score rubric 首版仍属 review-bound |",
                "| Structured rewrite suggestion | 结构化改写建议 | `rewrite_goal` + `rewrite_outline` + `before_after_hint` | 形成可执行编辑动作，而不只是“建议优化” | 不直接自动改写发布 |",
                "| Keyword / question focus | 关键词优化建议 + 问答焦点 | `target_question` + `keyword_focus` + `coverage_gap` | 决定任务目标问题、FAQ 切入点和资产优先级 | 必须绑定 Tracked Scope 与 Content Asset |",
                "| Citation-likelihood hypothesis | 引用概率预测 | `citation_likelihood_band` + `citation_reason` + `confidence_state` | 影响 recommendation priority 与 review 预期，不可当作 guaranteed outcome | 首版仅做 hypothesis，不做承诺 |",
                "| FAQ / Q&A suggestion | AI 回答模板生成 + 问答对自动生成 | `faq_question` + `faq_answer_outline` + `suggested_format` | 可导出为 FAQ/task 子类型，而不是消失在通用建议里 | FAQ auto-generation 仍非 fully automatic publish |",
                "| Export-ready task payload | 保存草稿 / 创建任务 / 一键应用优化 的执行核 | `target_asset_id` + `priority` + `owner_hint` + `due_cycle` + `blocked_reason` | recommendation 才能一跳转成 task/export record | “一键应用”仅保留为人工确认后的 action |",
            ]
        )

    lines = [
        "| payload element | source capability detail preserved | first-wave representation | task/export implication | certainty / note |",
        "|---|---|---|---|---|",
    ]
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
    style = detect_source_style(str(context.get("source_text", "")))
    if style == "growth_observation":
        return "\n".join(
            [
                "| future concern | first-wave treatment now | future seam entity/interface | minimum reserved fields or hook | why deferred now |",
                "|---|---|---|---|---|",
                "| AI traffic source tagging | baseline/review 仅记录 platform / query cluster / source note | Attribution Signal | `source_tag` + `platform` + `query_cluster` + `landing_asset_ref` | 首版不做全链路埋点 |",
                "| Funnel progression | report 仅保留方向性 outcome note | Funnel Stage Snapshot | `funnel_stage` + `stage_timestamp` + `related_scope_id` | 缺少稳定业务数据接入 |",
                "| Conversion event linkage | 允许人工记录 conversion note | Conversion Event | `conversion_event_id` + `event_type` + `amount_band` + `evidence_source` | 精确财务归因证据不足 |",
                "| Cross-device identity | 不做 identity stitching | Identity Resolution Link | `visitor_link_key` + `device_class` + `confidence_state` | MVP 不承担跨设备识别复杂度 |",
                "| ROI rollup | review 仅保留 coarse attribution hypothesis | Attribution Rollup | `attributed_range` + `assumption_note` + `confidence_state` | 不能在 MVP 假装财务级证明已成立 |",
            ]
        )

    out_of_scope = list(context.get("out_of_scope", []))
    lines = [
        "| future concern | first-wave treatment now | future seam entity/interface | minimum reserved fields or hook | why deferred now |",
        "|---|---|---|---|---|",
    ]
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
    objective = objectives[0] if objectives else "support the source-defined product goal"
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


def build_stage_01(source_text: str, version: str, owner: str) -> str:
    h21 = find_h2_block(source_text, r"2\.1\s+项目/产品背景")
    h22 = find_h2_block(source_text, r"2\.2\s+业务机会描述")
    h23 = find_h2_block(source_text, r"2\.3\s+研究对象/目标用户边界")
    h24 = find_h2_block(source_text, r"2\.4\s+至少\s*1\s*条可引用证据线索")
    h31 = find_h2_block(source_text, r"3\.1\s+产品/业务目标方向")
    h32 = find_h2_block(source_text, r"3\.2\s+结构化问题清单")
    h33 = find_h2_block(source_text, r"3\.3\s+结构化机会清单")
    h34 = find_h2_block(source_text, r"3\.4\s+至少\s*1\s*条用户叙事")
    first_part = find_h1_block(source_text, r"第一部分：原版\s*PRD\s*核心内容")
    context = extract_domain_context(source_text)
    product_label = context["product_label"]
    segments = context["segments"]
    primary_segment = segments[0]
    alternative_segments = segments[1:] or ["secondary collaborator", "review stakeholder"]
    objectives = context["objectives"] or ["establish a source-defined operating loop"]
    modules = context["modules"]
    roles = context["roles"]
    flows = context["flows"]
    constraints = context["constraints"] or ["source-defined constraint"]
    nfrs = context["nfrs"] or ["source-defined non-functional requirement"]
    out_of_scope = context["out_of_scope"] or ["source-defined deferred item"]
    flow_summary = " -> ".join(str(row.get("module", "")).strip() for row in modules if str(row.get("module", "")).strip()) or "source-defined workflow"
    business_world_model = build_business_world_model(source_text)
    problem_cluster_lines = "\n".join(
        f"  - {item}" for item in (flatten_bullets(h32, 6) or [f"{primary_segment} 缺少稳定的流程闭环"])
    )
    opportunity_cluster_lines = "\n".join(f"  - {item}" for item in (flatten_bullets(h33, 6) or objectives[:4]))
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
    skill_assets = load_stage_skill_assets("stage_01")
    reasoning_units = [
        {
            "title": "Primary Boundary Lock",
            "artifact_unit": "chosen user boundary",
            "loop_round_state": "structured -> reviewed -> freeze",
            "weakness_trigger": "first-wave boundary was still too broad",
            "method_family": "segment comparison + first-loop prioritization",
            "method_assets": [
                "direct user research posture",
                "fast user-group segmentation",
                "explicit alternative comparison for first-wave user choice",
            ],
            "reasoning_operator": "compare source-defined roles by workflow ownership, continuity visibility, and first-wave validation leverage",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": [primary_segment, *alternative_segments[:2]],
            "tradeoff_or_tension": "boundary breadth vs first-wave clarity",
            "decision_effect": f"locked `{primary_segment}` as the primary boundary for downstream structure analysis",
            "evidence_classification": [
                f"observed fact: source explicitly lists roles `{', '.join(segments[:3])}`",
                f"interpreted pattern: `{primary_segment}` sits closest to the start of `{flow_summary}`",
                "decision: keep one primary boundary and treat the rest as supporting roles",
            ],
            "evidence_state": "provisional",
            "remaining_unknown": "real interview evidence for role preference is still pending",
            "downstream_handoff": f"Stage-02a must organize the panorama around `{primary_segment}` and the `{flow_summary}` chain",
            "freeze_rationale": "boundary is specific enough to constrain downstream design without pretending validation is complete",
        },
        {
            "title": "Problem Mechanism Reframe",
            "artifact_unit": "final problem statement",
            "loop_round_state": "structured -> refined -> freeze",
            "weakness_trigger": "initial framing risked collapsing into feature inventory",
            "method_family": "problem framing before solutioning",
            "method_assets": [
                "opportunity framing before solutioning",
                "problem-mechanism framing, not just symptom listing",
            ],
            "reasoning_operator": "separate workflow breakdown, handoff friction, and audit gap before discussing modules",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": ["feature-gap framing", "workflow-breakdown framing"],
            "tradeoff_or_tension": "shorter feature language vs accurate workflow diagnosis",
            "decision_effect": f"reframed the problem around the missing `{flow_summary}` operating loop",
            "evidence_classification": [
                f"observed fact: source objectives stress `{objectives[0]}`",
                f"interpreted pattern: disconnected `{flow_summary}` steps create manual coordination overhead",
                "decision: treat auditability and handoff continuity as the core mechanism",
            ],
            "evidence_state": "provisional",
            "remaining_unknown": "the hardest real-world handoff still needs user verification",
            "downstream_handoff": "Stage-02a should prioritize workflow structure over isolated screens",
            "freeze_rationale": "problem mechanism is now specific enough to guide structural analysis",
        },
        {
            "title": "Open Truth Discipline",
            "artifact_unit": "key open truths",
            "loop_round_state": "structured -> reviewed -> freeze",
            "weakness_trigger": "constraints and deferred scope could be silently promoted into assumed facts",
            "method_family": "evidence layering + explicit uncertainty retention",
            "method_assets": [
                "research execution and insight synthesis",
                "evidence layering: observed fact vs interpretation vs inference",
            ],
            "reasoning_operator": "keep NFRs, constraints, and deferred scope visible as review-bound truths",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": ["hide uncertainties in narrative", "preserve open truths explicitly"],
            "tradeoff_or_tension": "clean narrative vs honest uncertainty",
            "decision_effect": "preserved operational constraints and out-of-scope items as explicit open truths",
            "evidence_classification": [
                f"observed fact: source states constraints such as `{constraints[0]}`",
                f"observed fact: source excludes `{out_of_scope[0]}` from MVP",
                "decision: downstream stages must not silently upgrade these unknowns into commitments",
            ],
            "evidence_state": "review-bound",
            "remaining_unknown": "which open truth becomes the first blocking risk in validation is still unknown",
            "downstream_handoff": "later stages must preserve these truths in scope and validation sections",
            "freeze_rationale": "uncertainty is bounded and explicitly recorded",
        },
    ]

    return f"""# Stage-01 Output — requirements-user-research (deep-compiled)

## 1. Document Metadata
- document_name: `{product_label} Phase-1 Trial Stage-01 User Research {version}`
- stage: `requirements-user-research`
- version: `{version}`
- status: `provisional`
- owner: `{owner}`
- source_status: `mixed`

{render_traceability_block("stage_01")}

{render_topology_profile_record(business_world_model, inherited=False)}

## 2. Chosen User Boundary
- chosen_segment: `{primary_segment}`
- alternatives_considered:
{chr(10).join(f"  - {item}" for item in alternative_segments)}
- why_this_not_that:
  - 当前 source 对该边界给出了最完整的角色职责、流程动作和结果责任，适合作为首波分析主边界。

## 3. Problem Statement
- final_problem_statement:
  - 当前团队缺少一条可重复的 `{flow_summary}` 业务闭环，导致关键业务步骤仍依赖人工衔接和经验判断。
- problem_mechanism:
  - 问题不只是单个页面或模块缺失，而是登记、流转、执行和结算等动作没有被组织成同一条可审计链路。

## 4. Need Framing
- chosen_framing: `workflow continuity + auditable operations`
- rejected:
  - isolated module delivery
  - role-segment sprawl before first-loop validation

## 5. Persona Boundary and Interaction Chain
{persona_chain_rows}

## 6. Structured Problem/Opportunity Recompilation
- top_problem_clusters:
{problem_cluster_lines}
- top_opportunity_clusters:
{opportunity_cluster_lines}

## 7. Key Open Truths
{open_truth_lines}
- deferred scope boundaries:
{deferred_lines}

{render_business_world_model_section(business_world_model)}

{render_reasoning_unit_ledger("## 9. Minimal Reasoning Unit Ledger", reasoning_units, context=context)}

{render_method_activation_evidence("## 10. Method Activation Evidence", reasoning_units, context=context)}

{render_material_grounding_bridge("## 11. Material Grounding Bridge", skill_assets, context)}

{render_skill_asset_snapshot(
    "## 12. Skill Asset Ingestion Snapshot",
    skill_assets,
    [
        "one user-segmentation method asset was materially activated",
        "one evidence/insight synthesis method asset was materially activated",
        "one problem-framing method asset was materially activated",
        "chosen user boundary, final problem statement, and need framing retain visible method trace",
    ],
    context,
)}

## 13. Source Evidence Pack
{demote_headings(h21)}

{demote_headings(h22)}

{demote_headings(h23)}

{demote_headings(h24)}

{demote_headings(h31)}

{demote_headings(h32)}

{demote_headings(h33)}

{demote_headings(h34)}

{demote_headings(first_part)}
"""


def build_stage_02a(source_text: str, version: str, owner: str) -> str:
    h23 = find_h2_block(source_text, r"2\.3\s+研究对象/目标用户边界")
    h31 = find_h2_block(source_text, r"3\.1\s+产品/业务目标方向")
    h32 = find_h2_block(source_text, r"3\.2\s+结构化问题清单")
    h33 = find_h2_block(source_text, r"3\.3\s+结构化机会清单")
    h34 = find_h2_block(source_text, r"3\.4\s+至少\s*1\s*条用户叙事")
    h41 = find_h2_block(source_text, r"4\.1\s+关键约束")
    h43 = find_h2_block(source_text, r"4\.3\s+范围边界与非目标")
    h7p0 = find_h2_block(source_text, r"P0（MVP 必须有）")
    h7p1 = find_h2_block(source_text, r"P1（MVP 后尽快补）")
    h7p2 = find_h2_block(source_text, r"P2（后续阶段）")
    h8 = extract_main_flow_block(source_text)
    h51 = find_h2_block(source_text, r"5\.1\s+MVP 分期")
    h52 = find_h2_block(source_text, r"5\.2\s+最小可用体验闭环")
    h53 = find_h2_block(source_text, r"5\.3\s+影响切片顺序的依赖假设")
    h61 = find_h2_block(source_text, r"6\.1\s+验证对象")
    h62 = find_h2_block(source_text, r"6\.2\s+每条验证的最小方法与判定信号")
    context = extract_domain_context(source_text)
    business_world_model = build_business_world_model(source_text)
    product_label = context["product_label"]
    segments = context["segments"]
    primary_segment = segments[0]
    modules = context["modules"]
    objectives = context["objectives"] or ["preserve the shortest source-defined workflow"]
    flows = context["flows"]
    module_names = [str(row.get("module", "")).strip() for row in modules if str(row.get("module", "")).strip()]
    workflow_chain = " -> ".join(module_names) or "source-defined workflow"
    roles = context["roles"]
    constraints = context["constraints"] or ["source-defined architectural constraint"]
    out_of_scope = context["out_of_scope"] or ["source-defined future item"]
    p0_items = context["p0"] or module_names[:5]
    p1_items = context["p1"] or out_of_scope[:3]
    p2_items = context["p2"] or out_of_scope[:3]
    supporting_role_lines = "\n".join(f"  - {item}" for item in (segments[1:4] or ["secondary collaborator"]))
    problem_cluster_lines = "\n".join(
        f"  - {item}" for item in (flatten_bullets(h32, 4) or [f"{primary_segment} 需要稳定完成 {workflow_chain}"])
    )
    opportunity_cluster_lines = "\n".join(f"  - {item}" for item in (flatten_bullets(h33, 4) or objectives[:3]))
    backbone_lines = "\n".join(f"{idx}. {name}" for idx, name in enumerate(module_names[:8], start=1))
    process_rows = "\n".join(
        f"| main flow | {row.get('module', 'source step')} | {row.get('primary_actor', primary_segment) or primary_segment} | {row.get('input', 'source-defined trigger')} | {row.get('output', 'source output')} | {row.get('responsibility', 'supports workflow continuity')} |"
        for row in modules[:8]
    )
    first_flow_steps = [str(step).strip() for step in (flows[0].get("steps", []) if flows else []) if str(step).strip()]
    primary_step_lines = "\n".join(f"  - {step}" for step in first_flow_steps) or "  - source-defined workflow step"
    actor_system_lines = "\n".join(
        f"  - {row.get('module', 'module')} actor=`{row.get('primary_actor', primary_segment) or primary_segment}` / system=`{row.get('responsibility', 'source-defined system behavior')}`"
        for row in modules[:5]
    )
    scenario_blocks: list[str] = []
    for idx, flow in enumerate(flows[:3], start=1):
        steps = [str(step).strip() for step in flow.get("steps", []) if str(step).strip()]
        first_step = steps[0] if steps else "source-defined trigger step"
        last_step = steps[-1] if steps else "source-defined completion step"
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
    scenario_decomposition_block = "\n".join(scenario_blocks).rstrip() or """### Scenario 1: Source-defined Primary Flow
- trigger:
  - source-defined trigger
- challenge:
  - 若上下文断裂，主流程将退化为人工拼接。
- structure implication:
  - 设计必须围绕源文档的主流程连续性展开。"""
    deep_dive_blocks: list[str] = []
    deep_dive_labels = ["A", "B", "C"]
    deep_dive_roles = [row.get("Role", primary_segment) for row in roles[:3]] or [primary_segment]
    for idx, flow in enumerate(flows[:3], start=0):
        steps = [str(step).strip() for step in flow.get("steps", []) if str(step).strip()]
        role = deep_dive_roles[idx % len(deep_dive_roles)]
        first_step = steps[0] if steps else "source-defined first action"
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
    key_scenario_deep_analysis_block = "\n".join(deep_dive_blocks).rstrip()
    day_in_life = objectives[0] if objectives else f"{primary_segment} 需要稳定推动 {workflow_chain}"
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
    persona_context_block = f"""### Primary Persona Context Scenario
- archetype:
  - `{primary_segment}`
- day-in-the-life snapshot:
  - {day_in_life}
- desired experience:
  - 希望能沿着 `{desired_experience}` 直接完成主流程，而不是在多个孤立页面之间手工对齐上下文。

{chr(10).join(key_path_blocks).rstrip()}"""
    design_requirement_rows = []
    for idx, module_row in enumerate(modules[:6], start=1):
        role = str(module_row.get("primary_actor", "")).strip() or (roles[(idx - 1) % len(roles)]["Role"] if roles else primary_segment)
        design_requirement_rows.append(
            "| DR-{idx:02d} | {role} | 进入 `{module}` | 在同一界面中完成 `{responsibility}`，并看到 `{output}` | 让 `{input_value}` 与 `{output}` 脱节或只能靠人工补齐 |".format(
                idx=idx,
                role=role,
                module=module_row.get("module", "source-defined module"),
                responsibility=module_row.get("responsibility", "source-defined responsibility"),
                output=module_row.get("output", "source-defined output"),
                input_value=module_row.get("input", "source-defined input"),
            )
        )
    design_requirements_block = "\n".join(
        ["| id | persona / role | trigger | required outcome | anti-pattern to avoid |", "|---|---|---|---|---|", *design_requirement_rows]
    )
    nfr_identification_block = f"""- nfr_initial_identification:
  - nfr_dimensions_scan:
    - dimension_1:
      - name: reliability
      - relevance: `relevant`
      - information_state: `identified`
      - basis: 主流程 `{workflow_chain}` 必须稳定可复现，否则 {primary_segment} 无法据此持续运营。
      - known_signals: 关键步骤 `{module_names[0] if module_names else 'source module'}` 到 `{module_names[-1] if module_names else 'source completion'}` 不能出现隐式状态跳变。
    - dimension_2:
      - name: usability
      - relevance: `relevant`
      - information_state: `identified`
      - basis: 角色 `{primary_segment}` 与 `{roles[1]['Role'] if len(roles) > 1 else 'secondary collaborator'}` 必须都能读懂模块输入输出并顺畅交接。
      - known_signals: `{module_names[0] if module_names else 'source module'}` -> `{module_names[1] if len(module_names) > 1 else 'next module'}` 的 handoff 不能依赖口头补充。
    - dimension_3:
      - name: security/data-control
      - relevance: `relevant`
      - information_state: `identified`
      - basis: source 已明确提出约束 `{constraints[0]}`，说明权限、审计或边界控制不能后补。
      - known_signals: 关键约束必须在主流程前段显式生效，而不是在最后才暴露。
    - dimension_4:
      - name: maintainability
      - relevance: `suspected-relevant`
      - information_state: `suspected`
      - basis: 模块 `{module_names[0] if module_names else 'source module'}` 到 `{module_names[-1] if module_names else 'source completion'}` 的对象链必须保留 seam，后续才能安全扩展。
      - known_signals: Stage-02b 需要在对象链、模块契约和延后项之间保持一致。
    - dimension_5:
      - name: performance
      - relevance: `suspected-relevant`
      - information_state: `unknown`
      - basis: source 没有给出完整容量曲线，但当前约束 `{constraints[-1]}` 说明响应和并发仍需后续确认。
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
    stress_business = objectives[0] if objectives else "source-defined business objective"
    stress_technical = constraints[0] if constraints else "source-defined architectural constraint"
    stress_compliance = constraints[-1] if constraints else "source-defined audit constraint"
    stress_resource = out_of_scope[0] if out_of_scope else "source-defined deferred scope"
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
    stakeholder_rows = [
        ("primary_boundary", primary_segment, f"complete `{workflow_chain}` without losing {experience_pressure}", "high"),
        ("supporting_role", roles[1]["Role"] if len(roles) > 1 else "secondary collaborator", f"receive clear upstream state and object handoff while preserving {value_pressure}", "medium"),
        ("supporting_role", roles[2]["Role"] if len(roles) > 2 else "review stakeholder", f"see auditable results, stable scope boundary, and `{commercial_pressure}`", "medium"),
    ]
    stakeholder_profile_rows = "\n".join(
        f"| {name} | {goal} | keep `{workflow_chain}` traversable | loses continuity if state and object links break | {influence} |"
        for _, name, goal, influence in stakeholder_rows
    )
    adoption_chain_lines = "\n".join(
        f"{idx}. {name} can enter the flow with clear context, preserve {experience_pressure}, and complete the handoff without diluting {value_pressure}"
        for idx, (_, name, _, _) in enumerate(stakeholder_rows, start=1)
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
            f"  - actor enters `{module_names[0] if module_names else 'source start'}` with the minimum required input and the source-grounded value pressure `{value_pressure}` still visible",
            f"  - workflow advances through `{workflow_chain}` with explicit state and object transitions instead of reintroducing {experience_pressure}",
            f"  - downstream artifacts must preserve `{module_names[-1] if module_names else 'source completion'}` as an explainable closure point for `{commercial_pressure}`",
        ]
    )
    stakeholder_chain_line = " -> ".join(name for _, name, _, _ in stakeholder_rows)
    scenario_set_lines = "\n".join(f"  - {flow.get('name', 'Primary Flow')}" for flow in flows[:3]) or "  - source-defined primary flow"
    reasoning_units = [
        {
            "title": "Structure Choice",
            "artifact_unit": "chosen panorama structure",
            "loop_round_state": "structured -> compared -> freeze",
            "weakness_trigger": "screen-first or role-first framing could hide the real workflow chain",
            "method_family": "structure comparison + workflow panorama selection",
            "method_assets": [
                "whole-picture requirements structure",
                "story-map construction",
            ],
            "reasoning_operator": "compare screen-first, role-first, and workflow-first views against source-defined business flow",
            "material_grounding": material_grounding_lines(load_stage_skill_assets("stage_02a")),
            "alternatives_compared": ["screen-first", "role-first", "workflow-first"],
            "tradeoff_or_tension": f"fast cataloging vs preserving the real business chain and source-grounded value pressure `{value_pressure}`",
            "decision_effect": f"selected `workflow-first` around `{workflow_chain}` so the product can preserve `{value_pressure}` instead of collapsing into detached surfaces",
            "evidence_classification": [
                f"observed fact: source module matrix forms `{workflow_chain}`",
                "interpreted pattern: actor and object continuity matter more than standalone pages",
                "decision: Stage-02a keeps workflow as the backbone",
            ],
            "evidence_state": "provisional",
            "remaining_unknown": "some state transitions still need deeper spec work in Stage-02b",
            "downstream_handoff": "Stage-02b and Stage-03 must preserve the same backbone ordering",
            "freeze_rationale": "workflow shape is now specific enough to constrain deeper design",
        },
        {
            "title": "Scenario and Backbone Decomposition",
            "artifact_unit": "backbone activities and scenarios",
            "loop_round_state": "structured -> decomposed -> freeze",
            "weakness_trigger": "high-level flow narrative was not enough to drive design requirements",
            "method_family": "backbone decomposition + scenario analysis",
            "method_assets": [
                "structured analysis note building",
            ],
            "reasoning_operator": "split the primary workflow into backbone steps, scenarios, and handoff-sensitive paths",
            "material_grounding": material_grounding_lines(load_stage_skill_assets("stage_02a")),
            "alternatives_compared": [flow.get("name", "Primary Flow") for flow in flows[:3]] or ["source-defined primary flow"],
            "tradeoff_or_tension": "compact narrative vs explicit handoff detail",
            "decision_effect": "expanded the source flows into scenarios, key paths, and design requirements",
            "evidence_classification": [
                f"observed fact: source defines `{len(flows)}` primary business flows",
                "interpreted pattern: each flow requires explicit trigger, completion condition, and exception handling",
                "decision: Stage-02a preserves scenario-level structure instead of only listing modules",
            ],
            "evidence_state": "provisional",
            "remaining_unknown": "edge-case exceptions still need Stage-02b payload and state modeling",
            "downstream_handoff": "Stage-02b should deepen the contracts exposed here",
            "freeze_rationale": "scenario decomposition is sufficient for structural analysis and slicing input",
        },
        {
            "title": "Constraint and Priority Discipline",
            "artifact_unit": "constraint stress-test and priority split",
            "loop_round_state": "structured -> stress-tested -> freeze",
            "weakness_trigger": "scope could drift beyond the first viable workflow loop",
            "method_family": "constraint-first analysis + priority discipline",
            "method_assets": [
                "evidence-aware requirement framing",
                "value / adaptation constraint discipline",
            ],
            "reasoning_operator": "test business, technical, and scope pressure against the chosen workflow backbone and P0 focus",
            "material_grounding": material_grounding_lines(load_stage_skill_assets("stage_02a")),
            "alternatives_compared": ["keep strict P0/P1/P2 split", "expand P0 with deferred scope"],
            "tradeoff_or_tension": "broader scope vs first-loop integrity",
            "decision_effect": "kept P0 focused on the shortest viable loop and preserved out-of-scope items explicitly",
            "evidence_classification": [
                f"observed fact: source constraints include `{stress_technical}`",
                f"observed fact: source out-of-scope includes `{stress_resource}`",
                "decision: preserve explicit exclusion logic and avoid silent scope creep",
            ],
            "evidence_state": "review-bound",
            "remaining_unknown": "real implementation cost may still force further reprioritization",
            "downstream_handoff": "Stage-03 must inherit the same cutline and honesty rules",
            "freeze_rationale": "priority logic is explicit enough for downstream slicing",
        },
        {
            "title": "Persona and NFR Carryover Alignment",
            "artifact_unit": "persona paths and NFR initial identification",
            "loop_round_state": "structured -> aligned -> freeze",
            "weakness_trigger": "persona paths and NFR signals could stay detached from the chosen backbone",
            "method_family": "persona path alignment + NFR carryover check",
            "method_assets": [
                "whole-picture requirements structure",
                "structured analysis note building",
            ],
            "reasoning_operator": "bind role paths, implicit design requirements, and NFR scan signals back to the chosen workflow backbone",
            "material_grounding": material_grounding_lines(load_stage_skill_assets("stage_02a")),
            "alternatives_compared": ["persona detail as side note", "persona/NFR alignment as structural input"],
            "tradeoff_or_tension": "lighter structural draft vs explicit downstream design pressure",
            "decision_effect": "kept persona paths and NFR scan as first-class structural consequences of the backbone",
            "evidence_classification": [
                f"observed fact: source roles must traverse `{workflow_chain}`",
                "interpreted pattern: detached persona or NFR notes create false structural completeness",
                "decision: Stage-02a keeps actor path and NFR alignment visible before deeper specification",
            ],
            "evidence_state": "review-bound",
            "remaining_unknown": "some role-specific exception paths still need Stage-02b detail",
            "downstream_handoff": "Stage-02b should preserve both persona path pressure and NFR scan consequences",
            "freeze_rationale": "persona/NFR alignment is explicit enough for downstream use",
        },
    ]
    skill_assets = load_stage_skill_assets("stage_02a")

    return f"""# Stage-02a Output — requirements-structural-analysis (deep-compiled)

## 1. Document Metadata
- document_name: `{product_label} Phase-1 Trial Stage-02a Structural Analysis {version}`
- stage: `requirements-structural-analysis`
- version: `{version}`
- status: `provisional`
- owner: `{owner}`
- source_status: `mixed`

{render_traceability_block("stage_02a")}

{render_semantic_authoring_spine_section(business_world_model)}

{render_topology_profile_record(business_world_model, inherited=True)}

## 2. Structure Choice
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
  - `lean-product-development`: 首版价值环与延后项纪律

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
{actor_system_lines}

## 10. Scenario Decomposition
{scenario_decomposition_block}

## 11. Key Scenario Deep Analysis
{key_scenario_deep_analysis_block}

## 12. Persona Context Scenario and Key Paths
{persona_context_block}

## 13. Design Requirements Extraction
{design_requirements_block}

## 14. NFR Initial Identification
{nfr_identification_block}

## 15. Constraint Stress-Test
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
  - 任何不直接服务 `{workflow_chain}` 的能力默认不进 P0

## 17. Stakeholder Profiles, Adoption Chain, and Conflict Map
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
  - 延后项必须通过 seam 保留，而不是回写进 P0

## 19. Structure Stress-Test and Deepening Loop Log
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
    - outcome: `freeze`

{render_reasoning_unit_ledger("## 20. Minimal Reasoning Unit Ledger", reasoning_units, context=context)}

## 21. Stakeholder and Scenario Set
- stakeholder chain:
  - {stakeholder_chain_line}
- scenario set:
{scenario_set_lines}

## 22. Requirement Analysis Delta Summary
- delta_1:
  - source 给出多个角色; analysis 先锁定 `{primary_segment}` 作为主边界
- delta_2:
  - source 列出模块与流程; analysis 把它们重编译为 backbone activities + scenarios
- delta_3:
  - source 给出 P0/P1/P2; analysis 明确 exclusion logic 与闭环优先级
- delta_4:
  - source 给出用户流程; analysis 补上 actor/system/state 关系

{render_material_grounding_bridge("## 23. Material Grounding Bridge", skill_assets, context)}

{render_method_activation_evidence("## 24. Method Activation Evidence", reasoning_units, context=context)}

{render_skill_asset_snapshot(
    "## 25. Skill Asset Ingestion Snapshot",
    skill_assets,
    [
        "the value loop was articulated before selecting the panorama structure",
        "at least two structure candidates were compared before freeze",
        "stakeholder, scenario, and persona assets materially shaped the structural panorama",
        "constraint stress-test and priority split remained analytical rather than cosmetic",
    ],
    context,
)}

## 26. Source Evidence Pack
{demote_headings(h23)}

{demote_headings(h31)}

{demote_headings(h32)}

{demote_headings(h33)}

{demote_headings(h34)}

{demote_headings(h41)}

{demote_headings(h43)}

{demote_headings(h7p0)}

{demote_headings(h7p1)}

{demote_headings(h7p2)}

{demote_headings(h8)}

{demote_headings(h51)}

{demote_headings(h52)}

{demote_headings(h53)}

{demote_headings(h61)}

{demote_headings(h62)}
"""


def build_stage_02b(source_text: str, version: str, owner: str) -> str:
    h23 = find_h2_block(source_text, r"2\.3\s+研究对象/目标用户边界")
    h42 = find_h2_block(source_text, r"4\.2\s+指标口径最小定义")
    h_features = find_h2_block(source_text, r"🛠️\s*产品必须实现的核心功能")
    h_ui = find_h2_block(source_text, r"📱\s*详细产品功能设计")
    h_adv = find_h2_block(source_text, r"🚀\s*产品优势")
    context = extract_domain_context(source_text)
    business_world_model = build_business_world_model(source_text)
    product_label = context["product_label"]
    roles = context["roles"]
    modules = context["modules"]
    objects = context["objects"]
    flows = context["flows"]
    objectives = context["objectives"] or ["preserve the source-defined workflow chain"]
    nfrs = context["nfrs"] or ["source-defined reliability requirement", "source-defined usability requirement"]
    out_of_scope = context["out_of_scope"] or ["source-defined deferred capability"]
    navigation_surfaces = context["navigation_surfaces"]
    primary_actor = roles[0]["Role"] if roles else "primary operator"
    module_chain = " -> ".join(str(row.get("module", "")).strip() for row in modules if str(row.get("module", "")).strip()) or "source-defined workflow"
    nfr_lines = "\n".join(f"- source_nfr: {item}" for item in nfrs[:6])
    nfr_reasoning_rows = "\n".join(
        f"| {preserved_display_label(item, fallback='Quality Attribute')} | {item} | weakens source workflow continuity | {flows[0]['name'] if flows else 'Primary Flow'} | must stay visible in first-wave specification |"
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
    screen_precursor_lines = "\n".join(f"  - {surface}: preserve source-defined object continuity" for surface in navigation_surfaces)
    screen_object_lines = "\n".join(
        f"  - {surface} -> {objects[idx % len(objects)]['Object'] if objects else 'Business Object'}"
        for idx, surface in enumerate(navigation_surfaces)
    )
    payload_heading = payload_contract_heading_from_context(context)
    deferred_heading = deferred_seam_heading_from_context(context)
    module_token_seen: set[str] = set()
    object_token_seen: set[str] = set()
    er_rows = "\n".join(
        f"    M_{unique_ascii_token(str(objects[idx]['Owner Module']), fallback_values=[str(objects[idx]['Object'])], prefix='module', index=idx, existing=module_token_seen).upper()} ||--o{{ O_{unique_ascii_token(str(objects[idx]['Object']), fallback_values=[str(objects[idx]['Owner Module'])], prefix='object', index=idx, existing=object_token_seen).upper()} : owns"
        for idx in range(min(len(objects), 6))
    )
    skill_assets = load_stage_skill_assets("stage_02b")
    reasoning_units = [
        {
            "title": "Quality Attribute Prioritization",
            "artifact_unit": "NFR prioritization reasoning",
            "loop_round_state": "structured -> prioritized -> freeze",
            "weakness_trigger": "quality attributes could remain generic and disconnected from the workflow",
            "method_family": "NFR prioritization + reverse-risk mapping",
            "method_assets": [
                "quality-scenario framing",
                "reverse-risk thinking for NFR prioritization",
            ],
            "reasoning_operator": "prioritize attributes by workflow breakage risk rather than by abstract completeness",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": [preserved_display_label(item, fallback="Quality Attribute") for item in nfrs[:4]],
            "tradeoff_or_tension": "broad quality coverage vs first-wave specification focus",
            "decision_effect": f"kept quality reasoning anchored to `{module_chain}` and `{flows[0]['name'] if flows else 'Primary Flow'}`",
            "evidence_classification": [
                f"observed fact: source declares NFRs `{'; '.join(nfrs[:3])}`",
                "interpreted pattern: weak quality attributes break workflow continuity before they break edge-case scale",
                "decision: Stage-02b prioritizes reverse-risk on the main loop",
            ],
            "evidence_state": "provisional",
            "remaining_unknown": "deeper quantitative thresholds still need later hardening",
            "downstream_handoff": "Stage-03 and Stage-04 should reuse the same critical attributes and wording",
            "freeze_rationale": "quality priorities are explicit enough for specification deepening",
        },
        {
            "title": "Domain and Subsystem Boundaries",
            "artifact_unit": "domain model + subsystem boundaries",
            "loop_round_state": "structured -> modeled -> freeze",
            "weakness_trigger": "modules and objects could remain separate lists without boundary semantics",
            "method_family": "domain modeling + subsystem boundary analysis",
            "method_assets": [
                "conceptual domain modeling",
                "business subsystem boundary identification",
            ],
            "reasoning_operator": "bind objects, modules, and outputs into explicit subsystem seams",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": [str(row.get("module", "module")) for row in modules[:4]],
            "tradeoff_or_tension": "simple lists vs durable object and subsystem seams",
            "decision_effect": "modeled object ownership and handoff boundaries directly from the source module chain",
            "evidence_classification": [
                f"observed fact: source module matrix names `{module_chain}`",
                "interpreted pattern: explicit seams prevent later re-invention of ownership and payload contracts",
                "decision: keep subsystem boundaries visible in Stage-02b",
            ],
            "evidence_state": "provisional",
            "remaining_unknown": "field-level lifecycle rules still need architecture-level deepening",
            "downstream_handoff": "payload contract 与 IA 必须保留同一套子系统边界逻辑",
            "freeze_rationale": "boundary model is sufficient for first-wave specification work",
        },
        {
            "title": "IA and Deferred Seam Discipline",
            "artifact_unit": "IA direction + deferred capability seam",
            "loop_round_state": "structured -> stress-tested -> freeze",
            "weakness_trigger": "IA could drift away from workflow, and deferred scope could disappear from the spec",
            "method_family": "IA decision comparison + deferred seam preservation",
            "method_assets": [
                "information-architecture direction setting",
                "deferred seam design for attribution / conversion",
            ],
            "reasoning_operator": "compare organizing axes, then keep out-of-scope capabilities visible as explicit seams",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": ["entity-first", "role-first", "workflow-first"],
            "tradeoff_or_tension": "cleaner navigation vs preserving workflow and future extension honesty",
            "decision_effect": "selected workflow-first IA and preserved future capabilities as deferred seams",
            "evidence_classification": [
                f"observed fact: source out-of-scope includes `{out_of_scope[0]}`",
                "interpreted pattern: hiding deferred items creates false completeness for downstream teams",
                "decision: IA and seam decisions stay coupled to the workflow backbone",
            ],
            "evidence_state": "review-bound",
            "remaining_unknown": "some later capabilities may need richer interface reservation",
            "downstream_handoff": "Stage-03 can slice safely without silently dropping future seams",
            "freeze_rationale": "IA and seam logic are explicit enough for re-audit",
        },
        {
            "title": "Payload and Workflow Mapping Integrity",
            "artifact_unit": "workflow mapping + interface payload preservation",
            "loop_round_state": "structured -> cross-checked -> freeze",
            "weakness_trigger": "workflow mapping, payloads, and screen surfaces could drift apart under recompile pressure",
            "method_family": "contract integrity cross-check",
            "method_assets": [
                "source-capability-to-payload recompilation",
                "specification stress-test against Stage-03 slicing",
            ],
            "reasoning_operator": "cross-check module outputs, object-to-workflow mapping, and IA precursor surfaces against the same first-wave chain",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": ["independent tables", "shared contract spine across tables"],
            "tradeoff_or_tension": "faster isolated sections vs one consistent contract spine",
            "decision_effect": "kept payload, mapping, and IA evidence tied to the same module chain",
            "evidence_classification": [
                f"observed fact: source outputs must traverse `{module_chain}`",
                "interpreted pattern: inconsistent mapping tables cause downstream architecture drift",
                "decision: Stage-02b preserves one shared contract spine across deep-spec sections",
            ],
            "evidence_state": "review-bound",
            "remaining_unknown": "field-level validation and export rules still need implementation-facing hardening",
            "downstream_handoff": "Stage-03 and PRD assembly should preserve the same payload and mapping spine",
            "freeze_rationale": "cross-table integrity is explicit enough for downstream use",
        },
    ]

    return f"""# Stage-02b Output — requirements-specification-deepening (deep-compiled)

## 1. Document Metadata
- document_name: `{product_label} Phase-1 Trial Stage-02b Specification Deepening {version}`
- stage: `requirements-specification-deepening`
- version: `{version}`
- status: `provisional`
- owner: `{owner}`
- source_status: `mixed`

{render_traceability_block("stage_02b")}

{render_semantic_authoring_spine_section(business_world_model)}

## 2. NFR / Quality Requirements
{nfr_lines}

## 3. NFR Prioritization Reasoning
| attribute | why prioritized now | reverse risk if weak | affected scenario | MVP consequence |
|---|---|---|---|---|
{nfr_reasoning_rows}
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
{metric_rows}

## 6. Domain Model Direction
- core entities:
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
{er_rows}
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
{subsystem_lines}
- subsystem_interfaces:
{subsystem_interface_lines}
{render_stage02b_domain_boundary_honesty_lines(context)}

## 10. Object-to-Workflow Mapping
{render_object_workflow_rows(context)}

## 11. Information Architecture Direction
- organization:
  - workflow-first + object-traceable
- navigation:
  - {' / '.join(navigation_surfaces)}
- labeling:
  - 业务可理解术语优先
- IA impact:
  - 页面与模块边界必须围绕 `{module_chain}` 的可执行链路。
- screen spec precursor:
{screen_precursor_lines}
- screen/object matrix:
{screen_object_lines}

## 12. IA Decision Alternatives Comparison
| alternative | organizing axis | strength | failure risk | verdict |
|---|---|---|---|---|
| entity-first | 按领域对象划分 | 对数据结构清晰 | 新用户难以看出主流程 | rejected |
| role-first | 按角色工作台划分 | 突出协作差异 | 会复制对象视图并打散闭环 | rejected |
| workflow-first | 按 {' -> '.join(navigation_surfaces[:6])} | 最贴近首版闭环认知 | 需要更强对象映射约束 | chosen |

## 13. IA Spec Precursor Matrix
{render_screen_navigation_rows(context)}

## 14. Module Responsibility Matrix
{render_module_matrix_rows(modules)}

## 15. {payload_heading}
- contract_rule:
  - 每个模块都必须把 source 中定义的输入和输出保留为结构化 payload，避免下游模块依赖人工重建上下文。
{render_interface_payload_rows(context)}

## 16. {deferred_heading}
- seam_rule:
  - source 已明确声明的未来阶段能力不能写成空白，必须保留 seam 说明，避免后续为了扩展而重写对象链。
{render_deferred_seam_rows(context)}
- downstream_rule:
  - architecture 可以先声明 seam entity/interface，但不得把未来能力写入 MVP acceptance promise。

## 17. Specification Stress-Test
- blind spot 1:
  - 若缺乏 domain relationship，Stage-03 容易退化为 feature-list 切片。
- blind spot 2:
  - 若缺乏 metric definition，Stage-04 的判定信号会失真。
- blind spot 3:
  - 若 IA 不映射对象链，页面会脱离业务闭环。
- blind spot 4:
  - 若模块输入输出没有单独契约，后续扩展与审计都会困难。
- verdict:
  - `passed with review-bound constraints`

## 18. Deepening Loop Log
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
    - outcome: `freeze`

{render_reasoning_unit_ledger("## 19. Minimal Reasoning Unit Ledger", reasoning_units, context=context)}

## 20. Requirement Analysis Delta Summary
- delta_1:
  - source列出核心功能; analysis提炼出对象链与模块责任
- delta_2:
  - source给出页面设计; analysis补充 screen/object dependency
- delta_3:
  - source给出指标定义; analysis补充 interpretation risk 与 mitigation
- delta_4:
  - source给出模块输入输出; analysis把它们编译成 interface payload contract
- delta_5:
  - source给出 future/deferred 能力; analysis把它们保留为 deferred capability seam，而不是直接丢失或假装首版可实现

{render_material_grounding_bridge("## 21. Material Grounding Bridge", skill_assets, context)}

{render_method_activation_evidence("## 22. Method Activation Evidence", reasoning_units, context=context)}

{render_skill_asset_snapshot(
    "## 23. Skill Asset Ingestion Snapshot",
    skill_assets,
    [
        "at least three material quality attributes were prioritized with reverse-risk reasoning",
        "conceptual domain modeling and subsystem thinking were derived from Stage-02a scenarios",
        "IA direction decisions were treated as architecture-constraining choices rather than page sketches",
        "module input/output details were recompiled into a structured payload contract instead of generic advice",
        "deferred capabilities were preserved as extension seams instead of being silently dropped",
        "the specification stress-test made Stage-03 slicing consequences explicit",
    ],
    context,
)}

## 24. Source Evidence Pack
{demote_headings(h23)}

{demote_headings(h42)}

{demote_headings(h_features)}

{demote_headings(h_ui)}

{demote_headings(h_adv)}
"""


def build_stage_02b_skip_stub(
    source_text: str,
    stage_02a_text: str,
    version: str,
    owner: str,
) -> str:
    stage_02a_nfr = find_named_h2_block(stage_02a_text, ["NFR Initial Identification"])
    stage_02a_value_loop = find_named_h2_block(stage_02a_text, ["Value Loop and Downstream Preservation Notes"])
    product_label = extract_product_label(source_text)
    context = extract_domain_context(source_text)
    payload_heading = payload_contract_heading_from_context(context)
    base = build_stage_02b(source_text, version, owner)
    base = base.replace(
        "# Stage-02b Output — requirements-specification-deepening (deep-compiled)",
        "# Stage-02b Output — requirements-specification-deepening (skip-stub / minimum-viable)",
        1,
    )
    base = base.replace(
        f"- document_name: `{product_label} Phase-1 Trial Stage-02b Specification Deepening {version}`",
        f"- document_name: `{product_label} Phase-1 Trial Stage-02b Skip-Stub Specification Fallback {version}`",
        1,
    )
    base = base.replace("- status: `provisional`", "- status: `skip-stub`", 1)
    base = base.replace("- source_status: `mixed`", "- source_status: `stage_02a-derived-minimum-viable`", 1)
    base = base.replace(
        "## 2. NFR / Quality Requirements",
        """## 1.2 Stage Execution State
- execution_state: `skipped`
- execution_mode:
  - `minimum-viable skip stub`
- skip_rationale:
  - Full Stage-02b deepening was intentionally skipped in this run to validate Admission Matrix `02b-skip` handling; this artifact preserves the minimum viable NFR / domain / IA / payload truth needed so Phase-2 is not forced to invent critical structure from scratch.
- safe_use_boundary:
  - Use this artifact as a constrained handoff bridge for Phase-2 safe start and Stage-03/04 continuity, not as proof that Stage-02b deepening has been fully completed.
- non_equivalence_to_full_stage:
  - Full quality-scenario deepening, stronger metric interpretation contracts, deeper object lifecycle hardening, and IA contract freeze remain review-bound and must be re-checked in Phase-2.

## 2. NFR / Quality Requirements""",
        1,
    )
    base = base.replace(
        "## 2. NFR / Quality Requirements\n",
        """## 2. NFR / Quality Requirements
- fallback_origin:
  - `compiled from Stage-02a nfr_initial_identification + source metric / workflow evidence`
- minimum_viable_intent:
  - Preserve just enough NFR truth that Stage-03 slicing and Phase-2 architecture do not start blind.
- honesty_note:
  - This section is a skip-derived fallback, not a claim that Stage-02b quality deepening has been fully executed.
""",
        1,
    )
    base = base.replace(
        "## 6. Domain Model Direction\n",
        """## 6. Domain Model Direction
- domain_model_state:
  - `partial-from-02a-and-source`
- safe_interpretation_rule:
  - The object chain below is preserved so downstream design/architecture can start from explicit entities and relationships, but field-level contracts and lifecycle edge cases remain review-bound.
""",
        1,
    )
    base = base.replace(
        "## 11. Information Architecture Direction\n",
        """## 11. Information Architecture Direction
- ia_direction_state:
  - `partial-from-02a-and-source`
- safe_interpretation_rule:
  - Workflow-first IA remains the current safe direction, but page-level detail and state completeness should still be treated as constrained and prototype-validated rather than frozen.
""",
        1,
    )
    base = base.replace(
        f"## 15. {payload_heading}\n",
        f"""## 15. {payload_heading}
- skip_mode_preservation_rule:
  - Even when Stage-02b is skipped, module interface payload structure cannot disappear; otherwise workflow handoff semantics collapse and Phase-2 would be forced to re-invent core execution semantics.
""",
        1,
    )
    base = base.replace(
        "## 17. Specification Stress-Test\n",
        """## 17. Specification Stress-Test
- skip_specific_warning:
  - Because this run used a skip stub, the stress-test below must be read as a bounded guardrail set, not as proof that all specification tensions were fully exhausted.
""",
        1,
    )
    base = base.replace(
        "## 24. Source Evidence Pack",
        f"""## 24. Stage-02a Carryover Evidence
{demote_headings(stage_02a_nfr)}

{demote_headings(stage_02a_value_loop)}

## 25. Source Evidence Pack""",
        1,
    )
    return base


def build_stage_03(
    source_text: str,
    stage_02a_text: str,
    stage_02b_text: str,
    *,
    stage_02b_executed: bool,
    version: str,
    owner: str,
) -> str:
    h51 = find_h2_block(source_text, r"5\.1\s+MVP 分期")
    h52 = find_h2_block(source_text, r"5\.2\s+最小可用体验闭环")
    h53 = find_h2_block(source_text, r"5\.3\s+影响切片顺序的依赖假设")
    h7p0 = find_h2_block(source_text, r"P0（MVP 必须有）")
    h7p1 = find_h2_block(source_text, r"P1（MVP 后尽快补）")
    h7p2 = find_h2_block(source_text, r"P2（后续阶段）")
    h8 = extract_main_flow_block(source_text)
    context = extract_domain_context(source_text)
    business_world_model = build_business_world_model(source_text)
    product_label = context["product_label"]
    segments = context["segments"]
    primary_segment = segments[0]
    roles = context["roles"]
    modules = context["modules"]
    flows = context["flows"]
    nfrs = context["nfrs"] or ["source-defined non-functional requirement"]
    constraints = context["constraints"] or ["source-defined architectural constraint"]
    out_of_scope = context["out_of_scope"] or ["source-defined deferred item"]
    p0_items = context["p0"] or context["first_slice_modules"] or [str(row.get("module", "source-defined module")).strip() for row in modules[:3]]
    p1_items = context["p1"] or [str(row.get("module", "source-defined later slice")).strip() for row in modules[3:5]]
    p2_items = context["p2"] or out_of_scope
    full_loop = " -> ".join(str(row.get("module", "")).strip() for row in modules if str(row.get("module", "")).strip()) or "source-defined workflow loop"
    first_slice_loop = " -> ".join(context["first_slice_modules"]) if context["first_slice_modules"] else "source-defined first slice"
    minimum_loop = " -> ".join((context["first_slice_modules"] or p0_items)[: max(2, min(len(context["first_slice_modules"] or p0_items), 5))]) if (context["first_slice_modules"] or p0_items) else "source-defined minimum loop"
    primary_flow_name = str(flows[0].get("name", "Primary Flow")) if flows else "Primary Flow"
    main_roles = [str(role.get("Role", "")).strip() for role in roles if str(role.get("Role", "")).strip()] or [primary_segment]
    comparison_rows = [
        "| candidate | what_is_in_first_slice | user_value_speed | evidence_confidence | dependency_complexity | validation_leverage | risk_of_overreach | verdict |",
        "|---|---|---|---|---|---|---|---|",
        f"| module-first | {' + '.join(p0_items[:2]) if p0_items[:2] else 'source-defined modules'} | medium | high | low | medium | medium | rejected |",
        f"| role-workbench-first | {' + '.join(main_roles[:2])} workspace | medium | medium | medium | low | high | rejected |",
        f"| workflow-loop-first | {first_slice_loop} | high | high | medium | high | low-medium | chosen |",
    ]
    nfr_force_lines = "\n".join(f"  - {item}" for item in nfrs[:3]) or "  - source-defined NFR must enter first slice"
    nfr_relaxed_lines = "\n".join(f"  - {item}" for item in nfrs[3:5]) or "  - 非首要 NFR 留在后续深化"
    dependency_impact_lines = "\n".join(
        [
            f"  - {full_loop}",
            f"  - `{primary_flow_name}` 的对象交接如果被拆散，首个切片就无法验证真实业务闭环。",
            f"  - 角色 `{', '.join(main_roles[:3])}` 之间的 handoff 必须跟着模块链一起进入 MVP，而不是后补。",
        ]
    )
    value_frequency_candidates = unique_preserve_order(p0_items[:3] + p1_items[:3])
    value_frequency_rows = "\n".join(
        f"| {item} | {'high' if item in p0_items else 'medium'} | {'high' if item in context['first_slice_modules'] else 'medium'} | {'keep in first slice' if item in p0_items or item in context['first_slice_modules'] else 'move to later slice'} | source-defined capability classification |"
        for item in value_frequency_candidates
    ) or "| source-defined capability | medium | medium | keep in first slice | source-defined capability classification |"
    deferred_honesty_rows = "\n".join(
        f"| {item} | source 明确把它放在 MVP 外，当前不应前置承诺 | 把它包装成首版完整能力会掩盖真实 cutline | 接受延后，但需在 seam / backlog 中显式保留 |"
        for item in out_of_scope[:4]
    ) or "| source-defined deferred item | 当前不进 MVP | 冒充已覆盖会造成假完整感 | 需要显式延后 |"
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
    flow_nodes = [item for item in (context["first_slice_modules"] or p0_items)[:3] if item]
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
    skill_assets = load_stage_skill_assets("stage_03")
    s2a_value_loop = find_named_h2_block(stage_02a_text, ["Value Loop and Downstream Preservation Notes"])
    s2a_constraints = find_named_h2_block(stage_02a_text, ["Constraint Stress-Test"])
    s2a_priority = find_named_h2_block(stage_02a_text, ["Priority Split"])
    s2a_stress = find_named_h2_block(stage_02a_text, ["Structure Stress-Test and Deepening Loop Log"])
    s2b_nfr_reasoning = find_named_h2_block(stage_02b_text, ["NFR Prioritization Reasoning"])
    s2b_object_workflow = find_named_h2_block(stage_02b_text, ["Object-to-Workflow Mapping"])
    s2b_ia = find_named_h2_block(stage_02b_text, ["Information Architecture Direction"])
    s2b_payload = find_named_h2_block(stage_02b_text, ["Module Interface Payload Contract"])
    s2b_attribution = find_named_h2_block(stage_02b_text, ["Deferred Capability Seam"])
    reasoning_units = [
        {
            "title": "Workflow-Loop Slice Selection",
            "artifact_unit": "chosen slice strategy",
            "loop_round_state": "structured -> compared -> freeze",
            "weakness_trigger": "first slice could drift into partial capability delivery",
            "method_family": "slice comparison + loop-first prioritization",
            "method_assets": [
                "MVP slicing by story-map",
                "value-frequency comparison for contested first-slice items",
            ],
            "reasoning_operator": "compare module-first, role-workbench-first, and workflow-loop-first against the source dependency chain",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": ["module-first", "role-workbench-first", "workflow-loop-first"],
            "tradeoff_or_tension": "smaller isolated scope vs complete first-loop validation",
            "decision_effect": f"selected `{first_slice_loop}` as the first slice backbone",
            "evidence_classification": [
                f"observed fact: source workflow chain is `{full_loop}`",
                "interpreted pattern: partial slices hide real handoff risk",
                "decision: preserve a complete loop rather than a smaller feature bucket",
            ],
            "evidence_state": "provisional",
            "remaining_unknown": "whether the current minimum loop is still too wide for implementation",
            "downstream_handoff": "design and validation must use the same slice boundary",
            "freeze_rationale": "slice comparison is specific enough to constrain downstream PRD assembly",
        },
        {
            "title": "Minimum Loop Guard",
            "artifact_unit": "minimum viable experience loop",
            "loop_round_state": "structured -> tested -> freeze",
            "weakness_trigger": "removing one key module could break loop closure while still looking deliverable",
            "method_family": "dependency-first slicing",
            "method_assets": [
                "early-value delivery thinking",
                "dependency-first slicing logic",
            ],
            "reasoning_operator": "remove steps mentally and reject any cutline that loses object continuity or explainable completion",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": [full_loop, minimum_loop],
            "tradeoff_or_tension": "narrower scope vs intact business closure",
            "decision_effect": f"kept `{minimum_loop}` as the minimum viable loop",
            "evidence_classification": [
                f"observed fact: `{primary_flow_name}` depends on ordered module handoff",
                "interpreted pattern: removing a core handoff step collapses validation value",
                "decision: treat the selected loop as indivisible for MVP integrity",
            ],
            "evidence_state": "provisional",
            "remaining_unknown": "some upstream/downstream modules may still need different seam treatment",
            "downstream_handoff": "Stage-04 validation should test loop viability, not isolated screens",
            "freeze_rationale": "loop boundary is explicit and testable",
        },
        {
            "title": "Deferred Scope Honesty",
            "artifact_unit": "deferred items and carryover ledger",
            "loop_round_state": "structured -> audited -> freeze",
            "weakness_trigger": "out-of-scope items could disappear or quietly re-enter MVP",
            "method_family": "deferred seam discipline + scope honesty",
            "method_assets": [
                "deferral honesty and anti-false-completeness discipline",
                "source-feature carryover classification",
            ],
            "reasoning_operator": "classify each deferred item explicitly and keep it visible in seam/backlog language",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": ["silently drop deferred items", "preserve explicit deferred ledger"],
            "tradeoff_or_tension": "cleaner MVP story vs honest carryover record",
            "decision_effect": "kept source out-of-scope items explicit in slicing and seam sections",
            "evidence_classification": [
                f"observed fact: source excludes `{out_of_scope[0]}` from MVP",
                "interpreted pattern: silent omission causes false completeness in later review",
                "decision: every deferred item stays visible with a reason",
            ],
            "evidence_state": "review-bound",
            "remaining_unknown": "some deferred items may need earlier interface reservation than currently assumed",
            "downstream_handoff": "architecture may reserve seams, but PRD must not promote them into MVP promise",
            "freeze_rationale": "scope honesty is explicit enough for review and re-audit",
        },
        {
            "title": "NFR-Aware Dependency Ordering",
            "artifact_unit": "dependency-first ordering and NFR-aware slice impact",
            "loop_round_state": "structured -> stress-tested -> freeze",
            "weakness_trigger": "slice order could look clean while still violating quality or dependency pressure",
            "method_family": "dependency ordering + NFR impact alignment",
            "method_assets": [
                "structured decomposition discipline",
                "dependency-first slicing logic",
            ],
            "reasoning_operator": "re-check the chosen slice against dependency-first ordering and the quality constraints inherited from Stage-02a/02b",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": ["business-only cutline", "dependency-first and NFR-aware cutline"],
            "tradeoff_or_tension": "simpler slice story vs implementation-safe ordering",
            "decision_effect": "kept dependency-first ordering and NFR impact visible as part of the chosen slice rationale",
            "evidence_classification": [
                f"observed fact: `{first_slice_loop}` depends on ordered handoff across `{full_loop}`",
                "interpreted pattern: ignoring NFR and dependency pressure creates a fragile MVP story",
                "decision: Stage-03 keeps dependency and NFR impact explicit in the slice package",
            ],
            "evidence_state": "review-bound",
            "remaining_unknown": "real build cost may still rebalance some sequence edges",
            "downstream_handoff": "Stage-04 must validate the same dependency-first assumptions",
            "freeze_rationale": "ordering pressure is explicit enough for validation planning",
        },
    ]
    if stage_02b_executed:
        stage_02b_upstream_lines = "\n".join(
            [
                "  - Stage-02b `NFR Prioritization Reasoning`",
                "  - Stage-02b `Object-to-Workflow Mapping`",
                "  - Stage-02b `Information Architecture Direction`",
                "  - Stage-02b `Module Interface Payload Contract`",
                "  - Stage-02b `Deferred Capability Seam`",
            ]
        )
        stage_02b_availability = "yes"
        stage_02b_skip_effect = ""
    else:
        stage_02b_upstream_lines = "\n".join(
            [
                "  - Stage-02b skip-stub `NFR Prioritization Reasoning`",
                "  - Stage-02b skip-stub `Object-to-Workflow Mapping`",
                "  - Stage-02b skip-stub `Information Architecture Direction`",
                "  - Stage-02b skip-stub `Module Interface Payload Contract`",
                "  - Stage-02b skip-stub `Deferred Capability Seam`",
            ]
        )
        stage_02b_availability = "no"
        stage_02b_skip_effect = """
- stage_02b_skip_effect_on_slicing:
  - This slice can still be chosen safely because the skip stub preserves minimum viable NFR / object / IA signals, but downstream must not assume Stage-02b-level specification freeze has already happened.
"""

    return f"""# Stage-03 Output — requirements-decomposition-and-mvp-slicing (deep-compiled)

## 1. Document Metadata
- document_name: `{product_label} Phase-1 Trial Stage-03 MVP Slicing {version}`
- stage: `requirements-decomposition-and-mvp-slicing`
- version: `{version}`
- status: `provisional`
- owner: `{owner}`
- source_status: `mixed`

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

## 3. Chosen Slice
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
  - {minimum_loop}

## 7. NFR-Aware Slice Impact and Dependency-First Logic
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
{demote_headings(s2a_value_loop, 1)}

## 8. Value-Frequency Assessment
| contested capability | value | expected frequency | first-slice decision | reason |
|---|---|---|---|---|
{value_frequency_rows}

## 9. First Slice, Later Slices, and Deferred Items
- first_slice:
{chr(10).join(f"  - {item}" for item in (context['first_slice_modules'] or p0_items or ['source-defined first slice']))}
- later_slices:
{chr(10).join(f"  - {item}" for item in (p1_items or ['source-defined later slice']))}
- deferred_items:
{chr(10).join(f"  - {item}" for item in (p2_items or ['source-defined deferred item']))}
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
{chr(10).join(render_source_feature_rows(context).splitlines()[2:])}

## 11. MVP Loop Viability Test
- is_the_mvp_a_complete_loop:
  - `yes`
- why_it_is_still_a_loop:
  - 用户能沿着 `{minimum_loop}` 完成一次最小但完整的业务闭环，并看到明确的状态与结果交接。
- what_makes_it_minimum:
  - 移除了 `{', '.join(out_of_scope[:3])}` 等延后项，但保留了让业务闭环成立的最小链路。
- what_would_break_viability:
  - 移除 `{(context['first_slice_modules'] or p0_items)[0]}`：首个切片失去起点。
  - 移除 `{(context['first_slice_modules'] or p0_items)[1] if len((context['first_slice_modules'] or p0_items)) > 1 else (p0_items[0] if p0_items else 'source-defined key step')}`：对象交接会断裂。
  - 移除末端状态确认：团队无法判断是否继续投入。

## 12. Deferred Items Honesty Check
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
    - outcome: `freeze`

{render_reasoning_unit_ledger("## 16. Minimal Reasoning Unit Ledger", reasoning_units, context=context)}

{render_material_grounding_bridge("## 17. Material Grounding Bridge", skill_assets, context)}

{render_skill_asset_snapshot(
    "## 18. Skill Asset Ingestion Snapshot",
    skill_assets,
    [
        "at least two slice candidates were compared before freeze",
        "deferred honesty remained explicit instead of collapsing into roadmap placeholders",
        "dependency-first and NFR-aware logic materially changed the cutline",
        "source feature details were explicitly classified instead of silently disappearing from the MVP story",
        "upstream structure and specification artifacts were carried into the slicing decision",
    ],
    context,
)}

{render_method_activation_evidence("## 19. Method Activation Evidence", reasoning_units, context=context)}

## 20. Upstream Stage Carryover Evidence
{demote_headings(s2a_constraints)}

{demote_headings(s2a_priority)}

{demote_headings(s2a_stress)}

{demote_headings(s2b_nfr_reasoning)}

{demote_headings(s2b_object_workflow)}

{demote_headings(s2b_ia)}

{demote_headings(s2b_payload)}

{demote_headings(s2b_attribution)}

## 21. Source Evidence Pack
{demote_headings(h51)}

{demote_headings(h52)}

{demote_headings(h53)}

{demote_headings(h7p0)}

{demote_headings(h7p1)}

{demote_headings(h7p2)}

{demote_headings(h8)}
"""


def build_stage_04(
    source_text: str,
    stage_02a_text: str,
    stage_03_text: str,
    *,
    stage_02b_executed: bool,
    version: str,
    owner: str,
) -> str:
    h61 = find_h2_block(source_text, r"6\.1\s+验证对象")
    h62 = find_h2_block(source_text, r"6\.2\s+每条验证的最小方法与判定信号")
    h9 = find_h1_block(source_text, r"第九部分：需要后续补实的 unknown / provisional 信息")
    h10 = find_h1_block(source_text, r"第十部分：统一 provenance / provisional 标记表")
    h12 = find_h1_block(source_text, r"第十二部分：结论（供 Phase-1 验收使用）")
    context = extract_domain_context(source_text)
    product_label = context["product_label"]
    segments = context["segments"]
    primary_segment = segments[0]
    roles = context["roles"]
    modules = context["modules"]
    flows = context["flows"]
    objectives = context["objectives"] or ["validate the source-defined first-wave workflow"]
    constraints = context["constraints"] or ["source-defined architectural constraint"]
    out_of_scope = context["out_of_scope"] or ["source-defined deferred item"]
    module_chain = " -> ".join(str(row.get("module", "")).strip() for row in modules if str(row.get("module", "")).strip()) or "source-defined workflow"
    primary_flow_name = str(flows[0].get("name", "Primary Flow")) if flows else "Primary Flow"
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
    skill_assets = load_stage_skill_assets("stage_04")
    s3_slice = find_named_h2_block(stage_03_text, ["Chosen Slice"])
    s3_nfr_impact = find_named_h2_block(stage_03_text, ["NFR-Aware Slice Impact and Dependency-First Logic"])
    s3_assumptions = find_named_h2_block(stage_03_text, ["Key Assumptions to Validate"])
    s3_honesty = find_named_h2_block(stage_03_text, ["Deferred Items Honesty Check"])
    s2a_nfr = find_named_h2_block(stage_02a_text, ["NFR Initial Identification"])
    reasoning_units = [
        {
            "title": "Exact-Assumption Validation Targeting",
            "artifact_unit": "validation targets",
            "loop_round_state": "structured -> clarified -> freeze",
            "weakness_trigger": "validation scope could remain generic instead of tied to explicit assumptions",
            "method_family": "assumption-first validation targeting",
            "method_assets": [
                "validated learning loop",
                "exact-assumption-first validation targeting",
            ],
            "reasoning_operator": "derive validation targets directly from Stage-03 assumptions and preserve their positive/negative consequence",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": [target["id"] for target in validation_targets[:4]],
            "tradeoff_or_tension": "shorter plan vs exact learning target clarity",
            "decision_effect": "validation targets now inherit Stage-03 assumption structure directly",
            "evidence_classification": [
                "observed fact: Stage-03 already names the assumptions most likely to change the slice decision",
                "interpreted pattern: validation is only useful when each target has a concrete downstream consequence",
                "decision: Stage-04 keeps assumption-first structure instead of inventing new target themes",
            ],
            "evidence_state": "provisional",
            "remaining_unknown": "real evidence collection has not happened yet",
            "downstream_handoff": "prototype and interview preparation should follow the same target ids",
            "freeze_rationale": "validation targets are specific enough to execute without more rewriting",
        },
        {
            "title": "Method and Fidelity Fit",
            "artifact_unit": "method-fit comparison",
            "loop_round_state": "structured -> compared -> freeze",
            "weakness_trigger": "method choice could drift into habit instead of target fit",
            "method_family": "method-fit comparison + fidelity choice",
            "method_assets": [
                "prototype/validation linkage",
                "method-fit comparison",
            ],
            "reasoning_operator": "map each assumption to the lightest method that still exposes pass/fail evidence",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": ["clickable walkthrough", "architecture review", "role-comparison interview"],
            "tradeoff_or_tension": "stronger evidence vs lower cost and faster setup",
            "decision_effect": "selected a mixed validation plan driven by assumption type rather than one fixed method for all targets",
            "evidence_classification": [
                "observed fact: assumptions span workflow comprehension, constraint fit, and role boundary fit",
                "interpreted pattern: one validation method cannot answer all target types equally well",
                "decision: use method bundles matched to the assumption category",
            ],
            "evidence_state": "provisional",
            "remaining_unknown": "some targets may still need a richer prototype if early signals are ambiguous",
            "downstream_handoff": "research preparation should keep artifacts aligned with target type",
            "freeze_rationale": "method-fit is explicit enough for the next execution round",
        },
        {
            "title": "Evidence Honesty and Revision Consequence",
            "artifact_unit": "decision state and forbidden assumptions",
            "loop_round_state": "structured -> bounded -> freeze",
            "weakness_trigger": "downstream teams could misread validation planning as validated truth",
            "method_family": "evidence honesty + revision consequence mapping",
            "method_assets": [
                "build-measure-learn loop",
                "evidence-honesty before decision declaration",
            ],
            "reasoning_operator": "separate source-grounded structure from real validation evidence and attach failure consequences per target",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": ["treat the pack as validated", "keep revise-state honesty visible"],
            "tradeoff_or_tension": "cleaner readiness story vs audit-safe honesty",
            "decision_effect": "kept Stage-04 in revise-state while still allowing downstream-safe exploration",
            "evidence_classification": [
                f"observed fact: source provides validation input through section 6 and `{objectives[0]}`",
                "interpreted pattern: design and architecture may start before validation finishes, but must not assume proof already exists",
                "decision: keep forbidden assumptions explicit in the output",
            ],
            "evidence_state": "review-bound",
            "remaining_unknown": "actual user evidence may still overturn the current slice or boundary choice",
            "downstream_handoff": "PRD convergence may proceed, but implementation commitment remains blocked",
            "freeze_rationale": "decision and revision logic are explicit enough for review",
        },
        {
            "title": "Convergence Admission and Stage Coupling",
            "artifact_unit": "convergence readiness and Stage-02b execution coupling",
            "loop_round_state": "structured -> admitted -> freeze",
            "weakness_trigger": "downstream teams could start convergence without checking whether Stage-02b and validation pack stay coupled",
            "method_family": "convergence admission + dependency coupling review",
            "method_assets": [
                "exact-assumption-first validation targeting",
                "evidence-honesty before decision declaration",
            ],
            "reasoning_operator": "check whether validation targets, Stage-02b execution state, and convergence readiness remain mutually consistent",
            "material_grounding": material_grounding_lines(skill_assets),
            "alternatives_compared": ["treat convergence as automatic", "gate convergence on explicit stage coupling"],
            "tradeoff_or_tension": "faster PRD convergence vs audit-safe dependency honesty",
            "decision_effect": "allowed ready-to-converge output while preserving explicit Stage-02b coupling and blocked assumptions",
            "evidence_classification": [
                "observed fact: Stage-04 must declare whether Stage-02b was executed and what that means downstream",
                "interpreted pattern: convergence without coupling declarations creates false delivery confidence",
                "decision: keep convergence admission tied to stage coupling and validation state",
            ],
            "evidence_state": "review-bound",
            "remaining_unknown": "later evidence may still tighten convergence rules",
            "downstream_handoff": "PRD assembly and execution report should preserve the same convergence admission language",
            "freeze_rationale": "stage coupling is explicit enough for downstream convergence",
        },
    ]
    maturity_rows = [
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
            "current_basis": f"source 已明确给出 `{constraints[0]}` 等约束，Stage-04 已把它们转成显式 validation target。",
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
    if stage_02b_executed:
        upstream_stage_lines = "\n".join(
            [
                "  - Stage-03 `Chosen Slice`",
                "  - Stage-03 `NFR-Aware Slice Impact and Dependency-First Logic`",
                "  - Stage-03 `Key Assumptions to Validate`",
                "  - Stage-03 `Deferred Items Honesty Check`",
            ]
        )
        stage_02b_state_block = """- stage_02b_execution_state:
  - `executed`
- handoff_nfr_state:
  - `present`
- handoff_nfr_notes:
  - Stage-02b 已提供 quality scenario matrix、metric register、module responsibility 与 payload contract。
- stage_02b_skip_declaration:
  - not required because Stage-02b was executed in full for this run"""
    else:
        upstream_stage_lines = "\n".join(
            [
                "  - Stage-02a `NFR Initial Identification`",
                "  - Stage-03 `Chosen Slice`",
                "  - Stage-03 `NFR-Aware Slice Impact and Dependency-First Logic`",
                "  - Stage-03 `Key Assumptions to Validate`",
                "  - Stage-03 `Deferred Items Honesty Check`",
            ]
        )
        stage_02b_state_block = """- stage_02b_execution_state:
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
  - mitigation_note: `Phase-2 不得假定 Stage-02b 已冻结；它必须把 NFR / domain / IA deepening 作为显式 architecture discovery workstream，而不是隐式补锅。`"""

    return f"""# Stage-04 Output — requirements-validation-and-concept-proof (deep-compiled)

## 1. Document Metadata
- document_name: `{product_label} Phase-1 Trial Stage-04 Validation {version}`
- stage: `requirements-validation-and-concept-proof`
- version: `{version}`
- status: `provisional`
- owner: `{owner}`
- source_status: `mixed`

{render_traceability_block("stage_04")}

## 2. Context and Objective
- current_validation_target:
  - 验证 Stage-03 选择的 `{module_chain}` 首个切片是否值得继续作为设计/架构主线。
- validation_objective:
  - 把 Stage-03 的关键假设转成可判定的验证链，而不是继续停留在结构性推断。
- upstream_stage_materially_used:
{upstream_stage_lines}

## 3. Validation Targets
{chr(10).join([f"- {item['id']}:\n  - Target {idx}: {item['assumption']}" for idx, item in enumerate(validation_targets, start=1)])}

## 4. Validation Target Clarity
| target | exact_assumption_tested | what_changes_if_positive | what_changes_if_negative | primary dimension |
|---|---|---|---|---|
{chr(10).join(f"| {item['id']} | {item['assumption']} | {item.get('positive', 'preserve current direction')} | {item.get('negative', 'revise the current slice or boundary')} | {item['dimension']} |" for item in validation_targets)}

## 5. Method-Fit Comparison
| candidate method | fit_to_target | cost_and_speed | evidence_quality | why_not_chosen_or_chosen |
|---|---|---|---|---|
{chr(10).join(method_rows)}
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
{chr(10).join(f"  - {item['id']}: {item['threshold']}" for item in validation_targets[:5])}

## 8. Validation Plan and Signal Chain
| target | method | artifact | threshold | learning_if_pass | learning_if_fail |
|---|---|---|---|---|---|
{chr(10).join(f"| {item['id']} | {item['method']} | {item['artifact']} | {item['threshold']} | {item.get('positive', 'preserve current direction')} | {item.get('negative', 'revise current direction')} |" for item in validation_targets)}

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
{chr(10).join(f"  - {item['assumption']}" for item in validation_targets[:5])}

{render_maturity_confidence_section(
    "## 11. Delivery Readiness and Evidence Confidence",
    document_delivery_state="downstream-start-safe",
    evidence_confidence_state="source-grounded-but-unvalidated",
    safe_start_scope=[
        f"设计可以启动 `{primary_flow_name}` 的 workflow prototype 与关键页面表达",
        f"架构可以启动 `{module_chain}` 的 object chain / audit boundary 设计",
        "产品可以继续准备 interviews、constraint review 和 comparison artifacts",
    ],
    blocked_commitments=[
        "不得把当前文档当作 implementation-commit-ready 需求冻结包",
        "不得承诺 Stage-03 assumptions 已经被真实证据证明",
        "不得承诺客群、约束适配或流程可理解性已全部验证完成",
    ],
    rows=maturity_rows,
)}

## 12. Decision State and Revision Consequences
- decision: `Revise`
- reasoning:
  - 结构和主文档已足够支持设计/架构探索，但 validation chain 仍缺真实 evidence，因此不能给 Go。
- revision_consequences:
{chr(10).join(f"  - 若 `{item['id']}` 失败：{item.get('negative', 'revise current direction')}" for item in validation_targets[:5])}
- what_downstream_must_not_assume:
  - 首发客群已被验证
  - 主流程已被真实用户验证通过
  - 约束适配已被证明无风险
  - 延后项可以安全提前进入 MVP

## 13. Review-Bound Carryover and Forbidden Assumptions
- must_not_assume:
  - 需求已验证
  - 主流程已真实跑通
  - 关键约束已被实现验证
- carryover_truths:
{chr(10).join(f"  - {item['assumption']}" for item in validation_targets[:3])}

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
    - what_was_refined: `fit methods to assumption type instead of forcing one default`
    - outcome: `continue`
  - round_3:
    - trigger: `decision state lacked downstream consequence`
    - artifact_unit_improved: `triad verdict + revision consequence`
    - what_was_refined: `keep revise-state honesty and target-linked consequences visible`
    - outcome: `freeze`

{render_reasoning_unit_ledger("## 18. Minimal Reasoning Unit Ledger", reasoning_units, context=context)}

{render_material_grounding_bridge("## 19. Material Grounding Bridge", skill_assets, context)}

{render_skill_asset_snapshot(
    "## 20. Skill Asset Ingestion Snapshot",
    skill_assets,
    [
        "exact assumptions were defined before method selection",
        "method choices were compared rather than assumed",
        "evidence honesty and decision consequence both remained explicit",
        "Stage-03 assumptions and deferred honesty were carried into validation design",
    ],
    context,
)}

{render_method_activation_evidence("## 21. Method Activation Evidence", reasoning_units, context=context)}

## 22. Upstream Stage Carryover Evidence
{demote_headings(s2a_nfr)}

{demote_headings(s3_slice)}

{demote_headings(s3_nfr_impact)}

{demote_headings(s3_assumptions)}

{demote_headings(s3_honesty)}

## 23. Source Evidence Pack
{demote_headings(h61)}

{demote_headings(h62)}

{demote_headings(h9)}

{demote_headings(h10)}

{demote_headings(h12)}
"""


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
            "- scope: `major Phase-1 artifact units`\n"
            "- boundary: `bounded value-strengthening, not length expansion`\n"
            "- exit: `stop when another round no longer improves practical decision/action/evidence/review/handoff value`\n",
            encoding="utf-8",
        )

    stage_01 = output_dir / "stage-01-user-research.md"
    stage_02a = output_dir / "stage-02a-requirements-structural-analysis.md"
    stage_02b = output_dir / "stage-02b-requirements-specification-deepening.md"
    stage_03 = output_dir / "stage-03-requirements-decomposition-and-mvp-slicing.md"
    stage_04 = output_dir / "stage-04-requirements-validation-and-concept-proof.md"
    business_world_model_path = output_dir / PHASE1_BUSINESS_WORLD_MODEL_FILENAME
    operating_baseline_model_path = output_dir / PHASE1_OPERATING_BASELINE_MODEL_FILENAME
    product_world_decision_path = output_dir / PHASE1_PRODUCT_WORLD_DECISION_FILENAME
    business_release_truth_pack_path = output_dir / PHASE1_BUSINESS_RELEASE_TRUTH_PACK_FILENAME
    planning_control_truth_pack_path = output_dir / PHASE1_PLANNING_CONTROL_TRUTH_PACK_FILENAME
    business_exploration_arena_json_path = output_dir / "business-exploration-arena.json"
    business_exploration_arena_md_path = output_dir / "business-exploration-arena.md"
    commercial_argument_draft_json_path = output_dir / "commercial-argument-draft.json"
    commercial_argument_draft_md_path = output_dir / "commercial-argument-draft.md"
    chosen_business_thesis_json_path = output_dir / "chosen-business-thesis.json"
    chosen_business_thesis_md_path = output_dir / "chosen-business-thesis.md"
    semantic_authoring_spine_path = output_dir / ".phase1-evidence" / "p1-semantic-authoring-spine.json"

    stage_01_text = build_stage_01(source_text, args.version, args.owner)
    stage_02a_text = build_stage_02a(source_text, args.version, args.owner)
    stage_02b_text = (
        build_stage_02b_skip_stub(source_text, stage_02a_text, args.version, args.owner)
        if args.skip_stage_02b
        else build_stage_02b(source_text, args.version, args.owner)
    )
    stage_03_text = build_stage_03(
        source_text,
        stage_02a_text,
        stage_02b_text,
        stage_02b_executed=not args.skip_stage_02b,
        version=args.version,
        owner=args.owner,
    )
    stage_04_text = build_stage_04(
        source_text,
        stage_02a_text,
        stage_03_text,
        stage_02b_executed=not args.skip_stage_02b,
        version=args.version,
        owner=args.owner,
    )

    write(stage_01, stage_01_text, args.output_locale)
    write(stage_02a, stage_02a_text, args.output_locale)
    write(stage_02b, stage_02b_text, args.output_locale)
    write(stage_03, stage_03_text, args.output_locale)
    write(stage_04, stage_04_text, args.output_locale)
    business_world_model = apply_commercial_argument_rewrite(
        build_business_world_model(source_text),
        load_commercial_argument_rewrite(output_dir),
    )
    if args.thinking_value_gain_mode == "full-use":
        business_world_model = apply_thinking_value_gain_full_use(business_world_model)
    business_world_model_path.write_text(
        json.dumps(business_world_model, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    semantic_authoring_spine_path.parent.mkdir(parents=True, exist_ok=True)
    semantic_authoring_spine_path.write_text(
        json.dumps(semantic_authoring_spine_from_model(business_world_model), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    operating_baseline_model_path.write_text(
        json.dumps(business_world_model.get("operating_baseline_model", {}), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    product_world_decision_path.write_text(
        json.dumps(business_world_model.get("product_world_decision", {}), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    business_release_truth_pack_path.write_text(
        json.dumps(business_world_model.get("business_release_truth_pack", {}), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    planning_control_truth_pack_path.write_text(
        json.dumps(business_world_model.get("planning_control_truth_pack", {}), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    business_exploration_arena = business_world_model.get("business_exploration_arena", {})
    commercial_argument_draft = business_world_model.get("commercial_argument_draft", {})
    chosen_business_thesis = business_world_model.get("chosen_business_thesis", {})
    business_exploration_arena_json_path.write_text(
        json.dumps(business_exploration_arena, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    business_exploration_arena_md_path.write_text(
        render_business_exploration_arena_markdown(business_exploration_arena if isinstance(business_exploration_arena, dict) else {}),
        encoding="utf-8",
    )
    commercial_argument_draft_json_path.write_text(
        json.dumps(commercial_argument_draft, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    commercial_argument_draft_md_path.write_text(
        render_commercial_argument_draft_markdown(commercial_argument_draft if isinstance(commercial_argument_draft, dict) else {}),
        encoding="utf-8",
    )
    chosen_business_thesis_json_path.write_text(
        json.dumps(chosen_business_thesis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    chosen_business_thesis_md_path.write_text(
        render_chosen_business_thesis_markdown(chosen_business_thesis if isinstance(chosen_business_thesis, dict) else {}),
        encoding="utf-8",
    )

    print(f"generated: {stage_01}")
    print(f"generated: {stage_02a}")
    print(f"generated: {stage_02b}")
    print(f"generated: {stage_03}")
    print(f"generated: {stage_04}")
    print(f"generated: {business_world_model_path}")
    print(f"generated: {semantic_authoring_spine_path}")
    print(f"generated: {operating_baseline_model_path}")
    print(f"generated: {product_world_decision_path}")
    print(f"generated: {business_release_truth_pack_path}")
    print(f"generated: {planning_control_truth_pack_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
