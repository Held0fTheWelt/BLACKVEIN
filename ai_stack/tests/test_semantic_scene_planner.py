"""Bounded semantic scene planner enrichment tests."""

from __future__ import annotations

from ai_stack.semantic_scene_planner import (
    SEMANTIC_SCENE_PLANNER_VERSION,
    build_semantic_scene_plan_enrichment,
)


def test_scene_planner_builds_pressure_target_beats_and_obligation() -> None:
    enrichment = build_semantic_scene_plan_enrichment(
        selected_scene_function="redirect_blame",
        selected_responder_set=[{"actor_id": "michel_longstreet", "role": "primary_responder"}],
        pacing_mode="standard",
        silence_brevity_decision={"mode": "normal", "reason": "default"},
        semantic_move_record={
            "move_type": "direct_accusation",
            "social_move_family": "attack",
            "target_actor_hint": "michel_longstreet",
            "scene_risk_band": "high",
            "subtext": {
                "subtext_function": "force_accountability",
                "hidden_intent_hypothesis": "force_accountability",
            },
        },
        social_state_record={
            "social_risk_band": "high",
            "responder_asymmetry_code": "blame_on_host_spouse_axis",
            "dominant_relationship_axis_id": "host_guest_civility_axis",
        },
        character_mind_records=[
            {
                "runtime_actor_id": "michel_longstreet",
                "tactical_posture": "deflect_practical_shame",
                "pressure_response_bias": "deflect_then_minimize",
            }
        ],
        scene_assessment={"pressure_state": "high_blame"},
        implied_continuity_by_function={"redirect_blame": "blame_pressure"},
        prior_continuity_impacts=[],
        selection_source="semantic_pipeline_v1",
    )

    assert enrichment["semantic_scene_planner_version"] == SEMANTIC_SCENE_PLANNER_VERSION
    assert enrichment["narrative_scene_function"] == "force_accountability"
    assert enrichment["realization_mode"] == "npc_dialogue_and_visible_reaction"
    assert enrichment["scene_target"]["target_function"] == "force_reaction"
    assert enrichment["scene_target"]["target_kind"] == "actor"
    assert enrichment["pressure_target"]["target_actor_id"] == "michel_longstreet"
    assert enrichment["pressure_target"]["pressure_axis"] == "accountability"
    assert enrichment["pressure_target"]["target_function"] == "force_reaction"
    assert enrichment["target_obligations"][0]["obligation_kind"] == "respect_commit_authority"
    assert enrichment["actor_directives"][0]["directive"] == "force_npc_reaction"
    assert enrichment["handover_policy"]["policy"] == "offer_response_under_tension"
    assert enrichment["continuity_obligation"]["continuity_class"] == "blame_pressure"
    assert enrichment["expected_transition_pattern"] == "hard"
    assert enrichment["dramatic_beats"][0]["beat_kind"] == "npc_dialogue_beat"
    assert enrichment["dramatic_beats"][0]["beat_function"] == "force_accountability"
    assert enrichment["dramatic_beats"][0]["beat_intent"] == "shift_accountability"
    assert "pressure_axis:accountability" in enrichment["planner_rationale_codes"]
    assert "narrative_scene_function:force_accountability" in enrichment["planner_rationale_codes"]


def test_scene_planner_marks_off_scope_containment_as_diagnostics_only() -> None:
    enrichment = build_semantic_scene_plan_enrichment(
        selected_scene_function="scene_pivot",
        selected_responder_set=[],
        pacing_mode="containment",
        silence_brevity_decision={"mode": "normal", "reason": "slice_boundary"},
        semantic_move_record={
            "move_type": "off_scope_containment",
            "social_move_family": "neutral",
            "scene_risk_band": "low",
        },
        social_state_record={"social_risk_band": "low"},
        character_mind_records=[],
        implied_continuity_by_function={"scene_pivot": "refused_cooperation"},
        prior_continuity_impacts=[],
        selection_source="semantic_pipeline_v1",
    )

    assert enrichment["expected_transition_pattern"] == "diagnostics_only"
    assert enrichment["narrative_scene_function"] == "contain_out_of_scope"
    assert enrichment["scene_target"]["target_function"] == "return_to_scene_scope"
    assert enrichment["handover_policy"]["policy"] == "contain_and_return_to_scene"
    assert enrichment["actor_directives"][0]["directive"] == "contain_without_forcing_npc"
    assert enrichment["pressure_target"]["target_kind"] == "scene"
    assert enrichment["continuity_obligation"]["commit_authority"] == "commit_seam"


def test_scene_planner_arranges_opening_setup_with_actor_directive() -> None:
    enrichment = build_semantic_scene_plan_enrichment(
        selected_scene_function="establish_pressure",
        selected_responder_set=[{"actor_id": "veronique_houllie", "role": "primary_responder"}],
        pacing_mode="standard",
        silence_brevity_decision={"mode": "normal", "reason": "opening"},
        semantic_move_record={
            "move_type": "establish_situational_pressure",
            "social_move_family": "neutral",
            "scene_risk_band": "moderate",
            "feature_snapshot": {},
        },
        social_state_record={"social_risk_band": "moderate"},
        character_mind_records=[],
        scene_assessment={"scene_phase": "opening", "current_scene_id": "living_room"},
        implied_continuity_by_function={"establish_pressure": "situational_pressure"},
        prior_continuity_impacts=[],
        selection_source="engine_opening_turn",
    )

    assert enrichment["narrative_scene_function"] == "arrange_scene"
    assert enrichment["scene_target"]["target_kind"] == "setup"
    assert enrichment["scene_target"]["target_function"] == "create_playable_setup"
    assert enrichment["pressure_function"] == "seed_initial_pressure"
    assert enrichment["actor_directives"][0]["directive"] == "stage_npc_presence"
    assert enrichment["dramatic_beats"][0]["beat_kind"] == "setup_beat"
    assert enrichment["dramatic_beats"][-1]["beat_kind"] == "player_handover_beat"
    assert enrichment["handover_policy"]["policy"] == "offer_player_action_after_setup"


def test_scene_planner_uses_non_pressure_target_for_player_action() -> None:
    enrichment = build_semantic_scene_plan_enrichment(
        selected_scene_function="establish_pressure",
        selected_responder_set=[],
        pacing_mode="standard",
        silence_brevity_decision={"mode": "normal", "reason": "default"},
        semantic_move_record={
            "move_type": "establish_situational_pressure",
            "social_move_family": "neutral",
            "scene_risk_band": "low",
            "feature_snapshot": {
                "player_input_kind_is_action": True,
                "player_input_kind_is_speech": False,
            },
        },
        social_state_record={"social_risk_band": "low"},
        character_mind_records=[],
        scene_assessment={"current_scene_id": "living_room"},
        implied_continuity_by_function={"establish_pressure": "situational_pressure"},
        prior_continuity_impacts=[],
        selection_source="semantic_pipeline_v1",
    )

    assert enrichment["narrative_scene_function"] == "narrate_consequence"
    assert enrichment["pressure_function"] == "none"
    assert enrichment["scene_target"]["target_kind"] == "player_affordance"
    assert enrichment["scene_target"]["target_function"] == "render_action_consequence"
    assert enrichment["actor_directives"][0]["directive"] == "narrate_without_forcing_npc"
    assert enrichment["handover_policy"]["policy"] == "return_control_after_narration"
