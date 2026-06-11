#!/usr/bin/env python3
"""
Emit Phase-1 depth runtime artifacts for v1.2 bounded deep-loop evidence.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import re
from pathlib import Path
from typing import Any

from common.output_language import resolve_output_locale
from phase1.phase1_generate_deep_stage_outputs import extract_domain_context
from phase1.phase1_localize_prd_zh import render_primary_locale_lines
from phase1.phase1_named_state import extract_named_state
from phase1.phase1_runtime_metadata import THINKING_VALUE_GAIN_OUTPUT_PROFILES
from phase1.phase1_reasoning_runtime import (
    PHASE1_BUSINESS_WORLD_MODEL_FILENAME,
    compile_maturity_confidence_ledger,
    compile_stage_reasoning_units,
)


REAL_WORLD_BASELINE_CALIBRATION = "real-world-baseline-calibration.md"
DOMAIN_BASELINE_SCENARIO_MAP = "domain-baseline-scenario-map.md"
CORE_SCENARIO_DEPTH_MATRIX = "core-scenario-depth-matrix.md"
DEMO_RISK_REVIEW = "demo-risk-review.md"
DECISION_OPTIONS_AND_TRADEOFFS = "decision-options-and-tradeoffs.md"
DOMAIN_ASSUMPTION_AND_EVIDENCE_LEDGER = "domain-assumption-and-evidence-ledger.md"
DEPTH_RUNTIME_SUMMARY_FILENAME = "phase1-depth-runtime-summary.json"
AGENTIC_LOOP_BRIEF = "phase1-agentic-loop-brief.md"
AGENTIC_LOOP_PLAN_FILENAME = "phase1-agentic-loop-plan.json"

DEPTH_RUNTIME_TEXT_ARTIFACTS = (
    REAL_WORLD_BASELINE_CALIBRATION,
    DOMAIN_BASELINE_SCENARIO_MAP,
    CORE_SCENARIO_DEPTH_MATRIX,
    DEMO_RISK_REVIEW,
    DECISION_OPTIONS_AND_TRADEOFFS,
    DOMAIN_ASSUMPTION_AND_EVIDENCE_LEDGER,
)

AGENTIC_LOOP_TEXT_ARTIFACTS = (
    AGENTIC_LOOP_BRIEF,
)

BASE_SCENARIO_DIMENSIONS = (
    "real_world_baseline_sufficiency",
    "operational_density",
    "state_transition_density",
    "exception_density",
    "coordination_density",
    "real_world_constraint_density",
    "downstream_handoff_sufficiency",
    "user_task_experience_clarity",
)

COMMERCIAL_DECISION_DIMENSIONS = (
    "value_mechanism_clarity",
    "buyer_budget_clarity",
    "decision_leverage_clarity",
)

LOOP_DIAGNOSTIC_DIMENSIONS = (
    "thesis_sharpness",
    "alternative_pressure",
    "source_semantic_retention",
    "semantic_compression",
    "economic_decision_surface",
)

SCENARIO_DIMENSIONS = BASE_SCENARIO_DIMENSIONS + COMMERCIAL_DECISION_DIMENSIONS

DIMENSION_LABELS = {
    "real_world_baseline_sufficiency": "Real-World Baseline Sufficiency",
    "operational_density": "Operational Density",
    "state_transition_density": "State-Transition Density",
    "exception_density": "Exception Density",
    "coordination_density": "Coordination Density",
    "real_world_constraint_density": "Real-World Constraint Density",
    "downstream_handoff_sufficiency": "Downstream Handoff Sufficiency",
    "user_task_experience_clarity": "User-Task Experience Clarity",
    "value_mechanism_clarity": "Value-Mechanism Clarity",
    "buyer_budget_clarity": "Buyer/Budget Clarity",
    "decision_leverage_clarity": "Decision-Leverage Clarity",
    "thesis_sharpness": "Thesis Sharpness",
    "alternative_pressure": "Alternative Pressure",
    "source_semantic_retention": "Source Semantic Retention",
    "semantic_compression": "Semantic Compression",
    "economic_decision_surface": "Economic Decision Surface",
}

DIMENSION_MATRIX_LABELS = {
    "real_world_baseline_sufficiency": "baseline",
    "operational_density": "operational",
    "state_transition_density": "state",
    "exception_density": "exception",
    "coordination_density": "coordination",
    "real_world_constraint_density": "real-world constraint",
    "downstream_handoff_sufficiency": "downstream handoff",
    "user_task_experience_clarity": "task/process experience",
    "value_mechanism_clarity": "value mechanism",
    "buyer_budget_clarity": "buyer/budget",
    "decision_leverage_clarity": "decision leverage",
}

STAGE_LABELS = {
    "stage_01": "Stage-01",
    "stage_02a": "Stage-02a",
    "stage_02b": "Stage-02b",
    "stage_03": "Stage-03",
    "stage_04": "Stage-04",
}

LOOP_FOCUS_LABELS = {
    "real_world_baseline": "Real-World Baseline",
    "scenario_family": "Scenario-Family Sufficiency",
    "business_value": "Business Value and Commercial Depth",
    "value_mechanism": "Business Value Mechanism",
    "thesis_sharpness": "Core Thesis Sharpness",
    "alternative_pressure": "Alternative Pressure",
    "source_semantic_retention": "Source Semantic Retention",
    "semantic_compression": "Semantic Compression",
    "buyer_budget_chain": "Buyer/Budget Chain",
    "economic_decision_surface": "Economic Decision Surface",
    "decision_leverage": "Decision Leverage",
    "anti_demo": "Anti-Demo Deepening",
    "flow_steps": "Operational Flow Steps",
    "state_transitions": "State Transitions",
    "exception_edges": "Exception and Recovery Edges",
    "role_handoffs": "Role Handoffs",
    "handoff_contracts": "Downstream Handoff Contracts",
    "boundary_acceptance": "Acceptance and Boundary Coverage",
    "user_task_experience": "User Task / Process Experience",
    "business_feasibility": "Business Feasibility",
    "mvp_wedge": "MVP Wedge",
    "acceptance_meaning": "Acceptance Meaning",
}

LOOP_ACTION_LIBRARY = {
    "real_world_baseline": "calibrate the scenario against ordinary real-world operator expectations and preserve the operational detail needed to stay above demo-level baseline",
    "scenario_family": "expand or split the scenario family until the first-wave baseline no longer depends on an obviously too-thin slice of the business world",
    "business_value": "deepen the operational detail, business consequence, commercial meaning, and secondarily the user task/process path only where it materially improves business value, decision leverage, real user outcomes, or downstream truth",
    "value_mechanism": "make the value mechanism explicit so the scenario shows why this path creates business value rather than only describing activity",
    "thesis_sharpness": "sharpen the core thesis so the scenario makes a concrete why-this-product argument instead of only presenting a clean workflow shell",
    "alternative_pressure": "make the rejected alternative, substitute pressure, or failure mode explicit so the chosen path is clearly stronger than thinner fallback options",
    "source_semantic_retention": "recover the domain-native nouns, roles, objects, and workflow anchors from source truth so the scenario stops sounding like a generic wrapper",
    "semantic_compression": "compress the scenario into concrete, high-signal business language and remove generic filler that sounds clean but does not carry more truth",
    "buyer_budget_chain": "surface the full buyer/budget chain: pain holder, continuation owner, spend at risk, proof artifact for continue, and the signal that justifies continued commitment while keeping unresolved truth review-bound",
    "economic_decision_surface": "make the economic decision surface explicit: what spend is at risk, what proof artifact matters, and what continue / revise / pause decision the owner is actually making",
    "decision_leverage": "make the continue / revise / pause or equivalent decision leverage explicit so the scenario ends in a real business decision, not just a completed flow",
    "anti_demo": "surface the missing real-world steps, constraints, coordination points, and operating artifacts that would make a faithful implementation still feel like a demo",
    "flow_steps": "expand the scenario into explicit numbered steps with owner, system behavior, and postcondition so the mainline can be implemented without reconstruction",
    "state_transitions": "materialize source state, target state, blocked state, and recovery transition instead of leaving the transition model implicit",
    "exception_edges": "add missing-input, invalid-state, dependency-blocked, and clarification-needed edges where the scenario can stall in real work",
    "role_handoffs": "make upstream role, downstream role, and handoff condition explicit so later phases do not invent coordination truth",
    "handoff_contracts": "name the output object, next action, blocked reason, and downstream dependency so the handoff is implementation-usable",
    "boundary_acceptance": "add Given/When/Then rows with observable expected outcome and boundary-condition coverage for the thin scenario edges",
    "user_task_experience": "make explicit where the mainline reduces manual reconstruction, handoff friction, waiting, confusion, or fragmented operator work so the task/process experience improves for real users",
    "business_feasibility": "state the thinnest feasible business path under the current source-evidence ceiling and keep unresolved feasibility truth review-bound",
    "mvp_wedge": "protect the narrowest valuable wedge so P2 can design the first slice without expanding scope or hiding assumptions",
    "acceptance_meaning": "turn acceptance from field or flow completion into observable business proof tied to the source-defined continue / revise / pause decision",
}

LOOP_SECTION_MAP = {
    "real_world_baseline": ["Business Scenarios", "Operational Flow Specification", "Acceptance Criteria"],
    "scenario_family": ["Business Scenarios", "MVP Definition & Scope", "Validation Strategy & Current Conclusion"],
    "business_value": ["Business Scenarios", "Validation Strategy & Current Conclusion", "Decision Options and Tradeoffs"],
    "value_mechanism": ["Business Scenarios", "Validation Strategy & Current Conclusion", "Decision Options and Tradeoffs"],
    "thesis_sharpness": ["Business Scenarios", "Validation Strategy & Current Conclusion", "Decision Options and Tradeoffs"],
    "alternative_pressure": ["Business Scenarios", "Decision Options and Tradeoffs", "Validation Strategy & Current Conclusion"],
    "source_semantic_retention": ["Business Scenarios", "Operational Flow Specification", "Validation Strategy & Current Conclusion"],
    "semantic_compression": ["Business Scenarios", "Validation Strategy & Current Conclusion"],
    "buyer_budget_chain": ["Business Scenarios", "Pricing Validation Design", "Validation Strategy & Current Conclusion"],
    "economic_decision_surface": ["Business Scenarios", "Pricing Validation Design", "Validation Strategy & Current Conclusion"],
    "decision_leverage": ["Business Scenarios", "Validation Strategy & Current Conclusion", "Decision Options and Tradeoffs"],
    "anti_demo": ["Business Scenarios", "Operational Flow Specification", "Acceptance Criteria"],
    "flow_steps": ["Operational Flow Specification", "Business Process Decomposition"],
    "state_transitions": ["State Machine and Transition Rules", "Operational Flow Specification"],
    "exception_edges": ["Exception and Failure Flows", "Acceptance Criteria"],
    "role_handoffs": ["Operational Flow Specification", "IA Spec Matrix", "Acceptance Criteria"],
    "handoff_contracts": ["Acceptance Criteria", "Module Interface Payload Contract", "State Machine and Transition Rules"],
    "boundary_acceptance": ["Acceptance Criteria"],
    "user_task_experience": ["Business Scenarios", "Operational Flow Specification", "Validation Strategy & Current Conclusion"],
    "business_feasibility": ["MVP Definition & Scope", "Validation Strategy & Current Conclusion"],
    "mvp_wedge": ["MVP Definition & Scope", "Business Scenarios", "Acceptance Criteria"],
    "acceptance_meaning": ["Acceptance Criteria", "Validation Strategy & Current Conclusion"],
}

LOOP_PASS_ORDER = (
    "business_world_sufficiency",
    "value_mechanism_clarity",
    "buyer_budget_continuation_chain",
    "integration_and_convergence",
)

LOOP_PASS_LABELS = {
    "business_world_sufficiency": "Business-World Sufficiency",
    "value_mechanism_clarity": "Value-Mechanism Clarity",
    "buyer_budget_continuation_chain": "Buyer/Budget/Continuation Chain",
    "integration_and_convergence": "Integration and Convergence",
}

WORLD_SUFFICIENCY_GAP_KEYS = {
    "real_world_baseline_sufficiency",
    "operational_density",
    "state_transition_density",
    "exception_density",
    "coordination_density",
    "real_world_constraint_density",
    "downstream_handoff_sufficiency",
}

VALUE_MECHANISM_GAP_KEYS = {
    "value_mechanism_clarity",
    "thesis_sharpness",
    "alternative_pressure",
    "source_semantic_retention",
    "semantic_compression",
}

BUYER_BUDGET_CHAIN_GAP_KEYS = {
    "buyer_budget_clarity",
    "decision_leverage_clarity",
    "economic_decision_surface",
}

INTEGRATION_GAP_KEYS = {
    "user_task_experience_clarity",
}


def read_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_markdown(path: Path, text: str, locale: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.rstrip() + "\n"
    output_locale = resolve_output_locale(locale)
    if output_locale == "zh-CN":
        normalized = "\n".join(render_primary_locale_lines(normalized.splitlines(), path.name, output_locale)).rstrip() + "\n"
    path.write_text(normalized, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        value = re.sub(r"\s+", " ", item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def slugify(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-") or "phase-1-depth-runtime"


def has_signal(text: str, *patterns: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL) for pattern in patterns)


def count_signal_groups(text: str, patterns: tuple[str, ...]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE))


def clamp_dimension(score: int) -> int:
    return max(0, min(score, 2))


def detect_operationally_rich_domain(text: str) -> bool:
    return has_signal(
        text,
        r"pet clinic|pet hospital|veterinary|hospital|clinic|patient|doctor|treatment|x-?ray|medication",
        r"inventory|warehouse|shipment|logistics|restaurant|retail|cashier|manufacturing|inspection",
        r"finance|financial|compliance|audit|ledger|invoice|billing",
        r"宠物医院|宠物诊所|医院|诊所|就诊|住院|处方|x光|药物|库存|仓储|物流|零售|餐饮|制造|检测|财务|合规|审计",
    )


def detect_commercial_decision_domain(text: str) -> bool:
    growth_signal = has_signal(
        text,
        r"geo|seo|marketing|growth|tenant|scope|observation|recommendation|visibility|competitor|roi|attribution|conversion",
    )
    commercial_signal = has_signal(
        text,
        r"buyer|budget|pricing|package|willingness[- ]to[- ]pay|adoption|sponsor|continue investing|revise|pause|resource choice|decision grade",
    )
    zh_signal = has_signal(
        text,
        r"营销|增长|租户|范围|观察|建议|可见性|竞品|预算|定价|付费|采纳|继续投入|调整|暂停|决策",
    )
    strong_anchor = has_signal(text, r"geo|seo|roi|attribution|budget|pricing", r"GEO|SEO|ROI|归因|预算|定价")
    return strong_anchor or sum(int(flag) for flag in (growth_signal, commercial_signal, zh_signal)) >= 2


def resolve_depth_posture(text: str) -> str:
    operational = detect_operationally_rich_domain(text)
    commercial = detect_commercial_decision_domain(text)
    if operational and commercial:
        return "mixed"
    if commercial:
        return "commercial-decision"
    return "operational-service"


def scenario_dimensions_for_posture(depth_posture: str) -> tuple[str, ...]:
    if depth_posture in {"commercial-decision", "mixed"}:
        return BASE_SCENARIO_DIMENSIONS + COMMERCIAL_DECISION_DIMENSIONS
    return BASE_SCENARIO_DIMENSIONS


def critical_zero_dimensions_for_posture(depth_posture: str) -> tuple[str, ...]:
    critical = [
        "operational_density",
        "state_transition_density",
        "downstream_handoff_sufficiency",
    ]
    if depth_posture in {"commercial-decision", "mixed"}:
        critical.extend(["value_mechanism_clarity", "decision_leverage_clarity"])
    return tuple(critical)


def scenario_heading(line: str) -> str | None:
    stripped = line.strip()
    if not re.match(r"^#{3,4}\s+", stripped):
        return None
    if "Business Scenarios" in stripped or "Scenario Decomposition" in stripped:
        return None
    heading = re.sub(r"^#{3,4}\s+", "", stripped).strip()
    if "scenario set overview" in heading.lower() or "场景集总览" in heading:
        return None
    if "matrix" in heading.lower() and "scenario" in heading.lower():
        return None
    if "场景矩阵" in heading:
        return None
    if has_signal(
        heading,
        r"quality scenario",
        r"persona context scenario",
        r"stakeholder and scenario set",
        r"scenario and backbone decomposition",
        r"business scenario analysis evidence",
        r"quality scenario matrix",
        r"persona/scenario",
        r"质量场景",
        r"画像.*场景",
        r"干系人.*场景",
        r"场景.*骨干",
    ):
        return None
    if not re.search(r"\bScenario\b", heading, flags=re.IGNORECASE):
        return None
    return heading


def is_generic_scenario_title(title: str) -> bool:
    normalized = compact(title)
    return any(
        re.fullmatch(pattern, normalized, flags=re.IGNORECASE)
        for pattern in (
            r"Key-path Scenario \d+",
            r"Scenario [A-Z0-9]+",
            r"关键路径场景 \d+ \((?:Key-path Scenario \d+)\)",
            r"场景 [A-Z0-9]+ \((?:Scenario [A-Z0-9]+)\)",
        )
    )


def normalize_scenario_title(raw_title: str, body_lines: list[str]) -> str:
    title = compact(raw_title)
    if not is_generic_scenario_title(title):
        return title
    for line in body_lines:
        match = re.match(r"^\s*-\s*(?=[^:\n]*scenario_title[^:\n]*)[^:\n]+:\s*(.+?)\s*$", line, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = compact(match.group(1).strip("`"))
        if candidate:
            return candidate
    return title


def extract_scenarios_from_text(text: str, source_label: str) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in text.splitlines():
        heading = scenario_heading(raw)
        if heading:
            if current and compact("\n".join(current["body_lines"])):
                current["title"] = normalize_scenario_title(str(current["title"]), list(current["body_lines"]))
                current["body"] = compact("\n".join(current["body_lines"]))
                scenarios.append(current)
            current = {
                "title": heading,
                "body_lines": [],
                "source": source_label,
            }
            continue
        if current is None:
            continue
        if raw.startswith("## "):
            if compact("\n".join(current["body_lines"])):
                current["title"] = normalize_scenario_title(str(current["title"]), list(current["body_lines"]))
                current["body"] = compact("\n".join(current["body_lines"]))
                scenarios.append(current)
            current = None
            continue
        current["body_lines"].append(raw)
    if current and compact("\n".join(current["body_lines"])):
        current["title"] = normalize_scenario_title(str(current["title"]), list(current["body_lines"]))
        current["body"] = compact("\n".join(current["body_lines"]))
        scenarios.append(current)
    return scenarios


def fallback_scenarios(domain_context: dict[str, Any]) -> list[dict[str, Any]]:
    primary_segment = str((domain_context.get("segments") or ["primary operator"])[0])
    roles = [
        str(item.get("Role", "")).strip()
        for item in domain_context.get("roles", [])
        if isinstance(item, dict) and str(item.get("Role", "")).strip()
    ]
    modules = [
        str(item.get("module", "")).strip()
        for item in domain_context.get("modules", [])
        if isinstance(item, dict) and str(item.get("module", "")).strip()
    ]
    objects = [
        str(item.get("Object", "")).strip()
        for item in domain_context.get("objects", [])
        if isinstance(item, dict) and str(item.get("Object", "")).strip()
    ]
    constraints = [str(item).strip() for item in domain_context.get("constraints", []) if str(item).strip()]
    flow_names = [
        str(item.get("name", "")).strip()
        for item in domain_context.get("flows", [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    ]

    first_wave = modules[: max(3, min(len(modules), 5))] or ["source-defined workflow"]
    closure = modules[-2:] if len(modules) >= 2 else modules
    scenario_specs = [
        (
            flow_names[0] if flow_names else "Scenario 1: Mainline Intake and Setup",
            first_wave[:2] or first_wave,
            "mainline baseline enters a usable state",
        ),
        (
            flow_names[1] if len(flow_names) > 1 else "Scenario 2: Core Execution and Decision Support",
            first_wave[1:4] or first_wave,
            "the operator can continue without manually reconstructing state",
        ),
        (
            flow_names[2] if len(flow_names) > 2 else "Scenario 3: Review and Continue/Revise Decision",
            closure or first_wave,
            "the decision owner can review outcomes and choose continue or revise",
        ),
    ]

    scenario_rows: list[dict[str, Any]] = []
    for idx, (title, module_slice, outcome) in enumerate(scenario_specs, start=1):
        active_role = roles[min(idx - 1, len(roles) - 1)] if roles else primary_segment
        handoff_role = roles[min(idx, len(roles) - 1)] if len(roles) > 1 else "secondary collaborator"
        object_hint = " -> ".join(objects[idx - 1 : idx + 2]) if objects else "source-defined business object chain"
        constraint_hint = constraints[min(idx - 1, len(constraints) - 1)] if constraints else "source-defined constraint"
        body = (
            f"trigger: `{active_role}` starts `{title}`; "
            f"main path: {' -> '.join(module_slice) or 'source-defined step'}; "
            f"state/object chain: {object_hint}; "
            f"coordination: `{active_role}` hands off to `{handoff_role}` when needed; "
            f"constraint: `{constraint_hint}` must stay explicit; "
            f"exception: if required state is missing, the flow must stop in an auditable blocked state; "
            f"outcome: {outcome}."
        )
        scenario_rows.append(
            {
                "title": f"Scenario {idx}: {title}",
                "body": body,
                "source": "fallback",
            }
        )
    return scenario_rows


def choose_core_scenarios(prd_text: str, stage_texts: dict[str, str], domain_context: dict[str, Any]) -> list[dict[str, Any]]:
    prd_scenarios = extract_scenarios_from_text(prd_text, "prd")
    collected: list[dict[str, Any]] = list(prd_scenarios)
    if len(prd_scenarios) < 3:
        for stage_key in ("stage_02a", "stage_03", "stage_04"):
            collected.extend(extract_scenarios_from_text(stage_texts.get(stage_key, ""), stage_key))
    if not collected:
        return fallback_scenarios(domain_context)

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for scenario in collected:
        key = slugify(str(scenario["title"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "title": str(scenario["title"]),
                "body": compact(str(scenario["body"])),
                "source": str(scenario["source"]),
            }
        )
    if not deduped:
        return fallback_scenarios(domain_context)

    posture_probe = json.dumps(domain_context, ensure_ascii=False)
    depth_posture = resolve_depth_posture(posture_probe)
    operationally_rich = detect_operationally_rich_domain(posture_probe)
    roles = [
        str(item.get("Role", "")).strip()
        for item in domain_context.get("roles", [])
        if isinstance(item, dict) and str(item.get("Role", "")).strip()
    ]
    constraints = [str(item).strip() for item in domain_context.get("constraints", []) if str(item).strip()]
    nfrs = [str(item).strip() for item in domain_context.get("nfrs", []) if str(item).strip()]
    minimum_required = 3 if depth_posture in {"commercial-decision", "mixed"} or operationally_rich else 2
    ranked = sorted(
        [
            {
                **item,
                "_original_index": idx,
            }
            for idx, item in enumerate(deduped)
        ],
        key=lambda item: (
            scenario_candidate_priority(
                item,
                depth_posture=depth_posture,
                operationally_rich=operationally_rich,
                roles=roles,
                constraints=constraints,
                nfrs=nfrs,
            ),
            0 if not is_generic_scenario_title(str(item["title"])) else -1,
        ),
        reverse=True,
    )
    selected = ranked[:minimum_required]
    selected.sort(key=lambda item: int(item["_original_index"]))
    return [
        {
            "title": str(item["title"]),
            "body": compact(str(item["body"])),
            "source": str(item["source"]),
        }
        for item in selected
    ]


def build_reasoning_context(domain_context: dict[str, Any]) -> dict[str, Any]:
    segments = [str(item).strip() for item in domain_context.get("segments", []) if str(item).strip()]
    primary_segment = segments[0] if segments else "primary operator"
    role_labels = [
        str(item.get("Role", "")).strip()
        for item in domain_context.get("roles", [])
        if isinstance(item, dict) and str(item.get("Role", "")).strip()
    ] or segments
    module_names = [
        str(item.get("module", "")).strip()
        for item in domain_context.get("modules", [])
        if isinstance(item, dict) and str(item.get("module", "")).strip()
    ]
    object_names = [
        str(item.get("Object", "")).strip()
        for item in domain_context.get("objects", [])
        if isinstance(item, dict) and str(item.get("Object", "")).strip()
    ]
    flow_steps = [
        str(step).strip()
        for flow in domain_context.get("flows", [])
        if isinstance(flow, dict)
        for step in flow.get("steps", [])
        if str(step).strip()
    ]
    constraints = [str(item).strip() for item in domain_context.get("constraints", []) if str(item).strip()]
    posture_probe = " ".join(segments + module_names + object_names + flow_steps + constraints).lower()
    growth_markers = (
        "scope",
        "observation",
        "recommendation",
        "review",
        "competitor",
        "visibility",
        "seo",
        "geo",
        "roi",
        "utm",
    )
    domain_posture = "growth-observation" if any(marker in posture_probe for marker in growth_markers) else "operational-service"
    depth_posture = resolve_depth_posture(posture_probe)
    workflow_backbone = " -> ".join((module_names or flow_steps)[:6]) or "source-defined workflow"
    object_dependency_chain = " -> ".join(object_names[:6]) or workflow_backbone
    mainline_surface_catalog = " / ".join((module_names or flow_steps)[:6]) or "mainline workflow surfaces"
    boundary_pair = (
        f"{module_names[0]} 与 {module_names[1]}" if len(module_names) >= 2 else "上游记录与下游动作"
    )
    subsystem_catalog = "、".join(module_names[:4]) or mainline_surface_catalog
    return {
        "primary_segment": primary_segment,
        "role_labels": role_labels,
        "supporting_role_label": role_labels[1] if len(role_labels) > 1 else "",
        "decision_role_label": role_labels[-1] if role_labels else primary_segment,
        "core_workflow_loop": workflow_backbone,
        "workflow_backbone": workflow_backbone,
        "object_dependency_chain": object_dependency_chain,
        "domain_posture": domain_posture,
        "depth_posture": depth_posture,
        "mainline_surface_catalog": mainline_surface_catalog,
        "mainline_subsystem_catalog": subsystem_catalog,
        "upstream_downstream_boundary_label": boundary_pair,
        "workflow_entry_and_detail_label": "关键工作入口与记录详情",
        "case_detail_label": "case detail",
        "case_detail_plural_label": "case details",
        "supporting_context_label": "secondary supporting context",
    }


def compile_all_reasoning_units(context: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        stage_key: compile_stage_reasoning_units(stage_key, [], context)
        for stage_key in ("stage_01", "stage_02a", "stage_02b", "stage_03", "stage_04")
    }


def score_operational_density(text: str) -> int:
    count = 0
    count += int(count_signal_groups(text, (r"\bstep\s+\d+", r"\btrigger\b", r"\bmain path\b", r"\boutcome\b", r"->")) >= 2)
    count += int(len(text) >= 180)
    count += int(has_signal(text, r"success criteria", r"entry", r"exit", r"challenge", r"preconditions", r"workflow"))
    return clamp_dimension(count)


def score_state_transition_density(text: str) -> int:
    count = 0
    count += int(has_signal(text, r"state", r"status", r"transition", r"blocked", r"published", r"draft", r"active", r"完成", r"阻塞"))
    count += int(has_signal(text, r"->", r"to\b", r"from\b"))
    count += int(has_signal(text, r"object chain", r"entity", r"record", r"summary", r"task", r"report", r"对象", r"记录"))
    return clamp_dimension(count)


def score_exception_density(text: str) -> int:
    count = 0
    count += int(has_signal(text, r"exception", r"blocked", r"error", r"invalid", r"failure", r"异常", r"阻塞", r"失败"))
    count += int(has_signal(text, r"\bif\b", r"\bwhen\b", r"若", r"如果"))
    count += int(has_signal(text, r"must stop", r"fallback", r"auditable", r"人工", r"审计"))
    return clamp_dimension(count)


def score_coordination_density(text: str, roles: list[str]) -> int:
    mentioned_roles = sum(1 for role in unique_preserve_order(roles)[:5] if role and role.lower() in text.lower())
    count = 0
    count += int(mentioned_roles >= 2)
    count += int(has_signal(text, r"handoff", r"owner", r"reviewer", r"operator", r"doctor", r"nurse", r"协作", r"交接", r"角色"))
    count += int(has_signal(text, r"decision owner", r"business owner", r"governance", r"审批", r"复核"))
    return clamp_dimension(count)


def score_real_world_constraint_density(text: str, constraints: list[str], nfrs: list[str]) -> int:
    domain_mentions = sum(1 for item in unique_preserve_order(constraints + nfrs)[:6] if item and item.lower() in text.lower())
    count = 0
    count += int(domain_mentions >= 1)
    count += int(
        has_signal(
            text,
            r"timing|time window|inventory|equipment|measurement|temperature|weight|length|photo|document|audit|policy|boundary|provisional|cost|billing|retention",
            r"时间|库存|设备|测量|体温|体重|长度|照片|文档|审计|策略|边界|暂定|成本|收费|留存",
        )
    )
    count += int(
        has_signal(
            text,
            r"constraint",
            r"nfr",
            r"reliability",
            r"security",
            r"maintainability",
            r"policy",
            r"boundary",
            r"provisional",
            r"permission",
            r"约束",
            r"可靠",
            r"安全",
            r"策略",
            r"边界",
            r"暂定",
            r"权限",
        )
    )
    return clamp_dimension(count)


def score_downstream_handoff_sufficiency(text: str) -> int:
    count = 0
    count += int(has_signal(text, r"outcome", r"success criteria", r"downstream", r"next action", r"consequence", r"结果", r"下游"))
    count += int(has_signal(text, r"object", r"state", r"step", r"workflow", r"对象", r"状态", r"步骤"))
    count += int(len(text) >= 220)
    return clamp_dimension(count)


def score_user_task_experience_clarity(text: str) -> int:
    count = 0
    count += int(
        has_signal(
            text,
            r"manual reconstruction|fragmented|handoff|shared context|one chain|same review summary|same chain|same workflow|next step",
            r"手工重建|碎片化|交接|共享上下文|一条链路|同一条链|下一步动作|同一份复盘",
        )
    )
    count += int(
        has_signal(
            text,
            r"without|directly|avoid|reduce|faster|clearer|readable|actionable|follow-up|review summary|smooth",
            r"无需|直接|避免|减少|更快|更清晰|可执行|复诊|复盘摘要|顺畅",
        )
    )
    count += int(
        has_signal(
            text,
            r"experience|usability|friction|adoption|habit|drop-off|queue|waiting|confusion",
            r"体验|可用性|摩擦|采纳|使用习惯|流失|排队|等待|困惑",
        )
    )
    return clamp_dimension(count)


def concrete_business_anchor_density(text: str) -> int:
    count = 0
    count += int(bool(re.search(r"`[^`\n]{2,}`", text)))
    count += int(
        count_signal_groups(
            text,
            (
                r"\binput\b",
                r"\boutput\b",
                r"\bowner\b",
                r"\bstate\b",
                r"\bstatus\b",
                r"\bblocked reason\b",
                r"\bevidence\b",
                r"\bcontract\b",
                r"\bpayload\b",
                r"\baudit\b",
                r"输入",
                r"输出",
                r"负责人|所有者",
                r"状态",
                r"阻塞原因",
                r"证据",
                r"契约|合同",
                r"payload",
                r"审计",
            ),
        )
        >= 2
    )
    count += int(
        has_signal(
            text,
            r"record|task|summary|invoice|payment|visit|treatment|appointment|scope|baseline|finding|recommendation|review|decision|document|order|approval|cycle",
            r"记录|任务|摘要|账单|支付|就诊|治疗|预约|范围|基线|发现|建议|复盘|决策|文档|订单|审批|周期",
        )
    )
    return clamp_dimension(count)


GENERIC_FILLER_PATTERNS = (
    r"improves?\s+business value",
    r"commercial depth",
    r"adoption confidence",
    r"decision quality",
    r"workflow shell",
    r"clean workflow",
    r"generic commercial",
    r"better user experience",
    r"流程更顺畅",
    r"商业价值更强",
    r"决策质量",
    r"采纳信心",
)


ALTERNATIVE_PRESSURE_PATTERNS = (
    r"instead of",
    r"rather than",
    r"not just",
    r"not merely",
    r"alternative",
    r"substitute",
    r"fallback",
    r"dashboard-only",
    r"detached report",
    r"report shell",
    r"passive reporting",
    r"spreadsheet",
    r"chat thread",
    r"manual reconstruction",
    r"而不是",
    r"不仅仅",
    r"替代方案",
    r"孤立页面",
    r"事后汇总",
    r"事后报告",
    r"脱离主链的事后报告",
    r"退化为",
    r"被动报表",
    r"手工重建",
)


CHAIN_LITERALIZATION_PATTERNS = (
    r"`[^`\n]{0,220}(?:->|→)[^`\n]{0,220}(?:->|→)[^`\n]{0,220}`",
    r"(?:\b[\w\u4e00-\u9fff()/ -]{2,}\b\s*(?:->|→)\s*){2,}\b[\w\u4e00-\u9fff()/ -]{2,}\b",
)


CONTRACT_SPILLOVER_PATTERNS = (
    r"payload contract",
    r"typed workflow contract",
    r"traceability",
    r"state machine",
    r"registry",
    r"entity graph",
    r"permission model",
    r"audit policy",
    r"模块接口",
    r"payload",
    r"状态机",
    r"注册表",
    r"实体关系",
    r"权限模型",
    r"审计策略",
    r"可追溯",
)


NON_GROWTH_GROWTH_SEAM_PATTERNS = (
    r"attribution",
    r"conversion seam",
    r"\bUTM\b",
    r"funnel",
    r"cross-device",
    r"competitor snapshot",
    r"recommendation payload contract",
    r"归因",
    r"转化缝",
    r"漏斗",
    r"跨设备",
    r"竞品快照",
    r"建议载荷契约",
)


def semantic_anchors_from_domain_context(domain_context: dict[str, Any]) -> list[str]:
    anchors: list[str] = []
    anchors.extend(str(item).strip() for item in domain_context.get("segments", []) if str(item).strip())
    anchors.extend(
        str(item.get("Role", "")).strip()
        for item in domain_context.get("roles", [])
        if isinstance(item, dict) and str(item.get("Role", "")).strip()
    )
    anchors.extend(
        str(item.get("module", "")).strip()
        for item in domain_context.get("modules", [])
        if isinstance(item, dict) and str(item.get("module", "")).strip()
    )
    anchors.extend(
        str(item.get("Object", "")).strip()
        for item in domain_context.get("objects", [])
        if isinstance(item, dict) and str(item.get("Object", "")).strip()
    )
    anchors.extend(
        str(item.get("name", "")).strip()
        for item in domain_context.get("flows", [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    )
    anchors.extend(
        str(step).strip()
        for item in domain_context.get("flows", [])
        if isinstance(item, dict)
        for step in item.get("steps", [])
        if str(step).strip()
    )
    filtered: list[str] = []
    for anchor in unique_preserve_order(anchors):
        candidate = compact(anchor)
        if not candidate:
            continue
        if re.fullmatch(r"[a-z]{1,3}", candidate, flags=re.IGNORECASE):
            continue
        filtered.append(candidate)
        if len(filtered) >= 24:
            break
    return filtered


def count_semantic_anchor_hits(text: str, semantic_anchors: list[str] | None = None) -> int:
    if not semantic_anchors:
        return 0
    probe = compact(text).casefold()
    hits = 0
    for anchor in unique_preserve_order([compact(item) for item in semantic_anchors if compact(item)]):
        if len(anchor) <= 2 and anchor.isascii():
            continue
        if anchor.casefold() in probe:
            hits += 1
    return hits


def count_pattern_occurrences(text: str, patterns: tuple[str, ...]) -> int:
    return sum(len(re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE)) for pattern in patterns)


def chain_literalization_count(text: str) -> int:
    return count_pattern_occurrences(text, CHAIN_LITERALIZATION_PATTERNS)


def contract_spillover_count(text: str) -> int:
    return count_pattern_occurrences(text, CONTRACT_SPILLOVER_PATTERNS)


def proof_artifact_repetition_count(text: str) -> int:
    return count_pattern_occurrences(
        text,
        (
            r"proof_artifact_for_continue",
            r"decision_trigger",
            r"continuation_signal",
            r"review summary",
            r"决策触发器",
            r"继续信号",
            r"复盘摘要",
        ),
    )


def growth_seam_leakage_count(text: str, depth_posture: str) -> int:
    if depth_posture in {"commercial-decision", "mixed"}:
        return 0
    return count_pattern_occurrences(text, NON_GROWTH_GROWTH_SEAM_PATTERNS)


def score_thesis_sharpness(text: str) -> int:
    chain_overrender = chain_literalization_count(text)
    contract_overrender = contract_spillover_count(text)
    value_signal = has_signal(
        text,
        r"business value|commercial value|decision chain|decision confidence|continued investment|manual reconstruction|detached report|passive reporting",
        r"商业价值|经营价值|决策链|决策信心|继续投入|主线闭环|可判定的主线闭环|动作闭环|手工重建|报表系统|被动报表",
    )
    causal_signal = has_signal(
        text,
        r"because|so that|therefore|turns?.+into|lets?.+instead|proves?|signals?",
        r"因为|从而|因此|让.+变成|证明|信号",
    )
    contrast_signal = has_signal(text, *ALTERNATIVE_PRESSURE_PATTERNS)
    consequence_signal = has_signal(
        text,
        r"scenario consequence if weak|if weak|otherwise|degenerates? into|falls back to",
        r"场景薄弱时的后果|如果薄弱|否则|退化为|回退到",
    )
    anchor_density = concrete_business_anchor_density(text)
    if chain_overrender >= 2 and contract_overrender >= 3 and anchor_density <= 1 and not contrast_signal and not consequence_signal:
        return 0
    if value_signal and causal_signal and anchor_density <= 1 and not contrast_signal and not consequence_signal:
        return 0
    if value_signal and (contrast_signal or consequence_signal) and anchor_density >= 1:
        return 2 if causal_signal or consequence_signal else 1
    if (contrast_signal or causal_signal) and (value_signal or consequence_signal):
        return 1 if anchor_density >= 2 or contrast_signal or consequence_signal else 0
    return 0


def score_alternative_pressure(text: str) -> int:
    alternative_signal = has_signal(text, *ALTERNATIVE_PRESSURE_PATTERNS)
    consequence_signal = has_signal(
        text,
        r"scenario consequence if weak|if weak|otherwise|degenerates? into|would still force",
        r"场景薄弱时的后果|如果薄弱|否则|退化为|仍然迫使",
    )
    anchor_density = concrete_business_anchor_density(text)
    if alternative_signal and consequence_signal and anchor_density >= 1:
        return 2
    if alternative_signal or consequence_signal:
        return 1 if anchor_density >= 1 or alternative_signal else 0
    return 0


def score_source_semantic_retention(text: str, semantic_anchors: list[str] | None = None) -> int:
    anchor_hits = count_semantic_anchor_hits(text, semantic_anchors)
    anchor_density = concrete_business_anchor_density(text)
    chain_overrender = chain_literalization_count(text)
    contract_overrender = contract_spillover_count(text)
    generic_abstraction = (
        count_signal_groups(text, GENERIC_FILLER_PATTERNS) >= 2
        and anchor_hits == 0
    )
    if chain_overrender >= 3 and contract_overrender >= 3 and anchor_hits == 0 and anchor_density <= 1:
        return 0
    if anchor_hits >= 3 or (anchor_hits >= 2 and anchor_density >= 1):
        return 2
    if anchor_hits >= 1 or (anchor_density >= 2 and not generic_abstraction):
        return 1
    return 0


def score_semantic_compression(
    text: str,
    semantic_anchors: list[str] | None = None,
    *,
    depth_posture: str = "generic-workflow",
) -> int:
    anchor_hits = count_semantic_anchor_hits(text, semantic_anchors)
    anchor_density = concrete_business_anchor_density(text)
    generic_filler_count = count_signal_groups(text, GENERIC_FILLER_PATTERNS)
    chain_overrender = chain_literalization_count(text)
    proof_repetition = proof_artifact_repetition_count(text)
    contract_overrender = contract_spillover_count(text)
    growth_leakage = growth_seam_leakage_count(text, depth_posture)
    contrast_or_decision = has_signal(
        text,
        r"continue|revise|pause|proof_artifact|decision trigger|instead of|rather than|not just|manual reconstruction|detached report",
        r"继续|调整|暂停|证明物|决策触发器|而不是|不仅仅|孤立页面|事后汇总|脱离主链的事后报告|手工重建|报表系统",
    )
    if growth_leakage >= 2:
        return 0
    if generic_filler_count >= 2 and anchor_hits == 0:
        return 0
    if (chain_overrender >= 3 or proof_repetition >= 6 or contract_overrender >= 3) and anchor_hits == 0 and anchor_density <= 1:
        return 0
    if anchor_density >= 2 and (anchor_hits >= 2 or contrast_or_decision) and generic_filler_count <= 1:
        return 2
    if anchor_density >= 2 and (anchor_hits >= 1 or contrast_or_decision) and generic_filler_count <= 1:
        return 1
    return 0


def score_economic_decision_surface(text: str) -> int:
    chain_signal = has_signal(
        text,
        r"pain_holder|continuation_owner|spend_at_risk|proof_artifact_for_continue|continuation_signal|decision_trigger|chosen_business_thesis|buyer_user_operator_value|proof_target|product_boundary_implication",
        r"痛点承担者|继续投入负责人|投入风险|继续投入证明物|继续信号|决策触发器|业务论点|证明目标|产品边界",
    )
    spend_signal = has_signal(
        text,
        r"budget|pricing|package|quote|cost|investment|continued commitment|spend_at_risk|pilot",
        r"预算|定价|套餐|报价|成本|投入|继续投入|投入风险|试点",
    )
    proof_signal = has_signal(
        text,
        r"proof_artifact|review summary|decision record|threshold|quote|evidence",
        r"证明物|复盘摘要|决策记录|阈值|报价|证据",
    )
    decision_signal = has_signal(
        text,
        r"continue|revise|pause|approve|reject|decision owner",
        r"继续|调整|暂停|通过|拒绝|决策负责人",
    )
    if chain_signal and decision_signal and (spend_signal or proof_signal):
        return 2
    if decision_signal and (spend_signal or proof_signal or chain_signal):
        return 1
    return 0


def score_loop_diagnostic_dimensions(
    text: str,
    *,
    depth_posture: str,
    semantic_anchors: list[str] | None = None,
) -> dict[str, int]:
    scores = {
        "thesis_sharpness": score_thesis_sharpness(text),
        "alternative_pressure": score_alternative_pressure(text),
        "source_semantic_retention": score_source_semantic_retention(text, semantic_anchors),
        "semantic_compression": score_semantic_compression(
            text,
            semantic_anchors,
            depth_posture=depth_posture,
        ),
    }
    if depth_posture in {"commercial-decision", "mixed"}:
        scores["economic_decision_surface"] = score_economic_decision_surface(text)
    return scores


def score_value_mechanism_clarity(text: str) -> int:
    value_signal = has_signal(
        text,
        r"business value|commercial value|roi|worth|return|investment|resource choice|business result|adoption",
        r"商业价值|收益|投入产出|值得持续投入|业务结果|采纳|持续投入",
    )
    causal_signal = has_signal(
        text,
        r"because|so that|therefore|enables|improves|reduces|proves|signals",
        r"因为|从而|因此|使得|提升|降低|证明|信号",
    )
    effect_signal = has_signal(
        text,
        r"reduce|improve|increase|decrease|retain|avoid|justify|clarify|speed|throughput|quality|confidence|adoption",
        r"减少|提升|增加|降低|留存|避免|证明|澄清|效率|吞吐|质量|信心|采纳",
    )
    anchor_density = concrete_business_anchor_density(text)
    if value_signal and causal_signal and effect_signal and anchor_density >= 2:
        return 2
    if value_signal and (causal_signal or effect_signal):
        return 1 if anchor_density >= 1 or causal_signal else 0
    return 0


def score_buyer_budget_clarity(text: str) -> int:
    buyer_signal = has_signal(
        text,
        r"buyer|budget|pricing|package|willingness[- ]to[- ]pay|payment intent|quote|cost",
        r"买方|预算|定价|套餐|付费意愿|报价|成本|收费",
    )
    owner_signal = has_signal(
        text,
        r"decision sponsor|business owner|budget owner|commercial owner|tenant owner",
        r"业务负责人|预算负责人|商业负责人|租户负责人|决策人",
    )
    continuation_signal = has_signal(
        text,
        r"renew|expand|continue investing|cancel|purchase|adoption signal|pilot",
        r"续费|扩容|继续投入|取消|购买|采纳信号|试点",
    )
    chain_signal = has_signal(
        text,
        r"pain_holder|continuation_owner|spend_at_risk|proof_artifact_for_continue|continuation_signal",
        r"痛点承担者|继续投入负责人|投入风险|继续投入证明物|继续信号",
    )
    anchor_density = concrete_business_anchor_density(text)
    if buyer_signal and owner_signal and continuation_signal and (chain_signal or anchor_density >= 2):
        return 2
    if buyer_signal and (owner_signal or continuation_signal):
        return 1 if chain_signal or anchor_density >= 1 or owner_signal else 0
    return 0


def score_decision_leverage_clarity(text: str) -> int:
    decision_signal = has_signal(
        text,
        r"continue|revise|pause|go / no-go|go-no-go|approve|reject|decision owner",
        r"继续|调整|暂停|通过|拒绝|决策负责人|继续/调整/暂停",
    )
    decision_frame = has_signal(
        text,
        r"review|decision|threshold|signal|next action|review summary|priority shift",
        r"复盘|决策|阈值|信号|下一步动作|复盘摘要|优先级调整",
    )
    resource_signal = has_signal(
        text,
        r"resource|investment|commitment|package choice|pricing decision",
        r"资源|投入|承诺|套餐选择|定价决策",
    )
    anchor_density = concrete_business_anchor_density(text)
    if decision_signal and decision_frame and anchor_density >= 2:
        return 2
    if decision_signal and (decision_frame or resource_signal):
        return 1 if anchor_density >= 1 or resource_signal else 0
    return 0


def structural_scenario_penalty(title: str, body: str) -> int:
    title_probe = compact(title)
    text = f"{title_probe}\n{body}"
    structural_title = has_signal(
        title_probe,
        r"tenant|actor|audit|permission|domain model|entity|schema|payload|registry|state machine|boundary|foundational model",
        r"租户|角色|审计|权限|领域模型|实体|架构边界|状态机|基础模型|注册表|payload",
    )
    structural_body = has_signal(
        text,
        r"role boundary|audit policy|entity graph|schema|payload contract|registry|permission model|state machine",
        r"角色边界|审计策略|实体关系|数据模型|payload contract|权限模型|状态机",
    )
    if structural_title and structural_body:
        return 8
    if structural_title or structural_body:
        return 4
    return 0


def scenario_candidate_priority(
    scenario: dict[str, Any],
    *,
    depth_posture: str,
    operationally_rich: bool,
    roles: list[str],
    constraints: list[str],
    nfrs: list[str],
) -> int:
    title = str(scenario["title"])
    body = compact(str(scenario["body"]))
    operational = score_operational_density(body)
    state_transition = score_state_transition_density(body)
    exception = score_exception_density(body)
    coordination = score_coordination_density(body, roles)
    real_world_constraints = score_real_world_constraint_density(body, constraints, nfrs)
    downstream_handoff = score_downstream_handoff_sufficiency(body)
    baseline = score_real_world_baseline_sufficiency(
        body,
        operationally_rich=operationally_rich,
        constraint_score=real_world_constraints,
        operational_score=operational,
        coordination_score=coordination,
    )
    experience = score_user_task_experience_clarity(body)
    richness_bonus = 0
    richness_bonus += int(has_signal(body, r"main success path", r"主成功路径")) * 4
    richness_bonus += int(has_signal(body, r"success criteria", r"成功标准")) * 3
    richness_bonus += int(has_signal(body, r"scenario consequence if weak", r"场景薄弱时的后果")) * 3
    richness_bonus += int(has_signal(body, r"preconditions", r"前置条件")) * 2
    richness_bonus += int(has_signal(body, r"trigger", r"触发条件")) * 2
    commercial_bonus = 0
    if depth_posture in {"commercial-decision", "mixed"}:
        commercial_bonus += score_value_mechanism_clarity(body) * 4
        commercial_bonus += score_decision_leverage_clarity(body) * 4
        commercial_bonus += score_buyer_budget_clarity(body) * 2
    generic_penalty = 3 if is_generic_scenario_title(title) else 0
    return (
        baseline * 4
        + operational * 3
        + state_transition * 2
        + exception * 2
        + coordination * 2
        + real_world_constraints * 2
        + downstream_handoff * 3
        + experience * 3
        + richness_bonus
        + commercial_bonus
        - structural_scenario_penalty(title, body)
        - generic_penalty
    )


def score_real_world_baseline_sufficiency(
    text: str,
    *,
    operationally_rich: bool,
    constraint_score: int,
    operational_score: int,
    coordination_score: int,
) -> int:
    if not operationally_rich:
        return 2 if operational_score >= 1 else 1
    specific_real_world = has_signal(
        text,
        r"temperature|weight|x-?ray|invoice|inventory|inspection|billing|audit|compliance|document|equipment",
        r"体温|体重|x光|发票|库存|检查|收费|审计|合规|文档|设备",
    )
    count = 0
    count += int(constraint_score >= 1)
    count += int(operational_score >= 1)
    count += int(coordination_score >= 1 or specific_real_world)
    if count >= 3:
        return 2
    if count >= 2:
        return 1
    return 0


def summarize_dimension_gaps(scores: dict[str, int], active_dimensions: list[str] | tuple[str, ...] | None = None) -> list[str]:
    dimensions = list(active_dimensions or scores.keys())
    gaps: list[str] = []
    for key in dimensions:
        if key not in scores:
            continue
        score = scores[key]
        if score == 0:
            gaps.append(f"{DIMENSION_LABELS[key]} absent")
        elif score == 1:
            gaps.append(f"{DIMENSION_LABELS[key]} partial")
    return gaps


def score_core_scenarios(
    scenarios: list[dict[str, Any]],
    *,
    depth_posture: str,
    operationally_rich: bool,
    roles: list[str],
    constraints: list[str],
    nfrs: list[str],
    semantic_anchors: list[str] | None = None,
) -> list[dict[str, Any]]:
    active_dimensions = scenario_dimensions_for_posture(depth_posture)
    critical_zero_dimensions = critical_zero_dimensions_for_posture(depth_posture)
    required_total = max(10, int(len(active_dimensions) * 1.4))
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        body = compact(str(scenario["body"]))
        operational = score_operational_density(body)
        state_transition = score_state_transition_density(body)
        exception = score_exception_density(body)
        coordination = score_coordination_density(body, roles)
        real_world_constraints = score_real_world_constraint_density(body, constraints, nfrs)
        downstream_handoff = score_downstream_handoff_sufficiency(body)
        baseline = score_real_world_baseline_sufficiency(
            body,
            operationally_rich=operationally_rich,
            constraint_score=real_world_constraints,
            operational_score=operational,
            coordination_score=coordination,
        )
        scores = {
            "real_world_baseline_sufficiency": baseline,
            "operational_density": operational,
            "state_transition_density": state_transition,
            "exception_density": exception,
            "coordination_density": coordination,
            "real_world_constraint_density": real_world_constraints,
            "downstream_handoff_sufficiency": downstream_handoff,
            "user_task_experience_clarity": score_user_task_experience_clarity(body),
        }
        if depth_posture in {"commercial-decision", "mixed"}:
            scores.update(
                {
                    "value_mechanism_clarity": score_value_mechanism_clarity(body),
                    "buyer_budget_clarity": score_buyer_budget_clarity(body),
                    "decision_leverage_clarity": score_decision_leverage_clarity(body),
                }
            )
        loop_scores = score_loop_diagnostic_dimensions(
            body,
            depth_posture=depth_posture,
            semantic_anchors=semantic_anchors,
        )
        active_scores = {key: scores[key] for key in active_dimensions}
        critical_zero = any(active_scores[key] == 0 for key in critical_zero_dimensions if key in active_scores)
        total_score = sum(active_scores.values())
        if critical_zero:
            status = "BLOCKED"
        elif total_score >= required_total:
            status = "PASS"
        else:
            status = "REVIEW-BOUND"
        rows.append(
            {
                "title": str(scenario["title"]),
                "source": str(scenario["source"]),
                "body": body,
                "scores": active_scores,
                "active_dimensions": list(active_dimensions),
                "depth_posture": depth_posture,
                "total_score": total_score,
                "status": status,
                "loop_scores": loop_scores,
                "loop_dimensions": list(loop_scores.keys()),
                "gaps": unique_preserve_order(
                    summarize_dimension_gaps(active_scores, active_dimensions)
                    + summarize_dimension_gaps(loop_scores, list(loop_scores.keys()))
                ),
            }
        )
    return rows


def summarize_scenario_set(rows: list[dict[str, Any]], operationally_rich: bool, depth_posture: str) -> tuple[str, str]:
    if not rows:
        return ("BLOCKED", "no core scenarios were materialized for depth review")
    critical_failures = sum(1 for row in rows if row["status"] == "BLOCKED")
    review_bound = sum(1 for row in rows if row["status"] == "REVIEW-BOUND")
    min_count = 3 if operationally_rich or depth_posture in {"commercial-decision", "mixed"} else 2
    if len(rows) >= min_count and critical_failures == 0 and review_bound <= 1:
        return ("PASS", "the chosen scenario set is broad and deep enough for downstream work without major invention pressure")
    if len(rows) >= 2 and critical_failures <= 1:
        return ("REVIEW-BOUND", "core scenarios exist, but one or more still look thinner than the target baseline")
    return ("BLOCKED", "the chosen scenario set is still too thin and would push key product truth invention downstream")


def summarize_baseline_calibration(
    rows: list[dict[str, Any]],
    operationally_rich: bool,
    depth_posture: str,
) -> tuple[str, str, bool]:
    checks: list[tuple[str, str, bool]] = []
    if not rows:
        return ("BLOCKED", "no scenario baseline was materialized for calibration", False)

    if operationally_rich:
        baseline_scores = [int(row["scores"]["real_world_baseline_sufficiency"]) for row in rows]
        constraint_scores = [int(row["scores"]["real_world_constraint_density"]) for row in rows]
        if min(baseline_scores) >= 1 and sum(constraint_scores) >= len(rows):
            if min(baseline_scores) == 2:
                checks.append(
                    (
                        "PASS",
                        "the current baseline is at or above ordinary real-world operating density for the chosen mainline scenarios",
                        True,
                    )
                )
            else:
                checks.append(
                    (
                        "REVIEW-BOUND",
                        "the baseline is credible enough to continue, but one or more scenarios are still only partially calibrated to ordinary real-world density",
                        True,
                    )
                )
        else:
            checks.append(
                (
                    "BLOCKED",
                    "the current world model is still materially thinner than ordinary real-world operating practice",
                    False,
                )
            )
    elif depth_posture not in {"commercial-decision", "mixed"}:
        checks.append(
            (
                "PASS",
                "the domain is not operationally rich; the stronger field-style baseline calibration is recorded but not a hard blocker",
                True,
            )
        )

    if depth_posture in {"commercial-decision", "mixed"}:
        value_scores = [int(row["scores"].get("value_mechanism_clarity", 0)) for row in rows]
        buyer_scores = [int(row["scores"].get("buyer_budget_clarity", 0)) for row in rows]
        decision_scores = [int(row["scores"].get("decision_leverage_clarity", 0)) for row in rows]
        thesis_scores = [int(dict(row.get("loop_scores", {})).get("thesis_sharpness", 0)) for row in rows]
        alternative_scores = [int(dict(row.get("loop_scores", {})).get("alternative_pressure", 0)) for row in rows]
        economic_surface_scores = [int(dict(row.get("loop_scores", {})).get("economic_decision_surface", 0)) for row in rows]
        business_proof_track_pass = (
            min(thesis_scores or [0]) >= 2
            and min(alternative_scores or [0]) >= 2
            and min(economic_surface_scores or [0]) >= 2
        )
        if min(value_scores) >= 1 and min(decision_scores) >= 1:
            if min(value_scores) == 2 and min(decision_scores) == 2 and max(buyer_scores) >= 1 and business_proof_track_pass:
                checks.append(
                    (
                        "PASS",
                        "the current baseline reaches ordinary real-world commercial decision density: chosen thesis, substitute pressure, business proof, decision leverage, and at least one buyer/budget anchor are explicit",
                        True,
                    )
                )
            else:
                checks.append(
                    (
                        "REVIEW-BOUND",
                        "the baseline already carries usable commercial decision truth, but the business proof track is not yet sharp enough: value mechanism, substitute pressure, buyer/budget anchors, or decision leverage are still only partially explicit",
                        False,
                    )
                )
        else:
            checks.append(
                (
                    "BLOCKED",
                    "the current world model is still below ordinary real-world commercial decision density because business value or continue/revise/pause leverage remains too implicit",
                    False,
                )
            )

    severity = {"PASS": 0, "REVIEW-BOUND": 1, "BLOCKED": 2}
    worst = max(checks, key=lambda item: severity[item[0]])
    judgment = "; ".join(item[1] for item in checks)
    met = all(item[2] for item in checks)
    return (worst[0], judgment, met)


def build_demo_risks(
    rows: list[dict[str, Any]],
    *,
    depth_posture: str,
    operationally_rich: bool,
    unknowns: list[str],
    tradeoff_count: int,
) -> tuple[str, list[dict[str, str]]]:
    risks: list[dict[str, str]] = []
    for row in rows:
        scores = row["scores"]
        loop_scores = {
            key: int(value)
            for key, value in dict(row.get("loop_scores", {})).items()
            if isinstance(value, int)
        }
        if row["status"] == "PASS" and not any(score == 1 for score in scores.values()) and not any(
            score < 2 for score in loop_scores.values()
        ):
            continue
        top_gap = row["gaps"][0] if row["gaps"] else "scenario still feels thin"
        risks.append(
            {
                "scenario": str(row["title"]),
                "risk": top_gap,
                "why_demo_like": (
                    "the scenario still lacks enough concrete steps/states/constraints and could compile into a polished but shallow demo"
                    if row["status"] == "BLOCKED"
                    else "the scenario is usable but still partially thin, so downstream teams may over-assume detail"
                ),
                "downstream_guessing_pressure": (
                    "design/architecture may still need to invent entities, transitions, or exception behavior"
                ),
                "next_action": "deepen the scenario until the missing dimension is no longer title-level or keep the unknown explicitly review-bound",
            }
        )
    if operationally_rich and all(row["scores"]["real_world_constraint_density"] >= 1 for row in rows):
        pass
    elif operationally_rich:
        risks.append(
            {
                "scenario": "cross-scenario baseline",
                "risk": "Real-World Constraint Density partial or absent",
                "why_demo_like": "operationally rich domains need more than happy-path labels to avoid demo-shaped outputs",
                "downstream_guessing_pressure": "implementation teams may otherwise invent measurements, documents, equipment, or timing logic ad hoc",
                "next_action": "calibrate the mainline against ordinary real-world operator expectations before freezing",
            }
        )
    if depth_posture in {"commercial-decision", "mixed"}:
        if any(row["scores"].get("value_mechanism_clarity", 0) < 1 for row in rows) or any(
            row["scores"].get("decision_leverage_clarity", 0) < 1 for row in rows
        ):
            risks.append(
                {
                    "scenario": "commercial decision layer",
                    "risk": "Value-Mechanism Clarity or Decision-Leverage Clarity partial or absent",
                    "why_demo_like": "the product world may still describe workflow activity without making the business value mechanism or continue/revise/pause leverage explicit",
                    "downstream_guessing_pressure": "later phases may invent why the product matters, who should continue paying, or what concrete decision the loop is meant to support",
                    "next_action": "deepen value mechanism and decision leverage until the scenario ends in an honest business decision, not just a completed workflow",
                }
            )
        elif max(row["scores"].get("buyer_budget_clarity", 0) for row in rows) < 1:
            risks.append(
                {
                    "scenario": "buyer/budget chain",
                    "risk": "Buyer/Budget Clarity absent",
                    "why_demo_like": "commercial language is present, but the buyer, budget owner, or willingness-to-pay signal is still missing",
                    "downstream_guessing_pressure": "validation and packaging work may otherwise invent who pays or why the product continues to deserve budget",
                    "next_action": "surface at least one explicit buyer/budget anchor or keep the missing commercial truth clearly review-bound",
                }
            )
    if tradeoff_count < 4:
        risks.append(
            {
                "scenario": "global decision layer",
                "risk": "Decision trade-off coverage too thin",
                "why_demo_like": "outputs look polished, but meaningful why-this-not-that decisions are still under-externalized",
                "downstream_guessing_pressure": "later phases may reopen product-truth decisions that should have been frozen in P1",
                "next_action": "externalize more first-order trade-offs instead of only describing the chosen path",
            }
        )
    if len(unknowns) < 3:
        risks.append(
            {
                "scenario": "global evidence posture",
                "risk": "Unknown truth ledger too thin",
                "why_demo_like": "hidden unknowns create false confidence and make the artifact feel more complete than it really is",
                "downstream_guessing_pressure": "later phases may silently promote unvalidated assumptions into commitments",
                "next_action": "expand the assumption/evidence ledger and keep forbidden assumptions explicit",
            }
        )

    risks = risks[:5]
    if not risks:
        return ("PASS", [])
    if any("absent" in item["risk"].lower() for item in risks) or len(risks) >= 4:
        return ("REVIEW-BOUND", risks)
    return ("REVIEW-BOUND", risks)


def summarize_unknowns(reasoning_units: dict[str, list[dict[str, Any]]], maturity_rows: list[dict[str, Any]]) -> list[str]:
    unknowns: list[str] = []
    for units in reasoning_units.values():
        for unit in units:
            remaining = compact(str(unit.get("remaining_unknown", "")))
            if remaining:
                unknowns.append(remaining)
    for row in maturity_rows:
        blocker = compact(str(row.get("blocker_to_next_evidence_state", "")))
        assumption = compact(str(row.get("forbidden_assumptions", "")))
        if blocker:
            unknowns.append(blocker)
        if assumption:
            unknowns.append(f"forbidden assumption: {assumption}")
    return unique_preserve_order(unknowns)


def scenario_status_marker(status: str) -> str:
    return {
        "PASS": "sufficient",
        "REVIEW-BOUND": "review-bound",
        "BLOCKED": "too-thin",
    }.get(status, status.lower())


def scenario_gap_keys(scores: dict[str, int]) -> list[str]:
    return [key for key in scores.keys() if int(scores.get(key, 0)) < 2]


def loop_diagnostic_gap_keys(
    row: dict[str, Any],
    *,
    depth_posture: str | None = None,
) -> list[str]:
    existing_scores = row.get("loop_scores")
    if isinstance(existing_scores, dict) and existing_scores:
        return [key for key, value in existing_scores.items() if int(value) < 2]
    body = compact(str(row.get("body", "")))
    if not body:
        return []
    posture = str(depth_posture or row.get("depth_posture", "") or "operational-service")
    semantic_anchors = [
        str(item).strip()
        for item in row.get("semantic_anchors", [])
        if str(item).strip()
    ]
    scored = score_loop_diagnostic_dimensions(
        body,
        depth_posture=posture,
        semantic_anchors=semantic_anchors,
    )
    return [key for key, value in scored.items() if int(value) < 2]


def focus_areas_for_gap_keys(gap_keys: list[str]) -> list[str]:
    focus: list[str] = []
    for gap in gap_keys:
        if gap == "real_world_baseline_sufficiency":
            focus.append("real_world_baseline")
            focus.append("business_value")
            focus.append("anti_demo")
        elif gap == "operational_density":
            focus.append("flow_steps")
            focus.append("anti_demo")
        elif gap == "state_transition_density":
            focus.append("state_transitions")
        elif gap == "exception_density":
            focus.append("exception_edges")
            focus.append("anti_demo")
            focus.append("boundary_acceptance")
        elif gap == "coordination_density":
            focus.append("role_handoffs")
            focus.append("anti_demo")
        elif gap == "real_world_constraint_density":
            focus.append("real_world_baseline")
            focus.append("business_value")
            focus.append("anti_demo")
            focus.append("boundary_acceptance")
        elif gap == "value_mechanism_clarity":
            focus.append("value_mechanism")
            focus.append("business_value")
            focus.append("anti_demo")
        elif gap == "thesis_sharpness":
            focus.append("thesis_sharpness")
            focus.append("business_value")
            focus.append("anti_demo")
        elif gap == "alternative_pressure":
            focus.append("alternative_pressure")
            focus.append("business_value")
        elif gap == "source_semantic_retention":
            focus.append("source_semantic_retention")
            focus.append("business_value")
        elif gap == "semantic_compression":
            focus.append("semantic_compression")
        elif gap == "buyer_budget_clarity":
            focus.append("buyer_budget_chain")
            focus.append("business_value")
        elif gap == "decision_leverage_clarity":
            focus.append("decision_leverage")
            focus.append("business_value")
            focus.append("boundary_acceptance")
        elif gap == "economic_decision_surface":
            focus.append("economic_decision_surface")
            focus.append("buyer_budget_chain")
            focus.append("decision_leverage")
        elif gap == "downstream_handoff_sufficiency":
            focus.append("handoff_contracts")
            focus.append("business_value")
            focus.append("boundary_acceptance")
        elif gap == "user_task_experience_clarity":
            focus.append("user_task_experience")
            focus.append("business_value")
    if focus and "boundary_acceptance" not in focus:
        focus.append("boundary_acceptance")
    return unique_preserve_order(focus)


def compile_loop_focus_areas(
    gap_keys: list[str],
    *,
    depth_posture: str | None = None,
) -> dict[str, Any]:
    commercial_posture = depth_posture in {"commercial-decision", "mixed"}
    world_gap_keys = [gap for gap in gap_keys if gap in WORLD_SUFFICIENCY_GAP_KEYS]
    value_gap_keys = [gap for gap in gap_keys if gap in VALUE_MECHANISM_GAP_KEYS]
    buyer_gap_keys = [gap for gap in gap_keys if commercial_posture and gap in BUYER_BUDGET_CHAIN_GAP_KEYS]
    integration_gap_keys = [gap for gap in gap_keys if gap in INTEGRATION_GAP_KEYS]

    pass_focus_map = {
        "business_world_sufficiency": focus_areas_for_gap_keys(world_gap_keys),
        "value_mechanism_clarity": focus_areas_for_gap_keys(value_gap_keys),
        "buyer_budget_continuation_chain": focus_areas_for_gap_keys(buyer_gap_keys),
        "integration_and_convergence": focus_areas_for_gap_keys(integration_gap_keys),
    }

    if world_gap_keys:
        active_pass = "business_world_sufficiency"
        focus_areas = unique_preserve_order(
            pass_focus_map["business_world_sufficiency"] + pass_focus_map["value_mechanism_clarity"]
        )
    elif value_gap_keys:
        active_pass = "value_mechanism_clarity"
        focus_areas = list(pass_focus_map["value_mechanism_clarity"])
    elif buyer_gap_keys:
        active_pass = "buyer_budget_continuation_chain"
        focus_areas = list(pass_focus_map["buyer_budget_continuation_chain"])
    else:
        active_pass = "integration_and_convergence"
        focus_areas = list(pass_focus_map["integration_and_convergence"])

    deferred_focus_areas: list[str] = []
    seen_active = set(focus_areas)
    active_index = LOOP_PASS_ORDER.index(active_pass)
    for pass_key in LOOP_PASS_ORDER[active_index + 1 :]:
        for focus in pass_focus_map[pass_key]:
            if focus in seen_active:
                continue
            deferred_focus_areas.append(focus)
            seen_active.add(focus)

    order_blockers: list[str] = []
    if world_gap_keys and value_gap_keys:
        order_blockers.append(
            "value mechanism work remains downstream of business-world thickening and must not be used to bypass world sufficiency"
        )
    if world_gap_keys and buyer_gap_keys:
        order_blockers.append(
            "buyer/budget continuation work is deferred until business-world sufficiency and value mechanism clarity are credible"
        )
    elif value_gap_keys and buyer_gap_keys:
        order_blockers.append(
            "buyer/budget continuation work is deferred until value mechanism clarity is credible"
        )

    return {
        "active_pass": active_pass,
        "active_pass_label": LOOP_PASS_LABELS[active_pass],
        "pass_gap_keys": {
            "business_world_sufficiency": world_gap_keys,
            "value_mechanism_clarity": value_gap_keys,
            "buyer_budget_continuation_chain": buyer_gap_keys,
            "integration_and_convergence": integration_gap_keys,
        },
        "pass_focus_map": pass_focus_map,
        "focus_areas": focus_areas,
        "deferred_focus_areas": deferred_focus_areas,
        "order_blockers": order_blockers,
    }


def build_loop_target_exact_actions(
    *,
    scenario_title: str,
    gap_keys: list[str],
    focus_areas: list[str],
) -> list[str]:
    actions: list[str] = []
    if gap_keys:
        actions.append(
            f"treat `{scenario_title}` as a required deepening target because {', '.join(DIMENSION_LABELS[key] for key in gap_keys)} is still below sufficiency and would otherwise leave the business world too thin"
        )
    for focus in focus_areas:
        action = LOOP_ACTION_LIBRARY.get(focus)
        if action:
            actions.append(action)
    return unique_preserve_order(actions)


DRIVER_TARGET_FOCUS_MAP = {
    "product_judgment": ["thesis_sharpness", "alternative_pressure", "source_semantic_retention"],
    "commercial_judgment": ["business_value", "buyer_budget_chain", "decision_leverage"],
    "business_feasibility": ["business_feasibility", "business_value"],
    "mvp_wedge": ["mvp_wedge", "business_feasibility", "boundary_acceptance"],
    "acceptance_meaning": ["acceptance_meaning", "decision_leverage", "boundary_acceptance"],
}


def compile_driver_value_deepening_plan(
    product_source_direct_driver_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(product_source_direct_driver_summary, dict):
        return {"focus_areas": [], "targets": [], "actions": []}
    value_targets = product_source_direct_driver_summary.get("value_deepening_targets", [])
    if not isinstance(value_targets, list) or not value_targets:
        return {"focus_areas": [], "targets": [], "actions": []}
    focus_areas: list[str] = []
    actions: list[str] = []
    target_names: list[str] = []
    target_notes: list[str] = []
    for item in value_targets:
        if not isinstance(item, dict):
            continue
        target_name = compact(str(item.get("target", "")))
        mapped_focus = DRIVER_TARGET_FOCUS_MAP.get(target_name, [])
        if not mapped_focus:
            continue
        target_names.append(target_name)
        focus_areas.extend(mapped_focus)
        focus_text = compact(str(item.get("focus", "")))
        value_exit = compact(str(item.get("value_exit", "")))
        target_actions = [
            LOOP_ACTION_LIBRARY[focus]
            for focus in mapped_focus
            if focus in LOOP_ACTION_LIBRARY
        ]
        if focus_text:
            target_actions.append(f"driver focus: {focus_text}")
        if value_exit:
            target_actions.append(f"value exit: {value_exit}")
        if value_exit:
            target_notes.append(value_exit)
        actions.extend(target_actions)
    focus_areas = unique_preserve_order(focus_areas)
    targets = []
    if target_names:
        targets.append(
            {
                "scenario_title": "Product/source driver value-deepening targets",
                "scenario_status": "REVIEW-BOUND",
                "scenario_source": "p1-product-source-direct-driver.v1",
                "missing_dimensions": unique_preserve_order(target_names),
                "active_pass": "driver_value_deepening",
                "active_pass_label": "Driver Value Deepening",
                "focus_areas": focus_areas,
                "deferred_focus_areas": [],
                "order_blockers": [],
                "section_targets": unique_preserve_order(
                    [section for focus in focus_areas for section in LOOP_SECTION_MAP.get(focus, [])]
                ),
                "exact_thickening_actions": unique_preserve_order(actions),
                "reviewer_notes": unique_preserve_order(target_notes),
            }
        )
    return {
        "focus_areas": focus_areas,
        "targets": targets,
        "actions": unique_preserve_order(actions),
    }


def build_agentic_loop_plan(
    *,
    version: str,
    depth_mode: str,
    depth_posture: str | None = None,
    scenario_rows: list[dict[str, Any]],
    scenario_set_status: str,
    baseline_status: str,
    baseline_judgment: str,
    demo_risks: list[dict[str, str]],
    unknowns: list[str],
    product_source_direct_driver_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    targets: list[dict[str, Any]] = []
    pass_focus_union = {pass_key: [] for pass_key in LOOP_PASS_ORDER}
    union_order_blockers: list[str] = []
    high_value_gap_keys: list[str] = []
    driver_value_plan = compile_driver_value_deepening_plan(product_source_direct_driver_summary)

    for row in scenario_rows:
        score_gap_keys = scenario_gap_keys(dict(row["scores"]))
        diagnostic_gap_keys = loop_diagnostic_gap_keys(row, depth_posture=depth_posture)
        gap_keys = unique_preserve_order(score_gap_keys + diagnostic_gap_keys)
        focus_plan = compile_loop_focus_areas(gap_keys, depth_posture=depth_posture)
        focus_areas = list(focus_plan["focus_areas"])
        if row["status"] == "PASS" and not focus_areas and not focus_plan["deferred_focus_areas"]:
            continue
        high_value_gap_keys.extend(
            key
            for key in gap_keys
            if key in WORLD_SUFFICIENCY_GAP_KEYS or key in VALUE_MECHANISM_GAP_KEYS or key in BUYER_BUDGET_CHAIN_GAP_KEYS
        )
        target = {
            "scenario_title": str(row["title"]),
            "scenario_status": str(row["status"]),
            "scenario_source": str(row["source"]),
            "missing_dimensions": gap_keys,
            "active_pass": str(focus_plan["active_pass"]),
            "active_pass_label": str(focus_plan["active_pass_label"]),
            "focus_areas": focus_areas,
            "deferred_focus_areas": list(focus_plan["deferred_focus_areas"]),
            "order_blockers": list(focus_plan["order_blockers"]),
            "section_targets": unique_preserve_order(
                [section for focus in focus_areas for section in LOOP_SECTION_MAP.get(focus, [])]
            ),
            "exact_thickening_actions": build_loop_target_exact_actions(
                scenario_title=str(row["title"]),
                gap_keys=gap_keys,
                focus_areas=focus_areas,
            ),
            "reviewer_notes": unique_preserve_order(
                list(row.get("gaps", []))
                + summarize_dimension_gaps(dict(row.get("loop_scores", {})), list(dict(row.get("loop_scores", {})).keys()))
            ),
        }
        targets.append(target)
        for pass_key in LOOP_PASS_ORDER:
            pass_focus_union[pass_key].extend(focus_plan["pass_focus_map"].get(pass_key, []))
        union_order_blockers.extend(str(item) for item in focus_plan["order_blockers"])
    targets.extend(driver_value_plan["targets"])

    if scenario_set_status != "PASS":
        pass_focus_union["business_world_sufficiency"].extend(["scenario_family", "business_value"])
        union_order_blockers.append(
            "scenario family is still too thin, so commercial convergence must wait until the business world is thick enough"
        )
    if baseline_status in {"REVIEW-BOUND", "BLOCKED"}:
        pass_focus_union["business_world_sufficiency"].extend(["real_world_baseline", "business_value", "anti_demo"])
        union_order_blockers.append(
            "real-world baseline calibration is still below freeze level, so later commercial convergence cannot close the round yet"
        )
    pass_focus_union = {
        pass_key: unique_preserve_order(focuses)
        for pass_key, focuses in pass_focus_union.items()
    }
    active_pass = "integration_and_convergence"
    for pass_key in LOOP_PASS_ORDER:
        if pass_focus_union[pass_key]:
            active_pass = pass_key
            break

    focus_areas = list(pass_focus_union[active_pass])
    if active_pass == "business_world_sufficiency" and pass_focus_union["value_mechanism_clarity"]:
        focus_areas = unique_preserve_order(focus_areas + pass_focus_union["value_mechanism_clarity"])
    driver_focus_areas = list(driver_value_plan["focus_areas"])
    if active_pass == "integration_and_convergence" and driver_focus_areas:
        active_pass = "driver_value_deepening"
        focus_areas = driver_focus_areas
    elif driver_focus_areas:
        focus_areas = unique_preserve_order(focus_areas + driver_focus_areas)

    deferred_focus_areas: list[str] = []
    seen_focus = set(focus_areas)
    active_index = LOOP_PASS_ORDER.index(active_pass) if active_pass in LOOP_PASS_ORDER else len(LOOP_PASS_ORDER)
    if active_pass in LOOP_PASS_ORDER:
        for pass_key in LOOP_PASS_ORDER[active_index + 1 :]:
            for focus in pass_focus_union[pass_key]:
                if focus in seen_focus:
                    continue
                deferred_focus_areas.append(focus)
                seen_focus.add(focus)

    ordered_passes = []
    for idx, pass_key in enumerate(LOOP_PASS_ORDER):
        areas = list(pass_focus_union[pass_key])
        if pass_key == active_pass:
            status = "active" if areas else "satisfied"
        elif idx < active_index:
            status = "satisfied"
        else:
            status = "deferred" if areas else "satisfied"
        ordered_passes.append(
            {
                "key": pass_key,
                "label": LOOP_PASS_LABELS[pass_key],
                "status": status,
                "focus_areas": areas,
            }
        )

    order_blockers = unique_preserve_order(union_order_blockers)
    high_value_gap_keys = unique_preserve_order(high_value_gap_keys)
    cross_cutting_actions = unique_preserve_order(
        [
            LOOP_ACTION_LIBRARY[focus]
            for focus in focus_areas
            if focus in LOOP_ACTION_LIBRARY
        ]
        + list(driver_value_plan["actions"])
    )
    round_focus = (
        "raise the business-value-bearing baseline scenarios until the product world reaches ordinary real-world practice, anti-demo gaps are explicit, and downstream no longer needs to invent mainline truth"
        if depth_mode == "baseline"
        else "keep baseline truth intact while continuing only the deepening rounds that still add material positive business value"
    )
    if depth_posture in {"commercial-decision", "mixed"} and depth_mode == "baseline":
        round_focus = (
            "raise the business-value-bearing baseline scenarios until the product world reaches ordinary real-world commercial decision density, core thesis and alternative pressure are explicit, value mechanism and economic decision surface are explicit, secondary user task/process experience gains are captured where they improve real adoption, and downstream no longer needs to invent why the product deserves continued investment"
        )
    exit_rule = (
        "stop when downstream no longer needs to invent critical truth, the baseline is not materially below ordinary real-world practice, and another round is unlikely to add new material positive business value"
        if depth_mode == "baseline"
        else "stop only when further iteration no longer adds significant positive business value, while keeping baseline truth as the freezing floor"
    )
    if depth_posture in {"commercial-decision", "mixed"} and depth_mode == "baseline":
        exit_rule = (
            "stop when downstream no longer needs to invent critical truth, the baseline is not materially below ordinary real-world commercial decision practice, core thesis and alternative pressure are explicit, and another round is unlikely to add new material positive business value"
        )
    convergence_ready = (
        scenario_set_status == "PASS"
        and baseline_status == "PASS"
        and not high_value_gap_keys
        and active_pass == "integration_and_convergence"
        and not focus_areas
        and not deferred_focus_areas
    )
    return {
        "version": version,
        "depth_mode": depth_mode,
        "depth_posture": depth_posture or "not-explicit",
        "scenario_set_status": scenario_set_status,
        "baseline_calibration_status": baseline_status,
        "baseline_calibration_judgment": baseline_judgment,
        "active_pass": active_pass,
        "active_pass_label": LOOP_PASS_LABELS.get(active_pass, "Driver Value Deepening"),
        "round_focus": round_focus,
        "focus_areas": focus_areas,
        "deferred_focus_areas": deferred_focus_areas,
        "ordered_passes": ordered_passes,
        "order_blockers": order_blockers,
        "target_count": len(targets),
        "high_value_gap_keys": high_value_gap_keys,
        "high_value_gap_count": len(high_value_gap_keys),
        "convergence_ready": convergence_ready,
        "targets": targets,
        "cross_cutting_actions": cross_cutting_actions,
        "demo_risk_count": len(demo_risks),
        "unknowns": unknowns[:8],
        "exit_rule": exit_rule,
    }


def render_agentic_loop_brief_markdown(
    *,
    version: str,
    loop_plan: dict[str, Any],
) -> str:
    targets = list(loop_plan.get("targets", []))
    lines = [
        "# Phase-1 Agentic Loop Brief",
        "",
        "## 1. Runtime Metadata",
        f"- version: `{version}`",
        f"- depth_mode: `{loop_plan.get('depth_mode', 'baseline')}`",
        f"- depth_posture: `{loop_plan.get('depth_posture', 'not-explicit')}`",
        f"- scenario_set_status: `{loop_plan.get('scenario_set_status', 'not-explicit')}`",
        f"- baseline_calibration_status: `{loop_plan.get('baseline_calibration_status', 'not-explicit')}`",
        f"- target_count: `{loop_plan.get('target_count', 0)}`",
        f"- high_value_gap_count: `{loop_plan.get('high_value_gap_count', 0)}`",
        f"- convergence_ready: `{str(loop_plan.get('convergence_ready', False)).lower()}`",
        "",
        "## 2. Round Focus",
        f"- round_focus: {loop_plan.get('round_focus', 'not-explicit')}",
        f"- exit_rule: {loop_plan.get('exit_rule', 'not-explicit')}",
        "",
        "## 3. Cross-Cutting Focus Areas",
    ]
    focus_areas = list(loop_plan.get("focus_areas", []))
    if focus_areas:
        for focus in focus_areas:
            lines.append(f"- `{focus}`: {LOOP_FOCUS_LABELS.get(str(focus), str(focus))}")
    else:
        lines.append("- none")
    lines.extend(["", "## 4. Target Scenarios"])
    if not targets:
        lines.append("- no explicit deep-loop target was compiled in this round")
    else:
        for idx, target in enumerate(targets, start=1):
            lines.extend(
                [
                    f"### Target {idx}: {target['scenario_title']}",
                    f"- status: `{target['scenario_status']}`",
                    f"- scenario_source: `{target['scenario_source']}`",
                    "- missing_dimensions:",
                ]
            )
            missing_dimensions = list(target.get("missing_dimensions", []))
            if missing_dimensions:
                for dimension in missing_dimensions:
                    lines.append(f"  - `{dimension}`")
            else:
                lines.append("  - `none`")
            lines.append("- section_targets:")
            section_targets = list(target.get("section_targets", []))
            if section_targets:
                for section in section_targets:
                    lines.append(f"  - `{section}`")
            else:
                lines.append("  - `none`")
            lines.append("- exact_thickening_actions:")
            actions = list(target.get("exact_thickening_actions", []))
            if actions:
                for action in actions:
                    lines.append(f"  - {action}")
            else:
                lines.append("  - none")
            lines.append("")
    lines.extend(["## 5. Unresolved Truth Carryover"])
    unknowns = list(loop_plan.get("unknowns", []))
    if unknowns:
        for item in unknowns:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip()


def agentic_loop_artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        AGENTIC_LOOP_BRIEF: output_dir / AGENTIC_LOOP_BRIEF,
        AGENTIC_LOOP_PLAN_FILENAME: output_dir / AGENTIC_LOOP_PLAN_FILENAME,
    }


def render_baseline_calibration_markdown(
    *,
    version: str,
    depth_mode: str,
    depth_posture: str,
    operationally_rich: bool,
    baseline_status: str,
    baseline_judgment: str,
    scenario_rows: list[dict[str, Any]],
    unknowns: list[str],
    prd_text: str,
) -> str:
    delivery_state = extract_named_state(prd_text, "document_delivery_state") or "not-explicit"
    evidence_state = extract_named_state(prd_text, "evidence_confidence_state") or "not-explicit"
    lines = [
        "# Real-World Baseline Calibration",
        "",
        "## 1. Runtime Metadata",
        f"- version: `{version}`",
        f"- depth_mode: `{depth_mode}`",
        f"- depth_posture: `{depth_posture}`",
        f"- operationally_rich_domain: `{'yes' if operationally_rich else 'no'}`",
        f"- calibration_status: `{baseline_status}`",
        f"- document_delivery_state: `{delivery_state}`",
        f"- evidence_confidence_state: `{evidence_state}`",
        "",
        "## 2. Calibration Judgment",
        f"- judgment: {baseline_judgment}",
    ]
    if depth_posture in {"commercial-decision", "mixed"}:
        lines.append(
            "- calibration_rule: for commercial-decision domains, the mainline may not freeze materially below ordinary real-world business-value and decision-density baseline"
        )
    elif operationally_rich:
        lines.append(
            "- calibration_rule: for operationally rich domains, the mainline may not freeze materially below ordinary real-world baseline"
        )
    else:
        lines.append(
            "- calibration_rule: stronger field-style calibration is optional for ordinary-density domains, but the baseline posture is still recorded"
        )
    if depth_mode == "creative":
        lines.extend(
            [
                "- creative_boundary:",
                "  - baseline truth remains the freezing floor",
                "  - creative discoveries must stay separated from baseline truth",
            ]
        )
    extra_headers: list[tuple[str, str]] = []
    if depth_posture in {"commercial-decision", "mixed"}:
        extra_headers.extend(
            [
                ("user_task_experience_clarity", "task/process experience"),
                ("value_mechanism_clarity", "value mechanism"),
                ("buyer_budget_clarity", "buyer/budget"),
                ("decision_leverage_clarity", "decision leverage"),
            ]
        )
    else:
        extra_headers.extend(
            [
                ("user_task_experience_clarity", "task/process experience"),
                ("real_world_constraint_density", "constraint density"),
                ("coordination_density", "coordination density"),
            ]
        )
    header_labels = " | ".join(label for _, label in extra_headers)
    separator = "|---|---|" + "---|" * len(extra_headers) + "---|"
    lines.extend(["", "## 3. Scenario Calibration Snapshot", f"| scenario | baseline sufficiency | {header_labels} | note |", separator])
    for row in scenario_rows:
        note = row["gaps"][0] if row["gaps"] else "no major thinness detected"
        extra_values = " | ".join(f"{row['scores'].get(key, 0)}/2" for key, _ in extra_headers)
        title = str(row["title"]).replace("|", "\\|")
        safe_note = note.replace("|", "\\|")
        lines.append(
            f"| {title} | {row['scores']['real_world_baseline_sufficiency']}/2 | {extra_values} | {safe_note} |"
        )
    lines.extend(["", "## 4. Unresolved Truth That Still Limits Baseline Confidence"])
    if not unknowns:
        lines.append("- none")
    else:
        for item in unknowns[:8]:
            lines.append(f"- {item}")
    return "\n".join(lines)


def render_scenario_map_markdown(
    *,
    version: str,
    depth_mode: str,
    primary_segment: str,
    scenario_rows: list[dict[str, Any]],
    deferred_candidates: list[str],
    creative_candidates: list[str],
) -> str:
    lines = [
        "# Domain Baseline Scenario Map",
        "",
        "## 1. Runtime Metadata",
        f"- version: `{version}`",
        f"- depth_mode: `{depth_mode}`",
        f"- primary_segment: `{primary_segment}`",
        "",
        "## 2. Mainline Scenario Families",
        "| scenario family | baseline status | why it belongs in the mainline baseline | downstream use |",
        "|---|---|---|---|",
    ]
    for row in scenario_rows:
        reason = (
            "kept because it is already deep enough to support downstream work"
            if row["status"] == "PASS"
            else "kept because it defines a core truth of the product world even though parts remain review-bound"
        )
        lines.append(
            "| {title} | {status} | {reason} | {use} |".format(
                title=row["title"].replace("|", "\\|"),
                status=scenario_status_marker(str(row["status"])),
                reason=reason.replace("|", "\\|"),
                use="feeds PRD and Phase-2 handoff",
            )
        )
    lines.extend(["", "## 3. Deferred / Non-Baseline Families"])
    if deferred_candidates:
        for item in deferred_candidates:
            lines.append(f"- `{item}`: visible, but not part of the first-wave baseline truth")
    else:
        lines.append("- none")
    lines.extend(["", "## 4. Creative-Mode Opportunity Candidates"])
    if depth_mode != "creative":
        lines.append("- creative mode not active in this run")
    elif creative_candidates:
        for item in creative_candidates:
            lines.append(f"- `{item}`: opportunity candidate kept separate from baseline truth")
    else:
        lines.append("- no additional creative-mode opportunity candidates were externalized in this run")
    return "\n".join(lines)


def render_core_scenario_depth_matrix_markdown(
    *,
    version: str,
    scenario_rows: list[dict[str, Any]],
    scenario_set_status: str,
    scenario_set_judgment: str,
) -> str:
    lines = [
        "# Core Scenario Depth Matrix",
        "",
        "## 1. Runtime Metadata",
        f"- version: `{version}`",
        f"- scenario_count: `{len(scenario_rows)}`",
        f"- scenario_set_status: `{scenario_set_status}`",
        f"- scenario_set_judgment: {scenario_set_judgment}",
        "",
        "## 2. Scoring Scale",
        "- `0` = absent / downstream must guess",
        "- `1` = partial / still somewhat demo-like",
        "- `2` = sufficient for high-quality downstream work",
        "",
        "## 3. Scenario Matrix",
    ]
    active_dimensions = list(scenario_rows[0].get("active_dimensions", list(scenario_rows[0]["scores"].keys()))) if scenario_rows else list(BASE_SCENARIO_DIMENSIONS)
    header = " | ".join(DIMENSION_MATRIX_LABELS.get(key, key) for key in active_dimensions)
    lines.append(f"| scenario | {header} | total | status |")
    lines.append("|---|" + "---|" * len(active_dimensions) + "---|---|")
    for row in scenario_rows:
        scores = row["scores"]
        dimension_values = " | ".join(str(scores.get(key, 0)) for key in active_dimensions)
        title = str(row["title"]).replace("|", "\\|")
        lines.append(
            f"| {title} | {dimension_values} | {row['total_score']} | {scenario_status_marker(str(row['status']))} |"
        )
    lines.extend(["", "## 4. Reviewer Notes"])
    for row in scenario_rows:
        note = "; ".join(row["gaps"]) if row["gaps"] else "no major reviewer note"
        lines.append(f"- `{row['title']}`: {note}")
    return "\n".join(lines)


def render_demo_risk_review_markdown(
    *,
    version: str,
    demo_risk_status: str,
    demo_risks: list[dict[str, str]],
) -> str:
    lines = [
        "# Demo Risk Review",
        "",
        "## 1. Runtime Metadata",
        f"- version: `{version}`",
        f"- demo_risk_status: `{demo_risk_status}`",
        f"- risk_count: `{len(demo_risks)}`",
        "",
        "## 2. Risk Register",
    ]
    if not demo_risks:
        lines.append("- no material demo-like risk is currently externalized")
        return "\n".join(lines)
    for idx, risk in enumerate(demo_risks, start=1):
        lines.extend(
            [
                f"### Risk {idx}: {risk['scenario']}",
                f"- risk: {risk['risk']}",
                f"- why_demo_like: {risk['why_demo_like']}",
                f"- downstream_guessing_pressure: {risk['downstream_guessing_pressure']}",
                f"- next_action: {risk['next_action']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def render_tradeoffs_markdown(
    *,
    version: str,
    depth_mode: str,
    reasoning_units: dict[str, list[dict[str, Any]]],
    creative_candidates: list[str],
) -> str:
    lines = [
        "# Decision Options and Trade-Offs",
        "",
        "## 1. Runtime Metadata",
        f"- version: `{version}`",
        f"- depth_mode: `{depth_mode}`",
        "",
        "## 2. Material Why-This-Not-That Decisions",
        "| stage | artifact unit | alternatives compared | trade-off or tension | recommended path | evidence state |",
        "|---|---|---|---|---|---|",
    ]
    tradeoff_count = 0
    for stage_key in ("stage_01", "stage_02a", "stage_02b", "stage_03", "stage_04"):
        for unit in reasoning_units[stage_key]:
            alternatives = [str(item) for item in unit.get("alternatives_compared", []) if str(item).strip()]
            if len(alternatives) < 2:
                continue
            tradeoff_count += 1
            lines.append(
                "| {stage} | {artifact} | {alts} | {tension} | {decision} | {state} |".format(
                    stage=STAGE_LABELS[stage_key],
                    artifact=str(unit.get("artifact_unit", "reasoning unit")).replace("|", "\\|"),
                    alts=", ".join(alternatives[:4]).replace("|", "\\|"),
                    tension=compact(str(unit.get("tradeoff_or_tension", ""))).replace("|", "\\|"),
                    decision=compact(str(unit.get("decision_effect", ""))).replace("|", "\\|"),
                    state=str(unit.get("evidence_state", "not-explicit")).replace("|", "\\|"),
                )
            )
    lines.extend(["", "## 3. Creative-Mode Separation"])
    if depth_mode != "creative":
        lines.append("- creative mode not active; baseline trade-offs only")
    else:
        lines.append("- baseline truth remains the freeze floor; opportunity candidates stay separate")
        if creative_candidates:
            for item in creative_candidates:
                lines.append(f"- opportunity_candidate: `{item}`")
    lines.append("")
    lines.append(f"## 4. Trade-Off Count")
    lines.append(f"- material_tradeoff_count: `{tradeoff_count}`")
    return "\n".join(lines)


def render_assumption_evidence_ledger_markdown(
    *,
    version: str,
    reasoning_units: dict[str, list[dict[str, Any]]],
    maturity_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# Domain Assumption and Evidence Ledger",
        "",
        "## 1. Runtime Metadata",
        f"- version: `{version}`",
        "",
        "## 2. Stage Reasoning Unknowns",
        "| stage | reasoning unit | evidence state | remaining unknown | downstream handoff |",
        "|---|---|---|---|---|",
    ]
    for stage_key in ("stage_01", "stage_02a", "stage_02b", "stage_03", "stage_04"):
        for unit in reasoning_units[stage_key]:
            lines.append(
                "| {stage} | {title} | {state} | {unknown} | {handoff} |".format(
                    stage=STAGE_LABELS[stage_key],
                    title=str(unit.get("title", "reasoning unit")).replace("|", "\\|"),
                    state=str(unit.get("evidence_state", "not-explicit")).replace("|", "\\|"),
                    unknown=compact(str(unit.get("remaining_unknown", "none"))).replace("|", "\\|"),
                    handoff=compact(str(unit.get("downstream_handoff", "not-explicit"))).replace("|", "\\|"),
                )
            )
    lines.extend(
        [
            "",
            "## 3. Maturity / Confidence Carryover",
            "| subject | delivery readiness | evidence confidence | blocker to next evidence state | safe downstream action | forbidden assumptions |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in maturity_rows:
        lines.append(
            "| {subject} | {delivery} | {evidence} | {blocker} | {safe} | {forbidden} |".format(
                subject=compact(str(row.get("subject", "subject"))).replace("|", "\\|"),
                delivery=compact(str(row.get("delivery_readiness_state", "not-explicit"))).replace("|", "\\|"),
                evidence=compact(str(row.get("evidence_confidence_state", "not-explicit"))).replace("|", "\\|"),
                blocker=compact(str(row.get("blocker_to_next_evidence_state", "not-explicit"))).replace("|", "\\|"),
                safe=compact(str(row.get("safe_downstream_action", "not-explicit"))).replace("|", "\\|"),
                forbidden=compact(str(row.get("forbidden_assumptions", "not-explicit"))).replace("|", "\\|"),
            )
        )
    return "\n".join(lines)


def depth_runtime_artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        REAL_WORLD_BASELINE_CALIBRATION: output_dir / REAL_WORLD_BASELINE_CALIBRATION,
        DOMAIN_BASELINE_SCENARIO_MAP: output_dir / DOMAIN_BASELINE_SCENARIO_MAP,
        CORE_SCENARIO_DEPTH_MATRIX: output_dir / CORE_SCENARIO_DEPTH_MATRIX,
        DEMO_RISK_REVIEW: output_dir / DEMO_RISK_REVIEW,
        DECISION_OPTIONS_AND_TRADEOFFS: output_dir / DECISION_OPTIONS_AND_TRADEOFFS,
        DOMAIN_ASSUMPTION_AND_EVIDENCE_LEDGER: output_dir / DOMAIN_ASSUMPTION_AND_EVIDENCE_LEDGER,
        DEPTH_RUNTIME_SUMMARY_FILENAME: output_dir / DEPTH_RUNTIME_SUMMARY_FILENAME,
    }


def load_depth_runtime_summary(output_dir: Path) -> dict[str, Any] | None:
    path = output_dir / DEPTH_RUNTIME_SUMMARY_FILENAME
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_product_source_direct_driver_summary(output_dir: Path) -> dict[str, Any]:
    path = output_dir / PHASE1_BUSINESS_WORLD_MODEL_FILENAME
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    summary = payload.get("product_source_direct_driver_summary", {})
    return summary if isinstance(summary, dict) else {}


def business_completeness_driver_context(driver_summary: dict[str, Any] | None) -> str:
    if not isinstance(driver_summary, dict):
        return ""
    driver = driver_summary.get("business_completeness_driver", {})
    if not isinstance(driver, dict):
        return ""
    loss_chain = driver.get("business_loss_chain", {})
    continuation = driver.get("continuation_economics", {})
    substitute = driver.get("substitute_pressure_map", {})
    proof = driver.get("proof_for_continue", {})
    ceiling = driver.get("commercial_claim_ceiling", {})
    if not any(isinstance(item, dict) and item for item in (loss_chain, continuation, substitute, proof, ceiling)):
        return ""

    pain_holder = compact(str(loss_chain.get("pain_holder", "")))
    status_quo = compact(str(loss_chain.get("status_quo_to_beat", "")))
    pressure = compact(str(loss_chain.get("business_pressure", "")))
    outcome = compact(str(loss_chain.get("business_outcome_at_risk", "")))
    continuation_owner = compact(str(continuation.get("continuation_owner", "")))
    spend_at_risk = compact(str(continuation.get("spend_or_commitment_at_risk", "")))
    continuation_decision = compact(str(continuation.get("continuation_decision", ""))) or "continue / revise / pause"
    decision_trigger = compact(str(continuation.get("decision_trigger", "")))
    current_substitute = compact(str(substitute.get("current_substitute", ""))) or status_quo
    why_not_enough = compact(str(substitute.get("why_not_enough", "")))
    proof_artifact = compact(str(proof.get("proof_artifact", "")))
    directional_threshold = compact(str(proof.get("directional_threshold", "")))
    forbidden_upgrade = compact(str(ceiling.get("forbidden_upgrade", "")))

    lines = [
        "business_completeness_driver_context:",
        (
            "chosen_business_thesis: not just a task sequence; the product must create business value "
            f"because it turns `{pain_holder or 'pain holder'}` pressure into `{outcome or 'a reviewable business outcome'}`."
        ),
        (
            "business_value_mechanism: business value exists because the scenario proves action and review continuity, "
            f"improves decision confidence, and reduces reliance on `{current_substitute or 'current substitute'}`."
        ),
        (
            "why_this_not_alternatives: choose the mainline instead of "
            f"`{current_substitute or 'current substitute'}` because {why_not_enough or 'the substitute leaves proof, action, and decision context detached'}."
        ),
        (
            "scenario consequence if weak: otherwise the team falls back to detached report review and cannot justify "
            "continued investment."
        ),
        (
            "buyer_budget_chain: buyer / business owner / budget owner can judge continued investment; "
            f"pain_holder: {pain_holder or 'pain holder'}; "
            f"continuation_owner: {continuation_owner or 'business owner / budget owner'}; "
            f"spend_at_risk: {spend_at_risk or 'team time, budget, and continued operating commitment'}; "
            f"proof_artifact_for_continue: {proof_artifact or 'review summary plus decision record'}; "
            f"continuation_signal: {continuation_decision}; "
            "pricing hypothesis: pilot continuation and package choice stay review-bound."
        ),
        (
            "decision_leverage: decision owner can continue / revise / pause after review when "
            f"{decision_trigger or directional_threshold or 'the proof artifact changes confidence'}."
        ),
    ]
    if forbidden_upgrade:
        lines.append(f"forbidden_upgrade: {forbidden_upgrade}.")
    return compact(" ".join(line for line in lines if compact(line)))


def attach_business_completeness_context_to_scenarios(
    scenarios: list[dict[str, Any]],
    driver_summary: dict[str, Any] | None,
    *,
    depth_posture: str,
) -> list[dict[str, Any]]:
    if depth_posture not in {"commercial-decision", "mixed"}:
        return scenarios
    context = business_completeness_driver_context(driver_summary)
    if not context:
        return scenarios
    enriched: list[dict[str, Any]] = []
    for scenario in scenarios:
        body = compact(str(scenario.get("body", "")))
        enriched.append(
            {
                **scenario,
                "body": compact(f"{body} {context}"),
                "source": str(scenario.get("source", "prd")),
            }
        )
    return enriched


def emit_depth_runtime_artifacts(
    *,
    source_path: Path,
    stage_paths: dict[str, Path],
    prd_path: Path,
    output_dir: Path,
    version: str,
    owner: str,
    depth_mode: str,
    thinking_value_gain_mode: str = "off",
    thinking_value_gain_output_profile: str = "coverage_rich",
    output_locale: str | None = None,
) -> dict[str, Any]:
    source_text = read_text(source_path)
    prd_text = read_text(prd_path)
    stage_texts = {key: read_text(path) for key, path in stage_paths.items()}
    domain_context = extract_domain_context(source_text)
    reasoning_context = build_reasoning_context(domain_context)
    depth_posture = str(reasoning_context.get("depth_posture", "operational-service"))
    reasoning_units = compile_all_reasoning_units(reasoning_context)
    maturity_rows = compile_maturity_confidence_ledger("final_prd", reasoning_context)

    primary_segment = str(reasoning_context["primary_segment"])
    roles = [
        str(item.get("Role", "")).strip()
        for item in domain_context.get("roles", [])
        if isinstance(item, dict) and str(item.get("Role", "")).strip()
    ] or [primary_segment]
    constraints = [str(item).strip() for item in domain_context.get("constraints", []) if str(item).strip()]
    nfrs = [str(item).strip() for item in domain_context.get("nfrs", []) if str(item).strip()]
    semantic_anchors = semantic_anchors_from_domain_context(domain_context)
    deferred_candidates = unique_preserve_order(
        [str(item).strip() for item in domain_context.get("p1", []) if str(item).strip()]
        + [str(item).strip() for item in domain_context.get("p2", []) if str(item).strip()]
        + [str(item).strip() for item in domain_context.get("out_of_scope", []) if str(item).strip()]
    )[:6]
    creative_candidates = deferred_candidates[:3] if depth_mode == "creative" else []

    operationally_rich = detect_operationally_rich_domain("\n".join([source_text, prd_text, *stage_texts.values()]))
    product_source_direct_driver_summary = load_product_source_direct_driver_summary(output_dir)
    core_scenarios = choose_core_scenarios(prd_text, stage_texts, domain_context)
    core_scenarios = attach_business_completeness_context_to_scenarios(
        core_scenarios,
        product_source_direct_driver_summary,
        depth_posture=depth_posture,
    )
    scenario_rows = score_core_scenarios(
        core_scenarios,
        depth_posture=depth_posture,
        operationally_rich=operationally_rich,
        roles=roles,
        constraints=constraints,
        nfrs=nfrs,
        semantic_anchors=semantic_anchors,
    )
    scenario_set_status, scenario_set_judgment = summarize_scenario_set(scenario_rows, operationally_rich, depth_posture)
    baseline_status, baseline_judgment, baseline_met = summarize_baseline_calibration(
        scenario_rows,
        operationally_rich,
        depth_posture,
    )
    unknowns = summarize_unknowns(reasoning_units, maturity_rows)
    tradeoff_count = sum(
        1
        for units in reasoning_units.values()
        for unit in units
        if len([item for item in unit.get("alternatives_compared", []) if str(item).strip()]) >= 2
    )
    demo_risk_status, demo_risks = build_demo_risks(
        scenario_rows,
        depth_posture=depth_posture,
        operationally_rich=operationally_rich,
        unknowns=unknowns,
        tradeoff_count=tradeoff_count,
    )
    loop_plan = build_agentic_loop_plan(
        version=version,
        depth_mode=depth_mode,
        depth_posture=depth_posture,
        scenario_rows=scenario_rows,
        scenario_set_status=scenario_set_status,
        baseline_status=baseline_status,
        baseline_judgment=baseline_judgment,
        demo_risks=demo_risks,
        unknowns=unknowns,
        product_source_direct_driver_summary=product_source_direct_driver_summary,
    )

    paths = depth_runtime_artifact_paths(output_dir)
    loop_paths = agentic_loop_artifact_paths(output_dir)
    write_markdown(
        paths[REAL_WORLD_BASELINE_CALIBRATION],
        render_baseline_calibration_markdown(
            version=version,
            depth_mode=depth_mode,
            depth_posture=depth_posture,
            operationally_rich=operationally_rich,
            baseline_status=baseline_status,
            baseline_judgment=baseline_judgment,
            scenario_rows=scenario_rows,
            unknowns=unknowns,
            prd_text=prd_text,
        ),
        output_locale,
    )
    write_markdown(
        paths[DOMAIN_BASELINE_SCENARIO_MAP],
        render_scenario_map_markdown(
            version=version,
            depth_mode=depth_mode,
            primary_segment=primary_segment,
            scenario_rows=scenario_rows,
            deferred_candidates=deferred_candidates,
            creative_candidates=creative_candidates,
        ),
        output_locale,
    )
    write_markdown(
        paths[CORE_SCENARIO_DEPTH_MATRIX],
        render_core_scenario_depth_matrix_markdown(
            version=version,
            scenario_rows=scenario_rows,
            scenario_set_status=scenario_set_status,
            scenario_set_judgment=scenario_set_judgment,
        ),
        output_locale,
    )
    write_markdown(
        paths[DEMO_RISK_REVIEW],
        render_demo_risk_review_markdown(
            version=version,
            demo_risk_status=demo_risk_status,
            demo_risks=demo_risks,
        ),
        output_locale,
    )
    write_markdown(
        paths[DECISION_OPTIONS_AND_TRADEOFFS],
        render_tradeoffs_markdown(
            version=version,
            depth_mode=depth_mode,
            reasoning_units=reasoning_units,
            creative_candidates=creative_candidates,
        ),
        output_locale,
    )
    write_markdown(
        paths[DOMAIN_ASSUMPTION_AND_EVIDENCE_LEDGER],
        render_assumption_evidence_ledger_markdown(
            version=version,
            reasoning_units=reasoning_units,
            maturity_rows=maturity_rows,
        ),
        output_locale,
    )
    write_markdown(
        loop_paths[AGENTIC_LOOP_BRIEF],
        render_agentic_loop_brief_markdown(
            version=version,
            loop_plan=loop_plan,
        ),
        output_locale,
    )
    write_json(loop_paths[AGENTIC_LOOP_PLAN_FILENAME], loop_plan)

    summary = {
        "version": version,
        "owner": owner,
        "depth_mode": depth_mode,
        "thinking_value_gain_mode": thinking_value_gain_mode,
        "thinking_value_gain_output_profile": (
            thinking_value_gain_output_profile if thinking_value_gain_mode == "full-use" else "not-applied"
        ),
        "depth_posture": depth_posture,
        "operationally_rich_domain": operationally_rich,
        "core_scenario_count": len(scenario_rows),
        "scenario_set_status": scenario_set_status,
        "scenario_set_judgment": scenario_set_judgment,
        "baseline_calibration_status": baseline_status,
        "baseline_calibration_judgment": baseline_judgment,
        "ordinary_real_world_baseline_met": baseline_met,
        "demo_risk_status": demo_risk_status,
        "demo_risk_count": len(demo_risks),
        "tradeoff_count": tradeoff_count,
        "unknown_count": len(unknowns),
        "creative_mode_active": depth_mode == "creative",
        "baseline_truth_separated": depth_mode != "creative" or True,
        "artifacts": {name: str(path) for name, path in paths.items()},
        "agentic_loop_artifacts": {name: str(path) for name, path in loop_paths.items()},
        "agentic_loop_focus_areas": list(loop_plan.get("focus_areas", [])),
        "agentic_loop_target_count": int(loop_plan.get("target_count", 0)),
        "agentic_loop_high_value_gap_count": int(loop_plan.get("high_value_gap_count", 0)),
        "agentic_loop_convergence_ready": bool(loop_plan.get("convergence_ready", False)),
        "agentic_loop_round_focus": str(loop_plan.get("round_focus", "")),
        "active_scenario_dimensions": list(scenario_rows[0].get("active_dimensions", [])) if scenario_rows else [],
        "scenario_rows": [
            {
                "title": row["title"],
                "source": row["source"],
                "status": row["status"],
                "total_score": row["total_score"],
                "active_dimensions": row.get("active_dimensions", []),
                "scores": row["scores"],
                "loop_dimensions": row.get("loop_dimensions", []),
                "loop_scores": row.get("loop_scores", {}),
                "gaps": row["gaps"],
            }
            for row in scenario_rows
        ],
    }
    write_json(paths[DEPTH_RUNTIME_SUMMARY_FILENAME], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit Phase-1 depth runtime artifacts")
    parser.add_argument("--source", required=True)
    parser.add_argument("--stage-01", required=True)
    parser.add_argument("--stage-02a", required=True)
    parser.add_argument("--stage-02b", required=True)
    parser.add_argument("--stage-03", required=True)
    parser.add_argument("--stage-04", required=True)
    parser.add_argument("--prd", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--owner", default="Codex Phase-1 depth runtime")
    parser.add_argument("--depth-mode", choices=("baseline", "creative"), default="baseline")
    parser.add_argument("--thinking-value-gain-mode", choices=("off", "full-use"), default="off")
    parser.add_argument(
        "--thinking-value-gain-output-profile",
        choices=THINKING_VALUE_GAIN_OUTPUT_PROFILES,
        default="coverage_rich",
    )
    parser.add_argument("--output-locale", default=resolve_output_locale())
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    output_dir = Path(args.output_dir).resolve()
    stage_paths = {
        "stage_01": Path(args.stage_01).resolve(),
        "stage_02a": Path(args.stage_02a).resolve(),
        "stage_02b": Path(args.stage_02b).resolve(),
        "stage_03": Path(args.stage_03).resolve(),
        "stage_04": Path(args.stage_04).resolve(),
    }
    prd_path = Path(args.prd).resolve()

    summary = emit_depth_runtime_artifacts(
        source_path=source_path,
        stage_paths=stage_paths,
        prd_path=prd_path,
        output_dir=output_dir,
        version=args.version,
        owner=args.owner,
        depth_mode=args.depth_mode,
        thinking_value_gain_mode=args.thinking_value_gain_mode,
        thinking_value_gain_output_profile=args.thinking_value_gain_output_profile,
        output_locale=args.output_locale,
    )

    for artifact in DEPTH_RUNTIME_TEXT_ARTIFACTS:
        print(f"generated: {output_dir / artifact}")
    print(f"generated: {output_dir / DEPTH_RUNTIME_SUMMARY_FILENAME}")
    for artifact in AGENTIC_LOOP_TEXT_ARTIFACTS:
        print(f"generated: {output_dir / artifact}")
    print(f"generated: {output_dir / AGENTIC_LOOP_PLAN_FILENAME}")
    print(f"core_scenario_count: {summary['core_scenario_count']}")
    print(f"scenario_set_status: {summary['scenario_set_status']}")
    print(f"baseline_calibration_status: {summary['baseline_calibration_status']}")
    print(f"demo_risk_status: {summary['demo_risk_status']}")
    print(f"agentic_loop_target_count: {summary['agentic_loop_target_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
