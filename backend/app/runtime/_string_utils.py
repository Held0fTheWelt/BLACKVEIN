"""Private runtime string helpers — leaf module."""
from __future__ import annotations


def _cap_str(s: str | None, max_len: int) -> str | None:
    """Cap string to max length with ellipsis suffix if truncated."""
    if s is None:
        return None
    t = str(s).strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"
