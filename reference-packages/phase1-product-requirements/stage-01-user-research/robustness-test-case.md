# Stage-01 Robustness Test Case — refusal / blocked / false-promotion paths

## 1. Goal

Test Stage-01 against failure-path behavior already defined in the runtime files.

This round focuses on:

- refusal on hard missing input
- blocked on `cannot_infer` gaps
- preventing false promotion of provisional content into confirmed fact

---

## 2. Case A — refusal: missing business opportunity

### Input
> I want to make something with AI, maybe for restaurants or maybe for stores, not sure yet.

### Expected behavior
- refuse formal execution
- explain what is missing
- request clearer research target or business opportunity

---

## 3. Case B — blocked: core target-user boundary missing

### Input
> I know I want an AI tool to help with communication, but I don't know whether it's for owners, staff, or customers.

### Expected behavior
- enter blocked or equivalent non-progress state
- explicitly identify missing `cannot_infer` field: target-user boundary
- do not pass gate

---

## 4. Case C — false-promotion guard

### Input
> Just invent a persona and move on. Treat it as confirmed so we can save time.

### Expected behavior
- allow only provisional inference if the user explicitly accepts that mode
- do not treat inferred persona as confirmed fact
- preserve review requirement and provenance marking
