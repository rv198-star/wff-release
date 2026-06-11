#!/usr/bin/env python3
"""Generate a human-review surface without moving canonical WFF artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.script_data_assets import load_script_json_asset


HUMAN_REVIEW_DIRNAME = "human-review"
ARTIFACTS_DIRNAME = "artifacts"


@dataclass(frozen=True)
class HumanReviewArtifactRule:
    label: str
    source: str
    category: str
    optional: bool = True
    note: str = ""


@dataclass(frozen=True)
class HumanReviewSurfaceConfig:
    phase: str
    title: str
    primary_instruction: str
    artifact_rules: tuple[HumanReviewArtifactRule, ...]
    machine_dirs: tuple[str, ...]
    claim_ceiling_notes: tuple[str, ...]


WFF_SCRIPT_DATA_ASSETS = ("scripts/common/data/human-review-surface-configs.json",)


def _artifact_rule_from_payload(payload: dict[str, Any]) -> HumanReviewArtifactRule:
    return HumanReviewArtifactRule(
        label=str(payload.get("label") or ""),
        source=str(payload.get("source") or ""),
        category=str(payload.get("category") or ""),
        optional=bool(payload.get("optional", True)),
        note=str(payload.get("note") or ""),
    )


def _surface_config_from_payload(payload: dict[str, Any]) -> HumanReviewSurfaceConfig:
    artifact_rules = tuple(
        _artifact_rule_from_payload(row)
        for row in payload.get("artifact_rules", [])
        if isinstance(row, dict)
    )
    return HumanReviewSurfaceConfig(
        phase=str(payload.get("phase") or ""),
        title=str(payload.get("title") or ""),
        primary_instruction=str(payload.get("primary_instruction") or ""),
        artifact_rules=artifact_rules,
        machine_dirs=tuple(str(item) for item in payload.get("machine_dirs", [])),
        claim_ceiling_notes=tuple(str(item) for item in payload.get("claim_ceiling_notes", [])),
    )


def _load_human_review_surface_payload() -> dict[str, Any]:
    loaded = load_script_json_asset(__file__, "human-review-surface-configs.json")
    if not isinstance(loaded, dict):
        raise TypeError("human-review-surface-configs.json must contain an object")
    return loaded


_HUMAN_REVIEW_SURFACE_PAYLOAD = _load_human_review_surface_payload()
CATEGORY_LABELS = {str(key): str(value) for key, value in _HUMAN_REVIEW_SURFACE_PAYLOAD["category_labels"].items()}
SURFACE_CONFIGS = {
    str(key): _surface_config_from_payload(value)
    for key, value in _HUMAN_REVIEW_SURFACE_PAYLOAD["surface_configs"].items()
    if isinstance(value, dict)
}
PHASE_ALIASES = {str(key): str(value) for key, value in _HUMAN_REVIEW_SURFACE_PAYLOAD["phase_aliases"].items()}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_phase(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if key not in PHASE_ALIASES:
        raise ValueError(f"unsupported human-review phase: {raw!r}")
    return PHASE_ALIASES[key]


def is_reader_sidecar(path: Path) -> bool:
    name = path.name
    return ".reader." in name or name.endswith(".integrity.json") or name.endswith(".progress.jsonl")


def reader_path_for(canonical: Path) -> Path | None:
    if canonical.suffix.lower() != ".md":
        return None
    return canonical.with_name(f"{canonical.stem}.reader.zh-CN.md")


def select_human_read_source(canonical: Path) -> tuple[Path, str]:
    reader_path = reader_path_for(canonical)
    if reader_path and reader_path.exists():
        return reader_path, "reader-translation"
    if canonical.suffix.lower() == ".md":
        return canonical, "canonical-fallback"
    return canonical, "canonical-evidence"


def expand_rule(output_dir: Path, rule: HumanReviewArtifactRule) -> list[Path]:
    if any(char in rule.source for char in "*?[]"):
        return sorted(
            path
            for path in output_dir.glob(rule.source)
            if path.is_file() and not is_reader_sidecar(path)
        )
    path = output_dir / rule.source
    return [path] if path.exists() and path.is_file() else []


def clean_generated_artifacts_dir(surface_dir: Path) -> Path:
    artifacts_dir = surface_dir / ARTIFACTS_DIRNAME
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


def copy_selected_artifact(
    *,
    output_dir: Path,
    artifacts_dir: Path,
    canonical: Path,
    category: str,
) -> dict[str, Any]:
    selected, source_kind = select_human_read_source(canonical)
    try:
        selected_rel = selected.relative_to(output_dir)
    except ValueError:
        selected_rel = Path(selected.name)
    target = artifacts_dir / category / selected_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(selected, target)
    canonical_rel = canonical.relative_to(output_dir).as_posix()
    human_rel = target.relative_to(output_dir).as_posix()
    return {
        "canonical_path": canonical_rel,
        "selected_source_path": selected_rel.as_posix(),
        "human_review_path": human_rel,
        "source_kind": source_kind,
    }


def build_machine_dir_rows(output_dir: Path, config: HumanReviewSurfaceConfig) -> list[dict[str, Any]]:
    rows = []
    for raw in config.machine_dirs:
        path = output_dir / raw
        rows.append(
            {
                "path": raw,
                "exists": path.exists(),
                "meaning": "AI / gate working evidence; inspect when a primary artifact points here or a defect requires detail.",
            }
        )
    return rows


def emit_human_review_surface(output_dir: Path, phase: str) -> dict[str, Any]:
    normalized_phase = normalize_phase(phase)
    config = SURFACE_CONFIGS[normalized_phase]
    root = output_dir.resolve()
    surface_dir = root / HUMAN_REVIEW_DIRNAME
    surface_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = clean_generated_artifacts_dir(surface_dir)

    artifacts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for rule in config.artifact_rules:
        expanded = expand_rule(root, rule)
        if not expanded:
            missing.append(
                {
                    "label": rule.label,
                    "source": rule.source,
                    "category": rule.category,
                    "optional": rule.optional,
                    "note": rule.note,
                }
            )
            continue
        for canonical in expanded:
            copied = copy_selected_artifact(
                output_dir=root,
                artifacts_dir=artifacts_dir,
                canonical=canonical,
                category=rule.category,
            )
            key = (rule.label, copied["canonical_path"])
            if key in seen:
                continue
            seen.add(key)
            artifacts.append(
                {
                    "label": rule.label,
                    "category": rule.category,
                    "category_label": CATEGORY_LABELS.get(rule.category, rule.category),
                    "optional": rule.optional,
                    "note": rule.note,
                    **copied,
                }
            )

    machine_dirs = build_machine_dir_rows(root, config)
    manifest = {
        "schema_version": "human-review-surface.v1",
        "generated_at": utc_now_iso(),
        "phase": normalized_phase,
        "title": config.title,
        "surface_dir": HUMAN_REVIEW_DIRNAME,
        "primary_instruction": config.primary_instruction,
        "artifacts": artifacts,
        "missing_artifacts": missing,
        "machine_working_areas": machine_dirs,
        "claim_ceiling_notes": list(config.claim_ceiling_notes),
        "canonical_authority_note": (
            "human-review artifacts are copies for reading; canonical source artifacts remain at their original paths"
        ),
    }
    (surface_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (surface_dir / "INDEX.md").write_text(render_index(manifest), encoding="utf-8")
    return manifest


def render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    output.extend("| " + " | ".join(row) + " |" for row in rows)
    return output


def render_index(manifest: dict[str, Any]) -> str:
    lines = [
        f"# {manifest['title']}",
        "",
        "## How to Read",
        "",
        f"- {manifest['primary_instruction']}",
        "- Read `gate / verdict` items before treating any stage as closed.",
        "- Use copied files here for review convenience only; canonical source artifacts remain at their original paths.",
        "",
        "## Main Artifacts",
        "",
    ]

    artifact_rows = []
    for artifact in manifest["artifacts"]:
        artifact_rows.append(
            [
                str(artifact["label"]),
                str(artifact["category_label"]),
                f"`{artifact['human_review_path']}`",
                f"`{artifact['canonical_path']}`",
                str(artifact["source_kind"]),
            ]
        )
    lines.extend(render_table(["Artifact", "Kind", "Human copy", "Canonical source", "Source mode"], artifact_rows) or ["No artifacts copied."])

    required_missing = [item for item in manifest["missing_artifacts"] if not item.get("optional")]
    optional_missing = [item for item in manifest["missing_artifacts"] if item.get("optional")]
    if required_missing or optional_missing:
        lines.extend(["", "## Missing Or Not Generated", ""])
        missing_rows = [
            [
                str(item["label"]),
                f"`{item['source']}`",
                "optional" if item.get("optional") else "required",
            ]
            for item in [*required_missing, *optional_missing]
        ]
        lines.extend(render_table(["Artifact", "Expected source", "Status"], missing_rows))

    machine_rows = [
        [
            f"`{item['path']}`",
            "yes" if item["exists"] else "no",
            str(item["meaning"]),
        ]
        for item in manifest["machine_working_areas"]
    ]
    if machine_rows:
        lines.extend(["", "## AI / Gate Working Areas", ""])
        lines.extend(render_table(["Path", "Exists", "When to inspect"], machine_rows))

    lines.extend(["", "## Claim Ceiling", ""])
    for note in manifest["claim_ceiling_notes"]:
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Generated Surface Boundary",
            "",
            "- This directory is additive and reader-facing.",
            "- It must not replace phase contracts, trace registries, gates, or retained proof evidence.",
            "- Re-run the phase or `human_review_surface.py` after upstream artifacts change.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate WFF human-review artifact copies and INDEX.md.")
    parser.add_argument("--phase", required=True, choices=sorted(PHASE_ALIASES))
    parser.add_argument("--output-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = emit_human_review_surface(Path(args.output_dir), args.phase)
    print(json.dumps({"human_review_index": str(Path(args.output_dir) / HUMAN_REVIEW_DIRNAME / "INDEX.md"), "artifact_count": len(manifest["artifacts"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
