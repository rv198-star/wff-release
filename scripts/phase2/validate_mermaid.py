#!/usr/bin/env python3
"""
Validate Mermaid block presence, syntax, semantic depth, and optional renderability
for Phase-2 artifacts.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from phase2.phase2_quality_check import analyze_stage, mermaid_blocks, mermaid_counts, read_text


EXPECTED_TYPES = {
    "stage_01": {"C4Context": 1, "flowchart_TD": 1},
    "stage_02": {"flowchart_LR": 1, "erDiagram": 1, "stateDiagram-v2": 3},
    "stage_03": {"flowchart_LR": 2},
    "stage_04": {"C4Container": 1, "sequenceDiagram": 3, "gantt": 1},
}

WRAPPER_PAIRS = {"[": "]", "(": ")", "{": "}"}


def detect_type(first_line: str) -> str:
    if first_line.startswith("C4Context"):
        return "C4Context"
    if first_line.startswith("C4Container"):
        return "C4Container"
    if first_line.startswith("stateDiagram-v2"):
        return "stateDiagram-v2"
    if first_line.startswith("sequenceDiagram"):
        return "sequenceDiagram"
    if first_line.startswith("erDiagram"):
        return "erDiagram"
    if first_line.startswith("gantt"):
        return "gantt"
    if first_line.startswith("flowchart TD"):
        return "flowchart_TD"
    if first_line.startswith("flowchart LR"):
        return "flowchart_LR"
    if first_line.startswith("flowchart TB"):
        return "flowchart_TB"
    return "unknown"


def basic_syntax_errors(diagram_type: str, body: str) -> list[str]:
    errors: list[str] = []
    if diagram_type in {"flowchart_TD", "flowchart_LR"} and "-->" not in body:
        errors.append("flowchart missing arrow edge")
    if diagram_type == "flowchart_TB":
        errors.append("flowchart TB is not an approved Phase-2 syntax; use flowchart TD or flowchart LR as required")
    if diagram_type == "sequenceDiagram" and ("participant " not in body or "->>" not in body):
        errors.append("sequenceDiagram missing participant or message edge")
    if diagram_type == "stateDiagram-v2" and "-->" not in body:
        errors.append("stateDiagram-v2 missing transition edge")
    if diagram_type == "erDiagram" and not any(token in body for token in ("||", "o{", "}o", "}|")):
        errors.append("erDiagram missing relationship cardinality")
    if diagram_type == "gantt" and "section " not in body:
        errors.append("gantt missing section definition")
    if diagram_type == "C4Context" and "Rel(" not in body:
        errors.append("C4Context missing Rel(...) entries")
    if diagram_type == "C4Container" and "Container" not in body:
        errors.append("C4Container missing Container(...) entries")
    return errors


def lines_without_header(body: str) -> list[str]:
    return [line.strip() for line in body.splitlines()[1:] if line.strip()]


def count_c4_elements(body: str) -> int:
    return sum(
        1
        for line in lines_without_header(body)
        if re.match(r"^(Person|System|System_Ext|Container|ContainerDb)\(", line)
    )


def count_c4_relationships(body: str) -> int:
    return sum(1 for line in lines_without_header(body) if line.startswith("Rel("))


def count_flowchart_nodes(body: str) -> int:
    nodes: set[str] = set()
    for line in lines_without_header(body):
        if line.startswith("subgraph") or line == "end":
            continue
        for token in re.findall(r"\b([A-Za-z][A-Za-z0-9_]*)\s*(?=\[|\(|\{)", line):
            nodes.add(token)
    return len(nodes)


def count_flowchart_edges(body: str) -> int:
    return sum(1 for line in lines_without_header(body) if any(token in line for token in ("-->", "-. ", "-.->", "==>")))


def count_state_nodes(body: str) -> int:
    states: set[str] = set()
    for line in lines_without_header(body):
        if "-->" not in line:
            continue
        cleaned = line.split(":", 1)[0]
        left, right = [part.strip() for part in cleaned.split("-->", 1)]
        for candidate in (left, right):
            if candidate and candidate != "[*]":
                states.add(candidate)
    return len(states)


def count_state_transitions(body: str) -> int:
    return sum(1 for line in lines_without_header(body) if "-->" in line)


def count_sequence_participants(body: str) -> int:
    return sum(1 for line in lines_without_header(body) if line.startswith(("participant ", "actor ")))


def count_sequence_messages(body: str) -> int:
    return sum(1 for line in lines_without_header(body) if any(token in line for token in ("->>", "-->>", "-x", "--x")))


def count_er_entities(body: str) -> int:
    entities: set[str] = set()
    for line in lines_without_header(body):
        if not any(token in line for token in ("||", "o{", "}o", "}|", "|o", "}|")):
            continue
        parts = re.findall(r"\b([A-Z][A-Z0-9_]+)\b", line)
        if len(parts) >= 2:
            entities.update(parts[:2])
    return len(entities)


def count_er_relationships(body: str) -> int:
    return sum(
        1
        for line in lines_without_header(body)
        if any(token in line for token in ("||", "o{", "}o", "}|", "|o"))
    )


def count_gantt_tasks(body: str) -> int:
    task_count = 0
    for line in lines_without_header(body):
        if line.startswith(("title ", "dateFormat ", "section ")):
            continue
        if ":" in line:
            task_count += 1
    return task_count


def semantic_errors(diagram_type: str, body: str) -> list[str]:
    errors: list[str] = []
    if diagram_type in {"C4Context", "C4Container"}:
        element_count = count_c4_elements(body)
        relationship_count = count_c4_relationships(body)
        if element_count < 4:
            errors.append(f"{diagram_type} has too few elements ({element_count} < 4)")
        if relationship_count < 3:
            errors.append(f"{diagram_type} has too few relationships ({relationship_count} < 3)")
    elif diagram_type in {"flowchart_TD", "flowchart_LR"}:
        node_count = count_flowchart_nodes(body)
        edge_count = count_flowchart_edges(body)
        if node_count < 4:
            errors.append(f"{diagram_type} has too few nodes ({node_count} < 4)")
        if edge_count < 3:
            errors.append(f"{diagram_type} has too few edges ({edge_count} < 3)")
    elif diagram_type == "stateDiagram-v2":
        state_count = count_state_nodes(body)
        transition_count = count_state_transitions(body)
        if state_count < 4:
            errors.append(f"stateDiagram-v2 has too few states ({state_count} < 4)")
        if transition_count < 4:
            errors.append(f"stateDiagram-v2 has too few transitions ({transition_count} < 4)")
    elif diagram_type == "sequenceDiagram":
        participant_count = count_sequence_participants(body)
        message_count = count_sequence_messages(body)
        if participant_count < 3:
            errors.append(f"sequenceDiagram has too few participants ({participant_count} < 3)")
        if message_count < 4:
            errors.append(f"sequenceDiagram has too few messages ({message_count} < 4)")
    elif diagram_type == "erDiagram":
        entity_count = count_er_entities(body)
        relationship_count = count_er_relationships(body)
        if entity_count < 5:
            errors.append(f"erDiagram has too few entities ({entity_count} < 5)")
        if relationship_count < 3:
            errors.append(f"erDiagram has too few relationships ({relationship_count} < 3)")
    elif diagram_type == "gantt":
        task_count = count_gantt_tasks(body)
        if task_count < 4:
            errors.append(f"gantt has too few tasks ({task_count} < 4)")
    return errors


def clean_cell(value: str) -> str:
    return value.strip().strip("`").strip()


def normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", clean_cell(value).lower())


def parse_markdown_tables(block: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    lines = block.splitlines()
    idx = 0
    while idx < len(lines):
        if not lines[idx].lstrip().startswith("|"):
            idx += 1
            continue
        group: list[str] = []
        while idx < len(lines) and lines[idx].lstrip().startswith("|"):
            group.append(lines[idx].strip())
            idx += 1
        if len(group) < 2 or "---" not in group[1]:
            continue
        headers = [normalize_header(part) for part in group[0].strip("|").split("|")]
        rows: list[dict[str, str]] = []
        for row_line in group[2:]:
            parts = [clean_cell(part) for part in row_line.strip("|").split("|")]
            if len(parts) < len(headers):
                parts.extend([""] * (len(headers) - len(parts)))
            rows.append(dict(zip(headers, parts)))
        tables.append({"headers": headers, "rows": rows})
    return tables


def table_column_values(block: str, header_names: tuple[str, ...]) -> list[str]:
    wanted = {normalize_header(name) for name in header_names}
    values: list[str] = []
    for table in parse_markdown_tables(block):
        column = next((header for header in table["headers"] if header in wanted), "")
        if not column:
            continue
        for row in table["rows"]:
            value = clean_cell(row.get(column, ""))
            if value:
                values.append(value)
    return list(dict.fromkeys(values))


def parse_module_names(block: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"`(geo\.[^`]+)`", block)))


def parse_service_names(block: str) -> list[str]:
    names = []
    for line in block.splitlines():
        if not line.startswith("  - "):
            continue
        stripped = line.strip()
        if stripped.startswith("- `") and stripped.endswith("`:"):
            names.append(clean_cell(stripped.split("`", 2)[1]))
        elif stripped.startswith("- ") and stripped.endswith(":"):
            names.append(clean_cell(stripped[2:-1]))
    return list(dict.fromkeys(names))


def parse_schema_table_names(block: str) -> list[str]:
    return table_column_values(block, ("table_name",))


def normalize_text(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = value.replace("_", " ").replace("-", " ").replace(".", " ")
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def normalized_tokens(value: str) -> set[str]:
    return {token for token in normalize_text(value).split() if len(token) > 1}


def unwrap_wrappers(value: str) -> str:
    text = value.strip()
    for _ in range(6):
        if len(text) >= 2 and WRAPPER_PAIRS.get(text[0]) == text[-1]:
            text = text[1:-1].strip()
            continue
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'", "`"}:
            text = text[1:-1].strip()
            continue
        break
    return text.strip()


def extract_flowchart_labels(body: str) -> list[str]:
    labels: list[str] = []
    for line in lines_without_header(body):
        if line.startswith("subgraph") or line == "end":
            continue
        for shape in re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\s*(\[[^\]]+\]|\([^)]+\)|\{[^}]+\})", line):
            label = unwrap_wrappers(shape)
            if label and not label.startswith("subgraph"):
                labels.append(label)
    return list(dict.fromkeys(labels))


def extract_sequence_participant_labels(body: str) -> list[str]:
    participants: list[str] = []
    for line in lines_without_header(body):
        match = re.match(r"^(participant|actor)\s+([A-Za-z][A-Za-z0-9_]*)\s*(?:as\s+(.+))?$", line)
        if not match:
            continue
        participants.append(unwrap_wrappers(match.group(3) or match.group(2)))
    return list(dict.fromkeys(participants))


def coverage_threshold(expected_count: int, *, floor: int, ratio: float) -> int:
    if expected_count <= 0:
        return 0
    return min(expected_count, max(math.ceil(expected_count * ratio), min(floor, expected_count)))


def semantic_name_match(expected: str, observed: str) -> bool:
    expected_normalized = normalize_text(expected)
    observed_normalized = normalize_text(observed)
    if not expected_normalized or not observed_normalized:
        return False
    if expected_normalized == observed_normalized:
        return True
    if expected_normalized in observed_normalized or observed_normalized in expected_normalized:
        return True
    expected_tokens = normalized_tokens(expected)
    observed_tokens = normalized_tokens(observed)
    if not expected_tokens or not observed_tokens:
        return False
    shared = expected_tokens & observed_tokens
    if not shared:
        return False
    required = len(expected_tokens) if len(expected_tokens) <= 3 else max(3, math.ceil(len(expected_tokens) * 0.6))
    return len(shared) >= min(required, len(expected_tokens))


def coverage_report(expected_names: list[str], observed_names: list[str]) -> dict[str, Any]:
    matched: list[str] = []
    missing: list[str] = []
    for expected in expected_names:
        if any(semantic_name_match(expected, observed) for observed in observed_names):
            matched.append(expected)
        else:
            missing.append(expected)
    return {
        "expected_count": len(expected_names),
        "observed_count": len(observed_names),
        "matched_count": len(matched),
        "matched_names": matched,
        "missing_names": missing,
    }


def best_flowchart_coverage(block_entries: list[dict[str, Any]], expected_names: list[str]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for block in block_entries:
        if block["type"] not in {"flowchart_TD", "flowchart_LR"}:
            continue
        labels = extract_flowchart_labels(block["body"])
        coverage = coverage_report(expected_names, labels)
        coverage.update({"index": block["index"], "labels": labels})
        candidates.append(coverage)
    if not candidates:
        return {"index": None, "labels": [], "expected_count": len(expected_names), "observed_count": 0, "matched_count": 0, "matched_names": [], "missing_names": expected_names}
    return max(candidates, key=lambda item: (item["matched_count"], item["observed_count"]))


def stage_alignment_checks(
    stage_key: str,
    block_entries: list[dict[str, Any]],
    stage_analysis: dict[str, Any],
    analyses: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    if stage_key == "stage_02":
        modules = parse_module_names(stage_analysis["blocks"]["module_map"])
        if modules:
            best = best_flowchart_coverage(block_entries, modules)
            required = coverage_threshold(len(modules), floor=4, ratio=0.7)
            checks.append(
                {
                    "check_name": "Stage-02 decomposition flowchart aligns with module_map",
                    "result": "pass" if best["matched_count"] >= required else "fail",
                    "details": (
                        f"best_flowchart=#{best['index']} matched_modules={best['matched_count']}/{len(modules)} "
                        f"(required {required}); missing={', '.join(best['missing_names'][:4]) or 'none'}"
                    ),
                    "matched_count": best["matched_count"],
                    "expected_count": len(modules),
                    "matched_names": best["matched_names"],
                    "missing_names": best["missing_names"],
                }
            )

    if stage_key == "stage_03":
        schema_tables = parse_schema_table_names(stage_analysis["blocks"]["schema_draft"])
        if schema_tables:
            best = best_flowchart_coverage(block_entries, schema_tables)
            required = coverage_threshold(len(schema_tables), floor=5, ratio=0.7)
            checks.append(
                {
                    "check_name": "Stage-03 data-ownership flowchart exposes schema table labels",
                    "result": "pass" if best["matched_count"] >= required else "fail",
                    "details": (
                        f"best_flowchart=#{best['index']} matched_schema_labels={best['matched_count']}/{len(schema_tables)} "
                        f"(required {required}); missing={', '.join(best['missing_names'][:4]) or 'none'}"
                    ),
                    "matched_count": best["matched_count"],
                    "expected_count": len(schema_tables),
                    "matched_names": best["matched_names"],
                    "missing_names": best["missing_names"],
                }
            )

    if stage_key == "stage_04" and analyses and "stage_02" in analyses:
        service_candidates = parse_service_names(analyses["stage_02"]["blocks"]["service_candidates"])
        if service_candidates:
            sequence_labels = []
            for block in block_entries:
                if block["type"] != "sequenceDiagram":
                    continue
                sequence_labels.extend(extract_sequence_participant_labels(block["body"]))
            service_like_labels = [label for label in dict.fromkeys(sequence_labels) if "service" in normalize_text(label)]
            unmatched = [
                label
                for label in service_like_labels
                if not any(normalize_text(candidate) == normalize_text(label) for candidate in service_candidates)
            ]
            checks.append(
                {
                    "check_name": "Stage-04 sequence participants align with Stage-02 service candidates",
                    "result": "pass" if not unmatched else "fail",
                    "details": (
                        f"service_participants={len(service_like_labels)}; unmatched={', '.join(unmatched) or 'none'}"
                    ),
                    "matched_count": len(service_like_labels) - len(unmatched),
                    "expected_count": len(service_like_labels),
                    "matched_names": [label for label in service_like_labels if label not in unmatched],
                    "missing_names": unmatched,
                }
            )

    return checks


def resolve_renderer(explicit_path: str | None = None) -> str | None:
    if explicit_path:
        return explicit_path if Path(explicit_path).exists() or shutil.which(explicit_path) else None
    return shutil.which("mmdc")


def render_stage_blocks(
    stage_key: str,
    block_entries: list[dict[str, Any]],
    *,
    renderer: str | None,
    requested: bool,
    timeout_seconds: int,
) -> dict[str, Any]:
    if not requested:
        return {
            "requested": False,
            "available": bool(renderer),
            "renderer": renderer or "",
            "timeout_seconds": timeout_seconds,
            "status": "not-requested",
            "passed": True,
            "results": [],
        }
    if not renderer:
        return {
            "requested": True,
            "available": False,
            "renderer": "",
            "timeout_seconds": timeout_seconds,
            "status": "unavailable",
            "passed": False,
            "results": [],
            "error": "mmdc not found in PATH",
        }

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"phase2-mermaid-{stage_key}-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        for block in block_entries:
            input_path = tmp_root / f"{stage_key}-block-{block['index']}.mmd"
            output_path = tmp_root / f"{stage_key}-block-{block['index']}.svg"
            input_path.write_text(block["body"] + "\n", encoding="utf-8")
            try:
                proc = subprocess.run(
                    [renderer, "-i", str(input_path), "-o", str(output_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
                render_ok = proc.returncode == 0 and output_path.exists()
                results.append(
                    {
                        "index": block["index"],
                        "type": block["type"],
                        "result": "pass" if render_ok else "fail",
                        "stderr": proc.stderr.strip(),
                        "stdout": proc.stdout.strip(),
                    }
                )
            except subprocess.TimeoutExpired:
                results.append(
                    {
                        "index": block["index"],
                        "type": block["type"],
                        "result": "fail",
                        "stderr": f"mmdc timeout after {timeout_seconds}s",
                        "stdout": "",
                    }
                )

    passed = all(item["result"] == "pass" for item in results)
    return {
        "requested": True,
        "available": True,
        "renderer": renderer,
        "timeout_seconds": timeout_seconds,
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": results,
    }


def validate_stage(
    stage_key: str,
    path: Path,
    *,
    analyses: dict[str, dict[str, Any]] | None = None,
    render_requested: bool = False,
    renderer: str | None = None,
    render_timeout_seconds: int = 20,
) -> dict[str, Any]:
    text = read_text(path)
    stage_analysis = analyses.get(stage_key) if analyses else analyze_stage(stage_key, path)
    block_entries = []
    for index, (first_line, body) in enumerate(mermaid_blocks(text), start=1):
        diagram_type = detect_type(first_line)
        syntax_issue_list = basic_syntax_errors(diagram_type, body)
        semantic_issue_list = semantic_errors(diagram_type, body)
        block_entries.append(
            {
                "index": index,
                "type": diagram_type,
                "first_line": first_line,
                "body": body,
                "syntax_errors": syntax_issue_list,
                "semantic_errors": semantic_issue_list,
            }
        )

    blocks = [
        {
            "index": block["index"],
            "type": block["type"],
            "first_line": block["first_line"],
            "syntax_errors": block["syntax_errors"],
            "semantic_errors": block["semantic_errors"],
        }
        for block in block_entries
    ]
    counts = mermaid_counts(text)
    missing = []
    for diagram_type, minimum in EXPECTED_TYPES.get(stage_key, {}).items():
        current = counts.get(diagram_type, 0)
        if current < minimum:
            missing.append({"type": diagram_type, "current": current, "minimum": minimum})

    syntax_errors = [block for block in blocks if block["syntax_errors"]]
    semantic_errors_blocks = [block for block in blocks if block["semantic_errors"]]
    alignment_checks = stage_alignment_checks(stage_key, block_entries, stage_analysis, analyses)
    alignment_failures = [check for check in alignment_checks if check["result"] == "fail"]
    render_validation = render_stage_blocks(
        stage_key,
        block_entries,
        renderer=renderer,
        requested=render_requested,
        timeout_seconds=render_timeout_seconds,
    )
    passed = not missing and not syntax_errors and not semantic_errors_blocks and not alignment_failures and render_validation["passed"]
    return {
        "path": str(path),
        "counts": counts,
        "blocks": blocks,
        "missing_expected_types": missing,
        "syntax_error_blocks": syntax_errors,
        "semantic_error_blocks": semantic_errors_blocks,
        "semantic_alignment_checks": alignment_checks,
        "semantic_alignment_failures": alignment_failures,
        "render_validation": render_validation,
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Mermaid blocks for Phase-2 artifacts")
    parser.add_argument("--stage-01", required=True)
    parser.add_argument("--stage-02", required=True)
    parser.add_argument("--stage-03", required=True)
    parser.add_argument("--stage-04", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--render", action="store_true", help="Render Mermaid blocks with mmdc when available")
    parser.add_argument("--mmdc-path", help="Optional explicit path to mmdc")
    parser.add_argument("--render-timeout-seconds", type=int, default=20)
    args = parser.parse_args()

    stage_paths = {
        stage_key: Path(getattr(args, stage_key))
        for stage_key in ("stage_01", "stage_02", "stage_03", "stage_04")
    }
    analyses = {stage_key: analyze_stage(stage_key, path) for stage_key, path in stage_paths.items()}
    renderer = resolve_renderer(args.mmdc_path)
    result = {
        stage_key: validate_stage(
            stage_key,
            path,
            analyses=analyses,
            render_requested=args.render,
            renderer=renderer,
            render_timeout_seconds=args.render_timeout_seconds,
        )
        for stage_key, path in stage_paths.items()
    }
    result["render_validation"] = {
        "requested": bool(args.render),
        "available": bool(renderer),
        "renderer": renderer or "",
        "timeout_seconds": args.render_timeout_seconds,
    }
    result["overall_passed"] = all(stage["passed"] for stage in result.values() if isinstance(stage, dict) and "passed" in stage)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": args.output,
                "overall_passed": result["overall_passed"],
                "render_requested": bool(args.render),
                "render_available": bool(renderer),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
