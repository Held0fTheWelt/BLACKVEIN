"""
MVP4 Contract 2: Opening Truthfulness

Verifies that opening turns (Turn 0) are:
1. Non-empty with visible output
2. Use the canonical narrator-path opening route rather than the player-turn graph
3. Preserve the speech-free opening boundary while allowing scripted continuation
4. Pass actor-lane validation
"""

import pytest
from app.story_runtime import StoryRuntimeManager


@pytest.fixture(autouse=True)
def _isolate_langfuse_backend_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    """These unit contracts should not wait on a live backend credential endpoint."""
    from app.observability import langfuse_adapter as lf_mod

    monkeypatch.setenv("BACKEND_RUNTIME_CONFIG_URL", "")
    monkeypatch.delenv("INTERNAL_RUNTIME_CONFIG_TOKEN", raising=False)
    lf_mod.LangfuseAdapter._instance = None
    monkeypatch.setattr(
        lf_mod.LangfuseAdapter,
        "_fetch_credentials_from_backend",
        lambda self: None,
    )


def _test_governed_story_runtime_config() -> dict:
    """Test runtime config with mock provider for testing."""
    return {
        "config_version": "cfg_world_engine_test_fixture",
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


@pytest.fixture
def runtime_manager():
    """Create a StoryRuntimeManager with test governance config."""
    manager = StoryRuntimeManager(
        governed_runtime_config=_test_governed_story_runtime_config()
    )
    manager._skip_graph_opening_on_create = False
    return manager


def _god_of_carnage_projection():
    """Build a valid God of Carnage runtime projection for testing."""
    return {
        "module_id": "god_of_carnage",
        "module_version": "1.0.0",
        "start_scene_id": "scene_1_opening",
        "runtime_profile_id": "god_of_carnage_solo",
        "runtime_module_id": "solo_story_runtime",
        "content_module_id": "god_of_carnage",
        "human_actor_id": "annette_reille",
        "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
        "actor_lanes": {
            "annette_reille": "human",
            "alain_reille": "npc",
            "veronique_vallon": "npc",
            "michel_longstreet": "npc",
        },
        "selected_player_role": "annette",
        "character_ids": ["annette_reille", "alain_reille", "veronique_vallon", "michel_longstreet"],
    }


@pytest.mark.mvp4
def test_mvp4_opening_exists_and_non_empty(runtime_manager):
    """Contract 2.1: Opening turn must exist and have non-empty visible output."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    # Opening should be in diagnostics at index 0
    assert len(session.diagnostics) > 0, "Opening turn not created"
    opening_event = session.diagnostics[0]

    # Verify opening has non-empty visible output
    assert opening_event is not None
    assert isinstance(opening_event, dict)

    visible_bundle = opening_event.get("visible_output_bundle")
    assert visible_bundle is not None, "No visible output in opening"
    assert isinstance(visible_bundle, dict)

    # Should have scene_blocks (narrative content)
    scene_blocks = visible_bundle.get("scene_blocks", [])
    assert isinstance(scene_blocks, list)
    assert len(scene_blocks) > 0, "Opening has no scene blocks"

    # Should have narrator content
    gm_narration = visible_bundle.get("gm_narration", [])
    assert isinstance(gm_narration, list)
    assert len(gm_narration) > 0, "Opening has no narrator content"


@pytest.mark.mvp4
def test_mvp4_opening_uses_canonical_narrator_path(runtime_manager):
    """Contract 2.2: speech-free opening uses the narrator path, not the player-turn graph/RAG path."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    opening_event = session.diagnostics[0]

    model_route = opening_event.get("model_route", {})
    assert model_route is not None, "No model_route in opening"

    generation = model_route.get("generation", {})
    assert generation is not None, "No generation metadata"

    metadata = generation.get("metadata", {})
    assert metadata is not None, "No generation metadata"

    adapter = metadata.get("adapter", "")
    assert adapter == "goc_narrator_path_direct"

    assert generation.get("success") is True, "Opening model generation did not succeed"
    assert generation.get("fallback_used") is False

    retrieval = opening_event.get("retrieval", {})
    assert retrieval == {}

    summary = opening_event.get("observability_path_summary", {})
    assert summary.get("selected_model") == "narrator_path_renderer"
    assert summary.get("selected_provider") == "world_engine"
    assert summary.get("director_path_mode") == "narrator_path"
    assert summary.get("narrator_path_selected") is True
    assert summary.get("route_model_called") is False
    assert summary.get("invoke_model_called") is False
    assert summary.get("retrieval_called") is False
    assert summary.get("retrieval_context_attached") is False
    assert summary.get("nodes_executed") == [
        "director.narrator_path.select",
        "narrator_path.realize",
        "souffleuse.select",
        "souffleuse.realize",
        "visible.project",
        "commit.apply",
    ]

    visible_bundle = opening_event.get("visible_output_bundle", {})
    scene_blocks = visible_bundle.get("scene_blocks", [])
    assert scene_blocks, "Opening did not project live output into scene blocks"
    assert not any(str(block.get("text") or "").lstrip().startswith("{") for block in scene_blocks)
    scene_envelope = opening_event.get("scene_turn_envelope", {})
    ldss_diag = (scene_envelope.get("diagnostics") or {}).get("live_dramatic_scene_simulator") or {}
    assert any(str(b.get("block_type")) == "narrator" for b in scene_blocks)
    assert any(str(b.get("block_type")) == "souffleuse" for b in scene_blocks)
    assert ldss_diag.get("invoked") is False, "LDSS must only run as fallback when live output fails"
    assert ldss_diag.get("status") == "not_invoked_live_graph_primary"


@pytest.mark.mvp4
def test_mvp4_opening_keeps_speech_free_narrator_boundary(runtime_manager):
    """Contract 2.3: narrator path does not require full NPC agency for Turn 0."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    opening_event = session.diagnostics[0]

    visible_bundle = opening_event.get("visible_output_bundle", {})
    assert isinstance(visible_bundle, dict), "No visible output bundle"

    scene_blocks = visible_bundle.get("scene_blocks", [])
    assert len(scene_blocks) > 0, "Opening has no scene blocks"

    gm_narration = visible_bundle.get("gm_narration", [])
    assert len(gm_narration) > 0, "Opening has no narrator content"
    assert opening_event.get("director_path_mode") == "narrator_path"
    continuation = opening_event.get("scripted_continuation") or {}
    envelope = opening_event.get("scene_turn_envelope") or {}
    if continuation.get("scene_block_count", 0) > 0:
        assert envelope.get("npc_agency_plan") is not None
    else:
        assert envelope.get("npc_agency_plan") is None


@pytest.mark.mvp4
def test_mvp4_opening_passes_validation(runtime_manager):
    """Contract 2.4: Opening must pass validation gate."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    opening_event = session.diagnostics[0]

    # Validation should be approved
    validation_outcome = opening_event.get("validation_outcome", {})
    assert isinstance(validation_outcome, dict)
    assert validation_outcome.get("status") == "approved", \
        f"Opening validation failed: {validation_outcome.get('reason')}"


@pytest.mark.mvp4
def test_mvp4_opening_has_actor_lane_context(runtime_manager):
    """Contract 2.5: Opening session includes actor lane information."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    # Session should retain actor lane information from runtime_projection
    assert session.runtime_projection.get("human_actor_id") == "annette_reille"
    assert session.runtime_projection.get("npc_actor_ids") == [
        "alain_reille",
        "veronique_vallon",
        "michel_longstreet",
    ]
    assert session.runtime_projection.get("actor_lanes") is not None

    # Verify actor lanes are properly configured
    actor_lanes = session.runtime_projection.get("actor_lanes", {})
    assert actor_lanes.get("annette_reille") == "human"
    assert actor_lanes.get("alain_reille") == "npc"
    assert actor_lanes.get("veronique_vallon") == "npc"
    assert actor_lanes.get("michel_longstreet") == "npc"


@pytest.mark.mvp4
def test_mvp4_opening_session_ready_after_create(runtime_manager):
    """Contract 2.6: Session should be ready for turns after opening succeeds."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    # Session should be in sessions dict and ready
    assert session.session_id in runtime_manager.sessions
    assert session.turn_counter == 0, "Opening should set turn_counter to 0"
    assert len(session.history) == 1, "Opening should create one historical record"
    assert len(session.diagnostics) == 1, "Opening should create exactly one diagnostic entry"
    assert session.history[0].get("turn_kind") == "opening", "Historical record should be marked as opening"


@pytest.mark.mvp4
def test_mvp4_opening_turn_number_is_zero(runtime_manager):
    """Contract 2.7: Opening turn number must be 0."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    opening_event = session.diagnostics[0]
    assert opening_event.get("turn_number") == 0, "Opening must have turn_number = 0"
    assert opening_event.get("turn_kind") == "opening", "Opening must have turn_kind = 'opening'"


@pytest.mark.mvp4
def test_mvp4_opening_turn_contains_committed_truth(runtime_manager):
    """Contract 2.8: Opening must contain committed narrative truth, not proposals."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    opening_event = session.diagnostics[0]

    # Should have committed_result indicating commit applied
    committed_result = opening_event.get("committed_result", {})
    assert isinstance(committed_result, dict)
    assert committed_result.get("commit_applied") is True, "Opening must have commit_applied=True"

    # Should have narrative_commit with scene change
    narrative_commit = opening_event.get("narrative_commit", {})
    assert isinstance(narrative_commit, dict)
    assert "committed_scene_id" in narrative_commit, "Opening must have committed_scene_id"


@pytest.mark.mvp4
def test_mvp4_opening_quality_class_is_healthy(runtime_manager):
    """Contract 2.9: Opening via narrator path should achieve healthy quality."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    opening_event = session.diagnostics[0]

    gov = opening_event.get("runtime_governance_surface", {})
    quality_class = gov.get("quality_class")
    assert quality_class in ["healthy", "approved", "degraded"], \
        f"Opening quality class unexpected: {quality_class}"


@pytest.mark.mvp4
def test_mvp4_opening_no_degradation_signals(runtime_manager):
    """Contract 2.10: Opening via narrator path should have no degradation signals."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    opening_event = session.diagnostics[0]

    gov = opening_event.get("runtime_governance_surface", {})
    degradation_signals = gov.get("degradation_signals", [])
    assert isinstance(degradation_signals, list)
    benign_opening = {"non_factual_staging", "ldss_fallback_after_live_opening_failure"}
    unknown = [s for s in degradation_signals if s not in benign_opening]
    assert not unknown, f"Unexpected opening degradation signals: {degradation_signals}"


@pytest.mark.mvp4
def test_mvp4_direct_session_create_requires_actor_ownership_contract(runtime_manager):
    """Contract 2.11: direct WE session creation must reject missing GoC actor ownership."""
    projection = {
        "module_id": "god_of_carnage",
        "module_version": "1.0.0",
        "start_scene_id": "scene_1_opening",
        "selected_player_role": "veronique",
    }

    with pytest.raises(ValueError, match="human_actor_id"):
        runtime_manager.create_session(
            module_id="god_of_carnage",
            runtime_projection=projection,
        )
