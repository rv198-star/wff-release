#!/usr/bin/env python3
"""
Finalize the Phase-3 trace registry by binding Phase-2 trace surfaces to implementation artifacts.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


TRACE_LINK_STOPWORDS = {
    "api",
    "app",
    "apps",
    "contract",
    "contracts",
    "controller",
    "foundation",
    "module",
    "modules",
    "repository",
    "runtime",
    "service",
    "test",
    "tests",
    "unit",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def stable_artifact_id(prefix: str, source: str) -> str:
    compact = re.sub(r"[^A-Z0-9]+", "-", str(source).upper()).strip("-")
    compact = re.sub(r"-+", "-", compact)
    digest = hashlib.sha1(str(source).encode("utf-8")).hexdigest()[:8].upper()
    if len(compact) > 36:
        compact = compact[:36].rstrip("-")
    return f"{prefix}-{compact}-{digest}" if compact else f"{prefix}-{digest}"


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return bool(row)


def _trace_db_project_scope(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT project_scope FROM artifacts LIMIT 1").fetchone()
    if row and row[0]:
        return str(row[0])
    meta = conn.execute("SELECT project_key, project_root FROM registry_meta LIMIT 1").fetchone()
    if meta and meta[0] and meta[1]:
        return f"{meta[0]}:{Path(str(meta[1])).resolve()}"
    return ""


def _artifact_exists(conn: sqlite3.Connection, project_scope: str, artifact_id: str) -> bool:
    row = conn.execute(
        "SELECT artifact_id FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
        (project_scope, artifact_id),
    ).fetchone()
    return bool(row)


def _upsert_trace_artifact(
    conn: sqlite3.Connection,
    *,
    project_scope: str,
    artifact_id: str,
    artifact_type: str,
    stage_or_lane: str,
    status: str,
    source_path: str,
    source_anchor: str,
    language_role: str = "phase3-runtime-evidence",
) -> bool:
    timestamp = now_iso()
    existing = conn.execute(
        "SELECT artifact_id FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
        (project_scope, artifact_id),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE artifacts SET artifact_type=?, stage_or_lane=?, status=?, source_path=?, source_anchor=?, language_role=?, updated_at=? WHERE project_scope=? AND artifact_id=?",
            (
                artifact_type,
                stage_or_lane,
                status,
                source_path,
                source_anchor,
                language_role,
                timestamp,
                project_scope,
                artifact_id,
            ),
        )
        return False
    conn.execute(
        "INSERT INTO artifacts (project_scope, artifact_id, artifact_type, stage_or_lane, status, source_path, source_anchor, language_role, canonical_of, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            project_scope,
            artifact_id,
            artifact_type,
            stage_or_lane,
            status,
            source_path,
            source_anchor,
            language_role,
            None,
            timestamp,
            timestamp,
        ),
    )
    return True


def _insert_trace_link(
    conn: sqlite3.Connection,
    *,
    project_scope: str,
    from_artifact_id: str,
    to_artifact_id: str,
    link_type: str,
    source_path: str,
    evidence_anchor: str,
) -> bool:
    existing = conn.execute(
        "SELECT id FROM links WHERE project_scope = ? AND from_artifact_id = ? AND to_artifact_id = ? AND link_type = ?",
        (project_scope, from_artifact_id, to_artifact_id, link_type),
    ).fetchone()
    if existing:
        return False
    conn.execute(
        "INSERT INTO links (project_scope, from_artifact_id, to_artifact_id, link_type, source_path, evidence_anchor, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            project_scope,
            from_artifact_id,
            to_artifact_id,
            link_type,
            source_path,
            evidence_anchor,
            now_iso(),
        ),
    )
    return True


def _phase3_source_artifact_type(source_type: str) -> str:
    normalized = str(source_type or "").strip().lower()
    if normalized == "scenario":
        return "SCENARIO"
    if normalized == "security-decision":
        return "SECURITY"
    if normalized == "replay":
        return "VERIFY"
    return ""


def _phase3_source_stage(source_type: str) -> str:
    normalized = str(source_type or "").strip().lower()
    if normalized == "scenario":
        return "phase-3-scenario"
    if normalized == "security-decision":
        return "phase-3-security"
    if normalized == "replay":
        return "phase-3-replay"
    return "phase-3-source"


def project_phase3_trace_registry_to_trace_db(
    *,
    trace_db_path: Path,
    trace_registry_final: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    rows = trace_registry_final.get("rows", []) if isinstance(trace_registry_final, dict) else []
    confirmed_rows = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("binding_status", "")).strip() == "confirmed"
        and str(row.get("final_resolution", "")).strip() == "confirmed"
    ]
    if not confirmed_rows:
        return {
            "artifact_kind": "phase3-trace-db-projection.v1",
            "status": "no-confirmed-rows",
            "p3_indexed": False,
            "confirmed_row_count": 0,
            "indexed_source_count": 0,
            "test_artifact_count": 0,
            "implementation_artifact_count": 0,
            "link_count": 0,
            "trace_db_path": str(trace_db_path),
        }
    if not trace_db_path.exists():
        return {
            "artifact_kind": "phase3-trace-db-projection.v1",
            "status": "missing-trace-db",
            "p3_indexed": False,
            "confirmed_row_count": len(confirmed_rows),
            "indexed_source_count": 0,
            "test_artifact_count": 0,
            "implementation_artifact_count": 0,
            "link_count": 0,
            "trace_db_path": str(trace_db_path),
            "reason": "trace_db_missing",
        }

    conn = sqlite3.connect(trace_db_path)
    try:
        required_tables = {"registry_meta", "artifacts", "links"}
        try:
            missing_tables = sorted(table for table in required_tables if not _table_exists(conn, table))
        except sqlite3.DatabaseError:
            return {
                "artifact_kind": "phase3-trace-db-projection.v1",
                "status": "unavailable",
                "p3_indexed": False,
                "confirmed_row_count": len(confirmed_rows),
                "indexed_source_count": 0,
                "test_artifact_count": 0,
                "implementation_artifact_count": 0,
                "link_count": 0,
                "trace_db_path": str(trace_db_path),
                "reason": "trace_db_not_sqlite",
            }
        if missing_tables:
            return {
                "artifact_kind": "phase3-trace-db-projection.v1",
                "status": "unavailable",
                "p3_indexed": False,
                "confirmed_row_count": len(confirmed_rows),
                "indexed_source_count": 0,
                "test_artifact_count": 0,
                "implementation_artifact_count": 0,
                "link_count": 0,
                "trace_db_path": str(trace_db_path),
                "reason": "trace_db_schema_incomplete",
                "missing_tables": missing_tables,
            }
        project_scope = _trace_db_project_scope(conn)
        if not project_scope:
            return {
                "artifact_kind": "phase3-trace-db-projection.v1",
                "status": "unavailable",
                "p3_indexed": False,
                "confirmed_row_count": len(confirmed_rows),
                "indexed_source_count": 0,
                "test_artifact_count": 0,
                "implementation_artifact_count": 0,
                "link_count": 0,
                "trace_db_path": str(trace_db_path),
                "reason": "project_scope_unresolved",
            }

        source_path_text = str(source_path)
        test_artifact_ids: set[str] = set()
        implementation_artifact_ids: set[str] = set()
        indexed_source_ids: set[str] = set()
        skipped_rows: list[dict[str, str]] = []
        inserted_link_count = 0

        for row in confirmed_rows:
            source_id = str(row.get("source_id", "")).strip().upper()
            source_type = str(row.get("source_type", "")).strip()
            if not source_id:
                skipped_rows.append({"source_id": "", "reason": "missing_source_id"})
                continue
            if not _artifact_exists(conn, project_scope, source_id):
                phase3_source_type = _phase3_source_artifact_type(source_type)
                if not phase3_source_type:
                    skipped_rows.append({"source_id": source_id, "reason": "source_artifact_not_registered"})
                    continue
                _upsert_trace_artifact(
                    conn,
                    project_scope=project_scope,
                    artifact_id=source_id,
                    artifact_type=phase3_source_type,
                    stage_or_lane=_phase3_source_stage(source_type),
                    status="confirmed",
                    source_path=source_path_text,
                    source_anchor=source_id.lower(),
                )
            test_targets = sorted({str(item).strip() for item in row.get("test_targets", []) if str(item).strip()})
            implementation_targets = sorted(
                {str(item).strip() for item in row.get("implementation_targets", []) if str(item).strip()}
            )
            if not test_targets or not implementation_targets:
                skipped_rows.append({"source_id": source_id, "reason": "missing_test_or_implementation_target"})
                continue

            indexed_source_ids.add(source_id)
            evidence_anchor = source_id.lower()
            row_test_artifact_ids: set[str] = set()
            for test_target in test_targets:
                test_artifact_id = stable_artifact_id("P3-VERIFY", test_target)
                test_artifact_ids.add(test_artifact_id)
                row_test_artifact_ids.add(test_artifact_id)
                _upsert_trace_artifact(
                    conn,
                    project_scope=project_scope,
                    artifact_id=test_artifact_id,
                    artifact_type="VERIFY",
                    stage_or_lane="phase-3-test",
                    status="confirmed",
                    source_path=test_target,
                    source_anchor=evidence_anchor,
                )
                if _insert_trace_link(
                    conn,
                    project_scope=project_scope,
                    from_artifact_id=source_id,
                    to_artifact_id=test_artifact_id,
                    link_type="verified_by",
                    source_path=source_path_text,
                    evidence_anchor=evidence_anchor,
                ):
                    inserted_link_count += 1

            for implementation_target in implementation_targets:
                implementation_artifact_id = stable_artifact_id("P3-IMPL", implementation_target)
                implementation_artifact_ids.add(implementation_artifact_id)
                _upsert_trace_artifact(
                    conn,
                    project_scope=project_scope,
                    artifact_id=implementation_artifact_id,
                    artifact_type="SERVICE",
                    stage_or_lane="phase-3-implementation",
                    status="confirmed",
                    source_path=implementation_target,
                    source_anchor=evidence_anchor,
                )
                if _insert_trace_link(
                    conn,
                    project_scope=project_scope,
                    from_artifact_id=source_id,
                    to_artifact_id=implementation_artifact_id,
                    link_type="implemented_by",
                    source_path=source_path_text,
                    evidence_anchor=evidence_anchor,
                ):
                    inserted_link_count += 1

                for test_artifact_id in row_test_artifact_ids:
                    if _insert_trace_link(
                        conn,
                        project_scope=project_scope,
                        from_artifact_id=test_artifact_id,
                        to_artifact_id=implementation_artifact_id,
                        link_type="exercises",
                        source_path=source_path_text,
                        evidence_anchor=evidence_anchor,
                    ):
                        inserted_link_count += 1

        conn.commit()
        confirmed_source_ids = {
            str(row.get("source_id", "")).strip().upper()
            for row in confirmed_rows
            if str(row.get("source_id", "")).strip()
        }
        p3_indexed = indexed_source_ids == confirmed_source_ids and not skipped_rows
        return {
            "artifact_kind": "phase3-trace-db-projection.v1",
            "status": "indexed" if p3_indexed else "partial",
            "p3_indexed": p3_indexed,
            "confirmed_row_count": len(confirmed_rows),
            "indexed_source_count": len(indexed_source_ids),
            "test_artifact_count": len(test_artifact_ids),
            "implementation_artifact_count": len(implementation_artifact_ids),
            "link_count": inserted_link_count,
            "trace_db_path": str(trace_db_path),
            "project_scope": project_scope,
            "skipped_rows": skipped_rows,
        }
    finally:
        conn.close()


def initialize_phase3_trace_registry(test_trace_matrix: dict[str, Any]) -> dict[str, Any]:
    rows = test_trace_matrix.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("test trace matrix must contain rows")
    registry_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        registry_rows.append(
            {
                "source_id": str(row.get("source_id", "")).strip(),
                "source_type": str(row.get("source_type", "")).strip(),
                "source_subject": str(row.get("source_subject", "")).strip(),
                "upstream_trace_ids": list(row.get("upstream_trace_ids", [])),
                "linked_rbi_or_wp": list(row.get("linked_rbi_or_wp", [])),
                "test_targets": list(row.get("test_targets", [])),
                "implementation_targets": [],
                "work_packages": [],
                "binding_status": "pending-implementation",
                "verification_hook": str(row.get("verification_hook", "")).strip(),
            }
        )
    return {
        "rows": registry_rows,
        "summary": {
            "source_count": len(registry_rows),
            "pending_source_count": len(registry_rows),
            "resolved_source_count": 0,
        },
        "source_matrix": trace_matrix_source_summary(test_trace_matrix, len(registry_rows)),
    }


def trace_matrix_source_summary(test_trace_matrix: dict[str, Any], row_count: int) -> dict[str, Any]:
    summary = test_trace_matrix.get("summary", {})
    matrix_row_count = row_count
    if isinstance(summary, dict) and isinstance(summary.get("matrix_row_count"), (int, float)):
        matrix_row_count = int(summary["matrix_row_count"])
    return {
        "row_count": matrix_row_count,
        "sidecar_unavailable": bool(test_trace_matrix.get("sidecar_unavailable", False)),
        "sidecar_id": str(test_trace_matrix.get("sidecar_id") or "").strip(),
        "reason": str(test_trace_matrix.get("reason") or "").strip(),
    }


def parse_bindings(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not payload:
        return {}
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        return {}
    mapping: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "")).strip()
        if not source_id:
            continue
        implementation_targets = sorted(
            {
                str(item).strip()
                for item in row.get("implementation_targets", [])
                if str(item).strip()
            }
        )
        work_packages = sorted({str(item).strip() for item in row.get("work_packages", []) if str(item).strip()})
        runtime_evidence_refs = sorted(
            {str(item).strip() for item in row.get("runtime_evidence_refs", []) if str(item).strip()}
        )
        mapping[source_id.upper()] = {
            "operation_id": str(row.get("operation_id", "")).strip(),
            "implementation_targets": implementation_targets,
            "work_packages": work_packages,
            "runtime_evidence_refs": runtime_evidence_refs,
            "binding_status": str(row.get("binding_status", "")).strip() or (
                "bound" if implementation_targets else "unbound"
            ),
        }
    return mapping


def trace_tokens(value: str) -> set[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    tokens: set[str] = set()
    for raw_token in re.split(r"[^A-Za-z0-9]+", expanded):
        token = raw_token.lower()
        if len(token) < 4 or token in TRACE_LINK_STOPWORDS:
            continue
        tokens.add(token)
        if token.endswith("ies") and len(token) > 4:
            tokens.add(token[:-3] + "y")
        elif token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "us", "is")):
            tokens.add(token[:-1])
    return tokens


def semantic_trace_tokens(value: str) -> set[str]:
    tokens = trace_tokens(value)
    expanded = set(tokens)
    for token in tokens:
        if token.endswith("ing") and len(token) > 6:
            root = token[:-3]
            if len(root) >= 4:
                expanded.add(root)
    return expanded


def compact_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def operation_from_contract_targets(test_targets: list[str]) -> str:
    contract_targets = [
        str(target).split("/")[-1].removesuffix(".contract.test.ts")
        for target in test_targets
        if str(target).startswith("tests/contracts/") and str(target).endswith(".contract.test.ts")
    ]
    return contract_targets[0] if len(contract_targets) == 1 else ""


def infer_operation_id(row: dict[str, Any], binding: dict[str, Any], test_targets: list[str]) -> str:
    explicit = str(binding.get("operation_id", "")).strip()
    if explicit:
        return explicit
    target_operation = operation_from_contract_targets(test_targets)
    if target_operation:
        return target_operation
    hook = str(row.get("verification_hook", "")).strip()
    match = re.search(r"`([A-Za-z][A-Za-z0-9]+)`?", hook)
    if match:
        return match.group(1)
    match = re.match(r"^\s*([A-Za-z][A-Za-z0-9]+)\s*/", hook)
    if match:
        return match.group(1)
    return ""


def target_matches_operation(target: str, operation_id: str) -> bool:
    if not operation_id:
        return False
    operation_compact = compact_token(operation_id)
    target_compact = compact_token(target)
    if operation_compact and operation_compact in target_compact:
        return True
    operation_tokens = trace_tokens(operation_id)
    target_tokens = trace_tokens(target)
    if any(token in operation_compact for token in target_tokens):
        return True
    return bool(operation_tokens) and len(operation_tokens & target_tokens) >= min(2, len(operation_tokens))


def source_test_evidence_matches_runtime(test_targets: list[str], runtime_evidence_refs: list[str]) -> list[str]:
    test_compacts = {compact_token(target) for target in test_targets if compact_token(target)}
    return [
        target
        for target in runtime_evidence_refs
        if compact_token(target) in test_compacts
    ]


def source_module_tokens(row: dict[str, Any], operation_id: str, test_targets: list[str]) -> set[str]:
    return semantic_trace_tokens(
        " ".join(
            [
                str(row.get("source_subject", "")),
                str(row.get("verification_hook", "")),
                operation_id,
                " ".join(test_targets),
            ]
        )
    )


def module_target_matches_source(
    row: dict[str, Any],
    operation_id: str,
    test_targets: list[str],
    implementation_targets: list[str],
) -> list[str]:
    source_tokens = source_module_tokens(row, operation_id, test_targets)
    operation_tokens = semantic_trace_tokens(operation_id)
    matches: list[str] = []
    for target in implementation_targets:
        if not target.startswith("apps/api/src/modules/"):
            continue
        target_tokens = semantic_trace_tokens(target)
        if operation_tokens and target_tokens and (operation_tokens & target_tokens):
            matches.append(target)
            continue
        if not operation_tokens and source_tokens and target_tokens and (source_tokens & target_tokens):
            matches.append(target)
    return matches


def source_mentions_operation(row: dict[str, Any], operation_id: str) -> bool:
    if not operation_id:
        return False
    source_text = " ".join(
        [
            str(row.get("source_subject", "")),
            str(row.get("verification_hook", "")),
        ]
    )
    operation_compact = compact_token(operation_id)
    source_compact = compact_token(source_text)
    if operation_compact and operation_compact in source_compact:
        return True
    operation_tokens = trace_tokens(operation_id)
    source_tokens = trace_tokens(source_text)
    return bool(operation_tokens) and len(operation_tokens & source_tokens) >= min(2, len(operation_tokens))


def build_trace_link_evidence(
    *,
    row: dict[str, Any],
    binding: dict[str, Any],
    test_targets: list[str],
    implementation_targets: list[str],
    runtime_evidence_refs: list[str],
) -> dict[str, Any]:
    source_type = str(row.get("source_type", "")).strip().lower()
    operation_id = infer_operation_id(row, binding, test_targets)
    source_operation_match = source_mentions_operation(row, operation_id)
    contract_target_matches = [
        target for target in test_targets if target.startswith("tests/contracts/") and target_matches_operation(target, operation_id)
    ]
    implementation_target_matches = [
        target for target in implementation_targets if target.startswith("apps/api/") and target_matches_operation(target, operation_id)
    ]
    runtime_target_matches = [
        target
        for target in runtime_evidence_refs
        if target.startswith("tests/contracts/") and target_matches_operation(target, operation_id)
    ]
    source_runtime_matches = source_test_evidence_matches_runtime(test_targets, runtime_evidence_refs)
    module_source_matches = module_target_matches_source(row, operation_id, test_targets, implementation_targets)

    confirmed_by: list[str] = []
    review_reasons: list[str] = []
    if source_type == "contract-trace":
        if source_operation_match:
            confirmed_by.append("source_mentions_operation")
        else:
            review_reasons.append("source_does_not_match_operation")
        if contract_target_matches:
            confirmed_by.append("contract_test_matches_operation")
        else:
            review_reasons.append("contract_test_does_not_match_operation")
        if implementation_target_matches:
            confirmed_by.append("implementation_target_matches_operation")
        else:
            review_reasons.append("implementation_target_does_not_match_operation")
        if runtime_target_matches:
            confirmed_by.append("runtime_evidence_matches_operation")

        confirmed = source_operation_match and bool(contract_target_matches) and bool(implementation_target_matches)
    else:
        source_id = str(row.get("source_id", "")).strip()
        source_identity_matches = [
            target for target in test_targets if compact_token(source_id) and compact_token(source_id) in compact_token(target)
        ]
        primary_tests = [
            target
            for target in test_targets
            if target.startswith(("tests/scenarios/", "tests/replays/", "tests/unit/api/foundation/"))
        ]
        if source_type == "security-decision":
            source_identity_matches = primary_tests
        has_work_or_impl = bool(implementation_targets)
        if source_identity_matches:
            confirmed_by.append("source_test_target_matches_source_id")
        else:
            review_reasons.append("source_test_target_does_not_match_source_id")
        if primary_tests:
            confirmed_by.append("source_specific_test_target_present")
        else:
            review_reasons.append("source_specific_test_target_missing")
        if has_work_or_impl:
            confirmed_by.append("implementation_target_present")
        else:
            review_reasons.append("implementation_target_missing")
        if source_runtime_matches:
            confirmed_by.append("runtime_evidence_matches_source_test")
        else:
            review_reasons.append("runtime_evidence_does_not_match_source_test")
        operation_required = source_type in {"scenario", "replay"} and bool(operation_id)
        if operation_required:
            if implementation_target_matches:
                confirmed_by.append("implementation_target_matches_operation")
            elif module_source_matches and source_runtime_matches:
                confirmed_by.append("module_target_matches_source_context")
            else:
                review_reasons.append("implementation_target_does_not_match_operation")
        elif source_type in {"scenario", "replay"}:
            if module_source_matches and source_runtime_matches:
                confirmed_by.append("module_target_matches_source_context")
            else:
                review_reasons.append("operation_identity_missing")
        confirmed = bool(
            primary_tests
            and source_identity_matches
            and has_work_or_impl
            and source_runtime_matches
            and (not operation_required or implementation_target_matches or module_source_matches)
            and "operation_identity_missing" not in review_reasons
        )

    return {
        "operation_id": operation_id,
        "confirmed": confirmed,
        "confirmed_by": confirmed_by,
        "review_reasons": review_reasons,
        "matched_contract_tests": contract_target_matches,
        "matched_implementation_targets": sorted(set([*implementation_target_matches, *module_source_matches])),
        "matched_runtime_evidence_refs": sorted(set([*runtime_target_matches, *source_runtime_matches])),
    }


def finalize_trace_registry(
    *,
    test_trace_matrix: dict[str, Any],
    implementation_bindings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = test_trace_matrix.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("test trace matrix must contain rows")

    binding_by_source = parse_bindings(implementation_bindings)
    final_rows: list[dict[str, Any]] = []
    unresolved_trace_ids: list[str] = []
    review_trace_ids: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "")).strip().upper()
        source_type = str(row.get("source_type", "")).strip()
        test_targets = sorted({str(item).strip() for item in row.get("test_targets", []) if str(item).strip()})
        binding = binding_by_source.get(source_id, {})
        implementation_targets = list(binding.get("implementation_targets", []))
        work_packages = list(binding.get("work_packages", []))
        runtime_evidence_refs = list(binding.get("runtime_evidence_refs", []))
        mechanically_bound = bool(test_targets and implementation_targets)
        trace_link_evidence = build_trace_link_evidence(
            row=row,
            binding=binding,
            test_targets=test_targets,
            implementation_targets=implementation_targets,
            runtime_evidence_refs=runtime_evidence_refs,
        )
        confirmed = mechanically_bound and bool(trace_link_evidence.get("confirmed"))
        review_bound = mechanically_bound and not confirmed
        if not mechanically_bound:
            unresolved_trace_ids.append(source_id)
        elif review_bound:
            unresolved_trace_ids.append(source_id)
            review_trace_ids.append(source_id)
        binding_status = "confirmed" if confirmed else "review" if review_bound else "unbound"
        final_resolution = "confirmed" if confirmed else "review" if review_bound else "unresolved"
        final_rows.append(
            {
                "source_id": source_id,
                "source_type": source_type,
                "source_subject": str(row.get("source_subject", "")).strip(),
                "upstream_trace_ids": row.get("upstream_trace_ids", []),
                "verification_hook": str(row.get("verification_hook", "")).strip(),
                "test_targets": test_targets,
                "implementation_targets": implementation_targets,
                "work_packages": work_packages,
                "runtime_evidence_refs": runtime_evidence_refs,
                "binding_status": binding_status,
                "final_resolution": final_resolution,
                "trace_link_evidence": trace_link_evidence,
            }
        )

    source_type_breakdown: dict[str, int] = {}
    for row in final_rows:
        source_type_breakdown[row["source_type"]] = source_type_breakdown.get(row["source_type"], 0) + 1

    return {
        "rows": final_rows,
        "summary": {
            "source_count": len(final_rows),
            "resolved_source_count": len(final_rows) - len(unresolved_trace_ids),
            "confirmed_source_count": len(final_rows) - len(unresolved_trace_ids),
            "review_source_count": len(review_trace_ids),
            "unresolved_source_count": len(unresolved_trace_ids),
            "unresolved_trace_ids": unresolved_trace_ids,
            "review_trace_ids": review_trace_ids,
            "source_type_breakdown": source_type_breakdown,
        },
        "source_matrix": trace_matrix_source_summary(test_trace_matrix, len(final_rows)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Finalize the Phase-3 trace registry")
    parser.add_argument("--test-trace-matrix", required=True)
    parser.add_argument("--implementation-bindings")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = finalize_trace_registry(
        test_trace_matrix=load_json(Path(args.test_trace_matrix).resolve()),
        implementation_bindings=load_json(Path(args.implementation_bindings).resolve()) if args.implementation_bindings else None,
    )
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), **report["summary"]}, ensure_ascii=False))
    return 0 if not report["summary"]["unresolved_trace_ids"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
