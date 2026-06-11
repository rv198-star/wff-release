#!/usr/bin/env python3
"""Run the modular Phase-3 foundation / first-version capability."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from phase3.phase3_first_version_runtime import (  # noqa: F401
    build_parser,
    build_phase3_runner_context,
    main as _foundation_main,
    parse_phase3_first_version_args,
    validate_phase3_runner_args,
)


def main(argv: list[str] | None = None) -> int:
    return _foundation_main(
        argv,
        runner_actor="run_impl_foundation",
        generation_entrypoint="scripts/phase3/run_impl_foundation.py",
    )


if __name__ == "__main__":
    raise SystemExit(main())
