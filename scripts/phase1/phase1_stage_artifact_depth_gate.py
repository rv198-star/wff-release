#!/usr/bin/env python3
"""
Phase-1 stage artifact depth gate.

Purpose:
- block extremely thin Stage-01/02a/02b/03/04 artifacts
- require minimum stage-to-source depth ratios
- require minimum stage structure signals before PRD assembly
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from common.script_data_assets import load_script_json_asset
from phase1.phase1_version_contract import extract_version_identifiers


@dataclass(frozen=True)
class StageRule:
    key: str
    min_source_char_ratio: float
    min_source_line_ratio: float
    min_chars_abs: int
    min_lines_abs: int
    required_signals: tuple[tuple[str, str], ...]


WFF_SCRIPT_DATA_ASSETS = ("scripts/phase1/data/stage-artifact-depth-rules.json",)
_STAGE_ARTIFACT_DEPTH_RULES = load_script_json_asset(__file__, "stage-artifact-depth-rules.json")


def _load_stage_rules(data: dict[str, object]) -> dict[str, StageRule]:
    rules: dict[str, StageRule] = {}
    for key, raw_rule in data.items():
        rule = raw_rule if isinstance(raw_rule, dict) else {}
        rules[str(key)] = StageRule(
            key=str(rule.get("key", key)),
            min_source_char_ratio=float(rule.get("min_source_char_ratio", 0)),
            min_source_line_ratio=float(rule.get("min_source_line_ratio", 0)),
            min_chars_abs=int(rule.get("min_chars_abs", 0)),
            min_lines_abs=int(rule.get("min_lines_abs", 0)),
            required_signals=tuple(
                (str(signal[0]), str(signal[1]))
                for signal in rule.get("required_signals", [])
                if isinstance(signal, (list, tuple)) and len(signal) >= 2
            ),
        )
    return rules


STAGE_RULES = _load_stage_rules(_STAGE_ARTIFACT_DEPTH_RULES["stage_rules"])
MIN_REASONING_UNITS = {
    str(key): int(value)
    for key, value in _STAGE_ARTIFACT_DEPTH_RULES["min_reasoning_units"].items()
}
REASONING_FIELD_PATTERNS = tuple(
    (str(pattern[0]), str(pattern[1]), float(pattern[2]))
    for pattern in _STAGE_ARTIFACT_DEPTH_RULES["reasoning_field_patterns"]
)
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def count_chars_lines(text: str) -> tuple[int, int]:
    chars = len(text)
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    return chars, lines


def infer_stage_key(path: Path) -> str | None:
    name = path.name.lower()
    if "stage-02b" in name:
        return "stage_02b"
    if "stage-02a" in name:
        return "stage_02a"
    if "stage-01" in name:
        return "stage_01"
    if "stage-03" in name:
        return "stage_03"
    if "stage-04" in name:
        return "stage_04"
    return None


def block_after_anchor(text: str, anchor_pattern: str) -> str:
    match = re.search(anchor_pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    tail = text[match.end() :]
    next_top_level = re.search(r"^-\s+[^:\n]{1,160}:\s*$|^##\s+", tail, flags=re.MULTILINE)
    end = next_top_level.start() if next_top_level else len(tail)
    return tail[:end]


def extract_version_tokens(text: str) -> set[str]:
    return extract_version_identifiers(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-1 stage artifact depth gate")
    parser.add_argument("--source", required=True)
    parser.add_argument("--stage", action="append", default=[])
    parser.add_argument("--min-total-stage-char-ratio", type=float, default=1.10)
    parser.add_argument("--min-total-stage-line-ratio", type=float, default=1.00)
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    stage_paths = [Path(item).resolve() for item in args.stage]

    print("== Phase-1 Stage Artifact Depth Gate ==")
    print(f"source: {source_path}")
    print(f"stage_files: {len(stage_paths)}")

    blocked = False
    if not stage_paths:
        print("[BLOCKED] no stage files provided")
        print("FINAL: BLOCKED")
        return 2

    source_text = read_text(source_path)
    source_chars, source_lines = count_chars_lines(source_text)
    print(f"source_size: chars={source_chars}, lines={source_lines}")

    stage_by_key: dict[str, Path] = {}
    for stage_path in stage_paths:
        key = infer_stage_key(stage_path)
        if key is None:
            print(f"[BLOCKED] cannot infer stage type from file name: {stage_path.name}")
            blocked = True
            continue
        if key in stage_by_key:
            print(
                f"[BLOCKED] duplicated stage artifact for `{key}`: "
                f"{stage_by_key[key].name} and {stage_path.name}"
            )
            blocked = True
            continue
        stage_by_key[key] = stage_path

    for key in STAGE_RULES:
        if key not in stage_by_key:
            print(f"[BLOCKED] missing required stage artifact: {key}")
            blocked = True

    total_stage_chars = 0
    total_stage_lines = 0

    for key, rule in STAGE_RULES.items():
        stage_path = stage_by_key.get(key)
        if stage_path is None:
            continue
        if not stage_path.exists():
            print(f"[BLOCKED] stage artifact not found: {stage_path}")
            blocked = True
            continue

        stage_text = read_text(stage_path)
        stage_chars, stage_lines = count_chars_lines(stage_text)
        total_stage_chars += stage_chars
        total_stage_lines += stage_lines
        char_ratio = stage_chars / source_chars if source_chars else 0.0
        line_ratio = stage_lines / source_lines if source_lines else 0.0
        min_chars = max(rule.min_chars_abs, int(source_chars * rule.min_source_char_ratio))
        min_lines = max(rule.min_lines_abs, int(source_lines * rule.min_source_line_ratio))

        print(f"\n-- {key} / {stage_path.name} --")
        print(
            f"size: chars={stage_chars}, lines={stage_lines}; "
            f"source_ratios: char={char_ratio:.3f}, line={line_ratio:.3f}"
        )

        if stage_chars < min_chars:
            print(f"[BLOCKED] chars {stage_chars} < min_chars {min_chars}")
            blocked = True
        else:
            print(f"[PASS] chars {stage_chars} >= min_chars {min_chars}")
        if stage_lines < min_lines:
            print(f"[BLOCKED] lines {stage_lines} < min_lines {min_lines}")
            blocked = True
        else:
            print(f"[PASS] lines {stage_lines} >= min_lines {min_lines}")

        trial_tokens = extract_version_tokens(stage_text)
        if len(trial_tokens) != 1:
            print(
                f"[BLOCKED] expected exactly one version identifier in stage file, "
                f"found: {sorted(trial_tokens)}"
            )
            blocked = True
        else:
            token = next(iter(trial_tokens))
            print(f"[PASS] version identifier present: {token}")

        signal_hits = 0
        for label, pattern in rule.required_signals:
            if re.search(pattern, stage_text, flags=re.IGNORECASE | re.MULTILINE):
                signal_hits += 1
                print(f"[PASS] signal `{label}`")
            else:
                print(f"[BLOCKED] missing signal `{label}`")
                blocked = True

        min_reasoning_units = MIN_REASONING_UNITS[key]
        reasoning_unit_count = len(
            re.findall(
                r"^###\s+(?:Reasoning Unit\s+\d+:|推理单元\s+\d+[：:])",
                stage_text,
                flags=re.IGNORECASE | re.MULTILINE,
            )
        )
        if reasoning_unit_count < min_reasoning_units:
            print(
                f"[BLOCKED] reasoning unit count too low: {reasoning_unit_count} < {min_reasoning_units}"
            )
            blocked = True
        else:
            print(f"[PASS] reasoning unit count: {reasoning_unit_count} >= {min_reasoning_units}")

        for label, pattern, ratio in REASONING_FIELD_PATTERNS:
            hits = len(re.findall(pattern, stage_text, flags=re.IGNORECASE | re.MULTILINE))
            required_hits = max(1, int(min_reasoning_units * ratio))
            if hits < required_hits:
                print(
                    f"[BLOCKED] reasoning field `{label}` count too low: {hits} < {required_hits}"
                )
                blocked = True
            else:
                print(f"[PASS] reasoning field `{label}` count: {hits} >= {required_hits}")

        if key == "stage_02a":
            activity_items = len(
                re.findall(
                    r"^\s*(?:\d+\.\s+|-\s+)(?:Configure|Generate|Interpret|Execute|Review|[^`\n]{2,})",
                    stage_text,
                    flags=re.IGNORECASE | re.MULTILINE,
                )
            )
            if activity_items < 5:
                print(f"[BLOCKED] backbone activity item count too low: {activity_items} < 5")
                blocked = True
            else:
                print(f"[PASS] backbone activity item count: {activity_items} >= 5")

            scenario_hits = len(
                re.findall(
                    r"Scenario\s+[0-9A-Z]|Scenario Deep Dive|scenario consequence|key-path scenario|DR-\d+",
                    stage_text,
                    flags=re.IGNORECASE,
                )
            )
            if scenario_hits < 10:
                print(f"[BLOCKED] Stage-02a scenario/design signal count too low: {scenario_hits} < 10")
                blocked = True
            else:
                print(f"[PASS] Stage-02a scenario/design signal count: {scenario_hits} >= 10")

            nfr_scan_block = block_after_anchor(stage_text, r"^\s*-\s+nfr_initial_identification:\s*$")
            if not nfr_scan_block:
                print("[BLOCKED] missing explicit `nfr_initial_identification` data block")
                blocked = True
            else:
                print("[PASS] explicit `nfr_initial_identification` data block present")
                required_nfr_fields = (
                    ("nfr_dimensions_scan", r"^\s*-\s+nfr_dimensions_scan:\s*$"),
                    ("nfr_scan_completeness", r"^\s*-\s+nfr_scan_completeness:\s*$"),
                    ("stage_02b_dependency_note", r"^\s*-\s+stage_02b_dependency_note:\s*$"),
                    ("stage_02b_planned", r"stage_02b_planned"),
                    ("if_skipped_impact", r"if_skipped_impact"),
                    ("minimum_viable_for_phase2", r"minimum_viable_for_phase2"),
                )
                for label, pattern in required_nfr_fields:
                    if re.search(pattern, nfr_scan_block, flags=re.IGNORECASE | re.MULTILINE):
                        print(f"[PASS] Stage-02a NFR scan field `{label}`")
                    else:
                        print(f"[BLOCKED] Stage-02a NFR scan missing field `{label}`")
                        blocked = True

        if key == "stage_02b":
            entity_hits = len(
                re.findall(
                    r"\bmodule\b|\bobject\b|\bentity\b|\bworkflow\b|\bstate\b|核心实体|实体|对象|模块",
                    stage_text,
                    flags=re.IGNORECASE,
                )
            )
            if entity_hits < 5:
                print(f"[BLOCKED] domain-entity signal count too low: {entity_hits} < 5")
                blocked = True
            else:
                print(f"[PASS] domain-entity signal count: {entity_hits} >= 5")

            spec_hits = len(
                re.findall(
                    r"erDiagram|subsystem|screen/module|quality scenario|metric|action payload|task bridge|workflow mapping",
                    stage_text,
                    flags=re.IGNORECASE,
                )
            )
            if spec_hits < 10:
                print(f"[BLOCKED] Stage-02b specification signal count too low: {spec_hits} < 10")
                blocked = True
            else:
                print(f"[PASS] Stage-02b specification signal count: {spec_hits} >= 10")

        if key == "stage_04":
            target_hits = len(re.findall(r"Target\s*[1-9]|target\s*[1-9]|验证对象", stage_text, flags=re.IGNORECASE))
            if target_hits < 3:
                print(f"[BLOCKED] validation target signal count too low: {target_hits} < 3")
                blocked = True
            else:
                print(f"[PASS] validation target signal count: {target_hits} >= 3")

        if key == "stage_03":
            slice_hits = len(
                re.findall(
                    r"Slice Alternatives Comparison|Value-Frequency Assessment|MVP Loop Viability Test|Deferred Items Honesty Check|Slice Map and Dependency View|what_changes_if_positive",
                    stage_text,
                    flags=re.IGNORECASE,
                )
            )
            if slice_hits < 6:
                print(f"[BLOCKED] Stage-03 slicing-method signal count too low: {slice_hits} < 6")
                blocked = True
            else:
                print(f"[PASS] Stage-03 slicing-method signal count: {slice_hits} >= 6")

        if key == "stage_04":
            validation_hits = len(
                re.findall(
                    r"Validation Target Clarity|Method-Fit Comparison|Prototype Fidelity Record|Validation Dimensions Covered|Evidence State Honesty|Validation Flow|ready-to-converge",
                    stage_text,
                    flags=re.IGNORECASE,
                )
            )
            if validation_hits < 6:
                print(f"[BLOCKED] Stage-04 validation-method signal count too low: {validation_hits} < 6")
                blocked = True
            else:
                print(f"[PASS] Stage-04 validation-method signal count: {validation_hits} >= 6")

            stage_02b_state_block = block_after_anchor(
                stage_text,
                r"^\s*-\s+(?:stage_02b_execution_state|Stage-02b 执行状态\s+\(stage_02b_execution_state\)):\s*$",
            )
            if not stage_02b_state_block:
                print("[BLOCKED] missing explicit `stage_02b_execution_state` field")
                blocked = True
            else:
                state_match = re.search(r"`?(executed|skipped|partial)`?", stage_02b_state_block, flags=re.IGNORECASE)
                if not state_match:
                    print("[BLOCKED] `stage_02b_execution_state` exists but state value is missing/invalid")
                    blocked = True
                else:
                    state_value = state_match.group(1).lower()
                    print(f"[PASS] stage_02b_execution_state: {state_value}")
                    if state_value in {"skipped", "partial"}:
                        skip_decl_block = block_after_anchor(stage_text, r"^\s*-\s+stage_02b_skip_declaration:\s*$")
                        if not skip_decl_block:
                            print("[BLOCKED] missing `stage_02b_skip_declaration` block for skipped/partial Stage-02b")
                            blocked = True
                        else:
                            required_skip_fields = (
                                ("nfr_source", r"nfr_source"),
                                ("domain_model_state", r"domain_model_state"),
                                ("ia_direction_state", r"ia_direction_state"),
                                ("impact_on_phase2", r"impact_on_phase2"),
                                ("minimum_viable_for_phase2", r"minimum_viable_for_phase2"),
                                ("mitigation_note", r"mitigation_note"),
                            )
                            for label, pattern in required_skip_fields:
                                if re.search(pattern, skip_decl_block, flags=re.IGNORECASE | re.MULTILINE):
                                    print(f"[PASS] Stage-04 skip declaration field `{label}`")
                                else:
                                    print(f"[BLOCKED] Stage-04 skip declaration missing field `{label}`")
                                    blocked = True

        print(f"signal_hits: {signal_hits}/{len(rule.required_signals)}")

    total_char_ratio = total_stage_chars / source_chars if source_chars else 0.0
    total_line_ratio = total_stage_lines / source_lines if source_lines else 0.0
    print("\n-- Stage Aggregate --")
    print(
        f"total_stage_size: chars={total_stage_chars}, lines={total_stage_lines}; "
        f"source_ratios: char={total_char_ratio:.3f}, line={total_line_ratio:.3f}"
    )
    if total_char_ratio < args.min_total_stage_char_ratio:
        print(
            "[BLOCKED] total stage char ratio too low: "
            f"{total_char_ratio:.3f} < {args.min_total_stage_char_ratio:.3f}"
        )
        blocked = True
    else:
        print(
            "[PASS] total stage char ratio: "
            f"{total_char_ratio:.3f} >= {args.min_total_stage_char_ratio:.3f}"
        )
    if total_line_ratio < args.min_total_stage_line_ratio:
        print(
            "[BLOCKED] total stage line ratio too low: "
            f"{total_line_ratio:.3f} < {args.min_total_stage_line_ratio:.3f}"
        )
        blocked = True
    else:
        print(
            "[PASS] total stage line ratio: "
            f"{total_line_ratio:.3f} >= {args.min_total_stage_line_ratio:.3f}"
        )

    if blocked:
        print("FINAL: BLOCKED")
        return 2
    print("FINAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
