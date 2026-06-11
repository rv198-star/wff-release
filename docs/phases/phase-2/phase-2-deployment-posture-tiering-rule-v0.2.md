# Phase-2 Deployment Posture Tiering Rule (v0.2)

## Purpose

This rule separates two concerns that should not be mixed:

- design discipline
- deployment / infrastructure posture

Phase-2 should keep a high design standard even for small cases.
What should vary by need is the deployment and infrastructure weight, not whether the design is structured well.

## Rule 1. High-spec design discipline stays fixed

The following design discipline should stay available across `light`, `standard`, and `heavy` cases:

- service-first or clear application-service decomposition
- interface-first / contract-first boundaries
- test-first or verification-first thinking
- IoC / DI and other explicit decoupling seams
- AOP-style cross-cutting isolation where it improves clarity
- explicit module, boundary, and ownership design
- explicit failure semantics, security posture, and observability posture

These are design-quality choices.
They do not by themselves force a distributed deployment.

## Rule 2. Deployment posture is a separate control surface

Phase-2 should explicitly select one deployment posture:

- `light`
- `standard`
- `heavy`

This posture controls deployment/runtime/infrastructure weight.
It does not replace the existing `complexity-profile`.

Relationship to the current control surface:

- `complexity-profile` controls minimum output thresholds and expected design density
- `deployment_posture` controls how heavy the deployment and infrastructure solution is allowed to become

`micro / standard / complex` is therefore not a license to silently move into heavier runtime topology.

## Rule 3. Default to the lightest deployment posture that satisfies explicit constraints

Phase-2 should begin from `light` and upgrade only when an explicit trigger exists.

### 3.1 Light

Default posture for small and moderate cases unless stronger triggers exist.

Typical shape:

- one deployable unit or modular monolith
- synchronous calls first
- one primary data store first
- internal events allowed, but no broker is required
- orchestration may stay inside the application process

### 3.2 Standard

Use when the case clearly benefits from stronger deployment separation or selective asynchronous infrastructure, but does not yet justify a platform-heavy runtime.

Typical shape:

- modular runtime with limited service separation
- selective async infrastructure where it closes a real constraint
- more explicit integration isolation than `light`
- limited extra infrastructure with explicit justification

### 3.3 Heavy

Use only when the case is explicitly constrained into a heavier runtime posture.

Typical shape:

- multi-service or distributed deployment
- event bus, workflow engine, or other explicit coordination infrastructure
- multiple infrastructure dependencies
- stronger isolation, compliance, resilience, or scale posture

## Rule 4. Trigger-backed upgrade only

AI must not upgrade deployment posture because a design looks cleaner, more scalable, more future-proof, or more advanced.

A posture upgrade must be supported by explicit case signals such as:

- multiple teams or domains need partially independent deployment/evolution
- explicit asynchronous decoupling or eventual-consistency workflow is required
- scale, throughput, isolation, or resilience requirements exceed simpler runtime options
- external integration surface is materially broad or operationally sensitive
- compliance, audit, tenancy, or boundary isolation requirements require it
- inherited platform constraints or organization standards require it

If the signals are weak or ambiguous, keep the deployment posture lighter and carry uncertainty as review-bound instead of silently upgrading.

## Rule 5. Human override is allowed, but never silent

Human-directed deployment posture override is allowed.
This preserves a governance escape hatch for platform strategy, team constraints, procurement realities, or explicit architectural preference.

However, a human override must produce an explicit warning record.

Minimum warning fields:

- `deployment_posture_suggested`
- `deployment_posture_selected`
- `deployment_posture_warning_class`
- `deployment_posture_override_source`
- `deployment_posture_override_reason`
- `deployment_posture_added_risks`

Recommended warning classes:

- `constraint-backed-override`
- `preference-driven-override`

Interpretation:

- `constraint-backed-override`: not the lightest posture, but there is a real external constraint
- `preference-driven-override`: upgrade was chosen mainly by preference, standardization desire, or future-oriented bias, so over-design risk must stay visible

## Rule 6. Anti-patterns

The following are not valid trigger reasons by themselves:

- "it may be useful later"
- "this is more scalable in theory"
- "this architecture is more modern"
- "AI can implement it anyway"
- "the team is familiar with it"

These reasons may appear inside a human override rationale, but they must not be treated as system-valid upgrade triggers.

## Rule 7. Practical interpretation for the current Phase-2 rollout

For the current repository state:

- keep high-spec design discipline stable across all cases
- keep the existing `complexity-profile` for threshold scaling
- tier deployment/runtime/infrastructure weight separately through `deployment_posture`
- do not let AI silently convert complexity or design neatness into infrastructure heaviness
- allow human-forced posture override, but emit an explicit warning trail in the wrapper and execution report
