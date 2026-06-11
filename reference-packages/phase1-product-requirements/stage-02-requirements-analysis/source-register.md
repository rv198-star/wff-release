# Stage-02 Source Register — requirements-analysis

## Usage

This file records which sources are allowed into Stage-02 authoring, why they are included, and what role they play.

---

## Tier 1 — Repo policy / stage governance / hard constraints

### 1. `docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md`
- why included: defines how PM Skills, book bundles, repo governance, and authoring constraints should be absorbed
- expected role: prevents Stage-02 from drifting into PM-style free discussion or book-driven over-expansion
- hard rule or reference: hard rule

### 2. `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- why included: defines intake, blocked, provisional, review, gate-pass rules
- expected role: constrains Stage-02 handling of provisional Stage-01 inputs
- hard rule or reference: hard rule

### 3. `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- why included: defines Stage-02 required outputs, entry gate, exit gate, and refusal logic
- expected role: direct gate authority for Stage-02
- hard rule or reference: hard rule

### 4. `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- why included: defines required Stage-02 structure evidence and minimum diagram elements
- expected role: hard diagram-gate authority
- hard rule or reference: hard rule

### 5. `templates/skill-contract.md`
- why included: provides normalized Stage-02 contract structure
- expected role: runtime contract template
- hard rule or reference: hard rule

### 6. `templates/stage-sop.md`
- why included: provides normalized Stage-02 SOP structure
- expected role: runtime SOP template
- hard rule or reference: hard rule

### 7. `templates/output-template.md`
- why included: provides normalized Stage-02 output-template structure
- expected role: runtime output template skeleton
- hard rule or reference: hard rule

---

## Tier 2 — Skill authoring official / benchmark constraints

### 8. Anthropic / Claude Skills authoring constraints
- why included: constrain structure, supporting-file roles, and stable runtime file organization
- expected role: keep Stage-02 package authoring disciplined
- hard rule or reference: structure benchmark

### 9. `skill-creator` / skill authoring discipline references
- why included: keeps Stage-02 traceable and supporting-file aware
- expected role: authoring benchmark
- hard rule or reference: structure benchmark

---

## Tier 3 — Domain / method sources for Stage-02

### 10. `sources/books/extracted/effective-requirements-analysis/`
- why included: provides templates, requirements-analysis structure, and analysis task discipline
- expected role: primary template/analysis source for Stage-02
- hard rule or reference: method source

### 11. `sources/books/extracted/product-demand-fit/`
- why included: preserves problem/evidence quality before analysis structure is built
- expected role: upstream evidence-quality source
- hard rule or reference: method source

### 12. `sources/books/extracted/user-story-mapping/`
- why included: provides whole-picture structure and story-map organization logic
- expected role: primary panorama/story-map source
- hard rule or reference: method source

### 13. `sources/books/extracted/lean-product-development/`
- why included: provides value/adaptation constraints and principle boundaries
- expected role: principle/governance source
- hard rule or reference: principle source

### 14. `external-projects/Product-Manager-Skills/`
- why included: provides clarification and artifact-structuring behavior where Stage-01 handoff is still partially provisional
- expected role: behavior reference, not gate authority
- hard rule or reference: behavior reference

---

## Tier 4 — Current sample package

### 15. `reference-packages/phase1-product-requirements/stage-02-requirements-analysis/*`
- why included: provides the prior shape for comparison
- expected role: shape reference only
- hard rule or reference: reference-only sample
