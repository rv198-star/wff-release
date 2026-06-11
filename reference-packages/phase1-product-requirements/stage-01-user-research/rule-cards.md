# Stage-01 Rule Cards — requirements-user-research

## 使用说明

本文件只记录原子规则，不直接写 prose 段落。每条规则尽量只表达一个断言。

---

## RC-01
- statement：Stage-01 的目标是形成可信的用户理解与问题定义输入，而不是直接定义产品方案。
- type：requirement
- source：`reference-packages/phase1-product-requirements/stage-01-user-research/skill-contract.md`
- source_tier：Tier 4
- confidence：medium-high
- applies_to_stage：Stage-01

## RC-02
- statement：若无业务机会描述或研究对象不清，则拒绝进入 Stage-01 正式执行。
- type：prohibition
- source：`docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-03
- statement：Stage-01 必须输出用户群边界，而不是泛化人群标签。
- type：requirement
- source：`docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-04
- statement：Stage-01 必须至少形成一版 User Case / User Story 草案。
- type：requirement
- source：`docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-05
- statement：Stage-01 必须形成结构化的问题 / 机会清单，且每条至少包含对象、痛点、证据来源。
- type：requirement
- source：`docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-06
- statement：Stage-01 的输出必须能被 Stage-02 直接消费，即回答“要结构化什么、为谁、为什么”。
- type：requirement
- source：`docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-07
- statement：Stage-01 图示不是 hard gate，但无图时必须有结构化表格替代。
- type：requirement
- source：`docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-08
- statement：Stage-01 默认应采用 Clarification Active → Blocked / Provisional Inference / Gate Pass 的状态机推进，而不是自由聊天。
- type：requirement
- source：`docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-09
- statement：AI 可以生成 provisional draft，但不得把 inferred 内容伪装成 confirmed input。
- type：prohibition
- source：`docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-10
- statement：所有 provisional artifact 必须显式标记 status / source / confidence / verification。
- type：requirement
- source：`docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-11
- statement：Stage-01 的 intake 行为优先参考 PM Skills 的 guided/context dump/best guess facilitation pattern。
- type：heuristic
- source：`docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-12
- statement：Stage-01 在方法内容上优先看 `product-demand-fit`、`behind-the-scenes-product`、`inspired`、`lean-product-development` 四个 source bundles。
- type：requirement
- source：`docs/internal/source-registers/product-requirements-source-index.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-13
- statement：`product-demand-fit` 负责补强研究执行、问题框定、洞察推理与机会形成。
- type：heuristic
- source：`docs/internal/source-registers/product-requirements-source-index.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-14
- statement：`behind-the-scenes-product` 负责补强用户理解、用户分群与产品判断能力。
- type：heuristic
- source：`docs/internal/source-registers/product-requirements-source-index.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-15
- statement：`inspired` 负责补产品定义边界与探索优先原则，避免过早沉入方案细节。
- type：heuristic
- source：`docs/internal/source-registers/product-requirements-source-index.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-16
- statement：`lean-product-development` 负责提供原则/治理约束，不应直接下沉成 Stage-01 的细节模板。
- type：boundary
- source：`sources/books/extracted/lean-product-development/alignment-review.md`
- source_tier：Tier 3
- confidence：high
- applies_to_stage：Stage-01

## RC-17
- statement：Stage-01 应优先吸收“直接研究用户”和“快速划分用户群”两类方法资产。
- type：requirement
- source：`reference-packages/phase1-product-requirements/stage-01-user-research/source-cards.md`
- source_tier：Tier 4
- confidence：medium-high
- applies_to_stage：Stage-01

## RC-18
- statement：多角色决策链、复杂组织协作或高影响面出现时，干系人分析表应作为可选增强包启用。
- type：exception
- source：`docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-19
- statement：Stage-01 的 `cannot_infer` 至少包括目标用户核心边界、关键业务目标方向、真实约束边界。
- type：requirement
- source：`docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01

## RC-20
- statement：Stage-01 可 provisional infer 的内容包括 proto-persona、User Case / User Story 初稿、问题/机会清单初稿。
- type：requirement
- source：`docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- source_tier：Tier 1
- confidence：high
- applies_to_stage：Stage-01
