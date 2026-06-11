# Stage-02 Merge Decisions — requirements-analysis

## Purpose

Record overlap, conflict, and precedence decisions for Stage-02 rule cards.

---

## Cluster A — Structural output closure

### Included rules
- RC-04 panorama/story-map output
- RC-05 key constraints list
- RC-06 initial priority split
- RC-07 goal→activity→task→constraint walk-through

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- Together these form the Stage-02 output closure
- But they define different acceptance points and must stay separately testable

---

## Cluster B — Diagram evidence gate

### Included rules
- RC-09 required diagram gate
- RC-10 required structure artifact type
- RC-11 minimum `story-map` elements
- RC-12 return/fail action when structure evidence is absent
- RC-20 high-risk point visibility

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- This is one governance chain, but each rule controls a different point: obligation, artifact type, minimum elements, fail path, downstream validation visibility

---

## Cluster C — Upstream provisional handling

### Included rules
- RC-02 Stage-01 structured input requirement
- RC-03 refusal if research conclusions are missing
- RC-13 preserve Stage-01 provisional uncertainty
- RC-14 Stage-02 may only consume provisional input as review-bound input

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- Stage-02 has to distinguish missing-input refusal from provisional-input handling; merging these would blur the boundary

---

## Cluster D — Source-bundle roles

### Included rules
- RC-15 effective-requirements-analysis role
- RC-16 user-story-mapping role
- RC-17 product-demand-fit role
- RC-18 lean-product-development role

### Decision
- KEEP-SEPARATE-BUT-LINKED

### Reason
- We need both bundle selection and bundle role clarity; Stage-02 will overfit one source if this is collapsed too early

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
- If a sample file says “diagram recommended” but gate docs say required, gate docs win.
- If Stage-01 hands off provisional content, Stage-02 must preserve that uncertainty until review clears it.
- If a story map exists but does not satisfy minimum elements, Stage-02 still fails the diagram gate.
