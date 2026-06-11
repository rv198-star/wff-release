# Stage-05 Skill Contract -- prototype-spec-bridging

## 1. Skill Goal
- This skill converts the converged Phase-1 product definition package into a page-level `Surface Matrix` authority for downstream authoring and derived prototype-generation workflows.
- It does **not** generate HTML directly, finalize visual design, or produce implementation-level engineering design.

## 2. Inputs
- Required inputs:
  - converged PRD main document
  - Stage-02a structural analysis output
  - Stage-02b specification deepening output
  - Stage-03 MVP slicing output
  - Stage-04 validation / handoff output
- Optional inputs:
  - low-fidelity wireframe direction
  - design-system constraints
  - prototype execution environment constraints
- Missing-input handling:
  - refuse or remain blocked if there is no converged PRD
  - refuse or return if upstream artifacts are too weak to reconstruct page / flow / state logic

## 2.1 Intake and State Rules
- Default intake mode:
  - prototype-spec-from-product-definition
- Allowed modes:
  - Guided
  - Context dump
  - Best guess (only if all inferred prototype assumptions remain explicit and review-bound)
- `cannot_infer` fields:
  - new product capability not present in upstream artifacts
  - visual brand decisions not present in upstream artifacts
  - implementation detail such as final API, database, or integration behavior
  - user-flow branch that contradicts frozen MVP scope or deferred-item boundaries
- `can_provisionally_infer` fields:
  - page grouping
  - first-pass page layout emphasis
  - first-pass component arrangement
  - first-pass page naming for prototype readability
- `must_validate_before_exit` fields:
  - confidence that the prototype page map preserves the upstream workflow backbone
  - confidence that key states are explicit enough for prototype execution
  - confidence that deferred / non-goal boundaries remain visible
- Provisional inference entry condition:
  - only when the team accepts a prototype-oriented recompilation that still preserves explicit inference notes
- User review checkpoint:
  - page map, main flow, and state coverage must be reviewable before downstream use
- Final gate-pass condition:
  - a prototype-spec exists, page-level Surface Matrix authority exists, main flow exists, page briefs exist, key states exist, and prototype generation constraints are explicit

## 3. Execution Steps
1. Read the converged PRD and identify the first-wave workflow backbone.
2. Reconcile Stage-02a / 02b / 03 / 04 details that materially affect pages, actions, objects, and states.
3. Define the page map and route graph needed for page-level authority.
   - Emit `## 4. Page Map` as a Markdown table, not prose or nested bullets.
   - The table is the authoritative page-level `Surface Matrix`.
   - The table must include, in order: `page_id`, `page_name`, `route`, `page_blueprint_type`, `primary_actor`, `allowed_roles`, `primary_user_goal`, `bound_use_case_ids`, `business_objects`, `must_show_together`, `required_regions`, `entry_conditions`, `exit_conditions`, `next_route_candidates`, `denied_behavior`, `readiness_status`, `blocked_reason`, `primary_action`, `route_pattern`, `parent_page`.
   - `route` is the authority field; `route_pattern` is retained as a compatibility mirror only.
   - Missing values must be explicit `TBD`; top-level pages use `—` for `parent_page`.
   - if `bound_use_case_ids` cannot be explicitly recovered from upstream evidence, the page must be marked `review-bound` or `blocked` with a concrete `blocked_reason`
4. Define page briefs with goals, information blocks, actions, and exit paths.
   - Every page row must have a matching heading `### Page Brief: {page_name} ({page_id})`.
   - Each page brief must include `why_it_exists`, `dominant_interaction_pattern`, `key_data_objects`, and `business_state_transitions`.
5. Define object / state coverage and critical empty / error / loading / permission variants.
6. Freeze prototype execution constraints, deferred boundaries, and explicit inference notes.
   - `prototype-prompt-pack.md` is derived supplementary guidance only; it must not replace page-level authority.

## 4. Outputs
- prototype specification document
  - page-level surface matrix / page map
- main flow / route graph
- page-level briefing set
- object / state matrix
- prototype execution constraints

## 4.1 Output Status and Provenance Rules
- Provisional output allowed:
  - yes, but only with explicit inference labeling
- Output status values:
  - `draft | provisional | review | approved`
- Required provenance labels:
  - `source: upstream-artifacts | inferred | mixed`
- Required confidence / verification labels:
  - yes

## 5. Output Template
- Template path:
  - `output-template.md`
- Required fields:
  - prototype_goal
  - target_consumer
  - prototype_scope
  - page_map
  - main_flow
  - page_briefs
  - object_state_matrix
  - key_state_coverage
  - deferred_and_non_goals
  - prototype_generation_constraints
- Provenance / assumptions fields:
  - status
  - source
  - confidence
  - verification
  - prototype_inference_log
  - what_breaks_if_wrong
- Diagram fields:
  - `diagram_obligation`
  - `diagram_type`
  - `diagram_minimum_elements`
  - `fail_action`
- Page Map contract:
  - `page_map` must be a Markdown table, never free-text prose or nested bullet output
  - required columns: `page_id`, `page_name`, `route`, `page_blueprint_type`, `primary_actor`, `allowed_roles`, `primary_user_goal`, `bound_use_case_ids`, `business_objects`, `must_show_together`, `required_regions`, `entry_conditions`, `exit_conditions`, `next_route_candidates`, `denied_behavior`, `readiness_status`, `blocked_reason`, `primary_action`, `route_pattern`, `parent_page`
  - blank values are not allowed; use `TBD`
  - `route` is authoritative; `route_pattern` is a compatibility mirror
- Page Brief contract:
  - every page in `page_map` must have a matching `Page Brief`
  - required fields: `why_it_exists`, `dominant_interaction_pattern`, `key_data_objects`, `business_state_transitions`

## 6. Acceptance Criteria
- DoD:
  - a coherent page-level Surface Matrix exists
  - the page map is emitted as a Markdown table with all required columns
  - the first-wave workflow can be followed across page transitions
  - each page has an explicit goal and core actions
  - each page has a structured `Page Brief` with the required four fields
  - key empty / error / loading / permission states are explicit
  - deferred items and non-goals remain explicit
  - downstream consumers can start without reconstructing product logic from the full PRD
- Common defects:
  - page-shell output with no business action logic
  - hidden invention of features outside first-wave scope
  - missing empty / error / permission states
  - deferred items silently pulled into the prototype mainline
  - prototype-friendly page naming that breaks upstream object consistency
- Gate-fail situations:
  - no coherent page map
  - page map emitted as prose or nested bullets instead of a Markdown table
  - required page-map columns missing
  - page-map cells left blank instead of `TBD`
  - no end-to-end main flow
  - no usable page briefs
  - no state coverage
  - no usable downstream authority handoff
- When provisional content cannot continue downstream:
  - if prototype logic depends on unresolved `cannot_infer` fields that were never preserved as explicit inference notes

## 7. Boundaries
- This skill does not:
  - generate HTML directly
  - finalize UI visual design
  - change MVP scope
  - define final implementation architecture
  - define API / database contract detail
- It should hand off to:
  - Phase-2 engineering alignment
  - derived prototype prompt-pack generation

## 8. Flow Rules
- Upstream sources:
  - converged PRD
  - Stage-02a / 02b / 03 / 04 outputs
- Downstream target:
  - Phase-2 engineering alignment
  - derived prototype prompt-pack generation
- Fields that must be explicit before downstream:
  - page-level surface matrix / page map
  - main flow / route graph
  - page briefs
  - object / state matrix
  - key state coverage
  - deferred and non-goal boundaries
  - prototype generation constraints
- Whether provisional content may enter downstream:
  - yes, but only as explicitly labeled prototype inference
- Required marking when provisional content is handed off:
  - preserve `status / source / confidence / verification`
  - preserve `AI-INFERRED DRAFT -- UNVERIFIED` where applicable
  - preserve `prototype_inference_log`
  - preserve explicit non-goal and deferred-item markings
  - preserve the rule that `prototype-prompt-pack.md` is supplementary only and cannot mutate page-level authority
