# Stage-02.5 Runtime Decision Log — third-party-integration-architecture-design

## 1. Case A — active provider lane
- input summary:
  - case depends on external identity provider and LLM provider
- transition:
  - `S0 Intake Received` -> `S1 Activation Decision` -> `S3 Active Modeling`
- decision reason:
  - Stage-03 and Phase-3 would otherwise need to invent auth and adapter posture
- gate outcome:
  - active Stage-02.5 required

## 2. Case B — skipped provider lane
- input summary:
  - case is materially internal and no external provider boundary survives Stage-02
- transition:
  - `S0 Intake Received` -> `S1 Activation Decision` -> `S2 Skip Decision`
- decision reason:
  - no material third-party contract exists
- gate outcome:
  - skipped is allowed only with explicit reason

## 3. Case C — blocked because fallback and test posture are absent
- input summary:
  - payment provider is marked critical, but no timeout, retry, fallback, or test posture is stated
- transition:
  - `S3 Active Modeling` -> `S4 Blocked`
- decision reason:
  - provider dependence is active but operationally undefined
- gate outcome:
  - no Stage-03/Phase-3 handoff until repaired

