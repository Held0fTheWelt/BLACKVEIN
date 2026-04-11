"""WOS_VSL MVP MCP measurement helpers (ROADMAP_MVP_WOS_VSL §10.3–10.5).

Used by tests and release-check scripts. Thresholds match the roadmap pilot table where noted.
"""

from __future__ import annotations

from ai_stack.mcp_canonical_surface import (
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    McpToolClass,
)

# Roadmap §10.3 — high-risk write tool count <= 5 (static inventory).
MVP_HIGH_RISK_WRITE_TOOL_MAX = 5

# Roadmap §10.3 — read-via-resource share >= 70% for *stable read surfaces* (MVP cut).
MVP_READ_VIA_RESOURCE_MIN = 0.7

# Tools that are stable, read-only observation surfaces and have a first-class MCP resource URI
# (docs/mcp/MVP_SUITE_MAP.md). Research/diagnostic one-offs are out of this denominator for MVP.
STABLE_READ_TOOLS_FOR_RESOURCE_METRIC: frozenset[str] = frozenset(
    {
        "wos.system.health",
        "wos.mcp.operator_truth",
        "wos.capabilities.catalog",
        "wos.session.get",
        "wos.session.diag",
        "wos.session.state",
        "wos.session.logs",
        "wos.goc.list_modules",
        "wos.goc.get_module",
    }
)

# Subset of stable reads that already have a ``resources/read`` implementation (see ``tools/mcp_server/resource_prompt_support``).
# When adding a new stable read tool, either add a resource URI or remove it from this set until the resource exists.
TOOLS_WITH_MCP_RESOURCE_IMPL: frozenset[str] = frozenset(
    {
        "wos.system.health",
        "wos.mcp.operator_truth",
        "wos.capabilities.catalog",
        "wos.session.get",
        "wos.session.diag",
        "wos.session.state",
        "wos.session.logs",
        "wos.goc.list_modules",
        "wos.goc.get_module",
    }
)


def write_capable_tool_count() -> int:
    """Count ``McpToolClass.write_capable`` tools in the canonical MCP strand."""
    return sum(1 for d in CANONICAL_MCP_TOOL_DESCRIPTORS if d.tool_class is McpToolClass.write_capable)


def high_risk_mcp_mutation_tool_count() -> int:
    """MVP pilot static count: write_capable tools plus ``wos.session.execute_turn`` (runtime mutation)."""
    names = {d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS}
    n = write_capable_tool_count()
    if "wos.session.execute_turn" in names:
        n += 1
    return n


def read_via_resource_share() -> float:
    """Share of stable read tools that have an MCP resource twin implemented (roadmap §10.3)."""
    stable = STABLE_READ_TOOLS_FOR_RESOURCE_METRIC
    if not stable:
        return 0.0
    covered = len(stable & TOOLS_WITH_MCP_RESOURCE_IMPL)
    return covered / len(stable)
