# PX-SK-06 Skill Contract — gap-analysis-and-change-decomposition (partial)

## 1. Skill Goal

- Package a bounded brownfield change into a downstream-consumable artifact without pretending a full target architecture already exists.
- Preserve affected modules, compatibility constraints, and invariants so the case can re-enter Phase-1 or go directly to Phase-3 honestly.

## 2. Inputs

- required:
  - bounded change request or hotspot statement
  - `PX-SK-01` output for the affected slice
- optional:
  - `PX-SK-04` output
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
- `brownfield_handoff_packet` preserves Phase-1 consumption notes, Phase-3 consumption notes, compatibility claim ceiling, and route decision rationale
- downstream path is explicit:
  - back to Phase-1
  - directly to Phase-3
  - protect first, then continue

## 3. Outputs

- phase1 constrained re-entry summary
- brownfield handoff packet
- brownfield non-goals
- change-point package
- affected module list
- compatibility constraint set
- brownfield invariant set
- downstream route recommendation

## 4. Gate Conditions

- `PXG-06-1`: the change point, affected modules, impacted surfaces, acceptance criteria, and downstream route are explicit in a Phase-1-consumable summary
- `PXG-06-2`: compatibility constraints and invariants are preserved rather than implied
- `PXG-06-3`: the downstream route is explicit as `return-to-phase-1`, `direct-to-phase-3`, or `protect-first-then-continue`
- `PXG-06-4`: route rationale and compatibility claim ceiling are explicit so downstream work does not treat the case as greenfield

## 5. Acceptance Criteria

- Phase-1 or Phase-3 can consume the package without rediscovering the brownfield constraints
- brownfield non-goals and third-party integration change hints are preserved instead of being silently dropped
- downstream consumers can tell which constraints are existing-system truth and which product / implementation questions still need judgment
- the output stays local and honest instead of inflating into full-system architecture prose

## 6. Boundaries

- no full TO-BE architecture here
- no full requirement rewrite here
- no silent loss of compatibility constraints
- no route decision by enum alone; the rationale must explain why the case returns to P1, goes direct to P3, or protects first
