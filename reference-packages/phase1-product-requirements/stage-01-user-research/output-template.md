# Stage-01 Output Template — requirements-user-research

## 1. Document Metadata
- document_name:
- stage:
  - requirements-user-research
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
- current_problem_or_opportunity:
- document_objective:
- assumptions:
- open_questions:

## 2.1 Business Exploration Arena
- business_thesis_candidates:
  - candidate_id:
  - thesis_name:
  - target_user_or_buyer:
  - primary_pain:
  - value_mechanism:
  - likely_first_product_boundary:
  - proof_question:
- substitute_and_current_state_map:
  - substitutes:
  - substitute_pressure_types:
    - `read-only substitute | human-service substitute | fragmented-tool substitute | system-of-record substitute | workflow-fragment substitute | other:<name>`
  - current_state_pressure:
  - minimum_proof_to_beat_substitutes:
- buyer_value_proof_map:
  - primary_user:
  - continuation_or_approval_owner:
  - evidence_that_changes_decision:
- reality_density_map:
  - primary_reality_focus:
  - ordinary_baseline_probe:

## 2.2 Chosen Business Thesis
- commercial_argument_draft:
  - argument_narrative:
  - primary_substitute_pressure:
  - why_substitute_is_not_enough:
  - proof_that_changes_decision:
  - directional_proof_when_exact_roi_missing:
  - architecture_pressure:
- business_argument:
- chosen_thesis:
- why_this_not_alternatives:
- current_state_substitute_to_beat:
- substitute_pressure_types:
- buyer_user_operator_value:
- proof_target:
- review_bound_truth:
- product_boundary_implication:
- thesis_quality_gate:
  - judgment: `agentic-rewrite-required | agentic-rewrite-not-required`
  - missing_or_weak_signals:
  - script_boundary: `risk-record-only; final commercial judgment remains agentic`

## 2.3 Business Proof Track Record
- proof_track:
  - `economic-decision-proof | operational-service-proof | mixed-proof`
- dominant_proof_risk:
- proof_questions:
  - question:
- substitute_pressure:
  - alternative:
- proof_artifact:
- continuation_decision:

### Compatibility Routing Hint
- topology_archetype:
  - `execution-centric | decision-centric | hybrid`
- topology_rationale:
- primary_depth_axes:
  - `operational-chain | exception-state | role-coordination | substitute-positioning | proof-evidence | buyer-budget-continuation | other:<name>`
- secondary_depth_axes:
  - `operational-chain | exception-state | role-coordination | substitute-positioning | proof-evidence | buyer-budget-continuation | other:<name>`
- ordinary_real_world_baseline_definition:
- misfit_risk_if_wrong:
- reclassification_trigger:

## 3. Core Structured Output
- target_user_groups:
  - group:
  - boundary:
  - goal:
  - pain_point:
  - evidence_source:
- final_problem_statement:
- primary_need_framing_choice:
- first_pass_user_case_or_user_story:
- structured_problem_list:
- structured_opportunity_list:

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

This section is REQUIRED, not optional. It captures the thinking path that produced the structured output above.

### Entry Mode Record
- entry_mode:
  - `Guided | Context Dump | Best Guess`
- mode_rationale:
  - (why this mode was chosen for this run)

### Clarification Evidence
- key_questions_asked:
  - (list of the clarification questions actually asked, adapted from the Step 2 sequence)
- critical_answers_that_changed_direction:
  - (list of answers or discoveries that materially shifted the analysis direction)
- questions_skipped_and_why:
  - (any Step 2 questions that were skipped, with reasoning)

### User Boundary Alternatives
- candidates_considered:
  - candidate_1:
    - segment:
    - commercial_value:
    - behavioral_reachability:
    - evidence_strength:
    - risk:
    - cost_willingness_signal: (what would this user sacrifice — time, money, switching cost, workflow change?)
  - candidate_2:
    - segment:
    - commercial_value:
    - behavioral_reachability:
    - evidence_strength:
    - risk:
    - cost_willingness_signal:
  - candidate_3:
    - segment:
    - commercial_value:
    - behavioral_reachability:
    - evidence_strength:
    - risk:
    - cost_willingness_signal:
- chosen_segment:
- why_this_not_that:
  - (explicit comparison rationale: why the chosen segment, why not the others)
- deferred_segments_rationale:
  - (why non-chosen segments are deferred / excluded / secondary)

### Problem Narrative
- insight_synthesis_method:
  - reasoning_type: `inductive | deductive | abductive`
  - key_patterns_identified: (recurring patterns across evidence sources)
  - explanatory_hypotheses: (best explanations for observed patterns)
  - research_to_product_bridge: (how does the research insight translate to product direction?)
- empathy_narrative:
  - I am [specific user]
  - trying to [achieve outcome in user language]
  - but [what blocks them]
  - because [root friction or structural cause]
  - which makes me feel [emotional or practical cost]
- final_problem_statement:
  - (one strong, concise, shareable sentence)
- alternative_framings_considered:
  - framing_1:
    - description:
    - why_rejected:
  - framing_2:
    - description:
    - why_rejected:
- framing_selection_rationale:
  - (if multiple framings were considered, why the chosen one is primary)

### Need Framing Alternatives
- framings_compared:
  - framing_1:
    - name:
    - description:
    - strengths:
    - weaknesses:
    - downstream_implications:
  - framing_2:
    - name:
    - description:
    - strengths:
    - weaknesses:
    - downstream_implications:
- chosen_framing:
- why_this_framing_not_that:
  - (explicit rationale for the selected need framing)
- ambiguity_note:
  - (if no meaningful ambiguity exists, document why comparison was unnecessary)

### Stress Test Outcomes
- customer_care_test:
  - would_user_care:
    - (yes/no + reasoning)
  - problem_specific_enough:
    - (yes/no + reasoning)
  - real_problem_or_feature_wish:
    - (assessment with evidence)
  - so_what_answer:
    - (the concrete answer to "so what?")
  - verdict:
    - `passed | failed | inconclusive`
  - verdict_reasoning:
- positioning_pressure_test:
  - likely_category:
    - (what product category this belongs to)
  - misleading_adjacent_category:
    - (what tempting but wrong category to avoid)
  - primary_benefit:
    - (the benefit that matters most to the chosen user)
  - first_competitor_comparison:
    - (what the user would compare this against first)
  - verdict:
    - `passed | failed | inconclusive`
  - verdict_reasoning:
- feasibility_gate_test:
  - technically_feasible:
    - (yes/no + reasoning)
  - business_model_sustainable:
    - (yes/no + reasoning)
  - regulatory_barriers:
    - (yes/no + reasoning)
  - capability_gap:
    - (yes/no + reasoning)
  - verdict:
    - `passed | failed | inconclusive`
  - verdict_reasoning:

### Deepening Loop Log
- loop_state:
  - `S-draft-structured | S-deepening-round-1 | S-deepening-round-2 | S-deepening-round-3 | S-review-bound-freeze | S-return-remediate | S-blocked`
- rounds_executed:
  - (number: 0-3)
- round_log:
  - (for each round executed, record the following)
  - round_N:
    - trigger:
      - (which of the 7 deepening conditions justified this round)
    - artifact_unit_improved:
      - (which specific unit: user boundary / problem statement / need framing / assumptions / etc.)
    - what_was_refined:
      - (description of the improvement)
    - alternatives_compared:
      - (if any new alternatives were compared in this round)
    - stress_test_improved:
      - (yes/no — did a previously failed/inconclusive stress test now pass?)
    - outcome:
      - `continue | freeze | return | block`
- freeze_rationale:
  - (if frozen: why another round is unlikely to create major improvement)
- return_rationale:
  - (if returned: what specific clarification or remediation is needed)
- block_rationale:
  - (if blocked: what non-inferable truth would need to be invented)

## 4. Key Judgments and Constraints
- key_judgments:
  - (each judgment should include the sub-fields below)
  - judgment:
  - evidence_grade:
    - `user-confirmed | inferred | speculative`
  - rejected_alternatives:
    - (what other options were considered and why they were not chosen)
  - what_would_change_decision:
    - (under what conditions would this judgment be reversed)
- reasoning_notes:
  - chosen_user_boundary_rationale:
  - why_this_not_that:
    - (summary of the most important selection decisions; detailed comparison lives in Section 3.2)
  - customer_care_or_so_what_stress_test:
    - (summary verdict; detailed results live in Section 3.2)
- key_constraints:
- explicit_exclusions:

## 5. Diagram / Structured Representation
- requires_uml_or_mermaid:
  - no hard requirement
- diagram_type:
  - `actor-map | opportunity-segmentation-map | table-only`
- diagram_obligation:
  - `optional`
- diagram_minimum_elements:
  - if no diagram is used, provide a structured table covering user group, goal, pain point, and evidence source
- fail_action:
  - return to clarification and re-structure the user understanding output

## 6. Acceptance and Flow
- minimum_acceptance:
  - explicit user-group boundaries
  - final problem statement exists
  - at least one User Case / User Story draft
  - structured problem / opportunity list
  - Stage-02-consumable handoff
  - Section 3.2 Reasoning Evidence is populated (entry mode, user boundary alternatives, insight synthesis, problem narrative, stress test outcomes including feasibility gate, loop log)
  - at least one user-segment alternative was compared with why-this-not-that
  - all three stress tests have recorded verdicts (customer-care, positioning-pressure, feasibility-gate)
- handoff_to:
  - `requirements-structural-analysis` (Stage-02a)
- handoff_package:
  - structured research summary
  - user-group boundary draft
  - final problem statement
  - first-pass User Case / User Story draft
  - structured problem / opportunity list
  - assumptions / open questions
  - reasoning evidence summary (user boundary alternatives, stress test outcomes, need framing rationale)
- downstream_usage_rule:
  - downstream may use provisional content only as explicitly marked review-bound input

## 7. Referenced Assets
- referenced_cards:
- referenced_inputs:
- supporting_template_references:
  - `templates/research-notes.md`
  - `templates/stakeholder-analysis.md` (when multi-role decision chains or high-impact collaboration applies)

## 8. Core Business Deliverables Coverage
- checklist_reference:
  - `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`
- core_deliverables_covered:
  - target user boundary
  - user groups / segments
  - final problem statement
  - User Story / User Case
  - problem list
  - opportunity list
- core_deliverables_pending:
  - requirements panorama
  - main flow / backbone activities
  - MVP definition
  - validation conclusion

## 9. PRD Main Document Section Mapping
- prd_template_reference:
  - `docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md`
- this_stage_feeds:
  - `target_user_groups` → PRD §3 (Target Users & Key Roles)
  - `final_problem_statement` → PRD §2 (Problem Statement)
  - `primary_need_framing_choice` → PRD §5 (Strategic Context), PRD §6 (Product Direction Overview)
  - `first_pass_user_case_or_user_story` → PRD §14 (User Stories, Use Cases, and Requirements)
  - `structured_problem_list` → PRD §2 (Problem Statement)
  - `structured_opportunity_list` → PRD §5 (Strategic Context)
  - Section 3.2 `user_boundary_alternatives` + `why_this_not_that` → PRD §17 (Key Decision Rationale Summary)
  - Section 3.2 `need_framing_alternatives` + `why_this_framing_not_that` → PRD §17 (Key Decision Rationale Summary)
  - Section 3.2 `stress_test_outcomes` → PRD §16 (Dependencies, Risks, and Review-Bound Truth)
