# Stage-01 Self-Test Case — acceptance-coverage-planning

## Test goal

Verify that the Stage-01 runtime package can transform a realistic implementation handoff into a usable validation planning package without:

- silently guessing acceptance claims
- silently dropping traceability
- collapsing gate posture into generic prose

## Input scenario

### Project context
- A team has completed a bounded implementation handoff for a small internal service.
- Requirements and API contract anchors exist.
- The team needs a first-pass acceptance/UAT package before execution begins.

### Known constraints
- One environment has partial access only.
- High-risk validation areas are authentication, data correctness, and export behavior.
- The team wants a lightweight but explicit execution-control artifact.

### Missing / review-bound items
- not all non-critical scenarios are fully prioritized
- one downstream environment limitation remains unresolved

## Expected Stage-01 behavior

The runtime package should:

1. recognize that a usable upstream handoff exists
2. create explicit acceptance mapping
3. produce coverage rationale and exclusions
4. define entry/exit gate posture
5. keep unresolved environment limits visible
6. declare clearly whether Stage-02 may start

## Failure conditions

The self-test fails if the stage:

- produces generic testing prose with no mapping
- loses `TEST-* -> API-* -> REQ-*` discipline
- omits explicit gate semantics
- hides environment blockers
