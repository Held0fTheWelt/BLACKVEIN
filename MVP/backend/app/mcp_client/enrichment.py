"""MCP preflight enrichment for AI execution."""

import time
from typing import Any

from app.mcp_client.client import MCPEnrichmentClient, MCPToolError
from app.observability.audit_log import log_mcp_tool_call


# Preflight tools in priority order (primary, supplemental, optional)
_PREFLIGHT_TOOLS = [
    ("wos.session.get", "primary"),
    ("wos.session.state", "supplemental"),
    ("wos.session.logs", "supplemental"),
    ("wos.session.diag", "optional"),
]


def build_mcp_enrichment(
    session_id: str,
    trace_id: str | None,
    client: MCPEnrichmentClient,
    *,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    """Build MCP context enrichment by calling operator endpoints.

    Calls tools in priority order. Any tool failure is graceful (warning logged,
    turn continues). All tool calls are logged via audit log.

    Args:
        session_id: Session ID
        trace_id: Trace ID for observability
        client: MCP client to use for tool calls
        timeout_seconds: Timeout per tool call

    Returns:
        dict with:
        - session_snapshot: wos.session.get result or None
        - state_snapshot: wos.session.state result or None
        - recent_logs: wos.session.logs result or None
        - diagnostics: wos.session.diag result or None
        - tool_calls: list of {tool_name, success, error, duration_ms}
        - warnings: list of warning messages
        - call_count: number of tool calls attempted
    """
    enrichment = {
        "session_snapshot": None,
        "state_snapshot": None,
        "recent_logs": None,
        "diagnostics": None,
        "tool_calls": [],
        "warnings": [],
        "call_count": 0,
    }

    for tool_name, priority in _PREFLIGHT_TOOLS:
        enrichment["call_count"] += 1
        start_time = time.time()

        try:
            result = client.call_tool(tool_name, {"session_id": session_id}, timeout_seconds=timeout_seconds)
            duration_ms = int((time.time() - start_time) * 1000)

            # Log success
            log_mcp_tool_call(trace_id, session_id, tool_name, duration_ms, success=True)

            # Store result
            _store_tool_result(enrichment, tool_name, result)

            enrichment["tool_calls"].append(
                {
                    "tool_name": tool_name,
                    "success": True,
                    "duration_ms": duration_ms,
                }
            )
        except MCPToolError as e:
            duration_ms = int((time.time() - start_time) * 1000)

            # Log failure
            log_mcp_tool_call(trace_id, session_id, tool_name, duration_ms, success=False, error=e.reason)

            # Add warning based on priority
            if priority == "primary":
                enrichment["warnings"].append(f"Primary tool '{tool_name}' failed: {e.reason}")
            else:
                enrichment["warnings"].append(f"Tool '{tool_name}' unavailable ({priority}): {e.reason}")

            enrichment["tool_calls"].append(
                {
                    "tool_name": tool_name,
                    "success": False,
                    "error": e.reason,
                    "duration_ms": duration_ms,
                }
            )

    return enrichment


def _store_tool_result(enrichment: dict[str, Any], tool_name: str, data: dict[str, Any]) -> None:
    """Store tool result in enrichment dict at appropriate key.

    Args:
        enrichment: Enrichment dict to update
        tool_name: Tool name (e.g., "wos.session.get")
        data: Tool result data
    """
    if tool_name == "wos.session.get":
        enrichment["session_snapshot"] = data
    elif tool_name == "wos.session.state":
        enrichment["state_snapshot"] = data
    elif tool_name == "wos.session.logs":
        enrichment["recent_logs"] = data
    elif tool_name == "wos.session.diag":
        enrichment["diagnostics"] = data
