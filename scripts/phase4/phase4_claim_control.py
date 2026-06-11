#!/usr/bin/env python3
"""Phase-4 claim-control authority adapter.

Phase-4 closure artifacts are evidence and judgment surfaces.  This adapter
records how they are bounded by upstream claim-control surfaces without turning
P4 scorecards, Markdown, or gate reports into a new source of accepted truth.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
from typing import Any

from common.claim_control_acceptance import evaluate_claim_control_acceptance, infer_artifact_metadata
from common.claim_control_contract import resolve_claim_control_route
from common.claim_control_runtime import claims_from_sidecar
from common.cross_phase_surface_policy import resolve_cross_phase_surface_path


CLAIM_CONTROL_RENDERED_REFS_RE = re.compile(
    r"<!--\s*claim-control-rendered-refs:\s*(?P<refs>.*?)\s*-->",
    flags=re.IGNORECASE,
)
PROPOSED_CLAIM_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_-])PROPOSED[-:][A-Za-z0-9_.:-]+(?![A-Za-z0-9_-])"
)

CORE_PHASE4_ARTIFACTS = (
    "phase-verdict.json",
    "phase4-delivery-gate.json",
    "phase4-quality-check.json",
    "phase4-run-metadata.json",
    "phase-mainline-scorecard.md",
    "phase-acceptance-matrix.md",
    "stage-03-validation-closure-and-delivery-readiness-judgment/test-closure-judgment.md",
    "stage-03-validation-closure-and-delivery-readiness-judgment/downstream-boundary-note.md",
    "stage-04-release-readiness-and-final-handoff/release-readiness-gate.json",
    "stage-04-release-readiness-and-final-handoff/go-no-go-closure.json",
    "stage-04-release-readiness-and-final-handoff/go-no-go-closure.md",
    "stage-04-release-readiness-and-final-handoff/residual-risk-acceptance.json",
    "stage-04-release-readiness-and-final-handoff/final-handoff-package.md",
    "stage-04-release-readiness-and-final-handoff/stage-04-summary.json",
    "stage4-release-readiness-contract-report.json",
)


def discover_phase3_claim_control_sidecars(phase3_root: str | Path) -> list[Path]:
    root = Path(phase3_root)
    return sorted(path for path in root.rglob("*.claim-control.json") if path.is_file())


def default_phase4_claim_artifacts(output_dir: str | Path) -> list[Path]:
    root = Path(output_dir)
    return [root / relative for relative in CORE_PHASE4_ARTIFACTS if (root / relative).exists()]


def phase4_claim_control_report_paths(output_dir: str | Path) -> dict[str, Path]:
    root = Path(output_dir)
    return {
        "json": resolve_cross_phase_surface_path(root, "phase4", "phase4-claim-control-report.json"),
        "md": resolve_cross_phase_surface_path(root, "phase4", "phase4-claim-control-report.md"),
    }


def _sidecar_artifact_path(sidecar_path: Path) -> Path:
    stem = sidecar_path.name.removesuffix(".claim-control.json")
    markdown = sidecar_path.with_name(f"{stem}.md")
    if markdown.exists():
        return markdown
    json_artifact = sidecar_path.with_name(f"{stem}.json")
    if json_artifact.exists():
        return json_artifact
    return markdown


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def _split_explicit_refs(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,\s]+", value) if part.strip()]


def _normalized_proposed_ref(value: str) -> str:
    return value.strip().rstrip(".,;:)")


def _explicit_claim_refs(text: str) -> list[str]:
    refs: set[str] = set()
    for match in CLAIM_CONTROL_RENDERED_REFS_RE.finditer(text):
        refs.update(_split_explicit_refs(match.group("refs")))
    return sorted(refs)


def _proposed_claim_refs(text: str) -> list[str]:
    return sorted(
        {ref for ref in (_normalized_proposed_ref(match) for match in PROPOSED_CLAIM_REF_RE.findall(text)) if ref}
    )


def _artifact_route_decision(artifact_path: Path, *, upstream_surface_count: int) -> dict[str, Any]:
    metadata = infer_artifact_metadata(
        artifact_path,
        {
            "artifact_id": f"phase4:{artifact_path.stem}",
            "source_count": max(2, upstream_surface_count),
            "high_downstream_trust": True,
            "downstream_consumed": True,
        },
    )
    return resolve_claim_control_route(metadata, {"profile_id": "phase4"})


def _upstream_surface_rows(phase3_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], set[str]]:
    rows: list[dict[str, Any]] = []
    accepted_claim_ids: set[str] = set()
    for sidecar_path in discover_phase3_claim_control_sidecars(phase3_root):
        artifact_path = _sidecar_artifact_path(sidecar_path)
        if not artifact_path.exists():
            acceptance = {
                "overall_status": "review_bound",
                "claim_ceiling": "review-bound:missing-upstream-artifact",
                "classifications": ["upstream_artifact_missing"],
            }
        else:
            acceptance = evaluate_claim_control_acceptance(artifact_path, surface_path=sidecar_path)
        if acceptance.get("overall_status") == "pass":
            for claim in claims_from_sidecar(sidecar_path, source_label="phase3-claim-control"):
                accepted_claim_ids.add(claim.id)
        rows.append(
            {
                "sidecar_path": str(sidecar_path),
                "artifact_path": str(artifact_path),
                "overall_status": str(acceptance.get("overall_status") or ""),
                "claim_ceiling": str(acceptance.get("claim_ceiling") or ""),
                "classifications": list(acceptance.get("classifications", [])),
            }
        )

    counts = Counter(row["overall_status"] for row in rows)
    summary = {
        "upstream_surface_count": len(rows),
        "upstream_status_counts": [{"status": status, "count": count} for status, count in sorted(counts.items())],
        "accepted_upstream_claim_count": len(accepted_claim_ids),
    }
    return rows, summary, accepted_claim_ids


def _artifact_audit_row(
    *,
    artifact_path: Path,
    accepted_upstream_claim_ids: set[str],
    upstream_surface_count: int,
    upstream_available: bool,
    upstream_all_pass: bool,
) -> dict[str, Any]:
    text = _read_text(artifact_path)
    explicit_refs = _explicit_claim_refs(text)
    proposed_refs = _proposed_claim_refs(text)
    proposed_ref_set = set(proposed_refs)
    unknown_refs = sorted(
        ref for ref in explicit_refs if ref not in accepted_upstream_claim_ids and ref not in proposed_ref_set
    )

    classifications: list[str] = []
    if not upstream_available:
        classifications.append("phase4_missing_upstream_claim_control")
    elif not upstream_all_pass:
        classifications.append("phase4_upstream_claim_control_not_green")
    if unknown_refs:
        classifications.append("phase4_unknown_upstream_claim_ref")
    if proposed_refs:
        classifications.append("phase4_unreviewed_proposed_claim")

    if unknown_refs or proposed_refs:
        overall_status = "blocked"
        claim_ceiling = "blocked:phase4-claim-control-invalid"
    elif not upstream_available:
        overall_status = "review_bound"
        claim_ceiling = "review-bound:missing-upstream-claim-control"
    elif not upstream_all_pass:
        overall_status = "review_bound"
        claim_ceiling = "review-bound:upstream-claim-control-not-green"
    else:
        overall_status = "pass"
        claim_ceiling = "claim-controlled"

    return {
        "artifact_path": str(artifact_path),
        "overall_status": overall_status,
        "claim_ceiling": claim_ceiling,
        "route_decision": _artifact_route_decision(
            artifact_path,
            upstream_surface_count=upstream_surface_count,
        ),
        "classifications": sorted(set(classifications)),
        "explicit_claim_refs": explicit_refs,
        "unknown_upstream_claim_refs": unknown_refs,
        "proposed_claim_refs": proposed_refs,
    }


def build_phase4_claim_control_report(
    *,
    phase3_root: str | Path,
    output_dir: str | Path,
    artifact_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    upstream_rows, upstream_summary, accepted_claim_ids = _upstream_surface_rows(Path(phase3_root))
    upstream_available = bool(upstream_rows)
    upstream_all_pass = upstream_available and all(row["overall_status"] == "pass" for row in upstream_rows)
    artifacts = [
        _artifact_audit_row(
            artifact_path=Path(path),
            accepted_upstream_claim_ids=accepted_claim_ids,
            upstream_surface_count=len(upstream_rows),
            upstream_available=upstream_available,
            upstream_all_pass=upstream_all_pass,
        )
        for path in (artifact_paths or default_phase4_claim_artifacts(output_dir))
    ]

    if any(row["overall_status"] == "blocked" for row in artifacts):
        overall_status = "blocked"
        claim_ceiling = "blocked:phase4-claim-control-invalid"
    elif not upstream_available:
        overall_status = "review_bound"
        claim_ceiling = "review-bound:missing-upstream-claim-control"
    elif not upstream_all_pass:
        overall_status = "review_bound"
        claim_ceiling = "review-bound:upstream-claim-control-not-green"
    else:
        overall_status = "pass"
        claim_ceiling = "claim-controlled"

    return {
        "artifact_kind": "phase4-claim-control-report",
        "overall_status": overall_status,
        "claim_ceiling": claim_ceiling,
        "phase3_root": str(Path(phase3_root)),
        **upstream_summary,
        "upstream_surfaces": upstream_rows,
        "artifacts": artifacts,
        "creates_claims": False,
        "uses_rendered_views_as_truth": False,
        "policy": "P4 closure artifacts register upstream claim ceilings and evidence refs; they do not create accepted truth.",
    }


def render_phase4_claim_control_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase-4 Claim Control Report",
        "",
        f"- overall_status: `{report['overall_status']}`",
        f"- claim_ceiling: `{report['claim_ceiling']}`",
        f"- upstream_surface_count: `{report['upstream_surface_count']}`",
        f"- accepted_upstream_claim_count: `{report['accepted_upstream_claim_count']}`",
        f"- creates_claims: `{str(report['creates_claims']).lower()}`",
        f"- uses_rendered_views_as_truth: `{str(report['uses_rendered_views_as_truth']).lower()}`",
        "",
        "## Artifact Routes",
        "",
        "| artifact | status | ceiling | route | classifications |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["artifacts"]:
        route = row.get("route_decision", {}).get("route", "")
        classifications = ", ".join(row.get("classifications", [])) or "-"
        lines.append(
            f"| `{Path(row['artifact_path']).name}` | `{row['overall_status']}` | "
            f"`{row['claim_ceiling']}` | `{route}` | {classifications} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def emit_phase4_claim_control_report(
    *,
    phase3_root: str | Path,
    output_dir: str | Path,
    artifact_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    report = build_phase4_claim_control_report(
        phase3_root=phase3_root,
        output_dir=output_dir,
        artifact_paths=artifact_paths,
    )
    paths = phase4_claim_control_report_paths(output_dir)
    paths["json"].parent.mkdir(parents=True, exist_ok=True)
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["md"].parent.mkdir(parents=True, exist_ok=True)
    paths["md"].write_text(render_phase4_claim_control_markdown(report), encoding="utf-8")
    return {
        "report_path": str(paths["json"]),
        "markdown_path": str(paths["md"]),
        "report": report,
    }
