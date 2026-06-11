# Stage-03 Skill Contract — data-storage-and-interface-design

## 1. Skill Goal
- Transform Stage-02 decomposition outputs into explicit data model, storage strategy, and interface contract package that supports Stage-04 convergence and delivery handoff.

## 2. Inputs
- Required:
  - Stage-02 domain/module/service/dependency outputs
  - Stage-02 conceptual entity relationship and domain event outputs
- Optional:
  - system constraints and non-functional guidance updates
  - security or compliance constraints
  - expected volume, latency, and growth signals
  - existing platform or stack constraints
  - current external evidence for versions, LTS/support windows, licenses, benchmarks, and security notices
  - external dependency availability, ownership, procurement, or contract feasibility signals
  - substitute-boundary or degraded-mode expectations
- Missing-input handling: refuse/block if Stage-02 package is absent or incoherent
- declaration-state rule: preserve `present | absent | unknown | deferred` carryover for unresolved constraints and quality inputs

## 2.1 Intake and State Rules
- `cannot_infer`:
  - final data ownership boundaries without decomposition basis
  - aggregate lifecycle or write paths that cannot be performed by declared owning modules
  - stable interface contracts without dependency/context inputs
  - access-pattern-driven index posture without any query/filter/sort/join basis
  - duplicated command boundaries for one authoritative business mutation without explicit split semantics
  - public-boundary object, contract, snapshot, or endpoint-visible names that are not defined or explicitly marked derived/deferred
  - production-final stack or deployment commitments without constraint basis
  - production-ready external dependency guarantees when availability / ownership / feasibility basis is unknown
  - substitute-boundary viability when no contract delta or tradeoff note exists
  - internal class names, service implementation names, or private method names without implementation-stage basis
  - current version/LTS/license/security/performance claims from stale model memory alone
  - technology_selection_evaluation_matrix entries marked `externally-verified` without an accompanying evidence_sources field listing at minimum: source URL or document name, and query/verification date; field-value claim alone is not sufficient
  - optimum architecture candidate without identifying the dominant bottleneck first
  - mainstream baseline sufficiency just because it is common or easy to explain
- `can_provisionally_infer`:
  - first-pass schema and contract drafts
  - first-pass interaction flow assumptions
  - first-pass security architecture posture
  - first-pass stack/deployment assumptions
  - first-pass capacity/performance estimates
  - first-pass technology selection candidates pending external verification
  - first-pass dominant bottleneck hypothesis and alternative candidate set pending validation
  - first-pass critical external dependency realizability scan
  - first-pass substitute-boundary plan
  - downstream assumption contract
- `must_validate_before_exit`:
  - data/interface package is Stage-04-consumable
  - API endpoint draft includes at minimum: HTTP method, path, key request body fields (≥3 fields per mutating endpoint), primary success response shape, and at least one explicit failure/error semantic per endpoint; path-only or method-only drafts do not pass this gate
  - storage rationale is explicit
  - access-pattern and index strategy is explicit enough for downstream convergence
  - canonical response/error contract is explicit enough for downstream convergence
  - schema draft and API endpoint draft are explicit enough for downstream convergence
  - when schema evolution or rollout sequencing risk exists, schema_migration_strategy is explicit with migration tooling, backward-compatibility rule, version tagging convention, rollback posture, and deployment order note
  - schema draft covers each core aggregate table with: table name, ≥5 key column names, PK declaration, at least one FK or cross-table reference semantic, and critical constraints (unique / not-null); table-name-only or column-direction-only drafts do not pass this gate
  - API endpoint draft includes for each mutating endpoint: HTTP method, path, key request body fields (≥3 fields), primary success response shape, and at least one explicit failure/error semantic; path-only drafts do not pass this gate
  - API endpoint draft records response_profile, retryability_policy, and idempotency_rule for implementation-facing endpoints
  - response/error handling differentiates `business_error` from `system_error`
  - aggregate lifecycle and write ownership remain aligned
  - each authoritative business mutation has one primary command boundary or an explicit non-overlapping multi-step split
  - public-boundary names are registry-closed across schema, contracts, endpoints, and handoff notes
  - security, stack/deployment, and capacity/performance assumptions are explicit rather than hidden
  - technology selection evaluation matrix is explicit
  - time-sensitive technology facts are externally verified rather than memory-only
  - dominant bottleneck hypothesis is explicit and names the specific dominant constraint (not a generic description)
  - materially different alternatives are evaluated with ≥3 candidates including: (1) mainstream baseline, (2) constraint-dominant alternative, and ≥1 additional materially different option
  - when multi-candidate tradeoff evaluation is active, the tradeoff closure bundle is explicit: `technology_selection_evaluation_matrix`, `architecture_alternative_candidate_set`, `baseline_insufficiency_note`, `constraint_dominant_optimum_candidate`, and `key_tradeoff_decisions`
  - technology_selection_evaluation_matrix covers ≥10 evaluation dimensions per candidate with non-placeholder values
  - every not-chosen candidate has an explicit rejection_reason that references the dominant constraint, not just generic feasibility
  - chosen candidate explicitly states why it beats the mainstream baseline under the dominant constraint, not merely that it is "sufficient"
  - mainstream baseline insufficiency is explicit where the dominant constraint makes it inadequate
  - schema_draft covers every module declared in Stage-02 decomposition; missing any Stage-02 module's schema representation = gate fail
  - API endpoint draft covers at least one mutating endpoint per Stage-02 module; missing any Stage-02 module's API representation = gate fail
  - all known business scenarios are covered through a scenario matrix
  - Phase-1 trace hotspots such as `return-for-clarification`, boundary visibility, and `overview -> findings -> tasks -> reports` continuity are explicitly absorbed through scenario or contract rows rather than assumed by proximity to the main happy path
  - scenario_coverage_matrix includes ≥2 explicitly labeled `concurrent_conflict` rows with visible coordination/locking/merge strategy
  - critical, failure-path, or concurrent-conflict scenarios keep GWT-compatible acceptance structure: either explicit `given / when / then` columns or Given/When/Then wording inside `acceptance_criteria`
  - public boundary-visible names are explicit without freezing private implementation symbols
  - declaration-state and NFR handling remain explicit
  - critical external dependency realizability is explicit for every dependency whose absence would invalidate schema, endpoint, or flow design
  - substitute-boundary plan exists when external dependency realizability is `partial | unknown | unavailable`
  - downstream `may-assume | must-not-assume` contract is explicit for external dependency, transport, and runtime commitments

## 3. Execution Steps
1. intake Stage-02 package and declaration states
2. define data entities/ownership boundaries
3. identify the dominant bottleneck or constraint that governs the architecture choice
4. build scenario coverage matrix across all known business scenarios
5. define schema draft, storage strategy, and tradeoffs
6. define access-pattern and index strategy for dominant read/write paths plus schema migration/version-tagging posture where rollout sequencing matters
7. define interface contracts, canonical response/error contract, API endpoint draft, scenario GWT-compatible acceptance structure, and error/compatibility behavior
8. define interaction flow, security posture, and dependency-impact notes
9. evaluate critical external dependency realizability and substitute-boundary options
10. define stack/deployment assumptions, build materially different architecture alternatives, and fill the technology selection evaluation matrix
11. verify time-sensitive technology facts with external evidence, close the tradeoff reasoning bundle (`baseline insufficiency -> optimum candidate -> key tradeoff decisions`), and state downstream assumption limits

## 4. Outputs
- data model summary
- data ownership map
- storage strategy and constraints
- access-pattern and index strategy
- schema migration strategy
- schema draft
- interface contract set
- canonical response/error contract
- API endpoint draft
- lifecycle and command consistency checks
- public-boundary registry closure notes
- interaction flow notes
- scenario coverage matrix
- security architecture outline
- critical external dependency realizability
- substitute-boundary plan
- technology stack and deployment assumptions
- technology selection evaluation matrix
- dominant bottleneck hypothesis
- architecture alternative candidate set
- baseline insufficiency note
- constraint-dominant optimum candidate
- capacity and performance assumptions
- key design tradeoff decisions
- downstream assumption contract

## 5. Acceptance Criteria
- Stage-04 can converge design without re-deriving core data/interface assumptions
- Stage-04 can converge without inventing schema, endpoint, security, or runtime assumptions from scratch
- Stage-04 does not need to reinvent the technology selection rationale or evidence trail
- Stage-04 does not need to invent hot-path indexes or response/error envelope semantics from scratch
- Stage-04 does not need to infer the dominant bottleneck, why baseline lost, or which stronger candidate won
- Stage-04 does not need to guess whether a critical dependency is direct, substitute-boundary, or still blocked/review-bound
- Stage-04 does not need to repair ownerless lifecycle states, overlapping command endpoints, or dangling public-boundary names
- all known business scenarios are covered, even if only critical ones are diagrammed later
- critical, failure-path, and concurrent-conflict scenarios remain GWT-compatible rather than collapsing into unstructured acceptance prose
- unresolved items and provisional content are explicit
- unresolved declaration states and NFR handling are explicit rather than implied
- at least one structured visual representation is present (Mermaid diagram, ASCII block diagram, or equivalent structured table view); if diagram_obligation=required and no visual representation exists, stage status must be downgraded to `blocked`, not `provisional` or `pass`

## 6. Boundaries
- no final delivery-prototype convergence
- no production-final schema/endpoint lock without review or source basis
- no silent conversion of draft security or performance assumptions into approved guarantees
- no duplicate command boundaries claiming the same authoritative mutation without explicit split semantics
- no dangling public-boundary names that disappear from schema/contract/endpoint definitions
- no mandatory entity class, service implementation class, or internal method naming
- no final technology selection based only on model memory when current external facts matter
- no early stop at an acceptable mainstream solution when dominant constraints indicate a stronger architecture pattern should be evaluated
- no silent conversion of review-bound assumptions into approved constraints
- no silent conversion of partially realizable external dependencies into implementation-ready baseline commitments

## 7. Flow Rules
- handoff target: `design-convergence-and-delivery-prototype`
- preserve `present | absent | unknown | deferred` semantics wherever Stage-04 would otherwise inherit ambiguity silently
- preserve downstream `may-assume | must-not-assume` rules wherever external dependency or runtime commitments remain review-bound
