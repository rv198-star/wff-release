from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase3.phase3_delivery_gate import (
    build_phase3_mainline_assessment_summary,
    write_phase3_mainline_assessment_artifacts,
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def emit_phase3_mainline_assessment(
    *,
    output_dir: Path,
    assessment: dict[str, Any],
    case_name: str = "",
    version: str = "",
    output_locale: str = "zh-CN",
    human_review: dict[str, Any] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    assessment_artifacts = write_phase3_mainline_assessment_artifacts(
        output_dir=output_dir,
        assessment=assessment,
        case_name=case_name,
        version=version,
        output_locale=output_locale,
        human_review=human_review,
    )
    assessment_summary = build_phase3_mainline_assessment_summary(
        assessment=assessment,
        artifact_paths=assessment_artifacts,
    )
    return assessment_artifacts, assessment_summary


def update_phase3_run_metadata_with_assessment(
    *,
    metadata_path: Path,
    assessment_artifacts: dict[str, str],
    assessment_summary: dict[str, Any],
) -> dict[str, Any]:
    metadata = load_json_if_exists(metadata_path) or {}
    metadata["mainline_assessment_artifacts"] = assessment_artifacts
    metadata["mainline_assessment_summary"] = assessment_summary
    metadata["phase_verdict_path"] = assessment_summary.get("phase_verdict_path", "")
    metadata["phase_verdict"] = assessment_summary.get("phase_verdict", "")
    metadata["phase_total_score"] = assessment_summary.get("phase_total_score")
    metadata["phase_review_bound_items_count"] = assessment_summary.get("review_bound_items_count", 0)
    metadata["phase_blockers_count"] = assessment_summary.get("blockers_count", 0)
    write_json(metadata_path, metadata)
    return metadata
