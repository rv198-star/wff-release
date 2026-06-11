#!/usr/bin/env python3
"""
Converge an audit-rich Phase-1 PRD into a downstream-consumable PRD.

The assembled PRD is allowed to retain runtime/audit residue needed for
intermediate review. This script separates that residue into a standalone
convergence evidence memo so the final PRD can stay design/architecture-ready.
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
import sys
from pathlib import Path

from common.output_language import resolve_output_locale
from phase1.phase1_localize_prd_zh import render_primary_locale_lines

TRACE_BULLET_PREFIXES = (
    "loop_state:",
    "rounds_executed:",
    "round_log:",
    "sop_execution_steps_compiled:",
    "sop_checkpoints_compiled:",
    "sop_handoff_obligations_compiled:",
    "sop_output_obligations_compiled:",
    "source_bundles_loaded:",
    "required_method_assets_materially_applied:",
    "current_use_rules_compiled:",
    "reasoning_template_obligations_compiled:",
    "runtime_use_rules_respected:",
    "method_asset_activation:",
)

TRACE_ONLY_H3_TITLES = {
    "Integrated Slicing Trace",
    "Validation Traceability",
}

COMPACT_REASONING_LEDGER_TITLES = {
    "Boundary Reasoning Ledger",
    "Structural Reasoning Ledger",
    "Specification Reasoning Ledger",
    "Slice Reasoning Ledger",
    "Validation Reasoning Ledger",
}

PRESERVED_MACHINE_READABLE_H3_TITLES = (
    "Competitive Landscape Summary",
    "Acceptance Criteria",
    "Pricing Validation Design",
    "Information Architecture Spec Matrix",
    "Core Business Objects",
    "Epic Decomposition",
    "Story Quality Gate (INVEST)",
)

NARRATIVE_COMPRESSION_REWRITE_FILENAME = "prd-narrative-compression-rewrite.json"
NARRATIVE_COMPRESSION_REQUIRED_KEYS = {
    "compression_intent",
    "main_narrative_replacements",
    "evidence_relocation_notes",
    "must_preserve_business_signals",
    "must_preserve_gate_evidence",
    "risk_review",
    "quality_state",
}
ALLOWED_NARRATIVE_COMPRESSION_TARGETS = {
    "Executive Summary",
    "Chosen Business Thesis",
    "Problem Statement",
    "Protected Business-World Truth Spine",
}


def is_runtime_material_block(title: str) -> bool:
    return title.startswith("Material-Grounded ") and title.endswith(" Rules")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def load_narrative_compression_rewrite(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if not NARRATIVE_COMPRESSION_REQUIRED_KEYS.issubset(payload):
        return None
    replacements = payload.get("main_narrative_replacements")
    if not isinstance(replacements, list):
        return None
    return payload


def _heading_matches_narrative_target(section_title: str, target_heading: str) -> bool:
    normalized_section = normalize_heading(section_title)
    normalized_target = normalize_heading(target_heading)
    if normalized_section == normalized_target:
        return True
    return normalized_target in normalized_section or normalized_section.endswith(normalized_target)


def strip_narrative_compression_provenance(text: str) -> str:
    return re.sub(
        r"\n## Narrative Compression Provenance\n(?:- .*\n?)*\s*$",
        "\n",
        text.rstrip() + "\n",
        flags=re.MULTILINE,
    ).rstrip()


def apply_narrative_compression_rewrite(text: str, rewrite: dict[str, object] | None) -> str:
    if not isinstance(rewrite, dict):
        return text
    text = strip_narrative_compression_provenance(text)
    replacements_raw = rewrite.get("main_narrative_replacements")
    if not isinstance(replacements_raw, list):
        return text
    replacements: list[dict[str, object]] = [item for item in replacements_raw if isinstance(item, dict)]
    if not replacements:
        return text

    sections = split_h2_sections(text)
    if not sections:
        return text
    rebuilt: list[str] = []
    applied: list[str] = []
    for heading, section_title, body in sections:
        replacement = None
        for candidate in replacements:
            target = str(candidate.get("target_heading", "")).strip()
            replacement_text = str(candidate.get("replacement_markdown", "")).strip()
            if target in ALLOWED_NARRATIVE_COMPRESSION_TARGETS and replacement_text and _heading_matches_narrative_target(section_title, target):
                replacement = candidate
                break
        if replacement is None:
            rebuilt.append("\n".join([heading, body]).strip())
            continue
        replacement_text = str(replacement.get("replacement_markdown", "")).strip()
        preserved_refs = replacement.get("preserved_references", [])
        ref_lines = []
        if isinstance(preserved_refs, list) and preserved_refs:
            ref_lines = ["", "### Preserved References", *[f"- {str(item).strip()}" for item in preserved_refs if str(item).strip()]]
        rebuilt.append("\n".join([heading, "", replacement_text, *ref_lines]).strip())
        applied.append(str(replacement.get("target_heading", "")).strip())

    result = "\n\n".join(rebuilt).strip()
    if applied:
        provenance = [
            "",
            "## Narrative Compression Provenance",
            f"- quality_state: `{str(rewrite.get('quality_state', 'review-bound')).strip()}`",
            f"- compression_intent: {str(rewrite.get('compression_intent', '')).strip()}",
            f"- applied_targets: {', '.join(applied)}",
            f"- risk_review: {str(rewrite.get('risk_review', '')).strip()}",
        ]
        result = "\n".join([result, *provenance]).strip()
    return result + "\n"


def normalize_heading(raw: str) -> str:
    value = raw.strip()
    value = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", value).strip()
    return value


def has_heading(text: str, level: int, title: str) -> bool:
    return bool(
        re.search(
            rf"^{re.escape('#' * level)}\s+{re.escape(title)}\s*$",
            text,
            flags=re.MULTILINE,
        )
    )


def missing_preserved_machine_blocks(source_text: str, final_text: str) -> list[str]:
    missing: list[str] = []
    for title in PRESERVED_MACHINE_READABLE_H3_TITLES:
        if has_heading(source_text, 3, title) and not has_heading(final_text, 3, title):
            missing.append(title)
    return missing


def split_h2_sections(text: str) -> list[tuple[str, str, str]]:
    matches = list(re.finditer(r"^##\s+.*$", text, flags=re.MULTILINE))
    sections: list[tuple[str, str, str]] = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        heading = match.group(0).strip()
        title = normalize_heading(re.sub(r"^##\s+", "", heading))
        body = text[match.end() : end].strip("\n")
        sections.append((heading, title, body))
    return sections


def split_h3_blocks(body: str) -> list[tuple[str | None, str]]:
    if not body.strip():
        return []
    matches = list(re.finditer(r"^###\s+.*$", body, flags=re.MULTILINE))
    if not matches:
        return [(None, body.strip("\n"))]

    blocks: list[tuple[str | None, str]] = []
    prefix = body[: matches[0].start()].strip("\n")
    if prefix:
        blocks.append((None, prefix))

    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        heading = match.group(0).strip()
        content = body[match.end() : end].strip("\n")
        blocks.append((heading, content))
    return blocks


def is_trace_bullet(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped.startswith("- "):
        return False
    payload = stripped[2:]
    return any(payload.startswith(prefix) for prefix in TRACE_BULLET_PREFIXES)


def normalize_spacing(text: str) -> str:
    lines = text.splitlines()
    compact: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip():
            blank_run = 0
            compact.append(line.rstrip())
            continue
        blank_run += 1
        if blank_run <= 1:
            compact.append("")
    return "\n".join(compact).strip()


def flatten_single_value_bullets(text: str) -> str:
    lines = text.splitlines()
    flattened: list[str] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        parent = re.match(r"^(\s*)-\s+([^:\n][^:\n]*?):\s*$", line)
        if not parent:
            flattened.append(line)
            idx += 1
            continue

        parent_indent = len(parent.group(1))
        label = parent.group(2)
        children: list[tuple[int, str]] = []
        probe = idx + 1
        while probe < len(lines):
            current = lines[probe]
            if not current.strip():
                probe += 1
                continue
            if current.startswith("#"):
                break
            current_indent = len(current) - len(current.lstrip(" "))
            if current_indent <= parent_indent:
                break
            children.append((probe, current))
            probe += 1

        if len(children) == 1:
            child_match = re.match(r"^\s*-\s+(.+?)\s*$", children[0][1])
            if child_match:
                flattened.append(f"{' ' * parent_indent}- {label}: {child_match.group(1)}")
                idx = children[0][0] + 1
                continue

        flattened.append(line)
        idx += 1

    return normalize_spacing("\n".join(flattened))


def normalize_field_value(raw: str) -> str:
    lines = [line.rstrip() for line in raw.strip().splitlines() if line.strip()]
    if not lines:
        return ""
    cleaned: list[str] = []
    for idx, line in enumerate(lines):
        value = line
        if idx == 0:
            value = re.sub(r"^\s*", "", value)
        value = re.sub(r"^\s*-\s+", "", value)
        value = re.sub(r"^\s+", "", value)
        cleaned.append(value.strip().strip("`"))
    return "; ".join(item for item in cleaned if item)


def extract_field(body: str, field: str) -> str:
    match = re.search(
        rf"^\s*-\s+{re.escape(field)}:\s*(?P<body>.*?)(?=^\s*-\s+[a-z_]+:|^#{3,6}\s+Reasoning Unit|\Z)",
        body,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if not match:
        return ""
    return normalize_field_value(match.group("body"))


def compress_reasoning_ledger(body: str) -> str:
    matches = list(re.finditer(r"^#{3,6}\s+Reasoning Unit\s+\d+:\s+(.+)$", body, flags=re.MULTILINE))
    if not matches:
        return body.strip()

    compact_blocks: list[str] = []
    for idx, match in enumerate(matches):
        title = match.group(1).strip()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        unit_body = body[match.end() : end]
        compared = extract_field(unit_body, "alternatives_compared")
        tradeoff = extract_field(unit_body, "tradeoff_or_tension")
        effect = extract_field(unit_body, "decision_effect")
        unknown = extract_field(unit_body, "remaining_unknown")
        downstream = extract_field(unit_body, "downstream_handoff")

        lines = [f"### Reasoning Unit {idx + 1}: {title}"]
        if compared:
            lines.append(f"- alternatives_compared: {compared}")
        if tradeoff:
            lines.append(f"- tradeoff_or_tension: {tradeoff}")
        if effect:
            lines.append(f"- decision_effect: {effect}")
        if unknown:
            lines.append(f"- remaining_unknown: {unknown}")
        if downstream:
            lines.append(f"- downstream_handoff: {downstream}")
        compact_blocks.append("\n".join(lines).strip())

    return "\n\n".join(compact_blocks).strip()


def compress_validation_maturity_block(body: str) -> str:
    lines = body.splitlines()
    kept: list[str] = []
    dropped_table = False
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.lstrip().startswith("|"):
            dropped_table = True
            idx += 1
            while idx < len(lines) and lines[idx].lstrip().startswith("|"):
                idx += 1
            continue
        kept.append(line)
        idx += 1
    if dropped_table:
        if kept and kept[-1].strip():
            kept.append("")
        kept.append("- subject_level_ledger_note:")
        kept.append("  - detailed subject-level maturity/confidence ledger is preserved in PRD §19 and the convergence evidence memo")
        kept.append("- forbidden_assumptions:")
        kept.append("  - subject-level forbidden_assumptions remain binding; see PRD §19 and the convergence evidence memo")
    return normalize_spacing("\n".join(kept))


def extract_trace_groups(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines()
    kept: list[str] = []
    removed: list[str] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        if not is_trace_bullet(line):
            kept.append(line)
            idx += 1
            continue

        group = [line]
        idx += 1
        while idx < len(lines):
            current = lines[idx]
            if current.startswith("## ") or current.startswith("### "):
                break
            if current.startswith("- ") and not is_trace_bullet(current):
                break
            group.append(current)
            idx += 1
        removed.append("\n".join(group).rstrip())

    return normalize_spacing("\n".join(kept)), removed


def update_source_artifacts(body: str, *, assembled_name: str, evidence_name: str | None) -> str:
    lines = body.splitlines()
    existing = {line.strip() for line in lines if line.strip().startswith("- ")}
    additions = [f"- {assembled_name}"]
    if evidence_name:
        additions.append(f"- {evidence_name}")
    for item in additions:
        if item not in existing:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(item)
    return normalize_spacing("\n".join(lines))


def build_convergence_evidence_lines(
    *,
    title: str,
    assembled_path: Path,
    output_path: Path,
    evidence_path: Path,
    delta_body: str | None,
    removed_blocks: list[dict[str, str]],
) -> list[str]:
    lines = [
        f"# {normalize_heading(title)} — Convergence Evidence Memo",
        "",
        "## 0. Metadata",
        f"- assembled_prd: `{assembled_path.name}`",
        f"- converged_prd: `{output_path.name}`",
        f"- convergence_evidence: `{evidence_path.name}`",
        f"- extracted_runtime_trace_blocks: `{len(removed_blocks)}`",
        f"- analysis_delta_ledger_externalized: `{'yes' if delta_body else 'no'}`",
        "",
        "## 1. Convergence Summary",
        "- goal: separate downstream-consumable PRD content from runtime/audit residue",
        "- final_prd_boundary: keep sections that product/design/architecture must directly consume",
        "- evidence_boundary: preserve delta ledger and runtime traces outside the final PRD instead of deleting them",
        "- expected_effect: final PRD stays deep and usable without carrying stage-SOP/material-ingestion noise inline",
    ]

    if delta_body:
        lines.extend(
            [
                "",
                "## 2. Analysis Delta Ledger",
                delta_body.strip(),
            ]
        )

    lines.extend(["", "## 3. Extracted Runtime Trace Blocks"])
    if not removed_blocks:
        lines.append("- none")
    else:
        for idx, block in enumerate(removed_blocks, start=1):
            lines.extend(
                [
                    "",
                    f"### Trace {idx}",
                    f"- source_section: `{block['section']}`",
                    f"- source_block: `{block['block']}`",
                    "",
                    block["content"].rstrip(),
                ]
            )

    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Converge an audit-rich Phase-1 PRD")
    parser.add_argument("--assembled-prd", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--evidence-output")
    parser.add_argument("--narrative-compression-rewrite")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    args = parser.parse_args()

    assembled_path = Path(args.assembled_prd).resolve()
    output_path = Path(args.output).resolve()
    evidence_path = (
        Path(args.evidence_output).resolve()
        if args.evidence_output
        else output_path.with_name(f"{output_path.stem}-convergence-evidence{output_path.suffix}")
    )

    source_text = read_text(assembled_path)
    title_match = re.search(r"^#\s+(.+)$", source_text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Phase-1 PRD"

    cleaned_sections: list[str] = []
    removed_blocks: list[dict[str, str]] = []
    delta_body: str | None = None

    for heading, section_title, body in split_h2_sections(source_text):
        if section_title == "Analysis Delta Ledger":
            delta_body = body.strip()
            continue

        rebuilt_blocks: list[str] = []
        for block_heading, block_body in split_h3_blocks(body):
            block_title = (
                normalize_heading(re.sub(r"^###\s+", "", block_heading)) if block_heading else "(section-body)"
            )
            if block_heading and block_title in TRACE_ONLY_H3_TITLES:
                removed_blocks.append(
                    {
                        "section": section_title,
                        "block": block_title,
                        "content": "\n".join([block_heading, block_body]).strip(),
                    }
                )
                continue

            if block_heading and is_runtime_material_block(block_title):
                removed_blocks.append(
                    {
                        "section": section_title,
                        "block": block_title,
                        "content": "\n".join([block_heading, block_body]).strip(),
                    }
                )
                continue

            if block_heading and block_title in COMPACT_REASONING_LEDGER_TITLES:
                removed_blocks.append(
                    {
                        "section": section_title,
                        "block": block_title,
                        "content": "\n".join([block_heading, block_body]).strip(),
                    }
                )
                cleaned_body = compress_reasoning_ledger(block_body)
                if cleaned_body.strip():
                    rebuilt_blocks.append("\n".join([block_heading, cleaned_body]).strip())
                continue

            if (
                block_heading
                and section_title == "Validation Strategy & Current Conclusion"
                and block_title == "Delivery Readiness and Evidence Confidence"
            ):
                removed_blocks.append(
                    {
                        "section": section_title,
                        "block": f"{block_title} (full-ledger)",
                        "content": "\n".join([block_heading, block_body]).strip(),
                    }
                )
                cleaned_body = compress_validation_maturity_block(block_body)
                rebuilt_blocks.append("\n".join([block_heading, cleaned_body]).strip())
                continue

            cleaned_body, stripped_groups = extract_trace_groups(block_body)
            for group in stripped_groups:
                removed_blocks.append(
                    {
                        "section": section_title,
                        "block": block_title,
                        "content": group,
                    }
                )

            if section_title == "Source Artifacts":
                cleaned_body = update_source_artifacts(
                    cleaned_body,
                    assembled_name=assembled_path.name,
                    evidence_name=evidence_path.name,
                )

            if not cleaned_body.strip() and block_heading:
                continue
            if block_heading:
                rebuilt_blocks.append("\n".join([block_heading, cleaned_body]).strip())
            elif cleaned_body.strip():
                rebuilt_blocks.append(cleaned_body.strip())

        section_payload = heading
        if rebuilt_blocks:
            section_payload = "\n".join([heading, "", "\n\n".join(rebuilt_blocks).strip()]).strip()
        cleaned_sections.append(section_payload)

    final_prd = flatten_single_value_bullets("\n\n".join([f"# {title}", *cleaned_sections]).strip())
    final_prd = apply_narrative_compression_rewrite(
        final_prd,
        load_narrative_compression_rewrite(Path(args.narrative_compression_rewrite).resolve() if args.narrative_compression_rewrite else None),
    )
    missing_blocks = missing_preserved_machine_blocks(source_text, final_prd)
    if missing_blocks:
        print("== Phase-1 PRD Convergence ==")
        print(f"assembled_prd: {assembled_path}")
        print(f"converged_prd: {output_path}")
        print("FINAL: BLOCKED")
        print(f"missing_preserved_blocks: {', '.join(missing_blocks)}")
        return 2
    evidence_lines = build_convergence_evidence_lines(
        title=title,
        assembled_path=assembled_path,
        output_path=output_path,
        evidence_path=evidence_path,
        delta_body=delta_body,
        removed_blocks=removed_blocks,
    )
    output_locale = resolve_output_locale(args.output_locale)
    evidence_text = "\n".join(
        render_primary_locale_lines(evidence_lines, evidence_path.name, output_locale)
    ).strip()

    write_text(output_path, final_prd)
    write_text(evidence_path, evidence_text)

    print("== Phase-1 PRD Convergence ==")
    print(f"assembled_prd: {assembled_path}")
    print(f"converged_prd: {output_path}")
    print(f"convergence_evidence: {evidence_path}")
    print(f"trace_blocks_externalized: {len(removed_blocks)}")
    print(f"analysis_delta_externalized: {'yes' if delta_body else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
