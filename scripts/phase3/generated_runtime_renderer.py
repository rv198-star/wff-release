#!/usr/bin/env python3
"""Render generated Phase-3 operation-support runtime artifacts."""

from __future__ import annotations

import json
from typing import Any

from common.script_data_assets import load_script_text_asset
from phase3.api_support_renderer import binding_rbac_policies, index_compiled_bindings_by_endpoint
from phase3.renderer_common import json_clone, normalize_default_tenant_id, stable_uuid_seed


WFF_SCRIPT_DATA_ASSETS = ("scripts/phase3/data/generated-runtime.ts.template",)


def load_generated_runtime_template() -> str:
    return load_script_text_asset(__file__, "generated-runtime.ts.template")


def build_runtime_operation_specs(
    openapi_spec: dict[str, object],
    compiled_bindings: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    spec_index: dict[str, dict[str, Any]] = {}
    paths = openapi_spec.get("paths", {})
    if not isinstance(paths, dict):
        return spec_index
    binding_index = index_compiled_bindings_by_endpoint(compiled_bindings)
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId", "")).strip()
            if not operation_id:
                continue
            responses = operation.get("responses", {})
            if not isinstance(responses, dict):
                responses = {}
            success_status = next((code for code in sorted(responses) if str(code).startswith("2")), "200")
            success_content = responses.get(success_status, {})
            success_example: object = {}
            if isinstance(success_content, dict):
                content = success_content.get("content", {})
                if isinstance(content, dict):
                    app_json = content.get("application/json", {})
                    if isinstance(app_json, dict):
                        success_example = json_clone(app_json.get("example", {}))
            request_example: object = {}
            request_required_fields: list[str] = []
            request_schema_source = ""
            request_body = operation.get("requestBody", {})
            if isinstance(request_body, dict):
                content = request_body.get("content", {})
                if isinstance(content, dict):
                    app_json = content.get("application/json", {})
                    if isinstance(app_json, dict):
                        request_example = json_clone(app_json.get("example", {}))
                        request_schema = app_json.get("schema", {})
                        if isinstance(request_schema, dict):
                            request_schema_source = str(request_schema.get("x-schema-source", "")).strip()
                            if request_schema_source != "inferred-from-example":
                                raw_required = request_schema.get("required", [])
                                if isinstance(raw_required, list):
                                    request_required_fields = [
                                        str(item).strip()
                                        for item in raw_required
                                        if str(item).strip()
                                    ]
            failure_cases: list[dict[str, str]] = []
            for status, response in responses.items():
                if not str(status).startswith(("4", "5")):
                    continue
                if not isinstance(response, dict):
                    continue
                example = {}
                content = response.get("content", {})
                if isinstance(content, dict):
                    app_json = content.get("application/json", {})
                    if isinstance(app_json, dict):
                        example = app_json.get("example", {})
                failure_cases.append(
                    {
                        "status": str(status),
                        "error_kind": str(example.get("error_kind", "")).strip(),
                        "error_code": str(example.get("error_code", "")).strip(),
                        "retryability": str(example.get("retryability", "")).strip(),
                    }
                )
            parameters = operation.get("parameters", [])
            path_params = []
            required_path_params = []
            if isinstance(parameters, list):
                for parameter in parameters:
                    if not isinstance(parameter, dict):
                        continue
                    if str(parameter.get("in", "")).strip() == "path":
                        parameter_name = str(parameter.get("name", "")).strip()
                        if parameter_name:
                            path_params.append(parameter_name)
                            if bool(parameter.get("required")):
                                required_path_params.append(parameter_name)
            tags = operation.get("tags", [])
            tag = str(tags[0]).strip() if isinstance(tags, list) and tags else "default"
            matching_bindings = binding_index.get((str(method).upper(), str(path).strip()), [])
            spec_index[operation_id] = {
                "operationId": operation_id,
                "method": str(method).upper(),
                "path": str(path),
                "tag": tag,
                "purpose": str(operation.get("summary", "")).strip(),
                "requestExample": request_example,
                "requestRequiredFields": request_required_fields,
                "requestSchemaSource": request_schema_source,
                "responseExample": success_example,
                "failureCases": failure_cases,
                "successStatus": success_status,
                "pathParams": path_params,
                "requiredPathParams": required_path_params,
                "rbacPolicies": binding_rbac_policies(matching_bindings),
                "paginationRule": str(operation.get("x-pagination-rule", "")).strip(),
                "retryabilityPolicy": str(operation.get("x-retryability-policy", "")).strip(),
                "idempotencyRule": str(operation.get("x-idempotency-rule", "")).strip(),
            }
    return spec_index


def infer_default_tenant(operation_specs: dict[str, dict[str, Any]]) -> str:
    for spec in operation_specs.values():
        request_example = spec.get("requestExample", {})
        if isinstance(request_example, dict):
            tenant_id = str(request_example.get("tenant_id") or request_example.get("tenantId") or "").strip()
            if tenant_id:
                return normalize_default_tenant_id(tenant_id)
        response_example = spec.get("responseExample", {})
        if isinstance(response_example, dict):
            data = response_example.get("data", {})
            if isinstance(data, dict):
                tenant_id = str(data.get("tenant_id") or data.get("tenantId") or "").strip()
                if tenant_id:
                    return normalize_default_tenant_id(tenant_id)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        tenant_id = str(item.get("tenant_id") or item.get("tenantId") or "").strip()
                        if tenant_id:
                            return normalize_default_tenant_id(tenant_id)
    return "11111111-1111-1111-1111-111111111111"


def render_generated_runtime(operation_specs: dict[str, dict[str, Any]], default_tenant_id: str) -> str:
    template = load_generated_runtime_template()
    return (
        template.replace(
            "__OPERATION_SPECS__",
            json.dumps(operation_specs, ensure_ascii=False, indent=2, sort_keys=True),
        )
        .replace("__DEFAULT_TENANT_ID__", default_tenant_id)
    )
