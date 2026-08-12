"""Lightweight P1 authority-to-canonical application verification.

The existing Phase-1 renderer remains the only PRD generator. This module does
not render or rewrite product content. It verifies that the generated canonical
PRD consumed the accepted authority and did not retain common parallel-truth
patterns after draft convergence.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from common.agentic_decision_authority import write_json_atomic


P1_CANONICAL_CONVERGENCE_SCHEMA = "wff.p1-canonical-authority-convergence.v1"
P1_CANONICAL_WRITER_ID = "phase1-existing-renderer-authority-bound.v1"
WORLD_KNOWLEDGE_CONTRACT = "p1-world-knowledge-backfill-v1"
AUTHORITY_MARKER = "## Snapshot-Bound Agentic Product Authority"


class P1CanonicalAuthorityConvergenceError(ValueError):
    """Raised when the existing P1 renderer did not consume accepted authority."""


def _digest_bytes(value: bytes) -> str:
    return "sha256:" + sha256(value).hexdigest()


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _digest_bytes(payload)


def _text(value: object) -> str:
    return str(value or "").strip()


def _rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _canonical_body(text: str) -> str:
    return text.split(AUTHORITY_MARKER, 1)[0]


def _contains_normalized(haystack: str, needle: str) -> bool:
    normalized_haystack = re.sub(r"\s+", " ", haystack).casefold()
    normalized_needle = re.sub(r"\s+", " ", needle).casefold().strip()
    return bool(normalized_needle and normalized_needle in normalized_haystack)


def _product_world_decision(authority: Mapping[str, Any]) -> dict[str, Any]:
    decision = authority.get("product_world_decision")
    return dict(decision) if isinstance(decision, Mapping) else {}


def _topology_mode(authority: Mapping[str, Any]) -> str:
    topology = _product_world_decision(authority).get("topology", {})
    return _text(topology.get("mode")) if isinstance(topology, Mapping) else ""


def _ownership_posture(authority: Mapping[str, Any]) -> str:
    ownership = _product_world_decision(authority).get("ownership", {})
    return _text(ownership.get("posture")) if isinstance(ownership, Mapping) else ""


def _topology_requires_independence(authority: Mapping[str, Any]) -> bool:
    return _topology_mode(authority) == "independent-outcomes"


def _ownership_is_review_bound(authority: Mapping[str, Any]) -> bool:
    return _ownership_posture(authority) in {"review-bound", "mixed"}


def validate_p1_canonical_authority_application(
    *,
    authority: Mapping[str, Any],
    artifact_text: str,
) -> dict[str, Any]:
    if authority.get("schema_version") != "wff.p1-agentic-product-authority.v1":
        raise P1CanonicalAuthorityConvergenceError("P1 authority schema is invalid")
    if authority.get("status") != "accepted-p1-agentic-product-authority":
        raise P1CanonicalAuthorityConvergenceError("P1 authority is not accepted")
    if authority.get("world_knowledge_contract") != WORLD_KNOWLEDGE_CONTRACT:
        raise P1CanonicalAuthorityConvergenceError("P1 world-knowledge contract is missing or stale")

    body = _canonical_body(artifact_text)
    conflicts: list[dict[str, str]] = []
    commitments = _rows(authority.get("commitments"))
    features = _rows(authority.get("feature_dispositions"))
    backfill = _rows(authority.get("world_knowledge_backfill"))

    for row in commitments:
        item_id = _text(row.get("commitment_id"))
        statement = _text(row.get("statement"))
        if not item_id:
            continue
        if item_id not in body:
            conflicts.append({"kind": "missing-commitment-identity", "item": item_id})
        if statement and not _contains_normalized(body, statement):
            conflicts.append({"kind": "missing-commitment-statement", "item": item_id})
        if _text(row.get("status")) == "review-bound":
            body_lines = body.splitlines()
            item_line_index = next((index for index, line in enumerate(body_lines) if item_id in line), -1)
            item_window = "\n".join(body_lines[item_line_index : item_line_index + 2]) if item_line_index >= 0 else ""
            if "review-bound" not in item_window.casefold() and "待评审" not in item_window:
                conflicts.append({"kind": "review-bound-status-lost", "item": item_id})

    for row in features:
        item_id = _text(row.get("feature_id"))
        disposition = _text(row.get("disposition"))
        if disposition not in {"later-slice", "deferred-seam", "explicit-exclusion", "unresolved-review-bound", "context-completion"}:
            continue
        if item_id and item_id not in artifact_text:
            conflicts.append({"kind": "scope-disposition-not-visible", "item": item_id})

    for row in backfill:
        backfill_id = _text(row.get("backfill_id"))
        status = _text(row.get("status"))
        truth_state = _text(row.get("truth_state"))
        compatibility = _text(row.get("source_compatibility"))
        if status == "accepted" and (truth_state != "agentic-world-knowledge" or compatibility != "consistent"):
            conflicts.append({"kind": "invalid-accepted-world-knowledge", "item": backfill_id or "missing-id"})
        if status in {"accepted", "review-bound"} and backfill_id and backfill_id not in body:
            conflicts.append({"kind": "world-knowledge-backfill-not-visible", "item": backfill_id})

    product_world = _product_world_decision(authority)
    topology = product_world.get("topology", {}) if isinstance(product_world.get("topology"), Mapping) else {}
    ownership = product_world.get("ownership", {}) if isinstance(product_world.get("ownership"), Mapping) else {}
    world_objects = _rows(product_world.get("objects"))
    world_summary = _text(product_world.get("summary"))
    topology_statement = _text(topology.get("statement"))
    ownership_statement = _text(ownership.get("statement"))
    if world_summary and not _contains_normalized(body, world_summary):
        conflicts.append({"kind": "product-world-summary-not-visible", "item": world_summary[:240]})
    if topology_statement and not _contains_normalized(body, topology_statement):
        conflicts.append({"kind": "product-world-topology-not-visible", "item": topology_statement[:240]})
    if ownership_statement and not _contains_normalized(body, ownership_statement):
        conflicts.append({"kind": "product-world-ownership-not-visible", "item": ownership_statement[:240]})
    for row in world_objects:
        object_id = _text(row.get("object_id"))
        name = _text(row.get("name"))
        if object_id and object_id not in body:
            conflicts.append({"kind": "product-world-object-identity-not-visible", "item": object_id})
        if name and not _contains_normalized(body, name):
            conflicts.append({"kind": "product-world-object-not-visible", "item": object_id or name[:240]})

    if _topology_requires_independence(authority):
        if not re.search(r"\bindependent(?:ly)?\b|独立(?:验证|结束|闭环|流程)", body, flags=re.IGNORECASE):
            conflicts.append({"kind": "independent-topology-not-applied", "item": "accepted-world"})
        serial_heading = re.search(r"^#{2,6}[^\n]*(?:->|→)[^\n]*$", body, flags=re.MULTILINE)
        if serial_heading:
            conflicts.append({"kind": "serial-heading-conflicts-with-independent-topology", "item": serial_heading.group(0).strip()})

    if _ownership_is_review_bound(authority):
        for line in body.splitlines():
            lowered = line.casefold()
            stripped = line.strip()
            if not re.search(r"primary[_ ]actor|only writer|\bowns?\b|唯一写入者|主要角色|责任角色", lowered):
                continue
            if re.search(r"review-bound|待评审|unresolved|authority-bound|accepted authority explicitly names|does not|must not|cannot|不得|不能|未确认", lowered):
                continue
            if re.search(r"\bwhich\b|\bwhether\b|\bthe primary actor\b|must declare primary actor", lowered) or stripped.endswith("?"):
                continue
            if stripped.startswith("|") and re.search(r"\|\s*primary[_ ]actor\s*\|", lowered):
                header_cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                if any(cell in {"activity", "activity_type", "screen/module", "primary_actor", "primary actor"} for cell in header_cells):
                    continue
            conflicts.append({"kind": "unconfirmed-ownership-promoted", "item": stripped[:240]})

    for pattern, kind in (
        (r"\bmodule_[123]\b", "generic-module-placeholder"),
        (r"candidate worlds and mechanical feature hints are non-authoritative[\s\S]*?^##\s+(?!Snapshot-Bound)", "authority-appended-before-more-canonical-content"),
    ):
        match = re.search(pattern, body, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            conflicts.append({"kind": kind, "item": match.group(0)[:240]})

    projection = {
        "authority_digest": _text(authority.get("content_digest")),
        "commitment_ids": [_text(row.get("commitment_id")) for row in commitments if _text(row.get("commitment_id"))],
        "feature_ids": [_text(row.get("feature_id")) for row in features if _text(row.get("feature_id"))],
        "backfill_ids": [_text(row.get("backfill_id")) for row in backfill if _text(row.get("backfill_id"))],
        "world_object_ids": [_text(row.get("object_id")) for row in world_objects if _text(row.get("object_id"))],
        "topology_mode": _topology_mode(authority),
        "ownership_posture": _ownership_posture(authority),
        "independent_topology_required": _topology_requires_independence(authority),
        "ownership_review_bound": _ownership_is_review_bound(authority),
    }
    return {
        "schema_version": P1_CANONICAL_CONVERGENCE_SCHEMA,
        "status": "pass" if not conflicts else "blocked",
        "writer_id": P1_CANONICAL_WRITER_ID,
        "authority_digest": projection["authority_digest"],
        "projection_digest": _canonical_digest(projection),
        "artifact_digest": _digest_bytes(artifact_text.encode("utf-8")),
        "canonical_body_digest": _digest_bytes(body.encode("utf-8")),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "checked_commitment_count": len(projection["commitment_ids"]),
        "checked_feature_count": len(projection["feature_ids"]),
        "checked_backfill_count": len(projection["backfill_ids"]),
        "checked_world_object_count": len(projection["world_object_ids"]),
        "topology_mode": projection["topology_mode"],
        "ownership_posture": projection["ownership_posture"],
        "independent_topology_required": projection["independent_topology_required"],
        "claim_ceiling": (
            "This report proves bounded application checks over the accepted P1 authority and generated PRD. "
            "It does not prove domain correctness, owner confirmation, P2 quality, UAT, release readiness, or production readiness."
        ),
    }


def verify_p1_canonical_prd(
    *,
    prd_path: Path,
    authority: Mapping[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    text = prd_path.read_text(encoding="utf-8")
    report = validate_p1_canonical_authority_application(authority=authority, artifact_text=text)
    report["artifact_name"] = prd_path.name
    report["artifact_path"] = str(prd_path)
    write_json_atomic(report_path, report)
    if report["status"] != "pass":
        kinds = sorted({row["kind"] for row in report["conflicts"]})
        raise P1CanonicalAuthorityConvergenceError(
            "P1 existing renderer did not converge to accepted authority: " + ", ".join(kinds)
        )
    return report
