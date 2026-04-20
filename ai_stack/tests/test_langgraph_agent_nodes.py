"""
Tests for LangGraph Agent Nodes.
"""

import pytest
from unittest.mock import Mock
from ai_stack.langgraph_agent_nodes import (
    initialize_state,
    reason_decision,
    select_action,
    execute_turn,
    interpret_result
)
from ai_stack.langgraph_agent_state import AgentState
from ai_stack.mcp_agent_interface import MCPAgentInterface
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog


class TestInitializeStateNode:
    """Test state initialization node."""

    def test_initialize_state_success(self):
        """Test successful state initialization."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {"session_id": "abc"}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {"location": "forest"}
        }

        state = initialize_state(
            "abc",
            1,
            mock_interface
        )

        assert state.session_id == "abc"
        assert state.player_id == 1
        assert state.current_state == {"location": "forest"}
        assert not state.is_degraded

    def test_initialize_state_session_not_found(self):
        """Test initialization when session not found."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": False,
            "error": "Session not found"
        }

        state = initialize_state("abc", 1, mock_interface)

        assert state.session_id == "abc"
        assert state.is_degraded is True
        assert "Session init failed" in state.errors[0]

    def test_initialize_state_with_profile(self):
        """Test initialization with operational profile."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {}
        }

        profile = {"difficulty": "hard"}
        state = initialize_state("abc", 1, mock_interface, profile)

        assert state.operational_profile == profile


class TestReasonDecisionNode:
    """Test decision reasoning node."""

    def test_reason_decision_success(self):
        """Test successful reasoning."""
        catalog = CanonicalPromptCatalog()
        mock_interface = Mock()

        state = AgentState(session_id="abc", player_id=1)

        result = reason_decision(state, mock_interface, catalog)

        assert result.session_id == "abc"
        assert len(result.reasoning_steps) > 0
        assert not result.is_degraded

    def test_reason_decision_skips_if_degraded(self):
        """Test reasoning skips if state degraded."""
        catalog = CanonicalPromptCatalog()
        mock_interface = Mock()

        state = AgentState(session_id="abc", player_id=1)
        state.add_error("Already degraded")

        initial_steps = len(state.reasoning_steps)
        result = reason_decision(state, mock_interface, catalog)

        # Should not add new reasoning
        assert len(result.reasoning_steps) == initial_steps

    def test_reason_decision_adds_reasoning_steps(self):
        """Test reasoning adds steps to state."""
        catalog = CanonicalPromptCatalog()
        mock_interface = Mock()

        state = AgentState(session_id="abc", player_id=1)

        result = reason_decision(state, mock_interface, catalog)

        assert len(result.reasoning_steps) > 0


class TestSelectActionNode:
    """Test action selection node."""

    def test_select_action_success(self):
        """Test successful action selection."""
        catalog = CanonicalPromptCatalog()

        state = AgentState(session_id="abc", player_id=1)
        state.add_reasoning_step("Analysis step")

        result = select_action(state, catalog)

        assert result.decision is not None
        assert len(result.decision) > 0

    def test_select_action_chooses_default_if_no_reasoning(self):
        """Test falls back to default if no reasoning."""
        catalog = CanonicalPromptCatalog()

        state = AgentState(session_id="abc", player_id=1)

        result = select_action(state, catalog)

        # Should have safe default
        assert result.decision == "move_forward"

    def test_select_action_uses_default_if_degraded(self):
        """Test uses safe default if degraded."""
        catalog = CanonicalPromptCatalog()

        state = AgentState(session_id="abc", player_id=1)
        state.add_error("Error")

        result = select_action(state, catalog)

        # Should use safe default
        assert result.decision == "move_forward"


class TestExecuteTurnNode:
    """Test turn execution node."""

    def test_execute_turn_success(self):
        """Test successful turn execution."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {
                "turn_number": 1,
                "world_state": {"location": "forest"},
                "narrative": "You move forward"
            }
        }

        state = AgentState(session_id="abc", player_id=1, decision="move_forward")

        result = execute_turn(state, mock_interface)

        assert result.turn_number == 1
        assert result.previous_action == "move_forward"
        assert "You move forward" in result.previous_result

    def test_execute_turn_no_decision(self):
        """Test execution fails without decision."""
        mock_interface = Mock(spec=MCPAgentInterface)

        state = AgentState(session_id="abc", player_id=1)

        result = execute_turn(state, mock_interface)

        assert result.is_degraded is True
        assert "No decision made" in result.errors[0]

    def test_execute_turn_mcp_error(self):
        """Test execution handles MCP errors."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_execute_turn.return_value = {
            "success": False,
            "error": "Action blocked"
        }

        state = AgentState(session_id="abc", player_id=1, decision="move_forward")

        result = execute_turn(state, mock_interface)

        assert result.is_degraded is True


class TestInterpretResultNode:
    """Test result interpretation node."""

    def test_interpret_result_success(self):
        """Test successful result interpretation."""
        catalog = CanonicalPromptCatalog()

        state = AgentState(
            session_id="abc",
            player_id=1,
            previous_result="You moved forward"
        )

        result = interpret_result(state, catalog)

        assert result.session_id == "abc"

    def test_interpret_result_with_degraded_state(self):
        """Test interpretation handles degraded state."""
        catalog = CanonicalPromptCatalog()

        state = AgentState(session_id="abc", player_id=1)
        state.add_error("Degraded")

        result = interpret_result(state, catalog)

        # Should handle gracefully
        assert result.is_degraded is True


class TestNodeErrorHandling:
    """Test error handling across nodes."""

    def test_all_nodes_return_state(self):
        """Test all nodes return AgentState even on error."""
        catalog = CanonicalPromptCatalog()
        mock_interface = Mock()

        state = AgentState(session_id="abc", player_id=1)

        # All nodes should return state type
        assert isinstance(reason_decision(state, mock_interface, catalog), AgentState)
        assert isinstance(select_action(state, catalog), AgentState)
        assert isinstance(execute_turn(state, mock_interface), AgentState)
        assert isinstance(interpret_result(state, catalog), AgentState)

    def test_nodes_never_raise_exceptions(self):
        """Test nodes never raise exceptions."""
        catalog = CanonicalPromptCatalog()
        mock_interface = Mock()
        mock_interface.call_execute_turn.side_effect = Exception("Test error")

        state = AgentState(session_id="abc", player_id=1, decision="move")

        # Should not raise
        result = execute_turn(state, mock_interface)
        assert isinstance(result, AgentState)
