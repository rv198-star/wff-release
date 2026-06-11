# Stage-02b Self-Test Case — Stage-02a panorama to specification deepening

## 1. Test Goal

Use a valid Stage-02a structural panorama to test whether Stage-02b can:

- identify product-relevant NFR / quality requirements
- produce a conceptual domain model instead of a feature noun list
- derive IA direction decisions that materially constrain Stage-03
- prepare a Stage-03-consumable handoff without pretending unresolved constraints are fully confirmed

---

## 2. Simulated Upstream Input

Use the Stage-02 dry-run output for the restaurant-owner AI reply assistant as the upstream package, including:

- structured requirements panorama / story-map
- backbone activities
- key constraints
- initial priority split
- high-risk validation point
- provisional status preserved

---

## 3. Expected Stage-02b Behavior

### 3.1 Expected specification focus
The skill should:

- identify at least 3 material quality attributes
- turn the scenario/workflow structure into core business entities and relationships
- identify at least 2 IA direction decisions that affect architecture or MVP scope
- explain how Stage-03 slicing would be weaker if this specification layer were missing

### 3.2 Expected provisional behavior
- Stage-02b should not silently upgrade Stage-02a uncertainty into confirmed specification truth.
- If quality thresholds, domain boundaries, or IA choices depend on unresolved context, that dependency must remain explicit.

### 3.3 Expected diagram behavior
- Stage-02b must produce a conceptual domain-model artifact, normally a Mermaid ER diagram.
- If there is no domain-model evidence or no specification stress-test, the test should fail.

---

## 4. Expected Minimum Output Shape

The resulting Stage-02b output should include at least:

- NFR / quality requirements summary
- quality-scenario table for key attributes
- conceptual domain model
- key data characteristics
- IA direction decisions
- specification stress-test
- Stage-03-consumable handoff note

---

## 5. Expected Acceptance Judgment

### PASS if:
- material NFRs are identified with reasoning
- a conceptual domain model exists
- IA direction is explicit where it constrains Stage-03 or architecture
- Stage-03 could use the handoff without re-deriving NFR/domain/IA from scratch

### FAIL if:
- output is only a screen wishlist or feature list
- there is no conceptual domain model
- there is no quality-priority reasoning
- unresolved assumptions disappear as if confirmed
