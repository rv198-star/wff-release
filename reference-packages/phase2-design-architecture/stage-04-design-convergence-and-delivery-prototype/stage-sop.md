# Stage-04 SOP — design-convergence-and-delivery-prototype

## 1. Stage Positioning
- goal: converge Stage-01~03 into delivery-ready design package
- upstream: Stage-01~03
- downstream: implementation phase

## 2. Start Conditions
- required: usable Stage-01~03 package set
- required carryover: Stage-03 scenario coverage matrix
- required carryover: Stage-03 technology selection evaluation matrix
- required carryover: dominant bottleneck hypothesis, alternatives, baseline insufficiency note, and optimum candidate
- refuse: missing critical Stage-03 outputs
- blocked: unresolved contradictions prevent coherent convergence
- declaration-state rule: keep `present | absent | unknown | deferred` semantics explicit in the final convergence and handoff package

## 3. Standard Execution Steps
1. aggregate and reconcile prior-stage outputs
2. confirm all known business scenarios remain covered
3. review whether technology selections remain evidence-backed and realizable
4. review dominant bottleneck, alternatives, and acceptable-vs-optimal distinction
5. produce convergence summary and prototype-oriented expression
6. produce critical interaction sequence views for key public-boundary scenarios
7. produce verification notes, optimality review, unresolved-item register, and coarse-grained implementation task sketch with effort-basis/FTE realism
8. close identity/auth vendor/token lifecycle posture where delivery realism depends on it
9. assemble downstream handoff package, quick-start path, and glossary/onboarding summary

## 3.1 State Flow
- S0 intake → S1 clarification → S2 blocked
- S3 provisional inference (review-bound)
- S4 user review → S5 gate pass → S6 escalate

## 4. Process Checkpoints
- coherence across Stage-01~03 is explicit
- structural consistency across lifecycle ownership, command boundaries, and named public artifacts is explicit
- unresolved items are explicit
- handoff package is implementation-consumable
- all known business scenarios remain covered
- only critical public-boundary scenarios are diagrammed in detail (hard gate: critical_interaction_sequence_set must include at minimum one happy-path sequence and one blocked/failure-path sequence, each as numbered step list, Mermaid sequence diagram, or equivalent structured form; narrative description alone = gate fail)
- technology selection evidence is preserved for downstream review
- acceptable-vs-optimal distinction is explicit
- baseline insufficiency and winning candidate remain visible
- implementation task sketch is present and remains coarse-grained
- implementation task sketch includes effort_basis, team_assumption, fte_breakdown, and rollback/fallback posture instead of duration-only guessing
- identity/auth vendor, token lifecycle, and key-rotation posture are explicit when delivery realism depends on them
- readiness wording is calibrated to current verification/confidence/realizability evidence
- internal private choreography is not mistaken for required design output
- declaration-state/NFR semantics preserved

## 5. Method Assets
- required: architecture synthesis and diagram expression references
- anti-patterns: fake certainty, missing unresolved notes, silent handoff assumptions, hidden structural contradictions, readiness overclaim

## 6. Output Rules
- required outputs: convergence package + prototype expression + verification + handoff
- required outputs also include a coarse-grained implementation task sketch
- diagram obligation: `required` (hard gate: absence of structured visual representation = gate fail; stage must be downgraded to `blocked`, not `provisional` or `pass`)
- only critical public-boundary scenarios require detailed sequence views
- technology choices should not arrive in Stage-04 as unexplained conclusions; carry forward evidence references
- convergence must preserve why stronger candidates were chosen over mainstream baseline where relevant
- review-bound markers required for unresolved content
- structural contradictions in lifecycle ownership, command boundaries, or public-name closure must downgrade readiness instead of being hidden
- declaration-state carryover and final NFR handling must be explicit in handoff-facing sections
- final readiness language must not exceed the package's verification/confidence/realizability evidence
- implementation task sketch must stay at slice/module/work-package level, not class/method/file/ticket level
- downstream handoff must include a quick-start path and glossary/onboarding summary when a new implementation squad would otherwise need to reconstruct Phase-2 vocabulary

## 7. Stage Acceptance
- downstream handoff can start implementation planning without re-synthesizing prior stages
- downstream should not need to infer cross-boundary interaction order from prose alone
- downstream should not need to guess why the final architecture is better than the default baseline under dominant constraints
- downstream should not receive a stronger readiness claim than the evidence supports
- downstream should not receive a fake coding-level plan disguised as a Stage-04 design artifact

## 8. Handoff Rules
- include consumption rule for review-bound items and unresolved constraints
- include implementation task sketch only at coarse-grained work-package level
