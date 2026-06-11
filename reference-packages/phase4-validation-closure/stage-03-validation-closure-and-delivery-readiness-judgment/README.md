# Stage-03 Runtime Package — validation-closure-and-delivery-readiness-judgment

## Purpose

This stage reviews validation results and converts them into a downstream-ready closure judgment.

Its job is to make explicit:

- what was reviewed
- what evidence exists
- what risks and unresolved defects remain
- what closure decision was reached
- what downstream consumers may and must not assume

## Runtime package role

This directory holds the runtime-facing assets for Stage-03, including:

- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`
- verification assets

## Upstream dependency

Stage-03 depends on a usable Stage-02 output package with explicit:

- execution evidence package
- evidence summary
- defect and blocked/risk visibility
- Stage-03 handoff summary

## Downstream target

Stage-03 hands off to the optional Phase-4 Stage-04 release-readiness extension, or an equivalent downstream consumer, with an explicit validation judgment and known reliance boundaries.
