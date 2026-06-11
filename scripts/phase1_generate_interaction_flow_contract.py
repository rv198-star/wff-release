#!/usr/bin/env python3
"""Compatibility entrypoint for Phase-1 interaction flow contract generation."""

from __future__ import annotations

from phase1.phase1_generate_interaction_flow_contract import *  # noqa: F401,F403
from phase1.phase1_generate_interaction_flow_contract import main


if __name__ == "__main__":
    raise SystemExit(main())

