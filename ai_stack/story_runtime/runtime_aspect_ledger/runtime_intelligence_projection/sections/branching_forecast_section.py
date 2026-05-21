"""Projection section builder for `branching_forecast`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_BRANCHING_FORECAST_SECTION_PARAMS = ('branching_forecast',)


def build_branching_forecast_section(**values: Any) -> dict[str, Any]:
    branching_forecast = values['branching_forecast']
    return {
                    "schema_version": branching_forecast.get("schema_version"),
                    "status": branching_forecast.get("status"),
                    "source": branching_forecast.get("source"),
                    "forecast_only": bool(branching_forecast.get("forecast_only")),
                    "authoritative": bool(branching_forecast.get("authoritative")),
                    "inactive_branches_authoritative": bool(
                        branching_forecast.get("inactive_branches_authoritative")
                    ),
                    "mutates_canonical_state": bool(branching_forecast.get("mutates_canonical_state")),
                    "selection_required_to_commit": bool(
                        branching_forecast.get("selection_required_to_commit")
                    ),
                    "trigger_reasons": branching_forecast.get("trigger_reasons") or [],
                    "option_count": int(branching_forecast.get("option_count") or 0),
                    "options": branching_forecast.get("options") or [],
                    "path_signature": branching_forecast.get("path_signature"),
                    "dominant_thread_kind": branching_forecast.get("dominant_thread_kind"),
                    "thread_pressure_level": int(branching_forecast.get("thread_pressure_level") or 0),
                }

