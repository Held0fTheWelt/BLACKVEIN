"""MCP resources, prompts, and ``WOS_MCP_SUITE`` filtering."""

from unittest.mock import patch

from ai_stack.mcp_canonical_surface import McpSuite, canonical_tool_names_for_suite
from tools.mcp_server.server import McpServer
from tools.mcp_server.tools_registry import create_default_registry


def test_resources_list_returns_entries(monkeypatch):
    monkeypatch.delenv("WOS_MCP_SUITE", raising=False)
    server = McpServer()
    resp = server.dispatch(
        {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}},
        "trace-r1",
    )
    assert "result" in resp
    r = resp["result"]["resources"]
    assert len(r) >= 8
    uris = {x["uri"] for x in r}
    assert "wos://system/health" in uris
    assert "wos://session/{session_id}/diagnostics" in uris


def test_resources_read_health_mock(monkeypatch):
    monkeypatch.delenv("WOS_MCP_SUITE", raising=False)
    with patch("tools.mcp_server.backend_client.BackendClient.health") as mh:
        mh.return_value = {"ok": True}
        server = McpServer()
        resp = server.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "resources/read",
                "params": {"uri": "wos://system/health"},
            },
            "trace-r2",
        )
    assert "result" in resp
    contents = resp["result"]["contents"]
    assert contents[0]["mimeType"] == "application/json"
    assert "ok" in contents[0]["text"]


def test_prompts_list_and_get(monkeypatch):
    monkeypatch.delenv("WOS_MCP_SUITE", raising=False)
    server = McpServer()
    lst = server.dispatch(
        {"jsonrpc": "2.0", "id": 3, "method": "prompts/list", "params": {}},
        "trace-p1",
    )
    names = {p["name"] for p in lst["result"]["prompts"]}
    assert "wos-admin-session-triage" in names

    got = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "prompts/get",
            "params": {"name": "wos-admin-session-triage"},
        },
        "trace-p2",
    )
    assert "messages" in got["result"]


def test_suite_filter_limits_tools(monkeypatch):
    monkeypatch.setenv("WOS_MCP_SUITE", McpSuite.wos_admin.value)
    reg = create_default_registry(suite_filter=McpSuite.wos_admin)
    expected = set(canonical_tool_names_for_suite(McpSuite.wos_admin))
    assert set(reg.list_tool_names()) == expected


def test_suite_filter_hides_foreign_prompts(monkeypatch):
    monkeypatch.setenv("WOS_MCP_SUITE", McpSuite.wos_runtime_control.value)
    server = McpServer()
    resp = server.dispatch(
        {"jsonrpc": "2.0", "id": 5, "method": "prompts/list", "params": {}},
        "trace-p3",
    )
    assert resp["result"]["prompts"] == []


def test_initialize_advertises_capabilities(monkeypatch):
    monkeypatch.delenv("WOS_MCP_SUITE", raising=False)
    server = McpServer()
    resp = server.dispatch(
        {"jsonrpc": "2.0", "id": 6, "method": "initialize", "params": {}},
        "trace-init",
    )
    caps = resp["result"]["capabilities"]
    assert "resources" in caps
    assert "prompts" in caps
    assert "tools" in caps
    assert resp["result"]["serverInfo"].get("wos_mcp_suite") == "all"
