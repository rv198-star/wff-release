#!/usr/bin/env python3
"""
Phase-1 PRD assembly integrity gate.

Purpose:
- ensure PRD is assembled from stage artifacts instead of mirroring the source input
- block raw-source append patterns
- ensure source-artifact inventory is present and references stage outputs
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse

from phase1.phase1_gate_authority import emit_compatibility_warning
from phase1.mainline_gates import run_prd_assembly_integrity_gate


def main() -> int:
    emit_compatibility_warning("scripts/phase1/phase1_prd_assembly_integrity_gate.py")
    parser = argparse.ArgumentParser(description="Phase-1 PRD assembly integrity gate")
    parser.add_argument("--source", required=True)
    parser.add_argument("--prd", required=True)
    parser.add_argument("--report")
    parser.add_argument("--stage", action="append", default=[])
    parser.add_argument("--max-copy-block-chars", type=int, default=2800)
    parser.add_argument("--max-copy-block-ratio", type=float, default=0.18)
    args = parser.parse_args()

    return run_prd_assembly_integrity_gate(args)


if __name__ == "__main__":
    raise SystemExit(main())
