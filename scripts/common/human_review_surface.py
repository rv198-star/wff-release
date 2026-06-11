#!/usr/bin/env python3
"""Generate a human-review surface without moving canonical WFF artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HUMAN_REVIEW_DIRNAME = "human-review"
ARTIFACTS_DIRNAME = "artifacts"


@dataclass(frozen=True)
class HumanReviewArtifactRule:
    label: str
    source: str
    category: str
    optional: bool = True
    note: str = ""


@dataclass(frozen=True)
class HumanReviewSurfaceConfig:
    phase: str
    title: str
    primary_instruction: str
    artifact_rules: tuple[HumanReviewArtifactRule, ...]
    machine_dirs: tuple[str, ...]
    claim_ceiling_notes: tuple[str, ...]


CATEGORY_LABELS = {
    "primary": "human primary read",
    "gate": "gate / verdict",
    "review": "review / trace support",
}


SURFACE_CONFIGS: dict[str, HumanReviewSurfaceConfig] = {
    "phase1": HumanReviewSurfaceConfig(
        phase="phase1",
        title="Phase-1 Human Review",
        primary_instruction="Start with the PRD and phase verdict, then inspect review-bound gaps before downstream design.",
        artifact_rules=(
            HumanReviewArtifactRule("PRD main document", "phase-1-product-requirements-document-main-document.md", "primary", False),
            HumanReviewArtifactRule("Chosen business thesis", "chosen-business-thesis.md", "primary"),
            HumanReviewArtifactRule("Phase-1 execution report", "phase-1-execution-report.md", "gate"),
            HumanReviewArtifactRule("Phase mainline scorecard", "phase-mainline-scorecard.md", "gate"),
            HumanReviewArtifactRule("Phase acceptance matrix", "phase-acceptance-matrix.md", "gate"),
            HumanReviewArtifactRule("Phase verdict", "phase-verdict.json", "gate"),
            HumanReviewArtifactRule("Domain assumption and evidence ledger", "domain-assumption-and-evidence-ledger.md", "review"),
            HumanReviewArtifactRule("Demo risk review", "demo-risk-review.md", "review"),
        ),
        machine_dirs=(".phase1-diagnostics", ".phase1-evidence", ".trace"),
        claim_ceiling_notes=(
            "P1 can support downstream demand/design entry only inside the stated evidence boundary.",
            "P1 does not prove production approval, budget approval, owner sign-off, real UAT, or production risk acceptance.",
        ),
    ),
    "phase2": HumanReviewSurfaceConfig(
        phase="phase2",
        title="Phase-2 Human Review",
        primary_instruction="Start with the Engineering Spec Pack and Phase-3 implementation entry, then inspect gates and review-bound architecture gaps.",
        artifact_rules=(
            HumanReviewArtifactRule("Engineering Spec Pack", "engineering-spec-pack.md", "primary", False),
            HumanReviewArtifactRule("Phase-3 implementation entry", "phase-3-implementation-entry.md", "primary"),
            HumanReviewArtifactRule("Existing-system architecture change intake", "existing-system-architecture-change-intake.md", "primary"),
            HumanReviewArtifactRule("Phase-2 execution report", "phase-2-execution-report.md", "gate"),
            HumanReviewArtifactRule("Phase mainline scorecard", "phase-mainline-scorecard.md", "gate"),
            HumanReviewArtifactRule("Phase acceptance matrix", "phase-acceptance-matrix.md", "gate"),
            HumanReviewArtifactRule("Phase verdict", "phase-verdict.json", "gate"),
            HumanReviewArtifactRule("Baseline lock", "baseline-lock.json", "review"),
        ),
        machine_dirs=(".phase2-diagnostics", ".phase2-evidence", ".trace"),
        claim_ceiling_notes=(
            "P2 constrains implementation and architecture decisions; it does not prove generated implementation quality.",
            "Architecture facts inherited from PX or P1 remain review-bound unless the source evidence closes them.",
        ),
    ),
    "phase3": HumanReviewSurfaceConfig(
        phase="phase3",
        title="Phase-3 Human Review",
        primary_instruction="Start with action cards, execution/acceptance reports, and delivery gates before reading code or raw evidence.",
        artifact_rules=(
            HumanReviewArtifactRule("Action cards", "action-cards/*-action-card.md", "primary"),
            HumanReviewArtifactRule("Phase-3 execution report", "phase-3-execution-report.md", "gate"),
            HumanReviewArtifactRule("Phase-3 acceptance report", "phase-3-acceptance-report.md", "gate"),
            HumanReviewArtifactRule("Phase mainline scorecard", "phase-mainline-scorecard.md", "gate"),
            HumanReviewArtifactRule("Phase acceptance matrix", "phase-acceptance-matrix.md", "gate"),
            HumanReviewArtifactRule("Phase verdict", "phase-verdict.json", "gate"),
            HumanReviewArtifactRule("Delivery gate", "phase3-delivery-gate.json", "gate"),
            HumanReviewArtifactRule("Code review report", ".phase3-review/code-review-report.md", "review"),
            HumanReviewArtifactRule("Security audit report", ".phase3-review/security-audit-report.md", "review"),
            HumanReviewArtifactRule("Test obligation matrix", ".phase3-review/test-obligation-matrix.md", "review"),
            HumanReviewArtifactRule("Test richness review", ".phase3-review/test-richness-review.md", "review"),
            HumanReviewArtifactRule("Implementation bindings", "implementation-bindings.json", "review"),
            HumanReviewArtifactRule("Final trace registry", "phase-3-trace-registry-final.json", "review"),
        ),
        machine_dirs=(".phase3-diagnostics", "apps", "packages", "tests", "db", "contracts", "work-packages"),
        claim_ceiling_notes=(
            "P3 delivery-ready is bounded by development / pre-production runtime evidence.",
            "P3 does not prove production readiness, real UAT, owner sign-off, capacity proof, or production risk acceptance.",
        ),
    ),
    "phase4": HumanReviewSurfaceConfig(
        phase="phase4",
        title="Phase-4 Human Review",
        primary_instruction="Start with closure judgment, delivery gate, and downstream boundary notes before raw evidence details.",
        artifact_rules=(
            HumanReviewArtifactRule(
                "Validation closure judgment",
                "stage-03-validation-closure-and-delivery-readiness-judgment/test-closure-judgment.md",
                "primary",
            ),
            HumanReviewArtifactRule(
                "Downstream boundary note",
                "stage-03-validation-closure-and-delivery-readiness-judgment/downstream-boundary-note.md",
                "primary",
            ),
            HumanReviewArtifactRule(
                "Testing-validation planning package",
                "stage-01-acceptance-coverage-planning/testing-validation-planning-package.md",
                "primary",
            ),
            HumanReviewArtifactRule(
                "Test execution evidence",
                "stage-02-evidence-execution-and-defect-identification/test-execution-evidence.md",
                "primary",
            ),
            HumanReviewArtifactRule("Phase-4 delivery gate", "phase4-delivery-gate.json", "gate"),
            HumanReviewArtifactRule("Phase mainline scorecard", "phase-mainline-scorecard.md", "gate"),
            HumanReviewArtifactRule("Phase acceptance matrix", "phase-acceptance-matrix.md", "gate"),
            HumanReviewArtifactRule("Phase verdict", "phase-verdict.json", "gate"),
            HumanReviewArtifactRule("Output contract report", ".phase4-review/phase4-output-contract-report.md", "review"),
            HumanReviewArtifactRule(
                "Review-bound record",
                "stage-02-evidence-execution-and-defect-identification/review-bound-record.json",
                "review",
            ),
            HumanReviewArtifactRule(
                "Defect record",
                "stage-02-evidence-execution-and-defect-identification/defect-record.json",
                "review",
            ),
        ),
        machine_dirs=(".phase4-contract", ".phase4-review", "stage-01-acceptance-coverage-planning", "stage-02-evidence-execution-and-defect-identification", "stage-03-validation-closure-and-delivery-readiness-judgment"),
        claim_ceiling_notes=(
            "P4 judges evidence sufficiency and routing under a claim ceiling; it is not production approval.",
            "Missing external owner / UAT / production evidence must remain explicit instead of being inferred from green gates.",
        ),
    ),
    "phasex": HumanReviewSurfaceConfig(
        phase="phasex",
        title="PhaseX Human Review",
        primary_instruction="Start with the Wave-1 manifest, then read the selected scan / health / handoff outputs for facts, inferences, unknowns, and route decisions.",
        artifact_rules=(
            HumanReviewArtifactRule("PhaseX manifest", "phasex-wave1-manifest.md", "primary", False),
            HumanReviewArtifactRule("Code baseline", "wff-x-scan-code-baseline.md", "primary"),
            HumanReviewArtifactRule("DB baseline", "wff-x-scan-db-baseline.md", "primary"),
            HumanReviewArtifactRule("Business architecture scan", "wff-x-scan-biz-arch.md", "primary"),
            HumanReviewArtifactRule("Tech health", "wff-x-scan-tech-health.md", "primary"),
            HumanReviewArtifactRule("Test protection plan", "wff-x-plan-test-protection.md", "primary"),
            HumanReviewArtifactRule("Target-driver intake", "wff-x-intake-target-driver.md", "primary"),
        ),
        machine_dirs=(),
        claim_ceiling_notes=(
            "PX separates observed system facts, Agentic inference, unknowns, and route recommendations.",
            "PX does not prove production migration safety or arbitrary brownfield-system quality without fresh evidence and review.",
        ),
    ),
}

PHASE_ALIASES = {
    "p1": "phase1",
    "phase1": "phase1",
    "phase-1": "phase1",
    "p2": "phase2",
    "phase2": "phase2",
    "phase-2": "phase2",
    "p3": "phase3",
    "phase3": "phase3",
    "phase-3": "phase3",
    "p4": "phase4",
    "phase4": "phase4",
    "phase-4": "phase4",
    "px": "phasex",
    "phasex": "phasex",
    "phase-x": "phasex",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_phase(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if key not in PHASE_ALIASES:
        raise ValueError(f"unsupported human-review phase: {raw!r}")
    return PHASE_ALIASES[key]


def is_reader_sidecar(path: Path) -> bool:
    name = path.name
    return ".reader." in name or name.endswith(".integrity.json") or name.endswith(".progress.jsonl")


def reader_path_for(canonical: Path) -> Path | None:
    if canonical.suffix.lower() != ".md":
        return None
    return canonical.with_name(f"{canonical.stem}.reader.zh-CN.md")


def select_human_read_source(canonical: Path) -> tuple[Path, str]:
    reader_path = reader_path_for(canonical)
    if reader_path and reader_path.exists():
        return reader_path, "reader-translation"
    if canonical.suffix.lower() == ".md":
        return canonical, "canonical-fallback"
    return canonical, "canonical-evidence"


def expand_rule(output_dir: Path, rule: HumanReviewArtifactRule) -> list[Path]:
    if any(char in rule.source for char in "*?[]"):
        return sorted(
            path
            for path in output_dir.glob(rule.source)
            if path.is_file() and not is_reader_sidecar(path)
        )
    path = output_dir / rule.source
    return [path] if path.exists() and path.is_file() else []


def clean_generated_artifacts_dir(surface_dir: Path) -> Path:
    artifacts_dir = surface_dir / ARTIFACTS_DIRNAME
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


def copy_selected_artifact(
    *,
    output_dir: Path,
    artifacts_dir: Path,
    canonical: Path,
    category: str,
) -> dict[str, Any]:
    selected, source_kind = select_human_read_source(canonical)
    try:
        selected_rel = selected.relative_to(output_dir)
    except ValueError:
        selected_rel = Path(selected.name)
    target = artifacts_dir / category / selected_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(selected, target)
    canonical_rel = canonical.relative_to(output_dir).as_posix()
    human_rel = target.relative_to(output_dir).as_posix()
    return {
        "canonical_path": canonical_rel,
        "selected_source_path": selected_rel.as_posix(),
        "human_review_path": human_rel,
        "source_kind": source_kind,
    }


def build_machine_dir_rows(output_dir: Path, config: HumanReviewSurfaceConfig) -> list[dict[str, Any]]:
    rows = []
    for raw in config.machine_dirs:
        path = output_dir / raw
        rows.append(
            {
                "path": raw,
                "exists": path.exists(),
                "meaning": "AI / gate working evidence; inspect when a primary artifact points here or a defect requires detail.",
            }
        )
    return rows


def emit_human_review_surface(output_dir: Path, phase: str) -> dict[str, Any]:
    normalized_phase = normalize_phase(phase)
    config = SURFACE_CONFIGS[normalized_phase]
    root = output_dir.resolve()
    surface_dir = root / HUMAN_REVIEW_DIRNAME
    surface_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = clean_generated_artifacts_dir(surface_dir)

    artifacts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for rule in config.artifact_rules:
        expanded = expand_rule(root, rule)
        if not expanded:
            missing.append(
                {
                    "label": rule.label,
                    "source": rule.source,
                    "category": rule.category,
                    "optional": rule.optional,
                    "note": rule.note,
                }
            )
            continue
        for canonical in expanded:
            copied = copy_selected_artifact(
                output_dir=root,
                artifacts_dir=artifacts_dir,
                canonical=canonical,
                category=rule.category,
            )
            key = (rule.label, copied["canonical_path"])
            if key in seen:
                continue
            seen.add(key)
            artifacts.append(
                {
                    "label": rule.label,
                    "category": rule.category,
                    "category_label": CATEGORY_LABELS.get(rule.category, rule.category),
                    "optional": rule.optional,
                    "note": rule.note,
                    **copied,
                }
            )

    machine_dirs = build_machine_dir_rows(root, config)
    manifest = {
        "schema_version": "human-review-surface.v1",
        "generated_at": utc_now_iso(),
        "phase": normalized_phase,
        "title": config.title,
        "surface_dir": HUMAN_REVIEW_DIRNAME,
        "primary_instruction": config.primary_instruction,
        "artifacts": artifacts,
        "missing_artifacts": missing,
        "machine_working_areas": machine_dirs,
        "claim_ceiling_notes": list(config.claim_ceiling_notes),
        "canonical_authority_note": (
            "human-review artifacts are copies for reading; canonical source artifacts remain at their original paths"
        ),
    }
    (surface_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (surface_dir / "INDEX.md").write_text(render_index(manifest), encoding="utf-8")
    return manifest


def render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    output.extend("| " + " | ".join(row) + " |" for row in rows)
    return output


def render_index(manifest: dict[str, Any]) -> str:
    lines = [
        f"# {manifest['title']}",
        "",
        "## How to Read",
        "",
        f"- {manifest['primary_instruction']}",
        "- Read `gate / verdict` items before treating any stage as closed.",
        "- Use copied files here for review convenience only; canonical source artifacts remain at their original paths.",
        "",
        "## Main Artifacts",
        "",
    ]

    artifact_rows = []
    for artifact in manifest["artifacts"]:
        artifact_rows.append(
            [
                str(artifact["label"]),
                str(artifact["category_label"]),
                f"`{artifact['human_review_path']}`",
                f"`{artifact['canonical_path']}`",
                str(artifact["source_kind"]),
            ]
        )
    lines.extend(render_table(["Artifact", "Kind", "Human copy", "Canonical source", "Source mode"], artifact_rows) or ["No artifacts copied."])

    required_missing = [item for item in manifest["missing_artifacts"] if not item.get("optional")]
    optional_missing = [item for item in manifest["missing_artifacts"] if item.get("optional")]
    if required_missing or optional_missing:
        lines.extend(["", "## Missing Or Not Generated", ""])
        missing_rows = [
            [
                str(item["label"]),
                f"`{item['source']}`",
                "optional" if item.get("optional") else "required",
            ]
            for item in [*required_missing, *optional_missing]
        ]
        lines.extend(render_table(["Artifact", "Expected source", "Status"], missing_rows))

    machine_rows = [
        [
            f"`{item['path']}`",
            "yes" if item["exists"] else "no",
            str(item["meaning"]),
        ]
        for item in manifest["machine_working_areas"]
    ]
    if machine_rows:
        lines.extend(["", "## AI / Gate Working Areas", ""])
        lines.extend(render_table(["Path", "Exists", "When to inspect"], machine_rows))

    lines.extend(["", "## Claim Ceiling", ""])
    for note in manifest["claim_ceiling_notes"]:
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Generated Surface Boundary",
            "",
            "- This directory is additive and reader-facing.",
            "- It must not replace phase contracts, trace registries, gates, or retained proof evidence.",
            "- Re-run the phase or `human_review_surface.py` after upstream artifacts change.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate WFF human-review artifact copies and INDEX.md.")
    parser.add_argument("--phase", required=True, choices=sorted(PHASE_ALIASES))
    parser.add_argument("--output-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = emit_human_review_surface(Path(args.output_dir), args.phase)
    print(json.dumps({"human_review_index": str(Path(args.output_dir) / HUMAN_REVIEW_DIRNAME / "INDEX.md"), "artifact_count": len(manifest["artifacts"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
