#!/usr/bin/env python3
"""Phase-2 first-version runtime slice: phase2_first_version_design_model.py."""

from __future__ import annotations

from phase2.phase2_first_version_semantic_model import *  # noqa: F401,F403

def adr_content_for(
    *,
    title: str,
    service: ServiceSpec,
    case_name: str,
    upstream_ids: list[str],
    root_namespace: str,
) -> dict[str, object]:
    service_scope = f"`{service.home_module}` / `{service.public_contract}` / `{service.endpoint_name}`"
    ids = ", ".join(upstream_ids)
    lowered_title = title.lower()

    if title == "Adopt modular-monolith boundary with explicit public contracts":
        return {
            "context": f"First-wave `{case_name}` needs one workflow spine from intake and execution to closure, but current scale is closer to 120 req/min with 4x burst than to a multi-team, multi-region platform. The dominant constraint is keeping boundary, replay, and review-bound truth explicit without paying microservice coordination cost too early.",
            "decision": f"Adopt a modular-monolith baseline anchored by {service_scope}. Keep public contracts and ownership boundaries stable now, and defer physical service splits until runtime evidence shows throughput, team topology, or compliance isolation actually demand them.",
            "alternatives": [
                (
                    "split into microservices immediately",
                    "gives stronger physical isolation, but higher deployment complexity, more cross-service latency, and slower first-wave iteration for a case that still values workflow traceability over regional scale.",
                ),
                (
                    "keep one flat controller-led application layer",
                    "looks simpler in week one, but weakens contract ownership, makes replay evidence harder to preserve, and increases regression risk once findings, tasking, and review evolve independently.",
                ),
            ],
            "consequences": {
                "positive": "For the first-wave team and current throughput target, contract and module ownership remain explicit while onboarding and change cost stay manageable.",
                "negative": "Stage documents and namespace discipline become heavier up front, and any future physical decomposition still needs a deliberate migration plan for the next 2 to 3 releases instead of a silent refactor.",
                "risks": "If boundary complexity, compliance isolation, or p95 latency pressure grows materially over the next 2 to 3 releases, the same boundaries must be promotable into stronger runtime isolation without renaming public contracts.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the 120 req/min first-wave capacity target, and the requirement to preserve boundary/replay/review closure semantics across Stage-03 and Stage-04.",
        }

    if "payload" in lowered_title or "handoff" in lowered_title:
        return {
            "context": f"The insight -> action -> work path is the business hinge of `{case_name}`. If the handoff payload is reconstructed ad hoc during task creation, upstream rationale, target object hints, payload version, and blocked-reason semantics drift immediately.",
            "decision": f"Freeze a typed action-handoff payload before any downstream mutation. {service_scope} becomes the explicit boundary that carries payloadVersion, owner, target object, and decision posture into downstream execution without lossy remapping.",
            "alternatives": [
                (
                    "derive work-item fields dynamically from loose prose",
                    "is faster to scaffold, but weaker for replay, harder to diff over time, and more likely to lose blocked-reason or target-object semantics during operator handoff.",
                ),
                (
                    "flatten decision and execution into one mutable record",
                    "reduces short-term joins, but erases decision-stage history, blurs approval versus execution ownership, and makes audit or rollback analysis materially worse.",
                ),
            ],
            "consequences": {
                "positive": "Work-item creation stays deterministic in the first-wave release, and replay or audit can compare pre-execution and post-execution state without inventing missing payload context.",
                "negative": "Writers must honor payload versioning and schema discipline, so ad hoc field additions become slower than a free-form note-based workflow.",
                "risks": "If future slices need richer generated suggestions or partial approvals, the payload contract must expand additively instead of silently drifting through task-side convenience fields.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids} plus the acceptance rule that upstream actions cannot become work items unless typed payload, target intent, and blocked-state semantics remain explicit.",
        }

    if "audit" in lowered_title or "isolation" in lowered_title or "boundary" in lowered_title:
        return {
            "context": f"`{case_name}` is multi-actor and boundary-scoped. Cross-boundary access, privileged reads, and review/work-item mutations all become release-blocking if they rely on implicit trust rather than an auditable policy edge.",
            "decision": f"Route every sensitive read or mutation through an explicit boundary policy check anchored by {service_scope}. Fail closed on mismatch, and force audit visibility on work-item mutation, review closure, and privileged boundary reads instead of permitting convenience bypasses.",
            "alternatives": [
                (
                    "check roles only inside individual controllers",
                    "is lighter to code, but produces uneven enforcement, weaker audit closure, and a higher chance of boundary leakage when new endpoints or background flows appear.",
                ),
                (
                    "permit an internal-admin bypass for first-wave speed",
                    "reduces short-term friction, but raises compliance and trust risk immediately because the product then depends on operator discipline rather than enforceable policy contracts.",
                ),
            ],
            "consequences": {
                "positive": "The first-wave design keeps boundary, policy, and audit edges explicit across API, review, and work flows instead of treating them as implementation trivia.",
                "negative": "There is more upfront policy and audit ceremony, and local development must preserve deny-path and break-glass scenarios rather than only happy-path flows.",
                "risks": "Provider-specific auth posture may still change later, so the policy contract must survive vendor swaps without breaking boundary claims, session boundaries, or audit correlation.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the deny-path acceptance criteria, and the requirement that audit-sensitive edges remain explicit before Phase-3 implementation starts.",
        }

    if title in {
        "Use asynchronous observation completion events with idempotent replay",
        DEFAULT_GENERIC_ASYNC_COMPLETION_ADR_TITLE,
    }:
        async_pack = async_completion_runtime_pack_for_title(title)
        return {
            "context": (
                f"{async_pack['context_surface_label']} are the first likely burst surfaces in `{case_name}`. "
                "They are slower and less predictable than simple reads, and they risk duplicate writes if the "
                "system treats completion as a one-shot synchronous mutation."
            ),
            "decision": (
                f"Use asynchronous completion events with idempotent replay anchored by {service_scope}. "
                "Completion can finish outside the request path, but the "
                f"{async_pack['completion_identity_label']} and replay identity must remain stable so "
                f"{async_pack['completion_result_label']} twice under retry or delayed processing."
            ),
            "alternatives": [
                (
                    async_pack["sync_alternative_name"],
                    async_pack["sync_alternative_reason"],
                ),
                (
                    "fire-and-forget completion without replay identity",
                    "reduces queue discipline, but increases duplicate registration risk and makes later audit or recovery more fragile when completion is retried.",
                ),
            ],
            "consequences": {
                "positive": async_pack["positive_consequence"],
                "negative": "Operators need explicit queued/running/completed semantics, and implementation must preserve event identity instead of relying on opaque background jobs.",
                "risks": "If queue depth or completion latency exceeds the current p95 budget, the system may need stronger scheduling or physical decomposition in a later release.",
            },
            "evidence": (
                f"Bound to Phase-1 trace ids {ids}, {async_pack['evidence_chain_label']}, and the explicit "
                f"requirement to keep {async_pack['replay_target_label']} replayable under retry or delayed processing."
            ),
        }

    if title == "Keep review-bound truth explicit instead of narrative readiness upgrades":
        return {
            "context": f"The review surface in `{case_name}` closes the loop, but upstream evidence may stay weak, contradictory, or still under validation. If review output upgrades uncertain signals into certainty, the product becomes operationally dangerous even if the workflow looks complete.",
            "decision": f"Keep review-bound truth explicit in {service_scope}. Require uncertainty level, note, and continue-or-revise posture to survive into review closure, and forbid narrative upgrades that turn review-bound evidence into false production confidence.",
            "alternatives": [
                (
                    "summarize weak evidence as a clean business-ready verdict",
                    "reads better in demos, but increases decision risk because operators can no longer see where the closure package still depends on weak or missing proof.",
                ),
                (
                    "leave uncertainty only in analyst notes outside the main report",
                    "reduces UI clutter, but makes review outcomes less traceable and easier to misread when downstream teams consume the closure without the side notes.",
                ),
            ],
            "consequences": {
                "positive": "The first-wave review package remains honest about weak evidence and therefore safer for operators, business owners, and the next architecture decisions taken during release planning.",
                "negative": "Closure language is less polished and may feel less sales-friendly because it preserves uncertainty and review-bound qualifiers in the mainline artifact.",
                "risks": "If future teams optimize for presentation over truth preservation, they may try to remove uncertainty semantics unless the contract and acceptance surfaces keep them mandatory.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the review uncertainty acceptance criteria, and the explicit rule that downstream must not silently upgrade review-bound truth.",
        }

    if title == "Standardize response envelope and business/system error split":
        return {
            "context": f"`{case_name}` spans validation failures, permission denials, conflicts, timeouts, and external-runtime uncertainty. If each endpoint invents its own response and error shape, callers cannot reason consistently about retry, operator action, or audit correlation.",
            "decision": f"Standardize a single response envelope and a business_error versus system_error split anchored by {service_scope}. Every endpoint keeps trace_id, caller-action semantics, and stable machine-readable error_code behavior instead of bespoke per-surface payloads.",
            "alternatives": [
                (
                    "allow each endpoint to define its own ad hoc response shape",
                    "gives local flexibility, but increases client complexity, weakens replay tooling, and makes cross-surface error handling materially less deterministic.",
                ),
                (
                    "rely on HTTP status only with minimal body detail",
                    "is lighter at first glance, but loses retry guidance, domain-specific conflict meaning, and traceable caller action for review-critical workflows.",
                ),
            ],
            "consequences": {
                "positive": "Implementation and testing can reuse one consistent envelope across first-wave reads, writes, and negative paths, which improves traceability and contract tooling.",
                "negative": "Teams must conform to the shared shape, so hyper-local response optimizations become slower than they would in a free-form API style.",
                "risks": "If provider or background-job surfaces later need richer metadata, the envelope must expand additively instead of branching into multiple incompatible error contracts.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the contract-first API posture, and the requirement that callers can distinguish validation, permission, conflict, and system timeout outcomes deterministically.",
        }

    if title == "Use cursor-based pagination and indexed access patterns for growth surfaces":
        return {
            "context": f"Audit trails, findings, task boards, and historical review surfaces all grow over time in `{case_name}`. Offset pagination looks simpler early on, but becomes less stable under concurrent writes and makes audit or replay views harder to reason about.",
            "decision": f"Use cursor-based pagination and indexed access paths for growth surfaces anchored by {service_scope}. Keep tenant_id, status, updated_at, and cycle-aligned predicates explicit now so first-wave read patterns do not force a later contract rewrite.",
            "alternatives": [
                (
                    "use offset-based pagination everywhere",
                    "is simpler for prototypes, but weaker under concurrent writes, less stable for audit history, and more likely to produce duplicate or skipped rows across large result sets.",
                ),
                (
                    "avoid explicit index posture until implementation tuning",
                    "saves design time, but increases the risk of late-stage schema churn when task, finding, or audit growth surfaces begin missing the p95 latency target.",
                ),
            ],
            "consequences": {
                "positive": "First-wave task, finding, and audit surfaces have a stable read contract that can scale from day one without changing page semantics under write pressure.",
                "negative": "The design package must state index and cursor rules earlier than a throwaway prototype usually would, which adds up-front specificity.",
                "risks": "If access patterns shift materially after real usage, the index strategy still needs profiling and may require additive indexes or archival adjustments in a later release.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the 365d hot-retention assumption, and the requirement that growth surfaces stay reviewable without unstable offset paging.",
        }

    if title == "Reserve attribution and external-identity concerns as explicit extension seams":
        return {
            "context": f"`{case_name}` already hints at attribution and external identity needs, but the Phase-1 package does not yet justify a provider-specific commitment. The dominant constraint is avoiding silent omission while also avoiding fake precision.",
            "decision": f"Reserve attribution and external-identity concerns as explicit extension seams connected to {service_scope}. Keep named ports, seam fields, and re-entry hooks visible in Phase-2, but do not claim provider-ready posture before Stage-02.5 is activated by a real dependency commitment.",
            "alternatives": [
                (
                    "drop attribution and identity seams until later",
                    "reduces document size, but creates higher migration cost later because downstream contracts and object chains no longer preserve where those concerns must reconnect.",
                ),
                (
                    "freeze a named provider and callback posture immediately",
                    "looks more concrete, but would overfit the first-wave design to evidence the PRD does not yet provide and would risk false certainty about auth or attribution runtime behavior.",
                ),
            ],
            "consequences": {
                "positive": "The first-wave package stays honest while preserving extension points that Phase-3 can consume without rewriting public contracts if identity or attribution becomes mandatory within the next 2 releases.",
                "negative": "Some readers will see more deferred seams in the Phase-2 design because the package prefers explicit placeholders, named ports, and review-bound fields over pretending provider posture is already closed.",
                "risks": "If a concrete provider becomes MVP-critical before Stage-02.5 is reopened, teams may hard-code vendor choices, timeout budgets, and callback shapes that miss the p95 latency target and break the replaceable-seam contract.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the deferred attribution seam requirement, and the rule that external-identity posture must remain explicit instead of silently hidden in implementation assumptions.",
        }

    if title == DEFAULT_GENERIC_EXTENSION_SEAM_ADR_TITLE or ("seam" in lowered_title and "extension" in lowered_title):
        return {
            "context": f"`{case_name}` may need later-wave connectors, provider bindings, or deferred capabilities, but the current Phase-1 evidence does not justify freezing a vendor-specific runtime posture. The dominant constraint is to keep the reconnection points explicit without inventing false readiness.",
            "decision": f"Reserve deferred extension and external dependency concerns as explicit seams connected to {service_scope}. Keep named ports, seam fields, and re-entry hooks visible in Phase-2, but do not claim provider-ready posture before a real dependency commitment or Stage-02.5 activation exists.",
            "alternatives": [
                (
                    "drop extension seams until implementation discovers them",
                    "reduces document size, but shifts structural truth into hidden implementation choices and raises the cost of reconnecting contracts later.",
                ),
                (
                    "freeze a provider-specific design immediately",
                    "looks more concrete, but overfits the current package to evidence the PRD does not yet provide and risks false certainty about runtime behavior.",
                ),
            ],
            "consequences": {
                "positive": "The first-wave package stays honest while preserving extension points that later phases can consume without rewriting public contracts if external dependencies become mandatory.",
                "negative": "Readers will see more explicit placeholder seams because the package prefers named ports and review-bound honesty over pretending those dependencies are already closed.",
                "risks": "If a concrete dependency becomes MVP-critical before the seam is reopened deliberately, teams may hard-code vendor choices or callback shapes that break the replaceable-seam contract.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the deferred extension boundary carried forward from the PRD, and the rule that missing provider truth must remain explicit instead of silently disappearing.",
        }

    if title == "Separate contract-facing namespaces from internal storage layout":
        return {
            "context": f"The public API and handoff contracts in `{case_name}` need to stay stable longer than any one storage or indexing strategy. If contract names mirror table layout too closely, later storage refactors become visible API churn.",
            "decision": f"Separate contract-facing namespaces from internal storage layout, using {service_scope} as the reference for stable public naming while allowing internal tables, indexes, and denormalized read structures to evolve behind the contract boundary.",
            "alternatives": [
                (
                    "name contracts directly after current table structures",
                    "is straightforward initially, but increases API drift risk once storage optimization, archival, or read-model reshaping changes table ownership or join strategy.",
                ),
                (
                    "hide namespaces entirely and rely on prose-only naming",
                    "reduces visible ceremony, but weakens traceability because downstream implementation and review surfaces lose a stable contract namespace to bind against.",
                ),
            ],
            "consequences": {
                "positive": "Public boundaries remain stable through first-wave implementation even if relational schema, indexing, or read-model layout becomes more specialized under real load.",
                "negative": "Engineers must maintain an explicit mapping between contract names and storage structures rather than treating one as an alias of the other.",
                "risks": "If namespace discipline slips in Phase-3, storage-driven renames may leak into APIs and break traceability across replay, review, and implementation handoff.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the object-chain continuity requirement, and the expectation that storage optimization should not rename public contracts midstream.",
        }

    if title == "Carry work-package and RBI chain into implementation intake unchanged":
        return {
            "context": f"The current `{case_name}` pack is implementation-planning-ready, not runtime-proven. If work-package and RBI relationships are flattened into generic todos before Phase-3 starts, unresolved truth and delivery sequence become much harder to govern.",
            "decision": f"Carry work-package ordering and RBI ownership into implementation intake unchanged, with {service_scope} and related handoff artifacts preserving blockers, replay hooks, and closure rules exactly as they were decided in Phase-2.",
            "alternatives": [
                (
                    "convert the handoff into a loose backlog without RBI bindings",
                    "is easier for local planning, but loses blocker semantics, reduces traceability, and makes it too easy to start slices in an order that invalidates the design rationale.",
                ),
                (
                    "recompute work packages during implementation kickoff",
                    "can feel more flexible, but creates avoidable churn because the same sequencing and risk questions must then be rediscovered after Phase-2 already answered them.",
                ),
            ],
            "consequences": {
                "positive": "Phase-3 onboarding starts with stable sequencing, blocker ownership, and replay evidence instead of a rewritten backlog that drops unresolved truth.",
                "negative": "Implementation intake becomes more structured and may feel heavier than a simple engineering TODO list in the first few days.",
                "risks": "If teams bypass the preserved RBI chain, they may mark slices done while still relying on unclosed runtime proofs or human sign-off assumptions.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the implementation-intake handoff rule, and the requirement that review-bound or runtime-bound items stay explicit during downstream planning.",
        }

    return {
        "context": f"Phase-1 PRD for `{case_name}` requires this architecture decision to remain explicit across Stage-03 contracts, Stage-04 handoff, and first-wave implementation intake.",
        "decision": f"Use {service_scope} as the stable boundary anchor for this decision, and preserve the closing constraint instead of allowing local implementation convenience to redefine it later.",
        "alternatives": [
            (
                "collapse the concern into local implementation heuristics",
                "is faster short term, but weaker for traceability, replay, and downstream review because the decision no longer has a visible contract anchor.",
            ),
            (
                "defer the concern until implementation discovers it organically",
                "saves design time now, but raises later migration, coordination, and consistency risk once multiple slices depend on the same unresolved choice.",
            ),
        ],
        "consequences": {
            "positive": "The first-wave package keeps this choice visible to design, implementation, and review surfaces instead of hiding it in code comments or local assumptions.",
            "negative": "The design pack becomes more explicit and therefore slightly heavier than a thin architecture summary would be.",
            "risks": "If runtime evidence later changes the dominant constraint, the boundary must evolve additively instead of silently changing semantics mid-release.",
        },
        "evidence": f"Bound to Phase-1 trace ids {ids} and the requirement that downstream artifacts can explain why this decision exists without reverse-engineering implementation code.",
    }


def table_owner_for_name(context: dict[str, object], root_namespace: str, table_name: str) -> str:
    semantic_owner = semantic_table_owner(table_name, root_namespace)
    if semantic_owner:
        return semantic_owner
    modules = require_context_modules(context)
    for module in modules:
        if table_name in {to_snake(item) for item in module_core_objects(module)}:
            return infer_home_namespace(root_namespace, module)
    return f"{root_namespace}.unassigned"


def table_owner_for_object(
    context: dict[str, object],
    root_namespace: str,
    obj: str,
    table_name: str,
    services: list[ServiceSpec],
) -> str:
    semantic_owner = semantic_table_owner(table_name, root_namespace)
    if semantic_owner:
        return semantic_owner
    service_owner = owning_service_for_object(obj, services).home_module if services else ""
    if service_owner and "review.bound.technical" not in service_owner:
        return service_owner
    return table_owner_for_name(context, root_namespace, table_name)


def build_table_specs(
    context: dict[str, object],
    root_namespace: str,
    complexity_profile: str,
    services: list[ServiceSpec],
) -> list[dict[str, object]]:
    require_context_modules(context)
    core_objects = phase3_executable_business_objects(
        context,
        [str(item) for item in context.get("core_objects", []) if str(item).strip()],
    )
    supplemental_objects = phase3_executable_business_objects(
        context,
        [str(item) for item in context.get("supplemental_objects", []) if str(item).strip()],
    )
    selected_objects = unique_preserve(
        core_objects
        + phase3_executable_business_objects(
            context,
            [service.owns_or_coordinates for service in services if object_requires_persistent_table(service.owns_or_coordinates)],
        )
    )
    preferred = unique_preserve(selected_objects + supplemental_objects)
    profile = normalized_complexity_profile(complexity_profile)
    if profile == "micro":
        expansion_budget = 1
    elif profile == "standard":
        expansion_budget = len(supplemental_objects)
    else:
        expansion_budget = len(supplemental_objects)
    desired = max(
        profile_minimum(complexity_profile, "stage_03_schema_tables"),
        min(len(preferred), len(selected_objects) + expansion_budget),
    )

    specs: list[dict[str, object]] = []
    for obj in preferred:
        technical_name = context_technical_name(context, obj)
        technical_slug = context_technical_slug(context, obj)
        if not technical_name_can_enter_phase3_surface(technical_name, technical_slug):
            continue
        table_name = semantic_table_name(technical_name)
        if table_name in {spec["table_name"] for spec in specs}:
            continue
        owner = table_owner_for_object(context, root_namespace, obj, table_name, services)
        if owner.endswith(".unassigned"):
            owner = owning_service_for_object(obj, services).home_module
        design = table_design_template(table_name)

        specs.append(
            {
                "object_name": obj,
                "technical_name": technical_name,
                "table_name": table_name,
                "owner": owner,
                "pk": design["pk"],
                "fk": design["fk"],
                "unique_constraints": design["unique_constraints"],
                "composite_indexes": design["composite_indexes"],
                "pii_level": design["pii_level"],
                "sensitive_fields": design["sensitive_fields"],
                "masking_or_encryption": design["masking_or_encryption"],
                "retention_rule": design["retention_rule"],
                "audit_access_rule": design["audit_access_rule"],
                "compliance_note": design["compliance_note"],
                "field_rows": design["field_rows"],
            }
        )
        if len(specs) >= desired:
            break
    return specs


def distribute_phase1_ids(rows: list[str], bucket_count: int) -> list[list[str]]:
    buckets = round_robin_chunks(rows, bucket_count)
    return [bucket if bucket else [rows[idx % len(rows)]] for idx, bucket in enumerate(buckets)] if rows else buckets


def build_stage_03_endpoint_specs(
    services: list[ServiceSpec],
    *,
    root_namespace: str,
    table_specs: list[dict[str, object]] | None = None,
) -> list[ServiceSpec]:
    endpoint_specs = [*services]
    existing_objects = {
        token
        for service in services
        for token in (to_snake(service.owns_or_coordinates), to_snake(service_technical_name(service)))
        if token
    }
    existing_endpoints = {
        (service.endpoint_name, service.method, service.path)
        for service in endpoint_specs
    }

    def append_endpoint(spec: ServiceSpec) -> None:
        key = (spec.endpoint_name, spec.method, spec.path)
        if key in existing_endpoints:
            return
        existing_endpoints.add(key)
        endpoint_specs.append(spec)

    for service in services:
        technical_name = service_technical_name(service)
        entity_slug = service_technical_slug(service)
        if not technical_name_can_enter_phase3_surface(technical_name, entity_slug):
            continue
        append_endpoint(
            ServiceSpec(
                f"{technical_name}StatusService",
                service.domain,
                service.home_module,
                "transactional",
                service.owns_or_coordinates,
                f"Update{technical_name}Status",
                f"{technical_name}StatusChanged",
                f"Apply bounded state updates for {service.owns_or_coordinates}.",
                service.public_contract,
                f"Update{technical_name}Status",
                "PATCH",
                f"/api/v1/{pluralize_slug(entity_slug)}/{{id}}",
                technical_name=technical_name,
                technical_slug=entity_slug,
            )
        )
        append_endpoint(
            ServiceSpec(
                f"{technical_name}QueryService",
                service.domain,
                f"{service.home_module}.query",
                "read-assembly",
                service.owns_or_coordinates,
                f"List{to_pascal(pluralize_slug(entity_slug).replace('-', ' '))}",
                "none",
                f"Expose list and query surfaces for {service.owns_or_coordinates}.",
                f"{service.home_module}.{technical_name}List",
                f"List{to_pascal(pluralize_slug(entity_slug).replace('-', ' '))}",
                "GET",
                f"/api/v1/{pluralize_slug(entity_slug)}",
                technical_name=technical_name,
                technical_slug=entity_slug,
            )
        )
    if table_specs:
        for spec in table_specs:
            object_name = str(spec.get("object_name", "")).strip()
            if not object_name:
                continue
            object_key = to_snake(object_name)
            if not object_key or object_key in existing_objects:
                continue
            owner = owning_service_for_object(object_name, services)
            technical_name = str(spec.get("technical_name") or service_technical_name(owner)).strip()
            entity_slug = str(spec.get("technical_slug") or choose_technical_slug(technical_name, prefix="entity")).strip()
            if not technical_name_can_enter_phase3_surface(technical_name, entity_slug):
                continue
            public_contract = f"{owner.domain}.{technical_name}"
            append_endpoint(
                ServiceSpec(
                    f"{technical_name}StatusService",
                    owner.domain,
                    owner.home_module,
                    "transactional",
                    object_name,
                    f"Update{technical_name}Status",
                    f"{technical_name}StatusChanged",
                    f"Apply bounded state updates for {object_name}.",
                    public_contract,
                    f"Update{technical_name}Status",
                    "PATCH",
                    f"/api/v1/{pluralize_slug(entity_slug)}/{{id}}",
                    technical_name=technical_name,
                    technical_slug=entity_slug,
                )
            )
            append_endpoint(
                ServiceSpec(
                    f"{technical_name}QueryService",
                    owner.domain,
                    f"{owner.home_module}.query",
                    "read-assembly",
                    object_name,
                    f"List{to_pascal(pluralize_slug(entity_slug).replace('-', ' '))}",
                    "none",
                    f"Expose list and query surfaces for {object_name}.",
                    f"{owner.home_module}.{technical_name}List",
                    f"List{to_pascal(pluralize_slug(entity_slug).replace('-', ' '))}",
                    "GET",
                    f"/api/v1/{pluralize_slug(entity_slug)}",
                    technical_name=technical_name,
                    technical_slug=entity_slug,
                )
            )
            existing_objects.add(object_key)
    if len(services) > 1:
        anchor = services[0]
        append_endpoint(
            ServiceSpec(
                "AggregateReadService",
                anchor.domain,
                f"{root_namespace}.aggregate.read",
                "read-assembly",
                "Cross-module summary",
                "ListCrossModuleSummaries",
                "none",
                "Expose cross-module read surfaces when multiple service boundaries participate in one workflow.",
                f"{root_namespace}.aggregate.CrossModuleSummary",
                "ListCrossModuleSummaries",
                "GET",
                "/api/v1/cross-module-summaries",
            )
        )
    return endpoint_specs


def _sample_request_example_value(field_name: str) -> object:
    return projected_sample_request_example_value(field_name)


def _set_nested_request_example_path(example: dict[str, object], target_path: str, value: object) -> None:
    set_projected_nested_request_example_path(example, target_path, value)


def build_request_mapping_lookup(binding_rows: list[list[str]]) -> dict[tuple[str, str], list[str]]:
    lookup: dict[tuple[str, str], list[str]] = {}
    for row in binding_rows:
        if len(row) < 9:
            continue
        path = str(row[6]).strip()
        method = str(row[7]).strip().upper()
        mapping_text = str(row[8]).strip()
        if not path or not method or not mapping_text or mapping_text.startswith("review-bound"):
            continue
        key = (path, method)
        lookup.setdefault(key, []).append(mapping_text)
    return lookup


def enrich_request_example_with_request_mappings(
    example: dict[str, object],
    service: ServiceSpec,
    request_mapping_lookup: dict[tuple[str, str], list[str]] | None = None,
) -> dict[str, object]:
    return enrich_projected_request_example_with_request_mappings(
        example,
        service_projection_spec(service),
        request_mapping_lookup=request_mapping_lookup,
    )


def stage_03_request_example(
    service: ServiceSpec,
    request_mapping_lookup: dict[tuple[str, str], list[str]] | None = None,
) -> dict[str, object]:
    return projected_request_example(
        service_projection_spec(service),
        request_mapping_lookup=request_mapping_lookup,
    )


def stage_03_response_example(service: ServiceSpec) -> dict[str, object]:
    return projected_response_example(service_projection_spec(service))


def stage_03_contract_schema_fields(
    service: ServiceSpec,
    request_mapping_lookup: dict[tuple[str, str], list[str]] | None = None,
) -> list[str]:
    return projected_contract_schema_fields(
        service_projection_spec(service),
        request_mapping_lookup=request_mapping_lookup,
    )


def build_object_profile(service: ServiceSpec, obj_name: str) -> dict[str, str]:
    technical_name = service_technical_name(service)
    object_key = to_snake(technical_name)
    event_name = event_name_for_model(service, obj_name)
    state_map = {
        "transactional": "created / active / completed / archived",
        "orchestration": "queued / running / completed / archived",
        "read-assembly": "prepared / refreshed / stale / archived",
        "policy": "draft / active / restricted / archived",
        "domain": "draft / active / revised / archived",
        "support": "recorded / confirmed / exported / archived",
    }
    aggregate_kind = {
        "transactional": "aggregate-root",
        "orchestration": "aggregate-root",
        "read-assembly": "read-model",
        "policy": "aggregate-root",
        "domain": "aggregate-root",
        "support": "support-entity",
    }.get(service.service_type, "aggregate-root")
    return {
        "aggregate_kind": aggregate_kind,
        "primary_states": state_map.get(service.service_type, "draft / active / archived"),
        "authoritative_mutations": f"{service.primary_inbound}, update {object_key}, archive {object_key}",
        "emitted_events": event_name,
        "failure_guardrail": f"{obj_name} 的变更必须收敛在 `{service.service_name}` 内，并保留可追溯证据。",
        "mutation_guard": f"只有 `{service.service_name}` 可以权威修改 `{object_key}`；下游模块只能按契约读取。",
        "collaborators": f"{event_source_path_for_model(service, obj_name)}，并保留 review / audit 可见面。",
        "read_only_refs": f"{service.public_contract}, {service.endpoint_name}, version anchors",
        "must_not_write": "所有非 owner 模块",
        "conflict_rule": f"对 `{object_key}` 的版本化写入必须拒绝过期更新",
        "change_propagation_path": f"{service.service_name} -> public contract -> 下游读取与 review 面",
        "must_not_own": "相邻模块的权威对象",
        "public_boundary_status": "active / contract-bound",
    }


def build_ownership_profile(obj_name: str, services: list[ServiceSpec], owner: ServiceSpec) -> dict[str, str]:
    technical_name = service_technical_name(owner)
    obj_key = to_snake(technical_name)
    read_consumers = [
        service.service_name
        for service in services
        if service.service_name != owner.service_name
        and (
            obj_key in to_snake(service.owns_or_coordinates)
            or obj_key in to_snake(service_technical_name(service))
            or obj_key in to_snake(service.purpose)
            or service.service_type == "read-assembly"
        )
    ]
    propagated_by = event_name_for_model(owner, obj_name)
    return {
        "read_consumers": ", ".join(read_consumers) if read_consumers else "downstream read surfaces",
        "change_propagation_path": f"{owner.service_name} -> {propagated_by} -> 下游读取与 review 面",
        "forbidden_shortcut": f"不得绕过 `{owner.service_name}` 从其他模块或表耦合捷径直接写 `{obj_key}`。",
        "closure_note": f"`{obj_name}` 继续由 `{owner.service_name}` 持有权威写入，其余位置只读消费。",
    }


def generic_endpoint_policy(service: ServiceSpec) -> list[str]:
    rate_limit = {
        "transactional": "20 req/min per tenant",
        "orchestration": "10 req/min per workflow boundary",
        "read-assembly": "60 req/min per tenant",
        "policy": "120 req/min per subject",
        "domain": "30 req/min per tenant",
        "support": "24 req/min per tenant",
    }.get(service.service_type, "30 req/min")
    pagination = "cursor-based for list endpoints" if service.endpoint_name.startswith("List") else "none"
    response_profile = f"{service.method} `{service.endpoint_name}` returns a contract-bound response for `{service.owns_or_coordinates}`."
    retryability = "safe to retry on system_error with the same idempotency anchor when applicable"
    idempotency = "naturally idempotent read" if service.method == "GET" else f"{to_snake(service_technical_name(service))} id or caller token"
    failure_codes = "400 invalid_request; 403 forbidden; 404 not_found; 409 version_conflict; 503 dependency_unavailable"
    return [rate_limit, pagination, response_profile, retryability, idempotency, failure_codes]


def _primary_req_id(upstream_trace_ids: list[str]) -> str:
    for prefix in ("P1-REQ-", "P1-AC-", "P1-UC-", "P1-US-", "P1-EP-"):
        for trace_id in upstream_trace_ids:
            if trace_id.startswith(prefix):
                return trace_id
    return upstream_trace_ids[0] if upstream_trace_ids else "P1-REQ-TBD"


def choose_service_match_for_interaction(
    interaction: dict[str, str],
    page_row: dict[str, str],
    endpoint_specs: list[ServiceSpec],
) -> InteractionServiceMatch:
    if not endpoint_specs:
        return InteractionServiceMatch(
            service=None,
            score=0,
            semantic_overlap=0,
            has_object_overlap=False,
            method_match=False,
            blocked_reason="no endpoint specs available for interaction-level binding",
        )
    preferred_method = "GET" if str(interaction.get("trigger_kind", "")).strip() == "page_load" else "POST"
    business_objects = split_inline_values(page_row.get("business_objects", ""))
    page_name = str(page_row.get("page_name", "")).strip()
    page_blueprint_type = normalize_blueprint_type(str(page_row.get("page_blueprint_type", "")).strip())
    goal_focus_tokens = semantic_focus_tokens(
        " ".join(
            [
                str(page_row.get("primary_user_goal", "")).strip(),
                str(page_row.get("primary_action", "")).strip(),
            ]
        )
    )
    interaction_blob = " ".join(
        [
            interaction.get("interaction_id", ""),
            interaction.get("region", ""),
            interaction.get("element_type", ""),
            interaction.get("interaction_pattern", ""),
            interaction.get("action_type", ""),
            interaction.get("user_intent", ""),
            page_row.get("page_name", ""),
            page_row.get("primary_user_goal", ""),
            " ".join(business_objects),
        ]
    )
    tokens = semantic_tokens(interaction_blob)
    page_name_tokens = semantic_tokens(page_name)
    interaction_region = str(interaction.get("region", "")).strip().lower()
    action_type = str(interaction.get("action_type", "")).strip().lower()
    scored: list[InteractionServiceMatch] = []
    for service in endpoint_specs:
        score = 0
        method_match = service.method == preferred_method
        if method_match:
            score += 5
        service_blob = " ".join(
            [
                service.service_name,
                service.domain,
                service.home_module,
                service.owns_or_coordinates,
                service.purpose,
                service.endpoint_name,
                service.path,
            ]
        )
        service_tokens = semantic_tokens(service_blob)
        semantic_overlap = len(tokens & service_tokens)
        score += semantic_overlap
        goal_overlap = len(goal_focus_tokens & service_tokens)
        score += goal_overlap * 2
        module_overlap = len(page_name_tokens & semantic_tokens(service.home_module))
        score += module_overlap * 2
        page_name_key = to_snake(page_name)
        home_module_key = to_snake(service.home_module)
        if page_name_key and home_module_key and (page_name_key in home_module_key or home_module_key in page_name_key):
            score += 4
        has_object_overlap = bool(
            business_objects
            and any(
                to_snake(obj) in to_snake(service.owns_or_coordinates)
                or to_snake(obj) in to_snake(service_technical_name(service))
                for obj in business_objects
            )
        )
        if has_object_overlap:
            score += 4
        if action_type == "load_context" and service.service_type == "read-assembly":
            score += 3
            if interaction_region == "context_header" and {"summary", "overview"} & service_tokens:
                score += 2
            if interaction_region == "context_header" and page_blueprint_type == "review-decision" and {"review", "workflow"} & service_tokens:
                score += 2
            if interaction_region == "data_view" and page_blueprint_type == "review-decision" and "workflow" in service_tokens and {"review", "summary", "closure"} & service_tokens:
                score += 1
        if service.method != preferred_method and preferred_method == "POST" and service.method == "PATCH":
            score += 1
        scored.append(
            InteractionServiceMatch(
                service=service,
                score=score,
                semantic_overlap=semantic_overlap,
                has_object_overlap=has_object_overlap,
                method_match=method_match,
            )
        )
    scored.sort(
        key=lambda item: (
            -item.score,
            -int(item.has_object_overlap),
            -item.semantic_overlap,
            item.service.service_name if item.service else "",
        )
    )
    best = scored[0]
    next_score = scored[1].score if len(scored) > 1 else -999
    strong_enough = (
        best.has_object_overlap
        or best.semantic_overlap >= 2
        or (best.method_match and best.semantic_overlap >= 1 and best.score >= 8)
    )
    clearly_better = len(scored) == 1 or best.has_object_overlap or (best.score - next_score) >= 2
    if strong_enough and clearly_better and best.service is not None:
        return best
    return InteractionServiceMatch(
        service=None,
        score=best.score,
        semantic_overlap=best.semantic_overlap,
        has_object_overlap=best.has_object_overlap,
        method_match=best.method_match,
        blocked_reason=(
            "insufficient service-binding confidence: no explicit business-object overlap or stable semantic lead"
        ),
    )


def choose_service_for_interaction(
    interaction: dict[str, str],
    page_row: dict[str, str],
    endpoint_specs: list[ServiceSpec],
) -> ServiceSpec | None:
    return choose_service_match_for_interaction(interaction, page_row, endpoint_specs).service


def binding_mode_for_interaction(interaction: dict[str, str]) -> str:
    trigger_kind = str(interaction.get("trigger_kind", "")).strip()
    action_type = str(interaction.get("action_type", "")).strip().lower()
    if trigger_kind == "page_load" or action_type == "load_context":
        return "read"
    if action_type in {"record_payment", "submit", "approve"}:
        return "read_write"
    return "write"


def display_field_set_for_page(page_row: dict[str, str], interaction: dict[str, str]) -> list[str]:
    business_objects = phase3_surface_safe_labels(split_inline_values(page_row.get("business_objects", "")))
    region = str(interaction.get("region", "")).strip()
    suffix = "summary" if region in {"context_header", "data_view"} else "fields"
    if business_objects:
        return [f"{to_camel(obj)}{suffix[:1].upper() + suffix[1:]}" for obj in business_objects[:3]]
    return ["pageContextSummary"] if region in {"context_header", "data_view"} else ["primaryActionFields"]


def label_can_enter_phase3_surface(label: str) -> bool:
    return technical_name_can_enter_phase3_surface(
        choose_technical_pascal(label, prefix="Entity"),
        choose_technical_slug(label, prefix="entity"),
    )


def phase3_surface_safe_labels(values: list[str]) -> list[str]:
    return [value for value in values if label_can_enter_phase3_surface(value)]


def _safe_schema_slug(raw: str, fallback: str) -> str:
    slug = choose_technical_slug(raw, prefix="entity").replace("-", "_")
    if slug and technical_name_can_enter_phase3_surface("", slug):
        return slug
    fallback_slug = choose_technical_slug(fallback, prefix="entity").replace("-", "_")
    if fallback_slug and technical_name_can_enter_phase3_surface("", fallback_slug):
        return fallback_slug
    return "primary_action"


def input_schema_ref_for_interaction(page_row: dict[str, str], interaction: dict[str, str]) -> str:
    if str(interaction.get("trigger_kind", "")).strip() == "page_load":
        return "—"
    page_slug = _safe_schema_slug(str(page_row.get("page_name", "")).strip(), "primary action")
    action_slug = _safe_schema_slug(str(interaction.get("action_type", "")).strip() or "action", "action")
    return f"{page_slug}_{action_slug}_form"


def validation_rules_for_interaction(interaction: dict[str, str]) -> str:
    if str(interaction.get("trigger_kind", "")).strip() == "page_load":
        return "not_applicable"
    action_type = str(interaction.get("action_type", "")).strip() or "action"
    return f"require-valid-{slugify(action_type)}-input; preserve-blocked-rule-before-submit"


def enabled_rule_for_interaction(interaction: dict[str, str]) -> str:
    if str(interaction.get("trigger_kind", "")).strip() == "page_load":
        return "not_applicable"
    blocked_rule = str(interaction.get("blocked_rule", "")).strip()
    if blocked_rule in {"—", "-", "none", "n/a"}:
        blocked_rule = ""
    if blocked_rule:
        return f"enabled_when_not({blocked_rule})"
    return "enabled_when_visibility_rule_passes"


def _flatten_request_example_paths(value: object, *, prefix: str = "request") -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for key, subvalue in value.items():
            current = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(subvalue, dict):
                paths.extend(_flatten_request_example_paths(subvalue, prefix=current))
            elif isinstance(subvalue, list) and subvalue and isinstance(subvalue[0], dict):
                paths.extend(_flatten_request_example_paths(subvalue[0], prefix=current))
            else:
                paths.append(current)
        return paths
    return [prefix] if prefix else []


def _expand_field_hint_phrases(value: str) -> list[str]:
    cleaned = re.sub(r"^depends on\s+", "", str(value or "").strip(), flags=re.IGNORECASE)
    if not cleaned:
        return []
    segments = [segment.strip() for segment in re.split(r"[;,]", cleaned) if segment.strip()]
    phrases: list[str] = []
    for segment in segments:
        if "/" not in segment:
            phrases.append(segment)
            continue
        parts = [part.strip() for part in segment.split("/") if part.strip()]
        if not parts:
            continue
        phrases.append(parts[0])
        first_words = parts[0].split()
        prefix_words = first_words[:-1]
        for part in parts[1:]:
            if " " in part or not prefix_words:
                phrases.append(part)
            else:
                phrases.append(" ".join([*prefix_words, part]))
    return phrases


def _field_name_from_hint(value: str) -> str:
    cleaned = re.sub(r"^depends on\s+", "", str(value or "").strip(), flags=re.IGNORECASE)
    if not cleaned:
        return ""
    if len(cleaned.split()) > 6 and not re.search(r"(?:^|[^A-Za-z0-9])(id|_id)(?:[^A-Za-z0-9]|$)", cleaned, flags=re.IGNORECASE):
        return ""
    stopwords = {
        "a",
        "an",
        "and",
        "or",
        "the",
        "current",
        "required",
        "minimum",
        "workflow",
        "business",
        "record",
        "module",
        "explicit",
        "complete",
        "completed",
        "ownership",
        "payload",
        "signals",
        "history",
        "rules",
        "ready",
    }
    tokens = [
        token
        for token in re.split(r"[^A-Za-z0-9]+", cleaned)
        if token and token.lower() not in stopwords
    ]
    if not tokens:
        return ""
    candidate = to_camel(" ".join(tokens))
    if len(candidate) <= 1:
        return ""
    return candidate


def _page_input_field_hints(page_row: dict[str, str]) -> list[str]:
    hints: list[str] = []
    for raw in (
        str(page_row.get("entry_conditions", "")).strip(),
        str(page_row.get("entry_condition", "")).strip(),
    ):
        if not raw:
            continue
        lowered = raw.lower()
        if not any(token in raw for token in (",", "/", ";")) and not re.search(r"(?:^|[^A-Za-z0-9])(?:[A-Za-z0-9_]*id)(?:[^A-Za-z0-9]|$)", lowered):
            continue
        for phrase in _expand_field_hint_phrases(raw):
            normalized = _field_name_from_hint(phrase)
            if normalized:
                hints.append(normalized)
    return unique_preserve(hints)


def _mapping_alias_for_request_path(path: str) -> str:
    normalized = str(path or "").strip()
    if normalized.startswith("request."):
        normalized = normalized[len("request.") :]
    if normalized.startswith("query."):
        normalized = normalized[len("query.") :]
    if normalized.startswith("input."):
        normalized = normalized[len("input.") :]
    return to_camel(normalized.replace(".", " "))


def _service_request_mappings_for_interaction(page_row: dict[str, str], service: ServiceSpec) -> list[str]:
    request_example = stage_03_request_example(service)
    example_paths = _flatten_request_example_paths(request_example, prefix="request")
    if not example_paths:
        return []
    page_field_hints = _page_input_field_hints(page_row)
    hint_paths: list[str] = []
    if any(path.startswith("request.input.") for path in example_paths) and page_field_hints:
        for hint in page_field_hints:
            target = f"request.{hint}" if hint.endswith("Id") else f"request.input.{hint}"
            hint_paths.append(target)
    effective_paths = [
        path
        for path in example_paths
        if path != "request.input.summary" or not hint_paths
    ] + hint_paths
    mappings: list[str] = []
    seen_targets: set[str] = set()
    for path in effective_paths:
        target = str(path).strip()
        if not target or target in seen_targets:
            continue
        seen_targets.add(target)
        alias = _mapping_alias_for_request_path(target)
        if not alias:
            continue
        mappings.append(f"{alias} -> {target}")
    return mappings


def request_field_mapping_for_interaction(
    page_row: dict[str, str],
    interaction: dict[str, str],
    service: ServiceSpec | None = None,
) -> str:
    if str(interaction.get("trigger_kind", "")).strip() == "page_load":
        business_objects = phase3_surface_safe_labels(split_inline_values(page_row.get("business_objects", "")))
        if business_objects:
            object_slug = to_camel(business_objects[0])
            return f"{object_slug}Id -> query.{object_slug}Id"
        return "pageContextId -> query.pageContextId"
    if service is not None:
        service_mappings = _service_request_mappings_for_interaction(page_row, service)
        if service_mappings:
            return "; ".join(service_mappings)
    input_schema_ref = input_schema_ref_for_interaction(page_row, interaction)
    field_prefix = input_schema_ref.replace("_form", "")
    return f"{field_prefix}.summary -> request.input.summary"


def response_field_mapping_for_interaction(page_row: dict[str, str], interaction: dict[str, str]) -> str:
    fields = display_field_set_for_page(page_row, interaction)
    if not fields:
        return "response.status -> ui.status"
    return "; ".join(f"response.{to_camel(field)} -> ui.{field}" for field in fields[:3])


def _mapping_field_names(mapping_text: str, *, right_hand: bool = False) -> list[str]:
    names: list[str] = []
    for raw_entry in str(mapping_text or "").split(";"):
        entry = raw_entry.strip().strip("`")
        if not entry:
            continue
        left, _, right = entry.partition("->")
        candidate = right if right_hand else left
        normalized = str(candidate).strip()
        if not normalized:
            continue
        field = normalized.split(".")[-1].replace("[]", "").strip()
        if field and field not in names and field not in {"request", "response", "query", "ui", "input"}:
            names.append(field)
    return names


def _resource_id_candidates(api_path: str) -> set[str]:
    segments = [
        segment
        for segment in str(api_path).split("/")
        if segment
        and segment not in {"api"}
        and not re.fullmatch(r"v\d+", segment)
        and not segment.startswith("{")
    ]
    if not segments:
        return set()
    resource_token = segments[-1].rstrip("s")
    camel = to_camel(resource_token.replace("-", " "))
    candidates = {
        f"{camel}Id" if camel else "",
        f"{resource_token}_id" if resource_token else "",
    }
    return {candidate for candidate in candidates if candidate}


def _normalize_contract_enum(value: str) -> str:
    cleaned = str(value or "").strip().lower()
    if not cleaned or cleaned in {"—", "-", "none", "n/a"}:
        return ""
    return re.sub(r"[\s-]+", "_", cleaned)


def _interaction_internal_exposure(page_row: dict[str, str]) -> str:
    audience_mode = _normalize_contract_enum(page_row.get("audience_mode", ""))
    page_name = str(page_row.get("page_name", "")).strip().lower()
    blueprint = normalize_blueprint_type(str(page_row.get("page_blueprint_type", "")).strip())
    if audience_mode and audience_mode != "app":
        return "review_only"
    if "review" in page_name or blueprint == "review-decision":
        return "review_only"
    return "user_visible"


def _handoff_materialization(
    *,
    page_row: dict[str, str],
    interaction: dict[str, str],
    flow_row: dict[str, str],
) -> str:
    has_handoff = any(
        str(item or "").strip()
        for item in (
            interaction.get("next_route", ""),
            flow_row.get("next_page_id", ""),
            flow_row.get("visible_next_page_id", ""),
            flow_row.get("handoff_context_fields", ""),
            flow_row.get("handoff_surface_type", ""),
        )
    )
    if not has_handoff:
        return ""
    handoff_visibility = _normalize_contract_enum(page_row.get("handoff_visibility", ""))
    if handoff_visibility in {"implicit_context", "user_visible_summary", "review_only"}:
        return handoff_visibility
    handoff_surface_type = _normalize_contract_enum(flow_row.get("handoff_surface_type", ""))
    if handoff_surface_type == "review_queue":
        return "review_only"
    if handoff_surface_type in {"hidden_transition", "same_role_continue", "next_role_workspace"}:
        return "implicit_context"
    if _normalize_contract_enum(page_row.get("audience_mode", "")) not in {"", "app"}:
        return "review_only"
    return "user_visible_summary"


def _ui_refresh_targets(
    *,
    page_row: dict[str, str],
    interaction: dict[str, str],
    response_field_mapping: str,
    has_handoff: bool,
    binding_mode: str,
) -> str:
    if binding_mode not in {"write", "read_write"}:
        return ""
    targets: list[str] = []
    interaction_region = str(interaction.get("region", "")).strip()
    if interaction_region:
        targets.append(interaction_region)
    required_regions = split_inline_values(page_row.get("required_regions", ""))
    if "status_feedback" in required_regions or str(interaction.get("success_state", "")).strip():
        targets.append("status_feedback")
    if has_handoff or "next_steps" in required_regions:
        targets.append("next_steps")
    for field in _mapping_field_names(response_field_mapping, right_hand=True):
        targets.append(f"projection:{field}")
    return ", ".join(unique_preserve(targets))


def _value_source_contract(
    *,
    interaction: dict[str, str],
    input_fields: list[str],
    server_generated_fields: list[str],
    flow_row: dict[str, str],
) -> str:
    if not input_fields and not server_generated_fields:
        return ""
    flow_context_fields = {
        field
        for field in split_inline_values(flow_row.get("handoff_context_fields", ""))
        if field
    }
    entries: list[str] = []
    for field in unique_preserve(input_fields + server_generated_fields):
        value_source = "user_input"
        if field in server_generated_fields:
            value_source = "system_generated"
        elif str(interaction.get("trigger_kind", "")).strip() == "page_load" or field in flow_context_fields:
            value_source = "workflow_context"
        entries.append(f"{field}={value_source}")
    return "; ".join(entries)


def rbac_policy_for_page(page_row: dict[str, str]) -> str:
    roles = split_inline_values(page_row.get("allowed_roles", "")) or [page_row.get("primary_actor", "TBD")]
    return ", ".join(role for role in roles if role) or "TBD"


def audit_event_for_interaction(interaction: dict[str, str]) -> str:
    return slugify(str(interaction.get("interaction_id", "")).replace(".", "_")) or "interaction_event"


def build_binding_and_trace_rows(
    *,
    phase1_page_map: list[dict[str, str]],
    phase1_interactions: list[dict[str, str]],
    phase1_flow_rows: list[dict[str, str]] | None = None,
    endpoint_specs: list[ServiceSpec],
    trace_rows: list[dict[str, str]],
) -> tuple[list[list[str]], list[list[str]], list[list[str]]]:
    page_by_id = {
        str(row.get("page_id", "")).strip(): row
        for row in phase1_page_map
        if str(row.get("page_id", "")).strip()
    }
    flow_by_interaction = {
        str(row.get("from_interaction_id", "")).strip(): row
        for row in (phase1_flow_rows or [])
        if str(row.get("from_interaction_id", "")).strip()
    }
    req_ids = [
        row["trace_id"]
        for row in trace_rows
        if row.get("unit_type") in {"requirement", "acceptance-criteria"}
    ] or [row["trace_id"] for row in trace_rows]
    req_groups = distribute_phase1_ids(req_ids, max(len(phase1_interactions), 1)) if req_ids else []

    binding_rows: list[list[str]] = []
    enrichment_rows: list[list[str]] = []
    traceability_rows: list[list[str]] = []
    for idx, interaction in enumerate(phase1_interactions, start=1):
        page_id = str(interaction.get("page_id", "")).strip()
        page_row = page_by_id.get(page_id, {})
        flow_row = flow_by_interaction.get(str(interaction.get("interaction_id", "")).strip(), {})
        service_match = choose_service_match_for_interaction(interaction, page_row, endpoint_specs)
        service = service_match.service
        binding_mode = binding_mode_for_interaction(interaction)
        service_binding_id = (
            f"{interaction['interaction_id']}.{slugify(service.endpoint_name)}"
            if service is not None
            else f"{interaction['interaction_id']}.unresolved-service-binding"
        )
        display_field_set = ", ".join(display_field_set_for_page(page_row, interaction))
        input_schema_ref = input_schema_ref_for_interaction(page_row, interaction)
        validation_rules = validation_rules_for_interaction(interaction)
        enabled_rule = enabled_rule_for_interaction(interaction)
        request_field_mapping = request_field_mapping_for_interaction(page_row, interaction, service)
        response_field_mapping = response_field_mapping_for_interaction(page_row, interaction)
        input_fields = _mapping_field_names(request_field_mapping)
        server_generated_fields = [
            field
            for field in input_fields
            if service is not None and service.method.upper() == "POST" and field in _resource_id_candidates(service.path)
        ]
        handoff_materialization = _handoff_materialization(
            page_row=page_row,
            interaction=interaction,
            flow_row=flow_row,
        )
        ui_refresh_targets = _ui_refresh_targets(
            page_row=page_row,
            interaction=interaction,
            response_field_mapping=response_field_mapping,
            has_handoff=bool(handoff_materialization),
            binding_mode=binding_mode,
        )
        internal_exposure = _interaction_internal_exposure(page_row)
        value_source_contract = _value_source_contract(
            interaction=interaction,
            input_fields=input_fields,
            server_generated_fields=server_generated_fields,
            flow_row=flow_row,
        )
        readiness_status = str(interaction.get("readiness_status", "review-bound")).strip() or "review-bound"
        blocked_reason = str(interaction.get("blocked_reason", "")).strip()
        if blocked_reason in {"—", "-", "none", "n/a"}:
            blocked_reason = ""
        if binding_mode == "read" and not blocked_reason and input_schema_ref == "—":
            blocked_reason = ""
        if readiness_status == "ready" and not str(interaction.get("use_case_id", "")).strip():
            readiness_status = "review-bound"
            blocked_reason = blocked_reason or "missing use_case_id for interaction-level binding"
        if service is None:
            readiness_status = "review-bound"
            blocked_reason = blocked_reason or service_match.blocked_reason or "service binding requires human review"
        binding_rows.append(
            [
                service_binding_id,
                interaction["interaction_id"],
                interaction.get("use_case_id", "TBD") or "TBD",
                "",
                binding_mode,
                service.service_name if service is not None else "UNRESOLVED_SERVICE_BINDING",
                service.path if service is not None else "—",
                service.method if service is not None else "—",
                request_field_mapping if service is not None else "review-bound / unresolved-service-binding",
                response_field_mapping if service is not None else "review-bound / unresolved-service-binding",
                service.owns_or_coordinates if service is not None else "—",
                rbac_policy_for_page(page_row),
                audit_event_for_interaction(interaction),
                generic_endpoint_policy(service)[-1] if service is not None else "—",
                ", ".join(server_generated_fields) or "—",
                ui_refresh_targets or "—",
                handoff_materialization or "—",
                readiness_status,
                blocked_reason or "—",
            ]
        )
        enrichment_rows.append(
            [
                interaction["interaction_id"],
                page_id,
                input_schema_ref,
                display_field_set,
                validation_rules,
                enabled_rule,
                value_source_contract or "—",
                internal_exposure,
                interaction.get("error_state", "TBD") or "TBD",
                readiness_status,
                blocked_reason or "—",
            ]
        )
        upstream_req_ids = req_groups[idx - 1] if idx - 1 < len(req_groups) else (req_groups[-1] if req_groups else ["P1-REQ-TBD"])
        primary_req_id = _primary_req_id(upstream_req_ids)
        traceability_rows.append(
            [
                f"trace.{slugify(interaction['interaction_id'])}",
                primary_req_id,
                interaction.get("use_case_id", "TBD") or "TBD",
                page_id or "TBD",
                interaction["interaction_id"],
                service_binding_id,
                service.path if service is not None else "—",
                "phase3-contract-tests, phase4-closure",
                "phase3-productness-gate",
                str(page_row.get("canonical_page_id", "")).strip() or "—",
                _normalize_contract_enum(page_row.get("audience_mode", "")) or "—",
                internal_exposure,
                "current",
                ", ".join(upstream_req_ids),
            ]
        )
    return binding_rows, enrichment_rows, traceability_rows


def service_event_name(service: ServiceSpec) -> str:
    return service.primary_outbound or f"{service_technical_name(service)}Changed"


def event_subject_for_model(service: ServiceSpec | None, obj: str) -> str:
    candidate = str(obj or "").strip()
    if candidate and label_can_enter_phase3_surface(candidate):
        return candidate
    if service is not None:
        return service.owns_or_coordinates or service_technical_name(service)
    return "Source Evidence"


def event_subject_pascal(service: ServiceSpec, obj: str) -> str:
    return to_pascal(event_subject_for_model(service, obj))


def event_name_for_model(service: ServiceSpec, obj: str) -> str:
    subject = event_subject_for_model(service, obj)
    if to_snake(subject) == to_snake(service.owns_or_coordinates):
        return service_event_name(service)
    suffix = "Prepared" if service.service_type == "read-assembly" else "Recorded" if service.service_type == "support" else "Changed"
    return f"{to_pascal(subject)}{suffix}"


def event_trigger_for_model(service: ServiceSpec, obj: str) -> str:
    subject_label = event_subject_for_model(service, obj)
    if to_snake(subject_label) == to_snake(service.owns_or_coordinates):
        return f"{service.primary_inbound} succeeds for {subject_label}"
    subject = to_pascal(subject_label)
    if service.service_type == "read-assembly":
        return f"{subject} read context is confirmed for downstream projection"
    if service.service_type == "support":
        return f"{subject} record is appended after support/audit workflow commits"
    obj_key = to_snake(obj)
    if "revision" in obj_key or "cycle" in obj_key or "conclusion" in obj_key:
        return f"{subject} lifecycle changes after review/state boundary is committed"
    return f"{subject} lifecycle changes after {service.service_name} commits authoritative state"


def event_model_effect_for_model(service: ServiceSpec, obj: str) -> str:
    subject = event_subject_pascal(service, obj)
    if service.service_type == "read-assembly":
        return f"{subject} read projection must be visible through `{service.public_contract}` without write authority"
    if service.service_type == "support":
        return f"{subject} append/replay effect must be visible through `{service.public_contract}`"
    return f"{subject} lifecycle and read-effect must be visible through `{service.public_contract}`"


def event_p3_handoff_for_model(service: ServiceSpec, obj: str) -> str:
    event_name = event_name_for_model(service, obj)
    subject = event_subject_pascal(service, obj)
    if service.service_type == "read-assembly":
        return f"bind `{event_name}` to read projection service/repository/unit intent for `{subject}`; validate payload/idempotency evidence before implementation closure"
    if service.service_type == "support":
        return f"bind `{event_name}` to append/replay service/repository/unit intent for `{subject}`; validate payload/idempotency evidence before implementation closure"
    return f"bind `{event_name}` to lifecycle service/repository/unit intent for `{subject}`; validate payload/idempotency evidence before implementation closure"


def event_source_path_for_model(service: ServiceSpec, obj: str) -> str:
    event_name = event_name_for_model(service, obj)
    subject = event_subject_for_model(service, obj)
    if to_snake(subject) == to_snake(service.owns_or_coordinates):
        return (
            f"入口由 `{service.primary_inbound}` 触发，"
            f"`{service.service_name}` 提交 `{subject}` 权威状态后经 `{event_name}` 向下游传播"
        )
    return f"由 `{service.service_name}` 提交 `{subject}` 权威状态后经 `{event_name}` 向下游传播"


def event_reliability_posture_for_model(service: ServiceSpec, obj: str) -> str:
    subject = event_subject_for_model(service, obj)
    payload = event_payload_contract(subject, service)
    idempotency = f"dedupe on {to_snake(subject)}_id + version"
    if service.service_type == "read-assembly":
        commit_boundary = "read context confirmation before projection handoff"
        replay = f"read projection consumers preserve source trace_id and {idempotency}"
    elif service.service_type == "support":
        commit_boundary = "append-only audit/support record commit"
        replay = f"append/replay consumers preserve event identity and {idempotency}"
    else:
        commit_boundary = "authoritative owner write commit before fan-out"
        replay = f"lifecycle consumers preserve version ordering and {idempotency}"
    return (
        f"commit boundary: {commit_boundary}; "
        f"required payload ids: {payload}; "
        f"idempotency/replay: {replay}; "
        "claim ceiling: missing commit or payload evidence remains review-bound until P3 runtime/test proof; "
        "P3 validation hook: assert payload ids, idempotency, and event effect before implementation closure"
    )


def event_model_business_meaning(service: ServiceSpec, obj: str) -> str:
    action = "读取上下文已稳定" if service.service_type == "read-assembly" else "权威状态已变更"
    subject = event_subject_for_model(service, obj)
    return f"`{subject}` 的{action}，下游只能消费该事实或请求新版本，不能回写事件来源。"


def event_payload_contract(obj: str, service: ServiceSpec | None = None) -> str:
    snake = to_snake(event_subject_for_model(service, obj))
    return f"{snake}_id, tenant_id, version, trace_id, changed_at"


def event_schema_posture(service: ServiceSpec, obj: str | None = None) -> str:
    if obj:
        return event_reliability_posture_for_model(service, obj)
    if service.service_type in {"orchestration", "support"}:
        return "versioned envelope + additive payload fields; replay identity is mandatory"
    if service.service_type == "read-assembly":
        return "read-model event aliases may be additive; source event name remains stable"
    return "stable event name + additive payload; removing identifiers requires returning to P2"


def event_downstream_usage_rule(service: ServiceSpec) -> str:
    if service.service_type == "read-assembly":
        return "P3 may build projection/read tests from this event, but must not treat it as write authority"
    return "P3 must bind service/repository/unit behavior to this event before claiming implementation closure"


def event_driver_rows(
    *,
    services: list[ServiceSpec],
    aggregate_objects: list[str],
    event_target: int,
) -> tuple[list[list[str]], list[list[str]], list[list[str]], list[list[str]]]:
    event_objects = aggregate_objects[:event_target] if aggregate_objects else [
        service.owns_or_coordinates for service in services[:event_target]
    ]
    events: list[list[str]] = []
    vocabulary_rows: list[list[str]] = []
    model_rows: list[list[str]] = []
    carry_forward_rows: list[list[str]] = []
    for idx, obj in enumerate(event_objects):
        service = owning_service_for_object(obj, services)
        subject = event_subject_for_model(service, obj)
        event_name = event_name_for_model(service, obj)
        consumer = (
            owning_service_for_object(event_objects[idx + 1], services).service_name
            if idx + 1 < len(event_objects)
            else "downstream review surfaces"
        )
        trigger = event_trigger_for_model(service, obj)
        payload = event_payload_contract(subject, service)
        ordering = "after authoritative write" if service.service_type != "read-assembly" else "after source context read is confirmed"
        idempotency = f"dedupe on {to_snake(subject)}_id + version"
        events.append([event_name, service.service_name, consumer, trigger, payload, ordering, idempotency])
        vocabulary_rows.append(
            [
                event_name,
                event_model_business_meaning(service, obj),
                service.service_name,
                consumer,
                payload,
                ordering,
                idempotency,
                event_downstream_usage_rule(service),
            ]
        )
        model_rows.append(
            [
                f"EVT-{idx + 1:02d}",
                event_name,
                trigger,
                f"{service.service_name} -> {consumer}",
                event_model_effect_for_model(service, obj),
                event_schema_posture(service, obj),
                event_p3_handoff_for_model(service, obj),
                "resolved",
            ]
        )
        carry_forward_rows.append(
            [
                event_name,
                event_p3_handoff_for_model(service, obj),
                event_name,
                "事件名与 P3 touchpoint 直接沿用 Stage-02 event model driver 的对象级语义",
            ]
        )
    return events, vocabulary_rows, model_rows, carry_forward_rows


def owning_service_for_object(obj_name: str, services: list[ServiceSpec]) -> ServiceSpec:
    obj_key = to_snake(obj_name)
    if not services:
        raise SystemExit("rendering requires at least one ServiceSpec")
    exact = next(
        (
            service
            for service in services
            if to_snake(service.owns_or_coordinates) == obj_key
            or to_snake(service_technical_name(service)) == obj_key
        ),
        None,
    )
    if exact:
        return exact
    partial = next(
        (
            service
            for service in services
            if obj_key in to_snake(service.owns_or_coordinates)
            or to_snake(service.owns_or_coordinates) in obj_key
            or obj_key in to_snake(service_technical_name(service))
            or to_snake(service_technical_name(service)) in obj_key
        ),
        None,
    )
    if partial:
        return partial
    semantic = next(
        (
            service
            for service in services
            if obj_key in to_snake(service.purpose) or obj_key in to_snake(service.public_contract)
        ),
        None,
    )
    return semantic or services[0]


def grouped_service_pairs(services: list[ServiceSpec]) -> list[tuple[ServiceSpec, ServiceSpec]]:
    if len(services) < 2:
        return []
    return [(services[idx], services[idx + 1]) for idx in range(len(services) - 1)]


__all__ = [name for name in globals() if not name.startswith("__")]
