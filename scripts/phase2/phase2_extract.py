"""Phase-2 dynamic extraction helpers for Phase-1 artifacts."""

from __future__ import annotations

import re
import sys

GENERIC_SUBSYSTEM_FIELD_KEYS = {
    "module_detail",
    "responsibility",
    "input",
    "output",
    "account_boundary",
    "interface_payloads",
    "sensitivity",
    "not_realtime_hard",
}


def _heading_block(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^###\s+(?:.+\(\s*)?{re.escape(heading)}(?:\s*\).*)?\s*$",
        flags=re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^###\s+.+$|^##\s+.+$", text[start:], flags=re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def _normalize_key(raw: str) -> str:
    value = raw.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


def _split_pipe_row(line: str) -> list[str]:
    trimmed = line.strip().strip("|")
    return [cell.strip() for cell in trimmed.split("|")]


def _coerce_table_cells(cells: list[str], header_count: int) -> list[str]:
    if len(cells) == header_count:
        return cells
    if len(cells) < header_count or header_count <= 1:
        return []
    collapsed: list[str] = [cells[0]]
    middle_source = cells[1:-1]
    middle_header_count = header_count - 2
    if middle_header_count == 1:
        collapsed.append(" | ".join(middle_source))
    else:
        collapsed.extend(middle_source[: middle_header_count - 1])
        collapsed.append(" | ".join(middle_source[middle_header_count - 1 :]))
    collapsed.append(cells[-1])
    return collapsed if len(collapsed) == header_count else []


def parse_markdown_table(block: str) -> list[dict[str, str]]:
    lines = [line.rstrip() for line in block.splitlines() if line.strip()]
    for idx in range(len(lines) - 1):
        if "|" not in lines[idx] or "|" not in lines[idx + 1]:
            continue
        if not re.match(r"^\s*\|?[\-:\s|]+\|?\s*$", lines[idx + 1]):
            continue
        headers = [_normalize_key(cell) for cell in _split_pipe_row(lines[idx])]
        rows: list[dict[str, str]] = []
        for line in lines[idx + 2 :]:
            if "|" not in line:
                break
            cells = _split_pipe_row(line)
            if len(cells) != len(headers):
                cells = _coerce_table_cells(cells, len(headers))
            if len(cells) != len(headers):
                continue
            rows.append({header: cell for header, cell in zip(headers, cells)})
        if rows:
            return rows
    return []


def _split_values(raw: str) -> list[str]:
    cleaned = raw.replace("`", "").replace("+", "/")
    parts = re.split(r"[/,;]| and |\|", cleaned)
    results: list[str] = []
    for part in parts:
        value = part.strip().strip("-").strip()
        if not value:
            continue
        results.append(value)
    return results


def extract_module_rows(prd_text: str) -> list[dict[str, str]]:
    block = (
        _heading_block(prd_text, "Information Architecture Spec Matrix")
        or _heading_block(prd_text, "Module Matrix")
        or _heading_block(prd_text, "Module Responsibility Matrix")
    )
    if not block:
        return []
    table_rows = parse_markdown_table(block)
    if table_rows:
        return table_rows
    rows: list[dict[str, str]] = []
    for match in re.finditer(r"^[ \t]*-[ \t]*(?:module_[0-9]+):[ \t]*(.+?)\s*$", block, flags=re.MULTILINE):
        rows.append({"module": match.group(1).strip()})
    return rows


def extract_subsystem_rows(prd_text: str) -> list[dict[str, object]]:
    block = _heading_block(prd_text, "Business Subsystem Boundaries")
    rows: list[dict[str, object]] = []
    if not block:
        return rows
    table_rows = parse_markdown_table(block)
    if table_rows:
        for row in table_rows:
            subsystem_name = (
                row.get("subsystem")
                or row.get("module_name")
                or row.get("module")
                or row.get("domain_name")
                or row.get("domain")
                or ""
            ).strip()
            if not subsystem_name or _normalize_key(subsystem_name) in GENERIC_SUBSYSTEM_FIELD_KEYS:
                continue
            object_source = (
                row.get("core_objects")
                or row.get("objects")
                or row.get("what")
                or row.get("owned_objects")
                or row.get("subsystem_objects")
                or row.get("subsystem_interfaces")
                or ""
            ).strip()
            rows.append(
                {
                    "module_name": subsystem_name,
                    "core_objects": _split_values(object_source),
                    "raw": object_source,
                }
            )
        if rows:
            return rows
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        value = stripped[2:].strip()
        if value == "subsystems:":
            continue
        subsystem, remainder = value.split(":", 1)
        if _normalize_key(subsystem) in GENERIC_SUBSYSTEM_FIELD_KEYS:
            continue
        objects: list[str] = []
        owns_match = re.search(r"owns\s+(.+)", remainder, flags=re.IGNORECASE)
        if owns_match:
            objects = _split_values(owns_match.group(1))
        elif remainder.strip():
            objects = _split_values(remainder)
        rows.append({"module_name": subsystem.strip(), "core_objects": objects, "raw": remainder.strip()})
    return rows


def extract_core_business_objects(prd_text: str) -> list[str]:
    values: list[str] = []
    domain_block = _heading_block(prd_text, "Domain Model Direction")
    capture = False
    for line in domain_block.splitlines():
        stripped = line.strip()
        if stripped == "- core entities:":
            capture = True
            continue
        if capture and (
            stripped.startswith("- relationship direction:")
            or stripped.startswith("- entity catalog:")
            or stripped.startswith("- object lifecycle notes:")
        ):
            break
        if capture and stripped.startswith("- "):
            values.append(stripped[2:].strip().strip("`"))
            continue
        if capture and stripped and not stripped.startswith("- "):
            break

    for heading in ("Core Business Objects", "Entity Registry"):
        block = _heading_block(prd_text, heading)
        table_rows = parse_markdown_table(block)
        for row in table_rows:
            for key in ("object", "entity", "name", "core_object"):
                if row.get(key):
                    values.append(row[key].strip().strip("`"))
    return _unique(values)


def extract_object_alias_hints(prd_text: str) -> dict[str, list[str]]:
    hints: dict[str, list[str]] = {}
    for heading in ("Core Business Objects", "Entity Registry"):
        block = _heading_block(prd_text, heading)
        for row in parse_markdown_table(block):
            primary_name = (
                row.get("object")
                or row.get("entity")
                or row.get("name")
                or row.get("core_object")
                or ""
            ).strip().strip("`")
            if not primary_name:
                continue
            candidates = _unique(
                _split_values(
                    " / ".join(
                        [
                            row.get("description", ""),
                            row.get("alias", ""),
                            row.get("english_name", ""),
                            row.get("technical_name", ""),
                        ]
                    )
                )
            )
            if candidates:
                hints.setdefault(primary_name, [])
                hints[primary_name].extend(candidates)
            module_name = (
                row.get("module_name")
                or row.get("module")
                or row.get("domain_name")
                or row.get("domain")
                or ""
            ).strip().strip("`")
            if module_name and candidates:
                hints.setdefault(module_name, [])
                hints[module_name].extend(candidates)
    return {key: _unique(values) for key, values in hints.items() if _unique(values)}


def extract_module_definitions(prd_text: str, root_namespace: str) -> list[dict[str, object]]:
    module_rows = extract_module_rows(prd_text)
    subsystem_rows = extract_subsystem_rows(prd_text)
    core_objects = extract_core_business_objects(prd_text)
    if not module_rows and not subsystem_rows:
        raise SystemExit("需要先完成 WO-02b 的 P1 动态提取：P1 PRD 缺少 IA Spec Matrix 或等效的 module/entity 定义")

    modules: list[dict[str, object]] = []
    if module_rows:
        for idx, row in enumerate(module_rows, start=1):
            name = row.get("module_name") or row.get("module") or row.get("domain_name") or row.get("domain") or f"module_{idx}"
            module_objects = _objects_for_row(row, core_objects)
            if not module_objects and idx <= len(subsystem_rows):
                module_objects = list(subsystem_rows[idx - 1]["core_objects"])
            service_type = infer_service_type(" ".join(row.values()))
            primary_object = _choose_primary_object(name, module_objects)
            modules.append(
                {
                    "module_name": name.strip(),
                    "core_objects": module_objects,
                    "primary_object": primary_object,
                    "primary_endpoint": infer_primary_endpoint(name, [primary_object], service_type),
                    "event": infer_event_name(name, [primary_object], service_type),
                    "home_namespace": f"{root_namespace}.{slugify(name).replace('-', '.')}",
                    "service_type": service_type,
                }
            )
    else:
        for row in subsystem_rows:
            name = str(row["module_name"])
            module_objects = _pick_known_objects([str(item) for item in row["core_objects"]], core_objects)
            service_type = infer_service_type(name)
            primary_object = _choose_primary_object(name, module_objects)
            modules.append(
                {
                    "module_name": name,
                    "core_objects": module_objects,
                    "primary_object": primary_object,
                    "primary_endpoint": infer_primary_endpoint(name, [primary_object], service_type),
                    "event": infer_event_name(name, [primary_object], service_type),
                    "home_namespace": f"{root_namespace}.{slugify(name).replace('-', '.')}",
                    "service_type": service_type,
                }
            )
    return modules


def extract_dynamic_domains(prd_text: str, root_namespace: str) -> list[str]:
    modules = extract_module_definitions(prd_text, root_namespace)
    return _unique([str(module["module_name"]) for module in modules])


def extract_dynamic_objects(prd_text: str) -> list[str]:
    return extract_core_business_objects(prd_text)


def extract_dynamic_adr_titles(prd_text: str, modules: list[dict[str, object]]) -> list[str]:
    titles: list[str] = []
    constraints = re.findall(r"^[ \t]*-[ \t]*(?:technical constraints|compliance/privacy constraints|resource/timeline constraints|business constraints):[ \t]*(.+?)\s*$", prd_text, flags=re.MULTILINE)
    for item in constraints:
        titles.append(_constraint_to_adr(item))

    quality_block = _heading_block(prd_text, "Top Quality Attributes")
    for row in parse_markdown_table(quality_block):
        quality = row.get("quality_attribute") or row.get("quality") or row.get("attribute")
        if quality:
            titles.append(f"{quality.strip()} assurance strategy")

    for match in re.finditer(r"decision_effect:[ \t]*(.+)$", prd_text, flags=re.MULTILINE):
        titles.append(_constraint_to_adr(match.group(1)))

    if titles:
        return _unique(titles)
    return [f"{module['module_name']} API contract strategy" for module in modules]


def extract_dynamic_primary_surfaces(prd_text: str, prototype_pages: list[dict[str, str]]) -> list[str]:
    if prototype_pages:
        return _unique([str(page.get("page_name", "")).strip() for page in prototype_pages if str(page.get("page_name", "")).strip()])

    ia_block = _heading_block(prd_text, "Information Architecture Direction")
    match = re.search(r"navigation:[ \t]*(.+)$", ia_block, flags=re.MULTILINE)
    if match:
        return _unique([item.strip() for item in match.group(1).split("/") if item.strip()])

    screen_match = re.search(r"screen/module consequence:[ \t]*(.+)$", ia_block, flags=re.MULTILINE)
    if screen_match:
        return _unique([item.strip() for item in screen_match.group(1).split("/") if item.strip()])

    table_block = _heading_block(prd_text, "Object-to-Workflow Mapping")
    rows = parse_markdown_table(table_block)
    surfaces = [row.get("workflow_step", "").strip() for row in rows if row.get("workflow_step")]
    if surfaces:
        return _unique(surfaces)

    print("WARNING: Phase-1 prototype/page map missing; inferred generic primary surfaces from IA", file=sys.stderr)
    return ["overview", "workflow", "review"]


def infer_service_type(raw: str) -> str:
    lowered = raw.lower()
    normalized = lowered.replace("review-ready", "review_ready").replace("review ready", "review_ready")
    if re.search(r"\b(task|bridge|workflow|execute)\b", normalized):
        return "transactional"
    if re.search(r"\b(sample|orchestration|cycle|run)\b", normalized):
        return "orchestration"
    if re.search(r"\b(report|review|reporting|finding|read|query|detail|search|list|dashboard|workspace)\b", normalized):
        return "read-assembly"
    if re.search(r"\b(governance|permission|policy)\b", normalized):
        return "policy"
    return "domain"


def infer_primary_endpoint(module_name: str, core_objects: list[str], service_type: str) -> str:
    primary_object = core_objects[-1] if service_type in {"orchestration", "read-assembly"} and core_objects else core_objects[0] if core_objects else module_name
    subject = to_pascal(primary_object)
    verb = {
        "transactional": "Create",
        "orchestration": "Start",
        "read-assembly": "List",
        "policy": "Get",
        "domain": "Manage",
    }.get(service_type, "Handle")
    return f"{verb}{subject}"


def infer_event_name(module_name: str, core_objects: list[str], service_type: str) -> str:
    primary_object = core_objects[-1] if service_type in {"orchestration", "read-assembly"} and core_objects else core_objects[0] if core_objects else module_name
    subject = to_pascal(primary_object)
    suffix = {
        "transactional": "Updated",
        "orchestration": "Completed",
        "read-assembly": "Prepared",
        "policy": "Evaluated",
        "domain": "Changed",
    }.get(service_type, "Changed")
    return f"{subject}{suffix}"


def _objects_for_row(row: dict[str, str], known_objects: list[str]) -> list[str]:
    objects: list[str] = []
    for key in ("core_objects", "objects", "owns", "output", "input"):
        explicit = row.get(key)
        if explicit:
            objects.extend(_pick_known_objects(_split_values(explicit), known_objects))
    values = " ".join(str(value) for value in row.values())
    for object_name in known_objects:
        if _matches_object(values, object_name):
            objects.append(object_name)
    return _unique(objects)


def _choose_primary_object(module_name: str, module_objects: list[str]) -> str:
    if not module_objects:
        return module_name.strip()
    module_key = to_snake(module_name)
    for object_name in module_objects:
        if to_snake(object_name) == module_key:
            return object_name
    return module_objects[0]


def _pick_known_objects(candidates: list[str], known_objects: list[str]) -> list[str]:
    picked: list[str] = []
    normalized_known = {to_snake(item): item for item in known_objects}
    for candidate in candidates:
        key = to_snake(candidate)
        if key in normalized_known:
            picked.append(normalized_known[key])
    return picked


def _matches_object(haystack: str, object_name: str) -> bool:
    normalized_haystack = to_snake(haystack)
    object_key = to_snake(object_name)
    if object_key in normalized_haystack:
        return True
    haystack_tokens = {_singularize(part) for part in normalized_haystack.split("_") if part}
    object_tokens = [_singularize(part) for part in object_key.split("_") if part]
    if not object_tokens:
        return False
    if object_tokens[-1] in haystack_tokens:
        return True
    meaningful = [token for token in object_tokens if len(token) > 3]
    return bool(meaningful) and all(token in haystack_tokens for token in meaningful)


def _singularize(raw: str) -> str:
    if raw.endswith("ies") and len(raw) > 3:
        return raw[:-3] + "y"
    if raw.endswith("s") and len(raw) > 2:
        return raw[:-1]
    return raw


def _constraint_to_adr(raw: str) -> str:
    cleaned = raw.strip().rstrip("。.")
    cleaned = cleaned[:1].upper() + cleaned[1:] if cleaned else "Architecture constraint"
    if not cleaned.lower().endswith(("strategy", "policy", "boundary", "contract", "decision")):
        cleaned += " strategy"
    return cleaned


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return ordered


def slugify(raw: str) -> str:
    chars: list[str] = []
    last_dash = False
    for ch in raw.strip().lower():
        if ch.isalnum():
            chars.append(ch)
            last_dash = False
        elif not last_dash:
            chars.append("-")
            last_dash = True
    return "".join(chars).strip("-") or "module"


def to_snake(raw: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw)
    value = value.replace("&", " and ")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if value:
        return value.lower()
    unicode_tokens = [f"u{ord(ch):04x}" for ch in raw if ch.isalnum()]
    return "_".join(unicode_tokens) or "entity"


def to_pascal(raw: str) -> str:
    words = re.split(r"[^A-Za-z0-9]+", raw)
    identifier = "".join(word[:1].upper() + word[1:] for word in words if word)
    if identifier:
        return identifier
    unicode_tokens = [f"U{ord(ch):04X}" for ch in raw if ch.isalnum()]
    return "".join(unicode_tokens) or "Entity"
