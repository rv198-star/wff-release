#!/usr/bin/env python3
"""
Shared host-port allocation helpers for Phase-3 runtime flows.
"""

from __future__ import annotations

import socket
import subprocess
from collections.abc import Mapping
from typing import Callable


HostPortProbe = Callable[[str, int], bool]


def host_port_in_use(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
            except OSError:
                return True
        return False
    except PermissionError:
        pass
    try:
        completed = subprocess.run(
            ["ss", "-ltn"],
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception:
        return False
    if completed.returncode != 0:
        return False
    token = f":{port}"
    return any(token in line for line in completed.stdout.splitlines())


def choose_available_host_port(
    *,
    requested_port: int,
    exclude_ports: set[int] | None = None,
    host: str = "0.0.0.0",
    min_port: int = 1,
    max_port: int = 65535,
    fallback_port: int | None = None,
    port_in_use: HostPortProbe | None = None,
) -> int:
    normalized_min = max(1, int(min_port))
    normalized_max = min(65535, int(max_port))
    if normalized_min > normalized_max:
        normalized_min, normalized_max = normalized_max, normalized_min
    excluded = set(exclude_ports or set())
    probe = port_in_use or host_port_in_use

    try:
        start = int(requested_port)
    except (TypeError, ValueError):
        start = fallback_port if fallback_port is not None else normalized_min
    start = max(normalized_min, start)
    if start <= normalized_max:
        for candidate in range(start, normalized_max + 1):
            if candidate in excluded:
                continue
            if not probe(host, candidate):
                return candidate

    if fallback_port is not None:
        try:
            normalized_fallback = int(fallback_port)
        except (TypeError, ValueError):
            normalized_fallback = None
        if (
            normalized_fallback is not None
            and normalized_min <= normalized_fallback <= normalized_max
            and normalized_fallback not in excluded
            and not probe(host, normalized_fallback)
        ):
            return normalized_fallback

    return max(normalized_min, min(normalized_max, start))


def allocate_host_ports(
    *,
    requested_ports: Mapping[str, int],
    exclude_ports: set[int] | None = None,
    host: str = "0.0.0.0",
    min_port: int = 1,
    max_port: int = 65535,
    port_bounds: Mapping[str, tuple[int, int]] | None = None,
    fallback_ports: Mapping[str, int] | None = None,
    port_in_use: HostPortProbe | None = None,
) -> dict[str, int]:
    selected: dict[str, int] = {}
    reserved_ports = set(exclude_ports or set())
    for key, requested in requested_ports.items():
        bounds = port_bounds.get(key, (min_port, max_port)) if port_bounds else (min_port, max_port)
        selected[key] = choose_available_host_port(
            requested_port=requested,
            exclude_ports=reserved_ports,
            host=host,
            min_port=bounds[0],
            max_port=bounds[1],
            fallback_port=fallback_ports.get(key) if fallback_ports else None,
            port_in_use=port_in_use,
        )
        reserved_ports.add(selected[key])
    return selected
