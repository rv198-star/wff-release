# Design/Architecture Stage Source-Unit Coverage Ledger（v0.1）

## 目的

这份 ledger 用来把当前 Stage-2 的覆盖判断，从“bundle 级印象”推进到“单元级可审计记录”。

它不是总审计报告，也不是 runtime Skill 文件，而是：

> **一个持续维护的中间台账**，
> 用于回答：当前 Stage-2 到底有哪些 source units 被吸收、影响了什么、哪些能力已覆盖、哪些仍为空白。

它应与下列文档一起使用：

- `docs/phases/phase-2/design-architecture-case-backed-absorption-matrix-v0.1.md`
- `docs/phases/phase-2/phase-2-case-backed-validation-matrix-v0.1.md`

也就是说，这份 ledger 回答“吸收了什么”，而 case-backed matrix 回答“被哪些真实/历史/打包案例实际压过”。

---

## 字段说明

### `source_container`
素材所属 bundle。

### `source_unit_id`
单元标识（通常为 card 名、stage-guidance 名或 index-level method unit）。

### `unit_type`
支持：
- `card`
- `guidance`
- `index-method`

### `current_stage_usage`
当前主要被哪个 Stage-2 子阶段使用。

### `influence_level`
支持：
- `primary`
- `support`
- `weak`
- `sidecar`
- `gap`

### `expected_decision_impact`
主要改变什么：
- contract
- sop
- output shape
- gate/refusal
- handoff
- behavior pattern
- audit/governance

### `omission_code`
若未充分纳入，使用：
- `deferred`
- `redundant`
- `misfit`
- `blocked`

### `justification`
一句到两句，解释当前定位。

---

## Ledger Entries（当前 Stage-2 初版）

| source_container | source_unit_id | unit_type | current_stage_usage | influence_level | expected_decision_impact | omission_code | justification |
|---|---|---|---|---|---|---|---|
| `ddd-reference` | `bounded-context-and-model-boundary` | card | architecture-definition-and-boundary-setting | primary | output shape, gate/refusal |  | 当前边界定义主 authority 之一。 |
| `ddd-reference` | `aggregate-boundary-and-transactional-consistency` | card | domain-module-service-decomposition | primary | output shape, behavior pattern |  | 直接影响聚合与一致性边界表达。 |
| `ddd-reference` | `anticorruption-layer-for-defensive-integration` | card | data-storage-and-interface-design | primary | output shape, gate/refusal |  | 当前跨边界隔离的关键规则源。 |
| `ddd-starter-modelling-process` | `eight-step-ddd-modelling-backbone` | card | Phase-2 shared spine | support | sop, behavior pattern |  | 提供 discovery→decompose→define 的方法骨架，但不直接替代 Stage-2 四子阶段结构。 |
| `ddd-starter-modelling-process` | `adapt-the-order-dont-standardize-the-sequence` | card | Phase-2 shared spine | primary | gate/refusal, behavior pattern |  | 抑制把方法骨架僵化为线性流程。 |
| `bounded-context-canvas` | `bounded-context-canvas-as-design-record` | card | architecture-definition-and-boundary-setting | primary | output shape, contract |  | 当前单上下文设计模板的最强候选。 |
| `bounded-context-canvas` | `inbound-outbound-communication-reveals-real-boundaries` | card | data-storage-and-interface-design | primary | output shape, gate/refusal |  | 直接影响边界暴露面与消息/接口审查。 |
| `context-mapping` | `team-relationship-is-the-prerequisite-to-pattern-choice` | card | architecture-definition-and-boundary-setting | primary | behavior pattern, gate/refusal |  | 关系模式选择前必须先判团队关系。 |
| `context-mapping` | `small-context-maps-answer-explicit-questions` | card | design-convergence-and-delivery-prototype | primary | output shape, handoff |  | 直接限制 context map 图示的粒度和用途。 |
| `eventstorming-glossary-cheat-sheet` | `domain-event-is-the-core-observation-unit` | card | architecture-definition-and-boundary-setting | primary | behavior pattern, output shape |  | 作为 discovery vocabulary 的核心单元。 |
| `eventstorming-glossary-cheat-sheet` | `hotspots-preserve-conflict-and-uncertainty` | card | design-convergence-and-delivery-prototype | primary | gate/refusal, handoff |  | 阻止把不确定性默默吞掉。 |
| `eventstorming-glossary-cheat-sheet` | `policy-command-query-bridge-process-understanding-and-design` | card | domain-module-service-decomposition | support | output shape, behavior pattern |  | 提供从事件到流程/规则建模的桥梁。 |
| `context-mapper` | `cml-as-machine-readable-ddd-model` | card | data-storage-and-interface-design | support | output shape, audit/governance |  | 提供 machine-readable formalization 方向，但当前不是主 contract。 |
| `context-map-discovery` | `discover-contexts-before-discovering-relationships` | card | architecture-definition-and-boundary-setting | primary | sop, behavior pattern |  | brownfield 分析时的关键顺序规则。 |
| `context-map-discovery` | `name-mapping-is-a-first-class-brownfield-problem` | card | design-convergence-and-delivery-prototype | support | audit/governance |  | 当前作为 brownfield 分析的补充风险卡。 |
| `software-architecture-in-practice` | `quality-attribute-scenarios-make-nfrs-actionable` | card | architecture-definition-and-boundary-setting | primary | contract, output shape |  | 当前 NFR → QA scenario 的主 authority。 |
| `software-architecture-in-practice` | `tactics-bridge-quality-to-design` | card | data-storage-and-interface-design | primary | behavior pattern, output shape |  | 当前 QA → design action 的主桥梁。 |
| `software-architecture-in-practice` | `three-step-view-selection-method` | card | design-convergence-and-delivery-prototype | primary | output shape, handoff |  | 直接影响 Stage-2 文档包如何选择视图。 |
| `software-architecture-in-practice` | `view-template-five-sections` | card | design-convergence-and-delivery-prototype | primary | output shape, contract |  | 可直接转化为 view-level output template。 |
| `software-architecture-in-practice` | `atam-phases-and-output-package` | card | design-convergence-and-delivery-prototype | primary | output shape, audit/governance |  | 当前 architecture evaluation output package 的核心来源。 |
| `software-architecture-in-practice` | `availability-design-checklist-review-card` | card | design-convergence-and-delivery-prototype | support | gate/refusal |  | 当前 availability review gate 候选。 |
| `software-architecture-in-practice` | `security-design-checklist-review-card` | card | design-convergence-and-delivery-prototype | support | gate/refusal |  | 当前 security review gate 候选。 |
| `software-architecture-in-practice` | `variability-quality-attribute-needs-scenarios-and-mechanisms` | card | design-convergence-and-delivery-prototype | support | contract, audit/governance |  | 当前 variability 尚非主链，但已具备明确接入点。 |
| `cqrs-journey` | `cqrs-separates-write-and-read-responsibilities` | card | data-storage-and-interface-design | primary | output shape, behavior pattern |  | CQRS/读写模型分离的主 vocabulary source。 |
| `cqrs-journey` | `event-sourcing-is-optional-and-has-costs` | card | data-storage-and-interface-design | primary | gate/refusal, behavior pattern |  | 当前 ES adoption 的关键 tradeoff gate。 |
| `cqrs-journey` | `cross-bounded-context-communication-needs-explicit-style` | card | data-storage-and-interface-design | primary | output shape, gate/refusal |  | 直接约束 CQRS 分区系统中的跨 BC 通信方式。 |
| `cqrs-journey` | `honor-message-idempotency-in-at-least-once-systems` | card | design-convergence-and-delivery-prototype | primary | gate/refusal, audit/governance |  | 当前消息系统韧性主规则之一。 |
| `cqrs-journey` | `rebuild-read-models-during-migration-with-dual-running` | card | design-convergence-and-delivery-prototype | primary | handoff, behavior pattern |  | 直接影响 projection migration / dual-running 方案。 |
| `cqrs-journey` | `scalability-optimism-needs-bottleneck-realism` | card | design-convergence-and-delivery-prototype | primary | gate/refusal |  | 当前 CQRS 生产现实主义的关键警示卡。 |
| `api-interface-design` | `api-first-and-openapi-first-prevent-contract-drift` | card | data-storage-and-interface-design | primary | contract, sop |  | 当前统一 interface contract baseline 的核心入口规则。 |
| `api-interface-design` | `idempotency-is-the-foundation-of-retry-safe-apis` | card | data-storage-and-interface-design | primary | gate/refusal, contract |  | 直接补足了先前 ledger 标出的接口契约薄弱点之一。 |
| `api-interface-design` | `structured-errors-are-part-of-the-contract` | card | data-storage-and-interface-design | primary | contract, handoff |  | 当前错误模型统一性的主来源。 |
| `api-interface-design` | `backward-compatibility-prefer-compatible-extension-over-versioning` | card | design-convergence-and-delivery-prototype | primary | gate/refusal, audit/governance |  | 当前接口兼容性与演化政策的主规则卡。 |
| `api-interface-design` | `collections-need-explicit-pagination-filtering-sorting-discipline` | card | data-storage-and-interface-design | primary | output shape, contract |  | 当前集合接口规则（分页/过滤/排序）的主来源。 |
| `api-interface-design` | `long-running-operations-need-explicit-async-contracts` | card | data-storage-and-interface-design | primary | output shape, contract |  | 当前 LRO/异步接口契约的主来源。 |
| `database-design-for-mere-mortals` | `database-design-process-seven-phases` | card | data-storage-and-interface-design | support | sop, behavior pattern |  | 提供端到端逻辑数据库设计流程骨架，防止直接“拍脑袋建表”。 |
| `database-design-for-mere-mortals` | `mission-statement-keeps-database-scope-focused` | card | data-storage-and-interface-design | support | gate/refusal, contract |  | 用使命声明冻结数据库目的，抑制范围膨胀。 |
| `database-design-for-mere-mortals` | `elements-of-the-ideal-field-checklist` | card | data-storage-and-interface-design | primary | gate/refusal, audit/governance |  | 字段级完整性审查清单（multipart/multivalued/计算值/重复字段）。 |
| `database-design-for-mere-mortals` | `elements-of-the-ideal-table-checklist` | card | data-storage-and-interface-design | primary | gate/refusal, audit/governance |  | 表级结构审查清单（单主题/PK/无异常字段/最小冗余）。 |
| `database-design-for-mere-mortals` | `elements-of-a-primary-key-plus-exclusive-identification-test` | card | data-storage-and-interface-design | primary | gate/refusal, behavior pattern |  | 主键独占标识测试，防止 reference 字段残留导致间接依赖。 |
| `database-design-for-mere-mortals` | `elements-of-a-foreign-key-and-spec-adjustments` | card | data-storage-and-interface-design | primary | gate/refusal, contract |  | 外键要素 + 规格调整规则，消除命名歧义并强化关系完整性。 |
| `database-design-for-mere-mortals` | `spec-sheet-templates-field-business-rule-view` | card | design-convergence-and-delivery-prototype | support | handoff, audit/governance |  | 三类规格表模板，支持从设计到实现/审计的可交付记录。 |
| `designing-interfaces` | `safe-exploration-requires-undo-and-predictable-back` | card | design-convergence-and-delivery-prototype | support | gate/refusal, behavior pattern |  | 安全探索原则：Undo + 可预测回退，降低试错成本。 |
| `designing-interfaces` | `navigation-cost-is-a-design-budget` | card | design-convergence-and-delivery-prototype | primary | gate/refusal, output shape |  | 把 context switch 视为成本，约束导航深度与跳转次数。 |
| `designing-interfaces` | `keep-distances-short-80-20-structure` | card | architecture-definition-and-boundary-setting | support | output shape, sop |  | 用 80/20 规则驱动 IA：高频用例尽量一屏/少跳转。 |
| `designing-interfaces` | `navigation-signposts-keep-users-found` | card | design-convergence-and-delivery-prototype | primary | gate/refusal, output shape |  | “保持被找到”作为导航验收要点：signposts + wayfinding + escape hatch。 |
| `designing-interfaces` | `modal-panel-when-to-use-and-how-to-minimize-disruption` | card | design-convergence-and-delivery-prototype | support | gate/refusal, behavior pattern |  | 模态面板使用边界：只在必须阻断时用，并最小化干扰。 |
| `designing-interfaces` | `visual-hierarchy-rank-importance-and-relationships` | card | design-convergence-and-delivery-prototype | support | gate/refusal, output shape |  | 视觉层级规则：让结构可被一眼推断，降低理解成本。 |
| `designing-interfaces` | `app-functions-four-page-goals-framework` | card | architecture-definition-and-boundary-setting | support | output shape, sop |  | 用四种页面目标框架约束 IA 与模式族选择。 |
| `designing-interfaces` | `two-panel-selector-reduces-context-switch-and-memory-burden` | card | design-convergence-and-delivery-prototype | support | output shape, behavior pattern |  | 列表结构选择：同屏总览+细节减少跳转与记忆负担。 |
| `designing-interfaces` | `forms-beware-literal-mapping-from-data-model` | card | data-storage-and-interface-design | support | gate/refusal, output shape |  | 反实现驱动表单：避免字段直译导致难用与冗长。 |
| `designing-interfaces` | `mobile-challenges-tiny-width-touch-typing-environment-attention` | card | design-convergence-and-delivery-prototype | support | gate/refusal, behavior pattern |  | 移动端约束清单：触摸/输入/环境/注意力等硬边界。 |
| `designing-interfaces` | `color-rules-readability-first-and-colorblind-safe` | card | design-convergence-and-delivery-prototype | support | gate/refusal, audit/governance |  | 配色可读性门槛 + 色盲安全规则。 |
| `designing-interfaces` | `typography-readability-rules-for-body-text` | card | design-convergence-and-delivery-prototype | support | gate/refusal, output shape |  | 正文字体可读性规则，避免装饰体与全大写。 |
| `designing-interfaces` | `mobile-touch-tools-overlay-controls-on-demand` | card | design-convergence-and-delivery-prototype | support | output shape, behavior pattern |  | 沉浸式内容工具按需 overlay，释放空间与注意力。 |
| `designing-interfaces` | `visual-deep-background-soft-focus-gradients-no-focal-points` | card | design-convergence-and-delivery-prototype | support | output shape, audit/governance |  | 背景要后退：软焦/渐变/弱焦点，避免与内容抢注意力。 |
| `designing-interfaces` | `visual-contrasting-font-weights-for-clarity-and-drama` | card | design-convergence-and-delivery-prototype | support | output shape, behavior pattern |  | 字重对比作为层级与强调工具（对比要强）。 |
| `designing-interfaces` | `mobile-generous-borders-make-hit-targets-bigger-than-they-look` | card | design-convergence-and-delivery-prototype | support | gate/refusal, output shape |  | 触控命中区要足够大；可用 iceberg tips 扩大点击区。 |
| `designing-interfaces` | `mobile-loading-indicators-show-progress-in-situ` | card | design-convergence-and-delivery-prototype | support | gate/refusal, behavior pattern |  | 就地加载指示：在内容将出现处显示进度，降低等待焦虑。 |
| `designing-interfaces` | `mobile-streamlined-branding-small-fast-usable` | card | design-convergence-and-delivery-prototype | support | gate/refusal, audit/governance |  | 移动端品牌要小且快，并为恶劣环境强化对比与字号。 |
| `designing-interfaces` | `mobile-infinite-list-load-more-avoids-long-initial-load` | card | design-convergence-and-delivery-prototype | support | output shape, behavior pattern |  | 长列表用“加载更多”追加，避免分页跳转与长首屏等待。 |
| `designing-interfaces` | `mobile-richly-connected-apps-link-to-native-functions-with-prefill` | card | design-convergence-and-delivery-prototype | support | output shape, handoff |  | 利用拨号/地图/日历/邮件等原生能力，按上下文预填数据，减少手动切换。 |
| `designing-interfaces` | `visual-hairlines-one-pixel-lines-for-refinement` | card | design-convergence-and-delivery-prototype | support | output shape, audit/governance |  | 1px 细线做分隔/纹理与精致层次；低对比更“轻”。 |
| `designing-interfaces` | `visual-few-hues-many-values-avoid-rainbow-noise` | card | design-convergence-and-delivery-prototype | support | gate/refusal, audit/governance |  | 少色相多明度的配色策略，避免界面噪声与注意力竞争。 |
| `diagram-expression` | `c4-selects-abstraction-level-before-notation` | card | architecture-definition-and-boundary-setting | primary | output shape, behavior pattern |  | 当前图示前置抽象层级选择的主规则。 |
| `diagram-expression` | `use-sequence-diagrams-for-runtime-interaction-and-handoff` | card | data-storage-and-interface-design; design-convergence-and-delivery-prototype | primary | handoff, output shape |  | 当前 runtime interaction 与 handoff 图示的主来源。 |
| `diagram-expression` | `class-and-er-diagrams-are-structural-not-process-diagrams` | card | domain-module-service-decomposition; data-storage-and-interface-design | primary | gate/refusal, output shape |  | 当前结构图 vs 流程图分工的主规则。 |
| `diagram-expression` | `evidence-diagrams-and-handoff-diagrams-serve-different-purposes` | card | design-convergence-and-delivery-prototype | primary | handoff, audit/governance |  | 当前 evidence/handoff 图示分层的核心规则。 |
| `about-face-4` | `personas-are-composite-archetypes-with-goals` | card | architecture-definition-and-boundary-setting | support | output shape, gate/refusal |  | 作为交互设计决策主体与反“弹性用户”护栏。 |
| `about-face-4` | `scenarios-bridge-research-and-design-requirements` | card | architecture-definition-and-boundary-setting | support | output shape, sop |  | 作为研究→需求→交互推演的桥梁单元。 |
| `about-face-4` | `design-requirements-are-not-features` | card | architecture-definition-and-boundary-setting | support | contract, gate/refusal |  | 防止把需求写成特性清单，降低过早锁死。 |
| `about-face-4` | `platform-and-posture-should-follow-usage-context` | card | design-convergence-and-delivery-prototype | support | behavior pattern, output shape |  | 用 posture 决策约束交互密度与导航组织。 |
| `about-face-4` | `flow-and-transparency-avoid-modal-interruptions` | card | design-convergence-and-delivery-prototype | support | gate/refusal, behavior pattern |  | 把模态打断当作高成本，指导对话框治理。 |
| `about-face-4` | `interaction-burden-is-tax-on-users-reduce-navigation` | card | design-convergence-and-delivery-prototype | support | sop, gate/refusal |  | 负担审计 lens：导航/记忆/视觉/肢体工作最小化。 |
| `about-face-4` | `do-dont-ask-replace-confirmation-dialogs-with-undo` | card | design-convergence-and-delivery-prototype | support | behavior pattern, gate/refusal |  | 以可撤销/可恢复替代确认对话框。 |
| `about-face-4` | `rich-visual-modeless-feedback-prevents-errors` | card | design-convergence-and-delivery-prototype | support | behavior pattern, output shape |  | 用非模态反馈替代“事后告知式”对话框。 |
| `information-architecture-for-the-web` | `ia-design-for-finding-and-understanding` | card | architecture-definition-and-boundary-setting | support | gate/refusal, behavior pattern |  | 将 IA 明确为“找+懂”的基础约束，防止只画 sitemap。 |
| `information-architecture-for-the-web` | `ia-anatomy-top-down-bottom-up-invisible` | card | architecture-definition-and-boundary-setting | support | output shape, audit/governance |  | deep-link 现实与 invisible IA 纳入可审计范围。 |
| `information-architecture-for-the-web` | `organization-schemes-exact-vs-ambiguous` | card | architecture-definition-and-boundary-setting | support | output shape, behavior pattern |  | 组织方案选择框架（精确/模糊/混合）。 |
| `information-architecture-for-the-web` | `labeling-jargon-is-a-user-hostile-smell` | card | design-convergence-and-delivery-prototype | support | gate/refusal |  | 顶层标签行话是硬风险点；作为收敛 gate。 |
| `information-architecture-for-the-web` | `navigation-stress-test-parachute-into-the-middle` | card | design-convergence-and-delivery-prototype | support | audit/governance, gate/refusal |  | deep-link 入场压力测试；作为验收检查。 |
| `information-architecture-for-the-web` | `search-is-not-a-substitute-for-navigation` | card | design-convergence-and-delivery-prototype | support | gate/refusal, behavior pattern |  | 反“search 当补丁”决策约束。 |
| `information-architecture-for-the-web` | `metadata-and-controlled-vocab-are-system-glue` | card | design-convergence-and-delivery-prototype | support | output shape, behavior pattern |  | 引入词表/元数据统一搜索/导航/标签语言。 |
| `information-architecture-for-the-web` | `faceted-classification-and-guided-navigation` | card | design-convergence-and-delivery-prototype | support | output shape, behavior pattern |  | 分面作为可演进 findability 底座；支撑组合查询与筛选。 |
| `information-architecture-for-the-web` | `content-analysis-inventory-audit-noahs-ark-sampling` | card | architecture-definition-and-boundary-setting | support | audit/governance, output shape |  | bottom-up 证据管道：内容清单/审计为 taxonomy/metadata 输入。 |
| `information-architecture-for-the-web` | `information-architecture-style-guide-as-governance-tool` | card | design-convergence-and-delivery-prototype | support | audit/governance, handoff |  | IA style guide 作为 anti-drift 交付物与治理手册。 |
| `reactive-messaging-patterns-with-the-actor-model` | `actor-is-a-single-message-no-shared-state-async-boundary` | card | architecture-definition-and-boundary-setting | support | behavior pattern, contract |  | 把 actor 定义为异步协作与并发隔离边界。 |
| `reactive-messaging-patterns-with-the-actor-model` | `supervision-is-the-primary-resilience-mechanism` | card | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | support | behavior pattern, gate/refusal |  | 故障恢复策略从监督层级出发，而不是局部 try/catch 拼凑。 |
| `reactive-messaging-patterns-with-the-actor-model` | `command-event-document-messages-have-different-intents` | card | design-convergence-and-delivery-prototype | support | contract, output shape |  | 区分三类消息意图，形成更清晰的 async contract。 |
| `reactive-messaging-patterns-with-the-actor-model` | `request-reply-return-address-and-correlation-are-first-class` | card | design-convergence-and-delivery-prototype | support | contract, behavior pattern |  | 请求-回复、return address、correlation 是异步协作主骨架。 |
| `reactive-messaging-patterns-with-the-actor-model` | `normalized-message-model-reduces-n-squared-integration-cost` | card | design-convergence-and-delivery-prototype | support | contract, output shape |  | canonical message model 降低多系统异步整合复杂度。 |
| `reactive-messaging-patterns-with-the-actor-model` | `anti-corruption-translation-should-live-at-adapters-and-endpoints` | card | design-convergence-and-delivery-prototype | support | contract, handoff |  | 外部消息翻译应停留在端点/适配器，不污染核心 actor 模型。 |
| `reactive-messaging-patterns-with-the-actor-model` | `idempotent-receiver-and-persistent-subscriber-harden-delivery` | card | design-convergence-and-delivery-prototype | support | gate/refusal, audit/governance |  | 支撑消息重试/重放/恢复场景下的投产可靠性。 |
| `reactive-messaging-patterns-with-the-actor-model` | `control-bus-wire-tap-and-message-metadata-enable-operations` | card | design-convergence-and-delivery-prototype | support | audit/governance, handoff |  | 异步系统的消息级可观测性与调试治理基础。 |
| `reactive-messaging-patterns-with-the-actor-model` | `recipient-list-and-aggregator-form-a-scatter-gather-backbone` | card | design-convergence-and-delivery-prototype | support | behavior pattern, contract |  | scatter-gather 的核心组合模式，适合并行询价/比选/聚合。 |
| `reactive-messaging-patterns-with-the-actor-model` | `message-bridge-enables-interoperability-between-incompatible-messaging-systems` | card | design-convergence-and-delivery-prototype | support | handoff, contract |  | 处理不同消息基础设施之间的互操作边界。 |
| `reactive-messaging-patterns-with-the-actor-model` | `content-enricher-adds-missing-context-before-leaving-the-system` | card | design-convergence-and-delivery-prototype | support | output shape, handoff |  | 为外部消费者补齐上下文而不污染内部模型。 |
| `reactive-messaging-patterns-with-the-actor-model` | `claim-check-replaces-large-payloads-with-retrievable-tokens` | card | design-convergence-and-delivery-prototype | support | output shape, behavior pattern |  | 大消息/复杂载荷的分离与按需检索模式。 |
| `reactive-messaging-patterns-with-the-actor-model` | `competing-consumers-and-dispatchers-balance-workload` | card | design-convergence-and-delivery-prototype | support | behavior pattern, audit/governance |  | worker pool / 调度分发 / 负载均衡设计依据。 |
| `vaughn-vernon-event-driven-architecture` | `eventstorming-is-a-bridge-to-event-driven-architecture` | card | architecture-definition-and-boundary-setting | support | behavior pattern, handoff |  | 把 EventStorming 产物推进到 event-driven architecture 设计。 |
| `vaughn-vernon-event-driven-architecture` | `significant-system-outcomes-should-be-captured-as-events` | card | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | support | contract, behavior pattern |  | 以“重要系统结果”作为事件建模与外发基础。 |
| `vaughn-vernon-event-driven-architecture` | `event-driven-and-message-driven-architectures-are-related-but-not-identical` | card | architecture-definition-and-boundary-setting | support | contract |  | 澄清 event-driven / message-driven 术语边界。 |
| `vaughn-vernon-event-driven-architecture` | `rest-and-event-driven-microservices-can-coexist` | card | design-convergence-and-delivery-prototype | support | contract, behavior pattern |  | 同步接口与异步事件协作并存，而非二选一。 |
| `vaughn-vernon-event-driven-architecture` | `actor-model-sagas-process-managers-form-an-async-coordination-toolkit` | card | design-convergence-and-delivery-prototype | support | behavior pattern, output shape |  | 异步协作工具包的整体心智模型。 |
| `vaughn-vernon-event-driven-architecture` | `cqrs-and-event-sourcing-are-advanced-follow-on-not-default-starting-points` | card | design-convergence-and-delivery-prototype | support | gate/refusal, behavior pattern |  | 将 CQRS/ES 定位为深化工具，而不是默认起点。 |
| `cloudevents` | `cloudevents-provides-a-vendor-neutral-event-envelope` | card | architecture-definition-and-boundary-setting | support | contract, output shape |  | 以标准 envelope 统一跨平台事件元数据。 |
| `cloudevents` | `events-are-facts-messages-are-transport-carriers` | card | architecture-definition-and-boundary-setting | support | contract |  | 澄清事件语义与消息传输机制的边界。 |
| `cloudevents` | `cloudevents-required-attributes-form-the-minimum-interoperable-contract` | card | design-convergence-and-delivery-prototype | support | contract |  | 最小互操作事件契约。 |
| `cloudevents` | `type-is-the-primary-versioning-signal-dataschema-is-informational` | card | design-convergence-and-delivery-prototype | support | audit/governance, contract |  | 事件演进与 schema 治理的核心规则。 |
| `cloudevents` | `extensions-and-bindings-extend-core-without-redefining-it` | card | design-convergence-and-delivery-prototype | support | contract, handoff |  | 将核心模型、扩展、格式、协议绑定分层。 |
| `cloudevents` | `keep-events-compact-link-large-payloads-instead-of-embedding` | card | design-convergence-and-delivery-prototype | support | gate/refusal, output shape |  | 控制事件大小，避免大对象直嵌。 |
| `asyncapi` | `asyncapi-document-is-the-machine-readable-async-contract` | card | architecture-definition-and-boundary-setting | support | contract, handoff |  | 把 sender/receiver async contract 结构化为机器可读文档。 |
| `asyncapi` | `channels-organize-message-flow-across-topics-queues-paths-and-subjects` | card | design-convergence-and-delivery-prototype | support | output shape, contract |  | 用统一 channel 抽象组织多协议消息流。 |
| `asyncapi` | `operations-describe-what-the-application-sends-or-receives` | card | design-convergence-and-delivery-prototype | support | behavior pattern, contract |  | 用 send/receive 明确应用相对 channel 的职责。 |
| `asyncapi` | `messages-may-represent-events-commands-queries-or-responses` | card | architecture-definition-and-boundary-setting; design-convergence-and-delivery-prototype | support | contract |  | 保持 message 语义广度，不把 AsyncAPI 缩减成“事件目录”。 |
| `asyncapi` | `asyncapi-is-protocol-agnostic-bindings-carry-protocol-specific-details` | card | design-convergence-and-delivery-prototype | support | contract, handoff |  | 协议无关核心 + bindings 细节分层。 |
| `asyncapi` | `servers-channels-operations-messages-and-components-form-the-core-model` | card | design-convergence-and-delivery-prototype | support | output shape, handoff |  | AsyncAPI 核心模型骨架。 |

---

## 当前从这份 Ledger 能直接看出的结论

### 1. 本次新纳入的五组资产已进入主链
这次明确纳入控制面的新增主资产是：
- `eventstorming-glossary-cheat-sheet`
- `software-architecture-in-practice`
- `cqrs-journey`
- `api-interface-design`
- `diagram-expression`

它们都不再是 sidecar，而已进入 `primary` 或 `support` 的正式覆盖层。

### 2. Stage-2 当前最强的 source family
- 边界与战略：`ddd-reference` + `ddd-starter-modelling-process` + `bounded-context-canvas` + `context-mapping`
- discovery/workshop：`eventstorming-glossary-cheat-sheet`
- formalization / brownfield：`context-mapper` + `context-map-discovery`
- architecture method spine：`software-architecture-in-practice`
- CQRS/ES adoption & hardening：`cqrs-journey`
- interface contract baseline：`api-interface-design`
- expression / handoff layer：`diagram-expression`

### 3. 当前仍保留的 gap / deferred area
- async event contract 侧支已由 `cloudevents` + `asyncapi` 形成独立 supporting bundles；当前缺口已从“有没有标准化 contract 层”转为“是否需要更细的 protocol binding / schema registry / governance 细化”。
- database-design 本体仍未形成独立 source family；当前只有 ER 作为交付表达图种，以及 DDD/CQRS/SAIP 对一致性、聚合、读模型和 tactics 的间接覆盖。后续仍值得补：schema strategy、normalization/denormalization、indexing、storage-model tradeoffs、migration/evolution 等数据库设计参考。
- variability 已进入 SAIP，但尚未成为 Stage-2 主链刚性 requirement
- diagram expression 已有第一版 bundle，但若后续需要更严格 UML notation discipline，可再引入 UML-oriented companion source
- TOGAF/SOA 仍应保持 review lens / deferred supporting role，而非主链来源

---

## 下一步建议

1. 基于这份 register + ledger，起草 `design-architecture-skill-authoring-basis-v0.1.md`
2. 明确四个 Stage-2 substages 各自的 shared spine vs local variation
3. 再决定哪些 cards 进入 future runtime `source-cards.md`，哪些保留为 supporting bundles
