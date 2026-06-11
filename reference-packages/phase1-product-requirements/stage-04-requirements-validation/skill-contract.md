# Stage-04 Skill Contract — requirements-validation-and-concept-proof

## 1. Skill Goal
- This skill validates key assumptions, key decisions, and key MVP/slice choices, then feeds the results back into the earlier product/requirements stages.
- It does **not** claim complete market truth or perform high-fidelity design delivery.

## 2. Inputs
- Required inputs:
  - Stage-03 MVP definition
  - Stage-03 slice explanation
  - key assumptions to validate
  - key risks / decision points
- Optional inputs:
  - low-fidelity prototype direction
  - explicit review-bound uncertainty carried from Stage-03
- Missing-input handling:
  - refuse or do not start if there is no explicit validation target

## 2.1 Intake and State Rules
- Default intake mode:
  - hypothesis-first validation
- Allowed modes:
  - Guided
  - Context dump
  - Best guess (only if explicit review-bound assumptions are preserved)
- `cannot_infer` fields:
  - confirmed validation conclusion when no real evidence path exists
  - confirmed decision state where the hypothesis/result chain was never explicit
  - confirmed revision priority if feedback/evidence is too weak
- `can_provisionally_infer` fields:
  - first-pass validation method
  - low-cost prototype direction
  - draft decision hypothesis
- `must_validate_before_exit` fields:
  - confidence that the chosen method actually tests the key assumption
  - confidence that the signal/threshold is meaningful
  - confidence that the revision recommendation matches the evidence
- Provisional inference entry condition:
  - only when the team explicitly accepts a provisional validation design built on still-review-bound assumptions
- User review checkpoint:
  - any provisional validation design or conclusion must be reviewable before design/architecture handoff
- Final gate-pass condition:
  - a validation target exists, a validation record exists, a conclusion exists, and a revision path is explicit

## 3. Execution Steps
1. Identify the exact assumption / risk / decision that must be validated.
2. Choose a low-cost validation method.
3. Produce a prototype or equivalent validation artifact if needed.
4. Record feedback / signals / observations.
5. Derive an explicit Go / No-Go / Revise decision and revision recommendation.

## 4. Outputs
- validation record
- prototype or equivalent validation artifact (when needed)
- validation conclusion
- revision recommendations

## 4.1 Output Status and Provenance Rules
- Provisional output allowed:
  - yes, but only with explicit review-bound semantics
- Output status values:
  - `draft | provisional | review | approved`
- Required provenance labels:
  - `source: user | inferred | external | mixed`
- Required confidence / verification labels:
  - yes

## 5. Output Template
- Template path:
  - `output-template.md`
- Required fields:
  - hypothesis / validation target
  - validation method
  - feedback / signal / observation
  - decision result
  - revision recommendations
- Provenance / assumptions fields:
  - status
  - source
  - confidence
  - verification
  - assumptions_to_validate
  - what_changes_if_wrong
- Diagram fields:
  - `diagram_obligation`
  - `diagram_type`
  - `diagram_minimum_elements`
  - `fail_action`

## 6. Acceptance Criteria
- DoD:
  - explicit validation target exists
  - validation record exists
  - validation conclusion exists
  - revision recommendation exists
  - design/architecture handoff package exists
- Common defects:
  - collecting feedback without a clear hypothesis
  - using a prototype without knowing what it is supposed to validate
  - reporting “positive feedback” without an explicit decision state
  - giving a conclusion with no revision consequence
  - flattening review-bound uncertainty into fake certainty
- Gate-fail situations:
  - no explicit validation target
  - no explainable validation conclusion
  - no revision recommendation
  - no design/architecture-consumable handoff
- When provisional content cannot continue downstream:
  - if the conclusion depends on unresolved `cannot_infer` fields that were never confirmed or explicitly review-bound

## 7. Boundaries
- This skill does not:
  - deliver high-fidelity design
  - finalize architecture
  - claim proven market fit beyond the evidence actually gathered
- It should hand off to:
  - design / architecture

## 8. Flow Rules
- Upstream sources:
  - Stage-03 MVP/slicing outputs
- Downstream target:
  - design / architecture
- Fields that must be explicit before downstream:
  - validation target
  - method and evidence summary
  - decision state
  - revision recommendation
  - unresolved risk if any remains
  - NFR state: `present | absent | unknown | deferred`
- Whether provisional content may enter downstream:
  - yes, but only as explicitly labeled review-bound validation output
- Required marking when provisional content is handed off:
  - preserve `status / source / confidence / verification`
  - preserve `AI-INFERRED DRAFT — UNVERIFIED` where applicable
  - preserve assumptions_to_validate
  - preserve the explicit NFR state declaration instead of leaving it implicit
