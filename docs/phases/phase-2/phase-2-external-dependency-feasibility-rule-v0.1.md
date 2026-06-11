# Phase-2 External Dependency / API Feasibility Rule（v0.1）

## 1. Why this rule exists

The restaurant-owner happy-path case exposed a serious Phase-2 weakness:

- the product context depended on WeChat-style messaging
- Phase-2 correctly modeled an integration/adapter boundary
- but it did **not** escalate the fact that real API/control feasibility was unknown or difficult enough
- the result was an engineering spec that looked cleaner than the real realizability state

This rule exists to stop that failure pattern.

---

## 2. Core rule

If a business case depends on an external platform, API, or integration boundary for its mainline workflow, then Phase-2 must classify the dependency explicitly as one of:

1. **available and usable**
2. **available but constrained**
3. **unknown / unverified**
4. **not available for first-pass realization**

It is not acceptable to describe such a dependency only as a generic “adapter” or “adjacent system” if feasibility is actually uncertain.

---

## 3. Required Phase-2 handling

### A. In Architecture Summary
The dependency must be named explicitly in:

- system boundary notes
- constraint posture / NFR posture
- key architecture decisions

### B. In Delivery Expression
Phase-2 must state whether the first-pass realization mode is:

- real integration
- constrained integration
- simulated/manual boundary

### C. In Implementation-Facing Handoff
Phase-2 must say what implementation may and must not assume.

At minimum, it must answer:

- may implementation assume direct integration exists?
- if not, what substitute boundary is allowed for first-pass realization?

---

## 4. Decision threshold

### If the dependency is central but feasibility is unresolved
Then the item is:

- at least **Downstream-Risk-Amplifying Carryover**
- and may become **Must-Resolve-Before-Next-Phase** if no honest first-pass substitute boundary exists

### If a clean substitute exists
Then Phase-2 may continue, but must explicitly say so.

Example:

- direct platform API unavailable
- first-pass realization may use manual/simulated ingest boundary instead

That is acceptable **only if stated explicitly**.

---

## 5. Anti-pattern to forbid

Do not let Phase-2 outputs use language like:

- “integration adapter”
- “external boundary”
- “channel interface”

as if those phrases alone solved engineering feasibility.

If actual access/SDK/API reality is uncertain, the uncertainty must stay visible.

---

## 6. Immediate interpretation

This rule should be used as a review lens for:

- future Phase-2 happy-path trials
- engineering spec pack evaluation
- convergence reviews where a case appears technically plausible at the prose layer but risky at the realization layer
