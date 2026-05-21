"""Projection section builder for `sensory_context`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_SENSORY_CONTEXT_SECTION_PARAMS = ('sensory_context_actual', 'sensory_context_expected', 'sensory_context_rec', 'sensory_context_selected')


def build_sensory_context_section(**values: Any) -> dict[str, Any]:
    """Return the sensory context diagnostic section from normalized ledger records."""
    sensory_context_actual = values['sensory_context_actual']
    sensory_context_expected = values['sensory_context_expected']
    sensory_context_rec = values['sensory_context_rec']
    sensory_context_selected = values['sensory_context_selected']
    return {
                    "schema_version": sensory_context_expected.get("schema_version")
                    or sensory_context_selected.get("schema_version")
                    or sensory_context_actual.get("schema_version"),
                    "policy_present": bool(sensory_context_expected.get("policy_present")),
                    "policy_enabled": bool(sensory_context_expected.get("policy_enabled")),
                    "intensity": _record_nested_value(
                        sensory_context_selected, "intensity", "target"
                    ),
                    "location_id": _record_nested_value(
                        sensory_context_selected, "location_id", "target"
                    ),
                    "object_id": _record_nested_value(
                        sensory_context_selected, "object_id", "target"
                    ),
                    "mood_key": _record_nested_value(
                        sensory_context_selected, "mood_key", "target"
                    ),
                    "selected_layer_ids": sensory_context_selected.get("selected_layer_ids")
                    or (
                        sensory_context_selected.get("target", {}).get("selected_layer_ids")
                        if isinstance(sensory_context_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "required_layer_ids": sensory_context_selected.get("required_layer_ids")
                    or (
                        sensory_context_selected.get("target", {}).get("required_layer_ids")
                        if isinstance(sensory_context_selected.get("target"), dict)
                        else []
                    )
                    or sensory_context_actual.get("required_layer_ids")
                    or [],
                    "event_count": int(sensory_context_actual.get("event_count") or 0),
                    "realized_layer_ids": sensory_context_actual.get("realized_layer_ids") or [],
                    "contract_pass": sensory_context_actual.get("contract_pass"),
                    "failure_codes": sensory_context_actual.get("failure_codes")
                    or _record_reasons(sensory_context_rec),
                    "failure_reason": sensory_context_rec.get("failure_reason")
                    or (
                        _record_reasons(sensory_context_rec)[0]
                        if _record_reasons(sensory_context_rec)
                        else None
                    ),
                    "status": sensory_context_rec.get("status"),
                }

