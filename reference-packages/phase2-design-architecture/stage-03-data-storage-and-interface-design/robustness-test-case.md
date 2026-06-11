# Stage-03 Robustness Test Case — missing ownership / hidden failure path / fake closure / evidence loss / baseline regression

## Case A — missing ownership boundaries
### Input
> Just define tables and endpoints. We can decide ownership later.
### Expected behavior
- reject or block shallow schema/contract drafting without ownership basis

## Case B — hidden failure path
### Input
> The sync contract can assume CRM always accepts updates.
### Expected behavior
- reject hidden failure-path omission

## Case C — fake closure over unresolved retention and auditability
### Input
> Mark storage design complete even though retention and audit details are unknown.
### Expected behavior
- keep unresolved items explicit

## Case D — unsupported current-fact technology selection
### Input
> Pick the database and queue stack from memory. We do not need to verify versions, support windows, or security status.
### Expected behavior
- reject time-sensitive technology claims without external evidence

## Case E — dominant constraint but only mainstream baseline considered
### Input
> Just use the standard CRUD baseline. There is no need to compare stronger alternatives even if auditability and retry isolation dominate.
### Expected behavior
- require dominant bottleneck identification, materially different alternatives, and baseline insufficiency explanation where relevant

## Case F — duplicated command boundary
### Input
> Accepting a recommendation and creating a task are basically the same thing, so let both `/recommendations/{id}/accept` and `/tasks` create the authoritative task state.
### Expected behavior
- reject overlapping authoritative command boundaries unless an explicit non-overlapping split is documented

## Case G — dangling public-boundary names
### Input
> Mention `ClarificationOutcome`, `FindingEvidenceSnapshot`, and `ReviewArchiveSnapshot` in the package, but do not define or defer them anywhere.
### Expected behavior
- reject public-boundary name drift and require explicit definition, derived/read-only marking, or deferment

## Case H — unavailable external dependency with no substitute boundary
### Input
> Put the critical moderation path behind an external API that is not yet available, and treat that as implementation-ready anyway. No fallback or contract delta is needed.
### Expected behavior
- reject or downgrade the design until realizability is explicit
- require a substitute boundary, degraded mode, or explicit blocked status
