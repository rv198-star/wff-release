# Evidence and Uncertainty Protocol（v0.1）

## 1. Purpose

This protocol defines how runtimes should handle evidence, inference, uncertainty, and downstream honesty.

Its purpose is to prevent two common failures:

- weak evidence being silently upgraded into fact
- useful reasoning being discarded because the evidence is not yet complete

The correct behavior is explicit classification, not silence.

---

## 2. Statement Classes

Each important statement should be identifiable as one of:

- `observed fact`
  - directly present in source input or verified evidence
- `interpreted pattern`
  - analytical synthesis drawn from multiple facts
- `inferred assumption`
  - plausible but not yet confirmed
- `decision`
  - chosen direction, boundary, or trade-off
- `downstream prohibition`
  - what later consumers must not silently assume

These classes may coexist in the same section, but they should not be flattened.

---

## 3. Evidence States

The default evidence states are:

- `confirmed`
- `provisional`
- `review-bound`
- `blocked`

Use them as follows:

- `confirmed`
  - sufficiently grounded for downstream reuse
- `provisional`
  - currently usable, but still requires explicit later confirmation
- `review-bound`
  - usable only if downstream preserves the uncertainty honestly
- `blocked`
  - cannot be responsibly carried forward

---

## 4. Required Questions

For each high-impact inference or decision, ask:

- what evidence supports this?
- what part is still inference?
- what would change the conclusion?
- can downstream safely proceed if this remains unresolved?
- what must downstream not assume?

If these questions cannot be answered, the statement should not be hardened.

---

## 5. Downstream Honesty Rule

When evidence is weak but progression is still allowed, the runtime must preserve:

- unresolved truth
- confidence level
- verification need
- consequence if wrong
- forbidden downstream assumptions

This is what makes review-bound progression legitimate rather than misleading.

---

## 6. Minimum Record

At minimum, a runtime should preserve for each high-impact unresolved item:

- `status`
- `source`
- `confidence`
- `verification`
- `what_changes_if_wrong`
- `downstream_must_not_assume`

---

## 7. Anti-Patterns

Do not:

- replace uncertainty with confident prose
- hide unresolved truth in a generic "risks" bucket
- treat "not yet tested" as equivalent to "probably fine"
- let downstream consumers infer certainty that the current phase has not earned
