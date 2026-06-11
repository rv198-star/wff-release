# Phase-1 PRD Excellence Scoring Rubric v0.1

## Purpose

This rubric is stricter than the current executable convergence gates.

It is designed to answer a different question:

- convergence gates ask: "can this PRD be passed downstream without obvious structural failure?"
- this rubric asks: "how close is this PRD to an excellent, complete, externally credible product requirements document?"

The intent is to reduce self-congratulation risk when the generator and the gates are produced by the same skill family.

## Scoring Dimensions

Total score: 100

- structural completeness: 8
- detail richness: 12
- reasoning and trade-off depth: 12
- business value and commercial logic: 12
- user and operating insight: 10
- workflow and specification executability: 14
- validation and risk discipline: 10
- handoff readiness: 7
- coherence and non-template quality: 5
- delivery readiness maturity: 6
- evidence confidence posture: 4

## Dimension Intent

### Structural Completeness

Checks whether the PRD actually covers the full narrative chain from problem to handoff, rather than stopping at isolated sections.

### Detail Richness

Rewards concrete specification density:

- tables
- flow definitions
- exception handling
- acceptance criteria
- state and object detail

This dimension should not be won by raw length alone.

### Reasoning And Trade-off Depth

Looks for visible decision work:

- alternatives compared
- why this, not that
- trade-offs
- downstream consequences
- deferred honesty

### Business Value And Commercial Logic

Checks whether the PRD explains why the product should matter commercially, not only functionally:

- why now
- value proposition
- target segment choice logic
- business outcome path
- willingness-to-pay or budget logic
- competitive context

### User And Operating Insight

Looks for real user-role understanding and operational usage context, not just persona labels.

### Workflow And Specification Executability

Checks whether design and engineering can derive real process behavior and spec detail without inventing the product from scratch.

### Validation And Risk Discipline

Rewards exact assumptions, thresholds, methods, evidence-state honesty, and explicit risks.

### Handoff Readiness

Checks whether design and architecture can start with explicit constraints instead of vague direction.

### Coherence And Non-template Quality

Rewards document convergence quality and penalizes visible repetition or stitched-together residue.

### Delivery Readiness Maturity

This measures whether the PRD is explicit enough for downstream design / architecture / next-step work to start safely.

It rewards:

- explicit `document_delivery_state`
- explicit `safe_start_scope`
- blocked commitments
- acceptance criteria
- dependency and risk visibility
- downstream handoff clarity

### Evidence Confidence Posture

This measures how strong the truth basis currently is and how honestly that confidence is expressed.

It rewards:

- explicit `evidence_confidence_state`
- separation of design-time inference vs. real evidence
- clear remaining unknowns
- review-bound / forbidden-assumption honesty

It stays intentionally strict: a review-bound but well-written PRD can score high on delivery readiness while still scoring only moderate on evidence confidence.

## Dual-Lens Read

Besides the strict total score, the runtime should expose two companion readings:

- `document_maturity_score`
  - how mature the PRD artifact is under the currently available inputs
- `business_completeness_score`
  - how complete the business truth / evidence / commercialization picture is against an ideal template

This avoids one common misread:

- a mature PRD should not be scored down as if it were structurally weak just because interviews, external validation, or repeated sampling have not happened yet
- but the missing evidence should still remain visible as a lower business-completeness reading

## Interpretation

- `<45`: thin draft
- `45-60`: structured but thin
- `60-75`: starter PRD
- `75-85`: strong review-bound PRD
- `85-92`: high-quality review-bound PRD
- `92+`: excellent PRD candidate

`92+` does not mean "validated market truth".
It means the document itself is approaching excellent PRD quality.

## Current Script

Source of truth:

- `scripts/phase1/phase1_prd_excellence_regression.py`
