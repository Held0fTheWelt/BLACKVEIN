"""Focused WOS_VSL MVP closure checks (Docker / CI entrypoint-friendly)."""

from ai_stack.wos_vsl_mcp_metrics import (
    MVP_HIGH_RISK_WRITE_TOOL_MAX,
    MVP_READ_VIA_RESOURCE_MIN,
    high_risk_mcp_mutation_tool_count,
    read_via_resource_share,
    write_capable_tool_count,
)


def test_write_capable_tools_within_roadmap_budget():
    assert write_capable_tool_count() <= MVP_HIGH_RISK_WRITE_TOOL_MAX


def test_high_risk_mutation_tools_within_roadmap_budget():
    assert high_risk_mcp_mutation_tool_count() <= MVP_HIGH_RISK_WRITE_TOOL_MAX


def test_read_via_resource_share_meets_mvp_floor():
    assert read_via_resource_share() >= MVP_READ_VIA_RESOURCE_MIN
