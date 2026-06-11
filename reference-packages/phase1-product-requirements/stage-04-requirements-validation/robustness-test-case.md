# Stage-04 Robustness Test Case — refusal / blocked / fake-validation paths

## 1. Goal

Test Stage-04 against failure-path behavior already defined in the runtime files.

This round focuses on:

- refusal when no explicit validation target exists
- blocked when the target is too vague to design a method/signal chain
- fail when there is feedback but no explicit decision or revision consequence

---

## 2. Case A — refusal: no explicit validation target

### Input
- Stage-03 package with slices but no explicit key assumption / risk / decision to validate

### Expected behavior
- refuse or not start
- explain that no explicit validation target exists

---

## 3. Case B — blocked: target too vague

### Input
- “We should validate whether users like it” with no hypothesis or decision target

### Expected behavior
- enter blocked or equivalent non-progress state
- explain that method/result/decision chain cannot be defined from this target

---

## 4. Case C — fake validation: feedback with no decision consequence

### Input
- prototype shown, some positive comments noted, but no Go / No-Go / Revise and no revision recommendation

### Expected behavior
- fail Stage-04 acceptance
- explain that feedback alone is not a complete validation result
