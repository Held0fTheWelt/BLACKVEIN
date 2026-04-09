"""MCP M1 named gate coverage (G-MCP-01 … G-MCP-07)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_stack.mcp_canonical_surface import (
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    McpOperatingProfile,
    build_compact_mcp_operator_truth,
    capability_records_for_mcp,
    classify_mcp_no_eligible_discipline,
    verify_catalog_names_alignment,
)
from tools.mcp_server.server import McpServer
from tools.mcp_server.tools_registry import create_default_registry

REPO_ROOT = Path(__file__).resolve().parents[3]


REQUIRED_OPERATOR_TRUTH_KEYS = frozenset(
    {
        "grammar_version",
        "authority_source",
        "startup_profile",
        "operational_state",
        "route_status",
        "available_vs_deferred",
        "governance_posture",
        "readiness_posture",
        "no_eligible_operator_meaning",
        "runtime_authority_preservation",
    }
)


def test_g_mcp_01_authority_parity_registry_matches_descriptors():
    reg = create_default_registry()
    names_reg = set(reg.list_tool_names())
    names_desc = {d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS}
    assert names_reg == names_desc
    align = verify_catalog_names_alignment()
    assert align["aligned"] is True
    cap_names = {r["name"] for r in capability_records_for_mcp()}
    assert cap_names == set(align["expected"])


def test_g_mcp_02_governance_visible_on_registry_and_catalog():
    reg = create_default_registry()
    for t in reg.list_tools():
        gov = t["governance"]
        assert set(gov) >= {
            "published_vs_draft",
            "canonical_vs_supporting",
            "runtime_safe_vs_internal_only",
            "writers_room_visible_vs_runtime_hidden",
            "reviewable_vs_publishable_posture",
        }
    for row in capability_records_for_mcp():
        gp = row["governance_posture"]
        assert set(gp) >= {
            "published_vs_draft",
            "canonical_vs_supporting",
            "runtime_safe_vs_internal_only",
            "writers_room_visible_vs_runtime_hidden",
            "reviewable_vs_publishable_posture",
        }


def test_g_mcp_03_write_capable_denied_under_review_safe(monkeypatch):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", McpOperatingProfile.review_safe.value)
    with patch("tools.mcp_server.backend_client.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            server = McpServer()
            req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "wos.session.create", "arguments": {"module_id": "m"}},
            }
            resp = server.dispatch(req, "trace-rs")
            assert "error" in resp
            assert resp["error"]["code"] == -32003


def test_g_mcp_03_audit_log_includes_canonical_fields(monkeypatch, capsys):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", McpOperatingProfile.healthy.value)
    with patch("tools.mcp_server.backend_client.BackendClient.health") as mh:
        mh.return_value = {"ok": True}
        server = McpServer()
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "wos.system.health", "arguments": {}},
        }
        server.dispatch(req, "trace-audit")
    err = capsys.readouterr().err
    assert '"type": "tool_call"' in err
    assert '"tool_class": "read_only"' in err
    assert '"authority_source": "backend_http_authority"' in err
    assert '"operating_profile": "healthy"' in err


def test_g_mcp_04_no_eligible_honesty_tokens():
    ne_mis = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=False,
        implemented_tool_count=5,
        deferred_stub_count=4,
        profile=McpOperatingProfile.healthy,
    )
    assert ne_mis["discipline_worst_case"] == "misconfigured"

    ne_deg = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=True,
        implemented_tool_count=5,
        deferred_stub_count=4,
        profile=McpOperatingProfile.degraded,
    )
    assert ne_deg["discipline_worst_case"] == "degraded_but_controlled"

    ne_ti = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=True,
        implemented_tool_count=5,
        deferred_stub_count=4,
        profile=McpOperatingProfile.test_isolated,
    )
    assert ne_ti["discipline_worst_case"] == "test_isolated_empty_or_suppressed"

    ne_true = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=True,
        implemented_tool_count=0,
        deferred_stub_count=0,
        profile=McpOperatingProfile.healthy,
    )
    assert ne_true["discipline_worst_case"] == "true_no_eligible_adapter"

    ne_ok = classify_mcp_no_eligible_discipline(
        catalog_alignment_ok=True,
        implemented_tool_count=3,
        deferred_stub_count=1,
        profile=McpOperatingProfile.healthy,
    )
    assert ne_ok["applicable"] is False


def test_g_mcp_05_operator_truth_compact_shape():
    reg = create_default_registry()
    ot = build_compact_mcp_operator_truth(
        backend_reachable=None,
        catalog_alignment_ok=True,
        registry_tool_names=reg.list_tool_names(),
    )
    assert REQUIRED_OPERATOR_TRUTH_KEYS <= frozenset(ot.keys())
    assert len(json.dumps(ot)) < 8000


def test_g_mcp_06_no_capability_invoke_import_in_server():
    import tools.mcp_server.server as srv

    src = open(srv.__file__, encoding="utf-8").read()
    assert "CapabilityRegistry" not in src
    assert "create_default_capability_registry" not in src


def test_g_mcp_06_review_bound_tools_are_implemented(monkeypatch):
    """Verify review-bound session tools are now fully implemented."""
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", McpOperatingProfile.healthy.value)
    with patch("tools.mcp_server.backend_client.BackendClient._post") as mock_post:
        mock_post.return_value = {"status": "executed"}
        server = McpServer()
        req = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "wos.session.execute_turn", "arguments": {"session_id": "s1", "prompt": "test"}},
        }
        resp = server.dispatch(req, "trace-implemented")
        # Should succeed since tool is implemented
        assert "result" in resp or "error" not in resp


def test_g_mcp_07_closure_report_contains_gate_matrix():
    report_path = REPO_ROOT / "tests" / "reports" / "MCP_M1_CLOSURE_REPORT.md"
    assert report_path.is_file()
    text = report_path.read_text(encoding="utf-8")
    for n in range(1, 9):
        assert f"G-MCP-{n:02d}" in text
    assert "Status: final canonical closure evidence" in text
    assert "Canonical report authority" in text
    assert "Validation Commands" in text
    assert "Actual Results" in text
    assert (
        "python -m pytest ai_stack/tests/test_mcp_canonical_surface.py "
        "tools/mcp_server/tests/test_mcp_m1_gates.py tools/mcp_server/tests/test_rpc.py "
        "-q --tb=short --no-cov"
    ) in text
    assert "python -m pytest backend/tests/runtime/test_mcp_enrichment.py -q --tb=short --no-cov" in text


def test_g_mcp_08_closure_report_is_singular_m1_authority():
    report_dir = REPO_ROOT / "tests" / "reports"
    canonical = report_dir / "MCP_M1_CLOSURE_REPORT.md"
    assert canonical.is_file()
    canonical_text = canonical.read_text(encoding="utf-8")
    assert "Canonical report authority" in canonical_text
    candidates = sorted(report_dir.glob("*MCP_M1*REPORT*.md"))
    assert canonical in candidates
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if path == canonical:
            assert "Canonical report authority" in text
            continue
        assert "Superseded by tests/reports/MCP_M1_CLOSURE_REPORT.md" in text


def test_operating_profiles_resolve(monkeypatch):
    monkeypatch.setenv("WOS_MCP_OPERATING_PROFILE", "test_isolated")
    reg = create_default_registry()
    ot = build_compact_mcp_operator_truth(
        backend_reachable=None,
        catalog_alignment_ok=True,
        registry_tool_names=reg.list_tool_names(),
    )
    assert ot["startup_profile"] == "test_isolated"
    assert ot["operational_state"] == "test_isolated"
