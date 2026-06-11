#!/usr/bin/env python3
"""
Phase-1 PRD section scoring gate.

This gate turns "looks deep enough" into a reproducible closing acceptance test.
Each critical PRD section is scored across five dimensions:
- completeness
- detail depth
- decision / trade-off clarity
- downstream usability
- uncertainty / boundary honesty

The closing bar is intentionally strict: every tracked section must reach the
configured threshold, not just the average score.
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
import sys
from dataclasses import dataclass
from pathlib import Path

from phase1.phase1_gate_authority import emit_compatibility_warning


@dataclass(frozen=True)
class PatternDef:
    label: str
    regex: str


@dataclass(frozen=True)
class SectionRule:
    name: str
    title_pattern: str
    required_subheadings: tuple[str, ...]
    min_nonempty_lines: int
    detail_patterns: tuple[PatternDef, ...]
    decision_patterns: tuple[PatternDef, ...]
    downstream_patterns: tuple[PatternDef, ...]
    honesty_patterns: tuple[PatternDef, ...]


def pattern(label: str, regex: str) -> PatternDef:
    return PatternDef(label=label, regex=regex)


SECTION_RULES: tuple[SectionRule, ...] = (
    SectionRule(
        name="Problem Statement",
        title_pattern=r"(?:2\.\s+)?Problem Statement",
        required_subheadings=(
            "Synthesized Problem Narrative",
            "Evidence Status",
            "Integrated Problem Evidence",
            "Source Signal Recompilation",
        ),
        min_nonempty_lines=28,
        detail_patterns=(
            pattern("final_problem_statement", r"final_problem_statement"),
            pattern("problem_mechanism", r"problem_mechanism"),
            pattern("problem_clusters", r"top_problem_clusters"),
            pattern("opportunity_clusters", r"top_opportunity_clusters"),
            pattern("segment_signals", r"segment signals:|客群信号"),
            pattern("capability_signals", r"capability signals:|能力信号"),
            pattern("metric_signals", r"metric signals:|指标信号"),
        ),
        decision_patterns=(
            pattern("mechanism_shift", r"problem_mechanism"),
            pattern(
                "operating_chain",
                r"primary object.*analysis cycle.*insight.*action.*review summary|signal.*action.*review|洞察.*动作.*复盘|经营链路|闭环|baseline.*insight.*action.*review|current-状态 snapshot.*recommendation.*review",
            ),
            pattern("state_visibility", r"当前状态可见性|state visibility|可见性|visibility|current-状态 snapshot"),
            pattern("not_dashboard", r"不是缺少一个监控页面|this is not|孤立报表页|孤立后台设置页|dashboard"),
        ),
        downstream_patterns=(
            pattern(
                "current_operating_visibility",
                r"当前可见性位置|current-状态 snapshot|可见性不可观测|current visibility position question|当前记录链路是否|operating visibility note|continuous visibility|连续可见",
            ),
            pattern(
                "gap_question",
                r"缺口在哪|gap|最大缺口|下一步关注点|优先级和投入方向难以稳定判断|哪些环节仍会让|handoff 中丢失|丢失关键上下文",
            ),
            pattern(
                "fragmented_tool_gap",
                r"竞品为何领先|竞品为什么领先|竞品差距|partial[_ -]?tool[_ -]?gap[_ -]?question|局部工具为何不足|fragmented point tools|why can fragmented .* tools not close|point tools may",
            ),
            pattern(
                "business_or_operating_change",
                r"业务方向变化|投入无法变成可解释决策|是否继续投入|资源节奏|优先级和投入方向|会如何变化|执行质量.*如何变化|异常处理.*如何变化|复盘判断.*如何变化|预算判断.*会如何变化|门店执行质量",
            ),
        ),
        honesty_patterns=(
            pattern("review_bound_inferred", r"review-bound\s*/\s*inferred|review-bound|inferred"),
            pattern("open_truths", r"付费意愿|recommendation trust|next-step guidance trust|指标稳定性|真实门店采纳摩擦|范围接受度|经营分析需求"),
            pattern("source_vs_inference", r"user-confirmed|review-bound"),
            pattern(
                "mechanism_breakage",
                r"搜索入口变化|入口变化|无法变成可解释决策|信号无法变成行动|行动无法变成复盘|上下文会在模块之间丢失|上下文会在环节之间丢失|重新回到人工补录|重新回到人工拼接|口头交接|问题需要被重编译成同一条信号 -> 行动 -> 复盘链路",
            ),
        ),
    ),
    SectionRule(
        name="Target Users & Key Roles",
        title_pattern=r"(?:3\.\s+)?Target Users & Key Roles",
        required_subheadings=(
            "Primary Boundary",
            "Secondary / Supporting Roles",
            "Out-of-scope Users",
            "Persona Boundary and Interaction Chain",
            "Persona / JTBD Matrix",
            "Persona Context Scenario and Key Paths",
            "Design Requirements Extraction",
        ),
        min_nonempty_lines=90,
        detail_patterns=(
            pattern("role_chain_table", r"\| role \| goal \| friction \| first-wave responsibility \|"),
            pattern(
                "jtbd_table",
                r"\| role \| context \| main job \| success signal \| failure consequence \||"
                r"\| 角色 .* 情境 .* 核心任务 .* success .* failure consequence .* \|",
            ),
            pattern("key_path_1", r"Key-path Scenario 1"),
            pattern("key_path_2", r"Key-path Scenario 2"),
            pattern("key_path_3", r"Key-path Scenario 3"),
            pattern("dr_01", r"DR-01"),
            pattern("dr_06", r"DR-06"),
        ),
        decision_patterns=(
            pattern("chosen_segment", r"chosen segment"),
            pattern("why_this_not_that", r"why this not that"),
            pattern("out_of_scope_users", r"Out-of-scope Users"),
            pattern("boundary_lock_reasoning", r"Reasoning Unit 1:\s+Primary Boundary Lock"),
            pattern("tradeoff", r"tradeoff_or_tension"),
        ),
        downstream_patterns=(
            pattern("primary_operator", r"primary operator|核心业务操作者|receptionist|veterinarian|clinic manager|execution operator|decision owner|governance reviewer|marketing owner|content operator|business owner"),
            pattern("execution_operator", r"content operator|execution operator|cashier|operator|veterinarian|marketing owner"),
            pattern("decision_owner", r"business owner|decision owner|clinic manager"),
            pattern("governance_role", r"IT/legal reviewer|governance reviewer"),
            pattern("implied_design_requirement", r"implied_design_requirement"),
            pattern("required_outcome", r"required outcome"),
        ),
        honesty_patterns=(
            pattern("anti_pattern", r"anti-pattern to avoid"),
            pattern("review_bound", r"review-bound"),
            pattern("remaining_unknown", r"remaining_unknown"),
            pattern("scope_boundary", r"Out-of-scope Users|out-of-scope"),
        ),
    ),
    SectionRule(
        name="Business Scenarios",
        title_pattern=r"(?:7\.\s+)?Business Scenarios",
        required_subheadings=(
            "Scenario Set Overview",
            "Scenario Decomposition",
            "Key Scenario Deep Analysis",
        ),
        min_nonempty_lines=40,
        detail_patterns=(
            pattern("scenario_a", r"Scenario A"),
            pattern("scenario_b", r"Scenario B"),
            pattern("scenario_c", r"Scenario C"),
            pattern("main_success_path", r"main success path"),
            pattern("exception_paths", r"key exception paths"),
            pattern("success_criteria", r"success criteria"),
            pattern("structure_implication", r"structure implication"),
        ),
        decision_patterns=(
            pattern("structure_implication", r"structure implication"),
            pattern("baseline_consequence", r"配置必须要求|baseline|business context 定义不清"),
            pattern("task_consequence", r"finding.*recommendation|发现项.*recommendation|建议.*任务|insight.*任务|action recommendation.*业务动作|无法转成任务"),
            pattern("review_consequence", r"review 页面必须保留趋势"),
        ),
        downstream_patterns=(
            pattern("preconditions", r"preconditions"),
            pattern("main_success_path", r"main success path"),
            pattern("exception_paths", r"key exception paths"),
            pattern("success_criteria", r"success criteria"),
            pattern("trigger", r"trigger"),
        ),
        honesty_patterns=(
            pattern("weak_consequence", r"scenario consequence if weak"),
            pattern("blocked_path", r"阻止进入 baseline|允许保存草稿"),
            pattern("review_uncertainty", r"观望|revisit|调整"),
            pattern("action_failure", r"退化为报告系统|不会稳定支持"),
        ),
    ),
    SectionRule(
        name="Requirements Structure",
        title_pattern=r"(?:8\.\s+)?Requirements Structure",
        required_subheadings=(
            "Goal",
            "Structure Choice",
            "Structure Alternatives Comparison",
            "Problem-to-Structure Mapping",
            "Backbone Activities (Business Process Decomposition Precursor)",
            "Business Process Identification",
            "Workflow / State Detail",
            "Constraint Stress-Test",
            "Priority Split",
            "Business Process Decomposition",
            "Exception and Failure Flows",
        ),
        min_nonempty_lines=180,
        detail_patterns=(
            pattern("workflow_steps", r"Step 1 初始化配置|Step 1|步骤\s*1"),
            pattern("actor_system_decomposition", r"actor/system decomposition"),
            pattern("tension_register", r"tension register"),
            pattern("p0_p1_p2", r"\bP0\b.*\bP1\b.*\bP2\b|\bP0\b|\bP1\b|\bP2\b"),
            pattern("mermaid_diagram", r"```mermaid"),
            pattern("business_process_table", r"\| activity \| primary actor \| trigger \| preconditions \| system behavior \| outputs \| postconditions \|"),
            pattern("exception_flows", r"Exception 1:|Exception 2:|Exception 3:|异常 1：|异常 2：|异常 3："),
            pattern("reasoning_units", r"Reasoning Unit 4:\s+Priority Cutline for First-Wave Structure"),
        ),
        decision_patterns=(
            pattern("chosen_structure", r"chosen_panorama_structure"),
            pattern("why_not_that", r"why_this_structure_not_that"),
            pattern(
                "candidate_verdict",
                r"\| candidate \| backbone shape \| strength \| failure risk \| verdict \||workflow-first|工作流优先",
            ),
            pattern("exclusion_logic", r"exclusion logic"),
            pattern("decision_endpoint", r"Reasoning Unit 3:\s+Review as Decision Endpoint"),
        ),
        downstream_patterns=(
            pattern("primary_owner", r"primary owner"),
            pattern("trigger_output", r"\| process type \| process name \| primary owner \| trigger \| output \| why it matters \||流程类型|process 名称"),
            pattern("system_behavior", r"system behavior"),
            pattern("postconditions", r"postconditions"),
            pattern("handling_strategy", r"handling strategy"),
            pattern("state_detail", r"state:\s*scope_ready|state:\s*baseline_ready|状态:\s*scope_ready|状态:\s*baseline_ready"),
        ),
        honesty_patterns=(
            pattern("constraints", r"business constraints|technical constraints|compliance/privacy constraints"),
            pattern("tensions", r"coverage vs focus|automation vs trust|attribution depth vs MVP speed"),
            pattern("review_bound", r"review-bound"),
            pattern("remaining_unknown", r"remaining_unknown"),
            pattern("exception_honesty", r"不得伪装成正向验证|blocked"),
        ),
    ),
    SectionRule(
        name="NFR / Quality Requirements",
        title_pattern=r"(?:9\.\s+)?NFR\s*/\s*Quality Requirements",
        required_subheadings=(
            "Top Quality Attributes",
            "NFR / Quality Requirements",
            "NFR Prioritization Reasoning",
            "Quality Scenario Matrix",
            "Metric Definition and Interpretation Register",
            "Module Responsibility Matrix",
        ),
        min_nonempty_lines=65,
        detail_patterns=(
            pattern("top_attributes", r"reliability|usability|security/data-control|maintainability"),
            pattern("prioritization_table", r"\| attribute \| why prioritized now \| reverse risk if weak \| affected scenario \| MVP consequence \|"),
            pattern("quality_scenario_matrix", r"\| attribute \| stimulus \| environment \| expected response \| measure \|"),
            pattern("metric_register", r"\| metric \| meaning \| first-wave use \| interpretation risk \| mitigation \|"),
            pattern("module_matrix", r"\| module \| responsibility \| input \| output \| architectural note \|"),
            pattern("stress_test", r"Specification Stress-Test"),
            pattern("reasoning_units", r"Reasoning Unit 4:\s+Workflow-First IA Direction"),
        ),
        decision_patterns=(
            pattern("why_prioritized", r"why prioritized now"),
            pattern("reverse_risk", r"reverse risk if weak"),
            pattern("deprioritized", r"deprioritized_attributes"),
            pattern("decision_effect", r"decision_effect"),
            pattern("alternatives_compared", r"alternatives_compared"),
        ),
        downstream_patterns=(
            pattern("stimulus_environment", r"stimulus|environment|expected response|measure"),
            pattern("responsibility_chain", r"responsibility|input|output|architectural note"),
            pattern("mitigation", r"mitigation"),
            pattern("recommendation_constraint", r"cannot silently auto-execute|manual confirmation|next_step_constraint"),
            pattern("review_consequence", r"MVP consequence"),
        ),
        honesty_patterns=(
            pattern("interpretation_risk", r"interpretation risk"),
            pattern("blind_spot", r"blind spot"),
            pattern("review_bound", r"review-bound"),
            pattern("remaining_unknown", r"remaining_unknown"),
        ),
    ),
    SectionRule(
        name="Domain Model",
        title_pattern=r"(?:10\.\s+)?Domain Model",
        required_subheadings=(
            "Domain Model Direction",
            "Deferred Attribution and Conversion Seam",
            "Conceptual ER Diagram",
            "Key Relationships and Data Characteristics",
            "Business Subsystem Boundaries",
            "Object-to-Workflow Mapping",
        ),
        min_nonempty_lines=80,
        detail_patterns=(
            pattern("core_entities", r"core entities"),
            pattern("attribution_seam", r"Deferred Capability Seam|Deferred Attribution and Conversion Seam|future seam entity/interface"),
            pattern("entity_catalog", r"entity catalog"),
            pattern("object_lifecycle", r"object lifecycle notes"),
            pattern("er_diagram", r"erDiagram"),
            pattern("subsystem_interfaces", r"subsystem_interfaces"),
            pattern("workflow_mapping", r"\| workflow step \| primary object \| secondary object \| downstream effect \||\| 工作流步骤 .* 主对象 .* 次对象 .* 下游影响 .* \|"),
        ),
        decision_patterns=(
            pattern("relationship_direction", r"relationship direction"),
            pattern("first_wave_decision", r"\| dimension \| first-wave decision \| rationale \|"),
            pattern("subsystem_boundaries", r"Scope & Governance|Review & Reporting|Business Subsystem Boundaries|module seam"),
            pattern("deferred_but_preserved", r"虽然 deferred|extension seam|避免 Phase-2 重写对象链|reserved for later integrations"),
            pattern("constraints", r"cannot跨 tenant|不能跨 tenant|constraints|account boundary|auth|audit|retention boundary"),
        ),
        downstream_patterns=(
            pattern("account_boundary", r"account boundary"),
            pattern("sampling_window", r"sampling window|data window|采样窗口|per-cycle analysis and review history"),
            pattern("task_fields", r"assignee,\s*(?:status|状态),\s*due cycle"),
            pattern("attribution_fields", r"source_reference|source_tag|stage_placeholder|funnel_stage|outcome_event|conversion_event|multi-entry|cross-device|extension_context|future seam field|extension fields"),
            pattern("interface_payloads", r"payload element|target_asset_id|owner_hint|blocked_reason|extension_context|input \| output \| architectural note|interface_payloads:\s*what:"),
            pattern("workflow_mapping", r"downstream effect"),
        ),
        honesty_patterns=(
            pattern("sensitivity", r"sensitivity"),
            pattern("not_realtime_hard", r"not realtime-hard|not realtime"),
            pattern("tenant_constraint", r"不能跨 tenant 混用|tenant-private|不能跨\s*租户|tenant\)-private|clinic-private|clinic account boundary|single-account business boundary"),
            pattern("no_exact_roi", r"粗粒度归因|coarse attribution|不能在 MVP 假装财务级证明已成立|不能冒充首版已完成能力|must not overstate"),
            pattern("volume_growth", r"highest growth object|最高增长对象|throughput variance|traffic spikes|long-tail exceptions|admin reporting needs still need evidence"),
        ),
    ),
    SectionRule(
        name="Information Architecture Direction",
        title_pattern=r"(?:11\.\s+)?Information Architecture Direction",
        required_subheadings=(
            "IA Direction Summary",
            "Information Architecture Direction",
            "IA Decision Alternatives Comparison",
            "IA Spec Matrix",
            "Integrated IA Evidence",
        ),
        min_nonempty_lines=48,
        detail_patterns=(
            pattern("navigation", r"navigation"),
            pattern("screen_spec_precursor", r"screen spec precursor"),
            pattern("screen_object_matrix", r"screen/object matrix"),
            pattern("ia_alternatives", r"\| alternative \| organizing axis \| strength \| failure risk \| verdict \|"),
            pattern("ia_spec_matrix", r"\| screen/module \| primary actor \| required information objects \| entry conditions \| exit actions \| downstream dependency \|"),
            pattern("integrated_evidence", r"Integrated IA Evidence"),
        ),
        decision_patterns=(
            pattern("workflow_first_chosen", r"workflow-first"),
            pattern("chosen_verdict", r"\|\s*workflow-first\s*\|.*\|\s*chosen\s*\|"),
            pattern("failure_risk", r"failure risk"),
            pattern("architecture_impact", r"architecture impact|IA impact"),
        ),
        downstream_patterns=(
            pattern("primary_actor", r"primary actor"),
            pattern("required_objects", r"required information objects"),
            pattern("entry_conditions", r"entry conditions"),
            pattern("exit_actions", r"exit actions"),
            pattern("dependency", r"downstream dependency"),
            pattern("navigation_surface_set", r"navigation:|screen/module consequence|source-defined primary surfaces|workflow-first"),
        ),
        honesty_patterns=(
            pattern("failure_risk", r"failure risk"),
            pattern("dependency_visibility", r"depends on"),
            pattern("object_traceability", r"object traceability|screen/object"),
            pattern("constraints", r"需要更强对象映射约束|must围绕|必须围绕|约束\s*\(constraints\)"),
        ),
    ),
    SectionRule(
        name="MVP Definition & Scope",
        title_pattern=r"(?:12\.\s+)?MVP Definition & Scope",
        required_subheadings=(
            "Slice Decision Context",
            "Slice Strategy",
            "Scope, Dependency Logic, and Cutline",
            "Source Feature Carryover Ledger",
            "Value Loop and Downstream Preservation Notes",
            "Operational Flow Specification",
            "State Machine and Transition Rules",
            "Acceptance Criteria",
        ),
        min_nonempty_lines=140,
        detail_patterns=(
            pattern("candidate_table", r"\| candidate \| what_is_in_first_slice \| user_value_speed \| evidence_confidence \| dependency_complexity \| validation_leverage \| risk_of_overreach \| verdict \|"),
            pattern("scope_boundaries", r"in-scope:|out-of-scope:|later slice|deferred seam|explicit out-of-scope|non-goals"),
            pattern("loop_definitions", r"complete_experience_loop|minimum_viable_experience_loop"),
            pattern("slice_lists", r"first_slice:|later_slices:|deferred_items:"),
            pattern("carryover_ledger", r"Source Feature Carryover Ledger|\| source feature detail \| classification \| preserved form in first-wave PRD \| why this classification \| downstream note \|"),
            pattern("carryover_classification", r"first-wave abstraction|later slice|deferred seam|explicit out-of-scope"),
            pattern("reasoning_units", r"Reasoning Unit 4:\s+Deferred Honesty and Assumption Carryover"),
            pattern("operational_flow", r"Operational Flow Specification"),
            pattern("state_machine", r"State Machine and Transition Rules"),
            pattern("acceptance_criteria", r"AC-01|Acceptance Criteria"),
        ),
        decision_patterns=(
            pattern("chosen_slice", r"chosen_slice_strategy"),
            pattern("why_this_slice_not_that", r"why_this_slice_not_that"),
            pattern("explicit_exclusion_rule", r"explicit_exclusion_rule"),
            pattern("dependency_first_chain", r"dependency_first_chain"),
            pattern("carryover_rule", r"source 中写到的详细能力不得静默消失|不得静默消失"),
            pattern("chosen_verdict", r"\|\s*workflow-loop-first\s*\|.*\|\s*chosen\s*\|"),
        ),
        downstream_patterns=(
            pattern("step_1_10", r"Step 1:|Step 10:|步骤 1|步骤 10"),
            pattern("transition_guards", r"transition guard"),
            pattern("task_state", r"created / accepted / executed / blocked"),
            pattern("acceptance_ac", r"AC-01|AC-12"),
            pattern("core_navigation", r"screen/module consequence|navigation:|module responsibility|source-defined primary surfaces"),
            pattern("feature_carryover", r"mobile push|UTM|auto publish|auto A/B|deferred seam|carryover ledger|explicit out-of-scope|extension seam"),
            pattern("execution_review_link", r"task-review linkage|Review 没有 Task 状态输入|Review 没有 work item 状态输入|work item-review linkage|closure and audit-ready review|terminal closure and audit review must stay linked"),
        ),
        honesty_patterns=(
            pattern("deferred_items", r"deferred_items"),
            pattern("non_goals", r"non-goals|out-of-scope"),
            pattern("review_bound", r"review-bound"),
            pattern("deferred_seam", r"deferred seam"),
            pattern("remaining_unknown", r"remaining_unknown"),
            pattern("anti_false_completeness", r"假 MVP|假完整感|false completeness"),
        ),
    ),
    SectionRule(
        name="User Stories, Use Cases, and Requirements",
        title_pattern=r"(?:14\.\s+)?User Stories,\s*Use Cases,\s*and Requirements",
        required_subheadings=(
            "Primary User Story",
            "Supporting Use Cases",
            "Requirement Translation",
            "Recommendation Payload Contract",
            "Extended Requirement Set",
            "Requirement Trace Matrix",
        ),
        min_nonempty_lines=78,
        detail_patterns=(
            pattern("primary_story", r"Primary User Story|作为核心业务操作者|作为 .*负责人|作为 .*操作者"),
            pattern("supporting_use_cases", r"Use Case 1|Use Case 4"),
            pattern(
                "requirement_translation",
                r"Requirement Translation(?: Registry)?|\| requirement_id \| epic_id \| story_or_use_case \| requirement_class \| requirement_statement \| why_this_class \|",
            ),
            pattern("payload_contract", r"Module Interface Payload Contract|Recommendation Payload Contract|\| payload element \| source capability detail preserved \| first-wave representation \| task/export implication \| certainty / note \|"),
            pattern("payload_details", r"structured fields|结构化字段|target_asset_id|priority|owner_hint|blocked_reason|extension_context"),
            pattern("extended_requirements", r"RQ-01|RQ-18"),
            pattern(
                "trace_matrix",
                r"Requirement Trace Matrix|\| (?:epic(?:_id)?|epic) \| (?:story_or_use_case|story/use case) \| (?:requirement_id|requirement) \| (?:(?:requirement_class|requirement class) \| )?(?:acceptance_criteria|acceptance criteria) \| (?:boundary_condition|boundary condition) \| (?:related_flow_step|related flow step) \|",
            ),
        ),
        decision_patterns=(
            pattern(
                "theme_structure",
                r"Requirement Translation(?: Registry)?|requirement_class|why_this_class",
            ),
            pattern("payload_vs_generic", r"不是 generic|泛化内容建议|不得退化成"),
            pattern("attribution_requirement", r"RQ-17|deferred extension|source reference|source tagging|multi-entry|cross-device|extension seam|seam 字段"),
            pattern("carryover_requirement", r"RQ-18|carryover ledger|first-wave abstraction|deferred seam"),
            pattern("boundary_requirement", r"review-bound truths|non-goals"),
        ),
        downstream_patterns=(
            pattern("task_export_fields", r"target_asset_id|priority|owner_hint|blocked_reason|导出为 task"),
            pattern("citation_and_faq", r"extension_context|structured fields|execution-semantic fields"),
            pattern("attribution_fields", r"source_reference|source_tag|platform|stage_placeholder|outcome_event|conversion event|multi-entry|cross-device|extension_context|deferred seam"),
            pattern("acceptance_mapping", r"AC-05|AC-13|AC-14|AC-15"),
            pattern("flow_mapping", r"flow_mapping:.*(?:canonical Flow|Flow \d+)|Step 5|Step 6|Step 9|Step 10"),
        ),
        honesty_patterns=(
            pattern("review_bound", r"review-bound"),
            pattern("no_exact_roi", r"不得把它们包装成已完成 ROI 证明|不承诺精确财务解释|粗粒度归因|不能伪装成首版已交付能力"),
            pattern("deferred_seam", r"deferred seam"),
            pattern("explicit_out_of_scope", r"explicit out-of-scope|out-of-scope"),
            pattern("clarification_path", r"return-for-clarification"),
        ),
    ),
    SectionRule(
        name="Validation Strategy & Current Conclusion",
        title_pattern=r"(?:13\.\s+)?Validation Strategy & Current Conclusion",
        required_subheadings=(
            "Validation Context",
            "Targets, Methods, and Thresholds",
            "Evidence State and Current Decision",
            "Delivery Readiness and Evidence Confidence",
            "Validation Flow and Convergence Readiness",
            "Review-Bound Carryover",
        ),
        min_nonempty_lines=110,
        detail_patterns=(
            pattern("targets", r"target_1:|target_5:"),
            pattern("assumption_table", r"\| target \| exact_assumption_tested \| what_changes_if_positive \| what_changes_if_negative \| primary dimension \|"),
            pattern("method_table", r"\| candidate method \| fit_to_target \| cost_and_speed \| evidence_quality \| why_not_chosen_or_chosen \|"),
            pattern("signal_thresholds", r"signal thresholds|signal_thresholds|信号 thresholds"),
            pattern("decision_and_revision", r"decision:\s*`?(Revise|Go|Blocked)`?|revision_consequences"),
            pattern("mermaid", r"```mermaid"),
            pattern("maturity_confidence", r"Delivery Readiness and Evidence Confidence|document_delivery_state|evidence_confidence_state"),
            pattern("reasoning_units", r"Reasoning Unit 4:\s+Decision State and Convergence Admission"),
        ),
        decision_patterns=(
            pattern("exact_assumption", r"exact_assumption_tested"),
            pattern("positive_change", r"what_changes_if_positive"),
            pattern("negative_change", r"what_changes_if_negative"),
            pattern("decision_state", r"decision:\s*`?(Revise|Go|Blocked)`?"),
            pattern("delivery_state", r"document_delivery_state"),
            pattern("evidence_confidence_state", r"evidence_confidence_state"),
            pattern("admission_state", r"ready-to-converge|convergence admission"),
        ),
        downstream_patterns=(
            pattern("chosen_method", r"chosen_method"),
            pattern("fidelity", r"fidelity_chosen|fidelity_rationale"),
            pattern("artifact_threshold", r"\| target \| method \| artifact \| threshold \| learning_if_pass \| learning_if_fail \|"),
            pattern("downstream_handoff", r"downstream_handoff"),
            pattern("safe_start_scope", r"safe_start_scope|safe_downstream_action"),
            pattern("blocked_commitments", r"blocked_commitments"),
            pattern("validation_flow", r"Exact Assumption.*Chosen Method.*Signal / Threshold|Validation Flow"),
        ),
        honesty_patterns=(
            pattern("design_time_inference", r"what_is_design_time_inference"),
            pattern("real_evidence", r"what_is_real_evidence"),
            pattern("unknowns", r"what_remains_unknown"),
            pattern("must_not_assume", r"must_not_assume"),
            pattern("forbidden_assumptions", r"forbidden_assumptions"),
            pattern("review_bound", r"review-bound"),
        ),
    ),
    SectionRule(
        name="Handoff to Design / Architecture",
        title_pattern=r"(?:18\.\s+)?Handoff to Design\s*/\s*Architecture",
        required_subheadings=(
            "Design Can Start",
            "Architecture Can Start",
            "Must Not Assume",
        ),
        min_nonempty_lines=28,
        detail_patterns=(
            pattern("workflow_prototype", r"workflow prototype|Step 1\.\.5|Step 1\.\.10|Step 1"),
            pattern("insight_action_bridge", r"insight[s]?\s*->\s*(?:action recommendation|next-step action|work item)|finding[s]?\s*->\s*task|issue signal.*work item|发现.*任务"),
            pattern("review_expression", r"review summary|review expression|review report|评审结论|复盘结论"),
            pattern(
                "core_object_chain",
                r"core business objects|核心业务对象|object_state_matrix|业务对象|Pet Profile\s*/\s*Visit Request|Payment Record\s*/\s*Clinical Note|Appointment Slot",
            ),
            pattern("evolvable_boundaries", r"analysis|action recommendation|next-step action|work item|review/report|对象链|extension seam"),
            pattern("boundary_first", r"租户边界|权限边界|审计边界"),
        ),
        decision_patterns=(
            pattern("not_nav_shell", r"而不是先画导航壳子"),
            pattern("before_after_order", r"先.*再讨论"),
            pattern("focus_on_decision_expression", r"决策表达"),
            pattern("must_not_assume_heading", r"Must Not Assume"),
        ),
        downstream_patterns=(
            pattern("prototype", r"prototype"),
            pattern("information_priority", r"信息优先级"),
            pattern("core_objects", r"核心对象链"),
            pattern("evolvable_boundaries", r"可演进边界"),
            pattern("boundary_work", r"边界"),
            pattern("automation_constraint", r"自动化执行|automation constraint|automation layer"),
        ),
        honesty_patterns=(
            pattern("must_not_assume", r"Must Not Assume"),
            pattern("validated_warning", r"validated"),
            pattern("automation_warning", r"automation"),
            pattern("mvp_warning", r"MVP"),
        ),
    ),
    SectionRule(
        name="Acceptance & Status",
        title_pattern=r"(?:19\.\s+)?Acceptance\s*&\s*Status",
        required_subheadings=(
            "Overall Admission",
            "Review Warnings / Pending External Confirmation",
            "Warning & Pending Confirmation Ledger",
            "Document Delivery State",
            "Evidence Confidence State",
            "Safe Start Scope",
            "Blocked Commitments",
            "Maturity & Confidence Ledger",
        ),
        min_nonempty_lines=40,
        detail_patterns=(
            pattern("warning_heading", r"Review Warnings / Pending External Confirmation"),
            pattern("warning_ledger", r"Warning & Pending Confirmation Ledger"),
            pattern("warning_level", r"warning_level"),
            pattern("missing_external_confirmation", r"missing_external_confirmation"),
            pattern("current_document_position", r"current_document_position"),
            pattern("safe_current_use", r"safe_current_use|safe_downstream_action"),
            pattern("document_delivery_state", r"document_delivery_state"),
            pattern("evidence_confidence_state", r"evidence_confidence_state"),
            pattern("blocked_commitments", r"blocked_commitments"),
            pattern("maturity_table", r"\| subject \| delivery_readiness_state \| evidence_confidence_state \|"),
        ),
        decision_patterns=(
            pattern("warning_high", r"warning-high"),
            pattern("warning_medium", r"warning-medium"),
            pattern("warning_low_or_watch", r"warning-low|watch-only"),
            pattern("document_not_equal_business", r"不等于业务已 externally-validated|does not equal"),
            pattern("delivery_state_boundary", r"downstream-start-safe|review-ready|blocked"),
            pattern("business_completeness_note", r"business_completeness_interpretation"),
        ),
        downstream_patterns=(
            pattern("safe_start_scope", r"safe_start_scope"),
            pattern("blocked_commitments", r"blocked_commitments"),
            pattern("safe_current_use", r"safe_current_use|safe_downstream_action"),
            pattern("stronger_commitment_blocker", r"stronger_commitment_blocker"),
            pattern("pending_confirmation", r"pending confirmation|pending_external"),
            pattern("implementation_ready_boundary", r"implementation-commit-ready"),
        ),
        honesty_patterns=(
            pattern("source_grounded_unvalidated", r"source-grounded-but-unvalidated"),
            pattern("design_time_inference", r"design-time-inference-heavy|design_time_inference"),
            pattern("forbidden_assumptions", r"forbidden_assumptions"),
            pattern("warning_binding", r"warning.*约束力|warning-bearing"),
            pattern("blocked", r"`blocked`|blocked"),
            pattern("must_not_assume", r"Must Not Assume|must_not_assume"),
        ),
    ),
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_heading(raw: str) -> str:
    value = raw.strip()
    value = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", value).strip()
    return value


def canonicalize_heading(raw: str) -> str:
    value = normalize_heading(raw)
    value = re.sub(r"\s*\([^)]*\)\s*$", "", value).strip().lower()
    value = re.sub(r"\s+", " ", value)
    aliases = {
        "module interface payload contract": "payload contract",
        "recommendation payload contract": "payload contract",
        "deferred capability seam": "deferred seam",
        "deferred attribution and conversion seam": "deferred seam",
    }
    value = aliases.get(value, value)
    return value


def heading_matches(required: str, actual: str) -> bool:
    required_raw = re.sub(r"\s+", " ", normalize_heading(required).lower())
    actual_raw = re.sub(r"\s+", " ", normalize_heading(actual).lower())
    required_key = canonicalize_heading(required)
    actual_key = canonicalize_heading(actual)
    return (
        actual_key == required_key
        or actual_key.startswith(required_key)
        or required_key.startswith(actual_key)
        or required_raw in actual_raw
        or actual_raw in required_raw
    )


def extract_h2_block(text: str, title_pattern: str) -> str | None:
    match = re.search(
        rf"^##\s+(?:\d+\.\s+)?[^\n]*?(?:{title_pattern})[^\n]*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return None
    start = match.end()
    next_h2 = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)
    end = start + next_h2.start() if next_h2 else len(text)
    return text[start:end]


def canonicalize_bilingual_text(text: str) -> str:
    normalized_lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            canonical_cells = []
            for cell in cells:
                aliases = re.findall(r"\(([^()\n]+)\)", cell)
                canonical_cells.append(aliases[-1].strip() if aliases else cell)
            normalized_lines.append("| " + " | ".join(canonical_cells) + " |")
            continue
        normalized_lines.append(re.sub(r"([^|\n()]+?)\s*\(([^()\n]+)\)", r"\2", raw))
    return "\n".join(normalized_lines)


def extract_h3_titles(block: str) -> list[str]:
    return [
        normalize_heading(match.group(1))
        for match in re.finditer(r"^###\s+(.+)$", block, flags=re.MULTILINE)
    ]


def count_nonempty_lines(block: str) -> int:
    return sum(1 for line in block.splitlines() if line.strip())


def matched_labels(text: str, patterns: tuple[PatternDef, ...]) -> list[str]:
    normalized = canonicalize_bilingual_text(text)
    return [
        item.label
        for item in patterns
        if re.search(item.regex, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        or re.search(item.regex, normalized, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    ]


def ratio_score(matched: int, total: int, max_points: float) -> float:
    if total <= 0:
        return max_points
    return round(max_points * matched / total, 1)


def score_section(text: str, rule: SectionRule, threshold: float) -> dict[str, object]:
    block = extract_h2_block(text, rule.title_pattern)
    if block is None:
        return {
            "name": rule.name,
            "present": False,
            "score": 0.0,
            "verdict": "BLOCKED",
            "line_count": 0,
            "dimensions": [
                {
                    "name": "completeness",
                    "score": 0.0,
                    "matched": 0,
                    "total": len(rule.required_subheadings),
                    "missing": list(rule.required_subheadings),
                }
            ],
            "missing_summary": ["section missing"],
        }

    h3_titles = extract_h3_titles(block)
    matched_headings = [
        title
        for title in rule.required_subheadings
        if any(heading_matches(title, item) for item in h3_titles)
    ]
    missing_headings = [
        title
        for title in rule.required_subheadings
        if not any(heading_matches(title, item) for item in h3_titles)
    ]
    line_count = count_nonempty_lines(block)

    detail_hits = matched_labels(block, rule.detail_patterns)
    decision_hits = matched_labels(block, rule.decision_patterns)
    downstream_hits = matched_labels(block, rule.downstream_patterns)
    honesty_hits = matched_labels(block, rule.honesty_patterns)

    completeness_score = ratio_score(len(matched_headings), len(rule.required_subheadings), 20.0)
    depth_line_score = round(10.0 * min(1.0, line_count / rule.min_nonempty_lines), 1)
    depth_structure_score = ratio_score(len(detail_hits), len(rule.detail_patterns), 10.0)
    depth_score = round(depth_line_score + depth_structure_score, 1)
    decision_score = ratio_score(len(decision_hits), len(rule.decision_patterns), 20.0)
    downstream_score = ratio_score(len(downstream_hits), len(rule.downstream_patterns), 20.0)
    honesty_score = ratio_score(len(honesty_hits), len(rule.honesty_patterns), 20.0)
    total_score = round(
        completeness_score + depth_score + decision_score + downstream_score + honesty_score,
        1,
    )

    dimensions = [
        {
            "name": "completeness",
            "score": completeness_score,
            "matched": len(matched_headings),
            "total": len(rule.required_subheadings),
            "missing": missing_headings,
        },
        {
            "name": "detail_depth",
            "score": depth_score,
            "line_score": depth_line_score,
            "line_count": line_count,
            "min_line_target": rule.min_nonempty_lines,
            "matched": len(detail_hits),
            "total": len(rule.detail_patterns),
            "missing": [item.label for item in rule.detail_patterns if item.label not in detail_hits],
        },
        {
            "name": "decision_tradeoff",
            "score": decision_score,
            "matched": len(decision_hits),
            "total": len(rule.decision_patterns),
            "missing": [item.label for item in rule.decision_patterns if item.label not in decision_hits],
        },
        {
            "name": "downstream_usability",
            "score": downstream_score,
            "matched": len(downstream_hits),
            "total": len(rule.downstream_patterns),
            "missing": [item.label for item in rule.downstream_patterns if item.label not in downstream_hits],
        },
        {
            "name": "boundary_honesty",
            "score": honesty_score,
            "matched": len(honesty_hits),
            "total": len(rule.honesty_patterns),
            "missing": [item.label for item in rule.honesty_patterns if item.label not in honesty_hits],
        },
    ]

    verdict = "PASS" if total_score >= threshold else "BLOCKED"
    missing_summary = []
    if missing_headings:
        missing_summary.append(f"missing_subheadings={', '.join(missing_headings)}")
    if line_count < rule.min_nonempty_lines:
        missing_summary.append(f"line_depth={line_count}/{rule.min_nonempty_lines}")
    for dimension in dimensions[1:]:
        if dimension["missing"]:
            missing_summary.append(
                f"{dimension['name']} missing: {', '.join(dimension['missing'][:3])}"
            )

    return {
        "name": rule.name,
        "present": True,
        "score": total_score,
        "verdict": verdict,
        "line_count": line_count,
        "dimensions": dimensions,
        "missing_summary": missing_summary,
    }


def main() -> int:
    emit_compatibility_warning("scripts/phase1/phase1_prd_section_scoring_gate.py")
    parser = argparse.ArgumentParser(description="Phase-1 PRD section scoring gate")
    parser.add_argument("--prd", required=True)
    parser.add_argument("--min-section-score", type=float, default=90.0)
    parser.add_argument(
        "--min-dimension-score",
        type=float,
        default=16.0,
        help="minimum score each scoring dimension must reach; prevents one thin dimension from being masked by others",
    )
    parser.add_argument("--output-json")
    args = parser.parse_args()

    prd_path = Path(args.prd).resolve()
    text = read_text(prd_path)

    results = [score_section(text, rule, args.min_section_score) for rule in SECTION_RULES]
    for item in results:
        dimension_scores = [float(dimension["score"]) for dimension in item["dimensions"]]
        dimension_blocked = any(score < args.min_dimension_score for score in dimension_scores)
        if item["verdict"] == "PASS" and dimension_blocked:
            item["verdict"] = "BLOCKED"
            item["missing_summary"].append(
                f"dimension_floor={args.min_dimension_score} not met"
            )
    average = round(sum(item["score"] for item in results) / len(results), 1) if results else 0.0
    blocked = [item for item in results if item["verdict"] != "PASS"]

    payload = {
        "prd": str(prd_path),
        "min_section_score": args.min_section_score,
        "min_dimension_score": args.min_dimension_score,
        "average_score": average,
        "sections": results,
    }
    if args.output_json:
        output_path = Path(args.output_json).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("== Phase-1 PRD Section Scoring Gate ==")
    print(f"prd: {prd_path}")
    print(f"min_section_score: {args.min_section_score}")
    print(f"min_dimension_score: {args.min_dimension_score}")
    for item in results:
        print(f"\n[{item['verdict']}] {item['name']}: total={item['score']}/100")
        for dimension in item["dimensions"]:
            if dimension["name"] == "detail_depth":
                print(
                    "  - detail_depth: "
                    f"{dimension['score']}/20 "
                    f"(lines={dimension['line_count']}/{dimension['min_line_target']}, "
                    f"signals={dimension['matched']}/{dimension['total']})"
                )
            else:
                print(
                    f"  - {dimension['name']}: {dimension['score']}/20 "
                    f"(matched={dimension['matched']}/{dimension['total']})"
                )
        if item["missing_summary"]:
            print(f"  - gaps: {'; '.join(item['missing_summary'][:4])}")

    print(f"\naverage_score: {average}")
    if blocked:
        print(f"blocked_sections: {', '.join(item['name'] for item in blocked)}")
        print("FINAL: BLOCKED")
        return 2

    print("FINAL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
