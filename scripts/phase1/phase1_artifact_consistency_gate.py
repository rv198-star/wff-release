#!/usr/bin/env python3
"""
Phase-1 artifact consistency gate.

Checks that PRD, execution report, and stage artifacts belong to the same run
version (for example `trial-v8`) and that report-inventoried artifacts exist.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import sys

from phase1.mainline_gates import (
    extract_trial_tokens,
    normalize_expected_version,
    run_artifact_consistency_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-1 artifact consistency gate")
    parser.add_argument("--prd", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--stage", action="append", default=[])
    parser.add_argument("--expected-version")
    parser.add_argument(
        "--require-stage-files",
        action="store_true",
        help="fail if no stage artifact files can be resolved",
    )
    args = parser.parse_args()

    return run_artifact_consistency_gate(args)


if __name__ == "__main__":
    sys.exit(main())
