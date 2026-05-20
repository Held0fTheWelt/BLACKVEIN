"""P0 regression: action resolution requires AI semantics and content grounding."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_stack.player_action_resolution import resolve_player_action
from ai_stack.language_io.language_adapter import clear_language_adapter_caches


@pytest.fixture(autouse=True)
def _clear_language_adapter_cache():
    clear_language_adapter_caches()
    yield
    clear_language_adapter_caches()


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


def _semantic(
    *,
    raw_kind: str = "action",
    verb: str,
    action_kind: str,
    target_query: str | None,
    target_id: str | None,
    target_type: str | None,
    source_query: str | None = None,
    source_id: str | None = None,
    actor_id: str = "annette_reille",
    commit_policy: str = "commit_action",
) -> dict:
    payload = {
        "player_input_kind": raw_kind,
        "verb": verb,
        "action_kind": action_kind,
        "target_query": target_query,
        "resolved_target_id": target_id,
        "resolved_target_type": target_type,
        "source_query": source_query,
        "resolved_source_id": source_id,
        "commit_policy": commit_policy,
        "confidence": "high" if target_id else "low",
    }
    return {
        "player_input_kind": raw_kind,
        "narrator_response_expected": True,
        "npc_response_expected": False,
        "actor_id": actor_id,
        "semantic_action": payload,
    }


def test_raw_movement_without_semantic_payload_does_not_guess_kitchen() -> None:
    out = resolve_player_action(
        raw_text="Gehe in die Kueche",
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
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "ambiguous"
    assert aff["target_resolution_source"] == "semantic_ai_resolution_required"


def test_ai_semantics_resolve_kitchen_against_content_surface() -> None:
    out = resolve_player_action(
        raw_text="Gehe in die Kueche",
        interpreted_input=_semantic(
            verb="move_to",
            action_kind="movement",
            target_query="Kueche",
            target_id="kitchen",
            target_type="location",
        ),
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "move_to"
    assert frame["resolved_target_id"] == "kitchen"
    assert frame["target_resolution_source"] == "ai_semantic_resolution.content_id"


def test_ai_semantics_resolve_prevented_stairwell_without_forbidden_map() -> None:
    out = resolve_player_action(
        raw_text="Gehe ins Treppenhaus",
        interpreted_input=_semantic(
            verb="move_to",
            action_kind="movement",
            target_query="Treppenhaus",
            target_id="building_stairwell",
            target_type="location",
            actor_id="alain_reille",
            commit_policy="no_commit",
        ),
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "prevented"
    assert aff["action_commit_policy"] == "no_commit"


def test_ai_semantics_resolve_actor_from_runtime_roster() -> None:
    out = resolve_player_action(
        raw_text="Begrüße Véronique",
        interpreted_input=_semantic(
            verb="greet",
            action_kind="social_nonverbal_action",
            target_query="Véronique",
            target_id="veronique_vallon",
            target_type="actor",
        ),
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "greet"
    assert frame["resolved_target_type"] == "actor"
    assert frame["resolved_target_id"] == "veronique_vallon"


def test_source_resolution_uses_ai_provided_content_id() -> None:
    out = resolve_player_action(
        raw_text="Ich nehme ein Glas aus dem Schrank",
        interpreted_input=_semantic(
            verb="take",
            action_kind="object_interaction",
            target_query="Glas",
            target_id="glasses",
            target_type="object",
            source_query="Schrank",
            source_id="glassware_cabinet",
        ),
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["resolved_target_id"] == "glasses"
    assert frame["resolved_source_id"] == "glassware_cabinet"
    assert frame["source_resolution_source"] == "ai_semantic_resolution.content_id"


def test_unknown_ai_target_query_stays_clarification() -> None:
    out = resolve_player_action(
        raw_text="Schalte den Hyperraum ein",
        interpreted_input=_semantic(
            verb="activate",
            action_kind="object_interaction",
            target_query="Hyperraum",
            target_id=None,
            target_type=None,
        ),
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "unknown_target"
    assert aff["action_commit_policy"] == "needs_clarification"


def test_mixed_action_speech_uses_ai_semantic_speech_text() -> None:
    out = resolve_player_action(
        raw_text="Ich stehe auf und sage: Das reicht.",
        interpreted_input={
            **_semantic(
                raw_kind="mixed",
                verb="stand_up",
                action_kind="movement",
                target_query=None,
                target_id=None,
                target_type=None,
            ),
            "semantic_action": {
                "player_input_kind": "mixed",
                "verb": "stand_up",
                "action_kind": "movement",
                "speech_text": "Das reicht.",
                "commit_policy": "commit_action",
            },
        },
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        content_modules_root=_root(),
    )
    frame = out["player_action_frame"]
    assert frame["speech_text"] == "Das reicht."
    assert frame["verb"] == "stand_up"
