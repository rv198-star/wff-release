# Stage-02 SOP — evidence-execution-and-defect-identification

## 1. Stage Positioning
- Stage name:
  - `evidence-execution-and-defect-identification`
- Stage goal:
  - execute the bounded validation work under inherited Stage-01 controls and produce evidence, defect visibility, and unresolved-risk visibility for Stage-03
- Parent phase:
  - validation / closure
- Upstream dependency:
  - Stage-01 validation planning package
- Downstream target:
  - `validation-closure-and-delivery-readiness-judgment`

## 2. Start Conditions
- Required inputs:
  - Stage-01 output package or equivalent `TEST-STG01-OUTPUT-*`
  - acceptance checklist linkage
  - execution-control linkage
  - Stage-02 may-start declaration
- Refusal rule:
  - refuse or do not start if Stage-01 may-start is `no` and no explicit override exists

## 3. Standard Execution Steps
1. Validate Stage-01 inherited scope and may-start conditions.
2. Execute bounded validation scenarios.
3. Capture pass/fail/blocked outcomes with evidence paths.
4. Record defects and unresolved risks explicitly.
5. For a current requested frontend with passing P3 browser evidence, package the exact application/page identity, bound consumer journeys, terminal-persona coverage, business-data/clean-first-use contract, project locale, screenshots, and traces into two isolated review requests. Run **Round 1 OMR** first from `open-ended-maturity-review-request.json`: no fixed dimension checklist, no SQR score/findings, findings before holistic score, PASS only at score >= 80 with no `critical`/`high` finding. Then run **Round 2 SQR** from `ui-product-review-request.json`: fixed dimensions include productness, first-entry/navigation/task continuity, terminal-role fidelity/least privilege, business-data sufficiency, Interaction Affordance & Task Efficiency, project-language alignment, clean first use/context recovery, trust/history/provenance, Metadata Leakage, page composition/hierarchy, business language, state/action clarity, desktop/mobile usability, and accessibility baseline. Do not feed OMR findings/results into SQR. Finally run **RSG**: both reviews must independently PASS and their scores are never averaged. Do not let screenshot existence, structural checks, keyword rules, a super-role account, fixture IDs, or one review's score substitute for the bound consumer journeys or the other review. Require factual desktop/mobile document-level viewport-fit evidence with no horizontal overflow; screenshot presence alone is not sufficient. If factual evidence is insufficient, keep the relevant review review-bound instead of inferring a pass. After OMR validation, emit `open-ended-maturity-learning-candidates.json` by retaining the reviewer-provided finding facts only; do not generalize, score patterns, affect the current verdict, or mutate SQR. Repeated OMR patterns may later be promoted into SQR only as stable cross-case/version business-independent regression knowledge through an explicit later Agentic/governance decision; OMR remains a permanent discovery layer.
6. Assemble the execution evidence package for Stage-03.

## 4. Process Checkpoints
- Checkpoint 1:
  - Stage-01 inherited controls are explicit
- Checkpoint 2:
  - execution outcomes are explicit
- Checkpoint 3:
  - evidence paths exist
- Checkpoint 4:
  - defects / blocked items / unresolved risks are explicit
- Checkpoint 5:
  - current requested frontend OMR is current-bound, dimension-free, and independently resolved before synthesis
- Checkpoint 5a:
  - validated OMR findings are retained as non-authoritative learning candidates without changing the current review or automatically extending SQR
- Checkpoint 6:
  - current requested frontend SQR is current-bound, dimension-scored, and independent of OMR findings/results
- Checkpoint 7:
  - RSG records PASS only when OMR AND SQR pass; otherwise it preserves the blocking/review-bound return path without score averaging
- Checkpoint 8:
  - Stage-03 handoff package is explicit

## 5. Handoff Rules
- Handoff target:
  - `validation-closure-and-delivery-readiness-judgment`
- Handoff package:
  - execution evidence package
  - execution log linkage
  - defect record linkage
  - evidence pointer list
  - unresolved-risk log
