#!/usr/bin/env python3
"""
Generate a zh-CN audit mirror for the converged Phase-1 PRD main document.

Intent:
- keep the English PRD as the runtime/canonical artifact
- emit a separate Chinese review mirror for human reviewers
- preserve key domain terms and state labels in bilingual form
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import re
from pathlib import Path


def normalize_lookup_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


TITLE_MAP = {
    "Prototype Spec": "原型规格说明 (Prototype Spec)",
    "Prototype Prompt Pack": "原型提示包 (Prototype Prompt Pack)",
    "Phase-1 Execution Report": "Phase-1 执行报告 (Phase-1 Execution Report)",
}


HEADING_MAP = {
    "Document Metadata": "文档元信息 (Document Metadata)",
    "Metadata": "元信息 (Metadata)",
    "Executive Summary": "执行摘要 (Executive Summary)",
    "Problem Statement": "问题陈述 (Problem Statement)",
    "Target Users & Key Roles": "目标用户与关键角色 (Target Users & Key Roles)",
    "Stakeholder Analysis": "干系人分析 (Stakeholder Analysis)",
    "Strategic Context": "战略背景 (Strategic Context)",
    "Product Direction Overview": "产品方向总览 (Product Direction Overview)",
    "Business Scenarios": "业务场景 (Business Scenarios)",
    "Requirements Structure": "需求结构 (Requirements Structure)",
    "NFR / Quality Requirements": "非功能 / 质量需求 (NFR / Quality Requirements)",
    "Domain Model": "领域模型 (Domain Model)",
    "Information Architecture Direction": "信息架构方向 (Information Architecture Direction)",
    "MVP Definition & Scope": "MVP 定义与范围 (MVP Definition & Scope)",
    "Validation Strategy & Current Conclusion": "验证策略与当前结论 (Validation Strategy & Current Conclusion)",
    "User Stories, Use Cases, and Requirements": "用户故事、用例与需求 (User Stories, Use Cases, and Requirements)",
    "Out of Scope": "范围外项 (Out of Scope)",
    "Dependencies, Risks, and Review-Bound Truth": "依赖、风险与评审保留真相 (Dependencies, Risks, and Review-Bound Truth)",
    "Key Decision Rationale Summary": "关键决策依据摘要 (Key Decision Rationale Summary)",
    "Handoff to Design / Architecture": "交接给设计 / 架构 (Handoff to Design / Architecture)",
    "Acceptance & Status": "验收与状态 (Acceptance & Status)",
    "Source Artifacts": "来源产物 (Source Artifacts)",
    "Synthesized Problem Narrative": "综合问题叙述 (Synthesized Problem Narrative)",
    "Problem Boundary Clarification": "问题边界澄清 (Problem Boundary Clarification)",
    "Evidence Status": "证据状态 (Evidence Status)",
    "Integrated Problem Evidence": "综合问题证据 (Integrated Problem Evidence)",
    "Source Signal Recompilation": "来源信号重编译 (Source Signal Recompilation)",
    "Primary Boundary": "核心边界 (Primary Boundary)",
    "Why This Segment, Not Others": "为何选择该细分而非其他 (Why This Segment, Not Others)",
    "Secondary / Supporting Roles": "次要 / 支撑角色 (Secondary / Supporting Roles)",
    "Out-of-scope Users": "范围外用户 (Out-of-scope Users)",
    "Role Interaction Note": "角色交互说明 (Role Interaction Note)",
    "Fragile Points in Adoption": "采纳脆弱点 (Fragile Points in Adoption)",
    "Persona Boundary and Interaction Chain": "Persona 边界与交互链 (Persona Boundary and Interaction Chain)",
    "User/Goal/Problem Panorama": "用户 / 目标 / 问题全景 (User/Goal/Problem Panorama)",
    "Persona / JTBD Matrix": "Persona / JTBD 矩阵 (Persona / JTBD Matrix)",
    "Persona Context Scenario and Key Paths": "Persona 情境与关键路径 (Persona Context Scenario and Key Paths)",
    "Primary Persona Context Scenario": "核心 Persona 情境 (Primary Persona Context Scenario)",
    "Design Requirements Extraction": "设计需求提取 (Design Requirements Extraction)",
    "Boundary Reasoning Ledger": "边界推理台账 (Boundary Reasoning Ledger)",
    "Stakeholder Chain Summary": "干系人链摘要 (Stakeholder Chain Summary)",
    "Adoption Fragility": "采纳脆弱性 (Adoption Fragility)",
    "Key Stakeholder Profiles": "关键干系人画像 (Key Stakeholder Profiles)",
    "Adoption Chain": "采纳链 (Adoption Chain)",
    "Stakeholder Conflict Map": "干系人冲突图 (Stakeholder Conflict Map)",
    "Why Now": "为何现在做 (Why Now)",
    "Chosen Need Framing": "选定的需求 framing (Chosen Need Framing)",
    "Business Outcome Path": "业务结果路径 (Business Outcome Path)",
    "Context Pressure Note": "上下文压力说明 (Context Pressure Note)",
    "Integrated Direction Evidence": "综合方向证据 (Integrated Direction Evidence)",
    "Product Direction Summary": "产品方向摘要 (Product Direction Summary)",
    "First-wave Value Proposition": "首波价值主张 (First-wave Value Proposition)",
    "What This Product Is Not": "本产品不是什么 (What This Product Is Not)",
    "Capability Recompilation": "能力重编译 (Capability Recompilation)",
    "Product Mechanism": "产品机制 (Product Mechanism)",
    "Integrated Product Mechanism Evidence": "综合产品机制证据 (Integrated Product Mechanism Evidence)",
    "Scenario Set Overview": "场景集总览 (Scenario Set Overview)",
    "Scenario Decomposition": "场景拆解 (Scenario Decomposition)",
    "Key Scenario Deep Analysis": "关键场景深度分析 (Key Scenario Deep Analysis)",
    "Goal": "目标 (Goal)",
    "Structure Choice": "结构选择 (Structure Choice)",
    "Structure Alternatives Comparison": "结构备选方案对比 (Structure Alternatives Comparison)",
    "Problem-to-Structure Mapping": "问题到结构的映射 (Problem-to-Structure Mapping)",
    "Value Loop and Downstream Preservation Notes": "价值闭环与下游保留说明 (Value Loop and Downstream Preservation Notes)",
    "Backbone Activities (Business Process Decomposition Precursor)": "骨干活动（业务流程分解前导） (Backbone Activities (Business Process Decomposition Precursor))",
    "Business Process Identification": "业务流程识别 (Business Process Identification)",
    "Workflow / State Detail": "工作流 / 状态细节 (Workflow / State Detail)",
    "Constraint Stress-Test": "约束压力测试 (Constraint Stress-Test)",
    "Priority Split": "优先级切分 (Priority Split)",
    "Diagram": "图示 (Diagram)",
    "Business Process Decomposition": "业务流程分解 (Business Process Decomposition)",
    "Exception and Failure Flows": "异常与失败流程 (Exception and Failure Flows)",
    "Structure Stress-Test and Deepening Loop Log": "结构压力测试与深化循环日志 (Structure Stress-Test and Deepening Loop Log)",
    "Structure Stress-Test": "结构压力测试 (Structure Stress-Test)",
    "Deepening Loop Log": "深化循环日志 (Deepening Loop Log)",
    "Structural Reasoning Ledger": "结构推理台账 (Structural Reasoning Ledger)",
    "Top Quality Attributes": "最高优先质量属性 (Top Quality Attributes)",
    "NFR / Quality Requirements": "非功能 / 质量需求 (NFR / Quality Requirements)",
    "NFR Prioritization Reasoning": "NFR 优先级推理 (NFR Prioritization Reasoning)",
    "Quality Scenario Matrix": "质量场景矩阵 (Quality Scenario Matrix)",
    "Metric Definition and Interpretation Register": "指标定义与解读登记表 (Metric Definition and Interpretation Register)",
    "Module Responsibility Matrix": "模块职责矩阵 (Module Responsibility Matrix)",
    "Specification Stress-Test": "规格压力测试 (Specification Stress-Test)",
    "Specification Reasoning Ledger": "规格推理台账 (Specification Reasoning Ledger)",
    "Domain Model Direction": "领域模型方向 (Domain Model Direction)",
    "Conceptual ER Diagram": "概念 ER 图 (Conceptual ER Diagram)",
    "Key Relationships and Data Characteristics": "关键关系与数据特征 (Key Relationships and Data Characteristics)",
    "Business Subsystem Boundaries": "业务子系统边界 (Business Subsystem Boundaries)",
    "Object-to-Workflow Mapping": "对象到工作流映射 (Object-to-Workflow Mapping)",
    "IA Direction Summary": "信息架构方向摘要 (IA Direction Summary)",
    "IA Decision Alternatives Comparison": "信息架构备选方案对比 (IA Decision Alternatives Comparison)",
    "IA Spec Matrix": "信息架构规格矩阵 (IA Spec Matrix)",
    "Integrated IA Evidence": "综合 IA 证据 (Integrated IA Evidence)",
    "Slice Decision Context": "切片决策上下文 (Slice Decision Context)",
    "Slice Strategy": "切片策略 (Slice Strategy)",
    "Scope, Dependency Logic, and Cutline": "范围、依赖逻辑与切线 (Scope, Dependency Logic, and Cutline)",
    "Deferred Honesty, Assumptions, and Slice Map": "延后诚实性、假设与切片图 (Deferred Honesty, Assumptions, and Slice Map)",
    "Slice Reasoning Ledger": "切片推理台账 (Slice Reasoning Ledger)",
    "Operational Flow Specification": "操作流程规格 (Operational Flow Specification)",
    "State Machine and Transition Rules": "状态机与状态转移规则 (State Machine and Transition Rules)",
    "Acceptance Criteria": "验收标准 (Acceptance Criteria)",
    "Validation Context": "验证上下文 (Validation Context)",
    "Targets, Methods, and Thresholds": "目标、方法与阈值 (Targets, Methods, and Thresholds)",
    "Evidence State and Current Decision": "证据状态与当前决策 (Evidence State and Current Decision)",
    "Delivery Readiness and Evidence Confidence": "交付成熟度与证据置信度 (Delivery Readiness and Evidence Confidence)",
    "Validation Flow and Convergence Readiness": "验证流程与收口准备度 (Validation Flow and Convergence Readiness)",
    "Validation Reasoning Ledger": "验证推理台账 (Validation Reasoning Ledger)",
    "Review-Bound Carryover": "评审保留的延续项 (Review-Bound Carryover)",
    "Epic Decomposition": "史诗分解 (Epic Decomposition)",
    "Primary User Story": "核心用户故事 (Primary User Story)",
    "Supporting Use Cases": "支撑用例 (Supporting Use Cases)",
    "Story Quality Gate (INVEST)": "故事质量门禁 (INVEST) (Story Quality Gate (INVEST))",
    "Requirement Translation": "需求转译 (Requirement Translation)",
    "Extended Requirement Set": "扩展需求集 (Extended Requirement Set)",
    "Dependencies": "依赖项 (Dependencies)",
    "Risks": "风险 (Risks)",
    "Risk Register": "风险登记表 (Risk Register)",
    "Review-Bound Truth": "评审保留真相 (Review-Bound Truth)",
    "Integrated Decision Trace": "综合决策轨迹 (Integrated Decision Trace)",
    "Stage-02b Execution State": "Stage-02b 执行状态 (Stage-02b Execution State)",
    "Design Can Start": "可启动的设计工作 (Design Can Start)",
    "Architecture Can Start": "可启动的架构工作 (Architecture Can Start)",
    "Must Not Assume": "禁止默认假设 (Must Not Assume)",
    "Overall Admission": "总体验收结论 (Overall Admission)",
    "Review Warnings / Pending External Confirmation": "评审告警 / 待外部确认 (Review Warnings / Pending External Confirmation)",
    "Warning & Pending Confirmation Ledger": "告警与待确认台账 (Warning & Pending Confirmation Ledger)",
    "Document Delivery State": "文档交付状态 (Document Delivery State)",
    "Evidence Confidence State": "证据置信状态 (Evidence Confidence State)",
    "Safe Start Scope": "可安全启动范围 (Safe Start Scope)",
    "Blocked Commitments": "被阻断的承诺 (Blocked Commitments)",
    "Maturity & Confidence Ledger": "成熟度与置信度台账 (Maturity & Confidence Ledger)",
    "Convergence Summary": "收敛摘要 (Convergence Summary)",
    "Analysis Delta Ledger": "分析差异台账 (Analysis Delta Ledger)",
    "Extracted Runtime Trace Blocks": "抽取的运行时 Trace 块 (Extracted Runtime Trace Blocks)",
    "Context and Objective": "上下文与目标 (Context and Objective)",
    "Prototype Scope and Boundary": "原型范围与边界 (Prototype Scope and Boundary)",
    "Page Map": "页面地图 (Page Map)",
    "Main Flow and Key Transitions": "主流程与关键迁移 (Main Flow and Key Transitions)",
    "Page Briefs": "页面简述 (Page Briefs)",
    "Core Objects and State Matrix": "核心对象与状态矩阵 (Core Objects and State Matrix)",
    "Key State Coverage": "关键状态覆盖 (Key State Coverage)",
    "Prototype Generation Constraints": "原型生成约束 (Prototype Generation Constraints)",
    "Provenance / Confidence / Verification": "来源 / 置信度 / 验证 (Provenance / Confidence / Verification)",
    "Reasoning Evidence": "推理证据 (Reasoning Evidence)",
    "Page-Map Construction Reasoning": "页面地图构建推理 (Page-Map Construction Reasoning)",
    "Flow Preservation Reasoning": "流程保真推理 (Flow Preservation Reasoning)",
    "State Coverage Honesty": "状态覆盖诚实性 (State Coverage Honesty)",
    "Deferred / Non-Goal Preservation": "延后项 / 非目标保留 (Deferred / Non-Goal Preservation)",
    "Deepening Loop Log": "深化循环日志 (Deepening Loop Log)",
    "Method-Family Usage Evidence": "方法族使用证据 (Method-Family Usage Evidence)",
    "Diagram / Structured Representation": "图示 / 结构化表示 (Diagram / Structured Representation)",
    "Acceptance and Flow": "验收与流转 (Acceptance and Flow)",
    "Referenced Upstream Artifacts": "引用的上游产物 (Referenced Upstream Artifacts)",
    "Prototype Execution Mapping": "原型执行映射 (Prototype Execution Mapping)",
    "Source Notes": "来源说明 (Source Notes)",
    "External AI Prompt": "外部 AI 提示词 (External AI Prompt)",
    "Human Review Notes": "人工评审说明 (Human Review Notes)",
    "Upstream Signals Preserved": "已保留的上游信号 (Upstream Signals Preserved)",
}

HEADING_BODY_MAP = {
    "Baseline Establishment": "建立初始工作基线 (Baseline Establishment)",
    "Findings-to-Task Translation": "将发现转为任务 (Findings-to-Task Translation)",
    "Post-Optimization Review": "优化后复盘 (Post-Optimization Review)",
    "[Primary Operator] Establish Initial Baseline": "[核心操作者] 建立初始基线 ([Primary Operator] Establish Initial Baseline)",
    "[Content Operator] Translate Finding into Action": "[Operator] Translate Finding into Action",
    "[Business Owner] Review Next-cycle Outcome": "[Decision Owner] Review Next-cycle Outcome",
    "Primary Boundary Lock": "锁定核心边界",
    "Problem Mechanism Reframe": "重构问题机制",
    "Need Framing and Open-Truth Discipline": "需求 framing 与开放真相纪律",
    "Workflow-First Panorama Choice": "选择工作流优先的全景结构",
    "Findings-to-Task Backbone Hardening": "强化发现到任务的主骨架",
    "Review as Decision Endpoint": "将复盘作为决策终点",
    "Priority Cutline for First-Wave Structure": "首波结构的优先级切线",
    "NFR Priority Lock": "锁定 NFR 优先级",
    "Object-Chain Domain Recompilation": "对象链领域重编译",
    "Subsystem Boundary Map": "子系统边界映射",
    "Workflow-First IA Direction": "工作流优先的信息架构方向",
    "Stage-03 Slice-Readiness Pressure Test": "Stage-03 切片就绪度压力测试",
    "Workflow-Loop Slice Selection": "工作流闭环切片选择",
    "Minimum Viable Loop Guard": "最小可行闭环守卫",
    "Dependency-First Cutline": "依赖优先切线",
    "Deferred Honesty and Assumption Carryover": "延后诚实性与假设延续",
    "Exact-Assumption Targeting": "精确假设定靶",
    "Method-Fit and Fidelity Selection": "方法匹配与保真度选择",
    "Evidence Honesty Classification": "证据诚实性分级",
    "Decision State and Convergence Admission": "决策状态与收口准入",
}


FIELD_LABEL_MAP = {
    "document_name": "文档名称 (document_name)",
    "version": "版本 (version)",
    "status": "状态 (status)",
    "delivery_profile": "交付画像 (delivery_profile)",
    "source_status": "来源状态 (source_status)",
    "intended_consumers": "目标消费者 (intended_consumers)",
    "ai_inferred_marker": "AI 推断标记 (ai_inferred_marker)",
    "document_maturity_interpretation": "文档成熟度解读 (document_maturity_interpretation)",
    "business_completeness_interpretation": "业务完善度解读 (business_completeness_interpretation)",
    "warning_count_by_level": "按级别统计的告警数量 (warning_count_by_level)",
    "interpretation_rule": "解读规则 (interpretation_rule)",
    "document_delivery_state": "文档交付状态 (document_delivery_state)",
    "evidence_confidence_state": "证据置信状态 (evidence_confidence_state)",
    "safe_start_scope": "可安全启动范围 (safe_start_scope)",
    "blocked_commitments": "被阻断的承诺 (blocked_commitments)",
    "stage_02b_execution_state": "Stage-02b 执行状态 (stage_02b_execution_state)",
    "handoff_nfr_state": "交接 NFR 状态 (handoff_nfr_state)",
    "handoff_nfr_notes": "交接 NFR 说明 (handoff_nfr_notes)",
    "stage_02b_skip_declaration": "Stage-02b 跳过声明 (stage_02b_skip_declaration)",
    "supporting_review_artifact": "支撑评审产物 (supporting_review_artifact)",
    "value_dimension": "价值维度 (value_dimension)",
    "usability_dimension": "可用性维度 (usability_dimension)",
    "feasibility_dimension": "可行性维度 (feasibility_dimension)",
    "dimensions_gap_note": "维度缺口说明 (dimensions_gap_note)",
    "what_is_design_time_inference": "属于设计期推断 (what_is_design_time_inference)",
    "what_is_real_evidence": "属于真实证据 (what_is_real_evidence)",
    "what_remains_unknown": "仍然未知 (what_remains_unknown)",
    "subject_level_ledger_note": "主体级台账说明 (subject_level_ledger_note)",
    "forbidden_assumptions": "禁止的默认假设 (forbidden_assumptions)",
}

FIELD_LABEL_MAP.update(
    {
        "this is not": "这不是 (this is not)",
        "actual operating problem": "真实经营问题 (actual operating problem)",
        "downstream consequence": "下游后果 (downstream consequence)",
        "review-bound / inferred": "评审保留 / 推断项 (review-bound / inferred)",
        "source vision": "源素材愿景 (source vision)",
        "source objectives": "源素材目标 (source objectives)",
        "current_truth_state": "当前真相状态 (current_truth_state)",
        "missing_evidence_to_unlock": "解锁所需证据 (missing_evidence_to_unlock)",
        "source_evidence": "源素材证据 (source_evidence)",
        "must_not_assume": "不得默认假设 (must_not_assume)",
        "lifecycle implication": "生命周期影响 (lifecycle implication)",
        "audit implication": "审计影响 (audit implication)",
        "review implication": "评审影响 (review implication)",
        "role implication": "角色影响 (role implication)",
        "partial-tool gap question": "局部工具缺口问题 (partial-tool gap question)",
        "carryover rule": "承接规则 (carryover rule)",
        "return-for-clarification": "返回澄清 (return-for-clarification)",
        "top_problem_clusters": "核心问题簇 (top_problem_clusters)",
        "top_opportunity_clusters": "核心机会簇 (top_opportunity_clusters)",
        "chosen segment": "选定细分 (chosen segment)",
        "primary_boundary": "核心边界 (primary_boundary)",
        "core_problem_clusters": "核心问题簇 (core_problem_clusters)",
        "core_opportunity_clusters": "核心机会簇 (core_opportunity_clusters)",
        "archetype": "原型画像 (archetype)",
        "actor_goal": "角色目标 (actor_goal)",
        "implied_design_requirement": "隐含设计要求 (implied_design_requirement)",
        "alternatives_compared": "对比过的方案 (alternatives_compared)",
        "tradeoff_or_tension": "权衡 / 张力 (tradeoff_or_tension)",
        "decision_effect": "决策效果 (decision_effect)",
        "remaining_unknown": "剩余未知 (remaining_unknown)",
        "downstream_handoff": "向下游的交接要求 (downstream_handoff)",
        "direct user": "直接使用者 (direct user)",
        "operational partner": "执行协作方 (operational partner)",
        "budget / continuation authority": "预算 / 持续投入决策者 (budget / continuation authority)",
        "risk gate": "风险闸口 (risk gate)",
        "trigger": "触发条件 (trigger)",
        "preconditions": "前置条件 (preconditions)",
        "key exception paths": "关键异常路径 (key exception paths)",
        "supporting_roles": "支撑角色 (supporting_roles)",
        "goal_direction": "目标方向 (goal_direction)",
        "user-confirmed": "用户已确认 (user-confirmed)",
        "final_problem_statement": "最终问题陈述 (final_problem_statement)",
        "problem_mechanism": "问题机制 (problem_mechanism)",
        "problem mechanism": "问题机制 (problem mechanism)",
        "segment signals": "客群信号 (segment signals)",
        "capability signals": "能力信号 (capability signals)",
        "metric signals": "指标信号 (metric signals)",
        "why this not that": "为何是这个而不是别的 (why this not that)",
        "why_this_structure_not_that": "为何选这种结构而不是别的 (why_this_structure_not_that)",
        "tension register": "张力登记表 (tension register)",
        "actor/system decomposition": "角色 / 系统拆解 (actor/system decomposition)",
        "chosen_method": "选定方法 (chosen_method)",
        "reasoning": "原因说明 (reasoning)",
        "nfr_source": "NFR 来源 (nfr_source)",
        "domain_model_state": "领域模型状态 (domain_model_state)",
        "ia_direction_state": "信息架构方向状态 (ia_direction_state)",
        "impact_on_phase2": "对 Phase-2 的影响 (impact_on_phase2)",
        "minimum_viable_for_phase2": "对 Phase-2 是否最小可用 (minimum_viable_for_phase2)",
        "mitigation_note": "补偿说明 (mitigation_note)",
        "user boundary": "用户边界 (user boundary)",
        "structure": "结构选择 (structure)",
        "slice": "切片策略 (slice)",
        "validation method": "验证方法 (validation method)",
        "deferral strategy": "延后策略 (deferral strategy)",
        "requirement theme a": "需求主题 A (requirement theme A)",
        "requirement theme b": "需求主题 B (requirement theme B)",
        "requirement theme c": "需求主题 C (requirement theme C)",
        "requirement theme d": "需求主题 D (requirement theme D)",
        "requirement theme e": "需求主题 E (requirement theme E)",
        "chosen_framing": "选定 framing (chosen_framing)",
        "delta_1": "变化点 1 (delta_1)",
        "delta_2": "变化点 2 (delta_2)",
        "delta_3": "变化点 3 (delta_3)",
        "delta_4": "变化点 4 (delta_4)",
        "value_loop": "价值闭环 (value_loop)",
        "design_should_preserve": "设计需要保留 (design_should_preserve)",
        "architecture_should_preserve": "架构需要保留 (architecture_should_preserve)",
        "structure implication": "结构含义 (structure implication)",
        "main success path": "主成功路径 (main success path)",
        "success criteria": "成功标准 (success criteria)",
        "scenario consequence if weak": "场景薄弱时的后果 (scenario consequence if weak)",
        "failure trigger": "失败触发条件 (failure trigger)",
        "handling strategy": "处理策略 (handling strategy)",
        "business constraints": "业务约束 (business constraints)",
        "technical constraints": "技术约束 (technical constraints)",
        "compliance/privacy constraints": "合规 / 隐私约束 (compliance/privacy constraints)",
        "resource/timeline constraints": "资源 / 时间约束 (resource/timeline constraints)",
        "exclusion logic": "排除逻辑 (exclusion logic)",
        "current_validation_target": "当前验证目标 (current_validation_target)",
        "upstream_stage_materially_used": "实质使用的上游阶段产物 (upstream_stage_materially_used)",
        "fidelity_chosen": "选定保真度 (fidelity_chosen)",
        "fidelity_rationale": "保真度选择理由 (fidelity_rationale)",
        "prototype_or_equivalent_artifact": "原型或等价产物 (prototype_or_equivalent_artifact)",
        "evidence_summary": "证据摘要 (evidence_summary)",
        "revision_consequences": "修订后果 (revision_consequences)",
        "what_downstream_must_not_assume": "下游不得默认假设 (what_downstream_must_not_assume)",
        "unified_product_pack_status": "统一产品包状态 (unified_product_pack_status)",
        "why_chosen": "为何选用 (why_chosen)",
        "method_bundle_activation": "方法包激活 (method_bundle_activation)",
        "chosen_panorama_structure": "选定的全景结构 (chosen_panorama_structure)",
        "challenge": "挑战 (challenge)",
        "current_product_context": "当前产品上下文 (current_product_context)",
        "prototype_goal": "原型目标 (prototype_goal)",
        "assumptions": "假设 (assumptions)",
        "open_questions": "开放问题 (open_questions)",
        "prototype_scope": "原型范围 (prototype_scope)",
        "first_wave_in_scope": "首波范围内项 (first_wave_in_scope)",
        "later_slices": "后续切片 (later_slices)",
        "deferred_items": "延后项 (deferred_items)",
        "non_goals": "非目标项 (non_goals)",
        "scope_boundary_note": "范围边界说明 (scope_boundary_note)",
        "page_map": "页面地图 (page_map)",
        "page_name": "页面名称 (page_name)",
        "page_role": "页面角色 (page_role)",
        "primary_actor": "主要角色 (primary_actor)",
        "why_it_exists": "存在原因 (why_it_exists)",
        "main_flow": "主流程 (main_flow)",
        "alternate_paths": "替代路径 (alternate_paths)",
        "consequence": "结果影响 (consequence)",
        "visible_pages": "可见页面 (visible_pages)",
        "page_briefs": "页面简述 (page_briefs)",
        "page_goal": "页面目标 (page_goal)",
        "entry_condition": "进入条件 (entry_condition)",
        "secondary_support_regions": "次级支持区域 (secondary_support_regions)",
        "dominant_component_pattern": "主导组件模式 (dominant_component_pattern)",
        "action_model": "动作模型 (action_model)",
        "forbidden_layout_patterns": "禁止布局模式 (forbidden_layout_patterns)",
        "must_show_together": "必须同时展示 (must_show_together)",
        "core_information_blocks": "核心信息块 (core_information_blocks)",
        "core_actions": "核心动作 (core_actions)",
        "required_user_inputs_or_confirmations": "必需的用户输入或确认 (required_user_inputs_or_confirmations)",
        "render_blocks_in_order": "按顺序渲染的区块 (render_blocks_in_order)",
        "field_groups": "字段分组 (field_groups)",
        "input_controls": "输入控件 (input_controls)",
        "summary_cards": "摘要卡片 (summary_cards)",
        "detail_fields_in_order": "按顺序展示的明细字段 (detail_fields_in_order)",
        "table_columns": "表格列 (table_columns)",
        "filters_and_selectors": "筛选与选择器 (filters_and_selectors)",
        "required_status_messages": "必需状态消息 (required_status_messages)",
        "important_state_variants": "重要状态变体 (important_state_variants)",
        "primary_cta_label": "主要 CTA 文案 (primary_cta_label)",
        "secondary_ctas": "次级 CTA (secondary_ctas)",
        "submission_feedback": "提交通知反馈 (submission_feedback)",
        "context_arrives_from": "上下文来源 (context_arrives_from)",
        "context_must_continue_to": "上下文必须延续到 (context_must_continue_to)",
        "exit_paths": "退出路径 (exit_paths)",
        "prototype_inference_note": "原型推断说明 (prototype_inference_note)",
        "object_state_matrix": "对象状态矩阵 (object_state_matrix)",
        "visible_in_pages": "出现于页面 (visible_in_pages)",
        "required_states": "必需状态 (required_states)",
        "state_changing_actions": "改变状态的动作 (state_changing_actions)",
        "blocked_or_exception_notes": "阻断或异常说明 (blocked_or_exception_notes)",
        "key_state_coverage": "关键状态覆盖 (key_state_coverage)",
        "where_visible": "出现位置 (where_visible)",
        "why_required": "为什么必须存在 (why_required)",
        "execution_handoff_note": "执行交接说明 (execution_handoff_note)",
        "external_executor_brief": "外部执行器简报 (external_executor_brief)",
        "prototype_inference_log": "原型推断日志 (prototype_inference_log)",
        "inferred_item": "推断项 (inferred_item)",
        "why_needed": "为何需要 (why_needed)",
        "why_safe_enough": "为何足够安全 (why_safe_enough)",
        "what_breaks_if_wrong": "如果判断错误会破坏什么 (what_breaks_if_wrong)",
        "page_candidates_considered": "已考虑的页面候选 (page_candidates_considered)",
        "why_considered": "为何考虑 (why_considered)",
        "why_rejected_or_kept": "为何保留或淘汰 (why_rejected_or_kept)",
        "chosen_page_map_logic": "选定页面地图逻辑 (chosen_page_map_logic)",
        "workflow_backbone_used": "采用的工作流骨架 (workflow_backbone_used)",
        "minimum_acceptance": "最小验收条件 (minimum_acceptance)",
        "handoff_to": "交接给 (handoff_to)",
        "handoff_package": "交接包 (handoff_package)",
        "referenced_prd": "引用的 PRD (referenced_prd)",
        "referenced_stage_outputs": "引用的阶段产物 (referenced_stage_outputs)",
        "referenced_sections": "引用的章节 (referenced_sections)",
        "this_artifact_feeds": "本产物供给下游 (this_artifact_feeds)",
        "persona_context_signal": "角色上下文信号 (persona_context_signal)",
        "design_requirement_signal": "设计需求信号 (design_requirement_signal)",
        "carryover_signal": "保留项信号 (carryover_signal)",
        "deferred_honesty_signal": "延后诚实性信号 (deferred_honesty_signal)",
        "acceptance_signal": "验收信号 (acceptance_signal)",
        "constraints": "约束 (constraints)",
        "what": "内容 (what)",
        "reliability": "可靠性 (reliability)",
        "security/data-control": "安全 / 数据控制 (security/data-control)",
        "performance": "性能 (performance)",
        "maintainability": "可维护性 (maintainability)",
        "navigation": "导航 (navigation)",
        "portability": "可移植性 (portability)",
        "labeling": "标签表达 (labeling)",
        "usability": "可用性 (usability)",
        "applicable": "适用 (applicable)",
        "architecture impact": "架构影响 (architecture impact)",
        "ia impact": "信息架构影响 (IA impact)",
        "blind spot 1": "盲点 1 (blind spot 1)",
        "blind spot 2": "盲点 2 (blind spot 2)",
        "blind spot 3": "盲点 3 (blind spot 3)",
        "blind spot 4": "盲点 4 (blind spot 4)",
        "why": "原因 (why)",
        "verdict": "结论 (verdict)",
        "rejected": "不选 (rejected)",
    }
)

FIELD_LABEL_MAP.update(
    {
        "owner": "负责人 (owner)",
        "derived_from_contract": "派生自契约 (derived_from_contract)",
        "intended_user": "目标使用者 (intended_user)",
        "downstream_usage_rule": "下游使用规则 (downstream_usage_rule)",
        "product value promise": "产品价值承诺 (product value promise)",
        "primary operator": "主要操作者 (primary operator)",
        "product context": "产品上下文 (product context)",
        "in scope": "范围内项 (in scope)",
        "forbidden assumption": "禁止假设 (forbidden assumption)",
        "from page": "起始页面 (from page)",
        "user goal": "用户目标 (user goal)",
        "system response": "系统响应 (system response)",
        "to page": "目标页面 (to page)",
        "context continuity": "上下文连续性 (context continuity)",
        "product purpose": "产品用途 (product purpose)",
        "primary actor": "主要角色 (primary actor)",
        "entry condition": "进入条件 (entry condition)",
        "secondary support regions": "次级支持区域 (secondary support regions)",
        "dominant component pattern": "主导组件模式 (dominant component pattern)",
        "action model": "动作模型 (action model)",
        "forbidden layout patterns": "禁止布局模式 (forbidden layout patterns)",
        "render blocks in order": "按顺序渲染的区块 (render blocks in order)",
        "primary cta label": "主要 CTA 文案 (primary cta label)",
        "secondary ctas": "次级 CTA (secondary CTAs)",
        "context arrives from": "上下文来源 (context arrives from)",
        "context must continue to": "上下文必须延续到 (context must continue to)",
        "required status messages": "必需状态消息 (required status messages)",
        "submission feedback the ui must make explicit": "界面必须显式给出的提交反馈 (submission feedback the UI must make explicit)",
        "page blueprint type": "页面蓝图类型 (page blueprint type)",
        "primary work region": "主工作区域 (primary work region)",
        "must visibly show together": "必须显式同时展示 (must visibly show together)",
        "required information blocks": "必需信息块 (required information blocks)",
        "field groups that must exist on the page": "页面上必须存在的字段分组 (field groups that must exist on the page)",
        "input controls to materialize": "需要实体化的输入控件 (input controls to materialize)",
        "summary cards or top-line badges to show": "需要展示的摘要卡片或顶部徽标 (summary cards or top-line badges to show)",
        "detail fields in reading order": "按阅读顺序展示的明细字段 (detail fields in reading order)",
        "table or list columns when tabular presentation is used": "使用表格或列表展示时的列定义 (table or list columns when tabular presentation is used)",
        "filters and selectors to expose": "需要暴露的筛选与选择器 (filters and selectors to expose)",
        "required user inputs / confirmations": "必需的用户输入 / 确认项 (required user inputs / confirmations)",
        "primary actions the ui must make operable": "界面必须可操作的主动作 (primary actions the UI must make operable)",
        "extra page-specific execution guardrails": "额外的页面级执行护栏 (extra page-specific execution guardrails)",
        "homepage / first screen requirements": "首页 / 首屏要求 (homepage / first screen requirements)",
        "language and terminology": "语言与术语 (language and terminology)",
        "required deliverables from the external ai run": "外部 AI 运行必须交付的内容 (required deliverables from the external AI run)",
        "acceptance checklist before you stop": "结束前的验收清单 (acceptance checklist before you stop)",
    }
)


TABLE_HEADER_MAP = {
    "artifact_id": "产物 ID (artifact_id)",
    "artifact_type": "产物类型 (artifact_type)",
    "file": "文件 (file)",
    "role": "角色 (role)",
    "goal": "目标 (goal)",
    "friction": "阻力 / 摩擦 (friction)",
    "first-wave responsibility": "首波职责 (first-wave responsibility)",
    "context": "情境 (context)",
    "main job": "核心任务 (main job)",
    "success signal": "成功信号 (success signal)",
    "failure consequence": "失败后果 (failure consequence)",
    "id": "编号 (id)",
    "persona / role": "Persona / 角色 (persona / role)",
    "trigger": "触发条件 (trigger)",
    "required outcome": "必需结果 (required outcome)",
    "anti-pattern to avoid": "需要避免的反模式 (anti-pattern to avoid)",
    "stakeholder": "干系人 (stakeholder)",
    "interest / concern": "关注点 / 顾虑 (interest / concern)",
    "success criteria": "成功标准 (success criteria)",
    "resistance pattern": "阻力模式 (resistance pattern)",
    "influence": "影响力 (influence)",
    "engagement approach": "介入方式 (engagement approach)",
    "module": "模块 (module)",
    "responsibility": "职责 (responsibility)",
    "input": "输入 (input)",
    "output": "输出 (output)",
    "architectural note": "架构说明 (architectural note)",
    "candidate": "候选项 (candidate)",
    "backbone shape": "骨干形态 (backbone shape)",
    "strength": "优势 (strength)",
    "failure risk": "失败风险 (failure risk)",
    "verdict": "判定 (verdict)",
    "problem cluster": "问题簇 (problem cluster)",
    "affected actor": "受影响角色 (affected actor)",
    "structure consequence": "结构后果 (structure consequence)",
    "why it belongs in Stage-02a": "为何归属于 Stage-02a (why it belongs in Stage-02a)",
    "process type": "流程类型 (process type)",
    "process name": "流程名称 (process name)",
    "primary owner": "主负责人 (primary owner)",
    "why it matters": "为何重要 (why it matters)",
    "activity": "活动 (activity)",
    "primary actor": "主角色 (primary actor)",
    "preconditions": "前置条件 (preconditions)",
    "system behavior": "系统行为 (system behavior)",
    "outputs": "输出项 (outputs)",
    "postconditions": "后置条件 (postconditions)",
    "attribute": "属性 (attribute)",
    "why prioritized now": "当前优先级原因 (why prioritized now)",
    "reverse risk if weak": "若弱化的反向风险 (reverse risk if weak)",
    "affected scenario": "受影响场景 (affected scenario)",
    "MVP consequence": "对 MVP 的影响 (MVP consequence)",
    "stimulus": "刺激条件 (stimulus)",
    "environment": "环境 (environment)",
    "expected response": "预期响应 (expected response)",
    "measure": "度量方式 (measure)",
    "metric": "指标 (metric)",
    "meaning": "含义 (meaning)",
    "first-wave use": "首波用途 (first-wave use)",
    "interpretation risk": "解读风险 (interpretation risk)",
    "mitigation": "缓解措施 (mitigation)",
    "dimension": "维度 (dimension)",
    "first-wave decision": "首波决策 (first-wave decision)",
    "rationale": "依据 (rationale)",
    "workflow step": "工作流步骤 (workflow step)",
    "primary object": "主对象 (primary object)",
    "secondary object": "次对象 (secondary object)",
    "downstream effect": "下游影响 (downstream effect)",
    "alternative": "备选项 (alternative)",
    "organizing axis": "组织轴 (organizing axis)",
    "screen/module": "页面 / 模块 (screen/module)",
    "required information objects": "所需信息对象 (required information objects)",
    "entry conditions": "进入条件 (entry conditions)",
    "exit actions": "退出动作 (exit actions)",
    "downstream dependency": "下游依赖 (downstream dependency)",
    "what_is_in_first_slice": "首个切片包含什么 (what_is_in_first_slice)",
    "user_value_speed": "用户价值速度 (user_value_speed)",
    "evidence_confidence": "证据置信度 (evidence_confidence)",
    "dependency_complexity": "依赖复杂度 (dependency_complexity)",
    "validation_leverage": "验证杠杆 (validation_leverage)",
    "risk_of_overreach": "过度承诺风险 (risk_of_overreach)",
    "contested capability": "有争议能力 (contested capability)",
    "value": "价值 (value)",
    "expected frequency": "预期频率 (expected frequency)",
    "first-slice decision": "首切片决策 (first-slice decision)",
    "reason": "原因 (reason)",
    "item": "条目 (item)",
    "why_not_in_mvp": "为何不进 MVP (why_not_in_mvp)",
    "what_would_falsely_make_mvp_look_complete": "什么会制造假完整感 (what_would_falsely_make_mvp_look_complete)",
    "impact_of_deferral": "延后影响 (impact_of_deferral)",
    "target": "目标 (target)",
    "exact_assumption_tested": "被精确验证的假设 (exact_assumption_tested)",
    "what_changes_if_positive": "若验证为正会改变什么 (what_changes_if_positive)",
    "what_changes_if_negative": "若验证为负会改变什么 (what_changes_if_negative)",
    "primary dimension": "主维度 (primary dimension)",
    "candidate method": "候选方法 (candidate method)",
    "fit_to_target": "与目标的匹配度 (fit_to_target)",
    "cost_and_speed": "成本与速度 (cost_and_speed)",
    "evidence_quality": "证据质量 (evidence_quality)",
    "why_not_chosen_or_chosen": "为何选 / 不选 (why_not_chosen_or_chosen)",
    "method": "方法 (method)",
    "artifact": "产物 (artifact)",
    "threshold": "阈值 (threshold)",
    "learning_if_pass": "若通过将学到什么 (learning_if_pass)",
    "learning_if_fail": "若未通过将学到什么 (learning_if_fail)",
    "risk": "风险 (risk)",
    "class": "类别 (class)",
    "likelihood": "可能性 (likelihood)",
    "impact": "影响 (impact)",
    "subject": "主题 (subject)",
    "delivery_readiness_state": "交付成熟度状态 (delivery_readiness_state)",
    "evidence_confidence_state": "证据置信状态 (evidence_confidence_state)",
    "current_basis": "当前依据 (current_basis)",
    "blocker_to_next_delivery_state": "升级到下一交付状态的阻断项 (blocker_to_next_delivery_state)",
    "blocker_to_next_evidence_state": "升级到下一证据状态的阻断项 (blocker_to_next_evidence_state)",
    "safe_downstream_action": "可安全启动的下游动作 (safe_downstream_action)",
    "forbidden_assumptions": "禁止的默认假设 (forbidden_assumptions)",
    "warning_level": "告警级别 (warning_level)",
    "warning_basis": "告警依据 (warning_basis)",
    "missing_external_confirmation": "缺失的外部确认 (missing_external_confirmation)",
    "current_document_position": "当前文档定位 (current_document_position)",
    "safe_current_use": "当前可安全使用方式 (safe_current_use)",
    "stronger_commitment_blocker": "更强承诺的阻断项 (stronger_commitment_blocker)",
}


TOKEN_MAP = {
    "downstream-start-safe": "可安全启动下游 (downstream-start-safe)",
    "implementation-commit-ready": "可进入实现承诺 (implementation-commit-ready)",
    "review-ready": "评审就绪 (review-ready)",
    "artifact-draft": "产物草稿 (artifact-draft)",
    "source-grounded-but-unvalidated": "基于素材但未外部验证 (source-grounded-but-unvalidated)",
    "design-time-inference-heavy": "设计期推断占主导 (design-time-inference-heavy)",
    "partially-signal-backed": "已有部分信号支撑 (partially-signal-backed)",
    "externally-validated": "已被外部验证 (externally-validated)",
    "contradicted": "已被证伪 (contradicted)",
    "warning-high": "高告警 (warning-high)",
    "warning-medium": "中告警 (warning-medium)",
    "warning-low": "低告警 (warning-low)",
    "watch-only": "观察项 (watch-only)",
    "PASS with constrained/review-bound conditions": "通过，但带受限 / 评审保留条件 (PASS with constrained/review-bound conditions)",
    "review-bound-starter-pack": "评审保留启动包 (review-bound-starter-pack)",
    "implementation-ready-prd": "实现就绪 PRD (implementation-ready-prd)",
    "provisional": "暂定 (provisional)",
    "mixed": "混合来源 (mixed)",
    "AI-INFERRED DRAFT — UNVERIFIED": "AI 推断草稿，尚未验证 (AI-INFERRED DRAFT — UNVERIFIED)",
}

TOKEN_MAP.update(
    {
        "ready-to-converge": "可收口 (ready-to-converge)",
    }
)


TERM_MAP = {
    "Tenant": "租户 (Tenant)",
    "tenant": "租户 (tenant)",
    "workflow prototype": "工作流原型 (workflow prototype)",
    "workflow": "工作流 (workflow)",
    "state machine": "状态机 (state machine)",
    "state transition": "状态迁移 (state transition)",
    "object chain": "对象链 (object chain)",
    "core object": "核心对象 (core object)",
    "core business object": "核心业务对象 (core business object)",
    "business object": "业务对象 (business object)",
    "interface contract": "接口契约 (interface contract)",
    "subsystem boundary": "子系统边界 (subsystem boundary)",
    "metric register": "指标登记表 (metric register)",
    "uncertainty note": "不确定性说明 (uncertainty note)",
    "transition guard": "状态转移守卫 (transition guard)",
    "value proposition": "价值主张 (value proposition)",
    "clickable prototype": "可点击原型 (clickable prototype)",
    "sample report": "样例报告 (sample report)",
    "reviewer": "评审者 (reviewer)",
    "appointment": "预约 (appointment)",
    "payment": "支付 (payment)",
    "invoice": "账单 (invoice)",
    "prescription": "处方 (prescription)",
    "clinical note": "临床记录 (clinical note)",
    "visit request": "就诊请求 (visit request)",
    "pet profile": "宠物档案 (pet profile)",
    "appointment slot": "预约时段 (appointment slot)",
    "workflow prototype": "工作流原型 (workflow prototype)",
}

INLINE_PHRASE_MAP = {
    "workflow story-map": "工作流故事地图 (workflow story-map)",
    "feature shelf": "功能货架 (feature shelf)",
    "workflow-first": "工作流优先 (workflow-first)",
    "automation-first": "自动化优先 (automation-first)",
    "dashboard-only": "仅仪表板 (dashboard-only)",
    "single-metric vanity product": "单指标虚荣型产品 (single-metric vanity product)",
    "must stay separable from UI": "必须与 UI 解耦 (must stay separable from UI)",
    "needs explicit rubric/versioning": "需要显式评分规则 / 版本化 (needs explicit rubric/versioning)",
    "cannot silently auto-execute in MVP": "在 MVP 中不得静默自动执行 (cannot silently auto-execute in MVP)",
    "should support manual confirmation": "应支持人工确认 (should support manual confirmation)",
    "must preserve uncertainty honesty": "必须保留不确定性诚实性 (must preserve uncertainty honesty)",
    "execution record": "执行记录 (execution record)",
    "main flow": "主流程 (main flow)",
    "variant flow": "变体流程 (variant flow)",
    "supporting": "支撑流程 (supporting)",
    "management": "管理流程 (management)",
    "task execution": "任务执行 (task execution)",
    "keep in first slice": "保留在首个切片 (keep in first slice)",
    "whole-picture": "全局视角 (whole-picture)",
    "problem-to-structure": "问题到结构 (problem-to-structure)",
    "backbone activities": "骨干活动 (backbone activities)",
    "review-bound truths": "评审保留真相 (review-bound truths)",
    "open truths": "开放真相 (open truths)",
    "priority context": "优先级上下文 (priority context)",
    "business decision": "业务决策 (business decision)",
    "launch-platform feasibility": "上线平台可行性 (launch-platform feasibility)",
    "metric stability": "指标稳定性 (metric stability)",
    "adjust focus": "调整关注点 (adjust focus)",
    "all scenarios": "所有场景 (all scenarios)",
    "clickable walkthrough": "可点击走查 (clickable walkthrough)",
    "commercial model and willingness-to-pay": "商业模式与付费意愿 (commercial model and willingness-to-pay)",
    "budget / priority decision": "预算 / 优先级决策 (budget / priority decision)",
    "approval / rejection": "批准 / 驳回 (approval / rejection)",
    "demand already validated": "需求已被验证 (demand already validated)",
    "metric trust fully validated": "指标信任度已被充分验证 (metric trust fully validated)",
    "willingness-to-pay already proven": "付费意愿已被证明 (willingness-to-pay already proven)",
    "automation can be safely attached to MVP": "自动化可以安全挂接到 MVP (automation can be safely attached to MVP)",
    "formal decision": "正式决策 (formal decision)",
    "detailed subject-level maturity/confidence ledger is preserved in PRD §19 and the convergence evidence memo": "详细的主题级成熟度 / 置信度台账保存在 PRD §19 与 convergence evidence memo 中 (detailed subject-level maturity/confidence ledger is preserved in PRD §19 and the convergence evidence memo)",
    "subject-level forbidden_assumptions remain binding; see PRD §19 and the convergence evidence memo": "主题级 forbidden_assumptions 仍然有效；见 PRD §19 与 convergence evidence memo (subject-level forbidden_assumptions remain binding; see PRD §19 and the convergence evidence memo)",
    "Product framing:": "产品 framing：",
    "You are designing a high-fidelity prototype for the product": "你正在为如下产品设计高保真原型",
    "Design objective:": "设计目标：",
    "Non-negotiable product truths:": "不可违背的产品事实：",
    "Allowed design exploration:": "允许的设计探索：",
    "Forbidden output patterns:": "禁止的输出模式：",
    "Workflow backbone that must remain operable:": "必须保持可操作的工作流骨架：",
    "Page contracts:": "页面契约：",
    "Homepage / first screen requirements:": "首页 / 首屏要求：",
    "Language and terminology:": "语言与术语：",
    "Required deliverables from the external AI run:": "外部 AI 运行必须交付的内容：",
    "Acceptance checklist before you stop:": "结束前的验收清单：",
    "Copy the prompt below into the external design / HTML generation system. Keep the non-negotiable contract intact.": "把下面的提示词复制到外部设计 / HTML 生成系统中，并保持其中不可违背的契约不被修改。",
    "This pack is for high-fidelity prototype generation outside the framework runtime.": "该提示包用于框架运行时之外的高保真原型生成。",
    "Do not treat it as a substitute for the implementation-facing contract.": "不要把它当作面向实现的正式契约替代品。",
    "Create a terminal-user-facing business application prototype, not a demo shell, API explorer, runtime console, acceptance dashboard, or stepper-driven showcase.": "创建一个面向终端业务用户的应用原型，而不是演示外壳、API Explorer、运行时控制台、验收看板或 stepper 式展示页。",
    "The prototype must feel like a usable product for the named operator on day one, even if styling remains MVP-level.": "即使视觉样式仍处于 MVP 水平，原型也必须让被点名的操作者在第一天就感到它是可用产品。",
    "Every primary page must let the user see the required business context and take the next workflow action directly on the page.": "每个主页面都必须让用户在页内看到所需业务上下文，并直接完成下一个工作流动作。",
    "You may choose visual hierarchy, spacing, component styling, typography, and layout treatment.": "你可以自主选择视觉层级、留白、组件样式、字体和布局处理方式。",
    "You may simplify the visual system for MVP delivery, but the output must still look and behave like a real product surface for business operators.": "为满足 MVP 交付，你可以简化视觉系统，但输出仍必须在观感和行为上像真实的业务产品界面。",
    "No API explorer framing.": "不要采用 API Explorer 式 framing。",
    "No debug console framing.": "不要采用调试控制台式 framing。",
    "No acceptance harness framing.": "不要采用验收 harness 式 framing。",
    "No homepage dominated by step cards, generic walkthrough cards, or engineering scaffolding language.": "首页不要被步骤卡片、通用走查卡片或工程脚手架式语言主导。",
    "No page that only dumps contracts or instructions without giving the user an operable surface.": "不要出现只堆契约或说明、却不给用户可操作界面的页面。",
    "Present the product explicitly as": "把产品明确呈现为",
    "Explain what workflow the product supports, who it serves, and where the operator should start.": "说明该产品支持什么工作流、服务谁，以及操作者应从哪里开始。",
    "The first screen must expose a real entry into the workflow, not only explanatory copy.": "首屏必须暴露真实的工作流入口，不能只有解释性文案。",
    "The first screen must feel like a product workbench or governed setup/dashboard, not a slideshow or demo launcher.": "首屏必须像产品工作台或受治理的设置 / 仪表板，而不是幻灯片或演示启动页。",
    "Keep upstream page names and domain nouns recognizable.": "保持上游页面名称和领域名词可辨识。",
    "Prefer business-facing copy over engineering copy.": "优先使用面向业务的文案，而不是工程化文案。",
    "Do not replace product nouns with generic labels such as workspace, module, panel, console, playground, or explorer.": "不要把产品名词替换成 workspace、module、panel、console、playground 或 explorer 这类泛化标签。",
    "A clickable multi-page prototype or a small multi-file HTML site.": "一个可点击的多页面原型，或一个小型多文件 HTML 站点。",
    "One homepage / entry page plus the full first-wave workflow pages.": "一个首页 / 入口页，加上完整的首波工作流页面。",
    "Real form controls for the required inputs or confirmations.": "把必需输入或确认项做成真实表单控件。",
    "Empty, loading, blocked, and error states on the pages where those states matter.": "在相关页面中显式呈现 empty、loading、blocked、error 状态。",
    "Visible carry-forward context when moving between dependent pages.": "在存在依赖的页面跳转之间，显式展示被带入的上下文。",
    "Confirm that the output reads like a business product for operators, not a framework demo.": "确认输出读起来像面向操作者的业务产品，而不是框架 demo。",
    "Confirm that each workflow page exposes both required data and the next user action.": "确认每个工作流页面同时暴露所需数据和下一步用户动作。",
    "Confirm that deferred and non-goal items are not silently promoted into the visible product.": "确认延后项和非目标项没有被静默提升为可见产品能力。",
    "Reviewers may iterate visual styling, hierarchy, and microcopy with the external AI.": "评审者可以与外部 AI 一起迭代视觉样式、信息层级和微文案。",
    "Reviewers must not break the contract in `prototype-spec.md` while refining high-fidelity output.": "在细化高保真输出时，评审者不得破坏 `prototype-spec.md` 中的契约。",
    "If external exploration reveals missing product truths, update the Phase-1/Phase-2 source artifacts rather than silently patching the prototype only.": "如果外部探索暴露出缺失的产品事实，应更新 Phase-1/Phase-2 源产物，而不是只对原型做静默补丁。",
    "This section is REQUIRED, not optional.": "本节为必填项，不是可选项。",
    "Make the first-wave workflow reviewable through page map, route graph, page briefs, and key-state coverage before external HTML execution begins.": "在外部 HTML 执行开始前，通过页面地图、路由图、页面简述和关键状态覆盖，让首波工作流具备可评审性。",
    "Workflow-first organization remains primary; support pages stay secondary to the main operating backbone.": "工作流优先的组织方式保持主导；支撑页面从属于主运营骨架。",
    "The prototype should keep the mainline route walkable while preserving multiple blocked or exception paths so review honesty is visible, not implied.": "原型应保持主线路径可走通，同时保留多个阻断或异常路径，让评审诚实性是可见的，而不是靠暗示。",
    "Supporting detail blocks are folded into their parent workflow objects instead of being modeled as standalone state machines.": "支撑性明细区块应折叠进其父级工作流对象，而不是被建模为独立状态机。",
    "The prototype executor may choose layout and styling, but must not invent new product capabilities, hidden states, or automation claims outside the first-wave boundary.": "原型执行者可以自主选择布局和样式，但不得在首波边界之外虚构新的产品能力、隐藏状态或自动化声明。",
    "Stage-05 keeps the first-wave workflow bounded to the primary operating loop. Deferred and explicit out-of-scope items remain visible so the prototype does not create false completeness.": "Stage-05 将首波工作流限定在主运营闭环之内。延后项和明确的范围外事项必须保持可见，避免原型制造出虚假的完整感。",
    "How much visual hierarchy and guidance is needed before onboarding friction becomes too high?": "在 onboarding 摩擦变得过高之前，需要多强的视觉层级和引导？",
    "Which state surfaces need the strongest emphasis in the prototype review round?": "在原型评审轮次中，哪些状态页面需要被最强调？",
    "no direct mainline neighbor is defined for this page in the current workflow backbone": "当前工作流骨架中没有为该页面定义直接的主线相邻页面",
    "preserve blocked or exception context where the workflow can stop or degrade.": "在工作流可能停止或降级的地方，保留阻断 / 异常上下文。",
    "This section is REQUIRED, not optional.": "本节是必需的，不是可选项。",
    "never use labels such as `API Explorer`, `Runtime Console`, `Acceptance Dashboard`, or `Demo Steps` as the dominant UX framing": "不要把 `API Explorer`、`Runtime Console`、`Acceptance Dashboard` 或 `Demo Steps` 之类的标签作为主导 UX framing",
    "treat the site as a business application named": "把该站点视为一个业务应用，名称为",
    "the first screen must explain what workflow the product supports, who it serves, and where the operator should start": "首屏必须说明产品支持什么工作流、服务于谁，以及操作者应从哪里开始",
    "every workflow page must expose the information needed to decide and the controls needed to continue, not just explanatory copy": "每个工作流页面都必须展示做决策所需的信息和继续推进所需的控件，不能只给解释性文案",
    "when a later page depends on earlier context, show the carried-forward context on arrival instead of resetting to an empty shell": "当后续页面依赖前文上下文时，到达页面后应展示被带入的上下文，而不是重置为空壳",
    "route from prior workflow step": "从前一工作流步骤路由进入",
    "a primary business work area": "一个主业务工作区",
    "a primary business work area for the current workflow step": "围绕当前工作流步骤展开的主业务工作区",
    "business work surface with one dominant action area": "具有一个主导动作区域的业务工作界面",
    "secondary support regions for status, trace, and follow-up": "用于状态、追踪和后续动作的次级支持区域",
    "page header": "页面页头",
    "core information block": "核心信息块",
    "next action block": "下一步动作区块",
    "workflow context": "工作流上下文",
    "primary action input group": "主动作输入分组",
    "current workflow status": "当前工作流状态",
    "next decision point": "下一个决策点",
    "primary object summary": "主对象摘要",
    "next-step context": "下一步上下文",
    "name": "名称",
    "status": "状态",
    "updated_at": "更新时间",
    "complete the current workflow action honestly": "如实完成当前工作流动作",
    "do not render the page as a contract checklist or schema viewer": "不要把页面做成契约清单或 schema 查看器",
    "do not make the dominant layout a stepper, wizard shell, or acceptance walkthrough": "不要让主布局变成 stepper、wizard 外壳或验收式走查",
    "do not separate the primary business object from the action needed to advance it": "不要把主要业务对象与推进它所需的动作拆开",
    "do not use a generic debug sidebar as the dominant right-hand rail": "不要把通用调试侧栏作为主导性的右侧栏",
    "Save draft": "保存草稿",
    "Return to previous step": "返回上一步",
    "primary selector": "主选择器",
    "page-specific rule to preserve:": "必须保留的页面级规则：",
    "as a business-facing surface, not as a generic placeholder screen": "作为一个面向业务的操作界面，而不是通用占位页",
    "page headings, labels, and CTAs should keep upstream domain nouns visible instead of collapsing into generic debug vocabulary": "页面标题、标签和 CTA 应保留上游领域名词的可见性，而不是塌缩成通用调试词汇",
    "the primary action on this page must be operable, not merely described": "该页面上的主动作必须可操作，而不只是被描述出来",
    "keep the upstream information objects explicit on the page:": "在页面上明确展示这些上游信息对象：",
    "the page must expose enough inputs or selections to complete the intended next action:": "页面必须暴露足够的输入或选择项，以完成预期的下一步动作：",
    "loading / empty / error / blocked states must be explicit": "必须显式呈现 loading / empty / error / blocked 状态",
    "success: preserve submitted context for the next workflow step": "成功：保留已提交上下文，并带入下一工作流步骤",
    "blocked: explain what still prevents progression": "阻断：说明当前仍是什么因素阻止继续推进",
    "priority": "优先级",
    "execution note": "执行备注",
    "threshold interpretation": "阈值解读",
    "support the user in completing:": "支持用户完成：",
    "primary actions on this page must make these next moves directly operable:": "该页面上的主动作必须让以下后续动作可以被直接操作：",
    "create task": "创建任务",
    "assign owner": "指派责任人",
    "continue": "继续",
    "severity": "严重级别",
    "recommended next action": "建议的下一步动作",
    "signal": "信号",
    "task": "任务",
    "state": "状态",
    "metric / signal": "指标 / 信号",
    "delta": "变化量",
    "source brief": "源素材（source brief）",
    "source material": "源素材（source material）",
    "reader-facing product document": "面向读者的产品文档",
    "source-defined": "源素材定义的（source-defined）",
    "field validation": "现场验证（field validation）",
    "real deployment readiness": "真实部署就绪",
    "production-safe or commercially validated": "生产安全或商业验证完成",
    "does not equal": "不等于",
    "loading:": "加载中：",
    "empty:": "空态：",
    "error:": "错误：",
    "blocked:": "阻断：",
    "success:": "成功：",
    "| control:": "| 控件：",
    "| required:": "| 必填：",
    "| purpose:": "| 用途：",
    "Machine-readable acceptance matrix:": "机器可读验收矩阵：",
    "Acceptance summary:": "验收摘要：",
    "(deep-compiled)": "（深度编译）",
}


def localize_fragmented_tool_gap(match: re.Match[str]) -> str:
    tool_set = match.group(1).strip()
    loop = match.group(2).strip()
    tool_set = re.sub(r",\s*or\s+", "、", tool_set, flags=re.IGNORECASE)
    tool_set = re.sub(r",\s*", "、", tool_set)
    return f"为什么分散的 {tool_set} 工具无法闭合完整的 {loop} 运营闭环"


REGEX_REPLACEMENTS = [
    (re.compile(r"\bStep (\d+)\b"), r"步骤 \1"),
    (re.compile(r"\bUse Case (\d+)\b"), r"用例 \1 (Use Case \1)"),
    (re.compile(r"\bScenario ([A-Z])\b"), r"场景 \1 (Scenario \1)"),
    (re.compile(r"\bSlice ([A-Z])\b"), r"切片 \1 (Slice \1)"),
    (re.compile(r"\bModule ([A-Z])\b"), r"模块 \1 (Module \1)"),
    (re.compile(r"\bException (\d+):"), r"异常 \1："),
    (re.compile(r"-> state:"), r"-> 状态:"),
    (
        re.compile(
            r"\bstakeholder evidence showing who funds or authorizes the next commitment,\s*"
            r"what spend is really at risk,\s*and what proof is sufficient to\s*(?:continue|继续)\b",
            re.IGNORECASE,
        ),
        "仍需补充谁出资或授权下一轮投入、真实投入成本是多少，以及什么证据足以支持继续",
    ),
    (re.compile(r"同一\s*review\s*面", re.IGNORECASE), "同一评审界面（review surface）"),
    (re.compile(r"\breview\s*面", re.IGNORECASE), "评审界面（review surface）"),
    (
        re.compile(r"`([^`]+)` must preserve (.+?) as product state, not as a loose workflow note\.?", re.IGNORECASE),
        r"`\1` 必须把 \2 保留为产品状态，而不是松散的工作流说明。",
    ),
    (
        re.compile(r"`([^`]+)` must turn (.+?) into NFR / acceptance evidence\.?", re.IGNORECASE),
        r"`\1` 必须把 \2 转成 NFR / 验收证据。",
    ),
    (
        re.compile(r"`([^`]+)` must keep (.+?) visible as the decision surface\.?", re.IGNORECASE),
        r"`\1` 必须让 \2 在决策界面保持可见。",
    ),
    (
        re.compile(r"`([^`]+)` must keep (.+?) attached to permission and accountability boundaries\.?", re.IGNORECASE),
        r"`\1` 必须让 \2 继续绑定权限与责任边界。",
    ),
    (
        re.compile(r"system must preserve the full object chain across `([^`]+)`", re.IGNORECASE),
        r"系统必须保留贯穿 `\1` 的完整对象链（object chain）",
    ),
    (
        re.compile(r"\bthe PRD recompiles source material into a reader-facing product document\.?", re.IGNORECASE),
        "本 PRD 将源素材重编为面向读者的产品文档。",
    ),
    (
        re.compile(r"\bsource brief gives explicit (.+?)\.?$", re.IGNORECASE),
        r"源素材（source brief）明确给出 \1。",
    ),
    (
        re.compile(r"\bthe current draft already proves real deployment readiness\.?", re.IGNORECASE),
        "当前草稿已经证明真实部署就绪。",
    ),
    (
        re.compile(r"the workflow must preserve (.+?) when (.+?) are unavailable", re.IGNORECASE),
        r"工作流必须在 \2 不可用时保留 \1",
    ),
    (
        re.compile(r"why can fragmented (.+?) tools not close the full (.+?) operating loop", re.IGNORECASE),
        localize_fragmented_tool_gap,
    ),
    (
        re.compile(r"if a downstream actor cannot proceed, the payload must preserve a clarification path\.?", re.IGNORECASE),
        "如果下游角色无法继续，载荷必须保留澄清路径。",
    ),
    (
        re.compile(
            r"carry forward the active (.+?) context from `(.+?)` into `(.+?)` so the operator does not need to reconstruct the workflow state after navigation"
        ),
        r"把当前激活的 \1 上下文从 `\2` 带到 `\3`，这样操作者在跳转后无需重新拼装工作流状态",
    ),
    (
        re.compile(
            r"carry the decision outcome and current object selection from `(.+?)` into `(.+?)` with enough visible context to preserve action order and workflow continuity"
        ),
        r"把决策结果和当前对象选择从 `\1` 带到 `\2`，并保留足够的显式上下文，以维持动作顺序和工作流连续性",
    ),
    (re.compile(r"^(\s*-\s+)Page (\d+):"), r"\1页面 \2："),
]

REGEX_LOCALIZED_PROTECTION_PATTERNS = (
    re.compile(r"用例 \d+ \(Use Case \d+\)"),
    re.compile(r"场景 [A-Z] \(Scenario [A-Z]\)"),
    re.compile(r"切片 [A-Z] \(Slice [A-Z]\)"),
    re.compile(r"模块 [A-Z] \(Module [A-Z]\)"),
    re.compile(r"[\u4e00-\u9fff][^()\n|`]{0,80}\([A-Za-z0-9][A-Za-z0-9 _/.-]{0,80}\)"),
    re.compile(r"[\u4e00-\u9fff][^（）\n|`]{0,80}（[A-Za-z0-9][A-Za-z0-9 _/.-]{0,80}）"),
)

PROTECTED_LITERAL_PHRASES = (
    "overview / findings / tasks / reports",
    "overview / findings / tasks / competitors / reports / settings",
    "overview / insights / work items / competitors / reports / settings",
    "task-review linkage",
    "work item-review linkage",
    "Review 没有 Task 状态输入",
    "Review 没有 work item 状态输入",
)

MACHINE_DELTA_LEDGER_FIELDS = {
    "source_evidence",
    "analytical_inference",
    "decision_or_tradeoff",
    "downstream_impact",
}

FIELD_LABEL_MAP = {normalize_lookup_key(key): value for key, value in FIELD_LABEL_MAP.items()}
TABLE_HEADER_MAP = {normalize_lookup_key(key): value for key, value in TABLE_HEADER_MAP.items()}
HEADING_BODY_MAP = {normalize_lookup_key(key): value for key, value in HEADING_BODY_MAP.items()}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def protect_existing_localized_segments(text: str, mapping: dict[str, str], prefix: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}
    localized_values = sorted({value for value in mapping.values() if value}, key=len, reverse=True)
    protected = text
    for localized in localized_values:
        placeholder = f"__{prefix}_{len(placeholders)}__"
        placeholders[placeholder] = localized
        protected = protected.replace(localized, placeholder)
    return protected, placeholders


def restore_protected_localized_segments(text: str, placeholders: dict[str, str]) -> str:
    restored = text
    for placeholder, localized in placeholders.items():
        restored = restored.replace(placeholder, localized)
    return restored


def protect_literal_phrases(text: str, phrases: tuple[str, ...], prefix: str) -> tuple[str, dict[str, str]]:
    protected = text
    placeholders: dict[str, str] = {}
    for phrase in sorted({item for item in phrases if item}, key=len, reverse=True):
        placeholder = f"__{prefix}_{len(placeholders)}__"
        placeholders[placeholder] = phrase
        protected = protected.replace(phrase, placeholder)
    return protected, placeholders


def protect_regex_localized_segments(text: str, prefix: str = "L10N_REGEX") -> tuple[str, dict[str, str]]:
    protected = text
    placeholders: dict[str, str] = {}
    for pattern in REGEX_LOCALIZED_PROTECTION_PATTERNS:
        def replacer(match: re.Match[str]) -> str:
            placeholder = f"__{prefix}_{len(placeholders)}__"
            placeholders[placeholder] = match.group(0)
            return placeholder

        protected = pattern.sub(replacer, protected)
    return protected, placeholders


def infer_dynamic_bilingual_map(text: str) -> dict[str, str]:
    if "|" in text or "`" in text:
        return {}
    if re.match(r"^\s*(?:[-*]|\d+\.)\s+", text):
        return {}

    inferred: dict[str, str] = {}
    for match in re.finditer(r"(?<!\S)([^\n()|`:]{1,80}?)\s*\(([^()\n|`:]{1,80})\)", text):
        localized, english = match.groups()
        localized = localized.strip().strip("：:;,，")
        english = english.strip()
        if not localized or not english:
            continue
        if any(token in localized for token in ("|", "`", ":")):
            continue
        if re.search(r"[\u4e00-\u9fff]", english):
            continue
        if not re.search(r"[\u4e00-\u9fff]", localized):
            continue
        if normalize_lookup_key(english) == normalize_lookup_key(localized):
            continue
        inferred.setdefault(english, f"{localized} ({english})")
    return inferred


def append_mirror_suffix(title: str) -> str:
    if "中文评审镜像 / zh-CN Audit Mirror" in title:
        return title
    return f"{title}（中文评审镜像 / zh-CN Audit Mirror）"


def looks_like_primary_locale_text(text: str) -> bool:
    lines = text.splitlines()
    if not lines:
        return False
    first_line = lines[0].strip()
    return "产品需求文档 (PRD)" in first_line or "原型规格说明" in first_line or "Phase-1 执行报告" in first_line


def mirror_existing_primary_locale_text(
    text: str,
    canonical_name: str,
    *,
    include_mirror_note: bool = True,
) -> str:
    lines = text.splitlines()
    if not lines:
        return text

    output: list[str] = []
    inserted_note = False
    for idx, raw in enumerate(lines):
        if idx == 0 and raw.startswith("# "):
            output.append(f"# {append_mirror_suffix(raw[2:].strip())}")
            if include_mirror_note:
                output.append("")
                output.extend(build_mirror_note(canonical_name))
                output.append("")
                inserted_note = True
            continue
        output.append(raw)

    if include_mirror_note and not inserted_note:
        output = [*build_mirror_note(canonical_name), "", *output]
    return "\n".join(output)


def localize_title(title: str) -> str:
    if title in TITLE_MAP:
        return f"{TITLE_MAP[title]}（中文评审镜像 / zh-CN Audit Mirror）"

    match = re.fullmatch(r"(Stage-\d+[A-Za-z]?)\s+Output\s+[—-]\s+(.+)", title)
    if match:
        stage_label, detail = match.groups()
        localized_detail = re.sub(r"\s+（深度编译）$", "（深度编译）", replace_phrases(detail, INLINE_PHRASE_MAP))
        return f"{stage_label} 产物 — {localized_detail}（中文评审镜像 / zh-CN Audit Mirror）"

    match = re.fullmatch(r"(.+?)\s+[—-]\s+Convergence Evidence Memo", title)
    if match:
        base = match.group(1).strip()
        return f"{base} 收敛证据备忘录 (Convergence Evidence Memo)（中文评审镜像 / zh-CN Audit Mirror）"

    updated = re.sub(
        r"\bProduct Requirements Document(?:\s*\(PRD\))?\b",
        "产品需求文档 (PRD)",
        title,
        flags=re.IGNORECASE,
    )
    if "产品需求文档 (PRD)" in title:
        updated = title
    elif updated == title:
        updated = re.sub(r"\bPRD\b", "产品需求文档 (PRD)", updated)
    if updated == title:
        updated = append_mirror_suffix(title)
    else:
        updated = append_mirror_suffix(updated)
    return updated


def localize_primary_title(title: str) -> str:
    if title in TITLE_MAP:
        return TITLE_MAP[title]

    match = re.fullmatch(r"(Stage-\d+[A-Za-z]?)\s+Output\s+[—-]\s+(.+)", title)
    if match:
        stage_label, detail = match.groups()
        localized_detail = re.sub(r"\s+（深度编译）$", "（深度编译）", replace_phrases(detail, INLINE_PHRASE_MAP))
        return f"{stage_label} 产物 — {localized_detail}"

    match = re.fullmatch(r"(.+?)\s+[—-]\s+Convergence Evidence Memo", title)
    if match:
        base = match.group(1).strip()
        return f"{base} 收敛证据备忘录 (Convergence Evidence Memo)"

    updated = re.sub(
        r"\bProduct Requirements Document(?:\s*\(PRD\))?\b",
        "产品需求文档 (PRD)",
        title,
        flags=re.IGNORECASE,
    )
    if "产品需求文档 (PRD)" in title:
        return title
    if updated == title:
        updated = re.sub(r"\bPRD\b", "产品需求文档 (PRD)", updated)
    return updated


def localize_heading_title(title: str) -> str:
    normalized_title = normalize_lookup_key(title)
    if title in HEADING_MAP:
        return HEADING_MAP[title]
    if normalized_title in HEADING_BODY_MAP:
        return f"{HEADING_BODY_MAP[normalized_title]} ({title})"

    match = re.fullmatch(r"Key-path Scenario (\d+)", title)
    if match:
        number = match.group(1)
        return f"关键路径场景 {number} (Key-path Scenario {number})"

    match = re.fullmatch(r"Scenario (\d+): (.+)", title)
    if match:
        number, body = match.groups()
        localized_body = HEADING_BODY_MAP.get(normalize_lookup_key(body), body)
        return f"场景 {number}：{localized_body} (Scenario {number}: {body})"

    match = re.fullmatch(r"Scenario Deep Dive ([A-Z]): (.+)", title)
    if match:
        label, body = match.groups()
        localized_body = HEADING_BODY_MAP.get(normalize_lookup_key(body), body)
        return f"场景深挖 {label}：{localized_body} (Scenario Deep Dive {label}: {body})"

    match = re.fullmatch(r"Reasoning Unit (\d+): (.+)", title)
    if match:
        number, body = match.groups()
        localized_body = HEADING_BODY_MAP.get(normalize_lookup_key(body), body)
        return f"推理单元 {number}：{localized_body} (Reasoning Unit {number}: {body})"

    return title


def localize_heading_line(line: str) -> str:
    match = re.match(r"^(#{1,6}\s+)(\d+\.\s+)?(.+?)\s*$", line)
    if not match:
        return line
    prefix, number, title = match.groups()
    localized = localize_heading_title(title.strip())
    return f"{prefix}{number or ''}{localized}".rstrip()


def localize_field_label_line(line: str) -> str:
    match = re.match(r"^(\s*-\s+)([^:]{1,120}?)(:\s*.*)$", line)
    if not match:
        return line
    prefix, label, suffix = match.groups()
    localized = FIELD_LABEL_MAP.get(normalize_lookup_key(label))
    if not localized:
        return line
    return f"{prefix}{localized}{suffix}"


def is_machine_delta_ledger_field_line(line: str) -> bool:
    match = re.match(r"^\s*-\s+([^:]{1,120}?):", line)
    return bool(match and normalize_lookup_key(match.group(1)) in MACHINE_DELTA_LEDGER_FIELDS)


def is_h2_heading_line(line: str) -> bool:
    return bool(re.match(r"^##\s+", line)) and not re.match(r"^###\s+", line)


def is_analysis_delta_ledger_heading(line: str) -> bool:
    return bool(re.match(r"^##\s+(?:\d+\.\s+)?[^\n]*Analysis Delta Ledger[^\n]*$", line, flags=re.IGNORECASE))


def localize_table_header_line(line: str) -> str:
    if not line.lstrip().startswith("|"):
        return line
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    localized = [TABLE_HEADER_MAP.get(normalize_lookup_key(cell), cell) for cell in cells]
    return "| " + " | ".join(localized) + " |"


def replace_exact_tokens(text: str, mapping: dict[str, str]) -> str:
    ordered = sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True)
    text, regex_protected = protect_regex_localized_segments(text, "L10N_TOKEN_REGEX")
    text, protected = protect_existing_localized_segments(text, mapping, "L10N_EXISTING_TOKEN")
    placeholders: dict[str, str] = {}
    for raw, localized in ordered:
        placeholder = f"__L10N_TOKEN_{len(placeholders)}__"
        placeholders[placeholder] = localized
        text = re.sub(
            rf"(?<![A-Za-z0-9_./-]){re.escape(raw)}(?![A-Za-z0-9_./-])",
            placeholder,
            text,
        )
    for placeholder, localized in placeholders.items():
        text = text.replace(placeholder, localized)
    text = restore_protected_localized_segments(text, protected)
    return restore_protected_localized_segments(text, regex_protected)


def replace_phrases(text: str, mapping: dict[str, str]) -> str:
    ordered = sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True)
    text, regex_protected = protect_regex_localized_segments(text, "L10N_PHRASE_REGEX")
    text, protected = protect_existing_localized_segments(text, mapping, "L10N_EXISTING_PHRASE")
    placeholders: dict[str, str] = {}
    for raw, localized in ordered:
        placeholder = f"__L10N_PHRASE_{len(placeholders)}__"
        placeholders[placeholder] = localized
        pattern = re.escape(raw)
        if raw and raw[0].isalnum():
            pattern = rf"(?<![A-Za-z0-9_]){pattern}"
        if raw and raw[-1].isalnum():
            pattern = rf"{pattern}(?![A-Za-z0-9_])"
        text = re.sub(pattern, placeholder, text)
    for placeholder, localized in placeholders.items():
        text = text.replace(placeholder, localized)
    text = restore_protected_localized_segments(text, protected)
    return restore_protected_localized_segments(text, regex_protected)


def localize_inline_line(line: str) -> str:
    dynamic_map = infer_dynamic_bilingual_map(line)
    localized, protected_regex = protect_regex_localized_segments(line)
    localized, protected_literals = protect_literal_phrases(localized, PROTECTED_LITERAL_PHRASES, "L10N_LITERAL")
    for pattern, replacement in REGEX_REPLACEMENTS:
        localized = pattern.sub(replacement, localized)
    localized = replace_exact_tokens(localized, TOKEN_MAP)
    localized = replace_exact_tokens(localized, TERM_MAP)
    if dynamic_map:
        localized = replace_exact_tokens(localized, dynamic_map)
        localized = replace_phrases(localized, dynamic_map)
    localized = replace_phrases(localized, INLINE_PHRASE_MAP)
    localized = restore_protected_localized_segments(localized, protected_literals)
    return restore_protected_localized_segments(localized, protected_regex)


def build_mirror_note(canonical_name: str) -> list[str]:
    return [
        "> 中文评审镜像（zh-CN audit mirror）",
        f"> canonical_of: `{canonical_name}`",
        "> 规则: 关键领域对象、状态枚举与交接术语保持中英双语；若中英语义冲突，以英文 canonical 为准。",
    ]


def localize_text(
    text: str,
    canonical_name: str,
    *,
    include_mirror_note: bool = True,
    include_mirror_suffix: bool = True,
) -> str:
    if include_mirror_suffix and looks_like_primary_locale_text(text):
        return mirror_existing_primary_locale_text(
            text,
            canonical_name,
            include_mirror_note=include_mirror_note,
        )

    lines = text.splitlines()
    output: list[str] = []
    inserted_note = False
    in_machine_delta_ledger = False

    for idx, raw in enumerate(lines):
        line = raw
        if idx == 0 and line.startswith("# "):
            title = line[2:].strip()
            output.append(f"# {localize_title(title) if include_mirror_suffix else localize_primary_title(title)}")
            if include_mirror_note:
                output.append("")
                output.extend(build_mirror_note(canonical_name))
                output.append("")
                inserted_note = True
            continue

        if re.match(r"^#{1,6}\s+", line):
            if is_h2_heading_line(line):
                in_machine_delta_ledger = is_analysis_delta_ledger_heading(line)
            output.append(localize_heading_line(line))
            continue

        if not (in_machine_delta_ledger and is_machine_delta_ledger_field_line(line)):
            line = localize_field_label_line(line)
        line = localize_table_header_line(line)
        line = localize_inline_line(line)
        output.append(line)

    if include_mirror_note and not inserted_note:
        output = [*build_mirror_note(canonical_name), "", *output]

    return "\n".join(output)


def render_primary_locale_lines(
    lines: list[str],
    canonical_name: str,
    locale: str | None,
    *,
    preserve_table_body_literals: bool = False,
) -> list[str]:
    if str(locale or "").strip() != "zh-CN":
        return list(lines)

    output: list[str] = []
    flattened: list[str] = []
    in_machine_delta_ledger = False
    for raw in lines:
        parts = str(raw).splitlines()
        if not parts:
            flattened.append("")
            continue
        flattened.extend(parts)

    for idx, raw in enumerate(flattened):
        line = raw
        if idx == 0 and line.startswith("# "):
            output.append(f"# {localize_primary_title(line[2:].strip())}")
            continue
        if re.match(r"^#{1,6}\s+", line):
            if is_h2_heading_line(line):
                in_machine_delta_ledger = is_analysis_delta_ledger_heading(line)
            output.append(localize_heading_line(line))
            continue
        if not (in_machine_delta_ledger and is_machine_delta_ledger_field_line(line)):
            line = localize_field_label_line(line)
        line = localize_table_header_line(line)
        if preserve_table_body_literals and line.strip().startswith("|"):
            output.append(line)
            continue
        line = localize_inline_line(line)
        output.append(line)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate zh-CN audit mirror for the Phase-1 PRD")
    parser.add_argument("--canonical-prd", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    canonical_path = Path(args.canonical_prd).resolve()
    output_path = Path(args.output).resolve()
    text = read_text(canonical_path)
    localized = localize_text(text, canonical_path.name)
    write_text(output_path, localized)

    print("== Phase-1 PRD zh-CN Mirror ==")
    print(f"canonical_prd: {canonical_path}")
    print(f"zh_prd: {output_path}")
    print("FINAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
