"""Projection section builder for `relationship_state`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_RELATIONSHIP_STATE_SECTION_PARAMS = ('relationship_state_actual', 'relationship_state_expected', 'relationship_state_rec', 'relationship_state_selected')


def build_relationship_state_section(**values: Any) -> dict[str, Any]:
    relationship_state_actual = values['relationship_state_actual']
    relationship_state_expected = values['relationship_state_expected']
    relationship_state_rec = values['relationship_state_rec']
    relationship_state_selected = values['relationship_state_selected']
    return {
                    "schema_version": relationship_state_expected.get("schema_version")
                    or relationship_state_selected.get("schema_version")
                    or relationship_state_actual.get("schema_version"),
                    "policy_present": bool(relationship_state_expected.get("policy_present")),
                    "policy_enabled": bool(relationship_state_expected.get("policy_enabled")),
                    "target_axis_ids": relationship_state_selected.get("target_axis_ids")
                    or (
                        relationship_state_selected.get("target", {}).get("target_axis_ids")
                        if isinstance(relationship_state_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "target_relationship_ids": relationship_state_selected.get("target_relationship_ids")
                    or (
                        relationship_state_selected.get("target", {}).get("target_relationship_ids")
                        if isinstance(relationship_state_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "pressure_band": relationship_state_selected.get("pressure_band")
                    or (
                        relationship_state_selected.get("target", {}).get("pressure_band")
                        if isinstance(relationship_state_selected.get("target"), dict)
                        else None
                    ),
                    "requires_visible_relationship_beat": bool(
                        relationship_state_selected.get("requires_visible_relationship_beat")
                        or (
                            relationship_state_selected.get("target", {}).get("requires_visible_relationship_beat")
                            if isinstance(relationship_state_selected.get("target"), dict)
                            else False
                        )
                    ),
                    "pair_count": int(relationship_state_actual.get("pair_count") or 0),
                    "axis_count": int(relationship_state_actual.get("axis_count") or 0),
                    "transition_event_count": int(
                        relationship_state_actual.get("transition_event_count") or 0
                    ),
                    "contract_pass": relationship_state_actual.get("contract_pass"),
                    "failure_codes": relationship_state_actual.get("failure_codes")
                    or _record_reasons(relationship_state_rec),
                    "failure_reason": relationship_state_rec.get("failure_reason")
                    or (
                        _record_reasons(relationship_state_rec)[0]
                        if _record_reasons(relationship_state_rec)
                        else None
                    ),
                    "status": relationship_state_rec.get("status"),
                }

