import sys
sys.path.insert(0, "../")

import pytest
from tools_registry import create_default_registry


def test_tools_list_returns_three_tools():
    """tools/list returns expected tool structure."""
    registry = create_default_registry()
    tools = registry.list_tools()
    assert len(tools) == 3
    assert tools[0]["name"] == "wos.system.health"
    assert tools[0]["permission"] == "read"


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
