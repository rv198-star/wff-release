# Stage-02 Skill Contract — evidence-execution-and-defect-identification

## 1. Skill Goal
- This skill executes bounded validation work based on Stage-01 outputs and produces reviewable execution evidence for Stage-03 closure judgment.
- It does **not** reopen Stage-01 planning policy, silently rewrite scope, or perform final release-readiness approval.

## 2. Inputs
- Required inputs:
  - Stage-01 validation planning package (`TEST-STG01-OUTPUT-*`)
  - acceptance checklist reference
  - coverage explanation reference
  - test entry/exit gate checklist reference
  - test execution-control reference
  - Stage-02 may-start declaration from Stage-01
- Optional inputs:
  - additional execution clarifications from maintainers
  - explicitly approved waivers
  - operator-facing install/run guidance
- Missing-input handling:
  - refuse or remain blocked if Stage-01 outputs are absent or non-usable
  - refuse to start when Stage-02 may-start decision is `no` and no approved override exists
  - preserve unresolved execution constraints explicitly instead of masking them with optimistic assumptions

## 2.1 Intake and State Rules
- Default intake mode:
  - bounded execution under inherited validation controls
- Allowed modes:
  - Guided
  - Context dump
  - Best guess (only for non-critical execution sequencing and only when review-bound marking remains explicit)
- `cannot_infer` fields:
  - gate pass when required execution evidence is missing
  - defect absence when execution did not actually cover the relevant scenario
  - closure-worthy pass judgment
- `can_provisionally_infer` fields:
  - execution grouping under known constraints
  - low-risk ordering decisions that do not alter acceptance scope
- `must_validate_before_exit` fields:
  - execution results for planned scenarios
  - evidence paths for meaningful outcomes
  - explicit defect / blocked / risk logging
  - explicit trace links from execution to acceptance items where applicable

## 3. Execution Steps
1. Validate Stage-01 may-start conditions and inherited execution controls.
2. Execute bounded validation work for the declared in-scope scenarios.
3. Produce execution evidence and capture pass/fail/blocked outcomes.
4. Record defect, blocked, and unresolved-risk information explicitly.
5. Assemble the Stage-02 execution evidence package for Stage-03 closure judgment.

## 4. Outputs
- `TEST-STG02-OUTPUT-*` execution evidence package
- execution result summary
- execution log / UAT run record linkage
- defect record linkage
- evidence pointer list
- explicit blocked / unresolved-risk log
- Stage-03 handoff summary

## 5. Output Template
- Template path:
  - `output-template.md`
- Required fields:
  - execution scope completion summary
  - execution result summary
  - evidence summary
  - defect / blocked / unresolved-risk log
  - Stage-03 handoff summary

## 6. Acceptance Criteria
- DoD:
  - planned execution scope is completed or explicitly returned as partial/blocked
  - evidence exists for meaningful results
  - defect visibility is explicit
  - unresolved execution conditions are logged
  - Stage-03 handoff package is closure-consumable
- Common defects:
  - claiming completion with no evidence paths
  - hiding blocked items inside narrative summaries
  - defect language with no structured record shape
  - silent scope drift from Stage-01

## 7. Boundaries
- This skill does not:
  - redesign Stage-01 planning policy
  - finalize Stage-03 closure decisions
  - perform final release-readiness approval
- It should hand off to:
  - `validation-closure-and-delivery-readiness-judgment`
