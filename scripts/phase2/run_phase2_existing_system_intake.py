#!/usr/bin/env python3
"""Phase-2 existing-system architecture-change intake entrypoint."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from phase2.phase2_first_version_runtime import main as _runtime_main, parse_phase2_first_version_args  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = parse_phase2_first_version_args(argv)
    if not str(getattr(args, "existing_system_architecture_change_intake", "") or "").strip():
        print("[BLOCKED] --existing-system-architecture-change-intake is required for this entrypoint")
        return 2
    return _runtime_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
