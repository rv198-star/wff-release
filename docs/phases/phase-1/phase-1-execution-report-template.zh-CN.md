# Phase-1 执行报告模板（v0.1）

## 1. 运行元信息
- case_name:
- input_source:
- run_owner:
- run_date:
- report_version:
- delivery_profile:
  - `review-bound-starter-pack | implementation-ready-prd`
- depth_mode:
  - `baseline | creative`
- depth_mode_boundary:
  - `creative starts only after baseline sufficiency; baseline truth and creative discoveries must remain separated`
- official_runtime_entry:
  - `scripts/phase1/run_phase1_full_trial.py`
- convergence_engine:
  - `scripts/phase1/run_phase1_convergence.py`
- prd_convergence_script:
  - `scripts/phase1/phase1_converge_prd.py`
- current_overall_status:
  - `admission-review-ready | review-bound-but-not-ready | blocked`

## 2. 阶段输出清单
- stage_01_output:
- stage_02a_output:
- stage_02b_output:
  - `produced | skipped (reason: ...)`
- stage_03_output:
- stage_04_output:
- prd_assembled_draft:
- prd_main_document:
- prd_main_document_zh:
- prd_convergence_evidence:

## 3. 交付物判定矩阵

| 交付物 | Verdict | 原因 | 未决 truth 分类 | 下一步动作 |
|---|---|---|---|---|
| target user boundary | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| user groups | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| user story / user case | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| problem list | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| opportunity list | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| requirements panorama | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| main flow / backbone activities | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| requirements structure / story map | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| key constraints | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| initial priority split | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| complete experience loop | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| minimum viable experience loop | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| MVP definition | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| first slice | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| later slices | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| deferred items | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| key assumptions to validate | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| validation target | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| validation method | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| prototype/equivalent artifact | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| feedback / signal / result | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| validation conclusion | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| decision state | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| revision recommendations | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| design/architecture handoff package | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |
| PRD convergence evidence state | `PASS | WARNING | SKIP | BLOCKED` |  | `none | A | B | C` |  |

## 4. 阶段摘要

### Stage-01 摘要
- outcome:
- strongest_output:
- weakest_output:
- progression_judgment:

### Stage-02a 摘要
- outcome:
- strongest_output:
- weakest_output:
- progression_judgment:

### Stage-02b 摘要
- executed: `yes | skipped`
- skip_rationale:
- outcome:
- strongest_output:
- weakest_output:
- progression_judgment:

### Stage-03 摘要
- outcome:
- strongest_output:
- weakest_output:
- progression_judgment:

### Stage-04 摘要
- outcome:
- strongest_output:
- weakest_output:
- progression_judgment:

## 5. Warning 汇总
- 列出所有 `WARNING` 项
- 解释为什么它们不是 `BLOCKED`
- 解释下游必须如何保留这些 review-bound carryover

## 6. Blocker 汇总
- 列出所有 `BLOCKED` 项
- 指明哪些属于 Class C unresolved truth
- 指明 remediation 路径

## 7. Admission Recommendation
- recommended_formal_state:
  - `PASS | PASS with constrained/review-bound conditions | BLOCKED`
- reasoning:
- downstream_forbidden_assumptions:
- unresolved_truth_to_preserve:

### 判定说明
- 即使上面的矩阵只有 `PASS` / `WARNING`，formal admission 仍然可以是 `BLOCKED`。
- 触发条件是：当前剩余问题属于 **Class C 的 closure / evidence 缺口**，而不是某一行结构字段单独缺失。
- 也就是说，矩阵用于表达交付物层状态，formal admission 用于表达是否可以诚实进入下一阶段。
- 但在 v0.1 中，**缺少真实反馈 / 真实信号 / 真实验证记录本身，默认应先按 `WARNING` 处理**，而不是自动视为 `BLOCKED`。
- 只有当这种缺失会逼着下游阶段发明核心 user / scope / constraint truth 时，才应升级为 Class C / `BLOCKED`。

## 8. PRD 收敛结论
- prd_assembled: `yes | no`
- prd_converged: `yes | no`
- prd_deep_compilation_state:
  - `assembled-audit-rich | converged-candidate | deepening-round-1 | deepening-round-2 | deepening-round-3 | review-bound-freeze | return-remediate | blocked`
- convergence_externalization_note:
- prd_mainline_gate_bundle_command:
  - canonical 主线 gate surface:
    - `python3 scripts/phase1/run_phase1_convergence.py --source <structured-input.md> --report <phase-1-execution-report.md> --prd-candidate <prd-main-document.md> ...`
- prd_mainline_gate_bundle_result:
  - `PASS | BLOCKED`
- prd_mainline_gate_bundle_internal_gates:
  - `assembly_integrity_gate | analysis_delta_gate | section_scoring_gate | artifact_consistency_gate`
- prd_mainline_gate_bundle_detail_note:
  - 子 gate 细节仍可为审计/调试外显，但它们不再是 Phase-1 canonical 主线命令面
- not_ready_yet_because:
- next_round_focus:
