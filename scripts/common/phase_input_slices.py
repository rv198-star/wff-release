"""Exact original-value reads extracted from B 6da99f015's fact catalog.

Only callers choose IDs/pointers. Reading an object does not grant identities
for its nested entities. Bindings are local evidence, not model output syntax.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
import re
from pathlib import Path
from typing import Any, Mapping
from common.agentic_decision_authority import canonical_digest
from common.semantic_materialization import get_pointer, pointer_token as _pointer_token, load_json_strict, write_json_exclusive


# The two P2 upstream families from B's _fact_catalog. These are local schema
# identities, never new business types or model-facing composition handles.
SEMANTIC_REF_FIELDS = {
    "p2-upstream-commitment": ("/p1_authority/accepted_commitments/", "commitment_id"),
    "p2-interaction-context": ("/p1_authority/interaction_relevant_product_context/task_contexts/", "context_id"),
}


class InputSliceError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _append_p1_source_slices(facts: list[dict[str, Any]], projection: Mapping[str, Any],
                             document: Mapping[str, Any]) -> None:
    """Original fields and collection objects, not inferred business/stage chunks.

    Top-level fields and their direct object fields remain addressable;
    object collection elements are complete original values. Primitive arrays
    remain one exact field (no per-scalar/identifier locator explosion). Existing typed rows
    are reused. Whole candidate roots remain legal reads without nested ID grants.
    Only portable P2 calls supply this validated, immutable upstream document.
    """
    from common.semantic_materialization import get_pointer
    raw = document.get("data")
    if (document.get("role") != "p1-agentic-authority" or not document.get("logical_id")
            or not isinstance(raw, bytes) or document.get("sha256") != "sha256:" + sha256(raw).hexdigest()):
        raise InputSliceError("fact-source-binding", "P1 source document bytes/digest differ")
    try:
        source = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise InputSliceError("fact-source-binding", "Invalid P1 source JSON") from exc
    if (not isinstance(source, dict)
            or source.get("content_digest") != canonical_digest({k: v for k, v in source.items() if k != "content_digest"})
            or any(projection.get(key) != source.get(source_key) for key, source_key in
                   (("authority_digest", "content_digest"), ("decision_id", "decision_id"), ("decision_digest", "decision_digest")))):
        raise InputSliceError("fact-source-binding", "P1 original Authority identity differs from projection")
    identity = {key: document[key] for key in ("logical_id", "sha256")}
    identity.update({"authority_schema_version": source["schema_version"],
                     "authority_digest": source["content_digest"],
                     "decision_id": source["decision_id"], "decision_digest": source["decision_digest"]})
    existing = {row.get("path"): row for row in facts if row.get("kind") == "semantic-identity"}

    def emit(value: Any, path: str, source_path: str, descend: bool = True) -> None:
        if canonical_digest(get_pointer(source, source_path)) != canonical_digest(value):
            raise InputSliceError("fact-source-binding", f"P1 projected value differs at {path}")
        row = existing.get(path)
        if row is None:
            row = {"fact_ref": "P1-SLICE:" + path, "kind": "p1-source-slice", "path": path,
                   "value": deepcopy(value), "semantic_refs": []}
            facts.append(row)
        elif canonical_digest(row["value"]) != canonical_digest(value):
            raise InputSliceError("fact-source-binding", f"P1 typed row differs at {path}")
        row["p1_source"] = {**identity, "path": source_path, "value_digest": canonical_digest(value)}
        if not descend:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                token = "/" + _pointer_token(key)
                emit(child, path + token, source_path + token, False)
                if isinstance(child, list):
                    for index, row in enumerate(child):
                        if isinstance(row, dict):
                            emit(row, path + token + f"/{index}", source_path + token + f"/{index}", False)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                # A collection row is the original indivisible read value, not
                # a semantic work item. Do not recursively multiply its fields.
                if isinstance(child, dict):
                    emit(child, path + f"/{index}", source_path + f"/{index}", False)

    absent_defaults = {"unresolved_items": [], "world_knowledge_contract": "", "world_knowledge_backfill": [],
                       "product_world_decision": {}, "product_judgment": {},
                       "interaction_relevant_product_context": None, "interaction_semantics_contract": "",
                       "claim_ceiling": "", "world_alignment": {}, "material_feature_review": {},
                       "context_sufficiency": {}, "truth_boundary": {}, "context_evidence": []}
    for key, value in projection.items():
        if key in {"accepted_commitments", "other_commitments"}:
            accepted = key == "accepted_commitments"
            original = [(i, row) for i, row in enumerate(source.get("commitments", []))
                        if (row.get("status") == "accepted") == accepted]
            if canonical_digest(value) != canonical_digest([row for _, row in original]):
                raise InputSliceError("fact-source-binding", "P1 commitment source order/cardinality differs")
            for index, (source_index, row) in enumerate(original):
                # Existing commitment rows carry the sole canonical identity grant.
                emit(row, f"/p1_authority/{key}/{index}", f"/commitments/{source_index}", False)
        elif key in {"decision_id", "decision_digest", "authority_digest", "application_digest"}:
            continue  # Publication identity already binds the root; not product content.
        elif key in source:
            emit(value, "/p1_authority/" + _pointer_token(key), "/" + _pointer_token(key))
        elif key in absent_defaults and canonical_digest(value) == canonical_digest(absent_defaults[key]):
            continue  # Existing legacy projection default, never an original source fact.
        else:
            raise InputSliceError("fact-source-binding", f"P1 projection has no original field: {key}")


def _fact_index(catalog: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if catalog.get("content_digest") != canonical_digest({k: v for k, v in catalog.items() if k != "content_digest"}):
        raise InputSliceError("fact-catalog-digest", "Frozen catalog digest differs")
    rows = catalog.get("facts")
    if catalog.get("schema_version") != "wff.semantic-fact-catalog.v2" or not isinstance(rows, list):
        raise InputSliceError("fact-catalog", "Admitted fact catalog is invalid")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("fact_ref"), str):
            raise InputSliceError("fact-catalog", "Admitted fact catalog row is invalid")
        ref = str(row["fact_ref"])
        if not ref or ref in result:
            raise InputSliceError("fact-catalog", f"Duplicate/empty admitted fact reference: {ref or 'empty'}")
        semantic_refs = row.get("semantic_refs")
        if not isinstance(semantic_refs, list):
            raise InputSliceError("fact-catalog-semantic-ref", f"{ref} lacks explicit semantic_refs")
        identities: set[tuple[str, str]] = set()
        for semantic in semantic_refs:
            if not isinstance(semantic, Mapping):
                raise InputSliceError("fact-catalog-semantic-ref", f"{ref} has invalid semantic ref")
            kind = str(semantic.get("kind") or ""); value = str(semantic.get("ref") or "")
            if kind not in SEMANTIC_REF_FIELDS or not value or set(semantic) != {"kind", "ref"}:
                raise InputSliceError("fact-catalog-semantic-ref", f"{ref} has invalid canonical semantic ref")
            prefix, field = SEMANTIC_REF_FIELDS[kind]
            original = row.get("value")
            if (row.get("kind") != "semantic-identity"
                    or re.fullmatch(re.escape(prefix) + r"(?:0|[1-9][0-9]*)", str(row.get("path", ""))) is None
                    or not isinstance(original, Mapping) or original.get(field) != value):
                raise InputSliceError("fact-catalog-semantic-ref", f"{ref} differs from its original typed identity")
            identity = (kind, value)
            if identity in identities:
                raise InputSliceError("fact-catalog-semantic-ref", f"{ref} duplicates canonical semantic ref {kind}:{value}")
            identities.add(identity)
        result[ref] = deepcopy(row)
    return result


def _selected_facts(catalog: Mapping[str, Any], refs: list[str]) -> list[dict[str, Any]]:
    index = _fact_index(catalog)
    missing = [ref for ref in refs if ref not in index]
    if missing:
        raise InputSliceError("context-request-unknown", "Unknown admitted fact refs: " + ", ".join(missing))
    return [deepcopy(index[ref]) for ref in refs]


def _facts_in_catalog_order(*, catalog: Mapping[str, Any], refs: list[str]) -> list[dict[str, Any]]:
    index = _fact_index(catalog)
    unique = list(dict.fromkeys(str(ref) for ref in refs))
    unknown = [ref for ref in unique if ref not in index]
    if unknown:
        raise InputSliceError(
            "fact-read-binding-unknown",
            "Actual fact-read binding references facts outside the frozen catalog: " + ", ".join(unknown),
        )
    wanted = set(unique)
    return [deepcopy(row) for row in catalog["facts"] if str(row["fact_ref"]) in wanted]


def source_catalog(*, projection: Mapping[str, Any], document: Mapping[str, Any]) -> dict:
    """Derive explicit typed reads from the original fields, as B's catalog did."""
    facts = []
    interaction = projection.get("interaction_relevant_product_context", {})
    contexts = interaction.get("task_contexts", []) if isinstance(interaction, Mapping) else []
    for kind, rows, label in (
        ("p2-upstream-commitment", projection.get("accepted_commitments", []), "COMMITMENT"),
        ("p2-interaction-context", contexts, "INTCTX"),
    ):
        prefix, field = SEMANTIC_REF_FIELDS[kind]
        if not isinstance(rows, list):
            raise InputSliceError("fact-catalog-semantic-ref", "P1 typed collection must be an array")
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping) or not isinstance(row.get(field), str) or not row[field]:
                raise InputSliceError("fact-catalog-semantic-ref", "P1 typed identity is missing")
            facts.append({"fact_ref": f"SEM-P2-{label}-{index + 1:05d}", "kind": "semantic-identity",
                          "path": prefix + str(index), "value": deepcopy(dict(row)),
                          "semantic_refs": [{"kind": kind, "ref": row[field]}]})
    _append_p1_source_slices(facts, projection, document)
    for row in facts:
        if "p1_source" not in row:
            raise InputSliceError("fact-source-binding", "Typed row has no original source binding")
    body = {"schema_version": "wff.semantic-fact-catalog.v2", "facts": facts}
    body["content_digest"] = canonical_digest(body)
    _fact_index(body)
    return body


def selected_facts(catalog: Mapping[str, Any], refs: list[str]) -> list[dict]:
    return _selected_facts(catalog, refs)


def require_typed_ref(facts: list[dict], *, kind: str, ref: str) -> None:
    """Family and ID must be explicitly granted, never found by recursive search."""
    if not any({"kind": kind, "ref": ref} in row["semantic_refs"] for row in facts):
        raise InputSliceError("typed-reference", "Reference is outside the selected entity family")


def read_binding(*, catalog: Mapping[str, Any], run_id: str, section: str,
                 read_version: int, refs: list[str], producer_call_id: str) -> dict:
    facts = _facts_in_catalog_order(catalog=catalog, refs=refs)
    if not run_id or not section or not producer_call_id or type(read_version) is not int or read_version < 1:
        raise InputSliceError("fact-read-binding-subject", "Explicit call/section/version required")
    body = {"schema_version": "wff.phase-input-read-binding.v1", "run_id": run_id,
            "section": section, "read_version": read_version, "producer_call_id": producer_call_id,
            "fact_catalog_digest": catalog["content_digest"],
            "fact_refs": [f["fact_ref"] for f in facts], "facts": facts, "authority_created": False}
    return {**body, "content_digest": canonical_digest(body)}


def validate_read_binding(value: Mapping[str, Any], *, catalog: Mapping[str, Any],
                          run_id: str, section: str, read_version: int) -> dict:
    try:
        expected = read_binding(catalog=catalog, run_id=run_id, section=section,
            read_version=read_version, refs=value["fact_refs"], producer_call_id=value["producer_call_id"])
    except (KeyError, TypeError) as exc:
        raise InputSliceError("fact-read-binding-shape", "Malformed read binding") from exc
    if value != expected:
        raise InputSliceError("fact-read-binding-conflict", "Read bytes, identity or version differs")
    return deepcopy(expected)


def persist_read_binding(path: Path, value: Mapping[str, Any], **binding_context) -> dict:
    validated = validate_read_binding(value, **binding_context)
    if path.exists():
        if load_json_strict(path) != validated:
            raise InputSliceError("fact-read-binding-conflict", "Retained read binding differs")
    else:
        write_json_exclusive(path, validated)
    return validated


def load_read_binding(path: Path, **binding_context) -> dict:
    return validate_read_binding(load_json_strict(path), **binding_context)
