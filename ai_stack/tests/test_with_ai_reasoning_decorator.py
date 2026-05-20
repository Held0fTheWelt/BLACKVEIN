"""
Tests for turn execution decorator with AI reasoning.

Tests:
- Decorator enables/disables AI for players
- Decorator collects diagnostics
- Decorator gracefully handles AI failures
- Decorator never breaks turn execution
- AI reasoning is injected into response

Constitutional Laws:
- Law 6: Fail closed - AI errors don't break turns
- Law 10: Catastrophic failure - AI failures handled gracefully
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from ai_stack.with_ai_reasoning_decorator import (
    WithAIReasoning,
    with_ai_reasoning,
    set_orchestrator,
    enable_ai_for_player,
    disable_ai_for_player,
    is_ai_enabled_for_player,
    AIReasoningDiagnostics
)
from ai_stack.langgraph.langgraph_agent_state import AgentState
from ai_stack.mcp.mcp_agent_interface import MCPAgentInterface
from ai_stack.prompt_store.catalog import CanonicalPromptCatalog


class TestAIReasoningDiagnostics:
    """Test diagnostics collection."""

    def test_diagnostics_initialize(self):
        """Test diagnostics initialize with defaults."""
        diag = AIReasoningDiagnostics()
        assert diag.ai_enabled is False
        assert diag.reasoning_error is None
        assert diag.reasoning_degraded is False

    def test_diagnostics_to_dict(self):
        """Test diagnostics serialization."""
        diag = AIReasoningDiagnostics()
        diag.ai_enabled = True
        diag.reasoning_duration_ms = 150
        diag.decision_made = "attack"

        result = diag.to_dict()
        assert result["ai_enabled"] is True
        assert result["reasoning_duration_ms"] == 150
        assert result["decision_made"] == "attack"


class TestWithAIReasoningBasic:
    """Test basic decorator functionality."""

    def test_decorator_initializes(self):
        """Test decorator can be initialized."""
        decorator = WithAIReasoning()
        assert decorator is not None
        assert decorator.enabled_by_default is False

    def test_decorator_initializes_with_config(self):
        """Test decorator initialization with config."""
        mock_interface = Mock(spec=MCPAgentInterface)
        catalog = CanonicalPromptCatalog()

        decorator = WithAIReasoning(mock_interface, catalog, enabled_by_default=True)
        assert decorator.mcp_interface == mock_interface
        assert decorator.enabled_by_default is True

    def test_decorator_wraps_function(self):
        """Test decorator wraps a function."""
        decorator = WithAIReasoning()

        def dummy_route():
            return "response", 200

        wrapped = decorator(dummy_route)
        assert wrapped is not None
        assert callable(wrapped)


class TestAIEnablement:
    """Test AI enablement per player."""

    def test_ai_disabled_by_default(self):
        """Test AI is disabled by default."""
        decorator = WithAIReasoning()
        assert decorator.is_ai_enabled("player1") is False

    def test_ai_enabled_by_default(self):
        """Test AI enabled by default when configured."""
        decorator = WithAIReasoning(enabled_by_default=True)
        assert decorator.is_ai_enabled("player1") is True

    def test_enable_ai_for_player(self):
        """Test enabling AI for specific player."""
        decorator = WithAIReasoning()
        assert decorator.is_ai_enabled("player1") is False

        decorator.set_player_ai_enabled("player1", True)
        assert decorator.is_ai_enabled("player1") is True

    def test_disable_ai_for_player(self):
        """Test disabling AI for specific player."""
        decorator = WithAIReasoning(enabled_by_default=True)
        assert decorator.is_ai_enabled("player1") is True

        decorator.set_player_ai_enabled("player1", False)
        assert decorator.is_ai_enabled("player1") is False

    def test_ai_per_player_independent(self):
        """Test AI setting is independent per player."""
        decorator = WithAIReasoning()

        decorator.set_player_ai_enabled("player1", True)
        decorator.set_player_ai_enabled("player2", False)

        assert decorator.is_ai_enabled("player1") is True
        assert decorator.is_ai_enabled("player2") is False


class TestDecoratorExecution:
    """Test decorator execution behavior."""

    def test_decorator_preserves_function_result(self):
        """Test decorator preserves original function result."""
        decorator = WithAIReasoning()

        def dummy_route():
            return {"message": "success"}, 200

        wrapped = decorator(dummy_route)
        result, status = wrapped()

        assert result["message"] == "success"
        assert status == 200

    def test_decorator_injects_diagnostics(self):
        """Test decorator injects diagnostics into response."""
        mock_interface = Mock(spec=MCPAgentInterface)
        catalog = CanonicalPromptCatalog()
        decorator = WithAIReasoning(mock_interface, catalog)

        # Enable AI for player
        decorator.set_player_ai_enabled("player1", True)

        def dummy_route(player_id, session_id):
            return {"message": "success"}, 200

        wrapped = decorator(dummy_route)

        # Mock the orchestrator
        with patch.object(decorator, '_get_orchestrator') as mock_orch_method:
            mock_orch = Mock()
            mock_state = Mock(spec=AgentState)
            mock_state.is_degraded = False
            mock_state.action_selected = "move"
            mock_orch.run.return_value = mock_state
            mock_orch_method.return_value = mock_orch

            result, status = wrapped(player_id="player1", session_id="session1")

            assert "ai_diagnostics" in result
            assert result["ai_diagnostics"]["ai_enabled"] is True
            assert result["ai_diagnostics"]["decision_made"] == "move"

    def test_decorator_skips_ai_when_disabled(self):
        """Test decorator skips AI reasoning when disabled."""
        decorator = WithAIReasoning()
        # AI is disabled by default

        def dummy_route(player_id, session_id):
            return {"message": "success"}, 200

        wrapped = decorator(dummy_route)

        with patch.object(decorator, '_get_orchestrator') as mock_orch_method:
            result, status = wrapped(player_id="player1", session_id="session1")

            # Orchestrator should not be called
            mock_orch_method.assert_not_called()
            assert "ai_diagnostics" in result
            assert result["ai_diagnostics"]["ai_enabled"] is False

    def test_decorator_handles_ai_failure_gracefully(self):
        """Test decorator handles AI failure without breaking turn (Law 6)."""
        mock_interface = Mock(spec=MCPAgentInterface)
        catalog = CanonicalPromptCatalog()
        decorator = WithAIReasoning(mock_interface, catalog)

        decorator.set_player_ai_enabled("player1", True)

        def dummy_route(player_id, session_id):
            return {"message": "success"}, 200

        wrapped = decorator(dummy_route)

        with patch.object(decorator, '_get_orchestrator') as mock_orch_method:
            mock_orch = Mock()
            # Simulate orchestrator failure
            mock_orch.run.side_effect = Exception("AI failure")
            mock_orch_method.return_value = mock_orch

            # Should not raise - Law 6: fail closed
            result, status = wrapped(player_id="player1", session_id="session1")

            assert result["message"] == "success"
            assert status == 200
            assert result["ai_diagnostics"]["reasoning_error"] is not None
            assert result["ai_diagnostics"]["reasoning_degraded"] is True

    def test_decorator_records_reasoning_time(self):
        """Test decorator records AI reasoning duration."""
        mock_interface = Mock(spec=MCPAgentInterface)
        catalog = CanonicalPromptCatalog()
        decorator = WithAIReasoning(mock_interface, catalog)

        decorator.set_player_ai_enabled("player1", True)

        def dummy_route(player_id, session_id):
            return {"message": "success"}, 200

        wrapped = decorator(dummy_route)

        with patch.object(decorator, '_get_orchestrator') as mock_orch_method:
            mock_orch = Mock()
            mock_state = Mock(spec=AgentState)
            mock_state.is_degraded = False
            mock_state.action_selected = "attack"
            mock_orch.run.return_value = mock_state
            mock_orch_method.return_value = mock_orch

            result, status = wrapped(player_id="player1", session_id="session1")

            assert result["ai_diagnostics"]["reasoning_duration_ms"] is not None
            assert result["ai_diagnostics"]["reasoning_duration_ms"] >= 0

    def test_decorator_handles_missing_player_id(self):
        """Test decorator handles missing player_id gracefully."""
        decorator = WithAIReasoning()

        def dummy_route():
            return {"message": "success"}, 200

        wrapped = decorator(dummy_route)
        result, status = wrapped()

        assert result["message"] == "success"
        assert status == 200
        assert "ai_diagnostics" in result

    def test_decorator_catches_wrapper_errors(self):
        """Test decorator catches errors in wrapped function."""
        decorator = WithAIReasoning()

        def failing_route():
            raise ValueError("Route error")

        wrapped = decorator(failing_route)

        # Should propagate the route error (not silenced)
        with pytest.raises(ValueError):
            wrapped()


class TestModuleLevelAPI:
    """Test module-level API functions."""

    def test_with_ai_reasoning_decorator_usage(self):
        """Test using @with_ai_reasoning as module decorator."""
        @with_ai_reasoning
        def dummy_route():
            return {"message": "success"}, 200

        result, status = dummy_route()
        assert result["message"] == "success"
        assert "ai_diagnostics" in result

    def test_set_orchestrator_function(self):
        """Test set_orchestrator module function."""
        mock_interface = Mock(spec=MCPAgentInterface)
        catalog = CanonicalPromptCatalog()

        set_orchestrator(mock_interface, catalog)

        # Should not raise
        assert True

    def test_enable_disable_module_functions(self):
        """Test module-level enable/disable functions."""
        enable_ai_for_player("player1")
        assert is_ai_enabled_for_player("player1") is True

        disable_ai_for_player("player1")
        assert is_ai_enabled_for_player("player1") is False

    def test_module_functions_independent(self):
        """Test module-level functions are independent."""
        enable_ai_for_player("player1")
        disable_ai_for_player("player2")

        assert is_ai_enabled_for_player("player1") is True
        assert is_ai_enabled_for_player("player2") is False
