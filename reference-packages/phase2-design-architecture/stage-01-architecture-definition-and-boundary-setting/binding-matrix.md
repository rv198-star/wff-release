# Stage-01 Binding Matrix — architecture-definition-and-boundary-setting

## Purpose

Bind canonical Stage-01 rules into runtime files before prose drafting.

---

## 1. Bind to `skill-contract.md`

- RC-01: Stage-01 freezes architecture entry package before decomposition
- RC-02: upstream declaration-state handling is explicit
- RC-03: refusal/block without architecture-entry input
- RC-04: required system boundary output
- RC-05: inherited vs inferred constraints requirement
- RC-06: no silent complete-NFR assumption
- RC-07: NFR expansion/gap-preservation rule
- RC-08: required capability map output
- RC-09: required architecture decision output
- RC-11: provenance / confidence / verification semantics
- RC-19: Stage-02-consumable handoff package
- RC-20: provisional/review-bound truth boundary
- RC-21: boundary-level security sketch requirement
- RC-22: order-of-magnitude capacity estimation requirement

---

## 2. Bind to `stage-sop.md`

- RC-02: intake by declaration states
- RC-03: refusal/block rules
- RC-05: separate inherited vs inferred constraints during execution
- RC-07: quality-attribute expansion step
- RC-21: security-sketch step
- RC-22: capacity-estimation step
- RC-08: capability-map generation step
- RC-09: architecture-direction selection and decision rationale step
- RC-10: diagram creation step
- RC-12: TOGAF as review lens only
- RC-13: SOA-lite / SOMA / BPMN sidecar-only usage
- RC-20: keep review-bound/placeholder content explicitly marked

---

## 3. Bind to `output-template.md`

- RC-04: system boundary statement field
- RC-05: inherited constraints vs inferred constraints fields
- RC-07: quality-attribute / NFR expansion fields
- RC-21: security architecture sketch fields
- RC-22: capacity estimation fields
- RC-08: capability map field
- RC-09: key architecture decisions field
- RC-10: Mermaid diagram fields and minimum elements
- RC-11: status / source / confidence / verification / assumptions / open_questions fields
- RC-19: handoff package and downstream usage fields
- RC-20: placeholder/review-bound markers

---

## 4. Bind to `source-cards.md`

- RC-14: `ddd-reference` role
- RC-15: `software-architecture-in-practice` role
- RC-16: `diagram-expression` role
- RC-17: `iso-25010-quality-model` optional supporting role
- RC-18: `eventstorming-glossary-cheat-sheet` optional supporting role
- RC-12 / RC-13: anti-creep boundary rules for review lenses and sidecars

---

## 5. Do not bind directly into runtime prose

- older human-review-only wording from `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- broader Stage-2 source containers that belong more naturally to later substages
- speculative TOGAF / SOA governance expansions not admitted by the current Stage-2 backbone
