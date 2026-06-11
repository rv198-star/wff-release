# Stage-03 Merge Decisions — data-storage-and-interface-design

## Cluster A — Data/interface closure
- rules: RC-01, RC-04, RC-05, RC-06, RC-07
- decision: KEEP-SEPARATE-BUT-LINKED
- reason: data, storage, interface, and interaction controls are related but independently verifiable.

## Cluster B — Input and truth-boundary controls
- rules: RC-02, RC-03, RC-09, RC-10, RC-12
- decision: KEEP-SEPARATE-BUT-LINKED
- reason: upstream dependency, refusal criteria, declaration semantics, anti-fake-certainty, and provisional marking must stay separate.

## Cluster C — Method boundary controls
- rules: RC-08, RC-11
- decision: KEEP-SEPARATE-BUT-LINKED
- reason: diagram obligation and lens-only constraints should remain explicit.
