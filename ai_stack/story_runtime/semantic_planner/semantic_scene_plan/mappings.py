"""Deterministic mapping tables and external planner constants."""

from __future__ import annotations

from typing import Final

from ai_stack.story_runtime.director.capabilities_manager.director_capability_manager import (
    DIRECTOR_CAPABILITY_MANAGER_PLAN_SCHEMA_VERSION,
    audit_director_capability_paths,
)
from ai_stack.contracts.dramatic_capability_contracts import (
    NPC_ACTION_GESTURE_OPTIONAL,
    NPC_DIRECT_ANSWER_ALLOWED,
    NPC_SOCIAL_REACTION_OPTIONAL,
    NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
    NARRATOR_OBJECT_STATE_DESCRIBE,
    NARRATOR_OPENING_EVENT_REALIZE,
    NARRATOR_PERCEPTION_RESULT_DESCRIBE,
    NARRATOR_SCENE_CONTEXT_ESTABLISH,
)
from ai_stack.story_runtime.god_of_carnage.god_of_carnage_frozen_vocabulary import (
    CONTINUITY_CLASSES,
    TRANSITION_PATTERNS,
)


SEMANTIC_SCENE_PLANNER_VERSION: Final[str] = "goc_semantic_scene_planner_v1"


_CONTINUITY_BY_SCENE_FUNCTION: Final[dict[str, str]] = {
    "establish_pressure": "situational_pressure",
    "escalate_conflict": "situational_pressure",
    "probe_motive": "situational_pressure",
    "repair_or_stabilize": "repair_attempt",
    "withhold_or_evade": "silent_carry",
    "reveal_surface": "revealed_fact",
    "redirect_blame": "blame_pressure",
    "scene_pivot": "alliance_shift",
}


_PRESSURE_AXIS_BY_MOVE_TYPE: Final[dict[str, str]] = {
    "off_scope_containment": "boundary",
    "silence_withdrawal": "withholding",
    "repair_attempt": "repair",
    "direct_accusation": "accountability",
    "indirect_provocation": "provocation",
    "evasive_deflection": "deflection",
    "humiliating_exposure": "dignity",
    "alliance_reposition": "alliance",
    "probe_inquiry": "motive",
    "escalation_threat": "rupture",
    "reveal_surface": "exposure",
    "establish_situational_pressure": "situational",
    "competing_repair_and_reveal": "repair_vs_exposure",
}


_PRESSURE_AXIS_BY_SCENE_FUNCTION: Final[dict[str, str]] = {
    "establish_pressure": "situational",
    "escalate_conflict": "rupture",
    "probe_motive": "motive",
    "repair_or_stabilize": "repair",
    "withhold_or_evade": "withholding",
    "reveal_surface": "exposure",
    "redirect_blame": "accountability",
    "scene_pivot": "alliance",
}


_BEAT_INTENTS_BY_SCENE_FUNCTION: Final[dict[str, tuple[str, ...]]] = {
    "establish_pressure": ("anchor_scene_pressure", "invite_specific_response"),
    "escalate_conflict": (
        "raise_pressure",


        "force_visible_reaction",
        "leave_tension_unresolved",
    ),
    "probe_motive": ("press_for_motive", "preserve_ambiguity"),
    "repair_or_stabilize": ("test_repair_sincerity", "allow_partial_release"),
    "withhold_or_evade": ("mark_withheld_response", "preserve_negative_space"),
    "reveal_surface": ("surface_allowed_information", "register_social_cost"),
    "redirect_blame": ("shift_accountability", "carry_blame_forward"),
    "scene_pivot": ("change_pressure_axis", "preserve_scene_boundary"),
}


_NARRATIVE_SCENE_FUNCTION_BY_MOVE_TYPE: Final[dict[str, str]] = {
    "off_scope_containment": "contain_out_of_scope",
    "silence_withdrawal": "preserve_negative_space",
    "repair_attempt": "test_repair_sincerity",
    "direct_accusation": "force_accountability",
    "indirect_provocation": "raise_pressure",
    "evasive_deflection": "narrate_evasion",
    "humiliating_exposure": "force_accountability",
    "alliance_reposition": "shift_social_arrangement",
    "probe_inquiry": "probe_motive",
    "escalation_threat": "raise_pressure",
    "reveal_surface": "surface_information",
    "establish_situational_pressure": "establish_scene_pressure",
    "competing_repair_and_reveal": "test_repair_sincerity",
}


_NARRATIVE_SCENE_FUNCTION_BY_SCENE_FUNCTION: Final[dict[str, str]] = {
    "establish_pressure": "establish_scene_pressure",
    "escalate_conflict": "raise_pressure",
    "probe_motive": "probe_motive",
    "repair_or_stabilize": "test_repair_sincerity",
    "withhold_or_evade": "narrate_evasion",
    "reveal_surface": "surface_information",
    "redirect_blame": "force_accountability",
    "scene_pivot": "shift_social_arrangement",
}


_PRESSURE_FUNCTION_BY_AXIS: Final[dict[str, str]] = {
    "accountability": "force_accountability",
    "alliance": "test_alliance_position",
    "boundary": "contain_boundary",
    "deflection": "mark_deflection",
    "dignity": "register_dignity_cost",
    "exposure": "force_disclosure_pressure",
    "motive": "probe_motive",
    "provocation": "raise_provocation",
    "repair": "test_repair_sincerity",
    "repair_vs_exposure": "hold_repair_exposure_tension",
    "rupture": "escalate_rupture",
    "situational": "seed_initial_pressure",
    "withholding": "preserve_withholding",
}


_REALIZATION_MODE_BY_NARRATIVE_FUNCTION: Final[dict[str, str]] = {
    "arrange_scene": "mixed_narration_and_npc_action",
    "contain_out_of_scope": "narration",
    "establish_scene_anchor": "narration",
    "establish_scene_pressure": "mixed_narration_and_npc_action",
    "force_accountability": "npc_dialogue_and_visible_reaction",
    "narrate_consequence": "narration",
    "narrate_evasion": "npc_action_or_narration",
    "narrate_sensory_focus": "narration",
    "preserve_negative_space": "silence_and_visible_reaction",
    "probe_motive": "npc_dialogue_and_visible_reaction",
    "raise_pressure": "npc_dialogue_and_visible_reaction",
    "shift_social_arrangement": "mixed_narration_and_npc_action",
    "surface_information": "npc_dialogue_or_visible_evidence",
    "test_repair_sincerity": "npc_dialogue_and_visible_reaction",
}


_TARGET_FUNCTION_BY_NARRATIVE_FUNCTION: Final[dict[str, str]] = {


    "arrange_scene": "create_playable_setup",
    "contain_out_of_scope": "return_to_scene_scope",
    "establish_scene_anchor": "anchor_room_and_cast",
    "establish_scene_pressure": "seed_initial_pressure",
    "force_accountability": "force_reaction",
    "narrate_consequence": "render_action_consequence",
    "narrate_evasion": "make_evasion_visible",
    "narrate_sensory_focus": "render_perceptual_detail",
    "preserve_negative_space": "hold_silence_and_invite_visibility",
    "probe_motive": "draw_out_motive",
    "raise_pressure": "intensify_visible_conflict",
    "shift_social_arrangement": "reposition_relationship_axis",
    "surface_information": "surface_allowed_information",
    "test_repair_sincerity": "test_repair_sincerity",
}


_TARGET_EFFECT_BY_NARRATIVE_FUNCTION: Final[dict[str, str]] = {
    "arrange_scene": "playable_setup_ready",
    "contain_out_of_scope": "scene_scope_restored",
    "establish_scene_anchor": "scene_anchor_visible",
    "establish_scene_pressure": "initial_pressure_visible",
    "force_accountability": "accountability_reaction_visible",
    "narrate_consequence": "player_action_consequence_visible",
    "narrate_evasion": "evasion_cost_visible",
    "narrate_sensory_focus": "perceptual_detail_available",
    "preserve_negative_space": "withholding_visible_without_forced_speech",
    "probe_motive": "motive_pressure_visible",
    "raise_pressure": "conflict_pressure_raised",
    "shift_social_arrangement": "relationship_axis_repositioned",
    "surface_information": "allowed_information_surfaced",
    "test_repair_sincerity": "repair_offer_tested",
}


_TARGET_KIND_BY_NARRATIVE_FUNCTION: Final[dict[str, str]] = {
    "arrange_scene": "setup",
    "contain_out_of_scope": "scene",
    "establish_scene_anchor": "room",
    "establish_scene_pressure": "setup",
    "narrate_consequence": "player_affordance",
    "narrate_sensory_focus": "room",
    "shift_social_arrangement": "relationship",
    "surface_information": "information",
}


_BEAT_TEMPLATES_BY_NARRATIVE_FUNCTION: Final[
    dict[str, tuple[tuple[str, str, str, str], ...]]
] = {
    "arrange_scene": (
        ("setup_beat", "establish_arrangement", "stage_room_and_present_cast", "director"),
        ("npc_action_beat", "force_initial_npc_position", "stage_npc_presence", "npc"),
        ("player_handover_beat", "offer_playable_opening", "handover_control_to_player", "director"),
    ),
    "contain_out_of_scope": (
        ("narration_beat", "mark_boundary", "preserve_scene_scope", "narrator"),
        ("player_handover_beat", "return_to_scene", "handover_control_to_player", "director"),
    ),
    "establish_scene_anchor": (
        ("environment_beat", "anchor_room", "anchor_scene_space", "narrator"),
        ("setup_beat", "make_cast_position_visible", "stage_present_cast", "director"),
        ("player_handover_beat", "offer_playable_opening", "handover_control_to_player", "director"),
    ),
    "establish_scene_pressure": (
        ("setup_beat", "seed_initial_pressure", "anchor_scene_pressure", "director"),
        ("npc_action_beat", "force_visible_reaction", "invite_specific_response", "npc"),
    ),
    "force_accountability": (
        ("npc_dialogue_beat", "force_accountability", "shift_accountability", "npc"),
        ("relationship_shift_beat", "register_social_cost", "carry_blame_forward", "director"),
    ),
    "narrate_consequence": (
        ("narration_beat", "render_action_consequence", "show_consequence", "narrator"),
        ("player_handover_beat", "return_control", "handover_control_to_player", "director"),


    ),
    "narrate_evasion": (
        ("npc_action_beat", "mark_evasion", "mark_withheld_response", "npc"),
        ("silence_beat", "preserve_gap", "preserve_negative_space", "director"),
    ),
    "narrate_sensory_focus": (
        ("environment_beat", "focus_sensory_detail", "narrate_sensory_focus", "narrator"),
        ("information_beat", "surface_available_cue", "surface_allowed_information", "narrator"),
    ),
    "preserve_negative_space": (
        ("silence_beat", "hold_silence", "mark_withheld_response", "director"),
        ("npc_action_beat", "force_visible_reaction_without_speech", "preserve_negative_space", "npc"),
    ),
    "probe_motive": (
        ("npc_dialogue_beat", "probe_motive", "press_for_motive", "npc"),
        ("silence_beat", "preserve_ambiguity", "preserve_ambiguity", "director"),
    ),
    "raise_pressure": (
        ("npc_dialogue_beat", "raise_pressure", "raise_pressure", "npc"),
        ("npc_action_beat", "force_visible_reaction", "force_visible_reaction", "npc"),
        ("transition_beat", "leave_tension_unresolved", "leave_tension_unresolved", "director"),
    ),
    "shift_social_arrangement": (
        ("setup_beat", "reposition_relationship_axis", "change_pressure_axis", "director"),
        ("interruption_beat", "force_npc_interruption", "stage_interruption", "npc"),
        ("transition_beat", "preserve_scene_boundary", "preserve_scene_boundary", "director"),
    ),
    "surface_information": (
        ("information_beat", "surface_allowed_information", "surface_allowed_information", "npc"),
        ("relationship_shift_beat", "register_social_cost", "register_social_cost", "director"),
    ),
    "test_repair_sincerity": (
        ("npc_dialogue_beat", "test_repair_sincerity", "test_repair_sincerity", "npc"),
        ("recovery_beat", "allow_partial_release", "allow_partial_release", "director"),
    ),
}


_HARD_TRANSITION_SCENE_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {"escalate_conflict", "redirect_blame", "reveal_surface"}
)
