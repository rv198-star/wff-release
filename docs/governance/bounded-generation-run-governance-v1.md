# Bounded Generation and Run Governance v1

This contract implements the approved generation rules for the P1/P2 rectification cycle. It follows the Workflow / Agentic / Evidence responsibility matrix and the P3 realization-decisions contract. It defines generation control; it does not claim that the deferred D pipeline or P3 runtime redirection is already implemented. Frozen P1/P2 remain read-only within the cycle.

## 1. Four generation rules

- Repair only the failed section with concrete diagnostics, at most twice after its initial attempt (`attempt=0,1,2`). If it still fails, deliver a `degraded-T1` or `degraded-T2` gap marker and continue other sections. A completed but invalid remote response is not a terminal failure of the entire unit.
- Prohibit carrying **unaccepted answers across runs**. Diagnostic repair within one run and reuse of already accepted sections with their exact input/template identity are allowed. Rerun only failed or changed sections; do not launder stale acceptance into current evidence.
- Deliver useful sections with explicit gaps and claim ceilings. Complete frozen batches and immutable evidence are requirements of the formal exit only; they are not prerequisites for development iteration.
- Default to permissive local parsing plus strict code validation. Harmless representation differences may be normalized; invalid references, structure, or identities still fail validation. Provider schema is optional only when small and shallow; D defaults to no provider schema. Never use a giant provider schema or one atomic response for an entire unit.

## 2. Mechanical gates, judgment, and template boundaries

Generation hard gates cover structure and identity only: IDs, references, per-section output shape, and no unregistered new facts. Slot bounds and successful rendering are structural checks. Semantic quality is reviewed through scores or warnings, not a full-content coverage/closure gate. Missing content is explicit downstream feedback; a polished schema or a test count does not prove business value.

Agentic selects patterns, parameters, trimming, and bounded business-specific text. Workflow instantiates patterns, fills slots, generates provenance and claim ceilings from references, numbers, cross-references, and renders. The model never writes composition handles, nested compositions, or variant tags. A versioned template contains section skeletons, pattern applicability/parameters, and fixed expression; it carries no business answers or business defaults and never pads output to a quota. Unmatched cases may use bounded custom sections marked for later template consideration. Report custom-section proportion.

The seven conservative defaults in `reference-packages/phase3-implementation-delivery/p3-realization-decisions-contract.md` are approved risk-handling rules, mechanically applied by Workflow to gap decisions. They are not permission to embed scenario answers or business defaults in templates/scripts. Sensitive decisions retain `confirmation_required = true`, provenance, and a claim ceiling.

This generation rule does not turn a failing runtime test into a success or relax source/digest identity. P4 remains read-only; existing OMR → isolated SQR reviews semantic quality and T2 decisions without extra review rounds. Formal claims remain bounded by evidence.

## 3. Development and formal exit

Development permits a single scenario and a single section, an authorized real call with a template, prompt repair followed by a bounded rerun, and cache replay. A **single-scenario single-section real run with a template** is valid CP2 evidence. Identify replayed versus real calls; cache evidence cannot masquerade as a fresh model run. Preserve accepted sections and gaps independently.

Frozen batches, immutable formal evidence, and three-of-three (3/3) scenario qualification apply at the formal exit. They must not block a development section from yielding useful evidence. The independent model-authorization and declared-run-cap rules still apply during development; M0 makes no real model calls.

## 4. Per-call limits

- Request: at most approximately 60K tokens.
- Output: at most approximately 8K tokens.
- Local schema depth: at most three layers.

Split sections or simplify representation when a limit would be exceeded. Do not increase the budget, add retries/rules, or move to a giant provider schema to compensate. Every real round changes exactly one axis: content, mechanism, or acceptance strictness. Declare that axis in the issue and PR. The approximate Stage-05 total of 15–25K output tokens per scenario is a provisional multi-call size target, not a single-call allowance; M1 evidence calibrates it.

## 5. Retain runtime simplification

Do not introduce standing Plan Challenge steps, an Integrator, duplicate approval, generation self-evaluation, whole-package sufficiency, or a fixed one-time supplemental-material allowance. Retrieve only relevant upstream fragments by ID/digest within the declared call/token limits. No new gate, role, controller, recovery layer, or audit round may compensate for failure.

Existing review remains bounded OMR followed by isolated SQR; neither is a generation self-evaluation or a new approval controller. P3 batches each slice's T2/conflict/infeasible gaps into one small call, checking existing decisions and delegation rules first. T0/T1 never escalate merely for reassurance. Keep records in the existing Authority Delta and human projection; no new Authority path/store. Runtime implementation follows the assigned later WPs, not this documentation change.

## 6. Separate evidence from code

Code/contract PRs add no files to historical run snapshots in the source repository. Retain run evidence in the WP0.1 artifact repository with read-only access. The source repository retains only indexes and summaries containing sha256 and exact source/commit identities; no copied frozen install packs in code PRs. Historical evidence is not rewritten.

Each real model call emits one JSONL line with: `run_id`, `wp`, `scenario`, `section` or `slice`, `attempt` (0–2), `request_tokens`, `output_tokens`, `duration_ms`, `parse_ok`, `validate_ok`, `diagnostics` (summary), `outcome`, `template_version`, `patterns[]`, `model`, and `prompt_sha256`. `outcome` is one of `accepted`, `repaired`, `degraded-T1`, `degraded-T2`, or `failed`.

Indexes include the exact command, output, exit status, CI URL when applicable, record location, and sha256. Report maximum/median output tokens, maximum request tokens, first-attempt and repaired acceptance rates, delivered/total sections, total tokens, call count, custom-section proportion, and from M1 onward gap-decision count and delegation hit rate. Every metric must be recomputable from raw records; do not substitute verbatim-adoption rate, test count, or a self-declared PASS.

## 7. Authorization and human stop-loss

Only WPs marked model execution “yes” or “possible” may make real model calls. Before each round, declare purpose, the one changed axis, call-count cap, token cap, and stop conditions in the WP issue. Caps are ceilings, not spending targets. Exceeding a declared cap requires Owner approval before any additional call. A P3 decision-call cap exhausted within a run selects and records conservative defaults without another call.

Never run until PASS or continue because budget remains. Two consecutive rounds within a milestone without measurable progress, or two failed acceptance reviews, stop execution: report evidence and options to the Owner, who decides scope reduction or the next direction. Do not invent another gate/role/controller to avoid stopping. Sustained high SQR rejection of T2 decisions requires an Owner principle-change decision before joint role decisions may be enabled. Propose the undecided token/decision-cap/rejection-rate parameters from M1 measurements in its acceptance request; the auditor ratifies them there.
