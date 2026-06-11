# Stage-01 SOP — architecture-definition-and-boundary-setting

## 1. Stage Positioning
- Stage name:
  - architecture-definition-and-boundary-setting
- Stage goal:
  - turn the Phase-1 handoff into a clear architecture entry package by freezing boundary, constraint posture, capability structure, and architecture direction
- Parent phase:
  - design / architecture
- Upstream dependency:
  - Phase-1 handoff package and validation conclusion
- Downstream target:
  - domain-module-service-decomposition

## 2. Start Conditions
- Required inputs:
  - Phase-1 handoff package or equivalent architecture-entry bundle
  - MVP boundary / validated scope summary
  - critical scenarios or main-flow summary
  - declaration states for critical upstream inputs, especially NFR state
- Optional inputs:
  - existing architecture notes or brownfield context
  - existing standards / platform constraints / system landscape references
  - prior sketches or architecture direction candidates
  - any known trust-boundary / identity / compliance posture clues
  - any order-of-magnitude traffic, growth, or data-volume hints
  - any known external dependency availability / ownership / feasibility clues
  - any known substitute-boundary or fallback constraints
- Pre-start checks:
  - is there a usable upstream handoff package?
  - are critical inputs explicitly declared as `present | absent | unknown | deferred` instead of left implicit?
  - is there enough scope basis to freeze a system boundary?
- Refusal rule:
  - refuse or do not start if no architecture-entry handoff exists
- Clarification expansion rule:
  - clarify scope boundary, scenario basis, and NFR declaration status before selecting architecture direction
- Enter `Blocked` when:
  - boundary or critical constraints remain too unclear to form a defensible architecture entry package
- Enter `Provisional Inference` when:
  - the team explicitly accepts review-bound boundary or constraint framing over still-incomplete upstream input

## 2.1 Workflow / Context Boundary
- `workflow_certainty`:
  - high for the Stage-01 shell; required steps, checkpoints, and handoff rules are fixed
- `context_certainty`:
  - medium and inherited from Phase-1 handoff quality plus declaration states
- `fixed_workflow_scope`:
  - declaration-state inspection, boundary freeze, constraint split, dependency scan, security/capacity posture, review/gate/handoff
- `agentic_scope`:
  - architecture-direction comparison, constraint interpretation, substitute-boundary reasoning, dependency realism, downstream assumption shaping
- `context_completion_policy`:
  - use targeted clarification and review-bound inference; if the missing truth belongs to Phase-1 product semantics, return upstream
- `external_evidence_policy`:
  - pull platform/provider/security/compliance evidence only when it materially changes boundary viability or architecture direction
- `return-upstream rule`:
  - do not hide Phase-1 business gaps behind architecture prose

## 3. Standard Execution Steps
1. Inspect the Phase-1 handoff and register declaration states for scope, constraints, NFRs, and unresolved risks.
   - 1a. For each `forbidden_assumption` in the Phase-1 handoff, explicitly register it as a Stage-01 architecture constraint or exclusion. Record: the original forbidden assumption text, how it maps to an architecture constraint, and what architecture work it prohibits or limits.
   - 1b. If any forbidden assumption is ambiguous or cannot be mapped to a concrete architecture constraint, flag it for clarification before proceeding to boundary definition (Step 2).
2. Define the system boundary, adjacent systems, and explicit out-of-scope concerns.
3. Separate inherited constraints from inferred, unknown, or deferred constraints; expand partial NFRs into architecture-facing quality-attribute structure.
4. Scan critical dependencies for realizability, substitute-boundary candidates, and explicit downstream assumption limits.
5. Produce a lightweight security architecture sketch and an order-of-magnitude capacity estimation based on current boundary truth and explicit uncertainty.
6. Build the capability map and identify candidate architecture direction.
7. Produce required Mermaid diagrams and record key architecture decisions, assumptions, open questions, and downstream usage rules.
8. Assemble the Stage-02 handoff package.

## 3.1 Intake / Clarification / Review State Flow
- `S0 Intake Received`:
  - inspect the Phase-1 handoff package and declaration states
- `S1 Clarification Active`:
  - clarify boundary ambiguity, quality-attribute gaps, and scenario basis before architecture direction is selected
- `S2 Blocked`:
  - stop if no defensible boundary or constraint posture can be formed
- `S3 Provisional Inference`:
  - allow only review-bound draft boundary/capability/architecture framing
- `S4 User Review`:
  - review provisional constraints, architecture direction, and any placeholder diagram content
- `S5 Gate Pass`:
  - pass only when Stage-02 can consume the package without re-deriving the architecture entry conditions
- `S6 Escalate`:
  - escalate if the architecture entry package cannot be stabilized under the current evidence boundary

## 3.2 Targeted Design Loop Control
- Default loop mode:
  - targeted design review
- Workflow / agentic boundary:
  - Steps 1-8 remain the fixed workflow shell; deepening may strengthen boundary, trade-off, or dependency reasoning inside that shell, but it may not skip the required declaration-state, security, or handoff checkpoints
- New-round trigger:
  - only when another round is likely to create `positive_design_value_gain`
- `positive_design_value_gain` means at least one of:
  - clearer boundary and decomposition basis
  - less downstream design-truth invention
  - stronger trade-off explicitness
  - stronger dependency/security realism
  - lower overdesign or false-certainty risk
- Forbidden loop behavior:
  - reopening business-world discovery
  - adding infrastructure complexity without evidence
  - style-only rewriting
- Freeze rule:
  - freeze only when Stage-02 can proceed without reconstructing architecture-entry truth and another round is unlikely to add material design value

## 4. Process Checkpoints
- Checkpoint 1:
  - upstream declaration states are explicit
  - all upstream forbidden_assumptions are registered as architecture constraints or exclusions
  - no forbidden_assumption is left unaddressed or silently ignored
- Checkpoint 2:
  - system boundary is explicit and scope edges are named
- Checkpoint 3:
  - inherited constraints are separated from inferred/unknown/deferred constraints
- Checkpoint 3A:
  - critical dependency realizability is explicit
  - substitute-boundary candidates or explicit no-substitute judgment exist where needed
- Checkpoint 4:
  - NFR handling is explicit and architecture-facing
- Checkpoint 4A:
  - boundary-level security posture is explicit
  - auth sequence diagram and key-management posture are explicit enough that Stage-03 does not have to invent them
- Checkpoint 4B:
  - capacity posture is explicit at order-of-magnitude level
- Checkpoint 5:
  - capability map is usable for decomposition
- Checkpoint 6:
  - architecture decisions and rationale are explicit
- Checkpoint 6A:
  - downstream `may-assume | must-not-assume` contract is explicit before Stage-02 handoff
- Checkpoint 7 (diagram gate):
  - at least one structured visual representation is present (Mermaid diagram, ASCII block diagram, or equivalent structured table view); diagram_obligation=required with no visual representation = gate fail; stage must be downgraded to `blocked`, not `provisional` or `pass`
- Fields that require confirmation or explicit review-bound status:
  - architecture direction chosen over partial evidence
  - inferred constraints that materially shape decomposition
  - placeholder diagram elements used in dry-run or verification
- Fields allowed as provisional only:
  - first-pass capability grouping
  - draft quality-attribute structure over incomplete input
  - first-pass architecture direction candidate

## 5. Referenced Method Assets
- Required cards:
  - bounded-context / system-boundary language
  - quality-attribute framing / architecture approach guidance
  - diagram expression / Mermaid evidence discipline
- Optional cards:
  - ISO 25010 quality taxonomy support
  - EventStorming discovery vocabulary support
- Boundary / anti-pattern cards:
  - do not treat TOGAF as Stage-2 backbone
  - do not let SOA-lite / SOMA / BPMN replace the current stage spine
  - do not present partial NFR input as complete
  - do not jump into decomposition/interface detail before boundary framing is stable

## 6. Output Generation Rules
- Required outputs:
  - system boundary statement
  - inherited vs inferred/unknown/deferred constraint structure
  - critical dependency realizability scan
  - first-pass realization mode
  - substitute-boundary candidates
  - security architecture sketch
  - capacity estimation
  - capability map
  - architecture direction summary
  - key architecture decisions
  - downstream assumption contract
- Minimum output rule:
  - Stage-02 must be able to start decomposition without reconstructing boundary, constraint posture, or architecture direction from scratch
- Prototype / diagram rule:
  - Mermaid is required
  - include one system-boundary/context view, one capability-map or equivalent structural view, and one auth-sequence `sequenceDiagram`
  - placeholder diagrams are allowed only in dry-run/verification when explicitly labeled
- Provenance / assumptions marking rule:
  - any provisional constraint, architecture choice, or diagram placeholder must preserve status, source, confidence, verification, assumptions, and open_questions fields
- Diagram obligation / fail action:
  - `diagram_obligation: required`
  - if boundary or capability structure cannot be expressed clearly, return to boundary clarification before passing gate

## 7. Stage Acceptance
- Minimum completion standard:
  - system boundary exists
  - constraint posture exists
  - NFR handling state exists
  - dependency realizability posture exists
  - security architecture sketch exists
  - capacity estimation exists
  - capability map exists
  - architecture direction and decisions exist
  - downstream assumption contract exists
  - Stage-02 handoff package exists
- Common failure signals:
  - product-scope restatement without architecture edges
  - silent NFR-complete assumption
  - trust-boundary concerns fully deferred with no Stage-01 sketch
  - auth posture named only as generic RBAC/SSO without an explicit auth sequence and key-management boundary
  - capacity posture omitted because scale is not yet exact
  - critical dependency realism omitted even though the architecture direction depends on it
  - capability list with no structural meaning
  - architecture direction with no rationale
  - TOGAF/SOA-lite drift into backbone replacement
  - placeholder content presented as approved architecture truth
  - upstream forbidden_assumptions not registered or silently violated in architecture decisions
- Return path:
  - return to declaration-state clarification, boundary framing, or constraint expansion as needed
- State return rule on failure:
  - go back to `S1 Clarification Active` or `S2 Blocked`
- Escalation rule:
  - escalate if no stable architecture entry package can be formed with the available handoff quality

## 8. Handoff Rules
- Handoff target:
  - domain-module-service-decomposition
- Handoff package:
  - system boundary statement
  - inherited constraints and inferred/review-bound constraints
  - upstream NFR state and handling note
  - critical dependency realizability scan
  - first-pass realization mode
  - substitute-boundary candidates
  - security architecture sketch
  - capacity estimation
  - capability map
  - architecture direction summary
  - key architecture decisions
  - downstream assumption contract
  - assumptions / open questions / review-bound items
- Handoff explanation requirement:
  - explain what is in scope, what constrains the design, why the architecture direction was chosen, and what Stage-02 must preserve or resolve next
- Provisional content in handoff:
  - allowed only if explicitly labeled
- Whether downstream may consume provisional content:
  - yes, but only as review-bound architecture input, never as silently approved truth
