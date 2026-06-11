# Stage-02 Skill Contract — requirements-analysis

## 1. Skill Goal
- This skill converts Stage-01 user-understanding outputs into a structured requirements view that can support decomposition, MVP slicing, and downstream design reasoning.
- It does **not** perform implementation slicing yet.

## 2. Inputs
- Required inputs:
  - Stage-01 structured research summary
  - Stage-01 topology profile record
  - explicit user-group boundaries
  - structured problem / opportunity list
  - business or product goal direction
- Optional inputs:
  - market context
  - competitor context
  - stakeholder context
  - Stage-01 provisional notes that remain explicitly marked
- Missing-input handling:
  - refuse or return to Stage-01 if foundational user/problem structure is missing

## 2.1 Intake and State Rules
- Default intake mode:
  - structure-first analysis
- Allowed modes:
  - Guided
  - Context dump
  - Best guess (only if upstream provisional status is explicitly preserved)
- `cannot_infer` fields:
  - confirmed user boundary if still unresolved upstream
  - confirmed business goal direction if still unresolved upstream
  - real hard constraints that were never actually confirmed
- `can_provisionally_infer` fields:
  - first-pass panorama structure
  - initial priority grouping
  - high-risk validation point candidates
- `must_validate_before_exit` fields:
  - confidence of priority ordering
  - confidence of key constraints where evidence is thin
  - confidence of main-flow assumptions if upstream user understanding is still provisional
- Provisional inference entry condition:
  - only when Stage-01 already handed off explicitly marked provisional input or the user explicitly requests a best-guess structure draft
- User review checkpoint:
  - any Stage-02 structure built on provisional assumptions must be reviewable before Stage-03 handoff
- Final gate-pass condition:
  - whole-picture structure exists, key constraints are explicit, and the output is strong enough for Stage-03 to slice without guessing the panorama

## 2.2 Workflow / Context Certainty and Agentic Boundary
- `workflow_certainty`:
  - high for the Stage-02 shell: handoff inspection, structure comparison, stress tests, evidence assembly, and Stage-03 handoff are fixed
- `context_certainty`:
  - medium and inherited from Stage-01; if Stage-01 truth is weak, Stage-02 should expose that weakness rather than mask it
- `fixed_workflow_scope`:
  - handoff inspection
  - value-loop articulation
  - structure-alternative comparison
  - stakeholder / scenario / constraint / priority evidence shape
  - review / gate / handoff marking
- `agentic_scope`:
  - topology-profile carryover check
  - value-loop articulation
  - structure-choice rationale
  - stakeholder-conflict reasoning
  - scenario-depth and priority reasoning
  - Stage-03 sliceability judgment
- `topology_profile_carryover_rule`:
  - inherit the Stage-01 `topology profile`
  - if Stage-02 structure pressure contradicts the inherited profile, return upstream or explicitly reroute with rationale instead of silently drifting
- `topology_axis_structure_rule`:
  - preserve the inherited `primary_depth_axes` in the panorama and scenario structure
  - preserve `secondary_depth_axes` where they materially affect sliceability or handoff
  - if none of the inherited axes fit the structure pressure anymore, name the new axis explicitly rather than flattening everything into one generic panorama
- `context_completion_policy`:
  - allow narrow inference only after inherited uncertainty is made explicit; if core business truth is missing, return to Stage-01 rather than invent it here
- `external_evidence_policy`:
  - use external/domain references only to strengthen structure realism, stakeholder realism, or business-process baseline; do not reopen broad product ideation
- `domain_language_preservation_rule`:
  - keep user/business terminology visible; do not flatten Stage-01 semantics into generic structure labels
  - consume the inherited `Chosen Business Thesis` before decomposing structures; if Stage-02 cannot preserve why-this-not-alternatives, substitute pressure, and proof target, return to Stage-01 rather than inventing a generic workflow shell

## 3. Execution Steps
1. Confirm the Stage-01 handoff quality and identify any remaining provisional uncertainty.
2. Build a requirements panorama / story map / equivalent structure view.
3. Separate goals, activities, tasks, and constraints.
4. Produce a structured analysis note and initial priority split.
5. Preserve unresolved uncertainty explicitly instead of silently flattening it.

## 3.1 Loop / Deep Thinking / Freeze Rule
- Default loop mode:
  - `baseline`
- `creative` mode rule:
  - allowed only when the parent Phase-1 run is explicitly in `creative` mode and Stage-01 baseline truth is already sufficient
- Allowed deepening focus:
  - value-loop articulation
  - structure alternatives
  - stakeholder conflicts
  - business-scenario depth
  - priority and constraint reasoning
  - Stage-03 sliceability
- New-round trigger:
  - only when another round is likely to create `positive_business_value_gain`
- `positive_business_value_gain` means:
  - clearer and more realistic product loop structure
  - stronger stakeholder/business-scenario realism
  - less Stage-03 truth invention
  - clearer trade-off or boundary reasoning
  - removal of fake certainty or demo-like simplification
- Forbidden loop behavior:
  - inventing a new user world that contradicts Stage-01
  - generic feature brainstorming
  - style-only rewriting
- Exit states:
  - `freeze | freeze-with-review-bound-warning | return-remediate | blocked`
- Freeze precondition:
  - Stage-03 can proceed without rebuilding the panorama, and another round is unlikely to add material positive business value

## 4. Outputs
- structured requirements analysis note
- inherited topology profile record
- requirements panorama / story-map / equivalent structure view
- key constraints list
- initial priority split
- NFR initial identification（non-functional requirements dimension scan）
  - which NFR dimensions are relevant to this product (e.g. performance, security, availability, usability, etc.)
  - current information state per dimension: `identified | suspected | not-applicable | unknown`
  - this is NOT a full quality-scenario table — it is a lightweight scan to ensure downstream awareness
  - if Stage-02b will be executed, this scan feeds into its deeper NFR analysis
  - if Stage-02b is skipped, this scan becomes the minimum viable NFR input for Phase-2

## 4.1 Output Status and Provenance Rules
- Provisional output allowed:
  - yes, but only with explicit upstream/downstream review boundaries
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
  - goal
  - inherited topology profile record
  - main activities
  - task structure
  - key constraints
  - initial priority split
  - high-risk validation point
  - nfr_initial_identification
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
  - a requirements panorama exists
  - inherited topology profile is explicit and preserved or rerouted with rationale
  - goals, activities, tasks, and constraints are distinguishable
  - at least one whole-picture structure artifact exists
  - key constraints are explicit
  - initial priority split exists
  - NFR initial identification exists with at least dimension relevance and information state
  - Stage-03 can consume the output without reconstructing the panorama from scratch
- Common defects:
  - only a list of stories/tasks exists
  - goal/constraint confusion
  - structure exists visually but not analytically
  - provisional upstream uncertainty is silently upgraded to confirmed fact
- Gate-fail situations:
  - no whole-picture structure
  - no valid structure evidence artifact
  - no key constraints list
  - no Stage-03-consumable handoff
- When provisional content cannot continue downstream:
  - if the panorama depends on unresolved `cannot_infer` fields that were never confirmed or explicitly review-bound

## 7. Boundaries
- This skill does not:
  - slice implementation into MVP releases
  - define final validation results
  - design architecture or UI deliverables
- It should hand off to:
  - `requirements-decomposition-and-mvp-slicing`

## 8. Flow Rules
- Upstream sources:
  - Stage-01 structured user-understanding outputs
- Downstream target:
  - `requirements-decomposition-and-mvp-slicing`
- Fields that must be explicit before downstream:
  - requirements panorama
  - main flow / backbone structure
  - key constraints
  - initial priority split
  - high-risk validation point
  - nfr_initial_identification (dimension relevance + information state)
- Whether provisional content may enter downstream:
  - yes, but only as explicitly labeled review-bound analysis
- Required marking when provisional content is handed off:
  - preserve `status / source / confidence / verification`
  - preserve `AI-INFERRED DRAFT — UNVERIFIED` where applicable
  - preserve assumptions_to_validate
