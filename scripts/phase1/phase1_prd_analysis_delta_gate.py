#!/usr/bin/env python3
"""
Phase-1 PRD analysis-delta gate.

This gate is intentionally strict:
- PRD or a dedicated convergence-evidence memo must include an "Analysis Delta Ledger" section
- each delta entry must carry source evidence, analytical inference, decision/tradeoff, and downstream impact
- enough deltas must exist across multiple categories
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import sys

from phase1.phase1_gate_authority import emit_compatibility_warning
from phase1.mainline_gates import (
    extract_delta_section,
    run_prd_analysis_delta_gate,
    split_delta_entries,
)


def main() -> int:
    emit_compatibility_warning("scripts/phase1/phase1_prd_analysis_delta_gate.py")
    parser = argparse.ArgumentParser(description="Phase-1 PRD analysis delta gate")
    parser.add_argument("--prd", required=True)
    parser.add_argument(
        "--delta-ledger",
        help="optional external convergence evidence markdown carrying the Analysis Delta Ledger",
    )
    parser.add_argument("--min-deltas", type=int, default=12)
    parser.add_argument("--min-category-coverage", type=int, default=5)
    args = parser.parse_args()

    return run_prd_analysis_delta_gate(args)


if __name__ == "__main__":
    sys.exit(main())
