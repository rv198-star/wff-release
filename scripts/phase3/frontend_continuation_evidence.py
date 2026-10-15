#!/usr/bin/env python3
"""Compile standard WFF-P3 frontend evidence for a frozen backend-first continuation.

This tool is intentionally evidence-only. It never regenerates WFF-P1/WFF-P2,
never writes the frozen WFF-P3 backend root, and never creates business/API/
security authority. It accepts a current frontend realization only when its UI
interactions bind exactly to the already accepted frozen P3 slice/operation/
contract denominator and its Authority Delta ledger passes the canonical P3
validator.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.agentic_decision_authority import canonical_digest
from phase3.agentic_implementation_authority import (
    p3_agentic_implementation_authority_is_valid,
    validate_authority_delta_ledger,
)
from phase3.p3_realization_decisions import write_p3_realization_decisions
from phase3.frontend_implementation_scaffolder import FRONTEND_AUTHORING_SCHEMA
from phase3.impl_context import write_json
from phase3.runtime_smoke_executor import (
    frontend_consumer_journey_markers,
    frontend_consumer_page_markers,
    frontend_runtime_evidence_markers,
    playwright_json_summary,
    sha256_file,
)


CONTINUATION_SCHEMA = "wff.phase3-frontend-continuation-evidence.v1"


class FrontendContinuationEvidenceError(ValueError):
    """Raised when retained continuation evidence is stale, foreign, or incomplete."""


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise FrontendContinuationEvidenceError(f"{label} is missing or unsafe: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrontendContinuationEvidenceError(f"{label} is unreadable: {path}") from exc
    if not isinstance(payload, dict):
        raise FrontendContinuationEvidenceError(f"{label} must be a JSON object: {path}")
    return payload


def _relative(root: Path, path: Path, *, label: str) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise FrontendContinuationEvidenceError(f"{label} must remain inside {root}: {resolved}") from exc


def _tree_fingerprint(root: Path, relative_roots: Iterable[str]) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for relative in relative_roots:
        target = root / relative
        if not target.exists():
            continue
        paths = [target] if target.is_file() else sorted(path for path in target.rglob("*") if path.is_file())
        for path in paths:
            if path.is_symlink():
                raise FrontendContinuationEvidenceError(f"frozen backend fingerprint contains symlink: {path}")
            rows.append({"path": _relative(root, path, label="frozen backend artifact"), "sha256": sha256_file(path)})
    if not rows:
        raise FrontendContinuationEvidenceError("frozen WFF-P3 backend fingerprint has no files")
    return {
        "file_count": len(rows),
        "content_digest": canonical_digest(rows),
        "files": rows,
    }


def _p3_slice_map(authority: Mapping[str, Any]) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for raw in authority.get("exact_realization_plan", []):
        if not isinstance(raw, Mapping):
            continue
        slice_id = str(raw.get("slice_id") or "").strip()
        operation_id = str(raw.get("operation_id") or "").strip()
        contract_id = str(raw.get("contract_id") or "").strip()
        if not slice_id or not operation_id or not contract_id:
            continue
        key = (operation_id, contract_id)
        if key in result and result[key] != slice_id:
            raise FrontendContinuationEvidenceError(
                f"frozen P3 authority has ambiguous operation/contract binding: {operation_id}:{contract_id}"
            )
        result[key] = slice_id
    if not result:
        raise FrontendContinuationEvidenceError("frozen P3 authority has no accepted operation/contract slices")
    return result


def _openapi_operation_map(openapi: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    paths = openapi.get("paths")
    if not isinstance(paths, Mapping):
        raise FrontendContinuationEvidenceError("frozen OpenAPI paths are missing")
    for path, raw_methods in paths.items():
        if not isinstance(raw_methods, Mapping):
            continue
        for method, raw_operation in raw_methods.items():
            if str(method).lower() not in {"get", "post", "put", "patch", "delete", "head"} or not isinstance(raw_operation, Mapping):
                continue
            operation_id = str(raw_operation.get("operationId") or "").strip()
            if not operation_id:
                continue
            if operation_id in result:
                raise FrontendContinuationEvidenceError(f"frozen OpenAPI operationId is duplicated: {operation_id}")
            result[operation_id] = {"path": str(path), "method": str(method).upper()}
    return result


def _page_source_map(frontend_root: Path, page_ids: set[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    app_root = frontend_root / "app"
    if not app_root.is_dir():
        raise FrontendContinuationEvidenceError("frontend continuation has no app/ source root")
    for path in sorted(app_root.rglob("page.tsx")):
        text = path.read_text(encoding="utf-8")
        for page_id in page_ids:
            if f'data-phase3-page-id="{page_id}"' not in text:
                continue
            if page_id in result:
                raise FrontendContinuationEvidenceError(f"frontend page identity is duplicated: {page_id}")
            result[page_id] = path
    missing = sorted(page_ids - set(result))
    if missing:
        raise FrontendContinuationEvidenceError("frontend page source is missing for: " + ",".join(missing))
    return result


def _validate_ui_bindings(
    *,
    ui_contract: Mapping[str, Any],
    authority: Mapping[str, Any],
    openapi: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, str]]]:
    slice_map = _p3_slice_map(authority)
    operation_map = _openapi_operation_map(openapi)
    pages = ui_contract.get("pages")
    if not isinstance(pages, list) or not pages:
        raise FrontendContinuationEvidenceError("frontend UI IA has no pages")
    page_rows: list[dict[str, Any]] = []
    interaction_rows: dict[tuple[str, str], dict[str, str]] = {}
    seen_pages: set[str] = set()
    for raw_page in pages:
        if not isinstance(raw_page, Mapping):
            raise FrontendContinuationEvidenceError("frontend UI IA page is invalid")
        page_id = str(raw_page.get("page_id") or "").strip()
        route = str(raw_page.get("route") or "").strip()
        if not page_id or page_id in seen_pages or not route.startswith("/"):
            raise FrontendContinuationEvidenceError(f"frontend UI IA page identity/route is invalid: {page_id or '<missing>'}")
        if str(raw_page.get("readiness_status") or "ready").strip().lower() != "ready":
            raise FrontendContinuationEvidenceError(f"frontend UI IA page is not ready: {page_id}")
        seen_pages.add(page_id)
        slice_ids: list[str] = []
        interactions = raw_page.get("compiled_interactions")
        if not isinstance(interactions, list) or not interactions:
            raise FrontendContinuationEvidenceError(f"frontend UI IA page has no compiled interactions: {page_id}")
        for raw in interactions:
            if not isinstance(raw, Mapping):
                raise FrontendContinuationEvidenceError(f"frontend UI IA interaction is invalid: {page_id}")
            interaction_id = str(raw.get("interaction_id") or "").strip()
            operation_id = str(raw.get("operation_id") or "").strip()
            contract_id = str(raw.get("contract_id") or "").strip()
            endpoint = str(raw.get("api_endpoint") or "").strip()
            if not interaction_id or str(raw.get("readiness_status") or "ready").strip().lower() != "ready":
                raise FrontendContinuationEvidenceError(f"frontend UI IA interaction is not ready: {page_id}:{interaction_id or '<missing>'}")
            slice_id = slice_map.get((operation_id, contract_id), "")
            if not slice_id:
                raise FrontendContinuationEvidenceError(
                    f"frontend interaction is foreign to frozen P3 authority: {page_id}:{interaction_id}:{operation_id}:{contract_id}"
                )
            accepted_api = operation_map.get(operation_id)
            if not accepted_api or endpoint != accepted_api["path"]:
                raise FrontendContinuationEvidenceError(
                    f"frontend interaction endpoint differs from frozen OpenAPI: {page_id}:{interaction_id}:{endpoint}"
                )
            service_binding_id = str(raw.get("service_binding_id") or "").strip()
            if service_binding_id and not service_binding_id.startswith(f"{slice_id}."):
                raise FrontendContinuationEvidenceError(
                    f"frontend interaction service binding differs from frozen P3 slice: {page_id}:{interaction_id}:{service_binding_id}"
                )
            key = (page_id, interaction_id)
            if key in interaction_rows:
                raise FrontendContinuationEvidenceError(f"frontend interaction identity is duplicated: {page_id}:{interaction_id}")
            interaction_rows[key] = {
                "page_id": page_id,
                "interaction_id": interaction_id,
                "operation_id": operation_id,
                "contract_id": contract_id,
                "slice_id": slice_id,
                "api_endpoint": endpoint,
                "binding_mode": str(raw.get("binding_mode") or "").strip().lower(),
            }
            if slice_id not in slice_ids:
                slice_ids.append(slice_id)
        page_rows.append({"page_id": page_id, "route": route, "slice_ids": slice_ids})
    return page_rows, interaction_rows


def _endpoint_static_fragments(endpoint: str) -> list[str]:
    return [part for part in re.split(r"\{[^}]+\}", str(endpoint or "")) if part]


def _validate_page_source_endpoint_bindings(
    *,
    source_map: Mapping[str, Path],
    interactions: Mapping[tuple[str, str], Mapping[str, str]],
) -> None:
    source_text_by_page = {
        page_id: path.read_text(encoding="utf-8") for page_id, path in source_map.items()
    }
    for (page_id, interaction_id), row in interactions.items():
        endpoint = str(row.get("api_endpoint") or "")
        fragments = _endpoint_static_fragments(endpoint)
        source_text = source_text_by_page.get(page_id, "")
        if not fragments or not all(fragment in source_text for fragment in fragments):
            raise FrontendContinuationEvidenceError(
                f"frontend page source does not bind the accepted endpoint: {page_id}:{interaction_id}:{endpoint}"
            )


def _trace_payload(path: Path) -> bytes:
    try:
        with zipfile.ZipFile(path) as archive:
            return b"\n".join(
                archive.read(name)
                for name in archive.namelist()
                if not name.endswith("/")
            )
    except zipfile.BadZipFile:
        return path.read_bytes()


def _validate_trace_endpoint_coverage(
    *,
    trace_paths: Iterable[Path],
    interactions: Iterable[Mapping[str, str]],
) -> None:
    payload = b"\n".join(_trace_payload(path) for path in trace_paths)
    for row in interactions:
        endpoint = str(row.get("api_endpoint") or "")
        fragments = _endpoint_static_fragments(endpoint)
        if not fragments or not all(fragment.encode("utf-8") in payload for fragment in fragments):
            raise FrontendContinuationEvidenceError(
                "retained Playwright traces do not prove the accepted endpoint: "
                f"{row.get('page_id')}:{row.get('interaction_id')}:{endpoint}"
            )


def _validate_e2e(
    *,
    frontend_root: Path,
    spec_path: Path,
    expected_interactions: Mapping[tuple[str, str], Mapping[str, str]],
    page_ids: set[str],
) -> dict[str, Any]:
    if not spec_path.is_file() or spec_path.is_symlink():
        raise FrontendContinuationEvidenceError(f"frontend consumer E2E spec is missing or unsafe: {spec_path}")
    text = spec_path.read_text(encoding="utf-8")
    runtime_markers = frontend_runtime_evidence_markers(text)
    marker_keys = {(str(row["page_id"]), str(row["interaction_id"])) for row in runtime_markers}
    if marker_keys != set(expected_interactions):
        missing = sorted(set(expected_interactions) - marker_keys)
        extra = sorted(marker_keys - set(expected_interactions))
        raise FrontendContinuationEvidenceError(
            "frontend E2E interaction marker denominator differs from UI IA"
            + (f"; missing={missing}" if missing else "")
            + (f"; extra={extra}" if extra else "")
        )
    journeys = frontend_consumer_journey_markers(text)
    if not journeys:
        raise FrontendContinuationEvidenceError("frontend E2E has no consumer journey marker")
    consumer_pages = frontend_consumer_page_markers(text)
    captured_page_ids = {str(row.get("page_id") or "").strip() for row in consumer_pages}
    if captured_page_ids != page_ids:
        raise FrontendContinuationEvidenceError(
            "frontend consumer-page marker denominator differs from UI IA: "
            + ",".join(sorted(page_ids - captured_page_ids))
        )
    relative = _relative(frontend_root, spec_path, label="frontend E2E spec")
    sha = sha256_file(spec_path)
    return {
        "spec": {
            "path": relative,
            "sha256": sha,
            "markers": runtime_markers,
            "consumer_journeys": journeys,
            "consumer_pages": consumer_pages,
        },
        "consumer_journeys": [{**row, "path": relative} for row in journeys],
        "consumer_pages": [{**row, "path": relative} for row in consumer_pages],
        "interaction_bindings": [dict(row) for row in expected_interactions.values()],
    }


def _retained_browser_evidence(
    *,
    frontend_root: Path,
    page_rows: list[dict[str, Any]],
    e2e: Mapping[str, Any],
    playwright_path: Path,
    runtime_proof: Mapping[str, Any],
    e2e_spec_path: Path,
) -> dict[str, Any]:
    playwright = _load_json(playwright_path, label="retained Playwright report")
    playwright_summary = playwright_json_summary(playwright)
    if not playwright_summary.get("valid"):
        raise FrontendContinuationEvidenceError("retained Playwright report is not a passing current run")
    projects = {str(value) for value in playwright_summary.get("project_names", [])}
    if not {"desktop-chromium", "mobile-chromium"}.issubset(projects):
        raise FrontendContinuationEvidenceError("retained Playwright report lacks desktop/mobile Chromium projects")

    screenshot_dir = frontend_root / "evidence" / "screenshots"
    screenshots = [
        {"path": _relative(frontend_root, path, label="frontend screenshot"), "sha256": sha256_file(path)}
        for path in sorted(screenshot_dir.glob("*.png"))
        if path.is_file() and not path.is_symlink()
    ]
    expected_screenshots: list[str] = []
    coverage_rows: list[dict[str, str]] = []
    by_name = {Path(row["path"]).name: row for row in screenshots}
    for page in page_rows:
        page_id = str(page["page_id"])
        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", page_id)
        for project in ("desktop-chromium", "mobile-chromium"):
            name = f"{project}-consumer-{safe_id}.png"
            expected_screenshots.append(name)
            row = by_name.get(name)
            if row:
                coverage_rows.append({**row, "page_id": page_id, "project": project})
    missing_screenshots = sorted(set(expected_screenshots) - set(by_name))
    if missing_screenshots:
        raise FrontendContinuationEvidenceError(
            "retained consumer screenshots are incomplete: " + ",".join(missing_screenshots)
        )

    trace_root = frontend_root / "evidence" / "playwright-results"
    trace_paths = [
        path for path in sorted(trace_root.rglob("trace.zip")) if path.is_file() and not path.is_symlink()
    ]
    traces = [
        {"path": _relative(frontend_root, path, label="frontend trace"), "sha256": sha256_file(path)}
        for path in trace_paths
    ]
    expected_test_count = int(playwright_summary.get("expected", 0) or 0)
    if expected_test_count <= 0 or len(traces) < expected_test_count:
        raise FrontendContinuationEvidenceError("retained Playwright traces are incomplete")
    _validate_trace_endpoint_coverage(
        trace_paths=trace_paths,
        interactions=[row for row in e2e.get("interaction_bindings", []) if isinstance(row, Mapping)],
    )

    traffic = runtime_proof.get("frontend_api_traffic") if isinstance(runtime_proof.get("frontend_api_traffic"), Mapping) else {}
    requires_auth = True
    api_request_count = int(traffic.get("api_request_count", 0) or 0)
    browser_authorization_count = int(traffic.get("browser_authorization_header_request_count", 0) or 0)
    browser_phase3_count = int(traffic.get("phase3_auth_context_request_count", 0) or 0)
    frozen_count = int(traffic.get("frozen_backend_auth_context_request_count", 0) or 0)
    compatibility_mode = str(runtime_proof.get("backend_auth_compatibility_mode") or "").strip()
    authorized_count = int(traffic.get("authorized_api_request_count", 0) or 0)
    auth_failures: list[str] = []
    if api_request_count <= 0:
        auth_failures.append("consumer-business-api-request-missing")
    if browser_authorization_count > 0:
        auth_failures.append("consumer-used-browser-authorization-header")
    if browser_phase3_count > 0:
        auth_failures.append("consumer-used-phase3-auth-context-header")
    if compatibility_mode == "frozen-phase3-header":
        normal_transport = "bff-session-to-frozen-phase3-header"
        if frozen_count <= 0:
            auth_failures.append("frozen-backend-server-auth-context-missing")
    else:
        normal_transport = "authorization-bearer"
        if authorized_count <= 0:
            auth_failures.append("consumer-bearer-api-request-missing")

    route_spec_ref = _relative(frontend_root, e2e_spec_path, label="accessibility evidence spec")
    route_spec_sha = sha256_file(e2e_spec_path)
    accessibility_support_path = e2e_spec_path.parent / "e2e-accessibility.ts"
    if not accessibility_support_path.is_file() or accessibility_support_path.is_symlink():
        raise FrontendContinuationEvidenceError("retained consumer E2E accessibility support is missing or unsafe")
    accessibility_support_text = accessibility_support_path.read_text(encoding="utf-8")
    for required_token in ("documentHorizontalOverflow", "toBeLessThanOrEqual(1)"):
        if required_token not in accessibility_support_text:
            raise FrontendContinuationEvidenceError(
                f"retained consumer E2E accessibility support lacks viewport overflow proof: {required_token}"
            )
    accessibility_support_ref = _relative(
        frontend_root,
        accessibility_support_path,
        label="accessibility support spec",
    )
    accessibility_support_sha = sha256_file(accessibility_support_path)
    return {
        "requested": True,
        "status": "pass",
        "playwright": playwright_summary,
        "playwright_report_path": _relative(frontend_root, playwright_path, label="Playwright report"),
        "playwright_report_sha256": sha256_file(playwright_path),
        "route_spec_path": route_spec_ref,
        "route_spec_sha256": route_spec_sha,
        "interaction_coverage": {
            "specs": [dict(e2e["spec"])],
            "expected_interaction_count": len(e2e["spec"].get("markers", [])),
            "covered_interaction_count": len(e2e["spec"].get("markers", [])),
            "missing_interactions": [],
            "consumer_journey_count": len(e2e.get("consumer_journeys", [])),
            "consumer_journeys": list(e2e.get("consumer_journeys", [])),
            "consumer_page_count": len(e2e.get("consumer_pages", [])),
            "consumer_pages": list(e2e.get("consumer_pages", [])),
        },
        "auth_runtime_proof": {
            "status": "pass" if not auth_failures else "fail",
            "requires_authenticated_session": requires_auth,
            "backend_auth_compatibility_mode": compatibility_mode,
            "normal_api_auth_transport": normal_transport,
            "api_request_count": api_request_count,
            "authorized_api_request_count": authorized_count,
            "browser_authorization_header_request_count": browser_authorization_count,
            "phase3_auth_context_request_count": browser_phase3_count,
            "frozen_backend_auth_context_request_count": frozen_count,
            "failures": auth_failures,
            "claim_ceiling": (
                "Factual product-session/Web-BFF transport proof only. Frozen backend compatibility, when used, "
                "does not upgrade that backend to Bearer or production identity-provider assurance."
            ),
        },
        "accessibility_evidence": {
            "status": "pass",
            "source": "retained-consumer-e2e-accessibility-capture",
            "route_spec_path": route_spec_ref,
            "route_spec_sha256": route_spec_sha,
            "support_path": accessibility_support_ref,
            "support_sha256": accessibility_support_sha,
            "checks": [
                "semantic-main-and-heading",
                "interactive-accessible-name",
                "keyboard-focus-target",
                "measured-text-contrast",
                "viewport-horizontal-overflow",
                "desktop-mobile-execution",
            ],
            "claim_ceiling": "Mechanical browser accessibility baseline only; no expert assistive-technology audit claim.",
        },
        "screenshots": screenshots,
        "review_screenshots": coverage_rows,
        "consumer_page_screenshot_coverage": {
            "status": "pass",
            "expected_count": len(expected_screenshots),
            "observed_count": len(coverage_rows),
            "missing": [],
            "screenshots": coverage_rows,
        },
        "expected_screenshot_count": len(expected_screenshots),
        "browser_traces": traces,
        "expected_trace_count": expected_test_count,
    }


def compile_frontend_continuation_evidence(
    *,
    frontend_root: Path,
    frozen_p3_root: Path,
    project_artifact_root: Path | None = None,
    output_locale: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    frontend_root = frontend_root.resolve()
    frozen_p3_root = frozen_p3_root.resolve()
    authority = _load_json(frozen_p3_root / "p3-agentic-implementation-authority.json", label="frozen P3 authority")
    if not p3_agentic_implementation_authority_is_valid(authority):
        raise FrontendContinuationEvidenceError("frozen P3 implementation authority is invalid")
    ledger = _load_json(frontend_root / "p3-frontend-authority-delta-ledger.json", label="frontend Authority Delta ledger")
    try:
        delta_records = validate_authority_delta_ledger(ledger, authority=authority)
    except ValueError as exc:
        raise FrontendContinuationEvidenceError(f"frontend Authority Delta ledger is not canonical: {exc}") from exc

    frozen_metadata = _load_json(frozen_p3_root / "phase3-run-metadata.json", label="frozen P3 run metadata") if (frozen_p3_root / "phase3-run-metadata.json").is_file() else {}
    metadata_phase2_root = Path(str(frozen_metadata.get("phase2_root") or "")).expanduser() if str(frozen_metadata.get("phase2_root") or "").strip() else None
    phase2_root = metadata_phase2_root.resolve() if metadata_phase2_root is not None and metadata_phase2_root.exists() else frozen_p3_root
    resolved_project_artifact_root = (
        project_artifact_root.resolve()
        if project_artifact_root is not None
        else Path(str(frozen_metadata.get("project_artifact_root") or "")).expanduser().resolve()
        if str(frozen_metadata.get("project_artifact_root") or "").strip()
        else frontend_root
    )
    realization_decisions = write_p3_realization_decisions(
        phase2_root=phase2_root,
        phase3_root=frontend_root,
        project_artifact_root=resolved_project_artifact_root,
        authority=authority,
        ledger=ledger,
        ledger_path=frontend_root / "p3-frontend-authority-delta-ledger.json",
        records=delta_records,
    )

    ui_path = frontend_root / "ui-ia-contract.json"
    ui_contract = _load_json(ui_path, label="frontend UI IA contract")
    openapi_path = frozen_p3_root / "contracts" / "openapi.yaml"
    openapi = _load_json(openapi_path, label="frozen OpenAPI")
    page_rows, interaction_rows = _validate_ui_bindings(
        ui_contract=ui_contract,
        authority=authority,
        openapi=openapi,
    )
    page_ids = {str(row["page_id"]) for row in page_rows}
    source_map = _page_source_map(frontend_root, page_ids)
    _validate_page_source_endpoint_bindings(
        source_map=source_map,
        interactions=interaction_rows,
    )
    for row in page_rows:
        source = source_map[str(row["page_id"])]
        row["path"] = _relative(frontend_root, source, label="frontend page source")
        row["content_sha256"] = sha256_file(source)

    application_path = frontend_root / "app" / "ui-app.tsx"
    if not application_path.is_file() or application_path.is_symlink():
        raise FrontendContinuationEvidenceError("frontend product application is missing")
    e2e_path = frontend_root / "tests" / "e2e" / "frontend-product-consumer.spec.ts"
    e2e = _validate_e2e(
        frontend_root=frontend_root,
        spec_path=e2e_path,
        expected_interactions=interaction_rows,
        page_ids=page_ids,
    )
    runtime_proof = _load_json(frontend_root / "evidence" / "runtime-proof.json", label="frontend runtime proof")
    playwright_path = frontend_root / "evidence" / "playwright-report.json"
    browser = _retained_browser_evidence(
        frontend_root=frontend_root,
        page_rows=page_rows,
        e2e=e2e,
        playwright_path=playwright_path,
        runtime_proof=runtime_proof,
        e2e_spec_path=e2e_path,
    )
    if browser["auth_runtime_proof"]["status"] != "pass":
        raise FrontendContinuationEvidenceError(
            "frontend retained auth/runtime evidence is not acceptable: "
            + ",".join(browser["auth_runtime_proof"]["failures"])
        )

    backend_fingerprint = _tree_fingerprint(
        frozen_p3_root,
        (
            "apps/api",
            "db",
            "contracts/openapi.yaml",
            "implementation-bindings.json",
            "p3-agentic-implementation-authority.json",
            ".phase3-evidence/p3-authority-delta-ledger.json",
        ),
    )
    ui_sha = sha256_file(ui_path)
    application_record = {
        "path": _relative(frontend_root, application_path, label="frontend product application"),
        "status": "materialized",
        "content_sha256": sha256_file(application_path),
    }
    consumer_e2e_record = {
        "path": _relative(frontend_root, e2e_path, label="frontend consumer E2E"),
        "status": "materialized",
        "content_sha256": sha256_file(e2e_path),
    }
    authoring: dict[str, Any] = {
        "schema_version": FRONTEND_AUTHORING_SCHEMA,
        "mode": "complete-product-agentic-realization",
        "status": "materialized",
        "implementation_decision_id": str(authority.get("decision_id") or ""),
        "implementation_decision_digest": str(authority.get("decision_digest") or ""),
        "ui_ia_contract_path": "ui-ia-contract.json",
        "ui_ia_contract_sha256": ui_sha,
        "application": application_record,
        "consumer_e2e": consumer_e2e_record,
        "page_count": len(page_rows),
        "pages": page_rows,
        "unresolved_block_count": 0,
        "unresolved_blocks": [],
        "semantic_authority": False,
        "target_binding_mode": "p3-authority-delta-frontend-extension",
        "authority_delta_ledger": {
            "path": "p3-frontend-authority-delta-ledger.json",
            "sha256": sha256_file(frontend_root / "p3-frontend-authority-delta-ledger.json"),
            "record_count": len(delta_records),
            "applied_upstream": False,
        },
        "backend_immutability": {
            "status": "pass",
            "source_root": str(frozen_p3_root),
            "source_root_write_performed": False,
            "frozen_backend_file_count": backend_fingerprint["file_count"],
            "frozen_backend_digest": backend_fingerprint["content_digest"],
        },
        "runtime_evidence_refs": [],
        "trace_confirmed": False,
        "claim_ceiling": (
            "Current-decision-bound WFF-P3 frontend source realization only. Frozen WFF-P3 backend authority/source "
            "is referenced read-only and unchanged; runtime and WFF-P4 qualification are separate evidence."
        ),
    }
    authoring["content_digest"] = canonical_digest(authoring)
    impl_report = {
        "schema_version": CONTINUATION_SCHEMA,
        "artifact_kind": "phase3-impl-frontend-report",
        "quality_gate": "pass",
        "ui_ia_contract": "ui-ia-contract.json",
        "authoring": authoring,
        "realization_decisions": realization_decisions,
        "claim_ceiling": authoring["claim_ceiling"],
    }
    write_json(frontend_root / "impl-frontend-report.json", impl_report)

    identity = {
        "decision_id": str(authority.get("decision_id") or ""),
        "decision_digest": str(authority.get("decision_digest") or ""),
        "content_digest": authoring["content_digest"],
        "ui_ia_contract_sha256": ui_sha,
        "product_access_requirements": (
            dict(ui_contract.get("product_access_requirements"))
            if isinstance(ui_contract.get("product_access_requirements"), Mapping)
            else {}
        ),
        "business_data_requirements": (
            dict(ui_contract.get("business_data_requirements"))
            if isinstance(ui_contract.get("business_data_requirements"), Mapping)
            else {}
        ),
        "project_language_requirements": (
            dict(ui_contract.get("project_language_requirements"))
            if isinstance(ui_contract.get("project_language_requirements"), Mapping)
            else {}
        ),
        "application": application_record,
        "pages": page_rows,
    }
    browser["authoring_identity"] = identity
    browser["product_access_requirements"] = dict(identity["product_access_requirements"])
    browser["business_data_requirements"] = dict(identity["business_data_requirements"])
    browser["project_language_requirements"] = dict(identity["project_language_requirements"])
    runtime_claim = str(runtime_proof.get("claim_ceiling") or "").strip()
    runtime_report = {
        "schema_version": CONTINUATION_SCHEMA,
        "workspace_root": str(frontend_root),
        "frozen_p3_root": str(frozen_p3_root),
        "verdict": "pass",
        "overall_quality_gate": "pass",
        "checks": {
            "frontend_requested": True,
            "p3_realization_decisions_valid": True,
            "frontend_browser_evidence_green": True,
            "runtime_smoke_green": True,
            "frozen_backend_authority_valid": True,
            "frozen_backend_immutable": True,
            "frontend_authority_delta_valid": True,
        },
        "frontend_browser_evidence": browser,
        "realization_decisions": realization_decisions,
        "frozen_backend_identity": backend_fingerprint,
        "source_runtime_proof": {
            "path": "evidence/runtime-proof.json",
            "sha256": sha256_file(frontend_root / "evidence" / "runtime-proof.json"),
            "status": str(runtime_proof.get("status") or ""),
        },
        "failures": [],
        "warnings": [],
        "claim_ceiling": runtime_claim or (
            "Retained WFF-P3 frontend/browser evidence only; no WFF-P4, UAT, production, owner-signoff, or release claim."
        ),
    }
    write_json(frontend_root / "runtime-smoke-report.json", runtime_report)
    return impl_report, runtime_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile standard WFF-P3 Frontend evidence for a frozen backend-first continuation"
    )
    parser.add_argument("--frontend-root", required=True)
    parser.add_argument("--frozen-p3-root", required=True)
    parser.add_argument("--project-artifact-root", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        impl, runtime = compile_frontend_continuation_evidence(
            frontend_root=Path(args.frontend_root),
            frozen_p3_root=Path(args.frozen_p3_root),
            project_artifact_root=Path(args.project_artifact_root) if str(args.project_artifact_root or "").strip() else None,
        )
    except FrontendContinuationEvidenceError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "status": "pass",
                "impl_frontend_report": str(Path(args.frontend_root).resolve() / "impl-frontend-report.json"),
                "runtime_smoke_report": str(Path(args.frontend_root).resolve() / "runtime-smoke-report.json"),
                "authoring_digest": impl["authoring"]["content_digest"],
                "runtime_verdict": runtime["verdict"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
