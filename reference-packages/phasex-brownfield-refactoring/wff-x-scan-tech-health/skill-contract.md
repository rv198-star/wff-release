# wff-x-scan-tech-health Skill Contract — scan-tech-health

## 1. Skill Goal

- Score the technical health of the existing system using the PhaseX baseline.
- Convert raw brownfield structure into prioritized risk, debt, and next-step guidance.

## 2. Inputs

- required:
  - `wff-x-scan-code-baseline` output
- optional:
  - existing test results
  - CI history
  - dependency audit output
  - incident or reliability notes

## 2.1 Cannot Infer

- real test effectiveness from test file count alone
- production reliability from code style alone
- security maturity from dependency versions alone
- performance risk without workload or hotspot evidence
- that a requested change is “just refactor” unless the behavior-preservation boundary is explicit

## 2.2 Must Validate Before Exit

- a scoring dimension set is named
- top technical debt items are prioritized
- at least one risk matrix is present
- `brownfield_health_judgment` explains current change safety, dominant risk, recommended next move, and review-bound decisions
- `risk_to_action_map` turns each material risk into `stop`, `assess-more`, `build-safety-net`, `proceed-technical-refactor`, or `package-target-driver`
- refactor boundary vs feature-change boundary is explicit
- the recommendation states whether the system can move directly to change or must first add protection

## 3. Outputs

- health scorecard
- brownfield health judgment
- top debt register
- risk matrix
- risk-to-action map
- evidence-backed score rationale
- recommended next move

## 4. Default Dimensions

- code quality and maintainability
- testability and existing coverage posture
- dependency health
- coupling / blast radius
- documentation / operability

## 5. Gate Conditions

- `PXG-04-1`: every scored dimension has explicit evidence or a declared uncertainty note
- `PXG-04-2`: the risk matrix is non-empty when blocker-grade or high-blast-radius issues exist
- `PXG-04-3`: refactor boundary and recommended next move are explicit
- `PXG-04-4`: risk-to-action rationale is explicit and does not treat the scorecard as the decision
- `PXG-04-5`: if a specialized profile is claimed, its overlay must include quantitative evidence rather than prose only:
  - performance: at least one baseline metric plus one hotspot evidence
  - compliance: obligation-to-control mapping plus explicit uncovered items
  - coupling: at least one measurable coupling artifact with threshold or rank

## 6. Acceptance Criteria

- the output makes change risk legible instead of just descriptive
- the assessment distinguishes blocker-grade issues from tolerable debt
- the scorecard supports the brownfield judgment instead of replacing it
- specialized overlays stay evidence-backed instead of becoming optional commentary blocks
- the next move is clear:
  - assess more
  - build safety net
  - proceed to bounded change
  - proceed to technical refactor

## 7. Boundaries

- no target architecture synthesis here
- no requirement reframing here
- no fake precision when evidence is thin
- no “refactor” label unless the behavior-preservation claim is defensible
