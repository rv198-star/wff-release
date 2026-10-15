"""Structural contract for Product Interaction Semantics authority.

This module owns only the shape and authority boundary introduced by Issue #1118.
It does not decide business truth, candidate vocabulary, UI widgets, page composition,
or whether any concrete P3 realization is the best product choice.
"""

from __future__ import annotations

from typing import Any, Mapping

from common.agentic_decision_authority import canonical_digest


PRODUCT_INTERACTION_SEMANTIC_FIELDS = (
    "user_meaning",
    "value_source",
    "cardinality",
    "editability",
    "candidate_source",
    "discovery_requirement",
    "context_carryover",
    "default_or_recent_semantics",
    "usage_frequency",
    "error_cost",
    "validation_semantics",
    "privacy_or_sensitivity",
    "free_form_allowed",
    "free_form_rationale",
    "truth_state",
    "unresolved_interaction_gaps",
)

FORBIDDEN_P2_PRESENTATION_AUTHORITY_FIELDS = frozenset(
    {
        "widget_type",
        "control_type",
        "react_component",
        "html_input_type",
        "use_multiselect",
        "interaction_pattern",
        "component_type",
    }
)


class ProductInteractionSemanticsContractError(ValueError):
    """Raised when Product Interaction Semantics crosses its authority boundary."""


def _find_forbidden_presentation_field(value: Any, *, path: str = "product_interaction_semantics") -> str | None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            key = str(raw_key).strip()
            if key in FORBIDDEN_P2_PRESENTATION_AUTHORITY_FIELDS:
                return f"{path}.{key}"
            found = _find_forbidden_presentation_field(nested, path=f"{path}.{key or '<empty>'}")
            if found:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = _find_forbidden_presentation_field(nested, path=f"{path}[{index}]")
            if found:
                return found
    return None


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_p2_product_interaction_semantics(semantics: Mapping[str, Any]) -> None:
    """Validate structure without deciding the semantic values themselves."""

    if not isinstance(semantics, Mapping):
        raise ProductInteractionSemanticsContractError("Product Interaction Semantics must be an object")

    forbidden_path = _find_forbidden_presentation_field(semantics)
    if forbidden_path:
        raise ProductInteractionSemanticsContractError(
            f"P2 Product Interaction Semantics contains forbidden presentation authority: {forbidden_path}"
        )

    missing = [field for field in PRODUCT_INTERACTION_SEMANTIC_FIELDS if field not in semantics]
    if missing:
        raise ProductInteractionSemanticsContractError(
            "Product Interaction Semantics missing required semantic fields: " + ", ".join(missing)
        )

    unexpected = sorted(set(semantics) - set(PRODUCT_INTERACTION_SEMANTIC_FIELDS))
    if unexpected:
        raise ProductInteractionSemanticsContractError(
            "Product Interaction Semantics contains unsupported top-level fields: " + ", ".join(unexpected)
        )

    text_fields = (
        "user_meaning",
        "value_source",
        "cardinality",
        "editability",
        "discovery_requirement",
        "context_carryover",
        "default_or_recent_semantics",
        "usage_frequency",
        "error_cost",
        "validation_semantics",
        "privacy_or_sensitivity",
        "free_form_rationale",
        "truth_state",
    )
    for field in text_fields:
        if not _non_empty_text(semantics.get(field)):
            raise ProductInteractionSemanticsContractError(
                f"Product Interaction Semantics requires non-empty semantic text: {field}"
            )

    candidate_source = semantics.get("candidate_source")
    if not (
        _non_empty_text(candidate_source)
        or isinstance(candidate_source, Mapping)
        or isinstance(candidate_source, list)
    ):
        raise ProductInteractionSemanticsContractError(
            "Product Interaction Semantics candidate_source must explicitly describe the accepted, absent, or unresolved candidate source"
        )

    if not isinstance(semantics.get("free_form_allowed"), bool):
        raise ProductInteractionSemanticsContractError(
            "Product Interaction Semantics free_form_allowed must be boolean"
        )

    gaps = semantics.get("unresolved_interaction_gaps")
    if not isinstance(gaps, list):
        raise ProductInteractionSemanticsContractError(
            "Product Interaction Semantics unresolved_interaction_gaps must be a list"
        )


def product_interaction_semantics_digest(semantics: Mapping[str, Any]) -> str:
    """Return a stable digest after structural boundary validation."""

    validate_p2_product_interaction_semantics(semantics)
    return canonical_digest(dict(semantics))


def validate_p3_realization_binding(
    semantics: Mapping[str, Any],
    realization: Mapping[str, Any],
) -> None:
    """Bind a P3 realization to frozen semantics without judging its UI choice.

    The realization may name any concrete control/component strategy. This function
    deliberately does not whitelist or map those choices; it only proves that P3 is
    consuming the same semantic packet without claiming to rewrite its authority.
    """

    validate_p2_product_interaction_semantics(semantics)
    if not isinstance(realization, Mapping):
        raise ProductInteractionSemanticsContractError("P3 realization binding must be an object")

    expected_digest = product_interaction_semantics_digest(semantics)
    if str(realization.get("semantic_contract_digest") or "").strip() != expected_digest:
        raise ProductInteractionSemanticsContractError("P3 realization semantic contract digest mismatch")

    if str(realization.get("authority_owner") or "").strip() != "P3 Agentic":
        raise ProductInteractionSemanticsContractError(
            "Concrete product realization must remain owned by P3 Agentic"
        )

    if realization.get("semantic_authority") is not False:
        raise ProductInteractionSemanticsContractError(
            "P3 realization binding must remain non-authoritative for P2 semantic truth"
        )

    for field in ("control_choice", "rationale"):
        if not _non_empty_text(realization.get(field)):
            raise ProductInteractionSemanticsContractError(
                f"P3 realization binding requires non-empty {field}"
            )
