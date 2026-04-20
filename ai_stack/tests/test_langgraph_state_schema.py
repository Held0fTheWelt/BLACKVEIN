"""
Tests for LangGraph Agent State Schema.
"""

import pytest
import json
from ai_stack.langgraph_agent_state import AgentState, create_initial_state


class TestAgentStateBasic:
    """Test basic state functionality."""

    def test_state_initializes(self):
        """Test state can be initialized."""
        state = AgentState(
            session_id="abc123",
            player_id=1,
            current_state={}
        )
        assert state is not None
        assert state.session_id == "abc123"
        assert state.player_id == 1

    def test_state_validates_game_context(self):
        """Test state captures game context."""
        world = {"location": "forest", "enemies": 2}
        state = AgentState(
            session_id="abc123",
            player_id=1,
            current_state=world
        )
        assert state.current_state == world
        assert state.current_state["location"] == "forest"

    def test_state_tracks_turn_number(self):
        """Test state tracks turn progression."""
        state = AgentState(
            session_id="abc123",
            player_id=1,
            turn_number=5,
            current_state={}
        )
        assert state.turn_number == 5

    def test_state_initializes_with_defaults(self):
        """Test state initializes with sensible defaults."""
        state = AgentState(session_id="abc", player_id=1)
        assert state.reasoning_steps == []
        assert state.errors == []
        assert state.is_degraded is False
        assert state.decision is None


class TestAgentStateImmutability:
    """Test state immutability after lock."""

    def test_state_is_immutable_after_lock(self):
        """Test state cannot be modified after lock."""
        state = AgentState(session_id="abc", player_id=1)
        state.lock()

        # Attempt to modify should fail
        with pytest.raises(ValueError):
            state.decision = "attack_north"

    def test_can_modify_before_lock(self):
        """Test state can be modified before lock."""
        state = AgentState(session_id="abc", player_id=1)
        state.decision = "attack_north"
        assert state.decision == "attack_north"

    def test_lock_prevents_all_modifications(self):
        """Test lock prevents all field modifications."""
        state = AgentState(session_id="abc", player_id=1)
        state.lock()

        fields_to_test = ["turn_number", "previous_action", "is_degraded"]
        for field in fields_to_test:
            with pytest.raises(ValueError):
                setattr(state, field, "modified")


class TestAgentStateSerializability:
    """Test state serialization to JSON."""

    def test_state_serializes_to_dict(self):
        """Test state converts to dictionary."""
        state = AgentState(
            session_id="abc",
            player_id=1,
            decision="attack",
            current_state={"health": 100}
        )
        data = state.to_dict()
        assert isinstance(data, dict)
        assert data["session_id"] == "abc"
        assert data["decision"] == "attack"

    def test_state_serializes_to_json(self):
        """Test state serializes to JSON string."""
        state = AgentState(
            session_id="abc",
            player_id=1,
            decision="attack"
        )
        json_str = state.to_json()
        assert isinstance(json_str, str)
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["session_id"] == "abc"

    def test_state_deserializes_from_dict(self):
        """Test state deserializes from dictionary."""
        data = {
            "session_id": "abc",
            "player_id": 1,
            "decision": "attack",
            "current_state": {"location": "forest"}
        }
        state = AgentState.from_dict(data)
        assert state.session_id == "abc"
        assert state.decision == "attack"

    def test_state_deserializes_from_json(self):
        """Test state deserializes from JSON."""
        json_str = '{"session_id": "abc", "player_id": 1, "turn_number": 0, "current_state": {}, "previous_action": null, "previous_result": null, "reasoning_steps": [], "decision": null, "mcp_logs": [], "diagnostics": {}, "operational_profile": {}, "errors": [], "is_degraded": false}'

        state = AgentState.from_json(json_str)
        assert state.session_id == "abc"
        assert state.player_id == 1

    def test_roundtrip_serialization(self):
        """Test state survives roundtrip serialization."""
        original = AgentState(
            session_id="abc",
            player_id=1,
            turn_number=3,
            decision="attack_north",
            current_state={"health": 100}
        )

        # To JSON and back
        json_str = original.to_json()
        restored = AgentState.from_json(json_str)

        assert restored.session_id == original.session_id
        assert restored.player_id == original.player_id
        assert restored.decision == original.decision
        assert restored.current_state == original.current_state


class TestAgentStateErrorTracking:
    """Test error tracking and degradation."""

    def test_add_error_marks_degraded(self):
        """Test adding error marks state as degraded."""
        state = AgentState(session_id="abc", player_id=1)
        assert state.is_degraded is False

        state.add_error("MCP timeout")
        assert state.is_degraded is True
        assert "MCP timeout" in state.errors

    def test_multiple_errors_tracked(self):
        """Test multiple errors are tracked."""
        state = AgentState(session_id="abc", player_id=1)
        state.add_error("Error 1")
        state.add_error("Error 2")
        assert len(state.errors) == 2

    def test_cannot_add_error_when_locked(self):
        """Test cannot add errors to locked state."""
        state = AgentState(session_id="abc", player_id=1)
        state.lock()
        with pytest.raises(ValueError):
            state.add_error("Error")


class TestAgentStateReasoningSteps:
    """Test reasoning step tracking."""

    def test_add_reasoning_step(self):
        """Test adding reasoning steps."""
        state = AgentState(session_id="abc", player_id=1)
        state.add_reasoning_step("Analyzing enemy position")
        state.add_reasoning_step("Calculating damage")
        assert len(state.reasoning_steps) == 2
        assert "Analyzing enemy position" in state.reasoning_steps

    def test_cannot_add_reasoning_when_locked(self):
        """Test cannot add reasoning to locked state."""
        state = AgentState(session_id="abc", player_id=1)
        state.lock()
        with pytest.raises(ValueError):
            state.add_reasoning_step("Step")


class TestCreateInitialState:
    """Test helper function for state creation."""

    def test_create_initial_state(self):
        """Test creating initial state."""
        world = {"location": "forest"}
        state = create_initial_state(
            session_id="abc",
            player_id=1,
            current_state=world
        )
        assert state.session_id == "abc"
        assert state.current_state == world
        assert state.turn_number == 0

    def test_create_initial_state_with_profile(self):
        """Test creating initial state with profile."""
        profile = {"difficulty": "hard"}
        state = create_initial_state(
            session_id="abc",
            player_id=1,
            current_state={},
            operational_profile=profile
        )
        assert state.operational_profile == profile


class TestAgentStateRepr:
    """Test string representation."""

    def test_repr_includes_key_info(self):
        """Test repr includes key information."""
        state = AgentState(
            session_id="abc",
            player_id=1,
            decision="attack"
        )
        repr_str = repr(state)
        assert "abc" in repr_str
        assert "attack" in repr_str
