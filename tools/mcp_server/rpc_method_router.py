"""JSON-RPC method routing for MCP server (DS-029: flat dispatch helpers)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .server import McpServer


def route_mcp_method(server: McpServer, method: str | None, params: dict, trace_id: str) -> dict:
    """Invoke the handler for a known MCP method; raise ValueError if unknown."""
    if method == "initialize":
        return server.handle_initialize(params)
    if method == "tools/list":
        return server.handle_tools_list(params)
    if method == "tools/call":
        return server.handle_tools_call(params, trace_id)
    if method == "resources/list":
        return server.handle_resources_list(params)
    if method == "resources/read":
        return server.handle_resources_read(params, trace_id)
    if method == "prompts/list":
        return server.handle_prompts_list(params)
    if method == "prompts/get":
        return server.handle_prompts_get(params)
    raise ValueError(f"Unknown method: {method}")
