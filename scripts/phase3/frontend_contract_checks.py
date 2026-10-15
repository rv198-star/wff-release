#!/usr/bin/env python3
"""
Frontend contract evidence checks for Phase-3 delivery closure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from phase3.delivery_asset_checks import file_sha256
from phase3.operable_surface_contract_metrics import evaluate_surface_contract_taxonomy


def safe_load_json(path: Path | None) -> tuple[dict[str, Any] | None, str]:
    if path is None or not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None, "invalid-json"
    if not isinstance(payload, dict):
        return None, "invalid-json"
    return payload, "ok"


def ui_ia_contract_valid(path: Path | None) -> tuple[bool, dict[str, Any]]:
    if path is None or not path.exists():
        return False, {"reason": "missing"}
    payload, status = safe_load_json(path)
    if status != "ok" or not isinstance(payload, dict):
        return False, {"reason": "invalid-json"}
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        return False, {"reason": "pages-missing"}
    access_requirements = payload.get("product_access_requirements") if isinstance(payload.get("product_access_requirements"), dict) else {}
    terminal_qualification = (
        access_requirements.get("terminal_role_qualification")
        if isinstance(access_requirements.get("terminal_role_qualification"), dict)
        else {}
    )
    if terminal_qualification and str(terminal_qualification.get("status") or "").strip() not in {"", "sufficient"}:
        return False, {
            "reason": "terminal-role-authority-insufficient",
            "missing_role_authority_page_ids": terminal_qualification.get("missing_role_authority_page_ids", []),
            "return_owner": "P3 gap decision",
        }
    if bool(terminal_qualification.get("super_role_qualifies_terminal_roles")):
        return False, {"reason": "super-role-terminal-qualification-forbidden"}
    business_data = payload.get("business_data_requirements") if isinstance(payload.get("business_data_requirements"), dict) else {}
    if str(business_data.get("read_model_status") or "").strip() in {"authority-gap", "registered-p3-read-model"}:
        from phase3.p3_fact_registration import realized_read_model_resolution
        if not realized_read_model_resolution(root=path.parent, requirements=business_data):
            return False, {
                "reason": "business-read-model-authority-gap",
                "missing_authority": business_data.get("missing_authority", []),
                "return_owner": "P3 gap decision",
            }
    if business_data.get("consumer_manual_internal_ids_allowed") is False and business_data.get("manual_identifier_inputs"):
        return False, {
            "reason": "manual-internal-identifier-inputs-present",
            "rows": business_data.get("manual_identifier_inputs", []),
        }
    project_language = payload.get("project_language_requirements") if isinstance(payload.get("project_language_requirements"), dict) else {}
    if bool(project_language.get("consumer_copy_must_match_project_locale")) and not str(project_language.get("consumer_locale") or "").strip():
        return False, {"reason": "project-consumer-locale-missing"}
    required_page_keys = {
        "data_required",
        "data_presentation",
        "display_fields",
        "user_inputs",
        "actions_and_transitions",
        "state_conditions",
        "field_source_mapping",
    }
    realization_hint_keys = {
        "page_blueprint_type",
        "primary_work_region",
        "secondary_support_regions",
        "dominant_component_pattern",
        "action_model",
    }
    realization_open_pages: list[str] = []
    has_operable_flow = False
    checked_pages = 0
    generic_shell_page_ids: list[str] = []
    generic_shell_section_ids = {
        "business-summary",
        "filters-selectors",
        "working-list",
        "detail-reading-chain",
        "action-feedback",
        "state-honesty",
    }
    allowed_action_input_sources = {"user-input", "workflow-context", "response-binding", "auth-session"}
    for page in pages:
        if not isinstance(page, dict):
            continue
        checked_pages += 1
        if not required_page_keys.issubset(page.keys()):
            return False, {"reason": "required-keys-missing", "page_id": page.get("page_id")}
        missing_realization_hints = [
            key
            for key in realization_hint_keys
            if (
                not page.get(key)
                or (isinstance(page.get(key), list) and not [item for item in page.get(key, []) if str(item).strip()])
            )
        ]
        if missing_realization_hints:
            realization_open_pages.append(str(page.get("page_id") or ""))
        display_fields = page.get("display_fields")
        if not isinstance(display_fields, list):
            return False, {"reason": "display-fields-invalid", "page_id": page.get("page_id")}
        if page.get("data_required") and not display_fields:
            return False, {"reason": "display-fields-missing", "page_id": page.get("page_id")}
        sections = page.get("sections")
        if isinstance(sections, list):
            section_ids = {
                str(item.get("section_id", "")).strip()
                for item in sections
                if isinstance(item, dict) and str(item.get("section_id", "")).strip()
            }
            if section_ids and section_ids.issubset(generic_shell_section_ids):
                generic_shell_page_ids.append(str(page.get("page_id") or ""))
        transitions = page.get("actions_and_transitions")
        if not isinstance(transitions, list):
            return False, {"reason": "transitions-invalid", "page_id": page.get("page_id")}
        visible_user_inputs = {
            str(item.get("field", "")).strip()
            for item in page.get("user_inputs", [])
            if isinstance(item, dict) and str(item.get("field", "")).strip()
        }
        page_field_sources: dict[str, str] = {}
        for mapping in page.get("field_source_mapping", []):
            if not isinstance(mapping, dict):
                continue
            field = str(mapping.get("field", "")).strip()
            source = str(mapping.get("source", "")).strip()
            if field and source and field not in page_field_sources:
                page_field_sources[field] = source
        available_response_binding_targets: set[str] = set()
        for transition in transitions:
            if not isinstance(transition, dict):
                continue
            required_fields = [
                str(field).strip()
                for field in transition.get("required_fields", [])
                if str(field).strip()
            ]
            required_input_sources = transition.get("required_input_sources", [])
            source_by_field: dict[str, str] = {}
            if isinstance(required_input_sources, list):
                for entry in required_input_sources:
                    if not isinstance(entry, dict):
                        continue
                    field = str(entry.get("field", "")).strip()
                    source = str(entry.get("source", "")).strip()
                    if field and source and field not in source_by_field:
                        source_by_field[field] = source
            for field in required_fields:
                source = source_by_field.get(field) or page_field_sources.get(field, "")
                if source not in allowed_action_input_sources:
                    return False, {
                        "reason": "action-input-source-missing",
                        "page_id": page.get("page_id"),
                        "action": transition.get("action"),
                        "field": field,
                    }
                if source == "user-input" and field not in visible_user_inputs:
                    return False, {
                        "reason": "action-input-closure-missing",
                        "page_id": page.get("page_id"),
                        "action": transition.get("action"),
                        "field": field,
                        "source": source,
                    }
                if source == "response-binding" and field not in available_response_binding_targets:
                    return False, {
                        "reason": "action-input-closure-missing",
                        "page_id": page.get("page_id"),
                        "action": transition.get("action"),
                        "field": field,
                        "source": source,
                    }
            action = str(transition.get("action", "")).strip().lower()
            on_success = str(transition.get("on_success", "")).strip().lower()
            next_route = str(transition.get("next_route", "")).strip()
            has_structured_navigation = next_route.startswith("/")
            has_navigation_copy = bool(re.search(r"/[a-z0-9][a-z0-9/_-]*", on_success))
            has_progress_copy = (
                "navigate to" in on_success
                or "go to" in on_success
                or "refresh current page state" in on_success
                or "advance-workflow-or-refresh-page-state" in on_success
                or "进入" in on_success
                or "跳转" in on_success
                or "下一步" in on_success
                or "带入下一步" in on_success
            )
            if action and (has_structured_navigation or has_navigation_copy or has_progress_copy):
                has_operable_flow = True
            for binding in transition.get("response_bindings", []):
                if not isinstance(binding, dict):
                    continue
                target = str(binding.get("to", "")).strip()
                if target:
                    available_response_binding_targets.add(target)
    if checked_pages == 0:
        return False, {"reason": "no-valid-pages"}
    if generic_shell_page_ids:
        return False, {
            "reason": "generic-shell-sections-detected",
            "page_count": checked_pages,
            "has_operable_flow": has_operable_flow,
            "generic_shell_page_ids": generic_shell_page_ids,
        }
    return has_operable_flow, {
        "reason": "ok",
        "page_count": checked_pages,
        "has_operable_flow": has_operable_flow,
        "p3_realization_open_page_ids": [page_id for page_id in realization_open_pages if page_id],
    }


def productness_report_contract_reference(productness_gate_report: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(productness_gate_report, dict):
        return {"ui_ia_contract_path": "", "ui_ia_contract_sha256": ""}
    nested = productness_gate_report.get("ui_ia_contract_reference")
    if not isinstance(nested, dict):
        nested = {}
    report_path = str(
        nested.get("ui_ia_contract_path")
        or productness_gate_report.get("ui_ia_contract_path")
        or ""
    ).strip()
    report_sha256 = str(
        nested.get("ui_ia_contract_sha256")
        or productness_gate_report.get("ui_ia_contract_sha256")
        or ""
    ).strip()
    return {
        "ui_ia_contract_path": report_path,
        "ui_ia_contract_sha256": report_sha256,
    }


def productness_report_matches_contract(
    ui_ia_contract_path: Path | None,
    productness_gate_report: dict[str, Any] | None,
) -> tuple[bool, str]:
    if not isinstance(productness_gate_report, dict):
        return False, "report-missing"
    checks = productness_gate_report.get("taxonomy_checks")
    metrics = productness_gate_report.get("contract_metrics")
    if not isinstance(checks, dict) or not isinstance(metrics, dict):
        return False, "report-payload-missing"
    reference = productness_report_contract_reference(productness_gate_report)
    report_path = reference["ui_ia_contract_path"]
    report_sha256 = reference["ui_ia_contract_sha256"]
    if not report_path or not report_sha256:
        return False, "fingerprint-missing"
    if ui_ia_contract_path is None or not ui_ia_contract_path.exists():
        return False, "current-contract-missing"
    try:
        current_path = str(ui_ia_contract_path.resolve())
        referenced_path = str(Path(report_path).resolve())
    except OSError:
        return False, "path-invalid"
    if referenced_path != current_path:
        return False, "path-mismatch"
    if report_sha256 != file_sha256(ui_ia_contract_path):
        return False, "hash-mismatch"
    return True, "matched"


def surface_contract_taxonomy_report(
    ui_ia_contract_path: Path | None,
    productness_gate_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_trusted, report_validation_reason = productness_report_matches_contract(
        ui_ia_contract_path,
        productness_gate_report,
    )
    if report_trusted and isinstance(productness_gate_report, dict):
        checks = productness_gate_report.get("taxonomy_checks")
        metrics = productness_gate_report.get("contract_metrics")
        if isinstance(checks, dict) and isinstance(metrics, dict):
            contract_failures = productness_gate_report.get("contract_failures", [])
            contract_warnings = productness_gate_report.get("contract_warnings", [])
            return {
                "present": True,
                "source": "phase3-productness-gate",
                "gate_pass": not contract_failures,
                "checks": checks,
                "metrics": metrics,
                "failures": [str(item) for item in contract_failures],
                "warnings": [str(item) for item in contract_warnings if str(item).strip()],
                "report_reused": True,
                "report_validation_reason": report_validation_reason,
            }
    if ui_ia_contract_path is None or not ui_ia_contract_path.exists():
        return {
            "present": False,
            "source": "missing",
            "gate_pass": False,
            "checks": {},
            "metrics": {},
            "failures": ["surface_contract_evidence_missing"],
            "warnings": [],
            "report_reused": False,
            "report_validation_reason": report_validation_reason,
        }
    payload, payload_status = safe_load_json(ui_ia_contract_path)
    if payload_status != "ok" or not isinstance(payload, dict) or not payload:
        return {
            "present": False,
            "source": "invalid-ui-ia-contract",
            "gate_pass": False,
            "checks": {},
            "metrics": {},
            "failures": ["surface_contract_invalid_json"],
            "warnings": [],
            "report_reused": False,
            "report_validation_reason": report_validation_reason,
        }
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        return {
            "present": False,
            "source": "invalid-ui-ia-contract",
            "gate_pass": False,
            "checks": {},
            "metrics": {},
            "failures": ["surface_contract_pages_missing"],
            "warnings": [],
            "report_reused": False,
            "report_validation_reason": report_validation_reason,
        }
    assessment = evaluate_surface_contract_taxonomy(payload)
    return {
        "present": True,
        "source": "ui-ia-contract",
        **assessment,
        "report_reused": False,
        "report_validation_reason": (
            "recomputed-from-current-contract"
            if report_validation_reason in {"report-missing", "report-payload-missing"}
            else report_validation_reason
        ),
    }
