# Stage-03 Self-Test Case — decomposition package to data/interface package

## 1. Test Goal

Use one Stage-02 decomposition brief to verify that Stage-03 can produce a data/storage/interface package usable for Stage-04 convergence.

Focus:

- ownership-aware data design
- lifecycle/write-path consistency
- storage rationale
- explicit interface contracts
- command-boundary uniqueness
- public-boundary name closure
- schema and endpoint draft clarity
- scenario coverage across all known business scenarios
- technology selection rationale and evidence quality
- dominant bottleneck and alternative-search quality
- security/runtime assumption clarity
- interaction-flow clarity

---

## 2. Input Brief

> Stage-02 defines capture, summarization, review, and CRM sync services. Review must stay explicit. CRM integration remains external-facing. Quality uncertainty still exists around latency and auditability.

---

## 3. Expected Minimum Output Shape
- data model summary
- data ownership map
- storage strategy
- schema draft
- interface contracts
- API endpoint draft
- interaction flow
- scenario coverage matrix
- security architecture outline
- technology stack and deployment assumptions
- technology selection evaluation matrix
- dominant bottleneck hypothesis
- architecture alternative candidate set
- baseline insufficiency note
- constraint-dominant optimum candidate
- capacity and performance assumptions
- tradeoff decisions

---

## 4. PASS / FAIL

### PASS if:
- Stage-04 can converge design without rebuilding data/interface/runtime assumptions
- all known business scenarios are covered without forcing private class/method design
- technology selection is justified with explicit dimensions and external evidence for time-sensitive claims
- dominant bottleneck is explicit and the selected candidate is stronger than a merely acceptable baseline where required
- lifecycle ownership and command boundaries do not conflict
- public-boundary names are defined or explicitly deferred/derived

### FAIL if:
- schemas have no ownership boundaries
- lifecycle states have no owner-aligned writer
- schema draft omits key structures or relations
- contracts hide failure behavior
- API endpoint shape is absent where interfaces are claimed
- more than one endpoint claims the same authoritative mutation without explicit split semantics
- named contracts, snapshots, or objects appear without definition or deferment note
- known business scenarios are missing from coverage
- internal class/method names are treated as mandatory design outputs
- technology choices are asserted without evidence when current facts matter
- dominant bottleneck is never identified
- only one safe mainstream candidate is presented when stronger alternatives should be evaluated
- security or performance assumptions are left implicit
- unresolved quality concerns disappear
