"""Runtime memory index projections for retrieval routing."""

from __future__ import annotations

from typing import Any


RUNTIME_MEMORY_INDEXES_SCHEMA_VERSION = "runtime_memory_indexes.v1"


def _list_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def build_runtime_memory_indexes_from_state(state: dict[str, Any]) -> dict[str, Any]:
    """Build bounded memory index projections from committed runtime state."""
    callback = state.get("prior_callback_web_state") if isinstance(state.get("prior_callback_web_state"), dict) else {}
    cascade = (
        state.get("prior_consequence_cascade_state")
        if isinstance(state.get("prior_consequence_cascade_state"), dict)
        else {}
    )
    social = state.get("prior_social_state_record") if isinstance(state.get("prior_social_state_record"), dict) else {}
    relationship = (
        state.get("prior_relationship_state_record")
        if isinstance(state.get("prior_relationship_state_record"), dict)
        else {}
    )
    planner_truth = state.get("prior_planner_truth") if isinstance(state.get("prior_planner_truth"), dict) else {}
    npc_sim = state.get("npc_agency_simulation") if isinstance(state.get("npc_agency_simulation"), dict) else {}
    scene_events = _list_rows(state.get("continuity_impacts"))[:20]
    beat_history = _list_rows(planner_truth.get("beat_history"))[:20]
    knowledge_boundary = _list_rows(state.get("dramatic_irony_record") if isinstance(state.get("dramatic_irony_record"), list) else [])
    return {
        "schema_version": RUNTIME_MEMORY_INDEXES_SCHEMA_VERSION,
        "source": "committed_runtime_projection",
        "scene_event_log_index": {
            "entries": scene_events,
            "count": len(scene_events),
        },
        "beat_history_index": {
            "entries": beat_history,
            "count": len(beat_history),
            "current_phase": planner_truth.get("beat_phase"),
        },
        "relationship_memory_index": {
            "relationship_axes": relationship.get("axis_states") if isinstance(relationship, dict) else {},
            "social_pressure_codes": social.get("relationship_pressure_codes") if isinstance(social, dict) else [],
        },
        "agent_private_memory_index": {
            "npc_private_plans": _list_rows(npc_sim.get("npc_private_plans")),
            "candidate_actor_ids": list(npc_sim.get("candidate_actor_ids") or [])[:16],
        },
        "knowledge_boundary_index": {
            "facts": knowledge_boundary,
            "known_by_actor_ids": list((state.get("dramatic_irony_record") or {}).get("known_by_actor_ids") or [])
            if isinstance(state.get("dramatic_irony_record"), dict)
            else [],
        },
        "callback_web_index": {
            "edges": _list_rows(callback.get("edges"))[:20],
            "selected_kind": callback.get("selected_callback_kind"),
        },
        "world_state_history_index": {
            "consequence_items": _list_rows(cascade.get("items"))[:20],
            "selected_ids": list(cascade.get("selected_consequence_ids") or [])[:20],
        },
    }

