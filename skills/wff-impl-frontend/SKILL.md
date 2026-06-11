---
name: wff-impl-frontend
description: Use when implementing Phase-3 web frontend slices from frozen API contracts and prototype surfaces, including the HTML2Code default lane and the optional Figma2HTML lane.
---

# Phase-3 Frontend Web Implementation

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


## Scope

This skill owns S03 web implementation after the contract pack exists.

It turns frozen contract truth into bounded, testable web surfaces.
It does not authorize silent UX drift, ad hoc API calls, or Phase-4 polish work inside Phase-3 packets.

Primary capability runner:

```bash
python3 scripts/phase3/run_impl_frontend.py \
  --phase2-root <phase2-root> \
  --output-dir <phase3-output> \
  --ui-ia-contract <phase3-output>/prototype-fallback/ui-ia-contract.json
```

This runner must not create `apps/api`; backend delivery is owned by `wff-impl-backend`.

## Reference Package

Read `reference-packages/phase3-implementation-delivery/wff-impl-frontend/` for the capability contract, SOP, output template, and source cards.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write UI copy, page titles, empty/error/denied guidance, implementation notes, and audit-facing frontend summaries in Chinese
- preserve code, file paths, commands, routes, component ids, API/schema field names, trace ids, artifact ids, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only UI text, packet notes, or frontend review conclusions unless the user explicitly requests English

## Boundary

- Phase-3 frontend means `contract-verified implementation surface`, not final design-system maturity.
- A fallback prototype or low-fidelity IA contract is only an input. It is not acceptable as the final Phase-3 frontend output.
- Default lane: `HTML2Code`.
- Optional lane: `Figma2HTML`, only when a real Figma source exists.
- Do not invent new public fields, routes, or response semantics.
- Do not hand-roll public HTTP calls; use the generated typed API client.

## Required Inputs

Read:
- `docs/phases/phase-3/phase-3-skill-architecture-design-v0.1.md`
- the case `tech-stack-decision.yaml`
- the case `openapi.yaml`
- the case `phase3-toolchain-bootstrap.json`
- shared types / API client
- the case `implementation-bindings.json`
- the owning WP `work-package-packets/<wp-id>/execution-packet.md`
- the case `work-package-wave-plan.json`
- the assigned `worker-input-packets/wave-XX/frontend-worker-input-packet.md`
- the case `dispatch-manifest.json` or `execution-runtime-state.json`
- frontend surface definitions from the Engineering Spec Pack
- the case `prototype-fallback/ui-ia-contract.json` when present, including:
  - `page_blueprint_type`
  - `primary_work_region`
  - `dominant_component_pattern`
  - `business_state_transitions`
  - `semantic_guardrails`
  - `prototype_generation_constraints`
  - `external_executor_brief`
- the prototype-spec's `prototype_generation_constraints` section (§9) when present, especially:
  - `must_present_as_business_product_not_demo_shell`
  - `must_not_render_demo_console_or_api_explorer`
  - `must_not_center_home_on_stepper_or_debug_cards`
  - `must_not_replace_page_intent_with_generic_workspace_labels`
  These are Phase-3 disqualifying constraints, not optional style notes.
- generated scenario/replay tests

## Pre-execution Gate

Before starting any implementation work, verify the following mandatory inputs exist.
If ANY check fails, the skill MUST refuse execution and return a structured refusal message
specifying what is missing and which upstream phase needs to provide it.

| Check | Source | Refusal Action |
| --- | --- | --- |
| `page_blueprint_type` defined for each assigned page | `implementation-bindings.json` or `ui-ia-contract.json` | Refuse. Require fallback to Phase-2 to complete Frontend Surface Architecture. |
| At least one page has a non-generic `interaction_pattern` | Engineering Spec Pack `Frontend Surface Architecture` §D.3 or `ui-ia-contract.json` | Refuse. Require Phase-2 to complete Interaction Pattern Assignment. |
| Page component regions defined | Engineering Spec Pack `Frontend Surface Architecture` §D.1 or `ui-ia-contract.json` | Refuse. Require Phase-2 to complete the Page Component Tree. |
| Assigned pages and compiled interactions are all `readiness_status = ready` | `ui-ia-contract.json` compiled page / interaction rows | Refuse. Keep `blocked / review-bound / stale` explicit; require upstream contract owner to resolve or downgrade the packet scope. |
| Core interaction authority chain is complete | `ui-ia-contract.json` compiled interactions or `implementation-bindings.json` | Refuse. Require upstream to freeze `service_binding_id / domain_service / api_endpoint / request_field_mapping / response_field_mapping`, and flow fields such as `flow_id / next_page_id / failure_route` when the interaction continues across pages. |

Refusal message format:

```text
PHASE-3 FRONTEND EXECUTION REFUSED
Reason: {specific missing input}
Required upstream action: {which phase/stage needs to provide what}
Affected pages: {list of page_ids without required input}
```

The refusal reason MUST explicitly call out any of the following when present:
- authority missing
- underconstrained contract
- `blocked`
- `review-bound`
- `stale`

## Execution Playbook

1. Freeze the packet boundary first.
   Use the assigned frontend worker packet as the unit of work.
   Keep implementation inside the owning `wp_id`, listed routes, linked operations, and trace subjects.
   Before coding, cross-check the packet route list against the full Phase-2 or fallback UI IA route/page inventory; missing core pages must be surfaced back to the orchestrator instead of silently ignored.
2a. Translate the prototype surface into implementation design before coding.
   Read the packet route list, the prototype surface, the generated shared types, the generated API client,
   and any `ui-ia-contract` page blueprint before editing UI code.
   For each assigned page:
   - identify the page's business function and the decision or workflow step it advances
   - choose the interaction pattern that matches that function
     (wizard / stepper, dashboard / summary, list / kanban, detail-form, decision workbench)
   - identify which business objects and business state transitions must become visible in the UI
   - map each state transition to a concrete UI change, not only an API request + raw response dump
   - identify domain-specific validation and context carry-forward requirements
   Do NOT build a generic renderer that accepts page-brief metadata or section configuration as runtime input.
   Pages with different business functions must have meaningfully different component composition.
   Before proceeding to Step 2b, verify:
   - [ ] Every page has a distinct component composition that reflects its `page_blueprint_type`
   - [ ] No `ui-ia-contract.json` field with `visibility: "agent-internal"` is planned as visible UI text
   - [ ] Page titles use business language from P1 `page_name`, not P2 technical surface names
   - [ ] Empty states use guided onboarding/helpful copy, not "等待XX数据" style placeholders
   - [ ] Error states use alert/toast plus retry guidance, not raw JSON display
   If any check fails, fix the implementation design before writing code.
2b. Bind the route to frozen contract truth.
   Use the generated API client only after the implementation design is clear.
   Treat request / response envelopes, pagination, denied states, and business-error codes as required UI inputs, not backend details.
   The page must materially show the fields the IA says users need to see, and must expose the fields the IA says users need to submit.
   Map response fields into specific business UI elements rather than generic JSON/result panels.
   If the assigned page still contains `blocked / review-bound / stale` contract rows, stop and refuse execution instead of papering over them with placeholders.
3. Implement the surface in this order:
   - route shell and layout
   - data loader / action path through generated client
   - success state
   - loading state
   - empty state
   - denied / permission state
   - recoverable error state
4. Keep state surfaces explicit.
   Do not collapse loading / empty / denied / error into one fallback screen.
   If the packet owns a mutation, preserve pending, success, business-error, and retry guidance surfaces explicitly.
5. Make the page materially operable.
   The delivered route must let a user actually do the IA-defined job:
   - load or refresh the required data
   - display the IA-required data fields in the UI, not only raw JSON or explanatory text
   - enter the declared inputs
   - submit the declared fields to the correct API binding
   - see the resulting state change or returned records
   - follow the declared next/previous flow direction when the IA defines it
   Static contract summaries, API explorers, debug panels, handoff placeholders, or route-only shells do not satisfy this bar.
6. Complete focused unit/component tests when the packet introduces non-trivial view-model logic, reducers, selectors, or state helpers.
7. Close the packet against verification, not screenshots.
   Relevant scenario / replay / contract-linked targeted tests must stay green first.
   The packet must pass lint / typecheck / build and remain aligned to the owning WP acceptance boundary.

## P3 Done vs P4 Done

Done in Phase-3:
- the route renders against frozen contracts
- the generated API client is the only public HTTP path
- loading / empty / denied / error surfaces are visible in code
- the route is operationally usable for its IA-defined purpose rather than explanatory-only
- the page exposes the declared action flow, not only a route placeholder or contract dump
- owned targeted interface evidence is green
- any remaining frontend unit/component gap is explicit follow-up, not hidden debt

Deferred to Phase-4 unless the packet explicitly requires them:
- visual polish beyond prototype fidelity
- design-system extraction / abstraction cleanup
- analytics instrumentation beyond contract-critical telemetry
- advanced performance tuning beyond passing build/runtime gates

## Completion Standard

Frontend work is Phase-3 acceptable only when:
- the target surface renders against frozen contracts
- the generated client and shared types remain the contract boundary
- the final route is operationally usable for its IA-defined purpose, not a scaffold or debug/explorer screen
- all implemented pages have a traceable link back to a Phase-2 Frontend Surface Architecture `page_id`
- no assigned page or compiled interaction remains `blocked`, `review-bound`, or `stale`
- no core interaction still requires guessing missing service / field / flow authority
- relevant targeted interface tests stay green for the owned surface
- non-trivial UI-state logic has relevant unit/component coverage, or any remaining gap is explicitly recorded as Phase-4 follow-up
- relevant scenario/replay tests pass
- the owning WP remains green in the WP gate
- error and empty states remain explicit
- all core frontend pages/routes assigned by Phase-2 or fallback IA are materially represented across the packet set

Semantic disqualifiers - the work is NOT Phase-3 acceptable if ANY of these are true:
- Category A: Metadata Leakage (agent-internal content rendered as UI)
- pages render prototype-spec metadata such as `page_goal`, `purpose`, `design_guardrails`, `positioning`, or `problem_statement` as visible UI copy instead of using them to shape the page
- pages display `primary_actor` persona labels in the UI
- pages display `required_status_messages` as a raw list instead of contextual state indicators
- pages display product-positioning or scope-limitation disclaimer text as visible working-UI content
- any `ui-ia-contract.json` field marked `visibility: "agent-internal"` appears in the rendered page
- Category B: Generic Rendering (contract viewer pattern)
- all pages share the same generic rendering logic with only JSON/configuration differences
- the page uses a generic `renderSectionCard(section)` / `renderBlueprintSurface()` / `view`-switch renderer as the dominant implementation pattern
- pages with different `page_blueprint_type` values have near-identical DOM structure and do not respect `dominant_layout.prohibited`
- Category C: Technical Surface (debug/API explorer pattern)
- user interaction is effectively "fill parameters -> call endpoint -> display raw JSON response"
- the delivered surface would reasonably be mistaken for an API explorer, contract viewer, acceptance harness, or demo shell instead of a business product page
- raw JSON error responses are rendered directly in the UI instead of user-friendly recovery guidance
- form placeholder values use developer test data such as `tenant-acme` or `finding_001`
- pages expose backend terminology such as `payload`, `idempotent key`, or `posture` as end-user copy
- Category D: Business Logic Absence
- business object state transitions are not reflected in UI state changes after the user acts
- the page does not implement the declared `page_blueprint_type` interaction pattern
- an `analysis-board` page does not surface summary metrics or prioritization context
- a `decision-workbench` page does not present actions with supporting evidence
- an `execution-workbench` page does not provide task progress/status handling
- a `setup-flow` page does not guide the user through a clear staged setup experience
- a `review-decision` page does not surface evidence for the decision being made
- Category E: Missing Blueprint Passthrough
- the skill executed without a `page_blueprint_type` definition for any page
- the skill used api-endpoint-inferred mode to determine page layout
- the skill generated pages without an explicit interaction pattern from upstream
