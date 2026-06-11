# Stage-02.5 Robustness Test Case — hidden dependency / no auth / no fallback / fake skip

## Case A — dependency exists but Stage-02.5 omitted
### Expected behavior
- warn that activation/skip decision is missing when external dependence is visible upstream

## Case B — active dependency with no auth posture
### Expected behavior
- fail active-lane completeness

## Case C — active dependency with no timeout / retry / fallback
### Expected behavior
- fail active-lane completeness

## Case D — active dependency with no test strategy
### Expected behavior
- fail active-lane completeness

## Case E — skipped with no reason
### Expected behavior
- fail skipped-lane completeness

## Case F — active lane with no risk register
### Expected behavior
- fail active-lane completeness

