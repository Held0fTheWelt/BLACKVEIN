import json
from unittest.mock import Mock, patch

import pytest
from ai_stack.mcp_canonical_surface import CANONICAL_MCP_TOOL_DESCRIPTORS
from tools.mcp_server.server import McpServer


def test_tools_list_valid_response():
    """tools/list returns valid response structure."""
    server = McpServer()
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    response = server.dispatch(request, "trace-1")
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert "tools" in response["result"]
    assert len(response["result"]["tools"]) == len(CANONICAL_MCP_TOOL_DESCRIPTORS)


def test_unknown_tool_returns_error():
    """Calling unknown tool returns TOOL_NOT_FOUND error."""
    server = McpServer()
    request = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "unknown.tool", "arguments": {}}}
    response = server.dispatch(request, "trace-2")
    assert "error" in response
    assert response["error"]["code"] == -32000
    assert "unknown.tool" in response["error"]["message"]


def test_tools_call_success():
    """tools/call with valid tool returns result (mocked backend)."""
    with patch("tools.mcp_server.backend_client.BackendClient.health") as mock_health:
        mock_health.return_value = {"status": "ok"}
        server = McpServer()
        request = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "wos.system.health", "arguments": {}}}
        response = server.dispatch(request, "trace-3")
        assert "result" in response
        assert response["result"]["status"] == "healthy"


def test_unknown_method_returns_error():
    """Unknown method returns METHOD_NOT_FOUND error."""
    server = McpServer()
    request = {"jsonrpc": "2.0", "id": 4, "method": "unknown.method", "params": {}}
    response = server.dispatch(request, "trace-4")
    assert "error" in response
    assert response["error"]["code"] == -32601


def test_initialize_returns_server_info():
    """initialize request returns server info."""
    server = McpServer()
    request = {"jsonrpc": "2.0", "id": 5, "method": "initialize", "params": {}}
    response = server.dispatch(request, "trace-5")
    assert "result" in response
    assert "serverInfo" in response["result"]
    assert response["result"]["serverInfo"]["name"] == "wos-mcp-server"
