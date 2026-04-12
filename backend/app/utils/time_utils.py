"""Shared time utilities — leaf module, no app.* imports."""
from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC datetime (use as SQLAlchemy column default or in services)."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Return current UTC datetime as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


# Alias for callers using _utc_iso name
_utc_iso = utc_now_iso
