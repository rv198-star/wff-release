from __future__ import annotations

import re
from pathlib import Path
from typing import Any


FAKE_RUNTIME_MARKERS = (
    "invokeOperation(",
    "resetGeneratedRuntime(",
    "runtime-test-kit",
    "generated-runtime",
    "generatedRuntime",
    "invoke_operation(",
)

SERVICE_TRANSPORT_PATTERNS = (
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\baxios\b"),
    re.compile(r"\bundici\b"),
    re.compile(r"\bsupertest\s*\("),
    re.compile(r"\brequest\s*\("),
    re.compile(r"\bcurl\s+"),
    re.compile(r"\bgrpc\b", re.IGNORECASE),
    re.compile(r"\bgraphql-request\b"),
    re.compile(r"\binvokeHttpOperation\s*\("),
)

SERVICE_TARGET_PATTERNS = (
    re.compile(r"https?://"),
    re.compile(r"\b(?:API|SERVICE|TEST)_BASE_URL\b"),
    re.compile(r"\b(?:API|SERVICE)_HOST\b"),
    re.compile(r"\bPORT\b"),
    re.compile(r"/healthz\b"),
    re.compile(r"/readyz\b"),
)

SERVICE_STARTUP_PATTERNS = (
    re.compile(r"\bspawn\s*\("),
    re.compile(r"\bexeca\s*\("),
    re.compile(r"\bexecFile\s*\("),
    re.compile(r"\bdocker compose\b"),
    re.compile(r"\bdocker-compose\b"),
    re.compile(r"\b(?:app|server)\.listen\s*\("),
    re.compile(r"\bstartServer\s*\("),
    re.compile(r"\blaunchServer\s*\("),
    re.compile(r"\bwaitFor(?:Health|Ready)\b"),
    re.compile(r"\bstartBackendRuntime\s*\("),
)

MIGRATION_PATTERNS = (
    re.compile(r"\brunMigrations\s*\("),
    re.compile(r"\binitializeDatabase\s*\("),
    re.compile(r"\brestoreScenario\s*\("),
    re.compile(r"\bapplyMigrations\s*\("),
    re.compile(r"\bresetDatabase\s*\("),
    re.compile(r"\bpnpm\s+(?:--filter\s+\S+\s+)?migrate\b"),
    re.compile(r"\bprisma migrate\b"),
    re.compile(r"\bdbmate\b"),
    re.compile(r"\bnode-pg-migrate\b"),
    re.compile(r"\bmigration\b", re.IGNORECASE),
)

SQL_QUERY_PATTERNS = (
    re.compile(r"\bDATABASE_URL\b"),
    re.compile(r"\bpg\b"),
    re.compile(r"\bpostgres(?:ql)?\b", re.IGNORECASE),
    re.compile(r"\.query\s*\("),
    re.compile(r"\bcollectPersistenceRoundTripEvidence\s*\("),
    re.compile(r"\bSELECT\b"),
    re.compile(r"\bINSERT\s+INTO\b"),
    re.compile(r"\bUPDATE\b"),
    re.compile(r"\bDELETE\s+FROM\b"),
    re.compile(r"\bqueryTableColumns\s*\("),
    re.compile(r"\bqueryTableIndexes\s*\("),
)

PERSISTENCE_PATH_HINTS = ("tests/sql/", "tests/persistence/", "tests/integration/", "tests/db/", "tests/database/")
SCHEMA_ONLY_PATH_HINTS = ("tests/schema/", ".schema.test.")
DB_SURFACE_MARKERS = (
    "database",
    "migrate",
    "migration",
    "postgres",
    "prisma",
    "drizzle",
    "typeorm",
    "sequelize",
    "repository",
    "/db/",
)


def flatten_packet_tests(packet_document: dict[str, Any], categories: tuple[str, ...]) -> list[str]:
    test_targets = packet_document.get("test_targets", {})
    if not isinstance(test_targets, dict):
        return []
    flattened: list[str] = []
    for key in categories:
        for item in test_targets.get(key, []):
            normalized = str(item).strip()
            if normalized:
                flattened.append(normalized)
    return sorted(set(flattened))


def normalize_test_target(value: str, *, workspace_root: Path) -> str:
    normalized = str(value).strip()
    if not normalized:
        return ""
    workspace_root_resolved = workspace_root.resolve()
    candidate = Path(normalized)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        try:
            return str(resolved.relative_to(workspace_root_resolved)).replace("\\", "/")
        except ValueError:
            return str(resolved).replace("\\", "/")
    return str(candidate).replace("\\", "/")


def path_text_if_exists(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def packet_lane(packet_document: dict[str, Any]) -> str:
    lane = str(packet_document.get("lane", "")).strip().lower()
    if lane:
        return lane
    packet_id_value = str(packet_document.get("packet_id", "")).strip().lower()
    if ":" in packet_id_value:
        return packet_id_value.rsplit(":", 1)[-1]
    return ""


def regex_matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def text_contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def workspace_requires_persistence_truth(*, packet_document: dict[str, Any], workspace_root: Path) -> bool:
    packet_targets = [
        str(item).strip().lower()
        for item in [
            *packet_document.get("implementation_targets", []),
            *packet_document.get("work_package_ids", []),
        ]
        if str(item).strip()
    ]
    packet_tests = [
        str(item).strip().lower()
        for item in flatten_packet_tests(packet_document, ("contract", "scenario", "replay", "unit"))
        if str(item).strip()
    ]
    commands = packet_document.get("verification_commands", {})
    command_values = []
    if isinstance(commands, dict):
        command_rows = commands.get("commands", {})
        if isinstance(command_rows, dict):
            command_values = [str(value).strip().lower() for value in command_rows.values() if str(value).strip()]

    if any(any(marker in target for marker in DB_SURFACE_MARKERS) for target in [*packet_targets, *packet_tests, *command_values]):
        return True

    db_artifact_candidates = (
        workspace_root / "apps" / "api" / "src" / "runtime" / "database.ts",
        workspace_root / "apps" / "api" / "src" / "runtime" / "migrate.ts",
        workspace_root / "db",
        workspace_root / "prisma",
        workspace_root / "migrations",
    )
    return any(candidate.exists() for candidate in db_artifact_candidates)


def analyze_backend_test_file(test_path: str, *, workspace_root: Path) -> dict[str, Any]:
    normalized_path = normalize_test_target(test_path, workspace_root=workspace_root)
    content = path_text_if_exists(workspace_root / normalized_path)
    lowered_path = normalized_path.lower()
    lowered_content = content.lower()
    fake_runtime = text_contains_any(content, FAKE_RUNTIME_MARKERS)
    transport_client = regex_matches_any(content, SERVICE_TRANSPORT_PATTERNS)
    transport_target = regex_matches_any(content, SERVICE_TARGET_PATTERNS)
    startup_signal = regex_matches_any(content, SERVICE_STARTUP_PATTERNS)
    migration_signal = regex_matches_any(content, MIGRATION_PATTERNS)
    sql_signal = regex_matches_any(content, SQL_QUERY_PATTERNS)
    persistence_path = any(hint in lowered_path for hint in PERSISTENCE_PATH_HINTS)
    schema_only = any(hint in lowered_path for hint in SCHEMA_ONLY_PATH_HINTS)
    harness_database_reset_signal = (
        content
        and "startBackendRuntime(" in content
        and any(token in content for token in ("initializeDatabase(", "restoreScenario(", "resetDatabase("))
    )
    service_boundary_truth = bool(
        content
        and not fake_runtime
        and transport_client
        and (transport_target or startup_signal)
    )
    sql_persistence_truth = bool(
        content
        and not fake_runtime
        and not schema_only
        and sql_signal
        and (persistence_path or migration_signal or "database_url" in lowered_content or ".query(" in lowered_content)
    )
    service_persistence_roundtrip_truth = bool(
        content
        and not fake_runtime
        and service_boundary_truth
        and sql_signal
    )
    migration_execution_truth = bool(
        content
        and not fake_runtime
        and migration_signal
        and (
            persistence_path
            or harness_database_reset_signal
            or "database_url" in lowered_content
            or "migrate" in lowered_path
        )
    )
    return {
        "test_path": normalized_path,
        "file_present": bool(content),
        "fake_runtime_detected": fake_runtime,
        "service_boundary_truth": service_boundary_truth,
        "sql_persistence_truth": sql_persistence_truth,
        "service_persistence_roundtrip_truth": service_persistence_roundtrip_truth,
        "migration_execution_truth": migration_execution_truth,
    }


def analyze_backend_evidence(
    *,
    packet_document: dict[str, Any],
    workspace_root: Path,
    targeted_test_report: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if packet_lane(packet_document) != "backend":
        return None

    requires_persistence_truth = workspace_requires_persistence_truth(
        packet_document=packet_document,
        workspace_root=workspace_root,
    )
    passed_targeted_tests = []
    if isinstance(targeted_test_report, dict):
        passed_targeted_tests = [
            normalize_test_target(str(item).strip(), workspace_root=workspace_root)
            for item in targeted_test_report.get("passed_tests", [])
            if normalize_test_target(str(item).strip(), workspace_root=workspace_root)
        ]
    analyzed_tests = [
        analyze_backend_test_file(test_path, workspace_root=workspace_root)
        for test_path in sorted(set(passed_targeted_tests))
    ]
    service_boundary_truth = any(row["service_boundary_truth"] for row in analyzed_tests)
    sql_persistence_truth = any(row["sql_persistence_truth"] for row in analyzed_tests)
    service_persistence_roundtrip_truth = any(row["service_persistence_roundtrip_truth"] for row in analyzed_tests)
    migration_execution_truth = any(row["migration_execution_truth"] for row in analyzed_tests)

    missing_truths: list[str] = []
    if not service_boundary_truth:
        missing_truths.append("service_boundary_truth")
    if requires_persistence_truth and not sql_persistence_truth:
        missing_truths.append("sql_persistence_truth")
    if requires_persistence_truth and not service_persistence_roundtrip_truth:
        missing_truths.append("service_persistence_roundtrip_truth")
    if requires_persistence_truth and not migration_execution_truth:
        missing_truths.append("migration_execution")

    return {
        "applicable": True,
        "requires_persistence_truth": requires_persistence_truth,
        "service_boundary_truth": service_boundary_truth,
        "sql_persistence_truth": sql_persistence_truth,
        "service_persistence_roundtrip_truth": service_persistence_roundtrip_truth,
        "migration_execution": migration_execution_truth,
        "passed_targeted_test_count": len(analyzed_tests),
        "analyzed_targeted_tests": analyzed_tests,
        "missing_truths": missing_truths,
    }
