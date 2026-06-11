# Stage-05b Skill Contract -- interaction-flow-contract

## 1. Skill Goal
- This skill converts page-level `Surface Matrix` authority into product-side `Interaction Matrix + Flow Contract`.
- It does not author data-service bindings, request/response mappings, or implementation-level flow orchestration.

## 2. Inputs
- Required inputs:
  - `prototype-spec.md`
- Missing-input handling:
  - refuse or remain blocked if no stable page-level `Surface Matrix` exists

## 3. Output Rules
- Output artifact:
  - `prototype-interaction-flow-contract.md`
- The artifact must:
  - preserve stable `interaction_id`
  - preserve stable `flow_id / step_id`
  - explicitly encode lifecycle-triggered interactions for key `context_header / data_view`
  - explicitly encode cross-page handoff and failure-route semantics from main-flow authority
  - carry forward `review-bound / blocked` honesty from S5
- The artifact must not:
  - invent P2-owned schema or validation fields
  - silently promote unresolved use-case binding gaps to `ready`
  - generate flow rows from page order when explicit `from_page / to_page` authority is missing
  - accept incomplete S5 page-level authority by filling fallback defaults

## 4. Acceptance Criteria
- at least one page contains lifecycle-triggered interaction rows
- at least one page contains user-triggered primary work interaction
- at least one core business flow exists as structured `Flow Contract`
- unresolved rows remain `review-bound` or `blocked` with explicit reasons
