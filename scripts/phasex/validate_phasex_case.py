#!/usr/bin/env python3
"""
Validate a PhaseX Wave-1 case root for profile fit and minimum authored quality.
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

from common.script_data_assets import load_script_json_asset
from phasex.scaffold_phasex_case import PROFILE_METHOD_BACKBONES, PROFILE_OUTPUTS


MANIFEST_NAME = "phasex-wave1-manifest.md"
SCAFFOLD_MARKERS = ("state: `fresh-target`", "scaffolded_target:")
PROFILE_RE = re.compile(r"selected_profile:\s*`([^`]+)`")

WFF_SCRIPT_DATA_ASSETS = ("scripts/phasex/data/validation-snippet-rules.json",)
_VALIDATION_SNIPPET_RULES = load_script_json_asset(__file__, "validation-snippet-rules.json")


def _snippet_rule_map_from_payload(payload: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(payload, dict):
        return {}
    return {
        str(path): tuple(str(snippet) for snippet in snippets)
        for path, snippets in payload.items()
        if isinstance(snippets, list)
    }


BASE_REQUIRED_SNIPPETS = _snippet_rule_map_from_payload(_VALIDATION_SNIPPET_RULES.get("base_required_snippets", {}))

PROFILE_SPECIFIC_SNIPPETS = {
    str(profile): _snippet_rule_map_from_payload(files)
    for profile, files in _VALIDATION_SNIPPET_RULES.get("profile_specific_snippets", {}).items()
    if isinstance(files, dict)
}


def extract_selected_profile(text: str) -> str:
    match = PROFILE_RE.search(text)
    return match.group(1) if match else ""


def inspect_case(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / MANIFEST_NAME
    manifest_exists = manifest_path.exists()
    manifest_text = manifest_path.read_text(encoding="utf-8") if manifest_exists else ""
    selected_profile = extract_selected_profile(manifest_text)
    profile_known = selected_profile in PROFILE_OUTPUTS

    issues: list[str] = []
    warnings: list[str] = []

    if not manifest_exists:
        issues.append(f"missing {MANIFEST_NAME}")
    if manifest_exists and not selected_profile:
        issues.append("manifest missing selected_profile")
    if selected_profile and not profile_known:
        issues.append(f"unknown selected_profile: {selected_profile}")

    manifest_backbone_missing: list[str] = []
    if profile_known:
        for item in PROFILE_METHOD_BACKBONES[selected_profile]:
            if item not in manifest_text:
                manifest_backbone_missing.append(item)
        if manifest_backbone_missing:
            issues.append(
                "manifest missing method backbone entries: "
                + ", ".join(manifest_backbone_missing)
            )

    file_rows: list[dict[str, Any]] = []
    missing_files: list[str] = []
    scaffold_files: list[str] = []
    content_issues: list[str] = []

    if profile_known:
        required_filenames = [filename for _, filename, _, _ in PROFILE_OUTPUTS[selected_profile]]
    else:
        required_filenames = []

    for filename in required_filenames:
        path = output_dir / filename
        exists = path.exists()
        still_scaffold_target = False
        text = ""
        if exists:
            text = path.read_text(encoding="utf-8")
            still_scaffold_target = any(marker in text for marker in SCAFFOLD_MARKERS)
        else:
            missing_files.append(filename)
        if still_scaffold_target:
            scaffold_files.append(filename)
        if exists and not still_scaffold_target:
            missing_snippets = [
                snippet for snippet in BASE_REQUIRED_SNIPPETS.get(filename, ()) if snippet not in text
            ]
            if selected_profile in PROFILE_SPECIFIC_SNIPPETS:
                missing_snippets.extend(
                    snippet
                    for snippet in PROFILE_SPECIFIC_SNIPPETS[selected_profile].get(filename, ())
                    if snippet not in text
                )
            if missing_snippets:
                content_issues.append(
                    f"{filename} missing required authored content: {', '.join(missing_snippets)}"
                )
            if (
                filename == "wff-x-intake-target-driver.md"
                and "related_third_party_dependencies" in text
            ):
                content_issues.append(
                    "wff-x-intake-target-driver.md uses deprecated field name: related_third_party_dependencies"
                )
        file_rows.append(
            {
                "file": filename,
                "exists": exists,
                "still_scaffold_target": still_scaffold_target,
                "required": True,
            }
        )

    extra_wave1_files = sorted(
        path.name
        for path in output_dir.glob("wff-x-*.md")
        if path.name not in required_filenames
    )
    if extra_wave1_files:
        warnings.append(
            "extra Wave-1 files outside selected profile: " + ", ".join(extra_wave1_files)
        )

    legacy_wave1_files = sorted(path.name for path in output_dir.glob("px-sk-*.md"))
    if legacy_wave1_files:
        issues.append(
            "legacy PhaseX PX-SK files are no longer accepted: "
            + ", ".join(legacy_wave1_files)
        )

    if missing_files:
        issues.append("missing required files: " + ", ".join(missing_files))
    if scaffold_files:
        issues.append("files still scaffold-only: " + ", ".join(scaffold_files))
    issues.extend(content_issues)

    if not manifest_exists or not profile_known or missing_files:
        status = "invalid-root"
    elif scaffold_files:
        status = "scaffold-only"
    elif content_issues or manifest_backbone_missing or legacy_wave1_files:
        status = "authored-invalid"
    else:
        status = "authored-valid"

    return {
        "output_dir": str(output_dir),
        "manifest_exists": manifest_exists,
        "selected_profile": selected_profile,
        "profile_known": profile_known,
        "manifest_backbone_missing": manifest_backbone_missing,
        "file_rows": file_rows,
        "missing_files": missing_files,
        "scaffold_files": scaffold_files,
        "extra_wave1_files": extra_wave1_files,
        "status": status,
        "passed": status == "authored-valid",
        "issues": issues,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a PhaseX Wave-1 brownfield case root."
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    result = inspect_case(Path(args.output_dir).resolve())
    payload = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload.rstrip())
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
