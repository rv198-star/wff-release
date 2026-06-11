# Stage-04 Self-Test Case — Stage-03 MVP slicing to validation conclusion

## 1. Test Goal

Use a valid Stage-03 MVP/slicing package to test whether Stage-04 can:

- identify explicit validation targets
- create a validation chain from hypothesis to decision
- produce a usable conclusion and revision recommendation
- prepare a design/architecture-consumable handoff

---

## 2. Simulated Upstream Input

Use the Stage-03 dry-run output for the restaurant-owner AI reply assistant as the upstream package, including:

- MVP definition
- first/later/deferred slicing
- key assumptions to validate
- provisional status preserved

---

## 3. Expected Stage-04 Behavior

### 3.1 Expected validation focus
The skill should:

- identify a specific assumption or decision to validate
- choose a lightweight validation method
- produce a conclusion that clearly changes or confirms something
- produce a revision path or a confirmation path

### 3.2 Expected provisional behavior
- Stage-04 should not erase review-bound uncertainty from Stage-03.
- If the conclusion still depends on weak evidence, that uncertainty must stay visible.

### 3.3 Expected structure behavior
- The stage should make the chain hypothesis → method → result → decision explicit.
- A `validation-flow` is recommended but not mandatory.

---

## 4. Expected Minimum Output Shape

The resulting Stage-04 output should include at least:

- validation target / hypothesis
- validation method
- signal / feedback / result
- decision state
- revision recommendation
- design/architecture handoff package

---

## 5. Expected Acceptance Judgment

### PASS if:
- a clear validation target exists
- a usable conclusion exists
- revision recommendations exist
- design/architecture could understand what changed and what remains risky

### FAIL if:
- there is no explicit validation target
- there is feedback but no decision state
- there is a conclusion but no revision consequence
- unresolved assumptions disappear as if fully validated
