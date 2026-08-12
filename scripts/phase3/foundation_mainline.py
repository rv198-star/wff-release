from __future__ import annotations

import importlib
import json
import shutil
from pathlib import Path
from typing import Any, Callable

from common.cross_phase_surface_policy import find_cross_phase_surface_path
from common.semantic_consistency import (
    build_semantic_realization_ledger,
    canonical_digest,
    load_json_object,
    p1_claim_control_from_authority,
    phase2_claim_control_verification_is_valid,
    verify_phase2_claim_control_report,
    verify_semantic_commitment_union,
)
from phase3.agentic_implementation_loop import write_agentic_implementation_loop_artifacts
from phase3.agentic_implementation_authority import (
    finalize_p3_agentic_implementation_application,
    p3_agentic_implementation_authority_is_valid,
)
from phase3.action_card_execution_map import build_action_card_execution_context
from phase3.contract_test_scaffolder import contract_test_filename
from phase3.contract_tools import slugify
from phase3.implementation_binding_tools import backend_module_unit_test_path, parse_openapi_operations
from phase2.project_language_handoff import build_project_language_handoff
from phase3.phase3_implementation_action_card_scaffolder import load_action_card_obligations
from phase3.project_implementation_conventions import parse_stack_decision_text, synthesize_project_implementation_conventions
from phase3.synthesis_boundary import write_phase3_synthesis_brief_artifacts
from phase3.timing_report import record_timing_segment, set_timing_segment, start_timer, write_phase3_timing_report
from phase3.trace_registry import project_phase3_trace_registry_to_trace_db
from phase3.validation_levels import build_validation_profile, normalize_validation_level


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_phase2_semantic_commitment_authority(phase2_root: Path) -> dict[str, Any]:
    persisted_union = load_json_object(
        find_cross_phase_surface_path(
            phase2_root,
            "phase2",
            "semantic-commitment-union.json",
        )
    )
    operation_source_obligations = load_json_object(
        find_cross_phase_surface_path(
            phase2_root,
            "phase2",
            "operation-source-obligation-matrix.json",
        )
    )
    p1_operation_resolutions = load_json_object(
        find_cross_phase_surface_path(
            phase2_root,
            "phase2",
            "p1-value-to-p2-operation-resolution-matrix.json",
        )
    )
    operation_semantics = load_json_object(
        find_cross_phase_surface_path(
            phase2_root,
            "phase2",
            "operation-behavior-semantics.json",
        )
    )
    p1_commitment_authority_path = find_cross_phase_surface_path(
        phase2_root,
        "phase2",
        "p1-commitment-authority.json",
    )
    p1_commitment_authority = load_json_object(p1_commitment_authority_path)
    p1_claim_control = p1_claim_control_from_authority(p1_commitment_authority)
    raw_p2_claim_control_report = load_json_object(
        phase2_root / "phase2-claim-control-report.json"
    )
    rebuilt_p2_claim_control = verify_phase2_claim_control_report(
        phase2_root=phase2_root,
        report=raw_p2_claim_control_report,
        p1_commitment_authority=p1_commitment_authority,
    )
    p2_claim_control_report = rebuilt_p2_claim_control["report"]
    p2_claim_control_verification = rebuilt_p2_claim_control["verification"]
    persisted_p2_verification = load_json_object(
        find_cross_phase_surface_path(
            phase2_root,
            "phase2",
            "phase2-claim-control-verification.json",
        )
    )
    persisted_p2_verification_matches = bool(
        phase2_claim_control_verification_is_valid(persisted_p2_verification)
        and str(persisted_p2_verification.get("content_digest") or "")
        == str(p2_claim_control_verification.get("content_digest") or "")
    )
    if not persisted_p2_verification_matches:
        p2_claim_control_verification = {
            **p2_claim_control_verification,
            "status": "blocked",
            "verified": False,
            "failures": sorted(
                set(
                    [
                        *(
                            p2_claim_control_verification.get("failures", [])
                            if isinstance(p2_claim_control_verification.get("failures"), list)
                            else []
                        ),
                        "persisted_phase2_claim_control_verification_mismatch",
                    ]
                )
            ),
        }
        p2_claim_control_verification["content_digest"] = canonical_digest(
            {
                key: p2_claim_control_verification[key]
                for key in p2_claim_control_verification
                if key != "content_digest"
            }
        )
    p2_commitment_disposition_ledger = load_json_object(
        phase2_root / "p2-commitment-disposition-ledger.json"
    )
    verification_result = verify_semantic_commitment_union(
        persisted_union=persisted_union,
        p1_claim_control=p1_claim_control,
        operation_source_obligations=operation_source_obligations,
        p1_operation_resolutions=p1_operation_resolutions,
        operation_semantics=operation_semantics,
        p2_claim_control_report=p2_claim_control_report,
        p1_commitment_authority=p1_commitment_authority,
        p2_claim_control_verification=p2_claim_control_verification,
        p2_commitment_disposition_ledger=p2_commitment_disposition_ledger,
    )
    return {
        "persisted_union": persisted_union,
        "rebuilt_union": verification_result["rebuilt_union"],
        "verification": verification_result["verification"],
        "p1_commitment_authority": p1_commitment_authority,
        "phase2_claim_control_verification": p2_claim_control_verification,
        "source_paths": {
            "p1_commitment_authority": str(p1_commitment_authority_path),
            "phase2_claim_control_report": str(
                phase2_root / "phase2-claim-control-report.json"
            ),
            "phase2_claim_control_verification": str(
                find_cross_phase_surface_path(
                    phase2_root,
                    "phase2",
                    "phase2-claim-control-verification.json",
                )
            ),
        },
    }


def write_semantic_realization_ledger(
    *,
    phase2_root: Path,
    output_dir: Path,
    implementation_bindings: dict[str, Any],
    trace_registry_final: dict[str, Any],
) -> dict[str, Any]:
    authority = load_phase2_semantic_commitment_authority(phase2_root)
    persisted_union = authority["persisted_union"]
    if not persisted_union:
        return {}
    ledger = build_semantic_realization_ledger(
        commitment_union=authority["rebuilt_union"],
        implementation_bindings=implementation_bindings,
        trace_registry_final=trace_registry_final,
        commitment_union_verification=authority["verification"],
        authority_source_paths=authority["source_paths"],
    )
    write_json(output_dir / "semantic-realization-ledger.json", ledger)
    return ledger


def carry_phase2_trace_identity_source(*, phase2_root: Path, output_dir: Path) -> dict[str, Any]:
    source = phase2_root / ".trace" / "trace.db"
    target = output_dir / ".trace" / "trace.db"
    if not source.exists():
        return {
            "status": "missing",
            "source": str(source),
            "target": str(target),
            "trace_db_present": False,
            "reason": "phase2_trace_db_missing",
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return {
        "status": "carried",
        "source": str(source),
        "target": str(target),
        "trace_db_present": target.exists(),
        "size_bytes": target.stat().st_size if target.exists() else 0,
    }


def optional_phase3_diagnostic_module(module_name: str):
    try:
        return importlib.import_module(f"phase3.{module_name}")
    except ModuleNotFoundError as exc:
        if exc.name == f"phase3.{module_name}":
            return None
        raise


def diagnostic_sidecar_unavailable_summary(sidecar_id: str) -> dict[str, object]:
    return {
        "mode": "unavailable",
        "sidecar_id": sidecar_id,
        "reason": f"{sidecar_id}_sidecar_not_packaged",
    }


def write_test_obligation_artifacts(*args: object, **kwargs: object) -> dict[str, object]:
    module = optional_phase3_diagnostic_module("test_obligation_matrix")
    if module is None:
        return diagnostic_sidecar_unavailable_summary("test_obligation_matrix")
    return module.write_test_obligation_artifacts(*args, **kwargs)


def write_test_richness_review_artifacts(*args: object, **kwargs: object) -> dict[str, object]:
    module = optional_phase3_diagnostic_module("test_richness_review")
    if module is None:
        return diagnostic_sidecar_unavailable_summary("test_richness_review")
    return module.write_test_richness_review_artifacts(*args, **kwargs)


def write_agentic_generation_quality_loop_artifacts(*args: object, **kwargs: object) -> dict[str, object]:
    module = optional_phase3_diagnostic_module("agentic_generation_quality_loop")
    if module is None:
        return {
            **diagnostic_sidecar_unavailable_summary("agentic_generation_quality_loop"),
            "selected_behavior_unit_count": 0,
            "generated_quality_obligation_test_path": "",
        }
    return module.write_agentic_generation_quality_loop_artifacts(*args, **kwargs)


def runtime_operation_specs_from_openapi(openapi_spec: dict[str, object]) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    paths = openapi_spec.get("paths", {})
    if not isinstance(paths, dict):
        return specs
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId", "")).strip()
            if not operation_id:
                continue
            tags = operation.get("tags", [])
            specs[operation_id] = {
                "operationId": operation_id,
                "method": str(method).upper(),
                "path": str(path),
                "tag": str(tags[0]).strip() if isinstance(tags, list) and tags else "default",
                "executionMode": operation.get("x-execution-mode")
                or operation.get("x_execution_mode")
                or operation.get("executionMode")
                or operation.get("execution_mode"),
                "requestRequiredFields": operation.get("x-request-required-fields")
                or operation.get("x_request_required_fields")
                or operation.get("requestRequiredFields")
                or [],
                "responseExample": operation.get("x-response-example")
                or operation.get("x_response_example")
                or operation.get("responseExample")
                or {},
                "failureCases": operation.get("x-failure-cases")
                or operation.get("x_failure_cases")
                or operation.get("failureCases")
                or [],
                "idempotencyRule": operation.get("x-idempotency-rule")
                or operation.get("x_idempotency_rule")
                or operation.get("idempotencyRule")
                or "",
                "purpose": operation.get("description") or operation.get("summary") or "",
            }
    return specs


def resolve_optional_path(value: str) -> Path | None:
    normalized = str(value).strip()
    if not normalized:
        return None
    return Path(normalized).resolve()


def load_service_authoring_packet(args: Any) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    packet_path = resolve_optional_path(getattr(args, "service_authoring_packet_path", ""))
    if packet_path is None:
        return None, {
            "mode": "disabled",
            "path": "",
            "operation_count": 0,
        }

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if not isinstance(packet, dict):
        raise ValueError("service authoring packet must be a JSON object")
    operations = packet.get("operations")
    return packet, {
        "mode": str(packet.get("mode", "")).strip(),
        "path": str(packet_path),
        "operation_count": len(operations) if isinstance(operations, dict) else 0,
    }


def is_strict_runtime_closure_mode(value: object) -> bool:
    return str(value or "").strip() == "strict-runtime"


def is_experimental_synthesis_boundary_enabled(args: Any) -> bool:
    return bool(getattr(args, "enable_experimental_synthesis_boundary", False))


def load_pre_generation_synthesis_bindings(
    *,
    implementation_bindings_path: Path,
    trace_registry: dict[str, Any],
    openapi_spec: dict[str, object] | None = None,
) -> dict[str, Any]:
    if implementation_bindings_path.exists():
        current = json.loads(implementation_bindings_path.read_text(encoding="utf-8"))
        if isinstance(current, dict) and current.get("rows"):
            return enrich_pre_generation_synthesis_bindings(current, openapi_spec=openapi_spec)
    rows = trace_registry.get("rows", [])
    return enrich_pre_generation_synthesis_bindings(
        {
            "artifact_kind": "phase3-pre-generation-source-bindings",
            "rows": rows if isinstance(rows, list) else [],
        },
        openapi_spec=openapi_spec,
    )


def _operation_targets(openapi_spec: dict[str, object] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(openapi_spec, dict):
        return {}
    targets: dict[str, dict[str, Any]] = {}
    for operation in parse_openapi_operations(openapi_spec):
        operation_id = str(operation.get("operation_id", "")).strip()
        if not operation_id:
            continue
        module_slug = slugify(str(operation.get("tag", "")).strip()) or slugify(operation_id) or "default"
        contract_target = f"tests/contracts/{contract_test_filename(operation_id, operation.get('method', ''), operation.get('path', ''))}"
        targets[operation_id.lower()] = {
            "operation_id": operation_id,
            "implementation_targets": [
                f"apps/api/src/modules/{module_slug}/{module_slug}.controller.ts",
                f"apps/api/src/modules/{module_slug}/{module_slug}.repository.ts",
                f"apps/api/src/modules/{module_slug}/{module_slug}.service.ts",
            ],
            "test_targets": [
                contract_target,
                backend_module_unit_test_path(module_slug),
            ],
            "runtime_evidence_refs": [
                contract_target,
                backend_module_unit_test_path(module_slug),
            ],
        }
    return targets


def _merge_string_lists(*values: object) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, list):
            continue
        for item in value:
            text = str(item).strip()
            if text and text not in seen:
                merged.append(text)
                seen.add(text)
    return merged


def enrich_pre_generation_synthesis_bindings(
    bindings: dict[str, Any],
    *,
    openapi_spec: dict[str, object] | None,
) -> dict[str, Any]:
    operation_targets = _operation_targets(openapi_spec)
    if not operation_targets:
        return bindings
    enriched = dict(bindings)
    rows = []
    for row in bindings.get("rows", []):
        if not isinstance(row, dict):
            continue
        next_row = dict(row)
        haystack = " ".join(
            [
                str(next_row.get("operation_id", "")),
                str(next_row.get("verification_hook", "")),
                " ".join(str(target) for target in next_row.get("test_targets", []) if str(target).strip()),
            ]
        ).lower()
        for key, target_info in operation_targets.items():
            if key not in haystack:
                continue
            next_row["operation_id"] = next_row.get("operation_id") or target_info["operation_id"]
            next_row["implementation_targets"] = _merge_string_lists(
                next_row.get("implementation_targets"),
                target_info["implementation_targets"],
            )
            next_row["test_targets"] = _merge_string_lists(next_row.get("test_targets"), target_info["test_targets"])
            next_row["runtime_evidence_refs"] = _merge_string_lists(
                next_row.get("runtime_evidence_refs"),
                target_info["runtime_evidence_refs"],
            )
            if not next_row.get("binding_status"):
                next_row["binding_status"] = "suggested"
            break
        rows.append(next_row)
    enriched["rows"] = rows
    return enriched


def resolve_phase3_foundation_paths(
    *,
    output_dir: Path,
    bootstrap: dict[str, object],
    enable_ui_fallback: bool,
) -> dict[str, Path]:
    ui_ia_contract_path = bootstrap["ui_ia_contract_path"]
    return {
        "ui_fallback_report_path": bootstrap["ui_fallback_report_path"],
        "ui_ia_contract_path": ui_ia_contract_path,
        "ui_contract_input_path": ui_ia_contract_path if enable_ui_fallback else output_dir / ".phase3-no-ui-contract.json",
        "stack_decision_path": output_dir / "tech-stack-decision.yaml",
        "openapi_path": bootstrap["openapi_path"],
        "migration_path": bootstrap["migration_path"],
        "shared_types_path": bootstrap["shared_types_path"],
        "api_client_path": bootstrap["api_client_path"],
        "schema_tests_dir": output_dir / "tests" / "schema",
        "sql_tests_dir": bootstrap["sql_tests_dir"],
        "contracts_dir": bootstrap["contracts_dir"],
        "scenarios_dir": bootstrap["scenarios_dir"],
        "replays_dir": bootstrap["replays_dir"],
        "trace_matrix_path": bootstrap["trace_matrix_path"],
        "implementation_bindings_path": bootstrap["implementation_bindings_path"],
        "trace_registry_path": output_dir / "phase-3-trace-registry.json",
        "quality_report_path": output_dir / "phase3-quality-check.json",
        "coverage_plan_path": output_dir / "test-coverage-plan.md",
        "test_richness_review_path": output_dir / "test-richness-review.json",
        "toolchain_bootstrap_path": output_dir / "phase3-toolchain-bootstrap.json",
        "bootstrap_worker_run_report_path": output_dir / "bootstrap-worker-run-report.json",
        "trace_registry_final_path": output_dir / "phase-3-trace-registry-final.json",
        "acceptance_report_path": output_dir / "phase-3-acceptance-report.md",
        "execution_report_path": output_dir / "phase-3-execution-report.md",
        "delivery_gate_path": output_dir / "phase3-delivery-gate.json",
        "run_metadata_path": output_dir / "phase3-run-metadata.json",
        "agentic_implementation_loop_path": output_dir / "agentic-implementation-loop.json",
        "agentic_implementation_loop_markdown_path": output_dir / "agentic-implementation-loop.md",
        "agentic_generation_quality_loop_path": output_dir / "agentic-generation-quality-loop.json",
        "agentic_generation_quality_loop_markdown_path": output_dir / "agentic-generation-quality-loop.md",
        "business_behavior_authoring_plan_path": output_dir
        / ".phase3-review"
        / "business-behavior-authoring-plan.json",
        "action_card_execution_map_path": output_dir / ".phase3-review" / "action-card-execution-map.json",
    }


def prepare_phase3_foundation_workspace(
    *,
    args: Any,
    phase2_root: Path,
    output_dir: Path,
    output_locale: str,
    ui_locale: str,
    esp_text: str,
    stage_03_text: str,
    stage_04_text: str,
    bootstrap: dict[str, object],
    paths: dict[str, Path],
    build_test_coverage_plan_fn: Callable[..., str],
    build_stack_decision_document_fn: Callable[..., str],
    generate_project_scaffold_fn: Callable[..., dict[str, Any]],
    bootstrap_phase3_toolchain_fn: Callable[..., dict[str, Any]],
    scaffold_schema_tests_fn: Callable[..., dict[str, Any]],
    initialize_phase3_trace_registry_fn: Callable[[dict[str, Any]], dict[str, Any]],
    scaffold_phase3_implementation_fn: Callable[..., dict[str, Any]],
    initialize_optional_dispatch_lane_fn: Callable[..., dict[str, Any]],
    analyze_phase3_bootstrap_fn: Callable[..., dict[str, Any]],
    finalize_trace_registry_fn: Callable[..., dict[str, Any]],
    timing_segments: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    timing_segments = timing_segments if timing_segments is not None else {}
    generation_started = start_timer()
    paths.setdefault(
        "business_behavior_authoring_plan_path",
        output_dir / ".phase3-review" / "business-behavior-authoring-plan.json",
    )
    paths.setdefault(
        "action_card_execution_map_path",
        output_dir / ".phase3-review" / "action-card-execution-map.json",
    )
    stack_decision_path = paths["stack_decision_path"]
    toolchain_bootstrap_path = paths["toolchain_bootstrap_path"]
    schema_tests_dir = paths["schema_tests_dir"]
    coverage_plan_path = paths["coverage_plan_path"]
    trace_registry_path = paths["trace_registry_path"]
    implementation_bindings_path = paths["implementation_bindings_path"]
    quality_report_path = paths["quality_report_path"]
    run_metadata_path = paths["run_metadata_path"]
    trace_registry_final_path = paths["trace_registry_final_path"]

    stack_decision_path.write_text(
        build_stack_decision_document_fn(
            esp_text=esp_text,
            stage_03_text=stage_03_text,
            stage_04_text=stage_04_text,
            title=args.title,
            output_locale=output_locale,
        ),
        encoding="utf-8",
    )

    spec = bootstrap["spec"]
    matrix = bootstrap["matrix"]
    ui_fallback_summary = bootstrap["ui_fallback_summary"]
    scaffold_summary = generate_project_scaffold_fn(
        output_dir=output_dir,
        project_name=args.title,
        ui_ia_contract_path=paths["ui_contract_input_path"],
        ui_locale=ui_locale,
    )

    schema_summary = scaffold_schema_tests_fn(esp_text, schema_tests_dir)
    sql_summary = bootstrap["sql_summary"]
    contract_summary = bootstrap["contract_summary"]
    scenario_summary = bootstrap["scenario_summary"]
    replay_summary = bootstrap["replay_summary"]
    coverage_plan_path.write_text(
        build_test_coverage_plan_fn(
            schema_count=schema_summary["count"],
            sql_count=sql_summary["count"],
            contract_count=contract_summary["count"],
            scenario_count=scenario_summary["count"],
            replay_count=replay_summary["count"],
            output_locale=output_locale,
        ),
        encoding="utf-8",
    )

    trace_registry = initialize_phase3_trace_registry_fn(matrix)
    trace_registry_path.write_text(
        json.dumps(trace_registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    synthesis_boundary_enabled = is_experimental_synthesis_boundary_enabled(args)
    phase3_synthesis_brief: dict[str, Any] | None = None
    phase3_synthesis_brief_summary: dict[str, Any] = {
        "mode": "experimental-disabled",
        "json_path": "",
        "markdown_path": "",
        "brief": None,
    }
    if synthesis_boundary_enabled:
        pre_generation_bindings = load_pre_generation_synthesis_bindings(
            implementation_bindings_path=implementation_bindings_path,
            trace_registry=trace_registry,
            openapi_spec=spec,
        )
        phase3_synthesis_brief_summary = write_phase3_synthesis_brief_artifacts(
            output_dir=output_dir,
            case_name=args.title,
            version=args.version,
            phase2_root=phase2_root,
            implementation_bindings=pre_generation_bindings,
            mainline_verification_mode=str(getattr(args, "mainline_verification_mode", "disabled")),
            output_locale=output_locale,
        )
        phase3_synthesis_brief = phase3_synthesis_brief_summary["brief"]
    service_authoring_packet, service_authoring_packet_summary = load_service_authoring_packet(args)
    module_synthesis_bundle_summary = {
        "mode": "retired-from-active-foundation-runtime",
        "path": "",
    }
    action_card_obligations = load_action_card_obligations(phase2_root)
    p2_project_language_handoff = build_project_language_handoff(
        component_catalog=action_card_obligations.get("component_catalog", {}),
        component_obligations=action_card_obligations.get("component_obligations", {}),
        domain_glossary=[],
        ui_surface_context={
            "applicable": bool(paths["ui_contract_input_path"].exists()),
            "reason": "frontend/UI surface declared"
            if paths["ui_contract_input_path"].exists()
            else "no frontend/UI surface declared",
        },
    )
    action_card_execution_context = build_action_card_execution_context(
        component_obligations=action_card_obligations.get("component_obligations", {}),
        component_catalog=action_card_obligations.get("component_catalog", {}),
    )
    action_card_execution_map = action_card_execution_context["pointer_manifest"]
    action_card_rich_context = action_card_execution_context["rich_context"]
    write_json(paths["action_card_execution_map_path"], action_card_execution_map)
    action_card_execution_map_summary = {
        "mode": "default-p3-mainline-pointer-manifest",
        "path": str(paths["action_card_execution_map_path"]),
        "operation_count": action_card_execution_map.get("summary", {}).get("operation_count", 0),
        "action_card_ref_count": action_card_execution_map.get("summary", {}).get("action_card_ref_count", 0),
        "rich_context_persisted": action_card_execution_map.get("summary", {}).get("rich_context_persisted", False),
        "component_count": action_card_rich_context.get("summary", {}).get("component_count", 0),
        "review_bound_operation_count": action_card_execution_map.get("summary", {}).get(
            "review_bound_operation_count",
            0,
        ),
    }
    project_implementation_conventions = synthesize_project_implementation_conventions(
        p2_language_handoff=p2_project_language_handoff,
        tech_stack_decision=parse_stack_decision_text(stack_decision_path.read_text(encoding="utf-8")),
        action_card_context=action_card_rich_context,
        frontend_surface_context=None,
    )
    project_implementation_convention_summary = {
        "mode": project_implementation_conventions.get("mode", ""),
        **(
            project_implementation_conventions.get("summary", {})
            if isinstance(project_implementation_conventions.get("summary"), dict)
            else {}
        ),
    }
    implementation_authority = load_json_object(
        output_dir / "p3-agentic-implementation-authority.json"
    )
    accepted_implementation_authority = p3_agentic_implementation_authority_is_valid(
        implementation_authority
    )
    agentic_semantic_decisions: dict[str, Any] | None = (
        dict(implementation_authority.get("agentic_semantic_decisions", {}))
        if accepted_implementation_authority
        and isinstance(implementation_authority.get("agentic_semantic_decisions"), dict)
        else None
    )
    business_behavior_authoring_plan_summary: dict[str, Any] = {
        "mode": "retired-from-active-foundation-runtime",
        "path": "",
        "persisted": False,
        "operation_count": 0,
        "fallback_operation_count": 0,
    }
    agentic_semantic_authoring_summary: dict[str, Any] = {
        "mode": (
            str(agentic_semantic_decisions.get("mode") or "")
            if isinstance(agentic_semantic_decisions, dict)
            else "disabled"
        ),
        "persisted": False,
        **(
            agentic_semantic_decisions.get("summary", {})
            if isinstance(agentic_semantic_decisions, dict)
            and isinstance(agentic_semantic_decisions.get("summary"), dict)
            else {
                "agentic_semantic_decision_count": 0,
                "default_heavy_artifact_count": 0,
            }
        ),
    }
    agentic_module_implementation_brief_summary: dict[str, Any] = {
        "mode": "retired-from-active-foundation-runtime",
        "persisted": False,
        "module_count": 0,
        "persisted_default_heavy_artifact_count": 0,
    }
    action_card_direct_implementation_driver_summary: dict[str, Any] = {
        "mode": "retired-from-active-foundation-runtime",
        "persisted": False,
        "operation_count": 0,
        "persisted_default_heavy_artifact_count": 0,
    }
    implementation_summary = scaffold_phase3_implementation_fn(
        esp_text=esp_text,
        openapi_spec=spec,
        phase3_trace_registry=trace_registry,
        output_dir=output_dir,
        ui_ia_contract_path=paths["ui_contract_input_path"],
        behavior_card_models=bootstrap.get("behavior_card_models", {}),
        synthesis_brief=phase3_synthesis_brief,
        service_authoring_packet=service_authoring_packet,
        module_synthesis_bundle_path=None,
        action_card_execution_map=action_card_rich_context,
        action_card_execution_map_path=paths["action_card_execution_map_path"],
        business_behavior_authoring_plan=None,
        business_behavior_authoring_plan_path=None,
        agentic_semantic_decisions=agentic_semantic_decisions,
        project_implementation_conventions=project_implementation_conventions,
        module_implementation_briefs=None,
        action_card_direct_implementation_driver=None,
        include_frontend=bool(
            getattr(args, "enable_ui_fallback", False)
            or getattr(args, "require_frontend_contract", False)
        ),
    )
    test_obligation_summary = write_test_obligation_artifacts(
        output_dir=output_dir,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        openapi_spec=spec,
        behavior_card_models=bootstrap.get("behavior_card_models", {}),
    )
    test_richness_review_summary = write_test_richness_review_artifacts(
        output_dir=output_dir,
        test_obligation_audit_path=output_dir / "test-obligation-audit.json",
    )
    implementation_bindings = json.loads(implementation_bindings_path.read_text(encoding="utf-8"))
    test_richness_review = {}
    if paths["test_richness_review_path"].exists():
        test_richness_review = json.loads(paths["test_richness_review_path"].read_text(encoding="utf-8"))
    strict_runtime_closure = is_strict_runtime_closure_mode(getattr(args, "mainline_verification_mode", "disabled"))
    full_targeted_evidence = bool(getattr(args, "full_targeted_evidence", True))
    validation_level = normalize_validation_level(
        getattr(args, "validation_level", ""),
        full_targeted_evidence=full_targeted_evidence,
    )
    validation_profile = build_validation_profile(
        validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )
    agentic_implementation_loop_summary = write_agentic_implementation_loop_artifacts(
        output_dir=output_dir,
        case_name=args.title,
        version=args.version,
        implementation_bindings=implementation_bindings,
        test_richness_review=test_richness_review,
        mainline_verification_mode=str(getattr(args, "mainline_verification_mode", "disabled")),
        dispatch_lane_enabled=bool(args.enable_dispatch_lane),
        output_locale=output_locale,
    )
    agentic_generation_quality_loop_summary = write_agentic_generation_quality_loop_artifacts(
        output_dir=output_dir,
        case_name=args.title,
        version=args.version,
        implementation_bindings=implementation_bindings,
        output_locale=output_locale,
    )
    record_timing_segment(timing_segments, "generation", generation_started)
    toolchain_started = start_timer()
    toolchain_bootstrap_report = bootstrap_phase3_toolchain_fn(
        workspace_root=output_dir,
        install=bool(getattr(args, "install_toolchain", False) or strict_runtime_closure),
        strict=strict_runtime_closure,
        output_path=toolchain_bootstrap_path,
    )
    record_timing_segment(timing_segments, "toolchain_install", toolchain_started)
    dispatch_lane_started = start_timer()
    dispatch_lane_state = initialize_optional_dispatch_lane_fn(
        enabled=args.enable_dispatch_lane,
        dispatch_lane_mode=str(getattr(args, "dispatch_lane_mode", "enabled" if args.enable_dispatch_lane else "disabled")),
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        spec=spec,
        implementation_bindings=implementation_bindings,
        output_dir=output_dir,
        toolchain_bootstrap_path=toolchain_bootstrap_path,
    )
    record_timing_segment(
        timing_segments,
        "dispatch_lane",
        dispatch_lane_started,
        status="recorded" if args.enable_dispatch_lane else "skipped",
    )
    worker_run_report_path = dispatch_lane_state["worker_run_report_path"]
    bootstrap_worker_run_report_path = dispatch_lane_state["bootstrap_worker_run_report_path"]
    subagent_execution_summary = (
        dispatch_lane_state.get("subagent_execution_summary", {})
        if isinstance(dispatch_lane_state.get("subagent_execution_summary", {}), dict)
        else {}
    )
    subagent_slice_summary = (
        dispatch_lane_state.get("subagent_slice_summary", {})
        if isinstance(dispatch_lane_state.get("subagent_slice_summary", {}), dict)
        else {}
    )

    quality = analyze_phase3_bootstrap_fn(
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        openapi_path=paths["openapi_path"],
        migration_path=paths["migration_path"],
        shared_types_path=paths["shared_types_path"],
        api_client_path=paths["api_client_path"],
        contracts_dir=paths["contracts_dir"],
        scenarios_dir=paths["scenarios_dir"],
        replays_dir=paths["replays_dir"],
        test_trace_matrix_path=paths["trace_matrix_path"],
        stack_decision_path=stack_decision_path,
        schema_tests_dir=schema_tests_dir,
        trace_registry_path=trace_registry_path,
        implementation_bindings_path=implementation_bindings_path,
        work_package_packets_dir=(output_dir / "work-package-packets") if args.enable_dispatch_lane else None,
        work_package_wave_plan_path=(output_dir / "work-package-wave-plan.json") if args.enable_dispatch_lane else None,
        execution_loop_plan_path=(output_dir / "execution-loop-plan.json") if args.enable_dispatch_lane else None,
        worker_input_packets_dir=(output_dir / "worker-input-packets") if args.enable_dispatch_lane else None,
        execution_runtime_state_path=(output_dir / "execution-runtime-state.json") if args.enable_dispatch_lane else None,
        dispatch_manifest_path=(output_dir / "dispatch-manifest.json") if args.enable_dispatch_lane else None,
        worker_run_report_path=worker_run_report_path if args.enable_dispatch_lane else None,
        runtime_cycle_summary_path=(output_dir / "runtime-cycle-summary.json") if args.enable_dispatch_lane else None,
        runtime_environment_ledger_path=dispatch_lane_state["runtime_environment_ledger_path"] if args.enable_dispatch_lane else None,
        coverage_plan_path=coverage_plan_path,
        ci_workflow_path=output_dir / ".github" / "workflows" / "ci.yml",
        docker_compose_dev_path=output_dir / "docker-compose.dev.yml",
        docker_compose_prod_path=output_dir / "docker-compose.prod.yml",
        dockerfile_path=output_dir / "Dockerfile",
        env_example_path=output_dir / ".env.example",
        runtime_entrypoint_path=output_dir / "apps" / "api" / "src" / "main.ts",
        root_package_json_path=output_dir / "package.json",
        api_package_json_path=output_dir / "apps" / "api" / "package.json",
        toolchain_bootstrap_report_path=toolchain_bootstrap_path,
        test_obligation_audit_path=(
            (output_dir / "test-obligation-audit.json")
            if (output_dir / "test-obligation-audit.json").exists()
            else None
        ),
        test_richness_review_path=(
            paths["test_richness_review_path"] if paths["test_richness_review_path"].exists() else None
        ),
        require_frontend_contract=args.require_frontend_contract,
    )
    write_json(quality_report_path, quality)
    write_json(
        run_metadata_path,
        {
            "case_name": args.title,
            "version": args.version,
            "phase2_root": str(phase2_root),
            "artifact_kind": "fresh-phase3-foundation-run",
            "generation_entrypoint": getattr(args, "generation_entrypoint", "scripts/phase3/run_phase3_first_version.py"),
            "generation_purity": "fresh-from-phase2-root",
            "mainline_profile": "backend-first",
            "frontend_contract_required": args.require_frontend_contract,
            "ui_lane_enabled": args.enable_ui_fallback,
            "ui_lane_mode": str(ui_fallback_summary.get("mode", "not-requested")),
            "dispatch_lane_enabled": args.enable_dispatch_lane,
            "dispatch_lane_mode": str(getattr(args, "dispatch_lane_mode", "enabled" if args.enable_dispatch_lane else "disabled")),
            "has_execution_loop_plan": args.enable_dispatch_lane,
            "subagent_execution_request": str(subagent_execution_summary.get("request", "")),
            "subagent_execution_mode": str(subagent_execution_summary.get("mode", "")),
            "subagent_execution_status": str(subagent_execution_summary.get("status", "")),
            "subagent_runner_supported": bool(subagent_execution_summary.get("runner_supported", False)),
            "subagent_execution_claim_ceiling": str(subagent_execution_summary.get("claim_ceiling", "")),
            "subagent_slice_count": int(subagent_slice_summary.get("slice_count", 0) or 0),
            "subagent_blocked_slice_count": int(subagent_slice_summary.get("blocked_slice_count", 0) or 0),
            "subagent_overall_slice_run_status": str(
                subagent_slice_summary.get("overall_slice_run_status", "not-applicable") or "not-applicable"
            ),
            "subagent_actual_execution_count": int(
                subagent_slice_summary.get("actual_subagent_execution_count", 0) or 0
            ),
            "subagent_write_runner_execution_count": int(
                subagent_slice_summary.get("write_runner_execution_count", 0) or 0
            ),
            "subagent_read_only_review_count": int(subagent_slice_summary.get("read_only_review_count", 0) or 0),
            "action_card_runner_supported": bool(
                subagent_slice_summary.get("action_card_runner_supported", False)
            ),
            "action_card_runner_protocol_version": str(
                subagent_slice_summary.get("runner_protocol_version", "action-card-runner/v1")
            ),
            "action_card_runner_kind": str(subagent_slice_summary.get("runner_kind", "generic")),
            "subagent_configured_authoring_max_workers": int(
                subagent_slice_summary.get("configured_authoring_max_workers", 0) or 0
            ),
            "subagent_active_authoring_max_workers": int(
                subagent_slice_summary.get("active_authoring_max_workers", 0) or 0
            ),
            "subagent_configured_verification_max_workers": int(
                subagent_slice_summary.get("configured_verification_max_workers", 0) or 0
            ),
            "has_agentic_implementation_loop": True,
            "agentic_implementation_loop": str(paths["agentic_implementation_loop_path"]),
            "agentic_implementation_loop_markdown": str(paths["agentic_implementation_loop_markdown_path"]),
            "agentic_implementation_loop_summary": agentic_implementation_loop_summary,
            "has_agentic_generation_quality_loop": paths["agentic_generation_quality_loop_path"].exists(),
            "agentic_generation_quality_loop": (
                str(paths["agentic_generation_quality_loop_path"])
                if paths["agentic_generation_quality_loop_path"].exists()
                else ""
            ),
            "agentic_generation_quality_loop_markdown": (
                str(paths["agentic_generation_quality_loop_markdown_path"])
                if paths["agentic_generation_quality_loop_markdown_path"].exists()
                else ""
            ),
            "agentic_generation_quality_loop_summary": agentic_generation_quality_loop_summary,
            "has_phase3_synthesis_brief": synthesis_boundary_enabled,
            "phase3_synthesis_brief": str(phase3_synthesis_brief_summary["json_path"]) if synthesis_boundary_enabled else "",
            "phase3_synthesis_brief_markdown": str(phase3_synthesis_brief_summary["markdown_path"]) if synthesis_boundary_enabled else "",
            "phase3_synthesis_brief_summary": phase3_synthesis_brief.get("summary", {}) if phase3_synthesis_brief else {"mode": "experimental-disabled"},
            "has_service_authoring_packet": service_authoring_packet is not None,
            "service_authoring_packet_summary": service_authoring_packet_summary,
            "has_module_synthesis_bundle": False,
            "module_synthesis_bundle_summary": module_synthesis_bundle_summary,
            "has_business_behavior_authoring_plan": False,
            "business_behavior_authoring_plan": "",
            "business_behavior_authoring_plan_summary": business_behavior_authoring_plan_summary,
            "has_action_card_authoring_projection": True,
            "action_card_authoring_projection_persisted": False,
            "has_action_card_execution_map": True,
            "action_card_execution_map": str(paths["action_card_execution_map_path"]),
            "action_card_execution_map_summary": action_card_execution_map_summary,
            "has_agentic_semantic_authoring": accepted_implementation_authority,
            "agentic_semantic_authoring_candidate_present": False,
            "agentic_semantic_authoring_candidate_authority": (
                "accepted-host-agent-implementation-authority"
                if accepted_implementation_authority
                else "none"
            ),
            "agentic_implementation_decision_id": str(
                implementation_authority.get("decision_id") or ""
            ),
            "agentic_implementation_decision_digest": str(
                implementation_authority.get("decision_digest") or ""
            ),
            "agentic_semantic_authoring_summary": agentic_semantic_authoring_summary,
            "has_project_implementation_conventions": True,
            "project_implementation_convention_summary": project_implementation_convention_summary,
            "has_agentic_module_implementation_brief": False,
            "agentic_module_implementation_brief_summary": agentic_module_implementation_brief_summary,
            "has_action_card_direct_implementation_driver": False,
            "action_card_direct_implementation_driver_default": False,
            "action_card_direct_implementation_driver": "",
            "action_card_direct_implementation_driver_persisted": False,
            "action_card_direct_implementation_driver_summary": action_card_direct_implementation_driver_summary,
            "mainline_verification_mode": str(getattr(args, "mainline_verification_mode", "disabled")),
            "validation_level": validation_level,
            "validation_profile": validation_profile,
            "full_targeted_evidence": full_targeted_evidence,
            "toolchain_install_requested": bool(getattr(args, "install_toolchain", False) or strict_runtime_closure),
            "runtime_closure_mode": "strict-runtime" if strict_runtime_closure else "default",
            "runtime_smoke_requested": bool(getattr(args, "run_runtime_smoke", False)),
            "ui_prototype_fallback_report": str(paths["ui_fallback_report_path"]) if args.enable_ui_fallback else "",
            "bootstrap_worker_run_report": str(bootstrap_worker_run_report_path) if args.enable_dispatch_lane else "",
            "behavior_card_summary": bootstrap.get("behavior_card_summary", {"count": 0}),
        },
    )

    trace_identity_source_summary = carry_phase2_trace_identity_source(
        phase2_root=phase2_root,
        output_dir=output_dir,
    )
    trace_registry_final = finalize_trace_registry_fn(
        test_trace_matrix=matrix,
        implementation_bindings=implementation_bindings,
    )
    trace_registry_final = {
        **trace_registry_final,
        "trace_db_present": bool(trace_identity_source_summary.get("trace_db_present")),
        "trace_identity_source": trace_identity_source_summary,
    }
    trace_registry_final["trace_db_projection"] = project_phase3_trace_registry_to_trace_db(
        trace_db_path=output_dir / ".trace" / "trace.db",
        trace_registry_final=trace_registry_final,
        source_path=trace_registry_final_path,
    )
    write_json(trace_registry_final_path, trace_registry_final)
    semantic_realization_ledger = write_semantic_realization_ledger(
        phase2_root=phase2_root,
        output_dir=output_dir,
        implementation_bindings=implementation_bindings,
        trace_registry_final=trace_registry_final,
    )

    return {
        "ui_fallback_summary": ui_fallback_summary,
        "scaffold_summary": scaffold_summary,
        "schema_summary": schema_summary,
        "sql_summary": sql_summary,
        "contract_summary": contract_summary,
        "behavior_card_summary": bootstrap.get("behavior_card_summary", {"count": 0}),
        "scenario_summary": scenario_summary,
        "replay_summary": replay_summary,
        "implementation_summary": implementation_summary,
        "test_obligation_summary": test_obligation_summary,
        "test_richness_review_summary": test_richness_review_summary,
        "phase3_synthesis_brief": phase3_synthesis_brief,
        "phase3_synthesis_brief_summary": phase3_synthesis_brief_summary,
        "service_authoring_packet_summary": service_authoring_packet_summary,
        "module_synthesis_bundle_summary": module_synthesis_bundle_summary,
        "action_card_execution_map": action_card_execution_map,
        "action_card_rich_context": action_card_rich_context,
        "action_card_execution_map_summary": action_card_execution_map_summary,
        "business_behavior_authoring_plan": None,
        "business_behavior_authoring_plan_summary": business_behavior_authoring_plan_summary,
        "p2_project_language_handoff": p2_project_language_handoff,
        "project_implementation_conventions": project_implementation_conventions,
        "project_implementation_convention_summary": project_implementation_convention_summary,
        "agentic_semantic_decisions": agentic_semantic_decisions,
        "agentic_semantic_authoring_summary": agentic_semantic_authoring_summary,
        "agentic_module_implementation_briefs": None,
        "agentic_module_implementation_brief_summary": agentic_module_implementation_brief_summary,
        "action_card_direct_implementation_driver": None,
        "action_card_direct_implementation_driver_summary": action_card_direct_implementation_driver_summary,
        "agentic_implementation_loop_summary": agentic_implementation_loop_summary,
        "agentic_generation_quality_loop_summary": agentic_generation_quality_loop_summary,
        "implementation_bindings": implementation_bindings,
        "dispatch_lane_state": dispatch_lane_state,
        "quality": quality,
        "toolchain_bootstrap_report": toolchain_bootstrap_report,
        "trace_registry_final": trace_registry_final,
        "semantic_realization_ledger": semantic_realization_ledger,
        "trace_identity_source_summary": trace_identity_source_summary,
        "bootstrap_worker_run_report_path": bootstrap_worker_run_report_path,
    }


def finalize_phase3_foundation_delivery(
    *,
    args: Any,
    output_dir: Path,
    output_locale: str,
    paths: dict[str, Path],
    workspace: dict[str, Any],
    generate_phase3_delivery_handoff_fn: Callable[..., dict[str, Any]],
    finalize_phase3_delivery_closure_fn: Callable[..., tuple[dict[str, Any], dict[str, str], dict[str, Any]]],
    refresh_phase3_post_execution_fn: Callable[..., dict[str, Any]],
    execute_phase3_mainline_backend_verification_fn: Callable[..., dict[str, Any]],
    timing_segments: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, object], dict[str, Any]]:
    del finalize_phase3_delivery_closure_fn

    mode = str(getattr(args, "mainline_verification_mode", "disabled")).strip() or "disabled"
    strict_runtime_closure = is_strict_runtime_closure_mode(mode)
    full_targeted_evidence = bool(getattr(args, "full_targeted_evidence", True))
    validation_level = normalize_validation_level(
        getattr(args, "validation_level", ""),
        full_targeted_evidence=full_targeted_evidence,
    )
    validation_profile = build_validation_profile(
        validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )
    toolchain_status = str(workspace["toolchain_bootstrap_report"].get("overall_status", "unknown")).strip() or "unknown"
    if mode == "disabled":
        if timing_segments is not None:
            set_timing_segment(
                timing_segments,
                "mainline_backend_verification",
                duration_seconds=0.0,
                status="not-requested",
            )
        mainline_backend_verification = {
            "mode": mode,
            "attempted": False,
            "status": "not-requested",
            "reason": "mainline verification disabled",
            "toolchain_status": toolchain_status,
            "validation_level": validation_level,
            "validation_profile": validation_profile,
            "full_targeted_evidence": full_targeted_evidence,
        }
    elif toolchain_status != "ready":
        if timing_segments is not None:
            set_timing_segment(
                timing_segments,
                "mainline_backend_verification",
                duration_seconds=0.0,
                status="blocked" if strict_runtime_closure else "skipped",
            )
        mainline_backend_verification = {
            "mode": mode,
            "attempted": False,
            "status": "blocked" if strict_runtime_closure else "skipped",
            "reason": (
                f"strict_runtime_toolchain_not_ready:{toolchain_status}"
                if strict_runtime_closure
                else f"toolchain_not_ready:{toolchain_status}"
            ),
            "toolchain_status": toolchain_status,
            "validation_level": validation_level,
            "validation_profile": validation_profile,
            "full_targeted_evidence": full_targeted_evidence,
        }
    else:
        verification_started = start_timer()
        verification_result = execute_phase3_mainline_backend_verification_fn(
            output_dir=output_dir,
            implementation_bindings_path=paths["implementation_bindings_path"],
            actor=getattr(args, "runner_actor", "run_phase3_first_version"),
            note="internal backend verification for backend-first mainline",
            validation_level=validation_level,
            full_targeted_evidence=full_targeted_evidence,
        )
        if verification_result.get("sidecar_unavailable"):
            sidecar_status = "blocked" if strict_runtime_closure else "skipped"
            if timing_segments is not None:
                set_timing_segment(
                    timing_segments,
                    "mainline_backend_verification",
                    duration_seconds=0.0,
                    status=sidecar_status,
                )
            mainline_backend_verification = {
                "mode": mode,
                "attempted": False,
                "status": sidecar_status,
                "toolchain_status": toolchain_status,
                **verification_result,
                "status": sidecar_status,
                "reason": str(verification_result.get("reason") or "mainline_backend_verification_sidecar_not_packaged"),
                "validation_level": validation_level,
                "validation_profile": validation_profile,
                "full_targeted_evidence": full_targeted_evidence,
            }
        else:
            mainline_backend_verification = {
                "mode": mode,
                "status": "executed",
                "toolchain_status": toolchain_status,
                **verification_result,
                "validation_level": validation_level,
                "validation_profile": validation_profile,
                "full_targeted_evidence": full_targeted_evidence,
            }
            if timing_segments is not None:
                record_timing_segment(timing_segments, "mainline_backend_verification", verification_started)

    mainline_status = str(mainline_backend_verification.get("status", "")).strip()
    mainline_verdict = str(mainline_backend_verification.get("overall_verdict", "")).strip().lower()
    mainline_verification_failed = mainline_status == "executed" and mainline_verdict in {"fail", "failed", "blocked"}
    mainline_verification_green = mainline_status == "executed" and mainline_verdict in {"", "pass", "passed"}
    auto_run_runtime_smoke = (
        validation_level == "strict"
        and full_targeted_evidence
        and bool(mainline_backend_verification.get("attempted"))
        and mainline_verification_green
    )
    run_runtime_smoke = bool(getattr(args, "run_runtime_smoke", False)) or auto_run_runtime_smoke
    skip_coverage_collection = strict_runtime_closure and mainline_verification_failed
    refresh_summary = refresh_phase3_post_execution_fn(
        output_dir,
        strict_runtime_closure=strict_runtime_closure,
        run_runtime_smoke=run_runtime_smoke,
        skip_coverage_collection=skip_coverage_collection,
        coverage_collection_skip_reason=(
            "mainline_backend_verification_failed" if skip_coverage_collection else ""
        ),
        toolchain_bootstrap_report_path=paths["toolchain_bootstrap_path"],
        unit_test_report_path=resolve_optional_path(mainline_backend_verification.get("unit_test_report_path", "")),
        wp_gate_report_path=resolve_optional_path(mainline_backend_verification.get("wp_gate_report_path", "")),
        verification_ledger_report_path=resolve_optional_path(
            mainline_backend_verification.get("verification_ledger_path", "")
        ),
        runtime_smoke_report_path=resolve_optional_path(
            mainline_backend_verification.get("runtime_smoke_report_path", "")
        ),
    )
    if timing_segments is not None:
        refresh_timing_segments = refresh_summary.get("timing_segments", {})
        if isinstance(refresh_timing_segments, dict):
            for name, payload in refresh_timing_segments.items():
                if isinstance(payload, dict):
                    timing_segments[name] = dict(payload)
    delivery_handoff_summary = generate_phase3_delivery_handoff_fn(
        output_dir=output_dir,
        case_name=args.title,
        version=args.version,
        tech_stack_text=paths["stack_decision_path"].read_text(encoding="utf-8"),
        output_locale=output_locale,
    )
    return refresh_summary, delivery_handoff_summary, mainline_backend_verification


def build_phase3_foundation_summary(
    *,
    args: Any,
    output_dir: Path,
    paths: dict[str, Path],
    workspace: dict[str, Any],
    refresh_summary: dict[str, Any],
    delivery_handoff_summary: dict[str, object],
    mainline_backend_verification: dict[str, Any],
) -> dict[str, object]:
    dispatch_lane_state = workspace["dispatch_lane_state"]
    subagent_execution_summary = (
        dispatch_lane_state.get("subagent_execution_summary", {})
        if isinstance(dispatch_lane_state.get("subagent_execution_summary", {}), dict)
        else {}
    )
    subagent_slice_summary = (
        dispatch_lane_state.get("subagent_slice_summary", {})
        if isinstance(dispatch_lane_state.get("subagent_slice_summary", {}), dict)
        else {}
    )
    scaffold_quality_gate = str(workspace["quality"].get("overall_quality_gate", "")).strip() or "unknown"
    phase_verdict = str(refresh_summary.get("phase_verdict", "")).strip()
    final_quality_gate = "pass" if scaffold_quality_gate == "pass" and phase_verdict.startswith("PASS") else "fail"
    return {
        "output_dir": str(output_dir),
        "quality_gate": final_quality_gate,
        "scaffold_quality_gate": scaffold_quality_gate,
        "recommended_formal_state": refresh_summary.get("recommended_formal_state", ""),
        "stack_decision": str(paths["stack_decision_path"]),
        "schema_summary": workspace["schema_summary"],
        "contract_summary": workspace["contract_summary"],
        "behavior_card_summary": workspace.get("behavior_card_summary", {"count": 0}),
        "scenario_summary": workspace["scenario_summary"],
        "replay_summary": workspace["replay_summary"],
        "scaffold_summary": workspace["scaffold_summary"],
        "mainline_profile": "backend-first",
        "frontend_contract_required": args.require_frontend_contract,
        "ui_lane_enabled": args.enable_ui_fallback,
        "dispatch_lane_enabled": args.enable_dispatch_lane,
        "dispatch_lane_mode": str(getattr(args, "dispatch_lane_mode", "enabled" if args.enable_dispatch_lane else "disabled")),
        "subagent_execution_summary": subagent_execution_summary,
        "subagent_slice_summary": subagent_slice_summary,
        "validation_level": normalize_validation_level(
            getattr(args, "validation_level", ""),
            full_targeted_evidence=bool(getattr(args, "full_targeted_evidence", True)),
        ),
        "full_targeted_evidence": bool(getattr(args, "full_targeted_evidence", True)),
        "ui_prototype_fallback_summary": workspace["ui_fallback_summary"],
        "implementation_summary": workspace["implementation_summary"],
        "work_package_packet_summary": dispatch_lane_state["wp_packet_summary"],
        "work_package_wave_summary": dispatch_lane_state["wp_wave_summary"],
        "execution_loop_summary": dispatch_lane_state["execution_loop_summary"],
        "execution_dispatch_summary": dispatch_lane_state["execution_dispatch_summary"],
        "worker_run_report_summary": dispatch_lane_state["worker_run_report_summary"],
        "bootstrap_worker_run_report_summary": dispatch_lane_state["bootstrap_worker_run_report_summary"],
        "worker_packet_run_summary": dispatch_lane_state["worker_packet_run_summary"],
        "runtime_cycle_summary": dispatch_lane_state["runtime_cycle_summary"],
        "runtime_environment_ledger_summary": dispatch_lane_state["runtime_environment_ledger_summary"],
        "agentic_implementation_loop_summary": workspace["agentic_implementation_loop_summary"],
        "agentic_generation_quality_loop_summary": workspace["agentic_generation_quality_loop_summary"],
        "service_authoring_packet_summary": workspace["service_authoring_packet_summary"],
        "module_synthesis_bundle_summary": workspace["module_synthesis_bundle_summary"],
        "mainline_backend_verification": mainline_backend_verification,
        "delivery_handoff_summary": delivery_handoff_summary,
        "quality_report": str(paths["quality_report_path"]),
        "toolchain_bootstrap_report": str(paths["toolchain_bootstrap_path"]),
        "bootstrap_worker_run_report": (
            str(workspace["bootstrap_worker_run_report_path"]) if args.enable_dispatch_lane else ""
        ),
        "ui_prototype_fallback_report": str(paths["ui_fallback_report_path"]) if args.enable_ui_fallback else "",
        "delivery_gate_report": refresh_summary.get("delivery_gate_path", str(paths["delivery_gate_path"])),
        "mainline_assessment_artifacts": refresh_summary.get("mainline_assessment_paths", {}),
        "mainline_assessment_summary": refresh_summary.get("mainline_assessment_summary", {}),
        "phase_verdict_path": refresh_summary.get("phase_verdict_path", ""),
        "phase_verdict": phase_verdict,
        "phase_total_score": refresh_summary.get("phase_total_score"),
        "run_metadata": str(paths["run_metadata_path"]),
    }


def run_phase3_foundation_mainline_impl(
    *,
    args: Any,
    phase2_root: Path,
    output_dir: Path,
    output_locale: str,
    ui_locale: str,
    esp_text: str,
    stage_03_text: str,
    stage_04_text: str,
    bootstrap: dict[str, object],
    build_test_coverage_plan_fn: Callable[..., str],
    build_stack_decision_document_fn: Callable[..., str],
    generate_project_scaffold_fn: Callable[..., dict[str, Any]],
    bootstrap_phase3_toolchain_fn: Callable[..., dict[str, Any]],
    scaffold_schema_tests_fn: Callable[..., dict[str, Any]],
    initialize_phase3_trace_registry_fn: Callable[[dict[str, Any]], dict[str, Any]],
    scaffold_phase3_implementation_fn: Callable[..., dict[str, Any]],
    initialize_optional_dispatch_lane_fn: Callable[..., dict[str, Any]],
    analyze_phase3_bootstrap_fn: Callable[..., dict[str, Any]],
    finalize_trace_registry_fn: Callable[..., dict[str, Any]],
    generate_phase3_delivery_handoff_fn: Callable[..., dict[str, Any]],
    finalize_phase3_delivery_closure_fn: Callable[..., tuple[dict[str, Any], dict[str, str], dict[str, Any]]],
    refresh_phase3_post_execution_fn: Callable[..., dict[str, Any]],
    execute_phase3_mainline_backend_verification_fn: Callable[..., dict[str, Any]],
) -> dict[str, object]:
    paths = resolve_phase3_foundation_paths(
        output_dir=output_dir,
        bootstrap=bootstrap,
        enable_ui_fallback=args.enable_ui_fallback,
    )
    timing_segments: dict[str, dict[str, Any]] = {}
    workspace = prepare_phase3_foundation_workspace(
        args=args,
        phase2_root=phase2_root,
        output_dir=output_dir,
        output_locale=output_locale,
        ui_locale=ui_locale,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        bootstrap=bootstrap,
        paths=paths,
        build_test_coverage_plan_fn=build_test_coverage_plan_fn,
        build_stack_decision_document_fn=build_stack_decision_document_fn,
        generate_project_scaffold_fn=generate_project_scaffold_fn,
        bootstrap_phase3_toolchain_fn=bootstrap_phase3_toolchain_fn,
        scaffold_schema_tests_fn=scaffold_schema_tests_fn,
        initialize_phase3_trace_registry_fn=initialize_phase3_trace_registry_fn,
        scaffold_phase3_implementation_fn=scaffold_phase3_implementation_fn,
        initialize_optional_dispatch_lane_fn=initialize_optional_dispatch_lane_fn,
        analyze_phase3_bootstrap_fn=analyze_phase3_bootstrap_fn,
        finalize_trace_registry_fn=finalize_trace_registry_fn,
        timing_segments=timing_segments,
    )
    refresh_summary, delivery_handoff_summary, mainline_backend_verification = finalize_phase3_foundation_delivery(
        args=args,
        output_dir=output_dir,
        output_locale=output_locale,
        paths=paths,
        workspace=workspace,
        generate_phase3_delivery_handoff_fn=generate_phase3_delivery_handoff_fn,
        finalize_phase3_delivery_closure_fn=finalize_phase3_delivery_closure_fn,
        refresh_phase3_post_execution_fn=refresh_phase3_post_execution_fn,
        execute_phase3_mainline_backend_verification_fn=execute_phase3_mainline_backend_verification_fn,
        timing_segments=timing_segments,
    )
    implementation_authority = load_json_object(
        output_dir / "p3-agentic-implementation-authority.json"
    )
    implementation_application = (
        finalize_p3_agentic_implementation_application(
            output_dir=output_dir,
            authority=implementation_authority,
        )
        if p3_agentic_implementation_authority_is_valid(implementation_authority)
        else {}
    )
    summary = build_phase3_foundation_summary(
        args=args,
        output_dir=output_dir,
        paths=paths,
        workspace=workspace,
        refresh_summary=refresh_summary,
        delivery_handoff_summary=delivery_handoff_summary,
        mainline_backend_verification=mainline_backend_verification,
    )
    timing_report_path = write_phase3_timing_report(output_dir=output_dir, segments=timing_segments)
    summary["timing_report"] = str(timing_report_path)
    summary["agentic_implementation_authority"] = str(
        output_dir / "p3-agentic-implementation-authority.json"
    )
    summary["agentic_implementation_application"] = implementation_application
    return summary
