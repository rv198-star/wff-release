#!/usr/bin/env python3
"""Render generated Phase-3 API support artifacts."""

from __future__ import annotations

import json
from typing import Any

from common.script_data_assets import load_script_text_asset
from phase3.renderer_common import (
    camel_case,
    extract_ui_policy_roles,
    lower_camel,
    normalize_ui_role_name,
    ordered_ui_roles,
    runtime_spec_for_operation,
    split_ui_role_candidates,
)


WFF_SCRIPT_DATA_ASSETS = (
    "scripts/phase3/data/api-runtime-adapter.ts.template",
    "scripts/phase3/data/api-envelope.ts.template",
    "scripts/phase3/data/api-errors.ts.template",
    "scripts/phase3/data/api-pagination.ts.template",
    "scripts/phase3/data/api-auth-session.ts.template",
    "scripts/phase3/data/api-runtime-test-kit.ts.template",
    "scripts/phase3/data/api-generated-router.ts.template",
)


def load_api_support_template(template_name: str) -> str:
    return load_script_text_asset(__file__, template_name)


def render_runtime_adapter_module() -> str:
    return load_api_support_template("api-runtime-adapter.ts.template")


def render_envelope_module() -> str:
    return load_api_support_template("api-envelope.ts.template")


def render_errors_module() -> str:
    return load_api_support_template("api-errors.ts.template")


def render_pagination_module() -> str:
    return load_api_support_template("api-pagination.ts.template")


def render_auth_session_module() -> str:
    return load_api_support_template("api-auth-session.ts.template")


def index_compiled_bindings_by_endpoint(
    compiled_bindings: list[dict[str, Any]] | None,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    binding_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in compiled_bindings or []:
        method = str(row.get("http_method") or "").strip().upper()
        path = str(row.get("api_endpoint") or "").strip()
        if not method or not path:
            continue
        binding_index.setdefault((method, path), []).append(row)
    return binding_index


def binding_rbac_policies(rows: list[dict[str, Any]], *, locale: str | None = None) -> list[str]:
    return ordered_ui_roles(
        *[
            extract_ui_policy_roles(
                row.get("rbac_policy") or row.get("visibility_rule") or "",
                locale=locale,
            )
            for row in rows
            if isinstance(row, dict)
        ],
        locale=locale,
    )


def render_generated_runtime_facade() -> str:
    return "\n".join(
        [
            'import {',
            "  buildFailurePayload,",
            "  buildOperationPayload,",
            "  countGeneratedRecords,",
            "  getAuditRecords,",
            "  getGeneratedRecord,",
            "  invokeGeneratedOperation as invokeOperationSupport,",
            "  listGeneratedRecords,",
            "  normalizeIdValue,",
            "  persistenceProbeHints,",
            "  recordGeneratedAuditEvent,",
            "  resetGeneratedRuntime as resetSupportRuntime,",
            "  seedGeneratedRuntimePersistence as seedSupportPersistence,",
            "  seedGeneratedRuntimeState as seedSupportRuntimeState,",
            '} from "./operation-support.js";',
            "",
            "/**",
            " * Compatibility facade kept for existing tests and bootstrap tooling.",
            " *",
            " * Real repository execution should import explicit helpers from",
            " * `operation-support.ts` instead of routing every call through this facade.",
            " */",
            "",
            "export {",
            "  buildFailurePayload,",
            "  buildOperationPayload,",
            "  countGeneratedRecords,",
            "  getAuditRecords,",
            "  getGeneratedRecord,",
            "  listGeneratedRecords,",
            "  normalizeIdValue,",
            "  persistenceProbeHints,",
            "  recordGeneratedAuditEvent,",
            "  seedSupportPersistence as seedGeneratedRuntimePersistence,",
            "  seedSupportRuntimeState as seedGeneratedRuntimeState,",
            "};",
            "",
            "export function resetGeneratedRuntime(): void {",
            "  resetSupportRuntime();",
            "}",
            "",
            "export async function invokeGeneratedOperation(operationId: string, payload: unknown): Promise<unknown> {",
            "  return invokeOperationSupport(operationId, payload);",
            "}",
            "",
        ]
    )


def render_runtime_test_kit(
    *,
    operations_by_tag: dict[str, list[dict[str, str]]],
) -> str:
    import_lines = [
        'import { ApiError } from "../../apps/api/src/common/errors";',
        'import {',
        "  buildFailurePayload,",
        "  buildOperationPayload,",
        "  countGeneratedRecords,",
        "  getGeneratedRecord,",
        "  getAuditRecords,",
        "  invokeGeneratedOperation,",
        "  listGeneratedRecords,",
        "  resetGeneratedRuntime as resetGeneratedRuntimeSupport,",
        '} from "../../apps/api/src/common/generated-runtime";',
    ]
    handler_lines = [
        "const operationHandlers: Record<string, (payload: unknown) => Promise<unknown>> = {",
    ]
    for module_slug, grouped_operations in operations_by_tag.items():
        controller_class = f"{camel_case(module_slug)}Controller"
        import_lines.append(
            f'import {{ {controller_class} }} from "../../apps/api/src/modules/{module_slug}/{module_slug}.controller";'
        )
        for operation in grouped_operations:
            operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
            method_name = lower_camel(operation_id)
            handler_lines.append(
                f'  "{operation_id}": (payload) => new {controller_class}().{method_name}(payload),'
            )
    handler_lines.extend(["};", ""])
    return load_api_support_template("api-runtime-test-kit.ts.template").replace(
        "__IMPORT_LINES__",
        "\n".join(import_lines),
    ).replace(
        "__OPERATION_HANDLER_BLOCK__",
        "\n".join(handler_lines),
    )


def render_generated_api_router(
    *,
    operations_by_tag: dict[str, list[dict[str, str]]],
    operation_specs: dict[str, dict[str, Any]],
    compiled_bindings: list[dict[str, Any]] | None = None,
) -> str:
    import_lines = [
        'import type { IncomingMessage, ServerResponse } from "node:http";',
        'import { URL } from "node:url";',
        'import { normalizeAuthSession, parseAuthorizationHeader } from "./common/auth-session.js";',
        'import { ApiError, createApiError } from "./common/errors.js";',
        'import { recordGeneratedAuditEvent } from "./common/operation-support.js";',
    ]
    binding_index = index_compiled_bindings_by_endpoint(compiled_bindings)
    route_rows: list[str] = []
    for module_slug, grouped_operations in operations_by_tag.items():
        controller_class = f"{camel_case(module_slug)}Controller"
        import_lines.append(f'import {{ {controller_class} }} from "./modules/{module_slug}/{module_slug}.controller.js";')
        for operation in grouped_operations:
            operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
            spec = runtime_spec_for_operation(operation, operation_specs)
            success_status = int(str(spec.get("successStatus", "200")).strip() or "200")
            matching_bindings = binding_index.get((str(operation["method"]).upper(), str(operation["path"]).strip()), [])
            binding_sources = [
                str(row.get("service_binding_id") or "").strip()
                for row in matching_bindings
                if str(row.get("service_binding_id") or "").strip()
            ]
            binding_modes = sorted(
                {
                    str(row.get("binding_mode") or "").strip()
                    for row in matching_bindings
                    if str(row.get("binding_mode") or "").strip()
                }
            )
            rbac_policies = binding_rbac_policies(matching_bindings)
            failure_semantics = sorted(
                {
                    str(row.get("failure_codes") or "").strip()
                    for row in matching_bindings
                    if str(row.get("failure_codes") or "").strip()
                }
            )
            route_rows.extend(
                [
                    "  {",
                    f'    operationId: "{operation_id}",',
                    f'    method: "{str(operation["method"]).upper()}",',
                    f'    pathTemplate: "{operation["path"]}",',
                    f"    successStatus: {success_status},",
                    f"    bindingSources: {json.dumps(binding_sources, ensure_ascii=False)},",
                    f"    bindingModes: {json.dumps(binding_modes, ensure_ascii=False)},",
                    f"    rbacPolicies: {json.dumps(rbac_policies, ensure_ascii=False)},",
                    f"    failureSemantics: {json.dumps(failure_semantics, ensure_ascii=False)},",
                    f"    handler: (payload) => new {controller_class}().{lower_camel(operation_id)}(payload),",
                    "  },",
                ]
            )
    route_rows_text = "\n".join(route_rows)
    return (
        load_api_support_template("api-generated-router.ts.template")
        .replace("__IMPORT_LINES__", "\n".join(import_lines))
        .replace(
            "__DERIVED_ARTIFACT_AUTHORITY__",
            "compiled-bindings" if binding_index else "missing-compiled-bindings",
        )
        .replace("__ROUTE_ROWS_BLOCK__", f"{route_rows_text}\n" if route_rows_text else "")
    )


def render_generated_runtime_positioning() -> str:
    return "\n".join(
        [
            "# Generated Runtime Positioning",
            "",
            "## Scope",
            "- The foundation package may include a generated runtime to bootstrap early verification, but Phase-3 is not complete while business behavior still depends primarily on it.",
            "- `generated-runtime.ts` now exists as a compatibility facade; shared execution semantics live in `operation-support.ts`, and repository modules should bind through explicit operation plans rather than treating the facade as the default backend.",
            "- Generated controller/service/repository adapters preserve the frozen Phase-2 contract surface, but they must be replaced with real implementation code before `delivery-ready`.",
            "",
            "## Why This Exists In Phase-3",
            "- It makes contract, scenario, replay, lint, typecheck, and build lanes executable early in the implementation cycle.",
            "- It exposes semantic gaps early without claiming that the underlying business/domain stack is complete.",
            "",
            "## Concurrency Validation Boundary",
            "- Phase-3 conflict scenarios normally validate deterministic conflict-path semantics against the generated runtime.",
            "- They prove idempotency, version-conflict handling, retry guidance, and authoritative final state preservation.",
            "- They do not, by themselves, prove production-grade parallel race safety, database lock behavior, or multi-node contention correctness.",
            "",
            "## Replacement Rule",
            "1. Replace repository delegates with real DAL/domain implementations during Phase-3 implementation, not as a default deferred step.",
            "2. Keep the frozen OpenAPI plus unit/contract/scenario/replay tests green during each replacement.",
            "3. Do not treat `generated-runtime.ts` as delivery evidence once real implementation work is underway.",
            "",
            "## Completion Interpretation",
            "- `foundation-ready` means the scaffold and failing-test package are frozen and implementation may start.",
            "- `delivery-ready` requires runnable implementation code plus executed unit/contract/scenario/replay evidence; scaffold-only runtime behavior is insufficient.",
            "",
        ]
    )
