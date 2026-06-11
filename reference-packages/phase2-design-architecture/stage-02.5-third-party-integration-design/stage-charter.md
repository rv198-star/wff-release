# Stage-02.5 Charter — third-party-integration-architecture-design

## 1. Authoring Goal
- Target Stage Skill: `third-party-integration-architecture-design`
- Parent phase: design / architecture
- Goal: make third-party provider boundaries explicit enough that downstream stages do not redesign them ad hoc

## 2. Problem This Stage Must Solve
- whether the lane is active or skipped
- which consuming module owns each external dependency
- which internal adapter port shields provider-specific behavior
- how auth, timeout, retry, fallback, and degraded-mode posture work
- how the dependency is tested safely before production

## 3. Upstream Inputs
- Phase-1 third-party dependency manifest
- Stage-01 architecture boundary and constraints
- Stage-02 decomposition and consuming modules

## 4. Downstream Handoff
- Stage-03 consumes adapter, provider, and failure posture
- Phase-3 consumes named internal ports, mock/sandbox strategy, and error mapping

