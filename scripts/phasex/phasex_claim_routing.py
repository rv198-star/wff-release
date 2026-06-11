#!/usr/bin/env python3
"""Phase X adapters for shared dual-path claim-control routing.

The helpers here keep PX-specific generated artifacts on the generic Path A/B
contract without using rendered Markdown as truth.  They only inspect explicit
claim-control markers and obvious proposed-claim leakage.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Any

from common.claim_control_acceptance import infer_artifact_metadata
from common.claim_control_contract import resolve_claim_control_route


CLAIM_CONTROL_RENDERED_REFS_RE = re.compile(
    r"<!--\s*claim-control-rendered-refs:\s*(?P<refs>.*?)\s*-->",
    flags=re.IGNORECASE,
)
PX_CLAIM_ASSERTION_RE = re.compile(
    r"<!--\s*px-claim:\s*(?P<claim_id>[^|]+?)\s*\|\s*(?P<text>.*?)\s*-->",
    flags=re.IGNORECASE,
)
PROPOSED_CLAIM_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_-])PROPOSED[-:][A-Za-z0-9_.:-]+(?![A-Za-z0-9_-])"
)


def phasex_claim_control_route_decision(
    *,
    artifact_path: str | Path,
    artifact_id: str,
) -> dict[str, Any]:
    """Resolve PX route metadata using the shared generic router."""

    metadata = infer_artifact_metadata(
        artifact_path,
        {
            "artifact_id": artifact_id,
            "source_count": 2,
            "high_downstream_trust": True,
            "downstream_consumed": True,
        },
    )
    return resolve_claim_control_route(metadata, {"profile_id": "phasex"})


def _split_explicit_refs(value: str) -> list[str]:
    refs: list[str] = []
    for part in re.split(r"[,\s]+", value):
        ref = part.strip()
        if ref:
            refs.append(ref)
    return refs


def _normalized_assertion_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalized_proposed_ref(value: str) -> str:
    return value.strip().rstrip(".,;:)")


def audit_phasex_artifact_claim_refs(
    *,
    artifact_path: str | Path,
    accepted_claim_ids: set[str],
) -> dict[str, Any]:
    """Audit explicit PX claim refs without deriving new accepted truth."""

    path = Path(artifact_path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    proposed_claim_refs = sorted(
        {ref for ref in (_normalized_proposed_ref(match) for match in PROPOSED_CLAIM_REF_RE.findall(text)) if ref}
    )

    explicit_claim_refs: set[str] = set()
    assertion_texts_by_id: dict[str, set[str]] = defaultdict(set)
    for match in CLAIM_CONTROL_RENDERED_REFS_RE.finditer(text):
        explicit_claim_refs.update(_split_explicit_refs(match.group("refs")))
    for match in PX_CLAIM_ASSERTION_RE.finditer(text):
        claim_id = match.group("claim_id").strip()
        if not claim_id:
            continue
        explicit_claim_refs.add(claim_id)
        assertion_texts_by_id[claim_id].add(_normalized_assertion_text(match.group("text")))

    proposed_claim_id_set = set(proposed_claim_refs)
    unknown_claim_refs = sorted(
        ref
        for ref in explicit_claim_refs
        if ref not in accepted_claim_ids and ref not in proposed_claim_id_set
    )
    conflicting_claim_refs = sorted(
        claim_id for claim_id, texts in assertion_texts_by_id.items() if len({text for text in texts if text}) > 1
    )

    classifications: list[str] = []
    if unknown_claim_refs:
        classifications.append("phasex_unknown_claim_ref")
    if proposed_claim_refs:
        classifications.append("phasex_unreviewed_proposed_claim")
    if conflicting_claim_refs:
        classifications.append("phasex_conflicting_source_claim")

    return {
        "artifact_kind": "phasex-claim-ref-audit",
        "overall_status": "pass" if not classifications else "blocked",
        "classifications": classifications,
        "explicit_claim_refs": sorted(explicit_claim_refs),
        "unknown_claim_refs": unknown_claim_refs,
        "proposed_claim_refs": proposed_claim_refs,
        "conflicting_claim_refs": conflicting_claim_refs,
        "policy": "explicit refs are evidence only; proposed claims must return to claim review",
    }
