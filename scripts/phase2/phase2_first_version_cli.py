#!/usr/bin/env python3
"""Phase-2 first-version runtime slice: phase2_first_version_cli.py."""

from __future__ import annotations

from phase2.phase2_first_version_support import *  # noqa: F401,F403

def phase2_first_version_authority() -> dict[str, Any]:
    return dict(PHASE2_FIRST_VERSION_AUTHORITY)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Official Phase-2 mainline entry: generate a fresh first version from a Phase-1 PRD.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "validation profile: phase; default status: default fresh Phase-2 mainline; "
            "claim ceiling: P2 architecture/spec artifacts and declared wrapper evidence only."
        ),
    )
    parser.add_argument("--phase1-prd", required=True, help="Path to the Phase-1 PRD main document.")
    parser.add_argument(
        "--existing-system-architecture-change-intake",
        default="",
        help=(
            "Optional P2 Existing-System Architecture Change Intake Packet. "
            "This sidecar does not replace --phase1-prd."
        ),
    )
    parser.add_argument("--output-dir", required=True, help="Fresh Phase-2 case root.")
    parser.add_argument("--version", default="v-next", help="Phase-2 version label.")
    parser.add_argument("--case-name", default="", help="Optional case-name override.")
    parser.add_argument(
        "--complexity-profile",
        default="",
        help="Optional complexity profile override: micro | standard | complex.",
    )
    parser.add_argument(
        "--complexity-override-justification",
        default="",
        help="Justification forwarded to the full-trial wrapper when --complexity-profile overrides the classifier.",
    )
    parser.add_argument(
        "--deployment-posture",
        default="light",
        choices=("light", "standard", "heavy"),
        help="Deployment/infrastructure posture to pass into wrapper metadata: light | standard | heavy.",
    )
    parser.add_argument(
        "--deployment-posture-suggested",
        default="light",
        choices=("light", "standard", "heavy"),
        help="Suggested deployment/infrastructure posture recorded by wrapper metadata.",
    )
    parser.add_argument(
        "--deployment-posture-warning-class",
        default="none",
        choices=("none", "constraint-backed-override", "preference-driven-override"),
        help="Wrapper warning class when selected deployment posture differs from suggested posture.",
    )
    parser.add_argument(
        "--deployment-posture-override-source",
        default="",
        help="Wrapper override source when selected deployment posture differs from suggested posture.",
    )
    parser.add_argument(
        "--deployment-posture-override-reason",
        default="",
        help="Wrapper override reason when selected deployment posture differs from suggested posture.",
    )
    parser.add_argument(
        "--deployment-posture-added-risks",
        default="",
        help="Wrapper added-risk summary when selected deployment posture differs from suggested posture.",
    )
    parser.add_argument(
        "--pure-prd-direct",
        action="store_true",
        help="Record this run as a pure direct baseline from the Phase-1 PRD main document.",
    )
    parser.add_argument(
        "--owner",
        default="codex",
        help="Run owner recorded in sidecar metadata.",
    )
    parser.add_argument(
        "--output-locale",
        default=resolve_output_locale(),
        help="Default language for human-reviewed generated reports.",
    )
    parser.add_argument(
        "--thinking-value-gain-mode",
        choices=("off", "full-use"),
        default="off",
        help="Mindthus TVG strategy marker for Phase-2 generation; defaults to off.",
    )
    parser.add_argument(
        "--thinking-value-gain-output-profile",
        choices=THINKING_VALUE_GAIN_OUTPUT_PROFILES,
        default="coverage_rich",
        help="Mindthus TVG output profile to use when TVG full-use is enabled.",
    )
    parser.add_argument(
        "--run-wrapper",
        action="store_true",
        help="Complete the official Phase-2 mainline bundle with scripts/phase2/phase2_closure_runtime.py.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into an existing non-empty output directory.",
    )
    return parser


def parse_phase2_first_version_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return parse_phase2_first_version_args(argv)


__all__ = [name for name in globals() if not name.startswith("__")]
