# Stage-02.5 Skill Contract — third-party-integration-architecture-design

## 1. Skill Goal
- Convert Phase-1 third-party dependency signals plus Phase-2 Stage-01/02 architecture truth into an explicit integration-design lane.
- Freeze provider-facing decisions before Stage-03 and Phase-3 silently reinvent auth, adapter, fallback, or mock/sandbox posture.

## 2. Inputs
- Required when active:
  - Phase-1 third-party dependency manifest or equivalent dependency evidence
  - Stage-01 architecture definition and boundary constraints
  - Stage-02 module/service decomposition
  - provider docs, sandbox rules, or contract evidence when available
- Optional:
  - procurement or ownership constraints
  - compliance / cross-border / retention constraints
  - target SLA, quota, and cost signals

## 2.1 Trigger and Skip Rules
- trigger when Phase-1 or Phase-2 reveals material external provider dependence
- skip only when the case is materially internal and Stage-03/Phase-3 will not depend on an external provider contract
- if skipped, record an explicit skip reason; silence is not a valid state

## 2.2 Cannot Infer
- provider-facing auth or key-management posture without naming it
- fallback/degraded mode for a critical dependency without explicit statement
- internal adapter contract if the dependency owner and consuming module remain ambiguous
- test posture for external integrations by assuming production-only validation

## 2.3 Must Validate Before Exit
- every active dependency has a dependency-manifest row
- every active dependency has an IDR
- every active dependency has auth posture plus timeout / retry / fallback posture
- every active dependency has an adapter-spec row with internal port and provider endpoint mapping
- every active dependency has a local / CI / staging / production test strategy
- integration risk register is non-empty when Stage-02.5 is active

## 3. Outputs
- activation decision
- third-party dependency manifest
- integration decision records
- integration adapter specifications
- integration test strategy
- integration risk register

## 4. Acceptance Criteria
- Stage-03 does not need to invent provider bindings, adapter seams, or failure mapping from scratch
- Phase-3 can implement adapters against named internal ports instead of vendor SDK leakage
- mock / sandbox / live validation posture is explicit before implementation begins
- auth, key-management, timeout, retry, and fallback posture remain visible in the design handoff

## 5. Boundaries
- no production code or SDK implementation
- no deep internal schema design unless it is required to explain adapter contract impact
- no silent downgrade from active to skipped because evidence feels inconvenient

## 6. Flow Rules
- handoff target: `Stage-03 data-storage-and-interface-design` and `Phase-3 implementation entry`
- active dependencies must stay visible through Stage-03 contracts and Phase-3 adapter work

