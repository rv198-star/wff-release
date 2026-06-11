from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.output_language import resolve_output_locale


@dataclass(frozen=True)
class Phase3ImplContext:
    phase2_root: Path | None
    output_dir: Path
    output_locale: str
    ui_locale: str
    title: str
    version: str


def load_phase2_source_texts(phase2_root: Path) -> tuple[str, str, str]:
    return (
        (phase2_root / "engineering-spec-pack.md").read_text(encoding="utf-8"),
        (phase2_root / "stage-03-data-storage-and-interface-design.md").read_text(encoding="utf-8"),
        (phase2_root / "stage-04-design-convergence-and-delivery-prototype.md").read_text(encoding="utf-8"),
    )


def p2_operation_claim_id(operation_id: str) -> str:
    return f"P2-OP:{str(operation_id).strip()}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_impl_context(args: Any, *, require_phase2_root: bool = True) -> Phase3ImplContext:
    phase2_root = Path(args.phase2_root).resolve() if getattr(args, "phase2_root", "") else None
    if require_phase2_root and phase2_root is None:
        raise ValueError("--phase2-root is required")
    output_dir = Path(getattr(args, "output_dir", "") or getattr(args, "workspace_root", "")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_locale = resolve_output_locale(getattr(args, "output_locale", None))
    ui_locale = str(getattr(args, "ui_locale", "") or output_locale)
    return Phase3ImplContext(
        phase2_root=phase2_root,
        output_dir=output_dir,
        output_locale=output_locale,
        ui_locale=ui_locale,
        title=str(getattr(args, "title", "") or "Phase-3 Implementation"),
        version=str(getattr(args, "version", "") or "0.1.0"),
    )


def emit_summary(summary: dict[str, Any]) -> int:
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if str(summary.get("quality_gate", "pass")) == "pass" else 1
