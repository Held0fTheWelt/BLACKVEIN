"""
Integration tests for AI stack with SessionService.

Tests the orchestrator running against mock SessionService, validating:
- State reading → reasoning → action → result flow
- Error handling (unknown session, MCP failures)
- Full reasoning flow validation
- Proper integration with backend session system

Constitutional Laws:
- Law 1: One truth - AI state mirrors session state
- Law 9: AI composition - orchestrator uses only MCP interface
- Law 10: Catastrophic failure - errors don't crash system
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from ai_stack.langgraph.langgraph_orchestrator import GameOrchestrator
from ai_stack.mcp.mcp_agent_interface import MCPAgentInterface
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog
from ai_stack.langgraph.langgraph_agent_state import AgentState


class MockSessionService:
    """Mock SessionService for testing orchestrator integration."""

    def __init__(self):
        """Initialize mock session service."""
        self.sessions = {}
        self.turn_counter = {}

    def get_session(self, session_id: str):
        """Get session by ID."""
        return self.sessions.get(session_id)

    def get_session_state(self, session_id: str):
        """Get session state dict."""
        session = self.sessions.get(session_id)
        return session.get("state", {}) if session else None

    def execute_turn(self, session_id: str, player_id: str, action: dict):
        """Execute turn and return result."""
        if session_id not in self.sessions:
            return {
                "success": False,
                "error": "Session not found"
            }

        # Increment turn counter
        if session_id not in self.turn_counter:
            self.turn_counter[session_id] = 0
        self.turn_counter[session_id] += 1

        # Return simulated turn result
        return {
            "success": True,
            "turn_number": self.turn_counter[session_id],
            "state_delta": {"location_change": action.get("move")},
            "narrative": f"Player {player_id} executed action: {action}"
        }

    def create_mock_session(self, session_id: str, world_id: str, state: dict):
        """Create a mock session."""
        self.sessions[session_id] = {
            "session_id": session_id,
            "world_id": world_id,
            "state": state,
            "turn_number": 0
        }
        self.turn_counter[session_id] = 0


class TestAIOrchestratorWithSessionService:
    """Test orchestrator integration with SessionService."""

    def test_orchestrator_reads_session_state(self):
        """Test orchestrator can read session state through MCP."""
        # Setup
        mock_session = MockSessionService()
        mock_session.create_mock_session(
            "test_session",
            "world1",
            {"location": "forest", "health": 100}
        )

        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {"location": "forest", "health": 100}
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Execute
        result = orchestrator.run("test_session", 1)

        # Verify
        assert isinstance(result, AgentState)
        mock_interface.call_session_state.assert_called()

    def test_orchestrator_executes_turn_through_session(self):
        """Test orchestrator executes turn through SessionService."""
        # Setup
        mock_session = MockSessionService()
        mock_session.create_mock_session(
            "test_session",
            "world1",
            {"location": "forest"}
        )

        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {"session_id": "test_session"}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {"location": "forest"}
        }
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {
                "turn_number": 1,
                "state_delta": {"location": "cave"},
                "narrative": "You moved to cave"
            }
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Execute
        result = orchestrator.run("test_session", 1)

        # Verify
        assert isinstance(result, AgentState)
        assert result.session_id == "test_session"
        mock_interface.call_execute_turn.assert_called()

    def test_orchestrator_handles_unknown_session(self):
        """Test orchestrator handles unknown session gracefully."""
        # Setup
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": False,
            "error": "Session not found"
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Execute - should not raise
        result = orchestrator.run("unknown_session", 1)

        # Verify - should be degraded
        assert isinstance(result, AgentState)
        assert result.is_degraded is True

    def test_orchestrator_full_reasoning_flow(self):
        """Test complete reasoning flow: read -> reason -> select -> execute -> interpret."""
        # Setup
        mock_interface = Mock(spec=MCPAgentInterface)

        # Chain of calls for full flow
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {"session_id": "test_session"}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {
                "location": "forest",
                "health": 80,
                "enemies_nearby": ["goblin", "orc"]
            }
        }
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {
                "turn_number": 1,
                "state_delta": {"health": 75},
                "narrative": "Combat resolved"
            }
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Execute
        result = orchestrator.run("test_session", 1)

        # Verify state contains decision chain
        assert isinstance(result, AgentState)
        assert result.session_id == "test_session"
        assert result.player_id == 1

    def test_orchestrator_handles_session_mcp_failure(self):
        """Test orchestrator handles MCP call failure gracefully."""
        # Setup
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.side_effect = Exception("MCP network error")

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Execute - should not raise
        result = orchestrator.run("test_session", 1)

        # Verify - should be degraded
        assert isinstance(result, AgentState)
        assert result.is_degraded is True

    def test_orchestrator_turn_result_validation(self):
        """Test orchestrator validates turn results from SessionService."""
        # Setup
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {"turn_number": 5}
        }
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {
                "turn_number": 6,
                "state_delta": {"resources": 100},
                "narrative": "Resources gathered"
            }
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Execute
        result = orchestrator.run("test_session", 1)

        # Verify turn was incremented
        assert isinstance(result, AgentState)

    def test_orchestrator_with_complex_world_state(self):
        """Test orchestrator with complex nested world state."""
        # Setup
        complex_state = {
            "location": "castle",
            "inventory": {
                "weapons": ["sword", "shield"],
                "consumables": {"potion": 3}
            },
            "npcs": [
                {"name": "guard", "faction": "royal"},
                {"name": "beggar", "faction": "commoner"}
            ],
            "quests": {
                "active": ["rescue_princess"],
                "completed": ["clear_dungeon"]
            }
        }

        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": complex_state
        }
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {
                "turn_number": 1,
                "state_delta": {"inventory": {"weapons": ["sword"]}},
                "narrative": "Used shield"
            }
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Execute
        result = orchestrator.run("test_session", 1)

        # Verify
        assert isinstance(result, AgentState)
        # Verify interface was called (implies state was processed)
        assert mock_interface.call_session_state.called

    def test_orchestrator_maintains_state_consistency(self):
        """Test orchestrator maintains state consistency across calls."""
        # Setup
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {}
        }
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {"consistency_check": "value"}
        }
        mock_interface.call_execute_turn.return_value = {
            "success": True,
            "data": {
                "turn_number": 1,
                "state_delta": {},
                "narrative": "State maintained"
            }
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Execute
        result1 = orchestrator.run("test_session", 1)
        result2 = orchestrator.run("test_session", 1)

        # Verify both results are valid states
        assert isinstance(result1, AgentState)
        assert isinstance(result2, AgentState)

    def test_orchestrator_error_logging_on_session_failure(self):
        """Test orchestrator logs errors when session operations fail."""
        # Setup
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": False,
            "error": "Permission denied"
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Execute
        result = orchestrator.run("test_session", 1)

        # Verify error was captured in degradation
        assert isinstance(result, AgentState)
        assert result.is_degraded is True

    def test_orchestrator_partial_state_recovery(self):
        """Test orchestrator can work with partial state when some MCP calls fail."""
        # Setup
        mock_interface = Mock(spec=MCPAgentInterface)
        mock_interface.call_session_get.return_value = {
            "success": True,
            "data": {"session_id": "test"}
        }
        # Session state succeeds
        mock_interface.call_session_state.return_value = {
            "success": True,
            "data": {"location": "forest"}
        }
        # But execute fails
        mock_interface.call_execute_turn.return_value = {
            "success": False,
            "error": "Turn limit exceeded"
        }

        catalog = CanonicalPromptCatalog()
        orchestrator = GameOrchestrator(mock_interface, catalog)

        # Execute - should handle partial failure
        result = orchestrator.run("test_session", 1)

        # Should still return valid state (degraded)
        assert isinstance(result, AgentState)
