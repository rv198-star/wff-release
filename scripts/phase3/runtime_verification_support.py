from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from common.host_port_allocator import host_port_in_use
import phase3.execution_runtime_preflight as runtime_preflight
import phase3.verification_execution as verification_execution


def shell_executable() -> str:
    return shutil.which("zsh") or shutil.which("bash") or shutil.which("sh") or "/bin/sh"


def build_execution_env(*, workspace_root: Path, run_dir: Path) -> dict[str, str]:
    return runtime_preflight.build_execution_env(workspace_root=workspace_root, run_dir=run_dir)


def ensure_backend_runtime_preflight(
    *,
    packet_document: dict[str, Any],
    workspace_root: Path,
    execution_env: dict[str, str],
    run_dir: Path,
) -> dict[str, Any]:
    return runtime_preflight.ensure_backend_runtime_preflight(
        packet_document=packet_document,
        workspace_root=workspace_root,
        execution_env=execution_env,
        run_dir=run_dir,
        port_in_use_probe=host_port_in_use,
        subprocess_run=subprocess.run,
        shell_resolver=shell_executable,
        sleep_seconds=runtime_preflight.time.sleep,
    )


def teardown_backend_runtime_preflight(*, workspace_root: Path, execution_env: dict[str, str]) -> None:
    runtime_preflight.teardown_backend_runtime_preflight(
        workspace_root=workspace_root,
        execution_env=execution_env,
        subprocess_run=subprocess.run,
        shell_resolver=shell_executable,
    )


def run_verification_commands(
    *,
    packet_document: dict[str, Any],
    workspace_root: Path,
    run_dir: Path,
) -> dict[str, Any]:
    return verification_execution.run_verification_commands(
        packet_document=packet_document,
        workspace_root=workspace_root,
        run_dir=run_dir,
        shell_resolver=shell_executable,
        subprocess_run=subprocess.run,
        runtime_preflight_starter=ensure_backend_runtime_preflight,
        runtime_preflight_teardown=teardown_backend_runtime_preflight,
    )
