# Phase-1 Thinking Loop（v0.1）

## 1. Purpose

This document defines the **Phase-1 specialization** of the bounded deepening loop that sits between:

- the Phase-1 thinking runtime layer
- and the existing convergence driver / stage output system

The generic loop semantics now live in:

- `runtime-deps/mindthus/source/skills/3l5s/resources/three-layer-recursive-loop.md`
- `docs/governance/deepening-and-freeze-protocol-v0.1.md`

Its purpose is to prevent two failure modes:

1. **too shallow** — one-pass reasoning that never becomes strong analysis
2. **never-ending** — endless brainstorming that never freezes into phase outputs

The loop therefore exists to support:

> **limited iterative deepening with explicit exit conditions**

---

## 2. Scope boundary

This is a **Phase-1-only** loop model layered on top of the shared deepening/freeze protocol.

It governs:

- Stage-01 through Stage-04 analytical refinement

It does **not** yet define:

- a Phase-2 design loop
- a generic project-wide loop
- a live orchestration engine implementation

---

## 3. Why the loop is necessary

Phase-1 now has:

- structured stage outputs
- a thinking runtime layer
- a convergence driver
- an execution report

But without an explicit loop, the runtime falls into a false binary:

- either do one thinking pass and freeze too early
- or keep refining informally with no stable stop rule

The loop solves this by making iteration explicit, bounded, and auditable.

---

## 4. Relationship to existing assets

### Thinking runtime layer
Defines **what kinds of thinking** must happen.

### Thinking loop
Defines **how many rounds** of deepening may happen and **when to stop**.

### Shared deepening/freeze protocol
Defines the reusable loop semantics that other phases may later adopt.

### Shared reasoning loop
Defines the reusable round structure and loop-state model that other phases may later adopt.

### Convergence driver
Defines **how stage outputs are executed, evaluated, and converged** across Phase-1.

In short:

- thinking runtime = reasoning behavior
- shared reasoning loop = reusable round structure
- shared deepening/freeze protocol = reusable iteration-state resolution
- thinking loop = Phase-1 artifact-specific iteration control
- convergence driver = stage/pack/report control

---

## 5. Loop design principle

The loop is not for polishing style.

The loop exists only to improve:

- clarity of user/problem framing
- quality of alternatives comparison
- quality of trade-off reasoning
- quality of rationale capture
- stage-to-stage downstream usability

If a new round does not materially improve one of those, it should not run.

The loop is also artifact-driven.

Each round must be anchored to one or more **specific stage artifact units**, not to a vague sense that “the thinking is not good enough yet.”

Examples:
- Stage-01 user boundary
- Stage-01 final problem statement
- Stage-02 backbone flow
- Stage-03 chosen MVP loop
- Stage-04 decision-state rationale

The loop is also method-guided.

Each round should ask:

- which required cards should shape the reasoning?
- which anti-pattern cards warn against weak or misleading reasoning?
- which optional cards would materially strengthen this artifact unit?

Template/SOP checks still matter, but mainly to ensure the refined reasoning can be written back into the current stage skill cleanly.

The loop should therefore refine artifact units **through method assets**, not just through raw intuition.

---

## 5.1 Value-based convergence and certainty boundary

Phase-1 loops are intentionally high-agentic because workflow is only the outer frame.

Default mode is:

- `baseline`

Optional stronger exploration is:

- `creative`
- allowed only on explicit user request
- allowed only after baseline sufficiency already exists

A new round is justified only if it is expected to create `positive business value gain`.

For this repo, that means at least one of:

- a more realistic ordinary real-world baseline
- a thicker and more credible core scenario family
- surfacing and comparing a higher-value operating option before later cost/scope trimming
- a clearer business value mechanism
- a sharper buyer / budget / willingness-to-pay judgment
- a clearer continue / revise / pause decision
- a clearer user task path or lower user-process friction that materially improves real adoption or task completion
- a clearer `why-this-not-that` decision
- less downstream invention of critical product truth
- removal of a demo-like omission that would weaken downstream work

If the expected gain is only:

- style cleanup
- structure completion without stronger truth
- generic abstraction
- earlier cost/budget trimming before the strongest value-bearing options are surfaced
- more commercial wording without stronger business consequence
- cosmetic surface polish without stronger user outcome or business consequence

then the loop should not continue.

When ordinary real-world baseline is still uncertain and materially affects the chosen product world, at least one loop round should prefer calibration/evidence over self-generated speculation.

The loop must also preserve this truth order:

1. `ordinary real operating baseline`
2. `product world selection`
3. `business/release truth compression`
4. `planning/control truth split`

Hard rule:

- do not jump directly from scenario notes into `planning/control truth`
- do not let workflow/control surfaces decide product category or value framing
- if the loop produces cleaner control truth but weaker business truth, treat that round as regression

## 6. Loop states

Each stage may move through the following loop states:

### `S-draft-structured`
Initial structure exists.

Symptoms:
- fields are filled
- direction is visible
- reasoning may still be shallow

### `S-deepening-round-1`
First analytical deepening round.

Focus:
- clarification
- alternatives
- trade-offs
- stress tests
- rationale capture

### `S-deepening-round-2`
Second deepening round.

Focus:
- only high-value gaps exposed by round 1 or comparison review
- no broad re-exploration

### `S-deepening-round-3`
Third and final deepening round.

Focus:
- final integration of the strongest reasoning improvements
- tighten synthesis, not reopen the whole problem space
- no new broad exploration unless a true blocker is discovered

### `S-review-bound-freeze`
Good enough to freeze and move to next stage under explicit warning/review-bound semantics if needed.

### `S-return-remediate`
Current stage cannot responsibly freeze yet; clarification or targeted remediation is required.

### `S-blocked`
Current stage cannot continue without inventing non-inferable truth or violating phase rules.

---

## 7. Default loop limit

### Default rule
Each stage gets:

- one structured draft
- up to **three** deepening rounds

After that, the stage must end in one of:

- `S-review-bound-freeze`
- `S-return-remediate`
- `S-blocked`

### Why
Three rounds are the better default because they allow:
- one first-pass analytical deepening
- one comparison/feedback absorption round
- one final integration round

while still remaining clearly bounded.

The third round is not permission for broad re-exploration.
It is the last chance to turn improved reasoning into a stable stage result.

---

## 8. What counts as a valid new round

A new round is justified only if at least one of these is true:

1. the current conclusion is still too generic
2. a meaningful alternative was not explored
3. the `why-this-not-that` rationale is weak
4. the customer-care / so-what stress test fails or is inconclusive
5. downstream usability is still weak
6. a comparison replay revealed a better reasoning pattern worth absorbing
7. a specific stage artifact unit remains shallow, weakly justified, or weakly handed off

If none of these are true, do not loop again.

Additional order rule:

- if `business-world sufficiency` or `value mechanism clarity` is still weak, a buyer/budget-only rewrite does not count as a valid convergence round; loop focus must return to world/value deepening first

### Extra rule for round 3
Round 3 is allowed only when:

- rounds 1 and 2 already improved the stage materially,
- but the current artifact still lacks synthesis quality or downstream usability,
- and the expected work is integrative rather than exploratory.

Round 3 must not be used to reopen the full problem space.

---

## 9. Stage-specific loop focus

## 9.1 Stage-01

Each additional round may improve only these areas:

- target user boundary sharpness
- problem-framing quality
- need-framing alternatives
- why-this-not-that clarity
- Stage-02 handoff usefulness

The preferred decomposition units are:

- primary user boundary
- final problem statement
- need framing choice
- customer-care / so-what stress-test outcome
- assumptions-to-validate

Not allowed in later rounds:
- endless expansion of user lists
- generic market brainstorming without decision pressure
- style-only rewriting

## 9.2 Stage-02

Each additional round may improve only these areas:

- backbone flow clarity
- structure alternatives comparison
- boundary reasoning
- constraint realism
- Stage-03 sliceability

The preferred decomposition units are:

- backbone flow
- requirements panorama
- structure alternative comparison
- key constraints
- priority split

## 9.3 Stage-03

Each additional round may improve only these areas:

- MVP loop viability
- slice alternatives comparison
- deferral honesty
- trade-off clarity
- Stage-04 validation leverage

The preferred decomposition units are:

- complete experience loop
- minimum viable experience loop
- first slice choice
- deferred items
- validation assumptions

## 9.4 Stage-04

Each additional round may improve only these areas:

- validation target clarity
- method-fit reasoning
- evidence-state honesty
- decision-state rationale
- revision consequences

The preferred decomposition units are:

- validation target
- method fit
- evidence state
- decision state
- revision recommendation

---

## 10. Freeze criteria

A stage may enter `S-review-bound-freeze` when all of the following are true:

1. the core framing is explicit enough
2. at least one meaningful alternative has been considered when ambiguity was material
3. the main assumptions are explicit
4. downstream can proceed without inventing core truth
5. another round is unlikely to create major analytical improvement

This does not require perfection.

It requires **bounded sufficiency**.

---

## 11. Return / remediate criteria

A stage should enter `S-return-remediate` when:

- the direction is visible but still too weak to freeze
- one or two missing clarifications would significantly improve downstream usability
- a focused remediation path exists

Examples:
- user boundary still too broad
- problem framing still feature-smuggled
- alternatives were listed but not actually compared
- validation target exists but method fit is weak

---

## 12. Blocked criteria

A stage should enter `S-blocked` when:

- freezing would force the next stage to invent core user/scope/constraint truth
- the current stage cannot produce a minimally defensible result from available evidence
- unresolved issues are Class C and cannot be honestly carried as warning-bearing review-bound items

Examples:
- no defensible primary user boundary
- no usable problem framing at all
- no viable MVP loop can be defended
- validation conclusion would be pure fabrication

---

## 13. Exit mechanism

The loop must always terminate in one of these exits:

### Exit A — `Freeze`
The stage is good enough for downstream use.

### Exit B — `Return`
The stage needs one more targeted external clarification/remediation before it can freeze.

### Exit C — `Blocked`
The stage cannot proceed responsibly.

There is no “continue refining indefinitely” exit.

---

## 14. Evidence required per round

Each round should leave behind a minimal record of:

- what was refined
- which alternative(s) were compared
- what trade-off was clarified
- whether the stress test outcome improved
- why the stage is now frozen / returned / blocked

This record may live in:

- stage reasoning evidence note
- stage output reasoning section
- execution report notes

---

## 15. Interaction with the convergence driver

The driver already contains an outer execution loop:

- run stage
- classify
- continue / return / block

This thinking loop should run **inside** each stage before the driver decides whether to proceed.

So the intended model is:

1. stage draft
2. bounded thinking loop
3. freeze/return/block stage result
4. driver classifies and moves on

---

## 16. Biggest dangers

### If the loop is missing
The stage outputs will look complete structurally while remaining analytically thin.

### If the loop has no exit
Phase-1 turns into an endless workshop and loses its phase progression value.

---

## 17. Immediate application

Use this loop first on:

- Stage-01

because Stage-01 already has:

- v3 replay
- A/B comparison
- v4 refinement

and therefore already provides the clearest evidence that bounded analytical looping improves output quality.

---

## 18. Summary sentence

> **Phase-1 should not use one-pass thinking or infinite thinking; it should use a bounded convergence loop that deepens reasoning just enough to freeze responsibly.**
