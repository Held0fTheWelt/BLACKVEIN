"""MCP static catalog counts (cockpit + MCP server)."""

from ai_stack.mcp_canonical_surface import McpSuite
from ai_stack.mcp_static_catalog import mcp_exposure_counts_by_suite, mcp_suite_registry_rows


def test_mcp_suite_registry_rows_covers_all_suites():
    rows = mcp_suite_registry_rows()
    ids = {r["suite_name"] for r in rows}
    for s in McpSuite:
        assert s.value in ids


def test_mcp_exposure_counts_non_negative():
    c = mcp_exposure_counts_by_suite()
    assert c["wos-admin"]["tools"] >= 1
    assert c["wos-admin"]["resources"] >= 1
    assert all(v["tools"] >= 0 and v["resources"] >= 0 and v["prompts"] >= 0 for v in c.values())
