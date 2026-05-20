"""Kleine Hilfen für Inspector-Projektions-Sektionen (DS-018)."""

from __future__ import annotations

from typing import Any


def non_empty_dict(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)
