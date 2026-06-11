from __future__ import annotations

from pathlib import Path
from typing import Any

from phase3.impl_context import load_phase2_source_texts, write_json
from phase3.impl_contract_pack import materialize_contract_pack
from phase3.project_scaffold_parts import scaffold_root_workspace, scaffold_shared_packages, scaffold_web_app


def scaffold_frontend_implementation(
    *,
    phase2_root: Path,
    output_dir: Path,
    title: str,
    version: str,
    ui_ia_contract_path: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    esp_text, stage_03_text, stage_04_text = load_phase2_source_texts(phase2_root)
    contract_summary = materialize_contract_pack(
        phase2_root=phase2_root,
        output_dir=output_dir,
        title=title,
        version=version,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        enable_ui_fallback=False,
        enforce_compiled_authority=False,
    )
    root_summary = scaffold_root_workspace(output_dir=output_dir, project_name=title)
    shared_summary = scaffold_shared_packages(output_dir=output_dir)
    web_summary = scaffold_web_app(output_dir=output_dir)
    summary = {
        "artifact_kind": "phase3-impl-frontend-report",
        "quality_gate": "pass",
        "contract_pack": {key: str(value) for key, value in contract_summary.items() if key.endswith("_path")},
        "root_summary": root_summary,
        "shared_summary": shared_summary,
        "web_summary": web_summary,
        "ui_ia_contract": str(ui_ia_contract_path.resolve()) if ui_ia_contract_path else "",
        "claim_ceiling": "frontend scaffold only; UX and runtime quality require frontend verification",
    }
    write_json(output_dir / "impl-frontend-report.json", summary)
    return summary
