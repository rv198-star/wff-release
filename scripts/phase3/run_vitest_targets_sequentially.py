#!/usr/bin/env python3
"""
Run Vitest targets sequentially and emit a merged JSON report.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


NON_FAILING_ASSERTION_STATUSES = {"passed", "skipped", "pending"}


def _suite_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("testResults", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _assertion_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for suite in _suite_rows(payload):
        assertions = suite.get("assertionResults", [])
        if not isinstance(assertions, list):
            continue
        rows.extend(item for item in assertions if isinstance(item, dict))
    return rows


def _load_vitest_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _process_output(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return ""


def _byte_count(value: str) -> int:
    return len(value.encode("utf-8"))


def _write_batch_output_logs(
    *,
    report_path: Path,
    batch_index: int,
    completed: subprocess.CompletedProcess[str],
) -> tuple[Path, Path]:
    log_dir = report_path.parent / f"{report_path.stem}-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"batch-{batch_index:03d}.stdout.log"
    stderr_path = log_dir / f"batch-{batch_index:03d}.stderr.log"
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    return stdout_path, stderr_path


def _terminate_process_group(process: subprocess.Popen[str], signal_value: signal.Signals) -> None:
    try:
        os.killpg(process.pid, signal_value)
    except ProcessLookupError:
        return
    except PermissionError:
        process.kill()


def _run_vitest_batch(
    command: list[str],
    *,
    workspace_root: Path,
    timeout_seconds: int,
    env: dict[str, str],
) -> tuple[subprocess.CompletedProcess[str], bool]:
    process = subprocess.Popen(
        command,
        cwd=workspace_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=max(1, int(timeout_seconds)))
        return subprocess.CompletedProcess(command, int(process.returncode or 0), stdout, stderr), False
    except subprocess.TimeoutExpired as exc:
        stdout = _process_output(exc.stdout)
        stderr = _process_output(exc.stderr)
        _terminate_process_group(process, signal.SIGTERM)
        try:
            stdout_after, stderr_after = process.communicate(timeout=5)
        except subprocess.TimeoutExpired as kill_exc:
            stdout += _process_output(kill_exc.stdout)
            stderr += _process_output(kill_exc.stderr)
            _terminate_process_group(process, signal.SIGKILL)
            stdout_after, stderr_after = process.communicate()
        stdout += _process_output(stdout_after)
        stderr += _process_output(stderr_after)
        return subprocess.CompletedProcess(command, 124, stdout, stderr), True


def _synthetic_failure_payload(
    *,
    workspace_root: Path,
    target: str,
    completed: subprocess.CompletedProcess[str] | None,
    reason: str,
    stdout_log_path: Path | None = None,
    stderr_log_path: Path | None = None,
) -> dict[str, Any]:
    resolved_target = str((workspace_root / target).resolve())
    message_parts = [reason]
    if stdout_log_path is not None:
        message_parts.append(f"stdout_log_path={stdout_log_path}")
    if stderr_log_path is not None:
        message_parts.append(f"stderr_log_path={stderr_log_path}")
    if completed is not None and (completed.stdout or completed.stderr):
        message_parts.append(
            "raw subprocess output is stored in log files; use --show-subprocess-output to mirror it to terminal"
        )
    message = "\n".join(part for part in message_parts if part).strip()
    return {
        "startTime": 0,
        "success": False,
        "testResults": [
            {
                "name": resolved_target,
                "status": "failed",
                "message": message,
                "assertionResults": [],
            }
        ],
    }


def _write_merged_report(
    report_path: Path,
    payloads: list[dict[str, Any]],
    overall_success: bool,
    batch_timing: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    merged = merge_vitest_payloads(payloads)
    merged["success"] = bool(merged["success"]) and overall_success
    if batch_timing is not None:
        merged["phase3_batch_timing"] = batch_timing
    report_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return merged


def merge_vitest_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    suites = [suite for payload in payloads for suite in _suite_rows(payload)]
    assertions = [assertion for payload in payloads for assertion in _assertion_rows(payload)]
    suite_statuses = [str(suite.get("status", "")).strip().lower() for suite in suites]
    assertion_statuses = [str(row.get("status", "")).strip().lower() for row in assertions]
    start_times = [
        int(payload.get("startTime", 0) or 0)
        for payload in payloads
        if str(payload.get("startTime", "")).strip()
    ]
    success = bool(payloads) and all(bool(payload.get("success", False)) for payload in payloads)
    return {
        "numTotalTestSuites": len(suites),
        "numPassedTestSuites": sum(1 for status in suite_statuses if status == "passed"),
        "numFailedTestSuites": sum(1 for status in suite_statuses if status == "failed"),
        "numPendingTestSuites": sum(1 for status in suite_statuses if status == "pending"),
        "numTotalTests": len(assertions),
        "numPassedTests": sum(1 for status in assertion_statuses if status == "passed"),
        "numFailedTests": sum(1 for status in assertion_statuses if status == "failed"),
        "numPendingTests": sum(1 for status in assertion_statuses if status in NON_FAILING_ASSERTION_STATUSES - {"passed"}),
        "numTodoTests": sum(1 for status in assertion_statuses if status == "todo"),
        "startTime": min(start_times) if start_times else 0,
        "success": success,
        "testResults": suites,
    }


def run_vitest_targets_sequentially(
    *,
    workspace_root: Path,
    config_path: str,
    report_path: Path,
    targets: list[str],
    target_timeout_seconds: int = 120,
    batch_size: int = 1,
    show_subprocess_output: bool = False,
) -> dict[str, Any]:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if not targets:
        payload = merge_vitest_payloads([])
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload

    normalized_targets = [str(target).strip() for target in targets if str(target).strip()]
    batches = [
        normalized_targets[index:index + max(1, int(batch_size))]
        for index in range(0, len(normalized_targets), max(1, int(batch_size)))
    ]
    payloads: list[dict[str, Any]] = []
    batch_timing: list[dict[str, Any]] = []
    overall_success = True
    with tempfile.TemporaryDirectory(prefix="vitest-seq-", dir=report_path.parent) as tmp_dir:
        tmp_root = Path(tmp_dir)
        for index, batch_targets in enumerate(batches, start=1):
            if not batch_targets:
                continue
            label = ", ".join(batch_targets)
            sys.stderr.write(f"[vitest-seq] batch {index}/{len(batches)} start {label}\n")
            sys.stderr.flush()
            target_report = tmp_root / f"target-{index:03d}.json"
            command = [
                "pnpm",
                "exec",
                "vitest",
                "run",
                "--config",
                config_path,
                "--reporter=json",
                "--outputFile",
                str(target_report),
                *batch_targets,
            ]
            completed: subprocess.CompletedProcess[str] | None = None
            timed_out = False
            batch_timeout_seconds = max(1, int(target_timeout_seconds)) * max(1, len(batch_targets))
            started_at = time.time()
            started_monotonic = time.monotonic()
            completed, timed_out = _run_vitest_batch(
                command,
                workspace_root=workspace_root,
                timeout_seconds=batch_timeout_seconds,
                env=os.environ.copy(),
            )
            finished_at = time.time()
            duration_ms = int((time.monotonic() - started_monotonic) * 1000)
            stdout_log_path, stderr_log_path = _write_batch_output_logs(
                report_path=report_path,
                batch_index=index,
                completed=completed,
            )
            if show_subprocess_output and completed.stdout:
                sys.stdout.write(completed.stdout)
            if show_subprocess_output and completed.stderr:
                sys.stderr.write(completed.stderr)
            payload = _load_vitest_payload(target_report)
            failure_reason = ""
            if payload is None:
                failure_reason = f"target_timeout_after_{batch_timeout_seconds}_seconds" if timed_out else "framework_report_missing"
                synthetic_payloads = [
                    _synthetic_failure_payload(
                        workspace_root=workspace_root,
                        target=target,
                        completed=completed,
                        reason=failure_reason,
                        stdout_log_path=stdout_log_path,
                        stderr_log_path=stderr_log_path,
                    )
                    for target in batch_targets
                ]
                payload = merge_vitest_payloads(synthetic_payloads)
            elif timed_out:
                failure_reason = f"target_timeout_after_{batch_timeout_seconds}_seconds"
            elif completed.returncode != 0:
                failure_reason = "command_failed"
            payloads.append(payload)
            if completed.returncode != 0:
                overall_success = False
            batch_timing.append(
                {
                    "batch_index": index,
                    "batch_count": len(batches),
                    "targets": batch_targets,
                    "started_at_epoch_s": started_at,
                    "finished_at_epoch_s": finished_at,
                    "duration_ms": duration_ms,
                    "exit_code": int(completed.returncode),
                    "timed_out": timed_out,
                    "failure_reason": failure_reason,
                    "stdout_log_path": str(stdout_log_path),
                    "stderr_log_path": str(stderr_log_path),
                    "stdout_bytes": _byte_count(completed.stdout or ""),
                    "stderr_bytes": _byte_count(completed.stderr or ""),
                }
            )
            _write_merged_report(report_path, payloads, overall_success, batch_timing)
            sys.stderr.write(
                f"[vitest-seq] batch {index}/{len(batches)} done rc={completed.returncode} "
                f"stdout_bytes={_byte_count(completed.stdout or '')} "
                f"stderr_bytes={_byte_count(completed.stderr or '')}\n"
            )
            sys.stderr.flush()

    return _write_merged_report(report_path, payloads, overall_success, batch_timing)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Vitest targets sequentially and merge JSON output")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--config", default="vitest.config.ts")
    parser.add_argument("--report-path", required=True)
    parser.add_argument("--target", action="append", dest="targets", default=[])
    parser.add_argument("--target-timeout-seconds", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument(
        "--show-subprocess-output",
        action="store_true",
        help="mirror child Vitest stdout/stderr to terminal; by default full output is written only to log artifacts",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    merged = run_vitest_targets_sequentially(
        workspace_root=Path(args.workspace_root).resolve(),
        config_path=str(args.config).strip() or "vitest.config.ts",
        report_path=Path(args.report_path).resolve(),
        targets=[str(target).strip() for target in args.targets if str(target).strip()],
        target_timeout_seconds=max(1, int(args.target_timeout_seconds)),
        batch_size=max(1, int(args.batch_size)),
        show_subprocess_output=bool(args.show_subprocess_output),
    )
    return 0 if merged.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
