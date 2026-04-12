"""Shared analytics date helpers — cycle-breaking leaf module."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse YYYY-MM-DD string to UTC datetime at start of day."""
    if not date_str or not date_str.strip():
        return None
    try:
        dt = datetime.strptime(date_str.strip()[:10], "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _date_to_end_of_day(date_dt: datetime) -> datetime:
    """Convert date to end of day (start of next day, exclusive)."""
    return (date_dt + timedelta(days=1)).replace(tzinfo=timezone.utc)
