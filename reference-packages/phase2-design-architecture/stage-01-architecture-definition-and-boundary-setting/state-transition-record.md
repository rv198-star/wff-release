# Stage-01 State Transition Record — architecture-definition-and-boundary-setting

## 1. Transition Table

| From | Trigger | To | Why | Allowed Next |
|---|---|---|---|---|
| `S0 Intake Received` | usable Phase-1 handoff exists | `S1 Clarification Active` | boundary and constraint shaping can start | `S3 Provisional Inference`, `S5 Gate Pass`, `S2 Blocked` |
| `S1 Clarification Active` | quality / NFR inputs remain partial but architecture work can continue | `S3 Provisional Inference` | must preserve review-bound uncertainty | `S4 User Review`, `S2 Blocked` |
| `S1 Clarification Active` | no defensible architecture-entry basis | `S2 Blocked` | cannot infer boundary safely | `S1 Clarification Active` |
| `S3 Provisional Inference` | provisional boundary / capability / direction package produced | `S4 User Review` | inferred content must be reviewed | `S5 Gate Pass`, `S2 Blocked` |
| `S4 User Review` | review accepts boundary package with explicit unresolved items | `S5 Gate Pass` | Stage-02 can consume package safely | Stage-02 handoff |
| `S4 User Review` | review finds unresolved fatal gap | `S2 Blocked` | package not safe for downstream | `S1 Clarification Active` |

## 2. Minimum Missing-Field Conditions
- no upstream handoff package -> blocked
- no boundary basis -> blocked
- hidden NFR uncertainty -> not eligible for clean gate pass
