#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from artifact_consistency.audit import (
    audit_file,
    build_inventory_report,
    load_contract,
    write_inventory_json_report,
    write_inventory_markdown_report,
    write_json_report,
    write_markdown_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit rendered artifact consistency")
    parser.add_argument("--profile", default="generic")
    parser.add_argument("--contract")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    parser.add_argument("--output-inventory-json")
    parser.add_argument("--output-inventory-md")
    args = parser.parse_args()

    artifact_path = Path(args.artifact)
    contract = load_contract(Path(args.contract) if args.contract else None)

    report = audit_file(
        artifact_path,
        profile=args.profile,
        contract=contract,
    )

    if args.output_inventory_json or args.output_inventory_md:
        inventory_report = build_inventory_report(artifact_path.read_text(encoding="utf-8"), contract=contract)
        if args.output_inventory_json:
            write_inventory_json_report(inventory_report, Path(args.output_inventory_json))
        if args.output_inventory_md:
            write_inventory_markdown_report(inventory_report, Path(args.output_inventory_md))

    if args.output_json:
        write_json_report(report, Path(args.output_json))
    if args.output_md:
        write_markdown_report(report, Path(args.output_md))

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
