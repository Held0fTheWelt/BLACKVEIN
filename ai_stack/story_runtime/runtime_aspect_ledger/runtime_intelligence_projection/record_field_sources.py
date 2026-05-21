"""Collect expected, selected, and actual field maps from aspect records."""

from __future__ import annotations

from typing import Any

from ..projection_helpers import _record_block
from .record_field_catalog import RECORD_FIELD_NAMES


def collect_record_field_sources(values: dict[str, Any]) -> dict[str, Any]:
    return {
        output_name: _record_block(values[record_name], field_name)
        for output_name, record_name, field_name in RECORD_FIELD_NAMES
    }
