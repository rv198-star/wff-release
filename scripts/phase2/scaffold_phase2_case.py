#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
from pathlib import Path


STAGE_FILES = {
    "stage-01-architecture-definition-and-boundary-setting.md": "Stage-01: architecture-definition-and-boundary-setting",
    "stage-02-domain-module-service-decomposition.md": "Stage-02: domain-module-service-decomposition",
    "stage-03-data-storage-and-interface-design.md": "Stage-03: data-storage-and-interface-design",
    "stage-04-design-convergence-and-delivery-prototype.md": "Stage-04: design-convergence-and-delivery-prototype",
}

OPTIONAL_STAGE_FILE = {
    "stage-02.5-third-party-integration-architecture-design.md": "Stage-02.5: third-party-integration-architecture-design",
}

STAGE_TEMPLATE_PATHS = {
    "stage-01-architecture-definition-and-boundary-setting.md": "reference-packages/phase2-design-architecture/stage-01-architecture-definition-and-boundary-setting/output-template.md",
    "stage-02-domain-module-service-decomposition.md": "reference-packages/phase2-design-architecture/stage-02-domain-module-service-decomposition/output-template.md",
    "stage-03-data-storage-and-interface-design.md": "reference-packages/phase2-design-architecture/stage-03-data-storage-and-interface-design/output-template.md",
    "stage-04-design-convergence-and-delivery-prototype.md": "reference-packages/phase2-design-architecture/stage-04-design-convergence-and-delivery-prototype/output-template.md",
}

OPTIONAL_STAGE_TEMPLATE_PATHS = {
    "stage-02.5-third-party-integration-architecture-design.md": "reference-packages/phase2-design-architecture/stage-02.5-third-party-integration-design/output-template.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a fresh Phase-2 case root for first-pass generation."
    )
    parser.add_argument("--phase1-prd", required=True, help="Path to the Phase-1 PRD.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Target Phase-2 case directory, for example tmp/local-artifacts/<case>/phase-2-v6.",
    )
    parser.add_argument("--case-name", help="Optional case name override.")
    parser.add_argument("--version", default="v-next", help="Case version label.")
    parser.add_argument(
        "--pure-prd-direct",
        action="store_true",
        help="Mark this scaffold as a pure Phase-1 PRD direct first-pass baseline with stricter provenance rules.",
    )
    parser.add_argument(
        "--with-stage-02-5",
        action="store_true",
        help="Also scaffold the optional Stage-02.5 third-party integration lane.",
    )
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
            "Use --force only when you explicitly want to overwrite or refresh stub targets."
        )
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def infer_case_name(output_dir: Path) -> str:
    if output_dir.name.startswith("phase-2") and output_dir.parent.name:
        return output_dir.parent.name
    return output_dir.name


def build_manifest(
    case_name: str,
    version: str,
    phase1_prd: Path,
    output_dir: Path,
    pure_prd_direct: bool = False,
    with_stage_02_5: bool = False,
) -> str:
    lines = [
        "# Phase-2 First-Pass Generation Manifest",
        "",
        "## Identity",
        "",
        f"- case_name: `{case_name}`",
        f"- version: `{version}`",
        f"- phase1_prd: `{phase1_prd}`",
        f"- output_dir: `{output_dir}`",
        "",
        "## Fresh First-Pass Rule",
        "",
        "- This case root is scaffolded for first-pass Phase-2 generation.",
        "- Do not copy prior Phase-2 prose into the Stage outputs and relabel it as a new version.",
        "- Re-derive Stage-01..04 from Phase-1 authority inputs plus the official Phase-2 stage packs.",
        "- If an earlier Phase-2 case is consulted, record it as a sidecar reference and restate any reused claim with fresh evidence.",
        "",
        "## Required Inputs",
        "",
    ]
    if pure_prd_direct:
        lines.extend(
            [
                "- Phase-1 PRD main document only",
                "- Official Phase-2 stage package templates and source cards",
                "",
                "## Generation Purity Contract",
                "",
                "- generation_mode: `phase1-prd-direct-fresh-first-pass`",
                "- authority_input_mode: `phase1_prd_main_only`",
                "- prohibited_as_authority_inputs:",
                "  - prior Phase-2 Stage outputs",
                "  - prior Phase-2 execution reports / ESP / implementation entry",
                "  - supplemental Phase-1 prototype spec",
                "  - supplemental Phase-1 execution report",
                "- purity_rule:",
                "  - this version is the direct baseline derived from the Phase-1 PRD, not a patched carry-forward from earlier Phase-2 versions",
                "- version_freeze_rule:",
                "  - once this baseline is authored and wrapped, any later content fixes must move to a new rerun or follow-up version label such as `v8-r1`, not overwrite the pure baseline",
                "",
                "## Expected Outputs",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "- Phase-1 PRD main document",
                "- Phase-1 prototype spec when available",
                "- Phase-1 execution report when available",
                "- Official Phase-2 stage package templates and source cards",
                "",
                "## Expected Outputs",
                "",
            ]
        )
    for filename, stage_name in STAGE_FILES.items():
        lines.append(f"- `{filename}`: fresh authored output for {stage_name}")
    if with_stage_02_5:
        for filename, stage_name in OPTIONAL_STAGE_FILE.items():
            lines.append(f"- `{filename}`: optional authored output for {stage_name} when third-party integration design is active")
    lines.extend(
        [
            "- `phase-2-execution-report.md` after Stage-01..04 are authored",
            "- `engineering-spec-pack.md` after the wrapper run",
            "- `phase-3-implementation-entry.md` after the wrapper run",
            "",
            "## Authoring Order",
            "",
            "1. Stage-01",
            "2. Stage-02",
            "3. Stage-02.5 (optional, when third-party integration design is active)",
            "4. Stage-03",
            "5. Stage-04",
            "6. `scripts/phase2/run_phase2_full_trial.py`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def build_stage_stub(
    stage_name: str,
    template_path: str,
    phase1_prd: Path,
    output_dir: Path,
    filename: str,
    pure_prd_direct: bool = False,
) -> str:
    authoring_mode = (
        "derive-directly-from-phase1-prd-and-official-stage-pack"
        if pure_prd_direct
        else "derive-from-phase1-and-official-stage-pack"
    )
    return "\n".join(
        [
            f"# {stage_name}",
            "",
            "## Status",
            "",
            "- state: `fresh-first-pass-target`",
            f"- authoring_mode: `{authoring_mode}`",
            "",
            "## Inputs",
            "",
            f"- phase1_prd: `{phase1_prd}`",
            f"- official_template: `{template_path}`",
            f"- case_root: `{output_dir}`",
            "",
            "## Rules",
            "",
            "- Do not copy prior Phase-2 case prose into this file.",
            "- Re-derive all claims from Phase-1 authority inputs plus the official stage package.",
            "- If a previous Phase-2 case is consulted as a comparison, log it in the authored output as a sidecar reference rather than a baseline source of truth.",
            *(
                [
                    "- Pure PRD direct mode is active: treat the Phase-1 PRD main document as the only authority input.",
                    "- Do not use prior Phase-2 outputs, Phase-1 prototype spec, or Phase-1 execution report as baseline content sources.",
                    "- If later optimization is needed after this baseline is authored, create a new rerun/follow-up version instead of patching this direct baseline in place.",
                ]
                if pure_prd_direct
                else []
            ),
            "",
            "## Next Step",
            "",
            "- Replace this stub with a complete Stage output that satisfies the current Phase-2 gates.",
            "",
            f"<!-- scaffolded_target: {filename} -->",
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    phase1_prd = Path(args.phase1_prd).resolve()
    output_dir = Path(args.output_dir).resolve()
    case_name = args.case_name or infer_case_name(output_dir)

    ensure_output_dir(output_dir, args.force)

    manifest_path = output_dir / "phase-2-first-pass-generation-manifest.md"
    write_text(
        manifest_path,
        build_manifest(
            case_name=case_name,
            version=args.version,
            phase1_prd=phase1_prd,
            output_dir=output_dir,
            pure_prd_direct=args.pure_prd_direct,
            with_stage_02_5=args.with_stage_02_5,
        ),
    )

    for filename, stage_name in STAGE_FILES.items():
        stub_path = output_dir / filename
        write_text(
            stub_path,
            build_stage_stub(
                stage_name=stage_name,
                template_path=STAGE_TEMPLATE_PATHS[filename],
                phase1_prd=phase1_prd,
                output_dir=output_dir,
                filename=filename,
                pure_prd_direct=args.pure_prd_direct,
            ),
        )

    if args.with_stage_02_5:
        for filename, stage_name in OPTIONAL_STAGE_FILE.items():
            stub_path = output_dir / filename
            write_text(
                stub_path,
                build_stage_stub(
                    stage_name=stage_name,
                    template_path=OPTIONAL_STAGE_TEMPLATE_PATHS[filename],
                    phase1_prd=phase1_prd,
                    output_dir=output_dir,
                    filename=filename,
                    pure_prd_direct=args.pure_prd_direct,
                ),
            )

    print(f"Scaffolded fresh Phase-2 case at: {output_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
