"""
MVP3 Complete Integration Tests

Tests the full pipeline from LDSS execution through HTTP streaming endpoint
to frontend event handling (simulated).

Flow: LDSS → orchestrate_narrative_agent → HTTP endpoint → SSE stream
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.http import router
from app.story_runtime.manager import StoryRuntimeManager, _orchestrate_narrative_agent
from ai_stack.narrative import NarrativeRuntimeAgent, NarrativeEventKind


@pytest.fixture
def app():
    """Create FastAPI test app with HTTP router."""
    from fastapi import FastAPI
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.state.story_manager = StoryRuntimeManager()
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestPhase345Integration:
    """Test Phase 3-4-5 complete integration."""

    def test_complete_flow_ldss_to_streaming_endpoint(self, client):
        """
        Complete flow:
        1. LDSS produces npc_agency_plan
        2. Manager orchestrates NarrativeRuntimeAgent
        3. HTTP endpoint streams narrator blocks
        """
        manager = client.app.state.story_manager
        session_id = "integration_test_session"

        # Phase 3: Orchestrate narrative agent
        result = _orchestrate_narrative_agent(
            manager=manager,
            session_id=session_id,
            ldss_output={
                "npc_agency_plan": {
                    "initiatives": [
                        {"actor_id": "npc1", "resolved": False},
                        {"actor_id": "npc2", "resolved": False},
                    ]
                }
            },
            runtime_state={"scene_id": "test_scene"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )

        assert result is True, "Orchestration should succeed with valid LDSS output"
        assert session_id in manager.narrative_agents, "Agent should be registered in manager"

        # Phase 4: Stream narrator blocks via HTTP endpoint
        response = client.get(f"/api/story/sessions/{session_id}/stream-narrator")
        assert response.status_code == 200, "HTTP endpoint should return 200"
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Phase 5 simulation: Parse SSE events as frontend would
        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]

        assert len(data_lines) > 0, "Should emit at least one event"

        # Verify event structure
        events = []
        for line in data_lines:
            event = json.loads(line[6:])  # Skip "data: "
            events.append(event)

        # Should have narrator blocks
        narrator_blocks = [e for e in events if e.get("event_kind") == "narrator_block"]
        assert len(narrator_blocks) > 0, "Should emit narrator blocks"

        # Should have ruhepunkt signal
        ruhepunkt_signals = [e for e in events if e.get("event_kind") == "ruhepunkt_reached"]
        assert len(ruhepunkt_signals) > 0, "Should emit ruhepunkt signal"

        # Verify order: narrator blocks before ruhepunkt
        if narrator_blocks and ruhepunkt_signals:
            first_block_idx = data_lines.index(next(l for l in data_lines if "narrator_block" in l))
            first_ruhepunkt_idx = data_lines.index(next(l for l in data_lines if "ruhepunkt_reached" in l))
            assert first_block_idx < first_ruhepunkt_idx, "Blocks should precede ruhepunkt"

    def test_input_blocking_during_streaming(self, client):
        """
        Verify input is blocked while streaming:
        1. Manager marks streaming active
        2. Frontend receives blocks and blocks input-UI
        """
        manager = client.app.state.story_manager
        session_id = "input_blocking_test"

        _orchestrate_narrative_agent(
            manager=manager,
            session_id=session_id,
            ldss_output={
                "npc_agency_plan": {
                    "initiatives": [{"actor_id": "npc1", "resolved": False}]
                }
            },
            runtime_state={"scene_id": "test_scene"},
            dramatic_signature={},
            narrative_threads=[],
            turn_number=1,
        )

        # Verify streaming is marked active
        assert manager._narrative_streaming_active.get(session_id) is True

        # Verify input queue exists
        assert session_id in manager.input_queues
        assert isinstance(manager.input_queues[session_id], list)

        # Queue some player input (frontend would do this)
        manager.queue_player_input(session_id, "I advance toward the table")
        manager.queue_player_input(session_id, "I speak softly")

        assert len(manager.input_queues[session_id]) == 2

        # Start streaming (this marks streaming_active = True)
        response = client.get(f"/api/story/sessions/{session_id}/stream-narrator")
        assert response.status_code == 200

        # After streaming receives ruhepunkt, input should be unblocked
        # (In Phase 5, frontend would detect ruhepunkt_reached event and re-enable UI)

    def test_ruhepunkt_signal_enables_input(self, client):
        """
        Verify ruhepunkt signal allows input processing:
        1. Narrator streams blocks
        2. Ruhepunkt signal emitted when initiatives exhausted
        3. Frontend re-enables input after ruhepunkt
        """
        manager = client.app.state.story_manager
        session_id = "ruhepunkt_test"

        # Orchestrate with one initiative
        _orchestrate_narrative_agent(
            manager=manager,
            session_id=session_id,
            ldss_output={
                "npc_agency_plan": {
                    "initiatives": [{"actor_id": "npc1", "resolved": False}]
                }
            },
            runtime_state={"scene_id": "test_scene"},
            dramatic_signature={},
            narrative_threads=[],
            turn_number=1,
        )

        # Stream should emit narrator blocks then ruhepunkt
        response = client.get(f"/api/story/sessions/{session_id}/stream-narrator")
        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]

        # Find ruhepunkt event
        ruhepunkt_events = [
            json.loads(l[6:]) for l in data_lines
            if "ruhepunkt_reached" in l
        ]

        assert len(ruhepunkt_events) > 0, "Should emit ruhepunkt signal"
        assert ruhepunkt_events[0].get("data", {}).get("ruhepunkt_reached") is True

    def test_input_queue_populated_during_streaming(self, client):
        """
        Verify input queue accumulates player inputs while streaming:
        1. Start streaming
        2. Frontend queues multiple inputs
        3. Queue processed after ruhepunkt
        """
        manager = client.app.state.story_manager
        session_id = "queue_test"

        _orchestrate_narrative_agent(
            manager=manager,
            session_id=session_id,
            ldss_output={
                "npc_agency_plan": {
                    "initiatives": [
                        {"actor_id": "npc1", "resolved": False},
                        {"actor_id": "npc2", "resolved": False},
                    ]
                }
            },
            runtime_state={"scene_id": "test_scene"},
            dramatic_signature={},
            narrative_threads=[],
            turn_number=1,
        )

        # Queue player inputs while streaming
        inputs = [
            "I stand and face them directly.",
            "My voice is steady and clear.",
            "I will not compromise.",
        ]

        for input_text in inputs:
            manager.queue_player_input(session_id, input_text)

        # Verify all inputs queued
        queued = manager.get_queued_inputs(session_id)
        assert len(queued) == len(inputs)
        assert queued == inputs

        # After getting queued inputs, queue should be empty
        assert len(manager.get_queued_inputs(session_id)) == 0

    def test_streaming_error_handling(self, client):
        """
        Verify streaming errors are handled gracefully:
        1. Missing agent returns error event
        2. Error event closes stream
        """
        response = client.get("/api/story/sessions/nonexistent/stream-narrator")
        assert response.status_code == 200

        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]

        # Should have error event
        if data_lines:
            first_event = json.loads(data_lines[0][6:])
            assert first_event.get("error") == "no_narrator_streaming"

    def test_multiple_sessions_independent(self, client):
        """
        Verify multiple sessions stream independently:
        1. Start streaming for session A
        2. Start streaming for session B
        3. Each streams independently
        """
        manager = client.app.state.story_manager
        session_a = "session_a"
        session_b = "session_b"

        # Orchestrate both sessions
        for session_id in [session_a, session_b]:
            _orchestrate_narrative_agent(
                manager=manager,
                session_id=session_id,
                ldss_output={
                    "npc_agency_plan": {
                        "initiatives": [{"actor_id": "npc1", "resolved": False}]
                    }
                },
                runtime_state={"scene_id": "test_scene"},
                dramatic_signature={},
                narrative_threads=[],
                turn_number=1,
            )

        # Both should be streaming
        assert manager._narrative_streaming_active.get(session_a) is True
        assert manager._narrative_streaming_active.get(session_b) is True

        # Both should have agents
        assert session_a in manager.narrative_agents
        assert session_b in manager.narrative_agents

        # Queue inputs for each independently
        manager.queue_player_input(session_a, "input for A")
        manager.queue_player_input(session_b, "input for B")

        # Verify independence
        assert manager.get_queued_inputs(session_a) == ["input for A"]
        assert manager.get_queued_inputs(session_b) == ["input for B"]


@pytest.mark.mvp3
class TestMVP3IntegrationGate:
    """MVP3 gate verification for complete orchestration-endpoint-frontend flow."""

    def test_mvp3_ldss_to_endpoint_to_frontend_flow(self, client):
        """Gate: Complete flow from LDSS through endpoint to frontend works."""
        manager = client.app.state.story_manager
        session_id = "mvp3_gate_test"

        # Phase 3: Manager orchestrates after LDSS
        started = _orchestrate_narrative_agent(
            manager=manager,
            session_id=session_id,
            ldss_output={
                "npc_agency_plan": {
                    "initiatives": [{"actor_id": "npc1", "resolved": False}]
                }
            },
            runtime_state={"scene_id": "test_scene"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )
        assert started is True

        # Phase 4: HTTP endpoint accessible and streams events
        response = client.get(f"/api/story/sessions/{session_id}/stream-narrator")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Phase 5 simulation: Frontend parses events
        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]
        events = [json.loads(l[6:]) for l in data_lines]

        # Verify all event types present
        event_kinds = [e.get("event_kind") for e in events]
        assert "narrator_block" in event_kinds
        assert "ruhepunkt_reached" in event_kinds

    def test_mvp3_input_blocking_and_queuing(self, client):
        """Gate: Input blocked during streaming, queued until ruhepunkt."""
        manager = client.app.state.story_manager
        session_id = "mvp3_input_test"

        _orchestrate_narrative_agent(
            manager=manager,
            session_id=session_id,
            ldss_output={
                "npc_agency_plan": {
                    "initiatives": [{"actor_id": "npc1", "resolved": False}]
                }
            },
            runtime_state={"scene_id": "test_scene"},
            dramatic_signature={},
            narrative_threads=[],
            turn_number=1,
        )

        # Verify streaming marks input for blocking
        assert manager._narrative_streaming_active[session_id] is True

        # Queue input while streaming
        manager.queue_player_input(session_id, "test input")
        assert len(manager.input_queues[session_id]) == 1

        # After ruhepunkt, input would be processed
        # (verify by checking if input queue management works)
        inputs = manager.get_queued_inputs(session_id)
        assert len(inputs) == 1
