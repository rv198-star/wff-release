#!/usr/bin/env python3
"""Assemble the v1.6 reader lane into the accepted Human Review dossier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from release.render_human_review_dossier import (  # noqa: E402
    DEFAULT_DOSSIER_MANIFEST_PATH,
    DOSSIER_SCHEMA_VERSION,
    refresh_human_review_dossier,
)
from release.render_reader_preview import (  # noqa: E402
    default_preview_path,
    render_reader_preview,
    resolve_accepted_reader,
)
from common.human_semantic_projection import (  # noqa: E402
    PROJECTION_KINDS,
    validate_projection_artifact,
)
from common.review_map_generation import (  # noqa: E402
    validate_review_map_artifact,
)


class AssemblyError(ValueError):
    """The current v1.6 artifacts are not ready for a complete dossier."""


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _case_file(case_root: Path, value: object, field: str) -> Path:
    raw = Path(str(value or ""))
    path = raw.resolve() if raw.is_absolute() else (case_root / raw).resolve()
    if not _inside(path, case_root) or not path.is_file() or path.is_symlink():
        raise AssemblyError(f"{field} must be a regular file inside the case root")
    return path


def _relative(path: Path, case_root: Path) -> str:
    return path.resolve().relative_to(case_root).as_posix()


def _load_json(path: Path, field: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssemblyError(f"{field} is not readable JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssemblyError(f"{field} must be a JSON object")
    return payload


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
        os.replace(temporary, path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def _translation_targets(case_root: Path) -> list[dict[str, Any]]:
    manifest_path = case_root / "reader-translation-manifest.json"
    manifest = _load_json(manifest_path, "reader translation manifest")
    if manifest.get("target_locale") != "zh-CN":
        raise AssemblyError("reader translation manifest must target zh-CN")
    raw_targets = manifest.get("targets")
    if not isinstance(raw_targets, list):
        raise AssemblyError("reader translation targets must be a list")
    targets: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_targets, start=1):
        if not isinstance(raw, dict):
            raise AssemblyError(f"reader translation target {index} must be an object")
        if raw.get("status") != "generated" or raw.get("verdict") != "pass":
            continue
        canonical = _case_file(case_root, raw.get("canonical"), f"target {index} canonical")
        reader = _case_file(case_root, raw.get("reader"), f"target {index} reader")
        integrity = _case_file(case_root, raw.get("integrity_json"), f"target {index} integrity")
        target = resolve_accepted_reader(case_root, reader)
        if target.canonical_path != canonical or target.integrity_path != integrity:
            raise AssemblyError(f"target {index} accepted reader identity is inconsistent")
        targets.append({**raw, "canonical_path": canonical, "reader_path": reader})
    return targets


def _single_target(targets: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    matches = [target for target in targets if target.get("kind") == kind]
    if len(matches) != 1:
        raise AssemblyError(f"exactly one accepted {kind} reader is required")
    return matches[0]


def _accepted_review_maps(case_root: Path) -> dict[str, Path]:
    manifest = _load_json(
        case_root / "human-review" / "review-map-manifest.json",
        "review-map manifest",
    )
    if manifest.get("schema_version") != "wff.human-review-map-manifest.v1":
        raise AssemblyError("review-map manifest schema is invalid")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise AssemblyError("review-map manifest entries must be a list")
    accepted: dict[str, Path] = {}
    for raw in entries:
        if not isinstance(raw, dict) or raw.get("status") != "generated":
            continue
        kind = str(raw.get("kind") or "")
        if kind not in {"p1", "p2"} or kind in accepted:
            continue
        path = _case_file(case_root, raw.get("path"), f"{kind} review-map bundle")
        if not validate_review_map_artifact(
            case_root=case_root,
            kind=kind,
            output_path=path,
            expected_source_hashes=raw.get("source_hashes"),
            expected_sha256=raw.get("sha256"),
        ):
            raise AssemblyError(f"{kind} review-map bundle is missing, stale, or invalid")
        accepted[kind] = path
    if set(accepted) != {"p1", "p2"}:
        raise AssemblyError("accepted P1 and P2 review-map bundles are required")
    return accepted


def _retire_synthetic_map_artifacts(case_root: Path) -> None:
    map_root = case_root / "human-review" / "maps"
    for name in (
        "p1-product-flow.json",
        "p1-product-flow.html",
        "p2-architecture-flow.json",
        "p2-architecture-flow.html",
    ):
        (map_root / name).unlink(missing_ok=True)


def _card_id(path: Path) -> str:
    match = re.match(r"(.+?)-action-card$", path.stem, flags=re.IGNORECASE)
    return (match.group(1) if match else path.stem).upper()


def _accepted_semantic_projections(case_root: Path) -> dict[str, dict[str, Any]]:
    manifest_path = case_root / "human-review" / "semantic-projection-manifest.json"
    manifest = _load_json(manifest_path, "human semantic projection manifest")
    if manifest.get("schema_version") != "wff.human-semantic-projection-manifest.v1":
        raise AssemblyError("human semantic projection manifest schema is invalid")
    if manifest.get("status") != "generated":
        raise AssemblyError("human semantic projections are not generated")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise AssemblyError("human semantic projection entries must be a list")
    accepted: dict[str, dict[str, Any]] = {}
    for raw in entries:
        if not isinstance(raw, dict) or raw.get("status") != "generated":
            continue
        kind = str(raw.get("kind") or "")
        if kind not in PROJECTION_KINDS or kind in accepted:
            continue
        path = _case_file(case_root, raw.get("path"), f"{kind} human projection")
        if not validate_projection_artifact(
            case_root=case_root,
            kind=kind,
            output_path=path,
            expected_source_hashes=raw.get("source_hashes"),
            expected_sha256=raw.get("sha256"),
        ):
            raise AssemblyError(f"{kind} human projection is missing, stale, or invalid")
        accepted[kind] = _load_json(path, f"{kind} human projection")
    if set(accepted) != set(PROJECTION_KINDS):
        missing = sorted(set(PROJECTION_KINDS) - set(accepted))
        raise AssemblyError("accepted human semantic projections are required: " + ", ".join(missing))
    return accepted


def _materialize_document_projection(
    case_root: Path,
    *,
    kind: str,
    payload: dict[str, Any],
) -> Path:
    output = case_root / "human-review" / "projections" / "materialized" / f"{kind}.md"
    text = "\n\n".join(
        [
            f"# {str(payload['document_title']).strip()}",
            str(payload["reader_summary"]).strip(),
            str(payload["main_markdown"]).strip(),
            "## 技术附录",
            (
                "完整机器身份索引保存在"
                f"[{kind} 语义投影 JSON](../{kind}.json)，不在本页逐项展开。"
            ),
            str(payload["appendix_markdown"]).strip(),
        ]
    ).rstrip() + "\n"
    _atomic_text(output, text)
    return output


def _component_source_map(card_targets: list[dict[str, Any]]) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for target in card_targets:
        canonical = target["canonical_path"]
        mapping[_card_id(canonical)] = canonical
    return mapping


def _materialize_action_projection(
    case_root: Path,
    *,
    payload: dict[str, Any],
    card_targets: list[dict[str, Any]],
) -> tuple[Path, list[dict[str, Any]]]:
    output_root = case_root / "human-review" / "projections" / "materialized" / "action-cards"
    source_by_component = _component_source_map(card_targets)
    ordered_cards: list[dict[str, Any]] = []
    validation_cards: list[str] = []
    validation_bindings: list[dict[str, Any]] = []
    for index, raw in enumerate(payload.get("cards", []), start=1):
        if not isinstance(raw, dict):
            raise AssemblyError(f"human Action Card {index} is invalid")
        components = [str(item) for item in raw.get("component_ids", [])]
        source_paths = [source_by_component[item] for item in components if item in source_by_component]
        if len(source_paths) != len(components) or not source_paths:
            raise AssemblyError(f"human Action Card {index} source components are inconsistent")
        output = output_root / f"action-card-{index:02d}.md"
        card_id = str(raw.get("id") or f"HAC-{index:02d}")
        card_title = str(raw.get("title") or "").strip()
        text = "\n\n".join(
            [
                f"# 行动卡 {index}：{card_title}",
                str(raw.get("summary") or "").strip(),
                str(raw.get("main_markdown") or "").strip(),
                "## A. 技术附录与追踪",
                (
                    "完整组件、操作和来源身份保存在"
                    "[Action Card 语义投影 JSON](../../action-card-set.json)，"
                    "本附录只解释责任、证明和待决风险。"
                ),
                str(raw.get("appendix_markdown") or "").strip(),
            ]
        ).rstrip() + "\n"
        _atomic_text(output, text)
        canonical = source_paths[0]
        validation_cards.append(str(canonical))
        ordered_cards.append(
            {
                "id": card_id,
                "title": card_title,
                "artifact": {
                    "kind": "p3-action-card",
                    "identity": "human-projection",
                    "path": _relative(output, case_root),
                    "canonical_path": _relative(canonical, case_root),
                },
            }
        )
        validation_bindings.append(
            {
                "id": card_id,
                "title": card_title,
                "component_ids": components,
                "operation_ids": [str(item) for item in raw.get("operation_ids", [])],
                "canonical_paths": [_relative(path, case_root) for path in source_paths],
            }
        )
    validation_path = output_root / "validation.json"
    _atomic_text(
        validation_path,
        json.dumps(
            {
                "passed": True,
                "projection_kind": "action-card-set",
                "cards": validation_cards,
                "source_component_count": len(source_by_component),
                "human_card_count": len(ordered_cards),
                "bindings": validation_bindings,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    return validation_path, ordered_cards


def assemble_v16_dossier(case_root: Path) -> dict[str, Any]:
    root = case_root.resolve()
    targets = _translation_targets(root)
    prd = _single_target(targets, "p1-prd")
    esp = _single_target(targets, "p2-esp")
    review_maps = _accepted_review_maps(root)
    projections = _accepted_semantic_projections(root)
    _retire_synthetic_map_artifacts(root)
    card_targets = [target for target in targets if target.get("kind") == "p3-action-card"]
    if not card_targets:
        raise AssemblyError("at least one accepted P3 Action Card reader is required")

    prd_projection = _materialize_document_projection(
        root, kind="prd-core", payload=projections["prd-core"]
    )
    esp_projection = _materialize_document_projection(
        root, kind="esp-core", payload=projections["esp-core"]
    )
    validation_path, ordered_cards = _materialize_action_projection(
        root,
        payload=projections["action-card-set"],
        card_targets=card_targets,
    )

    originals: list[dict[str, str]] = []
    artifacts: list[tuple[str, str, dict[str, Any]]] = [
        ("prd-reader", "PRD 中文阅读版", prd),
        ("esp-reader", "ESP 中文阅读版", esp),
    ]
    for identifier, label, target in artifacts:
        preview = default_preview_path(target["reader_path"])
        accepted = resolve_accepted_reader(root, target["reader_path"])
        _atomic_text(preview, render_reader_preview(accepted, preview))
        originals.append(
            {"id": identifier, "label": label, "kind": "reader-preview", "path": _relative(preview, root)}
        )

    manifest = {
        "schema_version": DOSSIER_SCHEMA_VERSION,
        "title": "软件生命周期审阅资料",
        "locale": "zh-CN",
        "sections": [
            {
                "id": "prd",
                "role": "prd",
                "title": "产品需求文档（PRD）",
                "artifact": {
                    "kind": "p1-prd",
                    "identity": "human-projection",
                    "path": _relative(prd_projection, root),
                    "canonical_path": _relative(prd["canonical_path"], root),
                    "standalone_html_path": originals[0]["path"],
                },
            },
            {
                "id": "product-flow",
                "role": "product-diagram",
                "title": "产品与业务图",
                "bundle_path": _relative(review_maps["p1"], root),
            },
            {
                "id": "esp",
                "role": "esp",
                "title": "架构设计与工程规格（ESP）",
                "artifact": {
                    "kind": "p2-esp",
                    "identity": "human-projection",
                    "path": _relative(esp_projection, root),
                    "canonical_path": _relative(esp["canonical_path"], root),
                    "standalone_html_path": originals[1]["path"],
                },
            },
            {
                "id": "architecture-flow",
                "role": "architecture-diagram",
                "title": "架构与数据图",
                "bundle_path": _relative(review_maps["p2"], root),
            },
            {
                "id": "action-cards",
                "role": "action-cards",
                "title": "实施行动卡（Action Cards）",
                "validation_path": _relative(validation_path, root),
                "cards": ordered_cards,
            },
        ],
        "originals": originals,
        "source_adapter": "v1.6-human-semantic-projection",
    }
    manifest_path = root / DEFAULT_DOSSIER_MANIFEST_PATH
    _atomic_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    report = refresh_human_review_dossier(root, manifest_path=manifest_path)
    if not report.get("dossier_ready"):
        raise AssemblyError(str(report.get("dossier_error") or "dossier was not ready"))
    return {**report, "manifest": str(manifest_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = assemble_v16_dossier(args.case_root)
    except (AssemblyError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "not-ready", "detail": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "generated", **report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
