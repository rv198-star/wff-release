# P2 Existing-System Architecture Change Intake Packet

本模板用于存量系统上的架构变更输入。它是 P1 PRD 的旁支补充，不替代 P1 PRD，也不替代 `Phase-2 Design Input Contract`。

规则：

- 只在存量系统架构变更时使用。
- 不要把 PhaseX 原始扫描表直接贴进来。
- 不要把推断写成确认事实。
- 不要把需求目标改写成技术目标。
- 不要把破坏性删除或替换伪装成普通架构设计。
- `AC-3` 和 `AC-4` 不能直接声明 ready-for-P3。

---

- `packet_subtype`: `existing-system-architecture-change`
- `producer`: `PhaseX | human | other`
- `source_status`: `observed | mixed | inference-heavy`
- `admission_status`: `ready-for-P2 | provisional-ready-for-P2 | architecture-decision-required | blocked`
- `change_impact_level`: `AC-1 | AC-2 | AC-3 | AC-4`
- `change_mode`: `additive | compatibility-wrap | deprecate | archive | downgrade | destructive`
- `case_id`: `<case-id>`
- `prepared_at`: `<YYYY-MM-DD>`

## Architecture Change Brief

说明本架构变更对应的 P1 需求、验收压力或 `Phase-2 Design Input Contract` 行。

只写整理后的事实和问题，不要粘贴原始扫描表。

### Current Architecture Facts

列出现有系统架构事实。只写有证据支撑的内容，例如模块、服务、数据库、接口、部署、外部依赖、调用方。

### Inferred Architecture Semantics

列出从现有系统材料推断出来的架构含义。每条都必须保留 `inferred` 标签和推断依据。

### Architecture Change Pressure

说明目标需求对现有架构造成的压力，例如容量、接口兼容、数据迁移、模块边界、部署方式、外部依赖。

### Existing Contracts To Preserve

列出不能破坏的旧契约，包括 API、表结构、数据语义、调用方行为、运行入口、部署约束。

## Architecture Change Impact Triage

Agent 先做技术变更分级评估，再进入架构变更设计。

| item_id | impacted_area | impact_level | evidence | breaks_existing_contract | compatibility_path | migration_path | rollback_path | decision |
|---|---|---|---|---|---|---|---|---|
| TRI-001 | `<db/api/service/runtime/external-caller>` | `AC-1 | AC-2 | AC-3 | AC-4` | `<evidence>` | `<yes/no/unknown>` | `<strategy or missing>` | `<strategy or missing>` | `<strategy or missing>` | `<ready-for-P2 | architecture-decision-required | blocked>` |

分级规则：

- `AC-1`：局部调整，不破坏 DB/API/外部契约。
- `AC-2`：影响契约，但有清楚兼容、迁移和回滚策略。
- `AC-3`：高风险改造，例如 DB 底层改造、公共 API breaking change、服务拆分、跨系统影响。
- `AC-4`：系统级重构、技术战略替换或大范围重建。

## Architecture Change Design

Agent 根据分级结果设计变更方案。

### Compatibility Strategy

说明如何保持旧契约可用。优先新增、包一层、兼容字段、适配器、灰度、双跑。

### Migration Strategy

说明迁移顺序、数据迁移、调用方迁移、验证点，以及人工确认证据（如有）。

### Rollback Strategy

说明失败后如何回退到旧路径、旧数据、旧接口或降级模式。

### Removal Or Destructive Change Decision

说明是否涉及删除、drop、breaking change、替换旧模块、停止旧接口。

如果涉及，必须标记为 `architecture-decision-required` 或 `blocked`，并说明需要谁决策。

### Source Conflicts

列出代码、数据库、文档、运行观察和用户说法之间的冲突。

### Open Architecture Gaps

列出会影响边界、数据、接口、部署、迁移或回滚判断的未知点。

## Owner Confirmation Policy

- Owner / maintainer confirmation is optional evidence, not an admission prerequisite.
- If no owner can be found, record `owner_availability: no owner available`.
- Missing owner confirmation must lower the claim ceiling and keep affected facts review-bound, but must not block P2 by itself.
- In no-owner cases, prefer additive compatibility, adapter seams, feature flags, migration/rollback protection, and conservative defaults.

## Stage Expression Map

| P2 Stage | Side-Branch Material To Express | Required Output |
|---|---|---|
| Stage-01 | `<boundary / impact level / decision gate>` | `<boundary decision / compatibility posture / review-bound item>` |
| Stage-02 | `<module / service / domain impact>` | `<additive boundary / adapter / preserved contract / deprecated boundary>` |
| Stage-03 | `<data / API / external interface impact>` | `<schema migration / API compatibility / rollback-safe contract>` |
| Stage-04 | `<migration / verification / rollback / P3 handoff>` | `<implementation slice / protection test / decision gate / handoff constraint>` |

## Truth-State Ledger

| item_id | statement | truth_state | evidence_pointer | P2_handling |
|---|---|---|---|---|
| TS-001 | `<statement>` | `observed | inferred | unknown | conflict | review-bound` | `<file/line/doc/runtime/user note>` | `<Stage-01 / Stage-02 / Stage-03 / Stage-04 / blocked>` |

## Admission Decision

- `admission_status`: `ready-for-P2 | provisional-ready-for-P2 | architecture-decision-required | blocked`
- `claim_ceiling`: `<what P2 may and may not claim>`
- `reason`: `<short reason>`

## Handoff Note For wff-arch

说明 `wff-arch` 应如何消费本输入包：

- 哪些现有架构事实可进入设计约束
- 哪些推断必须保持 review-bound
- 哪些旧契约必须保留
- 哪些数据、接口、运行时变更需要兼容、迁移和回滚策略
- 哪些 `AC-3 / AC-4` 项需要显式决策或阻断；人工确认只作为可选证据
- 哪些缺口不能交给 P3 自行脑补
