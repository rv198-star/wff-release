# Phase-2 完成摘要与 Phase-3 启动指导（v0.1）

## 这份文档的目的

这份文档用于冻结第二阶段（design / architecture）的完成状态，并把本阶段开发中抽取出来的经验整理成第三阶段（实现 / 开发）可直接复用的启动指导。

它不是一次 PR 摘要，而是 Phase 级经验沉淀文档。

---

## 一、Phase-2 当前完成状态

### 结论

第二阶段（design / architecture）已经完成首轮正式落地，并已经合并进入 `main`。

当前已经形成：

- 4 个 Stage 子阶段完整包
- runtime 4 件套
- design-time controls
- self-test / dry-run / verification
- robustness 覆盖
- bilingual audit mirrors（runtime + verification）
- core business deliverables checklist 接入
- coarse-grained traceability baseline + registry-backed pilot 接入
- all-stage minimum runtime-hardening evidence surface
- public-boundary-only 冻结纪律
- Stage-01 安全架构草图 + 容量估算输出
- Stage-01 依赖 realizability / substitute-boundary / downstream assumption contract 输出
- Stage-03 全量场景 coverage + 技术选型证据 + 主导瓶颈/替代候选输出
- Stage-03 关键外部依赖 realizability + substitute-boundary 输出
- Stage-04 关键 public-boundary 时序集 + 最优性审查 + 粗粒度 implementation task sketch 输出

---

## 二、Phase-2 的 4 个 Stage 子阶段

### Stage-01：architecture-definition-and-boundary-setting
- 冻结系统边界、约束态势、能力结构、架构方向
- 在边界层补出安全架构草图与容量估算
- 明确吸纳上游 `present | absent | unknown | deferred` 状态

### Stage-02：domain-module-service-decomposition
- 将 Stage-01 的边界与能力结果转成领域 / 模块 / 服务分解结构
- 补出概念 ER、领域事件目录，并只冻结 public boundary

### Stage-03：data-storage-and-interface-design
- 将分解结果转成数据归属、存储策略、schema/API 草案、交互流、安全/部署假设
- 强制覆盖所有已知业务场景，并对技术选型、主导瓶颈、替代候选与最优候选做显式记录

### Stage-04：design-convergence-and-delivery-prototype
- 将前 3 个 Stage 收敛成 implementation-facing design handoff 包
- 保留关键 public-boundary 时序、技术选型证据链、coarse-grained implementation task sketch，以及 acceptable vs optimal 审查

---

## 三、Phase-2 相比 Phase-1 的关键增量经验

### 1. NFR 不确定性在设计阶段不能再隐式存在
Phase-1 可以接受 NFR 信息不完整，只要不隐藏。

Phase-2 不行。

因为一旦进入架构边界、分解与接口设计，未显式表达的 NFR 会直接变成结构性债务。

这意味着：

- `present | absent | unknown | deferred` 必须跨 Stage 连续保留
- `key constraints` 不能被自动当成完整 NFR 基线

### 2. 边界错误代价更高
Phase-1 的问题通常还可以在后续分析和验证中回收。

Phase-2 的 Stage-01 一旦边界定义偏差，后面 Stage-02/03/04 全都会被污染。

因此边界冻结在 Phase-2 中不是文档动作，而是下游结构控制动作。

### 3. 方法 creep 风险显著升高
设计 / 架构阶段天然会吸引 TOGAF、SOA-lite、SOMA、BPMN 等大方法体系。

Phase-2 的经验是：

- 它们可以做 review lens / sidecar
- 但绝不能替代当前 4 个 Stage 的执行骨架

### 4. “看起来完整”比“真的可交接”更容易误判
Phase-4 收敛时尤其明显：

- 文档可以很快变得“好看”
- 但 unresolved risks、review-bound items、downstream usage rules 仍可能缺失

所以 Phase-2 必须把 false-readiness 防护显式写进验证和 robustness。

### 5. public boundary 才是这一层真正要冻结的粒度
Phase-2 的经验是：

- 模块对模块、应用对应用可见的对象 / 契约 / 交互名称应该冻结
- 内部类名、方法名、文件结构不应在这一层被伪装成“必须确定”
- Stage-04 的 implementation task sketch 也只能冻结到 slice / module / work-package 粒度

### 6. 场景 coverage 与详细时序不是一回事
Phase-2 已证明：

- 所有已知业务场景都应被 coverage matrix 承接
- 但详细时序图只应要求关键 public-boundary 场景

### 7. 技术选型不能只靠模型记忆
当技术选型依赖版本、LTS、license、安全公告、benchmark 等当前事实时：

- 必须保留外部证据
- 必须让审计层能看到证据来源，而不是只看到结论

### 8. 架构评审要区分“可接受”与“更优”
对于强主导约束场景，Phase-2 不应停在主流可行方案。

必须继续回答：

- 主导瓶颈是什么
- 主流基线为什么不足
- 为什么最终候选比主流基线更强

---

## 四、Phase-2 已验证有效的建设方式

### 1. 先 control artifacts，再 runtime files
Phase-2 再次证明：

- `stage-charter`
- `source-register`
- `rule-cards`
- `merge-decisions`
- `binding-matrix`

应先于 runtime 4 件套完成。

### 2. verification 不能只停在 `verification.md`
真正有效的验证层至少应包含：

- `self-test-case.md`
- `self-test-dry-run-output.md`
- `self-test-verification-report.md`
- `robustness-test-case.md`
- `robustness-test-report.md`

### 3. bilingual audit mirrors 不是可有可无
在当前项目里，英文运行时主文件 + 中文审计镜像的双轨方式是可维护的。

Phase-2 已经证明这套方式不仅适用于 Phase-1，也适用于更复杂的设计 / 架构阶段。

### 4. traceability 至少要做到 coarse-grained baseline
不能只写 narrative handoff。

至少需要：

- `artifact_id`
- `artifact_type`
- `depends_on`
- `feeds`
- `source_path`
- `source_anchor`

并在 dry-run 输出中出现真实示例，而不只是模板占位。

### 5. runtime hardening 应该先 pilot，再按价值扩到全 Phase
不需要等完整 orchestrator 才开始。

Phase-2 的经验是：

- 先在最关键的 Stage-01 做 runtime-decision / state-transition / failure-path pilot
- 再把这套证据面复制到 Stage-02~04
- 但仍然保持“first-pass evidence depth”，不假装已经有 live orchestrator proof

---

## 五、这些经验对 Phase-3 的直接指导

### 1. Phase-3 不应回到“写实现提示词”模式
Phase-3 如果只是代码实现 prompt 包，会直接丢掉前两阶段建立的控制面。

Phase-3 仍应保持：

- artifact-first
- gate / refusal
- explicit handoff
- runtime vs audit segregation
- deliverables checklist 挂靠
- traceability baseline
- public-boundary-first 冻结纪律
- evidence-backed technology selection
- acceptable-vs-optimal distinction when strong constraints dominate

### 2. Phase-3 的 Stage-01 应首先解决“实现入口与构建边界”
正如 Phase-2 先冻结边界，Phase-3 的最前一层也应先冻结：

- implementation scope
- module ownership / implementation readiness
- test / build / delivery baseline

而不是直接开始生成代码任务。

### 3. Phase-3 必须更早引入 runtime hardening
因为进入实现阶段后，runtime hardening 的意义会更高：

- refusal / blocked / missing dependency
- build / test gating
- implementation handoff consistency

建议：

- 不要把 runtime-hardening pilot 拖到 Phase-3 尾部
- 应该在最早两级 Stage 就开始介入

### 4. Phase-3 应继承而不是重造 checklist / traceability 模式
Phase-2 已经验证：

- deliverables checklist
- coarse-grained traceability baseline
- output-template 挂靠

这些不是设计阶段特例，而是后续 Phase 也应继承的工程基线。

### 5. Phase-3 也应继承“coverage 先于细化时序”的原则
实现阶段可以继续细化内部实现，但不应倒推 Phase-2 去强行冻结所有内部时序。

---

## 六、推荐给 Phase-3 的启动顺序

### 第一步：冻结 Phase-3 family structure
- 明确 Phase-3 的 4 个 Stage 子阶段
- 明确每个 Stage 的目标与 handoff 关系

### 第二步：先写 control layer
- `stage-charter`
- `source-register`
- `rule-cards`
- `merge-decisions`
- `binding-matrix`

### 第三步：再写 runtime 4 件套
- `skill-contract`
- `stage-sop`
- `output-template`
- `source-cards`

### 第四步：从一开始就带 verification / robustness / traceability
- 不要等“包写完了再补”
- 应边写边锁定最小验证面

---

## 七、一句话结论

Phase-2 给 Phase-3 的最大经验不是“如何写设计文档”，而是：

> **越接近真实工程执行，越要把不确定性、边界、交接和验证前置为工程结构本身，而不是事后补充说明。**
