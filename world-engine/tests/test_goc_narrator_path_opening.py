from __future__ import annotations

from typing import Any

from app.story_runtime import StoryRuntimeManager


class _ExplodingTurnGraph:
    def run(self, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("GoC Turn-0 narrator_path must not call the full turn graph")


def _explode_opening_prompt(_session: Any) -> str:
    raise AssertionError("GoC Turn-0 narrator_path must not render the model opening prompt")


def _governed_config() -> dict[str, Any]:
    return {
        "config_version": "cfg_test_narrator_path",
        "generation_execution_mode": "mock_only",
        "providers": [{"provider_id": "mock_default", "provider_type": "mock"}],
        "models": [
            {
                "model_id": "mock_deterministic",
                "provider_id": "mock_default",
                "model_name": "mock-deterministic",
                "model_role": "mock",
                "timeout_seconds": 5,
                "structured_output_capable": True,
            }
        ],
        "routes": [
            {
                "route_id": "narrative_live_generation_global",
                "preferred_model_id": "mock_deterministic",
                "fallback_model_id": "mock_deterministic",
                "mock_model_id": "mock_deterministic",
            }
        ],
    }


def _projection() -> dict[str, Any]:
    return {
        "module_id": "god_of_carnage",
        "module_version": "1.0.0",
        "start_scene_id": "scene_1_opening",
        "human_actor_id": "veronique",
        "npc_actor_ids": ["michel", "annette", "alain"],
        "actor_lanes": {
            "veronique": "human",
            "michel": "npc",
            "annette": "npc",
            "alain": "npc",
        },
        "selected_player_role": "veronique",
        "character_ids": ["veronique", "michel", "annette", "alain"],
        "runtime_profile_id": "god_of_carnage_solo",
        "runtime_module_id": "solo_story_runtime",
        "content_module_id": "god_of_carnage",
    }


def test_goc_opening_uses_narrator_path_without_full_turn_graph() -> None:
    manager = StoryRuntimeManager(governed_runtime_config=_governed_config())
    manager.turn_graph = _ExplodingTurnGraph()  # type: ignore[assignment]
    manager._build_opening_prompt = _explode_opening_prompt  # type: ignore[method-assign]

    session = manager.create_session_proto(
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        session_output_language="de",
        trace_id="0123456789abcdef0123456789abcdef",
    )

    opening = session.diagnostics[-1]
    assert opening["turn_kind"] == "opening"
    assert opening["director_path_mode"] == "narrator_path"
    assert opening["validation_outcome"]["status"] == "approved"
    assert opening["validation_outcome"]["reason"] == "narrator_path_opening_contract_passed"

    bundle = opening["visible_output_bundle"]
    blocks = bundle["scene_blocks"]
    assert len(blocks) >= 5
    assert {block["block_type"] for block in blocks} == {"narrator"}
    assert "Parc Montsouris" in blocks[0]["text"]
    assert "Arbeitszimmer" in blocks[-1]["text"]

    route = opening["model_route"]
    generation = route["generation"]
    assert generation["metadata"]["adapter"] == "goc_narrator_path_direct"
    assert generation["fallback_used"] is False
    assert opening["retrieval"] == {}
    assert opening["selected_responder_set"] == []

    envelope = opening["scene_turn_envelope"]
    assert envelope["npc_agency_plan"] is None
    assert envelope["diagnostics"]["npc_agency"]["npc_agency_plan_built"] is False
    assert opening["runtime_governance_surface"]["director_path_mode"] == "narrator_path"
