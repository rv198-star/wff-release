# Stage-04 Merge Decisions — requirements-validation-and-concept-proof

## Purpose

Record overlap, conflict, and precedence decisions for Stage-04 rule cards.

---

## Cluster A — Validation closure

### Included rules
- RC-04 validation conclusion
- RC-05 validation record
- RC-06 revision recommendations
- RC-07 explicit decision state

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- These rules form the Stage-04 closure, but each one defines a separate acceptance point and should remain testable.

---

## Cluster B — Validation target and evidence chain

### Included rules
- RC-02 explicit validation target
- RC-03 refusal if none exists
- RC-09 validation-flow structure
- RC-10 no fake completion over review-bound uncertainty

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- This is one chain, but target definition, refusal, evidence structure, and truth-boundary discipline are different controls.

---

## Cluster C — Source roles

### Included rules
- RC-11 user-story-mapping role
- RC-12 inspired role
- RC-13 lean-product-development role
- RC-14 validate assumptions inherited from Stage-03

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- Stage-04 needs clear distinction between learning-loop method, prototype/validation mindset, principle constraints, and inherited assumption targets.

---

## Conflict and precedence

Current stable precedence:

1. Repo policy / Phase-1 gate docs
2. Skill authoring constraints
3. Diagram evidence rubric
4. Source index / stage package definitions
5. Book-derived guidance
6. Existing sample wording

### Practical conclusions
- If a prototype exists but there is no explicit hypothesis/method/result chain, Stage-04 still fails.
- If the output gives “positive feedback” without a decision state or revision path, Stage-04 is incomplete.
- If upstream assumptions are still review-bound, Stage-04 may still proceed, but it must not present its conclusion as fully settled truth.
