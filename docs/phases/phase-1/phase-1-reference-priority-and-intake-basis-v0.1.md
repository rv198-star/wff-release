# 第一阶段（产品 / 需求）参考优先级与 Intake Basis（v0.1）

## 目的

在正式开发第一阶段 Stage Skills 之前，先冻结一条关键原则：

> 第一阶段（产品 / 需求）不再默认以“传统纯人类团队 discovery 流程”作为主参考源，
> 而是以 **PM Skills 作为前台 intake / discovery orchestration 的首要参考层**，
> 以本仓库现有文档作为 **gate / refusal / handoff / audit 的治理约束层**。

这份文档的目的不是定义完整 Stage Skill，而是定义：

- 第一阶段到底优先参考什么
- 哪些素材负责“怎么启动与推进”
- 哪些素材负责“什么情况下允许推进”
- 当不同来源发生冲突时，以谁为准

---

## 1. 背景判断

当前第一阶段的现实启动方式，与传统 PM / 产品团队的纯人类协作前提已经不同：

- 传统素材大量默认：
  - 多轮用户访谈
  - 多角色面对面讨论
  - PM 作为跨人协作的中心
- 当前项目更真实的启动方式是：
  - 用户先向 AI 简要描述“想做什么”
  - AI 通过澄清问题帮助补齐上下文
  - AI 作为 gatekeeper 判断是否满足进入下一阶段的最小条件
  - 若用户要求加速推进，AI 可以进入 provisional inference 模式，产出可评审草案

因此，第一阶段不应直接照搬“人类 PM 团队 discovery playbook”，而应优先采用更适合 AI-first 工作方式的参考系。

---

## 2. 参考优先级（Reference Priority）

在第一阶段真正进入 Stage Skill 编写时，当前实际使用的参考源不止三类，而是四类：

1. PM Skills（启动 / warm-up / facilitation 技巧层）
2. 本仓库治理与阶段规则（artifact / gate / refusal / handoff 约束层）
3. 书本与抽取素材（方法扩展与跨项目类型补给层）
4. Skill authoring 官方/基准参考源（用于约束 Skill 本身的结构与写法）

其中第 4 类不是第一阶段方法内容的主来源，但在“正式编写 Stage Skill”时是不可缺失的结构性参考层。

## 2.1 Primary：PM Skills（首要参考层，但不是直接挪用层）

第一阶段的 **入口对话、信息收集、澄清补全、assumption 显式化、best-guess 模式**，优先参考 `external-projects/Product-Manager-Skills/`。

但这里的“优先参考”必须明确理解为：

> **借用 PM Skills 已成熟的 startup / warm-up / facilitation 技巧，**
> **而不是直接把 PM Skills 整体原样移植为本项目的第一阶段 Stage Skill。**

换句话说，PM Skills 在第一阶段更像：

- 一个成熟的 intake / warm-up 技巧库
- 一个对话式 discovery / clarification 的行为参考
- 一个从模糊问题走向结构化产物的前台 orchestration 参考

它**不是**：

- 本项目第一阶段的完整 contract 来源
- 本项目最终 output schema / gate schema 的直接来源
- 本项目适用范围的完整上界

它们解决的是：

- 如何从一句模糊需求启动
- 如何问澄清问题，而不是直接进入方案生成
- 如何把 discovery notes / scattered notes 转成结构化产物
- 如何在 context 不完整时继续推进，但不把 assumptions 伪装成事实

它们**没有单独解决完**的是：

- 本项目要求的 artifact-first output contract
- 更强的 gate / refusal / handoff 审计约束
- diagram evidence / traceability / downstream package 规则
- 面向更泛软件项目类型的阶段适配问题

优先吸收的 skill / doc：

- `skills/workshop-facilitation/SKILL.md`
  - 提供 `Guided / Context dump / Best guess` 三种入口模式
  - 明确 one-question-at-a-time、progress labels、assumption labeling
- `START_HERE.md`
  - 明确 “Ask for clarifying questions first”
  - 明确 “Ask up to 3 clarifying questions first, then output markdown, end with assumptions / risks / next steps”
- `skills/problem-framing-canvas/SKILL.md`
  - 适合第一阶段早期问题框定
- `skills/problem-statement/SKILL.md`
  - 适合把用户输入收束成 formal problem statement
- `skills/discovery-process/SKILL.md`
  - 适合定义从问题假设到验证的渐进式流程
- `skills/prd-development/SKILL.md`
  - 适合后半段把 discovery/clarification 产物收束成交付型文档
- `skills/lean-ux-canvas/SKILL.md`
  - 适合显式管理 assumptions / experiments / validation needs

### PM Skills 在第一阶段承担的职责

- intake orchestration
- clarification protocol
- assumption surfacing
- best-guess / provisional drafting
- discovery-to-artifact structuring

### PM Skills 在第一阶段**不直接承担**的职责

- 最终 gate schema 定义
- 最终 refusal / handoff contract 定义
- 最终 output-template 的字段冻结
- 面向所有项目类型的 canonical 阶段边界定义

### 为什么不能直接照搬 PM Skills

1. **它的长处在“启动与澄清”，不在“工程治理闭环”**
   - PM Skills 很强于提问、问题框定、problem statement、PRD structuring、assumptions surfacing。
   - 但本项目要求的不只是“把需求聊清楚”，还要求：
     - output 必须可交接
     - gate / refusal 必须可判定
     - 下游设计 / 架构 / 开发阶段必须能稳定消费

2. **它的案例与语境具有明显的 PM / SaaS / onboarding / churn 倾向**
   - PM Skills 的大量示例都围绕 onboarding、retention、activation、churn、B2B/B2C SaaS 等典型 PM 场景。
   - 这些技巧对第一阶段 warm-up 很有价值，但不能自动代表：
     - 桌面软件
     - 内部系统
     - workflow automation
     - agentic tools
     - 非 SaaS 的复杂软件项目

3. **本项目目标是软件工程 Meta Skills，而不是 PM-only Skills**
   - `README.md` 明确本仓库目标是软件工程生命周期 Meta Skills，强调 multi-lane、artifact-first、gate/handoff。
   - 因此第一阶段必须吸收 PM Skills 的长处，但不能被其领域边界反向限定。

---

## 2.2 Secondary：本仓库现有 Stage Governance（治理约束层，也是 PM Skills 的约束吸收层）

本仓库现有文档不作为第一阶段“如何开启对话”的主参考源，而是作为：

- gate / refusal / handoff 的硬约束
- audit / traceability / diagram evidence 的治理基线
- 阶段链路、产物边界、最小准入的判定标准

更重要的是：

> **本仓库是 PM Skills 的吸收与约束层。**

也就是说：

- PM Skills 提供可复用的 startup / warm-up 技巧
- 本仓库决定这些技巧最后能生成什么类型的 artifact
- 本仓库决定哪些字段必须补齐、哪些缺失必须 refusal、哪些内容只能 provisional

优先依赖：

- `README.md`
  - `AI-first, human-as-fallback`
  - `artifact-first`
  - `gate / refusal / handoff 明确化`
  - `UML / Mermaid required`
- `docs/phases/phase-1/product-requirements-stage-package-v0.md`
  - 定义第一阶段 4 子阶段骨架与文档结构
- `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
  - 定义 required / optional / entry gate / refusal / exit gate
- `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
  - 定义 diagram evidence 的 required/recommended/optional 及最小元素
- `docs/collaboration-ops.md`
  - 定义 docs-first、AI-first、artifact/gate controlled 的操作基调

### 本仓库在第一阶段承担的职责

- gatekeeper logic
- refusal rules
- handoff package definition
- diagram evidence rules
- auditability / traceability boundary

---

## 2.2B Skill Authoring 官方/基准参考源（结构约束层）

这类来源不负责定义第一阶段“产品/需求方法内容”，但负责约束：

- Skill 应如何组织结构
- 触发语义 / instruction 层 / reference note 层如何区分
- 哪些 authoring discipline 应被保留，避免 Skill 文本失控

当前可确认的参考包括：

- Anthropic / Claude Skills 官方文档与格式要求
- `skill-creator` 一类 authoring 规范参考
- 已验证的 `skill-authoring-workflow` 实践参考

这一层的重要性在于：

- PM Skills 解决“怎么启动和澄清”
- 书本素材解决“方法内容从哪里来”
- 本仓库解决“哪些规则能过 gate”
- **但 Skill authoring 官方/基准参考源解决“Skill 这种东西本身该怎么写才稳”**

---

## 2.3 Tertiary：书本/抽取素材（方法扩展与跨项目类型补给层）

`sources/books/extracted/`、`source cards`、overlay package 以及后续桥接资产，主要承担：

- 方法论支撑
- 边界条件
- anti-pattern
- 补充 explanation 与引用基础

它们**不应**继续作为第一阶段 intake 交互协议的主参考源。

原因：

- 它们更擅长方法知识与阶段支撑
- 不擅长定义 AI-first 的对话式 intake 行为
- 若把它们作为第一参考层，容易把第一阶段又拉回“模拟传统人类 PM 团队流程”

但它们在第一阶段仍然非常重要，因为：

- 它们能帮助我们摆脱 PM Skills 自带的 SaaS / PM 语境偏置
- 它们能补齐更广泛项目类型需要的边界条件
- 它们能把第一阶段从“产品 PM warm-up”扩展成“泛软件项目启动与需求收束”

---

## 3. 第一阶段的 Intake Basis（启动基础）

## 3.0 核心定义：不是直接套 PM Skills，而是“PM Skills 启动 + 本仓库约束 + 书本素材扩展”

第一阶段的正确理解应是：

> **PM Skills 提供 startup / warm-up / clarification 行为骨架**  
> **本仓库提供 artifact/gate/handoff 的硬约束骨架**  
> **书本与抽取素材提供跨项目类型的方法扩展与边界补给**

因此，第一阶段既不是：

- 直接照搬 PM Skills
- 也不是回到传统书本流程逐步照抄

而是三层组合后的新入口模型。

## 3.1 默认启动模型

第一阶段默认按以下模式启动：

1. 用户用自然语言简述“想做什么”
2. AI 不立即产出方案，而先进入澄清/问题框定阶段
3. AI 作为 intake orchestrator 收集最小启动信息
4. AI 作为 gatekeeper 判断是否满足进入后续 Stage 的最低条件
5. 若用户强行要求推进，则进入 provisional inference 流程
6. provisional package 必须经用户评审确认后，才能继续进入下游阶段

---

## 3.2 Intake 行为优先遵循 PM Skills facilitation pattern

默认采用以下行为基线：

- **先澄清后输出**
- **一轮一个问题**（one-step-at-a-time）
- **允许三种入口模式**：
  - Guided
  - Context dump
  - Best guess
- **必须显式 assumptions / risks / next steps**
- **若进入 best-guess / provisional 模式，必须把 assumptions to validate 单独列出**

---

## 3.3 Stage progression 优先遵循本仓库 gate / refusal 规则

虽然 intake 行为优先参考 PM Skills，但是否允许进入下一阶段，必须遵循本仓库 gate 文档，而不是仅凭“问得差不多了”。

也就是说：

- PM Skills 负责“怎么把信息问出来”
- 本仓库负责“这些信息是否足以推进”
- 书本/抽取素材负责“如何把第一阶段扩展到更泛项目类型，而不是停留在 SaaS/PM 语境”

---

## 4. 冲突处理原则（Conflict Resolution）

### 4.1 当 PM Skills 倾向继续推进，但本仓库 gate 判定不足时

以本仓库 gate 判定为准。

例如：

- PM Skills 可以通过 best-guess mode 先产出结构化草案
- 但若 `product-requirements-gates-and-minimum-admission-v0.1.md` 判定关键字段未满足
- 则该草案只能保持为 provisional / inferred draft，不能自动视为 gate pass

### 4.2 当本仓库只有阶段骨架，缺少具体 intake / questioning 机制时

以 PM Skills 的 facilitation / interactive pattern 补齐。

也就是说，本仓库不再自行发明一套完全独立的“第一阶段提问行为”，而优先借用 PM Skills 已成熟的模式。

### 4.3 当书本/方法素材与 AI-first intake 行为冲突时

优先保持 AI-first intake 模型稳定，方法素材仅作为补充，而不是反向覆盖入口协议。

---

## 5. 第一阶段后续 Skill 开发的吸收顺序

后续正式开发第一阶段 Stage Skills 时，默认采用以下吸收顺序：

1. **先确定入口模式与 question flow**（来自 PM Skills）
2. **再接入 stage gate / refusal / handoff 约束**（来自本仓库）
3. **最后补入方法资产与 source cards**（来自 references / overlay / extracted-books）

这能保证：

- 不会先被方法素材拉进“重人类流程”
- 不会只学 PM Skills 而失去治理边界
- 不会在阶段骨架尚未稳定时过早做素材细节堆叠

---

## 6. v0.1 结论

第一阶段（产品 / 需求）应明确采用以下分工：

> **PM Skills = 前台 startup / warm-up / discovery orchestrator**  
> **software-lifecycle-skills = 后台 governance / stage gate engine**  
> **references / extracted-books = 跨项目类型的方法扩展与边界补给层**

这意味着：

- 第一阶段优先参考 PM Skills 的 startup / warm-up 技巧，是正式策略，不是临时偏好
- 但第一阶段并不是直接挪用 PM Skills，而是经过本仓库 artifact/gate 体系约束后的吸收式使用
- 本仓库继续保留对 gate / refusal / handoff / audit 的主导权
- 书本与抽取素材不仅是方法资产层，也是 Phase-1 从 SaaS/PM 场景扩展到更泛软件项目类型的重要补给层

这条规则一旦冻结，后续第一阶段 Skill 开发就不需要再反复争论“该先看 PM Skills 还是先看书本/旧模板”。
