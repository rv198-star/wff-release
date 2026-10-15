#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import argparse

from common.action_card_authority_projection import action_card_report_allows_implementation
from common.agentic_decision_authority import load_json_object
from common.output_language import resolve_output_locale
from common.wff_core_runtime import WFFCoreConsumerError, require_capability_binding
from phase3.impl_action_cards import run_impl_action_cards
from phase3.impl_context import emit_summary, write_json
from phase3.impl_db_schema import run_impl_db_schema
from phase3.run_impl_api_docs import main as api_docs_main
from phase3.run_impl_backend import main as backend_main
from phase3.run_impl_frontend import main as frontend_main
from phase3.run_impl_verification import main as verification_main
from phase3.agentic_implementation_authority import (
    P3AgenticImplementationAuthorityError,
    apply_p3_agentic_implementation_authority_to_workspace,
    finalize_p3_agentic_implementation_application,
    prepare_and_accept_p3_implementation_authority,
)
from phase3.p3_realization_decisions import (
    persist_p3_realization_knowledge,
    resolve_project_artifact_root,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase-3 implementation aggregate capability")
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--project-artifact-root",
        default="",
        help=(
            "project-level human artifact root for p3-realization-decisions.md; "
            "full-lifecycle orchestration should pass the case root explicitly"
        ),
    )
    parser.add_argument("--title", default="Phase-3 Implementation")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--enable-frontend", action="store_true")
    parser.add_argument(
        "--ui-ia-contract",
        default="",
        help="explicit current UI IA contract required when --enable-frontend requests supported Agentic frontend authoring",
    )
    parser.add_argument(
        "--mainline-verification-mode",
        choices=("disabled", "if-ready", "strict-runtime"),
        default="disabled",
        help=(
            "keep the historical structural aggregate by default; use strict-runtime for current-generation "
            "S3 materialization, runtime evidence, Trace and delivery closure"
        ),
    )
    parser.add_argument(
        "--strict-runtime",
        dest="mainline_verification_mode",
        action="store_const",
        const="strict-runtime",
        help="alias for --mainline-verification-mode strict-runtime",
    )
    parser.add_argument("--install-toolchain", action="store_true")
    parser.add_argument("--run-runtime-smoke", action="store_true")
    parser.add_argument(
        "--frontend-interaction-spec",
        action="append",
        default=[],
        help="current project Playwright spec under tests/e2e; repeat for every requested frontend interaction evidence file",
    )
    parser.add_argument(
        "--install-playwright-browser",
        action="store_true",
        help="install Chromium before requested frontend browser/runtime evidence",
    )
    parser.add_argument(
        "--thinking-value-gain-mode",
        choices=("off", "full-use"),
        default="off",
        help="record the requested P3 TVG strategy; accepted Agentic implementation authority remains the semantic source of truth",
    )
    parser.add_argument(
        "--thinking-value-gain-output-profile",
        choices=("insight_dense", "balanced", "coverage_rich"),
        default="coverage_rich",
        help="record the requested P3 TVG output profile when TVG is enabled",
    )
    parser.add_argument(
        "--authority-delta-ledger",
        default="",
        help="optional current-decision P3 Authority Delta ledger for local persistence/runtime precision",
    )
    parser.add_argument(
        "--agentic-source-root",
        default="",
        help="optional same-decision S3 root containing materialized @wff:agentic blocks",
    )
    parser.add_argument(
        "--validation-level",
        choices=("fast", "focused", "strict"),
        default="strict",
        help="runtime evidence depth when mainline verification is enabled",
    )
    parser.add_argument(
        "--critical-targeted-evidence-only",
        dest="full_targeted_evidence",
        action="store_false",
        help="use critical targeted evidence instead of the strict full-targeted set",
    )
    parser.add_argument(
        "--full-targeted-evidence",
        dest="full_targeted_evidence",
        action="store_true",
        help="run the full targeted evidence set; default for strict-runtime",
    )
    parser.set_defaults(full_targeted_evidence=True)
    parser.add_argument(
        "--agentic-implementation-decision",
        default="",
        help=(
            "accepted current-snapshot host-Agent implementation decision; "
            "when omitted, the canonical phase2-root/p3-agentic-implementation-decision.json is used if present"
        ),
    )
    parser.add_argument("--output-locale", default=resolve_output_locale())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        require_capability_binding(
            "implementation-delivery",
            phase_id="P3",
            route_key="phase-3",
            required_contracts=(
                "phase-contract",
                "handoff-contract",
                "artifact-identity-contract",
                "evidence-contract",
                "claim-state-contract",
            ),
        )
    except WFFCoreConsumerError as exc:
        print(f"[BLOCKED] {exc}")
        return 2
    phase2_root = Path(args.phase2_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    project_artifact_root = resolve_project_artifact_root(
        phase2_root=phase2_root,
        output_dir=output_dir,
        explicit_root=Path(args.project_artifact_root).resolve()
        if str(args.project_artifact_root or "").strip()
        else None,
    )
    ui_ia_contract_path = (
        Path(args.ui_ia_contract).resolve()
        if str(args.ui_ia_contract or "").strip()
        else None
    )
    if args.enable_frontend:
        if ui_ia_contract_path is None:
            try:
                from phase3.ui_ia_contract_compiler import compile_ui_ia_contract_only
            except ModuleNotFoundError as exc:
                print(f"[BLOCKED] requested frontend clean path lacks current UI IA compiler dependency: {exc.name}")
                return 2
            ui_ia_contract_path = output_dir / ".phase3-evidence" / "ui-ia-contract.json"
            try:
                compiled_ui = compile_ui_ia_contract_only(
                    phase2_root=phase2_root,
                    output_path=ui_ia_contract_path,
                    ui_locale=resolve_output_locale(args.output_locale),
                )
            except (OSError, ValueError) as exc:
                print(f"[BLOCKED] current P1/P2 authority cannot compile requested frontend UI IA: {exc}")
                return 2
            print(
                "[INFO] compiled current UI IA for requested frontend without fixing P3 realization detail: "
                f"{len(compiled_ui.get('pages', []))} pages -> {ui_ia_contract_path}"
            )
        if not ui_ia_contract_path.is_file() or ui_ia_contract_path.is_symlink():
            print("[BLOCKED] --ui-ia-contract must be a readable regular file")
            return 2
    explicit_decision = str(args.agentic_implementation_decision or "").strip()
    canonical_decision = phase2_root / "p3-agentic-implementation-decision.json"
    decision_path = (
        Path(explicit_decision).resolve()
        if explicit_decision
        else canonical_decision.resolve()
        if canonical_decision.is_file() and not canonical_decision.is_symlink()
        else None
    )
    action_cards = run_impl_action_cards(
        phase2_root=phase2_root,
        output_dir=output_dir,
        output_locale=resolve_output_locale(args.output_locale),
    )
    if not action_card_report_allows_implementation(action_cards):
        print("[BLOCKED] Action Card semantic convergence failed; implementation authority/code generation is not allowed")
        return 2
    try:
        implementation_authority = prepare_and_accept_p3_implementation_authority(
            phase2_root=phase2_root,
            output_dir=output_dir,
            decision_path=decision_path,
            action_card_root=output_dir,
        )
    except P3AgenticImplementationAuthorityError as exc:
        print(f"[BLOCKED] {exc}")
        return 2
    if args.mainline_verification_mode != "disabled":
        from phase3.impl_mainline_closure import run_impl_mainline_closure

        if args.mainline_verification_mode == "strict-runtime" and args.validation_level != "strict":
            print("[BLOCKED] strict-runtime requires --validation-level strict")
            return 2
        agentic_source_root = (
            Path(args.agentic_source_root).resolve()
            if str(args.agentic_source_root or "").strip()
            else None
        )
        authority_delta_ledger = (
            load_json_object(Path(args.authority_delta_ledger).resolve())
            if str(args.authority_delta_ledger or "").strip()
            else None
        )
        try:
            closure = run_impl_mainline_closure(
                phase2_root=phase2_root,
                output_dir=output_dir,
                authority=implementation_authority,
                title=args.title,
                version=args.version,
                agentic_source_root=agentic_source_root,
                authority_delta_ledger=authority_delta_ledger,
                project_artifact_root=project_artifact_root,
                install_toolchain=bool(args.install_toolchain),
                run_runtime_smoke=bool(args.run_runtime_smoke),
                verification_mode=args.mainline_verification_mode,
                validation_level=args.validation_level,
                full_targeted_evidence=bool(args.full_targeted_evidence),
                enable_frontend=bool(args.enable_frontend),
                ui_ia_contract_path=ui_ia_contract_path,
                frontend_interaction_specs=[Path(item).resolve() for item in args.frontend_interaction_spec],
                install_playwright_browser=bool(args.install_playwright_browser),
            )
        except ModuleNotFoundError as exc:
            print(f"[BLOCKED] selected install profile lacks P3 runtime-closure dependency: {exc.name}")
            return 2
        except ValueError as exc:
            print(f"[BLOCKED] P3 runtime closure authority is invalid: {exc}")
            return 2
        summary = {
            "artifact_kind": "phase3-impl-aggregate-report",
            "quality_gate": closure["quality_gate"],
            "action_cards": action_cards,
            "agentic_implementation_authority": {
                "decision_id": implementation_authority.get("decision_id"),
                "decision_digest": implementation_authority.get("decision_digest"),
                "authority_digest": implementation_authority.get("content_digest"),
            },
            "mainline_runtime_closure": closure,
            "realization_decisions": closure.get("realization_decisions", {}),
            "thinking_value_gain_mode": args.thinking_value_gain_mode,
            "thinking_value_gain_output_profile": args.thinking_value_gain_output_profile,
            "overall_claim": {
                "recommended_formal_state": (
                    "implementation-ready" if closure["quality_gate"] == "pass" else "implementation-in-progress"
                ),
                "decision": "continue" if closure["quality_gate"] == "pass" else "return-required",
                "minimum_rerun": "P4" if closure["quality_gate"] == "pass" else "P3",
            },
            "claim_ceiling": closure["claim_ceiling"],
        }
        write_json(output_dir / "phase3-impl-aggregate-report.json", summary)
        return emit_summary(summary)

    authority_delta_ledger = (
        load_json_object(Path(args.authority_delta_ledger).resolve())
        if str(args.authority_delta_ledger or "").strip()
        else None
    )
    realization_knowledge = persist_p3_realization_knowledge(
        phase2_root=phase2_root,
        output_dir=output_dir,
        project_artifact_root=project_artifact_root,
        authority=implementation_authority,
        supplied_ledger=authority_delta_ledger,
    )
    db_schema = run_impl_db_schema(phase2_root=phase2_root, output_dir=output_dir)
    verification_generate_code = verification_main(
        [
            "--mode",
            "generate-tests",
            "--phase2-root",
            str(phase2_root),
            "--output-dir",
            str(output_dir),
        ]
    )
    backend_code = backend_main(
        [
            "--phase2-root",
            str(phase2_root),
            "--output-dir",
            str(output_dir),
            "--title",
            args.title,
            "--version",
            args.version,
        ]
    )
    agentic_projection = apply_p3_agentic_implementation_authority_to_workspace(
        output_dir=output_dir,
        authority=implementation_authority,
    )
    api_docs_code = api_docs_main(
        [
            "--baseline-openapi",
            str(output_dir / "contracts" / "openapi.yaml"),
            "--output-dir",
            str(output_dir / "api-docs"),
            "--title",
            f"{args.title} API Documentation",
            "--output-locale",
            args.output_locale,
        ]
    )
    frontend_code = 0
    frontend_report: dict[str, object] = {}
    if args.enable_frontend:
        frontend_argv = [
            "--phase2-root",
            str(phase2_root),
            "--output-dir",
            str(output_dir),
            "--title",
            args.title,
            "--version",
            args.version,
            "--ui-ia-contract",
            str(ui_ia_contract_path),
            "--implementation-authority",
            str(output_dir / "p3-agentic-implementation-authority.json"),
            "--authority-delta-ledger",
            str(realization_knowledge["authority_delta_ledger_path"]),
            "--project-artifact-root",
            str(project_artifact_root),
        ]
        if str(args.agentic_source_root or "").strip():
            frontend_argv.extend(["--agentic-source-root", str(Path(args.agentic_source_root).resolve())])
        frontend_code = frontend_main(frontend_argv)
        try:
            frontend_report = load_json_object(output_dir / "impl-frontend-report.json")
        except (OSError, ValueError):
            frontend_report = {}
    verification_code = verification_main(["--mode", "verify", "--workspace-root", str(output_dir)])
    implementation_application = finalize_p3_agentic_implementation_application(
        output_dir=output_dir,
        authority=implementation_authority,
    )
    semantic_blocking_count = int(
        implementation_application.get("ledger", {}).get("counts", {}).get("blocking", 0) or 0
    )
    backend_structural_green = bool(
        backend_code == 0
        and frontend_code == 0
        and api_docs_code == 0
        and verification_generate_code == 0
        and verification_code == 0
    )
    application_complete = bool(
        implementation_application.get("application", {}).get("application_status") == "complete"
    )
    frontend_authoring_status = str(
        ((frontend_report.get("authoring") if isinstance(frontend_report, dict) else {}) or {}).get("status") or ""
    )
    frontend_runtime_pending = bool(args.enable_frontend and frontend_authoring_status == "materialized")
    overall_state = (
        "implementation-ready"
        if backend_structural_green
        and application_complete
        and semantic_blocking_count == 0
        and not args.enable_frontend
        else "implementation-in-progress"
    )
    summary = {
        "artifact_kind": "phase3-impl-aggregate-report",
        "quality_gate": "pass"
        if overall_state == "implementation-ready"
        else "blocked",
        "action_cards": action_cards,
        "realization_decisions": realization_knowledge,
        "db_schema": db_schema,
        "verification_generate_exit_code": verification_generate_code,
        "backend_exit_code": backend_code,
        "api_docs_exit_code": api_docs_code,
        "frontend_exit_code": frontend_code,
        "frontend_authoring": frontend_report.get("authoring", {}) if isinstance(frontend_report, dict) else {},
        "frontend_runtime_pending": frontend_runtime_pending,
        "verification_exit_code": verification_code,
        "agentic_implementation_authority": {
            "decision_id": implementation_authority.get("decision_id"),
            "decision_digest": implementation_authority.get("decision_digest"),
            "authority_digest": implementation_authority.get("content_digest"),
        },
        "agentic_projection": agentic_projection["projection"],
        "thinking_value_gain_mode": args.thinking_value_gain_mode,
        "thinking_value_gain_output_profile": args.thinking_value_gain_output_profile,
        "backend_runtime_verification": {
            "status": "pass" if backend_structural_green else "blocked",
            "scope": "structural generation/verification; not current-generation runtime execution",
        },
        "semantic_realization": {
            "status": implementation_application.get("ledger", {}).get("status"),
            "counts": implementation_application.get("ledger", {}).get("counts", {}),
            "missing_bindings": implementation_application.get("ledger", {}).get("missing_bindings", []),
        },
        "overall_claim": {
            "recommended_formal_state": overall_state,
            "decision": "continue" if overall_state == "implementation-ready" else "return-required",
            "minimum_rerun": "P4" if overall_state == "implementation-ready" else "P3",
        },
        "claim_ceiling": (
            "Requested frontend complete-product source realization may be materialized, but P3 still requires current real "
            "Web/API browser evidence including a first-entry-to-outcome consumer journey before frontend implementation can close. "
            "Independent P4 consumer/product qualification remains separate."
            if args.enable_frontend
            else (
                "accepted host-Agent implementation semantics are projected into code/tests/bindings, but this modular profile "
                "does not claim current-generation runtime/Trace confirmation unless the exact application receipt is complete"
            )
        ),
    }
    write_json(output_dir / "phase3-impl-aggregate-report.json", summary)
    return emit_summary(summary)


if __name__ == "__main__":
    raise SystemExit(main())
