# Phase-1 PRD Main Document Template（v0.1）

## 1. Purpose

This template defines the **main PRD document** that Phase-1 should ultimately converge into.

It is derived from:

- the structural clarity of PM Skills PRD template
- the Phase-1 Unified Product Pack semantics in this repo
- the current Stage-01 / Stage-02a / Stage-02b / Stage-03 / Stage-04 canonical outputs

Its role is to turn distributed Phase-1 outputs into:

> **one complete PRD main document for product, design, architecture, and review consumption**

This template does **not** replace Stage-01..04 outputs.
Those remain the working and evidentiary artifacts.

This template defines the final converged document.

The final converged PRD should preserve deep product/design/architecture content, but it should not be forced to inline every runtime trace from stage compilation or deep-loop execution. Those traces belong in the convergence evidence memo when they are useful for audit but noisy for downstream consumers.

It also defines the minimum depth bar for that converged document.
A PRD that merely mirrors stage fields or stays at summary-bullet depth should be treated as an incomplete convergence result, not a successful main document.
A PRD that becomes materially shorter than the structured input by compressing away high-value business detail should also be treated as incomplete unless it provides demonstrably denser synthesis.

---

## 2. Relationship to existing Phase-1 artifacts

### Stage outputs
- remain the working-stage artifacts
- preserve stage-local reasoning, assumptions, and handoff logic

### Unified Product Pack
- remains the Phase-1 convergence concept
- but should now be understood as converging **into** this PRD main document rather than stopping at a lightweight summary object

### Execution report
- remains the acceptance / warning / review-bound audit layer
- it does not replace the PRD main document

### Convergence evidence memo
- preserves analysis delta ledger and runtime trace residue
- should exist beside the final PRD when the assembled draft contains heavy audit/runtime material
- allows the final PRD to stay downstream-consumable without deleting audit evidence

---

## 3. Template

```markdown
# [Product / Initiative Name] PRD

## 0. Document Metadata
- document_name:
- version:
- status:
  - `draft | provisional | review | approved`
- delivery_profile:
  - `review-bound-starter-pack | implementation-ready-prd`
- source_status:
  - `user-confirmed | provisional | mixed`
- intended_consumers:
  - `product-review | design | architecture | mixed`
- ai_inferred_marker:
  - `AI-INFERRED DRAFT — UNVERIFIED` (required if provisional content exists)

## 1. Executive Summary
- One-paragraph overview of:
  - target user
  - core problem
  - proposed first-wave solution direction
  - expected product/business impact

Anti-compression rule:
- this section may compress, but later sections must re-expand the critical business detail rather than leaving the whole document summary-like

## 2. Problem Statement
- Final problem statement
- Who has this problem?
- Why is it painful?
- Why now?
- Evidence status:
  - what is user-confirmed
  - what is review-bound / inferred
- Problem-mechanism explanation:
  - what changed in the world or workflow that makes this problem newly important?
  - why existing alternatives are insufficient

Depth rule:
- this section must read as a coherent problem narrative, not just a list of pain points

## 3. Target Users & Key Roles
- Primary target user boundary
  - chosen segment and why-this-not-that rationale
  - cost-willingness signal (what would this user sacrifice?)
- Secondary/supporting roles
- Out-of-scope users (with explicit exclusion rationale)
- Jobs-to-be-done / user goals
- Use Case / User Story
- Role interaction note:
  - how do the primary and supporting roles interact in the first-wave loop?

### Persona Profiles
For each primary persona:
- name / archetype label
- role and context
- key goals
- key pain points
- behavioral characteristics relevant to product
- context scenario (a day-in-the-life or workflow snapshot)
- key-path scenario (the primary interaction path with the product)
- design requirements implied by this persona

Depth rule:
- this section must make the user boundary and role logic sufficiently explicit that design can start journey and screen framing without inventing a different primary user

## 4. Stakeholder Analysis
- Key stakeholders:
  - direct users
  - indirect users (affected by product outputs)
  - decision makers (budget / adoption / cancellation authority)
  - influencers (champions, detractors, domain experts)
  - regulators / compliance bodies (if applicable)
- For each key stakeholder:
  - role and relationship to the product
  - primary interest / concern
  - success criteria
  - potential resistance or adoption barrier
  - influence level and engagement approach
- Adoption chain analysis:
  - who must adopt first?
  - what unlocks the next stakeholder?
  - where is the adoption chain most fragile?
- Stakeholder tension note:
  - where do stakeholder incentives or concerns conflict?

## 5. Strategic Context
- Current opportunity / why now
- Current market / business framing
- Competitive or adjacent alternatives (if relevant)
- Chosen need framing
- Why-this-not-that summary (which framings were considered and rejected)
- Competitive Landscape Summary:
  - preserve at least 3 comparison targets or alternative classes when market comparison materially affects positioning
  - include pricing model signal, capability-coverage contrast, and evidence status
  - if exact competitor names are not yet confirmed, keep alternative classes explicit and mark vendor-level detail as review-bound instead of dropping the section
- Context pressure note:
  - what strategic pressure makes this framing worth prioritizing now?

## 6. Product Direction Overview
- Product direction summary
- Chosen category / positioning direction
- First-wave value proposition
- What this product is not
- Product mechanism summary:
  - in 1-2 short paragraphs, explain what the product actually does in the user's loop, not just how it is positioned
- Capability recompilation note:
  - recompile the most important source capabilities/features into product-module responsibility language
  - do not collapse all meaningful product capability detail into one generic workflow paragraph

Depth rule:
- this section must be strong enough that a reader can explain the product to design/architecture without falling back to generic feature names

## 7. Business Scenarios
For each key business scenario (at least 3):
- scenario name
- trigger / starting condition
- key actor(s)
- scenario flow (step-by-step or narrative)
- challenge / friction point in this scenario
- proposed solution direction for this scenario
- success measure for this scenario
- evidence status: `confirmed | provisional | inferred`
- scenario consequence:
  - what goes wrong if the product does not handle this scenario well?

Depth rule:
- each scenario must be concrete enough that downstream can derive workflow implications from it

## 8. Requirements Structure
- Goal
- Chosen panorama structure and structure rationale
- Value loop articulation (what does the user do, get back, why return?)
- Backbone flow / main activities
- Key constraints (stress-tested)
- Initial priority split
- High-risk validation points
- Consumer translation:
  - what design should preserve from this structure
  - what architecture should preserve from this structure
- Workflow/state detail note:
  - preserve or recompile the key step-by-step workflow and state-change logic from the source package
- implementation-ready supplement (required when `delivery_profile=implementation-ready-prd`):
  - `Business Process Decomposition` table with at least:
    - actor
    - trigger
    - preconditions
    - system behavior
    - outputs
    - postconditions
  - `Exception and Failure Flows` with at least 3 explicit exception paths and handling strategy

### Diagram (recommended)
- Mermaid/UML for:
  - backbone activity flow
  - activity relationships

## 9. NFR / Quality Requirements
(from Stage-02b — include only if Stage-02b was executed)
- Key quality attributes and why they matter for this product:
  - for each key attribute:
    - attribute name (security / reliability / usability / performance / maintainability / portability)
    - relevance to product
    - reverse-risk assessment (if this fails, worst realistic consequence)
    - affected business scenarios
- Quality-scenario tables (for key attributes):
  - stimulus → environment → response → measure
- NFR MVP impact:
  - which NFRs constrain what must be in the first slice
  - which NFRs can be relaxed for MVP
- Architecture consequence:
  - what architectural pressure does each top NFR create?
- Metric interpretation note:
  - if the source package contains metric definitions or scoring logic, recompile them here or in an explicitly referenced adjacent section; do not silently drop them

## 10. Domain Model
(from Stage-02b — include only if Stage-02b was executed)
- Core business entities (at least 5) with descriptions
- Deferred attribution / conversion seam:
  - if source capabilities include attribution / conversion / UTM / funnel / cross-device language, preserve an explicit seam instead of silently dropping it
  - name the future entity/interface or reserved hook, even if MVP does not implement it yet
- Key relationships (association, composition, generalization) with cardinality
- Key data characteristics:
  - data window / freshness
  - data sources
  - data sensitivity
  - data volume estimates (order of magnitude)
- Business subsystem boundaries (if applicable):
  - subsystem groupings and rationale
  - key interfaces between subsystems (why they communicate, what flows, what constraints apply)
- Object lifecycle note:
  - for the most important entities, what state or transition matters to downstream design/architecture?

### Diagram (required if domain model is present)
- Mermaid ER diagram for conceptual domain model
- Optional: business subsystem boundary diagram

## 11. Information Architecture Direction
(from Stage-02b — include only if Stage-02b was executed)
- Organization strategy: how information is structured (exact / ambiguous / faceted classification; hierarchical / flat / hybrid; primary axis)
- Labeling direction: user language vs. system language; key labeling decisions
- Navigation strategy direction: global / local / contextual navigation needs
- IA decisions that constrain architecture or MVP scope
- Screen/module consequence:
  - which IA decisions are likely to shape first-wave product surfaces?
- implementation-ready supplement (required when `delivery_profile=implementation-ready-prd`):
  - `IA Spec Matrix` that maps:
    - screen/module
    - primary actor
    - required information objects
    - entry conditions
    - exit actions
    - downstream dependency

## 12. MVP Definition & Scope
- Complete experience loop
- Minimum viable experience loop
- Chosen slice strategy and why-this-slice-not-that rationale
- First slice
- Later slices
- Deferred items (with honesty check: why deferred, what would falsely make MVP look complete)
- Source Feature Carryover Ledger:
  - classify important detailed source features into `first-wave abstraction | later slice | deferred seam | explicit out-of-scope`
  - do not allow meaningful source capabilities to disappear silently during slicing
- NFR-aware slicing impact (which NFRs forced capabilities into first slice; which relaxed for MVP)
- Domain dependency impact on slice ordering (if applicable)
- MVP boundary explanation:
  - what is the smallest believable first-wave promise?
  - what would make the product look complete while actually remaining misleading?
- Source-scope preservation note:
  - preserve or recompile explicit in-scope / out-of-scope / later / deferred distinctions from the source package
- implementation-ready supplement (required when `delivery_profile=implementation-ready-prd`):
  - `Operational Flow Specification`:
    - main path steps with actor-action and system-response pairs
  - `State Machine and Transition Rules`:
    - named states and explicit transitions
    - transition guards and failure exits
  - `Acceptance Criteria`:
    - machine-checkable AC items (`AC-1`, `AC-2`, ...)
    - each AC maps to one epic, one user story/use case, and one flow step
    - distinguish `anchor` ACs (critical path / high-risk path) from `supporting` ACs where the case genuinely benefits from that split
    - express each AC in `Given | When | Then` form
    - `anchor` ACs should also carry `expected_outcome` or an equivalent observable success signal
    - include explicit `boundary_condition_type` and `boundary_case`
    - boundary-condition coverage must include more than the happy path; permission, missing-input, invalid-state, threshold, or recovery edges should be visible where relevant
    - the converged PRD must preserve this as a machine-readable matrix or equivalent structured block; do not collapse it into prose-only AC bullets

Depth rule:
- this section must be strong enough that product and architecture can discuss first-wave scope without reconstructing the slice logic from stage artifacts

### Diagram (recommended)
- Mermaid/UML for:
  - slice map
  - activity-to-slice relationship
  - Use Case relationship if useful

## 13. Validation Strategy & Current Conclusion
- Validation target / hypothesis (exact assumption being tested)
  - what changes if positive
  - what changes if negative
- Validation method and why-this-method-not-that rationale
- Prototype fidelity and rationale (`paper-sketch | clickable | coded | none`)
- Pricing Validation Design:
  - pricing / packaging hypotheses to probe
  - evidence collection method
  - pass / fail interpretation
  - if willingness-to-pay is still review-bound, preserve the experiment design rather than silently omitting commercial validation
  - if buyer/budget truth matters, preserve an explicit chain table for:
    - `pain_holder`
    - `continuation_owner`
    - `spend_at_risk`
    - `proof_artifact_for_continue`
    - `continuation_signal`
- Current feedback / signal state
- Three-dimensional validation assessment:
  - value dimension: `validated | partially-validated | not-validated | not-tested`
  - usability dimension: `validated | partially-validated | not-validated | not-tested`
  - feasibility dimension: `validated | partially-validated | not-validated | not-tested`
  - gaps note for any dimension marked `not-tested`
- Evidence state honesty:
  - what is design-time inference
  - what is real evidence
  - what remains unknown
- Decision state (`Go | No-Go | Revise`) with explicit rationale
- Revision recommendations
- What downstream must NOT assume
- Evidence weakness consequence:
  - what specifically remains too weak for direct downstream commitment?
- Threshold preservation note:
  - if the source package contains validation thresholds, success signals, or decision conditions, preserve or recompile them rather than replacing them with generic "validate later" language

### Diagram (optional)
- Mermaid/UML for:
  - validation flow
  - hypothesis → method → signal → result → decision

## 14. User Stories, Use Cases, and Requirements
- Epic Decomposition
  - `Epic Registry`:
    - `epic_id | epic_name | user_value | included_user_stories_or_use_cases | downstream_architecture_pressure`
- Primary User Story / User Case
- Supporting user scenarios
- Story Quality Gate
  - evaluate primary story and supporting use cases with `INVEST`
  - preferred matrix:
    - `story_or_use_case | epic_id | independent | negotiable | valuable | estimable | small | testable | risk_or_note`
  - the converged PRD must preserve `Story Quality Gate` as its own explicit section rather than compressing it into a prose summary
- Core requirements implied by Stage-01..03 outputs
  - classify each requirement as:
    - `functional_requirement`
    - `governance_constraint`
    - `quality_or_compliance_constraint`
- Recommendation Payload Contract:
  - if the source package contains detailed recommendation outputs, recompile them into an explicit payload contract instead of generic recommendation language
- Edge cases / constraints if already visible at Phase-1 depth
- Requirement translation note:
  - translate the user stories/use cases into the most important first-wave product requirements in direct language
- Capability preservation note:
  - if the source package contains detailed capability definitions, page-level functions, or priority groups, recompile the most decision-relevant parts here or in §6/§12 rather than dropping them
- implementation-ready supplement (required when `delivery_profile=implementation-ready-prd`):
  - `Requirement Trace Matrix`:
    - epic -> story/use case -> requirement (`requirement_class`) -> acceptance criteria -> boundary condition -> related flow step
- `Business Value Signal Registry` (required for v1.2.3 ACD handoff):
  - columns: `value_signal_id | upstream_trace_id | business_value_weight | business_value_reason | anti_demo_risk | core_success_path | downstream_depth_hint | evidence_or_review_bound`
  - allowed values: `business_value_weight=BV0|BV1|BV2|BV3`, `anti_demo_risk=low|medium|high|critical`, `core_success_path=yes|no`, `downstream_depth_hint=none|standard|deep|critical`
  - every non-review-bound row must bind at least one `P1-UC-*`, `P1-REQ-*`, or `P1-AC-*` trace id
  - P1 signals are business inputs for P2 ACD synthesis; P1 must not assign Service/Domain/Repository components, and P3 must not invent missing rows

## 15. Out of Scope
- Explicit exclusions
- Deferred items
- Things intentionally not promised in first-wave delivery
- Honesty note:
  - what tempting interpretation should readers explicitly avoid?

## 16. Dependencies, Risks, and Review-Bound Truth
- Product/business risks
- Key unresolved truths (classified by unresolved-truth handling rules)
- What downstream must not assume
- What remains review-bound
- Risk consequence note:
  - if each top unresolved truth is wrong, what changes in product/design/architecture?

## 17. Key Decision Rationale Summary
This section consolidates the major why-this-not-that decisions from across stages:
- user boundary choice rationale (from Stage-01)
- need framing choice rationale (from Stage-01)
- structure choice rationale (from Stage-02a)
- NFR priority rationale (from Stage-02b, if present)
- slice strategy rationale (from Stage-03)
- validation method rationale (from Stage-04)

## 18. Handoff to Design / Architecture
- Handoff type
- Design/architecture-consumable summary
- NFR state (`present-with-quality-scenarios | present-identification-only | absent | deferred`)
- Domain model state (`present-with-ER | absent | deferred`)
- Handoff package references
- Design may safely start:
  - (what design work can begin now without inventing core truth?)
- Architecture may safely start:
  - (what architecture work can begin now without inventing core truth?)
- Deferred seam note:
  - if attribution / conversion is deferred, state what seam or extension boundary architecture must still preserve now
- Must not assume:
  - (explicit forbidden downstream assumptions)
- Next validation / remediation:
  - (what should happen before freezing deeper downstream decisions?)

Depth rule:
- this section must function as an actual handoff note, not only a status declaration

## 19. Acceptance & Status
- Current Phase-1 status
- Admission reading:
  - `PASS | PASS with constrained/review-bound conditions | BLOCKED`
- Why not clean-pass (if applicable)
- Review warnings / pending external confirmation:
  - which subjects remain warning-bearing even though the PRD itself is mature enough to pass
  - what external confirmation is still missing
  - what safe current use is allowed
  - what stronger commitment is still blocked
- Dual-read note:
  - separate `document maturity` from `business completeness`
- Execution report reference
- convergence_smoke_test:
  - checklist_reference: `docs/phases/phase-1/phase-1-prd-convergence-smoke-test-v0.1.md`
  - quick_checks_result: `all-pass | has-fails`
  - depth_probes_result: `all-pass | soft-fails-only | has-hard-fails`
  - convergence_verdict: `approved | conditional | blocked`
  - smoke_test_notes: (any notes from the smoke test reviewer)

## 20. Source Artifacts
- Stage-01 reference
- Stage-02a reference
- Stage-02b reference (if executed)
- Stage-03 reference
- Stage-04 reference
- Execution report reference
- artifact_traceability_rules:
  - convention_reference: `docs/governance/artifact-traceability-minimum-rules-v0.1.md`
  - prd_artifact_id: (this PRD's artifact ID, e.g. `P1-PRD-001`)
  - source_artifacts_with_ids:
    - (list each Stage output referenced in this PRD, with its artifact ID)
    - example: `P1-S01-OUT-001 — Stage-01 User Research Output`
    - example: `P1-S02a-OUT-001 — Stage-02a Requirements Analysis Output`
    - example: `P1-S04-HND-001 — Stage-04 Handoff Package`
  - traceability_completeness: `full | partial | minimal`
  - traceability_gaps: (any referenced artifacts that lack IDs or cannot be resolved)

## 20.5 zh-CN Audit Mirror Rule
- If the PRD is intended for human review, also emit `geo-rpd-main-document.zh-CN.md`.
- The Chinese file is an audit mirror, not the canonical runtime artifact.
- Keep critical domain objects, state labels, and handoff terminology in bilingual form.
- If the English and Chinese files drift semantically, fix the English canonical source and regenerate the mirror.

## 21. Analysis Delta Ledger
For each material decision/trade-off introduced during PRD deep-compilation, add one delta entry.

Required fields per delta:
- `source_evidence`:
  - exact source statement(s), section(s), or artifact(s) used as input
- `analytical_inference`:
  - what inference was made from source evidence and why
- `decision_or_tradeoff`:
  - what concrete decision was made (or rejected) and the trade-off
- `downstream_impact`:
  - explicit impact to product/design/architecture/handoff
- `category`:
  - one of:
    - `segment_user`
    - `capability_module`
    - `metrics_measurement`
    - `mvp_slice_scope`
    - `validation`
    - `architecture_design`

Format:
- use `### Delta N` headings (`N` starting from 1)
- keep entries auditable and non-generic
```

## 4. PRD Deep-Compilation Acceptance Checks

Before treating a PRD generated from this template as complete, check:

1. Does each depth-sensitive section explain decisions and consequences, not just name them?
2. Can design derive the primary workflow and screen/module implications without reconstructing the logic from stage artifacts?
3. Can architecture derive the first-wave object/dependency model and boundary assumptions without inventing the product mechanism?
4. Are review-bound truths explicit enough that downstream will not silently promote them?
5. Is the document meaningfully deeper than a section-by-section stage-output mirror?
6. Has high-value source detail been preserved or recompilied, rather than merely compressed away?
7. If the PRD is materially shorter than the structured input, is that because of denser synthesis rather than loss of decision-relevant detail?
8. Does the PRD include an Analysis Delta Ledger with auditable source-to-decision traceability and category coverage?
9. If `delivery_profile=implementation-ready-prd`, does the PRD include executable process/IA/flow specification (decomposition table, exception flows, IA spec matrix, state machine, AC trace matrix)?

If any answer is `no`, the PRD should return to deep-compilation rather than be treated as cleanly assembled.

---

## 4. Required content source mapping

### From Stage-01
- final problem statement
- target user boundary (with why-this-not-that rationale)
- user groups
- Use Case / User Story
- problem list
- opportunity list
- need framing choice (with alternatives considered and rationale)
- persona profiles (with context/key-path scenarios)
- empathy narrative

### From Stage-02a
- chosen panorama structure and structure rationale
- value loop articulation
- backbone flow
- key constraints (stress-tested)
- priority split
- stakeholder profiles (with adoption chain analysis)
- key business scenario analysis (at least 3 scenarios with challenge-solution depth)
- persona/scenario set with design requirements

### From Stage-02b (if executed)
- NFR / quality requirements summary with quality-scenario tables
- conceptual domain model (entities + relationships + ER diagram)
- key data characteristics
- business subsystem boundaries (if applicable)
- IA direction decisions
- specification stress-test outcome
- NFR MVP impact assessment

### From Stage-03
- complete experience loop
- minimum viable experience loop
- chosen slice strategy and why-this-slice-not-that rationale
- first/later/deferred slices (with deferral honesty check)
- NFR-aware slicing impact
- domain dependency impact on slice ordering
- slice rationale

### From Stage-04
- validation target (with positive/negative change articulation)
- method and why-this-method-not-that rationale
- prototype fidelity and rationale
- current evidence state
- three-dimensional validation assessment (value / usability / feasibility)
- evidence state honesty (inference vs. real evidence vs. unknown)
- validation conclusion
- decision state and rationale
- revision recommendations
- forbidden downstream assumptions

### From execution report
- current admission reading
- warnings / review-bound carryover
- unresolved truth to preserve

---

## 5. Mermaid / UML usage rule

This PRD template explicitly allows and encourages Mermaid/UML where it improves clarity.

Recommended uses:

- Use Case relationship sketch
- backbone activity flow
- conceptual domain model ER diagram (from Stage-02b)
- business subsystem boundary diagram (from Stage-02b, if applicable)
- slice map
- validation flow

Rule:

- diagrams must clarify structure
- diagrams must not replace required prose
- diagrams should stay lightweight and product-facing

---

## 6. What this PRD is not

It is not:

- a replacement for stage outputs
- a substitute for execution report
- a visual/UI final spec
- a fully validated business case when evidence is still review-bound

It is:

> **the main product-facing converged document for Phase-1.**

---

## 7. Summary sentence

> **Phase-1 should end not only with stage outputs and a convergence pack, but with one complete PRD main document assembled from those artifacts.**
