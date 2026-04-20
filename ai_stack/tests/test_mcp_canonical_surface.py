import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_canonical_surface import CanonicalMCPSurface


class TestCanonicalMCPSurface:
    """Test canonical MCP surface for AI use."""

    @pytest.fixture
    def surface(self):
        return CanonicalMCPSurface()

    def test_surface_defines_all_tools(self, surface):
        """Surface defines all expected tools."""
        tools = surface.list_tool_specs()

        tool_names = {t["name"] for t in tools}
        expected = {
            "wos.session.get",
            "wos.session.state",
            "wos.session.logs",
            "wos.session.diag",
            "wos.session.execute_turn"
        }

        assert expected == tool_names

    def test_tool_specs_include_schema(self, surface):
        """Tool specs include input/output schemas."""
        tools = surface.list_tool_specs()

        for tool in tools:
            assert "input_schema" in tool
            assert "output_schema" in tool
            assert "description" in tool

    def test_surface_is_ai_friendly(self, surface):
        """Surface is formatted for AI agent consumption."""
        spec = surface.get_tool_spec("wos.session.execute_turn")

        assert spec is not None
        assert spec["description"] is not None
        assert len(spec["description"]) > 10
