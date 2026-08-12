"""Mechanical finding-lineage validation for bounded challenge cycles."""

from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Iterable, Mapping


FINDING_DISPOSITIONS = frozenset({
    "contract-or-context-insufficient",
    "valid-actionable",
    "valid-review-bound",
    "context-mismatch-or-noise",
})
FINDING_LINEAGE_STATUSES = frozenset({
    "opened",
    "carried",
    "resolved",
    "review-bound",
    "rejected",
})


class FindingLineageError(ValueError):
    """Raised when a material finding disappears or has invalid lineage."""


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def digest_valid(value: object) -> bool:
    return bool(re.fullmatch(r"sha256:[0-9a-f]{64}", str(value or "")))


def normalize_finding_for_cycle(
    raw: Mapping[str, Any],
    *,
    cycle_number: int,
) -> dict[str, Any]:
    finding = dict(raw)
    finding_id = str(finding.get("finding_id") or "").strip()
    disposition = str(finding.get("disposition") or "").strip()
    default_status = {
        "valid-actionable": "opened",
        "valid-review-bound": "review-bound",
        "contract-or-context-insufficient": "review-bound",
        "context-mismatch-or-noise": "rejected",
    }.get(disposition, "opened")
    finding["origin_cycle"] = int(finding.get("origin_cycle") or cycle_number)
    finding["prior_finding_id"] = str(finding.get("prior_finding_id") or "")
    finding["lineage_status"] = str(finding.get("lineage_status") or default_status)
    if finding["lineage_status"] in {"resolved", "rejected"} and not str(
        finding.get("resolution_evidence_digest") or ""
    ):
        finding["resolution_evidence_digest"] = canonical_digest(
            {
                "finding_id": finding_id,
                "cycle_number": cycle_number,
                "disposition": disposition,
                "owner_rationale": str(finding.get("owner_rationale") or ""),
                "artifact_changed": bool(finding.get("artifact_changed")),
            }
        )
    return finding


def normalize_findings(
    findings: Iterable[Mapping[str, Any]],
    *,
    cycle_number: int,
) -> list[dict[str, Any]]:
    return [
        normalize_finding_for_cycle(row, cycle_number=cycle_number)
        for row in findings
    ]


def validate_cycle_findings(
    *,
    findings: Iterable[Mapping[str, Any]],
    cycle_number: int,
    lineage_origins: dict[str, int],
    unresolved_lineage: Mapping[str, str],
) -> tuple[list[dict[str, str]], dict[str, str]]:
    finding_ids: set[str] = set()
    material_rows: list[dict[str, str]] = []
    required_from_previous = set(unresolved_lineage)
    next_unresolved: dict[str, str] = {}

    for finding in findings:
        if not isinstance(finding, Mapping):
            raise FindingLineageError("challenge finding is invalid")
        finding_id = str(finding.get("finding_id") or "").strip()
        if not finding_id or finding_id in finding_ids:
            raise FindingLineageError(
                "challenge finding identity is missing or duplicated"
            )
        finding_ids.add(finding_id)
        if not str(finding.get("statement") or "").strip():
            raise FindingLineageError("challenge finding statement is missing")
        materiality = str(finding.get("materiality") or "").strip()
        if materiality not in {"material", "trivial"}:
            raise FindingLineageError("challenge finding materiality is invalid")
        disposition = str(finding.get("disposition") or "").strip()
        if disposition not in FINDING_DISPOSITIONS:
            raise FindingLineageError("challenge finding disposition is invalid")
        if not str(finding.get("owner_rationale") or "").strip():
            raise FindingLineageError("owner reconciliation rationale is missing")
        if "score" in finding or "confidence_score" in finding:
            raise FindingLineageError(
                "finding scores cannot become semantic truth"
            )

        lineage_status = str(finding.get("lineage_status") or "").strip()
        if lineage_status not in FINDING_LINEAGE_STATUSES:
            raise FindingLineageError(
                "challenge finding lineage status is invalid"
            )
        origin_cycle = int(finding.get("origin_cycle") or 0)
        prior_finding_id = str(finding.get("prior_finding_id") or "").strip()
        if finding_id in lineage_origins:
            if (
                origin_cycle != lineage_origins[finding_id]
                or prior_finding_id != finding_id
            ):
                raise FindingLineageError(
                    "challenge finding lineage does not bind its prior identity"
                )
        else:
            if origin_cycle != cycle_number or prior_finding_id:
                raise FindingLineageError(
                    "new challenge finding has invalid lineage origin"
                )
            lineage_origins[finding_id] = origin_cycle

        if lineage_status in {"resolved", "rejected"} and not digest_valid(
            finding.get("resolution_evidence_digest")
        ):
            raise FindingLineageError(
                "closed finding lacks resolution evidence digest"
            )
        if disposition == "valid-actionable":
            if lineage_status not in {"opened", "carried", "resolved"}:
                raise FindingLineageError(
                    "actionable finding has incompatible lineage status"
                )
            if finding.get("artifact_changed") is not True:
                raise FindingLineageError(
                    "actionable finding lacks a substantive artifact change"
                )
        elif (
            disposition == "valid-review-bound"
            and lineage_status != "review-bound"
        ):
            raise FindingLineageError(
                "review-bound finding has incompatible lineage status"
            )
        elif (
            disposition == "contract-or-context-insufficient"
            and lineage_status != "review-bound"
        ):
            raise FindingLineageError(
                "insufficient-context finding must remain review-bound"
            )
        elif (
            disposition == "context-mismatch-or-noise"
            and lineage_status != "rejected"
        ):
            raise FindingLineageError(
                "rejected-noise finding has incompatible lineage status"
            )

        if lineage_status in {"opened", "carried", "review-bound"}:
            next_unresolved[finding_id] = lineage_status
        if materiality == "material":
            material_rows.append(
                {
                    "finding_id": finding_id,
                    "disposition": disposition,
                    "lineage_status": lineage_status,
                }
            )

    missing = sorted(required_from_previous - finding_ids)
    if missing:
        raise FindingLineageError(
            "unresolved findings disappeared between challenge cycles: "
            + ", ".join(missing)
        )
    return material_rows, next_unresolved
