#!/usr/bin/env python3
"""Read frozen P1 facts into the six P2 input categories without generation.

IDs, values and source ceilings remain those of P1. Missing information becomes
next-version feedback; it never causes regeneration or a business default.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.agentic_decision_authority import canonical_digest
from common.phase_input_slices import source_catalog
from common.semantic_materialization import get_pointer, pointer_token, write_json_exclusive

SCHEMA = "wff.p1-p2-input-projection.v1"
CATEGORIES = ("roles_responsibilities", "tasks_outcomes", "objects_attributes",
              "business_rules", "language_terms", "non_goals")
PROVENANCE_FIELDS = ("truth_state", "claim_ceiling", "source_refs", "backfill_refs",
                     "context_refs", "basis")
NON_GOAL_DISPOSITIONS = {"later-slice", "deferred-seam", "explicit-exclusion"}


class ProjectionError(ValueError):
    """An original input or reference identity could not be established."""


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _strict_source(raw: bytes) -> dict:
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ProjectionError("Duplicate source JSON key: " + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ProjectionError("Non-JSON source number: " + value)

    try:
        source = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as exc:
        raise ProjectionError("P1 source must be strict UTF-8 JSON") from exc
    if not isinstance(source, dict):
        raise ProjectionError("P1 source must be an object")
    if source.get("schema_version") != "wff.p1-agentic-product-authority.v1" or source.get("phase_id") != "P1":
        raise ProjectionError("Unsupported original P1 Authority format")
    if source.get("content_digest") != canonical_digest({k: v for k, v in source.items() if k != "content_digest"}):
        raise ProjectionError("P1 Authority digest differs")
    for key in ("decision_id", "decision_digest"):
        if not isinstance(source.get(key), str) or not source[key]:
            raise ProjectionError("P1 original identity is missing: " + key)
    return source


def _rows(value: Any, path: str, id_field: str | None = None) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ProjectionError("Original collection must contain objects: " + path)
    if id_field:
        identities = [row.get(id_field) for row in value]
        if any(not isinstance(x, str) or not x for x in identities) or len(set(identities)) != len(identities):
            raise ProjectionError("Original IDs are absent or duplicated: " + path)
    return value


def _mapping(value: Any, path: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ProjectionError("Original field must be an object: " + path)
    return value


def project_p1(raw: bytes, *, expected_sha256: str, logical_id: str) -> dict:
    """Project original schema fields, preserving absence, values and row order."""
    actual = hashlib.sha256(raw).hexdigest()
    expected = expected_sha256.removeprefix("sha256:")
    if actual != expected or not isinstance(logical_id, str) or not logical_id:
        raise ProjectionError("Frozen input SHA or logical identity differs")
    source = _strict_source(raw)
    commitments = _rows(source.get("commitments"), "/commitments", "commitment_id")
    features = _rows(source.get("feature_dispositions"), "/feature_dispositions", "feature_id")
    world = _mapping(source.get("product_world_decision"), "/product_world_decision")
    objects = _rows(world.get("objects"), "/product_world_decision/objects", "object_id")
    ownership = _mapping(world.get("ownership"), "/product_world_decision/ownership")
    assignments = _rows(ownership.get("assignments"), "/product_world_decision/ownership/assignments")
    interaction = _mapping(source.get("interaction_relevant_product_context"), "/interaction_relevant_product_context")
    contexts = _rows(interaction.get("task_contexts"), "/interaction_relevant_product_context/task_contexts", "context_id")

    # This is the read adapter's original-value view, not a generated P1 product.
    view = {k: v for k, v in source.items() if k not in
            {"schema_version", "phase_id", "content_digest", "commitments"}}
    view["authority_digest"] = source["content_digest"]
    view["accepted_commitments"] = [row for row in commitments if row.get("status") == "accepted"]
    view["other_commitments"] = [row for row in commitments if row.get("status") != "accepted"]
    catalog = source_catalog(projection=view, document={"logical_id": logical_id,
        "role": "p1-agentic-authority", "data": raw, "sha256": "sha256:" + actual})
    by_pointer = {row["p1_source"]["path"]: row for row in catalog["facts"]}
    identity = {"logical_id": logical_id, "sha256": "sha256:" + actual,
                "authority_schema_version": source["schema_version"],
                "authority_digest": source["content_digest"], "decision_id": source["decision_id"],
                "decision_digest": source["decision_digest"]}
    categories = {category: [] for category in CATEGORIES}
    gaps = []

    def binding(path: str) -> dict:
        value = get_pointer(source, path)
        anchor = path
        while anchor and anchor not in by_pointer:
            anchor = anchor.rsplit("/", 1)[0]
        if anchor:
            fact = by_pointer[anchor]
            if canonical_digest(get_pointer(fact["value"], path[len(anchor):])) != canonical_digest(value):
                raise ProjectionError("Original slice differs at " + path)
            base = fact["p1_source"]
        else:
            base = identity
        return {**base, "path": path, "value_digest": canonical_digest(value)}

    def gap(category: str, code: str, path: str, detail: Any, *, missing_field: str | None = None):
        original = get_pointer(source, path)
        field = "finding_id" if isinstance(original, dict) and original.get("finding_id") else None
        body = {"id": "P1-PROJECTION-GAP-" + canonical_digest(
                    {"input": actual, "category": category, "path": path, "code": code, "field": missing_field}).split(":")[-1][:24],
                "category": category, "code": code, "p1_id": original[field] if field else source["decision_id"],
                "id_pointer": path + "/" + field if field else "/decision_id",
                "source": binding(path), "detail": deepcopy(detail),
                "backport_target": "next-version-P1", "upstream_reconciled": False,
                "claim_ceiling": "Recorded input gap; no new business fact or upstream regeneration."}
        if missing_field is not None:
            body["missing_field"] = missing_field
        gaps.append({**body, "content_digest": canonical_digest(body)})

    def item(category: str, path: str, fields: tuple[str, ...], id_field: str | None):
        row = get_pointer(source, path)
        selected = {key: deepcopy(row[key]) for key in (*fields, *PROVENANCE_FIELDS) if key in row}
        if not any(key in row for key in fields):
            return
        body = {"p1_id": row[id_field] if id_field else source["decision_id"],
                "p1_id_kind": id_field.removesuffix("_id") if id_field else "decision",
                "id_pointer": path + "/" + id_field if id_field else "/decision_id",
                "source": binding(path), "value": selected}
        categories[category].append({**body, "content_digest": canonical_digest(body)})

    for index, row in enumerate(assignments):
        item("roles_responsibilities", f"/product_world_decision/ownership/assignments/{index}",
             ("role", "commitment_ids"), None)
    for index, row in enumerate(commitments):
        if row.get("status") != "accepted":
            continue
        path = f"/commitments/{index}"
        item("business_rules", path, ("kind", "statement", "status", "owner", "feature_ids"), "commitment_id")
        item("roles_responsibilities", path, ("owner",), "commitment_id")
    for index, row in enumerate(contexts):
        path = f"/interaction_relevant_product_context/task_contexts/{index}"
        item("roles_responsibilities", path, ("user_role_or_actor", "task", "commitment_ids"), "context_id")
        item("tasks_outcomes", path, ("task", "business_outcome", "outcome_contract", "commitment_ids",
             "task_frequency", "usage_pattern", "operator_proficiency_or_context", "material_friction",
             "expected_system_memory_or_defaults", "high_frequency_low_step_requirement"), "context_id")
        item("language_terms", path, ("business_vocabulary",), "context_id")
        for key in ("task", "business_outcome"):
            if key not in row or row[key] is None or row[key] == "":
                gap("tasks_outcomes", "missing-field", path, "Original task field is absent or empty.", missing_field=key)
    if "topology" in world:
        item("tasks_outcomes", "/product_world_decision", ("topology",), None)
    for index, row in enumerate(objects):
        path = f"/product_world_decision/objects/{index}"
        item("objects_attributes", path, ("name", "key_attributes", "attributes", "commitment_ids"), "object_id")
        if not any(key in row and row[key] not in (None, "", [], {}) for key in ("key_attributes", "attributes")):
            gap("objects_attributes", "missing-field", path, "No original structured key attributes supplied.",
                missing_field="key_attributes/attributes")
    for index, row in enumerate(features):
        if row.get("disposition") in NON_GOAL_DISPOSITIONS:
            item("non_goals", f"/feature_dispositions/{index}",
                 ("disposition", "statement", "affected_flows", "affected_objects", "owner"), "feature_id")
    item("language_terms", "", ("language", "terminology"), "decision_id")

    def collect_unresolved(value: Any, path: str = ""):
        if isinstance(value, dict):
            for key, child in value.items():
                pointer = path + "/" + pointer_token(key)
                if key in {"unresolved_items", "missing_facts"} and isinstance(child, list):
                    for index, original in enumerate(child):
                        gap("upstream", "upstream-unresolved" if key == "unresolved_items" else "upstream-missing-fact",
                            pointer + f"/{index}", original)
                else:
                    collect_unresolved(child, pointer)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                collect_unresolved(child, path + f"/{index}")
    collect_unresolved(source)
    for category in CATEGORIES:
        if not categories[category]:
            gap(category, "empty-category", "", "No original fields admitted for this category.")
    body = {"schema_version": SCHEMA, "source": binding(""),
            "fact_catalog_digest": catalog["content_digest"], "categories": categories,
            "backport_queue": gaps, "authority_created": False}
    return {**body, "content_digest": canonical_digest(body)}


def validate_projection(projection: Mapping[str, Any], raw: bytes, *, expected_sha256: str,
                        logical_id: str) -> None:
    if projection != project_p1(raw, expected_sha256=expected_sha256, logical_id=logical_id):
        raise ProjectionError("Projection differs from original IDs, values or digests")


def select_items(projection: Mapping[str, Any], *, category: str, p1_ids: list[str]) -> list[dict]:
    """Select original IDs in source order, retaining the explicit identity family."""
    body = {k: v for k, v in projection.items() if k != "content_digest"}
    if projection.get("schema_version") != SCHEMA or projection.get("content_digest") != canonical_digest(body):
        raise ProjectionError("Projection digest or format differs")
    if category not in CATEGORIES or not isinstance(p1_ids, list) or any(not isinstance(x, str) for x in p1_ids):
        raise ProjectionError("Select an explicit category and original P1 IDs")
    rows = projection["categories"][category]
    wanted = set(p1_ids)
    if wanted - {row["p1_id"] for row in rows}:
        raise ProjectionError("Requested ID is not admitted in this category")
    return [deepcopy(row) for row in rows if row["p1_id"] in wanted]


def volume_report(projection: Mapping[str, Any], *, source_bytes: int) -> dict:
    def measure(value):
        raw = json_bytes(value)
        chars = len(raw.decode("utf-8"))
        return {"bytes": len(raw), "characters": chars, "sha256": hashlib.sha256(raw).hexdigest(),
                "estimated_tokens": (chars + 2) // 3, "token_estimate_method": "ceil(Unicode characters / 3)",
                "token_upper_bound": len(raw), "upper_bound_method": "UTF-8 bytes for byte-based tokenization",
                "exact_token_count": False, "scope": "document text only; no request framing or model usage"}
    return {"schema_version": "wff.p1-p2-projection-volume.v1", "source_bytes": source_bytes,
            "projection": measure(projection),
            "categories": {key: {"items": len(rows), **measure(rows)} for key, rows in projection["categories"].items()},
            "backport_queue_items": len(projection["backport_queue"]), "model_calls": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--logical-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    raw = args.authority.read_bytes()
    result = project_p1(raw, expected_sha256=args.expected_sha256, logical_id=args.logical_id)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json_exclusive(args.output_dir / "projection.json", result)
    write_json_exclusive(args.output_dir / "backport-queue.json", result["backport_queue"])
    report = volume_report(result, source_bytes=len(raw))
    write_json_exclusive(args.output_dir / "volume-report.json", report)
    print(json.dumps({"projection_sha256": report["projection"]["sha256"],
                      "bytes": report["projection"]["bytes"],
                      "estimated_tokens": report["projection"]["estimated_tokens"],
                      "exact_token_count": False, "backport_items": len(result["backport_queue"]),
                      "model_calls": 0}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
