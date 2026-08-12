"""Declarative extension registry for the WFF Core contract.

The registry stores metadata only. It never imports, loads, starts, discovers,
or installs extension implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping, Sequence

from .errors import ContractValidationError, ExtensionRegistrationError
from .models import ExtensionDescriptor, ExtensionKind, FailurePolicy


_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_DESCRIPTOR_FIELDS = {
    "extension_id",
    "extension_kind",
    "core_contract_range",
    "route_keys",
    "phase_ids",
    "consumes_contracts",
    "produces_contracts",
    "compatibility_aliases",
    "truth_owner",
    "failure_policy",
}
_PROHIBITED_DESCRIPTOR_FIELDS = {
    "loader",
    "loader_hook",
    "module",
    "module_path",
    "entrypoint",
    "entry_point",
    "callback",
    "callbacks",
    "lifecycle_hook",
    "install",
    "installer",
    "package",
    "package_name",
    "discovery",
    "marketplace",
    "hot_reload",
}


def parse_version(value: str) -> tuple[int, int, int]:
    match = _VERSION.fullmatch(str(value).strip())
    if match is None:
        raise ContractValidationError("version must use MAJOR.MINOR.PATCH")
    return tuple(int(item) for item in match.groups())  # type: ignore[return-value]


def contract_range_supports(version_range: str, version: str) -> bool:
    """Evaluate the bounded range form accepted by ExtensionDescriptor."""
    current = parse_version(version)
    clauses = [item.strip() for item in str(version_range).split(",") if item.strip()]
    if not clauses or not clauses[0].startswith(">="):
        raise ContractValidationError("contract range must start with >=")
    minimum = parse_version(clauses[0][2:])
    if current < minimum:
        return False
    for clause in clauses[1:]:
        if not clause.startswith("<"):
            raise ContractValidationError("only an optional < upper bound is supported")
        if current >= parse_version(clause[1:]):
            return False
    return True


def _array_field(value: object, label: str) -> tuple[object, ...]:
    if not isinstance(value, (list, tuple)):
        raise ExtensionRegistrationError(f"{label} must be an array")
    return tuple(value)


def descriptor_from_mapping(value: Mapping[str, object]) -> ExtensionDescriptor:
    """Build one descriptor while rejecting executable/plugin fields and extras."""
    keys = set(value)
    prohibited = sorted(keys & _PROHIBITED_DESCRIPTOR_FIELDS)
    if prohibited:
        raise ExtensionRegistrationError(
            "extension descriptors may not contain executable loading fields: "
            + ", ".join(prohibited)
        )
    extra = sorted(keys - _DESCRIPTOR_FIELDS)
    missing = sorted(_DESCRIPTOR_FIELDS - keys)
    if extra or missing:
        raise ExtensionRegistrationError(
            f"extension descriptor field mismatch; missing={missing}, extra={extra}"
        )
    try:
        return ExtensionDescriptor(
            extension_id=str(value["extension_id"]),
            extension_kind=ExtensionKind(str(value["extension_kind"])),
            core_contract_range=str(value["core_contract_range"]),
            route_keys=_array_field(value["route_keys"], "route_keys"),
            phase_ids=_array_field(value["phase_ids"], "phase_ids"),
            consumes_contracts=_array_field(value["consumes_contracts"], "consumes_contracts"),
            produces_contracts=_array_field(value["produces_contracts"], "produces_contracts"),
            compatibility_aliases=_array_field(value["compatibility_aliases"], "compatibility_aliases"),
            truth_owner=str(value["truth_owner"]),
            failure_policy=FailurePolicy(str(value["failure_policy"])),
        )
    except (TypeError, ValueError, ContractValidationError) as exc:
        raise ExtensionRegistrationError(f"invalid extension descriptor: {exc}") from exc


@dataclass(frozen=True)
class RegistrySnapshot:
    core_version: str
    descriptors: tuple[ExtensionDescriptor, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "core_version": self.core_version,
            "descriptor_count": len(self.descriptors),
            "descriptors": [item.to_dict() for item in self.descriptors],
        }


class ExtensionRegistry:
    """In-memory, declarative descriptor registry.

    Storage and indexing are internal implementation details. The public
    contract is descriptor validation, fail-closed registration, and resolution
    through public operations.
    """

    def __init__(
        self,
        *,
        core_version: str = "1.0.0",
        contract_ids: Iterable[str] = (),
    ) -> None:
        parse_version(core_version)
        self.core_version = core_version
        self.contract_ids = frozenset(str(item).strip() for item in contract_ids if str(item).strip())
        self._descriptors: dict[str, ExtensionDescriptor] = {}
        self._route_index: dict[str, str] = {}
        self._phase_index: dict[str, str] = {}
        self._alias_index: dict[str, str] = {}

    def register(self, descriptor: ExtensionDescriptor) -> ExtensionDescriptor:
        if not isinstance(descriptor, ExtensionDescriptor):
            raise ExtensionRegistrationError("registry accepts ExtensionDescriptor values only")
        if not contract_range_supports(descriptor.core_contract_range, self.core_version):
            raise ExtensionRegistrationError(
                f"extension {descriptor.extension_id} does not support Core {self.core_version}"
            )
        if descriptor.extension_id in self._descriptors:
            raise ExtensionRegistrationError(
                f"duplicate extension_id: {descriptor.extension_id}"
            )
        if self.contract_ids:
            unknown = sorted(
                (set(descriptor.consumes_contracts) | set(descriptor.produces_contracts))
                - self.contract_ids
            )
            if unknown:
                raise ExtensionRegistrationError(
                    f"extension {descriptor.extension_id} references unknown Core contracts: "
                    + ", ".join(unknown)
                )
        route_collisions = sorted(
            value
            for value in descriptor.route_keys
            if value in self._route_index or value in self._alias_index
        )
        if route_collisions:
            raise ExtensionRegistrationError(
                f"extension {descriptor.extension_id} collides on route/alias key: "
                + ", ".join(route_collisions)
            )
        phase_collisions = sorted(
            value for value in descriptor.phase_ids if value in self._phase_index
        )
        if phase_collisions:
            raise ExtensionRegistrationError(
                f"extension {descriptor.extension_id} collides on phase id: "
                + ", ".join(phase_collisions)
            )
        alias_collisions = sorted(
            value
            for value in descriptor.compatibility_aliases
            if value in self._alias_index or value in self._route_index
        )
        if alias_collisions:
            raise ExtensionRegistrationError(
                f"extension {descriptor.extension_id} collides on route/alias key: "
                + ", ".join(alias_collisions)
            )
        self._descriptors[descriptor.extension_id] = descriptor
        for value in descriptor.route_keys:
            self._route_index[value] = descriptor.extension_id
        for value in descriptor.phase_ids:
            self._phase_index[value] = descriptor.extension_id
        for value in descriptor.compatibility_aliases:
            self._alias_index[value] = descriptor.extension_id
        return descriptor

    def register_mapping(self, value: Mapping[str, object]) -> ExtensionDescriptor:
        return self.register(descriptor_from_mapping(value))

    def register_many(
        self,
        descriptors: Sequence[ExtensionDescriptor] | Iterable[ExtensionDescriptor],
    ) -> RegistrySnapshot:
        for descriptor in descriptors:
            self.register(descriptor)
        return self.snapshot()

    def descriptor(self, extension_id: str) -> ExtensionDescriptor | None:
        return self._descriptors.get(str(extension_id).strip())

    def descriptor_for_route(self, route_key: str) -> ExtensionDescriptor | None:
        identifier = self._route_index.get(str(route_key).strip())
        return self._descriptors.get(identifier) if identifier else None

    def descriptor_for_phase(self, phase_id: str) -> ExtensionDescriptor | None:
        identifier = self._phase_index.get(str(phase_id).strip())
        return self._descriptors.get(identifier) if identifier else None

    def descriptor_for_alias(self, alias: str) -> ExtensionDescriptor | None:
        normalized = str(alias).strip()
        identifier = self._alias_index.get(normalized)
        if identifier is None:
            identifier = self._route_index.get(normalized)
        return self._descriptors.get(identifier) if identifier else None

    def snapshot(self) -> RegistrySnapshot:
        return RegistrySnapshot(
            core_version=self.core_version,
            descriptors=tuple(
                self._descriptors[identifier]
                for identifier in sorted(self._descriptors)
            ),
        )

    def __len__(self) -> int:
        return len(self._descriptors)
