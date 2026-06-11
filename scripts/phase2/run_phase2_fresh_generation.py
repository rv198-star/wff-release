#!/usr/bin/env python3
"""Official Phase-2 fresh-generation runtime entrypoint."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from phase2.phase2_first_version_runtime import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
