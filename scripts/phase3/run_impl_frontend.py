#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import argparse

from common.output_language import resolve_output_locale
from phase3.frontend_implementation_scaffolder import scaffold_frontend_implementation
from phase3.impl_context import emit_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Phase-3 frontend capability artifacts")
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--title", default="Phase-3 Frontend")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--ui-ia-contract", default="")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = scaffold_frontend_implementation(
        phase2_root=Path(args.phase2_root).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        title=args.title,
        version=args.version,
        ui_ia_contract_path=Path(args.ui_ia_contract).resolve() if args.ui_ia_contract else None,
    )
    return emit_summary(summary)


if __name__ == "__main__":
    raise SystemExit(main())
