# Stage-02a Output Template — requirements-structural-analysis

## 1. Document Metadata
- document_name:
- stage:
  - requirements-structural-analysis
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

## 2.1 Inherited Topology Profile Record
- inherited_topology_archetype:
  - `execution-centric | decision-centric | hybrid`
- inherited_topology_rationale:
- inherited_primary_depth_axes:
  - `operational-chain | exception-state | role-coordination | substitute-positioning | proof-evidence | buyer-budget-continuation | other:<name>`
- inherited_secondary_depth_axes:
  - `operational-chain | exception-state | role-coordination | substitute-positioning | proof-evidence | buyer-budget-continuation | other:<name>`
- topology_source_artifact:
- structure_implications:
- misfit_risk_if_wrong:
- reclassification_status:
  - `unchanged | rerouted`
- reclassification_rationale:

## 3. Core Structured Output
- goal:
- chosen_panorama_structure:
- backbone_activities:
  - activity:
  - tasks:
  - is_main_flow:
- requirements_panorama:
  - `story-map | requirements-structure`
- key_constraints:
- initial_priority_split:
  - high_value_first:
  - high_risk_to_validate:
  - deferrable:
- high_risk_validation_point:

- stakeholder_analysis:
  - stakeholder_list:
    - stakeholder_N:
      - role:
      - relationship_to_product:
      - influence_level: `high | medium | low`
      - key_concerns:
  - key_stakeholder_profiles:
    - stakeholder_N:
      - role:
      - success_criteria:
      - potential_resistance:
      - conflict_points:
      - engagement_strategy:
  - adoption_chain:
    - (who must say yes, in what order, for the product to be adopted)
  - stakeholder_conflicts:
    - (where do stakeholder interests diverge)

- chosen_business_thesis_carryover:
  - chosen_thesis:
  - why_this_not_alternatives:
  - current_state_substitute_to_beat:
  - proof_target:
  - product_boundary_implication:
  - stage_02_structural_implication:

- key_business_scenarios:
  - business_processes_identified:
    - main_flow:
    - variant_flows:
    - supporting_processes:
    - management_processes:
  - scenario_list:
    - scenario_N:
      - role:
      - scenario_name: `[verb-object]`
      - backbone_activity:
      - analysis_depth: `full | identification-only`
  - key_scenario_analysis:
    - scenario_N:
      - scenario_context: (who, when, why triggered)
      - key_challenges: (what makes this hard, uncertain, or failure-prone)
      - solution_direction: (what the product must do — functional need, not UI)
      - success_criteria: (how we know it is handled well)

- persona_scenario_set:
  - personas:
    - persona_N:
      - name:
      - type: `primary | secondary | negative`
      - role_archetype:
      - goals:
        - life_goals:
        - experience_goals:
        - end_goals:
      - behavioral_patterns:
      - pain_points:
      - mental_model:
  - context_scenarios:
    - scenario_N:
      - persona:
      - trigger_situation:
      - narrative: (day-in-the-life description in user language)
      - expected_outcome:
  - key_path_scenarios:
    - scenario_N:
      - persona:
      - interaction_traced:
      - linked_business_scenario:
      - end_to_end_flow:
  - design_requirements:
    - requirement_N:
      - pattern: "The system must enable [persona] to [accomplish goal] when [context/trigger] so that [outcome]"
      - source_scenario:
      - priority: `high | medium | low`

### 3.0 NFR Initial Identification

> This section is a lightweight NFR dimension scan, NOT a full quality-scenario table.
> Its purpose is to ensure downstream stages (especially Phase-2 architecture) have minimum awareness of which NFR dimensions are relevant and what is currently known.

- nfr_initial_identification:
  - nfr_dimensions_scan:
    - dimension_1:
      - name: (e.g. performance, security, availability, usability, scalability, maintainability, etc.)
      - relevance: `relevant | suspected-relevant | not-applicable`
      - information_state: `identified | suspected | not-applicable | unknown`
      - basis: (why this dimension is relevant or not — brief evidence or reasoning)
      - known_signals: (any constraints, user expectations, or domain patterns already surfaced in Stage-01/02a)
    - dimension_2:
      - ...
    - (repeat for each considered dimension)
  - nfr_scan_completeness:
    - dimensions_considered: (count)
    - dimensions_relevant: (count)
    - dimensions_unknown: (count)
    - scan_confidence: `high | medium | low`
    - scan_confidence_note: (what would increase confidence — e.g. "need user input on expected load" or "security requirements depend on data sensitivity classification not yet done")
  - stage_02b_dependency_note:
    - stage_02b_planned: `yes | no | undecided`
    - if_skipped_impact: (what Phase-2 will lack if 02b is not executed — must be explicitly stated)
    - minimum_viable_for_phase2: `yes | no`
    - minimum_viable_note: (if yes: what Phase-2 can safely start with from this scan alone; if no: what additional work is needed before Phase-2)

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

### Value Loop Articulation
- value_loop_description:
  - (what does the user do, what do they get back, why do they return — in outcome language)
- stage_01_framing_preserved:
  - (which Stage-01 user/problem framing decisions are carried forward and why)

### Structure Alternatives Comparison
- candidates_considered:
  - candidate_1:
    - name:
    - description:
    - clarity:
    - downstream_sliceability:
    - customer_problem_fit:
    - value_first_realism:
    - evidence_strength:
    - risk_of_fake_certainty:
  - candidate_2:
    - name:
    - description:
    - clarity:
    - downstream_sliceability:
    - customer_problem_fit:
    - value_first_realism:
    - evidence_strength:
    - risk_of_fake_certainty:
- chosen_structure:
- why_this_structure_not_that:
  - (explicit comparison rationale for each rejected candidate)

### Constraint Stress-Test Outcomes
- constraints_tested:
  - constraint_N:
    - constraint:
    - real_or_inferred_or_convenient:
    - what_collapses_if_wrong:
    - belongs_in: `key_constraints | assumptions_to_validate`
- structure_dependency_check:
  - (does this structure depend on evidence we do not really have?)
  - (are we confusing a useful shape with validated truth?)

### Priority Split Reasoning
- high_value_first_rationale:
  - (why these items are high-value, not merely visible)
- high_risk_to_validate_rationale:
  - (why these items need validation, not just "they are hard")
- deferrable_rationale:
  - (why deferral does not break first-loop viability)

### Structure Stress-Test Outcome
- can_stage_03_slice_without_rebuilding:
  - (yes/no + reasoning)
- backbone_is_product_loop_not_feature_list:
  - (yes/no + reasoning)
- structure_survives_weakened_assumption:
  - (yes/no — which assumption was tested?)
- upstream_uncertainty_preserved_honestly:
  - (yes/no + reasoning)
- verdict:
  - `passed | failed | inconclusive`

### Stakeholder Analysis Evidence
- stakeholder_identification_method:
  - (how were stakeholders identified — systematic sweep, upstream input, domain knowledge)
- key_conflicts_surfaced:
  - (what stakeholder conflicts were identified and how they affect structure)
- adoption_chain_reasoning:
  - (why this adoption sequence, what would change if a key stakeholder resists)

### Business Scenario Analysis Evidence
- scenario_selection_rationale:
  - (why these scenarios were selected for deep analysis)
- deprioritized_scenarios:
  - (which scenarios were identified but not deeply analyzed, and why)
- scenario_challenge_quality:
  - (are the identified challenges real constraints or just complexity signals?)

### Persona/Scenario Construction Evidence
- persona_data_sources:
  - (what Stage-01 research data supports each persona)
- scenario_coverage_assessment:
  - (do the context + key-path scenarios cover the critical paths identified in business scenario analysis?)
- design_requirement_traceability:
  - (can each design requirement be traced back to a persona goal + scenario context?)

### Deepening Loop Log
- loop_state:
  - `S-draft-structured | S-deepening-round-N | S-review-bound-freeze | S-return-remediate | S-blocked`
- rounds_executed:
- round_log:
  - round_N:
    - trigger:
    - artifact_unit_improved:
    - what_was_refined:
    - alternatives_compared:
    - stress_test_improved:
    - outcome:
      - `continue | freeze | return | block`
- freeze_rationale:
- return_rationale:
- block_rationale:

## 4. Key Judgments and Constraints
- key_judgments:
  - (each judgment should include the sub-fields below)
  - judgment:
  - evidence_grade:
    - `user-confirmed | inferred | speculative`
  - rejected_alternatives:
  - what_would_change_decision:
- reasoning_notes:
  - chosen_structure_rationale:
    - (summary; detailed comparison lives in Section 3.2)
  - why_this_structure_not_that:
    - (summary; detailed comparison lives in Section 3.2)
  - priority_split_rationale:
    - (summary; detailed reasoning lives in Section 3.2)
  - constraint_interpretation_rationale:
    - (summary; detailed stress-test lives in Section 3.2)
- key_constraints_interpretation:
- explicit_exclusions:

## 5. Diagram / Structured Representation
- requires_uml_or_mermaid:
  - yes, unless a structure table gives equivalent minimum elements
- diagram_type:
  - `story-map | requirements-structure` (required)
  - `business-process-flow` (optional)
  - `business-scenario-map` (optional)
- diagram_obligation:
  - `required`
- diagram_minimum_elements:
  - at least 3 backbone activities
  - at least 2 tasks under each activity
  - one marked main flow
  - at least one boundary / exclusion
  - at least one high-risk validation point
- fail_action:
  - return to structure building; if upstream understanding is too weak, return to Stage-01 clarification

## 6. Acceptance and Flow
- minimum_acceptance:
  - whole-picture structure exists
  - key constraints exist and are stress-tested
  - initial priority split exists with analytical rationale
  - chosen structure rationale exists with alternatives comparison
  - Section 3.2 Reasoning Evidence is populated
  - structure stress-test has been applied
  - stakeholder analysis exists (key stakeholders with profiles and adoption chain)
  - key business scenarios have scenario-level analysis (at least 3)
  - primary persona exists with behavioral goals and context scenario
  - design requirements extracted from personas/scenarios
  - Stage-02b-consumable or Stage-03-consumable handoff exists
- handoff_to:
  - `requirements-specification-deepening` (Stage-02b) or `requirements-decomposition-and-mvp-slicing` (Stage-03)
- handoff_package:
  - structured requirements analysis note
  - structure artifact
  - key constraints list
  - initial priority split
  - structure rationale
  - high-risk validation point
  - stakeholder list + key stakeholder profiles
  - key business scenario analysis
  - persona set with context/key-path scenarios
  - design requirements
  - assumptions / open questions
- downstream_usage_rule:
  - downstream may consume provisional content only as explicitly marked review-bound analysis input

## 7. Referenced Assets
- referenced_cards:
- referenced_inputs:

## 8. Core Business Deliverables Coverage
- checklist_reference:
  - `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`
- core_deliverables_covered:
  - requirements panorama
  - main flow / backbone activities
  - requirements structure / story map
  - key constraints
  - initial priority split
  - chosen structure rationale
  - high-risk validation point
  - stakeholder analysis (list + profiles + adoption chain)
  - key business scenario analysis (scenario-challenge-solution)
  - persona set (primary + secondary with goals and scenarios)
  - design requirements (interaction outcomes from personas/scenarios)
- core_deliverables_pending:
  - MVP definition
  - first / later / deferred slices
  - validation conclusion

## 9. PRD Main Document Section Mapping
- prd_template_reference:
  - `docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md`
- this_stage_feeds:
  - `panorama` + `backbone_flow` → PRD §8 (Requirements Structure)
  - `stakeholder_analysis` → PRD §4 (Stakeholder Analysis)
  - `key_business_scenarios` → PRD §7 (Business Scenarios)
  - `persona_scenario_set` → PRD §3 (Persona Profiles within Target Users & Key Roles)
  - `value_loop` → PRD §6 (Product Direction Overview)
  - `key_constraints` + `priority_split` → PRD §8 (Requirements Structure)
  - `explicit_exclusions` → PRD §15 (Out of Scope)
  - key-path scenarios → PRD §14 (User Stories, Use Cases, and Requirements)
  - Section 3.2 `structure_alternatives` + `why_this_structure_not_that` → PRD §17 (Key Decision Rationale Summary)
  - Section 3.2 `stakeholder_analysis_evidence` → PRD §4 (Stakeholder Analysis)
  - Section 3.2 `business_scenario_analysis_evidence` → PRD §7 (Business Scenarios)
