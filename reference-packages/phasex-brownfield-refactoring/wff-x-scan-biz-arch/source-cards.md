# wff-x-scan-biz-arch Source Cards — scan-biz-arch

## Primary Inputs

- `wff-x-scan-code-baseline` codebase baseline output
- product documents, user manuals, support tickets, incident notes, or stakeholder notes
- route/controller/service behavior when documentation is thin
- `wff-x-scan-db-baseline` data baseline when business meaning depends on persisted concepts

## Method Cards To Apply

- business truth must be review-bound when inferred from implementation
- role, frequency, and risk drive flow priority
- business rules, implementation rules, and architecture hints must stay separate
- source conflicts are useful evidence, not cleanup residue

## Anti-Patterns

- treating routes, table names, or service names as confirmed product truth
- hiding unknowns to make P1 re-entry look complete
- letting P2 architecture language replace P1 business judgment
- skipping role / permission discovery because the codebase is backend-heavy
- claiming stakeholder or owner sign-off from repository evidence
