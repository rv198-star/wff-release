# 设计时资产 vs 最终 Skill 包资产分层说明（v0.1）

## 目的

本文件用于正式区分：

- 哪些资产属于 **设计 / 编制 / 审查 / 反思** 过程中的中间态资产
- 哪些资产属于 **最终 Skill 包** 的运行时/交付时资产

如果这层不被明确，仓库会持续出现一种错觉：

> 只要资产越来越多，就好像主线越来越膨胀。

但实际情况可能是：

> 增长的是设计时与审计时资产，  
> 而不是最终 Skill 包本体。

---

## 1. 为什么这层区分现在必须冻结

当前仓库已经形成了大量有价值工件，包括：

- shared spine docs
- stage runtime files
- Chinese audit mirrors
- self-test / dry-run / verification reports
- robustness reports
- source coverage audit
- source-unit ledger
- document-library template ledger
- `wff-base-traceability-management` skill
- handoff templates

这些工件并不都应进入最终 Skill 包。

如果不明确分层，会带来两个直接问题：

1. **误判膨胀**
   - 把设计/审计工件也算进“最终包”，自然会觉得系统越来越重。

2. **主线混淆**
   - 执行者无法分清：
     - 哪些是运行时必须资产
     - 哪些只是 authoring / review / audit 资产

---

## 2. 资产分层总则

本仓库的资产应至少分成三层：

### Layer A — 最终运行时资产（Runtime Deliverables）

这些是最终 Skill 包的主体，应尽量稳定、少而硬。

### Layer B — 审计 / 审查资产（Audit / Review Assets）

这些用于：
- 人类审计
- 证据留存
- 质量判断

它们有价值，但不默认进入最终发布包主体。

### Layer C — 设计 / 编制中间态资产（Design-Time / Authoring Assets）

这些用于：
- 目标冻结
- 选材控制
- 冲突决策
- 方法沉淀
- 演进反思

它们是“建造脚手架”，不是最终交付房子。

---

## 3. 哪些属于最终 Skill 包资产

## 3.1 Shared Runtime Spine（共享运行时骨架）

这类资产属于最终系统的 shared runtime layer，应保留：

- `docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md`
- `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`
- `templates/skill-contract.md`
- `templates/stage-sop.md`
- `templates/output-template.md`
- `templates/handoff-checklist.md`
- `templates/handoff-contract.md`

这些资产的共同特点：

- 会直接影响运行时 contract / SOP / output / gate / handoff
- 删除它们会使主线运行失控

---

## 3.2 Stage Runtime Packs（阶段运行时包）

每个 Stage 的最终运行时资产至少包括：

- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

这些才是每个 Stage Skill 最终应该交付给运行时/执行系统的核心包。

---

## 3.3 Chinese Audit Mirrors（条件性运行时伴生资产）

这类文件服务人类审计，但依然和最终包有直接对应关系：

- `*.zh-CN.md`

建议定位：

- **伴生资产**
- 默认不算最终发布包主干
- 但属于正式产物族的一部分

---

## 4. 哪些属于设计/编制中间态资产

以下资产默认应被视为 **design-time / authoring assets**：

- `stage-charter.md`
- `source-register.md`
- `rule-cards.md`
- `merge-decisions.md`
- `binding-matrix.md`

这些资产的共同特点：

- 它们帮助作者把 Skill 写对
- 但最终执行者并不依赖这些文件来运行 Stage Skill

所以它们不应被视为最终 Skill 包必须对外发布的部分。

---

## 5. 哪些属于审计 / 审查资产

以下资产默认应视为 **audit / review assets**：

- `self-test-case.md`
- `self-test-dry-run-output.md`
- `self-test-verification-report.md`
- `robustness-test-case.md`
- `robustness-test-report.md`
- `docs/internal/source-registers/source-coverage-audit-report-v0.1.md`
- `docs/internal/source-registers/phase-1-source-unit-coverage-ledger-v0.1.md`
- `docs/internal/source-registers/phase-1-document-library-template-unit-ledger-v0.1.md`

这些资产的共同特点：

- 它们用于证明“这个 Skill 是怎么被设计、验证、审查出来的”
- 而不是用于“这个 Skill 在运行时要怎么执行”

所以它们应默认保留在仓库中，但不应自动视为最终运行时包的一部分。

---

## 6. Traceability / Meta-Skills 属于哪层

### `wff-base-traceability-management`

应视为：

- **基础设施支撑 Skill**

它不是 Phase-1 单个 Stage 的运行时资产，
但它是整个仓库方法栈的一部分。

### `wff-meta-source-unit-coverage-ledger`

应视为：

- **元技能 / authoring governance skill**

它服务 Stage Skill 创建，不服务单个业务 Stage 的运行时执行。

---

## 7. 判断一个工件属于哪层的标准

问三个问题：

1. 删除它，Stage 还能不能正常运行？
2. 删除它，会不会只影响审计/复盘，而不影响运行？
3. 它主要服务作者，还是主要服务执行者？

### 归类规则

#### 若删除它会让 Stage 运行失控
- 属于 Runtime Deliverable

#### 若删除它主要影响审计/证明，但不影响运行
- 属于 Audit / Review Asset

#### 若删除它主要影响作者写作质量，但不影响最终运行
- 属于 Design-Time / Authoring Asset

---

## 8. 这条分层会如何减少“膨胀感”

当前很多“看起来变重”的部分，实际属于：

- 设计时脚手架
- 审计证据
- 中间态台账

一旦把它们从最终 Skill 包主线里剥离出来，主线就会重新收束成：

- shared runtime spine
- stage runtime packs
- optional zh audit mirrors

这比“把所有工件都算最终包”的感觉要轻得多，也更真实。

---

## 9. 当前结论

### 结论 1
我们当前确实有很多工件，但并不意味着最终 Skill 包已经膨胀到不可控。

### 结论 2
真正的问题不是“工件太多”，而是：

> **设计时资产、审计资产、运行时资产没有被正式剥离。**

### 结论 3
一旦按本文件把层次分开，当前系统会更容易理解为：

- 主线运行包：有限且明确
- 中间态资产：为写对、审对、改对服务

这会显著减少“全收导致主线膨胀”的错觉。
