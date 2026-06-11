#!/usr/bin/env python3
"""
Apply Phase-3 work-package gate results and refresh runtime dispatch state.
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
from typing import Any

from common.output_language import localize_phase3_wp_gate_cycle_report
from phase3.execution_packet_access import load_json_if_exists as load_verification_ledger_if_exists
from phase3.runtime_cycle import run_runtime_cycle
from phase3.verification_ledger import synthesize_gate_inputs_from_ledger


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def load_json_if_exists(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return load_json(path)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def report_is_pass(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    for key in ("overall_quality_gate", "verdict", "status", "gate"):
        value = report.get(key)
        if value is not None:
            return str(value).lower() == "pass"
    return False


def parse_passed_tests(test_report: dict[str, Any]) -> set[str]:
    candidates = []
    for key in ("passed_tests", "passed", "green_tests"):
        value = test_report.get(key)
        if isinstance(value, list):
            candidates.extend(str(item).strip() for item in value if str(item).strip())
    return set(candidates)


def split_required_optional_tests(test_targets: set[str]) -> tuple[set[str], set[str]]:
    required: set[str] = set()
    optional: set[str] = set()
    for test_target in test_targets:
        normalized = str(test_target).strip()
        if not normalized:
            continue
        if (
            normalized.startswith("tests/sql/")
            or normalized.startswith("tests/contracts/")
            or normalized.startswith("tests/unit/api/")
        ):
            required.add(normalized)
        else:
            optional.add(normalized)
    return required, optional


def infer_binding_lane_hint(*, test_targets: set[str], implementation_targets: set[str]) -> str:
    has_backend_tests = any(
        target.startswith("tests/sql/")
        or target.startswith("tests/contracts/")
        or target.startswith("tests/unit/api/")
        for target in test_targets
    )
    has_frontend_tests = any(target.startswith("tests/unit/web/") for target in test_targets)
    if has_backend_tests and has_frontend_tests:
        return "fullstack"
    if has_backend_tests:
        return "backend"
    if has_frontend_tests:
        return "frontend"

    has_scenario_tests = any(target.startswith("tests/scenarios/") for target in test_targets)
    has_backend_implementation = any(target.startswith("apps/api/") for target in implementation_targets)
    has_frontend_implementation = any(target.startswith("apps/web/") for target in implementation_targets)
    if has_scenario_tests and has_frontend_implementation:
        return "frontend"
    if has_scenario_tests and has_backend_implementation:
        return "backend"
    if has_backend_implementation and has_frontend_implementation:
        return "fullstack"
    if has_backend_implementation:
        return "backend"
    if has_frontend_implementation:
        return "frontend"
    return ""


def split_tests_by_validation_layer(test_targets: set[str], *, lane_hint: str = "") -> dict[str, set[str]]:
    layers: dict[str, set[str]] = {
        "L1-db-sql": set(),
        "L2-atomic-api": set(),
        "L3-composed-api": set(),
        "L4-flow-api": set(),
        "optional": set(),
    }
    for test_target in test_targets:
        normalized = str(test_target).strip()
        if not normalized:
            continue
        if normalized.startswith("tests/sql/"):
            layers["L1-db-sql"].add(normalized)
            continue
        if normalized.startswith("tests/contracts/") or normalized.startswith("tests/unit/api/"):
            layers["L2-atomic-api"].add(normalized)
            continue
        if normalized.startswith("tests/scenarios/"):
            if lane_hint == "frontend":
                layers["optional"].add(normalized)
            else:
                layers["L3-composed-api"].add(normalized)
            continue
        if normalized.startswith("tests/replays/"):
            if lane_hint == "frontend":
                layers["optional"].add(normalized)
            else:
                layers["L4-flow-api"].add(normalized)
            continue
        layers["optional"].add(normalized)
    return layers


def runtime_rows_by_wp(runtime_environment_ledger: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    mapping: dict[str, list[dict[str, Any]]] = {}
    if not runtime_environment_ledger:
        return mapping
    for row in runtime_environment_ledger.get("rows", []):
        if not isinstance(row, dict):
            continue
        for wp_id in [str(item).strip() for item in row.get("work_package_ids", []) if str(item).strip()]:
            mapping.setdefault(wp_id, []).append(row)
    return mapping


def verification_rows_by_wp(verification_ledger: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    mapping: dict[str, list[dict[str, Any]]] = {}
    if not verification_ledger:
        return mapping
    latest_by_packet = verification_ledger.get("latest_by_packet", {})
    if not isinstance(latest_by_packet, dict):
        return mapping
    for row in latest_by_packet.values():
        if not isinstance(row, dict):
            continue
        for wp_id in [str(item).strip() for item in row.get("work_package_ids", []) if str(item).strip()]:
            mapping.setdefault(wp_id, []).append(row)
    return mapping


def backend_truths_for_wp(verification_rows: list[dict[str, Any]]) -> dict[str, Any]:
    backend_rows = [
        row
        for row in verification_rows
        if str(row.get("lane", "")).strip().lower() == "backend"
        and str(row.get("overall_verdict", "")).strip().lower() == "pass"
    ]
    if not backend_rows:
        return {
            "requires_backend_truth": False,
            "requires_persistence_truth": False,
            "service_boundary_truth": True,
            "sql_persistence_truth": True,
            "service_persistence_roundtrip_truth": True,
            "migration_execution": True,
            "missing_truths": [],
        }

    requires_persistence_truth = any(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("requires_persistence_truth"))
        for row in backend_rows
    )
    service_boundary_truth = all(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("service_boundary_truth"))
        for row in backend_rows
    )
    sql_persistence_truth = all(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("sql_persistence_truth"))
        for row in backend_rows
        if bool(row.get("backend_evidence", {}).get("requires_persistence_truth"))
    )
    service_persistence_roundtrip_truth = all(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("service_persistence_roundtrip_truth"))
        for row in backend_rows
        if bool(row.get("backend_evidence", {}).get("requires_persistence_truth"))
    )
    migration_execution = all(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("migration_execution"))
        for row in backend_rows
        if bool(row.get("backend_evidence", {}).get("requires_persistence_truth"))
    )

    missing_truths: list[str] = []
    if not service_boundary_truth:
        missing_truths.append("service_boundary_truth")
    if requires_persistence_truth and not sql_persistence_truth:
        missing_truths.append("sql_persistence_truth")
    if requires_persistence_truth and not service_persistence_roundtrip_truth:
        missing_truths.append("service_persistence_roundtrip_truth")
    if requires_persistence_truth and not migration_execution:
        missing_truths.append("migration_execution")
    return {
        "requires_backend_truth": True,
        "requires_persistence_truth": requires_persistence_truth,
        "service_boundary_truth": service_boundary_truth,
        "sql_persistence_truth": sql_persistence_truth,
        "service_persistence_roundtrip_truth": service_persistence_roundtrip_truth,
        "migration_execution": migration_execution,
        "missing_truths": missing_truths,
    }


def infer_wp_lane(runtime_rows: list[dict[str, Any]], verification_rows: list[dict[str, Any]]) -> str:
    for row in verification_rows:
        lane = str(row.get("lane", "")).strip().lower()
        if lane in {"backend", "frontend", "platform"}:
            return lane
    for row in runtime_rows:
        packet_id = str(row.get("packet_id", "")).strip().lower()
        if packet_id.endswith(":backend"):
            return "backend"
        if packet_id.endswith(":frontend"):
            return "frontend"
        if packet_id.endswith(":platform"):
            return "platform"
    return ""


def runtime_rows_for_lane(runtime_rows: list[dict[str, Any]], lane: str) -> list[dict[str, Any]]:
    normalized_lane = str(lane).strip().lower()
    if normalized_lane not in {"backend", "frontend", "platform"}:
        return runtime_rows
    selected = []
    for row in runtime_rows:
        packet_lane = str(row.get("lane", "")).strip().lower()
        packet_id = str(row.get("packet_id", "")).strip().lower()
        if packet_lane == normalized_lane or packet_id.endswith(f":{normalized_lane}"):
            selected.append(row)
    return selected or runtime_rows


def analyze_phase3_wp_gate(
    *,
    implementation_bindings: dict[str, Any],
    test_report: dict[str, Any],
    typecheck_report: dict[str, Any] | None = None,
    lint_report: dict[str, Any] | None = None,
    build_report: dict[str, Any] | None = None,
    verification_ledger: dict[str, Any] | None = None,
    runtime_environment_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = implementation_bindings.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("implementation_bindings must contain rows")

    passed_tests = parse_passed_tests(test_report)
    wp_to_required_tests: dict[str, set[str]] = {}
    wp_to_optional_tests: dict[str, set[str]] = {}
    wp_to_layer_tests: dict[str, dict[str, set[str]]] = {}
    wp_lane_hints: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        tests = {str(item).strip() for item in row.get("test_targets", []) if str(item).strip()}
        required_tests, optional_tests = split_required_optional_tests(tests)
        implementation_targets = {
            str(item).strip() for item in row.get("implementation_targets", []) if str(item).strip()
        }
        lane_hint = infer_binding_lane_hint(
            test_targets=tests,
            implementation_targets=implementation_targets,
        )
        layer_tests = split_tests_by_validation_layer(tests, lane_hint=lane_hint)
        for wp in [str(item).strip() for item in row.get("work_packages", []) if str(item).strip()]:
            wp_to_required_tests.setdefault(wp, set()).update(required_tests)
            wp_to_optional_tests.setdefault(wp, set()).update(optional_tests)
            if lane_hint and wp not in wp_lane_hints:
                wp_lane_hints[wp] = lane_hint
            current_layers = wp_to_layer_tests.setdefault(
                wp,
                {
                    "L1-db-sql": set(),
                    "L2-atomic-api": set(),
                    "L3-composed-api": set(),
                    "L4-flow-api": set(),
                    "optional": set(),
                },
            )
            for layer_name, layer_entries in layer_tests.items():
                current_layers[layer_name].update(layer_entries)

    build_green = report_is_pass(build_report) if build_report is not None else True
    lint_green = report_is_pass(lint_report) if lint_report is not None else True
    typecheck_green = report_is_pass(typecheck_report) if typecheck_report is not None else True
    runtime_by_wp = runtime_rows_by_wp(runtime_environment_ledger)
    verification_by_wp = verification_rows_by_wp(verification_ledger)

    wp_rows: list[dict[str, Any]] = []
    failed_wps: list[str] = []
    runtime_blocked_wps: list[str] = []
    for wp_id in sorted(set(wp_to_required_tests) | set(wp_to_optional_tests)):
        required_tests = sorted(wp_to_required_tests.get(wp_id, set()))
        optional_tests = sorted(wp_to_optional_tests.get(wp_id, set()))
        missing_required_tests = sorted(test for test in required_tests if test not in passed_tests)
        missing_optional_tests = sorted(test for test in optional_tests if test not in passed_tests)
        runtime_rows = runtime_by_wp.get(wp_id, [])
        verification_rows = verification_by_wp.get(wp_id, [])
        lane = infer_wp_lane(runtime_rows, verification_rows) or wp_lane_hints.get(wp_id, "")
        relevant_runtime_rows = runtime_rows_for_lane(runtime_rows, lane)
        runtime_available = (
            all(str(row.get("current_availability", "")).strip() == "available" for row in relevant_runtime_rows)
            if relevant_runtime_rows
            else True
        )
        required_runtime_environments = sorted(
            {
                str(row.get("required_runtime_environment", "")).strip()
                for row in relevant_runtime_rows
                if str(row.get("required_runtime_environment", "")).strip()
            }
        )
        runtime_blocked_capabilities = sorted(
            {
                str(item).strip()
                for row in relevant_runtime_rows
                for item in row.get("blocked_capabilities", [])
                if str(item).strip()
            }
        )
        backend_truth = backend_truths_for_wp(verification_rows)
        layer_tests = wp_to_layer_tests.get(
            wp_id,
            {
                "L1-db-sql": set(),
                "L2-atomic-api": set(),
                "L3-composed-api": set(),
                "L4-flow-api": set(),
                "optional": set(),
            },
        )
        layer_order = ("L1-db-sql", "L2-atomic-api", "L3-composed-api", "L4-flow-api")
        enforce_layer_order = lane != "frontend" and bool(required_tests)
        layer_results: list[dict[str, Any]] = []
        blocking_layer = ""
        for layer_name in layer_order:
            required_layer_tests = sorted(layer_tests.get(layer_name, set()))
            missing_layer_tests = sorted(test for test in required_layer_tests if test not in passed_tests)
            layer_pass = (not required_layer_tests or not missing_layer_tests) if enforce_layer_order else True
            if not layer_pass and not blocking_layer:
                blocking_layer = layer_name
            layer_results.append(
                {
                    "layer": layer_name,
                    "required_count": len(required_layer_tests),
                    "passed_count": len(required_layer_tests) - len(missing_layer_tests),
                    "missing_tests": missing_layer_tests,
                    "status": "pass" if layer_pass else "blocked",
                }
            )
        has_verification_evidence = bool(verification_by_wp.get(wp_id, []))
        pending_dispatch_validation = (
            bool(missing_required_tests)
            and not has_verification_evidence
            and bool(runtime_rows)
            and runtime_available
        )
        wp_static_green = (
            not missing_required_tests
            and build_green
            and lint_green
            and typecheck_green
            and not backend_truth["missing_truths"]
            and not blocking_layer
        )
        wp_pass = wp_static_green and runtime_available
        if wp_pass:
            status = "pass"
        elif pending_dispatch_validation:
            status = "ready"
        elif wp_static_green and not runtime_available:
            status = "runtime-blocked"
            runtime_blocked_wps.append(wp_id)
        else:
            status = "blocked" if not required_tests else "in-progress"
        if not wp_pass and status not in {"runtime-blocked", "ready"}:
            failed_wps.append(wp_id)
        wp_rows.append(
            {
                "wp_id": wp_id,
                "relevant_test_count": len(required_tests),
                "passed_test_count": len(required_tests) - len(missing_required_tests),
                "missing_tests": missing_required_tests,
                "optional_test_count": len(optional_tests),
                "passed_optional_test_count": len(optional_tests) - len(missing_optional_tests),
                "missing_optional_tests": missing_optional_tests,
                "runtime_environment_available": runtime_available,
                "required_runtime_environments": required_runtime_environments,
                "runtime_blocked_capabilities": runtime_blocked_capabilities,
                "backend_truth_required": backend_truth["requires_backend_truth"],
                "backend_persistence_truth_required": backend_truth["requires_persistence_truth"],
                "backend_service_boundary_truth": backend_truth["service_boundary_truth"],
                "backend_sql_persistence_truth": backend_truth["sql_persistence_truth"],
                "backend_service_persistence_roundtrip_truth": backend_truth["service_persistence_roundtrip_truth"],
                "backend_migration_execution": backend_truth["migration_execution"],
                "missing_backend_truths": backend_truth["missing_truths"],
                "lane": lane or "unknown",
                "validation_layer_enforced": enforce_layer_order,
                "validation_layers": layer_results,
                "blocking_validation_layer": blocking_layer,
                "status": status,
            }
        )

    return {
        "overall_quality_gate": "pass"
        if not failed_wps and not runtime_blocked_wps and build_green and lint_green and typecheck_green
        else "fail",
        "recommended_formal_state": "implementation-ready"
        if not failed_wps and not runtime_blocked_wps and build_green and lint_green and typecheck_green
        else "implementation-in-progress",
        "checks": {
            "work_package_count": len(wp_rows),
            "passed_work_package_count": len(wp_rows) - len(failed_wps) - len(runtime_blocked_wps),
            "runtime_blocked_work_package_count": len(runtime_blocked_wps),
            "build_gate": build_green,
            "lint_gate": lint_green,
            "typecheck_gate": typecheck_green,
        },
        "rows": wp_rows,
        "failed_work_packages": failed_wps,
        "runtime_blocked_work_packages": runtime_blocked_wps,
    }


def build_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    lines = [
        "# Phase-3 WP Gate Cycle Report",
        "",
        "## Gate",
        f"- overall_quality_gate: {report['wp_gate_report']['overall_quality_gate']}",
        f"- recommended_formal_state: {report['wp_gate_report']['recommended_formal_state']}",
        f"- passed_work_package_count: {report['wp_gate_report']['checks']['passed_work_package_count']}",
        f"- work_package_count: {report['wp_gate_report']['checks']['work_package_count']}",
        "",
        "## Runtime",
        f"- dispatchable_packet_count: {report['runtime_summary'].get('dispatchable_packet_count', 0)}",
        f"- in_progress_packet_count: {report['runtime_summary'].get('in_progress_packet_count', 0)}",
        f"- verified_packet_count: {report['runtime_summary'].get('verified_packet_count', 0)}",
        f"- current_dispatch_wave: {report['runtime_summary'].get('current_dispatch_wave', 'none')}",
        "",
        "## Work Packages",
    ]
    for row in report["wp_gate_report"].get("rows", []) or [{"wp_id": "none", "status": ""}]:
        if row["wp_id"] == "none":
            lines.append("- none")
        else:
            lines.append(
                f"- {row['wp_id']} [{row['status']}] passed={row['passed_test_count']}/{row['relevant_test_count']}"
            )
    return localize_phase3_wp_gate_cycle_report("\n".join(lines) + "\n", output_locale)


def run_wp_gate_cycle(
    *,
    output_dir: Path,
    test_report_path: Path,
    implementation_bindings_path: Path | None = None,
    typecheck_report_path: Path | None = None,
    lint_report_path: Path | None = None,
    build_report_path: Path | None = None,
    verification_ledger_path: Path | None = None,
    runtime_environment_ledger_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    implementation_path = implementation_bindings_path or (output_dir / "implementation-bindings.json")
    execution_loop_plan_path = output_dir / "execution-loop-plan.json"
    ledger_path = verification_ledger_path or (output_dir / "phase3-verification-ledger.json")
    runtime_ledger_path = runtime_environment_ledger_path or (output_dir / "runtime-environment-ledger.json")
    if not implementation_path.exists():
        raise ValueError(f"implementation bindings missing: {implementation_path}")
    if not execution_loop_plan_path.exists():
        raise ValueError(f"execution loop plan missing: {execution_loop_plan_path}")

    base_test_report = load_json(test_report_path)
    ledger = load_verification_ledger_if_exists(ledger_path)
    ledger_inputs = synthesize_gate_inputs_from_ledger(ledger) if ledger else {}
    combined_passed_tests = sorted(
        {
            str(item).strip()
            for item in [
                *(base_test_report.get("passed_tests", []) if isinstance(base_test_report.get("passed_tests"), list) else []),
                *(ledger_inputs.get("test_report", {}).get("passed_tests", []) if isinstance(ledger_inputs.get("test_report", {}).get("passed_tests"), list) else []),
            ]
            if str(item).strip()
        }
    )

    wp_gate_report = analyze_phase3_wp_gate(
        implementation_bindings=load_json(implementation_path),
        test_report={
            **base_test_report,
            "passed_tests": combined_passed_tests,
        },
        typecheck_report=ledger_inputs.get("typecheck_report") or load_json_if_exists(typecheck_report_path),
        lint_report=ledger_inputs.get("lint_report") or load_json_if_exists(lint_report_path),
        build_report=ledger_inputs.get("build_report") or load_json_if_exists(build_report_path),
        verification_ledger=ledger,
        runtime_environment_ledger=load_json_if_exists(runtime_ledger_path),
    )
    wp_gate_path = output_dir / "phase3-wp-gate.json"
    wp_gate_md_path = output_dir / "phase3-wp-gate.md"
    write_text(wp_gate_path, json.dumps(wp_gate_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    runtime_summary = run_runtime_cycle(
        execution_loop_plan_path=execution_loop_plan_path,
        output_dir=output_dir,
        worker_run_report_path=output_dir / "worker-run-report.json",
        wp_gate_report_path=wp_gate_path,
        runtime_environment_ledger_path=runtime_ledger_path if runtime_ledger_path.exists() else None,
    )
    report = {
        "wp_gate_report": wp_gate_report,
        "runtime_summary": {
            key: value
            for key, value in runtime_summary.items()
            if key
            in {
                "dispatchable_packet_count",
                "ready_packet_count",
                "queued_packet_count",
                "in_progress_packet_count",
                "implemented_packet_count",
                "verified_packet_count",
                "blocked_packet_count",
                "current_dispatch_wave",
                "overall_status",
                "output_path",
                "manifest_path",
            }
        },
        "wp_gate_path": str(wp_gate_path),
        "wp_gate_markdown_path": str(wp_gate_md_path),
    }
    write_text(wp_gate_md_path, build_markdown(report))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply WP gate results and refresh runtime state")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--test-report", required=True)
    parser.add_argument("--implementation-bindings")
    parser.add_argument("--typecheck-report")
    parser.add_argument("--lint-report")
    parser.add_argument("--build-report")
    parser.add_argument("--verification-ledger")
    parser.add_argument("--runtime-environment-ledger")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = run_wp_gate_cycle(
        output_dir=Path(args.output_dir).resolve(),
        test_report_path=Path(args.test_report).resolve(),
        implementation_bindings_path=Path(args.implementation_bindings).resolve() if args.implementation_bindings else None,
        typecheck_report_path=Path(args.typecheck_report).resolve() if args.typecheck_report else None,
        lint_report_path=Path(args.lint_report).resolve() if args.lint_report else None,
        build_report_path=Path(args.build_report).resolve() if args.build_report else None,
        verification_ledger_path=Path(args.verification_ledger).resolve() if args.verification_ledger else None,
        runtime_environment_ledger_path=Path(args.runtime_environment_ledger).resolve()
        if args.runtime_environment_ledger
        else None,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["wp_gate_report"]["overall_quality_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
