---
name: wff-interaction-map
description: Render an existing source-labeled P1 or P2 interaction-map packet for human review without changing phase authority, gates, or claim ceilings.
---

# WFF Interaction Map Rendering Kernel

## Status And Boundary

This is an optional Beta companion used by human-review artifacts. It is not a
lifecycle phase, content author, evidence acceptance mechanism, gate, or claim
authority. It must not create missing product or architecture truth.

P1 product truth remains owned by `wff-req`; P2 architecture truth remains
owned by `wff-arch`. Unknown or conflicting content stays review-bound in the
source packet.

## Packet Contract

The renderer accepts `wff.interaction_map.v1` packets. Packets preserve source
IDs, evidence states, node order, relation order, and the originating phase's
authority. Validation proves packet structure only; it does not prove that the
underlying business or architecture statement is true.

## Commands

Validate a packet:

```bash
python3 skills/wff-interaction-map/scripts/validate_interaction_map.py \
  --packet <packet.json> [--output <report.json>]
```

Check deterministic presentation constraints:

```bash
python3 skills/wff-interaction-map/scripts/check_interaction_map_layout.py \
  --packet <packet.json> [--output <report.json>]
```

The human-review dossier imports `render_embedded_svg()` from
`skills/wff-interaction-map/scripts/render_interactive_map.py`. The function validates before rendering,
uses no network or browser storage, and returns an SVG projection without
mutating the packet.

## Script Authority

- `validate_interaction_map.py` owns structural and reference checks only.
- `check_interaction_map_layout.py` owns deterministic layout constraints and
  advisory warnings only.
- `render_interactive_map.py` owns mechanical HTML/SVG projection only.

None of these scripts may infer source truth, change P1-P4 execution state, or
raise a claim ceiling.
