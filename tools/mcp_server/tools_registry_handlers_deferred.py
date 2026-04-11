"""Stub handlers for canonical tools not wired in the active MCP suite."""

from __future__ import annotations

from typing import Any, Callable

from ai_stack.mcp_canonical_surface import McpImplementationStatus


def deferred_stub_handler_factory(name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            "code": "NOT_IMPLEMENTED",
            "reason": f"{name} is not available in this phase",
            "implementation_status": McpImplementationStatus.deferred_stub.value,
            "authority_note": "deferred_stub_non_authoritative",
        }

    return handler
