# Testing-Validation Stage Source-Unit Coverage Ledger（v0.1）

## 目的

这份 ledger 追踪 Phase-4 当前已吸收 / 待吸收的 source units，确保来源不只是“被提到”，而是被明确映射到具体的 Phase-4 子阶段工件。

当前版本聚焦：

- `acceptance-coverage-planning`
- `evidence-execution-and-defect-identification`
- `validation-closure-and-delivery-readiness-judgment`

以及：

- 当前仓库里已经存在的 source units
- 明确缺失但必须补齐的 Tier-0 样例类型

---

## 字段说明

- `source_container`: 来源容器
- `source_unit`: 具体文件或样例类型
- `target_phase4_artifact`: 主要喂给哪个 Phase-4 工件
- `status`: `absorbed | pending | sidecar`
- `notes`: 当前吸收结果或下一步用途

---

## Current coverage rows

| source_container | source_unit | target_phase4_artifact | status | notes |
|---|---|---|---|---|
| `testing-validation-source-library-seed` | `docs/source-registers/testing-validation-source-library-seed-v0.1.md` | `Phase-4 source strategy / starter-set policy` | absorbed | 已定义 Phase-4 的 Tier-0 / Tier-1 sourcing posture、目标输出、以及“不押注 UI 自动化”的边界。 |
| `testing-validation-stage-package-v0` | `docs/phases/phase-4/testing-validation-stage-package-v0.md` | `Phase-4 family structure baseline` | absorbed | 已冻结 3 个子阶段名称、目标、输入/输出方向，可直接作为后续 control-layer authoring baseline。 |
| `development-implementation-source-library-seed` | `docs/source-registers/development-implementation-source-library-seed-v0.1.md` §`Phase-3 vs Phase-4 的测试边界` | `Phase-4 scope boundary note` | absorbed | 已明确 Phase-3 负责 unit/interface smoke，Phase-4 负责 coverage planning、cross-system validation、defect evidence、closure judgment。 |
| `contract-spine` | `docs/source-registers/contract-spine-source-register-v0.1.md` | `acceptance mapping rules` | absorbed | 已用于 `TEST-* -> API-* -> REQ-*` spine 定义。 |
| `contract-spine` | `docs/plans/2026-03-16-contract-spine-pack-design.md` §`Acceptance Mapping (Phase-4)` | `acceptance checklist mapping field set` | absorbed | 已明确 acceptance case 要引用 `REQ-*` 与一个或多个 `API-*`，并声明证据类型。 |
| `contract-registry-template` | `templates/contract-registry-template.md` | `contract index anchor for Phase-4 checklist` | absorbed | 已提供 `API-*` registry 与 `related_tests (TEST-*)` 字段，支持 acceptance checklist traceability。 |
| `round-04-test-gate-cards` | `archive/extraction-runs/round-04/merge-drafts/round-04-cluster-D-merge-decision.md` §`card-test-entry-exit-gate` | `Stage-03 gate checklist spine` | absorbed | entry evidence、exit evidence、sign-off、re-test condition 都已明确，适合直连 Stage-03 gate artifact。 |
| `round-04-test-gate-cards` | `archive/extraction-runs/round-04/round-04-main-repo-absorption-map.md` | `Phase-4 gate-governance adoption note` | absorbed | 证明 `card-test-entry-exit-gate` 已是 adopt/PASS 级资产。 |
| `round-04-test-gate-cards` | `archive/extraction-runs/round-04/round-04-diagram-gate-evidence.md` | `gate artifact evidence note` | absorbed | 证明 test entry/exit gate 不需要 diagram 才能成为有效 gate artifact。 |
| `round-04-test-gate-cards` | `archive/extraction-runs/round-04/merge-drafts/round-04-cluster-D-merge-decision.md` §`card-test-plan-gate-model` | `Stage-01 test-plan spine` | sidecar | 结构强但仍需把示例阈值归一化成 policy fields；适合作为 Stage-01 模板参考，不宜直接照抄。 |
| `testing-validation-external-intake-v1` | `sources/web/testing-validation/acceptance-uat-checklist-notes.md` | `Stage-01 acceptance catalog template` | absorbed | 已吸收 UAT checklist / test case 字段 spine：scope、entry/exit criteria、test steps、expected/actual、status。 |
| `testing-validation-external-intake-v1` | `sources/web/testing-validation/defect-record-notes.md` | `Stage-02 defect record template` | absorbed | 已吸收 defect log / defect report 字段 spine：severity、reproduction、expected/actual、environment、evidence path、resolution action。 |
| `testing-validation-external-intake-v1` | `sources/web/testing-validation/operator-runbook-notes.md` | `Stage-02 operator-facing install/run guide template` | absorbed | 已吸收 operator guide / runbook 字段 spine：prerequisites、steps、verification、troubleshooting、rollback。 |
| `testing-validation-external-intake-v1` | `sources/web/testing-validation/closure-and-gate-notes.md` | `Stage-03 closure judgment template` | absorbed | 已吸收 closure/gate 字段 spine：entry/exit review、verdict、risk acceptance、sign-off、re-test condition。 |
| `acceptance-checklist-samples` | `2 real acceptance checklist templates from different projects/teams` | `Stage-01 acceptance catalog template` | pending | 当前仓库无此类真实样例；这是最重要的 Tier-0 缺口之一。 |
| `entry-exit-gate-checklist-samples` | `1 executable entry/exit gate checklist` | `Stage-01 gate checklist` / `Stage-03 closure checklist` | pending | 虽然已有 extracted gate cards，但仍建议补一个真实项目 checklist 样例，帮助字段落地。 |
| `uat-run-log-samples` | `1 UAT execution record sample` | `Stage-02 execution log template` | pending | 需要环境、版本、执行者、结果、证据路径字段。 |
| `defect-record-samples` | `1 defect record template with reproduction/evidence fields` | `Stage-02 defect record template` | pending | 需要 severity、reproduction、impact scope、evidence path、module/requirement linkage。 |
| `go-no-go-closure-samples` | `1 closure or go/no-go summary sample` | `Stage-03 closure judgment template` | pending | 需要 closure verdict、risk acceptance、residual issues、downstream release note。 |
| `install-run-manual-samples` | `1 install/deploy/run manual sample` | `Stage-02 operator-facing install/run guide template` | pending | 这是 Phase-4 seed doc 明确提出但当前 repo 尚未补上的“可验收运行性”要素。 |
| `ieee-829-style-test-doc-spine` | `test plan / log / incident / summary field types` | `Stage-01 plan fields`; `Stage-02 log fields`; `Stage-03 summary fields` | pending | 当前只有 seed-level recommendation，尚未有本地摘录或整理笔记。 |
| `risk-based-testing` | `coverage prioritization / risk-tiered exit criteria examples` | `Stage-01 coverage rationale`; `Stage-03 exit criteria reasoning` | pending | 当前只有 seed-level recommendation；后续应以轻量 field-type 形式吸收。 |
| `odc-defect-taxonomy` | `defect classification field examples` | `Stage-02 defect classification sidecar` | pending | 可后补，不应阻塞 Phase-4 启动。 |

---

## Current interpretation

- 当前已存在的本地 source units 足以支持 **Phase-4 的 source-preparation 与 scope freeze**。
- 当前已经有 first-pass 外部 intake，可支撑进一步 control-layer authoring；但仍不足以直接宣称 runtime package authoring fully ready，因为 Tier-0 真样例的数量与多样性仍然偏少。
- Phase-4 的下一步应该是：
  - 继续补真实模板与样例
  - 然后把这些样例映射进 Stage-01/02/03 control artifacts
  - 再做 authoring readiness checkpoint
