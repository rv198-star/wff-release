# Stage Skill Construction Lifecycle Reference（v0.1）

## 目的

这份文档是 `wff-meta-stage-skill-construction-lifecycle` 元技能的 supporting reference。

它不是 Skill 的替代，而是更长的说明稿，用于承载：

- 全流程 checklist
- 产物分层说明
- 每一步应产生哪些中间工件
- 什么时候该停、什么时候该继续

---

## 1. 生命周期总览

### A. 素材准备
- 明确阶段目标
- 明确来源容器
- 建 `source-register`
- 建 `source-unit-coverage-ledger`

### B. 编写前准备
- `stage-charter`
- `rule-cards`
- `merge-decisions`
- `binding-matrix`

### C. 正式编写
- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

### D. 审计与追踪
- 中文镜像（如需）
- traceability naming / binding
- core deliverables coverage

### E. 验证
- self-test case
- dry-run output
- verification report
- robustness coverage（如有必要）

### F. 复盘与交接
- source coverage audit
- template-unit ledger（如需）
- runtime vs audit vs design-time segregation
- next-session handoff

---

## 2. 每一步的 stopping criteria

### 素材准备结束的标准
- source coverage 不再只停留在 bundle/book 级印象
- omission reason 已写清

### 编写前准备结束的标准
- 规则不再分散在脑中
- merge / binding 已清楚

### 正式编写结束的标准
- runtime 4 件套齐全
- 核心阶段职责明确

### 验证结束的标准
- 至少有 1 个 valid-input dry-run
- 有 verification report

### 复盘结束的标准
- 当前新增资产已被分层为 runtime / audit / design-time
- 下个阶段或下个会话有明确入口

---

## 3. 当前 repo 中可直接复用的 supporting assets

- `docs/stage-skill-authoring-workflow-v0.1.md`
- `docs/governance/design-time-vs-runtime-artifacts-segregation-v0.1.md`
- `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`
- `skills/wff-meta-source-unit-coverage-ledger/SKILL.md`
- `skills/wff-base-traceability-management/SKILL.md`

---

## 4. 建议的下阶段启动顺序

如果要开始下一个大阶段（如 design / architecture），推荐顺序：

1. 复制 shared spine 思路
2. 先建立 source-register 和 unit-level coverage ledger
3. 再建立 stage-charter / rule-cards / merge-decisions / binding-matrix
4. 再写 runtime 4 件套
5. 再做 self-test / dry-run / verification

---

## 5. 这份 reference 不该替代什么

它不替代：
- runtime package 本身
- source-unit ledger 本身
- traceability registry 本身

它只是作为元技能的长说明稿存在。
