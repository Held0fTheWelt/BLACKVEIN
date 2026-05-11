"""P0 regression: action resolution via ontology + entity registry (no phrase-specific engine branches)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_stack.action_ontology import clear_action_ontology_cache
from ai_stack.player_action_resolution import resolve_player_action


@pytest.fixture(autouse=True)
def _clear_ontology_cache():
    clear_action_ontology_cache()
    yield
    clear_action_ontology_cache()


def _root() -> Path:
    return Path(__file__).resolve().parents[2] / "content" / "modules"


def _projection() -> dict:
    return {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette_reille",
        "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
        "actor_lanes": {
            "annette_reille": "human",
            "alain_reille": "npc",
            "veronique_vallon": "npc",
            "michel_longstreet": "npc",
        },
    }


def test_gehe_kueche_resolves_kitchen_offscreen() -> None:
    out = resolve_player_action(
        raw_text="Gehe in die Kueche",
        interpreted_input={
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "projection_captures": {"room": "die Kueche"},
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "move_to"
    assert frame["resolved_target_id"] == "kitchen"
    assert frame["affordance_status"] == "allowed_offscreen"


def test_begruesse_accented_name_resolves_actor() -> None:
    out = resolve_player_action(
        raw_text="Begrüße Véronique",
        interpreted_input={
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "greet"
    assert frame["resolved_target_type"] == "actor"
    assert frame["resolved_target_id"] == "veronique_vallon"


def test_mixed_stand_and_say_carries_speech_text() -> None:
    out = resolve_player_action(
        raw_text="Ich stehe auf und sage: Das reicht.",
        interpreted_input={
            "player_input_kind": "mixed",
            "narrator_response_expected": True,
            "npc_response_expected": True,
            "projection_captures": {"speech": "Das reicht."},
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["speech_text"] == "Das reicht."
    assert frame["verb"] == "stand_up"
