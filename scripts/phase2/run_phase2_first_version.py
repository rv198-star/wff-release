#!/usr/bin/env python3
"""Deprecated compatibility entrypoint for Phase-2 first-version generation.

Prefer `scripts/phase2/run_phase2_fresh_generation.py` for fresh P1 -> P2
runs, or `scripts/phase2/run_phase2_existing_system_intake.py` when the run is
anchored by an existing-system architecture-change intake packet. This wrapper
remains temporarily to preserve older automation and release-validation command
surfaces while #93 validates the modular P2 runtime split.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from phase2.phase2_first_version_runtime import *  # noqa: F401,F403,E402
from phase2.phase2_first_version_runtime import main as _runtime_main  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return _runtime_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
