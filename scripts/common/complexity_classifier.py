#!/usr/bin/env python3
"""
Suggest a Phase-2 complexity profile from a Phase-1 PRD.
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

from common.gwt_format_checker import markdown_tables


COMPLEXITY_PROFILES = ("micro", "standard", "complex")
PROFILE_ORDER = {"micro": 0, "standard": 1, "complex": 2}

INTEGRATION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("llm_provider", r"\b(openai|anthropic|llm provider|model provider)\b"),
    ("identity_provider", r"\b(auth0|clerk|okta|oauth|oidc|sso|identity provider)\b"),
    ("payment_provider", r"\b(stripe|adyen|payment provider|billing provider)\b"),
    ("message_bus", r"\b(kafka|sqs|pubsub|pub/sub|queue|event bus|消息队列)\b"),
    ("warehouse", r"\b(bigquery|snowflake|redshift|warehouse)\b"),
    ("storage", r"\b(s3|blob storage|object storage|minio)\b"),
    ("search", r"\b(elasticsearch|opensearch|search engine)\b"),
    ("crm", r"\b(salesforce|hubspot|crm)\b"),
    ("email", r"\b(sendgrid|ses|mailgun|email provider)\b"),
    ("analytics", r"\b(segment|mixpanel|amplitude|analytics sdk)\b"),
    ("cms_or_store", r"\b(shopify|wordpress|contentful|cms)\b"),
    ("webhook_or_external_api", r"\b(webhook|external api|third-party api|第三方接口|外部接口)\b"),
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_h2_block(text: str, title_pattern: str) -> str:
    match = re.search(rf"^##\s+{title_pattern}\b.*$", text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_h2 = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)
    end = start + next_h2.start() if next_h2 else len(text)
    return text[start:end]


def extract_h3_block(text: str, title_pattern: str) -> str:
    match = re.search(rf"^###\s+{title_pattern}\b.*$", text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^##\s+|^###\s+", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def count_table_rows(block: str, required_headers: set[str]) -> int:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(str(row.get(header, "")).strip() for header in required_headers))
    return 0


def count_epics(text: str) -> int:
    block = extract_h3_block(text, r"Epic Decomposition|史诗分解")
    rows = count_table_rows(block, {"epic_id", "epic_name"})
    if rows:
        return rows
    return len(re.findall(r"\bEP-[0-9]{2,3}\b", block))


def count_requirements(text: str) -> int:
    registry_block = extract_h3_block(text, r"Requirement Translation Registry|需求转译")
    rows = count_table_rows(registry_block, {"requirement_id", "requirement_class"})
    if rows:
        return rows
    extended_block = extract_h3_block(text, r"Extended Requirement Set")
    return len(re.findall(r"\bRQ-[0-9]{2,3}\b", extended_block))


def count_domain_entities(text: str) -> int | None:
    block = extract_h2_block(text, r"(?:10\.\s+)?Domain Model")
    if not block:
        return None
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if headers & {"entity", "entity_name", "business_entity", "domain_entity", "object"}:
            entity_header = next(
                header
                for header in ("entity", "entity_name", "business_entity", "domain_entity", "object")
                if header in headers
            )
            count = sum(1 for row in table["rows"] if str(row.get(entity_header, "")).strip())
            if count:
                return count

    entities: set[str] = set()
    in_mermaid = False
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("```mermaid"):
            in_mermaid = True
            continue
        if in_mermaid and stripped == "```":
            in_mermaid = False
            continue
        if not in_mermaid:
            continue
        if not any(token in stripped for token in ("||--", "}o--", "}o..", "||..", "|o--", "|{--")):
            continue
        for entity in re.findall(r"\b[A-Z][A-Za-z0-9_]+\b", stripped):
            if entity not in {"ER", "Diagram"}:
                entities.add(entity)
    return len(entities) or None


def count_external_integrations(text: str) -> int:
    dependencies_block = extract_h2_block(text, r"(?:16\.\s+)?Dependencies, Risks, and Review-Bound Truth")
    architecture_block = extract_h2_block(text, r"(?:18\.\s+)?Handoff to Design / Architecture")
    search_text = "\n".join([dependencies_block, architecture_block, text[:4000]])
    categories = {
        name
        for name, pattern in INTEGRATION_PATTERNS
        if re.search(pattern, search_text, flags=re.IGNORECASE)
    }
    return len(categories)


def bucket_from_thresholds(value: int, *, micro_max: int, standard_max: int) -> str:
    if value <= micro_max:
        return "micro"
    if value <= standard_max:
        return "standard"
    return "complex"


def vote_summary(votes: list[str]) -> tuple[str, dict[str, int]]:
    counts = {profile: votes.count(profile) for profile in COMPLEXITY_PROFILES}
    max_votes = max(counts.values()) if counts else 0
    tied = [profile for profile, count in counts.items() if count == max_votes]
    if "standard" in tied:
        chosen = "standard"
    else:
        chosen = sorted(tied, key=lambda profile: PROFILE_ORDER[profile])[0]
    return chosen, counts


def classify_phase1_prd(phase1_prd: Path) -> dict[str, object]:
    text = read_text(phase1_prd)

    epic_count = count_epics(text)
    requirement_count = count_requirements(text)
    external_integration_count = count_external_integrations(text)
    domain_count_hint = count_domain_entities(text)

    indicators: dict[str, dict[str, object]] = {
        "epic_count": {
            "value": epic_count,
            "profile_vote": bucket_from_thresholds(epic_count, micro_max=2, standard_max=5),
            "rule": "micro <= 2, standard 3-5, complex >= 6",
            "reason": f"Epic Decomposition rows = {epic_count}",
        },
        "requirement_count": {
            "value": requirement_count,
            "profile_vote": bucket_from_thresholds(requirement_count, micro_max=8, standard_max=25),
            "rule": "micro <= 8, standard 9-25, complex >= 26",
            "reason": f"Requirement rows = {requirement_count}",
        },
        "external_integration_count": {
            "value": external_integration_count,
            "profile_vote": bucket_from_thresholds(external_integration_count, micro_max=1, standard_max=4),
            "rule": "micro <= 1, standard 2-4, complex >= 5",
            "reason": f"Detected integration categories = {external_integration_count}",
        },
    }
    if domain_count_hint is not None:
        indicators["domain_count_hint"] = {
            "value": domain_count_hint,
            "profile_vote": bucket_from_thresholds(domain_count_hint, micro_max=2, standard_max=4),
            "rule": "micro <= 2, standard 3-4, complex >= 5",
            "reason": f"Detected domain/entity hint = {domain_count_hint}",
        }
    else:
        indicators["domain_count_hint"] = {
            "value": None,
            "profile_vote": "standard",
            "rule": "micro <= 2, standard 3-4, complex >= 5",
            "reason": "Domain/entity hint could not be read reliably; defaulted to standard-biased vote",
        }

    votes = [str(indicator["profile_vote"]) for indicator in indicators.values()]
    suggested_profile, vote_counts = vote_summary(votes)
    max_votes = max(vote_counts.values()) if vote_counts else 0
    confidence = "high" if max_votes >= 3 else "medium" if max_votes == 2 else "low"

    return {
        "phase1_prd": str(phase1_prd),
        "indicators": indicators,
        "vote_counts": vote_counts,
        "suggested_profile": suggested_profile,
        "selection_confidence": confidence,
        "rationale": [str(indicator["reason"]) for indicator in indicators.values()],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest a Phase-2 complexity profile from a Phase-1 PRD")
    parser.add_argument("--phase1-prd", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    report = classify_phase1_prd(Path(args.phase1_prd).resolve())
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).resolve().write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
