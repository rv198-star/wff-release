# Stage-02 Self-Test Case — evidence-execution-and-defect-identification

## Test goal

Verify that the Stage-02 runtime package can execute bounded validation work and produce evidence/defect visibility without:

- silently hiding blocked scenarios
- reporting pass/fail with no evidence
- collapsing defects into narrative-only notes

## Input scenario

- Stage-01 has already produced a usable validation planning package.
- Three acceptance scenarios are in scope.
- One scenario passes, one fails with a reproducible defect, and one remains blocked by environment access.

## Expected Stage-02 behavior

1. record all three outcomes explicitly
2. preserve evidence for executed scenarios
3. preserve a structured defect record for the failure
4. keep the blocked scenario visible instead of dropping it
5. hand off the unresolved risk set to Stage-03
