#!/usr/bin/env python3
"""Resolve P2 source surfaces for P3 traceable behavior cards."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import importlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from common.cross_phase_surface_policy import find_cross_phase_surface_path

TRACE_ID_RE = re.compile(r"\bP[12]-(?:US|UC|REQ|AC|DTR|CTR|RP|RT)-\d+\b")


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _markdown_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for index, line in enumerate(lines, start=1):
        if not line.strip().startswith("|"):
            continue
        cells = _split_table_row(line)
        if not cells or all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        if any(cell in {"trace_id", "replay_id"} for cell in cells):
            header = cells
            next_index = index + 1
            while next_index <= len(lines):
                body = lines[next_index - 1]
                if not body.strip().startswith("|"):
                    break
                body_cells = _split_table_row(body)
                if body_cells and all(set(cell) <= {"-", ":", " "} for cell in body_cells):
                    next_index += 1
                    continue
                if len(body_cells) >= len(header):
                    rows.append({"file": str(path), "line": next_index, "data": dict(zip(header, body_cells))})
                next_index += 1
    return rows





def load_operation_source_obligation_matrix(phase2_root: Path) -> dict[str, dict[str, Any]]:
    path = find_cross_phase_surface_path(phase2_root, "phase2", "operation-source-obligation-matrix.json")
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    operations = payload.get("operations", [])
    if not isinstance(operations, list):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for row in operations:
        if not isinstance(row, dict):
            continue
        operation_id = str(row.get("operation_id", "")).strip()
        if operation_id:
            rows[operation_id] = row
    return rows


def load_p1_value_operation_resolution_matrix(phase2_root: Path) -> dict[str, dict[str, Any]]:
    path = find_cross_phase_surface_path(phase2_root, "phase2", "p1-value-to-p2-operation-resolution-matrix.json")
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    resolutions = payload.get("resolutions", [])
    if not isinstance(resolutions, list):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for row in resolutions:
        if not isinstance(row, dict):
            continue
        operation_id = str(row.get("operation_id", "")).strip()
        if operation_id:
            rows[operation_id] = row
    return rows


def _trace_ids_from_resolution(row: dict[str, Any] | None) -> list[str]:
    if not row:
        return []
    candidates: list[Any] = []
    for key in ("p1_trace_ids", "p2_contract_ids", "p2_flow_ids", "p2_sequence_ids", "p2_state_ids"):
        value = row.get(key)
        if isinstance(value, list):
            candidates.extend(value)
        else:
            candidates.append(value)
    contract_trace_id = row.get("contract_trace_id")
    if contract_trace_id:
        candidates.append(contract_trace_id)
    return list(dict.fromkeys(str(item).strip() for item in candidates if TRACE_ID_RE.fullmatch(str(item).strip())))


def load_operation_design_source_registry(phase2_root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    path = find_cross_phase_surface_path(phase2_root, "phase2", "operation-design-source-registry.json")
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        return {}
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in sources:
        if not isinstance(row, dict):
            continue
        operation_id = str(row.get("operation_id", "")).strip()
        source_type = str(row.get("source_type", "")).strip()
        source_id = str(row.get("source_id", "")).strip()
        if operation_id and source_type and source_id:
            rows[(operation_id, source_type)] = row
    return rows


def load_operation_behavior_semantics(phase2_root: Path) -> dict[str, dict[str, Any]]:
    path = find_cross_phase_surface_path(phase2_root, "phase2", "operation-behavior-semantics.json")
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    operations = payload.get("operations", [])
    if not isinstance(operations, list):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for row in operations:
        if not isinstance(row, dict):
            continue
        operation_id = str(row.get("operation_id", "")).strip()
        if operation_id:
            rows[operation_id] = row
    return rows


def _structured_semantics_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    status = str(row.get("semantic_status") or row.get("status") or "review_bound")
    if status != "resolved":
        return {
            "status": "review_bound",
            "source_authority": "p2-structured",
            "review_bound_reasons": row.get("review_bound_reasons", ["operation_semantics_not_found"]),
        }
    return {
        "status": "resolved",
        "source_authority": str(row.get("source_authority") or "p2-structured"),
        "owner_service": row.get("owner_service", ""),
        "aggregate": row.get("aggregate", ""),
        "state_set": row.get("state_set", []),
        "trigger_events": row.get("trigger_events", []),
        "mutation_guard": row.get("mutation_guard", ""),
        "terminal_or_failure_exit": row.get("terminal_or_failure_exit", ""),
        "readonly_dependencies": row.get("readonly_dependencies", []),
        "evidence_keys": row.get("evidence_keys", []),
        "source_evidence": row.get("source_evidence", []),
        "review_bound_reasons": row.get("review_bound_reasons", []),
    }


def extract_operation_semantics_from_available_runtime(operation_id: str, source_texts: list[str]) -> dict[str, Any]:
    for module_name in ("phase3.phase3_operation_semantics", "phase3_operation_semantics"):
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        extractor = getattr(module, "extract_operation_semantics", None)
        if callable(extractor):
            return extractor(operation_id, source_texts)
    return {
        "status": "review_bound",
        "source_authority": "profile-fallback",
        "review_bound_reasons": ["operation_semantics_runtime_not_available"],
    }


def _registry_design_source(root: Path, operation_id: str, source_type: str) -> dict[str, Any] | None:
    row = load_operation_design_source_registry(root).get((operation_id, source_type))
    if not row:
        return None
    source_stage = str(row.get("source_stage", "")).strip()
    source_file = "stage-04-design-convergence-and-delivery-prototype.md" if source_stage == "Stage-04" else "stage-03-data-storage-and-interface-design.md"
    source_path = root / source_file
    return {
        "status": "resolved",
        "authority": "registry-bound",
        "trace_id": str(row.get("source_id", "")).strip(),
        "source_type": source_type,
        "subject": operation_id,
        "file": str(source_path),
        "line": None,
        "marker": str(row.get("evidence_ref", "")).strip() or source_type,
        "upstream_contract_trace_id": str(row.get("upstream_contract_trace_id", "")).strip(),
    }


def _registry_design_contract(root: Path, operation_id: str) -> dict[str, Any] | None:
    source = _registry_design_source(root, operation_id, "P2-CTR")
    if not source:
        return None
    source["subject"] = operation_id
    source["upstream_trace_ids"] = []
    return source


def build_source_requirement_statuses(bundle: dict[str, Any], risk_row: dict[str, Any] | None) -> dict[str, str]:
    source_types = ["P2-CTR", "P2-FLOW", "P2-SEQ", "P2-STATE", "P2-RP"]
    if not risk_row:
        return {source_type: "review_bound" for source_type in source_types}
    required = {str(item) for item in risk_row.get("required_source_types", [])}
    not_required = {str(item) for item in risk_row.get("not_required_source_types", [])}
    review_bound_missing = {str(item) for item in risk_row.get("review_bound_missing_sources", [])}
    statuses: dict[str, str] = {}
    source_lookup = {
        "P2-CTR": bundle.get("contract_source", {}),
        "P2-FLOW": bundle.get("flow_source", {}),
        "P2-SEQ": bundle.get("sequence_source", {}),
        "P2-STATE": bundle.get("state_source", {}),
        "P2-RP": {},
    }
    for source_type in source_types:
        if source_type in not_required and source_type not in required:
            statuses[source_type] = "not_required"
        elif source_type in review_bound_missing:
            statuses[source_type] = "review_bound"
        elif source_type in required:
            source = source_lookup.get(source_type, {})
            if source.get("status") == "resolved":
                statuses[source_type] = str(source.get("authority") or "resolved")
            else:
                statuses[source_type] = "review_bound"
        else:
            statuses[source_type] = "not_required"
    return statuses


def _registry_db_path(root: Path) -> Path:
    return root / ".trace" / "trace.db"


def _resolve_registry_source_path(root: Path, source_path: str) -> tuple[str, str]:
    if not source_path:
        return "", "missing-source"
    path = Path(source_path)
    candidate = path if path.is_absolute() else root / path
    try:
        candidate.resolve().relative_to(root.resolve())
        inside_root = True
    except Exception:
        inside_root = False
    if candidate.exists() and inside_root:
        return str(candidate), "registry-bound"
    if path.is_absolute() and not inside_root:
        current_candidate = root / path.name
        if current_candidate.exists():
            return str(current_candidate), "rewritten-current-run"
        return str(candidate), "stale-binding"
    return str(candidate), "missing-source"


def _registry_rows(root: Path) -> list[dict[str, Any]]:
    db_path = _registry_db_path(root)
    if not db_path.exists():
        return []
    try:
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        rows = [dict(row) for row in con.execute("select * from artifacts").fetchall()]
        con.close()
        return rows
    except sqlite3.Error:
        return []


def _registry_upstream_ids(root: Path, artifact_id: str) -> list[str]:
    db_path = _registry_db_path(root)
    if not db_path.exists() or not artifact_id:
        return []
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute(
            "select from_artifact_id, to_artifact_id from links where from_artifact_id = ? or to_artifact_id = ?",
            (artifact_id, artifact_id),
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return []
    upstream: list[str] = []
    for left, right in rows:
        for candidate in (left, right):
            value = str(candidate or "")
            if value != artifact_id and value.startswith("P1-"):
                upstream.append(value)
    return list(dict.fromkeys(upstream))


def _find_registry_contract(root: Path, operation_id: str) -> dict[str, Any] | None:
    needle = _normalize(operation_id)
    for row in _registry_rows(root):
        artifact_id = str(row.get("artifact_id") or "")
        artifact_type = str(row.get("artifact_type") or "")
        stage = str(row.get("stage_or_lane") or "")
        anchor = str(row.get("source_anchor") or "")
        searchable = _normalize(" ".join([artifact_id, artifact_type, stage, anchor]))
        if not artifact_id.startswith("P2-CTR") and artifact_id != operation_id:
            continue
        if needle not in searchable:
            continue
        resolved_path, binding_status = _resolve_registry_source_path(root, str(row.get("source_path") or ""))
        upstream_ids = _registry_upstream_ids(root, artifact_id)
        return {
            "status": "resolved",
            "authority": "registry-bound",
            "binding_status": binding_status,
            "trace_id": artifact_id,
            "subject": artifact_id,
            "file": resolved_path,
            "anchor": anchor,
            "line": None,
            "upstream_trace_ids": upstream_ids,
        }
    return None

def _find_contract(root: Path, operation_id: str) -> dict[str, Any]:
    needle = _normalize(operation_id)
    best: dict[str, Any] | None = None
    for path in sorted(root.rglob("*.md")):
        if ".trace" in path.parts:
            continue
        for row in _markdown_rows(path):
            data = row["data"]
            subject = str(data.get("trace_subject") or data.get("scenario_or_contract") or "")
            hook = str(data.get("verification_hook") or data.get("semantic_bridge_note") or "")
            trace_id = str(data.get("trace_id") or data.get("replay_id") or "")
            searchable = _normalize(subject + " " + hook + " " + trace_id)
            if needle and needle in searchable:
                if trace_id.startswith("P2-CTR") or best is None:
                    best = row
                    if trace_id.startswith("P2-CTR"):
                        break
        if best and str(best["data"].get("trace_id") or "").startswith("P2-CTR"):
            break
    if not best:
        return {"status": "review_bound", "reason": "operation contract source missing"}
    data = best["data"]
    return {
        "status": "resolved",
        "trace_id": str(data.get("trace_id") or data.get("replay_id") or ""),
        "subject": str(data.get("trace_subject") or data.get("scenario_or_contract") or ""),
        "file": best["file"],
        "line": best["line"],
        "upstream_trace_ids": TRACE_ID_RE.findall(str(data.get("upstream_trace_ids") or "")),
    }


def _find_text_source(root: Path, operation_id: str, marker: str, missing_reason: str) -> dict[str, Any]:
    needle = _normalize(operation_id)
    marker_norm = _normalize(marker)
    for path in sorted(root.rglob("*.md")):
        if ".trace" in path.parts:
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for index, line in enumerate(lines, start=1):
            line_norm = _normalize(line)
            if marker_norm in line_norm and (needle in line_norm or any(needle in _normalize(l) for l in lines[index : index + 8])):
                return {"status": "resolved", "file": str(path), "line": index, "marker": marker}
    return {"status": "review_bound", "reason": missing_reason}


def resolve_behavior_sources(phase2_root: str | Path, operation_id: str) -> dict[str, Any]:
    root = Path(phase2_root)
    contract = _find_registry_contract(root, operation_id) or _registry_design_contract(root, operation_id) or _find_contract(root, operation_id)
    if contract.get("status") == "resolved" and not contract.get("authority"):
        contract["authority"] = "markdown-fallback"
    flow = _registry_design_source(root, operation_id, "P2-FLOW") or _find_text_source(root, operation_id, "interaction_flow", "P2 interaction flow source missing")
    sequence = _registry_design_source(root, operation_id, "P2-SEQ") or _find_text_source(root, operation_id, "sequenceDiagram", "P2 sequence diagram source missing")
    state = _registry_design_source(root, operation_id, "P2-STATE") or _find_text_source(root, operation_id, "stateDiagram-v2", "exact operation-to-state binding missing")
    review_bound = [
        str(source.get("reason"))
        for source in (contract, flow, sequence, state)
        if source.get("status") == "review_bound" and source.get("reason")
    ]
    if contract.get("binding_status") in {"stale-binding", "rewritten-current-run"}:
        review_bound.append("stale trace registry binding")
    resolution_rows = load_p1_value_operation_resolution_matrix(root)
    resolution_row = resolution_rows.get(operation_id)
    resolution_trace_ids = _trace_ids_from_resolution(resolution_row)
    p2_ids = [contract["trace_id"]] if contract.get("trace_id") else []
    upstream_trace_ids = list(
        dict.fromkeys(
            trace_id
            for trace_id in [*contract.get("upstream_trace_ids", []), *resolution_trace_ids, *p2_ids]
            if TRACE_ID_RE.fullmatch(str(trace_id or ""))
        )
    )
    if not any(trace_id.startswith("P1-") for trace_id in upstream_trace_ids):
        review_bound.append("upstream_trace_ids_missing_p1")
    bundle: dict[str, Any] = {
        "operation_id": operation_id,
        "contract_source": contract,
        "flow_source": flow,
        "sequence_source": sequence,
        "state_source": state,
        "upstream_trace_ids": upstream_trace_ids,
        "review_bound": review_bound,
    }
    structured_semantics = _structured_semantics_row(load_operation_behavior_semantics(root).get(operation_id))
    if structured_semantics is not None:
        operation_semantics = structured_semantics
    else:
        semantic_texts = [path.read_text(encoding="utf-8", errors="ignore") for path in sorted(root.rglob("*.md")) if ".trace" not in path.parts]
        operation_semantics = extract_operation_semantics_from_available_runtime(operation_id, semantic_texts)
    bundle["operation_semantics"] = operation_semantics
    if operation_semantics.get("status") == "review_bound":
        bundle["review_bound"].extend(str(item) for item in operation_semantics.get("review_bound_reasons", []) if str(item).strip())
    risk_rows = load_operation_source_obligation_matrix(root)
    matrix_present = find_cross_phase_surface_path(root, "phase2", "operation-source-obligation-matrix.json").exists()
    risk_row = risk_rows.get(operation_id)
    if risk_row:
        bundle["operation_risk_row_status"] = "resolved"
        bundle["risk_tier"] = risk_row.get("risk_tier", "")
        bundle["risk_triggers"] = risk_row.get("risk_triggers", [])
        bundle["required_source_types"] = risk_row.get("required_source_types", [])
        bundle["not_required_source_types"] = risk_row.get("not_required_source_types", [])
        bundle["classification_rationale"] = risk_row.get("classification_rationale", "")
        bundle["source_requirement_statuses"] = build_source_requirement_statuses(bundle, risk_row)
    elif matrix_present:
        bundle["operation_risk_row_status"] = "p2_operation_risk_row_missing"
        bundle["risk_tier"] = "review-bound"
        bundle["required_source_types"] = []
        bundle["not_required_source_types"] = []
        bundle["source_requirement_statuses"] = build_source_requirement_statuses(bundle, None)
        bundle["review_bound"].append("p2_operation_risk_row_missing")
    else:
        bundle["operation_risk_row_status"] = "matrix_not_present"
        bundle["source_requirement_statuses"] = {}
    return bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve Phase-2 source bundle for a P3 behavior card")
    parser.add_argument("phase2_root")
    parser.add_argument("operation_id")
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    bundle = resolve_behavior_sources(args.phase2_root, args.operation_id)
    payload = json.dumps(bundle, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
