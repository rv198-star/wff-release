# Stage-02b Robustness Test Case — refusal / blocked / fake-specification paths

## 1. Goal

Test Stage-02b against failure-path behavior already defined in the runtime files.

This round focuses on:

- refusal when Stage-02a scenario depth is missing
- blocked when specification would depend on non-inferable missing constraints
- fail when output is only feature/screen listing without NFR/domain/IA reasoning

---

## 2. Case A — refusal: no Stage-02a scenario depth

### Input
- a pseudo Stage-02a package that contains only backbone activities and a rough story map, but no usable business scenario analysis

### Expected behavior
- refuse or return to Stage-02a
- explain that specification deepening cannot proceed without scenario-level depth

---

## 3. Case B — blocked: critical specification truth is non-inferable

### Input
- a Stage-02a-like package where security/privacy/tenancy context is missing, but the requested output would require architecture-constraining decisions about data control and cross-role access

### Expected behavior
- enter blocked or equivalent non-progress state
- explain that critical NFR or domain-boundary decisions would be fabricated from missing non-inferable truth

---

## 4. Case C — fake specification: feature nouns / screen wishlists only

### Input
- a draft that lists pages, features, and “should be secure / fast / easy to use,” but contains:
  - no NFR prioritization reasoning
  - no conceptual domain model
  - no IA direction rationale
  - no specification stress-test

### Expected behavior
- fail Stage-02b acceptance
- explain that specification-grade reasoning is missing
- return to Stage-02b deepening or upstream clarification
