# Stage-2 Traceability Baseline (v0.1)

## 1. Purpose

This document freezes the minimum artifact-level traceability baseline that Phase-2 should adopt now.

Related Phase-2 support docs:

- `docs/phases/phase-2/stage-2-core-business-deliverables-checklist-v0.1.md`
- `docs/phases/phase-2/stage-2-runtime-hardening-targets-v0.1.md`
- `docs/internal/improvement-reports/stage-2-retrospective-and-optimization-v0.1.md`

The goal is **not** to fully implement fine-grained future `wff-base-traceability-management` coverage for every internal sub-artifact.
The goal is to stop Phase-2 from staying at “template placeholders only” and to make the coarse stage chain executable through the current `wff-base-traceability-management` pilot.

This baseline therefore defines:

- what Phase-2 documents must expose now
- how canonical IDs should look in first-pass dry-run artifacts
- how stage-to-stage `depends_on` and `feeds` should be expressed at the coarse-grained artifact level
- how `source_path` and `source_anchor` should be prepared for later `wff-base-traceability-management` binding

Current aligned state:

- all four Phase-2 runtime output templates expose the baseline trace fields
- all four Phase-2 self-test dry-run outputs demonstrate concrete coarse-grained IDs and links
- Phase-2 support docs and package README reference this baseline explicitly
- the official Phase-2 execution entry can now initialize, bind, register, validate, and report the Stage-01~04 coarse artifact chain through `wff-base-traceability-management`

---

## 2. Scope of this baseline

This v0.1 baseline covers **coarse-grained stage output artifacts**, not every internal paragraph-level artifact.

That means the first managed unit is:

- one Stage output document / dry-run output as one coarse artifact

It does **not yet** require full decomposition into:

- `BOUNDARY-*`
- `CAPABILITY-*`
- `SERVICE-*`
- `DATA-*`
- `RISK-*`

inside every section.

---

## 3. Required Stage-2 traceability fields now

All Phase-2 runtime output templates should expose at least:

- `artifact_id`
- `artifact_type`
- `depends_on`
- `feeds`
- `traceability_managed_by`
- `trace_binding_note`
- `source_path`
- `source_anchor`

The meaning is:

- `artifact_id`: canonical identity for the current coarse output artifact
- `artifact_type`: high-level artifact class
- `depends_on`: immediate upstream coarse artifacts required by this artifact
- `feeds`: immediate downstream coarse artifacts that should consume this artifact
- `source_path`: path of the concrete output artifact file
- `source_anchor`: document anchor that the `wff-base-traceability-management` layer can bind to now or later

---

## 4. Canonical ID shape for Stage-2 first pass

Current first-pass recommendation for the four Phase-2 substages:

- Stage-01 output artifact: `ARCH-STG01-OUTPUT-0001`
- Stage-02 output artifact: `ARCH-STG02-OUTPUT-0001`
- Stage-03 output artifact: `ARCH-STG03-OUTPUT-0001`
- Stage-04 output artifact: `ARCH-STG04-OUTPUT-0001`

Optional future refinement can split further into section-level IDs, but that is not required in this baseline.

---

## 5. Stage-to-stage coarse link baseline

### Stage-01
- `depends_on`:
  - `REQ-STG04-OUTPUT-0001` (or equivalent Phase-1 handoff coarse artifact)
- `feeds`:
  - `ARCH-STG02-OUTPUT-0001`

### Stage-02
- `depends_on`:
  - `ARCH-STG01-OUTPUT-0001`
- `feeds`:
  - `ARCH-STG03-OUTPUT-0001`

### Stage-03
- `depends_on`:
  - `ARCH-STG02-OUTPUT-0001`
- `feeds`:
  - `ARCH-STG04-OUTPUT-0001`

### Stage-04
- `depends_on`:
  - `ARCH-STG03-OUTPUT-0001`
- `feeds`:
  - `IMPL-STG00-INPUT-0001` (or equivalent downstream implementation-entry artifact)

---

## 6. Source binding baseline

Each coarse output artifact should also prepare for binding via:

- `source_path`
- `source_anchor`

Recommended first-pass anchors:

- Stage-01: `#arch-stg01-output-0001`
- Stage-02: `#arch-stg02-output-0001`
- Stage-03: `#arch-stg03-output-0001`
- Stage-04: `#arch-stg04-output-0001`

This keeps the docs compatible with the `wff-base-traceability-management` direction that prefers document binding through file + anchor rather than file alone.

---

## 7. What this baseline does not claim

This baseline does **not** mean:

- fine-grained `wff-base-traceability-management` runtime infrastructure is fully implemented
- every Phase-2 internal paragraph/table/diagram node is registry-managed
- link validation is automated for all future decomposition levels
- collision / rename reconciliation is solved

It currently means:

> Phase-2 artifacts are no longer traceability-empty or traceability-abstract, and the coarse Stage-01~04 chain can be registry-initialized, bound, validated, and reported in an official run.

They now carry a stable coarse-grained identity and coarse upstream/downstream linkage model that a future management layer can consume.

---

## 8. Immediate rule

From this point onward, Phase-2 output examples should not leave `artifact_id / depends_on / feeds / source_path / source_anchor` completely blank in dry-run outputs.

For official Phase-2 runs, do not stop at template fields:

- initialize the registry
- bind the artifacts
- register the Stage-01~04 chain
- validate the registry
- emit the registry report

Even if the management layer is not yet live, the authored package should demonstrate the intended coarse trace model concretely.
