"""MVP MCP suite map completeness — every canonical tool has a suite; every suite is non-empty."""

from ai_stack.mcp_canonical_surface import (
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    MCP_SUITES_ALL,
    McpSuite,
    canonical_tool_names_for_suite,
)


def test_every_canonical_tool_has_mcp_suite():
    for d in CANONICAL_MCP_TOOL_DESCRIPTORS:
        assert d.mcp_suite in MCP_SUITES_ALL, d.name


def test_every_suite_has_at_least_one_tool():
    for suite in MCP_SUITES_ALL:
        names = canonical_tool_names_for_suite(suite)
        assert len(names) >= 1, f"empty suite: {suite.value}"


def test_suite_tool_partition_covers_all_descriptors():
    all_assigned: set[str] = set()
    for suite in MCP_SUITES_ALL:
        all_assigned.update(canonical_tool_names_for_suite(suite))
    canonical_names = {d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS}
    assert all_assigned == canonical_names


def test_expected_suite_for_representative_tools():
    by_name = {d.name: d.mcp_suite for d in CANONICAL_MCP_TOOL_DESCRIPTORS}
    assert by_name["wos.session.create"] is McpSuite.wos_runtime_control
    assert by_name["wos.session.execute_turn"] is McpSuite.wos_runtime_control
    assert by_name["wos.session.diag"] is McpSuite.wos_runtime_read
    assert by_name["wos.goc.get_module"] is McpSuite.wos_author
    assert by_name["wos.research.explore"] is McpSuite.wos_ai
    assert by_name["wos.system.health"] is McpSuite.wos_admin
