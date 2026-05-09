"""CallToolResult wrap/unwrap for strict MCP hosts."""

from __future__ import annotations

from tools.mcp_server.call_tool_result import unwrap_call_tool_result, wrap_call_tool_result


def test_wrap_unwrap_roundtrip():
    inner = {"ok": True, "n": 1, "s": "x"}
    wrapped = wrap_call_tool_result(inner)
    assert "content" in wrapped
    assert wrapped["content"][0]["type"] == "text"
    out = unwrap_call_tool_result(wrapped)
    assert out == inner


def test_unwrap_legacy_bare_dict():
    bare = {"status": "healthy"}
    assert unwrap_call_tool_result(bare) == bare
