# Stage-05 Output Template -- prototype-spec-bridging

## 1. Document Metadata
- document_name:
- stage:
  - prototype-spec-bridging
- version:
- status:
  - `draft | provisional | review | approved`
- owner:
- source_status:
  - `upstream-artifacts | inferred | mixed`

## 1.1 Traceability Naming and Registry
- artifact_id:
- artifact_type:
  - `SPEC | FLOW | STATE | HOFF`
- depends_on:
- feeds:
- traceability_managed_by:
  - `wff-base-traceability-management`
- trace_binding_note:
  - artifact identity and upstream / downstream relations should be allocated and managed through the `wff-base-traceability-management` skill, not free-typed manually

## 2. Context and Objective
- current_product_context:
- prototype_goal:
- intended_consumers:
  - Phase-1 downstream authoring
  - Phase-2 engineering alignment
  - derived prototype prompt-pack generator
  - design review
  - architecture review
- authority_role:
  - `P1 Surface Matrix authority`
- supplementary_artifacts:
  - `prototype-prompt-pack.md` is derived supplementary guidance only; it must not replace page-level authority
- assumptions:
- open_questions:

## 3. Prototype Scope and Boundary
- prototype_scope:
  - first_wave_in_scope:
  - explicit_out_of_scope:
  - deferred_items:
  - non_goals:
- scope_boundary_note:
- forbidden_assumptions:

## 4. Page Map
- page_map_format_rule:
  - MUST use a Markdown table; free-text lists or prose are not allowed
  - all required columns must exist in the exact order below
  - empty values must be written as `TBD`; top-level pages use `—` for `parent_page`
  - this table is the authoritative page-level `Surface Matrix`
  - `route` is the authority field; `route_pattern` is a compatibility mirror only
  - `page_name` must stay business-semantic; do not replace it with endpoint or schema names
- required_page_map_table:

| page_id | page_name | route | page_blueprint_type | primary_actor | allowed_roles | primary_user_goal | bound_use_case_ids | business_objects | must_show_together | required_regions | entry_conditions | exit_conditions | next_route_candidates | denied_behavior | readiness_status | blocked_reason | primary_action | route_pattern | parent_page |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P01 | 首页仪表板 / overview | /overview | dashboard | marketing owner | marketing owner | 保持首波工作流与当前优先级可见 | uc.use-case-1 | Scope, Finding, Recommendation | Scope + Recommendation, next action readiness | context_header,data_view,work_area,status_feedback,next_steps | scope is configured | next item selected | /findings | show-inline-denied-banner | ready | `` | 查看基线与本轮重点 | /overview | — |
| P02 | 发现详情 / findings | /findings | analysis-board | marketing owner | marketing owner | 解释 finding 并进入决策 | uc.use-case-2 | Finding, Recommendation, Competitor Context | Finding + Recommendation + next action readiness | context_header,data_view,work_area,status_feedback,next_steps | overview context selected | recommendation decision recorded | /decisions | hide-primary-action-and-show-denied-hint | ready | `` | 解释 finding 并进入决策 | /findings | P01 |
| P03 | 决策工作台 / decisions | /decisions | decision-workbench | marketing owner | marketing owner | 冻结 recommendation 决策 | uc.use-case-3 | Recommendation, Task, Evidence | Recommendation + Task + next action readiness | context_header,data_view,work_area,status_feedback,next_steps | finding context preserved | decision confirmed | /tasks | hide-primary-action-and-show-denied-hint | ready | `` | 冻结 recommendation 决策 | /decisions | P02 |
| P04 | 执行工作台 / tasks | /tasks | execution-workbench | content operator | content operator | 接收并推进 task | uc.use-case-4 | Task, Owner, Execution Note | Task + Execution Note + next action readiness | context_header,data_view,work_area,status_feedback,next_steps | decision frozen | task execution updated | /review | hide-primary-action-and-show-denied-hint | ready | `` | 接收并推进 task | /tasks | P03 |
| P05 | 复盘结论 / review | /review | review-decision | business owner | business owner | 做出 continue / revise 决策 | uc.use-case-5 | Review Report, Task, Trend | Review Report + Trend + next action readiness | context_header,data_view,work_area,status_feedback,next_steps,audit_strip | task execution context preserved | decision recorded | — | show-inline-denied-banner | ready | `` | 做出 continue / revise 决策 | /review | P04 |

- page_map_column_rules:
  - `page_id`: unique page identifier in `P01`, `P02` style
  - `page_name`: business page name, may include route slug suffix for clarity
  - `route`: canonical route authority for downstream consumption
  - `page_blueprint_type`: one of `dashboard | setup-flow | analysis-board | decision-workbench | execution-workbench | review-decision | detail-view | list-view`
  - `primary_actor`: primary role using the page
  - `allowed_roles`: stable role list allowed to access the page
  - `primary_user_goal`: page-level business goal, not visual description
  - `bound_use_case_ids`: use cases bound to the page-level contract
  - `business_objects`: page-level business object set
  - `must_show_together`: objects / context that must remain visible together
  - `required_regions`: required regions such as `context_header,data_view,work_area,status_feedback,next_steps`
  - `entry_conditions`: what must already be true before the page may be entered
  - `exit_conditions`: what must be true before the page can complete or hand off
  - `next_route_candidates`: allowed next routes from this page
  - `denied_behavior`: frontend behavior when access is denied
  - `readiness_status`: `ready | blocked | review-bound | stale`
  - `blocked_reason`: required whenever `readiness_status != ready`
  - `primary_action`: legacy compatibility field for existing downstream consumers
  - `route_pattern`: compatibility mirror of `route`
  - `parent_page`: derived navigation hierarchy field; use `—` for top-level pages
- navigation_structure_note:
  - page hierarchy should preserve the first-wave workflow backbone rather than flatten every page to the top level

## 5. Main Flow and Key Transitions
- main_flow:
  - step_1:
    - from_page:
    - user_goal:
      - what the user is trying to accomplish at this step
      - do not restate the system behavior here
    - system_response:
      - what the product/system must do, validate, generate, or reveal in response
      - do not duplicate user_goal
    - to_page:
  - step_2:
    - from_page:
    - user_goal:
      - what the user is trying to accomplish at this step
      - do not restate the system behavior here
    - system_response:
      - what the product/system must do, validate, generate, or reveal in response
      - do not duplicate user_goal
    - to_page:
- alternate_paths:
  - path_1:
    - trigger:
    - consequence:
    - visible_pages:
- route_graph_note:

## 6. Page Briefs
- page_briefs_rule:
  - every page in §4 must have one matching `Page Brief`
  - the heading format MUST be `### Page Brief: {page_name} ({page_id})`
  - the four fields below are mandatory and must not be omitted

### Page Brief: {page_name} ({page_id})
- **why_it_exists**:
- **dominant_interaction_pattern**: `wizard | master-detail | kanban | summary-cards | form | table-view`
- **key_data_objects**:
- **business_state_transitions**:

- page_briefs_extended_fields:
  - recommended_layout:
    - primary_region:
      - what occupies the main content area
    - secondary_region:
      - sidebar or supplementary content (if any)
    - action_region:
      - where primary and secondary CTAs are placed
  - entry_condition:
    - what must already be true before the user arrives here
    - do not restate `why_it_exists`
  - core_information_blocks:
    - block_1:
    - block_2:
  - core_actions:
    - action_1:
    - action_2:
  - important_state_variants:
    - normal
    - empty
    - error
    - loading
    - permission_limited
    - disabled_or_blocked
  - exit_paths:
  - user_facing_copy_hints:
    - page_title_text:
    - primary_cta_text:
    - empty_state_message:
  - prototype_inference_note:

## 7. Core Objects and State Matrix
- object_state_matrix:
  - object_1:
    - object_name:
    - visible_in_pages:
    - required_states:
      - state_1:
      - state_2:
    - state_changing_actions:
    - blocked_or_exception_notes:
  - object_2:
    - object_name:
    - visible_in_pages:
    - required_states:
    - state_changing_actions:
    - blocked_or_exception_notes:

## 8. Key State Coverage
- key_state_coverage:
  - loading_state:
    - where_visible:
    - why_required:
  - empty_state:
    - where_visible:
    - why_required:
  - error_state:
    - where_visible:
    - why_required:
  - permission_state:
    - where_visible:
    - why_required:
  - disabled_or_blocked_state:
    - where_visible:
    - why_required:
- state_gap_note:

## 9. Prototype Generation Constraints
- prototype_generation_constraints:
  - must_preserve_main_flow:
  - must_not_add_features_outside_scope:
  - must_cover_key_states:
  - must_keep_deferred_items_out_of_mainline_ui:
  - must_mark_inferred_content:
  - may_use_static_html_css_js_only:
  - preferred_output_shape:
    - `single-file | small-multi-file`
  - prototype_prompt_pack_status:
    - `derived supplementary only`
  - phase3_consumption_rules:
    - page_map.page_name is the authoritative source for route paths and page titles in Phase-3
    - page_map.page_blueprint_type is the authoritative source for layout pattern selection in Phase-3
    - Phase-2 and Phase-3 scripts MUST NOT replace page_name with API-endpoint-derived names
    - `prototype-prompt-pack.md` must not add, replace, or mutate page-level authority fields
    - Phase-3 frontend implementation MUST NOT render page_goal, positioning, primary_actor, or design_guardrails as user-visible UI copy
    - these fields shape the page design; they are not the page content
- execution_handoff_note:

## 10. Provenance / Confidence / Verification
- source:
  - `upstream-artifacts | inferred | mixed`
- confidence:
  - `high | medium | low`
- verification:
  - `required | waived | confirmed`
- prototype_inference_log:
  - inference_1:
    - inferred_item:
    - why_needed:
    - why_safe_enough:
    - what_breaks_if_wrong:
- ai_inferred_marker:
  - `AI-INFERRED DRAFT -- UNVERIFIED` (required if provisional content exists)

## 11. Reasoning Evidence

This section is REQUIRED, not optional.

### Page-Map Construction Reasoning
- page_candidates_considered:
  - candidate_1:
    - name:
    - why_considered:
    - why_rejected_or_kept:
  - candidate_2:
    - name:
    - why_considered:
    - why_rejected_or_kept:
- chosen_page_map_logic:
- why_this_page_map_not_that:

### Flow Preservation Reasoning
- workflow_backbone_used:
- what_must_not_break_across_pages:
- where_route_simplification_was_allowed:
- where_route_simplification_was_forbidden:

### State Coverage Honesty
- explicit_states_preserved_from_upstream:
- states_inferred_for_prototype_usability:
- states_still_missing:
- downstream_risk_if_missing:

### Deferred / Non-Goal Preservation
- deferred_items_that_must_remain_hidden_from_mainline:
- non_goals_that_must_not_reappear_as_ui:
- prototype_risk_if_boundary_is_blurred:

### Deepening Loop Log
- loop_state:
  - `S-draft-structured | S-deepening-round-N | S-review-bound-freeze | S-return-remediate | S-blocked`
- rounds_executed:
- round_log:
  - round_N:
    - trigger:
    - artifact_unit_improved:
    - what_was_refined:
    - outcome:
      - `continue | freeze | return | block`
- freeze_rationale:

## 12. Diagram / Structured Representation
- requires_uml_or_mermaid:
  - yes
- diagram_type:
  - `page-map-and-route-graph`
- diagram_obligation:
  - `required`
- diagram_minimum_elements:
  - major pages
  - main flow transitions
  - at least one alternate / exception path
  - explicit start and end points
- fail_action:
  - return to page-map and route clarification if no coherent route graph exists

## 13. Acceptance and Flow
- minimum_acceptance:
  - prototype goal exists
  - page map exists
  - main flow exists
  - page briefs exist
  - object / state matrix exists
  - key state coverage exists
  - prototype generation constraints exist
  - external-prototype-consumable handoff exists
- handoff_to:
  - external HTML prototype execution
- handoff_package:
  - prototype-spec document
  - page map
  - route graph
  - page briefs
  - object / state matrix
  - key state coverage
  - deferred / non-goal boundary note
  - prototype generation constraints
- downstream_usage_rule:
  - downstream may consume provisional content only as explicitly marked prototype inference
  - downstream must not treat inferred UI detail as confirmed product truth
- output_validation_rules:
  - Page Map MUST be a Markdown table; prose description or nested list output is a gate-fail
  - the table MUST contain at least `page_id`, `page_name`, and `page_blueprint_type`
  - all required columns in §4 MUST be present; missing values MUST be marked `TBD`, never left blank
  - every page row in §4 MUST have a matching `Page Brief`

## 14. Referenced Upstream Artifacts
- referenced_prd:
- referenced_stage_outputs:
  - Stage-02a:
  - Stage-02b:
  - Stage-03:
  - Stage-04:
- referenced_sections:

## 15. Prototype Execution Mapping
- this_artifact_feeds:
  - page_map -> HTML page / file planning
  - main_flow -> clickable route design
  - page_briefs -> page content / module scaffolding
  - object_state_matrix -> stateful UI representation
  - key_state_coverage -> empty / error / loading / permission page variants
  - prototype_generation_constraints -> prototype executor guardrails
