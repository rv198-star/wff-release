#!/usr/bin/env python3
"""Generate P3-S3 backend code and test files without executing them."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.output_language import resolve_output_locale
from common.agentic_decision_authority import load_json_object, write_json_atomic
from phase3.agentic_implementation_authority import P3AgenticImplementationAuthorityError, prepare_and_accept_p3_implementation_authority, validate_authority_delta_ledger
from phase3.backend_implementation_scaffolder import scaffold_backend_implementation
from phase3.s3_code_realization import S3CodeRealizationError, generate_s3_db_support, realize_s3_code_and_tests

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate P3-S3 backend code/tests without execution")
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--action-card-root", required=True)
    parser.add_argument("--agentic-implementation-decision", required=True)
    parser.add_argument("--authority-delta-ledger", default="")
    parser.add_argument("--agentic-source-root", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--title", default="Phase-3 S3 Backend Realization")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    del args.output_locale
    phase2_root = Path(args.phase2_root).resolve()
    action_card_root = Path(args.action_card_root).resolve()
    decision_path = Path(args.agentic_implementation_decision).resolve()
    output_dir = Path(args.output_dir).resolve()
    try:
        authority = prepare_and_accept_p3_implementation_authority(
            phase2_root=phase2_root,
            action_card_root=action_card_root,
            output_dir=output_dir,
            decision_path=decision_path,
        )
        delta_records = validate_authority_delta_ledger(load_json_object(Path(args.authority_delta_ledger).resolve()), authority=authority) if str(args.authority_delta_ledger).strip() else None
        if delta_records is not None:
            write_json_atomic(output_dir / ".phase3-evidence" / "p3-authority-delta-ledger.json", load_json_object(Path(args.authority_delta_ledger).resolve()))
        backend = scaffold_backend_implementation(
            phase2_root=phase2_root,
            output_dir=output_dir,
            title=args.title,
            version=args.version,
        )
        db_schema = generate_s3_db_support(phase2_root=phase2_root, output_dir=output_dir, authority=authority, delta_records=delta_records)
        realization = realize_s3_code_and_tests(output_dir=output_dir, authority=authority, agentic_source_root=Path(args.agentic_source_root) if str(args.agentic_source_root).strip() else None)
    except (P3AgenticImplementationAuthorityError, S3CodeRealizationError, OSError, ValueError) as exc:
        print(f"[BLOCKED] {exc}")
        return 2
    authoring_required = realization["receipt"].get("status") == "authoring-required"
    report = {
        "artifact_kind": "phase3-s3-generation-only-report.v1",
        "quality_gate": "authoring-required" if authoring_required else "generated-not-executed",
        "decision_id": authority.get("decision_id"),
        "decision_digest": authority.get("decision_digest"),
        "backend_scaffold": backend,
        "db_schema": db_schema,
        "realization_receipt": realization["receipt"],
        "execution": {
            "tests_executed": False,
            "runtime_started": False,
            "trace_confirmed": False,
            "status": "not-executed-by-design",
        },
        "claim_ceiling": realization["receipt"]["claim_ceiling"],
    }
    write_json_atomic(output_dir / "p3-s3-generation-only-report.json", report)
    print(json.dumps({
        "status": report["quality_gate"],
        "decision_id": report["decision_id"],
        "implementation_targets": realization["receipt"]["declared_implementation_target_count"],
        "test_targets": realization["receipt"]["declared_test_target_count"],
        "execution": "not-executed-by-design",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
