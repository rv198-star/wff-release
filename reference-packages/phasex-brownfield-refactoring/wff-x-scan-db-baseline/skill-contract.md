# wff-x-scan-db-baseline Skill Contract — scan-db-baseline

## 1. Skill Goal

- Extract the current data architecture into a structured brownfield baseline.
- Make schemas, tables, relationships, indexes, constraints, sensitive fields, and migration pressure explicit before target architecture or implementation work begins.
- Produce P2-consumable data constraints and only limited P3 seed material for migration or persistence-risk cases.

## 2. Inputs

- required:
  - accessible database, DDL, schema dump, migration directory, or ORM model set
  - current repository baseline from `wff-x-scan-code-baseline` when available
- optional:
  - data dictionary
  - ER diagram
  - query logs
  - migration history
  - operational notes about data volume, retention, or compliance

## 2.1 Cannot Infer

- true production data volume from local schema alone
- real data quality from field names alone
- regulatory classification without source evidence or owner statement
- domain ownership of tables without code, document, or stakeholder evidence

## 2.2 Must Validate Before Exit

- schema source and confidence are explicit
- major tables, key entities, relationships, and constraints are listed
- sensitive fields and uncertainty are recorded instead of silently ignored
- `database_truth_packet` separates observed data evidence, inferred schema semantics, migration pressure, explicit unknowns, and downstream truth implications
- P2 consumption material is clearly separated from P3 seed material

## 3. Outputs

- database baseline summary
- database truth packet:
  - observed data evidence
  - inferred schema semantics
  - migration pressure
  - explicit unknowns
  - downstream truth implications
- table / entity inventory
- relationship and constraint map
- index and query-risk notes
- sensitive data register
- P2 consumption packet
- P3 seed material for migration or persistence-risk cases

## 4. Gate Conditions

- `PXG-02-1`: data source, schema confidence, and table/entity inventory are present
- `PXG-02-2`: key relationships, constraints, and indexes are recorded or explicitly unknown
- `PXG-02-3`: sensitive fields and compliance uncertainty are reviewable
- `PXG-02-4`: P2-consumable data constraints are explicit, and P3 seed material is clearly marked as non-authoritative

## 5. Acceptance Criteria

- P2 can consume the data baseline without rediscovering schema shape from scratch
- table facts, schema inferences, and unknowns are separated
- persistence or migration hotspots are preserved as P3 seed material without becoming implementation instructions
- data risk claims are capped by available schema and runtime evidence

## 6. Boundaries

- no target data architecture here
- no migration plan here
- no direct database refactor execution here
- no unsupported claims about production data volume, quality, compliance, or ownership

## 7. Flow Rules

- typical downstream:
  - `wff-x-design-target-arch` for target architecture design
  - P2 data/storage/interface design when the case re-enters the main lifecycle
  - `wff-x-plan-migration` when migration or cutover semantics are later opened
