# Stage-02b SOP — requirements-specification-deepening

## 1. Stage Positioning
- Stage name:
  - requirements-specification-deepening
- Stage goal:
  - deepen the Stage-02a structural panorama with non-functional requirements analysis, domain model direction, information architecture direction, and business subsystem boundaries — producing specification-grade inputs for Stage-03 slicing
- Parent phase:
  - product / requirements
- Upstream dependency:
  - Stage-02a structured outputs (structural panorama, stakeholder analysis, business scenarios, persona/scenario set)
- Downstream target:
  - `requirements-decomposition-and-mvp-slicing` (Stage-03)

## 2. Start Conditions
- Required inputs:
  - Stage-02a structural panorama (backbone flow + story map)
  - Stage-02a key business scenario analysis (at least 3 scenarios with scenario-challenge-solution)
  - Stage-02a persona set with context/key-path scenarios
  - Stage-02a stakeholder profiles
  - Stage-02a key constraints list
- Optional inputs:
  - technical constraints from engineering team
  - existing system architecture context
  - regulatory/compliance requirements
  - data sensitivity classification
- Pre-start checks:
  - does Stage-02a provide enough scenario depth to drive NFR and domain model analysis?
  - are the business scenarios specific enough to identify quality attributes that matter?
- Refusal rule:
  - return to Stage-02a if the structural panorama lacks scenario-level depth (only backbone activities without business scenario analysis)
- Clarification expansion rule:
  - clarify missing scenario or constraint context before attempting NFR or domain model analysis
- Enter `Blocked` when:
  - Stage-02a outputs are too abstract to derive meaningful NFR or domain model direction
- Enter `Provisional Inference` when:
  - the team explicitly accepts provisional specification drafting while Stage-02a refinement is still in progress

## 3. Standard Execution Steps

### Step 1 — Upstream Handoff Inspection
- Check Stage-02a handoff completeness:
  - structural panorama with backbone flow
  - key business scenario analysis (scenario-challenge-solution depth)
  - persona/scenario set with design requirements
  - stakeholder profiles with adoption chain
  - key constraints list (stress-tested)
  - reasoning evidence (Section 3.2 of Stage-02a output)
- Classify: which Stage-02a outputs are confirmed vs. provisional vs. still-open?
- Identify gaps that would affect NFR analysis, domain modeling, or IA direction
- **Micro-checkpoint MC1**: Is there enough scenario depth to drive specification-level analysis? If no → return to Stage-02a or enter `S2 Blocked`

### Step 2 — NFR / Quality Requirements Analysis
- Identify key quality attributes relevant to the product, systematically scanning:
  - **Security**: authentication, authorization, data protection, audit trail needs
  - **Reliability**: availability targets, fault tolerance, data integrity, recovery requirements
  - **Usability**: learnability, efficiency of use, error tolerance, accessibility
  - **Performance**: response time expectations, throughput, scalability boundaries
  - **Maintainability**: modifiability, testability, deployment complexity
  - **Portability**: platform constraints, data migration, integration adaptability
- For each identified quality attribute, apply **reverse-risk thinking**:
  - if this quality attribute fails, what is the worst realistic consequence?
  - which business scenarios from Stage-02a would be most affected?
  - which stakeholders would be most impacted?
- For key quality attributes (those with material impact on MVP or architecture), produce a **quality-scenario table**:
  - stimulus: what event triggers the quality concern (e.g., "100 concurrent users query AI mention rates")
  - environment: under what conditions (e.g., "normal operation", "peak load", "degraded mode")
  - response: what the system must do (e.g., "return results within 3 seconds")
  - measure: how we know it is met (e.g., "95th percentile response time < 3s")
- Not all NFRs need full quality-scenario depth — only those that directly affect MVP scope or architecture decisions
- **Micro-checkpoint MC2**: Are at least 3 quality attributes identified with material product impact, each with at least one threat scenario? If no → expand analysis before proceeding

### Step 3 — Domain Model Direction
- From Stage-02a business scenarios and persona interactions, identify **core business entities**:
  - what are the key "things" the system must know about, create, or manipulate?
  - what are the relationships between these entities?
  - what are the key lifecycle states of each entity?
- Before freezing the domain direction, compile any source-level structured capability detail into a **Module Interface Payload Contract**:
  - if the source names specific structured outputs (e.g., score fields, diagnosis summaries, reserved action data, domain-specific structured records), Stage-02b must preserve them as explicit fields instead of collapsing them into generic summary prose
- If the source names future measurement / external identity / source-tag / journey-stage / multi-entry capability, preserve them as a **Deferred Capability Seam**:
  - define the future object/interface seam or reserved fields now
  - do not silently drop those capabilities
  - do not falsely upgrade them into MVP promises
- Produce a **conceptual domain model** (entity-relationship level, NOT database design):
  - entities with brief descriptions
  - key relationships (association, composition, generalization)
  - cardinality where it matters for architecture
  - render as Mermaid ER diagram
- Identify **key data characteristics**:
  - data window: how far back must data be retained? what is the freshness requirement?
  - data sources: where does data originate? (user input, external API, system-generated, imported)
  - data sensitivity: what data has privacy/compliance implications?
  - data volume estimates: order-of-magnitude expectations for key entities
- If the system is complex enough, identify **business subsystem boundaries**:
  - which groups of entities and scenarios form natural clusters?
  - where are the natural boundary lines between subsystems?
  - what are the key interfaces between subsystems? (Why does subsystem A need to talk to subsystem B? What data flows across the boundary? What constraints apply?)
  - subsystem boundaries should reflect business logic groupings, not technical layer splits
- **Micro-checkpoint MC3**: Are at least 5 core business entities identified with relationships? Is a conceptual ER diagram producible? If no → revisit Stage-02a scenarios for missing domain context
- **Micro-checkpoint MC3b**: If the source contains detailed structured capability or future extension language, has Stage-02b preserved it as either payload contract or deferred seam rather than dropping it or flattening it?

### Step 4 — Information Architecture Direction
- From Stage-02a personas, scenarios, and domain model, identify **IA direction decisions** that will affect architecture:
  - **Organization strategy**: how should the product's information be organized?
    - exact classification (clear categories, each item belongs to one place) vs. ambiguous classification (items may belong to multiple categories) vs. faceted classification (multiple independent dimensions)
    - hierarchical vs. flat vs. hybrid?
    - what is the primary axis of organization? (by workflow stage? by entity type? by user role? by time?)
  - **Labeling direction**: what language should the product use?
    - user language (as discovered in Stage-01 research) vs. system/domain language?
    - key labeling decisions that affect user mental model
    - terminology conflicts between stakeholder groups
  - **Navigation strategy direction**:
    - global navigation needs (what must be accessible from everywhere?)
    - local navigation needs (what must be accessible within a workflow context?)
    - contextual navigation needs (what must be accessible based on current task?)
  - This step produces **direction decisions, not detailed IA design** — the goal is to identify IA choices that constrain architecture and MVP scope
- **Micro-checkpoint MC4**: Are at least 2 IA direction decisions identified that would affect architecture or MVP scope? If no → consider whether the product is simple enough that IA direction is trivially obvious (document this conclusion)

### Step 5 — Specification Stress-Test & Evidence Assembly
- Apply a specification stress-test:
  1. If Stage-03 received only Stage-02a's structural panorama without this specification deepening, what slicing decisions would have blind spots?
  2. Do the identified NFRs materially constrain what can be in the first slice? (e.g., security requirements that force certain capabilities into MVP)
  3. Does the domain model reveal entity dependencies that affect slice ordering?
  4. Do IA direction decisions constrain what user flows are feasible in the first slice?
  5. Would Stage-03 accidentally flatten structured source detail into generic prose because the payload contract was not specified?
  6. Would deferred future capability be lost or reintroduced later without a seam?
- Assemble all reasoning evidence:
  - NFR analysis summary with quality-scenario tables for key attributes
  - domain model with ER diagram and data characteristics
  - business subsystem boundaries (if applicable)
  - IA direction decisions with rationale
  - specification stress-test outcome
- Verify completeness of required evidence items:
  1. NFR prioritization reasoning (why these quality attributes are most critical)
  2. domain model decisions (why this entity structure, what alternatives were considered)
  3. IA direction reasoning (why this organization/navigation strategy, what impact on architecture)
  4. specification stress-test outcome
  5. deepening loop log
- Mark unresolved specification gaps explicitly

## 3.1 Intake / Clarification / Review State Flow
- `S0 Intake Received`:
  - capture the Stage-02a package, inspect specification-readiness
- `S1 Clarification Active`:
  - clarify missing scenario or constraint context before specification analysis
- `S2 Blocked`:
  - stop if specification analysis would be fabricated without adequate upstream scenario depth
- `S3 Provisional Inference`:
  - allow only review-bound provisional specification drafting
- `S4 User Review`:
  - review NFR priorities, domain model choices, IA direction decisions
- `S5 Gate Pass`:
  - pass only when Stage-03 can consume the specification deepening safely AND reasoning evidence is in place
- `S6 Escalate`:
  - escalate if specification decisions require technical expertise or stakeholder input not available

## 3.2 Thinking Loop Integration

After the initial draft is produced (Steps 1-5), the stage enters a bounded deepening loop.

### Loop states
- `S-draft-structured`: initial specification exists; may still be shallow
- `S-deepening-round-1`: first deepening (NFR coverage, domain model completeness, IA direction clarity)
- `S-deepening-round-2`: second deepening (only high-value gaps; no broad re-exploration)
- `S-deepening-round-3`: final deepening (integration and synthesis tightening only)
- `S-review-bound-freeze` / `S-return-remediate` / `S-blocked`

### Default loop limit
- One structured draft + up to THREE deepening rounds

### Stage-02b specific deepening focus
Each round may improve only:
- NFR coverage and quality-scenario precision
- domain model completeness and relationship clarity
- IA direction decision specificity
- subsystem boundary reasoning
- Stage-03 specification consumability

Not allowed in later rounds:
- expanding NFR analysis into full architecture design
- deepening domain model into database schema design
- turning IA direction into detailed wireframe-level IA
- adding new quality attributes without evidence of material impact

### Per-round evidence requirement
Each round must record: what was refined, alternatives compared, trade-offs clarified, stress test improvement, freeze/continue/return/block rationale

## 4. Process Checkpoints

### Specification depth checkpoints
- Checkpoint 1:
  - at least 3 quality attributes identified with material product impact
- Checkpoint 2:
  - key quality attributes have quality-scenario tables (stimulus → environment → response → measure)
- Checkpoint 3:
  - conceptual domain model exists with at least 5 core entities and relationships
- Checkpoint 4:
  - IA direction decisions are identified where they affect architecture
- Checkpoint 4b:
  - module interface payload contract exists when the source contains detailed structured outputs
- Checkpoint 4c:
  - deferred capability seam exists when the source contains future measurement / external identity / source-tag / journey-stage / multi-entry language

### Reasoning quality checkpoints
- Checkpoint 5:
  - NFR prioritization has analytical rationale (not just listing)
- Checkpoint 6:
  - domain model decisions have alternatives reasoning
- Checkpoint 7:
  - specification stress-test has been applied (Stage-03 can slice with awareness of NFR and domain constraints)

### Confirmation and provisional rules
- Fields that require confirmation or explicit review-bound status:
  - quality attribute priority rankings (which NFRs are critical vs. nice-to-have)
  - domain model entity boundaries (especially if business logic is ambiguous)
  - subsystem boundary decisions (if applicable)
- Fields allowed as provisional only:
  - first-pass quality-scenario measures (specific numbers may need validation)
  - IA direction decisions (conceptual level, will be refined in design phase)

## 5. Referenced Method Assets
- Required cards:
  - `effective-requirements-analysis` ch19: quality requirements analysis (quality-scenario template, reverse-risk thinking, NFR categorization)
  - `effective-requirements-analysis` ch17-18: domain modeling + business data analysis (conceptual ER, entity lifecycle, data characteristics)
  - `effective-requirements-analysis` ch7-8: business subsystem decomposition + business interface analysis (boundary identification, interface Why/What/Constraints)
  - `information-architecture-for-the-web`: organization systems, labeling systems, navigation systems (conceptual layer only — direction decisions, not detailed IA design)
  - preserve detailed source capability and future extension signals by recompiling them into typed payloads or deferred seams, not generic placeholders
- Optional cards:
  - `effective-requirements-analysis` ch14-16: functional requirements specification (if Stage-02b scope extends to functional specification)
  - ISO 25010 quality model reference (if systematic NFR coverage is needed)
- Boundary / anti-pattern cards:
  - do not turn NFR analysis into full architecture design — this is requirements specification, not solution architecture
  - do not turn domain modeling into database schema design — conceptual entities and relationships, not tables and columns
  - do not turn IA direction into wireframes — organization/navigation/labeling strategy, not page layouts
  - do not add quality attributes without evidence of material impact — avoid NFR checklisting

## 6. Output Generation Rules
- Required outputs:
  - NFR / quality requirements summary with key quality-scenario tables
  - conceptual domain model (entities + relationships + Mermaid ER diagram)
  - key data characteristics (window, sources, sensitivity, volume estimates)
  - IA direction decisions with rationale
  - specification stress-test outcome
- Conditional outputs:
  - business subsystem boundaries (only if system complexity warrants it)
  - business interface definitions (only if subsystem boundaries are identified)
- Minimum output rule:
  - Stage-03 must be able to factor NFR and domain constraints into slicing decisions
- Diagram obligation:
  - `diagram_obligation: required` (conceptual domain model ER diagram)
  - optional: business subsystem boundary diagram, information organization strategy diagram
- Provenance / assumptions marking rule:
  - any provisional specification assumptions must keep status, source, confidence, verification, and assumptions_to_validate fields
- Reasoning capture rule:
  - the following items are REQUIRED, not optional:
    - NFR prioritization reasoning
    - domain model decisions with alternatives
    - IA direction reasoning
    - specification stress-test outcome
    - deepening loop log

## 7. Stage Acceptance
- Minimum completion standard:
  - at least 3 quality attributes analyzed with material product impact
  - key quality attributes have quality-scenario tables
  - conceptual domain model exists with entities, relationships, and ER diagram
  - key data characteristics identified
  - IA direction decisions documented (or explicitly assessed as trivially obvious)
  - specification stress-test applied
  - reasoning evidence section populated
  - Stage-03-consumable handoff exists
- Common failure signals:
  - NFR listed as a checklist without analysis of impact or scenarios
  - domain model is a database schema instead of a conceptual model
  - IA direction is a wireframe instead of strategy decisions
  - quality-scenario tables have made-up numbers without basis
  - no specification stress-test (Stage-03 blind spots not assessed)
  - subsystem boundaries drawn along technical layers instead of business logic clusters
  - no deepening loop log
- Return path:
  - return to Stage-02a if scenario depth is insufficient to drive specification
- State return rule on failure:
  - go back to `S1 Clarification Active` or `S2 Blocked`
- Escalation rule:
  - escalate if NFR decisions or domain model choices require technical expertise not available in the current team

## 8. Handoff Rules
- Handoff target:
  - `requirements-decomposition-and-mvp-slicing` (Stage-03)
- Handoff package:
  - Stage-02a full outputs (structural panorama, stakeholder analysis, business scenarios, persona/scenario set, design requirements)
  - NFR / quality requirements summary with quality-scenario tables
  - conceptual domain model with ER diagram
  - key data characteristics
  - business subsystem boundaries (if applicable)
  - IA direction decisions
  - specification stress-test outcome
  - assumptions / open questions where still needed
- Handoff explanation requirement:
  - explain which NFRs constrain MVP scope (e.g., security requirements that must be in first slice)
  - explain the domain model's key entity dependencies that affect slice ordering
  - explain IA direction decisions that constrain feasible user flows
- Provisional content in handoff:
  - allowed only if explicitly labeled
- Whether downstream may consume provisional content:
  - yes, but only as review-bound input, never as silently confirmed fact
