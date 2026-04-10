"""Static MCP resource and prompt catalog specs (suite attribution).

Single source for ``tools.mcp_server.resource_prompt_support`` and backend cockpit counts.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ai_stack.mcp_canonical_surface import CANONICAL_MCP_TOOL_DESCRIPTORS, McpSuite

# (uri, name, description, suite)
MCP_RESOURCE_SPECS: tuple[tuple[str, str, str, McpSuite], ...] = (
    (
        "wos://system/health",
        "system_health",
        "Backend health JSON (GET /api/v1/health)",
        McpSuite.wos_admin,
    ),
    (
        "wos://mcp/operator_truth",
        "operator_truth",
        "MCP operator truth aggregate; optional query probe_backend=true|false",
        McpSuite.wos_admin,
    ),
    (
        "wos://capabilities/catalog",
        "capabilities_catalog",
        "Capability catalog with governance metadata",
        McpSuite.wos_admin,
    ),
    (
        "wos://session/{session_id}",
        "session_snapshot",
        "Backend session snapshot; substitute {session_id}",
        McpSuite.wos_admin,
    ),
    (
        "wos://session/{session_id}/diagnostics",
        "session_diagnostics",
        "Session diagnostics bundle",
        McpSuite.wos_runtime_read,
    ),
    (
        "wos://session/{session_id}/state",
        "session_state",
        "World-engine session state snapshot",
        McpSuite.wos_runtime_read,
    ),
    (
        "wos://session/{session_id}/logs",
        "session_logs",
        "Session logs; optional query limit=N (default 100)",
        McpSuite.wos_runtime_read,
    ),
    (
        "wos://content/modules",
        "content_modules_list",
        "List module ids under content/modules",
        McpSuite.wos_author,
    ),
    (
        "wos://content/module/{module_id}",
        "content_module_detail",
        "Module file manifest; substitute {module_id}",
        McpSuite.wos_author,
    ),
)

# (prompt_name, title, description, suite)
MCP_PROMPT_SPECS: tuple[tuple[str, str, str, McpSuite], ...] = (
    (
        "wos-admin-session-triage",
        "Admin: triage a weak run",
        "Call resources: health, operator_truth, then session snapshot for the backend session_id.",
        McpSuite.wos_admin,
    ),
    (
        "wos-runtime-read-trace-review",
        "Runtime read: trace review order",
        "For a session_id, read resources in order: diagnostics, state, logs.",
        McpSuite.wos_runtime_read,
    ),
    (
        "wos-author-module-spotcheck",
        "Author: module spot-check",
        "List modules (resource wos://content/modules), then read wos://content/module/{module_id}.",
        McpSuite.wos_author,
    ),
    (
        "wos-ai-research-bundle",
        "AI: bounded research bundle",
        "Use research tools only: explore with mandatory budget → validate → bundle.build (review-bound).",
        McpSuite.wos_ai,
    ),
)


def mcp_exposure_counts_by_suite() -> dict[str, dict[str, int]]:
    """Return tool/resource/prompt counts per suite id (e.g. wos-admin)."""
    out: dict[str, dict[str, int]] = defaultdict(lambda: {"tools": 0, "resources": 0, "prompts": 0})
    for d in CANONICAL_MCP_TOOL_DESCRIPTORS:
        key = d.mcp_suite.value
        out[key]["tools"] += 1
    for _u, _n, _d, suite in MCP_RESOURCE_SPECS:
        out[suite.value]["resources"] += 1
    for _name, _t, _desc, suite in MCP_PROMPT_SPECS:
        out[suite.value]["prompts"] += 1
    return {k: dict(v) for k, v in out.items()}


def mcp_suite_registry_rows() -> list[dict[str, Any]]:
    """Stable suite list for cockpit overview (all five suites, zeros if no tools)."""
    canonical = {s.value for s in McpSuite}
    counts = mcp_exposure_counts_by_suite()
    rows = []
    for suite_id in sorted(canonical):
        c = counts.get(suite_id, {"tools": 0, "resources": 0, "prompts": 0})
        rows.append(
            {
                "suite_name": suite_id,
                "display_name": suite_id,
                "tool_count": c["tools"],
                "resource_count": c["resources"],
                "prompt_count": c["prompts"],
            }
        )
    return rows
