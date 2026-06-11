#!/usr/bin/env python3
"""Render the generated Phase-3 backend runtime harness."""

from __future__ import annotations

from common.script_data_assets import load_script_text_asset


WFF_SCRIPT_DATA_ASSETS = ("scripts/phase3/data/backend-runtime-harness.ts.template",)


def render_backend_runtime_harness() -> str:
    return load_script_text_asset(__file__, "backend-runtime-harness.ts.template")
