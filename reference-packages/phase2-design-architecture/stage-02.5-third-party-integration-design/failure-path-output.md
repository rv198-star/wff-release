# Stage-02.5 Failure-Path Output — third-party-integration-architecture-design

## 1. Input

> The GEO case depends on an external LLM provider. We can decide retry/fallback later, and CI can just hit the real API.

## 2. Runtime-Style Failure Output
- artifact_id:
  - `ARCH-STG025-FAIL-0001`
- status:
  - `blocked`
- entered_state:
  - `S3 Active Modeling`
- terminal_state_for_this_attempt:
  - `S4 Blocked`
- blocked_reason:
  - active dependency lacks timeout / retry / fallback posture
  - test strategy is production-only and non-defensible
  - provider boundary would leak uncertainty into Stage-03 and Phase-3
- next_required_action:
  - add IDR depth, adapter mapping, negative-path test strategy, and risk registration before handoff

