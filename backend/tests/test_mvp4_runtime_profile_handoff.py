from __future__ import annotations

from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.mvp_handoff


def _handoff(**overrides):
    data = {
        "contract": "create_run_response.v1",
        "content_module_id": "god_of_carnage",
        "runtime_profile_id": "god_of_carnage_solo",
        "runtime_module_id": "solo_story_runtime",
        "runtime_mode": "solo_story",
        "selected_player_role": "annette",
        "human_actor_id": "annette",
        "npc_actor_ids": ["alain", "veronique", "michel"],
        "actor_lanes": {
            "annette": "human",
            "alain": "npc",
            "veronique": "npc",
            "michel": "npc",
        },
        "visitor_present": False,
        "content_hash": "sha256:test",
    }
    data.update(overrides)
    return data


def _compiled_projection():
    return {
        "module_id": "god_of_carnage",
        "module_version": "0.1.0",
        "start_scene_id": "scene_1",
        "character_ids": ["annette", "alain", "veronique", "michel"],
    }


@pytest.mark.mvp4
def test_compile_player_module_preserves_authoritative_runtime_profile_handoff(monkeypatch):
    from app.api.v1 import game_routes

    class RuntimeProjection:
        def model_dump(self, mode: str):
            assert mode == "json"
            return _compiled_projection()

    monkeypatch.setattr(game_routes, "resolve_canonical_module_id_for_template", lambda _template_id: "god_of_carnage")
    monkeypatch.setattr(game_routes, "compile_module", lambda _module_id: SimpleNamespace(runtime_projection=RuntimeProjection()))

    module_id, runtime_projection, provenance = game_routes._compile_player_module(
        "god_of_carnage_solo",
        runtime_profile_handoff=_handoff(),
    )

    assert module_id == "god_of_carnage"
    assert runtime_projection["content_module_id"] == "god_of_carnage"
    assert runtime_projection["runtime_profile_id"] == "god_of_carnage_solo"
    assert runtime_projection["runtime_module_id"] == "solo_story_runtime"
    assert runtime_projection["selected_player_role"] == "annette"
    assert runtime_projection["human_actor_id"] == "annette"
    assert runtime_projection["npc_actor_ids"] == ["alain", "veronique", "michel"]
    assert runtime_projection["actor_lanes"]["annette"] == "human"
    assert "visitor" not in runtime_projection["actor_lanes"]
    assert provenance["runtime_profile_handoff"]["runtime_profile_id"] == "god_of_carnage_solo"


@pytest.mark.mvp4
def test_runtime_profile_handoff_rejects_visitor_actor():
    from app.api.v1 import game_routes
    from app.services.game_service import GameServiceError

    with pytest.raises(GameServiceError, match="visitor"):
        game_routes._runtime_profile_handoff_from_run_payload(
            _handoff(
                npc_actor_ids=["alain", "visitor"],
                actor_lanes={"annette": "human", "alain": "npc", "visitor": "npc"},
            )
        )


@pytest.mark.mvp4
def test_runtime_profile_handoff_rejects_content_module_mismatch():
    from app.api.v1 import game_routes
    from app.services.game_service import GameServiceError

    with pytest.raises(GameServiceError, match="does not match compiled module"):
        game_routes._merge_runtime_profile_handoff(
            _compiled_projection(),
            module_id="god_of_carnage",
            handoff=_handoff(content_module_id="god_of_carnage_solo"),
        )
