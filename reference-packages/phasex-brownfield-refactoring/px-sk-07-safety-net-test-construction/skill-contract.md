# PX-SK-07 Skill Contract — safety-net-test-construction

## 1. Skill Goal

- Define the minimum useful test protection needed before brownfield refactoring or risky local change.
- Turn technical hotspots into an ordered safety-net plan rather than generic “add more tests” advice.
- Preserve the refactoring discipline that structural change should happen under self-testing, fast-feedback conditions.

## 2. Inputs

- required:
  - `PX-SK-01` output
  - `PX-SK-04` output when available
- optional:
  - existing test suite
  - production defect history
  - API contracts
  - replay logs

## 2.1 Cannot Infer

- that a module is protected because unit tests exist nearby
- that integration behavior is stable without contract or smoke coverage
- that visual or UX regression is irrelevant for all brownfield work

## 2.2 Must Validate Before Exit

- at least one protected critical path is named
- candidate test additions are prioritized
- test types are matched to risk:
  - unit
  - contract
  - integration
  - smoke
- the plan states whether current feedback is fast enough for small-step refactoring
- protection effectiveness criteria are explicit
- `safety_net_strategy` states protected behavior, fastest repeatable feedback, minimum pre-change protection, change blockers, and evidence to collect before change
- `go_no_go_protection_decision` explains whether implementation is blocked, guarded, or protected enough

## 3. Outputs

- safety-net candidate list
- safety-net strategy
- prioritized test construction plan
- execution ordering
- protection effectiveness criteria
- go / no-go protection decision

## 4. Gate Conditions

- `PXG-07-1`: at least one critical path and its minimum protection are explicit
- `PXG-07-2`: each high-risk hotspot is mapped to a concrete test type or protection mechanism
- `PXG-07-3`: the plan states whether the feedback loop is fast enough for small-step refactoring
- `PXG-07-4`: go / no-go protection decision is explicit and tied to evidence, not generic test advice

## 5. Acceptance Criteria

- a change team knows what to protect first and why
- tests are proposed against real hotspots and interfaces, not generic best practice
- the output states whether implementation can start immediately or must wait for protection
- safety-net strategy starts from `PX-SK-04` risk when available and does not demand a full test suite when a smaller fast feedback loop is the honest first protection

## 6. Boundaries

- Wave-1 does not require generating the full test suite automatically
- this is protection planning first, not implementation of all tests
- do not claim regression safety without explicit coverage targets
- do not approve risky refactor work under a slow or non-self-checking feedback loop without naming that gap
