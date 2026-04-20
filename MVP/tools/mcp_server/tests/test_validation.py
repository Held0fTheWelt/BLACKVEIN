import pytest
from tools.mcp_server.server import McpServer
from tools.mcp_server.errors import InvalidInputError


def test_missing_required_field_raises_error():
    """Input validation rejects missing required fields."""
    server = McpServer()
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "wos.session.create",
            "arguments": {}
        }
    }
    response = server.dispatch(request, "trace-1")
    assert "error" in response
    assert response["error"]["code"] == -32602
