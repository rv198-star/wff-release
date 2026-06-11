# Stage-01 Merge Decisions — architecture-definition-and-boundary-setting

## Purpose

Record overlap, conflict, and precedence decisions for Stage-01 rule cards.

---

## Cluster A — Boundary / constraint / capability closure

### Included rules
- RC-01 freeze Stage-01 architecture entry package
- RC-04 system boundary statement
- RC-05 inherited vs inferred constraints
- RC-07 NFR expansion or explicit gap preservation
- RC-08 capability map
- RC-09 architecture decisions
- RC-19 decomposition-ready handoff

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- These rules form the Stage-01 closure, but each one defines a different acceptance point: scope, constraints, quality handling, structure, decision rationale, and downstream usability.

---

## Cluster B — Truth boundary and declaration discipline

### Included rules
- RC-02 explicit declaration-state consumption
- RC-03 refusal/block without architecture-entry input
- RC-06 no silent NFR-complete assumption
- RC-11 provenance / confidence / verification preservation
- RC-20 no false certainty over review-bound content

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- This is one governance chain, but intake state, refusal, NFR truth boundary, provenance marking, and anti-fake-certainty controls must remain independently testable.

---

## Cluster C — Method-lens boundaries

### Included rules
- RC-12 TOGAF lens only
- RC-13 SOA-lite / SOMA / BPMN sidecar only
- RC-14 DDD boundary language role
- RC-15 SAIP architecture-quality role
- RC-16 diagram-expression role
- RC-17 ISO 25010 optional supporting role
- RC-18 EventStorming vocabulary optional role

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- Stage-01 needs a clear difference between backbone sources, supporting sources, and review-lens-only assets; otherwise method creep becomes invisible.

---

## Conflict and precedence

Current stable precedence:

1. Repo policy / Stage-2 authoring basis / execution plan
2. Lifecycle and runtime-layering constraints
3. Stage-2 source register authority
4. Stage package business-intent draft
5. Book/bundle-derived method guidance
6. Existing Phase-1 sample wording

### Practical conclusions
- If a TOGAF-style completeness check suggests extra domains, Stage-01 may record the review finding, but it still must express outputs in the current Stage-2 backbone.
- If upstream constraints are vague, Stage-01 may expand them into quality-attribute structure, but it must not pretend the upstream handoff was already complete.
- If diagram placeholders exist in dry-run or verification, they remain placeholders and do not count as approved architecture evidence.
