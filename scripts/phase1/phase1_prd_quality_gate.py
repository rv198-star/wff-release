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
from typing import Iterable


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


CATEGORIES: tuple[CategoryDef, ...] = (
    CategoryDef(
        name="segment_landscape",
        ratio_required=0.6,
        min_required=2,
        patterns=(
            PatternDef("b2b", r"\bB2B\b"),
            PatternDef("consumer_brand", r"消费品牌"),
            PatternDef("ecommerce", r"电商"),
            PatternDef("creator", r"内容创作者"),
            PatternDef("local_service", r"本地服务"),
        ),
    ),
    CategoryDef(
        name="capability_clusters",
        ratio_required=0.6,
        min_required=2,
        patterns=(
            PatternDef("core_capability", r"核心能力|core capability"),
            PatternDef("key_feature", r"关键功能|key feature"),
            PatternDef("competitor_analysis", r"竞争对手监控分析|竞品"),
            PatternDef("business_module", r"业务模块|business module|系统功能|system function|功能集群|capability cluster"),
            PatternDef("automation_execution", r"自动化优化执行|自动化"),
        ),
    ),
    CategoryDef(
        name="metric_definitions",
        ratio_required=0.75,
        min_required=2,
        patterns=(
            PatternDef("key_metric", r"关键指标|KPI|key metric|度量|measurement|measure"),
            PatternDef("quality_score", r"提及内容质量评分|质量评分"),
            PatternDef("roi", r"\bROI\b|转化效果"),
            PatternDef("coverage_rate", r"重点问题覆盖率"),
        ),
    ),
    CategoryDef(
        name="mvp_scope_boundaries",
        ratio_required=0.7,
        min_required=2,
        patterns=(
            PatternDef("mvp_in_scope", r"MVP in-scope|MVP In-scope|MVP in scope"),
            PatternDef("mvp_out_scope", r"MVP out-of-scope|MVP Out-of-scope|out-of-scope"),
            PatternDef("phase2_candidates", r"Phase-2 candidates|Phase-2"),
            PatternDef("non_goals", r"non-goals|non-goals|非目标"),
        ),
    ),
    CategoryDef(
        name="validation_thresholds",
        ratio_required=0.5,
        min_required=2,
        patterns=(
            PatternDef("target_sections", r"Target\s*[1-9]"),
            PatternDef("at_least_n_people", r"至少\s*[0-9]+\s*位"),
            PatternDef("percent_70", r"70%"),
            PatternDef("percent_50", r"50%"),
            PatternDef("signal_threshold", r"signal\s*/\s*threshold|threshold|判定信号"),
        ),
    ),
    CategoryDef(
        name="priority_groups",
        ratio_required=1.0,
        min_required=2,
        patterns=(
            PatternDef("p0", r"\bP0\b"),
            PatternDef("p1", r"\bP1\b"),
            PatternDef("p2", r"\bP2\b"),
        ),
    ),
    CategoryDef(
        name="workflow_steps",
        ratio_required=0.6,
        min_required=2,
        patterns=(
            PatternDef("step_1", r"Step\s*1|初始化配置"),
            PatternDef("step_2", r"Step\s*2|步骤\s*2|流程|workflow|process"),
            PatternDef("step_3", r"Step\s*3|步骤\s*3|操作|operation"),
            PatternDef("step_4", r"Step\s*4|步骤\s*4|执行|execute|run"),
            PatternDef("step_5", r"Step\s*5|步骤\s*5|step"),
        ),
    ),
    CategoryDef(
        name="page_or_module_hints",
        ratio_required=0.6,
        min_required=2,
        patterns=(
            PatternDef("dashboard", r"首页仪表板|dashboard"),
            PatternDef("list_page", r"列表页|list page"),
            PatternDef("detail_page", r"详情页|detail page"),
            PatternDef("management_page", r"管理页|management page|设置页|settings page"),
            PatternDef("module_wording", r"Module\s*[A-Z]|模块"),
        ),
    ),
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
