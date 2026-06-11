from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from common.claim_control_runtime import (
    accepted_claims_from_phase1_trace_units,
    claims_from_sidecar,
)
from phase1.phase1_trace_units import extract_phase1_trace_units


PHASE1_UPSTREAM_CLAIM_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:P1-(?:AC|EP|REQ|UC|US)-\d{3}|FLOW-\d{1,4}|STATE-[A-Za-z0-9_:-]+)(?![A-Za-z0-9_-])"
)


def default_claim_control_sidecar_path(artifact_path: Path) -> Path:
    return artifact_path.with_name(f"{artifact_path.stem}.claim-control.json")


def phase1_claims_for_phase2(phase1_prd: Path) -> tuple[list[Any], str, Path | None]:
    sidecar_path = default_claim_control_sidecar_path(phase1_prd)
    if sidecar_path.exists():
        return claims_from_sidecar(sidecar_path, source_label="phase1-claim-control"), "upstream-claim-control", sidecar_path
    trace_units = extract_phase1_trace_units(phase1_prd.read_text(encoding="utf-8"))
    return (
        accepted_claims_from_phase1_trace_units(trace_units, source_label=phase1_prd.name),
        "compatibility-fallback-phase1-trace-units",
        None,
    )


def extract_phase1_upstream_claim_refs(text: str) -> list[str]:
    return sorted(set(PHASE1_UPSTREAM_CLAIM_REF_RE.findall(text)))


def audit_phase2_artifact_upstream_claim_refs(
    artifact_path: Path,
    *,
    accepted_phase1_claim_ids: set[str],
) -> dict[str, Any]:
    text = artifact_path.read_text(encoding="utf-8") if artifact_path.exists() else ""
    refs = extract_phase1_upstream_claim_refs(text)
    unknown_refs = sorted(ref for ref in refs if ref not in accepted_phase1_claim_ids)
    classifications = ["phase2_unknown_upstream_p1_claim_ref"] if unknown_refs else []
    return {
        "overall_status": "blocked" if unknown_refs else "pass",
        "declared_upstream_p1_claim_refs": refs,
        "unknown_upstream_p1_claim_refs": unknown_refs,
        "classifications": classifications,
    }


def phase2_claim_control_report_status(
    *,
    artifact_statuses: list[str],
    phase1_claim_source_mode: str,
) -> str:
    if any(status == "blocked" for status in artifact_statuses):
        return "blocked"
    if not artifact_statuses or any(status != "pass" for status in artifact_statuses):
        return "review_bound"
    if phase1_claim_source_mode != "upstream-claim-control":
        return "review_bound"
    return "pass"


def phase2_claim_control_claim_ceiling(
    *,
    overall_status: str,
    phase1_claim_source_mode: str,
) -> str:
    if overall_status == "blocked":
        return "blocked:phase2-upstream-claim-ref-invalid"
    if phase1_claim_source_mode != "upstream-claim-control":
        return "review-bound:phase1-claim-control-unavailable"
    if overall_status == "review_bound":
        return "review-bound:phase2-claim-control-incomplete"
    return "claim-controlled"
