# Stage-02.5 State Transition Record — third-party-integration-architecture-design

## 1. Transition Table

| From | Trigger | To | Why | Allowed Next |
|---|---|---|---|---|
| `S0 Intake Received` | dependency evidence exists | `S1 Activation Decision` | lane applicability must be made explicit | `S2 Skip Decision`, `S3 Active Modeling`, `S4 Blocked` |
| `S1 Activation Decision` | no material external dependency | `S2 Skip Decision` | explicit skip is valid | `S5 Gate Pass` |
| `S1 Activation Decision` | material dependency confirmed | `S3 Active Modeling` | active lane is required | `S5 Gate Pass`, `S4 Blocked` |
| `S3 Active Modeling` | manifest, IDR, adapter, test, and risk outputs complete | `S5 Gate Pass` | downstream consumption can proceed | Stage-03 / Phase-3 handoff |
| `S3 Active Modeling` | missing auth/fallback/test/risk posture | `S4 Blocked` | provider-boundary truth is incomplete | `S3 Active Modeling` |

## 2. Minimum Missing-Field Conditions
- active dependency with no IDR -> blocked
- active dependency with no auth posture -> blocked
- active dependency with no timeout / retry / fallback posture -> blocked
- active dependency with no test strategy -> blocked
- skipped with no reason -> blocked

