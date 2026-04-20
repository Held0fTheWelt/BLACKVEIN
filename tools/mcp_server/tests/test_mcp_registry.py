import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import MCPRegistry, ToolSpec


class TestMCPRegistry:
    """Test MCP tool registry."""

    @pytest.fixture
    def registry(self):
        return MCPRegistry()

    def test_register_and_retrieve_tool(self, registry):
        """Can register and retrieve tools."""
        spec = ToolSpec(
            name="test_tool",
            description="Test tool",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            handler=lambda x: x
        )

        registry.register_tool(spec)
        retrieved = registry.get_tool("test_tool")

        assert retrieved is not None
        assert retrieved.name == "test_tool"

    def test_list_tools(self, registry):
        """Can list all registered tools."""
        spec1 = ToolSpec("tool1", "Tool 1", {}, {}, lambda x: x)
        spec2 = ToolSpec("tool2", "Tool 2", {}, {}, lambda x: x)

        registry.register_tool(spec1)
        registry.register_tool(spec2)

        tools = registry.list_tools()
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools

    def test_call_tool_success(self, registry):
        """Tool calls succeed with valid input."""
        spec = ToolSpec(
            name="add",
            description="Add numbers",
            input_schema={},
            output_schema={},
            handler=lambda x: x.get("a", 0) + x.get("b", 0)
        )

        registry.register_tool(spec)
        result = registry.call_tool("add", {"a": 5, "b": 3})

        assert result["success"] is True
        assert result["result"] == 8

    def test_call_tool_not_found(self, registry):
        """Tool not found returns error."""
        result = registry.call_tool("nonexistent", {})
        assert result["success"] is False
        assert "not found" in result["error"]
