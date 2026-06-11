# Stage-03 Self-Test Case — Stage-02 panorama to MVP slicing

## 1. Test Goal

Use a valid Stage-02 structured requirements panorama to test whether Stage-03 can:

- identify a complete experience loop
- cut a minimum viable experience loop
- separate first slice, later slices, and deferred items
- satisfy the required `slice-map` evidence gate
- prepare a Stage-04-consumable handoff without pretending validation is already complete

---

## 2. Simulated Upstream Input

Use the Stage-02 dry-run output for the restaurant-owner AI reply assistant as the upstream package, including:

- goal
- backbone activities
- key constraints
- initial priority split
- high-risk validation point
- provisional status preserved

---

## 3. Expected Stage-03 Behavior

### 3.1 Expected slicing focus
The skill should:

- identify the full experience loop
- cut a minimum viable loop rather than just a smaller feature list
- explain why certain items are first-slice and others are deferred
- carry forward key assumptions that Stage-04 should validate

### 3.2 Expected provisional behavior
- Stage-03 should not erase the Stage-02 review-bound uncertainty.
- If the MVP boundary depends on unresolved user/value assumptions, those assumptions must remain explicit.

### 3.3 Expected diagram behavior
- Stage-03 must produce a `slice-map`.
- If slice boundaries, acceptance targets, or dependencies are missing, the test should fail.

---

## 4. Expected Minimum Output Shape

The resulting Stage-03 output should include at least:

- complete experience loop
- minimum viable experience loop
- first slice
- later slices
- deferred items
- slice rationale
- key assumptions to validate
- slice-map evidence metadata

---

## 5. Expected Acceptance Judgment

### PASS if:
- a real MVP loop exists
- slicing logic is explainable
- deferred items are explicit
- Stage-04 could use the handoff to design validation focus

### FAIL if:
- output is only a phased scope list
- no `slice-map` evidence exists
- deferred items are missing
- unresolved assumptions disappear as if confirmed
