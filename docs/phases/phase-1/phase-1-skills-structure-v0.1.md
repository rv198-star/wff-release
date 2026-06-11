# 第一阶段（产品 / 需求）Skills 结构设计（v0.1）

## 目的

本文件用于在正式落笔 Stage-01 / Stage-02 之前，先冻结第一阶段 Skills 的整体结构。

它回答的问题不是：

- 某个具体 Stage Skill 该写什么细节

而是：

- Phase-1 整体应该长成什么结构
- 哪些是“正式 Skill 包的一部分”
- 哪些是“编写过程中的中间产物”
- 哪些需要中英双轨以便人类审计，哪些最终不应进入发布包
- 哪些内容应共享，哪些应按子阶段分化

补充：

- 设计时资产、审计资产、最终运行时资产必须显式分层，不能混为一谈

这一步的目的是减少后续返工。

---

## 1. Phase-1 不只是 Stage Skills，还需要项目级执行控制层

当前第一阶段主链固定为 4 个逻辑 Stage Skills，其中 Stage-02 在运行时拆成 `02a + 02b` 两个执行包：

1. `requirements-user-research`
2. `requirements-structural-analysis`（Stage-02a）
3. `requirements-specification-deepening`（Stage-02b）
4. `requirements-decomposition-and-mvp-slicing`
5. `requirements-validation-and-concept-proof`

此外，当前还新增一个**可选桥接 Stage pack**，不属于默认主链执行包：

6. `prototype-spec-bridging`（Stage-05，可选分叉桥接阶段）

主链 Stage packs 不是 4 个互相孤立的文档包，而是一套：

> **共享同一 intake / governance / provenance / handoff 语言，但在输出、gate 和方法资产上逐阶段分化的 Skill family。**

但如果只有这些 Stage packs，仍然会留下一个关键断口：

- 可以“看起来按 Stage 跑了”
- 却没有项目级控制层强制把深生成、PRD 装配、收敛门禁、execution report 串成唯一合法入口
- 从而让手工逐阶段填模板的浅层运行混入正式交付

此外，`prototype-spec-bridging` 的定位不是继续推进主链分析，而是：

- 从 converged PRD 与 late-stage outputs 分叉
- 面向外部原型执行重编译输入
- 形成 `prototype-spec.md`

因此，Phase-1 不能只被理解为一组 Stage Skills。
它还必须包含一个**项目级执行控制层**，把 Stage family 收束成真实可交付的运行系统。

因此，Phase-1 的结构应该理解为：

- **Family-level shared spine**
- **Project-level execution control layer**
- **Stage-level execution packs**
- **Authoring-time intermediate artifacts**

---

## 2. Phase-1 的四层结构

在进入四层结构之前，先补一个总原则：

## 2.0 两类文件形态：运行时文件 vs 审计镜像文件

为了兼顾：

- Skill 运行时稳定性
- 人类审计可读性
- 最终发布包的简洁性

第一阶段允许采用 **英文运行时文件 + 中文审计镜像文件** 的双轨写法。

但必须明确：

> 这不是 Phase-1 的局部特例，  
> 而是项目级原则“英文面向 AI / 运行时，中文面向人类 / 审计”的当前具象化落地。

### A. 运行时文件（Runtime Assets）

这类文件的目标是：

- 结构稳定
- 便于后续 Skill 运行/加载/复用
- 作为最终发布包的主体

默认应优先保持英文命名与英文正文语义稳定。

### B. 审计镜像文件（Audit Mirror Assets）

这类文件的目标是：

- 方便人类审阅
- 方便讨论阶段边界、规则含义、约束是否成立
- 帮助避免英文文件语义被误解

它们应作为**独立文件**存在，而不是把中英混写在同一个运行时文件中。

### 结论

> 运行时文件服务系统执行，审计镜像文件服务人类理解。  
> 最终发布包默认保留运行时文件，按需移除不必要的中文审计镜像文件。

换句话说，Phase-1 当前的英中文件双轨，不是临时折中，而是对全项目语言分工原则的具体实现。

进一步的资产分层说明，见：

- `docs/governance/design-time-vs-runtime-artifacts-segregation-v0.1.md`

## 2.1 Family-Level Shared Spine（共享骨架层）

这一层不属于单个 Stage，而属于整个 Phase-1 共同继承的骨架。

当前已经冻结或接近冻结的内容包括：

- `runtime-deps/mindthus/source/skills/3l5s/SKILL.md`
- `runtime-deps/mindthus/source/skills/using-mindthus/SKILL.md`
- `docs/governance/evidence-and-uncertainty-protocol-v0.1.md`
- `docs/governance/deepening-and-freeze-protocol-v0.1.md`
- `docs/governance/handoff-and-convergence-protocol-v0.1.md`
- `docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md`
- `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`
- `templates/handoff-checklist.md`
- `templates/handoff-contract.md`
- `docs/phases/phase-1/phase-1-skill-authoring-basis-v0.1.md`
- `templates/skill-contract.md`
- `templates/stage-sop.md`
- `templates/output-template.md`

这一层解决：

- 跨阶段共用的 reasoning kernel
- source cards 如何被转成实际 reasoning operation
- evidence / uncertainty / review-bound 的公共语义
- bounded deepening / freeze 的公共协议
- downstream handoff / convergence 的公共协议
- 参考法源优先级
- intake state machine
- provisional inference policy
- gate / refusal / handoff 的基本表达
- provenance / verification / diagram 的通用字段
- Phase-1 核心业务产物基准
- cross-stage handoff checklist / contract 的显式模板化

> 这一层应尽量稳定，不随某个单独 Stage Skill 的局部偏好而改变。

---

## 2.2 Project-Level Execution Control Layer（项目级执行控制层）

这一层不属于某一个 Stage runtime pack，但决定了真实案例如何被合法执行成官方 Phase-1 产物。

当前应视为这一层核心资产的包括：

- `docs/phases/phase-1/phase-1-convergence-driver-v0.1.md`
- `scripts/phase1/run_phase1_full_trial.py`
- `scripts/phase1/run_phase1_convergence.py`
- `scripts/phase1/phase1_generate_deep_stage_outputs.py`
- `scripts/phase1/phase1_assemble_prd.py`
- `scripts/phase1/phase1_converge_prd.py`
- `scripts/phase1/phase1_emit_execution_report.py`
- `scripts/phase1/phase1_stage_artifact_depth_gate.py`
- `scripts/phase1/phase1_prd_quality_gate.py`
- `scripts/phase1/phase1_prd_executability_gate.py`

这一层解决：

- 真实案例的官方运行入口
- Stage 产物生成、PRD 装配、PRD 收敛、执行报告的固定链路
- non-shrinking、depth、executability 与 `prd_mainline_gate_bundle` 级门禁
- 失败后是否回到 remediation loop，而不是靠人工总结掩盖
- “正式交付”与“调试/审计/作者手工检查”之间的边界

补充说明：

- `phase1_prd_assembly_integrity_gate.py`
- `phase1_prd_analysis_delta_gate.py`
- `phase1_prd_section_scoring_gate.py`
- `phase1_artifact_consistency_gate.py`

当前仍保留为 bundle internal / compatibility gate scripts。
它们属于 `prd_mainline_gate_bundle` 的内部实现与审计细节，不再应被视作并列的 canonical Phase-1 mainline command surface。

硬规则：

- 真实案例正式交付必须经过这一层
- 仅按 Stage `output-template.md` 手工填充并串联，不构成有效 Phase-1 正式结果
- 手工逐 Stage 运行只允许用于 `authoring / audit / debug / targeted remediation`

---

## 2.3 Stage-Level Execution Packs（子阶段执行包）

这一层才是每个 Stage Skill 真正落地的内容。

每个运行时 Stage pack 固定由 4 个正式文档组成：

- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

必要时，还可以有对应的**中文审计镜像文件**，例如：

- `skill-contract.zh-CN.md`
- `stage-sop.zh-CN.md`
- `output-template.zh-CN.md`
- `source-cards.zh-CN.md`

其中：

- 英文版是运行时主文件
- 中文版是审计镜像文件
- 两者应保持一一对应，但不混写在同一文件中

其中：

### `skill-contract.md`
定义：
- 输入 / 输出
- `cannot_infer / can_provisionally_infer / must_validate_before_exit`
- gate / refusal
- 下游 handoff 前提

### `stage-sop.md`
定义：
- intake → clarification → blocked → provisional → review → gate-pass 的过程流
- review checkpoints
- return path / escalation path

### `output-template.md`
定义：
- 文档字段
- provenance / confidence / verification
- diagram obligation / fail action
- handoff package
- 当前阶段覆盖的核心业务产物

### `source-cards.md`
定义：
- required method assets
- optional support assets
- boundary / anti-pattern cards

补充规则：
- `source-cards.md` 不再承担通用 thinking SOP 本体
- 它只负责声明“本 Stage 应优先调用哪些方法资产”
- 通用的素材卡使用方式、证据处理、deepening/freeze、handoff/convergence，统一由公共 reasoning-kernel 文档提供

> 这 4 个英文主文件是正式 Stage Skill 成品的一部分。少一个都不完整。  
> 中文镜像文件用于审计与 review，不默认视为最终发布包必需项。

---

## 2.4 Authoring-Time Intermediate Artifacts（编写期中间产物层）

这一层不是最终 Stage Skill 成品，但必须在编写阶段存在。

按 `docs/stage-skill-authoring-workflow-v0.1.md`，至少包括：

- `stage-charter.md`
- `source-register.md`
- `rule-cards.md`
- `merge-decisions.md`
- `binding-matrix.md`
- `verification-report.md`

这些文档的作用不是给终端使用者看，而是确保：

- 目标冻结
- 选材有 why-included
- 重复/冲突有显式决议
- hard rules 可追溯
- 正文不是作者临场发挥产物
- 英文运行时主文件与中文审计镜像之间不会发生语义漂移

> 它们是“编写控制层”，不是“运行时内容层”。

更明确的分层原则见：

- `docs/governance/design-time-vs-runtime-artifacts-segregation-v0.1.md`

---

## 3. 共享内容与分化内容

## 3.1 应共享的部分

以下内容在 4 个 Stage Skills 中应高度一致：

- intake state names 与基本含义
- provisional inference 标记方式
- provenance / verification 字段
- handoff_package 字段表达
- diagram obligation 表达方式
- 引用法源层级（repo policy / skill-authoring constraint / source bundles）
- 英文主文件与中文审计镜像之间的语义对应规则

## 3.2 应分化的部分

以下内容必须按阶段变化：

- required / optional outputs
- `cannot_infer` 字段范围
- refusal 条件
- diagram type 与 minimum elements
- source bundles 选择
- downstream handoff 内容

换句话说：

> **结构统一，方法分化，gate 精准化。**

---

## 4. Family 级与 Stage 级的关系

后续每写一个 Stage Skill，都不应该从零开始，而应该按以下关系继承：

### Family 层提供
- 统一语言
- 统一约束
- 统一模板字段
- 统一 authoring workflow
- 统一的中英双轨审计规则

### Execution control 层提供
- 真实案例的 canonical run order
- stage outputs → assembled PRD → converged PRD → evidence memo → execution report 的固定链路
- 自动 remediation / return / blocked 的项目级判定
- 把“结构正确但分析过浅”的情况挡在正式交付之外

### Stage 层负责
- 把统一骨架具体化到当前问题域
- 绑定本阶段的 source bundles / source cards
- 定义本阶段独有 gate / refusal / handoff 细节
- 生成必要的中文审计镜像文件（若该阶段进入人类审计）

因此，Stage Skill 不应：

- 自创自己的 intake 状态
- 自改 provisional 语义
- 自改 provenance 字段语义
- 在英文主文件中混入大量中文解释性文本
- 让中文镜像文件变成与英文主文件不一致的“第二套规则”

如果某个 Stage 真的需要突破这些共性，应该先回到 Family-Level Shared Spine 讨论，而不是在局部文档里偷偷偏离。

---

## 5. Phase-1 的推荐实现顺序

### Step A：先冻结 Family 层
当前这一步已基本完成。

### Step B：先做 Stage-01 与 Stage-02
原因：
- 它们定义第一阶段的启动质量与结构化质量
- 它们决定 Stage-03 / Stage-04 的输入是否稳定

### Step C：再做 Stage-03 与 Stage-04
在前两段稳定后，补全拆解与验证收口。

### Step D：接入项目级执行控制层
把 Stage family 接进：

- `scripts/phase1/run_phase1_full_trial.py`
- `scripts/phase1/run_phase1_convergence.py`
- PRD assembly / convergence / gates / execution-report 链路

直到真实案例输出不再依赖手工串 Stage，才算从“可读的 Stage 包”进入“可交付的 Phase-1 系统”。

### Step E：最后做 Phase-1 family review
验证 4 个 Stage Skills 与项目级执行控制层是否真的共享同一套骨架，而不是名义上一致、实际各写各的。

---

## 6. 当前结论：下一步该直接写什么

基于当前结构，下一步不应直接“凭感觉写 Stage-01 正文”，而应：

1. 先为 `requirements-user-research` 建 authoring intermediate artifacts
   - `stage-charter`
   - `source-register`
   - `rule-cards`
   - `merge-decisions`
   - `binding-matrix`
2. 再正式写：
   - `skill-contract.md`
   - `stage-sop.md`
   - `output-template.md`
   - `source-cards.md`

3. 把这些 Stage packs 接进项目级执行控制层：
   - `scripts/phase1/run_phase1_full_trial.py`
   - `scripts/phase1/run_phase1_convergence.py`
   - PRD assembly / convergence / execution report

4. 若进入人类审计轮次，再补对应的：
   - `*.zh-CN.md` 审计镜像文件

> 也就是说：现在不该直接跳进正文，也不该把手工串 Stage 误当成正式运行；而该先按结构设计进入受控 authoring，再接入 full-trial control layer。 
