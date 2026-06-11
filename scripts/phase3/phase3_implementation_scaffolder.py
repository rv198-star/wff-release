#!/usr/bin/env python3
"""
Generate the initial implementation bindings and executable source scaffolds for Phase-3.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import importlib
import json
from pathlib import Path
from typing import Any

from phase3.contract_test_scaffolder import build_contract_test_target_lookup, contract_test_filename
from phase3.api_support_renderer import (
    extract_ui_policy_roles,
    normalize_ui_role_name,
    ordered_ui_roles,
    render_auth_session_module,
    render_envelope_module,
    render_errors_module,
    render_generated_api_router,
    render_generated_runtime_facade,
    render_generated_runtime_positioning,
    render_pagination_module,
    render_runtime_adapter_module,
    render_runtime_test_kit,
    split_ui_role_candidates,
)
from phase3.backend_module_renderer import (
    camel_case,
    lower_camel,
    operation_primary_record_hint,
    render_backend_foundation_unit_test,
    render_backend_module_unit_test,
    render_controller_module,
    render_repository_module,
    render_service_module,
    snake_case,
    stable_slug,
    synthesis_units_for_module,
)
from phase3.backend_runtime_harness_renderer import render_backend_runtime_harness
from phase3.generated_runtime_renderer import (
    build_runtime_operation_specs,
    infer_default_tenant,
    render_generated_runtime,
)
from phase3.contract_tools import (
    extract_nested_bullet_items,
    load_openapi_document,
)
from phase3.implementation_binding_tools import (
    append_generated_sql_test_bindings,
    append_generated_unit_test_bindings,
    backend_foundation_unit_test_paths,
    backend_module_unit_test_path,
    expand_scope_term_equivalents,
    build_wp_lookup,
    foundation_implementation_targets_for_test_targets,
    frontend_surface_unit_test_path,
    infer_work_packages_from_replay_overlap,
    infer_work_packages_from_targets,
    parse_openapi_operations,
    propagate_shared_test_bindings,
    rebind_cross_operation_test_rows,
    suggest_work_packages,
    trace_ids_in_text,
    scope_tokens,
    unit_test_targets_for_implementation_targets,
)
from phase3.surface_policy import write_phase3_diagnostic_surface


def _module_synthesis_tools():
    return importlib.import_module("phase3.module_synthesis")


def _frontend_scaffold_renderer():
    return importlib.import_module("phase3.frontend_scaffold_renderer")


def sanitize_route_segment(route_value: str, fallback_surface: str) -> str:
    candidates = [part for part in str(route_value).split("/") if part.strip()]
    normalized = [stable_slug(part, fallback="surface") for part in candidates]
    if normalized:
        return "/".join(normalized)
    return stable_slug(fallback_surface, fallback="surface")


def route_slug(surface: str) -> str:
    return stable_slug(surface, fallback="surface")


def infer_targets_from_scope(
    *,
    scope: str,
    acceptance_criteria: str,
    operations_by_tag: dict[str, list[dict[str, str]]],
    ui_pages: list[dict[str, Any]],
    output_dir: Path,
) -> list[str]:
    if ui_pages:
        return _frontend_scaffold_renderer().infer_targets_from_scope(
            scope=scope,
            acceptance_criteria=acceptance_criteria,
            operations_by_tag=operations_by_tag,
            ui_pages=ui_pages,
            output_dir=output_dir,
        )
    targets: set[str] = set()
    scope_terms = expand_scope_term_equivalents(scope_tokens(scope) | scope_tokens(acceptance_criteria))
    if not scope_terms:
        return []
    for module_slug, grouped_operations in operations_by_tag.items():
        haystack = " ".join(
            " ".join([operation["operation_id"], operation["tag"], operation["path"]])
            for operation in grouped_operations
        )
        if len(scope_terms & scope_tokens(haystack)) >= 1:
            base_path = Path("apps") / "api" / "src" / "modules" / module_slug
            targets.update(
                [
                    str(base_path / f"{module_slug}.controller.ts"),
                    str(base_path / f"{module_slug}.service.ts"),
                    str(base_path / f"{module_slug}.repository.ts"),
                ]
            )
    return sorted(targets)


def load_ui_pages(*args: Any, **kwargs: Any) -> Any:
    return _frontend_scaffold_renderer().load_ui_pages(*args, **kwargs)


def merge_preferred_ui_sections(*args: Any, **kwargs: Any) -> Any:
    return _frontend_scaffold_renderer().merge_preferred_ui_sections(*args, **kwargs)


def normalize_ui_input_spec(*args: Any, **kwargs: Any) -> Any:
    return _frontend_scaffold_renderer().normalize_ui_input_spec(*args, **kwargs)


def render_home_page(*args: Any, **kwargs: Any) -> str:
    return _frontend_scaffold_renderer().render_home_page(*args, **kwargs)


def render_auth_entry_page(*args: Any, **kwargs: Any) -> str:
    return _frontend_scaffold_renderer().render_auth_entry_page(*args, **kwargs)


def ui_app_context(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _frontend_scaffold_renderer().ui_app_context(*args, **kwargs)


def render_page_component(*args: Any, **kwargs: Any) -> str:
    return _frontend_scaffold_renderer().render_page_component(*args, **kwargs)


def render_ui_app(*args: Any, **kwargs: Any) -> str:
    return _frontend_scaffold_renderer().render_ui_app(*args, **kwargs)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def operation_by_contract_test_target(operations: list[dict[str, str]]) -> dict[str, str]:
    target_lookup = build_contract_test_target_lookup(list(operations))
    mapping: dict[str, str] = {}
    for operation in operations:
        operation_id = str(operation.get("operation_id", "")).strip() or f"{operation['method']}-{operation['path']}"
        method = str(operation.get("method", "")).upper()
        path = str(operation.get("path", "")).strip()
        target = target_lookup.get((operation_id, method, path))
        if target:
            mapping[f"tests/contracts/{target}"] = operation_id
    return mapping


def infer_binding_operation_id(
    *,
    source_subject: str,
    test_targets: list[str],
    operations: list[dict[str, str]],
    contract_operation_by_test: dict[str, str],
) -> str:
    direct_matches = [
        contract_operation_by_test[target]
        for target in test_targets
        if target in contract_operation_by_test and contract_operation_by_test[target]
    ]
    if len(set(direct_matches)) == 1:
        return direct_matches[0]

    normalized_subject = source_subject.lower()
    subject_matches = [
        str(operation.get("operation_id", "")).strip()
        for operation in operations
        if str(operation.get("operation_id", "")).strip()
        and str(operation.get("operation_id", "")).strip().lower() in normalized_subject
    ]
    if len(set(subject_matches)) == 1:
        return subject_matches[0]
    return ""


def scaffold_phase3_implementation(
    *,
    esp_text: str,
    openapi_spec: dict[str, object],
    phase3_trace_registry: dict[str, Any],
    output_dir: Path,
    ui_ia_contract_path: Path | None = None,
    behavior_card_models: dict[str, dict[str, Any]] | None = None,
    synthesis_brief: dict[str, Any] | None = None,
    service_authoring_packet: dict[str, Any] | None = None,
    module_synthesis_bundle_path: Path | None = None,
    action_card_execution_map: dict[str, Any] | None = None,
    action_card_execution_map_path: Path | None = None,
    business_behavior_authoring_plan: dict[str, Any] | None = None,
    business_behavior_authoring_plan_path: Path | None = None,
    agentic_semantic_decisions: dict[str, Any] | None = None,
    project_implementation_conventions: dict[str, Any] | None = None,
    module_implementation_briefs: dict[str, Any] | None = None,
    action_card_direct_implementation_driver: dict[str, Any] | None = None,
    include_backend: bool = True,
    include_frontend: bool = True,
) -> dict[str, object]:
    operations = parse_openapi_operations(openapi_spec)
    wp_rows = build_wp_lookup(esp_text)
    frontend_renderer = _frontend_scaffold_renderer() if include_frontend else None
    if frontend_renderer is not None:
        primary_surfaces = extract_nested_bullet_items(esp_text, "primary_surfaces")
        ui_pages = frontend_renderer.load_ui_pages(
            output_dir=output_dir,
            primary_surfaces=primary_surfaces,
            ui_ia_contract_path=ui_ia_contract_path,
        )
        app_context = frontend_renderer.ui_app_context(ui_pages)
        compiled_bindings = frontend_renderer.load_compiled_bindings(
            output_dir=output_dir,
            ui_ia_contract_path=ui_ia_contract_path,
        )
    else:
        ui_pages = []
        app_context = {}
        compiled_bindings = []
    runtime_specs = build_runtime_operation_specs(openapi_spec, compiled_bindings=compiled_bindings)
    module_synthesis_candidate_ledger: dict[str, Any] | None = None
    module_synthesis_bundle: dict[str, Any] | None = None
    module_synthesis_authoring_context: dict[str, Any] | None = None
    module_synthesis_summary: dict[str, Any] = {
        "mode": "disabled",
        "selected_module": "",
        "authoring_context_path": "",
        "authoring_context_sha256": "",
        "candidate_ledger_path": "",
        "selected_manifest_path": "",
        "module_behavior_plan_path": "",
        "renderer_bypass_evidence_path": "",
        "human_review_packet_path": "",
        "tvg_quality_audit_path": "",
        "obligation_consumption_audit_path": "",
        "module_rewrite_packet_path": "",
        "bypassed_renderers": [],
    }
    if module_synthesis_bundle_path is not None:
        module_synthesis_tools = _module_synthesis_tools()
        module_synthesis_candidate_ledger = module_synthesis_tools.build_module_candidate_ledger(
            openapi_spec=openapi_spec,
            phase3_trace_registry=phase3_trace_registry,
            operation_specs=runtime_specs,
        )
        manifest_path = module_synthesis_bundle_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("module synthesis bundle manifest must be a JSON object")
        selected_module = str(manifest.get("selected_module", "")).strip()
        module_synthesis_authoring_context = module_synthesis_tools.build_module_authoring_context(
            openapi_spec=openapi_spec,
            candidate_ledger=module_synthesis_candidate_ledger,
            selected_module=selected_module,
            phase3_trace_registry=phase3_trace_registry,
            operation_specs=runtime_specs,
            behavior_card_models=behavior_card_models,
        )
        module_synthesis_bundle = module_synthesis_tools.load_module_synthesis_bundle(
            bundle_root=module_synthesis_bundle_path,
            candidate_ledger=module_synthesis_candidate_ledger,
            authoring_context=module_synthesis_authoring_context,
        )
        quality_paths = module_synthesis_tools.write_module_synthesis_quality_evidence(
            output_dir=output_dir,
            bundle=module_synthesis_bundle,
        )
        module_synthesis_summary["module_behavior_plan_path"] = quality_paths["module_behavior_plan_path"]
        module_synthesis_summary["tvg_quality_audit_path"] = quality_paths["tvg_quality_audit_path"]
        module_synthesis_summary["obligation_consumption_audit_path"] = quality_paths["obligation_consumption_audit_path"]
        module_synthesis_summary["module_rewrite_packet_path"] = quality_paths["module_rewrite_packet_path"]
        quality_audit = module_synthesis_bundle.get("quality_audit", {})
        if not isinstance(quality_audit, dict) or quality_audit.get("overall_quality_gate") != "pass":
            failures = "; ".join(str(item) for item in quality_audit.get("failures", []) if str(item).strip()) if isinstance(quality_audit, dict) else ""
            raise ValueError(f"module synthesis quality gate failed: {failures}")

    module_targets_by_contract: dict[str, list[str]] = {}
    operations_by_tag: dict[str, list[dict[str, str]]] = {}
    for operation in operations:
        operations_by_tag.setdefault(
            stable_slug(
                operation["tag"],
                fallback=str(operation.get("operation_id") or "default"),
            ),
            [],
        ).append(operation)

    default_tenant_id = infer_default_tenant(runtime_specs)
    if include_backend:
        write_text(output_dir / "apps" / "api" / "src" / "common" / "envelope.ts", render_envelope_module())
        write_text(output_dir / "apps" / "api" / "src" / "common" / "errors.ts", render_errors_module())
        write_text(output_dir / "apps" / "api" / "src" / "common" / "pagination.ts", render_pagination_module())
        write_text(output_dir / "apps" / "api" / "src" / "common" / "auth-session.ts", render_auth_session_module())
        write_text(output_dir / "apps" / "api" / "src" / "common" / "runtime-adapter.ts", render_runtime_adapter_module())
        write_text(
            output_dir / "apps" / "api" / "src" / "common" / "operation-support.ts",
            render_generated_runtime(runtime_specs, default_tenant_id),
        )
        write_text(
            output_dir / "apps" / "api" / "src" / "common" / "generated-runtime.ts",
            render_generated_runtime_facade(),
        )
        write_text(
            output_dir / "apps" / "api" / "src" / "generated-api-router.ts",
            render_generated_api_router(
                operations_by_tag=operations_by_tag,
                operation_specs=runtime_specs,
                compiled_bindings=compiled_bindings,
            ),
        )
        write_text(
            output_dir / "tests" / "support" / "runtime-test-kit.ts",
            render_runtime_test_kit(operations_by_tag=operations_by_tag),
        )
        write_text(
            output_dir / "tests" / "support" / "backend-runtime-harness.ts",
            render_backend_runtime_harness(),
        )
        foundation_unit_test_paths = backend_foundation_unit_test_paths()
        for relative_path in foundation_unit_test_paths:
            write_text(output_dir / Path(relative_path), render_backend_foundation_unit_test(runtime_specs))
        write_phase3_diagnostic_surface(
            output_dir,
            "generated-runtime-positioning.md",
            render_generated_runtime_positioning(),
        )
    else:
        foundation_unit_test_paths = []
    if include_frontend:
        assert frontend_renderer is not None
        write_text(output_dir / "apps" / "web" / "app" / "page.tsx", frontend_renderer.render_home_page(ui_pages, operations, wp_rows))
        write_text(output_dir / "apps" / "web" / "app" / "ui-app.tsx", frontend_renderer.render_ui_app(ui_pages))
        route_guard_policy = app_context.get("route_guard_policy") if isinstance(app_context.get("route_guard_policy"), dict) else {}
        auth_entry_route = frontend_renderer.normalize_ui_route((route_guard_policy or {}).get("auth_entry_route") or "")
        if auth_entry_route and auth_entry_route != "/":
            write_text(output_dir / "apps" / "web" / "app" / auth_entry_route.strip("/") / "page.tsx", frontend_renderer.render_auth_entry_page(ui_pages))
        write_text(output_dir / "apps" / "web" / "app" / "workflow-storage.ts", frontend_renderer.render_workflow_storage_module())
        write_text(output_dir / "apps" / "web" / "app" / "role-session-storage.ts", frontend_renderer.render_role_session_storage_module())
        write_text(output_dir / "apps" / "web" / "app" / "workflow-progress-storage.ts", frontend_renderer.render_workflow_progress_storage_module())

    written_modules: list[str] = []
    written_repositories: list[str] = []
    written_unit_tests: list[str] = [str(output_dir / Path(relative_path)) for relative_path in foundation_unit_test_paths]
    contract_target_lookup = build_contract_test_target_lookup(list(operations))
    backend_operation_items = operations_by_tag.items() if include_backend else []
    for module_slug, grouped_operations in backend_operation_items:
        module_class = camel_case(module_slug)
        controller_path = output_dir / "apps" / "api" / "src" / "modules" / module_slug / f"{module_slug}.controller.ts"
        service_path = output_dir / "apps" / "api" / "src" / "modules" / module_slug / f"{module_slug}.service.ts"
        repository_path = output_dir / "apps" / "api" / "src" / "modules" / module_slug / f"{module_slug}.repository.ts"
        unit_test_path = output_dir / backend_module_unit_test_path(module_slug)
        module_synthesis_units = synthesis_units_for_module(
            synthesis_brief,
            module_slug=module_slug,
            operations=grouped_operations,
        )
        write_text(
            controller_path,
            render_controller_module(module_class, grouped_operations, module_slug),
        )
        if module_synthesis_bundle is not None and str(module_synthesis_bundle.get("selected_module", "")) == module_slug:
            files_by_role = module_synthesis_bundle["files_by_role"]
            write_text(service_path, str(files_by_role["service"]["content"]))
            write_text(repository_path, str(files_by_role["repository"]["content"]))
            write_text(unit_test_path, str(files_by_role["unit-test"]["content"]))
        else:
            write_text(
                service_path,
                render_service_module(
                    module_class,
                    grouped_operations,
                    module_slug,
                    behavior_card_models=behavior_card_models,
                    operation_specs=runtime_specs,
                    synthesis_units=module_synthesis_units,
                    authoring_packet=service_authoring_packet,
                    business_behavior_authoring_plan=business_behavior_authoring_plan,
                    action_card_execution_map=action_card_execution_map,
                    action_card_direct_implementation_driver=action_card_direct_implementation_driver,
                    agentic_semantic_decisions=agentic_semantic_decisions,
                    module_implementation_briefs=module_implementation_briefs,
                ),
            )
            write_text(
                repository_path,
                render_repository_module(
                    module_class,
                    grouped_operations,
                    module_slug,
                    runtime_specs,
                    behavior_card_models=behavior_card_models,
                    business_behavior_authoring_plan=business_behavior_authoring_plan,
                    action_card_execution_map=action_card_execution_map,
                    action_card_direct_implementation_driver=action_card_direct_implementation_driver,
                    agentic_semantic_decisions=agentic_semantic_decisions,
                    module_implementation_briefs=module_implementation_briefs,
                ),
            )
            write_text(
                unit_test_path,
                render_backend_module_unit_test(
                    module_slug,
                    grouped_operations,
                    runtime_specs,
                    behavior_card_models=behavior_card_models,
                    synthesis_units=module_synthesis_units,
                    business_behavior_authoring_plan=business_behavior_authoring_plan,
                    action_card_execution_map=action_card_execution_map,
                    action_card_direct_implementation_driver=action_card_direct_implementation_driver,
                    agentic_semantic_decisions=agentic_semantic_decisions,
                    module_implementation_briefs=module_implementation_briefs,
                ),
            )
        written_modules.extend([str(controller_path), str(service_path)])
        written_repositories.append(str(repository_path))
        written_unit_tests.append(str(unit_test_path))
        for operation in grouped_operations:
            contract_path = (
                f"tests/contracts/{contract_target_lookup[(operation['operation_id'], str(operation['method']).upper(), str(operation['path']))]}"
            )
            module_targets_by_contract.setdefault(contract_path, [])
            module_targets_by_contract[contract_path].extend(
                [
                    str(controller_path.relative_to(output_dir)),
                    str(service_path.relative_to(output_dir)),
                    str(repository_path.relative_to(output_dir)),
                ]
            )

    if module_synthesis_candidate_ledger is not None and module_synthesis_bundle is not None:
        module_synthesis_summary = module_synthesis_tools.write_module_synthesis_evidence(
            output_dir=output_dir,
            candidate_ledger=module_synthesis_candidate_ledger,
            bundle=module_synthesis_bundle,
            authoring_context=module_synthesis_authoring_context,
        )

    written_pages: list[str] = []
    frontend_pages = ui_pages if include_frontend else []
    for index, page in enumerate(frontend_pages):
        surface = str(page.get("page_title") or "").strip()
        if not surface:
            continue
        assert frontend_renderer is not None
        route = frontend_renderer.ui_page_route_segment(page, surface)
        page_path = output_dir / "apps" / "web" / "app" / route / "page.tsx"
        unit_test_path = output_dir / frontend_surface_unit_test_path(route)
        write_text(
            page_path,
            frontend_renderer.render_page_component(
                surface,
                page_contract=page,
                related_operations=frontend_renderer.related_operations_for_surface(surface, operations, page_contract=page),
                related_work_packages=frontend_renderer.related_work_packages_for_surface(surface, wp_rows, page_contract=page),
                navigation={
                    "previous_route": str(frontend_pages[index - 1].get("route", "")).strip() if index > 0 else "",
                    "next_route": str(frontend_pages[index + 1].get("route", "")).strip() if index + 1 < len(frontend_pages) else "",
                },
                app_context=app_context,
            ),
        )
        write_text(unit_test_path, frontend_renderer.render_frontend_page_unit_test(route))
        written_pages.append(str(page_path))
        written_unit_tests.append(str(unit_test_path))

    work_package_plans: list[str] = []
    inferred_targets_by_wp: dict[str, list[str]] = {}
    for row in wp_rows:
        wp_id = str(row.get("wp_id", "")).strip()
        scope = str(row.get("scope", row.get("implementation_scope", ""))).strip()
        acceptance_criteria = str(row.get("acceptance_criteria", "")).strip()
        target = output_dir / "work-packages" / wp_id.lower() / "implementation-plan.md"
        write_text(
            target,
            "\n".join(
                [
                    f"# {wp_id} Implementation Plan",
                    "",
                    f"- scope: {scope}",
                    f"- acceptance_criteria: {acceptance_criteria}",
                    f"- estimated_effort: {str(row.get('estimated_effort', 'n/a')).strip()}",
                    f"- depends_on: {', '.join(row.get('depends_on', [])) or 'none'}",
                    f"- linked_rbi_or_slice: {', '.join(row.get('linked_rbi_or_slice', [])) or 'none'}",
                    "",
                ]
            ),
        )
        work_package_plans.append(str(target))
        inferred_targets_by_wp[wp_id] = infer_targets_from_scope(
            scope=scope,
            acceptance_criteria=acceptance_criteria,
            operations_by_tag=operations_by_tag,
            ui_pages=ui_pages,
            output_dir=output_dir,
        )

    trace_rows = phase3_trace_registry.get("rows", [])
    if not isinstance(trace_rows, list):
        raise ValueError("phase-3 trace registry must contain rows")

    direct_work_package_map: dict[str, list[str]] = {}
    test_target_to_source_ids: dict[str, set[str]] = {}
    for row in trace_rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "")).strip().upper()
        source_subject = str(row.get("source_subject", "")).strip()
        direct_work_package_map[source_id] = suggest_work_packages(
            source_id,
            source_subject,
            wp_rows,
            source_type=str(row.get("source_type", "")).strip(),
            verification_hook=str(row.get("verification_hook", "")).strip(),
        )
        for test_target in [str(item) for item in row.get("test_targets", []) if str(item).strip()]:
            test_target_to_source_ids.setdefault(test_target, set()).add(source_id)

    binding_rows: list[dict[str, Any]] = []
    contract_operation_by_test = operation_by_contract_test_target(operations)
    for row in trace_rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "")).strip().upper()
        source_subject = str(row.get("source_subject", "")).strip()
        test_targets = [str(item) for item in row.get("test_targets", []) if str(item).strip()]
        implementation_targets: list[str] = []
        for test_target in test_targets:
            implementation_targets.extend(module_targets_by_contract.get(test_target, []))
        implementation_targets.extend(foundation_implementation_targets_for_test_targets(test_targets))
        implementation_targets = sorted(set(implementation_targets))
        work_packages = list(direct_work_package_map.get(source_id, []))
        if not work_packages:
            for test_target in test_targets:
                for related_source_id in sorted(test_target_to_source_ids.get(test_target, set())):
                    if related_source_id == source_id:
                        continue
                    work_packages.extend(direct_work_package_map.get(related_source_id, []))
        work_packages = sorted(set(work_packages))
        if not work_packages and implementation_targets:
            work_packages = infer_work_packages_from_targets(
                implementation_targets=implementation_targets,
                inferred_targets_by_wp=inferred_targets_by_wp,
            )
        if not work_packages:
            work_packages = infer_work_packages_from_replay_overlap(
                source_row=row,
                trace_rows=trace_rows,
            )
        if not implementation_targets and work_packages:
            for wp_id in work_packages:
                implementation_targets.extend(inferred_targets_by_wp.get(wp_id, []))
            if not implementation_targets:
                implementation_targets.extend(
                    [str((Path("work-packages") / wp_id.lower() / "implementation-plan.md")) for wp_id in work_packages]
                )
        binding_row = {
            "source_id": source_id,
            "source_type": str(row.get("source_type", "")).strip(),
            "source_subject": source_subject,
            "test_targets": sorted(set(test_targets)),
            "implementation_targets": sorted(set(implementation_targets)),
            "work_packages": work_packages,
            "runtime_evidence_refs": sorted(set(test_targets)),
            "binding_status": "suggested",
        }
        operation_id = infer_binding_operation_id(
            source_subject=source_subject,
            test_targets=sorted(set(test_targets)),
            operations=operations,
            contract_operation_by_test=contract_operation_by_test,
        )
        if operation_id:
            binding_row["operation_id"] = operation_id
            behavior_model = (behavior_card_models or {}).get(operation_id)
            operation_semantics = (
                behavior_model.get("operation_semantics", {})
                if isinstance(behavior_model, dict) and isinstance(behavior_model.get("operation_semantics"), dict)
                else {}
            )
            if operation_semantics:
                binding_row["operation_semantics"] = dict(operation_semantics)
        binding_rows.append(binding_row)

    propagate_shared_test_bindings(
        binding_rows=binding_rows,
        inferred_targets_by_wp=inferred_targets_by_wp,
    )
    rebind_cross_operation_test_rows(
        binding_rows=binding_rows,
        operations=operations,
        output_dir=output_dir,
        inferred_targets_by_wp=inferred_targets_by_wp,
        wp_rows=wp_rows,
    )
    propagate_shared_test_bindings(
        binding_rows=binding_rows,
        inferred_targets_by_wp=inferred_targets_by_wp,
    )
    append_generated_unit_test_bindings(binding_rows)
    append_generated_sql_test_bindings(binding_rows, output_dir=output_dir)

    action_card_projection_default = action_card_execution_map is not None and business_behavior_authoring_plan is not None
    business_behavior_plan_default = business_behavior_authoring_plan is not None and not action_card_projection_default
    semantic_decision_summary = (
        agentic_semantic_decisions.get("summary", {})
        if isinstance(agentic_semantic_decisions, dict) and isinstance(agentic_semantic_decisions.get("summary"), dict)
        else {}
    )
    project_convention_summary = (
        project_implementation_conventions.get("summary", {})
        if isinstance(project_implementation_conventions, dict)
        and isinstance(project_implementation_conventions.get("summary"), dict)
        else {}
    )
    module_implementation_summary = (
        module_implementation_briefs.get("summary", {})
        if isinstance(module_implementation_briefs, dict)
        and isinstance(module_implementation_briefs.get("summary"), dict)
        else {}
    )
    action_card_direct_driver_summary = (
        action_card_direct_implementation_driver.get("summary", {})
        if isinstance(action_card_direct_implementation_driver, dict)
        and isinstance(action_card_direct_implementation_driver.get("summary"), dict)
        else {}
    )
    report = {
        "artifact_kind": "compiled-binding-artifact",
        "compiled_bindings": compiled_bindings,
        "rows": binding_rows,
        "metadata": {
            "agentic_body_authoring_default": True,
            "agentic_body_authoring_mode": "default-p3-mainline",
            "agentic_body_authoring_control_boundary": "workflow supplies OpenAPI/runtime/trace context; Agentic body authoring kernel shapes default service/repository/unit bodies; evidence verifies runtime and caps claims",
            "agentic_body_authoring_gate_policy": "no new F5/F6-style gate controls default content truth",
            "business_behavior_authoring_plan_default": business_behavior_plan_default,
            "business_behavior_authoring_plan_kind": str((business_behavior_authoring_plan or {}).get("artifact_kind", ""))
            if business_behavior_plan_default
            else "",
            "business_behavior_authoring_plan_path": str(business_behavior_authoring_plan_path or "")
            if business_behavior_plan_default
            else "",
            "action_card_execution_map_default": action_card_execution_map is not None,
            "action_card_authoring_projection_default": action_card_projection_default,
            "action_card_authoring_projection_persisted": False,
            "action_card_rich_context_persisted": False,
            "agentic_semantic_authoring_default": agentic_semantic_decisions is not None,
            "agentic_semantic_authoring_mode": str((agentic_semantic_decisions or {}).get("mode", "")),
            "agentic_semantic_decision_count": int(semantic_decision_summary.get("agentic_semantic_decision_count", 0) or 0),
            "script_semantic_default_count": int(semantic_decision_summary.get("script_semantic_default_count", 0) or 0),
            "owner_not_declared_count": int(semantic_decision_summary.get("owner_not_declared_count", 0) or 0),
            "aggregate_review_bound_count": int(semantic_decision_summary.get("aggregate_review_bound_count", 0) or 0),
            "default_heavy_artifact_count": int(semantic_decision_summary.get("default_heavy_artifact_count", 0) or 0),
            "project_convention_synthesis_default": project_implementation_conventions is not None,
            "project_convention_default_heavy_artifact_count": int(
                project_convention_summary.get("default_heavy_artifact_count", 0) or 0
            ),
            "agentic_module_implementation_brief_default": module_implementation_briefs is not None,
            "agentic_module_implementation_brief_mode": str((module_implementation_briefs or {}).get("mode", "")),
            "agentic_module_implementation_brief_module_count": int(
                module_implementation_summary.get("module_count", 0) or 0
            ),
            "agentic_module_implementation_brief_persisted": False,
            "agentic_module_implementation_default_heavy_artifact_count": int(
                module_implementation_summary.get("persisted_default_heavy_artifact_count", 0) or 0
            ),
            "action_card_direct_implementation_driver_default": action_card_direct_implementation_driver is not None,
            "action_card_direct_implementation_driver_kind": str(
                (action_card_direct_implementation_driver or {}).get("artifact_kind", "")
            ),
            "action_card_direct_implementation_driver_persisted": False,
            "action_card_direct_implementation_driver_operation_count": int(
                action_card_direct_driver_summary.get("operation_count", 0) or 0
            ),
            "action_card_direct_implementation_default_heavy_artifact_count": int(
                action_card_direct_driver_summary.get("persisted_default_heavy_artifact_count", 0) or 0
            ),
            "module_synthesis_mode": module_synthesis_summary["mode"],
        },
        "summary": {
            "binding_count": len(binding_rows),
            "compiled_binding_count": len(compiled_bindings),
            "work_package_count": len(wp_rows),
            "module_stub_count": len(written_modules),
            "repository_stub_count": len(written_repositories),
            "frontend_page_count": len(written_pages),
            "unit_test_count": len(written_unit_tests),
            "work_package_plan_count": len(work_package_plans),
            "runtime_positioning_present": True,
            "synthesis_selected_unit_count": len(synthesis_brief.get("selected_semantic_units", []))
            if isinstance(synthesis_brief, dict) and isinstance(synthesis_brief.get("selected_semantic_units"), list)
            else 0,
            "agentic_body_authoring_default": True,
            "agentic_body_authoring_mode": "default-p3-mainline",
            "business_behavior_authoring_plan_default": business_behavior_plan_default,
            "business_behavior_authoring_plan_path": str(business_behavior_authoring_plan_path or "")
            if business_behavior_plan_default
            else "",
            "action_card_authoring_projection_default": action_card_projection_default,
            "action_card_authoring_projection_persisted": False,
            "action_card_rich_context_persisted": False,
            "agentic_semantic_authoring_default": agentic_semantic_decisions is not None,
            "agentic_semantic_decision_count": int(semantic_decision_summary.get("agentic_semantic_decision_count", 0) or 0),
            "script_semantic_default_count": int(semantic_decision_summary.get("script_semantic_default_count", 0) or 0),
            "owner_not_declared_count": int(semantic_decision_summary.get("owner_not_declared_count", 0) or 0),
            "aggregate_review_bound_count": int(semantic_decision_summary.get("aggregate_review_bound_count", 0) or 0),
            "default_heavy_artifact_count": int(semantic_decision_summary.get("default_heavy_artifact_count", 0) or 0),
            "project_convention_synthesis_default": project_implementation_conventions is not None,
            "project_convention_default_heavy_artifact_count": int(
                project_convention_summary.get("default_heavy_artifact_count", 0) or 0
            ),
            "agentic_module_implementation_brief_default": module_implementation_briefs is not None,
            "agentic_module_implementation_brief_module_count": int(
                module_implementation_summary.get("module_count", 0) or 0
            ),
            "agentic_module_implementation_brief_persisted": False,
            "agentic_module_implementation_default_heavy_artifact_count": int(
                module_implementation_summary.get("persisted_default_heavy_artifact_count", 0) or 0
            ),
            "action_card_direct_implementation_driver_default": action_card_direct_implementation_driver is not None,
            "action_card_direct_implementation_driver_persisted": False,
            "action_card_direct_implementation_driver_operation_count": int(
                action_card_direct_driver_summary.get("operation_count", 0) or 0
            ),
            "action_card_direct_implementation_default_heavy_artifact_count": int(
                action_card_direct_driver_summary.get("persisted_default_heavy_artifact_count", 0) or 0
            ),
            "business_behavior_authoring_plan_operation_count": (business_behavior_authoring_plan or {})
            .get("summary", {})
            .get("operation_count", 0)
            if isinstance((business_behavior_authoring_plan or {}).get("summary", {}), dict)
            else 0,
            "module_synthesis_mode": module_synthesis_summary["mode"],
            "module_synthesis_selected_module": module_synthesis_summary["selected_module"],
            "module_synthesis_authoring_context_path": module_synthesis_summary["authoring_context_path"],
            "module_synthesis_authoring_context_sha256": module_synthesis_summary["authoring_context_sha256"],
            "module_synthesis_behavior_plan_path": module_synthesis_summary["module_behavior_plan_path"],
            "module_synthesis_renderer_bypass_evidence_path": module_synthesis_summary["renderer_bypass_evidence_path"],
            "module_synthesis_human_review_packet_path": module_synthesis_summary["human_review_packet_path"],
            "module_synthesis_tvg_quality_audit_path": module_synthesis_summary["tvg_quality_audit_path"],
            "module_synthesis_obligation_consumption_audit_path": module_synthesis_summary["obligation_consumption_audit_path"],
            "module_synthesis_rewrite_packet_path": module_synthesis_summary["module_rewrite_packet_path"],
        },
    }
    output_path = output_dir / "implementation-bindings.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"output_path": str(output_path), **report["summary"]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Phase-3 implementation bindings and source scaffolds")
    parser.add_argument("--esp", required=True)
    parser.add_argument("--openapi", required=True)
    parser.add_argument("--trace-registry", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ui-ia-contract")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir).resolve()
    summary = scaffold_phase3_implementation(
        esp_text=Path(args.esp).resolve().read_text(encoding="utf-8"),
        openapi_spec=load_openapi_document(Path(args.openapi).resolve()),
        phase3_trace_registry=json.loads(Path(args.trace_registry).resolve().read_text(encoding="utf-8")),
        output_dir=output_dir,
        ui_ia_contract_path=Path(args.ui_ia_contract).resolve() if args.ui_ia_contract else None,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
