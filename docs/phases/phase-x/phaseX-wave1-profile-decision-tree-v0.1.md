# PhaseX Wave-1 Profile Decision Tree（v0.1）

## Purpose

This is the lightweight orchestration surface for the current PhaseX Wave-1 implementation.

It answers one question:

> which minimal PhaseX profile should be used for this brownfield case right now?

## Decision Tree

### Step 1

Is there an existing codebase or legacy runtime that materially constrains the next move?

- if `no`: do not use PhaseX; start from the greenfield mainline
- if `yes`: continue

### Step 2

Is the immediate goal mainly “understand the system and judge technical risk”?

- if `yes`: use `assessment-only`
- if `no`: continue

### Step 3

Is the intended change primarily technical refactoring, testability improvement, or debt reduction while keeping business behavior broadly stable?

- if `yes`: use `technical-refactor`
- if `no`: continue

### Step 4

Is there a bounded local change request that must preserve existing compatibility constraints?

- if `yes`: use `partial-change`
- if `no`: continue

### Step 5

If none of the Wave-1 profiles fit cleanly:

- stop at PhaseX planning boundary
- record that Wave-2 or a broader PhaseX lane is required
- do not fake-fit the case into Wave-1

## Profile Summary

| Profile | Skills | Typical Exit | Use When |
|---|---|---|---|
| `assessment-only` | `PX-SK-01 -> PX-SK-04` | human decision / continue later | baseline and health first |
| `technical-refactor` | `PX-SK-01 -> PX-SK-04 -> PX-SK-07` | Phase-3 | brownfield technical work needs protection |
| `partial-change` | `PX-SK-01 -> PX-SK-06 partial` | Phase-1 or Phase-3 | bounded local change on existing system |

## Decision Notes

### Prefer `assessment-only` when:
- code ownership is unclear
- runnability is uncertain
- no safe change plan exists yet

### Prefer `technical-refactor` when:
- debt or fragility is obvious
- the next risk is “we cannot change this safely”
- the business is not asking for major product redesign first

### Prefer `partial-change` when:
- there is already a specific change point
- only a local slice needs to re-enter the lifecycle
- compatibility rules are likely more important than full-system redesign

## Exit Rules

### Exit to Phase-1

Choose this when the output contains:
- a real change request
- affected modules
- compatibility constraints
- brownfield invariants that architecture/product design must respect

### Exit to Phase-3

Choose this when the output contains:
- a technical-only brownfield task package
- safety-net priorities
- no product-level requirement reframing is needed

### Stay in PhaseX

Choose this when:
- the baseline is still too weak
- the system is not runnable enough
- the recommended next move is “protect and assess more before changing”

## One-Line Summary

Wave-1 should choose the smallest honest profile, not the richest-sounding one.

