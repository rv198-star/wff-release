from __future__ import annotations

import argparse
import difflib
import re
from pathlib import Path

from phase1.phase1_version_contract import extract_version_identifiers, normalize_version_identifier

DELTA_SECTION_PATTERN = re.compile(
    r"^##\s+(?:\d+\.\s+)?[^\n]*Analysis Delta Ledger[^\n]*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
NEXT_H2_PATTERN = re.compile(r"^##\s+", flags=re.MULTILINE)
DELTA_ENTRY_PATTERN = re.compile(r"^###\s+Delta\s+\d+\b", flags=re.MULTILINE)

DELTA_REQUIRED_FIELDS = (
    r"-\s*source_evidence:",
    r"-\s*analytical_inference:",
    r"-\s*decision_or_tradeoff:",
    r"-\s*downstream_impact:",
)

DELTA_CATEGORY_PATTERNS = {
    "segment_user": r"(segment|user|persona|客群|用户)",
    "capability_module": r"(capability|module|功能|模块)",
    "metrics_measurement": r"(metric|measurement|指标|评分|口径)",
    "mvp_slice_scope": r"(mvp|slice|scope|in-scope|out-of-scope|切片|范围)",
    "validation": r"(validation|threshold|hypothesis|验证|阈值|假设)",
    "architecture_design": r"(architecture|design|domain|ia|架构|设计|对象|边界)",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def longest_common_block_size(a: str, b: str) -> int:
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return matcher.find_longest_match(0, len(a), 0, len(b)).size


def extract_report_inventory_files(report_text: str, report_path: Path) -> list[Path]:
    files: list[Path] = []
    patterns = (
        re.compile(
            r"^\s*-\s*(stage_[0-9a-z_]+)(?:\s+\S+)?:\s*`?([^`]+)`?\s*$",
            flags=re.IGNORECASE,
        ),
        re.compile(r"^\s*-\s*stage_[0-9a-z_]+:\s*`?([^`]+)`?\s*$", flags=re.IGNORECASE),
    )
    for line in report_text.splitlines():
        value = ""
        for pattern in patterns:
            match = pattern.match(line)
            if not match:
                continue
            value = match.group(match.lastindex or 1).strip()
            break
        if not value or value.startswith("produced") or value.startswith("skipped") or value in {"", "none", "n/a"}:
            continue
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = (report_path.parent / candidate).resolve()
        files.append(candidate)
    return files


def normalize_expected_version(raw: str) -> str:
    return normalize_version_identifier(raw)


def extract_trial_tokens(text: str) -> set[str]:
    return extract_version_identifiers(text)


def extract_delta_section(text: str) -> str | None:
    start_match = DELTA_SECTION_PATTERN.search(text)
    if not start_match:
        return None
    start = start_match.start()
    tail = text[start:]
    next_h2 = NEXT_H2_PATTERN.search(tail, pos=1)
    if next_h2:
        return tail[: next_h2.start()]
    return tail


def split_delta_entries(delta_text: str) -> list[str]:
    positions = [match.start() for match in DELTA_ENTRY_PATTERN.finditer(delta_text)]
    if not positions:
        return []
    entries = []
    for idx, pos in enumerate(positions):
        end = positions[idx + 1] if idx + 1 < len(positions) else len(delta_text)
        entries.append(delta_text[pos:end].strip())
    return entries


def run_prd_assembly_integrity_gate(args: argparse.Namespace) -> int:
    source_path = Path(args.source).resolve()
    prd_path = Path(args.prd).resolve()
    report_path = Path(args.report).resolve() if args.report else None

    source_text = read_text(source_path)
    prd_text = read_text(prd_path)

    print("== Phase-1 PRD Assembly Integrity Gate ==")
    print(f"source: {source_path}")
    print(f"prd:    {prd_path}")
    if report_path:
        print(f"report: {report_path}")

    blocked = False

    source_artifacts_section = re.search(
        r"^##\s+(?:20\.\s+)?[^\n]*Source Artifacts[^\n]*$",
        prd_text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not source_artifacts_section:
        print("[BLOCKED] missing required section: `## Source Artifacts`")
        blocked = True
    else:
        print("[PASS] `## Source Artifacts` section present")

    stage_files: list[Path] = []
    if args.stage:
        for stage in args.stage:
            stage_path = Path(stage)
            if not stage_path.is_absolute() and report_path:
                stage_path = (report_path.parent / stage_path).resolve()
            elif not stage_path.is_absolute():
                stage_path = stage_path.resolve()
            stage_files.append(stage_path)
    elif report_path:
        stage_files = extract_report_inventory_files(read_text(report_path), report_path)

    if not stage_files:
        print("[BLOCKED] no stage files provided/resolved for integrity verification")
        blocked = True

    for stage_path in stage_files:
        if not stage_path.exists():
            print(f"[BLOCKED] stage artifact missing: {stage_path}")
            blocked = True
            continue
        base = stage_path.name
        if re.search(re.escape(base), prd_text, flags=re.IGNORECASE):
            print(f"[PASS] stage artifact referenced in PRD: {base}")
        else:
            print(f"[BLOCKED] stage artifact not referenced in PRD: {base}")
            blocked = True

    if source_text.strip() and source_text.strip() in prd_text:
        print("[BLOCKED] source text appears as a full raw append in PRD")
        blocked = True
    else:
        print("[PASS] no full source raw append detected")

    common_size = longest_common_block_size(source_text, prd_text)
    ratio = common_size / len(source_text) if source_text else 0.0
    print(f"longest_common_block: chars={common_size}, source_ratio={ratio:.3f}")
    if common_size > args.max_copy_block_chars and ratio > args.max_copy_block_ratio:
        print(
            "[BLOCKED] longest common block exceeds thresholds "
            f"(chars>{args.max_copy_block_chars} and ratio>{args.max_copy_block_ratio:.3f})"
        )
        blocked = True
    else:
        print("[PASS] longest common block within anti-mirror thresholds")

    banned_patterns = [
        r"^##\s+.*Source Appendix",
        r"^##\s+.*原始输入全文",
        r"^##\s+.*附录.*原文",
    ]
    banned_hits = 0
    for pattern in banned_patterns:
        if re.search(pattern, prd_text, flags=re.IGNORECASE | re.MULTILINE):
            print(f"[BLOCKED] banned appendix pattern found: `{pattern}`")
            blocked = True
            banned_hits += 1
    if banned_hits == 0:
        print("[PASS] no banned raw-source appendix headings found")

    if blocked:
        print("FINAL: BLOCKED")
        return 2
    print("FINAL: PASS")
    return 0


def run_prd_analysis_delta_gate(args: argparse.Namespace) -> int:
    prd_path = Path(args.prd)
    text = prd_path.read_text(encoding="utf-8")
    delta_path = Path(args.delta_ledger).resolve() if args.delta_ledger else None
    delta_text = delta_path.read_text(encoding="utf-8") if delta_path and delta_path.exists() else ""

    print("== Phase-1 PRD Analysis Delta Gate ==")
    print(f"prd: {prd_path}")
    if delta_path:
        print(f"delta_ledger: {delta_path}")

    delta_section = extract_delta_section(text)
    delta_source = "prd"
    if delta_section is None and delta_text:
        delta_section = extract_delta_section(delta_text)
        if delta_section is not None:
            delta_source = "external delta ledger"
    if delta_section is None:
        print("[BLOCKED] Missing required section: `## Analysis Delta Ledger` in PRD or external delta ledger")
        print("FINAL: BLOCKED")
        return 2
    print(f"[PASS] Analysis Delta Ledger resolved from: {delta_source}")

    entries = split_delta_entries(delta_section)
    print(f"delta_entries_found: {len(entries)}")
    if len(entries) < args.min_deltas:
        print(f"[BLOCKED] delta entry count {len(entries)} < min_deltas {args.min_deltas}")
        print("FINAL: BLOCKED")
        return 2

    malformed = []
    for idx, entry in enumerate(entries, start=1):
        missing = []
        for field_pattern in DELTA_REQUIRED_FIELDS:
            if not re.search(field_pattern, entry, flags=re.IGNORECASE):
                missing.append(field_pattern)
        if missing:
            malformed.append((idx, missing))
    if malformed:
        print("[BLOCKED] Some delta entries are missing required fields:")
        for idx, missing in malformed:
            print(f"  - Delta {idx}: missing {', '.join(missing)}")
        print("FINAL: BLOCKED")
        return 2

    category_hits = {name: False for name in DELTA_CATEGORY_PATTERNS}
    for entry in entries:
        for name, pattern in DELTA_CATEGORY_PATTERNS.items():
            if re.search(pattern, entry, flags=re.IGNORECASE):
                category_hits[name] = True

    covered = [name for name, hit in category_hits.items() if hit]
    print(f"category_coverage: {len(covered)}/{len(DELTA_CATEGORY_PATTERNS)}")
    print(f"covered_categories: {', '.join(covered)}")
    if len(covered) < args.min_category_coverage:
        print(
            "[BLOCKED] insufficient category coverage for analytical deltas "
            f"({len(covered)} < {args.min_category_coverage})"
        )
        print("FINAL: BLOCKED")
        return 2

    print("[PASS] analysis delta ledger structure and coverage")
    print("FINAL: PASS")
    return 0


def run_artifact_consistency_gate(args: argparse.Namespace) -> int:
    prd_path = Path(args.prd).resolve()
    report_path = Path(args.report).resolve()

    prd_text = read_text(prd_path)
    report_text = read_text(report_path)

    expected_version = None
    if args.expected_version:
        expected_version = normalize_expected_version(args.expected_version)

    print("== Phase-1 Artifact Consistency Gate ==")
    print(f"prd: {prd_path}")
    print(f"report: {report_path}")

    blocked = False

    prd_tokens = extract_trial_tokens(prd_text)
    report_tokens = extract_trial_tokens(report_text)
    if not prd_tokens:
        print("[BLOCKED] no version identifier found in PRD")
        blocked = True
    if not report_tokens:
        print("[BLOCKED] no version identifier found in execution report")
        blocked = True

    derived_expected = expected_version
    if derived_expected is None and prd_tokens:
        if len(prd_tokens) == 1:
            derived_expected = next(iter(prd_tokens))
        else:
            print(f"[BLOCKED] PRD has multiple version identifiers: {sorted(prd_tokens)}")
            blocked = True

    if derived_expected:
        print(f"expected_version: {derived_expected}")
        if derived_expected not in prd_tokens:
            print(f"[BLOCKED] PRD does not contain expected version `{derived_expected}`")
            blocked = True
        else:
            print("[PASS] PRD version token matches expected version")
        if derived_expected not in report_tokens:
            print(f"[BLOCKED] execution report does not contain expected version `{derived_expected}`")
            blocked = True
        else:
            print("[PASS] report version token matches expected version")

    stage_files: list[Path] = []
    if args.stage:
        for stage in args.stage:
            path = Path(stage)
            if not path.is_absolute():
                path = (report_path.parent / path).resolve()
            stage_files.append(path)
    else:
        stage_files = extract_report_inventory_files(report_text, report_path)

    if not stage_files and args.require_stage_files:
        print("[BLOCKED] no stage files resolved from args/report inventory")
        blocked = True

    if stage_files:
        print(f"resolved_stage_files: {len(stage_files)}")
    for stage_path in stage_files:
        if not stage_path.exists():
            print(f"[BLOCKED] stage file not found: {stage_path}")
            blocked = True
            continue
        print(f"[PASS] stage file exists: {stage_path.name}")
        stage_text = read_text(stage_path)
        stage_tokens = extract_trial_tokens(stage_text)
        if not stage_tokens:
            print(f"[BLOCKED] stage file has no version identifier: {stage_path.name}")
            blocked = True
            continue
        if len(stage_tokens) > 1:
            print(f"[BLOCKED] stage file has multiple version identifiers: {stage_path.name} -> {sorted(stage_tokens)}")
            blocked = True
            continue
        stage_token = next(iter(stage_tokens))
        if derived_expected and stage_token != derived_expected:
            print(
                f"[BLOCKED] stage version mismatch: {stage_path.name} "
                f"has `{stage_token}` expected `{derived_expected}`"
            )
            blocked = True
        else:
            print(f"[PASS] stage version identifier: {stage_path.name} -> {stage_token}")

    if blocked:
        print("FINAL: BLOCKED")
        return 2
    print("FINAL: PASS")
    return 0
