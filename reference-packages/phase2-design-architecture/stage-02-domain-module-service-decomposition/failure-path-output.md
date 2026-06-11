# Stage-02 Failure-Path Output — domain-module-service-decomposition

## 1. Input

> Keep the review module read-only, but let it still mark upstream task and observation aggregates as `reviewed` so decomposition stays flexible.

## 2. Runtime-Style Failure Output

- artifact_id:
  - `ARCH-STG02-FAIL-0001`
- source:
  - `user`
- status:
  - `blocked`
- entered_state:
  - `S1 Clarification Active`
- terminal_state_for_this_attempt:
  - `S2 Blocked`
- blocked_reason:
  - ownerless lifecycle closure would be introduced
  - read-only downstream consumer is being used as an upstream truth writer
  - decomposition ownership boundaries are not defensible
- cannot_infer:
  - authoritative domain ownership
  - Stage-03-safe lifecycle/write-path model
- next_required_action:
  - remodel the lifecycle so one owning module/service boundary is authoritative, or convert the downstream artifact into an explicit read-only projection/reference
- downstream_handoff:
  - not allowed
