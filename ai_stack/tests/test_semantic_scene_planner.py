"""Bounded semantic scene planner enrichment tests."""

from __future__ import annotations

from ai_stack.story_runtime.semantic_planner.semantic_scene_planner import (
    SEMANTIC_SCENE_PLANNER_VERSION,
    build_semantic_scene_plan_enrichment,
)
from ai_stack.story_runtime.god_of_carnage.god_of_carnage_yaml_authority import load_goc_canonical_path_yaml


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


def test_scene_planner_builds_content_guided_dialogue_and_capability_gate() -> None:
    step_id = "opening_006_armed_vs_carrying"
    enrichment = build_semantic_scene_plan_enrichment(
        selected_scene_function="redirect_blame",
        selected_responder_set=[{"actor_id": "alain_reille", "role": "primary_responder"}],
        pacing_mode="standard",
        silence_brevity_decision={"mode": "normal", "reason": "default"},
        semantic_move_record={
            "move_type": "direct_accusation",
            "scene_risk_band": "high",
            "subtext": {"subtext_function": "force_accountability"},
        },
        social_state_record={"social_risk_band": "high"},
        character_mind_records=[],
        scene_assessment={
            "canonical_path_step_id": step_id,
            "scene_node_id": "written_statement_negotiation",
        },
        canonical_path=load_goc_canonical_path_yaml(),
        scene_graph={
            "nodes": [
                {
                    "id": "written_statement_negotiation",
                    "phase_id": "opening",
                    "canonical_path_step_id": step_id,
                }
            ]
        },
        locations={"places": [{"id": "longstreet_den", "inventory_object_ids": ["study_laptop"]}]},
        objects={"object_documents": {"study_laptop": {"id": "study_laptop"}}},
        content_access_policy={"blocked_entities": [], "gated_entities": []},
        character_documents={
            "veronique": {"actor_id": "veronique_vallon"},
            "michel": {"actor_id": "michel_longstreet"},
            "annette": {"actor_id": "annette_reille"},
            "alain": {"actor_id": "alain_reille"},
        },
        beat_library={
            "patterns": {
                "single_word_challenge": {"id": "single_word_challenge"},
                "paraphrase_required_with_facts": {"id": "paraphrase_required_with_facts"},
            },
            "pattern_files": {
                "single_word_challenge": "direction/beat_library/npc_speak/single_word_challenge.yaml",
                "paraphrase_required_with_facts": "direction/beat_library/npc_speak/paraphrase_required_with_facts.yaml",
            },
        },
        opening_quote_anchors={
            "copyright_policy": {
                "quote_usage": "short_anchor_only",
                "max_words_per_runtime_quote": 5,
                "must_not": ["continuous_verbatim_dialogue"],
            }
        },
        actor_lane_context={
            "human_actor_id": "annette_reille",
            "ai_forbidden_actor_ids": ["annette_reille"],
        },
        current_scene_id="written_statement_negotiation",
        turn_input_class="player_input",
        selection_source="semantic_pipeline_v1",
    )

    assert enrichment["content_frame"]["canonical_path_step_id"] == step_id
    assert enrichment["content_frame"]["object_focus_ids"] == ["study_laptop"]
    assert enrichment["speech_policy"]["speech_required"] is True
    assert enrichment["speech_policy"]["speech_function"] == "object_to_word_armed_with_a_single_word_question"
    assert enrichment["quote_moment_policy"]["mode"] == "moment_locked"
    assert enrichment["quote_moment_policy"]["exact_quote_allowed"] is True
    assert enrichment["quote_moment_policy"]["max_words_per_runtime_quote"] == 5

    dialogue = enrichment["dialogue_plan"]
    assert dialogue[0]["beat_pattern_ref"] == "single_word_challenge"
    assert dialogue[0]["actor_id"] == "alain_reille"
    assert dialogue[0]["quote_use"] == "exact_anchor_allowed"
    assert dialogue[0]["forces_response_chain"]["target_actor_id"] == "veronique_vallon"
    assert dialogue[1]["actor_id"] == "veronique_vallon"
    assert dialogue[1]["forced_by_previous_beat"] is True

    assert any(beat["beat_kind"] == "npc_speak_beat" for beat in enrichment["dramatic_beats"])
    assert enrichment["handover_policy"]["policy"] == "offer_player_action_after_dialogue_chain"

    manager_plan = enrichment["capability_manager_plan"]
    assert manager_plan["run_only_selected_capabilities"] is True
    assert manager_plan["dispatch_status"] == "passed"
    assert manager_plan["decision_basis"]["canonical_path_step_id"] == step_id
    assert manager_plan["decision_basis"]["speech_required"] is True
    assert "npc.social_reaction.optional" in manager_plan["required_capabilities"]
    assert "narrator.opening_event.realize" in manager_plan["selected_capabilities"]
    audit = manager_plan["capability_dispatch_audit"]
    assert audit["status"] == "passed"
    assert audit["loop_guard"]["recursive_dispatch_allowed"] is False
    assert audit["loop_guard"]["queue_expansion_allowed"] is False
    assert audit["dispatch_queue"] == manager_plan["selected_capabilities"]
    assert len(audit["paths"]) == len(manager_plan["selected_capabilities"])
    for path in audit["paths"]:
        assert path["status"] == "passed"
        assert path["cycle_detected"] is False
        assert path["terminal_node"] == "terminal"
        assert path["depth"] <= audit["max_path_depth"]
    assert "capability_manager:selective_capability_gate" in enrichment["planner_rationale_codes"]
