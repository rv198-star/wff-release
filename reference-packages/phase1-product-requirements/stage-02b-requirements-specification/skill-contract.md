# Stage-02b Skill Contract — requirements-specification-deepening

## 1. Skill Goal
- This skill deepens the Stage-02a structural panorama into specification-grade inputs for Stage-03.
- It focuses on non-functional requirements, conceptual domain model direction, business subsystem boundaries, and information architecture direction.
- It does **not** define solution architecture, database schema, or detailed screen design.

## 2. Inputs
- Required inputs:
  - Stage-02a structural panorama
  - Stage-02a business scenario analysis
  - Stage-02a persona/context-scenario set
  - Stage-02a stakeholder profiles and key constraints
- Optional inputs:
  - engineering constraints
  - existing system context
  - compliance or data-governance inputs
- Missing-input handling:
  - refuse formal execution if Stage-02a does not contain enough scenario depth to support NFR or domain-model analysis

## 2.1 Intake and State Rules
- Default intake mode:
  - clarification-first
- Allowed modes:
  - Guided
  - Context dump
  - Best guess
- `cannot_infer` fields:
  - critical quality-attribute priorities that depend on missing business scenarios
  - domain boundaries that would be fabricated without usable Stage-02a inputs
  - real compliance, security, or tenancy constraints not present in source material
- `can_provisionally_infer` fields:
  - first-pass quality-scenario measures
  - conceptual entity relationships
  - IA direction decisions
- `must_validate_before_exit` fields:
  - NFR thresholds that materially constrain architecture
  - ambiguous entity-boundary decisions
  - subsystem boundaries that depend on missing technical or organizational evidence
- Provisional inference entry condition:
  - the team explicitly accepts review-bound specification drafting while upstream uncertainty remains visible
- User review checkpoint:
  - all provisional NFR, domain-model, and IA direction decisions must be reviewed before gate pass
- Final gate-pass condition:
  - Stage-03 can consume the outputs without re-deriving NFR priorities, domain structure, or IA direction from scratch

## 3. Execution Steps
1. Inspect Stage-02a handoff completeness and identify specification-impacting gaps.
2. Analyze NFR / quality requirements with reverse-risk reasoning and quality-scenario depth where needed.
3. Produce a conceptual domain model with entity relationships and data characteristics.
4. Derive business subsystem boundaries and IA direction decisions where they materially constrain Stage-03.
5. Apply a specification stress-test and assemble reasoning evidence.

## 4. Outputs
- NFR / quality requirements summary
- conceptual domain model direction
- business subsystem boundaries when applicable
- information architecture direction
- specification stress-test outcome

## 4.1 Output Status and Provenance Rules
- Provisional output allowed:
  - yes, but only with explicit review-bound labeling and review
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
  - NFR / quality requirements
  - domain model direction
  - business subsystem boundaries (if applicable)
  - information architecture direction
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
  - at least 3 quality attributes with material impact are analyzed
  - conceptual domain model exists with core entities and relationships
  - IA direction is explicit where it affects Stage-03 slicing or architecture
  - Stage-03 can consume the specification deepening safely
- Common defects:
  - NFR checklisting without prioritization reasoning
  - domain model reduced to feature nouns instead of business entities
  - IA direction missing or reduced to screen wishlists
  - unresolved ambiguity silently upgraded into confirmed specification truth
- Gate-fail situations:
  - no usable Stage-02a scenario depth
  - no conceptual domain model
  - no specification stress-test
  - no Stage-03-consumable handoff
- When provisional content cannot continue downstream:
  - if it would force Stage-03 to invent critical NFR or domain constraints

## 7. Boundaries
- This skill does not:
  - produce solution architecture
  - define table/column-level schema
  - replace Stage-03 MVP slicing
  - replace Stage-04 validation
- It should hand off to:
  - `requirements-decomposition-and-mvp-slicing`

## 8. Flow Rules
- Upstream sources:
  - Stage-02a structured analysis package
  - scenario and stakeholder evidence
  - key constraints
- Downstream target:
  - `requirements-decomposition-and-mvp-slicing`
- Fields that must be confirmed before downstream:
  - the existence of material quality attributes
  - the core entity/object chain
  - whether IA direction materially constrains first-slice design
- Whether provisional content may enter downstream:
  - yes, but only as explicitly marked review-bound analysis input
- Required marking when provisional content is handed off:
  - `AI-INFERRED DRAFT — UNVERIFIED`
  - source / confidence / verification
  - assumptions_to_validate
