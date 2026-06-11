#!/usr/bin/env python3
"""
Generate a structural Phase-3 code review report from implementation evidence.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import re
from pathlib import Path
from typing import Any

from common.output_language import localize_phase3_code_review_report, resolve_output_locale
from phase3.phase3_artifact_quality import analyze_behavior_card_quality
from phase3.surface_policy import phase3_surface_exists, write_phase3_profiled_surface


PLACEHOLDER_PATTERNS = (
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r'throw new Error\("Implement [^"]+"\)', re.IGNORECASE),
)

MOCK_RUNTIME_TOKENS = (
    "generated-runtime",
    "generatedRuntime",
    "invokeGeneratedOperation",
    "annotateRuntimePayload",
    "operation-support",
    "runtime-support-kernel",
)

STACK_DEPENDENCY_RULES: dict[str, tuple[str, ...]] = {
    "nestjs": ("@nestjs/core",),
    "nextjs": ("next",),
    "vite": ("vite",),
    "react": ("react",),
    "express": ("express",),
    "fastify": ("fastify",),
}

FRONTEND_CONTRACT_META_TOKENS = (
    "Data required",
    "Data presentation",
    "Field bindings",
    "Linked contracts",
    "Implementation handoff",
    "Generated execution surfaces",
    "IA posture",
    "Page-first structure",
    "Contract-linked actions",
    "This page is generated from the frozen IA contract",
    "What This Screen Does",
    "Action Panel",
    "Runtime Result",
    "Flow Guidance",
    "Operational entrypoint",
    "Frozen IA routes",
    "Primary action:",
)

FRONTEND_API_RUNTIME_TOKENS = (
    "callApi(",
    "fetch(",
    "createApiClient(",
    "useQuery(",
    "useMutation(",
    ".request(",
)

FRONTEND_STRUCTURAL_RUNTIME_GROUPS = (
    (
        "goal",
        (
            'data-phase3-region="goal"',
            'data-phase3-region="workflow-intent"',
            'data-phase3-region="setup-flow"',
            'data-phase3-region="review-decision"',
            "const userGoal =",
        ),
    ),
    (
        "work-area",
        (
            'data-phase3-region="work-area"',
            "renderActionForm(",
            "renderActionButtons(",
            'sectionShell("Current action"',
            'sectionShell("Decision guidance"',
        ),
    ),
    (
        "data-view",
        (
            'data-phase3-region="data-view"',
            'data-phase3-region="decision-workbench"',
            'data-phase3-region="record-workbench"',
            'data-phase3-region="detail-view"',
            "renderMetricStrip(",
            "renderEvidenceDetails(",
            "renderOutcomeCard(",
        ),
    ),
    (
        "next-steps",
        (
            'data-phase3-region="next-steps"',
            "renderContinuationPanel(",
            "navigation.next_route",
        ),
    ),
)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def is_unexecutable_contract_trace_gap(row: dict[str, Any]) -> bool:
    source_type = str(row.get("source_type") or "").strip().lower()
    if source_type != "contract-trace":
        return False
    if any(str(item).strip() for item in row.get("test_targets", []) if item is not None):
        return False
    final_resolution = str(row.get("final_resolution") or "").strip().lower()
    binding_status = str(row.get("binding_status") or "").strip().lower()
    if final_resolution:
        return final_resolution == "unresolved"
    return binding_status in {"suggested", "unresolved"}


def count_unresolved_traces(trace_registry_final: dict[str, Any] | None) -> int:
    if not trace_registry_final:
        return 0
    rows = trace_registry_final.get("rows", [])
    if isinstance(rows, list):
        unresolved_count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            final_resolution = str(row.get("final_resolution") or "").strip().lower()
            binding_status = str(row.get("binding_status") or "").strip().lower()
            if final_resolution:
                if final_resolution != "unresolved":
                    continue
            elif binding_status not in {"suggested", "unresolved"}:
                continue
            if is_unexecutable_contract_trace_gap(row):
                continue
            unresolved_count += 1
        return unresolved_count
    return int(trace_registry_final.get("summary", {}).get("unresolved_source_count", 0) or 0)


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def normalize_contract_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9\u4e00-\u9fff]+", str(value).lower()))


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def source_has_editable_controls(source_bundle: str) -> bool:
    return any(token in source_bundle for token in ("renderInputField(", "renderEditableControl(", "<input", "<select", "<textarea"))


def source_has_action_execution(source_bundle: str) -> bool:
    return any(token in source_bundle for token in ("runBoundAction(", "callApi(", "actionsAndTransitions", "api_binding", "primaryCta"))


def source_preserves_workflow_context(source_bundle: str) -> bool:
    return any(
        token in source_bundle
        for token in ("readWorkflowContext(", "persistWorkflowContext(", "unlockWorkflowRoute(", "navigation.next_route", "next_route")
    )


def contract_guidance_is_satisfied(
    *,
    page: dict[str, Any],
    guidance: str,
    source_bundle: str,
    source_bundle_normalized: str,
    missing_display_fields: list[str],
    missing_input_fields: list[str],
) -> bool:
    normalized_guidance = normalize_contract_text(guidance)
    if not normalized_guidance:
        return True
    if normalized_guidance in source_bundle_normalized:
        return True

    lower_guidance = guidance.strip().lower()
    business_objects = [
        normalize_contract_text(str(item))
        for item in page.get("business_objects", [])
        if normalize_contract_text(str(item))
    ]
    action_labels = [
        normalize_contract_text(str(item.get("action") or ""))
        for item in page.get("actions_and_transitions", [])
        if isinstance(item, dict) and normalize_contract_text(str(item.get("action") or ""))
    ]

    if "在页面上明确展示这些上游信息对象" in guidance:
        entity_segment = guidance.split("：", 1)[-1] if "：" in guidance else guidance.split(":", 1)[-1]
        entities = business_objects or [
            normalize_contract_text(item)
            for item in re.split(r"[,，/]+", entity_segment)
            if normalize_contract_text(item)
        ]
        return bool(entities) and all(entity in source_bundle_normalized for entity in entities)

    if lower_guidance.startswith("support the action directly:"):
        target = normalize_contract_text(guidance.split(":", 1)[-1] if ":" in guidance else guidance)
        if not source_has_action_execution(source_bundle):
            return False
        if not action_labels:
            return True
        if not target:
            return True
        if any(target in label or label in target for label in action_labels):
            return True
        return True

    if lower_guidance == "the page must expose enough inputs or selections to complete the intended next action":
        return not missing_input_fields and source_has_editable_controls(source_bundle) and source_has_action_execution(source_bundle)

    if lower_guidance == "the primary business context and the next action must stay together on the page":
        has_context = (not missing_display_fields) or all(item in source_bundle_normalized for item in business_objects)
        has_next_action = source_has_action_execution(source_bundle) and any(
            token in source_bundle for token in ("next_route", "renderContinuationPanel(", "renderActionForm(", "renderActionButtons(")
        )
        return has_context and has_next_action and not missing_frontend_structure_groups(source_bundle)

    if lower_guidance.startswith(("carry ", "derive ")) or "workflow" in lower_guidance or "工作流" in guidance:
        return source_preserves_workflow_context(source_bundle)

    if "business review surface" in lower_guidance or lower_guidance.startswith("render this page as a business "):
        return source_has_action_execution(source_bundle) and not missing_frontend_structure_groups(source_bundle)

    return False


def missing_frontend_structure_groups(source_bundle: str) -> list[str]:
    return [
        label
        for label, tokens in FRONTEND_STRUCTURAL_RUNTIME_GROUPS
        if not any(token in source_bundle for token in tokens)
    ]


def substantive_line_count(text: str) -> int:
    count = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("//") or line.startswith("/*") or line.startswith("*") or line.startswith("*/"):
            continue
        count += 1
    return count


def contains_placeholder_content(text: str) -> bool:
    sanitized = re.sub(r"\bplaceholder\s*=\s*(\{[^}]*\}|\"[^\"]*\"|'[^']*')", "", text)
    return any(pattern.search(sanitized) for pattern in PLACEHOLDER_PATTERNS)


def method_count(text: str) -> int:
    class_match = re.search(r"export class \w+\s*{(?P<body>.*)}\s*$", text, flags=re.DOTALL)
    if not class_match:
        return 0
    body = class_match.group("body")
    return len(
        re.findall(
            r"^\s*(?:public |private |protected )?(?:async )?(?!constructor\b)[A-Za-z_][A-Za-z0-9_]*\s*\(",
            body,
            flags=re.MULTILINE,
        )
    )


METHOD_START_PATTERN = re.compile(
    r"^\s*(?:public |private |protected )?(?:async )?(?!constructor\b)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
)


def extract_method_bodies(text: str) -> list[dict[str, str]]:
    methods: list[dict[str, str]] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        match = METHOD_START_PATTERN.match(line)
        if not match or "{" not in line:
            index += 1
            continue
        brace_depth = line.count("{") - line.count("}")
        body_lines: list[str] = []
        index += 1
        while index < len(lines):
            current = lines[index]
            brace_depth += current.count("{") - current.count("}")
            if brace_depth <= 0:
                break
            body_lines.append(current)
            index += 1
        methods.append({"name": match.group("name"), "body": "\n".join(body_lines)})
        index += 1
    return methods


def substantive_method_lines(body: str) -> list[str]:
    lines: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("//") or line.startswith("/*") or line.startswith("*") or line.startswith("*/"):
            continue
        lines.append(line)
    return lines


def is_metadata_only_method(body: str) -> bool:
    lines = substantive_method_lines(body)
    if len(lines) != 2:
        return False
    assignment, delegate = lines
    if not re.match(r"const\s+\w+\s*=\s*annotateRuntimePayload\(payload,\s*\{.+\}\);$", assignment):
        return False
    return bool(
        re.match(r"return\s+this\.\w+\.\w+\(\w+\);$", delegate)
        or re.match(r'return\s+invokeGeneratedOperation\("[^"]+",\s*\w+\)(?:\s+as\s+Promise<[^>]+>)?;$', delegate)
    )


def passthrough_method_count(text: str) -> int:
    return len(
        re.findall(
            r"return this\.\w+\.\w+\(payload\);|return invokeGeneratedOperation\(\"[^\"]+\", payload\);",
            text,
        )
    )


def metadata_only_method_count(text: str) -> int:
    return sum(1 for method in extract_method_bodies(text) if is_metadata_only_method(method["body"]))


def unknown_payload_signature_count(text: str) -> int:
    return len(re.findall(r"\bpayload\s*:\s*unknown\b", text))


def contains_scaffold_marker(text: str) -> bool:
    markers = (
        "Phase-3 scaffold root",
        "Generated Phase-3 surface scaffold",
        "Replace this surface with production UI",
        "export {};",
    )
    return any(marker in text for marker in markers)


def is_runtime_kernel_backed_target(text: str) -> bool:
    return any(token in text for token in ("invokeGeneratedOperation", "generated-runtime", "operation-support", "buildOperationPlan"))


def has_domain_specific_logic(text: str) -> bool:
    if is_runtime_kernel_backed_target(text):
        return False
    method_total = method_count(text)
    if method_total == 0:
        return False
    domain_tokens = (
        "if (",
        "switch (",
        "case ",
        "throw ",
        "error_code",
        "status",
        "state",
        "transition",
        "permission",
        "tenant",
        "version",
    )
    return any(token in text for token in domain_tokens) and substantive_line_count(text) > method_total + 3


def classify_implementation_depth(target: str, text: str) -> str:
    if not target.endswith((".controller.ts", ".service.ts", ".repository.ts")):
        return "review-bound"
    if is_runtime_kernel_backed_target(text):
        return "runtime-kernel-backed"
    if has_domain_specific_logic(text):
        return "domain-specific"
    return "review-bound"


def package_dependency_names(output_dir: Path) -> set[str]:
    dependency_names: set[str] = set()
    for package_path in (
        output_dir / "package.json",
        output_dir / "apps" / "api" / "package.json",
        output_dir / "apps" / "web" / "package.json",
    ):
        payload = load_json_if_exists(package_path)
        if not payload:
            continue
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            deps = payload.get(key, {})
            if isinstance(deps, dict):
                dependency_names.update(str(name).strip() for name in deps.keys() if str(name).strip())
    return dependency_names


def yaml_field(document: str, key: str) -> str:
    match = re.search(rf'{re.escape(key)}:\s*"([^"]+)"', document)
    return match.group(1).strip() if match else ""


def compare_stack_decision_against_dependencies(output_dir: Path) -> list[dict[str, str]]:
    tech_stack_text = read_text_if_exists(output_dir / "tech-stack-decision.yaml")
    if not tech_stack_text:
        return []

    dependency_names = package_dependency_names(output_dir)
    issues: list[dict[str, str]] = []
    for key, label in (("backend_framework", "backend"), ("frontend_framework", "frontend")):
        declared = yaml_field(tech_stack_text, key).strip().lower()
        if not declared:
            continue
        required_packages = STACK_DEPENDENCY_RULES.get(declared, ())
        if required_packages and not any(package in dependency_names for package in required_packages):
            issues.append(
                {
                    "surface": label,
                    "declared_framework": declared,
                    "required_packages": ", ".join(required_packages),
                }
            )
    return issues


def operation_support_has_real_roundtrip_support(text: str) -> bool:
    required_tokens = (
        "persistRecord(",
        "loadRecordFromPersistence(",
        "listRecordsFromPersistence(",
        "persistCommandRecord(",
        'SELECT * FROM "',
        'INSERT INTO "',
    )
    return all(token in text for token in required_tokens)


def analyze_mock_runtime_dependencies(output_dir: Path) -> list[dict[str, Any]]:
    source_root = output_dir / "apps" / "api" / "src"
    if not source_root.exists():
        return []
    support_path = source_root / "common" / "operation-support.ts"
    support_text = read_text_if_exists(support_path)
    support_is_db_backed = operation_support_has_real_roundtrip_support(support_text)
    findings: list[dict[str, Any]] = []
    for path in sorted(source_root.rglob("*.ts")):
        relative = str(path.relative_to(output_dir))
        text = read_text_if_exists(path)
        matched_tokens = sorted({token for token in MOCK_RUNTIME_TOKENS if token in text})
        if not matched_tokens:
            continue
        imports_generated_runtime = bool(re.search(r'from\s+["\'][^"\']*generated-runtime(?:\.js)?["\']', text))
        invokes_generated_runtime = "invokeGeneratedOperation(" in text
        imports_operation_support = bool(re.search(r'from\s+["\'][^"\']*operation-support(?:\.js)?["\']', text))
        if relative == "apps/api/src/common/generated-runtime.ts":
            continue
        if relative == "apps/api/src/common/runtime-adapter.ts":
            continue
        if relative == "apps/api/src/common/operation-support.ts":
            if support_is_db_backed:
                continue
            findings.append(
                {
                    "path": relative,
                    "matched_tokens": matched_tokens,
                    "severity": "critical",
                    "core_path": True,
                }
            )
            continue
        if imports_generated_runtime or invokes_generated_runtime:
            findings.append(
                {
                    "path": relative,
                    "matched_tokens": matched_tokens,
                    "severity": "critical" if relative.endswith((".repository.ts", ".dao.ts", ".adapter.ts")) else "high",
                    "core_path": True,
                }
            )
            continue
        if imports_operation_support and not support_is_db_backed:
            findings.append(
                {
                    "path": relative,
                    "matched_tokens": matched_tokens,
                    "severity": "high",
                    "core_path": relative.endswith((".repository.ts", ".dao.ts", ".adapter.ts")),
                }
            )
            continue
    return findings


def fs_routes_from_app_dir(app_dir: Path, *, output_dir: Path) -> set[str]:
    routes: set[str] = set()
    if not app_dir.exists():
        return routes
    for path in app_dir.rglob("page.tsx"):
        relative = path.relative_to(app_dir)
        parts = [part for part in relative.parts[:-1] if part not in {"(app)", "(pages)"}]
        if not parts:
            routes.add("/")
            continue
        routes.add("/" + "/".join(parts))
    return routes


def literal_routes_from_frontend_sources(output_dir: Path) -> set[str]:
    routes: set[str] = set()
    frontend_root = output_dir / "apps" / "web"
    if not frontend_root.exists():
        return routes
    for path in frontend_root.rglob("*.[tj]s*"):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        text = read_text_if_exists(path)
        for match in re.findall(r'["\'](/[^"\']*)["\']', text):
            normalized = "/" + match.strip().lstrip("/")
            routes.add(normalized.rstrip("/") or "/")
    return routes


def load_ui_contract(output_dir: Path) -> dict[str, Any] | None:
    for candidate in (
        output_dir / "prototype-fallback" / "ui-delivery-contract.json",
        output_dir / "prototype-fallback" / "ui-ia-contract.json",
    ):
        payload = load_json_if_exists(candidate)
        if payload:
            return payload
    return None


def analyze_frontend_core_surface_gaps(output_dir: Path) -> list[dict[str, str]]:
    ui_contract = load_ui_contract(output_dir)
    if not ui_contract:
        return []
    pages = ui_contract.get("pages", [])
    if not isinstance(pages, list):
        return []
    implemented_routes = fs_routes_from_app_dir(output_dir / "apps" / "web" / "app", output_dir=output_dir)
    implemented_routes.update(literal_routes_from_frontend_sources(output_dir))
    missing: list[dict[str, str]] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        route = str(page.get("route") or "").strip()
        if not route:
            continue
        normalized = route.rstrip("/") or "/"
        if normalized not in implemented_routes:
            missing.append(
                {
                    "page_id": str(page.get("page_id") or ""),
                    "page_title": str(page.get("page_title") or page.get("title") or normalized),
                    "route": normalized,
                }
            )
    return missing


def frontend_route_dir(output_dir: Path, route: str) -> Path:
    normalized = route.strip().strip("/")
    if not normalized:
        return output_dir / "apps" / "web" / "app"
    return output_dir / "apps" / "web" / "app" / normalized


def read_route_source_bundle(output_dir: Path, route: str) -> str:
    route_dir = frontend_route_dir(output_dir, route)
    texts: list[str] = []
    if route_dir.exists() and route_dir.is_dir():
        for path in sorted(route_dir.rglob("*.[tj]s*")):
            if path.is_file():
                texts.append(read_text_if_exists(path))
    else:
        page_path = route_dir / "page.tsx"
        if page_path.exists():
            texts.append(read_text_if_exists(page_path))
    return "\n".join(texts)


def analyze_frontend_contract_meta_surfaces(output_dir: Path) -> list[dict[str, Any]]:
    ui_contract = load_ui_contract(output_dir)
    if not ui_contract:
        return []
    pages = ui_contract.get("pages", [])
    if not isinstance(pages, list):
        return []
    findings: list[dict[str, Any]] = []
    home_text = read_text_if_exists(output_dir / "apps" / "web" / "app" / "page.tsx")
    home_matches = sorted(token for token in FRONTEND_CONTRACT_META_TOKENS if token in home_text)
    if home_matches:
        findings.append(
            {
                "route": "/",
                "page_title": "home",
                "matched_tokens": home_matches,
            }
        )
    for page in pages:
        if not isinstance(page, dict):
            continue
        route = str(page.get("route") or "").strip()
        if not route:
            continue
        source_bundle = read_route_source_bundle(output_dir, route)
        matched_tokens = sorted(token for token in FRONTEND_CONTRACT_META_TOKENS if token in source_bundle)
        if len(matched_tokens) >= 2:
            findings.append(
                {
                    "route": route.rstrip("/") or "/",
                    "page_title": str(page.get("page_title") or page.get("title") or route),
                    "matched_tokens": matched_tokens,
                }
            )
    return findings


def analyze_frontend_operability_gaps(output_dir: Path) -> list[dict[str, str]]:
    ui_contract = load_ui_contract(output_dir)
    if not ui_contract:
        return []
    pages = ui_contract.get("pages", [])
    if not isinstance(pages, list):
        return []
    gaps: list[dict[str, str]] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        route = str(page.get("route") or "").strip()
        if not route:
            continue
        source_bundle = read_route_source_bundle(output_dir, route)
        if not source_bundle.strip():
            continue
        missing_runtime_binding = not any(token in source_bundle for token in FRONTEND_API_RUNTIME_TOKENS)
        missing_user_work_structure = bool(missing_frontend_structure_groups(source_bundle))
        if missing_runtime_binding or missing_user_work_structure:
            reason_parts: list[str] = []
            if missing_runtime_binding:
                reason_parts.append("missing runtime API binding")
            if missing_user_work_structure:
                reason_parts.append("missing goal/work/data/next-step structure")
            gaps.append(
                {
                    "route": route.rstrip("/") or "/",
                    "page_title": str(page.get("page_title") or page.get("title") or route),
                    "reason": "; ".join(reason_parts),
                }
            )
    return gaps


def analyze_frontend_contract_alignment_gaps(output_dir: Path) -> list[dict[str, Any]]:
    ui_contract = load_ui_contract(output_dir)
    if not ui_contract:
        return []
    pages = ui_contract.get("pages", [])
    if not isinstance(pages, list):
        return []
    gaps: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        route = str(page.get("route") or "").strip()
        if not route:
            continue
        source_bundle = read_route_source_bundle(output_dir, route)
        if not source_bundle.strip():
            continue
        source_bundle_normalized = normalize_contract_text(source_bundle)
        missing_display_fields = sorted(
            [
                str(field).strip()
                for field in page.get("display_fields", [])
                if str(field).strip() and str(field).strip() not in source_bundle
            ]
        )
        missing_input_fields = sorted(
            [
                str(item.get("field") or "").strip()
                for item in page.get("user_inputs", [])
                if isinstance(item, dict)
                and str(item.get("field") or "").strip()
                and str(item.get("field") or "").strip() not in source_bundle
            ]
        )
        missing_contract_guidance = sorted(
            {
                str(item).strip()
                for item in [
                    *page.get("must_show_together", []),
                    *page.get("required_user_inputs_or_confirmations", []),
                    *page.get("executor_brief", []),
                    str(page.get("context_arrives_from") or "").strip(),
                    str(page.get("context_must_continue_to") or "").strip(),
                ]
                if str(item).strip()
                and not contract_guidance_is_satisfied(
                    page=page,
                    guidance=str(item).strip(),
                    source_bundle=source_bundle,
                    source_bundle_normalized=source_bundle_normalized,
                    missing_display_fields=missing_display_fields,
                    missing_input_fields=missing_input_fields,
                )
            }
        )
        if missing_display_fields or missing_input_fields or missing_contract_guidance:
            gaps.append(
                {
                    "route": route.rstrip("/") or "/",
                    "page_title": str(page.get("page_title") or page.get("title") or route),
                    "missing_display_fields": missing_display_fields,
                    "missing_input_fields": missing_input_fields,
                    "missing_contract_guidance": missing_contract_guidance,
                }
            )
    return gaps


def analyze_implementation_targets(
    output_dir: Path,
    implementation_bindings: dict[str, Any] | None,
) -> dict[str, list[str]]:
    placeholder_targets: list[str] = []
    empty_shell_targets: list[str] = []
    thin_targets: list[str] = []
    passthrough_targets: list[str] = []
    metadata_only_targets: list[str] = []
    unknown_payload_targets: list[str] = []
    scaffold_marker_targets: list[str] = []
    runtime_kernel_backed_targets: list[str] = []
    domain_specific_targets: list[str] = []
    review_bound_depth_targets: list[str] = []
    if not implementation_bindings:
        return {
            "placeholder_targets": placeholder_targets,
            "empty_shell_targets": empty_shell_targets,
            "passthrough_targets": passthrough_targets,
            "metadata_only_targets": metadata_only_targets,
            "thin_targets": thin_targets,
            "unknown_payload_targets": unknown_payload_targets,
            "scaffold_marker_targets": scaffold_marker_targets,
            "runtime_kernel_backed_targets": runtime_kernel_backed_targets,
            "domain_specific_targets": domain_specific_targets,
            "review_bound_depth_targets": review_bound_depth_targets,
        }

    target_paths = sorted(
        {
            str(target).strip()
            for row in implementation_bindings.get("rows", [])
            if isinstance(row, dict)
            for target in row.get("implementation_targets", [])
            if str(target).strip()
        }
    )
    for target in target_paths:
        path = output_dir / target
        text = read_text_if_exists(path)
        if not text:
            continue
        if contains_placeholder_content(text):
            placeholder_targets.append(target)
        method_total = method_count(text)
        passthrough_total = passthrough_method_count(text)
        metadata_only_total = metadata_only_method_count(text)
        if target.endswith((".controller.ts", ".service.ts", ".repository.ts")) and method_total == 0:
            empty_shell_targets.append(target)
        if target.endswith((".controller.ts", ".service.ts", ".repository.ts")) and method_total > 0 and passthrough_total >= method_total:
            passthrough_targets.append(target)
        if target.endswith((".controller.ts", ".service.ts", ".repository.ts")) and method_total > 0 and metadata_only_total >= method_total:
            metadata_only_targets.append(target)
        if target.endswith((".controller.ts", ".service.ts", ".repository.ts")) and unknown_payload_signature_count(text) > 0:
            unknown_payload_targets.append(target)
        if target.endswith((".ts", ".tsx")) and substantive_line_count(text) <= 3:
            thin_targets.append(target)
        if target.endswith((".controller.ts", ".service.ts", ".repository.ts")):
            depth = classify_implementation_depth(target, text)
            if depth == "runtime-kernel-backed":
                runtime_kernel_backed_targets.append(target)
            elif depth == "domain-specific":
                domain_specific_targets.append(target)
            else:
                review_bound_depth_targets.append(target)
        if contains_scaffold_marker(text):
            scaffold_marker_targets.append(target)

    for target in ("apps/api/src/main.ts", "apps/web/app/page.tsx"):
        path = output_dir / target
        text = read_text_if_exists(path)
        if text and contains_scaffold_marker(text):
            scaffold_marker_targets.append(target)

    return {
        "placeholder_targets": sorted(set(placeholder_targets)),
        "empty_shell_targets": sorted(set(empty_shell_targets)),
        "passthrough_targets": sorted(set(passthrough_targets)),
        "metadata_only_targets": sorted(set(metadata_only_targets)),
        "thin_targets": sorted(set(thin_targets)),
        "unknown_payload_targets": sorted(set(unknown_payload_targets)),
        "scaffold_marker_targets": sorted(set(scaffold_marker_targets)),
        "runtime_kernel_backed_targets": sorted(set(runtime_kernel_backed_targets)),
        "domain_specific_targets": sorted(set(domain_specific_targets)),
        "review_bound_depth_targets": sorted(set(review_bound_depth_targets)),
    }


def find_stub_tests(output_dir: Path) -> list[str]:
    tests_root = output_dir / "tests"
    if not tests_root.exists():
        return []
    stubbed: list[str] = []
    for path in tests_root.rglob("*.test.ts"):
        text = read_text_if_exists(path)
        if contains_placeholder_content(text):
            stubbed.append(str(path.relative_to(output_dir)))
    return sorted(stubbed)


def implementation_targets_missing(output_dir: Path, implementation_bindings: dict[str, Any] | None) -> list[str]:
    if not implementation_bindings:
        return []
    missing: list[str] = []
    for row in implementation_bindings.get("rows", []):
        if not isinstance(row, dict):
            continue
        for target in row.get("implementation_targets", []):
            normalized = str(target).strip()
            if normalized and not (output_dir / normalized).exists():
                missing.append(normalized)
    return sorted(set(missing))


BEHAVIOR_CARD_STEP_RE = re.compile(r"behavior-card-step:\s*(step-\d+)", re.IGNORECASE)


ACTION_CARD_BLOCKER_PRIORITY = [
    "p1_value_to_p2_operation_resolution_matrix_missing",
    "implementation_component_catalog_missing",
    "component_action_card_obligation_matrix_missing",
    "component_action_card_obligation_missing",
    "action_card_p1_trace_missing",
    "action_card_depth_mismatch",
    "action_card_source_material_missing",
    "action_card_concrete_source_id_missing",
    "required_action_card_missing",
    "acd_required_deep_but_card_slim",
    "split_required_card_implemented_directly",
]


def extract_action_card_consistency(output_dir: Path) -> dict[str, Any] | None:
    validation_path = output_dir / "action-cards" / "validation.json"
    if not validation_path.exists():
        return None
    try:
        payload = json.loads(validation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"classification": "component_action_card_obligation_missing", "action_card_blockers": ["invalid_action_card_validation_json"]}
    blockers = [str(item) for item in payload.get("blockers", []) if str(item).strip()]
    classification = "consistent"
    for candidate in ACTION_CARD_BLOCKER_PRIORITY:
        if candidate in blockers:
            classification = candidate
            break
    if classification == "consistent" and blockers:
        classification = blockers[0]
    return {
        "classification": classification,
        "operation_count": 0,
        "missing_test_steps": [],
        "missing_implementation_steps": [],
        "action_card_blockers": blockers,
    }


def extract_behavior_card_consistency(output_dir: Path) -> dict[str, Any]:
    action_card_result = extract_action_card_consistency(output_dir)
    if action_card_result and action_card_result.get("classification") != "consistent":
        return action_card_result
    card_dir = output_dir / "behavior-cards"
    if not card_dir.exists():
        return {"classification": "consistent", "operation_count": 0, "missing_test_steps": [], "missing_implementation_steps": []}
    classifications: list[str] = []
    missing_test_steps: list[str] = []
    missing_implementation_steps: list[str] = []
    warnings: list[str] = []
    operation_count = 0
    test_text = "\n".join(read_text_if_exists(path) for path in (output_dir / "tests").rglob("*.test.ts")) if (output_dir / "tests").exists() else ""
    implementation_text = "\n".join(read_text_if_exists(path) for path in (output_dir / "apps" / "api" / "src" / "modules").rglob("*.ts")) if (output_dir / "apps" / "api" / "src" / "modules").exists() else ""
    covered_steps = sorted(set(BEHAVIOR_CARD_STEP_RE.findall(test_text)))
    implemented_steps = sorted(set(BEHAVIOR_CARD_STEP_RE.findall(implementation_text)))
    for card_path in sorted(card_dir.glob("*.behavior-card.md")):
        operation_count += 1
        card_report = analyze_behavior_card_quality(read_text_if_exists(card_path), high_risk=True)
        card_steps = [str(item) for item in card_report.get("steps", []) if str(item).strip()]
        card_warnings = [str(item) for item in card_report.get("warnings", []) if str(item).strip()]
        warnings.extend(card_warnings)
        trace_authority_status = str(card_report.get("trace_authority_status", "")).strip()
        if "trace_authority_not_registry_bound" in card_warnings or trace_authority_status in {"partial", "fallback_or_review_bound"}:
            result = {"classification": "trace_authority_gap", "missing_test_steps": [], "missing_implementation_steps": []}
        elif str(card_report.get("overall_quality_gate", "")).lower() not in {"pass", ""}:
            result = {"classification": "p2_handoff_gap", "missing_test_steps": [], "missing_implementation_steps": []}
        else:
            result = {
                "classification": "consistent",
                "missing_test_steps": [step for step in card_steps if step not in covered_steps],
                "missing_implementation_steps": [step for step in card_steps if step not in implemented_steps],
            }
            if result["missing_test_steps"]:
                result["classification"] = "action_card_test_gap"
            elif result["missing_implementation_steps"]:
                result["classification"] = "action_card_implementation_gap"
            if set(covered_steps) - set(card_steps) or set(implemented_steps) - set(card_steps):
                result["classification"] = "trace_drift"
        classifications.append(str(result.get("classification", "consistent")))
        missing_test_steps.extend(str(item) for item in result.get("missing_test_steps", []) if str(item).strip())
        missing_implementation_steps.extend(str(item) for item in result.get("missing_implementation_steps", []) if str(item).strip())
    if "trace_authority_gap" in classifications:
        classification = "trace_authority_gap"
    elif "trace_drift" in classifications:
        classification = "trace_drift"
    elif "p2_handoff_gap" in classifications:
        classification = "p2_handoff_gap"
    elif "action_card_test_gap" in classifications or "p3_test_gap" in classifications:
        classification = "action_card_test_gap"
    elif "action_card_implementation_gap" in classifications or "p3_implementation_gap" in classifications:
        classification = "action_card_implementation_gap"
    else:
        classification = "consistent"
    return {
        "classification": classification,
        "operation_count": operation_count,
        "covered_steps": covered_steps,
        "implemented_steps": implemented_steps,
        "missing_test_steps": sorted(set(missing_test_steps)),
        "missing_implementation_steps": sorted(set(missing_implementation_steps)),
        "warnings": sorted(set(warnings)),
    }


def build_findings(
    *,
    output_dir: Path,
    implementation_bindings: dict[str, Any] | None,
    trace_registry_final: dict[str, Any] | None,
    openapi_diff_report: dict[str, Any] | None,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    unresolved_trace_count = count_unresolved_traces(trace_registry_final)
    if unresolved_trace_count > 0:
        findings.append(
            {
                "severity": "critical",
                "title": "Unresolved trace subjects remain after implementation binding",
                "evidence": f"unresolved_source_count={unresolved_trace_count}",
            }
        )

    if openapi_diff_report and str(openapi_diff_report.get("verdict", "")).lower() == "fail":
        findings.append(
            {
                "severity": "critical",
                "title": "Final OpenAPI drifted incompatibly from the frozen S01 contract",
                "evidence": f"removed_operations={len(openapi_diff_report.get('removed_operations', []))}",
            }
        )

    missing_targets = implementation_targets_missing(output_dir, implementation_bindings)
    if missing_targets:
        findings.append(
            {
                "severity": "high",
                "title": "Implementation bindings reference files that were not materialized",
                "evidence": f"missing_targets={len(missing_targets)}",
            }
        )

    target_analysis = analyze_implementation_targets(output_dir, implementation_bindings)
    mock_runtime_dependencies = analyze_mock_runtime_dependencies(output_dir)
    stack_consistency_issues = compare_stack_decision_against_dependencies(output_dir)
    frontend_core_surface_gaps = analyze_frontend_core_surface_gaps(output_dir)
    frontend_contract_meta_surfaces = analyze_frontend_contract_meta_surfaces(output_dir)
    frontend_operability_gaps = analyze_frontend_operability_gaps(output_dir)
    frontend_contract_alignment_gaps = analyze_frontend_contract_alignment_gaps(output_dir)
    behavior_card_consistency = extract_behavior_card_consistency(output_dir)
    if target_analysis["placeholder_targets"]:
        findings.append(
            {
                "severity": "high",
                "title": "Implementation targets still contain TODO or not-implemented placeholders",
                "evidence": ", ".join(target_analysis["placeholder_targets"][:3]),
            }
        )
    if target_analysis["empty_shell_targets"]:
        findings.append(
            {
                "severity": "high",
                "title": "Controller/service/repository shells exist without real executable methods",
                "evidence": ", ".join(target_analysis["empty_shell_targets"][:3]),
            }
        )
    if target_analysis["passthrough_targets"]:
        findings.append(
            {
                "severity": "high",
                "title": "Layered modules remain pure passthrough adapters into generated runtime",
                "evidence": ", ".join(target_analysis["passthrough_targets"][:3]),
            }
        )
    if target_analysis["metadata_only_targets"]:
        findings.append(
            {
                "severity": "low" if phase3_surface_exists(output_dir, "generated-runtime-positioning.md") else "medium",
                "title": "Layered modules are metadata-only adapters that annotate payloads before delegating",
                "evidence": ", ".join(target_analysis["metadata_only_targets"][:3]),
            }
        )
    if target_analysis["unknown_payload_targets"]:
        findings.append(
            {
                "severity": "medium",
                "title": "Generated module methods still use generic unknown payload signatures",
                "evidence": ", ".join(target_analysis["unknown_payload_targets"][:3]),
            }
        )
    stub_tests = find_stub_tests(output_dir)
    if stub_tests:
        findings.append(
            {
                "severity": "high",
                "title": "Generated test pack still contains placeholder harness throws",
                "evidence": ", ".join(stub_tests[:3]),
            }
        )
    thin_targets = [
        target
        for target in target_analysis["thin_targets"]
        if target not in target_analysis["placeholder_targets"]
        and target not in target_analysis["empty_shell_targets"]
    ]
    if thin_targets:
        findings.append(
            {
                "severity": "medium",
                "title": "Implementation targets are unusually thin and should be reviewed for semantic depth",
                "evidence": ", ".join(thin_targets[:3]),
            }
        )
    if target_analysis["scaffold_marker_targets"]:
        findings.append(
            {
                "severity": "medium",
                "title": "Frontend or entrypoint surfaces remain scaffold-level placeholders",
                "evidence": ", ".join(target_analysis["scaffold_marker_targets"][:3]),
            }
        )
    blocking_mock_runtime_dependencies = [
        row for row in mock_runtime_dependencies if row["severity"] in {"critical", "high"} or row.get("core_path")
    ]
    if blocking_mock_runtime_dependencies:
        if any(row["severity"] == "critical" for row in mock_runtime_dependencies):
            highest = "critical"
        elif any(row["severity"] == "high" for row in mock_runtime_dependencies):
            highest = "high"
        else:
            highest = "low"
        findings.append(
            {
                "severity": highest,
                "title": "Core execution paths still depend on generated runtime or equivalent mock kernel surfaces",
                "evidence": ", ".join(row["path"] for row in blocking_mock_runtime_dependencies[:3]),
            }
        )
    if stack_consistency_issues:
        findings.append(
            {
                "severity": "high",
                "title": "Declared framework stack drifted from actual package dependencies",
                "evidence": ", ".join(
                    f"{row['surface']}={row['declared_framework']}" for row in stack_consistency_issues[:3]
                ),
            }
        )
    if frontend_core_surface_gaps:
        findings.append(
            {
                "severity": "high",
                "title": "Frontend core surfaces from the UI IA contract are missing implementation routes",
                "evidence": ", ".join(row["route"] for row in frontend_core_surface_gaps[:3]),
            }
        )
    if frontend_contract_meta_surfaces:
        findings.append(
            {
                "severity": "high",
                "title": "Frontend pages still render contract/meta scaffold content instead of user-facing MVP screens",
                "evidence": ", ".join(row["route"] for row in frontend_contract_meta_surfaces[:3]),
            }
        )
    if frontend_operability_gaps:
        findings.append(
            {
                "severity": "high",
                "title": "Frontend core surfaces do not yet expose a complete user-operable workflow structure",
                "evidence": ", ".join(
                    f"{row['route']} ({row.get('reason', 'operability gap')})" for row in frontend_operability_gaps[:3]
                ),
            }
        )
    if frontend_contract_alignment_gaps:
        findings.append(
            {
                "severity": "high",
                "title": "Frontend pages are missing IA-required display fields or input fields in implementation code",
                "evidence": ", ".join(row["route"] for row in frontend_contract_alignment_gaps[:3]),
            }
        )

    for required in (
        "apps/api/src/common/envelope.ts",
        "apps/api/src/common/errors.ts",
        "apps/api/src/common/pagination.ts",
    ):
        if not (output_dir / required).exists():
            findings.append(
                {
                    "severity": "high",
                    "title": "Common API contract support surface is missing",
                    "evidence": required,
                }
            )

    return findings


def build_report_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    findings = report.get("findings", [])
    lines = [
        "# Phase-3 Code Review Report",
        "",
        "## Summary",
        f"- critical_findings: {report['summary']['critical_findings']}",
        f"- high_findings: {report['summary']['high_findings']}",
        f"- medium_findings: {report['summary']['medium_findings']}",
        f"- low_findings: {report['summary']['low_findings']}",
        f"- reviewed_target_count: {report['summary']['reviewed_target_count']}",
        f"- metadata_only_target_count: {report['summary']['metadata_only_target_count']}",
        f"- mock_runtime_dependency_count: {report['summary']['mock_runtime_dependency_count']}",
        f"- stack_consistency_issue_count: {report['summary']['stack_consistency_issue_count']}",
        f"- frontend_core_surface_gap_count: {report['summary']['frontend_core_surface_gap_count']}",
        f"- frontend_contract_meta_surface_count: {report['summary']['frontend_contract_meta_surface_count']}",
        f"- frontend_operability_gap_count: {report['summary']['frontend_operability_gap_count']}",
        f"- frontend_contract_alignment_gap_count: {report['summary']['frontend_contract_alignment_gap_count']}",
        "",
        "## Findings",
    ]
    if not findings:
        lines.append("- none")
    else:
        for finding in findings:
            lines.append(
                f"- [{finding['severity']}] {finding['title']} ({finding['evidence']})"
            )
    lines.append("")
    return localize_phase3_code_review_report("\n".join(lines), output_locale)


def analyze_phase3_code_review(
    *,
    output_dir: Path,
    implementation_bindings: dict[str, Any] | None = None,
    trace_registry_final: dict[str, Any] | None = None,
    openapi_diff_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target_analysis = analyze_implementation_targets(output_dir, implementation_bindings)
    mock_runtime_dependencies = analyze_mock_runtime_dependencies(output_dir)
    stack_consistency_issues = compare_stack_decision_against_dependencies(output_dir)
    frontend_core_surface_gaps = analyze_frontend_core_surface_gaps(output_dir)
    frontend_contract_meta_surfaces = analyze_frontend_contract_meta_surfaces(output_dir)
    frontend_operability_gaps = analyze_frontend_operability_gaps(output_dir)
    frontend_contract_alignment_gaps = analyze_frontend_contract_alignment_gaps(output_dir)
    behavior_card_consistency = extract_behavior_card_consistency(output_dir)
    findings = build_findings(
        output_dir=output_dir,
        implementation_bindings=implementation_bindings,
        trace_registry_final=trace_registry_final,
        openapi_diff_report=openapi_diff_report,
    )
    counts = {
        "critical_findings": sum(1 for row in findings if row["severity"] == "critical"),
        "high_findings": sum(1 for row in findings if row["severity"] == "high"),
        "medium_findings": sum(1 for row in findings if row["severity"] == "medium"),
        "low_findings": sum(1 for row in findings if row["severity"] == "low"),
    }
    reviewed_target_count = len(
        {
            str(target).strip()
            for row in (implementation_bindings or {}).get("rows", [])
            if isinstance(row, dict)
            for target in row.get("implementation_targets", [])
            if str(target).strip()
        }
    )
    return {
        "summary": {
            **counts,
            "reviewed_target_count": reviewed_target_count,
            "trace_gap_count": count_unresolved_traces(trace_registry_final),
            "openapi_diff_verdict": str((openapi_diff_report or {}).get("verdict", "unknown")),
            "placeholder_target_count": len(target_analysis["placeholder_targets"]),
            "passthrough_target_count": len(target_analysis["passthrough_targets"]),
            "metadata_only_target_count": len(target_analysis["metadata_only_targets"]),
            "unknown_payload_target_count": len(target_analysis["unknown_payload_targets"]),
            "scaffold_marker_target_count": len(target_analysis["scaffold_marker_targets"]),
            "runtime_kernel_backed_target_count": len(target_analysis["runtime_kernel_backed_targets"]),
            "domain_specific_target_count": len(target_analysis["domain_specific_targets"]),
            "review_bound_depth_target_count": len(target_analysis["review_bound_depth_targets"]),
            "mock_runtime_dependency_count": len(mock_runtime_dependencies),
            "stack_consistency_issue_count": len(stack_consistency_issues),
            "frontend_core_surface_gap_count": len(frontend_core_surface_gaps),
            "frontend_contract_meta_surface_count": len(frontend_contract_meta_surfaces),
            "frontend_operability_gap_count": len(frontend_operability_gaps),
            "frontend_contract_alignment_gap_count": len(frontend_contract_alignment_gaps),
            "all_payload_typed": len(target_analysis["unknown_payload_targets"]) == 0,
            "stub_test_count": len(find_stub_tests(output_dir)),
            "behavior_card_consistency": behavior_card_consistency,
        },
        "behavior_card_consistency": behavior_card_consistency,
        "findings": findings,
        "implementation_depth": {
            "runtime_kernel_backed_targets": target_analysis["runtime_kernel_backed_targets"],
            "domain_specific_targets": target_analysis["domain_specific_targets"],
            "review_bound_targets": target_analysis["review_bound_depth_targets"],
        },
        "mock_runtime_dependencies": mock_runtime_dependencies,
        "stack_consistency_issues": stack_consistency_issues,
        "frontend_core_surface_gaps": frontend_core_surface_gaps,
        "frontend_contract_meta_surfaces": frontend_contract_meta_surfaces,
        "frontend_operability_gaps": frontend_operability_gaps,
        "frontend_contract_alignment_gaps": frontend_contract_alignment_gaps,
    }


def run_phase3_code_review(
    *,
    output_dir: Path,
    implementation_bindings: dict[str, Any] | None = None,
    trace_registry_final: dict[str, Any] | None = None,
    openapi_diff_report: dict[str, Any] | None = None,
    output_locale: str | None = None,
) -> dict[str, Any]:
    report = analyze_phase3_code_review(
        output_dir=output_dir,
        implementation_bindings=implementation_bindings,
        trace_registry_final=trace_registry_final,
        openapi_diff_report=openapi_diff_report,
    )
    json_path = output_dir / "code-review-metrics.json"
    md_path = write_phase3_profiled_surface(output_dir, "code-review-report.md", build_report_markdown(report, output_locale))
    write_text(json_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        **report["summary"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the structural Phase-3 code review")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--implementation-bindings")
    parser.add_argument("--trace-registry-final")
    parser.add_argument("--openapi-diff-report")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = run_phase3_code_review(
        output_dir=Path(args.output_dir).resolve(),
        implementation_bindings=load_json(Path(args.implementation_bindings).resolve()) if args.implementation_bindings else None,
        trace_registry_final=load_json(Path(args.trace_registry_final).resolve()) if args.trace_registry_final else None,
        openapi_diff_report=load_json(Path(args.openapi_diff_report).resolve()) if args.openapi_diff_report else None,
        output_locale=args.output_locale,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["critical_findings"] == 0 and summary["high_findings"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
