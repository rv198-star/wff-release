# Stage-03 Skill Contract — requirements-decomposition-and-mvp-slicing

## 1. Skill Goal
- This skill converts a structured requirements panorama into an explainable MVP boundary and delivery slices that can support validation and downstream design decisions.
- It does **not** perform validation itself.

## 2. Inputs
- Required inputs:
  - Stage-02 structured requirements analysis note
  - panorama / story-map / equivalent structure artifact
  - key constraints list
  - product / delivery goal direction
- Optional inputs:
  - initial priority split
  - review-bound provisional assumptions carried from Stage-02
  - market or stakeholder constraints if they materially affect slicing
- Missing-input handling:
  - refuse or return if no whole-picture structure exists upstream

## 2.1 Intake and State Rules
- Default intake mode:
  - slice-from-structure
- Allowed modes:
  - Guided
  - Context dump
  - Best guess (only if upstream provisional uncertainty is explicitly preserved)
- `cannot_infer` fields:
  - confirmed MVP boundary if upstream structure is still unresolved at the core level
  - confirmed hard constraints that were never actually established
  - confirmed dependency assumptions that drive slice order but are still unknown
- `can_provisionally_infer` fields:
  - first-pass slice boundaries
  - initial acceptance targets for slices
  - first-pass deferred-item grouping
- `must_validate_before_exit` fields:
  - confidence of value-vs-risk tradeoffs in slicing
  - confidence of dependency assumptions that shape slice order
  - confidence that the proposed loop is truly “minimum viable” rather than just “small enough”
  - epic decomposition coherence if stories/use cases are used downstream for traceability
  - story quality if downstream work depends on the story/use-case set as implementation intake
  - acceptance-boundary coverage if the package claims implementation-ready handoff depth
- Provisional inference entry condition:
  - only when the team explicitly accepts a provisional slicing draft on top of still-review-bound upstream structure
- User review checkpoint:
  - any provisional slice-map or MVP boundary must be reviewable before Stage-04 handoff
- Final gate-pass condition:
  - a minimum viable experience loop exists, the slice logic is explainable, and deferred items are explicit

## 3. Execution Steps
1. Confirm the Stage-02 panorama and identify any remaining review-bound uncertainty.
2. Identify the complete experience loop that the product is trying to support.
3. Cut the minimum viable experience loop.
4. Separate first slice, later slices, and deferred items.
5. Explain slice logic in terms of value, risk, and dependency.

## 4. Outputs
- MVP definition
- release slicing explanation
- structured decomposition result
- epic decomposition
- story quality gate (`INVEST`)
- requirement translation registry (`requirement_class`)
- acceptance-boundary coverage plan (`Given / When / Then + boundary_condition`)

## 4.1 Output Status and Provenance Rules
- Provisional output allowed:
  - yes, but only with explicit review-bound semantics
- Output status values:
  - `draft | provisional | review | approved`
- Required provenance labels:
  - `source: user | inferred | external | mixed`
- Required confidence / verification labels:
  - yes

## 5. Output Template
- Template path:
  - `output-template.md`
- Required fields:
  - minimum viable experience loop
  - first slice
  - later slices
  - deferred items
  - epic decomposition
  - story quality gate
  - requirement translation registry
  - acceptance-boundary coverage plan
  - slice rationale
  - key assumptions to validate
- Provenance / assumptions fields:
  - status
  - source
  - confidence
  - verification
  - assumptions_to_validate
  - what_changes_if_wrong
- Diagram fields:
  - `diagram_obligation`
  - `diagram_type`
  - `diagram_minimum_elements`
  - `fail_action`

## 6. Acceptance Criteria
- DoD:
  - a minimum viable experience loop exists
  - slice logic is explainable through value, risk, and dependency
  - first / later / deferred items are explicit
  - first-wave stories/use cases are grouped under explicit epics
  - primary story/use cases carry visible `INVEST` evaluation
  - translated requirements distinguish `functional_requirement` from governance/compliance constraints
  - acceptance-boundary coverage is explicit enough that downstream teams do not have to invent edge cases from prose
  - a valid slice-map or equivalent structure exists
  - Stage-04 can consume the output as a validation-ready review-bound package
- Common defects:
  - a smaller backlog list presented as MVP slicing
  - no visible experience loop
  - no explicit deferred items
  - no acceptance targets or dependency logic
  - stories/use cases exist but no explicit epic grouping exists
  - stories/use cases exist but no visible `INVEST` weakness/gap callout exists
  - requirement translation exists but functional requirements and governance constraints are mixed into one indistinct list
  - acceptance criteria are implied in prose only, without `Given / When / Then` or boundary coverage
  - unresolved upstream uncertainty flattened into false confidence
- Gate-fail situations:
  - no whole experience loop
  - no valid slice-map evidence
  - no explicit deferred items (without explanation)
  - no Stage-04-consumable handoff
- When provisional content cannot continue downstream:
  - if slice logic depends on unresolved `cannot_infer` fields that were never confirmed or explicitly review-bound

## 7. Boundaries
- This skill does not:
  - execute validation experiments
  - declare market proof or user proof
  - design implementation architecture
- It should hand off to:
  - `requirements-validation-and-concept-proof`

## 8. Flow Rules
- Upstream sources:
  - Stage-02 structured analysis outputs
- Downstream target:
  - `requirements-validation-and-concept-proof`
- Fields that must be explicit before downstream:
  - MVP boundary
  - slice explanation
  - deferred items
  - slice-map or equivalent structure evidence
  - key assumptions to validate
- Whether provisional content may enter downstream:
  - yes, but only as explicitly labeled review-bound slicing analysis
- Required marking when provisional content is handed off:
  - preserve `status / source / confidence / verification`
  - preserve `AI-INFERRED DRAFT — UNVERIFIED` where applicable
  - preserve assumptions_to_validate
