"""Projection section builder for `meta_narrative_awareness`."""

from __future__ import annotations

from typing import Any

from ...projection_helpers import _record_reasons

BUILD_META_NARRATIVE_AWARENESS_SECTION_PARAMS = (
    "meta_narrative_actual",
    "meta_narrative_expected",
    "meta_narrative_rec",
    "meta_narrative_selected",
)


def build_meta_narrative_awareness_section(**values: Any) -> dict[str, Any]:
    meta_narrative_actual = values['meta_narrative_actual']
    meta_narrative_expected = values['meta_narrative_expected']
    meta_narrative_rec = values['meta_narrative_rec']
    meta_narrative_selected = values['meta_narrative_selected']
    reasons = _record_reasons(meta_narrative_rec)
    return {
        "schema_version": meta_narrative_expected.get("schema_version")
        or meta_narrative_selected.get("schema_version")
        or meta_narrative_actual.get("schema_version"),
        "policy_present": bool(meta_narrative_expected.get("policy_present")),
        "policy_enabled": bool(meta_narrative_expected.get("policy_enabled")),
        "opt_in_required": bool(meta_narrative_expected.get("opt_in_required")),
        "opt_in_enabled": bool(meta_narrative_selected.get("opt_in_enabled")),
        "active": bool(meta_narrative_selected.get("active")),
        "awareness_tier": meta_narrative_selected.get("awareness_tier"),
        "intensity": meta_narrative_selected.get("intensity"),
        "trigger_frequency": meta_narrative_selected.get("trigger_frequency"),
        "supported_actor_ids": meta_narrative_selected.get("supported_actor_ids") or [],
        "configured_actor_ids": meta_narrative_selected.get("configured_actor_ids") or [],
        "selected_actor_ids": meta_narrative_selected.get("selected_actor_ids") or [],
        "allowed_awareness_modes": meta_narrative_expected.get("allowed_awareness_modes") or [],
        "forbidden_awareness_modes": meta_narrative_expected.get("forbidden_awareness_modes") or [],
        "allowed_fourth_wall_levels": meta_narrative_expected.get("allowed_fourth_wall_levels") or [],
        "max_events_per_turn": int(meta_narrative_selected.get("max_events_per_turn") or 0),
        "max_direct_addresses_per_turn": int(
            meta_narrative_selected.get("max_direct_addresses_per_turn") or 0
        ),
        "direct_player_address_allowed": bool(
            meta_narrative_selected.get("direct_player_address_allowed")
        ),
        "narrator_negotiation_allowed": bool(
            meta_narrative_selected.get("narrator_negotiation_allowed")
        ),
        "cross_session_memory_allowed": bool(
            meta_narrative_selected.get("cross_session_memory_allowed")
        ),
        "selected_memory_ref_ids": meta_narrative_selected.get("selected_memory_ref_ids") or [],
        "adaptive_signal_codes": meta_narrative_selected.get("adaptive_signal_codes") or [],
        "structured_events_present": bool(meta_narrative_actual.get("structured_events_present")),
        "event_count": int(meta_narrative_actual.get("event_count") or 0),
        "realized_actor_ids": meta_narrative_actual.get("realized_actor_ids") or [],
        "awareness_modes": meta_narrative_actual.get("awareness_modes") or [],
        "fourth_wall_levels": meta_narrative_actual.get("fourth_wall_levels") or [],
        "direct_address_count": int(meta_narrative_actual.get("direct_address_count") or 0),
        "realized_memory_ref_ids": meta_narrative_actual.get("realized_memory_ref_ids") or [],
        "cross_session_memory_ref_count": int(
            meta_narrative_actual.get("cross_session_memory_ref_count") or 0
        ),
        "contract_pass": meta_narrative_actual.get("contract_pass"),
        "failure_codes": meta_narrative_actual.get("failure_codes") or reasons,
        "failure_reason": meta_narrative_rec.get("failure_reason") or (reasons[0] if reasons else None),
        "status": meta_narrative_rec.get("status"),
    }
