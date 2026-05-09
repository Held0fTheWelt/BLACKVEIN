"""MCP ``CallToolResult`` wire format for ``tools/call`` success payloads.

Strict MCP hosts (including Cursor's agent bridge) expect tool output under
``result.content[]`` with ``type: "text"`` and JSON in ``text``. Returning a
bare dict as ``result`` leaves those clients with an empty tool surface.

See MCP specification: tool call results use a ``content`` array (commonly ``type: "text"`` + JSON string).
"""

from __future__ import annotations

import json
from typing import Any


def wrap_call_tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Return MCP ``CallToolResult`` wrapping ``payload`` as JSON text."""
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return {"content": [{"type": "text", "text": text}]}


def unwrap_call_tool_result(result: Any) -> dict[str, Any] | None:
    """Extract inner tool dict from ``CallToolResult``; support legacy bare dict."""
    if not isinstance(result, dict):
        return None
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and str(first.get("type") or "").strip().lower() == "text":
            raw = first.get("text")
            if isinstance(raw, str) and raw.strip():
                try:
                    out = json.loads(raw)
                    return out if isinstance(out, dict) else None
                except json.JSONDecodeError:
                    return None
    if "content" not in result:
        return result
    return None
