from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common.output_language import is_zh_output, localize_phase3_delivery_runbook
from phase3.review_support import write_text_file


def ensure_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return "preserved"
    path.write_text(content, encoding="utf-8")
    return "generated"


def yaml_field(document: str, key: str, default: str = "") -> str:
    match = re.search(rf"{re.escape(key)}:\s*\"([^\"]+)\"", document)
    return match.group(1).strip() if match else default


def build_runbook(
    *,
    case_name: str,
    version: str,
    tech_stack_text: str,
    wp_gate_report: dict[str, Any] | None,
    verification_ledger_report: dict[str, Any] | None,
    output_locale: str | None = None,
) -> str:
    preferred_vendor = yaml_field(tech_stack_text, "preferred_vendor_class", "real session-or-token auth boundary")
    auth_integration_mode = yaml_field(tech_stack_text, "integration_mode", "runtime-agnostic-real-auth")
    primary_db = yaml_field(tech_stack_text, "primary_database", "postgresql")
    queue_store = yaml_field(tech_stack_text, "queue_or_coordination_store", "redis")
    frontend_framework = yaml_field(tech_stack_text, "frontend_framework", "react-vite")
    backend_framework = yaml_field(tech_stack_text, "backend_framework", "node-http")
    passed_wp_count = int((wp_gate_report or {}).get("checks", {}).get("passed_work_package_count", 0) or 0)
    total_wp_count = int((wp_gate_report or {}).get("checks", {}).get("work_package_count", 0) or 0)
    passed_tests = int((verification_ledger_report or {}).get("summary", {}).get("aggregated_passed_test_count", 0) or 0)
    auth_precondition = (
        "- Provision external IdP / OIDC credentials and inject them through environment variables."
        if auth_integration_mode == "external-idp"
        else "- Provision signing/session secrets for the selected real auth boundary and verify tenant-scoped claim/session enforcement."
    )
    auth_smoke_check = (
        "- Verify auth redirect / session bootstrap succeeds."
        if auth_integration_mode == "external-idp"
        else "- Verify bearer/session authentication succeeds and tenant-scoped claims are accepted."
    )
    return localize_phase3_delivery_runbook(
        "\n".join(
            [
                "# Deploy Runbook",
                "",
                "## 1. Release Metadata",
                f"- case_name: {case_name}",
                f"- version: {version}",
                f"- backend_framework: {backend_framework}",
                f"- frontend_framework: {frontend_framework}",
                f"- auth_vendor_class: {preferred_vendor}",
                f"- primary_database: {primary_db}",
                f"- queue_or_coordination_store: {queue_store}",
                "",
                "## 2. Preconditions",
                auth_precondition,
                f"- Ensure {primary_db} and {queue_store} are reachable from the runtime environment.",
                "- For local compose validation, use `runtime-compose.env.example`; it uses container-internal service addresses and should not be confused with host-local developer env files.",
                f"- Confirm implementation gate is green for all work packages ({passed_wp_count}/{total_wp_count}).",
                f"- Confirm verification ledger remains green ({passed_tests} passed tests aggregated).",
                "",
                "## 3. Deploy Steps",
                "1. Build the workspace image from the repository root Dockerfile.",
                "2. Apply database migrations from `db/migrations/` before shifting traffic.",
                "3. For local compose validation, run `docker compose --env-file runtime-compose.env.example -f docker-compose.prod.yml up -d --build` from the release root.",
                "4. Start the API runtime with `pnpm --filter @app/api start:container` or the production compose template.",
                "5. Roll out the API and web services with the production compose template or the target platform equivalent.",
                "6. Run smoke checks against `/healthz`, `/readyz`, the final OpenAPI, and key scenario entrypoints.",
                "",
                "## 4. Smoke Checks",
                auth_smoke_check,
                "- Verify tenant-isolated scope detail and review-report reads succeed.",
                "- Verify audit log listing endpoint responds with the standard envelope.",
                "",
                "## 5. Rollback",
                "- Repoint traffic to the previous release image tag.",
                "- Revert the latest migration only if the migration is marked reversible for this release.",
                "- Disable async launch paths if queue-backed task orchestration exhibits contention.",
                "",
                "## 6. Observability",
                "- Monitor API error envelope rates by `error_code`.",
                "- Alert on cross-tenant denial spikes and task conflict retries.",
                "- Track observation run launch latency and review-report generation latency against the performance baseline.",
                "",
            ]
        ),
        output_locale,
    )


def build_runtime_compose_env_example(tech_stack_text: str) -> str:
    auth_integration_mode = yaml_field(tech_stack_text, "integration_mode", "runtime-agnostic-real-auth")
    auth_lines = (
        [
            "OIDC_ISSUER_URL=https://example-issuer",
            "OIDC_CLIENT_ID=phase3-local-client",
            "OIDC_CLIENT_SECRET=phase3-local-secret",
        ]
        if auth_integration_mode == "external-idp"
        else [
            "AUTH_TOKEN_SECRET=phase3-local-dev-secret",
        ]
    )
    auth_lines = [*auth_lines, "PHASE3_ALLOW_AUTH_CONTEXT_HEADER=false"]
    return "\n".join(
        [
            "POSTGRES_USER=postgres",
            "POSTGRES_PASSWORD=postgres",
            "POSTGRES_DB=app",
            "DATABASE_URL=postgresql://postgres:postgres@postgres:5432/app",
            "REDIS_URL=redis://redis:6379",
            *auth_lines,
            "PORT=3000",
            "HOST=0.0.0.0",
            "WEB_PORT=3100",
            "WEB_API_BASE_URL=http://api:3000",
            "VITE_API_BASE_URL=/api",
            "VITE_PHASE3_ALLOW_AUTH_CONTEXT_HEADER=false",
            "API_HOST_PORT=53000",
            "WEB_HOST_PORT=53100",
            "POSTGRES_HOST_PORT=55432",
            "REDIS_HOST_PORT=56379",
            "",
        ]
    )


def build_dockerfile() -> str:
    return "\n".join(
        [
            "FROM node:20-alpine AS builder",
            "WORKDIR /app",
            "RUN corepack enable",
            "",
            "COPY package.json pnpm-workspace.yaml .npmrc tsconfig.base.json ./",
            "COPY apps ./apps",
            "COPY packages ./packages",
            "COPY db ./db",
            "",
            "RUN pnpm install --frozen-lockfile=false",
            "RUN pnpm build",
            "",
            "FROM node:20-alpine AS runtime",
            "WORKDIR /app",
            "RUN addgroup -S nodeapp && adduser -S nodeapp -G nodeapp",
            "RUN corepack enable",
            "COPY --from=builder /app /app",
            "ENV CONTAINER_HEALTH_PORT=3000",
            "ENV CONTAINER_HEALTH_PATH=/healthz",
            "USER nodeapp",
            "EXPOSE 3000",
            "EXPOSE 3100",
            "HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 CMD wget -q -O - \"http://127.0.0.1:${CONTAINER_HEALTH_PORT}${CONTAINER_HEALTH_PATH}\" >/dev/null 2>&1 || exit 1",
            "CMD [\"pnpm\", \"--filter\", \"@app/api\", \"start:container\"]",
            "",
        ]
    )


def build_compose_prod(tech_stack_text: str) -> str:
    auth_integration_mode = yaml_field(tech_stack_text, "integration_mode", "runtime-agnostic-real-auth")
    auth_env_lines = (
        [
            "      OIDC_ISSUER_URL: ${OIDC_ISSUER_URL}",
            "      OIDC_CLIENT_ID: ${OIDC_CLIENT_ID}",
            "      OIDC_CLIENT_SECRET: ${OIDC_CLIENT_SECRET}",
        ]
        if auth_integration_mode == "external-idp"
        else [
            "      AUTH_TOKEN_SECRET: ${AUTH_TOKEN_SECRET:?AUTH_TOKEN_SECRET is required}",
        ]
    )
    auth_env_lines = [*auth_env_lines, "      PHASE3_ALLOW_AUTH_CONTEXT_HEADER: ${PHASE3_ALLOW_AUTH_CONTEXT_HEADER:-false}"]
    lines = [
        "services:",
        "  api:",
        "    build: .",
        "    command: [\"pnpm\", \"--filter\", \"@app/api\", \"start:container\"]",
        "    depends_on:",
        "      - postgres",
        "      - redis",
        "    environment:",
        "      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is required}",
        "      REDIS_URL: ${REDIS_URL:-redis://redis:6379}",
        "      PORT: ${PORT:-3000}",
        "      HOST: ${HOST:-0.0.0.0}",
        "      CONTAINER_HEALTH_PORT: ${PORT:-3000}",
        "      CONTAINER_HEALTH_PATH: /healthz",
        "    ports:",
        "      - \"${API_HOST_PORT:-53000}:3000\"",
        "    healthcheck:",
        "      test: [\"CMD-SHELL\", \"wget -q -O - http://127.0.0.1:3000/healthz >/dev/null 2>&1\"]",
        "      interval: 10s",
        "      timeout: 3s",
        "      retries: 5",
        "  postgres:",
        "    image: postgres:16",
        "    environment:",
        "      POSTGRES_USER: ${POSTGRES_USER:-postgres}",
        "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}",
        "      POSTGRES_DB: ${POSTGRES_DB:-app}",
        "    ports:",
        "      - \"127.0.0.1:${POSTGRES_HOST_PORT:-55432}:5432\"",
        "  redis:",
        "    image: redis:7",
        "    ports:",
        "      - \"127.0.0.1:${REDIS_HOST_PORT:-56379}:6379\"",
        "  web:",
        "    build: .",
        "    command: [\"pnpm\", \"--filter\", \"@app/web\", \"start\"]",
        "    depends_on:",
        "      - api",
        "    environment:",
        "      HOST: ${HOST:-0.0.0.0}",
        "      WEB_PORT: ${WEB_PORT:-3100}",
        "      WEB_API_BASE_URL: ${WEB_API_BASE_URL:-http://api:3000}",
        "      VITE_API_BASE_URL: ${VITE_API_BASE_URL:-/api}",
        "      CONTAINER_HEALTH_PORT: ${WEB_PORT:-3100}",
        "      CONTAINER_HEALTH_PATH: /",
        "    ports:",
        "      - \"${WEB_HOST_PORT:-53100}:3100\"",
        "    healthcheck:",
        "      test: [\"CMD-SHELL\", \"wget -q -O - http://127.0.0.1:3100/ >/dev/null 2>&1\"]",
        "      interval: 10s",
        "      timeout: 3s",
        "      retries: 5",
        "",
    ]
    api_env_insert_at = lines.index("      PORT: ${PORT:-3000}")
    lines[api_env_insert_at:api_env_insert_at] = auth_env_lines
    return "\n".join(lines)


def build_performance_baseline(
    *,
    wp_gate_report: dict[str, Any] | None,
    verification_ledger_report: dict[str, Any] | None,
    coverage_gate_report: dict[str, Any] | None = None,
    output_locale: str | None = None,
) -> dict[str, Any]:
    aggregated = (verification_ledger_report or {}).get("aggregated", {})
    verification_timing = aggregated.get("verification_timing", {}) if isinstance(aggregated, dict) else {}
    packet_timing = verification_timing.get("packet_duration_ms", {}) if isinstance(verification_timing, dict) else {}
    step_timing = verification_timing.get("step_duration_ms", {}) if isinstance(verification_timing, dict) else {}
    measured_from_verification_runs = int(packet_timing.get("sample_count", 0) or 0) > 0
    coverage_checks = coverage_gate_report.get("checks", {}) if isinstance(coverage_gate_report, dict) else {}
    coverage_collection_status = (
        str(coverage_gate_report.get("collection_status", "")).strip()
        if isinstance(coverage_gate_report, dict)
        else ""
    )
    return {
        "baseline_type": "verification-derived-pre-production-baseline" if measured_from_verification_runs else "pre-production-target",
        "measured_in_live_env": False,
        "measured_from_verification_runs": measured_from_verification_runs,
        "coverage_collection_status": coverage_collection_status or "not_collected_in_current_delivery_handoff",
        "notes": (
            [
                "该文件记录部署入口性能目标，以及当前 Phase-3 运行中可获得的验证派生耗时证据。",
                "验证派生耗时来自结构化 packet 运行，而不是生产实时遥测。",
                "在首个环境部署后，应以实测遥测替换这些目标值。",
                "当覆盖率产物已采集时，行覆盖率/分支覆盖率应以专门的覆盖率门禁为准。",
            ]
            if is_zh_output(output_locale)
            else [
                "This file captures deployment-entry performance targets plus any verification-derived timing evidence available in the current Phase-3 run.",
                "Verification-derived timings come from structured packet runs, not live production telemetry.",
                "Targets should be replaced with measured telemetry after the first environment deployment.",
                "Line/branch coverage should be read from the dedicated coverage gate when that artifact is collected.",
            ]
        ),
        "targets": {
            "api_p95_ms": 300,
            "api_p99_ms": 800,
            "queue_enqueue_p95_ms": 200,
            "error_rate_pct": 1.0,
        },
        "evidence": {
            "passed_work_packages": int((wp_gate_report or {}).get("checks", {}).get("passed_work_package_count", 0) or 0),
            "total_work_packages": int((wp_gate_report or {}).get("checks", {}).get("work_package_count", 0) or 0),
            "successful_packet_count": int((verification_ledger_report or {}).get("summary", {}).get("successful_packet_count", 0) or 0),
            "aggregated_passed_test_count": int((verification_ledger_report or {}).get("summary", {}).get("aggregated_passed_test_count", 0) or 0),
        },
        "coverage_metrics": {
            "lines_pct": float(coverage_checks.get("lines_pct", 0.0) or 0.0) if coverage_gate_report else 0.0,
            "functions_pct": float(coverage_checks.get("functions_pct", 0.0) or 0.0) if coverage_gate_report else 0.0,
            "branches_pct": float(coverage_checks.get("branches_pct", 0.0) or 0.0) if coverage_gate_report else 0.0,
            "statements_pct": float(coverage_checks.get("statements_pct", 0.0) or 0.0) if coverage_gate_report else 0.0,
        },
        "observed_verification_metrics": {
            "packet_duration_ms": packet_timing if isinstance(packet_timing, dict) else {},
            "step_duration_ms": step_timing if isinstance(step_timing, dict) else {},
        },
    }


def generate_phase3_delivery_handoff(
    *,
    output_dir: Path,
    case_name: str,
    version: str,
    tech_stack_text: str,
    wp_gate_report: dict[str, Any] | None = None,
    verification_ledger_report: dict[str, Any] | None = None,
    coverage_gate_report: dict[str, Any] | None = None,
    output_locale: str | None = None,
) -> dict[str, Any]:
    deploy_runbook_path = output_dir / "deploy-runbook.md"
    dockerfile_path = output_dir / "Dockerfile"
    compose_prod_path = output_dir / "docker-compose.prod.yml"
    runtime_env_example_path = output_dir / "runtime-compose.env.example"
    performance_baseline_path = output_dir / "performance-baseline.json"

    write_text_file(
        deploy_runbook_path,
        build_runbook(
            case_name=case_name,
            version=version,
            tech_stack_text=tech_stack_text,
            wp_gate_report=wp_gate_report,
            verification_ledger_report=verification_ledger_report,
            output_locale=output_locale,
        ),
    )
    dockerfile_write_mode = ensure_text(dockerfile_path, build_dockerfile())
    compose_prod_write_mode = ensure_text(compose_prod_path, build_compose_prod(tech_stack_text))
    runtime_env_example_write_mode = ensure_text(
        runtime_env_example_path,
        build_runtime_compose_env_example(tech_stack_text),
    )
    write_text_file(
        performance_baseline_path,
        json.dumps(
            build_performance_baseline(
                wp_gate_report=wp_gate_report,
                verification_ledger_report=verification_ledger_report,
                coverage_gate_report=coverage_gate_report,
                output_locale=output_locale,
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    return {
        "deploy_runbook_path": str(deploy_runbook_path),
        "dockerfile_path": str(dockerfile_path),
        "compose_prod_path": str(compose_prod_path),
        "runtime_env_example_path": str(runtime_env_example_path),
        "performance_baseline_path": str(performance_baseline_path),
        "dockerfile_write_mode": dockerfile_write_mode,
        "compose_prod_write_mode": compose_prod_write_mode,
        "runtime_env_example_write_mode": runtime_env_example_write_mode,
    }
