# Development Stage Source Register（v0.2）

## 目的

这份 register 用来回答：

- 当前 Phase-3（开发实现阶段）有哪些可正式引用的 source containers
- 哪些来源已足以支撑 Stage-01 control-layer / runtime authoring
- 哪些来源属于 backbone / sidecar / 后续补强

它延续 v0.1 的 register 角色，但明确反映 Phase-3 已切换为 **web/template-first** 的 sourcing posture。

---

## 字段说明

### `source_container`
素材容器名，通常对应：

- `sources/books/extracted/<bundle-name>`
- `sources/web/<bundle-name>`
- `docs/<seed or register doc>`

### `source_type`
支持：

- `book`
- `external-method-bundle`
- `official-spec-bundle`
- `repo-governance`
- `project-seed-doc`

### `primary_stage_focus`
主要支撑的 Phase-3 子阶段，可多项：

- `implementation-readiness-and-task-alignment`
- `constrained-feature-implementation`
- `implementation-audit-and-handoff-gate`

### `coverage_role`
- `foundation`
- `primary-bundle`
- `supporting-bundle`
- `sidecar`

### `authoring_readiness`
- `bundle-ready`
- `quote-ready`
- `authoring-input-ready`
- `partial`

---

## Register Entries（当前 Phase-3 v0.2）

| source_container | source_type | primary_stage_focus | coverage_role | authoring_readiness | notes |
|---|---|---|---|---|---|
| `the-art-of-unit-testing` | `book` | implementation-readiness-and-task-alignment; constrained-feature-implementation; implementation-audit-and-handoff-gate | foundation | authoring-input-ready | 继续作为 testing/testability backbone；最适合 Stage-01 testability baseline 与 Stage-03 test audit spine。 |
| `contract-spine` | `project-seed-doc` | implementation-readiness-and-task-alignment; constrained-feature-implementation; implementation-audit-and-handoff-gate | primary-bundle | authoring-input-ready | Contract Spine Pack 继续负责 API-* / contract drift / acceptance mapping，是 Phase-2→3→4 的主脊梁。 |
| `development-implementation-source-library-seed` | `project-seed-doc` | implementation-readiness-and-task-alignment; constrained-feature-implementation; implementation-audit-and-handoff-gate | primary-bundle | authoring-input-ready | 当前 Phase-3 source strategy 与 starter set 总入口；用于解释为什么 Phase-3 要 web/template-first。 |
| `github-actions` | `official-spec-bundle` | implementation-readiness-and-task-alignment; constrained-feature-implementation | primary-bundle | authoring-input-ready | 已有 first-pass notes；直接支撑 Stage-01 `build-test-gate-manifest.md`、command-level gate semantics、Stage-02 execution evidence expectations。 |
| `google-engineering-practices` | `external-method-bundle` | implementation-readiness-and-task-alignment; constrained-feature-implementation; implementation-audit-and-handoff-gate | primary-bundle | authoring-input-ready | 已有 overview + code review guidance；直接支撑 Stage-01 `coding-baseline-contract.md`、Stage-02 change discipline、Stage-03 code quality review。 |
| `pact` | `official-spec-bundle` | implementation-readiness-and-task-alignment; constrained-feature-implementation; implementation-audit-and-handoff-gate | primary-bundle | authoring-input-ready | 已有 consumer/provider workflow notes；直接支撑 `api_contract_smoke_cmd`、Stage-02 contract verification evidence、Stage-03 contract drift audit。 |
| `semantic-versioning` | `official-spec-bundle` | implementation-readiness-and-task-alignment; implementation-audit-and-handoff-gate | primary-bundle | authoring-input-ready | 已有 spec + npm practical notes；直接支撑 shared component extraction policy、compatibility language、change-impact review。 |
| `dev-containers` | `official-spec-bundle` | implementation-readiness-and-task-alignment; constrained-feature-implementation | primary-bundle | authoring-input-ready | 已有 spec + local-development notes；直接支撑 bootstrap/prerequisites/blocked-remediation realism。 |
| `continuous-delivery` | `book` | implementation-readiness-and-task-alignment; constrained-feature-implementation | supporting-bundle | partial | 仍是高价值 supporting book，但当前不作为 Stage-01 authoring blocker；适合第二轮补强 gate/evidence philosophy。 |
| `accelerate` | `book` | implementation-readiness-and-task-alignment; implementation-audit-and-handoff-gate | supporting-bundle | partial | 仍是 supporting book；适合第二轮补强 delivery-quality signals 与 handoff decision evidence。 |

---

## 当前可直接看出的结论（v0.2）

### 1. Phase-3 现在已有可执行的 Stage-01 web-native spine

Stage-01 最关键的五类来源现在已经进入 register：

- `github-actions`
- `google-engineering-practices`
- `pact`
- `semantic-versioning`
- `dev-containers`

它们分别补上了：

- command-level gates
- review/change discipline
- contract verification
- breaking-change / compatibility semantics
- bootstrap / blocked-remediation realism

### 2. Book backbone 仍保留，但不再主导 Stage-01 authoring

- `the-art-of-unit-testing` 继续是 backbone
- `continuous-delivery` / `accelerate` 继续保留为 supporting books

但 Phase-3 当前不再依赖“先深拆更多书”才能继续 Stage-01 authoring。

### 2.5 Stage-01 source coverage is now operationally tracked

Stage-01 已建立独立的 source-unit coverage ledger：

- `docs/source-registers/development-stage-source-unit-coverage-ledger-v0.1.md`

该 ledger 是 Wave-1 / Wave-2 来源吸收的操作层追踪文件，不由 source register 直接替代。

### 3. 当前最合理的下一步

在 source register 已升级到 v0.2 后，最合理的下一步是：

1. 建立 Stage-01 source-unit coverage ledger
2. 创建缺失的 Stage-01 control-layer templates
3. 把 v0.2 register 中的 primary bundles 绑定进这些模板

### 4. 当前 readiness judgement

基于 v0.2 register，Phase-3 当前最合理的状态判断为：

- **mostly ready for Stage-01 authoring**

仍未完全 ready 的原因不再是 source container 太少，而是：

- Stage-01 control-layer 还缺少若干 canonical artifact paths
- Wave-2 strengthening sources 还未按需吸收
