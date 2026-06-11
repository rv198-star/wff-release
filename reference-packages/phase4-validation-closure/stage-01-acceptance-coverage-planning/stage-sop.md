# Stage-01 SOP — acceptance-coverage-planning

## 1. Stage Positioning
- Stage name:
  - `acceptance-coverage-planning`
- Stage goal:
  - turn the upstream implementation handoff into a Stage-01 validation package by freezing acceptance mapping, coverage rationale, gate posture, execution-control posture, and Stage-02 start conditions
- Parent phase:
  - validation / closure
- Upstream dependency:
  - Phase-3 implementation handoff package
- Downstream target:
  - `evidence-execution-and-defect-identification`

## 2. Start Conditions
- Required inputs:
  - implementation handoff package or equivalent `IMPL-STG03-HANDOFF-*`
  - requirement / contract anchors sufficient for first-pass acceptance mapping
  - enough source basis to define gate and execution-control posture
- Optional inputs:
  - explicit risk priorities
  - environment-specific constraints
  - upstream review-bound notes
- Refusal rule:
  - refuse or do not start if no usable implementation handoff exists

## 3. Standard Execution Steps
1. Inspect the implementation handoff and register explicit input states.
2. Freeze acceptance scope and acceptance mapping.
3. Freeze coverage rationale and exclusions.
4. Freeze entry/exit gate posture and execution-control posture.
5. Assemble the validation planning package and declare whether Stage-02 may start.

## 4. Process Checkpoints
- Checkpoint 1:
  - implementation handoff dependency is explicit
- Checkpoint 2:
  - acceptance mapping is explicit and traceable
- Checkpoint 3:
  - coverage rationale exists
- Checkpoint 4:
  - gate and execution-control linkage exists
- Checkpoint 5:
  - Stage-02 may-start decision is explicit

## 5. Output Generation Rules
- Required outputs:
  - validation planning package
  - linked acceptance checklist
  - linked coverage explanation
  - linked gate checklist
  - linked execution-control artifact
- Minimum output rule:
  - Stage-02 must be able to start or remain blocked without reconstructing Stage-01 logic from scratch

## 6. Stage Acceptance
- Minimum completion standard:
  - handoff dependency exists
  - acceptance mapping exists
  - coverage rationale exists
  - gate and execution-control linkage exists
  - Stage-02 may-start declaration exists
- Common failure signals:
  - generic testing plan with no traceability
  - narrative-only gate posture
  - no explicit start/blocked decision for Stage-02

## 7. Handoff Rules
- Handoff target:
  - `evidence-execution-and-defect-identification`
- Handoff package:
  - validation planning package
  - acceptance checklist linkage
  - coverage rationale linkage
  - gate linkage
  - execution-control linkage
  - Stage-02 may-start declaration
