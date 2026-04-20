import pytest
from tools.mcp_server.rate_limiter import RateLimiter


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
