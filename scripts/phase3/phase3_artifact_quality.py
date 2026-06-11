#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import re
from pathlib import Path
from typing import Any

from phase3.phase3_behavior_card_validator import validate_behavior_card
from phase3.review_support import emit_gate_cli_result


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def list_test_files(root: Path, subdir: str, suffix: str) -> list[Path]:
    base = root / "tests" / subdir
    if not base.exists():
        return []
    return sorted(base.glob(f"*{suffix}"))


def list_nested_test_files(root: Path, subdir: str, suffix: str) -> list[Path]:
    base = root / "tests" / subdir
    if not base.exists():
        return []
    return sorted(base.rglob(f"*{suffix}"))


ENUM_LIKE_OPENAPI_FIELDS = {"status", "state", "severity", "priority", "decisionposture", "uncertaintylevel", "risklevel"}


def normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def iter_openapi_operations(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    operations: list[tuple[str, str, dict[str, Any]]] = []
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return operations
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if str(method).lower() in {"get", "post", "put", "patch", "delete"} and isinstance(operation, dict):
                operations.append((str(path), str(method).lower(), operation))
    return operations


def operation_response_schema(operation: dict[str, Any], status_prefix: str) -> dict[str, Any]:
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return {}
    status = next((key for key in sorted(responses) if str(key).startswith(status_prefix)), "")
    response = responses.get(status, {})
    if not isinstance(response, dict):
        return {}
    content = response.get("content", {})
    app_json = content.get("application/json", {}) if isinstance(content, dict) else {}
    schema = app_json.get("schema", {}) if isinstance(app_json, dict) else {}
    return schema if isinstance(schema, dict) else {}


def success_data_schema(schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties", {})
    data_schema = properties.get("data", {}) if isinstance(properties, dict) else {}
    if isinstance(data_schema, dict) and data_schema.get("type") == "array":
        items = data_schema.get("items", {})
        return items if isinstance(items, dict) else {}
    return data_schema if isinstance(data_schema, dict) else {}


def enum_like_fields_without_enum(schema: dict[str, Any]) -> list[str]:
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return []
    missing: list[str] = []
    for field, field_schema in properties.items():
        if normalize_token(str(field)) not in ENUM_LIKE_OPENAPI_FIELDS:
            continue
        if isinstance(field_schema, dict) and "enum" not in field_schema:
            missing.append(str(field))
    return missing


def is_standard_error_envelope(schema: dict[str, Any]) -> bool:
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(properties, dict) or not isinstance(required, list):
        return False
    required_set = set(str(item) for item in required)
    if not {"error_kind", "error_code", "retryability"}.issubset(required_set):
        return False
    if schema.get("additionalProperties") is not False:
        return False
    error_code = properties.get("error_code", {})
    return isinstance(error_code, dict) and "enum" in error_code


def analyze_openapi_contract_quality(spec: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    inferred_schema_count = 0
    schema_count = 0
    missing_enum_constraint_count = 0
    weak_error_envelope_count = 0
    missing_pagination_meta_count = 0
    for path, method, operation in iter_openapi_operations(spec):
        reasons: list[str] = []
        request_body = operation.get("requestBody", {})
        if isinstance(request_body, dict):
            content = request_body.get("content", {})
            app_json = content.get("application/json", {}) if isinstance(content, dict) else {}
            request_schema = app_json.get("schema", {}) if isinstance(app_json, dict) else {}
            if isinstance(request_schema, dict):
                schema_count += 1
                if request_schema.get("x-schema-source") == "inferred-from-example":
                    inferred_schema_count += 1
        success_schema = operation_response_schema(operation, "2")
        if success_schema:
            schema_count += 1
            data_schema = success_data_schema(success_schema)
            missing_enum_fields = enum_like_fields_without_enum(data_schema)
            if missing_enum_fields:
                missing_enum_constraint_count += len(missing_enum_fields)
                reasons.append("missing_enum_constraints")
            pagination_rule = str(operation.get("x-pagination-rule", "")).strip().lower()
            properties = success_schema.get("properties", {}) if isinstance(success_schema, dict) else {}
            if pagination_rule not in {"", "none", "not_applicable", "n/a"} and isinstance(properties, dict) and "pagination" not in properties:
                missing_pagination_meta_count += 1
                reasons.append("missing_pagination_meta")
        responses = operation.get("responses", {})
        if isinstance(responses, dict):
            for status, response in responses.items():
                if not str(status).startswith(("4", "5")) or not isinstance(response, dict):
                    continue
                content = response.get("content", {})
                app_json = content.get("application/json", {}) if isinstance(content, dict) else {}
                schema = app_json.get("schema", {}) if isinstance(app_json, dict) else {}
                if not isinstance(schema, dict) or not is_standard_error_envelope(schema):
                    weak_error_envelope_count += 1
                    reasons.append("weak_error_envelope")
        if reasons:
            findings.append({"path": path, "method": method, "operation_id": operation.get("operationId", ""), "reasons": sorted(set(reasons))})
    inferred_schema_ratio = inferred_schema_count / schema_count if schema_count else 0.0
    return {
        "overall_quality_gate": "fail" if findings else "pass",
        "summary": {
            "operation_count": len(iter_openapi_operations(spec)),
            "schema_count": schema_count,
            "inferred_schema_count": inferred_schema_count,
            "inferred_schema_ratio": inferred_schema_ratio,
            "missing_enum_constraint_count": missing_enum_constraint_count,
            "weak_error_envelope_count": weak_error_envelope_count,
            "missing_pagination_meta_count": missing_pagination_meta_count,
        },
        "findings": findings,
    }




BLOCKER_REASON_SET = {
    "fake_green_tautology",
    "runtime_toolkit_self_check",
    "invocation_only",
    "shape_only_core_test",
    "failure_path_mismatch",
    "missing_initialize_database",
    "missing_restore_scenario",
    "unit_semantic_assertion_missing",
}

WARNING_REASON_SET = {
    "generic_truthiness",
    "low_diagnostic_precision",
    "empty_expected_context",
    "field_presence_only",
    "generic_header_assertions",
}

ALLOWED_REASON_SET = {
    "helper_guard_truthiness",
    "trace_linkage_guard",
    "replay_continuity_anchor",
}


def has_fake_green_tautology(text: str) -> bool:
    return "expect(true).toBe(true)" in text or "expect(true).toEqual(true)" in text


def has_runtime_toolkit_self_check(text: str) -> bool:
    return "Object.keys(runtimeKit)" in text or "toContain(\"invokeHttpOperation\")" in text or "toContain('invokeHttpOperation')" in text


def has_invocation_without_result_assertion(text: str) -> bool:
    has_invocation = "invokeHttpOperation(" in text or ".fetch(" in text or "runtime.query(" in text
    if not has_invocation:
        return False
    semantic_markers = (
        "extractEnvelopeData",
        "captureApiError",
        "error.envelope.error_code",
        "collectPersistenceRoundTripEvidence",
        "expect(data.",
        "expect(finalData.",
        "expect(finalRecord.",
        "expect(selected)",
        "expect(rows)",
    )
    return not any(marker in text for marker in semantic_markers)


def has_generic_truthiness(text: str) -> bool:
    return ".toBeTruthy()" in text or ".not.toBeTruthy()" in text


def classify_truthiness_usage(text: str) -> str | None:
    if not has_generic_truthiness(text):
        return None
    if (
        "function assert" in text
        or "function expect" in text
        or "actual).toBeTruthy()" in text
        or re.search(r"expect\([A-Za-z_][A-Za-z0-9_]*\)\.toBeTruthy\(\)", text)
    ):
        return "helper_guard_truthiness"
    return "generic_truthiness"


def has_failure_path_mismatch(text: str) -> bool:
    return "captureApiError(" in text and "error.envelope.error_code" not in text


def has_low_diagnostic_sql_reject(text: str) -> bool:
    return "runtime.query" in text and ".rejects.toBeTruthy()" in text


def classify_finding_severity(reasons: list[str]) -> str:
    if any(reason in BLOCKER_REASON_SET for reason in reasons):
        return "blocker"
    if any(reason in WARNING_REASON_SET for reason in reasons):
        return "warning"
    if reasons and all(reason in ALLOWED_REASON_SET for reason in reasons):
        return "allowed"
    return "none"

def has_empty_expected_context(text: str) -> bool:
    return bool(re.search(r"const\s+expectedContextFields\s*=\s*\[\s*\]", text))


def has_field_presence_loop(text: str) -> bool:
    return "toHaveProperty(field)" in text and "finalDataFields" in text


def has_only_generic_header_assertions(text: str) -> bool:
    generic_tokens = (
        "upstreamTraceIds.length",
        "acceptanceCriteria.length",
        "operationIds.length",
        "results).toHaveLength(operationIds.length)",
        "Array.isArray(finalData)",
    )
    return sum(1 for token in generic_tokens if token in text) >= 3


def has_business_value_assertion(text: str) -> bool:
    if re.search(r"expect\([^\n]+\)\.toBe\([^\n]+\)", text) and "Array.isArray" not in text:
        return True
    if re.search(r"expect\([^\n]+\)\.toEqual\([^\n]+\)", text):
        return True
    if re.search(r"expect\([^\n]+\)\.toMatchObject\([^\n]+\)", text):
        return True
    return False


def has_context_propagation_assertion(text: str) -> bool:
    return bool(re.search(r"expect\([^\n]+Data\.[A-Za-z0-9_]+\)\.toBe\([^\n]+Data\.[A-Za-z0-9_]+\)", text))


def has_error_path_assertion(text: str) -> bool:
    return ("captureApiError" in text or "captureRuntimeError" in text) and "error.envelope.error_code" in text


def has_unit_semantic_assertion(text: str) -> bool:
    if bool(re.search(r"expect\(error\.(?:envelope\.)?error_code\)\.toBe\(", text)) or bool(re.search(r"expect\(error\.status\)\.toBe\(", text)):
        return True
    return bool(
        re.search(
            r"expect\((?!result\.|Object\.|Array\.)[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\)\.to(?:Be|Equal)\(",
            text,
        )
    )


def has_persistence_roundtrip_assertion(text: str) -> bool:
    return (
        "collectPersistenceRoundTripEvidence" in text
        and "mismatchedFieldNames.length === 0" in text
        and ("fullyMatchedEvidence.length" in text or "persistenceEvidenceCount" in text)
    )


def touches_backend_runtime(text: str) -> bool:
    return any(
        token in text
        for token in (
            "startBackendRuntime",
            "invokeHttpOperation",
            "runtime.query",
            "collectPersistenceRoundTripEvidence",
        )
    )


def has_initialize_database(text: str) -> bool:
    return "initializeDatabase(" in text


def has_restore_scenario(text: str) -> bool:
    return "restoreScenario(" in text or "resetDatabase(" in text


def classify_test_file(path: Path, kind: str) -> dict[str, Any]:
    text = read_text(path)
    reasons: list[str] = []
    strengths: list[str] = []
    if has_fake_green_tautology(text):
        reasons.append("fake_green_tautology")
    if has_runtime_toolkit_self_check(text):
        reasons.append("runtime_toolkit_self_check")
    if has_invocation_without_result_assertion(text):
        reasons.append("invocation_only")
    truthiness_classification = classify_truthiness_usage(text)
    if truthiness_classification:
        reasons.append(truthiness_classification)
    if has_failure_path_mismatch(text):
        reasons.append("failure_path_mismatch")
    if has_low_diagnostic_sql_reject(text):
        reasons.append("low_diagnostic_precision")
    if has_empty_expected_context(text):
        reasons.append("empty_expected_context")
    if has_field_presence_loop(text):
        reasons.append("field_presence_only")
    if has_only_generic_header_assertions(text):
        reasons.append("generic_header_assertions")
    if kind == "unit" and not has_unit_semantic_assertion(text):
        reasons.append("unit_semantic_assertion_missing")
    runtime_backed = touches_backend_runtime(text)
    if runtime_backed and not has_initialize_database(text):
        reasons.append("missing_initialize_database")
    if runtime_backed and not has_restore_scenario(text):
        reasons.append("missing_restore_scenario")
    if has_business_value_assertion(text):
        strengths.append("business_value_assertion")
    if has_context_propagation_assertion(text):
        strengths.append("context_propagation_assertion")
    if has_error_path_assertion(text):
        strengths.append("error_path_assertion")
    if has_persistence_roundtrip_assertion(text):
        strengths.append("persistence_roundtrip_assertion")
    if "upstreamTraceIds.length" in text or "linkedRbiOrWp.length" in text:
        strengths.append("trace_linkage_guard")
    if kind == "replay" and "expectedOutcome.length" in text:
        strengths.append("replay_continuity_anchor")
    if len(strengths) >= 2 and "field_presence_only" in reasons:
        reasons = [reason for reason in reasons if reason != "field_presence_only"] + ["helper_guard_truthiness"]
    if len(strengths) >= 2 and "generic_header_assertions" in reasons:
        reasons = [reason for reason in reasons if reason != "generic_header_assertions"]
    if len(strengths) < 2 and ("field_presence_only" in reasons or "generic_header_assertions" in reasons):
        if kind in {"scenario", "replay", "contract"}:
            reasons.append("shape_only_core_test")
    severity = classify_finding_severity(reasons)
    weak = severity in {"blocker", "warning"}
    return {
        "path": str(path),
        "kind": kind,
        "weak": weak,
        "severity": severity,
        "reasons": reasons,
        "strengths": strengths,
    }


def analyze_test_assertion_quality(root: Path) -> dict[str, Any]:
    root = root.resolve()
    rows: list[dict[str, Any]] = []
    for path in list_test_files(root, "contracts", ".contract.test.ts"):
        rows.append(classify_test_file(path, "contract"))
    for path in list_test_files(root, "scenarios", ".scenario.test.ts"):
        rows.append(classify_test_file(path, "scenario"))
    for path in list_test_files(root, "replays", ".replay.test.ts"):
        rows.append(classify_test_file(path, "replay"))
    for path in list_nested_test_files(root, "unit/api", ".unit.test.ts"):
        rows.append(classify_test_file(path, "unit"))
    findings = [row for row in rows if row["weak"]]
    weak_contract_count = sum(1 for row in findings if row["kind"] == "contract")
    weak_scenario_count = sum(1 for row in findings if row["kind"] == "scenario")
    weak_replay_count = sum(1 for row in findings if row["kind"] == "replay")
    weak_unit_count = sum(1 for row in findings if row["kind"] == "unit")
    blocker_count = sum(1 for row in findings if row["severity"] == "blocker")
    warning_count = sum(1 for row in findings if row["severity"] == "warning")
    allowed_count = sum(1 for row in rows if row["severity"] == "allowed")
    review_bound = blocker_count == 0 and warning_count > 0
    report = {
        "workspace_root": str(root),
        "overall_quality_gate": "fail" if blocker_count else "pass",
        "review_bound": review_bound,
        "summary": {
            "contract_count": sum(1 for row in rows if row["kind"] == "contract"),
            "scenario_count": sum(1 for row in rows if row["kind"] == "scenario"),
            "replay_count": sum(1 for row in rows if row["kind"] == "replay"),
            "unit_count": sum(1 for row in rows if row["kind"] == "unit"),
            "weak_contract_count": weak_contract_count,
            "weak_scenario_count": weak_scenario_count,
            "weak_replay_count": weak_replay_count,
            "weak_unit_count": weak_unit_count,
            "blocker_count": blocker_count,
            "warning_count": warning_count,
            "allowed_count": allowed_count,
        },
        "findings": findings,
        "allowed_findings": [row for row in rows if row["severity"] == "allowed"],
    }
    return report


def analyze_behavior_card_quality(markdown: str, *, high_risk: bool = True) -> dict[str, Any]:
    validation = validate_behavior_card(markdown, high_risk=high_risk)
    blockers = list(validation.get("blockers", []))
    warnings = list(validation.get("warnings", []))
    normalized = markdown.lower()
    if high_risk and "todo" in normalized:
        blockers.append("field_filled_only")
    state_section_present = "## 5. State And Persistence Effects" in markdown
    if high_risk and (
        not state_section_present
        or "tables / collections / queues affected" not in markdown
        or re.search(r"tables / collections / queues affected:\s*(?:pending|todo|none)\b", normalized)
    ):
        blockers.append("missing_state_persistence_effects")
    if high_risk and ("## 6. Test Mapping" not in markdown or "## 7. Implementation Mapping" not in markdown):
        blockers.append("missing_test_or_implementation_mapping")
    if high_risk and re.search(r"\|\s*(?:todo|pending)\s*\|", normalized):
        warnings.append("generic_placeholder_mapping")
    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    return {
        "overall_quality_gate": "fail" if blockers else "pass",
        "blockers": blockers,
        "warnings": warnings,
        "trace_ids": validation.get("trace_ids", []),
        "steps": [f"step-{item}" for item in re.findall(r"^\s*(\d+)\.\s+", markdown, re.MULTILINE)],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Phase-3 generated test assertion quality")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = analyze_test_assertion_quality(Path(args.workspace_root))
    return emit_gate_cli_result(report, output_path=Path(args.output) if args.output else None)


if __name__ == "__main__":
    raise SystemExit(main())
