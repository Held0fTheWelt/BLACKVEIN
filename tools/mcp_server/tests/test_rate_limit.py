import pytest
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
