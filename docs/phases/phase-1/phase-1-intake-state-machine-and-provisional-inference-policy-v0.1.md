# 第一阶段（产品 / 需求）Intake State Machine 与 Provisional Inference Policy（v0.1）

## 目的

本文件定义第一阶段（产品 / 需求）在正式构建 Stage Skills 之前必须冻结的启动机制：

- 当用户只给出一句模糊描述时，AI 应如何启动
- 什么时候应继续澄清，什么时候应拒绝推进
- 在用户强行要求推进时，AI 是否允许推演 provisional package
- 哪些字段允许推演，哪些字段不能推演
- 什么条件下才允许进入下一阶段

这份文档的定位不是“对话技巧建议”，而是第一阶段的 **state machine + governance policy**。

它与以下文档共同组成 Phase-1 的正式启动约束：

- `docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md`
- `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`

---

## 1. 核心原则

### 1.1 AI 的角色

在第一阶段，AI 不是“替用户决定方向”的 authority，而是：

- intake orchestrator
- clarification facilitator
- artifact drafter
- gatekeeper

也就是说：

- AI 可以帮助用户把模糊想法收束成结构化输入
- AI 可以推演 provisional draft
- AI 不可以把未验证推演内容伪装成真实事实输入

### 1.2 State Machine 高于自由发挥

第一阶段默认不采用“想到哪问到哪”的自由聊天模式。

所有启动都应落在以下状态机中：

- `S0 Intake Received`
- `S1 Clarification Active`
- `S2 Blocked`
- `S3 Provisional Inference`
- `S4 User Review`
- `S5 Gate Pass`
- `S6 Escalate`

---

## 2. 状态定义

## S0 — Intake Received

### 含义
用户刚表达了“想做什么”，但系统还未判断是否已具备进入正式收束的最小信息。

### 允许动作
- 记录用户原始描述
- 识别初步问题域 / 目标域
- 进入 `S1 Clarification Active`

### 不允许动作
- 直接进入下游阶段
- 直接给出“已完成需求分析”类结论

---

## S1 — Clarification Active

### 含义
AI 进入结构化澄清阶段，目的是补齐最小启动信息，而不是立刻产出完整方案。

### 默认行为
- 优先采用 PM Skills 的 facilitation pattern：
  - one-step-at-a-time
  - Guided / Context dump / Best guess
  - assumptions / risks / next steps 显式化

### 本阶段至少要尝试补齐的内容
- 用户想解决什么问题
- 用户希望为谁解决
- 当前为什么值得做 / 为什么现在做
- 已知约束或排除项
- 已有证据 / 经验 / 参考信息

### 可触发的后续状态
- 信息已达到最低条件 → `S5 Gate Pass`
- 关键字段缺失且无法合理推进 → `S2 Blocked`
- 用户明确要求“先推一版看看” → `S3 Provisional Inference`

---

## S2 — Blocked

### 含义
当前信息不足以进入正式下游阶段，且缺失的是硬约束字段。

### 典型触发条件
- 连研究对象 / 目标用户都不清楚
- 连问题/机会描述都不清楚
- 连业务目标或约束边界都完全缺失

### 默认动作
- 明确告知缺失项
- 指出不能推进的原因
- 给出用户可补充的信息清单

### 可触发的后续状态
- 用户补齐关键信息 → 回到 `S1 Clarification Active`
- 用户明确要求 AI 先推一版 → `S3 Provisional Inference`
- 涉及高风险/高歧义/需真实人类外部验证 → `S6 Escalate`

---

## S3 — Provisional Inference

### 含义
用户明知关键输入不完整，仍要求系统先推演一版可评审草案。AI 可以继续，但只能生成 **provisional / inferred draft**。

### 前置条件
- 用户已被明确告知当前信息不足
- 用户已明确要求继续推进或接受 provisional 模式

### 允许动作
- 基于用户信息 + 公开资料 + repo 方法资产推演草案
- 给出初版 problem framing / user case / story map / MVP slicing / validation assumptions

### 不允许动作
- 把 inferred 内容写成 confirmed input
- 绕过后续用户评审直接进入下一阶段

### 强制标记要求

所有 provisional artifact 必须在文档级或区块级显式标记：

- `status: provisional`
- `source: user | inferred | external`
- `confidence: high | medium | low`
- `verification: required | waived`

并追加：

- `AI-INFERRED DRAFT — UNVERIFIED`
- `assumptions`
- `assumptions_to_validate`
- `what_changes_if_wrong`

### 可触发的后续状态
- provisional 草案已生成 → `S4 User Review`

---

## S4 — User Review

### 含义
用户对 provisional draft 进行审阅，决定哪些内容接受、哪些内容修正、哪些内容拒绝。

### 默认动作
- 要求用户确认关键字段
- 要求用户指出错误 assumptions
- 要求用户确认是否接受风险并继续

### 必须明确的结论类型
- `accept`
- `accept_with_corrections`
- `reject_and_return`

### 可触发的后续状态
- 关键字段被确认 / 被显式 waive → `S5 Gate Pass`
- 用户指出缺口或反对推演 → 回到 `S1 Clarification Active` 或 `S2 Blocked`

---

## S5 — Gate Pass

### 含义
当前阶段的最小准入已满足，允许进入下一阶段。

### 必须满足的条件
- 关键字段已确认，或
- 用户已对关键缺失项做显式风险接受（waive），且该字段不属于“cannot infer”类
- 当前输出满足对应阶段的 gate / refusal / output 最低要求

### 注意
`useful for thinking` 不等于 `sufficient for progression`。

即使 PM Skills 风格的输出已经“很像一个完整方案”，如果未满足本仓库 gate，则不能进入下一阶段。

---

## S6 — Escalate

### 含义
问题已超出 AI 在当前上下文中可靠推进的边界，必须要求真实世界补证据、真实人类判断，或更高级别治理介入。

### 典型触发条件
- 涉及受监管 / 高风险业务
- 必须依赖真实用户访谈而当前没有可信替代
- 争议点会显著影响后续方向，但无足够证据支持推演

---

## 3. 字段分类规则

## 3.1 `cannot_infer`（不能推演）

这类字段缺失时，默认不得把 AI 推演当成可直接过 gate 的事实。

包括但不限于：

- 最终目标用户 / 使用对象的核心边界
- 用户明确不接受的范围 / 禁区
- 关键业务目标 / 成功标准的大方向
- 真实存在的组织/预算/时间/合规约束

规则：
- 缺失时优先 `S2 Blocked`
- 若用户强推，可进入 `S3 Provisional Inference`
- 但没有用户 review/确认，不得 `S5 Gate Pass`

---

## 3.2 `can_provisionally_infer`（可以 provisional 推演）

这类字段可由 AI 先给出“草案级结构”，供用户评审。

包括但不限于：

- proto-persona
- User Case / User Story 初稿
- 关键问题 / 机会清单初稿
- story-map 骨架
- MVP 切片初稿
- 假设清单与验证路径初稿

规则：
- 允许在 `S3 Provisional Inference` 生成
- 必须在 `S4 User Review` 中被确认 / 修正 / 拒绝

---

## 3.3 `must_validate_before_exit`（进入下阶段前必须验证）

这类字段可先写出，但在阶段出口前不能继续保持“默认真实”。

包括但不限于：

- 用户痛点强度
- 用户真实行为模式
- 假设的优先级权重
- 市场/竞品中的关键事实判断
- “这个需求值得做”的高影响证据

规则：
- 可先 provisional
- 但在阶段出口或 handoff 前必须被验证 / 修正 / waive

---

## 4. 状态转换规则（简表）

| From | Trigger | To | Rule |
|---|---|---|---|
| S0 | 接收原始需求描述 | S1 | 默认进入澄清 |
| S1 | 关键字段满足最低条件 | S5 | 可进入当前阶段执行 / 下游阶段 |
| S1 | 关键字段硬缺失 | S2 | 进入 blocked |
| S1 | 用户要求“先推一版” | S3 | 进入 provisional |
| S2 | 用户补充关键信息 | S1 | 回到澄清 |
| S2 | 用户要求继续且接受 provisional 风险 | S3 | 允许 provisional |
| S2 | 高风险 / 高歧义 / 需真实外部证据 | S6 | 升级 |
| S3 | provisional 草案生成 | S4 | 进入用户评审 |
| S4 | 用户确认关键字段或显式 waive | S5 | gate pass |
| S4 | 用户拒绝 / 指出关键错误 | S1 / S2 | 回到澄清或 blocked |

---

## 5. 与阶段 gate 的绑定方式

本状态机只定义“启动与推进方式”，不替代具体 Stage gate。

具体阶段（Stage-01 ~ Stage-04）是否允许通过，仍以：

- `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`

为准。

也就是说：

- state machine 决定 “怎么走”
- stage gate 决定 “走没走到可通过状态”

---

## 6. 对第一阶段 Skill 编写的直接影响

后续所有第一阶段 Stage Skill 至少要显式表达：

- 当前阶段允许的 intake mode
- 缺失输入时进入哪种状态
- 什么字段属于 `cannot_infer`
- 什么字段允许 provisional inference
- 是否必须用户评审后才能进入下游阶段
- 下游 handoff 是否允许携带 provisional 内容，若允许应如何标识

---

## 7. v0.1 结论

第一阶段的正式启动模型应理解为：

> **AI 负责 intake、clarification、drafting 与 gatekeeping；**  
> **用户负责确认关键事实、接受或拒绝 provisional inference、并最终批准推进。**

这使得第一阶段既不会退回“传统纯人类 discovery 流程”，也不会滑向“AI 看起来写得完整就算已确认”的伪完成状态。
