# Stage-03 Merge Decisions — requirements-decomposition-and-mvp-slicing

## Purpose

Record overlap, conflict, and precedence decisions for Stage-03 rule cards.

---

## Cluster A — MVP closure

### Included rules
- RC-04 MVP definition
- RC-05 release slicing explanation
- RC-06 minimum viable experience loop
- RC-07 explainable slicing logic
- RC-08 explicit deferred items

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- These rules form the Stage-03 closure, but each one defines a different acceptance point and should remain separately testable.

---

## Cluster B — Slice-map evidence gate

### Included rules
- RC-09 required slice-map gate
- RC-10 minimum slice-map elements
- RC-11 fail if only a phased list exists

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- This is one gate chain, but the obligation, minimum elements, and failure signal must remain separate for verification.

---

## Cluster C — Upstream uncertainty and downstream validation connection

### Included rules
- RC-12 preserve provisional uncertainty
- RC-16 carry forward high-risk validation point
- RC-17 do not pretend validation already happened

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- These govern the Stage-03 / Stage-04 seam and must not collapse into a vague “remember uncertainty” rule.

---

## Cluster D — Source roles

### Included rules
- RC-13 user-story-mapping role
- RC-14 effective-requirements-analysis role
- RC-15 lean-product-development role

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- Stage-03 needs clear distinction between slicing method, decomposition support, and principle constraints.

---

## Conflict and precedence

Current stable precedence:

1. Repo policy / Phase-1 gate docs
2. Diagram evidence rubric
3. Skill authoring constraints
4. Source index / stage package definitions
5. Book-derived guidance
6. Existing sample wording

### Practical conclusions
- If a sample file implies diagram is only recommended, gate docs and diagram rubric still make `slice-map` required.
- If slicing logic ignores deferred items, Stage-03 fails even if the MVP label looks plausible.
- If the output looks like a phased backlog but lacks slice boundaries and acceptance targets, it fails the Stage-03 structure gate.
