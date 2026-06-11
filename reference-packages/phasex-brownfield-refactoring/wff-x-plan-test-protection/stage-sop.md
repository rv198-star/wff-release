# wff-x-plan-test-protection SOP — plan-test-protection

## 1. Positioning

- goal: decide what must be tested before brownfield change
- upstream: `wff-x-scan-code-baseline`, preferably `wff-x-scan-tech-health`
- downstream: Phase-3 brownfield implementation or a dedicated protection sprint

## 2. Start Conditions

- required: baseline exists
- preferred: health assessment exists
- blocked: change surface is unknown and critical paths cannot be named

## 3. Standard Execution Steps

1. identify critical business and technical paths likely to break during change
2. inspect existing test posture for those paths
3. start from `wff-x-scan-tech-health` risks when health assessment exists
4. identify protection gaps by surface and risk level
5. choose the lightest effective test type for each gap
6. name the fastest repeatable feedback loop that can protect the next change honestly
7. order the work so high-blast-radius protections land first
8. define what evidence would prove the safety net is good enough
9. produce a go / no-go protection decision before handoff

## 4. Process Checkpoints

- critical paths are named
- test gaps are prioritized
- each proposed test has a reason tied to a hotspot or invariant
- fastest repeatable feedback is named even if it is currently missing
- change blockers and pre-change evidence are explicit
- go/no-go rule for implementation is explicit

## 5. Output Rules

- prefer tables for candidate tests and priorities
- keep proposed tests close to observable behavior or contracts
- distinguish “must-have before change” from “nice-to-have after change”
- do not require a complete test suite when a smaller safety net can protect the highest-risk behavior honestly

## 6. Stage Acceptance

- a refactor team can start with a clear protection order
- brownfield change no longer depends on hope or manual memory alone
- implementation state is honestly classified as blocked, guarded, or protected enough
