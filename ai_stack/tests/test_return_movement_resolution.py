"""Return movement is resolved from AI semantics, not phrase maps."""

from __future__ import annotations

from ai_stack.langgraph.langgraph_synthetic_action_resolution import build_synthetic_generation_for_action_resolution
from ai_stack.player_action_resolution import resolve_player_action
from ai_stack.language_io.language_adapter import resolve_content_modules_root

MODULE = "god_of_carnage"
_LANG = "de"


def _semantic_return_to_living_room() -> dict:
    return {
        "player_input_kind": "action",
        "narrator_response_expected": True,
        "npc_response_expected": False,
        "semantic_action": {
            "player_input_kind": "action",
            "verb": "move_to",
            "action_kind": "movement",
            "target_query": "Wohnzimmer",
            "resolved_target_id": "living_room",
            "resolved_target_type": "location",
            "commit_policy": "commit_action",
            "confidence": "high",
        },
    }


def test_return_movement_with_ai_semantic_target_resolves_living_room() -> None:
    raw = "Ich gehe zurück ins Wohnzimmer."
    out = resolve_player_action(
        raw_text=raw,
        interpreted_input=_semantic_return_to_living_room(),
        module_id=MODULE,
        runtime_projection={},
        player_local_context={"current_location_id": "bathroom", "previous_location_id": "hallway"},
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "allowed"
    assert aff["resolved_target_id"] == "living_room"
    assert aff["target_resolution_source"] == "ai_semantic_resolution.content_id"


def test_return_movement_without_ai_semantics_needs_resolution() -> None:
    raw = "Ich gehe zurück."
    out = resolve_player_action(
        raw_text=raw,
        interpreted_input={"player_input_kind": "action"},
        module_id=MODULE,
        runtime_projection={},
        player_local_context={"current_location_id": "bathroom", "previous_location_id": "living_room"},
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "ambiguous"
    assert aff["action_commit_policy"] == "needs_clarification"
    assert aff["target_resolution_source"] == "semantic_ai_resolution_required"


def test_return_movement_synthetic_updates_player_local_context() -> None:
    raw = "Ich gehe zurück ins Wohnzimmer."
    plc = {"current_location_id": "bathroom", "previous_location_id": "hallway"}
    out = resolve_player_action(
        raw_text=raw,
        interpreted_input=_semantic_return_to_living_room(),
        module_id=MODULE,
        runtime_projection={},
        player_local_context=plc,
    )
    gen = build_synthetic_generation_for_action_resolution(
        module_id=MODULE,
        lang=_LANG,
        player_action_frame=out["player_action_frame"],
        affordance_resolution=out["affordance_resolution"],
        scene_affordance_model=out["scene_affordance_model"],
        current_player_local_context=plc,
        content_modules_root=resolve_content_modules_root(),
    )
    meta = gen.get("metadata") or {}
    uplc = meta.get("updated_player_local_context") or {}
    assert uplc.get("current_location_id") == "living_room"
    assert uplc.get("previous_location_id") == "bathroom"
