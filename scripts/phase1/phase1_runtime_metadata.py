#!/usr/bin/env python3
"""
Shared Phase-1 runtime metadata helpers.
"""

from __future__ import annotations


OFFICIAL_RUNTIME_ENTRY = "scripts/phase1/run_phase1_full_trial.py"
CONVERGENCE_ENGINE = "scripts/phase1/run_phase1_convergence.py"
PRD_CONVERGENCE_SCRIPT = "scripts/phase1/phase1_converge_prd.py"


def build_runtime_metadata_lines(depth_mode: str, *, thinking_value_gain_mode: str = "off") -> list[str]:
    lines = [
        "- depth_mode:",
        f"  - `{depth_mode}`",
        "- depth_mode_boundary:",
        (
            "  - `creative starts only after baseline sufficiency; baseline truth and creative discoveries must remain separated`"
            if depth_mode == "creative"
            else "  - `baseline is the default v1.2 mode`"
        ),
        "- official_runtime_entry:",
        f"  - `{OFFICIAL_RUNTIME_ENTRY}`",
        "- convergence_engine:",
        f"  - `{CONVERGENCE_ENGINE}`",
        "- prd_convergence_script:",
        f"  - `{PRD_CONVERGENCE_SCRIPT}`",
    ]
    lines.extend([
        "- thinking_value_gain_mode:",
        f"  - `{thinking_value_gain_mode}`",
        "- thinking_value_gain_boundary:",
        (
            "  - `full-use is experimental bounded value-strengthening; stop when added rounds no longer improve practical value`"
            if thinking_value_gain_mode == "full-use"
            else "  - `off unless explicitly requested for bounded module value-gain`"
        ),
    ])
    return lines
