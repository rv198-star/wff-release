# Stage-02 Merge Decisions — domain-module-service-decomposition

## Cluster A — Decomposition closure
- rules: RC-01, RC-04, RC-05, RC-06, RC-07
- decision: KEEP-SEPARATE-BUT-LINKED
- reason: each rule controls a different acceptance point (domain, module, service, dependency).

## Cluster B — Input truth-boundary discipline
- rules: RC-02, RC-03, RC-09, RC-12
- decision: KEEP-SEPARATE-BUT-LINKED
- reason: handoff quality, refusal, declaration semantics, and provisional marking are distinct controls.

## Cluster C — Method boundary controls
- rules: RC-08, RC-10, RC-11
- decision: KEEP-SEPARATE-BUT-LINKED
- reason: diagram obligations and anti-method-creep constraints should stay independently testable.

## Precedence
1. kickoff/lifecycle governance docs
2. templates/handoff constraints
3. Stage-2 stage package intent
4. method assets
5. sample wording
