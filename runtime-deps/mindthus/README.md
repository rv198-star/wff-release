# Mindthus External Reference

This directory pins the external Mindthus methodology source used by this
project during the migration away from duplicated local methodology documents.

Tracked files:

- `mindthus.lock.json`: the pinned upstream repo, tag, commit, and materialized
  source directory name.
- `README.md`: this operating note.

Generated local files:

- `source/`: a local git checkout of the pinned Mindthus revision. It is ignored
  by this repository and must not be committed.
- `bootstrap-report.json`: the latest bootstrap or preflight result. It is
  ignored because it records local runtime state.

Use:

```bash
python3 scripts/release/bootstrap_mindthus_dependency.py --check-only
python3 scripts/release/bootstrap_mindthus_dependency.py
```

This repo does not install Mindthus skills globally. Runtime integration should
read the pinned source from this fixed external reference location after the
bootstrap/preflight check has succeeded.
