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
5. For current requested-frontend P3 browser evidence, run a two-round independent AI Review before subjective `ui-review` may pass. **Round 1 OMR** emits `open-ended-maturity-review-request.json` first, exposes no fixed scoring dimensions and no SQR score/findings, requires concrete evidence-backed findings before one holistic maturity score, and passes only at score >= 80 with no `critical`/`high` finding. **Round 2 SQR** emits `ui-product-review-request.json` with fixed qualification dimensions including Interaction Affordance & Task Efficiency; the structured reviewer must not receive OMR findings/results. **RSG** synthesizes only the two independent verdicts and never averages scores: OMR PASS AND SQR PASS are both required. Browser/screenshot evidence proves observation only, and a bound first-entry-to-meaningful-outcome consumer journey is a prerequisite rather than something an AI score may substitute for. Factual admission requires independent terminal-persona evidence when roles exist, forbids super-role substitution and manual internal-ID qualification, and requires clean-first-use evidence when the current UI contract says it is required. Workflow validates current evidence binding and response completeness only; factual accessibility/browser evidence must include document-level desktop/mobile viewport-fit proof with no horizontal overflow, because screenshot presence alone does not prove viewport fit. When that or other factual evidence is insufficient, the relevant review remains review-bound instead of inferring a pass. After validating OMR, Workflow retains the reviewer-provided findings verbatim enough for later comparison in `open-ended-maturity-learning-candidates.json`; the learning record is non-authoritative, does not affect the current OMR/SQR/RSG result, does not generalize categories, and cannot add an SQR dimension automatically. Repeated OMR finding patterns may be generalized into later SQR dimensions/checks only when they are stable, cross-case/version, business-independent regression knowledge and an explicit later Agentic/governance decision accepts the promotion; OMR remains mandatory after such promotion.
6. Assemble the Stage-02 execution evidence package for Stage-03 closure judgment.

## 4. Outputs
- `TEST-STG02-OUTPUT-*` execution evidence package
- current `open-ended-maturity-review-request.json` plus Open-ended Maturity Review findings/holistic score when requested frontend browser evidence exists
- `open-ended-maturity-learning-candidates.json`, retaining validated OMR findings as non-authoritative later-learning candidates without changing the current review
- current `ui-product-review-request.json` plus Structured Qualification Review assessments/findings
- `review-synthesis-gate.json` recording the non-averaged OMR + SQR synthesis verdict
- Review Synthesis Gate status; no combined/averaged AI score
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
