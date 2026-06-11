# Stage-01 Self-Test Case — informal brief to structured user-understanding output

## 1. Test Goal

Use one informal requirement brief to simulate the expected Stage-01 behavior:

- clarification before solutioning
- refusal or blocked handling if key inputs are missing
- provisional inference only when explicitly allowed
- structured outputs that match Stage-01 expectations

This is not a full dialogue transcript benchmark. It is a lightweight self-test for Stage-01 behavior and output shape.

---

## 2. Informal Input Brief

> I want to build a simple tool for small restaurant owners. They often respond to customers through WeChat and lose track of repeated questions. I hope AI can help them reply faster and maybe organize common questions. I don't know exactly what the product should look like yet, and I haven't talked to many users formally.

---

## 3. Expected Stage-01 Behavior

### 3.1 Expected clarification focus
The skill should ask about:

- who the primary users are exactly
- what repeated customer-question scenarios matter most
- what pain is strongest today
- what evidence already exists
- whether there are any hard constraints or exclusions

### 3.2 Expected blocked/provisional behavior
- If the user still cannot define the target user boundary, Stage-01 should not silently gate-pass.
- If the user says “just draft something first”, Stage-01 may enter provisional inference.
- Any inferred proto-persona / story / opportunity list must be labeled as provisional.

---

## 4. Expected Minimum Output Shape

The resulting Stage-01 output should include at least:

- explicit target user group boundary
- one first-pass User Case or User Story
- structured problem list
- structured opportunity list
- assumptions
- open questions
- provenance / confidence / verification labels if any inferred content exists

---

## 5. Expected Acceptance Judgment

### PASS if:
- the output is no longer a vague note pile
- Stage-02 could use it to build a structured requirements view
- inferred content is not presented as confirmed fact

### FAIL if:
- there is still no real target-user boundary
- the output jumps directly into solution design
- provisional content is unlabeled
- there is no User Case / User Story draft

---

## 6. Optional Human Audit Check

If Chinese mirror files exist, auditors should confirm:

- the Chinese mirror matches the English runtime meaning
- no new hard rule was added only in Chinese
- no English rule was softened or changed in Chinese
