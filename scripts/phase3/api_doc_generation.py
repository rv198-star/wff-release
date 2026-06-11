#!/usr/bin/env python3
"""
Generate final API documentation assets for a Phase-3 run.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from html import escape
from string import Template
from pathlib import Path
from typing import Any

from phase3.openapi_diff_checker import compare_openapi_docs
from common.output_language import localize_phase3_api_doc_consistency_report, resolve_output_locale
from common.script_data_assets import load_script_text_asset
from phase3.contract_tools import load_openapi_document
from phase3.surface_policy import write_phase3_profiled_surface

WFF_SCRIPT_DATA_ASSETS = ("scripts/phase3/data/api-doc-index.html.template",)
API_DOC_INDEX_TEMPLATE = Template(load_script_text_asset(__file__, "api-doc-index.html.template"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def iter_operations(document: dict[str, object]) -> list[dict[str, object]]:
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        return []
    operations: list[dict[str, object]] = []
    for raw_path, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        for method, operation in sorted(path_item.items()):
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            operations.append(
                {
                    "path": str(raw_path),
                    "method": str(method).upper(),
                    "operation_id": str(operation.get("operationId", "")).strip(),
                    "summary": str(operation.get("summary", "")).strip(),
                    "response_codes": sorted(str(code) for code in responses.keys()) if isinstance(responses, dict) else [],
                }
            )
    return operations


def doc_runtime_document(document: dict[str, object]) -> dict[str, object]:
    runtime_document = json.loads(json.dumps(document, ensure_ascii=False))
    if not isinstance(runtime_document, dict):
        return {}
    servers = runtime_document.get("servers")
    if not isinstance(servers, list) or not servers:
        runtime_document["servers"] = [{"url": "/"}]
    return runtime_document


OPENAPI_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def auth_error_schema() -> dict[str, object]:
    return {
        "type": "object",
        "required": ["error_kind", "error_code", "retryability"],
        "additionalProperties": True,
        "properties": {
            "error_kind": {"type": "string"},
            "error_code": {"type": "string"},
            "retryability": {"type": "string"},
            "message": {"type": "string"},
        },
    }


def auth_error_example(error_code: str) -> dict[str, str]:
    return {
        "error_kind": "auth_error",
        "error_code": error_code,
        "retryability": "caller_after_fix",
    }


def forbidden_error_example() -> dict[str, str]:
    return {
        "error_kind": "business_error",
        "error_code": "rbac_forbidden",
        "retryability": "never",
    }


def ensure_openapi_bearer_auth(document: dict[str, object]) -> dict[str, object]:
    secured = json.loads(json.dumps(document, ensure_ascii=False))
    if not isinstance(secured, dict):
        return {}
    components = secured.setdefault("components", {})
    if not isinstance(components, dict):
        components = {}
        secured["components"] = components
    security_schemes = components.setdefault("securitySchemes", {})
    if not isinstance(security_schemes, dict):
        security_schemes = {}
        components["securitySchemes"] = security_schemes
    security_schemes.setdefault(
        "BearerAuth",
        {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
    )

    paths = secured.get("paths", {})
    if not isinstance(paths, dict):
        return secured
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if str(method).lower() not in OPENAPI_HTTP_METHODS or not isinstance(operation, dict):
                continue
            if operation.get("x-auth-required") is False:
                continue
            operation.setdefault("security", [{"BearerAuth": []}])
            responses = operation.setdefault("responses", {})
            if not isinstance(responses, dict):
                responses = {}
                operation["responses"] = responses
            responses.setdefault(
                "401",
                {
                    "description": "Authentication failed",
                    "content": {
                        "application/json": {
                            "schema": auth_error_schema(),
                            "examples": {
                                "missing_bearer_token": {"value": auth_error_example("missing_bearer_token")},
                                "invalid_auth_token": {"value": auth_error_example("invalid_auth_token")},
                            },
                        }
                    },
                },
            )
            responses.setdefault(
                "403",
                {
                    "description": "Authorization failed",
                    "content": {
                        "application/json": {
                            "schema": auth_error_schema(),
                            "example": forbidden_error_example(),
                        }
                    },
                },
            )
    return secured


def normalize_api_evidence_links(evidence_links: list[dict[str, object]] | None) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in evidence_links or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "method": str(item.get("method", "")).strip().upper(),
                "path": str(item.get("path", "")).strip(),
                "p1_scenario": str(item.get("p1_scenario", "")).strip(),
                "p2_contract": str(item.get("p2_contract", "")).strip(),
                "test_evidence": str(item.get("test_evidence", "")).strip(),
                "evidence_level": str(item.get("evidence_level", "")).strip(),
                "infra_proof": str(item.get("infra_proof", "")).strip(),
                "review_bound": str(item.get("review_bound", "")).strip(),
            }
        )
    return normalized


def api_evidence_linkage_truth(evidence_links: list[dict[str, str]]) -> bool:
    if not evidence_links:
        return False
    required_fields = ("method", "path", "p1_scenario", "p2_contract", "test_evidence", "evidence_level")
    return all(all(row.get(field) for field in required_fields) for row in evidence_links)


def build_api_evidence_rows(evidence_links: list[dict[str, str]]) -> list[str]:
    rows: list[str] = []
    for item in evidence_links:
        rows.append(
            "<tr>"
            f"<td><code>{escape(item['method'])} {escape(item['path'])}</code></td>"
            f"<td>{escape(item['p1_scenario'] or '-')}</td>"
            f"<td>{escape(item['p2_contract'] or '-')}</td>"
            f"<td><code>{escape(item['test_evidence'] or '-')}</code></td>"
            f"<td>{escape(item['evidence_level'] or '-')}</td>"
            f"<td>{escape(item['infra_proof'] or '-')}</td>"
            f"<td>{escape(item['review_bound'] or '-')}</td>"
            "</tr>"
        )
    return rows


def build_doc_index_html(
    *,
    title: str,
    document: dict[str, object],
    diff_report: dict[str, object],
    output_locale: str | None = None,
    evidence_links: list[dict[str, str]] | None = None,
) -> str:
    rows = []
    for operation in iter_operations(document):
        rows.append(
            "<tr>"
            f"<td><code>{escape(str(operation['method']))}</code></td>"
            f"<td><code>{escape(str(operation['path']))}</code></td>"
            f"<td>{escape(str(operation['operation_id']) or '-')}</td>"
            f"<td>{escape(', '.join(str(code) for code in operation['response_codes']) or '-')}</td>"
            "</tr>"
        )
    diff_status = str(diff_report.get("verdict", "unknown")).upper()
    zh = resolve_output_locale(output_locale) == "zh-CN"
    lang = "zh-CN" if zh else "en"
    verdict_label = "OpenAPI 差异结论" if zh else "OpenAPI diff verdict"
    operations_label = "接口操作" if zh else "Operations"
    interactive_label = "交互式调试文档" if zh else "Interactive API explorer"
    raw_spec_label = "原始 OpenAPI JSON" if zh else "Raw OpenAPI JSON"
    redoc_label = "ReDoc 只读文档" if zh else "ReDoc reference"
    summary_label = "文档标准" if zh else "Doc standard"
    summary_value = "FastAPI 风格 Swagger /docs + ReDoc" if zh else "FastAPI-style Swagger /docs + ReDoc"
    evidence_title = "Evidence-linked API surface"
    evidence_rows = build_api_evidence_rows(evidence_links or [])
    evidence_empty = "No linked runtime evidence supplied yet."
    evidence_section = [
        '    <section class="panel">',
        f"      <h2>{escape(evidence_title)}</h2>",
    ]
    if evidence_rows:
        evidence_section.extend(
            [
                "      <table>",
                "        <thead><tr><th>API</th><th>P1 scenario</th><th>P2 contract</th><th>Test evidence</th><th>Evidence level</th><th>Infra proof</th><th>Review-bound</th></tr></thead>",
                "        <tbody>",
                *[f"          {row}" for row in evidence_rows],
                "        </tbody>",
                "      </table>",
            ]
        )
    else:
        evidence_section.append(f"      <p>{escape(evidence_empty)}</p>")
    evidence_section.append("    </section>")
    operations_rows = "\n".join(f"          {row}" for row in rows)
    if operations_rows:
        operations_rows += "\n"
    evidence_section_text = "\n".join(evidence_section)
    return API_DOC_INDEX_TEMPLATE.substitute(
        lang=escape(lang),
        title=escape(title),
        verdict_label=escape(verdict_label),
        operations_label=escape(operations_label),
        interactive_label=escape(interactive_label),
        raw_spec_label=escape(raw_spec_label),
        redoc_label=escape(redoc_label),
        summary_label=escape(summary_label),
        summary_value=escape(summary_value),
        diff_status=escape(diff_status),
        diff_status_class=escape(str(diff_report.get("verdict", "unknown")).lower()),
        operations_count=str(len(rows)),
        operations_rows=operations_rows,
        evidence_section=evidence_section_text,
    )


def build_redoc_html(
    *,
    title: str,
    diff_report: dict[str, object],
    output_locale: str | None = None,
) -> str:
    diff_status = str(diff_report.get("verdict", "unknown")).upper()
    zh = resolve_output_locale(output_locale) == "zh-CN"
    lang = "zh-CN" if zh else "en"
    verdict_label = "OpenAPI 差异结论" if zh else "OpenAPI diff verdict"
    back_label = "返回 Swagger /docs" if zh else "Back to Swagger /docs"
    subtitle = "ReDoc 只读参考" if zh else "ReDoc reference view"
    return "\n".join(
        [
            "<!doctype html>",
            f"<html lang=\"{lang}\">",
            "<head>",
            "  <meta charset=\"utf-8\">",
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            f"  <title>{escape(title)} · ReDoc</title>",
            "  <style>",
            "    body { margin: 0; font-family: ui-sans-serif, system-ui, sans-serif; background: #f3f6fb; }",
            "    .top { display: flex; flex-wrap: wrap; gap: 12px; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #d8e0e8; background: #fff; }",
            "    .top a { text-decoration: none; color: #0f5bd8; font-weight: 600; }",
            "    .status { color: #516071; }",
            "  </style>",
            "</head>",
            "<body>",
            '  <div class="top">',
            f"    <div><strong>{escape(title)}</strong><div class=\"status\">{escape(subtitle)} · {escape(verdict_label)}: {escape(diff_status)}</div></div>",
            f'    <a href="./index.html">{escape(back_label)}</a>',
            "  </div>",
            '  <redoc spec-url="./openapi.json"></redoc>',
            '  <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>',
            "</body>",
            "</html>",
            "",
        ]
    )


def build_diff_markdown(diff_report: dict[str, object], output_locale: str | None = None) -> str:
    removed = [str(item) for item in diff_report.get("removed_operations", [])]
    added = [str(item) for item in diff_report.get("added_operations", [])]
    changed = diff_report.get("changed_status_codes", [])
    requires_adr_escalation = str(diff_report.get("verdict", "unknown")).lower() == "fail"
    lines = [
        "# API Doc Consistency Report",
        "",
        f"- verdict: {diff_report.get('verdict', 'unknown')}",
        f"- requires_adr_escalation: {'true' if requires_adr_escalation else 'false'}",
        "",
        "## Removed Operations",
        *(["- none"] if not removed else [f"- {item}" for item in removed]),
        "",
        "## Added Operations",
        *(["- none"] if not added else [f"- {item}" for item in added]),
        "",
        "## Changed Status Codes",
    ]
    if not changed:
        lines.append("- none")
    else:
        for row in changed:
            if not isinstance(row, dict):
                continue
            lines.append(
                f"- {row.get('operation', 'unknown')}: missing={','.join(row.get('missing_status_codes', [])) or 'none'} "
                f"added={','.join(row.get('added_status_codes', [])) or 'none'}"
            )
    lines.extend(
        [
            "",
            "## Publication Decision",
            (
                "- Block publication until the frozen contract is updated or an ADR explicitly approves the incompatible drift."
                if requires_adr_escalation
                else "- Publishable against the frozen contract baseline."
            ),
            "",
        ]
    )
    return localize_phase3_api_doc_consistency_report("\n".join(lines), output_locale)


def generate_phase3_api_docs(
    *,
    baseline_openapi: dict[str, object],
    output_dir: Path,
    title: str = "Phase-3 API Documentation",
    candidate_openapi: dict[str, object] | None = None,
    output_locale: str | None = None,
    evidence_links: list[dict[str, object]] | None = None,
) -> dict[str, Any]:
    final_document = ensure_openapi_bearer_auth(candidate_openapi or baseline_openapi)
    diff_report = compare_openapi_docs(baseline_openapi, final_document)
    resolved_title = title
    if resolve_output_locale(output_locale) == "zh-CN":
        resolved_title = title.replace("API Documentation", "API 文档")
    runtime_document = doc_runtime_document(final_document)
    normalized_evidence_links = normalize_api_evidence_links(evidence_links)

    openapi_final_path = output_dir / "openapi-final.yaml"
    api_doc_dir = output_dir / "docs" / "api"
    api_doc_index_path = api_doc_dir / "index.html"
    api_doc_redoc_path = api_doc_dir / "redoc.html"
    api_doc_json_path = api_doc_dir / "openapi.json"
    diff_json_path = output_dir / "openapi-diff.json"
    diff_md_path = write_phase3_profiled_surface(
        output_dir,
        "api-doc-consistency-report.md",
        build_diff_markdown(diff_report, output_locale),
    )

    write_text(openapi_final_path, json.dumps(final_document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(api_doc_json_path, json.dumps(runtime_document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(diff_json_path, json.dumps(diff_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(
        api_doc_index_path,
        build_doc_index_html(
            title=resolved_title,
            document=runtime_document,
            diff_report=diff_report,
            output_locale=output_locale,
            evidence_links=normalized_evidence_links,
        ),
    )
    write_text(
        api_doc_redoc_path,
        build_redoc_html(
            title=resolved_title,
            diff_report=diff_report,
            output_locale=output_locale,
        ),
    )

    return {
        "openapi_final_path": str(openapi_final_path),
        "api_doc_dir": str(api_doc_dir),
        "api_doc_index_path": str(api_doc_index_path),
        "api_doc_redoc_path": str(api_doc_redoc_path),
        "openapi_diff_report_path": str(diff_json_path),
        "openapi_diff_markdown_path": str(diff_md_path),
        "operation_count": len(iter_operations(final_document)),
        "api_evidence_linkage_count": len(normalized_evidence_links),
        "api_evidence_linkage_truth": api_evidence_linkage_truth(normalized_evidence_links),
        "diff_verdict": diff_report["verdict"],
        "requires_adr_escalation": str(diff_report.get("verdict", "unknown")).lower() == "fail",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate final OpenAPI and API doc assets")
    parser.add_argument("--baseline-openapi", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--title", default="Phase-3 API Documentation")
    parser.add_argument("--candidate-openapi")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = generate_phase3_api_docs(
        baseline_openapi=load_openapi_document(Path(args.baseline_openapi).resolve()),
        candidate_openapi=load_openapi_document(Path(args.candidate_openapi).resolve()) if args.candidate_openapi else None,
        output_dir=Path(args.output_dir).resolve(),
        title=args.title,
        output_locale=args.output_locale,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
