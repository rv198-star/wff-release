#!/usr/bin/env python3
"""
Shared helpers for Phase-4 testing-validation scripts.
"""

from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from common.claim_ceiling_surface import (
    claim_ceiling_allows_phase4_validation_entry,
    claim_ceiling_blocks_ready,
    read_claim_ceiling_report,
)
from common.markdown_table_tools import (
    render_markdown_table as render_common_markdown_table,
    sanitize_markdown_table_cell,
)


VISUAL_EVIDENCE_SUFFIXES = {
    ".gif",
    ".jpeg",
    ".jpg",
    ".mp4",
    ".png",
    ".webm",
    ".webp",
}

UI_PRODUCT_REVIEW_SCHEMA = "wff.phase4-ui-product-review-request.v4"
UI_PRODUCT_REVIEW_EVIDENCE_TYPE = "agentic-ui-product-review"
UI_PRODUCT_REVIEW_DIMENSIONS = (
    "productness",
    "first-entry-navigation-and-task-continuity",
    "role-fidelity-and-least-privilege",
    "business-data-sufficiency",
    "interaction-affordance-and-task-efficiency",
    "project-language-alignment",
    "clean-first-use-and-context-recovery",
    "trust-history-and-provenance",
    "metadata-leakage",
    "composition-and-information-hierarchy",
    "business-language",
    "state-and-action-clarity",
    "desktop-mobile-usability",
    "accessibility-baseline",
)
UI_PRODUCT_REVIEW_RETURN_PATHS = {"p3-frontend-authoring", "p2-authority", "p3-authority-delta"}
OPEN_ENDED_MATURITY_REVIEW_SCHEMA = "wff.phase4-open-ended-maturity-review-request.v1"
OPEN_ENDED_MATURITY_REVIEW_EVIDENCE_TYPE = "agentic-open-ended-maturity-review"
OPEN_ENDED_MATURITY_PASS_SCORE = 80.0
OPEN_ENDED_MATURITY_BLOCKING_SEVERITIES = {"critical", "high"}
P3_REALIZATION_DECISIONS_FILENAME = "p3-realization-decisions.md"
P3_REALIZATION_DECISIONS_MARKER = "<!-- wff:p3-realization-decisions:v1 -->"
P3_REALIZATION_NO_MATERIAL_DECISIONS = (
    "No material realization decisions beyond frozen P1/P2 authority were recorded for this P3 decision."
)


def _ui_review_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _ui_review_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _ui_review_evidence_ref(phase3_root: Path, raw_path: str) -> tuple[str, Path | None]:
    value = str(raw_path or "").strip()
    if not value:
        return "", None
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (phase3_root / path).resolve()
    try:
        relative = resolved.relative_to(phase3_root.resolve()).as_posix()
    except ValueError:
        return value, None
    return relative, resolved if resolved.is_file() else None


def _ui_review_find_ia_contract(phase3_root: Path, expected_sha256: str) -> tuple[str, dict[str, Any]]:
    candidates = [
        phase3_root / "prototype-fallback" / "ui-ia-contract.json",
        phase3_root / "ui-ia-contract.json",
    ]
    authoring_report_path = phase3_root / "impl-frontend-report.json"
    authoring_report = load_json(authoring_report_path) if authoring_report_path.is_file() else {}
    authoring = authoring_report.get("authoring") if isinstance(authoring_report.get("authoring"), dict) else {}
    for raw in (authoring_report.get("ui_ia_contract"), authoring.get("ui_ia_contract_path")):
        if str(raw or "").strip():
            candidates.append(Path(str(raw)).expanduser())
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not resolved.is_file() or resolved.is_symlink():
            continue
        seen.add(resolved)
        if expected_sha256 and _ui_review_sha256(resolved) != expected_sha256:
            continue
        payload = load_json(resolved)
        if not payload:
            continue
        try:
            path_ref = resolved.relative_to(phase3_root.resolve()).as_posix()
        except ValueError:
            path_ref = str(resolved)
        return path_ref, payload
    return "", {}


def build_ui_product_review_request(*, phase3_root: Path) -> dict[str, Any]:
    phase3_root = phase3_root.resolve()
    runtime_path = phase3_root / "runtime-smoke-report.json"
    runtime = load_json(runtime_path) if runtime_path.is_file() else {}
    browser = runtime.get("frontend_browser_evidence") if isinstance(runtime.get("frontend_browser_evidence"), dict) else {}
    checks = runtime.get("checks") if isinstance(runtime.get("checks"), dict) else {}
    requested = bool(browser.get("requested")) or bool(checks.get("frontend_requested"))
    if not requested:
        return {
            "schema_version": UI_PRODUCT_REVIEW_SCHEMA,
            "status": "not-required",
            "review_required": False,
            "reason": "current Phase-3 root has no requested frontend browser evidence",
            "required_dimensions": list(UI_PRODUCT_REVIEW_DIMENSIONS),
            "creates_product_judgment": False,
        }

    identity = browser.get("authoring_identity") if isinstance(browser.get("authoring_identity"), dict) else {}
    failures: list[str] = []
    if str(runtime.get("verdict") or "") != "pass":
        failures.append("runtime-smoke-not-pass")
    if str(browser.get("status") or "") != "pass" or not bool(checks.get("frontend_browser_evidence_green")):
        failures.append("frontend-browser-evidence-not-pass")
    binding_identity = {
        "authoring_content_digest": str(identity.get("content_digest") or "").strip(),
        "implementation_decision_id": str(identity.get("decision_id") or "").strip(),
        "implementation_decision_digest": str(identity.get("decision_digest") or "").strip(),
        "ui_ia_contract_sha256": str(identity.get("ui_ia_contract_sha256") or "").strip(),
    }
    if not all(binding_identity.values()):
        failures.append("frontend-review-identity-incomplete")

    application = identity.get("application") if isinstance(identity.get("application"), dict) else {}
    application_binding = {
        "path": str(application.get("path") or "").strip(),
        "content_sha256": str(application.get("content_sha256") or "").strip(),
    }
    application_path = (phase3_root / application_binding["path"]).resolve() if application_binding["path"] else phase3_root
    try:
        application_path.relative_to(phase3_root)
    except ValueError:
        failures.append("frontend-review-application-source-foreign")
    else:
        if (
            not application_binding["path"]
            or not application_binding["content_sha256"]
            or not application_path.is_file()
            or application_path.is_symlink()
            or _ui_review_sha256(application_path) != application_binding["content_sha256"]
        ):
            failures.append("frontend-review-application-source-drift")

    pages = [
        {
            "page_id": str(row.get("page_id") or "").strip(),
            "route": str(row.get("route") or "").strip(),
            "source_path": str(row.get("path") or "").strip(),
            "content_sha256": str(row.get("content_sha256") or "").strip(),
            "slice_ids": [str(value) for value in ensure_list(row.get("slice_ids")) if str(value).strip()],
        }
        for row in ensure_list(identity.get("pages"))
        if isinstance(row, dict) and str(row.get("page_id") or "").strip() and str(row.get("route") or "").strip()
    ]
    if not pages:
        failures.append("frontend-review-pages-missing")
    for page in pages:
        source_path = str(page.get("source_path") or "").strip()
        expected_source_sha = str(page.get("content_sha256") or "").strip()
        resolved_source = (phase3_root / source_path).resolve() if source_path else phase3_root
        try:
            resolved_source.relative_to(phase3_root)
        except ValueError:
            failures.append(f"frontend-review-page-source-foreign:{source_path or '<missing>'}")
            continue
        if (
            not source_path
            or not expected_source_sha
            or not resolved_source.is_file()
            or resolved_source.is_symlink()
            or _ui_review_sha256(resolved_source) != expected_source_sha
        ):
            failures.append(f"frontend-review-page-source-drift:{page.get('page_id') or source_path or '<missing>'}")

    def verified_evidence(rows: Any, kind: str) -> list[dict[str, str]]:
        verified: list[dict[str, str]] = []
        for raw in ensure_list(rows):
            if not isinstance(raw, dict):
                continue
            path_ref, resolved = _ui_review_evidence_ref(phase3_root, str(raw.get("path") or ""))
            expected = str(raw.get("sha256") or "").strip()
            if resolved is None or not expected or _ui_review_sha256(resolved) != expected:
                failures.append(f"frontend-review-{kind}-invalid:{path_ref or '<missing>'}")
                continue
            verified.append({"path": path_ref, "sha256": expected})
        return verified

    review_screenshot_rows = browser.get("review_screenshots") if isinstance(browser.get("review_screenshots"), list) else []
    screenshots = verified_evidence(review_screenshot_rows or browser.get("screenshots"), "screenshot")
    traces = verified_evidence(browser.get("browser_traces"), "trace")
    if len(screenshots) < len(pages) * 2:
        failures.append("frontend-review-desktop-mobile-screenshots-incomplete")
    if not traces:
        failures.append("frontend-review-traces-missing")
    project_names = {
        str(value)
        for value in ensure_list((browser.get("playwright") if isinstance(browser.get("playwright"), dict) else {}).get("project_names"))
        if str(value).strip()
    }
    if not {"desktop-chromium", "mobile-chromium"}.issubset(project_names):
        failures.append("frontend-review-desktop-mobile-projects-incomplete")

    accessibility = browser.get("accessibility_evidence") if isinstance(browser.get("accessibility_evidence"), dict) else {}
    accessibility_checks = {
        str(value).strip()
        for value in ensure_list(accessibility.get("checks"))
        if str(value).strip()
    }
    required_accessibility_checks = {
        "semantic-main-and-heading",
        "interactive-accessible-name",
        "keyboard-focus-target",
        "measured-text-contrast",
        "viewport-horizontal-overflow",
        "desktop-mobile-execution",
    }
    accessibility_route_spec = str(accessibility.get("route_spec_path") or "").strip()
    accessibility_route_sha = str(accessibility.get("route_spec_sha256") or "").strip()
    browser_route_spec = str(browser.get("route_spec_path") or "").strip()
    browser_route_sha = str(browser.get("route_spec_sha256") or "").strip()
    accessibility_path = (phase3_root / accessibility_route_spec).resolve() if accessibility_route_spec else phase3_root
    accessibility_valid = bool(
        str(accessibility.get("status") or "").strip() == "pass"
        and required_accessibility_checks.issubset(accessibility_checks)
        and accessibility_route_spec
        and accessibility_route_spec == browser_route_spec
        and accessibility_route_sha
        and accessibility_route_sha == browser_route_sha
    )
    if accessibility_valid:
        try:
            accessibility_path.relative_to(phase3_root)
        except ValueError:
            accessibility_valid = False
        else:
            accessibility_valid = bool(
                accessibility_path.is_file()
                and not accessibility_path.is_symlink()
                and _ui_review_sha256(accessibility_path) == accessibility_route_sha
            )
    if not accessibility_valid:
        failures.append("frontend-review-accessibility-evidence-missing-or-stale")

    product_access_requirements = (
        browser.get("product_access_requirements")
        if isinstance(browser.get("product_access_requirements"), dict)
        else identity.get("product_access_requirements")
        if isinstance(identity.get("product_access_requirements"), dict)
        else {}
    )
    business_data_requirements = (
        browser.get("business_data_requirements")
        if isinstance(browser.get("business_data_requirements"), dict)
        else identity.get("business_data_requirements")
        if isinstance(identity.get("business_data_requirements"), dict)
        else {}
    )
    project_language_requirements = (
        browser.get("project_language_requirements")
        if isinstance(browser.get("project_language_requirements"), dict)
        else identity.get("project_language_requirements")
        if isinstance(identity.get("project_language_requirements"), dict)
        else {}
    )
    auth_runtime_proof = browser.get("auth_runtime_proof") if isinstance(browser.get("auth_runtime_proof"), dict) else {}
    if bool(product_access_requirements.get("requires_authenticated_session")):
        consumer_page_coverage = (
            browser.get("consumer_page_screenshot_coverage")
            if isinstance(browser.get("consumer_page_screenshot_coverage"), dict)
            else {}
        )
        if not review_screenshot_rows or str(consumer_page_coverage.get("status") or "") != "pass":
            failures.append("frontend-review-post-sign-in-page-screenshots-incomplete")
        if str(auth_runtime_proof.get("status") or "") != "pass":
            failures.append("frontend-review-authenticated-session-evidence-missing")
        compatibility_mode = str(auth_runtime_proof.get("backend_auth_compatibility_mode") or "").strip()
        if compatibility_mode == "frozen-phase3-header":
            if str(auth_runtime_proof.get("normal_api_auth_transport") or "") != "bff-session-to-frozen-phase3-header":
                failures.append("frontend-review-frozen-backend-auth-transport-mismatch")
            if int(auth_runtime_proof.get("frozen_backend_auth_context_request_count", 0) or 0) <= 0:
                failures.append("frontend-review-frozen-backend-auth-evidence-missing")
        else:
            if str(auth_runtime_proof.get("normal_api_auth_transport") or "") != "authorization-bearer":
                failures.append("frontend-review-normal-auth-transport-not-bearer")
            if int(auth_runtime_proof.get("authorized_api_request_count", 0) or 0) <= 0:
                failures.append("frontend-review-authorized-business-api-evidence-missing")
    if int(auth_runtime_proof.get("browser_authorization_header_request_count", 0) or 0) > 0:
        failures.append("frontend-review-browser-authorization-shortcut-observed")
    if int(auth_runtime_proof.get("phase3_auth_context_request_count", 0) or 0) > 0:
        failures.append("frontend-review-phase3-auth-shortcut-observed")

    interaction_coverage = browser.get("interaction_coverage") if isinstance(browser.get("interaction_coverage"), dict) else {}
    terminal_qualification = (
        product_access_requirements.get("terminal_role_qualification")
        if isinstance(product_access_requirements.get("terminal_role_qualification"), dict)
        else {}
    )
    if bool(terminal_qualification.get("independent_persona_required")):
        expected_personas = [
            row
            for row in ensure_list(product_access_requirements.get("test_personas"))
            if isinstance(row, dict) and str(row.get("persona_id") or "").strip()
        ]
        if str(terminal_qualification.get("status") or "") != "sufficient":
            failures.append("frontend-review-terminal-role-authority-insufficient")
        if bool(terminal_qualification.get("super_role_qualifies_terminal_roles")):
            failures.append("frontend-review-super-role-terminal-qualification-forbidden")
        if int(interaction_coverage.get("covered_terminal_role_persona_count", 0) or 0) != len(expected_personas):
            failures.append("frontend-review-terminal-role-persona-evidence-incomplete")
    if bool(business_data_requirements.get("requires_business_data_discovery")):
        if str(business_data_requirements.get("read_model_status") or "") != "sufficient":
            failures.append("frontend-review-business-read-model-authority-insufficient")
    if bool(business_data_requirements.get("clean_first_use_required")):
        clean_database_evidence = (
            browser.get("clean_first_use_database_evidence")
            if isinstance(browser.get("clean_first_use_database_evidence"), dict)
            else {}
        )
        if str(clean_database_evidence.get("status") or "") != "pass" or int(
            clean_database_evidence.get("business_row_count", -1) or 0
        ) != 0:
            failures.append("frontend-review-clean-first-use-database-not-empty")
        if int(interaction_coverage.get("clean_first_use_count", 0) or 0) <= 0:
            failures.append("frontend-review-clean-first-use-evidence-missing")
    if ensure_list(business_data_requirements.get("manual_identifier_inputs")):
        failures.append("frontend-review-manual-internal-identifier-contract-present")
    if bool(project_language_requirements.get("consumer_copy_must_match_project_locale")) and not str(
        project_language_requirements.get("consumer_locale") or ""
    ).strip():
        failures.append("frontend-review-project-language-contract-missing")
    spec_sha_by_path = {
        str(row.get("path") or "").strip(): str(row.get("sha256") or "").strip()
        for row in ensure_list(interaction_coverage.get("specs"))
        if isinstance(row, dict) and str(row.get("path") or "").strip()
    }
    consumer_journeys: list[dict[str, str]] = []
    for raw in ensure_list(interaction_coverage.get("consumer_journeys")):
        if not isinstance(raw, dict):
            continue
        row = {
            "journey_id": str(raw.get("journey_id") or "").strip(),
            "entry_route": str(raw.get("entry_route") or "").strip(),
            "outcome": str(raw.get("outcome") or "").strip(),
            "path": str(raw.get("path") or "").strip(),
        }
        expected_sha = spec_sha_by_path.get(row["path"], "")
        journey_path = (phase3_root / row["path"]).resolve() if row["path"] else phase3_root
        try:
            journey_path.relative_to(phase3_root)
        except ValueError:
            failures.append(f"frontend-review-consumer-journey-foreign:{row['journey_id'] or '<missing>'}")
            continue
        if (
            not all((row["journey_id"], row["entry_route"], row["outcome"], row["path"], expected_sha))
            or not journey_path.is_file()
            or journey_path.is_symlink()
            or _ui_review_sha256(journey_path) != expected_sha
        ):
            failures.append(f"frontend-review-consumer-journey-invalid:{row['journey_id'] or '<missing>'}")
            continue
        consumer_journeys.append({**row, "sha256": expected_sha})
    if not consumer_journeys:
        failures.append("frontend-review-consumer-journey-missing")

    ui_path, ui_contract = _ui_review_find_ia_contract(phase3_root, binding_identity["ui_ia_contract_sha256"])
    if not ui_contract:
        failures.append("frontend-review-ui-ia-contract-unavailable")
    ui_pages = {
        str(row.get("page_id") or "").strip(): row
        for row in ensure_list(ui_contract.get("pages"))
        if isinstance(row, dict) and str(row.get("page_id") or "").strip()
    }
    review_surfaces: list[dict[str, Any]] = []
    for page in pages:
        ui_page = ui_pages.get(page["page_id"], {})
        review_surfaces.append(
            {
                **page,
                "page_title": str(ui_page.get("page_title") or ui_page.get("page_name") or page["page_id"]).strip(),
                "page_blueprint_type": str(ui_page.get("page_blueprint_type") or "").strip(),
                "primary_work_region": str(ui_page.get("primary_work_region") or "").strip(),
                "dominant_component_pattern": str(ui_page.get("dominant_component_pattern") or "").strip(),
                "action_model": str(ui_page.get("action_model") or "").strip(),
                "required_regions": [str(value) for value in ensure_list(ui_page.get("required_regions")) if str(value).strip()],
                "compiled_interaction_ids": [
                    str(row.get("interaction_id"))
                    for row in ensure_list(ui_page.get("compiled_interactions"))
                    if isinstance(row, dict) and str(row.get("interaction_id") or "").strip()
                ],
            }
        )

    binding = {
        **binding_identity,
        "runtime_smoke_report_sha256": _ui_review_sha256(runtime_path) if runtime_path.is_file() else "",
        "application": application_binding,
        "screenshots": screenshots,
        "browser_traces": traces,
        "accessibility_evidence": accessibility if accessibility_valid else {},
        "product_access_requirements": product_access_requirements,
        "business_data_requirements": business_data_requirements,
        "project_language_requirements": project_language_requirements,
        "auth_runtime_proof": auth_runtime_proof,
        "interaction_coverage": interaction_coverage,
        "consumer_journeys": consumer_journeys,
        "pages": pages,
    }
    request_id = _ui_review_digest({
        "schema_version": UI_PRODUCT_REVIEW_SCHEMA,
        "binding": binding,
        "required_dimensions": list(UI_PRODUCT_REVIEW_DIMENSIONS),
    }) if not failures else ""
    questions = {
        "productness": "Does the rendered surface behave and read like a real product interface rather than a design demo, debug shell, contract viewer, API explorer, or generic CRUD renderer?",
        "first-entry-navigation-and-task-continuity": "From the bound normal entry route, can the intended consumer understand the product and current task, enter the required role/session through a product-facing path when applicable, navigate the core journey, preserve business context, recover from navigation mistakes, and reach the bound meaningful outcome without engineering-only route knowledge or storage injection?",
        "role-fidelity-and-least-privilege": "Do independently qualified terminal personas see only the pages, actions, and business data supported by their accepted role authority, with cross-role denial/recovery behavior clear and no super-role account standing in for terminal-role qualification?",
        "business-data-sufficiency": "Can users discover, select, inspect, and continue work from real business records through accepted read models, with enough role-appropriate business context to make the next decision rather than merely recognize a record, instead of relying on empty shells, fixtures, manually typed internal identifiers, or hidden engineering references?",
        "interaction-affordance-and-task-efficiency": "Do concrete controls and task flows match accepted business/data semantics, realistic usage frequency, and plausible working-set size: bounded choices are constrained, multi-value inputs are structured, existing context/defaults/recent values are reused where authorized, user-supplied evidence remains real user input, and repeated/high-frequency work uses search/filter/sort/grouping/recency/prioritization/bulk behavior when the task actually justifies it without imposing a fixed widget quota?",
        "project-language-alignment": "Does consumer-facing copy follow the project/default consumer locale while preserving canonical technical identifiers only where users do not consume them as product language? Full i18n is not required unless separately authorized.",
        "clean-first-use-and-context-recovery": "Starting from an empty business-data state, can a real role enter through the product, create the first valid business object, discover/read it through the product, reload or re-enter, recover context, and continue without seeded business fixtures or manually supplied internal identifiers?",
        "trust-history-and-provenance": "Where the task depends on prior work, review, audit, privacy, evidence, or provisional truth, does the product expose enough current-state plus history/change/provenance/trust context for a returning user to understand what happened and what may safely or usefully happen next?",
        "metadata-leakage": "Are internal goals, constraints, design rationale, blueprint/region/operation/binding/Agent/authority metadata kept out of product copy unless a real user task explicitly needs the explanation?",
        "composition-and-information-hierarchy": "Does each page use page-specific business composition and a useful information hierarchy rather than a generic shell with renamed labels?",
        "business-language": "Does user-facing language use business/task terms instead of implementation, API, contract, architecture, or methodology vocabulary?",
        "state-and-action-clarity": "Are current state, primary actions, validation, success/loading/empty/error/retry/denied feedback, and next steps clear for the user task?",
        "desktop-mobile-usability": "Do the retained desktop and mobile views preserve usable hierarchy, actions, content density, and feedback without obvious viewport-specific breakage?",
        "accessibility-baseline": "Does the current factual evidence support keyboard/focus operation, semantic structure, accessible names/labels, and usable contrast/mobile interaction? Mark this dimension review-bound rather than pass when those facts are not evidenced.",
    }
    return {
        "schema_version": UI_PRODUCT_REVIEW_SCHEMA,
        "review_layer": "structured-qualification-review",
        "review_round": 2,
        "status": "review-required" if not failures else "blocked",
        "review_required": True,
        "review_request_id": request_id,
        "current_binding": binding,
        "runtime_smoke_report": "runtime-smoke-report.json" if runtime_path.is_file() else "",
        "ui_ia_contract_path": ui_path,
        "review_surfaces": review_surfaces,
        "required_dimensions": [{"dimension": dimension, "question": questions[dimension]} for dimension in UI_PRODUCT_REVIEW_DIMENSIONS],
        "review_instruction": (
            "Run only after the first-round Open-ended Maturity Review has been completed, but do not provide that review's "
            "score, findings, summary, or verdict to this reviewer. Evaluate only the current bound product evidence against "
            "the fixed qualification dimensions so the structured result remains independently comparable."
        ),
        "review_response_contract": {
            "evidence_type": UI_PRODUCT_REVIEW_EVIDENCE_TYPE,
            "required_fields": ["review_request_id", "reviewer", "status", "reviewed_page_ids", "assessments", "evidence_paths"],
            "finding_required_on_fail": True,
            "allowed_return_paths": sorted(UI_PRODUCT_REVIEW_RETURN_PATHS),
            "fixed_dimensions": True,
            "must_not_receive_open_ended_review_output": True,
            "human_signoff_created": False,
        },
        "blocking_reasons": failures,
        "creates_product_judgment": False,
        "claim_ceiling": "This request packages current P3 application/page/browser and consumer-journey evidence for independent Agentic UI/Product Review; AI review remains supporting qualification evidence and cannot replace the bound consumer journey itself.",
    }


def build_open_ended_maturity_review_request(*, phase3_root: Path) -> dict[str, Any]:
    """Build the first-round open-ended product maturity review request.

    This request intentionally contains no fixed scoring dimensions and no structured-review
    score/findings. It is identity-bound to the same current rendered evidence as the later
    structured qualification review, but asks the reviewer to discover problems freely first.
    """
    structured = build_ui_product_review_request(phase3_root=phase3_root)
    if not bool(structured.get("review_required")):
        return {
            "schema_version": OPEN_ENDED_MATURITY_REVIEW_SCHEMA,
            "status": str(structured.get("status") or "not-required"),
            "review_required": False,
            "reason": str(structured.get("reason") or "current Phase-3 root has no requested frontend browser evidence"),
            "creates_product_judgment": False,
        }

    failures = [str(value) for value in ensure_list(structured.get("blocking_reasons")) if str(value).strip()]
    current_binding = dict(structured.get("current_binding") or {})
    surfaces = [
        {
            "page_id": str(row.get("page_id") or "").strip(),
            "route": str(row.get("route") or "").strip(),
            "page_title": str(row.get("page_title") or row.get("page_id") or "").strip(),
            "source_path": str(row.get("source_path") or "").strip(),
        }
        for row in ensure_list(structured.get("review_surfaces"))
        if isinstance(row, dict) and str(row.get("page_id") or "").strip()
    ]
    request_binding = {
        "current_binding": current_binding,
        "review_surfaces": surfaces,
        "runtime_smoke_report": str(structured.get("runtime_smoke_report") or ""),
        "ui_ia_contract_path": str(structured.get("ui_ia_contract_path") or ""),
    }
    request_id = _ui_review_digest({
        "schema_version": OPEN_ENDED_MATURITY_REVIEW_SCHEMA,
        "binding": request_binding,
        "pass_score_floor": OPEN_ENDED_MATURITY_PASS_SCORE,
        "blocking_severities": sorted(OPEN_ENDED_MATURITY_BLOCKING_SEVERITIES),
        "fixed_dimensions": False,
    }) if not failures else ""
    return {
        "schema_version": OPEN_ENDED_MATURITY_REVIEW_SCHEMA,
        "review_layer": "open-ended-maturity-review",
        "review_round": 1,
        "status": "review-required" if not failures else "blocked",
        "review_required": True,
        "review_request_id": request_id,
        "current_binding": current_binding,
        "runtime_smoke_report": str(structured.get("runtime_smoke_report") or ""),
        "ui_ia_contract_path": str(structured.get("ui_ia_contract_path") or ""),
        "review_surfaces": surfaces,
        "review_instruction": (
            "Treat the current rendered frontend as a formal product about to be handed to real terminal users. "
            "Do not use a predefined dimension checklist and do not infer quality from test/browser pass status. "
            "Freely discover any product incompleteness, task break, confusing interaction, missing business context, "
            "unrecoverable state, fake/synthetic behavior, engineering/demo residue, weak information architecture, "
            "or other reason the product would not be ready for real use. Record concrete findings with evidence first; "
            "only after the findings are complete assign one holistic maturity score."
        ),
        "review_response_contract": {
            "evidence_type": OPEN_ENDED_MATURITY_REVIEW_EVIDENCE_TYPE,
            "required_fields": [
                "review_request_id",
                "reviewer",
                "status",
                "reviewed_page_ids",
                "holistic_score",
                "summary",
                "findings",
                "evidence_paths",
            ],
            "fixed_dimensions": False,
            "pass_score_floor": OPEN_ENDED_MATURITY_PASS_SCORE,
            "blocking_severities": sorted(OPEN_ENDED_MATURITY_BLOCKING_SEVERITIES),
            "allowed_return_paths": sorted(UI_PRODUCT_REVIEW_RETURN_PATHS),
            "human_signoff_created": False,
        },
        "blocking_reasons": failures,
        "creates_product_judgment": False,
        "claim_ceiling": (
            "First-round open-ended maturity review request only. It deliberately excludes the later structured-review "
            "rubric, score, assessments and findings so product-maturity discovery is not anchored by qualification scoring."
        ),
    }


def validate_open_ended_maturity_review(
    entry: dict[str, Any],
    *,
    review_request: dict[str, Any],
) -> tuple[bool, list[str], float | None, list[dict[str, Any]]]:
    errors: list[str] = []
    if str(review_request.get("status") or "") != "review-required":
        errors.append("current-open-ended-maturity-review-request-not-ready")
    if str(entry.get("review_request_id") or "").strip() != str(review_request.get("review_request_id") or "").strip():
        errors.append("open-ended-maturity-review-request-id-mismatch")
    if not str(entry.get("reviewer") or "").strip():
        errors.append("open-ended-maturity-review-reviewer-missing")
    status = str(entry.get("status") or "").strip().lower()
    if status not in {"pass", "fail", "review-bound"}:
        errors.append("open-ended-maturity-review-status-invalid")
    if ensure_list(entry.get("assessments")):
        errors.append("open-ended-maturity-review-fixed-assessments-forbidden")

    page_ids = {
        str(row.get("page_id") or "").strip()
        for row in ensure_list(review_request.get("review_surfaces"))
        if isinstance(row, dict) and str(row.get("page_id") or "").strip()
    }
    reviewed_page_ids = {str(value).strip() for value in ensure_list(entry.get("reviewed_page_ids")) if str(value).strip()}
    if page_ids and not page_ids.issubset(reviewed_page_ids):
        errors.append("open-ended-maturity-review-page-coverage-incomplete")

    score: float | None = None
    try:
        score = float(entry.get("holistic_score"))
    except (TypeError, ValueError):
        errors.append("open-ended-maturity-review-score-invalid")
    else:
        if score < 0 or score > 100:
            errors.append("open-ended-maturity-review-score-invalid")
    if not str(entry.get("summary") or "").strip():
        errors.append("open-ended-maturity-review-summary-missing")

    binding = review_request.get("current_binding") if isinstance(review_request.get("current_binding"), dict) else {}
    current_evidence = {
        str(row.get("path") or "")
        for key in ("screenshots", "browser_traces")
        for row in ensure_list(binding.get(key))
        if isinstance(row, dict) and str(row.get("path") or "").strip()
    }
    supplied_evidence = {str(value).strip() for value in ensure_list(entry.get("evidence_paths")) if str(value).strip()}
    if current_evidence and not (current_evidence & supplied_evidence):
        errors.append("open-ended-maturity-review-current-visual-evidence-missing")

    findings: list[dict[str, Any]] = []
    for raw in ensure_list(entry.get("findings")):
        if not isinstance(raw, dict):
            continue
        finding = {
            key: str(raw.get(key) or "").strip()
            for key in ("finding_id", "category", "severity", "page_id", "evidence_ref", "observation", "user_impact", "return_path")
        }
        finding["severity"] = finding["severity"].lower()
        if not all(finding.values()):
            errors.append("open-ended-maturity-review-finding-incomplete")
            continue
        if finding["page_id"] not in page_ids and finding["page_id"] != "__product__":
            errors.append(f"open-ended-maturity-review-finding-page-foreign:{finding['finding_id']}")
        if finding["evidence_ref"] not in current_evidence:
            errors.append(f"open-ended-maturity-review-finding-evidence-foreign:{finding['finding_id']}")
        if finding["return_path"] not in UI_PRODUCT_REVIEW_RETURN_PATHS:
            errors.append(f"open-ended-maturity-review-return-path-invalid:{finding['finding_id']}")
        if finding["severity"] not in {"critical", "high", "medium", "low"}:
            errors.append(f"open-ended-maturity-review-severity-invalid:{finding['finding_id']}")
        findings.append(finding)

    blocking_findings = [row for row in findings if row["severity"] in OPEN_ENDED_MATURITY_BLOCKING_SEVERITIES]
    if status == "pass":
        if score is not None and score < OPEN_ENDED_MATURITY_PASS_SCORE:
            errors.append("open-ended-maturity-review-pass-score-below-floor")
        if blocking_findings:
            errors.append("open-ended-maturity-review-pass-has-blocking-findings")
    if status == "fail":
        if not findings:
            errors.append("open-ended-maturity-review-fail-requires-finding")
        if score is not None and score >= OPEN_ENDED_MATURITY_PASS_SCORE and not blocking_findings:
            errors.append("open-ended-maturity-review-fail-requires-low-score-or-blocking-finding")
    if status == "review-bound" and not str(entry.get("review_bound_reason") or "").strip():
        errors.append("open-ended-maturity-review-bound-reason-missing")
    return not errors, errors, score, findings


def validate_agentic_ui_product_review(
    entry: dict[str, Any],
    *,
    review_request: dict[str, Any],
) -> tuple[bool, list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[str] = []
    if str(review_request.get("status") or "") != "review-required":
        errors.append("current-ui-product-review-request-not-ready")
    if str(entry.get("review_request_id") or "").strip() != str(review_request.get("review_request_id") or "").strip():
        errors.append("ui-product-review-request-id-mismatch")
    if not str(entry.get("reviewer") or "").strip():
        errors.append("ui-product-review-reviewer-missing")
    status = str(entry.get("status") or "").strip().lower()
    if status not in {"pass", "fail", "review-bound"}:
        errors.append("ui-product-review-status-invalid")

    page_ids = {
        str(row.get("page_id") or "").strip()
        for row in ensure_list(review_request.get("review_surfaces"))
        if isinstance(row, dict) and str(row.get("page_id") or "").strip()
    }
    reviewed_page_ids = {str(value).strip() for value in ensure_list(entry.get("reviewed_page_ids")) if str(value).strip()}
    if page_ids and not page_ids.issubset(reviewed_page_ids):
        errors.append("ui-product-review-page-coverage-incomplete")

    assessments: list[dict[str, Any]] = []
    by_dimension: dict[str, dict[str, Any]] = {}
    for raw in ensure_list(entry.get("assessments")):
        if not isinstance(raw, dict):
            continue
        dimension = str(raw.get("dimension") or "").strip()
        if dimension not in UI_PRODUCT_REVIEW_DIMENSIONS or dimension in by_dimension:
            continue
        assessment = {
            "dimension": dimension,
            "status": str(raw.get("status") or "").strip().lower(),
            "rationale": str(raw.get("rationale") or "").strip(),
        }
        assessments.append(assessment)
        by_dimension[dimension] = assessment
    missing = [dimension for dimension in UI_PRODUCT_REVIEW_DIMENSIONS if dimension not in by_dimension]
    if missing:
        errors.append("ui-product-review-dimensions-missing:" + ",".join(missing))
    for dimension, assessment in by_dimension.items():
        if assessment["status"] not in {"pass", "fail", "review-bound"} or not assessment["rationale"]:
            errors.append(f"ui-product-review-assessment-invalid:{dimension}")

    binding = review_request.get("current_binding") if isinstance(review_request.get("current_binding"), dict) else {}
    current_evidence = {
        str(row.get("path") or "")
        for key in ("screenshots", "browser_traces")
        for row in ensure_list(binding.get(key))
        if isinstance(row, dict) and str(row.get("path") or "").strip()
    }
    supplied_evidence = {str(value).strip() for value in ensure_list(entry.get("evidence_paths")) if str(value).strip()}
    if current_evidence and not (current_evidence & supplied_evidence):
        errors.append("ui-product-review-current-visual-evidence-missing")

    findings: list[dict[str, Any]] = []
    for raw in ensure_list(entry.get("findings")):
        if not isinstance(raw, dict):
            continue
        finding = {
            key: str(raw.get(key) or "").strip()
            for key in ("finding_id", "category", "severity", "page_id", "evidence_ref", "observation", "user_impact", "return_path")
        }
        finding["severity"] = finding["severity"].lower()
        if not all(finding.values()):
            errors.append("ui-product-review-finding-incomplete")
            continue
        if finding["page_id"] not in page_ids:
            errors.append(f"ui-product-review-finding-page-foreign:{finding['finding_id']}")
        if finding["evidence_ref"] not in current_evidence:
            errors.append(f"ui-product-review-finding-evidence-foreign:{finding['finding_id']}")
        if finding["return_path"] not in UI_PRODUCT_REVIEW_RETURN_PATHS:
            errors.append(f"ui-product-review-return-path-invalid:{finding['finding_id']}")
        findings.append(finding)

    assessment_statuses = {row["status"] for row in assessments}
    if status == "pass" and assessment_statuses != {"pass"}:
        errors.append("ui-product-review-pass-requires-all-dimensions-pass")
    if status == "fail" and ("fail" not in assessment_statuses or not findings):
        errors.append("ui-product-review-fail-requires-failed-dimension-and-finding")
    if status == "review-bound" and "review-bound" not in assessment_statuses:
        errors.append("ui-product-review-bound-requires-review-bound-dimension")
    return not errors, errors, assessments, findings


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def stable_suffix(raw: str) -> str:
    text = raw.strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if text:
        return text
    digest = hashlib.sha1(str(raw or "").encode("utf-8")).hexdigest()[:10].upper()
    return f"U-{digest}" if digest else "UNKNOWN"


def compact_token(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", raw.lower())


def extract_phase3_surface_markers_from_text(text: str) -> list[str]:
    markers = re.findall(r"data-phase3-surface\s*=\s*[\"']([^\"']+)[\"']", text)
    return dedupe_preserve_order(str(marker).strip() for marker in markers if str(marker).strip())


def extract_phase3_surface_markers_from_file(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    return extract_phase3_surface_markers_from_text(path.read_text(encoding="utf-8"))


def api_id_for_operation(operation_id: str) -> str:
    return f"API-{stable_suffix(operation_id)}"


def prefixed_id(prefix: str, raw: str) -> str:
    return f"{prefix}-{stable_suffix(raw)}"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def discover_phase3_trace_registry_path(phase3_root: Path) -> Path:
    for name in ("phase-3-trace-registry-final.json", "phase3-trace-registry-final.json"):
        path = phase3_root / name
        if path.exists() and path.is_file():
            return path
    return phase3_root / "phase-3-trace-registry-final.json"


def _runtime_evidence_path(phase3_root: Path, raw_path: str) -> Path:
    path = Path(str(raw_path or "").strip())
    return path if path.is_absolute() else phase3_root / path


def _load_runtime_evidence_report(path: Path) -> tuple[dict[str, Any] | None, str]:
    if path.suffix.lower() != ".json":
        return None, "runtime-evidence-ref-not-json"
    if not path.exists() or not path.is_file():
        return None, "runtime-evidence-ref-missing"
    try:
        return load_json(path), ""
    except (OSError, ValueError, json.JSONDecodeError):
        return None, "runtime-evidence-ref-malformed"


def _current_s4_runtime_evidence_is_pass(payload: dict[str, Any]) -> bool:
    explicit = str(payload.get("overall_quality_gate") or payload.get("verdict") or payload.get("status") or "").strip().lower()
    if explicit in {"pass", "passed", "complete", "completed"}:
        return True
    s4_a = payload.get("s4_a") if isinstance(payload.get("s4_a"), dict) else {}
    s4_b = payload.get("s4_b") if isinstance(payload.get("s4_b"), dict) else {}
    s4_c = payload.get("s4_c") if isinstance(payload.get("s4_c"), dict) else {}
    readiness = s4_c.get("runtime_readiness") if isinstance(s4_c.get("runtime_readiness"), dict) else {}
    route_count = int(readiness.get("route_count", 0) or 0)
    ready_count = int(readiness.get("ready_operation_count", 0) or 0)
    missing = [str(value) for value in ensure_list(readiness.get("missing_operation_ids")) if str(value).strip()]
    return bool(
        str(s4_a.get("typecheck") or "").lower() == "pass"
        and str(s4_a.get("build") or "").lower() == "pass"
        and str(s4_b.get("status") or "").lower() == "pass"
        and str(s4_c.get("migration") or "").lower() == "pass"
        and route_count > 0
        and ready_count == route_count
        and not missing
    )


def _load_p3_realization_decisions_summary(
    *,
    phase3_root: Path,
    authority: dict[str, Any],
    delta: dict[str, Any],
) -> dict[str, Any]:
    metadata = load_json_if_exists(phase3_root / "phase3-run-metadata.json") or {}
    binding_path = phase3_root / ".phase3-evidence" / "p3-realization-decisions-binding.json"
    binding = load_json_if_exists(binding_path) or {}
    if binding:
        raw_path = str(binding.get("path") or "").strip()
        root_relative = str(binding.get("project_artifact_root_relative") or "").strip()
        if not raw_path or Path(raw_path).is_absolute() or not root_relative or Path(root_relative).is_absolute():
            path = (phase3_root / P3_REALIZATION_DECISIONS_FILENAME).resolve()
        else:
            path = (phase3_root / root_relative / raw_path).resolve()
    else:
        raw_path = str(metadata.get("p3_realization_decisions_path") or "").strip()
        if raw_path:
            path = Path(raw_path).expanduser()
            if not path.is_absolute():
                project_root = str(metadata.get("project_artifact_root") or "").strip()
                base = Path(project_root).expanduser() if project_root else phase3_root
                path = base / path
            path = path.resolve()
        else:
            path = (phase3_root / P3_REALIZATION_DECISIONS_FILENAME).resolve()

    errors: list[str] = []
    if not path.is_file() or path.is_symlink():
        return {
            "status": "missing",
            "valid": False,
            "path": str(path),
            "errors": ["p3-realization-decisions-missing"],
        }
    text = path.read_text(encoding="utf-8")
    if P3_REALIZATION_DECISIONS_MARKER not in text:
        errors.append("schema-marker-missing")
    decision_id = str(authority.get("decision_id") or delta.get("decision_id") or "").strip()
    decision_digest = str(authority.get("decision_digest") or delta.get("decision_digest") or "").strip()
    ledger_digest = str(delta.get("content_digest") or "").strip()
    content_sha256 = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    if binding:
        if Path(str(binding.get("path") or "")).is_absolute() or Path(str(binding.get("project_artifact_root_relative") or "")).is_absolute():
            errors.append("binding-path-not-portable")
        if str(binding.get("status") or "") != "bound":
            errors.append("binding-status-invalid")
        if str(binding.get("content_sha256") or "") != content_sha256:
            errors.append("binding-content-sha256-mismatch")
        if str(binding.get("p3_decision_id") or "") != decision_id:
            errors.append("binding-decision-id-mismatch")
        if str(binding.get("p3_decision_digest") or "") != decision_digest:
            errors.append("binding-decision-digest-mismatch")
        if str(binding.get("authority_delta_content_digest") or "") != ledger_digest:
            errors.append("binding-authority-delta-digest-mismatch")
        if binding.get("upstream_reconciled") is not False:
            errors.append("binding-upstream-reconciliation-invalid")
    else:
        errors.append("p3-realization-decisions-binding-missing")
    for label, expected in (
        ("P3 implementation decision id", decision_id),
        ("P3 implementation decision digest", decision_digest),
        ("Authority Delta content digest", ledger_digest),
    ):
        if not expected or not re.search(rf"^- {re.escape(label)}: `{re.escape(expected)}`$", text, flags=re.MULTILINE):
            errors.append(f"metadata-mismatch:{label}")
    for exact in (
        "- upstream_reconciled: `false`",
        "- PRD backfill: `not-performed`",
        "- ESP backfill: `not-performed`",
    ):
        if exact not in text:
            errors.append(f"boundary-missing:{exact.split(':', 1)[0].lstrip('- ')}")
    records = [row for row in ensure_list(delta.get("records")) if isinstance(row, dict)]
    if not records:
        if P3_REALIZATION_NO_MATERIAL_DECISIONS not in text:
            errors.append("no-material-decisions-declaration-missing")
    else:
        for row in records:
            delta_id = str(row.get("delta_id") or "").strip()
            if not delta_id:
                errors.append("delta-id-missing")
                continue
            if f"`{delta_id}`" not in text:
                errors.append(f"authority-delta-not-projected:{delta_id}")
    return {
        "status": "pass" if not errors else "blocked",
        "valid": not errors,
        "path": str(path),
        "content_sha256": content_sha256,
        "binding_path": str(binding_path),
        "record_count": len(records),
        "errors": errors,
    }


def load_phase3_current_closure_summary(phase3_root: Path) -> dict[str, Any]:
    authority_path = phase3_root / "p3-agentic-implementation-authority.json"
    application_path = phase3_root / "p3-agentic-implementation-application-receipt.json"
    exact_path = phase3_root / "p3-exact-realization-binding-ledger.json"
    delta_path = phase3_root / ".phase3-evidence" / "p3-authority-delta-ledger.json"
    bindings_path = phase3_root / "implementation-bindings.json"
    trace_path = discover_phase3_trace_registry_path(phase3_root)
    profile_detected = any(path.exists() for path in (authority_path, application_path, exact_path, delta_path))
    if not profile_detected:
        return {"present": False, "complete": False, "evidence_paths": [], "runtime_evidence_refs": []}

    authority = load_json_if_exists(authority_path) or {}
    application = load_json_if_exists(application_path) or {}
    exact = load_json_if_exists(exact_path) or {}
    delta = load_json_if_exists(delta_path) or {}
    bindings = load_json_if_exists(bindings_path) or {}
    trace = load_json_if_exists(trace_path) or {}
    trace_rows = [row for row in ensure_list(trace.get("rows")) if isinstance(row, dict)]
    runtime_refs = dedupe_preserve_order(
        str(ref).strip()
        for row in trace_rows
        for ref in ensure_list(row.get("runtime_evidence_refs"))
        if str(ref).strip()
    )
    runtime_paths = [_runtime_evidence_path(phase3_root, ref) for ref in runtime_refs]
    runtime_report_results = [_load_runtime_evidence_report(path) for path in runtime_paths]
    runtime_reports = [report for report, reason in runtime_report_results if report is not None and not reason]
    invalid_runtime_evidence_refs = [
        ref
        for ref, (_report, reason) in zip(runtime_refs, runtime_report_results)
        if reason
    ]
    runtime_refs_complete = bool(runtime_paths) and not invalid_runtime_evidence_refs and len(runtime_reports) == len(runtime_paths)
    runtime_pass = runtime_refs_complete and all(_current_s4_runtime_evidence_is_pass(report) for report in runtime_reports)

    exact_counts = exact.get("counts") if isinstance(exact.get("counts"), dict) else {}
    exact_rows = [row for row in ensure_list(exact.get("rows")) if isinstance(row, dict)]
    exact_complete = bool(
        exact.get("status") == "exact-realization-bindings-complete"
        and int(exact_counts.get("blocking", 0) or 0) == 0
        and int(exact_counts.get("exact", 0) or 0) == len(exact_rows)
        and exact_rows
        and all(str(row.get("binding_status") or "") == "exact" and row.get("trace_confirmed") is True for row in exact_rows)
    )
    application_complete = bool(
        application.get("application_status") == "complete"
        and not ensure_list(application.get("missing_applications"))
    )
    authority_complete = bool(authority.get("status") == "accepted-p3-agentic-implementation-authority")
    binding_rows = [row for row in ensure_list(bindings.get("rows")) if isinstance(row, dict)]
    bindings_complete = bool(binding_rows) and len(binding_rows) >= len(exact_rows)
    confirmed_trace_rows = [
        row
        for row in trace_rows
        if str(
            row.get("final_resolution")
            or row.get("binding_status")
            or row.get("status")
            or row.get("trace_status")
            or ""
        ).strip().lower() == "confirmed"
    ]
    legacy_trace_status = str(trace.get("execution_status") or "").strip().lower()
    legacy_trace_status_compatible = (
        not legacy_trace_status
        or legacy_trace_status in {"confirmed", "confirmed-s4", "pass", "verified"}
    )
    trace_complete = bool(
        trace_rows
        and len(confirmed_trace_rows) == len(trace_rows)
        and legacy_trace_status_compatible
    )
    delta_safe = bool(
        delta
        and delta.get("upstream_mutation_performed") is False
        and str(delta.get("reconciliation_status") or "").strip().startswith("deferred")
    )
    decision_digests = {
        str(value).strip()
        for value in (
            authority.get("decision_digest"),
            application.get("decision_digest"),
            exact.get("decision_digest"),
            delta.get("decision_digest"),
        )
        if str(value).strip()
    }
    trace_digests = {
        str(row.get("implementation_decision_digest") or "").strip()
        for row in trace_rows
        if str(row.get("implementation_decision_digest") or "").strip()
    }
    digest_aligned = len(decision_digests) == 1 and (not trace_digests or trace_digests == decision_digests)
    realization_decisions = _load_p3_realization_decisions_summary(
        phase3_root=phase3_root,
        authority=authority,
        delta=delta,
    )
    realization_decisions_complete = bool(realization_decisions.get("valid"))
    complete = bool(
        authority_complete
        and application_complete
        and exact_complete
        and bindings_complete
        and trace_complete
        and delta_safe
        and realization_decisions_complete
        and runtime_pass
        and digest_aligned
    )
    realization_decisions_path = Path(str(realization_decisions.get("path") or "")).expanduser()
    evidence_paths = [
        relative_to_root(path, phase3_root)
        for path in (authority_path, application_path, exact_path, bindings_path, trace_path, delta_path, *runtime_paths)
        if path.exists() and path.is_file()
    ]
    if realization_decisions_path.is_file():
        evidence_paths.append(str(realization_decisions_path))
    claim_ceilings = dedupe_preserve_order(
        str(report.get("claim_ceiling") or "").strip()
        for report in runtime_reports
        if str(report.get("claim_ceiling") or "").strip()
    )
    return {
        "present": True,
        "complete": complete,
        "authority_complete": authority_complete,
        "application_complete": application_complete,
        "exact_bindings_complete": exact_complete,
        "trace_complete": trace_complete,
        "authority_delta_safe": delta_safe,
        "realization_decisions_complete": realization_decisions_complete,
        "realization_decisions": realization_decisions,
        "runtime_evidence_complete": runtime_refs_complete,
        "runtime_evidence_pass": runtime_pass,
        "digest_aligned": digest_aligned,
        "decision_digest": next(iter(decision_digests), ""),
        "exact_binding_count": len(exact_rows),
        "trace_row_count": len(trace_rows),
        "confirmed_trace_count": len(confirmed_trace_rows),
        "runtime_evidence_refs": [relative_to_root(path, phase3_root) for path in runtime_paths],
        "invalid_runtime_evidence_refs": invalid_runtime_evidence_refs,
        "evidence_paths": dedupe_preserve_order(evidence_paths),
        "claim_ceilings": claim_ceilings,
        "recommended_formal_state": "delivery-ready" if complete else "implementation-in-progress",
        "phase_verdict": "PASS with review-bound items" if complete else "RETURN-REMEDIATE",
        "phase_complete": complete,
        "implementation_complete": complete,
        "backend_interface_gate": complete,
        "backend_persistence_truth_required": True,
        "backend_persistence_gate": runtime_pass,
        "backend_migration_gate": runtime_pass,
        "full_targeted_evidence_present": runtime_refs_complete,
        "full_targeted_evidence_status": "pass" if runtime_pass else "fail" if runtime_refs_complete else "missing",
    }


def load_phase3_runtime_environment_summary(phase3_root: Path) -> dict[str, Any]:
    ledger_path = phase3_root / "runtime-environment-ledger.json"
    ledger = load_json_if_exists(ledger_path) or {}
    rows = [row for row in ensure_list(ledger.get("rows")) if isinstance(row, dict)]
    rows_by_packet: dict[str, dict[str, Any]] = {}
    lane_summary: dict[str, dict[str, Any]] = {}

    for row in rows:
        packet_id = str(row.get("packet_id") or "").strip()
        if packet_id:
            rows_by_packet[packet_id] = row
        lane = str(row.get("lane") or "unknown").strip().lower() or "unknown"
        lane_row = lane_summary.setdefault(
            lane,
            {
                "lane": lane,
                "packet_count": 0,
                "available_packet_count": 0,
                "missing_packet_count": 0,
                "required_runtime_environments": [],
                "blocked_capabilities": [],
                "allowed_progress_ceilings": [],
            },
        )
        lane_row["packet_count"] += 1
        required_runtime = str(row.get("required_runtime_environment") or "").strip()
        if required_runtime:
            lane_row["required_runtime_environments"] = dedupe_preserve_order(
                [*lane_row["required_runtime_environments"], required_runtime]
            )
        blocked_capabilities = [str(value) for value in ensure_list(row.get("blocked_capabilities")) if str(value).strip()]
        if blocked_capabilities:
            lane_row["blocked_capabilities"] = dedupe_preserve_order(
                [*lane_row["blocked_capabilities"], *blocked_capabilities]
            )
        allowed_progress_ceiling = str(row.get("allowed_progress_ceiling") or "").strip()
        if allowed_progress_ceiling:
            lane_row["allowed_progress_ceilings"] = dedupe_preserve_order(
                [*lane_row["allowed_progress_ceilings"], allowed_progress_ceiling]
            )
        if str(row.get("current_availability") or "").strip().lower() == "available":
            lane_row["available_packet_count"] += 1
        else:
            lane_row["missing_packet_count"] += 1

    for lane_row in lane_summary.values():
        lane_row["all_runtime_available"] = lane_row["packet_count"] > 0 and lane_row["missing_packet_count"] == 0

    missing_runtime_lanes = sorted(
        lane for lane, lane_row in lane_summary.items() if int(lane_row.get("missing_packet_count", 0) or 0) > 0
    )
    return {
        "present": bool(ledger),
        "path": relative_to_root(ledger_path, phase3_root) if ledger_path.exists() else "",
        "available_runtime_environments": [
            str(value) for value in ensure_list(ledger.get("available_runtime_environments")) if str(value).strip()
        ],
        "packet_count": len(rows),
        "packets_with_available_runtime": len(
            [row for row in rows if str(row.get("current_availability") or "").strip().lower() == "available"]
        ),
        "packets_missing_runtime": len(
            [row for row in rows if str(row.get("current_availability") or "").strip().lower() != "available"]
        ),
        "missing_runtime_lanes": missing_runtime_lanes,
        "lanes": lane_summary,
        "rows": rows,
        "rows_by_packet": rows_by_packet,
    }


def _current_closure_supersedes_mainline(
    *,
    current_closure: Mapping[str, Any],
    metadata: Mapping[str, Any],
    metadata_summary: Mapping[str, Any],
    verdict: Mapping[str, Any],
) -> bool:
    current_digest = str(current_closure.get("decision_digest") or "").strip()
    recorded_digests = {
        str(value).strip()
        for value in (
            metadata.get("agentic_implementation_decision_digest"),
            metadata_summary.get("agentic_implementation_decision_digest"),
            verdict.get("agentic_implementation_decision_digest"),
        )
        if str(value).strip()
    }
    return bool(current_digest and recorded_digests and current_digest not in recorded_digests)


def load_phase3_mainline_summary(phase3_root: Path) -> dict[str, Any]:
    metadata = load_json_if_exists(phase3_root / "phase3-run-metadata.json") or {}
    metadata_summary = metadata.get("mainline_assessment_summary")
    metadata_artifacts = metadata.get("mainline_assessment_artifacts")
    verdict = load_json_if_exists(phase3_root / "phase-verdict.json") or {}
    claim_ceiling_report = read_claim_ceiling_report(phase3_root)
    current_closure = load_phase3_current_closure_summary(phase3_root)

    if not isinstance(metadata_summary, dict):
        metadata_summary = {}
    if not isinstance(metadata_artifacts, dict):
        metadata_artifacts = {}
    # Current modular closure may replace a legacy mainline snapshot only when the
    # decision identity proves that snapshot is stale. Mechanical closure completeness
    # alone must not erase contemporaneous quality or claim-ceiling evidence.
    current_closure_is_only_source = not verdict and not metadata_summary
    current_closure_explicitly_supersedes = bool(current_closure.get("complete")) and _current_closure_supersedes_mainline(
        current_closure=current_closure,
        metadata=metadata,
        metadata_summary=metadata_summary,
        verdict=verdict,
    )
    if current_closure.get("present") and (
        current_closure_is_only_source or current_closure_explicitly_supersedes
    ):
        current_ceiling = "; ".join(str(value) for value in current_closure.get("claim_ceilings", []) if str(value).strip())
        return {
            "present": True,
            "source": "p3-current-closure",
            "phase": "P3",
            "mainline_profile": "current-modular",
            "recommended_formal_state": str(current_closure.get("recommended_formal_state") or "implementation-in-progress"),
            "phase_verdict": str(current_closure.get("phase_verdict") or "RETURN-REMEDIATE"),
            "phase_total_score": None,
            "review_bound_items_count": 1 if current_closure.get("complete") else 0,
            "blockers_count": 0 if current_closure.get("complete") else 1,
            "warning_count": 0,
            "failure_count": 0 if current_closure.get("complete") else 1,
            "claim_ceiling_report": {
                "present": True,
                "requested_formal_state": str(current_closure.get("recommended_formal_state") or "implementation-in-progress"),
                "resolved_formal_state": str(current_closure.get("recommended_formal_state") or "implementation-in-progress"),
                "claim_ceiling": str(current_closure.get("recommended_formal_state") or "implementation-in-progress"),
                "blocking_delivery_ready": not bool(current_closure.get("complete")),
                "detail": current_ceiling,
                "reasons": [],
            },
            "claim_ceiling_present": bool(current_ceiling),
            "claim_ceiling_resolved_formal_state": str(current_closure.get("recommended_formal_state") or "implementation-in-progress"),
            "claim_ceiling_blocks_ready": False,
            "phase_complete": bool(current_closure.get("phase_complete")),
            "implementation_complete": bool(current_closure.get("implementation_complete")),
            "phase_verdict_path": "p3-exact-realization-binding-ledger.json",
            "phase_scorecard_path": "",
            "phase_acceptance_matrix_path": "",
        }

    return {
        "present": bool(verdict) or bool(metadata_summary),
        "source": "phase-verdict.json" if verdict else ("phase3-run-metadata.json" if metadata_summary else ""),
        "phase": str(verdict.get("phase") or metadata_summary.get("phase") or "P3").strip() or "P3",
        "mainline_profile": str(
            verdict.get("mainline_profile") or metadata_summary.get("mainline_profile") or "backend-first"
        ).strip()
        or "backend-first",
        "recommended_formal_state": str(
            verdict.get("recommended_formal_state") or metadata_summary.get("recommended_formal_state") or ""
        ).strip(),
        "phase_verdict": str(verdict.get("verdict") or metadata_summary.get("phase_verdict") or "").strip(),
        "phase_total_score": verdict.get("total_score", metadata_summary.get("phase_total_score")),
        "review_bound_items_count": int(
            verdict.get("review_bound_items_count", metadata_summary.get("review_bound_items_count", 0)) or 0
        ),
        "blockers_count": int(verdict.get("blockers_count", metadata_summary.get("blockers_count", 0)) or 0),
        "warning_count": int(verdict.get("warning_count", metadata_summary.get("warning_count", 0)) or 0),
        "failure_count": int(verdict.get("failure_count", metadata_summary.get("failure_count", 0)) or 0),
        "claim_ceiling_report": claim_ceiling_report,
        "claim_ceiling_present": bool(claim_ceiling_report.get("present")),
        "claim_ceiling_resolved_formal_state": str(
            claim_ceiling_report.get("resolved_formal_state") or "unknown"
        ).strip(),
        "claim_ceiling_blocks_ready": claim_ceiling_blocks_ready(claim_ceiling_report),
        "phase_complete": bool(verdict.get("phase_complete", metadata_summary.get("phase_complete", False))),
        "implementation_complete": bool(
            verdict.get("implementation_complete", metadata_summary.get("implementation_complete", False))
        ),
        "phase_verdict_path": str(
            metadata.get("phase_verdict_path")
            or metadata_summary.get("phase_verdict_path")
            or metadata_artifacts.get("verdict_path")
            or (relative_to_root(phase3_root / "phase-verdict.json", phase3_root) if verdict else "")
        ).strip(),
        "phase_scorecard_path": str(
            metadata_summary.get("phase_scorecard_path")
            or metadata_artifacts.get("scorecard_path")
            or (
                relative_to_root(phase3_root / "phase-mainline-scorecard.md", phase3_root)
                if (phase3_root / "phase-mainline-scorecard.md").exists()
                else ""
            )
        ).strip(),
        "phase_acceptance_matrix_path": str(
            metadata_summary.get("phase_acceptance_matrix_path")
            or metadata_artifacts.get("acceptance_matrix_path")
            or (
                relative_to_root(phase3_root / "phase-acceptance-matrix.md", phase3_root)
                if (phase3_root / "phase-acceptance-matrix.md").exists()
                else ""
            )
        ).strip(),
    }


def load_phase3_trace_registry_for_validation(phase3_root: Path) -> dict[str, Any]:
    trace_path = discover_phase3_trace_registry_path(phase3_root)
    trace = load_json_if_exists(trace_path) or {}
    current = load_phase3_current_closure_summary(phase3_root)
    if not current.get("present"):
        return trace
    authority = load_json_if_exists(phase3_root / "p3-agentic-implementation-authority.json") or {}
    plan_index = {
        (
            str(row.get("contract_id") or "").strip().upper(),
            str(row.get("operation_id") or "").strip(),
        ): row
        for row in ensure_list(authority.get("exact_realization_plan"))
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
    enriched_rows: list[dict[str, Any]] = []
    for raw_row in ensure_list(trace.get("rows")):
        if not isinstance(raw_row, dict):
            continue
        row = dict(raw_row)
        key = (
            str(row.get("contract_id") or row.get("source_id") or "").strip().upper(),
            str(row.get("operation_id") or "").strip(),
        )
        plan = plan_index.get(key, {})
        if not ensure_list(row.get("upstream_trace_ids")):
            commitment_id = str(plan.get("commitment_id") or "").strip()
            if commitment_id:
                row["upstream_trace_ids"] = [commitment_id.removeprefix("p1:")]
        if not str(row.get("source_type") or "").strip():
            row["source_type"] = "contract-trace"
        if not str(row.get("source_subject") or "").strip():
            row["source_subject"] = f"{row.get('operation_id') or row.get('contract_id') or 'P3 operation'} accepted contract"
        enriched_rows.append(row)
    return {**trace, "rows": enriched_rows, "validation_projection_source": "inherited-from-p3-exact-closure"}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_openapi_spec(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def discover_openapi_path(phase3_root: Path) -> Path:
    direct = phase3_root / "openapi-final.yaml"
    if direct.exists():
        return direct
    fallback = phase3_root / "contracts" / "openapi.yaml"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"no Phase-3 OpenAPI artifact found under {phase3_root}")


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def markdown_cell(value: Any) -> str:
    return sanitize_markdown_table_cell(
        value,
        pipe_escape="backslash",
        none_replacement="",
        list_separator=", ",
    )


def render_markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    return render_common_markdown_table(
        headers,
        rows,
        pipe_escape="backslash",
        none_replacement="",
        list_separator=", ",
    )


def clamp_assessment_dimension(score: int) -> int:
    return max(0, min(5, score))


PHASE4_FORMAL_STATE_RANK = {
    "testing-validation-return-required": 0,
    "testing-validation-complete-with-review-bound-items": 1,
    "testing-validation-complete-with-mock-dependency": 1,
    "testing-validation-complete": 2,
}


def build_phase4_claim_ceiling_report(
    *,
    requested_formal_state: str,
    closure_decision: str,
    checks: dict[str, Any],
    upstream_claim_ceiling_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    upstream_claim_ceiling_report = upstream_claim_ceiling_report or {}
    checks = checks if isinstance(checks, dict) else {}
    requested = str(requested_formal_state or "").strip() or "testing-validation-return-required"
    requested_rank = PHASE4_FORMAL_STATE_RANK.get(requested, 0)
    resolved_rank = requested_rank
    reasons: list[dict[str, str]] = []

    def cap(state: str, reason: str, signal: str, detail: str) -> None:
        nonlocal resolved_rank
        rank = PHASE4_FORMAL_STATE_RANK.get(state, 0)
        resolved_rank = min(resolved_rank, rank)
        reasons.append(
            {
                "reason": reason,
                "signal": signal,
                "detail": detail,
                "ceiling": state,
            }
        )

    upstream_state = str(upstream_claim_ceiling_report.get("resolved_formal_state") or "unknown").strip()
    upstream_claim_ceiling_blocks_ready = claim_ceiling_blocks_ready(upstream_claim_ceiling_report)
    upstream_claim_ceiling_allows_validation = claim_ceiling_allows_phase4_validation_entry(upstream_claim_ceiling_report)
    if upstream_claim_ceiling_blocks_ready:
        if upstream_claim_ceiling_allows_validation:
            cap(
                "testing-validation-complete-with-review-bound-items",
                "upstream_claim_ceiling_caps_release_ready",
                "phase3_claim_ceiling",
                f"Phase-3 claim ceiling is `{upstream_state}`; Phase-4 may validate but must keep release readiness review-bound.",
            )
        else:
            cap(
                "testing-validation-return-required",
                "upstream_claim_ceiling_blocks_ready",
                "phase3_claim_ceiling",
                f"Phase-3 claim ceiling is `{upstream_state}` and cannot be upgraded by Phase-4.",
            )

    blocking_count = int(checks.get("blocking_count") or 0)
    review_bound_count = int(checks.get("review_bound_count") or 0)
    signoff_pending_count = int(checks.get("signoff_pending_count") or 0)
    signoff_not_ready_count = int(checks.get("signoff_not_ready_count") or 0)

    if closure_decision in {"return", "testing-validation-return-required"} or blocking_count > 0:
        cap(
            "testing-validation-return-required",
            "phase4_closure_return_required",
            "phase4_closure",
            "Phase-4 closure contains blocking or return-required evidence.",
        )
    if closure_decision == "pass-with-mock-dependency":
        cap(
            "testing-validation-complete-with-mock-dependency",
            "mock_dependency_present",
            "phase4_closure",
            "Runtime evidence still depends on mock or unresolved runtime-environment truth.",
        )
    if (
        closure_decision == "pass-with-review-bound-items"
        or review_bound_count > 0
        or signoff_pending_count > 0
        or signoff_not_ready_count > 0
    ):
        cap(
            "testing-validation-complete-with-review-bound-items",
            "residual_review_bound_items",
            "phase4_closure",
            "Review-bound, visual, or signoff items remain and cannot be promoted to complete.",
        )

    if any(row.get("reason") == "mock_dependency_present" for row in reasons) and not any(
        row.get("reason") in {"upstream_claim_ceiling_blocks_ready", "phase4_closure_return_required"}
        for row in reasons
    ):
        resolved_state = "testing-validation-complete-with-mock-dependency"
    else:
        resolved_state = next(
            state for state, rank in PHASE4_FORMAL_STATE_RANK.items() if rank == resolved_rank
        )
    return {
        "artifact_kind": "phase4-claim-ceiling-report.v1",
        "requested_formal_state": requested,
        "resolved_formal_state": resolved_state,
        "claim_ceiling": resolved_state,
        "blocking_delivery_ready": resolved_state != "testing-validation-complete",
        "reasons": reasons,
        "inputs": {
            "closure_decision": closure_decision,
            "blocking_count": blocking_count,
            "review_bound_count": review_bound_count,
            "signoff_pending_count": signoff_pending_count,
            "signoff_not_ready_count": signoff_not_ready_count,
            "upstream_claim_ceiling_state": upstream_state,
        },
        "upstream_claim_ceiling_report": upstream_claim_ceiling_report,
        "policy": "Phase-4 may confirm or lower upstream ceilings; it must not upgrade review-bound or unknown evidence.",
    }


def render_phase4_scorecard_markdown(assessment: dict[str, Any]) -> str:
    lines = [
        "# Phase-4 Mainline Scorecard",
        "",
        f"- total_score: `{assessment['total_score']}` / 100",
        f"- verdict: `{assessment['verdict']}`",
        f"- closure_decision: `{assessment['closure_decision']}`",
        "",
        "| Dimension | Weight | Score | Notes |",
        "|---|---:|---:|---|",
    ]
    for row in assessment["dimension_scores"]:
        notes = "; ".join(str(item) for item in row.get("notes", [])) or "-"
        lines.append(f"| {row['label']} | {row['weight']} | {row['score']} / 5 | {notes} |")
    return "\n".join(lines).rstrip() + "\n"


def render_phase4_acceptance_matrix_markdown(assessment: dict[str, Any]) -> str:
    lines = [
        "# Phase-4 Acceptance Matrix",
        "",
        f"- verdict: `{assessment['verdict']}`",
        f"- closure_decision: `{assessment['closure_decision']}`",
        "",
        "| Acceptance Item | Status | Why |",
        "|---|---|---|",
    ]
    for row in assessment["acceptance_rows"]:
        lines.append(f"| {row['label']} | `{row['status']}` | {row['why']} |")
    return "\n".join(lines).rstrip() + "\n"


def build_phase4_mainline_assessment(
    *,
    stage1_summary: dict[str, Any],
    stage2_summary: dict[str, Any],
    stage3_summary: dict[str, Any],
) -> dict[str, Any]:
    phase3_mainline_summary_present = bool(stage1_summary.get("phase3_mainline_summary_present"))
    trace_mapping_complete = bool(stage1_summary.get("trace_mapping_complete"))
    functional_api_mapping_complete = bool(stage1_summary.get("functional_api_mapping_complete"))
    decision_alignment_complete = bool(stage1_summary.get("decision_alignment_complete"))
    high_priority_unmapped_count = int(stage1_summary.get("high_priority_unmapped_count") or 0)

    functional_non_pass_count = int(stage2_summary.get("functional_non_pass_count") or 0)
    functional_conditional_pass_count = int(stage2_summary.get("functional_conditional_pass_count") or 0)
    data_fidelity_non_pass_count = int(stage2_summary.get("data_fidelity_non_pass_count") or 0)
    data_fidelity_conditional_pass_count = int(stage2_summary.get("data_fidelity_conditional_pass_count") or 0)
    ui_review_non_pass_count = int(stage2_summary.get("ui_review_non_pass_count") or 0)
    visual_review_bound_count = int(stage2_summary.get("visual_review_bound_count") or 0)
    review_bound_count = int(stage2_summary.get("review_bound_count") or 0)
    signoff_pending_count = int(stage2_summary.get("signoff_pending_count") or 0)
    signoff_not_ready_count = int(
        stage2_summary.get("signoff_not_ready_count", stage3_summary.get("signoff_not_ready_count", 0)) or 0
    )

    closure_decision = str(stage3_summary.get("closure_decision", "")).strip() or "return"
    upstream_claim_ceiling_report = (
        stage3_summary.get("upstream_claim_ceiling_report")
        if isinstance(stage3_summary.get("upstream_claim_ceiling_report"), dict)
        else stage1_summary.get("phase3_claim_ceiling_report")
        if isinstance(stage1_summary.get("phase3_claim_ceiling_report"), dict)
        else {}
    )
    upstream_claim_ceiling_blocks_ready = claim_ceiling_blocks_ready(upstream_claim_ceiling_report)
    upstream_claim_ceiling_allows_validation = claim_ceiling_allows_phase4_validation_entry(upstream_claim_ceiling_report)
    upstream_claim_ceiling_blocks_validation = (
        upstream_claim_ceiling_blocks_ready and not upstream_claim_ceiling_allows_validation
    )
    upstream_claim_ceiling_state = str(
        upstream_claim_ceiling_report.get("resolved_formal_state") or "unknown"
    ).strip()
    blocking_count = int(stage3_summary.get("blocking_count") or 0)
    mock_dependency_present = functional_conditional_pass_count > 0 or data_fidelity_conditional_pass_count > 0
    review_pending = (
        ui_review_non_pass_count > 0
        or visual_review_bound_count > 0
        or signoff_pending_count > 0
        or signoff_not_ready_count > 0
        or review_bound_count > 0
    )
    requested_formal_state = str(stage3_summary.get("recommended_formal_state") or "").strip()
    if not requested_formal_state:
        requested_formal_state = {
            "pass": "testing-validation-complete",
            "pass-with-mock-dependency": "testing-validation-complete-with-mock-dependency",
            "pass-with-review-bound-items": "testing-validation-complete-with-review-bound-items",
            "return": "testing-validation-return-required",
        }.get(closure_decision, "testing-validation-return-required")
    claim_ceiling_report = (
        stage3_summary.get("claim_ceiling_report")
        if isinstance(stage3_summary.get("claim_ceiling_report"), dict)
        else build_phase4_claim_ceiling_report(
            requested_formal_state=requested_formal_state,
            closure_decision=closure_decision,
            checks={
                "blocking_count": blocking_count,
                "review_bound_count": review_bound_count,
                "signoff_pending_count": signoff_pending_count,
                "signoff_not_ready_count": signoff_not_ready_count,
            },
            upstream_claim_ceiling_report=upstream_claim_ceiling_report,
        )
    )

    dimension_rows = [
        {
            "key": "planning_and_traceability",
            "label": "测试规划与追踪完整度",
            "weight": 25,
            "score": clamp_assessment_dimension(
                int(phase3_mainline_summary_present)
                + int(trace_mapping_complete)
                + int(functional_api_mapping_complete)
                + int(decision_alignment_complete)
                + int(high_priority_unmapped_count == 0)
            ),
            "notes": [
                f"trace_mapping_complete={str(trace_mapping_complete).lower()}",
                f"functional_api_mapping_complete={str(functional_api_mapping_complete).lower()}",
                f"decision_alignment_complete={str(decision_alignment_complete).lower()}",
                f"high_priority_unmapped_count={high_priority_unmapped_count}",
            ],
        },
        {
            "key": "execution_truth",
            "label": "执行证据真实性",
            "weight": 25,
            "score": clamp_assessment_dimension(
                int(functional_non_pass_count == 0)
                + int(data_fidelity_non_pass_count == 0)
                + int(functional_conditional_pass_count == 0)
                + int(data_fidelity_conditional_pass_count == 0)
                + int(phase3_mainline_summary_present)
            ),
            "notes": [
                f"functional_non_pass_count={functional_non_pass_count}",
                f"data_fidelity_non_pass_count={data_fidelity_non_pass_count}",
                f"functional_conditional_pass_count={functional_conditional_pass_count}",
                f"data_fidelity_conditional_pass_count={data_fidelity_conditional_pass_count}",
            ],
        },
        {
            "key": "closure_boundary_quality",
            "label": "收口边界质量",
            "weight": 20,
            "score": clamp_assessment_dimension(
                int(closure_decision in {"pass", "pass-with-review-bound-items", "pass-with-mock-dependency"})
                + int(blocking_count == 0)
                + int(trace_mapping_complete)
                + int(decision_alignment_complete)
                + int(phase3_mainline_summary_present)
                - int(upstream_claim_ceiling_blocks_validation)
            ),
            "notes": [
                f"closure_decision={closure_decision}",
                f"upstream_claim_ceiling_state={upstream_claim_ceiling_state}",
                f"blocking_count={blocking_count}",
                f"signoff_pending_count={signoff_pending_count}",
                f"signoff_not_ready_count={signoff_not_ready_count}",
            ],
        },
        {
            "key": "review_bound_honesty",
            "label": "review-bound / signoff 诚实度",
            "weight": 15,
            "score": clamp_assessment_dimension(
                int(phase3_mainline_summary_present)
                + int(bool(closure_decision))
                + int((not mock_dependency_present) or closure_decision == "pass-with-mock-dependency")
                + int((not review_pending) or closure_decision in {"pass-with-review-bound-items", "return"})
                + int((blocking_count == 0) or closure_decision == "return")
            ),
            "notes": [
                f"mock_dependency_present={str(mock_dependency_present).lower()}",
                f"review_pending={str(review_pending).lower()}",
                f"review_bound_count={review_bound_count}",
                f"signoff_pending_count={signoff_pending_count}",
                f"signoff_not_ready_count={signoff_not_ready_count}",
            ],
        },
        {
            "key": "downstream_decision_readiness",
            "label": "下游决策可用度",
            "weight": 15,
            "score": clamp_assessment_dimension(
                int(closure_decision != "return")
                + int(blocking_count == 0)
                + int(signoff_pending_count == 0)
                + int(signoff_not_ready_count == 0)
                + int(review_bound_count == 0)
                + int(high_priority_unmapped_count == 0)
            ),
            "notes": [
                f"closure_decision={closure_decision}",
                f"review_bound_count={review_bound_count}",
                f"signoff_pending_count={signoff_pending_count}",
                f"signoff_not_ready_count={signoff_not_ready_count}",
            ],
        },
    ]

    planning_status = (
        "PASS"
        if trace_mapping_complete and functional_api_mapping_complete and decision_alignment_complete and high_priority_unmapped_count == 0
        else "REVIEW-BOUND"
        if trace_mapping_complete and decision_alignment_complete
        else "BLOCKED"
    )
    planning_why = (
        "acceptance planning is trace-complete and key Phase-2 decisions are covered"
        if planning_status == "PASS"
        else "planning is mostly usable, but some higher-priority decision coverage remains review-bound"
        if planning_status == "REVIEW-BOUND"
        else "acceptance planning still leaves trace or decision-coverage gaps that weaken closure"
    )
    mandatory_status = (
        "PASS"
        if functional_non_pass_count == 0
        and data_fidelity_non_pass_count == 0
        and not mock_dependency_present
        else "REVIEW-BOUND"
        if functional_non_pass_count == 0 and data_fidelity_non_pass_count == 0
        else "BLOCKED"
    )
    mandatory_why = (
        "functional and data-fidelity items both passed with non-conditional evidence"
        if mandatory_status == "PASS"
        else "mandatory evidence passed, but runtime truth still carries conditional/mock-dependency posture"
        if mandatory_status == "REVIEW-BOUND"
        else "mandatory functional or data-fidelity evidence still contains blocking failures"
    )
    nonfunctional_status = (
        "PASS"
        if not review_pending and blocking_count == 0
        else "REVIEW-BOUND"
        if blocking_count == 0 and closure_decision in {"pass-with-review-bound-items", "pass-with-mock-dependency"}
        else "BLOCKED"
    )
    nonfunctional_why = (
        "UI/visual/manual signoff surfaces are closed without residual review-bound items"
        if nonfunctional_status == "PASS"
        else "UI/visual/manual signoff gaps remain, but they are explicitly preserved in the closure posture"
        if nonfunctional_status == "REVIEW-BOUND"
        else "non-functional evidence still contains structural blockers or hidden unresolved truth"
    )
    closure_status = (
        "BLOCKED"
        if upstream_claim_ceiling_blocks_validation
        else "REVIEW-BOUND"
        if upstream_claim_ceiling_blocks_ready
        else
        "PASS"
        if closure_decision == "pass"
        else "REVIEW-BOUND"
        if closure_decision in {"pass-with-review-bound-items", "pass-with-mock-dependency"}
        else "BLOCKED"
    )
    closure_why = (
        f"upstream claim ceiling is `{upstream_claim_ceiling_state}`, so P4 cannot promote the package to testing-validation-complete"
        if upstream_claim_ceiling_blocks_validation
        else f"upstream claim ceiling is `{upstream_claim_ceiling_state}`, so validation closure remains review-bound"
        if upstream_claim_ceiling_blocks_ready
        else
        "closure package gives a clear downstream decision boundary without residual review-bound items"
        if closure_status == "PASS"
        else "closure package is usable, but downstream must keep the explicit review-bound boundary visible"
        if closure_status == "REVIEW-BOUND"
        else "closure decision is return and still requires remediation before downstream adoption"
    )

    acceptance_rows = [
        {
            "key": "phase3_mainline_truth_present",
            "label": "Phase-3 主线结论已被 P4 显式消费",
            "status": "PASS" if phase3_mainline_summary_present else "BLOCKED",
            "why": (
                "Phase-4 consumed explicit Phase-3 mainline truth"
                if phase3_mainline_summary_present
                else "Phase-4 is missing the upstream Phase-3 mainline truth anchor"
            ),
        },
        {
            "key": "acceptance_planning_trace_complete",
            "label": "测试规划与决策覆盖完整",
            "status": planning_status,
            "why": planning_why,
        },
        {
            "key": "mandatory_execution_evidence_passed",
            "label": "功能/数据保真主证据已通过",
            "status": mandatory_status,
            "why": mandatory_why,
        },
        {
            "key": "nonfunctional_gaps_explicit",
            "label": "非功能 review-bound 与签核缺口显式外露",
            "status": nonfunctional_status,
            "why": nonfunctional_why,
        },
        {
            "key": "downstream_decision_boundary_clear",
            "label": "下游不需要猜测收口边界",
            "status": closure_status,
            "why": closure_why,
        },
    ]

    total_score = round(sum((row["score"] / 5) * row["weight"] for row in dimension_rows), 1)
    blockers_count = sum(1 for row in acceptance_rows if row["status"] == "BLOCKED")
    review_bound_items_count = sum(1 for row in acceptance_rows if row["status"] == "REVIEW-BOUND")
    min_dimension_score = min((row["score"] for row in dimension_rows), default=0)

    if closure_decision == "return" or blockers_count > 0 or total_score < 70:
        verdict = "RETURN-REMEDIATE"
    elif upstream_claim_ceiling_blocks_validation:
        verdict = "RETURN-REMEDIATE"
    elif total_score >= 85 and min_dimension_score >= 3 and review_bound_items_count == 0 and closure_decision == "pass":
        verdict = "PASS"
    else:
        verdict = "PASS with review-bound items"

    return {
        "phase": "P4",
        "closure_decision": closure_decision,
        "dimension_scores": dimension_rows,
        "acceptance_rows": acceptance_rows,
        "total_score": total_score,
        "verdict": verdict,
        "review_bound_items_count": review_bound_items_count,
        "blockers_count": blockers_count,
        "signoff_pending_count": signoff_pending_count,
        "signoff_not_ready_count": signoff_not_ready_count,
        "phase3_mainline_summary_present": phase3_mainline_summary_present,
        "recommended_formal_state": str(claim_ceiling_report.get("resolved_formal_state") or requested_formal_state),
        "claim_ceiling_report": claim_ceiling_report,
        "upstream_claim_ceiling_report": upstream_claim_ceiling_report,
        "upstream_claim_ceiling_blocks_ready": upstream_claim_ceiling_blocks_ready,
        "upstream_claim_ceiling_allows_validation": upstream_claim_ceiling_allows_validation,
        "upstream_claim_ceiling_blocks_validation": upstream_claim_ceiling_blocks_validation,
        "upstream_claim_ceiling_state": upstream_claim_ceiling_state,
        "functional_non_pass_count": functional_non_pass_count,
        "data_fidelity_non_pass_count": data_fidelity_non_pass_count,
    }


def write_phase4_mainline_assessment_artifacts(
    *,
    output_dir: Path,
    assessment: dict[str, Any],
) -> dict[str, str]:
    scorecard_path = output_dir / "phase-mainline-scorecard.md"
    acceptance_matrix_path = output_dir / "phase-acceptance-matrix.md"
    verdict_path = output_dir / "phase-verdict.json"
    write_text(scorecard_path, render_phase4_scorecard_markdown(assessment))
    write_text(acceptance_matrix_path, render_phase4_acceptance_matrix_markdown(assessment))
    write_json(verdict_path, assessment)
    return {
        "scorecard_path": str(scorecard_path),
        "acceptance_matrix_path": str(acceptance_matrix_path),
        "verdict_path": str(verdict_path),
    }


def build_phase4_metadata_payload(
    *,
    case_name: str,
    version: str,
    phase3_root: Path,
    artifact_kind: str,
    generation_entrypoint: str,
    generation_purity: str,
    external_evidence_manifest: Path | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "generated_at": utc_now_iso(),
        "case_name": case_name,
        "version": version,
        "artifact_version": "v1",
        "phase3_root": str(phase3_root),
        "artifact_kind": artifact_kind,
        "generation_entrypoint": generation_entrypoint,
        "generation_purity": generation_purity,
        "external_evidence_manifest": str(external_evidence_manifest) if external_evidence_manifest else "",
    }
    if extra_fields:
        payload.update(extra_fields)
    return payload


def build_phase4_quality_check_payload(
    *,
    stage1_summary: dict[str, Any],
    stage2_summary: dict[str, Any],
    stage3_summary: dict[str, Any],
    extra_checks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks = {
        "stage01_trace_mapping_complete": stage1_summary["trace_mapping_complete"],
        "stage01_functional_api_mapping_complete": stage1_summary["functional_api_mapping_complete"],
        "stage01_functional_api_optional_count": stage1_summary["functional_api_optional_count"],
        "stage01_data_fidelity_count": stage1_summary.get("data_fidelity_count", 0),
        "stage01_decision_alignment_complete": stage1_summary["decision_alignment_complete"],
        "stage01_high_priority_unmapped_count": stage1_summary["high_priority_unmapped_count"],
        "stage01_human_signoff_required_count": stage1_summary["human_signoff_required_count"],
        "stage02_functional_non_pass_count": stage2_summary["functional_non_pass_count"],
        "stage02_functional_conditional_pass_count": stage2_summary.get("functional_conditional_pass_count", 0),
        "stage02_data_fidelity_non_pass_count": stage2_summary.get("data_fidelity_non_pass_count", 0),
        "stage02_data_fidelity_conditional_pass_count": stage2_summary.get("data_fidelity_conditional_pass_count", 0),
        "stage02_ui_review_non_pass_count": stage2_summary["ui_review_non_pass_count"],
        "stage02_visual_review_bound_count": stage2_summary["visual_review_bound_count"],
        "stage02_signoff_pending_count": stage2_summary["signoff_pending_count"],
        "stage02_signoff_not_ready_count": stage2_summary.get("signoff_not_ready_count", 0),
        "stage03_closure_decision": stage3_summary["closure_decision"],
        "stage03_signoff_pending_count": stage3_summary["signoff_pending_count"],
        "stage03_signoff_not_ready_count": stage3_summary.get("signoff_not_ready_count", 0),
    }
    if extra_checks:
        checks = {**extra_checks, **checks}
    return {
        "generated_at": utc_now_iso(),
        "overall_quality_gate": stage3_summary["closure_decision"],
        "checks": checks,
        "summaries": {
            "stage01": stage1_summary,
            "stage02": stage2_summary,
            "stage03": stage3_summary,
        },
    }


def build_phase4_mainline_assessment_summary(
    *,
    assessment: dict[str, Any],
    artifact_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    artifact_paths = artifact_paths or {}
    return {
        "phase": str(assessment.get("phase", "P4")).strip() or "P4",
        "phase_verdict": str(assessment.get("verdict", "")).strip(),
        "phase_total_score": assessment.get("total_score"),
        "review_bound_items_count": int(assessment.get("review_bound_items_count", 0) or 0),
        "blockers_count": int(assessment.get("blockers_count", 0) or 0),
        "signoff_pending_count": int(assessment.get("signoff_pending_count", 0) or 0),
        "signoff_not_ready_count": int(assessment.get("signoff_not_ready_count", 0) or 0),
        "closure_decision": str(assessment.get("closure_decision", "")).strip(),
        "phase_scorecard_path": str(artifact_paths.get("scorecard_path", "")).strip(),
        "phase_acceptance_matrix_path": str(artifact_paths.get("acceptance_matrix_path", "")).strip(),
        "phase_verdict_path": str(artifact_paths.get("verdict_path", "")).strip(),
    }


def _test_bucket(index: dict[str, dict[str, Any]], test_id: str) -> dict[str, Any]:
    return index.setdefault(
        test_id,
        {
            "report_paths": [],
            "pass_count": 0,
            "fail_count": 0,
            "verdict": "not-run",
            "latest_verdict": "not-run",
            "latest_report_path": "",
        },
    )


def _record_test_verdict(
    index: dict[str, dict[str, Any]],
    *,
    test_id: str,
    verdict: str,
    report_ref: str,
) -> None:
    normalized_test_id = str(test_id).strip()
    normalized_verdict = str(verdict).strip().lower()
    if not normalized_test_id or normalized_verdict not in {"pass", "fail"}:
        return
    bucket = _test_bucket(index, normalized_test_id)
    if normalized_verdict == "pass":
        bucket["pass_count"] += 1
    else:
        bucket["fail_count"] += 1
    bucket["report_paths"] = dedupe_preserve_order([*bucket["report_paths"], report_ref])
    bucket["latest_verdict"] = normalized_verdict
    bucket["latest_report_path"] = report_ref


def _ingest_test_report_payload(
    index: dict[str, dict[str, Any]],
    *,
    payload: dict[str, Any],
    report_ref: str,
) -> None:
    for passed_test in ensure_list(payload.get("passed_tests") or payload.get("observed_passed_tests")):
        _record_test_verdict(index, test_id=str(passed_test), verdict="pass", report_ref=report_ref)
    for failed_test in ensure_list(
        payload.get("failed_tests") or payload.get("observed_failed_tests") or payload.get("missing_expected_tests")
    ):
        _record_test_verdict(index, test_id=str(failed_test), verdict="fail", report_ref=report_ref)


def _ingest_phase3_verification_ledger(
    index: dict[str, dict[str, Any]],
    *,
    ledger: dict[str, Any],
    report_ref: str,
) -> None:
    aggregated = ledger.get("aggregated", {}) if isinstance(ledger.get("aggregated"), dict) else {}
    _ingest_test_report_payload(index, payload=aggregated, report_ref=report_ref)

    latest_by_packet = ledger.get("latest_by_packet", {}) if isinstance(ledger.get("latest_by_packet"), dict) else {}
    for packet_row in latest_by_packet.values():
        if isinstance(packet_row, dict):
            _ingest_test_report_payload(index, payload=packet_row, report_ref=report_ref)


def collect_test_evidence(phase3_root: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    report_patterns = [
        "worker-runs/**/test-report.json",
        ".phase3-mainline-execution/backend-runs/**/test-report.json",
        ".phase3-mainline-execution/backend-runs/**/unit-test-report.json",
        ".phase3-mainline-execution/backend-runs/**/full-test-report.json",
        ".phase3-mainline-execution/backend-runs/**/verification-report.json",
        "test-report.json",
        "unit-test-report.json",
        "full-test-report.json",
    ]
    report_paths: list[Path] = []
    for pattern in report_patterns:
        report_paths.extend(sorted(phase3_root.glob(pattern)))
    for report_path in dedupe_preserve_order(str(path) for path in report_paths):
        path = Path(report_path)
        report = load_json(path)
        _ingest_test_report_payload(index, payload=report, report_ref=relative_to_root(path, phase3_root))

    ledger_path = phase3_root / "phase3-verification-ledger.json"
    if ledger_path.exists():
        _ingest_phase3_verification_ledger(
            index,
            ledger=load_json(ledger_path),
            report_ref=relative_to_root(ledger_path, phase3_root),
        )

    current_closure = load_phase3_current_closure_summary(phase3_root)
    if current_closure.get("runtime_evidence_pass"):
        trace_path = discover_phase3_trace_registry_path(phase3_root)
        trace = load_json_if_exists(trace_path) or {}
        for row in ensure_list(trace.get("rows")):
            if not isinstance(row, dict):
                continue
            if str(
                row.get("final_resolution")
                or row.get("binding_status")
                or row.get("status")
                or row.get("trace_status")
                or ""
            ).strip().lower() != "confirmed":
                continue
            report_refs = [
                str(value).strip() for value in ensure_list(row.get("runtime_evidence_refs")) if str(value).strip()
            ] or [relative_to_root(trace_path, phase3_root)]
            for target in ensure_list(row.get("test_targets")):
                target_id = str(target).strip()
                if not target_id:
                    continue
                for report_ref in report_refs:
                    _record_test_verdict(index, test_id=target_id, verdict="pass", report_ref=report_ref)

    for bucket in index.values():
        if bucket["latest_verdict"] in {"pass", "fail"}:
            bucket["verdict"] = bucket["latest_verdict"]
        elif bucket["pass_count"] > 0:
            bucket["verdict"] = "pass"
        else:
            bucket["verdict"] = "not-run"
    return index


def collect_visual_evidence_paths(phase3_root: Path) -> list[str]:
    search_roots = [
        phase3_root,
        phase3_root / "apps",
        phase3_root / "docs",
        phase3_root / "evidence",
        phase3_root / "screenshots",
        phase3_root / "worker-runs",
    ]
    results: list[str] = []
    seen_paths: set[Path] = set()
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for path in search_root.rglob("*"):
            if path in seen_paths or not path.is_file():
                continue
            if "node_modules" in path.parts:
                continue
            if path.suffix.lower() not in VISUAL_EVIDENCE_SUFFIXES:
                continue
            seen_paths.add(path)
            results.append(relative_to_root(path, phase3_root))
    return dedupe_preserve_order(results)


def load_frontend_packets(phase3_root: Path) -> list[dict[str, Any]]:
    return load_worker_packets(phase3_root, lane="frontend")


def load_worker_packets(phase3_root: Path, lane: str | None = None) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    pattern = "worker-input-packets/wave-*/*-worker-input-packet.json"
    for packet_path in sorted(phase3_root.glob(pattern)):
        packet = load_json(packet_path)
        packet_lane = str(packet.get("lane") or packet_path.name.split("-worker-input-packet.json")[0] or "")
        if lane is not None and packet_lane != lane:
            continue
        packet["packet_path"] = relative_to_root(packet_path, phase3_root)
        packet["lane"] = packet_lane
        packets.append(packet)
    return packets


def extract_operation_ids_from_text(text: str) -> list[str]:
    return dedupe_preserve_order(re.findall(r'operationId"\s*:\s*"([A-Za-z0-9_]+)"', text))


def extract_operation_ids_from_file(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    return extract_operation_ids_from_text(path.read_text(encoding="utf-8"))


def _alias_tuple(value: str, aliases: Iterable[str] | None = None) -> tuple[str, ...]:
    resolved = tuple(str(item) for item in (aliases or ()) if str(item))
    return resolved or (value,)


def normalize_text(value: str) -> str:
    return " ".join(str(value).replace(" ", " ").split())


def block_lines(text: str, block_name: str) -> list[str]:
    lines = text.splitlines()
    start = None
    marker = f"- {block_name}:"
    for idx, line in enumerate(lines):
        if line.startswith(marker):
            start = idx
            break
    if start is None:
        return []
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("- ") and not line.startswith("  - "):
            break
        collected.append(line)
    return collected


def block_text(text: str, block_name: str) -> str:
    return "\n".join(block_lines(text, block_name)).strip()


def heading_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    prefix = f"## {heading}"
    start = None
    for idx, line in enumerate(lines):
        if line.startswith(prefix):
            start = idx
            break
    if start is None:
        return ""
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def markdown_heading_section(text: str, heading: str, *, aliases: Iterable[str] | None = None) -> str:
    for candidate in _alias_tuple(heading, aliases):
        pattern = re.compile(rf"^(#+)\s+{re.escape(candidate)}\s*$", re.MULTILINE)
        match = pattern.search(text)
        if not match:
            continue
        level = len(match.group(1))
        start = match.start()
        end = len(text)
        for next_match in pattern.finditer(text):
            if next_match.start() == match.start():
                continue
            if len(next_match.group(1)) <= level:
                end = next_match.start()
                break
        general_heading_re = re.compile(r"^(#+)\s+.+$", re.MULTILINE)
        for next_match in general_heading_re.finditer(text, match.end()):
            if len(next_match.group(1)) <= level:
                end = next_match.start()
                break
        return text[start:end].strip()
    return ""


def extract_structured_field(
    entry: str,
    field_name: str,
    *,
    indent: int = 4,
    aliases: Iterable[str] | None = None,
) -> str:
    field_names = _alias_tuple(field_name, aliases)
    candidate_indents = [indent]
    candidate_indents.extend(
        indent_value
        for indent_value in (
            len(match.group(1))
            for alias in field_names
            for match in re.finditer(rf"^( *)- {re.escape(alias)}:", entry, flags=re.MULTILINE)
        )
        if indent_value not in candidate_indents
    )
    for current_indent in candidate_indents:
        value = extract_structured_field_at_indent(
            entry,
            field_name,
            indent=current_indent,
            aliases=field_names,
        )
        if value:
            return value
    return ""


def extract_structured_field_at_indent(
    entry: str,
    field_name: str,
    *,
    indent: int = 4,
    aliases: Iterable[str] | None = None,
) -> str:
    del field_name
    field_names = _alias_tuple("", aliases)
    lines = entry.splitlines()
    collected: list[str] = []
    capturing = False
    for line in lines:
        for alias in field_names:
            prefix = " " * indent + f"- {alias}:"
            if line.startswith(prefix):
                capturing = True
                remainder = line[len(prefix) :].strip()
                if remainder:
                    collected.append(remainder.strip("`"))
                break
        else:
            prefix = ""
        if prefix:
            continue
        if not capturing:
            continue
        if line.startswith(" " * indent + "- ") and not line.startswith(" " * (indent + 2) + "- "):
            break
        stripped = line.strip()
        if stripped:
            collected.append(stripped.strip("`"))
    return normalize_text(" ".join(collected))


def extract_structured_block(
    entry: str,
    field_name: str,
    *,
    indent: int = 4,
    aliases: Iterable[str] | None = None,
) -> str:
    field_names = _alias_tuple(field_name, aliases)
    candidate_indents = [indent]
    candidate_indents.extend(
        indent_value
        for indent_value in (
            len(match.group(1))
            for alias in field_names
            for match in re.finditer(rf"^( *)- {re.escape(alias)}:", entry, flags=re.MULTILINE)
        )
        if indent_value not in candidate_indents
    )
    for current_indent in candidate_indents:
        value = extract_structured_block_at_indent(
            entry,
            field_name,
            indent=current_indent,
            aliases=field_names,
        )
        if value:
            return value
    return ""


def extract_structured_block_at_indent(
    entry: str,
    field_name: str,
    *,
    indent: int = 4,
    aliases: Iterable[str] | None = None,
) -> str:
    del field_name
    field_names = _alias_tuple("", aliases)
    lines = entry.splitlines()
    collected: list[str] = []
    capturing = False
    for line in lines:
        for alias in field_names:
            prefix = " " * indent + f"- {alias}:"
            if line.startswith(prefix):
                capturing = True
                remainder = line[len(prefix) :].rstrip()
                if remainder.strip():
                    collected.append(remainder.strip())
                break
        else:
            prefix = ""
        if prefix:
            continue
        if not capturing:
            continue
        if line.startswith(" " * indent + "- ") and not line.startswith(" " * (indent + 2) + "- "):
            break
        collected.append(line.rstrip())
    return "\n".join(collected).strip()
