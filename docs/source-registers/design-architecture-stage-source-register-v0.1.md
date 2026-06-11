# Design/Architecture Stage Source Register（v0.1）

## 目的

这份 register 用来回答：

- 当前 Stage-2 已经有哪些**可正式引用**的 source containers
- 每个 source container 的主要用途是什么
- 它们主要服务 Stage-2 的哪个子阶段
- 哪些已经达到“bundle-ready / quote-ready / authoring-input-ready”

它不是 runtime 文件，而是：

> **Stage-2 的 source control artifact**，
> 用来把“已经抽了很多素材”推进成“已经可被阶段编目与覆盖管理”的状态。

---

## 字段说明

### `source_container`
素材容器名，通常对应 `sources/books/extracted/<bundle-name>`。

### `source_type`
支持：
- `book`
- `external-method-bundle`
- `course-doc-bundle`
- `official-spec-bundle`
- `standard/reference`
- `repo-governance`

### `primary_stage_focus`
主要支撑的 Stage-2 子阶段，可多项：
- `architecture-definition-and-boundary-setting`
- `domain-module-service-decomposition`
- `data-storage-and-interface-design`
- `design-convergence-and-delivery-prototype`

### `coverage_role`
该 source 在当前阶段中的角色：
- `foundation`
- `primary-bundle`
- `supporting-bundle`
- `sidecar`

### `authoring_readiness`
当前是否已达到：
- `bundle-ready`
- `quote-ready`
- `authoring-input-ready`
- `partial`

### `notes`
解释其定位边界与当前使用方式。

---

## Register Entries（当前 Stage-2 初版）

| source_container | source_type | primary_stage_focus | coverage_role | authoring_readiness | notes |
|---|---|---|---|---|---|
| `ddd-reference` | `book` | architecture-definition-and-boundary-setting; domain-module-service-decomposition; data-storage-and-interface-design; design-convergence-and-delivery-prototype | foundation | authoring-input-ready | 当前 Stage-2 的 strategic DDD foundation；提供 bounded context / aggregates / context map / ACL / core domain 等基础语言。 |
| `ddd-starter-modelling-process` | `external-method-bundle` | architecture-definition-and-boundary-setting; domain-module-service-decomposition; design-convergence-and-delivery-prototype | primary-bundle | authoring-input-ready | 提供 8-step 方法骨架；不应直接等同 Stage-2 子阶段结构。 |
| `bounded-context-canvas` | `external-method-bundle` | architecture-definition-and-boundary-setting; domain-module-service-decomposition | primary-bundle | authoring-input-ready | 单 bounded context 设计模板来源，适合作为 output-template 候选。 |
| `context-mapping` | `external-method-bundle` | architecture-definition-and-boundary-setting; data-storage-and-interface-design; design-convergence-and-delivery-prototype | primary-bundle | authoring-input-ready | 提供 relationship pattern selection、team relationship 前置判断与图示使用边界。 |
| `eventstorming-glossary-cheat-sheet` | `external-method-bundle` | architecture-definition-and-boundary-setting; domain-module-service-decomposition; design-convergence-and-delivery-prototype | primary-bundle | authoring-input-ready | 提供 discovery vocabulary + facilitation discipline；当前是 discovery/workshop support source。 |
| `context-mapper` | `external-method-bundle` | architecture-definition-and-boundary-setting; domain-module-service-decomposition; data-storage-and-interface-design | supporting-bundle | authoring-input-ready | 提供 CML、architectural refactoring、formalization mindset；更适合作为 support layer，而非主流程骨架。 |
| `context-map-discovery` | `external-method-bundle` | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | primary-bundle | authoring-input-ready | brownfield reverse-engineering source；用于从现有系统恢复 context map。 |
| `software-architecture-in-practice` | `book` | architecture-definition-and-boundary-setting; data-storage-and-interface-design; design-convergence-and-delivery-prototype | foundation | authoring-input-ready | 当前 Stage-2 的 architecture methods foundation；提供 views, QA scenarios, tactics, ADD, ATAM, CBAM, doc package, checklist gates。 |
| `cqrs-journey` | `book` | domain-module-service-decomposition; data-storage-and-interface-design; design-convergence-and-delivery-prototype | primary-bundle | authoring-input-ready | CQRS/ES adoption 与 production hardening source；覆盖 PM/saga、idempotency、replay、snapshots、upgrade、performance realism。 |
| `api-interface-design` | `external-method-bundle` | data-storage-and-interface-design; design-convergence-and-delivery-prototype | primary-bundle | authoring-input-ready | 当前 Stage-2 的 unified interface contract baseline；覆盖 API-first、compatibility、status codes、errors、pagination、LRO、handoff docs。 |
| `database-design-for-mere-mortals` | `book` | data-storage-and-interface-design; design-convergence-and-delivery-prototype | supporting-bundle | authoring-input-ready | 逻辑数据库设计方法包：使命/目标→表/字段→PK/FK/关系→规格表→业务规则→视图→完整性复核；提供关键 checklist 与规格表模板，适合作为数据建模与完整性 review 的引用源。 |
| `designing-interfaces` | `book` | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | supporting-bundle | authoring-input-ready | 交互设计模式库：已抽取 IA/结构、导航、列表结构、表单原则、动效边界与视觉层级等可复用 cards，并提供 Stage-2 curated minimum sets 作为评审 gate 与输出约束。 |
| `diagram-expression` | `external-method-bundle` | architecture-definition-and-boundary-setting; domain-module-service-decomposition; data-storage-and-interface-design; design-convergence-and-delivery-prototype | primary-bundle | authoring-input-ready | 当前 Stage-2 的 expression/rubric layer；覆盖 diagram type selection、Mermaid/C4 表达边界、evidence vs handoff 图示分层。 |
| `iso-25010-quality-model` | `standard/reference` | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | supporting-bundle | bundle-ready | 作为质量属性分类参考；与 SAIP 的 QA scenario / tactics 形成互补。 |
| `about-face-4` | `book` | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | supporting-bundle | authoring-input-ready | 交互设计方法与决策规则包：persona/scenario/设计需求/posture/flow/负担消除/非模态反馈/撤销；用于补强 Stage-2 的“交互行为质量”与原型收敛审查。 |
| `information-architecture-for-the-web` | `book` | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | supporting-bundle | authoring-input-ready | IA 基础方法与系统组件包：组织/标签/导航/搜索/元数据/受控词表 + 交付与治理生命周期；用于补强 Stage-2 的“可找可懂”与 IA 治理能力。 |
| `reactive-messaging-patterns-with-the-actor-model` | `book` | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | supporting-bundle | authoring-input-ready | Actor/消息驱动异步架构模式包：reactive 四性、actor 边界、监督、消息结构、路由、转换、端点、可观测性；用于补强 DDD 之后的 async collaboration / integration / runtime design。 |
| `vaughn-vernon-event-driven-architecture` | `course-doc-bundle` | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | supporting-bundle | authoring-input-ready | Vaughn Vernon 课程线桥接包：EventStorming→Event-Driven Architecture、event-driven vs message-driven、REST 共存、actor/saga/CQRS 邻接关系；用于补强 DDD 发现到异步架构设计之间的过渡层。 |
| `cloudevents` | `official-spec-bundle` | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | supporting-bundle | authoring-input-ready | CloudEvents 标准事件信封包：统一事件 envelope、required attributes、versioning、bindings/extensions、payload sizing；用于补强异步事件契约标准化层。 |
| `asyncapi` | `official-spec-bundle` | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | supporting-bundle | authoring-input-ready | AsyncAPI 异步接口契约包：machine-readable async contract、channels / operations / messages / servers / bindings 核心模型；用于补强异步 API 描述与 handoff 层。 |

---

## 当前可直接看出的结论

### 1. Stage-2 已经具备两条 foundation spine
- `ddd-reference`
- `software-architecture-in-practice`

### 2. 当前五组 newly-admitted primary bundles
这次正式纳入控制面的新增主资产是：
- `eventstorming-glossary-cheat-sheet`
- `software-architecture-in-practice`
- `cqrs-journey`
- `api-interface-design`
- `diagram-expression`

它们现在都已达到：
- `bundle-ready`
- `quote-ready`
- `authoring-input-ready`

### 3. 当前 Stage-2 的 source family 已明显成形
- DDD strategic + discovery
- bounded context design templates
- relationship mapping
- formalization / reverse engineering
- architecture quality methods
- CQRS/ES tradeoff and production hardening
- lightweight interface contract baseline
- diagram expression / evidence / handoff layer

这意味着：

> Stage-2 现在缺的已经不再是“有没有 source bundles”，
> 而是“如何把这些 bundles 编排进 source-unit coverage 与 authoring basis”。
