#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import argparse

from phase3.impl_context import emit_summary
from phase3.impl_verification_pack import run_impl_verification


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase-3 implementation verification capability")
    parser.add_argument("--mode", choices=("generate-tests", "verify"), default="verify")
    parser.add_argument("--workspace-root", default="")
    parser.add_argument("--phase2-root", default="")
    parser.add_argument("--output-dir", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace_root = Path(args.workspace_root or args.output_dir).resolve()
    phase2_root = Path(args.phase2_root).resolve() if args.phase2_root else None
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    summary = run_impl_verification(
        mode=args.mode,
        workspace_root=workspace_root,
        phase2_root=phase2_root,
        output_dir=output_dir,
    )
    return emit_summary(summary)


if __name__ == "__main__":
    raise SystemExit(main())
