# Traceability Management Skill Support

This skill package contains the support scripts for the `wff-base-traceability-management` skill.

Its purpose is to provide a lightweight, project-bound registry/index layer for docs-first traceability.

## Principles

- Documents remain the source of truth.
- SQLite is derived and project-bound.
- IDs are allocated by the skill, not free-typed by authors.
- Chinese audit mirrors are linked through `canonical_of`, not given a parallel business identity system.

## Planned v0.1 scripts

- `init_registry.py`
- `allocate_id.py`
- `bind_artifact.py`
- `link_artifacts.py`
- `validate_registry.py`
- `report_registry.py`
- `trace_upstream.py`
