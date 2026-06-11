from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from pathlib import Path
from typing import Any


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
MERMAID_RE = re.compile(r"```mermaid\s*(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class AuditFinding:
    code: str
    severity: str
    message: str
    source_view: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "source_view": self.source_view,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class AuditReport:
    profile: str
    findings: list[AuditFinding]
    reference_sets: dict[str, list[str]] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not any(finding.severity in {"severe", "error"} for finding in self.findings)

    @property
    def status(self) -> str:
        return "pass" if self.passed else "fail"

    def finding_by_code(self, code: str) -> AuditFinding | None:
        for finding in self.findings:
            if finding.code == code:
                return finding
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "status": self.status,
            "reference_sets": self.reference_sets,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def build_rendered_inventory(markdown: str) -> dict[str, Any]:
    headings = _extract_headings(markdown)
    sections = _section_ranges(markdown, headings)
    return {
        "headings": [
            {"level": heading["level"], "title": heading["title"]}
            for heading in headings
        ],
        "sections": [
            {
                "title": section["title"],
                "level": section["level"],
                "body": section["body"],
                "direct_body": section["direct_body"],
            }
            for section in sections
        ],
        "tables": _extract_tables(markdown),
        "mermaid_blocks": _extract_mermaid_blocks(markdown),
        "text": markdown,
    }


def build_inventory_report(markdown: str, *, contract: dict[str, Any] | None = None) -> dict[str, Any]:
    inventory = build_rendered_inventory(markdown)
    text = str(inventory.get("text", ""))
    contract = contract or {}
    return {
        "summary": {
            "heading_count": len(inventory.get("headings", [])),
            "section_count": len(inventory.get("sections", [])),
            "table_count": len(inventory.get("tables", [])),
            "mermaid_block_count": len(inventory.get("mermaid_blocks", [])),
        },
        "headings": inventory.get("headings", []),
        "candidate_tokens": _candidate_tokens(text),
        "contract_refs": _contract_refs(text, contract),
        "key_value_fields": _key_value_field_groups(inventory),
        "tables": _inventory_table_summaries(inventory),
        "mermaid_blocks": _inventory_mermaid_summaries(inventory),
    }


def audit_text(
    markdown: str,
    *,
    profile: str = "generic",
    contract: dict[str, Any] | None = None,
) -> AuditReport:
    normalized_profile = profile.strip().lower()
    if contract is None:
        return AuditReport(profile=normalized_profile, findings=[])

    inventory = build_rendered_inventory(markdown)
    reference_sets = _build_reference_sets(inventory, contract)
    relation_sets = _build_relation_sets(inventory, contract)
    findings: list[AuditFinding] = []
    findings.extend(_run_set_rules(reference_sets, contract))
    findings.extend(_run_relation_rules(relation_sets, contract))
    findings.extend(_run_table_value_rules(inventory, contract))
    findings.extend(_run_table_key_coverage_rules(inventory, contract))
    findings.extend(_run_table_subset_rules(inventory, contract))
    findings.extend(_run_table_unique_key_rules(inventory, contract))
    findings.extend(_run_mermaid_node_value_rules(inventory, contract))
    findings.extend(_run_field_subset_rules(inventory, contract))
    findings.extend(_run_field_value_rules(inventory, contract))
    findings.extend(_run_forbidden_alias_rules(inventory, contract))
    findings.extend(_run_forbidden_pattern_rules(inventory, contract))
    return AuditReport(
        profile=normalized_profile,
        findings=findings,
        reference_sets={name: sorted(values, key=_ref_sort_key) for name, values in sorted(reference_sets.items())},
    )


def audit_file(
    path: Path,
    *,
    profile: str = "generic",
    contract: dict[str, Any] | None = None,
) -> AuditReport:
    return audit_text(path.read_text(encoding="utf-8"), profile=profile, contract=contract)


def load_contract(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_report(report: AuditReport, path: Path) -> None:
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown_report(report: AuditReport, path: Path) -> None:
    path.write_text(render_markdown_report(report), encoding="utf-8")


def write_inventory_json_report(report: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_inventory_markdown_report(report: dict[str, Any], path: Path) -> None:
    path.write_text(render_inventory_markdown_report(report), encoding="utf-8")


def render_markdown_report(report: AuditReport) -> str:
    lines = [
        "# Artifact Consistency Audit",
        "",
        f"- Profile: `{report.profile}`",
        f"- Status: `{report.status}`",
        "",
    ]
    if report.reference_sets:
        lines.append("## Reference Sets")
        lines.append("")
        for name, refs in sorted(report.reference_sets.items()):
            rendered = ", ".join(refs) if refs else "(none)"
            lines.append(f"- `{name}`: {rendered}")
        lines.append("")
    if not report.findings:
        lines.append("No findings.")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Findings")
    lines.append("")
    for finding in report.findings:
        lines.append(f"### {_title_for_code(finding.code)}")
        lines.append("")
        lines.append(f"- Severity: `{finding.severity}`")
        lines.append(f"- Source view: `{finding.source_view}`")
        lines.append(f"- Message: {finding.message}")
        if finding.evidence:
            lines.append("- Evidence:")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(finding.evidence, ensure_ascii=False, indent=2))
            lines.append("```")
        lines.append("")
    return "\n".join(lines)


def render_inventory_markdown_report(report: dict[str, Any]) -> str:
    summary = dict(report.get("summary", {}))
    lines = [
        "# Rendered Artifact Inventory",
        "",
        "## Summary",
        "",
    ]
    for key in ["heading_count", "section_count", "table_count", "mermaid_block_count"]:
        lines.append(f"- `{key}`: {summary.get(key, 0)}")
    lines.extend(["", "## Candidate Tokens", ""])
    for name, values in sorted(dict(report.get("candidate_tokens", {})).items()):
        rendered = ", ".join(values) if values else "(none)"
        lines.append(f"- `{name}`: {rendered}")
    contract_refs = dict(report.get("contract_refs", {}))
    if contract_refs:
        lines.extend(["", "## Contract Refs", ""])
        for name, values in sorted(contract_refs.items()):
            rendered = ", ".join(values) if values else "(none)"
            lines.append(f"- `{name}`: {rendered}")
    lines.append("")
    return "\n".join(lines)


def _extract_headings(markdown: str) -> list[dict[str, Any]]:
    return [
        {
            "level": len(match.group(1)),
            "title": match.group(2).strip().strip("#").strip(),
            "start": match.start(),
            "end": match.end(),
        }
        for match in HEADING_RE.finditer(markdown)
    ]


def _section_ranges(markdown: str, headings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for index, heading in enumerate(headings):
        end = len(markdown)
        direct_end = headings[index + 1]["start"] if index + 1 < len(headings) else len(markdown)
        for next_heading in headings[index + 1 :]:
            if next_heading["level"] <= heading["level"]:
                end = next_heading["start"]
                break
        sections.append(
            {
                "level": heading["level"],
                "title": heading["title"],
                "body": markdown[heading["end"] : end],
                "direct_body": markdown[heading["end"] : direct_end],
            }
        )
    return sections


def _extract_tables(markdown: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not _looks_like_table_row(line):
            index += 1
            continue
        if index + 1 >= len(lines) or not _looks_like_separator_row(lines[index + 1].strip()):
            index += 1
            continue
        headers = [_clean_cell(cell) for cell in _split_table_row(line)]
        rows: list[dict[str, str]] = []
        index += 2
        while index < len(lines) and _looks_like_table_row(lines[index].strip()):
            cells = _split_table_row(lines[index].strip())
            row: dict[str, str] = {}
            for column_index, header in enumerate(headers):
                row[header] = _clean_cell(cells[column_index]) if column_index < len(cells) else ""
            rows.append(row)
            index += 1
        tables.append({"headers": headers, "rows": rows})
    return tables


def _extract_mermaid_blocks(markdown: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for match in MERMAID_RE.finditer(markdown):
        body = match.group(1).strip()
        first_line = body.splitlines()[0].strip() if body.splitlines() else ""
        blocks.append(
            {
                "diagram_type": _mermaid_diagram_type(first_line),
                "first_line": first_line,
                "body": body,
            }
        )
    return blocks


def _build_reference_sets(inventory: dict[str, Any], contract: dict[str, Any]) -> dict[str, set[str]]:
    reference_sets: dict[str, set[str]] = {}
    patterns = dict(contract.get("id_patterns", {}))
    for spec in contract.get("reference_sets", []):
        name = str(spec["name"])
        source = dict(spec.get("source", {}))
        pattern_names = [str(pattern_name) for pattern_name in spec.get("patterns", [])]
        source_text = _source_text_for_reference_set(inventory, source)
        refs: set[str] = set()
        for pattern_name in pattern_names:
            pattern = patterns.get(pattern_name)
            if isinstance(pattern, dict):
                refs.update(_extract_refs(source_text, pattern))
        reference_sets[name] = refs
    return reference_sets


def _source_text_for_reference_set(inventory: dict[str, Any], source: dict[str, Any]) -> str:
    ref_columns = _source_ref_columns(source)
    if ref_columns:
        values: list[str] = []
        for row in _table_rows_for_source(inventory, source):
            value, _column = _row_value_from_columns(row, ref_columns)
            if value:
                values.append(value)
        return _apply_source_text_options("\n".join(values), source)

    if _source_table_headers(source):
        return "\n".join(_table_text(table) for table in _tables_for_source(inventory, source))

    section_titles = [str(title) for title in source.get("section_titles", [])]
    if section_titles:
        return _apply_source_text_options("\n".join(_section_bodies(inventory, section_titles)), source)

    mermaid_types = [str(item).lower() for item in source.get("mermaid_diagram_types", [])]
    if mermaid_types:
        return "\n".join(
            str(block["body"])
            for block in inventory.get("mermaid_blocks", [])
            if str(block.get("diagram_type", "")).lower() in mermaid_types
        )

    return _apply_source_text_options(str(inventory.get("text", "")), source)


def _apply_source_text_options(text: str, source: dict[str, Any]) -> str:
    if source.get("exclude_mermaid"):
        text = MERMAID_RE.sub("", text)
    return text


def _build_relation_sets(inventory: dict[str, Any], contract: dict[str, Any]) -> dict[str, set[tuple[str, str]]]:
    relation_sets: dict[str, set[tuple[str, str]]] = {}
    patterns = dict(contract.get("relation_patterns", {}))
    for spec in contract.get("relation_sets", []):
        name = str(spec["name"])
        pattern = patterns.get(str(spec.get("pattern", "")))
        if not isinstance(pattern, dict):
            relation_sets[name] = set()
            continue
        source = dict(spec.get("source", {}))
        spec_type = str(spec.get("type", "")).strip().lower()
        if spec_type == "table_columns":
            relation_sets[name] = _relation_set_from_table_columns(inventory, spec, pattern)
        elif spec_type == "mermaid_edges":
            relation_sets[name] = _relation_set_from_mermaid_edges(
                _source_text_for_reference_set(inventory, source), pattern
            )
        else:
            relation_sets[name] = set()
    return relation_sets


def _relation_set_from_table_columns(
    inventory: dict[str, Any], spec: dict[str, Any], pattern: dict[str, Any]
) -> set[tuple[str, str]]:
    rows = _table_rows_for_source(inventory, dict(spec.get("source", {})))
    from_column = str(spec.get("from_column", ""))
    to_column = str(spec.get("to_column", ""))
    relations: set[tuple[str, str]] = set()
    for row in rows:
        subject = _canonicalize_relation_endpoint(_row_value(row, from_column), pattern, "from")
        target = _canonicalize_relation_endpoint(_row_value(row, to_column), pattern, "to")
        if subject and target:
            relations.add((subject, target))
    return relations


def _relation_set_from_mermaid_edges(text: str, pattern: dict[str, Any]) -> set[tuple[str, str]]:
    relations: set[tuple[str, str]] = set()
    for left, right in _extract_mermaid_edge_endpoints(text):
        subject = _canonicalize_relation_endpoint(left, pattern, "from")
        target = _canonicalize_relation_endpoint(right, pattern, "to")
        if subject and target:
            relations.add((subject, target))
    return relations


def _extract_mermaid_edge_endpoints(text: str) -> list[tuple[str, str]]:
    endpoints: list[tuple[str, str]] = []
    edge_re = re.compile(r"^\s*(?P<left>.+?)\s*(?:-->|---|==>|-\.->)(?:\|.*?\|)?\s*(?P<right>.+?)\s*$")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%%") or stripped.lower().startswith(("flowchart", "graph ")):
            continue
        match = edge_re.match(stripped)
        if not match:
            continue
        endpoints.append((_clean_mermaid_endpoint(match.group("left")), _clean_mermaid_endpoint(match.group("right"))))
    return endpoints


def _extract_mermaid_node_labels(text: str) -> list[tuple[str, str]]:
    node_re = re.compile(
        r"(?P<node>[A-Za-z][A-Za-z0-9_.-]*)\s*"
        r"(?P<label>\[/?[^\]\n]+/?\]|\(\([^\)\n]+\)\)|\([^\)\n]+\)|\{\{[^\}\n]+\}\}|\{[^\}\n]+\})"
    )
    labels: list[tuple[str, str]] = []
    for match in node_re.finditer(text):
        labels.append((match.group("node"), _clean_mermaid_node_label(match.group("label"))))
    return labels


def _clean_mermaid_endpoint(value: str) -> str:
    value = value.strip().strip(";")
    value = re.sub(r"\s*:::.*$", "", value)
    value = re.sub(r"\[.*$", "", value)
    value = re.sub(r"\(.*$", "", value)
    value = re.sub(r"\{.*$", "", value)
    return value.strip().strip('"')


def _clean_mermaid_node_label(value: str) -> str:
    label = value.strip()
    changed = True
    while changed and len(label) >= 2:
        changed = False
        for left, right in (("[[", "]]"), ("((", "))"), ("{{", "}}"), ("[", "]"), ("(", ")"), ("{", "}")):
            if label.startswith(left) and label.endswith(right):
                label = label[len(left) : -len(right)].strip()
                changed = True
                break
    return label.strip().strip('"').strip("'").strip("/").strip("\\").strip()


def _canonicalize_relation_endpoint(value: str, pattern: dict[str, Any], side: str) -> str:
    regex = pattern.get(f"{side}_regex") or pattern.get("regex")
    canonical = str(pattern.get(f"{side}_canonical", pattern.get("canonical", "{match}")))
    if not regex:
        return value
    match = re.search(str(regex), value, re.IGNORECASE)
    if not match:
        return ""
    values: dict[str, Any] = {"match": match.group(0)}
    values.update(match.groupdict())
    for key, item in list(values.items()):
        if isinstance(item, str) and item.isdigit():
            values[key] = int(item)
    return canonical.format(**values)


def _section_bodies(inventory: dict[str, Any], titles: list[str]) -> list[str]:
    title_patterns = [re.compile(re.escape(title), re.IGNORECASE) for title in titles]
    return [
        str(section["body"])
        for section in inventory.get("sections", [])
        if any(pattern.search(str(section["title"])) for pattern in title_patterns)
    ]


def _extract_refs(text: str, pattern: dict[str, Any]) -> set[str]:
    regex = re.compile(str(pattern["regex"]), re.IGNORECASE)
    canonical = str(pattern.get("canonical", "{match}"))
    refs: set[str] = set()
    for match in regex.finditer(text):
        values: dict[str, Any] = {"match": match.group(0)}
        values.update(match.groupdict())
        for key, value in list(values.items()):
            if isinstance(value, str) and value.isdigit():
                values[key] = int(value)
        refs.add(canonical.format(**values))
    return refs


def _candidate_tokens(text: str) -> dict[str, list[str]]:
    return {
        "id_like": sorted(_extract_id_like_tokens(text), key=_ref_sort_key),
        "state_like": sorted(_extract_state_like_tokens(text)),
        "camel_case": sorted(_extract_camel_case_tokens(text)),
        "api_paths": sorted(_extract_api_paths(text)),
    }


def _contract_refs(text: str, contract: dict[str, Any]) -> dict[str, list[str]]:
    refs: dict[str, list[str]] = {}
    for name, pattern in dict(contract.get("id_patterns", {})).items():
        if isinstance(pattern, dict):
            refs[str(name)] = sorted(_extract_refs(text, pattern), key=_ref_sort_key)
    return refs


def _key_value_field_groups(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for section in inventory.get("sections", []):
        fields = _extract_key_value_fields(str(section.get("direct_body", section.get("body", ""))))
        if fields:
            groups.append({"section": str(section.get("title", "")), "fields": fields})
    return groups


def _inventory_table_summaries(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "headers": table.get("headers", []),
            "row_count": len(table.get("rows", [])),
            "candidate_tokens": _candidate_tokens(_table_text(table)),
        }
        for table in inventory.get("tables", [])
    ]


def _inventory_mermaid_summaries(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "diagram_type": block.get("diagram_type", "unknown"),
            "first_line": block.get("first_line", ""),
            "candidate_tokens": _candidate_tokens(str(block.get("body", ""))),
        }
        for block in inventory.get("mermaid_blocks", [])
    ]


def _table_text(table: dict[str, Any]) -> str:
    parts: list[str] = []
    parts.extend(str(header) for header in table.get("headers", []))
    for row in table.get("rows", []):
        parts.extend(str(value) for value in row.values())
    return "\n".join(parts)


def _extract_id_like_tokens(text: str) -> set[str]:
    return set(re.findall(r"\bP\d-(?:CMP|CTR|FLOW|SEQ|STATE|RP|REQ|AC)-\d+\b|\b(?:REQ|AC|FLOW)-\d+\b", text))


def _extract_state_like_tokens(text: str) -> set[str]:
    return {
        match.group(0)
        for match in re.finditer(r"\b[a-z][a-z0-9]+(?:_[a-z0-9]+)+\b", text)
        if any(part in match.group(0) for part in ["active", "ready", "progress", "state", "status"])
    }


def _extract_camel_case_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*\b", text))


def _extract_api_paths(text: str) -> set[str]:
    return set(re.findall(r"(?<![A-Za-z0-9_])/api/[A-Za-z0-9_./{}-]+", text))


def _run_set_rules(reference_sets: dict[str, set[str]], contract: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for rule in contract.get("set_rules", []):
        required_name = str(rule["required_from"])
        target_name = str(rule["must_exist_in"])
        required_refs = reference_sets.get(required_name, set())
        target_refs = reference_sets.get(target_name, set())
        missing = sorted(required_refs - target_refs, key=_ref_sort_key)
        if not missing:
            continue
        findings.append(
            AuditFinding(
                code=str(rule["code"]),
                severity=str(rule.get("severity", "severe")),
                message=str(rule.get("message", "Required references are missing from a rendered view.")),
                source_view="contract_set_rule",
                evidence={
                    "required_from": required_name,
                    "must_exist_in": target_name,
                    "required_refs": sorted(required_refs, key=_ref_sort_key),
                    "target_refs": sorted(target_refs, key=_ref_sort_key),
                    "missing_refs": missing,
                },
            )
        )
    return findings


def _run_relation_rules(
    relation_sets: dict[str, set[tuple[str, str]]], contract: dict[str, Any]
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for rule in contract.get("relation_rules", []):
        required_name = str(rule["required_from"])
        target_name = str(rule["must_exist_in"])
        required_relations = relation_sets.get(required_name, set())
        target_relations = relation_sets.get(target_name, set())
        missing = sorted(required_relations - target_relations, key=_relation_sort_key)
        if not missing:
            continue
        findings.append(
            AuditFinding(
                code=str(rule["code"]),
                severity=str(rule.get("severity", "severe")),
                message=str(rule.get("message", "Required relations are missing from a rendered view.")),
                source_view="contract_relation_rule",
                evidence={
                    "required_from": required_name,
                    "must_exist_in": target_name,
                    "required_relations": _format_relations(required_relations),
                    "target_relations": _format_relations(target_relations),
                    "missing_relations": _format_relations(missing),
                },
            )
        )
    return findings


def _run_table_value_rules(inventory: dict[str, Any], contract: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for rule in contract.get("table_value_rules", []):
        source_a_rows = _table_rows_for_source(inventory, dict(rule.get("source_a", {})))
        source_b_rows = _table_rows_for_source(inventory, dict(rule.get("source_b", {})))
        source_a_key_columns = _column_candidates(rule, "source_a_key_columns", "source_a_key_column", "key_column")
        source_b_key_columns = _column_candidates(rule, "source_b_key_columns", "source_b_key_column", "key_column")
        source_a_value_columns = _column_candidates(rule, "source_a_value_columns", "source_a_value_column", "value_column")
        source_b_value_columns = _column_candidates(rule, "source_b_value_columns", "source_b_value_column", "value_column")
        source_a = _table_key_value_map(
            source_a_rows,
            source_a_key_columns,
            source_a_value_columns,
            key_pattern=rule.get("source_a_key_pattern"),
            value_pattern=rule.get("source_a_value_pattern"),
        )
        source_b = _table_key_value_map(
            source_b_rows,
            source_b_key_columns,
            source_b_value_columns,
            key_pattern=rule.get("source_b_key_pattern"),
            value_pattern=rule.get("source_b_value_pattern"),
        )
        for key, value_a in sorted(source_a.items()):
            value_b = source_b.get(key)
            if value_b is None or _normalize_value(value_a["value"]) == _normalize_value(value_b["value"]):
                continue
            findings.append(
                AuditFinding(
                    code=str(rule["code"]),
                    severity=str(rule.get("severity", "severe")),
                    message=str(rule.get("message", "Rendered table values conflict.")),
                    source_view="contract_table_value_rule",
                    evidence={
                        "key": key,
                        "source_a_key_column": value_a["key_column"],
                        "source_b_key_column": value_b["key_column"],
                        "source_a_value_column": value_a["value_column"],
                        "source_b_value_column": value_b["value_column"],
                        "source_a_key_columns": source_a_key_columns,
                        "source_b_key_columns": source_b_key_columns,
                        "source_a_value_columns": source_a_value_columns,
                        "source_b_value_columns": source_b_value_columns,
                        "source_a_value": value_a["value"],
                        "source_b_value": value_b["value"],
                        "source_a_raw_value": value_a["raw_value"],
                        "source_b_raw_value": value_b["raw_value"],
                    },
                )
            )
    return findings


def _run_table_subset_rules(inventory: dict[str, Any], contract: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for rule in contract.get("table_subset_rules", []):
        rows = _table_rows_for_source(inventory, dict(rule.get("source", {})))
        key_column = str(rule["key_column"])
        required_column = str(rule["required_column"])
        available_column = str(rule["available_column"])
        patterns = _patterns_for_rule(contract, rule)
        for row in rows:
            key = _row_value(row, key_column)
            raw_required = _row_value(row, required_column)
            raw_available = _row_value(row, available_column)
            required_refs = _extract_refs_with_patterns(raw_required, patterns)
            available_refs = _extract_refs_with_patterns(raw_available, patterns)
            missing = sorted(required_refs - available_refs, key=_ref_sort_key)
            if not missing:
                continue
            findings.append(
                AuditFinding(
                    code=str(rule["code"]),
                    severity=str(rule.get("severity", "severe")),
                    message=str(rule.get("message", "Required references are missing from available references.")),
                    source_view="contract_table_subset_rule",
                    evidence={
                        "key": key,
                        "key_column": key_column,
                        "required_column": required_column,
                        "available_column": available_column,
                        "required_refs": sorted(required_refs, key=_ref_sort_key),
                        "available_refs": sorted(available_refs, key=_ref_sort_key),
                        "missing_refs": missing,
                        "raw_required": raw_required,
                        "raw_available": raw_available,
                    },
                )
            )
    return findings


def _run_table_key_coverage_rules(inventory: dict[str, Any], contract: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for rule in contract.get("table_key_coverage_rules", []):
        source_a = dict(rule.get("source_a", {}))
        source_b = dict(rule.get("source_b", {}))
        source_a_key_columns = _column_candidates(rule, "source_a_key_columns", "source_a_key_column", "key_column")
        source_b_key_columns = _column_candidates(rule, "source_b_key_columns", "source_b_key_column", "key_column")
        source_a_keys = _table_key_map(
            _table_rows_for_source(inventory, source_a),
            source_a_key_columns,
            key_pattern=rule.get("source_a_key_pattern", rule.get("key_pattern")),
        )
        source_b_keys = _table_key_map(
            _table_rows_for_source(inventory, source_b),
            source_b_key_columns,
            key_pattern=rule.get("source_b_key_pattern", rule.get("key_pattern")),
        )
        missing = sorted(set(source_a_keys) - set(source_b_keys), key=_ref_sort_key)
        if not missing:
            continue
        findings.append(
            AuditFinding(
                code=str(rule["code"]),
                severity=str(rule.get("severity", "severe")),
                message=str(rule.get("message", "Required table keys are missing from a rendered view.")),
                source_view="contract_table_key_coverage_rule",
                evidence={
                    "required_from": _source_label(source_a),
                    "must_exist_in": _source_label(source_b),
                    "source_a_key_columns": source_a_key_columns,
                    "source_b_key_columns": source_b_key_columns,
                    "source_a_keys": sorted(source_a_keys, key=_ref_sort_key),
                    "source_b_keys": sorted(source_b_keys, key=_ref_sort_key),
                    "missing_keys": missing,
                    "missing_raw_keys": [source_a_keys[key]["raw_key"] for key in missing],
                },
            )
        )
    return findings


def _run_table_unique_key_rules(inventory: dict[str, Any], contract: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for rule in contract.get("table_unique_key_rules", []):
        rows = _table_rows_for_source(inventory, dict(rule.get("source", {})))
        key_column = str(rule["key_column"])
        value_columns = [str(column) for column in rule.get("value_columns", [])]
        grouped: dict[str, dict[str, set[str]]] = {}
        raw_grouped: dict[str, dict[str, list[str]]] = {}
        for row in rows:
            key = _row_value(row, key_column)
            if not key:
                continue
            grouped.setdefault(key, {column: set() for column in value_columns})
            raw_grouped.setdefault(key, {column: [] for column in value_columns})
            for column in value_columns:
                value = _row_value(row, column)
                if not value:
                    continue
                grouped[key][column].add(_normalize_value(value))
                raw_grouped[key][column].append(value)
        for key, column_values in sorted(grouped.items()):
            conflicting_columns = [column for column, values in column_values.items() if len(values) > 1]
            if not conflicting_columns:
                continue
            findings.append(
                AuditFinding(
                    code=str(rule["code"]),
                    severity=str(rule.get("severity", "severe")),
                    message=str(rule.get("message", "A rendered table defines conflicting values for the same key.")),
                    source_view="contract_table_unique_key_rule",
                    evidence={
                        "key": key,
                        "key_column": key_column,
                        "conflicting_columns": conflicting_columns,
                        "values_by_column": {
                            column: raw_grouped[key][column]
                            for column in conflicting_columns
                        },
                    },
                )
            )
    return findings


def _run_mermaid_node_value_rules(inventory: dict[str, Any], contract: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    patterns = dict(contract.get("id_patterns", {}))
    for rule in contract.get("mermaid_node_value_rules", []):
        table_source = dict(rule.get("table_source", rule.get("source", {})))
        mermaid_source = dict(rule.get("mermaid_source", {}))
        key_columns = _column_candidates(rule, "key_columns", "key_column", "key_column")
        value_columns = _column_candidates(rule, "value_columns", "value_column", "value_column")
        key_pattern = rule.get("key_pattern")
        key_pattern_spec = patterns.get(str(key_pattern)) if isinstance(key_pattern, str) else key_pattern
        table_values = _table_key_value_map(
            _table_rows_for_source(inventory, table_source),
            key_columns,
            value_columns,
            key_pattern=key_pattern_spec,
            value_pattern=rule.get("value_pattern"),
        )
        mermaid_text = _source_text_for_reference_set(inventory, mermaid_source)
        mermaid_values = _mermaid_node_value_map(mermaid_text, key_pattern_spec)
        for key, table_value in sorted(table_values.items()):
            mermaid_value = mermaid_values.get(key)
            if mermaid_value is None or _normalize_value(table_value["value"]) == _normalize_value(mermaid_value["value"]):
                continue
            findings.append(
                AuditFinding(
                    code=str(rule["code"]),
                    severity=str(rule.get("severity", "severe")),
                    message=str(rule.get("message", "Mermaid node labels conflict with a rendered table value.")),
                    source_view="contract_mermaid_node_value_rule",
                    evidence={
                        "key": key,
                        "key_columns": key_columns,
                        "value_columns": value_columns,
                        "table_value": table_value["value"],
                        "mermaid_value": mermaid_value["value"],
                        "table_raw_value": table_value["raw_value"],
                        "mermaid_raw_value": mermaid_value["raw_value"],
                        "mermaid_node": mermaid_value["node"],
                    },
                )
            )
    return findings


def _mermaid_node_value_map(text: str, key_pattern: Any) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for raw_node, label in _extract_mermaid_node_labels(text):
        key = _canonicalize_cell(raw_node, key_pattern)
        if key and label:
            result[key] = {"node": raw_node, "raw_value": label, "value": label}
    return result


def _run_field_subset_rules(inventory: dict[str, Any], contract: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for rule in contract.get("field_subset_rules", []):
        fields = _extract_key_value_fields(_source_text_for_reference_set(inventory, dict(rule.get("source", {}))))
        key_field = str(rule.get("key_field", rule["required_field"]))
        required_field = str(rule["required_field"])
        available_field = str(rule["available_field"])
        raw_required = _field_value(fields, required_field)
        raw_available = _field_value(fields, available_field)
        patterns = _patterns_for_rule(contract, rule)
        required_refs = _extract_refs_with_patterns(raw_required, patterns)
        available_refs = _extract_refs_with_patterns(raw_available, patterns)
        missing = sorted(required_refs - available_refs, key=_ref_sort_key)
        if not missing:
            continue
        findings.append(
            AuditFinding(
                code=str(rule["code"]),
                severity=str(rule.get("severity", "severe")),
                message=str(rule.get("message", "Required references are missing from available references.")),
                source_view="contract_field_subset_rule",
                evidence={
                    "key": key_field,
                    "key_field": key_field,
                    "required_field": required_field,
                    "available_field": available_field,
                    "required_refs": sorted(required_refs, key=_ref_sort_key),
                    "available_refs": sorted(available_refs, key=_ref_sort_key),
                    "missing_refs": missing,
                    "raw_required": raw_required,
                    "raw_available": raw_available,
                },
            )
        )
    return findings


def _run_field_value_rules(inventory: dict[str, Any], contract: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for rule in contract.get("field_value_rules", []):
        source_a_fields = _extract_key_value_fields(_source_text_for_reference_set(inventory, dict(rule.get("source_a", {}))))
        source_b_fields = _extract_key_value_fields(_source_text_for_reference_set(inventory, dict(rule.get("source_b", {}))))
        source_a_field_names = _column_candidates(rule, "source_a_fields", "source_a_field", "field")
        source_b_field_names = _column_candidates(rule, "source_b_fields", "source_b_field", "field")
        value_a, source_a_field = _field_value_from_names(source_a_fields, source_a_field_names)
        value_b, source_b_field = _field_value_from_names(source_b_fields, source_b_field_names)
        if not value_a or not value_b or _normalize_value(value_a) == _normalize_value(value_b):
            continue
        findings.append(
            AuditFinding(
                code=str(rule["code"]),
                severity=str(rule.get("severity", "severe")),
                message=str(rule.get("message", "Rendered key-value fields conflict.")),
                source_view="contract_field_value_rule",
                evidence={
                    "field": str(rule.get("field") or source_a_field or source_b_field),
                    "source_a_field": source_a_field,
                    "source_b_field": source_b_field,
                    "source_a_fields": source_a_field_names,
                    "source_b_fields": source_b_field_names,
                    "source_a_value": value_a,
                    "source_b_value": value_b,
                },
            )
        )
    return findings


def _run_forbidden_alias_rules(inventory: dict[str, Any], contract: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    text = str(inventory.get("text", ""))
    for rule in contract.get("forbidden_aliases", []):
        for alias in [str(item) for item in rule.get("forbidden", [])]:
            pattern = _identifier_variant_pattern(alias) if rule.get("match_identifier_variants") else rf"\b{re.escape(alias)}\b"
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            findings.append(
                AuditFinding(
                    code=str(rule["code"]),
                    severity=str(rule.get("severity", "severe")),
                    message=str(rule.get("message", "A forbidden alias appears in the rendered artifact.")),
                    source_view="contract_alias_rule",
                    evidence={
                        "canonical": str(rule.get("canonical", "")),
                        "forbidden_alias": alias,
                        "matched_text": match.group(0),
                    },
                )
            )
    return findings


def _run_forbidden_pattern_rules(inventory: dict[str, Any], contract: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for rule in contract.get("forbidden_patterns", []):
        source = rule.get("source")
        text = (
            _source_text_for_reference_set(inventory, dict(source))
            if isinstance(source, dict)
            else str(inventory.get("text", ""))
        )
        regex = str(rule["regex"])
        for match in re.finditer(regex, text, re.IGNORECASE):
            findings.append(
                AuditFinding(
                    code=str(rule["code"]),
                    severity=str(rule.get("severity", "severe")),
                    message=str(rule.get("message", "A forbidden pattern appears in the rendered artifact.")),
                    source_view="contract_forbidden_pattern_rule",
                    evidence={
                        "regex": regex,
                        "matched_text": match.group(0),
                    },
                )
            )
    return findings


def _table_rows_for_source(inventory: dict[str, Any], source: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for table in _tables_for_source(inventory, source):
        rows.extend(table.get("rows", []))
    return rows


def _tables_for_source(inventory: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    section_titles = [str(title) for title in source.get("section_titles", [])]
    if not section_titles:
        tables = list(inventory.get("tables", []))
    else:
        tables = []
        for section_body in _section_bodies(inventory, section_titles):
            tables.extend(_extract_tables(section_body))

    required_headers = {_normalize_header(header) for header in _source_table_headers(source)}
    if not required_headers:
        return tables
    return [
        table
        for table in tables
        if required_headers.issubset({_normalize_header(str(header)) for header in table.get("headers", [])})
    ]


def _source_table_headers(source: dict[str, Any]) -> list[str]:
    for key in ("table_headers", "required_headers", "required_table_headers"):
        raw_headers = source.get(key)
        if raw_headers is None:
            continue
        if isinstance(raw_headers, str):
            return [raw_headers]
        return [str(header) for header in raw_headers if str(header)]
    return []


def _source_ref_columns(source: dict[str, Any]) -> list[str]:
    for key in ("ref_columns", "reference_columns", "columns"):
        raw_columns = source.get(key)
        if raw_columns is None:
            continue
        if isinstance(raw_columns, str):
            return [raw_columns] if raw_columns else []
        return [str(column) for column in raw_columns if str(column)]
    return []


def _column_candidates(rule: dict[str, Any], plural_key: str, singular_key: str, fallback_key: str) -> list[str]:
    raw_columns = rule.get(plural_key)
    if raw_columns is None:
        raw_columns = rule.get(singular_key, rule.get(fallback_key, ""))
    if isinstance(raw_columns, str):
        return [raw_columns] if raw_columns else []
    return [str(column) for column in raw_columns if str(column)]


def _table_key_value_map(
    rows: list[dict[str, str]],
    key_columns: list[str],
    value_columns: list[str],
    *,
    key_pattern: Any = None,
    value_pattern: Any = None,
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        raw_key, key_column = _row_value_from_columns(row, key_columns)
        raw_value, value_column = _row_value_from_columns(row, value_columns)
        key = _canonicalize_cell(raw_key, key_pattern)
        value = _canonicalize_cell(raw_value, value_pattern)
        if key and value:
            result[key] = {
                "raw_key": raw_key,
                "raw_value": raw_value,
                "key_column": key_column,
                "value_column": value_column,
                "value": value,
            }
    return result


def _table_key_map(
    rows: list[dict[str, str]],
    key_columns: list[str],
    *,
    key_pattern: Any = None,
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        raw_key, key_column = _row_value_from_columns(row, key_columns)
        key = _canonicalize_cell(raw_key, key_pattern)
        if key:
            result[key] = {"raw_key": raw_key, "key_column": key_column}
    return result


def _patterns_for_rule(contract: dict[str, Any], rule: dict[str, Any]) -> list[dict[str, Any]]:
    patterns = dict(contract.get("id_patterns", {}))
    return [
        pattern
        for pattern_name in [str(name) for name in rule.get("patterns", [])]
        if isinstance((pattern := patterns.get(pattern_name)), dict)
    ]


def _extract_refs_with_patterns(text: str, patterns: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for pattern in patterns:
        refs.update(_extract_refs(text, pattern))
    return refs


def _extract_key_value_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*(?:[-*]\s*)?(?P<key>[A-Za-z0-9_.-]+)\s*:\s*(?P<value>.+?)\s*$", line)
        if not match:
            continue
        fields[match.group("key")] = match.group("value")
    return fields


def _field_value(fields: dict[str, str], field_name: str) -> str:
    normalized_target = _normalize_header(field_name)
    for key, value in fields.items():
        if _normalize_header(key) == normalized_target:
            return value
    return ""


def _field_value_from_names(fields: dict[str, str], field_names: list[str]) -> tuple[str, str]:
    for field_name in field_names:
        value = _field_value(fields, field_name)
        if value:
            return value, field_name
    return "", field_names[0] if field_names else ""


def _row_value(row: dict[str, str], column_name: str) -> str:
    normalized_target = _normalize_header(column_name)
    for header, value in row.items():
        if _normalize_header(header) == normalized_target:
            return value
    return ""


def _row_value_from_columns(row: dict[str, str], column_names: list[str]) -> tuple[str, str]:
    for column_name in column_names:
        value = _row_value(row, column_name)
        if value:
            return value, column_name
    return "", column_names[0] if column_names else ""


def _identifier_variant_pattern(value: str) -> str:
    parts = [part for part in re.split(r"[-_\s]+", value.strip()) if part]
    if len(parts) <= 1:
        return rf"\b{re.escape(value)}\b"
    return r"\b" + r"[-_\s]+".join(re.escape(part) for part in parts) + r"\b"


def _source_label(source: dict[str, Any]) -> str:
    section_titles = [str(title) for title in source.get("section_titles", []) if str(title)]
    if section_titles:
        return ", ".join(section_titles)
    table_headers = _source_table_headers(source)
    if table_headers:
        return ", ".join(table_headers)
    mermaid_types = [str(item) for item in source.get("mermaid_diagram_types", []) if str(item)]
    if mermaid_types:
        return ", ".join(mermaid_types)
    return "artifact"


def _canonicalize_cell(value: str, pattern: Any) -> str:
    if isinstance(pattern, dict):
        refs = sorted(_extract_refs(value, pattern), key=_ref_sort_key)
        if refs:
            return refs[0]
    return value


def _title_for_code(code: str) -> str:
    label = code.rsplit(".", 1)[-1]
    words = []
    for part in label.split("_"):
        if part.lower() == "ids":
            words.append("IDs")
        else:
            words.append(part.capitalize())
    return " ".join(words)


def _looks_like_table_row(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and line.count("|") >= 2


def _looks_like_separator_row(line: str) -> bool:
    if not _looks_like_table_row(line):
        return False
    cells = _split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _split_table_row(line: str) -> list[str]:
    return [_clean_cell(cell) for cell in line.strip().strip("|").split("|")]


def _clean_cell(value: str) -> str:
    return value.strip().strip("`").strip()


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", _clean_cell(value).lower().replace("_", " "))


def _normalize_value(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _mermaid_diagram_type(first_line: str) -> str:
    lower = first_line.lower()
    if lower.startswith("flowchart"):
        return "flowchart"
    if lower.startswith("statediagram"):
        return "stateDiagram"
    if lower.startswith("sequencediagram"):
        return "sequenceDiagram"
    if lower.startswith("erdiagram"):
        return "erDiagram"
    if lower.startswith("gantt"):
        return "gantt"
    return first_line.split(maxsplit=1)[0] if first_line else "unknown"


def _ref_sort_key(value: str) -> tuple[str, int, str]:
    match = re.match(r"^([A-Za-z_-]+)-0*(\d+)$", value)
    if match:
        return (match.group(1), int(match.group(2)), value)
    return (value, -1, value)


def _relation_sort_key(relation: tuple[str, str]) -> tuple[tuple[str, int, str], tuple[str, int, str]]:
    return (_ref_sort_key(relation[0]), _ref_sort_key(relation[1]))


def _format_relations(relations: set[tuple[str, str]] | list[tuple[str, str]]) -> list[str]:
    return [f"{left} -> {right}" for left, right in sorted(relations, key=_relation_sort_key)]
