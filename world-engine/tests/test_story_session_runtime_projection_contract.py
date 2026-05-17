from __future__ import annotations

import pytest

from app.story_runtime.manager import StorySessionContractError, _validate_runtime_projection_contract


def _projection_for(
    *,
    selected_player_role: str,
    human_actor_id: str,
    npc_actor_ids: list[str],
) -> dict:
    return {
        "module_id": "god_of_carnage",
        "start_scene_id": "apartment_arrival",
        "selected_player_role": selected_player_role,
        "human_actor_id": human_actor_id,
        "npc_actor_ids": npc_actor_ids,
        "actor_lanes": {
            human_actor_id: "human",
            **{actor_id: "npc" for actor_id in npc_actor_ids},
        },
    }


def test_runtime_projection_accepts_role_slug_resolving_to_human_actor_id() -> None:
    projection = _projection_for(
        selected_player_role="annette",
        human_actor_id="annette_reille",
        npc_actor_ids=["alain_reille", "veronique_vallon", "michel_longstreet"],
    )

    _validate_runtime_projection_contract("god_of_carnage", projection)


def test_runtime_projection_rejects_role_slug_resolving_to_different_human_actor_id() -> None:
    projection = _projection_for(
        selected_player_role="annette",
        human_actor_id="alain_reille",
        npc_actor_ids=["annette_reille", "veronique_vallon", "michel_longstreet"],
    )

    with pytest.raises(StorySessionContractError, match="resolve to human_actor_id"):
        _validate_runtime_projection_contract("god_of_carnage", projection)


def test_runtime_projection_rejects_human_actor_in_npc_list_by_content_alias() -> None:
    projection = _projection_for(
        selected_player_role="annette",
        human_actor_id="annette_reille",
        npc_actor_ids=["annette", "alain_reille", "veronique_vallon", "michel_longstreet"],
    )

    with pytest.raises(StorySessionContractError, match="human_actor_id cannot also appear"):
        _validate_runtime_projection_contract("god_of_carnage", projection)
