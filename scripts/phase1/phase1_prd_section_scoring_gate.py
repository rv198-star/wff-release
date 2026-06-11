#!/usr/bin/env python3
"""
Phase-1 PRD section scoring gate.

This gate turns "looks deep enough" into a reproducible closing acceptance test.
Each critical PRD section is scored across five dimensions:
- completeness
- detail depth
- decision / trade-off clarity
- downstream usability
- uncertainty / boundary honesty

The closing bar is intentionally strict: every tracked section must reach the
configured threshold, not just the average score.
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
from dataclasses import dataclass
from pathlib import Path

from common.script_data_assets import load_script_json_asset
from phase1.phase1_gate_authority import emit_compatibility_warning


@dataclass(frozen=True)
class PatternDef:
    label: str
    regex: str


@dataclass(frozen=True)
class SectionRule:
    name: str
    title_pattern: str
    required_subheadings: tuple[str, ...]
    min_nonempty_lines: int
    detail_patterns: tuple[PatternDef, ...]
    decision_patterns: tuple[PatternDef, ...]
    downstream_patterns: tuple[PatternDef, ...]
    honesty_patterns: tuple[PatternDef, ...]


WFF_SCRIPT_DATA_ASSETS = (
    "scripts/phase1/data/prd-section-scoring-rules.json",
)


def _coerce_pattern_defs(items: object) -> tuple[PatternDef, ...]:
    if not isinstance(items, list):
        return ()
    return tuple(
        PatternDef(label=str(item.get("label", "")), regex=str(item.get("regex", "")))
        for item in items
        if isinstance(item, dict)
    )


def _coerce_section_rule(item: object) -> SectionRule | None:
    if not isinstance(item, dict):
        return None
    return SectionRule(
        name=str(item.get("name", "")),
        title_pattern=str(item.get("title_pattern", "")),
        required_subheadings=tuple(str(value) for value in item.get("required_subheadings", []) if str(value)),
        min_nonempty_lines=int(item.get("min_nonempty_lines", 0)),
        detail_patterns=_coerce_pattern_defs(item.get("detail_patterns")),
        decision_patterns=_coerce_pattern_defs(item.get("decision_patterns")),
        downstream_patterns=_coerce_pattern_defs(item.get("downstream_patterns")),
        honesty_patterns=_coerce_pattern_defs(item.get("honesty_patterns")),
    )


def _load_section_rules() -> tuple[SectionRule, ...]:
    loaded = load_script_json_asset(__file__, "prd-section-scoring-rules.json")
    if not isinstance(loaded, dict):
        return ()
    rules = [_coerce_section_rule(item) for item in loaded.get("section_rules", [])]
    return tuple(rule for rule in rules if rule is not None)


SECTION_RULES = _load_section_rules()

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_heading(raw: str) -> str:
    value = raw.strip()
    value = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", value).strip()
    return value


def canonicalize_heading(raw: str) -> str:
    value = normalize_heading(raw)
    value = re.sub(r"\s*\([^)]*\)\s*$", "", value).strip().lower()
    value = re.sub(r"\s+", " ", value)
    aliases = {
        "module interface payload contract": "payload contract",
        "recommendation payload contract": "payload contract",
        "deferred capability seam": "deferred seam",
        "deferred attribution and conversion seam": "deferred seam",
    }
    value = aliases.get(value, value)
    return value


def heading_matches(required: str, actual: str) -> bool:
    required_raw = re.sub(r"\s+", " ", normalize_heading(required).lower())
    actual_raw = re.sub(r"\s+", " ", normalize_heading(actual).lower())
    required_key = canonicalize_heading(required)
    actual_key = canonicalize_heading(actual)
    return (
        actual_key == required_key
        or actual_key.startswith(required_key)
        or required_key.startswith(actual_key)
        or required_raw in actual_raw
        or actual_raw in required_raw
    )


def extract_h2_block(text: str, title_pattern: str) -> str | None:
    match = re.search(
        rf"^##\s+(?:\d+\.\s+)?[^\n]*?(?:{title_pattern})[^\n]*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return None
    start = match.end()
    next_h2 = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)
    end = start + next_h2.start() if next_h2 else len(text)
    return text[start:end]


def canonicalize_bilingual_text(text: str) -> str:
    normalized_lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            canonical_cells = []
            for cell in cells:
                aliases = re.findall(r"\(([^()\n]+)\)", cell)
                canonical_cells.append(aliases[-1].strip() if aliases else cell)
            normalized_lines.append("| " + " | ".join(canonical_cells) + " |")
            continue
        normalized_lines.append(re.sub(r"([^|\n()]+?)\s*\(([^()\n]+)\)", r"\2", raw))
    return "\n".join(normalized_lines)


def extract_h3_titles(block: str) -> list[str]:
    return [
        normalize_heading(match.group(1))
        for match in re.finditer(r"^###\s+(.+)$", block, flags=re.MULTILINE)
    ]


def count_nonempty_lines(block: str) -> int:
    return sum(1 for line in block.splitlines() if line.strip())


def matched_labels(text: str, patterns: tuple[PatternDef, ...]) -> list[str]:
    normalized = canonicalize_bilingual_text(text)
    return [
        item.label
        for item in patterns
        if re.search(item.regex, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        or re.search(item.regex, normalized, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    ]


def ratio_score(matched: int, total: int, max_points: float) -> float:
    if total <= 0:
        return max_points
    return round(max_points * matched / total, 1)


def score_section(text: str, rule: SectionRule, threshold: float) -> dict[str, object]:
    block = extract_h2_block(text, rule.title_pattern)
    if block is None:
        return {
            "name": rule.name,
            "present": False,
            "score": 0.0,
            "verdict": "BLOCKED",
            "line_count": 0,
            "dimensions": [
                {
                    "name": "completeness",
                    "score": 0.0,
                    "matched": 0,
                    "total": len(rule.required_subheadings),
                    "missing": list(rule.required_subheadings),
                }
            ],
            "missing_summary": ["section missing"],
        }

    h3_titles = extract_h3_titles(block)
    matched_headings = [
        title
        for title in rule.required_subheadings
        if any(heading_matches(title, item) for item in h3_titles)
    ]
    missing_headings = [
        title
        for title in rule.required_subheadings
        if not any(heading_matches(title, item) for item in h3_titles)
    ]
    line_count = count_nonempty_lines(block)

    detail_hits = matched_labels(block, rule.detail_patterns)
    decision_hits = matched_labels(block, rule.decision_patterns)
    downstream_hits = matched_labels(block, rule.downstream_patterns)
    honesty_hits = matched_labels(block, rule.honesty_patterns)

    completeness_score = ratio_score(len(matched_headings), len(rule.required_subheadings), 20.0)
    depth_line_score = round(10.0 * min(1.0, line_count / rule.min_nonempty_lines), 1)
    depth_structure_score = ratio_score(len(detail_hits), len(rule.detail_patterns), 10.0)
    depth_score = round(depth_line_score + depth_structure_score, 1)
    decision_score = ratio_score(len(decision_hits), len(rule.decision_patterns), 20.0)
    downstream_score = ratio_score(len(downstream_hits), len(rule.downstream_patterns), 20.0)
    honesty_score = ratio_score(len(honesty_hits), len(rule.honesty_patterns), 20.0)
    total_score = round(
        completeness_score + depth_score + decision_score + downstream_score + honesty_score,
        1,
    )

    dimensions = [
        {
            "name": "completeness",
            "score": completeness_score,
            "matched": len(matched_headings),
            "total": len(rule.required_subheadings),
            "missing": missing_headings,
        },
        {
            "name": "detail_depth",
            "score": depth_score,
            "line_score": depth_line_score,
            "line_count": line_count,
            "min_line_target": rule.min_nonempty_lines,
            "matched": len(detail_hits),
            "total": len(rule.detail_patterns),
            "missing": [item.label for item in rule.detail_patterns if item.label not in detail_hits],
        },
        {
            "name": "decision_tradeoff",
            "score": decision_score,
            "matched": len(decision_hits),
            "total": len(rule.decision_patterns),
            "missing": [item.label for item in rule.decision_patterns if item.label not in decision_hits],
        },
        {
            "name": "downstream_usability",
            "score": downstream_score,
            "matched": len(downstream_hits),
            "total": len(rule.downstream_patterns),
            "missing": [item.label for item in rule.downstream_patterns if item.label not in downstream_hits],
        },
        {
            "name": "boundary_honesty",
            "score": honesty_score,
            "matched": len(honesty_hits),
            "total": len(rule.honesty_patterns),
            "missing": [item.label for item in rule.honesty_patterns if item.label not in honesty_hits],
        },
    ]

    verdict = "PASS" if total_score >= threshold else "BLOCKED"
    missing_summary = []
    if missing_headings:
        missing_summary.append(f"missing_subheadings={', '.join(missing_headings)}")
    if line_count < rule.min_nonempty_lines:
        missing_summary.append(f"line_depth={line_count}/{rule.min_nonempty_lines}")
    for dimension in dimensions[1:]:
        if dimension["missing"]:
            missing_summary.append(
                f"{dimension['name']} missing: {', '.join(dimension['missing'][:3])}"
            )

    return {
        "name": rule.name,
        "present": True,
        "score": total_score,
        "verdict": verdict,
        "line_count": line_count,
        "dimensions": dimensions,
        "missing_summary": missing_summary,
    }


def main() -> int:
    emit_compatibility_warning("scripts/phase1/phase1_prd_section_scoring_gate.py")
    parser = argparse.ArgumentParser(description="Phase-1 PRD section scoring gate")
    parser.add_argument("--prd", required=True)
    parser.add_argument("--min-section-score", type=float, default=90.0)
    parser.add_argument(
        "--min-dimension-score",
        type=float,
        default=16.0,
        help="minimum score each scoring dimension must reach; prevents one thin dimension from being masked by others",
    )
    parser.add_argument("--output-json")
    args = parser.parse_args()

    prd_path = Path(args.prd).resolve()
    text = read_text(prd_path)

    results = [score_section(text, rule, args.min_section_score) for rule in SECTION_RULES]
    for item in results:
        dimension_scores = [float(dimension["score"]) for dimension in item["dimensions"]]
        dimension_blocked = any(score < args.min_dimension_score for score in dimension_scores)
        if item["verdict"] == "PASS" and dimension_blocked:
            item["verdict"] = "BLOCKED"
            item["missing_summary"].append(
                f"dimension_floor={args.min_dimension_score} not met"
            )
    average = round(sum(item["score"] for item in results) / len(results), 1) if results else 0.0
    blocked = [item for item in results if item["verdict"] != "PASS"]

    payload = {
        "prd": str(prd_path),
        "min_section_score": args.min_section_score,
        "min_dimension_score": args.min_dimension_score,
        "average_score": average,
        "sections": results,
    }
    if args.output_json:
        output_path = Path(args.output_json).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("== Phase-1 PRD Section Scoring Gate ==")
    print(f"prd: {prd_path}")
    print(f"min_section_score: {args.min_section_score}")
    print(f"min_dimension_score: {args.min_dimension_score}")
    for item in results:
        print(f"\n[{item['verdict']}] {item['name']}: total={item['score']}/100")
        for dimension in item["dimensions"]:
            if dimension["name"] == "detail_depth":
                print(
                    "  - detail_depth: "
                    f"{dimension['score']}/20 "
                    f"(lines={dimension['line_count']}/{dimension['min_line_target']}, "
                    f"signals={dimension['matched']}/{dimension['total']})"
                )
            else:
                print(
                    f"  - {dimension['name']}: {dimension['score']}/20 "
                    f"(matched={dimension['matched']}/{dimension['total']})"
                )
        if item["missing_summary"]:
            print(f"  - gaps: {'; '.join(item['missing_summary'][:4])}")

    print(f"\naverage_score: {average}")
    if blocked:
        print(f"blocked_sections: {', '.join(item['name'] for item in blocked)}")
        print("FINAL: BLOCKED")
        return 2

    print("FINAL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
