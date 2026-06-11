# Phase-1 PRD Convergence Smoke Test（v0.1）

## 1. Purpose

This checklist is used AFTER the PRD main document is assembled from Stage outputs.

It answers one question: **Can Phase-2 (design/architecture) start work using ONLY this PRD, without needing to read raw Stage-01~04 outputs?**

It is NOT a replacement for the PRD Deep-Compilation Acceptance Checks (which assess document quality).
It is a **consumer-perspective readiness test**.

---

## 2. Quick Checks (pass/fail)

Run these first. Any FAIL blocks convergence sign-off.

| # | Check | Pass condition | Fail action |
|---|---|---|---|
| QC-1 | **Scope boundary is actionable** | §12 MVP Definition contains explicit in-scope / out-of-scope / deferred lists that an architect can use to draw system boundary without guessing | Return to Stage-03/04 output review |
| QC-2 | **Main flows are walkable** | §7 Business Scenarios + §8 Requirements Structure contain at least 3 step-by-step scenarios an architect can trace through without asking "what happens between step X and Y?" | Deepen §7 scenarios |
| QC-3 | **NFR state is consumable** | §9 NFR section exists AND either contains quality-scenario tables (if 02b executed) OR contains NFR initial identification scan with dimension relevance + information state (if 02b skipped) | Return to Stage-02a/02b output |
| QC-4 | **Handoff is self-contained** | §18 Handoff contains safe_start_scope, forbidden_assumptions, and unresolved_truths — all three must be non-empty and specific (not generic placeholders) | Return to Stage-04 handoff assembly |
| QC-5 | **Decision rationale exists** | §17 Key Decision Rationale contains at least 3 substantive decisions with explicit "why this not that" reasoning | Deepen §17 |
| QC-6 | **Validation conclusion is honest** | §13 Validation contains three-dimensional verdict (value / usability / feasibility) with evidence_summary per dimension — not just a blanket "validated" | Return to Stage-04 validation |
| QC-7 | **Truth honesty is maintained** | §16 Dependencies & Review-Bound Truth contains at least one item — a PRD with zero review-bound truths is suspicious of false certainty | Review for suppressed uncertainty |

---

## 3. Depth Probes (structural test)

Run these after all Quick Checks pass. These test whether the PRD has enough depth for Phase-2 to work, not just enough structure.

### DP-1: Module Boundary Derivation Test

**Question**: From §8 (Requirements Structure) and §10 (Domain Model, if present), can you identify at least 3 distinct capability groups / module boundaries without needing to read Stage-02a/02b raw outputs?

- **PASS**: 3+ capability groups are identifiable from PRD content alone, with clear separation rationale
- **SOFT FAIL**: capability groups exist but boundaries are vague — architect would need to ask clarifying questions
- **HARD FAIL**: no capability grouping is derivable from the PRD

### DP-2: NFR Architecture Consequence Test

**Question**: For each NFR dimension marked `relevant` or `identified` in §9, does the PRD explain (even briefly) what architecture consequence this NFR has? (e.g. "performance: sub-200ms response → implies caching layer or read replica")

- **PASS**: at least 2 NFR dimensions have explicit architecture consequence notes
- **SOFT FAIL**: NFR dimensions are listed but consequences are generic or absent
- **HARD FAIL**: §9 is empty or placeholder-only

### DP-3: Forbidden Assumption Specificity Test

**Question**: In §18 Handoff → forbidden_assumptions, are the items **specific enough** that an architect could write a concrete check against them? (e.g. "do not assume payment integration is in-scope for MVP" vs. generic "do not assume scope is final")

- **PASS**: all forbidden assumptions are specific and testable
- **SOFT FAIL**: some are specific, some are generic
- **HARD FAIL**: all are generic or section is empty

---

## 4. Scoring

| Result | Action |
|---|---|
| All QC pass + all DP pass | Convergence approved — PRD is Phase-2 ready |
| All QC pass + DP soft fails only | Convergence conditional — note soft fails in handoff, Phase-2 intake must acknowledge |
| Any QC fail | Convergence blocked — fix before handoff |
| Any DP hard fail | Convergence blocked — PRD lacks necessary depth |

---

## 5. Usage rule

- This checklist should be run by the person/agent responsible for PRD convergence (typically after Stage-04 completion, during UPP assembly)
- Results should be recorded in the PRD's §19 (Acceptance & Status) or equivalent
- If the PRD was produced by an AI agent, a separate reviewer (human or different agent) should run this checklist to avoid self-grading bias
