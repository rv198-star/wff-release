# 产品 / 需求阶段：Gate、必选/可选与最小准入（v0.1）

目的：把“产品 / 需求阶段（4 个逻辑 Stage Skills / 5 个运行时执行包）”从**有骨架**推进到**可执行、可判定、可交接**。

本文件不追求一次性完美；它的目标是让执行者（人或 Agent）在信息不完整时也能：

- 知道哪些是 **必选（required）**，哪些是 **可选（optional）**
- 知道每一阶段的 **入口 gate / refusal / 出口 gate**
- 知道不满足时 **退回到哪一步、补什么证据**

依据：

- `docs/phases/phase-1/product-requirements-stage-package-v0.md`
- `reference-packages/phase1-product-requirements/*/skill-contract.md`
- `reference-packages/phase1-product-requirements/*/stage-sop.md`
- repo 原则：`README.md`（artifact-first、gate/refusal/handoff 明确化、UML/Mermaid required）

---

## 0. 统一约定（适用于 4 个逻辑子阶段 / 当前 5 个运行时执行包）

### 0.1 必选字段（所有阶段的输出物都必须显式写出）

> 这是一组“可交接最小字段集”。不要求立刻做到全链路 traceability，但必须显式化，避免下游无法消费。

- `status`: `draft | review | approved`
- `assumptions`: 列出当前仍未验证、但被当作前提的假设（可为空数组，但不能缺失字段）
- `open_questions`: 列出会影响下游判断的未决问题（可为空数组，但不能缺失字段）
- `handoff_to`: 下游阶段/角色（例如 `stage-03-requirements-decomposition` 或 “设计/架构阶段”）
- `handoff_package`: 交接包清单（以 bullet list 给出）

### 0.2 图示策略（不把图当装饰）

每个阶段都要声明：

- `diagram_obligation`: `required | recommended | optional`
- `diagram_type`: （见 `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`）
- `diagram_minimum_elements`: 当 obligation 为 `required` 时必填
- `fail_action`: 图示不满足时如何退回（refuse / return_to_previous_stage / request_missing_input）

注意：需求阶段图示不要求“严格 UML”；Mermaid 只是推荐的**可复制文本证据载体**。当 Mermaid 不可用时，允许用“结构化表格”替代，但必须满足同等的最小元素。

---

## 1. Stage-01：需求调研 / 用户理解（`requirements-user-research`）

### 1.1 必选输出（required）

- 调研记录（结构化结论，不是原始素材堆）
- 用户群划分草案
- `User Case / User Story` 草案（至少一版）
- 关键问题 / 机会清单

### 1.2 可选输出（optional，按触发条件启用）

- 干系人分析表（触发：多角色决策链 / 复杂组织协作 / 高影响面）

### 1.3 入口 gate（启动条件）

required：

- 已明确“研究目标/研究对象/业务机会描述”中的至少两项
- 有可引用的输入证据：用户反馈/数据/访谈线索/市场信息任一

refusal（拒绝/退回）：

- 若无业务机会描述或研究对象不清：拒绝进入调研执行，先要求明确研究目标（参见示例 `stage-01-user-research/skill-contract.md`）

### 1.4 出口 gate（最小完成标准 / DoD）

必须同时满足：

- 用户群边界已写出（不是“泛人群”标签）
- 至少一版 User Case / User Story 草案
- 问题/机会清单为结构化条目（每条至少包含：对象/痛点/证据来源）
- 输出可被 Stage-02a 消费（能回答“要结构化什么、为谁、为什么”）

### 1.5 图示要求

- `diagram_obligation`: `optional`
- 推荐图类型：`actor-map` 或 `opportunity-segmentation-map`
- 若不画图：必须用表格替代（用户群×目标×痛点×证据来源）

---

## 2. Stage-02a：需求结构分析（`requirements-structural-analysis`）

### 2.1 必选输出（required）

- 需求结构分析说明
- 需求全景图 / 故事地图（或同等结构化视图）
- 关键约束清单
- 优先级初稿（至少分成：高价值优先 / 高风险待验证 / 可延后）

### 2.2 入口 gate（启动条件）

required：

- 有 Stage-01 的结构化结论：用户群 + 关键问题（参见示例 `stage-02-requirements-analysis/skill-contract.md`）
- 业务目标/产品目标已给出（可粗，但必须显式）

refusal（拒绝/退回）：

- 缺少基础调研结论则退回上阶段补足共享理解（参见示例 `stage-02-requirements-analysis/stage-sop.md`）

### 2.3 出口 gate（最小完成标准 / DoD）

必须同时满足：

- 全景结构已建立（能从“目标→活动→任务→约束”走通）
- 主干流程已明确（至少 1 条 end-to-end 主干）
- 关键约束已识别（且与目标/任务区分清楚）
- 输出可供 Stage-02b / Stage-03 消费（能回答“按什么结构深化、按什么结构拆、边界在哪、风险在哪”）

常见失败信号（直接 FAIL）：

- 只有用户故事条目，没有全景结构（参见示例 `stage-02-requirements-analysis/stage-sop.md`）

### 2.4 图示要求

- `diagram_obligation`: `required`
- `diagram_type`: `story-map` 或 `requirements-structure`
- `fail_action`: `return_to_stage-02a step-1`（补全景结构）或 `return_to_stage-01`（补用户群与关键问题结构）

最小元素（必须具备）：

- ≥ 3 个主干活动（Backbone activities）
- 每个活动下 ≥ 2 个任务（tasks）
- 标注“主干流程”与至少一处“关键边界/排除项”
- 至少标注 1 个“高风险待验证点”（供 Stage-04 消费）

---

## 3. Stage-02b：需求规格深化（`requirements-specification-deepening`）

### 3.1 必选输出（required）

- NFR / 质量需求分析
- 领域对象 / 域模型方向
- 信息架构方向
- 指标定义与解释口径

### 3.2 入口 gate（启动条件）

required：

- Stage-02a 的全景结构、主干流程、约束与优先级已形成
- 当前项目需要把 PRD 交给设计 / 架构而不是停留在结构全景层

refusal（拒绝/退回）：

- 若 Stage-02a 全景仍不稳定，则退回 Stage-02a 补结构，而不是直接发明 NFR/对象/IA

### 3.3 出口 gate（最小完成标准 / DoD）

必须同时满足：

- 至少形成一版 NFR / 质量需求判断，且能解释为什么这些属性现在重要
- 至少形成一版对象链 / 域模型方向，供架构理解核心实体与关系
- 至少形成一版 IA 方向，供设计理解页面/模块/导航组织
- 输出可供 Stage-03 切片与最终 PRD convergence 消费，而不必重新发明规格级约束

常见失败信号（直接 FAIL）：

- 只有“以后再考虑 NFR/对象/IA”的口头占位，没有任何结构化输出
- 领域对象、指标口径、页面组织仍完全由下游猜

### 3.4 图示要求

- `diagram_obligation`: `required`
- `diagram_type`: `conceptual-er | information-architecture-structure`
- `fail_action`: `return_to_stage-02b step-1`（补对象/IA 结构）或 `return_to_stage-02a`（若上游全景本身不稳）

最小元素（必须具备）：

- ≥ 5 个核心业务对象或等价对象簇
- 至少 1 条对象主链（例如 `scope -> observation -> finding -> task -> review`）
- 至少 1 份页面/模块/导航组织方向
- 至少 1 组关键指标定义或解释口径

---

## 4. Stage-03：需求拆解 / MVP 切片（`requirements-decomposition-and-mvp-slicing`）

### 4.1 必选输出（required）

- MVP 定义（最小可用体验闭环）
- 发布切片说明（首批/后续/暂缓项）
- 需求拆解结果（可用 story map 标注或拆解表表达）

### 4.2 入口 gate（启动条件）

required：

- Stage-02a 的全景结构/故事地图存在
- Stage-02b 的规格深化输出存在，至少覆盖 NFR / 域模型 / IA 方向
- 产品目标/交付目标存在

refusal（拒绝/退回）：

- 未形成全景结构则拒绝切片（参见示例 `stage-03-requirements-decomposition/stage-sop.md`）

### 4.3 出口 gate（最小完成标准 / DoD）

必须同时满足：

- 已形成“最小可用体验闭环”（闭环要显式写出：触发→关键动作→反馈/结果）
- 切片逻辑可解释（为什么这样切、风险在哪里、依赖是什么）
- 首批/后续/暂缓项明确，且“暂缓项”不为空（如果确实没有暂缓项，必须解释原因）

### 4.4 图示要求

- `diagram_obligation`: `required`
- `diagram_type`: `slice-map`
- `fail_action`: `return_to_stage-03 step-1`（补闭环与切片逻辑）

最小元素（必须具备）：

- ≥ 2 个切片（Slice-0/1 或 First/Next）
- 每个切片至少包含：能力边界、验收目标、关键依赖
- 明确“暂缓项/拒绝项”（以及原因）

---

## 5. Stage-04：需求验证 / 概念验证（`requirements-validation-and-concept-proof`）

### 5.1 必选输出（required）

- 假设验证结论（必须可解释：基于什么证据得出什么结论）
- 验证记录（验证方式、样本/反馈、关键发现）
- 修订建议（回灌到 Stage-02a / Stage-02b / Stage-03 的哪些部分）

### 5.2 可选输出（optional）

- 低保真 / 概念原型说明（当验证方式需要原型时启用；否则可用“流程走查脚本/问题清单”替代）

### 5.3 入口 gate（启动条件）

required：

- 已明确待验证对象：假设/风险/关键决策点

refusal：

- 没有明确待验证对象则拒绝启动（参见示例 `stage-04-requirements-validation/stage-sop.md`）
- 若无明确假设，则拒绝进入验证阶段（参见示例 `stage-04-requirements-validation/skill-contract.md`）

### 5.4 出口 gate（最小完成标准 / DoD）

必须同时满足：

- 已形成验证结论（Go / No-Go / Revise 三选一，或等价判定）
- 已说明结论将如何影响：MVP 边界 / 切片顺序 / 约束 / 优先级
- 交接给“设计/架构阶段”的 handoff 包包含：结论、原型或替代证据、修订建议

### 5.5 图示要求

- `diagram_obligation`: `recommended`
- `diagram_type`: `validation-flow`
- 允许用表格替代：假设→验证方式→阈值→结果→决策

---

## 6. v0.1 的适用边界

- 本文件优先保证“产品/需求→设计/架构”的主链能稳定 handoff。
- 不在 v0.1 强制：完整的编号体系落地、SQLite 索引、全生命周期 trace matrix。
- 后续增强点：把 `docs/governance/artifact-traceability-layer-v0.md` 的字段（implements/verifies/feeds 等）逐步纳入各阶段输出模板的必填字段。
