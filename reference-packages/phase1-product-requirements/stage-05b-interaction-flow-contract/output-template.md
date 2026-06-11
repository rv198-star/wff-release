# Stage-05b Output Template -- interaction-flow-contract

## 1. Metadata
- document_name:
- artifact_id:
- version:
- status:
  - `draft | provisional | review | approved`
- owner:
- derived_from:
  - `prototype-spec.md`

## 2. Objective and Authority
- authority_role:
  - `P1 Interaction Matrix + Flow Contract authority`
- upstream_dependency:
  - `prototype-spec.md` remains the page-level `Surface Matrix` authority
- downstream_usage_rule:
  - P2 may enrich P2-owned columns later, but must not silently rewrite P1-owned interaction or flow semantics
- S5_to_S5b_boundary:
  - `S5` owns page-level route / blueprint / role / object / required-regions truth
  - `S5b` owns interaction-level product-side semantics and cross-page flow semantics
  - `prototype-prompt-pack.md` is supplementary only

## 3. Interaction Matrix
- table_rule:
  - MUST use a Markdown table
  - every core page should contain lifecycle-triggered rows for key `context_header / data_view`
  - if readiness is not `ready`, `blocked_reason` must be explicit

| interaction_id | page_id | region | element_type | interaction_pattern | trigger_kind | action_type | user_intent | visibility_rule | blocked_rule | success_state | error_state | next_route | use_case_id | readiness_status | blocked_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| onboarding-scope-setup.load-context-header | P01 | context_header | summary-card | detail-inspect | page_load | load_context | 查看当前页面上下文与角色状态 | role in [growth owner] | block-if-required-page-context-is-missing | render-context-summary | show-context-load-error | — | uc.use-case-1 | ready | `` |
| onboarding-scope-setup.load-data-view | P01 | data_view | detail-panel | detail-inspect | page_load | load_context | 查看页面决策所需数据 | role in [growth owner] | block-if-required-page-context-is-missing | render-page-data-view | show-data-view-load-error | — | uc.use-case-1 | ready | `` |
| onboarding-scope-setup.activate-scope-and-continue | P01 | work_area | form | create-record | user_action | create | 激活 scope 并继续主流程 | role in [growth owner] | block-if-entry-conditions-or-upstream-context-are-not-satisfied | advance-workflow-or-refresh-page-state | show-inline-action-error-and-preserve-context | /overview | uc.use-case-1 | ready | `` |

## 4. Flow Contract
- table_rule:
  - MUST use a Markdown table
  - if a flow step depends on a review-bound / blocked page, the flow row must inherit that readiness state
  - rows must be derived from explicit `from_page / to_page / context_that_must_survive_navigation` authority, not from page order

| flow_id | use_case_id | step_id | step_order | from_page_id | from_interaction_id | transition_condition | next_page_id | handoff_context_fields | failure_route | termination_condition | readiness_status | blocked_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| flow.use-case-1 | uc.use-case-1 | step.onboarding-scope-setup-to-overview | 1 | P01 | onboarding-scope-setup.activate-scope-and-continue | activate scope completed and workflow_context preserved | P02 | workflow_context | /onboarding-scope-setup | — | ready | `` |

## 5. P1 / P2 Boundary
- P1-owned interaction fields:
  - `interaction_id / page_id / region / element_type / interaction_pattern / trigger_kind / action_type / user_intent / visibility_rule / blocked_rule / success_state / error_state / next_route / readiness_status / blocked_reason`
- P1-owned flow fields:
  - `use_case_id / flow_id / step_id / step_order / from_page_id / from_interaction_id / transition_condition / next_page_id / handoff_context_fields / failure_route / termination_condition / readiness_status / blocked_reason`
- P2-owned later enrichment:
  - `input_schema_ref / display_field_set / validation_rules / enabled_rule`
