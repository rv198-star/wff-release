# wff-x-scan-db-baseline Source Cards — scan-db-baseline

## Primary Inputs

- `wff-x-scan-code-baseline` codebase baseline output when available
- DDL, migration files, ORM models, or database schema dump
- `docs/source-registers/phaseX-source-library-seed-v0.1.md`
- `sources/books/extracted/refactoring-databases-evolutionary-database-design/`

## Method Cards To Apply

- schema is an evolvable asset, not only a snapshot
- database refactoring must preserve information semantics as well as behavior
- schema version tracking and migration history matter for brownfield planning
- shared schemas create compatibility windows and transition-period risk
- database regression tests are evidence inputs for later migration or cutover work

## Anti-Patterns

- treating table names as business truth
- treating missing foreign keys as proof that relationships do not exist
- declaring migration safety from static schema only
- hiding sensitive-data uncertainty because the current task is not compliance-focused
- producing a P3 implementation plan before P2 has consumed the data constraints
