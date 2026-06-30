# Phase-3 Action Card Runner Protocol v0.1

Status: runtime-facing adapter protocol

This protocol keeps Phase-3 Action Card execution agent-agnostic. WFF owns the slice
packet contract, scheduling evidence, and claim ceilings. A runner adapter owns how a
specific coding environment performs the write-capable work.

## Boundary

WFF core must not depend on Codex, Claude Code, Cursor, GitHub Actions, or any other
specific code-agent runtime. Those tools may be provided as adapters that implement
this protocol.

The stable protocol id is:

```text
action-card-runner/v1
```

## Runtime Entry

Phase-3 may invoke one batch runner command for a worker packet's ready Action Card
slices:

```bash
PHASE3_ACTION_CARD_BATCH_RUNNER_CMD="..."
```

The batch runner is the preferred acceleration surface. It receives the whole slice
manifest once and may fan out through the current host/container's native SubAgent
facility, a single `codex exec` supervisor, Claude Code tasks, CI jobs, local workers,
or sequential batch processing. If no batch runner is configured, Phase-3 falls back to
the existing main-thread generation path; SubAgent execution is skipped rather than
degrading to multiple per-slice CLI cold starts.

For explicit compatibility or diagnostics, Phase-3 may invoke a per-slice runner
command:

```bash
PHASE3_ACTION_CARD_RUNNER_CMD="..."
```

For compatibility, `PHASE3_ACTION_CARD_SLICE_RUNNER_CMD` may still be accepted as a
legacy alias, but new integrations should use `PHASE3_ACTION_CARD_RUNNER_CMD`.

When no per-slice runner command is supplied, explicit per-slice runs may auto-discover the bundled
`scripts/phase3/action_card_agent_runner.py` adapter. That adapter is still
protocol-based: it receives one slice packet, prepares a bounded prompt, invokes a
write-capable code agent, checks only allowed file changes, runs listed slice
commands, and writes the standard result JSON.

The same bundled adapter can also be used as an explicit batch runner:

```bash
PHASE3_ACTION_CARD_BATCH_RUNNER_CMD="python scripts/phase3/action_card_agent_runner.py"
```

In batch mode, the bundled adapter accepts the worker-packet slice manifest, writes
one packet/result pair per ready slice, and records
`action-card-agent-adapter/batch-runner-report.json`. Its current implementation is
batch-supervised but sequential inside the adapter; `--max-workers` is recorded as
capacity metadata until a host-native SubAgent/worktree fanout adapter is supplied.

The bundled adapter runs each slice in an isolated workspace. Dependency roots such
as `node_modules` are copied into that workspace rather than symlinked back to the
source workspace, so write-capable agents and verification commands cannot mutate the
source workspace through dependency aliases.

Auto-discovery can be disabled:

```bash
PHASE3_ACTION_CARD_RUNNER_AUTO_DISCOVERY=0
```

The bundled adapter can be pointed at any code-agent command:

```bash
PHASE3_ACTION_CARD_AGENT_CMD="..."
```

If no agent command is supplied, the adapter may auto-discover `codex exec` when
available. The bundled Codex discovery preserves user config by default so the
current environment's provider, auth, and model-routing configuration remains
available to the adapter. User/project exec rules are also preserved by default so
SubAgent execution sees the same code-agent environment as the parent process.
Hermetic diagnostics may explicitly set `PHASE3_ACTION_CARD_AGENT_IGNORE_USER_CONFIG=1`
and/or `PHASE3_ACTION_CARD_AGENT_IGNORE_RULES=1`. Agent-level discovery can be
disabled separately:

```bash
PHASE3_ACTION_CARD_AGENT_AUTO_DISCOVERY=0
```

The optional model hint for the bundled adapter is:

```bash
PHASE3_ACTION_CARD_AGENT_MODEL=gpt-5.3-codex
```

Codex adapter runs may also provide fallback model hints for the current
environment:

```bash
PHASE3_ACTION_CARD_AGENT_FALLBACK_MODELS=gpt-5.3-codex,gpt-5.4
```

These are adapter hints, not WFF methodology. Before running a Codex slice, the
bundled adapter performs a small liveness probe for the primary command and any
fallback model variants. If a model cannot answer that probe inside
`PHASE3_ACTION_CARD_AGENT_LIVENESS_TIMEOUT_SECONDS` (default `30` seconds), the adapter records
`agent_liveness_probe_timeout:<seconds>:model=<model>` and tries the next model
variant instead of spending the full slice timeout. If every variant fails the
probe, the slice blocks with `no_live_agent_command_variant`.

The bundled adapter has two timeout layers. The inner code-agent timeout defaults to
`900` seconds and is expected to write controlled evidence. Codex auto-discovery
uses `codex exec --json` so the adapter can observe JSONL events while preserving
the same user config/rules environment as the main process. If a Codex slice
execution produces no event/output inside
`PHASE3_ACTION_CARD_AGENT_FIRST_OUTPUT_TIMEOUT_SECONDS` (default `10` seconds),
or produces only startup events without a substantive agent/tool event inside
`PHASE3_ACTION_CARD_AGENT_FIRST_PROGRESS_TIMEOUT_SECONDS` (default `120`
seconds), the adapter records
`agent_no_response_timeout:<seconds>:model=<model>` and may retry the same live
model once with a compact prompt before trying another live model variant. A
timeout after the agent has started changing files is recorded as
`agent_command_timeout:<seconds>`. A Codex timeout with no allowed-file changes
means the agent/model invocation did not produce usable slice work evidence and
is not, by itself, evidence that the Action Card slice was too large. Slice
command timeout also defaults to `900` seconds. The outer slice-runner timeout is
derived from liveness-probe timeouts, first-output/progress no-response attempts,
configured agent timeout, command timeout, repair-attempt count, and a cleanup
overhead so the adapter has time to record its own controlled blocker before the
worker packet falls back to `slice_runner_timeout:<seconds>`.

Optional metadata:

```bash
PHASE3_ACTION_CARD_RUNNER_KIND=generic
```

Examples of runner kinds include `generic`, `codex`, `claude-code`, `cursor`,
`github-actions`, and `human`.

## Dynamic Adapter Bootstrap

Each backend worker packet run that has Action Card slices writes a bootstrap packet
under the run directory:

```text
action-card-runner-bootstrap/
```

The bootstrap packet is for dynamic agent self-adaptation. It tells the current Code
Agent or external runner how to implement `action-card-runner/v1` without requiring
WFF core to know whether the environment is Codex, Claude Code, Cursor, CI, or a
human handoff.

The bootstrap packet includes:

- `runner-protocol.md`: the invocation contract for the current run.
- `capability-probe.md`: questions the adapter should answer before choosing a mode.
- `adapter-instructions.md`: supported modes such as direct write, subagent parallel,
  worktree parallel, sequential, or manual handoff.
- `result-schema.json`: the standard result JSON shape.

The bootstrap packet is guidance only. It is not execution evidence, durable release
proof, or permission to widen slice boundaries.

## Runner Invocation

The preferred batch runner is called once per worker packet with:

```text
<batch-runner> --slice-manifest <path> --result-dir <path> --workspace-root <path> --run-dir <path> --max-workers <n>
```

It writes one result JSON per ready slice into `--result-dir`, named from the slice id
as `<safe-slice-id>.result.json`.

The explicit compatibility per-slice runner is called once per ready Action Card slice
with:

```text
--slice-packet <path>
--result <path>
--workspace-root <path>
--run-dir <path>
```

The runner may use any internal mechanism: host-native SubAgents, a local process, a
Code Agent, a worktree, a queue, or a human handoff. That mechanism is outside the WFF
core contract.

Batch runners receive an authoring worker limit. The default `3` is intentionally
conservative because write-capable Code Agent sessions have non-trivial startup,
repository-context, model-queue, and local verification cost. Runs that have enough
CPU/model capacity may raise the limit:

```bash
PHASE3_ACTION_CARD_AUTHORING_MAX_WORKERS=5
```

`PHASE3_ACTION_CARD_SLICE_MAX_WORKERS` remains a compatibility alias. Worker packet
manifests record `configured_authoring_max_workers` and
`active_authoring_max_workers` so later review can see whether a run used the default
or an explicit override.

## Input Contract

The slice packet includes at minimum:

- `slice_id`
- `slice_status`
- `action_card_refs`
- `source_refs`
- `operation_id` or `operation_ids`
- `allowed_edit_files`
- `forbidden_edit_patterns`
- `green_commands`
- `done_criteria`
- `claim_ceiling`

Adapters must treat `allowed_edit_files` and `forbidden_edit_patterns` as hard write
scope boundaries unless they return blocked.

## Result Contract

The runner writes JSON to `--result`:

```json
{
  "slice_id": "wave-01:backend:createexample",
  "status": "implemented",
  "changed_files": ["apps/api/src/modules/example/example.service.ts"],
  "commands_run": ["pnpm exec vitest run tests/contracts/createexample.contract.test.ts"],
  "evidence_summary": "Implemented the slice and ran targeted contract tests.",
  "blockers": [],
  "claim_ceiling": "slice-level runner evidence only"
}
```

Accepted successful statuses are `implemented`, `pass`, `passed`, `success`, and
`done`. Review-only statuses such as `reviewed` and `read-only-reviewed` do not count
as write execution.

## Evidence And Claims

Runner evidence can raise a slice from protocol-ready to runner-executed only when the
result records changed files or a clear no-change rationale, commands or explicit
blocked reasons, and a bounded claim ceiling.

Runner evidence does not by itself prove Phase-3 completion. Phase-3 completion still
depends on packet gates, verification/runtime evidence, traceability, review, and the
global claim ceiling.

Runtime evidence must make SubAgent cost visible instead of hiding it inside the
Phase-3 total. `phase3-timing-report.json` includes a `dispatch_lane` segment, and
`subagent-slice-run-manifest.json` records `slice_runner_duration_seconds`,
`slice_runner_cumulative_duration_seconds`, `slowest_slice_duration_seconds`, and
`slowest_slice_id`. A slow run should be explained from those fields before blaming
Action Card size or generation quality.

If the bundled adapter's post-edit command evidence fails, the adapter may perform a
bounded repair loop in the same isolated slice workspace. The repair prompt includes
the failed command, blockers, changed files, and stdout/stderr tails. The adapter must
rerun the slice commands after repair and merge back only when the final slice status
is successful.

Timeouts and boundary violations are controlled blockers:

- Agent timeout is recorded as `agent_command_timeout:<seconds>`.
- Codex liveness probe timeout is recorded as
  `agent_liveness_probe_timeout:<seconds>:model=<model>`.
- Codex no-response slice timeout with no allowed-file changes is recorded as
  `agent_no_response_timeout:<seconds>:model=<model>`.
- Slice command timeout is recorded as `command_timeout:<seconds>:<command>`.
- Runner timeout is recorded as `slice_runner_timeout:<seconds>`.
- Any file change outside `allowed_edit_files`, whether made by the agent or by a
  verification command, is recorded as `forbidden_file_changes_detected:<path>`.

A blocked slice must not be hidden by a green global verification run. Worker packet
manifests recompute `packet_claim_ceiling` after runner execution. If any slice is
blocked, the manifest gate is blocked and Phase-3 formal delivery claims are capped
until the slice is repaired or explicitly routed.

## Adapter Examples

- A Codex adapter may spawn Codex worker agents and merge their patch results.
- A Claude Code adapter may use Claude Code tasks or worktrees and write the same
  result JSON.
- A CI adapter may dispatch independent jobs and collect their artifacts.
- A human adapter may expose the slice packet to an engineer and record their
  result manually.

All adapters are interchangeable only to the extent that they honor
`action-card-runner/v1`.
