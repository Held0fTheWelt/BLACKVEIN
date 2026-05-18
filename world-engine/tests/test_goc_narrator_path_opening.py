from __future__ import annotations

import json
from typing import Any

from app.story_runtime import StoryRuntimeManager
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import ModelRegistry, ModelSpec, RoutingPolicy


class _ExplodingTurnGraph:
    def run(self, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("GoC Turn-0 narrator_path must not call the full turn graph")


def _explode_opening_prompt(_session: Any) -> str:
    raise AssertionError("GoC Turn-0 narrator_path must not render the model opening prompt")


class _OutputModuleAdapter(BaseModelAdapter):
    adapter_name = "test_output_module"

    def generate(
        self,
        prompt: str,
        *,
        timeout_seconds: float = 10.0,
        retrieval_context: str | None = None,
        model_name: str | None = None,
    ) -> ModelCallResult:
        if "Souffleuse output-module input:\n" in prompt:
            source = json.loads(prompt.split("Souffleuse output-module input:\n", 1)[1])
            assert source["scene_blocks"][0]["target_actor_id"] == "veronique_vallon"
            assert source["scene_blocks"][0]["source_facts"]["character_situational_stance"]
            assert source["scene_blocks"][0]["source_facts"]["character_professional_identity"]
            assert source["scene_blocks"][0]["source_facts"]["character_partner"]["name"]
            assert source["scene_blocks"][0]["source_facts"]["character_voice"]
            assert source["scene_blocks"][0]["source_facts"]["future_knowledge_policy"] == "infer_baseline_stance_only_no_future_event_disclosure"
            assert source["scene_blocks"][0]["source_facts"]["character_souffleuse_guidance"]
            assert source["scene_blocks"][0]["source_facts"]["cue_surface_policy"]["output_shape"] == "inward_footing_not_character_sheet"
            assert "pre_action_inward_footing" in source["scene_blocks"][0]["guidance_kinds"]
            assert "character_statement_pressure" not in source["scene_blocks"][0]["source_facts"]
            assert "text" not in source["scene_blocks"][0]
            payload = {
                "scene_blocks": [
                    {
                        "id": block["id"],
                        "text": (
                            "Véroniques Blick bleibt beim Laptop; Michel steht nah genug, um die Form zu halten. "
                            "Das Haus soll höflich bleiben, ohne Brunos Verletzung klein zu machen."
                        ),
                    }
                    for block in source["scene_blocks"]
                ]
            }
            return ModelCallResult(
                content=json.dumps(payload),
                success=True,
                metadata={"adapter": self.adapter_name},
            )
        source = json.loads(prompt.split("Narrator synthesis input:\n", 1)[1])
        assert source["source_input_mode"] == "semantic_frames_with_fallback_blocks"
        assert source["narrative_source_frames"]
        assert "text" not in source["scene_blocks"][0]
        assert source["scene_blocks"][0]["source_facts"]["semantic_input_language"] == "en"
        assert source["scene_blocks"][0]["source_facts"]["mandatory_beat"]["coverage_cues"]
        assert any(
            (block["source_facts"].get("transition_from_previous") or {}).get("location_changed")
            for block in source["scene_blocks"]
        )
        hard_cut_blocks = [
            block
            for block in source["scene_blocks"]
            if (block["source_facts"].get("transition_from_previous") or {})
            .get("directed_transition", {})
            .get("kind")
            == "hard_cut"
        ]
        assert [block["canonical_mandatory_beat_id"] for block in hard_cut_blocks] == ["room_perception_winter_light"]
        assert any(block.get("visual_emphasis", {}).get("kind") == "dramatic_moment" for block in source["scene_blocks"])
        payload = {
            "scene_blocks": [
                {"id": block["id"], "text": f"Synthetisierte Erzählung {index}."}
                for index, block in enumerate(source["scene_blocks"], start=1)
            ]
        }
        return ModelCallResult(content=json.dumps(payload), success=True, metadata={"adapter": self.adapter_name})


def _install_output_module(manager: StoryRuntimeManager) -> None:
    registry = ModelRegistry()
    registry.register(
        ModelSpec(
            model_name="test_output_model",
            provider="test_output",
            llm_or_slm="llm",
            timeout_seconds=5.0,
            structured_output_capable=True,
            cost_class="test",
            latency_class="test",
            use_cases=("narrative_formulation", "output_realization"),
            provider_model_name="test-output-model",
        )
    )
    manager.registry = registry
    manager.routing = RoutingPolicy(registry)
    manager.adapters = {"test_output": _OutputModuleAdapter()}


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

    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        session_output_language="en",
        trace_id="0123456789abcdef0123456789abcdef",
    )

    opening = session.diagnostics[-1]
    assert opening["turn_kind"] == "opening"
    assert opening["director_path_mode"] == "narrator_path"
    assert opening["validation_outcome"]["status"] == "approved"
    assert opening["validation_outcome"]["reason"] == "narrator_path_opening_contract_passed"

    bundle = opening["visible_output_bundle"]
    blocks = bundle["scene_blocks"]
    narrator_blocks = [block for block in blocks if block["block_type"] == "narrator"]
    souffleuse_blocks = [block for block in blocks if block["block_type"] == "souffleuse"]
    assert len(narrator_blocks) >= 6
    assert len(souffleuse_blocks) == 1
    assert {block["block_type"] for block in blocks} == {"narrator", "souffleuse"}
    assert narrator_blocks[0]["canonical_mandatory_beat_id"] == "park_edge_establishing_image"
    assert "Winter afternoon" in narrator_blocks[0]["text"]
    assert any("home office" in block["text"] for block in narrator_blocks)
    assert souffleuse_blocks[0]["visible_lane"] == "player_hint"
    assert souffleuse_blocks[0]["internal_resolution_language"] == "en"
    assert "souffleuse.situational_stance" in opening["director_narrator_path_plan"]["selected_capabilities"]

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


def test_goc_opening_de_uses_output_module_for_visible_text() -> None:
    manager = StoryRuntimeManager(governed_runtime_config=_governed_config())
    _install_output_module(manager)
    manager.turn_graph = _ExplodingTurnGraph()  # type: ignore[assignment]
    manager._build_opening_prompt = _explode_opening_prompt  # type: ignore[method-assign]

    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=_projection(),
        session_output_language="de",
        trace_id="0123456789abcdef0123456789abcdef",
    )

    opening = session.diagnostics[-1]
    blocks = opening["visible_output_bundle"]["scene_blocks"]
    narrator_blocks = [block for block in blocks if block["block_type"] == "narrator"]
    souffleuse_blocks = [block for block in blocks if block["block_type"] == "souffleuse"]

    assert narrator_blocks[0]["text"] == "Synthetisierte Erzählung 1."
    assert narrator_blocks[0]["source"] == "narrator_path_synthesis_module"
    assert len(souffleuse_blocks) == 1
    assert "Du bist" not in souffleuse_blocks[0]["text"]
    assert "Michel" in souffleuse_blocks[0]["text"]
    assert "Laptop" in souffleuse_blocks[0]["text"]
    assert "Souffleuse:" not in souffleuse_blocks[0]["text"]
    assert souffleuse_blocks[0]["speaker_label"] == "Souffleuse"
    assert souffleuse_blocks[0]["player_display_text"] == souffleuse_blocks[0]["text"]
    assert souffleuse_blocks[0]["source_before_output_module"] == "canonical_path_souffleuse_cue"
    assert souffleuse_blocks[0]["visible_output_language"] == "de"
    assert souffleuse_blocks[0]["session_output_language"] == "de"
    assert souffleuse_blocks[0]["requires_output_realization"] is False
    assert souffleuse_blocks[0]["output_realization_source"] == "souffleuse_output_module"
    realization = opening["runtime_governance_surface"]["narrator_path"]["output_realization"]
    assert realization["status"] == "synthesized"
    assert realization["session_output_language"] == "de"
    assert realization["adapter"] == "test_output_module"
    assert realization["adapter_invocation_mode"] == "narrator_path_synthesis_module"
    souffleuse_realization = opening["runtime_governance_surface"]["narrator_path"][
        "souffleuse_output_realization"
    ]
    assert souffleuse_realization["status"] == "realized"
    assert souffleuse_realization["session_output_language"] == "de"
