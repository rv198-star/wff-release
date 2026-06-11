# Stage-03 SOP — data-storage-and-interface-design

## 1. Stage Positioning
- goal: produce data/storage/interface design package from Stage-02 decomposition
- upstream: Stage-02
- downstream: Stage-04

## 2. Start Conditions
- required: Stage-02 handoff with domain/module/service/dependency structure plus conceptual ER and domain event coverage
- refuse: missing or unusable Stage-02 package
- blocked: unclear ownership or unresolved boundary contradictions prevent coherent data/interface framing
- declaration-state rule: keep `present | absent | unknown | deferred` semantics explicit for unresolved quality, storage, or contract concerns
- realizability rule: keep external dependency realizability and substitute-boundary posture explicit wherever Stage-04 would otherwise overclaim readiness

## 3. Standard Execution Steps
1. validate Stage-02 intake
2. define data ownership and model boundaries
3. identify dominant bottleneck/constraint hypothesis
4. build scenario coverage matrix across all known business scenarios
5. define schema draft and storage/constraint strategy
6. define access-pattern-driven index strategy, hotspot rationale, and schema migration/version-tagging posture where rollout sequencing matters
7. define interface contracts, canonical response/error contract, API endpoint draft, scenario GWT-compatible acceptance structure, and interaction flow
8. define security posture and critical external dependency realizability
9. define substitute-boundary plan plus stack/deployment assumptions
10. build materially different architecture alternatives, complete the technology selection evaluation matrix, and verify time-sensitive facts with external evidence
11. define capacity/performance assumptions, record baseline insufficiency where relevant, capture the constraint-dominant optimum candidate, and capture design tradeoffs/review-bound assumptions
12. state downstream `may-assume | must-not-assume` limits and assemble Stage-04 handoff package

## 3.1 State Flow
- S0 intake → S1 clarification → S2 blocked
- S3 provisional inference (review-bound)
- S4 user review → S5 gate pass → S6 escalate

## 4. Process Checkpoints
- ownership boundaries explicit
- aggregate lifecycle and write ownership aligned
- storage rationale explicit
- index strategy explicit and tied to concrete access paths, not only declared as leftover DDL hints
- interface contracts explicit
- canonical response/error contract explicit
- schema draft explicit (each core aggregate table must include: table name, ≥5 key column names, PK declaration, at least one FK or cross-table reference semantic, and critical constraints; table-name-only or column-direction-only drafts do not pass this checkpoint)
- API endpoint draft explicit
- one primary command boundary per authoritative mutation explicit
- public-boundary names registry-closed across schema/contracts/endpoints or explicitly marked derived/deferred
- interaction flow explicit
- critical external dependency realizability explicit
- substitute-boundary plan explicit where realizability is not `confirmed`
- dominant bottleneck hypothesis explicit: names the specific dominant constraint, not a generic description; has explicit causal link to architecture alternative selection
- materially different alternatives explicit: ≥3 candidates (mainstream baseline + constraint-dominant alternative + ≥1 other); each not-chosen candidate has rejection_reason referencing the dominant constraint
- technology_selection_evaluation_matrix covers ≥10 evaluation dimensions per candidate with non-placeholder values; chosen candidate explicitly states superiority over baseline under dominant constraint
- tradeoff closure bundle explicit when multi-candidate evaluation is in scope: `technology_selection_evaluation_matrix` + `architecture_alternative_candidate_set` + `baseline_insufficiency_note` + `constraint_dominant_optimum_candidate` + `key_tradeoff_decisions`; a matrix alone does not close the reasoning chain
- baseline insufficiency explicit where relevant: must state concretely why mainstream baseline fails under the dominant constraint, not merely that a stronger option exists
- constraint-dominant optimum candidate explicit
- schema_draft covers every module declared in Stage-02 decomposition; absence of any Stage-02 module's schema = gate fail
- access_pattern_and_index_strategy covers the hot filters/sorts/joins that dominate storage cost; index names without access-pattern mapping do not pass this checkpoint
- API endpoint draft covers at least one mutating endpoint per Stage-02 module; absence of any Stage-02 module's API coverage = gate fail
- API endpoint draft records response_profile, retryability_policy, and idempotency_rule for implementation-facing endpoints
- business errors and system errors stay distinguishable in the response/error contract and endpoint failure semantics
- scenario coverage across all known business scenarios explicit
- scenario coverage includes ≥2 explicitly labeled concurrent-conflict rows with visible coordination/locking/merge strategy
- critical, failure-path, or concurrent-conflict scenarios keep GWT-compatible acceptance structure: dedicated `given / when / then` columns when helpful, otherwise explicit Given/When/Then language inside `acceptance_criteria`
- public boundary-visible names explicit
- security posture explicit
- stack/deployment assumptions explicit
- technology selection matrix explicit
- external evidence used where technology facts are time-sensitive; any entry in technology_selection_evaluation_matrix marked `externally-verified` must include an evidence_sources field listing at minimum: source URL or document name, and query/verification date; field-value claim alone is not sufficient
- schema draft covers each core aggregate table with: table name, ≥5 key column names, PK declaration, at least one FK or cross-table reference semantic, and critical constraints (unique / not-null); column-direction-only or table-name-only drafts do not pass this checkpoint
- API endpoint draft includes for each mutating endpoint: HTTP method, path, key request body fields (≥3 fields), primary success response shape, and at least one explicit failure/error semantic; path-only drafts do not pass this checkpoint
- capacity/performance assumptions explicit
- downstream `may-assume | must-not-assume` contract explicit
- private implementation symbols not prematurely frozen
- declaration-state/NFR semantics preserved

## 5. Method Assets
- required: architecture/data/interface design references
- optional: quality taxonomy references
- anti-patterns: schema without ownership, ownerless lifecycle states, duplicated command boundaries, dangling named artifacts, contracts without failure semantics, hidden coupling, silent stack/security assumptions
- anti-patterns: indexes listed without query-path rationale, response schemas implied only by examples, business/system failures collapsed into one generic error bucket, retryability omitted while proposing asynchronous or dependency-heavy flows

## 6. Output Rules
- required outputs: data/storage/interface/interaction + schema/API/security/stack/performance package
- diagram obligation: `required` (hard gate: absence of structured visual representation = gate fail; stage must be downgraded to `blocked`, not `provisional` or `pass`)
- provisional items must keep provenance markers
- scenario coverage matrix is required for all known business scenarios
- concurrency or authoritative-write conflict must not be left implicit; if multiple actors or retries can touch the same authoritative surface, include explicit concurrent-conflict scenarios
- freeze public boundary-visible names and contracts only; defer internal class/method/file symbols
- technology selection must include comparison dimensions and evidence sources
- tradeoff-heavy reasoning must close as a bundle; if a multi-candidate selection is kept, explain why baseline loses, who wins under the dominant constraint, and which tradeoffs are deliberately accepted
- storage design must include an access-pattern-driven index strategy, not only schema-level `index_hint` strings
- when rollout sequencing or backward compatibility matters, schema design must include migration tooling, compatibility, version-tagging, rollback, and deployment-order posture
- response formatting and exception handling must be standardized at the Stage-03 contract layer; endpoint-local status-code prose alone is not enough
- when selection depends on current facts, official/current external sources must be consulted instead of relying on memory alone
- any technology selection entry marked `externally-verified` must include an evidence_sources field listing at minimum: source URL or document name, and query/verification date; undocumented external verification is treated as inferred
- critical external dependencies must carry realizability status, evidence basis, and substitute-boundary handling where needed
- identify dominant bottleneck before settling on architecture choice
- do not stop at the first acceptable mainstream solution when dominant constraints suggest a stronger alternative should be evaluated
- lifecycle states and write paths must stay aligned with declared owners
- each authoritative business mutation must map to one primary command boundary unless an explicit non-overlapping split is documented
- public-boundary objects/contracts/snapshots/endpoints must be registry-closed or explicitly marked derived/deferred
- schema/API/security/stack/performance content may remain draft, but cannot be omitted when downstream decisions depend on it
- downstream handoff must say what implementation may rely on directly versus what remains review-bound or substitute-boundary-only
- declaration-state carryover must remain explicit in handoff-facing sections

## 7. Stage Acceptance
- Stage-04 can converge without re-deriving Stage-03 core outputs or inventing omitted implementation-facing assumptions
- Stage-04 should not need to infer which scenarios exist, but may select only critical scenarios for detailed sequence views
- Stage-04 should not need to reconstruct why baseline architecture was insufficient or which candidate best fits the dominant constraint
- Stage-04 should not need to reconcile overlapping command endpoints or undefined public-boundary names
- Stage-04 should not need to infer whether a critical external dependency is direct, substitute-boundary, or blocked

## 8. Handoff Rules
- handoff to Stage-04 with explicit unresolved and review-bound items
