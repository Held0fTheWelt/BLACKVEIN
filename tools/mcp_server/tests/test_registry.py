from ai_stack.mcp_canonical_surface import CANONICAL_MCP_TOOL_DESCRIPTORS, verify_catalog_names_alignment
from tools.mcp_server.tools_registry import create_default_registry, cursor_safe_name


def test_tools_list_returns_expected_tools():
    registry = create_default_registry()
    tools = registry.list_tools()
    assert len(tools) == len(CANONICAL_MCP_TOOL_DESCRIPTORS)

    # tools/list emits the cursor-safe wire form; canonical_name preserves
    # the dotted M1 identity. See tools/mcp_server/tools_registry.py and
    # docs/mcp/12_M1_canonical_parity.md.
    wire_names = {tool["name"] for tool in tools}
    canonical_names = {tool["canonical_name"] for tool in tools}
    expected_canonical = {d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS}
    expected_wire = {cursor_safe_name(n) for n in expected_canonical}
    assert wire_names == expected_wire
    assert canonical_names == expected_canonical

    health_tool = next(t for t in tools if t["canonical_name"] == "wos.system.health")
    assert health_tool["name"] == "wos_system_health"
    assert health_tool["permission"] == "read"
    assert health_tool["tool_class"] == "read_only"
    assert health_tool["authority_source"] == "backend_http_authority"
    assert health_tool["rate_limit"]["limit"] == "30 per minute"
    assert health_tool["rate_limit"]["source"] == "mcp_json_rpc_dispatch"
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
        assert "canonical_name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert "permission" in tool
        assert "tool_class" in tool
        assert "authority_source" in tool
        assert "implementation_status" in tool
        assert "governance" in tool
        assert "rate_limit" in tool


def test_session_create_is_write_capable():
    registry = create_default_registry()
    tool = registry.get("wos.session.create")
    assert tool is not None
    assert tool.tool_class.value == "write_capable"


def test_execute_turn_is_write_capable():
    registry = create_default_registry()
    tool = registry.get("wos.session.execute_turn")
    assert tool is not None
    assert tool.tool_class.value == "write_capable"


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
