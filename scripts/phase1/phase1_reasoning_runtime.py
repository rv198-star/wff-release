#!/usr/bin/env python3
"""
Compile Phase-1 reasoning units from stage method assets and operator registry.
"""

from __future__ import annotations

import re
from typing import Any

from common.script_data_assets import load_script_json_asset

WFF_SCRIPT_DATA_ASSETS = (
    "scripts/phase1/data/phase1-reasoning-runtime-blueprints.json",
)

PHASE1_BUSINESS_WORLD_MODEL_FILENAME = "phase1-business-world-model.json"
PHASE1_OPERATING_BASELINE_MODEL_FILENAME = "phase1-operating-baseline-model.json"
PHASE1_PRODUCT_WORLD_DECISION_FILENAME = "phase1-product-world-decision.json"
PHASE1_BUSINESS_RELEASE_TRUTH_PACK_FILENAME = "phase1-business-release-truth-pack.json"
PHASE1_PLANNING_CONTROL_TRUTH_PACK_FILENAME = "phase1-planning-control-truth-pack.json"


def _load_reasoning_runtime_blueprints() -> dict[str, Any]:
    loaded = load_script_json_asset(__file__, "phase1-reasoning-runtime-blueprints.json")
    return loaded if isinstance(loaded, dict) else {}


def _coerce_operator_library(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _coerce_blueprint_map(value: object) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, dict):
        return {}
    coerced: dict[str, list[dict[str, Any]]] = {}
    for key, items in value.items():
        if not isinstance(items, list):
            continue
        coerced[str(key)] = [dict(item) for item in items if isinstance(item, dict)]
    return coerced


_REASONING_RUNTIME_BLUEPRINTS = _load_reasoning_runtime_blueprints()
OPERATOR_LIBRARY = _coerce_operator_library(_REASONING_RUNTIME_BLUEPRINTS.get("operator_library"))
STAGE_REASONING_BLUEPRINTS = _coerce_blueprint_map(
    _REASONING_RUNTIME_BLUEPRINTS.get("stage_reasoning_blueprints")
)
MATURITY_CONFIDENCE_BLUEPRINTS = _coerce_blueprint_map(
    _REASONING_RUNTIME_BLUEPRINTS.get("maturity_confidence_blueprints")
)

def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.lower()).strip()


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def method_matches(method: str, hint: str) -> bool:
    normalized_method = normalize_text(method)
    normalized_hint = normalize_text(hint)
    if not normalized_method or not normalized_hint:
        return False
    if normalized_hint in normalized_method or normalized_method in normalized_hint:
        return True
    tokens = [token for token in normalized_hint.split() if len(token) > 2 or re.search(r"[\u4e00-\u9fff]", token)]
    return bool(tokens) and all(token in normalized_method for token in tokens)


def resolve_method_assets(available_methods: list[str], hints: list[str]) -> list[str]:
    resolved: list[str] = []
    for hint in hints:
        match = next((method for method in available_methods if method_matches(method, hint)), None)
        resolved.append(match or hint)
    return unique_preserve_order(resolved)


def render_template_value(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return value.format(**context)
    if isinstance(value, dict):
        return {key: render_template_value(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [render_template_value(item, context) for item in value]
    return value


NON_GROWTH_DOMAIN_CONTAMINATION_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\bSEO dashboard\b", "single-view dashboard"),
    (r"\bpage-level tracking\b", "surface-level event logging"),
    (r"\bcompetitor snapshot\b", "peer comparison snapshot"),
    (r"\bcompetitor context\b", "peer comparison context"),
    (r"\brecommendation-first\b", "guidance-first"),
    (r"\brecommendation-only\b", "guidance-only"),
    (r"\bRecommendation Payload Contract\b", "Module Interface Payload Contract"),
    (r"\brecommendation payload contract\b", "module interface payload contract"),
    (r"\bsource-level recommendation detail\b", "source-level structured capability detail"),
    (r"\brecommendation detail\b", "structured capability detail"),
    (r"\bdetailed recommendation outputs\b", "detailed structured outputs"),
    (r"\bdetailed recommendation capability\b", "detailed structured capability"),
    (r"\baction recommendation payload\b", "structured action payload"),
    (r"\brecommendation capability\b", "structured capability"),
    (r"\brecommendation outputs\b", "structured outputs"),
    (r"\brecommendation trust\b", "next-step guidance trust"),
    (r"\brecommendation-to-task bridge\b", "next-step-guidance-to-task bridge"),
    (r"\brecommendation\s*/\s*task\s*/\s*review\b", "evidence / next action / result judgment"),
    (r"\brecommendation\s+与\s+task\b", "next-step guidance 与 downstream execution"),
    (r"\brecommendation/task\b", "next-step-guidance/downstream-execution"),
    (r"\bDeferred Attribution and Conversion Seam\b", "Deferred Capability Seam"),
    (r"\bdeferred attribution / conversion seam\b", "deferred capability seam"),
    (r"\battribution\s*/\s*conversion\b", "future measurement / downstream outcome"),
    (r"\bfuture measurement seam\s*/\s*conversion\b", "future measurement seam / downstream outcome"),
    (r"\battribution\b", "future measurement seam"),
    (r"\bUTM\b", "source tag"),
    (r"\bfunnel\b", "journey stage"),
    (r"\bcross-device\b", "multi-entry"),
]


def _semantic_guard_role_labels(context: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(context, dict):
        return {
            "primary_segment": "primary operator",
            "supporting_role": "supporting operator",
            "decision_role": "decision reviewer",
        }
    roles = [
        str(item).strip()
        for item in context.get("role_labels", [])
        if str(item).strip()
    ]
    primary_segment = str(context.get("primary_segment", "")).strip() or (roles[0] if roles else "primary operator")
    supporting_role = (
        str(context.get("supporting_role_label", "")).strip()
        or (roles[1] if len(roles) > 1 else "")
        or "supporting operator"
    )
    decision_role = (
        str(context.get("decision_role_label", "")).strip()
        or (roles[-1] if roles else "")
        or primary_segment
        or "decision reviewer"
    )
    return {
        "primary_segment": primary_segment,
        "supporting_role": supporting_role,
        "decision_role": decision_role,
    }


def _non_growth_domain_contamination_replacements(context: dict[str, Any] | None) -> list[tuple[str, str]]:
    labels = _semantic_guard_role_labels(context)
    return [
        (r"\bmarketing owner\b", labels["primary_segment"]),
        (r"\bMarketing Owner\b", labels["primary_segment"]),
        (r"\bcontent operator\b", labels["supporting_role"]),
        (r"\bContent Operator\b", labels["supporting_role"]),
        (r"\bbusiness owner\b", labels["decision_role"]),
        (r"\bBusiness Owner\b", labels["decision_role"]),
        *NON_GROWTH_DOMAIN_CONTAMINATION_REPLACEMENTS,
    ]


def _contextual_domain_purity_replacements(context: dict[str, Any] | None) -> list[tuple[str, str]]:
    if not isinstance(context, dict):
        return []
    if str(context.get("domain_posture", "")).strip() == "growth-observation":
        return []
    mainline_surface_catalog = str(context.get("mainline_surface_catalog", "")).strip() or "mainline workflow surfaces"
    mainline_subsystem_catalog = str(context.get("mainline_subsystem_catalog", "")).strip() or mainline_surface_catalog
    upstream_downstream_boundary_label = (
        str(context.get("upstream_downstream_boundary_label", "")).strip() or "上游记录与下游动作"
    )
    object_dependency_chain = str(context.get("object_dependency_chain", "")).strip() or "source-defined workflow chain"
    workflow_entry_and_detail = str(context.get("workflow_entry_and_detail_label", "")).strip() or "关键工作入口与记录详情"
    case_detail_label = str(context.get("case_detail_label", "")).strip() or "current case detail"
    case_detail_plural_label = str(context.get("case_detail_plural_label", "")).strip() or "current case details"
    supporting_context_label = str(context.get("supporting_context_label", "")).strip() or "secondary supporting context"
    return [
        (
            r"overview\s*/\s*findings\s*/\s*tasks\s*/\s*competitors\s*/\s*reports\s*/\s*settings",
            mainline_surface_catalog,
        ),
        (r"\boverview 与 findings\b", workflow_entry_and_detail),
        (
            r"scope\s*->\s*observation.*?review chain",
            object_dependency_chain,
        ),
        (
            r"Scope Definition\s*->\s*Analysis Cycle\s*->\s*Insight Record\s*->\s*next-step action\s*->\s*Execution Task\s*->\s*Review Summary",
            object_dependency_chain,
        ),
        (
            r"Scope\s*&\s*Governance、Observation\s*&\s*Scoring、next-step guidance\s*&\s*Tasking、Review\s*&\s*Reporting",
            mainline_subsystem_catalog,
        ),
        (r"governance\s*/\s*observation\s*/\s*next-step guidance\s*/\s*review split", mainline_subsystem_catalog),
        (r"Observation 与 next-step guidance", upstream_downstream_boundary_label),
        (r"\bcompetitor context\b", supporting_context_label),
        (r"\bdashboard-only\b", "summary-only"),
    ]


def sanitize_domain_default_truth(value: Any, context: dict[str, Any] | None = None) -> Any:
    if isinstance(value, str):
        sanitized = value
        replacements: list[tuple[str, str]] = []
        if isinstance(context, dict) and str(context.get("domain_posture", "")).strip() != "growth-observation":
            replacements.extend(_non_growth_domain_contamination_replacements(context))
            replacements.extend(_contextual_domain_purity_replacements(context))
        for pattern, replacement in replacements:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized
    if isinstance(value, dict):
        return {key: sanitize_domain_default_truth(item, context=context) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_domain_default_truth(item, context=context) for item in value]
    return value


def _compact_truth_text(value: Any) -> str:
    compacted = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(compacted) >= 2 and compacted.startswith("`") and compacted.endswith("`"):
        compacted = compacted[1:-1].strip()
    return compacted


def _non_empty_truth_values(values: list[Any]) -> list[str]:
    return [text for text in (_compact_truth_text(value) for value in values) if text]


def classify_substitute_pressure_types(substitutes: list[str], topology_archetype: str) -> list[str]:
    """Classify plausible current-state substitutes without naming cases."""
    text = " ".join(substitutes).lower()
    classes: list[str] = []
    if re.search(r"dashboard|report|archive|bi\b|visibility|summary", text):
        classes.append("read-only substitute")
    if re.search(r"agency|consultant|advisor|advisory|manual service|manual-service|coordinator", text):
        classes.append("human-service substitute")
    if re.search(r"spreadsheet|sheet|chat|form|calendar|ticket", text):
        classes.append("fragmented-tool substitute")
    if re.search(r"crm|emr|record|inventory|ledger|case log|case-log", text):
        classes.append("system-of-record substitute")
    if re.search(r"workflow fragment|single|appointment|task|approval|review step|fragment", text):
        classes.append("workflow-fragment substitute")
    if not classes:
        classes.extend(
            ["read-only substitute", "human-service substitute"]
            if topology_archetype == "decision-centric"
            else ["system-of-record substitute", "workflow-fragment substitute"]
        )
    return unique_preserve_order(classes)


def thesis_quality_gate(thesis: dict[str, Any], substitute_types: list[str]) -> dict[str, str]:
    """Record quality risk signals while leaving rewrite judgment to the agent."""
    combined = " ".join(str(value) for value in thesis.values()).lower()
    missing: list[str] = []
    if not _compact_truth_text(thesis.get("current_state_substitute_to_beat")) or not substitute_types:
        missing.append("plausible-substitute-pressure")
    if "because" not in combined and "因为" not in combined:
        missing.append("why-this-not-that-causal-argument")
    if not re.search(r"continue|revise|pause|继续|调整|暂停|closure|handoff|exception", combined):
        missing.append("investment-or-operating-proof")
    if not _compact_truth_text(thesis.get("buyer_user_operator_value")):
        missing.append("user-buyer-operator-value")
    if not _compact_truth_text(thesis.get("product_boundary_implication")):
        missing.append("architecture-pressure")
    return {
        "judgment": "agentic-rewrite-required" if missing else "agentic-rewrite-not-required",
        "missing_or_weak_signals": ", ".join(missing) if missing else "none",
        "script_boundary": "risk-record-only; final commercial judgment remains agentic",
    }


def select_primary_substitute_to_beat(substitutes: list[str], *, decision_pressure: bool) -> str:
    """Pick the substitute that creates the strongest generic business pressure."""
    if decision_pressure:
        for substitute in substitutes:
            if re.search(r"dashboard|report|archive|bi\b|visibility|summary|advisory|advisor|agency|manual", substitute, flags=re.IGNORECASE):
                return substitute
    for substitute in substitutes:
        if re.search(r"record|fragment|workflow|single|appointment|task|approval|inventory|emr|crm", substitute, flags=re.IGNORECASE):
            return substitute
    return substitutes[0] if substitutes else "current manual or partial substitute"


def build_commercial_argument_draft(arena: dict[str, Any]) -> dict[str, Any]:
    """Draft the reader-facing commercial argument before thesis fields."""
    candidates = [item for item in arena.get("business_thesis_candidates", []) if isinstance(item, dict)]
    chosen = candidates[0] if candidates else {}
    substitute_map = arena.get("substitute_and_current_state_map", {})
    buyer_map = arena.get("buyer_value_proof_map", {})
    reality_map = arena.get("reality_density_map", {})
    topology_archetype = str(arena.get("topology_archetype", "hybrid"))
    substitutes = _non_empty_truth_values(list(substitute_map.get("substitutes", []) if isinstance(substitute_map, dict) else []))
    proof_target = _compact_truth_text(buyer_map.get("evidence_that_changes_decision") if isinstance(buyer_map, dict) else "") or _compact_truth_text(chosen.get("proof_question")) or "review-bound proof target"
    decision_trigger = _compact_truth_text(buyer_map.get("continue_revise_pause_trigger") if isinstance(buyer_map, dict) else "")
    continuation_owner = _compact_truth_text(buyer_map.get("continuation_or_approval_owner") if isinstance(buyer_map, dict) else "") or _compact_truth_text(chosen.get("target_user_or_buyer")) or "decision owner"
    primary_pain = _compact_truth_text(chosen.get("primary_pain")) or _compact_truth_text(substitute_map.get("current_state_pressure") if isinstance(substitute_map, dict) else "") or "source-defined business pressure"
    chosen_name = _compact_truth_text(chosen.get("thesis_name")) or "source-grounded product thesis"
    boundary = _compact_truth_text(chosen.get("likely_first_product_boundary")) or "source-defined first-version boundary"
    decision_pressure = bool(
        topology_archetype == "decision-centric"
        or (
            topology_archetype == "hybrid"
            and re.search(r"continue|revise|pause|继续|调整|暂停|budget|investment|投入|决策|decision", " ".join([proof_target, decision_trigger, continuation_owner]), flags=re.IGNORECASE)
        )
    )
    substitute_to_beat = select_primary_substitute_to_beat(substitutes, decision_pressure=decision_pressure)
    substitute_types = classify_substitute_pressure_types(substitutes, topology_archetype)
    if decision_pressure:
        why_substitute_is_not_enough = (
            f"{substitute_to_beat} can expose signals, but it does not connect evidence, action, and review into a decision the {continuation_owner} can use."
        )
        directional_proof = "directional review evidence is useful before exact ROI because it can still support continue / revise / pause decisions"
        value_mechanism = "decision certainty"
        argument_narrative = (
            f"{chosen_name} deserves investment now because {primary_pain}. "
            f"The product is not just {substitute_to_beat}: {why_substitute_is_not_enough} "
            f"The first proof target is {proof_target}; even before exact ROI is available, {directional_proof}. "
            f"That makes the first product boundary {boundary}, with architecture preserving action, evidence, and review continuity instead of a read-only surface."
        )
    else:
        why_substitute_is_not_enough = (
            f"{substitute_to_beat} may record parts of the work, but it leaves role handoff, exception handling, or closure proof fragmented."
        )
        directional_proof = "closure evidence and exception resolution are useful before broader optimization proof because they show the service loop is real"
        value_mechanism = "service closure"
        argument_narrative = (
            f"{chosen_name} deserves commitment now because {primary_pain}. "
            f"The product is not merely {substitute_to_beat}: {why_substitute_is_not_enough} "
            f"The first proof target is {proof_target}; {directional_proof}. "
            f"That makes the first product boundary {boundary}, with architecture preserving handoff, exception, and closure states instead of a record-only shell."
        )
    return {
        "artifact_type": "commercial_argument_draft",
        "truth_state": "source-grounded-deterministic-fallback",
        "generation_mode": "deterministic-fallback",
        "quality_state": "source-grounded-but-needs-compression",
        "argument_narrative": argument_narrative,
        "primary_substitute_pressure": substitute_to_beat,
        "substitute_pressure_types": substitute_types,
        "why_substitute_is_not_enough": why_substitute_is_not_enough,
        "proof_that_changes_decision": proof_target,
        "directional_proof_when_exact_roi_missing": directional_proof,
        "value_mechanism": value_mechanism,
        "architecture_pressure": "preserve proof-bearing action/review continuity before reporting convenience" if decision_pressure else "preserve service handoff, exception, and closure proof before record convenience",
        "review_bound_truth": decision_trigger or "review-bound truth remains explicit until external evidence exists",
        "source_grounding_notes": _non_empty_truth_values([primary_pain, proof_target, substitute_to_beat])[:5],
        "rewrite_required": "agentic-commercial-argument-rewrite-required-before-claiming-sharpness",
    }


def _truth_signal_phrase(values: list[Any], fallback: str, *, limit: int = 2) -> str:
    picked = _non_empty_truth_values(values)
    if not picked:
        return fallback
    return "; ".join(picked[:limit])


TRUTH_ACTION_PATTERN = re.compile(
    r"reduce|improve|increase|avoid|prevent|stabilize|retain|clarify|support|complete|"
    r"continue|revise|pause|review|decision|"
    r"降低|减少|提升|改善|避免|防止|稳定|留存|澄清|支撑|完成|复盘|决策|继续|调整|暂停",
    flags=re.IGNORECASE,
)
TRUTH_ECONOMIC_SIGNAL_PATTERN = re.compile(
    r"budget|pricing|package|pilot|pay|willingness|quote|commercial|invest|investment|"
    r"预算|定价|试点|付费|意愿|报价|投入",
    flags=re.IGNORECASE,
)
TRUTH_CONTRACT_SPILLOVER_PATTERN = re.compile(
    r"payload|schema|registry|state machine|permission model|audit policy|entity graph|"
    r"traceability|contract|interface|模块接口|状态机|注册表|权限模型|审计策略|实体关系|可追溯",
    flags=re.IGNORECASE,
)
TRUTH_VALIDATION_SCAFFOLD_PATTERN = re.compile(
    r"simulation|signal|threshold|walkthrough|interview|prototype|validation|test|target_\d+|"
    r"演练|信号|阈值|访谈|原型|验证|测试|判定",
    flags=re.IGNORECASE,
)
TRUTH_PRESSURE_PATTERN = re.compile(
    r"lack|missing|cannot|unable|fragment|manual|waste|friction|delay|blocked|drop|lag|invisible|"
    r"缺少|缺失|无法|不能|碎片|人工|浪费|摩擦|延迟|阻塞|遗漏|滞后|断层|不可见|失控|买单",
    flags=re.IGNORECASE,
)
TRUTH_DIRECT_FAILURE_PATTERN = re.compile(
    r"lack|missing|cannot|unable|fragment|manual|waste|friction|delay|blocked|drop|lag|invisible|"
    r"缺少|缺失|无法|不能|碎片|人工|浪费|摩擦|延迟|阻塞|遗漏|滞后|断层|不可见|失控",
    flags=re.IGNORECASE,
)
TRUTH_STRATEGIC_PATTERN = re.compile(
    r"rather than|instead of|not just|not another|if\b|when\b|because\b|so\b|"
    r"而不是|而非|如果|当|因为|所以|以便|才能|workflow-first|闭环|判断|经营|证据链|行动|任务",
    flags=re.IGNORECASE,
)
TRUTH_POSITIVE_VALUE_PATTERN = re.compile(
    r"worth|valuable|improve|reduce|retain|support|investment|budget|judge|decision|easier|"
    r"值得|价值|提升|降低|减少|支撑|投入|预算|判断|决策|更容易|闭环|组织成|方向性收益",
    flags=re.IGNORECASE,
)
TRUTH_NOUNISH_PATTERN = re.compile(r"^[A-Za-z0-9\u4e00-\u9fff /&()（）,，._+-]{1,40}$")
TRUTH_SIGNAL_LABEL_PATTERN = re.compile(
    r"^(?:line|signal|evidence|clue|observation|finding|线索|证据|信号)\s*\d*\s*[:：-]\s*",
    flags=re.IGNORECASE,
)
TRUTH_SCAFFOLD_PREFIX_PATTERN = re.compile(
    r"^(?:adoption signal|review simulation|clickable(?:\s*/\s*structured prototype)? review|"
    r"structured prototype review|walkthrough|访谈/演练|点击原型 walkthrough \+ 访谈)\s*[:：-]\s*",
    flags=re.IGNORECASE,
)
TOPOLOGY_OPERATIONAL_PATTERN = re.compile(
    r"workflow|flow|handoff|state|execute|execution|service|visit|intake|register|task|queue|"
    r"流程|主线|链路|交接|状态|执行|服务|登记|履约|任务|处理|闭环",
    flags=re.IGNORECASE,
)
TOPOLOGY_EXCEPTION_PATTERN = re.compile(
    r"blocked|missing|constraint|permission|audit|approval|exception|fallback|retry|error|boundary|"
    r"阻塞|缺失|约束|权限|审计|审批|异常|回退|失败|边界|合规",
    flags=re.IGNORECASE,
)
TOPOLOGY_ROLE_PATTERN = re.compile(
    r"role|actor|owner|operator|manager|reviewer|staff|team|handoff|"
    r"角色|责任|负责人|执行|经理|评审|协作|交接|团队",
    flags=re.IGNORECASE,
)
TOPOLOGY_SUBSTITUTE_PATTERN = re.compile(
    r"dashboard|report(?:ing)?|tool|sheet|overlay|agency|manual advisory|"
    r"仪表盘|报表|工具|替代|壳子|而不是|而非|not just|rather than|instead of",
    flags=re.IGNORECASE,
)
TOPOLOGY_PROOF_PATTERN = re.compile(
    r"proof|evidence|review|signal|trend|baseline|conclusion|confidence|judge|decision|"
    r"证据|证明|评审|复盘|信号|趋势|基线|结论|判断|决策|方向性",
    flags=re.IGNORECASE,
)
TOPOLOGY_CONTINUATION_PATTERN = re.compile(
    r"budget|pricing|pay|quote|invest|investment|continue|revise|pause|buy|commercial|fund|"
    r"预算|定价|付费|报价|投入|继续|调整|暂停|买单|商业|经费",
    flags=re.IGNORECASE,
)
TRUTH_OPERATIONAL_FRAGMENT_PATTERN = re.compile(
    r"^(?:arrange|establish|register|execute|complete|create|build|trigger|configure|push|generate|"
    r"查看|建立|完成|推动|生成|触发|配置|登记|安排|执行)\b",
    flags=re.IGNORECASE,
)
TRUTH_CONSEQUENCE_PATTERN = re.compile(
    r"lead to|results? in|causes?|keeps?|so that|turn .* into|"
    r"worth continued investment|continued investment|budget review|action loop|"
    r"用户流失|运营判断滞后|持续投入|预算评审|动作闭环|看到了问题但没有动作|"
    r"经营动作|continue / revise / pause|继续投入|继续 / 调整 / 暂停|失控",
    flags=re.IGNORECASE,
)
TRUTH_CONDITIONAL_PATTERN = re.compile(
    r"^\s*(?:if\b|when\b|如果|若|当(?!前))",
    flags=re.IGNORECASE,
)
TRUTH_NEGATIVE_CONDITIONAL_PATTERN = re.compile(
    r"^\s*(?:if\b\s+(?:no|without)|when\b\s+(?:no|without)|如果没有|若没有|当没有)",
    flags=re.IGNORECASE,
)
TRUTH_OPPORTUNITY_PREFIX_PATTERN = re.compile(r"^(?:用|通过|借助|use|using)\b", flags=re.IGNORECASE)
TRUTH_CONTRAST_PATTERN = re.compile(r"rather than|instead of|not just|not another|而不是|而非|不愿意|不是", flags=re.IGNORECASE)
TRUTH_EXPERIENCE_FAILURE_PATTERN = re.compile(
    r"wait|waiting|handoff|manual reconstruction|manual|delay|friction|duplicate|blocked|"
    r"人工|人工遗漏|交接|补录|延迟|摩擦|阻塞|遗漏|失控",
    flags=re.IGNORECASE,
)


def _looks_like_workflow_chain(text: str) -> bool:
    probe = _normalize_truth_signal_text(text)
    return probe.count("->") + probe.count("→") >= 2


def _normalize_truth_signal_text(value: Any) -> str:
    text = _compact_truth_text(value)
    previous = None
    while text and text != previous:
        previous = text
        text = TRUTH_SIGNAL_LABEL_PATTERN.sub("", text).strip()
        text = TRUTH_SCAFFOLD_PREFIX_PATTERN.sub("", text).strip()
    return text.strip(" -–—")


def _strip_truth_modal(text: str) -> str:
    compact = _normalize_truth_signal_text(text)
    compact = re.sub(r"\bcan\b\s+", "", compact, flags=re.IGNORECASE)
    compact = re.sub(r"(?<=[\u4e00-\u9fffA-Za-z0-9)])能", "", compact, count=1)
    return compact.strip()


def _compress_truth_sentence(candidate: str, *, intent: str) -> str:
    text = _normalize_truth_signal_text(candidate)
    if not text:
        return ""

    zh_conditional = re.match(r"^(?:如果|若|当(?!前))\s*(.+?)[，,]\s*(?:就|则)?\s*(.+)$", text)
    if zh_conditional and intent != "pressure":
        condition = _strip_truth_modal(zh_conditional.group(1)).strip(" ，,。.;；:")
        outcome = _normalize_truth_signal_text(zh_conditional.group(2)).strip(" ，,。.;；:")
        if condition and outcome:
            return f"{condition}，{outcome}"

    en_conditional = re.match(r"^(?:if|when)\s+(.+?)[,，]\s*(?:then\s+)?(.+)$", text, flags=re.IGNORECASE)
    if en_conditional and intent != "pressure":
        condition = _strip_truth_modal(en_conditional.group(1)).strip(" ,.;:")
        outcome = _normalize_truth_signal_text(en_conditional.group(2)).strip(" ,.;:")
        if condition and outcome:
            return f"{condition}, {outcome}"

    zh_opportunity = re.match(
        r"^(?:用|通过|借助)\s*(.+?)(减少|降低|提升|改善|避免|防止|支撑|形成|组织成)(.+)$",
        text,
    )
    if zh_opportunity and intent in {"value", "commercial", "experience"}:
        subject = _normalize_truth_signal_text(zh_opportunity.group(1)).strip(" ，,。.;；:")
        verb = zh_opportunity.group(2).strip()
        outcome = _normalize_truth_signal_text(zh_opportunity.group(3)).strip(" ，,。.;；:")
        if subject and outcome:
            return f"{subject}{verb}{outcome}"

    return text


def _truth_sentence_matches_intent(text: str, *, intent: str) -> bool:
    if intent == "pressure":
        if TRUTH_CONDITIONAL_PATTERN.search(text) and not TRUTH_NEGATIVE_CONDITIONAL_PATTERN.search(text):
            return False
        return bool(TRUTH_DIRECT_FAILURE_PATTERN.search(text))
    if intent == "commercial":
        return bool(TRUTH_ECONOMIC_SIGNAL_PATTERN.search(text))
    if intent == "experience":
        return bool(TRUTH_EXPERIENCE_FAILURE_PATTERN.search(text))
    positive_value = bool(TRUTH_POSITIVE_VALUE_PATTERN.search(text) or TRUTH_CONTRAST_PATTERN.search(text))
    if TRUTH_DIRECT_FAILURE_PATTERN.search(text) and not positive_value:
        return False
    return bool(
        TRUTH_POSITIVE_VALUE_PATTERN.search(text)
        or TRUTH_ACTION_PATTERN.search(text)
        or TRUTH_STRATEGIC_PATTERN.search(text)
    )


def _rank_truth_sentence(candidate: str, *, intent: str) -> int:
    text = _compress_truth_sentence(candidate, intent=intent)
    score = 0
    if len(text) >= 18:
        score += 1
    if len(text) >= 36:
        score += 1
    if re.search(r"[，,；;：:!?？。]", text):
        score += 1
    if TRUTH_STRATEGIC_PATTERN.search(text):
        score += 3
    if TRUTH_ECONOMIC_SIGNAL_PATTERN.search(text):
        score += 2
    if TRUTH_ACTION_PATTERN.search(text):
        score += 2
    if TRUTH_NOUNISH_PATTERN.fullmatch(text):
        score -= 2
    if len(text) <= 12:
        score -= 2
    if intent == "pressure":
        if TRUTH_PRESSURE_PATTERN.search(text):
            score += 4
        if TRUTH_DIRECT_FAILURE_PATTERN.search(text):
            score += 4
        if TRUTH_CONSEQUENCE_PATTERN.search(text):
            score += 3
        if TRUTH_PRESSURE_PATTERN.search(text) and TRUTH_ECONOMIC_SIGNAL_PATTERN.search(text):
            score += 3
        if TRUTH_CONDITIONAL_PATTERN.search(text) and not TRUTH_DIRECT_FAILURE_PATTERN.search(text):
            score -= 4
        if TRUTH_OPERATIONAL_FRAGMENT_PATTERN.search(text) and not TRUTH_DIRECT_FAILURE_PATTERN.search(text):
            score -= 4
        if TRUTH_OPPORTUNITY_PREFIX_PATTERN.search(text) and not TRUTH_DIRECT_FAILURE_PATTERN.search(text):
            score -= 3
        if TRUTH_POSITIVE_VALUE_PATTERN.search(text) and not TRUTH_PRESSURE_PATTERN.search(text):
            score -= 2
        if re.search(r"willingness|pay|budget|quote|试点|付费|意愿|报价|买单", text, flags=re.IGNORECASE) and not TRUTH_DIRECT_FAILURE_PATTERN.search(text):
            score -= 2
    elif intent == "commercial":
        if TRUTH_ECONOMIC_SIGNAL_PATTERN.search(text):
            score += 5
        if re.search(r"continue|revise|pause|预算评审|动作闭环|买单|持续投入", text, flags=re.IGNORECASE):
            score += 3
        if TRUTH_CONTRAST_PATTERN.search(text):
            score += 2
    elif intent == "experience":
        if TRUTH_EXPERIENCE_FAILURE_PATTERN.search(text):
            score += 4
        if re.search(r"wait|waiting|handoff|manual reconstruction|人工遗漏|交接|补录|失控", text, flags=re.IGNORECASE):
            score += 3
        if TRUTH_CONDITIONAL_PATTERN.search(text) and not TRUTH_DIRECT_FAILURE_PATTERN.search(text):
            score -= 2
    else:
        if TRUTH_POSITIVE_VALUE_PATTERN.search(text):
            score += 3
        if TRUTH_OPERATIONAL_FRAGMENT_PATTERN.search(text) and not (
            TRUTH_POSITIVE_VALUE_PATTERN.search(text) or TRUTH_ECONOMIC_SIGNAL_PATTERN.search(text)
        ):
            score -= 4
        if TRUTH_DIRECT_FAILURE_PATTERN.search(text) and not TRUTH_POSITIVE_VALUE_PATTERN.search(text):
            score -= 6
        if TRUTH_CONSEQUENCE_PATTERN.search(text):
            score += 2
    return score


def _select_ranked_truth_sentence(
    values: list[str],
    workflow_label: str,
    fallback: str,
    *,
    intent: str,
    exclude: set[str] | None = None,
) -> str:
    ranked: list[tuple[int, int, str]] = []
    excluded = {normalized.casefold() for normalized in (exclude or set()) if normalized}
    for idx, raw in enumerate(values):
        candidate = _normalize_truth_signal_text(raw)
        if not candidate or len(candidate) < 12 or len(candidate) > 180:
            continue
        if _looks_like_truth_field_dump(candidate) or _looks_like_validation_scaffold(candidate):
            continue
        if re.match(r"^(?:系统必须|must\b)", candidate, flags=re.IGNORECASE):
            continue
        if _overlaps_flow_summary(candidate, workflow_label):
            continue
        if candidate.casefold() in excluded:
            continue
        compressed = _compress_truth_sentence(candidate, intent=intent)
        if not compressed or compressed.casefold() in excluded:
            continue
        if not _truth_sentence_matches_intent(compressed, intent=intent):
            continue
        ranked.append((-_rank_truth_sentence(compressed, intent=intent), idx, compressed))
    if ranked:
        ranked.sort()
        return ranked[0][2]
    return _compress_truth_sentence(fallback, intent=intent) if fallback else ""


def _looks_like_truth_field_dump(text: str) -> bool:
    probe = _normalize_truth_signal_text(text)
    if not probe:
        return False
    if _looks_like_workflow_chain(probe):
        return True
    if probe.count(";") >= 2:
        return True
    return bool(TRUTH_CONTRACT_SPILLOVER_PATTERN.search(probe))


def _looks_like_validation_scaffold(text: str) -> bool:
    raw_probe = _compact_truth_text(text)
    probe = _normalize_truth_signal_text(text)
    if not probe and not raw_probe:
        return False
    if TRUTH_VALIDATION_SCAFFOLD_PATTERN.search(raw_probe) or TRUTH_VALIDATION_SCAFFOLD_PATTERN.search(probe):
        return True
    if "% " in raw_probe or "% " in probe or re.search(r"\b>=?\s*\d+", raw_probe) or re.search(r"\b>=?\s*\d+", probe):
        return True
    return False


def _curate_truth_signals(values: list[Any], *, limit: int = 3, fallback: list[str] | None = None) -> list[str]:
    curated: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = _compress_truth_sentence(raw, intent="value")
        if not text or len(text) > 140 or _looks_like_truth_field_dump(text):
            continue
        if not _truth_sentence_matches_intent(text, intent="value"):
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        curated.append(text)
        if len(curated) >= limit:
            break
    if curated:
        return curated
    fallback_values = []
    for raw in fallback or []:
        text = _normalize_truth_signal_text(raw)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        fallback_values.append(text)
        if len(fallback_values) >= limit:
            break
    return fallback_values


def _human_join_truth_labels(values: list[str], fallback: str) -> str:
    labels = unique_preserve_order([_normalize_truth_signal_text(value) for value in values if _normalize_truth_signal_text(value)])
    labels = labels[:3]
    if not labels:
        return fallback
    rendered = [f"`{label}`" for label in labels]
    if len(rendered) == 1:
        return rendered[0]
    if len(rendered) == 2:
        return f"{rendered[0]} and {rendered[1]}"
    return f"{rendered[0]}, {rendered[1]}, and {rendered[2]}"


def _condense_chain_labels(values: list[str], *, head: int = 2, tail: int = 1) -> str:
    labels = [value for value in (_normalize_truth_signal_text(item) for item in values) if value]
    if not labels:
        return "source-defined workflow"
    if len(labels) <= head + tail + 1:
        return " -> ".join(labels)
    return " -> ".join([*labels[:head], "...", *labels[-tail:]])


def _overlaps_flow_summary(candidate: str, flow_summary: str) -> bool:
    left = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", candidate.casefold()).strip()
    right = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", flow_summary.casefold()).strip()
    if not left or not right:
        return False
    if left in right or right in left:
        return True
    left_tokens = {token for token in left.split() if len(token) > 1 or re.search(r"[\u4e00-\u9fff]", token)}
    right_tokens = {token for token in right.split() if len(token) > 1 or re.search(r"[\u4e00-\u9fff]", token)}
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens) / max(1, len(left_tokens))
    return overlap >= 0.6


def _select_objective_phrase(objectives: list[str], workflow_label: str) -> str:
    for raw in objectives:
        candidate = _compress_truth_sentence(raw, intent="value")
        if not candidate or len(candidate) > 120 or _looks_like_truth_field_dump(candidate):
            continue
        if _overlaps_flow_summary(candidate, workflow_label):
            continue
        return candidate
    return "the mainline work becomes routine instead of manually reconstructed"


def _select_boundary_anchor(
    preferred_labels: list[str],
    secondary_labels: list[str],
    fallback: str,
) -> str:
    for raw in [*preferred_labels, *secondary_labels]:
        candidate = _normalize_truth_signal_text(raw)
        if not candidate or len(candidate) > 80 or _looks_like_truth_field_dump(candidate):
            continue
        return candidate
    return fallback


def _proof_artifact_phrase(exit_anchor: str, object_names: list[str]) -> str:
    object_phrase = _human_join_truth_labels(object_names[:2], "the mainline objects")
    return f"traceable `{exit_anchor}` grounded in {object_phrase}"


def _select_pressure_phrase(values: list[str], workflow_label: str, fallback: str) -> str:
    return _select_ranked_truth_sentence(
        values,
        workflow_label,
        fallback,
        intent="pressure",
    )


def _curate_commercial_truth(values: list[str]) -> list[str]:
    curated: list[str] = []
    seen: set[str] = set()
    for raw in values:
        candidate = _compress_truth_sentence(raw, intent="commercial")
        if not candidate or len(candidate) > 180:
            continue
        if (
            _looks_like_truth_field_dump(candidate)
            or _looks_like_validation_scaffold(raw)
            or _looks_like_validation_scaffold(candidate)
        ):
            continue
        if re.search(r"至少|试用|意向|prototype|访谈|walkthrough|判定信号", candidate, flags=re.IGNORECASE):
            continue
        if not TRUTH_ECONOMIC_SIGNAL_PATTERN.search(candidate):
            continue
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        curated.append(candidate)
        if len(curated) >= 3:
            break
    return curated


def _select_commercial_phrase(values: list[str], workflow_label: str, fallback: str = "") -> str:
    return _select_ranked_truth_sentence(
        values,
        workflow_label,
        fallback,
        intent="commercial",
    )


def _select_value_phrase(
    values: list[str],
    workflow_label: str,
    fallback: str,
    *,
    exclude: set[str] | None = None,
) -> str:
    return _select_ranked_truth_sentence(
        values,
        workflow_label,
        fallback,
        intent="value",
        exclude=exclude,
    )


def _join_truth_clauses(values: list[str]) -> str:
    rendered: list[str] = []
    for raw in values:
        text = _normalize_truth_signal_text(raw)
        if not text:
            continue
        if not re.search(r"[。.!?]$", text):
            text = f"{text}。"
        rendered.append(text)
    return " ".join(rendered).strip()


def _truth_role_weight(role: str) -> int:
    lowered = str(role or "").casefold()
    score = 0
    if re.search(r"owner|manager|lead|head|director|sponsor|founder|负责人|经理|主管|总监|院长|店长", lowered):
        score += 4
    if re.search(r"decision|review|审批|评审|决策|governance|finance|ops|operation|business|admin|管理", lowered):
        score += 2
    if re.search(r"operator|执行|运营", lowered):
        score += 1
    return score


def _select_truth_continuation_owner(primary_segment: str, roles: list[str]) -> str:
    candidates = unique_preserve_order([primary_segment, *roles])
    weighted = [(_truth_role_weight(candidate), -idx, candidate) for idx, candidate in enumerate(candidates)]
    best = max(weighted) if weighted else None
    return best[2] if best else (primary_segment or "primary operator")


def _truth_slot(
    value: Any,
    *,
    truth_state: str,
    source_signals: list[Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "truth_state": _compact_truth_text(truth_state) or "review-bound",
        "value": _compact_truth_text(value),
    }
    signals = _non_empty_truth_values(list(source_signals or []))
    if signals:
        payload["source_signals"] = signals
    return payload


def _count_topology_pattern_hits(values: list[Any], pattern: re.Pattern[str]) -> tuple[int, list[str]]:
    matches: list[str] = []
    for raw in values:
        candidate = _compact_truth_text(raw)
        if not candidate or not pattern.search(candidate):
            continue
        matches.append(candidate)
    return len(matches), unique_preserve_order(matches)


def _topology_axis_signal_samples(
    *,
    objectives: list[str],
    module_names: list[str],
    flow_names: list[str],
    object_names: list[str],
    roles: list[str],
    constraints: list[str],
    nfrs: list[str],
    business_value_signals: list[str],
    pressure_signals: list[str],
    commercial_decision_signals: list[str],
    user_experience_signals: list[str],
) -> dict[str, list[str]]:
    operational_hits = _count_topology_pattern_hits(
        [*module_names, *flow_names, *object_names, *pressure_signals, *user_experience_signals],
        TOPOLOGY_OPERATIONAL_PATTERN,
    )[1]
    exception_hits = _count_topology_pattern_hits(
        [*constraints, *nfrs, *pressure_signals, *user_experience_signals],
        TOPOLOGY_EXCEPTION_PATTERN,
    )[1]
    role_hits = _count_topology_pattern_hits(
        [*roles, *pressure_signals, *user_experience_signals, *module_names],
        TOPOLOGY_ROLE_PATTERN,
    )[1]
    substitute_hits = _count_topology_pattern_hits(
        [*objectives, *business_value_signals, *pressure_signals, *commercial_decision_signals],
        TOPOLOGY_SUBSTITUTE_PATTERN,
    )[1]
    proof_hits = _count_topology_pattern_hits(
        [*objectives, *business_value_signals, *commercial_decision_signals, *module_names, *flow_names],
        TOPOLOGY_PROOF_PATTERN,
    )[1]
    continuation_hits = _count_topology_pattern_hits(
        [*objectives, *business_value_signals, *commercial_decision_signals, *pressure_signals],
        TOPOLOGY_CONTINUATION_PATTERN,
    )[1]
    return {
        "operational-chain": operational_hits[:3],
        "exception-state": exception_hits[:3],
        "role-coordination": role_hits[:3],
        "substitute-positioning": substitute_hits[:3],
        "proof-evidence": proof_hits[:3],
        "buyer-budget-continuation": continuation_hits[:3],
    }


def infer_topology_profile(context: dict[str, Any]) -> dict[str, Any]:
    domain_posture = _compact_truth_text(context.get("domain_posture")) or "generic-workflow"
    objectives = _non_empty_truth_values(list(context.get("objectives", [])))
    roles = _non_empty_truth_values(list(context.get("roles", [])))
    constraints = _non_empty_truth_values(list(context.get("constraints", [])))
    nfrs = _non_empty_truth_values(list(context.get("nfrs", [])))
    business_value_signals = _non_empty_truth_values(list(context.get("business_value_signals", [])))
    pressure_signals = _non_empty_truth_values(list(context.get("pressure_signals", [])))
    commercial_decision_signals = _non_empty_truth_values(list(context.get("commercial_decision_signals", [])))
    strong_commercial_signals = [
        item
        for item in commercial_decision_signals
        if not re.search(
            r"待验证|unknown|provisional|意向|试用|walkthrough|interview|访谈|原型|验证|判定信号",
            item,
            flags=re.IGNORECASE,
        )
    ]
    user_experience_signals = _non_empty_truth_values(list(context.get("user_experience_signals", [])))
    module_rows = [row for row in context.get("modules", []) if isinstance(row, dict)]
    object_rows = [row for row in context.get("objects", []) if isinstance(row, dict)]
    flow_rows = [row for row in context.get("flows", []) if isinstance(row, dict)]
    module_names = _non_empty_truth_values([row.get("module", "") for row in module_rows])
    flow_names = _non_empty_truth_values([row.get("name", "") for row in flow_rows])
    object_names = unique_preserve_order(
        _non_empty_truth_values(
            [
                row.get("Object", "") or row.get("object", "") or row.get("Owner Module", "")
                for row in object_rows
            ]
        )
    )

    samples = _topology_axis_signal_samples(
        objectives=objectives,
        module_names=module_names,
        flow_names=flow_names,
        object_names=object_names,
        roles=roles,
        constraints=constraints,
        nfrs=nfrs,
        business_value_signals=business_value_signals,
        pressure_signals=pressure_signals,
        commercial_decision_signals=strong_commercial_signals,
        user_experience_signals=user_experience_signals,
    )

    operational_chain_score = (
        min(len(module_names), 3)
        + min(len(flow_names), 2)
        + min(max(len(object_names) - 1, 0), 2)
        + min(len(samples["operational-chain"]), 2)
    )
    exception_state_score = (
        min(len(constraints), 2)
        + min(len(nfrs), 1)
        + min(len(samples["exception-state"]), 2)
    )
    role_coordination_score = (
        min(max(len(roles) - 1, 0), 3)
        + min(len(samples["role-coordination"]), 2)
    )
    substitute_positioning_score = min(len(samples["substitute-positioning"]), 3)
    proof_evidence_score = min(len(samples["proof-evidence"]), 3) + (1 if commercial_decision_signals else 0)
    buyer_budget_continuation_score = (
        min(len(samples["buyer-budget-continuation"]), 3)
        + (2 if strong_commercial_signals else 0)
    )

    axis_scores = {
        "operational-chain": operational_chain_score,
        "exception-state": exception_state_score,
        "role-coordination": role_coordination_score,
        "substitute-positioning": substitute_positioning_score,
        "proof-evidence": proof_evidence_score,
        "buyer-budget-continuation": buyer_budget_continuation_score,
    }
    execution_score = (
        axis_scores["operational-chain"]
        + axis_scores["exception-state"]
        + axis_scores["role-coordination"]
    )
    decision_score = (
        axis_scores["substitute-positioning"]
        + axis_scores["proof-evidence"]
        + axis_scores["buyer-budget-continuation"] * 2
    )
    if decision_score >= execution_score + 2:
        topology_archetype = "decision-centric"
        ordered_axes = [
            "buyer-budget-continuation",
            "proof-evidence",
            "substitute-positioning",
        ]
        primary_depth_axes = [axis for axis in ordered_axes if axis_scores[axis] > 0] or ordered_axes[:2]
        secondary_depth_axes = [
            axis
            for axis in ("operational-chain", "role-coordination", "exception-state")
            if axis_scores[axis] >= 2
        ]
        ordinary_real_world_baseline_definition = (
            "ordinary real-world baseline means the product preserves one economic decision loop: "
            "signal -> action -> review -> continue / revise / pause, with explicit proof artifacts "
            "and a visible reason why this should beat reporting-only substitutes"
        )
        misfit_risk_if_wrong = (
            "If this profile is wrong, the output can stay orderly while the business proof target "
            "collapses into reporting, dashboard language, or workflow cosmetics."
        )
        structure_implications = (
            "Preserve substitute comparison, proof artifacts, and the continue / revise / pause "
            "decision path before compressing the structure into a generic workflow shell."
        )
    elif execution_score >= decision_score + 2:
        topology_archetype = "execution-centric"
        primary_depth_axes = [
            axis
            for axis in ("operational-chain", "role-coordination", "exception-state")
            if axis_scores[axis] >= 4
        ] or ["operational-chain", "role-coordination"]
        secondary_depth_axes = [
            axis
            for axis in ("operational-chain", "role-coordination", "exception-state")
            if axis not in primary_depth_axes and axis_scores[axis] >= 2
        ]
        ordinary_real_world_baseline_definition = (
            "ordinary real-world baseline means the product preserves one role-owned operating chain "
            "with visible state handoff, blocked conditions, and next-step continuity"
        )
        misfit_risk_if_wrong = (
            "If this profile is wrong, the output can stay structured while the operating world "
            "remains thin, handoffs stay implicit, and the product feels like a clean demo shell."
        )
        structure_implications = (
            "Preserve actor ownership, state visibility, blocked reasons, and cross-step handoff "
            "instead of flattening the product into isolated capability buckets."
        )
    else:
        topology_archetype = "hybrid"
        primary_depth_axes = unique_preserve_order(
            [
                "operational-chain" if axis_scores["operational-chain"] > 0 else "",
                "buyer-budget-continuation" if axis_scores["buyer-budget-continuation"] > 0 else "",
                "proof-evidence" if axis_scores["proof-evidence"] > 0 else "",
            ]
        ) or ["operational-chain", "proof-evidence"]
        secondary_depth_axes = [
            axis
            for axis in (
                "role-coordination",
                "exception-state",
                "substitute-positioning",
            )
            if axis_scores[axis] >= 2
        ]
        ordinary_real_world_baseline_definition = (
            "ordinary real-world baseline means the product must survive both real operating handoffs "
            "and the economic decision loop that decides whether another round continues"
        )
        misfit_risk_if_wrong = (
            "If this profile is wrong, the output may preserve one side of the business while making "
            "the other side thin: either a crisp workflow with weak decision leverage or a sharp decision story with fake operations."
        )
        structure_implications = (
            "Keep execution continuity and decision-proof continuity visible together; do not let one "
            "axis erase the other during structure compression."
        )

    dominant_axis = max(axis_scores, key=axis_scores.get)
    rationale_samples = samples.get(dominant_axis, [])
    rationale_example = rationale_samples[0] if rationale_samples else (
        commercial_decision_signals[0]
        if commercial_decision_signals
        else pressure_signals[0]
        if pressure_signals
        else objectives[0]
        if objectives
        else "source-defined operating pressure"
    )
    topology_rationale = (
        f"This run is routed as `{topology_archetype}` because the strongest reusable depth pressure sits around "
        f"`{', '.join(primary_depth_axes)}` and is visible in source-grounded signals such as `{rationale_example}`."
    )
    reclassification_trigger = (
        "Reclassify before freeze if later rounds show the dominant credibility risk has shifted to the opposite side "
        "of the business topology."
    )

    return {
        "topology_archetype": topology_archetype,
        "topology_rationale": topology_rationale,
        "primary_depth_axes": primary_depth_axes,
        "secondary_depth_axes": secondary_depth_axes,
        "ordinary_real_world_baseline_definition": ordinary_real_world_baseline_definition,
        "misfit_risk_if_wrong": misfit_risk_if_wrong,
        "structure_implications": structure_implications,
        "reclassification_trigger": reclassification_trigger,
        "domain_posture": domain_posture,
        "axis_scores": axis_scores,
        "axis_signal_samples": samples,
    }


def build_business_proof_track(
    *,
    topology_archetype: str,
    domain_posture: str,
    primary_depth_axes: list[str],
    secondary_depth_axes: list[str],
    chosen_product_world: str,
    rejected_product_worlds: list[str],
    proof_artifact: str,
    continuation_owner: str,
    spend_at_risk: str,
    decision_trigger: str,
) -> dict[str, Any]:
    decision_axes = {"buyer-budget-continuation", "proof-evidence", "substitute-positioning"}
    execution_axes = {"operational-chain", "role-coordination", "exception-state"}
    axis_set = set(primary_depth_axes) | set(secondary_depth_axes)
    decision_pressure = len(axis_set & decision_axes)
    execution_pressure = len(axis_set & execution_axes)

    if topology_archetype == "decision-centric" or (
        topology_archetype == "hybrid" and decision_pressure >= execution_pressure
    ):
        proof_track = "economic-decision-proof"
        dominant_proof_risk = "business-proof-thinness"
        proof_questions = [
            "why the product should beat reporting-only substitutes",
            "who owns continuation or budget commitment",
            "what proof artifact is enough before exact attribution is available",
            "what signal triggers continue / revise / pause",
        ]
    elif topology_archetype == "execution-centric" or domain_posture == "operational-service":
        proof_track = "operational-service-proof"
        dominant_proof_risk = "operating-world-thinness"
        proof_questions = [
            "whether the operating chain reflects real work rather than a demo path",
            "which role owns each state handoff",
            "which blocked, invalid, or exception states prevent unsafe progress",
            "what record proves the service loop is complete",
        ]
    else:
        proof_track = "mixed-proof"
        dominant_proof_risk = "unbalanced-proof-thinness"
        proof_questions = [
            "which side is the dominant failure risk: operations or business proof",
            "what proof artifact lets the next decision continue safely",
            "what workflow detail must stay explicit so proof does not become decorative",
        ]

    return {
        "artifact_type": "business_proof_track",
        "proof_track": proof_track,
        "dominant_proof_risk": dominant_proof_risk,
        "routing_hint": topology_archetype,
        "primary_depth_axes": primary_depth_axes,
        "secondary_depth_axes": secondary_depth_axes,
        "chosen_product_world": chosen_product_world,
        "substitute_pressure": rejected_product_worlds,
        "proof_questions": proof_questions,
        "proof_artifact": proof_artifact,
        "continuation_owner": continuation_owner,
        "spend_at_risk": spend_at_risk,
        "continuation_decision": decision_trigger,
    }




def choose_business_thesis(arena: dict[str, Any], source_text: str = "", commercial_argument_draft: dict[str, Any] | None = None) -> dict[str, Any]:
    """Select the strongest business thesis after arena exploration.

    The selector is generic: it chooses by topology, proof pressure, and
    substitute pressure, never by case name.
    """
    candidates = [item for item in arena.get("business_thesis_candidates", []) if isinstance(item, dict)]
    chosen = candidates[0] if candidates else {}
    rejected = candidates[1:]
    substitutes_map = arena.get("substitute_and_current_state_map", {})
    buyer_map = arena.get("buyer_value_proof_map", {})
    reality_map = arena.get("reality_density_map", {})
    topology_archetype = str(arena.get("topology_archetype", "hybrid"))
    substitutes = _non_empty_truth_values(list(substitutes_map.get("substitutes", []) if isinstance(substitutes_map, dict) else []))
    primary_reality_focus = _compact_truth_text(reality_map.get("primary_reality_focus") if isinstance(reality_map, dict) else "")
    chosen_name = _compact_truth_text(chosen.get("thesis_name")) or "source-grounded product thesis"
    chosen_boundary = _compact_truth_text(chosen.get("likely_first_product_boundary")) or "source-defined first-version boundary"
    chosen_pain = _compact_truth_text(chosen.get("primary_pain")) or "source-defined business pressure"
    chosen_value = _compact_truth_text(chosen.get("value_mechanism")) or "preserve the source-defined value mechanism"
    proof_target = _compact_truth_text(buyer_map.get("evidence_that_changes_decision") if isinstance(buyer_map, dict) else "") or _compact_truth_text(chosen.get("proof_question")) or "review-bound proof target"
    decision_trigger = _compact_truth_text(buyer_map.get("continue_revise_pause_trigger") if isinstance(buyer_map, dict) else "")
    continuation_owner = _compact_truth_text(buyer_map.get("continuation_or_approval_owner") if isinstance(buyer_map, dict) else "") or _compact_truth_text(chosen.get("target_user_or_buyer")) or "decision owner"
    decision_pressure = bool(
        topology_archetype == "decision-centric"
        or (
            topology_archetype == "hybrid"
            and re.search(r"continue|revise|pause|继续|调整|暂停|budget|investment|投入|决策|decision", " ".join([proof_target, decision_trigger, continuation_owner]), flags=re.IGNORECASE)
        )
    )
    draft = commercial_argument_draft if isinstance(commercial_argument_draft, dict) else {}
    substitute_to_beat = _compact_truth_text(draft.get("primary_substitute_pressure")) or select_primary_substitute_to_beat(substitutes, decision_pressure=decision_pressure)
    rejected_names = [_compact_truth_text(item.get("thesis_name")) for item in rejected if _compact_truth_text(item.get("thesis_name"))]
    if decision_pressure:
        why = (
            f"Choose `{chosen_name}` because it keeps proof, action, and the {continuation_owner} decision loop connected; "
            f"{substitute_to_beat} is weaker because it can show signals without changing a continue / revise / pause decision."
        )
    elif topology_archetype == "execution-centric":
        why = (
            f"Choose `{chosen_name}` because it preserves real service operation, role handoff, exception handling, and closure proof; "
            f"{substitute_to_beat} is weaker because it can leave the operating chain fragmented or record-only."
        )
    else:
        why = (
            f"Choose `{chosen_name}` because it preserves both execution continuity and decision proof; "
            f"{substitute_to_beat} is weaker because one side of the business truth remains thin."
        )
    draft_substitute_types = draft.get("substitute_pressure_types", [])
    substitute_types = draft_substitute_types if isinstance(draft_substitute_types, list) and draft_substitute_types else classify_substitute_pressure_types(substitutes, topology_archetype)
    proof_phrase = proof_target or "review-bound proof target"
    business_argument = _compact_truth_text(draft.get("argument_narrative")) or (
        f"Why this product deserves to exist: {chosen_name} is worth building now because {chosen_pain}. "
        f"It must beat {substitute_to_beat} ({', '.join(substitute_types)}) by turning the source-defined work into "
        f"{proof_phrase}, so the {continuation_owner} can decide whether to continue, revise, or pause instead of only reading a thinner substitute."
        if decision_pressure
        else f"Why this product deserves to exist: {chosen_name} is worth building now because {chosen_pain}. "
        f"It must beat {substitute_to_beat} ({', '.join(substitute_types)}) by preserving role handoff, exception handling, and closure proof instead of leaving a record-only or fragmented operating chain."
    )
    thesis = {
        "artifact_type": "chosen_business_thesis",
        "truth_state": "source-grounded-after-arena",
        "derived_from": "commercial_argument_draft" if draft else "business_exploration_arena",
        "chosen_thesis": chosen_name,
        "business_argument": business_argument,
        "why_this_not_alternatives": why,
        "rejected_alternatives": rejected_names,
        "current_state_substitute_to_beat": substitute_to_beat,
        "substitute_pressure_types": substitute_types,
        "buyer_user_operator_value": f"{chosen_value} Primary pressure: {chosen_pain}",
        "proof_target": proof_target,
        "review_bound_truth": (
            decision_trigger
            or "Keep unverified economics, exact attribution, adoption threshold, and operating completeness review-bound until evidence exists."
        ),
        "product_boundary_implication": chosen_boundary,
        "reality_density_focus": primary_reality_focus,
    }
    thesis["quality_gate"] = thesis_quality_gate(thesis, substitute_types)
    return thesis


def build_business_proof_track_from_chosen_thesis(
    base_track: dict[str, Any],
    chosen_business_thesis: dict[str, Any],
) -> dict[str, Any]:
    """Keep Business Proof Track as a derived view of the selected thesis."""
    track = dict(base_track)
    if not chosen_business_thesis:
        return track
    substitute = _compact_truth_text(chosen_business_thesis.get("current_state_substitute_to_beat"))
    proof_target = _compact_truth_text(chosen_business_thesis.get("proof_target"))
    review_bound = _compact_truth_text(chosen_business_thesis.get("review_bound_truth"))
    why = _compact_truth_text(chosen_business_thesis.get("why_this_not_alternatives"))
    if substitute:
        track["substitute_pressure"] = unique_preserve_order([substitute, *list(track.get("substitute_pressure", []))])
    if proof_target:
        track["proof_artifact"] = proof_target
    if review_bound:
        track["continuation_decision"] = review_bound
    if why:
        track["proof_questions"] = f"{track.get('proof_questions', '')}; selected thesis pressure: {why}".strip("; ")
    track["derived_from"] = "chosen_business_thesis"
    return track

def build_business_exploration_arena(
    *,
    topology_archetype: str,
    domain_posture: str,
    primary_segment: str,
    roles: list[str],
    objectives: list[str],
    pressure_signals: list[str],
    business_value_signals: list[str],
    commercial_decision_signals: list[str],
    user_experience_signals: list[str],
    workflow_backbone: list[str],
    object_chain: list[str],
    chosen_product_world: str,
    rejected_product_worlds: list[str],
    proof_artifact: str,
    continuation_owner: str,
    spend_at_risk: str,
    decision_trigger: str,
) -> dict[str, Any]:
    """Build the pre-assembly business reasoning arena.

    This surface is intentionally earlier than truth packs: it exposes competing
    business interpretations before workflow assembly compresses them.
    """
    decision_heavy = topology_archetype == "decision-centric" or "decision" in topology_archetype
    operational_heavy = topology_archetype == "execution-centric" or domain_posture == "operational-service"
    workflow_surface = _human_join_truth_labels(workflow_backbone[:4], "the source-defined mainline")
    object_surface = _human_join_truth_labels(object_chain[:4], "the source-defined business objects")
    pressure = _truth_signal_phrase(
        unique_preserve_order([*pressure_signals, *business_value_signals, *user_experience_signals]),
        "the source-defined business pressure",
    )
    commercial_pressure = _truth_signal_phrase(
        commercial_decision_signals,
        spend_at_risk or "review-bound continuation economics",
    )
    candidate_target = continuation_owner if decision_heavy else primary_segment
    candidates: list[dict[str, str]] = [
        {
            "candidate_id": "BT-01",
            "thesis_name": chosen_product_world,
            "target_user_or_buyer": candidate_target,
            "primary_pain": pressure,
            "value_mechanism": (
                f"Preserve {workflow_surface} and {object_surface} so the next action and proof surface stay connected."
            ),
            "likely_first_product_boundary": workflow_surface,
            "proof_question": (
                "What evidence is enough for continue / revise / pause before perfect proof exists?"
                if decision_heavy
                else "Which role-owned handoff, blocked state, or closure record proves the service loop is real?"
            ),
        }
    ]
    for idx, rejected in enumerate(rejected_product_worlds[:3], start=2):
        candidates.append(
            {
                "candidate_id": f"BT-{idx:02d}",
                "thesis_name": rejected,
                "target_user_or_buyer": primary_segment,
                "primary_pain": pressure,
                "value_mechanism": "Lower implementation scope, but weaker proof of action continuity or business decision leverage.",
                "likely_first_product_boundary": workflow_surface,
                "proof_question": "What business truth would this thinner alternative fail to prove?",
            }
        )
    substitute_defaults = (
        ["dashboard-only visibility layer", "reporting-only overlay", "manual advisory without guided follow-through"]
        if decision_heavy
        else ["isolated workflow fragments", "record-only system without action continuity", "reporting-only overlay"]
    )
    substitutes = unique_preserve_order([*rejected_product_worlds, *substitute_defaults])[:5]
    primary_reality_focus = (
        "decision loop: signal -> action -> evidence -> continue / revise / pause"
        if decision_heavy and not operational_heavy
        else "service operating chain: intake -> handoff -> exception handling -> closure proof"
        if operational_heavy and not decision_heavy
        else "hybrid reality: service execution continuity plus economic decision proof"
    )
    return {
        "artifact_type": "business_exploration_arena",
        "truth_state": "source-grounded-pre-assembly",
        "topology_archetype": topology_archetype,
        "business_thesis_candidates": candidates,
        "substitute_and_current_state_map": {
            "substitutes": substitutes,
            "current_state_pressure": pressure,
            "minimum_proof_to_beat_substitutes": (
                "show why the chosen path changes a continuation decision, not only a report view"
                if decision_heavy
                else "show why the chosen path reduces real handoff loss, blocked work, or closure ambiguity"
            ),
        },
        "buyer_value_proof_map": {
            "primary_user": primary_segment,
            "continuation_or_approval_owner": continuation_owner,
            "operator_roles": unique_preserve_order([primary_segment, *roles])[:5],
            "evidence_that_changes_decision": proof_artifact,
            "spend_or_commitment_at_risk": commercial_pressure,
            "continue_revise_pause_trigger": decision_trigger,
        },
        "reality_density_map": {
            "primary_reality_focus": primary_reality_focus,
            "workflow_backbone": workflow_backbone,
            "object_chain": object_chain,
            "ordinary_baseline_probe": (
                "Do real decision owners have enough directional proof and substitute comparison to keep investing?"
                if decision_heavy
                else "Do real operators have enough state, exception, and role-handoff detail to avoid demo-thin execution?"
            ),
        },
        "arena_exit_questions": [
            "Which thesis creates the strongest reusable business value?",
            "Which substitute would a real buyer or operator choose instead?",
            "What real-world detail would make the product feel non-demo?",
            "What proof must Phase-2 preserve architecturally?",
        ],
    }

def compile_business_world_truth_spine(context: dict[str, Any]) -> dict[str, Any]:
    product_source_direct_driver = (
        context.get("product_source_direct_driver")
        if isinstance(context.get("product_source_direct_driver"), dict)
        else {}
    )
    domain_posture = str(context.get("domain_posture", "")).strip() or "generic-workflow"
    primary_segment = _compact_truth_text(context.get("primary_segment")) or "primary operator"
    roles = _non_empty_truth_values(list(context.get("roles", [])))
    alternative_segments = _non_empty_truth_values(list(context.get("alternative_segments", [])))
    objectives = _non_empty_truth_values(list(context.get("objectives", [])))
    constraints = _non_empty_truth_values(list(context.get("constraints", [])))
    nfrs = _non_empty_truth_values(list(context.get("nfrs", [])))
    out_of_scope = _non_empty_truth_values(list(context.get("out_of_scope", [])))
    business_value_signals = _non_empty_truth_values(list(context.get("business_value_signals", [])))
    pressure_signals = _non_empty_truth_values(list(context.get("pressure_signals", [])))
    commercial_decision_signals = _non_empty_truth_values(list(context.get("commercial_decision_signals", [])))
    user_experience_signals = _non_empty_truth_values(list(context.get("user_experience_signals", [])))

    module_rows = [row for row in context.get("modules", []) if isinstance(row, dict)]
    object_rows = [row for row in context.get("objects", []) if isinstance(row, dict)]
    flow_rows = [row for row in context.get("flows", []) if isinstance(row, dict)]

    module_names = _non_empty_truth_values([row.get("module", "") for row in module_rows])
    flow_names = _non_empty_truth_values([row.get("name", "") for row in flow_rows])
    object_names = unique_preserve_order(
        _non_empty_truth_values(
            [
                row.get("Object", "") or row.get("object", "") or row.get("Owner Module", "")
                for row in object_rows
            ]
        )
    )
    full_flow_summary = (
        _compact_truth_text(context.get("flow_summary"))
        or " -> ".join(module_names[:6])
        or " -> ".join(flow_names[:3])
        or "source-defined workflow"
    )
    flow_chain_labels = module_names or flow_names or [part.strip() for part in re.split(r"\s*(?:->|→)\s*", full_flow_summary) if part.strip()]
    flow_summary = _condense_chain_labels(flow_chain_labels)
    workflow_surface = _human_join_truth_labels(flow_chain_labels[:3], "the source-defined mainline")
    entry_anchor = _select_boundary_anchor(
        module_names[:2],
        object_names[:2],
        "source-defined entry context",
    )
    exit_anchor = _select_boundary_anchor(
        list(reversed(module_names[-2:])),
        list(reversed(object_names[-2:])),
        "source-defined business outcome",
    )
    chosen_object_anchor = ", ".join(f"`{name}`" for name in object_names[:4]) if object_names else "`source-defined business object`"
    curated_business_signals = _curate_truth_signals(
        business_value_signals,
        fallback=[entry_anchor, exit_anchor],
    )
    curated_commercial_signals = _curate_commercial_truth(commercial_decision_signals)
    curated_experience_signals = _curate_truth_signals(
        user_experience_signals,
        fallback=[primary_segment, entry_anchor, exit_anchor],
    )
    objective_phrase = _select_objective_phrase(objectives, flow_summary)
    business_pressure = _select_pressure_phrase(pressure_signals, flow_summary, "")
    if not business_pressure:
        business_pressure = _select_pressure_phrase(
            [*business_value_signals, *curated_business_signals],
            flow_summary,
            "manual reconstruction, weak actionability, and lower decision confidence",
        )
    user_experience_pressure = _select_pressure_phrase(
        [*user_experience_signals, *curated_experience_signals],
        flow_summary,
        "waiting, handoff friction, and manual reconstruction",
    )
    if not TRUTH_DIRECT_FAILURE_PATTERN.search(user_experience_pressure):
        user_experience_pressure = "waiting, handoff friction, and manual reconstruction"
    primary_value_statement = _select_value_phrase(
        [objective_phrase, *business_value_signals, *user_experience_signals],
        flow_summary,
        objective_phrase,
    )
    secondary_value_statement = _select_value_phrase(
        [*business_value_signals, *commercial_decision_signals, *user_experience_signals],
        flow_summary,
        "",
        exclude={primary_value_statement},
    )
    commercial_value_statement = _select_commercial_phrase(
        [*curated_commercial_signals, *business_value_signals],
        flow_summary,
        "",
    )
    topology_profile = infer_topology_profile(
        {
            "domain_posture": domain_posture,
            "roles": roles,
            "objectives": objectives,
            "modules": module_rows,
            "objects": object_rows,
            "flows": flow_rows,
            "constraints": constraints,
            "nfrs": nfrs,
            "business_value_signals": business_value_signals,
            "pressure_signals": pressure_signals,
            "commercial_decision_signals": commercial_decision_signals,
            "user_experience_signals": user_experience_signals,
        }
    )
    topology_archetype = str(topology_profile.get("topology_archetype", "hybrid")).strip() or "hybrid"
    primary_depth_axes = [
        str(item).strip()
        for item in topology_profile.get("primary_depth_axes", [])
        if str(item).strip()
    ]
    secondary_depth_axes = [
        str(item).strip()
        for item in topology_profile.get("secondary_depth_axes", [])
        if str(item).strip()
    ]
    ordinary_real_world_baseline_definition = str(
        topology_profile.get("ordinary_real_world_baseline_definition", "")
    ).strip()
    misfit_risk_if_wrong = str(topology_profile.get("misfit_risk_if_wrong", "")).strip()
    topology_rationale = str(topology_profile.get("topology_rationale", "")).strip()
    structure_implications = str(topology_profile.get("structure_implications", "")).strip()
    reclassification_trigger = str(topology_profile.get("reclassification_trigger", "")).strip()
    continuation_owner = _select_truth_continuation_owner(primary_segment, roles)
    proof_artifact = _proof_artifact_phrase(exit_anchor, object_names)
    object_surface = _human_join_truth_labels(object_names[:4], "the source-defined business objects")

    has_commercial_truth = bool(curated_commercial_signals)
    if has_commercial_truth:
        spend_at_risk = _truth_signal_phrase(
            curated_commercial_signals,
            "continued operating commitment and review-bound budget judgment",
        )
        decision_trigger = (
            f"`{continuation_owner}` 只有在看完 {proof_artifact}，并能围绕 {spend_at_risk} 做出判断时，"
            "才会进入继续 / 调整 / 暂停。"
        )
        buyer_truth_state = "source-grounded-but-review-bound"
        current_truth_state = (
            "当前已经看到继续投入压力，但真实 buyer / budget 确认仍保持 review-bound，需等待外部验证。"
        )
        missing_evidence_to_unlock = (
            "真实 buyer 或 budget owner 的反馈、报价或继续投入证据，以及这条主线值得进入下一轮投入的现场证明。"
        )
    else:
        spend_at_risk = (
            "review-bound / missing evidence: direct spend-at-risk truth is not explicit in the source; "
            "do not infer package, budget, or continuation economics yet."
        )
        decision_trigger = (
            f"review-bound / missing evidence: keep the continuation decision explicit after reviewing {proof_artifact}; "
            "the source does not yet prove the real spend threshold or commitment owner."
        )
        buyer_truth_state = "review-bound / missing evidence"
        current_truth_state = (
            "review-bound / missing evidence: the source defines the operating chain, but not yet a validated buyer/budget owner or spend threshold"
        )
        missing_evidence_to_unlock = (
            "stakeholder evidence showing who funds or authorizes the next commitment, what spend is really at risk, and what proof is sufficient to continue"
        )

    domain_type = (
        "native-digital / market-mediated"
        if domain_posture == "growth-observation"
        else "physical/operational-rich"
        if domain_posture == "operational-service"
        else "mixed / undetermined"
    )
    if topology_archetype == "decision-centric" and domain_posture == "growth-observation":
        chosen_product_world = "visibility intelligence + guided optimization"
        rejected_product_worlds = [
            "dashboard-only visibility layer",
            "reporting-only review surface",
            "manual advisory without guided follow-through",
        ]
    elif topology_archetype == "execution-centric" and domain_posture == "operational-service":
        chosen_product_world = "decision-ready service operations system"
        rejected_product_worlds = [
            "isolated workflow fragments",
            "reporting-only overlay",
            "record-only system without action continuity",
        ]
    elif topology_archetype == "decision-centric":
        chosen_product_world = "decision-support system with guided action"
        rejected_product_worlds = [
            "reporting-only overlay",
            "dashboard-only visibility layer",
            "manual advisory without guided follow-through",
        ]
    elif topology_archetype == "execution-centric":
        chosen_product_world = "workflow-backed operating system"
        rejected_product_worlds = [
            "isolated workflow fragments",
            "record-only system without action continuity",
            "reporting-only overlay",
        ]
    else:
        chosen_product_world = "decision-ready operating system"
        rejected_product_worlds = [
            "isolated workflow fragments",
            "reporting-only overlay",
            "manual advisory without guided follow-through",
        ]
    business_proof_track = build_business_proof_track(
        topology_archetype=topology_archetype,
        domain_posture=domain_posture,
        primary_depth_axes=primary_depth_axes,
        secondary_depth_axes=secondary_depth_axes,
        chosen_product_world=chosen_product_world,
        rejected_product_worlds=rejected_product_worlds,
        proof_artifact=proof_artifact,
        continuation_owner=continuation_owner,
        spend_at_risk=spend_at_risk,
        decision_trigger=decision_trigger,
    )
    arena_workflow_backbone = unique_preserve_order(flow_chain_labels[:6] or module_names[:6] or flow_names[:6])
    arena_object_chain = unique_preserve_order(object_names[:6] or arena_workflow_backbone)
    business_exploration_arena = build_business_exploration_arena(
        topology_archetype=topology_archetype,
        domain_posture=domain_posture,
        primary_segment=primary_segment,
        roles=roles,
        objectives=objectives,
        pressure_signals=pressure_signals,
        business_value_signals=business_value_signals,
        commercial_decision_signals=curated_commercial_signals,
        user_experience_signals=user_experience_signals,
        workflow_backbone=arena_workflow_backbone,
        object_chain=arena_object_chain,
        chosen_product_world=chosen_product_world,
        rejected_product_worlds=rejected_product_worlds,
        proof_artifact=proof_artifact,
        continuation_owner=continuation_owner,
        spend_at_risk=spend_at_risk,
        decision_trigger=decision_trigger,
    )
    commercial_argument_draft = build_commercial_argument_draft(business_exploration_arena)
    chosen_business_thesis = choose_business_thesis(
        business_exploration_arena,
        commercial_argument_draft=commercial_argument_draft,
    )
    business_proof_track = build_business_proof_track_from_chosen_thesis(
        business_proof_track,
        chosen_business_thesis,
    )

    core_thesis_mainline = (
        f"把 {workflow_surface} 收成同一条可判定主线，"
        f"让 `{primary_segment}` 能把当前信号推进成下一步动作，"
        f"并让 `{continuation_owner}` 能围绕 {proof_artifact} 判断下一轮是否继续投入，"
        "而不是只看到事后报告。"
    )
    if objective_phrase and objective_phrase != "the mainline work becomes routine instead of manually reconstructed":
        core_thesis = f"{objective_phrase}. {core_thesis_mainline}"
    else:
        core_thesis = core_thesis_mainline
    why_now_tail = (
        f"`{continuation_owner}` 仍无法在同一 review 面判断下一轮是否继续投入。"
        if has_commercial_truth
        else "关键判断仍停留在 review-bound。"
    )
    why_now = (
        f"当前已经确认的压力是：{business_pressure}。"
        f"只要 {workflow_surface} 仍然断裂，`{primary_segment}` 就仍要承受 {user_experience_pressure}，"
        f"{why_now_tail}"
    )
    primary_alternatives = [chosen_product_world, *rejected_product_worlds]
    why_this_not_that = (
        f"选择 {chosen_product_world}，因为 `{entry_anchor}`、`{exit_anchor}` 和 {object_surface} "
        "必须在下一步动作与 review 判断中保持连续可见；"
        "更薄的替代路径会把上下文、证据和下一动作重新拆散。"
    )
    value_lead_clauses = unique_preserve_order(
        [
            clause
            for clause in [
                primary_value_statement,
                secondary_value_statement,
                commercial_value_statement,
            ]
            if clause
        ]
    )[:2]
    value_lead = _join_truth_clauses(value_lead_clauses)
    if value_lead:
        value_mechanism = (
            f"{value_lead} 系统通过把 `{entry_anchor}`、`{exit_anchor}` 和 {object_surface} "
            f"保持在同一条连续主线上，让 `{primary_segment}` 与 `{continuation_owner}` "
            "不必再在分散记录之间重建上下文。"
        )
    else:
        value_mechanism = (
            f"把 `{entry_anchor}`、`{exit_anchor}` 和 {object_surface} 放在同一条可追踪主线上，"
            f"让 `{primary_segment}` 能继续推进工作，"
            f"并让 `{continuation_owner}` 能在同一证据面做出下一轮判断。"
        )
    protected_business_nouns = unique_preserve_order(
        [
            primary_segment,
            *roles[:4],
            *alternative_segments[:3],
            *module_names[:6],
            *object_names[:6],
            *flow_names[:3],
            *constraints[:2],
            *nfrs[:2],
            *out_of_scope[:2],
        ]
    )
    operating_baseline_statement = (
        f"The ordinary real operating baseline is `{domain_type}` under `{topology_archetype}`: "
        f"{ordinary_real_world_baseline_definition or f'`{primary_segment}` works across {workflow_surface} and absorbs {user_experience_pressure} when the chain breaks.'}"
    )
    product_world_decision_basis = (
        "Choose the product world that preserves the topology-matched mainline, keeps proof attached to the next action, "
        "and lets the continuation owner make a real continue / revise / pause judgment."
    )
    state_handoff_anchors = unique_preserve_order(
        [
            entry_anchor,
            exit_anchor,
            "review decision ready",
        ]
    )
    object_chain = unique_preserve_order(object_names[:6] or flow_chain_labels[:6] or [entry_anchor, exit_anchor])
    workflow_backbone = unique_preserve_order(flow_chain_labels[:6] or object_chain)
    business_release_truth_pack = {
        "truth_state": "source-grounded",
        "domain_type": domain_type,
        "topology_archetype": topology_archetype,
        "primary_depth_axes": primary_depth_axes,
        "secondary_depth_axes": secondary_depth_axes,
        "chosen_product_world": chosen_product_world,
        "category_framing": chosen_product_world,
        "core_thesis": core_thesis,
        "why_now": why_now,
        "why_this_not_that": why_this_not_that,
        "value_mechanism": value_mechanism,
        "proof_artifact_for_continue": proof_artifact,
        "spend_at_risk": spend_at_risk,
        "decision_trigger": decision_trigger,
        "pain_holder": primary_segment,
        "continuation_owner": continuation_owner,
        "protected_business_nouns": protected_business_nouns[:10],
    }
    planning_control_truth_pack = {
        "truth_state": "source-grounded",
        "domain_posture": domain_posture,
        "domain_type": domain_type,
        "topology_archetype": topology_archetype,
        "primary_depth_axes": primary_depth_axes,
        "secondary_depth_axes": secondary_depth_axes,
        "workflow_backbone": workflow_backbone,
        "object_chain": object_chain,
        "state_handoff_anchors": state_handoff_anchors,
        "proof_artifact_for_continue": proof_artifact,
        "continuation_owner": continuation_owner,
        "protected_business_nouns": protected_business_nouns[:10],
    }
    product_source_direct_driver_summary: dict[str, Any] = {}
    if product_source_direct_driver:
        source_truth_admission = product_source_direct_driver.get("source_truth_admission", {})
        product_judgment = product_source_direct_driver.get("product_judgment", {})
        commercial_judgment = product_source_direct_driver.get("commercial_judgment", {})
        business_feasibility = product_source_direct_driver.get("business_feasibility", {})
        mvp_wedge = product_source_direct_driver.get("mvp_wedge", {})
        acceptance_meaning = product_source_direct_driver.get("acceptance_meaning", {})
        open_truth_gap_routing = product_source_direct_driver.get("open_truth_gap_routing", {})
        business_completeness_driver = product_source_direct_driver.get("business_completeness_driver", {})
        business_judgment_synthesis = product_source_direct_driver.get("business_judgment_synthesis", {})
        business_judgment_transformation = product_source_direct_driver.get("business_judgment_transformation", {})
        semantic_authoring_spine = product_source_direct_driver.get("semantic_authoring_spine", {})
        semantic_authoring_summary = product_source_direct_driver.get("semantic_authoring_summary", {})
        forbidden_assumptions = product_source_direct_driver.get("forbidden_downstream_assumptions", [])
        value_targets = product_source_direct_driver.get("value_deepening_targets", [])
        product_source_direct_driver_summary = {
            "driver_id": product_source_direct_driver.get("driver_id", "p1-product-source-direct-driver.v1"),
            "source_truth_admission": source_truth_admission,
            "product_judgment": product_judgment,
            "commercial_judgment": commercial_judgment,
            "business_feasibility": business_feasibility,
            "mvp_wedge": mvp_wedge,
            "acceptance_meaning": acceptance_meaning,
            "open_truth_gap_routing": open_truth_gap_routing,
            "business_completeness_driver": business_completeness_driver,
            "business_judgment_synthesis": business_judgment_synthesis,
            "business_judgment_transformation": business_judgment_transformation,
            "semantic_authoring_spine": semantic_authoring_spine,
            "semantic_authoring_summary": semantic_authoring_summary,
            "forbidden_downstream_assumptions": forbidden_assumptions,
            "value_deepening_targets": value_targets,
        }
        business_release_truth_pack.update(
            {
                "source_truth_admission": source_truth_admission,
                "product_judgment": product_judgment,
                "commercial_judgment": commercial_judgment,
                "business_feasibility": business_feasibility,
                "mvp_wedge": mvp_wedge,
                "acceptance_meaning": acceptance_meaning,
                "open_truth_gap_routing": open_truth_gap_routing,
                "business_completeness_driver": business_completeness_driver,
                "business_judgment_synthesis": business_judgment_synthesis,
                "business_judgment_transformation": business_judgment_transformation,
                "semantic_authoring_spine": semantic_authoring_spine,
                "semantic_authoring_summary": semantic_authoring_summary,
                "forbidden_downstream_assumptions": forbidden_assumptions,
            }
        )
        planning_control_truth_pack.update(
            {
                "source_truth_admission": source_truth_admission,
                "business_completeness_driver": business_completeness_driver,
                "semantic_authoring_summary": semantic_authoring_summary,
                "forbidden_downstream_assumptions": forbidden_assumptions,
                "open_truth_gap_routing": open_truth_gap_routing,
            }
        )

    payload: dict[str, Any] = {
        "artifact_type": "business_world_model",
        "schema_version": "v0.1",
        "status": "provisional",
        "domain_posture": domain_posture,
        "topology_profile": {
            "topology_archetype": topology_archetype,
            "topology_rationale": topology_rationale,
            "primary_depth_axes": primary_depth_axes,
            "secondary_depth_axes": secondary_depth_axes,
            "ordinary_real_world_baseline_definition": ordinary_real_world_baseline_definition,
            "misfit_risk_if_wrong": misfit_risk_if_wrong,
            "structure_implications": structure_implications,
            "reclassification_trigger": reclassification_trigger,
        },
        "topology_archetype": topology_archetype,
        "primary_depth_axes": primary_depth_axes,
        "secondary_depth_axes": secondary_depth_axes,
        "misfit_risk_if_wrong": misfit_risk_if_wrong,
        "operating_baseline_model": {
            "artifact_type": "operating_baseline_model",
            "truth_state": "source-grounded",
            "domain_type": domain_type,
            "domain_posture": domain_posture,
            "topology_archetype": topology_archetype,
            "primary_depth_axes": primary_depth_axes,
            "secondary_depth_axes": secondary_depth_axes,
            "baseline_statement": operating_baseline_statement,
            "ordinary_real_world_baseline_definition": ordinary_real_world_baseline_definition,
            "workflow_backbone": workflow_backbone,
            "object_chain": object_chain,
        },
        "product_world_option_set": {
            "artifact_type": "product_world_option_set",
            "truth_state": "source-grounded",
            "domain_type": domain_type,
            "topology_archetype": topology_archetype,
            "chosen": chosen_product_world,
            "options": [chosen_product_world, *rejected_product_worlds],
            "selection_rule": product_world_decision_basis,
        },
        "business_exploration_arena": business_exploration_arena,
        "commercial_argument_draft": commercial_argument_draft,
        "chosen_business_thesis": chosen_business_thesis,
        "product_source_direct_driver_summary": product_source_direct_driver_summary,
        "product_world_decision": {
            "artifact_type": "product_world_decision",
            "truth_state": "source-grounded",
            "domain_type": domain_type,
            "topology_archetype": topology_archetype,
            "chosen_product_world": chosen_product_world,
            "category_framing": chosen_product_world,
            "decision_basis": product_world_decision_basis,
            "rejected_worlds": rejected_product_worlds,
        },
        "business_release_truth_pack": business_release_truth_pack,
        "planning_control_truth_pack": planning_control_truth_pack,
        "business_proof_track": business_proof_track,
        "core_thesis": _truth_slot(core_thesis, truth_state="source-grounded", source_signals=curated_business_signals[:3]),
        "why_now": _truth_slot(
            why_now,
            truth_state="source-grounded",
            source_signals=[*curated_business_signals[:2], *curated_experience_signals[:1]],
        ),
        "primary_alternative_set": {
            "truth_state": "source-grounded",
            "chosen": primary_alternatives[0],
            "options": primary_alternatives,
        },
        "why_this_not_that": _truth_slot(
            why_this_not_that,
            truth_state="source-grounded",
            source_signals=[entry_anchor, exit_anchor, *flow_chain_labels[:1], *object_names[:2]],
        ),
        "value_mechanism": _truth_slot(
            value_mechanism,
            truth_state="source-grounded",
            source_signals=[*curated_business_signals[:2], *curated_experience_signals[:1]],
        ),
        "buyer_budget_chain": {
            "truth_state": buyer_truth_state,
            "pain_holder": primary_segment,
            "continuation_owner": continuation_owner,
            "spend_at_risk": spend_at_risk,
            "proof_artifact_for_continue": proof_artifact,
            "decision_trigger": decision_trigger,
            "current_truth_state": current_truth_state,
            "missing_evidence_to_unlock": missing_evidence_to_unlock,
        },
        "spend_at_risk": _truth_slot(
            spend_at_risk,
            truth_state=buyer_truth_state,
            source_signals=curated_commercial_signals[:3],
        ),
        "proof_artifact_for_continue": _truth_slot(
            proof_artifact,
            truth_state="source-grounded",
            source_signals=[exit_anchor, *object_names[:2]],
        ),
        "decision_trigger": _truth_slot(
            decision_trigger,
            truth_state=buyer_truth_state,
            source_signals=curated_commercial_signals[:2],
        ),
        "protected_business_nouns": {
            "truth_state": "source-grounded",
            "values": protected_business_nouns,
        },
    }
    return sanitize_domain_default_truth(
        payload,
        context={
            "domain_posture": domain_posture,
            "primary_segment": primary_segment,
            "role_labels": roles,
            "supporting_role_label": roles[1] if len(roles) > 1 else "",
            "decision_role_label": roles[-1] if roles else primary_segment,
        },
    )


def compile_operator_text(operator_keys: list[str], context: dict[str, Any] | None = None) -> str:
    operators = unique_preserve_order([OPERATOR_LIBRARY[key] for key in operator_keys])
    return str(sanitize_domain_default_truth("; then ".join(operators), context=context))


def compile_stage_reasoning_units(
    stage_key: str,
    available_methods: list[str],
    context: dict[str, Any],
    material_grounding: list[str] | None = None,
) -> list[dict[str, Any]]:
    blueprints = STAGE_REASONING_BLUEPRINTS[stage_key]
    units: list[dict[str, Any]] = []
    for blueprint in blueprints:
        unit: dict[str, Any] = {}
        for key, value in blueprint.items():
            if key in {"method_hints", "operator_keys"}:
                continue
            unit[key] = render_template_value(value, context)
        resolved_methods = resolve_method_assets(available_methods, blueprint["method_hints"])
        unit["method_family"] = " + ".join(resolved_methods)
        unit["method_assets"] = list(resolved_methods)
        unit["reasoning_operator"] = compile_operator_text(blueprint["operator_keys"], context=context)
        if material_grounding:
            unit["material_grounding"] = list(material_grounding)
        unit["_resolved_methods"] = resolved_methods
        unit["_resolved_operator_keys"] = list(blueprint["operator_keys"])
        units.append(sanitize_domain_default_truth(unit, context=context))
    return units


def compile_maturity_confidence_ledger(
    blueprint_key: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    blueprints = MATURITY_CONFIDENCE_BLUEPRINTS[blueprint_key]
    return [sanitize_domain_default_truth(render_template_value(item, context), context=context) for item in blueprints]


def activated_method_families(units: list[dict[str, Any]]) -> list[str]:
    methods: list[str] = []
    for unit in units:
        explicit_assets = unit.get("method_assets", [])
        if isinstance(explicit_assets, list):
            methods.extend(str(item).strip() for item in explicit_assets if str(item).strip())
            continue
        resolved_methods = [str(item).strip() for item in unit.get("_resolved_methods", []) if str(item).strip()]
        if resolved_methods:
            methods.extend(resolved_methods)
            continue
        method_family = str(unit.get("method_family", "")).strip()
        if method_family:
            methods.extend(part.strip() for part in method_family.split(" + ") if part.strip())
    return unique_preserve_order(methods)


def activated_operator_texts(units: list[dict[str, Any]]) -> list[str]:
    keys: list[str] = []
    for unit in units:
        keys.extend(unit.get("_resolved_operator_keys", []))
    return unique_preserve_order([OPERATOR_LIBRARY[key] for key in keys])
