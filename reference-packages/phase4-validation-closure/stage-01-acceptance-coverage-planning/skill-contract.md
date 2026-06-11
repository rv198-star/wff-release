# Stage-01 Skill Contract — acceptance-coverage-planning

## 1. Skill Goal
- This skill converts the upstream implementation handoff into a controlled validation planning package that Stage-02 can consume without guessing acceptance scope, coverage posture, gate semantics, or execution-control structure.
- It does **not** execute tests, close the testing phase, or replace downstream evidence collection and closure judgment.

## 2. Inputs
- Required inputs:
  - Phase-3 implementation handoff package or equivalent `IMPL-STG03-HANDOFF-*`
  - requirement / contract references that support acceptance mapping
  - enough source basis to define coarse acceptance, coverage, and gate posture
- Optional inputs:
  - human-provided risk priorities
  - environment limitations or acceptance-specific constraints
  - explicitly inherited review-bound items from upstream
- Missing-input handling:
  - refuse or remain blocked if no usable implementation handoff exists
  - refuse to pass if acceptance claims cannot be tied back to requirements/contracts
  - preserve unresolved inputs explicitly instead of hiding them behind optimistic planning language

## 2.1 Intake and State Rules
- Default intake mode:
  - control-first testing-validation framing
- Allowed modes:
  - Guided
  - Context dump
  - Best guess (only when review-bound assumptions remain explicit)
- `cannot_infer` fields:
  - honest acceptance claims when requirement / contract anchors are missing
  - executable entry/exit gate posture when no evidence basis exists
  - Stage-02 may-start decision when environment readiness is too unclear
- `can_provisionally_infer` fields:
  - first-pass scope prioritization
  - provisional coverage depth selection
  - provisional execution grouping where full scenario detail is absent
- `must_validate_before_exit` fields:
  - acceptance mapping `TEST-* -> API-* -> REQ-*`
  - entry/exit gate posture
  - Stage-02 may-start declaration
  - explicit blocked / review-bound handling for missing environment basis
- Final gate-pass condition:
  - Stage-01 output package exists, acceptance/coverage/gate/execution artifacts are linked, traceability hooks are explicit, and Stage-02 can tell whether it may start or must remain blocked

## 3. Execution Steps
1. Inspect the implementation handoff and register the state of required inputs, constraints, and unresolved items.
2. Freeze acceptance scope and map acceptance items to requirements/contracts where applicable.
3. Define coverage rationale, priority posture, and explicit exclusions.
4. Freeze entry/exit gate semantics and execution-control posture for Stage-02.
5. Produce the validation planning package and explicit Stage-02 may-start declaration.

## 4. Outputs
- validation planning package
- acceptance checklist / catalog linkage
- coverage explanation linkage
- test entry/exit gate checklist linkage
- test execution-control linkage
- Stage-02 may-start declaration

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
  - implementation handoff summary
  - decision mode and Stage-01 posture
  - acceptance mapping linkage
  - coverage rationale linkage
  - gate and execution-control linkage
  - traceability hooks
  - Stage-02 may-start declaration

## 6. Acceptance Criteria
- DoD:
  - implementation handoff dependency is explicit
  - acceptance mapping is explicit
  - coverage rationale is explicit
  - gate semantics are explicit
  - execution-control linkage exists
  - Stage-02 may-start declaration exists
- Common defects:
  - generic testing advice with no acceptance mapping
  - narrative-only gate language
  - no explicit execution-control posture
  - silent scope expansion beyond upstream handoff
  - no blocked/remediation posture for missing environment prerequisites

## 7. Boundaries
- This skill does not:
  - execute test cases
  - produce defect records
  - close the validation-closure phase
  - make final release-readiness decisions
- It should hand off to:
  - `evidence-execution-and-defect-identification`

## 8. Flow Rules
- Upstream sources:
  - Phase-3 implementation handoff package
  - Stage-01 control-layer artifacts and source register
- Downstream target:
  - `evidence-execution-and-defect-identification`
- Fields that must be explicit before downstream:
  - acceptance scope and mapping
  - coverage rationale
  - gate posture
  - execution-control posture
  - Stage-02 may-start decision
