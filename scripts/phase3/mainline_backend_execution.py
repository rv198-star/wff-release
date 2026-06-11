from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase3.execution_loop_builder import build_verification_commands
from phase3.validation_levels import build_validation_profile, normalize_validation_level
from phase3.wp_gate_cycle import analyze_phase3_wp_gate
from phase3.worker_packet_runner import record_verification_report, run_verification_commands


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_json_if_exists(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def normalize_target(value: str) -> str:
    return str(value).strip().replace("\\", "/")


def is_backend_implementation_target(value: str) -> bool:
    normalized = normalize_target(value).lower()
    if not normalized:
        return False
    return not normalized.startswith("apps/web/")


def classify_backend_test_targets(test_targets: list[str]) -> dict[str, list[str]]:
    classified = {
        "sql": [],
        "contract": [],
        "scenario": [],
        "replay": [],
        "unit": [],
    }
    for raw_target in test_targets:
        target = normalize_target(raw_target)
        lowered = target.lower()
        if not target:
            continue
        if lowered.startswith("tests/sql/") or ".sql.test." in lowered:
            bucket = "sql"
        elif lowered.startswith("tests/contracts/") or ".contract.test." in lowered:
            bucket = "contract"
        elif lowered.startswith("tests/scenarios/") or ".scenario.test." in lowered:
            bucket = "scenario"
        elif lowered.startswith("tests/replays/") or ".replay.test." in lowered:
            bucket = "replay"
        elif lowered.startswith("tests/unit/api/"):
            bucket = "unit"
        else:
            continue
        if target not in classified[bucket]:
            classified[bucket].append(target)
    return classified


def build_phase3_mainline_backend_packet(
    *,
    implementation_bindings: dict[str, Any],
    validation_level: str = "",
    full_targeted_evidence: bool = True,
) -> dict[str, Any]:
    validation_level = normalize_validation_level(
        validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )
    validation_profile = build_validation_profile(
        validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )
    rows = implementation_bindings.get("rows", [])
    if not isinstance(rows, list):
        rows = []

    implementation_targets: list[str] = []
    source_rows: list[dict[str, str]] = []
    work_package_ids: list[str] = []
    collected_tests: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        for raw_target in row.get("implementation_targets", []):
            target = normalize_target(raw_target)
            if is_backend_implementation_target(target) and target not in implementation_targets:
                implementation_targets.append(target)
        for raw_wp in row.get("work_packages", []):
            wp_id = normalize_target(raw_wp)
            if wp_id and wp_id not in work_package_ids:
                work_package_ids.append(wp_id)
        source_id = normalize_target(str(row.get("source_id", "")))
        source_type = normalize_target(str(row.get("source_type", "")))
        source_subject = normalize_target(str(row.get("source_subject", "")))
        if source_id:
            source_rows.append(
                {
                    "source_id": source_id,
                    "source_type": source_type,
                    "source_subject": source_subject,
                }
            )
        for raw_test in row.get("test_targets", []):
            test_target = normalize_target(raw_test)
            if test_target and test_target not in collected_tests:
                collected_tests.append(test_target)

    test_targets = classify_backend_test_targets(collected_tests)
    primary_test_categories = [key for key, values in test_targets.items() if values]

    return {
        "packet_id": "mainline:backend",
        "lane": "backend",
        "worker_packet_status": "ready",
        "dispatch_state": "mainline-internal",
        "primary_test_categories": primary_test_categories,
        "implementation_targets": implementation_targets,
        "work_package_ids": work_package_ids,
        "source_rows": source_rows,
        "test_targets": test_targets,
        "validation_level": validation_level,
        "validation_profile": validation_profile,
        "verification_commands": build_verification_commands(
            "backend",
            test_targets,
            validation_level=validation_level,
            full_targeted_evidence=full_targeted_evidence,
        ),
        "coordination_notes": [
            "This internal packet exists only to produce minimal backend execution evidence for the backend-first mainline.",
            "It is not an optional dispatch-lane handoff and should not be treated as a user-facing workflow step.",
        ],
    }


def next_mainline_verification_run_dir(output_dir: Path) -> Path:
    root = output_dir / ".phase3-mainline-execution" / "backend-runs"
    root.mkdir(parents=True, exist_ok=True)
    existing = [path for path in root.iterdir() if path.is_dir() and path.name.startswith("run-")]
    next_index = len(existing) + 1
    return root / f"run-{next_index:03d}"


def resolve_report_path(raw: object) -> Path | None:
    normalized = str(raw or "").strip()
    if not normalized:
        return None
    return Path(normalized).resolve()


def write_mainline_wp_gate_report(
    *,
    output_dir: Path,
    implementation_bindings: dict[str, Any],
    verification_execution: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    ledger_path = output_dir / "phase3-verification-ledger.json"
    targeted_test_report = load_json_if_exists(resolve_report_path(verification_execution.get("test_report_path"))) or {}
    full_test_report = load_json_if_exists(resolve_report_path(verification_execution.get("full_test_report_path"))) or {}
    unit_test_report = load_json_if_exists(resolve_report_path(verification_execution.get("unit_test_report_path"))) or {}

    combined_passed_tests = sorted(
        {
            str(item).strip()
            for item in [
                *(targeted_test_report.get("passed_tests", []) if isinstance(targeted_test_report.get("passed_tests"), list) else []),
                *(full_test_report.get("passed_tests", []) if isinstance(full_test_report.get("passed_tests"), list) else []),
                *(unit_test_report.get("passed_tests", []) if isinstance(unit_test_report.get("passed_tests"), list) else []),
            ]
            if str(item).strip()
        }
    )
    combined_failed_tests = sorted(
        {
            str(item).strip()
            for item in [
                *(targeted_test_report.get("failed_tests", []) if isinstance(targeted_test_report.get("failed_tests"), list) else []),
                *(full_test_report.get("failed_tests", []) if isinstance(full_test_report.get("failed_tests"), list) else []),
                *(unit_test_report.get("failed_tests", []) if isinstance(unit_test_report.get("failed_tests"), list) else []),
            ]
            if str(item).strip()
        }
    )
    wp_gate_report = analyze_phase3_wp_gate(
        implementation_bindings=implementation_bindings,
        test_report={
            "passed_tests": combined_passed_tests,
            "failed_tests": combined_failed_tests,
        },
        typecheck_report=load_json_if_exists(resolve_report_path(verification_execution.get("typecheck_report_path"))),
        lint_report=load_json_if_exists(resolve_report_path(verification_execution.get("lint_report_path"))),
        build_report=load_json_if_exists(resolve_report_path(verification_execution.get("build_report_path"))),
        verification_ledger=load_json_if_exists(ledger_path),
    )
    wp_gate_report_path = output_dir / "phase3-wp-gate.json"
    write_text(
        wp_gate_report_path,
        json.dumps(wp_gate_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return str(wp_gate_report_path), wp_gate_report


def execute_phase3_mainline_backend_verification(
    *,
    output_dir: Path,
    implementation_bindings_path: Path,
    actor: str = "run_phase3_first_version",
    note: str = "",
    validation_level: str = "",
    full_targeted_evidence: bool = True,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    implementation_bindings = json.loads(implementation_bindings_path.read_text(encoding="utf-8"))
    validation_level = normalize_validation_level(
        validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )
    validation_profile = build_validation_profile(
        validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )
    packet = build_phase3_mainline_backend_packet(
        implementation_bindings=implementation_bindings,
        validation_level=validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )
    run_dir = next_mainline_verification_run_dir(output_dir)
    packet_path = output_dir / ".phase3-mainline-execution" / "mainline-backend-packet.json"
    summary_path = output_dir / ".phase3-mainline-execution" / "mainline-backend-verification-summary.json"

    write_text(packet_path, json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    verification_execution = run_verification_commands(
        packet_document=packet,
        workspace_root=output_dir,
        run_dir=run_dir,
    )
    record_verification_report(
        ledger_path=output_dir / "phase3-verification-ledger.json",
        verification_report_path=Path(verification_execution["report_path"]).resolve(),
    )
    wp_gate_report_path, wp_gate_report = write_mainline_wp_gate_report(
        output_dir=output_dir,
        implementation_bindings=implementation_bindings,
        verification_execution=verification_execution,
    )

    summary = {
        "attempted": True,
        "actor": actor,
        "note": note.strip() or "internal backend verification for backend-first mainline",
        "packet_id": packet["packet_id"],
        "packet_path": str(packet_path),
        "run_dir": str(run_dir),
        "overall_verdict": verification_execution["overall_verdict"],
        "verification_report_path": verification_execution["report_path"],
        "verification_report_markdown_path": verification_execution["report_markdown_path"],
        "verification_ledger_path": str(output_dir / "phase3-verification-ledger.json"),
        "unit_test_report_path": verification_execution.get("unit_test_report_path", ""),
        "targeted_test_report_path": verification_execution.get("test_report_path", ""),
        "full_test_report_path": verification_execution.get("full_test_report_path", ""),
        "lint_report_path": verification_execution.get("lint_report_path", ""),
        "typecheck_report_path": verification_execution.get("typecheck_report_path", ""),
        "build_report_path": verification_execution.get("build_report_path", ""),
        "wp_gate_report_path": wp_gate_report_path,
        "wp_gate_report_overall_quality_gate": wp_gate_report.get("overall_quality_gate", ""),
        "backend_evidence": verification_execution.get("backend_evidence"),
        "validation_level": validation_level,
        "validation_profile": validation_profile,
        "full_targeted_evidence": bool(full_targeted_evidence),
    }
    write_text(summary_path, json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {
        **summary,
        "summary_path": str(summary_path),
    }
