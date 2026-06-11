#!/usr/bin/env python3
"""Compatibility entrypoint for the Phase-1 PRD executability gate."""

from __future__ import annotations

from phase1.phase1_prd_executability_gate import *  # noqa: F401,F403
from phase1.phase1_prd_executability_gate import main


if __name__ == "__main__":
    raise SystemExit(main())

