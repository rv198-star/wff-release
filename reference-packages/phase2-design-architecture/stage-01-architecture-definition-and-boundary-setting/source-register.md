# Stage-01 Source Register — architecture-definition-and-boundary-setting

## Usage

This file records the controlled source set allowed to shape Stage-01 authoring, plus why each source is included or omitted.

---

## Tier 1 — Repo policy / stage governance / hard constraints

### 1. `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- why included: freezes the Stage-2 skeleton, declaration-state requirement, NFR handling direction, and TOGAF-lens boundary in this worktree
- expected role: direct Stage-01 governance source for contract, SOP, output, and handoff behavior
- hard rule or reference: hard rule

### 2. `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- why included: defines Stage-2 substage goals and expected outputs at package level
- expected role: Stage-01 business-intent and output-shape reference
- hard rule or reference: reference

### 3. `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- why included: freezes control-artifact-first lifecycle and verification stopping criteria
- expected role: authoring lifecycle constraint
- hard rule or reference: hard rule

### 4. `docs/governance/design-time-vs-runtime-artifacts-segregation-v0.1.md`
- why included: distinguishes design-time controls from runtime package and audit evidence
- expected role: prevent Stage-01 package layering confusion
- hard rule or reference: hard rule

### 5. `templates/skill-contract.md`
- why included: provides the canonical contract skeleton
- expected role: Stage-01 contract template
- hard rule or reference: hard rule

### 6. `templates/stage-sop.md`
- why included: provides the canonical SOP skeleton
- expected role: Stage-01 SOP template
- hard rule or reference: hard rule

### 7. `templates/output-template.md`
- why included: provides the canonical output-template skeleton
- expected role: Stage-01 output template scaffold
- hard rule or reference: hard rule

### 8. `templates/handoff-checklist.md`
- why included: carries explicit handoff declaration and review-bound checks
- expected role: downstream handoff checklist reference
- hard rule or reference: hard rule

### 9. `templates/handoff-contract.md`
- why included: defines `upstream_nfr_state` and downstream handling rule
- expected role: Stage-01 handoff contract reference
- hard rule or reference: hard rule

---

## Tier 2 — Stage-2 source control authority

### 10. `docs/phases/phase-2/design-architecture-source-library-seed-v0.1.md`
- why included: defines the current Stage-2 starter source strategy and anti-overfitting constraints
- expected role: source-admission and method-boundary reference for first-pass Stage-2 authoring
- hard rule or reference: governance reference

### 11. `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- why included: establishes the intended Stage-01 business purpose and family shape
- expected role: business-level stage intent reference
- hard rule or reference: reference

---

## Tier 3 — Stage-01 method sources

### 13. `ddd-reference`
- why included: foundation source for bounded context language, boundary discipline, and strategic design vocabulary
- expected role: primary Stage-01 boundary/capability language source
- hard rule or reference: foundation method source

### 14. `software-architecture-in-practice`
- why included: foundation source for architecture views, quality attributes, architecture approaches, and review logic
- expected role: primary Stage-01 architecture direction and quality-attribute source
- hard rule or reference: foundation method source

### 15. `diagram-expression`
- why included: primary bundle for Mermaid/C4-style expression discipline and evidence-vs-handoff diagram separation
- expected role: direct source for diagram obligation and minimum expression quality
- hard rule or reference: primary-bundle method source

### 16. `iso-25010-quality-model`
- why included: optional support source when NFR input must be expanded into explicit quality-attribute structure
- expected role: supporting quality taxonomy reference
- hard rule or reference: supporting-bundle method source

### 17. `eventstorming-glossary-cheat-sheet`
- why included: optional support source for discovery vocabulary when upstream scenarios are still coarse
- expected role: supporting discovery vocabulary, not Stage-01 backbone
- hard rule or reference: supporting-bundle method source

---

## Tier 4 — Runtime package references

### 18. `reference-packages/phase1-product-requirements/stage-04-requirements-validation/`
- why included: shows the most recent Phase-1 handoff semantics into design / architecture
- expected role: structural reference only, not Stage-2 hard-rule authority
- hard rule or reference: reference-only sample

---

## Known but excluded or deferred sources

### `context-mapping`
- omission reason: valuable for relationship modeling, but Stage-01 current slice stops at boundary/capability direction and should not overfit context-map detail into decomposition-ready structure too early

### `context-map-discovery`
- omission reason: useful for brownfield reverse-engineering; keep deferred unless Stage-01 input explicitly centers on recovering architecture from an existing opaque system

### `bounded-context-canvas`
- omission reason: stronger fit for later decomposition/detailing once Stage-01 freezes architecture boundary and direction

### `context-mapper`
- omission reason: support/formalization lens only; not needed in the minimal Stage-01 runtime package

### `about-face-4`, `information-architecture-for-the-web`, `designing-interfaces`
- omission reason: interaction/IA quality support is important, but Stage-01 should not drift into interface or prototype convergence concerns

### `reactive-messaging-patterns-with-the-actor-model`, `vaughn-vernon-event-driven-architecture`, `cloudevents`, `asyncapi`, `cqrs-journey`
- omission reason: async/event/interface concerns are intentionally deferred to later Stage-2 substages unless major architecture-direction uncertainty explicitly requires them

### TOGAF / SOA-lite / SOMA / BPMN vocabulary
- omission reason: allowed only as completeness or review lens; not admitted as Stage-01 runtime backbone
