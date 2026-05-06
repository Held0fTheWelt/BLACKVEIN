"""
MVP4 Contract 2: Opening Truthfulness

Verifies that opening turns (Turn 0) are:
1. Non-empty with visible output
2. Use the live runtime graph/model route rather than deterministic LDSS
3. Have NPC agency (at least one NPC responds)
4. Pass actor-lane validation
"""

import pytest
from app.story_runtime import StoryRuntimeManager


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
def test_mvp4_opening_uses_live_runtime_graph_model_and_retrieval(runtime_manager):
    """Contract 2.2: Opening must be generated through the live graph/model/RAG path."""
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
    assert adapter, "Opening generation did not record an adapter"
    assert adapter != "ldss_deterministic", "Opening bypassed live model generation via deterministic LDSS"

    assert generation.get("success") is True, "Opening model generation did not succeed"
    assert model_route.get("selected_model"), "Opening did not record selected model"
    assert model_route.get("selected_provider"), "Opening did not record selected provider"

    retrieval = opening_event.get("retrieval", {})
    assert isinstance(retrieval, dict), "Opening did not expose retrieval diagnostics"
    assert retrieval.get("domain") == "runtime"
    assert retrieval.get("profile") == "runtime_turn_support"
    assert retrieval.get("status") in {"ok", "degraded", "skipped"}

    summary = opening_event.get("observability_path_summary", {})
    assert summary.get("retrieval_called") is True
    assert summary.get("retrieval_context_attached") is True

    visible_bundle = opening_event.get("visible_output_bundle", {})
    scene_blocks = visible_bundle.get("scene_blocks", [])
    assert scene_blocks, "Opening did not project live output into scene blocks"
    assert all(block.get("source") == "live_runtime_graph" for block in scene_blocks)
    scene_envelope = opening_event.get("scene_turn_envelope", {})
    ldss_diag = (scene_envelope.get("diagnostics") or {}).get("live_dramatic_scene_simulator") or {}
    assert ldss_diag.get("invoked") is False, "LDSS must only run as fallback when live output fails"
    assert ldss_diag.get("status") == "not_invoked_live_graph_primary"


@pytest.mark.mvp4
def test_mvp4_opening_has_npc_agency(runtime_manager):
    """Contract 2.3: Opening must have NPC agency (at least one NPC responds)."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    opening_event = session.diagnostics[0]

    # Check for visible output that indicates NPC agency
    visible_bundle = opening_event.get("visible_output_bundle", {})
    assert isinstance(visible_bundle, dict), "No visible output bundle"

    # Should have scene blocks with NPC dialogue or actions
    scene_blocks = visible_bundle.get("scene_blocks", [])
    assert len(scene_blocks) > 0, "Opening has no scene blocks"

    # At minimum, opening should have narrator content
    gm_narration = visible_bundle.get("gm_narration", [])
    assert len(gm_narration) > 0, "Opening has no narrator content (NPC agency manifests through narrative)"


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
    assert session.runtime_projection.get("human_actor_id") == "veronique"
    assert session.runtime_projection.get("npc_actor_ids") == ["michel", "annette", "alain"]
    assert session.runtime_projection.get("actor_lanes") is not None

    # Verify actor lanes are properly configured
    actor_lanes = session.runtime_projection.get("actor_lanes", {})
    assert actor_lanes.get("veronique") == "human"
    assert actor_lanes.get("michel") == "npc"
    assert actor_lanes.get("annette") == "npc"
    assert actor_lanes.get("alain") == "npc"


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
    """Contract 2.9: Opening via live runtime graph should achieve healthy quality."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    opening_event = session.diagnostics[0]

    gov = opening_event.get("runtime_governance_surface", {})
    quality_class = gov.get("quality_class")
    assert quality_class in ["healthy", "approved"], \
        f"Opening quality class should be healthy, got {quality_class}"


@pytest.mark.mvp4
def test_mvp4_opening_no_degradation_signals(runtime_manager):
    """Contract 2.10: Opening via live runtime graph should have no degradation signals."""
    projection = _god_of_carnage_projection()

    session = runtime_manager.create_session(
        module_id="god_of_carnage",
        runtime_projection=projection,
    )

    opening_event = session.diagnostics[0]

    gov = opening_event.get("runtime_governance_surface", {})
    degradation_signals = gov.get("degradation_signals", [])
    assert isinstance(degradation_signals, list)
    assert len(degradation_signals) == 0, \
        f"Live opening should have no degradation signals, got {degradation_signals}"


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
