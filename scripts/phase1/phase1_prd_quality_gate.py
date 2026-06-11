#!/usr/bin/env python3
"""
Phase-1 PRD quality gate.

Purpose:
- detect "rules added but no practical effect" failure modes
- block PRD outputs that are over-compressed versus the structured source input
- check whether high-value source detail is preserved/recompiled in the PRD
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from common.script_data_assets import load_script_json_asset


@dataclass(frozen=True)
class PatternDef:
    label: str
    regex: str


@dataclass(frozen=True)
class CategoryDef:
    name: str
    ratio_required: float
    min_required: int
    patterns: tuple[PatternDef, ...]


@dataclass
class CategoryResult:
    name: str
    active: bool
    required: int
    source_hits: list[str]
    prd_hits: list[str]
    passed: bool


WFF_SCRIPT_DATA_ASSETS = ("scripts/phase1/data/prd-quality-gate-categories.json",)
_PRD_QUALITY_GATE_CATEGORIES = load_script_json_asset(__file__, "prd-quality-gate-categories.json")


def _pattern_def_from_payload(entry: dict[str, Any]) -> PatternDef:
    return PatternDef(label=str(entry["label"]), regex=str(entry["regex"]))


def _category_def_from_payload(entry: dict[str, Any]) -> CategoryDef:
    patterns = tuple(
        _pattern_def_from_payload(pattern)
        for pattern in entry.get("patterns", [])
        if isinstance(pattern, dict)
    )
    return CategoryDef(
        name=str(entry["name"]),
        ratio_required=float(entry["ratio_required"]),
        min_required=int(entry["min_required"]),
        patterns=patterns,
    )


CATEGORIES: tuple[CategoryDef, ...] = tuple(
    _category_def_from_payload(category)
    for category in _PRD_QUALITY_GATE_CATEGORIES.get("categories", [])
    if isinstance(category, dict)
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def count_sizes(text: str) -> tuple[int, int, int]:
    chars = len(text)
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    bytes_len = len(text.encode("utf-8"))
    return chars, lines, bytes_len


def matched_labels(text: str, patterns: Iterable[PatternDef]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern.regex, text, flags=re.IGNORECASE | re.MULTILINE):
            hits.append(pattern.label)
    return hits


def eval_category(source_text: str, prd_text: str, definition: CategoryDef) -> CategoryResult:
    src_hits = matched_labels(source_text, definition.patterns)
    prd_hits = matched_labels(prd_text, definition.patterns)
    if not src_hits:
        return CategoryResult(
            name=definition.name,
            active=False,
            required=0,
            source_hits=src_hits,
            prd_hits=prd_hits,
            passed=True,
        )
    required = max(definition.min_required, int(math.ceil(len(src_hits) * definition.ratio_required)))
    required = min(required, len(src_hits))
    passed = len(prd_hits) >= required
    return CategoryResult(
        name=definition.name,
        active=True,
        required=required,
        source_hits=src_hits,
        prd_hits=prd_hits,
        passed=passed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-1 PRD quality gate")
    parser.add_argument("--source", required=True, help="structured source input markdown")
    parser.add_argument("--prd", required=True, help="PRD markdown (assembled or converged)")
    parser.add_argument(
        "--convergence-evidence",
        help="optional convergence evidence markdown whose externalized audit trace should count toward stage-depth preservation",
    )
    parser.add_argument(
        "--stage",
        action="append",
        default=[],
        help="stage artifact file used for stage-to-prd depth ratio checks",
    )
    parser.add_argument(
        "--min-stage-char-ratio",
        type=float,
        default=0.40,
        help="minimum prd/(sum(stage chars)) when stage files are provided",
    )
    parser.add_argument(
        "--min-stage-line-ratio",
        type=float,
        default=0.30,
        help="minimum prd/(sum(stage lines)) when stage files are provided",
    )
    parser.add_argument(
        "--min-source-char-ratio",
        type=float,
        default=0.85,
        help="minimum prd/source character ratio even when stage-aware mode is active",
    )
    parser.add_argument(
        "--min-source-line-ratio",
        type=float,
        default=0.80,
        help="minimum prd/source line ratio even when stage-aware mode is active",
    )
    parser.add_argument(
        "--min-source-byte-ratio",
        type=float,
        default=1.00,
        help="minimum prd/source byte ratio even when stage-aware mode is active",
    )
    parser.add_argument(
        "--min-char-ratio",
        type=float,
        default=0.90,
        help="fallback minimum prd/source character ratio when no stage files are provided",
    )
    parser.add_argument(
        "--min-line-ratio",
        type=float,
        default=0.80,
        help="fallback minimum prd/source line ratio when no stage files are provided",
    )
    parser.add_argument(
        "--require-non-shrinking",
        action="store_true",
        help="require PRD chars >= source chars",
    )
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    prd_path = Path(args.prd).resolve()
    convergence_evidence_path = Path(args.convergence_evidence).resolve() if args.convergence_evidence else None
    stage_paths = [Path(item).resolve() for item in args.stage]
    source_text = read_text(source_path)
    prd_text = read_text(prd_path)
    evidence_text = (
        read_text(convergence_evidence_path)
        if convergence_evidence_path and convergence_evidence_path.exists()
        else ""
    )

    src_chars, src_lines, src_bytes = count_sizes(source_text)
    prd_chars, prd_lines, prd_bytes = count_sizes(prd_text)
    effective_chars = prd_chars
    effective_lines = prd_lines
    effective_bytes = prd_bytes
    ev_chars = ev_lines = ev_bytes = 0
    if evidence_text:
        ev_chars, ev_lines, ev_bytes = count_sizes(evidence_text)
        effective_chars += ev_chars
        effective_lines += ev_lines
        effective_bytes += ev_bytes
    char_ratio = prd_chars / src_chars if src_chars else 0.0
    line_ratio = prd_lines / src_lines if src_lines else 0.0
    byte_ratio = prd_bytes / src_bytes if src_bytes else 0.0

    length_fail_reasons: list[str] = []
    stage_chars = 0
    stage_lines = 0
    stage_bytes = 0
    stage_char_ratio = 0.0
    stage_line_ratio = 0.0
    stage_byte_ratio = 0.0
    stage_mode = bool(stage_paths)
    if stage_mode:
        for stage_path in stage_paths:
            if not stage_path.exists():
                length_fail_reasons.append(f"stage file not found: {stage_path}")
                continue
            stage_text = read_text(stage_path)
            chars, lines, bytes_len = count_sizes(stage_text)
            stage_chars += chars
            stage_lines += lines
            stage_bytes += bytes_len

        if stage_chars == 0 or stage_lines == 0 or stage_bytes == 0:
            length_fail_reasons.append("stage-aware mode enabled but stage size baseline is zero")
        else:
            stage_char_ratio = effective_chars / stage_chars
            stage_line_ratio = effective_lines / stage_lines
            stage_byte_ratio = effective_bytes / stage_bytes
            if stage_char_ratio < args.min_stage_char_ratio:
                length_fail_reasons.append(
                    "stage_char_ratio "
                    f"{stage_char_ratio:.3f} < min_stage_char_ratio {args.min_stage_char_ratio:.3f}"
                )
            if stage_line_ratio < args.min_stage_line_ratio:
                length_fail_reasons.append(
                    "stage_line_ratio "
                    f"{stage_line_ratio:.3f} < min_stage_line_ratio {args.min_stage_line_ratio:.3f}"
                )
            if char_ratio < args.min_source_char_ratio:
                length_fail_reasons.append(
                    "source_char_ratio "
                    f"{char_ratio:.3f} < min_source_char_ratio {args.min_source_char_ratio:.3f}"
                )
            if line_ratio < args.min_source_line_ratio:
                length_fail_reasons.append(
                    "source_line_ratio "
                    f"{line_ratio:.3f} < min_source_line_ratio {args.min_source_line_ratio:.3f}"
                )
            if byte_ratio < args.min_source_byte_ratio:
                length_fail_reasons.append(
                    "source_byte_ratio "
                    f"{byte_ratio:.3f} < min_source_byte_ratio {args.min_source_byte_ratio:.3f}"
                )
    else:
        if char_ratio < args.min_char_ratio:
            length_fail_reasons.append(
                f"char_ratio {char_ratio:.3f} < min_char_ratio {args.min_char_ratio:.3f}"
            )
        if line_ratio < args.min_line_ratio:
            length_fail_reasons.append(
                f"line_ratio {line_ratio:.3f} < min_line_ratio {args.min_line_ratio:.3f}"
            )
    if args.require_non_shrinking and prd_chars < src_chars:
        length_fail_reasons.append(
            f"prd_chars {prd_chars} < source_chars {src_chars} with require_non_shrinking"
        )

    category_results = [eval_category(source_text, prd_text, cat) for cat in CATEGORIES]
    active_results = [res for res in category_results if res.active]
    category_failures = [res for res in active_results if not res.passed]

    print("== Phase-1 PRD Quality Gate ==")
    print(f"source: {source_path}")
    print(f"prd:    {prd_path}")
    if convergence_evidence_path:
        print(f"convergence_evidence: {convergence_evidence_path}")
    print(
        f"size: source chars={src_chars}, lines={src_lines}, bytes={src_bytes}; "
        f"prd chars={prd_chars}, lines={prd_lines}, bytes={prd_bytes}"
    )
    if evidence_text:
        print(
            "effective_deliverable: "
            f"chars={effective_chars}, lines={effective_lines}, bytes={effective_bytes} "
            f"(includes external evidence chars={ev_chars}, lines={ev_lines}, bytes={ev_bytes})"
        )
    print(
        f"ratios: char_ratio={char_ratio:.3f}, "
        f"line_ratio={line_ratio:.3f}, byte_ratio={byte_ratio:.3f}"
    )
    if stage_mode:
        print(
            "stage_baseline: "
            f"chars={stage_chars}, lines={stage_lines}, bytes={stage_bytes}; "
            f"stage_char_ratio={stage_char_ratio:.3f}, "
            f"stage_line_ratio={stage_line_ratio:.3f}, "
            f"stage_byte_ratio={stage_byte_ratio:.3f}"
        )
    if args.require_non_shrinking:
        print("rule: require_non_shrinking=ON")

    print("\n-- Category Coverage --")
    for res in category_results:
        if not res.active:
            print(f"[SKIP] {res.name}: not active in source")
            continue
        verdict = "PASS" if res.passed else "BLOCKED"
        print(
            f"[{verdict}] {res.name}: "
            f"src_hits={len(res.source_hits)}, prd_hits={len(res.prd_hits)}, required={res.required}"
        )
        print(f"  src: {', '.join(res.source_hits)}")
        print(f"  prd: {', '.join(res.prd_hits) if res.prd_hits else '(none)'}")

    blocked = False
    print("\n-- Gate Verdict --")
    if length_fail_reasons:
        blocked = True
        print("[BLOCKED] length/compression gate failed:")
        for reason in length_fail_reasons:
            print(f"  - {reason}")
    else:
        print("[PASS] length/compression gate")

    if category_failures:
        blocked = True
        print("[BLOCKED] source-detail preservation gate failed:")
        for failure in category_failures:
            print(
                f"  - {failure.name}: required {failure.required}, got {len(failure.prd_hits)}"
            )
    else:
        print("[PASS] source-detail preservation gate")

    if blocked:
        print("\nFINAL: BLOCKED")
        return 2
    print("\nFINAL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
