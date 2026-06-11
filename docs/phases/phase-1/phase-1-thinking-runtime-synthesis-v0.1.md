# Phase-1 Thinking Runtime Synthesis（v0.1）

## 1. Why this document exists

The project has now clarified a critical design mistake:

> We defined lifecycle flow, norms, templates, gates, and desired output constraints, but we did **not** explicitly encode the thinking runtime that should generate those outputs with judgment.

As a result, current Phase-1 is good at:

- structured decomposition
- gate / refusal / handoff control
- warning / review-bound reporting
- artifact shaping

But it is still weak at:

- deep product analysis
- alternatives exploration
- trade-off articulation
- progressive clarification
- decision-rationale capture

This document synthesizes the missing runtime behaviors by learning from:

- **Superpowers brainstorming**
- **Product-Manager-Skills**
- **AWS Working Backwards style PM artifacts**
- and secondarily, **Everything Claude Code** where orchestration/control-surface design is relevant

---

## 2. Core correction

The problem is not mainly “missing fields.”

The problem is:

> **Phase-1 currently has strong artifact constraints but weak thinking runtime.**

Therefore, the right next move is not simply to add more template sections.

The right next move is:

> **retain current artifact/gate/handoff structure, while adding a first-class Phase-1 thinking runtime that governs how analysis is performed before outputs are locked.**

---

## 3. What the references do better

## 3.1 Superpowers brainstorming

The key behaviors are:

- understand first, do not jump to output
- ask one question at a time
- propose 2-3 approaches
- explain trade-offs
- recommend one approach with reasoning
- validate incrementally

Why this matters:

- it prevents premature structure filling
- it keeps ambiguity visible long enough for better decisions
- it treats analysis as a conversation, not a template dump

## 3.2 Product-Manager-Skills — workshop-facilitation

The facilitation system makes runtime behavior explicit:

- session heads-up
- entry modes: `Guided | Context dump | Best guess`
- one-step-at-a-time flow
- progress labels
- adaptive questioning
- numbered options at decision points
- interruption-safe handling
- assumptions-to-validate when best-guess mode is used

Why this matters:

- it turns “clarify if needed” into a repeatable interaction protocol
- it gives the agent pacing, not only content fields

## 3.3 Product-Manager-Skills — AWS Working Backwards / press release

The press-release method contributes a different strength:

- customer-first narrative forcing function
- value-before-feature framing
- “would a customer care?” stress test
- explicit revise loop if the story is weak

Why this matters:

- it pressure-tests whether the idea is compelling before downstream elaboration
- it prevents feature-centric pseudo-analysis

## 3.4 Product-Manager-Skills — problem statement and PRD workflow

The problem-statement and PRD skills do several useful things:

- force empathy-driven problem framing
- separate user problem from business symptom and feature request
- make root-cause language explicit
- require evidence and emotional realism
- tie workflow skills to a facilitation source of truth

Why this matters:

- it treats PM documents as reasoning artifacts, not just formatted outputs

## 3.5 Everything Claude Code (secondary reference)

This repo is less useful for PM thinking depth itself, but useful for:

- harness/control-surface architecture
- orchestration layering
- explicit commands + rules + skills + hooks separation
- performance-system framing

Why this matters:

- it reinforces that a complete system needs not just domain content, but a runtime/control layer
- however, it is a secondary reference for Phase-1 compared with PM Skills and Superpowers

---

## 4. The missing Phase-1 thinking-runtime mechanisms

The references point to several mechanisms missing or underpowered in current Phase-1.

## 4.1 Guided clarification protocol

Current Phase-1 says “clarify” but does not strongly standardize:

- how many rounds
- how to phrase questions
- how to choose between guided / context-dump / best-guess entry
- how to show progress
- when to stop asking and synthesize

### Needed behavior
- a visible session entry protocol
- one-question-at-a-time clarification
- bounded multi-turn discovery
- explicit assumptions-to-validate when best-guess mode is used

## 4.2 Alternatives-and-tradeoffs protocol

Current Phase-1 captures chosen outputs more than rejected alternatives.

### Needed behavior
- at major decision points, generate 2-3 options
- compare them using:
  - value
  - evidence strength
  - risk
  - dependency load
  - launch realism
- record:
  - recommended option
  - why not the others

## 4.3 Narrative stress-test protocol

Current Phase-1 is rich in structure but weak in customer-facing narrative stress tests.

### Needed behavior
- before or during convergence, test whether the product story can be told clearly
- use pressure-test questions such as:
  - would a customer care?
  - is the problem obvious?
  - is the value outcome measurable?
  - does this survive the “so what?” test?

## 4.4 Progressive validation inside a stage

Current Phase-1 is stronger at stage-level gateing than within-stage reasoning validation.

### Needed behavior
- require micro-checkpoints within a stage, not only end-of-stage checks
- validate partial conclusions before more structure is built on top of them

## 4.5 Decision-rationale capture

Current system preserves unresolved truth well, but preserves reasoning depth less well.

### Needed behavior
- every major decision should capture:
  - what options were considered
  - what trade-offs mattered
  - what evidence supported the recommendation
  - what could change the decision later

## 4.6 Analysis deepening before artifact freezing

Current system too easily moves from input → categorized structure.

### Needed behavior
- introduce a deliberate deepening step before final stage output lock-in
- use this step to:
  - sharpen ambiguity
  - compare alternatives
  - enrich rationale
  - surface contradiction and tension

---

## 5. What Phase-1 should learn first

The learning order should be conservative.

We should **not** immediately rewrite the whole Stage family.

Instead, Phase-1 should first learn and absorb these mechanisms:

1. **entry-mode protocol**
   - Guided / Context dump / Best guess
2. **one-question-at-a-time clarification**
3. **decision-point option framing**
4. **alternatives + trade-offs blocks**
5. **narrative stress-test questions**
6. **section-by-section / within-stage validation**
7. **decision-rationale capture**

---

## 6. What should NOT change yet

This correction does **not** imply:

- deleting the current Stage system
- removing gate/refusal/reporting semantics
- replacing artifact templates with freeform conversation
- jumping immediately to Phase-2-wide redesign

The current structure layer still matters.

The right architecture is:

> **thinking runtime first, structure layer second, convergence/reporting layer third**

not:

> structure only.

---

## 7. Immediate project implication

The project should now treat the following statement as true:

> **Phase-1 is the first place where the repo must evolve from artifact-constrained runtime packs into a thinking-guided runtime system.**

This does not require immediate repo-wide refactoring.

It does require a focused next slice:

- define how the thinking runtime fits into Phase-1
- define where it runs relative to current Stage-01..04
- define what output evidence it must leave behind

---

## 8. Recommended next artifacts

The next design artifacts after this synthesis should be:

- a **common reasoning kernel**
- and a **Phase-1 integration layer** that binds the kernel onto Stage-01~04

The shared kernel should define:

- method-card reasoning SOP
- evidence / uncertainty handling
- bounded deepening and freeze semantics
- handoff / convergence protocol

The Phase-1 integration layer should define:

- Phase-1 artifact-unit mapping
- Phase-1 stage emphasis and narrowing rules
- Phase-1-specific runtime traces and handoff semantics

This synthesis document intentionally stops short of that implementation design.

---

## 9. Summary sentence

> **We already have Phase-1 artifact constraints; what we now need is a Phase-1 thinking runtime that can produce those artifacts with real judgment rather than mere structural compliance.**
