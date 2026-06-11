#!/usr/bin/env python3
"""Stage-neutral claim-control acceptance runner.

This module is an adapter over the shared Path A/B claim-control contract. It
routes generated artifacts from generic metadata, validates an optional
claim-control sidecar, and makes missing surfaces review-bound instead of
deriving truth from Markdown, Mermaid, tables, trace rows, or prose.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import copy
import hashlib
import json
import re
import sys
from typing import Any


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.claim_control_contract import (  # noqa: E402
    resolve_claim_control_route,
    validate_path_a_surface,
    validate_path_b_surface,
)


HEADING_RE = re.compile(r"^#{1,6}\s+\S", flags=re.MULTILINE)
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", flags=re.MULTILINE)
MERMAID_BLOCK_RE = re.compile(r"```mermaid\b", flags=re.IGNORECASE)
ID_TOKEN_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,8}-[A-Z0-9]{1,8}(?:-[0-9]{1,4})?\b")
LEGACY_ID_TOKEN_RE = re.compile(r"\b(?:REQ|AC|FLOW|STATE|UC|CMP)-[0-9]{1,4}\b", flags=re.IGNORECASE)


def _read_text_if_possible(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _claim_surface_hash(surface: dict[str, Any]) -> str:
    payload = copy.deepcopy(surface)
    render_refs = payload.get("render_refs")
    if not isinstance(render_refs, dict):
        render_refs = {}
        payload["render_refs"] = render_refs
    render_refs["claim_surface_hash"] = ""
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _artifact_id(path: Path) -> str:
    return path.stem.strip() or path.name.strip()


def _estimate_claim_count(text: str) -> int:
    refs = set(ID_TOKEN_RE.findall(text)) | {item.upper() for item in LEGACY_ID_TOKEN_RE.findall(text)}
    return len(refs)


def infer_artifact_metadata(artifact_path: str | Path, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Infer route metadata from a rendered artifact without extracting truth.

    The inferred counts are only routing hints. They are not accepted claims and
    must not be used as a claim index or repair input.
    """

    path = Path(artifact_path)
    text = _read_text_if_possible(path) if path.exists() else ""
    has_mermaid = bool(MERMAID_BLOCK_RE.search(text))
    has_tables = bool(TABLE_SEPARATOR_RE.search(text))
    heading_count = len(HEADING_RE.findall(text))
    has_prose_sections = heading_count > 1 or len([line for line in text.splitlines() if line.strip()]) > 8
    view_count = 0
    view_count += 1 if has_prose_sections or text.strip() else 0
    view_count += 1 if has_mermaid else 0
    view_count += 1 if has_tables else 0
    metadata = {
        "artifact_id": _artifact_id(path),
        "source_count": 1,
        "view_count": view_count,
        "claim_count": _estimate_claim_count(text),
        "has_mermaid": has_mermaid,
        "has_tables": has_tables,
        "has_prose_sections": has_prose_sections,
        "inference_policy": "routing-hints-only-not-claim-truth",
    }
    if overrides:
        for key, value in overrides.items():
            if value is not None:
                metadata[key] = value
    return metadata


def default_surface_path(artifact_path: str | Path) -> Path:
    path = Path(artifact_path)
    return path.with_name(f"{path.stem}.claim-control.json")


def load_claim_control_surface(surface_path: str | Path | None) -> dict[str, Any] | None:
    if not surface_path:
        return None
    path = Path(surface_path)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"claim-control surface must be a JSON object: {path}")
    return payload


def _metadata_from_surface(surface: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    metadata = surface.get("artifact_metadata")
    if isinstance(metadata, dict):
        merged = dict(fallback)
        merged.update(metadata)
        return merged
    return fallback


def _missing_surface_report(
    *,
    artifact_path: Path,
    surface_path: Path,
    metadata: dict[str, Any],
    route_decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_kind": "claim-control-acceptance-report",
        "artifact_path": str(artifact_path),
        "surface_path": str(surface_path),
        "overall_status": "review_bound",
        "claim_ceiling": "review-bound:missing-claim-control-surface",
        "classifications": ["claim_control_surface_missing"],
        "route_decision": route_decision,
        "metadata": metadata,
        "mechanism_report": None,
        "creates_claims": False,
        "uses_rendered_views_as_truth": False,
        "policy": "missing claim-control surfaces cap authority; rendered artifacts are evidence views only",
    }


def _invalid_surface_report(
    *,
    artifact_path: Path,
    surface_path: Path,
    metadata: dict[str, Any],
    route_decision: dict[str, Any],
    mechanism_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_kind": "claim-control-acceptance-report",
        "artifact_path": str(artifact_path),
        "surface_path": str(surface_path),
        "overall_status": "blocked",
        "claim_ceiling": "blocked:claim-control-surface-invalid",
        "classifications": list(mechanism_report.get("classifications", [])),
        "route_decision": route_decision,
        "metadata": metadata,
        "mechanism_report": mechanism_report,
        "creates_claims": False,
        "uses_rendered_views_as_truth": False,
        "policy": "claim-control surface exists but failed the selected shared contract",
    }


def _passing_surface_report(
    *,
    artifact_path: Path,
    surface_path: Path,
    metadata: dict[str, Any],
    route_decision: dict[str, Any],
    mechanism_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_kind": "claim-control-acceptance-report",
        "artifact_path": str(artifact_path),
        "surface_path": str(surface_path),
        "overall_status": "pass",
        "claim_ceiling": "claim-controlled",
        "classifications": [],
        "route_decision": route_decision,
        "metadata": metadata,
        "mechanism_report": mechanism_report,
        "creates_claims": False,
        "uses_rendered_views_as_truth": False,
        "policy": "selected shared claim-control contract passed",
    }


def _claim_ref_is_rendered(text: str, claim_ref: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9_-]){re.escape(claim_ref)}(?![A-Za-z0-9_-])"
    return bool(re.search(pattern, text))


def _with_blocking_classification(
    mechanism_report: dict[str, Any],
    *,
    classification: str,
    checks: dict[str, Any],
) -> dict[str, Any]:
    classifications = sorted(set(list(mechanism_report.get("classifications", [])) + [classification]))
    merged_checks = dict(mechanism_report.get("checks", {}))
    merged_checks.update(checks)
    return {
        **mechanism_report,
        "overall_status": "blocked",
        "classifications": classifications,
        "checks": merged_checks,
    }


def _render_refs_surface(surface: dict[str, Any]) -> dict[str, Any]:
    render_refs = surface.get("render_refs")
    return render_refs if isinstance(render_refs, dict) else {}


def _accepted_claims_by_id(surface: dict[str, Any]) -> dict[str, dict[str, Any]]:
    claim_index = surface.get("claim_index")
    rows = claim_index.get("claims") if isinstance(claim_index, dict) else []
    claims: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return claims
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or "accepted").strip() != "accepted":
            continue
        claim_id = str(row.get("id") or "").strip()
        if claim_id:
            claims[claim_id] = row
    return claims


def _normalized_source_refs(row: dict[str, Any]) -> list[str]:
    refs = row.get("source_refs")
    if isinstance(refs, str):
        return [refs.strip()] if refs.strip() else []
    if not isinstance(refs, list):
        return []
    return sorted(str(item).strip() for item in refs if str(item).strip())


def _surface_requires_upstream_claim_control(surface: dict[str, Any]) -> bool:
    metadata = surface.get("artifact_metadata")
    if not isinstance(metadata, dict):
        return False
    return str(metadata.get("claim_lineage_mode") or "").strip() == "upstream-claim-control"


def _surface_requires_structured_claim_realization(surface: dict[str, Any]) -> bool:
    metadata = surface.get("artifact_metadata")
    if not isinstance(metadata, dict):
        return False
    return str(metadata.get("claim_realization_mode") or "").strip() == "agentic-structured"


def _enforce_artifact_hash(
    *,
    artifact_path: Path,
    surface: dict[str, Any],
    mechanism_report: dict[str, Any],
) -> dict[str, Any]:
    render_refs = _render_refs_surface(surface)
    expected_hash = str(render_refs.get("artifact_hash") or "").strip()
    actual_hash = _sha256_file(artifact_path) if artifact_path.exists() else ""
    status = "match" if expected_hash and expected_hash == actual_hash else "missing" if not expected_hash else "mismatch"
    checks = {
        "artifact_hash_expected": expected_hash,
        "artifact_hash_actual": actual_hash,
        "artifact_hash_status": status,
    }
    if status == "match":
        merged_checks = dict(mechanism_report.get("checks", {}))
        merged_checks.update(checks)
        return {**mechanism_report, "checks": merged_checks}
    return _with_blocking_classification(
        mechanism_report,
        classification="artifact_hash_missing" if status == "missing" else "artifact_hash_mismatch",
        checks=checks,
    )


def _enforce_claim_surface_hash(
    *,
    surface: dict[str, Any],
    mechanism_report: dict[str, Any],
) -> dict[str, Any]:
    render_refs = _render_refs_surface(surface)
    expected_hash = str(render_refs.get("claim_surface_hash") or "").strip()
    actual_hash = _claim_surface_hash(surface)
    status = "match" if expected_hash and expected_hash == actual_hash else "missing" if not expected_hash else "mismatch"
    checks = {
        "claim_surface_hash_expected": expected_hash,
        "claim_surface_hash_actual": actual_hash,
        "claim_surface_hash_status": status,
    }
    if status == "match":
        merged_checks = dict(mechanism_report.get("checks", {}))
        merged_checks.update(checks)
        return {**mechanism_report, "checks": merged_checks}
    return _with_blocking_classification(
        mechanism_report,
        classification="claim_surface_hash_missing" if status == "missing" else "claim_surface_hash_mismatch",
        checks=checks,
    )


def _load_surface_if_possible(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _upstream_surface_paths(surface: dict[str, Any]) -> tuple[list[str], str]:
    render_refs = _render_refs_surface(surface)
    raw_paths = render_refs.get("upstream_surface_paths")
    if raw_paths is None:
        return [], "missing"
    if not isinstance(raw_paths, list):
        return [], "malformed"
    return [str(item).strip() for item in raw_paths if str(item).strip()], "ok"


def _accepted_upstream_surfaces(
    surface: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, str], list[str], list[str], list[str]]:
    upstream_paths, _ = _upstream_surface_paths(surface)
    upstream_claims_by_id: dict[str, dict[str, Any]] = {}
    upstream_claim_paths_by_id: dict[str, str] = {}
    invalid_paths: list[str] = []
    missing_surfaces: list[str] = []
    hash_mismatches: list[str] = []

    for raw_path in upstream_paths:
        upstream_path = Path(raw_path)
        if not upstream_path.name.endswith(".claim-control.json"):
            invalid_paths.append(raw_path)
            continue
        upstream_surface = _load_surface_if_possible(upstream_path)
        if upstream_surface is None:
            missing_surfaces.append(raw_path)
            continue
        expected_hash = str(_render_refs_surface(upstream_surface).get("claim_surface_hash") or "").strip()
        actual_hash = _claim_surface_hash(upstream_surface)
        if not expected_hash or expected_hash != actual_hash:
            hash_mismatches.append(raw_path)
            continue
        for claim_id, claim in _accepted_claims_by_id(upstream_surface).items():
            upstream_claims_by_id.setdefault(claim_id, claim)
            upstream_claim_paths_by_id.setdefault(claim_id, raw_path)
    return upstream_claims_by_id, upstream_claim_paths_by_id, invalid_paths, missing_surfaces, hash_mismatches


def _current_evidence_claim_refs(mechanism_report: dict[str, Any]) -> list[str]:
    checks = mechanism_report.get("checks")
    if not isinstance(checks, dict):
        return []
    refs = checks.get("evidence_ledger_claim_refs")
    if isinstance(refs, list):
        return sorted(str(ref).strip() for ref in refs if str(ref).strip())
    return []


def _current_evidence_source_claim_refs(mechanism_report: dict[str, Any]) -> list[str]:
    checks = mechanism_report.get("checks")
    if not isinstance(checks, dict):
        return []
    refs = checks.get("evidence_source_claim_refs")
    if isinstance(refs, list):
        return sorted(str(ref).strip() for ref in refs if str(ref).strip())
    return []


def _render_ref_block_claim_map(mechanism_report: dict[str, Any]) -> dict[tuple[str, str], set[str]]:
    checks = mechanism_report.get("checks")
    if not isinstance(checks, dict):
        return {}
    entries = checks.get("evidence_ledger_entries")
    if not isinstance(entries, list):
        return {}
    result: dict[tuple[str, str], set[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        block_id = str(entry.get("block_id") or "").strip()
        view_id = str(entry.get("view_id") or "").strip()
        if not block_id or not view_id:
            continue
        refs = {
            str(ref).strip()
            for ref in entry.get("rendered_claim_refs", [])
            if str(ref).strip()
        }
        result[(block_id, view_id)] = refs
    return result


def _claim_realization_items(surface: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    payload = surface.get("claim_realizations")
    if payload is None:
        return [], "missing"
    if not isinstance(payload, dict):
        return [], "malformed"
    items = payload.get("items")
    if not isinstance(items, list):
        return [], "malformed"
    return [item for item in items if isinstance(item, dict)], "ok"


def _relation_items(surface: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    payload = surface.get("relations")
    if payload is None:
        return [], "missing"
    if not isinstance(payload, dict):
        return [], "malformed"
    items = payload.get("items")
    if not isinstance(items, list):
        return [], "malformed"
    return [item for item in items if isinstance(item, dict)], "ok"


def _canonical_name_items(surface: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    payload = surface.get("names")
    if payload is None:
        return [], "missing"
    if not isinstance(payload, dict):
        return [], "malformed"
    items = payload.get("items")
    if not isinstance(items, list):
        return [], "malformed"
    return [item for item in items if isinstance(item, dict)], "ok"


def _coverage_obligation_items(surface: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    payload = surface.get("coverage_obligations")
    if payload is None:
        return [], "missing"
    if not isinstance(payload, dict):
        return [], "malformed"
    items = payload.get("items")
    if not isinstance(items, list):
        return [], "malformed"
    return [item for item in items if isinstance(item, dict)], "ok"


def _render_ref_view_claim_map(mechanism_report: dict[str, Any]) -> dict[str, set[str]]:
    checks = mechanism_report.get("checks")
    if not isinstance(checks, dict):
        return {}
    entries = checks.get("evidence_ledger_entries")
    if not isinstance(entries, list):
        return {}
    result: dict[str, set[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        view_id = str(entry.get("view_id") or "").strip()
        if not view_id:
            continue
        refs = {
            str(ref).strip()
            for ref in entry.get("rendered_claim_refs", [])
            if str(ref).strip()
        }
        result.setdefault(view_id, set()).update(refs)
    return result


def _enforce_coverage_obligations(
    *,
    surface: dict[str, Any],
    mechanism_report: dict[str, Any],
) -> dict[str, Any]:
    items, status = _coverage_obligation_items(surface)
    accepted_ids = set(_accepted_claims_by_id(surface))
    view_claims = _render_ref_view_claim_map(mechanism_report)
    unknown_claim_refs: set[str] = set()
    malformed_indexes: list[int] = []
    missing_views: list[dict[str, str]] = []
    for index, item in enumerate(items):
        claim_id = str(item.get("claim_id") or "").strip()
        raw_required_view_ids = item.get("required_view_ids")
        required_view_ids = [
            str(view_id).strip()
            for view_id in raw_required_view_ids
            if str(view_id).strip()
        ] if isinstance(raw_required_view_ids, list) else []
        if not claim_id or not isinstance(raw_required_view_ids, list):
            malformed_indexes.append(index)
        if claim_id and claim_id not in accepted_ids:
            unknown_claim_refs.add(claim_id)
        for view_id in required_view_ids:
            if claim_id and claim_id not in view_claims.get(view_id, set()):
                missing_views.append({"claim_id": claim_id, "view_id": view_id})
    missing_views = sorted(missing_views, key=lambda row: (row["claim_id"], row["view_id"]))
    checks = mechanism_report.get("checks") if isinstance(mechanism_report.get("checks"), dict) else {}
    coverage_checks = {
        "coverage_obligation_surface_status": status,
        "coverage_obligation_count": len(items),
        "coverage_obligation_unknown_claim_refs": sorted(unknown_claim_refs),
        "coverage_obligation_malformed_item_indexes": malformed_indexes,
        "coverage_obligation_missing_views": missing_views,
    }
    merged_checks = dict(checks)
    merged_checks.update(coverage_checks)
    updated_report = {**mechanism_report, "checks": merged_checks}
    classifications = list(updated_report.get("classifications", []))
    if status == "malformed":
        classifications.append("coverage_obligation_surface_malformed")
    if malformed_indexes:
        classifications.append("coverage_obligation_item_malformed")
    if unknown_claim_refs:
        classifications.append("coverage_obligation_unknown_claim_ref")
    if missing_views:
        classifications.append("coverage_obligation_missing_view")
    if not classifications:
        return updated_report
    return {
        **updated_report,
        "overall_status": "blocked",
        "classifications": sorted(set(classifications)),
    }


def _enforce_canonical_names(
    *,
    artifact_path: Path,
    surface: dict[str, Any],
    mechanism_report: dict[str, Any],
) -> dict[str, Any]:
    items, status = _canonical_name_items(surface)
    artifact_text = _read_text_if_possible(artifact_path)
    accepted_ids = set(_accepted_claims_by_id(surface))
    unknown_refs: list[str] = []
    malformed_indexes: list[int] = []
    alias_owner: dict[str, str] = {}
    reused_aliases: set[str] = set()
    forbidden_allowed_overlap: set[str] = set()
    duplicate_canonical_values: dict[str, set[str]] = {}
    rendered_forbidden_aliases: list[dict[str, str]] = []
    for index, item in enumerate(items):
        claim_id = str(item.get("id") or "").strip()
        canonical = str(item.get("canonical") or "").strip()
        if not claim_id or not canonical:
            malformed_indexes.append(index)
        if claim_id and claim_id not in accepted_ids:
            unknown_refs.append(claim_id)
        aliases = {
            str(alias).strip()
            for alias in item.get("allowed_aliases", [])
            if str(alias).strip()
        }
        forbidden = {
            str(alias).strip()
            for alias in item.get("forbidden_aliases", [])
            if str(alias).strip()
        }
        for alias in sorted(forbidden):
            if _claim_ref_is_rendered(artifact_text, alias):
                rendered_forbidden_aliases.append({"claim_id": claim_id, "alias": alias})
        forbidden_allowed_overlap.update(aliases & forbidden)
        all_names = {canonical} | aliases
        for alias in all_names:
            owner = alias_owner.get(alias)
            if owner and owner != claim_id:
                reused_aliases.add(alias)
            else:
                alias_owner[alias] = claim_id
        if canonical:
            duplicate_canonical_values.setdefault(canonical, set()).add(claim_id)
    duplicate_canonical_names = sorted(
        canonical for canonical, owners in duplicate_canonical_values.items() if len(owners) > 1
    )
    checks = mechanism_report.get("checks") if isinstance(mechanism_report.get("checks"), dict) else {}
    name_checks = {
        "canonical_name_surface_status": status,
        "canonical_name_count": len(items),
        "canonical_name_unknown_claim_refs": sorted(set(unknown_refs)),
        "canonical_name_malformed_item_indexes": malformed_indexes,
        "canonical_alias_reused": sorted(reused_aliases),
        "canonical_forbidden_allowed_overlap": sorted(forbidden_allowed_overlap),
        "canonical_duplicate_names": duplicate_canonical_names,
        "canonical_forbidden_alias_rendered": sorted(
            rendered_forbidden_aliases,
            key=lambda row: (row["claim_id"], row["alias"]),
        ),
    }
    merged_checks = dict(checks)
    merged_checks.update(name_checks)
    updated_report = {**mechanism_report, "checks": merged_checks}
    classifications = list(updated_report.get("classifications", []))
    if status == "malformed":
        classifications.append("canonical_name_surface_malformed")
    if malformed_indexes:
        classifications.append("canonical_name_item_malformed")
    if unknown_refs:
        classifications.append("canonical_name_unknown_claim_ref")
    if reused_aliases:
        classifications.append("canonical_alias_reused")
    if forbidden_allowed_overlap:
        classifications.append("canonical_alias_forbidden_and_allowed")
    if duplicate_canonical_names:
        classifications.append("canonical_name_reused")
    if rendered_forbidden_aliases:
        classifications.append("canonical_forbidden_alias_rendered")
    if not classifications:
        return updated_report
    return {
        **updated_report,
        "overall_status": "blocked",
        "classifications": sorted(set(classifications)),
    }


def _enforce_relations(
    *,
    surface: dict[str, Any],
    mechanism_report: dict[str, Any],
) -> dict[str, Any]:
    items, status = _relation_items(surface)
    accepted_ids = set(_accepted_claims_by_id(surface))
    endpoint_refs: list[str] = []
    source_refs: list[str] = []
    malformed_indexes: list[int] = []
    for index, item in enumerate(items):
        subject = str(item.get("subject") or "").strip()
        predicate = str(item.get("predicate") or "").strip()
        object_ref = str(item.get("object") or "").strip()
        if not subject or not predicate or not object_ref:
            malformed_indexes.append(index)
        endpoint_refs.extend(ref for ref in [subject, object_ref] if ref)
        source_refs.extend(str(ref).strip() for ref in item.get("source_claim_refs", []) if str(ref).strip())
    unknown_endpoint_refs = sorted(set(endpoint_refs) - accepted_ids)
    unknown_source_refs = sorted(set(source_refs) - accepted_ids)
    checks = mechanism_report.get("checks") if isinstance(mechanism_report.get("checks"), dict) else {}
    relation_checks = {
        "relation_surface_status": status,
        "relation_count": len(items),
        "relation_endpoint_refs": sorted(set(endpoint_refs)),
        "relation_source_claim_refs": sorted(set(source_refs)),
        "relation_unknown_endpoint_refs": unknown_endpoint_refs,
        "relation_unknown_source_claim_refs": unknown_source_refs,
        "relation_malformed_item_indexes": malformed_indexes,
    }
    merged_checks = dict(checks)
    merged_checks.update(relation_checks)
    updated_report = {**mechanism_report, "checks": merged_checks}
    classifications = list(updated_report.get("classifications", []))
    if status == "malformed":
        classifications.append("relation_surface_malformed")
    if malformed_indexes:
        classifications.append("relation_item_malformed")
    if unknown_endpoint_refs:
        classifications.append("relation_unknown_endpoint_ref")
    if unknown_source_refs:
        classifications.append("relation_unknown_source_claim_ref")
    if not classifications:
        return updated_report
    return {
        **updated_report,
        "overall_status": "blocked",
        "classifications": sorted(set(classifications)),
    }


def _enforce_claim_realizations(
    *,
    surface: dict[str, Any],
    mechanism_report: dict[str, Any],
) -> dict[str, Any]:
    requires_realizations = _surface_requires_structured_claim_realization(surface)
    items, status = _claim_realization_items(surface)
    accepted_claims = _accepted_claims_by_id(surface)
    accepted_ids = set(accepted_claims)
    evidence_claim_refs = set(_current_evidence_claim_refs(mechanism_report))
    checks = mechanism_report.get("checks") if isinstance(mechanism_report.get("checks"), dict) else {}
    required_refs = {
        str(ref).strip()
        for ref in checks.get("required_claim_refs", [])
        if str(ref).strip()
    }
    rendered_refs = {
        str(ref).strip()
        for ref in checks.get("rendered_claim_refs", [])
        if str(ref).strip()
    }
    expected_refs = sorted(required_refs | rendered_refs)

    item_claim_refs = sorted(
        str(item.get("claim_id") or "").strip()
        for item in items
        if str(item.get("claim_id") or "").strip()
    )
    unknown_refs = sorted(ref for ref in item_claim_refs if ref not in accepted_ids)
    missing_required_refs = sorted(ref for ref in expected_refs if ref not in set(item_claim_refs))
    unresolved_evidence_refs = sorted(ref for ref in evidence_claim_refs if ref not in set(item_claim_refs))
    render_ref_block_claims = _render_ref_block_claim_map(mechanism_report)
    missing_render_ref_blocks = sorted(
        {
            str(item.get("block_id") or "").strip()
            for item in items
            if str(item.get("block_id") or "").strip()
            and str(item.get("view_id") or "").strip()
            and (str(item.get("block_id") or "").strip(), str(item.get("view_id") or "").strip())
            not in render_ref_block_claims
        }
    )
    refs_not_rendered_by_block = sorted(
        [
            {
                "block_id": str(item.get("block_id") or "").strip(),
                "claim_id": str(item.get("claim_id") or "").strip(),
                "view_id": str(item.get("view_id") or "").strip(),
            }
            for item in items
            if str(item.get("claim_id") or "").strip()
            and str(item.get("block_id") or "").strip()
            and str(item.get("view_id") or "").strip()
            and (str(item.get("block_id") or "").strip(), str(item.get("view_id") or "").strip())
            in render_ref_block_claims
            and str(item.get("claim_id") or "").strip()
            not in render_ref_block_claims[(str(item.get("block_id") or "").strip(), str(item.get("view_id") or "").strip())]
        ],
        key=lambda row: (row["block_id"], row["view_id"], row["claim_id"]),
    )
    items_missing_block_id = sorted(
        str(item.get("claim_id") or "").strip()
        for item in items
        if str(item.get("claim_id") or "").strip() and not str(item.get("block_id") or "").strip()
    )
    items_missing_view_id = sorted(
        str(item.get("claim_id") or "").strip()
        for item in items
        if str(item.get("claim_id") or "").strip() and not str(item.get("view_id") or "").strip()
    )
    items_missing_realization_text = sorted(
        str(item.get("claim_id") or "").strip()
        for item in items
        if str(item.get("claim_id") or "").strip() and not str(item.get("realization_text") or "").strip()
    )

    realization_checks = {
        "claim_realization_status": status,
        "claim_realization_item_claim_refs": item_claim_refs,
        "claim_realization_unknown_claim_refs": unknown_refs,
        "claim_realization_expected_claim_refs": expected_refs,
        "claim_realization_missing_required_claim_refs": missing_required_refs,
        "claim_realization_evidence_refs_unresolved": unresolved_evidence_refs,
        "claim_realization_missing_render_ref_blocks": missing_render_ref_blocks,
        "claim_realization_refs_not_rendered_by_block": refs_not_rendered_by_block,
        "claim_realization_items_missing_block_id": items_missing_block_id,
        "claim_realization_items_missing_view_id": items_missing_view_id,
        "claim_realization_items_missing_realization_text": items_missing_realization_text,
    }
    merged_checks = dict(checks)
    merged_checks.update(realization_checks)
    updated_report = {**mechanism_report, "checks": merged_checks}
    classifications = list(updated_report.get("classifications", []))

    if requires_realizations and status in {"missing", "malformed"}:
        classifications.append(
            "claim_realization_surface_missing" if status == "missing" else "claim_realization_surface_malformed"
        )
    if unknown_refs:
        classifications.append("claim_realization_unknown_claim_ref")
    if requires_realizations and missing_required_refs:
        classifications.append("claim_realization_missing_required_claim")
    if requires_realizations and unresolved_evidence_refs:
        classifications.append("claim_realization_evidence_ref_unresolved")
    if requires_realizations and missing_render_ref_blocks:
        classifications.append("claim_realization_missing_render_ref_block")
    if requires_realizations and refs_not_rendered_by_block:
        classifications.append("claim_realization_not_rendered_by_block")
    if requires_realizations and items_missing_block_id:
        classifications.append("claim_realization_missing_block_id")
    if requires_realizations and items_missing_view_id:
        classifications.append("claim_realization_missing_view_id")
    if requires_realizations and items_missing_realization_text:
        classifications.append("claim_realization_missing_text")
    if not classifications:
        return updated_report
    return {
        **updated_report,
        "overall_status": "blocked",
        "classifications": sorted(set(classifications)),
    }


def _upstream_claim_identity_mismatches(
    surface: dict[str, Any],
    upstream_claims_by_id: dict[str, dict[str, Any]],
    upstream_claim_paths_by_id: dict[str, str],
) -> list[dict[str, str]]:
    current_claims = _accepted_claims_by_id(surface)
    mismatches: list[dict[str, str]] = []

    for claim_id, upstream_claim in sorted(upstream_claims_by_id.items()):
        current_claim = current_claims.get(claim_id)
        if not current_claim:
            continue
        comparisons = {
            "kind": (
                str(current_claim.get("kind") or "").strip(),
                str(upstream_claim.get("kind") or "").strip(),
            ),
            "text": (
                str(current_claim.get("text") or "").strip(),
                str(upstream_claim.get("text") or "").strip(),
            ),
            "source_refs": (
                json.dumps(_normalized_source_refs(current_claim), ensure_ascii=False),
                json.dumps(_normalized_source_refs(upstream_claim), ensure_ascii=False),
            ),
        }
        for field, (current_value, upstream_value) in comparisons.items():
            if current_value != upstream_value:
                mismatches.append(
                    {
                        "claim_id": claim_id,
                        "field": field,
                        "upstream_surface_path": upstream_claim_paths_by_id.get(claim_id, ""),
                    }
                )
    return mismatches


def _enforce_upstream_claim_identity(
    *,
    surface: dict[str, Any],
    surface_path: Path,
    mechanism_report: dict[str, Any],
) -> dict[str, Any]:
    upstream_paths, lineage_status = _upstream_surface_paths(surface)
    (
        upstream_claims_by_id,
        upstream_claim_paths_by_id,
        invalid_paths,
        missing_surfaces,
        hash_mismatches,
    ) = _accepted_upstream_surfaces(surface)
    mismatches = _upstream_claim_identity_mismatches(surface, upstream_claims_by_id, upstream_claim_paths_by_id)
    requires_upstream = _surface_requires_upstream_claim_control(surface)
    evidence_claim_refs = _current_evidence_source_claim_refs(mechanism_report)
    self_reference_paths = [
        path for path in upstream_paths if Path(path).resolve() == surface_path.resolve()
    ]
    unresolved_refs = (
        sorted(ref for ref in evidence_claim_refs if ref not in upstream_claims_by_id)
        if requires_upstream and upstream_claims_by_id and not self_reference_paths
        else []
    )
    checks = {
        "upstream_claim_lineage_status": lineage_status,
        "upstream_claim_surface_paths": upstream_paths,
        "upstream_claim_surface_invalid_paths": invalid_paths,
        "upstream_claim_identity_mismatches": mismatches,
        "upstream_claim_surface_missing": missing_surfaces,
        "upstream_claim_surface_hash_mismatches": hash_mismatches,
        "upstream_claim_lineage_self_references": self_reference_paths,
        "upstream_claim_refs_unresolved": unresolved_refs,
    }
    merged_checks = dict(mechanism_report.get("checks", {}))
    merged_checks.update(checks)
    updated_report = {**mechanism_report, "checks": merged_checks}
    classifications = list(updated_report.get("classifications", []))
    if requires_upstream and lineage_status in {"missing", "malformed"}:
        classifications.append("upstream_claim_lineage_malformed" if lineage_status == "malformed" else "upstream_claim_lineage_missing")
    if requires_upstream and lineage_status == "ok" and not upstream_paths:
        classifications.append("upstream_claim_lineage_missing")
    if requires_upstream and invalid_paths:
        classifications.append("upstream_claim_lineage_invalid_path")
    if self_reference_paths:
        classifications.append("upstream_claim_lineage_self_reference")
    if mismatches:
        classifications.append("upstream_claim_identity_mismatch")
    if missing_surfaces:
        classifications.append("upstream_claim_surface_missing")
    if hash_mismatches:
        classifications.append("upstream_claim_surface_hash_mismatch")
    if unresolved_refs:
        classifications.append("upstream_claim_ref_unresolved")
    if not classifications:
        return updated_report
    return {
        **updated_report,
        "overall_status": "blocked",
        "classifications": sorted(set(classifications)),
    }


def _enforce_rendered_ref_presence(
    *,
    artifact_path: Path,
    mechanism_report: dict[str, Any],
) -> dict[str, Any]:
    """Verify declared rendered refs appear in the rendered artifact text.

    This check does not extract new truth from Markdown.  It only verifies that
    the generator's own `rendered_claim_refs` declaration is backed by the
    rendered artifact it points at.
    """

    checks = dict(mechanism_report.get("checks", {}))
    rendered_refs = [str(ref).strip() for ref in checks.get("rendered_claim_refs", []) if str(ref).strip()]
    if not rendered_refs:
        return mechanism_report

    artifact_text = _read_text_if_possible(artifact_path)
    missing_refs = sorted(ref for ref in rendered_refs if not _claim_ref_is_rendered(artifact_text, ref))
    if not missing_refs:
        checks["rendered_claim_refs_missing_from_artifact"] = []
        return {**mechanism_report, "checks": checks}

    classifications = sorted(
        set(list(mechanism_report.get("classifications", [])) + ["rendered_claim_ref_missing_from_artifact"])
    )
    checks["rendered_claim_refs_missing_from_artifact"] = missing_refs
    return {
        **mechanism_report,
        "overall_status": "blocked",
        "classifications": classifications,
        "checks": checks,
    }


def evaluate_claim_control_acceptance(
    artifact_path: str | Path,
    *,
    surface_path: str | Path | None = None,
    metadata_overrides: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Route and validate one generated artifact through Path A or Path B."""

    artifact = Path(artifact_path)
    selected_surface_path = Path(surface_path) if surface_path else default_surface_path(artifact)
    fallback_metadata = infer_artifact_metadata(artifact, metadata_overrides)
    surface = load_claim_control_surface(selected_surface_path)
    metadata = _metadata_from_surface(surface, fallback_metadata) if surface else fallback_metadata
    route_decision = resolve_claim_control_route(metadata, profile=profile)

    if surface is None:
        return _missing_surface_report(
            artifact_path=artifact,
            surface_path=selected_surface_path,
            metadata=metadata,
            route_decision=route_decision,
        )

    mechanism_report = (
        validate_path_a_surface(surface)
        if route_decision["required_mechanism"] == "validate_path_a_surface"
        else validate_path_b_surface(surface)
    )
    mechanism_report = _enforce_rendered_ref_presence(
        artifact_path=artifact,
        mechanism_report=mechanism_report,
    )
    mechanism_report = _enforce_artifact_hash(
        artifact_path=artifact,
        surface=surface,
        mechanism_report=mechanism_report,
    )
    mechanism_report = _enforce_claim_surface_hash(
        surface=surface,
        mechanism_report=mechanism_report,
    )
    mechanism_report = _enforce_claim_realizations(
        surface=surface,
        mechanism_report=mechanism_report,
    )
    mechanism_report = _enforce_relations(
        surface=surface,
        mechanism_report=mechanism_report,
    )
    mechanism_report = _enforce_canonical_names(
        artifact_path=artifact,
        surface=surface,
        mechanism_report=mechanism_report,
    )
    mechanism_report = _enforce_coverage_obligations(
        surface=surface,
        mechanism_report=mechanism_report,
    )
    mechanism_report = _enforce_upstream_claim_identity(
        surface=surface,
        surface_path=selected_surface_path,
        mechanism_report=mechanism_report,
    )
    if mechanism_report.get("overall_status") != "pass":
        return _invalid_surface_report(
            artifact_path=artifact,
            surface_path=selected_surface_path,
            metadata=metadata,
            route_decision=route_decision,
            mechanism_report=mechanism_report,
        )
    return _passing_surface_report(
        artifact_path=artifact,
        surface_path=selected_surface_path,
        metadata=metadata,
        route_decision=route_decision,
        mechanism_report=mechanism_report,
    )


def render_markdown_report(report: dict[str, Any]) -> str:
    route = report.get("route_decision", {}) if isinstance(report.get("route_decision"), dict) else {}
    classifications = report.get("classifications", []) if isinstance(report.get("classifications"), list) else []
    lines = [
        "# Claim Control Acceptance Report",
        "",
        f"- artifact_path: `{report.get('artifact_path', '')}`",
        f"- surface_path: `{report.get('surface_path', '')}`",
        f"- overall_status: `{report.get('overall_status', '')}`",
        f"- claim_ceiling: `{report.get('claim_ceiling', '')}`",
        f"- route: `{route.get('route', '')}`",
        f"- required_mechanism: `{route.get('required_mechanism', '')}`",
        f"- creates_claims: `{str(report.get('creates_claims', False)).lower()}`",
        f"- uses_rendered_views_as_truth: `{str(report.get('uses_rendered_views_as_truth', False)).lower()}`",
        "",
        "## Classifications",
    ]
    if classifications:
        lines.extend(f"- `{item}`" for item in classifications)
    else:
        lines.append("- none")
    lines.extend(["", "## Policy", "", str(report.get("policy", ""))])
    return "\n".join(lines).rstrip() + "\n"


def _parse_profile(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("--profile-json must decode to a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run generic claim-control acceptance for one generated artifact")
    parser.add_argument("--artifact", required=True, help="Rendered artifact path to route and validate")
    parser.add_argument("--surface", default="", help="Optional claim-control sidecar JSON path")
    parser.add_argument("--output-json", default="", help="Optional JSON report path")
    parser.add_argument("--output-md", default="", help="Optional Markdown report path")
    parser.add_argument("--profile-json", default="", help="Optional route profile JSON object")
    args = parser.parse_args(argv)

    report = evaluate_claim_control_acceptance(
        args.artifact,
        surface_path=args.surface or None,
        profile=_parse_profile(args.profile_json),
    )

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(render_markdown_report(report), encoding="utf-8")
    if not args.output_json and not args.output_md:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
