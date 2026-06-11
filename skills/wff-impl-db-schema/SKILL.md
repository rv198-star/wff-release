---
name: wff-impl-db-schema
description: Use when generating only the Phase-3 database schema, migration, and schema/SQL test surfaces from a completed Phase-2 handoff.
---

# Phase-3 DB Schema Implementation

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


## Scope

This skill owns the DB schema capability inside P3.
It materializes database migration and schema/SQL test surfaces without creating backend API or frontend web applications.

Use it when:
- the user wants to inspect or validate database structure independently
- a P2 Engineering Spec Pack has schema draft rows
- backend/frontend implementation should remain untouched

Do not use it to decide a new database architecture. Storage posture and schema ownership come from P2; unresolved design gaps must be returned upstream or marked review-bound.

## Reference Package

Read `reference-packages/phase3-implementation-delivery/wff-impl-db-schema/` for the capability contract, SOP, output template, and source cards.

## Runner

Primary command:

```bash
python3 scripts/phase3/run_impl_db_schema.py \
  --phase2-root <phase2-root> \
  --output-dir <phase3-output>
```

Primary outputs:
- `db/migrations/001_initial_schema.sql`
- `tests/schema/*`
- `tests/sql/*`
- `db-schema-report.json`

## Completion Standard

This skill is complete when the migration and schema/SQL tests are generated and `db-schema-report.json` records the table count and report paths.
It does not prove runtime DB correctness; runtime proof still requires verification on the selected database environment.
