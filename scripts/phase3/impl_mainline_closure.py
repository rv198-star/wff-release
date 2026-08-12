from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from common.agentic_decision_authority import write_json_atomic
from phase3.agentic_implementation_authority import (
    build_authority_delta_ledger,
    finalize_p3_agentic_implementation_application,
    validate_authority_delta_ledger,
    validate_authority_delta_records,
)
from phase3.backend_implementation_scaffolder import scaffold_backend_implementation
from phase3.foundation_mainline import carry_phase2_trace_identity_source
from phase3.impl_context import load_phase2_source_texts
from phase3.impl_verification_pack import run_impl_verification
from phase3.s3_code_realization import generate_s3_db_support, realize_s3_code_and_tests


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    write_json_atomic(path, dict(payload))


def _passed_tests(report_path: str | Path | None) -> list[str]:
    if not report_path:
        return []
    payload = _load_json(Path(report_path))
    values = payload.get("passed_tests", [])
    if not isinstance(values, list):
        return []
    return sorted({str(item).strip().replace("\\", "/") for item in values if str(item).strip()})


_VERIFICATION_REPORT_KEYS = (
    "targeted_test_report_path",
    "full_test_report_path",
    "unit_test_report_path",
    "sql_test_report_path",
    "contract_test_report_path",
    "scenario_test_report_path",
    "replay_test_report_path",
)


def _normalized_test_values(payload: Mapping[str, Any], key: str) -> set[str]:
    values = payload.get(key, [])
    if not isinstance(values, list):
        return set()
    return {
        str(item).strip().replace("\\", "/")
        for item in values
        if str(item).strip()
    }


def _verification_passed_tests(verification: Mapping[str, Any]) -> list[str]:
    passed: set[str] = set()
    failed: set[str] = set()
    for key in _VERIFICATION_REPORT_KEYS:
        raw = verification.get(key)
        if not raw:
            continue
        payload = _load_json(Path(str(raw)))
        passed.update(_normalized_test_values(payload, "passed_tests"))
        failed.update(_normalized_test_values(payload, "failed_tests"))
    return sorted(passed - failed)


def _runtime_evidence_ref(output_dir: Path, report_path: Path) -> str:
    resolved_output = output_dir.resolve()
    resolved_report = report_path.resolve()
    try:
        return str(resolved_report.relative_to(resolved_output)).replace("\\", "/")
    except ValueError:
        return str(resolved_report).replace("\\", "/")


def _verification_report_evidence_by_test(
    *,
    output_dir: Path,
    verification: Mapping[str, Any],
    globally_passed_tests: set[str],
) -> dict[str, list[str]]:
    evidence_by_test: dict[str, set[str]] = {}
    for key in _VERIFICATION_REPORT_KEYS:
        raw = verification.get(key)
        if not raw:
            continue
        report_path = Path(str(raw))
        payload = _load_json(report_path)
        report_passed = _normalized_test_values(payload, "passed_tests")
        report_failed = _normalized_test_values(payload, "failed_tests")
        effective = (report_passed - report_failed).intersection(globally_passed_tests)
        if not effective:
            continue
        ref = _runtime_evidence_ref(output_dir, report_path)
        for test_ref in effective:
            evidence_by_test.setdefault(test_ref, set()).add(ref)
    return {key: sorted(values) for key, values in evidence_by_test.items()}


def _declared_operation_ids(evidence_text: str) -> list[str]:
    """Read the explicit generated `operationIds` set without inferring new operation authority."""
    match = re.search(r"\boperationIds\b[^=]*=\s*\[([^\]]*)\]", evidence_text)
    if not match:
        return []
    return list(dict.fromkeys(re.findall(r"[\"']([A-Za-z][A-Za-z0-9]*)[\"']", match.group(1))))


def _unique_values(rows: list[Mapping[str, Any]], key: str) -> list[str]:
    result: list[str] = []
    for row in rows:
        for item in row.get(key, []) if isinstance(row.get(key), list) else []:
            value = str(item).strip()
            if value and value not in result:
                result.append(value)
    return result


def project_trace_evidence_bindings(
    *,
    output_dir: Path,
    test_trace_matrix: Mapping[str, Any],
) -> dict[str, Any]:
    """Add evidence-only scenario/replay bindings without changing accepted contract authority."""
    bindings_path = output_dir / "implementation-bindings.json"
    bindings = _load_json(bindings_path)
    rows = bindings.get("rows", []) if isinstance(bindings.get("rows"), list) else []
    authoritative_rows = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("operation_id") or "").strip()
        and not str(row.get("binding_authority") or "").strip()
    ]
    by_source_id = {
        str(row.get("source_id") or "").strip().upper(): row
        for row in rows
        if isinstance(row, dict) and str(row.get("source_id") or "").strip()
    }
    operations = {
        str(row.get("operation_id") or "").strip(): row
        for row in authoritative_rows
        if str(row.get("operation_id") or "").strip()
    }
    added: list[dict[str, Any]] = []
    ambiguous: list[str] = []
    unresolved: list[str] = []
    unknown_operation_ids: dict[str, list[str]] = {}
    for matrix_row in test_trace_matrix.get("rows", []):
        if not isinstance(matrix_row, dict):
            continue
        source_id = str(matrix_row.get("source_id") or "").strip()
        if not source_id or source_id.upper() in by_source_id:
            continue
        source_type = str(matrix_row.get("source_type") or "").strip()
        if source_type == "contract-trace":
            # Exact contract identity is Authority-owned. Never repair a contract-id mismatch by operation similarity.
            unresolved.append(source_id)
            continue
        test_targets = sorted({str(item).strip().replace("\\", "/") for item in matrix_row.get("test_targets", []) if str(item).strip()})
        evidence_text = "\n".join(
            [
                str(matrix_row.get("source_subject") or ""),
                str(matrix_row.get("verification_hook") or ""),
                *test_targets,
                *[
                    (output_dir / target).read_text(encoding="utf-8", errors="ignore")
                    for target in test_targets
                    if (output_dir / target).is_file()
                ],
            ]
        )
        declared_operation_ids = _declared_operation_ids(evidence_text)
        if declared_operation_ids:
            unknown = [operation_id for operation_id in declared_operation_ids if operation_id not in operations]
            if unknown:
                unknown_operation_ids[source_id] = unknown
                unresolved.append(source_id)
                continue
            matches = declared_operation_ids
        else:
            matches = [operation_id for operation_id in operations if operation_id and operation_id in evidence_text]

        if not matches:
            unresolved.append(source_id)
            continue
        if len(matches) > 1:
            if not declared_operation_ids or source_type not in {"scenario", "replay"}:
                ambiguous.append(source_id)
                continue
            owners = [operations[operation_id] for operation_id in matches]
            authority_contract_ids = [
                str(owner.get("contract_id") or owner.get("source_id") or "").strip()
                for owner in owners
            ]
            decision_ids = list(
                dict.fromkeys(str(owner.get("implementation_decision_id") or "").strip() for owner in owners)
            )
            decision_digests = list(
                dict.fromkeys(str(owner.get("implementation_decision_digest") or "").strip() for owner in owners)
            )
            implementation_targets = _unique_values(owners, "implementation_targets")
            if (
                any(not contract_id for contract_id in authority_contract_ids)
                or any(not list(owner.get("implementation_targets", [])) for owner in owners)
                or len(decision_ids) != 1
                or len(decision_digests) != 1
                or not decision_ids[0]
                or not decision_digests[0]
            ):
                unresolved.append(source_id)
                continue
            derived = {
                "source_id": source_id,
                "source_type": source_type,
                "source_subject": str(matrix_row.get("source_subject") or "").strip(),
                "operation_id": "",
                "operation_ids": matches,
                "contract_id": source_id,
                "authority_contract_ids": authority_contract_ids,
                "implementation_decision_id": decision_ids[0],
                "implementation_decision_digest": decision_digests[0],
                "implementation_targets": implementation_targets,
                "test_targets": test_targets,
                "work_packages": _unique_values(owners, "work_packages"),
                "runtime_evidence_refs": [],
                "binding_status": "generated-not-executed",
                "binding_authority": "derived-multi-operation-evidence-only-from-explicit-operation-set",
            }
            rows.append(derived)
            by_source_id[source_id.upper()] = derived
            added.append({"source_id": source_id, "operation_ids": matches})
            continue

        operation_id = matches[0]
        owner = operations[operation_id]
        derived = {
            "source_id": source_id,
            "source_type": source_type,
            "source_subject": str(matrix_row.get("source_subject") or "").strip(),
            "operation_id": operation_id,
            "contract_id": source_id,
            "authority_contract_id": str(owner.get("contract_id") or owner.get("source_id") or "").strip(),
            "implementation_decision_id": str(owner.get("implementation_decision_id") or "").strip(),
            "implementation_decision_digest": str(owner.get("implementation_decision_digest") or "").strip(),
            "implementation_targets": list(owner.get("implementation_targets", [])),
            "test_targets": test_targets,
            "work_packages": list(owner.get("work_packages", [])),
            "runtime_evidence_refs": [],
            "binding_status": "generated-not-executed",
            "binding_authority": "derived-evidence-only-from-explicit-operation-reference",
        }
        rows.append(derived)
        by_source_id[source_id.upper()] = derived
        added.append({"source_id": source_id, "operation_id": operation_id})
    bindings["rows"] = rows
    bindings["trace_evidence_projection"] = {
        "added_count": len(added),
        "added": added,
        "ambiguous_source_ids": sorted(ambiguous),
        "unresolved_source_ids": sorted(unresolved),
        "unknown_operation_ids": {key: value for key, value in sorted(unknown_operation_ids.items())},
        "rule": "Scenario/replay evidence may bind one exact accepted operation or an explicit exact operationIds set; contract-trace identities remain exact-only and are never repaired by operation similarity.",
    }
    _write_json(bindings_path, bindings)
    return bindings["trace_evidence_projection"]


def bind_runtime_evidence(
    *,
    output_dir: Path,
    verification: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind passed-test identities and retained reports without changing accepted S2/P3 authority."""
    bindings_path = output_dir / "implementation-bindings.json"
    bindings = _load_json(bindings_path)
    rows = bindings.get("rows", []) if isinstance(bindings.get("rows"), list) else []
    non_operation_rows = (
        bindings.get("non_operation_rows", []) if isinstance(bindings.get("non_operation_rows"), list) else []
    )
    execution_rows = [*rows, *non_operation_rows]
    passed_tests = set(_verification_passed_tests(verification))
    evidence_by_test = _verification_report_evidence_by_test(
        output_dir=output_dir,
        verification=verification,
        globally_passed_tests=passed_tests,
    )

    bound_count = 0
    bound_non_operation_count = 0
    for row in execution_rows:
        if not isinstance(row, dict):
            continue
        test_targets = {
            str(item).strip().replace("\\", "/")
            for item in row.get("test_targets", [])
            if str(item).strip()
        }
        matched = sorted(test_targets & passed_tests)
        existing_test_refs = {
            str(item).strip().replace("\\", "/")
            for item in row.get("runtime_test_refs", [])
            if str(item).strip() and str(item).strip().replace("\\", "/") in passed_tests
        }
        legacy_test_refs = {
            str(item).strip().replace("\\", "/")
            for item in row.get("runtime_evidence_refs", [])
            if str(item).strip().replace("\\", "/") in passed_tests
        }
        runtime_test_refs = sorted(existing_test_refs | legacy_test_refs | set(matched))
        retained_report_refs = {
            str(item).strip().replace("\\", "/")
            for item in row.get("runtime_evidence_refs", [])
            if str(item).strip().lower().endswith(".json")
        }
        for test_ref in runtime_test_refs:
            retained_report_refs.update(evidence_by_test.get(test_ref, []))
        row["runtime_test_refs"] = runtime_test_refs
        row["runtime_evidence_refs"] = sorted(retained_report_refs)
        if runtime_test_refs:
            bound_count += 1
            if row.get("non_operation_realization_id"):
                bound_non_operation_count += 1
            if str(row.get("binding_status") or "") == "generated-not-executed":
                row["binding_status"] = "runtime-evidence-present"

    exact_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("binding_authority") or "").startswith("derived-"):
            continue
        operation_id = str(row.get("operation_id") or "").strip()
        contract_id = str(row.get("contract_id") or row.get("source_id") or "").strip()
        decision_id = str(row.get("implementation_decision_id") or "").strip()
        decision_digest = str(row.get("implementation_decision_digest") or "").strip()
        if operation_id and contract_id and decision_id and decision_digest:
            exact_by_key.setdefault((operation_id, contract_id, decision_id, decision_digest), []).append(row)

    projected_exact_row_ids: set[int] = set()
    projection_failures: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        binding_authority = str(row.get("binding_authority") or "")
        if not binding_authority.startswith("derived-"):
            continue
        runtime_test_refs = [str(item).strip() for item in row.get("runtime_test_refs", []) if str(item).strip()]
        runtime_evidence_refs = [str(item).strip() for item in row.get("runtime_evidence_refs", []) if str(item).strip()]
        if not runtime_test_refs or not runtime_evidence_refs:
            continue
        decision_id = str(row.get("implementation_decision_id") or "").strip()
        decision_digest = str(row.get("implementation_decision_digest") or "").strip()
        operation_ids = (
            [str(item).strip() for item in row.get("operation_ids", []) if str(item).strip()]
            if isinstance(row.get("operation_ids"), list)
            else []
        )
        contract_ids = (
            [str(item).strip() for item in row.get("authority_contract_ids", []) if str(item).strip()]
            if isinstance(row.get("authority_contract_ids"), list)
            else []
        )
        if not operation_ids:
            operation_id = str(row.get("operation_id") or "").strip()
            contract_id = str(row.get("authority_contract_id") or "").strip()
            operation_ids = [operation_id] if operation_id else []
            contract_ids = [contract_id] if contract_id else []
        if not operation_ids or len(operation_ids) != len(contract_ids):
            projection_failures.append({"source_id": row.get("source_id", ""), "reason": "operation-contract-set-invalid"})
            continue
        for operation_id, contract_id in zip(operation_ids, contract_ids):
            owners = exact_by_key.get((operation_id, contract_id, decision_id, decision_digest), [])
            if len(owners) != 1:
                projection_failures.append(
                    {
                        "source_id": row.get("source_id", ""),
                        "operation_id": operation_id,
                        "contract_id": contract_id,
                        "reason": "exact-owner-missing-or-ambiguous",
                    }
                )
                continue
            owner = owners[0]
            owner["runtime_test_refs"] = sorted(
                {
                    *[str(item).strip() for item in owner.get("runtime_test_refs", []) if str(item).strip()],
                    *runtime_test_refs,
                }
            )
            owner["runtime_evidence_refs"] = sorted(
                {
                    *[str(item).strip() for item in owner.get("runtime_evidence_refs", []) if str(item).strip().lower().endswith(".json")],
                    *runtime_evidence_refs,
                }
            )
            if str(owner.get("binding_status") or "") == "generated-not-executed":
                owner["binding_status"] = "runtime-evidence-present"
            projected_exact_row_ids.add(id(owner))

    bindings["execution_status"] = "executed" if passed_tests else "no-passed-runtime-evidence"
    bindings["runtime_evidence_summary"] = {
        "passed_test_count": len(passed_tests),
        "binding_rows_with_runtime_test_evidence": bound_count,
        "non_operation_rows_with_runtime_test_evidence": bound_non_operation_count,
        "exact_operation_rows_with_projected_runtime_evidence": len(projected_exact_row_ids),
        "projection_failures": projection_failures,
        "contract": "runtime_test_refs identify passed tests; runtime_evidence_refs identify retained parseable verification reports",
    }
    _write_json(bindings_path, bindings)
    return bindings["runtime_evidence_summary"]


def persist_authority_delta_ledger(
    *,
    output_dir: Path,
    authority: Mapping[str, Any],
    supplied_ledger: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if supplied_ledger is not None:
        ledger = dict(supplied_ledger)
        records = validate_authority_delta_ledger(ledger, authority=authority)
    else:
        records = validate_authority_delta_records(
            authority.get("authority_delta_records", []),
            known_slice_ids=set((authority.get("slice_decisions") or {}).keys()),
        )
        ledger = build_authority_delta_ledger(
            decision_id=str(authority.get("decision_id") or ""),
            decision_digest=str(authority.get("decision_digest") or ""),
            records=records,
        )
    _write_json(output_dir / ".phase3-evidence" / "p3-authority-delta-ledger.json", ledger)
    return records


def _write_trace_matrix(*, phase2_root: Path, output_dir: Path) -> dict[str, Any]:
    from phase3.test_trace_matrix_builder import build_test_trace_matrix

    esp_text, stage_03_text, stage_04_text = load_phase2_source_texts(phase2_root)
    matrix = build_test_trace_matrix(
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
    )
    _write_json(output_dir / "test-trace-matrix.json", matrix)
    return matrix


def _write_run_metadata(
    *,
    phase2_root: Path,
    output_dir: Path,
    title: str,
    version: str,
    authority: Mapping[str, Any],
    verification_mode: str,
    validation_level: str,
    full_targeted_evidence: bool,
) -> None:
    _write_json(
        output_dir / "phase3-run-metadata.json",
        {
            "artifact_kind": "phase3-run-metadata.v2",
            "case_name": title,
            "version": version,
            "phase2_root": str(phase2_root),
            "runner_actor": "run_impl",
            "generation_entrypoint": "scripts/phase3/run_impl.py",
            "mainline_verification_mode": verification_mode,
            "validation_level": validation_level,
            "full_targeted_evidence": full_targeted_evidence,
            "agentic_implementation_decision_id": str(authority.get("decision_id") or ""),
            "agentic_implementation_decision_digest": str(authority.get("decision_digest") or ""),
            "claim_ceiling": "Workflow metadata only; runtime and delivery claims require current-generation execution evidence.",
        },
    )


def _write_quality_report(
    *,
    phase2_root: Path,
    output_dir: Path,
    toolchain_report_path: Path,
) -> dict[str, Any]:
    from phase3.phase3_quality_check import analyze_phase3_bootstrap

    esp_text, stage_03_text, stage_04_text = load_phase2_source_texts(phase2_root)
    quality = analyze_phase3_bootstrap(
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        openapi_path=output_dir / "contracts" / "openapi.yaml",
        migration_path=output_dir / "db" / "migrations" / "001_initial_schema.sql",
        shared_types_path=output_dir / "packages" / "shared-types" / "index.ts",
        api_client_path=output_dir / "packages" / "api-client" / "index.ts",
        trace_registry_path=output_dir / "phase3-trace-registry-final.json",
        implementation_bindings_path=output_dir / "implementation-bindings.json",
        root_package_json_path=output_dir / "package.json",
        api_package_json_path=output_dir / "apps" / "api" / "package.json",
        toolchain_bootstrap_report_path=toolchain_report_path,
        contracts_dir=output_dir / "tests" / "contracts",
        scenarios_dir=output_dir / "tests" / "scenarios",
        replays_dir=output_dir / "tests" / "replays",
        test_trace_matrix_path=output_dir / "test-trace-matrix.json",
    )
    _write_json(output_dir / "phase3-quality-check.json", quality)
    return quality


def run_impl_mainline_closure(
    *,
    phase2_root: Path,
    output_dir: Path,
    authority: Mapping[str, Any],
    title: str,
    version: str,
    agentic_source_root: Path | None = None,
    authority_delta_ledger: Mapping[str, Any] | None = None,
    install_toolchain: bool = False,
    run_runtime_smoke: bool = False,
    verification_mode: str = "strict-runtime",
    validation_level: str = "strict",
    full_targeted_evidence: bool = True,
) -> dict[str, Any]:
    """Run the current modular S3->runtime/Trace closure. No semantic decision is created here."""
    phase2_root = phase2_root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_identity_source = carry_phase2_trace_identity_source(
        phase2_root=phase2_root,
        output_dir=output_dir,
    )

    delta_records = persist_authority_delta_ledger(
        output_dir=output_dir,
        authority=authority,
        supplied_ledger=authority_delta_ledger,
    )
    verification_generation = run_impl_verification(
        mode="generate-tests",
        workspace_root=output_dir,
        phase2_root=phase2_root,
        output_dir=output_dir,
    )
    backend = scaffold_backend_implementation(
        phase2_root=phase2_root,
        output_dir=output_dir,
        title=title,
        version=version,
        implementation_authority=authority,
    )
    db_schema = generate_s3_db_support(
        phase2_root=phase2_root,
        output_dir=output_dir,
        authority=authority,
        delta_records=delta_records,
    )
    realization = realize_s3_code_and_tests(
        output_dir=output_dir,
        authority=authority,
        agentic_source_root=agentic_source_root,
    )
    realization_status = str(realization.get("receipt", {}).get("status") or "")
    test_trace_matrix = _write_trace_matrix(phase2_root=phase2_root, output_dir=output_dir)
    trace_projection = project_trace_evidence_bindings(
        output_dir=output_dir,
        test_trace_matrix=test_trace_matrix,
    )
    _write_run_metadata(
        phase2_root=phase2_root,
        output_dir=output_dir,
        title=title,
        version=version,
        authority=authority,
        verification_mode=verification_mode,
        validation_level=validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )

    if realization_status == "authoring-required":
        return {
            "status": "authoring-required",
            "quality_gate": "blocked",
            "backend": backend,
            "db_schema": db_schema,
            "verification_generation": verification_generation,
            "realization": realization["receipt"],
            "trace_evidence_projection": trace_projection,
            "trace_identity_source": trace_identity_source,
            "execution": {"attempted": False, "status": "not-authorized-before-agentic-block-materialization"},
            "claim_ceiling": realization["receipt"].get("claim_ceiling", ""),
        }

    from phase3.mainline_backend_execution import execute_phase3_mainline_backend_verification
    from phase3.phase3_toolchain_bootstrap import bootstrap_phase3_toolchain
    from phase3.post_execution_refresh import refresh_phase3_post_execution

    strict_runtime = verification_mode == "strict-runtime"
    toolchain_report_path = output_dir / "phase3-toolchain-bootstrap.json"
    toolchain = bootstrap_phase3_toolchain(
        workspace_root=output_dir,
        install=bool(install_toolchain or strict_runtime),
        strict=strict_runtime,
        output_path=toolchain_report_path,
    )
    quality = _write_quality_report(
        phase2_root=phase2_root,
        output_dir=output_dir,
        toolchain_report_path=toolchain_report_path,
    )
    if strict_runtime and str(toolchain.get("overall_status") or "") != "ready":
        return {
            "status": "toolchain-blocked",
            "quality_gate": "blocked",
            "backend": backend,
            "db_schema": db_schema,
            "verification_generation": verification_generation,
            "realization": realization["receipt"],
            "trace_identity_source": trace_identity_source,
            "toolchain": toolchain,
            "bootstrap_quality": quality,
            "execution": {"attempted": False, "status": "toolchain-blocked"},
            "claim_ceiling": "Strict runtime closure requires a ready Node/pnpm/Docker toolchain.",
        }

    execution = execute_phase3_mainline_backend_verification(
        output_dir=output_dir,
        implementation_bindings_path=output_dir / "implementation-bindings.json",
        actor="run_impl",
        note="current modular P3 aggregate runtime verification",
        validation_level=validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )
    runtime_binding_summary = bind_runtime_evidence(output_dir=output_dir, verification=execution)
    refresh = refresh_phase3_post_execution(
        output_dir,
        strict_runtime_closure=strict_runtime,
        run_runtime_smoke=run_runtime_smoke,
        toolchain_bootstrap_report_path=toolchain_report_path,
        unit_test_report_path=Path(str(execution.get("unit_test_report_path"))) if execution.get("unit_test_report_path") else None,
        wp_gate_report_path=Path(str(execution.get("wp_gate_report_path"))) if execution.get("wp_gate_report_path") else None,
        verification_ledger_report_path=Path(str(execution.get("verification_ledger_path"))) if execution.get("verification_ledger_path") else None,
        runtime_smoke_report_path=Path(str(execution.get("runtime_smoke_report_path"))) if execution.get("runtime_smoke_report_path") else None,
    )
    application = finalize_p3_agentic_implementation_application(output_dir=output_dir, authority=authority)
    blocking = int(application.get("ledger", {}).get("counts", {}).get("blocking", 0) or 0)
    phase_verdict = str(refresh.get("phase_verdict") or "")
    runtime_verdict = str(execution.get("overall_verdict") or "").lower()
    complete = bool(
        runtime_verdict in {"pass", "passed"}
        and phase_verdict.startswith("PASS")
        and blocking == 0
        and application.get("application", {}).get("application_status") == "complete"
    )
    return {
        "status": "runtime-closure-complete" if complete else "runtime-closure-blocked",
        "quality_gate": "pass" if complete else "blocked",
        "backend": backend,
        "db_schema": db_schema,
        "verification_generation": verification_generation,
        "realization": realization["receipt"],
        "trace_evidence_projection": trace_projection,
        "trace_identity_source": trace_identity_source,
        "toolchain": toolchain,
        "bootstrap_quality": quality,
        "execution": execution,
        "runtime_binding_summary": runtime_binding_summary,
        "post_execution_refresh": refresh,
        "semantic_realization": application.get("ledger", {}),
        "application": application.get("application", {}),
        "claim_ceiling": (
            "Current-generation modular P3 runtime, evidence, Trace, and exact binding closure passed; "
            "this remains development/pre-production proof and does not imply production readiness."
            if complete
            else "P3 modular closure remains blocked by named runtime, Trace, delivery, or exact-binding evidence."
        ),
    }
