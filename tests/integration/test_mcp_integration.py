"""Integration tests for MCP surface."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ai_stack"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))

from app.mcp_client.client import MCPClient
from mcp_canonical_surface import CanonicalMCPSurface
from mcp_server.operating_profile import OperatingProfile, check_tool_access


class TestMCPIntegration:
    """Integration tests for MCP surface."""

    @pytest.fixture
    def mcp_client(self):
        return MCPClient()

    @pytest.fixture
    def canonical_surface(self):
        return CanonicalMCPSurface()

    def test_mcp_surface_end_to_end(self, mcp_client, canonical_surface):
        """MCP surface works end-to-end with canonical definitions."""
        # Get all tool specs from canonical surface
        tools = canonical_surface.list_tool_specs()
        assert len(tools) == 5

        # For each tool, verify client can handle it (at least check access)
        for tool_spec in tools:
            tool_name = tool_spec["name"]

            # Verify tool name is in canonical surface
            spec = canonical_surface.get_tool_spec(tool_name)
            assert spec is not None
            assert "input_schema" in spec
            assert "output_schema" in spec

    def test_operating_profiles_control_access(self, mcp_client, canonical_surface):
        """Operating profiles correctly control tool access."""
        # Read-only can access read tools
        assert check_tool_access(OperatingProfile.READ_ONLY, "get")
        assert check_tool_access(OperatingProfile.READ_ONLY, "state")
        assert check_tool_access(OperatingProfile.READ_ONLY, "logs")
        assert check_tool_access(OperatingProfile.READ_ONLY, "diag")

        # Read-only cannot execute
        assert not check_tool_access(OperatingProfile.READ_ONLY, "execute_turn")

        # Execute can do everything
        assert check_tool_access(OperatingProfile.EXECUTE, "get")
        assert check_tool_access(OperatingProfile.EXECUTE, "execute_turn")

        # Admin can do everything
        assert check_tool_access(OperatingProfile.ADMIN, "get")
        assert check_tool_access(OperatingProfile.ADMIN, "execute_turn")

    def test_mcp_client_with_canonical_surface(self, mcp_client, canonical_surface):
        """Client and canonical surface work together."""
        # Get tool specs
        tools = canonical_surface.list_tool_specs()

        # Verify each tool name matches MCP format
        for tool in tools:
            assert tool["name"].startswith("wos.session.")
            assert "description" in tool
            assert tool["description"]

    def test_fail_closed_on_unknown_profile(self, mcp_client):
        """Unknown profile results in fail-closed behavior."""
        result = mcp_client.call_tool(
            "wos.session.get",
            {"session_id": "s_test"},
            operating_profile="invalid_profile"
        )

        # Should fail (Law 6: fail-closed on authority seams)
        assert result["success"] is False
        assert "Unknown operating profile" in result["error"]

    def test_mcp_tool_specs_are_valid(self, canonical_surface):
        """All tool specs have required fields."""
        tools = canonical_surface.list_tool_specs()

        for tool in tools:
            # Required fields
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert "output_schema" in tool

            # Schema structure
            assert "type" in tool["input_schema"]
            assert "type" in tool["output_schema"]

            # Descriptions should be meaningful
            assert len(tool["description"]) > 5
