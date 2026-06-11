# P1 Value-Bearing Artifact Closure（v0.1）

状态：`WO-119A.07` 本地验证记录
日期：2026-05-03
所属工单：`WO-119A.07`
控制边界：`docs/governance/v1.3-product-flow-control-boundary-v0.1.md`
Stage Judgment Lens：`docs/governance/v1.3-stage-judgment-lens-v0.1.md`
英文镜像：`docs/phases/phase-1/p1-value-bearing-artifact-closure-v0.1.md`

## 目的

本文定义 `v1.3.1` Phase-1 product requirements 的 closure expectation。

P1 closure 必须证明 product requirement package 具备足够的 product、business、user、acceptance 和 source-truth value，使 P2 能基于它设计，而不需要编造缺失的 product truth。

## Closure Rule

P1 只有在输出对以下内容做出实质判断时，才可以 close：

- product value；
- business value；
- user 或 stakeholder value；
- pain strength 和 status quo pressure；
- narrowest valuable wedge；
- acceptance meaning；
- source truth confidence；
- open truth gaps 和 review-bound carryover。

Format completeness、trace closure、PRD assembly、convergence score 或 script pass 都只是 support signals。它们本身不足以构成 value-bearing closure。

## Required Closure Statement

P1 closeout surface 应说明：

- 当前值得推进的 product wedge 是什么；
- 它服务谁的问题或决策；
- 为什么 status quo 不足；
- 应保护的 smallest valuable slice 是什么；
- 哪些 source facts 足够强，可以驱动 architecture；
- 哪些事实仍然 review-bound；
- package 可以继续到 P2、需要 bounded P1 remediation，还是必须返回 pre-P1 source admission。

## Failure And Routing

Findings 路由如下：

- `源头事实缺口`（`source-truth-gap`）-> pre-P1 admission 或 P1，取决于 source 是否存在以及是否被 P1 mishandled；
- `产品/规格缺口`（`product-spec-gap`）-> P1 remediation；
- architecture、implementation 或 evidence issues -> 只有当 P1 truth 已充分时才进入下游 phase。

如果 P2 还需要编造 product goal、business value、user value、acceptance meaning 或 status quo pressure，则 P1 尚未 value-bearing closed。

## No-Gain Disclosure Rule

高分不等于价值增益。

如果 P1 run 得分较高，但没有选择 Agentic deepening target，closeout 必须做三选一：

- 标记结果为 `stable-no-material-gain`；
- 选择一个 bounded high-value deepening target，并对该 target rerun / remediate；
- 解释为什么再做一轮 deepening 不太可能产生有意义的 product 或 business value。

不得把 `target_count: 0` 加高分表述成 `v1.3.1` 已经提升 P1 输出质量的证明。

## 本地验证问题

如果本文和 P1 skill mirror 明确说明 P1 closure 是 product-value 和 source-truth judgment，而不是 PRD format completion，则 `WO-119A.07` 完成。
