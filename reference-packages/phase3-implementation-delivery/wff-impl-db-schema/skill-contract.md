# wff-impl-db-schema Skill Contract

## Responsibility

Generate database schema delivery artifacts from accepted Phase-2 data/storage contracts.

## Inputs

- Phase-2 data ownership and storage design.
- P2 entity/table/relationship constraints.
- ActionCards when available.

## Outputs

- database schema DDL or migration-ready schema draft.
- schema tests or schema verification notes.
- persistence assumptions and review-bound gaps.

## Boundaries

- Do not redesign the storage architecture.
- Do not replace DBA, migration, or production cutover approval.
- Do not hide unresolved data ownership or sensitive-field gaps.

## Runtime

Use `scripts/phase3/run_impl_db_schema.py`.
