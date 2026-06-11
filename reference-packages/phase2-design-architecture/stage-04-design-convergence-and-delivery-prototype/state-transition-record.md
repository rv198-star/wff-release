# Stage-04 State Transition Record — design-convergence-and-delivery-prototype

## 1. Transition Table

| From | Trigger | To | Why | Allowed Next |
|---|---|---|---|---|
| `S0 Intake Received` | Stage-01~03 package set is present | `S1 Clarification Active` | convergence review can start | `S3 Provisional Inference`, `S2 Blocked` |
| `S1 Clarification Active` | prior-stage truth is mostly convergent but some readiness remains review-bound | `S3 Provisional Inference` | handoff may continue with calibrated wording | `S4 User Review`, `S2 Blocked` |
| `S1 Clarification Active` | prior-stage contradictions or unrealized dependencies would invalidate the readiness label | `S2 Blocked` | Stage-04 must not hide structural gaps | `S1 Clarification Active` |
| `S3 Provisional Inference` | convergence package assembled | `S4 User Review` | review must confirm readiness calibration and downstream usage rules | `S5 Gate Pass`, `S2 Blocked`, `S1 Clarification Active` |
| `S4 User Review` | review accepts admission wording and downstream assumption limits | `S5 Gate Pass` | implementation-facing handoff is safe | downstream implementation intake |
| `S4 User Review` | review finds overstated readiness or suppressed contradictions | `S1 Clarification Active` | package must be repaired before pass | `S3 Provisional Inference`, `S2 Blocked` |

## 2. Minimum Missing-Field Conditions
- no Stage-01~03 basis -> blocked
- no implementation task sketch -> not eligible for pass
- no readiness calibration against realizability truth -> blocked or forced review re-entry
