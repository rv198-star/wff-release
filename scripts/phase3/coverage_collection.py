#!/usr/bin/env python3
"""
Collect Phase-3 unit-test coverage artifacts and emit a structured coverage gate.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from phase3.worker_packet_runner import build_execution_env, ensure_backend_runtime_preflight, teardown_backend_runtime_preflight


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


def first_existing_path(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def coverage_summary_candidates(workspace_root: Path) -> tuple[Path, ...]:
    return (
        workspace_root / "coverage" / "coverage-summary.json",
        workspace_root / "coverage-summary.json",
    )


def package_script(workspace_root: Path, script_name: str) -> str:
    package_json = load_json_if_exists(workspace_root / "package.json") or {}
    scripts = package_json.get("scripts", {})
    if not isinstance(scripts, dict):
        return ""
    return str(scripts.get(script_name, "")).strip()


def preferred_coverage_script(workspace_root: Path) -> tuple[str, bool]:
    if package_script(workspace_root, "test:coverage:unit"):
        return "test:coverage:unit", False
    if package_script(workspace_root, "test:coverage"):
        return "test:coverage", True
    return "", False


def coverage_runtime_preflight_packet(workspace_root: Path) -> dict[str, Any] | None:
    categories = {
        "sql": workspace_root / "tests" / "sql",
        "contract": workspace_root / "tests" / "contracts",
        "scenario": workspace_root / "tests" / "scenarios",
        "replay": workspace_root / "tests" / "replays",
    }
    test_targets: dict[str, list[str]] = {}
    for category, directory in categories.items():
        if not directory.exists():
            continue
        relative_paths = sorted(
            str(path.relative_to(workspace_root))
            for path in directory.rglob("*.test.ts")
            if path.is_file()
        )
        if relative_paths:
            test_targets[category] = relative_paths
    if not test_targets:
        return None
    return {
        "packet_id": "coverage:workspace",
        "test_targets": test_targets,
    }


def analyze_phase3_coverage(
    *,
    coverage_report: dict[str, object],
    replay_report: dict[str, object] | None = None,
    min_lines_pct: float = 80.0,
    min_functions_pct: float = 80.0,
    min_branches_pct: float = 70.0,
) -> dict[str, object]:
    workspace_totals = coverage_report.get("total", coverage_report)
    if not isinstance(workspace_totals, dict):
        raise ValueError("coverage report must contain an object payload")

    def aggregate_scope(path_matcher) -> dict[str, dict[str, float]] | None:  # type: ignore[no-untyped-def]
        metrics = {
            "lines": {"covered": 0, "total": 0},
            "functions": {"covered": 0, "total": 0},
            "branches": {"covered": 0, "total": 0},
            "statements": {"covered": 0, "total": 0},
        }
        matched = False
        for raw_path, file_report in coverage_report.items():
            if raw_path == "total" or not isinstance(file_report, dict):
                continue
            normalized_path = str(raw_path).replace("\\", "/")
            if not path_matcher(normalized_path):
                continue
            matched = True
            for name in metrics:
                file_metric = file_report.get(name, {})
                if not isinstance(file_metric, dict):
                    continue
                metrics[name]["covered"] += int(file_metric.get("covered", 0) or 0)
                metrics[name]["total"] += int(file_metric.get("total", 0) or 0)
        if not matched:
            return None
        if all(metric["total"] == 0 for metric in metrics.values()):
            return None
        return {
            name: {
                "covered": float(metric["covered"]),
                "total": float(metric["total"]),
                "pct": (float(metric["covered"]) / float(metric["total"]) * 100.0) if metric["total"] else 100.0,
            }
            for name, metric in metrics.items()
        }

    api_runtime_scope = aggregate_scope(
        lambda normalized_path: "/apps/api/" in normalized_path or normalized_path.startswith("apps/api/")
    )
    totals = api_runtime_scope or workspace_totals
    coverage_scope_basis = "api-runtime-files" if api_runtime_scope is not None else "workspace-total"

    def pct(name: str) -> float:
        metric = totals.get(name, {})
        if isinstance(metric, dict):
            return float(metric.get("pct", 0.0))
        return float(metric)

    def summary_from(report: dict[str, object] | None) -> dict[str, float] | None:
        if not isinstance(report, dict):
            return None
        return {
            f"{name}_pct": float((report.get(name, {}) if isinstance(report.get(name, {}), dict) else {}).get("pct", 0.0))
            for name in ("lines", "functions", "branches", "statements")
        }

    lines_pct = pct("lines")
    functions_pct = pct("functions")
    branches_pct = pct("branches")
    statements_pct = pct("statements")

    failures: list[str] = []
    if lines_pct < min_lines_pct:
        failures.append("lines_below_threshold")
    if functions_pct < min_functions_pct:
        failures.append("functions_below_threshold")
    if branches_pct < min_branches_pct:
        failures.append("branches_below_threshold")

    replay_summary = None
    if replay_report is not None:
        passed = int(replay_report.get("passed", replay_report.get("passed_count", 0)))
        total = int(replay_report.get("total", replay_report.get("total_count", 0)))
        replay_summary = {"passed": passed, "total": total}
        if total > 0 and passed < total:
            failures.append("replay_not_fully_green")

    return {
        "overall_quality_gate": "pass" if not failures else "fail",
        "checks": {
            "lines_pct": lines_pct,
            "functions_pct": functions_pct,
            "branches_pct": branches_pct,
            "statements_pct": statements_pct,
            "replay_summary": replay_summary,
            "coverage_scope_basis": coverage_scope_basis,
            "workspace_total": summary_from(workspace_totals),
            "api_runtime_scope": summary_from(api_runtime_scope),
        },
        "failures": failures,
    }


def collect_phase3_coverage(
    *,
    workspace_root: Path,
    output_path: Path | None = None,
    replay_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workspace_root = workspace_root.resolve()
    coverage_summary_path = first_existing_path(*coverage_summary_candidates(workspace_root))
    collection_status = "preexisting-artifact" if coverage_summary_path is not None else "not-collected"
    collection_command = ""
    command_exit_code = 0
    stdout_log_path = ""
    stderr_log_path = ""

    if coverage_summary_path is None:
        script_name, runtime_coupled_coverage = preferred_coverage_script(workspace_root)
        node_modules_ready = (workspace_root / "node_modules").exists()
        if script_name and node_modules_ready:
            reports_root = workspace_root / ".phase3-reports" / "coverage"
            execution_env = build_execution_env(workspace_root=workspace_root, run_dir=reports_root)
            stdout_path = reports_root / "coverage.stdout.log"
            stderr_path = reports_root / "coverage.stderr.log"
            runtime_preflight_packet = coverage_runtime_preflight_packet(workspace_root) if runtime_coupled_coverage else None
            runtime_preflight = {"required": False, "ready": True, "started": False}
            if runtime_preflight_packet is not None:
                runtime_preflight = ensure_backend_runtime_preflight(
                    packet_document=runtime_preflight_packet,
                    workspace_root=workspace_root,
                    execution_env=execution_env,
                    run_dir=reports_root,
                )
            if runtime_preflight.get("required") and not runtime_preflight.get("ready"):
                collection_command = str(runtime_preflight.get("command", ""))
                command_exit_code = 1
                stdout_log_path = str(runtime_preflight.get("stdout_log_path", ""))
                stderr_log_path = str(runtime_preflight.get("stderr_log_path", ""))
                collection_status = str(runtime_preflight.get("failure_reason", "runtime-preflight-failed") or "runtime-preflight-failed")
            else:
                try:
                    completed = subprocess.run(
                        f"pnpm {script_name}",
                        cwd=workspace_root,
                        shell=True,
                        executable="/bin/zsh",
                        text=True,
                        capture_output=True,
                        env=execution_env,
                    )
                finally:
                    if runtime_preflight.get("started"):
                        teardown_backend_runtime_preflight(workspace_root=workspace_root, execution_env=execution_env)
                collection_command = f"pnpm {script_name}"
                command_exit_code = int(completed.returncode)
                stdout_log_path = str(stdout_path)
                stderr_log_path = str(stderr_path)
                write_text(stdout_path, completed.stdout)
                write_text(stderr_path, completed.stderr)
                coverage_summary_path = first_existing_path(*coverage_summary_candidates(workspace_root))
                if completed.returncode == 0 and coverage_summary_path is not None:
                    collection_status = "collected"
                elif completed.returncode != 0:
                    collection_status = "collection-command-failed"
                else:
                    collection_status = "coverage-summary-missing-after-command"
        elif script_name:
            collection_status = "toolchain-not-ready-for-coverage"
        else:
            collection_status = "coverage-script-missing"

    if coverage_summary_path is None:
        report = {
            "collected": False,
            "collection_status": collection_status,
            "collection_command": collection_command,
            "command_exit_code": command_exit_code,
            "coverage_summary_path": "",
            "stdout_log_path": stdout_log_path,
            "stderr_log_path": stderr_log_path,
        }
        if output_path is not None:
            write_text(output_path.resolve(), json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return report

    coverage_report = load_json(coverage_summary_path)
    gate = analyze_phase3_coverage(coverage_report=coverage_report, replay_report=replay_report)
    report = {
        **gate,
        "collected": True,
        "collection_status": collection_status,
        "collection_command": collection_command,
        "command_exit_code": command_exit_code,
        "coverage_summary_path": str(coverage_summary_path),
        "stdout_log_path": stdout_log_path,
        "stderr_log_path": stderr_log_path,
    }
    if output_path is not None:
        write_text(output_path.resolve(), json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect or analyze Phase-3 coverage artifacts")
    parser.add_argument("--workspace-root")
    parser.add_argument("--coverage-json")
    parser.add_argument("--replay-json")
    parser.add_argument("--min-lines-pct", type=float, default=80.0)
    parser.add_argument("--min-functions-pct", type=float, default=80.0)
    parser.add_argument("--min-branches-pct", type=float, default=70.0)
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_path = Path(args.output).resolve() if args.output else None
    replay_report = load_json(Path(args.replay_json).resolve()) if args.replay_json else None
    if args.coverage_json:
        report = analyze_phase3_coverage(
            coverage_report=load_json(Path(args.coverage_json).resolve()),
            replay_report=replay_report,
            min_lines_pct=args.min_lines_pct,
            min_functions_pct=args.min_functions_pct,
            min_branches_pct=args.min_branches_pct,
        )
        if output_path is not None:
            write_text(output_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report.get("overall_quality_gate") == "pass" else 1

    if not args.workspace_root:
        raise SystemExit("either --workspace-root or --coverage-json is required")

    report = collect_phase3_coverage(
        workspace_root=Path(args.workspace_root),
        output_path=output_path,
        replay_report=replay_report,
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report.get("collected") else 1


if __name__ == "__main__":
    raise SystemExit(main())
