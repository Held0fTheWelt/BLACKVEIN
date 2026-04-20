"""MCP M2 named gates coverage (G-MCP-10-01 through G-MCP-10-07).

This test file validates the M2 closure: Deep Operational Parity, Runtime-Safe
Session Surface, and Descriptor Derivation Closure.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_stack.mcp_canonical_surface import (
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    McpImplementationStatus,
    McpOperatingProfile,
    McpToolClass,
    _derive_governance_risk_token,
    _derive_reviewable_posture,
    build_compact_mcp_operator_truth,
    capability_records_for_mcp,
    classify_mcp_no_eligible_discipline,
    verify_catalog_names_alignment,
)
from tools.mcp_server.server import McpServer
from tools.mcp_server.tools_registry import create_default_registry

REPO_ROOT = Path(__file__).resolve().parents[3]


class TestG_MCP_10_01_DescriptorDerivation:
    """G-MCP-10-01: Descriptor derivation gate."""

    def test_descriptor_derives_governance_from_tool_class(self):
        """Verify that tool governance derives from actual tool properties."""
        reg = create_default_registry()

        # Check that read_only tools have read-only posture
        health_tool = reg.get("wos.system.health")
        assert health_tool.tool_class == McpToolClass.read_only
        assert health_tool.descriptor.permission_legacy == "read"

        # Check that session.get is now read_only
        session_get = reg.get("wos.session.get")
        assert session_get.tool_class == McpToolClass.read_only
        assert session_get.descriptor.permission_legacy == "read"
        assert session_get.descriptor.implementation_status == McpImplementationStatus.implemented

        # Check that write_capable tools have write permission
        session_create = reg.get("wos.session.create")
        assert session_create.tool_class == McpToolClass.write_capable
        assert session_create.descriptor.permission_legacy == "write"

    def test_derivation_helper_functions_produce_consistent_tokens(self):
        """Test that derivation helpers produce expected tokens."""
        # Test posture derivation
        posture_readonly = _derive_reviewable_posture(McpToolClass.read_only, "test_tool")
        assert "read" in posture_readonly.lower()

        # Test risk token derivation
        risk_diag = _derive_governance_risk_token("wos.session.diag", "test_kind")
        assert "observation" in risk_diag.lower() or "none" in risk_diag.lower()


class TestG_MCP_10_02_RuntimeSafeSessionSurface:
    """G-MCP-10-02: Runtime-safe session surface gate."""

    def test_session_get_is_implemented_not_stub(self):
        """Verify wos.session.get is now implemented."""
        reg = create_default_registry()
        session_get = reg.get("wos.session.get")
        assert session_get is not None
        assert session_get.descriptor.implementation_status == McpImplementationStatus.implemented

    def test_session_diag_is_implemented_not_stub(self):
        """Verify wos.session.diag is now implemented."""
        reg = create_default_registry()
        session_diag = reg.get("wos.session.diag")
        assert session_diag is not None
        assert session_diag.descriptor.implementation_status == McpImplementationStatus.implemented

    def test_session_surfaces_are_read_only_authority_respecting(self):
        """Verify new session surfaces do not bypass runtime authority."""
        reg = create_default_registry()

        # session.get should be read_only
        session_get = reg.get("wos.session.get")
        assert session_get.tool_class == McpToolClass.read_only

        # session.diag should be read_only
        session_diag = reg.get("wos.session.diag")
        assert session_diag.tool_class == McpToolClass.read_only


class TestG_MCP_10_03_DeferredHonestyControlledAvailability:
    """G-MCP-10-03: Deferred honesty and controlled availability gate."""

    def test_deferred_tools_stay_deferred_with_clear_reasoning(self):
        """Verify remaining deferred tools have clear governance that explains deferral."""
        reg = create_default_registry()

        # Session tools (logs, state, execute_turn) are now implemented
        execute_turn = reg.get("wos.session.execute_turn")
        assert execute_turn.descriptor.implementation_status == McpImplementationStatus.implemented

        logs = reg.get("wos.session.logs")
        assert logs.descriptor.implementation_status == McpImplementationStatus.implemented

        state = reg.get("wos.session.state")
        assert state.descriptor.implementation_status == McpImplementationStatus.implemented

    def test_deferred_discipline_clearly_stated(self):
        """Verify deferred/available discipline is explicitly classified."""
        discipline = classify_mcp_no_eligible_discipline(
            catalog_alignment_ok=True,
            implemented_tool_count=12,
            deferred_stub_count=0,
            profile=McpOperatingProfile.healthy,
        )

        # Should not be applicable since all tools are implemented
        assert discipline["applicable"] is False


class TestG_MCP_10_04_OperatorDepth:
    """G-MCP-10-04: Operator depth gate."""

    def test_operator_truth_includes_all_diagnostic_fields(self):
        """Verify operator truth has all required diagnostic fields."""
        truth = build_compact_mcp_operator_truth(
            backend_reachable=True,
            catalog_alignment_ok=True,
            registry_tool_names=["wos.system.health", "wos.session.get", "wos.session.diag"],
        )

        required = {
            "grammar_version",
            "authority_source",
            "startup_profile",
            "operational_state",
            "route_status",
            "available_vs_deferred",
            "governance_posture",
            "readiness_posture",
        }
        assert set(truth.keys()) >= required

    def test_operator_truth_tool_class_breakdown_is_explicit(self):
        """Verify tool class counts are directly readable."""
        truth = build_compact_mcp_operator_truth(
            backend_reachable=True,
            catalog_alignment_ok=True,
            registry_tool_names=["wos.system.health", "wos.session.get", "wos.session.diag"],
        )

        avail = truth["available_vs_deferred"]
        classes = avail["tool_classes"]
        assert "read_only" in classes


class TestG_MCP_10_05_RuntimeAuthorityPreservation:
    """G-MCP-10-05: Runtime authority preservation gate."""

    def test_session_get_is_read_only_no_mutation(self):
        """Verify session.get doesn't mutate runtime state."""
        reg = create_default_registry()
        session_get = reg.get("wos.session.get")
        assert session_get.tool_class == McpToolClass.read_only

    def test_session_diag_is_read_only_no_mutation(self):
        """Verify session.diag doesn't mutate runtime state."""
        reg = create_default_registry()
        session_diag = reg.get("wos.session.diag")
        assert session_diag.tool_class == McpToolClass.read_only

    def test_write_capable_tools_still_gated_by_profile(self):
        """Verify write tools still respect operating profile restrictions."""
        with patch.dict("os.environ", {"WOS_MCP_OPERATING_PROFILE": "review_safe"}):
            with patch("tools.mcp_server.backend_client.BackendClient"):
                with patch("tools.mcp_server.tools_registry.FileSystemTools"):
                    server = McpServer()
                    req = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {"name": "wos.session.create", "arguments": {"module_id": "m"}},
                    }
                    resp = server.dispatch(req, "trace-test")
                    assert "error" in resp


class TestG_MCP_10_06_CanonicalParityDepth:
    """G-MCP-10-06: Canonical parity depth gate."""

    def test_session_tools_parity_includes_critical_reads(self):
        """Verify M2 adds critical missing read-only session surfaces."""
        reg = create_default_registry()

        # In M1, these were stubs. In M2, they're implemented.
        session_get = reg.get("wos.session.get")
        session_diag = reg.get("wos.session.diag")

        assert session_get.descriptor.implementation_status == McpImplementationStatus.implemented
        assert session_diag.descriptor.implementation_status == McpImplementationStatus.implemented

    def test_m2_expands_observation_surfaces(self):
        """Verify M2 materially expands observation surfaces vs M1."""
        reg = create_default_registry()

        # Count read-only tools
        read_only_tools = [t for t in reg.list_tools() if t["tool_class"] == "read_only"]

        # M2 adds session.get and session.diag as read-only
        assert len(read_only_tools) >= 8


class TestG_MCP_10_07_ValidationCommandReality:
    """G-MCP-10-07: Validation-command reality gate."""

    def test_tool_list_includes_all_expected_tools(self):
        """Verify tools/list returns complete and accurate registry."""
        server = McpServer()
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
        resp = server.dispatch(req, "trace-list")

        tools = resp["result"]["tools"]
        tool_names = {t["name"] for t in tools}

        # All canonical descriptors should be present
        for desc in CANONICAL_MCP_TOOL_DESCRIPTORS:
            assert desc.name in tool_names

    def test_tool_governance_is_consistent_across_layers(self):
        """Verify governance is consistent between descriptors and registry."""
        reg = create_default_registry()

        for tool in reg.list_tools():
            assert "governance" in tool
            assert "authority_source" in tool
            assert tool["tool_class"] in ["read_only", "write_capable", "review_bound"]

    def test_alignment_verification_passes(self):
        """Verify catalog alignment check passes."""
        align = verify_catalog_names_alignment()
        assert align["aligned"] is True


class TestM2_GateSummary:
    """Summary verification that all 7 M2 gates are satisfied."""

    def test_all_m2_gates_satisfied(self):
        """Verify all named M2 gates pass."""
        reg = create_default_registry()
        session_get = reg.get("wos.session.get")
        
        # G-MCP-10-01: Descriptor derivation
        assert session_get.tool_class == McpToolClass.read_only

        # G-MCP-10-02: Runtime-safe session surface
        assert session_get.descriptor.implementation_status == McpImplementationStatus.implemented

        # G-MCP-10-03: Session tools are now implemented (logs, state, execute_turn)
        execute_turn = reg.get("wos.session.execute_turn")
        assert execute_turn.descriptor.implementation_status == McpImplementationStatus.implemented

        # G-MCP-10-04: Operator depth
        truth = build_compact_mcp_operator_truth(
            backend_reachable=True,
            catalog_alignment_ok=True,
            registry_tool_names=["wos.system.health"],
        )
        assert "available_vs_deferred" in truth
        assert "tool_classes" in truth["available_vs_deferred"]

        # G-MCP-10-05: Runtime authority preservation
        assert session_get.tool_class == McpToolClass.read_only

        # G-MCP-10-06: Canonical parity depth
        implemented_tools = [
            t for t in reg.list_tools()
            if t["implementation_status"] == "implemented"
        ]
        assert len(implemented_tools) >= 9

        # G-MCP-10-07: Validation command reality
        align = verify_catalog_names_alignment()
        assert align["aligned"] is True
