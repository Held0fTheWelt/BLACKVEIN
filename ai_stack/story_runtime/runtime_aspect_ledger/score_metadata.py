"""Score metadata projection for aspect-ledger diagnostics.

Langfuse and governance views consume compact score metadata. This module keeps
that mapping separate from ledger mutation so scoring stays read-only.
"""

from __future__ import annotations

from typing import Any, Callable

from .normalization import get_aspect_record, normalize_runtime_aspect_ledger

def aspect_score_metadata(
    *,
    ledger: dict[str, Any] | None,
    aspect_name: str,
    score_name: str,
) -> dict[str, Any]:
    """Build required reason metadata for deterministic aspect scores."""
    normalized = (normalizer or normalize_runtime_aspect_ledger)(ledger)
    aspect = get_aspect_record(normalized, aspect_name)
    reasons = aspect.get("reasons") if isinstance(aspect.get("reasons"), list) else []
    actual = aspect.get("actual") if isinstance(aspect.get("actual"), dict) else {}
    selected = aspect.get("selected") if isinstance(aspect.get("selected"), dict) else {}
    target = selected.get("target") if isinstance(selected.get("target"), dict) else {}
    transition = selected.get("transition") if isinstance(selected.get("transition"), dict) else {}
    return {
        "score_name": score_name,
        "aspect_name": aspect_name,
        "session_id": normalized.get("session_id"),
        "trace_id": normalized.get("trace_id"),
        "turn_number": normalized.get("turn_number"),
        "status": aspect.get("status"),
        "failure_reason": aspect.get("failure_reason")
        or (reasons[0] if reasons else None),
        "offending_actor_id": aspect.get("offending_actor_id"),
        "offending_block_id": aspect.get("offending_block_id"),
        "missing_field": aspect.get("missing_field"),
        "expected_owner": aspect.get("expected_owner"),
        "actual_owner": aspect.get("actual_owner"),
        "selected_capability": aspect.get("selected_capability"),
        "realized_capability": aspect.get("realized_capability"),
        "selected_beat": aspect.get("selected_beat"),
        "lost_at_stage": aspect.get("lost_at_stage"),
        "planned_actor_ids": actual.get("planned_actor_ids"),
        "realized_actor_ids": actual.get("realized_actor_ids"),
        "missing_required_actor_ids": actual.get("missing_required_actor_ids"),
        "candidate_actor_ids": actual.get("candidate_actor_ids"),
        "independent_planning_used": actual.get("independent_planning_used"),
        "npc_agency_closure_status": actual.get("closure_status"),
        "scene_energy_level": selected.get("energy_level") or target.get("energy_level"),
        "scene_energy_transition": selected.get("target_transition")
        or transition.get("transition_intent"),
        "scene_energy_contract_pass": actual.get("contract_pass"),
        "scene_energy_failure_codes": actual.get("failure_codes"),
        "sensory_context_intensity": selected.get("intensity") or target.get("intensity"),
        "sensory_context_location_id": selected.get("location_id") or target.get("location_id"),
        "sensory_context_object_id": selected.get("object_id") or target.get("object_id"),
        "sensory_context_selected_layer_ids": selected.get("selected_layer_ids")
        or target.get("selected_layer_ids"),
        "sensory_context_realized_layer_ids": actual.get("realized_layer_ids"),
        "sensory_context_contract_pass": actual.get("contract_pass"),
        "sensory_context_failure_codes": actual.get("failure_codes"),
        "improvisational_coherence_contribution_id": selected.get("contribution_id"),
        "improvisational_coherence_contribution_kind": selected.get("contribution_kind"),
        "improvisational_coherence_acceptance_mode": selected.get("acceptance_mode")
        or actual.get("acceptance_mode"),
        "improvisational_coherence_advance_class": actual.get("advance_class"),
        "improvisational_coherence_acknowledged": actual.get("contribution_acknowledged"),
        "improvisational_coherence_contract_pass": actual.get("contract_pass"),
        "improvisational_coherence_failure_codes": actual.get("failure_codes"),
        "meta_narrative_awareness_active": selected.get("active"),
        "meta_narrative_awareness_tier": selected.get("awareness_tier"),
        "meta_narrative_awareness_intensity": selected.get("intensity"),
        "meta_narrative_awareness_trigger_frequency": selected.get("trigger_frequency"),
        "meta_narrative_awareness_selected_actor_ids": selected.get("selected_actor_ids"),
        "meta_narrative_awareness_direct_address_allowed": selected.get(
            "direct_player_address_allowed"
        ),
        "meta_narrative_awareness_cross_session_memory_allowed": selected.get(
            "cross_session_memory_allowed"
        ),
        "meta_narrative_awareness_selected_memory_ref_ids": selected.get(
            "selected_memory_ref_ids"
        ),
        "meta_narrative_awareness_adaptive_signal_codes": selected.get(
            "adaptive_signal_codes"
        ),
        "meta_narrative_awareness_event_count": actual.get("event_count"),
        "meta_narrative_awareness_direct_address_count": actual.get(
            "direct_address_count"
        ),
        "meta_narrative_awareness_realized_memory_ref_ids": actual.get(
            "realized_memory_ref_ids"
        ),
        "meta_narrative_awareness_contract_pass": actual.get("contract_pass"),
        "meta_narrative_awareness_failure_codes": actual.get("failure_codes"),
        "social_pressure_target_score": selected.get("target_score")
        or target.get("target_score"),
        "social_pressure_target_band": selected.get("target_band")
        or target.get("target_band"),
        "social_pressure_current_score": actual.get("current_score"),
        "social_pressure_current_band": actual.get("current_band"),
        "social_pressure_trend": selected.get("trend")
        or target.get("trend")
        or actual.get("trend"),
        "social_pressure_contract_pass": actual.get("contract_pass"),
        "social_pressure_failure_codes": actual.get("failure_codes"),
        "information_disclosure_selected_unit_ids": selected.get("selected_unit_ids"),
        "information_disclosure_visible_unit_ids": actual.get("visible_unit_ids"),
        "information_disclosure_contract_pass": actual.get("contract_pass"),
        "information_disclosure_failure_codes": actual.get("failure_codes"),
        "expectation_variation_selected_ids": selected.get("selected_variation_ids"),
        "expectation_variation_selected_types": selected.get("selected_variation_types"),
        "expectation_variation_realized_ids": actual.get("realized_variation_ids"),
        "expectation_variation_realized_types": actual.get("realized_variation_types"),
        "expectation_variation_budget_used": actual.get("budget_used"),
        "expectation_variation_contract_pass": actual.get("contract_pass"),
        "expectation_variation_failure_codes": actual.get("failure_codes"),
        "narrative_momentum_target_state": selected.get("target_state")
        or target.get("target_state"),
        "narrative_momentum_target_score": selected.get("target_score")
        or target.get("target_score"),
        "narrative_momentum_current_state": actual.get("current_state"),
        "narrative_momentum_current_score": actual.get("current_score"),
        "narrative_momentum_trend": actual.get("trend"),
        "narrative_momentum_velocity": actual.get("velocity"),
        "narrative_momentum_transition_allowed": actual.get("transition_allowed"),
        "narrative_momentum_progress_event_count": actual.get("progress_event_count"),
        "narrative_momentum_stall_budget_respected": actual.get("stall_budget_respected"),
        "narrative_momentum_contract_pass": actual.get("contract_pass"),
        "narrative_momentum_failure_codes": actual.get("failure_codes"),
        "genre_awareness_profile_id": selected.get("genre_profile_id")
        or target.get("genre_profile_id"),
        "genre_awareness_selected_registers": selected.get("selected_registers")
        or target.get("selected_registers"),
        "genre_awareness_required_conventions": selected.get("required_conventions")
        or target.get("required_conventions"),
        "genre_awareness_realized_profile_ids": actual.get("realized_profile_ids"),
        "genre_awareness_realized_registers": actual.get("realized_registers"),
        "genre_awareness_realized_conventions": actual.get("realized_conventions"),
        "genre_awareness_missing_required_conventions": actual.get(
            "missing_required_conventions"
        ),
        "genre_awareness_contract_pass": actual.get("contract_pass"),
        "genre_awareness_failure_codes": actual.get("failure_codes"),
        "consequence_cascade_selected_consequence_ids": selected.get("selected_consequence_ids"),
        "consequence_cascade_selected_edge_ids": selected.get("selected_edge_ids"),
        "consequence_cascade_selected_continuity_classes": selected.get(
            "selected_continuity_classes"
        ),
        "consequence_cascade_selected_statuses": selected.get("selected_statuses"),
        "consequence_cascade_atom_count": actual.get("atom_count"),
        "consequence_cascade_edge_count": actual.get("edge_count"),
        "consequence_cascade_contract_pass": actual.get("contract_pass"),
        "consequence_cascade_failure_codes": actual.get("failure_codes"),
        "dramatic_irony_selected_opportunity_ids": selected.get("selected_opportunity_ids"),
        "dramatic_irony_selected_fact_ids": selected.get("selected_fact_ids"),
        "dramatic_irony_realization_status": actual.get("realization_status"),
        "dramatic_irony_leak_blocked": actual.get("leak_blocked"),
        "dramatic_irony_violation_codes": actual.get("violation_codes"),
    }
