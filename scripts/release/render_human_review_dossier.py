#!/usr/bin/env python3
"""Render an explicit P1-P3 human-review dossier as one offline HTML document."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Sequence
from urllib.parse import quote, unquote, urlsplit, urlunsplit

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.script_data_assets import load_script_text_asset
from common.human_review_terminology import (
    REVIEW_BOUND_DISPLAY,
    localize_review_payload,
    localize_review_terms,
)
from common.human_review_map_contract import (
    ARCHITECTURE_NODE_STATES,
    RESPONSIBILITY_STATES,
    ROLE_EXPECTED_REVIEW_BUNDLE,
    ROLE_EXPECTED_REVIEW_VIEWS,
    SCENARIO_STEP_TONES,
    SEQUENCE_STEP_KINDS,
    SERVICE_OPERATION_KINDS,
)
from release.render_human_review_portal import (
    DEFAULT_PORTAL_PATH,
    DOSSIER_MANIFEST_FILENAME,
    MANIFEST_FILENAME,
    PORTAL_SCHEMA_VERSION,
    PortalError,
    discover_human_review_html,
    is_generated_human_review_dossier,
    refresh_human_review_portal,
    validate_portal_destination,
)
from release.render_reader_preview import (
    PreviewHeading,
    PreviewValidationError,
    render_markdown,
    resolve_accepted_reader,
)


WFF_SCRIPT_DATA_ASSETS = ("scripts/release/data/human-review-dossier.html.template",)

DOSSIER_SCHEMA_VERSION = "human-review-dossier-manifest.v1"
DOSSIER_MARKER = "human-review-dossier.v1"
DEFAULT_DOSSIER_MANIFEST_PATH = Path("human-review") / DOSSIER_MANIFEST_FILENAME
REQUIRED_ROLES = (
    "prd",
    "product-diagram",
    "esp",
    "architecture-diagram",
    "action-cards",
)
OPTIONAL_ROLES = ("impact-diagram",)
ROLE_EXPECTED_KIND = {
    "prd": "p1-prd",
    "esp": "p2-esp",
    "action-cards": "p3-action-card",
}
ROLE_EXPECTED_MAP_TYPE = {
    "product-diagram": "p1_business",
    "architecture-diagram": "p2_architecture_data",
    "impact-diagram": "px_current_state_impact",
}
ROLE_LABELS = {
    "prd": "PRD",
    "product-diagram": "产品与业务图",
    "esp": "ESP",
    "architecture-diagram": "架构与数据图",
    "action-cards": "Action Cards",
    "impact-diagram": "影响图",
}
TOP_NAV_LABELS = {
    "prd": "PRD",
    "product-diagram": "P1 业务图",
    "esp": "ESP",
    "architecture-diagram": "P2 架构图",
    "action-cards": "Action Cards",
    "impact-diagram": "影响图",
}
DOCUMENT_DISPLAY_TITLES = {
    "prd": "产品需求文档（PRD）",
    "esp": "工程规格说明（ESP）",
}
REDUNDANT_DOCUMENT_H1_TITLES = {
    "prd": {"PRD", "产品需求文档"},
    "esp": {"ESP", "Engineering Spec Pack", "工程规格说明"},
}
PROJECTION_REVIEW_TITLE_PATTERN = re.compile(r"审阅|审计文档|最终一致性")
MARKDOWN_HEADING_PATTERN = re.compile(
    r"^(?P<marks>#{1,6})[ \t]+(?P<title>.+?)[ \t]*$"
)
HEADING_NUMBER_PATTERN = re.compile(
    r"^(?:\d+(?:\.\d+)*(?:[A-Z])?[.、:：]?|[A-Z][.、:：])[ \t]+"
)
ALPHABETICAL_HEADING_NUMBER_PATTERN = re.compile(r"^[A-Z][.、:：][ \t]+")
OUTLINE_NUMBER_PATTERN = re.compile(
    r"^(?P<number>\d+(?:\.\d+)*(?:[A-Z])?[.、:：]?|[A-Z][.、:：])[ \t]+(?P<label>.+)$"
)
SOURCE_ID_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*\Z")
ACTION_COMPONENT_PATTERN = re.compile(r"\bP2-CMP-[A-Z0-9._:-]+\b", re.IGNORECASE)
ACTION_CARD_APPENDIX_HEADING_PATTERN = re.compile(
    r"^(#{2,6})\s+(?:附录\s*)?([A-Z])(?:[.、:：])\s+.+$",
    re.MULTILINE,
)
DOCUMENT_APPENDIX_HEADING_PATTERN = re.compile(
    r"^#{1,3}\s+"
    r"(?:(?:\d+(?:\.\d+)*(?:[A-Z])?|[A-Z])[.、:：]?\s+)?"
    r"(?:(?:技术|审计|证据|实现)?附录(?:$|[\s:：])|.+(?:附录|Appendix)\s*$)",
    re.MULTILINE | re.IGNORECASE,
)


class DossierError(ValueError):
    """The requested dossier does not meet its source and projection contract."""


@dataclass(frozen=True)
class ValidatedDossier:
    case_root: Path
    manifest_path: Path
    output_path: Path
    title: str
    locale: str
    sections: tuple[dict[str, Any], ...]
    originals: tuple[dict[str, Any], ...]
    action_card_count: int


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DossierError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: object, field: str, *, required: bool = False) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list):
        raise DossierError(f"{field} must be a list")
    result = [_nonempty_string(item, f"{field} item") for item in value]
    if required and not result:
        raise DossierError(f"{field} must not be empty")
    return result


def _object(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DossierError(f"{field} must be an object")
    return value


def _object_list(value: object, field: str, *, required: bool = True) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise DossierError(f"{field} must be a list")
    if required and not value:
        raise DossierError(f"{field} must not be empty")
    return [_object(item, f"{field}[{index}]") for index, item in enumerate(value, start=1)]


def _anchor_id(value: object, field: str) -> str:
    identifier = _nonempty_string(value, field)
    if not SOURCE_ID_PATTERN.fullmatch(identifier):
        raise DossierError(
            f"{field} must start with a letter and use only letters, digits, '_' or '-'"
        )
    return identifier


def _enum_string(value: object, field: str, allowed: set[str]) -> str:
    item = _nonempty_string(value, field)
    if item not in allowed:
        raise DossierError(f"{field} must be one of: {', '.join(sorted(allowed))}")
    return item


def _require_unique(identifier: str, seen: set[str], field: str) -> None:
    if identifier in seen:
        raise DossierError(f"{field} contains duplicate id: {identifier}")
    seen.add(identifier)


def _resolve_case_file(case_root: Path, value: object, field: str) -> Path:
    raw_path = _nonempty_string(value, field)
    candidate = Path(raw_path)
    if candidate.is_absolute():
        raise DossierError(f"{field} must be relative to the case root")
    resolved = (case_root / candidate).resolve()
    if not _inside(resolved, case_root):
        raise DossierError(f"{field} escapes the case root")
    if not resolved.is_file():
        raise DossierError(f"{field} is missing: {candidate.as_posix()}")
    return resolved


def _resolve_validation_card_path(case_root: Path, value: object, field: str) -> Path:
    raw_path = _nonempty_string(value, field)
    candidate = Path(raw_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (case_root / candidate).resolve()
    if not _inside(resolved, case_root):
        raise DossierError(f"{field} escapes the case root")
    if not resolved.is_file():
        raise DossierError(f"{field} is missing: {raw_path}")
    return resolved


def _relative_path(path: Path, case_root: Path) -> str:
    return path.relative_to(case_root).as_posix()


def _relative_href(target: Path, output_path: Path) -> str:
    relative = os.path.relpath(target, start=output_path.parent).replace(os.sep, "/")
    return quote(relative, safe="/._-~#?=&")


def _load_map_svg_renderer() -> Callable[..., str]:
    map_scripts = Path(__file__).resolve().parents[2] / "skills" / "wff-interaction-map" / "scripts"
    renderer_path = map_scripts / "render_interactive_map.py"
    if not renderer_path.is_file():
        raise DossierError(f"interaction-map renderer is unavailable: {renderer_path}")
    if str(map_scripts) not in sys.path:
        sys.path.insert(0, str(map_scripts))
    try:
        from render_interactive_map import render_embedded_svg
    except (ImportError, OSError) as exc:  # pragma: no cover - package boundary failure
        raise DossierError(f"interaction-map renderer could not be imported: {exc}") from exc
    return render_embedded_svg


def _marked_artifacts(case_root: Path) -> dict[Path, str]:
    return {
        item.path.resolve(): item.kind
        for item in discover_human_review_html(case_root, portal_path=case_root / DEFAULT_PORTAL_PATH)
    }


def _optional_marked_html_path(
    case_root: Path,
    source: dict[str, Any],
    *,
    field: str,
    expected_kind: str,
    marked: dict[Path, str],
    required: bool = False,
) -> Path | None:
    raw = source.get("standalone_html_path")
    if raw is None and not required:
        return None
    path = _resolve_case_file(case_root, raw, field)
    if path.suffix.lower() != ".html":
        raise DossierError(f"{field} must refer to an HTML artifact")
    actual_kind = marked.get(path)
    if actual_kind != expected_kind:
        raise DossierError(f"{field} is not a marked {expected_kind} HTML artifact")
    return path


def _normalize_artifact(
    case_root: Path,
    source: object,
    *,
    field: str,
    expected_kind: str,
    marked: dict[Path, str],
) -> dict[str, Any]:
    payload = _object(source, field)
    identity = _nonempty_string(payload.get("identity"), f"{field}.identity")
    if identity not in {"accepted-reader", "canonical", "human-projection"}:
        raise DossierError(
            f"{field}.identity must be accepted-reader, canonical, or human-projection"
        )
    kind = _nonempty_string(payload.get("kind"), f"{field}.kind")
    if kind != expected_kind:
        raise DossierError(f"{field}.kind must be {expected_kind}")
    path = _resolve_case_file(case_root, payload.get("path"), f"{field}.path")
    canonical_path = _resolve_case_file(
        case_root,
        payload.get("canonical_path"),
        f"{field}.canonical_path",
    )
    if path.suffix.lower() != ".md" or canonical_path.suffix.lower() != ".md":
        raise DossierError(f"{field} must reference Markdown artifacts")
    if identity == "canonical":
        if path != canonical_path:
            raise DossierError(f"{field}.path must equal canonical_path for canonical identity")
    elif identity == "accepted-reader":
        try:
            target = resolve_accepted_reader(case_root, path)
        except PreviewValidationError as exc:
            raise DossierError(f"{field} is not an accepted reader: {exc}") from exc
        if target.kind != expected_kind:
            raise DossierError(f"{field} reader kind does not match {expected_kind}")
        if target.canonical_path != canonical_path:
            raise DossierError(f"{field} canonical identity does not match the accepted reader")

    standalone_path = _optional_marked_html_path(
        case_root,
        payload,
        field=f"{field}.standalone_html_path",
        expected_kind="reader-preview",
        marked=marked,
    )
    return {
        "kind": kind,
        "identity": identity,
        "path": path,
        "canonical_path": canonical_path,
        "standalone_html_path": standalone_path,
    }


def _normalize_markdown_section(
    case_root: Path,
    section: dict[str, Any],
    *,
    marked: dict[Path, str],
) -> dict[str, Any]:
    role = _nonempty_string(section.get("role"), "section.role")
    expected_kind = ROLE_EXPECTED_KIND[role]
    return {
        "id": _nonempty_string(section.get("id"), "section.id"),
        "role": role,
        "title": _nonempty_string(section.get("title"), f"{role}.title"),
        "artifact": _normalize_artifact(
            case_root,
            section.get("artifact"),
            field=f"{role}.artifact",
            expected_kind=expected_kind,
            marked=marked,
        ),
    }


def _normalize_review_view_common(
    view: dict[str, Any],
    *,
    field: str,
    expected_type: str,
) -> dict[str, Any]:
    view_type = _nonempty_string(view.get("type"), f"{field}.type")
    if view_type != expected_type:
        raise DossierError(f"{field}.type must be {expected_type}")
    return {
        "type": view_type,
        "id": _anchor_id(view.get("id"), f"{field}.id"),
        "title": _nonempty_string(view.get("title"), f"{field}.title"),
        "summary": _nonempty_string(view.get("summary"), f"{field}.summary"),
        "tag": _nonempty_string(view.get("tag"), f"{field}.tag"),
        "diagram_title": _nonempty_string(
            view.get("diagram_title"), f"{field}.diagram_title"
        ),
        "diagram_note": _nonempty_string(
            view.get("diagram_note"), f"{field}.diagram_note"
        ),
        "caption": _nonempty_string(view.get("caption"), f"{field}.caption"),
        "source_refs": _string_list(
            view.get("source_refs"), f"{field}.source_refs", required=True
        ),
    }


def _normalize_business_landscape(view: dict[str, Any], field: str) -> dict[str, Any]:
    normalized = _normalize_review_view_common(
        view,
        field=field,
        expected_type="business-landscape",
    )
    roles: list[dict[str, str]] = []
    role_ids: set[str] = set()
    for index, role in enumerate(_object_list(view.get("roles"), f"{field}.roles"), start=1):
        role_field = f"{field}.roles[{index}]"
        role_id = _anchor_id(role.get("id"), f"{role_field}.id")
        _require_unique(role_id, role_ids, f"{field}.roles")
        roles.append(
            {
                "id": role_id,
                "label": _nonempty_string(role.get("label"), f"{role_field}.label"),
                "description": _nonempty_string(
                    role.get("description"), f"{role_field}.description"
                ),
            }
        )

    use_cases: list[dict[str, Any]] = []
    use_case_ids: set[str] = set()
    for index, use_case in enumerate(
        _object_list(view.get("use_cases"), f"{field}.use_cases"), start=1
    ):
        case_field = f"{field}.use_cases[{index}]"
        case_id = _anchor_id(use_case.get("id"), f"{case_field}.id")
        _require_unique(case_id, use_case_ids, f"{field}.use_cases")
        raw_responsibilities = _object(
            use_case.get("responsibilities"), f"{case_field}.responsibilities"
        )
        if set(raw_responsibilities) != role_ids:
            raise DossierError(
                f"{case_field}.responsibilities must name every declared role exactly"
            )
        responsibilities = {
            role_id: _enum_string(
                raw_responsibilities[role_id],
                f"{case_field}.responsibilities.{role_id}",
                RESPONSIBILITY_STATES,
            )
            for role_id in (role["id"] for role in roles)
        }
        use_cases.append(
            {
                "id": case_id,
                "name": _nonempty_string(use_case.get("name"), f"{case_field}.name"),
                "goal": _nonempty_string(use_case.get("goal"), f"{case_field}.goal"),
                "responsibilities": responsibilities,
                "features": _string_list(
                    use_case.get("features"), f"{case_field}.features", required=True
                ),
            }
        )
    normalized.update({"roles": roles, "use_cases": use_cases})
    return normalized


def _normalize_business_scenarios(view: dict[str, Any], field: str) -> dict[str, Any]:
    normalized = _normalize_review_view_common(
        view,
        field=field,
        expected_type="business-scenarios",
    )
    scenarios: list[dict[str, Any]] = []
    scenario_ids: set[str] = set()
    for index, scenario in enumerate(
        _object_list(view.get("scenarios"), f"{field}.scenarios"), start=1
    ):
        scenario_field = f"{field}.scenarios[{index}]"
        scenario_id = _anchor_id(scenario.get("id"), f"{scenario_field}.id")
        _require_unique(scenario_id, scenario_ids, f"{field}.scenarios")
        lanes: list[dict[str, str]] = []
        lane_ids: set[str] = set()
        for lane_index, lane in enumerate(
            _object_list(scenario.get("lanes"), f"{scenario_field}.lanes"), start=1
        ):
            lane_field = f"{scenario_field}.lanes[{lane_index}]"
            lane_id = _anchor_id(lane.get("id"), f"{lane_field}.id")
            _require_unique(lane_id, lane_ids, f"{scenario_field}.lanes")
            lanes.append(
                {
                    "id": lane_id,
                    "label": _nonempty_string(lane.get("label"), f"{lane_field}.label"),
                    "description": _nonempty_string(
                        lane.get("description"), f"{lane_field}.description"
                    ),
                }
            )

        steps: list[dict[str, str]] = []
        step_ids: set[str] = set()
        for step_index, step in enumerate(
            _object_list(scenario.get("steps"), f"{scenario_field}.steps"), start=1
        ):
            step_field = f"{scenario_field}.steps[{step_index}]"
            step_id = _anchor_id(step.get("id"), f"{step_field}.id")
            _require_unique(step_id, step_ids, f"{scenario_field}.steps")
            lane_id = _anchor_id(step.get("lane_id"), f"{step_field}.lane_id")
            if lane_id not in lane_ids:
                raise DossierError(f"{step_field}.lane_id must reference a declared lane")
            steps.append(
                {
                    "id": step_id,
                    "lane_id": lane_id,
                    "title": _nonempty_string(step.get("title"), f"{step_field}.title"),
                    "detail": _nonempty_string(step.get("detail"), f"{step_field}.detail"),
                    "tone": _enum_string(
                        step.get("tone"),
                        f"{step_field}.tone",
                        SCENARIO_STEP_TONES,
                    ),
                }
            )
        scenarios.append(
            {
                "id": scenario_id,
                "label": _nonempty_string(scenario.get("label"), f"{scenario_field}.label"),
                "title": _nonempty_string(scenario.get("title"), f"{scenario_field}.title"),
                "summary": _nonempty_string(
                    scenario.get("summary"), f"{scenario_field}.summary"
                ),
                "lanes": lanes,
                "steps": steps,
                "context": _string_list(scenario.get("context"), f"{scenario_field}.context"),
                "object_chain": _string_list(
                    scenario.get("object_chain"), f"{scenario_field}.object_chain"
                ),
                "caption": _nonempty_string(
                    scenario.get("caption"), f"{scenario_field}.caption"
                ),
            }
        )
    normalized["scenarios"] = scenarios
    return normalized


def _normalize_architecture_node(node: dict[str, Any], field: str) -> dict[str, str]:
    return {
        "name": _nonempty_string(node.get("name"), f"{field}.name"),
        "detail": _nonempty_string(node.get("detail"), f"{field}.detail"),
        "state": _enum_string(
            node.get("state"),
            f"{field}.state",
            ARCHITECTURE_NODE_STATES,
        ),
    }


def _normalize_technical_architecture(view: dict[str, Any], field: str) -> dict[str, Any]:
    normalized = _normalize_review_view_common(
        view,
        field=field,
        expected_type="technical-architecture",
    )
    external_nodes = [
        _normalize_architecture_node(node, f"{field}.external_nodes[{index}]")
        for index, node in enumerate(
            _object_list(view.get("external_nodes"), f"{field}.external_nodes", required=False),
            start=1,
        )
    ]
    layers: list[dict[str, Any]] = []
    layer_ids: set[str] = set()
    for index, layer in enumerate(_object_list(view.get("layers"), f"{field}.layers"), start=1):
        layer_field = f"{field}.layers[{index}]"
        layer_id = _anchor_id(layer.get("id"), f"{layer_field}.id")
        _require_unique(layer_id, layer_ids, f"{field}.layers")
        layers.append(
            {
                "id": layer_id,
                "name": _nonempty_string(layer.get("name"), f"{layer_field}.name"),
                "namespace": _nonempty_string(
                    layer.get("namespace"), f"{layer_field}.namespace"
                ),
                "nodes": [
                    _normalize_architecture_node(node, f"{layer_field}.nodes[{node_index}]")
                    for node_index, node in enumerate(
                        _object_list(layer.get("nodes"), f"{layer_field}.nodes"), start=1
                    )
                ],
            }
        )
    crosscutting = [
        {
            "name": _nonempty_string(item.get("name"), f"{field}.crosscutting[{index}].name"),
            "detail": _nonempty_string(
                item.get("detail"), f"{field}.crosscutting[{index}].detail"
            ),
        }
        for index, item in enumerate(
            _object_list(view.get("crosscutting"), f"{field}.crosscutting"), start=1
        )
    ]
    normalized.update(
        {
            "system_label": _nonempty_string(
                view.get("system_label"), f"{field}.system_label"
            ),
            "external_nodes": external_nodes,
            "layers": layers,
            "crosscutting": crosscutting,
        }
    )
    return normalized


def _normalize_service_modules(view: dict[str, Any], field: str) -> dict[str, Any]:
    normalized = _normalize_review_view_common(
        view,
        field=field,
        expected_type="service-modules",
    )
    modules: list[dict[str, Any]] = []
    module_ids: set[str] = set()
    for index, module in enumerate(
        _object_list(view.get("modules"), f"{field}.modules"), start=1
    ):
        module_field = f"{field}.modules[{index}]"
        module_id = _anchor_id(module.get("id"), f"{module_field}.id")
        _require_unique(module_id, module_ids, f"{field}.modules")
        services = []
        service_names: set[str] = set()
        operation_names: set[str] = set()
        for service_index, service in enumerate(
            _object_list(module.get("services"), f"{module_field}.services"), start=1
        ):
            service_field = f"{module_field}.services[{service_index}]"
            service_name = _nonempty_string(service.get("name"), f"{service_field}.name")
            _require_unique(service_name, service_names, f"{module_field}.services")
            operations = []
            for operation_index, operation in enumerate(
                _object_list(
                    service.get("operations"), f"{service_field}.operations"
                ),
                start=1,
            ):
                operation_field = f"{service_field}.operations[{operation_index}]"
                operation_name = _nonempty_string(
                    operation.get("name"), f"{operation_field}.name"
                )
                _require_unique(
                    operation_name, operation_names, f"{module_field}.operations"
                )
                operations.append(
                    {
                        "name": operation_name,
                        "kind": _enum_string(
                            operation.get("kind"),
                            f"{operation_field}.kind",
                            SERVICE_OPERATION_KINDS,
                        ),
                        "description": _nonempty_string(
                            operation.get("description"), f"{operation_field}.description"
                        ),
                        "output": _nonempty_string(
                            operation.get("output"), f"{operation_field}.output"
                        ),
                    }
                )
            services.append(
                {
                    "name": service_name,
                    "responsibility": _nonempty_string(
                        service.get("responsibility"), f"{service_field}.responsibility"
                    ),
                    "operations": operations,
                }
            )
        modules.append(
            {
                "id": module_id,
                "index": _nonempty_string(module.get("index"), f"{module_field}.index"),
                "category": _nonempty_string(
                    module.get("category"), f"{module_field}.category"
                ),
                "name": _nonempty_string(module.get("name"), f"{module_field}.name"),
                "summary": _nonempty_string(module.get("summary"), f"{module_field}.summary"),
                "description": _nonempty_string(
                    module.get("description"), f"{module_field}.description"
                ),
                "namespace": _nonempty_string(
                    module.get("namespace"), f"{module_field}.namespace"
                ),
                "services": services,
                "contract_note": _nonempty_string(
                    module.get("contract_note"), f"{module_field}.contract_note"
                ),
            }
        )
    normalized.update(
        {
            "modules": modules,
            "crosscutting": _string_list(
                view.get("crosscutting"), f"{field}.crosscutting", required=True
            ),
        }
    )
    return normalized


def _normalize_critical_sequences(view: dict[str, Any], field: str) -> dict[str, Any]:
    normalized = _normalize_review_view_common(
        view,
        field=field,
        expected_type="critical-sequences",
    )
    sequences: list[dict[str, Any]] = []
    sequence_ids: set[str] = set()
    for index, sequence in enumerate(
        _object_list(view.get("sequences"), f"{field}.sequences"), start=1
    ):
        sequence_field = f"{field}.sequences[{index}]"
        sequence_id = _anchor_id(sequence.get("id"), f"{sequence_field}.id")
        _require_unique(sequence_id, sequence_ids, f"{field}.sequences")
        participants: list[dict[str, str]] = []
        participant_ids: set[str] = set()
        for participant_index, participant in enumerate(
            _object_list(sequence.get("participants"), f"{sequence_field}.participants"),
            start=1,
        ):
            participant_field = f"{sequence_field}.participants[{participant_index}]"
            participant_id = _anchor_id(
                participant.get("id"), f"{participant_field}.id"
            )
            _require_unique(
                participant_id, participant_ids, f"{sequence_field}.participants"
            )
            participants.append(
                {
                    "id": participant_id,
                    "label": _nonempty_string(
                        participant.get("label"), f"{participant_field}.label"
                    ),
                    "detail": _nonempty_string(
                        participant.get("detail"), f"{participant_field}.detail"
                    ),
                }
            )
        steps = []
        for step_index, step in enumerate(
            _object_list(sequence.get("steps"), f"{sequence_field}.steps"), start=1
        ):
            step_field = f"{sequence_field}.steps[{step_index}]"
            source = _anchor_id(step.get("from"), f"{step_field}.from")
            target = _anchor_id(step.get("to"), f"{step_field}.to")
            if source not in participant_ids or target not in participant_ids:
                raise DossierError(
                    f"{step_field}.from and .to must reference declared participants"
                )
            steps.append(
                {
                    "from": source,
                    "to": target,
                    "kind": _enum_string(
                        step.get("kind"), f"{step_field}.kind", SEQUENCE_STEP_KINDS
                    ),
                    "label": _nonempty_string(step.get("label"), f"{step_field}.label"),
                    "detail": _nonempty_string(step.get("detail"), f"{step_field}.detail"),
                }
            )
        sequences.append(
            {
                "id": sequence_id,
                "label": _nonempty_string(sequence.get("label"), f"{sequence_field}.label"),
                "title": _nonempty_string(sequence.get("title"), f"{sequence_field}.title"),
                "summary": _nonempty_string(
                    sequence.get("summary"), f"{sequence_field}.summary"
                ),
                "participants": participants,
                "steps": steps,
                "caption": _nonempty_string(
                    sequence.get("caption"), f"{sequence_field}.caption"
                ),
            }
        )
    normalized["sequences"] = sequences
    return normalized


REVIEW_VIEW_NORMALIZERS: dict[str, Callable[[dict[str, Any], str], dict[str, Any]]] = {
    "business-landscape": _normalize_business_landscape,
    "business-scenarios": _normalize_business_scenarios,
    "technical-architecture": _normalize_technical_architecture,
    "service-modules": _normalize_service_modules,
    "critical-sequences": _normalize_critical_sequences,
}


def normalize_review_view_payload(
    payload: object,
    *,
    role: str,
    expected_type: str,
) -> dict[str, Any]:
    """Validate one independently authored review-map view."""
    expected_types = ROLE_EXPECTED_REVIEW_VIEWS.get(role, ())
    if expected_type not in expected_types:
        raise DossierError(f"{role} does not accept review view {expected_type}")
    view = _object(payload, f"{role}.{expected_type}")
    actual_type = _nonempty_string(view.get("type"), f"{role}.{expected_type}.type")
    if actual_type != expected_type:
        raise DossierError(f"{role} review view must be {expected_type}")
    return REVIEW_VIEW_NORMALIZERS[expected_type](view, f"{role}.{expected_type}")


def _normalize_review_bundle(
    case_root: Path,
    value: object,
    *,
    role: str,
) -> tuple[Path, dict[str, Any]]:
    path = _resolve_case_file(case_root, value, f"{role}.bundle_path")
    if path.suffix.lower() != ".json":
        raise DossierError(f"{role}.bundle_path must refer to a JSON review-map bundle")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DossierError(f"{role}.bundle_path could not be read: {exc}") from exc
    return path, normalize_review_bundle_payload(payload, role=role)


def normalize_review_bundle_payload(
    payload: object,
    *,
    role: str,
) -> dict[str, Any]:
    """Validate and normalize one in-memory review-map bundle."""

    bundle = _object(payload, f"{role}.bundle")
    expected_schema = ROLE_EXPECTED_REVIEW_BUNDLE[role]
    if bundle.get("schema_version") != expected_schema:
        raise DossierError(f"{role}.bundle schema_version must be {expected_schema}")
    raw_views = _object_list(bundle.get("views"), f"{role}.bundle.views")
    actual_types = [
        _nonempty_string(view.get("type"), f"{role}.bundle.views[{index}].type")
        for index, view in enumerate(raw_views, start=1)
    ]
    expected_types = list(ROLE_EXPECTED_REVIEW_VIEWS[role])
    if actual_types != expected_types:
        raise DossierError(
            f"{role}.bundle.views must be ordered as: {', '.join(expected_types)}"
        )
    normalized_views = [
        REVIEW_VIEW_NORMALIZERS[view_type](view, f"{role}.bundle.views[{index}]")
        for index, (view_type, view) in enumerate(zip(actual_types, raw_views), start=1)
    ]
    view_ids: set[str] = set()
    for view in normalized_views:
        _require_unique(view["id"], view_ids, f"{role}.bundle.views")
    return {"schema_version": expected_schema, "views": normalized_views}


def _normalize_map_section(
    case_root: Path,
    section: dict[str, Any],
    *,
    marked: dict[Path, str],
) -> dict[str, Any]:
    role = _nonempty_string(section.get("role"), "section.role")
    bundle_path: Path | None = None
    bundle: dict[str, Any] | None = None
    if section.get("bundle_path") is not None:
        if role not in ROLE_EXPECTED_REVIEW_BUNDLE:
            raise DossierError(f"{role} does not support a review-map bundle")
        bundle_path, bundle = _normalize_review_bundle(
            case_root,
            section.get("bundle_path"),
            role=role,
        )

    packet_path: Path | None = None
    packet: dict[str, Any] | None = None
    caption = ""
    source_refs: list[str] = []
    standalone_path: Path | None = None
    if section.get("packet_path") is not None or bundle is None:
        packet_path = _resolve_case_file(
            case_root, section.get("packet_path"), f"{role}.packet_path"
        )
        if packet_path.suffix.lower() != ".json":
            raise DossierError(f"{role}.packet_path must refer to a JSON interaction-map packet")
        try:
            packet_payload = json.loads(packet_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DossierError(f"{role}.packet_path could not be read: {exc}") from exc
        packet = _object(packet_payload, f"{role}.packet_path")
        expected_map_type = ROLE_EXPECTED_MAP_TYPE[role]
        if packet.get("map_type") != expected_map_type:
            raise DossierError(f"{role}.packet_path must contain a {expected_map_type} packet")
        source_refs = _string_list(
            section.get("source_refs"), f"{role}.source_refs", required=True
        )
        caption = _nonempty_string(section.get("caption"), f"{role}.caption")
        standalone_path = _optional_marked_html_path(
            case_root,
            section,
            field=f"{role}.standalone_html_path",
            expected_kind="interaction-map",
            marked=marked,
            required=True,
        )
    elif section.get("standalone_html_path") is not None:
        standalone_path = _optional_marked_html_path(
            case_root,
            section,
            field=f"{role}.standalone_html_path",
            expected_kind="interaction-map",
            marked=marked,
        )
    return {
        "id": _nonempty_string(section.get("id"), "section.id"),
        "role": role,
        "title": _nonempty_string(section.get("title"), f"{role}.title"),
        "packet_path": packet_path,
        "packet": packet,
        "caption": caption,
        "source_refs": source_refs,
        "standalone_html_path": standalone_path,
        "bundle_path": bundle_path,
        "bundle": bundle,
    }


def _normalize_action_cards_section(
    case_root: Path,
    section: dict[str, Any],
    *,
    marked: dict[Path, str],
) -> dict[str, Any]:
    role = "action-cards"
    validation_path = _resolve_case_file(case_root, section.get("validation_path"), f"{role}.validation_path")
    try:
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DossierError(f"{role}.validation_path could not be read: {exc}") from exc
    if not isinstance(validation, dict) or validation.get("passed") is not True:
        raise DossierError(f"{role}.validation_path must report passed=true")
    validation_cards = _string_list(validation.get("cards"), f"{role}.validation.cards", required=True)
    validated_paths = [
        _resolve_validation_card_path(case_root, item, f"{role}.validation.cards")
        for item in validation_cards
    ]

    cards_raw = section.get("cards")
    if not isinstance(cards_raw, list) or not cards_raw:
        raise DossierError(f"{role}.cards must be a non-empty list")
    cards: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_card in enumerate(cards_raw, start=1):
        card = _object(raw_card, f"{role}.cards[{index}]")
        card_id = _nonempty_string(card.get("id"), f"{role}.cards[{index}].id")
        if card_id in seen_ids:
            raise DossierError(f"{role}.cards contains duplicate id: {card_id}")
        seen_ids.add(card_id)
        artifact = _normalize_artifact(
            case_root,
            card.get("artifact"),
            field=f"{role}.cards[{index}].artifact",
            expected_kind="p3-action-card",
            marked=marked,
        )
        raw_title = card.get("title")
        card_title = str(raw_title).strip() if isinstance(raw_title, str) else card_id
        if artifact["identity"] == "human-projection" and (
            not card_title or card_title == card_id or ACTION_COMPONENT_PATTERN.search(card_title)
        ):
            raise DossierError(f"{role}.cards[{index}].title must be human-readable")
        cards.append(
            {
                "id": card_id,
                "title": card_title,
                "artifact": artifact,
            }
        )

    card_paths = [card["artifact"]["canonical_path"] for card in cards]
    if card_paths != validated_paths:
        raise DossierError(
            "action-cards.cards must match validation.json cards exactly and in validation order"
        )
    return {
        "id": _nonempty_string(section.get("id"), "section.id"),
        "role": role,
        "title": _nonempty_string(section.get("title"), f"{role}.title"),
        "validation_path": validation_path,
        "cards": cards,
    }


def _normalize_originals(case_root: Path, value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise DossierError("originals must be a non-empty list of explicit source links")
    originals: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(value, start=1):
        payload = _object(item, f"originals[{index}]")
        link_id = _nonempty_string(payload.get("id"), f"originals[{index}].id")
        if not SOURCE_ID_PATTERN.fullmatch(link_id):
            raise DossierError(f"originals[{index}].id has an invalid anchor-safe identifier")
        if link_id in seen_ids:
            raise DossierError(f"originals contains duplicate id: {link_id}")
        seen_ids.add(link_id)
        originals.append(
            {
                "id": link_id,
                "label": _nonempty_string(payload.get("label"), f"originals[{index}].label"),
                "kind": _nonempty_string(payload.get("kind"), f"originals[{index}].kind"),
                "path": _resolve_case_file(case_root, payload.get("path"), f"originals[{index}].path"),
            }
        )
    return originals


def _validate_section_id(section_id: str, seen_ids: set[str]) -> None:
    if not SOURCE_ID_PATTERN.fullmatch(section_id):
        raise DossierError("section.id must start with a letter and use only letters, digits, '_' or '-'")
    if section_id in seen_ids:
        raise DossierError(f"sections contains duplicate id: {section_id}")
    seen_ids.add(section_id)


def validate_dossier_manifest(
    case_root: Path,
    manifest_path: Path,
    *,
    output_path: Path | None = None,
) -> ValidatedDossier:
    """Validate explicit dossier inputs without deriving product or architecture truth."""
    root = _resolved(case_root)
    manifest = _resolved(manifest_path)
    output = _resolved(output_path) if output_path is not None else root / DEFAULT_PORTAL_PATH
    if not root.is_dir():
        raise DossierError(f"case root is not a directory: {root}")
    if not _inside(manifest, root):
        raise DossierError("dossier manifest must stay inside the case root")
    if not _inside(output, root) or output.suffix.lower() != ".html":
        raise DossierError("dossier output must be an HTML file inside the case root")
    if not manifest.is_file():
        raise DossierError(f"dossier manifest is missing: {manifest}")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DossierError(f"dossier manifest could not be read: {exc}") from exc
    root_payload = _object(payload, "dossier manifest")
    if root_payload.get("schema_version") != DOSSIER_SCHEMA_VERSION:
        raise DossierError(f"schema_version must be {DOSSIER_SCHEMA_VERSION}")

    title = _nonempty_string(root_payload.get("title"), "title")
    locale = _nonempty_string(root_payload.get("locale", "zh-CN"), "locale")
    sections_raw = root_payload.get("sections")
    if not isinstance(sections_raw, list):
        raise DossierError("sections must be a list")
    roles = [_nonempty_string(_object(item, "section").get("role"), "section.role") for item in sections_raw]
    expected_roles = list(REQUIRED_ROLES)
    if roles == [*REQUIRED_ROLES, *OPTIONAL_ROLES]:
        expected_roles.append("impact-diagram")
    if roles != expected_roles:
        raise DossierError(
            "sections must be ordered as PRD, product-diagram, ESP, architecture-diagram, action-cards, optional impact-diagram"
        )

    marked = _marked_artifacts(root)
    normalized_sections: list[dict[str, Any]] = []
    seen_section_ids: set[str] = set()
    for raw in sections_raw:
        section = _object(raw, "section")
        role = _nonempty_string(section.get("role"), "section.role")
        if role in {"prd", "esp"}:
            normalized = _normalize_markdown_section(root, section, marked=marked)
        elif role in ROLE_EXPECTED_MAP_TYPE:
            normalized = _normalize_map_section(root, section, marked=marked)
        else:
            normalized = _normalize_action_cards_section(root, section, marked=marked)
        _validate_section_id(normalized["id"], seen_section_ids)
        normalized_sections.append(normalized)

    originals = _normalize_originals(root, root_payload.get("originals"))
    original_paths = {item["path"] for item in originals}
    required_direct_paths = {
        section["artifact"]["standalone_html_path"]
        for section in normalized_sections
        if section["role"] in {"prd", "esp"} and section["artifact"]["standalone_html_path"] is not None
    }
    required_direct_paths.update(
        section["standalone_html_path"]
        for section in normalized_sections
        if section["role"] in ROLE_EXPECTED_MAP_TYPE
        and section["standalone_html_path"] is not None
    )
    required_direct_paths.update(
        card["artifact"]["standalone_html_path"]
        for section in normalized_sections
        if section["role"] == "action-cards"
        for card in section["cards"]
        if card["artifact"]["standalone_html_path"] is not None
    )
    missing_direct_paths = sorted(
        _relative_path(path, root) for path in required_direct_paths if path not in original_paths
    )
    if missing_direct_paths:
        raise DossierError(
            "originals must retain every declared standalone HTML path: " + ", ".join(missing_direct_paths)
        )
    unlisted_marked_paths = sorted(
        _relative_path(path, root) for path in marked if path not in original_paths
    )
    if unlisted_marked_paths:
        raise DossierError(
            "originals must retain every existing marked reader/map HTML path: "
            + ", ".join(unlisted_marked_paths)
        )

    action_section = next(section for section in normalized_sections if section["role"] == "action-cards")
    return ValidatedDossier(
        case_root=root,
        manifest_path=manifest,
        output_path=output,
        title=title,
        locale=locale,
        sections=tuple(normalized_sections),
        originals=tuple(originals),
        action_card_count=len(action_section["cards"]),
    )


def _apply_template(template: str, replacements: dict[str, str]) -> str:
    pattern = re.compile("|".join(re.escape(key) for key in sorted(replacements, key=len, reverse=True)))
    rendered = pattern.sub(lambda match: replacements[match.group(0)], template)
    unresolved = sorted(set(re.findall(r"@@WFF_[A-Z_]+@@", rendered)))
    if unresolved:
        raise RuntimeError("human-review dossier template has unresolved markers: " + ", ".join(unresolved))
    return rendered


def _artifact_identity_label(artifact: dict[str, Any]) -> str:
    if artifact["identity"] == "accepted-reader":
        return "已验收阅读版"
    if artifact["identity"] == "human-projection":
        return "人工审阅投影"
    return "canonical 原件投影"


def _artifact_source_line(artifact: dict[str, Any], output_path: Path) -> str:
    if artifact["identity"] == "human-projection" and artifact["standalone_html_path"] is None:
        source_path = artifact["canonical_path"]
        link_label = "打开工程原件"
        canonical_link = ""
    else:
        source_path = artifact["standalone_html_path"] or artifact["path"]
        link_label = "打开阅读原件"
        canonical_link = ""
        if artifact["standalone_html_path"] is None:
            canonical_href = html.escape(
                _relative_href(artifact["canonical_path"], output_path), quote=True
            )
            canonical_link = (
                f'<a href="{canonical_href}" target="_blank" rel="noopener noreferrer">canonical</a>'
            )
    source_href = html.escape(_relative_href(source_path, output_path), quote=True)
    return (
        '<p class="chapter-source">'
        f'<span>{html.escape(_artifact_identity_label(artifact))}</span>'
        f'<a href="{source_href}" target="_blank" rel="noopener noreferrer">{link_label}</a>'
        f"{canonical_link}"
        "</p>"
    )


def _rewrite_embedded_resource_href(
    href: str,
    *,
    source_path: Path,
    dossier: ValidatedDossier,
) -> str:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return href
    candidate = (source_path.parent / unquote(parsed.path)).resolve()
    if not _inside(candidate, dossier.case_root):
        return href
    relative = os.path.relpath(candidate, start=dossier.output_path.parent).replace(os.sep, "/")
    rebuilt = quote(relative, safe="/._-~")
    return urlunsplit(("", "", rebuilt, parsed.query, parsed.fragment))


def _render_markdown_text(
    markdown_text: str,
    *,
    artifact: dict[str, Any],
    dossier: ValidatedDossier,
    prefix: str,
    heading_level_offset: int,
) -> tuple[str, list[PreviewHeading]]:
    body, headings, _title = render_markdown(
        localize_review_terms(markdown_text),
        anchor_prefix=prefix,
        heading_level_offset=heading_level_offset,
        resource_href_rewriter=lambda href: _rewrite_embedded_resource_href(
            href,
            source_path=artifact["path"],
            dossier=dossier,
        ),
    )
    return body, headings


def _split_action_card_appendix(markdown_text: str) -> tuple[str, str]:
    """Split a contiguous alphabetical appendix without changing its source artifact."""
    matches = list(ACTION_CARD_APPENDIX_HEADING_PATTERN.finditer(markdown_text))
    for index, match in enumerate(matches):
        if match.group(2) != "A":
            continue
        heading = match.group(0)
        explicit_single_appendix = "附录" in heading or "追踪" in heading
        letters = [item.group(2) for item in matches[index:]]
        contiguous_appendix = False
        if len(letters) >= 2 and letters[1] == "B":
            expected = [chr(ord("A") + offset) for offset in range(len(letters))]
            contiguous_appendix = letters == expected
        if not explicit_single_appendix and not contiguous_appendix:
            continue
        main = markdown_text[: match.start()].rstrip()
        main = re.sub(r"\n[ \t]*---[ \t]*\Z", "", main).rstrip()
        return main + "\n", markdown_text[match.start() :].lstrip()
    return markdown_text, ""


def _split_document_appendix(markdown_text: str) -> tuple[str, str]:
    """Split a PRD/ESP appendix at its explicit semantic heading."""
    match = DOCUMENT_APPENDIX_HEADING_PATTERN.search(markdown_text)
    if match is None:
        return markdown_text, ""
    main = markdown_text[: match.start()].rstrip()
    main = re.sub(r"\n[ \t]*---[ \t]*\Z", "", main).rstrip()
    return main + "\n", markdown_text[match.start() :].lstrip()


def _strip_redundant_document_h1(markdown_text: str, *, role: str) -> str:
    """Hide process/redundant cover titles while preserving meaningful source titles."""
    match = re.match(
        r"\A(?:\ufeff)?[ \t]*# (?P<title>[^\r\n]+)(?:\r?\n){1,2}",
        markdown_text,
    )
    if match is None:
        return markdown_text
    title = match.group("title").strip()
    redundant_titles = REDUNDANT_DOCUMENT_H1_TITLES.get(role, set())
    if title not in redundant_titles and PROJECTION_REVIEW_TITLE_PATTERN.search(title) is None:
        return markdown_text
    return markdown_text[match.end() :]


def _number_markdown_headings(markdown_text: str) -> str:
    """Add stable hierarchical numbers while leaving an optional cover H1 unnumbered."""
    lines = markdown_text.splitlines(keepends=True)
    headings: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        match = MARKDOWN_HEADING_PATTERN.match(line.rstrip("\r\n"))
        if match is not None:
            headings.append((index, match))
    if not headings:
        return markdown_text

    numbered_headings = headings[1:] if headings[0][1].group("marks") == "#" else headings
    if not numbered_headings:
        return markdown_text
    base_level = min(len(match.group("marks")) for _index, match in numbered_headings)
    counters = [0] * 6
    for index, match in numbered_headings:
        level = len(match.group("marks"))
        depth = max(0, level - base_level)
        for parent in range(depth):
            if counters[parent] == 0:
                counters[parent] = 1
        counters[depth] += 1
        for deeper in range(depth + 1, len(counters)):
            counters[deeper] = 0
        title = match.group("title").strip()
        existing_number = HEADING_NUMBER_PATTERN.match(title)
        if existing_number is not None:
            if ALPHABETICAL_HEADING_NUMBER_PATTERN.match(title) is not None:
                continue
            title = title[existing_number.end() :].strip()
        number = ".".join(str(value) for value in counters[: depth + 1])
        newline = "\n" if lines[index].endswith("\n") else ""
        lines[index] = f'{match.group("marks")} {number} {title}{newline}'
    return "".join(lines)


def _section_display_title(section: dict[str, Any]) -> str:
    return DOCUMENT_DISPLAY_TITLES.get(section["role"], section["title"])


def _markdown_outline_items(headings: list[PreviewHeading]) -> list[tuple[str, str, int]]:
    """Project actual rendered Markdown headings into the active article outline."""
    nested_headings = [heading for heading in headings if heading.level >= 3]
    selected = nested_headings or headings
    if not selected:
        return []
    base_level = min(heading.level for heading in selected)
    return [
        (
            heading.anchor,
            heading.title,
            min(max(heading.level - base_level, 0), 3),
        )
        for heading in selected
    ]


def _render_outline_panel(
    section_id: str,
    title: str,
    items: list[tuple[str, str, int]],
    *,
    initial: bool = False,
) -> str:
    hidden = "" if initial else " hidden"
    rows = _render_outline_rows(section_id, items)
    return f'''<section class="rail-panel" data-rail-panel="{html.escape(section_id, quote=True)}" aria-label="{html.escape(title)} 文章目录"{hidden}>
  <p class="rail-article-title">{html.escape(title)}</p>
  <ol class="rail-list">{rows}</ol>
</section>'''


def _render_outline_rows(
    section_id: str,
    items: list[tuple[str, str, int]],
) -> str:
    if not items:
        return '<li class="rail-empty">本文章没有可定位段落</li>'
    return "\n".join(
        f'''<li class="rail-depth-{depth}"><a href="#{html.escape(anchor, quote=True)}" data-outline-link
          data-owner-section="{html.escape(section_id, quote=True)}" aria-current="false">{_render_outline_label(label)}</a></li>'''
        for anchor, label, depth in items
    )


def _render_outline_label(label: str) -> str:
    match = OUTLINE_NUMBER_PATTERN.match(label)
    if match is None:
        return f'<span class="rail-heading-label rail-heading-label-full">{html.escape(label)}</span>'
    return (
        f'<span class="rail-heading-number">{html.escape(match.group("number"))}</span>'
        f'<span class="rail-heading-label">{html.escape(match.group("label"))}</span>'
    )


def _render_appendix_outline_panel(groups: list[dict[str, Any]]) -> str:
    group_markup = []
    for group in groups:
        rows = _render_outline_rows("appendix", group["items"])
        group_markup.append(
            f'''<details class="rail-appendix-group" data-appendix-rail-group="{html.escape(group["id"], quote=True)}">
  <summary>{html.escape(group["label"])} <span>{len(group["items"])} 节</span></summary>
  <ol class="rail-list">{rows}</ol>
</details>'''
        )
    return f'''<section class="rail-panel" data-rail-panel="appendix" aria-label="附录文章目录" hidden>
  <p class="rail-article-title">附录</p>
  <div class="rail-appendix-groups">{"".join(group_markup)}</div>
</section>'''


def _render_markdown_section(
    section: dict[str, Any],
    dossier: ValidatedDossier,
) -> tuple[str, list[tuple[str, str, int]], dict[str, Any] | None]:
    artifact = section["artifact"]
    main_markdown, appendix_markdown = _split_document_appendix(
        artifact["path"].read_text(encoding="utf-8")
    )
    main_markdown = _strip_redundant_document_h1(
        main_markdown,
        role=section["role"],
    )
    main_markdown = _number_markdown_headings(main_markdown)
    body, headings = _render_markdown_text(
        main_markdown,
        artifact=artifact,
        dossier=dossier,
        prefix=f'{section["id"]}-content',
        heading_level_offset=1,
    )
    rendered = f'''<section class="chapter chapter-document" id="{section["id"]}" data-section>
  <div class="chapter-heading" data-reveal>
    <p class="chapter-kicker">{html.escape(ROLE_LABELS[section["role"]])}</p>
    <h2>{html.escape(_section_display_title(section))}</h2>
  </div>
  {_artifact_source_line(artifact, dossier.output_path)}
  <article class="document-content">{body}</article>
</section>'''
    appendix = (
        {
            "source_kind": section["role"],
            "source_label": ROLE_LABELS[section["role"]],
            "source_title": _section_display_title(section),
            "artifact": artifact,
            "markdown": appendix_markdown,
        }
        if appendix_markdown
        else None
    )
    return rendered, _markdown_outline_items(headings), appendix


REVIEW_VIEW_KICKERS = {
    "business-landscape": "P1 / relationship matrix",
    "business-scenarios": "P1 / actor swimlane",
    "technical-architecture": "P2 / layered system",
    "service-modules": "P2 / module and service design",
    "critical-sequences": "P2 / runtime sequence",
}


def _render_review_map_source(view: dict[str, Any]) -> str:
    source_refs = "".join(f"<code>{html.escape(item)}</code>" for item in view["source_refs"])
    if view.get("_collapse_source_refs"):
        source_markup = f'''<details class="figure-source-disclosure">
    <summary>来源引用 <span>{len(view["source_refs"])} 项</span></summary>
    <p class="figure-source">{source_refs}</p>
  </details>'''
    else:
        source_markup = f'<p class="figure-source"><span>来源引用</span>{source_refs}</p>'
    return f'''<footer class="review-map-source">
  <p>{html.escape(view["caption"])}</p>
  {source_markup}
</footer>'''


def _render_review_view_shell(
    section_id: str,
    view: dict[str, Any],
    index: int,
    body: str,
) -> tuple[str, tuple[str, str, int]]:
    anchor = f'{section_id}-{view["id"]}'
    rendered = f'''<section class="review-map-section" id="{html.escape(anchor, quote=True)}" data-review-map-view data-reveal>
  <header class="review-map-heading">
    <div class="review-map-number">{index:02d}</div>
    <div>
      <p class="review-map-kicker">{html.escape(REVIEW_VIEW_KICKERS[view["type"]])}</p>
      <h3>{html.escape(view["title"])}</h3>
      <p>{html.escape(view["summary"])}</p>
    </div>
    <span class="review-map-tag">{html.escape(view["tag"])}</span>
  </header>
  {body}
  {_render_review_map_source(view)}
</section>'''
    return rendered, (anchor, view["title"], 0)


def _render_business_landscape(section_id: str, view: dict[str, Any], index: int) -> tuple[str, tuple[str, str, int]]:
    matrix_id = f'{section_id}-{view["id"]}-matrix'
    role_buttons = [
        '<button type="button" data-role-filter="all" aria-pressed="true">全部</button>'
    ]
    role_buttons.extend(
        f'<button type="button" data-role-filter="{html.escape(role["id"], quote=True)}" '
        f'aria-pressed="false">{html.escape(role["label"])}</button>'
        for role in view["roles"]
    )
    role_headers = "".join(
        f'<th scope="col"><span class="role-heading"><b>{html.escape(role["label"])}</b>'
        f'<span>{html.escape(role["description"])}</span></span></th>'
        for role in view["roles"]
    )
    role_cols = "".join('<col class="role-col">' for _role in view["roles"])
    responsibility_markup = {
        "primary": ("primary", "P", "主责"),
        "support": ("support", "S", "协作"),
        "review": ("review", "R", "治理检查"),
        "none": ("none", "-", "无直接职责"),
    }
    rows: list[str] = []
    for use_case in view["use_cases"]:
        active_roles = [
            role["id"]
            for role in view["roles"]
            if use_case["responsibilities"][role["id"]] != "none"
        ]
        responsibility_cells = []
        for role in view["roles"]:
            state = use_case["responsibilities"][role["id"]]
            class_name, mark, label = responsibility_markup[state]
            responsibility_cells.append(
                f'<td><span class="responsibility-mark {class_name}" '
                f'aria-label="{html.escape(label)}" title="{html.escape(label, quote=True)}">{mark}</span></td>'
            )
        features = "".join(f"<li>{html.escape(item)}</li>" for item in use_case["features"])
        rows.append(
            f'''<tr data-review-roles="{html.escape(" ".join(active_roles), quote=True)}">
  <th scope="row"><span class="use-case-code">{html.escape(use_case["id"])}</span><span class="use-case-name">{html.escape(use_case["name"])}</span><span class="use-case-goal">{html.escape(use_case["goal"])}</span></th>
  {"".join(responsibility_cells)}
  <td><ul class="feature-list">{features}</ul></td>
</tr>'''
        )
    body = f'''<div class="review-diagram business-landscape">
  <div class="diagram-toolbar">
    <div><p class="diagram-title">{html.escape(view["diagram_title"])}</p><p class="diagram-note">{html.escape(view["diagram_note"])}</p></div>
    <div class="segmented" data-role-filter-group data-filter-target="{html.escape(matrix_id, quote=True)}" aria-label="按角色聚焦">{"".join(role_buttons)}</div>
  </div>
  <div class="matrix-wrap">
    <table class="business-table" id="{html.escape(matrix_id, quote=True)}">
      <colgroup><col class="use-case-col">{role_cols}<col class="features-col"></colgroup>
      <thead><tr><th scope="col">Use Case / 业务目标</th>{role_headers}<th scope="col">支撑 Features</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>
  <div class="diagram-legend">
    <span><span class="responsibility-mark primary">P</span>主责</span>
    <span><span class="responsibility-mark support">S</span>协作</span>
    <span><span class="responsibility-mark review">R</span>治理检查</span>
    <span>Features 归属 Use Case</span>
  </div>
</div>'''
    return _render_review_view_shell(section_id, view, index, body)


def _render_business_scenarios(section_id: str, view: dict[str, Any], index: int) -> tuple[str, tuple[str, str, int]]:
    group_id = f'{section_id}-{view["id"]}-tabs'
    buttons: list[str] = []
    panels: list[str] = []
    for scenario_index, scenario in enumerate(view["scenarios"]):
        active = scenario_index == 0
        panel_id = f'{group_id}-{scenario["id"]}'
        buttons.append(
            f'<button type="button" role="tab" data-tab-select="{html.escape(scenario["id"], quote=True)}" '
            f'aria-controls="{html.escape(panel_id, quote=True)}" aria-selected="{str(active).lower()}">'
            f'{html.escape(scenario["label"])}</button>'
        )
        step_count = len(scenario["steps"])
        step_positions = {step["id"]: position for position, step in enumerate(scenario["steps"], start=1)}
        flow_index = "".join(
            f'<span><b>{position:02d}</b><small>{html.escape(step["title"])}</small></span>'
            for position, step in enumerate(scenario["steps"], start=1)
        )
        lane_rows: list[str] = []
        for lane in scenario["lanes"]:
            lane_steps = []
            for step in scenario["steps"]:
                if step["lane_id"] != lane["id"]:
                    continue
                position = step_positions[step["id"]]
                lane_steps.append(
                    f'''<article class="scenario-step tone-{html.escape(step["tone"], quote=True)}" style="grid-column:{position}">
  <span>{position:02d}</span><strong>{html.escape(step["title"])}</strong><small>{html.escape(step["detail"])}</small>
</article>'''
                )
            lane_rows.append(
                f'''<div class="scenario-lane">
  <div class="scenario-lane-label"><strong>{html.escape(lane["label"])}</strong><span>{html.escape(lane["description"])}</span></div>
  <div class="scenario-timeline" style="--scenario-columns:{step_count}">{"".join(lane_steps)}</div>
</div>'''
            )
        context = "".join(f"<li>{html.escape(item)}</li>" for item in scenario["context"])
        object_chain = "".join(f"<li>{html.escape(item)}</li>" for item in scenario["object_chain"])
        context_markup = (
            f'<div class="scenario-context"><strong>贯穿上下文</strong><ul>{context}</ul></div>'
            if context
            else ""
        )
        chain_markup = (
            f'<div class="object-chain"><span>对象链</span><ol>{object_chain}</ol></div>'
            if object_chain
            else ""
        )
        panels.append(
            f'''<figure class="review-tab-panel scenario-panel{' is-active' if active else ''}" id="{html.escape(panel_id, quote=True)}" role="tabpanel" data-tab-panel="{html.escape(scenario["id"], quote=True)}">
  <div class="scenario-panel-heading"><h4>{html.escape(scenario["title"])}</h4><p>{html.escape(scenario["summary"])}</p></div>
  <div class="scenario-flow-index" style="--scenario-columns:{step_count}" aria-label="场景步骤">{flow_index}</div>
  <div class="scenario-lanes">{"".join(lane_rows)}</div>
  {context_markup}{chain_markup}
  <figcaption>{html.escape(scenario["caption"])}</figcaption>
</figure>'''
        )
    body = f'''<div class="review-diagram business-scenarios" data-tab-group id="{html.escape(group_id, quote=True)}">
  <div class="diagram-toolbar">
    <div><p class="diagram-title">{html.escape(view["diagram_title"])}</p><p class="diagram-note">{html.escape(view["diagram_note"])}</p></div>
    <div class="segmented" role="tablist" aria-label="业务场景">{"".join(buttons)}</div>
  </div>
  <div class="scenario-stack">{"".join(panels)}</div>
</div>'''
    return _render_review_view_shell(section_id, view, index, body)


def _architecture_node_markup(node: dict[str, str], *, button: bool, layer_id: str = "") -> str:
    state = node["state"]
    state_label = ""
    if state == "review-bound":
        state_label = f'<em>{REVIEW_BOUND_DISPLAY}</em>'
    elif state == "domain":
        state_label = '<em>domain</em>'
    attributes = (
        f' type="button" data-architecture-focus="{html.escape(layer_id, quote=True)}"'
        if button
        else ""
    )
    tag = "button" if button else "div"
    return (
        f'<{tag} class="architecture-node state-{html.escape(state, quote=True)}"{attributes}>'
        f'<strong>{html.escape(node["name"])}</strong><span>{html.escape(node["detail"])}</span>'
        f'{state_label}</{tag}>'
    )


def _render_technical_architecture(section_id: str, view: dict[str, Any], index: int) -> tuple[str, tuple[str, str, int]]:
    external = "".join(
        _architecture_node_markup(node, button=False) for node in view["external_nodes"]
    )
    layers = []
    for layer in view["layers"]:
        nodes = "".join(
            _architecture_node_markup(node, button=True, layer_id=layer["id"])
            for node in layer["nodes"]
        )
        layers.append(
            f'''<div class="architecture-layer" data-architecture-layer="{html.escape(layer["id"], quote=True)}">
  <div class="architecture-layer-name"><strong>{html.escape(layer["name"])}</strong><span>{html.escape(layer["namespace"])}</span></div>
  <div class="architecture-layer-nodes">{nodes}</div>
</div>'''
        )
    crosscutting = "".join(
        f'<div class="crosscut-item"><strong>{html.escape(item["name"])}</strong><span>{html.escape(item["detail"])}</span></div>'
        for item in view["crosscutting"]
    )
    body = f'''<div class="review-diagram technical-architecture" data-architecture-canvas>
  <div class="diagram-toolbar">
    <div><p class="diagram-title">{html.escape(view["diagram_title"])}</p><p class="diagram-note">{html.escape(view["diagram_note"])}</p></div>
    <button class="diagram-reset" type="button" data-architecture-reset hidden>显示全部技术层</button>
  </div>
  <div class="architecture-canvas">
    {'<div class="external-nodes">' + external + '</div>' if external else ''}
    <div class="architecture-grid">
      <div class="system-boundary"><span class="system-label">{html.escape(view["system_label"])}</span>{"".join(layers)}</div>
      <aside class="crosscutting"><h4>横切能力</h4>{crosscutting}</aside>
    </div>
  </div>
  <div class="diagram-legend"><span><i class="legend-line solid"></i>已定义边界</span><span><i class="legend-line domain"></i>领域模块</span><span><i class="legend-line review"></i>{REVIEW_BOUND_DISPLAY}</span></div>
</div>'''
    return _render_review_view_shell(section_id, view, index, body)


def _render_service_modules(section_id: str, view: dict[str, Any], index: int) -> tuple[str, tuple[str, str, int]]:
    group_id = f'{section_id}-{view["id"]}-tabs'
    buttons: list[str] = []
    panels: list[str] = []
    for module_index, module in enumerate(view["modules"]):
        active = module_index == 0
        panel_id = f'{group_id}-{module["id"]}'
        buttons.append(
            f'''<button class="module-button" type="button" role="tab" data-tab-select="{html.escape(module["id"], quote=True)}" aria-controls="{html.escape(panel_id, quote=True)}" aria-selected="{str(active).lower()}">
  <span>{html.escape(module["index"])} / {html.escape(module["category"])}</span><strong>{html.escape(module["name"])}</strong><small>{html.escape(module["summary"])}</small>
</button>'''
        )
        service_rows = []
        for service in module["services"]:
            operations = "".join(
                f'''<article class="service-operation"><header><span class="operation-kind kind-{html.escape(operation["kind"].lower(), quote=True)}">{html.escape(operation["kind"])}</span><code>{html.escape(operation["name"])}</code></header><p>{html.escape(operation["description"])}</p><span>{html.escape(operation["output"])}</span></article>'''
                for operation in service["operations"]
            )
            service_rows.append(
                f'''<tr><th scope="row"><code>{html.escape(service["name"])}</code><span>{html.escape(service["responsibility"])}</span></th><td><div class="service-operations">{operations}</div></td></tr>'''
            )
        panels.append(
            f'''<article class="review-tab-panel module-detail{' is-active' if active else ''}" id="{html.escape(panel_id, quote=True)}" role="tabpanel" data-tab-panel="{html.escape(module["id"], quote=True)}">
  <header><div><h4>{html.escape(module["name"])}</h4><p>{html.escape(module["description"])}</p></div><code class="module-namespace">{html.escape(module["namespace"])}</code></header>
  <div class="service-table-wrap"><table class="service-table"><thead><tr><th>服务组 / 责任</th><th>公开 C / Q / E 操作</th></tr></thead><tbody>{"".join(service_rows)}</tbody></table></div>
  <p class="module-contract-note">{html.escape(module["contract_note"])}</p>
</article>'''
        )
    crosscutting = "".join(f"<span>{html.escape(item)}</span>" for item in view["crosscutting"])
    body = f'''<div class="review-diagram service-modules" data-tab-group id="{html.escape(group_id, quote=True)}">
  <div class="diagram-toolbar"><div><p class="diagram-title">{html.escape(view["diagram_title"])}</p><p class="diagram-note">{html.escape(view["diagram_note"])}</p></div></div>
  <div class="module-topology" role="tablist" aria-label="服务模块">{"".join(buttons)}</div>
  <div class="module-crosscutting">{crosscutting}</div>
  <div class="module-details">{"".join(panels)}</div>
</div>'''
    return _render_review_view_shell(section_id, view, index, body)


def _render_critical_sequences(section_id: str, view: dict[str, Any], index: int) -> tuple[str, tuple[str, str, int]]:
    group_id = f'{section_id}-{view["id"]}-tabs'
    buttons: list[str] = []
    panels: list[str] = []
    for sequence_index, sequence in enumerate(view["sequences"]):
        active = sequence_index == 0
        panel_id = f'{group_id}-{sequence["id"]}'
        buttons.append(
            f'<button type="button" role="tab" data-tab-select="{html.escape(sequence["id"], quote=True)}" '
            f'aria-controls="{html.escape(panel_id, quote=True)}" aria-selected="{str(active).lower()}">'
            f'{html.escape(sequence["label"])}</button>'
        )
        participant_index = {
            participant["id"]: position
            for position, participant in enumerate(sequence["participants"])
        }
        participant_headers = "".join(
            f'<div><strong>{html.escape(participant["label"])}</strong><span>{html.escape(participant["detail"])}</span></div>'
            for participant in sequence["participants"]
        )
        message_rows = []
        for step_index, step in enumerate(sequence["steps"], start=1):
            source_index = participant_index[step["from"]]
            target_index = participant_index[step["to"]]
            start = min(source_index, target_index) + 2
            end = max(source_index, target_index) + 3
            direction = " reverse" if source_index > target_index else ""
            if source_index == target_index:
                direction += " self"
            message_rows.append(
                f'''<div class="sequence-message-row" style="--participant-count:{len(sequence["participants"])}">
  <span class="sequence-index">{step_index:02d}</span>
  <div class="sequence-message kind-{html.escape(step["kind"], quote=True)}{direction}" style="--sequence-start:{start};--sequence-end:{end}">
    <span class="sequence-route">{html.escape(step["from"])} -> {html.escape(step["to"])}</span>
    <strong>{html.escape(step["label"])}</strong><small>{html.escape(step["detail"])}</small>
  </div>
</div>'''
            )
        panels.append(
            f'''<figure class="review-tab-panel sequence-panel{' is-active' if active else ''}" id="{html.escape(panel_id, quote=True)}" role="tabpanel" data-tab-panel="{html.escape(sequence["id"], quote=True)}">
  <div class="sequence-panel-heading"><h4>{html.escape(sequence["title"])}</h4><p>{html.escape(sequence["summary"])}</p></div>
  <div class="sequence-scroll">
    <div class="sequence-chart" style="--participant-count:{len(sequence["participants"])}">
      <div class="sequence-participants"><span>Step</span>{participant_headers}</div>
      <div class="sequence-body">{"".join(message_rows)}</div>
    </div>
  </div>
  <figcaption>{html.escape(sequence["caption"])}</figcaption>
</figure>'''
        )
    body = f'''<div class="review-diagram critical-sequences" data-tab-group id="{html.escape(group_id, quote=True)}">
  <div class="diagram-toolbar">
    <div><p class="diagram-title">{html.escape(view["diagram_title"])}</p><p class="diagram-note">{html.escape(view["diagram_note"])}</p></div>
    <div class="segmented" role="tablist" aria-label="关键运行链路">{"".join(buttons)}</div>
  </div>
  <div class="sequence-stack">{"".join(panels)}</div>
  <div class="diagram-legend"><span><i class="legend-line solid"></i>同步调用</span><span><i class="legend-line async"></i>异步消息</span><span><i class="legend-line return"></i>返回 / 回执</span></div>
</div>'''
    return _render_review_view_shell(section_id, view, index, body)


REVIEW_VIEW_RENDERERS: dict[
    str,
    Callable[[str, dict[str, Any], int], tuple[str, tuple[str, str, int]]],
] = {
    "business-landscape": _render_business_landscape,
    "business-scenarios": _render_business_scenarios,
    "technical-architecture": _render_technical_architecture,
    "service-modules": _render_service_modules,
    "critical-sequences": _render_critical_sequences,
}


def _render_review_bundle_section(
    section: dict[str, Any],
    dossier: ValidatedDossier,
) -> tuple[str, list[tuple[str, str, int]]]:
    bundle_href = html.escape(_relative_href(section["bundle_path"], dossier.output_path), quote=True)
    links = [
        f'<a href="{bundle_href}" target="_blank" rel="noopener noreferrer">review-map bundle</a>'
    ]
    if section["packet_path"] is not None:
        packet_href = html.escape(
            _relative_href(section["packet_path"], dossier.output_path), quote=True
        )
        links.append(
            f'<a href="{packet_href}" target="_blank" rel="noopener noreferrer">兼容图形 packet</a>'
        )
    if section["standalone_html_path"] is not None:
        standalone_href = html.escape(
            _relative_href(section["standalone_html_path"], dossier.output_path), quote=True
        )
        links.append(
            f'<a href="{standalone_href}" target="_blank" rel="noopener noreferrer">独立图形原件</a>'
        )
    views: list[str] = []
    outline_items: list[tuple[str, str, int]] = []
    for index, view in enumerate(section["bundle"]["views"], start=1):
        render_view = {
            **localize_review_payload(view),
            "_collapse_source_refs": section["role"] == "architecture-diagram",
        }
        rendered_view, outline_item = REVIEW_VIEW_RENDERERS[view["type"]](
            section["id"], render_view, index
        )
        views.append(rendered_view)
        outline_items.append(outline_item)
    rendered = f'''<section class="chapter chapter-review-maps" id="{html.escape(section["id"], quote=True)}" data-section>
  <div class="chapter-heading" data-reveal>
    <p class="chapter-kicker">{html.escape(ROLE_LABELS[section["role"]])}</p>
    <h2>{html.escape(section["title"])}</h2>
  </div>
  <p class="chapter-source"><span>Agentic 显式审阅图投影</span>{"".join(links)}</p>
  <div class="review-map-collection">{"".join(views)}</div>
</section>'''
    return rendered, outline_items


def _render_map_section(
    section: dict[str, Any],
    dossier: ValidatedDossier,
    render_svg: Callable[..., str],
) -> tuple[str, list[tuple[str, str, int]]]:
    try:
        svg = render_svg(
            section["packet"],
            dossier.locale,
            id_namespace=section["id"],
            include_styles=True,
        )
    except (TypeError, ValueError) as exc:
        raise DossierError(f'{section["role"]}.packet_path failed interaction-map rendering: {exc}') from exc
    source_refs = "".join(f"<code>{html.escape(item)}</code>" for item in section["source_refs"])
    if section["role"] == "architecture-diagram":
        source_markup = f'''<details class="figure-source-disclosure">
        <summary>来源引用 <span>{len(section["source_refs"])} 项</span></summary>
        <p class="figure-source">{source_refs}</p>
      </details>'''
    else:
        source_markup = f'<p class="figure-source"><span>来源引用</span>{source_refs}</p>'
    packet_href = html.escape(_relative_href(section["packet_path"], dossier.output_path), quote=True)
    standalone_href = html.escape(
        _relative_href(section["standalone_html_path"], dossier.output_path), quote=True
    )
    rendered = f'''<section class="chapter chapter-figure" id="{section["id"]}" data-section>
  <div class="chapter-heading" data-reveal>
    <p class="chapter-kicker">{html.escape(ROLE_LABELS[section["role"]])}</p>
    <h2>{html.escape(section["title"])}</h2>
  </div>
  <figure class="map-figure" data-reveal>
    <div class="map-stage" aria-label="{html.escape(section["title"])}">{svg}</div>
    <figcaption id="{section["id"]}-caption" data-reveal>
      <p>{html.escape(section["caption"])}</p>
      {source_markup}
      <p class="figure-links"><a href="{packet_href}" target="_blank" rel="noopener noreferrer">图形 packet</a><a href="{standalone_href}" target="_blank" rel="noopener noreferrer">独立图形原件</a></p>
    </figcaption>
  </figure>
</section>'''
    return rendered, [
        (section["id"], "图形", 0),
        (f'{section["id"]}-caption', "图注与来源", 0),
    ]


def _render_action_cards_section(
    section: dict[str, Any],
    dossier: ValidatedDossier,
) -> tuple[str, list[tuple[str, str, int]], list[dict[str, Any]]]:
    card_groups: list[str] = []
    outline_items: list[tuple[str, str, int]] = []
    appendices: list[dict[str, Any]] = []
    for group_start in range(0, len(section["cards"]), 8):
        cards_markup: list[str] = []
        for offset, card in enumerate(section["cards"][group_start : group_start + 8]):
            artifact = card["artifact"]
            delay = offset * 60
            card_index = group_start + offset + 1
            card_anchor = f'{section["id"]}-card-{card_index}'
            card_markdown, appendix_markdown = _split_action_card_appendix(
                artifact["path"].read_text(encoding="utf-8")
            )
            body, _headings = _render_markdown_text(
                card_markdown,
                artifact=artifact,
                dossier=dossier,
                prefix=f'{section["id"]}-{card_index}',
                heading_level_offset=2,
            )
            display_title = f"行动卡 {card_index}：{card['title']}"
            if appendix_markdown:
                appendices.append(
                    {
                        "source_kind": "action-cards",
                        "source_label": "Action Card",
                        "source_title": display_title,
                        "artifact": artifact,
                        "markdown": appendix_markdown,
                    }
                )
            outline_items.append((card_anchor, display_title, 0))
            cards_markup.append(
                f'''<article class="action-card" id="{card_anchor}" data-card-id="{html.escape(card['id'], quote=True)}" data-reveal style="--reveal-delay:{delay}ms">
  <p class="action-card-id">{html.escape(display_title)}</p>
  {_artifact_source_line(artifact, dossier.output_path)}
  <div class="action-card-content">{body}</div>
</article>'''
            )
        card_groups.append('<div class="action-card-group">' + "\n".join(cards_markup) + "</div>")
    card_group_markup = "\n".join(card_groups)
    rendered = f'''<section class="chapter chapter-actions" id="{section["id"]}" data-section>
  <div class="chapter-heading" data-reveal>
    <p class="chapter-kicker">{html.escape(ROLE_LABELS[section["role"]])}</p>
    <h2>{html.escape(section["title"])}</h2>
  </div>
  <p class="chapter-intro">按业务与实施责任呈现 {len(section["cards"])} 张人工审阅行动卡；完整组件身份保留在机器 sidecar。</p>
  {card_group_markup}
</section>'''
    return rendered, outline_items, appendices


def _render_appendix_section(
    appendices: list[dict[str, Any]],
    dossier: ValidatedDossier,
) -> tuple[str, list[dict[str, Any]]]:
    group_labels = {
        "prd": "PRD 附录",
        "esp": "ESP 附录",
        "action-cards": "Action Card 附录",
    }
    group_order = tuple(group_labels)
    groups: list[str] = []
    outline_groups: list[dict[str, Any]] = []
    for source_kind in group_order:
        entries = [item for item in appendices if item["source_kind"] == source_kind]
        if not entries:
            continue
        articles: list[str] = []
        outline_items: list[tuple[str, str, int]] = []
        for index, appendix in enumerate(entries, start=1):
            artifact = appendix["artifact"]
            appendix_markdown = appendix["markdown"]
            if source_kind in {"prd", "esp"}:
                appendix_markdown = _number_markdown_headings(appendix_markdown)
            body, headings = _render_markdown_text(
                appendix_markdown,
                artifact=artifact,
                dossier=dossier,
                prefix=f"appendix-{source_kind}-{index}",
                heading_level_offset=0 if source_kind == "action-cards" else 1,
            )
            outline_items.extend(_markdown_outline_items(headings))
            articles.append(
                f'''<article class="appendix-source">
  <p class="appendix-origin">来自 {html.escape(appendix["source_label"])} · {html.escape(appendix["source_title"])}</p>
  {_artifact_source_line(artifact, dossier.output_path)}
  <div class="document-content">{body}</div>
</article>'''
            )
        group_id = f"appendix-{source_kind}"
        group_label = group_labels[source_kind]
        groups.append(
            f'''<details class="appendix-document-group" id="{group_id}">
  <summary><strong>{group_label}</strong><span>{len(outline_items)} 节 · 默认折叠</span></summary>
  <div class="appendix-group-body">{"".join(articles)}</div>
</details>'''
        )
        outline_groups.append(
            {"id": group_id, "label": group_label, "items": outline_items}
        )
    rendered = f'''<section class="chapter chapter-document chapter-appendix" id="appendix" data-section>
  <div class="chapter-heading" data-reveal>
    <p class="chapter-kicker">P1-P3 / 支撑材料</p>
    <h2>附录</h2>
  </div>
  <p class="chapter-intro">集中保留 PRD、ESP 与 Action Card 的追踪、契约、持久化、授权及证据索引；默认折叠，不打断主线阅读。</p>
  <div class="appendix-document-groups">{"".join(groups)}</div>
</section>'''
    return rendered, outline_groups


def _render_anchor_navigation(dossier: ValidatedDossier, *, has_appendix: bool) -> str:
    items: list[str] = []
    for index, section in enumerate(dossier.sections):
        current = "location" if index == 0 else "false"
        items.append(
            f'<li><a href="#{section["id"]}" data-anchor-link aria-current="{current}">'
            f'{html.escape(TOP_NAV_LABELS[section["role"]])}</a></li>'
        )
    if has_appendix:
        items.append(
            '<li><a href="#appendix" data-anchor-link aria-current="false">附录</a></li>'
        )
    return "\n".join(items)


def _render_rail_panels(
    dossier: ValidatedDossier,
    outlines: dict[str, list[tuple[str, str, int]]],
    *,
    appendix_groups: list[dict[str, Any]],
) -> str:
    panels = [
        _render_outline_panel(
            section["id"],
            _section_display_title(section),
            outlines[section["id"]],
            initial=index == 0,
        )
        for index, section in enumerate(dossier.sections)
    ]
    if appendix_groups:
        panels.append(_render_appendix_outline_panel(appendix_groups))
    return "\n".join(panels)


def _render_originals(dossier: ValidatedDossier) -> str:
    links = []
    for original in dossier.originals:
        href = html.escape(_relative_href(original["path"], dossier.output_path), quote=True)
        links.append(
            f'<li><a href="{href}" target="_blank" rel="noopener noreferrer">'
            f'<span>{html.escape(original["kind"])}</span>{html.escape(original["label"])}</a></li>'
        )
    return "\n".join(links)


def render_human_review_dossier(dossier: ValidatedDossier) -> str:
    """Render a validated dossier without adding summaries or source truth."""
    render_svg: Callable[..., str] | None = None
    sections: list[str] = []
    outlines: dict[str, list[tuple[str, str, int]]] = {}
    appendix_entries: list[dict[str, Any]] = []
    for section in dossier.sections:
        if section["role"] in {"prd", "esp"}:
            rendered_section, outline_items, document_appendix = _render_markdown_section(
                section, dossier
            )
            if document_appendix is not None:
                appendix_entries.append(document_appendix)
        elif section["role"] in ROLE_EXPECTED_MAP_TYPE:
            if section.get("bundle") is not None:
                rendered_section, outline_items = _render_review_bundle_section(section, dossier)
            else:
                if render_svg is None:
                    render_svg = _load_map_svg_renderer()
                rendered_section, outline_items = _render_map_section(
                    section, dossier, render_svg
                )
        else:
            rendered_section, outline_items, card_appendices = _render_action_cards_section(
                section, dossier
            )
            appendix_entries.extend(card_appendices)
        sections.append(rendered_section)
        outlines[section["id"]] = outline_items

    appendix_groups: list[dict[str, Any]] = []
    if appendix_entries:
        appendix_section, appendix_groups = _render_appendix_section(
            appendix_entries, dossier
        )
        sections.append(appendix_section)
    has_appendix = bool(appendix_entries)

    template = load_script_text_asset(__file__, "human-review-dossier.html.template")
    replacements = {
        "@@WFF_DOCUMENT_TITLE@@": html.escape(dossier.title),
        "@@WFF_CASE_NAME@@": html.escape(dossier.case_root.name),
        "@@WFF_LOCALE@@": html.escape(dossier.locale, quote=True),
        "@@WFF_SECTION_COUNT@@": str(len(dossier.sections) + int(has_appendix)),
        "@@WFF_ACTION_CARD_COUNT@@": str(dossier.action_card_count),
        "@@WFF_ANCHOR_NAVIGATION@@": _render_anchor_navigation(
            dossier, has_appendix=has_appendix
        ),
        "@@WFF_RAIL_PANELS@@": _render_rail_panels(
            dossier, outlines, appendix_groups=appendix_groups
        ),
        "@@WFF_ORIGINAL_LINKS@@": _render_originals(dossier),
        "@@WFF_DOSSIER_SECTIONS@@": "\n".join(sections),
    }
    return _apply_template(template, replacements)


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=path.parent,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(text)
            handle.flush()
        os.replace(temporary_path, path)
    except BaseException:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
        raise


def _is_generated_portal_manifest(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("schema_version") == PORTAL_SCHEMA_VERSION


def _dossier_report(dossier: ValidatedDossier, rendered: str, elapsed_seconds: float) -> dict[str, object]:
    inline_scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", rendered, flags=re.DOTALL)
    return {
        "generated": True,
        "mode": "dossier",
        "index": str(dossier.output_path),
        "manifest": str(dossier.manifest_path),
        "section_count": len(dossier.sections),
        "action_card_count": dossier.action_card_count,
        "html_bytes": len(rendered.encode("utf-8")),
        "inline_runtime_bytes": sum(len(script.encode("utf-8")) for script in inline_scripts),
        "render_duration_ms": round(elapsed_seconds * 1000, 2),
        "dossier_ready": True,
        "dossier_error": "",
    }


def _remove_stale_dossier_index(output_path: Path) -> None:
    if output_path.is_file() and is_generated_human_review_dossier(output_path):
        output_path.unlink()


def refresh_human_review_dossier(
    case_root: Path,
    *,
    manifest_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, object]:
    """Render the dossier when complete inputs exist, otherwise keep the #309 portal fallback."""
    root = _resolved(case_root)
    manifest = _resolved(manifest_path) if manifest_path is not None else root / DEFAULT_DOSSIER_MANIFEST_PATH
    output = _resolved(output_path) if output_path is not None else root / DEFAULT_PORTAL_PATH
    if not root.is_dir():
        raise DossierError(f"case root is not a directory: {root}")
    if not _inside(manifest, root):
        raise DossierError("dossier manifest must stay inside the case root")
    if not _inside(output, root) or output.suffix.lower() != ".html":
        raise DossierError("dossier output must be an HTML file inside the case root")

    if not manifest.is_file():
        _remove_stale_dossier_index(output)
        fallback = refresh_human_review_portal(root, output_path=output)
        return {
            **fallback,
            "mode": "portal" if fallback["generated"] else "none",
            "dossier_ready": False,
            "dossier_error": "dossier manifest is missing",
        }

    try:
        dossier = validate_dossier_manifest(root, manifest, output_path=output)
        validate_portal_destination(root, output_path=output)
        started = time.perf_counter()
        rendered = render_human_review_dossier(dossier)
        elapsed_seconds = time.perf_counter() - started
    except DossierError as exc:
        _remove_stale_dossier_index(output)
        fallback = refresh_human_review_portal(root, output_path=output)
        return {
            **fallback,
            "mode": "portal" if fallback["generated"] else "none",
            "dossier_ready": False,
            "dossier_error": str(exc),
        }

    _write_atomic(output, rendered)
    stale_portal_manifest = output.with_name(MANIFEST_FILENAME)
    if stale_portal_manifest.is_file() and _is_generated_portal_manifest(stale_portal_manifest):
        stale_portal_manifest.unlink()
    return _dossier_report(dossier, rendered, elapsed_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root", required=True, type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="defaults to <case-root>/human-review/dossier-manifest.json",
    )
    parser.add_argument("--output", type=Path, help="defaults to <case-root>/human-review/index.html")
    parser.add_argument("--open", action="store_true", dest="open_browser")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when complete dossier inputs are unavailable instead of accepting portal fallback",
    )
    return parser


def _error_payload(kind: str, message: str) -> str:
    return json.dumps({"generated": False, "error_kind": kind, "error": message}, ensure_ascii=False)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = refresh_human_review_dossier(
            args.case_root,
            manifest_path=args.manifest,
            output_path=args.output,
        )
    except (DossierError, PortalError) as exc:
        print(_error_payload("dossier_contract", str(exc)), file=sys.stderr)
        return 2
    except ModuleNotFoundError as exc:
        print(_error_payload("dependency_missing", str(exc)), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, RuntimeError) as exc:
        print(_error_payload("dossier_io", str(exc)), file=sys.stderr)
        return 2

    if args.strict and not report.get("dossier_ready"):
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1

    opened = False
    open_error = ""
    if args.open_browser and report.get("generated"):
        try:
            opened = bool(webbrowser.open(Path(str(report["index"])).as_uri()))
        except (OSError, webbrowser.Error) as exc:
            open_error = str(exc)
    report["opened"] = opened
    report["open_error"] = open_error
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
