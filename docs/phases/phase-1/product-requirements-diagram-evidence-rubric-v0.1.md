# 产品 / 需求阶段：Diagram Evidence Rubric（v0.1）

目的：把“UML / Mermaid required”落到需求阶段的可执行标准：**画什么**、**最小元素**、**通过/退回规则**。

注意：需求阶段不追求严格 UML 完整性。这里的 diagram 是“结构证据”，不是设计交付。

与 gate 的绑定：见 `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`。

---

## 0. 总原则

1. **Mermaid 优先**：它是可复制、可审计、可 diff 的文本证据。
2. **可降级到表格**：当 Mermaid 不可用时，允许用结构化表格替代，但必须包含同等“最小元素”。
3. **Required 才进入 gate 判定**：`recommended/optional` 不作为出口 gate 的硬条件，但仍建议产出以降低下游摩擦。

---

## 1. diagram_type 词汇表（v0.1）

### 1.1 `story-map`（需求全景 / 故事地图）

适用：Stage-02（required），Stage-03（作为输入）

Mermaid 建议：`flowchart TD` 或 `mindmap`（若环境支持）

最小元素（required 时必须具备）：

- Backbone activities ≥ 3
- 每个 activity 下 tasks ≥ 2
- 标注“主干流程”（例如用 `*` 或 `[MAIN]` 标注）
- 至少 1 个关键边界/排除项（Out of scope 或 Not-now）
- 至少 1 个高风险待验证点（供 Stage-04 使用）

Fail（不通过）判定：

- 只有 story 条目列表，没有活动/任务层级结构

退回动作：

- Stage-02：回到“建立需求全景图”步骤，补结构后再继续

---

### 1.2 `requirements-structure`（结构化需求视图）

适用：Stage-02（可与 story-map 二选一，但至少要有一个 required 结构证据）

表达方式：

- Mermaid flowchart（目标→活动→任务→约束）
- 或表格：目标/活动/任务/约束四列

最小元素：

- 目标（Goal）至少 1 个
- 活动（Activity）至少 3 个
- 约束（Constraint）至少 3 条，且能关联到活动/任务

---

### 1.3 `slice-map`（MVP 切片结构图）

适用：Stage-03（required）

表达方式：

- Mermaid flowchart（Slice-0/1/2 + 依赖）
- 或表格：切片/能力边界/验收目标/依赖/暂缓项

最小元素（required 时必须具备）：

- 至少 2 个切片
- 每个切片都写出：能力边界 + 验收目标 + 关键依赖
- 明确暂缓项/拒绝项（及原因）

Fail 判定：

- 只写“第一期做 A/B/C”，没有切片边界与验收目标

退回动作：

- Stage-03：回到“识别完整体验闭环 / 切出最小可用体验”步骤

---

### 1.4 `validation-flow`（验证流程/实验闭环图）

适用：Stage-04（recommended）

表达方式：

- Mermaid flowchart（假设→验证方式→指标阈值→结果→决策→回灌点）
- 或表格：假设/方式/阈值/结果/决策/回灌字段

最小元素（当你把 Stage-04 的出口 gate 强化为“必须可进入设计/架构”时才升级为 required）：

- 假设 ≥ 1
- 每条假设有明确的“验证方式”与“判定阈值/信号”
- 有明确决策输出（Go / No-Go / Revise）

---

### 1.5 `actor-map`（干系人/角色图）

适用：Stage-01（optional / recommended，按项目复杂度）

最小元素：

- 关键角色 ≥ 3
- 角色之间至少 2 条关系（影响/审批/使用/提供数据）

---

## 2. v0.1 的“最小准入”建议（把图示门槛定得足够轻）

如果你希望在不显著加重文档负担的前提下仍然可判定：

- 强制（required）：Stage-02 的 `story-map` 或 `requirements-structure`（二选一）、Stage-03 的 `slice-map`
- 推荐（recommended）：Stage-04 的 `validation-flow`
- 可选（optional）：Stage-01 的 `actor-map`
