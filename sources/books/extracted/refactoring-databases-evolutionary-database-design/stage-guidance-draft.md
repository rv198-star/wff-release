# Refactoring Databases: Evolutionary Database Design — Stage Guidance Draft

## Goal

Turn *Refactoring Databases: Evolutionary Database Design* into a reusable **schema-evolution and database-change-governance pack** for this repository.

This bundle is not trying to mirror the full refactoring catalog. It is primarily used to:

- define what database refactoring is and is not
- keep schema change evolutionary instead of big-bang
- make transition periods, scaffolding, migration, and rollback explicit
- connect schema evolution to build/test/deploy discipline

## Boundary

- This bundle does **not** replace static data-modeling references such as logical schema design, normalization, or ER-only design books.
- This bundle does **not** aim to exhaustively extract every structural/data-quality/ref integrity refactoring in pass-1.
- This bundle **does** provide reusable rules for evolutionary schema change, transition governance, deployment discipline, and change packaging.

## Best-fit mapping in this repository

This bundle is best treated as a cross-phase supporting source with two primary landing zones:

- Phase-2 `data-storage-and-interface-design`
- Phase-2 `design-convergence-and-delivery-prototype`

And one downstream support lane:

- Phase-3 schema-change / environment-bootstrap / rollback discipline

## Phase-2 outcomes this bundle should support

### 1. Schema evolution is modeled as bounded change, not one-shot redesign

- high-level data modeling may happen early
- detailed schema evolution should happen just in time
- large schema change should be decomposed into small executable steps

### 2. Database changes preserve both behavior and information meaning

- schema improvement must not silently mutate data meaning
- database refactoring must be separated from product/behavioral feature change

### 3. Multi-application compatibility is first-class

- if external programs are out of sync, the design must explicitly support a transition period
- scaffolding code, deprecated schema markers, and removal timing must be part of the design package

### 4. Schema design must include deployment and rollback truth

- design is incomplete if it ignores change scripts, migration scripts, environment promotion, and backout posture
- schema versioning and change ordering need machine-readable anchors

## Recommended card set (first absorption)

- `database-refactoring-retains-behavioral-and-informational-semantics.md`
- `evolutionary-data-modeling-combines-high-level-modeling-with-jit-detail.md`
- `database-regression-tests-enable-safe-schema-evolution-and-rollback.md`
- `developer-sandboxes-and-config-managed-db-assets-enable-safe-change.md`
- `database-refactoring-process-needs-verify-deprecate-migrate-test-version-and-announce.md`
- `multi-application-schema-change-needs-transition-period-and-scaffolding.md`
- `bundle-db-refactorings-with-unique-ids-and-schema-version-tracking.md`
- `production-deployment-needs-backup-retest-and-backout-discipline.md`

## Recommended Stage-2 absorption points

### `data-storage-and-interface-design`

Absorb as:

- schema evolution boundary rules
- migration and rollback expectations
- transition-period compatibility strategy
- versioned change-script and migration-script language

Best-fit output consequences:

- schema design sections should include `change strategy`, `migration path`, `compatibility rule`, `rollback signal`
- database design should not stop at `DDL shape`

### `design-convergence-and-delivery-prototype`

Absorb as:

- release bundle / deployment-window awareness
- deprecated-schema removal checkpoints
- consumer-update communication and release-note discipline

Best-fit handoff consequences:

- implementation-facing handoff should include database change ordering
- release-facing handoff should include deprecated-surface lifecycle and environment promotion notes

## Recommended Phase-3 support points

### `implementation-readiness-and-task-alignment`

Use as support for:

- change-log / update-log / migration-log expectations
- schema version tracking
- environment bootstrap realism

### `implementation-audit-and-handoff-gate`

Use as support for:

- rollback and backout honesty
- whether old/new schema coexistence has been explicitly planned
- whether database changes are still tightly coupled to duplicated SQL or uncontrolled direct access

## Future expansion (pass-2 candidates)

- structural refactoring selection cards from Chapters 6-9
- trigger/view/batch synchronization comparison card
- installation script and environment setup discipline card
- encapsulation / duplicate SQL reduction cards
