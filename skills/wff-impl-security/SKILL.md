---
name: wff-impl-security
description: Use when running the Phase-3 security audit over a stabilized implementation, especially for auth, tenant isolation, validation, secrets, sensitive data handling, and OWASP-class risks.
---

# Phase-3 Security Audit

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


## Scope

This skill owns the Stage-04 structural security audit after implementation and core verification are green.

It is a delivery readiness audit, not a substitute for penetration testing or production hardening.
Missing security evidence must remain explicit as findings or review-bound items rather than being inferred from filenames.

## Reference Package

Read `reference-packages/phase3-implementation-delivery/wff-impl-security/` for the capability contract, SOP, output template, and source cards.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write findings, risk explanations, exploit narratives, remediation guidance, and final audit conclusions in Chinese
- preserve code, file paths, commands, symbols, API/schema field names, trace ids, artifact ids, CVE/CWE identifiers, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only security reports or audit commentary unless the user explicitly requests English

## Rules

- Do not infer auth, tenant isolation, or secret hygiene from naming alone.
- If a multitenant path exists, cross-tenant denial evidence must be inspected explicitly.
- Missing validation or missing negative-path evidence counts against readiness.
- Secrets, tenant boundaries, and sensitive-field handling may not be waived because the implementation is early.
- If the audit depends on a control that is not materially implemented yet, record it as a finding instead of greenwashing it.

## Required Inputs

Read:
- `docs/phases/phase-3/phase-3-skill-architecture-design-v0.1.md`
- the case `tech-stack-decision.yaml`
- the case `openapi.yaml`
- the case `.env.example` or equivalent runtime env template
- the case `engineering-spec-pack.md` or Phase-2 data sensitivity and auth posture handoff
- tenant, auth, audit, and error-path tests in the current test tree
- the current implementation source tree
- `checklists/owasp-top10.yaml`
- `checklists/tenant-isolation.yaml`

## Required Outputs

- `security-audit-report.md`
- `security-audit-checklist.json`

## Primary Tool

- `scripts/phase3/phase3_delivery_gate.py --mode security-audit`

## Audit Playbook

Audit in this order:

1. Auth posture:
   - preferred auth vendor is frozen
   - backend contains a real auth/session/tenant enforcement surface
   - declared auth posture in `tech-stack-decision.yaml` and inherited engineering spec matches the actual implementation libraries/middleware
   - custom header parsing is not being used as a delivery-ready substitute for declared OIDC/OAuth2
   - development/test auth context headers are default-off and require explicit opt-in; if present, audit them as a controlled test channel rather than production auth
   - token / session expiry and forbidden-path handling are not silently skipped
2. Tenant and verification posture:
   - tenant isolation tests are present and not placeholder-only
   - audit-log or audit-surface tests are present and not placeholder-only
   - cross-tenant negative access and policy deny paths are materially evidenced when applicable
3. Validation / secret posture:
   - API inputs are validated through declared schemas or equivalent runtime validation
   - `.env.example` preserves secret placeholders
   - API error envelope keeps machine-readable error fields
4. Sensitive-data and OWASP posture:
   - P2 sensitivity-critical fields have a visible treatment posture
   - OWASP checklist surfaces are reviewed explicitly, not implied

If the only evidence is file names or placeholder throws, the audit must fail.

## Completion Standard

Security audit is done only when:
- `security-audit-report.md` and `security-audit-checklist.json` are both generated
- auth, tenant isolation, secret placeholder, and audit-surface status are explicit
- unverified or missing controls are recorded as findings instead of omitted
- the report clearly separates structural pass signals from review-bound or blocked areas
