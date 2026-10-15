#!/usr/bin/env python3
"""Shared mechanical helpers for Phase-3 scenario/replay test scaffolders."""

from __future__ import annotations

import json
import re

from phase3.test_scaffolder_common import normalize_field_token, response_data_for_operation


def response_is_array(endpoint_rows: list[dict[str, object]], operation_id: str) -> bool:
    return isinstance(response_data_for_operation(endpoint_rows, operation_id), list)


def response_data_example_record(endpoint_rows: list[dict[str, object]], operation_id: str) -> dict[str, object]:
    data = response_data_for_operation(endpoint_rows, operation_id)
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return {}


def ts_property_access(field: str) -> str:
    return f".{field}" if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", field) else f"[{json.dumps(field, ensure_ascii=False)}]"


def literal_ts_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _endpoint_row(endpoint_rows: list[dict[str, object]], operation_id: str) -> dict[str, object]:
    for row in endpoint_rows:
        if str(row.get("endpoint_name") or row.get("operation_id") or "").strip() == operation_id:
            return row
    return {}


def _mechanical_authority_example(row: dict[str, object]) -> bool:
    """Return True when the P2 authority renderer, not semantic authority, owns example values."""
    explicit = str(row.get("response_example_authority") or "").strip().casefold()
    if explicit:
        return explicit == "mechanical-shape-only"
    profile = str(row.get("response_profile") or "").casefold()
    return "contract-bound response for" in profile


def scalar_business_value_fields(endpoint_rows: list[dict[str, object]], operation_id: str) -> dict[str, object]:
    row = _endpoint_row(endpoint_rows, operation_id)
    record = response_data_example_record(endpoint_rows, operation_id)
    explicit_literals = {
        str(item).strip()
        for item in row.get("semantic_literal_fields", [])
        if str(item).strip()
    } if isinstance(row.get("semantic_literal_fields"), list) else set()
    mechanical_example = _mechanical_authority_example(row)
    values: dict[str, object] = {}
    for field, value in record.items():
        normalized = normalize_field_token(field)
        if normalized in {"traceid", "createdat", "updatedat"} or normalized.endswith("id"):
            continue
        if mechanical_example and field not in explicit_literals:
            # Authority-mode response examples are mechanically generated shape/sample
            # material. They cannot become business-value assertions without an
            # explicit authority-bearing literal marker.
            continue
        if isinstance(value, (str, int, float, bool)) and value is not None:
            values[field] = value
    return values


def first_matching_failure_code(failure_codes: list[str], pattern: str) -> str:
    regex = re.compile(pattern)
    for code in failure_codes:
        if regex.search(code):
            return code
    return ""


def provider_defer_is_explicit(p2_authority: dict[str, object] | None) -> bool:
    authority = p2_authority or {}
    realizations = authority.get("non_operation_realizations", []) if isinstance(authority, dict) else []
    if isinstance(realizations, list):
        for row in realizations:
            if not isinstance(row, dict):
                continue
            realization_id = str(row.get("realization_id") or "").upper().replace("_", "-")
            if "PROVIDER-DEFER" in realization_id:
                return True
    p1_authority = authority.get("p1_authority", {}) if isinstance(authority, dict) else {}
    feature_dispositions = p1_authority.get("feature_dispositions", []) if isinstance(p1_authority, dict) else []
    if isinstance(feature_dispositions, list):
        for row in feature_dispositions:
            if not isinstance(row, dict):
                continue
            feature_id = str(row.get("feature_id") or "").upper().replace("_", "-")
            if "PROVIDER-DEFER" in feature_id:
                return True
    return False


def provider_neutral_runtime_is_unconfigured(p2_authority: dict[str, object] | None) -> bool:
    """Return True when P2 requires a provider-neutral port but freezes no concrete provider.

    This is distinct from an explicit provider defer. The business capability may be
    first-wave authority, while the current generated deployment must still fail
    honestly until a concrete provider adapter is configured.
    """
    authority = p2_authority or {}
    dependencies = authority.get("dependency_dispositions", []) if isinstance(authority, dict) else []
    if not isinstance(dependencies, list):
        return False
    activated = [row for row in dependencies if isinstance(row, dict) and str(row.get("disposition") or "").strip() == "activate"]
    if not activated:
        return False
    provider_rows = [
        row for row in activated
        if any(token in " ".join(str(row.get(key) or "") for key in ("dependency_id", "statement", "reason", "claim_ceiling")).casefold()
               for token in ("provider-neutral", "provider neutral", "vendor", "model inference", "vision/ocr", "vision ocr"))
    ]
    return bool(provider_rows) and all(
        any(token in str(row.get("claim_ceiling") or "").casefold() for token in ("vendor", "provider", "quality", "accuracy"))
        for row in provider_rows
    )


def provider_unconfigured_operation_failures(p2_authority: dict[str, object] | None) -> dict[str, str]:
    """Return 503 operation boundaries for an unconfigured provider-neutral runtime."""
    authority = p2_authority or {}
    if not provider_neutral_runtime_is_unconfigured(authority):
        return {}
    decisions = authority.get("data_and_interaction_decisions", []) if isinstance(authority, dict) else []
    if not isinstance(decisions, list):
        return {}
    result: dict[str, str] = {}
    for row in decisions:
        if not isinstance(row, dict):
            continue
        operation_id = str(row.get("operation_id") or "").strip()
        raw_failures = row.get("failure_codes", "")
        candidates: list[tuple[str, str]] = []
        if isinstance(raw_failures, str):
            candidates.extend((status, code) for status, code in re.findall(r"\b(\d{3})\s+([A-Za-z0-9_-]+)", raw_failures))
        elif isinstance(raw_failures, list):
            candidates.extend(
                (str(failure.get("status") or "").strip(), str(failure.get("error_code") or "").strip())
                for failure in raw_failures if isinstance(failure, dict)
            )
        for status, code in candidates:
            normalized = code.casefold().replace("-", "_")
            if status == "503" and "unavailable" in normalized and any(token in normalized for token in ("model", "vision", "provider", "observation")):
                result[operation_id] = code
                break
    return result


def provider_runtime_boundary_failures(p2_authority: dict[str, object] | None) -> dict[str, str]:
    """Unify explicit defer and provider-neutral/unconfigured deployment boundaries."""
    return {
        **provider_deferred_operation_failures(p2_authority),
        **provider_unconfigured_operation_failures(p2_authority),
    }


def provider_deferred_operation_failures(p2_authority: dict[str, object] | None) -> dict[str, str]:
    """Return only authority-explicit provider/observation unavailability boundaries.

    Generic dependency failures remain normal failure variants. A positive scenario is
    bounded by honest unavailability only when P2 explicitly defers provider-deep work
    and the operation contract names a provider/observation-specific 503 code.
    """
    authority = p2_authority or {}
    if not provider_defer_is_explicit(authority):
        return {}
    decisions = authority.get("data_and_interaction_decisions", []) if isinstance(authority, dict) else []
    if not isinstance(decisions, list):
        return {}
    result: dict[str, str] = {}
    for row in decisions:
        if not isinstance(row, dict):
            continue
        operation_id = str(row.get("operation_id") or "").strip()
        if not operation_id:
            continue
        raw_failures = row.get("failure_codes", "")
        candidates: list[tuple[str, str]] = []
        if isinstance(raw_failures, str):
            candidates.extend(
                (status, code)
                for status, code in re.findall(r"\b(\d{3})\s+([A-Za-z0-9_-]+)", raw_failures)
            )
        elif isinstance(raw_failures, list):
            for failure in raw_failures:
                if not isinstance(failure, dict):
                    continue
                candidates.append(
                    (
                        str(failure.get("status") or "").strip(),
                        str(failure.get("error_code") or "").strip(),
                    )
                )
        for status, code in candidates:
            normalized = code.lower().replace("-", "_")
            provider_specific = ("provider" in normalized or "observation" in normalized) and "unavailable" in normalized
            if status == "503" and provider_specific:
                result[operation_id] = code
                break
    return result
