from __future__ import annotations

from pathlib import Path
from typing import Any

from phase3.contract_tools import generate_migration_sql, parse_schema_tables
from phase3.impl_context import load_phase2_source_texts, write_json
from phase3.schema_test_scaffolder import scaffold_schema_tests
from phase3.sql_test_scaffolder import scaffold_sql_tests


def run_impl_db_schema(
    *,
    phase2_root: Path,
    output_dir: Path,
    esp_text: str | None = None,
    stage_03_text: str | None = None,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> dict[str, Any]:
    del stage_03_text
    if esp_text is None:
        esp_text, _, _ = load_phase2_source_texts(phase2_root)

    migration_path = output_dir / "db" / "migrations" / "001_initial_schema.sql"
    migration_path.parent.mkdir(parents=True, exist_ok=True)
    tables = parse_schema_tables(esp_text)
    migration_path.write_text(generate_migration_sql(tables), encoding="utf-8")

    schema_summary = scaffold_schema_tests(esp_text, output_dir / "tests" / "schema")
    sql_summary = scaffold_sql_tests(
        esp_text,
        output_dir / "tests" / "sql",
        behavior_card_models=behavior_card_models,
    )
    summary = {
        "artifact_kind": "phase3-impl-db-schema-report",
        "quality_gate": "pass",
        "migration_path": str(migration_path),
        "table_count": len(tables),
        "schema_summary": schema_summary,
        "sql_summary": sql_summary,
        "claim_ceiling": "db schema artifacts only; runtime DB proof requires verification",
    }
    write_json(output_dir / "db-schema-report.json", summary)
    return summary
