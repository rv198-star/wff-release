# wff-x-scan-biz-arch SOP — scan-biz-arch

## 1. Positioning

- goal: recover current business semantics from an existing system
- upstream: business documents, code behavior, support evidence, `wff-x-scan-code-baseline`, and optionally `wff-x-scan-db-baseline`
- downstream: P1 constrained source-truth admission and secondary P2 architecture consumption

## 2. Start Conditions

- required: at least one evidence source that shows business behavior
- helpful: user manuals, product specs, route/controller/service behavior, role docs, ticket history
- blocked: only generic repository structure exists and no business behavior can be observed or supplied

## 3. Standard Execution Steps

1. collect business evidence sources and label their confidence
2. identify actors, roles, and permission hints
3. map visible business flows and prioritize them as `P0 | P1 | P2 | unknown`
4. use role, frequency, and risk to justify flow priority
5. extract business rules, exceptions, and invariants
6. compare code behavior against documents and note conflicts
7. separate observed business evidence from implementation-derived inference
8. create a P1 consumption packet with source truth, unknowns, and claim ceilings
9. create a secondary P2 packet with boundary and invariant hints

## 4. Process Checkpoints

- role and actor inventory is present
- core flows are present or explicit unknowns block completion
- priority rationale uses role, frequency, and risk
- business rule register is present
- source conflicts are named when docs and code disagree
- P1 and P2 packets are separated

## 5. Output Rules

- do not turn code structure into business truth without evidence
- do not erase unknowns to make the package look complete
- keep P1-facing source truth separate from P2-facing architecture hints
- write business semantics in terms a product reviewer can challenge

## 6. Stage Acceptance

- P1 can decide what business truth is known, inferred, or still missing
- P2 receives only secondary boundary / invariant hints, not hidden architecture decisions
