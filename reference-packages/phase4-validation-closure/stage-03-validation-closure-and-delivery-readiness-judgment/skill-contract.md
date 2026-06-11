# Stage-03 Skill Contract — validation-closure-and-delivery-readiness-judgment

## 1. Skill Goal
- This skill reviews Stage-02 execution evidence and converts it into a closure judgment that downstream consumers can rely on without guessing what was tested, what remains unresolved, or what the judgment boundary actually means.
- It does **not** approve final release readiness, hide unresolved defects, or replace optional Stage-04 release-readiness decision-making.

## 2. Inputs
- Required inputs:
  - Stage-02 execution evidence package (`TEST-STG02-OUTPUT-*`)
  - evidence summary
  - defect / blocked / unresolved-risk visibility
  - Stage-01 entry/exit gate references
- Optional inputs:
  - additional reviewer notes
  - explicitly approved residual-risk acceptance context
- Missing-input handling:
  - refuse or remain blocked if Stage-02 outputs are absent or non-usable
  - refuse to close when gate evidence is missing and no explicit waiver/review-bound logic exists
  - preserve unresolved items explicitly instead of compressing them into a false pass judgment

## 2.1 Intake and State Rules
- Default intake mode:
  - closure judgment under explicit gate and evidence discipline
- Allowed modes:
  - Guided
  - Context dump
  - Best guess (only for non-critical summarization and only when review-bound marking remains explicit)
- `cannot_infer` fields:
  - pass judgment when required evidence is absent
  - absence of critical defects when execution did not cover the relevant risk area
  - optional Stage-04 release-readiness approval
- `can_provisionally_infer` fields:
  - review-bound residual-risk wording
  - lightweight closure summary phrasing
- `must_validate_before_exit` fields:
  - entry/exit gate review result
  - unresolved defects and residual risks
  - final closure judgment rationale
  - explicit downstream note that optional Stage-04 approval remains outside this stage

## 3. Execution Steps
1. Validate the Stage-02 evidence package and inherited gate references.
2. Review gate fulfillment, unresolved defects, blocked scenarios, and residual risks.
3. Produce a validation closure judgment.
4. Record what downstream consumers may rely on and what remains review-bound.
5. Assemble the Stage-03 closure package for downstream handoff.

## 4. Outputs
- `TEST-STG03-OUTPUT-*` closure judgment package
- closure checklist / gate review result
- test conclusion summary
- residual-risk / risk-acceptance note
- downstream reliance boundary note

## 5. Output Template
- Template path:
  - `output-template.md`
- Required fields:
  - closure judgment summary
  - gate review result
  - unresolved defect / risk summary
  - downstream reliance boundary
  - handoff decision

## 6. Acceptance Criteria
- DoD:
  - closure judgment exists
  - gate review result exists
  - unresolved defect/risk visibility exists
  - downstream reliance boundary exists
  - no optional Stage-04 release-approval language is smuggled into the output
- Common defects:
  - closure judgment with no evidence basis
  - hidden unresolved defects
  - optional Stage-04 release-approval language in a Stage-03 artifact
  - narrative-only closure reasoning with no explicit verdict

## 7. Boundaries
- This skill does not:
  - approve final release readiness
  - rewrite Stage-02 evidence
  - silently waive critical unresolved items
- It should hand off to:
  - optional Phase-4 Stage-04 release-readiness extension or equivalent downstream consumer
