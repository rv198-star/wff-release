# Stage-01 Dry-Run Output — informal restaurant-owner brief

## 1. Document Metadata
- document_name:
  - restaurant-owner-ai-reply-assistant-stage-01-dry-run
- stage:
  - requirements-user-research
- version:
  - v0.1-dry-run
- status:
  - `provisional`
- owner:
  - AI dry-run
- source_status:
  - `mixed`

## 2. Context and Objective
- current_problem_or_opportunity:
  - Small restaurant owners repeatedly answer similar customer questions through WeChat and lose track of repeated issues.
- document_objective:
  - Produce a Stage-01 structured user-understanding package that can be reviewed and then passed to Stage-02.
- assumptions:
  - The primary operator is likely the restaurant owner or store manager, not a dedicated customer support team.
  - Repeated questions are likely about menu items, store hours, reservation availability, delivery, and basic service issues.
  - The current reply process is mostly manual and chat-thread based.
- open_questions:
  - Are the primary users single-store owners, multi-store operators, or frontline staff?
  - What volume of repeated questions justifies tool adoption?
  - Is the main value speed, consistency, FAQ organization, or all three?
  - Are there compliance or privacy constraints around customer chat history?

## 3. Core Structured Output
- target_user_groups:
  - group:
    - small restaurant owner-manager
    - boundary:
      - operates or directly supervises customer communication for a small restaurant, likely with limited tooling and no dedicated support workflow
    - goal:
      - reduce repetitive reply effort while keeping customer communication responsive
    - pain_point:
      - repeated customer questions are answered manually and inconsistently; useful reply patterns are not accumulated into reusable knowledge
    - evidence_source:
      - user-provided informal brief + AI inference
  - group:
    - small restaurant front-desk / operations assistant
    - boundary:
      - helps answer customer questions in WeChat but may not control business rules or product decisions
    - goal:
      - reply faster with less uncertainty
    - pain_point:
      - must repeatedly reconstruct answers without a stable response base
    - evidence_source:
      - AI inference from the operating context
- first_pass_user_case_or_user_story:
  - As a small restaurant owner-manager, I want repeated customer questions in WeChat to be recognized and organized so that I can reply faster without repeatedly typing the same answers.
  - As a small restaurant staff member, I want AI-assisted suggested replies for common customer questions so that I can respond consistently even when I am busy.
- structured_problem_list:
  - problem:
      - repeated customer inquiries are handled manually every time
    object:
      - restaurant owner-manager / staff
    pain_point:
      - response effort is repetitive and not cumulative
    evidence_source:
      - user brief
  - problem:
      - useful answers are not organized into a reusable knowledge base
    object:
      - restaurant operations
    pain_point:
      - each conversation starts from scratch
    evidence_source:
      - user brief + AI inference
  - problem:
      - the current target user boundary is still partially unclear
    object:
      - solution definition process
    pain_point:
      - downstream design may drift without confirming whether the primary user is owner, manager, or staff
    evidence_source:
      - Stage-01 clarification gap
- structured_opportunity_list:
  - opportunity:
      - create AI-assisted suggested replies for recurring WeChat questions
    target_object:
      - owner-manager / frontline responder
    expected_value:
      - reduced reply time and more consistent customer communication
    evidence_source:
      - user brief
  - opportunity:
      - organize repeated questions into a reusable FAQ / response memory
    target_object:
      - small restaurant operations
    expected_value:
      - accumulated knowledge rather than repeated ad hoc chat responses
    evidence_source:
      - user brief
  - opportunity:
      - later explore whether AI should only suggest replies or also help classify/route question types
    target_object:
      - future Stage-02 structure exploration
    expected_value:
      - clearer product boundary and scope options
    evidence_source:
      - AI inference

## 3.1 Provenance / Confidence / Verification
- source:
  - `mixed`
- confidence:
  - `medium`
- verification:
  - `required`
- assumptions_to_validate:
  - Is the primary user really the owner-manager?
  - Are FAQ organization and faster replies both core value drivers?
  - Is WeChat the dominant channel or just one of several channels?
- what_changes_if_wrong:
  - If the primary user is actually frontline staff rather than owner-manager, workflow priorities and permissions will change.
  - If the strongest pain is not reply speed but knowledge consistency, the product focus may shift from chat assistance to knowledge organization.
- ai_inferred_marker:
  - `AI-INFERRED DRAFT — UNVERIFIED`

## 4. Key Judgments and Constraints
- key_judgments:
  - The brief is strong enough to identify a plausible user/problem/opportunity direction.
  - The brief is not yet strong enough to confirm user boundary and constraint details.
- key_constraints:
  - Primary user boundary remains partially unconfirmed.
  - Hard business constraints are not yet known.
- explicit_exclusions:
  - No solution architecture or implementation slicing in Stage-01.

## 5. Diagram / Structured Representation
- requires_uml_or_mermaid:
  - no hard requirement
- diagram_type:
  - `table-only`
- diagram_obligation:
  - `optional`
- diagram_minimum_elements:
  - user group, goal, pain point, evidence source are explicitly represented in structured fields
- fail_action:
  - return to clarification if the user-group structure remains too vague for Stage-02

## 6. Acceptance and Flow
- minimum_acceptance:
  - explicit user-group boundaries
  - at least one User Case / User Story draft
  - structured problem / opportunity list
  - Stage-02-consumable handoff
- handoff_to:
  - `requirements-analysis`
- handoff_package:
  - structured research summary
  - user-group boundary draft
  - first-pass User Case / User Story draft
  - structured problem list
  - structured opportunity list
  - assumptions / open questions
- downstream_usage_rule:
  - downstream may use this output only as a provisional, review-bound input until key user-boundary assumptions are confirmed

## 7. Referenced Assets
- referenced_cards:
  - direct user research posture
  - fast user-group segmentation
  - product definition boundary
- referenced_inputs:
  - self-test informal brief
