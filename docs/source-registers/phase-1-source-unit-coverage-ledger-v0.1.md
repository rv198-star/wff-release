# Phase-1 Source-Unit Coverage Ledger（v0.1）

## 目的

这份台账用于把当前 Phase-1 的素材覆盖判断，从“bundle / 书级印象”推进到“素材库单元级可审计记录”。

它不是总审计报告，也不是阶段运行时文件，而是：

> **一个持续维护的中间台账**，
> 用于回答：当前到底有哪些 source units 被吸收、影响了什么、哪些还没吸收、为什么没吸收。

---

## 1. 字段说明

### `source_container`
素材所属容器，例如某个 extracted-book bundle、PM Skill 仓库、repo 治理文档集。

### `source_unit_id`
素材单元标识，可以是 card 名、template 单元名、PM skill 名、治理文档单元名。

### `unit_type`
支持：
- `card`
- `template`
- `guidance`
- `pm-skill`
- `governance-doc`

### `current_stage_usage`
当前被哪个阶段或共享骨架使用。

### `influence_level`
支持：
- `primary`
- `support`
- `weak`
- `sidecar`
- `gap`

### `expected_decision_impact`
该单元主要改变什么：
- contract
- sop
- output shape
- gate/refusal
- handoff
- behavior pattern
- audit/governance

### `omission_code`
若未充分纳入，必须使用：
- `deferred`
- `redundant`
- `misfit`
- `blocked`

### `justification`
一句到两句，解释为什么当前是这个影响等级 / omission 状态。

---

## 2. Ledger Entries（当前 Phase-1 样板）

| source_container | source_unit_id | unit_type | current_stage_usage | influence_level | expected_decision_impact | omission_code | justification |
|---|---|---|---|---|---|---|---|
| product-demand-fit | direct-user-research-principle | card | Stage-01 | primary | behavior pattern, output shape |  | 直接影响“先理解用户再组织问题”的 Stage-01 主行为。 |
| behind-the-scenes-product | rapid-user-group-segmentation | card | Stage-01 | primary | output shape |  | 直接影响用户分组与边界形成。 |
| inspired | product-discovery-before-definition | card | Stage-01 | support | behavior pattern, boundary |  | 用于抑制过早方案化，强化探索前置边界。 |
| lean-product-development | anti-framework-copying-principle | card | Stage-01 | support | governance |  | 主要作为原则约束，不主导 Stage-01 模板细节。 |
| effective-requirements-analysis | requirements-analysis-template-discipline | template | Stage-02 | primary | output shape, contract |  | 直接决定 Stage-02 的结构化分析模板与字段意识。 |
| user-story-mapping | whole-picture-structure | card | Stage-02 | primary | output shape, gate/refusal |  | 直接决定 Stage-02 必须形成 panorama / story-map，而不是故事条目列表。 |
| product-demand-fit | evidence-quality-guard | card | Stage-02 | support | gate/refusal |  | 主要约束 Stage-02 不脱离问题/证据质量前提。 |
| information-architecture-for-the-web | workflow-first-findability-direction | card | Stage-02b | primary | output shape, handoff |  | 直接决定 Stage-02b 的 workflow-first IA 方向与 screen/object matrix，不让规格退化成页面清单。 |
| information-architecture-for-the-web | organization-labeling-navigation-boundary | card | Stage-02b | support | gate/refusal, behavior pattern |  | 约束 Stage-02b 只产出组织/标签/导航方向，不滑向视觉稿或高保真页面设计。 |
| user-story-mapping | mvp-slicing-by-story-map | card | Stage-03 | primary | output shape, gate/refusal |  | 直接决定 Stage-03 的 MVP 切片逻辑与 slice-map 要求。 |
| lean-product-development | early-value-delivery-principle | card | Stage-03 | support | behavior pattern, gate/refusal |  | 约束 Stage-03 以早期价值而非任意分期来切片。 |
| effective-requirements-analysis | structured-decomposition-discipline | template | Stage-03 | support | output shape |  | 补 Stage-03 的结构化拆解纪律，但不主导 slicing 主方法。 |
| user-story-mapping | validated-learning-loop | card | Stage-04 | primary | output shape, behavior pattern |  | 直接影响 Stage-04 的验证链结构与修订回灌。 |
| user-story-mapping | build-measure-learn-loop | card | Stage-04 | primary | output shape |  | 直接影响 hypothesis → method → result → decision 的结构。 |
| inspired | prototype-validation-linkage | card | Stage-04 | support | behavior pattern |  | 为低成本原型验证提供产品方法支撑。 |
| PM Skills | workshop-facilitation | pm-skill | Phase-1 shared spine / Stage-01 | support | behavior pattern |  | 用于 guided / context dump / best-guess 入口组织，不进入 gate authority。 |
| PM Skills | discovery-process | pm-skill | Phase-1 shared spine | support | behavior pattern |  | 主要影响 discovery / clarification 的节奏，不定义 output schema。 |
| PM Skills | prd-development | pm-skill | Phase-1 shared spine | weak | output shape | misfit | 对后段交付文档有启发，但不适合作为当前 runtime contract 主来源。 |
| PM Skills | problem-framing-canvas | pm-skill | Stage-01 | weak | behavior pattern | deferred | 有价值，但当前尚未显式挂入 Stage-01 source-cards，后续可补。 |
| user-persona-methodology | persona-development-stages-and-key-outputs | card | none | sidecar | future architecture/data-product support | deferred | 当前被有意保留为 sidecar，不进入产品/需求主链。 |
| user-persona-platform | persona-platform-layered-architecture | card | none | sidecar | future architecture/platform support | deferred | 更适合设计/架构或数据平台阶段。 |
| document-library | requirements-contract-template-unit | template | none | gap | contract, output shape | blocked | 当前多次被提及，但尚未建立文档库模板单元的正式挂接证据。 |
| document-library | handoff-checklist-template-unit | template | none | gap | handoff, audit/governance | blocked | 当前 handoff 主要来自 repo 自己的规则层，文档库模板单元吸收证据不足。 |
| repo-governance | product-requirements-gates-and-minimum-admission-v0.1 | governance-doc | Phase-1 shared spine | primary | gate/refusal, handoff |  | 当前 Phase-1 四段主 gate authority。 |
| repo-governance | product-requirements-diagram-evidence-rubric-v0.1 | governance-doc | Phase-1 shared spine | primary | gate/refusal, output shape |  | 当前 diagram evidence 的主 authority。 |
| repo-governance | phase-1-intake-state-machine-and-provisional-inference-policy-v0.1 | governance-doc | Phase-1 shared spine | primary | behavior pattern, gate/refusal |  | 当前 Phase-1 intake / blocked / provisional / review 的主 authority。 |
| skill-authoring | Anthropic / Claude Skills authoring constraints | governance-doc | Phase-1 shared spine / all stages | support | audit/governance |  | 主要约束 Skill 结构与 supporting files 角色。 |
| skill-authoring | skill-creator discipline reference | guidance | Phase-1 shared spine / all stages | support | audit/governance |  | 提供 authoring discipline，而不是业务方法内容。 |

---

## 3. 当前从这份 Ledger 能直接看出的结论

### 3.1 当前主链最强的单元级来源
- Stage-01：`direct-user-research-principle`, `rapid-user-group-segmentation`
- Stage-02：`requirements-analysis-template-discipline`, `whole-picture-structure`, `workflow-first-findability-direction`
- Stage-03：`mvp-slicing-by-story-map`
- Stage-04：`validated-learning-loop`, `build-measure-learn-loop`

### 3.2 当前最真实的 gap
- 文档库模板单元目前仍然没有充分显式的挂接证据
- 一些 PM Skills 单元有启发价值，但还未进入正式 Stage artifacts

### 3.3 当前 sidecar 判断是合理的
- `user-persona-methodology`
- `user-persona-platform`

仍然更适合后续阶段，而不是现在强行拉入 Phase-1 主链。

---

## 4. 下一步如何继续维护

后续如果继续扩展该 ledger，优先顺序建议：

1. 文档库模板单元
2. PM Skills 具体 unit
3. Stage-02 / Stage-03 / Stage-04 的更细粒度 cards
4. 后续设计 / 架构阶段的 source-unit ledger
