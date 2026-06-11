# Testing-Validation Source Index（v0.1）

## 目的

这份最小索引表用于把 Phase-4（`testing-validation`）当前已经可用、或已经明确指向的素材容器收束成一个统一入口。

它回答三个问题：

- 当前仓库里有哪些素材已经能直接支撑 Phase-4 启动准备
- 哪些素材只是推荐方向，还缺真实 Tier-0 样例
- 这些素材分别主要喂给 Phase-4 的哪个子阶段

---

## Phase-4 边界说明（当前共识）

当前 repo 采用 4 个主生命周期大阶段，并把发布收口并入 Phase-4 的可选 Stage-04：

1. product-requirements
2. design-architecture
3. implementation-development
4. testing-validation

因此这里的 Phase-4 明确是：

- 测试设计 / 覆盖规划
- 测试执行 / 缺陷识别
- 测试收口 / 交付判断
- 可选：发布前收口 / 最终交接扩展

其中前 3 个子阶段是默认主链，发布收口只在需要正式 release gate 时作为可选 Stage-04 启用。

---

## 当前建议的 Phase-4 子阶段焦点

- `acceptance-coverage-planning`
- `evidence-execution-and-defect-identification`
- `validation-closure-and-delivery-readiness-judgment`
- `release-readiness-and-final-handoff`（optional）

---

## Source Index（v0.1）

| source_container | current_anchor | source_type | readiness_role | primary_stage_focus | current_state | notes |
|---|---|---|---|---|---|---|
| `testing-validation-source-library-seed` | `docs/source-registers/testing-validation-source-library-seed-v0.1.md` | project-seed-doc | foundation | all three Phase-4 stages | present | 当前 Phase-4 启动素材总入口；定义 Tier-0 / Tier-1 sourcing posture 与最小 starter set。 |
| `testing-validation-stage-package-v0` | `docs/phases/phase-4/testing-validation-stage-package-v0.md` | project-seed-doc | foundation | all three Phase-4 stages | present | 定义 3-stage family 骨架、目标、输入/输出与模板方向。 |
| `phase4-optional-stage04-release-readiness-draft` | `docs/release-readiness-stage-package-v0.md` | project-seed-doc | supporting | Stage-04 optional extension | present | 定义 Phase-4 可选 Stage-04 的发布收口 / 最终交接扩展边界，不再视为独立 Phase-5。 |
| `development-implementation-source-library-seed` | `docs/source-registers/development-implementation-source-library-seed-v0.1.md` | project-seed-doc | primary | Stage-01; Stage-02; Stage-03 | present | 给出 Phase-3 vs Phase-4 测试边界，避免把开发自检误塞进 Phase-4。 |
| `contract-spine` | `docs/source-registers/contract-spine-source-register-v0.1.md` | project-seed-doc | primary | Stage-01; Stage-02; Stage-03 | present | 负责 `TEST-* -> API-* -> REQ-*` 映射主脊梁。 |
| `contract-registry-template` | `templates/contract-registry-template.md` | repo-governance | primary | Stage-01; Stage-03 | present | 为 acceptance checklist 提供 `API-*` 索引与映射落点。 |
| `round-04-test-gate-cards` | `archive/extraction-runs/round-04/` | extracted-governance-bundle | primary | Stage-01; Stage-03 | present | 已有 `card-test-entry-exit-gate` PASS 与 `card-test-plan-gate-model` WARN，可分别支撑 gate checklist 与 test-plan spine。 |
| `acceptance-checklist-samples` | none yet | template-bundle | primary | Stage-01 | missing | 目标是提炼产品验收用例清单的字段 spine；当前仍缺仓库内真实样例。 |
| `entry-exit-gate-checklist-samples` | none yet | template-bundle | primary | Stage-01; Stage-03 | missing | 目标是补齐真实可执行的 entry/exit gate checklist 样例，用于把 extracted gate rule 转成项目级 checklist 字段。 |
| `uat-run-log-samples` | none yet | template-bundle | primary | Stage-02 | missing | 目标是固化验收执行记录、环境、版本、证据路径。 |
| `defect-record-samples` | none yet | template-bundle | primary | Stage-02; Stage-03 | missing | 目标是统一缺陷分类、复现证据、影响范围与 trace 关联字段。 |
| `go-no-go-closure-samples` | none yet | template-bundle | primary | Stage-03 | missing | 目标是固化测试收口判断与风险接受说明。 |
| `install-run-manual-samples` | none yet | template-bundle | primary | Stage-02; Stage-03 | missing | 目标是补齐 operator-facing 安装部署/运行说明，支持“可验收运行性”。 |
| `test-plan-standard-spine` | seed doc references IEEE 829 | standards-reference | supporting | Stage-01; Stage-02; Stage-03 | partial | 用于 test plan / execution log / incident / summary 的字段骨架，不要求全套标准化落地。 |
| `risk-based-testing` | seed doc references risk-based testing | method-reference | supporting | Stage-01; Stage-03 | partial | 用于 coverage prioritization 与 risk-tiered exit gate。 |
| `odc-defect-taxonomy` | seed doc references ODC | method-reference | sidecar | Stage-02; Stage-03 | partial | 用于缺陷分类字段与 exit gate 中的缺陷分布信号。 |

---

## 当前解释

- 当前仓库已经具备 **Phase-4 的方向性素材**，尤其是主链阶段骨架、边界说明、contract spine、test gate extracted assets。
- 当前仓库还**不具备足够多的 Tier-0 真实样例**，因此还不能像 Phase-3 那样直接进入较强的 runtime authoring。
- 这意味着：Phase-4 现在最合理的动作不是扩大主链刚性，而是先把 source-preparation 层补到可操作，再视发布场景决定是否启用可选 Stage-04。

---

## 当前最合理的下一步

1. 定向收集 5 类 Tier-0 真实样例：
   - acceptance checklist
   - entry/exit gate checklist
   - UAT run log
   - defect record
   - go/no-go closure
   - install/run manual
2. 把新增样例补入 `testing-validation-source-register-v0.1.md` 与 `testing-validation-source-unit-coverage-ledger-v0.1.md`
3. 再评估是否进入 Phase-4 Stage-01 control-layer authoring
