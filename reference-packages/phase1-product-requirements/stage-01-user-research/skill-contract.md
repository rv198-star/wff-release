# Stage-01 Skill Contract — requirements-user-research

## 1. Skill Goal
- This skill converts an informal project intent, problem clue, or opportunity clue into structured user-understanding inputs that Stage-02 can consume directly.
- It does **not** define the product solution itself.

## 2. Inputs
- Required inputs:
  - initial project background
  - business opportunity description
  - at least one evidence clue from user feedback, data, observation, interview clue, or market input
- Optional inputs:
  - market context
  - competitor context
  - internal stakeholder constraints
- Missing-input handling:
  - refuse formal execution if the business opportunity is absent or the target research object is still unclear

## 2.1 Intake and State Rules
- Default intake mode:
  - clarification-first
- Allowed modes:
  - Guided
  - Context dump
  - Best guess
- `cannot_infer` fields:
  - core target-user boundary
  - high-level business goal direction
  - real organizational / budget / timeline / compliance constraints
- `can_provisionally_infer` fields:
  - proto-persona
  - first-pass User Case / User Story
  - first-pass problem / opportunity list
- `must_validate_before_exit` fields:
  - pain intensity
  - behavior confidence
  - priority confidence of opportunities
- Provisional inference entry condition:
  - the user has been told the current inputs are insufficient and explicitly asks to continue with a provisional draft
- User review checkpoint:
  - all provisional content must be reviewed before gate pass
- Final gate-pass condition:
  - Stage-01 required outputs exist and key non-inferable fields are confirmed or otherwise remain blocked

## 2.2 Workflow / Context Certainty and Agentic Boundary
- `workflow_certainty`:
  - medium-high for the stage skeleton: entry mode, clarification cadence, alternatives comparison, stress tests, evidence assembly, and handoff rules are fixed
- `context_certainty`:
  - usually low-to-medium until user evidence, scenario detail, and real-world calibration are deepened
- `fixed_workflow_scope`:
  - entry-mode selection
  - clarification stop rule
  - segment / problem / need / stress-test evidence shape
  - review / gate / handoff marking
- `agentic_scope`:
  - user-segment comparison
  - Business Exploration Arena construction
  - Chosen Business Thesis selection
  - argument-first thesis compression before PRD assembly
  - substitute pressure classification by reusable substitute class, not by named case
  - Business Proof Track derivation from the chosen thesis
  - problem / need framing choice
  - scenario and business-detail deepening
  - anti-demo review
  - real-world baseline calibration when the domain is operationally rich
- `business_proof_track_routing_rule`:
  - before deepening, build a `Business Proof Track`, not a case label or standalone topology profile
  - choose one `proof_track`:
    - `economic-decision-proof`
    - `operational-service-proof`
    - `mixed-proof`
  - record `dominant_proof_risk`, `proof_questions`, `substitute_pressure`, `proof_artifact`, and `continuation_decision`
  - record thesis quality risk when a field-complete thesis lacks real substitute pressure, continuation proof, buyer/user/operator value, or downstream architecture pressure
  - keep `topology_archetype` only as compatibility routing metadata:
    - `execution-centric`
    - `decision-centric`
    - `hybrid`
  - choose `primary_depth_axes` and optional `secondary_depth_axes`
  - record `misfit_risk_if_wrong`
- `topology_axis_rule`:
  - actual deepening pressure comes from the chosen depth axes, not the archetype name alone
  - first-wave reusable axes:
    - `operational-chain`
    - `exception-state`
    - `role-coordination`
    - `substitute-positioning`
    - `proof-evidence`
    - `buyer-budget-continuation`
  - add a new axis explicitly if none of the current axes fit well enough
- `context_completion_policy`:
  - use user evidence first; if the business world is still thin, deepen via bounded inference and explicit evidence capture rather than generic template filling
- `external_evidence_policy`:
  - when ordinary real-world practice materially affects baseline sufficiency, calibrate against external reality or explicit domain references instead of staying fully self-generated
- `domain_language_preservation_rule`:
  - preserve domain language and business semantics; do not normalize them into generic cross-domain labels

## 3. Execution Steps
1. Clarify the target user, problem context, and opportunity context.
2. Identify what is confirmed, what is missing, and what may be provisionally inferred.
3. Produce structured user-understanding outputs.
4. If provisional content exists, route it through explicit user review before handoff.

## 3.1 Loop / Deep Thinking / Freeze Rule
- Default loop mode:
  - `baseline`
- `creative` mode rule:
  - allowed only on explicit user request and only after `baseline` sufficiency exists
- Allowed deepening focus:
  - topology profile selection and rationale
  - primary user boundary
  - problem statement and need framing
  - topology-profile-matched scenario density, operating detail, decision detail, exceptions, and constraints
  - `why-this-not-that` rationale
  - Stage-02 handoff sufficiency
- New-round trigger:
  - only when another round is likely to create `positive_business_value_gain`
- `positive_business_value_gain` means:
  - more realistic ordinary baseline
  - thicker and more credible core scenarios
  - clearer `why-this-not-that` decision
  - less downstream truth invention
  - removal of demo-like omissions
- Forbidden loop behavior:
  - style-only rewriting
  - endless user-list expansion
  - generic brainstorming without decision pressure
- Exit states:
  - `freeze | freeze-with-review-bound-warning | return-remediate | blocked`
- Freeze precondition:
  - downstream no longer needs to invent critical product truth and another round is unlikely to add material positive business value

## 4. Outputs
- structured research summary
- topology profile record
- user-group boundary draft
- first-pass User Case / User Story draft
- structured problem / opportunity list

## 4.1 Output Status and Provenance Rules
- Provisional output allowed:
  - yes, but only with explicit labeling and review
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
  - target user groups
  - topology profile record
  - User Case / User Story draft
  - structured problem list
  - structured opportunity list
  - assumptions
  - open questions
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
  - user-group boundaries are explicit
  - topology profile is explicit and justified
  - at least one User Case / User Story draft exists
  - the problem / opportunity list is structured and evidence-linked
  - the outputs can be consumed by Stage-02 to build a structured requirements view
- Common defects:
  - raw research notes without structured conclusions
  - user groups described as vague generic labels
  - opportunity statements without evidence source
  - inferred content presented as confirmed fact
- Gate-fail situations:
  - no clear research object
  - no business opportunity description
  - no structured user boundary
  - no Stage-02-consumable handoff
- When provisional content cannot continue downstream:
  - if it touches `cannot_infer` fields without explicit user confirmation

## 7. Boundaries
- This skill does not:
  - define the final product solution
  - decompose requirements into implementation slices
  - validate the concept in detail
- It should hand off to:
  - `requirements-analysis`

## 8. Flow Rules
- Upstream sources:
  - initial project intent
  - opportunity input
  - research clues
- Downstream target:
  - `requirements-analysis`
- Fields that must be confirmed before downstream:
  - target user boundary
  - business opportunity direction
  - real hard constraints if any were stated
- Whether provisional content may enter downstream:
  - yes, but only if explicitly labeled and attached to review status
- Required marking when provisional content is handed off:
  - `AI-INFERRED DRAFT — UNVERIFIED`
  - source / confidence / verification
  - assumptions_to_validate
