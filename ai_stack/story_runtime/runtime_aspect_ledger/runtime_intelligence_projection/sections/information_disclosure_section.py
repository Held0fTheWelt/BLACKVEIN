"""Projection section builder for `information_disclosure`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_INFORMATION_DISCLOSURE_SECTION_PARAMS = ('disclosure_actual', 'disclosure_expected', 'disclosure_rec', 'disclosure_selected')


def build_information_disclosure_section(**values: Any) -> dict[str, Any]:
    """Return the information disclosure diagnostic section from normalized ledger records."""
    disclosure_actual = values['disclosure_actual']
    disclosure_expected = values['disclosure_expected']
    disclosure_rec = values['disclosure_rec']
    disclosure_selected = values['disclosure_selected']
    return {
                    "policy_present": bool(disclosure_expected.get("policy_present")),
                    "policy_enabled": bool(disclosure_expected.get("policy_enabled")),
                    "commit_impact": disclosure_expected.get("commit_impact"),
                    "require_structured_events": bool(
                        disclosure_expected.get("require_structured_events")
                    ),
                    "max_visible_units_per_turn": int(
                        disclosure_expected.get("max_visible_units_per_turn") or 0
                    ),
                    "selected_unit_ids": disclosure_selected.get("selected_unit_ids") or [],
                    "allowed_unit_ids": disclosure_selected.get("allowed_unit_ids") or [],
                    "withheld_unit_ids": disclosure_selected.get("withheld_unit_ids")
                    or disclosure_actual.get("withheld_unit_ids")
                    or [],
                    "forbidden_unit_ids": disclosure_selected.get("forbidden_unit_ids") or [],
                    "disclosure_mode": disclosure_selected.get("disclosure_mode"),
                    "structured_events_present": bool(
                        disclosure_actual.get("structured_events_present")
                    ),
                    "event_count": int(disclosure_actual.get("event_count") or 0),
                    "visible_unit_ids": disclosure_actual.get("visible_unit_ids") or [],
                    "budget_used": int(disclosure_actual.get("budget_used") or 0),
                    "contract_pass": disclosure_actual.get("contract_pass"),
                    "failure_codes": disclosure_actual.get("failure_codes")
                    or _record_reasons(disclosure_rec),
                    "failure_reason": disclosure_rec.get("failure_reason")
                    or (_record_reasons(disclosure_rec)[0] if _record_reasons(disclosure_rec) else None),
                    "status": disclosure_rec.get("status"),
                }

