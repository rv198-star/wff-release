from __future__ import annotations

import re
import shlex
from typing import Any


SLICE_PACKET_CLAIM_CEILING = (
    "slice packet protocol only; implementation quality still requires a write-capable runner or human/main-thread "
    "execution, changed-file evidence, targeted tests, runtime evidence, and review; TPlan scout SubAgents may audit "
    "or score the packet, while code edits require an explicit write-capable runner"
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-") or "slice"


def _operation_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower()) or "operation"


def _target_test_stem(path: str) -> str:
    filename = str(path).strip().replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix in (
        ".contract.test.ts",
        ".scenario.test.ts",
        ".replay.test.ts",
        ".unit.test.ts",
        ".sql.test.ts",
        ".test.ts",
    ):
        if filename.endswith(suffix):
            filename = filename[: -len(suffix)]
            break
    return filename


def _target_operation_slug(path: str) -> str:
    return _operation_slug(_target_test_stem(path))


def _target_stem_words(path: str) -> set[str]:
    return {_operation_slug(part) for part in re.split(r"[^a-z0-9]+", _target_test_stem(path)) if part}


def _operation_words(operation_id: str) -> list[str]:
    return [
        word.lower()
        for word in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|[0-9]+", operation_id)
        if word
    ]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    selected: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        selected.append(normalized)
        seen.add(normalized)
    return selected


def _module_slug_for_operation(operation: dict[str, Any]) -> str:
    return _slug(str(operation.get("tag") or operation.get("operation_id") or operation.get("path") or "api"))


def _files_for_operation(operation: dict[str, Any], implementation_targets: list[str]) -> list[str]:
    module_slug = _module_slug_for_operation(operation)
    operation_id = str(operation.get("operation_id") or "").strip()
    selected = [
        target
        for target in implementation_targets
        if f"/{module_slug}/" in target or operation_id.lower() in target.lower()
    ]
    return _unique(selected)


def _tests_for_operation(operation: dict[str, Any], test_targets: dict[str, list[str]]) -> dict[str, list[str]]:
    operation_id = str(operation.get("operation_id") or "").strip()
    operation_slug = _operation_slug(operation_id)
    module_slug = _module_slug_for_operation(operation).replace("-", "")
    module_singular = module_slug[:-1] if module_slug.endswith("s") and len(module_slug) > 1 else module_slug
    operation_words = _operation_words(operation_id)
    operation_verb = operation_words[0] if operation_words else ""
    operation_nouns = {_operation_slug(word) for word in operation_words[1:]}
    allowed_alias_words = {word for word in {operation_verb, module_slug, module_singular} | operation_nouns if word}
    selected: dict[str, list[str]] = {"sql": [], "contract": [], "scenario": [], "replay": [], "unit": []}
    for family in selected:
        exact_matches: list[str] = []
        loose_matches: list[str] = []
        for target in test_targets.get(family, []):
            normalized = str(target).strip()
            target_slug = _target_operation_slug(normalized)
            target_words = _target_stem_words(normalized)
            exact_operation_match = bool(operation_slug and target_slug == operation_slug)
            exact_module_match = bool(
                (module_slug and target_slug == module_slug)
                or (module_singular and target_slug == module_singular)
            )
            target_names_module = bool(
                (module_slug and module_slug in target_words)
                or (module_singular and module_singular in target_words)
                or (module_singular and target_slug.endswith(module_singular))
            )
            loosely_matches_operation = bool(
                operation_verb
                and (operation_verb in target_words or target_slug.startswith(operation_verb))
                and target_names_module
                and target_words <= allowed_alias_words
            )
            if exact_operation_match:
                exact_matches.append(normalized)
            elif exact_module_match or loosely_matches_operation:
                loose_matches.append(normalized)
        selected[family].extend(exact_matches or loose_matches)
    return {family: _unique(values) for family, values in selected.items()}


def _source_refs_for_operation(source_rows: list[dict[str, Any]], *, source_type: str | None = None) -> list[str]:
    refs: list[str] = []
    for row in source_rows:
        source_id = str(row.get("source_id") or "").strip()
        row_source_type = str(row.get("source_type") or "").strip()
        if source_type and row_source_type != source_type:
            continue
        source_subject = str(row.get("source_subject") or "").strip()
        if source_id:
            refs.append(" | ".join(part for part in [source_id, row_source_type, source_subject] if part))
    return _unique(refs)


def _missing_tests_for_operation(operation: dict[str, Any], missing_test_targets: dict[str, list[str]]) -> list[str]:
    selected = _tests_for_operation(operation, missing_test_targets)
    return [target for values in selected.values() for target in values]


def _missing_contract_test_operation_ids(
    operations: list[dict[str, Any]], test_targets: dict[str, list[str]]
) -> list[str]:
    missing: list[str] = []
    for operation in operations:
        operation_id = str(operation.get("operation_id") or "").strip()
        operation_tests = _tests_for_operation(operation, test_targets)
        if not operation_tests.get("contract"):
            missing.append(operation_id or _http_surface(operation) or "unknown-operation")
    return _unique(missing)


def _http_surface(operation: dict[str, Any]) -> str:
    return f"{str(operation.get('method') or '').upper()} {str(operation.get('path') or '').strip()}".strip()


def _merge_tests(test_rows: list[dict[str, list[str]]]) -> dict[str, list[str]]:
    selected: dict[str, list[str]] = {"sql": [], "contract": [], "scenario": [], "replay": [], "unit": []}
    for row in test_rows:
        for family in selected:
            selected[family].extend(row.get(family, []))
    return {family: _unique(values) for family, values in selected.items()}


def _test_allowed_edit_files(operation_tests: dict[str, list[str]]) -> list[str]:
    return _unique(
        operation_tests.get("sql", [])
        + operation_tests.get("contract", [])
        + operation_tests.get("scenario", [])
        + operation_tests.get("replay", [])
        + operation_tests.get("unit", [])
    )


def _slice_targeted_tests(operation_tests: dict[str, list[str]]) -> list[str]:
    return _unique(
        operation_tests.get("sql", [])
        + operation_tests.get("contract", [])
        + operation_tests.get("scenario", [])
        + operation_tests.get("replay", [])
    )


def _quoted_targets(targets: list[str]) -> str:
    return " ".join(shlex.quote(str(target).strip()) for target in targets if str(target).strip())


def _slice_targeted_command(targets: list[str], *, packet_id: str, slice_slug: str) -> str:
    selected = _unique(targets)
    if not selected:
        return ""
    report_name = f"{_slug(packet_id)}-{_slug(slice_slug)}-targeted-tests.vitest.json"
    command = (
        "python3 scripts/run_vitest_targets_sequentially.py "
        '--workspace-root . --config vitest.config.ts '
        f'--report-path "$PHASE3_RUN_DIR/{report_name}"'
    )
    for target in selected:
        command = f"{command} --target {shlex.quote(target)}"
    return command


def _slice_unit_command(targets: list[str], *, packet_id: str, slice_slug: str) -> str:
    selected = _unique(targets)
    if not selected:
        return ""
    report_name = f"{_slug(packet_id)}-{_slug(slice_slug)}-unit-tests.vitest.json"
    return (
        f'pnpm exec vitest run --config vitest.config.ts --reporter=json --outputFile "$PHASE3_RUN_DIR/{report_name}" '
        + _quoted_targets(selected)
    ).strip()


def _group_operations_by_owned_files(
    operations: list[dict[str, Any]], implementation_targets: list[str]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], dict[str, Any]] = {}
    fallback_index = 0
    for operation in operations:
        owned_files = _files_for_operation(operation, implementation_targets)
        if owned_files:
            key = tuple(owned_files)
        else:
            fallback_index += 1
            key = (f"__missing_owned_files__:{fallback_index}",)
        row = grouped.setdefault(
            key,
            {
                "owned_files": owned_files,
                "operations": [],
                "module_slug": _module_slug_for_operation(operation),
            },
        )
        row["operations"].append(operation)
    return list(grouped.values())


def build_backend_subagent_slice_packets(worker_packet: dict[str, Any]) -> list[dict[str, Any]]:
    if str(worker_packet.get("lane") or "").strip() != "backend":
        return []
    operations = [row for row in worker_packet.get("contract_operations", []) if isinstance(row, dict)]
    implementation_targets = [str(item).strip() for item in worker_packet.get("implementation_targets", []) if str(item).strip()]
    test_targets = worker_packet.get("test_targets", {}) if isinstance(worker_packet.get("test_targets"), dict) else {}
    missing_test_targets = (
        worker_packet.get("missing_test_targets", {}) if isinstance(worker_packet.get("missing_test_targets"), dict) else {}
    )
    source_rows = [row for row in worker_packet.get("source_rows", []) if isinstance(row, dict)]
    packet_id = str(worker_packet.get("packet_id") or "backend").strip()

    slices: list[dict[str, Any]] = []
    for operation_group in _group_operations_by_owned_files(operations, implementation_targets):
        group_operations = [row for row in operation_group.get("operations", []) if isinstance(row, dict)]
        if not group_operations:
            continue
        operation_ids = _unique([str(operation.get("operation_id") or "").strip() for operation in group_operations])
        primary_operation_id = operation_ids[0] if operation_ids else ""
        operation_tests = _merge_tests([_tests_for_operation(operation, test_targets) for operation in group_operations])
        missing_contract_test_operation_ids = _missing_contract_test_operation_ids(group_operations, test_targets)
        missing_tests = _unique(
            [
                target
                for operation in group_operations
                for target in _missing_tests_for_operation(operation, missing_test_targets)
            ]
        )
        owned_files = _unique([str(item).strip() for item in operation_group.get("owned_files", []) if str(item).strip()])
        module_slug = str(operation_group.get("module_slug") or _module_slug_for_operation(group_operations[0])).strip()
        slice_slug = _operation_slug(primary_operation_id) if len(group_operations) == 1 else _slug(module_slug)
        blocking_reasons: list[str] = []
        if missing_tests:
            blocking_reasons.extend(f"missing_test_target:{target}" for target in missing_tests)
        if not owned_files:
            blocking_reasons.append("missing_owned_files")
        if missing_contract_test_operation_ids:
            blocking_reasons.extend(
                f"missing_contract_test:{operation_id}" for operation_id in missing_contract_test_operation_ids
            )
        status = "ready" if not blocking_reasons else "blocked"
        test_allowed_edit_files = _test_allowed_edit_files(operation_tests)
        targeted_tests = _slice_targeted_tests(operation_tests)
        unit_tests = operation_tests.get("unit", [])
        allowed_edit_files = _unique(owned_files + test_allowed_edit_files) if status == "ready" else []
        slices.append(
            {
                "slice_id": f"{packet_id}:{slice_slug}",
                "slice_kind": "backend-action-card-operation"
                if len(group_operations) == 1
                else "backend-action-card-module",
                "slice_status": status,
                "action_card_refs": _source_refs_for_operation(source_rows, source_type="action-card"),
                "source_refs": _source_refs_for_operation(source_rows),
                "operation_id": primary_operation_id,
                "operation_ids": operation_ids,
                "http_surface": _http_surface(group_operations[0]),
                "http_surfaces": _unique([_http_surface(operation) for operation in group_operations]),
                "subagent_entrypoint_hint": "wff-impl-backend",
                "current_subagent_permission": "read-only-audit",
                "write_execution_requirement": "requires-write-capable-runner",
                "owned_files": owned_files,
                "implementation_allowed_edit_files": owned_files,
                "test_allowed_edit_files": test_allowed_edit_files,
                "allowed_edit_files": allowed_edit_files,
                "forbidden_edit_patterns": [
                    "OpenAPI / shared contract files unless the slice explicitly returns upstream",
                    "migrations unless the Action Card owns schema change evidence",
                    "files outside allowed_edit_files",
                    "unrelated work-package or frontend files",
                ],
                "green_commands": {
                    "targeted_tests": targeted_tests,
                    "unit_tests": unit_tests,
                    "packet_command": _slice_targeted_command(
                        targeted_tests,
                        packet_id=packet_id,
                        slice_slug=slice_slug,
                    ),
                    "unit_command": _slice_unit_command(
                        unit_tests,
                        packet_id=packet_id,
                        slice_slug=slice_slug,
                    ),
                },
                "red_signal_rule": (
                    "Run the listed targeted tests before implementation when they already exist; if they are green, "
                    "preserve them as regression evidence for the slice."
                ),
                "done_criteria": [
                    "owned files implement the bound operation through controller/service/repository as needed",
                    "listed targeted tests are green for this slice",
                    "listed unit tests are green when service/domain logic is touched",
                    "no forbidden edit pattern is used",
                ],
                "subagent_return_contract": {
                    "required_fields": [
                        "slice_id",
                        "mode",
                        "commands_run",
                        "evidence_summary",
                        "blockers",
                        "claim_ceiling",
                    ],
                    "read_only_review_fields": [
                        "slice_id",
                        "review_score",
                        "findings",
                        "evidence_checked",
                        "blockers",
                        "claim_ceiling",
                    ],
                    "write_runner_return_fields": [
                        "slice_id",
                        "changed_files",
                        "commands_run",
                        "evidence_summary",
                        "blockers",
                        "claim_ceiling",
                    ],
                    "blocker_policy": "return blocked instead of broadening context or editing upstream truth",
                },
                "claim_ceiling": SLICE_PACKET_CLAIM_CEILING,
                "blocking_reasons": _unique(blocking_reasons),
            }
        )
    return slices


def mark_slice_file_conflicts(slices: list[dict[str, Any]]) -> dict[str, Any]:
    owners: dict[str, list[str]] = {}
    for slice_packet in slices:
        for file_path in slice_packet.get("owned_files", []):
            owners.setdefault(str(file_path), []).append(str(slice_packet.get("slice_id", "")))
    conflicts = {file_path: ids for file_path, ids in owners.items() if len(set(ids)) > 1}
    for slice_packet in slices:
        owned = {str(item) for item in slice_packet.get("owned_files", [])}
        if owned & set(conflicts):
            reasons = list(slice_packet.get("blocking_reasons", []))
            if "owned_file_conflict" not in reasons:
                reasons.append("owned_file_conflict")
            slice_packet["blocking_reasons"] = _unique(reasons)
            slice_packet["slice_status"] = "blocked"
    return {
        "conflict_count": len(conflicts),
        "conflicting_files": sorted(conflicts),
        "file_owners": {file_path: sorted(set(ids)) for file_path, ids in sorted(conflicts.items())},
    }
