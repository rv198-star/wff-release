#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import argparse

from common.output_language import resolve_output_locale
from phase3.impl_context import emit_summary
from phase3.impl_db_schema import run_impl_db_schema


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Phase-3 DB schema capability artifacts")
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output-locale", default=resolve_output_locale())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_impl_db_schema(phase2_root=Path(args.phase2_root).resolve(), output_dir=Path(args.output_dir).resolve())
    return emit_summary(summary)


if __name__ == "__main__":
    raise SystemExit(main())
