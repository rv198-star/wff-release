#!/usr/bin/env python3
"""Build one offline entry point for existing WFF human-review HTML artifacts."""

from __future__ import annotations

import argparse
import html
import importlib
import json
import os
import re
import sys
import webbrowser
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Sequence
from urllib.parse import quote

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.script_data_assets import load_script_text_asset


WFF_SCRIPT_DATA_ASSETS = ("scripts/release/data/human-review-portal.html.template",)

PORTAL_SCHEMA_VERSION = "wff-human-review-html-portal.v1"
DEFAULT_PORTAL_PATH = Path("human-review/index.html")
MANIFEST_FILENAME = "html-artifacts.json"
DOSSIER_MANIFEST_FILENAME = "dossier-manifest.json"
DOSSIER_SCHEMA_VERSION = "human-review-dossier-manifest.v1"
HTML_PROBE_LIMIT = 256 * 1024
PRUNED_DIRS = frozenset(
    {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__"}
)
SUPPORTED_MARKERS = {
    "reader-preview.v1": "reader-preview",
    "interaction-map.v1": "interaction-map",
}
KIND_ORDER = {"reader-preview": 0, "interaction-map": 1}
VIEW_KIND_LABELS = {
    "business_interaction": "业务交互图",
    "system_interaction": "架构与数据交互图",
    "current_state_impact": "现状影响图",
}


class PortalError(ValueError):
    """The requested portal root or output violates the navigation contract."""


@dataclass(frozen=True)
class HumanReviewHtmlArtifact:
    kind: str
    label: str
    path: Path
    type_label: str
    marker: str


class _ArtifactMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.marker = ""
        self.label = ""
        self.view_kind = ""
        self.body_reader_marker = False
        self.body_interaction_marker = False
        self.reader_preamble = False
        self.reader_article = False
        self.csp = ""
        self._inside_title = False
        self._title_parts: list[str] = []

    @property
    def title(self) -> str:
        return " ".join("".join(self._title_parts).split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {str(key).lower(): str(value or "") for key, value in attrs}
        normalized_tag = tag.lower()
        if normalized_tag == "title":
            self._inside_title = True
            return
        if normalized_tag == "meta":
            name = values.get("name", "").strip().lower()
            if name == "wff-human-review-artifact":
                self.marker = values.get("content", "").strip()
            elif name == "wff-human-review-label":
                self.label = values.get("content", "").strip()
            elif values.get("http-equiv", "").strip().lower() == "content-security-policy":
                self.csp = values.get("content", "")
            return
        if normalized_tag == "body":
            self.body_reader_marker = "data-wff-reader-preview" in values
            self.body_interaction_marker = "data-wff-interaction-map" in values
            self.view_kind = values.get("data-view-kind", "").strip()
        classes = set(values.get("class", "").split())
        self.reader_preamble = self.reader_preamble or "reader-preamble" in classes
        self.reader_article = self.reader_article or "reader-article" in classes

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self._title_parts.append(data)


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _clean_title(title: str) -> str:
    suffixes = (
        " | WFF 阅读版",
        " · WFF 交互图附属视图",
        " · WFF interaction-map companion",
    )
    for suffix in suffixes:
        if title.endswith(suffix):
            return title[: -len(suffix)].strip()
    return title.strip()


def _parse_metadata(path: Path) -> _ArtifactMetadataParser | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            probe = handle.read(HTML_PROBE_LIMIT)
    except OSError:
        return None

    parser = _ArtifactMetadataParser()
    try:
        parser.feed(probe)
    except (AssertionError, ValueError):
        return None
    return parser


def _parse_artifact(path: Path) -> HumanReviewHtmlArtifact | None:
    parser = _parse_metadata(path)
    if parser is None:
        return None

    marker = parser.marker
    kind = SUPPORTED_MARKERS.get(marker, "")
    if not kind and parser.body_interaction_marker:
        kind = "interaction-map"
        marker = "interaction-map.v1-legacy-body-marker"
    if (
        not kind
        and path.name.endswith(".reader.zh-CN.html")
        and parser.title.endswith(" | WFF 阅读版")
        and parser.reader_preamble
        and parser.reader_article
        and "connect-src 'none'" in parser.csp
    ):
        kind = "reader-preview"
        marker = "reader-preview.v1-legacy-fingerprint"
    if not kind:
        return None

    label = parser.label or _clean_title(parser.title) or path.stem
    if kind == "reader-preview":
        type_label = "本地化阅读文档"
    else:
        type_label = VIEW_KIND_LABELS.get(parser.view_kind, "交互图")
    return HumanReviewHtmlArtifact(
        kind=kind,
        label=label,
        path=path,
        type_label=type_label,
        marker=marker,
    )


def _is_generated_portal(path: Path) -> bool:
    parser = _parse_metadata(path)
    return parser is not None and parser.marker == "human-review-portal.v1"


def is_generated_human_review_dossier(path: Path) -> bool:
    """Return whether ``path`` is a WFF continuous human-review dossier."""
    parser = _parse_metadata(path)
    return parser is not None and parser.marker == "human-review-dossier.v1"


def _is_generated_dossier_manifest(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("schema_version") == DOSSIER_SCHEMA_VERSION


def _has_valid_dossier_manifest(case_root: Path, manifest_path: Path, output_path: Path) -> bool:
    """Avoid preserving a dossier whose explicit source contract no longer validates."""
    if not _is_generated_dossier_manifest(manifest_path):
        return False
    try:
        # The full dossier is deliberately optional for phase-scoped install
        # packs. Resolve it only when that renderer is actually bundled; this
        # module otherwise remains the navigation-only fallback.
        module_name = ".".join(("release", "render_human_review_dossier"))
        dossier_module = importlib.import_module(module_name)
        dossier_error = dossier_module.DossierError
        validate_dossier_manifest = dossier_module.validate_dossier_manifest
    except (AttributeError, ImportError):
        return False

    try:
        validate_dossier_manifest(case_root, manifest_path, output_path=output_path)
    except (dossier_error, OSError, UnicodeError):
        return False
    return True


def _is_generated_manifest(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("schema_version") == PORTAL_SCHEMA_VERSION


def _portal_paths(case_root: Path, output_path: Path | None) -> tuple[Path, Path, Path]:
    root = _resolved(case_root)
    output = _resolved(output_path) if output_path is not None else root / DEFAULT_PORTAL_PATH
    if not root.is_dir():
        raise PortalError(f"case root is not a directory: {root}")
    if not _inside(output, root):
        raise PortalError("portal output must stay inside the case root")
    if output.suffix.lower() != ".html":
        raise PortalError("portal output path must end in .html")
    return root, output, output.with_name(MANIFEST_FILENAME)


def validate_portal_destination(case_root: Path, *, output_path: Path | None = None) -> None:
    _root, output, manifest_path = _portal_paths(case_root, output_path)
    if output.exists() and not (
        output.is_file() and (_is_generated_portal(output) or is_generated_human_review_dossier(output))
    ):
        raise PortalError(f"portal output is occupied by a non-WFF file: {output}")
    # A complete dossier owns the same index and uses dossier-manifest.json as
    # its sidecar. Do not make a later standalone preview refresh reject or
    # overwrite that entry because a legacy portal manifest happens to remain.
    if is_generated_human_review_dossier(output):
        return
    if manifest_path.exists() and not (
        manifest_path.is_file() and _is_generated_manifest(manifest_path)
    ):
        raise PortalError(f"portal manifest is occupied by a non-WFF file: {manifest_path}")


def discover_human_review_html(
    case_root: Path,
    *,
    portal_path: Path | None = None,
) -> list[HumanReviewHtmlArtifact]:
    root = _resolved(case_root)
    if not root.is_dir():
        raise PortalError(f"case root is not a directory: {root}")
    excluded = _resolved(portal_path) if portal_path is not None else None
    artifacts: list[HumanReviewHtmlArtifact] = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if name not in PRUNED_DIRS)
        for filename in sorted(filenames):
            if not filename.lower().endswith(".html"):
                continue
            candidate = Path(dirpath) / filename
            if candidate.is_symlink():
                continue
            resolved = candidate.resolve()
            if excluded is not None and resolved == excluded:
                continue
            if not _inside(resolved, root) or not resolved.is_file():
                continue
            artifact = _parse_artifact(resolved)
            if artifact is not None:
                artifacts.append(artifact)

    artifacts.sort(
        key=lambda item: (
            KIND_ORDER[item.kind],
            item.path.relative_to(root).as_posix(),
        )
    )
    return artifacts


def _relative_href(target: Path, output_path: Path) -> str:
    relative = os.path.relpath(target, start=output_path.parent).replace(os.sep, "/")
    return quote(relative, safe="/._-~")


def _artifact_rows(
    artifacts: list[HumanReviewHtmlArtifact],
    output_path: Path,
    case_root: Path,
) -> str:
    rows: list[str] = []
    for index, artifact in enumerate(artifacts):
        href = html.escape(_relative_href(artifact.path, output_path), quote=True)
        label = html.escape(artifact.label)
        type_label = html.escape(artifact.type_label)
        relative_path = html.escape(artifact.path.relative_to(case_root).as_posix())
        selected = index == 0
        rows.append(
            f'''<li class="artifact-row" data-artifact-row="{index}">
  <a class="artifact-switch" href="{href}" target="audit-frame" data-artifact-index="{index}"
     aria-current="{'page' if selected else 'false'}">
    <span class="artifact-type">{type_label}</span>
    <span class="artifact-label">{label}</span>
    <span class="artifact-path">{relative_path}</span>
  </a>
  <a class="artifact-direct" href="{href}" target="_blank" rel="noopener noreferrer"
     aria-label="独立打开 {label}" title="独立打开">
    <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
  </a>
</li>'''
        )
    return "\n".join(rows)


def _apply_template(template: str, replacements: dict[str, str]) -> str:
    pattern = re.compile(
        "|".join(re.escape(key) for key in sorted(replacements, key=len, reverse=True))
    )
    rendered = pattern.sub(lambda match: replacements[match.group(0)], template)
    unresolved = sorted(set(re.findall(r"@@WFF_[A-Z_]+@@", rendered)))
    if unresolved:
        raise RuntimeError(f"human-review portal template has unresolved markers: {', '.join(unresolved)}")
    return rendered


def render_human_review_portal(
    case_root: Path,
    output_path: Path,
    artifacts: list[HumanReviewHtmlArtifact],
) -> str:
    if not artifacts:
        raise PortalError("cannot render a human-review portal without HTML artifacts")
    root = _resolved(case_root)
    output = _resolved(output_path)
    first = artifacts[0]
    template = load_script_text_asset(__file__, "human-review-portal.html.template")
    replacements = {
        "@@WFF_PORTAL_TITLE@@": html.escape(f"{root.name} · WFF 人类审计"),
        "@@WFF_CASE_NAME@@": html.escape(root.name),
        "@@WFF_ARTIFACT_COUNT@@": str(len(artifacts)),
        "@@WFF_ARTIFACT_ROWS@@": _artifact_rows(artifacts, output, root),
        "@@WFF_FIRST_HREF@@": html.escape(_relative_href(first.path, output), quote=True),
        "@@WFF_FIRST_LABEL@@": html.escape(first.label),
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


def _manifest_payload(
    case_root: Path,
    output_path: Path,
    artifacts: list[HumanReviewHtmlArtifact],
) -> dict[str, object]:
    return {
        "schema_version": PORTAL_SCHEMA_VERSION,
        "authority": "navigation-only human-review HTML surface",
        "truth_boundary": (
            "This manifest lists existing WFF human-review HTML projections only. "
            "It does not accept content, replace canonical artifacts, change gates, or raise claim ceilings."
        ),
        "index_path": output_path.relative_to(case_root).as_posix(),
        "artifact_count": len(artifacts),
        "artifacts": [
            {
                "kind": artifact.kind,
                "label": artifact.label,
                "type_label": artifact.type_label,
                "path": artifact.path.relative_to(case_root).as_posix(),
                "marker": artifact.marker,
                "rendering_role": "human-review-companion",
                "claim_authority": "none",
            }
            for artifact in artifacts
        ],
    }


def refresh_human_review_portal(
    case_root: Path,
    *,
    output_path: Path | None = None,
) -> dict[str, object]:
    root, output, manifest_path = _portal_paths(case_root, output_path)
    if is_generated_human_review_dossier(output):
        dossier_manifest = output.with_name(DOSSIER_MANIFEST_FILENAME)
        if _has_valid_dossier_manifest(root, dossier_manifest, output):
            artifacts = discover_human_review_html(root, portal_path=output)
            return {
                "generated": True,
                "mode": "dossier",
                "index": str(output),
                "manifest": str(dossier_manifest),
                "artifact_count": len(artifacts),
                "artifacts": [
                    {
                        "kind": artifact.kind,
                        "label": artifact.label,
                        "type_label": artifact.type_label,
                        "path": artifact.path.relative_to(root).as_posix(),
                        "marker": artifact.marker,
                        "rendering_role": "human-review-companion",
                        "claim_authority": "none",
                    }
                    for artifact in artifacts
                ],
            }
        output.unlink()
    artifacts = discover_human_review_html(root, portal_path=output)

    if not artifacts:
        if output.is_file() and _is_generated_portal(output):
            output.unlink()
        if manifest_path.is_file() and _is_generated_manifest(manifest_path):
            manifest_path.unlink()
        return {
            "generated": False,
            "index": "",
            "manifest": "",
            "artifact_count": 0,
            "artifacts": [],
        }

    validate_portal_destination(root, output_path=output)

    rendered = render_human_review_portal(root, output, artifacts)
    manifest = _manifest_payload(root, output, artifacts)
    _write_atomic(output, rendered)
    _write_atomic(
        manifest_path,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return {
        "generated": True,
        "index": str(output),
        "manifest": str(manifest_path),
        "artifact_count": len(artifacts),
        "artifacts": manifest["artifacts"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="defaults to <case-root>/human-review/index.html")
    parser.add_argument("--open", action="store_true", dest="open_browser")
    return parser


def _error_payload(kind: str, message: str) -> str:
    return json.dumps({"generated": False, "error_kind": kind, "error": message}, ensure_ascii=False)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = refresh_human_review_portal(args.case_root, output_path=args.output)
    except PortalError as exc:
        print(_error_payload("portal_contract", str(exc)), file=sys.stderr)
        return 1
    except (OSError, UnicodeError, RuntimeError) as exc:
        print(_error_payload("portal_io", str(exc)), file=sys.stderr)
        return 2

    opened = False
    open_error = ""
    if args.open_browser and report["generated"]:
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
