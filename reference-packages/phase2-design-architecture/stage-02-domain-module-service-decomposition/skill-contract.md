# Stage-02 Skill Contract — domain-module-service-decomposition

## 1. Skill Goal
- Convert Stage-01 boundary/capability outputs into decomposition-ready domain/module/service structure with explicit responsibilities, dependencies, and rationale.

## 2. Inputs
- Required:
  - Stage-01 handoff package
  - Stage-01 constraints and architecture decisions
  - explicit declaration states for critical unresolved inputs, including `present | absent | unknown | deferred` where relevant
- Optional:
  - legacy/system landscape context
  - team ownership constraints
- Missing-input handling:
  - refuse or block when Stage-01 package is absent or unusable

## 2.1 Intake and State Rules
- `cannot_infer`:
  - confirmed domain boundaries without boundary basis
  - final ownership model without collaboration constraints
  - aggregate lifecycle states that require a non-owning downstream module to write them
  - final class names, service implementation names, or internal method names without implementation-stage basis
- `can_provisionally_infer`:
  - first-pass module/service grouping
  - initial dependency direction
  - conceptual entity relationships and aggregate adjacency
  - domain event candidates at business-semantics level
- `must_validate_before_exit`:
  - decomposition usable for Stage-03
  - dependency map coherence
  - conceptual entity relationships are explicit enough for downstream storage/interface design
  - domain event catalog is explicit enough for downstream interaction and persistence planning
  - aggregate lifecycle states are owner-realizable and do not require downstream read-only consumers to mutate upstream truth
  - rationale completeness
  - declaration-state and NFR carryover remains explicit

## 2.2 Workflow / Context Certainty and Agentic Boundary
- `workflow_certainty`:
  - high for the Stage-02 shell: decomposition steps, ownership rules, dependency/event capture, and Stage-03 handoff are fixed
- `context_certainty`:
  - medium and inherited from Stage-01 boundary truth plus declaration-state carryover
- `fixed_workflow_scope`:
  - boundary-grounded intake
  - domain/module/service split
  - dependency/collaboration mapping
  - conceptual ER and domain-event capture
  - review / gate / handoff marking
- `agentic_scope`:
  - boundary-cut comparison
  - responsibility and ownership reasoning
  - collaboration trade-offs
  - event and lifecycle interpretation
  - Stage-03 design-sufficiency judgment
- `context_completion_policy`:
  - allow only narrow review-bound inference; if decomposition depends on missing boundary or business truth, return to Stage-01 rather than invent it here
- `external_evidence_policy`:
  - use external architecture or platform evidence only when it materially changes decomposition realism or ownership constraints
- `domain_language_preservation_rule`:
  - keep domain objects, events, and public boundary names readable and domain-native; do not collapse them into vague technical aliases

## 3. Execution Steps
1. Read Stage-01 boundary/capability outputs.
2. Define domain boundaries and responsibilities.
3. Derive module boundaries and service candidates.
4. Map dependencies and collaboration flow.
5. Capture conceptual entity relationships and domain event flow at domain level.
6. Record decomposition decisions, assumptions, and unresolved risks.

## 3.1 Loop / Deep Thinking / Freeze Rule
- Default loop mode:
  - targeted design review
- `creative` mode rule:
  - not part of the default Phase-2 mainline; use bounded decomposition loops only
- Allowed deepening focus:
  - boundary-cut rationale
  - responsibility and ownership closure
  - dependency/collaboration realism
  - domain-event and lifecycle coherence
  - Stage-03 handoff sufficiency
- New-round trigger:
  - only when another round is likely to create `positive_design_value_gain`
- `positive_design_value_gain` means:
  - clearer public boundary slices
  - less Stage-03 invention of object/event truth
  - stronger ownership and lifecycle closure
  - clearer trade-off rationale
  - lower hidden coupling or false-certainty risk
- Forbidden loop behavior:
  - reopening business-world discovery
  - freezing internal implementation symbols prematurely
  - style-only rewriting
- Exit states:
  - `freeze | freeze-with-review-bound-warning | return-remediate | blocked`
- Freeze precondition:
  - Stage-03 can proceed without redoing decomposition from scratch, and another round is unlikely to add material design value

## 4. Outputs
- domain map
- module map
- service candidate set
- responsibility matrix
- lifecycle ownership closure notes
- dependency/collaboration map
- conceptual entity relationship diagram
- domain event catalog
- decomposition decisions and rationale

## 5. Output Template
- `output-template.md`
- required fields: domain/module/service/dependency views, responsibility matrix, lifecycle ownership closure, conceptual ER coverage, domain event catalog, rationale, risk notes, declaration-state carryover

## 6. Acceptance Criteria
- decomposition is traceable to Stage-01
- responsibilities are explicit and non-overlapping
- dependencies are explicit and Stage-03-consumable
- Stage-03 does not need to invent core object relationships or event flow from scratch
- aggregate lifecycle states are closed by declared owners rather than by hidden downstream writeback
- decomposition freezes public boundary slices and names, not private implementation symbols
- unresolved/provisional items are clearly marked
- upstream declaration-state semantics remain explicit instead of being guessed over
- at least one structured visual representation is present (Mermaid diagram, ASCII block diagram, or equivalent structured table view); if diagram_obligation=required and no visual representation exists, stage status must be downgraded to `blocked`, not `provisional` or `pass`

## 7. Boundaries
- no final data model or API contract design
- no physical schema, table/column design, or transport-level endpoint definition
- no transport-binding event contract masquerading as domain decomposition
- no ownerless or read-only-consumer-driven aggregate lifecycle states
- no mandatory class, package, file, or method naming for internal implementation
- no prototype-convergence activity
- TOGAF/SOA-lite/SOMA/BPMN remain lens-only sidecars

## 8. Flow Rules
- handoff target: `data-storage-and-interface-design`
- downstream may consume provisional items only when explicitly marked review-bound
- carry forward `present | absent | unknown | deferred` semantics when Stage-03 would otherwise inherit ambiguity silently
