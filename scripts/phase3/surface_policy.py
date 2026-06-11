from __future__ import annotations

from pathlib import Path
from typing import Iterable


PROTECTED_PHASE3_SURFACES = frozenset(
    {
        "runtime-smoke-report.json",
        "runtime-smoke-report.md",
        "started-service-smoke-report.json",
        "phase-verdict.json",
        "phase3-delivery-gate.json",
        "phase3-verification-ledger.json",
        "phase3-verification-ledger.md",
        "agentic-generation-quality-loop.json",
        "agentic-generation-quality-loop.md",
        "agentic-repair-interrupt.json",
        "agentic-repair-interrupt.md",
        "agentic-implementation-loop.json",
        "agentic-implementation-loop.md",
        "phase3-wp-gate.json",
        "unit-test-report.json",
        "phase3-coverage-gate.json",
        "phase3-quality-check.json",
        "phase3-run-metadata.json",
        "phase-3-acceptance-report.md",
        "phase-3-execution-report.md",
        "phase-mainline-scorecard.md",
        "phase-acceptance-matrix.md",
        "test-richness-review.json",
        "test-obligation-audit.json",
        "test-obligation-matrix.json",
        "implementation-bindings.json",
        "openapi-final.yaml",
        "phase-3-trace-registry-final.json",
    }
)


P4_PHASE3_CONSUMER_SURFACES = frozenset(
    {
        "phase-verdict.json",
        "phase3-delivery-gate.json",
        "phase3-run-metadata.json",
        "phase-3-acceptance-report.md",
        "phase-3-execution-report.md",
        "phase-mainline-scorecard.md",
        "phase-acceptance-matrix.md",
        "code-review-metrics.json",
        "mock-dependency-manifest.json",
    }
)


DEWEIGHTED_PHASE3_DIAGNOSTIC_SURFACES = {
    "generated-runtime-positioning.md": ".phase3-diagnostics/generated-runtime-positioning.md",
    "api-doc-consistency-report.md": ".phase3-diagnostics/api-doc-consistency-report.md",
    "phase3-timing-report.json": ".phase3-diagnostics/phase3-timing-report.json",
}


REVIEW_PHASE3_SURFACES = frozenset(
    {
        "code-review-report.md",
        "security-audit-report.md",
        "phase3-synthesis-brief.json",
        "phase3-synthesis-brief.md",
        "test-obligation-matrix.md",
        "test-obligation-audit.md",
        "test-richness-review.md",
    }
)


DEWEIGHTED_PHASE3_REVIEW_SURFACES = {
    surface_name: f".phase3-review/{surface_name}" for surface_name in REVIEW_PHASE3_SURFACES
}


ROOT_PHASE3_SURFACE_PROFILES = {
    **{surface_name: "canonical" for surface_name in PROTECTED_PHASE3_SURFACES},
    **{surface_name: "p4-consumed" for surface_name in P4_PHASE3_CONSUMER_SURFACES},
    **{surface_name: "diagnostic" for surface_name in DEWEIGHTED_PHASE3_DIAGNOSTIC_SURFACES},
    **{surface_name: "review" for surface_name in REVIEW_PHASE3_SURFACES},
}


def resolve_phase3_diagnostic_surface_path(output_dir: Path, surface_name: str) -> Path:
    relative_path = DEWEIGHTED_PHASE3_DIAGNOSTIC_SURFACES[surface_name]
    return output_dir / relative_path


def resolve_phase3_surface_path(output_dir: Path, surface_name: str) -> Path:
    if surface_name in DEWEIGHTED_PHASE3_DIAGNOSTIC_SURFACES:
        return output_dir / DEWEIGHTED_PHASE3_DIAGNOSTIC_SURFACES[surface_name]
    if surface_name in DEWEIGHTED_PHASE3_REVIEW_SURFACES:
        return output_dir / DEWEIGHTED_PHASE3_REVIEW_SURFACES[surface_name]
    return output_dir / surface_name


def write_phase3_diagnostic_surface(output_dir: Path, surface_name: str, content: str) -> Path:
    output_path = resolve_phase3_surface_path(output_dir, surface_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def write_phase3_profiled_surface(output_dir: Path, surface_name: str, content: str) -> Path:
    output_path = resolve_phase3_surface_path(output_dir, surface_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def phase3_surface_exists(output_dir: Path, surface_name: str) -> bool:
    if (output_dir / surface_name).exists():
        return True
    return resolve_phase3_surface_path(output_dir, surface_name).exists()


def surface_profile_summary(surface_names: Iterable[str]) -> dict[str, float | int]:
    names = set(surface_names)
    moved_surfaces = names.intersection(DEWEIGHTED_PHASE3_DIAGNOSTIC_SURFACES).union(
        names.intersection(DEWEIGHTED_PHASE3_REVIEW_SURFACES)
    )
    root_count_before = len(names)
    root_reduction_count = len(moved_surfaces)
    root_count_after = root_count_before - root_reduction_count
    root_reduction_ratio = root_reduction_count / root_count_before if root_count_before else 0.0
    return {
        "root_count_before": root_count_before,
        "root_count_after": root_count_after,
        "root_reduction_count": root_reduction_count,
        "root_reduction_ratio": root_reduction_ratio,
    }
