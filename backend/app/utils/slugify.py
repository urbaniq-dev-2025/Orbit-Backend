from __future__ import annotations

import re


_slug_pattern = re.compile(r"[^a-z0-9]+")


def slugify(value: str, fallback: str = "workspace") -> str:
    """Convert a string to a URL-friendly slug.

    Args:
        value: Raw input string (e.g. workspace name).
        fallback: Value to use when the input results in an empty slug.

    Returns:
        Lowercase slug consisting of alphanumeric characters and hyphens.
    """

    if not value:
        return fallback
    slug = value.strip().lower()
    slug = _slug_pattern.sub("-", slug)
    slug = slug.strip("-")
    return slug or fallback




