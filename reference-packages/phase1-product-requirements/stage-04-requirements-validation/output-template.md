# Stage-04 Output Template — requirements-validation-and-concept-proof

## 1. Document Metadata
- document_name:
- stage:
  - requirements-validation-and-concept-proof
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
- current_validation_target:
- validation_objective:
- assumptions:
- open_questions:

## 3. Core Structured Output
- hypothesis_or_validation_target:
- validation_method:
- prototype_or_equivalent_artifact:
- feedback_or_signal:
- validation_conclusion:
- decision_state:
  - `Go | No-Go | Revise`
- revision_recommendations:

- validation_dimensions_covered:
  - value_dimension:
    - verdict: `validated | partially-validated | not-validated | not-tested`
    - evidence_summary: (what evidence supports this verdict)
  - usability_dimension:
    - verdict: `validated | partially-validated | not-validated | not-tested`
    - evidence_summary:
  - feasibility_dimension:
    - verdict: `validated | partially-validated | not-validated | not-tested`
    - evidence_summary:
  - dimensions_gap_note:
    - (for any dimension marked not-tested: what downstream must be aware of)

- prototype_fidelity_record:
  - fidelity_chosen: `paper-sketch | clickable | coded | none`
  - fidelity_rationale: (why this fidelity level was chosen for the validation target)

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

### Validation Target Clarity
- exact_assumption_tested:
  - (what specific assumption/risk/decision is being validated — not a vague area)
- what_changes_if_positive:
  - (concrete consequence of validation success)
- what_changes_if_negative:
  - (concrete consequence of validation failure)

### Method-Fit Comparison
- methods_considered:
  - method_1:
    - name:
    - fit_to_target:
    - cost_and_speed:
    - evidence_quality:
  - method_2:
    - name:
    - fit_to_target:
    - cost_and_speed:
    - evidence_quality:
- chosen_method:
- why_this_method_not_that:

### Evidence State Honesty
- what_is_design_time_inference:
  - (conclusions derived from analysis only, not real evidence)
- what_is_real_evidence:
  - (conclusions backed by actual signals/feedback/data)
- what_remains_unknown:
  - (gaps that neither inference nor evidence can fill)

### Delivery Readiness and Evidence Confidence
- document_delivery_state:
  - `artifact-draft | review-ready | downstream-start-safe | implementation-commit-ready | blocked`
- evidence_confidence_state:
  - `design-time-inference-heavy | source-grounded-but-unvalidated | partially-signal-backed | externally-validated | contradicted`
- safe_start_scope:
  - (what design / architecture / next-step work may begin now)
- blocked_commitments:
  - (what implementation, pricing, rollout, or certainty claims remain unsafe)
- maturity_confidence_ledger:
  - item_1:
    - subject:
    - delivery_readiness_state:
    - evidence_confidence_state:
    - current_basis:
    - blocker_to_next_delivery_state:
    - blocker_to_next_evidence_state:
    - safe_downstream_action:
    - forbidden_assumptions:

### Decision State Reasoning
- decision:
  - `Go | No-Go | Revise`
- why_this_decision:
  - (explicit rationale linking evidence state to decision)
- what_downstream_must_not_assume:
  - (forbidden assumptions for Phase-2 / design)

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
- key_judgments:
- reasoning_notes:
  - chosen_method_rationale:
  - evidence_state_interpretation:
  - decision_state_rationale:
  - revision_consequence_rationale:
- key_constraints:
- explicit_exclusions:

## 5. Diagram / Structured Representation
- requires_uml_or_mermaid:
  - optional but recommended when it clarifies the validation chain
- diagram_type:
  - `validation-flow | table-only`
- diagram_obligation:
  - `recommended`
- diagram_minimum_elements:
  - hypothesis
  - method
  - threshold/signal
  - result
  - decision
- fail_action:
  - return to target/method clarification if the validation chain is not explicit

## 6. Acceptance and Flow
- minimum_acceptance:
  - validation target exists
  - validation record exists
  - decision state exists
  - revision recommendation exists
  - validation rationale exists
  - design/architecture-consumable handoff exists
  - Unified Product Pack convergence readiness/state is explicit
- handoff_to:
  - design / architecture
- handoff_nfr_state:
  - `present | absent | unknown | deferred`
- handoff_nfr_notes:
- stage_02b_execution_state:
  - `executed | skipped | partial`
- stage_02b_skip_declaration: (required if stage_02b_execution_state is `skipped` or `partial`)
  - nfr_source: `02a-scan-only | 02b-full | 02b-partial | none`
  - domain_model_state: `not-produced | partial-from-02a | produced-in-02b`
  - ia_direction_state: `not-produced | partial-from-02a | produced-in-02b`
  - impact_on_phase2: (what architecture work is affected)
  - minimum_viable_for_phase2: `yes | no`
  - mitigation_note: (what Phase-2 should do to compensate)
- document_delivery_state:
  - `artifact-draft | review-ready | downstream-start-safe | implementation-commit-ready | blocked`
- evidence_confidence_state:
  - `design-time-inference-heavy | source-grounded-but-unvalidated | partially-signal-backed | externally-validated | contradicted`
- safe_start_scope:
- blocked_commitments:
- unified_product_pack_status:
  - `not-started | ready-to-converge | converged-post-stage`
- unified_product_pack_reference:
- handoff_package:
  - validation conclusion
  - validation record
  - prototype/equivalent artifact if used
  - validation rationale
  - revision recommendation
  - unresolved risks if any remain
  - explicit NFR state declaration
  - unified product pack reference if already assembled post-Stage-04
- downstream_usage_rule:
  - downstream may consume provisional content only as explicitly marked review-bound validation input
  - downstream must not infer that NFRs are complete merely from generic `key_constraints`

## 7. Referenced Assets
- referenced_cards:
- referenced_inputs:

## 8. Core Business Deliverables Coverage
- checklist_reference:
  - `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`
- core_deliverables_covered:
  - validation target / hypothesis
  - validation method
  - prototype or equivalent validation artifact
  - feedback / signal / result
  - validation conclusion
  - decision state
  - validation rationale
  - revision recommendations
  - design / architecture handoff package
  - Unified Product Pack convergence readiness/state
- core_deliverables_pending:
  - none within Phase-1 scope

## 9. PRD Main Document Section Mapping
- prd_template_reference:
  - `docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md`
- this_stage_feeds:
  - `hypothesis_or_validation_target` → PRD §13 (Validation Strategy & Current Conclusion)
  - `validation_method` → PRD §13 (Validation Strategy & Current Conclusion)
  - `validation_conclusion` + `decision_state` → PRD §13 (Validation Strategy & Current Conclusion)
  - `validation_dimensions_covered` → PRD §13 (Validation Strategy & Current Conclusion — three-dimensional assessment)
  - `prototype_fidelity_record` → PRD §13 (Validation Strategy & Current Conclusion)
  - `revision_recommendations` → PRD §13 (Validation Strategy & Current Conclusion)
  - `handoff_package` → PRD §18 (Handoff to Design / Architecture)
  - Section 3.2 `method_fit_comparison` + `why_this_method_not_that` → PRD §17 (Key Decision Rationale Summary)
  - Section 3.2 `evidence_state_honesty` → PRD §13 (Validation Strategy & Current Conclusion — evidence state)
  - Section 3.2 `decision_state_reasoning` + `what_downstream_must_not_assume` → PRD §16 (Dependencies, Risks), PRD §18 (Handoff)
  - `unified_product_pack_status` → PRD §19 (Acceptance & Status)
