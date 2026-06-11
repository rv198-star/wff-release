#!/usr/bin/env python3
"""Phase-2 first-version runtime slice: phase2_first_version_semantic_model.py."""

from __future__ import annotations

from phase2.phase2_first_version_cli import *  # noqa: F401,F403

def _short_stable_suffix(raw: str) -> str:
    return short_stable_suffix(raw)


def _ascii_words(raw: str) -> list[str]:
    return technical_ascii_words(raw)


def _ascii_pascal(raw: str) -> str:
    return technical_ascii_pascal(raw)


def _ascii_snake(raw: str) -> str:
    return technical_ascii_snake(raw)


def _ascii_slug(raw: str) -> str:
    return technical_ascii_slug(raw)


def _looks_like_generic_object_descriptor(raw: str) -> bool:
    return looks_like_generic_object_descriptor(raw)


def _technical_candidate_order(raw: str, alias_candidates: tuple[str, ...]) -> list[str]:
    return technical_candidate_order(raw, alias_candidates)











def to_upper_entity(raw: str) -> str:
    return semantic_table_name(raw).upper()



def render_markdown_cell(value: object) -> str:
    return sanitize_markdown_table_cell(value, escape_ampersand=True)


def make_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    return render_markdown_table(headers, rows, escape_ampersand=True)


def infer_schema_field_type(field_name: str, value: object) -> str:
    return infer_projected_schema_field_type(field_name, value)


def flatten_schema_fields(value: object, *, prefix: str = "") -> list[str]:
    return flatten_projected_schema_fields(value, prefix=prefix)


def extract_nested_bullet_values(block: str, field_name: str) -> list[str]:
    lines = block.splitlines()
    marker = f"- {field_name}:"
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == marker:
            start = idx
            break
    if start is None:
        return []

    values: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("### ") or line.startswith("## "):
            break
        if line.startswith("- ") and not line.startswith("  - "):
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            values.append(stripped[2:].strip().strip("`"))
    return values


def parse_labeled_bullets(block: str, prefix: str) -> list[tuple[str, str]]:
    return [
        (match.group(1).strip(), match.group(2).strip())
        for match in re.finditer(rf"^[ \t]*-[ \t]*({re.escape(prefix)}-[0-9]+):[ \t]*(.+?)\s*$", block, flags=re.MULTILINE)
    ]


READER_FACING_THESIS_KEY_ALIASES = {
    "产品押注": "chosen_thesis",
    "为什么现在": "why_now",
    "为什么这个切片": "product_boundary_implication",
    "为什么不是现状": "current_state_substitute_to_beat",
    "为什么不是单点工具/服务替代": "why_this_not_alternatives",
    "下一轮投入证据": "proof_target",
    "读者摘要": "business_argument",
    "源真相边界": "review_bound_truth",
    "阻断更强声明的开放真相": "review_bound_truth",
    "禁止升级": "review_bound_truth",
    "待复核事实": "review_bound_truth",
}


def _merge_simple_bullet_value(parsed: dict[str, object], key: str, value: str) -> None:
    existing = parsed.get(key)
    if isinstance(existing, str) and existing.strip() and value not in existing:
        parsed[key] = f"{existing}; {value}"
        return
    if not existing:
        parsed[key] = value


def parse_simple_heading_bullets(block: str, *, list_keys: set[str] | None = None) -> dict[str, object]:
    parsed: dict[str, object] = {}
    list_keys = list_keys or set()
    for raw_line in block.splitlines():
        match = re.match(r"^[ \t]*-[ \t]*(.+?)[：:][ \t]*(.+?)\s*$", raw_line)
        if not match:
            continue
        raw_key = match.group(1).strip().strip("`")
        key = READER_FACING_THESIS_KEY_ALIASES.get(raw_key, raw_key)
        value = match.group(2).strip().strip("`")
        if key in list_keys:
            parsed[key] = unique_preserve(
                [
                    item.strip().strip("`")
                    for item in re.split(r"\s*(?:->|→|,|;)\s*", value)
                    if item.strip().strip("`")
                ]
            )
            continue
        _merge_simple_bullet_value(parsed, key, value)
    return parsed


def heading_block_any_level(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = None
    start_level = ""
    for idx, line in enumerate(lines):
        match = re.match(r"^(##+)\s+(.*)$", line.strip())
        if not match:
            continue
        level = match.group(1)
        title = match.group(2).strip()
        if heading in title:
            start = idx
            start_level = level
            break
    if start is None:
        return ""

    collected = [lines[start]]
    for line in lines[start + 1 :]:
        match = re.match(r"^(##+)\s+", line.strip())
        if match:
            next_level = match.group(1)
            if len(next_level) <= len(start_level):
                break
        collected.append(line)
    return "\n".join(collected).strip()


def flatten_trace_units(units: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    ordered: list[dict[str, str]] = []
    for group in ("epic_trace_units", "use_case_trace_units", "requirement_trace_units", "acceptance_trace_units"):
        ordered.extend(units.get(group, []))
    return ordered


def round_robin_chunks(values: list[str], chunk_count: int) -> list[list[str]]:
    buckets = [[] for _ in range(max(chunk_count, 1))]
    if not values:
        return buckets
    for idx, value in enumerate(values):
        buckets[idx % len(buckets)].append(value)
    return buckets


def summarize_list(values: list[str], *, max_items: int = 4) -> str:
    trimmed = values[:max_items]
    if not trimmed:
        return "none"
    return ", ".join(f"`{item}`" for item in trimmed)




def semantic_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) > 1 and token not in {"the", "and", "for", "with", "from", "into", "page", "flow", "step"}
    }


def semantic_focus_tokens(value: str) -> set[str]:
    return {
        token
        for token in semantic_tokens(value)
        if token
        not in {
            "current",
            "context",
            "data",
            "detail",
            "details",
            "page",
            "screen",
            "status",
            "summary",
            "load",
            "loaded",
            "show",
            "stay",
            "together",
            "workspace",
            "required",
        }
    }


def normalize_blueprint_type(value: str) -> str:
    return re.sub(r"[\s_]+", "-", str(value or "").strip().lower()).strip("-")


def derive_root_namespace(case_name: str, prd_text: str) -> str:
    collapsed = slugify(case_name).replace("-", "")
    if collapsed:
        return collapsed[:16]
    return "case"


def derive_boundary_scope(prd_text: str) -> str:
    lowered = prd_text.lower()
    named_account_boundary = re.search(r"\b(?!single\b)[a-z][a-z0-9-]* account boundary\b", lowered)
    named_single_boundary = re.search(r"\bsingle-[a-z][a-z0-9-]+ deployment\b", lowered)
    named_private_boundary = re.search(r"\b[a-z][a-z0-9-]+-private boundary\b", lowered)
    if named_account_boundary or named_single_boundary or named_private_boundary:
        return "account"
    return "tenant"


def boundary_phrase(boundary_scope: str) -> str:
    return "account" if boundary_scope == "account" else "tenant"


def boundary_subject(boundary_scope: str) -> str:
    return "account" if boundary_scope == "account" else "tenant"


def workflow_scope_summary(context: dict[str, object]) -> str:
    domains = [str(item) for item in context.get("domains", []) if str(item).strip()]
    if domains:
        return " -> ".join(domains[:5])
    objects = [str(item) for item in context.get("core_objects", []) if str(item).strip()]
    if objects:
        return " -> ".join(objects[:5])
    return "source-defined workflow"


def derive_complexity_profile(args: argparse.Namespace, phase1_prd: Path) -> tuple[str, dict[str, object]]:
    if args.complexity_profile:
        chosen = normalized_complexity_profile(args.complexity_profile)
        return chosen, {"suggested_profile": chosen, "selection_confidence": "override", "indicators": {}}
    report = classify_phase1_prd(phase1_prd)
    return normalized_complexity_profile(str(report.get("suggested_profile", "standard"))), report


def to_pascal(raw: str) -> str:
    words = re.split(r"[^A-Za-z0-9]+", raw)
    identifier = "".join(word[:1].upper() + word[1:] for word in words if word)
    if identifier:
        return identifier
    return choose_technical_pascal(raw, prefix="Entity")


def to_camel(raw: str) -> str:
    pascal = to_pascal(raw)
    return pascal[:1].lower() + pascal[1:] if pascal else ""


def pluralize_slug(slug: str) -> str:
    if slug and not re.search(r"[a-z]", slug):
        return slug
    if slug.endswith("s"):
        return slug
    if slug.endswith("y") and len(slug) > 1 and slug[-2] not in "aeiou":
        return slug[:-1] + "ies"
    return slug + "s"


def infer_collection_alias(endpoint_name: str) -> str:
    if endpoint_name.startswith("List") and len(endpoint_name) > 4:
        return to_camel(endpoint_name[4:])
    return ""


def require_context_modules(context: dict[str, object]) -> list[dict[str, object]]:
    modules = context.get("modules")
    if not isinstance(modules, list) or not modules:
        raise SystemExit("需要先完成 WO-02b 的 P1 动态提取：context['modules'] 缺失或为空")
    normalized_modules: list[dict[str, object]] = []
    for module in modules:
        if isinstance(module, dict):
            normalized_modules.append(module)
    if not normalized_modules:
        raise SystemExit("需要先完成 WO-02b 的 P1 动态提取：context['modules'] 缺失或为空")
    return normalized_modules


















def service_technical_name(service: ServiceSpec) -> str:
    return service.technical_name or choose_technical_pascal(service.owns_or_coordinates, prefix="Entity")


def service_technical_slug(service: ServiceSpec) -> str:
    return service.technical_slug or choose_technical_slug(service_technical_name(service), prefix="entity")




def context_technical_name(context: dict[str, object], label: str, *, prefix: str = "Entity") -> str:
    hints = context.get("technical_name_hints", {})
    if isinstance(hints, dict):
        explicit = str(hints.get(label, "")).strip()
        if explicit:
            return explicit
    alias_hints = context.get("object_alias_hints", {})
    candidates = alias_hints.get(label, []) if isinstance(alias_hints, dict) else []
    return choose_technical_pascal(label, *[str(item) for item in candidates], prefix=prefix)


def context_technical_slug(context: dict[str, object], label: str, *, prefix: str = "entity") -> str:
    hints = context.get("technical_slug_hints", {})
    if isinstance(hints, dict):
        explicit = str(hints.get(label, "")).strip()
        if explicit:
            return explicit
    alias_hints = context.get("object_alias_hints", {})
    candidates = alias_hints.get(label, []) if isinstance(alias_hints, dict) else []
    return choose_technical_slug(label, *[str(item) for item in candidates], prefix=prefix)


def remember_unresolved_technical_name(
    unresolved_items: list[dict[str, str]],
    *,
    source_label: str,
    technical_name: str,
    technical_slug: str,
    source_kind: str,
) -> None:
    if not (technical_name_is_review_bound(technical_name) or technical_name_is_review_bound(technical_slug)):
        return
    cleaned_source = str(source_label or "").strip()
    if not cleaned_source:
        return
    key = (cleaned_source, str(technical_name or "").strip(), str(technical_slug or "").strip(), source_kind)
    seen = {
        (
            str(item.get("source_label", "")).strip(),
            str(item.get("technical_name", "")).strip(),
            str(item.get("technical_slug", "")).strip(),
            str(item.get("source_kind", "")).strip(),
        )
        for item in unresolved_items
    }
    if key in seen:
        return
    unresolved_items.append(
        {
            "source_label": cleaned_source,
            "source_kind": source_kind,
            "technical_name": str(technical_name or "").strip(),
            "technical_slug": str(technical_slug or "").strip(),
            "status": "review_bound",
            "reason": "no-usable-ascii-technical-name",
        }
    )


def technical_name_can_enter_phase3_surface(technical_name: str, technical_slug: str = "") -> bool:
    return not (technical_name_is_review_bound(technical_name) or technical_name_is_review_bound(technical_slug))


def context_label_can_enter_phase3_surface(context: dict[str, object], label: str) -> bool:
    technical_name = context_technical_name(context, label)
    technical_slug = context_technical_slug(context, label)
    return technical_name_can_enter_phase3_surface(technical_name, technical_slug)


def phase3_executable_business_objects(context: dict[str, object], values: list[str]) -> list[str]:
    return [
        value
        for value in persistent_business_objects(values)
        if context_label_can_enter_phase3_surface(context, value)
    ]


def _module_with_phase3_executable_primary(
    context: dict[str, object],
    module: dict[str, object],
) -> dict[str, object] | None:
    candidates = phase3_executable_business_objects(
        context,
        [module_primary_object(module), *module_core_objects(module)],
    )
    if not candidates:
        return None

    primary_object = candidates[0]
    executable = dict(module)
    executable["primary_object"] = primary_object
    executable["core_objects"] = candidates
    executable["technical_primary_object"] = context_technical_name(context, primary_object)
    executable["technical_primary_slug"] = context_technical_slug(context, primary_object)
    if not technical_name_can_enter_phase3_surface(
        str(executable.get("technical_module_name", "")),
        str(executable.get("technical_module_slug", "")),
    ):
        executable["technical_module_name"] = executable["technical_primary_object"]
        executable["technical_module_slug"] = executable["technical_primary_slug"]
        executable["home_namespace"] = ""
    executable["primary_endpoint"] = ""
    executable["event"] = ""
    return executable










def infer_home_namespace(root_namespace: str, module: dict[str, object]) -> str:
    explicit = str(module.get("home_namespace", "")).strip()
    if explicit:
        return explicit
    return f"{root_namespace}.{module_technical_slug(module).replace('-', '.')}"


def infer_public_contract(home_namespace: str, primary_object: str, technical_object: str | None = None) -> str:
    return f"{home_namespace}.{technical_object or to_pascal(primary_object)}"


def infer_http_method(service_type: str, endpoint_name: str) -> str:
    if endpoint_name.startswith(("Get", "List")) or service_type == "read-assembly":
        return "GET"
    if endpoint_name.startswith(("Update", "Patch")):
        return "PATCH"
    return "POST"


def infer_endpoint_path(module: dict[str, object], service_type: str, primary_object: str) -> str:
    base = pluralize_slug(module_technical_object_slug(module))
    if service_type == "read-assembly":
        return f"/api/v1/{base}"
    return f"/api/v1/{base}"


def release_service_type_surface(service_type: str) -> str:
    return {
        "transactional": "写入执行",
        "orchestration": "流程编排",
        "read-assembly": "读取汇总",
        "policy": "策略判断",
        "domain": "领域处理",
        "support": "审计支撑",
    }.get(service_type, "领域处理")


def release_domain_role_surface(service_types: list[str]) -> str:
    kinds = {item for item in service_types if item}
    if not kinds:
        return "主线业务能力域"
    if kinds <= {"domain", "transactional"}:
        return "主线业务能力域"
    if kinds <= {"orchestration"}:
        return "主线编排能力域"
    if kinds <= {"read-assembly"}:
        return "读取汇总能力域"
    if kinds <= {"policy"}:
        return "策略与权限能力域"
    if kinds <= {"support"}:
        return "审计与支撑能力域"
    if "orchestration" in kinds:
        return "主线协作编排域"
    if "read-assembly" in kinds:
        return "主线读取汇总域"
    return "主线协作能力域"


def release_module_role_surface() -> str:
    return "模块内权责与契约发布"


def release_slice_guardrail() -> str:
    return "相邻能力域只能只读消费，不接管本域写入权"


def release_handoff_rule() -> str:
    return "先在本域完成权威写入，再向下游传播变更"


def release_consistency_boundary(home_module: str, primary_object: str) -> str:
    return f"在 {home_module} 内保留 {primary_object} 的权威边界"


def release_change_propagation_note(service_name: str, endpoint_name: str) -> str:
    return f"{service_name} 先完成权威写入，再经 {endpoint_name} 向下游传播"


def release_read_context_purpose(primary_object: str) -> str:
    return f"围绕 {primary_object} 提供读取详情与评审上下文，供主线复核与下游消费。"


def release_workflow_audit_purpose() -> str:
    return "保留可审计的流程收口、异常处理与对操作者可见的评审证据。"


def release_cross_module_review_purpose() -> str:
    return "汇总主线中的跨模块收口、评审与异常摘要，供统一复核。"


def infer_service_purpose(module: dict[str, object], service_type: str, primary_object: str) -> str:
    module_surface = module_name(module)
    if service_type == "read-assembly":
        return (
            f"围绕 {primary_object} 汇总 {module_surface} 的可读详情，"
            "让评审与下游模块不必再次拼接上下文。"
        )
    if service_type == "orchestration":
        return (
            f"围绕 {primary_object} 编排 {module_surface} 的关键流程推进，"
            "并显式保留下一个动作所需上下文。"
        )
    if service_type == "policy":
        return (
            f"围绕 {primary_object} 明确 {module_surface} 的访问与策略判断边界，"
            "避免隐式放行或越权写入。"
        )
    if service_type == "support":
        return (
            f"围绕 {primary_object} 保留 {module_surface} 的审计与支撑记录，"
            "确保异常、复盘与责任追踪可回放。"
        )
    return (
        f"围绕 {primary_object} 明确 {module_surface} 的核心处理边界，"
        "让上下游能够直接理解状态变化与下一步动作。"
    )


def _prototype_page_value(page: dict[str, str], key: str) -> str:
    value = str(page.get(key) or "").strip().strip("`")
    return "" if value == "—" else value


def _objects_from_prototype_pages(prototype_pages: list[dict[str, str]]) -> list[str]:
    values: list[str] = []
    for page in prototype_pages:
        values.extend(split_inline_values(_prototype_page_value(page, "business_objects")))
    return unique_preserve(values)


def _module_definitions_from_prototype_pages(
    prototype_pages: list[dict[str, str]],
    root_namespace: str,
) -> list[dict[str, object]]:
    modules: list[dict[str, object]] = []
    seen: set[str] = set()
    for page in prototype_pages:
        module_name = _prototype_page_value(page, "canonical_page_id") or _prototype_page_value(page, "page_name")
        if not module_name:
            continue
        module_key = slugify(module_name)
        if not module_key or module_key in seen:
            continue
        seen.add(module_key)
        module_objects = split_inline_values(_prototype_page_value(page, "business_objects"))
        if not module_objects:
            module_objects = split_inline_values(_prototype_page_value(page, "must_show_together").replace("+", ","))
        service_type = (
            "read-assembly"
            if _prototype_page_value(page, "page_blueprint_type").lower() in {"dashboard", "review-decision"}
            else "domain"
        )
        primary_object = module_objects[-1] if module_objects else module_name.strip()
        module_stub = {
            "module_name": module_name.strip(),
            "primary_object": primary_object,
        }
        modules.append(
            {
                "module_name": module_name.strip(),
                "core_objects": module_objects,
                "primary_object": primary_object,
                "primary_endpoint": infer_primary_endpoint(module_stub, service_type),
                "event": infer_event_name(module_stub, service_type),
                "home_namespace": f"{root_namespace}.{module_key.replace('-', '.')}",
                "service_type": service_type,
            }
        )
    return modules


def _has_authoritative_phase1_business_truth(
    *,
    core_entities: list[str],
    dynamic_objects: list[str],
) -> bool:
    return len(unique_preserve(core_entities + dynamic_objects)) >= 3


def _module_definitions_from_business_objects(
    objects: list[str],
    root_namespace: str,
) -> list[dict[str, object]]:
    modules: list[dict[str, object]] = []
    for obj in unique_preserve(objects):
        modules.append(
            {
                "module_name": obj,
                "core_objects": [obj],
                "primary_object": obj,
                "primary_endpoint": infer_primary_endpoint({"module_name": obj, "primary_object": obj}, "domain"),
                "event": infer_event_name({"module_name": obj, "primary_object": obj}, "domain"),
                "home_namespace": f"{root_namespace}.{slugify(obj).replace('-', '.')}",
                "service_type": "domain",
            }
        )
    return modules


def parse_phase1_context(
    phase1_prd: Path,
    case_name: str,
    complexity_profile: str,
    prototype_pages: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    text = phase1_prd.read_text(encoding="utf-8")
    prototype_pages = prototype_pages or []
    domain_model = heading_section(text, "Domain Model")
    acceptance_block = heading_section(text, "Acceptance Criteria")
    requirement_block = heading_section(text, "Extended Requirement Set")
    subsystem_block = heading_section(text, "Business Subsystem Boundaries")
    module_matrix_block = heading_section(text, "Module Responsibility Matrix")
    nfr_block = heading_section(text, "Top Quality Attributes")
    business_truth_pack = parse_simple_heading_bullets(heading_block_any_level(text, "Business Truth Pack"))
    business_proof_track = parse_simple_heading_bullets(heading_block_any_level(text, "Business Proof Track"))
    chosen_business_thesis = parse_simple_heading_bullets(heading_block_any_level(text, "Chosen Business Thesis"))
    business_architecture_pressure = business_architecture_pressure_summary({"chosen_business_thesis": chosen_business_thesis})
    planning_truth_pack = parse_simple_heading_bullets(
        heading_block_any_level(text, "Planning Truth Pack"),
        list_keys={"object_chain", "state_handoff_anchors", "workflow_backbone"},
    )

    core_entities = extract_nested_bullet_values(domain_model, "core entities")
    durable_core_entities = persistent_business_objects(core_entities)
    subsystems = []
    for value in extract_nested_bullet_values(subsystem_block, "subsystems"):
        normalized = value.split(":", 1)[0].strip().replace("&", "and")
        if normalized:
            subsystems.append(normalized)
    module_names = [item[0] for item in parse_labeled_bullets(module_matrix_block, "module")]
    requirements = parse_labeled_bullets(requirement_block, "RQ")
    acceptance_items = parse_labeled_bullets(acceptance_block, "AC")
    trace_units = extract_phase1_trace_units(text)

    root_namespace = derive_root_namespace(case_name, text)
    boundary_scope = derive_boundary_scope(text)
    object_alias_hints = extract_object_alias_hints(text)
    prototype_modules = _module_definitions_from_prototype_pages(prototype_pages, root_namespace)
    prototype_objects = _objects_from_prototype_pages(prototype_pages)
    extracted_objects = persistent_business_objects(extract_dynamic_objects(text))
    authoritative_business_truth = _has_authoritative_phase1_business_truth(
        core_entities=durable_core_entities,
        dynamic_objects=extracted_objects,
    )
    try:
        extracted_modules = extract_module_definitions(text, root_namespace)
    except SystemExit:
        extracted_modules = []
    extracted_modules = sanitize_phase2_modules(extracted_modules, root_namespace=root_namespace)
    if not extracted_modules and authoritative_business_truth:
        extracted_modules = _module_definitions_from_business_objects(extracted_objects, root_namespace)
    modules = extracted_modules if authoritative_business_truth or not prototype_modules else prototype_modules
    modules = sanitize_phase2_modules(modules, root_namespace=root_namespace)
    technical_name_hints: dict[str, str] = {}
    technical_slug_hints: dict[str, str] = {}
    unresolved_technical_names: list[dict[str, str]] = []
    for module in modules:
        display_name = module_name(module)
        alias_candidates = unique_preserve(
            object_alias_hints.get(display_name, [])
            + [
                alias
                for object_name in module_core_objects(module)
                for alias in object_alias_hints.get(object_name, [])
            ]
        )
        technical_module_name = choose_technical_pascal(display_name, *alias_candidates, prefix="Module")
        primary_display = module_primary_object(module)
        primary_alias_candidates = unique_preserve(object_alias_hints.get(primary_display, []))
        technical_primary = choose_technical_pascal(primary_display, *primary_alias_candidates, prefix="Entity")
        technical_primary_slug = choose_technical_slug(primary_display, *primary_alias_candidates, prefix="entity")
        technical_module_slug = choose_technical_slug(display_name, *alias_candidates, prefix="module")
        module["technical_aliases"] = alias_candidates
        module["technical_module_name"] = technical_module_name
        module["technical_module_slug"] = technical_module_slug
        module["technical_primary_object"] = technical_primary
        module["technical_primary_slug"] = technical_primary_slug
        remember_unresolved_technical_name(
            unresolved_technical_names,
            source_label=display_name,
            technical_name=technical_module_name,
            technical_slug=technical_module_slug,
            source_kind="module",
        )
        remember_unresolved_technical_name(
            unresolved_technical_names,
            source_label=primary_display,
            technical_name=technical_primary,
            technical_slug=technical_primary_slug,
            source_kind="primary_object",
        )
        service_type = str(module.get("service_type", "domain")).strip() or "domain"
        endpoint_module = dict(module)
        endpoint_module.pop("primary_endpoint", None)
        endpoint_module.pop("event", None)
        module["primary_endpoint"] = infer_primary_endpoint(endpoint_module, service_type)
        module["event"] = infer_event_name(endpoint_module, service_type)
        module["home_namespace"] = f"{root_namespace}.{module['technical_module_slug'].replace('-', '.')}"
        technical_name_hints[display_name] = technical_primary
        technical_slug_hints[display_name] = str(module["technical_primary_slug"])
        for object_name in module_core_objects(module):
            object_technical_name = choose_technical_pascal(
                object_name,
                *object_alias_hints.get(object_name, []),
                prefix="Entity",
            )
            object_technical_slug = choose_technical_slug(
                object_name,
                *object_alias_hints.get(object_name, []),
                prefix="entity",
            )
            technical_name_hints.setdefault(
                object_name,
                object_technical_name,
            )
            technical_slug_hints.setdefault(
                object_name,
                object_technical_slug,
            )
            remember_unresolved_technical_name(
                unresolved_technical_names,
                source_label=object_name,
                technical_name=object_technical_name,
                technical_slug=object_technical_slug,
                source_kind="core_object",
            )
    dynamic_objects = persistent_business_objects(unique_preserve(
        extracted_objects + prototype_objects if authoritative_business_truth else prototype_objects + extracted_objects
    ))
    primary_object_seed = (
        persistent_business_objects(unique_preserve(durable_core_entities + extracted_objects))
        if authoritative_business_truth
        else persistent_business_objects(unique_preserve(prototype_objects + durable_core_entities))
    )
    objects = persistent_business_objects(unique_preserve(primary_object_seed + dynamic_objects))
    aggregate_target = max(profile_minimum(complexity_profile, "stage_02_aggregate_catalog"), 6)
    while dynamic_objects and len(objects) < aggregate_target + 3:
        additions = [item for item in dynamic_objects if item not in objects]
        if not additions:
            break
        objects.extend(additions)
        objects = unique_preserve(objects)

    if prototype_modules and not authoritative_business_truth:
        domains = unique_preserve([str(module["module_name"]) for module in prototype_modules])
    else:
        try:
            dynamic_domains = extract_dynamic_domains(text, root_namespace)
        except SystemExit:
            dynamic_domains = [str(module["module_name"]) for module in extracted_modules]
        domains = unique_preserve(subsystems + dynamic_domains)
        domains = unique_preserve(
            [domain for domain in domains if object_requires_persistent_table(domain)]
        )
        domain_target = max(profile_minimum(complexity_profile, "stage_02_domains"), 3)
        if dynamic_domains and len(domains) < domain_target:
            additions = [domain for domain in dynamic_domains if domain not in domains]
            if additions:
                domains.extend(additions)
                domains = unique_preserve(domains)

    semantic_support_objects = semantic_support_objects_from_names(objects)
    supplemental_objects = unique_preserve(
        semantic_support_objects
        or [f"{module_primary_object(module)} revision" for module in modules if module_primary_object(module)]
    )
    for object_name in unique_preserve(objects + supplemental_objects):
        revision_match = re.match(r"^(.*?)(?:\s+revision)$", object_name, flags=re.IGNORECASE)
        if revision_match:
            base_name = revision_match.group(1).strip()
            base_technical = technical_name_hints.get(base_name, "")
            base_slug = technical_slug_hints.get(base_name, "")
            if base_technical:
                technical_name_hints.setdefault(object_name, f"{base_technical}Revision")
            if base_slug:
                technical_slug_hints.setdefault(object_name, f"{base_slug}-revision")
        technical_name_hints.setdefault(
            object_name,
            choose_technical_pascal(object_name, *object_alias_hints.get(object_name, []), prefix="Entity"),
        )
        technical_slug_hints.setdefault(
            object_name,
            choose_technical_slug(object_name, *object_alias_hints.get(object_name, []), prefix="entity"),
        )
        remember_unresolved_technical_name(
            unresolved_technical_names,
            source_label=object_name,
            technical_name=str(technical_name_hints.get(object_name, "")),
            technical_slug=str(technical_slug_hints.get(object_name, "")),
            source_kind="business_object",
        )
    default_adr_titles = default_adr_titles_for_context(
        {
            "text": text,
            "objects": objects,
            "core_objects": primary_object_seed or unique_preserve(dynamic_objects),
            "supplemental_objects": supplemental_objects,
            "detected_core_entities": unique_preserve(core_entities),
            "domains": domains,
            "module_matrix_names": unique_preserve(
                [str(module.get("module_name") or "").strip() for module in modules if str(module.get("module_name") or "").strip()]
                + module_names
            ),
            "requirements": requirements,
            "acceptance_items": acceptance_items,
            "business_truth_pack": business_truth_pack,
            "business_proof_track": business_proof_track,
            "chosen_business_thesis": chosen_business_thesis,
            "business_architecture_pressure": business_architecture_pressure,
            "planning_truth_pack": planning_truth_pack,
        }
    )
    adr_titles = extract_dynamic_adr_titles(text, modules)
    adr_titles = unique_preserve(default_adr_titles + adr_titles)

    quality_attrs = unique_preserve(
        [line.strip("- ").strip() for line in nfr_block.splitlines() if re.match(r"^[ 	]*-[ 	]*[A-Za-z/_-]+:", line)]
        + ["reliability", "usability", "security_data_control", "maintainability"]
    )

    return {
        "text": text,
        "root_namespace": root_namespace,
        "boundary_scope": boundary_scope,
        "objects": objects,
        "core_objects": primary_object_seed or unique_preserve(dynamic_objects),
        "supplemental_objects": supplemental_objects,
        "detected_core_entities": unique_preserve(core_entities),
        "domains": domains,
        "detected_subsystems": unique_preserve(subsystems),
        "modules": modules,
        "adr_titles": adr_titles,
        "module_matrix_names": unique_preserve(
            [str(module.get("module_name") or "").strip() for module in modules if str(module.get("module_name") or "").strip()]
            + module_names
        ),
        "requirements": requirements,
        "acceptance_items": acceptance_items,
        "business_truth_pack": business_truth_pack,
        "business_proof_track": business_proof_track,
        "chosen_business_thesis": chosen_business_thesis,
        "business_architecture_pressure": business_architecture_pressure,
        "planning_truth_pack": planning_truth_pack,
        "trace_units": trace_units,
        "all_trace_rows": flatten_trace_units(trace_units),
        "quality_attributes": quality_attrs,
        "prototype_pages": prototype_pages,
        "object_alias_hints": object_alias_hints,
        "technical_name_hints": technical_name_hints,
        "technical_slug_hints": technical_slug_hints,
        "unresolved_technical_names": unresolved_technical_names,
    }

def text_has_any(text: str, *needles: str) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def build_service_specs(context: dict[str, object], complexity_profile: str) -> list[ServiceSpec]:
    root_namespace = str(context["root_namespace"])
    modules = require_context_modules(context)
    executable_modules = [
        executable
        for module in modules
        if (executable := _module_with_phase3_executable_primary(context, module)) is not None
    ]
    specs: list[ServiceSpec] = []
    seen_service_names: set[str] = set()
    target_floor = max(profile_minimum(complexity_profile, "stage_02_services"), 1)

    def add_service(spec: ServiceSpec) -> None:
        if spec.service_name in seen_service_names:
            return
        seen_service_names.add(spec.service_name)
        specs.append(spec)

    for spec in semantic_service_specs(context):
        add_service(spec)

    if len(specs) < target_floor:
        for module in executable_modules:
            service_type = str(module.get("service_type", "domain")).strip() or "domain"
            primary_object = module_primary_object(module)
            technical_object = module_technical_primary_object(module)
            technical_slug = module_technical_object_slug(module)
            if not technical_name_can_enter_phase3_surface(technical_object, technical_slug):
                continue
            home_namespace = infer_home_namespace(root_namespace, module)
            endpoint_name = infer_primary_endpoint(module, service_type)
            add_service(
                ServiceSpec(
                    infer_service_name(module, service_type),
                    module_name(module),
                    home_namespace,
                    service_type,
                    primary_object,
                    endpoint_name,
                    infer_event_name(module, service_type),
                    infer_service_purpose(module, service_type, primary_object),
                    infer_public_contract(home_namespace, primary_object, technical_object),
                    endpoint_name,
                    infer_http_method(service_type, endpoint_name),
                    infer_endpoint_path(module, service_type, primary_object),
                    technical_name=technical_object,
                    technical_slug=technical_slug,
                )
            )
            add_service(
                ServiceSpec(
                    f"{module_technical_name(module)}ReadService",
                    module_name(module),
                    home_namespace,
                    "read-assembly",
                    primary_object,
                    f"Get{technical_object}Detail",
                    f"{technical_object}DetailPrepared",
                    release_read_context_purpose(primary_object),
                    infer_public_contract(home_namespace, primary_object, technical_object),
                    f"Get{technical_object}Detail",
                    "GET",
                    infer_endpoint_path(module, "read-assembly", primary_object),
                    technical_name=technical_object,
                    technical_slug=technical_slug,
                )
            )
    if specs:
        add_service(
            ServiceSpec(
                "WorkflowAuditService",
                "workflow-audit",
                f"{root_namespace}.workflow.audit",
                "support",
                "Workflow audit record",
                "RecordWorkflowAudit",
                "WorkflowAuditRecorded",
                release_workflow_audit_purpose(),
                f"{root_namespace}.workflow.audit.WorkflowAuditRecord",
                "RecordWorkflowAudit",
                "POST",
                "/api/v1/workflow-audits",
            )
        )
        add_service(
            ServiceSpec(
                "CrossModuleReviewService",
                "cross-module-review",
                f"{root_namespace}.workflow.review",
                "read-assembly",
                "Workflow review summary",
                "ListWorkflowReviewSummaries",
                "WorkflowReviewPrepared",
                release_cross_module_review_purpose(),
                f"{root_namespace}.workflow.review.WorkflowReviewSummary",
                "ListWorkflowReviewSummaries",
                "GET",
                "/api/v1/workflow-review-summaries",
            )
        )
    return specs[: max(target_floor, len(specs))]


def select_preferred_service(services: list[ServiceSpec], preferred_names: list[str]) -> ServiceSpec:
    by_name = {service.service_name: service for service in services}
    for service_name in preferred_names:
        if service_name in by_name:
            return by_name[service_name]
    return services[0]


def select_adr_anchor_service(title: str, services: list[ServiceSpec]) -> ServiceSpec:
    lowered = title.lower()
    semantic_preference_groups = [
        (("payload", "handoff", "decision", "recommendation", "task"), ["recommendation_decision", "optimization_task"]),
        (("governance", "access", "policy", "audit", "isolation", "boundary"), ["tenant_access_policy", "tracked_scope"]),
        (("observation", "finding", "event", "query", "run"), ["observation_run", "finding_query"]),
        (("seam", "extension", "provider", "dependency"), ["tenant_access_policy", "tracked_scope", "observation_run"]),
        (("review", "uncertainty", "truth", "closure"), ["review_report"]),
    ]
    for keywords, preferred_keys in semantic_preference_groups:
        if not any(keyword in lowered for keyword in keywords):
            continue
        for preferred_key in preferred_keys:
            for service in services:
                if semantic_service_key(service) == preferred_key:
                    return service
    for service in services:
        search_space = " ".join(
            [
                service.service_name,
                service.domain,
                service.owns_or_coordinates,
                service.purpose,
                service.service_type,
            ]
        ).lower()
        if any(keyword in search_space for keyword in lowered.split()):
            return service
    return services[0]


def detect_external_integration_categories(prd_text: str) -> list[str]:
    categories: list[str] = []
    search_text = prd_text.lower()
    for name, pattern in INTEGRATION_PATTERNS:
        if re.search(pattern, search_text, flags=re.IGNORECASE):
            categories.append(name)
    return unique_preserve(categories)


def external_integration_display_name(category: str) -> str:
    return {
        "llm_provider": "LLM / Model Provider",
        "identity_provider": "Identity Provider / OIDC",
        "payment_provider": "Payment Provider",
        "message_bus": "Message Bus / Queue",
        "warehouse": "Warehouse / Analytics Store",
        "storage": "Object Storage",
        "search": "Search / Retrieval Service",
        "crm": "CRM / Business SaaS",
        "email": "Email Provider",
        "analytics": "Analytics SDK / Event Sink",
        "cms_or_store": "CMS / Store Platform",
        "webhook_or_external_api": "Webhook / External API",
    }.get(category, category.replace("_", " ").title())


def _render_stage_02_5_dependency_row(row_template: list[str], *, root_namespace: str, category: str) -> list[str]:
    return [Template(value).safe_substitute(root_namespace=root_namespace, category=category) for value in row_template]


def external_dependency_rows(categories: list[str], root_namespace: str) -> list[list[str]]:
    rows = [
        _render_stage_02_5_dependency_row(
            _STAGE_02_5_DEPENDENCY_ROW_TEMPLATES[category],
            root_namespace=root_namespace,
            category=category,
        )
        for category in categories
        if category in _STAGE_02_5_DEPENDENCY_ROW_TEMPLATES
    ]
    if rows:
        return rows
    fallback_category = categories[0] if categories else "external_dependency"
    return [
        _render_stage_02_5_dependency_row(
            _STAGE_02_5_FALLBACK_DEPENDENCY_ROW_TEMPLATE,
            root_namespace=root_namespace,
            category=fallback_category,
        )
    ]


def render_stage_02_5(*, phase1_prd: Path, context: dict[str, object], categories: list[str]) -> str:
    root_namespace = str(context["root_namespace"])
    category_names = [external_integration_display_name(category) for category in categories]
    category_summary = ", ".join(f"`{name}`" for name in category_names) if category_names else "`none-detected`"
    dependency_rows = external_dependency_rows(categories, root_namespace)

    idr_entries: list[str] = []
    adapter_rows: list[list[str]] = []
    test_rows: list[list[str]] = []
    risk_rows: list[list[str]] = []
    for idx, row in enumerate(dependency_rows, start=1):
        dependency_id = row[0]
        dependency_type = row[1]
        capability = row[2]
        consuming_module = row[3]
        internal_interface = f"{to_snake(dependency_type)}_port"
        idr_entries.append(
            "\n".join(
                [
                    f"  - idr_{idx:02d}:",
                    f"    - idr_id: `IDR-{idx:02d}`",
                    f"    - dependency_id: `{dependency_id}`",
                    "    - provider: not-selected-in-first-wave",
                    "    - integration_pattern: preserve adapter-layer seam only; do not freeze vendor SDK details before a real MVP binding exists",
                    f"    - internal_interface: `{internal_interface}`",
                    "    - authentication_method: define only when a named provider is activated; until then keep auth posture review-bound rather than fabricated",
                    "    - key_management: secret-store plus rotation policy placeholder, to be finalized only with a concrete vendor decision",
                    "    - timeout: provider-specific budget will be added when Stage-02.5 activates; current Phase-2 package only preserves the need for an explicit timeout budget",
                    "    - retry_policy: provider-specific retry, quota, and circuit-breaker rules are deferred until activation instead of being guessed in design prose",
                    "    - fallback_strategy: fail closed, surface review-bound state, and preserve audit visibility instead of inventing false availability guarantees",
                    f"    - activation_note: `{dependency_id}` remains skipped because Phase-1 identifies the capability need but does not yet bind provider, SLA, data-sovereignty, or sandbox strategy for {consuming_module}.",
                ]
            )
        )
        adapter_rows.append(
            [
                dependency_id,
                internal_interface,
                "provider endpoint to be named on activation",
                "map external timeout/rate-limit/provider errors into stable business/system error envelope",
                "contract fixture + sandbox or mock declared only when provider is selected",
            ]
        )
        test_rows.append(
            [
                dependency_id,
                "contract fixtures preserve payload shape without binding a real provider",
                "activate vendor-mock smoke tests when provider is selected",
                "run provider quota / auth / callback tests only after activation",
                "do not label the case provider-ready while Stage-02.5 is skipped",
                "tenant deny, timeout, quota exhaustion, and callback signature failure remain mandatory negative paths once activated",
            ]
        )
        risk_rows.append(
            [
                f"RISK-{idx:02d}",
                dependency_id,
                f"{capability} could become release-critical later and force a rushed provider decision if the seam is not kept explicit now.",
                "medium",
                "medium",
                "keep adapter/interface name stable, preserve review-bound language, and reopen Stage-02.5 before any provider-specific commitment",
                "phase-2 architecture owner",
            ]
        )

    stage = render_phase2_template(
        "stage-02-5-third-party-integration.md.template",
        {
            "phase1_prd": phase1_prd,
            "category_summary": category_summary,
            "dependency_manifest_table": make_markdown_table(
                ["dependency_id", "dependency_type", "capability", "consuming_module", "mvp_criticality", "current_decision", "reactivation_trigger"],
                dependency_rows,
            ),
            "integration_decision_records": chr(10).join(idr_entries),
            "adapter_specifications_table": make_markdown_table(
                ["dependency_id", "internal_port", "provider_endpoint", "error_mapping", "mock_strategy"],
                adapter_rows,
            ),
            "integration_test_strategy_table": make_markdown_table(
                ["dependency_id", "local_strategy", "ci_strategy", "staging_strategy", "production_guardrail", "negative_path_coverage"],
                test_rows,
            ),
            "risk_register_table": make_markdown_table(
                ["risk_id", "dependency_id", "risk_description", "impact", "likelihood", "mitigation", "owner"],
                risk_rows,
            ),
        },
    )
    return stage.rstrip() + "\n"


__all__ = [name for name in globals() if not name.startswith("__")]
