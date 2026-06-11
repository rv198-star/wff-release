# Stage-01 Source Cards — architecture-definition-and-boundary-setting

## 1. Required Source Bundles
- `ddd-reference`
- `software-architecture-in-practice`
- `diagram-expression`

## 2. Required Method Assets
- Phase-1 PRD `Phase-2 Design Input Contract` as the top-down absorption baseline
- system boundary / bounded-context language
- architecture direction and quality-attribute framing
- architecture decision record (ADR) structuring discipline
- capability-map prioritization / maturity framing discipline
- security posture detailing discipline for auth flow / session-token / key-management seams
- Mermaid / structural diagram expression discipline

## 3. Optional Support Assets
- `iso-25010-quality-model` for quality-attribute taxonomy support
- `eventstorming-glossary-cheat-sheet` for discovery vocabulary support when scenario language is weak

## 4. Boundary / Anti-Pattern Assets
- avoid treating product scope as architecture boundary
- avoid assuming `key constraints` equals complete NFR baseline
- avoid jumping into module/service/interface design before Stage-01 closure
- avoid letting TOGAF replace the Stage-2 backbone
- avoid letting SOA-lite / SOMA / BPMN become default runtime structure
- avoid presenting placeholder diagrams or review-bound assumptions as approved truth
- avoid forbidden-assumption rows that stop at source/compliance without citing verification evidence

## 5. Bundle Roles
- `ddd-reference`
  - provides Stage-01 boundary language, strategic framing, capability/bounded-context thinking, and capability-group prioritization framing
- `software-architecture-in-practice`
  - provides architecture approach logic, quality-attribute framing, review-oriented reasoning, and decision-structuring discipline
- `diagram-expression`
  - provides controlled diagram expression and evidence-vs-handoff diagram quality discipline
- `iso-25010-quality-model`
  - provides optional supporting taxonomy for expanding partial NFR input into architecture-facing quality attributes
- `eventstorming-glossary-cheat-sheet`
  - provides optional discovery vocabulary when upstream scenarios are too coarse for boundary discussion

## 6. Current Use Rule
- Use source bundles as controlled upstream assets only.
- Before drafting Stage-01, enumerate which Phase-1 trace units will be absorbed by which `P2-DTR-*` rows and which units are intentionally handed forward to Stage-03/04.
- Do not copy source-card prose directly into Stage-01 runtime files.
- If a source gap blocks Stage-01 drafting, record the gap explicitly before proposing a new bridge artifact.
- If TOGAF, SOA-lite, SOMA, or BPMN are mentioned, treat them as review/sidecar lenses only unless a later substage explicitly admits them.
