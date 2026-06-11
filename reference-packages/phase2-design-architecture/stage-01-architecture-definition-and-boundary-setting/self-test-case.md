# Stage-01 Self-Test Case — architecture-definition-and-boundary-setting

## 1. Test Goal

Use one lightweight Phase-1 handoff brief to verify that Stage-01 can turn product/requirements output into a decomposition-ready architecture-entry package.

This self-test focuses on:

- explicit system boundary framing
- inherited vs inferred constraint separation
- declaration-state handling using `present | absent | unknown | deferred`
- quality/NFR truth-boundary preservation
- Stage-02-consumable handoff structure

---

## 2. Input Brief

> Product/requirements handoff says we are building an AI meeting assistant for SMB sales teams. MVP includes meeting capture, summary review, and action-item sync to one CRM. The upstream package contains main flow, validated scope, and some platform constraints, but non-functional requirements are still incomplete. Privacy concerns are known. Exact latency expectations and audit-retention requirements are still not confirmed.

---

## 3. Expected Stage-01 Behavior

### 3.1 Expected clarification and framing focus
- identify the true system boundary rather than restating product scope only
- separate in-scope, adjacent, and out-of-scope concerns
- preserve upstream declaration-state semantics explicitly
- avoid pretending that partial `key constraints` already equal a complete NFR baseline

### 3.2 Expected provisional / blocked behavior
- if no architecture-entry handoff exists, refuse or block
- if quality attributes remain partial, preserve them as review-bound or explicitly unresolved
- allow architecture direction only as provisional if core constraints remain incomplete

---

## 4. Expected Minimum Output Shape

The resulting dry-run output should include at least:

- system boundary statement
- inherited constraints vs inferred / unknown / deferred constraints
- explicit upstream NFR state
- architecture-facing quality-attribute structure
- security architecture sketch
- capacity estimation
- capability map
- architecture direction and key decisions
- assumptions / open questions / provenance markers where inference exists

---

## 5. Expected Acceptance Judgment

### PASS if:
- Stage-02 can start decomposition without re-deriving Stage-01 from scratch
- unresolved quality/NFR items remain explicit
- inferred architecture content is not silently upgraded into confirmed fact

### FAIL if:
- output is just a restatement of product scope
- boundary and capability framing are missing
- NFR uncertainty disappears from the handoff
- architecture direction is asserted without provenance or caveats
