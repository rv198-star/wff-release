#!/usr/bin/env python3
"""Shared source-text normalization for Phase-1 authoring surfaces."""

from __future__ import annotations

import re


HANDOFF_NEXT_ACTION_SURFACE = "责任角色归属的下一步动作"


def normalize_source_handoff_phrases(value: object) -> str:
    """Compress generic handoff-control phrases into a reader-facing surface.

    Source packets may contain control shorthand such as "role-owned next
    action". It is useful as an elicitation hint, but generated artifacts should
    consume it as handoff semantics rather than repeat the process phrase.
    """

    text = str(value or "")
    replacements = (
        (r"\brole[-\s]+owned\s+next[-\s]+actions?\b", HANDOFF_NEXT_ACTION_SURFACE),
        (r"\bowner[-\s]+owned\s+next[-\s]+actions?\b", HANDOFF_NEXT_ACTION_SURFACE),
        (r"\bresponsibility[-\s]+owned\s+next[-\s]+actions?\b", HANDOFF_NEXT_ACTION_SURFACE),
        (r"\bnext[-\s]+action\s+ownership\b", "下一步动作责任归属"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text
