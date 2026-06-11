# Stage-02 Source Cards — domain-module-service-decomposition

## Required source bundles
- Phase-1 PRD `Phase-2 Design Input Contract`
- `ddd-reference`
- `software-architecture-in-practice`
- `diagram-expression`

## Optional support
- `azure domain analysis + tactical ddd`
- `iso-25010-quality-model`

## Boundary / anti-pattern cards
- avoid decomposition by label only
- avoid hidden ownership overlap
- avoid hidden dependency coupling
- avoid anti-cycle rules without explicit violation consequence
- avoid lifecycle ownership closure without conflict detection rule
- avoid replacing Stage-2 backbone with TOGAF/SOA process framing

## Use rule
- use source bundles as controlled upstream assets
- preserve the object/service/public-boundary names required to let Stage-03 and Stage-04 absorb the upstream Phase-1 trace contract without alias drift
- do not copy prose directly into runtime files
