# Phase-2 Realizability Architecture Review Rule（v0.1）

## 1. Why this rule exists

The restaurant-owner case exposed a deeper Phase-2 weakness than “one API may be hard to obtain.”

The real problem was:

> the architecture/design chain could produce a clean-looking bounded design and still fail to force a serious review of whether the design was actually realizable under current technical constraints.

This means the missing safeguard is not just an external-API rule.
It is a broader **realizability architecture review gate**.

---

## 2. Core rule

Phase-2 must not pass a design/architecture handoff as if it were implementation-facing unless it has explicitly reviewed:

1. **boundary coherence** — does the architecture shape make sense?
2. **dependency realizability** — can its critical dependencies actually be obtained or simulated honestly?
3. **execution realism** — is there a credible first-pass realization path?
4. **constraint integrity** — are critical constraints really preserved, or just mentioned?

In short:

> **Phase-2 must review not only whether the architecture is well-structured, but whether it is honestly realizable.**

---

## 3. What Phase-2 must review explicitly

### A. External dependency realizability

Examples:

- external APIs
- SDK access
- platform integration boundaries
- partner system dependencies
- authentication or credential requirements

Phase-2 must classify each mainline-critical dependency as:

- available and usable
- available but constrained
- unknown / unverified
- not available for first-pass realization

### B. Delivery path realism

Phase-2 must answer:

- is there a credible first-pass implementation path?
- if the intended integration path is not usable, is there an honest substitute boundary?
- does the delivery expression still represent something that can really be built next, not just something that sounds architecturally clean?

Recommended normalized values for `delivery_path_realism` are:

- `credible`
- `constrained`
- `weak`
- `blocked`

### C. Constraint integrity

Phase-2 must check whether key constraints are merely listed or actually shape the design.

For example:

- low-friction setup
- privacy / retention constraints
- human-in-control send boundary
- no heavy integration in first pass

If the design conflicts with those constraints in practice, the conflict must be surfaced.

### D. Review outcome

Phase-2 must not stop at “architecture summary + handoff package.”
It must also output a realizability judgment such as:

- `realizable as designed`
- `realizable only with constrained/simulated boundary`
- `review-bound`
- `blocked for implementation-facing handoff`

### E. Iterative review loop

This judgment is not required to be one-shot/final.

Phase-2 may and often should use an iterative cycle:

1. review
2. identify realizability gaps
3. revise the design/handoff package
4. re-review
5. repeat until the design is either:
   - good enough to pass honestly
   - or clearly blocked

The important rule is:

> **the loop may iterate, but each iteration must make the remaining realizability state clearer, not just cosmetically cleaner.**

---

## 4. Anti-pattern to forbid

Do not let Phase-2 pass because:

- the diagrams look coherent
- the modules decompose cleanly
- the handoff prose sounds implementation-facing

if the architecture still depends on assumptions that have not passed realizability review.

Examples of forbidden false-completion patterns:

- “we have an adapter” when no feasible integration path is known
- “the boundary is clean” when the real implementation path is missing
- “the design is ready” when critical constraints have not actually shaped the solution

---

## 5. What counts as an acceptable first-pass substitute

Phase-2 may still pass if a clear substitute exists, for example:

- simulated/manual ingest boundary instead of unavailable direct platform API
- bounded mock/stub lane for non-core integration realism
- narrowed first-slice scope that preserves the key user value without pretending missing infrastructure exists

But this is only acceptable if Phase-2 says so explicitly.

---

## 6. Required downstream expression

When realizability is constrained, the implementation-facing handoff must say:

- what implementation may rely on
- what implementation must not assume
- what substitute boundary is allowed
- which risks remain review-bound

If the design has already gone through one or more review rounds, it should also say:

- what changed in the latest revision
- which blockers were resolved
- which blockers remain

---

## 7. Immediate interpretation

This rule should now be used as a review lens for:

- Phase-2 Stage-04 implementation-facing handoff packages
- engineering spec packs
- bridge assessments between Phase-2 and Phase-3
- any happy-path case whose architecture looks clean but may hide realization problems

## 8. Practical stance

This rule should support:

- review → revise → review → revise

not just:

- review once → pass or fail forever

Architectural realizability is often clarified through iteration, and the repo should model that explicitly.
