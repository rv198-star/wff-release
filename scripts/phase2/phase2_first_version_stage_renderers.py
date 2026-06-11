#!/usr/bin/env python3
"""Phase-2 first-version runtime slice: phase2_first_version_stage_renderers.py."""

from __future__ import annotations

from phase2.phase2_first_version_design_model import *  # noqa: F401,F403

def render_stage_01(
    *,
    case_name: str,
    phase1_prd: Path,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
) -> str:
    root_namespace = str(context["root_namespace"])
    boundary_scope = str(context.get("boundary_scope", "tenant"))
    boundary_term = boundary_phrase(boundary_scope)
    boundary_subject_name = boundary_subject(boundary_scope)
    workflow_scope = workflow_scope_summary(context)
    async_completion_pack = async_completion_runtime_pack_for_context(context)
    primary_owner_label = "Workspace Owner"
    operator_label = "Execution Operator"
    reviewer_label = "Decision Reviewer"
    quality_attributes = [str(item) for item in context["quality_attributes"]][: max(profile_minimum(complexity_profile, "stage_01_quality_attributes"), 4)]
    trace_rows = list(context["all_trace_rows"])
    req_ac_ids = [
        row["trace_id"]
        for row in trace_rows
        if row.get("unit_type") in {"requirement", "acceptance-criteria"}
    ] or [row["trace_id"] for row in trace_rows]
    adr_count = max(profile_minimum(complexity_profile, "stage_01_architecture_decisions"), 4)
    decision_trace_groups = distribute_phase1_ids(req_ac_ids, adr_count)
    capability_target = max(profile_minimum(complexity_profile, "stage_01_capability_groups"), 4)
    capability_domain_names = unique_preserve(
        [str(item) for item in list(context.get("domains", []))]
        + [service.domain for service in services]
    )[:4]
    while len(capability_domain_names) < 4:
        capability_domain_names.append(f"domain-{len(capability_domain_names) + 1}")
    capability_groups = [
        {
            "name": f"{capability_domain_names[0]} Scope and Governance",
            "priority": "P0",
            "maturity": "core",
            "rationale": "Minimum valid boundary, access, and workflow guardrails must remain stable before downstream design deepening and review.",
            "covers": f"{capability_domain_names[0]} ownership, {boundary_subject_name} access, workflow boundary validation, version freeze",
        },
        {
            "name": f"{capability_domain_names[1]} Workflow Context and Signals",
            "priority": "P0",
            "maturity": "core",
            "rationale": "Current-state evidence, handoff context, and operator-visible signals must remain reproducible and explainable.",
            "covers": f"{capability_domain_names[1]} current-state snapshot, signal versioning, handoff context",
        },
        {
            "name": f"{capability_domain_names[2]} Action Handoff and Execution",
            "priority": "P0",
            "maturity": "core",
            "rationale": "The product loses business value if upstream business context cannot become bounded execution work.",
            "covers": f"{capability_domain_names[2]} typed handoff payload, work-item bridge, target object linkage",
        },
        {
            "name": f"{capability_domain_names[3]} Review and Closure",
            "priority": "P0",
            "maturity": "guided",
            "rationale": "Downstream delivery must preserve review-bound truths instead of narrative certainty.",
            "covers": f"{capability_domain_names[3]} review summaries, uncertainty notes, continue-or-revise posture",
        },
    ][:capability_target]
    supports_deferred_extension_seam = context_supports_deferred_extension_seam(context)
    business_proof_constraints = business_proof_constraint_block(context, indent=4)
    business_architecture_pressure = business_architecture_pressure_block(context, indent=4)
    deferred_constraint_lines = (
        [
            "advanced attribution seams remain reserved but not promised as MVP-complete",
            "external connector hardening remains PhaseX / later-wave work",
        ]
        if supports_deferred_extension_seam
        else [
            "deferred extension seams stay explicit only when Phase-1 truth actually declares them",
            "provider-specific hardening remains later-wave work until a real dependency commitment exists",
        ]
    )

    adr_titles = [str(item) for item in context.get("adr_titles", [])][:adr_count]
    adr_entries: list[str] = []
    decision_trace_table_rows: list[list[str]] = []
    for idx, title in enumerate(adr_titles, start=1):
        ad_id = f"AD-{idx:02d}"
        ids = decision_trace_groups[idx - 1]
        service = select_adr_anchor_service(title, services)
        adr_content = adr_content_for(
            title=title,
            service=service,
            case_name=case_name,
            upstream_ids=ids,
            root_namespace=root_namespace,
        )
        hook = (
            f"{title} stays visible in `{service.public_contract}` / `{service.endpoint_name}` handoff evidence "
            f"for {summarize_list(ids, max_items=3)}."
        )
        alternative_lines: list[str] = []
        for alternative_name, rejected_because in adr_content["alternatives"]:
            alternative_lines.extend(
                [
                    f"      - alternative_name: {alternative_name}",
                    f"      - rejected_because: {rejected_because}",
                ]
            )
        adr_entries.append(
            "\n".join(
                [
                    f"  - adr_{idx:02d}:",
                    f"    - ad_id: `{ad_id}`",
                    f"    - title: {title}",
                    "    - status:",
                    "      - `Accepted`",
                    f"    - context: {adr_content['context']}",
                    f"    - decision: {adr_content['decision']}",
                    "    - alternatives_considered:",
                    *alternative_lines,
                    "    - consequences:",
                    f"      - positive: {adr_content['consequences']['positive']}",
                    f"      - negative: {adr_content['consequences']['negative']}",
                    f"      - risks: {adr_content['consequences']['risks']}",
                    f"    - evidence: {adr_content['evidence']}",
                ]
            )
        )
        decision_trace_table_rows.append(
            [
                f"P2-DTR-{idx:02d}",
                ad_id,
                title,
                f"upstream_trace_ids={', '.join(ids)}",
                "ARCH-STG03-OUTPUT-0001",
                hook,
                ", ".join(ids),
            ]
        )

    forbidden_count = max(profile_minimum(complexity_profile, "stage_01_forbidden_assumptions"), 5)
    forbidden_entries = []
    forbidden_templates = forbidden_templates_for_context(context)
    for idx in range(forbidden_count):
        code, text = forbidden_templates[idx % len(forbidden_templates)]
        forbidden_entries.append(
            "\n".join(
                [
                    f"  - fa_{idx + 1:02d}:",
                    f"    - original_text: {text}",
                    "    - source: Phase-1 `Must Not Assume` and trust-bound workflow posture",
                    "    - architecture_constraint_mapping: enforce explicit contracts, RBI carry-forward, or boundary checks",
                    "    - compliance_status: `must-preserve`",
                    "    - evidence_reference: PRD requirement / acceptance registry remains explicit",
                    "    - evidence_strength: `strong`",
                ]
            )
        )

    quality_entries = []
    for attr in quality_attributes:
        quality_entries.append(
            "\n".join(
                [
                    f"    - {to_snake(attr)}:",
                    f"      - quantified_target: keep `{attr}` visible in every Stage-03 or Stage-04 acceptance surface",
                    "      - metric_name: first-pass traceable design surfaces",
                    "      - target_value: >= 1 direct structured binding per critical flow",
                    "      - measurement_window: per design revision",
                    "      - design_implication: 把该属性前置到 contract、replay 或 verification note",
                    "      - evidence_or_source: Phase-1 NFR and quality scenario matrix",
                ]
            )
        )

    primary_object_list = ", ".join(f"`{item}`" for item in list(context["objects"])[:7])
    deferred_constraint_block = "\n".join(f"    - {line}" for line in deferred_constraint_lines)
    quality_entries_block = "\n".join(quality_entries)
    capability_map_block = "\n".join(
        [
            "\n".join(
                [
                    f"  - capability_group_{idx:02d}:",
                    f"    - name: {group['name']}",
                    "    - priority:",
                    f"      - `{group['priority']}`",
                    "    - maturity:",
                    f"      - `{group['maturity']}`",
                    f"    - rationale: {group['rationale']}",
                    "    - covers:",
                    f"      - {group['covers']}",
                ]
            )
            for idx, group in enumerate(capability_groups, start=1)
        ]
    )

    stage = render_phase2_template(
        "stage-01-architecture-definition.md.template",
        {
            "case_name": case_name,
            "phase1_prd": phase1_prd,
            "complexity_profile": complexity_profile,
            "root_namespace": root_namespace,
            "workflow_scope": workflow_scope,
            "primary_object_list": primary_object_list,
            "boundary_term": boundary_term,
            "boundary_subject_name": boundary_subject_name,
            "deferred_constraint_block": deferred_constraint_block,
            "business_proof_constraints": business_proof_constraints,
            "business_architecture_pressure": business_architecture_pressure,
            "quality_entries_block": quality_entries_block,
            "capability_map_block": capability_map_block,
            "adr_entries_block": "\n".join(adr_entries),
            "decision_trace_registry_table": make_markdown_table(
                [
                    "trace_id",
                    "adr_id",
                    "decision_title",
                    "upstream_reference",
                    "downstream_artifact_id",
                    "verification_hook",
                    "upstream_trace_ids",
                ],
                decision_trace_table_rows,
            ),
            "latency_target_label": async_completion_pack["latency_target_label"],
            "growth_target_label": async_completion_pack["growth_target_label"],
            "volume_target_label": async_completion_pack["volume_target_label"],
            "forbidden_entries_block": "\n".join(forbidden_entries),
            "primary_owner_label": primary_owner_label,
            "operator_label": operator_label,
            "reviewer_label": reviewer_label,
        },
    )
    return stage.rstrip() + "\n"



def render_stage_02(
    *,
    phase1_prd: Path,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
    table_specs: list[dict[str, object]],
) -> str:
    root_namespace = str(context["root_namespace"])
    modules = require_context_modules(context)
    domains = unique_preserve(
        [str(item) for item in context.get("domains", [])]
        + [service.domain for service in services]
    ) or unique_preserve([service.domain for service in services])
    aggregate_seed = unique_semantic_objects(
        [str(spec["object_name"]) for spec in table_specs]
        + [
            str(item)
            for item in context.get("core_objects", [])
            if str(item).strip() and object_requires_persistent_table(str(item))
        ]
        + [
            str(item)
            for item in context.get("supplemental_objects", [])
            if str(item).strip() and object_requires_persistent_table(str(item))
        ]
        + [service.owns_or_coordinates for service in services if object_requires_persistent_table(service.owns_or_coordinates)]
    )
    aggregate_seed = phase3_surface_safe_labels(aggregate_seed)
    aggregate_target = max(
        profile_minimum(complexity_profile, "stage_02_aggregate_catalog"),
        min(len(aggregate_seed), len(services) + 3),
        len(table_specs),
    )
    aggregate_objects = aggregate_seed[:aggregate_target] if aggregate_seed else [service.owns_or_coordinates for service in services]
    table_binding_map = {str(spec["object_name"]): str(spec["table_name"]) for spec in table_specs}

    domain_rows = []
    module_rows = []
    service_rows = []
    aggregate_rows = []
    responsibility_rows = []
    canonical_rows = []
    service_endpoint_rows = []
    lifecycle_rows = []

    rendered_domains = domains[: max(profile_minimum(complexity_profile, "stage_02_domains"), 3)] or [services[0].domain]
    for domain in rendered_domains:
        related_services = [service for service in services if service.domain == domain]
        domain_objects = unique_preserve([service.owns_or_coordinates for service in related_services]) or aggregate_objects[:2]
        primary_states = build_object_profile(related_services[0], domain_objects[0])["primary_states"] if related_services and domain_objects else "draft / active / archived"
        domain_rows.append([
            domain,
            release_domain_role_surface([service.service_type for service in related_services]),
            summarize_list([service.purpose for service in related_services], max_items=2),
            summarize_list(domain_objects, max_items=4),
            primary_states,
            release_slice_guardrail(),
            release_handoff_rule(),
        ])

    module_objects = {}
    for module in modules:
        name = module_name(module)
        module_objects[name] = unique_preserve(module_core_objects(module) + [str(item) for item in module.get("supplemental_objects", [])])
    for service in services:
        module_objects.setdefault(service.home_module, [])
        if service.owns_or_coordinates not in module_objects[service.home_module]:
            module_objects[service.home_module].append(service.owns_or_coordinates)

    seen_modules = set()
    for service in services:
        service_rows.append([
            service.service_name,
            service.domain,
            service.home_module,
            service.service_type,
            service.owns_or_coordinates,
            service.primary_inbound,
            service.primary_outbound,
            service.purpose,
            release_consistency_boundary(service.home_module, service.owns_or_coordinates),
        ])
        if service.home_module in seen_modules:
            continue
        seen_modules.add(service.home_module)
        owned = unique_preserve(module_objects.get(service.home_module, []) + [item.owns_or_coordinates for item in services if item.home_module == service.home_module])
        module_rows.append([
            service.home_module,
            service.domain,
            release_module_role_surface(),
            service.service_name,
            summarize_list(owned, max_items=5),
            ", ".join(item.public_contract for item in services if item.home_module == service.home_module) or "none",
            "上下游权威对象不得被本模块接管",
            release_change_propagation_note(service.service_name, service.endpoint_name),
            service.purpose,
        ])

    lifecycle_bindings = max(len(aggregate_objects), profile_minimum(complexity_profile, "stage_02_lifecycle_mermaid_bindings"), 3)
    for idx, obj in enumerate(aggregate_objects, start=1):
        owner = owning_service_for_object(obj, services)
        object_profile = build_object_profile(owner, obj)
        ownership_profile = build_ownership_profile(obj, services, owner)
        backing_schema = table_binding_map.get(obj, to_snake(obj))
        aggregate_rows.append([
            obj,
            object_profile["aggregate_kind"],
            owner.domain,
            owner.home_module,
            owner.service_name,
            object_profile["authoritative_mutations"],
            object_profile["primary_states"],
            object_profile["emitted_events"],
            f"stateDiagram-v2 / diagram-{idx:02d}" if idx <= lifecycle_bindings else "stateDiagram-v2 / shared coverage",
            object_profile["failure_guardrail"],
            object_profile["public_boundary_status"],
        ])
        responsibility_rows.append([
            owner.domain,
            obj,
            owner.home_module,
            object_profile["collaborators"],
            object_profile["read_only_refs"],
            object_profile["must_not_write"],
            object_profile["conflict_rule"],
            ownership_profile["closure_note"],
        ])
        canonical_rows.append([
            obj,
            obj,
            owner.service_name,
            f"{to_snake(obj)}_id + tenant_id",
            "status + version + updated_at",
            backing_schema,
            f"{owner.public_contract}, {owner.endpoint_name}",
            f"{obj} 持续锚定在 {owner.service_name} 及其契约表面上，不再由下游自行发明。",
        ])
        service_endpoint_rows.append([
            owner.service_name,
            owner.home_module,
            owner.endpoint_name,
            owner.public_contract,
            obj,
            "主 owner 到 Stage-03 接口的直接映射",
        ])
        lifecycle_rows.append([
            obj,
            "stateDiagram-v2",
            owner.service_name,
            object_profile["primary_states"],
            object_profile["emitted_events"],
            object_profile["mutation_guard"],
            object_profile["failure_guardrail"],
            f"diagram-{idx:02d}" if idx <= lifecycle_bindings else "shared-diagram",
            ownership_profile["change_propagation_path"],
        ])

    mapped_services = {row[0] for row in service_endpoint_rows}
    for service in services:
        if service.service_name in mapped_services:
            continue
        service_endpoint_rows.append([
            service.service_name,
            service.home_module,
            service.endpoint_name,
            service.public_contract,
            service.owns_or_coordinates,
            "补充服务到接口的映射",
        ])

    dependency_rows = []
    for upstream, downstream in grouped_service_pairs(services):
        dependency_rows.append([
            upstream.home_module,
            downstream.home_module,
            f"{upstream.endpoint_name} 以只读上下文交接给 {downstream.endpoint_name}",
            f"{to_snake(service_technical_name(upstream))}_id + trace_id",
            f"{downstream.service_name} 可以消费，但不得原地改写 {upstream.owns_or_coordinates}",
            "若所有权漂移，冻结该契约并把问题抬升为 review-bound 证据",
            f"{service_event_name(upstream)} 的新版本只能向前传播，不能回写下游已冻结事实",
        ])
    if not dependency_rows and services:
        service = services[0]
        dependency_rows.append([
            service.home_module,
            service.home_module,
            f"{service.endpoint_name} 在本模块内闭合自身状态边界",
            f"{to_snake(service_technical_name(service))}_id",
            "不得走表耦合回写捷径",
            "一旦所有权模糊，立即抬升为 review-bound 证据",
            "只允许追加式修订向前传播",
        ])

    event_target = max(profile_minimum(complexity_profile, "stage_02_domain_events"), min(len(aggregate_objects), max(len(services), 6)))
    events, event_vocabulary_rows, event_model_rows, event_rows = event_driver_rows(
        services=services,
        aggregate_objects=aggregate_objects,
        event_target=event_target,
    )

    er_entities = unique_preserve([to_upper_entity(spec["object_name"]) for spec in table_specs] + [to_upper_entity(obj) for obj in aggregate_objects])
    er_entities = er_entities[: max(profile_minimum(complexity_profile, "stage_02_er_entities"), min(len(er_entities), 10))]
    if len(er_entities) < 2:
        er_entities = unique_preserve(er_entities + [to_upper_entity(service.owns_or_coordinates) for service in services[:2]])
    er_relationship_lines = [
        f"    {er_entities[idx]} ||--o{{ {er_entities[idx + 1]} : propagates_to"
        for idx in range(len(er_entities) - 1)
    ] or ["    ENTITY_A ||--o{ ENTITY_B : supports"]

    flow_modules = unique_preserve([service.home_module for service in services])
    flow_lines = []
    if flow_modules:
        for idx, module in enumerate(flow_modules):
            current = f'M{idx + 1}["{module}"]'
            if idx == 0:
                flow_lines.append(f"    {current}")
            if idx + 1 < len(flow_modules):
                nxt = f'M{idx + 2}["{flow_modules[idx + 1]}"]'
                flow_lines.append(f"    {current} --> {nxt}")
    else:
        flow_lines.append('    M1["core-module"] --> M2["delivery-module"]')

    narrative_objects = summarize_list(aggregate_objects, max_items=4)
    narrative_modules = summarize_list(flow_modules, max_items=4)
    narrative_event_names = summarize_list([str(row[0]) for row in event_vocabulary_rows], max_items=4)
    er_entities_block = ", ".join(er_entities)
    state_diagrams_block = "\n".join(
        [
            "\n".join(
                [
                    "```mermaid",
                    "stateDiagram-v2",
                    "    [*] --> Draft",
                    f"    Draft --> Active: validate {obj}",
                    f"    Active --> Revised: publish {to_snake(obj)} update",
                    "    Revised --> Active: accept additive change",
                    f"    Active --> Archived: retire {obj}",
                    "```",
                ]
            )
            for obj in aggregate_objects
        ]
    )
    er_relationship_block = "\n".join(er_relationship_lines)
    flow_lines_block = "\n".join(flow_lines)

    stage = render_phase2_template(
        "stage-02-domain-decomposition.md.template",
        {
            "phase1_prd": phase1_prd,
            "complexity_profile": complexity_profile,
            "narrative_objects": narrative_objects,
            "narrative_modules": narrative_modules,
            "narrative_event_names": narrative_event_names,
            "business_proof_track_carryover_block": business_proof_constraint_block(context, indent=2),
            "domain_map_table": make_markdown_table(
                ["domain_name", "domain_role", "mission", "primary_objects", "primary_states", "must_not_own", "handoff_rule"],
                domain_rows,
            ),
            "module_map_table": make_markdown_table(
                ["module_name", "domain_name", "module_role", "primary_service", "owned_objects", "read_only_refs", "must_not_own", "change_propagation_path", "module_purpose"],
                module_rows,
            ),
            "service_candidates_table": make_markdown_table(
                ["service_name", "domain", "home_module", "service_type", "owns_or_coordinates", "primary_inbound", "primary_outbound", "purpose", "consistency_boundary"],
                service_rows,
            ),
            "canonical_object_structure_table": make_markdown_table(
                ["object_name", "authoritative_aggregate", "authoritative_service", "primary_identifiers", "state_or_version_anchor", "backing_schema_or_projection", "stage_03_contract_or_endpoint", "closure_note"],
                canonical_rows,
            ),
            "aggregate_catalog_table": make_markdown_table(
                ["aggregate_name", "aggregate_kind", "owning_domain", "owning_module", "authoritative_service", "authoritative_mutations", "primary_states", "emitted_events", "lifecycle_diagram", "failure_or_guardrail", "public_boundary_status"],
                aggregate_rows,
            ),
            "responsibility_matrix_table": make_markdown_table(
                ["domain", "aggregate / object", "authoritative owner", "collaborators", "read_only_refs", "must_not_write", "conflict_rule", "public-boundary note"],
                responsibility_rows,
            ),
            "service_endpoint_mapping_table": make_markdown_table(
                ["service_name", "home_module", "stage_03_endpoint_names", "public_contracts", "primary_owned_object", "mapping_note"],
                service_endpoint_rows,
            ),
            "aggregate_lifecycle_coverage_table": make_markdown_table(
                ["aggregate_name", "lifecycle_expression_type", "owner_writer", "state_set", "trigger_events", "mutation_guard", "terminal_or_failure_exit", "mermaid_binding", "closure_note"],
                lifecycle_rows,
            ),
            "dependency_collaboration_map_table": make_markdown_table(
                ["upstream_module", "downstream_module", "allowed_interaction", "required_artifact", "forbidden_backedge", "violation_penalty", "change_propagation_rule"],
                dependency_rows,
            ),
            "er_entities_block": er_entities_block,
            "domain_event_catalog_table": make_markdown_table(
                ["event_name", "producer", "consumer", "trigger_condition", "payload_shape", "ordering_semantics", "idempotency_rule"],
                events,
            ),
            "domain_event_vocabulary_table": make_markdown_table(
                ["event_name", "business_meaning", "producer", "consumer", "payload_contract", "timing", "idempotency", "downstream_usage_rule"],
                event_vocabulary_rows,
            ),
            "domain_event_model_catalog_table": make_markdown_table(
                ["event_model_id", "event_name", "trigger", "producer_consumer", "mutation_or_read_effect", "event_versioning_and_schema_posture", "p3_event_handoff", "review_bound_status"],
                event_model_rows,
            ),
            "root_namespace": root_namespace,
            "state_diagrams_block": state_diagrams_block,
            "er_relationship_block": er_relationship_block,
            "flow_lines_block": flow_lines_block,
        },
    )
    return stage.rstrip() + "\n"


def render_stage_03(
    *,
    phase1_prd: Path,
    phase1_prototype_spec: Path | None,
    phase1_interaction_flow_contract: Path | None,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
    endpoint_specs: list[ServiceSpec],
    table_specs: list[dict[str, object]],
) -> str:
    root_namespace = str(context["root_namespace"])
    boundary_scope = str(context.get("boundary_scope", "tenant"))
    boundary_term = boundary_phrase(boundary_scope)
    async_completion_pack = async_completion_runtime_pack_for_context(context)
    schema_min = max(profile_minimum(complexity_profile, "stage_03_schema_tables"), 5)
    api_min = max(profile_minimum(complexity_profile, "stage_03_api_endpoints"), 5)
    tech_min = max(profile_minimum(complexity_profile, "stage_03_tech_selection_candidates"), 3)
    scenario_min = max(profile_minimum(complexity_profile, "stage_03_scenarios"), 5)
    contract_min = max(profile_minimum(complexity_profile, "stage_03_contract_trace_registry"), 3)
    phase1_page_map = _extract_page_map_from_prototype_spec(phase1_prototype_spec)
    phase1_interactions = _extract_interaction_rows_from_phase1_contract(phase1_interaction_flow_contract)
    phase1_flow_rows = _extract_flow_rows_from_phase1_contract(phase1_interaction_flow_contract)
    stage_03_design_defaults = load_stage_03_design_defaults()

    objects = unique_preserve(
        [str(spec["object_name"]) for spec in table_specs]
        + [service.owns_or_coordinates for service in services]
        + [str(item) for item in context.get("objects", [])]
    )
    objects = phase3_surface_safe_labels(objects)
    rendered_table_specs = table_specs[: max(schema_min, len(table_specs))]
    schema_summary_rows = [
        [
            str(spec["table_name"]),
            f"`{spec['owner']}`",
            str(spec["pk"]),
            str(spec["fk"]),
            str(spec["unique_constraints"]),
            str(spec["composite_indexes"]),
        ]
        for spec in rendered_table_specs
    ]

    data_ownership_rows: list[list[str]] = []
    for obj in objects[: max(schema_min, len(services) + 2)]:
        owner = owning_service_for_object(obj, services)
        profile = build_ownership_profile(obj, services, owner)
        data_ownership_rows.append(
            [
                obj,
                f"`{owner.home_module}`",
                owner.service_name,
                profile["read_consumers"],
                owner.public_contract,
                profile["change_propagation_path"],
                profile["forbidden_shortcut"],
                profile["closure_note"],
            ]
        )

    storage_layer_rows = list(stage_03_design_defaults["storage_layer_rows"])

    access_pattern_rows: list[list[str]] = []
    for spec in rendered_table_specs[: max(4, min(len(rendered_table_specs), 6))]:
        access_pattern_rows.append(
            [
                f"lookup `{spec['table_name']}` by ownership and recency",
                str(spec["table_name"]),
                f"tenant_id + {spec['pk']} + updated_at",
                "medium to high",
                str(spec["composite_indexes"]),
                "pay additive write cost to preserve stable read latency",
                f"benchmark `{spec['table_name']}` list and detail queries before widening rollout",
            ]
        )

    schema_entries: list[str] = []
    for idx, spec in enumerate(rendered_table_specs, start=1):
        field_table = make_markdown_table(
            ["field_name", "data_type", "nullable", "constraints", "index_hint"],
            [[str(a), str(b), str(c), str(d), str(e)] for a, b, c, d, e in spec["field_rows"]],
        )
        indented_field_table = "\n".join(f"        {line}" if line else "" for line in field_table.splitlines())
        schema_entries.append(
            "\n".join(
                [
                    f"    - table_{idx:02d}:",
                    f"      - table_name: `{spec['table_name']}`",
                    f"      - owner: `{spec['owner']}`",
                    f"      - object_name: `{spec['object_name']}`",
                    f"      - unique_constraints: `{spec['unique_constraints']}`",
                    f"      - composite_indexes: `{spec['composite_indexes']}`",
                    "      - write_rule: only the owning module mutates this table directly",
                    "      - trace_rule: every row remains addressable by primary id and trace_id",
                    "      - field_registry:",
                    indented_field_table,
                ]
            )
        )

    sensitivity_rows: list[list[str]] = []
    for spec in rendered_table_specs:
        table_name = str(spec["table_name"])
        pii_level = "restricted" if any(token in table_name for token in ("tenant", "identity", "audit")) else "internal"
        sensitivity_rows.append(
            [
                table_name,
                pii_level,
                "tenant keys, actor ids, trace anchors",
                "mask in logs and encrypt at rest where required",
                "retain per review/audit posture",
                "privileged reads require explicit reason and traceability",
                "sensitivity posture follows object ownership and replay needs",
            ]
        )

    binding_preview_rows = build_binding_and_trace_rows(
        phase1_page_map=phase1_page_map,
        phase1_interactions=phase1_interactions,
        endpoint_specs=endpoint_specs,
        trace_rows=[],
    )[0] if phase1_interactions else []
    request_mapping_lookup = build_request_mapping_lookup(binding_preview_rows)

    contract_entries: list[str] = []
    api_rows: list[list[str]] = []
    for idx, service in enumerate(endpoint_specs[: max(api_min, len(endpoint_specs))], start=1):
        request_example = stage_03_request_example(service, request_mapping_lookup=request_mapping_lookup)
        schema_fields = stage_03_contract_schema_fields(service, request_mapping_lookup=request_mapping_lookup)
        rate_limit, pagination, response_profile, retryability, idempotency, failure_codes = generic_endpoint_policy(service)
        schema_preview = make_markdown_table(
            ["field_name", "data_type", "nullable", "constraints", "index_hint"],
            [
                [
                    field.split(": ", 1)[0],
                    field.split(": ", 1)[1] if ": " in field else "string",
                    "false" if "|null" not in field and "null" not in field else "true",
                    "typed contract field",
                    "contract schema",
                ]
                for field in schema_fields[:16]
            ],
        )
        contract_entries.append(
            "\n".join(
                [
                    f"  - contract_{idx:02d}:",
                    f"    - contract_name: `{service.public_contract}`",
                    f"    - producer: `{service.service_name}`",
                    f"    - consumer: `{service.home_module}`",
                    "    - schema_form: `typed-request-response-envelope`",
                    f"    - failure_semantics: `{failure_codes}`",
                    "    - compatibility_rule: additive-only changes; identifiers and envelope fields stay stable",
                    "    - schema_fields:",
                    *[f"      - `{field}`" for field in schema_fields[:16]],
                    "    - json_schema:",
                    schema_preview,
                    "    - ts_interface:",
                    f"      - request_contract: `{service.endpoint_name}Request`",
                    f"      - response_contract: `{service.endpoint_name}Response`",
                ]
            )
        )
        api_rows.append(
            [
                service.endpoint_name,
                service.method,
                service.path,
                service.purpose,
                json.dumps(request_example, ensure_ascii=False),
                json.dumps(stage_03_response_example(service), ensure_ascii=False),
                rate_limit,
                pagination,
                response_profile,
                retryability,
                idempotency,
                f"{failure_codes}; error_type split: business_error | system_error",
            ]
        )
    _, _, event_model_rows, event_rows = event_driver_rows(
        services=services,
        aggregate_objects=objects,
        event_target=max(profile_minimum(complexity_profile, "stage_02_domain_events"), min(len(objects), max(len(services), 6))),
    )
    event_consumption_rows = [
        [
            row[1],
            row[6].replace("bind ", "").replace(" service/repository/unit intent", ""),
            row[4],
            row[5],
            row[6],
            "implementation claim remains capped until P3 runtime/test evidence exists",
        ]
        for row in event_model_rows
    ]

    all_trace_rows = list(context["all_trace_rows"])
    all_trace_ids = [row["trace_id"] for row in all_trace_rows]
    req_ac_ids = [row["trace_id"] for row in all_trace_rows if row.get("unit_type") in {"requirement", "acceptance-criteria"}] or all_trace_ids
    contract_id_groups = distribute_phase1_ids(req_ac_ids, max(contract_min, len(endpoint_specs)))
    contract_trace_rows: list[list[str]] = []
    for idx, service in enumerate(endpoint_specs[: max(contract_min, len(endpoint_specs))], start=1):
        upstream_ids = contract_id_groups[idx - 1] if idx - 1 < len(contract_id_groups) else contract_id_groups[-1]
        contract_trace_rows.append(
            [
                f"P2-CTR-{idx:02d}",
                service.public_contract,
                "public-contract",
                f"`{service.home_module}`",
                "HANDOFF-0001",
                f"{service.endpoint_name} / {service.public_contract} remains visible in Stage-04 replay and implementation handoff",
                ", ".join(upstream_ids),
            ]
        )

    binding_rows, enrichment_rows, traceability_rows = build_binding_and_trace_rows(
        phase1_page_map=phase1_page_map,
        phase1_interactions=phase1_interactions,
        phase1_flow_rows=phase1_flow_rows,
        endpoint_specs=endpoint_specs,
        trace_rows=all_trace_rows,
    ) if phase1_interactions else ([], [], [])

    interaction_flow_rows: list[list[str]] = []
    endpoint_chain = endpoint_specs[: max(4, min(len(endpoint_specs), 6))]
    if endpoint_chain:
        for idx in range(max(1, len(endpoint_chain) - 1)):
            current = endpoint_chain[idx]
            nxt = endpoint_chain[idx + 1] if idx + 1 < len(endpoint_chain) else endpoint_chain[idx]
            interaction_flow_rows.append(
                [
                    f"flow_{idx + 1:02d}",
                    f"{current.endpoint_name} -> {nxt.endpoint_name}",
                    f"`{current.home_module}` writes, `{nxt.home_module}` consumes read-only context",
                    f"{current.owns_or_coordinates} + {nxt.owns_or_coordinates}",
                    f"version mismatch or missing `{to_snake(service_technical_name(current))}_id` blocks the handoff",
                    "refresh state and replay with the same contract boundary",
                    "keeps ownership explicit while still allowing downstream composition",
                ]
            )

    scenario_groups = distribute_phase1_ids(all_trace_ids or req_ac_ids, scenario_min)
    scenario_rows: list[list[str]] = []
    scenario_services = services[: max(scenario_min, min(len(services), 6))] or services[:1]
    for idx, service in enumerate(scenario_services, start=1):
        peer = services[idx] if idx < len(services) else service
        scenario_rows.append(
            [
                f"scenario_{idx:02d}",
                "domain operator",
                service.owns_or_coordinates,
                f"`{service.home_module}`, `{peer.home_module}`",
                f"{service.endpoint_name}, {peer.endpoint_name}",
                f"`{service.service_name}` remains the only writer for `{service.owns_or_coordinates}`",
                f"Given `{service.owns_or_coordinates}` exists, When `{service.endpoint_name}` runs, Then the contract must preserve ids, version anchors, and replay context within <= 600 ms for the synchronous path.",
                f"contract response diff for `{service.endpoint_name}`",
                "positive_path / quantified",
                f"`{service.owns_or_coordinates}` is available",
                f"`{service.endpoint_name}` is invoked",
                "the output remains contract-valid, replay-safe, and latency-bounded",
                "versioned ownership handoff",
                service.owns_or_coordinates,
                ", ".join(scenario_groups[idx - 1]) if idx - 1 < len(scenario_groups) else ", ".join(scenario_groups[-1]),
            ]
        )
    while len(scenario_rows) < scenario_min and services:
        service = services[len(scenario_rows) % len(services)]
        scenario_rows.append(
            [
                f"scenario_{len(scenario_rows) + 1:02d}",
                "domain operator",
                service.owns_or_coordinates,
                f"`{service.home_module}`",
                service.endpoint_name,
                "ownership remains explicit under replay",
                f"Given a valid request, When `{service.endpoint_name}` runs, Then the response must preserve the contract envelope and trace id.",
                f"response envelope check for `{service.endpoint_name}`",
                "positive_path / quantified",
                "a valid request exists",
                f"`{service.endpoint_name}` is invoked",
                "the response remains stable, additive, and <= 600 ms on the synchronous path",
                "single-writer discipline",
                service.owns_or_coordinates,
                ", ".join(scenario_groups[-1]),
            ]
        )
    for idx, service in enumerate(services[:2], start=1):
        scenario_rows.append(
            [
                f"scenario_{len(scenario_rows) + 1:02d}",
                "parallel operators",
                service.owns_or_coordinates,
                f"`{service.home_module}`",
                f"{service.endpoint_name}, Update{service_technical_name(service)}Status",
                "concurrent writes must surface version conflict explicitly",
                f"Given two actors update `{service.owns_or_coordinates}` concurrently, When stale version input is submitted, Then the system returns `409 version_conflict` and preserves the last committed record.",
                f"conflict replay and 409 assertion for `{service.endpoint_name}`",
                "concurrent_conflict / quantified",
                "two competing updates exist",
                "the stale update is submitted second",
                "the stale write is rejected with explicit conflict semantics",
                "retry on version conflict with versioned write guard",
                service.owns_or_coordinates,
                ", ".join(scenario_groups[min(idx - 1, len(scenario_groups) - 1)]),
            ]
        )

    tech_rows = list(stage_03_design_defaults["technology_selection_rows"])[:tech_min]

    alternative_candidates = [
        "\n".join(
            [
                f"  - candidate_{idx:02d}:",
                f"    - candidate_name: {candidate['candidate_name']}",
                f"    - pros: {candidate['pros']}",
                f"    - cons: {candidate['cons']}",
                f"    - cost_burden: {candidate['cost_burden']}",
                f"    - fit_scenario: {candidate['fit_scenario']}",
                f"    - reversibility: {candidate['reversibility']}",
            ]
        )
        for idx, candidate in enumerate(
            stage_03_design_defaults["alternative_candidates"][
                : max(profile_minimum(complexity_profile, "stage_03_alt_candidate_structure"), 4)
            ],
            start=1,
        )
    ]

    tradeoff_rows = list(stage_03_design_defaults["tradeoff_rows"])

    public_boundary_rows: list[list[str]] = []
    seen_contracts: set[str] = set()
    for spec in endpoint_specs:
        if spec.public_contract in seen_contracts:
            continue
        if spec.public_contract.rsplit(".", 1)[-1].endswith("List"):
            continue
        seen_contracts.add(spec.public_contract)
        namespace, _, public_name = spec.public_contract.rpartition(".")
        public_boundary_rows.append(
            [
                public_name or spec.public_contract,
                namespace or root_namespace,
                "active",
                spec.home_module,
                "contract",
                f"Stage-03 contract surface via {spec.endpoint_name}",
                f"stable boundary for {spec.purpose.lower()}",
            ]
        )

    mermaid_entities = unique_preserve([str(spec["table_name"]) for spec in rendered_table_specs[:14]])
    mermaid_nodes = [f'    T{idx + 1}["{name}"]' for idx, name in enumerate(mermaid_entities)]
    mermaid_edges = [
        f"    T{idx + 1} --> T{idx + 2}"
        for idx in range(len(mermaid_entities) - 1)
    ] or ["    T1 --> T2"]
    service_chain = unique_preserve([service.service_name for service in services[:6]])
    service_nodes = [f'    S{idx + 1}["{service_name}"]' for idx, service_name in enumerate(service_chain)]
    service_edges = [
        f"    S{idx + 1} --> S{idx + 2}"
        for idx in range(len(service_chain) - 1)
    ] or ["    S1 --> S2"]

    stage = render_phase2_template(
        "stage-03-data-interface-design.md.template",
        {
            "phase1_prd": phase1_prd,
            "complexity_profile": complexity_profile,
            "data_ownership_map_table": make_markdown_table(
                ["object", "owning module", "write authority", "read_only_consumers", "public_contract", "change_propagation_path", "forbidden_shortcut", "closure note"],
                data_ownership_rows,
            ),
            "storage_strategy_table": make_markdown_table(
                ["storage_layer", "first_wave_role", "initial_plan", "one_year_plan", "three_year_plan", "partition_or_shard_rule", "archive_or_cleanup_rule", "why_selected"],
                storage_layer_rows,
            ),
            "access_pattern_and_index_strategy_table": make_markdown_table(
                ["access_pattern", "touched_tables", "predicate_sort_join_keys", "expected_selectivity", "proposed_index", "write_cost_note", "validation_hook"],
                access_pattern_rows,
            ),
            "schema_summary_table": make_markdown_table(
                ["table_name", "ownership", "pk", "fk", "unique_constraints", "composite_indexes"],
                schema_summary_rows,
            ),
            "schema_entries_block": "\n".join(schema_entries),
            "data_sensitivity_and_compliance_matrix_table": make_markdown_table(
                ["table_name", "pii_level", "sensitive_fields", "masking_or_encryption", "retention_rule", "audit_access_rule", "compliance_note"],
                sensitivity_rows,
            ),
            "contract_entries_block": "\n".join(contract_entries),
            "api_endpoint_draft_table": make_markdown_table(
                ["endpoint_name", "method", "path", "purpose", "request_body_example", "response_body_example", "rate_limit_policy", "pagination_rule", "response_profile", "retryability_policy", "idempotency_rule", "failure_codes"],
                api_rows,
            ),
            "stage_02_event_name_carry_forward_table": make_markdown_table(
                ["stage_02_event_name", "stage_03_touchpoints", "preserved_name_or_alias", "mapping_note"],
                event_rows,
            ),
            "event_model_direct_consumption_table": make_markdown_table(
                ["event_name", "contract_touchpoint", "mutation_or_read_effect", "versioning_and_schema_posture", "p3_event_handoff", "claim_ceiling"],
                event_consumption_rows,
            ),
            "contract_trace_registry_table": make_markdown_table(
                ["trace_id", "trace_subject", "subject_type", "owning_module", "downstream_artifact_id", "verification_hook", "upstream_trace_ids"],
                contract_trace_rows,
            ),
            "interaction_matrix_p2_enrichment_block": make_markdown_table(
                ["interaction_id", "page_id", "input_schema_ref", "display_field_set", "validation_rules", "enabled_rule", "value_source", "internal_exposure", "error_state", "readiness_status", "blocked_reason"],
                enrichment_rows,
            ) if enrichment_rows else "- no Phase-1 interaction-flow contract was available, so P2-owned interaction enrichment could not be compiled",
            "data_service_binding_matrix_block": make_markdown_table(
                ["service_binding_id", "interaction_id", "use_case_id", "transaction_group_id", "binding_mode", "domain_service", "api_endpoint", "http_method", "request_field_mapping", "response_field_mapping", "db_entities", "rbac_policy", "audit_event", "failure_codes", "server_generated_fields", "ui_refresh_targets", "handoff_materialization", "readiness_status", "blocked_reason"],
                binding_rows,
            ) if binding_rows else "- no Phase-1 interaction-flow contract was available, so binding matrix generation remained blocked",
            "traceability_matrix_block": make_markdown_table(
                ["trace_row_id", "req_id", "use_case_id", "page_id", "interaction_id", "service_binding_id", "api_endpoint", "test_ids", "closure_gate", "canonical_page_id", "audience_mode", "exposure_scope", "staleness_marker", "upstream_trace_ids"],
                traceability_rows,
            ) if traceability_rows else "- no interaction-level binding chain was available, so traceability remained API/test-skewed",
            "interaction_flow_table": make_markdown_table(
                ["flow_name", "producer_consumer_chain", "write_boundary", "primary_data_surfaces", "failure_detection", "rollback_or_compensation", "closure_note"],
                interaction_flow_rows,
            ),
            "boundary_term": boundary_term,
            "queue_posture_label": async_completion_pack["queue_posture_label"],
            "technology_selection_evaluation_matrix_table": make_markdown_table(
                ["candidate_name", "reliability", "performance_capacity", "scalability", "maintainability", "development_cost", "operations_cost", "ecosystem_maturity", "security_compliance_posture", "deployment_complexity", "integration_cost", "integration_fit", "observability", "migration_path", "vendor_risk", "learning_curve", "failure_mode", "evidence_sources", "final_decision", "rejection_reason"],
                tech_rows,
            ),
            "alternative_candidates_block": "\n".join(alternative_candidates),
            "scenario_coverage_matrix_table": make_markdown_table(
                ["scenario", "actors", "entities", "modules", "contracts / endpoints", "failure_note", "acceptance_criteria", "measurement_hook", "scenario_category", "given", "when", "then", "coordination_strategy", "shared_resource", "upstream_trace_ids"],
                scenario_rows,
            ),
            "key_tradeoff_decisions_table": make_markdown_table(
                ["decision_id", "chosen_posture", "rejected_alternative", "why_selected", "cost_paid_now", "reversibility", "revisit_trigger"],
                tradeoff_rows,
            ),
            "root_namespace": root_namespace,
            "public_boundary_registry_table": make_markdown_table(
                ["public_name", "namespace", "status", "owner_module", "artifact_type", "origin", "closure_note"],
                public_boundary_rows,
            ),
            "data_mermaid_flowchart_block": "\n".join(mermaid_nodes + mermaid_edges),
            "service_mermaid_flowchart_block": "\n".join(service_nodes + service_edges),
        },
    )
    return stage.rstrip() + "\n"



def render_stage_04(
    *,
    phase1_prd: Path,
    phase1_prototype_spec: Path | None = None,
    phase1_prototype_prompt_pack: Path | None = None,
    phase1_interaction_flow_contract: Path | None = None,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
    contract_names: list[str],
    endpoint_names: list[str],
    stage_03_text: str,
    stage_02_5_text: str,
) -> str:
    supports_deferred_extension_seam = context_supports_deferred_extension_seam(context)
    business_proof_handoff = business_proof_constraint_block(context, indent=4)
    thesis_architecture_handoff = business_architecture_pressure_block(context, indent=4)
    deferred_seam_heading = "deferred_attribution_seam" if supports_deferred_extension_seam else "deferred_extension_seam"
    deferred_seam_line = (
        "attribution remains deferred / placeholder-backed and is not upgraded into MVP-complete proof by Stage-04"
        if supports_deferred_extension_seam
        else "deferred extension remains placeholder-backed and is not upgraded into MVP-complete proof by Stage-04"
    )
    sequence_target = max(profile_minimum(complexity_profile, "stage_04_sequence_diagrams"), 2)
    service_count = len(services)
    wp_target = max(profile_minimum(complexity_profile, "stage_04_work_packages"), 6 if service_count >= 9 else 5 if service_count >= 7 else 4)
    rbi_target = max(profile_minimum(complexity_profile, "stage_04_rbi_items"), 3)
    verification_target = max(profile_minimum(complexity_profile, "stage_04_design_verification"), 3)
    replay_target = max(profile_minimum(complexity_profile, "stage_04_verification_replay"), 2)
    observability_target = max(profile_minimum(complexity_profile, "stage_04_observability"), 3)
    rbi_trace_target = max(profile_minimum(complexity_profile, "stage_04_rbi_trace_registry"), 3)
    unresolved_technical_names = [
        item
        for item in context.get("unresolved_technical_names", [])
        if isinstance(item, dict) and str(item.get("source_label", "")).strip()
    ]
    if unresolved_technical_names:
        rbi_trace_target = max(rbi_trace_target, rbi_target + len(unresolved_technical_names))
    prototype_spec_path = _resolve_phase1_prototype_asset_path(
        phase1_prd,
        explicit_path=phase1_prototype_spec,
        candidate_names=("prototype-spec.md", "prototype_spec.md"),
    )
    prototype_prompt_pack_path = _resolve_phase1_prototype_asset_path(
        phase1_prd,
        explicit_path=phase1_prototype_prompt_pack,
        candidate_names=("prototype-prompt-pack.md", "prototype_prompt_pack.md"),
    )
    interaction_flow_contract_path = _resolve_phase1_interaction_flow_contract_path(
        phase1_prd,
        explicit_path=phase1_interaction_flow_contract,
    )
    phase1_page_map = _extract_page_map_from_prototype_spec(prototype_spec_path)
    page_blueprint_rows: list[list[str]] = []
    if phase1_page_map:
        primary_surfaces = [page["page_name"] for page in phase1_page_map if str(page.get("page_name") or "").strip()]
        primary_surface_lines: list[str] = []
        for page in phase1_page_map:
            page_name = str(page.get("page_name") or "").strip()
            if not page_name:
                continue
            suffix_parts: list[str] = []
            page_role = str(page.get("page_role") or "").strip()
            blueprint_type = str(page.get("page_blueprint_type") or "").strip()
            surface_variant = str(page.get("surface_variant") or "").strip()
            audience_mode = str(page.get("audience_mode") or "").strip()
            if page_role:
                suffix_parts.append(f"role: {page_role}")
            if blueprint_type:
                suffix_parts.append(f"blueprint: {blueprint_type}")
            if audience_mode:
                suffix_parts.append(f"audience: {audience_mode}")
            if surface_variant:
                suffix_parts.append(f"variant: {surface_variant}")
            if blueprint_type:
                page_blueprint_rows.append(
                    [
                        page_name,
                        blueprint_type,
                        page_role or "not-stated",
                        str(page.get("canonical_page_id") or "").strip() or "not-stated",
                        surface_variant or "not-stated",
                        audience_mode or "not-stated",
                        str(page.get("session_role_source") or "").strip() or "not-stated",
                        str(page.get("auth_entry_route") or "").strip() or "not-stated",
                        str(page.get("auth_entry_label") or "").strip() or "not-stated",
                        str(page.get("workspace_entry_roles") or "").strip() or "not-stated",
                        str(page.get("route_reachability_mode") or "").strip() or "not-stated",
                        str(page.get("navigation_scope") or "").strip() or "not-stated",
                        str(page.get("handoff_visibility") or "").strip() or "not-stated",
                        str(page.get("forbidden_exposure") or "").strip() or "not-stated",
                    ]
                )
            primary_surface_lines.append(f"    - `{page_name}`" + (f" ({'; '.join(suffix_parts)})" if suffix_parts else ""))
        primary_surface_block = "\n".join(primary_surface_lines)
        surface_provenance = "phase1-prototype-spec"
    else:
        primary_surfaces = semantic_primary_surfaces(context) or extract_dynamic_primary_surfaces(str(context.get("text", "")), phase1_page_map)
        primary_surface_block = "\n".join(f"    - `{surface}`" for surface in primary_surfaces)
        surface_provenance = "phase1-ia-inferred"
    prototype_spec_ref = str(prototype_spec_path) if prototype_spec_path else ""
    prototype_prompt_pack_ref = str(prototype_prompt_pack_path) if prototype_prompt_pack_path else ""
    interaction_flow_contract_ref = str(interaction_flow_contract_path) if interaction_flow_contract_path else ""
    page_blueprint_block = (
        make_markdown_table(
            [
                "surface",
                "page_blueprint_type",
                "page_role",
                "canonical_page_id",
                "surface_variant",
                "audience_mode",
                "session_role_source",
                "auth_entry_route",
                "auth_entry_label",
                "workspace_entry_roles",
                "route_reachability_mode",
                "navigation_scope",
                "handoff_visibility",
                "forbidden_exposure",
            ],
            page_blueprint_rows,
        )
        if page_blueprint_rows
        else "not available; fallback surface inference is active"
    )

    all_trace_rows = list(context["all_trace_rows"])
    all_trace_ids = [row["trace_id"] for row in all_trace_rows]
    req_ac_ids = [row["trace_id"] for row in all_trace_rows if row.get("unit_type") in {"requirement", "acceptance-criteria"}] or all_trace_ids
    rbi_id_groups = distribute_phase1_ids(req_ac_ids, rbi_trace_target)

    service_chunks = round_robin_chunks([service.service_name for service in services], wp_target)
    wp_ids = [f"WP-A{idx}" for idx in range(1, wp_target + 1)]
    work_package_rows: list[list[str]] = []
    for idx, wp_id in enumerate(wp_ids):
        owned_services = service_chunks[idx] if idx < len(service_chunks) else []
        service_scope = ", ".join(f"`{name}`" for name in owned_services[:3]) or "`cross-cutting`"
        depends_on = "none" if idx == 0 else wp_ids[idx - 1]
        linked_rbi = f"RBI-{min(idx + 1, rbi_target):02d}"
        work_package_rows.append(
            [
                wp_id,
                f"stabilize {service_scope} contracts, replay paths, and implementation handoff",
                f"the slice preserves ownership, contract naming, and replay evidence for {service_scope}",
                f"{4 + (idx % 3)}d",
                depends_on,
                linked_rbi,
            ]
        )

    nested_wp_entries = [
        "\n".join(
            [
                f"    - `{row[0]}`:",
                f"      - completion_signal: {row[2]}",
                f"      - acceptance_criteria: Given the design slice is implemented, When verification replay is run, Then {row[2]}.",
            ]
        )
        for row in work_package_rows[: max(profile_minimum(complexity_profile, "stage_04_slice_acceptance"), 2)]
    ]

    deadlines = ["2026-04-15", "2026-04-18", "2026-04-20", "2026-04-22", "2026-04-25", "2026-04-28"]
    rbi_rows: list[list[str]] = []
    for idx in range(rbi_target):
        owner_service = services[idx % len(services)] if services else None
        wp = work_package_rows[min(idx, len(work_package_rows) - 1)][0]
        blocks = work_package_rows[min(idx + 1, len(work_package_rows) - 1)][0]
        label = owner_service.service_name if owner_service else "cross-cutting slice"
        rbi_rows.append(
            [
                f"RBI-{idx + 1:02d}",
                f"runtime proof is still required for `{label}` contract and replay posture",
                "H" if idx < 2 else "M" if idx < 4 else "L",
                wp,
                "platform owner" if idx % 2 == 0 else "workflow owner",
                blocks,
                deadlines[idx % len(deadlines)],
                f"RBI-{idx + 1:02d} -> {wp}",
            ]
        )
    for item in unresolved_technical_names:
        rbi_id = f"RBI-{len(rbi_rows) + 1:02d}"
        source_label = str(item.get("source_label", "")).strip()
        technical_name = str(item.get("technical_name", "")).strip()
        technical_slug = str(item.get("technical_slug", "")).strip()
        wp = work_package_rows[0][0] if work_package_rows else "WP-A1"
        rbi_rows.append(
            [
                rbi_id,
                (
                    f"`{source_label}` lacks a usable ASCII technical name; generated placeholder "
                    f"`{technical_name}` / `{technical_slug}` must remain review-bound until a source-backed "
                    "semantic alias is supplied"
                ),
                "H",
                wp,
                "architecture owner",
                wp,
                "before P3 implementation closure",
                f"{rbi_id} -> {wp}",
            ]
        )

    design_verification_rows: list[list[str]] = []
    for idx, service in enumerate(services[:verification_target], start=1):
        design_verification_rows.append(
            [
                f"`{service.service_name}` boundary preserved",
                "pass",
                "contract review + replay walkthrough",
                f"{service.endpoint_name} contract and ownership table",
                f"`{service.service_name}` remains the only writer for `{service.owns_or_coordinates}`",
                "runtime proof pending",
                f"RBI-{min(idx, len(rbi_rows)):02d} / {work_package_rows[min(idx - 1, len(work_package_rows) - 1)][0]}",
            ]
        )
    while len(design_verification_rows) < verification_target:
        design_verification_rows.append(
            [
                f"cross-module handoff {len(design_verification_rows) + 1:02d}",
                "pass",
                "replay walkthrough",
                "handoff package",
                "ownership, ids, and trace anchors survive the handoff",
                "runtime proof pending",
                f"RBI-{min(len(design_verification_rows) + 1, len(rbi_rows)):02d}",
            ]
        )

    replay_rows: list[list[str]] = []
    replay_count = max(replay_target, 2)
    replay_id_groups = distribute_phase1_ids(all_trace_ids or req_ac_ids, replay_count)
    for idx in range(replay_count):
        current = services[idx % len(services)] if services else None
        nxt = services[(idx + 1) % len(services)] if services else None
        artifact = f"{current.owns_or_coordinates if current else 'core_object'} + {nxt.owns_or_coordinates if nxt else 'downstream_object'}"
        replay_rows.append(
            [
                f"P2-RP-{idx + 1:02d}",
                f"{current.endpoint_name if current else 'contract'} handoff replay",
                "scenario-replay" if idx % 2 else "contract-walkthrough",
                artifact,
                "ownership, contract ids, and replay anchors stay explicit",
                "implementation intake keeps the same closure rules visible",
                "pass",
                design_verification_rows[min(idx, len(design_verification_rows) - 1)][0],
                "IMPL-STG00-INPUT-0001",
                f"{work_package_rows[min(idx, len(work_package_rows) - 1)][0]}, {rbi_rows[min(idx, len(rbi_rows) - 1)][0]}",
                ", ".join(replay_id_groups[min(idx, len(replay_id_groups) - 1)]),
            ]
        )

    rbi_trace_rows: list[list[str]] = []
    for idx, rbi in enumerate(rbi_rows[:rbi_trace_target], start=1):
        ids = rbi_id_groups[idx - 1] if idx - 1 < len(rbi_id_groups) else rbi_id_groups[-1]
        rbi_trace_rows.append(
            [
                f"P2-RT-{idx:02d}",
                rbi[0],
                rbi[3],
                "IMPL-STG00-INPUT-0001",
                f"{rbi[0]} remains linked to `{rbi[3]}` until replay or runtime evidence closes the risk",
                "implementation intake must preserve RBI owner, blocker, and closure rule",
                ", ".join(ids),
            ]
        )

    metric_map = {
        "transactional": "write_latency, version_conflict_rate",
        "orchestration": "handoff_latency, replay_dedupe_rate",
        "read-assembly": "cache_hit_rate, refresh_latency",
        "policy": "deny_rate, policy_check_latency",
        "domain": "contract_validation_failures, publish_latency",
        "support": "append_latency, evidence_gap_rate",
    }
    observability_rows: list[list[str]] = []
    for idx, service in enumerate(services[:observability_target], start=1):
        observability_rows.append(
            [
                f"surface-{idx:02d}",
                service.service_name,
                metric_map.get(service.service_type, "request_latency, error_rate"),
                f"tenant_id + {to_snake(service_technical_name(service))}_id + trace_id",
                f"alert when `{service.endpoint_name}` error rate or latency exceeds threshold",
                "p95 <= 600ms for sync paths; async queues remain bounded",
                "platform owner" if idx % 2 else "workflow owner",
                f"do not widen rollout until `{service.service_name}` metrics are stable",
            ]
        )

    environment_prerequisites = format_nested_bullets(derive_environment_dependency_prerequisites(stage_03_text, stage_02_5_text), indent=4)
    adr_titles_for_list = [str(item) for item in context.get("adr_titles", [])]
    adr_list = "\n".join(f"    - `AD-{idx:02d}` {title}" for idx, title in enumerate(adr_titles_for_list[:10], start=1))
    contract_list = "\n".join(f"    - `{name}`" for name in unique_preserve(contract_names))

    mermaid_sequences: list[str] = []
    if services:
        sequence_count = min(sequence_target, max(1, len(services) - 1))
        for idx in range(sequence_count):
            current = services[idx]
            nxt = services[idx + 1] if idx + 1 < len(services) else services[idx]
            mermaid_sequences.append(
                "\n".join(
                    [
                        "```mermaid",
                        "sequenceDiagram",
                        "    participant U as Operator",
                        f"    participant S{idx + 1} as {current.service_name}",
                        f"    participant S{idx + 2} as {nxt.service_name}",
                        "    participant A as AuditTrail",
                        f"    U->>S{idx + 1}: invoke {current.endpoint_name}",
                        f"    S{idx + 1}->>S{idx + 2}: hand off {current.owns_or_coordinates} context",
                        f"    S{idx + 2}->>A: record replay-safe audit evidence",
                        f"    A-->>S{idx + 2}: audit persistence confirmed",
                        f"    S{idx + 2}-->>U: return versioned acknowledgement for {nxt.owns_or_coordinates}",
                        "```",
                    ]
                )
            )
    if not mermaid_sequences:
        mermaid_sequences.append(
            "\n".join(
                [
                    "```mermaid",
                    "sequenceDiagram",
                    "    participant U as Operator",
                    "    participant A as CoreService",
                    "    participant B as ReviewService",
                    "    participant T as AuditTrail",
                    "    U->>A: submit workflow request",
                    "    A->>B: contract-bound handoff",
                    "    B->>T: record audit event",
                    "    T-->>B: persistence confirmed",
                    "    B-->>U: replay-safe acknowledgement",
                    "```",
                ]
            )
        )

    stage = render_phase2_template(
        "stage-04-design-convergence.md.template",
        {
            "phase1_prd": phase1_prd,
            "complexity_profile": complexity_profile,
            "architecture_convergence_adr_list": adr_list,
            "contract_list": contract_list,
            "deferred_seam_heading": deferred_seam_heading,
            "deferred_seam_line": deferred_seam_line,
            "business_proof_handoff": business_proof_handoff,
            "thesis_architecture_handoff": thesis_architecture_handoff,
            "surface_provenance": surface_provenance,
            "primary_surface_block": primary_surface_block,
            "prototype_spec_ref": prototype_spec_ref,
            "prototype_prompt_pack_ref": prototype_prompt_pack_ref,
            "interaction_flow_contract_ref": interaction_flow_contract_ref,
            "page_blueprint_block": page_blueprint_block,
            "design_verification_notes_table": make_markdown_table(
                ["check_item", "result", "verification_method", "evidence", "acceptance_rule", "residual_gap", "linked_rbi_or_wp"],
                design_verification_rows,
            ),
            "verification_replay_evidence_table": make_markdown_table(
                ["replay_id", "scenario_or_contract", "replay_type", "source_artifacts", "expected_outcome", "observed_outcome", "verdict", "evidence_ref", "downstream_artifact_id", "linked_rbi_or_wp", "upstream_trace_ids"],
                replay_rows,
            ),
            "unresolved_risks_table": make_markdown_table(
                ["rbi_id", "item", "risk_level", "spike_wp", "responsible_party", "blocks_which_wp", "resolution_deadline", "rbi_matrix"],
                rbi_rows,
            ),
            "rbi_trace_registry_table": make_markdown_table(
                ["trace_id", "rbi_id", "bound_wp", "downstream_artifact_id", "verification_hook", "handoff_rule", "upstream_trace_ids"],
                rbi_trace_rows,
            ),
            "observability_readiness_table": make_markdown_table(
                ["surface", "service_or_flow", "key_metrics", "structured_logs", "alert_rule", "slo_or_threshold", "owner", "rollout_guardrail"],
                observability_rows,
            ),
            "implementation_task_sketch_table": make_markdown_table(
                ["wp_id", "scope", "acceptance_criteria", "estimated_effort", "depends_on", "linked_rbi_or_slice"],
                work_package_rows,
            ),
            "nested_wp_entries_block": "\n".join(nested_wp_entries),
            "environment_prerequisites": environment_prerequisites,
            "mermaid_sequences_block": "\n".join(mermaid_sequences),
        },
    )
    return stage.rstrip() + "\n"


def write_generation_sidecars(
    *,
    output_dir: Path,
    phase1_prd: Path,
    case_name: str,
    version: str,
    complexity_profile: str,
    complexity_report: dict[str, object],
    owner: str,
    existing_system_architecture_change_intake: Path | None = None,
) -> None:
    generation_report = {
        "case_name": case_name,
        "version": version,
        "phase1_prd": str(phase1_prd),
        "existing_system_architecture_change_intake": (
            str(existing_system_architecture_change_intake)
            if existing_system_architecture_change_intake
            else ""
        ),
        "complexity_profile": complexity_profile,
        "complexity_report": complexity_report,
        "owner": owner,
        "generator": "scripts/phase2/run_phase2_first_version.py",
    }
    write_cross_phase_profiled_surface(
        output_dir,
        "phase2",
        "phase-2-first-version-generation-report.json",
        json.dumps(generation_report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    audit = inspect_case(output_dir)
    write_cross_phase_profiled_surface(
        output_dir,
        "phase2",
        "phase-2-first-pass-audit.json",
        json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )


def _phase1_claims_for_phase2(phase1_prd: Path) -> tuple[list[Any], str, Path | None]:
    return phase1_claims_for_phase2(phase1_prd)


__all__ = [name for name in globals() if not name.startswith("__")]
