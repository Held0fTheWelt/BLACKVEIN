"""PLAYER-LOCAL-CONTEXT-AND-NARRATOR-CONSEQUENCE-01: narrator consequence contract tests.

Verifies that the narrator consequence pipeline produces:
  - a LocalContextTransition with correct transition_type, to_area, new_area_established
  - a NarratorConsequencePlan with authored consequence_text (not a template restatement)
  - an updated player_local_context that advances the player into the new situation
  - correct German locale rendering (as runtime data, test code stays English)
  - multi-turn context persistence (player_local_context carries forward)

All test inputs and assertions are in English. German content appears only as runtime data
loaded from ``content/modules/god_of_carnage/locale/scene_affordances.yaml`` via
``load_goc_scene_affordances_block()`` (no duplicated hardcoded affordance tables in tests).
"""

from __future__ import annotations

import pytest

from ai_stack.goc_yaml_authority import load_goc_scene_affordances_block
from ai_stack.narrator_consequence_contracts import (
    build_local_context_transition,
    build_narrator_consequence_plan,
    build_updated_player_local_context,
)
from ai_stack.langgraph_synthetic_action_resolution import (
    build_synthetic_generation_for_action_resolution,
)
from story_runtime_core.content_locale import (
    clear_content_locale_caches,
    resolve_content_modules_root,
)

MODULE = "god_of_carnage"

_SCENE_AFFORDANCE_MODEL = load_goc_scene_affordances_block()


def setup_module(_m: object) -> None:
    clear_content_locale_caches()


def _root():
    return resolve_content_modules_root()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _frame(verb: str, target_id: str = "", alias: str = "", action_kind: str = "") -> dict:
    resolved_target = {"target_id": target_id, "matched_alias": alias} if target_id or alias else {}
    return {
        "verb": verb,
        "action_kind": action_kind or verb,
        "resolved_target": resolved_target,
    }


def _aff(status: str, policy: str = "commit") -> dict:
    return {"affordance_status": status, "action_commit_policy": policy}


# ---------------------------------------------------------------------------
# Movement — LocalContextTransition
# ---------------------------------------------------------------------------


def test_move_to_bathroom_offscreen_transition_type():
    lct = build_local_context_transition(
        player_action_frame=_frame("move_to", "bathroom", "bathroom"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    assert lct["transition_type"] == "move_offscreen"
    assert lct["to_area"] == "bathroom"
    assert lct["new_area_established"] is True
    assert lct["location_found"] is True
    assert lct["from_area"] == "vallon_living_room"


def test_move_to_hallway_adjacent_transition_type():
    lct = build_local_context_transition(
        player_action_frame=_frame("move_to", "hallway", "hallway"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    assert lct["transition_type"] == "move_local"
    assert lct["to_area"] == "hallway"
    assert lct["new_area_established"] is True
    assert lct["location_found"] is True


def test_move_to_kitchen_alias_matching():
    lct = build_local_context_transition(
        player_action_frame=_frame("move_to", "Küche", "Küche"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    assert lct["to_area"] == "kitchen"
    assert lct["location_found"] is True
    assert lct["new_area_established"] is True


def test_stand_up_no_area_change():
    lct = build_local_context_transition(
        player_action_frame=_frame("stand_up", action_kind="movement"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    assert lct["transition_type"] == "posture_change"
    assert lct["new_area_established"] is False
    assert lct["to_area"] is None


def test_blocked_movement_no_new_area():
    lct = build_local_context_transition(
        player_action_frame=_frame("move_to", "bathroom", "bathroom"),
        affordance_resolution=_aff("blocked"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    assert lct["transition_allowed"] is False
    assert lct["new_area_established"] is False


# ---------------------------------------------------------------------------
# Perception — LocalContextTransition
# ---------------------------------------------------------------------------


def test_look_at_window_perception_transition():
    lct = build_local_context_transition(
        player_action_frame=_frame("look_at", "window", "window"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    assert lct["transition_type"] == "perception"
    assert lct["object_found"] is True
    assert lct["new_area_established"] is False


def test_look_at_nonexistent_object_no_object_found():
    lct = build_local_context_transition(
        player_action_frame=_frame("look_at", "chandelier", "chandelier"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    assert lct["transition_type"] == "perception"
    assert lct["object_found"] is False


# ---------------------------------------------------------------------------
# NarratorConsequencePlan — authored text vs template fallback
# ---------------------------------------------------------------------------


def test_consequence_bathroom_en_uses_authored_text():
    lct = build_local_context_transition(
        player_action_frame=_frame("move_to", "bathroom", "bathroom"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    ncp = build_narrator_consequence_plan(
        lang="en",
        player_action_frame=_frame("move_to", "bathroom", "bathroom"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct,
    )
    assert ncp["consequence_text"] is not None
    assert "quiet" in ncp["consequence_text"] or "distance" in ncp["consequence_text"]
    assert ncp["source"] == "scene_affordance_detail"
    assert ncp["consequence_type"] == "area_transition"
    assert ncp["local_context_updated"] is True


def test_consequence_bathroom_de_uses_authored_german_text():
    lct = build_local_context_transition(
        player_action_frame=_frame("move_to", "bathroom", "Badezimmer"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    ncp = build_narrator_consequence_plan(
        lang="de",
        player_action_frame=_frame("move_to", "bathroom", "Badezimmer"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct,
    )
    assert ncp["consequence_text"] is not None
    assert "Stille" in ncp["consequence_text"] or "Abstand" in ncp["consequence_text"]
    assert ncp["source"] == "scene_affordance_detail"


def test_consequence_window_perception_en():
    lct = build_local_context_transition(
        player_action_frame=_frame("look_at", "window", "window"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    ncp = build_narrator_consequence_plan(
        lang="en",
        player_action_frame=_frame("look_at", "window", "window"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct,
    )
    assert ncp["consequence_text"] is not None
    assert "window" in ncp["consequence_text"].lower() or "street" in ncp["consequence_text"]
    assert ncp["consequence_type"] == "perception_result"
    assert ncp["source"] == "scene_affordance_detail"


def test_consequence_window_perception_de():
    lct = build_local_context_transition(
        player_action_frame=_frame("look_at", "window", "Fenster"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    ncp = build_narrator_consequence_plan(
        lang="de",
        player_action_frame=_frame("look_at", "window", "Fenster"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct,
    )
    assert ncp["consequence_text"] is not None
    assert "Fenster" in ncp["consequence_text"] or "Straße" in ncp["consequence_text"]
    assert ncp["source"] == "scene_affordance_detail"


def test_consequence_fallback_when_no_scene_model():
    lct = build_local_context_transition(
        player_action_frame=_frame("move_to", "bathroom", "bathroom"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model={},
        current_player_local_context=None,
    )
    ncp = build_narrator_consequence_plan(
        lang="en",
        player_action_frame=_frame("move_to", "bathroom", "bathroom"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model={},
        local_context_transition=lct,
    )
    assert ncp["consequence_text"] is None
    assert ncp["source"] == "template_fallback"


def test_consequence_unknown_object_no_authored_text():
    lct = build_local_context_transition(
        player_action_frame=_frame("look_at", "chandelier", "chandelier"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    ncp = build_narrator_consequence_plan(
        lang="en",
        player_action_frame=_frame("look_at", "chandelier", "chandelier"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct,
    )
    assert ncp["consequence_text"] is None
    assert ncp["source"] == "template_fallback"


# ---------------------------------------------------------------------------
# Updated player_local_context persistence
# ---------------------------------------------------------------------------


def test_updated_context_after_bathroom_move():
    lct = build_local_context_transition(
        player_action_frame=_frame("move_to", "bathroom", "bathroom"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    ncp = build_narrator_consequence_plan(
        lang="en",
        player_action_frame=_frame("move_to", "bathroom", "bathroom"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct,
    )
    uplc = build_updated_player_local_context(
        current_player_local_context=None,
        local_context_transition=lct,
        narrator_consequence_plan=ncp,
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
    )
    assert uplc["current_area"] == "bathroom"
    assert "look_at" in uplc.get("available_affordances", [])
    assert uplc.get("last_transition_type") == "move_offscreen"


def test_updated_context_after_kitchen_move():
    lct = build_local_context_transition(
        player_action_frame=_frame("move_to", "kitchen", "kitchen"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    ncp = build_narrator_consequence_plan(
        lang="en",
        player_action_frame=_frame("move_to", "kitchen", "kitchen"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct,
    )
    uplc = build_updated_player_local_context(
        current_player_local_context=None,
        local_context_transition=lct,
        narrator_consequence_plan=ncp,
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
    )
    assert uplc["current_area"] == "kitchen"
    assert "look_at" in uplc.get("available_affordances", [])
    assert "take" in uplc.get("available_affordances", [])


def test_updated_context_perception_does_not_change_area():
    prior = {"current_area": "vallon_living_room", "available_affordances": ["look_at"]}
    lct = build_local_context_transition(
        player_action_frame=_frame("look_at", "window", "window"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=prior,
    )
    ncp = build_narrator_consequence_plan(
        lang="en",
        player_action_frame=_frame("look_at", "window", "window"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct,
    )
    uplc = build_updated_player_local_context(
        current_player_local_context=prior,
        local_context_transition=lct,
        narrator_consequence_plan=ncp,
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
    )
    assert uplc["current_area"] == "vallon_living_room"
    assert uplc.get("last_perception_target") == lct.get("target_id") or uplc.get("last_perception_result") is not None


def test_multi_turn_context_persists_after_move():
    """Second turn starts from the updated context of the first turn."""
    lct1 = build_local_context_transition(
        player_action_frame=_frame("move_to", "bathroom", "bathroom"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    ncp1 = build_narrator_consequence_plan(
        lang="en",
        player_action_frame=_frame("move_to", "bathroom", "bathroom"),
        affordance_resolution=_aff("allowed_offscreen"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct1,
    )
    ctx_after_turn1 = build_updated_player_local_context(
        current_player_local_context=None,
        local_context_transition=lct1,
        narrator_consequence_plan=ncp1,
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
    )
    assert ctx_after_turn1["current_area"] == "bathroom"

    # Turn 2: look at window while in bathroom
    lct2 = build_local_context_transition(
        player_action_frame=_frame("look_at", "window", "window"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=ctx_after_turn1,
    )
    ncp2 = build_narrator_consequence_plan(
        lang="en",
        player_action_frame=_frame("look_at", "window", "window"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct2,
    )
    ctx_after_turn2 = build_updated_player_local_context(
        current_player_local_context=ctx_after_turn1,
        local_context_transition=lct2,
        narrator_consequence_plan=ncp2,
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
    )
    # Area must not change on perception
    assert ctx_after_turn2["current_area"] == "bathroom"
    assert lct2["from_area"] == "bathroom"


# ---------------------------------------------------------------------------
# build_synthetic_generation_for_action_resolution integration
# ---------------------------------------------------------------------------


def test_synthetic_gen_uses_authored_text_for_bathroom():
    gen = build_synthetic_generation_for_action_resolution(
        module_id=MODULE,
        lang="en",
        player_action_frame={
            "verb": "move_to",
            "action_kind": "movement",
            "resolved_target": {"target_id": "bathroom", "matched_alias": "bathroom"},
        },
        affordance_resolution={"affordance_status": "allowed_offscreen", "action_commit_policy": "commit"},
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        content_modules_root=_root(),
    )
    assert gen["success"] is True
    narr = gen["content"]
    assert "bathroom" in narr.lower() or "quiet" in narr or "distance" in narr, (
        f"Narrator text did not use authored entry detail: {narr!r}"
    )
    meta = gen["metadata"]
    assert meta.get("local_context_transition") is not None
    assert meta.get("narrator_consequence_plan") is not None
    assert meta["narrator_consequence_plan"]["source"] == "scene_affordance_detail"


def test_synthetic_gen_uses_authored_text_for_window_perception():
    gen = build_synthetic_generation_for_action_resolution(
        module_id=MODULE,
        lang="en",
        player_action_frame={
            "verb": "look_at",
            "action_kind": "perception",
            "resolved_target": {"target_id": "window", "matched_alias": "window"},
        },
        affordance_resolution={"affordance_status": "allowed", "action_commit_policy": "commit"},
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        content_modules_root=_root(),
    )
    narr = gen["content"]
    assert "window" in narr.lower() or "street" in narr, (
        f"Narrator text did not use authored perception detail: {narr!r}"
    )
    assert gen["metadata"]["narrator_consequence_plan"]["consequence_type"] == "perception_result"


def test_synthetic_gen_falls_back_to_template_when_no_scene_model():
    gen = build_synthetic_generation_for_action_resolution(
        module_id=MODULE,
        lang="en",
        player_action_frame={
            "verb": "move_to",
            "action_kind": "movement",
            "resolved_target": {"target_id": "bathroom", "matched_alias": "bathroom"},
        },
        affordance_resolution={"affordance_status": "allowed_offscreen", "action_commit_policy": "commit"},
        scene_affordance_model=None,
        content_modules_root=_root(),
    )
    assert gen["success"] is True
    meta = gen["metadata"]
    assert meta.get("local_context_transition") in (None, {})
    assert meta.get("narrator_consequence_plan") in (None, {})


def test_synthetic_gen_de_locale_bathroom():
    gen = build_synthetic_generation_for_action_resolution(
        module_id=MODULE,
        lang="de",
        player_action_frame={
            "verb": "move_to",
            "action_kind": "movement",
            "resolved_target": {"target_id": "bathroom", "matched_alias": "Badezimmer"},
        },
        affordance_resolution={"affordance_status": "allowed_offscreen", "action_commit_policy": "commit"},
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        content_modules_root=_root(),
    )
    narr = gen["content"]
    assert "Stille" in narr or "Abstand" in narr or "Badezimmer" in narr, (
        f"German narrator text did not use authored DE entry detail: {narr!r}"
    )


def test_synthetic_gen_narr_not_action_restatement_for_bathroom():
    gen = build_synthetic_generation_for_action_resolution(
        module_id=MODULE,
        lang="en",
        player_action_frame={
            "verb": "move_to",
            "action_kind": "movement",
            "resolved_target": {"target_id": "bathroom", "matched_alias": "bathroom"},
        },
        affordance_resolution={"affordance_status": "allowed_offscreen", "action_commit_policy": "commit"},
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        content_modules_root=_root(),
    )
    narr = gen["content"]
    # Must NOT be the thin template that only restates the action
    assert "tension remains audible" not in narr, (
        f"Narrator still using thin move_offscreen template: {narr!r}"
    )
    assert "step aside toward" not in narr, (
        f"Narrator still using thin move_offscreen template: {narr!r}"
    )


def test_synthetic_gen_perception_not_action_restatement_for_window():
    gen = build_synthetic_generation_for_action_resolution(
        module_id=MODULE,
        lang="en",
        player_action_frame={
            "verb": "look_at",
            "action_kind": "perception",
            "resolved_target": {"target_id": "window", "matched_alias": "window"},
        },
        affordance_resolution={"affordance_status": "allowed", "action_commit_policy": "commit"},
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        content_modules_root=_root(),
    )
    narr = gen["content"]
    assert "focus your attention" not in narr, (
        f"Narrator still using thin perception_object template: {narr!r}"
    )


# ---------------------------------------------------------------------------
# Affordance availability in consequence plan
# ---------------------------------------------------------------------------


def test_hallway_affordances_in_consequence_plan():
    lct = build_local_context_transition(
        player_action_frame=_frame("move_to", "hallway", "hallway"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        current_player_local_context=None,
    )
    ncp = build_narrator_consequence_plan(
        lang="en",
        player_action_frame=_frame("move_to", "hallway", "hallway"),
        affordance_resolution=_aff("allowed"),
        scene_affordance_model=_SCENE_AFFORDANCE_MODEL,
        local_context_transition=lct,
    )
    assert "look_at" in ncp["affordances_available"]
    assert "listen_to" in ncp["affordances_available"]
