# 产品 / 需求阶段 Skill 包（Phase-1）

## 1. 这是什么

这是当前仓库中已经正式落地的 **第一阶段（产品 / 需求）Stage Skill set**。

当前官方阶段入口是：

- `skills/wff-req/`
- `docs/phases/phase-1/phase-1-session-bootstrap.md`

它不再只是“看起来像未来成品的样板包”，而是：

- 已完成 4 个主链逻辑子阶段 / 5 个主链运行时执行包
- 已补入 1 个可选桥接阶段（Stage-05 Prototype Spec）
- 已完成中文审计镜像
- 已完成 happy-path dry-run 与 verification
- 已完成 rule-level robustness coverage
- 已接入 core business deliverables checklist 与 traceability naming block

也就是说，这个目录现在是：

> **Phase-1 的可执行运行时包 + 审计/验证配套资产**

---

## 2. 第一阶段包含的 4 个主链逻辑子阶段 / 5 个主链运行时执行包，以及 1 个可选桥接阶段

### Stage-01：需求调研 / 用户理解
回答：
- 我们面对的是谁
- 他们有什么问题
- 现在值得继续推进的机会是什么

### Stage-02a：需求分析 / 需求结构化
回答：
- Stage-01 的输入如何变成结构化需求全景
- 主干活动 / 主流程 / 关键约束是什么

### Stage-02b：需求规格深化 / 规格级补强
回答：
- 哪些 NFR、领域对象、信息架构方向会实质影响 Stage-03 的切片
- Stage-03 不能缺少哪些 specification-grade 输入

### Stage-03：需求拆解 / MVP 切片
回答：
- 如何形成最小可用体验闭环
- 如何切出 first / later / deferred items

### Stage-04：需求验证 / 概念验证
回答：
- 哪些关键假设需要验证
- 如何形成 Go / No-Go / Revise 结论并回灌前序阶段

### Stage-05：原型描述桥接 / Prototype Spec
回答：
- 如何把已收敛的 PRD 与 Stage-02a / 02b / 03 / 04 重新编译为原型可消费输入
- 如何在不重开产品定义的前提下，生成页面地图、主流程、状态覆盖与原型执行约束

补充定位：
- Stage-05 不是主链 Stage，不进入当前默认 full-trial
- 它位于 `PRD -> Prototype Spec -> 外部 HTML 原型执行` 的桥接分支上

---

## 3. 每个子阶段现在都有哪些资产

Stage-01 / Stage-02a / Stage-03 / Stage-04 当前已经具备三层资产。

Stage-02b 当前已补齐运行时主文件：
- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

Stage-05 当前首版已补齐运行时主文件：
- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

但它当前仍属于可选桥接阶段：
- 已完成 stage-pack 结构落位
- 尚未接入默认 `run_phase1_full_trial.py`
- 当前主交付物是 `prototype-spec.md`，不是 HTML 原型本身

但其中文审计镜像与部分 authoring-time / verification 资产仍在继续对齐，因此此目录当前是：

- 运行时主链可用
- 审计/验证镜像部分完成，部分待继续补齐

也就是说，当前这套 Phase-1 Stage 技能集不再存在“脚本依赖 Stage-02b，但 Stage-02b runtime pack 本身缺文件”的结构性缺口。

### A. 运行时主文件（Runtime Assets）
- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

### B. 中文审计镜像（Audit Mirrors）
- `*.zh-CN.md`

### C. 设计/审计/验证资产（非最终运行包主线）
- `stage-charter.md`
- `source-register.md`
- `rule-cards.md`
- `merge-decisions.md`
- `binding-matrix.md`
- `self-test-case.md`
- `self-test-dry-run-output.md`
- `self-test-verification-report.md`
- `robustness-test-case.md`
- `robustness-test-report.md`

这些资产并不都属于最终发布包主线。关于分层原则，见：

- `docs/governance/design-time-vs-runtime-artifacts-segregation-v0.1.md`

---

## 4. 当前 Phase-1 已经能产出的核心业务结果

当前 Phase-1 已经能产出并串成主链的核心业务产物包括：

- 用户边界 / 用户分组
- User Story / User Case
- 问题清单 / 机会清单
- 需求全景 / 主流程 / 故事地图
- 关键约束 / 初版优先级分组 / 高风险待验证点
- 完整体验闭环 / 最小可用体验闭环
- MVP 定义 / 首批切片 / 后续切片 / 暂缓项
- 验证对象 / 验证方式 / 验证结论 / 修订建议
- 进入设计 / 架构阶段的 handoff 包

完整基准见：

- `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`

---

## 5. 当前验证状态

### 已完成
- Stage-01 happy-path dry-run：PASS
- Stage-02 happy-path dry-run：PASS
- Stage-03 happy-path dry-run：PASS
- Stage-04 happy-path dry-run：PASS

### 已完成的 robustness 覆盖（rule-conformance level）
- refusal path coverage
- blocked path coverage
- fake-output prevention coverage

### 已完成的 traceability 基础设施接入
- `wff-base-traceability-management` skill MVP 已可用
- Phase-1 output templates 已接入 skill-managed traceability naming block

### 当前边界
Phase-1 当前已经足以作为“good input / cooperative path”的稳定主链。

但它还不等于：
- 全面 live runtime hardening
- 全部异常路径都已在真实 orchestrator/交互层执行验证

---

## 6. 现在到底怎么用这个 Phase-1 包（不是只读文档）

如果你真正关心的是：

- 需不需要先安装 Skill？
- 如果还没有把这些 Stage Skills 注册进系统，怎么直接跑官方链路？
- 输入到底要给什么？
- 怎样才能产出第一阶段交付物？

那么当前最准确的答案是：

> **真实案例的官方运行入口，不是手工逐 Stage 填模板，而是项目级 full trial runner。**

也就是说，当前 Phase-1 的推荐使用方式是：

- 先打开 `skills/wff-req/SKILL.md`
- 再打开 `docs/phases/phase-1/phase-1-session-bootstrap.md`
- 以 Stage runtime packs 作为方法/约束来源
- 以 `scripts/phase1/run_phase1_full_trial.py` 作为真实案例的官方运行入口
- 以 `scripts/phase1/run_phase1_convergence.py` 作为 gate / remediation 引擎

手工逐 Stage 运行只保留给审计、调试和定向补救，不再作为正式交付路径。

### 6.1 现在是否必须先安装这些 Skills？

**当前不必须。**

因为当前可以直接走仓库内脚本入口，不要求先把本地 Skills 注册成系统可发现能力。

### 6.2 官方运行入口是什么

官方入口由两层组成：

- 人类/Agent bootstrap 入口：
  - `skills/wff-req/SKILL.md`
  - `docs/phases/phase-1/phase-1-session-bootstrap.md`
- 实际 runtime 入口：

- `scripts/phase1/run_phase1_full_trial.py`

推荐命令：

```bash
python3 scripts/phase1/run_phase1_full_trial.py \
  --source <phase1-input.md> \
  --output-dir </tmp/software-lifecycle-skills/<case>/<trial>> \
  --version <trial-vN> \
  --profile implementation-ready-prd
```

这条链路会自动完成：

- deep Stage-01 / 02a / 02b / 03 / 04 产物生成
- audit-rich PRD assembled draft
- converged PRD main document
- zh-CN audit mirror
- convergence evidence memo
- execution report
- convergence gates
- gate 失败后的 auto-remediation（默认启用）

### 6.3 那输入到底应该给什么

如果你要运行官方 Phase-1 交付链路，最少需要准备一个案例输入包。

建议至少包括：

- 项目/需求背景
- 目标用户或使用对象
- 目标场景 / 主干流程
- 当前问题 / 机会 / why now
- 已知约束
- 已知假设
- 已有草图 / 页面 / 原型（如果有）

这些输入不要求一开始非常完整。

但至少要让 Stage-01 能回答：

- 谁是用户
- 他们要完成什么
- 当前问题是什么
- 为什么值得继续推进

### 6.4 跑完后会产出什么

完整链路至少会产出：

- Stage-01 output
- Stage-02a output
- Stage-02b output
- Stage-03 output
- Stage-04 output
- assembled PRD draft
- converged PRD main document
- zh-CN PRD audit mirror
- convergence evidence memo
- execution report
- convergence gate JSON
- excellence regression report

### 6.5 Stage runtime packs 现在扮演什么角色

Stage packs 仍然是权威方法资产：

- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

但它们现在的角色是：

- 定义每个 Stage 的边界、方法、产物结构
- 供 generator / convergence / reviewer 调用
- 在 gate 失败时支持 targeted remediation

它们**不再推荐作为官方最终交付的人肉直填路径**。

### 6.6 可以直接给 Agent 什么样的指令

如果环境已经能读取本仓库的本地 Skills，优先使用：

- `skills/wff-req/SKILL.md`
- `docs/phases/phase-1/phase-1-session-bootstrap.md`

如果当前环境还没注册本地 Skill，也可以直接给 Agent 这种要求：

> 请按仓库官方 Phase-1 full trial 链路运行真实案例。以 `scripts/phase1/run_phase1_full_trial.py` 为主入口，
> 输入源文件为 `<phase1-input.md>`，输出到 `<trial-output-dir>`，并保留 stage outputs、PRD、evidence、execution report 与 gates。

---

## 7. 审计 / 调试模式：什么时候才手工逐 Stage

手工逐 Stage 模式仍然保留，但只适合以下场景：

- authoring 新的 Stage pack
- 审计某个 Stage 的 contract / SOP / output surface
- gate 失败后，定向检查某个 Stage 为什么过薄或 reasoning 不足
- 在 rerun full trial 前，对单个弱点做 targeted remediation

它不适合：

- 把手工填出的 Stage 文档直接当成官方 Phase-1 交付物
- 跳过 PRD assembly / convergence / gates
- 用人工总结掩盖 stage depth / PRD depth 不足

### 7.1 正确的调试顺序

1. 先看 full-trial 的 gate 失败点
2. 确认是哪个 Stage / 哪个 artifact unit 过薄
3. 再打开该 Stage 的：
   - `skill-contract.md`
   - `stage-sop.md`
   - `output-template.md`
   - `source-cards.md`
4. 做定向修正，而不是从头手工重写整条链路
5. 修正后重新运行 `scripts/phase1/run_phase1_full_trial.py`

### 7.2 调试时要特别避免的错

- 把 Stage pack 当成模板题来填
- 只补字段，不补 alternatives / trade-off / reasoning evidence
- 直接改最终 PRD，而不回到导致薄弱的 stage artifact
- 在 gate 未通过时，靠人工判读把结果说成 PASS

### 7.3 如果你就是要人工看一遍 Stage 内容

那也应把目标限定为：

- 审计
- 解释
- 局部补救

不应把这一步定义成官方交付完成。

---

## 8. 当前最重要的 supporting assets

如果要理解或继续扩展这个 Phase-1 包，优先看：

- `docs/phases/phase-1/phase-1-session-bootstrap.md`
- `docs/phases/phase-1/phase-1-skills-structure-v0.1.md`
- `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`
- `docs/governance/design-time-vs-runtime-artifacts-segregation-v0.1.md`
- `docs/phases/phase-1/phase-1-traceability-gap-analysis-v0.1.md`
- `docs/phases/phase-1/phase-1-source-unit-coverage-ledger-v0.1.md`
- `docs/phases/phase-1/phase-1-document-library-template-unit-ledger-v0.1.md`

---

## 9. 如何把它作为下游阶段输入来使用

当前最推荐的使用方式不是继续在 Phase-1 内部无休止打磨，而是：

> **把它作为 design / architecture 阶段的正式上游输入基座。**

也就是说：

- design / architecture 阶段应接收：
  - Phase-1 的 handoff 包
  - Phase-1 的核心业务产物基准
  - review-bound / provisional 边界说明
  - traceability naming block

---

## 10. 当前最准确的一句话总结

这个目录现在已经不是样板，而是：

> **第一阶段（产品 / 需求）完整 Stage Skill set 的当前正式工作包。**
