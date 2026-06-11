# Stage-02.5 Merge Decisions — third-party-integration-architecture-design

## Cluster A — activation discipline
- rules: RC-01, RC-02
- decision: KEEP-SEPARATE-BUT-LINKED
- reason: activation and skip justification are different gates

## Cluster B — active-lane structural completeness
- rules: RC-03, RC-04, RC-05, RC-06, RC-07
- decision: KEEP-SEPARATE-BUT-LINKED
- reason: manifest, IDR, adapter, test, and risk surfaces must stay independently checkable

## Cluster C — downstream consumption
- rules: RC-08, RC-09, RC-10
- decision: KEEP-SEPARATE-BUT-LINKED
- reason: adapter isolation, resilience posture, and downstream consumption are related but not identical

