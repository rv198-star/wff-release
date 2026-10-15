#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import argparse

from common.agentic_decision_authority import load_json_object
from common.output_language import resolve_output_locale
from phase3.frontend_implementation_scaffolder import (
    FRONTEND_AUTHORING_SCHEMA,
    FrontendImplementationAuthoringError,
    scaffold_frontend_implementation,
)
from phase3.impl_context import emit_summary, write_json
from phase3.p3_realization_decisions import (
    persist_p3_realization_knowledge,
    resolve_project_artifact_root,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate or validate Phase-3 frontend capability artifacts")
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--project-artifact-root", default="")
    parser.add_argument("--authority-delta-ledger", default="")
    parser.add_argument("--title", default="Phase-3 Frontend")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--ui-ia-contract", default="")
    parser.add_argument(
        "--implementation-authority",
        default="",
        help=(
            "accepted p3-agentic-implementation-authority.json; when omitted, the current output-dir authority is used if present"
        ),
    )
    parser.add_argument(
        "--agentic-source-root",
        default="",
        help="optional same-decision frontend source root containing materialized @wff:agentic regions",
    )
    parser.add_argument("--frozen-input-decision", default="",
        help="P3 host decision over SHA-bound partial frozen P1/architecture/interaction inputs; retains review ceilings")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    return parser


def _blocked_summary(output_dir: Path, reason: str, *, ui_ia_contract: str = "") -> dict[str, object]:
    summary: dict[str, object] = {
        "artifact_kind": "phase3-impl-frontend-report",
        "quality_gate": "blocked",
        "ui_ia_contract": ui_ia_contract,
        "failures": [reason],
        "authoring": {
            "schema_version": FRONTEND_AUTHORING_SCHEMA,
            "mode": "complete-product-agentic-realization" if ui_ia_contract else "scaffold-only-compatibility",
            "status": "blocked",
            "semantic_authority": False,
            "runtime_evidence_refs": [],
            "trace_confirmed": False,
        },
        "claim_ceiling": "Frontend product realization is blocked; no consumer-journey runtime, Trace, P4, production, or UAT claim is created.",
    }
    write_json(output_dir / "impl-frontend-report.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    phase2_root = Path(args.phase2_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    project_artifact_root = resolve_project_artifact_root(
        phase2_root=phase2_root,
        output_dir=output_dir,
        explicit_root=Path(args.project_artifact_root).resolve()
        if str(args.project_artifact_root or "").strip()
        else None,
    )
    ui_path = Path(args.ui_ia_contract).resolve() if args.ui_ia_contract else None
    explicit_authority = str(args.implementation_authority or "").strip()
    authority_path = (
        Path(explicit_authority).resolve()
        if explicit_authority
        else (output_dir / "p3-agentic-implementation-authority.json").resolve()
    )
    authority = None
    if args.frozen_input_decision:
        if explicit_authority:
            return emit_summary(_blocked_summary(output_dir, "Choose one implementation decision input", ui_ia_contract=str(ui_path or "")))
        try:
            from phase3.frozen_input_admission import build_frozen_input_authority
            document = load_json_object(Path(args.frozen_input_decision).resolve())
            authority = build_frozen_input_authority(sources=document["sources"],
                fact_sources=document["fact_sources"], decision=document["decision"])
            if authority_path.exists() and load_json_object(authority_path) != authority:
                raise ValueError("Existing canonical implementation authority differs; retain its original decision")
            write_json(authority_path, authority)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return emit_summary(_blocked_summary(output_dir, f"Frozen-input P3 decision is unreadable: {exc}", ui_ia_contract=str(ui_path or "")))
    if authority_path.is_file() and not authority_path.is_symlink():
        try:
            authority = load_json_object(authority_path)
        except (OSError, ValueError) as exc:
            return emit_summary(
                _blocked_summary(output_dir, f"accepted P3 implementation authority is unreadable: {exc}", ui_ia_contract=str(ui_path or ""))
            )
    elif ui_path is not None:
        return emit_summary(
            _blocked_summary(
                output_dir,
                "requested frontend authoring requires accepted P3 implementation authority",
                ui_ia_contract=str(ui_path),
            )
        )

    realization_knowledge: dict[str, object] = {}
    if authority is not None:
        try:
            realization_knowledge = persist_p3_realization_knowledge(
                phase2_root=phase2_root,
                output_dir=output_dir,
                project_artifact_root=project_artifact_root,
                authority=authority,
                supplied_ledger=(
                    load_json_object(Path(args.authority_delta_ledger).resolve())
                    if str(args.authority_delta_ledger or "").strip()
                    else None
                ),
            )
        except (OSError, ValueError) as exc:
            return emit_summary(
                _blocked_summary(
                    output_dir,
                    f"P3 realization decisions artifact is blocked: {exc}",
                    ui_ia_contract=str(ui_path or ""),
                )
            )

    try:
        summary = scaffold_frontend_implementation(
            phase2_root=phase2_root,
            output_dir=output_dir,
            title=args.title,
            version=args.version,
            ui_ia_contract_path=ui_path,
            implementation_authority=authority,
            agentic_source_root=Path(args.agentic_source_root).resolve() if args.agentic_source_root else None,
        )
    except (FrontendImplementationAuthoringError, OSError, ValueError) as exc:
        summary = _blocked_summary(output_dir, str(exc), ui_ia_contract=str(ui_path or ""))
    if realization_knowledge:
        summary["realization_decisions"] = realization_knowledge
        write_json(output_dir / "impl-frontend-report.json", summary)
    return emit_summary(summary)


if __name__ == "__main__":
    raise SystemExit(main())
