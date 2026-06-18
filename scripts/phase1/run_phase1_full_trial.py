#!/usr/bin/env python3
"""Compatibility wrapper for the renamed Phase-1 source-to-PRD runner.

Use ``run_phase1_source_to_prd.py`` as the primary entrypoint. This legacy
path remains for one release cycle so existing commands and imports continue
to work while guidance moves away from the historical ``full_trial`` name.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from phase1.run_phase1_source_to_prd import *  # noqa: F401,F403
from phase1.run_phase1_source_to_prd import main


if __name__ == "__main__":
    raise SystemExit(main())
