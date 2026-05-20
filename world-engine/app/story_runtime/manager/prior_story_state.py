"""Prior story-state readers.

Extracts previous story-state surfaces that inform current turn execution and runtime truth reporting.
"""
from __future__ import annotations

from ._deps import *

def _beat_to_dramatic_signature(beat: BeatProgression | None) -> dict[str, str] | None:
    """Project a committed beat identity into the graph's prior_dramatic_signature kwarg.

    Values are short strings — the graph treats this as an opaque advisory
    signal, not a full continuity record. When no prior beat exists (first turn
    in a session) the return value is ``None`` so the graph keeps its existing
    first-turn behavior.
    """
    if beat is None:
        return None
    sig: dict[str, str] = {"prior_beat_id": beat.beat_id}
    if beat.pressure_state:
        sig["prior_pressure_state"] = beat.pressure_state
    if beat.pacing_carry_forward:
        sig["prior_pacing_mode"] = beat.pacing_carry_forward
    if beat.advancement_reason:
        sig["prior_beat_advancement_reason"] = beat.advancement_reason
    return sig

def _prior_beat_from_session(session: "StorySession") -> BeatProgression | None:
    """Read the most recent committed BeatProgression from the session's history.

    The commit resolver needs the prior beat to decide whether this turn
    carries continuity forward or advances the beat. History entries are
    ``committed_record`` dicts shaped by ``_finalize_committed_turn``; the
    beat lives on the embedded narrative_commit payload.
    """
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        beat_payload = commit.get("beat_progression")
        if not isinstance(beat_payload, dict):
            continue
        try:
            return BeatProgression.model_validate(beat_payload)
        except Exception:
            continue
    return None

def _prior_director_gathering_state_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest Phase-1 Director-Pause state from diagnostics."""
    for event in reversed(session.diagnostics or []):
        if not isinstance(event, dict):
            continue
        ps = event.get("observability_path_summary")
        ps = ps if isinstance(ps, dict) else {}
        state = ps.get("director_gathering_state")
        if isinstance(state, dict) and state:
            return dict(state)
        graph = event.get("graph_diagnostics")
        graph = graph if isinstance(graph, dict) else {}
        phase1 = graph.get("phase1_director_pause_diagnostics")
        phase1 = phase1 if isinstance(phase1, dict) else {}
        state = phase1.get("director_gathering_state")
        if isinstance(state, dict) and state:
            return dict(state)
    return None

def _prior_social_state_record_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed social-state record from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        summary = planner.get("social_state_summary")
        if not isinstance(summary, dict):
            continue
        record = summary.get("record")
        if isinstance(record, dict) and record:
            return dict(record)
        # Back-compat for any in-progress commit that stored the record fields
        # directly under social_state_summary before the nested "record" shape.
        if {"scene_pressure_state", "social_risk_band"} <= set(summary.keys()):
            return dict(summary)
    return None

def _prior_planner_truth_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest bounded planner-truth snapshot for graph rehydration."""
    allowed_keys = {
        "selected_scene_function",
        "responder_id",
        "primary_responder_id",
        "secondary_responder_ids",
        "responder_scope",
        "function_type",
        "pacing_mode",
        "silence_mode",
        "scene_energy_target",
        "scene_energy_transition",
        "scene_energy_validation",
        "scene_energy_level",
        "pacing_rhythm_state",
        "pacing_rhythm_target",
        "pacing_rhythm_validation",
        "temporal_control_state",
        "temporal_control_target",
        "temporal_control_validation",
        "sensory_context_state",
        "sensory_context_target",
        "sensory_context_validation",
        "genre_awareness_state",
        "genre_awareness_target",
        "genre_awareness_validation",
        "symbolic_object_resonance_state",
        "symbolic_object_resonance_target",
        "symbolic_object_resonance_validation",
        "social_pressure_state",
        "social_pressure_target",
        "social_pressure_validation",
        "expectation_variation_state",
        "expectation_variation_target",
        "expectation_variation_validation",
        "narrative_momentum_state",
        "narrative_momentum_target",
        "narrative_momentum_validation",
        "spoken_line_count",
        "action_line_count",
        "initiative_summary",
        "last_actor_outcome_summary",
        "scene_assessment_core",
        "social_outcome",
        "dramatic_direction",
        "social_state_summary",
        "continuity_impacts",
        "realized_secondary_responder_ids",
        "interruption_actor_id",
        "spoken_actor_summaries",
        "action_actor_summaries",
        "social_pressure_shift",
        "carry_forward_tension_notes",
        "initiative_seizer_id",
        "initiative_loser_id",
        "initiative_pressure_label",
        "npc_agency_simulation",
        "npc_long_horizon_state",
        "npc_private_plans",
        "npc_plan_conflict_resolution",
        "npc_agency_closure",
        "unresolved_npc_initiatives",
        "carried_forward_npc_initiatives",
    }
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        snapshot = {
            key: planner.get(key)
            for key in allowed_keys
            if planner.get(key) not in (None, "", [], {})
        }
        if snapshot:
            return snapshot
    return None

def _prior_pacing_rhythm_state_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed pacing-rhythm state from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        state = planner.get("pacing_rhythm_state")
        if isinstance(state, dict) and state:
            return dict(state)
    return None

def _prior_temporal_control_state_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed temporal-control state from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        state = planner.get("temporal_control_state")
        if isinstance(state, dict) and state:
            return dict(state)
    return None

def _prior_social_pressure_state_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed social-pressure metric from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        state = planner.get("social_pressure_state")
        if isinstance(state, dict) and state:
            return dict(state)
    return None

def _prior_relationship_state_record_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed relationship-state-machine record from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        state = planner.get("relationship_state_record")
        if isinstance(state, dict) and state:
            return dict(state)
    return None

def _prior_expectation_variation_state_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed expectation-variation state from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        state = planner.get("expectation_variation_state")
        if isinstance(state, dict) and state:
            return dict(state)
    return None

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
