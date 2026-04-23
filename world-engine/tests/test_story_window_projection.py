from __future__ import annotations

from app.story_runtime.manager import StorySession, _story_window_entries_for_session


def test_story_window_projection_uses_committed_opening_and_player_turn() -> None:
    session = StorySession(
        session_id="story-1",
        module_id="god_of_carnage",
        runtime_projection={"start_scene_id": "scene_1"},
        current_scene_id="scene_1",
    )
    session.diagnostics = [
        {
            "turn_number": 0,
            "turn_kind": "opening",
            "raw_input": "internal opening prompt hidden from players",
            "visible_output_bundle": {"gm_narration": ["The room is already tense."]},
            "narrative_commit": {"committed_consequences": ["opening_committed"]},
            "committed_turn_authority": {
                "authority_record_version": "committed_turn_authority.v1",
                "committed_scene_id": "scene_1",
                "validation_status": "approved",
                "commit_applied": True,
            },
            "runtime_governance_surface": {"governed_runtime_active": True},
        },
        {
            "turn_number": 1,
            "turn_kind": "player",
            "raw_input": "I say that is enough.",
            "visible_output_bundle": {
                "gm_narration": ["The answer lands hard."],
                "spoken_lines": ["Annette: Enough?"],
                "action_lines": ["Annette folds her arms and leans over the table."],
                "render_support": {
                    "projection_version": "director_surface_hints.v1",
                    "player_visible": False,
                    "director_surface_hints": [{"hint_type": "phase_context", "text": "Debate is open."}],
                },
            },
            "narrative_commit": {"committed_consequences": ["tension_escalates"]},
            "dramatic_context_summary": {
                "contract": "bounded_dramatic_context.v1",
                "selected_scene_function": "escalate_conflict",
                "function_type": "pressure_probe",
                "responder": {"responder_id": "annette_reille"},
                "pacing": {"pacing_mode": "compressed"},
                "scene_assessment": {"pressure_state": "high_blame"},
                "social_state": {"social_risk_band": "high"},
                "dramatic_outcome": {
                    "social_outcome": "tension_escalates",
                    "dramatic_direction": "humiliation_spikes",
                    "continuity_classes": ["blame_pressure"],
                },
                "beat": {"beat_id": "scene_1:escalate_conflict"},
                "narrative_threads": {"thread_pressure_level": 3},
            },
            "committed_turn_authority": {
                "authority_record_version": "committed_turn_authority.v1",
                "committed_scene_id": "scene_1",
                "validation_status": "approved",
                "commit_applied": True,
            },
            "runtime_governance_surface": {"governed_runtime_active": True, "fallback_stage_reached": "primary_only"},
            "selected_scene_function": "escalate_conflict",
            "visibility_class_markers": ["truth_aligned"],
        },
    ]

    entries = _story_window_entries_for_session(session)

    assert [entry["role"] for entry in entries] == ["runtime", "player", "runtime"]
    assert entries[0]["kind"] == "opening"
    assert entries[0]["text"] == "The room is already tense."
    assert "internal opening prompt" not in entries[0]["text"]
    assert entries[1]["text"] == "I say that is enough."
    assert entries[2]["text"] == "The answer lands hard."
    assert entries[2]["spoken_lines"] == ["Annette: Enough?"]
    assert entries[2]["action_lines"] == ["Annette folds her arms and leans over the table."]
    assert entries[2]["committed_consequences"] == ["tension_escalates"]
    assert entries[2]["responder_id"] == "annette_reille"
    assert entries[2]["quality_class"] == "healthy"
    assert entries[2]["degradation_signals"] == []
    assert entries[2]["degraded"] is False
    assert entries[2]["degraded_reasons"] == []
    assert entries[2]["render_support"]["player_visible"] is False
    assert entries[2]["authority_summary"]["validation_status"] == "approved"
    assert entries[2]["authority_summary"]["selected_scene_function"] == "escalate_conflict"
    assert entries[2]["authority_summary"]["visibility_class_markers"] == ["truth_aligned"]
    assert entries[2]["dramatic_context_summary"]["contract"] == "story_window_dramatic_context.v1"
    assert entries[2]["dramatic_context_summary"]["social_outcome"] == "tension_escalates"
    assert entries[2]["authority_summary"]["dramatic_context"]["social_risk_band"] == "high"


def test_story_window_projection_preserves_degraded_quality_fields() -> None:
    session = StorySession(
        session_id="story-2",
        module_id="god_of_carnage",
        runtime_projection={"start_scene_id": "scene_1"},
        current_scene_id="scene_1",
    )
    session.diagnostics = [
        {
            "turn_number": 1,
            "turn_kind": "player",
            "raw_input": "I push back.",
            "visible_output_bundle": {"gm_narration": ["The room stirs."]},
            "narrative_commit": {"committed_consequences": ["pressure_holds"]},
            "committed_turn_authority": {
                "authority_record_version": "committed_turn_authority.v1",
                "validation_status": "approved",
                "commit_applied": True,
                "quality_class": "degraded",
                "degradation_signals": ["fallback_used"],
            },
            "runtime_governance_surface": {
                "quality_class": "degraded",
                "degradation_signals": ["fallback_used"],
                "degradation_summary": "fallback_used",
                "fallback_stage_reached": "graph_fallback_executed",
            },
        }
    ]
    entries = _story_window_entries_for_session(session)
    runtime = entries[-1]
    assert runtime["quality_class"] == "degraded"
    assert runtime["degradation_signals"] == ["fallback_used"]
    assert runtime["degraded"] is True
    assert runtime["degraded_reasons"] == ["fallback_used"]


def test_story_window_projection_includes_vitality_and_passivity_fields() -> None:
    session = StorySession(
        session_id="story-3",
        module_id="god_of_carnage",
        runtime_projection={"start_scene_id": "scene_1"},
        current_scene_id="scene_1",
    )
    session.diagnostics = [
        {
            "turn_number": 1,
            "turn_kind": "player",
            "raw_input": "...",
            "visible_output_bundle": {"gm_narration": ["The room pauses."]},
            "narrative_commit": {"committed_consequences": ["pressure_holds"]},
            "committed_turn_authority": {
                "authority_record_version": "committed_turn_authority.v1",
                "validation_status": "approved",
                "commit_applied": True,
                "quality_class": "degraded",
                "degradation_signals": ["fallback_used"],
            },
            "runtime_governance_surface": {
                "quality_class": "degraded",
                "degradation_signals": ["fallback_used"],
                "fallback_stage_reached": "graph_fallback_executed",
            },
            "actor_survival_telemetry": {
                "vitality_telemetry_v1": {
                    "schema_version": "vitality_telemetry_v1",
                    "response_present": False,
                    "initiative_present": False,
                    "multi_actor_realized": False,
                    "sparse_input_recovery_applied": False,
                    "realized_actor_ids": [],
                    "rendered_actor_ids": [],
                },
                "operator_diagnostic_hints": {
                    "why_turn_felt_passive": ["single_actor_only", "thin_edge_withheld"],
                    "primary_passivity_factors": ["single_actor_only"],
                },
            },
        }
    ]
    entries = _story_window_entries_for_session(session)
    runtime = entries[-1]
    assert runtime["vitality_summary"]["response_present"] is False
    assert runtime["vitality_summary"]["realized_actor_ids"] == []
    assert runtime["why_turn_felt_passive"] == ["single_actor_only", "thin_edge_withheld"]
    assert runtime["primary_passivity_factors"] == ["single_actor_only"]
