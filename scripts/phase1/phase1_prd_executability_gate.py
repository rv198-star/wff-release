#!/usr/bin/env python3
"""
Phase-1 PRD executability gate.

This gate complements preservation/delta gates by checking whether the PRD is
usable for downstream execution rather than only structurally complete.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import re
import sys
from pathlib import Path

from common.gwt_format_checker import analyze_gwt_block, count_complete_rows, first_table_with_headers

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


def extract_h3_block(text: str, title_pattern: str) -> str | None:
    match = re.search(
        rf"^###\s+[^\n]*?(?:{title_pattern})[^\n]*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return None
    start = match.end()
    next_heading = re.search(r"^##\s+|^###\s+", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def count_pattern_hits(text: str, patterns: list[str]) -> int:
    hits = 0
    normalized = canonicalize_bilingual_text(text)
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) or re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE | re.MULTILINE,
        ):
            hits += 1
    return hits


def count_table_rows_with_headers(text: str, required_headers: set[str]) -> int:
    return count_complete_rows(first_table_with_headers(text, required_headers), required_headers)


def count_nonempty_content_lines(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-1 PRD executability gate")
    parser.add_argument("--prd", required=True)
    parser.add_argument(
        "--profile",
        default="review-bound-starter-pack",
        choices=("review-bound-starter-pack", "implementation-ready-prd"),
    )
    parser.add_argument("--min-review-process-signals", type=int, default=6)
    parser.add_argument("--min-review-ia-signals", type=int, default=6)
    parser.add_argument("--min-review-flow-signals", type=int, default=6)
    parser.add_argument("--min-implementation-main-steps", type=int, default=8)
    parser.add_argument("--min-implementation-exceptions", type=int, default=3)
    parser.add_argument("--min-implementation-transitions", type=int, default=8)
    parser.add_argument("--min-implementation-ac", type=int, default=10)
    parser.add_argument("--min-implementation-epics", type=int, default=3)
    parser.add_argument("--min-invest-rows", type=int, default=5)
    parser.add_argument("--min-boundary-coverage-rows", type=int, default=10)
    parser.add_argument("--min-reasoning-units", type=int, default=8)
    parser.add_argument("--min-competitive-lines", type=int, default=10)
    parser.add_argument("--min-pricing-lines", type=int, default=8)
    parser.add_argument("--min-invest-note-coverage", type=float, default=0.6)
    args = parser.parse_args()

    prd_path = Path(args.prd)
    text = prd_path.read_text(encoding="utf-8")

    print("== Phase-1 PRD Executability Gate ==")
    print(f"prd: {prd_path}")
    print(f"profile: {args.profile}")

    blocked = False

    required_h2 = {
        "requirements_structure": r"(?:8\.\s+)?Requirements Structure",
        "strategic_context": r"(?:5\.\s+)?Strategic Context",
        "ia_direction": r"(?:11\.\s+)?Information Architecture Direction",
        "mvp_scope": r"(?:12\.\s+)?MVP Definition & Scope",
        "validation_strategy": r"(?:13\.\s+)?Validation Strategy(?:\s*&\s*Current Conclusion)?",
        "stories_requirements": r"(?:14\.\s+)?User Stories, Use Cases, and Requirements",
    }
    h2_blocks: dict[str, str] = {}
    for name, pattern in required_h2.items():
        block = extract_h2_block(text, pattern)
        if block is None:
            print(f"[BLOCKED] missing required section: `{pattern}`")
            blocked = True
            continue
        print(f"[PASS] section present: {name}")
        h2_blocks[name] = block

    reasoning_unit_count = len(
        re.findall(
            r"^#{3,6}\s+(?:Reasoning Unit|推理单元)\s+\d+[:：]",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    if reasoning_unit_count >= args.min_reasoning_units:
        print(f"[PASS] PRD reasoning units: {reasoning_unit_count} >= {args.min_reasoning_units}")
    else:
        print(f"[BLOCKED] PRD reasoning units: {reasoning_unit_count} < {args.min_reasoning_units}")
        blocked = True

    if "requirements_structure" in h2_blocks:
        process_hits = count_pattern_hits(
            h2_blocks["requirements_structure"],
            [
                r"\bActivity\b",
                r"\bStep\s*[1-9]\b",
                r"workflow|流程",
                r"persona|角色|jtbd|job to be done",
                r"scenario|场景|handoff|交接",
                r"configure|初始化|配置|entry|入口",
                r"baseline|基线|closure|闭环",
                r"finding|缺口|business object|业务对象",
                r"task|任务",
                r"review|复盘",
                r"state|状态",
            ],
        )
        if process_hits >= args.min_review_process_signals:
            print(
                f"[PASS] business process analysis signals: {process_hits} "
                f">= {args.min_review_process_signals}"
            )
        else:
            print(
                f"[BLOCKED] business process analysis signals: {process_hits} "
                f"< {args.min_review_process_signals}"
            )
            blocked = True

    if "ia_direction" in h2_blocks:
        ia_hits = count_pattern_hits(
            h2_blocks["ia_direction"],
            [
                r"organization|组织",
                r"labeling|标签|命名",
                r"navigation|导航",
                r"screen|页面",
                r"module|模块",
                r"dashboard|仪表板|overview|screen/object matrix",
                r"findings?|发现|required information objects",
                r"tasks?|任务|entry conditions",
                r"assets?|资产|exit actions|dependency|traceability",
            ],
        )
        if ia_hits >= args.min_review_ia_signals:
            print(f"[PASS] IA depth signals: {ia_hits} >= {args.min_review_ia_signals}")
        else:
            print(f"[BLOCKED] IA depth signals: {ia_hits} < {args.min_review_ia_signals}")
            blocked = True

    if "mvp_scope" in h2_blocks:
        flow_hits = count_pattern_hits(
            h2_blocks["mvp_scope"],
            [
                r"complete experience loop|完整体验闭环|complete loop",
                r"minimum viable experience loop|最小可用体验闭环|minimum loop",
                r"\bStep\s*[1-9]\b|步骤\s*[1-9]",
                r"configure|初始化|配置",
                r"baseline|基线",
                r"recommendation|建议|treatment|治疗|diagnostic|检查|discharge|离院|出院|follow-?up|复诊",
                r"execute|执行",
                r"review|复盘",
                r"in-scope|in scope|in-scope|范围内",
                r"out-of-scope|out of scope|范围外|非目标",
            ],
        )
        has_scope_boundary = bool(
            re.search(r"in-scope|in scope|范围内", h2_blocks["mvp_scope"], flags=re.IGNORECASE)
            and re.search(
                r"out-of-scope|out of scope|范围外|非目标",
                h2_blocks["mvp_scope"],
                flags=re.IGNORECASE,
            )
        )
        if flow_hits >= args.min_review_flow_signals and has_scope_boundary:
            print(
                f"[PASS] operation flow signals: {flow_hits} >= {args.min_review_flow_signals}, "
                "scope boundary present"
            )
        else:
            print(
                f"[BLOCKED] operation flow signals or scope boundary insufficient: "
                f"hits={flow_hits}, has_scope_boundary={has_scope_boundary}"
            )
            blocked = True

    if "strategic_context" in h2_blocks:
        competitive_block = extract_h3_block(
            h2_blocks["strategic_context"],
            r"Competitive Landscape Summary|竞争格局|竞品",
        )
        if competitive_block is None:
            print("[BLOCKED] strategic context missing `Competitive Landscape Summary`")
            blocked = True
        else:
            competitive_lines = count_nonempty_content_lines(competitive_block)
            if competitive_lines >= args.min_competitive_lines:
                print(
                    f"[PASS] competitive landscape section depth: {competitive_lines} "
                    f">= {args.min_competitive_lines}"
                )
            else:
                print(
                    f"[WARN] competitive landscape section is thin: {competitive_lines} "
                    f"< {args.min_competitive_lines}"
                )

    if "validation_strategy" in h2_blocks:
        pricing_block = extract_h3_block(
            h2_blocks["validation_strategy"],
            r"Pricing Validation Design|定价验证",
        )
        if pricing_block is None:
            print("[BLOCKED] validation strategy missing `Pricing Validation Design`")
            blocked = True
        else:
            pricing_lines = count_nonempty_content_lines(pricing_block)
            pricing_signal_hits = count_pattern_hits(
                pricing_block,
                [
                    r"pricing|price|付费|报价|willingness-to-pay|预算",
                    r"experiment|test|pilot|interview|prototype|访谈|实验|试点",
                    r"threshold|pass|fail|signal|判定|阈值",
                ],
            )
            if pricing_lines >= args.min_pricing_lines and pricing_signal_hits >= 3:
                print(
                    f"[PASS] pricing validation section depth/signals: lines={pricing_lines}, "
                    f"signals={pricing_signal_hits}"
                )
            else:
                print(
                    f"[WARN] pricing validation section is thin: lines={pricing_lines}, "
                    f"signals={pricing_signal_hits}"
                )

    if "stories_requirements" in h2_blocks:
        req_hits = count_pattern_hits(
            h2_blocks["stories_requirements"],
            [
                r"user story|用户故事",
                r"use case|用例",
                r"epic|史诗",
                r"requirement|需求",
                r"translation|映射|转译",
                r"supporting",
            ],
        )
        payload_hits = count_pattern_hits(
            h2_blocks["stories_requirements"],
            [
                r"Module Interface Payload Contract|Recommendation Payload Contract|payload contract",
                r"structured payload|结构化字段|quality diagnosis",
                r"target_asset_id|priority|owner_hint|blocked_reason|extension_context",
                r"source_reference|source_tag|stage_placeholder|outcome event|conversion event|multi-entry|cross-device|extension seam|deferred seam",
                r"Requirement Trace Matrix|story/use case",
                r"Story Quality Gate|INVEST",
                r"Epic Decomposition|epic_id",
            ],
        )
        if req_hits >= 3 and payload_hits >= 4:
            print(
                f"[PASS] requirement translation signals: base={req_hits} >= 3, "
                f"payload/trace={payload_hits} >= 4"
            )
        else:
            print(
                "[BLOCKED] requirement translation signals insufficient: "
                f"base={req_hits} (need >=3), payload/trace={payload_hits} (need >=4)"
            )
            blocked = True

        requirement_class_hits = count_pattern_hits(
            h2_blocks["stories_requirements"],
            [
                r"functional_requirement",
                r"governance_constraint",
                r"quality_or_compliance_constraint",
            ],
        )
        if requirement_class_hits >= 2:
            print(f"[PASS] requirement classification signals: {requirement_class_hits} >= 2")
        else:
            print(
                "[WARN] requirement classification signals are weak: "
                "distinguish functional requirements from governance/compliance constraints"
            )

    if args.profile == "implementation-ready-prd":
        impl_sections = {
            "epic_decomposition": r"Epic Decomposition|史诗分解",
            "story_quality_gate": r"Story Quality Gate|INVEST",
            "process_decomposition": r"Business Process Decomposition|业务过程分解",
            "exception_flows": r"Exception and Failure Flows|异常流程|失败流程",
            "ia_spec_matrix": r"IA Spec Matrix|信息架构规格矩阵|IA 规格矩阵",
            "operational_flow_spec": r"Operational Flow Specification|操作流程规格",
            "state_machine": r"State Machine and Transition Rules|状态机",
            "acceptance_criteria": r"Acceptance Criteria|验收标准",
        }
        impl_blocks: dict[str, str] = {}
        for name, pattern in impl_sections.items():
            block = extract_h3_block(text, pattern)
            if block is None:
                print(f"[BLOCKED] implementation-ready section missing: `{pattern}`")
                blocked = True
                continue
            print(f"[PASS] implementation-ready section present: {name}")
            impl_blocks[name] = block

        if "operational_flow_spec" in impl_blocks:
            step_count = len(
                re.findall(
                    r"\bStep\s*[1-9]\b|步骤\s*[1-9]|^\s*[0-9]+\.\s+",
                    impl_blocks["operational_flow_spec"],
                    flags=re.IGNORECASE | re.MULTILINE,
                )
            )
            if step_count >= args.min_implementation_main_steps:
                print(
                    f"[PASS] implementation main-flow steps: {step_count} "
                    f">= {args.min_implementation_main_steps}"
                )
            else:
                print(
                    f"[BLOCKED] implementation main-flow steps: {step_count} "
                    f"< {args.min_implementation_main_steps}"
                )
                blocked = True

        if "exception_flows" in impl_blocks:
            exception_count = len(
                re.findall(
                    r"Exception\s*[0-9]+|异常\s*[0-9]+|失败场景\s*[0-9]+",
                    impl_blocks["exception_flows"],
                    flags=re.IGNORECASE,
                )
            )
            if exception_count >= args.min_implementation_exceptions:
                print(
                    f"[PASS] implementation exception-flow count: {exception_count} "
                    f">= {args.min_implementation_exceptions}"
                )
            else:
                print(
                    f"[BLOCKED] implementation exception-flow count: {exception_count} "
                    f"< {args.min_implementation_exceptions}"
                )
                blocked = True

        if "state_machine" in impl_blocks:
            transition_count = len(re.findall(r"->|→", impl_blocks["state_machine"]))
            if transition_count >= args.min_implementation_transitions:
                print(
                    f"[PASS] implementation state transitions: {transition_count} "
                    f">= {args.min_implementation_transitions}"
                )
            else:
                print(
                    f"[BLOCKED] implementation state transitions: {transition_count} "
                    f"< {args.min_implementation_transitions}"
                )
                blocked = True

        if "acceptance_criteria" in impl_blocks:
            ac_count = len(
                re.findall(r"\bAC[-_ ]?[0-9]+\b", impl_blocks["acceptance_criteria"], flags=re.IGNORECASE)
            )
            if ac_count >= args.min_implementation_ac:
                print(
                    f"[PASS] implementation acceptance criteria: {ac_count} "
                    f">= {args.min_implementation_ac}"
                )
            else:
                print(
                    f"[BLOCKED] implementation acceptance criteria: {ac_count} "
                    f"< {args.min_implementation_ac}"
                )
                blocked = True

            gwt_analysis = analyze_gwt_block(impl_blocks["acceptance_criteria"], id_headers=("ac_id",))
            gwt_rows = max(int(gwt_analysis["gwt_rows"]), int(gwt_analysis["keyword_rows"]))
            if gwt_rows >= args.min_implementation_ac:
                print(
                    f"[PASS] Given/When/Then acceptance rows: {gwt_rows} "
                    f">= {args.min_implementation_ac}"
                )
            else:
                print(
                    f"[BLOCKED] Given/When/Then acceptance rows: {gwt_rows} "
                    f"< {args.min_implementation_ac}"
                )
                blocked = True

            boundary_rows = int(gwt_analysis["boundary_rows"])
            if boundary_rows >= args.min_boundary_coverage_rows:
                print(
                    f"[PASS] acceptance boundary coverage rows: {boundary_rows} "
                    f">= {args.min_boundary_coverage_rows}"
                )
            else:
                print(
                    f"[BLOCKED] acceptance boundary coverage rows: {boundary_rows} "
                    f"< {args.min_boundary_coverage_rows}"
                )
                blocked = True

            ac_table = first_table_with_headers(
                impl_blocks["acceptance_criteria"],
                {"ac_id", "given", "when", "then"},
            )
            if ac_table is not None:
                headers = set(ac_table["headers"])
                if "ac_tier" in headers:
                    anchor_rows = sum(
                        1 for row in ac_table["rows"] if str(row.get("ac_tier", "")).strip().lower() == "anchor"
                    )
                    if anchor_rows >= 3:
                        print(f"[PASS] anchor AC rows: {anchor_rows} >= 3")
                    else:
                        print(
                            f"[WARN] anchor AC rows are thin: {anchor_rows}; "
                            "mark critical-path/high-risk ACs explicitly when claiming implementation-ready depth"
                        )
                else:
                    print("[WARN] acceptance criteria table missing `ac_tier`; anchor/supporting split is recommended")

                if "expected_outcome" in headers:
                    expected_outcome_rows = sum(
                        1 for row in ac_table["rows"] if str(row.get("expected_outcome", "")).strip()
                    )
                    if expected_outcome_rows >= max(3, min(ac_count, 5)):
                        print(
                            f"[PASS] AC expected outcome rows: {expected_outcome_rows} "
                            f">= {max(3, min(ac_count, 5))}"
                        )
                    else:
                        print(
                            f"[WARN] AC expected outcome rows are thin: {expected_outcome_rows}; "
                            "critical ACs should expose an observable success signal"
                        )
                else:
                    print("[WARN] acceptance criteria table missing `expected_outcome` column")

            boundary_variety = int(gwt_analysis["boundary_variety"])
            if boundary_variety:
                if boundary_variety >= 3:
                    print(f"[PASS] boundary-condition variety: {boundary_variety} >= 3")
                else:
                    print(
                        f"[WARN] boundary-condition variety is low: {boundary_variety}; "
                        "permission / missing-input / invalid-state / threshold / recovery edges should be visible where relevant"
                    )

        if "ia_spec_matrix" in impl_blocks:
            ia_matrix_rows = len(
                [
                    line
                    for line in impl_blocks["ia_spec_matrix"].splitlines()
                    if "|" in line and not re.fullmatch(r"\s*[-|:\s]+\s*", line)
                ]
            )
            if ia_matrix_rows >= 8:
                print(f"[PASS] implementation IA spec matrix rows: {ia_matrix_rows} >= 8")
            else:
                print(f"[BLOCKED] implementation IA spec matrix rows: {ia_matrix_rows} < 8")
                blocked = True

        if "epic_decomposition" in impl_blocks:
            epic_rows = count_table_rows_with_headers(
                impl_blocks["epic_decomposition"],
                {"epic_id", "epic_name", "user_value", "included_user_stories_or_use_cases"},
            )
            if epic_rows >= args.min_implementation_epics:
                print(f"[PASS] epic decomposition rows: {epic_rows} >= {args.min_implementation_epics}")
            else:
                print(f"[BLOCKED] epic decomposition rows: {epic_rows} < {args.min_implementation_epics}")
                blocked = True

        if "story_quality_gate" in impl_blocks:
            invest_rows = count_table_rows_with_headers(
                impl_blocks["story_quality_gate"],
                {
                    "story_or_use_case",
                    "epic_id",
                    "independent",
                    "negotiable",
                    "valuable",
                    "estimable",
                    "small",
                    "testable",
                },
            )
            if invest_rows >= args.min_invest_rows:
                print(f"[PASS] INVEST evaluation rows: {invest_rows} >= {args.min_invest_rows}")
            else:
                print(f"[BLOCKED] INVEST evaluation rows: {invest_rows} < {args.min_invest_rows}")
                blocked = True

            invest_table = first_table_with_headers(
                impl_blocks["story_quality_gate"],
                {
                    "story_or_use_case",
                    "epic_id",
                    "independent",
                    "negotiable",
                    "valuable",
                    "estimable",
                    "small",
                    "testable",
                },
            )
            if invest_table is not None:
                headers = set(invest_table["headers"])
                note_header = "risk_or_note" if "risk_or_note" in headers else "gap_note" if "gap_note" in headers else ""
                if note_header:
                    noted_rows = sum(
                        1 for row in invest_table["rows"] if str(row.get(note_header, "")).strip()
                    )
                    min_note_rows = max(1, round(invest_rows * args.min_invest_note_coverage))
                    if noted_rows >= min_note_rows:
                        print(f"[PASS] INVEST note rows: {noted_rows} >= {min_note_rows}")
                    else:
                        print(
                            f"[WARN] INVEST note rows are thin: {noted_rows}; "
                            "record real risk/gap notes instead of silent all-pass scoring"
                        )
                else:
                    print("[WARN] INVEST table missing `risk_or_note`/`gap_note` column")

    if blocked:
        print("FINAL: BLOCKED")
        return 2
    print("FINAL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
