from __future__ import annotations

from pathlib import Path


class CrossPhaseSurfacePolicyError(ValueError):
    """Raised when a surface movement would hide protected phase evidence."""


PROTECTED_CROSS_PHASE_SURFACES: dict[str, frozenset[str]] = {
    "phase1": frozenset(
        {
            "phase1-business-release-truth-pack.json",
            "phase1-planning-control-truth-pack.json",
            "phase1-business-world-model.json",
            "phase1-product-world-decision.json",
            "phase1-operating-baseline-model.json",
            "domain-assumption-and-evidence-ledger.md",
            "phase-verdict.json",
            "phase-mainline-scorecard.md",
            "phase-acceptance-matrix.md",
            "phase1-depth-runtime-summary.json",
            "phase1-prd-excellence-regression.json",
            "phase1-prd-excellence-regression.md",
        }
    ),
    "phase2": frozenset(
        {
            "engineering-spec-pack.md",
            "phase-3-implementation-entry.md",
            "baseline-lock.json",
            "phase-verdict.json",
            "phase-mainline-scorecard.md",
            "phase-acceptance-matrix.md",
        }
    ),
    "phase4": frozenset(
        {
            "phase4-delivery-gate.json",
            "phase4-quality-check.json",
            "phase4-run-metadata.json",
            "phase-verdict.json",
            "phase-mainline-scorecard.md",
            "phase-acceptance-matrix.md",
        }
    ),
}


PROFILED_CROSS_PHASE_SURFACES: dict[str, dict[str, str]] = {
    "phase1": {
        "phase1-convergence-gates-draft.json": ".phase1-evidence/phase1-convergence-gates-draft.json",
        "phase1-convergence-gates-final.json": ".phase1-evidence/phase1-convergence-gates-final.json",
        "phase-1-traceability-report.json": ".phase1-evidence/phase-1-traceability-report.json",
        "phase1-runtime-snapshot.json": ".phase1-diagnostics/phase1-runtime-snapshot.json",
        "phase1-timing-report.json": ".phase1-diagnostics/phase1-timing-report.json",
        "phase1-material-library-coverage-audit.md": ".phase1-diagnostics/phase1-material-library-coverage-audit.md",
        "phase1-material-library-coverage-audit.json": ".phase1-diagnostics/phase1-material-library-coverage-audit.json",
        "phase1-skill-family-audit.txt": ".phase1-diagnostics/phase1-skill-family-audit.txt",
        "phase-1-traceability-report.txt": ".phase1-diagnostics/phase-1-traceability-report.txt",
        "phase-1-traceability-validation.txt": ".phase1-diagnostics/phase-1-traceability-validation.txt",
    },
    "phase2": {
        "quality-check-report.json": ".phase2-evidence/quality-check-report.json",
        "phase-2-traceability-report.json": ".phase2-evidence/phase-2-traceability-report.json",
        "phase-1-to-phase-2-coverage.json": ".phase2-evidence/phase-1-to-phase-2-coverage.json",
        "cross-stage-consistency.json": ".phase2-evidence/cross-stage-consistency.json",
        "operation-source-obligation-matrix.json": ".phase2-evidence/operation-source-obligation-matrix.json",
        "operation-design-source-registry.json": ".phase2-evidence/operation-design-source-registry.json",
        "operation-behavior-semantics.json": ".phase2-evidence/operation-behavior-semantics.json",
        "p1-value-to-p2-operation-resolution-matrix.json": (
            ".phase2-evidence/p1-value-to-p2-operation-resolution-matrix.json"
        ),
        "implementation-depth-obligation-matrix.json": ".phase2-evidence/implementation-depth-obligation-matrix.json",
        "implementation-component-catalog.json": ".phase2-evidence/implementation-component-catalog.json",
        "component-action-card-obligation-matrix.json": (
            ".phase2-evidence/component-action-card-obligation-matrix.json"
        ),
        "phase-2-phase1-trace-resolution.json": ".phase2-evidence/phase-2-phase1-trace-resolution.json",
        "mermaid-validation-report.json": ".phase2-evidence/mermaid-validation-report.json",
        "phase-2-complexity-classification.json": ".phase2-evidence/phase-2-complexity-classification.json",
        "phase2-timing-report.json": ".phase2-diagnostics/phase2-timing-report.json",
        "phase-2-first-version-generation-report.json": (
            ".phase2-diagnostics/phase-2-first-version-generation-report.json"
        ),
        "phase-2-first-pass-audit.json": ".phase2-diagnostics/phase-2-first-pass-audit.json",
        "phase-2-first-pass-generation-manifest.md": ".phase2-diagnostics/phase-2-first-pass-generation-manifest.md",
        "phase-2-traceability-report.txt": ".phase2-diagnostics/phase-2-traceability-report.txt",
        "phase-2-traceability-validation.txt": ".phase2-diagnostics/phase-2-traceability-validation.txt",
        "phase2-full-trial-timing-report.json": ".phase2-diagnostics/phase2-full-trial-timing-report.json",
    },
    "phase4": {
        "phase4-output-contract-report.json": ".phase4-contract/phase4-output-contract-report.json",
        "phase4-output-contract-report.md": ".phase4-review/phase4-output-contract-report.md",
    },
}


OPTIONAL_LANE_CROSS_PHASE_SURFACES: dict[str, frozenset[str]] = {
    "phase1": frozenset(),
    "phase2": frozenset(),
    "phase4": frozenset(
        {
            "stage4-release-readiness-contract-report.json",
            "stage4-release-readiness-contract-report.md",
        }
    ),
}


def normalize_phase(phase: str) -> str:
    normalized = phase.strip().lower().replace("-", "")
    aliases = {
        "p1": "phase1",
        "phase1": "phase1",
        "phase01": "phase1",
        "p2": "phase2",
        "phase2": "phase2",
        "phase02": "phase2",
        "p4": "phase4",
        "phase4": "phase4",
        "phase04": "phase4",
    }
    if normalized not in aliases:
        raise CrossPhaseSurfacePolicyError(f"unsupported phase for cross-phase surface policy: {phase!r}")
    return aliases[normalized]


def classify_cross_phase_surface(phase: str, surface_name: str) -> str:
    normalized_phase = normalize_phase(phase)
    if surface_name in PROTECTED_CROSS_PHASE_SURFACES[normalized_phase]:
        return "protected"
    if surface_name in PROFILED_CROSS_PHASE_SURFACES[normalized_phase]:
        return "profile-candidate"
    if surface_name in OPTIONAL_LANE_CROSS_PHASE_SURFACES[normalized_phase]:
        return "optional-lane"
    return "keep-root"


def surface_may_be_removed(phase: str, surface_name: str) -> bool:
    return classify_cross_phase_surface(phase, surface_name) not in {"protected", "keep-root", "optional-lane"}


def surface_may_be_optionalized(phase: str, surface_name: str) -> bool:
    return classify_cross_phase_surface(phase, surface_name) == "optional-lane"


def resolve_cross_phase_surface_path(output_dir: Path, phase: str, surface_name: str) -> Path:
    normalized_phase = normalize_phase(phase)
    profiled = PROFILED_CROSS_PHASE_SURFACES[normalized_phase].get(surface_name)
    if profiled:
        return output_dir / profiled
    return output_dir / surface_name


def find_cross_phase_surface_path(output_dir: Path, phase: str, surface_name: str) -> Path:
    root_path = output_dir / surface_name
    if root_path.exists():
        return root_path
    return resolve_cross_phase_surface_path(output_dir, phase, surface_name)


def write_cross_phase_profiled_surface(output_dir: Path, phase: str, surface_name: str, content: str) -> Path:
    if classify_cross_phase_surface(phase, surface_name) != "profile-candidate":
        raise CrossPhaseSurfacePolicyError(f"{normalize_phase(phase)} surface is not approved for profile movement: {surface_name}")
    output_path = resolve_cross_phase_surface_path(output_dir, phase, surface_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def phase_surface_exists(output_dir: Path, phase: str, surface_name: str) -> bool:
    return (output_dir / surface_name).exists() or resolve_cross_phase_surface_path(output_dir, phase, surface_name).exists()
