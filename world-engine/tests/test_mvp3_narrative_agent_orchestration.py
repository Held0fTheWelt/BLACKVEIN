"""
Phase 3 (Days 5-6): Story Runtime Manager orchestration tests.

Tests the integration of NarrativeRuntimeAgent into StoryRuntimeManager
after LDSS execution, including input queuing and ruhepunkt detection.
"""

import pytest
from unittest.mock import MagicMock, patch

from story_runtime_core import ModelRegistry
from app.story_runtime.manager import (
    StoryRuntimeManager,
    StorySession,
    _orchestrate_narrative_agent,
    _check_ruhepunkt_signal,
    _process_input_queue,
)
from ai_stack.narrative import NarrativeRuntimeAgent, NarrativeEventKind


@pytest.fixture
def story_manager():
    """Create StoryRuntimeManager for testing."""
    return StoryRuntimeManager(registry=ModelRegistry(), adapters={})


@pytest.fixture
def sample_session():
    """Create a sample story session."""
    return StorySession(
        session_id="test_session_001",
        module_id="god_of_carnage",
        runtime_projection={
            "module_id": "god_of_carnage",
            "start_scene_id": "living_room",
            "human_actor_id": "you",
            "npc_actor_ids": ["annette", "alain"],
        },
    )


@pytest.fixture
def sample_ldss_output():
    """Sample LDSS output with NPC agency plan."""
    return {
        "visible_scene_output": {
            "blocks": [
                {
                    "id": "block_1",
                    "block_type": "actor_line",
                    "actor_id": "annette",
                    "text": "I disagree with your assessment.",
                }
            ]
        },
        "decision_count": 1,
        "scene_block_count": 1,
        "visible_actor_response_present": True,
        "npc_agency_plan": {
            "primary_responder_id": "annette",
            "secondary_responder_ids": ["alain"],
            "initiatives": [
                {"actor_id": "alain", "initiative_type": "challenge", "resolved": False},
            ],
        },
        "ldss_invoked": True,
        "legacy_blob_used": False,
    }


class TestNarrativeAgentOrchestration:
    """Test Phase 3 orchestration of NarrativeRuntimeAgent."""

    def test_orchestrate_narrative_agent_starts_streaming(self, story_manager):
        """_orchestrate_narrative_agent starts streaming when LDSS output valid."""
        started = _orchestrate_narrative_agent(
            manager=story_manager,
            session_id="test_session_001",
            ldss_output={
                "npc_agency_plan": {"initiatives": [{"actor_id": "npc1", "resolved": False}]}
            },
            runtime_state={"scene_id": "test"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )
        assert started is True
        assert "test_session_001" in story_manager.narrative_agents

    def test_orchestrate_narrative_agent_returns_false_without_ldss(self, story_manager):
        """_orchestrate_narrative_agent returns False when LDSS output missing."""
        started = _orchestrate_narrative_agent(
            manager=story_manager,
            session_id="test_session_001",
            ldss_output=None,
            runtime_state={"scene_id": "test"},
            dramatic_signature={},
            narrative_threads=[],
            turn_number=1,
        )
        assert started is False

    def test_check_ruhepunkt_signal_works(self, story_manager):
        """_check_ruhepunkt_signal detects ruhepunkt condition."""
        # Start streaming (streaming active = True)
        story_manager._narrative_streaming_active["test_session"] = True
        agent = NarrativeRuntimeAgent()
        story_manager.narrative_agents["test_session"] = agent

        # While streaming, ruhepunkt is not reached
        assert _check_ruhepunkt_signal(story_manager, "test_session") is False

        # When streaming stops, ruhepunkt is reached
        story_manager._narrative_streaming_active["test_session"] = False
        assert _check_ruhepunkt_signal(story_manager, "test_session") is True

    def test_process_input_queue_returns_and_clears(self, story_manager):
        """_process_input_queue returns queued inputs and clears queue."""
        session_id = "test_session"
        story_manager.input_queues[session_id] = ["input1", "input2", "input3"]

        # Get and clear queue
        inputs = _process_input_queue(story_manager, session_id)
        assert inputs == ["input1", "input2", "input3"]
        assert story_manager.input_queues[session_id] == []


class TestInputQueueing:
    """Test input queuing while narrator is streaming."""

    def test_queue_player_input(self, story_manager):
        """Player input is queued when narrator is streaming."""
        session_id = "test_session"
        story_manager.queue_player_input(session_id, "player says hello")
        story_manager.queue_player_input(session_id, "player asks why")

        assert story_manager.input_queues[session_id] == ["player says hello", "player asks why"]

    def test_get_queued_inputs_clears_queue(self, story_manager):
        """get_queued_inputs returns and clears queue."""
        session_id = "test_session"
        story_manager.queue_player_input(session_id, "input1")
        story_manager.queue_player_input(session_id, "input2")

        inputs = story_manager.get_queued_inputs(session_id)
        assert inputs == ["input1", "input2"]
        assert story_manager.get_queued_inputs(session_id) == []

    def test_is_narrative_streaming(self, story_manager):
        """is_narrative_streaming correctly reflects streaming state."""
        session_id = "test_session"

        # Initially not streaming
        assert story_manager.is_narrative_streaming(session_id) is False

        # Start streaming
        story_manager._narrative_streaming_active[session_id] = True
        assert story_manager.is_narrative_streaming(session_id) is True

        # Stop streaming
        story_manager._narrative_streaming_active[session_id] = False
        assert story_manager.is_narrative_streaming(session_id) is False


class TestTracingConfig:
    """Test Langfuse tracing configuration (MVP3 vs MVP4)."""

    def test_get_tracing_config_returns_false_mvp3(self, story_manager):
        """_get_tracing_config returns False in MVP3 (deferred to MVP4)."""
        config = story_manager._get_tracing_config("test_session")
        assert config is False

    def test_tracing_config_consistent_across_sessions(self, story_manager):
        """Tracing config is consistently False for all sessions in MVP3."""
        for session_id in ["session1", "session2", "session3"]:
            assert story_manager._get_tracing_config(session_id) is False


@pytest.mark.mvp3
class TestMVP3OrchestrationGate:
    """MVP3 gate verification for narrative agent orchestration."""

    def test_mvp3_narrative_agent_orchestration_available(self, story_manager, sample_ldss_output):
        """Gate: NarrativeRuntimeAgent can be orchestrated after LDSS."""
        result = _orchestrate_narrative_agent(
            manager=story_manager,
            session_id="test_session",
            ldss_output=sample_ldss_output,
            runtime_state={"scene_id": "test"},
            dramatic_signature={"tension": "high"},
            narrative_threads=[],
            turn_number=1,
        )
        assert result is True

    def test_mvp3_input_queuing_works(self, story_manager):
        """Gate: Player input can be queued while narrator streams."""
        session_id = "test_session"
        story_manager._narrative_streaming_active[session_id] = True

        story_manager.queue_player_input(session_id, "test input 1")
        story_manager.queue_player_input(session_id, "test input 2")

        assert len(story_manager.input_queues[session_id]) == 2

    def test_mvp3_ruhepunkt_detection_works(self, story_manager):
        """Gate: Ruhepunkt signal correctly detects when input can be processed."""
        session_id = "test_session"
        agent = NarrativeRuntimeAgent()
        story_manager.narrative_agents[session_id] = agent

        # Start streaming
        story_manager._narrative_streaming_active[session_id] = True
        assert _check_ruhepunkt_signal(story_manager, session_id) is False

        # Streaming ends -> ruhepunkt reached -> input can be processed
        story_manager._narrative_streaming_active[session_id] = False
        assert _check_ruhepunkt_signal(story_manager, session_id) is True

    def test_mvp3_orchestration_integrates_with_manager(self, story_manager):
        """Gate: Orchestration methods work with StoryRuntimeManager instance."""
        # Queue some inputs
        story_manager.queue_player_input("session1", "input1")
        story_manager.queue_player_input("session1", "input2")

        # Check streaming state
        assert story_manager.is_narrative_streaming("session1") is False

        # Get config
        config = story_manager._get_tracing_config("session1")
        assert config is False

        # Retrieve queued inputs
        inputs = story_manager.get_queued_inputs("session1")
        assert len(inputs) == 2
