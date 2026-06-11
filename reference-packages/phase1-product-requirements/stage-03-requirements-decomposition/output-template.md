# Stage-03 Output Template — requirements-decomposition-and-mvp-slicing

## 1. Document Metadata
- document_name:
- stage:
  - requirements-decomposition-and-mvp-slicing
- version:
- status:
  - `draft | provisional | review | approved`
- owner:
- source_status:
  - `user-confirmed | provisional | mixed`

## 1.1 Traceability Naming and Registry
- artifact_id:
- artifact_type:
  - `REQ | FLOW | ASSUME | MILESTONE`
- depends_on:
- feeds:
- traceability_managed_by:
  - `wff-base-traceability-management`
- trace_binding_note:
  - artifact identity and upstream/downstream relations should be allocated and managed through the `wff-base-traceability-management` skill, not free-typed manually

## 2. Context and Objective
- current_product_goal:
- why_slicing_is_needed:
- assumptions:
- open_questions:

## 3. Core Structured Output
- complete_experience_loop:
- minimum_viable_experience_loop:
- chosen_slice_strategy:
- first_slice:
- later_slices:
- deferred_items:
- epic_decomposition:
  - epic_N:
    - epic_id:
    - epic_name:
    - user_value:
    - included_user_stories_or_use_cases:
    - first_wave_status:
      - `first-slice | later-slice | mixed`
    - downstream_architecture_pressure:
- story_quality_gate:
  - story_or_use_case_N:
    - story_or_use_case:
    - mapped_epic_id:
    - independent:
    - negotiable:
    - valuable:
    - estimable:
    - small:
    - testable:
    - risk_or_note:
- requirement_translation_registry:
  - requirement_N:
    - requirement_id:
    - mapped_epic_id:
    - mapped_story_or_use_case:
    - requirement_class:
      - `functional_requirement | governance_constraint | quality_or_compliance_constraint`
    - requirement_statement:
    - why_this_class:
- acceptance_boundary_coverage_plan:
  - acceptance_item_N:
    - acceptance_id:
    - ac_tier:
      - `anchor | supporting`
    - mapped_epic_id:
    - mapped_story_or_use_case:
    - given:
    - when:
    - then:
    - expected_outcome:
    - boundary_condition_type:
    - boundary_case:
    - related_flow_step:
- source_feature_carryover_ledger:
  - source_feature_N:
    - source_detail:
    - classification:
      - `first-wave abstraction | later slice | deferred seam | explicit out-of-scope`
    - preserved_form:
    - why_this_classification:
    - downstream_visibility_rule:
- slice_rationale:
  - value_reason:
  - risk_reason:
  - dependency_reason:
- key_assumptions_to_validate:

- nfr_slice_impact:
  - stage_02b_available: `yes | no`
  - nfr_forcing_into_first_slice:
    - (which NFRs force capabilities into the first slice, and why — e.g., "data isolation required from day 1 due to multi-tenant architecture")
  - nfr_relaxed_for_mvp:
    - (which NFRs are intentionally relaxed for MVP, with justification — e.g., "performance target relaxed from 1s to 3s for MVP; acceptable for early adopters")
  - domain_dependency_impact:
    - (which domain model entity dependencies affected slice ordering — e.g., "recommendations depend on monitoring data; monitoring must be in first slice")
  - value_frequency_assessment:
    - (for contested first-slice items: value × frequency ranking that informed the decision)

## 3.1 Provenance / Confidence / Verification
- source:
  - `user | inferred | external | mixed`
- confidence:
  - `high | medium | low`
- verification:
  - `required | waived | confirmed`
- assumptions_to_validate:
- what_changes_if_wrong:
- ai_inferred_marker:
  - `AI-INFERRED DRAFT — UNVERIFIED` (required if provisional content exists)

## 3.2 Reasoning Evidence

This section is REQUIRED, not optional.

### Slice Alternatives Comparison
- candidates_considered:
  - candidate_1:
    - name:
    - what_is_in_first_slice:
    - user_value_speed:
    - evidence_confidence:
    - dependency_complexity:
    - validation_leverage:
    - risk_of_overreach:
  - candidate_2:
    - name:
    - what_is_in_first_slice:
    - user_value_speed:
    - evidence_confidence:
    - dependency_complexity:
    - validation_leverage:
    - risk_of_overreach:
- chosen_slice_strategy:
- why_this_slice_not_that:

### MVP Loop Viability Test
- is_the_mvp_a_complete_loop:
  - (yes/no + what makes it a loop, not just a reduced feature set)
- what_makes_it_minimum:
  - (what was removed and why the loop still works without it)
- what_would_break_viability:
  - (if we removed one more thing, what breaks?)

### Deferred Items Honesty Check
- for_each_deferred_item:
  - item:
  - why_not_in_mvp:
  - what_would_falsely_make_mvp_look_complete:
  - impact_of_deferral:

### Source Feature Carryover Ledger
- for_each_source_feature:
  - source_detail:
  - classification:
    - `first-wave abstraction | later slice | deferred seam | explicit out-of-scope`
  - preserved_form:
  - why_this_classification:
  - downstream_visibility_rule:

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

## 4. Key Judgments and Constraints
- slicing_basis:
- reasoning_notes:
  - chosen_mvp_rationale:
  - why_this_slice_not_that:
    - (summary; detailed comparison lives in Section 3.2)
  - deferred_items_rationale:
    - (summary; detailed honesty check lives in Section 3.2)
  - validation_linkage_rationale:
- major_constraints:
- explicit_exclusions:

## 5. Diagram / Structured Representation
- requires_uml_or_mermaid:
  - yes
- diagram_type:
  - `slice-map`
- diagram_obligation:
  - `required`
- diagram_minimum_elements:
  - at least 2 slices
  - each slice includes capability boundary
  - each slice includes acceptance target
  - each slice includes key dependency
  - deferred items are explicit
- fail_action:
  - return to slice logic work; if no defensible viable loop exists, return to upstream structure clarification

## 6. Acceptance and Flow
- minimum_acceptance:
  - minimum viable experience loop exists
  - first / later / deferred items are explicit
  - epic decomposition exists and groups the first-wave promise coherently
  - primary story/use cases have visible `INVEST` evaluation
  - requirement translation keeps `functional_requirement` and governance/compliance constraints distinguishable
  - acceptance-boundary coverage plan expresses key ACs with `Given / When / Then` and visible boundary cases
  - critical-path or high-risk ACs are visibly distinguished from supporting ACs when the case benefits from that split
  - source feature carryover ledger is explicit
  - slice logic is explainable
  - chosen slice rationale exists
  - slice-map evidence exists
  - Stage-04-consumable handoff exists
- handoff_to:
  - `requirements-validation-and-concept-proof`
- handoff_package:
  - MVP definition
  - slice explanation
  - slice-map evidence
  - source feature carryover ledger
  - slice rationale
  - key assumptions to validate
  - deferred items and rationale
- downstream_usage_rule:
  - downstream may consume provisional content only as explicitly marked review-bound validation input

## 7. Referenced Assets
- referenced_cards:
- referenced_inputs:

## 8. Core Business Deliverables Coverage
- checklist_reference:
  - `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`
- core_deliverables_covered:
  - complete experience loop
  - minimum viable experience loop
  - MVP definition
  - chosen slice rationale
  - first slice
  - later slices
  - deferred items
  - source feature carryover ledger
  - slice rationale
  - key assumptions to validate
- core_deliverables_pending:
  - validation target / hypothesis
  - validation method
  - validation conclusion
  - revision recommendations

## 9. PRD Main Document Section Mapping
- prd_template_reference:
  - `docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md`
- this_stage_feeds:
  - `complete_experience_loop` → PRD §12 (MVP Definition & Scope)
  - `minimum_viable_experience_loop` → PRD §12 (MVP Definition & Scope)
  - `first_slice` + `later_slices` → PRD §12 (MVP Definition & Scope)
  - `epic_decomposition` → PRD §14 (User Stories, Use Cases, and Requirements)
  - `story_quality_gate` → PRD §14 (User Stories, Use Cases, and Requirements — INVEST)
  - `requirement_translation_registry` → PRD §14 (User Stories, Use Cases, and Requirements — requirement translation and classification)
  - `acceptance_boundary_coverage_plan` → PRD §12 / §14 (Acceptance Criteria + Requirement Trace Matrix)
  - `deferred_items` → PRD §12 (MVP Definition & Scope), PRD §15 (Out of Scope)
  - `source_feature_carryover_ledger` → PRD §12 (MVP Definition & Scope), PRD §15 (Out of Scope)
  - `nfr_slice_impact` → PRD §12 (MVP Definition & Scope — NFR-aware slicing impact)
  - `key_assumptions_to_validate` → PRD §16 (Dependencies, Risks, and Review-Bound Truth)
  - Section 3.2 `slice_alternatives` + `why_this_slice_not_that` → PRD §17 (Key Decision Rationale Summary)
  - Section 3.2 `mvp_loop_viability_test` → PRD §12 (MVP Definition & Scope)
  - Section 3.2 `deferred_items_honesty_check` → PRD §12 (MVP Definition & Scope — deferred items rationale)
