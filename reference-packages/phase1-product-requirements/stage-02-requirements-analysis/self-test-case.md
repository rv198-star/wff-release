# Stage-02 Self-Test Case — Stage-01 provisional handoff to structured requirements panorama

## 1. Test Goal

Use a Stage-01-style provisional handoff to test whether Stage-02 can:

- preserve upstream uncertainty
- build a real requirements panorama instead of a flat list
- satisfy the required structure-evidence gate
- prepare a Stage-03-consumable handoff without pretending unresolved assumptions are confirmed

---

## 2. Simulated Upstream Input

Use the Stage-01 dry-run case for the restaurant-owner AI reply assistant as the upstream package, including:

- explicit user-group boundary draft
- first-pass User Case / User Story draft
- structured problem / opportunity list
- assumptions and open questions
- provisional status preserved

---

## 3. Expected Stage-02 Behavior

### 3.1 Expected analysis focus
The skill should:

- identify a product/requirements panorama
- distinguish goals, activities, tasks, and constraints
- create a whole-picture structure instead of only listing user stories
- identify at least one high-risk point that later validation should examine

### 3.2 Expected provisional behavior
- Stage-02 should not silently upgrade the still-uncertain primary user boundary.
- If the panorama depends on uncertain assumptions, those assumptions must remain explicit.

### 3.3 Expected diagram behavior
- Stage-02 must produce a `story-map` or `requirements-structure` artifact.
- If the structure artifact is missing or flat, the test should fail.

---

## 4. Expected Minimum Output Shape

The resulting Stage-02 output should include at least:

- goal
- backbone activities
- task structure
- key constraints
- initial priority split
- high-risk validation point
- diagram / structured evidence metadata
- assumptions / open questions / provenance markers if uncertainty remains

---

## 5. Expected Acceptance Judgment

### PASS if:
- there is a whole-picture structure
- Stage-03 could use the handoff for slicing logic
- upstream provisional uncertainty is preserved

### FAIL if:
- output is just a task/story list
- no diagram/structure evidence exists
- constraints are missing
- provisional assumptions disappear as if confirmed
