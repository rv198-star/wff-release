# wff-impl-security Skill Contract

## Responsibility

Review Phase-3 security posture and security-relevant implementation evidence.

## Inputs

- P2 security/foundation decisions.
- Implementation package.
- API/auth/session/tenant/secret handling surfaces.
- Security checklists.

## Outputs

- security audit report.
- routed security findings.
- claim ceiling for unresolved risks.

## Boundaries

- Do not certify production security.
- Do not create missing P2 security architecture.
- Do not hide critical evidence gaps behind a generic pass.

## Runtime

Use `scripts/phase3/phase3_delivery_gate.py --mode security-audit`.
