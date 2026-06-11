# Stage-02.5 Source Cards — third-party-integration-architecture-design

## Required source bundles
- Phase-1 PRD `third-party dependency manifest` when present
- Stage-01 architecture definition
- Stage-02 decomposition package
- provider API / auth / sandbox / quota docs when available

## Optional support
- security / compliance references
- resilience-pattern references
- cost / vendor-risk references

## Anti-pattern cards
- active dependency with no IDR
- provider SDK leaking directly into internal service contracts
- auth posture implied but never written
- timeout / retry / fallback omitted for critical dependency
- production-only testing assumption
- skip without reason

