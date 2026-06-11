# Stage-01 Skill Contract — architecture-definition-and-boundary-setting

## 1. Skill Goal
- This skill turns the Phase-1 handoff into a decomposition-ready architecture entry package by making system boundary, constraint posture, capability structure, architecture direction, boundary-level security posture, capacity posture, and review-bound uncertainty explicit.
- It does **not** perform full domain/service decomposition, detailed interface design, or delivery prototype convergence.

## 2. Inputs
- Required inputs:
  - Phase-1 handoff package or equivalent architecture-entry bundle
  - upstream problem/opportunity and MVP boundary summary
  - key scenarios / main flow / validation conclusion relevant to architecture framing
  - declaration states for critical upstream inputs, including NFR state
- Optional inputs:
  - existing architecture context or system landscape notes
  - existing constraints register, risk register, or platform standards
  - brownfield clues that help explain current boundaries
  - external dependency availability, ownership, procurement, or feasibility clues
  - substitute-boundary or fallback-mode hints
- Missing-input handling:
  - refuse or remain blocked if no architecture-entry handoff exists
  - preserve explicit `present | absent | unknown | deferred` declarations rather than guess missing content

## 2.1 Intake and State Rules
- Default intake mode:
  - declaration-aware architecture framing
- Allowed modes:
  - Guided
  - Context dump
  - Best guess (only when review-bound assumptions stay explicit)
- `cannot_infer` fields:
  - confirmed system boundary when no upstream scope basis exists
  - confirmed architecture direction when critical constraints remain undefined
  - confirmed NFR completeness when upstream state is not `present`
  - production-realizable dependency commitments when availability / ownership / feasibility basis is absent
  - downstream implementation assumptions beyond what Stage-01 explicitly permits
- `can_provisionally_infer` fields:
  - first-pass capability grouping
  - draft architecture direction candidates
  - draft quality-attribute framing for still-partial constraints
  - boundary-level security posture sketch
  - order-of-magnitude capacity posture
  - first-pass dependency realizability scan
  - first-pass substitute-boundary candidates
  - downstream assumption contract
- `must_validate_before_exit` fields:
  - boundary statement usability for Stage-02
  - inherited vs inferred constraint separation
  - critical dependency realizability scan exists for every dependency that could collapse the chosen boundary or architecture direction
  - substitute-boundary candidates exist where realizability is partial or review-bound
  - downstream `may-assume | must-not-assume` contract is explicit
  - security trust-boundary sketch sufficiency for downstream design
  - auth sequence diagram and key-management posture sufficiency for downstream design
  - capacity posture sufficiency for downstream design
  - architecture decision rationale and downstream impact
  - diagram coverage for boundary and capability views
- Provisional inference entry condition:
  - only when the team explicitly accepts review-bound architecture framing over incomplete upstream inputs
- User review checkpoint:
  - review any provisional architecture direction, inferred constraints, or placeholder diagram content before Stage-02 handoff
- Final gate-pass condition:
  - system boundary exists, constraint posture is explicit, capability map exists, architecture decisions exist, and Stage-02 handoff package is usable

## 2.2 Workflow / Context Certainty and Agentic Boundary
- `workflow_certainty`:
  - high for the Stage-01 shell: declaration-state inspection, boundary freeze, constraint separation, dependency scan, security/capacity posture, and handoff rules are fixed
- `context_certainty`:
  - medium and inherited from Phase-1 handoff quality plus declaration states; missing business truth must stay explicit
- `fixed_workflow_scope`:
  - declaration-state registration
  - system-boundary freeze
  - inherited vs inferred constraint split
  - dependency realizability scan
  - security / capacity baseline capture
  - review / gate / handoff marking
- `agentic_scope`:
  - architecture-direction comparison
  - constraint interpretation
  - substitute-boundary reasoning
  - dependency realism judgment
  - downstream assumption contract shaping
- `context_completion_policy`:
  - prefer targeted clarification and review-bound inference; if missing truth belongs to Phase-1 business semantics, return upstream rather than invent it in architecture
- `external_evidence_policy`:
  - use platform, provider, security, compliance, or operational evidence when it materially changes boundary viability or architecture direction
- `domain_language_preservation_rule`:
  - preserve upstream domain objects and business terminology; do not rename them into generic architecture placeholders

## 3. Execution Steps
1. Inspect the Phase-1 handoff and register declaration states for all critical inputs.
2. Freeze the system boundary, adjacent systems, and explicit out-of-scope concerns.
3. Separate inherited constraints from inferred, unknown, or deferred constraints and expand partial NFRs into architecture-facing quality structure.
4. Scan critical dependencies for realizability, substitute-boundary candidates, and downstream assumption limits.
5. Produce a lightweight security architecture sketch and an order-of-magnitude capacity estimation at the same boundary-definition level.
6. Build a capability map and select a working architecture direction.
7. Record key architecture decisions, diagram evidence, assumptions, open questions, and downstream assumption rules for downstream decomposition.

## 3.1 Loop / Deep Thinking / Freeze Rule
- Default loop mode:
  - targeted design review
- `creative` mode rule:
  - not part of the default Phase-2 mainline; Stage-01 may run only bounded design loops, not open-ended business exploration
- Allowed deepening focus:
  - boundary clarity
  - architecture-direction rationale
  - dependency realizability
  - security/capacity sufficiency
  - Stage-02 handoff sufficiency
- New-round trigger:
  - only when another round is likely to create `positive_design_value_gain`
- `positive_design_value_gain` means:
  - clearer boundary and decomposition basis
  - less downstream design-truth invention
  - stronger trade-off explicitness
  - stronger dependency or security realism
  - lower overdesign or false-certainty risk
- Forbidden loop behavior:
  - reopening the business model or user world
  - adding infrastructure weight without evidence
  - style-only rewriting
- Exit states:
  - `freeze | freeze-with-review-bound-warning | return-remediate | blocked`
- Freeze precondition:
  - Stage-02 can proceed without reconstructing architecture-entry truth, and another round is unlikely to add material design value

## 4. Outputs
- system boundary statement
- constraints register for inherited / inferred / unknown / deferred items
- critical dependency realizability scan
- first-pass realization mode
- substitute-boundary candidates
- security architecture sketch
- capacity estimation
- capability map
- architecture direction summary
- key architecture decisions
- downstream assumption contract
- Stage-02 handoff package

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
  - system boundary statement
  - inherited constraints
  - inferred / unknown / deferred constraints
  - critical dependency realizability scan
  - first-pass realization mode
  - substitute-boundary candidates
  - security architecture sketch
  - capacity estimation
  - capability map
  - architecture direction
  - key architecture decisions
- Provenance / assumptions fields:
  - status
  - source
  - confidence
  - verification
  - assumptions
  - open_questions
  - downstream_review_bound_inputs
- Diagram fields:
  - `diagram_obligation`
  - `diagram_type`
  - `diagram_minimum_elements`
  - `fail_action`

## 6. Acceptance Criteria
- DoD:
  - explicit system boundary exists
  - inherited vs inferred constraint posture exists
  - NFR state is explicit and not silently flattened into certainty
  - dependency realizability scan exists for critical boundary-shaping dependencies
  - substitute-boundary candidates or explicit no-substitute judgment exist where realizability is partial
  - boundary-level security posture exists
  - order-of-magnitude capacity posture exists
  - capability map exists
  - architecture decisions with rationale exist
  - downstream assumption contract exists
  - Stage-02-consumable handoff package exists
- Common defects:
  - restating product scope without architecture boundary
  - treating `key constraints` as complete NFR baseline without evidence
  - assuming an external dependency is usable/obtainable/owned just because it sounds plausible
  - deferring all trust-boundary or sensitive-edge thinking to a later stage
  - naming RBAC / SSO without showing an authenticated sequence or key-management posture
  - skipping capacity posture entirely because exact numbers are not available yet
  - jumping into service/interface detail before boundary/capability framing is stable
  - using TOGAF/SOA-lite vocabulary as backbone instead of lens
  - presenting placeholder diagrams or review-bound assumptions as approved architecture truth
- Gate-fail situations:
  - no architecture-entry handoff
  - no explicit boundary statement
  - no capability map or equivalent structural view
  - no architecture decision rationale
  - no explicit handling of partial/absent/unknown/deferred NFR input
  - no dependency realizability scan where critical external/brownfield dependencies shape the chosen boundary
  - no boundary-level security posture
  - no auth-sequence diagram or no explicit key-management posture when authenticated actors or machine credentials exist
  - no order-of-magnitude capacity posture
  - no downstream assumption contract for what Stage-02 may and must not assume
  - diagram_obligation=required but no structured visual representation present (Mermaid diagram, ASCII block diagram, or equivalent structured table view); absence of visual representation = gate fail, stage must be downgraded to `blocked`, not `provisional` or `pass`
- When provisional content cannot continue downstream:
  - if Stage-02 would have to guess core boundary, constraint posture, architecture direction, or dependency realizability posture from unresolved `cannot_infer` fields

## 7. Boundaries
- This skill does not:
  - perform detailed module/service decomposition
  - finalize interface contracts or storage design
  - produce delivery prototype artifacts
  - adopt TOGAF, SOA-lite, SOMA, or BPMN as the Stage-2 execution backbone
- It should hand off to:
  - `domain-module-service-decomposition`

## 8. Flow Rules
- Upstream sources:
  - Phase-1 handoff package
  - validation conclusion and key scenarios from Phase-1
- Downstream target:
  - `domain-module-service-decomposition`
- Fields that must be explicit before downstream:
  - system boundary statement
  - in-scope / adjacent / out-of-scope separation
  - inherited constraints and inferred/review-bound constraints
  - upstream NFR state and handling rule
  - security architecture sketch
  - capacity estimation
  - capability map
  - architecture direction and key decisions
  - dependency realizability scan and substitute-boundary candidates
  - downstream `may-assume | must-not-assume` contract
  - assumptions and open questions
- Whether provisional content may enter downstream:
  - yes, but only as explicitly marked review-bound architecture input
- Required marking when provisional content is handed off:
  - preserve `status / source / confidence / verification`
  - preserve assumptions / open questions
  - preserve explicit `present | absent | unknown | deferred` declarations
  - preserve dependency realizability status and substitute-boundary notes
  - preserve downstream usage prohibitions, not only allowed assumptions
  - preserve placeholder markers for any not-yet-realized diagram evidence
