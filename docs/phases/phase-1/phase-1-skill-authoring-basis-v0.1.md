# 第一阶段（产品 / 需求）Skill Authoring Basis（v0.1）

## 目的

本文件定义第一阶段（产品 / 需求）正式编写 Stage Skills 时的统一编写基座。

它解决的问题不是“某个阶段具体怎么写”，而是：

- 4 个子阶段应该共享什么
- 每个 Stage Skill 应按什么顺序编写
- 先做哪几项，才能最快得到可执行的第一批成果

本文件是从以下文档收束而来：

- `docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md`
- `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`
- `templates/skill-contract.md`
- `templates/stage-sop.md`
- `templates/output-template.md`
- `templates/handoff-checklist.md`
- `templates/handoff-contract.md`

---

## 1. 第一阶段 4 个 Stage Skills

当前第一阶段固定为以下 4 个逻辑子阶段；其中 Stage-02 当前在运行时拆成 `02a + 02b`：

1. `requirements-user-research`
2. `requirements-structural-analysis`（Stage-02a）
3. `requirements-specification-deepening`（Stage-02b）
4. `requirements-decomposition-and-mvp-slicing`
5. `requirements-validation-and-concept-proof`

这 4 个 Stage Skills 的共同目标不是“分别产出四份孤立文档”，而是共同形成一条稳定的：

> **用户意图 → 问题结构化 → 需求结构化 → MVP 切片 → 验证收口 → 进入设计/架构阶段 handoff**

---

## 1.1 Phase-1 正式运行不是手工串 Stage

必须区分两件事：

- Stage Skill 的 authoring / audit / debug
- Phase-1 真实案例的正式交付运行

当前官方运行入口应是：

- `scripts/phase1/run_phase1_full_trial.py`
- `scripts/phase1/run_phase1_convergence.py`

它们负责把：

- deep stage generation
- PRD assembly
- PRD convergence
- convergence gates
- execution report

串成一个项目级闭环。

硬规则：

- 手工按各 Stage 的 `output-template.md` 直接填正文，只能算 `authoring / audit / targeted remediation`
- 如果没有经过 full-trial orchestration 与 gates，就不应把结果声明为正式 Phase-1 交付物

---

## 2. 所有 Phase-1 Stage Skills 必须共享的基础能力

每个 Stage Skill 都必须显式继承：

### 2.1 Intake 继承项
- 支持 `Guided / Context dump / Best guess`
- 支持 `S0` 到 `S6` 的状态机约束
- 支持 `cannot_infer / can_provisionally_infer / must_validate_before_exit`

### 2.2 治理继承项
- 明确 required / optional outputs
- 明确 entry gate / refusal / exit gate
- 明确 handoff package
- 明确 provisional 内容能否进入下游

### 2.3 输出继承项
- `status`
- `assumptions`
- `open_questions`
- `source`
- `confidence`
- `verification`
- `handoff_to`
- `handoff_package`
- `core_deliverables_covered`
- `core_deliverables_pending`
- `handoff_decision`
- `downstream_review_bound_inputs`

### 2.4 Diagram 继承项
- `diagram_obligation`
- `diagram_type`
- `diagram_minimum_elements`
- `fail_action`

### 2.5 Execution-control 继承项
- 必须能被 `scripts/phase1/run_phase1_full_trial.py` 编入完整链路
- 必须允许 `scripts/phase1/run_phase1_convergence.py` 对其下游产物进行 gate / remediation 判断
- 不允许把“手工逐 Stage 运行”默认为正式交付路径

### 2.6 Workflow / Context Boundary 与 Loop 继承项
- 必须声明 `workflow_certainty` 与 `context_certainty`
- 必须声明 `fixed_workflow_scope` 与 `agentic_scope`
- 必须声明 `context_completion_policy` 与 `external_evidence_policy`
- 必须声明 loop mode、round trigger、`positive_business_value_gain` 定义、以及 `freeze | return-remediate | blocked` 出口
- `Phase-1` 默认是 `baseline`；`creative` 只允许在用户显式要求且 baseline 已达标后启动

---

## 3. 每个 Stage Skill 的标准编写顺序

后续正式写某一个 Stage Skill 时，固定按以下顺序编写：

1. **先写 `skill-contract.md`**
   - 定义输入、不可推演项、允许 provisional 的范围、输出物、gate 条件
   - 明确 `workflow/context certainty`、固定流程边界、Agent 可发挥边界、以及 loop/exit 规则
2. **再写 `stage-sop.md`**
   - 定义 intake/clarification/provisional/review 的流程与回退路径
   - 明确运行时如何触发 bounded deepening、何时 return upstream、何时冻结
3. **再写 `output-template.md`**
   - 把 output 字段、来源标记、diagram obligation、handoff package 明确成文档骨架
4. **最后写 `source-cards.md`**
   - 指定 required / optional / boundary / anti-pattern cards

原因：

- contract 决定边界
- SOP 决定过程
- output-template 决定交付形态
- source-cards 决定方法资产引用

并且：

- core business deliverables checklist 决定“当前阶段的输出到底挂靠到哪份统一业务产物基准”
- handoff-checklist / handoff-contract 模板决定“当前阶段交给下游时到底检查什么、承诺什么、保留什么”

如果顺序反过来，很容易先堆方法素材，再发现 contract/gate 无法落地。

---

## 4. 4 个阶段中“共享”与“变化”的部分

## 4.1 共享部分（统一）

以下部分应尽量统一：

- intake state machine
- provisional inference policy
- provenance / verification 字段
- handoff package 字段形态
- diagram obligation 的表达方式

## 4.2 按阶段变化的部分

以下部分应因 Stage 不同而变化：

- required / optional outputs
- `cannot_infer` 字段清单
- diagram type 与 minimum elements
- refusal 条件
- downstream handoff 内容

---

## 5. 第一批正式开发的最小实施批次

为了尽快从“文档评审脚手架”进入“可执行 Stage Skill 编写”，第一批只做以下内容：

### Batch-1（必须完成）
- common intake/state-machine policy
- hardened templates
- Stage-01 formalization
- Stage-02a / Stage-02b formalization

### Batch-2（紧随其后）
- Stage-03 formalization
- Stage-04 formalization
- Stage-01 → Stage-04 handoff chain review

这样做的原因是：

- Stage-01 / Stage-02 决定第一阶段启动与结构化质量
- 如果前两段没有先写硬，后两段会建立在不稳定输入上

---

## 6. 当前 authoring readiness 结论

当前仓库已经具备开始正式写第一阶段 Skills 的最小条件：

- 参考优先级已冻结
- intake state machine 已冻结
- gate / refusal / diagram rules 已定义
- 模板已补足 provenance / provisional / handoff / diagram 字段

因此下一步不再是“继续讨论是否能开始”，而是：

> **直接从 Stage-01 `requirements-user-research` 的正式 contract / SOP / output-template 编写开始，并在可用后接入 `scripts/phase1/run_phase1_full_trial.py` 的项目级执行入口。**
