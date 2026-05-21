"""Build semantic capability context from collected projection sources."""

from __future__ import annotations

from typing import Any

from ..projection_helpers import _first_text


def build_capability_context_sources(values: dict[str, Any]) -> dict[str, Any]:
    """Derive semantic capability-selection inputs from collected aspect evidence."""
    action_actual = values['action_actual']
    action_rec = values['action_rec']
    beat_rec = values['beat_rec']
    beat_selected = values['beat_selected']
    cap_actual = values['cap_actual']
    cap_expected = values['cap_expected']
    cap_selected = values['cap_selected']
    cascade_actual = values['cascade_actual']
    cascade_selected = values['cascade_selected']
    dramatic_irony_actual = values['dramatic_irony_actual']
    dramatic_irony_selected = values['dramatic_irony_selected']
    input_actual = values['input_actual']
    npc_agency_actual = values['npc_agency_actual']
    npc_agency_expected = values['npc_agency_expected']
    npc_agency_selected = values['npc_agency_selected']
    src = values['src']
    selected_beat_id = _first_text(
        [
            beat_selected.get("selected_beat_id"),
            beat_selected.get("selected_scene_function"),
            beat_rec.get("selected_beat"),
        ]
    )
    selected_capabilities = cap_selected.get("selected_capabilities")
    required_capabilities = cap_expected.get("required_capabilities")
    blocked_capabilities = cap_selected.get("blocked_capabilities") or cap_actual.get(
        "blocked_capabilities"
    )
    realized_capabilities = cap_actual.get("realized_capabilities")
    violated_capabilities = cap_actual.get("violated_capabilities") or cap_actual.get(
        "missing_required_capabilities"
    )
    npc_decision_required_signal = bool(
        npc_agency_expected.get("candidate_actor_ids")
        or npc_agency_selected.get("selected_private_plan_actor_ids")
        or npc_agency_actual.get("planned_actor_ids")
    )
    knowledge_gap_signal = bool(
        dramatic_irony_selected.get("selected_opportunity_ids")
        or dramatic_irony_selected.get("selected_fact_ids")
        or dramatic_irony_actual.get("opportunity_count")
        or dramatic_irony_actual.get("fact_count")
    )
    world_state_change_signal = bool(
        cascade_selected.get("selected_consequence_ids")
        or cascade_actual.get("event_count")
        or cascade_actual.get("consequence_count")
        or cascade_actual.get("committed_consequences")
    )
    raw_player_input_signal = (
        input_actual.get("raw_player_input")
        if "raw_player_input" in input_actual
        else src.get("raw_player_input")
    )
    capability_context = dict(
        turn_kind=src.get("turn_kind"),
        turn_number=src.get("turn_number"),
        raw_player_input=raw_player_input_signal,
        input_kind=input_actual.get("player_input_kind")
        or input_actual.get("input_kind")
        or action_actual.get("input_kind"),
        active_actor=src.get("active_actor"),
        npc_decision_required=npc_decision_required_signal or None,
        action_resolution_required=False if action_rec.get("applicable") is False else None,
        visible_projection_required=True,
        knowledge_gap_present=knowledge_gap_signal,
        world_state_change_requested=world_state_change_signal,
    )
    return {name: value for name, value in locals().items() if name != "values"}
