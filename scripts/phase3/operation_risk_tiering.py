#!/usr/bin/env python3
"""Shared P2/P3 operation risk tiering and source obligations."""

from __future__ import annotations

from pathlib import Path
import sys


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.operation_risk_tiering import *  # noqa: F401,F403


if __name__ == "__main__":
    raise SystemExit(main())
