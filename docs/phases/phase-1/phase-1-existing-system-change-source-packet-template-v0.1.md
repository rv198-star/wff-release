# Phase-1 Existing-System Change Source Packet Template（v0.1）

本模板保留标准 `P1 Source Input Packet` 外壳，让当前 P1 工具仍可把 `P1 Source Brief` 当作事实输入面来读取。

当输入来自已有系统上的需求变更、功能新增、改造或范围收敛时使用本模板。生产方可以是 PhaseX、人类评审者，或其他上游整理步骤。

规则：

- 不要混写已观察事实和推断含义。
- 不要把当前系统行为自动写成目标行为，除非用户明确要求保留。
- 不要静默解决来源冲突。
- 不要把代码、数据库、接口、性能或架构观察写成 P1 自己负责判断的架构真相。

---

# P1 Source Input Packet

- `packet_subtype`: `existing-system-change`
- `producer`: `PhaseX | human | other`
- `source_status`: `observed | mixed | inference-heavy`
- `admission_status`: `ready-for-P1 | provisional-ready-for-P1 | not-admission-ready`
- `case_id`: `<case-id>`
- `prepared_at`: `<YYYY-MM-DD>`

## P1 Source Brief

### Current State Summary

描述现有系统今天看起来如何工作。

这里是现状背景。除非明确要求保留，否则不要把它写成目标设计。

### Target Change Summary

描述本次请求的变更、新增、替换、改进或范围收敛。

如果这里不清楚，把输入包标为 `not-admission-ready` 或 `provisional-ready-for-P1`。

### Observed Business Facts

只列有来源证据支撑的事实，例如代码行为、配置、数据库结构、文档、运行观察或用户确认。

每条都应带一个简短证据指针。

### Inferred Business Semantics

列出从现有系统推断出来的业务含义。

每条都必须保留推断标签，并说明为什么这样推断。

### Legacy Behaviors To Preserve

列出本次变更不能破坏的历史行为。

如果“必须保留”只是推测而非确认，应标为 review-bound。

### Source Conflicts

列出代码、数据、文档、运行观察和用户说法之间的冲突。

除非来源明确确认，否则不要自行选择哪个版本是真相。

### Non-Goals

列出本次变更不处理的内容。

### Acceptance Pressure

列出会影响验收标准的业务、用户、运营、合规或评审压力。

## Demand Change Evaluation

这一节只判断“这个变更需求是否清楚、是否值得进入 P1 收敛”。It does not decide architecture, database, code, or implementation plan.

### Change Intent

说明用户这次到底想新增、修改、替换、提升或收敛什么。

如果目标只是一句模糊愿望，应标为 `return-to-intake` 或 `review-bound-provisional`。

### Business Impact

说明这次变更解决什么业务价值、损失、风险、运营压力、用户压力或评审压力。

不要把技术指标直接写成业务影响；如果只能看到技术现象，应说明它可能造成的业务压力或标为 review-bound。

### Affected Users / Workflows

列出受影响的用户、角色、工作流、报表、决策点或服务时刻。

如果只知道系统模块、不知道业务流程或用户影响，应标为 review-bound。

### Non-Goals / Scope Boundaries

列出本次变更不处理的内容，以及不应被当前系统现状顺手带入的范围。

### Proceed Decision

- `decision`: `proceed-to-P1 | return-to-intake | review-bound-provisional`
- `reason`: `<why this decision is appropriate>`
- `visible_gaps`: `<what P1 must preserve as open or review-bound>`

### Demand Clarification Questions

由 PX 或上游整理步骤生成少量高价值问题，帮助 P1 在正式收敛前补齐需求目标。

问题应聚焦五类内容：

- 业务目标
- 成功标准
- 优先用户 / 工作流
- 范围边界
- 证据来源与无人确认时的保守默认

### Demand Clarification Addendum

如果用户、Owner、操作者或其他可信来源提供补充答案，记录在这里。

- `clarification_status`: `not-answered | answered`
- `response_source`: `<who or what supplied the answer>`
- `target_success_boundary`: `<what target means in practical terms>`
- `acceptance_boundary`: `<what threshold makes the change acceptable>`
- `priority_users_workflows`: `<which users/workflows are P0/P1>`
- `scope_confirmation`: `<what must stay out or remain unchanged>`
- `compatibility_confirmation`: `<what compatibility promise must hold>`
- `conservative_default_if_unanswered`: `<safe default if later evidence is absent>`
- `remaining_review_bound_items`: `<what is still not confirmed>`

缺失答案不得阻塞 P1。已有答案只能作为 source clarification 使用，不等于 Owner 签字、UAT、真实市场验证、生产就绪或生产风险接受。

## Truth-State Ledger

| Item ID | Statement | Truth State | Evidence Pointer | P1 Handling |
|---|---|---|---|---|
| TS-001 | `<statement>` | `observed | inferred | unknown | conflict | user-confirmed | review-bound` | `<file/line/doc/user note>` | `<fact base / constraint / acceptance boundary / open gap / P2 clue>` |

## Open Truth Gaps

| Gap ID | Missing Truth | Why It Matters | Required Clarification |
|---|---|---|---|
| GAP-001 | `<missing truth>` | `<impact>` | `<question or evidence needed>` |

## Reviewer Concerns

列出 P1 评审者必须持续看见的问题，尤其是推断较重、来源冲突、目标变更不清楚的部分。

## Admission Decision

- `admission_status`: `ready-for-P1 | provisional-ready-for-P1 | not-admission-ready`
- `claim_ceiling`: `<what P1 may and may not claim from this packet>`
- `reason`: `<short reason>`

## Handoff Note For wff-req

说明 `wff-req` 应如何消费这个输入包：

- 哪些事实可以安全进入 PRD 事实基础
- 哪些内容必须保持 review-bound
- 哪些历史行为应转成约束或验收边界
- 哪些架构、数据库、接口、性能或代码质量观察只能作为 P2 线索
