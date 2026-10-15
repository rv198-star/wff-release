# wff-impl-backend SOP

1. Confirm ActionCards and contract pack exist.
2. Load stack decision and project implementation conventions.
3. Generate backend implementation through the official runtime. For replay-safe `return-existing` slices, preserve `exact binding -> authorization -> pre-service replay lookup -> Service/provider on miss -> persistence`; never allow replay to bypass role/tenant policy.
4. Run targeted backend verification, including contract-valid replay results for any P3-local replay payload extension.
5. Route missing source truth to P1/P2 or missing runtime evidence to P3 remediation.
6. Preserve generated-runtime limitations and claim ceilings in delivery reports.
