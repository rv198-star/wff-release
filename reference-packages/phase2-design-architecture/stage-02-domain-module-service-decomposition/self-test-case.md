# Stage-02 Self-Test Case — boundary package to decomposition package

## 1. Test Goal

Use one Stage-01-style architecture entry brief to verify that Stage-02 can produce a usable decomposition package.

Focus:

- domain/module/service partitioning
- responsibility and dependency clarity
- lifecycle ownership closure
- conceptual object relationship clarity
- domain event flow clarity
- declaration-state/NFR carryover
- Stage-03-consumable handoff

---

## 2. Input Brief

> Stage-01 already froze a modular meeting-assistant architecture with capabilities for ingestion, note processing, summary review, action extraction, and CRM sync. Boundary is clear. Quality gaps remain around latency and auditability.

---

## 3. Expected Stage-02 Behavior
- derive explicit domain/module/service candidates from Stage-01 capabilities
- derive a conceptual entity relationship view for core business objects
- derive a domain event catalog where state transitions matter downstream
- keep aggregate lifecycle states owner-realizable instead of pushing completion into downstream read-only modules
- preserve unresolved quality items rather than hide them
- provide dependency/collaboration map

---

## 4. Expected Minimum Output Shape
- domain map
- module map
- service candidates
- responsibility matrix
- dependency/collaboration map
- conceptual entity relationship diagram
- domain event catalog
- decomposition decisions with provenance markers if inferred

---

## 5. PASS / FAIL

### PASS if:
- Stage-03 can design data/interfaces from the result
- Stage-03 does not need to reinvent core object relationships or event triggers
- dependencies and ownership are explicit
- lifecycle states can be executed by declared owners without hidden downstream writeback

### FAIL if:
- decomposition is only a renamed capability list
- hidden ownership overlap remains
- lifecycle closure depends on a read-only downstream consumer mutating upstream truth
- object chain or event flow is only implied narratively
- unresolved quality concerns disappear from handoff
