from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from phase3.contract_tools import (
    endpoint_rows_from_openapi_spec,
    parse_replay_rows,
    parse_scenario_rows,
    parse_schema_tables,
)
from phase3.surface_policy import write_phase3_profiled_surface


HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
WRITE_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
HARDENING_FAMILIES = {
    "auth_authorization",
    "idempotency_duplicate_submit",
    "transaction_rollback",
    "audit_logging",
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "item"


def _safe_rows(loader: Any, text: str) -> list[dict[str, Any]]:
    try:
        rows = loader(text)
    except ValueError:
        return []
    return [row for row in rows if isinstance(row, dict)]


def _fallback_markdown_rows(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    header = [cell.strip().strip("`") for cell in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) < len(header):
            continue
        rows.append({key: cells[index] for index, key in enumerate(header)})
    return rows


def _schema_rows(text: str) -> list[dict[str, Any]]:
    rows = _safe_rows(parse_schema_tables, text)
    if rows:
        return rows
    return [row for row in _fallback_markdown_rows(text) if row.get("table_name")]


def _scenario_rows(text: str) -> list[dict[str, Any]]:
    rows = _safe_rows(parse_scenario_rows, text)
    if rows:
        return rows
    return [row for row in _fallback_markdown_rows(text) if row.get("scenario")]


def _replay_rows(text: str) -> list[dict[str, Any]]:
    rows = _safe_rows(parse_replay_rows, text)
    if rows:
        return rows
    return [row for row in _fallback_markdown_rows(text) if row.get("replay_id")]


def _behavior_model(operation_id: str, behavior_card_models: dict[str, dict[str, Any]] | None) -> dict[str, Any]:
    model = (behavior_card_models or {}).get(operation_id, {})
    return model if isinstance(model, dict) else {}


def _behavior_evidence_keys(model: dict[str, Any]) -> list[str]:
    semantics = model.get("operation_semantics") if isinstance(model.get("operation_semantics"), dict) else {}
    keys = semantics.get("evidence_keys") if isinstance(semantics.get("evidence_keys"), list) else []
    return [str(key).strip() for key in keys if str(key).strip()]


def _behavior_error_codes(endpoint: dict[str, Any], model: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    semantics = model.get("operation_semantics") if isinstance(model.get("operation_semantics"), dict) else {}
    for item in semantics.get("error_codes", []) if isinstance(semantics.get("error_codes"), list) else []:
        text = str(item).strip()
        if text and text not in codes:
            codes.append(text)
    for failure in endpoint.get("failure_codes", []) if isinstance(endpoint.get("failure_codes"), list) else []:
        if not isinstance(failure, dict):
            continue
        text = str(failure.get("error_code", "")).strip()
        if text and text not in codes:
            codes.append(text)
    return codes


def _response_has_roundtrip_record(endpoint: dict[str, Any]) -> bool:
    response = endpoint.get("response_body_example")
    if not isinstance(response, dict):
        return False
    data = response.get("data", {})
    if isinstance(data, list):
        return bool(data)
    return isinstance(data, dict) and bool(data)


def _is_write_endpoint(endpoint: dict[str, Any]) -> bool:
    return str(endpoint.get("method", "")).strip().upper() in WRITE_HTTP_METHODS


def _is_create_like_operation(operation_id: str) -> bool:
    return operation_id.startswith(("Create", "Launch", "Export"))


def _add_row(
    rows: list[dict[str, Any]],
    *,
    source_kind: str,
    source_ref: str,
    target_kind: str,
    target_ref: str,
    operation_id: str = "",
    table_name: str = "",
    expected_test_family: str,
    required_evidence: list[str],
    required_assertions: list[str],
) -> None:
    index = len(rows) + 1
    rows.append(
        {
            "obligation_id": f"TO-{index:04d}",
            "source_kind": source_kind,
            "source_ref": source_ref,
            "target_kind": target_kind,
            "target_ref": target_ref,
            "operation_id": operation_id,
            "table_name": table_name,
            "expected_test_family": expected_test_family,
            "required_evidence": required_evidence,
            "required_assertions": required_assertions,
            "status": "pending-audit",
            "status_reason": "audit not run",
        }
    )


def build_test_obligation_matrix(
    *,
    esp_text: str,
    stage_03_text: str,
    stage_04_text: str,
    openapi_spec: dict[str, Any],
    behavior_card_models: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    endpoints = endpoint_rows_from_openapi_spec(openapi_spec)
    tables = _schema_rows(esp_text)
    scenarios = _scenario_rows(stage_03_text)
    replays = _replay_rows(stage_04_text)
    rows: list[dict[str, Any]] = []

    for endpoint in endpoints:
        operation_id = str(endpoint.get("endpoint_name", "")).strip()
        if not operation_id:
            continue
        method = str(endpoint.get("method", "")).strip().upper()
        path = str(endpoint.get("path", "")).strip()
        model = _behavior_model(operation_id, behavior_card_models)
        evidence_keys = _behavior_evidence_keys(model)
        error_codes = _behavior_error_codes(endpoint, model)
        source_ref = f"{method} {path}#{operation_id}"

        _add_row(
            rows,
            source_kind="openapi",
            source_ref=source_ref,
            target_kind="test",
            target_ref=f"tests/contracts/{operation_id.lower()}.contract.test.ts",
            operation_id=operation_id,
            expected_test_family="openapi-contract",
            required_evidence=["started-service", "pure-openapi-payload", *evidence_keys],
            required_assertions=["2xx response shape", "response envelope", "no behavior-card helper enrichment"],
        )
        _add_row(
            rows,
            source_kind="hardening",
            source_ref=f"{operation_id}.auth_authorization",
            target_kind="test",
            target_ref=f"tests/contracts/{operation_id.lower()}.contract.test.ts",
            operation_id=operation_id,
            expected_test_family="auth_authorization",
            required_evidence=["started-service", "auth-error-envelope", "audit-record"],
            required_assertions=["missing bearer token", "invalid bearer token", "insufficient role", "allowed path"],
        )
        if _is_write_endpoint(endpoint):
            _add_row(
                rows,
                source_kind="hardening",
                source_ref=f"{operation_id}.audit_logging",
                target_kind="test",
                target_ref=f"tests/contracts/{operation_id.lower()}.contract.test.ts",
                operation_id=operation_id,
                expected_test_family="audit_logging",
                required_evidence=["started-service", "audit-record"],
                required_assertions=["denied audit", "allowed audit", "reason code"],
            )
        if _is_write_endpoint(endpoint) and _response_has_roundtrip_record(endpoint):
            _add_row(
                rows,
                source_kind="hardening",
                source_ref=f"{operation_id}.transaction_rollback",
                target_kind="test",
                target_ref=f"tests/contracts/{operation_id.lower()}.contract.test.ts",
                operation_id=operation_id,
                expected_test_family="transaction_rollback",
                required_evidence=["started-service", "real-sql", "row-count-before-after"],
                required_assertions=["transaction rollback probe", "force rollback after write", "target row counts unchanged"],
            )
        if _is_write_endpoint(endpoint) and _is_create_like_operation(operation_id) and _response_has_roundtrip_record(endpoint):
            _add_row(
                rows,
                source_kind="hardening",
                source_ref=f"{operation_id}.idempotency_duplicate_submit",
                target_kind="test",
                target_ref=f"tests/contracts/{operation_id.lower()}.contract.test.ts",
                operation_id=operation_id,
                expected_test_family="idempotency_duplicate_submit",
                required_evidence=["started-service", "real-sql", "audit-record"],
                required_assertions=["duplicate submit", "no duplicate durable state", "no second allowed audit", "duplicate audit"],
            )
        for error_code in error_codes:
            _add_row(
                rows,
                source_kind="behavior-card",
                source_ref=f"{operation_id}.error.{error_code}",
                target_kind="test",
                target_ref=f"tests/contracts/{operation_id.lower()}.contract.test.ts",
                operation_id=operation_id,
                expected_test_family="openapi-contract",
                required_evidence=["started-service", "error-envelope"],
                required_assertions=[f"{error_code} is returned with expected status"],
            )
        if model:
            _add_row(
                rows,
                source_kind="behavior-card",
                source_ref=f"{operation_id}.service",
                target_kind="test",
                target_ref="tests/unit/api/modules/*.unit.test.ts",
                operation_id=operation_id,
                expected_test_family="unit-service",
                required_evidence=["isolated-service-call", *evidence_keys],
                required_assertions=["validation", "permission or tenant boundary", "state transition", "error mapping"],
            )
            _add_row(
                rows,
                source_kind="behavior-card",
                source_ref=f"{operation_id}.repository",
                target_kind="test",
                target_ref="tests/unit/api/modules/*.unit.test.ts",
                operation_id=operation_id,
                expected_test_family="unit-repository",
                required_evidence=["repository boundary", "test double only for external dependencies"],
                required_assertions=["row mapping", "not-found or duplicate branch", "db error translation"],
            )

    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario", "")).strip()
        operations = [
            item.strip()
            for item in re.split(r"[,/]", str(scenario.get("operations", "")))
            if item.strip()
        ]
        _add_row(
            rows,
            source_kind="p1-p2-scenario",
            source_ref=scenario_id,
            target_kind="test",
            target_ref="tests/scenarios/*.scenario.test.ts",
            operation_id=",".join(operations),
            expected_test_family="scenario",
            required_evidence=["started-service", "business-chain"],
            required_assertions=[
                str(scenario.get("given", "")).strip() or "given precondition",
                str(scenario.get("when", "")).strip() or "when action",
                str(scenario.get("then", "")).strip() or "then outcome",
            ],
        )

    for table in tables:
        table_name = str(table.get("table_name", "")).strip()
        if not table_name:
            continue
        table_ref = f"tests/sql/{table_name}.sql.test.ts"
        for family, assertions in (
            ("sql", ["migration exposes table shape", "insert-read roundtrip"]),
            ("sql", ["not-null", "unique", "foreign-key where declared"]),
            ("sql", ["state update", "transaction rollback", "restore/reentry"]),
        ):
            _add_row(
                rows,
                source_kind="db-schema",
                source_ref=table_name,
                target_kind="test",
                target_ref=table_ref,
                table_name=table_name,
                expected_test_family=family,
                required_evidence=["real-sql"],
                required_assertions=assertions,
            )

    for replay in replays:
        replay_id = str(replay.get("replay_id", "")).strip()
        if not replay_id:
            continue
        _add_row(
            rows,
            source_kind="p2-replay",
            source_ref=replay_id,
            target_kind="test",
            target_ref="tests/replays/*.replay.test.ts",
            operation_id=str(replay.get("scenario_or_contract", "")).strip(),
            expected_test_family="replay",
            required_evidence=["replayable started-service behavior"],
            required_assertions=[str(replay.get("expected_outcome", "")).strip() or "expected outcome preserved"],
        )

    summary = {
        "operation_count": len(endpoints),
        "table_count": len(tables),
        "scenario_count": len(scenarios),
        "replay_count": len(replays),
        "obligation_count": len(rows),
        "families": sorted({str(row["expected_test_family"]) for row in rows}),
        "hardening_family_count": len({str(row["expected_test_family"]) for row in rows if str(row["expected_test_family"]) in HARDENING_FAMILIES}),
    }
    return {
        "artifact_kind": "phase3-test-obligation-matrix",
        "summary": summary,
        "rows": rows,
    }


def render_test_obligation_matrix_markdown(matrix: dict[str, Any]) -> str:
    summary = matrix.get("summary", {}) if isinstance(matrix.get("summary"), dict) else {}
    lines = [
        "# P3 Test Obligation Matrix",
        "",
        "## Summary",
        f"- operation_count: {summary.get('operation_count', 0)}",
        f"- table_count: {summary.get('table_count', 0)}",
        f"- scenario_count: {summary.get('scenario_count', 0)}",
        f"- replay_count: {summary.get('replay_count', 0)}",
        f"- obligation_count: {summary.get('obligation_count', 0)}",
        "",
        "## Obligations",
        "| obligation_id | family | operation | table | source | target | status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in matrix.get("rows", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            "| {obligation_id} | {family} | {operation} | {table} | {source} | {target} | {status} |".format(
                obligation_id=str(row.get("obligation_id", "")),
                family=str(row.get("expected_test_family", "")),
                operation=str(row.get("operation_id", "")),
                table=str(row.get("table_name", "")),
                source=str(row.get("source_ref", "")).replace("|", "\\|"),
                target=str(row.get("target_ref", "")).replace("|", "\\|"),
                status=str(row.get("status", "")),
            )
        )
    return "\n".join(lines) + "\n"


def _read_family_files(workspace_root: Path, family: str) -> list[tuple[Path, str]]:
    root = workspace_root / "tests" / family
    if not root.exists():
        return []
    return [(path, path.read_text(encoding="utf-8", errors="ignore")) for path in sorted(root.glob("*.ts"))]


def _contains_operation(text: str, operation_id: str) -> bool:
    return not operation_id or operation_id in text or operation_id.lower() in text.lower()


def _pure_openapi_contract_present(text: str, operation_id: str) -> bool:
    if not _contains_operation(text, operation_id):
        return False
    return (
        "documented OpenAPI request is directly executable" in text
        and "invokeHttpOperation(runtime, operationId, buildOperationPayload(operationId))" in text
    )


def _contract_error_present(text: str, operation_id: str, assertions: list[str]) -> bool:
    if not _contains_operation(text, operation_id):
        return False
    for assertion in assertions:
        parts = assertion.split()
        if not parts:
            continue
        error_code = parts[0]
        direct_payload = f'const payload = buildFailurePayload(operationId, "{error_code}");'
        direct_assertion = f'expect(error.envelope.error_code).toBe("{error_code}");'
        if direct_payload in text and direct_assertion in text:
            return True
    return False


def _contract_error_condition_signal_present(text: str, error_code: str) -> bool:
    lowered = text.lower()
    normalized = error_code.lower()
    if normalized in {"invalid_request", "validation_failed"} or "invalid" in normalized or "validation" in normalized:
        return True
    signals_by_code = {
        "forbidden": [
            "expectedownerservice",
            "tenant_forbidden",
            "deny_tenant",
            "wrong tenant",
            "wrongtenant",
            "roles: []",
            "unauthorized role",
            "auth_context",
        ],
        "version_conflict": [
            "expectedversion",
            "expected_version",
            "stale",
            "concurrent",
            "duplicate",
            "currentversion",
            "current_version",
        ],
        "not_found": [
            "missing_",
            "notfound",
            "not_found_id",
            "path_params",
            "unknown",
        ],
        "dependency_unavailable": [
            "simulate dependency",
            "simulatedependencyfailure",
            "simulate dependency failure",
            "dependency failure",
            "rejects",
            "mockrejectedvalue",
            "repository",
        ],
    }
    signals = signals_by_code.get(normalized, [])
    if not signals:
        return True
    return any(signal in lowered for signal in signals)


def _contract_error_condition_weak(text: str, operation_id: str, assertions: list[str]) -> bool:
    return bool(_contract_error_condition_gap_reason(text, operation_id, assertions))


def _error_condition_review_bound_reason(error_code: str) -> str:
    normalized = error_code.lower()
    if any(token in normalized for token in ("stale", "version")):
        return "stale_version_condition_not_derivable"
    if any(token in normalized for token in ("duplicate", "conflict")):
        return "duplicate_condition_not_derivable"
    if "idempot" in normalized or "replay" in normalized:
        return "idempotency_condition_not_derivable"
    return "contract_error_condition_weak"


def _contract_error_condition_gap_reason(text: str, operation_id: str, assertions: list[str]) -> str:
    if not _contains_operation(text, operation_id):
        return ""
    for assertion in assertions:
        parts = assertion.split()
        if not parts:
            continue
        error_code = parts[0]
        direct_payload = f'const payload = buildFailurePayload(operationId, "{error_code}");'
        direct_assertion = f'expect(error.envelope.error_code).toBe("{error_code}");'
        if direct_payload in text and direct_assertion in text:
            if not _contract_error_condition_signal_present(text, error_code):
                return _error_condition_review_bound_reason(error_code)
    return ""


def _contract_error_helper_only_signal_present(text: str, operation_id: str, assertions: list[str]) -> bool:
    if not _contains_operation(text, operation_id):
        return False
    error_codes = [assertion.split()[0] for assertion in assertions if assertion.split()]
    return any(
        error_code in text and f'buildBehaviorCardPayload(operationId, buildFailurePayload(operationId, "{error_code}")' in text
        for error_code in error_codes
    )


def _unit_status(files: list[tuple[Path, str]], operation_id: str, repository: bool) -> tuple[str, str]:
    keywords = ["repository", "duplicate", "not_found", "not-found", "db error"] if repository else [
        "service",
        "validates",
        "validation",
        "state",
        "permission",
        "tenant",
        "error",
    ]
    for _path, text in files:
        if _contains_operation(text, operation_id) and any(keyword in text.lower() for keyword in keywords):
            lowered = text.lower()
            evidence_family = _unit_evidence_family(text)
            if evidence_family == "generated-runtime-module":
                return "review-bound", "module_test_does_not_satisfy_unit_evidence"
            if evidence_family != "isolated-unit":
                if repository:
                    return "missing", "unit_repository_call_proof_missing"
                return "missing", "unit_service_isolation_missing"
            return "covered", "unit isolation and call-proof signal present"
    return "missing", "unit_tests_missing"


def _unit_evidence_family(text: str) -> str:
    lowered = text.lower()
    if any(
        token in lowered
        for token in ("vi.fn", "spyon", "tohavebeencalled", "fakerepository", "mockrepository", "mockedrepository")
    ):
        return "isolated-unit"
    if any(
        token in lowered
        for token in ("resetgeneratedruntime", "invokehttpoperation", "buildoperationpayload", "generated-runtime")
    ):
        return "generated-runtime-module"
    return "unknown"


def _scenario_failure_variant_weak(text: str) -> bool:
    if "buildFailurePayload" not in text:
        return False
    lowered = text.lower()
    invariance_tokens = (
        "collectscenariostate",
        "beforerows",
        "afterrows",
        "stateinvariance",
        "state invariance",
        "toeql(beforerows",
        "toequal(beforerows",
        "unchanged",
    )
    return not any(token in lowered for token in invariance_tokens)


def _scenario_status(files: list[tuple[Path, str]], row: dict[str, Any]) -> tuple[str, str]:
    operation_ids = [item.strip() for item in str(row.get("operation_id", "")).split(",") if item.strip()]
    required_assertions = [str(item).strip() for item in row.get("required_assertions", []) if str(item).strip()]
    for _path, text in files:
        operation_match = not operation_ids or any(_contains_operation(text, operation_id) for operation_id in operation_ids)
        assertion_match = any(assertion.split()[0] in text for assertion in required_assertions if assertion.split())
        if operation_match and assertion_match:
            if _scenario_failure_variant_weak(text):
                return "missing", "scenario_failure_variant_state_invariance_unproven"
            return "covered", "scenario assertion signal present"
    return "missing", "scenario_chain_missing"


def _foreign_key_probe_empty(text: str) -> bool:
    return bool(re.search(r"['\"]foreign_key['\"]\s*:\s*\[\s*\]", text))


def _foreign_key_probe_present(text: str) -> bool:
    match = re.search(r"['\"]foreign_key['\"]\s*:\s*\[(?P<body>.*?)\]", text, flags=re.DOTALL)
    if not match:
        return False
    return bool(match.group("body").strip())


def _sql_status(files: list[tuple[Path, str]], table_name: str, assertions: list[str]) -> tuple[str, str]:
    table_slug = _slug(table_name)
    for path, text in files:
        if table_slug not in _slug(path.stem) and table_name not in text:
            continue
        lowered = text.lower()
        if any("foreign-key" in item or "foreign key" in item for item in assertions):
            if _foreign_key_probe_empty(text):
                return "review-bound", "sql_foreign_key_probe_review_bound"
            if not _foreign_key_probe_present(text) and "23503" not in text:
                return "review-bound", "sql_foreign_key_probe_review_bound"
        if any("transaction" in item or "rollback" in item or "reentry" in item for item in assertions):
            if any(token in lowered for token in ("transaction", "rollback", "restore", "reentry")):
                if "state update" in " ".join(assertions).lower() and "update " not in lowered:
                    return "weak", "sql_state_update_probe_weak"
                return "covered", "sql transaction/reentry evidence present"
            return "weak", "sql_transaction_or_reentry_weak"
        if all(any(token.lower() in lowered for token in item.lower().split()) for item in assertions):
            return "covered", "sql assertion signal present"
        return "covered", "sql table test present"
    return "missing", "sql_test_missing"


def _replay_status(files: list[tuple[Path, str]], source_ref: str, operation_id: str) -> tuple[str, str]:
    for _path, text in files:
        if source_ref in text or _contains_operation(text, operation_id):
            lowered = text.lower()
            if not any(token in lowered for token in ("idempot", "second", "duplicate", "rerun")):
                return "missing", "replay_idempotency_stress_unproven"
            return "covered", "replay semantic and idempotency signal present"
    return "missing", "replay_test_missing"


def _matching_contract_texts(files: list[tuple[Path, str]], operation_id: str) -> list[str]:
    return [text for _path, text in files if _contains_operation(text, operation_id)]


def _all_tokens_present(text: str, tokens: list[str]) -> bool:
    lowered = text.lower()
    return all(token.lower() in lowered for token in tokens)


def _hardening_status(
    family: str,
    files: list[tuple[Path, str]],
    operation_id: str,
) -> tuple[str, str]:
    texts = _matching_contract_texts(files, operation_id)
    if not texts:
        return "missing", f"hardening_{family}_missing"

    for text in texts:
        lowered = text.lower()
        if family == "auth_authorization":
            if _all_tokens_present(
                text,
                [
                    "rejects missing bearer token",
                    "missing_bearer_token",
                    "rejects invalid bearer token",
                    "invalid_bearer_token",
                    "rejects valid bearer token with insufficient role",
                    "rbac_forbidden",
                    "accepts valid bearer token",
                ],
            ) or _all_tokens_present(
                text,
                [
                    "rejects missing bearer token",
                    "missing_bearer_token",
                    "rejects invalid bearer token",
                    "invalid_auth_token",
                    "rejects valid bearer token with insufficient role",
                    "rbac_forbidden",
                    "accepts valid bearer token",
                ],
            ):
                return "covered", "hardening auth/authorization evidence present"
        elif family == "idempotency_duplicate_submit":
            if _all_tokens_present(
                text,
                [
                    "duplicate submit does not create duplicate durable state",
                    "collectpersistenceroundtripevidence",
                    "afterallowedauditcount",
                    "beforeallowedauditcount",
                    "duplicateauditrecords",
                ],
            ):
                return "covered", "hardening duplicate-submit evidence present"
        elif family == "transaction_rollback":
            if _all_tokens_present(
                text,
                [
                    "transaction rollback probe leaves durable state unchanged",
                    "collectpersistencetargetrowcounts",
                    "force_transaction_rollback_probe",
                    "aftertargetrowcounts",
                    "beforetargetrowcounts",
                ],
            ):
                return "covered", "hardening transaction rollback evidence present"
        elif family == "audit_logging":
            has_audit_surface = "runtime.getauditrecords" in lowered
            has_denied = 'outcome === "denied"' in text or "outcome: \"denied\"" in text
            has_allowed = 'outcome === "allowed"' in text or "outcome: \"allowed\"" in text
            has_reason = "reason" in lowered or "error_code" in lowered
            if has_audit_surface and has_denied and has_allowed and has_reason:
                return "covered", "hardening audit/logging evidence present"

    return "missing", f"hardening_{family}_missing"


def _hardening_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    families: dict[str, dict[str, Any]] = {}
    for family in sorted(HARDENING_FAMILIES):
        family_rows = [row for row in rows if row.get("expected_test_family") == family]
        covered = sum(1 for row in family_rows if row.get("status") == "covered")
        missing = sum(1 for row in family_rows if row.get("status") == "missing")
        weak = sum(1 for row in family_rows if row.get("status") == "weak")
        review_bound = sum(1 for row in family_rows if row.get("status") == "review-bound")
        if not family_rows:
            status = "not-required"
        elif missing or weak:
            status = "missing"
        elif review_bound:
            status = "review-bound"
        else:
            status = "covered"
        families[family] = {
            "status": status,
            "obligation_count": len(family_rows),
            "covered_count": covered,
            "missing_count": missing,
            "weak_count": weak,
            "review_bound_count": review_bound,
        }
    blocking = [
        family
        for family, payload in families.items()
        if payload["obligation_count"] > 0 and payload["status"] in {"missing", "review-bound"}
    ]
    return {
        "overall_gate": "pass" if not blocking else "fail",
        "formal_state_ceiling": "not-capped-by-hardening-gate" if not blocking else "implementation-in-progress",
        "blocking_families": blocking,
        "families": families,
    }


def audit_test_obligation_matrix(matrix: dict[str, Any], *, workspace_root: Path) -> dict[str, Any]:
    workspace_root = workspace_root.resolve()
    family_files = {
        "contracts": _read_family_files(workspace_root, "contracts"),
        "scenarios": _read_family_files(workspace_root, "scenarios"),
        "sql": _read_family_files(workspace_root, "sql"),
        "unit": _read_family_files(workspace_root, "unit/api/modules") if (workspace_root / "tests" / "unit" / "api" / "modules").exists() else [],
        "replays": _read_family_files(workspace_root, "replays"),
    }
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []

    for raw_row in matrix.get("rows", []):
        if not isinstance(raw_row, dict):
            continue
        row = dict(raw_row)
        family = str(row.get("expected_test_family", "")).strip()
        operation_id = str(row.get("operation_id", "")).strip()
        table_name = str(row.get("table_name", "")).strip()
        assertions = [str(item) for item in row.get("required_assertions", []) if str(item).strip()]
        status = "missing"
        reason = "no matching test evidence"

        if family == "openapi-contract":
            if "no behavior-card helper enrichment" in assertions:
                if any(_pure_openapi_contract_present(text, operation_id) for _path, text in family_files["contracts"]):
                    status, reason = "covered", "pure OpenAPI consumer contract present"
                else:
                    reason = "openapi_consumer_contract_missing"
                    failures.append(reason)
            elif any(_contract_error_present(text, operation_id, assertions) for _path, text in family_files["contracts"]):
                gap_reasons = [
                    _contract_error_condition_gap_reason(text, operation_id, assertions)
                    for _path, text in family_files["contracts"]
                ]
                reason = next((item for item in gap_reasons if item), "")
                if reason:
                    if reason.endswith("_condition_not_derivable"):
                        status = "review-bound"
                        warnings.append(reason)
                    else:
                        failures.append(reason)
                else:
                    status, reason = "covered", "contract error assertion present"
            elif any(_contract_error_helper_only_signal_present(text, operation_id, assertions) for _path, text in family_files["contracts"]):
                reason = "contract_error_openapi_payload_missing"
                failures.append(reason)
            else:
                reason = "contract_error_assertion_missing"
                failures.append(reason)
        elif family == "unit-service":
            status, reason = _unit_status(family_files["unit"], operation_id, repository=False)
            if status == "missing":
                failures.append(reason)
            elif status == "review-bound":
                warnings.append(reason)
        elif family == "unit-repository":
            status, reason = _unit_status(family_files["unit"], operation_id, repository=True)
            if status == "missing":
                failures.append(reason)
            elif status == "review-bound":
                warnings.append(reason)
        elif family == "scenario":
            status, reason = _scenario_status(family_files["scenarios"], row)
            if status == "missing":
                failures.append(reason)
        elif family == "sql":
            status, reason = _sql_status(family_files["sql"], table_name, assertions)
            if status == "missing":
                failures.append(reason)
            elif status in {"weak", "review-bound"}:
                warnings.append(reason)
        elif family == "replay":
            status, reason = _replay_status(family_files["replays"], str(row.get("source_ref", "")), operation_id)
            if status == "missing":
                failures.append(reason)
        elif family in HARDENING_FAMILIES:
            status, reason = _hardening_status(family, family_files["contracts"], operation_id)
            if status == "missing":
                failures.append(reason)
            elif status in {"weak", "review-bound"}:
                warnings.append(reason)

        row["status"] = status
        row["status_reason"] = reason
        rows.append(row)

    unique_failures = sorted(set(failures))
    unique_warnings = sorted(set(warnings))
    hardening = _hardening_summary(rows)
    summary = {
        "obligation_count": len(rows),
        "covered_count": sum(1 for row in rows if row.get("status") == "covered"),
        "missing_count": sum(1 for row in rows if row.get("status") == "missing"),
        "weak_count": sum(1 for row in rows if row.get("status") == "weak"),
        "review_bound_count": sum(1 for row in rows if row.get("status") == "review-bound"),
        "failure_count": len(unique_failures),
        "warning_count": len(unique_warnings),
        "isolated_unit_evidence_count": sum(
            1 for _path, text in family_files["unit"] if _unit_evidence_family(text) == "isolated-unit"
        ),
        "module_evidence_count": sum(
            1 for _path, text in family_files["unit"] if _unit_evidence_family(text) == "generated-runtime-module"
        ),
        "hardening_overall_gate": hardening["overall_gate"],
    }
    return {
        "artifact_kind": "phase3-test-obligation-audit",
        "overall_quality_gate": "pass" if not unique_failures else "fail",
        "hardening": hardening,
        "summary": summary,
        "failures": unique_failures,
        "warnings": unique_warnings,
        "rows": rows,
    }


def write_test_obligation_artifacts(
    *,
    output_dir: Path,
    esp_text: str,
    stage_03_text: str,
    stage_04_text: str,
    openapi_spec: dict[str, Any],
    behavior_card_models: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    matrix = build_test_obligation_matrix(
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        openapi_spec=openapi_spec,
        behavior_card_models=behavior_card_models,
    )
    audit = audit_test_obligation_matrix(matrix, workspace_root=output_dir)
    matrix_path = output_dir / "test-obligation-matrix.json"
    audit_path = output_dir / "test-obligation-audit.json"
    matrix_markdown_path = write_phase3_profiled_surface(
        output_dir,
        "test-obligation-matrix.md",
        render_test_obligation_matrix_markdown(matrix),
    )
    audit_markdown_path = write_phase3_profiled_surface(
        output_dir,
        "test-obligation-audit.md",
        render_test_obligation_matrix_markdown(audit),
    )
    matrix_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "matrix_path": str(matrix_path),
        "matrix_markdown_path": str(matrix_markdown_path),
        "audit_path": str(audit_path),
        "audit_markdown_path": str(audit_markdown_path),
        "matrix": matrix,
        "audit": audit,
    }
