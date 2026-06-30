from __future__ import annotations

from phase3.backend_module_renderer import stable_slug
from phase3.renderer_common import unicode_slug


def sanitize_route_segment(route_value: str, fallback_surface: str) -> str:
    candidates = [part for part in str(route_value).split("/") if part.strip()]
    normalized = [unicode_slug(part, fallback="surface") for part in candidates]
    if normalized:
        return "/".join(normalized)
    return unicode_slug(fallback_surface, fallback="surface")


def frontend_route_file_segment(route_segment: str) -> str:
    parts = [part for part in str(route_segment or "").split("/") if part.strip()]
    normalized: list[str] = []
    for index, part in enumerate(parts, start=1):
        ascii_part = stable_slug(part, fallback="")
        if any(ord(char) > 127 for char in part):
            tokens: list[str] = []
            buffer = ""
            for char in part:
                if char.isascii() and char.isalnum():
                    buffer += char.lower()
                    continue
                if buffer:
                    tokens.append(buffer)
                    buffer = ""
                if char.isalnum():
                    tokens.append(f"u{ord(char):04x}")
            if buffer:
                tokens.append(buffer)
            ascii_part = stable_slug("-".join(tokens), fallback="")
        normalized.append(ascii_part or f"route-{index}")
    return "/".join(normalized) or "surface"


def route_slug(surface: str) -> str:
    return stable_slug(surface, fallback="surface")
