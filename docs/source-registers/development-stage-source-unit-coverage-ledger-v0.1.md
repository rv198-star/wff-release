# Development Stage Source-Unit Coverage Ledger（v0.1）

## 目的

这份 ledger 追踪 Phase-3 Stage-01 已吸收/待吸收的 source units，确保来源不只是“被收集”，而是被明确映射到具体控制层工件。

当前版本聚焦：

- `implementation-readiness-and-task-alignment`
- Wave-1 web-native / official sources

---

## 字段说明

- `source_container`: 来源容器
- `source_unit`: 具体页面/笔记文件
- `target_stage01_artifact`: 主要喂给哪个 Stage-01 工件
- `status`: `absorbed | pending | sidecar`
- `notes`: 当前吸收结果或下一步用途

---

## Wave-1 coverage rows

| source_container | source_unit | target_stage01_artifact | status | notes |
|---|---|---|---|---|
| `github-actions` | `actions-overview.md` | `templates/build-test-gate-manifest.md` | absorbed | 已用于 command-level CI gate backbone 与 Stage-03 evidence expectations framing。 |
| `github-actions` | `build-and-test-overview.md` | `templates/build-test-gate-manifest.md` | absorbed | 已用于 build/test commands should mirror local execution 的 Stage-01 gate realism。 |
| `github-actions` | `workflow-syntax-notes.md` | `templates/build-test-gate-manifest.md` | absorbed | 已用于 conditional gates / blocked semantics / required checks framing。 |
| `google-engineering-practices` | `overview.md` | `templates/coding-baseline-contract.md` | absorbed | 已用于 review/change discipline 的 Stage-01 baseline framing。 |
| `google-engineering-practices` | `code-review-guidelines.md` | `templates/coding-baseline-contract.md` | absorbed | 已用于 code-quality / tests / change clarity 等 gateable review rules。 |
| `pact` | `consumer-workflow.md` | `templates/build-test-gate-manifest.md` | absorbed | 已用于 `api_contract_smoke_cmd` 的 consumer-side contract workflow framing。 |
| `pact` | `provider-verification.md` | `templates/build-test-gate-manifest.md` | absorbed | 已用于 provider verification 作为 contract drift gate 的 Stage-01 semantics。 |
| `semantic-versioning` | `spec-summary.md` | `templates/shared-component-extraction-policy.md` | absorbed | 已用于 breaking change / compatibility / public API semantics。 |
| `semantic-versioning` | `npm-practical-notes.md` | `templates/shared-component-extraction-policy.md` | sidecar | 主要作为 practical compatibility notes，当前为辅助说明层。 |
| `dev-containers` | `spec-summary.md` | `templates/build-test-gate-manifest.md` | absorbed | 已用于 `dev_environment_bootstrap` / `test_environment_bootstrap` / prerequisites realism。 |
| `dev-containers` | `local-development-notes.md` | `templates/implementation-readiness-package.md` | absorbed | 已用于 blocked/remediation and operator bootstrap wording。 |
| `the-art-of-unit-testing` | `stage-guidance-draft.md` | `templates/coding-baseline-contract.md` | absorbed | 继续作为 Stage-01 testability/test-discipline backbone。 |
| `development-implementation-source-library-seed` | `docs/source-registers/development-implementation-source-library-seed-v0.1.md` | `templates/shared-component-extraction-policy.md` | absorbed | 已用于 extraction governance placement rule 和“不要把重构当交付”的控制语义。 |

---

## Current interpretation

- Wave-1 的核心 source units 已经全部有对应的 Stage-01 target artifact。
- 当前没有“已收进 repo 但完全未被挂接”的 Wave-1 核心来源。
- 后续 Wave-2 吸收应继续沿用本 ledger，而不是只更新 source register。
- Stage-01 runtime-facing source summary from the early hand-authored package is archived at `archive/examples/implementation-development-package/stage-01-implementation-readiness-and-task-alignment/source-pack.md` and `.zh-CN.md`.
