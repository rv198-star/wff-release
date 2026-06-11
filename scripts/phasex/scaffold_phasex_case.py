#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
from pathlib import Path


PROFILE_OUTPUTS = {
    "assessment-only": [
        (
            "PX-SK-01",
            "px-sk-01-codebase-baseline-extraction.md",
            "PX-SK-01: codebase-baseline-extraction",
            "reference-packages/phasex-brownfield-refactoring/px-sk-01-codebase-baseline-extraction/output-template.md",
        ),
        (
            "PX-SK-04",
            "px-sk-04-technical-health-assessment.md",
            "PX-SK-04: technical-health-assessment",
            "reference-packages/phasex-brownfield-refactoring/px-sk-04-technical-health-assessment/output-template.md",
        ),
    ],
    "technical-refactor": [
        (
            "PX-SK-01",
            "px-sk-01-codebase-baseline-extraction.md",
            "PX-SK-01: codebase-baseline-extraction",
            "reference-packages/phasex-brownfield-refactoring/px-sk-01-codebase-baseline-extraction/output-template.md",
        ),
        (
            "PX-SK-04",
            "px-sk-04-technical-health-assessment.md",
            "PX-SK-04: technical-health-assessment",
            "reference-packages/phasex-brownfield-refactoring/px-sk-04-technical-health-assessment/output-template.md",
        ),
        (
            "PX-SK-07",
            "px-sk-07-safety-net-test-construction.md",
            "PX-SK-07: safety-net-test-construction",
            "reference-packages/phasex-brownfield-refactoring/px-sk-07-safety-net-test-construction/output-template.md",
        ),
    ],
    "partial-change": [
        (
            "PX-SK-01",
            "px-sk-01-codebase-baseline-extraction.md",
            "PX-SK-01: codebase-baseline-extraction",
            "reference-packages/phasex-brownfield-refactoring/px-sk-01-codebase-baseline-extraction/output-template.md",
        ),
        (
            "PX-SK-06",
            "px-sk-06-gap-analysis-and-change-decomposition-partial.md",
            "PX-SK-06: gap-analysis-and-change-decomposition (partial)",
            "reference-packages/phasex-brownfield-refactoring/px-sk-06-gap-analysis-and-change-decomposition-partial/output-template.md",
        ),
    ],
}

PROFILE_RULES = {
    "assessment-only": {
        "path": "`PX-SK-01 -> PX-SK-04`",
        "typical_exit": "human decision / continue later",
    },
    "technical-refactor": {
        "path": "`PX-SK-01 -> PX-SK-04 -> PX-SK-07`",
        "typical_exit": "Phase-3 brownfield implementation",
    },
    "partial-change": {
        "path": "`PX-SK-01 -> PX-SK-06 partial`",
        "typical_exit": "Phase-1 constrained re-entry or direct Phase-3",
    },
}

PROFILE_METHOD_BACKBONES = {
    "assessment-only": [
        "`docs/internal/source-registers/phaseX-source-library-seed-v0.1.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/index-map.md`",
    ],
    "technical-refactor": [
        "`docs/internal/source-registers/phaseX-source-library-seed-v0.1.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/define-refactoring-by-behavior-preservation-and-change-cost.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/two-hats-separate-feature-work-from-refactoring-work.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/refactor-requires-self-testing-tests-and-fast-feedback-loop.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/branch-by-abstraction-for-long-running-refactors.md`",
        "`sources/books/extracted/the-art-of-unit-testing/stage-guidance-draft.md`",
    ],
    "partial-change": [
        "`docs/internal/source-registers/phaseX-source-library-seed-v0.1.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/define-refactoring-by-behavior-preservation-and-change-cost.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/two-hats-separate-feature-work-from-refactoring-work.md`",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a PhaseX Wave-1 brownfield case root."
    )
    parser.add_argument(
        "--system-root",
        required=True,
        help="Path to the existing system or brownfield repository root.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Target PhaseX case directory, for example tmp/local-artifacts/<case>/phase-x.",
    )
    parser.add_argument(
        "--profile",
        required=True,
        choices=sorted(PROFILE_OUTPUTS.keys()),
        help="PhaseX Wave-1 profile to scaffold.",
    )
    parser.add_argument("--case-name", help="Optional case name override.")
    parser.add_argument("--version", default="v-next", help="Case version label.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into an existing non-empty output directory.",
    )
    return parser.parse_args()


def ensure_output_dir(path: Path, force: bool) -> None:
    if path.exists() and any(path.iterdir()) and not force:
        raise SystemExit(
            f"Refusing to scaffold into non-empty directory: {path}\n"
            "Use --force only when you explicitly want to refresh PhaseX target files."
        )
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def infer_case_name(output_dir: Path) -> str:
    if output_dir.name.startswith("phase-x") and output_dir.parent.name:
        return output_dir.parent.name
    return output_dir.name


def build_manifest(
    *,
    case_name: str,
    version: str,
    system_root: Path,
    output_dir: Path,
    profile: str,
) -> str:
    lines = [
        "# PhaseX Wave-1 Manifest",
        "",
        "## Identity",
        "",
        f"- case_name: `{case_name}`",
        f"- version: `{version}`",
        f"- system_root: `{system_root}`",
        f"- output_dir: `{output_dir}`",
        f"- selected_profile: `{profile}`",
        "",
        "## Official Entry",
        "",
        "- skill: `skills/wff-x/`",
        "- bootstrap: `docs/phases/phase-x/phaseX-session-bootstrap.md`",
        "- decision_tree: `docs/phases/phase-x/phaseX-wave1-profile-decision-tree-v0.1.md`",
        "- stage_family: `reference-packages/phasex-brownfield-refactoring/`",
        "",
        "## Profile Rule",
        "",
        f"- execution_path: {PROFILE_RULES[profile]['path']}",
        f"- typical_exit: {PROFILE_RULES[profile]['typical_exit']}",
        "",
        "## Brownfield Boundary",
        "",
        "- Keep current-state truth separate from target-state recommendation.",
        "- Do not silently widen a bounded slice into a full-system redesign.",
        "- Record uncertainty explicitly when the repository does not expose enough evidence.",
        "- If the case no longer fits a Wave-1 profile honestly, stop and re-plan instead of fake-fitting it.",
        "",
        "## Method Backbone",
        "",
    ]

    for item in PROFILE_METHOD_BACKBONES[profile]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
        "## Required Outputs",
        "",
        ]
    )

    for _, filename, title, _ in PROFILE_OUTPUTS[profile]:
        lines.append(f"- `{filename}`: authored target for {title}")

    lines.extend(
        [
            "- `phasex-wave1-manifest.md`: profile and boundary record for this case root",
            "",
            "## Authoring Order",
            "",
        ]
    )
    for index, (_, _, title, _) in enumerate(PROFILE_OUTPUTS[profile], start=1):
        lines.append(f"{index}. {title}")
    lines.extend(
        [
            "",
            "## Downstream Intent",
            "",
            "- `assessment-only`: decide whether more work is justified",
            "- `technical-refactor`: protect brownfield change before implementation",
            "- `partial-change`: package the bounded change for Phase-1 or Phase-3 consumption",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def build_skill_stub(
    *,
    skill_id: str,
    skill_title: str,
    template_path: str,
    system_root: Path,
    output_dir: Path,
    filename: str,
    profile: str,
) -> str:
    return "\n".join(
        [
            f"# {skill_title}",
            "",
            "## Status",
            "",
            "- state: `fresh-target`",
            "- authoring_mode: `derive-from-brownfield-system-and-official-wave-1-pack`",
            f"- selected_profile: `{profile}`",
            "",
            "## Inputs",
            "",
            f"- system_root: `{system_root}`",
            f"- official_template: `{template_path}`",
            f"- case_root: `{output_dir}`",
            "",
            "## Rules",
            "",
            "- Treat the existing system as the source of current-state truth.",
            "- Do not copy earlier PhaseX case prose as if it were current evidence.",
            "- Keep observed facts, inferences, and recommendations clearly separated.",
            "- If evidence is too thin, record uncertainty instead of broadening scope to fake completeness.",
            "",
            "## Next Step",
            "",
            "- Replace this stub with a complete Wave-1 output for the selected profile.",
            "",
            f"<!-- scaffolded_target: {filename} -->",
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    system_root = Path(args.system_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    case_name = args.case_name or infer_case_name(output_dir)

    ensure_output_dir(output_dir, args.force)

    write_text(
        output_dir / "phasex-wave1-manifest.md",
        build_manifest(
            case_name=case_name,
            version=args.version,
            system_root=system_root,
            output_dir=output_dir,
            profile=args.profile,
        ),
    )

    for skill_id, filename, skill_title, template_path in PROFILE_OUTPUTS[args.profile]:
        write_text(
            output_dir / filename,
            build_skill_stub(
                skill_id=skill_id,
                skill_title=skill_title,
                template_path=template_path,
                system_root=system_root,
                output_dir=output_dir,
                filename=filename,
                profile=args.profile,
            ),
        )


if __name__ == "__main__":
    main()
