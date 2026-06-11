# Stage-02b Output Template — requirements-specification-deepening

## 1. Document Metadata
- document_name:
- stage:
  - requirements-specification-deepening
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
  - deepen Stage-02a structural panorama with NFR analysis, domain model direction, and IA direction to produce specification-grade inputs for Stage-03 slicing
- assumptions:
- open_questions:

## 3. Core Structured Output

### 3.0 NFR / Quality Requirements

- nfr_quality_requirements:
  - quality_attributes_identified:
    - attribute_N:
      - attribute: (e.g., security, reliability, usability, performance, maintainability, portability)
      - relevance_to_product: (why this attribute matters for this specific product)
      - reverse_risk_assessment: (if this fails, what is the worst realistic consequence?)
      - affected_business_scenarios: (which Stage-02a scenarios are most impacted?)
      - affected_stakeholders: (which stakeholders care most?)
      - analysis_depth: `full-quality-scenario | identification-only`
  - key_quality_scenario_tables:
    - attribute_N:
      - attribute:
      - scenarios:
        - scenario_N:
          - stimulus: (what event triggers the quality concern)
          - environment: (under what conditions)
          - response: (what the system must do)
          - measure: (how we know it is met)
  - nfr_mvp_impact:
    - (which NFRs constrain what must be in the first slice?)
    - (which NFRs can be relaxed for MVP and tightened later?)

### 3.1 Module Interface Payload Contract

- module_interface_payload_contract:
  - contract_rule:
    - Stage-02b must preserve detailed structured source capability as explicit payload when the source names specific structured outputs
  - payload_elements:
    - element_N:
      - source_capability_detail:
      - first_wave_representation:
      - task_export_implication:
      - certainty_or_note:

### 3.2 Domain Model Direction

- domain_model_direction:
  - core_entities:
    - entity_N:
      - name:
      - description:
      - key_attributes: (conceptual, not column-level)
      - lifecycle_states: (if applicable)
      - data_source: `user-input | external-api | system-generated | imported`
  - key_relationships:
    - relationship_N:
      - from_entity:
      - to_entity:
      - relationship_type: `association | composition | generalization`
      - cardinality: (if architecturally significant)
      - description:
  - domain_er_diagram:
    - (Mermaid ER diagram — required)
  - key_data_characteristics:
    - data_window: (how far back must data be retained? freshness requirement?)
    - data_sources_summary: (primary data origins)
    - data_sensitivity: (privacy/compliance implications)
    - data_volume_estimates: (order-of-magnitude for key entities)

### 3.3 Deferred Capability Seam

- deferred_capability_seam:
  - seam_rule:
    - if source capability includes future measurement / external identity / source-tag / journey-stage / multi-entry needs, preserve them as explicit deferred seam rather than silent omission
  - seam_items:
    - seam_N:
      - future_concern:
      - first_wave_treatment_now:
      - future_seam_entity_or_interface:
      - minimum_reserved_fields_or_hook:
      - why_deferred_now:

### 3.4 Business Subsystem Boundaries (if applicable)

- business_subsystem_boundaries:
  - applicable: `yes | no — reason`
  - subsystems:
    - subsystem_N:
      - name:
      - description:
      - entities_owned:
      - scenarios_owned:
  - subsystem_interfaces:
    - interface_N:
      - from_subsystem:
      - to_subsystem:
      - why: (why does A need to talk to B?)
      - what: (what data/events flow across?)
      - constraints: (what rules apply to this interface?)

### 3.5 Information Architecture Direction

- information_architecture_direction:
  - organization_strategy:
    - primary_axis: (by workflow stage? entity type? user role? time?)
    - classification_approach: `exact | ambiguous | faceted | hybrid`
    - hierarchy_approach: `hierarchical | flat | hybrid`
    - rationale:
  - labeling_direction:
    - language_choice: `user-language | domain-language | hybrid`
    - key_labeling_decisions: (terminology choices that affect user mental model)
    - terminology_conflicts: (between stakeholder groups, if any)
  - navigation_strategy_direction:
    - global_navigation_needs: (what must be accessible from everywhere?)
    - local_navigation_needs: (what must be accessible within workflow context?)
    - contextual_navigation_needs: (what must be accessible based on current task?)
  - ia_architecture_impact:
    - (which IA decisions constrain architecture or MVP scope?)

## 3.6 Provenance / Confidence / Verification
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

## 3.7 Reasoning Evidence

This section is REQUIRED, not optional.

### NFR Prioritization Reasoning
- why_these_quality_attributes:
  - (what evidence supports these as the most critical quality attributes?)
- deprioritized_attributes:
  - (which quality attributes were considered but deprioritized, and why?)
- nfr_mvp_constraint_reasoning:
  - (which NFRs force capabilities into the first slice, and why they cannot be deferred?)

### Domain Model Decisions
- entity_structure_rationale:
  - (why this entity grouping? what alternative structures were considered?)
- alternative_models_considered:
  - model_N:
    - description:
    - why_rejected:
- subsystem_boundary_rationale:
  - (if applicable: why these boundaries? what would change if boundaries shifted?)
- payload_contract_rationale:
  - (if applicable: why these payload elements were preserved; what would be lost if structured source detail stayed generic?)
- deferred_capability_seam_rationale:
  - (if applicable: why the seam is preserved now even though capability is deferred)

### IA Direction Reasoning
- organization_strategy_rationale:
  - (why this organization approach? what alternatives were considered?)
- navigation_strategy_rationale:
  - (why this navigation approach? how does it align with persona workflows?)
- architecture_impact_assessment:
  - (how do IA decisions constrain or enable architecture choices?)

### Specification Stress-Test Outcome
- stage_03_blind_spots_without_spec:
  - (what would Stage-03 miss if it only had Stage-02a's structural panorama?)
- nfr_slice_constraints:
  - (do any NFRs force capabilities into or out of the first slice?)
- domain_dependency_slice_impact:
  - (do entity dependencies affect slice ordering?)
- ia_feasibility_constraints:
  - (do IA direction decisions constrain feasible user flows in first slice?)
- verdict:
  - `passed | failed | inconclusive`

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
  - judgment:
  - evidence_grade:
    - `user-confirmed | inferred | speculative`
  - rejected_alternatives:
  - what_would_change_decision:
- reasoning_notes:
  - nfr_priority_rationale:
    - (summary; detailed reasoning in Section 3.5)
  - domain_model_rationale:
    - (summary; detailed reasoning in Section 3.5)
  - ia_direction_rationale:
    - (summary; detailed reasoning in Section 3.5)
- key_specification_constraints:
- explicit_exclusions:

## 5. Diagram / Structured Representation
- requires_uml_or_mermaid:
  - yes
- diagram_types:
  - `domain-model-er` (required)
  - `business-subsystem-boundary` (optional — only if subsystem boundaries identified)
  - `information-organization-strategy` (optional)
- diagram_obligation:
  - `required` (at minimum: conceptual domain model ER diagram)
- fail_action:
  - return to Stage-02a if domain model cannot be constructed from available scenario depth

## 6. Acceptance and Flow
- minimum_acceptance:
  - at least 3 quality attributes analyzed with material impact
  - key quality attributes have quality-scenario tables
  - module interface payload contract exists when source structured detail is specific
  - conceptual domain model with ER diagram exists
  - deferred capability seam exists when such source capability is present
  - key data characteristics identified
  - IA direction documented or assessed as trivially obvious
  - specification stress-test applied
  - Section 3.7 Reasoning Evidence populated
  - Stage-03-consumable handoff exists
- handoff_to:
  - `requirements-decomposition-and-mvp-slicing` (Stage-03)
- handoff_package:
  - Stage-02a full outputs
  - NFR / quality requirements summary
  - module interface payload contract
  - conceptual domain model with ER diagram
  - deferred capability seam
  - key data characteristics
  - business subsystem boundaries (if applicable)
  - IA direction decisions
  - specification stress-test outcome
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
  - NFR / quality requirements analysis
  - module interface payload contract
  - conceptual domain model
  - deferred capability seam
  - key data characteristics
  - business subsystem boundaries (if applicable)
  - information architecture direction
  - specification stress-test
- core_deliverables_pending:
  - MVP definition
  - first / later / deferred slices
  - validation conclusion

## 9. PRD Main Document Section Mapping
- prd_template_reference:
  - `docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md`
- this_stage_feeds:
  - `nfr_quality_requirements` + quality-scenario tables → PRD §9 (NFR / Quality Requirements)
  - `domain_model_direction` + ER diagram + data characteristics → PRD §10 (Domain Model)
  - `business_subsystem_boundaries` + interface definitions → PRD §10 (Domain Model — subsystem section)
  - `information_architecture_direction` → PRD §11 (Information Architecture Direction)
  - `nfr_mvp_impact` → PRD §12 (MVP Definition & Scope — NFR-aware slicing impact)
  - Section 3.5 `nfr_prioritization_reasoning` → PRD §17 (Key Decision Rationale Summary)
  - Section 3.5 `domain_model_decisions` → PRD §17 (Key Decision Rationale Summary)
  - Section 3.5 `ia_direction_reasoning` → PRD §17 (Key Decision Rationale Summary)
  - NFR state declaration → PRD §18 (Handoff to Design / Architecture)
