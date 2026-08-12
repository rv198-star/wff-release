#!/usr/bin/env python3
"""Generate source-bound P1/P2 review-map bundles outside the translation lane."""

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

from common.review_map_generation import (  # noqa: E402
    review_map_sources,
    sha256_file,
    source_receipt,
    validate_review_map_artifact,
)
from release.run_reader_translation_lane import _ensure_deps  # noqa: E402


MANIFEST_SCHEMA = "wff.human-review-map-manifest.v1"
KIND_CANONICAL = {
    "p1": "phase-1/phase-1-product-requirements-document-main-document.md",
    "p2": "phase-2/engineering-spec-pack.md",
}


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
        if isinstance(row, dict) and str(row.get("kind")) in KIND_CANONICAL
    }


def _expected_kinds(case_root: Path) -> list[str]:
    return [kind for kind, ref in KIND_CANONICAL.items() if (case_root / ref).is_file()]


def _output_path(case_root: Path, kind: str) -> Path:
    return case_root / "human-review" / "maps" / f"{kind}-review-map-bundle.json"


def run_map_lane(
    case_root: Path,
    *,
    emit_script: Path,
    locale: str = "zh-CN",
) -> dict[str, Any]:
    root = case_root.resolve()
    manifest_path = root / "human-review" / "review-map-manifest.json"
    previous = _previous_entries(manifest_path)
    dep_error, python_path = _ensure_deps(emit_script.resolve().parents[2])
    entries: list[dict[str, Any]] = []
    for kind in _expected_kinds(root):
        try:
            sources = review_map_sources(root, kind)
            receipt = source_receipt(root, sources)
        except ValueError as exc:
            entries.append({"kind": kind, "status": "failed", "detail": str(exc)})
            continue
        output = _output_path(root, kind)
        old = previous.get(kind, {})
        if (
            old.get("status") == "generated"
            and validate_review_map_artifact(
                case_root=root,
                kind=kind,
                output_path=output,
                expected_source_hashes=old.get("source_hashes"),
                expected_sha256=old.get("sha256"),
            )
        ):
            entries.append({**old, "detail": "reused current source-bound review map"})
            continue
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
        if not validate_review_map_artifact(
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
                    "detail": "generated review-map bundle failed parent-lane validation",
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
                "detail": "Agentic review-map bundle generated and validated",
            }
        )
    expected = _expected_kinds(root)
    generated = [row["kind"] for row in entries if row.get("status") == "generated"]
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_locale": locale,
        "status": "generated" if generated == expected and expected else "failed",
        "entries": entries,
    }
    _atomic_manifest(manifest_path, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root", required=True, type=Path)
    parser.add_argument("--target-locale", default="zh-CN")
    parser.add_argument(
        "--emit-script",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "common" / "review_map_generation.py",
    )
    args = parser.parse_args(argv)
    report = run_map_lane(
        args.case_root,
        emit_script=args.emit_script,
        locale=args.target_locale,
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "generated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
