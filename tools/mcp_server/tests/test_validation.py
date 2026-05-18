import pytest
from tools.mcp_server.server import McpServer
from tools.mcp_server.errors import InvalidInputError


def test_missing_required_field_raises_error():
    """Handler rejects missing player-session creation identifiers."""
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
    assert "result" in response
    text = response["result"]["content"][0]["text"]
    assert "run_id, template_id, runtime_profile_id, or module_id required" in text
