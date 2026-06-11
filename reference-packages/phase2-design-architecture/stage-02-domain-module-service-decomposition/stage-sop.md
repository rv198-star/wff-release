# Stage-02 SOP — domain-module-service-decomposition

## 1. Stage Positioning
- goal: freeze domain/module/service decomposition from Stage-01 package
- upstream: Stage-01
- downstream: Stage-03

## 2. Start Conditions
- required: Stage-01 outputs + constraint/declaration-state context
- refuse: no usable Stage-01 package
- blocked: decomposition cannot be justified by boundary/capability basis
- declaration-state rule: preserve `present | absent | unknown | deferred` semantics for unresolved upstream inputs rather than flattening them

## 2.1 Workflow / Context Boundary
- `workflow_certainty`:
  - high for the Stage-02 shell; required steps, checkpoints, and handoff rules are fixed
- `context_certainty`:
  - medium and inherited from Stage-01 boundary truth plus declaration-state carryover
- `fixed_workflow_scope`:
  - boundary-grounded intake, decomposition steps, dependency/event capture, review/gate/handoff
- `agentic_scope`:
  - boundary-cut comparison, ownership reasoning, lifecycle closure, dependency/event trade-offs, Stage-03 sufficiency judgment
- `context_completion_policy`:
  - allow only narrow review-bound inference; if decomposition depends on missing upstream truth, return to Stage-01
- `external_evidence_policy`:
  - use external architecture/platform evidence only when it materially changes decomposition realism or ownership constraints
- `return-upstream rule`:
  - do not hide missing boundary truth behind neat decomposition diagrams

## 3. Standard Execution Steps
1. intake and declaration-state check
2. domain boundary and responsibility definition
3. module/service candidate split
4. dependency and collaboration mapping
5. conceptual entity relationship and domain event capture
6. decision/rationale and risk capture
7. Stage-03 handoff assembly

## 3.1 State Flow
- S0 intake → S1 clarification → S2 blocked (if basis missing)
- S3 provisional inference (review-bound only)
- S4 user review → S5 gate pass → S6 escalate

## 3.2 Targeted Design Loop Control
- Default loop mode:
  - targeted design review
- Workflow / agentic boundary:
  - Steps 1-7 remain the fixed workflow shell; deepening may strengthen ownership, lifecycle, dependency, or event reasoning inside that shell, but it may not skip the required decomposition evidence
- New-round trigger:
  - only when another round is likely to create `positive_design_value_gain`
- `positive_design_value_gain` means at least one of:
  - clearer public boundary slices
  - less Stage-03 invention of object/event truth
  - stronger ownership and lifecycle closure
  - clearer trade-off rationale
  - lower hidden coupling or false-certainty risk
- Forbidden loop behavior:
  - reopening business-world discovery
  - freezing private implementation symbols prematurely
  - style-only rewriting
- Freeze rule:
  - freeze only when Stage-03 can proceed without redoing decomposition from scratch and another round is unlikely to add material design value

## 4. Process Checkpoints
- decomposition is boundary-grounded
- responsibilities are explicit
- dependencies are explicit
- aggregate lifecycle states are owned by declared writer modules
- downstream read-only consumers do not need to mutate upstream aggregates to complete a lifecycle
- conceptual entity relationships are explicit at domain level
- domain event producers/consumers are explicit where they shape downstream storage or interfaces
- public boundary names are explicit
- internal implementation symbols are not prematurely frozen
- NFR/declaration semantics preserved
- Mermaid structure/dependency views provided (hard gate: diagram_obligation=required with no structured visual representation = gate fail; stage must be downgraded to `blocked`, not `provisional` or `pass`)

## 5. Method Assets
- required: DDD decomposition language, architecture partitioning logic, diagram expression discipline
- optional: quality taxonomy checks
- anti-patterns: decomposition by naming only, hidden ownership, ownerless lifecycle states, hidden dependency coupling

## 6. Output Rules
- required outputs: domain/module/service/dependency + conceptual ER + domain events + decisions
- diagram obligation: `required`
- provisional content must keep provenance/confidence/verification markers
- freeze public boundary-visible structure only; defer private class/method/file design
- conceptual ER and domain event content must stay domain-level; no table/column or endpoint-field descent in this stage
- lifecycle states must remain owner-realizable; read-only downstream references belong in projections or events, not hidden upstream writebacks
- declaration-state carryover must remain explicit where unresolved boundary or quality concerns still matter downstream

## 7. Stage Acceptance
- Stage-03 can start without redoing decomposition from scratch or inventing core relationships/event paths
- no hidden overlap, ownerless lifecycle state, or silent dependency assumption

## 8. Handoff Rules
- handoff to Stage-03 with decomposition package and review-bound notes
