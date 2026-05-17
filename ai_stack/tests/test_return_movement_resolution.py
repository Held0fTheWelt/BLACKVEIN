"""Return-movement affordance resolution (MOVEMENT-RETURN-AFFORDANCE-CONTEXT-RESOLUTION-01).

German strings appear only as runtime input; assertions and docstrings are English.
"""

from __future__ import annotations

from ai_stack.langgraph_synthetic_action_resolution import build_synthetic_generation_for_action_resolution
from ai_stack.player_action_resolution import resolve_player_action
from story_runtime_core.content_locale import (
    classify_player_input_from_rules,
    resolve_content_modules_root,
)

MODULE = "god_of_carnage"
_LANG = "de"


def _classify(raw: str) -> dict:
    return classify_player_input_from_rules(
        raw,
        module_id=MODULE,
        lang_hint=_LANG,
        content_modules_root=resolve_content_modules_root(),
    )


def test_return_movement_without_target_uses_previous_location() -> None:
    raw = "Ich gehe zurück."
    interp = _classify(raw)
    assert interp.get("movement_return_intent") is True
    plc = {"current_location_id": "bathroom", "previous_location_id": "living_room"}
    out = resolve_player_action(
        raw_text=raw,
        interpreted_input=interp,
        module_id=MODULE,
        runtime_projection={},
        player_local_context=plc,
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "allowed"
    assert aff["resolved_target_id"] == "living_room"
    assert aff["target_resolution_source"] == "player_local_context.previous_location_id"
    frame = out["player_action_frame"]
    assert frame["player_input_kind"] == "movement_action"
    assert frame["verb"] == "move_to"


def test_return_movement_with_explicit_german_target_resolves_living_room() -> None:
    raw = "Ich gehe zurück ins Wohnzimmer."
    interp = _classify(raw)
    assert interp.get("movement_return_intent") is True
    plc = {"current_location_id": "bathroom", "previous_location_id": "hallway"}
    out = resolve_player_action(
        raw_text=raw,
        interpreted_input=interp,
        module_id=MODULE,
        runtime_projection={},
        player_local_context=plc,
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "allowed"
    assert aff["resolved_target_id"] == "living_room"
    assert aff["target_resolution_source"] == "scene_affordance_alias"


def test_return_movement_without_previous_location_needs_clarification() -> None:
    raw = "Ich gehe zurück."
    interp = _classify(raw)
    plc = {"current_location_id": "bathroom"}
    out = resolve_player_action(
        raw_text=raw,
        interpreted_input=interp,
        module_id=MODULE,
        runtime_projection={},
        player_local_context=plc,
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "ambiguous"
    assert aff["action_commit_policy"] == "needs_clarification"
    assert aff.get("target_resolution_source") == "missing_previous_location_id"
    assert aff.get("reason") == "missing_previous_location_id"


def test_return_movement_synthetic_updates_player_local_context() -> None:
    raw = "Ich gehe zurück."
    interp = _classify(raw)
    plc = {"current_location_id": "bathroom", "previous_location_id": "living_room"}
    out = resolve_player_action(
        raw_text=raw,
        interpreted_input=interp,
        module_id=MODULE,
        runtime_projection={},
        player_local_context=plc,
    )
    frame = out["player_action_frame"]
    aff = out["affordance_resolution"]
    sam = out["scene_affordance_model"]
    gen = build_synthetic_generation_for_action_resolution(
        module_id=MODULE,
        lang=_LANG,
        player_action_frame=frame,
        affordance_resolution=aff,
        scene_affordance_model=sam,
        current_player_local_context=plc,
    )
    meta = gen.get("metadata") or {}
    uplc = meta.get("updated_player_local_context") or {}
    assert uplc.get("current_location_id") == "living_room"
    assert uplc.get("previous_location_id") == "bathroom"
    narr = str(gen.get("content") or "")
    assert "sagt:" not in narr.lower()
