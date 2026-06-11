# Stage-03 Robustness Test Case — refusal / blocked / fake-slice paths

## 1. Goal

Test Stage-03 against failure-path behavior already defined in the runtime files.

This round focuses on:

- refusal when no whole-picture structure exists upstream
- blocked when MVP boundary depends on non-inferable missing fields
- fail when slicing is only a phased backlog list

---

## 2. Case A — refusal: no panorama upstream

### Input
- Stage-02 package with only a rough feature list and no story-map / equivalent structure

### Expected behavior
- refuse or return
- explain that slicing cannot start without a defensible whole-picture structure

---

## 3. Case B — blocked: MVP boundary depends on unresolved hard assumptions

### Input
- Stage-02 package where the core user/value model is still unknown, but slicing is requested anyway

### Expected behavior
- enter blocked or equivalent non-progress state
- explain that the MVP boundary would be fabricated from unresolved non-inferable assumptions

---

## 4. Case C — fake slicing: phased list without slice logic

### Input
- “Phase 1 do A/B/C, Phase 2 do D/E/F” with no viable loop, no dependencies, and no deferred-item rationale

### Expected behavior
- fail Stage-03 acceptance
- explain that this is a phased list, not an MVP slice-map
