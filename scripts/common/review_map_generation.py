#!/usr/bin/env python3
"""Agentic P1/P2 review-map authoring over bounded structured sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


REVIEW_MAP_KIND_BY_TARGET = {
    "p1-prd": "p1",
    "p2-esp": "p2",
}

REVIEW_MAP_ROLE = {
    "p1": "product-diagram",
    "p2": "architecture-diagram",
}

REVIEW_MAP_SCHEMA = {
    "p1": "wff.p1-human-review-map-bundle.v1",
    "p2": "wff.p2-human-review-map-bundle.v1",
}

REVIEW_MAP_SOURCES = {
    "p1": (
        "phase-1/phase1-business-release-truth-pack.json",
        "phase-1/.phase1-evidence/p1-semantic-authoring-spine.json",
        "phase-1/phase1-operating-baseline-model.json",
    ),
    "p2": (
        "phase-2/stage-01-architecture-definition-and-boundary-setting.claim-control.json",
        "phase-2/.phase2-evidence/implementation-component-catalog.json",
        "phase-2/.phase2-evidence/operation-behavior-semantics.json",
        "phase-2/.phase2-evidence/p1-value-to-p2-operation-resolution-matrix.json",
    ),
}


class ReviewMapGenerationError(ValueError):
    """The current structured sources cannot produce an accepted review map."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def review_map_kind_for_target(kind: str) -> str | None:
    return REVIEW_MAP_KIND_BY_TARGET.get(kind)


def review_map_output_path(canonical: Path, locale: str) -> Path:
    return canonical.with_name(f"{canonical.stem}.review-map-bundle.{locale}.json")


def review_map_sources(case_root: Path, kind: str, *, require: bool = True) -> list[Path]:
    if kind not in REVIEW_MAP_SOURCES:
        raise ReviewMapGenerationError(f"unsupported review-map kind: {kind}")
    root = case_root.resolve()
    sources: list[Path] = []
    missing: list[str] = []
    for ref in REVIEW_MAP_SOURCES[kind]:
        path = (root / ref).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
            missing.append(ref)
        else:
            sources.append(path)
    if missing and require:
        raise ReviewMapGenerationError(
            f"{kind} review-map structured sources are missing: {', '.join(missing)}"
        )
    return sources


def source_receipt(case_root: Path, sources: list[Path]) -> dict[str, str]:
    root = case_root.resolve()
    receipt: dict[str, str] = {}
    for source in sources:
        resolved = source.resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.is_symlink():
            raise ReviewMapGenerationError("review-map sources must be regular files inside case root")
        receipt[resolved.relative_to(root).as_posix()] = sha256_file(resolved)
    return receipt


def _map_contract(kind: str) -> str:
    if kind == "p1":
        return """The output schema_version is wff.p1-human-review-map-bundle.v1.
views must contain exactly these types in order:
1. business-landscape: common title fields, source_refs, roles(id/label/description), and use_cases(id/name/goal/responsibilities/features). responsibilities must cover every role and use only primary/support/review/none.
2. business-scenarios: common title fields, source_refs, and scenarios. Each scenario has id/label/title/summary, lanes(id/label/description), steps(id/lane_id/title/detail/tone), context, object_chain, and caption. tone is one of business/architecture/signal/review."""
    return """The output schema_version is wff.p2-human-review-map-bundle.v1.
views must contain exactly these types in order:
1. technical-architecture: common title fields, source_refs, system_label, external_nodes, layers(id/name/namespace/nodes), and crosscutting. Node state is one of standard/domain/review-bound.
2. service-modules: common title fields, source_refs, crosscutting, and modules with services and public operations. operation kind is one of C/Q/E.
3. critical-sequences: common title fields, source_refs, and sequences with participants and steps. step kind is one of sync/async/return and from/to must reference participant ids.
Every view's common title fields are id/title/summary/tag/diagram_title/diagram_note/caption."""


def _prompt(case_root: Path, kind: str, sources: list[Path], locale: str) -> str:
    from common.human_review_map_contract import review_map_bundle_schema

    root = case_root.resolve()
    allowed_refs = [source.resolve().relative_to(root).as_posix() for source in sources]
    source_blocks = []
    for source, ref in zip(sources, allowed_refs):
        source_blocks.append(f"\n## SOURCE: {ref}\n{source.read_text(encoding='utf-8')}")
    return "\n".join(
        [
            f"Author one {locale} human-review map bundle from the structured authority excerpts below.",
            "Return only one JSON object. Do not wrap it in a string or markdown fence.",
            "Interpret business and architecture semantics; do not derive relations from array order or file order.",
            "Include only claims supported by the supplied sources. Preserve uncertainty as review-bound and do not invent missing truth.",
            "Keep the views selective and decision-useful rather than exhaustive implementation inventories.",
            "Every source_refs item must be copied exactly from this allowed list:",
            json.dumps(allowed_refs, ensure_ascii=False),
            _map_contract(kind),
            "The complete output must satisfy this JSON Schema:",
            json.dumps(
                review_map_bundle_schema("prd-core" if kind == "p1" else "esp-core"),
                ensure_ascii=False,
            ),
            *source_blocks,
        ]
    )


def _parse_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    candidate = re.sub(r"^```(?:json)?\s*\n", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\n```\s*$", "", candidate)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ReviewMapGenerationError(f"review-map response is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReviewMapGenerationError("review-map response must be a JSON object")
    return payload


def _validate_bundle(
    *,
    case_root: Path,
    kind: str,
    payload: dict[str, Any],
    allowed_refs: set[str],
) -> dict[str, Any]:
    expected_schema = REVIEW_MAP_SCHEMA[kind]
    if payload.get("schema_version") != expected_schema:
        raise ReviewMapGenerationError(f"review-map schema must be {expected_schema}")
    from release.render_human_review_dossier import normalize_review_bundle_payload

    try:
        normalized = normalize_review_bundle_payload(payload, role=REVIEW_MAP_ROLE[kind])
    except ValueError as exc:
        raise ReviewMapGenerationError(f"review-map contract is invalid: {exc}") from exc
    for view in normalized["views"]:
        unknown = sorted(set(view["source_refs"]) - allowed_refs)
        if unknown:
            raise ReviewMapGenerationError(
                "review-map contains source refs outside the accepted packet: " + ", ".join(unknown)
            )
    return normalized


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
        os.replace(temporary, path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def generate_review_map_bundle(
    *,
    case_root: Path,
    kind: str,
    locale: str,
    sources: list[Path],
    output_path: Path,
    invoke: Callable[[str, str], str],
) -> dict[str, Any]:
    receipt = source_receipt(case_root, sources)
    system = (
        "You are a senior product and architecture reviewer. Semantic judgment belongs to you; "
        "the surrounding workflow will only validate and render your source-grounded output."
    )
    prompt = _prompt(case_root, kind, sources, locale)
    error = ""
    previous_candidate = ""
    for attempt in range(2):
        user_prompt = prompt
        if error:
            user_prompt += (
                "\n\nYour previous candidate failed deterministic validation and is included below. "
                "Repair that candidate rather than "
                "starting over. Return the complete corrected bundle and address this deterministic "
                f"validation error: {error}\n\n## PREVIOUS INVALID BUNDLE\n{previous_candidate}"
            )
        raw_candidate = invoke(system, user_prompt)
        previous_candidate = raw_candidate
        try:
            payload = _parse_json_object(raw_candidate)
            normalized = _validate_bundle(
                case_root=case_root,
                kind=kind,
                payload=payload,
                allowed_refs=set(receipt),
            )
        except ReviewMapGenerationError as exc:
            error = str(exc)
            if attempt == 0:
                continue
            raise
        _atomic_json(output_path, normalized)
        return {
            "path": str(output_path.resolve()),
            "sha256": sha256_file(output_path),
            "source_hashes": receipt,
        }
    raise ReviewMapGenerationError(error or "review-map generation failed")


def validate_review_map_artifact(
    *,
    case_root: Path,
    kind: str,
    output_path: Path,
    expected_source_hashes: object,
    expected_sha256: object | None = None,
) -> bool:
    if not output_path.is_file() or output_path.is_symlink() or not isinstance(expected_source_hashes, dict):
        return False
    try:
        if expected_sha256 is not None and sha256_file(output_path) != expected_sha256:
            return False
        sources = review_map_sources(case_root, kind)
        receipt = source_receipt(case_root, sources)
        if receipt != expected_source_hashes:
            return False
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return False
        _validate_bundle(
            case_root=case_root,
            kind=kind,
            payload=payload,
            allowed_refs=set(receipt),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ReviewMapGenerationError):
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root", required=True, type=Path)
    parser.add_argument("--kind", required=True, choices=("p1", "p2"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-locale", default="zh-CN")
    parser.add_argument("--model")
    parser.add_argument("--api-base")
    parser.add_argument("--api-key")
    args = parser.parse_args(argv)

    from common.emit_reader_translation import _call_llm, _get_client, _read_translation_config

    config = _read_translation_config()
    model = args.model or config.get("model", "gpt-5.4")
    api_base = args.api_base or config.get("api_base_url") or os.environ.get("OPENAI_BASE_URL")
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    client = _get_client(api_base=api_base, api_key=api_key)

    def invoke(system_prompt: str, user_prompt: str) -> str:
        return _call_llm(
            client=client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=int(config.get("max_tokens_per_segment", 32768)),
            timeout=float(config.get("timeout_seconds", 1800)),
        ).content

    try:
        report = generate_review_map_bundle(
            case_root=args.case_root.resolve(),
            kind=args.kind,
            locale=args.target_locale,
            sources=review_map_sources(args.case_root.resolve(), args.kind),
            output_path=args.output.resolve(),
            invoke=invoke,
        )
    except (OSError, UnicodeError, ReviewMapGenerationError, RuntimeError) as exc:
        print(json.dumps({"status": "failed", "kind": args.kind, "detail": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "generated", "kind": args.kind, **report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
