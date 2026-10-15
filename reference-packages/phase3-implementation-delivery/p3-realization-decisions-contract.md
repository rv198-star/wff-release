# P3 Realization Decisions — Project Knowledge Contract

## Purpose

`p3-realization-decisions.md` is the fixed human-readable project knowledge artifact for material decisions learned during WFF-P3 realization after P1 product authority and P2 architecture authority have been frozen.

It is a supplement to the PRD and ESP knowledge chain. It is **not**:

- a rewritten or new version of the PRD;
- a rewritten or new version of `engineering-spec-pack.md`;
- a Human Audit publication artifact;
- a replacement for the canonical P3 Authority Delta ledger;
- permission to introduce unregistered product, architecture, security, contract, or persistence truth. T1 inference and T2 gap decisions follow the protocol below.

## Fixed project-level path

The filename is project-contractual and must not vary by case name, locale, implementation lane, or agent:

```text
<project-artifact-root>/p3-realization-decisions.md
```

For the standard full-lifecycle layout:

```text
<project-artifact-root>/
├── phase-1/                 # PRD and P1 evidence
├── phase-2/                 # engineering-spec-pack.md and P2 evidence
├── phase-3/                 # implementation/runtime/evidence
├── phase-4/
└── p3-realization-decisions.md
```

Direct P3 callers should pass `--project-artifact-root`. If they do not, the P3 output directory is the bounded fallback project-artifact root.

P3 also records the lookup binding at:

```text
<phase3-root>/.phase3-evidence/p3-realization-decisions-binding.json
```

The binding is an address/digest sidecar only. The human-readable content remains at the project artifact root.

## Authority relationship

The machine Authority Delta ledger remains canonical:

```text
<phase3-root>/.phase3-evidence/p3-authority-delta-ledger.json
```

The Markdown projection must bind the same:

- P3 implementation decision id;
- P3 implementation decision digest;
- Authority Delta content digest;
- delta identities and reconciliation posture.

The document must always state:

```text
upstream_reconciled = false
PRD backfill = not-performed
ESP backfill = not-performed
```

P3 must never make the Markdown more authoritative than its machine ledger.

## Three decision levels and the T2 checklist

| Level | Definition | Treatment |
|---|---|---|
| T0 — implementation detail | Layout, component, navigation presentation, wording, visual treatment, loading/empty/error presentation, responsive behavior, accessibility, default sorting/pagination, or 404 handling that does not change business meaning | P3 decides; retain only material decisions. |
| T1 — reasoned inference | An unstated choice derived from explicit P1/P2 facts, such as role menus from operation ownership, list columns from accepted attributes and tasks, or confirmation for an irreversible operation | P3 records the basis and reasoning; inference cannot contradict an explicit upstream fact. |
| T2 — new fact | A choice that adds or changes business truth | Use the gap-decision protocol; never introduce it without a record. |

Classify as T2 when a choice introduces a business entity or meaningful field, a role or permission, a business rule/threshold/price/policy, a state or transition, an external integration, a compliance/legal claim, a real name/data fact, or API semantics. A conflict between explicit P1/P2 facts or an infeasible explicit upstream fact also triggers a gap decision; T0/T1 must not be escalated merely for reassurance.

Keep T1 reasoning in the existing realization-decisions projection and its canonical Authority Delta source: `id`, `level`, `decision`, `basis` (P1/P2 IDs and digests), `reasoning`, `alternatives`, `reversible`, and `backport_target`. Reuse accepted reasoning across slices and runs. P3 retains implementation-local judgment over decision-sufficient context, plausible working-set scale, longitudinal continuity, and the user-consumable result; these are not fixed widget quotas.

## Gap-decision protocol

P3 is the sole decision maker. It does not summon product/architecture roles, add an approval role, create another Authority path, or introduce a second store.

1. Trigger only for `T2`, `conflict` (P1 versus P2), or `infeasible` (explicit upstream content cannot be realized).
2. Before implementing each slice, batch its triggered gaps into one small decision call, separate from implementation. For each topic, check existing decisions first, then upstream delegation rules, and only if neither matches fill a decision card. Slices with only T0/T1 do not add a gap-decision call.
3. Load the existing topic register, delegation/default sections, relevant P1/P2 fragments selected by exact ID and digest, and the slice's gap and implementation constraints. For every selected basis record, also load the original P1 records named by its `p1_refs`; IDs without original content are not sufficient input. Preserve each admitted value, distinct original record and digest. The existing dry-run fact comparison checks the gap packet against this exact source selection, including missing or changed P1 originals. Do not send the full PRD.
4. The product side of the card names affected user tasks/journeys, commitments, role permissions, states, external wording, and changes to business meaning. The architecture side names the service/object, interface/data/consistency/idempotency effects, reversibility, and affected realized slices. The conclusion records alternatives, decision, rationale, sensitivity, and confirmation posture.
5. Workflow mechanically applies the conservative-default table below for sensitive categories; it does not ask the model to invent a safer business default. Mark sensitive decisions and every T2 decision with nonempty `new_facts` `confirmation_required = true`; this allows bounded delivery but is not product-owner approval.
6. Register decisions by a stable gap-topic key within the existing ledger (`id` may provide that key); later slices/runs reuse them without re-debate. Declare a per-run decision-call cap before starting. At the cap, make no further call: record the applicable conservative option and claim ceiling. The cap is calibrated from M1 evidence; increasing a declared cap requires Owner approval.

Each call remains within approximately 60K request tokens and 8K output tokens, with local schema depth at most three. Split input/output or simplify representation when needed; do not add retries, rules, or budget to compensate.

### Conservative defaults — seven categories

These are explicit governance rules, not business answers embedded in generation templates.

| Category | Rule ID | Workflow-applied default | Confirmation |
|---|---|---|---|
| Permissions | `DEF-PERM-01` | Least privilege; grant no operation not granted upstream; do not merge roles. | `true` |
| Security and credentials | `DEF-SEC-01` | Deny by default; do not weaken authentication or introduce new credentials. | `true` |
| Tenant isolation | `DEF-TENANT-01` | Strict isolation; no cross-tenant reads or writes. | `true` |
| Compliance/legal | `DEF-LEGAL-01` | Make no external compliance/legal claim; mark related text undecided. | `true` |
| Pricing/billing | `DEF-PRICE-01` | Set no price; show undecided/demo explicitly. | `true` |
| Real external integration | `DEF-EXT-01` | Disable or simulate with an explicit demo label. | `true` |
| Other non-sensitive T2 | `DEF-OTHER-01` | Choose the smallest reversible option; introduce no upstream-undefined state transition; mark undecided. | A card with new facts requires `true`; a card without new facts determines its posture. Retain `true` at the call cap. |

P1 remains frozen without a delegation section during M1–M3. Product-side gaps therefore use existing decisions and these defaults; their observed use informs the M4 P1 delegation section. The new P2 interaction section supplies architecture/interaction delegation rules. A matched delegation rule may support T1 only if it requires no new fact or contradiction; sensitive gaps still use the conservative defaults.

### Authority Delta decision record — fifteen fields

Extend the existing `p3-authority-delta-ledger.json`; do not create a parallel ledger. Keep existing slice/decision identities and `applied_upstream=false`, and retain `upstream_reconciled = false` and the PRD/ESP `not-performed` backfill posture.

| Field | Required content |
|---|---|
| `id` | Stable decision identity/topic registration key. |
| `trigger` | `T2`, `conflict`, or `infeasible`. |
| `question` | The bounded gap to resolve. |
| `decision` | The chosen local behavior. |
| `basis` | Exact P1/P2 IDs plus digests. |
| `rule` | Delegation/default rule ID, or `none`. |
| `alternatives` | Considered options. |
| `rationale` | Reason for the choice. |
| `reversible` | Whether the choice can be undone. |
| `affected_surfaces` | Affected slices, artifacts, contracts, or consumer surfaces. |
| `new_facts` | Explicit array of added/changed facts, including an empty array when none. |
| `sensitivity` | Applicable conservative-default category or non-sensitive posture. |
| `confirmation_required` | Boolean; sensitive categories and any T2 with nonempty `new_facts` always `true`. |
| `backport_target` | Next-version P1/P2 destination. |
| `supersedes` | Exact overridden upstream IDs, or an empty array. |

## Effective truth, checking, review, and backport

Effective truth = frozen P1/P2 + recorded P3 decision deltas. A delta takes precedence only over the explicit entries it names in `supersedes`. Only a gap decision can supersede an explicit upstream fact; T0/T1 cannot silently override it. Keep the original frozen bytes and digests. Generate the merged view for P4/UAT/EKRI in the existing human realization-decisions projection with source IDs/digests and delta IDs; this is a derived read view, never a new authority/store.

Workflow checks **no unregistered new facts**: compare P3 entities, roles, permissions, states, and API fields with the P1/P2 authority index. Every item outside the index must resolve to a T1 reasoning record or a gap-decision record. This verifies registration and identity; it does not mechanically decide whether the inference or decision is reasonable, nor demand upstream content completeness.

Extend the existing OMR → isolated SQR review scope to T2 decision records. SQR does not receive OMR findings/results. Retain rejection counts/rate, provenance, rule use, and claim ceilings. Put T1 reasoning and gap decisions into the existing next-version backport queue through `backport_target`; never rewrite or regenerate frozen P1/P2 within the cycle. No extra review round is added. Sustained high T2 rejection rates require Owner approval before introducing joint role decisions. The M1 acceptance threshold is 20%, using only model-new T2 (rule miss or new facts), accumulated per milestone with a denominator of at least 10; review-bound results are reported separately. Do not use conservative-rule records to dilute this denominator.

From M2 onward, an SQR-rejected T2 is marked rejected in the effective view and backport queue and is not an accepted decision reference. Its proposed facts and supersedes are inactive; the frozen source remains active. Delivery notes list any already-applied code surfaces explicitly. Retain the original decision and review findings as evidence; do not rewrite frozen M1 records or silently claim code was reverted.

If P3 judges the upstream direction fundamentally wrong, report the facts and options. A human decides whether to end the cycle and begin another version; it is not an automatic phase-regeneration route. Workflow reads older frozen formats compatibly, declares absent evidence and claim ceilings, and never demands regeneration solely because WFF contracts/formats changed.

## What belongs in the human projection

Material project knowledge includes realization decisions that a later maintainer, product owner, architect, P4 reviewer, later P3/change flow, or EKRI query may reasonably need to understand the currently realized product.

Typical examples:

- product/workspace/page responsibility and task-continuity decisions;
- stable navigation and user-visible state/recovery decisions;
- role/visibility product treatment inside already frozen permission truth;
- BFF/session/browser trust boundaries decided during realization;
- stable frontend/backend realization boundaries;
- bounded architecture precision discovered during implementation;
- truthful product handling for unavailable frozen backend/provider capability.

Incidental code detail should not be expanded into project knowledge. An Authority Delta record may carry:

```json
{
  "human_projection": {
    "visibility": "implementation-only",
    "knowledge_scope": "implementation"
  }
}
```

Material records use `visibility=project-knowledge` and one of:

```text
product | architecture | ux | implementation
```

Historical records without `human_projection` remain compatible and are conservatively retained in the human projection rather than silently discarded.

## Empty-delta rule

The file is a hard P3 artifact even when no material Authority Delta exists. In that case it must explicitly state:

> No material realization decisions beyond frozen P1/P2 authority were recorded for this P3 decision.

This gives downstream consumers one stable lookup path instead of forcing them to infer absence from a missing file.

## P3 and P4 Gate

P3 may not close its current realization knowledge contract unless:

1. the canonical Authority Delta ledger is valid;
2. `p3-realization-decisions.md` exists at the project artifact root;
3. the binding sidecar points to the exact Markdown bytes;
4. P3 decision and ledger digests align;
5. every delta is either projected as project knowledge or explicitly indexed as `implementation-only`;
6. upstream reconciliation remains false.

P4 is read-only over this artifact. P4 validates presence, identity, digest alignment, and delta coverage. P4 does not edit the document or promote it into upstream truth.

## EKRI ingestion convention

The Markdown declares:

```text
EKRI ingestion eligibility = eligible-p3-realization-project-knowledge
```

EKRI may consume this fixed artifact as project realization/evolution knowledge. Any EKRI projection must preserve at least:

```text
knowledge_origin = P3-realization
upstream_reconciled = false
authority_posture = project-realization-knowledge
```

EKRI consumption must not promote the document into P1 product authority or P2 architecture authority. Formal PRD/ESP absorption remains a future explicit change/reconciliation operation.

## Claim ceiling

This artifact proves retained, human-readable P3 realization knowledge. It does not prove PRD/ESP revision, production truth, UAT, owner sign-off, production readiness, release authorization, or publication readiness.

## Runtime API and retained evidence

`p3_gap_decisions.resolve_slice_gaps` receives the exact slice/gap IDs, frozen fact index, existing canonical records, admitted delegation rules, and the run's existing Journal, context and plain-text sender. A gap may declare the existing single `affected_authority` owner (`P1` or `P2`); product backports must name their P1 owner explicitly, while omitted ownership retains the architecture-call P2 convention. It returns records for the existing implementation decision / Authority Delta ledger; it creates no parallel decision store. Its per-run cap counts actual gap calls including the one permitted identical network resend. A missing/invalid response, exhausted cap or oversized request retains conservative confirmation-required records. Reuse an existing topic before calling; a second gap discovered in the same slice does not create another decision task.

Read D through `load_interaction_gap_context(path, expected_sha256=...)`. A bounded v2 delivery's authored archive is reference only; missing review is not accepted delegation truth. Source selection uses `p3_fact_registration.load_frozen_fact_index`: original IDs and original-row digests survive selection from externally SHA-bound files. Do not substitute a hash of adapter prose for the original identity.

Call `check_realized_facts` over actual `openapi`, `sql` and consumed `runtime-config` files. The report binds paths and SHA-256, covers entities/roles/permissions/states/API fields, and lists every unmatched fact. Missing parser coverage, unresolved schema references or conflicting declarations cannot prove zero. This is a registration check; original implementation review and runtime evidence must verify the application's actual use of these artifacts. A model-authored `new_facts` array alone is not an observed-fact inventory.

Use `effective_truth` as an in-memory read view and pass `frozen_facts` to the existing `write_p3_realization_decisions` projection to show original facts, exact digests and delta IDs. Only explicit T2 supersedes changes precedence. The same Markdown includes next-version backport; the original files remain unchanged. Historical callers without a full fact index retain source references and disclose that missing projection coverage.

`bounded_challenge_binding.p3_gap_review_scope` extends the original implementation subject with all T2 records and their original basis; prepare OMR and isolated SQR from these same original inputs. The existing review host binds settled calls and retains each review's raw evidence. `p3_t2_sqr_metrics` reports explicit record verdicts, findings, reviewed/rejected counts, missing IDs and a null rate when nothing was reviewed. It never treats missing records as accepted and does not schedule calls or joint roles.

A UI IA read-model gap remains a P3 decision route. `p3_read_model_bindings` must name the decision ID/digest, actual OpenAPI file/hash, method/path and operation ID registered by that decision. Compiler, frontend contract validation and runtime smoke validate this linkage; later runtime/browser evidence still proves actual reads. Permission/role gaps keep least privilege and independent-role qualification checks.


M2 addenda implementation: new T2 creation mechanically enforces confirmation for nonempty
`new_facts`; historical frozen records remain readable without rewriting them. Effective views and
resolution references still require confirmation for their new facts, even when a legacy
record has the old false flag. After the existing
isolated SQR, use `apply_p3_t2_sqr_results(records, scope, receipt, applied_surfaces)` with keyword
arguments to bind its verdicts to the original decision digests in the same canonical records.
Report every scoped decision's actually applied surfaces explicitly (an empty list means none
reported). The annotation is immutable and does not apply or undo code. Accepted decision references retain
the original record digest, so attaching a review does not invalidate existing realized API bindings;
the ledger digest still binds the annotation. Feed the annotated
records to the existing Authority Delta ledger and realization-decisions projection;
`effective_truth` exposes rejected status, backport status and already-applied rejected surfaces.
`registered_resolution` and topic reuse never consume a rejected decision as a resolution.
No extra review, authority store, role, or upstream mutation is introduced.
