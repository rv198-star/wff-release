#!/usr/bin/env python3
"""
Generate runnable SQL verification tests from the Phase-2 schema draft.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import re
from pathlib import Path

from common.script_data_assets import load_script_text_asset
from phase3.phase3_behavior_card_consumption import render_behavior_step_test_mapping
from phase3.contract_tools import parse_schema_tables


WFF_SCRIPT_DATA_ASSETS = ("scripts/phase3/data/sql-test.ts.template",)


def load_sql_test_template() -> str:
    return load_script_text_asset(__file__, "sql-test.ts.template")


def _render_sql_test_template(replacements: dict[str, object]) -> str:
    text = load_sql_test_template()
    for key, value in replacements.items():
        text = text.replace(key, str(value))
    unresolved = sorted(set(re.findall(r"__[A-Z0-9_]+__", text)))
    if unresolved:
        raise ValueError(f"unresolved SQL test template placeholders: {', '.join(unresolved)}")
    return text


def test_filename(table_name: str) -> str:
    return f"{table_name}.sql.test.ts"


def _snake_case(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", normalized)
    return normalized.strip("_").lower()


def _quoted_identifier(value: str) -> str:
    return f'"{value}"'


def _sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _varchar_limit(data_type: str) -> int | None:
    match = re.search(r"(?:var)?char\s*\(\s*(\d+)\s*\)", data_type.lower())
    if not match:
        return None
    return int(match.group(1))


def _apply_length_limit(value: object, data_type: str) -> object:
    if not isinstance(value, str):
        return value
    limit = _varchar_limit(data_type)
    if limit is None or limit <= 0:
        return value
    return value[:limit]


def _foreign_key_target(constraint_text: str) -> tuple[str, str] | None:
    match = re.search(r"fk\s+([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)", constraint_text)
    if not match:
        return None
    return match.group(1), match.group(2)


def _primary_key_field(table: dict[str, object]) -> str:
    for field in table.get("fields", []):
        constraint_text = str(field.get("constraints", "")).lower()
        if "pk" in constraint_text:
            return str(field.get("field_name", "")).strip()
    first = next(iter(table.get("fields", [])), {})
    return str(first.get("field_name", "")).strip()


def _sample_uuid(seed: str) -> str:
    slug = re.sub(r"[^a-f0-9]", "", seed.lower())
    slug = (slug + "0" * 32)[:32]
    return f"{slug[:8]}-{slug[8:12]}-{slug[12:16]}-{slug[16:20]}-{slug[20:32]}"


def _sample_scalar_value(
    *,
    table_name: str,
    field_name: str,
    data_type: str,
    constraint_text: str,
) -> object:
    normalized_field = _snake_case(field_name)
    lowered_type = data_type.lower()
    lowered_constraints = constraint_text.lower()
    if "uuid" in lowered_type:
        return _sample_uuid(f"{table_name}_{normalized_field}")
    if lowered_type.startswith("int") or lowered_type.startswith("bigint") or lowered_type.startswith("smallint"):
        return 1
    if lowered_type.startswith("numeric") or lowered_type.startswith("decimal"):
        return 1.25
    if lowered_type.startswith("boolean"):
        return False
    if "json" in lowered_type:
        return {"table": table_name, "field": normalized_field}
    if "timestamp" in lowered_type or "date" in lowered_type:
        return "2025-01-01T00:00:00Z"
    if normalized_field.endswith("status"):
        if "draft" in lowered_constraints:
            return _apply_length_limit("draft", lowered_type)
        if "active" in lowered_constraints:
            return _apply_length_limit("active", lowered_type)
        if "queued" in lowered_constraints:
            return _apply_length_limit("queued", lowered_type)
        if "created" in lowered_constraints:
            return _apply_length_limit("created", lowered_type)
        return _apply_length_limit("active", lowered_type)
    if "severity" in normalized_field:
        return _apply_length_limit("high", lowered_type)
    if "priority" in normalized_field:
        return _apply_length_limit("p1", lowered_type)
    if "score" in normalized_field:
        return 0.91
    if "version" in normalized_field or normalized_field.endswith("_no"):
        return 1
    if "count" in normalized_field or "position" in normalized_field:
        return 1
    if "region" in normalized_field:
        return _apply_length_limit("eu", lowered_type)
    if "tier" in normalized_field:
        return _apply_length_limit("pro", lowered_type)
    if "subject_type" in normalized_field:
        return _apply_length_limit("user", lowered_type)
    if "role" in normalized_field:
        return _apply_length_limit("tenant_admin", lowered_type)
    if "type" in normalized_field:
        return _apply_length_limit("generated", lowered_type)
    if "window" in normalized_field:
        return _apply_length_limit("7d", lowered_type)
    if "url" in normalized_field:
        return _apply_length_limit(f"https://example.test/{table_name}/{normalized_field}", lowered_type)
    if "locator" in normalized_field or "ref" in normalized_field or "key" in normalized_field:
        return _apply_length_limit(f"{table_name}-{normalized_field}-001", lowered_type)
    if "name" in normalized_field:
        return _apply_length_limit(f"{table_name} {normalized_field}", lowered_type)
    if "note" in normalized_field or "summary" in normalized_field or "reason" in normalized_field:
        return _apply_length_limit(f"{table_name} {normalized_field} note", lowered_type)
    return _apply_length_limit(f"{table_name}-{normalized_field}-value", lowered_type)


def _sample_value(
    *,
    table_name: str,
    field: dict[str, object],
    tables_by_name: dict[str, dict[str, object]],
) -> object:
    field_name = str(field.get("field_name", "")).strip()
    data_type = str(field.get("data_type", "")).strip()
    constraint_text = str(field.get("constraints", "")).strip()
    fk_target = _foreign_key_target(constraint_text)
    if fk_target:
        referenced_table, referenced_column = fk_target
        referenced = tables_by_name.get(referenced_table)
        if referenced:
            referenced_field = next(
                (
                    candidate
                    for candidate in referenced.get("fields", [])
                    if str(candidate.get("field_name", "")).strip() == referenced_column
                ),
                {"field_name": referenced_column, "data_type": "uuid", "constraints": "pk"},
            )
            return _sample_value(
                table_name=referenced_table,
                field=referenced_field,
                tables_by_name=tables_by_name,
            )
    return _sample_scalar_value(
        table_name=table_name,
        field_name=field_name,
        data_type=data_type,
        constraint_text=constraint_text,
    )


def _render_insert_statements(
    table_name: str,
    tables_by_name: dict[str, dict[str, object]],
    emitted: set[str] | None = None,
) -> list[str]:
    emitted = emitted or set()
    if table_name in emitted:
        return []
    emitted.add(table_name)
    table = tables_by_name[table_name]
    statements: list[str] = []
    for field in table.get("fields", []):
        fk_target = _foreign_key_target(str(field.get("constraints", "")).strip())
        if not fk_target:
            continue
        referenced_table, _ = fk_target
        if referenced_table != table_name and referenced_table in tables_by_name:
            statements.extend(_render_insert_statements(referenced_table, tables_by_name, emitted))

    columns: list[str] = []
    values: list[str] = []
    for field in table.get("fields", []):
        field_name = str(field.get("field_name", "")).strip()
        if not field_name:
            continue
        columns.append(_quoted_identifier(field_name))
        sample_value = _sample_value(table_name=table_name, field=field, tables_by_name=tables_by_name)
        data_type = str(field.get("data_type", "")).strip().lower()
        if isinstance(sample_value, dict):
            values.append(f"{_sql_literal(json.dumps(sample_value, ensure_ascii=False))}::jsonb")
        elif "timestamp" in data_type:
            values.append(f"{_sql_literal(sample_value)}::timestamptz")
        else:
            values.append(_sql_literal(sample_value))
    statements.append(
        f"INSERT INTO {_quoted_identifier(table_name)} ({', '.join(columns)}) VALUES ({', '.join(values)});"
    )
    return statements


def _expected_match(table: dict[str, object], tables_by_name: dict[str, dict[str, object]]) -> dict[str, object]:
    expected: dict[str, object] = {}
    for field in table.get("fields", []):
        field_name = str(field.get("field_name", "")).strip()
        if not field_name:
            continue
        normalized = _snake_case(field_name)
        if normalized.endswith("created_at") or normalized.endswith("updated_at") or normalized.endswith("collected_at"):
            continue
        if "json" in str(field.get("data_type", "")).lower():
            continue
        sample_value = _sample_value(
            table_name=str(table["table_name"]).strip(),
            field=field,
            tables_by_name=tables_by_name,
        )
        data_type = str(field.get("data_type", "")).strip().lower()
        if (data_type.startswith("numeric") or data_type.startswith("decimal")) and sample_value is not None:
            expected[field_name] = str(sample_value)
            continue
        expected[field_name] = sample_value
    return expected


def _required_field_names(table: dict[str, object]) -> list[str]:
    required: list[str] = []
    for field in table.get("fields", []):
        field_name = str(field.get("field_name", "")).strip()
        nullable = str(field.get("nullable", "")).strip().lower()
        constraints = str(field.get("constraints", "")).strip().lower()
        if field_name and (nullable == "false" or "not null" in constraints or "pk" in constraints):
            required.append(field_name)
    return required


def _unique_constraint_fields(table: dict[str, object]) -> list[list[str]]:
    constraints = [str(item).strip() for item in table.get("unique_constraints", []) if str(item).strip()]
    parsed: list[list[str]] = []
    for constraint in constraints:
        fields = [field.strip() for field in re.split(r"\s*\+\s*|\s*,\s*", constraint) if field.strip()]
        fields = [field for field in fields if " where " not in field.lower()]
        if len(fields) >= 1:
            parsed.append(fields)
    return parsed


def _foreign_key_fields(table: dict[str, object], tables_by_name: dict[str, dict[str, object]]) -> list[str]:
    fields: list[str] = []
    for field in table.get("fields", []):
        field_name = str(field.get("field_name", "")).strip()
        fk_target = _foreign_key_target(str(field.get("constraints", "")).strip())
        if not field_name or not fk_target:
            continue
        target_table, _target_field = fk_target
        if target_table not in tables_by_name:
            continue
        fields.append(field_name)
    return fields



def _split_sql_top_level_csv(value: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    depth = 0
    index = 0
    while index < len(value):
        char = value[index]
        current.append(char)
        if quote:
            if char == quote:
                if index + 1 < len(value) and value[index + 1] == quote:
                    index += 1
                    current.append(value[index])
                else:
                    quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == '(':
            depth += 1
        elif char == ')':
            depth = max(0, depth - 1)
        elif char == ',' and depth == 0:
            current.pop()
            parts.append(''.join(current).strip())
            current = []
        index += 1
    if current:
        parts.append(''.join(current).strip())
    return parts

def _clone_insert_with_overrides(insert_statement: str, overrides: dict[str, object]) -> str:
    table_match = re.match(r'INSERT INTO "([^"]+)" \((.+)\) VALUES \((.+)\);', insert_statement)
    if not table_match:
        return insert_statement
    table_name = table_match.group(1)
    columns = [column.strip().strip('"') for column in _split_sql_top_level_csv(table_match.group(2))]
    values = _split_sql_top_level_csv(table_match.group(3))
    if len(columns) != len(values):
        return insert_statement
    rendered_values = [
        _sql_literal(overrides[column]) if column in overrides else values[index]
        for index, column in enumerate(columns)
    ]
    return f'INSERT INTO "{table_name}" ({", ".join(_quoted_identifier(column) for column in columns)}) VALUES ({", ".join(rendered_values)});'


def _constraint_probe_statements(
    table: dict[str, object],
    tables_by_name: dict[str, dict[str, object]],
    insert_statements: list[str],
) -> dict[str, object]:
    table_name = str(table["table_name"]).strip()
    own_insert = insert_statements[-1] if insert_statements else ""
    required_fields = _required_field_names(table)
    unique_fields = _unique_constraint_fields(table)
    fk_fields = _foreign_key_fields(table, tables_by_name)
    probes: dict[str, object] = {
        "not_null": [],
        "unique": [],
        "foreign_key": [],
    }
    for field_name in required_fields[:1]:
        probes["not_null"].append(_clone_insert_with_overrides(own_insert, {field_name: None}))
    for fields in unique_fields[:1]:
        probes["unique"].append({"fields": fields, "setup": list(insert_statements), "duplicate": own_insert})
    for field_name in fk_fields[:1]:
        field = next((candidate for candidate in table.get("fields", []) if str(candidate.get("field_name", "")).strip() == field_name), {})
        data_type = str(field.get("data_type", "uuid")).strip()
        orphan_value = _sample_scalar_value(table_name=table_name, field_name=f"orphan_{field_name}", data_type=data_type, constraint_text="")
        probes["foreign_key"].append(_clone_insert_with_overrides(own_insert, {field_name: orphan_value}))
    return probes


def render_sql_test(
    table: dict[str, object],
    tables_by_name: dict[str, dict[str, object]],
    *,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> str:
    table_name = str(table["table_name"]).strip()
    fields = [
        str(row.get("field_name", "")).strip()
        for row in table.get("fields", [])
        if str(row.get("field_name", "")).strip()
    ]
    composite_indexes = [str(item).strip() for item in table.get("composite_indexes", []) if str(item).strip()]
    unique_constraints = [str(item).strip() for item in table.get("unique_constraints", []) if str(item).strip()]
    insert_statements = _render_insert_statements(table_name, tables_by_name)
    pk_field = _primary_key_field(table)
    pk_value = _sample_value(
        table_name=table_name,
        field=next(
            candidate for candidate in table.get("fields", []) if str(candidate.get("field_name", "")).strip() == pk_field
        ),
        tables_by_name=tables_by_name,
    )
    expected_match = _expected_match(table, tables_by_name)
    constraint_probes = _constraint_probe_statements(table, tables_by_name, insert_statements)
    selected_columns = sorted(expected_match)
    select_columns = ", ".join(_quoted_identifier(column) for column in selected_columns)
    behavior_mapping_lines = []
    for model in (behavior_card_models or {}).values():
        persistence_effects = str(model.get("persistence_effects", "")).lower()
        if table_name.lower() in persistence_effects:
            behavior_mapping_lines.extend(render_behavior_step_test_mapping(model)["sql"].splitlines())
    behavior_mapping_block = "\n".join(behavior_mapping_lines)
    behavior_mapping_block = behavior_mapping_block + "\n\n" if behavior_mapping_block else "\n"
    state_update_statement = f'`UPDATE "{table_name}" SET "{pk_field}" = "{pk_field}" WHERE "{pk_field}" = $1`'
    select_query = f'`SELECT {select_columns} FROM "{table_name}" WHERE "{pk_field}" = $1`'
    return _render_sql_test_template(
        {
            "__TABLE_NAME__": json.dumps(table_name, ensure_ascii=False),
            "__EXPECTED_COLUMNS__": json.dumps(fields, ensure_ascii=False, indent=2),
            "__EXPECTED_INDEX_HINTS__": json.dumps(composite_indexes + unique_constraints, ensure_ascii=False, indent=2),
            "__SEED_STATEMENTS__": json.dumps(insert_statements, ensure_ascii=False, indent=2),
            "__CONSTRAINT_PROBES__": json.dumps(constraint_probes, ensure_ascii=False, indent=2),
            "__PRIMARY_KEY_VALUE__": json.dumps(pk_value, ensure_ascii=False),
            "__EXPECTED_MATCH__": json.dumps(expected_match, ensure_ascii=False, indent=2),
            "__STATE_UPDATE_STATEMENT__": state_update_statement,
            "__BEHAVIOR_MAPPING_BLOCK__": behavior_mapping_block,
            "__DESCRIBE_LABEL__": json.dumps(f"SQL: {table_name}", ensure_ascii=False),
            "__SELECT_QUERY__": select_query,
        }
    )


def scaffold_sql_tests(
    esp_text: str,
    output_dir: Path,
    *,
    behavior_card_models: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    tables = parse_schema_tables(esp_text)
    tables_by_name = {str(table["table_name"]).strip(): table for table in tables}
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for table in tables:
        target = output_dir / test_filename(str(table["table_name"]))
        target.write_text(render_sql_test(table, tables_by_name, behavior_card_models=behavior_card_models), encoding="utf-8")
        files.append(str(target))
    return {"output_dir": str(output_dir), "files_created": files, "count": len(files)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate runnable SQL tests from ESP")
    parser.add_argument("--esp", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = scaffold_sql_tests(
        Path(args.esp).resolve().read_text(encoding="utf-8"),
        Path(args.output_dir).resolve(),
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
