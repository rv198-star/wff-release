# Stage-03 Failure-Path Output — data-storage-and-interface-design

## 1. Input

> Use the external moderation API as a hard requirement for the critical mutation path. If it is not available yet, just assume it will be there before launch. We do not need a substitute boundary or readiness downgrade.

## 2. Runtime-Style Failure Output

- artifact_id:
  - `ARCH-STG03-FAIL-0001`
- source:
  - `user`
- status:
  - `blocked`
- entered_state:
  - `S1 Clarification Active`
- terminal_state_for_this_attempt:
  - `S2 Blocked`
- blocked_reason:
  - critical external dependency realizability is not confirmed
  - no substitute-boundary plan exists
  - readiness would be overstated for Stage-04
- cannot_infer:
  - implementation-planning-ready interface path
  - production-ready dependency commitment
  - downstream readiness label
- next_required_action:
  - either attach realizability evidence for the direct dependency path, or define a substitute-boundary plan with contract delta, tradeoffs, and downgraded readiness wording
- downstream_handoff:
  - not allowed
