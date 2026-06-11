# PX-SK-04 SOP — technical-health-assessment

## 1. Positioning

- goal: judge brownfield technical risk and readiness for change
- upstream: `PX-SK-01`
- downstream: human decision, `PX-SK-07`, `PX-SK-06 partial`, or direct Phase-3 entry when risk is low

## 2. Start Conditions

- required: baseline extraction completed
- optional: tests, audit reports, CI signals, incidents
- blocked: baseline is too weak to name modules, surfaces, or runtime posture

## 3. Standard Execution Steps

1. choose the scoring dimensions that fit the case
2. score each dimension with explicit evidence
3. identify top debt and fragility items
4. build a risk matrix with likelihood and impact
5. convert validated hotspots into refactor candidates when the profile is `technical-refactor`
6. explain the brownfield health judgment before relying on the scorecard number
7. map each material risk to one action: `stop`, `assess-more`, `build-safety-net`, `proceed-technical-refactor`, or `package-partial-change`
8. judge whether protection is needed before change
9. recommend the smallest honest next move
10. if a specialized profile is enabled, attach the quantitative overlay before exit

## 4. Process Checkpoints

- every score has evidence or an uncertainty note
- debt items are prioritized, not merely listed
- risk matrix names at least one high-risk item when present
- `technical-refactor` runs separate refactor candidates from generic debt listing
- risk-to-action rationale is explicit and evidence-backed
- scorecard is used as supporting evidence, not the decision itself
- specialized profile claims are backed by metrics or control maps, not prose alone
- next move is explicit

## 5. Output Rules

- use tables for scorecard and debt register
- separate evidence-backed findings from tentative suspicions
- keep the assessment actionable rather than essay-like
- do not invent missing codebase truth that `PX-SK-01` did not establish

## 6. Stage Acceptance

- a reviewer can tell where the system is dangerous to change
- PhaseX can decide whether safety-net work is mandatory before implementation
- a reviewer can see why the selected next move follows from the evidence rather than from a bare score
