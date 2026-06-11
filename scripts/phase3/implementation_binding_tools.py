from __future__ import annotations

from collections import Counter
import json
import re
from pathlib import Path
from typing import Any

from phase3.contract_test_scaffolder import build_contract_test_target_lookup
from phase3.contract_tools import parse_implementation_start_order_rows, parse_work_package_rows


def backend_module_unit_test_path(module_slug: str) -> str:
    return f"tests/unit/api/modules/{module_slug}.unit.test.ts"


def backend_foundation_unit_test_paths() -> list[str]:
    return ["tests/unit/api/foundation/runtime-foundation.unit.test.ts"]


def foundation_implementation_targets_for_test_targets(test_targets: list[str]) -> list[str]:
    foundation_tests = set(backend_foundation_unit_test_paths())
    if not any(str(target).strip() in foundation_tests for target in test_targets):
        return []
    return [
        "apps/api/src/common/auth-session.ts",
        "apps/api/src/common/generated-runtime.ts",
        "apps/api/src/common/operation-support.ts",
        "apps/api/src/common/runtime-adapter.ts",
    ]


def frontend_surface_unit_test_path(route: str) -> str:
    return f"tests/unit/web/{route}.unit.test.ts"


def unit_test_targets_for_implementation_targets(targets: list[str]) -> list[str]:
    unit_targets: set[str] = set()
    for target in targets:
        normalized = str(target).strip()
        if not normalized:
            continue
        backend_match = re.match(r"^apps/api/src/modules/([^/]+)/", normalized)
        if backend_match:
            unit_targets.add(backend_module_unit_test_path(backend_match.group(1)))
            continue
        frontend_match = re.match(r"^apps/web/app/(.+)/page\.tsx$", normalized)
        if frontend_match:
            unit_targets.add(frontend_surface_unit_test_path(frontend_match.group(1).replace("/", "-")))
    return sorted(unit_targets)


def parse_openapi_operations(spec: dict[str, object]) -> list[dict[str, str]]:
    operations: list[dict[str, str]] = []
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return operations
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            tags = operation.get("tags", [])
            first_tag = str(tags[0]).strip() if isinstance(tags, list) and tags else "default"
            operations.append(
                {
                    "operation_id": str(operation.get("operationId", "")).strip(),
                    "method": str(method).lower(),
                    "path": str(path),
                    "tag": first_tag,
                }
            )
    return operations


def build_wp_lookup(esp_text: str) -> list[dict[str, object]]:
    try:
        rows = parse_work_package_rows(esp_text)
    except ValueError:
        rows = parse_implementation_start_order_rows(esp_text)
    return rows


TRACE_REF_PATTERN = re.compile(r"\b(?:SCN|RP)-[A-Za-z0-9][A-Za-z0-9_-]*\b", flags=re.IGNORECASE)
OPERATION_IDS_RE = re.compile(r"const operationIds = (\[[^;]*\]);", re.DOTALL)
SCOPE_TOKEN_STOPWORDS = {
    "after",
    "before",
    "context",
    "edge",
    "explicit",
    "foundation",
    "handoff",
    "into",
    "native",
    "path",
    "paths",
    "posture",
    "ready",
    "replay",
    "replayable",
    "remain",
    "remains",
    "still",
    "through",
    "under",
    "visible",
    "with",
    "without",
}

VERIFICATION_HOOK_STOPWORDS = {
    "audit",
    "check",
    "checklist",
    "coverage",
    "diff",
    "evidence",
    "hook",
    "matrix",
    "metric",
    "proof",
    "replay",
    "report",
    "response",
    "review",
    "score",
    "snapshot",
    "trace",
    "validation",
    "verify",
    "walkthrough",
}

SCOPE_TERM_EQUIVALENTS: dict[str, set[str]] = {
    "complete": {"completion"},
    "completion": {"complete"},
    "launch": {"start"},
    "start": {"launch"},
}


def trace_ids_in_text(text: str) -> set[str]:
    return {match.group(0).upper() for match in TRACE_REF_PATTERN.finditer(text)}


def scope_tokens(text: str) -> set[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    tokens: set[str] = set()
    for raw_token in re.split(r"[^A-Za-z0-9]+", expanded):
        token = raw_token.lower()
        if len(token) < 4 or token in SCOPE_TOKEN_STOPWORDS:
            continue
        tokens.add(token)
        if token.endswith("ies") and len(token) > 4:
            tokens.add(token[:-3] + "y")
        elif token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "us", "is")):
            tokens.add(token[:-1])
    return tokens


def expand_scope_term_equivalents(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    for token in list(tokens):
        expanded.update(SCOPE_TERM_EQUIVALENTS.get(token, set()))
    return expanded


def canonical_scope_token(token: str) -> str:
    group = {token}
    pending = [token]
    while pending:
        current = pending.pop()
        for equivalent in SCOPE_TERM_EQUIVALENTS.get(current, set()):
            if equivalent in group:
                continue
            group.add(equivalent)
            pending.append(equivalent)
    return sorted(group)[0]


def scope_concept_tokens(text: str) -> set[str]:
    return {canonical_scope_token(token) for token in scope_tokens(text)}


def suggest_work_packages(
    source_id: str,
    source_subject: str,
    wp_rows: list[dict[str, object]],
    *,
    source_type: str = "",
    verification_hook: str = "",
) -> list[str]:
    subject_tokens = scope_concept_tokens(source_subject)
    hook_tokens = {canonical_scope_token(token) for token in scope_tokens(verification_hook) - VERIFICATION_HOOK_STOPWORDS}
    source_tokens = subject_tokens | hook_tokens
    suggestions: list[str] = []
    fallback_scores: Counter[str] = Counter()
    for row in wp_rows:
        wp_id = str(row.get("wp_id", "")).strip()
        acceptance = str(row.get("acceptance_criteria", "")).strip()
        scope = str(row.get("scope", "")).strip() or str(row.get("implementation_scope", "")).strip()
        referenced = trace_ids_in_text(f"{scope} {acceptance}")
        wp_tokens = scope_concept_tokens(f"{scope} {acceptance}")
        if source_id.upper() in referenced:
            suggestions.append(wp_id)
            continue
        subject_overlap = len(subject_tokens & wp_tokens)
        hook_overlap = len(hook_tokens & wp_tokens)
        overlap_count = len(source_tokens & wp_tokens)
        if source_type == "contract-trace":
            if hook_overlap >= 1:
                fallback_scores[wp_id] += hook_overlap * 3 + subject_overlap
                continue
            if source_tokens and overlap_count >= 2:
                suggestions.append(wp_id)
                continue
            if subject_overlap >= 2:
                fallback_scores[wp_id] += subject_overlap
            continue
        if source_tokens and overlap_count >= 2:
            suggestions.append(wp_id)
        if source_type in {"scenario", "replay"}:
            if subject_overlap >= 1:
                fallback_scores[wp_id] += subject_overlap
                if source_type == "replay":
                    fallback_scores[wp_id] += hook_overlap
            elif not subject_tokens and hook_overlap >= 1:
                fallback_scores[wp_id] += hook_overlap

    normalized = sorted(set(filter(None, suggestions)))
    if normalized:
        return normalized
    if source_type not in {"contract-trace", "scenario", "replay"} or not fallback_scores:
        return normalized
    best_score = max(fallback_scores.values())
    if best_score <= 0:
        return normalized
    return sorted(set(normalized) | {wp_id for wp_id, score in fallback_scores.items() if score == best_score})


def infer_work_packages_from_targets(
    *,
    implementation_targets: list[str],
    inferred_targets_by_wp: dict[str, list[str]],
) -> list[str]:
    target_set = {str(item).strip() for item in implementation_targets if str(item).strip()}
    if not target_set:
        return []

    scores: Counter[str] = Counter()
    for wp_id, inferred_targets in inferred_targets_by_wp.items():
        inferred_target_set = {str(item).strip() for item in inferred_targets if str(item).strip()}
        overlap = len(target_set & inferred_target_set)
        if overlap >= 1:
            scores[wp_id] = overlap

    if not scores:
        return []
    best_score = max(scores.values())
    return sorted(wp_id for wp_id, score in scores.items() if score == best_score)


def explicit_work_packages(row: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(item).strip().upper()
            for item in row.get("linked_rbi_or_wp", [])
            if str(item).strip().upper().startswith("WP-")
        }
    )


def parse_operation_ids_from_generated_test(test_path: Path) -> list[str]:
    try:
        text = test_path.read_text(encoding="utf-8")
    except OSError:
        return []
    match = OPERATION_IDS_RE.search(text)
    if not match:
        return []
    try:
        raw = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def contract_test_operation_map(operations: list[dict[str, str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    target_lookup = build_contract_test_target_lookup(list(operations))
    for operation in operations:
        operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
        method = str(operation["method"]).upper()
        path = str(operation["path"])
        mapping[f"tests/contracts/{target_lookup[(operation_id, method, path)]}"] = operation_id
    return mapping


def rebind_cross_operation_test_rows(
    *,
    binding_rows: list[dict[str, Any]],
    operations: list[dict[str, str]],
    output_dir: Path,
    inferred_targets_by_wp: dict[str, list[str]],
    wp_rows: list[dict[str, object]],
) -> None:
    contract_operation_by_test = contract_test_operation_map(operations)
    operation_to_work_packages: dict[str, set[str]] = {}
    for row in binding_rows:
        work_packages = {
            str(item).strip().upper()
            for item in row.get("work_packages", [])
            if str(item).strip()
        }
        if not work_packages:
            continue
        for test_target in [
            str(item).strip().replace("\\", "/")
            for item in row.get("test_targets", [])
            if str(item).strip()
        ]:
            operation_id = contract_operation_by_test.get(test_target)
            if operation_id:
                operation_to_work_packages.setdefault(operation_id, set()).update(work_packages)

    if not operation_to_work_packages:
        return

    wp_order = {
        str(row.get("wp_id", "")).strip().upper(): index
        for index, row in enumerate(wp_rows)
        if str(row.get("wp_id", "")).strip()
    }
    fallback_order = len(wp_order) + 1

    for row in binding_rows:
        cross_operation_tests = [
            str(item).strip().replace("\\", "/")
            for item in row.get("test_targets", [])
            if str(item).strip().startswith(("tests/scenarios/", "tests/replays/"))
        ]
        if not cross_operation_tests:
            continue
        required_work_packages: set[str] = set()
        for test_target in cross_operation_tests:
            for operation_id in parse_operation_ids_from_generated_test(output_dir / test_target):
                required_work_packages.update(operation_to_work_packages.get(operation_id, set()))
        if not required_work_packages:
            continue
        latest_work_package = sorted(
            required_work_packages,
            key=lambda wp_id: (wp_order.get(wp_id, fallback_order), wp_id),
        )[-1]
        row["work_packages"] = [latest_work_package]
        implementation_targets = {
            str(item).strip()
            for item in row.get("implementation_targets", [])
            if str(item).strip()
        }
        implementation_targets.update(
            str(item).strip() for item in inferred_targets_by_wp.get(latest_work_package, []) if str(item).strip()
        )
        if implementation_targets:
            row["implementation_targets"] = sorted(implementation_targets)


def infer_work_packages_from_replay_overlap(
    *,
    source_row: dict[str, Any],
    trace_rows: list[dict[str, Any]],
) -> list[str]:
    source_upstream = {
        str(item).strip().upper()
        for item in source_row.get("upstream_trace_ids", [])
        if str(item).strip()
    }
    if len(source_upstream) < 2:
        return []

    scores: Counter[str] = Counter()
    for row in trace_rows:
        if row is source_row or str(row.get("source_type", "")).strip() != "replay":
            continue
        replay_work_packages = explicit_work_packages(row)
        if not replay_work_packages:
            continue
        replay_upstream = {
            str(item).strip().upper()
            for item in row.get("upstream_trace_ids", [])
            if str(item).strip()
        }
        overlap = len(source_upstream & replay_upstream)
        if overlap < 2:
            continue
        for wp_id in replay_work_packages:
            scores[wp_id] += overlap

    if not scores:
        return []
    best_score = max(scores.values())
    return sorted(wp_id for wp_id, score in scores.items() if score == best_score)


def propagate_shared_test_bindings(
    *,
    binding_rows: list[dict[str, Any]],
    inferred_targets_by_wp: dict[str, list[str]],
) -> None:
    shared_work_packages_by_test: dict[str, set[str]] = {}
    shared_targets_by_test: dict[str, set[str]] = {}
    for row in binding_rows:
        tests = {str(item).strip() for item in row.get("test_targets", []) if str(item).strip()}
        work_packages = {str(item).strip() for item in row.get("work_packages", []) if str(item).strip()}
        implementation_targets = {
            str(item).strip() for item in row.get("implementation_targets", []) if str(item).strip()
        }
        for test_target in tests:
            if work_packages:
                shared_work_packages_by_test.setdefault(test_target, set()).update(work_packages)
            if implementation_targets:
                shared_targets_by_test.setdefault(test_target, set()).update(implementation_targets)

    for row in binding_rows:
        tests = {str(item).strip() for item in row.get("test_targets", []) if str(item).strip()}
        work_packages = {str(item).strip() for item in row.get("work_packages", []) if str(item).strip()}
        if not work_packages:
            inherited_work_packages = {
                wp_id
                for test_target in tests
                for wp_id in shared_work_packages_by_test.get(test_target, set())
                if wp_id
            }
            if inherited_work_packages:
                row["work_packages"] = sorted(inherited_work_packages)
                work_packages = inherited_work_packages

        implementation_targets = {
            str(item).strip() for item in row.get("implementation_targets", []) if str(item).strip()
        }
        if not implementation_targets:
            inherited_targets = {
                target
                for test_target in tests
                for target in shared_targets_by_test.get(test_target, set())
                if target
            }
            for wp_id in work_packages:
                inherited_targets.update(
                    str(item).strip() for item in inferred_targets_by_wp.get(wp_id, []) if str(item).strip()
                )
            if not inherited_targets and work_packages:
                inherited_targets.update(
                    str((Path("work-packages") / wp_id.lower() / "implementation-plan.md"))
                    for wp_id in work_packages
                    if wp_id
                )
            if inherited_targets:
                row["implementation_targets"] = sorted(inherited_targets)


def append_generated_unit_test_bindings(binding_rows: list[dict[str, Any]]) -> None:
    foundation_tests = backend_foundation_unit_test_paths()
    for row in binding_rows:
        implementation_targets = [
            str(item).strip()
            for item in row.get("implementation_targets", [])
            if str(item).strip()
        ]
        generated_unit_tests = unit_test_targets_for_implementation_targets(implementation_targets)
        if any(target.startswith("apps/api/") for target in implementation_targets):
            generated_unit_tests = sorted({*generated_unit_tests, *foundation_tests})
        if not generated_unit_tests:
            continue
        row["test_targets"] = sorted(
            {
                str(item).strip()
                for item in [*row.get("test_targets", []), *generated_unit_tests]
                if str(item).strip()
            }
        )
        row["runtime_evidence_refs"] = sorted(
            {
                str(item).strip()
                for item in [*row.get("runtime_evidence_refs", []), *generated_unit_tests]
                if str(item).strip()
            }
        )


def append_generated_sql_test_bindings(binding_rows: list[dict[str, Any]], *, output_dir: Path) -> None:
    sql_tests = sorted(
        str(path.relative_to(output_dir)).replace("\\", "/")
        for path in (output_dir / "tests" / "sql").glob("*.sql.test.ts")
    )
    if not sql_tests:
        return
    for row in binding_rows:
        implementation_targets = [
            str(item).strip()
            for item in row.get("implementation_targets", [])
            if str(item).strip()
        ]
        if not any(target.startswith("apps/api/") for target in implementation_targets):
            continue
        row["test_targets"] = sorted(
            {
                str(item).strip()
                for item in [*row.get("test_targets", []), *sql_tests]
                if str(item).strip()
            }
        )
