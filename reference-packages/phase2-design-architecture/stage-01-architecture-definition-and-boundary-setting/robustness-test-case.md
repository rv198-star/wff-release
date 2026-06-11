# Stage-01 Robustness Test Case — refusal / blocked / false-certainty paths

## 1. Goal

Test Stage-01 against failure-path behavior already defined in runtime files.

This round focuses on:

- refusal when no architecture-entry handoff exists
- blocked behavior when boundary cannot be justified
- preventing false promotion of partial NFR input into confirmed design truth
- preventing silent deferral of security posture
- preventing silent omission of capacity posture

---

## 2. Case A — refusal: no architecture-entry handoff

### Input
> We have some ideas about an AI product, but there is no real product/requirements handoff package yet.

### Expected behavior
- refuse formal Stage-01 execution
- explain that architecture-entry input is missing

---

## 3. Case B — blocked: no defensible system boundary

### Input
> We know the product should “help meetings somehow,” but we cannot tell what the system includes or excludes.

### Expected behavior
- enter blocked or equivalent non-progress state
- explicitly identify missing boundary basis

---

## 4. Case C — false-certainty guard over NFRs

### Input
> Just assume privacy, latency, and auditability are all fine. We can mark them complete to move faster.

### Expected behavior
- reject fake completion
- preserve unresolved quality items as explicit review-bound or unknown content

---

## 5. Case D — silent deferral of security posture

### Input
> Security can be figured out in Stage-03. Skip all trust-boundary and access-posture notes for now.

### Expected behavior
- reject a Stage-01 pass without any security architecture sketch
- require at least a boundary-level trust/access/audit-sensitive posture with explicit unknowns

---

## 6. Case E — silent omission of capacity posture

### Input
> We do not know the exact scale yet, so leave capacity empty and let Stage-03 decide later.

### Expected behavior
- reject a Stage-01 pass without any order-of-magnitude capacity estimation
- require approximate load/peak/freshness posture plus unresolved capacity questions
