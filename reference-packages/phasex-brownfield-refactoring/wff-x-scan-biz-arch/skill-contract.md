# wff-x-scan-biz-arch Skill Contract — scan-biz-arch

## 1. Skill Goal

- Recover the current business semantics of the existing system so P1 can re-enter with source truth instead of implementation guesswork.
- Make business flows, roles, permissions, rules, exceptions, vocabulary, and unknowns explicit before target architecture or GAP work begins.
- Produce P1-consumable business truth with secondary P2 constraints.

## 2. Inputs

- required:
  - at least one credible source of business behavior: code behavior, product docs, user manuals, support tickets, logs, stakeholder notes, or `wff-x-scan-code-baseline`
- optional:
  - `wff-x-scan-db-baseline` data baseline
  - process diagrams
  - role / permission matrix
  - incident, defect, or operations history

## 2.1 Cannot Infer

- real business priority from code frequency alone
- business owner intent from implementation shape alone
- role authority from route names alone
- current policy truth from stale documentation

## 2.2 Must Validate Before Exit

- business evidence and implementation inference are separated
- core flows and roles are listed with confidence
- P0 / P1 flow priority is explained using role, frequency, and risk
- unknown business truth is preserved for P1 instead of filled by implementation guesses
- P2-facing constraints are secondary and marked as such

## 3. Outputs

- business baseline summary
- business truth packet:
  - observed business evidence
  - inferred business semantics
  - explicit unknowns
  - source conflict notes
  - downstream truth implications
- role and actor inventory
- process and workflow map
- business rule register
- exception and edge-case register
- P1 consumption packet
- P2 secondary consumption packet

## 4. Gate Conditions

- `PXG-03-1`: core business flows are listed and prioritized as `P0 | P1 | P2 | unknown`
- `PXG-03-2`: each core role has at least one linked action or explicit unknown
- `PXG-03-3`: business rules and implementation-derived inferences are not mixed
- `PXG-03-4`: P1 can see source truth, unknowns, and claim ceilings without treating implementation details as final product truth

## 5. Acceptance Criteria

- P1 can consume the package as brownfield source input
- P2 can consume secondary boundary and invariant hints without treating them as architecture decisions
- implementation facts are not promoted into business truth unless evidence supports the promotion
- conflicts between docs, code, and observed behavior are named

## 6. Boundaries

- no target product requirement authoring here
- no target architecture here
- no stakeholder sign-off claim
- no market validation claim
- no permission to overwrite P1 business judgment with code structure

## 7. Flow Rules

- typical downstream:
  - P1 constrained source-truth admission
  - `wff-x-design-target-arch` when target architecture is later opened
  - P2 boundary and invariant review as secondary consumption
