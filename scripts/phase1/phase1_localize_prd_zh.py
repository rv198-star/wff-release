#!/usr/bin/env python3
"""
Generate a zh-CN audit mirror for the converged Phase-1 PRD main document.

Intent:
- keep the English PRD as the runtime/canonical artifact
- emit a separate Chinese review mirror for human reviewers
- preserve key domain terms and state labels in bilingual form
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import re
from pathlib import Path

from common.script_data_assets import load_script_json_asset


def normalize_lookup_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


WFF_SCRIPT_DATA_ASSETS = ("scripts/phase1/data/prd-localization-zh.json",)


def load_localization_maps() -> dict[str, object]:
    loaded = load_script_json_asset(__file__, "prd-localization-zh.json")
    if not isinstance(loaded, dict):
        raise TypeError("prd-localization-zh.json must contain an object")
    return {key: dict(value) if isinstance(value, dict) else value for key, value in loaded.items()}


_LOCALIZATION_MAPS = load_localization_maps()
TITLE_MAP = _LOCALIZATION_MAPS["title_map"]
HEADING_MAP = _LOCALIZATION_MAPS["heading_map"]
HEADING_BODY_MAP = _LOCALIZATION_MAPS["heading_body_map"]
FIELD_LABEL_MAP = _LOCALIZATION_MAPS["field_label_map"]
TABLE_HEADER_MAP = _LOCALIZATION_MAPS["table_header_map"]
TOKEN_MAP = _LOCALIZATION_MAPS["token_map"]
TERM_MAP = _LOCALIZATION_MAPS["term_map"]
INLINE_PHRASE_MAP = _LOCALIZATION_MAPS["inline_phrase_map"]


def localize_fragmented_tool_gap(match: re.Match[str]) -> str:
    tool_set = match.group(1).strip()
    loop = match.group(2).strip()
    tool_set = re.sub(r",\s*or\s+", "、", tool_set, flags=re.IGNORECASE)
    tool_set = re.sub(r",\s*", "、", tool_set)
    return f"为什么分散的 {tool_set} 工具无法闭合完整的 {loop} 运营闭环"


def _regex_flags_from_names(flag_names: object) -> int:
    flags = 0
    if not isinstance(flag_names, list):
        return flags
    for flag_name in flag_names:
        name = str(flag_name).strip().upper()
        if name == "IGNORECASE":
            flags |= re.IGNORECASE
        elif name == "MULTILINE":
            flags |= re.MULTILINE
        elif name == "DOTALL":
            flags |= re.DOTALL
    return flags


def _regex_replacement_from_payload(entry: dict[str, object]) -> tuple[re.Pattern[str], object]:
    pattern = re.compile(str(entry["pattern"]), _regex_flags_from_names(entry.get("flags")))
    callback_name = str(entry.get("replacement_callback", "")).strip()
    if callback_name == "localize_fragmented_tool_gap":
        return pattern, localize_fragmented_tool_gap
    return pattern, str(entry.get("replacement", ""))


REGEX_REPLACEMENTS = [
    _regex_replacement_from_payload(entry)
    for entry in _LOCALIZATION_MAPS.get("regex_replacements", [])
    if isinstance(entry, dict)
]

REGEX_LOCALIZED_PROTECTION_PATTERNS = tuple(
    re.compile(str(pattern))
    for pattern in _LOCALIZATION_MAPS.get("regex_localized_protection_patterns", [])
)

PROTECTED_LITERAL_PHRASES = tuple(str(phrase) for phrase in _LOCALIZATION_MAPS.get("protected_literal_phrases", []))

MACHINE_DELTA_LEDGER_FIELDS = set(str(field) for field in _LOCALIZATION_MAPS.get("machine_delta_ledger_fields", []))

FIELD_LABEL_MAP = {normalize_lookup_key(key): value for key, value in FIELD_LABEL_MAP.items()}
TABLE_HEADER_MAP = {normalize_lookup_key(key): value for key, value in TABLE_HEADER_MAP.items()}
HEADING_BODY_MAP = {normalize_lookup_key(key): value for key, value in HEADING_BODY_MAP.items()}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def protect_existing_localized_segments(text: str, mapping: dict[str, str], prefix: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}
    localized_values = sorted({value for value in mapping.values() if value}, key=len, reverse=True)
    protected = text
    for localized in localized_values:
        placeholder = f"__{prefix}_{len(placeholders)}__"
        placeholders[placeholder] = localized
        protected = protected.replace(localized, placeholder)
    return protected, placeholders


def restore_protected_localized_segments(text: str, placeholders: dict[str, str]) -> str:
    restored = text
    for placeholder, localized in placeholders.items():
        restored = restored.replace(placeholder, localized)
    return restored


def protect_literal_phrases(text: str, phrases: tuple[str, ...], prefix: str) -> tuple[str, dict[str, str]]:
    protected = text
    placeholders: dict[str, str] = {}
    for phrase in sorted({item for item in phrases if item}, key=len, reverse=True):
        placeholder = f"__{prefix}_{len(placeholders)}__"
        placeholders[placeholder] = phrase
        protected = protected.replace(phrase, placeholder)
    return protected, placeholders


def protect_regex_localized_segments(text: str, prefix: str = "L10N_REGEX") -> tuple[str, dict[str, str]]:
    protected = text
    placeholders: dict[str, str] = {}
    for pattern in REGEX_LOCALIZED_PROTECTION_PATTERNS:
        def replacer(match: re.Match[str]) -> str:
            placeholder = f"__{prefix}_{len(placeholders)}__"
            placeholders[placeholder] = match.group(0)
            return placeholder

        protected = pattern.sub(replacer, protected)
    return protected, placeholders


def infer_dynamic_bilingual_map(text: str) -> dict[str, str]:
    if "|" in text or "`" in text:
        return {}
    if re.match(r"^\s*(?:[-*]|\d+\.)\s+", text):
        return {}

    inferred: dict[str, str] = {}
    for match in re.finditer(r"(?<!\S)([^\n()|`:]{1,80}?)\s*\(([^()\n|`:]{1,80})\)", text):
        localized, english = match.groups()
        localized = localized.strip().strip("：:;,，")
        english = english.strip()
        if not localized or not english:
            continue
        if any(token in localized for token in ("|", "`", ":")):
            continue
        if re.search(r"[\u4e00-\u9fff]", english):
            continue
        if not re.search(r"[\u4e00-\u9fff]", localized):
            continue
        if normalize_lookup_key(english) == normalize_lookup_key(localized):
            continue
        inferred.setdefault(english, f"{localized} ({english})")
    return inferred


def append_mirror_suffix(title: str) -> str:
    if "中文评审镜像 / zh-CN Audit Mirror" in title:
        return title
    return f"{title}（中文评审镜像 / zh-CN Audit Mirror）"


def looks_like_primary_locale_text(text: str) -> bool:
    lines = text.splitlines()
    if not lines:
        return False
    first_line = lines[0].strip()
    return "产品需求文档 (PRD)" in first_line or "原型规格说明" in first_line or "Phase-1 执行报告" in first_line


def mirror_existing_primary_locale_text(
    text: str,
    canonical_name: str,
    *,
    include_mirror_note: bool = True,
) -> str:
    lines = text.splitlines()
    if not lines:
        return text

    output: list[str] = []
    inserted_note = False
    for idx, raw in enumerate(lines):
        if idx == 0 and raw.startswith("# "):
            output.append(f"# {append_mirror_suffix(raw[2:].strip())}")
            if include_mirror_note:
                output.append("")
                output.extend(build_mirror_note(canonical_name))
                output.append("")
                inserted_note = True
            continue
        output.append(raw)

    if include_mirror_note and not inserted_note:
        output = [*build_mirror_note(canonical_name), "", *output]
    return "\n".join(output)


def localize_title(title: str) -> str:
    if title in TITLE_MAP:
        return f"{TITLE_MAP[title]}（中文评审镜像 / zh-CN Audit Mirror）"

    match = re.fullmatch(r"(Stage-\d+[A-Za-z]?)\s+Output\s+[—-]\s+(.+)", title)
    if match:
        stage_label, detail = match.groups()
        localized_detail = re.sub(r"\s+（深度编译）$", "（深度编译）", replace_phrases(detail, INLINE_PHRASE_MAP))
        return f"{stage_label} 产物 — {localized_detail}（中文评审镜像 / zh-CN Audit Mirror）"

    match = re.fullmatch(r"(.+?)\s+[—-]\s+Convergence Evidence Memo", title)
    if match:
        base = match.group(1).strip()
        return f"{base} 收敛证据备忘录 (Convergence Evidence Memo)（中文评审镜像 / zh-CN Audit Mirror）"

    updated = re.sub(
        r"\bProduct Requirements Document(?:\s*\(PRD\))?\b",
        "产品需求文档 (PRD)",
        title,
        flags=re.IGNORECASE,
    )
    if "产品需求文档 (PRD)" in title:
        updated = title
    elif updated == title:
        updated = re.sub(r"\bPRD\b", "产品需求文档 (PRD)", updated)
    if updated == title:
        updated = append_mirror_suffix(title)
    else:
        updated = append_mirror_suffix(updated)
    return updated


def localize_primary_title(title: str) -> str:
    if title in TITLE_MAP:
        return TITLE_MAP[title]

    match = re.fullmatch(r"(Stage-\d+[A-Za-z]?)\s+Output\s+[—-]\s+(.+)", title)
    if match:
        stage_label, detail = match.groups()
        localized_detail = re.sub(r"\s+（深度编译）$", "（深度编译）", replace_phrases(detail, INLINE_PHRASE_MAP))
        return f"{stage_label} 产物 — {localized_detail}"

    match = re.fullmatch(r"(.+?)\s+[—-]\s+Convergence Evidence Memo", title)
    if match:
        base = match.group(1).strip()
        return f"{base} 收敛证据备忘录 (Convergence Evidence Memo)"

    updated = re.sub(
        r"\bProduct Requirements Document(?:\s*\(PRD\))?\b",
        "产品需求文档 (PRD)",
        title,
        flags=re.IGNORECASE,
    )
    if "产品需求文档 (PRD)" in title:
        return title
    if updated == title:
        updated = re.sub(r"\bPRD\b", "产品需求文档 (PRD)", updated)
    return updated


def localize_heading_title(title: str) -> str:
    normalized_title = normalize_lookup_key(title)
    if title in HEADING_MAP:
        return HEADING_MAP[title]
    if normalized_title in HEADING_BODY_MAP:
        return f"{HEADING_BODY_MAP[normalized_title]} ({title})"

    match = re.fullmatch(r"Key-path Scenario (\d+)", title)
    if match:
        number = match.group(1)
        return f"关键路径场景 {number} (Key-path Scenario {number})"

    match = re.fullmatch(r"Scenario (\d+): (.+)", title)
    if match:
        number, body = match.groups()
        localized_body = HEADING_BODY_MAP.get(normalize_lookup_key(body), body)
        return f"场景 {number}：{localized_body} (Scenario {number}: {body})"

    match = re.fullmatch(r"Scenario Deep Dive ([A-Z]): (.+)", title)
    if match:
        label, body = match.groups()
        localized_body = HEADING_BODY_MAP.get(normalize_lookup_key(body), body)
        return f"场景深挖 {label}：{localized_body} (Scenario Deep Dive {label}: {body})"

    match = re.fullmatch(r"Reasoning Unit (\d+): (.+)", title)
    if match:
        number, body = match.groups()
        localized_body = HEADING_BODY_MAP.get(normalize_lookup_key(body), body)
        return f"推理单元 {number}：{localized_body} (Reasoning Unit {number}: {body})"

    return title


def localize_heading_line(line: str) -> str:
    match = re.match(r"^(#{1,6}\s+)(\d+\.\s+)?(.+?)\s*$", line)
    if not match:
        return line
    prefix, number, title = match.groups()
    localized = localize_heading_title(title.strip())
    return f"{prefix}{number or ''}{localized}".rstrip()


def localize_field_label_line(line: str) -> str:
    match = re.match(r"^(\s*-\s+)([^:]{1,120}?)(:\s*.*)$", line)
    if not match:
        return line
    prefix, label, suffix = match.groups()
    localized = FIELD_LABEL_MAP.get(normalize_lookup_key(label))
    if not localized:
        return line
    return f"{prefix}{localized}{suffix}"


def is_machine_delta_ledger_field_line(line: str) -> bool:
    match = re.match(r"^\s*-\s+([^:]{1,120}?):", line)
    return bool(match and normalize_lookup_key(match.group(1)) in MACHINE_DELTA_LEDGER_FIELDS)


def is_h2_heading_line(line: str) -> bool:
    return bool(re.match(r"^##\s+", line)) and not re.match(r"^###\s+", line)


def is_analysis_delta_ledger_heading(line: str) -> bool:
    return bool(re.match(r"^##\s+(?:\d+\.\s+)?[^\n]*Analysis Delta Ledger[^\n]*$", line, flags=re.IGNORECASE))


def localize_table_header_line(line: str) -> str:
    if not line.lstrip().startswith("|"):
        return line
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    localized = [TABLE_HEADER_MAP.get(normalize_lookup_key(cell), cell) for cell in cells]
    return "| " + " | ".join(localized) + " |"


def replace_exact_tokens(text: str, mapping: dict[str, str]) -> str:
    ordered = sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True)
    text, regex_protected = protect_regex_localized_segments(text, "L10N_TOKEN_REGEX")
    text, protected = protect_existing_localized_segments(text, mapping, "L10N_EXISTING_TOKEN")
    placeholders: dict[str, str] = {}
    for raw, localized in ordered:
        placeholder = f"__L10N_TOKEN_{len(placeholders)}__"
        placeholders[placeholder] = localized
        text = re.sub(
            rf"(?<![A-Za-z0-9_./-]){re.escape(raw)}(?![A-Za-z0-9_./-])",
            placeholder,
            text,
        )
    for placeholder, localized in placeholders.items():
        text = text.replace(placeholder, localized)
    text = restore_protected_localized_segments(text, protected)
    return restore_protected_localized_segments(text, regex_protected)


def replace_phrases(text: str, mapping: dict[str, str]) -> str:
    ordered = sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True)
    text, regex_protected = protect_regex_localized_segments(text, "L10N_PHRASE_REGEX")
    text, protected = protect_existing_localized_segments(text, mapping, "L10N_EXISTING_PHRASE")
    placeholders: dict[str, str] = {}
    for raw, localized in ordered:
        placeholder = f"__L10N_PHRASE_{len(placeholders)}__"
        placeholders[placeholder] = localized
        pattern = re.escape(raw)
        if raw and raw[0].isalnum():
            pattern = rf"(?<![A-Za-z0-9_]){pattern}"
        if raw and raw[-1].isalnum():
            pattern = rf"{pattern}(?![A-Za-z0-9_])"
        text = re.sub(pattern, placeholder, text)
    for placeholder, localized in placeholders.items():
        text = text.replace(placeholder, localized)
    text = restore_protected_localized_segments(text, protected)
    return restore_protected_localized_segments(text, regex_protected)


def localize_inline_line(line: str) -> str:
    dynamic_map = infer_dynamic_bilingual_map(line)
    localized, protected_regex = protect_regex_localized_segments(line)
    localized, protected_literals = protect_literal_phrases(localized, PROTECTED_LITERAL_PHRASES, "L10N_LITERAL")
    for pattern, replacement in REGEX_REPLACEMENTS:
        localized = pattern.sub(replacement, localized)
    localized = replace_exact_tokens(localized, TOKEN_MAP)
    localized = replace_exact_tokens(localized, TERM_MAP)
    if dynamic_map:
        localized = replace_exact_tokens(localized, dynamic_map)
        localized = replace_phrases(localized, dynamic_map)
    localized = replace_phrases(localized, INLINE_PHRASE_MAP)
    localized = restore_protected_localized_segments(localized, protected_literals)
    return restore_protected_localized_segments(localized, protected_regex)


def build_mirror_note(canonical_name: str) -> list[str]:
    return [
        "> 中文评审镜像（zh-CN audit mirror）",
        f"> canonical_of: `{canonical_name}`",
        "> 规则: 关键领域对象、状态枚举与交接术语保持中英双语；若中英语义冲突，以英文 canonical 为准。",
    ]


def localize_text(
    text: str,
    canonical_name: str,
    *,
    include_mirror_note: bool = True,
    include_mirror_suffix: bool = True,
) -> str:
    if include_mirror_suffix and looks_like_primary_locale_text(text):
        return mirror_existing_primary_locale_text(
            text,
            canonical_name,
            include_mirror_note=include_mirror_note,
        )

    lines = text.splitlines()
    output: list[str] = []
    inserted_note = False
    in_machine_delta_ledger = False

    for idx, raw in enumerate(lines):
        line = raw
        if idx == 0 and line.startswith("# "):
            title = line[2:].strip()
            output.append(f"# {localize_title(title) if include_mirror_suffix else localize_primary_title(title)}")
            if include_mirror_note:
                output.append("")
                output.extend(build_mirror_note(canonical_name))
                output.append("")
                inserted_note = True
            continue

        if re.match(r"^#{1,6}\s+", line):
            if is_h2_heading_line(line):
                in_machine_delta_ledger = is_analysis_delta_ledger_heading(line)
            output.append(localize_heading_line(line))
            continue

        if not (in_machine_delta_ledger and is_machine_delta_ledger_field_line(line)):
            line = localize_field_label_line(line)
        line = localize_table_header_line(line)
        line = localize_inline_line(line)
        output.append(line)

    if include_mirror_note and not inserted_note:
        output = [*build_mirror_note(canonical_name), "", *output]

    return "\n".join(output)


def render_primary_locale_lines(
    lines: list[str],
    canonical_name: str,
    locale: str | None,
    *,
    preserve_table_body_literals: bool = False,
) -> list[str]:
    if str(locale or "").strip() != "zh-CN":
        return list(lines)

    output: list[str] = []
    flattened: list[str] = []
    in_machine_delta_ledger = False
    for raw in lines:
        parts = str(raw).splitlines()
        if not parts:
            flattened.append("")
            continue
        flattened.extend(parts)

    for idx, raw in enumerate(flattened):
        line = raw
        if idx == 0 and line.startswith("# "):
            output.append(f"# {localize_primary_title(line[2:].strip())}")
            continue
        if re.match(r"^#{1,6}\s+", line):
            if is_h2_heading_line(line):
                in_machine_delta_ledger = is_analysis_delta_ledger_heading(line)
            output.append(localize_heading_line(line))
            continue
        if not (in_machine_delta_ledger and is_machine_delta_ledger_field_line(line)):
            line = localize_field_label_line(line)
        line = localize_table_header_line(line)
        if preserve_table_body_literals and line.strip().startswith("|"):
            output.append(line)
            continue
        line = localize_inline_line(line)
        output.append(line)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate zh-CN audit mirror for the Phase-1 PRD")
    parser.add_argument("--canonical-prd", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    canonical_path = Path(args.canonical_prd).resolve()
    output_path = Path(args.output).resolve()
    text = read_text(canonical_path)
    localized = localize_text(text, canonical_path.name)
    write_text(output_path, localized)

    print("== Phase-1 PRD zh-CN Mirror ==")
    print(f"canonical_prd: {canonical_path}")
    print(f"zh_prd: {output_path}")
    print("FINAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
