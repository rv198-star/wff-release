---
name: wff-base-traceability-management
description: Use when a docs-first project needs managed artifact identity, project-bound trace registry initialization, canonical ID allocation, file/anchor binding, upstream/downstream link integrity, or traceability reporting beyond manual handoff fields.
---

# Traceability Management

Version: v0.1

## Overview

This skill provides a **document registry management mechanism** for docs-first traceability.

It does not replace documents as the source of truth. Instead, it manages:

- canonical IDs
- file/anchor bindings
- upstream/downstream links
- project-bound SQLite registry initialization
- integrity validation
- trace reports

**Core rule:** Documents own meaning. This skill owns identity, bindings, and link integrity.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write registry explanations, integrity reports, trace summaries, and operator guidance in Chinese
- preserve code, file paths, commands, SQL schema names, trace ids, artifact ids, language-role values, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only traceability reports or governance commentary unless the user explicitly requests English

## When to Use

Use when:
- artifact IDs would otherwise be assigned manually and may drift or collide
- handoff fields exist, but artifact-level traceability is still uncontrolled
- a project needs a project-bound `trace.db` derived index
- file moves/renames would otherwise break trace links
- you need to trace an artifact upstream or inspect broken trace links

Do not use when:
- the user only needs a prose explanation of traceability concepts
- there is no bounded project context
- the request is for a full ALM platform or a global multi-project master database

## Core Model

### Documents remain source of truth
- Documents carry narrative content and business meaning.

### Skill manages registry control
- allocate IDs
- bind IDs to file/anchor locations
- link artifacts with `depends_on` / `feeds`
- validate integrity

### SQLite stays derived and project-bound
- each business project gets its own registry file
- SQLite is a generated/project-owned asset
- not a global shared DB

## Phase-1 / Phase-2 Fine-Grained Rule

For the Phase-1 -> Phase-2 top-down path, distinguish two identity layers:
- document-level fine-grained ids that live in authored markdown
- registry artifact types that live in SQLite

Document-level ids must stay explicit and stable:
- Phase-1 trace units: `P1-US-*`, `P1-UC-*`, `P1-REQ-*`, `P1-AC-*`
- Phase-2 decision traces: `P2-DTR-*`
- Phase-2 contract/public-boundary traces: `P2-CTR-*`
- Phase-2 operation behavior flow traces: `P2-FLOW-*`
- Phase-2 operation collaboration/ordering traces: `P2-SEQ-*`
- Phase-2 operation lifecycle/transition traces: `P2-STATE-*`
- Phase-2 replay evidence: `P2-RP-*`
- Phase-2 RBI traces: `P2-RT-*`

Registry artifact types remain generic:
- `DECISION`
- `INTERFACE`
- `FLOW`
- `SEQUENCE`
- `VERIFY`
- `RISK`

Operation-bound Phase-2 behavior source IDs map onto these generic registry artifact types:
- `P2-FLOW-*` binds as `FLOW` and anchors an operation or operation-family activity/interaction path.
- `P2-SEQ-*` binds as `SEQUENCE` and anchors cross-component ordering, collaboration, async, replay, or external dependency behavior.
- `P2-STATE-*` binds as `FLOW` or `DECISION` when no narrower registry type exists, and anchors aggregate lifecycle transitions, guards, and state effects.

These IDs are required only when the P2-authored shared operation risk row requires them. P3 may consume the bindings but must not invent them or replace them with a private Phase-3 trace family.

Do not collapse the document ids into generic registry ids and then lose the fine-grained Phase-1 / Phase-2 binding semantics.
`upstream_trace_ids` in the authored docs are the canonical bridge from Phase-2 design surfaces back to Phase-1 trace units.

## Commands

### `init-registry`
Initialize a project-bound registry and SQLite file.

Expected inputs:
- project root
- project key
- optional db path

### `allocate-id`
Allocate a canonical artifact ID within the current project scope.

Supported Phase-1 / Phase-2 pilot types now include:
- `REQ`
- `ARCH`
- `BOUNDARY`
- `CAPABILITY`
- `DECISION`
- `DOMAIN`
- `MODULE`
- `SERVICE`
- `ENTITY`
- `EVENT`
- `DEPENDENCY`
- `DATA`
- `SCHEMA`
- `STORAGE`
- `INTERFACE`
- `FLOW`
- `SCENARIO`
- `SECURITY`
- `DEPLOY`
- `PERF`
- `TECHSEL`
- `OPTIMAL`
- `ASSUME`
- `MILESTONE`
- `HANDOFF`
- `PROTOTYPE`
- `SEQUENCE`
- `VERIFY`
- `RISK`

These generic artifact types are registry allocation categories.
They do not replace the fine-grained document ids used in Stage outputs such as `P2-DTR-01` or `P2-CTR-01`.

### `bind`
Bind an allocated ID to:
- file path
- section/anchor
- language role

### `link`
Create a relationship:
- `depends_on`
- `feeds`

### `move` / `rename`
Update bindings when a file moves or is renamed.

### `validate`
Run integrity checks for:
- duplicate IDs
- broken bindings
- missing canonical mirror links
- broken `depends_on` / `feeds`
- cross-project contamination

### `report`
Generate:
- registry summary
- upstream/downstream chain report
- broken-link report
- runtime contract metadata for downstream runners:
  - `registry_db_path`
  - `trace_registry_root`
  - `project_key`
  - `project_root`
  - `project_scope`
  - `schema_version`
  - `artifact_count`
  - `link_count`

## Project Isolation Rule

Each business project must have its own registry.

Recommended v0.1 layout:
- `<project-root>/.trace/trace.db`

Also keep `project_scope` in registry tables as a second isolation guard.

## Chinese Audit Mirrors

Chinese mirror files do not get a second business identity system.

Instead:
- English runtime artifact = canonical identity holder
- Chinese audit artifact = its own registry record
- `canonical_of` links the Chinese mirror back to the English canonical artifact

## v0.1 Pilot Scope

Start with coarse-grained Phase-1 / Phase-2 stage outputs first.

Do not begin with full lifecycle coverage or paragraph-level decomposition.

Pilot goals:
- initialize registry
- allocate IDs
- bind Phase-1 output artifacts
- register `feeds` chain across Stage-01..04
- support upstream trace report
- support Phase-2 coarse stage-chain registration and validation

When Phase-1 fine-grained trace units are present, Phase-2 should additionally:
- preserve explicit `upstream_trace_ids` in authored tables
- link fine-grained Phase-2 rows back to `P1-*` trace units
- treat prose-only upstream references as remediation fallback, not preferred runtime behavior

## Common Mistakes

- Treating SQLite as the truth source
- Letting authors free-type canonical IDs
- Sharing one registry DB across unrelated business projects
- Giving Chinese mirrors new business IDs instead of linking them via `canonical_of`
- Expanding to `implements / verifies / related_*` before the registry core is stable

## Quick Reference

| Need | Command |
|---|---|
| Start a project registry | `init-registry` |
| Create canonical ID | `allocate-id` |
| Attach ID to doc location | `bind` |
| Record upstream/downstream relation | `link` |
| Update after file move | `move` / `rename` |
| Check integrity | `validate` |
| Trace/report | `report` |

## Runtime Report Contract

When a downstream runner consumes the traceability report in JSON form, the report should expose the runtime metadata needed to prove that the registry was actually initialized and bound in the current project scope.

Minimum required JSON fields:
- `registry_db_path`
- `trace_registry_root`
- `project_key`
- `project_root`
- `project_scope`
- `schema_version`
- `artifacts`
- `links`
- `artifact_count`
- `link_count`

If these fields are absent, downstream execution reports should treat the trace runtime as incomplete rather than silently rendering empty placeholders.
