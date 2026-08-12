#!/usr/bin/env python3
"""Run the non-blocking v1.6 human semantic projection lane."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.human_semantic_projection import (  # noqa: E402
    PROJECTION_KINDS,
    projection_source_refs,
    refresh_projection_rendering,
    sha256_file,
    source_receipt,
    validate_projection_artifact,
)
from release.audit_human_review_decision_quality import audit_case  # noqa: E402
from release.run_reader_translation_lane import _ensure_deps  # noqa: E402


MANIFEST_SCHEMA = "wff.human-semantic-projection-manifest.v1"


def _atomic_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _previous_entries(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return {
        str(row.get("kind")): row
        for row in payload.get("entries", [])
        if isinstance(row, dict) and str(row.get("kind")) in PROJECTION_KINDS
    }


def _output_path(case_root: Path, kind: str) -> Path:
    return case_root / "human-review" / "projections" / f"{kind}.json"


def _expected_kinds(case_root: Path) -> list[str]:
    root = case_root.resolve()
    expected: list[str] = []
    if (root / "phase-1" / "phase-1-product-requirements-document-main-document.md").is_file():
        expected.append("prd-core")
    if (root / "phase-2" / "engineering-spec-pack.md").is_file():
        expected.append("esp-core")
    if (root / "phase-3" / "action-cards" / "validation.json").is_file():
        expected.append("action-card-set")
    return expected


def run_projection_lane(
    case_root: Path,
    *,
    emit_script: Path,
    locale: str = "zh-CN",
) -> dict[str, Any]:
    root = case_root.resolve()
    manifest_path = root / "human-review" / "semantic-projection-manifest.json"
    previous = _previous_entries(manifest_path)
    dep_error, python_path = _ensure_deps(emit_script.resolve().parents[2])
    entries: list[dict[str, Any]] = []
    expected = _expected_kinds(root)

    for kind in expected:
        refs = projection_source_refs(root, kind)
        receipt = source_receipt(root, refs)
        output = _output_path(root, kind)
        old = previous.get(kind, {})
        if (
            old.get("status") == "generated"
            and validate_projection_artifact(
                case_root=root,
                kind=kind,
                output_path=output,
                expected_source_hashes=old.get("source_hashes"),
                expected_sha256=old.get("sha256"),
            )
        ):
            entries.append({**old, "detail": "reused current source-bound human projection"})
            continue
        if old.get("status") == "generated" and output.is_file():
            try:
                refreshed = refresh_projection_rendering(
                    case_root=root,
                    kind=kind,
                    output_path=output,
                    locale=locale,
                )
                refreshed_sha256 = str(refreshed["sha256"])
                if validate_projection_artifact(
                    case_root=root,
                    kind=kind,
                    output_path=output,
                    expected_source_hashes=receipt,
                    expected_sha256=refreshed_sha256,
                ):
                    quality_path = Path(
                        str(refreshed["decision_quality_path"])
                    ).resolve()
                    entries.append(
                        {
                            "kind": kind,
                            "status": "generated",
                            "path": output.relative_to(root).as_posix(),
                            "sha256": refreshed_sha256,
                            "source_hashes": receipt,
                            "decision_quality_verdict": str(
                                refreshed["decision_quality_verdict"]
                            ),
                            "decision_quality_score": float(
                                refreshed["decision_quality_score"]
                            ),
                            "decision_quality_path": quality_path.relative_to(
                                root
                            ).as_posix(),
                            "decision_quality_sha256": str(
                                refreshed["decision_quality_sha256"]
                            ),
                            "architecture_reconstruction_input": refreshed.get(
                                "architecture_reconstruction_input"
                            ),
                            "detail": (
                                "reused accepted structured review model and "
                                "deterministically refreshed reader rendering"
                            ),
                        }
                    )
                    continue
            except Exception:
                pass
        if dep_error:
            entries.append({"kind": kind, "status": "failed", "detail": dep_error["error"]})
            continue
        proc = subprocess.run(
            [
                python_path,
                str(emit_script),
                "--case-root",
                str(root),
                "--kind",
                kind,
                "--output",
                str(output),
                "--target-locale",
                locale,
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        payload: dict[str, Any] = {}
        try:
            payload = json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            pass
        if proc.returncode or payload.get("status") != "generated":
            entries.append(
                {
                    "kind": kind,
                    "status": "failed",
                    "detail": str(payload.get("detail") or proc.stderr.strip() or proc.stdout[:500]),
                }
            )
            continue
        output_sha256 = sha256_file(output)
        if not validate_projection_artifact(
            case_root=root,
            kind=kind,
            output_path=output,
            expected_source_hashes=receipt,
            expected_sha256=output_sha256,
        ):
            entries.append(
                {
                    "kind": kind,
                    "status": "failed",
                    "detail": "generated human projection failed parent-lane validation",
                }
            )
            continue
        quality_path = Path(str(payload.get("decision_quality_path") or "")).resolve()
        if not quality_path.is_file() or not quality_path.is_relative_to(root):
            entries.append(
                {
                    "kind": kind,
                    "status": "failed",
                    "detail": "decision-quality report is missing or outside the case root",
                }
            )
            continue
        entries.append(
            {
                "kind": kind,
                "status": "generated",
                "path": output.relative_to(root).as_posix(),
                "sha256": output_sha256,
                "source_hashes": receipt,
                "decision_quality_verdict": str(
                    payload.get("decision_quality_verdict") or "review-bound"
                ),
                "decision_quality_score": float(
                    payload.get("decision_quality_score") or 0.0
                ),
                "decision_quality_path": quality_path.relative_to(root).as_posix(),
                "decision_quality_sha256": str(
                    payload.get("decision_quality_sha256") or ""
                ),
                "architecture_reconstruction_input": payload.get(
                    "architecture_reconstruction_input"
                ),
                "detail": "human-first semantic projection generated and decision-quality audited",
            }
        )
        _atomic_manifest(
            manifest_path,
            {
                "schema_version": MANIFEST_SCHEMA,
                "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "target_locale": locale,
                "status": "running",
                "entries": entries,
            },
        )

    generated = [row["kind"] for row in entries if row.get("status") == "generated"]
    quality_verdicts = [
        str(row.get("decision_quality_verdict") or "review-bound")
        for row in entries
        if row.get("status") == "generated"
    ]
    quality_status = (
        "pass"
        if quality_verdicts and all(item == "pass" for item in quality_verdicts)
        else "review-bound"
        if quality_verdicts and all(item in {"pass", "review-bound"} for item in quality_verdicts)
        else "failed"
    )
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_locale": locale,
        "status": "generated" if generated == expected and expected else "failed",
        "decision_quality_status": quality_status,
        "expected_kinds": expected,
        "entries": entries,
    }
    if manifest["status"] == "generated":
        case_audit = audit_case(root, kinds=expected)
        manifest["decision_quality_status"] = case_audit["verdict"]
        manifest["decision_quality_audit_json"] = Path(
            case_audit["json_path"]
        ).relative_to(root).as_posix()
        manifest["decision_quality_audit_markdown"] = Path(
            case_audit["markdown_path"]
        ).relative_to(root).as_posix()
    _atomic_manifest(manifest_path, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root", required=True, type=Path)
    parser.add_argument("--target-locale", default="zh-CN")
    parser.add_argument(
        "--emit-script",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "common" / "human_semantic_projection.py",
    )
    args = parser.parse_args(argv)
    try:
        report = run_projection_lane(
            args.case_root,
            emit_script=args.emit_script,
            locale=args.target_locale,
        )
    except Exception as exc:
        print(json.dumps({"status": "failed", "detail": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "generated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
