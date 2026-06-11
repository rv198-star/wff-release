# Source Coverage Audit Report（v0.1）

## 目的

这份报告用于对当前仓库中“已用素材 / 未用素材 / 弱覆盖素材”的状态做一次正式自审查。

它回答的不是简单的“有没有提到某本书”，而是：

- 当前 Skills / Phase-1 产物真正受哪些来源主导
- 哪些来源只是辅助性引用
- 哪些来源存在但尚未进入实质产出
- 这些未覆盖是否合理，还是说明能力缺口

---

## 1. 审计范围

本次审计覆盖三类来源：

1. 书本拆解素材（`sources/books/extracted/*`）
2. 文档库 / repo 治理与阶段文档（`docs/*`, `templates/*`）
3. PM Skills / authoring references（`external-projects/Product-Manager-Skills/*` 及 skill-authoring benchmark references）

本次审计主要观察对象：

- Phase-1 四个 Stage Skills
- Phase-1 共享骨架文档
- 当前已经实现的 traceability-management Skill

---

## 2. 评估口径

本报告不用“用了 / 没用”二分法，而用以下五档：

### A. 主来源（Primary Use）
该来源明确决定了某一阶段或某一能力包的主要方法/结构。

### B. 支撑来源（Support Use）
该来源不是主导来源，但确实补强了边界、原则、证据质量或行为模式。

### C. 弱覆盖（Weak Use）
该来源在文档中被提及，但当前输出物里没有明显实质性影响。

### D. Sidecar 保留（Parked / Sidecar）
当前明确保留，但刻意不纳入主链核心。

### E. 覆盖缺口（Coverage Gap）
理论上应影响当前技能体系，但目前没有被充分纳入，且缺失理由不够充分。

此外，本报告采用 **influence-based coverage** 而不是 citation-count coverage：

- 不按“被提到几次”判断覆盖
- 而按“是否真实改变了 skill 行为、artifact 决策、模板字段、gate 逻辑、执行流程”判断覆盖

也就是说，审计单位不是：

> source → mention count

而是：

> source unit → claim / method / template / constraint → current artifact or skill behavior

### 关键纠偏：审计单位不是“整本书 / 整个 bundle”

本报告不再把以下对象直接当成覆盖单位：

- 一本原始书
- 一个完整 source bundle
- 一个完整 PM Skills 仓库目录

原因：

- 一本书只要被用到一个例子，整本书就被记为“已覆盖”，会严重高估覆盖度
- 一个 bundle 内部可能只有少数 cards 真正影响了当前 Stage Skill
- PM Skills 中被点名一个 skill，不代表整个 PM Skills 库已被覆盖

因此本报告的真正审计单位应是：

- source card
- template-like unit
- stage guidance draft unit
- PM Skill unit
- repo 治理/模板文档单元

bundle / book 只能作为**素材容器背景**，不能直接作为 coverage 结论单位。

---

## 2.1 Omission Codes（未纳入原因编码）

对当前未进入主链或弱覆盖的来源，必须至少落入以下之一：

- `deferred`：当前时序上暂缓，后续阶段有明确接入机会
- `redundant`：已有主来源已充分覆盖其主要价值
- `misfit`：与当前阶段/目标不匹配，不宜纳入
- `blocked`：本应纳入，但当前缺依赖或实现条件

不允许只写“暂未使用”而不给原因。

---

## 3. 书本拆解素材覆盖审计（容器视图，不作为最终覆盖结论）

当前需求 / 产品阶段 source index 收录 8 个 bundles：

1. `user-story-mapping`
2. `lean-product-development`
3. `inspired`
4. `behind-the-scenes-product`
5. `product-demand-fit`
6. `effective-requirements-analysis`
7. `user-persona-methodology`
8. `user-persona-platform`

### 3.1 主来源（Primary Use）

#### `product-demand-fit`
- 主要影响：Stage-01、Stage-02
- 证据：
  - 出现在 source index 的 Stage-01 / Stage-02 优先来源中
  - 出现在 Stage-01 `source-register.md` / `rule-cards.md` / `source-cards.md`
  - 出现在 Stage-02 `source-register.md` / `rule-cards.md` / `source-cards.md`
- 结论：**主来源**

#### `behind-the-scenes-product`
- 主要影响：Stage-01
- 证据：
  - source index 明确列为需求调研主来源之一
  - 出现在 Stage-01 `source-register.md` / `rule-cards.md` / `source-cards.md`
- 结论：**主来源**

#### `inspired`
- 主要影响：Stage-01、Stage-04
- 证据：
  - source index 中被列为需求调研 / 产品探索 / 需求验证优先来源
  - 出现在 Stage-01 与 Stage-04 的 `source-register.md` / `source-cards.md`
- 结论：**主来源**

#### `lean-product-development`
- 主要影响：Phase-1 全局
- 证据：
  - source index 中贯穿多个 Stage
  - 出现在 Stage-01..04 全部 source registers / source cards 中
  - 在多个阶段被明确定位为 principle / governance / anti-overbuild 约束来源
- 结论：**主来源（原则约束型）**

#### `effective-requirements-analysis`
- 主要影响：Stage-02、Stage-03
- 证据：
  - source index 中为 Stage-02 主来源，Stage-03 支撑来源
  - 出现在 Stage-02 / Stage-03 的 source-register / source-cards / rule-cards 中
- 结论：**主来源（结构化分析 / 模板型）**

#### `user-story-mapping`
- 主要影响：Stage-02、Stage-03、Stage-04
- 证据：
  - source index 中为 Stage-02 全景结构、Stage-03 切片、Stage-04 验证学习环的主来源
  - 出现在 Stage-02 / Stage-03 / Stage-04 的 source-register / source-cards / rule-cards 中
- 结论：**主来源**

---

### 3.2 Sidecar 保留

#### `user-persona-methodology`
- 当前状态：在 source index 中被明确标记为 sidecar / 数据能力支撑来源
- 当前影响：未实质进入 Phase-1 四段输出
- 结论：**Sidecar 保留（合理）**
- omission_code：`deferred`
- 理由：
  - 当前 Phase-1 主链聚焦产品/需求，不聚焦画像系统与数据平台治理
  - omission 是有意收敛，不是遗漏

#### `user-persona-platform`
- 当前状态：在 source index 中被明确标记为 sidecar / 平台能力支撑来源
- 当前影响：未实质进入 Phase-1 四段输出
- 结论：**Sidecar 保留（合理）**
- omission_code：`deferred`
- 理由：
  - 它更适合架构治理 / 数据平台设计类阶段
  - 目前不进入产品/需求主链是合理的

---

### 3.3 当前书本素材覆盖结论（仅作容器背景）

- 8 个 bundles 中：
  - 6 个已进入 Phase-1 主链（主来源或强支撑）
  - 2 个被明确 sidecar 保留

因此从 bundle 级看，不存在“重要书本素材完全被忽视且没有理由”的明显问题。

但这个结论只能作为**容器级背景**，不能替代更细粒度的素材库单元覆盖审计。

---

## 3.4 当前已经能确认的“单元级”使用证据

虽然当前仓库还没有一张完整的 unit ledger，但已经可以确认一批高影响单元级使用证据：

### Stage-01
- `direct user research` 类单元被明确吸收
- `fast user-group segmentation` 类单元被明确吸收
- `product discovery before product definition` 类单元被明确吸收

### Stage-02
- `requirements-analysis structure/template` 类单元被明确吸收
- `whole-picture structure / story-map construction` 类单元被明确吸收
- `problem/evidence quality guard` 类单元被明确吸收

### Stage-03
- `MVP slicing by story-map` 类单元被明确吸收
- `early-value delivery` 类单元被明确吸收
- `structured decomposition` 类单元被明确吸收

### Stage-04
- `validated learning loop` 类单元被明确吸收
- `build-measure-learn` 类单元被明确吸收
- `prototype/validation linkage` 类单元被明确吸收

这说明当前并不是“只有 bundle 被提到”，而是已经存在一批对当前 Skills 行为有实质影响的素材库单元。

但问题在于：

> 这些单元级证据现在散落在 `source-register / rule-cards / source-cards / source-index` 中，
> 还没有被汇总成一个正式的 unit-level coverage ledger。

---

## 4. 文档库 / repo 治理文档覆盖审计

### 4.1 强覆盖 / 核心治理来源

以下文档当前已显著进入主链：

- `docs/phases/phase-1/product-requirements-stage-package-v0.md`
- `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- `docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md`
- `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- `docs/phases/phase-1/phase-1-skills-structure-v0.1.md`
- `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`

结论：**强覆盖 / 核心治理来源**

---

### 4.2 弱覆盖或未进入主链的文档层素材

以下类型当前虽然存在，但还未看到明确进入 Phase-1 主线：

- 更广义的后续阶段 package docs（如 design-architecture stage docs）
- 原型追踪 / deeper traceability pack 的细粒度应用

结论：**当前合理未纳入**

理由：
- 当前主任务明确集中在 Phase-1
- 这些文档并非“漏了”，而是阶段时机未到

---

## 5. PM Skills 覆盖审计

### 5.1 已明确吸收的部分

从 `docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md` 可确认，PM Skills 在当前体系中被定义为：

- startup / warm-up / clarification 技巧层
- intake orchestration 参考层
- best-guess / provisional drafting 行为参考层

并明确优先吸收：
- `workshop-facilitation`
- `problem-framing-canvas`
- `discovery-process`
- `prd-development`

结论：**支撑来源（前台 intake / facilitation）**

---

### 5.2 未被吸收的部分是否构成缺口

当前 PM Skills 并没有被大量下沉到：

- gate 定义
- handoff contract
- output-template 主结构
- traceability / diagram evidence / refusal 主逻辑

这不是缺口，而是当前项目有意为之。

理由：
- PM Skills 的强项在启动、澄清、前台 facilitation
- 当前 repo 明确把本仓库治理层置于更高优先级
- 若把 PM Skills 下沉成主 contract 来源，反而会削弱当前 artifact-first / gate-first 体系

结论：**当前 omission 合理，不构成缺口**
- omission_code：`misfit`（对 runtime contract / gate 层而言）

---

## 6. Skill Authoring 参考源覆盖审计

当前可见的吸收痕迹：

- Anthropic / Claude Skills 官方规范
- `skill-creator`
- PM Skills `skill-authoring-workflow`

这些来源当前主要作用于：

- Skills 结构定义
- supporting files 设计
- authoring discipline

而不是业务方法主链。

结论：**支撑来源（authoring discipline）**

这是合理的，因为它们本来就不应主导业务内容。

---

## 7. 当前真正的覆盖缺口

如果要说当前最真实的覆盖缺口，不是“少看了哪本书”，而是：

### 7.1 文档库素材的吸收证据还不够显式

虽然我们前面反复提到“文档库素材”，但当前 Phase-1 的 source-register / source-cards 里，真正显式挂靠的仍然主要是：

- 书本 bundles
- PM Skills
- repo 自己的治理文档

对“文档库素材”的显式挂接证据目前偏弱。

结论：**弱覆盖 / 可能缺口**
- omission_code：`blocked`

理由补充：
- 不是完全不需要，而是当前缺少一轮独立的“文档库模板吸收度审计”和更显式的 source-register 映射方式

### 7.2 Phase-1 目前更像“方法+治理”强覆盖，而不是“模板库”强覆盖

当前 `effective-requirements-analysis` 已承担模板型来源角色，
但如果后续希望把 Phase-1 打磨成更强的“模板即产物”系统，可能还需要重新审查文档库中模板类素材的实际吸收度。

结论：**当前可接受，但后续值得专项审计**
- omission_code：`deferred`

### 7.3 缺少正式的“素材库单元级 coverage ledger”

这其实是当前最大的方法论缺口。

目前我们可以判断：
- 哪些 bundles 进入了主链
- 哪些 source registers 选择了哪些来源
- 哪些阶段 output 受哪些来源影响

但我们还不能系统回答：

- 当前一共有哪些 source cards / template units / PM Skill units 被纳入
- 哪些 unit 是 primary influence
- 哪些 unit 只是 support influence
- 哪些 unit 尚未进入任何 current artifact

结论：**真实缺口 / 高优先级后续审计项**
- omission_code：`blocked`

原因：
- 当前 source-register 更偏来源分层
- 当前 rule-cards 更偏阶段内规则收束
- 还缺一层专门记录“素材库单元覆盖状态”的 ledger

---

## 8. 审计结论

### 8.1 当前整体判断

当前并不存在“我们明明有很多素材，但大部分都被白白浪费了”的明显证据。

更准确地说：

- bundle 容器级覆盖较好
- PM Skills 作为前台 intake 技巧层被有控制地吸收
- repo 自有治理文档被强覆盖
- sidecar bundles 被有意保留而未强行拉入主链

### 8.2 当前最值得关注的问题

真正值得继续审计的不是“有没有用上更多书”，而是：

> **文档库素材的吸收证据是否已经足够显式、足够结构化。**

以及：

> **我们是否已经拥有一份正式的素材库单元级 coverage ledger。**

### 8.3 当前最诚实的结论

> 当前 Skills / Phase-1 产物对“书本主链容器 + PM Skills + repo 治理文档”的覆盖方向基本成立；
> 但如果把审计单位收紧到素材库单元层，当前仍缺少一份正式的 unit-level coverage ledger，
> 尤其在文档库模板单元吸收证据方面还不够显式。

---

## 9. 建议的后续动作

1. **单独补一轮“文档库模板吸收度审计”**
   - 不和书本主链混在一起
   - 重点看模板类、规范类、合同类文档

当前已补：
- `docs/source-registers/phase-1-document-library-template-unit-ledger-v0.1.md`

2. **建立素材库单元级 coverage ledger**
   - 推荐字段：
     - source_container
     - source_unit_id
     - unit_type (`card | template | guidance | pm-skill | governance-doc`)
     - current_stage_usage
     - influence_level (`primary | support | weak | sidecar | gap`)
     - expected_decision_impact
     - omission_code
     - justification

3. **在后续 Stage（尤其设计/架构阶段）继续复查 sidecar bundles 是否转为主链来源**
   - 特别是 `user-persona-methodology`
   - `user-persona-platform`

4. **保留当前 source-register 机制**
   - 因为它已经是当前审计中最可靠的来源使用证据之一

---

## 10. 本轮更新后的更精确结论

在补完 `docs/source-registers/phase-1-document-library-template-unit-ledger-v0.1.md` 以及新增 `templates/research-notes.md` / `templates/stakeholder-analysis.md` 之后，
当前对文档库模板吸收度的判断应更新为：

- 不是“大量模板单元没覆盖”
- 而是“Phase-1 文档库模板单元已经达到显式或条件显式覆盖”
- 当前剩余差异主要体现在影响等级，而不是‘是否已存在对应模板单元’

这说明原先文档库模板单元的主 gap 已经被进一步缩小到接近关闭。
