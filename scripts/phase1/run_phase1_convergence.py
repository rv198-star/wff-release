#!/usr/bin/env python3
"""
Executable Phase-1 convergence driver.

This script turns the deep-compilation loop from a documentation-only concept
into a reproducible gate-driven runtime.
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
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from common.output_language import resolve_output_locale
from common.cross_phase_surface_policy import resolve_cross_phase_surface_path
from common.wff_runtime_paths import resolve_wff_base_trace_scripts
from phase1.phase1_converge_prd import apply_narrative_compression_rewrite, load_narrative_compression_rewrite
from phase1.phase1_emit_depth_runtime_artifacts import (
    AGENTIC_LOOP_PLAN_FILENAME,
    DEPTH_RUNTIME_SUMMARY_FILENAME,
    DEPTH_RUNTIME_TEXT_ARTIFACTS,
)
from phase1.phase1_named_state import extract_named_state
from phase1.phase1_trace_units import PHASE1_PRD_ARTIFACT_ID, PHASE1_TRACE_UNIT_TYPE_MAP, extract_phase1_trace_units
from phase1.phase1_version_contract import extract_version_identifiers
ARTIFACT_ID_FIELD_PATTERN = r"^[ \t]*-[ \t]+artifact_id:[ \t]*`?([^`\n]+)`?[ \t]*$"
PHASE1_STAGE_TRACE_DEFAULTS = {
    "stage_01": "P1-S01-OUT-001",
    "stage_02a": "P1-S02a-OUT-001",
    "stage_02b": "P1-S02b-OUT-001",
    "stage_03": "P1-S03-OUT-001",
    "stage_04": "P1-S04-OUT-001",
}
PHASE1_MAINLINE_GATE_BUNDLE = "prd_mainline_gate_bundle"
COMMERCIAL_SAME_RUN_DEEPENING_FOCUS_AREAS = {
    "business_value",
    "value_mechanism",
    "buyer_budget_chain",
    "decision_leverage",
    "user_task_experience",
}
BUSINESS_WORLD_SAME_RUN_DEEPENING_FOCUS_AREAS = {
    "real_world_baseline",
    "scenario_family",
    "business_value",
    "anti_demo",
    "flow_steps",
    "state_transitions",
    "exception_edges",
    "role_handoffs",
    "handoff_contracts",
    "boundary_acceptance",
    "user_task_experience",
}
SAME_RUN_STAGE_REFRESH_FOCUS_AREAS = {
    "flow_steps",
    "state_transitions",
    "exception_edges",
    "role_handoffs",
    "real_world_baseline",
}


@dataclass(frozen=True)
class Phase1ConvergenceRuntimeContext:
    script_dir: Path
    python: str
    source_path: Path
    report_path: Path | None
    convergence_evidence_arg: Path | None
    stage_paths: list[Path]
    candidates: list[Path]
    profile: str
    max_rounds: int
    require_non_shrinking: bool
    depth_mode: str
    thinking_value_gain_mode: str
    output_json_path: Path | None
    auto_remediate: bool
    output_locale: str


def extract_trial_token(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    tokens = extract_version_identifiers(text)
    if len(tokens) == 1:
        return next(iter(tokens))
    return None


def run_command(command: list[str]) -> dict[str, object]:
    proc = subprocess.run(command, capture_output=True, text=True)
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def command_option(command: list[str], option: str, default: str = "") -> str:
    try:
        index = command.index(option)
        return str(command[index + 1])
    except (ValueError, IndexError):
        return default


def trace_project_scope_id(*, project_key: str, project_root: Path) -> str:
    return f"{project_key}:{project_root.resolve()}"


def trace_registry_db_path(project_root: Path, explicit_db_path: str = "") -> Path:
    if explicit_db_path:
        return Path(explicit_db_path).resolve()
    return project_root / ".trace" / "trace.db"


def open_trace_registry_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def complete_direct_trace_command(command: list[str], *, stdout: str) -> dict[str, object]:
    return {
        "command": command,
        "returncode": 0,
        "stdout": stdout,
        "stderr": "",
    }


def run_bind_artifact_in_process(command: list[str]) -> dict[str, object]:
    project_root = Path(command_option(command, "--project-root")).resolve()
    project_key = command_option(command, "--project-key")
    artifact_id = command_option(command, "--artifact-id")
    db_path = trace_registry_db_path(project_root, command_option(command, "--db-path"))
    scope_id = trace_project_scope_id(project_key=project_key, project_root=project_root)
    now = datetime.now(timezone.utc).isoformat()
    conn = open_trace_registry_db(db_path)
    try:
        existing = conn.execute(
            "SELECT artifact_id FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
            (scope_id, artifact_id),
        ).fetchone()
        values = (
            command_option(command, "--artifact-type"),
            command_option(command, "--stage-or-lane"),
            command_option(command, "--status", "draft"),
            command_option(command, "--source-path"),
            command_option(command, "--source-anchor"),
            command_option(command, "--language-role", "runtime-canonical-en"),
            command_option(command, "--canonical-of") or None,
            now,
            scope_id,
            artifact_id,
        )
        if existing:
            conn.execute(
                "UPDATE artifacts SET artifact_type=?, stage_or_lane=?, status=?, source_path=?, source_anchor=?, language_role=?, canonical_of=?, updated_at=? WHERE project_scope=? AND artifact_id=?",
                values,
            )
        else:
            conn.execute(
                "INSERT INTO artifacts (artifact_type, stage_or_lane, status, source_path, source_anchor, language_role, canonical_of, updated_at, project_scope, artifact_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (*values, now),
            )
        conn.commit()
    finally:
        conn.close()
    stdout = f"bound {artifact_id} -> {command_option(command, '--source-path')}#{command_option(command, '--source-anchor')}\n"
    return complete_direct_trace_command(command, stdout=stdout)


def run_link_artifacts_in_process(command: list[str]) -> dict[str, object]:
    project_root = Path(command_option(command, "--project-root")).resolve()
    project_key = command_option(command, "--project-key")
    from_artifact_id = command_option(command, "--from-artifact-id")
    to_artifact_id = command_option(command, "--to-artifact-id")
    link_type = command_option(command, "--link-type")
    if link_type not in {"depends_on", "feeds"}:
        raise SystemExit(f"unsupported link type: {link_type}")
    db_path = trace_registry_db_path(project_root, command_option(command, "--db-path"))
    scope_id = trace_project_scope_id(project_key=project_key, project_root=project_root)
    conn = open_trace_registry_db(db_path)
    try:
        for artifact_id in (from_artifact_id, to_artifact_id):
            row = conn.execute(
                "SELECT artifact_id FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
                (scope_id, artifact_id),
            ).fetchone()
            if not row:
                raise SystemExit(f"Artifact not found in scope: {artifact_id}")
        existing = conn.execute(
            "SELECT id FROM links WHERE project_scope = ? AND from_artifact_id = ? AND to_artifact_id = ? AND link_type = ?",
            (scope_id, from_artifact_id, to_artifact_id, link_type),
        ).fetchone()
        if existing:
            stdout = f"link already exists: {from_artifact_id} -[{link_type}]-> {to_artifact_id}\n"
            return complete_direct_trace_command(command, stdout=stdout)
        conn.execute(
            "INSERT INTO links (project_scope, from_artifact_id, to_artifact_id, link_type, source_path, evidence_anchor, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                scope_id,
                from_artifact_id,
                to_artifact_id,
                link_type,
                command_option(command, "--source-path") or None,
                command_option(command, "--evidence-anchor") or None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    stdout = f"linked {from_artifact_id} -[{link_type}]-> {to_artifact_id}\n"
    return complete_direct_trace_command(command, stdout=stdout)


def run_trace_registry_command_in_process(command: list[str]) -> dict[str, object] | None:
    if len(command) < 2:
        return None
    script_name = Path(str(command[1])).name
    if script_name == "bind_artifact.py":
        return run_bind_artifact_in_process(command)
    if script_name == "link_artifacts.py":
        return run_link_artifacts_in_process(command)
    return None


def apply_final_narrative_compression_if_present(
    *,
    chosen_prd_path: Path | None,
    output_dir: Path,
) -> bool:
    """Re-apply an explicitly authored narrative rewrite to the final selected PRD."""
    if chosen_prd_path is None or not chosen_prd_path.exists():
        return False
    rewrite = load_narrative_compression_rewrite(output_dir / "prd-narrative-compression-rewrite.json")
    if rewrite is None:
        return False
    original_text = chosen_prd_path.read_text(encoding="utf-8")
    rewritten_text = apply_narrative_compression_rewrite(original_text, rewrite)
    if rewritten_text == original_text:
        return False
    chosen_prd_path.write_text(rewritten_text, encoding="utf-8")
    return True


def build_gate_payload(name: str, command: list[str], result: dict[str, object]) -> dict[str, object]:
    return {
        "name": name,
        "returncode": result["returncode"],
        "command": " ".join(command),
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }


def run_gate_bundle(bundle_name: str, bundle_gates: list[tuple[str, list[str]]]) -> dict[str, object]:
    subgates: list[dict[str, object]] = []
    failed_subgates: list[str] = []
    summary_lines = [f"bundle: {bundle_name}"]
    combined_stdout_parts: list[str] = []
    combined_stderr_parts: list[str] = []

    for gate_name, command in bundle_gates:
        result = run_command(command)
        payload = build_gate_payload(gate_name, command, result)
        subgates.append(payload)
        verdict = "PASS" if result["returncode"] == 0 else "BLOCKED"
        summary_lines.append(f"- {gate_name}: {verdict}")
        if result["returncode"] != 0:
            failed_subgates.append(gate_name)
        stdout = str(result.get("stdout", "") or "").rstrip()
        stderr = str(result.get("stderr", "") or "").rstrip()
        combined_stdout_parts.append(f"$ {' '.join(command)}\n{stdout}".rstrip())
        if stderr:
            combined_stderr_parts.append(f"$ {' '.join(command)}\n{stderr}".rstrip())

    return {
        "name": bundle_name,
        "returncode": 0 if not failed_subgates else 2,
        "command": f"{bundle_name}: " + " ; ".join(" ".join(command) for _, command in bundle_gates),
        "stdout": "\n\n".join(part for part in combined_stdout_parts if part).rstrip(),
        "stderr": "\n\n".join(part for part in combined_stderr_parts if part).rstrip(),
        "subgates": subgates,
        "failed_subgates": failed_subgates,
        "summary": "\n".join(summary_lines),
    }


def resolve_phase1_script(script_dir: Path, script_name: str) -> Path:
    direct = script_dir / script_name
    if direct.exists():
        return direct
    nested = script_dir / "phase1" / script_name
    if nested.exists():
        return nested
    return direct


def generate_phase1_prototype_spec_artifact(
    *,
    python: str,
    script_dir: Path,
    prd_path: Path,
    stage_paths: list[Path],
    output_locale: str | None = None,
) -> dict[str, object]:
    stage_map = resolve_stage_map(stage_paths)
    required_stage_keys = ("stage_02a", "stage_03", "stage_04")
    missing_keys = [key for key in required_stage_keys if key not in stage_map]
    output_path = prd_path.parent / "prototype-spec.md"
    prompt_pack_output_path = prd_path.parent / "prototype-prompt-pack.md"
    if missing_keys:
        return {
            "ok": False,
            "message": f"cannot generate prototype-spec because stage files are missing: {', '.join(missing_keys)}",
            "output_path": str(output_path),
            "prompt_pack_output_path": str(prompt_pack_output_path),
        }
    version = infer_trial_token_from_paths([prd_path, *stage_paths]) or "v1"
    command = [
        python,
        str(resolve_phase1_script(script_dir, "phase1_generate_prototype_spec.py")),
        "--prd",
        str(prd_path),
        "--stage-02a",
        str(stage_map["stage_02a"]),
        "--stage-03",
        str(stage_map["stage_03"]),
        "--stage-04",
        str(stage_map["stage_04"]),
        "--output",
        str(output_path),
        "--prompt-pack-output",
        str(prompt_pack_output_path),
        "--version",
        version,
        "--output-locale",
        resolve_output_locale(output_locale),
    ]
    if "stage_02b" in stage_map:
        command.extend(["--stage-02b", str(stage_map["stage_02b"])])
    result = run_command(command)
    return {
        "ok": result["returncode"] == 0 and output_path.exists() and prompt_pack_output_path.exists(),
        "message": (
            "prototype-spec and prototype-prompt-pack generated"
            if result["returncode"] == 0 and output_path.exists() and prompt_pack_output_path.exists()
            else "prototype-spec generation failed"
        ),
        "command": " ".join(command),
        "returncode": result["returncode"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "output_path": str(output_path),
        "prompt_pack_output_path": str(prompt_pack_output_path),
    }


def generate_phase1_interaction_flow_contract_artifact(
    *,
    python: str,
    script_dir: Path,
    prototype_spec_path: Path,
    output_locale: str | None = None,
) -> dict[str, object]:
    output_path = prototype_spec_path.parent / "prototype-interaction-flow-contract.md"
    version = infer_trial_token_from_paths([prototype_spec_path]) or "v1"
    command = [
        python,
        str(resolve_phase1_script(script_dir, "phase1_generate_interaction_flow_contract.py")),
        "--prototype-spec",
        str(prototype_spec_path),
        "--output",
        str(output_path),
        "--version",
        version,
        "--output-locale",
        resolve_output_locale(output_locale),
    ]
    result = run_command(command)
    return {
        "ok": result["returncode"] == 0 and output_path.exists(),
        "message": (
            "prototype-interaction-flow-contract generated"
            if result["returncode"] == 0 and output_path.exists()
            else "prototype-interaction-flow-contract generation failed"
        ),
        "command": " ".join(command),
        "returncode": result["returncode"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "output_path": str(output_path),
    }


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


def first_markdown_title(path: Path) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def infer_trial_token_from_paths(paths: list[Path]) -> str | None:
    for path in paths:
        if not path.exists():
            continue
        token = extract_trial_token(path)
        if token:
            return token
    return None


def redact_runtime_text(value: str, source_path: Path) -> str:
    redacted = value.replace(str(source_path), "<source>")
    redacted = redacted.replace(source_path.name, "source.md")
    return redacted


def sanitize_runtime_payload(value: object, source_path: Path) -> object:
    if isinstance(value, str):
        return redact_runtime_text(value, source_path)
    if isinstance(value, list):
        return [sanitize_runtime_payload(item, source_path) for item in value]
    if isinstance(value, dict):
        sanitized: dict[object, object] = {}
        for key, item in value.items():
            if key in {"command", "stdout", "stderr"} and isinstance(item, str):
                sanitized[key] = "[omitted in artifact JSON; see console/runtime logs if needed]"
            elif key in {
                "source",
                "report",
                "prd",
                "convergence_evidence",
                "output_path",
                "prompt_pack_output_path",
                "interaction_flow_contract_output_path",
                "validation_path",
                "report_text_path",
                "phase_mainline_scorecard_path",
                "phase_acceptance_matrix_path",
                "phase_verdict_path",
            } and isinstance(item, str):
                sanitized[key] = redact_runtime_text(item, source_path)
            else:
                sanitized[key] = sanitize_runtime_payload(item, source_path)
        return sanitized
    return value


def infer_output_dir(prd_path: Path, stage_paths: list[Path]) -> Path:
    parents = {path.parent.resolve() for path in stage_paths if path.exists()}
    if len(parents) == 1:
        return next(iter(parents))
    return prd_path.parent.resolve()


def read_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_phase1_depth_runtime_summary(output_dir: Path) -> dict[str, object] | None:
    summary_path = output_dir / DEPTH_RUNTIME_SUMMARY_FILENAME
    if not summary_path.exists():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


def load_phase1_agentic_loop_plan(output_dir: Path) -> dict[str, object] | None:
    plan_path = output_dir / AGENTIC_LOOP_PLAN_FILENAME
    if not plan_path.exists():
        return None
    return json.loads(plan_path.read_text(encoding="utf-8"))


def count_matches(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE))


def has_signal(texts: list[str], *patterns: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL) for text in texts for pattern in patterns)


def gate_map_from_round(round_payload: dict[str, object] | None) -> dict[str, dict[str, object]]:
    if not isinstance(round_payload, dict):
        return {}
    gates = round_payload.get("gates", [])
    if not isinstance(gates, list):
        return {}
    gate_map: dict[str, dict[str, object]] = {}
    stack = [gate for gate in gates if isinstance(gate, dict)]
    while stack:
        gate = stack.pop(0)
        name = gate.get("name")
        if isinstance(name, str):
            gate_map[name] = gate
        subgates = gate.get("subgates")
        if isinstance(subgates, list):
            stack[0:0] = [item for item in subgates if isinstance(item, dict)]
    return gate_map


def gate_verdict(gate_map: dict[str, dict[str, object]], name: str) -> str:
    gate = gate_map.get(name)
    if not gate:
        return "SKIP"
    return "PASS" if gate.get("returncode") == 0 else "BLOCKED"


def detect_operationally_rich_domain(text: str) -> bool:
    return has_signal(
        [text],
        r"pet clinic|pet hospital|veterinary|hospital|clinic|patient|doctor|treatment|x-?ray|medication",
        r"inventory|warehouse|shipment|logistics|restaurant|retail|cashier|manufacturing|inspection",
        r"finance|financial|compliance|audit|ledger|invoice|billing",
        r"宠物医院|宠物诊所|医院|诊所|就诊|住院|处方|X光|药物|库存|仓储|物流|零售|餐饮|制造|检测|财务|合规|审计",
    )


def clamp_dimension(score: int) -> int:
    return max(0, min(5, score))


def render_phase1_scorecard_markdown(assessment: dict[str, object]) -> str:
    lines = [
        "# Phase-1 Mainline Scorecard",
        "",
        f"- depth_mode: `{assessment['depth_mode']}`",
        f"- operationally_rich_domain: `{'yes' if assessment['operationally_rich_domain'] else 'no'}`",
        f"- total_score: `{assessment['total_score']}` / 100",
        f"- verdict: `{assessment['verdict']}`",
        "",
        "| Dimension | Weight | Score | Notes |",
        "|---|---:|---:|---|",
    ]
    for row in assessment["dimension_scores"]:
        notes = "; ".join(row["notes"]) if row["notes"] else "-"
        lines.append(f"| {row['label']} | {row['weight']} | {row['score']} / 5 | {notes} |")
    return "\n".join(lines).rstrip() + "\n"


def render_phase1_acceptance_matrix_markdown(assessment: dict[str, object]) -> str:
    lines = [
        "# Phase-1 Acceptance Matrix",
        "",
        f"- depth_mode: `{assessment['depth_mode']}`",
        f"- verdict: `{assessment['verdict']}`",
        "",
        "| Acceptance Item | Status | Why |",
        "|---|---|---|",
    ]
    for row in assessment["acceptance_rows"]:
        lines.append(f"| {row['label']} | `{row['status']}` | {row['why']} |")
    return "\n".join(lines).rstrip() + "\n"


def build_phase1_mainline_assessment(
    *,
    depth_mode: str,
    source_path: Path,
    prd_path: Path,
    stage_paths: list[Path],
    convergence_evidence_path: Path | None,
    chosen_round: dict[str, object] | None,
    passed_round: int | None,
) -> dict[str, object]:
    stage_map = resolve_stage_map(stage_paths)
    output_dir = prd_path.parent.resolve()
    depth_runtime_summary = load_phase1_depth_runtime_summary(output_dir)
    agentic_loop_plan = load_phase1_agentic_loop_plan(output_dir)
    depth_runtime_texts = [read_text(output_dir / artifact_name) for artifact_name in DEPTH_RUNTIME_TEXT_ARTIFACTS]
    prd_text = read_text(prd_path)
    source_text = read_text(source_path)
    evidence_text = read_text(convergence_evidence_path)
    texts = [
        source_text,
        prd_text,
        evidence_text,
        *depth_runtime_texts,
        *(read_text(stage_map.get(key)) for key in ("stage_01", "stage_02a", "stage_02b", "stage_03", "stage_04")),
    ]
    combined_text = "\n".join(texts)
    gate_map = gate_map_from_round(chosen_round)
    depth_core_scenario_count = (
        int(depth_runtime_summary.get("core_scenario_count", 0))
        if isinstance(depth_runtime_summary, dict)
        else 0
    )
    depth_scenario_status = (
        str(depth_runtime_summary.get("scenario_set_status", "")).upper()
        if isinstance(depth_runtime_summary, dict)
        else ""
    )
    depth_scenario_judgment = (
        str(depth_runtime_summary.get("scenario_set_judgment", "")).strip()
        if isinstance(depth_runtime_summary, dict)
        else ""
    )
    depth_baseline_status = (
        str(depth_runtime_summary.get("baseline_calibration_status", "")).upper()
        if isinstance(depth_runtime_summary, dict)
        else ""
    )
    depth_posture = (
        str(depth_runtime_summary.get("depth_posture", "")).strip()
        if isinstance(depth_runtime_summary, dict)
        else ""
    )
    depth_baseline_judgment = (
        str(depth_runtime_summary.get("baseline_calibration_judgment", "")).strip()
        if isinstance(depth_runtime_summary, dict)
        else ""
    )
    ordinary_real_world_baseline_met = bool(depth_runtime_summary.get("ordinary_real_world_baseline_met", False)) if isinstance(depth_runtime_summary, dict) else False
    depth_artifact_count = sum(1 for artifact_name in DEPTH_RUNTIME_TEXT_ARTIFACTS if (output_dir / artifact_name).exists())

    scenario_count = max(
        count_matches(prd_text, r"####\s+Scenario\s+[A-Z0-9]+"),
        count_matches(prd_text, r"Key-path Scenario\s+\d+"),
        count_matches(prd_text, r"Scenario\s+[A-Z]:"),
        depth_core_scenario_count,
    )
    acceptance_count = count_matches(prd_text, r"\bAC[-_ ]?\d+\b")
    given_count = count_matches(prd_text, r"\bGiven\b")
    operationally_rich = detect_operationally_rich_domain(source_text + "\n" + prd_text)
    calibration_present = has_signal(
        texts,
        r"real-world baseline|baseline calibration|ordinary real-world|现实世界一般水平|真实世界一般水平|现实世界校准",
    ) or depth_baseline_status in {"PASS", "REVIEW-BOUND"}
    validation_signal_present = has_signal(
        texts,
        r"field validation|real evidence|real-world evidence|interview|walkthrough|用户验证|访谈|真实用户信号|现场验证",
        r"validation target|Validation Strategy|Method and Signal Definition|validation method|验证目标|验证方法",
    )
    key_scenario_deep = has_signal(texts, r"Key Scenario Deep Analysis", r"####\s+Scenario\s+[A-Z0-9]+", r"Key-path Scenario") or depth_core_scenario_count >= 2
    business_scenarios_present = has_signal(texts, r"Business Scenarios", r"Scenario Decomposition", r"Persona Context Scenario")
    flow_present = has_signal(texts, r"complete_experience_loop", r"Operational Flow", r"Business Process", r"main flow")
    constraints_present = has_signal(texts, r"Constraints", r"Architectural Constraints", r"Key constraints", r"约束")
    review_bound_present = has_signal(texts, r"review-bound", r"forbidden assumptions", r"unresolved truth", r"evidence_confidence_state")
    deferred_present = has_signal(texts, r"Deferred Items", r"deferred_items", r"\bdeferred\b")
    handoff_present = has_signal(texts, r"Handoff to Design / Architecture", r"Design Can Start", r"Architecture Can Start")
    validation_strategy_present = has_signal(texts, r"Validation Strategy", r"Validation Targets", r"Method and Signal Definition")
    quality_scenario_present = has_signal(texts, r"Quality Scenario Matrix", r"quality requirements", r"NFR")
    state_or_exception_present = has_signal(texts, r"state", r"状态", r"error", r"invalid_state_transition", r"blocked")
    placeholder_present = has_signal(texts, r"\bmissing\b", r"\bTODO\b", r"\btbd\b", r"to be determined")
    business_value_mechanism_present = has_signal(texts, r"business_value_mechanism", r"value mechanism", r"价值机制")
    decision_leverage_present = has_signal(texts, r"decision_leverage", r"continue / revise / pause", r"继续 / 调整 / 暂停")
    buyer_budget_chain_present = has_signal(
        texts,
        r"buyer_budget_chain",
        r"Buyer / Budget / Continuation Chain",
        r"proof_artifact_for_continue",
        r"continuation_owner",
        r"spend_at_risk",
    )
    pricing_validation_present = has_signal(
        texts,
        r"Pricing Validation Design",
        r"pricing_hypothesis",
        r"willingness-to-pay",
        r"pilot quote",
        r"预算|定价|付费意愿",
    )
    user_task_experience_present = has_signal(
        texts,
        r"user_task_experience",
        r"user_task_experience_gain",
        r"handoff friction",
        r"manual reconstruction",
        r"duplicate entry",
        r"等待|交接|补录|重复输入",
    )
    delivery_state = extract_named_state(prd_text, "document_delivery_state")
    evidence_state = extract_named_state(prd_text, "evidence_confidence_state")
    commercial_posture = depth_posture in {"commercial-decision", "mixed"}

    dimension_rows = [
        {
            "key": "business_baseline_and_scenario_set",
            "label": "业务基线与场景集充分性",
            "weight": 25,
            "score": clamp_dimension(
                int(scenario_count >= 3)
                + int(key_scenario_deep)
                + int(business_scenarios_present)
                + int(flow_present)
                + int((not operationally_rich) or calibration_present or validation_signal_present)
            ),
            "notes": [
                f"scenario_count={scenario_count}",
                "key scenario deep analysis visible" if key_scenario_deep else "key scenario deep analysis still weak",
                "operationally rich domain" if operationally_rich else "ordinary-density domain",
                (
                    "baseline calibration / field validation signal present"
                    if (calibration_present or validation_signal_present)
                    else "baseline calibration signal still weak"
                ),
            ],
        },
        {
            "key": "scenario_depth_and_executability",
            "label": "场景深度与可执行性",
            "weight": 20,
            "score": clamp_dimension(
                int(acceptance_count >= 8)
                + int(given_count >= 8)
                + int(gate_verdict(gate_map, "stage_artifact_depth_gate") == "PASS")
                + int(gate_verdict(gate_map, "executability_gate") == "PASS")
                + int(quality_scenario_present or state_or_exception_present)
            ),
            "notes": [
                f"acceptance_count={acceptance_count}",
                f"given_rows~={given_count}",
                f"stage_depth_gate={gate_verdict(gate_map, 'stage_artifact_depth_gate')}",
                f"executability_gate={gate_verdict(gate_map, 'executability_gate')}",
            ],
        },
        {
            "key": "business_value_and_process_experience",
            "label": "业务价值机制与流程体验",
            "weight": 10,
            "score": clamp_dimension(
                int(business_value_mechanism_present)
                + int(decision_leverage_present)
                + int(user_task_experience_present)
                + int((not commercial_posture) or pricing_validation_present)
                + int((not commercial_posture) or buyer_budget_chain_present)
            ),
            "notes": [
                "value mechanism explicit" if business_value_mechanism_present else "value mechanism still weak",
                "decision leverage explicit" if decision_leverage_present else "decision leverage still weak",
                "user task/process experience explicit" if user_task_experience_present else "user task/process experience still weak",
                "pricing validation explicit" if pricing_validation_present or not commercial_posture else "pricing validation still weak",
                "buyer/budget chain explicit" if buyer_budget_chain_present or not commercial_posture else "buyer/budget chain still weak",
            ],
        },
        {
            "key": "phase2_consumability",
            "label": "P2 可消费性",
            "weight": 20,
            "score": clamp_dimension(
                int(gate_verdict(gate_map, "quality_gate") == "PASS")
                + int(gate_verdict(gate_map, "assembly_integrity_gate") == "PASS")
                + int(gate_verdict(gate_map, "executability_gate") == "PASS")
                + int(handoff_present)
                + int(bool(delivery_state))
            ),
            "notes": [
                f"quality_gate={gate_verdict(gate_map, 'quality_gate')}",
                f"assembly_integrity_gate={gate_verdict(gate_map, 'assembly_integrity_gate')}",
                f"executability_gate={gate_verdict(gate_map, 'executability_gate')}",
                "handoff section explicit" if handoff_present else "handoff section weak or missing",
            ],
        },
        {
            "key": "evidence_calibration_and_honesty",
            "label": "证据/现实校准/诚实度",
            "weight": 15,
            "score": clamp_dimension(
                int(bool(evidence_state))
                + int(review_bound_present)
                + int(bool(evidence_text) and gate_verdict(gate_map, "analysis_delta_gate") == "PASS")
                + int(validation_strategy_present)
                + int((not operationally_rich) or calibration_present or validation_signal_present)
            ),
            "notes": [
                f"evidence_confidence_state={evidence_state or 'not-explicit'}",
                "review-bound honesty visible" if review_bound_present else "review-bound honesty weak",
                f"analysis_delta_gate={gate_verdict(gate_map, 'analysis_delta_gate')}",
            ],
        },
        {
            "key": "mainline_discipline",
            "label": "主线纪律与 optional 分层",
            "weight": 10,
            "score": clamp_dimension(
                int(bool(delivery_state))
                + int(has_signal(texts, r"MVP Definition & Scope", r"MVP Scope"))
                + int(constraints_present)
                + int(review_bound_present and deferred_present)
                + int(not placeholder_present)
            ),
            "notes": [
                f"document_delivery_state={delivery_state or 'not-explicit'}",
                "deferred/review-bound explicit" if review_bound_present and deferred_present else "optional layering still weak",
                "no obvious placeholder residue" if not placeholder_present else "placeholder residue still visible",
            ],
        },
    ]

    acceptance_rows: list[dict[str, str]] = []
    acceptance_rows.append(
        {
            "key": "prd_main_document_and_integrity",
            "label": "主 PRD 存在且自洽",
            "status": "PASS" if prd_path.exists() and gate_verdict(gate_map, "assembly_integrity_gate") == "PASS" else "BLOCKED",
            "why": (
                "PRD exists and assembly integrity gate passed"
                if prd_path.exists() and gate_verdict(gate_map, "assembly_integrity_gate") == "PASS"
                else "PRD missing or assembly integrity still blocked"
            ),
        }
    )
    if depth_scenario_status in {"PASS", "REVIEW-BOUND", "BLOCKED"}:
        scenario_status = depth_scenario_status
        scenario_why = depth_scenario_judgment or "scenario-set judgment was derived from explicit depth runtime artifacts"
    elif scenario_count >= 3 and key_scenario_deep and acceptance_count >= 8:
        scenario_status = "PASS"
        scenario_why = "core scenarios are not title-level and are supported by structured deepening"
    elif scenario_count >= 2 and key_scenario_deep:
        scenario_status = "REVIEW-BOUND"
        scenario_why = "core scenarios exist but still look somewhat thin for high-confidence downstream handoff"
    else:
        scenario_status = "BLOCKED"
        scenario_why = "core scenarios are still too thin or too few to prevent downstream invention"
    acceptance_rows.append(
        {
            "key": "core_scenarios_not_title_level",
            "label": "核心场景不再标题级",
            "status": scenario_status,
            "why": scenario_why,
        }
    )
    if gate_verdict(gate_map, "executability_gate") == "PASS" and acceptance_count >= 8 and given_count >= 8:
        ac_status = "PASS"
        ac_why = "acceptance criteria are executable and sufficiently explicit"
    elif gate_verdict(gate_map, "executability_gate") == "PASS" and acceptance_count >= 6:
        ac_status = "REVIEW-BOUND"
        ac_why = "acceptance criteria are usable but still not fully strong on boundary density"
    else:
        ac_status = "BLOCKED"
        ac_why = "acceptance criteria remain too weak for safe downstream execution"
    acceptance_rows.append(
        {
            "key": "acceptance_criteria_actionable",
            "label": "验收标准可被下游消费",
            "status": ac_status,
            "why": ac_why,
        }
    )
    scope_signals = int(has_signal(texts, r"MVP Definition & Scope", r"MVP Scope")) + int(constraints_present) + int(review_bound_present)
    acceptance_rows.append(
        {
            "key": "scope_constraints_review_bound_explicit",
            "label": "范围、约束、review-bound 项显式",
            "status": "PASS" if scope_signals == 3 else "REVIEW-BOUND" if scope_signals >= 2 else "BLOCKED",
            "why": (
                "scope boundary, constraints, and review-bound carryover are all explicit"
                if scope_signals == 3
                else "main scope/constraint semantics exist but still need cleaner explicitness"
                if scope_signals >= 2
                else "scope/constraint/review-bound carryover is too implicit"
            ),
        }
    )
    if operationally_rich and depth_baseline_status in {"PASS", "REVIEW-BOUND", "BLOCKED"}:
        calibration_status = depth_baseline_status
        calibration_why = depth_baseline_judgment or "baseline calibration judgment was derived from explicit depth runtime artifacts"
    elif not operationally_rich:
        calibration_status = "PASS"
        calibration_why = "the domain does not require the stronger operational-density calibration baseline"
    elif calibration_present:
        calibration_status = "PASS"
        calibration_why = "real-world baseline calibration is explicit"
    elif validation_signal_present and review_bound_present:
        calibration_status = "REVIEW-BOUND"
        calibration_why = "field validation / real-evidence posture is visible, but explicit baseline calibration is still not strong enough"
    else:
        calibration_status = "BLOCKED"
        calibration_why = "operationally rich domain still lacks a credible real-world baseline calibration posture"
    acceptance_rows.append(
        {
            "key": "real_world_baseline_calibration",
            "label": "高业务密度场景完成现实世界基线校准",
            "status": calibration_status,
            "why": calibration_why,
        }
    )
    if commercial_posture:
        if business_value_mechanism_present and decision_leverage_present and buyer_budget_chain_present and pricing_validation_present:
            value_status = "PASS"
            value_why = "value mechanism, continuation decision, pricing validation, and buyer/budget truth are all explicit enough for downstream business judgment"
        elif business_value_mechanism_present and (decision_leverage_present or buyer_budget_chain_present):
            value_status = "REVIEW-BOUND"
            value_why = "business value is visible, but continuation logic or pricing/budget truth is still too review-bound for a confident commercial freeze"
        else:
            value_status = "BLOCKED"
            value_why = "commercial posture still lacks enough value-mechanism or continuation-truth explicitness"
    else:
        if business_value_mechanism_present and (user_task_experience_present or decision_leverage_present):
            value_status = "PASS"
            value_why = "business value mechanism is explicit and the PRD also explains how the real operator path becomes easier or more decision-ready"
        elif business_value_mechanism_present:
            value_status = "REVIEW-BOUND"
            value_why = "business value is visible, but operator-path benefit or downstream decision leverage is still somewhat thin"
        else:
            value_status = "BLOCKED"
            value_why = "the PRD still describes workflow structure without making the business value mechanism explicit enough"
    acceptance_rows.append(
        {
            "key": "business_value_and_decision_truth_explicit",
            "label": "业务价值机制与关键决策真相显式",
            "status": value_status,
            "why": value_why,
        }
    )
    if gate_verdict(gate_map, "executability_gate") == "PASS" and gate_verdict(gate_map, "quality_gate") == "PASS" and handoff_present:
        handoff_status = "PASS"
        handoff_why = "Phase-2 can consume the PRD without reconstructing the product world"
    elif gate_verdict(gate_map, "executability_gate") == "PASS" and handoff_present:
        handoff_status = "REVIEW-BOUND"
        handoff_why = "Phase-2 can start, but some handoff truth still remains review-bound"
    else:
        handoff_status = "BLOCKED"
        handoff_why = "Phase-2 would still need to invent core product truth"
    acceptance_rows.append(
        {
            "key": "phase2_handoff_safe",
            "label": "P2 不需要再发明关键产品真相",
            "status": handoff_status,
            "why": handoff_why,
        }
    )

    total_score = round(sum((row["score"] / 5) * row["weight"] for row in dimension_rows), 1)
    blockers_count = sum(1 for row in acceptance_rows if row["status"] == "BLOCKED")
    review_bound_items_count = sum(1 for row in acceptance_rows if row["status"] == "REVIEW-BOUND")
    min_dimension_score = min((row["score"] for row in dimension_rows), default=0)
    agentic_loop_target_count = int(agentic_loop_plan.get("target_count", 0)) if isinstance(agentic_loop_plan, dict) else 0
    agentic_loop_active_pass = str(agentic_loop_plan.get("active_pass", "")).strip() if isinstance(agentic_loop_plan, dict) else ""
    agentic_loop_deferred_focus_areas = (
        [str(item).strip() for item in agentic_loop_plan.get("deferred_focus_areas", []) if str(item).strip()]
        if isinstance(agentic_loop_plan, dict)
        else []
    )
    same_run_required = bool(
        build_same_run_deepening_signal(
            {
                "depth_mode": depth_mode,
                "depth_posture": depth_posture,
                "baseline_calibration_status": depth_baseline_status,
                "agentic_loop_target_count": agentic_loop_target_count,
                "agentic_loop_active_pass": agentic_loop_active_pass,
                "agentic_loop_focus_areas": list(agentic_loop_plan.get("focus_areas", []))
                if isinstance(agentic_loop_plan, dict)
                else [],
                "agentic_loop_deferred_focus_areas": agentic_loop_deferred_focus_areas,
            }
        )
    )

    if passed_round is None:
        verdict = "BLOCKED"
    elif same_run_required:
        verdict = "RETURN-REMEDIATE"
    elif blockers_count > 0:
        verdict = "RETURN-REMEDIATE"
    elif total_score >= 80 and min_dimension_score >= 3:
        verdict = "PASS with review-bound items" if review_bound_items_count > 0 or (evidence_state or "").lower() == "review-bound" else "PASS"
    elif total_score >= 70:
        verdict = "PASS with review-bound items"
    else:
        verdict = "RETURN-REMEDIATE"

    return {
        "phase": "P1",
        "depth_mode": depth_mode,
        "depth_posture": depth_posture or "not-explicit",
        "operationally_rich_domain": operationally_rich,
        "scenario_count": scenario_count,
        "acceptance_count": acceptance_count,
        "given_count": given_count,
        "dimension_scores": dimension_rows,
        "acceptance_rows": acceptance_rows,
        "total_score": total_score,
        "verdict": verdict,
        "review_bound_items_count": review_bound_items_count,
        "blockers_count": blockers_count,
        "document_delivery_state": delivery_state,
        "evidence_confidence_state": evidence_state,
        "baseline_calibration_status": depth_baseline_status or "not-explicit",
        "baseline_calibration_judgment": depth_baseline_judgment,
        "ordinary_real_world_baseline_met": ordinary_real_world_baseline_met,
        "depth_runtime_summary_present": isinstance(depth_runtime_summary, dict),
        "depth_runtime_artifact_count": depth_artifact_count,
        "agentic_loop_plan_present": isinstance(agentic_loop_plan, dict),
        "agentic_loop_target_count": agentic_loop_target_count,
        "agentic_loop_active_pass": agentic_loop_active_pass,
        "agentic_loop_focus_areas": list(agentic_loop_plan.get("focus_areas", [])) if isinstance(agentic_loop_plan, dict) else [],
        "agentic_loop_deferred_focus_areas": agentic_loop_deferred_focus_areas,
        "same_run_required": same_run_required,
    }


def resolve_stage_map(stage_paths: list[Path]) -> dict[str, Path]:
    stage_map: dict[str, Path] = {}
    for stage_path in stage_paths:
        key = infer_stage_key(stage_path)
        if key:
            stage_map[key] = stage_path
    return stage_map


def derive_convergence_artifact_paths(prd_path: Path) -> tuple[Path, Path]:
    assembled = prd_path.parent / ".phase1-evidence" / f"{prd_path.stem}-assembled{prd_path.suffix}"
    evidence = prd_path.with_name(f"{prd_path.stem}-convergence-evidence{prd_path.suffix}")
    return assembled, evidence


def infer_stage_02b_skip_state(stage_map: dict[str, Path]) -> bool:
    for key, pattern in (
        ("stage_04", r"stage_02b_execution_state:\s*(?:\n\s*-\s*)?`?skipped`?"),
        ("stage_02b", r"execution_state:\s*`?skipped`?"),
    ):
        path = stage_map.get(key)
        if not path or not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            return True
    return False


def remediation_sections_for_gate(gate_name: str) -> list[str]:
    if gate_name == "quality_gate":
        return [
            "Problem Statement",
            "Target Users & Key Roles",
            "Requirements Structure",
            "MVP Definition & Scope",
            "Validation Strategy & Current Conclusion",
        ]
    if gate_name == "assembly_integrity_gate":
        return [
            "Integrated synthesis",
            "Source Artifacts chain",
            "anti-mirror convergence",
        ]
    if gate_name == "analysis_delta_gate":
        return [
            "Analysis Delta Ledger",
            "Key Decision Rationale Summary",
        ]
    if gate_name == "executability_gate":
        return [
            "Requirements Structure",
            "Information Architecture Direction",
            "MVP Definition & Scope",
            "Validation Strategy & Current Conclusion",
            "Handoff to Design / Architecture",
        ]
    if gate_name == "stage_artifact_depth_gate":
        return [
            "stage depth and method-activation evidence",
        ]
    if gate_name == "section_scoring_gate":
        return [
            "Problem Statement",
            "Target Users & Key Roles",
            "Business Scenarios",
            "Requirements Structure",
            "NFR / Quality Requirements",
            "Domain Model",
            "Information Architecture Direction",
            "MVP Definition & Scope",
            "Validation Strategy & Current Conclusion",
            "Handoff to Design / Architecture",
        ]
    return []


def remediation_consumers_for_gate(gate_name: str) -> list[str]:
    if gate_name in {"quality_gate", "analysis_delta_gate"}:
        return ["product-review", "design", "architecture"]
    if gate_name == "executability_gate":
        return ["design", "architecture", "handoff"]
    if gate_name == "assembly_integrity_gate":
        return ["product-review", "handoff"]
    if gate_name == "stage_artifact_depth_gate":
        return ["runtime-depth", "handoff"]
    if gate_name == "section_scoring_gate":
        return ["product-review", "design", "architecture", "handoff"]
    return []


def build_same_run_deepening_signal(assessment: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(assessment, dict):
        return None
    if str(assessment.get("depth_mode", "")).strip() != "baseline":
        return None

    depth_posture = str(assessment.get("depth_posture", "")).strip()
    focus_areas = [
        str(item).strip()
        for item in assessment.get("agentic_loop_focus_areas", [])
        if str(item).strip()
    ]
    deferred_focus_areas = [
        str(item).strip()
        for item in assessment.get("agentic_loop_deferred_focus_areas", [])
        if str(item).strip()
    ]
    active_pass = str(assessment.get("agentic_loop_active_pass", "")).strip()
    commercial_posture = depth_posture in {"commercial-decision", "mixed"}
    if active_pass != "business_world_sufficiency" and not commercial_posture:
        return None
    target_count = int(assessment.get("agentic_loop_target_count", 0) or 0)
    baseline_status = str(assessment.get("baseline_calibration_status", "")).strip().upper()
    reasons: list[str] = []
    sections_to_deepen: list[str] = []
    consumer_problems: list[str] = []

    if active_pass == "business_world_sufficiency" and target_count > 0:
        sections_to_deepen.extend(
            [
                "Business Scenarios",
                "Operational Flow Specification",
                "State Machine and Transition Rules",
                "Acceptance Criteria",
                "Validation Strategy & Current Conclusion",
            ]
        )
        if "scenario_family" in focus_areas:
            sections_to_deepen.append("MVP Definition & Scope")
        if any(focus in {"business_value", "user_task_experience"} for focus in focus_areas):
            sections_to_deepen.append("Decision Options and Tradeoffs")
        consumer_problems.extend(
            [
                "product strategy still depends on a business world that is too thin or too demo-like",
                "design should not invent the mainline steps, states, handoffs, or boundary truth",
                "architecture should not guess the real-world baseline, operating constraints, or downstream contracts",
            ]
        )
        if baseline_status in {"REVIEW-BOUND", "BLOCKED"}:
            reasons.append(
                "business-world baseline calibration is not yet PASS, so the runtime must keep deepening within the same run"
            )
        reasons.append(
            "business-world sufficiency is still the active pass, so the runtime must finish that closeout inside the same run"
        )
    elif active_pass == "value_mechanism_clarity" and target_count > 0:
        sections_to_deepen.extend(
            [
                "Business Scenarios",
                "Validation Strategy & Current Conclusion",
                "Decision Options and Tradeoffs",
            ]
        )
        consumer_problems.extend(
            [
                "product strategy still needs stronger value truth",
                "design should not invent why the workflow creates business value",
                "architecture should not guess the continue/revise decision semantics before value mechanism is explicit",
            ]
        )
        reasons.append(
            "value mechanism clarity is still the active pass, so buyer/budget convergence must remain downstream in the same run"
        )
    elif active_pass == "buyer_budget_continuation_chain" and target_count > 0:
        sections_to_deepen.extend(
            [
                "Business Scenarios",
                "Validation Strategy & Current Conclusion",
                "Decision Options and Tradeoffs",
                "Pricing Validation Design",
            ]
        )
        consumer_problems.extend(
            [
                "product strategy still needs stronger continuation truth",
                "design should not invent why the workflow deserves continued investment",
                "architecture should not guess the buyer/budget or continue/revise decision semantics",
            ]
        )
        reasons.append(
            "buyer/budget/continuation logic is still the active pass, so the runtime must finish that convergence inside the same run"
        )

    if commercial_posture and baseline_status in {"REVIEW-BOUND", "BLOCKED"} and active_pass != "business_world_sufficiency":
        reasons.append(
            "commercial baseline calibration is not yet PASS, so the runtime must keep deepening within the same run"
        )

    if active_pass == "business_world_sufficiency":
        unresolved_focus = [
            focus for focus in focus_areas if focus in BUSINESS_WORLD_SAME_RUN_DEEPENING_FOCUS_AREAS
        ]
    else:
        unresolved_focus = [
            focus for focus in focus_areas if focus in COMMERCIAL_SAME_RUN_DEEPENING_FOCUS_AREAS
        ]
    if target_count > 0 and unresolved_focus and (
        active_pass in {
            "business_world_sufficiency",
            "value_mechanism_clarity",
            "buyer_budget_continuation_chain",
        }
        or (commercial_posture and baseline_status in {"REVIEW-BOUND", "BLOCKED"})
    ):
        reasons.append(
            "agentic loop still carries unresolved same-run deepening targets: "
            + ", ".join(unresolved_focus)
        )
    if deferred_focus_areas:
        reasons.append(
            "later-pass focus remains deferred until the active pass clears: " + ", ".join(deferred_focus_areas)
        )

    if not reasons:
        return None

    return {
        "required": True,
        "active_pass": active_pass,
        "sections_to_deepen": list(dict.fromkeys(sections_to_deepen or [
            "Business Scenarios",
            "Validation Strategy & Current Conclusion",
            "Decision Options and Tradeoffs",
            "Pricing Validation Design",
        ])),
        "consumer_problems": list(dict.fromkeys(consumer_problems or [
            "product strategy still needs stronger value truth",
            "design should not invent why the workflow deserves continued investment",
            "architecture should not guess the buyer/budget or continue/revise decision semantics",
        ])),
        "rationale": reasons,
        "loop_focus_areas": focus_areas,
        "deferred_focus_areas": deferred_focus_areas,
        "refresh_stage_outputs": bool(set(focus_areas) & SAME_RUN_STAGE_REFRESH_FOCUS_AREAS),
        "reassemble_prd": True,
    }


def build_remediation_plan(
    failed_gates: list[str],
    stage_paths: list[Path],
    prd_path: Path | None = None,
    same_run_deepening: dict[str, object] | None = None,
) -> dict[str, object] | None:
    if not failed_gates and not same_run_deepening:
        return None

    sections: list[str] = []
    consumers: list[str] = []
    rationale: list[str] = []
    refresh_stage_outputs = False
    reassemble_prd = False
    output_dir = infer_output_dir(prd_path, stage_paths) if prd_path is not None else (stage_paths[0].parent.resolve() if stage_paths else None)
    loop_plan = load_phase1_agentic_loop_plan(output_dir) if output_dir is not None else None

    for gate_name in failed_gates:
        sections.extend(remediation_sections_for_gate(gate_name))
        consumers.extend(remediation_consumers_for_gate(gate_name))
        if gate_name == "stage_artifact_depth_gate":
            refresh_stage_outputs = True
            reassemble_prd = True
            rationale.append("stage artifacts are too thin or missing required runtime signals")
        elif gate_name in {
            "quality_gate",
            "assembly_integrity_gate",
            "analysis_delta_gate",
            "executability_gate",
        }:
            reassemble_prd = True
            rationale.append(f"{gate_name} indicates the assembled PRD still needs convergence deepening")

    if isinstance(same_run_deepening, dict):
        sections.extend(str(item).strip() for item in same_run_deepening.get("sections_to_deepen", []) if str(item).strip())
        consumers.extend(str(item).strip() for item in same_run_deepening.get("consumer_problems", []) if str(item).strip())
        rationale.extend(str(item).strip() for item in same_run_deepening.get("rationale", []) if str(item).strip())
        refresh_stage_outputs = refresh_stage_outputs or bool(same_run_deepening.get("refresh_stage_outputs"))
        reassemble_prd = reassemble_prd or bool(same_run_deepening.get("reassemble_prd", True))

    if not refresh_stage_outputs and not reassemble_prd:
        return None

    dedup_sections = list(dict.fromkeys(sections))
    dedup_consumers = list(dict.fromkeys(consumers))
    loop_focus_areas = []
    loop_targets = []
    loop_round_focus = ""
    loop_plan_path = ""
    loop_active_pass = ""
    if isinstance(loop_plan, dict):
        loop_focus_areas = [str(item).strip() for item in loop_plan.get("focus_areas", []) if str(item).strip()]
        loop_targets = [
            str(item.get("scenario_title", "")).strip()
            for item in loop_plan.get("targets", [])
            if isinstance(item, dict) and str(item.get("scenario_title", "")).strip()
        ]
        loop_round_focus = str(loop_plan.get("round_focus", "")).strip()
        loop_plan_path = str((output_dir / AGENTIC_LOOP_PLAN_FILENAME).resolve()) if output_dir is not None else ""
        loop_active_pass = str(loop_plan.get("active_pass", "")).strip()
    if isinstance(same_run_deepening, dict):
        loop_focus_areas = list(
            dict.fromkeys(
                loop_focus_areas
                + [
                    str(item).strip()
                    for item in same_run_deepening.get("loop_focus_areas", [])
                    if str(item).strip()
                ]
            )
        )
        if not loop_active_pass:
            loop_active_pass = str(same_run_deepening.get("active_pass", "")).strip()
    return {
        "refresh_stage_outputs": refresh_stage_outputs and bool(stage_paths),
        "reassemble_prd": reassemble_prd and bool(stage_paths),
        "sections_to_deepen": dedup_sections,
        "consumer_problems": dedup_consumers,
        "rationale": rationale,
        "loop_plan_path": loop_plan_path,
        "loop_active_pass": loop_active_pass,
        "loop_focus_areas": loop_focus_areas,
        "loop_target_count": len(loop_targets),
        "loop_target_scenarios": loop_targets[:5],
        "loop_round_focus": loop_round_focus,
    }


def execute_remediation_plan(
    plan: dict[str, object],
    *,
    source_path: Path,
    prd_path: Path,
    stage_paths: list[Path],
    script_dir: Path,
    python: str,
    profile: str,
    document_name: str | None,
    depth_mode: str,
    thinking_value_gain_mode: str = "off",
    output_locale: str | None = None,
) -> dict[str, object]:
    stage_map = resolve_stage_map(stage_paths)
    output_dir = infer_output_dir(prd_path, stage_paths)
    assembled_prd_path, convergence_evidence_path = derive_convergence_artifact_paths(prd_path)
    version = infer_trial_token_from_paths([prd_path, *stage_paths])
    if not version:
        return {
            "ok": False,
            "message": "cannot infer trial version for remediation",
            "actions": [],
        }

    actions: list[dict[str, object]] = []

    if plan.get("refresh_stage_outputs"):
        generator_cmd = [
            python,
            str(resolve_phase1_script(script_dir, "phase1_generate_deep_stage_outputs.py")),
            "--source",
            str(source_path),
            "--output-dir",
            str(output_dir),
            "--version",
            version,
            "--owner",
            "Codex convergence-remediation",
        ]
        if output_locale:
            generator_cmd.extend(["--output-locale", str(output_locale)])
        if thinking_value_gain_mode != "off":
            generator_cmd.extend(["--thinking-value-gain-mode", thinking_value_gain_mode])
        if infer_stage_02b_skip_state(stage_map):
            generator_cmd.append("--skip-stage-02b")
        result = run_command(generator_cmd)
        actions.append(
            {
                "type": "refresh_stage_outputs",
                "command": " ".join(generator_cmd),
                "returncode": result["returncode"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
            }
        )
        if result["returncode"] != 0:
            return {
                "ok": False,
                "message": "stage refresh failed",
                "actions": actions,
            }

    if plan.get("reassemble_prd"):
        required_stage_keys = ("stage_01", "stage_02a", "stage_03", "stage_04")
        if any(key not in stage_map for key in required_stage_keys):
            return {
                "ok": False,
                "message": "cannot reassemble PRD because required stage files are missing",
                "actions": actions,
            }
        assembled_name = document_name or first_markdown_title(prd_path) or "Phase-1 PRD Main Document"
        assemble_cmd = [
            python,
            str(resolve_phase1_script(script_dir, "phase1_assemble_prd.py")),
            "--source",
            str(source_path),
            "--stage-01",
            str(stage_map["stage_01"]),
            "--stage-02a",
            str(stage_map["stage_02a"]),
            "--stage-03",
            str(stage_map["stage_03"]),
            "--stage-04",
            str(stage_map["stage_04"]),
            "--output",
            str(assembled_prd_path),
            "--version",
            version,
            "--document-name",
            assembled_name,
            "--profile",
            profile,
            "--output-locale",
            resolve_output_locale(output_locale),
        ]
        loop_plan_path = str(plan.get("loop_plan_path", "")).strip()
        if loop_plan_path:
            assemble_cmd.extend(["--loop-plan", loop_plan_path])
        if "stage_02b" in stage_map:
            assemble_cmd.extend(["--stage-02b", str(stage_map["stage_02b"])])
        result = run_command(assemble_cmd)
        actions.append(
            {
                "type": "reassemble_prd",
                "command": " ".join(assemble_cmd),
                "returncode": result["returncode"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
            }
        )
        if result["returncode"] != 0:
            return {
                "ok": False,
                "message": "PRD reassembly failed",
                "actions": actions,
            }

        converge_cmd = [
            python,
            str(resolve_phase1_script(script_dir, "phase1_converge_prd.py")),
            "--assembled-prd",
            str(assembled_prd_path),
            "--output",
            str(prd_path),
            "--evidence-output",
            str(convergence_evidence_path),
            "--output-locale",
            resolve_output_locale(output_locale),
        ]
        result = run_command(converge_cmd)
        actions.append(
            {
                "type": "converge_prd",
                "command": " ".join(converge_cmd),
                "returncode": result["returncode"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
            }
        )
        if result["returncode"] != 0:
            return {
                "ok": False,
                "message": "PRD convergence failed",
                "actions": actions,
            }

        if "stage_02b" not in stage_map:
            return {
                "ok": False,
                "message": "depth runtime refresh requires stage-02b artifact",
                "actions": actions,
            }

        depth_runtime_cmd = [
            python,
            str(resolve_phase1_script(script_dir, "phase1_emit_depth_runtime_artifacts.py")),
            "--source",
            str(source_path),
            "--stage-01",
            str(stage_map["stage_01"]),
            "--stage-02a",
            str(stage_map["stage_02a"]),
            "--stage-02b",
            str(stage_map["stage_02b"]),
            "--stage-03",
            str(stage_map["stage_03"]),
            "--stage-04",
            str(stage_map["stage_04"]),
            "--prd",
            str(prd_path),
            "--output-dir",
            str(output_dir),
            "--version",
            version,
            "--owner",
            "Codex convergence-remediation",
            "--depth-mode",
            depth_mode,
            "--output-locale",
            resolve_output_locale(output_locale),
        ]
        result = run_command(depth_runtime_cmd)
        actions.append(
            {
                "type": "refresh_depth_runtime",
                "command": " ".join(depth_runtime_cmd),
                "returncode": result["returncode"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
            }
        )
        if result["returncode"] != 0:
            return {
                "ok": False,
                "message": "depth runtime refresh failed",
                "actions": actions,
            }

    return {
        "ok": True,
        "message": "remediation executed",
        "actions": actions,
        "prd": str(prd_path),
        "assembled_prd": str(assembled_prd_path),
        "convergence_evidence": str(convergence_evidence_path),
    }


def resolve_stage_paths(raw_stages: list[str], report_path: Path | None) -> list[Path]:
    resolved: list[Path] = []
    for stage in raw_stages:
        stage_path = Path(stage)
        if stage_path.is_absolute():
            resolved.append(stage_path.resolve())
            continue
        if report_path is not None:
            resolved.append((report_path.parent / stage_path).resolve())
        else:
            resolved.append(stage_path.resolve())
    return resolved


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def slugify(raw: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", raw.strip().lower())
    return value.strip("-") or "phase1-trace"


def extract_stage_artifact_id(path: Path, fallback: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(ARTIFACT_ID_FIELD_PATTERN, text, flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else fallback


def link_trace_artifact(
    *,
    python: str,
    trace_dir: Path,
    project_root: Path,
    project_key: str,
    from_id: str,
    to_id: str,
    link_type: str,
    source_path: str = "",
    evidence_anchor: str = "",
) -> dict[str, object]:
    command = [
        python,
        str(trace_dir / "link_artifacts.py"),
        "--project-root",
        str(project_root),
        "--project-key",
        project_key,
        "--from-artifact-id",
        from_id,
        "--to-artifact-id",
        to_id,
        "--link-type",
        link_type,
        "--source-path",
        source_path,
        "--evidence-anchor",
        evidence_anchor,
    ]
    return run_trace_registry_command_in_process(command) or run_command(command)


def bind_trace_artifact(
    *,
    python: str,
    trace_dir: Path,
    project_root: Path,
    project_key: str,
    artifact_id: str,
    artifact_type: str,
    source_path: str,
    source_anchor: str,
    stage_or_lane: str,
    status: str,
) -> dict[str, object]:
    command = [
        python,
        str(trace_dir / "bind_artifact.py"),
        "--project-root",
        str(project_root),
        "--project-key",
        project_key,
        "--artifact-id",
        artifact_id,
        "--artifact-type",
        artifact_type,
        "--source-path",
        source_path,
        "--source-anchor",
        source_anchor,
        "--stage-or-lane",
        stage_or_lane,
        "--status",
        status,
    ]
    return run_trace_registry_command_in_process(command) or run_command(command)


def artifact_type_for_phase1_trace_row(unit_group: str) -> str:
    return PHASE1_TRACE_UNIT_TYPE_MAP[unit_group]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase-1 convergence gates")
    parser.add_argument("--source", required=True)
    parser.add_argument("--report")
    parser.add_argument(
        "--convergence-evidence",
        help="optional external convergence evidence markdown carrying delta ledger/runtime trace",
    )
    parser.add_argument("--stage", action="append", default=[])
    parser.add_argument(
        "--profile",
        default="review-bound-starter-pack",
        choices=("review-bound-starter-pack", "implementation-ready-prd"),
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="hard cap of rounds to execute across provided PRD candidates",
    )
    parser.add_argument(
        "--require-non-shrinking",
        action="store_true",
        help="forwarded to quality gate",
    )
    parser.add_argument(
        "--depth-mode",
        choices=("baseline", "creative"),
        default="baseline",
        help="Phase-1 v1.2 depth mode; creative still needs baseline sufficiency first",
    )
    parser.add_argument("--thinking-value-gain-mode", choices=("off", "full-use"), default="off")
    parser.add_argument("--output-json")
    parser.add_argument(
        "--auto-remediate",
        action="store_true",
        help="on gate failure, regenerate stage outputs and/or reassemble PRD based on failed-gate mapping",
    )
    parser.add_argument("--output-locale", default=resolve_output_locale())

    prd_group = parser.add_mutually_exclusive_group(required=True)
    prd_group.add_argument("--prd")
    prd_group.add_argument("--prd-candidate", action="append")
    return parser


def parse_phase1_convergence_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def build_phase1_convergence_runtime_context(args: argparse.Namespace) -> Phase1ConvergenceRuntimeContext:
    script_dir = Path(__file__).resolve().parent
    python = sys.executable
    source_path = Path(args.source).resolve()
    report_path = Path(args.report).resolve() if args.report else None
    convergence_evidence_arg = Path(args.convergence_evidence).resolve() if args.convergence_evidence else None
    stage_paths = resolve_stage_paths(args.stage, report_path)
    candidates = [Path(args.prd).resolve()] if args.prd else [Path(item).resolve() for item in args.prd_candidate]

    if not candidates:
        raise ValueError("no PRD candidates provided")
    if args.auto_remediate and args.prd_candidate:
        raise ValueError("--auto-remediate currently supports only a single `--prd` entrypoint")

    return Phase1ConvergenceRuntimeContext(
        script_dir=script_dir,
        python=python,
        source_path=source_path,
        report_path=report_path,
        convergence_evidence_arg=convergence_evidence_arg,
        stage_paths=stage_paths,
        candidates=candidates[: int(args.max_rounds)],
        profile=str(args.profile),
        max_rounds=int(args.max_rounds),
        require_non_shrinking=bool(args.require_non_shrinking),
        depth_mode=str(args.depth_mode),
        thinking_value_gain_mode=str(getattr(args, "thinking_value_gain_mode", "off")),
        output_json_path=Path(args.output_json).resolve() if args.output_json else None,
        auto_remediate=bool(args.auto_remediate),
        output_locale=resolve_output_locale(args.output_locale),
    )


def print_phase1_convergence_runtime_start(context: Phase1ConvergenceRuntimeContext) -> None:
    print("== Phase-1 Convergence Runtime ==")
    print(f"source: {context.source_path}")
    print(f"profile: {context.profile}")
    print(f"depth_mode: {context.depth_mode}")
    print(f"thinking_value_gain_mode: {context.thinking_value_gain_mode}")
    if context.report_path:
        print(f"report: {context.report_path}")
    if context.stage_paths:
        print(f"stage_files: {len(context.stage_paths)}")
    print(f"round_candidates: {len(context.candidates)}")


def run_phase1_traceability_runtime(
    *,
    script_dir: Path,
    python: str,
    prd_path: Path,
    stage_paths: list[Path],
) -> dict[str, object]:
    project_root = prd_path.parent.resolve()
    project_key = slugify(project_root.name or prd_path.stem)
    trace_dir = resolve_wff_base_trace_scripts(
        project_root=project_root,
        fallback_roots=(script_dir, *script_dir.parents),
    )
    validation_path = resolve_cross_phase_surface_path(project_root, "phase1", "phase-1-traceability-validation.txt")
    report_text_path = resolve_cross_phase_surface_path(project_root, "phase1", "phase-1-traceability-report.txt")
    report_json_path = resolve_cross_phase_surface_path(project_root, "phase1", "phase-1-traceability-report.json")
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    report_text_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.parent.mkdir(parents=True, exist_ok=True)

    steps: list[dict[str, object]] = []

    steps.append(
        {
            "name": "init_registry",
            **run_command(
                [
                    python,
                    str(trace_dir / "init_registry.py"),
                    "--project-root",
                    str(project_root),
                    "--project-key",
                    project_key,
                    "--project-label",
                    prd_path.stem,
                ]
            ),
        }
    )
    if steps[-1]["returncode"] != 0:
        return {"ok": False, "message": "init_registry failed", "steps": steps}

    stage_map = resolve_stage_map(stage_paths)
    stage_bindings: list[tuple[str, Path, str]] = []
    for stage_key, path in stage_map.items():
        artifact_id = extract_stage_artifact_id(path, PHASE1_STAGE_TRACE_DEFAULTS.get(stage_key, "P1-OUT-UNKNOWN"))
        stage_bindings.append((stage_key, path, artifact_id))
        steps.append(
            {
                "name": f"bind_{stage_key}",
                **bind_trace_artifact(
                    python=python,
                    trace_dir=trace_dir,
                    project_root=project_root,
                    project_key=project_key,
                    artifact_id=artifact_id,
                    artifact_type="OUT",
                    source_path=relpath(path, project_root),
                    source_anchor=artifact_id.lower(),
                    stage_or_lane=stage_key.replace("_", "-"),
                    status="review",
                ),
            }
        )
        if steps[-1]["returncode"] != 0:
            return {"ok": False, "message": f"bind_{stage_key} failed", "steps": steps}

    steps.append(
        {
            "name": "bind_prd",
            **bind_trace_artifact(
                python=python,
                trace_dir=trace_dir,
                project_root=project_root,
                project_key=project_key,
                artifact_id=PHASE1_PRD_ARTIFACT_ID,
                artifact_type="PRD",
                source_path=relpath(prd_path, project_root),
                source_anchor="traceability-naming-and-registry",
                stage_or_lane="phase-1-prd",
                status="review",
            ),
        }
    )
    if steps[-1]["returncode"] != 0:
        return {"ok": False, "message": "bind_prd failed", "steps": steps}

    for stage_key, path, artifact_id in stage_bindings:
        steps.append(
            {
                "name": f"link_prd_depends_on_{stage_key}",
                **link_trace_artifact(
                    python=python,
                    trace_dir=trace_dir,
                    project_root=project_root,
                    project_key=project_key,
                    from_id=PHASE1_PRD_ARTIFACT_ID,
                    to_id=artifact_id,
                    link_type="depends_on",
                    source_path=relpath(prd_path, project_root),
                    evidence_anchor="traceability-naming-and-registry",
                ),
            }
        )
        if steps[-1]["returncode"] != 0:
            return {"ok": False, "message": f"link_prd_depends_on_{stage_key} failed", "steps": steps}

    stage_01 = stage_map.get("stage_01")
    stage_02a = stage_map.get("stage_02a")
    stage_03 = stage_map.get("stage_03")
    stage_04 = stage_map.get("stage_04")
    if stage_01 and stage_02a and stage_03 and stage_04:
        coarse_ids = [
            extract_stage_artifact_id(stage_01, PHASE1_STAGE_TRACE_DEFAULTS["stage_01"]),
            extract_stage_artifact_id(stage_02a, PHASE1_STAGE_TRACE_DEFAULTS["stage_02a"]),
            extract_stage_artifact_id(stage_03, PHASE1_STAGE_TRACE_DEFAULTS["stage_03"]),
            extract_stage_artifact_id(stage_04, PHASE1_STAGE_TRACE_DEFAULTS["stage_04"]),
        ]
        steps.append(
            {
                "name": "register_phase1_pilot",
                **run_command(
                    [
                        python,
                        str(trace_dir / "register_phase1_pilot.py"),
                        "--project-root",
                        str(project_root),
                        "--project-key",
                        project_key,
                        "--ids",
                        ",".join(coarse_ids),
                    ]
                ),
            }
        )
        if steps[-1]["returncode"] != 0:
            return {"ok": False, "message": "register_phase1_pilot failed", "steps": steps}

    if "stage_02b" in stage_map:
        stage_02b_id = extract_stage_artifact_id(stage_map["stage_02b"], PHASE1_STAGE_TRACE_DEFAULTS["stage_02b"])
        if stage_02a:
            steps.append(
                {
                    "name": "link_stage_02b_depends_on_stage_02a",
                    **link_trace_artifact(
                        python=python,
                        trace_dir=trace_dir,
                        project_root=project_root,
                        project_key=project_key,
                        from_id=stage_02b_id,
                        to_id=extract_stage_artifact_id(stage_02a, PHASE1_STAGE_TRACE_DEFAULTS["stage_02a"]),
                        link_type="depends_on",
                        source_path=relpath(stage_map["stage_02b"], project_root),
                        evidence_anchor=stage_02b_id.lower(),
                    ),
                }
            )
            if steps[-1]["returncode"] != 0:
                return {"ok": False, "message": "link_stage_02b_depends_on_stage_02a failed", "steps": steps}
        if stage_03:
            steps.append(
                {
                    "name": "link_stage_02b_feeds_stage_03",
                    **link_trace_artifact(
                        python=python,
                        trace_dir=trace_dir,
                        project_root=project_root,
                        project_key=project_key,
                        from_id=stage_02b_id,
                        to_id=extract_stage_artifact_id(stage_03, PHASE1_STAGE_TRACE_DEFAULTS["stage_03"]),
                        link_type="feeds",
                        source_path=relpath(stage_map["stage_02b"], project_root),
                        evidence_anchor=stage_02b_id.lower(),
                    ),
                }
            )
            if steps[-1]["returncode"] != 0:
                return {"ok": False, "message": "link_stage_02b_feeds_stage_03 failed", "steps": steps}
            steps.append(
                {
                    "name": "link_stage_03_depends_on_stage_02b",
                    **link_trace_artifact(
                        python=python,
                        trace_dir=trace_dir,
                        project_root=project_root,
                        project_key=project_key,
                        from_id=extract_stage_artifact_id(stage_03, PHASE1_STAGE_TRACE_DEFAULTS["stage_03"]),
                        to_id=stage_02b_id,
                        link_type="depends_on",
                        source_path=relpath(stage_03, project_root),
                        evidence_anchor=stage_02b_id.lower(),
                    ),
                }
            )
            if steps[-1]["returncode"] != 0:
                return {"ok": False, "message": "link_stage_03_depends_on_stage_02b failed", "steps": steps}
        if stage_04:
            steps.append(
                {
                    "name": "link_stage_02b_feeds_stage_04",
                    **link_trace_artifact(
                        python=python,
                        trace_dir=trace_dir,
                        project_root=project_root,
                        project_key=project_key,
                        from_id=stage_02b_id,
                        to_id=extract_stage_artifact_id(stage_04, PHASE1_STAGE_TRACE_DEFAULTS["stage_04"]),
                        link_type="feeds",
                        source_path=relpath(stage_map["stage_02b"], project_root),
                        evidence_anchor=stage_02b_id.lower(),
                    ),
                }
            )
            if steps[-1]["returncode"] != 0:
                return {"ok": False, "message": "link_stage_02b_feeds_stage_04 failed", "steps": steps}

    prd_text = prd_path.read_text(encoding="utf-8")
    phase1_units = extract_phase1_trace_units(prd_text)
    for unit_group, rows in phase1_units.items():
        artifact_type = artifact_type_for_phase1_trace_row(unit_group)
        for row in rows:
            artifact_id = row["trace_id"].strip()
            source_anchor = row.get("source_anchor", "").strip() or artifact_id.lower()
            steps.append(
                {
                    "name": f"bind_{artifact_id}",
                    **bind_trace_artifact(
                        python=python,
                        trace_dir=trace_dir,
                        project_root=project_root,
                        project_key=project_key,
                        artifact_id=artifact_id,
                        artifact_type=artifact_type,
                        source_path=relpath(prd_path, project_root),
                        source_anchor=source_anchor,
                        stage_or_lane="phase-1-prd-trace-unit",
                        status="review",
                    ),
                }
            )
            if steps[-1]["returncode"] != 0:
                return {"ok": False, "message": f"bind_{artifact_id} failed", "steps": steps}
            steps.append(
                {
                    "name": f"link_{artifact_id}_depends_on_prd",
                    **link_trace_artifact(
                        python=python,
                        trace_dir=trace_dir,
                        project_root=project_root,
                        project_key=project_key,
                        from_id=artifact_id,
                        to_id=PHASE1_PRD_ARTIFACT_ID,
                        link_type="depends_on",
                        source_path=relpath(prd_path, project_root),
                        evidence_anchor=source_anchor,
                    ),
                }
            )
            if steps[-1]["returncode"] != 0:
                return {"ok": False, "message": f"link_{artifact_id}_depends_on_prd failed", "steps": steps}

    validation = run_command(
        [
            python,
            str(trace_dir / "validate_registry.py"),
            "--project-root",
            str(project_root),
            "--project-key",
            project_key,
        ]
    )
    steps.append({"name": "validate_registry", **validation})
    validation_path.write_text(((validation["stdout"] or "") + (validation["stderr"] or "")).rstrip() + "\n", encoding="utf-8")
    if validation["returncode"] != 0:
        return {"ok": False, "message": "validate_registry failed", "steps": steps}

    report_text = run_command(
        [
            python,
            str(trace_dir / "report_registry.py"),
            "--project-root",
            str(project_root),
            "--project-key",
            project_key,
            "--format",
            "text",
        ]
    )
    steps.append({"name": "report_registry_text", **report_text})
    if report_text["returncode"] != 0:
        return {"ok": False, "message": "report_registry_text failed", "steps": steps}
    report_text_path.write_text((report_text["stdout"] or "").rstrip() + "\n", encoding="utf-8")

    report_json = run_command(
        [
            python,
            str(trace_dir / "report_registry.py"),
            "--project-root",
            str(project_root),
            "--project-key",
            project_key,
            "--format",
            "json",
        ]
    )
    steps.append({"name": "report_registry_json", **report_json})
    if report_json["returncode"] != 0:
        return {"ok": False, "message": "report_registry_json failed", "steps": steps}
    report_json_path.write_text((report_json["stdout"] or "").rstrip() + "\n", encoding="utf-8")

    return {
        "ok": True,
        "message": "traceability runtime completed",
        "steps": steps,
        "validation_path": str(validation_path),
        "report_text_path": str(report_text_path),
        "report_json_path": str(report_json_path),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_phase1_convergence_args(argv)
    try:
        context = build_phase1_convergence_runtime_context(args)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}")
        print("FINAL: BLOCKED")
        return 2

    print_phase1_convergence_runtime_start(context)

    all_rounds: list[dict[str, object]] = []
    passed_round = None

    idx = 1
    while idx <= len(context.candidates) and idx <= context.max_rounds:
        prd_path = context.candidates[idx - 1]
        state = "P0 converged-candidate" if idx == 1 else f"P{idx - 1} deepening-round-{idx - 1}"
        print(f"\n=== Round {idx} / state={state} ===")
        print(f"prd: {prd_path}")
        convergence_evidence_path = context.convergence_evidence_arg
        if convergence_evidence_path is None:
            _, inferred_evidence = derive_convergence_artifact_paths(prd_path)
            if inferred_evidence.exists():
                convergence_evidence_path = inferred_evidence
        if convergence_evidence_path:
            print(f"convergence_evidence: {convergence_evidence_path}")

        gates: list[dict[str, object]] = []
        if context.stage_paths:
            stage_depth_cmd = [
                context.python,
                str(resolve_phase1_script(context.script_dir, "phase1_stage_artifact_depth_gate.py")),
                "--source",
                str(context.source_path),
            ]
            for stage_path in context.stage_paths:
                stage_depth_cmd.extend(["--stage", str(stage_path)])
            gates.append({"name": "stage_artifact_depth_gate", "command": stage_depth_cmd})

        quality_cmd = [
            context.python,
            str(resolve_phase1_script(context.script_dir, "phase1_prd_quality_gate.py")),
            "--source",
            str(context.source_path),
            "--prd",
            str(prd_path),
        ]
        if context.require_non_shrinking:
            quality_cmd.append("--require-non-shrinking")
        if convergence_evidence_path:
            quality_cmd.extend(["--convergence-evidence", str(convergence_evidence_path)])
        for stage_path in context.stage_paths:
            quality_cmd.extend(["--stage", str(stage_path)])
        gates.append({"name": "quality_gate", "command": quality_cmd})
        mainline_bundle_gates: list[tuple[str, list[str]]] = []
        integrity_cmd = [
            context.python,
            str(resolve_phase1_script(context.script_dir, "phase1_prd_assembly_integrity_gate.py")),
            "--source",
            str(context.source_path),
            "--prd",
            str(prd_path),
        ]
        if context.report_path:
            integrity_cmd.extend(["--report", str(context.report_path)])
        for stage_path in context.stage_paths:
            integrity_cmd.extend(["--stage", str(stage_path)])
        mainline_bundle_gates.append(("assembly_integrity_gate", integrity_cmd))

        analysis_delta_cmd = [
            context.python,
            str(resolve_phase1_script(context.script_dir, "phase1_prd_analysis_delta_gate.py")),
            "--prd",
            str(prd_path),
        ]
        if convergence_evidence_path:
            analysis_delta_cmd.extend(["--delta-ledger", str(convergence_evidence_path)])
        mainline_bundle_gates.append(("analysis_delta_gate", analysis_delta_cmd))
        gates.append(
            {
                "name": "executability_gate",
                "command": [
                    context.python,
                    str(resolve_phase1_script(context.script_dir, "phase1_prd_executability_gate.py")),
                    "--prd",
                    str(prd_path),
                    "--profile",
                    context.profile,
                ],
            }
        )
        mainline_bundle_gates.append(
            (
                "section_scoring_gate",
                [
                    context.python,
                    str(resolve_phase1_script(context.script_dir, "phase1_prd_section_scoring_gate.py")),
                    "--prd",
                    str(prd_path),
                    "--min-section-score",
                    "90",
                ],
            )
        )

        if context.report_path:
            expected = extract_trial_token(prd_path)
            consistency_cmd = [
                context.python,
                str(resolve_phase1_script(context.script_dir, "phase1_artifact_consistency_gate.py")),
                "--prd",
                str(prd_path),
                "--report",
                str(context.report_path),
                "--require-stage-files",
            ]
            if expected:
                consistency_cmd.extend(["--expected-version", expected])
            for stage_path in context.stage_paths:
                consistency_cmd.extend(["--stage", str(stage_path)])
            mainline_bundle_gates.append(("artifact_consistency_gate", consistency_cmd))

        gates.append({"name": PHASE1_MAINLINE_GATE_BUNDLE, "bundle_gates": mainline_bundle_gates})

        round_result: dict[str, object] = {
            "round": idx,
            "state": state,
            "prd": str(prd_path),
            "convergence_evidence": str(convergence_evidence_path) if convergence_evidence_path else None,
            "gates": [],
        }
        failed = []
        for gate_def in gates:
            gate_name = str(gate_def["name"])
            if "bundle_gates" in gate_def:
                gate_payload = run_gate_bundle(gate_name, list(gate_def["bundle_gates"]))  # type: ignore[arg-type]
            else:
                command = list(gate_def["command"])  # type: ignore[arg-type]
                result = run_command(command)
                gate_payload = build_gate_payload(gate_name, command, result)
            round_result["gates"].append(gate_payload)
            print(f"\n-- {gate_name} --")
            print(str(gate_payload["command"]))
            subgates = gate_payload.get("subgates")
            if isinstance(subgates, list):
                summary = str(gate_payload.get("summary", "") or "").rstrip()
                if summary:
                    print(summary)
                failed.extend(str(name) for name in gate_payload.get("failed_subgates", []) if isinstance(name, str))
                for subgate in subgates:
                    if not isinstance(subgate, dict):
                        continue
                    print(f"\n  >> {subgate.get('name')}")
                    print(f"  {subgate.get('command')}")
                    stdout = str(subgate.get("stdout", "") or "").rstrip()
                    stderr = str(subgate.get("stderr", "") or "").rstrip()
                    if stdout:
                        print(stdout)
                    if stderr:
                        print(stderr)
            else:
                stdout = str(gate_payload.get("stdout", "") or "").rstrip()
                stderr = str(gate_payload.get("stderr", "") or "").rstrip()
                if stdout:
                    print(stdout)
                if stderr:
                    print(stderr)
                if gate_payload["returncode"] != 0:
                    failed.append(gate_name)

        round_result["failed_gates"] = failed
        all_rounds.append(round_result)

        if not failed:
            provisional_assessment = build_phase1_mainline_assessment(
                depth_mode=context.depth_mode,
                source_path=context.source_path,
                prd_path=prd_path,
                stage_paths=context.stage_paths,
                convergence_evidence_path=convergence_evidence_path,
                chosen_round=round_result,
                passed_round=idx,
            )
            round_result["provisional_phase_mainline_assessment"] = provisional_assessment
            same_run_deepening = build_same_run_deepening_signal(provisional_assessment)
            round_result["same_run_deepening"] = same_run_deepening
            if same_run_deepening:
                remediation = None
                if context.auto_remediate and idx < context.max_rounds:
                    remediation = build_remediation_plan(
                        [],
                        context.stage_paths,
                        prd_path=prd_path,
                        same_run_deepening=same_run_deepening,
                    )
                round_result["remediation"] = remediation
                reason_lines = list(same_run_deepening.get("rationale", []))
                print(
                    f"\n[RETURN] Round {idx} passed structural gates but still requires same-run value deepening"
                )
                print("state_transition: R11 Return / Remediation Needed -> same-run deepening")
                if provisional_assessment.get("baseline_calibration_status"):
                    print(
                        "baseline_calibration_status: "
                        f"{provisional_assessment['baseline_calibration_status']}"
                    )
                if provisional_assessment.get("agentic_loop_focus_areas"):
                    print(
                        "loop_focus_areas: "
                        + ", ".join(
                            str(item)
                            for item in provisional_assessment["agentic_loop_focus_areas"]
                            if str(item).strip()
                        )
                    )
                for reason in reason_lines:
                    print(f"- same_run_deepening_reason: {reason}")
                if remediation:
                    doc_name = first_markdown_title(prd_path)
                    remediation_result = execute_remediation_plan(
                        remediation,
                        source_path=context.source_path,
                        prd_path=prd_path,
                        stage_paths=context.stage_paths,
                        script_dir=context.script_dir,
                        python=context.python,
                        profile=context.profile,
                        document_name=doc_name,
                        depth_mode=context.depth_mode,
                        thinking_value_gain_mode=context.thinking_value_gain_mode,
                        output_locale=context.output_locale,
                    )
                    round_result["remediation_execution"] = remediation_result
                    if remediation_result["ok"]:
                        context.candidates.append(prd_path)
                        idx += 1
                        continue
                    print(f"[BLOCKED] remediation failed: {remediation_result['message']}")
                    print("state_transition: R12 Blocked")
                elif idx < len(context.candidates):
                    print("state_transition: R11 Return / Remediation Needed -> next PRD candidate")
                else:
                    print("[BLOCKED] same-run value deepening is required but auto-remediation is unavailable")
                    print("state_transition: R12 Blocked")
                idx += 1
                continue

            passed_round = idx
            print(f"\n[PASS] Round {idx} passed all gates")
            break

        remediation = None
        if context.auto_remediate and idx < context.max_rounds:
            remediation = build_remediation_plan(failed, context.stage_paths, prd_path=prd_path)
            round_result["remediation"] = remediation
            if remediation:
                print(f"\n[RETURN] Round {idx} failed gates: {', '.join(failed)}")
                print("state_transition: R11 Return / Remediation Needed -> auto remediation")
                print(f"remediation_sections: {', '.join(remediation['sections_to_deepen'])}")
                print(f"consumer_problems: {', '.join(remediation['consumer_problems'])}")
                if remediation.get("loop_round_focus"):
                    print(f"loop_round_focus: {remediation['loop_round_focus']}")
                if remediation.get("loop_focus_areas"):
                    print(f"loop_focus_areas: {', '.join(remediation['loop_focus_areas'])}")
                if remediation.get("loop_target_scenarios"):
                    print(f"loop_target_scenarios: {', '.join(remediation['loop_target_scenarios'])}")
                for reason in remediation["rationale"]:
                    print(f"- remediation_reason: {reason}")
                doc_name = first_markdown_title(prd_path)
                remediation_result = execute_remediation_plan(
                    remediation,
                    source_path=context.source_path,
                    prd_path=prd_path,
                    stage_paths=context.stage_paths,
                    script_dir=context.script_dir,
                    python=context.python,
                    profile=context.profile,
                    document_name=doc_name,
                    depth_mode=context.depth_mode,
                    thinking_value_gain_mode=context.thinking_value_gain_mode,
                    output_locale=context.output_locale,
                )
                round_result["remediation_execution"] = remediation_result
                if remediation_result["ok"]:
                    context.candidates.append(prd_path)
                    idx += 1
                    continue
                print(f"[BLOCKED] remediation failed: {remediation_result['message']}")
                print("state_transition: R12 Blocked")
            else:
                print(f"\n[BLOCKED] Final round failed gates with no actionable remediation: {', '.join(failed)}")
                print("state_transition: R12 Blocked")
        elif idx < len(context.candidates):
            print(f"\n[RETURN] Round {idx} failed gates: {', '.join(failed)}")
            print("state_transition: R11 Return / Remediation Needed -> next PRD candidate")
        else:
            print(f"\n[BLOCKED] Final round failed gates: {', '.join(failed)}")
            print("state_transition: R12 Blocked")

        idx += 1

    chosen_round = None
    if passed_round is not None and len(all_rounds) >= passed_round:
        chosen_round = all_rounds[passed_round - 1]
    elif all_rounds:
        chosen_round = all_rounds[-1]

    chosen_prd_path = Path(str(chosen_round["prd"])).resolve() if chosen_round and chosen_round.get("prd") else None
    chosen_convergence_evidence_path = None
    if chosen_round and chosen_round.get("convergence_evidence"):
        chosen_convergence_evidence_path = Path(str(chosen_round["convergence_evidence"])).resolve()
    elif context.convergence_evidence_arg is not None:
        chosen_convergence_evidence_path = context.convergence_evidence_arg

    mainline_assessment = None
    scorecard_path = None
    acceptance_matrix_path = None
    verdict_path = None
    if chosen_prd_path is not None:
        assessment_output_dir = infer_output_dir(chosen_prd_path, context.stage_paths)
        final_narrative_applied = apply_final_narrative_compression_if_present(
            chosen_prd_path=chosen_prd_path,
            output_dir=assessment_output_dir,
        )
        print(
            "final_narrative_compression: "
            + ("applied" if final_narrative_applied else "skipped")
        )
        scorecard_path = assessment_output_dir / "phase-mainline-scorecard.md"
        acceptance_matrix_path = assessment_output_dir / "phase-acceptance-matrix.md"
        verdict_path = assessment_output_dir / "phase-verdict.json"
        mainline_assessment = build_phase1_mainline_assessment(
            depth_mode=context.depth_mode,
            source_path=context.source_path,
            prd_path=chosen_prd_path,
            stage_paths=context.stage_paths,
            convergence_evidence_path=chosen_convergence_evidence_path,
            chosen_round=chosen_round if isinstance(chosen_round, dict) else None,
            passed_round=passed_round,
        )
        scorecard_path.write_text(render_phase1_scorecard_markdown(mainline_assessment), encoding="utf-8")
        acceptance_matrix_path.write_text(render_phase1_acceptance_matrix_markdown(mainline_assessment), encoding="utf-8")
        verdict_path.write_text(
            json.dumps(
                {
                    "phase": "P1",
                    "depth_mode": context.depth_mode,
                    "total_score": mainline_assessment["total_score"],
                    "verdict": mainline_assessment["verdict"],
                    "review_bound_items_count": mainline_assessment["review_bound_items_count"],
                    "blockers_count": mainline_assessment["blockers_count"],
                    "document_delivery_state": mainline_assessment["document_delivery_state"],
                    "evidence_confidence_state": mainline_assessment["evidence_confidence_state"],
                    "scorecard_path": str(scorecard_path),
                    "acceptance_matrix_path": str(acceptance_matrix_path),
                    "prd": str(chosen_prd_path),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\nphase_mainline_scorecard: {scorecard_path}")
        print(f"phase_acceptance_matrix: {acceptance_matrix_path}")
        print(f"phase_total_score: {mainline_assessment['total_score']} / 100")
        print(f"phase_verdict: {mainline_assessment['verdict']}")

    payload = {
        "source": str(context.source_path),
        "report": str(context.report_path) if context.report_path else None,
        "profile": context.profile,
        "depth_mode": context.depth_mode,
        "rounds": all_rounds,
        "passed_round": passed_round,
    }
    if mainline_assessment is not None:
        payload["phase_mainline_assessment"] = mainline_assessment
        payload["phase_mainline_scorecard_path"] = str(scorecard_path)
        payload["phase_acceptance_matrix_path"] = str(acceptance_matrix_path)
        payload["phase_verdict_path"] = str(verdict_path)
        payload["phase_verdict"] = str(mainline_assessment["verdict"])
        payload["phase_total_score"] = mainline_assessment["total_score"]
    traceability_runtime = None
    prototype_spec_generation = None
    interaction_flow_contract_generation = None
    runtime_blocked = False
    if passed_round is not None:
        passed_prd_path = Path(all_rounds[passed_round - 1]["prd"]).resolve()
        traceability_runtime = run_phase1_traceability_runtime(
            script_dir=context.script_dir,
            python=context.python,
            prd_path=passed_prd_path,
            stage_paths=context.stage_paths,
        )
        payload["traceability_runtime"] = traceability_runtime
        if traceability_runtime["ok"]:
            print(f"\ntrace_validation: {traceability_runtime['validation_path']}")
            print(f"trace_report: {traceability_runtime['report_text_path']}")
        else:
            print(f"\n[BLOCKED] phase-1 traceability runtime failed: {traceability_runtime['message']}")
            runtime_blocked = True
        if not runtime_blocked:
            prototype_spec_generation = generate_phase1_prototype_spec_artifact(
                python=context.python,
                script_dir=context.script_dir,
                prd_path=passed_prd_path,
                stage_paths=context.stage_paths,
                output_locale=context.output_locale,
            )
            payload["prototype_spec_generation"] = prototype_spec_generation
            if prototype_spec_generation["ok"]:
                print(f"prototype_spec: {prototype_spec_generation['output_path']}")
                print(f"prototype_prompt_pack: {prototype_spec_generation['prompt_pack_output_path']}")
            else:
                print(f"\n[BLOCKED] phase-1 prototype-spec generation failed: {prototype_spec_generation['message']}")
                if prototype_spec_generation.get("command"):
                    print(prototype_spec_generation["command"])
                if prototype_spec_generation.get("stdout"):
                    print(str(prototype_spec_generation["stdout"]).rstrip())
                if prototype_spec_generation.get("stderr"):
                    print(str(prototype_spec_generation["stderr"]).rstrip())
                runtime_blocked = True
        if not runtime_blocked and prototype_spec_generation is not None:
            interaction_flow_contract_generation = generate_phase1_interaction_flow_contract_artifact(
                python=context.python,
                script_dir=context.script_dir,
                prototype_spec_path=Path(str(prototype_spec_generation["output_path"])).resolve(),
                output_locale=context.output_locale,
            )
            payload["interaction_flow_contract_generation"] = {
                **interaction_flow_contract_generation,
                "interaction_flow_contract_output_path": interaction_flow_contract_generation.get("output_path"),
            }
            if interaction_flow_contract_generation["ok"]:
                print(f"prototype_interaction_flow_contract: {interaction_flow_contract_generation['output_path']}")
            else:
                print(
                    "\n[BLOCKED] phase-1 interaction-flow-contract generation failed: "
                    f"{interaction_flow_contract_generation['message']}"
                )
                if interaction_flow_contract_generation.get("command"):
                    print(interaction_flow_contract_generation["command"])
                if interaction_flow_contract_generation.get("stdout"):
                    print(str(interaction_flow_contract_generation["stdout"]).rstrip())
                if interaction_flow_contract_generation.get("stderr"):
                    print(str(interaction_flow_contract_generation["stderr"]).rstrip())
                runtime_blocked = True
        else:
            payload["prototype_spec_generation"] = prototype_spec_generation
            payload["interaction_flow_contract_generation"] = (
                {
                    **interaction_flow_contract_generation,
                    "interaction_flow_contract_output_path": interaction_flow_contract_generation.get("output_path"),
                }
                if interaction_flow_contract_generation is not None
                else None
            )
    if context.output_json_path is not None:
        context.output_json_path.parent.mkdir(parents=True, exist_ok=True)
        sanitized_payload = sanitize_runtime_payload(payload, context.source_path)
        context.output_json_path.write_text(json.dumps(sanitized_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nresult_json: {context.output_json_path}")

    if passed_round is None or runtime_blocked:
        print("FINAL: BLOCKED")
        return 2

    final_verdict = str(mainline_assessment["verdict"]) if isinstance(mainline_assessment, dict) else "PASS"
    if final_verdict in {"PASS", "PASS with review-bound items"}:
        print("FINAL: PASS")
        return 0
    print("FINAL: BLOCKED")
    return 2


if __name__ == "__main__":
    sys.exit(main())
