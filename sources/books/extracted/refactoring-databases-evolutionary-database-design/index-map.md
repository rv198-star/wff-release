# Refactoring Databases: Evolutionary Database Design — Index Map

## Scope

- Source file:
  - `sources/books/original/phase-02-design-architecture/refactoring-database-evolutionary-database-design.md`
- Extraction depth:
  - `index-map -> knowledge-card-draft -> stage-guidance-draft`
- Book type judgment:
  - `method-heavy`
  - `system / engineering-governance support`
- Primary Stage focus:
  - `architecture`
  - `data-storage-and-interface-design`
  - `development`
  - `release-prep`
- Current downstream target:
  - Phase-2 `data-storage-and-interface-design`
  - Phase-2 `design-convergence-and-delivery-prototype`
  - Phase-3 database-change / bootstrap / rollback governance support

## Extraction boundary (pass-1)

This is a bounded first pass.

- Extracted in pass-1:
  - Chapter 1: focus on `evolutionary data modeling`, `database regression testing`, `configuration management`, `developer sandboxes`
  - Chapter 2: focus on the definition and boundary of `database refactoring`
  - Chapter 3: focus on the executable process of database refactoring in single- and multi-application environments
  - Chapter 4: focus on deployment discipline, sandbox promotion, release bundles, backout
  - Chapter 5: focus on strategic rules with highest downstream value for this repo
- Deferred (index-only in pass-1):
  - exhaustive catalog extraction from Chapters 6-11
  - vendor-specific SQL examples
  - UML notation appendix

## Section map (organized by use)

| Section (by use) | Core problem solved | Stage | Type | Priority |
|---|---|---|---|---:|
| Evolutionary data modeling | Avoids up-front database freeze while preserving high-level modeling discipline | architecture | concept / method / boundary | very high |
| Database refactoring definition | Separates schema refactoring from feature change and from pure data change | architecture | concept / boundary | very high |
| Database regression testing | Makes schema change safe by requiring repeatable regression tests and rollback posture | development | method / checklist | very high |
| Configuration-managed database assets | Ensures schema scripts, migration scripts, data models, and reference data are versioned like code | development | checklist / governance | very high |
| Developer sandboxes | Requires isolated environments to test schema changes before promotion | development | method / boundary | very high |
| Refactoring process | Provides a stepwise flow: verify, choose, deprecate, test, modify, migrate, update consumers, regression-test, version, announce | architecture / development | method | very high |
| Transition period and scaffolding | Supports old/new schema in parallel for multi-application environments | architecture | method / risk / handoff | very high |
| Ordered refactoring bundles and version ids | Makes release packaging, replay, and environment synchronization possible | development / release-prep | governance / checklist | high |
| Deployment between sandboxes | Defines promotion gates, test-before/test-after discipline, and production backout | release-prep | method / checklist | very high |
| Small changes and encapsulated DB access | Reduces blast radius and coupling during schema evolution | architecture / development | heuristic / boundary | high |
| Database configuration table | Makes schema version explicit and machine-checkable | development | checklist / governance | high |
| Trigger-based synchronization during transition | Gives a default synchronization strategy for dual-schema periods | architecture | decision rule / risk | medium |

## Planned card clusters (pass-1)

- `database-refactoring-retains-behavioral-and-informational-semantics.md`
- `evolutionary-data-modeling-combines-high-level-modeling-with-jit-detail.md`
- `database-regression-tests-enable-safe-schema-evolution-and-rollback.md`
- `developer-sandboxes-and-config-managed-db-assets-enable-safe-change.md`
- `database-refactoring-process-needs-verify-deprecate-migrate-test-version-and-announce.md`
- `multi-application-schema-change-needs-transition-period-and-scaffolding.md`
- `bundle-db-refactorings-with-unique-ids-and-schema-version-tracking.md`
- `production-deployment-needs-backup-retest-and-backout-discipline.md`

## Planned card clusters (pass-2)

- `prefer-small-schema-changes-to-reduce-defect-localization-cost.md`
- `encapsulate-database-access-and-avoid-duplicated-sql.md`
- `prefer-triggers-for-transition-period-synchronization-but-watch-performance.md`
- `installation-script-must-create-upgrade-and-verify-a-database-environment.md`

## Skip / low-value (for this repo)

- publisher / copyright / praise / biography pages
- exhaustive refactoring catalog mirroring
- database-vendor-specific syntax detail when the underlying decision rule is already captured
