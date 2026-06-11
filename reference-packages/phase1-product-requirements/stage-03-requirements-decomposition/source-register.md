# Stage-03 Source Register — requirements-decomposition-and-mvp-slicing

## Usage

This file records which sources are allowed into Stage-03 authoring, why they are included, and what role they play.

---

## Tier 1 — Repo policy / stage governance / hard constraints

### 1. `docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md`
- why included: constrains how PM Skills, bundle knowledge, and governance are absorbed
- expected role: keeps Stage-03 inside the repo’s gate/refusal/handoff model
- hard rule or reference: hard rule

### 2. `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- why included: Stage-03 still needs provisional handling and review-bound semantics for unresolved upstream assumptions
- expected role: constrains slicing when upstream uncertainty survives
- hard rule or reference: hard rule

### 3. `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- why included: defines Stage-03 required outputs, entry gate, exit gate, and refusal logic
- expected role: direct gate authority for Stage-03
- hard rule or reference: hard rule

### 4. `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- why included: defines required `slice-map` evidence and minimum elements
- expected role: hard diagram-gate authority
- hard rule or reference: hard rule

### 5. `templates/skill-contract.md`
- why included: provides normalized contract structure
- expected role: Stage-03 runtime contract template
- hard rule or reference: hard rule

### 6. `templates/stage-sop.md`
- why included: provides normalized SOP structure
- expected role: Stage-03 runtime SOP template
- hard rule or reference: hard rule

### 7. `templates/output-template.md`
- why included: provides normalized output-template structure
- expected role: Stage-03 runtime output skeleton
- hard rule or reference: hard rule

---

## Tier 2 — Skill authoring official / benchmark constraints

### 8. Anthropic / Claude Skills authoring constraints
- why included: constrains structure, canonical main-file discipline, and supporting-file roles
- expected role: authoring benchmark
- hard rule or reference: structure benchmark

### 9. `skill-creator` / skill authoring discipline references
- why included: keeps Stage-03 authoring traceable and structured
- expected role: authoring benchmark
- hard rule or reference: structure benchmark

---

## Tier 3 — Domain / method sources for Stage-03

### 10. `sources/books/extracted/user-story-mapping/`
- why included: primary source for whole experience loop thinking, slicing, and story-map-guided release boundaries
- expected role: main Stage-03 slicing method source
- hard rule or reference: method source

### 11. `sources/books/extracted/effective-requirements-analysis/`
- why included: supports structured decomposition and keeps slicing tied to analyzable requirements rather than vague backlog grouping
- expected role: decomposition structure support source
- hard rule or reference: method source

### 12. `sources/books/extracted/lean-product-development/`
- why included: provides value/adaptation discipline and anti-overbuild constraints
- expected role: principle source
- hard rule or reference: principle source

### 13. `external-projects/Product-Manager-Skills/`
- why included: may support clarification and framing if Stage-02 handoff still contains review-bound uncertainty
- expected role: behavior reference only
- hard rule or reference: behavior reference

---

## Tier 4 — Current sample package

### 14. `reference-packages/phase1-product-requirements/stage-03-requirements-decomposition/*`
- why included: provides existing shape reference only
- expected role: reference-only sample
- hard rule or reference: reference-only sample
