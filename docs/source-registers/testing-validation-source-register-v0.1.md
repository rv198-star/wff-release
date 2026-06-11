# Testing-Validation Stage Source Register（v0.1）

## 目的

这份 register 用来回答：

- 当前 Phase-4（测试验证阶段）有哪些可正式引用的 source containers
- 哪些来源已经足以支撑 source-grounded authoring
- 哪些来源仍只是 starter set 方向，尚未具备本仓库内的真实锚点

它沿用 Phase-3 source register 的字段模型，但把状态判断改成更符合当前 Phase-4 现实：

> **控制面方向已清楚，真实 Tier-0 样例仍偏少。**

---

## 字段说明

### `source_container`
素材容器名，通常对应：

- `docs/<seed or register doc>`
- `templates/<governance template>`
- `archive/extraction-runs/<round outputs>`
- `sources/web/<bundle-name>`

### `source_type`
支持：

- `project-seed-doc`
- `repo-governance`
- `extracted-governance-bundle`
- `template-bundle`
- `standards-reference`
- `method-reference`

### `primary_stage_focus`
主要支撑的 Phase-4 子阶段，可多项：

- `acceptance-coverage-planning`
- `evidence-execution-and-defect-identification`
- `validation-closure-and-delivery-readiness-judgment`

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

## Register Entries（当前 Phase-4 v0.1）

| source_container | source_type | primary_stage_focus | coverage_role | authoring_readiness | notes |
|---|---|---|---|---|---|
| `testing-validation-source-library-seed` | `project-seed-doc` | acceptance-coverage-planning; evidence-execution-and-defect-identification; validation-closure-and-delivery-readiness-judgment | foundation | authoring-input-ready | 当前 Phase-4 starter set 总入口；明确了 Tier-0 / Tier-1 sourcing posture、目标工件、以及“不要把 UI 自动化或测试执行流程做成主链”的边界。 |
| `testing-validation-stage-package-v0` | `project-seed-doc` | acceptance-coverage-planning; evidence-execution-and-defect-identification; validation-closure-and-delivery-readiness-judgment | foundation | authoring-input-ready | 已经明确 3-stage family 骨架、每个 stage 的目标/输入/输出；足够支撑 control-layer 级别的范围冻结。 |
| `development-implementation-source-library-seed` | `project-seed-doc` | acceptance-coverage-planning; evidence-execution-and-defect-identification; validation-closure-and-delivery-readiness-judgment | primary-bundle | authoring-input-ready | 已明确 Phase-3 与 Phase-4 的测试边界：Phase-3 负责开发自检与 contract smoke，Phase-4 负责 coverage planning、跨模块验证、缺陷证据化、closure judgment。 |
| `contract-spine` | `project-seed-doc` | acceptance-coverage-planning; evidence-execution-and-defect-identification; validation-closure-and-delivery-readiness-judgment | primary-bundle | authoring-input-ready | 已明确 `TEST-* -> API-* -> REQ-*` acceptance mapping 是 Phase-4 的主脊梁，不应被省略成纯 narrative checklist。 |
| `contract-registry-template` | `repo-governance` | acceptance-coverage-planning; validation-closure-and-delivery-readiness-judgment | primary-bundle | authoring-input-ready | 可直接作为 Phase-4 acceptance mapping 的 contract index anchor，支撑 Stage-01 coverage planning 与 Stage-03 closure judgment 的引用纪律。 |
| `round-04-test-gate-cards` | `extracted-governance-bundle` | acceptance-coverage-planning; validation-closure-and-delivery-readiness-judgment | primary-bundle | authoring-input-ready | `card-test-entry-exit-gate` 已是 PASS 级 gate-rule 资产；`card-test-plan-gate-model` 虽仍需字段归一化，但足以作为 Phase-4 test-plan spine 的强参考。 |
| `testing-validation-external-intake-v1` | `external-method-bundle` | acceptance-coverage-planning; evidence-execution-and-defect-identification; validation-closure-and-delivery-readiness-judgment | primary-bundle | authoring-input-ready | 已新增 `sources/web/testing-validation/` first-pass intake notes，覆盖 acceptance/UAT checklist、defect record、operator runbook、closure/gate 字段 spine；适合直接支撑 control-layer authoring。 |
| `acceptance-checklist-samples` | `template-bundle` | acceptance-coverage-planning | primary-bundle | partial | seed doc 明确要求至少 2 份不同团队/项目的产品验收用例清单模板；当前仓库中尚未落库。 |
| `entry-exit-gate-checklist-samples` | `template-bundle` | acceptance-coverage-planning; validation-closure-and-delivery-readiness-judgment | primary-bundle | partial | Phase-4 当前最关键的 gate artifact 类型之一；已有 extracted gate cards，但尚缺“项目级真实 checklist 模板”样本。 |
| `uat-run-log-samples` | `template-bundle` | evidence-execution-and-defect-identification | primary-bundle | partial | 需要记录时间、环境、版本、结果、执行者、证据路径；当前种类缺失。 |
| `defect-record-samples` | `template-bundle` | evidence-execution-and-defect-identification; validation-closure-and-delivery-readiness-judgment | primary-bundle | partial | 需要复现步骤、证据、影响面、模块与 trace 映射字段；当前仓库缺失。 |
| `go-no-go-closure-samples` | `template-bundle` | validation-closure-and-delivery-readiness-judgment | primary-bundle | partial | 需要风险接受说明与 closure reasoning 字段；当前仓库缺失。 |
| `install-run-manual-samples` | `template-bundle` | evidence-execution-and-defect-identification; validation-closure-and-delivery-readiness-judgment | primary-bundle | partial | Phase-4 seed doc 明确要求 operator-facing install/run manual；当前仓库缺失。 |
| `ieee-829-style-test-doc-spine` | `standards-reference` | acceptance-coverage-planning; evidence-execution-and-defect-identification; validation-closure-and-delivery-readiness-judgment | supporting-bundle | partial | 可为 test plan / execution log / incident / summary 提供字段骨架，但当前 repo 只有种子文档中的推荐，没有本地标准摘录。 |
| `risk-based-testing` | `method-reference` | acceptance-coverage-planning; validation-closure-and-delivery-readiness-judgment | supporting-bundle | partial | 用于 coverage prioritization 与按风险分层的 exit criteria；当前只有 seed-level recommendation。 |
| `odc-defect-taxonomy` | `method-reference` | evidence-execution-and-defect-identification; validation-closure-and-delivery-readiness-judgment | sidecar | partial | 可用于缺陷分类与 process signal，但当前不应作为 Phase-4 启动 blocker。 |

---

## 当前可直接看出的结论（v0.1）

### 1. Phase-4 已经有“可冻结结构”的 source spine

目前最强的 Phase-4 本地来源已经具备：

- family skeleton
- Phase-3 / Phase-4 测试边界
- contract acceptance mapping spine
- entry/exit gate extracted governance assets
- first-pass external testing-validation intake notes

这意味着：

- Phase-4 **已经不再是零定义状态**
- 可以先进入 source-preparation / control-scope freeze

### 2. Phase-4 仍缺“可直接套用”的 Tier-0 样例层

最缺的不是测试理论，而是更完整、更多样的 Tier-0 真样例：

- acceptance checklist 真样例
- UAT run log 真样例
- defect record 真样例
- go/no-go closure 真样例
- install/run manual 真样例

这意味着：

- Phase-4 现在还不适合直接做强 runtime authoring
- 更适合先补 source-prep 与 Tier-0 intake

### 3. 当前最合理的 readiness judgement

基于 v0.1 register，Phase-4 当前最合理的状态判断为：

- **partially ready for source-grounded authoring**

当前没有 fully ready 的主要原因不是：

- 缺少阶段定义
- 缺少边界判断
- 缺少 gate 语言

而是：

- 缺少足够多的真实 Tier-0 模板/样例来把 output-template 和 gate checklist 写到可消费粒度

---

## 当前最合理的下一步

1. 定向收集最小 Tier-0 样例并落入 repo
2. 把这些样例增量映射到 `testing-validation-source-unit-coverage-ledger-v0.1.md`
3. 把这些样例绑定到 Stage-01/02/03 的 control artifacts
4. 再重新判断是否进入 Phase-4 Stage-01 control-layer authoring
