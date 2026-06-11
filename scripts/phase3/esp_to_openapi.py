#!/usr/bin/env python3
"""
Generate a JSON-compatible OpenAPI document from a Phase-2 Engineering Spec Pack.
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

from phase3.contract_tools import build_openapi_spec, parse_api_endpoint_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate OpenAPI from Engineering Spec Pack")
    parser.add_argument("--esp", required=True, help="Path to engineering-spec-pack.md")
    parser.add_argument("--output", required=True, help="Output path for openapi.yaml")
    parser.add_argument("--title", default="Phase-3 Contract Pack")
    parser.add_argument("--version", default="0.1.0")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    esp_path = Path(args.esp).resolve()
    output_path = Path(args.output).resolve()
    endpoint_rows = parse_api_endpoint_rows(esp_path.read_text(encoding="utf-8"))
    spec = build_openapi_spec(endpoint_rows, title=args.title, version=args.version)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "paths": len(spec["paths"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
