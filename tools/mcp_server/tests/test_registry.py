import pytest
from tools.mcp_server.tools_registry import create_default_registry


def test_tools_list_returns_nine_tools():
    """tools/list returns expected tool structure."""
    registry = create_default_registry()
    tools = registry.list_tools()
    assert len(tools) == 9

    # Check tool names are present
    tool_names = {tool["name"] for tool in tools}
    expected_names = {
        "wos.system.health",
        "wos.session.create",
        "wos.goc.list_modules",
        "wos.goc.get_module",
        "wos.content.search",
        "wos.session.get",
        "wos.session.execute_turn",
        "wos.session.logs",
        "wos.session.state",
    }
    assert tool_names == expected_names

    # Check first tool structure
    health_tool = next(t for t in tools if t["name"] == "wos.system.health")
    assert health_tool["permission"] == "read"


def test_tool_has_required_fields():
    """Each tool has name, description, inputSchema, permission."""
    registry = create_default_registry()
    tools = registry.list_tools()
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert "permission" in tool


def test_get_tool_by_name():
    """Can retrieve tool from registry."""
    registry = create_default_registry()
    tool = registry.get("wos.system.health")
    assert tool is not None
    assert tool.name == "wos.system.health"


def test_get_nonexistent_tool_returns_none():
    """Getting nonexistent tool returns None."""
    registry = create_default_registry()
    tool = registry.get("nonexistent")
    assert tool is None
