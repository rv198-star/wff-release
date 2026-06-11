# PhaseX Wave-1 实施计划（v0.1）

## 1. 目标

把 `PhaseX` 从“10 个 Skill 的完整蓝图”收敛为第一波可实施最小集，优先覆盖：

- 纯技术重构
- 局部需求变更
- 有现有代码库但缺少结构化基线的 brownfield 场景

Wave-1 不追求覆盖全部 brownfield 问题，而是先打通一条可进入、可评估、可保护、可下游衔接的最小 lane。

---

## 2. Wave-1 范围

只落以下 4 个 Skill：

1. `wff-x-scan-code-baseline scan-code-baseline`
2. `wff-x-scan-tech-health scan-tech-health`
3. `wff-x-plan-test-protection plan-test-protection`
4. `wff-x-intake-target-driver target-driver-intake` 的 `target-driver` profile

不纳入 Wave-1：

- `wff-x-scan-db-baseline scan-db-baseline`
- `wff-x-scan-biz-arch scan-biz-arch`
- `wff-x-design-target-arch design-target-arch`
- `wff-x-plan-refactor plan-refactor`
- `wff-x-plan-migration plan-migration`
- `outer-boundary concern outer-boundary-design`

---

## 3. 为什么这样收敛

原因不是这些 Skill 不重要，而是当前仓库缺少第二个 brownfield case，过早铺开会把 PhaseX 做成高复杂、低验证的庞大设计包。

Wave-1 选择这 4 个 Skill，是因为它们刚好构成最小闭环：

- `wff-x-scan-code-baseline` 回答“现在是什么”
- `wff-x-scan-tech-health` 回答“现在哪里最危险”
- `wff-x-plan-test-protection` 回答“动刀前怎么先上护网”
- `wff-x-intake-target-driver` 回答“局部变更如何转成可被 P1/P3 消费的任务或约束”

---

## 4. 目标场景

### 场景 A：纯技术重构

路径：

`wff-x-scan-code-baseline → wff-x-scan-tech-health → wff-x-plan-test-protection → P3 → P4`

### 场景 B：局部需求变更

路径：

`wff-x-scan-code-baseline (局部) → wff-x-intake-target-driver → P1 → P2 → P3 → P4`

### 场景 C：先评估再决定是否继续

路径：

`wff-x-scan-code-baseline → wff-x-scan-tech-health`

输出一份结构化基线和健康评估，供人工决策是否继续进入护网、重构或重回 P1。

---

## 5. 每个 Skill 的最小交付物

### wff-x-scan-code-baseline

最小输出：

- 代码库入口点清单
- 模块/目录结构画像
- 关键依赖图
- 第三方依赖初筛（如有）
- 技术栈清单
- API / route / job / CLI surface 清单
- 可运行性预检结果

### wff-x-scan-tech-health

最小输出：

- 健康评分卡
- Top-N 技术债清单
- 风险矩阵
- 建议优先处理面

默认维度：

- code quality
- test coverage / testability
- dependency health
- coupling / change blast radius
- documentation / operability

### wff-x-plan-test-protection

最小输出：

- safety-net candidate list
- 关键路径测试优先级
- 建议补齐的 contract / integration / smoke test skeleton plan
- 护网有效性判定标准

Wave-1 不要求自动生成所有测试代码，但要能稳定生成优先级清晰、可落地的护网计划。

### wff-x-intake-target-driver

最小输出：

- 变更点说明
- 受影响模块
- 受影响接口 / Schema surface
- 最小验收锚点
- brownfield non-goals
- 兼容性约束
- 建议重入路径：
  - 回 P1
  - 直接进 P3
  - 先补 wff-x-plan-test-protection

---

## 6. 编排策略

Wave-1 不单独做重 orchestrator。

先采用：

- 一个轻量 orchestration doc / profile decision tree
- 每个 Skill 独立 4 件套
- 明确输入/输出/前置条件/下游出口

原因：

- 当前阶段先需要“能用且不歧义”
- 不需要先造一个复杂编排器再验证问题定义

---

## 7. 与 P1 / P3 / P4 的接口

### 对 P1

Wave-1 只做最小接口，不立即重构整套 P1。

需要的最小接口：

- P1 接受来自 `wff-x-intake-target-driver` 的变更需求包
- 变更需求包中保留：
  - baseline constraints
  - compatibility rules
  - affected modules
  - impacted surfaces
  - acceptance criteria
  - recommended route
  - brownfield non-goals

### 对 P3

Wave-1 允许两种出口：

- 技术重构任务包直接进入 P3
- 护网先行任务进入 P3

P3 必须知道这些任务来自 brownfield，不得把它们当成 greenfield 纯新建功能处理。

### 对 P4

Wave-1 不单独重做 P4。

P4 只需接受：

- safety-net execution evidence
- regression / compatibility validation needs
- review-bound legacy constraints

---

## 8. 实施顺序

### Step 1

先写 `PhaseX` 的 repo-level architecture / bootstrap / reading order 文档。

### Step 2

落 `wff-x-scan-code-baseline` 与 `wff-x-scan-tech-health` 的 stage package 4 件套。

### Step 3

补 `wff-x-plan-test-protection`，让“评估完但无法安全开改”的场景有出口。

### Step 4

补 `wff-x-intake-target-driver`，打通“局部变更 → P1/P3”桥。

### Step 5

拿一个真实 brownfield case 做首轮回放。

在没有第二个 case 前，不进入 Wave-2。

---

## 9. 风险与边界

### 风险 1：把 PhaseX 做成新的默认主链

避免方式：

- 明确它是 sidecar family
- 不改写 P1-P4 的默认 greenfield 主链

### 风险 2：过早自动化深度过高

避免方式：

- Wave-1 先做结构提取、评分、计划和约束包
- 不在第一波强上重 AST / 深语义 / 自动大规模改码

### 风险 3：和 P3 重叠

避免方式：

- PhaseX 做“进入前桥接”和“安全改造前护网”
- P3 仍做正式实现

---

## 10. Done 定义

Wave-1 可视为完成，当且仅当：

1. 有一套明确的 PhaseX reading order 和边界定义
2. 4 个 Skill 各自拥有可读的 contract/SOP/template/source-cards
3. 至少 1 个 brownfield case 能完成：
   - baseline extraction
   - health assessment
   - safety-net recommendation
   - target-driver intake package
4. 至少有一个下游入口被真实消费：
   - 回 P1
   - 或直接进入 P3

---

## 11. 一句话结论

PhaseX Wave-1 的目标不是把 brownfield 世界一次性吃完，而是先建立一条能让历史系统安全接入 P1-P4 的最小桥梁。
