from ai_stack.mcp_canonical_surface import CANONICAL_MCP_TOOL_DESCRIPTORS, verify_catalog_names_alignment
from tools.mcp_server.tools_registry import create_default_registry


def test_tools_list_returns_expected_tools():
    registry = create_default_registry()
    tools = registry.list_tools()
    assert len(tools) == len(CANONICAL_MCP_TOOL_DESCRIPTORS)

    tool_names = {tool["name"] for tool in tools}
    expected_names = {d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS}
    assert tool_names == expected_names

    health_tool = next(t for t in tools if t["name"] == "wos.system.health")
    assert health_tool["permission"] == "read"
    assert health_tool["tool_class"] == "read_only"
    assert health_tool["authority_source"] == "backend_http_authority"
    assert "governance" in health_tool
    assert set(health_tool["governance"].keys()) == {
        "published_vs_draft",
        "canonical_vs_supporting",
        "runtime_safe_vs_internal_only",
        "writers_room_visible_vs_runtime_hidden",
        "reviewable_vs_publishable_posture",
    }


def test_tool_has_required_fields():
    registry = create_default_registry()
    tools = registry.list_tools()
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert "permission" in tool
        assert "tool_class" in tool
        assert "authority_source" in tool
        assert "implementation_status" in tool
        assert "governance" in tool


def test_session_create_is_write_capable():
    registry = create_default_registry()
    tool = registry.get("wos.session.create")
    assert tool is not None
    assert tool.tool_class.value == "write_capable"


def test_execute_turn_stub_is_review_bound():
    registry = create_default_registry()
    tool = registry.get("wos.session.execute_turn")
    assert tool is not None
    assert tool.tool_class.value == "review_bound"


def test_get_tool_by_name():
    registry = create_default_registry()
    tool = registry.get("wos.system.health")
    assert tool is not None
    assert tool.name == "wos.system.health"


def test_get_nonexistent_tool_returns_none():
    registry = create_default_registry()
    tool = registry.get("nonexistent")
    assert tool is None


def test_g_mcp_01_catalog_alignment():
    assert verify_catalog_names_alignment()["aligned"] is True
