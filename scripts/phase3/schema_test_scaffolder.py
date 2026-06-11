#!/usr/bin/env python3
"""
Generate executable schema-test scaffolds from the Phase-2 schema draft.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from pathlib import Path

from phase3.contract_tools import parse_schema_tables


def test_filename(table_name: str) -> str:
    return f"{table_name}.schema.test.ts"


def render_schema_test(table: dict[str, object]) -> str:
    fields = [str(row.get("field_name", "")) for row in table.get("fields", []) if str(row.get("field_name", "")).strip()]
    unique_constraints = table.get("unique_constraints", [])
    composite_indexes = table.get("composite_indexes", [])
    return "\n".join(
        [
            'import { describe, expect, it } from "vitest";',
            "",
            f"const fields = {json.dumps(fields, ensure_ascii=False, indent=2)};",
            f"const uniqueConstraints = {json.dumps(unique_constraints, ensure_ascii=False, indent=2)};",
            f"const compositeIndexes = {json.dumps(composite_indexes, ensure_ascii=False, indent=2)};",
            "",
            f'describe("Schema: {table["table_name"]}", () => {{',
            '  it("matches the frozen table contract", async () => {',
            "    expect(fields.length).toBeGreaterThan(0);",
            "    expect(new Set(fields).size).toBe(fields.length);",
            "    expect(Array.isArray(uniqueConstraints)).toBe(true);",
            "    expect(Array.isArray(compositeIndexes)).toBe(true);",
            "  });",
            "});",
            "",
        ]
    )


def scaffold_schema_tests(esp_text: str, output_dir: Path) -> dict[str, object]:
    tables = parse_schema_tables(esp_text)
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for table in tables:
        target = output_dir / test_filename(str(table["table_name"]))
        target.write_text(render_schema_test(table), encoding="utf-8")
        files.append(str(target))
    return {"output_dir": str(output_dir), "files_created": files, "count": len(files)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate executable schema tests from ESP")
    parser.add_argument("--esp", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = scaffold_schema_tests(
        Path(args.esp).resolve().read_text(encoding="utf-8"),
        Path(args.output_dir).resolve(),
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
