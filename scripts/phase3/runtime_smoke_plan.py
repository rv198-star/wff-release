from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse, urlunparse

from common.host_port_allocator import allocate_host_ports, host_port_in_use
from phase3.renderer_common import ascii_slug


def workspace_identity_slug(workspace_root: Path) -> str:
    resolved = str(workspace_root.resolve())
    digest = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:8]
    return f"{ascii_slug(workspace_root.name, fallback='phase3-runtime-smoke')}-{digest}"


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists() or not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def runtime_smoke_port_defaults(workspace_root: Path) -> dict[str, int]:
    defaults = {
        **parse_env_file(workspace_root / ".env.example"),
        **parse_env_file(workspace_root / ".env"),
    }
    resolved: dict[str, int] = {
        "WEB_HOST_PORT": 53100,
        "POSTGRES_HOST_PORT": 55432,
        "REDIS_HOST_PORT": 56379,
    }
    for key in tuple(resolved.keys()):
        raw = (
            os.environ.get(f"PHASE3_RUNTIME_SMOKE_{key}", "").strip()
            or os.environ.get(key, "").strip()
            or str(defaults.get(key, "")).strip()
        )
        if not raw:
            continue
        try:
            resolved[key] = int(raw)
        except ValueError:
            continue
    return resolved


def resolve_runtime_smoke_host_ports(
    *,
    workspace_root: Path,
    service_url: str,
    exclude_ports: set[int] | None = None,
    port_in_use_fn: Callable[[str, int], bool] = host_port_in_use,
) -> dict[str, int]:
    parsed = urlparse(service_url)
    defaults = runtime_smoke_port_defaults(workspace_root)
    return allocate_host_ports(
        requested_ports={
            "API_HOST_PORT": int(parsed.port or 3000),
            "WEB_HOST_PORT": defaults["WEB_HOST_PORT"],
            "POSTGRES_HOST_PORT": defaults["POSTGRES_HOST_PORT"],
            "REDIS_HOST_PORT": defaults["REDIS_HOST_PORT"],
        },
        exclude_ports=exclude_ports,
        port_in_use=port_in_use_fn,
    )


def normalize_runtime_smoke_service_url(service_url: str | None) -> str:
    value = str(service_url or "").strip()
    if not value or value.lower() in {"none", "null"}:
        return "http://127.0.0.1:3000"
    return value


def runtime_smoke_service_url(service_url: str, api_host_port: int) -> str:
    parsed = urlparse(normalize_runtime_smoke_service_url(service_url))
    scheme = parsed.scheme or "http"
    hostname = parsed.hostname or "127.0.0.1"
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname if api_host_port <= 0 else f"{hostname}:{api_host_port}"
    return urlunparse(parsed._replace(scheme=scheme, netloc=netloc))


def build_runtime_smoke_env(selected_host_ports: dict[str, int]) -> dict[str, str]:
    return {
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres",
        "POSTGRES_DB": "app",
        "DATABASE_URL": "postgresql://postgres:postgres@postgres:5432/app",
        "REDIS_URL": "redis://redis:6379",
        "OIDC_ISSUER_URL": "https://smoke.invalid/oidc",
        "OIDC_CLIENT_ID": "phase3-smoke-client",
        "OIDC_CLIENT_SECRET": "replace-me",
        "AUTH_TOKEN_SECRET": "replace-me",
        "PHASE3_ALLOW_AUTH_CONTEXT_HEADER": "false",
        "PORT": "3000",
        "HOST": "0.0.0.0",
        "WEB_PORT": "3100",
        "WEB_API_BASE_URL": "http://api:3000",
        "VITE_API_BASE_URL": "/api",
        "API_HOST_PORT": str(selected_host_ports["API_HOST_PORT"]),
        "WEB_HOST_PORT": str(selected_host_ports["WEB_HOST_PORT"]),
        "POSTGRES_HOST_PORT": str(selected_host_ports["POSTGRES_HOST_PORT"]),
        "REDIS_HOST_PORT": str(selected_host_ports["REDIS_HOST_PORT"]),
        "DOCKER_BUILDKIT": os.environ.get("DOCKER_BUILDKIT", "1") or "1",
        "COMPOSE_DOCKER_CLI_BUILD": os.environ.get("COMPOSE_DOCKER_CLI_BUILD", "1") or "1",
    }


def resolve_requested_runtime_smoke_service_url(explicit_service_url: str | None = None) -> str:
    explicit = (explicit_service_url or "").strip()
    if explicit:
        return explicit

    env_url = os.environ.get("PHASE3_RUNTIME_SMOKE_SERVICE_URL", "").strip()
    if env_url:
        return env_url

    for key in ("PHASE3_RUNTIME_SMOKE_API_HOST_PORT", "API_HOST_PORT"):
        raw = os.environ.get(key, "").strip()
        if not raw:
            continue
        try:
            port = int(raw)
        except ValueError:
            continue
        if 1 <= port <= 65535:
            return f"http://127.0.0.1:{port}"

    return "http://127.0.0.1:3000"


def build_runtime_smoke_plan(
    *,
    workspace_root: Path,
    service_url: str | None = None,
    exclude_ports: set[int] | None = None,
    port_in_use_fn: Callable[[str, int], bool] = host_port_in_use,
) -> dict[str, object]:
    workspace_root = workspace_root.resolve()
    workspace_slug = workspace_identity_slug(workspace_root)
    requested_service_url_input = (
        service_url if service_url is not None else resolve_requested_runtime_smoke_service_url()
    )
    requested_service_url = normalize_runtime_smoke_service_url(requested_service_url_input)
    selected_host_ports = resolve_runtime_smoke_host_ports(
        workspace_root=workspace_root,
        service_url=requested_service_url,
        exclude_ports=exclude_ports,
        port_in_use_fn=port_in_use_fn,
    )
    effective_service_url = runtime_smoke_service_url(requested_service_url, selected_host_ports["API_HOST_PORT"])
    runtime_env = build_runtime_smoke_env(selected_host_ports)
    return {
        "workspace_root": str(workspace_root),
        "workspace_slug": workspace_slug,
        "compose_project_name": f"phase3-smoke-{workspace_slug}",
        "requested_service_url_input": requested_service_url_input,
        "requested_service_url": requested_service_url,
        "service_url": effective_service_url,
        "selected_host_ports": selected_host_ports,
        "runtime_env": runtime_env,
    }
