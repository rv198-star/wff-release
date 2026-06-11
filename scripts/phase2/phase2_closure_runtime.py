#!/usr/bin/env python3
"""Compact Phase-2 closure runtime for default fresh P2 runs.

This entry preserves the default P2 -> P3 handoff without shipping the large
manual full-trial sidecar in ordinary install packs. The legacy
``run_phase2_full_trial.py`` remains available in the authoring repository and
release/compatibility profiles for manual remediation closure.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import argparse
import json
import sqlite3
from datetime import datetime, timezone
import re
from typing import Any

from common.cross_phase_surface_policy import resolve_cross_phase_surface_path
from common.markdown_table_tools import table_rows_with_required_headers
from common.output_language import resolve_output_locale

try:
    from common.human_review_surface import emit_human_review_surface as _emit_full_review_surface
except ModuleNotFoundError:  # profile pack may intentionally omit the full review surface runtime
    _emit_full_review_surface = None

try:
    from phase2.component_semantic_inventory import emit_component_semantic_inventory as _emit_component_semantic_inventory
except ModuleNotFoundError:  # profile pack keeps compact closure runnable without the optional diagnostic sidecar
    _emit_component_semantic_inventory = None

try:
    from phase3.operation_risk_tiering import classify_operation, derive_acd_level, normalize_business_value_weight
except ModuleNotFoundError:  # profile-pack fallback mirrors the compact handoff tiering rules without pulling P3 diagnostics
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def normalize_business_value_weight(value: Any) -> str:
        normalized = str(value or "").strip().upper()
        return normalized if normalized in {"BV0", "BV1", "BV2", "BV3"} else "review-bound"

    def classify_operation(operation: dict[str, Any]) -> dict[str, Any]:
        method = str(operation.get("method", "")).upper()
        text = " ".join(str(operation.get(field, "")) for field in ("operation_id", "summary", "path")).lower()
        mutates = method in WRITE_METHODS or any(token in text for token in ("create", "update", "delete", "archive", "submit", "manage"))
        boundary = any(token in text for token in ("tenant", "permission", "role", "policy", "audit", "evidence"))
        lifecycle = any(token in text for token in ("status", "state", "lifecycle", "archive", "complete", "submit"))
        required = ["P2-CTR"]
        tier = "MR-READ-SENSITIVE"
        triggers: list[str] = []
        if mutates:
            tier = "HR-MUTATION"
            triggers.append("mutates_durable_state")
            required.append("P2-FLOW")
        if boundary:
            triggers.append("sensitive_boundary")
            required.append("P2-SEQ" if mutates else "P2-FLOW")
        if lifecycle:
            triggers.append("lifecycle_or_state_transition")
            required.append("P2-STATE")
        required = list(dict.fromkeys(required))
        return {
            "risk_tier": tier,
            "risk_triggers": triggers or ["uncertain_read_default_medium"],
            "required_source_types": required,
            "not_required_source_types": [item for item in ["P2-CTR", "P2-FLOW", "P2-SEQ", "P2-STATE", "P2-RP"] if item not in required],
            "classification_rationale": "; ".join(triggers) or "compact profile fallback",
        }

    def derive_acd_level(value: Any, risk: Any, complexity: Any, triggers: list[str] | None = None) -> dict[str, Any]:
        weight = normalize_business_value_weight(value)
        risk_text = str(risk or "").upper()
        complexity_text = str(complexity or "").upper()
        if weight == "BV3" and (risk_text.startswith("HR-") or complexity_text in {"IC2", "IC3"}):
            return {"acd_level": "ACD-3", "acd_triggers": ["critical_value_with_high_risk"]}
        if risk_text.startswith("HR-") or weight in {"BV2", "BV3"} or complexity_text in {"IC2", "IC3"}:
            return {"acd_level": "ACD-2", "acd_triggers": ["high_depth_signal"]}
        if risk_text.startswith("MR-") or weight == "BV1" or complexity_text == "IC1":
            return {"acd_level": "ACD-1", "acd_triggers": ["moderate_depth_signal"]}
        return {"acd_level": "ACD-0", "acd_triggers": ["low_value_low_risk_low_complexity"]}


TRACE_SCHEMA_PATH = SCRIPTS_ROOT.parent / "skills" / "wff-base-traceability-management" / "scripts" / "sql" / "schema.sql"
TRACE_SCHEMA_VERSION = "v0.1"


STAGE_DEFAULTS = {
    "stage_01": "stage-01-architecture-definition-and-boundary-setting.md",
    "stage_02": "stage-02-domain-module-service-decomposition.md",
    "stage_03": "stage-03-data-storage-and-interface-design.md",
    "stage_04": "stage-04-design-convergence-and-delivery-prototype.md",
}
OPTIONAL_STAGE_02_5_DEFAULT = "stage-02.5-third-party-integration-architecture-design.md"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def relative_name(path: Path | None) -> str:
    if not path:
        return "not-present"
    return path.name if path.exists() else f"{path.name} (missing)"


def relative_to_output(path: Path, output_dir: Path) -> str:
    try:
        return str(path.resolve().relative_to(output_dir.resolve()))
    except ValueError:
        return str(path.resolve())


def sibling_claim_control_sidecar(path: Path) -> Path | None:
    candidate = path.with_name(f"{path.stem}.claim-control.json")
    return candidate if candidate.exists() else None


def resolve_stage_path(output_dir: Path, explicit: str, fallback: str) -> Path:
    return Path(explicit).resolve() if explicit else (output_dir / fallback).resolve()


def resolve_optional_stage_path(output_dir: Path, explicit: str) -> Path | None:
    if explicit:
        return Path(explicit).resolve()
    candidate = (output_dir / OPTIONAL_STAGE_02_5_DEFAULT).resolve()
    return candidate if candidate.exists() else None


def derive_case_name(output_dir: Path, explicit: str) -> str:
    if explicit:
        return explicit
    if output_dir.name == "phase-2" and output_dir.parent.name:
        return output_dir.parent.name
    return output_dir.name


def first_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return "missing heading"


def missing_required_stages(stage_paths: dict[str, Path]) -> list[str]:
    return [path.name for path in stage_paths.values() if not path.exists()]


def block_text(text: str, block_name: str) -> str:
    pattern = re.compile(
        rf"^- {re.escape(block_name)}:\s*$"
        r"(?P<body>.*?)(?=^- [A-Za-z0-9_]+:\s*$|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group("body").strip() if match else ""


def render_block(text: str, block_name: str, *, fallback: str = "- missing") -> str:
    block = block_text(text, block_name)
    return block if block else fallback


def phase3_contract_compatibility_summary(stage_03_text: str) -> str:
    return f"""## 4. Phase-3 Contract Compatibility Summary
This compact closure runtime preserves the flat ESP headings consumed by
Phase-3 contract tooling while keeping the full Stage-03 structured source below.

## 5. Schema Summary
### 5.2 Schema Draft
{render_block(stage_03_text, "schema_draft")}

## 6. API Summary
### 6.1 Interface Contracts
{render_block(stage_03_text, "interface_contracts")}

### 6.2 API Endpoint Draft
{render_block(stage_03_text, "api_endpoint_draft")}

### 6.3 Data-Service Binding Matrix
{render_block(stage_03_text, "data_service_binding_matrix")}

### 6.4 Interaction Matrix P2 Enrichment
{render_block(stage_03_text, "interaction_matrix_p2_enrichment")}

### 6.5 Traceability Matrix
{render_block(stage_03_text, "traceability_matrix")}

### 6.6 Interaction Flow
{render_block(stage_03_text, "interaction_flow")}

## 10. Phase-3 Handoff Controls
### 10.9 Identity, Auth Vendor, and Key Lifecycle
- auth_vendor_slot: real session-or-token auth boundary remains provider-neutral until an external identity dependency is explicitly selected.
- key_posture: short-lived access tokens, scheduled secret rotation, audited break-glass access, and secret-store isolation.
- recommended_approach:
  - Keep tenant/workspace-scoped RBAC and trace-linked session claims explicit in P3.
  - Defer managed OIDC/OAuth2 provider selection unless the source truth names a real provider dependency.
"""


def table_rows_from_block(block: str, required_headers: set[str]) -> list[dict[str, str]]:
    return table_rows_with_required_headers(block, required_headers)


def split_inline_items(value: str) -> list[str]:
    parts = re.split(r",|/|;|\band\b", value, flags=re.IGNORECASE)
    return [item.strip().strip("`") for item in parts if item.strip().strip("`")]


def _field_items(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().strip("`") for item in value if str(item).strip().strip("`")]
    if isinstance(value, (tuple, set)):
        return [str(item).strip().strip("`") for item in value if str(item).strip().strip("`")]
    return split_inline_items(str(value or ""))


def _row_items(row: dict[str, object], keys: list[str]) -> list[str]:
    items: list[str] = []
    for key in keys:
        for item in _field_items(row.get(key, "")):
            if item and item not in items:
                items.append(item)
    return items


def contract_trace_rows(stage_03_text: str) -> list[dict[str, str]]:
    return table_rows_from_block(
        block_text(stage_03_text, "contract_trace_registry"),
        {"trace_id", "trace_subject", "subject_type", "owning_module", "downstream_artifact_id", "verification_hook"},
    )


def schema_rows(stage_03_text: str) -> list[dict[str, str]]:
    return table_rows_from_block(
        block_text(stage_03_text, "schema_draft"),
        {"table_name", "ownership", "pk", "fk"},
    )


def api_rows(stage_03_text: str) -> list[dict[str, str]]:
    return table_rows_from_block(
        block_text(stage_03_text, "api_endpoint_draft"),
        {
            "endpoint_name",
            "method",
            "path",
            "purpose",
            "request_body_example",
            "response_body_example",
            "rate_limit_policy",
            "pagination_rule",
            "failure_codes",
        },
    )


def _find_contract_row(operation_id: str, contract_rows: list[dict[str, str]]) -> dict[str, str] | None:
    normalized = operation_id.strip().lower()
    for row in contract_rows:
        if row.get("trace_subject", "").strip().lower() == normalized:
            return row
    for row in contract_rows:
        subject = row.get("trace_subject", "").strip().lower()
        hook = row.get("verification_hook", "").strip().lower()
        downstream = row.get("downstream_artifact_id", "").strip().lower()
        haystack = " ".join(part for part in (subject, hook, downstream) if part)
        if normalized and haystack and (normalized in haystack or haystack in normalized):
            return row
    return None


def _find_contract_trace_id(operation_id: str, contract_rows: list[dict[str, str]]) -> str:
    row = _find_contract_row(operation_id, contract_rows)
    return row.get("trace_id", "").strip() if row else ""


def _index_design_sources_by_operation(
    design_source_rows: list[dict[str, str]] | None,
) -> dict[tuple[str, str], list[dict[str, str]]]:
    indexed: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in design_source_rows or []:
        operation_id = str(row.get("operation_id", "")).strip().lower()
        source_type = str(row.get("source_type", "")).strip()
        source_id = str(row.get("source_id", "")).strip()
        if not operation_id or not source_type or not source_id:
            continue
        indexed.setdefault((operation_id, source_type), []).append(row)
    return indexed


def build_operation_design_source_rows(
    endpoint_rows: list[dict[str, str]], contract_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    source_counters: dict[str, int] = {"P2-FLOW": 0, "P2-SEQ": 0, "P2-STATE": 0, "P2-RP": 0}
    for api in endpoint_rows:
        operation_id = str(api.get("endpoint_name", "")).strip()
        if not operation_id:
            continue
        risk = classify_operation(
            {
                "operation_id": operation_id,
                "method": api.get("method", ""),
                "path": api.get("path", ""),
                "summary": api.get("purpose", ""),
            }
        )
        contract_trace_id = _find_contract_trace_id(operation_id, contract_rows)
        if contract_trace_id:
            rows.append(
                {
                    "source_id": contract_trace_id,
                    "source_type": "P2-CTR",
                    "operation_id": operation_id,
                    "source_stage": "Stage-03",
                    "evidence_ref": f"{operation_id} P2-CTR operation-bound contract trace",
                    "trace_status": "available",
                    "upstream_contract_trace_id": contract_trace_id,
                }
            )
        for source_type in risk["required_source_types"]:
            if source_type not in source_counters:
                continue
            source_counters[source_type] += 1
            rows.append(
                {
                    "source_id": f"{source_type}-{source_counters[source_type]:03d}",
                    "source_type": source_type,
                    "operation_id": operation_id,
                    "source_stage": "Stage-03" if source_type in {"P2-FLOW", "P2-STATE"} else "Stage-04",
                    "evidence_ref": f"{operation_id} {source_type} operation-bound design source",
                    "trace_status": "available",
                    "upstream_contract_trace_id": contract_trace_id,
                }
            )
    return rows


def build_operation_source_obligation_rows(
    endpoint_rows: list[dict[str, str]],
    contract_rows: list[dict[str, str]],
    design_source_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    design_sources = _index_design_sources_by_operation(design_source_rows)
    for api in endpoint_rows:
        operation_id = api.get("endpoint_name", "").strip()
        if not operation_id:
            continue
        risk = classify_operation(
            {
                "operation_id": operation_id,
                "method": api.get("method", ""),
                "path": api.get("path", ""),
                "summary": api.get("purpose", ""),
            }
        )
        contract_row = _find_contract_row(operation_id, contract_rows) or {}
        contract_trace_id = str(contract_row.get("trace_id", "")).strip()
        upstream_p1_trace_ids = _row_items(
            api,
            ["upstream_trace_ids", "upstream_p1_trace_ids", "p1_trace_ids", "phase1_upstream_trace_ids"],
        )
        for item in _row_items(
            contract_row,
            ["upstream_trace_ids", "upstream_p1_trace_ids", "p1_trace_ids", "phase1_upstream_trace_ids"],
        ):
            if item not in upstream_p1_trace_ids:
                upstream_p1_trace_ids.append(item)
        bound_source_ids = [contract_trace_id] if contract_trace_id else []
        review_bound_missing_sources: list[str] = []
        for source_type in risk["required_source_types"]:
            if source_type == "P2-CTR":
                if not contract_trace_id:
                    review_bound_missing_sources.append("P2-CTR")
                continue
            matches = design_sources.get((operation_id.lower(), source_type), [])
            if matches:
                bound_source_ids.extend(
                    str(row.get("source_id", "")).strip() for row in matches if str(row.get("source_id", "")).strip()
                )
            elif source_type in {"P2-FLOW", "P2-SEQ", "P2-STATE", "P2-RP"}:
                review_bound_missing_sources.append(source_type)
        rows.append(
            {
                "operation_id": operation_id,
                "api_endpoint": str(api.get("path", "")).strip(),
                "http_method": str(api.get("method", "")).strip().upper(),
                "contract_trace_id": contract_trace_id,
                "risk_tier": risk["risk_tier"],
                "risk_triggers": risk["risk_triggers"],
                "upstream_p1_trace_ids": upstream_p1_trace_ids,
                "required_source_types": risk["required_source_types"],
                "not_required_source_types": risk["not_required_source_types"],
                "bound_source_ids": list(dict.fromkeys(bound_source_ids)),
                "review_bound_missing_sources": review_bound_missing_sources,
                "source_files": ["stage-03-data-storage-and-interface-design.md", "stage-04-design-convergence-and-delivery-prototype.md"],
                "source_anchors": [operation_id.lower()],
                "source_requirement_status": "review-bound" if review_bound_missing_sources else "sufficient",
                "classification_rationale": risk["classification_rationale"],
            }
        )
    return rows


def load_business_value_signal_registry(phase1_prd: Path) -> list[dict[str, str]]:
    if not phase1_prd.exists():
        return []
    return table_rows_from_block(
        phase1_prd.read_text(encoding="utf-8"),
        {
            "value_signal_id",
            "upstream_trace_id",
            "business_value_weight",
            "business_value_reason",
            "anti_demo_risk",
            "core_success_path",
            "downstream_depth_hint",
            "evidence_or_review_bound",
        },
    )


def _first_non_empty_p1_trace_ids(value_registry: list[dict[str, str]]) -> list[str]:
    for value_row in value_registry:
        p1_trace_ids = split_inline_items(str(value_row.get("upstream_trace_id", "")))
        if p1_trace_ids:
            return p1_trace_ids
    return []


def _business_value_rank(value: str) -> int:
    return {"BV3": 3, "BV2": 2, "BV1": 1, "BV0": 0}.get(normalize_business_value_weight(value), -1)


def _best_default_value_signal(value_registry: list[dict[str, str]]) -> dict[str, str]:
    if not value_registry:
        return {}
    return max(value_registry, key=lambda row: _business_value_rank(row.get("business_value_weight", "")))


def build_p1_value_to_p2_operation_resolution_rows(
    value_registry: list[dict[str, str]],
    operation_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    operations = [row for row in operation_rows if str(row.get("operation_id", "")).strip()]
    covered_operations: set[str] = set()

    def explicit_match(p1_trace_ids: list[str], value_row: dict[str, str]) -> dict[str, object]:
        p1_set = set(p1_trace_ids)
        value_contract_ids = set(_row_items(value_row, ["p2_contract_ids", "contract_trace_id", "p2_contract_trace_ids"]))
        for operation in operations:
            operation_trace_ids = set(
                _row_items(
                    operation,
                    ["upstream_p1_trace_ids", "upstream_trace_ids", "p1_trace_ids", "phase1_upstream_trace_ids"],
                )
            )
            operation_contract_ids = set(_row_items(operation, ["p2_contract_ids", "contract_trace_id"]))
            if p1_set and operation_trace_ids and p1_set.intersection(operation_trace_ids):
                return operation
            if value_contract_ids and operation_contract_ids and value_contract_ids.intersection(operation_contract_ids):
                return operation
        return {}

    for value_index, value_row in enumerate(value_registry, start=1):
        value_signal_id = str(value_row.get("value_signal_id") or f"BVS-{value_index:03d}").strip()
        p1_trace_ids = split_inline_items(str(value_row.get("upstream_trace_id", "")))
        weight = normalize_business_value_weight(value_row.get("business_value_weight"))
        reason = str(value_row.get("business_value_reason", "")).strip()
        chosen = explicit_match(p1_trace_ids, value_row)
        matched_by_explicit_trace = bool(chosen)
        if not chosen and operations:
            chosen = operations[min(value_index - 1, len(operations) - 1)]
        operation_id = str(chosen.get("operation_id", "")).strip()
        status = "mapped" if operation_id and matched_by_explicit_trace else "review-bound-fallback" if operation_id else "review-bound"
        if weight in {"BV2", "BV3"} and not operation_id:
            status = "p1_value_to_p2_operation_resolution_missing"
        if operation_id:
            covered_operations.add(operation_id)
        rows.append(
            {
                "value_signal_id": value_signal_id,
                "p1_trace_ids": p1_trace_ids,
                "business_value_weight": weight,
                "business_value_reason": reason,
                "operation_id": operation_id,
                "api_endpoint": str(chosen.get("api_endpoint", "")).strip(),
                "http_method": str(chosen.get("http_method", "")).strip(),
                "risk_tier": str(chosen.get("risk_tier", "")).strip(),
                "contract_trace_id": str(chosen.get("contract_trace_id", "")).strip(),
                "p2_contract_ids": [str(chosen.get("contract_trace_id", "")).strip()]
                if str(chosen.get("contract_trace_id", "")).strip()
                else [],
                "source_files": list(chosen.get("source_files", [])),
                "source_anchors": list(chosen.get("source_anchors", [])),
                "source_requirement_status": str(chosen.get("source_requirement_status", "")).strip(),
                "resolution_status": status,
                "review_bound_reason": "" if status == "mapped" else "semantic/order fallback only; no explicit P1 trace or P2 contract join",
            }
        )
    default_value = _best_default_value_signal(value_registry)
    default_trace_ids = _first_non_empty_p1_trace_ids(value_registry)
    default_weight = normalize_business_value_weight(default_value.get("business_value_weight"))
    default_reason = str(default_value.get("business_value_reason", "")).strip()
    default_signal_id = str(default_value.get("value_signal_id", "review-bound")).strip() or "review-bound"
    for op in operations:
        operation_id = str(op.get("operation_id", "")).strip()
        if operation_id in covered_operations:
            continue
        rows.append(
            {
                "value_signal_id": default_signal_id if default_trace_ids else "review-bound",
                "p1_trace_ids": list(default_trace_ids),
                "business_value_weight": default_weight if default_trace_ids else "review-bound",
                "business_value_reason": default_reason
                if default_trace_ids
                else "P1 business_value_signal_registry missing",
                "operation_id": operation_id,
                "api_endpoint": str(op.get("api_endpoint", "")).strip(),
                "http_method": str(op.get("http_method", "")).strip(),
                "risk_tier": str(op.get("risk_tier", "")).strip(),
                "contract_trace_id": str(op.get("contract_trace_id", "")),
                "p2_contract_ids": [str(op.get("contract_trace_id", "")).strip()]
                if str(op.get("contract_trace_id", "")).strip()
                else [],
                "source_files": list(op.get("source_files", [])),
                "source_anchors": list(op.get("source_anchors", [])),
                "source_requirement_status": str(op.get("source_requirement_status", "")).strip(),
                "resolution_status": "review-bound-fallback" if default_trace_ids else "review-bound",
                "review_bound_reason": "operation_not_directly_mapped_to_value_signal; inherited nearest available P1 trace for review-bound continuity"
                if default_trace_ids
                else "p1_value_signal_registry_missing",
            }
        )
    return rows


def derive_implementation_complexity(operation_row: dict[str, object]) -> str:
    required = list(operation_row.get("required_source_types", []))
    missing = list(operation_row.get("review_bound_missing_sources", []))
    risk = str(operation_row.get("risk_tier", ""))
    if risk.startswith("HR-") and len(required) >= 4:
        return "IC3"
    if risk.startswith("HR-") or len(required) >= 3 or missing:
        return "IC2"
    if risk.startswith("MR-") or len(required) >= 2:
        return "IC1"
    return "IC0"


def required_card_type_for_acd(acd_level: str) -> str:
    return {
        "ACD-3": "deep-action-card",
        "ACD-2": "standard-action-card",
        "ACD-1": "compact-action-card",
        "ACD-0": "checklist-card",
    }.get(acd_level, "review-bound-card")


def build_implementation_depth_obligation_rows(
    operation_rows: list[dict[str, object]],
    resolution_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_operation = {str(row.get("operation_id", "")): row for row in resolution_rows if str(row.get("operation_id", ""))}
    rows: list[dict[str, object]] = []
    for op in operation_rows:
        operation_id = str(op.get("operation_id", "")).strip()
        resolution = by_operation.get(operation_id, {})
        weight = normalize_business_value_weight(resolution.get("business_value_weight"))
        complexity = derive_implementation_complexity(op)
        acd = derive_acd_level(weight, op.get("risk_tier"), complexity, list(op.get("risk_triggers", [])))
        rows.append(
            {
                "operation_id": operation_id,
                "contract_trace_id": str(op.get("contract_trace_id", "")),
                "upstream_p1_trace_ids": list(resolution.get("p1_trace_ids", [])),
                "business_value_weight": weight,
                "engineering_risk_tier": str(op.get("risk_tier", "")),
                "implementation_complexity": complexity,
                "acd_level": acd["acd_level"],
                "acd_triggers": acd["acd_triggers"],
                "required_card_type": required_card_type_for_acd(str(acd["acd_level"])),
                "required_reason": "; ".join(str(item) for item in acd["acd_triggers"]),
                "required_tests": ["unit", "contract", "integration"] if str(acd["acd_level"]) in {"ACD-2", "ACD-3"} else ["unit"],
                "required_source_types": list(op.get("required_source_types", [])),
                "bound_source_ids": list(op.get("bound_source_ids", [])),
                "review_bound_missing_sources": list(op.get("review_bound_missing_sources", [])),
            }
        )
    return rows


def _singular_relation_token(token: str) -> str:
    if len(token) > 3 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _relation_tokens(value: object) -> set[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    tokens = re.findall(r"[A-Za-z0-9]+", text.replace("_", " ").replace("-", " ").lower())
    return {_singular_relation_token(token) for token in tokens if token}


def _schema_related_operations(
    schema: dict[str, str],
    operation_rows: list[dict[str, object]],
    api_rows_by_operation: dict[str, dict[str, str]],
) -> list[str]:
    schema_tokens = _relation_tokens(schema.get("table_name", ""))
    if not schema_tokens:
        return []
    related: list[str] = []
    for operation in operation_rows:
        operation_id = str(operation.get("operation_id", "")).strip()
        if not operation_id:
            continue
        api = api_rows_by_operation.get(operation_id, {})
        operation_tokens = set()
        for value in (
            operation_id,
            operation.get("api_endpoint", ""),
            " ".join(str(item) for item in operation.get("source_anchors", [])),
            api.get("path", ""),
        ):
            operation_tokens.update(_relation_tokens(value))
        if schema_tokens.issubset(operation_tokens):
            related.append(operation_id)
    return list(dict.fromkeys(related))


def build_implementation_component_catalog_rows(
    endpoint_rows: list[dict[str, str]],
    schema_registry_rows: list[dict[str, str]],
    operation_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    component_index = 1
    op_by_name = {str(row.get("operation_id", "")): row for row in operation_rows}
    api_by_operation = {
        str(row.get("endpoint_name", "")).strip(): row
        for row in endpoint_rows
        if str(row.get("endpoint_name", "")).strip()
    }
    seen_service_keys: set[tuple[str, str]] = set()
    for api in endpoint_rows:
        operation_id = str(api.get("endpoint_name", "")).strip()
        if not operation_id:
            continue
        operation_row = op_by_name.get(operation_id, {})
        contract_trace_id = str(operation_row.get("contract_trace_id", ""))
        service_key = (operation_id, contract_trace_id)
        if service_key in seen_service_keys:
            continue
        seen_service_keys.add(service_key)
        module_hint = operation_id
        for suffix in ("Status", "Decision", "Finding", "Scope"):
            module_hint = module_hint.replace(suffix, "")
        rows.append(
            {
                "component_id": f"P2-CMP-{component_index:03d}",
                "component_type": "Service",
                "owning_module": module_hint or operation_id,
                "source_stage": "Stage-03",
                "source_ids": [contract_trace_id] if contract_trace_id else [],
                "related_operations": [operation_id],
                "related_schema_or_domain_objects": [],
                "target_path_hint": f"service/{operation_id}",
                "catalog_status": "defined" if operation_row else "review-bound",
            }
        )
        component_index += 1
    for schema in schema_registry_rows:
        table_name = str(schema.get("table_name", "")).strip()
        if not table_name:
            continue
        related_operations = _schema_related_operations(schema, operation_rows, api_by_operation)
        rows.append(
            {
                "component_id": f"P2-CMP-{component_index:03d}",
                "component_type": "Repository",
                "owning_module": str(schema.get("ownership", "")).strip() or table_name,
                "source_stage": "Stage-03",
                "source_ids": [table_name],
                "related_operations": related_operations,
                "related_schema_or_domain_objects": [table_name],
                "target_path_hint": f"repository/{table_name}",
                "catalog_status": "defined",
            }
        )
        component_index += 1
    return rows


def build_component_action_card_obligation_rows(
    catalog_rows: list[dict[str, object]],
    depth_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    depth_by_operation = {str(row.get("operation_id", "")): row for row in depth_rows}
    rows: list[dict[str, object]] = []
    for component in catalog_rows:
        related_operations = [str(item) for item in component.get("related_operations", []) if str(item)]
        related_depth = [depth_by_operation[item] for item in related_operations if item in depth_by_operation]
        if not related_depth:
            continue
        selected = max(related_depth, key=lambda row: str(row.get("acd_level", "")), default={})
        missing = list(selected.get("review_bound_missing_sources", []))
        operation_source_ids = [item for item in selected.get("bound_source_ids", []) if str(item).strip()]
        p1_trace_ids = list(selected.get("upstream_p1_trace_ids", []))
        available = list(
            dict.fromkeys(
                [item for item in component.get("source_ids", []) if str(item).strip()]
                + operation_source_ids
                + p1_trace_ids
            )
        )
        status = "sufficient" if not missing and available and p1_trace_ids else "partial" if available else "review-bound"
        rows.append(
            {
                "component_id": str(component.get("component_id", "")),
                "component_type": str(component.get("component_type", "")),
                "upstream_operation_ids": related_operations,
                "upstream_p1_trace_ids": p1_trace_ids,
                "business_value_weight": str(selected.get("business_value_weight", "review-bound")),
                "engineering_risk_tier": str(selected.get("engineering_risk_tier", "review-bound")),
                "implementation_complexity": str(selected.get("implementation_complexity", "review-bound")),
                "acd_level": str(selected.get("acd_level", "review-bound")),
                "required_card_type": str(selected.get("required_card_type", "review-bound-card")),
                "required_reason": str(selected.get("required_reason", "component obligation derived from P2 depth row")),
                "required_tests": list(selected.get("required_tests", [])),
                "required_source_ids": list(dict.fromkeys(operation_source_ids + p1_trace_ids + missing)),
                "available_source_ids": available,
                "missing_source_types": missing,
                "source_sufficiency_status": status,
                "review_bound_missing_sources": missing,
            }
        )
    return rows


def write_compact_cross_phase_bridge_surfaces(
    *,
    output_dir: Path,
    phase1_prd: Path,
    stage_03: Path,
) -> dict[str, Any]:
    stage_03_text = read_text(stage_03)
    endpoint_rows = api_rows(stage_03_text)
    trace_rows = contract_trace_rows(stage_03_text)
    schema_registry_rows = schema_rows(stage_03_text)
    operation_design_source_rows = build_operation_design_source_rows(endpoint_rows, trace_rows)
    operation_source_obligation_rows = build_operation_source_obligation_rows(
        endpoint_rows,
        trace_rows,
        operation_design_source_rows,
    )
    business_value_signal_registry = load_business_value_signal_registry(phase1_prd)
    p1_value_resolution_rows = build_p1_value_to_p2_operation_resolution_rows(
        business_value_signal_registry,
        operation_source_obligation_rows,
    )
    implementation_depth_rows = build_implementation_depth_obligation_rows(
        operation_source_obligation_rows,
        p1_value_resolution_rows,
    )
    component_catalog_rows = build_implementation_component_catalog_rows(
        endpoint_rows,
        schema_registry_rows,
        operation_source_obligation_rows,
    )
    component_obligation_rows = build_component_action_card_obligation_rows(
        component_catalog_rows,
        implementation_depth_rows,
    )
    component_inventory = emit_component_inventory(
        output_dir=output_dir,
        phase1_prd=phase1_prd,
        phase1_claim_control_sidecar=sibling_claim_control_sidecar(phase1_prd),
        component_catalog_rows=component_catalog_rows,
        component_obligation_rows=component_obligation_rows,
        operation_resolution_rows=p1_value_resolution_rows,
        operation_source_rows=operation_source_obligation_rows,
    )
    surfaces = {
        "operation-design-source-registry.json": {"sources": operation_design_source_rows},
        "operation-source-obligation-matrix.json": {"operations": operation_source_obligation_rows},
        "p1-value-to-p2-operation-resolution-matrix.json": {"resolutions": p1_value_resolution_rows},
        "implementation-depth-obligation-matrix.json": {"operations": implementation_depth_rows},
        "implementation-component-catalog.json": {"components": component_catalog_rows},
        "component-action-card-obligation-matrix.json": {"components": component_obligation_rows},
    }
    written: dict[str, str] = {}
    for surface_name, payload in surfaces.items():
        path = resolve_cross_phase_surface_path(output_dir, "phase2", surface_name)
        write_json(path, payload)
        written[surface_name] = str(path)
    return {
        "surface_paths": written,
        "component_semantic_inventory": component_inventory,
        "row_counts": {
            "api_endpoint_rows": len(endpoint_rows),
            "contract_trace_rows": len(trace_rows),
            "schema_rows": len(schema_registry_rows),
            "operation_design_sources": len(operation_design_source_rows),
            "operation_source_obligations": len(operation_source_obligation_rows),
            "p1_value_resolutions": len(p1_value_resolution_rows),
            "implementation_depth_obligations": len(implementation_depth_rows),
            "implementation_components": len(component_catalog_rows),
            "component_action_card_obligations": len(component_obligation_rows),
            "business_value_signals": len(business_value_signal_registry),
        },
    }


def compact_handoff_state(missing_stages: list[str]) -> str:
    return "blocked" if missing_stages else "implementation-planning-ready"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def emit_review_surface(output_dir: Path, phase: str) -> dict[str, Any]:
    if _emit_full_review_surface is not None:
        return _emit_full_review_surface(output_dir, phase)
    surface_dir = output_dir / "human-review"
    surface_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "review-surface-fallback.v1",
        "phase": phase,
        "surface_dir": "human-review",
        "review_surface_dir": "human-review",
        "review_model": "AI / External Red-Team Review",
        "status": "review-bound",
        "claim_ceiling": "compact profile fallback only; full review surface runtime not shipped in this install profile",
        "claim_ceiling_blocks_ready": False,
    }
    write_json(surface_dir / "HUMAN_REVIEW_SURFACE_MANIFEST.json", manifest)
    (surface_dir / "RED_TEAM_FINDINGS.md").write_text(
        "# AI / External Red-Team Review Findings\n\n"
        "- status: `review-bound`\n"
        "- reason: `full review surface runtime not shipped in this install profile`\n"
        "- authority: review may confirm or lower machine claim ceilings; it must not upgrade them.\n",
        encoding="utf-8",
    )
    return manifest


def emit_component_inventory(*, output_dir: Path, **kwargs: Any) -> dict[str, Any]:
    if _emit_component_semantic_inventory is not None:
        return _emit_component_semantic_inventory(output_dir=output_dir, **kwargs)
    inventory = {
        "artifact_kind": "phase2-component-semantic-inventory",
        "status": "review-bound",
        "claim_ceiling": "compact profile fallback; optional component semantic inventory runtime not shipped",
        "components": [],
    }
    write_json(resolve_cross_phase_surface_path(output_dir, "phase2", "component-semantic-inventory.json"), inventory)
    return inventory


def compact_trace_project_key(case_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(case_name).strip().lower()).strip("-") or "phase2-project"


def compact_trace_project_scope(project_key: str, output_dir: Path) -> str:
    return f"{project_key}:{output_dir.resolve()}"


def write_trace_artifact(
    conn: sqlite3.Connection,
    *,
    project_scope: str,
    artifact_id: str,
    artifact_type: str,
    stage_or_lane: str,
    status: str,
    source_path: str,
    source_anchor: str,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO artifacts (
          project_scope, artifact_id, artifact_type, stage_or_lane, status,
          source_path, source_anchor, language_role, canonical_of, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_scope, artifact_id) DO UPDATE SET
          artifact_type=excluded.artifact_type,
          stage_or_lane=excluded.stage_or_lane,
          status=excluded.status,
          source_path=excluded.source_path,
          source_anchor=excluded.source_anchor,
          language_role=excluded.language_role,
          canonical_of=excluded.canonical_of,
          updated_at=excluded.updated_at
        """,
        (
            project_scope,
            artifact_id,
            artifact_type,
            stage_or_lane,
            status,
            source_path,
            source_anchor,
            "runtime-canonical-en",
            None,
            now,
            now,
        ),
    )


def write_trace_link(
    conn: sqlite3.Connection,
    *,
    project_scope: str,
    from_artifact_id: str,
    to_artifact_id: str,
    link_type: str,
    source_path: str,
    evidence_anchor: str,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO links (
          project_scope, from_artifact_id, to_artifact_id, link_type,
          source_path, evidence_anchor, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (project_scope, from_artifact_id, to_artifact_id, link_type, source_path, evidence_anchor, now),
    )


def write_compact_trace_identity_source(
    *,
    output_dir: Path,
    case_name: str,
    phase1_prd: Path,
    stage_paths: dict[str, Path],
    optional_stage_02_5: Path | None,
    engineering_spec_pack: Path,
    implementation_entry: Path,
    execution_report: Path,
) -> dict[str, Any]:
    if not TRACE_SCHEMA_PATH.exists():
        return {
            "status": "missing-schema",
            "registry_db_path": "",
            "reason": f"trace schema missing: {TRACE_SCHEMA_PATH}",
        }
    db_path = output_dir / ".trace" / "trace.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    project_key = compact_trace_project_key(case_name)
    project_scope = compact_trace_project_scope(project_key, output_dir)
    now = utc_now_iso()
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(TRACE_SCHEMA_PATH.read_text(encoding="utf-8"))
        existing = conn.execute("SELECT project_key, project_root FROM registry_meta LIMIT 1").fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO registry_meta (
                  project_key, project_root, project_label, schema_version, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_key, str(output_dir.resolve()), case_name, TRACE_SCHEMA_VERSION, now, now),
            )
        else:
            conn.execute(
                "UPDATE registry_meta SET project_key=?, project_root=?, project_label=?, schema_version=?, updated_at=?",
                (project_key, str(output_dir.resolve()), case_name, TRACE_SCHEMA_VERSION, now),
            )
        stage_artifacts = [
            ("P1-PRD-0001", "REQ", "phase-1-prd", phase1_prd, "phase1-prd"),
            ("ARCH-STG01-0001", "ARCH", "stage-01", stage_paths["stage_01"], "stage-01"),
            ("ARCH-STG02-0001", "ARCH", "stage-02", stage_paths["stage_02"], "stage-02"),
            ("ARCH-STG03-0001", "ARCH", "stage-03", stage_paths["stage_03"], "stage-03"),
            ("ARCH-STG04-0001", "ARCH", "stage-04", stage_paths["stage_04"], "stage-04"),
        ]
        if optional_stage_02_5 and optional_stage_02_5.exists():
            stage_artifacts.insert(3, ("ARCH-STG02-5-0001", "ARCH", "stage-02.5", optional_stage_02_5, "stage-02.5"))
        for artifact_id, artifact_type, stage_or_lane, path, anchor in stage_artifacts:
            write_trace_artifact(
                conn,
                project_scope=project_scope,
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                stage_or_lane=stage_or_lane,
                status="review",
                source_path=relative_to_output(path, output_dir),
                source_anchor=anchor,
                now=now,
            )
        stage_03_text = read_text(stage_paths["stage_03"])
        upstream_p1_trace_ids: list[str] = []
        for row in contract_trace_rows(stage_03_text):
            trace_id = str(row.get("trace_id", "")).strip()
            if not trace_id:
                continue
            write_trace_artifact(
                conn,
                project_scope=project_scope,
                artifact_id=trace_id,
                artifact_type="INTERFACE",
                stage_or_lane="stage-03-contract",
                status="review",
                source_path=relative_to_output(stage_paths["stage_03"], output_dir),
                source_anchor=trace_id.lower(),
                now=now,
            )
            write_trace_link(
                conn,
                project_scope=project_scope,
                from_artifact_id=trace_id,
                to_artifact_id="ARCH-STG03-0001",
                link_type="derived_from",
                source_path=relative_to_output(stage_paths["stage_03"], output_dir),
                evidence_anchor=trace_id.lower(),
                now=now,
            )
            for upstream_id in split_inline_items(str(row.get("upstream_trace_ids", ""))):
                if upstream_id not in upstream_p1_trace_ids:
                    upstream_p1_trace_ids.append(upstream_id)
                write_trace_link(
                    conn,
                    project_scope=project_scope,
                    from_artifact_id=trace_id,
                    to_artifact_id=upstream_id,
                    link_type="depends_on",
                    source_path=relative_to_output(stage_paths["stage_03"], output_dir),
                    evidence_anchor=trace_id.lower(),
                    now=now,
                )
        for upstream_id in upstream_p1_trace_ids:
            write_trace_artifact(
                conn,
                project_scope=project_scope,
                artifact_id=upstream_id,
                artifact_type="REQ",
                stage_or_lane="phase-1-trace",
                status="review",
                source_path=relative_to_output(phase1_prd, output_dir),
                source_anchor=upstream_id.lower(),
                now=now,
            )
            write_trace_link(
                conn,
                project_scope=project_scope,
                from_artifact_id=upstream_id,
                to_artifact_id="P1-PRD-0001",
                link_type="contained_in",
                source_path=relative_to_output(phase1_prd, output_dir),
                evidence_anchor=upstream_id.lower(),
                now=now,
            )
        for artifact_id, artifact_type, stage_or_lane, path, anchor in (
            ("HANDOFF-0001", "HANDOFF", "phase-2-engspec", engineering_spec_pack, "engineering-spec-pack"),
            ("IMPL-STG00-INPUT-0001", "HANDOFF", "implementation-entry", implementation_entry, "phase-3-implementation-entry"),
            ("VERIFY-0001", "VERIFY", "phase-2-report", execution_report, "phase-2-execution-report"),
        ):
            write_trace_artifact(
                conn,
                project_scope=project_scope,
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                stage_or_lane=stage_or_lane,
                status="review",
                source_path=relative_to_output(path, output_dir),
                source_anchor=anchor,
                now=now,
            )
        upstream_stage_ids = [artifact_id for artifact_id, *_ in stage_artifacts[1:]]
        for upstream_id in upstream_stage_ids:
            write_trace_link(
                conn,
                project_scope=project_scope,
                from_artifact_id="HANDOFF-0001",
                to_artifact_id=upstream_id,
                link_type="depends_on",
                source_path=relative_to_output(engineering_spec_pack, output_dir),
                evidence_anchor="engineering-spec-pack",
                now=now,
            )
            write_trace_link(
                conn,
                project_scope=project_scope,
                from_artifact_id="VERIFY-0001",
                to_artifact_id=upstream_id,
                link_type="depends_on",
                source_path=relative_to_output(execution_report, output_dir),
                evidence_anchor="phase-2-execution-report",
                now=now,
            )
        write_trace_link(
            conn,
            project_scope=project_scope,
            from_artifact_id="IMPL-STG00-INPUT-0001",
            to_artifact_id="HANDOFF-0001",
            link_type="depends_on",
            source_path=relative_to_output(implementation_entry, output_dir),
            evidence_anchor="phase-3-implementation-entry",
            now=now,
        )
        write_trace_link(
            conn,
            project_scope=project_scope,
            from_artifact_id="HANDOFF-0001",
            to_artifact_id="P1-PRD-0001",
            link_type="depends_on",
            source_path=relative_to_output(engineering_spec_pack, output_dir),
            evidence_anchor="engineering-spec-pack",
            now=now,
        )
        conn.commit()
        artifact_count = conn.execute(
            "SELECT COUNT(*) FROM artifacts WHERE project_scope = ?",
            (project_scope,),
        ).fetchone()[0]
        link_count = conn.execute(
            "SELECT COUNT(*) FROM links WHERE project_scope = ?",
            (project_scope,),
        ).fetchone()[0]
    finally:
        conn.close()
    return {
        "status": "written",
        "registry_db_path": str(db_path),
        "trace_registry_root": str(db_path.parent),
        "project_key": project_key,
        "project_scope": project_scope,
        "schema_version": TRACE_SCHEMA_VERSION,
        "artifact_count": artifact_count,
        "link_count": link_count,
    }


def write_engineering_spec_pack(
    *,
    output_path: Path,
    case_name: str,
    version: str,
    profile: str,
    owner: str,
    phase1_prd: Path,
    stage_paths: dict[str, Path],
    optional_stage_02_5: Path | None,
    output_locale: str,
) -> None:
    stage_sections = []
    for label, path in stage_paths.items():
        stage_sections.append(f"## {label.replace('_', '-').upper()} - {path.name}\n\n{read_text(path).strip()}")
    if optional_stage_02_5 and optional_stage_02_5.exists():
        stage_sections.insert(2, f"## STAGE-02.5 - {optional_stage_02_5.name}\n\n{read_text(optional_stage_02_5).strip()}")
    stage_03_text = read_text(stage_paths["stage_03"])
    contract_compatibility_summary = phase3_contract_compatibility_summary(stage_03_text)

    text = f"""# Engineering Spec Pack

## 1. Intake Metadata
- case_name: `{case_name}`
- report_version: `{version}`
- delivery_profile: `{profile}`
- run_owner: `{owner}`
- upstream_phase1_prd: `{phase1_prd}`
- output_locale: `{output_locale}`
- closure_runtime: `phase2_closure_runtime.py`

## 2. Phase-3 Quick Start
- Read this file first, then `phase-3-implementation-entry.md`.
- Preserve the public boundaries, ownership decisions, interface contracts, data model, and implementation handoff declared in Stage-01 through Stage-04.
- Treat review-bound or missing items as blockers for implementation claims, not as completed truth.

## 3. Source Stage Index
- stage_01: `{relative_name(stage_paths["stage_01"])}`
- stage_02: `{relative_name(stage_paths["stage_02"])}`
- stage_02_5: `{relative_name(optional_stage_02_5)}`
- stage_03: `{relative_name(stage_paths["stage_03"])}`
- stage_04: `{relative_name(stage_paths["stage_04"])}`

{contract_compatibility_summary}

{chr(10).join(stage_sections)}
"""
    output_path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_phase3_entry(
    *,
    output_path: Path,
    case_name: str,
    version: str,
    engineering_spec_pack: Path,
    execution_report: Path,
    stage_paths: dict[str, Path],
    optional_stage_02_5: Path | None,
    formal_state: str,
    compact_closure_formal_state: str,
) -> None:
    text = f"""# Phase-3 Implementation Entry

## 1. Intake Metadata
- case_name: `{case_name}`
- source_phase: `Phase-2`
- report_version: `{version}`
- strongest_supported_readiness_label: `{formal_state}`
- compact_closure_formal_state: `{compact_closure_formal_state}`
- closure_runtime: `phase2_closure_runtime.py`

## 2. Required Upstream Inputs
- engineering_spec_pack: `{engineering_spec_pack.name}`
- phase_2_execution_report: `{execution_report.name}`
- stage_01: `{relative_name(stage_paths["stage_01"])}`
- stage_02: `{relative_name(stage_paths["stage_02"])}`
- stage_02_5: `{relative_name(optional_stage_02_5)}`
- stage_03: `{relative_name(stage_paths["stage_03"])}`
- stage_04: `{relative_name(stage_paths["stage_04"])}`

## 3. Implementation Intake Rule
- may_start: `{"yes" if formal_state != "blocked" else "no"}`
- may_rely_on:
  - public-boundary contracts and ownership statements in `engineering-spec-pack.md`
  - explicit Stage-03 interface/data contracts
  - explicit Stage-04 handoff and review-bound items
- must_not_assume:
  - review-bound items are resolved
  - production approval, UAT, budget approval, or owner sign-off has happened
  - the compact closure runtime replaces release-proof validation

## 4. Start Sequence
1. Read `{engineering_spec_pack.name}`.
2. Review `{execution_report.name}` for claim ceilings and missing stages.
3. Translate Stage-04 implementation handoff into P3 task cards.
4. Keep unresolved gaps visible in P3 evidence.
"""
    output_path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_execution_report(
    *,
    output_path: Path,
    case_name: str,
    version: str,
    profile: str,
    owner: str,
    phase1_prd: Path,
    stage_paths: dict[str, Path],
    optional_stage_02_5: Path | None,
    missing_stages: list[str],
    formal_state: str,
    compact_closure_formal_state: str,
    complexity_profile: str,
    complexity_override_justification: str,
    deployment_posture: str,
    deployment_posture_suggested: str,
    deployment_posture_warning_class: str,
    deployment_posture_override_source: str,
    deployment_posture_override_reason: str,
    deployment_posture_added_risks: str,
) -> None:
    stage_rows = "\n".join(
        f"| `{key}` | `{path.name}` | `{'present' if path.exists() else 'missing'}` | {first_heading(read_text(path))} |"
        for key, path in stage_paths.items()
    )
    optional_status = "present" if optional_stage_02_5 and optional_stage_02_5.exists() else "not-present"
    missing_text = "\n".join(f"- `{name}`" for name in missing_stages) if missing_stages else "- none"
    text = f"""# Phase-2 Execution Report

## 1. Runtime Metadata
- case_name: `{case_name}`
- report_version: `{version}`
- profile: `{profile}`
- run_owner: `{owner}`
- closure_runtime: `phase2_closure_runtime.py`
- generated_at: `{utc_now_iso()}`
- upstream_phase1_prd: `{phase1_prd}`
- complexity_profile: `{complexity_profile}`
- complexity_override_justification: `{complexity_override_justification or 'none'}`

## 2. Closure Result
- recommended_formal_state: `{formal_state}`
- compact_closure_formal_state: `{compact_closure_formal_state}`
- claim_ceiling: compact P2 closure evidence for freshly authored Stage outputs; not release proof.
- missing_required_stages:
{missing_text}
- optional_stage_02_5: `{optional_status}`

## 3. Deployment Posture Context
- deployment_posture_selected: `{deployment_posture}`
- deployment_posture_suggested: `{deployment_posture_suggested}`
- deployment_posture_warning_class: `{deployment_posture_warning_class}`
- deployment_posture_override_source: `{deployment_posture_override_source or 'none'}`
- deployment_posture_override_reason: `{deployment_posture_override_reason or 'none'}`
- deployment_posture_added_risks: `{deployment_posture_added_risks or 'none'}`
- deployment posture override warning: `{deployment_posture_warning_class != 'none' or bool(deployment_posture_override_reason)}`

## 4. Stage Inventory
| stage | file | status | first_heading |
|---|---|---|---|
{stage_rows}
"""
    output_path.write_text(text.rstrip() + "\n", encoding="utf-8")


def build_compact_mainline_assessment(
    *,
    case_name: str,
    version: str,
    missing_stages: list[str],
    formal_state: str,
    handoff_state: str,
) -> dict[str, Any]:
    stage_status = "BLOCKED" if missing_stages else "PASS"
    readiness_status = "BLOCKED" if handoff_state == "blocked" else "PASS"
    claim_ceiling_status = "REVIEW-BOUND" if readiness_status == "PASS" else "BLOCKED"
    acceptance_rows = [
        {
            "key": "required_stage_files_present",
            "label": "Required Stage files present",
            "status": stage_status,
            "why": "all required Stage-01 through Stage-04 files are present"
            if not missing_stages
            else "missing required stages: " + ", ".join(missing_stages),
        },
        {
            "key": "handoff_surfaces_written",
            "label": "P2 to P3 handoff surfaces written",
            "status": stage_status,
            "why": "engineering spec pack, execution report, and implementation entry were written"
            if not missing_stages
            else "handoff surfaces are not safe while required stage files are missing",
        },
        {
            "key": "implementation_handoff_allowed",
            "label": "Implementation handoff allowed",
            "status": readiness_status,
            "why": "compact closure allows P3 planning to start while preserving unresolved review-bound items"
            if readiness_status == "PASS"
            else "compact closure blocks P3 planning until required stages exist",
        },
        {
            "key": "compact_claim_ceiling_preserved",
            "label": "Compact closure claim ceiling preserved",
            "status": claim_ceiling_status,
            "why": "this verdict proves handoff completeness only; it is not a full Phase-2 quality or release-proof score",
        },
    ]
    blockers_count = sum(1 for row in acceptance_rows if row["status"] == "BLOCKED")
    review_bound_items_count = sum(1 for row in acceptance_rows if row["status"] == "REVIEW-BOUND")
    return {
        "phase": "P2",
        "case_name": case_name,
        "version": version,
        "generated_at": utc_now_iso(),
        "closure_runtime": "phase2_closure_runtime.py",
        "overall_quality_gate": "pass" if blockers_count == 0 else "fail",
        "verdict": "PASS" if blockers_count == 0 else "BLOCKED",
        "recommended_formal_state": handoff_state,
        "compact_closure_formal_state": formal_state,
        "quality_score_claim": "not-scored",
        "total_score": None,
        "claim_ceiling": "compact P2 closure evidence for freshly authored Stage outputs; not release proof.",
        "missing_required_stages": missing_stages,
        "blockers_count": blockers_count,
        "review_bound_items_count": review_bound_items_count,
        "acceptance_rows": acceptance_rows,
    }


def write_compact_scorecard(output_path: Path, assessment: dict[str, Any]) -> None:
    total_score = assessment["total_score"] if assessment["total_score"] is not None else "not-scored"
    lines = [
        "# Phase-2 Mainline Scorecard",
        "",
        f"- verdict: `{assessment['verdict']}`",
        f"- recommended_formal_state: `{assessment['recommended_formal_state']}`",
        f"- compact_closure_formal_state: `{assessment['compact_closure_formal_state']}`",
        f"- total_score: `{total_score}`",
        f"- claim_ceiling: {assessment['claim_ceiling']}",
        f"- closure_runtime: `{assessment['closure_runtime']}`",
        "",
        "| Dimension | Status | Notes |",
        "|---|---|---|",
    ]
    for row in assessment["acceptance_rows"]:
        lines.append(f"| {row['label']} | `{row['status']}` | {row['why']} |")
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_compact_acceptance_matrix(output_path: Path, assessment: dict[str, Any]) -> None:
    lines = [
        "# Phase-2 Acceptance Matrix",
        "",
        f"- verdict: `{assessment['verdict']}`",
        f"- recommended_formal_state: `{assessment['recommended_formal_state']}`",
        f"- compact_closure_formal_state: `{assessment['compact_closure_formal_state']}`",
        "",
        "| Acceptance Item | Status | Why |",
        "|---|---|---|",
    ]
    for row in assessment["acceptance_rows"]:
        lines.append(f"| {row['label']} | `{row['status']}` | {row['why']} |")
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_compact_mainline_artifacts(output_dir: Path, assessment: dict[str, Any]) -> dict[str, str]:
    verdict_path = output_dir / "phase-verdict.json"
    scorecard_path = output_dir / "phase-mainline-scorecard.md"
    acceptance_matrix_path = output_dir / "phase-acceptance-matrix.md"
    write_json(verdict_path, assessment)
    write_compact_scorecard(scorecard_path, assessment)
    write_compact_acceptance_matrix(acceptance_matrix_path, assessment)
    return {
        "phase_verdict": str(verdict_path),
        "phase_mainline_scorecard": str(scorecard_path),
        "phase_acceptance_matrix": str(acceptance_matrix_path),
    }


def run_closure(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stage_paths = {
        "stage_01": resolve_stage_path(output_dir, args.stage_01, STAGE_DEFAULTS["stage_01"]),
        "stage_02": resolve_stage_path(output_dir, args.stage_02, STAGE_DEFAULTS["stage_02"]),
        "stage_03": resolve_stage_path(output_dir, args.stage_03, STAGE_DEFAULTS["stage_03"]),
        "stage_04": resolve_stage_path(output_dir, args.stage_04, STAGE_DEFAULTS["stage_04"]),
    }
    optional_stage_02_5 = resolve_optional_stage_path(output_dir, args.stage_02_5)
    missing_stages = missing_required_stages(stage_paths)
    formal_state = "blocked" if missing_stages else "review-bound"
    handoff_state = compact_handoff_state(missing_stages)
    case_name = derive_case_name(output_dir, args.case_name)
    output_locale = resolve_output_locale(args.output_locale)
    phase1_prd = Path(args.phase1_prd).resolve()

    engineering_spec_pack = output_dir / "engineering-spec-pack.md"
    implementation_entry = output_dir / "phase-3-implementation-entry.md"
    execution_report = output_dir / "phase-2-execution-report.md"
    bridge_surfaces = write_compact_cross_phase_bridge_surfaces(
        output_dir=output_dir,
        phase1_prd=phase1_prd,
        stage_03=stage_paths["stage_03"],
    )

    write_engineering_spec_pack(
        output_path=engineering_spec_pack,
        case_name=case_name,
        version=args.version,
        profile=args.profile,
        owner=args.owner,
        phase1_prd=phase1_prd,
        stage_paths=stage_paths,
        optional_stage_02_5=optional_stage_02_5,
        output_locale=output_locale,
    )
    write_phase3_entry(
        output_path=implementation_entry,
        case_name=case_name,
        version=args.version,
        engineering_spec_pack=engineering_spec_pack,
        execution_report=execution_report,
        stage_paths=stage_paths,
        optional_stage_02_5=optional_stage_02_5,
        formal_state=handoff_state,
        compact_closure_formal_state=formal_state,
    )
    write_execution_report(
        output_path=execution_report,
        case_name=case_name,
        version=args.version,
        profile=args.profile,
        owner=args.owner,
        phase1_prd=phase1_prd,
        stage_paths=stage_paths,
        optional_stage_02_5=optional_stage_02_5,
        missing_stages=missing_stages,
        formal_state=handoff_state,
        compact_closure_formal_state=formal_state,
        complexity_profile=args.complexity_profile,
        complexity_override_justification=args.complexity_override_justification,
        deployment_posture=args.deployment_posture,
        deployment_posture_suggested=args.deployment_posture_suggested,
        deployment_posture_warning_class=args.deployment_posture_warning_class,
        deployment_posture_override_source=args.deployment_posture_override_source,
        deployment_posture_override_reason=args.deployment_posture_override_reason,
        deployment_posture_added_risks=args.deployment_posture_added_risks,
    )
    trace_identity_source = write_compact_trace_identity_source(
        output_dir=output_dir,
        case_name=case_name,
        phase1_prd=phase1_prd,
        stage_paths=stage_paths,
        optional_stage_02_5=optional_stage_02_5,
        engineering_spec_pack=engineering_spec_pack,
        implementation_entry=implementation_entry,
        execution_report=execution_report,
    )
    assessment = build_compact_mainline_assessment(
        case_name=case_name,
        version=args.version,
        missing_stages=missing_stages,
        formal_state=formal_state,
        handoff_state=handoff_state,
    )
    mainline_artifacts = write_compact_mainline_artifacts(output_dir, assessment)
    report = {
        "closure_runtime": "phase2_closure_runtime.py",
        "case_name": case_name,
        "formal_state": formal_state,
        "handoff_readiness_state": handoff_state,
        "missing_required_stages": missing_stages,
        "runtime_context": {
            "complexity_profile": args.complexity_profile,
            "deployment_posture": args.deployment_posture,
            "deployment_posture_suggested": args.deployment_posture_suggested,
            "deployment_posture_warning_class": args.deployment_posture_warning_class,
        },
        "outputs": {
            "engineering_spec_pack": str(engineering_spec_pack),
            "phase3_implementation_entry": str(implementation_entry),
            "execution_report": str(execution_report),
        },
        "mainline_artifacts": mainline_artifacts,
        "cross_phase_bridge_surfaces": bridge_surfaces,
        "trace_identity_source": trace_identity_source,
    }
    write_json(output_dir / ".phase2-diagnostics" / "phase2-closure-runtime-report.json", report)
    emit_review_surface(output_dir, "phase2")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 2 if missing_stages else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run compact Phase-2 closure over fresh authored Stage outputs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "validation profile: phase-runtime; default status: compact default closure; "
            "claim ceiling: P2 handoff surfaces only, not release proof."
        ),
    )
    parser.add_argument("--phase1-prd", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--profile", default="implementation-planning-ready-design-package")
    parser.add_argument("--complexity-profile", default="auto")
    parser.add_argument("--complexity-override-justification", default="")
    parser.add_argument("--deployment-posture", default="light")
    parser.add_argument("--deployment-posture-suggested", default="light")
    parser.add_argument("--deployment-posture-warning-class", default="none")
    parser.add_argument("--deployment-posture-override-source", default="")
    parser.add_argument("--deployment-posture-override-reason", default="")
    parser.add_argument("--deployment-posture-added-risks", default="")
    parser.add_argument("--owner", default="Codex Phase-2 closure runtime")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    parser.add_argument("--case-name", default="")
    parser.add_argument("--stage-01", default="")
    parser.add_argument("--stage-02", default="")
    parser.add_argument("--stage-02-5", default="")
    parser.add_argument("--stage-03", default="")
    parser.add_argument("--stage-04", default="")
    parser.add_argument("--thinking-value-gain-mode", default="off")
    parser.add_argument("--thinking-value-gain-output-profile", default="coverage_rich")
    parser.add_argument("--existing-system-architecture-change-intake", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_closure(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
