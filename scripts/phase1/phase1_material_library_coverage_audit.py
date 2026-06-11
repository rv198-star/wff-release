#!/usr/bin/env python3
"""
Audit Phase-1 material-library coverage from source index -> stage source-cards ->
stage source-registers -> runtime activation evidence.
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
from dataclasses import dataclass
from pathlib import Path

from phase1.phase1_reasoning_runtime import method_matches


REPO_ROOT = Path(__file__).resolve().parents[2]

STAGES = {
    "stage_01": {
        "label": "Stage-01",
        "dir": REPO_ROOT / "reference-packages/phase1-product-requirements/stage-01-user-research",
        "artifact_name": "stage-01-user-research.md",
    },
    "stage_02a": {
        "label": "Stage-02a",
        "dir": REPO_ROOT / "reference-packages/phase1-product-requirements/stage-02-requirements-analysis",
        "artifact_name": "stage-02a-requirements-structural-analysis.md",
    },
    "stage_02b": {
        "label": "Stage-02b",
        "dir": REPO_ROOT / "reference-packages/phase1-product-requirements/stage-02b-requirements-specification",
        "artifact_name": "stage-02b-requirements-specification-deepening.md",
    },
    "stage_03": {
        "label": "Stage-03",
        "dir": REPO_ROOT / "reference-packages/phase1-product-requirements/stage-03-requirements-decomposition",
        "artifact_name": "stage-03-requirements-decomposition-and-mvp-slicing.md",
    },
    "stage_04": {
        "label": "Stage-04",
        "dir": REPO_ROOT / "reference-packages/phase1-product-requirements/stage-04-requirements-validation",
        "artifact_name": "stage-04-requirements-validation-and-concept-proof.md",
    },
}


@dataclass(frozen=True)
class StageCoverage:
    key: str
    label: str
    source_cards: str
    source_register_exists: bool
    required_bundles: list[str]
    required_methods: list[str]
    runtime_loaded_bundles: list[str]
    runtime_activated_methods: list[str]
    method_coverage_ratio: float
    matched_required_methods: list[str]
    unmatched_required_methods: list[str]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
    items: list[str] = []
    if not block:
        return items
    for line in block.splitlines()[1:]:
        bullet = re.match(r"^\s*-\s+`?([^`]+?)`?\s*$", line)
        if bullet:
            items.append(bullet.group(1).strip())
            continue
        numbered = re.match(r"^\s*\d+\.\s+`?([^`]+?)`?\s*$", line)
        if numbered:
            items.append(numbered.group(1).strip())
    return items


def extract_nested_bullets(text: str, label: str) -> list[str]:
    match = re.search(
        rf"^\s*-\s+{re.escape(label)}:\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return []
    tail = text[match.end() :]
    items: list[str] = []
    for line in tail.splitlines():
        if re.match(r"^\s*-\s+[A-Za-z_][A-Za-z0-9_ ]*:\s*$", line):
            break
        item = re.match(r"^\s{2,}-\s+`?([^`]+?)`?\s*$", line)
        if item:
            items.append(item.group(1).strip())
    return items


def parse_source_index_bundles(path: Path) -> list[str]:
    text = read_text(path)
    block = find_named_h2_block(text, ["当前纳入的 source bundles"])
    items = list_items_from_block(block)
    normalized: list[str] = []
    for item in items:
        value = item.strip().rstrip("/")
        if "/" in value:
            value = value.split("/")[-1]
        normalized.append(value)
    return normalized


def parse_coverage_ledger_container_influence(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    lines = read_text(path).splitlines()
    in_table = False
    containers: dict[str, list[str]] = {}
    for line in lines:
        if line.startswith("| source_container |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            if containers:
                break
            continue
        if re.search(r"\|\s*---", line):
            continue
        cols = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(cols) >= 5 and cols[0]:
            containers.setdefault(cols[0], []).append(cols[4])
    return containers


def build_stage_coverage(stage_key: str, stage_dir_output: Path | None) -> StageCoverage:
    stage = STAGES[stage_key]
    source_cards_path = stage["dir"] / "source-cards.md"
    source_register_path = stage["dir"] / "source-register.md"
    source_cards_text = read_text(source_cards_path)
    required_bundles = list_items_from_block(find_named_h2_block(source_cards_text, ["Required Source Bundles"]))
    required_methods = list_items_from_block(find_named_h2_block(source_cards_text, ["Required Method Assets"]))

    runtime_loaded_bundles: list[str] = []
    runtime_activated_methods: list[str] = []
    artifact_path = stage_dir_output / stage["artifact_name"] if stage_dir_output else None
    if artifact_path and artifact_path.exists():
        artifact_text = read_text(artifact_path)
        runtime_loaded_bundles = extract_nested_bullets(artifact_text, "source_bundles_loaded")
        method_block = find_named_h2_block(artifact_text, ["Method Activation Evidence"])
        runtime_activated_methods = extract_nested_bullets(method_block, "activated_method_families")

    matched_methods: list[str] = []
    unmatched_methods: list[str] = []
    for required in required_methods:
        if any(method_matches(activated, required) or method_matches(required, activated) for activated in runtime_activated_methods):
            matched_methods.append(required)
        else:
            unmatched_methods.append(required)

    ratio = round(len(matched_methods) / len(required_methods), 3) if required_methods else 1.0
    return StageCoverage(
        key=stage_key,
        label=str(stage["label"]),
        source_cards=str(source_cards_path),
        source_register_exists=source_register_path.exists(),
        required_bundles=required_bundles,
        required_methods=required_methods,
        runtime_loaded_bundles=runtime_loaded_bundles,
        runtime_activated_methods=runtime_activated_methods,
        method_coverage_ratio=ratio,
        matched_required_methods=matched_methods,
        unmatched_required_methods=unmatched_methods,
    )


def build_report(
    *,
    source_index_bundles: list[str],
    coverage_ledger_container_influence: dict[str, list[str]],
    stage_coverages: list[StageCoverage],
    stage_dir_output: Path | None,
) -> tuple[str, dict[str, object]]:
    source_index_set = set(source_index_bundles)
    coverage_container_set = set(coverage_ledger_container_influence)
    declared_bundle_map: dict[str, list[str]] = {}
    runtime_bundle_map: dict[str, list[str]] = {}
    missing_from_index: list[str] = []
    missing_from_ledger: list[str] = []
    stages_missing_register = [stage.label for stage in stage_coverages if not stage.source_register_exists]

    def is_intentional_sidecar(bundle: str) -> bool:
        influence_levels = {
            level.strip()
            for level in coverage_ledger_container_influence.get(bundle, [])
            if level.strip()
        }
        return bool(influence_levels) and influence_levels <= {"sidecar"}

    for stage in stage_coverages:
        for bundle in stage.required_bundles:
            declared_bundle_map.setdefault(bundle, []).append(stage.label)
            if bundle not in source_index_set and bundle not in missing_from_index:
                missing_from_index.append(bundle)
            if bundle not in coverage_container_set and bundle not in missing_from_ledger:
                missing_from_ledger.append(bundle)
        for bundle in stage.runtime_loaded_bundles:
            runtime_bundle_map.setdefault(bundle, []).append(stage.label)

    intentional_sidecar_index_bundles = [
        bundle
        for bundle in source_index_bundles
        if bundle not in declared_bundle_map and is_intentional_sidecar(bundle)
    ]
    unused_index_bundles = [
        bundle
        for bundle in source_index_bundles
        if bundle not in declared_bundle_map and bundle not in intentional_sidecar_index_bundles
    ]
    low_method_coverage = sorted(
        [stage for stage in stage_coverages if stage.method_coverage_ratio < 0.7],
        key=lambda item: item.method_coverage_ratio,
    )

    lines = [
        "# Phase-1 Material Library Coverage Audit",
        "",
        "## 1. Executive Summary",
        f"- source-index bundles: `{len(source_index_bundles)}`",
        f"- stage-declared distinct bundles: `{len(declared_bundle_map)}`",
        f"- stage-wired but missing from source index: `{', '.join(missing_from_index) if missing_from_index else '(none)'}`",
        f"- stage-wired but missing from source-unit coverage ledger: `{', '.join(missing_from_ledger) if missing_from_ledger else '(none)'}`",
        f"- indexed sidecar bundles intentionally not on the Phase-1 mainline: `{', '.join(intentional_sidecar_index_bundles) if intentional_sidecar_index_bundles else '(none)'}`",
        f"- indexed but currently unused by Phase-1 stage source-cards: `{', '.join(unused_index_bundles) if unused_index_bundles else '(none)'}`",
        f"- stages missing source-register.md: `{', '.join(stages_missing_register) if stages_missing_register else '(none)'}`",
        f"- runtime stage artifacts inspected: `{'yes' if stage_dir_output else 'no'}`",
        "",
        "## 2. Bundle Coverage Matrix",
        "",
        "| bundle | in_source_index | in_source_unit_ledger | declared_stages | runtime_loaded_stages | notes |",
        "|---|---|---|---|---|---|",
    ]

    all_bundles = sorted(set(source_index_bundles) | set(declared_bundle_map) | set(runtime_bundle_map))
    for bundle in all_bundles:
        notes: list[str] = []
        if bundle in source_index_set and bundle not in declared_bundle_map and is_intentional_sidecar(bundle):
            notes.append("indexed-sidecar-not-mainline")
        elif bundle in source_index_set and bundle not in declared_bundle_map:
            notes.append("indexed-but-unused")
        if bundle in declared_bundle_map and bundle not in source_index_set:
            notes.append("wired-without-source-index-entry")
        if bundle in declared_bundle_map and bundle not in coverage_container_set:
            notes.append("wired-without-ledger-entry")
        if not notes:
            notes.append("covered")
        lines.append(
            "| "
            + " | ".join(
                [
                    bundle,
                    "yes" if bundle in source_index_set else "no",
                    "yes" if bundle in coverage_container_set else "no",
                    ", ".join(declared_bundle_map.get(bundle, [])) or "(none)",
                    ", ".join(runtime_bundle_map.get(bundle, [])) or "(none)",
                    ", ".join(notes),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 3. Stage Method-Usage Coverage",
            "",
            "| stage | source_register | required_bundles | required_methods | runtime_activated_methods | method_coverage | unmatched_required_methods |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for stage in stage_coverages:
        lines.append(
            "| "
            + " | ".join(
                [
                    stage.label,
                    "present" if stage.source_register_exists else "missing",
                    str(len(stage.required_bundles)),
                    str(len(stage.required_methods)),
                    str(len(stage.runtime_activated_methods)),
                    f"{stage.method_coverage_ratio:.1%}",
                    ", ".join(stage.unmatched_required_methods) or "(none)",
                ]
            )
            + " |"
        )

    lines.extend(["", "## 4. Findings"])
    if missing_from_index:
        lines.append(
            f"- `source index drift`: {', '.join(f'`{item}`' for item in missing_from_index)} "
            "is already wired into stage source-cards but is absent from `docs/internal/source-registers/product-requirements-source-index.md`."
        )
    if missing_from_ledger:
        lines.append(
            f"- `source-unit ledger drift`: {', '.join(f'`{item}`' for item in missing_from_ledger)} "
            "is stage-wired but not represented in `docs/internal/source-registers/phase-1-source-unit-coverage-ledger-v0.1.md`."
        )
    if intentional_sidecar_index_bundles:
        lines.append(
            f"- `intentional sidecar posture`: {', '.join(f'`{item}`' for item in intentional_sidecar_index_bundles)} "
            "is indexed for later-stage reuse but is explicitly kept off the current Phase-1 mainline."
        )
    if unused_index_bundles:
        lines.append(
            f"- `indexed but unused bundles`: {', '.join(f'`{item}`' for item in unused_index_bundles)} "
            "is present in the product-requirements source index but not selected by the current Phase-1 stage source-cards."
        )
    if stages_missing_register:
        lines.append(
            f"- `stage source-register gap`: {', '.join(f'`{item}`' for item in stages_missing_register)} "
            "does not currently have a `source-register.md`, so allowed-source rationale is less auditable there."
        )
    if low_method_coverage:
        for stage in low_method_coverage:
            lines.append(
                f"- `method activation coverage`: {stage.label} matched only `{stage.method_coverage_ratio:.1%}` "
                f"of declared required method assets; unmatched: {', '.join(f'`{item}`' for item in stage.unmatched_required_methods)}."
            )
    if not any([missing_from_index, missing_from_ledger, unused_index_bundles, stages_missing_register, low_method_coverage]):
        lines.append("- no major coverage gaps detected")

    payload = {
        "source_index_bundles": source_index_bundles,
        "coverage_ledger_containers": sorted(coverage_container_set),
        "summary": {
            "source_index_bundle_count": len(source_index_bundles),
            "stage_declared_bundle_count": len(declared_bundle_map),
            "missing_from_source_index": missing_from_index,
            "missing_from_source_unit_ledger": missing_from_ledger,
            "indexed_sidecar_not_mainline": intentional_sidecar_index_bundles,
            "indexed_but_unused": unused_index_bundles,
            "stages_missing_source_register": stages_missing_register,
        },
        "stages": [
            {
                "stage": stage.label,
                "source_register_exists": stage.source_register_exists,
                "required_bundles": stage.required_bundles,
                "required_methods": stage.required_methods,
                "runtime_loaded_bundles": stage.runtime_loaded_bundles,
                "runtime_activated_methods": stage.runtime_activated_methods,
                "method_coverage_ratio": stage.method_coverage_ratio,
                "matched_required_methods": stage.matched_required_methods,
                "unmatched_required_methods": stage.unmatched_required_methods,
            }
            for stage in stage_coverages
        ],
    }
    return "\n".join(lines).rstrip() + "\n", payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase-1 material-library coverage")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--stage-dir")
    parser.add_argument("--output-md")
    parser.add_argument("--output-json")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    stage_dir_output = Path(args.stage_dir).resolve() if args.stage_dir else None
    source_index_path = repo_root / "docs/internal/source-registers/product-requirements-source-index.md"
    coverage_ledger_path = repo_root / "docs/internal/source-registers/phase-1-source-unit-coverage-ledger-v0.1.md"

    source_index_bundles = parse_source_index_bundles(source_index_path)
    coverage_ledger_container_influence = parse_coverage_ledger_container_influence(coverage_ledger_path)
    stage_coverages = [build_stage_coverage(stage_key, stage_dir_output) for stage_key in STAGES]
    markdown, payload = build_report(
        source_index_bundles=source_index_bundles,
        coverage_ledger_container_influence=coverage_ledger_container_influence,
        stage_coverages=stage_coverages,
        stage_dir_output=stage_dir_output,
    )

    if args.output_md:
        Path(args.output_md).resolve().write_text(markdown, encoding="utf-8")
    if args.output_json:
        Path(args.output_json).resolve().write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print("== Phase-1 Material Library Coverage Audit ==")
    print(f"source_index_bundles: {len(source_index_bundles)}")
    print(f"stage_declared_distinct_bundles: {len({bundle for stage in stage_coverages for bundle in stage.required_bundles})}")
    print(
        "missing_from_source_index: "
        + (", ".join(payload["summary"]["missing_from_source_index"]) or "(none)")
    )
    print(
        "indexed_sidecar_not_mainline: "
        + (", ".join(payload["summary"]["indexed_sidecar_not_mainline"]) or "(none)")
    )
    print(
        "indexed_but_unused: "
        + (", ".join(payload["summary"]["indexed_but_unused"]) or "(none)")
    )
    print(
        "stages_missing_source_register: "
        + (", ".join(payload["summary"]["stages_missing_source_register"]) or "(none)")
    )
    for stage in stage_coverages:
        print(
            f"{stage.label}: method_coverage={stage.method_coverage_ratio:.1%}; "
            f"unmatched={len(stage.unmatched_required_methods)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
