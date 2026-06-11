# 项目当前共识清单（短版）

## 这份文档是做什么的

这是给**新会话 / 上下文切换 / 新协作者接手**时优先阅读的短版 operating brief。

如果时间只够读一份文档，先读这份；
如果还需要更多上下文，再读：

- `docs/v1.2-design-principles-v0.1.md`
- `docs/current-canonical-reference-map-v0.1.md`
- `docs/phase-retrospective-and-next-step.md`
- `docs/blueprint.md`
- `docs/mvp-scope.md`

补充边界：

- `docs/plans/` 默认视为历史 planning / checkpoint 快照目录，不是当前 canonical truth 的首选入口

如果当前工作属于 `v1.2` 结构优化 / 设计纠偏 / 评分体系冻结，优先增加一条阅读规则：

> **先读 `docs/v1.2-design-principles-v0.1.md`，再做局部设计或实现判断。**

如果当前分歧属于：

- 某个阶段到底该更偏 `Workflow` 还是更偏 `Agentic`
- 哪些复杂度应留在主线，哪些应退出为 optional lane
- 是否又在用脚本替代判断

则补充阅读：

- `runtime-deps/mindthus/source/skills/wae/SKILL.md`

如果当前分歧属于：

- 该阶段到底算不算通过
- 应该给 `PASS`、`PASS with review-bound items`、`RETURN-REMEDIATE` 还是 `BLOCKED`
- 评分到底该看什么，不该看什么

则补充阅读：

- `docs/v1.2-mainline-scoring-and-acceptance-matrix-v0.1.md`

如果当前分歧属于：

- `P1` 是否还应继续 deep loop
- `P2` 是否该主要依赖 checklist / focused review
- `P1/P2` 是否用了错误的思维模式

则补充阅读：

- `docs/v1.2-phase-thinking-mode-split-v0.1.md`

---

## 1. 项目现在是什么

这个项目不是 prompt 库，也不是零散技能合集。

当前稳定共识是：

> 这是一个 **AI-first 的软件工程 Meta Skills 工程系统**，用 artifact contract、gate/refusal、阶段 handoff、知识底座和方法治理，把复杂研发过程重组为 AI 可执行、可审计、可渐进增强的系统。

---

## 2. 当前已完成到什么程度

当前已经完成：

- Phase-1（产品 / 需求）first-pass family
- Phase-2（设计 / 架构）first-pass family
- Phase-3（实现 / 开发）first-pass family
- Phase-4（测试 / 验证）first-pass family

当前已确认、但尚未进入默认主链的扩展方向：

- `PhaseX`：brownfield / legacy / refactoring / migration 场景的特殊扩展轨
- 它的定位不是新的默认 Phase-5，而是 P1-P4 之外的 sidecar family incubation track
- 当前应先保持为 design/planning draft，并优先考虑最小可用集落地，而不是一次性铺开全部 Skill

也就是说：

> 四个主阶段 family 都已经进入“可手工调用、可试跑、可审查”的 first-pass authored package 形态。

---

## 3. 当前主控制面是什么

现在最稳定的主控制面不是制度流程，而是：

- artifacts
- gates / refusal
- contracts
- stage handoffs
- source governance
- verification / robustness

一句话：

> **artifact-first，gate-explicit，handoff-explicit。**

---

## 4. 跨阶段已经验证成立的共识

### 4.1 control artifacts 先于 runtime prose
先冻结控制面，再写 runtime 包，稳定性更高。

### 4.2 README-level human entry 很重要
family README 能回答“这是什么、怎么用、边界在哪”，阶段包才真正可接手。

### 4.3 shape consistency 本身是产品特性
runtime 4-pack、verification、robustness、audit mirror 保持结构平行，会显著降低续写成本。

### 4.4 happy-path verification 不够
必须配套 self-test / dry-run / robustness，才能防止 false-readiness / fake-output。

### 4.5 跨阶段 basic usability 的最低证明标准
当前仓库的最低证明标准不应该只是“每个 phase 都有包”。

而应该是：

> **至少存在一个 sufficiently complete 的 happy-path case，能够从 Phase-1 贯穿到 Phase-4，而不在 family-level handoff 上被拒绝。**

如果做不到这一点，就还不能说整个跨阶段 package system 具备基本可用性。

---

## 5. 第三阶段带来的新共识

### 5.1 Phase-3 的 source strategy 应该是 web/template-first
实现 / 开发阶段很多关键素材更适合来自：

- 官方工程文档
- 真实项目模板
- 开源实现实践

书籍仍然重要，但更适合作为 backbone / anti-pattern / rationale 支撑，而不是主来源。

### 5.2 blocked / review-bound 输出本身是有效产物
“不能开工”如果表达清楚，就是有效 gate 结果，不是失败。

### 5.3 selective hardening 比全面对称 hardening 更划算
先在最关键入口 Stage 做 pilot hardening，比机械地给所有 Stage 补同样深度更值。

---

## 6. 当前最不该做的事

- 不要继续优先扩展新的 Meta Skills
- 不要继续大面积扩展文档库抽取范围
- 不要为了对称性继续堆文件
- 不要在没有真实 blocker 的情况下 reopen 已完成 Stage

---

## 7. 当前最该做的事

当前最合理的工作模式是：

1. 做跨阶段收敛 / 回顾 / 补漏
2. 只在真实 review 或试跑暴露问题时做 selective patching / hardening
3. 把经验继续沉回项目级 checklist / retrospective / hardening targets
4. 优先补跨阶段执行控制面（convergence driver / execution report），把 stage runtime packs 组织成真实案例可回放、可判级、可汇总的运行系统

一句话：

> **从“继续造包”切到“跨阶段收敛 + 验证可用性 + 定点硬化”。**

当前已经出现一个经过 GEO 案例压测后更明确的新 hardening 方向：

> **补 Phase-1 Convergence Driver + Phase-1 Execution Report，让“单输入案例 → Stage-01~04 → Unified Product Pack → Admission Recommendation”成为可重复回放的运行路径。**

这个方向当前属于一期能力闭环的一部分，而不是二期 adoption 包装。

另一个已经被明确记录、但当前**不着急立即修改**的 insight 是：

> **当前 Phase-1 偏强于结构化、gate、handoff 与 warning/reporting 语义，但仍明显弱于真正的产品分析深化。**

具体表现为：

- 当前系统更容易生成“结构完整的 summary/workpack”
- 但还不够容易生成“有 alternatives、trade-offs、why-this-not-that、渐进式澄清与决策理由”的高质量产品分析文档

后续可参考：

- `external-projects/Product-Manager-Skills/`
- 其中接近 AWS / PM 风格的问题，不是“多几个字段”，而是“把 guided questioning、decision points、trade-off articulation、interactive discovery 做成 runtime 主行为”

这条 insight 当前应被理解为：

- 已记录
- 已确认方向有价值
- 但暂不抢在当前一期主线前立即大改 Stage family

进一步校正项目级认识：

> **项目此前主要定义了软件生命周期中的流程、规范、模板与最终产出物约束，但没有把“思考、分析、博弈、取舍、渐进式澄清”编码为 Skills 的 runtime 主行为。**

这导致当前系统更容易：

- 严格遵循模板
- 严格走阶段流程
- 严格输出结构化文档

却不够容易：

- 自动进行深度问题分析
- 比较 alternatives 与 trade-offs
- 形成 why-this-not-that 的决策理由
- 通过多轮澄清把内容真正“增厚”为高判断力产品文档

当前最重要的项目纠偏不是继续扩 output 约束，而是：

> **在项目层面补“thinking runtime”，并从 Phase-1 开始学习 AWS / PM Skills / Superpowers 的 guided questioning、interactive discovery、decision points、trade-off articulation、incremental validation。**

这条纠偏在 `v1.2` 里已经进一步具体化为：

- `P1` 默认更偏 `Agentic-dominant within bounded workflow`
- `P2` 默认更偏 `Workflow-supported checklist + focused review`
- `P3` 默认更偏 `Workflow-dominant backend mainline + targeted agentic loops`
- `P4` 默认更偏 `Workflow-supported adversarial review + explicit closure judgment`

具体执行矩阵见：

- `runtime-deps/mindthus/source/skills/wae/SKILL.md`

这里的 thinking runtime 也已经进一步明确为：

- 不是脱离素材库的自由脑补
- 而是要主要结合方法论卡片与反模式卡片进行 **method-guided reasoning**
- 模板和 SOP 继续作为结构层 / 流程层存在，不是 thinking 深度的主要来源

同时，当前也已经明确：

> **Phase-1 的 thinking runtime 不应是一遍 enrich 就结束，也不应无限脑暴；应采用 bounded thinking loop。**

该 loop 当前已被定义为：

- 每个 Stage 默认 1 个结构化 draft + 最多 3 轮 deepening
- 之后必须进入 `freeze` / `return-remediate` / `blocked` 之一
- 其目标是让输出从“结构化合格”提升为“分析上足够可用”，但不牺牲阶段收敛性

补充说明：

- 第 3 轮不是重新发散探索，而是**最终整合轮**
- 它只用于把已经出现的高价值 reasoning 改进收敛成稳定阶段结果
- Thinking loop 的单元当前也已明确：**按阶段输入/输出物单元拆分，而不是按抽象复杂度拆分**

这条纠偏当前应被理解为：

- 已明确为正确问题定义
- 应先作为学习与设计方向保留
- 不在本轮立即重写整套 Stage Skills

另一个已经明确的新共识是：

> **Phase-2 不应把“核心思考质量”与“技术武器重量”混成同一套分档。**

更准确的控制原则应是：

- 最低论证纪律尽量固定，而不是按小项目/大项目随意降级
- 高规格设计方式可以长期保持，例如 service-first / interface-first / test-first / IoC 等解耦设计
- 真正需要分档的是部署 / 基础设施姿态，而不是把高规格设计本身打成重型方案
- complexity-profile 更适合控制产物阈值与设计密度，不应被理解为“自动允许更重部署方案”
- AI 不应自由升档部署姿态
- 人类可以强制升档，但必须显式给出 warning，并记录额外风险

这条共识当前已沉淀为：

- `docs/phases/phase-2/phase-2-deployment-posture-tiering-rule-v0.2.md`

另一个已经明确的新收敛方向是：

> **Phase-1 的最终交付体验不应停留在分散 stage outputs + lightweight convergence pack，而应进一步收敛为一份完整 PRD 主文档。**

当前已经新增：

- `docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md`

它借用 PM Skills 的 PRD 主结构，但保留本项目自己的：

- stage-derived content mapping
- review-bound / constrained-admission semantics
- Mermaid / UML 作为 Use Case、活动流、slice map、validation flow 的正式表达方式

进一步说，当前项目已经明确采用“两期目标切分”：

### 当前一期目标（优先级最高）

> **先把四大阶段从 first-pass package completeness，推进到足以稳定产出 runnable business project。**

这意味着当前最重要的验证标准，不应停留在“happy-path 不被 family-level handoff 拒绝”，而应继续追问：

- 这条链路是否能落到真实业务案例
- 是否能从 package truth 走到 runnable project truth
- 暴露出来的真实 gap 是否被系统吸收

### 当前二期目标（暂不抢跑）

> **在一期能力闭环成立后，再做 adoption / productization，包括 intent-first 入口、role-legible 导航、安装/注册、quickstart 等。**

当前不应让二期目标反客为主，否则容易出现“包装先于能力闭环”。

---

## 8. 当前 Phase-3 / Phase-4 的最准状态

Phase-3 现在已经：

- 完成 first-pass 3-stage runtime chain
- 完成 family-level consolidation
- 完成 Stage-01 selective hardening
- 完成至少一次真实 Stage-01 手工试跑

Phase-4 现在已经：

- 完成 first-pass 3-stage runtime chain
- 完成 family-level consolidation
- 完成 rule-level robustness coverage
- 完成 bilingual audit coverage（runtime / verification / robustness）
- 完成第一轮 audit/self-test checkpoint

但它还不等于：

- 全面 live runtime hardening
- 全部 adversarial-path 已验证
- registry/install-level packaging 完成

---

## 9. 当前推荐的 reopen / 继续条件

只有在以下情况发生时，才值得 reopen 某个已完成 Stage：

- 手工试跑失败
- 下游 Stage 消费失败
- 真实 blocker 暴露

否则默认：

> 保持当前包形态，避免无收益返工。

---

## 10. 一句话结论

当前项目已经从“基础设施建设期”进入：

> **四大阶段 first-pass family 已完成；当前应以跨阶段收敛、真实案例压测、选择性补漏为主，把系统推进到 runnable-project proof；之后再进入 adoption/productization 的二期。**

补充一条当前最重要的可用性判断：

> **happy-path 贯穿 Phase-1 → Phase-4，是当前跨阶段 package system 的 basic usability proof。**

但这还不是一期完成标准；一期真正想达到的是：

> **cross-phase runnable-project proof。**
