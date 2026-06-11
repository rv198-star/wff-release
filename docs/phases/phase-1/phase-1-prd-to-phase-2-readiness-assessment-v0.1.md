# Phase-1（产品/需求阶段）Skills PRD 产出支撑 Phase-2（设计/架构）评估报告

> **评估日期**: 2026-03-28
> **评估范围**: Phase-1 全部 4 个 Stage Skill（Stage-01 ~ Stage-04）的 PRD 产出体系，及其对 Phase-2 设计/架构阶段工作开展的支撑能力
> **评估依据**: skill-contract、output-template、stage-sop、source-cards、unified-product-pack、PRD main document template、phase-admission-matrix、handoff-and-convergence-protocol、cross-phase-unresolved-truth-handling、gates-and-minimum-admission、robustness-coverage 等核心文档

---

## 一、总体评估结论

### 总评：✅ 能够支撑，但存在若干需关注的衔接风险

Phase-1 的 PRD 产出体系**整体上能够支撑 Phase-2 设计/架构阶段的工作开展**。其在以下方面表现成熟：

- **产物覆盖完整**：28 项核心业务产物均有明确的主责任阶段和输出模板定义
- **Handoff 机制显式化**：从 Phase-1 Stage-04 到 Phase-2 Stage-01 的衔接有明确的 admission 条件、handoff 协议和 unresolved-truth 分类
- **Gate/Refusal 机制有效**：多层质量门禁（inlet → execution → outlet）能有效阻止假结构、假验证、假确定性流向下游
- **Unified Product Pack + PRD 主文档**：提供了从分散阶段产物到统一可消费文档的收敛路径

但同时存在 **5 个需要关注的衔接风险点**（详见第五节）。

---

## 二、评估维度 1：Phase-1 各 Stage 产出完整性

### 2.1 产物覆盖矩阵

| 核心业务产物类别 | 编号 | 产物名称 | 主责任 Stage | 覆盖状态 |
|---|---|---|---|---|
| **A. 用户与问题理解** | 1 | 目标用户边界 | Stage-01 | ✅ 完整覆盖 |
| | 2 | 用户分组 | Stage-01 | ✅ 完整覆盖 |
| | 3 | 用户故事/用户案例 | Stage-01 | ✅ 完整覆盖 |
| | 4 | 问题清单 | Stage-01 | ✅ 完整覆盖 |
| | 5 | 机会清单 | Stage-01 | ✅ 完整覆盖 |
| **B. 需求结构** | 6 | 需求全景 | Stage-02 | ✅ 完整覆盖 |
| | 7 | 主干活动/主流程 | Stage-02 | ✅ 完整覆盖 |
| | 8 | 需求结构图/故事地图 | Stage-02 | ✅ 完整覆盖（含 diagram obligation） |
| | 9 | 关键约束清单 | Stage-02 | ✅ 完整覆盖 |
| | 10 | 初版优先级分组 | Stage-02 | ✅ 完整覆盖 |
| | 11 | 高风险待验证点 | Stage-02 | ✅ 完整覆盖 |
| **C. MVP 与切片** | 12 | 完整体验闭环 | Stage-03 | ✅ 完整覆盖 |
| | 13 | 最小可用体验闭环 | Stage-03 | ✅ 完整覆盖（含 viability test） |
| | 14 | MVP 定义 | Stage-03 | ✅ 完整覆盖 |
| | 15 | 首批切片 | Stage-03 | ✅ 完整覆盖 |
| | 16 | 后续切片 | Stage-03 | ✅ 完整覆盖 |
| | 17 | 暂缓项 | Stage-03 | ✅ 完整覆盖（含 honesty check） |
| | 18 | 切片依据 | Stage-03 | ✅ 完整覆盖 |
| | 19 | 待验证关键假设 | Stage-03 | ✅ 完整覆盖 |
| **D. 验证与修订** | 20 | 验证对象/假设 | Stage-04 | ✅ 完整覆盖 |
| | 21 | 验证方式 | Stage-04 | ✅ 完整覆盖（含 method-fit comparison） |
| | 22 | 原型/等价验证材料 | Stage-04 | ✅ 完整覆盖（含 fidelity record） |
| | 23 | 反馈/信号/结果 | Stage-04 | ✅ 完整覆盖 |
| | 24 | 验证结论 | Stage-04 | ✅ 完整覆盖（含三维评估） |
| | 25 | 决策状态 | Stage-04 | ✅ 完整覆盖（Go/No-Go/Revise） |
| | 26 | 修订建议 | Stage-04 | ✅ 完整覆盖 |
| | 27 | 设计/架构 handoff 包 | Stage-04 | ✅ 完整覆盖 |
| | 28 | Unified Product Pack | Post-Stage-04 | ✅ 有定义（含 PRD 主文档模板） |

**完整性评分：28/28 项均有覆盖**

### 2.2 关键发现

- 每个 Stage 不仅定义了"产出什么"，还定义了"不允许产出什么"（refusal 条件），这显著降低了下游消费假产物的风险
- Stage-02 实际拆成 02a（结构化分析）+ 02b（规约深化），02b 负责 NFR、域模型和信息架构方向，这是对设计/架构阶段最重要的前置产出
- Stage-03 的 output-template 中包含 **NFR Slice Impact** 和 **Source Feature Carryover Ledger**，直接影响架构阶段的边界判断
- Stage-04 的 handoff 中包含显式的 **NFR 状态声明**（present | absent | unknown | deferred），是 Phase-2 能否正确启动的关键信号

---

## 三、评估维度 2：Phase-1 → Phase-2 Handoff 衔接质量

### 3.1 衔接路径全景

```
Phase-1 Stage-04 Output
    ├── Validation Record
    ├── Decision State (Go/No-Go/Revise)
    ├── Revision Recommendations
    ├── NFR State Declaration
    ├── Unresolved Risks
    └── Handoff Package
           │
           ▼
    Unified Product Pack Convergence
    (PRD Main Document)
           │
           ▼
Phase-2 Stage-01 Intake
    ├── Phase-1 Handoff Package ← 已对齐
    ├── MVP Boundary ← 已对齐
    ├── Key Scenarios/Main Flows ← 已对齐
    ├── NFR Declaration States ← 已对齐（显式 4-state）
    └── Problem/Opportunity Summary ← 已对齐
```

### 3.2 Phase-2 Stage-01 的 Intake 要求 vs Phase-1 产出对照

| Phase-2 Stage-01 需要的输入 | Phase-1 是否产出 | 对齐质量 |
|---|---|---|
| Phase-1 handoff package（或等价物） | ✅ Stage-04 显式产出 | 🟢 高 |
| 上游问题/机会摘要 | ✅ Stage-01 problem/opportunity list | 🟢 高 |
| MVP 边界 | ✅ Stage-03 MVP definition | 🟢 高 |
| 关键场景/主流程 | ✅ Stage-02a backbone activities | 🟢 高 |
| NFR 声明状态 | ✅ Stage-04 NFR state declaration | 🟢 高 |
| 验证结论与关键场景 | ✅ Stage-04 三维验证评估 | 🟢 高 |
| 概念域模型 | ⚠️ Stage-02b 可选（if executed） | 🟡 条件性 |
| 信息架构方向 | ⚠️ Stage-02b 可选（if executed） | 🟡 条件性 |
| 业务子系统边界 | ⚠️ Stage-02b 可选（if executed） | 🟡 条件性 |

### 3.3 Admission Matrix 检查

Phase Admission Matrix（`phase-admission-matrix-v0.1.md`）明确定义了三种入场状态：

- **PASS**：核心业务产物覆盖完整 + handoff 存在 + 决策状态存在 + 未解决项已分类
- **PASS with constrained conditions**：部分非关键项仍为 review-bound，但 handoff 仍可消费
- **BLOCKED**：无架构入场 handoff / Class C 未解决项强迫 Phase-2 发明核心真相

**评估结论：衔接机制设计完善，Phase-2 的 intake 需求在 Phase-1 产出中有明确对应。**

---

## 四、评估维度 3：PRD 产出的结构化程度和可消费性

### 4.1 PRD 主文档模板评估

PRD Main Document Template（`phase-1-prd-main-document-template-v0.1.md`）定义了 21 个核心章节，其中直接服务于 Phase-2 设计/架构消费的关键章节包括：

| PRD 章节 | 对 Phase-2 的价值 | 深度要求 |
|---|---|---|
| §3 Target Users & Key Roles | 设计 journey/screen framing 的基础 | ✅ 含 persona profiles + key-path scenarios |
| §7 Business Scenarios | 架构推导 workflow implications 的基础 | ✅ 要求至少 3 个场景含 challenge-solution depth |
| §8 Requirements Structure | 架构 capability boundary 的基础 | ✅ 含 consumer translation（设计/架构各应保持什么） |
| §9 NFR / Quality Requirements | 架构决策的核心驱动 | ✅ 含 quality-scenario tables + architecture consequence |
| §10 Domain Model | 架构对象/依赖模型的基础 | ✅ 含 ER diagram + subsystem boundaries |
| §11 Information Architecture | 设计 screen/module 规划的基础 | ✅ 含 IA Spec Matrix（implementation-ready 时） |
| §12 MVP Definition & Scope | 架构边界判断的基础 | ✅ 含 NFR-aware slicing impact |
| §18 Handoff to Design/Architecture | Phase-2 启动的直接基础 | ✅ 含 safe start scope + forbidden assumptions |

### 4.2 深度编译接受检查（Deep-Compilation Acceptance Checks）

PRD 模板定义了 9 项深度编译检查，其中 3 项直接验证对 Phase-2 的可消费性：

1. ✅ 设计能否不需重建逻辑即可推导出工作流？
2. ✅ 架构能否不需发明产品机制即可推导出首波对象/依赖模型？
3. ✅ review-bound truth 是否足够显式，下游不会静默提升为确认真相？

### 4.3 Analysis Delta Ledger

PRD 模板要求 Analysis Delta Ledger，每条决策 delta 需记录：
- `source_evidence` → `analytical_inference` → `decision_or_tradeoff` → `downstream_impact`

这为 Phase-2 提供了**决策可追溯性**，架构师可以理解"为什么这样做"而不只是"做了什么"。

### 4.4 评估结论

**PRD 产出的结构化程度高，对 Phase-2 的可消费性设计充分。** PRD 模板不仅定义了字段，还定义了深度规则（anti-compression rule、depth rule），防止产物退化为 summary-bullet 式的浅层文档。

---

## 五、评估维度 4：Gate/Refusal 机制和质量保障

### 5.1 多层质量门禁体系

Phase-1 建立了三层质量保障机制：

#### 第一层：Stage 级 Gate/Refusal
每个 Stage Skill 都定义了：
- **Inlet Gate**：启动前置条件
- **Refusal**：立即拒绝条件（如无明确调研对象、无全景结构、无验证假设等）
- **Outlet Gate**：最低完成标准（DoD）
- **Cannot-infer 字段**：不允许推断的硬边界

#### 第二层：Phase 级 Admission Matrix
- Phase-1 → Phase-2 有三级入场判定（PASS / PASS with constraints / BLOCKED）
- 显式定义 Class A/B/C 未解决真相分类
- Class C 项（如无架构入场 handoff）强制阻止 Phase-2 启动

#### 第三层：PRD Excellence Scoring Rubric
- 100 分制评分，跨 11 个维度
- **双镜头阅读**：区分文档成熟度分数 vs 业务完整度分数
- 防止"文档结构漂亮但业务真相缺失"的假成熟

### 5.2 Robustness Coverage

Phase-1 的鲁棒性覆盖已编码三个维度：

1. **硬缺失输入的拒绝**（Refusal on hard missing input）
2. **不可推断间隙的阻塞**（Blocked on gaps that cannot be inferred）
3. **虚假提升的防止**（Prevention of false promotion / fake structure / fake validation）

每个 Stage 都有对应的 `robustness-test-case.md` 和 `robustness-test-report.md` 作为覆盖证据。

### 5.3 关键防护机制亮点

| 防护对象 | 机制 | 评估 |
|---|---|---|
| 假结构（fake structure） | Stage-02 要求 diagram obligation + structure alternatives comparison | ✅ 有效 |
| 假验证（fake validation） | Stage-04 要求 evidence state honesty check（design-time inference vs real signals） | ✅ 有效 |
| 假确定性（fake certainty） | 全链路 provisional inference 标记 + NFR 4-state 声明 | ✅ 有效 |
| 假 MVP（smaller backlog as MVP） | Stage-03 要求 MVP Loop Viability Test | ✅ 有效 |
| 信息压缩丢失 | PRD anti-compression rule + capability preservation note | ✅ 有效 |

---

## 六、风险点与改进建议

### 风险 1：Stage-02b 的可选性导致 NFR/域模型缺失

**风险描述**：Stage-02b（规约深化）是可选执行的，但其产出（NFR、域模型、信息架构方向）恰恰是 Phase-2 架构设计最需要的前置信息。如果项目跳过 Stage-02b，Phase-2 将面临关键架构驱动信息缺失。

**当前缓解**：
- Stage-04 handoff 中有 NFR state declaration（可声明 `absent` 或 `deferred`）
- Phase-2 Stage-01 设计了对 absent/deferred NFR 的显式处理路径

**建议**：
- 在 Phase-1 → Phase-2 admission 规则中增加一条：如果 Stage-02b 未执行，handoff 中必须显式声明 NFR/域模型/IA 的缺失状态及其对架构工作的预期影响
- 考虑将 NFR 基础识别（不要求完整 quality-scenario tables）提升为 Stage-02a 的必选输出

**风险等级**：🟡 中等

---

### 风险 2：Unified Product Pack 到 PRD 主文档的收敛执行路径尚未充分验证

**风险描述**：UPP 和 PRD 主文档模板的定义已经成熟，但从分散 Stage 产物收敛到一份"设计/架构可直接消费"的 PRD 主文档，这个过程在真实案例中的执行效果尚未被充分验证。Restaurant-owner 案例做了第一次尝试，但仅此一例。

**当前缓解**：
- PRD 模板有 9 项 Deep-Compilation Acceptance Checks
- TOBECONTINUE.md 已明确下一步是"换新业务案例压测"

**建议**：
- 在下一轮压测中，重点关注 PRD 收敛过程中"是否发生信息压缩丢失"和"设计/架构消费者能否不查阅 Stage 产物即可启动工作"
- 考虑增加一个 convergence smoke test checklist（3-5 条快速检查）

**风险等级**：🟡 中等

---

### 风险 3：跨阶段 Traceability 仍为手工模式

**风险描述**：`phase-1-traceability-gap-analysis-v0.1.md` 已明确指出——Stage 级追溯（S01→S02→S03→S04）通过 handoff 字段存在，但 **Artifact 级追溯**（ID、depends_on、feeds）仍不完整且为手工管理。这意味着当 Phase-2 架构师需要回溯"某个架构决策的需求来源"时，可能面临追溯断链。

**当前缓解**：
- Traceability naming block 已接入
- `wff-base-traceability-management` 已存在但尚未全面落地

**建议**：
- 在 PRD 主文档的 §20 Source Artifacts 中，要求每个 Stage 引用附带明确的产物 ID
- 在 Phase-2 Stage-01 的 intake 中，验证上游 traceability ID 是否可解引用

**风险等级**：🟡 中等

---

### 风险 4：PRD 产出深度的实际执行与模板期望之间的差距

**风险描述**：PRD 模板的 depth rule 和 anti-compression rule 定义了高标准（如"架构能否不需发明产品机制即可推导出首波对象/依赖模型"），但 AI Agent 在实际执行时，可能产出满足字段但不满足深度要求的 PRD，即"结构完整但内容单薄"。

**当前缓解**：
- PRD Excellence Scoring Rubric 的双镜头评分可检测这一问题
- Robustness test 有"假结构/假确定性"防护

**建议**：
- 考虑在 PRD 收敛环节增加一个自动化 depth probe（如"从 §8 能否直接推导出至少 3 个模块边界？"），作为 smoke test
- 在 Phase-2 Stage-01 的 intake 反馈机制中，允许架构师标记"上游产物深度不足以启动 X 工作"并触发回灌

**风险等级**：🟡 中等

---

### 风险 5：Handoff 协议的"forbidden assumptions"执行力度

**风险描述**：handoff-and-convergence-protocol 要求显式声明 `forbidden_assumptions`（下游不允许假设的内容），但这一机制的有效性取决于 Phase-2 的 intake 是否真的检查并遵循这些禁令。目前 Phase-2 Stage-01 SOP 的第一步确实是"检查 Phase-1 handoff 并注册声明状态"，但缺少对 forbidden_assumptions 逐项核验的显式检查。

**当前缓解**：
- Phase-2 Stage-01 skill-contract 要求 "explicit declaration states for critical inputs"
- Cross-phase unresolved truth handling 有 Class A/B/C 分类

**建议**：
- 在 Phase-2 Stage-01 的 intake checklist 中增加一项："逐项确认 Phase-1 handoff 中的 forbidden_assumptions 已注册为本阶段约束"
- 在 Phase-2 的 verification report 中增加 "upstream forbidden assumption compliance check"

**风险等级**：🟢 低（机制已存在，需增强执行层面）

---

## 七、评分总结

| 评估维度 | 评分 | 说明 |
|---|---|---|
| 产物覆盖完整性 | ⭐⭐⭐⭐⭐ | 28/28 项全覆盖，且有 depth rule 保障 |
| Handoff 衔接设计 | ⭐⭐⭐⭐⭐ | Phase-2 intake 与 Phase-1 产出有明确对应，admission matrix 三级判定清晰 |
| PRD 结构化与可消费性 | ⭐⭐⭐⭐☆ | 模板设计优秀，但实际收敛执行效果需更多案例验证 |
| Gate/Refusal 质量保障 | ⭐⭐⭐⭐⭐ | 三层门禁 + 鲁棒性覆盖 + 假产物防护，业界少见的严谨程度 |
| Traceability 可追溯性 | ⭐⭐⭐☆☆ | Stage 级追溯存在，Artifact 级追溯仍为手工管理 |
| 实际执行验证程度 | ⭐⭐⭐☆☆ | 仅 restaurant-owner 一个案例做了端到端验证 |

### 综合评级：**B+（能够支撑，有改进空间）**

---

## 八、最终结论

> **Phase-1 的 PRD 产出体系能够支撑 Phase-2 设计/架构阶段的工作开展。**

具体而言：

1. **产物定义层面**：28 项核心业务产物全覆盖，每项都有明确的模板字段、depth rule 和 gate 条件。Phase-2 架构师能够获得启动工作所需的全部结构化信息。

2. **衔接机制层面**：Phase Admission Matrix + Handoff Protocol + Unresolved Truth Classification 构成了完整的跨阶段衔接治理。Phase-2 不会在"不知道上游给了什么"的情况下被迫启动。

3. **质量保障层面**：三层门禁（Stage gate → Phase admission → PRD scoring）+ robustness coverage 能有效阻止低质量产物流向下游。

4. **主要改进方向**：
   - Stage-02b 可选性带来的 NFR/域模型缺失风险需在 admission 规则中更显式处理
   - PRD 收敛执行路径需更多真实案例验证
   - Artifact 级追溯需从手工管理升级到系统化管理
   - PRD 深度的实际执行与模板期望之间的差距需要更多 smoke test 手段
