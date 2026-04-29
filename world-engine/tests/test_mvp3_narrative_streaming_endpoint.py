"""
Phase 4 (Days 7-8): HTTP Streaming Endpoint tests.

Tests the SSE streaming endpoint for narrator blocks, signal propagation,
and integration with StoryRuntimeManager's narrative orchestration.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.http import router
from app.story_runtime.manager import StoryRuntimeManager, _orchestrate_narrative_agent
from ai_stack.narrative import NarrativeRuntimeAgent, NarrativeEventKind, NarrativeRuntimeAgentEvent
from datetime import datetime, timezone


@pytest.fixture
def app():
    """Create FastAPI test app with HTTP router."""
    test_app = FastAPI()
    test_app.include_router(router)

    # Mock managers in app.state
    test_app.state.story_manager = StoryRuntimeManager()

    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_agent_input():
    """Sample input for narrator agent."""
    return {
        "runtime_state": {"scene_id": "living_room", "session_id": "test_session"},
        "npc_agency_plan": {
            "initiatives": [
                {"actor_id": "annette", "resolved": False},
            ]
        },
        "dramatic_signature": {"primary_tension": "conflict"},
        "narrative_threads": [],
        "session_id": "test_session",
        "turn_number": 1,
    }


class TestNarratorStreamingEndpoint:
    """Test Phase 4 streaming narrator endpoint."""

    def test_stream_narrator_blocks_endpoint_exists(self, client):
        """Endpoint /api/story/sessions/{session_id}/stream-narrator exists."""
        # Endpoint should 404 for non-existent session (no narrator streaming)
        response = client.get("/api/story/sessions/nonexistent/stream-narrator")
        assert response.status_code == 200  # SSE streams return 200 even with no agent

    def test_stream_narrator_blocks_no_agent_returns_error(self, client):
        """Endpoint returns error event when no narrator is streaming."""
        response = client.get(
            "/api/story/sessions/test_session/stream-narrator",
        )
        assert response.status_code == 200

        # Parse SSE response
        lines = response.text.strip().split("\n")
        assert len(lines) > 0

        # First line should be "data: ..."
        data_line = [l for l in lines if l.startswith("data:")][0]
        payload = json.loads(data_line[6:])  # Skip "data: "

        assert payload.get("error") == "no_narrator_streaming"
        assert payload.get("session_id") == "test_session"

    def test_stream_narrator_blocks_emits_events(self, client, sample_agent_input):
        """Streaming endpoint emits narrator block events from agent."""
        manager = client.app.state.story_manager

        # Create agent and orchestrate
        result = _orchestrate_narrative_agent(
            manager=manager,
            session_id="test_session",
            ldss_output={"npc_agency_plan": {"initiatives": [{"actor_id": "npc1", "resolved": False}]}},
            runtime_state={"scene_id": "test"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )
        assert result is True

        # Stream narrator blocks
        response = client.get("/api/story/sessions/test_session/stream-narrator")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Parse SSE events
        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]
        assert len(data_lines) > 0

        # Parse first event
        first_event = json.loads(data_lines[0][6:])
        assert "event_id" in first_event
        assert "event_kind" in first_event

    def test_stream_narrator_blocks_includes_narrator_blocks(self, client, sample_agent_input):
        """Stream includes events with narrator_block data."""
        manager = client.app.state.story_manager

        _orchestrate_narrative_agent(
            manager=manager,
            session_id="test_session",
            ldss_output={"npc_agency_plan": {"initiatives": [{"actor_id": "npc1", "resolved": False}]}},
            runtime_state={"scene_id": "test"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )

        response = client.get("/api/story/sessions/test_session/stream-narrator")
        assert response.status_code == 200

        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]

        # Find narrator block events
        narrator_events = []
        for line in data_lines:
            event = json.loads(line[6:])
            if event.get("event_kind") == "narrator_block":
                narrator_events.append(event)

        assert len(narrator_events) > 0, "Should have at least one narrator block event"

        # Narrator block event should have data with narrator_block
        for event in narrator_events:
            assert "data" in event
            assert "narrator_block" in event["data"] or event["data"].get("narrator_block")

    def test_stream_narrator_blocks_emits_ruhepunkt_signal(self, client, sample_agent_input):
        """Stream includes ruhepunkt_reached signal when initiatives exhausted."""
        manager = client.app.state.story_manager

        _orchestrate_narrative_agent(
            manager=manager,
            session_id="test_session",
            ldss_output={"npc_agency_plan": {"initiatives": [{"actor_id": "npc1", "resolved": False}]}},
            runtime_state={"scene_id": "test"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )

        response = client.get("/api/story/sessions/test_session/stream-narrator")
        assert response.status_code == 200

        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]

        # Find ruhepunkt signal
        ruhepunkt_events = []
        for line in data_lines:
            event = json.loads(line[6:])
            if event.get("event_kind") == "ruhepunkt_reached":
                ruhepunkt_events.append(event)

        assert len(ruhepunkt_events) > 0, "Should have ruhepunkt_reached signal"

        # Verify ruhepunkt event structure
        ruhepunkt = ruhepunkt_events[0]
        assert ruhepunkt.get("data", {}).get("ruhepunkt_reached") is True

    def test_stream_uses_sse_content_type(self, client, sample_agent_input):
        """Streaming response uses Server-Sent Events content type."""
        manager = client.app.state.story_manager

        _orchestrate_narrative_agent(
            manager=manager,
            session_id="test_session",
            ldss_output={"npc_agency_plan": {"initiatives": [{"actor_id": "npc1", "resolved": False}]}},
            runtime_state={"scene_id": "test"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )

        response = client.get("/api/story/sessions/test_session/stream-narrator")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_stream_narrator_blocks_handles_streaming_errors(self, client):
        """Endpoint gracefully handles streaming exceptions."""
        manager = client.app.state.story_manager

        # Create a mock agent that raises an error
        mock_agent = MagicMock(spec=NarrativeRuntimeAgent)

        def error_generator(input_arg):
            raise RuntimeError("Mock streaming error")
            yield  # unreachable

        mock_agent.stream_narrator_blocks = error_generator
        mock_agent.current_input = {}

        manager.narrative_agents["test_session"] = mock_agent

        response = client.get("/api/story/sessions/test_session/stream-narrator")
        assert response.status_code == 200

        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]

        # Should emit error event
        last_event = json.loads(data_lines[-1][6:])
        assert last_event.get("error") == "streaming_failed"

    def test_stream_narrator_blocks_event_structure(self, client, sample_agent_input):
        """Streamed events have correct structure (id, kind, timestamp, sequence, data)."""
        manager = client.app.state.story_manager

        _orchestrate_narrative_agent(
            manager=manager,
            session_id="test_session",
            ldss_output={"npc_agency_plan": {"initiatives": [{"actor_id": "npc1", "resolved": False}]}},
            runtime_state={"scene_id": "test"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )

        response = client.get("/api/story/sessions/test_session/stream-narrator")
        assert response.status_code == 200

        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]

        for line in data_lines:
            event = json.loads(line[6:])

            # Verify event structure
            assert "event_id" in event
            assert "event_kind" in event
            assert "timestamp" in event
            assert "sequence_number" in event
            assert "data" in event

            # Verify event_kind is valid (Phase 6 adds trace scaffold events)
            assert event["event_kind"] in [
                "narrator_block",
                "ruhepunkt_reached",
                "streaming_complete",
                "error",
                "trace_scaffold_emitted",  # Phase 6: tracing disabled signal
                "trace_scaffold_summary",  # Phase 6: trace metadata summary
            ]


@pytest.mark.mvp3
class TestMVP3StreamingGate:
    """MVP3 gate verification for HTTP streaming endpoint."""

    def test_mvp3_streaming_endpoint_available(self, client, sample_agent_input):
        """Gate: Streaming endpoint exists and is accessible."""
        manager = client.app.state.story_manager

        _orchestrate_narrative_agent(
            manager=manager,
            session_id="test_session",
            ldss_output={"npc_agency_plan": {"initiatives": [{"actor_id": "npc1", "resolved": False}]}},
            runtime_state={"scene_id": "test"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )

        response = client.get("/api/story/sessions/test_session/stream-narrator")
        assert response.status_code == 200

    def test_mvp3_streaming_emits_narrator_blocks(self, client, sample_agent_input):
        """Gate: Streaming endpoint emits narrator blocks."""
        manager = client.app.state.story_manager

        _orchestrate_narrative_agent(
            manager=manager,
            session_id="test_session",
            ldss_output={"npc_agency_plan": {"initiatives": [{"actor_id": "npc1", "resolved": False}]}},
            runtime_state={"scene_id": "test"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )

        response = client.get("/api/story/sessions/test_session/stream-narrator")
        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]

        narrator_blocks = [
            json.loads(l[6:])
            for l in data_lines
            if json.loads(l[6:]).get("event_kind") == "narrator_block"
        ]

        assert len(narrator_blocks) > 0

    def test_mvp3_streaming_signals_ruhepunkt(self, client, sample_agent_input):
        """Gate: Streaming endpoint signals ruhepunkt when input can be processed."""
        manager = client.app.state.story_manager

        _orchestrate_narrative_agent(
            manager=manager,
            session_id="test_session",
            ldss_output={"npc_agency_plan": {"initiatives": [{"actor_id": "npc1", "resolved": False}]}},
            runtime_state={"scene_id": "test"},
            dramatic_signature={"primary_tension": "conflict"},
            narrative_threads=[],
            turn_number=1,
        )

        response = client.get("/api/story/sessions/test_session/stream-narrator")
        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]

        ruhepunkt_signals = [
            json.loads(l[6:])
            for l in data_lines
            if json.loads(l[6:]).get("event_kind") == "ruhepunkt_reached"
        ]

        assert len(ruhepunkt_signals) > 0
