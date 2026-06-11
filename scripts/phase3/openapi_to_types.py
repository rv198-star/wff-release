#!/usr/bin/env python3
"""
Generate shared TypeScript types from a JSON-compatible OpenAPI document.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from pathlib import Path

from phase3.contract_tools import load_openapi_document


def ts_type_from_schema(schema: dict[str, object], indent: int = 0) -> str:
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        rendered_types: list[str] = []
        for item in schema_type:
            item_type = str(item).strip()
            if not item_type:
                continue
            item_schema = dict(schema)
            item_schema["type"] = item_type
            rendered_type = ts_type_from_schema(item_schema, indent)
            if rendered_type not in rendered_types:
                rendered_types.append(rendered_type)
        return " | ".join(rendered_types) if rendered_types else "unknown"
    if schema_type == "object":
        properties = schema.get("properties", {})
        required = set(schema.get("required", [])) if isinstance(schema.get("required", []), list) else set()
        if not isinstance(properties, dict) or not properties:
            return "Record<string, unknown>"
        pad = " " * indent
        inner_pad = " " * (indent + 2)
        lines = ["{"]
        for key, subschema in properties.items():
            if not isinstance(subschema, dict):
                subtype = "unknown"
            else:
                subtype = ts_type_from_schema(subschema, indent + 2)
            optional = "" if key in required else "?"
            lines.append(f"{inner_pad}{key}{optional}: {subtype};")
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if schema_type == "array":
        items = schema.get("items", {})
        item_type = ts_type_from_schema(items if isinstance(items, dict) else {}, indent)
        return f"Array<{item_type}>"
    if schema_type in {"integer", "number"}:
        return "number"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "null":
        return "null"
    return "string" if schema_type == "string" else "unknown"


def render_declaration(name: str, schema: dict[str, object]) -> str:
    if schema.get("type") == "object":
        return f"export interface {name} {ts_type_from_schema(schema, 0)}"
    return f"export type {name} = {ts_type_from_schema(schema, 0)};"


def success_response_schema(operation: dict[str, object]) -> dict[str, object]:
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return {}
    success_code = next((code for code in sorted(responses) if str(code).startswith("2")), None)
    if success_code is None:
        return {}
    response = responses.get(success_code, {})
    if not isinstance(response, dict):
        return {}
    content = response.get("content", {})
    if not isinstance(content, dict):
        return {}
    app_json = content.get("application/json", {})
    if not isinstance(app_json, dict):
        return {}
    return app_json.get("schema", {}) if isinstance(app_json.get("schema", {}), dict) else {}


def request_body_schema(operation: dict[str, object]) -> dict[str, object]:
    request_body = operation.get("requestBody", {})
    if not isinstance(request_body, dict):
        return {}
    content = request_body.get("content", {})
    if not isinstance(content, dict):
        return {}
    app_json = content.get("application/json", {})
    if not isinstance(app_json, dict):
        return {}
    return app_json.get("schema", {}) if isinstance(app_json.get("schema", {}), dict) else {}


def parameters_schema(operation: dict[str, object], location: str) -> dict[str, object]:
    parameters = operation.get("parameters", [])
    if not isinstance(parameters, list):
        return {}
    properties: dict[str, object] = {}
    required: list[str] = []
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        if parameter.get("in") != location:
            continue
        name = str(parameter.get("name", "")).strip()
        if not name:
            continue
        schema = parameter.get("schema", {})
        properties[name] = schema if isinstance(schema, dict) else {}
        if parameter.get("required"):
            required.append(name)
    if not properties:
        return {}
    payload: dict[str, object] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        payload["required"] = required
    return payload


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def iter_operation_models(spec: dict[str, object]) -> list[dict[str, object]]:
    models: list[dict[str, object]] = []
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return models
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId", "")).strip() or "UnnamedOperation"
            path_schema = parameters_schema(operation, "path")
            query_schema = parameters_schema(operation, "query")
            body_schema = request_body_schema(operation)
            response_schema = success_response_schema(operation)
            models.append(
                {
                    "operation_id": operation_id,
                    "method": str(method).lower(),
                    "path": str(path),
                    "path_type_name": f"{operation_id}PathParams",
                    "query_type_name": f"{operation_id}QueryParams",
                    "body_type_name": f"{operation_id}RequestBody",
                    "input_type_name": f"{operation_id}Input",
                    "response_type_name": f"{operation_id}SuccessResponse",
                    "path_schema": path_schema,
                    "query_schema": query_schema,
                    "body_schema": body_schema,
                    "response_schema": response_schema,
                    "has_path": bool(path_schema),
                    "has_query": bool(query_schema),
                    "has_body": bool(body_schema),
                    "binding_sources": _string_list(operation.get("x-derived-from-compiled-bindings")),
                    "binding_modes": _string_list(operation.get("x-binding-mode")),
                    "rbac_policies": _string_list(operation.get("x-rbac-policies")),
                    "failure_semantics": _string_list(operation.get("x-failure-semantics")),
                }
            )
    return models


def build_types_document(spec: dict[str, object]) -> str:
    lines = [
        "// Generated by openapi_to_types.py",
        f'// Derived artifact authority: {str(spec.get("x-derived-authority", "openapi")).strip() or "openapi"}',
        "",
        "export interface ApiErrorEnvelope {",
        "  error_kind: string;",
        "  error_code: string;",
        "  retryability?: string;",
        "  [key: string]: unknown;",
        "}",
        "",
    ]
    for model in iter_operation_models(spec):
        if model["binding_sources"] or model["binding_modes"] or model["rbac_policies"] or model["failure_semantics"]:
            lines.append(
                "// Derived from compiled bindings: "
                + ", ".join(model["binding_sources"] or ["none"])
            )
            if model["binding_modes"]:
                lines.append("// Binding modes: " + ", ".join(model["binding_modes"]))
            if model["rbac_policies"]:
                lines.append("// RBAC policies: " + ", ".join(model["rbac_policies"]))
            if model["failure_semantics"]:
                lines.append("// Failure semantics: " + " | ".join(model["failure_semantics"]))
        if model["has_path"]:
            lines.append(render_declaration(str(model["path_type_name"]), dict(model["path_schema"])))
            lines.append("")
        if model["has_query"]:
            lines.append(render_declaration(str(model["query_type_name"]), dict(model["query_schema"])))
            lines.append("")
        if model["has_body"]:
            lines.append(render_declaration(str(model["body_type_name"]), dict(model["body_schema"])))
            lines.append("")

        input_parts = {}
        required = []
        if model["has_path"]:
            input_parts["pathParams"] = {"type": "object", "properties": {}, "$ref_name": str(model["path_type_name"])}
            required.append("pathParams")
        if model["has_query"]:
            input_parts["query"] = {"type": "object", "properties": {}, "$ref_name": str(model["query_type_name"])}
        if model["has_body"]:
            input_parts["body"] = {"type": "object", "properties": {}, "$ref_name": str(model["body_type_name"])}

        if input_parts:
            lines.append(f"export interface {model['input_type_name']} {{")
            for key in input_parts:
                required_marker = "" if key in required else "?"
                ref_name = input_parts[key]["$ref_name"]
                lines.append(f"  {key}{required_marker}: {ref_name};")
            lines.append("}")
            lines.append("")
        else:
            lines.append(f"export interface {model['input_type_name']} {{}}")
            lines.append("")

        lines.append(render_declaration(str(model["response_type_name"]), dict(model["response_schema"])))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate shared TypeScript types from OpenAPI")
    parser.add_argument("--openapi", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    spec = load_openapi_document(Path(args.openapi).resolve())
    document = build_types_document(spec)
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    print(json.dumps({"output": str(output_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
