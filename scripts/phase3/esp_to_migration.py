#!/usr/bin/env python3
"""
Generate an initial SQL migration from a Phase-2 Engineering Spec Pack.
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

from phase3.contract_tools import generate_migration_sql, parse_schema_tables


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate SQL migration from Engineering Spec Pack")
    parser.add_argument("--esp", required=True, help="Path to engineering-spec-pack.md")
    parser.add_argument("--output", required=True, help="Output path for SQL migration")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    esp_path = Path(args.esp).resolve()
    output_path = Path(args.output).resolve()
    tables = parse_schema_tables(esp_path.read_text(encoding="utf-8"))
    sql = generate_migration_sql(tables)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(sql, encoding="utf-8")
    print(json.dumps({"output": str(output_path), "tables": len(tables)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
