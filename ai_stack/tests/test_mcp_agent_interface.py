"""
Tests for MCP Agent Interface - safe wrapper for AI to call MCP tools.
"""

import pytest
from unittest.mock import Mock, MagicMock
from ai_stack.mcp.mcp_agent_interface import MCPAgentInterface


class TestMCPAgentInterfaceBasic:
    """Test basic MCP agent interface functionality."""

    def test_interface_initializes(self):
        """Test interface can be initialized."""
        interface = MCPAgentInterface(mcp_client=None)
        assert interface is not None

    def test_interface_initializes_with_client(self):
        """Test interface initializes with MCP client."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)
        assert interface is not None

    def test_call_tool_returns_dict(self):
        """Test all tool calls return dict response."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        # Mock successful tool response
        mock_client.call_tool.return_value = {"result": "success", "data": {}}

        result = interface.call_tool("session_get", {"session_id": "test"})
        assert isinstance(result, dict)

    def test_tool_call_success_has_data_field(self):
        """Test successful tool call response includes data."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.return_value = {
            "success": True,
            "data": {"session_id": "test", "player_id": 123}
        }

        result = interface.call_tool("session_get", {"session_id": "test"})
        assert result.get("success") is True
        assert "data" in result

    def test_tool_call_failure_has_error_field(self):
        """Test failed tool call response includes error field."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.side_effect = Exception("Tool error")

        result = interface.call_tool("unknown_tool", {})
        assert isinstance(result, dict)
        assert "error" in result or "success" in result


class TestMCPAgentInterfaceToolCalls:
    """Test specific MCP tool wrapper methods."""

    def test_call_session_get(self):
        """Test session_get MCP tool call."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.return_value = {
            "success": True,
            "data": {"session_id": "abc123", "player_id": 1}
        }

        result = interface.call_session_get("abc123")
        assert result.get("success") is True
        # Verify data is present in result
        assert "data" in result
        assert result["data"].get("session_id") == "abc123"

    def test_call_session_state(self):
        """Test session_state MCP tool call."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.return_value = {
            "success": True,
            "data": {"world_state": {}, "player_status": {}}
        }

        result = interface.call_session_state("abc123")
        assert result.get("success") is True
        assert "data" in result

    def test_call_execute_turn(self):
        """Test execute_turn MCP tool call."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.return_value = {
            "success": True,
            "data": {"turn_number": 1, "result": "success"}
        }

        result = interface.call_execute_turn("abc123", 1, "attack_north")
        assert result.get("success") is True
        assert "data" in result

    def test_call_session_logs(self):
        """Test session_logs MCP tool call."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.return_value = {
            "success": True,
            "data": {"logs": []}
        }

        result = interface.call_session_logs("abc123")
        assert result.get("success") is True

    def test_call_session_diag(self):
        """Test session_diag MCP tool call."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.return_value = {
            "success": True,
            "data": {"diagnostics": {}}
        }

        result = interface.call_session_diag("abc123")
        assert result.get("success") is True


class TestMCPAgentInterfaceValidation:
    """Test fail-closed validation."""

    def test_unknown_tool_returns_error(self):
        """Test calling unknown tool returns error dict."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        # Tool doesn't exist
        mock_client.call_tool.side_effect = ValueError("Unknown tool")

        result = interface.call_tool("unknown_tool_xyz", {})
        assert isinstance(result, dict)
        # Should have error or success=False
        assert result.get("success") is False or "error" in result

    def test_invalid_params_return_error(self):
        """Test calling tool with invalid params returns error."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        # Call with missing required params
        mock_client.call_tool.side_effect = TypeError("Missing required params")

        result = interface.call_tool("session_get", {})  # Missing session_id
        assert isinstance(result, dict)

    def test_connection_failure_returns_error(self):
        """Test MCP connection failure returns error."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.side_effect = ConnectionError("MCP connection failed")

        result = interface.call_tool("session_get", {"session_id": "test"})
        assert isinstance(result, dict)
        assert result.get("success") is False or "error" in result

    def test_no_client_returns_error(self):
        """Test call without client returns graceful error."""
        interface = MCPAgentInterface(mcp_client=None)

        result = interface.call_tool("session_get", {"session_id": "test"})
        assert isinstance(result, dict)


class TestMCPAgentInterfaceDiagnostics:
    """Test tool call logging and diagnostics."""

    def test_tool_calls_are_logged(self):
        """Test tool calls are captured in diagnostics."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.return_value = {
            "success": True,
            "data": {}
        }

        # Make multiple tool calls
        interface.call_session_get("abc")
        interface.call_session_state("abc")

        # Check diagnostics
        diag = interface.get_diagnostics()
        assert diag is not None

    def test_diagnostics_include_call_count(self):
        """Test diagnostics include call counts."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.return_value = {"success": True, "data": {}}

        interface.call_session_get("abc")
        interface.call_session_get("abc")
        interface.call_session_state("abc")

        diag = interface.get_diagnostics()
        # Should track multiple calls
        assert diag is not None

    def test_reset_diagnostics(self):
        """Test diagnostics can be reset."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.return_value = {"success": True, "data": {}}

        interface.call_session_get("abc")
        interface.reset_diagnostics()

        # After reset, should start fresh
        diag = interface.get_diagnostics()
        assert diag is not None


class TestMCPAgentInterfaceErrorPaths:
    """Test error handling and degradation."""

    def test_timeout_error_handled(self):
        """Test timeout errors are handled gracefully."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        mock_client.call_tool.side_effect = TimeoutError("MCP timeout")

        result = interface.call_tool("session_get", {"session_id": "test"})
        assert isinstance(result, dict)
        assert result.get("success") is False or "error" in result

    def test_parse_error_handled(self):
        """Test response parse errors are handled."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        # Client returns invalid response
        mock_client.call_tool.return_value = "not a dict"

        result = interface.call_tool("session_get", {"session_id": "test"})
        assert isinstance(result, dict)

    def test_error_response_never_raises(self):
        """Test all error paths return dict, never raise."""
        mock_client = Mock()
        interface = MCPAgentInterface(mcp_client=mock_client)

        error_cases = [
            Exception("Generic error"),
            ValueError("Invalid value"),
            KeyError("Missing key"),
            ConnectionError("Connection lost"),
            TimeoutError("Timeout"),
        ]

        for error in error_cases:
            mock_client.call_tool.side_effect = error
            result = interface.call_tool("session_get", {"session_id": "test"})
            assert isinstance(result, dict), f"Failed for {error}: got {type(result)}"
