---
name: wff-impl-frontend
description: Use when implementing Phase-3 web frontend slices from frozen API contracts and prototype surfaces, including the HTML2Code default lane and the optional Figma2HTML lane.
---

# Phase-3 Frontend Web Implementation

Generation governance: `docs/governance/bounded-generation-run-governance-v1.md` (中文：`docs/governance/bounded-generation-run-governance-v1.zh-CN.md`). It bounds section generation and review without weakening factual runtime evidence.

When frozen inputs use a partial/older format without the legacy full P2 chain, the existing `run_impl_frontend.py --frozen-input-decision <file>` entry accepts a P3 host decision with `sources`, `fact_sources` (original ID/value selectors), and `decision`. It verifies original SHA256 and manifest members, records the selected operation scope in the canonical implementation authority, and keeps source gaps and review ceilings. Preserve the source bytes, use the same Authority Delta and existing OMR → isolated SQR, and bind actual realized facts/runtime evidence. This admission cannot create P2/S1B review receipts or promote selected execution into full delivery; existing legacy validation remains unchanged.

Realized-fact inventory follows the actual representation: resolve local OpenAPI references and JSON `contentSchema` fields; use the explicit `sqlite-ddl` format for supported SQLite tables, simple indexes and immutable-row triggers. Register each complete SQLite definition so constraints cannot disappear behind column parsing. Unsupported DDL remains an evidence gap. A consumed config may supply `x-wff-fact-id` to distinguish a representation from an original source ID, while preserving its runtime ID and meaning. Zero unregistered facts proves registration only; semantic review findings and runtime limitations remain authoritative.

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


## Scope

This skill owns S03 web implementation after the contract pack exists.

It turns frozen contract truth into bounded, testable web surfaces.
It does not authorize silent UX drift, ad hoc API calls, or Phase-4 polish work inside Phase-3 packets.

For requested frontend source authoring, use the focused frontend capability owner:

```bash
python3 scripts/phase3/run_impl_frontend.py \
  --phase2-root <phase2-root> \
  --output-dir <phase3-output> \
  --project-artifact-root <project-artifact-root> \
  --ui-ia-contract <exact-current-ui-ia-contract.json> \
  --implementation-authority <phase3-output>/p3-agentic-implementation-authority.json \
  --authority-delta-ledger <current-p3-authority-delta-ledger.json>
```

On the first pass, requested frontend page/test targets are materialized as protected Workflow shells containing bounded `@wff:agentic-begin/end` regions. `authoring-required` is a handoff, not completed frontend. The Host Agent may edit only those bounded regions and then rerun the same focused route, or provide a same-decision `--agentic-source-root` containing those materialized regions.

When a profile carries the aggregate/runtime dependencies (notably `full-lifecycle` / `full-pack`), `scripts/phase3/run_impl.py --enable-frontend --ui-ia-contract ...` may orchestrate this same focused capability. It is a caller, not a second frontend authoring owner.

When `run_impl_frontend.py` is called without `--ui-ia-contract`, it is scaffold-only compatibility and cannot satisfy requested frontend work. With an explicit UI IA contract, it requires the current accepted `p3-agentic-implementation-authority.json`. It must not create `apps/api`; backend delivery is owned by `wff-impl-backend`.

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
- treat `ui-ia-contract.json.project_language_requirements.consumer_locale` as the consumer-copy Gate for the current project; when it is `zh-CN`, the product-facing UI must default to Simplified Chinese. This does **not** require a full i18n platform unless separately authorized.

## Boundary

- Phase-3 frontend means a `contract-verified, consumer-operable product realization`, not merely a page scaffold. P3 need not pre-specify every design detail upstream, but the generated frontend must be complete enough for a terminal consumer to perform the intended business task over the real frontend/backend path.
- If implementation evidence only sharpens a frontend realization detail without contradicting frozen P1/P2/API/security truth, keep that refinement in the P3 implementation decision / Authority Delta; do not rewrite upstream authority mid-cycle. Use a P3 gap decision for unresolved product/architecture authority that changes business meaning, ownership, public contract semantics, security/permission truth, persistence authority, or another frozen boundary; record `supersedes` when applicable.
- Every material frontend realization decision must also remain human-queryable through the fixed project artifact `<project-artifact-root>/p3-realization-decisions.md`, bound to the canonical machine Authority Delta and governed by `reference-packages/phase3-implementation-delivery/p3-realization-decisions-contract.md`. This Markdown is a PRD/ESP supplement layer for project knowledge, not a PRD/ESP rewrite or Human Audit publication. Incidental code details may be marked `human_projection.visibility=implementation-only`; material product/architecture/UX decisions must remain visible project knowledge.
- A fallback prototype, deterministic scaffold, or low-fidelity IA contract is only bootstrap/input. It is not acceptable as completed frontend implementation.
- Requested frontend source authoring must preserve the accepted P3 decision and all frozen backend target/test bindings. When the accepted P3 authority already contains frontend targets, preserve that exact frontend denominator. When continuing a legitimately frozen **backend-first** P3 decision with zero accepted Web targets, P3 may add only frontend implementation/test targets through a `p3-authority-delta-frontend-extension`: every UI interaction must bind to an existing accepted P3 slice/operation/contract, `applied_upstream=false`, and no backend target, API/security truth, decision digest, or upstream authority may change.
- `impl-frontend-report.json.authoring.status = materialized` proves only current-decision-bound complete-product source realization. It does not prove browser/runtime behavior, Trace confirmation, consumer-task completion, P4 admission, production readiness, or UAT.
- Default lane: `HTML2Code`.
- Optional lane: `Figma2HTML`, only when a real Figma source exists.
- Do not introduce new business/public API fields, routes, or response semantics without a P3 gap-decision record. P3 runtime support may expose the implementation-level product session bridge `/auth/session`; this is not business-domain authority and must not be projected back into P1/P2 contracts.
- Do not hand-roll business HTTP calls; use the generated typed API client / accepted BFF path.
- For authenticated products, normal browser business traffic must ultimately reach the generated API as `Authorization: Bearer ...`. `phase3-role-session`, `x-phase3-auth-context`, `VITE_PHASE3_ALLOW_AUTH_CONTEXT_HEADER`, browser-storage identity injection, and test-runner Authorization headers are verification shortcuts and are forbidden in the consumer journey.
- Terminal-role qualification is least-privilege and independent. `product_access_requirements.test_personas` must contain one persona per accepted terminal role; a composite/super-role account may be useful for debug but cannot qualify any terminal role.
- Consumer surfaces may not require raw internal UUID/record identifiers as manual text input. Accepted internal references must come from response/workflow context or a real lookup/select/discovery surface. If the current UI-IA contract reports `business-read-model-authority-missing`, resolve the read-model gap by a P3 gap decision; never substitute fixtures, UUIDs, hidden reference fields, or frontend-only data for accepted truth.
- When P2 freezes an external identity provider, realize that provider contract and keep the local session adapter disabled. Otherwise P3 may choose the generated local session adapter as an implementation-level option only with explicit `PHASE3_LOCAL_AUTH_ENABLED=true`: deployment-provisioned users use scrypt password hashes, the Web support helpers `createProductSession` / `getProductSession` / `clearProductSession` encapsulate `/auth/session`, an HttpOnly SameSite=Strict BFF session cookie carries the browser session, and the BFF converts it to Bearer transport for business API calls. Browser-supplied Authorization is stripped rather than trusted. Local auth is disabled by default; production cookie transport defaults Secure. The Host Agent still owns the actual sign-in page, navigation, recovery, copy, and session UX.

## T0 / T1 / T2 and one-directional gap decisions

T0 is an implementation detail that leaves business meaning unchanged; P3 decides and records material choices. T1 is a choice inferred from explicit P1/P2 facts; record `id / level / decision / basis / reasoning / alternatives / reversible / backport_target` in the existing realization-decisions/Authority Delta surfaces. T2 adds or changes business truth and requires a recorded gap decision.

Use the T2 checklist: new entities or meaningful fields, roles/permissions, rules/thresholds/prices/policies, states/transitions, external integrations, compliance/legal claims, real names/data, or API semantics. Explicit P1/P2 conflicts and infeasible upstream facts are the other two triggers. T0/T1 do not escalate for reassurance and cannot supersede explicit facts.

P3 is the sole decision maker; no runtime role meeting or new approval/storage/Authority path is introduced. Before implementing a slice, batch its triggered gaps into one small call: existing topic decision → upstream delegation rule → decision card only if neither matches. Read only relevant P1/P2 IDs/digests. Workflow mechanically applies the seven conservative defaults, marks sensitive choices `confirmation_required = true`, and records all fifteen fields in the existing Authority Delta ledger. Reuse by topic, declare a per-run decision-call cap, and at the cap record conservative choices without another call.

Follow `reference-packages/phase3-implementation-delivery/p3-realization-decisions-contract.md` for the full decision card, default rules, fifteen fields, merged view, and no-unregistered-new-facts check. Effective truth is frozen P1/P2 plus P3 decisions; only a recorded gap decision with `supersedes` can override an explicit fact locally. Preserve `upstream_reconciled = false`. P4/UAT/EKRI consume the derived merged view; existing OMR → isolated SQR also reviews T2 records. `backport_target` feeds the next upstream version, never regeneration in the current cycle. If the direction is fundamentally wrong, P3 reports it and a human decides whether to end the cycle.

## Required Inputs

Read:
- `docs/phases/phase-3/phase-3-skill-architecture-design-v0.1.md`
- the case `tech-stack-decision.yaml`
- the case `openapi.yaml`
- the case `phase3-toolchain-bootstrap.json`
- shared types / API client
- the case `p3-agentic-implementation-authority.json`
- the case `implementation-bindings.json`, including the accepted backend denominator and either the existing frontend denominator or the exact slice/operation bindings required for a backend-first P3 frontend extension
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

Before implementation, verify identity and input bindings. Missing/stale identity stops only the affected slice until the current binding is restored. Content gaps use T0/T1 inference or the narrow T2/conflict/infeasible gap-decision protocol; review-bound content is allowed under its recorded ceiling. These are existing input checks, not a new approval gate.

| Check | Source | Refusal Action |
| --- | --- | --- |
| Consumer/business intent is sufficient to know who performs the task and what meaningful outcome is required | P1 / Action Card / accepted P3 context | Use a gap decision if missing truth changes scope, user/role meaning, outcome, or a frozen requirement. Layout, shell, navigation, component tree, wording, and visual treatment stay T0/T1. |
| Assigned pages/routes and compiled interactions are admitted and not `blocked / review-bound / stale` | `ui-ia-contract.json` / implementation bindings | Stop only stale/invalid bindings; classify content gaps and record a P3 decision before continuing the affected scope. |
| Core interaction/API authority chain is complete | `ui-ia-contract.json` / `implementation-bindings.json` | Use a P3 gap decision for missing or contradictory service/API/request/response/state/security authority. |
| Security/permission/session boundary truth is sufficient for the operation | P2/API/security authority | Use a P3 gap decision for a new role, permission, credential/security rule, tenant boundary, or trust decision; Workflow applies the sensitive defaults. Product-facing login/session **presentation and interaction** remain P3 realization decisions unless explicitly frozen upstream. |
| Terminal-role qualification is independently representable | `product_access_requirements.terminal_role_qualification` | Use a gap decision when role authority is missing/review-bound or qualification depends on a super-role. Apply `DEF-PERM-01`: do not merge roles, take least privilege, and mark confirmation required. |
| Business data can be discovered/read, recognized, **and used to make the next decision by the target persona** | `business_data_requirements` + accepted P2 API/read models | If a multi-page/durable business flow requires discovery and `read_model_status != sufficient`, or if the accepted read model exposes only technical identity/status without enough human/business label/context to distinguish **and act on** the correct record, resolve the missing API/read-model facts through a P3 gap decision. Recognizability is necessary but not sufficient: the role must have enough accepted decision context to choose, prioritize, review, or continue the task. Do not create hidden fixtures, hard-coded UUIDs, frontend-only list data, or UI-only labels detached from accepted data. |
| Successful consumer outcome is available, not only a technically successful response | accepted P2 response/result authority + P1 outcome + Action Cards | A successful mutation/read must expose or resolve the **user-consumable business result** the user needs to complete the accepted task, plus enough state or next-action context to understand what the result means. Route access, persistence, reload/re-entry, role-bounded access, a completion toast, or an opaque `*_ref`/`*_id` does not by itself qualify as the meaningful outcome. If only an opaque reference exists, use a P3 gap decision for a consumer-readable projection/resolver and cap claims until it is realized. Failure/unavailable-path evidence cannot by itself qualify the success path. |
| Normal operating-scale use can be realized without turning the product into a small-data demo | P1 task frequency + accepted P2 discovery/read authority + current P3 product context | P3 must make an implementation-local judgment about plausible working-set size, repeated-use frequency, lookup/selection behavior, recency, prioritization, and whether search/filter/sort/grouping/bulk interaction is justified. This is **not** a widget quota and does not require upstream schema changes merely because scale is unspecified. Use a gap decision only when efficient realization requires new read/query/business facts. |
| Longitudinal continuity is supportable for tasks that span time or prior records | accepted state/read/history/provenance authority + P3 product realization | For returning-user work, P3 must connect current state with the relevant prior change/history/provenance and a clear next action where the accepted task needs it. Reload safety alone is insufficient when the user would still have to reconstruct what happened from memory or technical identity. Use a gap decision for absent historical/business facts; presentation choices remain P3 T0/T1. |
| Product Interaction Semantics are sufficient for material consumer inputs/decisions | accepted P2 interaction authority + Action Cards | Preserve user meaning, source, cardinality, discovery/context/default/free-form/error-cost truth. If a required candidate/discovery source is absent or review-bound, resolve that gap through a P3 decision; do not compensate with opaque text entry or frontend-only options. For image/file semantics, the chosen control must feed an accepted materialization path that yields a backend/provider-readable resource reference; filename/size/local pseudo-refs are disallowed. The concrete control/component choice remains P3 Agentic authority. |
| `source=user-input` provenance remains real | accepted P2 Product Interaction Semantics + current frontend request construction | Every such field must come from a visible user input or an explicitly accepted carried user value. Reject generated UUIDs, random tokens, placeholder strings, pseudo-evidence, or any other P3-synthesized value used merely to satisfy the contract. |
| Project consumer locale is explicit | `project_language_requirements` | Consumer copy must follow the project locale. Missing locale is a contract gap; full i18n remains optional unless separately required. |
| P3 realization decision can safely choose implementation details inside frozen truth | accepted P3 authority + Action Cards | Continue in P3. Missing shell/layout/navigation/component/state-display/responsive/accessibility/404/copy/visual details are not upstream blockers by themselves. |

Refusal message format:

```text
PHASE-3 FRONTEND EXECUTION REFUSED
Reason: {specific missing input}
Required P3 action: {restore exact identity binding, or record the bounded gap decision}
Affected pages: {list of page_ids without required input}
```

Compatibility readers retain the historical label `Required upstream action:` only for next-version backport metadata. Current-cycle action uses `Required P3 action:` above; it never requests regeneration of frozen P1/P2 inputs.

The refusal reason MUST explicitly call out any of the following when present:
- authority missing
- underconstrained contract
- `blocked`
- `review-bound`
- `stale`

## Complete-product Authoring Protocol

For requested frontend work:

1. Workflow protects exact decision/source/page bindings; it does **not** own the product composition. The generated `apps/web/app/ui-app.tsx` exposes an application-level `product-application` Agentic region, and each page/test target keeps bounded Agentic regions.
2. The first run must stop at `authoring-required` while any required application/page/test Agentic region still contains `WFF_AGENTIC_BODY_REQUIRED`.
3. The Host Agent owns complete product realization inside those regions: application shell, product identity presentation, navigation, entry/session UX, route composition, page composition, human-facing states, recovery/404, responsive behavior, accessibility realization, and business interaction presentation when these details are not frozen upstream. When accepted Product Interaction Semantics exist, consume them as constraints rather than widget instructions: do not mechanically map `string -> input`, `enum -> select`, `array -> multiselect`, or `reference -> dropdown`. Multiple P3 realizations may be valid for the same frozen semantics; concrete control/component choice remains P3 Agentic authority. `scripts/common/product_interaction_semantics.py` may validate identity/authority binding only; it must not rank or choose the P3 realization. Before materializing the product, answer four implementation-local maturity questions without turning them into fixed component rules: **(a)** what user-consumable business result actually closes the task, **(b)** what role-appropriate context is sufficient for the next decision rather than mere record recognition, **(c)** whether the interaction still works at plausible repeated-use/working-set scale and what search/filter/sort/grouping/recency/bulk behavior is justified, and **(d)** how a returning user understands current state, relevant history/provenance, and next action. If one of these requires missing business/API/data truth, use the gap-decision protocol and record provenance, conservative defaults, and claim ceilings.
4. Record realization-only refinements in the P3 implementation decision / Authority Delta and maintain their human/project-knowledge projection in `<project-artifact-root>/p3-realization-decisions.md`. For material decisions, use `human_projection.visibility=project-knowledge` and classify the stable knowledge as `product`, `architecture`, `ux`, or `implementation`; use `implementation-only` only for incidental code-level choices that a later maintainer does not need as project knowledge. Do not rewrite P1/P2 simply to document implementation details discovered while building the product.
5. Do not edit protected source bindings, route/page identity, accepted API/security truth, or decision digests. Any change to those frozen inputs invalidates prior authoring instead of silently rebinding it.
6. Frontend authoring evidence remains non-authoritative: it contains no runtime evidence refs, no Trace confirmation, no consumer-task proof, and no P4/product admission result.
7. Do not restore a peer frontend lifecycle or separate semantic authority. This remains the existing P3 implementation-delivery path.

## Execution Playbook

1. Freeze the packet boundary first.
   Use the assigned frontend worker packet as the unit of work.
   Keep implementation inside the owning `wp_id`, listed routes, linked operations, and trace subjects.
   Before coding, cross-check the packet route list against the full Phase-2 or fallback UI IA route/page inventory; missing core pages must be surfaced back to the orchestrator instead of silently ignored.
2a. Make the P3 product-realization decision before coding.
   Read the packet route list, P1/P2/Action Card truth, generated shared types/API client, and any available UI-IA hints. Then decide at P3 implementation time:
   - application shell and product identity presentation;
   - public/normal entry behavior and product-facing login/session/role UX when required by frozen security truth; when no external provider is frozen, the generated P3 local session adapter is available through `/auth/session`, while the visible login experience remains Agentic-owned;
   - global/contextual navigation and route recovery/404 behavior;
   - interaction language, component composition, information hierarchy, content/copy, and visual treatment appropriate to the domain;
   - loading/empty/success/validation/denied/error/retry presentation;
   - cross-page UI state/context continuity;
   - the user-consumable business outcome that closes each primary journey, not merely technical success/re-entry;
   - decision-sufficient list/detail/queue context for the target persona;
   - plausible repeated-use / working-set scale and whether search/filter/sort/grouping/recency/prioritization/bulk behavior is justified without a fixed widget quota;
   - longitudinal continuity for returning users: current state, relevant history/change/provenance, and next action where the task spans time;
   - desktop/mobile responsive behavior and accessibility realization.
   These are P3 realization decisions unless explicitly frozen upstream. Record material refinements as P3 Authority Delta rather than forcing P1/P2 rewrites.
   For each assigned page, identify its business function, visible objects/state transitions, concrete UI changes, validation, and context carry-forward. Do NOT build a generic renderer that accepts page-brief metadata or section configuration as runtime input. Pages with different business functions must have meaningfully different component composition.
   Before proceeding to Step 2b, verify:
   - [ ] Every page has a distinct component composition that reflects its business function and any accepted blueprint hints; a missing blueprint hint is not itself an upstream blocker
   - [ ] No `ui-ia-contract.json` field with `visibility: "agent-internal"` is planned as visible UI text
   - [ ] Page titles use business language from P1 `page_name`, not P2 technical surface names
   - [ ] Empty states use guided onboarding/helpful copy, not "等待XX数据" style placeholders
   - [ ] Consumer-facing copy follows `project_language_requirements.consumer_locale`
   - [ ] No internal UUID/record id is exposed as a manual text field; use workflow/response context or real lookup/discovery
   - [ ] Role-specific application/nav/actions are driven by accepted terminal-role authority; no super-role is used as the product qualification persona
   - [ ] Error states use alert/toast plus retry guidance, not raw JSON display
   If any check fails, fix the implementation design before writing code.
2b. Bind the route to frozen contract truth.
   Use the generated API client only after the implementation design is clear.
   Treat request / response envelopes, pagination, denied states, and business-error codes as required UI inputs, not backend details.
   The page must materially show the fields the IA says users need to see, and must expose the fields the IA says users need to submit.
   Map response fields into specific business UI elements rather than generic JSON/result panels.
   A successful operation must visibly deliver or resolve the meaningful consumer outcome promised by the task; a toast such as “completed” plus an unread opaque reference does not close the success path. The outcome should leave the user able to understand the business result and what can or should happen next; persistence, route transition, role-bounded access, or reload/re-entry are supporting evidence, not the outcome itself. If the response only exposes a reference whose human-readable meaning is not accepted upstream, or the accepted read model does not contain enough business context for the next user decision, use a P3 gap decision instead of displaying the reference as if it were content.
   When the accepted input meaning is an image/file, prove the selected file is materially transferred/stored into an accepted backend/provider-readable resource before invoking the business operation; browser-local filename/size strings or synthetic local refs do not qualify.
   Keep engineering qualification language out of steady-state product copy. Evidence rules such as “no fake data”, “generated environment”, “manual UUID forbidden”, implementation version/path/tenant identifiers, or test/gate terminology may shape behavior and recovery, but must not be repeated as consumer-facing explanation unless the real user task requires that fact.
   For `blocked / review-bound / stale` contract rows, restore stale identity bindings and resolve content gaps through P3 decisions; carry honest review-bound ceilings instead of papering over gaps with placeholders.
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
   - understand the user-consumable business result and the next useful decision/action rather than only knowing that the operation persisted
   - distinguish and act on records using decision-sufficient business context, not merely technical identity or a thin display label
   - remain usable under plausible repeated-use/working-set scale, with search/filter/sort/grouping/recency/prioritization/bulk behavior when the actual task justifies it
   - return later and recover current state plus relevant history/provenance/next action when the workflow is longitudinal
   - follow the declared next/previous flow direction when the IA defines it
   Static contract summaries, API explorers, debug panels, handoff placeholders, or route-only shells do not satisfy this bar.
6. Complete focused unit/component tests when the packet introduces non-trivial view-model logic, reducers, selectors, or state helpers.
7. Close the packet against verification, not screenshots.
   Relevant scenario / replay / contract-linked targeted tests must stay green first.
   The packet must pass lint / typecheck / build and remain aligned to the owning WP acceptance boundary.

## P3 Done vs P4 Done

Source-authoring complete is **not** Phase-3 frontend complete. `authoring.status=materialized` only means all bounded source regions are current and materialized; requested frontend still requires P3 runtime/browser evidence before P3 can claim the frontend execution surface is complete.

P3 browser/runtime evidence is owned by the existing aggregate/runtime-smoke path, not this source-authoring skill as a second lifecycle. The current application/page authoring identity, exact UI IA hash, current P3 decision identity, and every current-ready compiled interaction are rebound before execution. Runtime must preserve the Agentic-authored `ui-app.tsx`; Workflow must not replace it with a deterministic route switch. Interaction evidence must live under `tests/e2e/**`, carry the exact `@wff:frontend-runtime-evidence page_id=... interaction_id=...` marker, exercise the exact current UI-IA API endpoint, and use the real generated Web/API path without request interception or route fulfillment. Consumer journeys use `@wff:frontend-consumer-journey journey_id=... entry_route=... outcome=... [persona_id=...]`; `outcome` must name a **user-consumable business result**, not merely authentication/route access, persistence, bounded-role access, reload/re-entry, or an internal reference. For multi-role products every accepted terminal persona must have an independently bound journey. A clean-first-use journey uses `@wff:frontend-clean-first-use journey_id=... [persona_id=...]` and must, from an empty business-data state, exercise a real write plus the required read/discovery path and prove reload/re-entry context recovery. Consumer E2E evidence containing hard-coded/random UUIDs is disqualified rather than accepted as business continuity proof. When authentication is required, consumer evidence must use runtime-isolated credentials only as **form input** to the product-facing session entry; it must not set Authorization or identity headers directly. For current generated backends, runtime proves the BFF-managed session becomes Bearer-authenticated business API traffic. For an explicitly declared frozen backend-first continuation whose accepted API runtime predates Bearer support, a Web-only compatibility adapter may convert the BFF session to that frozen backend's already-accepted internal auth-context transport; this adapter must be explicit, server-side only, preserve backend bytes/decision digest, record a lower claim ceiling, and still prove zero browser Authorization / `x-phase3-auth-context` injection. Write/mutation specs must use `testInfo.project.name` to isolate desktop/mobile evidence data within the same runtime wave. Runtime evidence must cover desktop and mobile Chromium, retain screenshots plus Playwright report/trace material, and factually prove that the rendered document does not widen beyond the current viewport. Screenshot presence alone is not viewport-fit evidence; document-level horizontal overflow must fail the browser Gate.

Done in Phase-3:
- the Agentic-authored application shell and routes render against frozen contracts under current runtime/browser evidence, not source materialization alone
- every accepted terminal role is qualified by an independent least-privilege persona journey; no super-role substitutes for terminal-role evidence
- at least one first-entry-to-meaningful-outcome consumer journey executes through the real generated Web/API path, where the outcome is a user-consumable business result rather than route/re-entry/persistence mechanics
- when the contract requires clean first use, an empty-state journey creates the first valid business object, discovers/reads it through accepted API authority, reloads/re-enters, and recovers context without fixture/random UUID shortcuts
- the generated API client / accepted HTTP boundary remains the business contract path; authenticated normal consumer use enters through product-facing session UX and reaches business APIs through the accepted server-side auth transport (Bearer for current generated backends; explicit Web-only compatibility transport only for frozen backend-first continuation), without browser localStorage/header identity injection
- loading / empty / success / validation / denied / error-retry / not-found behavior is realized where relevant to the accepted journey
- the product is operationally usable for its business purpose rather than explanatory-only
- pages expose the declared action flow and product navigation rather than route placeholders or contract dumps
- owned targeted interface evidence is green
- any remaining frontend unit/component gap is explicit follow-up, not hidden debt

Phase-4 is validation/qualification, not the owner of missing product realization. P3 must already provide the consumer-operable shell, navigation, interaction/state treatment, responsive behavior, accessibility realization, recovery behavior, and domain-appropriate product composition needed for the accepted task. The following may remain later optimization work when they do not block that consumer-operable bar:
- reusable design-system extraction / abstraction cleanup beyond the generated product's required consistency
- analytics instrumentation beyond contract-critical telemetry
- advanced performance tuning beyond passing build/runtime and consumer-task gates

## Completion Standard

Frontend work is Phase-3 acceptable only when:
- the target surface renders against frozen contracts under current generated Web/API runtime evidence
- every current-ready compiled interaction has exact current endpoint-bound browser evidence with no mock/interception substitution
- desktop/mobile Chromium evidence and retained factual browser artifacts exist for every authored page, including a document-level no-horizontal-overflow viewport check
- the generated client and shared types remain the contract boundary
- the final route is operationally usable for its IA-defined purpose, not a scaffold or debug/explorer screen
- all implemented pages have a traceable link back to a Phase-2 Frontend Surface Architecture `page_id`
- no assigned page or compiled interaction has unhandled content gaps or stale/invalid bindings; recorded review-bound gaps retain their claim ceilings
- no core interaction still requires guessing missing service / field / flow authority
- no consumer flow requires manually typed internal IDs; required reference discovery/read models are explicit, sufficient, human-recognizable, and decision-sufficient for the target persona
- every accepted success path delivers or resolves the meaningful consumer result and leaves enough result/next-action context for the user to proceed; failure-only provider evidence does not qualify a success path, and opaque refs are not rendered as business content without explicit authority
- repeated-use surfaces are judged against plausible operating scale; search/filter/sort/grouping/recency/prioritization/bulk behavior is added only when justified by the task, never as a widget quota
- longitudinal work exposes enough current state, relevant history/provenance, and next-action continuity for a returning user when the accepted task spans time
- image/file inputs use an accepted real materialization path to a backend/provider-readable resource; browser-local pseudo-refs are disqualifying
- consumer-facing copy matches the project locale contract and does not expose engineering qualification/gate language as steady-state product explanation
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
- a technically successful operation does not deliver the task's meaningful result to the consumer, or the product qualifies only an unavailable/failure path while the success path remains unconsumable
- selectable/readable durable records are technically discoverable but not human-recognizable for the target persona
- an image/file control reduces the selected file to filename/size/browser-local pseudo-reference instead of an accepted materialized resource
- business object state transitions are not reflected in UI state changes after the user acts
- when a `page_blueprint_type` is explicitly frozen upstream, the page contradicts that accepted interaction pattern
- when explicitly declared upstream, an `analysis-board` omits decision-relevant summary/prioritization, a `decision-workbench` omits supporting evidence, an `execution-workbench` omits task progress/status handling, a `setup-flow` omits guided setup, or a `review-decision` omits evidence for the decision
- Category E: Upstream-Detail Overreach
- the frontend demands upstream regeneration because shell/layout/navigation/component/state-display/responsive/accessibility/copy/visual realization details were not pre-specified
- the implementation introduces unregistered business/API/security/permission/persistence truth without the required gap decision
- the implementation treats missing blueprint hints as permission to use an API-endpoint-inferred generic renderer instead of making a bounded P3 product-realization decision
