import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.mcp_client.client import MCPClient


class TestMCPClient:
    """Test backend MCP client."""

    @pytest.fixture
    def mcp_client(self):
        return MCPClient()

    def test_client_can_call_session_get(self, mcp_client):
        """MCP client can call session.get tool."""
        result = mcp_client.call_tool(
            "wos.session.get",
            {"session_id": "s_test123"}
        )

        assert result["success"] is True
        assert "session_id" in result

    def test_client_enforces_operating_profile(self, mcp_client):
        """Client enforces operating profile access control."""
        result = mcp_client.call_tool(
            "wos.session.execute_turn",
            {
                "session_id": "s_test",
                "player_id": "p_1",
                "action": {"type": "move"}
            },
            operating_profile="read_only"
        )

        # Should fail because read_only cannot execute_turn
        assert result["success"] is False
        assert "unauthorized" in result.get("error", "").lower()

    def test_client_calls_world_engine(self, mcp_client):
        """Client forwards turn execution to world-engine."""
        result = mcp_client.call_tool(
            "wos.session.execute_turn",
            {
                "session_id": "s_test",
                "player_id": "p_1",
                "action": {"type": "move"}
            },
            operating_profile="execute"
        )

        assert result["success"] is True
        assert "new_turn_number" in result
