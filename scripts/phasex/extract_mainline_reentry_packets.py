#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import re
from typing import Any

from common.contamination_boundary import build_contamination_report
from common.script_data_assets import load_script_text_asset


PACKET_BLOCKS = {
    "p1": {
        "field": "px_to_p1_change_source_packet",
        "filename": "p1-existing-system-change-source-packet.md",
        "heading": "# P1 Source Input Packet",
        "required": (
            "packet_subtype",
            "existing-system-change",
            "demand_change_evaluation",
        ),
    },
    "p2": {
        "field": "px_to_p2_architecture_change_intake_packet",
        "filename": "p2-existing-system-architecture-change-intake.md",
        "heading": "# P2 Existing-System Architecture Change Intake Packet",
        "required": (
            "packet_subtype",
            "existing-system-architecture-change",
            "architecture_change_impact_triage",
        ),
    },
}

P1_CONFIRMATION_CHECKLIST_FILENAME = "p1-demand-confirmation-checklist.md"
PX_SEMANTIC_REENTRY_BRIEF_FILENAME = "px-semantic-reentry-brief.md"
PX_CONTAMINATION_REPORT_FILENAME = "px-contamination-report.json"
SCAN_CODE_BASELINE_FILENAME = "wff-x-scan-code-baseline.md"

WFF_SCRIPT_DATA_ASSETS = ("scripts/phasex/data/p1-reentry-packet.md.template",)
P1_REENTRY_PACKET_TEMPLATE = load_script_text_asset(__file__, "p1-reentry-packet.md.template")


TOP_LEVEL_FIELD_RE = re.compile(r"^-\s+([A-Za-z0-9_-]+):\s*$")
LIST_FIELD_RE = re.compile(r"^(?P<indent>\s*)-\s+(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)$")


def extract_list_block(text: str, field_name: str) -> str:
    lines = text.splitlines()
    start_index = -1
    for index, line in enumerate(lines):
        if re.match(rf"^-\s+{re.escape(field_name)}:\s*$", line):
            start_index = index
            break
    if start_index < 0:
        raise ValueError(f"missing wff-x-intake-target-driver field: {field_name}")

    block_lines = [lines[start_index]]
    for line in lines[start_index + 1 :]:
        if TOP_LEVEL_FIELD_RE.match(line):
            break
        block_lines.append(line)
    return "\n".join(block_lines).rstrip() + "\n"


def validate_required_tokens(block: str, required: tuple[str, ...], label: str) -> list[str]:
    return [f"{label} missing required token: {token}" for token in required if token not in block]


def clean_value(raw: str) -> str:
    value = str(raw or "").strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1].strip()
    return value


def block_value(block: str, key: str, default: str = "not provided") -> str:
    lines = block.splitlines()
    for index, line in enumerate(lines):
        match = LIST_FIELD_RE.match(line)
        if not match or match.group("key") != key:
            continue
        value = clean_value(match.group("value"))
        if value:
            return value
        base_indent = len(match.group("indent"))
        child_values: list[str] = []
        for child in lines[index + 1 :]:
            child_match = LIST_FIELD_RE.match(child)
            if child_match and len(child_match.group("indent")) <= base_indent:
                break
            stripped = child.strip()
            if stripped.startswith("- "):
                stripped = stripped[2:].strip()
            if stripped:
                child_values.append(clean_value(stripped))
        if child_values:
            return "; ".join(child_values)
        return default
    return default


CLARIFICATION_FIELD_LABELS = {
    "response_source": "response source",
    "target_success_boundary": "target success boundary",
    "acceptance_boundary": "acceptance boundary",
    "priority_users_workflows": "priority users / workflows",
    "scope_confirmation": "scope confirmation",
    "compatibility_confirmation": "compatibility confirmation",
    "conservative_default_if_unanswered": "conservative default if unanswered",
    "remaining_review_bound_items": "remaining review-bound items",
}


def collect_demand_clarification(block: str) -> dict[str, Any]:
    values = {
        "clarification_status": block_value(block, "clarification_status", ""),
    }
    for key in CLARIFICATION_FIELD_LABELS:
        values[key] = block_value(block, key, "")

    answered_keys = [
        key
        for key in CLARIFICATION_FIELD_LABELS
        if str(values.get(key) or "").strip()
    ]
    status = clean_value(values.get("clarification_status") or "").strip()
    if not status and answered_keys:
        status = "answered"
    if not status:
        status = "not-answered"
    answered = bool(answered_keys) and status != "not-answered"
    if answered and status == "not provided":
        status = "answered"
    if not answered:
        status = "not-answered"
    values["clarification_status"] = status
    values["answered"] = answered
    values["answered_keys"] = answered_keys
    return values


def render_demand_clarification_questions(
    *,
    target_change: str,
    affected_workflows: str,
    preserve: str,
    non_goals: str,
    source_conflicts: str,
    unknowns: str,
    acceptance_pressure: str,
) -> list[str]:
    return [
        "### Demand Clarification Questions",
        "",
        "These are reviewer clarification prompts, not P1 requirements.",
        "If unanswered, P1 must keep the related truth review-bound and must not promote the prompt text into product scope.",
        "",
        "- DCQ-001:",
        f"  - prompt: Confirm the exact business target behind `{target_change}`.",
        "  - default_if_unanswered: Keep the target review-bound and write a conservative demand boundary.",
        "- DCQ-002:",
        f"  - prompt: Confirm the success or failure threshold for `{acceptance_pressure}`.",
        "  - default_if_unanswered: Preserve the pressure as an open acceptance gap.",
        "- DCQ-003:",
        "  - prompt: Confirm priority among the affected workflow groups.",
        f"  - current_workflow_context: `{affected_workflows}`",
        "  - default_if_unanswered: Use the observed workflow only as inferred priority evidence.",
        "- DCQ-004:",
        "  - prompt: Confirm which legacy behavior and scope boundary must not change.",
        f"  - preserve_context: `{preserve}`",
        f"  - non_goal_context: `{non_goals}`",
        "  - default_if_unanswered: Preserve known legacy behavior and keep broader scope out.",
        "- DCQ-005:",
        f"  - prompt: Identify who or what can confirm `{unknowns}` when source conflict is `{source_conflicts}`.",
        "  - default_if_unanswered: Continue without owner confirmation, using conservative compatibility defaults.",
        "",
    ]


def render_demand_confirmation_boundary() -> list[str]:
    return [
        "### Demand Confirmation Boundary",
        "",
        "- Reviewer prompts are emitted in `p1-demand-confirmation-checklist.md`; they are not embedded as P1 source requirements.",
        "- P1 may consume answered addendum facts, claim ceilings, and remaining review-bound items from this packet.",
        "- P1 must not promote unanswered prompts, owner placeholders, or reviewer workflow text into product scope.",
        "",
    ]


def render_demand_confirmation_checklist(
    *,
    clarification: dict[str, Any],
    target_change: str,
    affected_workflows: str,
    preserve: str,
    non_goals: str,
    source_conflicts: str,
    unknowns: str,
    acceptance_pressure: str,
) -> str:
    lines = [
        "# PX-to-P1 Demand Confirmation Checklist",
        "",
        "This sidecar is for reviewer confirmation and source-truth boundary review.",
        "It is not a P1 requirement source and must not be copied into the P1 PRD as product scope.",
        "",
        "## Consumption Boundary",
        "",
        "| Consumer | May consume | Must not consume |",
        "|---|---|---|",
        "| P1 | answered addendum facts, remaining review-bound items, conservative default, claim ceiling | unanswered reviewer prompts as requirements |",
        "| P2 | architecture-relevant confirmed boundaries after P1 convergence | prompt text as architecture decisions |",
        "| P3 | only P2-approved constraints and runtime evidence obligations | PX reviewer checklist text directly |",
        "",
        "## Answered Confirmation Facts",
        "",
        "| Fact ID | Field | Answer | Truth state | P1 handling |",
        "|---|---|---|---|---|",
    ]
    fact_rows = [
        ("DCF-001", "target_success_boundary", "target success boundary"),
        ("DCF-002", "acceptance_boundary", "acceptance boundary"),
        ("DCF-003", "priority_users_workflows", "priority users / workflows"),
        ("DCF-004", "scope_confirmation", "scope confirmation"),
        ("DCF-005", "compatibility_confirmation", "compatibility confirmation"),
        ("DCF-006", "conservative_default_if_unanswered", "conservative default if unanswered"),
    ]
    any_fact = False
    for fact_id, key, label in fact_rows:
        value = str(clarification.get(key) or "").strip()
        if not value:
            continue
        any_fact = True
        lines.append(
            f"| {fact_id} | {label} | {value} | answer-backed / not owner sign-off | use as source clarification; keep claim ceiling explicit |"
        )
    if not any_fact:
        lines.append("| DCF-000 | none | no answered demand clarification facts provided | not-answered | keep demand truth review-bound |")
    lines.extend(
        [
            "",
            "## Remaining Review-Bound Items",
            "",
            "| Item ID | Review-bound item | Default handling until answered |",
            "|---|---|---|",
        ]
    )
    remaining = str(clarification.get("remaining_review_bound_items") or unknowns or "").strip()
    if remaining:
        lines.append(
            f"| DCR-001 | {remaining} | keep review-bound; do not claim owner sign-off, budget approval, UAT, production readiness, or production risk acceptance |"
        )
    else:
        lines.append(
            "| DCR-000 | no explicit remaining review-bound item was provided | keep generic owner / budget / UAT / production claims capped |"
        )
    lines.extend(
        [
            "",
            "## Reviewer Prompts",
            "",
            "These prompts guide human review. They are not product requirements.",
            "",
            "- DCQ-001:",
            f"  - prompt: Confirm the exact business target behind `{target_change}`.",
            "  - default_if_unanswered: Keep the target review-bound and write a conservative demand boundary.",
            "- DCQ-002:",
            f"  - prompt: Confirm the success or failure threshold for `{acceptance_pressure}`.",
            "  - default_if_unanswered: Preserve the pressure as an open acceptance gap.",
            "- DCQ-003:",
            "  - prompt: Confirm priority among the affected workflow groups.",
            f"  - current_workflow_context: `{affected_workflows}`",
            "  - default_if_unanswered: Use the observed workflow only as inferred priority evidence.",
            "- DCQ-004:",
            "  - prompt: Confirm which legacy behavior and scope boundary must not change.",
            f"  - preserve_context: `{preserve}`",
            f"  - non_goal_context: `{non_goals}`",
            "  - default_if_unanswered: Preserve known legacy behavior and keep broader scope out.",
            "- DCQ-005:",
            f"  - prompt: Identify who or what can confirm `{unknowns}` when source conflict is `{source_conflicts}`.",
            "  - default_if_unanswered: Continue without owner confirmation, using conservative compatibility defaults.",
            "",
            "## Checklist Verdict",
            "",
            f"- `clarification_status`: `{clarification['clarification_status']}`",
            "- `p1_requirement_promotion_allowed`: `false-for-prompts`",
            "- `p1_answered_fact_consumption_allowed`: `true-with-claim-ceiling`",
            "",
        ]
    )
    return "\n".join(lines)


def render_demand_clarification_addendum(clarification: dict[str, Any]) -> list[str]:
    lines = [
        "### Demand Clarification Addendum",
        "",
        f"- `clarification_status`: `{clarification['clarification_status']}`",
    ]
    if not clarification["answered"]:
        lines.extend(
            [
                "- `P1 handling`: continue without blocking, keep missing demand truth review-bound, and use conservative compatibility defaults where downstream design needs a provisional route.",
                "- `claim_ceiling`: no user answer, owner confirmation, market validation, UAT, or production authorization is proven by this packet.",
                "",
            ]
        )
        return lines

    for key, label in CLARIFICATION_FIELD_LABELS.items():
        value = str(clarification.get(key) or "").strip()
        if value:
            lines.append(f"- `{label}`: {value}")
    lines.extend(
        [
            "- `P1 handling`: treat answered items as addendum-backed source clarification for demand convergence; keep the remaining items review-bound.",
            "- `claim_ceiling`: this addendum improves P1 source truth, but it is not owner sign-off, UAT, market validation, production readiness, or production risk acceptance.",
            "",
        ]
    )
    return lines


def clarification_truth_statement(clarification: dict[str, Any]) -> str:
    values = [
        str(clarification.get("target_success_boundary") or "").strip(),
        str(clarification.get("acceptance_boundary") or "").strip(),
        str(clarification.get("priority_users_workflows") or "").strip(),
        str(clarification.get("scope_confirmation") or "").strip(),
        str(clarification.get("compatibility_confirmation") or "").strip(),
    ]
    compact = [value for value in values if value]
    if not compact:
        return "Demand clarification addendum was provided."
    return " / ".join(compact)


def sentence_case_label(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", str(value or "")).strip()
    if not cleaned:
        return fallback
    words = cleaned.split()
    if not words:
        return fallback
    return " ".join(word[:1].upper() + word[1:].lower() for word in words)


def compact_domain_phrase(*values: str) -> str:
    text = " ".join(str(value or "") for value in values).casefold()
    if "invoice adjustment" in text:
        return "Invoice Adjustment"
    if "legacy customer id" in text or ("customer id" in text and "partner" in text):
        return "Legacy Customer Id"
    if "oracle" in text and ("report" in text or "reporting" in text):
        return "Oracle Reporting"
    if "finance report" in text or "finance reporting" in text:
        return "Finance Reporting"
    if "order query" in text:
        return "Order Query"
    if "adjustment" in text:
        return "Adjustment"
    match = re.search(
        r"\b([a-z][a-z0-9]*(?:\s+[a-z][a-z0-9]*){0,2})\s+"
        r"(?:route|workflow|endpoint|behavior|policy|request|response|api|module|service|report|reports)\b",
        text,
    )
    if match:
        return sentence_case_label(match.group(1), "Existing Change")
    return "Existing Change"


def entity_name(label: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", label)
    return "".join(word[:1].upper() + word[1:] for word in words) or "ExistingChange"


def legacy_behavior_label(label: str) -> str:
    lowered = str(label or "").strip().lower()
    if not lowered:
        return "legacy behavior"
    return lowered if lowered.startswith("legacy ") else f"legacy {lowered}"


def infer_primary_actor(*values: str) -> str:
    text = " ".join(str(value or "") for value in values).casefold()
    if "invoice" in text or "billing" in text:
        return "Billing operations staff"
    if "partner" in text or "legacy customer id" in text:
        return "Partner operations staff"
    if "oracle" in text or "finance report" in text or "finance reporting" in text:
        return "Finance operations staff"
    if "order" in text or "buyer" in text or "support" in text:
        return "Buyers and support staff"
    if "patient" in text or "clinic" in text or "visit" in text:
        return "Clinic operations staff"
    if "admin" in text or "operator" in text:
        return "Operations staff"
    return "Existing-system users"


def infer_downstream_actor(*values: str) -> str:
    text = " ".join(str(value or "") for value in values).casefold()
    if "partner" in text and ("api" in text or "callback" in text or "customer id" in text):
        return "Partner API consumer"
    if "finance" in text or "report" in text or "oracle" in text:
        return "Finance report consumer"
    if "api" in text or "client" in text or "external" in text:
        return "API or client-system consumer"
    if "support" in text:
        return "Support workflow consumer"
    return "Downstream workflow consumer"


def infer_protected_entity(*values: str) -> str:
    text = " ".join(str(value or "") for value in values).casefold()
    if "invoice" in text:
        return "Invoice"
    if "order" in text:
        return "Order"
    if "legacy customer id" in text or "customer id" in text or "account reference" in text:
        return "CustomerIdentity"
    if "oracle" in text or "finance report" in text or "finance reporting" in text or "reporting" in text:
        return "FinanceReport"
    if "patient" in text:
        return "Patient"
    if "visit" in text:
        return "Visit"
    if "profile" in text or "identity" in text:
        return "UserProfile"
    if "schema" in text or "database" in text:
        return "Record"
    return "ExistingRecord"


def unique_nonempty(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def discover_scan_code_baseline(target_driver: Path) -> Path | None:
    candidate = target_driver.parent / SCAN_CODE_BASELINE_FILENAME
    return candidate if candidate.exists() else None


def extract_existing_system_conventions(scan_text: str) -> dict[str, Any]:
    path_refs = unique_nonempty(
        [
            ref
            for ref in re.findall(r"`([^`]+)`", scan_text)
            if re.search(r"\.(?:py|ts|tsx|js|jsx|java|kt|go|rb|php|cs)$", ref)
            or "/" in ref
        ]
    )
    route_refs = [ref for ref in path_refs if ref.startswith("/")]
    code_paths = [ref for ref in path_refs if not ref.startswith("/")]
    test_refs = [ref for ref in code_paths if re.search(r"(?:^|/)(?:test|tests|spec|specs)(?:/|$)|test_|_test|\.spec\.", ref)]
    package_refs = [ref for ref in code_paths if "/" in ref]
    convention_lines: list[str] = []
    if package_refs:
        convention_lines.append(
            "code_structure: observed package/module paths use slash-separated repository locations such as "
            + ", ".join(package_refs[:3])
        )
    if code_paths:
        if any(path.endswith(".py") for path in code_paths):
            convention_lines.append(
                "file_naming: observed Python module files use lower_snake or compact package filenames; preserve observed public module paths unless P2 accepts a migration"
            )
        else:
            convention_lines.append(
                "file_naming: preserve observed source file and module naming until architecture review accepts a rename"
            )
    if route_refs:
        convention_lines.append(
            "api_route_naming: observed route surfaces use current path names and brace-style parameters such as "
            + ", ".join(route_refs[:3])
        )
    if test_refs:
        convention_lines.append(
            "test_naming: observed test/spec paths should be preserved as compatibility evidence: "
            + ", ".join(test_refs[:3])
        )
    else:
        convention_lines.append(
            "test_naming: not observed in scan-code-baseline; keep test convention review-bound instead of inventing a style"
        )
    if not convention_lines:
        convention_lines.append(
            "review_bound: scan-code-baseline did not expose enough coding, naming, route, or test convention evidence"
        )
    confidence = "medium" if code_paths or route_refs else "low"
    return {
        "code_paths": code_paths,
        "route_refs": route_refs,
        "test_refs": test_refs,
        "convention_lines": convention_lines,
        "confidence": confidence,
        "claim_ceiling": "observed existing-system convention hints only; not a target architecture decision or rename authority",
    }


def build_semantic_reentry_context(
    *,
    p1_block: str,
    p2_block: str,
    scan_text: str,
) -> dict[str, Any]:
    current_state = block_value(p1_block, "current_state_summary")
    target_change = block_value(p1_block, "target_change_summary")
    observed_facts = block_value(p1_block, "observed_business_facts")
    inferred_semantics = block_value(p1_block, "inferred_business_semantics")
    preserve = block_value(p1_block, "legacy_behaviors_to_preserve")
    unknowns = block_value(p1_block, "explicit_unknowns")
    acceptance_pressure = block_value(p1_block, "acceptance_pressure")
    affected_workflows = block_value(p1_block, "affected_users_workflows")
    as_is_boundary = block_value(p2_block, "as_is_boundary_map")
    inventory = block_value(p2_block, "module_service_inventory")
    surface_constraints = block_value(p2_block, "interface_external_surface_constraints")
    compatibility_constraints = block_value(p2_block, "compatibility_constraints")
    change_label = compact_domain_phrase(current_state, target_change, observed_facts, affected_workflows)
    conventions = extract_existing_system_conventions(scan_text)
    source_signals = unique_nonempty(
        [
            current_state,
            target_change,
            observed_facts,
            affected_workflows,
            acceptance_pressure,
            as_is_boundary,
            inventory,
            surface_constraints,
            compatibility_constraints,
        ]
    )
    return {
        "canonical_domain": change_label,
        "primary_actor": infer_primary_actor(observed_facts, affected_workflows, current_state),
        "downstream_actor": infer_downstream_actor(affected_workflows, acceptance_pressure, preserve),
        "protected_entity": infer_protected_entity(change_label, observed_facts, preserve, affected_workflows),
        "protected_behavior": preserve,
        "proof_target": acceptance_pressure,
        "inferred_semantics": inferred_semantics,
        "review_bound_items": unknowns,
        "source_signals": source_signals,
        "existing_system_conventions": conventions,
    }


def render_semantic_reentry_brief(context: dict[str, Any]) -> str:
    conventions = context["existing_system_conventions"]
    lines = [
        "# PX Semantic Reentry Brief",
        "",
        "- purpose: Preserve brownfield source semantics and observed implementation conventions before P1/P2 consume PX output.",
        "- claim_ceiling: semantic bridge only; no owner sign-off, UAT, production readiness, or target architecture decision is implied.",
        f"- canonical_domain: `{context['canonical_domain']}`",
        f"- canonical_primary_actor: `{context['primary_actor']}`",
        f"- canonical_downstream_actor: `{context['downstream_actor']}`",
        f"- protected_entity: `{context['protected_entity']}`",
        f"- protected_behavior: {context['protected_behavior']}",
        f"- proof_target: {context['proof_target']}",
        f"- review_bound_items: {context['review_bound_items']}",
        "- source_signals:",
    ]
    for signal in context["source_signals"]:
        lines.append(f"  - {signal}")
    lines.extend(
        [
            "- existing_system_conventions:",
            f"  - confidence: `{conventions['confidence']}`",
            f"  - claim_ceiling: {conventions['claim_ceiling']}",
        ]
    )
    for line in conventions["convention_lines"]:
        lines.append(f"  - {line}")
    lines.append("")
    return "\n".join(lines)


def render_p1_semantic_reentry_section(context: dict[str, Any]) -> list[str]:
    conventions = context["existing_system_conventions"]
    lines = [
        "### PX Semantic Reentry Brief",
        "",
        "- consumption_rule: Use this as a brownfield source-semantics bridge; do not treat it as owner confirmation or target architecture authority.",
        f"- canonical_domain: `{context['canonical_domain']}`",
        f"- canonical_primary_actor: `{context['primary_actor']}`",
        f"- canonical_downstream_actor: `{context['downstream_actor']}`",
        f"- protected_entity: `{context['protected_entity']}`",
        f"- protected_behavior: {context['protected_behavior']}",
        f"- proof_target: {context['proof_target']}",
        f"- review_bound_items: {context['review_bound_items']}",
        "- source_signals:",
    ]
    for signal in context["source_signals"]:
        lines.append(f"  - {signal}")
    lines.extend(
        [
            "- existing_system_conventions:",
            f"  - confidence: `{conventions['confidence']}`",
            f"  - claim_ceiling: {conventions['claim_ceiling']}",
        ]
    )
    for line in conventions["convention_lines"]:
        lines.append(f"  - {line}")
    lines.append("")
    return lines


def render_existing_system_conventions_section(context: dict[str, Any]) -> list[str]:
    conventions = context["existing_system_conventions"]
    lines = [
        "## Existing-System Conventions",
        "",
        "- consumption_rule: Preserve observed brownfield coding, naming, route, and test conventions as design constraints until P2 explicitly accepts a migration.",
        f"- confidence: `{conventions['confidence']}`",
        f"- claim_ceiling: {conventions['claim_ceiling']}",
    ]
    for line in conventions["convention_lines"]:
        lines.append(f"- {line}")
    lines.append("")
    return lines


def render_p1_packet(*, block: str, semantic_context: dict[str, Any] | None = None) -> str:
    current_state = block_value(block, "current_state_summary")
    target_change = block_value(block, "target_change_summary")
    observed_facts = block_value(block, "observed_business_facts")
    inferred_semantics = block_value(block, "inferred_business_semantics")
    preserve = block_value(block, "legacy_behaviors_to_preserve")
    source_conflicts = block_value(block, "source_conflicts")
    unknowns = block_value(block, "explicit_unknowns")
    non_goals = block_value(block, "non_goals")
    acceptance_pressure = block_value(block, "acceptance_pressure")
    change_intent = block_value(block, "change_intent")
    business_impact = block_value(block, "business_impact")
    affected_workflows = block_value(block, "affected_users_workflows")
    scope_boundaries = block_value(block, "non_goals_scope_boundaries")
    proceed_decision = block_value(block, "proceed_decision")
    claim_ceiling = block_value(block, "claim_ceiling")
    clarification = collect_demand_clarification(block)
    clarification_statement = clarification_truth_statement(clarification)
    remaining_review_bound = str(
        clarification.get("remaining_review_bound_items") or unknowns
    ).strip()
    change_label = compact_domain_phrase(current_state, target_change, observed_facts, affected_workflows)
    change_entity = entity_name(change_label)
    legacy_label = legacy_behavior_label(change_label)
    primary_actor = infer_primary_actor(observed_facts, affected_workflows, current_state)
    downstream_actor = infer_downstream_actor(affected_workflows, acceptance_pressure, preserve)
    protected_entity = infer_protected_entity(change_label, observed_facts, preserve, affected_workflows)
    protected_label = re.sub(r"(?<!^)(?=[A-Z])", " ", protected_entity).lower()
    request_entity = f"{change_entity}Request"
    policy_entity = f"{change_entity}Policy"
    response_entity = f"{change_entity}Response"
    audit_entity = f"{change_entity}Audit"

    target_change_clarification_block = ""
    desired_outcome_clarification_block = ""
    acceptance_clarification_block = ""
    nonfunctional_requirements_block = ""
    truth_state_clarification_row = ""
    open_truth_gap_clarification_row = ""
    if clarification["answered"]:
        target_change_clarification_block = '\n'.join(
            [
                "Demand clarification addendum provides a sharper target and acceptance boundary:",
                f"- {clarification_statement}",
            ]
        ) + "\n"
        desired_outcome_clarification_block = '\n'.join(
            [
                f"- Clarified target success boundary: {clarification.get('target_success_boundary')}",
                f"- Clarified acceptance boundary: {clarification.get('acceptance_boundary')}",
                f"- Clarified priority workflow: {clarification.get('priority_users_workflows')}",
                f"- Clarified scope / compatibility boundary: {clarification.get('scope_confirmation')} / {clarification.get('compatibility_confirmation')}",
            ]
        ) + "\n"
        acceptance_clarification_block = '\n'.join(
            [
                f"- Clarified acceptance boundary: {clarification.get('acceptance_boundary')}",
                f"- Clarified target success boundary: {clarification.get('target_success_boundary')}",
                f"- Remaining review-bound items: {remaining_review_bound}",
            ]
        ) + "\n"
        nonfunctional_requirements_block = '\n'.join(
            [
                "### Non-functional Requirements",
                "",
                f"- Clarified load target: {clarification.get('target_success_boundary')}",
                f"- Clarified response-time target: {clarification.get('acceptance_boundary')}",
                f"- Rollout safety target: {clarification.get('conservative_default_if_unanswered')}",
                "",
            ]
        ) + "\n"
        truth_state_clarification_row = (
            f"| TS-005 | Demand clarification addendum: {clarification_statement} | answer-backed | PX-to-P1 Demand Clarification Addendum | source clarification for P1 convergence |\n"
        )
        if remaining_review_bound:
            open_truth_gap_clarification_row = (
                f"| GAP-002 | {remaining_review_bound} | Clarification answered part of the target, but remaining constraints still cap P1 claims. | Keep these items review-bound unless later evidence confirms them. |\n"
            )
        handoff_clarification_block = '\n'.join(
            [
                f"- Clarification addendum: {clarification_statement}",
                f"- Review-bound after addendum: {remaining_review_bound}",
            ]
        )
    else:
        handoff_clarification_block = "- Review-bound: target semantics, owner availability, and product acceptance policy."

    semantic_reentry_section = (
        '\n'.join(render_p1_semantic_reentry_section(semantic_context)) + "\n"
        if semantic_context
        else ""
    )

    return P1_REENTRY_PACKET_TEMPLATE.format(
        current_state=current_state,
        target_change=target_change,
        observed_facts=observed_facts,
        inferred_semantics=inferred_semantics,
        preserve=preserve,
        source_conflicts=source_conflicts,
        unknowns=unknowns,
        non_goals=non_goals,
        acceptance_pressure=acceptance_pressure,
        change_intent=change_intent,
        business_impact=business_impact,
        affected_workflows=affected_workflows,
        scope_boundaries=scope_boundaries,
        proceed_decision=proceed_decision,
        claim_ceiling=claim_ceiling,
        change_label=change_label,
        change_label_lower=change_label.lower(),
        legacy_label=legacy_label,
        primary_actor=primary_actor,
        downstream_actor=downstream_actor,
        protected_entity=protected_entity,
        protected_label=protected_label,
        request_entity=request_entity,
        policy_entity=policy_entity,
        response_entity=response_entity,
        audit_entity=audit_entity,
        target_change_clarification_block=target_change_clarification_block,
        semantic_reentry_section=semantic_reentry_section,
        desired_outcome_clarification_block=desired_outcome_clarification_block,
        demand_confirmation_boundary='\n'.join(render_demand_confirmation_boundary()),
        demand_clarification_addendum='\n'.join(render_demand_clarification_addendum(clarification)),
        acceptance_clarification_block=acceptance_clarification_block,
        nonfunctional_requirements_block=nonfunctional_requirements_block,
        truth_state_clarification_row=truth_state_clarification_row,
        open_truth_gap_clarification_row=open_truth_gap_clarification_row,
        handoff_clarification_block=handoff_clarification_block,
    )


def render_p2_packet(*, block: str, semantic_context: dict[str, Any] | None = None) -> str:
    as_is_boundary = block_value(block, "as_is_boundary_map")
    inventory = block_value(block, "module_service_inventory")
    data_constraints = block_value(block, "data_storage_constraints")
    surface_constraints = block_value(block, "interface_external_surface_constraints")
    runtime_constraints = block_value(block, "runtime_deployment_constraints")
    compatibility_constraints = block_value(block, "compatibility_constraints")
    health_pressure = block_value(block, "technical_health_pressure")
    target_pressure = block_value(block, "target_architecture_pressure")
    unresolved_questions = block_value(block, "unresolved_architecture_questions")
    impact_level = block_value(block, "change_impact_level")
    compatibility_strategy = block_value(block, "compatibility_strategy")
    migration_strategy = block_value(block, "migration_strategy")
    rollback_strategy = block_value(block, "rollback_strategy")
    gate_status = block_value(block, "decision_gate_status")
    evidence_state = block_value(block, "evidence_state_ledger")
    entry_points = block_value(block, "recommended_P2_entry_points")

    return "\n".join(
        [
            "# P2 Existing-System Architecture Change Intake Packet",
            "",
            "## Existing Architecture Boundary",
            "",
            f"- As-is boundary map: {as_is_boundary}",
            f"- Module/service inventory: {inventory}",
            f"- Runtime/deployment constraint: {runtime_constraints}",
            "",
            "## Protected Compatibility Constraints",
            "",
            f"- Data/storage constraint: {data_constraints}",
            f"- External/interface surface constraint: {surface_constraints}",
            f"- Compatibility constraint: {compatibility_constraints}",
            "",
            *(render_existing_system_conventions_section(semantic_context) if semantic_context else []),
            "## Architecture Change Impact Triage",
            "",
            f"- Change impact level: {impact_level}",
            f"- Technical health pressure: {health_pressure}",
            f"- Target architecture pressure: {target_pressure}",
            f"- Unresolved architecture question: {unresolved_questions}",
            f"- Decision gate status: {gate_status}",
            "",
            "## Change Strategy Guardrails",
            "",
            f"- Compatibility strategy: {compatibility_strategy}",
            f"- Migration strategy: {migration_strategy}",
            f"- Rollback strategy: {rollback_strategy}",
            f"- Evidence state: {evidence_state}",
            f"- Recommended P2 entry points: {entry_points}",
            "",
            "## P2 Handling Guidance",
            "",
            "- Run architecture change impact triage before normal target architecture expression.",
            "- Keep observed system facts, inferred architecture implications, explicit unknowns, and review-bound claims separate.",
            "- Prefer additive compatibility, adapter seams, staged migration, rollback, and protected legacy behavior.",
            "- Do not silently promote AC-3 / AC-4 scale changes as ready-for-P3 without explicit architecture review.",
            "",
        ]
    )


def write_packet(
    *,
    output_dir: Path,
    label: str,
    block: str,
    semantic_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = PACKET_BLOCKS[label]
    output_path = output_dir / str(spec["filename"])
    if label == "p1":
        packet_text = render_p1_packet(block=block, semantic_context=semantic_context)
    elif label == "p2":
        packet_text = render_p2_packet(block=block, semantic_context=semantic_context)
    else:
        packet_text = f"{spec['heading']}\n\n{block.rstrip()}\n"
    output_path.write_text(packet_text, encoding="utf-8")
    return {
        "label": label,
        "field": spec["field"],
        "path": str(output_path),
        "required_token_issues": validate_required_tokens(block, spec["required"], label),
    }


def write_p1_confirmation_checklist(*, output_dir: Path, block: str) -> dict[str, Any]:
    output_path = output_dir / P1_CONFIRMATION_CHECKLIST_FILENAME
    target_change = block_value(block, "target_change_summary")
    affected_workflows = block_value(block, "affected_users_workflows")
    preserve = block_value(block, "legacy_behaviors_to_preserve")
    source_conflicts = block_value(block, "source_conflicts")
    unknowns = block_value(block, "explicit_unknowns")
    non_goals = block_value(block, "non_goals")
    acceptance_pressure = block_value(block, "acceptance_pressure")
    clarification = collect_demand_clarification(block)
    output_path.write_text(
        render_demand_confirmation_checklist(
            clarification=clarification,
            target_change=target_change,
            affected_workflows=affected_workflows,
            preserve=preserve,
            non_goals=non_goals,
            source_conflicts=source_conflicts,
            unknowns=unknowns,
            acceptance_pressure=acceptance_pressure,
        ),
        encoding="utf-8",
    )
    return {
        "label": "p1-demand-confirmation-checklist",
        "field": "px_to_p1_change_source_packet",
        "path": str(output_path),
        "required_token_issues": [],
    }


def write_semantic_reentry_brief(*, output_dir: Path, context: dict[str, Any]) -> dict[str, Any]:
    output_path = output_dir / PX_SEMANTIC_REENTRY_BRIEF_FILENAME
    output_path.write_text(render_semantic_reentry_brief(context), encoding="utf-8")
    return {
        "label": "px-semantic-reentry-brief",
        "field": "px_semantic_reentry_brief",
        "path": str(output_path),
        "required_token_issues": [],
    }


def write_px_contamination_report(
    *,
    output_dir: Path,
    target_driver: Path,
    packets: list[dict[str, Any]],
    sidecars: list[dict[str, Any]],
) -> dict[str, Any]:
    parts = [target_driver.read_text(encoding="utf-8")]
    for row in [*packets, *sidecars]:
        path_value = row.get("path")
        if not path_value:
            continue
        path = Path(str(path_value))
        if path.exists() and path.suffix.lower() in {".md", ".markdown"}:
            parts.append(path.read_text(encoding="utf-8"))
    output_path = output_dir / PX_CONTAMINATION_REPORT_FILENAME
    build_contamination_report(
        "\n\n".join(parts),
        source_label=str(target_driver),
        boundary="px-to-p1-p2",
        output_path=output_path,
    )
    return {
        "label": "px-contamination-report",
        "field": "px_contamination_report",
        "path": str(output_path),
        "required_token_issues": [],
    }


def extract_packets(target_driver: Path, output_dir: Path) -> dict[str, Any]:
    text = target_driver.read_text(encoding="utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    packets = []
    sidecars = []
    issues = []
    packet_blocks: dict[str, str] = {}
    for label, spec in PACKET_BLOCKS.items():
        try:
            block = extract_list_block(text, str(spec["field"]))
        except ValueError as exc:
            issues.append(str(exc))
            continue
        packet_blocks[label] = block
    scan_path = discover_scan_code_baseline(target_driver)
    scan_text = scan_path.read_text(encoding="utf-8") if scan_path is not None else ""
    semantic_context = (
        build_semantic_reentry_context(
            p1_block=packet_blocks["p1"],
            p2_block=packet_blocks["p2"],
            scan_text=scan_text,
        )
        if {"p1", "p2"} <= set(packet_blocks)
        else None
    )
    if semantic_context:
        sidecars.append(write_semantic_reentry_brief(output_dir=output_dir, context=semantic_context))
    for label, spec in PACKET_BLOCKS.items():
        block = packet_blocks.get(label)
        if block is None:
            continue
        packet = write_packet(
            output_dir=output_dir,
            label=label,
            block=block,
            semantic_context=semantic_context,
        )
        packets.append(packet)
        issues.extend(packet["required_token_issues"])
        if label == "p1":
            sidecars.append(write_p1_confirmation_checklist(output_dir=output_dir, block=block))
    sidecars.append(
        write_px_contamination_report(
            output_dir=output_dir,
            target_driver=target_driver,
            packets=packets,
            sidecars=sidecars,
        )
    )
    return {
        "target_driver": str(target_driver),
        "output_dir": str(output_dir),
        "packets": packets,
        "sidecars": sidecars,
        "issues": issues,
        "passed": not issues and len(packets) == len(PACKET_BLOCKS),
    }


def validate_report_output_path(path: Path) -> None:
    if path.suffix.lower() in {".md", ".markdown"}:
        raise ValueError(
            f"refuses to overwrite canonical artifact with extraction report: {path}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract PhaseX target-driver mainline re-entry packets for P1/P2."
    )
    parser.add_argument("--target-driver", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest", default="")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve() if args.manifest else None
    if manifest_path:
        try:
            validate_report_output_path(manifest_path)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    result = extract_packets(Path(args.target_driver).resolve(), Path(args.output_dir).resolve())
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if manifest_path:
        manifest_path.write_text(payload, encoding="utf-8")
    print(payload.rstrip())
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
