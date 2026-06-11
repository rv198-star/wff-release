# Design/Architecture Case-Backed Absorption Matrix（v0.1）

## Purpose

This matrix complements the Stage-2 source-unit coverage ledger.

The ledger answers:
- which source units exist
- which Stage they influence

This matrix answers:
- which **case lane** actually exercised those absorbed rules
- whether a source unit is only package-shaped, historically corrected, or locally replayed in a real case

## Absorption Lanes

| lane | meaning |
|---|---|
| `package-self-test` | exercised inside the authored family self-test / dry-run / verification assets |
| `historical-real-case` | exercised because a real case exposed a defect and the rule was patched into the repo |
| `local-real-case` | exercised in a current repo-local case directory under `tmp/local-artifacts/` |

## Current Matrix

| source family / rule cluster | package-self-test | historical-real-case | local-real-case | current note |
|---|---|---|---|---|
| boundary / declaration-state continuity | yes | yes | yes | shared spine is now exercised in all three lanes |
| NFR / quality-attribute absorption | yes | partial | yes | strong in GEO and packaged family; still benefits from another live case |
| public-boundary-only freeze discipline | yes | yes | yes | stable across family and current local case |
| dependency realizability / substitute boundary | partial | yes | partial | restaurant-owner is the strongest corrective lane; now being pushed earlier into Stage-01/03 |
| dominant bottleneck / baseline insufficiency / optimum review | yes | partial | yes | present in package + GEO; historical restaurant case mainly forced realism more than optimality |
| traceability coarse chain | yes | partial | yes | templates + self-test + local case can now be registry-managed |
| runtime-hardening state evidence | yes | no | partial | now present across authored family; still needs more replay depth in more than one real case |

## Immediate Interpretation

Phase-2 source absorption should no longer be described as "starter source library only".

The stronger wording is:

> Stage-2 now has a formal unit-ledger plus a case-backed absorption matrix, but still needs more equally deep local real-case replay before it can claim broad saturation.
