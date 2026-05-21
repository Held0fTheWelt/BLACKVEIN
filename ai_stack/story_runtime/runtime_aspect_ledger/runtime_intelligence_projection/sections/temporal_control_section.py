"""Projection section builder for `temporal_control`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_TEMPORAL_CONTROL_SECTION_PARAMS = ('temporal_control_actual', 'temporal_control_expected', 'temporal_control_rec', 'temporal_control_selected')


def build_temporal_control_section(**values: Any) -> dict[str, Any]:
    """Return the temporal control diagnostic section from normalized ledger records."""
    temporal_control_actual = values['temporal_control_actual']
    temporal_control_expected = values['temporal_control_expected']
    temporal_control_rec = values['temporal_control_rec']
    temporal_control_selected = values['temporal_control_selected']
    return {
                    "schema_version": temporal_control_expected.get("schema_version")
                    or temporal_control_selected.get("schema_version")
                    or temporal_control_actual.get("schema_version"),
                    "policy_present": bool(temporal_control_expected.get("policy_present")),
                    "policy_enabled": bool(temporal_control_expected.get("policy_enabled")),
                    "commit_impact": temporal_control_expected.get("commit_impact"),
                    "require_structured_events": bool(
                        temporal_control_expected.get("require_structured_events")
                    ),
                    "allowed_operations": temporal_control_expected.get("allowed_operations")
                    or [],
                    "operation": temporal_control_selected.get("operation")
                    or _record_nested_value(temporal_control_selected, "operation", "target")
                    or temporal_control_actual.get("operation"),
                    "anchor_turn_id": temporal_control_selected.get("anchor_turn_id")
                    or _record_nested_value(temporal_control_selected, "anchor_turn_id", "target"),
                    "anchor_turn_number": temporal_control_selected.get("anchor_turn_number")
                    or _record_nested_value(
                        temporal_control_selected, "anchor_turn_number", "target"
                    ),
                    "recalled_turn_ids": temporal_control_selected.get("recalled_turn_ids")
                    or (
                        temporal_control_selected.get("target", {}).get("recalled_turn_ids")
                        if isinstance(temporal_control_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "recalled_consequence_ids": temporal_control_selected.get(
                        "recalled_consequence_ids"
                    )
                    or (
                        temporal_control_selected.get("target", {}).get(
                            "recalled_consequence_ids"
                        )
                        if isinstance(temporal_control_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "max_recalled_turns": int(
                        temporal_control_expected.get("max_recalled_turns") or 0
                    ),
                    "max_elapsed_turns": int(
                        temporal_control_expected.get("max_elapsed_turns") or 0
                    ),
                    "elapsed_turns": int(
                        temporal_control_actual.get("elapsed_turns")
                        or temporal_control_selected.get("elapsed_turns")
                        or (
                            temporal_control_selected.get("state", {}).get("elapsed_turns")
                            if isinstance(temporal_control_selected.get("state"), dict)
                            else 0
                        )
                        or 0
                    ),
                    "structured_events_present": bool(
                        temporal_control_actual.get("structured_events_present")
                    ),
                    "event_count": int(temporal_control_actual.get("event_count") or 0),
                    "realized_operations": temporal_control_actual.get(
                        "realized_operations"
                    )
                    or [],
                    "realized_turn_ids": temporal_control_actual.get("realized_turn_ids")
                    or [],
                    "realized_consequence_ids": temporal_control_actual.get(
                        "realized_consequence_ids"
                    )
                    or [],
                    "contract_pass": temporal_control_actual.get("contract_pass"),
                    "failure_codes": temporal_control_actual.get("failure_codes")
                    or _record_reasons(temporal_control_rec),
                    "failure_reason": temporal_control_rec.get("failure_reason")
                    or (
                        _record_reasons(temporal_control_rec)[0]
                        if _record_reasons(temporal_control_rec)
                        else None
                    ),
                    "status": temporal_control_rec.get("status"),
                }

