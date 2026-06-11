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
5. Assemble the execution evidence package for Stage-03.

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
