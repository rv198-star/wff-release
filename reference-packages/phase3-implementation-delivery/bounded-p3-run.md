# Bounded P3 repository entry

`scripts/phase3/run_bounded_p3.py dry-run|run --config <json> --out <directory>`
composes the existing frozen-input admission, delivered D reader, gap protocol,
shared bounded dispatch, Journal, draft CAS and original OMR then isolated SQR.
`run` also requires `--declaration <json>`. External directories hold only bound
configuration, declarations, immutable sizing substitutes and outputs.

Configuration supplies the original `inputs.sources` and `inputs.fact_sources`,
scenario `logical_id`, WP, phase/scenario `token_limit`, calibrated endpoint/model,
ordered author sections (instruction, selected fact IDs, D section IDs, exact
relative file allowlist, earlier dependencies), declared review groups, initial
records, gap slices, sizing substitutes and contingency reservation. Author
substitutes are actual retained file responses, never accepted new implementation.
The entry reads effective delivered D payloads; rejected authors remain unavailable
T2 context. Raw rejected D proposals are not passed as accepted design authority.

The dry run creates every author and original review prompt without constructing a
transport. It compares actual per-section author/reviewer facts, records prompt
hashes, maximum request estimate, all planned reservations, selected delivered D,
source admission, source commit and repository cleanliness. Gap prompts include the original P1 records named by the selected basis records' `p1_refs`. The same `fact_symmetry` report compares every gap fact with its admitted frozen original and lists its ID/digest under `gap_packets`; missing, changed or unrelated facts are violations of this existing check.
`require_fact_symmetry` remains enabled for M3. When `recompute_review_groups`
is enabled, actual author sizes choose the fewest fitting groups within the
allowance, releasing only unused protected slots after grouping. A declaration
may instead fix groups with `recompute_review_groups=false`; those groups never
merge. With `protect_reviews=true`, `protected_review_groups` optionally names
fixed zero-based group indices, each reserving 68K for OMR and 68K for SQR. Omit
that list to protect all groups as before. Selective protection requires fixed
groups so protected identities cannot move. Other declared groups are explicitly
unprotected, best-effort reviews. Settle protected OMR/SQR first, then attempt
optional reviews using the actual remainder. The same Journal reservation check still
preserves every unused protected token and call slot. A missing review is
`progress-unknown` in `review_progress`, never acceptance. Dry-run planned
reservation sums authors/gaps, protected slots and contingency; best-effort
reviews are sized and listed separately, with no guaranteed allocation.
No OMR finding enters SQR. No additional reviewer pass is created.

The configured ceiling is shared by at most two runs. Round two binds the first
run result, unchanged call JSONL and Journal accounting, cannot raise the scenario
ceiling, and may select only unmet sections. Its declaration must fit ceiling minus
first-run charge. Successful prior author files are retained; no accepted section
is regenerated. Each section permits at most two diagnostic repairs; decision
calls are capped at two per run. Transport recovery and manual first-attempt stop
use the existing shared rules and Journal; no controller or extra role is added.

The request calibration divisor starts at most1.4. Every completed response can
lower it, including after the initial three samples. Input at or below60K that
exceeds an estimate retains measured usage and continues while the Journal's total
budget/deadline permits. Output remains bounded at8K; cutoff/transport failures
consume the original request estimate plus8K. Unknown usage and measured input
above60K stop further dispatch. An estimate never replaces measured accounting.

`run-result.json`, original call JSONL, raw answers, review records, consumed D and
implementation files are evidence, with explicit unmet sections and claim ceilings.
Generated code still requires the existing fact-registration and runtime checks;
a structural file response or successful dry run does not prove runtime acceptance.
Apply the existing SQR decision annotations and report realized/runtime findings in
formal acceptance. Keep all frozen P1/P2 inputs unchanged; downstream gaps stay in
P3 and the next-version backport queue.

The existing fact-registration reader accepts original JSON or YAML OpenAPI bytes
using the locked safe YAML parser with local JSON-compatible scalar resolution
and scalar-string map keys, as required by the [OpenAPI format rules](https://spec.openapis.org/oas/v3.1.1.html#format).
Unquoted on/off/yes/no and date-like text keep their original string identities;
legacy implicit booleans, octal and timestamps are not substituted. It hashes the actual source artifact, resolves
only the already supported local references, and rejects ambiguous YAML mappings
or executable tags. Reading a format does not register its facts: all existing
identity/value/category comparisons and unsupported-schema diagnostics still apply. Non-string or empty fact identities remain in the report as `invalid-fact-id` findings, with their original value, type and artifact SHA; they are never converted into valid identities. Other observed facts are still checked. Non-string OpenAPI operation IDs produce an explicit parser diagnostic instead of a Python type error.
SQLite inspection also inventories rejecting BEFORE INSERT/UPDATE/DELETE triggers
with optional WHEN predicates, retaining every full lexical definition and the
explicit recursive-triggers pragma. Trigger bodies remain a single SELECT RAISE or SELECT CASE WHEN … THEN RAISE … END;
business writes, arbitrary pragmas and unsupported statements still prevent a
zero-unregistered claim. Parser coverage never supplies missing fact registration.

Model packets include each selected fact's exact kind, value and digest once.
Duplicate original-value/provenance metadata stays in the immutable admission
artifacts. When comparison pointers project a fact, its distinct full original
record remains model-visible; only an equal duplicate value is omitted. The author/reviewer comparison still checks every selected value.
For a second run that only completes missing reviews, `reuse_authored` may select
unchanged original authors that have never received either review. It binds the
original call, prompt/raw hashes, semantic configuration and dependencies; it
adds no synthetic call rows or author reservation. Already reviewed/rejected
authors are ineligible. Offline sizing uses their actual original outputs and
original author contexts, with the lowered request calibration carried forward.

For the M3 second acceptance, `protect_reviews=true` gives the existing Journal
one protected 68,000-token/call slot per planned review. Author/repair reservations
include all unused review slots; a human `stop_authors` does not cancel funded
OMR/SQR. Transport resends cannot consume another review's slot. Hard transport,
unknown-usage, total-budget and wall limits retain their existing semantics.

`bind-p2 --p2-result <current-run-result.json>` produces a configuration referencing
that scenario's entire current Stage01–04, engineering and D freeze, checking its
P1 identity and every manifest member against its retained digest before deriving
new selectors or digests. For each original family, remove P1 references found
in strictly more than half of that family's current records from the author's
P1 scope, falling back to its original scope if subtraction leaves it empty.
Select operations and other non-field families by intersecting that scope with
the records' own P1 references. Select fields by `operation_id` pointing to the
selected operations. Old IDs, paths and field names do not select records.
`p2_binding_scope` retains the original relation/family intent;
`p2_binding_evidence` records crosscut/effective references and every selected ID,
including each field's operation link. Every originally selected family must
remain nonempty or binding fails. Supplementary Stage04/engineering policy
selection stays unchanged and cannot hide an empty family. It does not rewrite
`AUTHOR`, `author_prompt`, or any case author instruction. P3 admission checks that
the bound sources/selectors are still those of this P2; stale old sources fail
locally. A complete artifact set does not imply all its sections passed review.

The offline `frozen_upstream` mode reads same-case original M3 author answers and
decisions, with their SHA-bound result/config/call log. It does not reuse those
answers for generation or review old products. Report prompt sizes, measured
comparisons, actual missing data and protected review/repair reserves for audit
verification. After the newly authorized P2 completes, bind its actual freeze and
repeat the zero-call P3 packing with the unchanged author instructions before
P3 dispatch; all calls remain inside the same declared scenario run and cap.


## P3 dispatch preconditions

After P2 completes, bind its actual freeze and repeat offline packing using the
request divisor that will be used at P3 startup. Dispatch P3 only if binding
succeeds without an empty or silently dropped original technical selection, all
author/review requests fit 60K within the declared group allowance, and
`planned_reservation_sum` fits the P3 cap. Failure of any condition is mechanism
recurrence ②: do not dispatch P3, change code/configuration, or add budget; retain
the diagnostics and stop.

## GEO-to-PetClinic recurrence decision

Use the Journal and calls records. Recurrence means (①) a planned review is
unfunded or its reservation is consumed by authors/repairs, excluding normal
release of surplus groups; (②) any request is rejected above 60K or review sizing
raises `SectionRejected`; (③) one validation-error class occurs on first answers
in at least three distinct sections that still fail after the existing bounded repairs; successfully repaired sections do not count, and pending/unattempted repairs are not treated as failed repairs; or (④) after `stop_authors` or budget
protection stops authors, a funded review does not execute. Three cumulative
transport errors and the wall-clock hard stop still stop all work; record them
separately, not as one of these four recurrences. Any recurrence in GEO cancels
PetClinic. Funded reviews otherwise finish under the existing hard limits.


## Binding a different frozen P2 run

Resolve both direct freezes and SHA-bound `freeze-lineage.json`/`previous_run`
references. Inherit stages not rerun and use the retained `new_architecture` or
`new_interaction` manifest when present, validating original members before
selecting facts. Accumulate transport errors across the bound P2 lineage; retain
`p2_freeze_lineage` provenance without copying or manufacturing upstream freezes.
Selected D sections must still exist in the admitted manifest; never drop a
missing selected section silently. The original M3 GEO input is first-round
architecture plus second-round D, not the first-round D freeze.

The same-scenario, same-P1 binding also covers every gap's `basis`, using the
original basis records' P1 relations and families. P1 basis IDs stay unchanged;
fields derive their scope from their parent operation and follow current selected
operations. Preserve scopes in `p2_basis_binding_scope` and per-selection evidence
in `p2_basis_binding_evidence`; any missing original family fails locally.
Rebinding must not leave old gap IDs behind even when author selections are valid.

Initial decision cards are exact-source claims. `p2_initial_records` retains the
originals only as binding evidence, outside model context. Keep cards whose basis
IDs/digests still match. For an unreviewed sensitive conservative-default card,
reapply the existing governance rule over its rebound basis without adding facts
or grants. Exclude stale inferences/semantic decisions from `initial_records` with
an explicit evidence reason; never transplant their inferred facts or review
annotations onto a new source by changing IDs. Rebinding to the original source
can restore its still-valid cards. Admission uses the existing gap/record
validators before dispatch and rejects stale basis/initial-record configuration.
This leaves author/review instructions and gap question text unchanged.

The earlier post-second-acceptance GEO P3 authorization is historical; the
current single-run allowance and M4 entry are in "Post-M3 A′ layered acceptance"
below. Original P3 answers/decisions remain immutable sizing data, never current
initial decisions or already accepted implementation. The operator counts R4③
only after the existing repair outcome is known, with the first call and all
repair IDs retained; successful repairs remove that section from the count.


## P3 dependency context and bounded semantic repair

Author dependencies are earlier sections. The entry supplies their transitive
original files, including explicit nulls when an earlier section has no accepted
file response. Consumer-test configurations must select the frontend and backend
implementations they exercise. Review groups receive those same dependency files,
including the contract, once per packet. Dependency files are contextual evidence,
not extra review subjects or extra reviewer rounds. Each subject keeps precisely
its own selected facts, D and decision content; dependent implementations do not
pull in unrelated design sections.

A permitted subsequent run can bind `repair_source` to an immutable previous
same-scenario result. The existing result/calls/Journal/file validation checks its
hashes and accounting. Unmet authors receive every applicable adverse OMR/SQR
finding and adverse decision finding, with original call IDs/digests and the prior
author digest. They rewrite their selected files against current truth and current
dependencies. Old accepted-decision prose is not a repair finding. Historical
findings do not populate the new decision ledger or reviewer packets. The first call of the new run is logged as attempt 1 (retain its source-review
call IDs when evaluating first-answer recurrence). The rewrite
consumes repair 1, leaving at most repair 2 for a structural diagnostic; it never
adds a review pass. The ordinary round-two path uses the same feedback behavior.
An external `repair_source` does not authorize another run or extra budget: that
requires the existing explicit authorization and declaration. The run still uses
its existing call/token/wall limits and reserves planned reviews before authors.

Source records remain complete in SHA-bound admission evidence. Model packets
omit provenance lists (`p1_refs`, `source_refs`, `backfill_refs`) and a repeated
self-ID equal to the surrounding fact key. Operation links, business fields,
semantics, authority and truth-state remain unchanged. Decision packets retain
semantic fields and the original ledger digest; redundant ledger coordinates
stay in the immutable original, and basis lists reference original IDs. Equal D
gap lists appear once. Review envelopes carry decision ID/digest once and share
identical claim-ceiling text by an explicit index. Author/reviewer comparison
reconstructs those envelope values; no source value or decision is rewritten.

Case instructions follow the frozen runtime baseline, or select a pre-registered
reversible P3-local deviation using the existing T2 ledger. Its exact source
basis, rationale, alternatives, affected surfaces, confirmation posture and claim
ceiling accompany every affected author and review. A local test carrier cannot
claim the original production deployment, security or authorization has passed.

SQLite inventories include partial-index WHERE clauses and single-statement
CASE rejection triggers, retaining their entire definitions. Unknown statements
still fail closed. A cross-artifact identity conflict produces a complete failing
report with both observations, not a partial zero-difference report. Comparison
projects explicit P2 operation method/path and field name/type (including array
elements, nullability and explicit enum members); it resolves only an exact
operation-ID namespace or a field's own enum sub-ID. Ambiguous prose remains an
unresolved comparison. Reports separate missing identities, different values,
unresolved representations and conflicting identities. An API explicitly referencing the same stable DB field ID can project SQLite
TEXT/string and REAL/number, and an unambiguous leading registered type or
method/path can project a descriptive value. This does not verify its prose
qualifications: complete SQL constraint definitions and semantic review remain
required. Different IDs, nullability, array types and predicates remain distinct;
unresolved descriptions are not counted as new identities. Parser success does not register new facts or prove semantics.


## Post-M3 A′ layered acceptance

Owner decision #1203/6185468576 and plan v1.3 fix `[contract, backend-core]`
and `[frontend-app, consumer-tests]`; protect group 0 only. Both original
review packets must estimate at most52K in the post-merge preflight, with planned
reservation at most439,638 and a clean zero-call report. Remove the added
3,000-token case-author target; keep complete answers and review material.
After the full suite has no new failures, declare the merged commit, bound
configuration/report hashes and new empty output directory, then await audit
release. One GEO P3 only, caps439,638 tokens/22 calls/3h; no P2 or PetClinic run.
Backend OMR and SQR acceptance plus the existing backend schema/runtime checks
form the M4 entry. Frontend authoring and reviews continue as progress only;
formal frontend acceptance awaits D roles_tasks/view_states/views. WP4.1 may
proceed independently; WP4.2 scenario runs await backend acceptance. Backend
failure ends model calls this cycle. Freeze and submit results, then stop; no
in-run edits or reruns. Historical M3 verdicts and per-section criteria stand.
