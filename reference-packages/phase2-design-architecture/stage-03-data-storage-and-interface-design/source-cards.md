# Stage-03 Source Cards — data-storage-and-interface-design

## Required source bundles
- Phase-1 PRD `Phase-2 Design Input Contract`
- `software-architecture-in-practice`
- `diagram-expression`
- `api-contract-example`
- `security-posture-detailing`

## Optional support
- `iso-25010-quality-model`

## Boundary / anti-pattern cards
- avoid schema design without ownership boundaries
- avoid interface contracts without error/compatibility semantics
- avoid calling field-summary tables "JSON examples"
- avoid generic schema field types such as `string` / `number` / `object` when the package claims implementation-planning readiness
- avoid hidden cross-boundary coupling
- avoid security sections that stop at generic authn/authz wording without token or key posture
- avoid externally-verified technology claims that provide URLs without verification dates
- avoid interface contracts that never leave prose and never enter JSON Schema / TypeScript interface structure
- avoid list/read endpoints that omit explicit rate-limit or pagination policy
- avoid bottleneck hypotheses that name a constraint but omit measurement/threshold/spike plan
- avoid alternative candidate sets that never state pros / cons / cost / fit / reversibility
- avoid technology selection matrices that only show summary/evidence/decision columns and skip comparison dimensions such as reliability, scalability, cost, or security
- avoid technology selection matrices that stop below 10 explicit comparison dimensions per candidate
- avoid public boundary registries that define names but omit namespace convention
- avoid scenario matrices that hide concurrent write/conflict behavior inside vague failure prose instead of explicit concurrent-conflict rows

## Use rule
- controlled source usage only; no direct prose copy
- every scenario / contract row that absorbs a Phase-1 unit must carry explicit `upstream_trace_ids`; do not rely on prose-only matching as the default mechanism
- if the API section claims request/response examples, they must be real JSON-shaped examples rather than prose-only field lists
