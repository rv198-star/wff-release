# Stage-02.5 Rule Cards — third-party-integration-architecture-design

## RC-01
- statement: Stage-02.5 must make activation or skip explicit when third-party dependence is materially present.
- type: requirement
- applies_to_stage: Stage-02.5

## RC-02
- statement: Skipped Stage-02.5 must include a concrete skip reason.
- type: requirement
- applies_to_stage: Stage-02.5

## RC-03
- statement: Active Stage-02.5 must include a dependency manifest.
- type: requirement
- applies_to_stage: Stage-02.5

## RC-04
- statement: Every active dependency must have an IDR with provider, integration pattern, internal interface, auth posture, key management, timeout, retry policy, and fallback strategy.
- type: requirement
- applies_to_stage: Stage-02.5

## RC-05
- statement: Every active dependency must have an adapter specification with internal port, provider endpoint, error mapping, and mock strategy.
- type: requirement
- applies_to_stage: Stage-02.5

## RC-06
- statement: Every active dependency must have a local / CI / staging / production test strategy with negative-path coverage.
- type: requirement
- applies_to_stage: Stage-02.5

## RC-07
- statement: Active Stage-02.5 must have a non-empty integration risk register.
- type: requirement
- applies_to_stage: Stage-02.5

## RC-08
- statement: Provider-specific behavior must be absorbed behind named internal ports rather than leaking directly into downstream public contracts.
- type: requirement
- applies_to_stage: Stage-02.5

## RC-09
- statement: Critical provider dependence must not remain active if fallback and degraded-mode posture are absent.
- type: prohibition
- applies_to_stage: Stage-02.5

## RC-10
- statement: Stage-03 and Phase-3 must consume Stage-02.5 outputs when the lane is active instead of silently redesigning provider-boundary behavior.
- type: requirement
- applies_to_stage: Stage-02.5

