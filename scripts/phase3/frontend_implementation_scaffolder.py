from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from common.agentic_decision_authority import canonical_digest
from phase3.agentic_implementation_authority import (
    p3_frontend_agentic_body_contract_is_compatible,
    p3_agentic_implementation_authority_is_valid,
)
from phase3.frontend_route_segments import frontend_route_file_segment, sanitize_route_segment
from phase3.impl_context import load_phase2_source_texts, write_json
from phase3.impl_contract_pack import materialize_contract_pack
from phase3.implementation_binding_tools import AGENTIC_BODY_SENTINEL, agentic_shell_projection, frontend_surface_unit_test_path, merge_bounded_agentic_regions, render_agentic_region
from phase3.project_scaffold_parts import scaffold_frozen_backend_frontend_runtime_overlay, scaffold_root_workspace, scaffold_shared_packages, scaffold_web_app


FRONTEND_AUTHORING_SCHEMA = "wff.phase3-frontend-product-authoring.v3"
PREVIOUS_FRONTEND_AUTHORING_SCHEMA = "wff.phase3-frontend-product-authoring.v2"
FRONTEND_APPLICATION_TARGET = "apps/web/app/ui-app.tsx"
FRONTEND_E2E_TARGET = "tests/e2e/frontend-product-consumer.spec.ts"

OPERATING_PRODUCT_MATURITY_QUESTIONS = {
    "meaningfulOutcomeClosure": (
        "What user-consumable business result closes the primary task, and can the user understand that result and the next useful action "
        "without treating route access, persistence, reload/re-entry, or an opaque identifier as the outcome?"
    ),
    "decisionContextSufficiency": (
        "Does each record, choice, result, or queue expose enough accepted role-appropriate business context for the user to choose, prioritize, "
        "review, or continue work confidently, rather than merely recognizing that a record exists?"
    ),
    "operatingScaleJudgment": (
        "Under the normal repeated-use frequency and plausible working-set size for this product, is the interaction still efficient, and are search, "
        "filtering, sorting, grouping, recency, prioritization, or bulk behavior justified by the task rather than by a fixed widget rule?"
    ),
    "longitudinalContinuity": (
        "When work spans time or prior records, can a returning user understand current state, relevant history/change or provenance, and the next action "
        "without reconstructing context from technical identifiers or memory?"
    ),
}


class FrontendImplementationAuthoringError(ValueError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(encoded)


_BACKEND_FREEZE_ROOTS = (
    "apps/api",
    "tests/contracts",
    "tests/scenarios",
    "tests/replays",
    "tests/sql",
    "tests/support",
    "tests/unit/api",
)


def _backend_freeze_fingerprint(output_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for relative_root in _BACKEND_FREEZE_ROOTS:
        root = output_dir / relative_root
        if not root.exists():
            continue
        if root.is_symlink():
            raise FrontendImplementationAuthoringError(
                f"frontend-only authoring refuses symlinked frozen backend root: {relative_root}"
            )
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue
            relative = path.relative_to(output_dir).as_posix()
            if path.is_symlink() or not path.is_file():
                raise FrontendImplementationAuthoringError(
                    f"frontend-only authoring refuses unsafe frozen backend path: {relative}"
                )
            rows.append({"path": relative, "sha256": _file_sha256(path)})
    return {
        "status": "frozen" if rows else "not-present",
        "file_count": len(rows),
        "content_digest": _json_sha256(rows),
        "files": rows,
    }


def _authority_has_materialized_backend_targets(authority: Mapping[str, Any] | None, output_dir: Path) -> bool:
    if not isinstance(authority, Mapping):
        return False
    targets: list[str] = []
    for row in authority.get("exact_realization_plan", []):
        if not isinstance(row, Mapping) or str(row.get("disposition") or "") != "implement":
            continue
        for field in ("declared_implementation_targets", "declared_test_targets"):
            for raw in row.get(field, []):
                target = str(raw or "").strip()
                if not target:
                    continue
                if target.startswith("apps/web/") or target.startswith("tests/unit/web/") or target.startswith("tests/e2e/frontend"):
                    continue
                targets.append(target)
    return bool(targets) and all((output_dir / target).is_file() for target in targets)


def _assert_backend_freeze_unchanged(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    if str(before.get("status") or "") == "not-present":
        return
    if before == after:
        return
    before_rows = {
        str(row.get("path") or ""): str(row.get("sha256") or "")
        for row in before.get("files", [])
        if isinstance(row, Mapping)
    }
    after_rows = {
        str(row.get("path") or ""): str(row.get("sha256") or "")
        for row in after.get("files", [])
        if isinstance(row, Mapping)
    }
    changed = sorted(
        path
        for path in set(before_rows) | set(after_rows)
        if before_rows.get(path) != after_rows.get(path)
    )
    raise FrontendImplementationAuthoringError(
        "frontend-only authoring changed frozen WFF-P3 backend surfaces: " + ",".join(changed[:12])
    )


def _phase2_auth_integration_mode(phase2_root: Path) -> str:
    path = phase2_root / "tech-stack-decision.yaml"
    if not path.is_file() or path.is_symlink():
        return "runtime-agnostic-real-auth"
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("integration_mode:"):
            continue
        value = line.split(":", 1)[1].strip().strip('"\'')
        return value or "runtime-agnostic-real-auth"
    return "runtime-agnostic-real-auth"


def _agentic_support_region(block_id: str) -> str:
    return render_agentic_region(block_id, f"// {AGENTIC_BODY_SENTINEL}:{block_id}")


def _agentic_body_region(block_id: str, *, indent: str = "  ") -> str:
    return render_agentic_region(block_id, f'throw new Error("{AGENTIC_BODY_SENTINEL}:{block_id}");', indent=indent)


def _contract_pack_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "openapi_path": output_dir / "contracts" / "openapi.yaml",
        "shared_types_path": output_dir / "packages" / "shared-types" / "index.ts",
        "api_client_path": output_dir / "packages" / "api-client" / "index.ts",
        "implementation_bindings_path": output_dir / "implementation-bindings.json",
        "ui_fallback_report_path": output_dir / "prototype-fallback" / "ui-prototype-fallback-report.json",
        "ui_ia_contract_path": output_dir / "prototype-fallback" / "ui-ia-contract.json",
    }


def _materialize_or_reuse_contract_pack(
    *,
    phase2_root: Path,
    output_dir: Path,
    title: str,
    version: str,
    implementation_authority: Mapping[str, Any] | None,
) -> dict[str, Any]:
    paths = _contract_pack_paths(output_dir)
    required = [
        paths["openapi_path"],
        paths["shared_types_path"],
        paths["api_client_path"],
        paths["implementation_bindings_path"],
    ]
    if all(path.is_file() and not path.is_symlink() for path in required):
        return {
            **paths,
            "ui_fallback_summary": {"mode": "existing-workspace", "reason": "preserve-current-contract-and-binding-state"},
        }
    esp_text, stage_03_text, stage_04_text = load_phase2_source_texts(phase2_root)
    return materialize_contract_pack(
        phase2_root=phase2_root,
        output_dir=output_dir,
        title=title,
        version=version,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        enable_ui_fallback=False,
        enforce_compiled_authority=False,
        implementation_authority=implementation_authority,
    )


def _load_ui_contract(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrontendImplementationAuthoringError("frontend UI IA contract is unreadable") from exc
    if not isinstance(payload, dict):
        raise FrontendImplementationAuthoringError("frontend UI IA contract must be an object")
    return payload


def _assert_page_authoring_readiness(page: Mapping[str, Any]) -> None:
    page_id = str(page.get("page_id") or "").strip()
    if not page_id:
        raise FrontendImplementationAuthoringError("frontend UI IA page_id is required")
    route = str(page.get("route") or "").strip()
    if not route.startswith("/"):
        raise FrontendImplementationAuthoringError(f"frontend UI IA route is invalid: {page_id}")
    page_status = str(page.get("readiness_status") or "").strip().lower()
    if page_status and page_status != "ready":
        raise FrontendImplementationAuthoringError(
            f"frontend UI IA page is not ready: {page_id}:{page_status}"
        )
    interactions = page.get("compiled_interactions", [])
    if not isinstance(interactions, list):
        raise FrontendImplementationAuthoringError(f"frontend UI IA compiled interactions are invalid: {page_id}")
    for raw in interactions:
        if not isinstance(raw, dict):
            raise FrontendImplementationAuthoringError(f"frontend UI IA interaction is invalid: {page_id}")
        interaction_id = str(raw.get("interaction_id") or "").strip()
        status = str(raw.get("readiness_status") or "").strip().lower()
        if status not in {"", "ready", "p3-realization-open"}:
            raise FrontendImplementationAuthoringError(
                f"frontend UI IA interaction is not ready: {page_id}:{interaction_id}:{status}"
            )
        if status == "p3-realization-open":
            candidates = [str(value).strip() for value in raw.get("operation_candidates", []) if str(value).strip()]
            if str(raw.get("authority_status") or "").strip().lower() != "sufficient" or not candidates:
                raise FrontendImplementationAuthoringError(
                    f"frontend UI IA realization-open interaction lacks frozen operation authority: {page_id}:{interaction_id}"
                )
            continue
        for field in ("service_binding_id", "domain_service", "api_endpoint", "response_field_mapping"):
            if not str(raw.get(field) or "").strip():
                raise FrontendImplementationAuthoringError(
                    f"frontend UI IA interaction lacks {field}: {page_id}:{interaction_id}"
                )
        binding_mode = str(raw.get("binding_mode") or "").strip().lower()
        action_type = str(raw.get("action_type") or "").strip().lower()
        if binding_mode == "write" or action_type in {"create", "update", "delete", "submit", "mutate"}:
            if not str(raw.get("request_field_mapping") or "").strip():
                raise FrontendImplementationAuthoringError(
                    f"frontend UI IA write interaction lacks request_field_mapping: {page_id}:{interaction_id}"
                )


def _expected_page_rows(ui_contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_pages = ui_contract.get("pages", [])
    if not isinstance(raw_pages, list) or not raw_pages:
        raise FrontendImplementationAuthoringError("frontend UI IA contract has no pages")
    rows: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    seen_tests: set[str] = set()
    for raw in raw_pages:
        if not isinstance(raw, dict):
            raise FrontendImplementationAuthoringError("frontend UI IA page must be an object")
        _assert_page_authoring_readiness(raw)
        page_id = str(raw.get("page_id") or "").strip()
        title = str(raw.get("page_title") or raw.get("page_name") or raw.get("title") or page_id).strip()
        route = str(raw.get("route") or "").strip()
        route_segment = sanitize_route_segment(route, title or page_id)
        file_segment = frontend_route_file_segment(route_segment)
        target = f"apps/web/app/{file_segment}/page.tsx"
        test_target = frontend_surface_unit_test_path(file_segment.replace("/", "-"))
        if target in seen_targets or test_target in seen_tests:
            raise FrontendImplementationAuthoringError(f"frontend UI IA routes collide after target normalization: {route}")
        seen_targets.add(target)
        seen_tests.add(test_target)
        source_projection = {
            "page_id": page_id,
            "route": route,
            "page_blueprint_type": str(raw.get("page_blueprint_type") or "").strip(),
            "required_regions": [str(item).strip() for item in raw.get("required_regions", []) if str(item).strip()],
            "compiled_interactions": [item for item in raw.get("compiled_interactions", []) if isinstance(item, dict)],
        }
        rows.append(
            {
                "page_id": page_id,
                "route": route,
                "title": title,
                "target": target,
                "test_target": test_target,
                "compiled_interactions": [item for item in raw.get("compiled_interactions", []) if isinstance(item, dict)],
                "canonical_operation_candidates": [
                    str(item).strip() for item in raw.get("canonical_operation_candidates", []) if str(item).strip()
                ],
                "source_sha256": _json_sha256(source_projection),
            }
        )
    return rows


def _authority_frontend_denominator(authority: Mapping[str, Any]) -> dict[str, dict[str, list[str]]]:
    if not p3_agentic_implementation_authority_is_valid(authority):
        raise FrontendImplementationAuthoringError("accepted P3 implementation authority is invalid")
    implementation_owners: dict[str, list[str]] = {}
    test_owners: dict[str, list[str]] = {}
    slice_decisions = authority.get("slice_decisions")
    if not isinstance(slice_decisions, dict):
        raise FrontendImplementationAuthoringError("accepted P3 implementation authority has no slice decisions")
    for slice_id, raw in slice_decisions.items():
        if not isinstance(raw, dict):
            continue
        normalized_slice = str(slice_id).strip()
        for target in raw.get("implementation_targets", []):
            path = str(target).strip().replace("\\", "/")
            if path.startswith("apps/web/"):
                implementation_owners.setdefault(path, []).append(normalized_slice)
        for target in raw.get("test_targets", []):
            path = str(target).strip().replace("\\", "/")
            if path.startswith("tests/unit/web/"):
                test_owners.setdefault(path, []).append(normalized_slice)
    return {
        "implementation": {path: list(dict.fromkeys(rows)) for path, rows in implementation_owners.items()},
        "tests": {path: list(dict.fromkeys(rows)) for path, rows in test_owners.items()},
    }


def _authority_delta_frontend_denominator(
    *,
    page_rows: list[dict[str, Any]],
    authority: Mapping[str, Any],
) -> dict[str, dict[str, list[str]]]:
    plan = [
        row
        for row in authority.get("exact_realization_plan", [])
        if isinstance(row, Mapping) and str(row.get("disposition") or "") == "implement"
    ]
    owners_by_operation: dict[str, list[str]] = {}
    owners_by_contract: dict[str, list[str]] = {}
    for row in plan:
        slice_id = str(row.get("slice_id") or "").strip()
        operation_id = str(row.get("operation_id") or "").strip()
        contract_id = str(row.get("contract_id") or "").strip()
        if slice_id and operation_id:
            owners_by_operation.setdefault(operation_id, []).append(slice_id)
        if slice_id and contract_id:
            owners_by_contract.setdefault(contract_id, []).append(slice_id)

    implementation: dict[str, list[str]] = {}
    tests: dict[str, list[str]] = {}
    for page in page_rows:
        slice_ids: list[str] = []
        for interaction in page.get("compiled_interactions", []):
            if not isinstance(interaction, Mapping):
                continue
            operation_id = str(interaction.get("operation_id") or "").strip()
            contract_id = str(interaction.get("contract_id") or "").strip()
            matched = owners_by_operation.get(operation_id, []) if operation_id else []
            if contract_id:
                contract_matches = owners_by_contract.get(contract_id, [])
                matched = [slice_id for slice_id in matched if slice_id in contract_matches] if matched else contract_matches
            slice_ids.extend(matched)
            for candidate in interaction.get("operation_candidates", []):
                slice_ids.extend(owners_by_operation.get(str(candidate).strip(), []))
        for candidate in page.get("canonical_operation_candidates", []):
            slice_ids.extend(owners_by_operation.get(str(candidate).strip(), []))
        slice_ids = list(dict.fromkeys(slice_ids))
        if not slice_ids:
            raise FrontendImplementationAuthoringError(
                f"frontend Authority Delta extension cannot bind page to frozen P3 operation/contract slices: {page['page_id']}"
            )
        implementation[str(page["target"])] = slice_ids
        tests[str(page["test_target"])] = slice_ids
    return {"implementation": implementation, "tests": tests}


def _assert_authority_target_coverage(
    *,
    page_rows: list[dict[str, Any]],
    authority: Mapping[str, Any],
) -> tuple[dict[str, dict[str, list[str]]], str]:
    denominator = _authority_frontend_denominator(authority)
    expected_impl = {str(row["target"]) for row in page_rows}
    expected_tests = {str(row["test_target"]) for row in page_rows}
    actual_impl = set(denominator["implementation"])
    actual_tests = set(denominator["tests"])
    if not actual_impl and not actual_tests:
        extension = _authority_delta_frontend_denominator(page_rows=page_rows, authority=authority)
        return extension, "p3-authority-delta-frontend-extension"
    if actual_impl != expected_impl:
        missing = sorted(expected_impl - actual_impl)
        extra = sorted(actual_impl - expected_impl)
        raise FrontendImplementationAuthoringError(
            "accepted P3 frontend implementation-target denominator differs from UI IA pages"
            + (f"; missing={','.join(missing)}" if missing else "")
            + (f"; extra={','.join(extra)}" if extra else "")
        )
    if actual_tests != expected_tests:
        missing = sorted(expected_tests - actual_tests)
        extra = sorted(actual_tests - expected_tests)
        raise FrontendImplementationAuthoringError(
            "accepted P3 frontend test-target denominator differs from UI IA pages"
            + (f"; missing={','.join(missing)}" if missing else "")
            + (f"; extra={','.join(extra)}" if extra else "")
        )
    return denominator, "accepted-p3-declared-frontend-targets"


def _render_application_shell(
    *,
    page_rows: list[Mapping[str, Any]],
    authority: Mapping[str, Any],
    product_access_requirements: Mapping[str, Any] | None = None,
    auth_integration_mode: str = "runtime-agnostic-real-auth",
) -> str:
    imports: list[str] = []
    page_bindings: list[dict[str, str]] = []
    for index, page in enumerate(page_rows, start=1):
        target = str(page["target"])
        prefix = "apps/web/app/"
        if not target.startswith(prefix) or not target.endswith(".tsx"):
            raise FrontendImplementationAuthoringError(f"frontend application page target is invalid: {target}")
        relative = "./" + target[len(prefix):].removesuffix(".tsx")
        component = f"AuthoredPage{index}"
        imports.append(f"import {component} from {json.dumps(relative)};")
        page_bindings.append(
            {
                "pageId": str(page["page_id"]),
                "route": str(page["route"]),
                "component": component,
                "target": target,
                "sourceSha256": str(page["source_sha256"]),
            }
        )
    binding = {
        "implementationDecisionId": str(authority.get("decision_id") or ""),
        "implementationDecisionDigest": str(authority.get("decision_digest") or ""),
        "pages": page_bindings,
        "applicationTarget": FRONTEND_APPLICATION_TARGET,
        "productAccessRequirements": dict(product_access_requirements or {}),
        "identityProviderMode": auth_integration_mode,
        "operatingProductMaturityQuestions": dict(OPERATING_PRODUCT_MATURITY_QUESTIONS),
        "p3RuntimeAuthCapabilities": {
            "localSessionAdapter": {
                "availability": (
                    "forbidden-by-external-idp-authority"
                    if auth_integration_mode == "external-idp"
                    else "explicit-opt-in-p3-runtime-support"
                ),
                "enablement": "PHASE3_LOCAL_AUTH_ENABLED=true plus deployment-provisioned PHASE3_AUTH_USERS_JSON",
                "signInEndpoint": "/auth/session",
                "signOutEndpoint": "/auth/session",
                "requestFields": ["username", "password"],
                "webHelpers": ["createProductSession", "getProductSession", "clearProductSession"],
                "browserSession": "HttpOnly SameSite=Strict BFF cookie",
                "apiTransport": "Authorization Bearer",
            },
            "externalIdentityProvider": (
                "required by accepted P2 security authority"
                if auth_integration_mode == "external-idp"
                else "not frozen; P3 may choose the explicitly enabled local adapter without creating business API authority"
            ),
        },
    }
    binding_json = json.dumps(binding, ensure_ascii=False, sort_keys=True)
    return "\n".join(
        [
            "// WFF protected application binding. Complete product realization belongs to the Agentic region below.",
            *imports,
            "",
            f"export const wffFrontendProductBinding = {binding_json} as const;",
            "",
            _agentic_support_region("product-application"),
            "",
        ]
    )


def _render_e2e_shell(
    *,
    ui_contract: Mapping[str, Any],
    page_rows: list[Mapping[str, Any]],
    authority: Mapping[str, Any],
    product_access_requirements: Mapping[str, Any] | None = None,
    auth_integration_mode: str = "runtime-agnostic-real-auth",
) -> str:
    interaction_bindings: list[dict[str, str]] = []
    for raw_page in ui_contract.get("pages", []):
        if not isinstance(raw_page, Mapping):
            continue
        page_id = str(raw_page.get("page_id") or "").strip()
        route = str(raw_page.get("route") or "").strip()
        for raw_interaction in raw_page.get("compiled_interactions", []):
            if not isinstance(raw_interaction, Mapping):
                continue
            status = str(raw_interaction.get("readiness_status") or "ready").strip().lower()
            interaction_id = str(raw_interaction.get("interaction_id") or "").strip()
            if status != "ready" or not interaction_id:
                continue
            interaction_bindings.append(
                {
                    "pageId": page_id,
                    "route": route,
                    "interactionId": interaction_id,
                    "apiEndpoint": str(raw_interaction.get("api_endpoint") or "").strip(),
                    "bindingMode": str(raw_interaction.get("binding_mode") or "").strip().lower(),
                    "serviceBindingId": str(raw_interaction.get("service_binding_id") or "").strip(),
                }
            )
    binding = {
        "implementationDecisionId": str(authority.get("decision_id") or ""),
        "implementationDecisionDigest": str(authority.get("decision_digest") or ""),
        "pages": [
            {"pageId": str(page["page_id"]), "route": str(page["route"])}
            for page in page_rows
        ],
        "interactions": interaction_bindings,
        "canonicalOperationCatalog": [
            dict(row) for row in ui_contract.get("canonical_operation_catalog", []) if isinstance(row, Mapping)
        ],
        "pageOperationCandidates": {
            str(page.get("page_id") or "").strip(): [
                str(value).strip()
                for value in page.get("canonical_operation_candidates", [])
                if str(value).strip()
            ]
            for page in ui_contract.get("pages", [])
            if isinstance(page, Mapping) and str(page.get("page_id") or "").strip()
        },
        "productAccessRequirements": dict(product_access_requirements or {}),
        "identityProviderMode": auth_integration_mode,
        "evidenceContract": {
            "runtimeMarker": "// @wff:frontend-runtime-evidence page_id=<page-id> interaction_id=<interaction-id>",
            "consumerJourneyMarker": "// @wff:frontend-consumer-journey journey_id=<id> entry_route=<public-route> outcome=<user-consumable-business-outcome>",
            "consumerJourneyOutcomeRule": (
                "outcome must name the user-consumable business result and resulting decision/next-step value; route access, auth success, "
                "persistence, bounded-role access, reload/re-entry, or an opaque id alone do not qualify as the meaningful outcome"
            ),
            "operatingProductMaturityQuestions": dict(OPERATING_PRODUCT_MATURITY_QUESTIONS),
            "consumerPageMarker": "// @wff:frontend-consumer-page page_id=<page-id>",
            "consumerPageCapture": "call wffCaptureConsumerPage(page, testInfo, '<page-id>') after the product-facing page is reached",
            "coverEveryReadyInteraction": True,
            "composeBusinessActionsOnlyFromCanonicalOperationCatalog": True,
            "realizationOpenInteractionPlacementBelongsToAgentic": True,
            "requireFirstEntryToOutcomeJourney": True,
            "authenticatedProductRequiresPostSignInPageCapture": True,
            "exerciseRealGeneratedWebApiPath": True,
            "forbidBrowserOrNetworkSubstitution": True,
            "writeEvidenceUsesProjectIsolation": "testInfo.project.name",
            "authenticatedJourneyCredentials": (
                "use runtime-isolated credentials only as product identity-UI input when authentication is required; "
                "the E2E journey must not reference /auth/session, cookies, Bearer tokens, or identity headers directly"
            ),
        },
    }
    binding_json = json.dumps(binding, ensure_ascii=False, sort_keys=True)
    return "\n".join(
        [
            "import { mkdirSync } from 'node:fs';",
            "import { join } from 'node:path';",
            "",
            "// WFF protected consumer-E2E binding. Agentic owns the human task flow and assertions inside the region below.",
            _agentic_support_region("consumer-e2e"),
            "",
            f"export const wffFrontendE2EBinding = {binding_json} as const;",
            "",
            "type WffScreenshotPage = { screenshot(options: { path: string; fullPage: boolean }): Promise<unknown> };",
            "type WffScreenshotTestInfo = { project: { name: string } };",
            "",
            "export async function wffCaptureConsumerPage(page: WffScreenshotPage, testInfo: WffScreenshotTestInfo, pageId: string): Promise<void> {",
            "  const accepted = wffFrontendE2EBinding.pages.some((entry) => entry.pageId === pageId);",
            "  if (!accepted) throw new Error(`WFF_CONSUMER_PAGE_FOREIGN:${pageId}`);",
            "  const screenshotDir = process.env.WFF_FRONTEND_SCREENSHOT_DIR ?? 'frontend-runtime-screenshots';",
            "  mkdirSync(screenshotDir, { recursive: true });",
            "  const safeId = pageId.replace(/[^A-Za-z0-9_.-]+/g, '-');",
            "  const screenshotPath = join(screenshotDir, `${testInfo.project.name}-consumer-${safeId}.png`);",
            "  try { await page.screenshot({ path: screenshotPath, fullPage: true }); }",
            "  catch { await page.screenshot({ path: screenshotPath, fullPage: false }); }",
            "}",
            "",
        ]
    )


def _render_page_shell(
    *,
    page: Mapping[str, Any],
    authority: Mapping[str, Any],
    slice_ids: list[str],
) -> str:
    binding = {
        "pageId": str(page["page_id"]),
        "route": str(page["route"]),
        "sourceSha256": str(page["source_sha256"]),
        "implementationDecisionId": str(authority.get("decision_id") or ""),
        "implementationDecisionDigest": str(authority.get("decision_digest") or ""),
        "sliceIds": slice_ids,
        "testTarget": str(page["test_target"]),
    }
    binding_json = json.dumps(binding, ensure_ascii=False, sort_keys=True)
    route_json = json.dumps(str(page["route"]), ensure_ascii=False)
    page_id_json = json.dumps(str(page["page_id"]), ensure_ascii=False)
    return (
        "// WFF protected frontend authoring shell. Product composition belongs only inside @wff:agentic regions.\n"
        + _agentic_support_region("page-support")
        + "\n\n"
        + f"export const wffFrontendAuthoringBinding = {binding_json} as const;\n\n"
        + "function renderAgenticPageContent() {\n"
        + _agentic_body_region("page-content")
        + "\n}\n\n"
        + "export default function Page() {\n"
        + f"  return <main data-phase3-surface={{{route_json}}} data-phase3-page-id={{{page_id_json}}}>{{renderAgenticPageContent()}}</main>;\n"
        + "}\n"
    )


def _render_test_shell(
    *,
    page: Mapping[str, Any],
    authority: Mapping[str, Any],
    slice_ids: list[str],
) -> str:
    binding = {
        "pageId": str(page["page_id"]),
        "target": str(page["target"]),
        "sourceSha256": str(page["source_sha256"]),
        "implementationDecisionId": str(authority.get("decision_id") or ""),
        "implementationDecisionDigest": str(authority.get("decision_digest") or ""),
        "sliceIds": slice_ids,
    }
    binding_json = json.dumps(binding, ensure_ascii=False, sort_keys=True)
    return (
        "import { describe, expect, it } from 'vitest';\n\n"
        + f"const wffFrontendTestBinding = {binding_json} as const;\n\n"
        + "describe('P3 frontend Agentic page realization', () => {\n"
        + "  it('proves the accepted page behavior without replacing upstream authority', async () => {\n"
        + _agentic_body_region("behavior-assertion", indent="    ")
        + "\n    expect(wffFrontendTestBinding.pageId).toBeTruthy();\n"
        + "  });\n"
        + "});\n"
    )


def _validate_agentic_source_root(
    *,
    source_root: Path,
    authority: Mapping[str, Any],
    ui_contract_sha256: str,
) -> bool:
    report_path = source_root / "impl-frontend-report.json"
    if not report_path.is_file() or report_path.is_symlink():
        raise FrontendImplementationAuthoringError("frontend Agentic source root lacks impl-frontend-report.json")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrontendImplementationAuthoringError("frontend Agentic source report is unreadable") from exc
    authoring = report.get("authoring") if isinstance(report, dict) else None
    if not isinstance(authoring, dict):
        raise FrontendImplementationAuthoringError("frontend Agentic source report lacks authoring identity")
    if str(authoring.get("ui_ia_contract_sha256") or "") != ui_contract_sha256:
        raise FrontendImplementationAuthoringError("frontend Agentic source root belongs to another UI IA contract")
    source_digest = str(authoring.get("implementation_decision_digest") or "")
    target_digest = str(authority.get("decision_digest") or "")
    if source_digest == target_digest:
        return False
    if str(authoring.get("status") or "") != "materialized" or int(authoring.get("unresolved_block_count") or 0) != 0:
        raise FrontendImplementationAuthoringError("frontend Agentic source must be fully materialized before cross-digest reuse")
    source_authority_path = source_root / "p3-agentic-implementation-authority.json"
    if not source_authority_path.is_file() or source_authority_path.is_symlink():
        raise FrontendImplementationAuthoringError("frontend Agentic source root lacks its P3 implementation authority")
    try:
        source_authority = json.loads(source_authority_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrontendImplementationAuthoringError("frontend Agentic source authority is unreadable") from exc
    if not isinstance(source_authority, dict) or not p3_agentic_implementation_authority_is_valid(source_authority):
        raise FrontendImplementationAuthoringError("frontend Agentic source authority is invalid")
    if str(source_authority.get("decision_digest") or "") != source_digest:
        raise FrontendImplementationAuthoringError("frontend Agentic source report diverges from its P3 implementation authority")
    if not p3_frontend_agentic_body_contract_is_compatible(source_authority, authority):
        raise FrontendImplementationAuthoringError("frontend Agentic source semantic body contract changed under the new P3 decision")
    return True


def _update_implementation_bindings(
    *,
    output_dir: Path,
    authority: Mapping[str, Any],
    authoring: Mapping[str, Any],
) -> None:
    path = output_dir / "implementation-bindings.json"
    if not path.is_file() or path.is_symlink():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrontendImplementationAuthoringError("implementation-bindings.json is unreadable") from exc
    if not isinstance(payload, dict):
        raise FrontendImplementationAuthoringError("implementation-bindings.json must be an object")
    existing_decision_digest = str(payload.get("decision_digest") or "").strip()
    if existing_decision_digest and existing_decision_digest != str(authority.get("decision_digest") or ""):
        raise FrontendImplementationAuthoringError("implementation-bindings.json belongs to another P3 decision")
    page_refs = {
        str(row.get("path") or ""): {
            "path": str(row.get("path") or ""),
            "page_id": str(row.get("page_id") or ""),
            "content_sha256": str(row.get("content_sha256") or ""),
            "shell_sha256": str(row.get("shell_sha256") or ""),
            "status": str(row.get("status") or ""),
        }
        for row in authoring.get("pages", [])
        if isinstance(row, dict) and str(row.get("path") or "")
    }
    for key in ("rows", "non_operation_rows"):
        rows = payload.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            refs = [page_refs[target] for target in row.get("implementation_targets", []) if target in page_refs]
            if refs:
                row["frontend_authoring"] = {
                    "status": str(authoring.get("status") or ""),
                    "implementation_decision_digest": str(authority.get("decision_digest") or ""),
                    "ui_ia_contract_sha256": str(authoring.get("ui_ia_contract_sha256") or ""),
                    "pages": refs,
                    "semantic_authority": False,
                }
    application = authoring.get("application") if isinstance(authoring.get("application"), dict) else {}
    consumer_e2e = authoring.get("consumer_e2e") if isinstance(authoring.get("consumer_e2e"), dict) else {}
    payload["frontend_authoring"] = {
        "schema_version": FRONTEND_AUTHORING_SCHEMA,
        "status": str(authoring.get("status") or ""),
        "implementation_decision_id": str(authority.get("decision_id") or ""),
        "implementation_decision_digest": str(authority.get("decision_digest") or ""),
        "ui_ia_contract_sha256": str(authoring.get("ui_ia_contract_sha256") or ""),
        "content_digest": str(authoring.get("content_digest") or ""),
        "application": {
            "path": str(application.get("path") or ""),
            "status": str(application.get("status") or ""),
            "content_sha256": str(application.get("content_sha256") or ""),
            "shell_sha256": str(application.get("shell_sha256") or ""),
        },
        "consumer_e2e": {
            "path": str(consumer_e2e.get("path") or ""),
            "status": str(consumer_e2e.get("status") or ""),
            "content_sha256": str(consumer_e2e.get("content_sha256") or ""),
            "shell_sha256": str(consumer_e2e.get("shell_sha256") or ""),
        },
        "semantic_authority": False,
        "runtime_evidence_refs": [],
        "trace_confirmed": False,
    }
    write_json(path, payload)


def _protected_shell_refresh_allowed(
    *,
    output_dir: Path,
    authority: Mapping[str, Any],
    ui_ia_contract_sha256: str,
) -> bool:
    """Allow one fail-closed generator-owned shell upgrade from the immediately previous schema.

    Agentic bodies remain the only preserved content. The refresh is allowed only for a fully
    materialized prior authoring bound to the same P3 decision and exact UI-IA identity; ordinary
    same-schema edits or changed upstream authority continue to fail closed.
    """
    report_path = output_dir / "impl-frontend-report.json"
    if not report_path.is_file() or report_path.is_symlink():
        return False
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    authoring = payload.get("authoring") if isinstance(payload, dict) else None
    if not isinstance(authoring, dict):
        return False
    if str(authoring.get("schema_version") or "") != PREVIOUS_FRONTEND_AUTHORING_SCHEMA:
        return False
    if str(authoring.get("status") or "") != "materialized":
        return False
    if int(authoring.get("unresolved_block_count") or 0) != 0:
        return False
    if bool(authoring.get("semantic_authority")):
        return False
    if str(authoring.get("implementation_decision_digest") or "") != str(authority.get("decision_digest") or ""):
        return False
    if str(authoring.get("ui_ia_contract_sha256") or "") != ui_ia_contract_sha256:
        return False
    application = authoring.get("application") if isinstance(authoring.get("application"), dict) else {}
    consumer_e2e = authoring.get("consumer_e2e") if isinstance(authoring.get("consumer_e2e"), dict) else {}
    pages = [row for row in authoring.get("pages", []) if isinstance(row, dict)]
    if str(application.get("status") or "") != "materialized" or str(consumer_e2e.get("status") or "") != "materialized":
        return False
    if any(str(row.get("status") or "") != "materialized" for row in pages):
        return False

    def recorded_shell_matches(relative: str, expected_digest: str) -> bool:
        path = output_dir / relative
        if not relative or not expected_digest or not path.is_file() or path.is_symlink():
            return False
        current = _sha256_bytes(agentic_shell_projection(path.read_text(encoding="utf-8")).encode("utf-8"))
        return current == expected_digest

    if not recorded_shell_matches(str(application.get("path") or ""), str(application.get("shell_sha256") or "")):
        return False
    if not recorded_shell_matches(str(consumer_e2e.get("path") or ""), str(consumer_e2e.get("shell_sha256") or "")):
        return False
    for row in pages:
        if not recorded_shell_matches(str(row.get("path") or ""), str(row.get("shell_sha256") or "")):
            return False
        if not recorded_shell_matches(str(row.get("test_path") or ""), str(row.get("test_shell_sha256") or "")):
            return False
    return True


def scaffold_frontend_implementation(
    *,
    phase2_root: Path,
    output_dir: Path,
    title: str,
    version: str,
    ui_ia_contract_path: Path | None = None,
    implementation_authority: Mapping[str, Any] | None = None,
    agentic_source_root: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    authoring_requested = ui_ia_contract_path is not None
    authority = dict(implementation_authority) if isinstance(implementation_authority, Mapping) else None
    preloaded_ui_contract: dict[str, Any] = {}
    web_locale = "en"
    if authoring_requested:
        assert ui_ia_contract_path is not None
        preloaded_ui_contract = _load_ui_contract(ui_ia_contract_path.resolve())
        language = preloaded_ui_contract.get("project_language_requirements")
        if isinstance(language, Mapping):
            web_locale = str(language.get("consumer_locale") or "en").strip() or "en"
    backend_freeze_before = _backend_freeze_fingerprint(output_dir)
    existing_wff_p3_backend = _authority_has_materialized_backend_targets(authority, output_dir)
    if authoring_requested and authority is None:
        raise FrontendImplementationAuthoringError(
            "requested frontend authoring requires accepted P3 implementation authority"
        )

    if authoring_requested and existing_wff_p3_backend:
        contract_paths = _contract_pack_paths(output_dir)
        required_existing = [
            contract_paths["openapi_path"],
            contract_paths["shared_types_path"],
            contract_paths["api_client_path"],
            contract_paths["implementation_bindings_path"],
        ]
        missing_existing = [path.relative_to(output_dir).as_posix() for path in required_existing if not path.is_file() or path.is_symlink()]
        if missing_existing:
            raise FrontendImplementationAuthoringError(
                "frontend-only continuation refuses to reconstruct frozen WFF-P3 contract/backend state; missing="
                + ",".join(missing_existing)
            )

    contract_summary = _materialize_or_reuse_contract_pack(
        phase2_root=phase2_root,
        output_dir=output_dir,
        title=title,
        version=version,
        implementation_authority=authority,
    )
    if authoring_requested and existing_wff_p3_backend:
        root_summary = scaffold_frozen_backend_frontend_runtime_overlay(output_dir=output_dir)
        shared_summary = {
            "mode": "preserved-existing-contract-client-packages",
            "files_created": [],
            "count": 0,
        }
    else:
        root_summary = scaffold_root_workspace(output_dir=output_dir, project_name=title)
        shared_summary = scaffold_shared_packages(output_dir=output_dir)
    web_summary = scaffold_web_app(
        output_dir=output_dir,
        preserve_existing=("apps/web/app/theme.css",) if authoring_requested else (),
        ui_locale=web_locale,
    )
    backend_freeze_after_scaffold = _backend_freeze_fingerprint(output_dir)
    _assert_backend_freeze_unchanged(backend_freeze_before, backend_freeze_after_scaffold)

    if not authoring_requested:
        summary = {
            "artifact_kind": "phase3-impl-frontend-report",
            "quality_gate": "pass",
            "contract_pack": {key: str(value) for key, value in contract_summary.items() if key.endswith("_path")},
            "root_summary": root_summary,
            "shared_summary": shared_summary,
            "web_summary": web_summary,
            "ui_ia_contract": "",
            "authoring": {
                "schema_version": FRONTEND_AUTHORING_SCHEMA,
                "mode": "scaffold-only-compatibility",
                "status": "not-requested",
                "semantic_authority": False,
                "runtime_evidence_refs": [],
                "trace_confirmed": False,
            },
            "claim_ceiling": (
                "frontend scaffold only; this compatibility mode cannot satisfy requested frontend Agentic authoring, "
                "runtime/browser acceptance, product review, or P3 completion"
            ),
        }
        write_json(output_dir / "impl-frontend-report.json", summary)
        return summary

    assert ui_ia_contract_path is not None
    assert authority is not None
    ui_path = ui_ia_contract_path.resolve()
    ui_contract = preloaded_ui_contract or _load_ui_contract(ui_path)
    ui_contract_sha256 = _file_sha256(ui_path)
    page_rows = _expected_page_rows(ui_contract)
    denominator, target_binding_mode = _assert_authority_target_coverage(page_rows=page_rows, authority=authority)
    source_root = agentic_source_root.resolve() if agentic_source_root is not None else None
    source_contract_compatible_refresh = False
    if source_root is not None:
        source_contract_compatible_refresh = _validate_agentic_source_root(
            source_root=source_root,
            authority=authority,
            ui_contract_sha256=ui_contract_sha256,
        )
    protected_shell_refresh = source_contract_compatible_refresh or _protected_shell_refresh_allowed(
        output_dir=output_dir,
        authority=authority,
        ui_ia_contract_sha256=ui_contract_sha256,
    )

    page_records: list[dict[str, Any]] = []
    unresolved_blocks: list[dict[str, str]] = []

    application_path = output_dir / FRONTEND_APPLICATION_TARGET
    application_path.parent.mkdir(parents=True, exist_ok=True)
    product_access_requirements = (
        ui_contract.get("product_access_requirements")
        if isinstance(ui_contract.get("product_access_requirements"), Mapping)
        else {}
    )
    auth_integration_mode = _phase2_auth_integration_mode(phase2_root)
    rendered_application = _render_application_shell(
        page_rows=page_rows,
        authority=authority,
        product_access_requirements=product_access_requirements,
        auth_integration_mode=auth_integration_mode,
    )
    application_content, application_blocks = merge_bounded_agentic_regions(
        application_path,
        rendered_application,
        source_path=(source_root / FRONTEND_APPLICATION_TARGET) if source_root is not None else None,
        error_type=FrontendImplementationAuthoringError,
        boundary_label="frontend application",
        allow_protected_shell_refresh=protected_shell_refresh,
    )
    application_path.write_text(application_content, encoding="utf-8")
    for block in application_blocks:
        if block["status"] == "authoring-required":
            unresolved_blocks.append(
                {
                    "page_id": "__application__",
                    "path": FRONTEND_APPLICATION_TARGET,
                    "block_id": block["block_id"],
                }
            )
    application_record = {
        "path": FRONTEND_APPLICATION_TARGET,
        "status": (
            "authoring-required"
            if any(block["status"] == "authoring-required" for block in application_blocks)
            else "materialized"
        ),
        "shell_sha256": _sha256_bytes(agentic_shell_projection(application_content).encode("utf-8")),
        "content_sha256": _file_sha256(application_path),
        "agentic_blocks": application_blocks,
    }

    e2e_path = output_dir / FRONTEND_E2E_TARGET
    e2e_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_e2e = _render_e2e_shell(
        ui_contract=ui_contract,
        page_rows=page_rows,
        authority=authority,
        product_access_requirements=product_access_requirements,
        auth_integration_mode=auth_integration_mode,
    )
    e2e_content, e2e_blocks = merge_bounded_agentic_regions(
        e2e_path,
        rendered_e2e,
        source_path=(source_root / FRONTEND_E2E_TARGET) if source_root is not None else None,
        error_type=FrontendImplementationAuthoringError,
        boundary_label="frontend consumer e2e",
        allow_protected_shell_refresh=protected_shell_refresh,
    )
    e2e_path.write_text(e2e_content, encoding="utf-8")
    for block in e2e_blocks:
        if block["status"] == "authoring-required":
            unresolved_blocks.append(
                {
                    "page_id": "__consumer_e2e__",
                    "path": FRONTEND_E2E_TARGET,
                    "block_id": block["block_id"],
                }
            )
    e2e_record = {
        "path": FRONTEND_E2E_TARGET,
        "status": (
            "authoring-required"
            if any(block["status"] == "authoring-required" for block in e2e_blocks)
            else "materialized"
        ),
        "shell_sha256": _sha256_bytes(agentic_shell_projection(e2e_content).encode("utf-8")),
        "content_sha256": _file_sha256(e2e_path),
        "agentic_blocks": e2e_blocks,
    }

    for page in page_rows:
        target = str(page["target"])
        test_target = str(page["test_target"])
        slice_ids = denominator["implementation"][target]
        if set(slice_ids) != set(denominator["tests"][test_target]):
            raise FrontendImplementationAuthoringError(
                f"frontend implementation/test target ownership differs: {target}:{test_target}"
            )
        page_path = output_dir / target
        test_path = output_dir / test_target
        page_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        rendered_page = _render_page_shell(page=page, authority=authority, slice_ids=slice_ids)
        rendered_test = _render_test_shell(page=page, authority=authority, slice_ids=slice_ids)
        page_content, page_blocks = merge_bounded_agentic_regions(
            page_path,
            rendered_page,
            source_path=(source_root / target) if source_root is not None else None,
            error_type=FrontendImplementationAuthoringError,
            boundary_label="frontend",
            allow_protected_shell_refresh=protected_shell_refresh,
        )
        test_content, test_blocks = merge_bounded_agentic_regions(
            test_path,
            rendered_test,
            source_path=(source_root / test_target) if source_root is not None else None,
            error_type=FrontendImplementationAuthoringError,
            boundary_label="frontend",
            allow_protected_shell_refresh=protected_shell_refresh,
        )
        page_path.write_text(page_content, encoding="utf-8")
        test_path.write_text(test_content, encoding="utf-8")
        for block in [*page_blocks, *test_blocks]:
            if block["status"] == "authoring-required":
                unresolved_blocks.append(
                    {
                        "page_id": str(page["page_id"]),
                        "path": target if block in page_blocks else test_target,
                        "block_id": block["block_id"],
                    }
                )
        page_records.append(
            {
                "page_id": str(page["page_id"]),
                "route": str(page["route"]),
                "path": target,
                "test_path": test_target,
                "source_sha256": str(page["source_sha256"]),
                "slice_ids": slice_ids,
                "status": (
                    "authoring-required"
                    if any(block["status"] == "authoring-required" for block in [*page_blocks, *test_blocks])
                    else "materialized"
                ),
                "shell_sha256": _sha256_bytes(agentic_shell_projection(page_content).encode("utf-8")),
                "content_sha256": _file_sha256(page_path),
                "test_shell_sha256": _sha256_bytes(agentic_shell_projection(test_content).encode("utf-8")),
                "test_content_sha256": _file_sha256(test_path),
                "agentic_blocks": {"page": page_blocks, "test": test_blocks},
            }
        )

    backend_freeze_after_authoring = _backend_freeze_fingerprint(output_dir)
    _assert_backend_freeze_unchanged(backend_freeze_before, backend_freeze_after_authoring)
    backend_immutability = {
        "status": "pass" if existing_wff_p3_backend else "not-applicable",
        "protected_roots": list(_BACKEND_FREEZE_ROOTS),
        "file_count": int(backend_freeze_after_authoring.get("file_count", 0) or 0),
        "before_digest": str(backend_freeze_before.get("content_digest") or ""),
        "after_digest": str(backend_freeze_after_authoring.get("content_digest") or ""),
        "claim": "WFF-P3 frontend authoring did not rewrite frozen backend service/test surfaces.",
    }

    authoring_status = "authoring-required" if unresolved_blocks else "materialized"
    authoring: dict[str, Any] = {
        "schema_version": FRONTEND_AUTHORING_SCHEMA,
        "mode": "complete-product-agentic-realization",
        "status": authoring_status,
        "implementation_decision_id": str(authority.get("decision_id") or ""),
        "implementation_decision_digest": str(authority.get("decision_digest") or ""),
        "ui_ia_contract_path": str(ui_path),
        "ui_ia_contract_sha256": ui_contract_sha256,
        "application": application_record,
        "consumer_e2e": e2e_record,
        "page_count": len(page_records),
        "pages": page_records,
        "unresolved_block_count": len(unresolved_blocks),
        "unresolved_blocks": unresolved_blocks,
        "semantic_authority": False,
        "runtime_evidence_refs": [],
        "trace_confirmed": False,
        "backend_immutability": backend_immutability,
        "target_binding_mode": target_binding_mode,
        "operating_product_maturity_questions": dict(OPERATING_PRODUCT_MATURITY_QUESTIONS),
        "boundary": (
            "Workflow owns exact source/decision bindings and protected boundaries. The Host Agent owns the complete "
            "product realization inside bounded @wff:agentic regions, including application composition, navigation, "
            "entry/session UX, human-facing state treatment, responsive behavior, accessibility realization, recovery, "
            "page composition and consumer E2E task evidence when those details are not frozen upstream. Realization-only refinements remain P3 "
            "implementation decisions / Authority Delta rather than forcing upstream rewrites."
        ),
        "claim_ceiling": (
            "This projection proves only current-decision-bound frontend product source realization. P3 completion still "
            "requires real Web/API/database runtime and consumer-operability evidence; it does not prove P4 acceptance, "
            "production readiness, owner sign-off, or UAT."
        ),
    }
    authoring["content_digest"] = canonical_digest(authoring)
    summary = {
        "artifact_kind": "phase3-impl-frontend-report",
        "quality_gate": "blocked" if unresolved_blocks else "pass",
        "contract_pack": {key: str(value) for key, value in contract_summary.items() if key.endswith("_path")},
        "root_summary": root_summary,
        "shared_summary": shared_summary,
        "web_summary": web_summary,
        "ui_ia_contract": str(ui_path),
        "authoring": authoring,
        "claim_ceiling": authoring["claim_ceiling"],
    }
    write_json(output_dir / "impl-frontend-report.json", summary)
    _update_implementation_bindings(
        output_dir=output_dir,
        authority=authority,
        authoring=authoring,
    )
    return summary
