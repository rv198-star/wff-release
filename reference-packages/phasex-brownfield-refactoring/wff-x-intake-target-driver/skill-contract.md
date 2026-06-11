# wff-x-intake-target-driver Skill Contract — target-driver-intake

## 1. Skill Goal

- Package a bounded brownfield change into a downstream-consumable artifact without pretending a full target architecture already exists.
- Preserve affected modules, compatibility constraints, and invariants so the case can re-enter Phase-1 or go directly to Phase-3 honestly.
- Produce PX Handoff Cards plus the mainline re-entry packets needed for P1 and P2 to consume existing-system truth without understanding PhaseX internals.

## 2. Inputs

- required:
  - bounded change request or hotspot statement
  - `wff-x-scan-code-baseline` output for the affected slice
- optional:
  - `wff-x-scan-tech-health` output
  - partial contracts or APIs
  - incident or stakeholder constraints

## 2.1 Cannot Infer

- full-system redesign from a local change point
- that product reframing is unnecessary unless the change is purely technical
- compatibility rules unless they are named or evidenced

## 2.2 Must Validate Before Exit

- change point is explicit
- affected modules or interfaces are named
- brownfield invariants are listed
- `px_handoff_cards` split the case into takeover units with evidence, gap, route, prework, and claim ceiling
- `px_to_p1_change_source_packet` is present when demand truth, target change, business impact, user/workflow impact, or acceptance pressure must return to P1
- `PX-to-P1 Demand Clarification Addendum` is recorded as optional demand clarification evidence when answers are available; missing answers must not block P1
- reviewer confirmation prompts are emitted as `p1-demand-confirmation-checklist.md` sidecar evidence and are not embedded into the P1 source packet as product requirements
- `px_to_p2_architecture_change_intake_packet` is present when architecture, data, interface, integration, deployment, performance, or compatibility pressure must enter P2
- `brownfield_handoff_packet` preserves Phase-1 consumption notes, Phase-3 consumption notes, compatibility claim ceiling, and route decision rationale
- downstream path is explicit:
  - `return-to-P1`
  - `enter-P2`
  - `protect-first`
  - `direct-to-P3`
  - `decision-required`
- Owner confirmation is optional evidence, not a lifecycle prerequisite. If no owner can be found, record the owner as unavailable, keep unverified truth review-bound, and route through the most conservative compatible path.

## 3. Outputs

- phase1 constrained re-entry summary
- PX Handoff Cards
- PX-to-P1 existing-system-change packet
- PX-to-P2 existing-system-architecture-change packet
- brownfield handoff packet
- brownfield non-goals
- change-point package
- affected module list
- compatibility constraint set
- brownfield invariant set
- downstream route recommendation

## 4. Gate Conditions

- `PXG-06-1`: the change point, affected modules, impacted surfaces, acceptance criteria, PX Handoff Cards, and downstream route are explicit in a Phase-1-consumable summary
- `PXG-06-2`: compatibility constraints and invariants are preserved rather than implied
- `PXG-06-3`: the downstream route is explicit as `return-to-P1`, `enter-P2`, `protect-first`, `direct-to-P3`, or `decision-required`
- `PXG-06-4`: route rationale and compatibility claim ceiling are explicit so downstream work does not treat the case as greenfield
- `PXG-06-5`: PX-to-P1 and PX-to-P2 packets use the mainline packet contracts instead of PhaseX internal skill structure

## 5. Acceptance Criteria

- Phase-1 or Phase-3 can consume the package without rediscovering the brownfield constraints
- Phase-1 can consume `PX-to-P1 existing-system-change packet` as a normal `P1 Source Input Packet`
- Phase-1 can use `PX-to-P1 Demand Clarification Addendum` to enrich demand convergence without treating it as owner sign-off, UAT, market validation, or production readiness
- Phase-1 does not need to ingest reviewer confirmation prompts; those prompts stay in `p1-demand-confirmation-checklist.md` for human review and must not become product scope
- Phase-2 can consume `PX-to-P2 existing-system-architecture-change packet` as a sidecar without replacing the P1 PRD
- brownfield non-goals and third-party integration change hints are preserved instead of being silently dropped
- downstream consumers can tell which constraints are existing-system truth and which product / implementation questions still need judgment
- the output stays local and honest instead of inflating into full-system architecture prose

## 6. Boundaries

- no full TO-BE architecture here
- no full requirement rewrite here
- no P3 implementation ActionCards here; PX Handoff Cards are takeover cards, not P3 implementation ActionCards
- no blocking P1 only because demand clarification answers or owner confirmation are unavailable
- no embedding unanswered reviewer confirmation questions into the P1 source packet as source truth
- no silent loss of compatibility constraints
- no route decision by enum alone; the rationale must explain why the case returns to P1, goes direct to P3, or protects first
