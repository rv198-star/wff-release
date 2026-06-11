# Mindthus Release Payload Reference

This directory pins the Mindthus methodology dependency used by WFF release
packs.

Tracked files:

- `mindthus.lock.json`: the pinned upstream repo, tag, commit, local source
  cache directory name, and release payload directory name.
- `release/`: the committed Mindthus release payload shipped inside WFF install
  packs and release bundles. It is a curated `v0.6.2` release payload, not the
  upstream git checkout.
- `README.md`: this operating note.

Generated local files:

- `source/`: a local git checkout/cache of the pinned Mindthus revision. It is
  ignored by this repository and must not be committed or shipped in WFF packs.
- `bootstrap-report.json`: the latest bootstrap or preflight result. It is
  ignored because it records local runtime state.

Use:

```bash
python3 scripts/release/bootstrap_mindthus_dependency.py --check-only
python3 scripts/release/bootstrap_mindthus_dependency.py
```

Bootstrap checks the committed `release/` payload first. If that payload is
present and matches the lock, release evaluation can run offline without cloning
Mindthus. `source/` is only a local fallback/cache used to refresh or repair the
payload; it is not a WFF-maintained source tree.
