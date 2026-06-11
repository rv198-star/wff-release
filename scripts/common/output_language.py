#!/usr/bin/env python3
"""
Global output-language policy helpers for human-reviewed generated artifacts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from common.script_data_assets import load_script_json_asset


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "config" / "generated-output-policy.json"
DEFAULT_POLICY = {
    "human_reviewed_output_locale": "zh-CN",
    "env_override": "WFF_OUTPUT_LOCALE",
    "allowed_locales": ["zh-CN", "en"],
    "scope": "human-reviewed generated artifacts and skill-guided outputs",
}

WFF_SCRIPT_DATA_ASSETS = ("scripts/common/data/output-language-replacements-zh.json",)
OUTPUT_LANGUAGE_REPLACEMENTS_ZH = load_script_json_asset(__file__, "output-language-replacements-zh.json")


def _replacement_table(name: str) -> list[tuple[str, str]]:
    table = OUTPUT_LANGUAGE_REPLACEMENTS_ZH.get(name, [])
    return [(str(source), str(target)) for source, target in table]


def _normalize_locale(value: str | None) -> str:
    candidate = str(value or "").strip()
    lowered = candidate.lower()
    if lowered in {"zh", "zh-cn", "zh_cn", "cn"}:
        return "zh-CN"
    if lowered in {"en", "en-us", "en_us", "english"}:
        return "en"
    return candidate or "zh-CN"


def read_output_language_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return dict(DEFAULT_POLICY)
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return dict(DEFAULT_POLICY)
    policy = dict(DEFAULT_POLICY)
    policy.update(payload)
    policy["human_reviewed_output_locale"] = _normalize_locale(
        str(policy.get("human_reviewed_output_locale", DEFAULT_POLICY["human_reviewed_output_locale"]))
    )
    return policy


def resolve_output_locale(explicit: str | None = None) -> str:
    if str(explicit or "").strip():
        return _normalize_locale(explicit)
    policy = read_output_language_policy()
    env_name = str(policy.get("env_override", DEFAULT_POLICY["env_override"]))
    env_value = os.getenv(env_name, "").strip()
    if env_value:
        return _normalize_locale(env_value)
    return _normalize_locale(str(policy.get("human_reviewed_output_locale", "zh-CN")))


def is_zh_output(locale: str | None = None) -> bool:
    return resolve_output_locale(locale) == "zh-CN"


def apply_replacements(text: str, replacements: list[tuple[str, str]]) -> str:
    localized = text
    for source, target in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        localized = localized.replace(source, target)
    return localized


PHASE3_COVERAGE_PLAN_ZH = _replacement_table("PHASE3_COVERAGE_PLAN_ZH")


PHASE3_ACCEPTANCE_REPORT_ZH = _replacement_table("PHASE3_ACCEPTANCE_REPORT_ZH")


PHASE3_EXECUTION_REPORT_ZH = _replacement_table("PHASE3_EXECUTION_REPORT_ZH")


PHASE2_PORTFOLIO_EVIDENCE_ZH = _replacement_table("PHASE2_PORTFOLIO_EVIDENCE_ZH")


PHASE2_ENGINEERING_SPEC_PACK_ZH = _replacement_table("PHASE2_ENGINEERING_SPEC_PACK_ZH")


PHASE2_IMPLEMENTATION_ENTRY_ZH = _replacement_table("PHASE2_IMPLEMENTATION_ENTRY_ZH")


PHASE2_EXECUTION_REPORT_ZH = _replacement_table("PHASE2_EXECUTION_REPORT_ZH")


PHASE1_EXECUTION_REPORT_ZH = _replacement_table("PHASE1_EXECUTION_REPORT_ZH")


PHASE3_DELIVERY_RUNBOOK_ZH = _replacement_table("PHASE3_DELIVERY_RUNBOOK_ZH")


PHASE3_API_DOC_CONSISTENCY_REPORT_ZH = _replacement_table("PHASE3_API_DOC_CONSISTENCY_REPORT_ZH")


PHASE3_CODE_REVIEW_REPORT_ZH = _replacement_table("PHASE3_CODE_REVIEW_REPORT_ZH")


PHASE3_SECURITY_AUDIT_REPORT_ZH = _replacement_table("PHASE3_SECURITY_AUDIT_REPORT_ZH")


PHASE3_RUNTIME_SMOKE_REPORT_ZH = _replacement_table("PHASE3_RUNTIME_SMOKE_REPORT_ZH")


PHASE4_STAGE1_MARKDOWN_ZH = _replacement_table("PHASE4_STAGE1_MARKDOWN_ZH")


PHASE4_STAGE2_EXECUTION_MARKDOWN_ZH = _replacement_table("PHASE4_STAGE2_EXECUTION_MARKDOWN_ZH")


PHASE4_STAGE3_CLOSURE_MARKDOWN_ZH = _replacement_table("PHASE4_STAGE3_CLOSURE_MARKDOWN_ZH")


INSTALL_PACK_AUDIT_ZH = _replacement_table("INSTALL_PACK_AUDIT_ZH")


RELEASE_BUNDLE_AUDIT_ZH = _replacement_table("RELEASE_BUNDLE_AUDIT_ZH")


PHASE3_VERIFICATION_LEDGER_ZH = _replacement_table("PHASE3_VERIFICATION_LEDGER_ZH")


PHASE3_RUNTIME_ENVIRONMENT_LEDGER_ZH = _replacement_table("PHASE3_RUNTIME_ENVIRONMENT_LEDGER_ZH")


PHASE3_EXECUTION_RUNTIME_STATE_ZH = _replacement_table("PHASE3_EXECUTION_RUNTIME_STATE_ZH")


PHASE3_DISPATCH_MANIFEST_ZH = _replacement_table("PHASE3_DISPATCH_MANIFEST_ZH")


PHASE3_DISPATCH_CYCLE_REPORT_ZH = _replacement_table("PHASE3_DISPATCH_CYCLE_REPORT_ZH")


PHASE3_DISPATCH_LOOP_REPORT_ZH = _replacement_table("PHASE3_DISPATCH_LOOP_REPORT_ZH")


PHASE3_WP_GATE_CYCLE_REPORT_ZH = _replacement_table("PHASE3_WP_GATE_CYCLE_REPORT_ZH")


PHASE3_RUNTIME_CYCLE_SUMMARY_ZH = _replacement_table("PHASE3_RUNTIME_CYCLE_SUMMARY_ZH")


PHASE3_TOOLCHAIN_BOOTSTRAP_REPORT_ZH = _replacement_table("PHASE3_TOOLCHAIN_BOOTSTRAP_REPORT_ZH")


PHASE3_WAVE_PLAN_ZH = _replacement_table("PHASE3_WAVE_PLAN_ZH")


PHASE3_WORKER_RUN_REPORT_ZH = _replacement_table("PHASE3_WORKER_RUN_REPORT_ZH")


PHASE3_WORKER_INPUT_PACKET_ZH = _replacement_table("PHASE3_WORKER_INPUT_PACKET_ZH")


PHASE3_EXECUTION_LOOP_PLAN_ZH = _replacement_table("PHASE3_EXECUTION_LOOP_PLAN_ZH")


PHASE3_EXECUTION_PACKET_ZH = _replacement_table("PHASE3_EXECUTION_PACKET_ZH")


PHASE3_WORKER_PACKET_RUNBOOK_ZH = _replacement_table("PHASE3_WORKER_PACKET_RUNBOOK_ZH")


PHASE3_PACKET_RUN_REPORT_ZH = _replacement_table("PHASE3_PACKET_RUN_REPORT_ZH")


PHASE3_VERIFICATION_REPORT_ZH = _replacement_table("PHASE3_VERIFICATION_REPORT_ZH")


P1P4_MAINLINE_CLOSURE_SUMMARY_ZH = _replacement_table("P1P4_MAINLINE_CLOSURE_SUMMARY_ZH")


WO15_DUAL_CASE_VALIDATION_SUMMARY_ZH = _replacement_table("WO15_DUAL_CASE_VALIDATION_SUMMARY_ZH")


def localize_phase3_coverage_plan(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_COVERAGE_PLAN_ZH) if is_zh_output(locale) else text


def localize_phase3_acceptance_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_ACCEPTANCE_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_execution_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_EXECUTION_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase2_portfolio_evidence(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE2_PORTFOLIO_EVIDENCE_ZH) if is_zh_output(locale) else text


def localize_phase2_engineering_spec_pack(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE2_ENGINEERING_SPEC_PACK_ZH) if is_zh_output(locale) else text


def localize_phase2_implementation_entry(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE2_IMPLEMENTATION_ENTRY_ZH) if is_zh_output(locale) else text


def localize_phase2_execution_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE2_EXECUTION_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase1_execution_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE1_EXECUTION_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_delivery_runbook(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_DELIVERY_RUNBOOK_ZH) if is_zh_output(locale) else text


def localize_phase3_api_doc_consistency_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_API_DOC_CONSISTENCY_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_code_review_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_CODE_REVIEW_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_security_audit_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_SECURITY_AUDIT_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_runtime_smoke_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_RUNTIME_SMOKE_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase4_stage1_markdown(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE4_STAGE1_MARKDOWN_ZH) if is_zh_output(locale) else text


def localize_phase4_stage2_execution_markdown(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE4_STAGE2_EXECUTION_MARKDOWN_ZH) if is_zh_output(locale) else text


def localize_phase4_stage3_closure_markdown(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE4_STAGE3_CLOSURE_MARKDOWN_ZH) if is_zh_output(locale) else text


def localize_install_pack_audit(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, INSTALL_PACK_AUDIT_ZH) if is_zh_output(locale) else text


def localize_release_bundle_audit(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, RELEASE_BUNDLE_AUDIT_ZH) if is_zh_output(locale) else text


def localize_phase3_verification_ledger(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_VERIFICATION_LEDGER_ZH) if is_zh_output(locale) else text


def localize_phase3_runtime_environment_ledger(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_RUNTIME_ENVIRONMENT_LEDGER_ZH) if is_zh_output(locale) else text


def localize_phase3_execution_runtime_state(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_EXECUTION_RUNTIME_STATE_ZH) if is_zh_output(locale) else text


def localize_phase3_dispatch_manifest(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_DISPATCH_MANIFEST_ZH) if is_zh_output(locale) else text


def localize_phase3_dispatch_cycle_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_DISPATCH_CYCLE_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_dispatch_loop_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_DISPATCH_LOOP_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_wp_gate_cycle_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_WP_GATE_CYCLE_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_runtime_cycle_summary(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_RUNTIME_CYCLE_SUMMARY_ZH) if is_zh_output(locale) else text


def localize_phase3_toolchain_bootstrap_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_TOOLCHAIN_BOOTSTRAP_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_wave_plan(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_WAVE_PLAN_ZH) if is_zh_output(locale) else text


def localize_phase3_worker_run_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_WORKER_RUN_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_worker_input_packet(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_WORKER_INPUT_PACKET_ZH) if is_zh_output(locale) else text


def localize_phase3_execution_loop_plan(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_EXECUTION_LOOP_PLAN_ZH) if is_zh_output(locale) else text


def localize_phase3_execution_packet(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_EXECUTION_PACKET_ZH) if is_zh_output(locale) else text


def localize_phase3_worker_packet_runbook(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_WORKER_PACKET_RUNBOOK_ZH) if is_zh_output(locale) else text


def localize_phase3_packet_run_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_PACKET_RUN_REPORT_ZH) if is_zh_output(locale) else text


def localize_phase3_verification_report(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, PHASE3_VERIFICATION_REPORT_ZH) if is_zh_output(locale) else text


def localize_p1_p4_mainline_closure_summary(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, P1P4_MAINLINE_CLOSURE_SUMMARY_ZH) if is_zh_output(locale) else text


def localize_wo15_dual_case_validation_summary(text: str, locale: str | None = None) -> str:
    return apply_replacements(text, WO15_DUAL_CASE_VALIDATION_SUMMARY_ZH) if is_zh_output(locale) else text
