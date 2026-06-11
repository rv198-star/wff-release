# Phase-1 文档库模板单元 Ledger（v0.1）

## 目的

这份台账专门针对 Phase-1 的**文档库模板单元**做覆盖审计。

它解决的不是书本/方法卡覆盖，而是：

- 哪些模板单元理论上应支撑 Phase-1
- 当前哪些模板单元已被显式吸收
- 哪些模板单元还只是被间接影射
- 哪些模板单元尚未被正式挂接，且理由是什么

---

## 1. 字段说明

### `template_unit_id`
模板单元标识。

### `target_stage`
理论上最应该进入哪个 Stage。

### `current_adoption_state`
支持：
- `explicit`
- `implicit`
- `missing`

### `influence_level`
支持：
- `primary`
- `support`
- `weak`
- `gap`

### `evidence`
当前有哪些文档/模板/阶段产物能证明它已被吸收。

### `omission_code`
若未充分吸收，必须是：
- `deferred`
- `redundant`
- `misfit`
- `blocked`

### `justification`
说明为什么现在是这个状态。

---

## 2. Phase-1 模板单元 Ledger

| template_unit_id | target_stage | current_adoption_state | influence_level | evidence | omission_code | justification |
|---|---|---|---|---|---|---|
| research-notes-template-unit | Stage-01 | explicit | support | `templates/research-notes.md` 已新增，且 Stage-01 `output-template.md` 已显式引用 supporting template |  | 已正式化为可复用模板单元 |
| user-group-segmentation-template-unit | Stage-01 | explicit | primary | Stage-01 output-template 已有 `target_user_groups` 结构，Stage-01 core deliverables checklist 已覆盖 user groups / boundary |  | 当前已显式吸收 |
| user-case-user-story-template-unit | Stage-01 | explicit | primary | Stage-01 output-template 已有 `first_pass_user_case_or_user_story` 字段 |  | 当前已显式吸收 |
| opportunity-list-template-unit | Stage-01 | explicit | primary | Stage-01 output-template 已有 `structured_opportunity_list` 字段 |  | 当前已显式吸收 |
| problem-list-template-unit | Stage-01 | explicit | primary | Stage-01 output-template 已有 `structured_problem_list` 字段 |  | 当前已显式吸收 |
| stakeholder-analysis-template-unit | Stage-01 | explicit | weak | `templates/stakeholder-analysis.md` 已新增，且 Stage-01 `output-template.md` 已显式作为条件性 supporting template 引用 |  | 已正式化为条件启用模板单元 |
| requirements-analysis-note-template-unit | Stage-02 | explicit | primary | Stage-02 output-template 已有 `goal`, `backbone_activities`, `key_constraints`, `initial_priority_split` 等结构 |  | 当前已显式吸收 |
| story-map-template-unit | Stage-02 | explicit | primary | Stage-02 output-template 已强制 `story-map | requirements-structure`，dry-run 已有 story_map evidence |  | 当前已显式吸收 |
| constraints-list-template-unit | Stage-02 | explicit | primary | Stage-02 output-template 已有 `key_constraints` |  | 当前已显式吸收 |
| priority-split-template-unit | Stage-02 | explicit | primary | Stage-02 output-template 已有 `initial_priority_split` |  | 当前已显式吸收 |
| mvp-definition-template-unit | Stage-03 | explicit | primary | Stage-03 output-template 已有 `minimum_viable_experience_loop` 与 MVP boundary 结构 |  | 当前已显式吸收 |
| release-slicing-template-unit | Stage-03 | explicit | primary | Stage-03 output-template 已有 `first_slice`, `later_slices`, `deferred_items`, `slice_rationale` |  | 当前已显式吸收 |
| requirements-decomposition-template-unit | Stage-03 | explicit | support | Stage-03 output-template 中通过 complete/minimum loop + slicing structure 表达 |  | 已吸收，但命名上更偏 slicing 而非“拆解模板” |
| assumptions-list-template-unit | Stage-04 | explicit | primary | Stage-04 output-template 已有 `hypothesis_or_validation_target` 与 `assumptions`, `assumptions_to_validate` |  | 当前已显式吸收 |
| validation-record-template-unit | Stage-04 | explicit | primary | Stage-04 output-template 已有 `validation_method`, `feedback_or_signal`, `validation_conclusion` |  | 当前已显式吸收 |
| low-fidelity-prototype-note-template-unit | Stage-04 | explicit | support | Stage-04 output-template 已有 `prototype_or_equivalent_artifact` |  | 已吸收，但保持 optional/recommended 地位 |
| handoff-checklist-template-unit | Cross-stage / Phase-1 end | explicit | support | `templates/handoff-checklist.md` 已新增，且 `templates/output-template.md` 已显式引用 |  | 已正式化为独立模板单元 |
| handoff-contract-template-unit | Cross-stage / Phase-1 end | explicit | support | `templates/handoff-contract.md` 已新增，且 `templates/output-template.md` 已显式引用 |  | 已正式化为独立模板单元 |

---

## 3. 当前结论

### 3.1 文档库模板单元并非“大量未吸收”

更准确的情况是：

- 核心 Stage-specific 模板单元已经有相当大一部分被显式吸收
- 真正偏弱的主要是：
- 少量条件性支持模板单元

### 3.2 当前最真实的 gap 被进一步收窄了

之前我们只能说：

> 文档库模板素材吸收证据偏弱。

现在更精确的说法是：

> Phase-1 文档库模板单元已经全部进入显式或条件显式状态；  
> 当前剩余差异更多体现在“primary / support / weak”影响级别上，而不是“是否有模板单元存在”。

---

## 4. 后续动作建议

1. 若继续强化 Phase-1：
   - 优先把当前条件性 support/weak 模板单元进一步接入各阶段实际 dry-run 产物

2. 对 handoff：
   - `handoff-checklist-template-unit` 与 `handoff-contract-template-unit` 已正式化，可继续向各阶段输出物接入

3. 对 Stage-01：
   - 若后续需要强化人类审计，可把 `research-notes` 与 `stakeholder-analysis` 从 supporting templates 提升为更强的运行时产物要求
