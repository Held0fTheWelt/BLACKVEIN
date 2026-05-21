"""Projection section builder for `improvisational_coherence`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_IMPROVISATIONAL_COHERENCE_SECTION_PARAMS = ('improvisational_actual', 'improvisational_expected', 'improvisational_rec', 'improvisational_selected')


def build_improvisational_coherence_section(**values: Any) -> dict[str, Any]:
    """Return the improvisational coherence diagnostic section from normalized ledger records."""
    improvisational_actual = values['improvisational_actual']
    improvisational_expected = values['improvisational_expected']
    improvisational_rec = values['improvisational_rec']
    improvisational_selected = values['improvisational_selected']
    return {
                    "schema_version": improvisational_expected.get("schema_version")
                    or improvisational_selected.get("schema_version")
                    or improvisational_actual.get("schema_version"),
                    "policy_present": bool(improvisational_expected.get("policy_present")),
                    "policy_enabled": bool(improvisational_expected.get("policy_enabled")),
                    "commit_impact": improvisational_expected.get("commit_impact"),
                    "require_structured_events": bool(
                        improvisational_expected.get("require_structured_events")
                    ),
                    "contribution_id": improvisational_selected.get("contribution_id"),
                    "contribution_kind": improvisational_selected.get("contribution_kind"),
                    "acceptance_mode": improvisational_selected.get("acceptance_mode")
                    or improvisational_actual.get("acceptance_mode"),
                    "advance_class": improvisational_actual.get("advance_class"),
                    "selected_scene_function": improvisational_selected.get(
                        "selected_scene_function"
                    ),
                    "visible_actor_ids": improvisational_selected.get("visible_actor_ids") or [],
                    "required_anchor_refs": improvisational_selected.get("required_anchor_refs")
                    or [],
                    "min_anchor_refs": int(
                        improvisational_selected.get("min_anchor_refs")
                        or improvisational_expected.get("min_anchor_refs")
                        or 0
                    ),
                    "anchor_refs": improvisational_actual.get("anchor_refs") or [],
                    "anchor_sources": improvisational_actual.get("anchor_sources") or [],
                    "requires_playable_boundary_reason": bool(
                        improvisational_selected.get("requires_playable_boundary_reason")
                    ),
                    "boundary_reason_code": improvisational_actual.get("boundary_reason_code")
                    or improvisational_selected.get("boundary_reason_code"),
                    "structured_events_present": bool(
                        improvisational_actual.get("structured_events_present")
                    ),
                    "event_count": int(improvisational_actual.get("event_count") or 0),
                    "contribution_acknowledged": bool(
                        improvisational_actual.get("contribution_acknowledged")
                    ),
                    "contract_pass": improvisational_actual.get("contract_pass"),
                    "failure_codes": improvisational_actual.get("failure_codes")
                    or _record_reasons(improvisational_rec),
                    "failure_reason": improvisational_rec.get("failure_reason")
                    or (
                        _record_reasons(improvisational_rec)[0]
                        if _record_reasons(improvisational_rec)
                        else None
                    ),
                    "status": improvisational_rec.get("status"),
                }

