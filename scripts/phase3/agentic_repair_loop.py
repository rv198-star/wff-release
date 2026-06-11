#!/usr/bin/env python3
"""
Prepare and run a Phase-3-local Agentic repair loop from an existing P3 checkpoint.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Callable

from phase3.mainline_backend_execution import execute_phase3_mainline_backend_verification
from phase3.phase3_toolchain_bootstrap import bootstrap_phase3_toolchain
from phase3.post_execution_refresh import refresh_phase3_post_execution


COPY_IGNORE_PATTERNS = (
    "node_modules",
    ".phase3-mainline-execution",
    "coverage",
    "dist",
    "build",
    "*.log",
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def resolve_optional_path(value: Any) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    return Path(raw).resolve()


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def copy_phase3_checkpoint(source_root: Path, repair_workspace_root: Path, *, force: bool = False) -> None:
    source_root = source_root.resolve()
    repair_workspace_root = repair_workspace_root.resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f"phase3 root does not exist: {source_root}")
    if source_root == repair_workspace_root or source_root in repair_workspace_root.parents:
        raise ValueError("repair workspace must not be inside the source Phase-3 root")
    if repair_workspace_root.exists() and force:
        shutil.rmtree(repair_workspace_root)
    if repair_workspace_root.exists() and any(repair_workspace_root.iterdir()):
        raise ValueError(f"repair workspace already exists and is not empty: {repair_workspace_root}")
    shutil.copytree(
        source_root,
        repair_workspace_root,
        ignore=shutil.ignore_patterns(*COPY_IGNORE_PATTERNS),
    )


def repair_packets_by_route(interrupt: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    active: list[dict[str, Any]] = []
    return_bound: list[dict[str, Any]] = []
    packets = interrupt.get("repair_packets", [])
    if not isinstance(packets, list):
        packets = []
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        route = str(packet.get("repair_route") or "").strip()
        owner_phase = str(packet.get("owner_phase") or "").strip()
        if route == "repair-in-phase" and owner_phase == "P3":
            active.append(dict(packet))
        else:
            return_bound.append(dict(packet))
    return active, return_bound


def build_targeted_gate_command(
    *,
    repair_workspace_root: Path,
    output_root: Path,
    case_name: str,
    version: str,
    output_locale: str,
    install_timeout_seconds: int = 90,
    full_targeted_evidence: bool = False,
) -> str:
    parts = [
        "python3",
        "scripts/phase3/agentic_repair_loop.py",
        "run-targeted-gate",
        "--repair-workspace-root",
        str(repair_workspace_root),
        "--output-root",
        str(output_root),
        "--case-name",
        case_name,
        "--version",
        version,
        "--output-locale",
        output_locale,
        "--install-timeout-seconds",
        str(max(1, int(install_timeout_seconds))),
    ]
    if full_targeted_evidence:
        parts.append("--full-targeted-evidence")
    else:
        parts.append("--critical-targeted-evidence-only")
    return " ".join(parts)


def render_repair_loop_markdown(plan: dict[str, Any], *, output_locale: str = "zh-CN") -> str:
    zh = str(output_locale or "").strip().lower() in {"zh", "zh-cn", "cn"}
    title = "# P3 Agentic Checkpoint Repair Loop" if not zh else "# P3 Agentic 检查点返工循环"
    active_title = "## Active P3 Repairs" if not zh else "## P3 内返工项"
    return_title = "## Upstream Returns" if not zh else "## 上游返回项"
    boundary_title = "## Boundary" if not zh else "## 边界"
    lines = [
        title,
        "",
        f"- mode: `{plan.get('mode', '')}`",
        f"- case_name: `{plan.get('case_name', '')}`",
        f"- version: `{plan.get('version', '')}`",
        f"- source_phase3_root: `{plan.get('source_phase3_root', '')}`",
        f"- repair_workspace_root: `{plan.get('repair_workspace_root', '')}`",
        f"- claim_ceiling: `{plan.get('claim_ceiling', '')}`",
        "",
        active_title,
    ]
    active_packets = plan.get("active_repair_packets", [])
    if not active_packets:
        lines.append("- none")
    for packet in active_packets if isinstance(active_packets, list) else []:
        if not isinstance(packet, dict):
            continue
        lines.append(
            f"- `{packet.get('defect_key', '')}` status=`{packet.get('status', '')}` "
            f"rerun=`{packet.get('minimum_rerun_boundary', '')}`"
        )
        if packet.get("packet_type"):
            lines.append(f"  - packet_type: `{packet.get('packet_type', '')}`")
        if packet.get("module_key"):
            lines.append(f"  - module_key: `{packet.get('module_key', '')}`")
        if packet.get("source"):
            lines.append(f"  - source: `{packet.get('source', '')}`")
        if packet.get("rewrite_objective"):
            lines.append(f"  - rewrite_objective: `{packet.get('rewrite_objective', '')}`")
        affected_files = string_list(packet.get("affected_files"))
        if affected_files:
            lines.append(f"  - affected_files: `{', '.join(affected_files)}`")
    lines.extend(["", return_title])
    return_packets = plan.get("return_bound_packets", [])
    if not return_packets:
        lines.append("- none")
    for packet in return_packets if isinstance(return_packets, list) else []:
        if not isinstance(packet, dict):
            continue
        lines.append(
            f"- `{packet.get('defect_key', '')}` owner=`{packet.get('owner_phase', '')}` "
            f"rerun=`{packet.get('minimum_rerun_boundary', '')}`"
        )
        if packet.get("packet_type"):
            lines.append(f"  - packet_type: `{packet.get('packet_type', '')}`")
        if packet.get("module_key"):
            lines.append(f"  - module_key: `{packet.get('module_key', '')}`")
        if packet.get("source"):
            lines.append(f"  - source: `{packet.get('source', '')}`")
        if packet.get("rewrite_objective"):
            lines.append(f"  - rewrite_objective: `{packet.get('rewrite_objective', '')}`")
    lines.extend(
        [
            "",
            boundary_title,
            "- This entry starts from an existing Phase-3 checkpoint.",
            "- Do not re-enter the release dual-case runner for repair.",
            "- Do not regenerate Phase-1 or Phase-2 unless a packet is explicitly returned upstream.",
            "- Run the targeted P3 gate from the repair workspace before changing the formal state.",
            "",
            "## Targeted Gate Command",
            "",
            "```bash",
            str(plan.get("targeted_gate_command", "")),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def prepare_agentic_repair_loop(
    *,
    phase3_root: Path,
    output_root: Path,
    case_name: str,
    version: str,
    output_locale: str = "zh-CN",
    force: bool = False,
) -> dict[str, Any]:
    phase3_root = phase3_root.resolve()
    output_root = output_root.resolve()
    repair_workspace_root = output_root / "repair-workspace"
    interrupt_path = phase3_root / "agentic-repair-interrupt.json"
    verdict_path = phase3_root / "phase-verdict.json"
    bindings_path = phase3_root / "implementation-bindings.json"
    for required_path in (interrupt_path, verdict_path, bindings_path):
        if not required_path.exists():
            raise FileNotFoundError(f"required Phase-3 repair input is missing: {required_path}")

    output_root.mkdir(parents=True, exist_ok=True)
    copy_phase3_checkpoint(phase3_root, repair_workspace_root, force=force)
    interrupt = load_json_object(interrupt_path)
    verdict = load_json_object(verdict_path)
    active_packets, return_bound_packets = repair_packets_by_route(interrupt)

    plan = {
        "artifact_kind": "phase3-agentic-checkpoint-repair-loop",
        "mode": "prepare",
        "case_name": str(case_name).strip(),
        "version": str(version).strip(),
        "source_phase3_root": str(phase3_root),
        "repair_workspace_root": str(repair_workspace_root.resolve()),
        "source_verdict": verdict.get("verdict", ""),
        "source_total_score": verdict.get("total_score"),
        "claim_ceiling": str(verdict.get("recommended_formal_state") or interrupt.get("claim_ceiling") or "implementation-in-progress"),
        "active_repair_packets": active_packets,
        "return_bound_packets": return_bound_packets,
        "forbidden_full_workflow_entrypoints": [
            "release dual-case runner",
            "Phase-1 full trial runner",
            "Phase-2 first-version runner",
        ],
        "targeted_gate_command": build_targeted_gate_command(
            repair_workspace_root=repair_workspace_root.resolve(),
            output_root=output_root,
            case_name=str(case_name).strip(),
            version=str(version).strip(),
            output_locale=output_locale,
            install_timeout_seconds=90,
        ),
        "stop_conditions": [
            "targeted P3 gate proves the active repair packet is closed",
            "packet is routed upstream with evidence and no local P3 rewrite",
            "max repair rounds are exhausted and claim remains capped",
        ],
    }
    write_json(output_root / "agentic-repair-loop.json", plan)
    (output_root / "agentic-repair-loop.md").write_text(
        render_repair_loop_markdown(plan, output_locale=output_locale),
        encoding="utf-8",
    )
    return plan


def classify_repair_gate_verdict(
    *,
    toolchain_status: str,
    verification: dict[str, Any],
    full_targeted_evidence: bool,
) -> str:
    if str(toolchain_status or "").strip() != "ready":
        return "blocked"
    command_verdict = str(verification.get("overall_verdict") or "").strip().lower()
    if command_verdict not in {"pass", "passed"}:
        return "fail"
    wp_gate = str(verification.get("wp_gate_report_overall_quality_gate") or "").strip().lower()
    if wp_gate == "pass":
        return "pass"
    if not full_targeted_evidence:
        return "sample-pass-review-bound"
    return "return-remediate"


def summarize_closure_refresh(refresh_summary: dict[str, Any]) -> dict[str, Any]:
    mainline_summary = refresh_summary.get("mainline_assessment_summary", {})
    if not isinstance(mainline_summary, dict):
        mainline_summary = {}
    phase_verdict = str(refresh_summary.get("phase_verdict") or mainline_summary.get("phase_verdict") or "").strip()
    phase_total_score = refresh_summary.get("phase_total_score", mainline_summary.get("phase_total_score"))
    return {
        "phase_verdict_path": str(refresh_summary.get("phase_verdict_path") or "").strip(),
        "phase_verdict": phase_verdict,
        "phase_total_score": phase_total_score,
        "recommended_formal_state": str(refresh_summary.get("recommended_formal_state") or "").strip(),
        "delivery_gate_path": str(refresh_summary.get("delivery_gate_path") or "").strip(),
        "mainline_assessment_summary": mainline_summary,
    }


def classify_repair_closure_verdict(
    *,
    repair_gate_verdict: str,
    closure_summary: dict[str, Any],
    full_targeted_evidence: bool,
) -> str:
    if not closure_summary:
        return "not-run"
    if not full_targeted_evidence:
        return "sample-pass-review-bound"
    if str(repair_gate_verdict or "").strip() != "pass":
        return str(repair_gate_verdict or "return-remediate").strip() or "return-remediate"
    phase_verdict = str(closure_summary.get("phase_verdict") or "").strip().lower()
    if phase_verdict.startswith("pass"):
        return "pass"
    if phase_verdict == "blocked":
        return "blocked"
    return "return-remediate"


def run_agentic_repair_targeted_gate(
    *,
    repair_workspace_root: Path,
    output_root: Path,
    case_name: str,
    version: str,
    output_locale: str = "zh-CN",
    install_toolchain: bool = False,
    install_timeout_seconds: int = 90,
    full_targeted_evidence: bool = False,
    refresh_closure: bool = False,
    run_runtime_smoke: bool = False,
    toolchain_bootstrap_fn: Callable[..., dict[str, Any]] = bootstrap_phase3_toolchain,
    execute_backend_verification_fn: Callable[..., dict[str, Any]] = execute_phase3_mainline_backend_verification,
    refresh_phase3_post_execution_fn: Callable[..., dict[str, Any]] = refresh_phase3_post_execution,
) -> dict[str, Any]:
    del output_locale

    repair_workspace_root = repair_workspace_root.resolve()
    output_root = output_root.resolve()
    bindings_path = repair_workspace_root / "implementation-bindings.json"
    if not bindings_path.exists():
        raise FileNotFoundError(f"implementation bindings missing in repair workspace: {bindings_path}")

    output_root.mkdir(parents=True, exist_ok=True)
    toolchain_report_path = output_root / "repair-toolchain-bootstrap.json"
    toolchain = toolchain_bootstrap_fn(
        workspace_root=repair_workspace_root,
        install=bool(install_toolchain),
        strict=False,
        output_path=toolchain_report_path,
        install_timeout_seconds=max(1, int(install_timeout_seconds)),
    )
    toolchain_status = str(toolchain.get("overall_status") or "").strip()
    verification: dict[str, Any] = {
        "attempted": False,
        "overall_verdict": "blocked",
        "reason": f"toolchain_not_ready:{toolchain_status or 'unknown'}",
    }
    if toolchain_status == "ready":
        verification = execute_backend_verification_fn(
            output_dir=repair_workspace_root,
            implementation_bindings_path=bindings_path,
            actor="agentic_repair_loop",
            note="P3-local repair targeted gate",
            full_targeted_evidence=bool(full_targeted_evidence),
        )
    repair_gate_verdict = classify_repair_gate_verdict(
        toolchain_status=toolchain_status,
        verification=verification,
        full_targeted_evidence=bool(full_targeted_evidence),
    )
    closure_refresh_summary: dict[str, Any] = {}
    closure_refresh_attempted = False
    if refresh_closure and bool(verification.get("attempted")):
        verification_verdict = str(verification.get("overall_verdict") or "").strip().lower()
        verification_failed = verification_verdict in {"fail", "failed", "blocked"}
        refresh_summary = refresh_phase3_post_execution_fn(
            repair_workspace_root,
            strict_runtime_closure=bool(full_targeted_evidence),
            run_runtime_smoke=bool(run_runtime_smoke),
            skip_coverage_collection=bool(full_targeted_evidence and verification_failed),
            coverage_collection_skip_reason=(
                "repair_targeted_gate_failed" if bool(full_targeted_evidence and verification_failed) else ""
            ),
            toolchain_bootstrap_report_path=toolchain_report_path,
            unit_test_report_path=resolve_optional_path(verification.get("unit_test_report_path", "")),
            wp_gate_report_path=resolve_optional_path(verification.get("wp_gate_report_path", "")),
            verification_ledger_report_path=resolve_optional_path(verification.get("verification_ledger_path", "")),
            runtime_smoke_report_path=resolve_optional_path(verification.get("runtime_smoke_report_path", "")),
        )
        closure_refresh_attempted = True
        closure_refresh_summary = summarize_closure_refresh(refresh_summary)
    repair_closure_verdict = classify_repair_closure_verdict(
        repair_gate_verdict=repair_gate_verdict,
        closure_summary=closure_refresh_summary,
        full_targeted_evidence=bool(full_targeted_evidence),
    )

    result = {
        "artifact_kind": "phase3-agentic-checkpoint-repair-loop-result",
        "mode": "run-targeted-gate",
        "case_name": str(case_name).strip(),
        "version": str(version).strip(),
        "repair_workspace_root": str(repair_workspace_root),
        "repair_gate_verdict": repair_gate_verdict,
        "repair_closure_verdict": repair_closure_verdict,
        "toolchain_bootstrap": toolchain,
        "targeted_gate": verification,
        "full_targeted_evidence": bool(full_targeted_evidence),
        "closure_refresh_requested": bool(refresh_closure),
        "closure_refresh_attempted": closure_refresh_attempted,
        "closure_refresh": closure_refresh_summary,
        "refreshed_phase_verdict": str(closure_refresh_summary.get("phase_verdict") or "").strip(),
        "refreshed_phase_total_score": closure_refresh_summary.get("phase_total_score"),
        "install_timeout_seconds": max(1, int(install_timeout_seconds)),
        "claim_ceiling": "implementation-in-progress",
        "forbidden_full_workflow_entrypoints": [
            "release dual-case runner",
            "Phase-1 full trial runner",
            "Phase-2 first-version runner",
        ],
    }
    write_json(output_root / "agentic-repair-loop-result.json", result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a Phase-3-local Agentic repair loop")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="copy an existing P3 checkpoint into a repair workspace")
    prepare.add_argument("--phase3-root", required=True)
    prepare.add_argument("--output-root", required=True)
    prepare.add_argument("--case-name", default="")
    prepare.add_argument("--version", default="")
    prepare.add_argument("--output-locale", default="zh-CN")
    prepare.add_argument("--force", action="store_true")

    gate = subparsers.add_parser("run-targeted-gate", help="run the P3 targeted gate from a repair workspace")
    gate.add_argument("--repair-workspace-root", required=True)
    gate.add_argument("--output-root", required=True)
    gate.add_argument("--case-name", default="")
    gate.add_argument("--version", default="")
    gate.add_argument("--output-locale", default="zh-CN")
    gate.add_argument("--install-toolchain", action="store_true")
    gate.add_argument("--install-timeout-seconds", type=int, default=90)
    gate.add_argument("--full-targeted-evidence", dest="full_targeted_evidence", action="store_true")
    gate.add_argument("--critical-targeted-evidence-only", dest="full_targeted_evidence", action="store_false")
    gate.add_argument("--refresh-closure", action="store_true")
    gate.add_argument("--run-runtime-smoke", action="store_true")
    gate.set_defaults(full_targeted_evidence=False)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        result = prepare_agentic_repair_loop(
            phase3_root=Path(args.phase3_root),
            output_root=Path(args.output_root),
            case_name=args.case_name,
            version=args.version,
            output_locale=args.output_locale,
            force=bool(args.force),
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    if args.command == "run-targeted-gate":
        result = run_agentic_repair_targeted_gate(
            repair_workspace_root=Path(args.repair_workspace_root),
            output_root=Path(args.output_root),
            case_name=args.case_name,
            version=args.version,
            output_locale=args.output_locale,
            install_toolchain=bool(args.install_toolchain),
            install_timeout_seconds=max(1, int(args.install_timeout_seconds)),
            full_targeted_evidence=bool(args.full_targeted_evidence),
            refresh_closure=bool(args.refresh_closure),
            run_runtime_smoke=bool(args.run_runtime_smoke),
        )
        print(json.dumps(result, ensure_ascii=False))
        if bool(args.refresh_closure):
            return 0 if str(result.get("repair_closure_verdict") or "").strip() == "pass" else 1
        return 0 if str(result.get("repair_gate_verdict") or "").strip() == "pass" else 1
    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
