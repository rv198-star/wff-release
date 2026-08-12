"""Packaged contract and current-capability metadata loaders."""

from __future__ import annotations

from importlib import resources
import json
from typing import Any

from .errors import ManifestError
from .registry import ExtensionRegistry, descriptor_from_mapping


CONTRACT_ID = "wff-core-contract"
CONTRACT_VERSION = "1.0.0"
CONTRACT_RESOURCE = "wff-core-contract.json"
CAPABILITY_RESOURCE = "current-capabilities.json"
P1_SEMANTIC_PROJECTION_SHA256 = "22a93eb1d2fabdddd2cc24bcf001aff14c6593e0a9ce6434b8c2c7feed7b4d9e"
EXPECTED_COUNTS = {
    "contracts": 9,
    "public_types": 13,
    "public_operations": 9,
    "invariants": 24,
}


def _load_json_resource(filename: str) -> dict[str, Any]:
    try:
        payload = resources.files("wff_core.contracts").joinpath(filename).read_text(
            encoding="utf-8"
        )
    except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
        raise ManifestError(f"packaged WFF Core resource is unavailable: {filename}: {exc}") from exc
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"packaged WFF Core resource is invalid JSON: {filename}: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestError(f"packaged WFF Core resource must be an object: {filename}")
    return value


def load_contract_manifest() -> dict[str, Any]:
    manifest = _load_json_resource(CONTRACT_RESOURCE)
    if manifest.get("schema_version") != "wff.core-contract-manifest.v1":
        raise ManifestError("unsupported WFF Core contract manifest schema")
    if manifest.get("contract_id") != CONTRACT_ID:
        raise ManifestError("unexpected WFF Core contract identity")
    if manifest.get("contract_version") != CONTRACT_VERSION:
        raise ManifestError("unexpected WFF Core contract version")
    projection_digest = str(manifest.get("p1_semantic_projection_sha256") or "")
    if projection_digest != P1_SEMANTIC_PROJECTION_SHA256:
        raise ManifestError("WFF Core manifest is not bound to the accepted P1 semantic projection")
    if manifest.get("source_decision") != "#863":
        raise ManifestError("WFF Core manifest source decision is invalid")
    counts = manifest.get("counts")
    if not isinstance(counts, dict) or counts != EXPECTED_COUNTS:
        raise ManifestError("WFF Core contract manifest counts do not match 1.0.0")
    contracts = manifest.get("contracts")
    public_types = manifest.get("public_types")
    operations = manifest.get("public_operations")
    invariants = manifest.get("invariants")
    if not all(isinstance(value, list) for value in (contracts, public_types, operations, invariants)):
        raise ManifestError("WFF Core contract manifest collections are invalid")
    contract_ids = {str(item.get("id") or "") for item in contracts if isinstance(item, dict)}
    type_ids = {str(item.get("id") or "") for item in public_types if isinstance(item, dict)}
    operation_ids = {str(item.get("id") or "") for item in operations if isinstance(item, dict)}
    if len(contract_ids) != EXPECTED_COUNTS["contracts"]:
        raise ManifestError("WFF Core contract ids are missing or duplicated")
    if len(type_ids) != EXPECTED_COUNTS["public_types"]:
        raise ManifestError("WFF Core public type ids are missing or duplicated")
    if len(operation_ids) != EXPECTED_COUNTS["public_operations"]:
        raise ManifestError("WFF Core operation ids are missing or duplicated")
    for operation in operations:
        if not isinstance(operation, dict):
            raise ManifestError("WFF Core operation row is invalid")
        if operation.get("contract_id") not in contract_ids:
            raise ManifestError("WFF Core operation references an unknown contract")
        unknown_types = (
            set(operation.get("input_type_ids") or ())
            | set(operation.get("output_type_ids") or ())
        ) - type_ids
        if unknown_types:
            raise ManifestError(
                "WFF Core operation references unknown public types: "
                + ", ".join(sorted(unknown_types))
            )
    return manifest


def load_current_capability_descriptors() -> tuple[dict[str, Any], ...]:
    manifest = load_contract_manifest()
    payload = _load_json_resource(CAPABILITY_RESOURCE)
    if payload.get("schema_version") != "wff.core-current-capabilities.v1":
        raise ManifestError("unsupported current-capability descriptor schema")
    if payload.get("core_contract_version") != CONTRACT_VERSION:
        raise ManifestError("capability descriptor manifest targets the wrong Core version")
    rows = payload.get("descriptors")
    if payload.get("descriptor_count") != 16:
        raise ManifestError("current-capability manifest descriptor_count must be sixteen")
    if not isinstance(rows, list) or len(rows) != 16:
        raise ManifestError("current-capability manifest must contain sixteen descriptors")
    contract_ids = {row["id"] for row in manifest["contracts"]}
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            raise ManifestError("capability descriptor row must be an object")
        try:
            descriptor = descriptor_from_mapping(raw)
        except Exception as exc:
            raise ManifestError(f"invalid current capability descriptor: {exc}") from exc
        if descriptor.extension_id in seen:
            raise ManifestError(
                f"duplicate current capability descriptor: {descriptor.extension_id}"
            )
        seen.add(descriptor.extension_id)
        unknown = (
            set(descriptor.consumes_contracts) | set(descriptor.produces_contracts)
        ) - contract_ids
        if unknown:
            raise ManifestError(
                f"current capability {descriptor.extension_id} references unknown contracts: "
                + ", ".join(sorted(unknown))
            )
        result.append(descriptor.to_dict())
    return tuple(result)


def build_current_registry() -> ExtensionRegistry:
    manifest = load_contract_manifest()
    contract_ids = [row["id"] for row in manifest["contracts"]]
    registry = ExtensionRegistry(
        core_version=CONTRACT_VERSION,
        contract_ids=contract_ids,
    )
    for row in load_current_capability_descriptors():
        registry.register_mapping(row)
    return registry
