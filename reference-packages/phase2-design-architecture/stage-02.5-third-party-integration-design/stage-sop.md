# Stage-02.5 SOP — third-party-integration-architecture-design

## 1. Stage Positioning
- goal: explicitly design third-party integration boundaries before Stage-03 and Phase-3
- upstream: Phase-1 dependency manifest, Stage-01, Stage-02
- downstream: Stage-03, Stage-04, Phase-3

## 2. Start Conditions
- required when active: at least one material external dependency is known
- allowed skip: no material external dependency exists
- blocked: dependency exists but no owner, consuming module, or provider posture can be stated

## 3. Standard Execution Steps
1. confirm whether Stage-02.5 is active or skipped
2. normalize the third-party dependency manifest and classify each dependency
3. author one IDR per active dependency
4. define adapter specifications with internal-port naming and provider mapping
5. define test posture across local, CI, staging, and production
6. register operational / compliance / vendor risks
7. hand off provider/auth/fallback/mock posture to Stage-03 and Phase-3

## 4. Process Checkpoints
- activation decision is explicit
- skip reason exists when skipped
- dependency manifest covers every active dependency
- each IDR names provider, integration pattern, internal interface, auth, key management, timeout, retry, and fallback
- adapter spec defines internal port plus provider endpoint/error mapping
- test strategy covers negative paths, not only happy path
- risk register is non-empty when active

## 5. Output Rules
- output may be `active` or `skipped`, never implicit
- use provider-agnostic internal-port naming where swap risk matters
- keep mock / sandbox / production guardrails explicit
- surface tenant / auth / key / degraded-mode posture rather than burying it in prose

## 6. Stage Acceptance
- Stage-03 can consume provider-boundary posture without re-deciding it
- Phase-3 can implement adapters and tests against explicit contracts
- critical external dependency risk remains visible in Stage-04 and beyond

