"""MCP canonical surface — no network; only ai_stack + stdlib."""

import builtins
import importlib
import sys

from ai_stack.mcp_canonical_surface import (
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    MCP_CATALOG_CAPABILITY_NAMES,
    build_compact_mcp_operator_truth,
    capability_records_for_mcp,
    resolve_mcp_operating_profile,
    verify_catalog_names_alignment,
)


def test_verify_catalog_names_alignment_succeeds():
    r = verify_catalog_names_alignment()
    assert r["aligned"] is True
    assert set(r["expected"]) == set(MCP_CATALOG_CAPABILITY_NAMES)


def test_capability_records_include_governance_and_tool_class():
    rows = capability_records_for_mcp()
    assert len(rows) == len(MCP_CATALOG_CAPABILITY_NAMES)
    for row in rows:
        assert "tool_class" in row
        assert "governance_posture" in row
        assert "authority_source" in row
        gp = row["governance_posture"]
        assert "published_vs_draft" in gp
        assert "canonical_vs_supporting" in gp


def test_operator_truth_compact_builds():
    names = [d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS]
    ot = build_compact_mcp_operator_truth(
        backend_reachable=None,
        catalog_alignment_ok=True,
        registry_tool_names=names,
    )
    assert ot["grammar_version"]
    assert ot["runtime_authority_preservation"]
    assert "no_eligible_operator_meaning" in ot
    assert "available_vs_deferred" in ot
    assert "governance_posture" in ot


def test_resolve_mcp_operating_profile_defaults_healthy(monkeypatch):
    monkeypatch.delenv("WOS_MCP_OPERATING_PROFILE", raising=False)
    assert resolve_mcp_operating_profile().value == "healthy"


def test_mcp_canonical_surface_import_does_not_require_optional_heavy_deps(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("langchain_core") or name == "numpy" or name.startswith("numpy."):
            raise ModuleNotFoundError(f"blocked optional dependency: {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    for module_name in ("ai_stack", "ai_stack.mcp_canonical_surface"):
        sys.modules.pop(module_name, None)
    module = importlib.import_module("ai_stack.mcp_canonical_surface")
    assert module.CANONICAL_MCP_TOOL_DESCRIPTORS
