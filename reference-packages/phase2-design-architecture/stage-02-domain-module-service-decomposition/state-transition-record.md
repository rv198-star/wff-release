# Stage-02 State Transition Record — domain-module-service-decomposition

## 1. Transition Table

| From | Trigger | To | Why | Allowed Next |
|---|---|---|---|---|
| `S0 Intake Received` | usable Stage-01 package exists | `S1 Clarification Active` | decomposition basis is available | `S3 Provisional Inference`, `S2 Blocked` |
| `S1 Clarification Active` | brownfield naming conflict remains but ownership can be made explicit | `S3 Provisional Inference` | draft decomposition may continue as review-bound | `S4 User Review`, `S2 Blocked` |
| `S1 Clarification Active` | hidden ownership overlap or ownerless lifecycle closure appears | `S2 Blocked` | decomposition is not safe for Stage-03 | `S1 Clarification Active` |
| `S3 Provisional Inference` | draft domain/module/service package assembled | `S4 User Review` | review must confirm non-overlap and handoff usability | `S5 Gate Pass`, `S2 Blocked`, `S1 Clarification Active` |
| `S4 User Review` | review confirms ownership closure and name mapping | `S5 Gate Pass` | Stage-03 may consume package safely | Stage-03 handoff |
| `S4 User Review` | review finds hidden overlap, ownerless closure, or unresolved brownfield contradiction | `S1 Clarification Active` | package must be repaired before pass | `S3 Provisional Inference`, `S2 Blocked` |

## 2. Minimum Missing-Field Conditions
- no Stage-01 package -> blocked
- no defensible ownership boundary -> blocked
- no explanation for brownfield naming / ownership conflict -> not eligible for clean gate pass
