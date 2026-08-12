"""Errors raised by the WFF Core structural contract implementation."""

from __future__ import annotations


class WFFCoreError(RuntimeError):
    """Base class for WFF Core failures."""


class ContractValidationError(WFFCoreError):
    """Raised when a public contract value is malformed or inconsistent."""


class ExtensionRegistrationError(WFFCoreError):
    """Raised when an extension descriptor cannot enter a registry snapshot."""


class ManifestError(WFFCoreError):
    """Raised when packaged contract or capability metadata cannot be trusted."""
