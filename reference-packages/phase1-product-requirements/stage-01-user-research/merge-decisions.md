# Stage-01 Merge Decisions — requirements-user-research

## 目的

记录 Stage-01 在 rule-cards 层面的重复、冲突与 precedence 决议。

---

## Cluster A — Stage-01 核心输出闭环

### 涉及规则
- RC-03 用户群边界
- RC-04 User Case / User Story 草案
- RC-05 问题 / 机会清单
- RC-06 可供 Stage-02 消费

### 决议
- KEEP-SEPARATE-BUT-LINKED

### 原因
- 这四条共同组成 Stage-01 的最小输出闭环
- 但它们不是同一条规则，不能粗暴合并成“输出结构化结论”一条

---

## Cluster B — Intake / Provisional 边界

### 涉及规则
- RC-08 状态机推进
- RC-09 不得把 inferred 内容当 confirmed input
- RC-10 provisional 标记要求
- RC-19 cannot_infer
- RC-20 can_provisionally_infer

### 决议
- KEEP-SEPARATE-BUT-LINKED

### 原因
- 这是同一治理链，但分属不同控制点：流程、禁止项、标记、字段边界、允许推演项
- 若合并成一条，会掩盖真正的 gate 细节

---

## Cluster C — 方法来源分工

### 涉及规则
- RC-12 Stage-01 四个核心 source bundles
- RC-13 product-demand-fit 角色
- RC-14 behind-the-scenes-product 角色
- RC-15 inspired 角色
- RC-16 lean-product-development 角色

### 决议
- KEEP-SEPARATE-BUT-LINKED

### 原因
- RC-12 定义“选谁”
- RC-13~16 定义“各自负责什么”
- 需要保持 bundle selection 与 bundle role 的分离

---

## 冲突与 precedence 说明

当前未发现实质冲突；已有规则可按以下 precedence 稳定解释：

1. Repo policy / Phase-1 gate docs
2. Skill authoring constraints
3. Source index / stage package definitions
4. Book-derived guidance
5. Existing sample package wording

### 具体结论
- 若样板包 wording 与 Phase-1 新 policy 不一致，以 Phase-1 policy 为准
- 若书本方法资产与 gate / refusal 冲突，以 gate / refusal 为准
- 若 PM Skills facilitation 允许继续推进，但 Stage-01 gate 不足，则只能保持 provisional，不得直接 pass gate
