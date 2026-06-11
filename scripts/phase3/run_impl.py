#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import argparse

from common.output_language import resolve_output_locale
from phase3.impl_action_cards import run_impl_action_cards
from phase3.impl_context import emit_summary
from phase3.impl_db_schema import run_impl_db_schema
from phase3.run_impl_api_docs import main as api_docs_main
from phase3.run_impl_backend import main as backend_main
from phase3.run_impl_frontend import main as frontend_main
from phase3.run_impl_verification import main as verification_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase-3 implementation aggregate capability")
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--title", default="Phase-3 Implementation")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--enable-frontend", action="store_true")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    phase2_root = Path(args.phase2_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    action_cards = run_impl_action_cards(
        phase2_root=phase2_root,
        output_dir=output_dir,
        output_locale=resolve_output_locale(args.output_locale),
    )
    db_schema = run_impl_db_schema(phase2_root=phase2_root, output_dir=output_dir)
    verification_generate_code = verification_main(
        [
            "--mode",
            "generate-tests",
            "--phase2-root",
            str(phase2_root),
            "--output-dir",
            str(output_dir),
        ]
    )
    backend_code = backend_main(
        [
            "--phase2-root",
            str(phase2_root),
            "--output-dir",
            str(output_dir),
            "--title",
            args.title,
            "--version",
            args.version,
        ]
    )
    api_docs_code = api_docs_main(
        [
            "--baseline-openapi",
            str(output_dir / "contracts" / "openapi.yaml"),
            "--output-dir",
            str(output_dir / "api-docs"),
            "--title",
            f"{args.title} API Documentation",
            "--output-locale",
            args.output_locale,
        ]
    )
    frontend_code = 0
    if args.enable_frontend:
        frontend_code = frontend_main(
            [
                "--phase2-root",
                str(phase2_root),
                "--output-dir",
                str(output_dir),
                "--title",
                args.title,
                "--version",
                args.version,
            ]
        )
    verification_code = verification_main(["--mode", "verify", "--workspace-root", str(output_dir)])
    summary = {
        "artifact_kind": "phase3-impl-aggregate-report",
        "quality_gate": "pass"
        if backend_code == 0
        and frontend_code == 0
        and api_docs_code == 0
        and verification_generate_code == 0
        and verification_code == 0
        else "blocked",
        "action_cards": action_cards,
        "db_schema": db_schema,
        "verification_generate_exit_code": verification_generate_code,
        "backend_exit_code": backend_code,
        "api_docs_exit_code": api_docs_code,
        "frontend_exit_code": frontend_code,
        "verification_exit_code": verification_code,
        "claim_ceiling": "aggregate capability smoke; full P3 equivalence requires strict-runtime validation",
    }
    return emit_summary(summary)


if __name__ == "__main__":
    raise SystemExit(main())
