from __future__ import annotations

from pathlib import Path


EXISTING_SYSTEM_ARCHITECTURE_CHANGE_INTAKE_FILENAME = (
    "existing-system-architecture-change-intake.md"
)


def resolve_existing_system_architecture_change_intake(raw_path: str) -> Path | None:
    cleaned = str(raw_path or "").strip()
    if not cleaned:
        return None
    path = Path(cleaned).resolve()
    if not path.exists():
        raise FileNotFoundError(f"existing-system architecture change intake not found: {path}")
    return path


def materialize_existing_system_architecture_change_intake(
    *,
    source: Path | None,
    output_dir: Path,
) -> Path | None:
    if source is None:
        return None
    target = output_dir / EXISTING_SYSTEM_ARCHITECTURE_CHANGE_INTAKE_FILENAME
    source_text = source.read_text(encoding="utf-8")
    if source.resolve() != target.resolve():
        target.write_text(source_text, encoding="utf-8")
    return target


def discover_existing_system_architecture_change_intake(output_dir: Path) -> Path | None:
    candidate = output_dir / EXISTING_SYSTEM_ARCHITECTURE_CHANGE_INTAKE_FILENAME
    return candidate if candidate.exists() else None


def render_existing_system_architecture_change_addendum(
    *,
    intake_path: Path | None,
    relative_to: Path,
) -> str:
    if intake_path is None:
        return ""
    intake_text = intake_path.read_text(encoding="utf-8").strip()
    try:
        display_path = intake_path.resolve().relative_to(relative_to.resolve())
    except ValueError:
        display_path = intake_path.resolve()
    return "\n".join(
        [
            "## Existing-System Architecture Change Addendum",
            "",
            "- source_packet:",
            f"  - `{display_path}`",
            "- packet_subtype:",
            "  - `existing-system-architecture-change`",
            "- processing_rule:",
            "  - Run `Architecture Change Impact Triage` before normal target design expression.",
            "  - Keep observed facts, inferred semantics, explicit unknowns, and review-bound claims separate.",
            "  - AC-3 / AC-4 items cannot be silently promoted as ready-for-P3.",
            "- compatibility_posture:",
            "  - Prefer additive compatibility, adapters, staged migration, rollback, and protected legacy behavior.",
            "",
            "### Source Packet Snapshot",
            "",
            intake_text,
        ]
    ).rstrip() + "\n"
