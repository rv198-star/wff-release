# 阶段复盘与下阶段切换说明

## 这份文档的目的

这不是聊天总结，而是当前项目从“基础设施建设期”切换到“阶段 Skill 建设期”的工作锚点。

在压缩上下文、切换会话或重新分工时，应优先阅读本文，再阅读：
- `docs/blueprint.md`
- `docs/mvp-scope.md`
- `docs/collaboration-ops.md`

---

## 一、当前项目整体目标（对齐版）

当前项目的核心目标已经比较清晰：

> 构建一套 AI-first 的软件工程 Meta Skills 体系，用 artifact contract、gate/refusal、阶段 handoff、知识底座与方法治理，把复杂软件研发过程重新组织为 AI 可执行、可审计、可渐进增强的工程系统。

这个目标包含几个已经稳定下来的原则：
- AI-first，human-as-fallback
- artifact-first
- gate / refusal / handoff 明确化
- UML / Mermaid required
- 多工程路线（multi-lane）
- 重方法资产，不重制度壳
- 高阶方法论先资产化，再逐步融入阶段 Skills

---

## 二、当前阶段判断

### 结论
项目已经不再停留在“基础设施建设期”，而是已经完成：

- 第一阶段（产品 / 需求）Stage Skill family
- 第二阶段（设计 / 架构）Stage Skill family
- 第三阶段（实现 / 开发）Stage Skill family 的 **first-pass family closure**
- 第四阶段（测试 / 验证）Stage Skill family 的 **first-pass family closure**

当前最准确的状态是：

> 四个主阶段 family 都已经进入“可手工调用、可试跑、可审查”的 first-pass authored package 形态。

### 已完成的基础设施

#### 1. 框架方向已稳定
- 项目不是 prompt 库，也不是零散技能合集
- 项目是 AI-first 的 Meta Skills 工程系统
- 主控制面是 artifacts / gates / contracts / handoffs

#### 2. 知识提炼工具已形成稳定基线

##### `book-to-skills-extraction`
- 已达到阶段性稳定基线
- 定位：原书 → 索引地图 → 知识卡 → 阶段指引 → Skill 引用层
- 已防止摘要化、书本视角残留、无 keep/discard、无 downstream mapping 等失败模式

##### `corpus-extraction-governance`
- 已达到更强的阶段性稳定基线
- 目前版本：`v1.2`
- 定位：文档库抽取治理中枢
- 已覆盖：
  - merge
  - promotion
  - diagram gate evidence
  - absorption mapping
  - blocker-remediation mode
  - mission completion rule

#### 3. 外部文档库抽取任务已完成
- 文档库抽取任务已经过多轮治理和收敛
- 到 round-05，已达到“任务完成”的判断标准
- 当前剩余的是个别资产的后续升格问题，不再属于“文档库抽取任务未完成”

---

## 三、当前最重要的判断

### 当前不需要继续优先做的事
- 不需要继续优先扩展新的 Meta Skills
- 不需要继续扩大文档库抽取范围
- 不需要继续把更多高阶方法论一股脑压进主框架

### 当前最应该开始做的事

> 从“阶段 family 的 first-pass 建设”转向“跨阶段收敛 + 整体回顾补漏 + 真实使用验证 + 选择性 hardening”。

这意味着当前自然切换点，已经不再是“开始下一个 family 建设”，而是：

- 对齐 Phase-1 / Phase-2 / Phase-3 / Phase-4 的顶层叙事、family README、checkpoint 与共识文档
- 用真实手工试跑或家族级审计验证 family 是否真的可消费
- 按 review/试跑反馈做 selective hardening，而不是继续对称性堆资产
- 逐步把跨阶段共性经验沉成更稳定的方法基线

---

## 四、两个 Meta Skills 是否达到阶段性稳定基线

### 结论：是

但成熟度有差异：

#### `book-to-skills-extraction`
- 稳定基线：已达到
- 当前定位：知识底座建设 Skill
- 当前成熟度：v1 稳定，可持续使用
- 后续增强应来自真实拆书轮次，不是纸上扩写

#### `corpus-extraction-governance`
- 稳定基线：已达到，且成熟度更高
- 当前定位：抽取治理与收敛控制中枢
- 当前成熟度：项目内可作为稳定工作法使用
- 后续增强应继续来自真实 round 的审计与 blocker 修复

---

## 五、SOMA / 流程编排 / 服务编排 当前定位

这部分已经形成稳定共识：

- 不作为当前主框架的强制骨架
- 也不只是挂起的旁支注释

当前采取的策略是：

> 先作为高阶方法资产进入知识底座层与方法治理层，后续在阶段 Skills 落地时，寻找自然插入点，再渐进式沉到 lane-supporting packs 或具体 Meta Skills 中。

这意味着：
- 现在继续抽取和沉淀它们的知识资产是对的
- 但不需要先做系统级强制 adoption

---

## 六、接下来该怎么推进

### 第一优先：把 Phase-1 ~ Phase-4 从“都已成形”推进到“整体叙事与边界一致”

建议当前优先工作不再是继续大规模扩建阶段包，而是：

1. 做 Phase-1 ~ Phase-4 的 cross-phase convergence review
2. 修补顶层文档、family README、checkpoint 中的阶段残留与叙事漂移
3. 仅在 review 或试跑暴露真实问题时做 selective hardening
4. 把这一轮跨阶段经验沉淀回项目级经验文档 / checklist / hardening targets

当前参考：

- `docs/plans/2026-03-16-phase-3-family-first-pass-checkpoint.md`
- `archive/examples/implementation-development-package/README.md`

### 第二优先：继续建立“抽取成果 → 阶段 Skill”映射

目标不是继续堆素材，而是继续明确：
- 哪些卡服务哪个阶段 Skill
- 哪些卡变成 contract 字段
- 哪些卡变成 checklist / gate / handoff 规则
- 哪些卡只做参考知识，不进入主链

### 第三优先：抽取线继续作为支撑线

抽取仍继续，但模式应保持为：

> 按阶段 Skill 的缺口定向抽取，而不是继续大面积扩库。

第三阶段已经验证出一个新共识：

> 对实现 / 开发 / 测试验证类阶段，很多高价值素材来自 **官方工程文档、真实模板、开源实践**，而不是只靠拆书。

---

## 七、协作方式

当前推荐固定分工：

### 角色 A：Meta Skills Owner + Auditor
职责：
- 维护项目级 Meta Skills
- 审计 round 产物
- 决定规则升级与 release 收口

### 角色 B：Extraction Operator
职责：
- 外部工作区中的抽取、merge、promotion、blocker 修补执行
- 提供真实样例、真实失败、真实 round 结果

协作接口文档：
- `docs/collaboration-ops.md`

目标：
- 用户不再做人肉传话筒

---

## 八、跨阶段经验总结（Phase-1 / Phase-2 / Phase-3 / Phase-4）

### 1. 跨阶段都成立的经验

#### 1.1 control artifacts 先于 runtime prose
- Phase-1 证明了先冻结 control 面再写 runtime 更稳。
- Phase-2 继续验证了这一点，尤其在设计边界容易漂的时候。
- Phase-3 更进一步证明：实现阶段如果不先冻结 gate/baseline/profile/extraction/control 面，runtime 包会迅速退化成普通 coding 提示词。

#### 1.2 README-level human entry 是真正的生产力资产
- 一旦 family README 能回答“这是什么、怎么用、边界在哪”，阶段包就从“作者自己知道怎么跑”变成“其他人也能接手试跑”。
- 这条在 Phase-1 / Phase-2 成立，在 Phase-3 family consolidation 中再次被验证。

#### 1.3 shape consistency 本身是产品特性
- runtime 4-pack、verification、robustness、audit mirror 的结构平行，极大降低了复审和续写成本。
- 真正高价值的“补漏”，通常是修正形态漂移，而不是增加更多文件。

#### 1.4 happy-path verification 不够
- 四个阶段都证明：只有 verification 不够，还需要 self-test / dry-run / robustness 才能守住 false-readiness / fake-output 边界。

### 2. 到了第三阶段发生的方法转向

#### 2.1 source strategy 必须从 book-first 转向 web/template-first
- Phase-1 / Phase-2 仍能大量受益于拆书和方法论提炼。
- Phase-3 则明确证明：实现类 gate、command baseline、bootstrap、contract verification、change discipline，更适合来自：
  - 官方工程文档
  - 真实项目模板
  - 开源实现实践
- 书籍仍重要，但更适合作为 backbone / anti-pattern / rationale 支撑，而不是主来源。

#### 2.2 blocked / review-bound 输出本身就是有效产物
- Phase-3 Stage-01 的真实手工试跑证明：一个 `stage02_may_start: no` 的 package 仍然是有效输出，只要它把 blocked/remediation/review-bound 条件说清楚。
- 这意味着“不能开工”不是失败，而是 gate 成功工作的一种结果。

#### 2.3 selective hardening 比全面对称 hardening 更划算
- Phase-2 的经验是：先在 Stage-01 做 pilot runtime-hardening，再把真正有价值的证据面扩到其余 Stage。
- Phase-3 进一步证明：应优先补**最关键入口 Stage**的 runtime-decision-log / state-transition-record / failure-path-output，再决定哪些其他 Stage 值得继续对称铺开。

#### 2.4 第四阶段进一步验证了“证据与边界”优先于扩包对称性
- Phase-4 进一步证明：测试 / 验证阶段的关键价值不是继续堆更多 testing prose，而是把 acceptance mapping、execution evidence、closure judgment、Phase-4 / Phase-5 boundary 说清楚。
- 这进一步强化了一个跨阶段共识：
  > **先把 truth boundary、gate、evidence、handoff 做对，再考虑更深的 live hardening。**

### 3. 现在应升级成项目级共识的方法

#### 3.1 先做 first-pass family closure，再决定 selective hardening
- 不要在 family 还没成链前就对单个 Stage 做过深 hardening。
- 更合理的节奏是：
  1. family 先成链
  2. 再选最关键位置做 pilot hardening

#### 3.2 只在真实使用失败时 reopen 已完成 Stage
- 对已成型 Stage，不应因为“还可以更漂亮”就回头补。
- 真正值得 reopen 的理由，应来自：
  - 手工试跑失败
  - 下游 Stage 消费失败
  - 真实 blocker 暴露

#### 3.3 “可消费” 与 “可开工/可放行” 必须分开表达
- 第三阶段尤其需要区分：
  - control-consumable
  - runnable-readiness-complete
  - downstream-passable
- 这个区分应该继续沉入后续 family 的 output / decision / verification 规则中。

---

## 九、当前阶段进入条件（更新版）

当满足以下条件时，可以认为项目已从基础设施期切换到四大阶段 first-pass 建设完成，并进入“试跑 / hardening / 收敛期”：

- [x] 至少两个项目级 Meta Skills 达到阶段稳定基线
- [x] 文档库抽取任务完成并形成可复用治理方法
- [x] 协作文档与角色分工清楚
- [x] 第一批阶段 Skills 范围冻结
- [x] 第一批阶段 Skills 的输入/输出/门槛/交付物开始正式定义
- [x] 第三阶段（实现 / 开发）family structure 冻结
- [x] 第三阶段的输入/输出/门槛/交付物开始正式定义
- [x] 第三阶段 first-pass 3-stage runtime chain 已形成
- [x] 第三阶段 family README 与 first-pass checkpoint 已建立
- [x] 第三阶段完成至少一处 selective hardening 试点
- [x] 第四阶段（测试 / 验证）family structure 冻结
- [x] 第四阶段的输入/输出/门槛/交付物开始正式定义
- [x] 第四阶段 first-pass 3-stage runtime chain 已形成
- [x] 第四阶段 family README、audit/self-test checkpoint 已建立

当前状态：

> 已完成 Phase-1 / Phase-2 / Phase-3 / Phase-4 的 first-pass family 建设，应进入跨阶段收敛、整体回顾补漏、真实试跑与选择性 hardening。

---

## 十、一句话结论

当前项目不应继续把主要精力放在 Meta Skills 扩张或抽取扩库上，
而应把 Phase-1 / Phase-2 / Phase-3 / Phase-4 已验证过的控制面与工程方法，转化为：

> 一个可整体回顾、可选择性补漏、可持续收敛，并为后续阶段准备提供稳定上游的跨阶段 Stage Skill 工程系统。
