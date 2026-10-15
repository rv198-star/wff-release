#!/usr/bin/env python3
"""
Execute Docker-based runtime smoke validation for a Phase-3 workspace.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import hashlib
import json
import re
import secrets
import shutil
from pathlib import Path
from typing import Any, Mapping

from common.host_port_allocator import host_port_in_use
from common.output_language import localize_phase3_runtime_smoke_report, resolve_output_locale
from phase3.phase3_started_service_smoke import run_phase3_started_service_smoke
from phase3.implementation_binding_tools import agentic_region_rows
from phase3.review_support import support_gate_exit_code, write_json_report
from phase3.runtime_smoke_executor import (
    command_has_host_port_bind_conflict,
    command_has_transient_network_failure,
    detect_compose_command,
    detect_pnpm_command,
    frontend_browser_substitution_findings,
    frontend_clean_first_use_markers,
    frontend_consumer_journey_markers,
    frontend_consumer_page_markers,
    frontend_runtime_evidence_markers,
    parse_playwright_json_output,
    run_command,
    sha256_file,
    wait_for_probe,
)
from phase3.runtime_smoke_plan import build_runtime_smoke_plan as canonical_build_runtime_smoke_plan


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    checks = report.get("checks", {})
    probes = report.get("probes", {})
    commands = report.get("commands", {})
    selected_host_ports = report.get("selected_host_ports", {})
    lines = [
        "# Phase-3 Runtime Smoke Report",
        "",
        "## Summary",
        f"- verdict: {report.get('verdict', 'unknown')}",
        f"- overall_quality_gate: {report.get('overall_quality_gate', 'unknown')}",
        f"- workspace_root: {report.get('workspace_root', '')}",
        f"- docker_available: {checks.get('docker_available', False)}",
        f"- compose_command_available: {checks.get('compose_command_available', False)}",
        f"- image_build_passed: {checks.get('image_build_passed', False)}",
        f"- compose_up_passed: {checks.get('compose_up_passed', False)}",
        f"- migration_passed: {checks.get('migration_passed', False)}",
        f"- health_probe_passed: {checks.get('health_probe_passed', False)}",
        f"- readiness_probe_passed: {checks.get('readiness_probe_passed', False)}",
        f"- frontend_requested: {checks.get('frontend_requested', False)}",
        f"- web_root_probe_passed: {checks.get('web_root_probe_passed', False)}",
        f"- web_runtime_proof_passed: {checks.get('web_runtime_proof_passed', False)}",
        f"- frontend_browser_evidence_green: {checks.get('frontend_browser_evidence_green', False)}",
        f"- started_service_smoke_green: {checks.get('started_service_smoke_green', False)}",
        "",
        "## Probes",
        f"- healthz_status: {probes.get('healthz', {}).get('status_code', 'n/a')}",
        f"- readyz_status: {probes.get('readyz', {}).get('status_code', 'n/a')}",
        f"- web_root_status: {probes.get('web_root', {}).get('status_code', 'n/a')}",
        f"- web_runtime_proof_status: {probes.get('web_runtime_proof', {}).get('status_code', 'n/a')}",
        "",
        "## Host Ports",
        f"- api_host_port: {selected_host_ports.get('API_HOST_PORT', 'n/a')}",
        f"- web_host_port: {selected_host_ports.get('WEB_HOST_PORT', 'n/a')}",
        f"- postgres_host_port: {selected_host_ports.get('POSTGRES_HOST_PORT', 'n/a')}",
        f"- redis_host_port: {selected_host_ports.get('REDIS_HOST_PORT', 'n/a')}",
        "",
        "## Commands",
    ]
    for key in ("image_build", "compose_up", "migration", "compose_down"):
        row = commands.get(key, {})
        lines.append(f"- {key}: exit_code={row.get('exit_code', 'n/a')} command={' '.join(row.get('command', []))}")
    lines.extend(
        [
            "",
            "## Failures",
            *([f"- {item}" for item in report.get("failures", [])] or ["- none"]),
            "",
            "## Warnings",
            *([f"- {item}" for item in report.get("warnings", [])] or ["- none"]),
            "",
        ]
    )
    return localize_phase3_runtime_smoke_report("\n".join(lines), output_locale)


def compact_terminal_summary(report: dict[str, Any], output_path: Path) -> dict[str, Any]:
    checks = report.get("checks", {})
    return {
        "verdict": report.get("verdict", "unknown"),
        "overall_quality_gate": report.get("overall_quality_gate", "unknown"),
        "output_path": str(output_path.resolve()),
        "markdown_output_path": str(output_path.resolve().with_suffix(".md")),
        "checks": {
            "runtime_smoke_green": bool(checks.get("runtime_smoke_green", False)),
            "image_build_passed": bool(checks.get("image_build_passed", False)),
            "compose_up_passed": bool(checks.get("compose_up_passed", False)),
            "migration_passed": bool(checks.get("migration_passed", False)),
            "health_probe_passed": bool(checks.get("health_probe_passed", False)),
            "readiness_probe_passed": bool(checks.get("readiness_probe_passed", False)),
            "frontend_requested": bool(checks.get("frontend_requested", False)),
            "web_root_probe_passed": bool(checks.get("web_root_probe_passed", False)),
            "web_runtime_proof_passed": bool(checks.get("web_runtime_proof_passed", False)),
            "frontend_browser_evidence_green": bool(checks.get("frontend_browser_evidence_green", False)),
            "started_service_smoke_green": bool(checks.get("started_service_smoke_green", False)),
        },
        "failures": report.get("failures", []),
        "warnings": report.get("warnings", []),
    }


def _build_runtime_smoke_plan(
    *,
    workspace_root: Path,
    service_url: str | None = None,
    exclude_ports: set[int] | None = None,
) -> dict[str, object]:
    return canonical_build_runtime_smoke_plan(
        workspace_root=workspace_root,
        service_url=service_url,
        exclude_ports=exclude_ports,
        port_in_use_fn=host_port_in_use,
    )


def redact_runtime_smoke_env(env: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in env.items():
        normalized = key.upper()
        if "SECRET" in normalized or "PASSWORD" in normalized or normalized.endswith("_KEY") or key == "PHASE3_AUTH_USERS_JSON":
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


def _runtime_auth_integration_mode(workspace_root: Path) -> str:
    path = workspace_root / "tech-stack-decision.yaml"
    if not path.is_file() or path.is_symlink():
        return "runtime-agnostic-real-auth"
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("integration_mode:"):
            continue
        return line.split(":", 1)[1].strip().strip('"\'') or "runtime-agnostic-real-auth"
    return "runtime-agnostic-real-auth"


def _provision_frontend_runtime_auth_fixture(
    env: dict[str, str],
    access_requirements: Mapping[str, Any] | None,
    *,
    integration_mode: str = "runtime-agnostic-real-auth",
    backend_auth_compatibility_mode: str = "",
) -> dict[str, str]:
    requirements = dict(access_requirements or {})
    if not bool(requirements.get("requires_authenticated_session")):
        return env
    if str(integration_mode or "").strip() == "external-idp":
        return env
    raw_personas = requirements.get("test_personas", [])
    personas = [dict(row) for row in raw_personas if isinstance(row, Mapping) and str(row.get("persona_id") or "").strip()]
    if not personas:
        personas = [{"persona_id": "user", "roles": requirements.get("required_roles", [])}]
    users: list[dict[str, Any]] = []
    credentials: list[tuple[str, str, str]] = []
    used_persona_ids: set[str] = set()
    for index, persona in enumerate(personas, start=1):
        raw_persona_id = str(persona.get("persona_id") or "").strip()
        roles = [str(role).strip() for role in persona.get("roles", []) if str(role).strip()]
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", raw_persona_id).strip("_").lower()
        identity_basis = raw_persona_id or "|".join(roles) or f"user{index}"
        persona_id = normalized or f"persona_{hashlib.sha256(identity_basis.encode('utf-8')).hexdigest()[:12]}"
        if persona_id in used_persona_ids:
            role_basis = "|".join(roles)
            if not role_basis:
                raise ValueError(f"duplicate frontend runtime persona identity: {raw_persona_id or persona_id}")
            persona_id = f"{persona_id}_{hashlib.sha256(role_basis.encode('utf-8')).hexdigest()[:8]}"
        if persona_id in used_persona_ids:
            raise ValueError(f"duplicate frontend runtime persona identity for roles: {','.join(roles)}")
        used_persona_ids.add(persona_id)
        username = f"phase3-runtime-{persona_id}"
        password = secrets.token_urlsafe(24)
        salt = secrets.token_bytes(16)
        password_hash = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
        if "authenticated" not in roles:
            roles.append("authenticated")
        users.append(
            {
                "username": username,
                "password_hash": f"scrypt${salt.hex()}${password_hash.hex()}",
                "subject_id": f"phase3-runtime-{persona_id}-subject",
                "tenant_id": "phase3-runtime-tenant",
                "roles": roles,
            }
        )
        credentials.append((persona_id, username, password))
    provisioned = dict(env)
    compatibility_mode = str(backend_auth_compatibility_mode or "").strip()
    if compatibility_mode == "frozen-phase3-header":
        provisioned["WFF_FROZEN_BACKEND_AUTH_ADAPTER"] = "phase3-header"
        provisioned["PHASE3_ALLOW_AUTH_CONTEXT_HEADER"] = "true"
    else:
        provisioned["PHASE3_LOCAL_AUTH_ENABLED"] = "true"
    provisioned["PHASE3_AUTH_USERS_JSON"] = json.dumps(users, separators=(",", ":"))
    provisioned["WFF_SESSION_COOKIE_SECURE"] = "false"
    first_persona, first_username, first_password = credentials[0]
    provisioned["WFF_FRONTEND_TEST_USERNAME"] = first_username
    provisioned["WFF_FRONTEND_TEST_PASSWORD"] = first_password
    for persona_id, username, password in credentials:
        env_prefix = re.sub(r"[^A-Za-z0-9]+", "_", persona_id).upper()
        provisioned[f"WFF_FRONTEND_TEST_{env_prefix}_USERNAME"] = username
        provisioned[f"WFF_FRONTEND_TEST_{env_prefix}_PASSWORD"] = password
    return provisioned


def _parse_postgres_table_counts(stdout: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for raw_line in str(stdout or "").splitlines():
        line = raw_line.strip()
        if not line or "|" not in line:
            continue
        table_name, raw_count = line.rsplit("|", 1)
        table_name = table_name.strip()
        try:
            count = int(raw_count.strip())
        except ValueError:
            continue
        if table_name:
            counts[table_name] = count
    return counts


def _evaluate_clean_first_use_table_counts(
    data_requirements: Mapping[str, Any],
    table_counts: Mapping[str, int],
    *,
    probe_passed: bool,
) -> dict[str, Any]:
    counts = {str(name): int(count) for name, count in table_counts.items()}
    has_authority_classifier = "clean_first_use_write_tables" in data_requirements
    if has_authority_classifier:
        write_tables = [
            str(value).strip()
            for value in data_requirements.get("clean_first_use_write_tables", [])
            if str(value).strip()
        ]
        missing_write_tables = sorted(table for table in write_tables if table not in counts)
        transaction_table_counts = {table: counts[table] for table in write_tables if table in counts}
        context_table_counts = {table: count for table, count in counts.items() if table not in set(write_tables)}
        transaction_row_count = sum(transaction_table_counts.values())
        authority_complete = bool(write_tables)
        clean = bool(probe_passed and counts and authority_complete and not missing_write_tables and transaction_row_count == 0)
        failure_code = ""
        if not authority_complete:
            failure_code = "frontend_clean_first_use_write_table_authority_missing"
        elif missing_write_tables:
            failure_code = "frontend_clean_first_use_write_table_missing"
        elif transaction_row_count != 0:
            failure_code = "frontend_clean_first_use_database_not_empty"
        elif not probe_passed or not counts:
            failure_code = "frontend_clean_first_use_database_probe_failed"
        return {
            "status": "pass" if clean else "fail",
            "table_counts": counts,
            "business_row_count": transaction_row_count,
            "transaction_table_counts": transaction_table_counts,
            "context_table_counts": context_table_counts,
            "missing_write_tables": missing_write_tables,
            "table_classification_source": str(
                data_requirements.get("clean_first_use_table_classification_source") or "p2-operation-table-authority"
            ),
            "failure_code": failure_code,
            "claim_ceiling": (
                "Pre-browser PostgreSQL emptiness for P2-authorized product write tables only; "
                "authority-approved context/reference data may already exist and later browser writes are evaluated separately."
            ),
        }

    business_row_count = sum(counts.values())
    clean = bool(probe_passed and counts and business_row_count == 0)
    return {
        "status": "pass" if clean else "fail",
        "table_counts": counts,
        "business_row_count": business_row_count,
        "transaction_table_counts": dict(counts),
        "context_table_counts": {},
        "missing_write_tables": [],
        "table_classification_source": "legacy-all-public-tables",
        "failure_code": "" if clean else "frontend_clean_first_use_database_not_empty",
        "claim_ceiling": (
            "Legacy pre-browser PostgreSQL public-table emptiness; current WFF contracts should provide "
            "P2-authorized clean-first-use write-table classification."
        ),
    }


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is unreadable: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _workspace_relative_path(workspace_root: Path, path: Path, *, label: str) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(workspace_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"{label} must remain inside the Phase-3 workspace: {resolved}") from exc


_FORBIDDEN_CONSUMER_AUTH_SHORTCUTS = (
    "phase3-role-session",
    "x-phase3-auth-context",
    "VITE_PHASE3_ALLOW_AUTH_CONTEXT_HEADER",
    "/auth/session",
)


def _frontend_consumer_auth_shortcut_findings(text: str) -> list[str]:
    regions = agentic_region_rows(text)
    authored_text = "\n".join(regions.values()) if regions else text
    return [marker for marker in _FORBIDDEN_CONSUMER_AUTH_SHORTCUTS if marker in authored_text]


def _validate_frontend_authoring_runtime_input(
    *,
    workspace_root: Path,
    authoring_report_path: Path,
    ui_ia_contract_path: Path,
) -> dict[str, Any]:
    report = _load_json_object(authoring_report_path, label="frontend authoring report")
    authoring = report.get("authoring") if isinstance(report.get("authoring"), dict) else {}
    if str(authoring.get("status") or "") != "materialized":
        raise ValueError("frontend runtime requires materialized complete-product authoring")
    if bool(authoring.get("semantic_authority")):
        raise ValueError("frontend authoring cannot enter runtime as semantic authority")
    if list(authoring.get("runtime_evidence_refs") or []):
        raise ValueError("frontend authoring already contains runtime evidence before P3 runtime execution")
    if bool(authoring.get("trace_confirmed")):
        raise ValueError("frontend authoring already claims Trace confirmation before P3 runtime execution")
    decision_id = str(authoring.get("implementation_decision_id") or "").strip()
    decision_digest = str(authoring.get("implementation_decision_digest") or "").strip()
    content_digest = str(authoring.get("content_digest") or "").strip()
    recorded_ui_sha = str(authoring.get("ui_ia_contract_sha256") or "").strip()
    if not all((decision_id, decision_digest, content_digest, recorded_ui_sha)):
        raise ValueError("frontend authoring identity is incomplete for runtime binding")
    application = authoring.get("application") if isinstance(authoring.get("application"), dict) else {}
    application_path = workspace_root / str(application.get("path") or "")
    if str(application.get("status") or "") != "materialized":
        raise ValueError("frontend runtime requires materialized product application authoring")
    if not application_path.is_file() or application_path.is_symlink():
        raise ValueError("frontend product application source is missing")
    application_sha = sha256_file(application_path)
    if application_sha != str(application.get("content_sha256") or ""):
        raise ValueError("frontend product application changed after authoring")
    application_shortcuts = _frontend_consumer_auth_shortcut_findings(application_path.read_text(encoding="utf-8"))
    if application_shortcuts:
        raise ValueError(
            "frontend product application uses forbidden consumer auth shortcut: " + ",".join(application_shortcuts)
        )
    consumer_e2e = authoring.get("consumer_e2e") if isinstance(authoring.get("consumer_e2e"), dict) else {}
    authored_e2e_specs: list[dict[str, str]] = []
    if consumer_e2e:
        e2e_path = workspace_root / str(consumer_e2e.get("path") or "")
        if str(consumer_e2e.get("status") or "") != "materialized":
            raise ValueError("frontend runtime requires materialized consumer E2E authoring")
        if not e2e_path.is_file() or e2e_path.is_symlink():
            raise ValueError("frontend consumer E2E source is missing")
        e2e_sha = sha256_file(e2e_path)
        if e2e_sha != str(consumer_e2e.get("content_sha256") or ""):
            raise ValueError("frontend consumer E2E source changed after authoring")
        authored_e2e_specs.append(
            {
                "path": _workspace_relative_path(workspace_root, e2e_path, label="frontend consumer E2E"),
                "content_sha256": e2e_sha,
            }
        )
    ui_path = ui_ia_contract_path.resolve()
    if not ui_path.is_file() or ui_path.is_symlink():
        raise ValueError("frontend runtime UI IA contract must be a readable regular file")
    if sha256_file(ui_path) != recorded_ui_sha:
        raise ValueError("frontend runtime UI IA contract changed after source authoring")
    ui_contract = _load_json_object(ui_path, label="frontend runtime UI IA contract")
    access_requirements = (
        dict(ui_contract.get("product_access_requirements"))
        if isinstance(ui_contract.get("product_access_requirements"), dict)
        else {}
    )
    business_data_requirements = (
        dict(ui_contract.get("business_data_requirements"))
        if isinstance(ui_contract.get("business_data_requirements"), dict)
        else {}
    )
    project_language_requirements = (
        dict(ui_contract.get("project_language_requirements"))
        if isinstance(ui_contract.get("project_language_requirements"), dict)
        else {}
    )
    backend_auth_compatibility_mode = str(ui_contract.get("backend_auth_compatibility_mode") or "").strip()
    if bool(access_requirements.get("requires_authenticated_session")):
        auth_transport = str(access_requirements.get("normal_api_auth_transport") or "").strip()
        if backend_auth_compatibility_mode == "frozen-phase3-header":
            if auth_transport != "bff-session-to-frozen-phase3-header":
                raise ValueError("frozen-backend frontend continuation must declare the BFF session compatibility transport")
        elif auth_transport != "authorization-bearer":
            raise ValueError("frontend authenticated consumer path must use Authorization Bearer transport")
    ui_pages = {
        str(row.get("page_id") or "").strip(): row
        for row in ui_contract.get("pages", [])
        if isinstance(row, dict) and str(row.get("page_id") or "").strip()
    }
    canonical_operation_catalog = {
        str(row.get("operation_id") or "").strip(): dict(row)
        for row in ui_contract.get("canonical_operation_catalog", [])
        if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
    }
    page_rows: list[dict[str, Any]] = []
    expected_interactions: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in authoring.get("pages", []):
        if not isinstance(raw, dict):
            continue
        page_id = str(raw.get("page_id") or "").strip()
        route = str(raw.get("route") or "").strip()
        if str(raw.get("status") or "") != "materialized" or not page_id or not route:
            raise ValueError("frontend authoring page identity is not materialized/current")
        page_path = workspace_root / str(raw.get("path") or "")
        test_path = workspace_root / str(raw.get("test_path") or "")
        if not page_path.is_file() or page_path.is_symlink() or sha256_file(page_path) != str(raw.get("content_sha256") or ""):
            raise ValueError(f"frontend authored page changed after authoring: {page_id}")
        page_shortcuts = _frontend_consumer_auth_shortcut_findings(page_path.read_text(encoding="utf-8"))
        if page_shortcuts:
            raise ValueError(
                f"frontend authored page uses forbidden consumer auth shortcut: {page_id}:" + ",".join(page_shortcuts)
            )
        if not test_path.is_file() or test_path.is_symlink() or sha256_file(test_path) != str(raw.get("test_content_sha256") or ""):
            raise ValueError(f"frontend authored page test changed after authoring: {page_id}")
        ui_page = ui_pages.get(page_id)
        if not isinstance(ui_page, dict) or str(ui_page.get("route") or "").strip() != route:
            raise ValueError(f"frontend UI IA page/route changed after authoring: {page_id}")
        for interaction in ui_page.get("compiled_interactions", []):
            if not isinstance(interaction, dict):
                continue
            status = str(interaction.get("readiness_status") or "ready").strip().lower()
            interaction_id = str(interaction.get("interaction_id") or "").strip()
            if not interaction_id:
                continue
            if status == "ready":
                expected_interactions[(page_id, interaction_id)] = {
                    "page_id": page_id,
                    "interaction_id": interaction_id,
                    "readiness_status": "ready",
                    "operation_id": str(interaction.get("operation_id") or "").strip(),
                    "api_endpoint": str(interaction.get("api_endpoint") or "").strip(),
                    "service_binding_id": str(interaction.get("service_binding_id") or "").strip(),
                    "binding_mode": str(interaction.get("binding_mode") or "").strip().lower(),
                }
                continue
            if status != "p3-realization-open":
                continue
            candidates = [
                str(value).strip()
                for value in interaction.get("operation_candidates", [])
                if str(value).strip()
            ]
            if str(interaction.get("authority_status") or "").strip().lower() != "sufficient" or not candidates:
                raise ValueError(
                    f"frontend realization-open interaction lacks sufficient operation authority: {page_id}:{interaction_id}"
                )
            candidate_operations: list[dict[str, str]] = []
            for operation_id in candidates:
                operation = canonical_operation_catalog.get(operation_id)
                if not operation:
                    raise ValueError(
                        f"frontend realization-open interaction references unknown canonical operation: {page_id}:{interaction_id}:{operation_id}"
                    )
                endpoint = str(operation.get("path") or "").strip()
                binding_mode = str(operation.get("binding_mode") or "").strip().lower()
                if not endpoint or binding_mode not in {"read", "write", "read_write"}:
                    raise ValueError(
                        f"frontend realization-open operation is incomplete: {page_id}:{interaction_id}:{operation_id}"
                    )
                candidate_operations.append(
                    {
                        "operation_id": operation_id,
                        "api_endpoint": endpoint,
                        "binding_mode": binding_mode,
                        "contract_id": str(operation.get("contract_id") or "").strip(),
                    }
                )
            expected_interactions[(page_id, interaction_id)] = {
                "page_id": page_id,
                "interaction_id": interaction_id,
                "readiness_status": "p3-realization-open",
                "operation_candidates": candidates,
                "candidate_operations": candidate_operations,
            }
        page_rows.append(
            {
                "page_id": page_id,
                "route": route,
                "path": _workspace_relative_path(workspace_root, page_path, label="frontend page"),
                "content_sha256": sha256_file(page_path),
                "slice_ids": [str(item) for item in raw.get("slice_ids", []) if str(item).strip()],
            }
        )
    if not page_rows:
        raise ValueError("frontend runtime requires at least one materialized authored page")
    return {
        "decision_id": decision_id,
        "decision_digest": decision_digest,
        "content_digest": content_digest,
        "ui_ia_contract_sha256": recorded_ui_sha,
        "product_access_requirements": access_requirements,
        "business_data_requirements": business_data_requirements,
        "project_language_requirements": project_language_requirements,
        "backend_auth_compatibility_mode": backend_auth_compatibility_mode,
        "application": {
            "path": _workspace_relative_path(workspace_root, application_path, label="frontend product application"),
            "content_sha256": application_sha,
            "shell_sha256": str(application.get("shell_sha256") or ""),
        },
        "authored_e2e_specs": authored_e2e_specs,
        "pages": page_rows,
        "expected_interactions": sorted(
            expected_interactions.values(),
            key=lambda row: (row["page_id"], row["interaction_id"]),
        ),
    }


def _validate_frontend_interaction_specs(
    *,
    workspace_root: Path,
    spec_paths: list[Path],
    expected_interactions: list[dict[str, Any]],
    known_routes: set[str] | None = None,
    known_page_ids: set[str] | None = None,
    access_requirements: Mapping[str, Any] | None = None,
    business_data_requirements: Mapping[str, Any] | None = None,
    auth_integration_mode: str = "runtime-agnostic-real-auth",
) -> dict[str, Any]:
    expected = {
        (row["page_id"], row["interaction_id"]): row
        for row in expected_interactions
    }
    covered: set[tuple[str, str]] = set()
    bindings: list[dict[str, Any]] = []
    journey_bindings: list[dict[str, str]] = []
    consumer_page_bindings: list[dict[str, str]] = []
    seen_journey_ids: set[str] = set()
    seen_consumer_page_ids: set[str] = set()
    requirements = dict(access_requirements or {})
    data_requirements = dict(business_data_requirements or {})
    requires_authenticated_session = bool(requirements.get("requires_authenticated_session"))
    terminal_qualification = (
        requirements.get("terminal_role_qualification")
        if isinstance(requirements.get("terminal_role_qualification"), Mapping)
        else {}
    )
    if terminal_qualification and str(terminal_qualification.get("status") or "").strip() not in {"", "sufficient"}:
        raise ValueError("frontend terminal-role qualification authority is not sufficient")
    test_personas = [
        dict(row)
        for row in requirements.get("test_personas", [])
        if isinstance(row, Mapping) and str(row.get("persona_id") or "").strip()
    ]
    persona_roles = {
        str(row.get("persona_id") or "").strip(): [str(role).strip() for role in row.get("roles", []) if str(role).strip()]
        for row in test_personas
    }
    required_roles = {str(role).strip() for role in requirements.get("required_roles", []) if str(role).strip()}
    if test_personas and (
        any(len(roles) != 1 for roles in persona_roles.values())
        or {roles[0] for roles in persona_roles.values() if roles} != required_roles
    ):
        raise ValueError("frontend terminal-role qualification requires one least-privilege persona per required role")
    if str(data_requirements.get("read_model_status") or "").strip() in {"authority-gap", "registered-p3-read-model"}:
        from common.p3_gap_records import registered_resolution
        ledger_path = workspace_root / ".phase3-evidence" / "p3-authority-delta-ledger.json"
        ledger = _load_json_object(ledger_path, label="P3 gap decision ledger") if ledger_path.is_file() else {}
        resolution = registered_resolution(ledger, "business-read-model-authority-missing")
        from phase3.p3_fact_registration import validate_read_model_bindings
        read_bindings = data_requirements.get("p3_read_model_bindings", [])
        if resolution is None or not validate_read_model_bindings(root=workspace_root,
                bindings=read_bindings, resolution=resolution, ledger=ledger):
            raise ValueError("p3-gap-decision-required: register and realize the read-model gap before runtime qualification")
        data_requirements["p3_gap_resolution"] = resolution
    requires_clean_first_use = bool(data_requirements.get("clean_first_use_required"))
    requires_business_data_discovery = bool(data_requirements.get("requires_business_data_discovery"))
    requires_context_reentry = bool(data_requirements.get("context_reentry_required"))
    authenticated_journey_spec_count = 0
    covered_personas: set[str] = set()
    clean_first_use_bindings: list[dict[str, str]] = []
    uuid_literal_re = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")
    for raw_path in spec_paths:
        path = raw_path if raw_path.is_absolute() else workspace_root / raw_path
        relative = _workspace_relative_path(workspace_root, path, label="frontend interaction spec")
        if not path.is_file() or path.is_symlink() or not relative.startswith("tests/e2e/"):
            raise ValueError(f"frontend interaction spec must be a regular tests/e2e file: {relative}")
        text = path.read_text(encoding="utf-8")
        regions = agentic_region_rows(text)
        authored_text = "\n".join(regions.values()) if regions else text
        substitution_findings = frontend_browser_substitution_findings(authored_text)
        if substitution_findings:
            raise ValueError(
                f"frontend interaction spec uses browser/network substitution: {relative}:{','.join(substitution_findings)}"
            )
        markers = frontend_runtime_evidence_markers(text)
        if not markers:
            raise ValueError(f"frontend interaction spec has no runtime evidence markers: {relative}")
        journey_markers = frontend_consumer_journey_markers(text)
        clean_first_use_markers = frontend_clean_first_use_markers(text)
        consumer_page_markers = frontend_consumer_page_markers(text)
        if journey_markers and ("randomUUID(" in text or "crypto.randomUUID(" in text or uuid_literal_re.search(text)):
            raise ValueError(f"frontend consumer journey uses fixture/random internal identifier instead of consumer discovery: {relative}")
        for page_marker in consumer_page_markers:
            page_id = str(page_marker.get("page_id") or "").strip()
            if not page_id or page_id in seen_consumer_page_ids:
                raise ValueError(
                    f"frontend consumer page evidence identity is missing or duplicated: {relative}:{page_id or '<missing>'}"
                )
            if known_page_ids is not None and page_id not in known_page_ids:
                raise ValueError(f"frontend consumer page evidence is foreign to current UI IA: {relative}:{page_id}")
            capture_pattern = re.compile(
                rf"wffCaptureConsumerPage\s*\([^;]*[\"']{re.escape(page_id)}[\"']\s*\)",
                re.DOTALL,
            )
            if not capture_pattern.search(text):
                raise ValueError(f"frontend consumer page evidence does not call the protected screenshot helper: {relative}:{page_id}")
            seen_consumer_page_ids.add(page_id)
            consumer_page_bindings.append({"page_id": page_id, "path": relative})
        if journey_markers and requires_authenticated_session:
            if auth_integration_mode == "external-idp":
                if "WFF_FRONTEND_TEST_USERNAME" not in text and "WFF_FRONTEND_TEST_PASSWORD" not in text:
                    authenticated_journey_spec_count += 1
            else:
                runtime_credential_tokens = ("WFF_FRONTEND_TEST_USERNAME", "WFF_FRONTEND_TEST_PASSWORD")
                if all(token in text for token in runtime_credential_tokens):
                    authenticated_journey_spec_count += 1
        journey_ids_in_spec = {str(row.get("journey_id") or "").strip() for row in journey_markers if str(row.get("journey_id") or "").strip()}
        for journey in journey_markers:
            journey_id = str(journey.get("journey_id") or "").strip()
            entry_route = str(journey.get("entry_route") or "").strip()
            persona_id = str(journey.get("persona_id") or "").strip()
            if persona_roles:
                if not persona_id and len(persona_roles) == 1:
                    persona_id = next(iter(persona_roles))
                    journey["persona_id"] = persona_id
                if not persona_id:
                    raise ValueError(f"frontend multi-role consumer journey must bind an independent persona: {relative}:{journey_id}")
                if persona_id not in persona_roles:
                    raise ValueError(f"frontend consumer journey persona is foreign to current role authority: {relative}:{journey_id}:{persona_id}")
                covered_personas.add(persona_id)
            if not journey_id or journey_id in seen_journey_ids:
                raise ValueError(f"frontend consumer journey identity is missing or duplicated: {relative}:{journey_id or '<missing>'}")
            if not entry_route.startswith("/"):
                raise ValueError(f"frontend consumer journey entry route is invalid: {relative}:{journey_id}:{entry_route}")
            if entry_route.startswith("/api/") or entry_route.startswith("/__wff-"):
                raise ValueError(f"frontend consumer journey entry route is not product-facing: {relative}:{journey_id}:{entry_route}")
            seen_journey_ids.add(journey_id)
            journey_bindings.append({**journey, "path": relative})
        resolved_marker_rows: list[tuple[dict[str, str], tuple[str, str], dict[str, Any]]] = []
        for marker in markers:
            pair = (marker["page_id"], marker["interaction_id"])
            expected_row = expected.get(pair)
            if expected_row is None:
                raise ValueError(
                    f"frontend interaction spec marker is foreign to current UI IA: {relative}:{pair[0]}:{pair[1]}"
                )
            readiness_status = str(expected_row.get("readiness_status") or "ready").strip().lower()
            marker_operation_id = str(marker.get("operation_id") or "").strip()
            resolved = dict(expected_row)
            if readiness_status == "p3-realization-open":
                if not marker_operation_id:
                    raise ValueError(
                        f"frontend realization-open runtime marker must select one canonical operation: {relative}:{pair[0]}:{pair[1]}"
                    )
                candidates = {
                    str(row.get("operation_id") or "").strip(): dict(row)
                    for row in expected_row.get("candidate_operations", [])
                    if isinstance(row, dict) and str(row.get("operation_id") or "").strip()
                }
                selected = candidates.get(marker_operation_id)
                if selected is None:
                    raise ValueError(
                        f"frontend realization-open runtime marker selects foreign operation: {relative}:{pair[0]}:{pair[1]}:{marker_operation_id}"
                    )
                resolved.update(selected)
            else:
                expected_operation_id = str(expected_row.get("operation_id") or "").strip()
                if marker_operation_id and expected_operation_id and marker_operation_id != expected_operation_id:
                    raise ValueError(
                        f"frontend runtime marker operation differs from current UI IA: {relative}:{pair[0]}:{pair[1]}:{marker_operation_id}"
                    )
                if marker_operation_id and not expected_operation_id:
                    resolved["operation_id"] = marker_operation_id
            resolved_marker_rows.append((marker, pair, resolved))
        binding_modes_in_spec = {
            str(resolved.get("binding_mode") or "").strip().casefold()
            for _, _, resolved in resolved_marker_rows
        }
        for clean_marker in clean_first_use_markers:
            clean_journey_id = str(clean_marker.get("journey_id") or "").strip()
            clean_persona_id = str(clean_marker.get("persona_id") or "").strip()
            if clean_journey_id not in journey_ids_in_spec:
                raise ValueError(f"frontend clean-first-use evidence is not bound to a consumer journey: {relative}:{clean_journey_id or '<missing>'}")
            if not any(mode in {"write", "read_write"} for mode in binding_modes_in_spec):
                raise ValueError(f"frontend clean-first-use evidence does not exercise a real write interaction: {relative}:{clean_journey_id}")
            if requires_business_data_discovery and not any(mode in {"read", "read_write"} for mode in binding_modes_in_spec):
                raise ValueError(f"frontend clean-first-use evidence does not exercise a real discovery/read interaction: {relative}:{clean_journey_id}")
            if requires_context_reentry and "page.reload(" not in text and text.count("page.goto(") < 2:
                raise ValueError(f"frontend clean-first-use evidence does not prove reload/re-entry context recovery: {relative}:{clean_journey_id}")
            if persona_roles and not clean_persona_id:
                matching_journey = next((row for row in journey_markers if str(row.get("journey_id") or "") == clean_journey_id), {})
                clean_persona_id = str(matching_journey.get("persona_id") or "").strip()
            clean_first_use_bindings.append(
                {"journey_id": clean_journey_id, "persona_id": clean_persona_id, "path": relative}
            )
        selected_operations: list[dict[str, str]] = []
        for marker, pair, resolved in resolved_marker_rows:
            endpoint = str(resolved.get("api_endpoint") or "").strip()
            if not endpoint or endpoint not in text:
                raise ValueError(
                    f"frontend interaction spec does not exercise current API endpoint: {relative}:{pair[0]}:{pair[1]}:{endpoint or '<missing>'}"
                )
            binding_mode = str(resolved.get("binding_mode") or "").strip().lower()
            if binding_mode in {"write", "read_write"} and "testInfo.project.name" not in text:
                raise ValueError(
                    f"frontend mutation evidence is not project-isolated: {relative}:{pair[0]}:{pair[1]}"
                )
            selected_operations.append(
                {
                    "page_id": pair[0],
                    "interaction_id": pair[1],
                    "operation_id": str(resolved.get("operation_id") or "").strip(),
                    "api_endpoint": endpoint,
                    "binding_mode": binding_mode,
                }
            )
            covered.add(pair)
        bindings.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "markers": markers,
                "selected_operations": selected_operations,
                "consumer_journeys": journey_markers,
                "consumer_pages": consumer_page_markers,
            }
        )
    missing = sorted(set(expected) - covered)
    if missing:
        raise ValueError(
            "frontend runtime interaction coverage is incomplete: "
            + ",".join(f"{page_id}:{interaction_id}" for page_id, interaction_id in missing)
        )
    if not journey_bindings:
        raise ValueError("frontend runtime requires at least one first-entry-to-outcome consumer journey spec")
    if persona_roles:
        missing_personas = sorted(set(persona_roles) - covered_personas)
        if missing_personas:
            raise ValueError("frontend terminal-role consumer journey coverage is incomplete: " + ",".join(missing_personas))
    if requires_clean_first_use and not clean_first_use_bindings:
        raise ValueError("frontend runtime requires clean-first-use consumer evidence from an empty business-data state")
    if requires_authenticated_session and authenticated_journey_spec_count <= 0:
        raise ValueError(
            "frontend authenticated consumer journey must sign in through the product session entry using runtime-isolated UI credentials; the E2E spec must not depend on session transport internals"
        )
    if requires_authenticated_session and known_page_ids is not None:
        missing_consumer_pages = sorted(known_page_ids - seen_consumer_page_ids)
        if missing_consumer_pages:
            raise ValueError(
                "frontend authenticated product lacks post-sign-in consumer page evidence: " + ",".join(missing_consumer_pages)
            )
    return {
        "specs": bindings,
        "expected_interaction_count": len(expected),
        "covered_interaction_count": len(covered),
        "missing_interactions": [],
        "consumer_journey_count": len(journey_bindings),
        "consumer_journeys": journey_bindings,
        "consumer_page_count": len(consumer_page_bindings),
        "consumer_pages": consumer_page_bindings,
        "authenticated_journey_spec_count": authenticated_journey_spec_count,
        "terminal_role_persona_count": len(persona_roles),
        "covered_terminal_role_persona_count": len(covered_personas),
        "covered_terminal_role_personas": sorted(covered_personas),
        "clean_first_use_count": len(clean_first_use_bindings),
        "clean_first_use": clean_first_use_bindings,
        "business_data_requirements": data_requirements,
    }


def _materialize_frontend_runtime_shell(*, workspace_root: Path, application: Mapping[str, Any]) -> dict[str, str]:
    required = [
        workspace_root / "apps/web/package.json",
        workspace_root / "apps/web/tsconfig.json",
        workspace_root / "apps/web/tsconfig.build.json",
        workspace_root / "apps/web/vite.config.ts",
        workspace_root / "apps/web/app/main.tsx",
        workspace_root / "apps/web/app/server.ts",
    ]
    missing = [path.relative_to(workspace_root).as_posix() for path in required if not path.is_file()]
    if missing:
        raise ValueError("frontend runtime scaffold is incomplete: " + ",".join(missing))
    app_path = workspace_root / str(application.get("path") or "")
    if not app_path.is_file() or app_path.is_symlink():
        raise ValueError("frontend runtime requires the materialized Agentic product application")
    app_sha256 = sha256_file(app_path)
    expected_app_sha256 = str(application.get("content_sha256") or "")
    if not expected_app_sha256 or app_sha256 != expected_app_sha256:
        raise ValueError("frontend runtime product application identity differs from authoring")
    index_path = workspace_root / "apps/web/index.html"
    angle = chr(60)
    index_html = (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"UTF-8\" />"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />"
        "<title>Generated Product</title></head><body><div id=\"root\"></div>"
        + angle + "script type=\"module\" src=\"/app/main.tsx\">" + angle + "/script>"
        "</body></html>\n"
    )
    write_text(index_path, index_html)
    return {
        "index_path": index_path.relative_to(workspace_root).as_posix(),
        "index_sha256": sha256_file(index_path),
        "app_path": app_path.relative_to(workspace_root).as_posix(),
        "app_sha256": app_sha256,
        "app_origin": "agentic-product-authoring-preserved",
        "web_package_sha256": sha256_file(workspace_root / "apps/web/package.json"),
        "web_server_sha256": sha256_file(workspace_root / "apps/web/app/server.ts"),
    }


def _render_frontend_playwright_config(workspace_root: Path, result_dir: Path) -> str:
    root_literal = json.dumps(str(workspace_root.resolve()), ensure_ascii=False)
    result_literal = json.dumps(str(result_dir.resolve()), ensure_ascii=False)
    return "\n".join(
        [
            "import { defineConfig, devices } from '@playwright/test';",
            f"const workspaceRoot = {root_literal};",
            f"const resultDir = {result_literal};",
            "export default defineConfig({",
            "  testDir: workspaceRoot,",
            "  outputDir: resultDir,",
            "  timeout: 30_000,",
            "  fullyParallel: false,",
            "  retries: 0,",
            "  use: { baseURL: process.env.WFF_FRONTEND_BASE_URL, trace: 'on' },",
            "  projects: [",
            "    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'] } },",
            "    { name: 'mobile-chromium', use: { ...devices['Pixel 5'] } },",
            "  ],",
            "});",
            "",
        ]
    )


def _render_frontend_route_runtime_spec(
    pages: list[dict[str, Any]],
    access_requirements: Mapping[str, Any] | None = None,
) -> str:
    requirements = dict(access_requirements or {})
    requires_authenticated_session = bool(requirements.get("requires_authenticated_session"))
    persona_by_role: dict[str, str] = {}
    for raw in requirements.get("test_personas", []):
        if not isinstance(raw, Mapping):
            continue
        persona_id = str(raw.get("persona_id") or "").strip()
        roles = [str(role).strip() for role in raw.get("roles", []) if str(role).strip()]
        if persona_id and len(roles) == 1:
            persona_by_role[roles[0]] = persona_id
    page_persona: dict[str, str] = {}
    qualification = requirements.get("terminal_role_qualification")
    role_page_coverage = qualification.get("role_page_coverage", {}) if isinstance(qualification, Mapping) else {}
    if isinstance(role_page_coverage, Mapping):
        for role, page_ids in role_page_coverage.items():
            persona_id = persona_by_role.get(str(role).strip(), "")
            if not persona_id or not isinstance(page_ids, list):
                continue
            for page_id in page_ids:
                normalized = str(page_id).strip()
                if normalized:
                    page_persona[normalized] = persona_id
    default_persona_id = next(iter(persona_by_role.values()), "")
    pages_json = json.dumps(
        [
            {
                "pageId": row["page_id"],
                "route": row["route"],
                "personaId": page_persona.get(str(row["page_id"]), default_persona_id),
            }
            for row in pages
        ],
        ensure_ascii=False,
        indent=2,
    )
    requires_auth_json = "true" if requires_authenticated_session else "false"
    default_persona_json = json.dumps(default_persona_id, ensure_ascii=False)
    return f"""import {{ expect, test }} from '@playwright/test';
import {{ mkdirSync }} from 'node:fs';
import {{ join }} from 'node:path';

const pages = {pages_json} as const;
const requiresAuthenticatedSession = {requires_auth_json};
const defaultPersonaId = {default_persona_json};
const screenshotDir = process.env.WFF_FRONTEND_SCREENSHOT_DIR ?? 'frontend-runtime-screenshots';
mkdirSync(screenshotDir, {{ recursive: true }});

function credential(personaId: string, kind: 'USERNAME' | 'PASSWORD'): string {{
  const prefix = personaId.replace(/[^A-Za-z0-9]+/g, '_').toUpperCase();
  return process.env[`WFF_FRONTEND_TEST_${{prefix}}_${{kind}}`]
    ?? process.env[`WFF_FRONTEND_TEST_${{kind}}`]
    ?? '';
}}

async function signInThroughProduct(page: import('@playwright/test').Page, personaId: string) {{
  if (!requiresAuthenticatedSession) return;
  const username = credential(personaId || defaultPersonaId, 'USERNAME');
  const password = credential(personaId || defaultPersonaId, 'PASSWORD');
  expect(username).not.toBe('');
  expect(password).not.toBe('');
  await page.goto('/auth/login', {{ waitUntil: 'networkidle' }});
  const usernameInput = page.locator('input[autocomplete="username"]');
  const passwordInput = page.locator('input[autocomplete="current-password"]');
  await expect(usernameInput).toBeVisible();
  await expect(passwordInput).toBeVisible();
  await usernameInput.fill(username);
  await passwordInput.fill(password);
  await page.locator('form button[type="submit"]').click();
  await expect(usernameInput).toHaveCount(0);
}}

async function assertAccessibilityBaseline(page: import('@playwright/test').Page) {{
  const findings = await page.locator('body').evaluate(() => {{
    const visible = (element: Element) => {{
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.visibility !== 'hidden' && style.display !== 'none' && Number(style.opacity || '1') > 0 && rect.width > 0 && rect.height > 0;
    }};
    const accessibleName = (element: Element) => {{
      const ariaLabel = element.getAttribute('aria-label')?.trim() ?? '';
      const labelledBy = (element.getAttribute('aria-labelledby') ?? '')
        .split(/\s+/)
        .filter(Boolean)
        .map((id) => document.getElementById(id)?.textContent?.trim() ?? '')
        .filter(Boolean)
        .join(' ');
      const formLabels = 'labels' in element
        ? Array.from((element as HTMLInputElement).labels ?? []).map((label) => label.textContent?.trim() ?? '').filter(Boolean).join(' ')
        : '';
      const text = (element.textContent ?? '').trim();
      return ariaLabel || labelledBy || formLabels || element.getAttribute('alt')?.trim() || element.getAttribute('title')?.trim() || element.getAttribute('placeholder')?.trim() || text;
    }};
    const interactive = Array.from(document.querySelectorAll('button, input:not([type="hidden"]), select, textarea, a[href]')).filter(visible);
    const unlabeledControls = interactive.filter((element) => !accessibleName(element)).map((element) => element.tagName.toLowerCase());

    const parseRgb = (value: string): [number, number, number] | null => {{
      const match = /rgba?\(\s*([\d.]+)[, ]+\s*([\d.]+)[, ]+\s*([\d.]+)/i.exec(value);
      return match ? [Number(match[1]), Number(match[2]), Number(match[3])] : null;
    }};
    const luminance = (rgb: [number, number, number]) => {{
      const linear = rgb.map((channel) => {{
        const value = channel / 255;
        return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      }});
      return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
    }};
    const contrastRatio = (left: [number, number, number], right: [number, number, number]) => {{
      const a = luminance(left);
      const b = luminance(right);
      return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    }};
    const effectiveBackground = (element: Element): [number, number, number] => {{
      let current: Element | null = element;
      while (current) {{
        const value = getComputedStyle(current).backgroundColor;
        const rgba = /rgba\([^)]*,\s*([\d.]+)\s*\)/i.exec(value);
        const rgb = parseRgb(value);
        if (rgb && (!rgba || Number(rgba[1]) > 0)) return rgb;
        current = current.parentElement;
      }}
      return [255, 255, 255];
    }};
    const textElements = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6,p,span,label,a,button,li,td,th,legend')).filter(
      (element) => visible(element) && Boolean((element.textContent ?? '').trim()),
    );
    const contrastFailures = textElements.flatMap((element) => {{
      const style = getComputedStyle(element);
      const foreground = parseRgb(style.color);
      if (!foreground) return [];
      const fontSize = Number.parseFloat(style.fontSize || '16');
      const fontWeight = Number.parseInt(style.fontWeight || '400', 10) || 400;
      const threshold = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700) ? 3 : 4.5;
      const ratio = contrastRatio(foreground, effectiveBackground(element));
      return ratio + 0.01 < threshold ? [`${{element.tagName.toLowerCase()}}:${{ratio.toFixed(2)}}<${{threshold}}`] : [];
    }});
    const viewportWidth = document.documentElement.clientWidth;
    const documentHorizontalOverflow = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - viewportWidth;
    return {{
      mainCount: document.querySelectorAll('main').length,
      headingCount: document.querySelectorAll('h1,h2,h3,h4,h5,h6').length,
      focusableCount: interactive.length,
      unlabeledControls,
      contrastFailures,
      documentHorizontalOverflow,
    }};
  }});
  expect(findings.mainCount).toBeGreaterThan(0);
  expect(findings.headingCount).toBeGreaterThan(0);
  expect(findings.unlabeledControls).toEqual([]);
  expect(findings.contrastFailures).toEqual([]);
  expect(findings.documentHorizontalOverflow).toBeLessThanOrEqual(1);
  if (findings.focusableCount > 0) {{
    await page.keyboard.press('Tab');
    const hasVisibleFocusTarget = await page.evaluate(() => {{
      const active = document.activeElement;
      return Boolean(active && active !== document.body && active !== document.documentElement);
    }});
    expect(hasVisibleFocusTarget).toBe(true);
  }}
}}

for (const appPage of pages) {{
  test(`runtime route ${{appPage.pageId}}`, async ({{ page, request }}, testInfo) => {{
    await signInThroughProduct(page, appPage.personaId);
    const browserErrors: string[] = [];
    page.on('console', (message) => {{ if (message.type() === 'error') browserErrors.push(message.text()); }});
    page.on('pageerror', (error) => browserErrors.push(String(error)));
    const response = await page.goto(appPage.route, {{ waitUntil: 'networkidle' }});
    expect(response?.ok()).toBeTruthy();
    const surface = page.locator(`main[data-phase3-page-id="${{appPage.pageId}}"][data-phase3-surface="${{appPage.route}}"]`);
    await expect(surface).toBeVisible();
    await expect(surface).not.toHaveText('');
    await assertAccessibilityBaseline(page);
    const runtimeProof = await request.get('/runtime-proof');
    expect(runtimeProof.ok()).toBeTruthy();
    expect((await runtimeProof.json()).ok).toBe(true);
    expect(browserErrors).toEqual([]);
    const safeId = appPage.pageId.replace(/[^A-Za-z0-9_.-]+/g, '-');
    const screenshotPath = join(screenshotDir, `${{testInfo.project.name}}-${{safeId}}.png`);
    try {{ await page.screenshot({{ path: screenshotPath, fullPage: true }}); }}
    catch {{ await page.screenshot({{ path: screenshotPath, fullPage: false }}); }}
  }});
}}

test('unknown route exposes product recovery instead of blank output', async ({{ page }}) => {{
  await signInThroughProduct(page, defaultPersonaId);
  const response = await page.goto('/__wff-not-found-probe__', {{ waitUntil: 'networkidle' }});
  expect(response?.ok()).toBeTruthy();
  const body = page.locator('body');
  await expect(body).not.toHaveText('');
  await expect(body).toContainText(/404|not found|page missing|未找到|找不到|不存在/i);
  expect(await page.locator('a[href], button').count()).toBeGreaterThan(0);
}});
"""


def _prepare_frontend_browser_evidence(
    *,
    workspace_root: Path,
    output_path: Path | None,
    authoring_report_path: Path,
    ui_ia_contract_path: Path,
    interaction_specs: list[Path],
) -> dict[str, Any]:
    identity = _validate_frontend_authoring_runtime_input(
        workspace_root=workspace_root,
        authoring_report_path=authoring_report_path,
        ui_ia_contract_path=ui_ia_contract_path,
    )
    authored_spec_paths = [
        Path(str(row.get("path") or ""))
        for row in identity.get("authored_e2e_specs", [])
        if isinstance(row, dict) and str(row.get("path") or "").strip()
    ]
    combined_spec_paths: list[Path] = []
    seen_spec_paths: set[str] = set()
    for raw_spec in [*authored_spec_paths, *interaction_specs]:
        candidate = raw_spec if raw_spec.is_absolute() else workspace_root / raw_spec
        key = _workspace_relative_path(workspace_root, candidate, label="frontend interaction spec")
        if not key or key in seen_spec_paths:
            continue
        seen_spec_paths.add(key)
        combined_spec_paths.append(candidate)
    auth_integration_mode = _runtime_auth_integration_mode(workspace_root)
    interaction_coverage = _validate_frontend_interaction_specs(
        workspace_root=workspace_root,
        spec_paths=combined_spec_paths,
        expected_interactions=identity["expected_interactions"],
        known_routes={str(row["route"]) for row in identity["pages"]},
        known_page_ids={str(row["page_id"]) for row in identity["pages"]},
        access_requirements=identity.get("product_access_requirements", {}),
        business_data_requirements=identity.get("business_data_requirements", {}),
        auth_integration_mode=auth_integration_mode,
    )
    runtime_shell = _materialize_frontend_runtime_shell(
        workspace_root=workspace_root,
        application=identity["application"],
    )
    run_token = identity["content_digest"].removeprefix("sha256:")[:16] or "current"
    evidence_dir = workspace_root / "evidence" / "frontend-runtime-evidence" / run_token
    evidence_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = evidence_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    config_path = evidence_dir / "playwright.config.ts"
    route_spec_path = evidence_dir / "wff-frontend-runtime-routes.spec.ts"
    result_dir = evidence_dir / "playwright-results"
    result_dir.mkdir(parents=True, exist_ok=True)
    write_text(config_path, _render_frontend_playwright_config(workspace_root, result_dir))
    write_text(
        route_spec_path,
        _render_frontend_route_runtime_spec(
            identity["pages"],
            identity.get("product_access_requirements", {}),
        ),
    )
    return {
        "identity": identity,
        "interaction_coverage": interaction_coverage,
        "runtime_shell": runtime_shell,
        "auth_integration_mode": auth_integration_mode,
        "evidence_dir": evidence_dir,
        "screenshot_dir": screenshot_dir,
        "config_path": config_path,
        "route_spec_path": route_spec_path,
        "route_spec_sha256": sha256_file(route_spec_path),
        "result_dir": result_dir,
        "playwright_report_path": evidence_dir / "playwright-report.json",
    }


def _collect_frontend_screenshot_bindings(screenshot_dir: Path) -> list[dict[str, str]]:
    return [
        {"path": str(path), "sha256": sha256_file(path)}
        for path in sorted(screenshot_dir.glob("*.png"))
        if path.is_file() and not path.is_symlink()
    ]


def _consumer_page_screenshot_coverage(
    screenshots: list[dict[str, str]],
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    expected_projects = ("desktop-chromium", "mobile-chromium")
    expected: list[str] = []
    observed_names = {Path(str(row.get("path") or "")).name for row in screenshots}
    bindings: list[dict[str, str]] = []
    for page in pages:
        page_id = str(page.get("page_id") or "").strip()
        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", page_id)
        for project in expected_projects:
            name = f"{project}-consumer-{safe_id}.png"
            expected.append(name)
            if name in observed_names:
                binding = next(
                    (row for row in screenshots if Path(str(row.get("path") or "")).name == name),
                    None,
                )
                if binding is not None:
                    bindings.append({**binding, "page_id": page_id, "project": project})
    missing = [name for name in expected if name not in observed_names]
    return {
        "status": "pass" if not missing else "fail",
        "expected_count": len(expected),
        "observed_count": len(bindings),
        "missing": missing,
        "screenshots": bindings,
    }


def _collect_frontend_trace_bindings(result_dir: Path) -> list[dict[str, str]]:
    return [
        {"path": str(path), "sha256": sha256_file(path)}
        for path in sorted(result_dir.rglob("trace.zip"))
        if path.is_file() and not path.is_symlink()
    ]


def _frontend_auth_runtime_proof(
    probe: Mapping[str, Any],
    access_requirements: Mapping[str, Any] | None,
    *,
    backend_auth_compatibility_mode: str = "",
) -> dict[str, Any]:
    requirements = dict(access_requirements or {})
    requires_authenticated_session = bool(requirements.get("requires_authenticated_session"))
    payload: dict[str, Any] = {}
    body_excerpt = str(probe.get("body_excerpt") or "").strip()
    if body_excerpt:
        try:
            raw_payload = json.loads(body_excerpt)
            if isinstance(raw_payload, dict):
                payload = raw_payload
        except json.JSONDecodeError:
            payload = {}
    traffic = payload.get("frontend_api_traffic") if isinstance(payload.get("frontend_api_traffic"), dict) else {}
    api_request_count = int(traffic.get("api_request_count", 0) or 0)
    authorized_api_request_count = int(traffic.get("authorized_api_request_count", 0) or 0)
    browser_authorization_header_request_count = int(traffic.get("browser_authorization_header_request_count", 0) or 0)
    phase3_auth_context_request_count = int(traffic.get("phase3_auth_context_request_count", 0) or 0)
    frozen_backend_auth_context_request_count = int(traffic.get("frozen_backend_auth_context_request_count", 0) or 0)
    adapter_mode = str(payload.get("auth_adapter_mode") or "").strip()
    compatibility_mode = str(backend_auth_compatibility_mode or "").strip()
    failures: list[str] = []
    if not bool(probe.get("ok")):
        failures.append("post-browser-runtime-proof-unavailable")
    if browser_authorization_header_request_count > 0:
        failures.append("consumer-used-browser-authorization-header")
    if phase3_auth_context_request_count > 0:
        failures.append("consumer-used-phase3-auth-context-header")
    if requires_authenticated_session:
        if api_request_count <= 0:
            failures.append("consumer-business-api-request-missing")
        if compatibility_mode == "frozen-phase3-header":
            if adapter_mode != "frozen-backend-phase3-header":
                failures.append("frozen-backend-auth-adapter-not-active")
            if frozen_backend_auth_context_request_count <= 0:
                failures.append("frozen-backend-bff-auth-context-missing")
        elif authorized_api_request_count <= 0:
            failures.append("consumer-bearer-api-request-missing")
    return {
        "status": "pass" if not failures else "fail",
        "requires_authenticated_session": requires_authenticated_session,
        "normal_api_auth_transport": str(requirements.get("normal_api_auth_transport") or ""),
        "api_request_count": api_request_count,
        "authorized_api_request_count": authorized_api_request_count,
        "browser_authorization_header_request_count": browser_authorization_header_request_count,
        "phase3_auth_context_request_count": phase3_auth_context_request_count,
        "frozen_backend_auth_context_request_count": frozen_backend_auth_context_request_count,
        "backend_auth_compatibility_mode": compatibility_mode,
        "auth_adapter_mode": adapter_mode,
        "failures": failures,
        "claim_ceiling": (
            "Factual browser-to-BFF auth proof over a frozen backend compatibility adapter; the browser did not inject identity headers, "
            "but the BFF translated the product session into the frozen backend's accepted internal auth-context transport. This does not "
            "upgrade the frozen backend to Bearer authentication or prove identity-provider assurance."
            if compatibility_mode == "frozen-phase3-header"
            else "Factual browser-to-Web-proxy auth transport proof only; it proves current consumer business traffic used normal Bearer "
            "transport and did not use the Phase-3 auth-context shortcut, but it does not prove identity-provider assurance."
        ),
    }


def run_phase3_runtime_smoke(
    *,
    workspace_root: Path,
    output_path: Path | None = None,
    image_tag: str = "",
    service_url: str = "http://127.0.0.1:3000",
    runtime_plan: dict[str, object] | None = None,
    startup_timeout_seconds: int = 45,
    command_timeout_seconds: int = 300,
    cleanup: bool = True,
    output_locale: str | None = None,
    run_started_service_smoke: bool = True,
    started_service_smoke_fn=run_phase3_started_service_smoke,
    include_frontend: bool = False,
    frontend_authoring_report_path: Path | None = None,
    frontend_ui_ia_contract_path: Path | None = None,
    frontend_interaction_specs: list[Path] | None = None,
    install_playwright_browser: bool = False,
) -> dict[str, Any]:
    workspace_root = workspace_root.resolve()
    dockerfile_path = workspace_root / "Dockerfile"
    compose_prod_path = workspace_root / "docker-compose.prod.yml"
    failures: list[str] = []
    warnings: list[str] = []
    commands: dict[str, Any] = {}
    probes: dict[str, Any] = {}
    started_service_smoke_report: dict[str, Any] = {}
    frontend_browser_context: dict[str, Any] = {}
    frontend_browser_evidence: dict[str, Any] = {
        "requested": include_frontend,
        "status": "not-requested" if not include_frontend else "preflight-pending",
        "claim_ceiling": "Browser/runtime evidence only; no product/UI/P4/production/UAT judgment.",
    }

    docker_available = bool(shutil.which("docker"))
    compose_command = detect_compose_command()
    compose_available = bool(compose_command)
    pnpm_command = detect_pnpm_command()
    if runtime_plan is None:
        runtime_plan = _build_runtime_smoke_plan(
            workspace_root=workspace_root,
            service_url=service_url,
        )
    workspace_slug = str(runtime_plan["workspace_slug"])
    normalized_image_tag = image_tag or f"{workspace_slug}:phase3-smoke"
    project_name = str(runtime_plan["compose_project_name"])
    requested_service_url_input = str(runtime_plan["requested_service_url_input"])
    requested_service_url = requested_service_url_input
    effective_service_url = str(runtime_plan["service_url"])
    selected_host_ports = dict(runtime_plan["selected_host_ports"])
    effective_web_url = str(runtime_plan.get("web_url") or f"http://127.0.0.1:{selected_host_ports['WEB_HOST_PORT']}")
    runtime_smoke_env = dict(runtime_plan["runtime_env"])
    if effective_service_url != requested_service_url_input:
        warnings.append("runtime_smoke_service_url_adjusted")

    if include_frontend:
        if not pnpm_command:
            failures.append("frontend_browser_pnpm_missing")
        try:
            if frontend_authoring_report_path is None or frontend_ui_ia_contract_path is None:
                raise ValueError("frontend runtime requires authoring report and exact UI IA contract")
            frontend_browser_context = _prepare_frontend_browser_evidence(
                workspace_root=workspace_root,
                output_path=output_path,
                authoring_report_path=frontend_authoring_report_path.resolve(),
                ui_ia_contract_path=frontend_ui_ia_contract_path.resolve(),
                interaction_specs=list(frontend_interaction_specs or []),
            )
            runtime_smoke_env = _provision_frontend_runtime_auth_fixture(
                runtime_smoke_env,
                frontend_browser_context["identity"].get("product_access_requirements", {}),
                integration_mode=str(frontend_browser_context.get("auth_integration_mode") or "runtime-agnostic-real-auth"),
                backend_auth_compatibility_mode=str(
                    frontend_browser_context["identity"].get("backend_auth_compatibility_mode") or ""
                ),
            )
            frontend_browser_evidence.update(
                {
                    "status": "preflight-pass",
                    "authoring_identity": frontend_browser_context["identity"],
                    "interaction_coverage": frontend_browser_context["interaction_coverage"],
                    "runtime_shell": frontend_browser_context["runtime_shell"],
                    "route_spec_path": _workspace_relative_path(
                        workspace_root,
                        frontend_browser_context["route_spec_path"],
                        label="frontend route evidence spec",
                    ),
                    "route_spec_sha256": frontend_browser_context["route_spec_sha256"],
                }
            )
        except ValueError as exc:
            failures.append("frontend_browser_preflight_failed")
            frontend_browser_evidence.update({"status": "preflight-fail", "failures": [str(exc)]})

    if not dockerfile_path.exists():
        failures.append("dockerfile_missing")
    if not compose_prod_path.exists():
        failures.append("compose_prod_missing")
    if not docker_available:
        failures.append("docker_missing")
    if docker_available and not compose_available:
        failures.append("docker_compose_missing")

    image_build_passed = False
    compose_up_passed = False
    migration_passed = False
    health_probe_passed = False
    readiness_probe_passed = False
    web_root_probe_passed = False
    web_runtime_proof_passed = False
    frontend_browser_evidence_green = False
    clean_first_use_database_evidence: dict[str, Any] = {
        "status": "not-required",
        "table_counts": {},
        "business_row_count": 0,
        "claim_ceiling": "Pre-browser PostgreSQL public-table emptiness only; later browser writes are evaluated separately.",
    }
    started_service_smoke_green = False
    compose_down_passed = not cleanup
    compose_started = False
    active_runtime_smoke_env = runtime_smoke_env
    compose_runtime_services = ["api", "web"] if include_frontend else ["api"]

    if not failures:
        try:
            commands["image_build"] = run_command(
                [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "build", *compose_runtime_services],
                workspace_root,
                command_timeout_seconds,
                runtime_smoke_env,
            )
            if not commands["image_build"].get("passed") and command_has_transient_network_failure(commands["image_build"]):
                image_build_attempts = [commands["image_build"]]
                warnings.append("docker_image_build_retried_after_transient_failure")
                commands["image_build"] = run_command(
                    [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "build", *compose_runtime_services],
                    workspace_root,
                    command_timeout_seconds,
                    runtime_smoke_env,
                )
                image_build_attempts.append(commands["image_build"])
                commands["image_build_attempts"] = image_build_attempts
            image_build_passed = bool(commands["image_build"].get("passed"))
            if not image_build_passed:
                failures.append("docker_image_build_failed")

            if image_build_passed:
                runtime_smoke_attempts: list[dict[str, Any]] = []
                excluded_ports: set[int] = set()

                def reallocate_ports_after_bind_conflict(attempt_record: dict[str, Any]) -> None:
                    nonlocal compose_down_passed
                    nonlocal effective_service_url
                    nonlocal effective_web_url
                    nonlocal runtime_smoke_env
                    nonlocal selected_host_ports
                    commands["compose_down"] = run_command(
                        [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "down", "--remove-orphans", "-v"],
                        workspace_root,
                        command_timeout_seconds,
                        active_runtime_smoke_env,
                    )
                    attempt_record["compose_down"] = commands["compose_down"]
                    compose_down_passed = bool(commands["compose_down"].get("passed"))
                    if not compose_down_passed:
                        warnings.append("docker_compose_down_failed")
                    excluded_ports.update(int(port) for port in selected_host_ports.values())
                    replanned_runtime_plan = _build_runtime_smoke_plan(
                        workspace_root=workspace_root,
                        service_url=requested_service_url_input,
                        exclude_ports=excluded_ports,
                    )
                    selected_host_ports = dict(replanned_runtime_plan["selected_host_ports"])
                    effective_service_url = str(replanned_runtime_plan["service_url"])
                    effective_web_url = str(replanned_runtime_plan.get("web_url") or f"http://127.0.0.1:{selected_host_ports['WEB_HOST_PORT']}")
                    runtime_smoke_env = dict(replanned_runtime_plan["runtime_env"])
                    if include_frontend and frontend_browser_context:
                        runtime_smoke_env = _provision_frontend_runtime_auth_fixture(
                            runtime_smoke_env,
                            frontend_browser_context["identity"].get("product_access_requirements", {}),
                            integration_mode=str(frontend_browser_context.get("auth_integration_mode") or "runtime-agnostic-real-auth"),
                            backend_auth_compatibility_mode=str(
                                frontend_browser_context["identity"].get("backend_auth_compatibility_mode") or ""
                            ),
                        )
                    warnings.append("runtime_smoke_ports_reallocated_after_bind_conflict")
                    if "runtime_smoke_service_url_adjusted" not in warnings and effective_service_url != requested_service_url_input:
                        warnings.append("runtime_smoke_service_url_adjusted")

                for attempt_index in range(1, 4):
                    active_runtime_smoke_env = runtime_smoke_env
                    attempt_record: dict[str, Any] = {
                        "attempt": attempt_index,
                        "selected_host_ports": dict(selected_host_ports),
                        "service_url": effective_service_url,
                        "web_url": effective_web_url,
                    }
                    commands["migration"] = run_command(
                        [
                            *compose_command,
                            "-p",
                            project_name,
                            "-f",
                            str(compose_prod_path),
                            "run",
                            "--rm",
                            "api",
                            "sh",
                            "-lc",
                            "until node apps/api/dist/runtime/migrate.js; do sleep 1; done",
                        ],
                        workspace_root,
                        command_timeout_seconds,
                        active_runtime_smoke_env,
                    )
                    attempt_record["migration"] = commands["migration"]
                    migration_passed = bool(commands["migration"].get("passed"))
                    compose_started = True
                    if not migration_passed and command_has_host_port_bind_conflict(commands["migration"]) and attempt_index < 3:
                        runtime_smoke_attempts.append(attempt_record)
                        reallocate_ports_after_bind_conflict(attempt_record)
                        migration_passed = False
                        continue
                    if not migration_passed:
                        runtime_smoke_attempts.append(attempt_record)
                        failures.append("docker_migration_failed")
                        break

                    commands["compose_up"] = run_command(
                        [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "up", "-d", *compose_runtime_services],
                        workspace_root,
                        command_timeout_seconds,
                        active_runtime_smoke_env,
                    )
                    attempt_record["compose_up"] = commands["compose_up"]
                    compose_up_passed = bool(commands["compose_up"].get("passed"))
                    if not compose_up_passed and command_has_host_port_bind_conflict(commands["compose_up"]) and attempt_index < 3:
                        runtime_smoke_attempts.append(attempt_record)
                        reallocate_ports_after_bind_conflict(attempt_record)
                        compose_up_passed = False
                        migration_passed = False
                        continue
                    runtime_smoke_attempts.append(attempt_record)
                    if not compose_up_passed:
                        failures.append("docker_compose_up_failed")
                        break

                    probes["healthz"] = wait_for_probe(
                        f"{effective_service_url.rstrip('/')}/healthz",
                        startup_timeout_seconds,
                        2.0,
                    )
                    health_probe_passed = bool(probes["healthz"].get("ok"))
                    if not health_probe_passed:
                        failures.append("health_probe_failed")
                        break

                    probes["readyz"] = wait_for_probe(
                        f"{effective_service_url.rstrip('/')}/readyz",
                        startup_timeout_seconds,
                        2.0,
                    )
                    readiness_probe_passed = bool(probes["readyz"].get("ok"))
                    if not readiness_probe_passed:
                        failures.append("readiness_probe_failed")
                    if include_frontend and readiness_probe_passed and frontend_browser_context:
                        data_requirements = frontend_browser_context["identity"].get("business_data_requirements", {})
                        if bool(data_requirements.get("clean_first_use_required")):
                            clean_probe_sql = (
                                "sql=$(psql -U postgres -d app -At -c \"SELECT format('SELECT %L, count(*) FROM %I.%I;', "
                                "tablename, schemaname, tablename) FROM pg_tables WHERE schemaname='public' ORDER BY tablename;\"); "
                                "if [ -n \"$sql\" ]; then printf '%s\\n' \"$sql\" | psql -U postgres -d app -At; fi"
                            )
                            commands["frontend_clean_database_probe"] = run_command(
                                [
                                    *compose_command,
                                    "-p",
                                    project_name,
                                    "-f",
                                    str(compose_prod_path),
                                    "exec",
                                    "-T",
                                    "postgres",
                                    "sh",
                                    "-lc",
                                    clean_probe_sql,
                                ],
                                workspace_root,
                                command_timeout_seconds,
                                active_runtime_smoke_env,
                            )
                            table_counts = _parse_postgres_table_counts(
                                str(commands["frontend_clean_database_probe"].get("stdout") or "")
                            )
                            clean_first_use_database_evidence = _evaluate_clean_first_use_table_counts(
                                data_requirements,
                                table_counts,
                                probe_passed=bool(commands["frontend_clean_database_probe"].get("passed")),
                            )
                            clean_first_use_database_evidence.update(
                                {
                                    "compose_project_name": project_name,
                                    "database_reset_posture": "run-scoped-compose-project-with-volume-removal",
                                }
                            )
                            if clean_first_use_database_evidence["status"] != "pass":
                                failures.append(
                                    str(clean_first_use_database_evidence.get("failure_code") or "frontend_clean_first_use_database_not_empty")
                                )
                        probes["web_root"] = wait_for_probe(
                            f"{effective_web_url.rstrip('/')}/",
                            startup_timeout_seconds,
                            2.0,
                        )
                        web_root_probe_passed = bool(probes["web_root"].get("ok"))
                        if not web_root_probe_passed:
                            failures.append("web_root_probe_failed")
                        probes["web_runtime_proof"] = wait_for_probe(
                            f"{effective_web_url.rstrip('/')}/runtime-proof",
                            startup_timeout_seconds,
                            2.0,
                        )
                        web_runtime_proof_passed = bool(probes["web_runtime_proof"].get("ok"))
                        if not web_runtime_proof_passed:
                            failures.append("web_runtime_proof_failed")
                    break
                if runtime_smoke_attempts:
                    commands["runtime_smoke_attempts"] = runtime_smoke_attempts

            if (
                include_frontend
                and frontend_browser_context
                and health_probe_passed
                and readiness_probe_passed
                and web_root_probe_passed
                and web_runtime_proof_passed
            ):
                browser_env = dict(active_runtime_smoke_env)
                browser_env["WFF_FRONTEND_BASE_URL"] = effective_web_url
                browser_env["WFF_FRONTEND_SCREENSHOT_DIR"] = str(frontend_browser_context["screenshot_dir"])
                browser_install_passed = True
                if install_playwright_browser:
                    commands["playwright_install"] = run_command(
                        pnpm_command + ["exec", "playwright", "install", "chromium"],
                        workspace_root,
                        command_timeout_seconds,
                        browser_env,
                    )
                    browser_install_passed = bool(commands["playwright_install"].get("passed"))
                    if not browser_install_passed:
                        failures.append("playwright_browser_install_failed")
                if browser_install_passed:
                    config_rel = _workspace_relative_path(
                        workspace_root,
                        frontend_browser_context["config_path"],
                        label="Playwright config",
                    )
                    route_spec_rel = _workspace_relative_path(
                        workspace_root,
                        frontend_browser_context["route_spec_path"],
                        label="frontend route evidence spec",
                    )
                    interaction_spec_paths = [
                        str(row.get("path") or "")
                        for row in frontend_browser_context["interaction_coverage"].get("specs", [])
                        if str(row.get("path") or "")
                    ]
                    commands["playwright"] = run_command(
                        pnpm_command
                        + [
                            "exec",
                            "playwright",
                            "test",
                            "--config",
                            config_rel,
                            "--reporter=json",
                            route_spec_rel,
                            *interaction_spec_paths,
                        ],
                        workspace_root,
                        command_timeout_seconds,
                        browser_env,
                    )
                    playwright_payload, playwright_summary = parse_playwright_json_output(
                        str(commands["playwright"].get("stdout") or "")
                    )
                    if playwright_payload:
                        write_text(
                            frontend_browser_context["playwright_report_path"],
                            json.dumps(playwright_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        )
                    screenshots = _collect_frontend_screenshot_bindings(frontend_browser_context["screenshot_dir"])
                    traces = _collect_frontend_trace_bindings(frontend_browser_context["result_dir"])
                    expected_screenshot_count = len(frontend_browser_context["identity"]["pages"]) * 2
                    access_requirements = frontend_browser_context["identity"].get("product_access_requirements", {})
                    requires_authenticated_session = bool(access_requirements.get("requires_authenticated_session"))
                    consumer_page_screenshot_coverage = _consumer_page_screenshot_coverage(
                        screenshots,
                        frontend_browser_context["identity"]["pages"],
                    )
                    review_screenshots = (
                        list(consumer_page_screenshot_coverage["screenshots"])
                        if requires_authenticated_session
                        else list(screenshots)
                    )
                    expected_trace_count = int(playwright_summary.get("expected", 0) or 0)
                    project_names = set(playwright_summary.get("project_names", []))
                    probes["web_runtime_proof_after_browser"] = wait_for_probe(
                        f"{effective_web_url.rstrip('/')}/runtime-proof",
                        5,
                        0.2,
                    )
                    auth_runtime_proof = _frontend_auth_runtime_proof(
                        probes["web_runtime_proof_after_browser"],
                        frontend_browser_context["identity"].get("product_access_requirements", {}),
                        backend_auth_compatibility_mode=str(
                            frontend_browser_context["identity"].get("backend_auth_compatibility_mode") or ""
                        ),
                    )
                    frontend_browser_evidence_green = bool(
                        commands["playwright"].get("passed")
                        and playwright_summary.get("valid")
                        and {"desktop-chromium", "mobile-chromium"}.issubset(project_names)
                        and len(screenshots) >= expected_screenshot_count
                        and (not requires_authenticated_session or consumer_page_screenshot_coverage["status"] == "pass")
                        and expected_trace_count > 0
                        and len(traces) >= expected_trace_count
                        and auth_runtime_proof["status"] == "pass"
                    )
                    frontend_browser_evidence.update(
                        {
                            "status": "pass" if frontend_browser_evidence_green else "fail",
                            "web_url": effective_web_url,
                            "playwright": playwright_summary,
                            "playwright_report_path": (
                                _workspace_relative_path(
                                    workspace_root,
                                    frontend_browser_context["playwright_report_path"],
                                    label="Playwright JSON report",
                                )
                                if frontend_browser_context["playwright_report_path"].is_file()
                                else ""
                            ),
                            "playwright_report_sha256": (
                                sha256_file(frontend_browser_context["playwright_report_path"])
                                if frontend_browser_context["playwright_report_path"].is_file()
                                else ""
                            ),
                            "playwright_result_dir": _workspace_relative_path(
                                workspace_root,
                                frontend_browser_context["result_dir"],
                                label="Playwright result directory",
                            ),
                            "interaction_specs": frontend_browser_context["interaction_coverage"].get("specs", []),
                            "product_access_requirements": frontend_browser_context["identity"].get("product_access_requirements", {}),
                            "business_data_requirements": frontend_browser_context["identity"].get("business_data_requirements", {}),
                            "project_language_requirements": frontend_browser_context["identity"].get("project_language_requirements", {}),
                            "clean_first_use_database_evidence": clean_first_use_database_evidence,
                            "auth_runtime_proof": auth_runtime_proof,
                            "accessibility_evidence": {
                                "status": "pass" if frontend_browser_evidence_green else "not-proven",
                                "source": "generated-browser-route-evidence",
                                "route_spec_path": route_spec_rel,
                                "route_spec_sha256": frontend_browser_context["route_spec_sha256"],
                                "checks": [
                                    "semantic-main-and-heading",
                                    "interactive-accessible-name",
                                    "keyboard-focus-target",
                                    "measured-text-contrast",
                                    "viewport-horizontal-overflow",
                                    "desktop-mobile-execution",
                                ],
                                "claim_ceiling": "Mechanical browser accessibility baseline only; it does not replace expert accessibility audit or human assistive-technology testing.",
                            },
                            "screenshots": screenshots,
                            "review_screenshots": review_screenshots,
                            "consumer_page_screenshot_coverage": consumer_page_screenshot_coverage,
                            "expected_screenshot_count": expected_screenshot_count,
                            "browser_traces": traces,
                            "expected_trace_count": expected_trace_count,
                            "web_probes": {
                                "root": probes.get("web_root", {}),
                                "runtime_proof": probes.get("web_runtime_proof", {}),
                                "runtime_proof_after_browser": probes.get("web_runtime_proof_after_browser", {}),
                            },
                        }
                    )
                    if not frontend_browser_evidence_green:
                        failures.append("frontend_browser_execution_failed")

            if run_started_service_smoke and health_probe_passed and readiness_probe_passed:
                started_service_smoke_output_path = (
                    output_path.resolve().parent / "started-service-smoke-report.json"
                    if output_path is not None
                    else workspace_root / "started-service-smoke-report.json"
                )
                started_service_smoke_report = started_service_smoke_fn(
                    workspace_root=workspace_root,
                    service_url=effective_service_url,
                    auth_secret=runtime_smoke_env["AUTH_TOKEN_SECRET"],
                    output_path=started_service_smoke_output_path,
                )
                started_service_smoke_green = str(started_service_smoke_report.get("verdict", "")).strip().lower() == "pass"
                if not started_service_smoke_green:
                    failures.append("started_service_smoke_failed")
        finally:
            if cleanup and compose_available and (compose_started or commands.get("compose_up")):
                commands["compose_down"] = run_command(
                    [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "down", "--remove-orphans", "-v"],
                    workspace_root,
                    command_timeout_seconds,
                    active_runtime_smoke_env,
                )
                compose_down_passed = bool(commands["compose_down"].get("passed"))
                if not compose_down_passed:
                    warnings.append("docker_compose_down_failed")

    report = {
        "workspace_root": str(workspace_root),
        "compose_project_name": project_name,
        "dockerfile_path": str(dockerfile_path),
        "compose_prod_path": str(compose_prod_path),
        "image_tag": normalized_image_tag,
        "requested_service_url": requested_service_url,
        "service_url": effective_service_url,
        "web_url": effective_web_url,
        "selected_host_ports": selected_host_ports,
        "runtime_smoke_env": redact_runtime_smoke_env(runtime_smoke_env),
        "overall_quality_gate": "pass" if not failures else "fail",
        "verdict": "pass" if not failures else "fail",
        "checks": {
            "dockerfile_present": dockerfile_path.exists(),
            "compose_prod_present": compose_prod_path.exists(),
            "docker_available": docker_available,
            "compose_command_available": compose_available,
            "image_build_passed": image_build_passed,
            "compose_up_passed": compose_up_passed,
            "migration_passed": migration_passed,
            "health_probe_passed": health_probe_passed,
            "readiness_probe_passed": readiness_probe_passed,
            "frontend_requested": include_frontend,
            "web_root_probe_passed": web_root_probe_passed,
            "web_runtime_proof_passed": web_runtime_proof_passed,
            "frontend_browser_evidence_green": frontend_browser_evidence_green,
            "started_service_smoke_requested": run_started_service_smoke,
            "started_service_smoke_present": bool(started_service_smoke_report),
            "started_service_smoke_green": started_service_smoke_green,
            "cleanup_requested": cleanup,
            "compose_down_passed": compose_down_passed,
            "runtime_smoke_green": not failures,
        },
        "commands": commands,
        "probes": probes,
        "frontend_browser_evidence": frontend_browser_evidence,
        "started_service_smoke": {
            "verdict": started_service_smoke_report.get("verdict", "") if started_service_smoke_report else "",
            "output_path": (
                str((output_path.resolve().parent / "started-service-smoke-report.json"))
                if output_path is not None and started_service_smoke_report
                else ""
            ),
            "checks": started_service_smoke_report.get("checks", {}) if started_service_smoke_report else {},
            "failures": started_service_smoke_report.get("failures", []) if started_service_smoke_report else [],
        },
        "failures": failures,
        "warnings": warnings,
    }

    if output_path is not None:
        output_path = output_path.resolve()
        write_json_report(output_path, report)
        write_text(output_path.with_suffix(".md"), build_markdown(report, output_locale))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Docker-based runtime smoke validation for a Phase-3 workspace")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--image-tag", default="")
    parser.add_argument("--service-url", default="http://127.0.0.1:3000")
    parser.add_argument("--startup-timeout-seconds", type=int, default=45)
    parser.add_argument("--command-timeout-seconds", type=int, default=300)
    parser.add_argument("--skip-cleanup", action="store_true")
    parser.add_argument("--skip-started-service-smoke", action="store_true")
    parser.add_argument("--include-frontend", action="store_true")
    parser.add_argument("--frontend-authoring-report", default="")
    parser.add_argument("--frontend-ui-ia-contract", default="")
    parser.add_argument("--frontend-interaction-spec", action="append", default=[])
    parser.add_argument("--install-playwright-browser", action="store_true")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    parser.add_argument(
        "--show-full-report",
        action="store_true",
        help="print the full runtime smoke JSON report to terminal; by default stdout is a compact summary",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_phase3_runtime_smoke(
        workspace_root=Path(args.workspace_root),
        output_path=Path(args.output),
        image_tag=args.image_tag,
        service_url=args.service_url,
        startup_timeout_seconds=max(1, int(args.startup_timeout_seconds)),
        command_timeout_seconds=max(1, int(args.command_timeout_seconds)),
        cleanup=not args.skip_cleanup,
        output_locale=args.output_locale,
        run_started_service_smoke=not args.skip_started_service_smoke,
        include_frontend=bool(args.include_frontend),
        frontend_authoring_report_path=(Path(args.frontend_authoring_report).resolve() if args.frontend_authoring_report else None),
        frontend_ui_ia_contract_path=(Path(args.frontend_ui_ia_contract).resolve() if args.frontend_ui_ia_contract else None),
        frontend_interaction_specs=[Path(item) for item in args.frontend_interaction_spec],
        install_playwright_browser=bool(args.install_playwright_browser),
    )
    terminal_payload = report if args.show_full_report else compact_terminal_summary(report, Path(args.output))
    print(json.dumps(terminal_payload, ensure_ascii=False))
    return support_gate_exit_code("verdict", report)


if __name__ == "__main__":
    raise SystemExit(main())
