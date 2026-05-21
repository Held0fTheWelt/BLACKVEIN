"""Projection section builder for `expectation_variation`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_EXPECTATION_VARIATION_SECTION_PARAMS = ('expectation_variation_actual', 'expectation_variation_expected', 'expectation_variation_rec', 'expectation_variation_selected')


def build_expectation_variation_section(**values: Any) -> dict[str, Any]:
    expectation_variation_actual = values['expectation_variation_actual']
    expectation_variation_expected = values['expectation_variation_expected']
    expectation_variation_rec = values['expectation_variation_rec']
    expectation_variation_selected = values['expectation_variation_selected']
    return {
                    "schema_version": expectation_variation_expected.get("schema_version")
                    or expectation_variation_actual.get("schema_version"),
                    "policy_present": bool(expectation_variation_expected.get("policy_present")),
                    "policy_enabled": bool(expectation_variation_expected.get("policy_enabled")),
                    "commit_impact": expectation_variation_expected.get("commit_impact"),
                    "require_structured_events": bool(
                        expectation_variation_expected.get("require_structured_events")
                    ),
                    "max_variation_units_per_turn": int(
                        expectation_variation_expected.get("max_variation_units_per_turn")
                        or 0
                    ),
                    "cooldown_turns": int(
                        expectation_variation_expected.get("cooldown_turns") or 0
                    ),
                    "allowed_variation_types": expectation_variation_expected.get(
                        "allowed_variation_types"
                    )
                    or [],
                    "selected_variation_ids": expectation_variation_selected.get(
                        "selected_variation_ids"
                    )
                    or [],
                    "selected_variation_types": expectation_variation_selected.get(
                        "selected_variation_types"
                    )
                    or [],
                    "withheld_variation_ids": expectation_variation_selected.get(
                        "withheld_variation_ids"
                    )
                    or [],
                    "required_setup_refs": expectation_variation_selected.get(
                        "required_setup_refs"
                    )
                    or [],
                    "budget_remaining": int(
                        expectation_variation_selected.get("budget_remaining")
                        or expectation_variation_actual.get("budget_remaining")
                        or 0
                    ),
                    "structured_events_present": bool(
                        expectation_variation_actual.get("structured_events_present")
                    ),
                    "event_count": int(expectation_variation_actual.get("event_count") or 0),
                    "realized_variation_ids": expectation_variation_actual.get(
                        "realized_variation_ids"
                    )
                    or [],
                    "realized_variation_types": expectation_variation_actual.get(
                        "realized_variation_types"
                    )
                    or [],
                    "budget_used": int(expectation_variation_actual.get("budget_used") or 0),
                    "contract_pass": expectation_variation_actual.get("contract_pass"),
                    "failure_codes": expectation_variation_actual.get("failure_codes")
                    or _record_reasons(expectation_variation_rec),
                    "failure_reason": expectation_variation_rec.get("failure_reason")
                    or (
                        _record_reasons(expectation_variation_rec)[0]
                        if _record_reasons(expectation_variation_rec)
                        else None
                    ),
                    "status": expectation_variation_rec.get("status"),
                }

