# Phase-1 Gate Authority Map

Status: v1.3.x maintenance authority map.

This document defines the current Phase-1 script authority boundary. It does not change gate behavior.

## Canonical Phase-1 Closure Entrypoints

Use these scripts for canonical Phase-1 mainline closure:

- `scripts/phase1/run_phase1_full_trial.py`
- `scripts/phase1/run_phase1_convergence.py`

Only these entrypoints can support a Phase-1 mainline closure claim. They may
invoke support gates as part of a bundle, but a support gate pass alone is not
Phase-1 closure.

## Phase-1 Support Gate Surface

These scripts are phase-profile support gates. They may block or inform the
canonical Phase-1 runner, but direct execution has a narrower claim ceiling:

- `scripts/phase1/phase1_stage_artifact_depth_gate.py`
- `scripts/phase1/phase1_prd_quality_gate.py`
- `scripts/phase1/phase1_prd_executability_gate.py`

Direct passes from these scripts are support evidence only unless the canonical
runner consumed them as part of the selected Phase-1 path.

## Bundle-Internal Compatibility Scripts

These scripts remain in the bundle for compatibility, audit, direct diagnostics, and targeted remediation:

- `scripts/phase1/phase1_prd_assembly_integrity_gate.py`
- `scripts/phase1/phase1_prd_analysis_delta_gate.py`
- `scripts/phase1/phase1_prd_section_scoring_gate.py`
- `scripts/phase1/phase1_artifact_consistency_gate.py`

They are not peer canonical closure gates. A direct pass from one of these scripts is support evidence only. It does not prove Phase-1 mainline closure unless the canonical driver consumed the result as part of `prd_mainline_gate_bundle`.

## Maintainer Rule

When adding, renaming, or retaining a Phase-1 gate-like script, update `scripts/phase1/phase1_gate_authority.py` first. Release manifests and runtime snapshots consume that map so the install pack does not drift into multiple apparent peer gate systems.
