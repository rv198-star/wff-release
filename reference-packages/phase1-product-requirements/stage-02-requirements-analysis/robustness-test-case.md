# Stage-02 Robustness Test Case — refusal / blocked / false-structure paths

## 1. Goal

Test Stage-02 against failure-path behavior already defined in the runtime files.

This round focuses on:

- refusal when Stage-01 structure is missing
- blocked when structure would depend on non-inferable missing fields
- fail when only flat story/task lists exist without a panorama

---

## 2. Case A — refusal: no Stage-01 structured input

### Input
- only a vague note pile from Stage-01 with no user-group boundary and no structured problem/opportunity list

### Expected behavior
- refuse or return to Stage-01
- explain that foundational research conclusions are missing

---

## 3. Case B — blocked: upstream non-inferable fields still absent

### Input
- a pseudo Stage-01 package with no confirmed user boundary and no explicit goal direction

### Expected behavior
- enter blocked or equivalent non-progress state
- explain that the panorama would be fabricated from missing non-inferable fields

---

## 4. Case C — structure fail: only flat list exists

### Input
- a list of 8 user stories / tasks with no goals, activities, constraints, or main flow

### Expected behavior
- fail Stage-02 acceptance
- explain that whole-picture structure evidence is missing
- return to structure-building or upstream clarification
