import pytest
from ai_stack.limit_inventory import (
    MCP_RATE_LIMIT_LABEL,
    MCP_RATE_LIMIT_MAX_CALLS,
    MCP_RATE_LIMIT_WINDOW_SECONDS,
)
from tools.mcp_server.rate_limiter import RateLimiter
from tools.mcp_server.server import McpServer


def test_allows_requests_under_limit():
    """Rate limiter allows requests under limit."""
    limiter = RateLimiter(max_calls=5, window_seconds=60)
    for i in range(5):
        assert limiter.is_allowed("client-1") is True


def test_blocks_requests_over_limit():
    """Rate limiter blocks requests over limit."""
    limiter = RateLimiter(max_calls=2, window_seconds=60)
    assert limiter.is_allowed("client-2") is True
    assert limiter.is_allowed("client-2") is True
    assert limiter.is_allowed("client-2") is False


def test_rate_limit_per_client():
    """Rate limit is per client ID."""
    limiter = RateLimiter(max_calls=1, window_seconds=60)
    assert limiter.is_allowed("client-a") is True
    assert limiter.is_allowed("client-a") is False
    assert limiter.is_allowed("client-b") is True


def test_server_rate_limit_uses_stable_client_key_not_trace_id(monkeypatch):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", "healthy")
    server = McpServer()
    server.rate_limiter = RateLimiter(max_calls=2, window_seconds=60)
    server.registry.get("wos.system.health").handler = lambda _args: {"status": "healthy"}
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "wos.system.health", "arguments": {}},
    }

    assert "result" in server.dispatch({**request, "id": 1}, "trace-1")
    assert "result" in server.dispatch({**request, "id": 2}, "trace-2")
    response = server.dispatch({**request, "id": 3}, "trace-3")

    assert response["error"]["code"] == -32002
    assert MCP_RATE_LIMIT_LABEL in response["error"]["message"]


def test_server_uses_central_mcp_limit_inventory(monkeypatch):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", "healthy")
    server = McpServer()

    assert server.rate_limiter.max_calls == MCP_RATE_LIMIT_MAX_CALLS
    assert server.rate_limiter.window_seconds == MCP_RATE_LIMIT_WINDOW_SECONDS

    health_tool = next(t for t in server.registry.list_tools() if t["canonical_name"] == "wos.system.health")
    assert health_tool["rate_limit"]["limit"] == MCP_RATE_LIMIT_LABEL
    assert health_tool["rate_limit"]["source"] == "mcp_json_rpc_dispatch"
    assert health_tool["rate_limit"]["tool"] == "wos.system.health"
