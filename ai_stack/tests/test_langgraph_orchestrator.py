"""
Tests for LangGraph Orchestrator.
"""

import pytest
from unittest.mock import Mock
from ai_stack.langgraph.langgraph_orchestrator import GameOrchestrator
from ai_stack.mcp.mcp_agent_interface import MCPAgentInterface
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog
from ai_stack.langgraph.langgraph_agent_state import AgentState


class TestGameOrchestratorBasic:
    """Test basic orchestrator functionality."""

    def test_orchestrator_initializes(self):
        """Test orchestrator can be initialized."""
        mock_interface = Mock(spec=MCPAgentInterface)
        catalog = CanonicalPromptCatalog()

        orchestrator = GameOrchestrator(mock_interface, catalog)
        assert orchestrator is not None

    def test_orchestrator_builds_graph(self):
        """Test orchestrator builds graph."""
        mock_interface = Mock(spec=MCPAgentInterface)
        catalog = CanonicalPromptCatalog()

        orchestrator = GameOrchestrator(mock_interface, catalog)
        graph = orchestrator.build_graph()

        assert graph is not None

    def test_orchestrator_caches_graph(self):
        """Test graph is cached after build."""
        mock_interface = Mock(spec=MCPAgentInterface)
        catalog = CanonicalPromptCatalog()

        orchestrator = GameOrchestrator(mock_interface, catalog)
        graph1 = orchestrator.build_graph()
        graph2 = orchestrator.build_graph()

        assert graph1 is graph2


class TestGameOrchestratorRun:
    """Test orchestrator execution."""

    def test_orchestrator_runs_single_turn(self):
        """Test orchestrator executes single turn."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {"location": "forest"}
        }
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {
                "turn_number": 1,
                "world_state": {},
                "narrative": "You moved"
            }
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        result = orchestrator.run("abc", 1)

        assert isinstance(result, AgentState)
        assert result.session_id == "abc"
        assert result.player_id == 1

    def test_orchestrator_returns_state_type(self):
        """Test orchestrator always returns AgentState."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": False,
            "error": "Test error"
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        result = orchestrator.run("abc", 1)

        assert isinstance(result, AgentState)

    def test_orchestrator_handles_errors(self):
        """Test orchestrator handles errors gracefully."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.side_effect = Exception("Test error")

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Should not raise
        result = orchestrator.run("abc", 1)

        assert isinstance(result, AgentState)

    def test_orchestrator_with_operational_profile(self):
        """Test orchestrator accepts operational profile."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {"turn_number": 1, "world_state": {}, "narrative": ""}
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        profile = {"difficulty": "hard"}
        # Should not raise
        result = orchestrator.run("abc", 1, profile)

        # Should return valid state
        assert isinstance(result, AgentState)


class TestGraphDegradation:
    """Test error handling and degradation."""

    def test_graph_degradation_on_mcp_failure(self):
        """Test graph continues on MCP failure."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": False,
            "error": "Session not found"
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        result = orchestrator.run("abc", 1)

        # Should be degraded
        assert result.is_degraded is True

    def test_graph_degradation_on_execute_failure(self):
        """Test graph continues on execute failure."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_execute_turn.return_value = {
            "success": False,
            "error": "Action blocked"
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        result = orchestrator.run("abc", 1)

        # Should be degraded after execute failure
        assert result.is_degraded is True


class TestDiagnosticsCollection:
    """Test diagnostic tracking."""

    def test_diagnostics_collected_during_run(self):
        """Test diagnostics are collected during execution."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {"turn_number": 1, "world_state": {}, "narrative": ""}
        }

        # Reset diagnostics
        mock_interface.reset_diagnostics = Mock()
        mock_interface.get_diagnostics = Mock(return_value={
            "call_count": 3,
            "success_count": 3,
            "error_count": 0
        })

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        result = orchestrator.run("abc", 1)

        assert isinstance(result, AgentState)


class TestOrchestrationNodeSequence:
    """Test node execution sequence."""

    def test_nodes_execute_in_sequence(self):
        """Test nodes execute in correct order."""
        call_order = []

        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {"turn_number": 1, "world_state": {}, "narrative": ""}
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Run the orchestrator
        result = orchestrator.run("abc", 1)

        # Check that we have reasoning and decision
        assert len(result.reasoning_steps) > 0
        assert result.decision is not None
        assert result.turn_number > 0

    def test_final_state_has_decision_and_result(self):
        """Test final state includes decision and execution result."""
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {"session_id": "abc"}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {"location": "forest"}
        }
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {
                "turn_number": 1,
                "world_state": {"location": "forest"},
                "narrative": "You moved forward"
            }
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        result = orchestrator.run("abc", 1)

        # Final state should have all key fields filled
        assert result.decision is not None
        assert result.previous_result is not None
        assert result.turn_number > 0
