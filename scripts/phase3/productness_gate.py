#!/usr/bin/env python3
"""
Phase-3 productness gate support for frontend surface contract review.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from phase3.operable_surface_contract_metrics import evaluate_surface_contract_taxonomy


ROUTE_DISQUALIFIED_WORDS = {
    "state",
    "mutation",
    "query",
    "handler",
    "callback",
    "webhook",
    "debug",
    "console",
}

METADATA_LEAK_PATTERNS = [
    r"positioning",
    r"design_guardrails",
    r"problem_statement",
    r"primary_actor",
    r"首版承诺",
    r"不承诺",
    r"non.?goal",
]

VISIBLE_CONTRACT_META_PATTERNS = [
    r"advance-workflow-or-refresh-page-state",
    r"carry the active selection and the last completed decision into the next page",
    r"derive visible context from the prior",
    r"block-if-[a-z0-9-]+",
    r"show-inline-action-error",
    r"show-data-view-load-error",
    r"show-context-load-error",
]

BACKEND_TERMINOLOGY = [
    "payload",
    "idempotent",
    "posture",
    "tenant-acme",
    "endpoint",
    "middleware",
    "handler",
    "serializer",
    "mutation",
    "resolver",
]

DEV_TEST_DATA_PATTERNS = [
    r"tenant-acme",
    r"finding_0+\d*",
    r"scope_0+\d*",
    r"task_0+\d*",
]

GENERIC_RENDERER_PATTERNS = [
    r"renderBlueprintSurface",
    r"renderSectionCard",
    r"renderPanel\(",
    r"renderFormPanel\(",
    r"renderStatusPanel\(",
    r"sections\.map\(",
    r"information_blocks\.map\(",
]

JSON_LEAK_PATTERNS = [
    r"\{JSON\.stringify",
    r"<pre[^>]*>\s*\{?\s*JSON\.stringify",
]

ERROR_RESPONSE_LEAK_PATTERNS = [
    r"setErrorText\([^)\n;]*parsed\.payload",
    r"setErrorText\([^)\n;]*response\.body",
    r"setErrorText\([^)\n;]*parsed\.raw",
]

PROHIBITED_LAYOUT_MATCHERS: dict[str, list[str]] = {
    "api-explorer": [
        r"API Explorer",
        r"Run request",
        r"Call API",
        r"request payload",
        r"response payload",
    ],
    "raw-json-display": JSON_LEAK_PATTERNS,
    "generic-json-viewer": JSON_LEAK_PATTERNS,
    "api-response-panel": JSON_LEAK_PATTERNS,
    "debug-console": [
        r"debug console",
        r"console panel",
        r"developer console",
    ],
    "debug-panel": [
        r"debug panel",
        r"developer panel",
    ],
    "api-call-buttons": [
        r"Call API",
        r"Run request",
        r"Send request",
    ],
}

BLUEPRINT_TYPE_ALIASES = {
    "setup-flow": "setup-flow",
    "configuration": "setup-flow",
    "analysis-board": "analysis-board",
    "dashboard": "analysis-board",
    "dashboard-workbench": "analysis-board",
    "record-list": "analysis-board",
    "comparison": "analysis-board",
    "record-workbench": "record-workbench",
    "decision-workbench": "record-workbench",
    "record-editor": "record-workbench",
    "billing-settlement": "record-workbench",
    "workflow-step": "record-workbench",
    "execution-workbench": "execution-workbench",
    "queue-board": "execution-workbench",
    "review-decision": "review-decision",
    "detail-view": "detail-view",
    "entity-detail": "detail-view",
    "record-detail": "detail-view",
}

EXPECTED_RENDER_REGIONS = {
    "setup-flow": "setup-flow",
    "analysis-board": "analysis-board",
    "record-workbench": "record-workbench",
    "execution-workbench": "execution-workbench",
    "review-decision": "review-decision",
    "detail-view": "detail-view",
}

SUPPORTED_BLUEPRINT_TYPES = frozenset(EXPECTED_RENDER_REGIONS)

REQUIRED_FRONTEND_EXPERIENCE_RULE_IDS = (
    "app-posture-follows-usage-context",
    "reduce-navigation-burden",
    "offer-choices-not-questions",
    "navigation-taxonomy",
    "placemaking",
    "metadata-controlled-vocabulary",
)

DEFAULT_APP_FORBIDDEN_EXPOSURES = frozenset({
    "role_switcher",
    "review_copy",
    "contract_metadata",
    "cross_role_cta",
})

CONTRACT_METADATA_EXPOSURE_PATTERNS = [
    r"Contract anchors",
    r"Allowed roles",
    r"Service binding",
    r"Visible work areas",
    r"Primary actor",
    *VISIBLE_CONTRACT_META_PATTERNS,
]

FORBIDDEN_EXPOSURE_PATTERNS: dict[str, dict[str, Any]] = {
    "role_switcher": {
        "haystack": "content",
        "patterns": [
            r"activateRole\(",
            r'<select\s+value=\{effectiveRole\}',
            r"setCurrentRole\(event\.target\.value\)",
            r"Switch role",
            r"切换角色",
        ],
    },
    "review_copy": {
        "haystack": "visible",
        "patterns": [
            r"\bHow to start\b",
            r"Open the first workflow page",
            r"generate the workflow context",
            r"Current workflow context",
            r"workflow context remembered by the browser",
            r"pending review, so it is not ready to run yet",
            r"fresh validated implementation binding",
            r"Work from the current role workspace and keep live records connected to backend actions\.",
            r"工作区",
            r"Each page should keep the goal, work area, current data, and next steps visible together\.",
            r"工作区",
            r"Start a role session before opening the pages available to that workspace\.",
            r"工作区",
            r"These pages are limited to the business work available to the active role\.",
            r"以下页面仅显示当前角色可进入的业务页面。",
            r"\bWorking selectors\b",
            r"\bWork area\b",
            r"\bLatest result\b",
            r"\bState and guidance\b",
            r"当前筛选与选择",
            r"工作区",
            r"最新结果",
            r"状态与提示",
        ],
    },
    "contract_metadata": {
        "haystack": "visible",
        "patterns": CONTRACT_METADATA_EXPOSURE_PATTERNS,
    },
    "cross_role_cta": {
        "haystack": "visible",
        "patterns": [
            r"Switch role and continue",
            r"切换角色并继续",
            r"Continue in [A-Za-z0-9 _-]+",
            r"切换到 .* 继续",
        ],
    },
}

IMPLICIT_HANDOFF_SUMMARY_PATTERNS = [
    r"Submission hands off to the next workspace\.",
            r"工作区",
]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _file_sha256(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _surface_contract_reference(path: Path | None) -> dict[str, Any]:
    return {
        "ui_ia_contract_path": str(path.resolve()) if path is not None and path.exists() else "",
        "ui_ia_contract_sha256": _file_sha256(path),
    }


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _normalize_blueprint_type(value: str, *, preserve_unknown: bool = False) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    normalized = re.sub(r"[\s_]+", "-", raw.lower())
    resolved = BLUEPRINT_TYPE_ALIASES.get(normalized)
    if resolved:
        return resolved
    return raw if preserve_unknown else ""


def _iter_visibility_wrapped_strings(node: Any) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    if isinstance(node, dict):
        visibility = str(node.get("visibility") or "").strip().lower()
        if visibility == "agent-internal":
            text = str(node.get("text") or "").strip()
            if text:
                matches.append((visibility, text))
            items = node.get("items", [])
            if isinstance(items, list):
                matches.extend(
                    (visibility, str(item).strip())
                    for item in items
                    if str(item).strip()
                )
        for value in node.values():
            matches.extend(_iter_visibility_wrapped_strings(value))
    elif isinstance(node, list):
        for item in node:
            matches.extend(_iter_visibility_wrapped_strings(item))
    return matches


def _layout_signature(content: str) -> set[str]:
    signature: set[str] = set()
    haystack = _main_layout_haystack(content)
    signature.update(
        f"region:{match.strip().lower()}"
        for match in re.findall(r'data-phase3-region="([^"]+)"', haystack)
        if match.strip()
    )
    signature.update(
        f"helper:{match.strip()}"
        for match in re.findall(
            r"\b(sectionShell|render[A-Z][A-Za-z0-9]+)\(",
            haystack,
        )
    )
    signature.update(
        f"title:{_normalized_text(match)}"
        for match in re.findall(
            r'\b(?:sectionShell|renderMetricStrip|renderDataTable|renderEvidenceDetails|renderActionForm|renderStatusCard|renderOutcomeCard|renderTransitionTimeline|renderContinuationPanel)\("([^"]+)"',
            haystack,
        )
        if _normalized_text(match)
    )
    signature.update(
        f"grid:{match.strip()}"
        for match in re.findall(r'gridTemplateColumns:\s*"([^"]+)"', haystack)
        if match.strip()
    )
    return signature


def _main_layout_haystack(content: str) -> str:
    main_match = re.search(
        r"<main\b.*?</main>",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    return main_match.group(0) if main_match else content


def _layout_helper_signature(content: str) -> set[str]:
    haystack = _main_layout_haystack(content)
    return {
        match.strip()
        for match in re.findall(r"\b(sectionShell|render[A-Z][A-Za-z0-9]+)\(", haystack)
        if match.strip()
    }


def _visible_ui_strings(content: str) -> list[str]:
    matches: list[str] = []
    matches.extend(
        match.strip()
        for match in re.findall(r">([^<>{\n][^<>{}]*)<", content)
        if match.strip()
    )
    matches.extend(
        match.strip()
        for match in re.findall(
            r'\b(?:sectionShell|renderMetricStrip|renderDataTable|renderEvidenceDetails|renderActionForm|renderStatusCard|renderOutcomeCard|renderTransitionTimeline|renderContinuationPanel)\("([^"\n]+)"',
            content,
        )
        if match.strip()
    )
    return matches


def _page_component_files(frontend_dir: Path) -> list[Path]:
    app_dir = frontend_dir / "app"
    if not app_dir.exists():
        return []
    return sorted(path for path in app_dir.rglob("page.tsx") if path.is_file())


def check_route_names(frontend_dir: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for page_file in _page_component_files(frontend_dir):
        route_dir = page_file.parent
        if route_dir == frontend_dir / "app":
            continue
        route = route_dir.relative_to(frontend_dir / "app").as_posix()
        words = set(route.replace("-", " ").replace("_", " ").split())
        disqualified = sorted(words & ROUTE_DISQUALIFIED_WORDS)
        if disqualified:
            issues.append(
                {
                    "check": "route-name",
                    "severity": "error",
                    "path": str(page_file.relative_to(frontend_dir)),
                    "message": f"Route '{route}' contains disqualified functional words: {', '.join(disqualified)}.",
                }
            )
    return issues


def check_metadata_leakage(frontend_dir: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for tsx_file in frontend_dir.rglob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8", errors="replace")
        for pattern in METADATA_LEAK_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(
                    {
                        "check": "metadata-leakage",
                        "severity": "error",
                        "path": str(tsx_file.relative_to(frontend_dir)),
                        "pattern": pattern,
                        "match_count": len(matches),
                        "message": f"File contains agent-internal metadata pattern '{pattern}'.",
                    }
                )
        visible_content = "\n".join(_visible_ui_strings(content))
        for pattern in VISIBLE_CONTRACT_META_PATTERNS:
            matches = re.findall(pattern, visible_content, re.IGNORECASE)
            if matches:
                issues.append(
                    {
                        "check": "metadata-leakage",
                        "severity": "error",
                        "path": str(tsx_file.relative_to(frontend_dir)),
                        "pattern": pattern,
                        "match_count": len(matches),
                        "message": f"File renders internal contract meta text matching '{pattern}'.",
                    }
                )
    return issues


def check_agent_internal_visibility(frontend_dir: Path, ui_ia_contract: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    protected_strings = {
        text.strip()
        for visibility, text in _iter_visibility_wrapped_strings(ui_ia_contract)
        if visibility == "agent-internal" and len(text.strip()) >= 4
    }
    if not protected_strings:
        return issues
    normalized_strings = {
        text: _normalized_text(text)
        for text in protected_strings
        if _normalized_text(text)
    }
    for tsx_file in frontend_dir.rglob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8", errors="replace")
        normalized_content = _normalized_text(content)
        for original_text, normalized_text in normalized_strings.items():
            if normalized_text and normalized_text in normalized_content:
                issues.append(
                    {
                        "check": "agent-internal-visibility",
                        "severity": "error",
                        "path": str(tsx_file.relative_to(frontend_dir)),
                        "text": original_text,
                        "message": "File renders text from a ui-ia-contract field marked visibility='agent-internal'.",
                    }
                )
    return issues


def check_generic_renderer(frontend_dir: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for tsx_file in frontend_dir.rglob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8", errors="replace")
        for pattern in GENERIC_RENDERER_PATTERNS:
            if re.search(pattern, content):
                issues.append(
                    {
                        "check": "generic-renderer",
                        "severity": "error",
                        "path": str(tsx_file.relative_to(frontend_dir)),
                        "pattern": pattern,
                        "message": f"File uses generic renderer pattern '{pattern}'.",
                    }
                )
    return issues


def check_json_leakage(frontend_dir: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for tsx_file in frontend_dir.rglob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8", errors="replace")
        for pattern in JSON_LEAK_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                issues.append(
                    {
                        "check": "json-leakage",
                        "severity": "error",
                        "path": str(tsx_file.relative_to(frontend_dir)),
                        "pattern": pattern,
                        "message": "File renders raw JSON to the UI.",
                    }
                )
    return issues


def check_error_response_leakage(frontend_dir: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for tsx_file in frontend_dir.rglob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8", errors="replace")
        for pattern in ERROR_RESPONSE_LEAK_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                issues.append(
                    {
                        "check": "error-response-leakage",
                        "severity": "error",
                        "path": str(tsx_file.relative_to(frontend_dir)),
                        "pattern": pattern,
                        "message": "File exposes raw error payloads instead of user-friendly recovery guidance.",
                    }
                )
    return issues


def check_dev_test_data(frontend_dir: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for tsx_file in frontend_dir.rglob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8", errors="replace")
        placeholder_values = re.findall(r'placeholder=(?:"([^"\n]+)"|\{"([^"\n]+)"\})', content)
        haystacks = [value for pair in placeholder_values for value in pair if value]
        haystacks.extend(_visible_ui_strings(content))
        joined = "\n".join(haystacks)
        for pattern in DEV_TEST_DATA_PATTERNS:
            matches = re.findall(pattern, joined, re.IGNORECASE)
            if matches:
                issues.append(
                    {
                        "check": "dev-test-data",
                        "severity": "error",
                        "path": str(tsx_file.relative_to(frontend_dir)),
                        "pattern": pattern,
                        "match_count": len(matches),
                        "message": f"File contains developer test-data pattern '{pattern}'.",
                    }
                )
    return issues


def check_backend_terminology(frontend_dir: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for tsx_file in frontend_dir.rglob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8", errors="replace")
        for literal in _visible_ui_strings(content):
            for term in BACKEND_TERMINOLOGY:
                if term.lower() in literal.lower():
                    issues.append(
                        {
                            "check": "backend-terminology",
                            "severity": "error",
                            "path": str(tsx_file.relative_to(frontend_dir)),
                            "term": term,
                            "context": literal[:100],
                            "message": f"UI string contains backend term '{term}'.",
                        }
                    )
    return issues


def check_supported_blueprints(ui_ia_contract: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for page in ui_ia_contract.get("pages", []):
        if not isinstance(page, dict):
            continue
        raw_blueprint = str(page.get("page_blueprint_type") or "").strip()
        if not raw_blueprint:
            continue
        normalized = _normalize_blueprint_type(raw_blueprint, preserve_unknown=True)
        if normalized in SUPPORTED_BLUEPRINT_TYPES:
            continue
        issues.append(
            {
                "check": "unsupported-blueprint",
                "severity": "error",
                "route": str(page.get("route") or "").strip(),
                "page_id": str(page.get("page_id") or "").strip(),
                "page_blueprint_type": raw_blueprint,
                "message": f"Page blueprint '{raw_blueprint}' is not supported by the fallback renderer taxonomy.",
            }
        )
    return issues


def check_blueprint_renderer_alignment(frontend_dir: Path, ui_ia_contract: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for page in ui_ia_contract.get("pages", []):
        if not isinstance(page, dict):
            continue
        route = str(page.get("route") or "").strip().strip("/")
        if not route:
            continue
        raw_blueprint = str(page.get("page_blueprint_type") or "").strip()
        normalized = _normalize_blueprint_type(raw_blueprint, preserve_unknown=True)
        expected_region = EXPECTED_RENDER_REGIONS.get(normalized)
        if not expected_region:
            continue
        page_path = frontend_dir / "app" / route / "page.tsx"
        if not page_path.exists():
            continue
        content = page_path.read_text(encoding="utf-8", errors="replace")
        expected_literal = f'data-phase3-region="{expected_region}"'
        if expected_literal in content:
            continue
        actual_regions = sorted(set(re.findall(r'data-phase3-region="([^"]+)"', content)))
        issues.append(
            {
                "check": "blueprint-renderer-alignment",
                "severity": "error",
                "path": str(page_path.relative_to(frontend_dir)),
                "route": route,
                "page_blueprint_type": raw_blueprint or normalized,
                "expected_region": expected_region,
                "actual_regions": actual_regions,
                "message": f"Blueprint '{raw_blueprint or normalized}' does not render its expected primary region '{expected_region}'.",
            }
        )
    return issues


def check_layout_homogeneity(frontend_dir: Path, ui_ia_contract: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    pages = ui_ia_contract.get("pages", [])
    if not isinstance(pages, list) or len(pages) < 2:
        return issues
    page_patterns: dict[str, set[str]] = {}
    page_helpers: dict[str, set[str]] = {}
    page_blueprints: dict[str, str] = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        route = str(page.get("route") or "").strip().strip("/")
        if not route:
            continue
        page_blueprints[route] = _normalize_blueprint_type(str(page.get("page_blueprint_type") or "").strip(), preserve_unknown=True)
        page_path = frontend_dir / "app" / route / "page.tsx"
        if not page_path.exists():
            continue
        content = page_path.read_text(encoding="utf-8", errors="replace")
        page_patterns[route] = _layout_signature(content)
        page_helpers[route] = _layout_helper_signature(content)
    routes = sorted(page_patterns)
    for index, route_a in enumerate(routes):
        for route_b in routes[index + 1 :]:
            type_a = page_blueprints.get(route_a, "")
            type_b = page_blueprints.get(route_b, "")
            if not type_a or not type_b or type_a == type_b:
                continue
            set_a = page_patterns.get(route_a, set())
            set_b = page_patterns.get(route_b, set())
            union = set_a | set_b
            if not union:
                continue
            similarity = len(set_a & set_b) / len(union)
            helper_a = page_helpers.get(route_a, set())
            helper_b = page_helpers.get(route_b, set())
            helper_union = helper_a | helper_b
            helper_similarity = len(helper_a & helper_b) / len(helper_union) if helper_union else 0.0
            if similarity > 0.80 or helper_similarity > 0.85:
                issues.append(
                    {
                        "check": "layout-homogeneity",
                        "severity": "error",
                        "pages": [route_a, route_b],
                        "blueprint_types": [type_a, type_b],
                        "similarity": round(similarity, 2),
                        "helper_similarity": round(helper_similarity, 2),
                        "message": f"Pages '{route_a}' and '{route_b}' are too similar despite different blueprint types.",
                    }
                )
    return issues


def check_prohibited_layout_patterns(frontend_dir: Path, ui_ia_contract: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for page in ui_ia_contract.get("pages", []):
        if not isinstance(page, dict):
            continue
        route = str(page.get("route") or "").strip().strip("/")
        if not route:
            continue
        page_path = frontend_dir / "app" / route / "page.tsx"
        if not page_path.exists():
            continue
        content = page_path.read_text(encoding="utf-8", errors="replace")
        dominant_layout = page.get("dominant_layout", {})
        prohibited = dominant_layout.get("prohibited", []) if isinstance(dominant_layout, dict) else []
        for rule in prohibited:
            normalized_rule = str(rule).strip()
            if not normalized_rule:
                continue
            patterns = PROHIBITED_LAYOUT_MATCHERS.get(normalized_rule, [])
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                    issues.append(
                        {
                            "check": "dominant-layout-prohibited",
                            "severity": "error",
                            "path": str(page_path.relative_to(frontend_dir)),
                            "route": route,
                            "prohibited_pattern": normalized_rule,
                            "pattern": pattern,
                            "message": f"Page violates dominant_layout.prohibited rule '{normalized_rule}'.",
                        }
                    )
                    break
    return issues


def check_surface_contract_taxonomy(ui_ia_contract: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not ui_ia_contract:
        return (
            [
                {
                    "check": "surface-contract-missing",
                    "severity": "error",
                    "message": "ui-ia-contract.json is required for WO-15 taxonomy productness review.",
                }
            ],
            {
                "gate_pass": False,
                "checks": {
                    "core_surface_present": False,
                    "core_interaction_guess_gate": False,
                    "operable_cross_page_flow_required": False,
                    "operable_cross_page_flow_gate": False,
                    "core_surface_pass_gate": False,
                    "role_surface_alignment_gate": False,
                    "authority_status_gate": False,
                },
                "metrics": {},
                "failures": ["surface_contract_missing"],
                "warnings": [],
            },
        )

    assessment = evaluate_surface_contract_taxonomy(ui_ia_contract)
    metrics = assessment["metrics"]
    checks = assessment["checks"]
    issues: list[dict[str, Any]] = []

    if not checks.get("core_surface_present"):
        issues.append(
            {
                "check": "core-surface-presence",
                "severity": "error",
                "message": "The surface contract does not declare any core pages.",
            }
        )
    if not checks.get("core_interaction_guess_gate"):
        issues.append(
            {
                "check": "core-interaction-guess",
                "severity": "error",
                "guess_count": metrics.get("core_interaction_guess_count", 0),
                "guess_rows": metrics.get("core_interaction_guess_rows", []),
                "message": "Core interactions still require Phase-3 to guess missing page/element/binding/flow dimensions.",
            }
        )
    if not checks.get("operable_cross_page_flow_gate"):
        issues.append(
            {
                "check": "operable-cross-page-flow",
                "severity": "error",
                "flow_count": metrics.get("operable_cross_page_flow_count", 0),
                "flow_rows": metrics.get("operable_cross_page_flows", []),
                "message": "Multi-surface contract does not compile at least one operable cross-page flow with handoff context.",
            }
        )
    if not checks.get("core_surface_pass_gate"):
        issues.append(
            {
                "check": "core-surface-pass",
                "severity": "error",
                "pass_count": metrics.get("core_surface_pass_count", 0),
                "core_surface_count": metrics.get("core_surface_count", 0),
                "failures": metrics.get("core_surface_failures", []),
                "message": "One or more core pages are missing blueprint / region / binding / read-side / role evidence.",
            }
        )
    if not checks.get("role_surface_alignment_gate"):
        issues.append(
            {
                "check": "role-surface-alignment",
                "severity": "error",
                "alignment": metrics.get("role_surface_alignment", {}),
                "message": "allowed_roles, visibility_rule, rbac_policy, and denied/error semantics are not aligned for all core pages.",
            }
        )
    core_non_ready_contract_rows = [
        row for row in metrics.get("core_non_ready_contract_rows", []) if isinstance(row, dict)
    ]
    support_non_ready_contract_rows = [
        row for row in metrics.get("non_ready_contract_rows", []) if isinstance(row, dict)
    ]
    if core_non_ready_contract_rows:
        issues.append(
            {
                "check": "contract-readiness-status",
                "severity": "error",
                "rows": core_non_ready_contract_rows,
                "message": "Surface authority still contains blocked / review-bound / stale rows and cannot be treated as implementation-ready truth.",
            }
        )
    elif support_non_ready_contract_rows:
        issues.append(
            {
                "check": "support-contract-readiness-status",
                "severity": "warning",
                "rows": support_non_ready_contract_rows,
                "message": "Support-scope surfaces still contain blocked / review-bound / stale rows, but core scope remains green.",
            }
        )
    readiness_consistency_issues = [
        row for row in metrics.get("readiness_consistency_issues", []) if isinstance(row, dict)
    ]
    if readiness_consistency_issues:
        issues.append(
            {
                "check": "contract-readiness-consistency",
                "severity": "error",
                "rows": readiness_consistency_issues,
                "message": "Surface authority contains inconsistent readiness or blocked-reason signaling.",
            }
        )
    return issues, assessment


def _ui_app_shell_path(frontend_dir: Path) -> Path:
    return frontend_dir / "app" / "ui-app.tsx"


def _app_context(ui_ia_contract: dict[str, Any]) -> dict[str, Any]:
    candidate = ui_ia_contract.get("app_context")
    return candidate if isinstance(candidate, dict) else {}


def _contract_pages(ui_ia_contract: dict[str, Any]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for page in ui_ia_contract.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_role = str(page.get("page_role") or "").strip().lower()
        if page_role in {"support", "supplemental", "supporting"}:
            continue
        pages.append(page)
    return pages


def _distinct_allowed_roles(ui_ia_contract: dict[str, Any]) -> list[str]:
    roles: list[str] = []
    seen: set[str] = set()
    for workspace in _app_context(ui_ia_contract).get("available_workspaces", []):
        if not isinstance(workspace, dict):
            continue
        role = str(workspace.get("role") or "").strip()
        if role and role not in seen:
            seen.add(role)
            roles.append(role)
    for page in _contract_pages(ui_ia_contract):
        for role_value in page.get("allowed_roles", []):
            role = str(role_value or "").strip()
            if role and role not in seen:
                seen.add(role)
                roles.append(role)
    return roles


def _workflow_shell_required(ui_ia_contract: dict[str, Any]) -> bool:
    app_context = _app_context(ui_ia_contract)
    if str(app_context.get("primary_navigation_mode") or "").strip() == "workflow-progression":
        return True
    pages = _contract_pages(ui_ia_contract)
    if len(pages) < 2:
        return False
    for page in pages:
        for interaction in page.get("compiled_interactions", []):
            if not isinstance(interaction, dict):
                continue
            if str(interaction.get("next_page_id") or "").strip() or str(interaction.get("next_route") or "").strip().startswith("/"):
                return True
    return False


def _experience_contract(ui_ia_contract: dict[str, Any]) -> dict[str, Any]:
    contract = ui_ia_contract.get("frontend_experience_contract")
    if isinstance(contract, dict):
        return contract
    app_context = _app_context(ui_ia_contract)
    fallback = app_context.get("frontend_experience_contract")
    return fallback if isinstance(fallback, dict) else {}


def _app_surface_pages(ui_ia_contract: dict[str, Any]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for page in _contract_pages(ui_ia_contract):
        audience_mode = str(page.get("audience_mode") or "app").strip().lower()
        if audience_mode in {"", "app"}:
            pages.append(page)
    return pages


def _page_forbidden_exposures(page: dict[str, Any]) -> set[str]:
    audience_mode = str(page.get("audience_mode") or "app").strip().lower()
    exposures = set(DEFAULT_APP_FORBIDDEN_EXPOSURES if audience_mode in {"", "app"} else set())
    exposures.update(
        str(item).strip()
        for item in page.get("forbidden_exposure", [])
        if str(item).strip()
    )
    return exposures


def _frontend_text_haystacks(frontend_dir: Path) -> list[tuple[str, str, str]]:
    haystacks: list[tuple[str, str, str]] = []
    for tsx_file in frontend_dir.rglob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8", errors="replace")
        visible = "\n".join(_visible_ui_strings(content))
        haystacks.append((str(tsx_file.relative_to(frontend_dir)), content, visible))
    return haystacks


def check_audience_boundary_exposure(frontend_dir: Path, ui_ia_contract: dict[str, Any]) -> tuple[list[dict[str, Any]], bool | None]:
    pages = _app_surface_pages(ui_ia_contract)
    if not pages:
        return [], None
    exposures = sorted({
        exposure
        for page in pages
        for exposure in _page_forbidden_exposures(page)
        if exposure in FORBIDDEN_EXPOSURE_PATTERNS
    })
    if not exposures:
        return [], None
    violations: list[dict[str, Any]] = []
    for relative_path, content, visible in _frontend_text_haystacks(frontend_dir):
        for exposure in exposures:
            config = FORBIDDEN_EXPOSURE_PATTERNS.get(exposure, {})
            haystack = content if config.get("haystack") == "content" else visible
            matched = [
                pattern
                for pattern in config.get("patterns", [])
                if re.search(pattern, haystack, re.IGNORECASE | re.DOTALL)
            ]
            if matched:
                violations.append(
                    {
                        "path": relative_path,
                        "exposure": exposure,
                        "patterns": sorted(set(matched)),
                    }
                )
    if not violations:
        return [], True
    return [
        {
            "check": "webapp-audience-boundary",
            "severity": "error",
            "dimension": "audience-boundary",
            "violations": violations,
            "message": "App surfaces expose reviewer/internal affordances that break the intended audience boundary.",
        }
    ], False


def check_handoff_exposure(frontend_dir: Path, ui_ia_contract: dict[str, Any]) -> tuple[list[dict[str, Any]], bool | None]:
    pages = _app_surface_pages(ui_ia_contract)
    if not pages:
        return [], None
    implicit_handoff_required = any(str(page.get("handoff_visibility") or "").strip().lower() == "implicit_context" for page in pages)
    cross_role_guard_required = any("cross_role_cta" in _page_forbidden_exposures(page) for page in pages)
    if not implicit_handoff_required and not cross_role_guard_required:
        return [], None
    patterns = list(FORBIDDEN_EXPOSURE_PATTERNS["cross_role_cta"]["patterns"])
    if implicit_handoff_required:
        patterns.extend(IMPLICIT_HANDOFF_SUMMARY_PATTERNS)
    violations: list[dict[str, Any]] = []
    for relative_path, _content, visible in _frontend_text_haystacks(frontend_dir):
        matched = [pattern for pattern in patterns if re.search(pattern, visible, re.IGNORECASE | re.DOTALL)]
        if matched:
            violations.append(
                {
                    "path": relative_path,
                    "patterns": sorted(set(matched)),
                }
            )
    if not violations:
        return [], True
    return [
        {
            "check": "webapp-handoff-exposure",
            "severity": "error",
            "dimension": "handoff-exposure",
            "violations": violations,
            "message": "App surfaces expose cross-role handoff copy that should stay implicit or audience-safe.",
        }
    ], False


def _rollup_gate_dimension(values: list[bool | None]) -> bool | None:
    relevant = [value for value in values if value is not None]
    if not relevant:
        return None
    return all(value is not False for value in relevant)


def check_web_app_gate(frontend_dir: Path, ui_ia_contract: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    app_context = _app_context(ui_ia_contract)
    experience_contract = _experience_contract(ui_ia_contract)
    pages = _contract_pages(ui_ia_contract)
    ui_app_path = _ui_app_shell_path(frontend_dir)
    ui_app_text = ui_app_path.read_text(encoding="utf-8", errors="replace") if ui_app_path.exists() else ""
    page_text_by_route: dict[str, str] = {}
    for page in pages:
        route = str(page.get("route") or "").strip().strip("/")
        if not route:
            continue
        page_path = frontend_dir / "app" / route / "page.tsx"
        if page_path.exists():
            page_text_by_route[route] = page_path.read_text(encoding="utf-8", errors="replace")
    multi_role_case = len(_distinct_allowed_roles(ui_ia_contract)) > 1
    login_session_required = any(
        str(page.get("session_role_source") or "").strip().lower() == "login_session"
        and str(page.get("audience_mode") or "app").strip().lower() in {"", "app"}
        for page in pages
    )
    workflow_shell_required = _workflow_shell_required(ui_ia_contract)
    posture_id = str((experience_contract.get("app_posture") or {}).get("posture_id") or "").strip()
    audience_boundary_issues, audience_boundary_safe = check_audience_boundary_exposure(frontend_dir, ui_ia_contract)
    handoff_exposure_issues, handoff_exposure_safe = check_handoff_exposure(frontend_dir, ui_ia_contract)
    issues.extend(audience_boundary_issues)
    issues.extend(handoff_exposure_issues)

    route_guard_policy = app_context.get("route_guard_policy") if isinstance(app_context.get("route_guard_policy"), dict) else {}

    role_session_shell = None
    if multi_role_case:
        contract_has_role_shell = bool(app_context.get("available_workspaces")) and bool(app_context.get("role_scoped_entry_routes")) and isinstance(route_guard_policy, dict)
        code_has_role_shell = bool(ui_app_text) and all(token in ui_app_text for token in ("readRoleSession(", "persistRoleSession(", "entryRouteForRole("))
        role_session_shell = contract_has_role_shell and code_has_role_shell
        if not role_session_shell:
            issues.append(
                {
                    "check": "webapp-role-session-shell",
                    "severity": "error",
                    "dimension": "audience-boundary",
                    "message": "Multi-role case must resolve from authenticated role session storage instead of a switchable workspace chooser.",
                }
            )

    auth_redirect_shell = None
    auth_entry_route = str(route_guard_policy.get("auth_entry_route") or "").strip()
    denied_behavior = str(route_guard_policy.get("denied_behavior") or "").strip().lower()
    auth_entry_route_segment = auth_entry_route.strip("/")
    auth_entry_page_exists = bool(auth_entry_route_segment) and (frontend_dir / "app" / auth_entry_route_segment / "page.tsx").exists()
    if login_session_required or denied_behavior == "redirect-to-login" or auth_entry_route:
        contract_has_auth_redirect = denied_behavior == "redirect-to-login" and bool(auth_entry_route)
        code_has_auth_redirect = bool(ui_app_text) and all(
            token in ui_app_text for token in ("authEntryRoute", "window.location.assign(authEntryRoute)")
        )
        auth_redirect_shell = contract_has_auth_redirect and code_has_auth_redirect and auth_entry_page_exists
        if not auth_redirect_shell:
            issues.append(
                {
                    "check": "webapp-auth-entry-shell",
                    "severity": "error",
                    "dimension": "audience-boundary",
                    "message": "Login-session app posture must redirect to a real auth entry route instead of chooser/demo fallback.",
                }
            )

    workflow_navigation_shell = None
    if workflow_shell_required:
        contract_has_workflow_nav = str(app_context.get("primary_navigation_mode") or "").strip() == "workflow-progression" and bool(app_context.get("local_nav_items")) and isinstance(app_context.get("route_reachability_policy"), dict)
        code_has_workflow_nav = bool(ui_app_text) and all(token in ui_app_text for token in ("isRouteReachable(", "route_reachability_policy", "currentNextStep"))
        workflow_navigation_shell = contract_has_workflow_nav and code_has_workflow_nav
        if not workflow_navigation_shell:
            issues.append(
                {
                    "check": "webapp-workflow-navigation-shell",
                    "severity": "error",
                    "dimension": "nav-posture",
                    "message": "Workflow case still behaves like a flat site menu and lacks reachability-controlled navigation.",
                }
            )

    generated_id_fields_safe = None
    generated_contract_issues: list[dict[str, Any]] = []
    generated_runtime_issues: list[dict[str, Any]] = []
    generated_field_present = False
    for page in pages:
        generated_inputs = [
            item
            for item in page.get("user_inputs", [])
            if isinstance(item, dict)
            and (
                str(item.get("value_source") or "").strip() == "system-generated"
                or bool(item.get("system_generated"))
                or bool(item.get("server_assigned"))
            )
        ]
        if not generated_inputs:
            continue
        generated_field_present = True
        for item in generated_inputs:
            control = str(item.get("control") or "").strip()
            editability = str(item.get("editability") or "").strip()
            if control != "hidden" and editability not in {"hidden", "readonly", "derived"}:
                generated_contract_issues.append(
                    {
                        "route": str(page.get("route") or "").strip(),
                        "field": str(item.get("field") or "").strip(),
                    }
                )
        route_key = str(page.get("route") or "").strip().strip("/")
        page_text = page_text_by_route.get(route_key, "")
        if page_text and not ("shouldHideInput(item)" in page_text and "shouldRenderReadOnlyInput(item)" in page_text):
            generated_runtime_issues.append(
                {
                    "route": str(page.get("route") or "").strip(),
                    "path": f"app/{route_key}/page.tsx",
                }
            )
    if generated_field_present:
        generated_id_fields_safe = not generated_contract_issues and not generated_runtime_issues
        if generated_contract_issues:
            issues.append(
                {
                    "check": "webapp-generated-id-input",
                    "severity": "error",
                    "dimension": "field-semantics",
                    "rows": generated_contract_issues,
                    "message": "System-generated identifiers are still modeled as editable user inputs.",
                }
            )
        elif generated_runtime_issues:
            issues.append(
                {
                    "check": "webapp-generated-id-consumption",
                    "severity": "error",
                    "dimension": "field-semantics",
                    "rows": generated_runtime_issues,
                    "message": "Generated identifiers are present in the contract but the page renderer does not expose hide/readonly handling.",
                }
            )

    choice_controls_consumed = None
    choice_contract_present = False
    choice_issues: list[dict[str, Any]] = []
    for page in pages:
        route = str(page.get("route") or "").strip()
        route_key = route.strip("/")
        page_text = page_text_by_route.get(route_key, "")
        select_fields = []
        lookup_fields = []
        number_fields = []
        datetime_fields = []
        for item in page.get("user_inputs", []):
            if not isinstance(item, dict):
                continue
            control = str(item.get("control") or "").strip()
            datatype = str(item.get("datatype") or "").strip()
            field = str(item.get("field") or "").strip()
            if control == "select" or datatype == "enum":
                choice_contract_present = True
                select_fields.append(field)
                if not item.get("options") and not str(item.get("options_source") or "").strip():
                    choice_issues.append({"route": route, "field": field, "reason": "missing-options"})
            if control == "lookup":
                choice_contract_present = True
                lookup_fields.append(field)
            if control == "number":
                choice_contract_present = True
                number_fields.append(field)
            if control == "datetime":
                choice_contract_present = True
                datetime_fields.append(field)
        if not page_text:
            continue
        if select_fields and '<select' not in page_text:
            choice_issues.append({"route": route, "fields": select_fields, "reason": "select-renderer-missing"})
        if lookup_fields and '<select' not in page_text and 'type="search"' not in page_text:
            choice_issues.append({"route": route, "fields": lookup_fields, "reason": "lookup-renderer-missing"})
        if number_fields and 'type="number"' not in page_text:
            choice_issues.append({"route": route, "fields": number_fields, "reason": "number-renderer-missing"})
        if datetime_fields and 'type="datetime-local"' not in page_text:
            choice_issues.append({"route": route, "fields": datetime_fields, "reason": "datetime-renderer-missing"})
    if choice_contract_present:
        choice_controls_consumed = not choice_issues
        if choice_issues:
            issues.append(
                {
                    "check": "webapp-choice-controls",
                    "severity": "error",
                    "dimension": "field-semantics",
                    "rows": choice_issues,
                    "message": "Choice-like fields still collapse to generic text input or lack consumable options.",
                }
            )

    placemaking_shell = None
    if workflow_shell_required or len(pages) > 1:
        contract_has_placemaking = bool(app_context.get("placemaking_markers")) and bool(app_context.get("next_step_cta"))
        code_has_placemaking = bool(ui_app_text) and all(token in ui_app_text for token in ("currentMarker", "currentNextStep")) and (
            "You are here" in ui_app_text
            or "当前位置" in ui_app_text
            or any(("You are here" in page_text or "当前位置" in page_text) for page_text in page_text_by_route.values())
        )
        placemaking_shell = contract_has_placemaking and code_has_placemaking
        if not placemaking_shell:
            issues.append(
                {
                    "check": "webapp-placemaking-shell",
                    "severity": "error",
                    "dimension": "nav-posture",
                    "message": "Internal pages lack stable current-location / next-step placemaking markers.",
                }
            )

    posture_alignment = None
    if posture_id == "sovereign-workflow-application":
        navigation_profile = experience_contract.get("navigation_profile") if isinstance(experience_contract.get("navigation_profile"), dict) else {}
        contract_alignment = (
            str(app_context.get("primary_navigation_mode") or "").strip() == "workflow-progression"
            and bool(navigation_profile.get("local_nav_present"))
            and bool(navigation_profile.get("contextual_nav_present"))
            and bool(navigation_profile.get("next_step_present"))
            and bool(navigation_profile.get("placemaking_present"))
        )
        code_alignment = bool(ui_app_text) and all(token in ui_app_text for token in ("roleMenuItems", "currentContextualNav", "currentNextStep", "currentMarker"))
        posture_alignment = contract_alignment and code_alignment
        if not posture_alignment:
            issues.append(
                {
                    "check": "webapp-posture-alignment",
                    "severity": "error",
                    "dimension": "nav-posture",
                    "message": "Declared sovereign workflow posture is not matched by the generated navigation shell.",
                }
            )

    audience_boundary = _rollup_gate_dimension([audience_boundary_safe, role_session_shell, auth_redirect_shell])
    handoff_exposure = _rollup_gate_dimension([handoff_exposure_safe])
    field_semantics = _rollup_gate_dimension([generated_id_fields_safe, choice_controls_consumed])
    nav_posture = _rollup_gate_dimension([workflow_navigation_shell, placemaking_shell, posture_alignment])

    return issues, {
        "multi_role_case": multi_role_case,
        "workflow_shell_required": workflow_shell_required,
        "posture_id": posture_id,
        "audience_boundary": audience_boundary,
        "handoff_exposure": handoff_exposure,
        "field_semantics": field_semantics,
        "nav_posture": nav_posture,
        "role_session_shell": role_session_shell,
        "auth_redirect_shell": auth_redirect_shell,
        "login_session_required": login_session_required,
        "auth_entry_page_exists": auth_entry_page_exists if auth_redirect_shell is not None else None,
        "workflow_navigation_shell": workflow_navigation_shell,
        "generated_id_fields_safe": generated_id_fields_safe,
        "choice_controls_consumed": choice_controls_consumed,
        "placemaking_shell": placemaking_shell,
        "app_posture_alignment": posture_alignment,
    }


def summarize_frontend_experience_contract(ui_ia_contract: dict[str, Any]) -> dict[str, Any]:
    contract = ui_ia_contract.get("frontend_experience_contract")
    if not isinstance(contract, dict):
        app_context = ui_ia_contract.get("app_context")
        if isinstance(app_context, dict) and isinstance(app_context.get("frontend_experience_contract"), dict):
            contract = app_context.get("frontend_experience_contract")
        else:
            contract = {}
    rule_rows = [row for row in contract.get("rule_coverage", []) if isinstance(row, dict)] if isinstance(contract, dict) else []
    covered_rule_ids = []
    source_cards = []
    for row in rule_rows:
        rule_id = str(row.get("rule_id") or "").strip()
        source_card = str(row.get("source_card") or "").strip()
        if rule_id:
            covered_rule_ids.append(rule_id)
        if source_card:
            source_cards.append(source_card)
    missing_rule_ids = [rule_id for rule_id in REQUIRED_FRONTEND_EXPERIENCE_RULE_IDS if rule_id not in covered_rule_ids]
    app_posture = contract.get("app_posture") if isinstance(contract, dict) and isinstance(contract.get("app_posture"), dict) else {}
    prototype_review_checklist = [row for row in contract.get("prototype_review_checklist", []) if isinstance(row, dict)] if isinstance(contract, dict) else []
    browser_audit_checklist = [row for row in contract.get("browser_audit_checklist", []) if isinstance(row, dict)] if isinstance(contract, dict) else []
    return {
        "experience_contract_present": bool(contract),
        "rule_bundle_id": str(contract.get("rule_bundle_id") or "").strip() if isinstance(contract, dict) else "",
        "app_posture_present": bool(str(app_posture.get("posture_id") or "").strip()),
        "rule_traceability_present": bool(rule_rows) and all(str(row.get("source_card") or "").strip() for row in rule_rows),
        "prototype_review_checklist_present": bool(prototype_review_checklist),
        "browser_audit_checklist_present": bool(browser_audit_checklist),
        "covered_rule_ids": sorted(set(covered_rule_ids)),
        "missing_rule_ids": missing_rule_ids,
        "source_cards": sorted(set(source_cards)),
    }


def run_gate(frontend_dir: Path, ui_ia_contract_path: Path | None) -> dict[str, Any]:
    ui_ia_contract = _load_json(ui_ia_contract_path) if ui_ia_contract_path and ui_ia_contract_path.exists() else {}
    surface_contract_reference = _surface_contract_reference(ui_ia_contract_path)
    issues: list[dict[str, Any]] = []
    contract_issues, contract_assessment = check_surface_contract_taxonomy(ui_ia_contract)
    experience_rule_checks = summarize_frontend_experience_contract(ui_ia_contract)
    web_app_issues, web_app_gate_checks = check_web_app_gate(frontend_dir, ui_ia_contract)
    issues.extend(contract_issues)
    issues.extend(web_app_issues)
    issues.extend(check_route_names(frontend_dir))
    issues.extend(check_metadata_leakage(frontend_dir))
    issues.extend(check_agent_internal_visibility(frontend_dir, ui_ia_contract))
    issues.extend(check_generic_renderer(frontend_dir))
    issues.extend(check_json_leakage(frontend_dir))
    issues.extend(check_error_response_leakage(frontend_dir))
    issues.extend(check_dev_test_data(frontend_dir))
    issues.extend(check_backend_terminology(frontend_dir))
    issues.extend(check_supported_blueprints(ui_ia_contract))
    issues.extend(check_blueprint_renderer_alignment(frontend_dir, ui_ia_contract))
    issues.extend(check_layout_homogeneity(frontend_dir, ui_ia_contract))
    issues.extend(check_prohibited_layout_patterns(frontend_dir, ui_ia_contract))
    errors = [issue for issue in issues if issue.get("severity") == "error"]
    warnings = [issue for issue in issues if issue.get("severity") == "warning"]
    return {
        "gate": "phase3-productness",
        "verdict": "FAIL" if errors else "PASS",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "taxonomy_checks": contract_assessment.get("checks", {}),
        "contract_metrics": contract_assessment.get("metrics", {}),
        "contract_failures": contract_assessment.get("failures", []),
        "contract_warnings": contract_assessment.get("warnings", []),
        "experience_rule_checks": experience_rule_checks,
        "web_app_gate_checks": web_app_gate_checks,
        **surface_contract_reference,
        "ui_ia_contract_reference": surface_contract_reference,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-3 Product-ness Gate")
    parser.add_argument("--frontend-dir", type=Path, required=True)
    parser.add_argument("--ui-ia-contract", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    result = run_gate(args.frontend_dir, args.ui_ia_contract)
    output_text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(output_text + "\n", encoding="utf-8")
    print(output_text)
    return 1 if result["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
