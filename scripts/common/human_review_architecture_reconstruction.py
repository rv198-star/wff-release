#!/usr/bin/env python3
"""Optional architecture-reconstruction input contract for Human Review ESP.

The contract is intentionally smaller than the future v1.7 reconstruction
system. It carries source-bound architecture, responsibility, intent, change,
and assurance evidence into the detached Human Review lane without creating or
resolving architecture truth in deterministic code.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "wff.human-review-architecture-reconstruction-input.v1"
DEFAULT_INPUT_REF = ".wff/architecture-reconstruction/review-input.json"
STATUS_VALUES = {"accepted", "review-bound"}
NODE_KINDS = {"system", "domain", "module", "service", "repository", "interface", "data", "assurance"}
VALIDITY_VALUES = {"current", "needs-review", "stale", "unknown"}


class ArchitectureReconstructionInputError(ValueError):
    """The optional reconstruction input is unsafe or structurally invalid."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _object(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ArchitectureReconstructionInputError(f"{field} must be an object")
    return value


def _text(value: object, field: str, *, minimum: int = 1, maximum: int = 1200) -> str:
    text = str(value or "").strip()
    if len(text) < minimum:
        raise ArchitectureReconstructionInputError(f"{field} is missing or too short")
    if len(text) > maximum:
        raise ArchitectureReconstructionInputError(f"{field} is too long")
    return text


def _identifier(value: object, field: str) -> str:
    identifier = _text(value, field, minimum=2, maximum=100)
    if not identifier[0].isalpha() or not all(
        character.isalnum() or character in "._-" for character in identifier
    ):
        raise ArchitectureReconstructionInputError(
            f"{field} must start with a letter and use only letters, digits, '.', '_', or '-'"
        )
    return identifier


def _strings(
    value: object,
    field: str,
    *,
    minimum: int = 0,
    maximum: int = 20,
    item_minimum: int = 2,
) -> list[str]:
    if not isinstance(value, list):
        raise ArchitectureReconstructionInputError(f"{field} must be a list")
    result: list[str] = []
    for index, raw in enumerate(value, start=1):
        item = _text(raw, f"{field}[{index}]", minimum=item_minimum, maximum=500)
        if item not in result:
            result.append(item)
    if len(result) < minimum or len(result) > maximum:
        raise ArchitectureReconstructionInputError(
            f"{field} must contain between {minimum} and {maximum} unique items"
        )
    return result


def _status(value: object, field: str) -> str:
    status = _text(value, field)
    if status not in STATUS_VALUES:
        raise ArchitectureReconstructionInputError(
            f"{field} must be accepted or review-bound"
        )
    return status


def _safe_source_ref(case_root: Path, value: object, field: str) -> tuple[str, Path]:
    ref = _text(value, field, minimum=3, maximum=320)
    relative = Path(ref)
    path = (case_root / relative).resolve()
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not path.is_relative_to(case_root)
        or not path.is_file()
        or path.is_symlink()
    ):
        raise ArchitectureReconstructionInputError(
            f"{field} must reference a regular case-relative source file"
        )
    return relative.as_posix(), path


def _source_refs(
    case_root: Path,
    value: object,
    field: str,
    *,
    minimum: int = 1,
) -> tuple[list[str], dict[str, str]]:
    refs = _strings(value, field, minimum=minimum, maximum=20, item_minimum=3)
    normalized: list[str] = []
    receipt: dict[str, str] = {}
    for index, raw in enumerate(refs, start=1):
        ref, path = _safe_source_ref(case_root, raw, f"{field}[{index}]")
        normalized.append(ref)
        receipt[ref] = sha256_file(path)
    return normalized, receipt


def _merge_receipts(receipts: Iterable[dict[str, str]]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for receipt in receipts:
        for ref, digest in receipt.items():
            previous = merged.get(ref)
            if previous is not None and previous != digest:
                raise ArchitectureReconstructionInputError(
                    f"architecture reconstruction source hash conflict: {ref}"
                )
            merged[ref] = digest
    return dict(sorted(merged.items()))


def _architecture_tree(case_root: Path, value: object) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ArchitectureReconstructionInputError(
            "architecture_tree must be a non-empty list"
        )
    nodes: list[dict[str, Any]] = []
    receipts: list[dict[str, str]] = []
    ids: set[str] = set()
    for index, raw in enumerate(value, start=1):
        field = f"architecture_tree[{index}]"
        item = _object(raw, field)
        node_id = _identifier(item.get("id"), f"{field}.id")
        if node_id in ids:
            raise ArchitectureReconstructionInputError(
                f"architecture_tree contains duplicate id: {node_id}"
            )
        ids.add(node_id)
        kind = _text(item.get("kind"), f"{field}.kind")
        if kind not in NODE_KINDS:
            raise ArchitectureReconstructionInputError(
                f"{field}.kind is unsupported: {kind}"
            )
        refs, receipt = _source_refs(case_root, item.get("source_refs"), f"{field}.source_refs")
        receipts.append(receipt)
        nodes.append(
            {
                "id": node_id,
                "name": _text(item.get("name"), f"{field}.name", minimum=2, maximum=160),
                "kind": kind,
                "parent_id": str(item.get("parent_id") or "").strip(),
                "responsibility": _text(
                    item.get("responsibility"),
                    f"{field}.responsibility",
                    minimum=12,
                    maximum=800,
                ),
                "source_refs": refs,
                "status": _status(item.get("status"), f"{field}.status"),
            }
        )
    for node in nodes:
        parent = node["parent_id"]
        if parent and parent not in ids:
            raise ArchitectureReconstructionInputError(
                f"architecture_tree parent_id is missing: {parent}"
            )
        if parent == node["id"]:
            raise ArchitectureReconstructionInputError(
                f"architecture_tree node cannot parent itself: {parent}"
            )
    return nodes, _merge_receipts(receipts)


def _responsibility_map(case_root: Path, value: object) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ArchitectureReconstructionInputError(
            "responsibility_map must be a non-empty list"
        )
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, str]] = []
    ids: set[str] = set()
    for index, raw in enumerate(value, start=1):
        field = f"responsibility_map[{index}]"
        item = _object(raw, field)
        row_id = _identifier(item.get("id"), f"{field}.id")
        if row_id in ids:
            raise ArchitectureReconstructionInputError(
                f"responsibility_map contains duplicate id: {row_id}"
            )
        ids.add(row_id)
        refs, receipt = _source_refs(case_root, item.get("source_refs"), f"{field}.source_refs")
        receipts.append(receipt)
        rows.append(
            {
                "id": row_id,
                "subject": _text(item.get("subject"), f"{field}.subject", minimum=2, maximum=180),
                "owner": _text(item.get("owner"), f"{field}.owner", minimum=2, maximum=180),
                "responsibility": _text(
                    item.get("responsibility"), f"{field}.responsibility", minimum=12, maximum=900
                ),
                "non_responsibilities": _strings(
                    item.get("non_responsibilities"),
                    f"{field}.non_responsibilities",
                    minimum=1,
                    maximum=10,
                    item_minimum=5,
                ),
                "source_refs": refs,
                "status": _status(item.get("status"), f"{field}.status"),
            }
        )
    return rows, _merge_receipts(receipts)


def _implementation_intents(case_root: Path, value: object) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ArchitectureReconstructionInputError(
            "implementation_intents must be a non-empty list"
        )
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, str]] = []
    ids: set[str] = set()
    for index, raw in enumerate(value, start=1):
        field = f"implementation_intents[{index}]"
        item = _object(raw, field)
        row_id = _identifier(item.get("id"), f"{field}.id")
        if row_id in ids:
            raise ArchitectureReconstructionInputError(
                f"implementation_intents contains duplicate id: {row_id}"
            )
        ids.add(row_id)
        refs, receipt = _source_refs(case_root, item.get("source_refs"), f"{field}.source_refs")
        receipts.append(receipt)
        rows.append(
            {
                "id": row_id,
                "subject": _text(item.get("subject"), f"{field}.subject", minimum=2, maximum=180),
                "intent": _text(item.get("intent"), f"{field}.intent", minimum=20, maximum=1000),
                "rationale": _text(
                    item.get("rationale"), f"{field}.rationale", minimum=12, maximum=900
                ),
                "constraints": _strings(
                    item.get("constraints"), f"{field}.constraints", minimum=1, maximum=10, item_minimum=5
                ),
                "source_refs": refs,
                "status": _status(item.get("status"), f"{field}.status"),
            }
        )
    return rows, _merge_receipts(receipts)


def _change_impacts(case_root: Path, value: object) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if value is None:
        return [], {}
    if not isinstance(value, list):
        raise ArchitectureReconstructionInputError("change_impacts must be a list")
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, str]] = []
    ids: set[str] = set()
    for index, raw in enumerate(value, start=1):
        field = f"change_impacts[{index}]"
        item = _object(raw, field)
        row_id = _identifier(item.get("id"), f"{field}.id")
        if row_id in ids:
            raise ArchitectureReconstructionInputError(
                f"change_impacts contains duplicate id: {row_id}"
            )
        ids.add(row_id)
        refs, receipt = _source_refs(case_root, item.get("source_refs"), f"{field}.source_refs")
        receipts.append(receipt)
        rows.append(
            {
                "id": row_id,
                "change": _text(item.get("change"), f"{field}.change", minimum=12, maximum=900),
                "affected_subjects": _strings(
                    item.get("affected_subjects"),
                    f"{field}.affected_subjects",
                    minimum=1,
                    maximum=20,
                ),
                "impact": _text(item.get("impact"), f"{field}.impact", minimum=12, maximum=900),
                "risk": _text(item.get("risk"), f"{field}.risk", minimum=8, maximum=700),
                "source_refs": refs,
                "status": _status(item.get("status"), f"{field}.status"),
            }
        )
    return rows, _merge_receipts(receipts)


def _assurance_ownership(case_root: Path, value: object) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ArchitectureReconstructionInputError(
            "assurance_ownership must be a non-empty list"
        )
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, str]] = []
    ids: set[str] = set()
    for index, raw in enumerate(value, start=1):
        field = f"assurance_ownership[{index}]"
        item = _object(raw, field)
        row_id = _identifier(item.get("id"), f"{field}.id")
        if row_id in ids:
            raise ArchitectureReconstructionInputError(
                f"assurance_ownership contains duplicate id: {row_id}"
            )
        ids.add(row_id)
        validity = _text(item.get("current_validity"), f"{field}.current_validity")
        if validity not in VALIDITY_VALUES:
            raise ArchitectureReconstructionInputError(
                f"{field}.current_validity is invalid: {validity}"
            )
        refs, receipt = _source_refs(case_root, item.get("source_refs"), f"{field}.source_refs")
        receipts.append(receipt)
        rows.append(
            {
                "id": row_id,
                "mechanism": _text(item.get("mechanism"), f"{field}.mechanism", minimum=2, maximum=180),
                "owner": _text(item.get("owner"), f"{field}.owner", minimum=2, maximum=180),
                "protects": _text(item.get("protects"), f"{field}.protects", minimum=12, maximum=900),
                "origin": _text(item.get("origin"), f"{field}.origin", minimum=5, maximum=500),
                "current_validity": validity,
                "retirement_candidate": bool(item.get("retirement_candidate", False)),
                "source_refs": refs,
                "status": _status(item.get("status"), f"{field}.status"),
            }
        )
    return rows, _merge_receipts(receipts)


def _open_conflicts(case_root: Path, value: object) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if value is None:
        return [], {}
    if not isinstance(value, list):
        raise ArchitectureReconstructionInputError("open_conflicts must be a list")
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, str]] = []
    ids: set[str] = set()
    for index, raw in enumerate(value, start=1):
        field = f"open_conflicts[{index}]"
        item = _object(raw, field)
        row_id = _identifier(item.get("id"), f"{field}.id")
        if row_id in ids:
            raise ArchitectureReconstructionInputError(
                f"open_conflicts contains duplicate id: {row_id}"
            )
        ids.add(row_id)
        refs, receipt = _source_refs(case_root, item.get("source_refs"), f"{field}.source_refs")
        receipts.append(receipt)
        rows.append(
            {
                "id": row_id,
                "statement": _text(item.get("statement"), f"{field}.statement", minimum=15, maximum=1000),
                "affected_subjects": _strings(
                    item.get("affected_subjects"),
                    f"{field}.affected_subjects",
                    minimum=1,
                    maximum=20,
                ),
                "decision_impact": _text(
                    item.get("decision_impact"),
                    f"{field}.decision_impact",
                    minimum=12,
                    maximum=900,
                ),
                "source_refs": refs,
                "status": "review-bound",
            }
        )
    return rows, _merge_receipts(receipts)


def normalize_reconstruction_input(
    *, case_root: Path, payload: object
) -> tuple[dict[str, Any], dict[str, str]]:
    root = case_root.resolve()
    data = _object(payload, "architecture_reconstruction_input")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ArchitectureReconstructionInputError(
            f"schema_version must be {SCHEMA_VERSION}"
        )
    tree, tree_receipt = _architecture_tree(root, data.get("architecture_tree"))
    responsibility, responsibility_receipt = _responsibility_map(
        root, data.get("responsibility_map")
    )
    intents, intent_receipt = _implementation_intents(
        root, data.get("implementation_intents")
    )
    impacts, impact_receipt = _change_impacts(root, data.get("change_impacts"))
    assurance, assurance_receipt = _assurance_ownership(
        root, data.get("assurance_ownership")
    )
    conflicts, conflict_receipt = _open_conflicts(root, data.get("open_conflicts"))
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "architecture_tree": tree,
        "responsibility_map": responsibility,
        "implementation_intents": intents,
        "change_impacts": impacts,
        "assurance_ownership": assurance,
        "open_conflicts": conflicts,
    }
    receipt = _merge_receipts(
        [
            tree_receipt,
            responsibility_receipt,
            intent_receipt,
            impact_receipt,
            assurance_receipt,
            conflict_receipt,
        ]
    )
    return normalized, receipt


def discover_reconstruction_input(
    case_root: Path, *, ref: str = DEFAULT_INPUT_REF
) -> dict[str, Any] | None:
    root = case_root.resolve()
    relative = Path(ref)
    path = (root / relative).resolve()
    if not path.exists():
        return None
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not path.is_relative_to(root)
        or not path.is_file()
        or path.is_symlink()
    ):
        raise ArchitectureReconstructionInputError(
            "architecture reconstruction input must be a regular case-relative file"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArchitectureReconstructionInputError(
            f"architecture reconstruction input is unreadable: {exc}"
        ) from exc
    normalized, source_hashes = normalize_reconstruction_input(
        case_root=root, payload=payload
    )
    conflict_ids = [item["id"] for item in normalized["open_conflicts"]]
    review_bound_count = sum(
        1
        for collection in (
            normalized["architecture_tree"],
            normalized["responsibility_map"],
            normalized["implementation_intents"],
            normalized["change_impacts"],
            normalized["assurance_ownership"],
            normalized["open_conflicts"],
        )
        for item in collection
        if item.get("status") == "review-bound"
    )
    return {
        "path": path,
        "ref": relative.as_posix(),
        "sha256": sha256_file(path),
        "payload": normalized,
        "source_hashes": source_hashes,
        "conflict_ids": conflict_ids,
        "summary": {
            "architecture_node_count": len(normalized["architecture_tree"]),
            "responsibility_count": len(normalized["responsibility_map"]),
            "implementation_intent_count": len(normalized["implementation_intents"]),
            "change_impact_count": len(normalized["change_impacts"]),
            "assurance_ownership_count": len(normalized["assurance_ownership"]),
            "open_conflict_count": len(conflict_ids),
            "review_bound_count": review_bound_count,
        },
    }


def validate_reconstruction_conflict_coverage(
    review_model: dict[str, Any], conflict_ids: list[str]
) -> None:
    if not conflict_ids:
        return
    observed = {
        str(anchor.get("identity") or "")
        for section in review_model.get("sections", [])
        if isinstance(section, dict)
        for anchor in section.get("evidence_anchors", [])
        if isinstance(anchor, dict)
    }
    missing = sorted(set(conflict_ids) - observed)
    if missing:
        raise ArchitectureReconstructionInputError(
            "structured ESP review model does not expose reconstruction conflicts as review evidence: "
            + ", ".join(missing)
        )


def reconstruction_receipt(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "schema_version": SCHEMA_VERSION,
        "path": str(value["ref"]),
        "sha256": str(value["sha256"]),
        "source_hashes": dict(value["source_hashes"]),
        "summary": dict(value["summary"]),
        "conflict_ids": list(value["conflict_ids"]),
    }
