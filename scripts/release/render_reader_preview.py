#!/usr/bin/env python3
"""Render an accepted zh-CN reader artifact as a standalone local HTML page."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Sequence
from urllib.parse import quote

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from markdown_it import MarkdownIt
from markdown_it.token import Token

from common.script_data_assets import load_script_text_asset
from release.render_human_review_portal import (
    DEFAULT_PORTAL_PATH,
    MANIFEST_FILENAME,
    PortalError,
    refresh_human_review_portal,
    validate_portal_destination,
)
from release.reader_translation_artifact_acceptance import build_reader_translation_artifact_acceptance


WFF_SCRIPT_DATA_ASSETS = ("scripts/release/data/reader-preview.html.template",)


class PreviewValidationError(ValueError):
    """The requested reader is not an accepted preview source."""


@dataclass(frozen=True)
class AcceptedReaderTarget:
    kind: str
    locale: str
    canonical_path: Path
    reader_path: Path
    integrity_path: Path


@dataclass(frozen=True)
class PreviewHeading:
    level: int
    title: str
    anchor: str


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def resolve_accepted_reader(case_root: Path, reader_path: Path) -> AcceptedReaderTarget:
    case_root = _resolved(case_root)
    reader_path = _resolved(reader_path)
    if not reader_path.is_file():
        raise PreviewValidationError(f"reader file missing: {reader_path}")
    if not reader_path.name.endswith(".reader.zh-CN.md"):
        raise PreviewValidationError("reader must use the *.reader.zh-CN.md artifact name")

    try:
        report = build_reader_translation_artifact_acceptance(case_root)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PreviewValidationError(f"reader acceptance could not be recomputed: {exc}") from exc

    if report.get("target_locale") != "zh-CN":
        raise PreviewValidationError(
            f"reader manifest target locale is not zh-CN: {report.get('target_locale') or 'missing'}"
        )

    matches = [
        target
        for target in report.get("targets", [])
        if _resolved(str(target.get("reader", ""))) == reader_path
    ]
    if not matches:
        raise PreviewValidationError("reader is not indexed by this case reader-translation manifest")
    if len(matches) != 1:
        raise PreviewValidationError("reader has multiple manifest target matches")

    target = matches[0]
    if target.get("acceptance_verdict") != "pass":
        issues = "; ".join(str(issue) for issue in target.get("issues", [])) or "acceptance did not pass"
        raise PreviewValidationError(f"reader target is not accepted: {issues}")

    canonical_path = _resolved(str(target["canonical"]))
    integrity_path = _resolved(str(target["integrity_json"]))
    return AcceptedReaderTarget(
        kind=str(target.get("kind", "reader-artifact")),
        locale="zh-CN",
        canonical_path=canonical_path,
        reader_path=reader_path,
        integrity_path=integrity_path,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _preamble_value(markdown_text: str, key: str) -> str:
    match = re.search(rf"^>\s*{re.escape(key)}:\s*`([^`]+)`\s*$", markdown_text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _heading_text(inline_token: Token) -> str:
    if not inline_token.children:
        return inline_token.content.strip()
    parts: list[str] = []
    for child in inline_token.children:
        if child.type in {"text", "code_inline"}:
            parts.append(child.content)
        elif child.type == "image":
            parts.append(child.content or child.attrGet("alt") or "")
    return "".join(parts).strip() or inline_token.content.strip()


def _decorate_tokens(
    tokens: list[Token],
    *,
    anchor_prefix: str = "section",
    heading_level_offset: int = 0,
    resource_href_rewriter: Callable[[str], str] | None = None,
) -> tuple[list[PreviewHeading], str]:
    headings: list[PreviewHeading] = []
    document_title = ""
    heading_number = 0

    for index, token in enumerate(tokens):
        if token.type == "heading_close" and heading_level_offset:
            source_level = int(token.tag.removeprefix("h"))
            token.tag = f"h{min(6, source_level + heading_level_offset)}"

        if token.type == "blockquote_open":
            blockquote_text: list[str] = []
            for candidate in tokens[index + 1 :]:
                if candidate.type == "blockquote_close":
                    break
                if candidate.type == "inline":
                    blockquote_text.append(candidate.content)
            if "localized reader artifact" in " ".join(blockquote_text):
                token.attrSet("class", "reader-preamble")

        if token.type == "heading_open" and index + 1 < len(tokens):
            inline = tokens[index + 1]
            heading_number += 1
            anchor = f"{anchor_prefix}-{heading_number}"
            title = _heading_text(inline)
            token.attrSet("id", anchor)
            source_level = int(token.tag.removeprefix("h"))
            level = min(6, source_level + heading_level_offset)
            if heading_level_offset:
                token.tag = f"h{level}"
            if not document_title and source_level == 1:
                document_title = title
            if level >= 2:
                headings.append(PreviewHeading(level=level, title=title, anchor=anchor))

        if token.type != "inline" or not token.children:
            continue
        for child in token.children:
            if child.type == "link_open":
                href = child.attrGet("href") or ""
                if href.startswith(("https://", "http://", "//")):
                    child.attrSet("target", "_blank")
                    child.attrSet("rel", "noopener noreferrer")
                elif resource_href_rewriter is not None and href and not href.startswith(("#", "mailto:", "tel:")):
                    child.attrSet("href", resource_href_rewriter(href))
            elif child.type == "image":
                source = child.attrGet("src") or ""
                if source.startswith(("https://", "http://", "//")):
                    # A reader projection must not fetch remote image content
                    # merely by opening an offline HTML artifact.
                    child.attrSet("src", "data:,")
                elif resource_href_rewriter is not None and source:
                    child.attrSet("src", resource_href_rewriter(source))

    return headings, document_title


def _render_fence(_renderer: Any, tokens: list[Token], index: int, _options: Any, _env: Any) -> str:
    token = tokens[index]
    language = token.info.strip().split(maxsplit=1)[0] if token.info.strip() else ""
    safe_language = re.sub(r"[^A-Za-z0-9_+.-]", "", language)[:40]
    label = safe_language or "代码"
    class_name = f' class="language-{html.escape(safe_language)}"' if safe_language else ""
    return (
        '<section class="code-block">'
        '<div class="code-head">'
        f'<span class="code-language">{html.escape(label)}</span>'
        '<button type="button" class="code-copy" data-copy-code>复制</button>'
        "</div>"
        f'<pre tabindex="0"><code{class_name}>{html.escape(token.content)}</code></pre>'
        "</section>\n"
    )


def _render_table_open(_renderer: Any, _tokens: list[Token], _index: int, _options: Any, _env: Any) -> str:
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="表格，可横向滚动"><table>\n'


def _render_table_close(_renderer: Any, _tokens: list[Token], _index: int, _options: Any, _env: Any) -> str:
    return "</table></div>\n"


def render_markdown(
    markdown_text: str,
    *,
    anchor_prefix: str = "section",
    heading_level_offset: int = 0,
    resource_href_rewriter: Callable[[str], str] | None = None,
) -> tuple[str, list[PreviewHeading], str]:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", anchor_prefix):
        raise ValueError("anchor_prefix must start with a letter and use only letters, digits, '_' or '-'")
    if not 0 <= heading_level_offset <= 5:
        raise ValueError("heading_level_offset must be between 0 and 5")
    renderer = MarkdownIt(
        "commonmark",
        {
            "html": False,
            "linkify": False,
            "typographer": False,
        },
    ).enable(("table", "strikethrough"))
    renderer.add_render_rule("fence", _render_fence)
    renderer.add_render_rule("table_open", _render_table_open)
    renderer.add_render_rule("table_close", _render_table_close)

    tokens = renderer.parse(markdown_text)
    headings, title = _decorate_tokens(
        tokens,
        anchor_prefix=anchor_prefix,
        heading_level_offset=heading_level_offset,
        resource_href_rewriter=resource_href_rewriter,
    )
    body = renderer.renderer.render(tokens, renderer.options, {})
    return body, headings, title


def _toc_items(headings: list[PreviewHeading]) -> str:
    if not headings:
        return '<li class="toc-empty">本文档没有二级标题</li>'
    items: list[str] = []
    for heading in headings:
        depth = min(max(heading.level - 2, 0), 3)
        items.append(
            f'<li class="toc-depth-{depth}">'
            f'<a href="#{heading.anchor}" data-heading-id="{heading.anchor}">{html.escape(heading.title)}</a>'
            "</li>"
        )
    return "".join(items)


def _relative_href(target: Path, output_path: Path) -> str:
    relative = os.path.relpath(target, start=output_path.parent).replace(os.sep, "/")
    return quote(relative, safe="/._-")


def _kind_label(kind: str) -> str:
    return {
        "p1-prd": "P1 产品需求文档",
        "p2-esp": "P2 工程规格包",
        "p3-action-card": "P3 行动卡",
    }.get(kind, kind or "WFF 阅读产物")


def _apply_template(template: str, replacements: dict[str, str]) -> str:
    pattern = re.compile("|".join(re.escape(key) for key in sorted(replacements, key=len, reverse=True)))
    rendered = pattern.sub(lambda match: replacements[match.group(0)], template)
    unresolved = sorted(set(re.findall(r"@@WFF_[A-Z_]+@@", rendered)))
    if unresolved:
        raise RuntimeError(f"reader preview template has unresolved markers: {', '.join(unresolved)}")
    return rendered


def render_reader_preview(target: AcceptedReaderTarget, output_path: Path) -> str:
    output_path = _resolved(output_path)
    reader_text = target.reader_path.read_text(encoding="utf-8")
    body, headings, markdown_title = render_markdown(reader_text)
    title = markdown_title or target.reader_path.stem
    artifact_label = _preamble_value(reader_text, "artifact_label") or _kind_label(target.kind)
    template = load_script_text_asset(__file__, "reader-preview.html.template")

    replacements = {
        "@@WFF_DOCUMENT_TITLE@@": html.escape(title),
        "@@WFF_DOCUMENT_BODY@@": body,
        "@@WFF_TOC_ITEMS@@": _toc_items(headings),
        "@@WFF_ARTIFACT_LABEL@@": html.escape(artifact_label),
        "@@WFF_KIND_LABEL@@": html.escape(_kind_label(target.kind)),
        "@@WFF_READER_NAME@@": html.escape(target.reader_path.name),
        "@@WFF_CANONICAL_NAME@@": html.escape(target.canonical_path.name),
        "@@WFF_INTEGRITY_NAME@@": html.escape(target.integrity_path.name),
        "@@WFF_READER_HREF@@": html.escape(_relative_href(target.reader_path, output_path), quote=True),
        "@@WFF_CANONICAL_HREF@@": html.escape(_relative_href(target.canonical_path, output_path), quote=True),
        "@@WFF_INTEGRITY_HREF@@": html.escape(_relative_href(target.integrity_path, output_path), quote=True),
        "@@WFF_READER_SHA@@": _sha256(target.reader_path),
        "@@WFF_CANONICAL_SHA@@": _sha256(target.canonical_path),
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


def default_preview_path(reader_path: Path) -> Path:
    return reader_path.with_suffix(".html")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root", required=True, type=Path)
    parser.add_argument("--reader", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="HTML output path; defaults beside the reader Markdown")
    parser.add_argument("--open", action="store_true", dest="open_browser", help="open the generated file in a browser")
    return parser


def _error_payload(kind: str, message: str) -> str:
    return json.dumps({"verdict": "fail", "error_kind": kind, "error": message}, ensure_ascii=False)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    case_root = _resolved(args.case_root)
    reader_path = _resolved(args.reader)
    output_path = _resolved(args.output) if args.output else default_preview_path(reader_path)

    if output_path.suffix.lower() != ".html":
        print(_error_payload("output_contract", "output path must end in .html"), file=sys.stderr)
        return 2
    reserved_navigation_paths = {
        case_root / DEFAULT_PORTAL_PATH,
        (case_root / DEFAULT_PORTAL_PATH).with_name(MANIFEST_FILENAME),
    }
    if output_path in {
        reader_path,
        case_root / "reader-translation-manifest.json",
        *reserved_navigation_paths,
    }:
        print(
            _error_payload("output_contract", "output path collides with a reserved reader or navigation file"),
            file=sys.stderr,
        )
        return 2
    try:
        output_path.relative_to(case_root)
    except ValueError:
        print(
            _error_payload("output_contract", "output path must stay inside the case root for unified HTML navigation"),
            file=sys.stderr,
        )
        return 2

    try:
        target = resolve_accepted_reader(case_root, reader_path)
        if output_path in {target.canonical_path, target.integrity_path}:
            raise PreviewValidationError("output path collides with a reader evidence file")
        validate_portal_destination(case_root)
        rendered = render_reader_preview(target, output_path)
        _write_atomic(output_path, rendered)
        portal_report = refresh_human_review_portal(case_root)
    except PreviewValidationError as exc:
        print(_error_payload("reader_not_accepted", str(exc)), file=sys.stderr)
        return 1
    except PortalError as exc:
        print(_error_payload("portal_contract", str(exc)), file=sys.stderr)
        return 2
    except ModuleNotFoundError as exc:
        print(_error_payload("dependency_missing", str(exc)), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, RuntimeError) as exc:
        print(_error_payload("preview_io", str(exc)), file=sys.stderr)
        return 2

    opened = False
    open_error = ""
    if args.open_browser:
        try:
            opened = bool(webbrowser.open(Path(str(portal_report["index"])).as_uri()))
        except (OSError, webbrowser.Error) as exc:
            open_error = str(exc)

    print(
        json.dumps(
            {
                "verdict": "pass",
                "reader": str(reader_path),
                "output": str(output_path),
                "html_portal": portal_report["index"],
                "html_artifact_count": portal_report["artifact_count"],
                "html_artifacts": portal_report["artifacts"],
                "opened": opened,
                "open_error": open_error,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
