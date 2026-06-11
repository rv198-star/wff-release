# Stage-05 SOP -- prototype-spec-bridging

## 1. Stage Positioning
- Stage name:
  - prototype-spec-bridging
- Stage goal:
  - recompile the converged Phase-1 product definition package into a page-level `Surface Matrix` authority
- Parent phase:
  - product / requirements
- Upstream dependency:
  - converged PRD
  - Stage-02a structural analysis output
  - Stage-02b specification deepening output
  - Stage-03 MVP slicing output
  - Stage-04 validation / handoff output
- Downstream target:
  - Phase-2 engineering alignment
  - derived `prototype-prompt-pack.md`
- Positioning rule:
  - this is a branch stage after PRD convergence, not part of the Stage-01 -> Stage-04 mainline
  - its primary role is to freeze page-level authority, not to act as an external prototype prompt handoff

## 2. Start Conditions
- Required inputs:
  - converged PRD
  - Stage-02a output
  - Stage-03 output
  - Stage-04 output
- Optional inputs:
  - Stage-02b output when available
  - low-fidelity wireframe direction
  - design-system constraints
  - prototype execution environment constraints
- Pre-start checks:
  - is there a stable first-wave workflow backbone in the converged PRD?
  - are first-wave scope, deferred items, and forbidden assumptions explicit enough for prototype recompilation?
  - is there enough object / state detail to define pages and route transitions?
- Refusal rule:
  - refuse to start if there is no converged PRD
- Clarification expansion rule:
  - clarify page / state-critical gaps before freezing a prototype page map
- Enter `Blocked` when:
  - page / route / state logic would need to be invented from non-inferable missing fields
- Enter `Provisional Inference` when:
  - the team explicitly accepts a prototype-oriented recompilation that keeps all inferred UI assumptions visible

## 3. Standard Execution Steps
1. Confirm the first-wave product backbone.
   - Re-read the converged PRD and identify the main first-wave workflow.
   - Reconcile Stage-02a scenarios and Stage-03 MVP boundary.
   - Preserve Stage-04 forbidden-assumption discipline.
   - **Micro-checkpoint**: Is the prototype still serving the first-wave workflow, not a broadened product dream?
2. Extract the prototype-worthy structure.
   - Pull page-driving details from:
     - Stage-02a: business backbone, key scenarios, design requirements
     - Stage-02b: objects, IA direction, payload / state semantics
     - Stage-03: first-wave boundary, deferred ledger, non-goals
     - Stage-04: validation-critical workflow and interaction emphasis
   - If Stage-02b is absent, preserve the gap explicitly instead of inventing structure.
3. Compare page-map candidates before freeze.
   - Generate 2-3 page-map / route-shape candidates when ambiguity matters.
   - Compare them for:
     - workflow continuity
     - page-count simplicity
     - object consistency
     - state visibility
     - deferred-boundary honesty
   - Choose with explicit `why-this-page-map-not-that` rationale.
   - Freeze the chosen `## 4. Page Map` as a Markdown table, not as prose or nested bullets.
   - The table is the authoritative page-level `Surface Matrix`.
   - The table must contain these columns in order:
     - `page_id`
     - `page_name`
     - `route`
     - `page_blueprint_type`
     - `primary_actor`
     - `allowed_roles`
     - `primary_user_goal`
     - `bound_use_case_ids`
     - `business_objects`
     - `must_show_together`
     - `required_regions`
     - `entry_conditions`
     - `exit_conditions`
     - `next_route_candidates`
     - `denied_behavior`
     - `readiness_status`
     - `blocked_reason`
     - `primary_action`
     - `route_pattern`
     - `parent_page`
   - `route` is the authority field; `route_pattern` is a compatibility mirror for existing downstream parsers.
   - if `bound_use_case_ids` cannot be explicitly recovered from upstream evidence, the page must not silently stay `ready`
   - Missing values must be written as `TBD`; top-level pages use `—` for `parent_page`.
4. Define the main flow and route graph.
   - Make the first-wave workflow walkable from start to finish.
   - Include at least one important alternate / exception path when it materially affects prototype review.
   - Keep `user_goal` and `system_response` semantically distinct:
     - `user_goal` = the outcome the user is trying to reach
     - `system_response` = what the product/system does in response
   - Treat identical `user_goal` and `system_response` text as an outlet-gate defect.
5. Define page briefs.
   - For each page, define:
     - `why_it_exists`
     - `dominant_interaction_pattern`
     - `key_data_objects`
     - `business_state_transitions`
   - Use the heading format `### Page Brief: {page_name} ({page_id})` for every page listed in `## 4. Page Map`.
   - The four required fields above must always be present, even when some values are still `TBD`.
   - Additional page-level execution guidance may follow the required fields, but must not replace them.
   - Keep `page_goal` and `entry_condition` semantically distinct:
     - `page_goal` = why the page exists in the workflow
     - `entry_condition` = what must already be true before arrival
   - Treat identical `page_goal` and `entry_condition` text as an outlet-gate defect.
   - **Micro-checkpoint**: Does every page exist for a workflow reason, not just for UI completeness?
6. Define object / state coverage.
   - Make sure key objects keep stable names across pages.
   - Explicitly surface loading / empty / error / permission / disabled states where they matter.
   - Do not hide missing states behind optimistic “normal-only” UI.
7. Freeze prototype generation constraints.
   - Preserve first-wave scope.
   - Preserve deferred items and non-goals.
   - Preserve explicit inference notes.
   - Keep the artifact page-authoritative, not implementation-level.
   - Treat `prototype-prompt-pack.md` as derived supplementary guidance, not as authority.
8. Assemble reasoning evidence and inference log into the output template.
9. Record which required method families from `source-cards.md` materially shaped page map, route graph, and state coverage.

## 3.1 Intake / Clarification / Review State Flow
- `S0 Intake Received`:
  - inspect PRD + stage outputs and identify prototype-spec readiness
- `S1 Clarification Active`:
  - clarify workflow, page, or state gaps before route freeze
- `S2 Blocked`:
  - stop if the page map would be fabricated from missing or contradictory upstream structure
- `S3 Provisional Inference`:
  - allow only review-bound prototype recompilation drafts
- `S4 User Review`:
  - review page map, route graph, state coverage, and deferred-item boundaries
- `S5 Gate Pass`:
  - pass only when downstream teams can start from the artifact without rebuilding product logic
- `S6 Escalate`:
  - escalate if no defensible page / route / state package can be formed under the current evidence boundary

## 4. Process Checkpoints
- Checkpoint 1:
  - the first-wave workflow backbone is explicit
- Checkpoint 2:
  - the page map is coherent and routeable
  - the page map is a Markdown table, not prose or nested bullets
  - required columns `page_id`, `page_name`, and `page_blueprint_type` are present
  - missing values are explicit `TBD` values, never blank cells
  - any page with inferred or missing use-case binding is marked `review-bound` or `blocked` with an explicit `blocked_reason`
- Checkpoint 3:
  - each page has a goal, core blocks, and core actions
  - `page_goal` is not a restatement of `entry_condition`
  - `user_goal` is not a restatement of `system_response`
  - every page row in `## 4. Page Map` has a matching `### Page Brief: {page_name} ({page_id})`
- Checkpoint 4:
  - object / state consistency is preserved across pages
- Checkpoint 5:
  - key empty / error / loading / permission / disabled states are explicit
- Checkpoint 6:
  - deferred items and non-goals remain visible
- Checkpoint 7:
  - prototype generation constraints are explicit
- Checkpoint 8:
  - required prototype-recompilation method families materially shaped the output
- Fields that require confirmation or explicit review-bound status:
  - page flows that imply new product capability
  - inferred state behavior not grounded in upstream artifacts
  - visual assumptions that materially alter user action order
- Fields allowed as provisional only:
  - first-pass page naming
  - first-pass component grouping
  - first-pass visual hierarchy emphasis

## 5. Referenced Method Assets
- Required cards:
  - workflow-to-page-map recompilation
  - IA-driven page grouping
  - page goal / action framing
  - object / state visibility discipline
  - deferred / non-goal preservation
  - prototype execution constraint framing
- Optional cards:
  - low-fidelity-to-high-fidelity carryover support
  - design-system alignment support
  - review-path simplification support
- Boundary / anti-pattern cards:
  - do not generate shell-only pages
  - do not invent out-of-scope features for prototype completeness
  - do not hide empty / error / permission states
  - do not turn prototype structure into implementation contract detail

## 6. Output Generation Rules
- Required outputs:
  - prototype specification document
  - page map
  - route graph
  - page briefs
  - object / state matrix
  - key-state coverage
  - prototype generation constraints
- Minimum output rule:
  - downstream consumers must be able to start without rereading the full PRD to reconstruct page-level product logic
- Prototype / diagram rule:
  - a page-map-and-route-graph diagram is required
  - it must show:
    - major pages
    - main flow transitions
    - at least one alternate / exception path
    - explicit start and end points
- Provenance / assumptions marking rule:
  - any provisional prototype assumptions must keep status, source, confidence, verification, and prototype_inference_log fields
- Reasoning capture rule:
  - when Stage-05 chooses a page map, simplifies route structure, or surfaces key states, preserve that reasoning in the output template's reasoning section
  - the following items are REQUIRED:
    - page-map construction reasoning
    - flow preservation reasoning
    - state coverage honesty
    - deferred / non-goal preservation
    - deepening loop log
- Diagram obligation / fail action:
  - `diagram_obligation: required`
  - if the route graph is unclear, return to workflow / page-map clarification before freezing the artifact
- Output contract / fail action:
  - fail the stage if `## 4. Page Map` is emitted as prose or nested bullets
  - fail the stage if the required page-map columns are missing
  - fail the stage if any required page-map value is left blank instead of `TBD`
  - fail the stage if any page in the table lacks a matching structured `Page Brief`

## 7. Stage Acceptance
- Minimum completion standard:
  - page-level Surface Matrix authority exists
  - page map compatibility view exists
  - main flow exists
  - page briefs exist
  - object / state matrix exists
  - key-state coverage exists
  - prototype execution constraints exist
  - derived supplementary prompt guidance exists
- Common failure signals:
  - pretty page names with no workflow meaning
  - free-form Page Map prose that cannot be parsed into stable page rows
  - no end-to-end route graph
  - states only exist in happy-path form
  - deferred items silently reappear in prototype scope
  - method bundles are listed but leave no visible effect on page / route / state decisions
  - unresolved uncertainty silently flattened into polished certainty
- Return path:
  - return to workflow clarification, page-map comparison, or upstream boundary clarification as needed
- State return rule on failure:
  - go back to `S1 Clarification Active` or `S2 Blocked`
- Escalation rule:
  - escalate if no defensible prototype-spec can be formed under the current evidence boundary

## 8. Handoff Rules
- Handoff target:
  - Phase-2 engineering alignment
  - derived `prototype-prompt-pack.md`
- Handoff package:
  - prototype-spec document
  - authoritative surface matrix / page map
  - route graph
  - page briefs
  - object / state matrix
  - key-state coverage
  - deferred / non-goal boundary note
  - prototype generation constraints
- Handoff explanation requirement:
  - explain what the first-wave workflow is, how pages connect, what each page must accomplish, what states must be visible, and what downstream consumers must not invent
- Provisional content in handoff:
  - allowed only if explicitly labeled
- Whether downstream may consume provisional content:
  - yes, but only as review-bound prototype input, never as silently confirmed product truth
- Supplementary prompt-pack rule:
  - `prototype-prompt-pack.md` may supplement visual generation, but it must not add, replace, or mutate page-level authority fields frozen in `prototype-spec.md`
