# Stage-05b SOP -- interaction-flow-contract

## 1. Stage Positioning
- Stage name:
  - interaction-flow-contract
- Stage goal:
  - convert the page-level `Surface Matrix` into product-side `Interaction Matrix + Flow Contract`
- Parent phase:
  - product / requirements
- Upstream dependency:
  - `prototype-spec.md`
- Downstream target:
  - Phase-2 engineering alignment
  - later compiled UI / flow consumers
- Positioning rule:
  - this stage follows `S5`
  - it must not rewrite page-level authority already frozen by `prototype-spec.md`

## 2. Standard Execution Steps
1. Read the page-level `Surface Matrix` from `prototype-spec.md`.
   - refuse to continue if required S5 authority fields are missing
2. Identify per-page lifecycle-triggered interactions required by `context_header / data_view`.
3. Identify each page's primary user-triggered interaction in `work_area`.
4. Freeze `Interaction Matrix` rows with stable `interaction_id`.
5. Freeze `Flow Contract` rows from explicit `## 5. Main Flow and Key Transitions` authority, not from page order.
   - use `from_page / to_page / context_that_must_survive_navigation` as the source of truth
6. Carry forward `review-bound / blocked` honesty from S5 instead of silently upgrading readiness.

## 3. Output Contract
- `prototype-interaction-flow-contract.md` is authoritative for:
  - `Interaction Matrix`
  - `Flow Contract`
- It must include:
  - `interaction_id / page_id / region / element_type / interaction_pattern / trigger_kind / action_type / user_intent / visibility_rule / blocked_rule / success_state / error_state / next_route / use_case_id / readiness_status / blocked_reason`
  - `flow_id / use_case_id / step_id / step_order / from_page_id / from_interaction_id / transition_condition / next_page_id / handoff_context_fields / failure_route / termination_condition / readiness_status / blocked_reason`
- It must not include P2-owned completion fields such as:
  - `input_schema_ref`
  - `display_field_set`
  - `validation_rules`
  - `enabled_rule`

## 4. Gate Rules
- pass only when:
  - at least one core page has explicit lifecycle-triggered interactions in `context_header / data_view`
  - at least one core business flow is represented as real `Flow Contract`, not only page-level `next_route`
  - `Flow Contract` rows come from explicit main-flow authority rather than page ordering heuristics
  - review-bound / blocked rows remain explicit and honest
- fail when:
  - interaction rows still live only inside narrative page briefs
  - flow remains only narrative or page-level route prose
  - flow rows are generated from page order rather than explicit `from_page / to_page` authority
  - incomplete S5 page-level authority is silently accepted with fallback defaults
  - missing upstream use-case evidence is silently replaced with fabricated certainty
