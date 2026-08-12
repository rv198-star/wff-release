#!/usr/bin/env python3
"""Shared WFF Core consumer adapter for repository and install-pack runtimes.

Install packs vendor the accepted ``wff_core`` package under ``scripts/`` so
normal imports resolve through the existing scripts root. Repository checkouts
fall back to the explicitly temporary P2 compatibility adapter. Consumers use
only the public top-level WFF Core types and operations; descriptor JSON is
loaded as distribution metadata and converted into public descriptors here.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
from importlib import resources
import json
from pathlib import Path
import sys
from typing import Any, Iterable

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


_IMPORT_MODE = "packaged-core"
try:
    from wff_core import (
        CONTRACT_ID,
        CONTRACT_VERSION,
        EntryKind,
        ExtensionDescriptor,
        ExtensionKind,
        FailurePolicy,
        RouteRequest,
        RouteResolution,
        register_extension,
        resolve_route,
    )
except ModuleNotFoundError as exc:
    if exc.name != "wff_core":
        raise
    repository_core_source = SCRIPTS_ROOT.parent / "wff-core" / "src"
    if not (repository_core_source / "wff_core" / "__init__.py").is_file():
        raise ModuleNotFoundError("repository WFF Core source is unavailable") from exc
    normalized_core_source = str(repository_core_source)
    if normalized_core_source not in sys.path:
        sys.path.insert(0, normalized_core_source)
    _IMPORT_MODE = "repository-source-core"
    from wff_core import (  # type: ignore[no-redef]
        CONTRACT_ID,
        CONTRACT_VERSION,
        EntryKind,
        ExtensionDescriptor,
        ExtensionKind,
        FailurePolicy,
        RouteRequest,
        RouteResolution,
        register_extension,
        resolve_route,
    )


EXPECTED_CONTRACT_ID = "wff-core-contract"
EXPECTED_CONTRACT_VERSION = "1.0.0"
EXPECTED_P1_SEMANTIC_SHA256 = "22a93eb1d2fabdddd2cc24bcf001aff14c6593e0a9ce6434b8c2c7feed7b4d9e"
EXTERNAL_ENTRY_NAMES = frozenset({"using-wff", "wff-req-chat", "wff-req", "wff-x"})


class WFFCoreConsumerError(RuntimeError):
    """Raised when an installed WFF surface cannot consume Core safely."""


def _text(value: object, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise WFFCoreConsumerError(f"{label} must be non-empty")
    return result


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise WFFCoreConsumerError(f"{label} must be an array")
    result: list[str] = []
    for item in value:
        text = _text(item, label)
        if text not in result:
            result.append(text)
    return tuple(result)


def _descriptor_from_mapping(row: object) -> ExtensionDescriptor:
    if not isinstance(row, dict):
        raise WFFCoreConsumerError("Core descriptor row must be an object")
    try:
        descriptor = ExtensionDescriptor(
            extension_id=_text(row.get("extension_id"), "extension_id"),
            extension_kind=ExtensionKind(_text(row.get("extension_kind"), "extension_kind")),
            core_contract_range=_text(row.get("core_contract_range"), "core_contract_range"),
            route_keys=_string_tuple(row.get("route_keys", []), "route_keys"),
            phase_ids=_string_tuple(row.get("phase_ids", []), "phase_ids"),
            consumes_contracts=_string_tuple(row.get("consumes_contracts", []), "consumes_contracts"),
            produces_contracts=_string_tuple(row.get("produces_contracts", []), "produces_contracts"),
            compatibility_aliases=_string_tuple(row.get("compatibility_aliases", []), "compatibility_aliases"),
            truth_owner=_text(row.get("truth_owner"), "truth_owner"),
            failure_policy=FailurePolicy(_text(row.get("failure_policy"), "failure_policy")),
        )
    except (TypeError, ValueError) as exc:
        raise WFFCoreConsumerError(f"invalid Core descriptor: {exc}") from exc
    return register_extension(descriptor)


def _load_json_resource(filename: str) -> object:
    try:
        target = resources.files("wff_core").joinpath("contracts", filename)
        return json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise WFFCoreConsumerError(f"cannot load packaged Core resource {filename}: {exc}") from exc


@lru_cache(maxsize=1)
def core_contract_manifest() -> dict[str, Any]:
    payload = _load_json_resource("wff-core-contract.json")
    if not isinstance(payload, dict):
        raise WFFCoreConsumerError("packaged Core contract manifest must be an object")
    if payload.get("contract_id") != EXPECTED_CONTRACT_ID or CONTRACT_ID != EXPECTED_CONTRACT_ID:
        raise WFFCoreConsumerError("unexpected WFF Core contract identity")
    if payload.get("contract_version") != EXPECTED_CONTRACT_VERSION or CONTRACT_VERSION != EXPECTED_CONTRACT_VERSION:
        raise WFFCoreConsumerError("unexpected WFF Core contract version")
    if payload.get("p1_semantic_projection_sha256") != EXPECTED_P1_SEMANTIC_SHA256:
        raise WFFCoreConsumerError("packaged WFF Core semantic digest does not match accepted P1")
    return payload


@lru_cache(maxsize=1)
def current_descriptors() -> tuple[ExtensionDescriptor, ...]:
    core_contract_manifest()
    payload = _load_json_resource("current-capabilities.json")
    if not isinstance(payload, dict) or not isinstance(payload.get("descriptors"), list):
        raise WFFCoreConsumerError("packaged Core capability descriptors are invalid")
    descriptors = tuple(_descriptor_from_mapping(row) for row in payload["descriptors"])
    if len(descriptors) != 16 or len({item.extension_id for item in descriptors}) != 16:
        raise WFFCoreConsumerError("packaged Core must expose exactly sixteen current capability descriptors")
    return descriptors


def descriptor_by_id(extension_id: str) -> ExtensionDescriptor:
    identifier = _text(extension_id, "extension_id")
    matches = [item for item in current_descriptors() if item.extension_id == identifier]
    if len(matches) != 1:
        raise WFFCoreConsumerError(f"Core descriptor is missing or ambiguous: {identifier}")
    return matches[0]


def descriptor_by_alias(alias: str) -> ExtensionDescriptor | None:
    normalized = _text(alias, "alias")
    matches = [
        item
        for item in current_descriptors()
        if normalized in item.compatibility_aliases or normalized in item.route_keys
    ]
    if len(matches) > 1:
        raise WFFCoreConsumerError(f"Core compatibility alias is ambiguous: {normalized}")
    return matches[0] if matches else None


def require_capability_binding(
    extension_id: str,
    *,
    required_contracts: Iterable[str] = (),
    phase_id: str = "",
    route_key: str = "",
) -> ExtensionDescriptor:
    """Fail closed unless a capability declares the required Core contracts."""
    descriptor = descriptor_by_id(extension_id)
    required = {str(item).strip() for item in required_contracts if str(item).strip()}
    missing = sorted(required - set(descriptor.consumes_contracts))
    if missing:
        raise WFFCoreConsumerError(
            f"{extension_id} does not consume required Core contracts: {', '.join(missing)}"
        )
    if phase_id and phase_id not in descriptor.phase_ids:
        raise WFFCoreConsumerError(f"{extension_id} does not implement phase id {phase_id}")
    if route_key and route_key not in descriptor.route_keys:
        raise WFFCoreConsumerError(f"{extension_id} does not declare route key {route_key}")
    return descriptor


def _descriptor_route_key(descriptor: ExtensionDescriptor, requested_name: str) -> str:
    if requested_name in descriptor.route_keys:
        return requested_name
    if len(descriptor.route_keys) == 1:
        return descriptor.route_keys[0]
    phase_routes = [value for value in descriptor.route_keys if value.startswith("phase-")]
    if len(phase_routes) == 1:
        return phase_routes[0]
    raise WFFCoreConsumerError(
        f"Core compatibility alias does not resolve to one route key: {requested_name}"
    )


def resolve_supported_entry(name: str, *, request_id: str = "core-route") -> RouteResolution:
    normalized = _text(name, "entry name")
    descriptor = descriptor_by_alias(normalized)
    intent_key = _descriptor_route_key(descriptor, normalized) if descriptor is not None else normalized
    entry_kind = EntryKind.EXTERNAL if normalized in EXTERNAL_ENTRY_NAMES else EntryKind.CONTINUATION
    return resolve_route(
        RouteRequest(
            request_id=request_id,
            entry_kind=entry_kind,
            intent_key=intent_key,
        ),
        current_descriptors(),
    )


def capability_binding_report(
    extension_id: str,
    *,
    required_contracts: Iterable[str] = (),
    phase_id: str = "",
    route_key: str = "",
) -> dict[str, Any]:
    descriptor = require_capability_binding(
        extension_id,
        required_contracts=required_contracts,
        phase_id=phase_id,
        route_key=route_key,
    )
    return {
        "schema_version": "wff.core-consumer-binding.v1",
        "status": "core-contract-bound",
        "import_mode": _IMPORT_MODE,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "p1_semantic_projection_sha256": EXPECTED_P1_SEMANTIC_SHA256,
        "extension_id": descriptor.extension_id,
        "extension_kind": descriptor.extension_kind.value,
        "phase_ids": list(descriptor.phase_ids),
        "route_keys": list(descriptor.route_keys),
        "consumes_contracts": list(descriptor.consumes_contracts),
        "produces_contracts": list(descriptor.produces_contracts),
        "truth_owner": descriptor.truth_owner,
        "failure_policy": descriptor.failure_policy.value,
        "claim_ceiling": (
            "This binding proves packaged descriptor identity and declared Core contract consumption only. "
            "It does not prove semantic sufficiency, implementation correctness, validation acceptance, or release readiness."
        ),
    }


def runtime_snapshot() -> dict[str, Any]:
    descriptors = current_descriptors()
    aliases = sorted(
        {
            alias
            for descriptor in descriptors
            for alias in (*descriptor.route_keys, *descriptor.compatibility_aliases)
        }
    )
    return {
        "schema_version": "wff.core-runtime-snapshot.v1",
        "status": "packaged-core-resolved",
        "import_mode": _IMPORT_MODE,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "p1_semantic_projection_sha256": EXPECTED_P1_SEMANTIC_SHA256,
        "descriptor_count": len(descriptors),
        "alias_count": len(aliases),
        "external_entries": sorted(EXTERNAL_ENTRY_NAMES),
        "compatibility_resolution": "descriptor-route-keys-and-aliases",
        "claim_ceiling": (
            "Runtime resolution proves Core package availability and descriptor closure only; "
            "it does not prove any lifecycle artifact or release claim."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the packaged WFF Core consumer boundary")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("snapshot")
    route = subparsers.add_parser("route")
    route.add_argument("name")
    binding = subparsers.add_parser("binding")
    binding.add_argument("extension_id")
    binding.add_argument("--contract", action="append", default=[])
    binding.add_argument("--phase-id", default="")
    binding.add_argument("--route-key", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "snapshot":
            payload = runtime_snapshot()
        elif args.command == "route":
            payload = resolve_supported_entry(args.name).to_dict()
        else:
            payload = capability_binding_report(
                args.extension_id,
                required_contracts=args.contract,
                phase_id=args.phase_id,
                route_key=args.route_key,
            )
    except WFFCoreConsumerError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
