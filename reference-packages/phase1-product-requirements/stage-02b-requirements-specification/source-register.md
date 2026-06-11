# Stage-02b Source Register — requirements-specification-deepening

## Usage

This file records which sources are allowed into Stage-02b authoring, why they are included, and what role they play.

---

## Tier 1 — Repo policy / stage governance / hard constraints

### 1. `docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md`
- why included: constrains how PM Skills, source bundles, and repo governance should be absorbed
- expected role: keeps Stage-02b inside the repo’s gate/refusal/handoff model
- hard rule or reference: hard rule

### 2. `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- why included: Stage-02b still carries provisional upstream truths and must preserve review-bound semantics
- expected role: constrains specification deepening when validation evidence is incomplete
- hard rule or reference: hard rule

### 3. `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- why included: defines Stage-02b required outputs, entry gate, exit gate, and refusal logic
- expected role: direct gate authority for Stage-02b
- hard rule or reference: hard rule

### 4. `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- why included: defines required structure evidence such as domain model / screen-object mapping support
- expected role: diagram/reference authority
- hard rule or reference: hard rule

### 5. `templates/skill-contract.md`
- why included: provides normalized contract structure
- expected role: Stage-02b runtime contract template
- hard rule or reference: hard rule

### 6. `templates/stage-sop.md`
- why included: provides normalized SOP structure
- expected role: Stage-02b runtime SOP template
- hard rule or reference: hard rule

### 7. `templates/output-template.md`
- why included: provides normalized output-template structure
- expected role: Stage-02b runtime output skeleton
- hard rule or reference: hard rule

---

## Tier 2 — Skill authoring official / benchmark constraints

### 8. Anthropic / Claude Skills authoring constraints
- why included: constrains structure, canonical main-file discipline, and supporting-file roles
- expected role: authoring benchmark
- hard rule or reference: structure benchmark

### 9. `skill-creator` / skill authoring discipline references
- why included: keeps Stage-02b authoring traceable and structured
- expected role: authoring benchmark
- hard rule or reference: structure benchmark

---

## Tier 3 — Domain / method sources for Stage-02b

### 10. `sources/books/extracted/effective-requirements-analysis/`
- why included: provides NFR analysis, conceptual domain modeling, and subsystem-boundary discipline
- expected role: primary specification-deepening source
- hard rule or reference: method source

### 11. `sources/books/extracted/information-architecture-for-the-web/`
- why included: provides organization, labeling, navigation, and findability direction at conceptual IA level
- expected role: IA direction source for Stage-02b
- hard rule or reference: method source

### 12. `sources/books/extracted/lean-product-development/`
- why included: provides anti-overbuild, value-first, and downstream handoff discipline
- expected role: principle source
- hard rule or reference: principle source

### 13. `external-projects/Product-Manager-Skills/`
- why included: may support clarification and light structuring when Stage-02a handoff is still partially review-bound
- expected role: behavior reference only
- hard rule or reference: behavior reference

---

## Tier 4 — Current sample package

### 14. `reference-packages/phase1-product-requirements/stage-02b-requirements-specification/*`
- why included: provides existing shape reference only
- expected role: reference-only sample
- hard rule or reference: reference-only sample
