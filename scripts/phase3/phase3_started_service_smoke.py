#!/usr/bin/env python3
"""
Run minimal real HTTP smoke checks against a Docker-started Phase-3 service.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import base64
import hashlib
import hmac
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from phase3.review_support import emit_gate_cli_result, write_json_report


HTTP_METHODS = ("post", "put", "patch", "delete", "get")
WRITE_METHODS = {"post", "put", "patch", "delete"}


def b64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def build_hs256_jwt(claims: dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            b64url(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")),
            b64url(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")),
        ]
    )
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{b64url(signature)}"


def load_openapi_spec(workspace_root: Path) -> dict[str, Any]:
    candidates = [
        workspace_root / "contracts" / "openapi.yaml",
        workspace_root / "openapi-final.yaml",
        workspace_root / "openapi.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def operation_request_body_example(operation: dict[str, Any]) -> dict[str, Any]:
    request_body = operation.get("requestBody", {})
    if not isinstance(request_body, dict):
        return {}
    content = request_body.get("content", {})
    if not isinstance(content, dict):
        return {}
    json_media = content.get("application/json", {})
    if not isinstance(json_media, dict):
        return {}
    example = json_media.get("example")
    if isinstance(example, dict):
        return dict(example)
    schema = json_media.get("schema", {})
    if not isinstance(schema, dict):
        return {}
    body: dict[str, Any] = {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(properties, dict) or not isinstance(required, list):
        return body
    for field in required:
        prop = properties.get(field, {})
        body[str(field)] = schema_example_value(str(field), prop if isinstance(prop, dict) else {})
    return body


def schema_example_value(field: str, schema: dict[str, Any]) -> Any:
    if "example" in schema:
        return schema["example"]
    value_type = str(schema.get("type", "string")).strip().lower()
    if value_type in {"integer", "number"}:
        return 1
    if value_type == "boolean":
        return True
    if value_type == "array":
        return []
    if value_type == "object":
        return {}
    return f"{field}-smoke"


def operation_parameters(operation: dict[str, Any]) -> list[dict[str, Any]]:
    params = operation.get("parameters", [])
    return [item for item in params if isinstance(item, dict)] if isinstance(params, list) else []


def parameter_example(parameter: dict[str, Any]) -> str:
    if "example" in parameter:
        return str(parameter["example"])
    schema = parameter.get("schema", {})
    if isinstance(schema, dict):
        return str(schema_example_value(str(parameter.get("name", "param")), schema))
    return f"{parameter.get('name', 'param')}-smoke"


def inject_path_parameters(path_template: str, operation: dict[str, Any]) -> str:
    resolved = path_template
    for parameter in operation_parameters(operation):
        if str(parameter.get("in", "")).lower() != "path":
            continue
        name = str(parameter.get("name", "")).strip()
        if not name:
            continue
        resolved = resolved.replace("{" + name + "}", urllib.parse.quote(parameter_example(parameter), safe=""))
    return resolved


def required_query_parameters(operation: dict[str, Any]) -> dict[str, str]:
    query: dict[str, str] = {}
    for parameter in operation_parameters(operation):
        if str(parameter.get("in", "")).lower() != "query" or not bool(parameter.get("required")):
            continue
        name = str(parameter.get("name", "")).strip()
        if name:
            query[name] = parameter_example(parameter)
    return query


def normalized_role_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_values = value
    else:
        raw_values = [value]
    roles: list[str] = []
    for raw in raw_values:
        role = str(raw or "").strip()
        if role and role not in roles:
            roles.append(role)
    return roles


def extract_operation_support_block(text: str, operation_id: str) -> str:
    marker = json.dumps(str(operation_id), ensure_ascii=False) + ":"
    start = text.find(marker)
    if start < 0:
        return ""
    brace_start = text.find("{", start + len(marker))
    if brace_start < 0:
        return ""
    depth = 0
    in_string = False
    escaped = False
    for index in range(brace_start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start : index + 1]
    return ""


def extract_rbac_policies_from_operation_support(workspace_root: Path, operation_id: str) -> list[str]:
    if not operation_id:
        return []
    support_path = workspace_root / "apps" / "api" / "src" / "common" / "operation-support.ts"
    if not support_path.exists():
        return []
    block = extract_operation_support_block(support_path.read_text(encoding="utf-8", errors="ignore"), operation_id)
    if not block:
        return []
    match = re.search(r'"rbacPolicies"\s*:\s*\[(.*?)\]', block, flags=re.DOTALL)
    if not match:
        return []
    return normalized_role_list(re.findall(r'"([^"]+)"', match.group(1)))


def operation_rbac_policies_from_workspace(workspace_root: Path, selected: dict[str, Any]) -> list[str]:
    operation = selected.get("operation", {})
    roles = []
    if isinstance(operation, dict):
        roles = normalized_role_list(operation.get("x-rbac-policies"))
    if roles:
        return roles
    return extract_rbac_policies_from_operation_support(workspace_root, str(selected.get("operation_id") or ""))


def select_smoke_operation(openapi_spec: dict[str, Any]) -> dict[str, Any]:
    paths = openapi_spec.get("paths", {})
    if not isinstance(paths, dict):
        return {}
    candidates: list[dict[str, Any]] = []
    for path_template, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            body = operation_request_body_example(operation)
            candidates.append(
                {
                    "operation_id": str(operation.get("operationId", f"{method.upper()} {path_template}")),
                    "operation": operation,
                    "method": method.upper(),
                    "path": str(path_template),
                    "resolved_path": inject_path_parameters(str(path_template), operation),
                    "query": required_query_parameters(operation),
                    "body": body,
                    "is_write": method in WRITE_METHODS,
                }
            )
    if not candidates:
        return {}
    return sorted(candidates, key=lambda item: (not bool(item["is_write"]), str(item["operation_id"])))[0]


def build_request_url(service_url: str, selected: dict[str, Any]) -> str:
    base = service_url.rstrip("/")
    path = str(selected.get("resolved_path") or selected.get("path") or "/")
    if not path.startswith("/"):
        path = f"/{path}"
    query = selected.get("query", {})
    suffix = f"?{urllib.parse.urlencode(query)}" if isinstance(query, dict) and query else ""
    return f"{base}{path}{suffix}"


def parse_response_body(raw: bytes) -> tuple[dict[str, Any], str]:
    text = raw.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = {}
    return payload if isinstance(payload, dict) else {}, text[:512]


def request_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any] | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    data = None
    request_headers = {"Accept": "application/json", **headers}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body_json, body_excerpt = parse_response_body(response.read(4096))
            status_code = int(response.status)
            return {"status_code": status_code, "body_json": body_json, "body_excerpt": body_excerpt, "ok": 200 <= status_code < 300}
    except urllib.error.HTTPError as exc:
        body_json, body_excerpt = parse_response_body(exc.read(4096))
        return {"status_code": int(exc.code), "body_json": body_json, "body_excerpt": body_excerpt, "ok": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive transport path
        return {"status_code": 0, "body_json": {}, "body_excerpt": "", "ok": False, "error": str(exc)}


def response_error_code(response: dict[str, Any]) -> str:
    body = response.get("body_json", {})
    if not isinstance(body, dict):
        return ""
    return str(body.get("error_code", "")).strip()


def safe_response(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "status_code": int(response.get("status_code", 0) or 0),
        "error_code": response_error_code(response),
        "ok": bool(response.get("ok")),
        "body_excerpt": str(response.get("body_excerpt", ""))[:512],
        **({"error": str(response.get("error"))} if response.get("error") else {}),
    }


def report_selected_operation(selected: dict[str, Any], rbac_policies: list[str]) -> dict[str, Any]:
    return {
        key: value
        for key, value in selected.items()
        if key in {"operation_id", "method", "path", "resolved_path", "query", "body", "is_write"}
    } | {"rbac_policies": rbac_policies}


def build_smoke_claims(*, role: str = "", roles: list[str] | None = None, suffix: str) -> dict[str, Any]:
    resolved_roles = normalized_role_list(roles if roles is not None else [role])
    return {
        "sub": f"phase3-smoke-{suffix}",
        "subject_id": f"phase3-smoke-{suffix}",
        "tenant_id": "tenant-001",
        "session_id": f"phase3-smoke-session-{suffix}",
        "roles": resolved_roles or ["authenticated"],
        "iat": int(time.time()),
    }


def report_exposes_bearer_token(report: dict[str, Any], tokens: list[str]) -> bool:
    serialized = json.dumps(report, ensure_ascii=False)
    return any(token and token in serialized for token in tokens)


def run_phase3_started_service_smoke(
    *,
    workspace_root: Path,
    service_url: str,
    auth_secret: str,
    output_path: Path | None = None,
    timeout_seconds: int = 10,
    request_fn: Callable[..., dict[str, Any]] = request_json,
) -> dict[str, Any]:
    workspace_root = workspace_root.resolve()
    failures: list[str] = []
    warnings: list[str] = []
    spec = load_openapi_spec(workspace_root)
    selected = select_smoke_operation(spec)
    requests: dict[str, Any] = {}

    if not selected:
        failures.append("openapi_smoke_operation_missing")
        report = {
            "workspace_root": str(workspace_root),
            "service_url": service_url,
            "overall_quality_gate": "fail",
            "verdict": "fail",
            "checks": {
                "openapi_operation_selected": False,
                "missing_bearer_passed": False,
                "invalid_bearer_passed": False,
                "forbidden_role_passed": False,
                "valid_bearer_passed": False,
                "raw_bearer_token_exposed": False,
            },
            "selected_operation": {},
            "requests": requests,
            "failures": failures,
            "warnings": warnings,
        }
        if output_path is not None:
            write_json_report(output_path.resolve(), report)
        return report

    url = build_request_url(service_url, selected)
    method = str(selected["method"])
    body = selected.get("body", {}) if method in {"POST", "PUT", "PATCH"} else None
    suffix = str(int(time.time()))
    valid_roles = operation_rbac_policies_from_workspace(workspace_root, selected) or ["authenticated"]
    forbidden_token = build_hs256_jwt(build_smoke_claims(role="phase3-forbidden-smoke-role", suffix=f"forbidden-{suffix}"), auth_secret)
    valid_token = build_hs256_jwt(build_smoke_claims(roles=valid_roles, suffix=f"valid-{suffix}"), auth_secret)

    missing_response = request_fn(method=method, url=url, headers={}, body=body, timeout_seconds=timeout_seconds)
    invalid_response = request_fn(
        method=method,
        url=url,
        headers={"Authorization": "Bearer definitely-invalid"},
        body=body,
        timeout_seconds=timeout_seconds,
    )
    forbidden_response = request_fn(
        method=method,
        url=url,
        headers={"Authorization": f"Bearer {forbidden_token}"},
        body=body,
        timeout_seconds=timeout_seconds,
    )
    valid_response = request_fn(
        method=method,
        url=url,
        headers={"Authorization": f"Bearer {valid_token}"},
        body=body,
        timeout_seconds=timeout_seconds,
    )

    requests["missing_bearer"] = safe_response(missing_response)
    requests["invalid_bearer"] = safe_response(invalid_response)
    requests["forbidden_role"] = safe_response(forbidden_response)
    requests["valid_bearer"] = safe_response(valid_response)

    missing_bearer_passed = int(missing_response.get("status_code", 0) or 0) == 401 and response_error_code(missing_response) == "missing_bearer_token"
    invalid_bearer_passed = int(invalid_response.get("status_code", 0) or 0) == 401 and response_error_code(invalid_response) == "invalid_auth_token"
    forbidden_role_passed = int(forbidden_response.get("status_code", 0) or 0) == 403 and response_error_code(forbidden_response) == "rbac_forbidden"
    valid_bearer_passed = 200 <= int(valid_response.get("status_code", 0) or 0) < 300

    if not missing_bearer_passed:
        failures.append("missing_bearer_smoke_failed")
    if not invalid_bearer_passed:
        failures.append("invalid_bearer_smoke_failed")
    if not forbidden_role_passed:
        failures.append("forbidden_role_smoke_failed")
    if not valid_bearer_passed:
        failures.append("valid_bearer_smoke_failed")

    report = {
        "workspace_root": str(workspace_root),
        "service_url": service_url,
        "overall_quality_gate": "pass" if not failures else "fail",
        "verdict": "pass" if not failures else "fail",
        "checks": {
            "openapi_operation_selected": True,
            "missing_bearer_passed": missing_bearer_passed,
            "invalid_bearer_passed": invalid_bearer_passed,
            "forbidden_role_passed": forbidden_role_passed,
            "valid_bearer_passed": valid_bearer_passed,
            "raw_bearer_token_exposed": False,
        },
        "selected_operation": report_selected_operation(selected, valid_roles),
        "requests": requests,
        "failures": failures,
        "warnings": warnings,
    }
    report["checks"]["raw_bearer_token_exposed"] = report_exposes_bearer_token(report, [forbidden_token, valid_token])
    if report["checks"]["raw_bearer_token_exposed"]:
        report["overall_quality_gate"] = "fail"
        report["verdict"] = "fail"
        report["failures"].append("raw_bearer_token_exposed")

    if output_path is not None:
        write_json_report(output_path.resolve(), report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run started-service API smoke checks for a Phase-3 workspace")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--service-url", required=True)
    parser.add_argument("--auth-secret", default="phase3-runtime-smoke-secret")
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=10)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_phase3_started_service_smoke(
        workspace_root=Path(args.workspace_root),
        service_url=args.service_url,
        auth_secret=args.auth_secret,
        output_path=Path(args.output),
        timeout_seconds=max(1, int(args.timeout_seconds)),
    )
    return emit_gate_cli_result(report, success_key="verdict")


if __name__ == "__main__":
    raise SystemExit(main())
