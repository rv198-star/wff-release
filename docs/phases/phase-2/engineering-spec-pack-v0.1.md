# Engineering Spec Pack（v0.1）

## 1. Purpose

The Engineering Spec Pack is the implementation-facing convergence artifact for Phase-2.

Its purpose is to turn the currently distributed Phase-2 outputs into one design/architecture package that can drive implementation directly, rather than stopping at architecture prose and handoff semantics.

It is **not** meant to replace the four Phase-2 stage runtime packages.
It is the convergence artifact produced after Phase-2 stage outputs have already been authored and reviewed.

---

## 2. Why it is needed

Current Phase-2 outputs already cover the right design content, including:

- system boundary statement
- constraint posture
- quality attribute / NFR absorption structure
- capability map
- architecture direction / key decisions
- domain map / module map / service candidates
- responsibility matrix / collaboration map
- data model / data ownership / storage strategy
- interface contracts / interaction flow / tradeoff decisions
- architecture convergence summary
- prototype or structured delivery expression
- implementation-facing handoff package

However, these outputs still tend to land as a design handoff package.

The Engineering Spec Pack exists to make the final implementation-facing engineering specification explicit.

---

## 3. Minimum contents

### A. Architecture summary
- quick-start reading path for a new implementation team
- system boundary
- architecture direction
- key architecture decisions
- constraint posture / quality attribute posture
- thesis-driven architecture translation when Phase-1 provides a chosen thesis: proof target supported, anti-collapse boundary, proof/evidence/review data objects, and first/deferred capability rationale

### B. Decomposition and ownership
- domain map
- module map
- service candidates
- responsibility matrix
- dependency / collaboration map

### C. Data / interface / storage specification
- data sensitivity / compliance matrix (PII posture, masking/encryption, retention, audit access)
- data model summary
- data ownership map
- storage strategy
- interface contracts
- interaction flow
- tradeoff decisions

### D. Frontend Surface Architecture

#### D.1 Page Component Tree
- page-level surface structure showing which component regions exist inside each page
- use at least an indented list or table that makes `page_id -> component_region -> component_type` explicit
- every page entry must map back to a `page_id` defined in the Phase-1 Stage-05 Page Map
- the tree should make the dominant work region, support regions, and action regions visible enough for implementation planning

#### D.2 Navigation Graph
- page-to-page route and navigation structure
- may be expressed as a Mermaid flowchart or adjacency-style table
- must explicitly identify:
  - `entry_page`
  - `primary_flow`
  - `secondary_flow`
- every transition should include its trigger condition so the navigation graph preserves workflow logic instead of route names only

#### D.3 Interaction Pattern Assignment
- per-page interaction pattern assignment table
- required format:

| page_id | page_name | interaction_pattern | justification |
| --- | --- | --- | --- |
| P01 | Example Page | Dashboard-Summary | Explain why this page should use this interaction mode in the workflow. |

- allowed `interaction_pattern` values:
  - `Master-Detail`
  - `Stepper-Wizard`
  - `Dashboard-Summary`
  - `List-Kanban`
  - `Decision-Workbench`
  - `Detail-Form`
  - `Setup-Flow`
  - `Review-Board`
- not all pages may use the same interaction pattern; the assignment should reflect the business role of each page

#### D.4 State Transition Surface Map
- table describing how business state changes become visible in the UI
- required format:

| page_id | business_object | state_from | state_to | ui_feedback |
| --- | --- | --- | --- | --- |
| P01 | Example Object | draft | active | Status badge changes, list refreshes, and the next step becomes available. |

- `ui_feedback` should explain how the user sees the transition happen, for example:
  - list refresh
  - state badge/color change
  - action area unlock
  - route transition into the next workflow step

### E. Delivery expression
- prototype or structured delivery expression
- implementation constraints
- handoff notes
- `domain_event_vocabulary` and `domain_event_model_catalog` for P3 consumption, produced from `p2-architecture-event-model-driver.v1`
- `review_bound_event_gaps` for unresolved event models, each with owner, validation path, and downstream usage rule
- `Operation Source Obligation Matrix` with per-operation required P2 source types
- `Implementation Depth Obligation Matrix` with P1 value + P2 risk + implementation complexity -> `acd_level`
- `Implementation Component Catalog` defining Service / Domain / Repository / Adapter identities before Phase-3
- `Component Action Card Obligation Matrix` defining card depth, required tests, required sources, source sufficiency, and review-bound gaps
- prototype or structured delivery expression
- implementation constraints
- unresolved risks and review-bound items
- identity/auth vendor/token lifecycle and key-rotation posture when delivery realism depends on them
- observability and operational readiness (logs / metrics / alerts / SLO / rollout guardrails)

### F. Realizability review
- dependency realizability classification
- delivery-path realism judgment (`credible | constrained | weak | blocked`)
- substitute-boundary declaration if direct realization is not available
- realizability judgment (`realizable as designed | realizable only with constrained/simulated boundary | review-bound | blocked for implementation-facing handoff`)

### F.1 Extension Decision Classification
- table of significant forward-looking design choices
- every significant extension choice must be classified as exactly one of:
  - `Mainline Required`
  - `ROI-Justified Extension Boundary`
  - `Optional / Expert Lane`
- required format:

| extension_decision | source_of_pressure | lane | lightweight_boundary | first_delivery_impact | ROI_judgment |
| --- | --- | --- | --- | --- | --- |
| Example extension | P1 proof track / dependency risk / explicit business path | ROI-Justified Extension Boundary | Interface seam, schema evolution note, or deferred adapter boundary | Low, no mandatory first-release implementation | Positive because future migration cost is materially higher than current boundary cost. |

- `source_of_pressure` must come from P1 thesis, proof track, explicit business path, dependency/runtime risk, compliance risk, or delivery economics; it must not be justified by “maybe later” alone
- `lightweight_boundary` should prefer module seams, interface contracts, schema evolution posture, ADRs, event naming, or deferred adapter contracts over premature full implementation

### F.2 Extensibility ROI Review
- for each `ROI-Justified Extension Boundary`, include:
  - source of extension pressure
  - cost if the boundary is not reserved now
  - current reservation cost
  - lightweight boundary chosen
  - first-delivery impact
  - ROI judgment
- if the ROI is not clear, move the item to `Optional / Expert Lane`

### F.3 Anti-Overengineering Review
- complexity added by the design
- current mainline need
- optional-lane candidate items
- simplification decision
- explicit statement that low-ROI future-state architecture does not enter the default implementation path

### G. Implementation-facing handoff
- implementation handoff package
- onboarding summary / glossary for the next team
- downstream assumptions the implementation phase may rely on
- downstream assumptions the implementation phase must not silently infer

---

## 4. Acceptance bar

The Engineering Spec Pack should not be considered complete unless:

- Phase-2 core business deliverables are covered at an implementation-facing level
- the handoff is explicit enough for Phase-3 Stage-01 to accept as a real implementation-entry package
- review-bound items are explicitly marked and do not replace core engineering decisions
- Phase-1 thesis pressure is visibly absorbed into ADRs, service boundaries, data model, risk strategy, and capability sequencing rather than copied as context only
- realizability review is explicit enough that a clean-looking design cannot pass while remaining practically non-buildable
- compliance-sensitive schema surfaces are carried forward with explicit masking/retention/audit rules
- observability and rollout guardrails are explicit enough that Phase-3 does not invent logs, metrics, alerts, and SLOs from scratch
- Frontend Surface Architecture's Page Component Tree covers all Phase-1-defined pages
- every page has an explicit Interaction Pattern assignment, and not all pages use the same pattern
- the Navigation Graph defines at least one complete primary business-flow path
- significant forward-looking design choices are classified as `Mainline Required`, `ROI-Justified Extension Boundary`, or `Optional / Expert Lane`
- every `ROI-Justified Extension Boundary` includes a source of pressure, lightweight boundary, first-delivery impact, and ROI judgment
- anti-overengineering review makes low-ROI future-state architecture explicit and keeps it out of the default implementation path
- no required section remains as a fallback placeholder such as `- missing`, `- schema draft missing`, or other wrapper-generated incompleteness markers

This means the pack should be judged against:

- `docs/phases/phase-2/stage-2-core-business-deliverables-checklist-v0.1.md`
- the actual Phase-2 Stage-04 implementation handoff rule

---

## 5. Relationship to existing Phase-2 artifacts

The Engineering Spec Pack should be assembled from the completed Phase-2 stage outputs rather than invented from scratch.

It is therefore a **convergence pack**, not a new parallel phase system.

Recommended upstream sources:

- Phase-2 Stage-01 output
- Phase-2 Stage-02 output
- Phase-2 Stage-03 output
- Phase-2 Stage-04 output

---

## 6. What it is not

It is not:

- only a stage README summary
- only an architecture-convergence prose note
- only a source-cards or source-register projection
- already the implemented system

It is the engineering-facing design pack that implementation should consume before code-instantiated evidence is expected.

It must now also make explicit whether the design is honestly realizable in the current technical environment, rather than assuming that structural cleanliness is enough.

It is not maximum architecture. It is sufficient, realizable, ROI-extensible architecture: strong enough for first delivery, honest enough for implementation, and forward-looking only where the ROI justifies paying design cost now.

## v1.3.6.14 P2 Project-Language Handoff

P2 must preserve project language for P3 before implementation generation starts:

- domain glossary and non-lossy business terms
- bounded-context / aggregate candidates
- component responsibility and source-backed preferred domain names
- architecture style constraints that affect implementation placement
- UI/UX intent only when frontend/UI surfaces exist

P2 must not write stack-specific implementation conventions for service, repository, DTO, test double, page, or component classes. P2 provides source-backed language material and explicit missing-language gaps; P3 owns stack-aware project implementation conventions from that material plus `tech-stack-decision.yaml`.
