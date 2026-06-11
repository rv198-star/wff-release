# wff-x-scan-db-baseline SOP — scan-db-baseline

## 1. Positioning

- goal: capture the current data architecture of the existing system
- upstream: schema, DDL, ORM models, migration files, and preferably `wff-x-scan-code-baseline`
- downstream: P2 architecture work, `wff-x-design-target-arch`, or later `wff-x-plan-migration`

## 2. Start Conditions

- required: at least one credible schema source is available
- helpful: migration history, production-like schema dump, data dictionary, or table-volume notes
- blocked: no schema, model, migration, or database access exists

## 3. Standard Execution Steps

1. identify schema source type and confidence
2. list tables, views, collections, or equivalent storage structures
3. group tables into likely entity / aggregate areas with confidence labels
4. record primary keys, foreign keys, unique constraints, and important indexes
5. identify sensitive fields and compliance uncertainty
6. detect shared-database, multi-application, or external synchronization pressure
7. identify migration and cutover seed risks without writing a migration plan
8. separate observed data facts from inferred schema semantics
9. create the P2 data constraint summary
10. create optional P3 seed material only for persistence or migration hotspots

## 4. Process Checkpoints

- schema source and confidence are named
- table/entity inventory is present
- relationship and constraint map is present or unknowns are explicit
- sensitive field register is present
- P2 consumption packet is present
- P3 seed material is marked as seed only, not as ActionCard or implementation truth

## 5. Output Rules

- keep data facts separate from business meaning
- do not infer owner, aggregate, or compliance truth from table names alone
- name unknowns when schema evidence is incomplete
- preserve migration pressure without prematurely selecting a cutover strategy

## 6. Stage Acceptance

- P2 can reason about data architecture constraints without rescanning schema from scratch
- later migration planning can see where persistence risk likely exists
- claim ceiling is explicit when only static schema evidence exists
