"""Regression: unresolved free action must not take the deterministic short path."""

from __future__ import annotations

from pathlib import Path

pytest_plugins = ("ai_stack.tests.goc_yaml_cache_fixtures",)

import pytest

pytest.importorskip(
    "ai_stack.langgraph_runtime",
    reason="LangGraph/LangChain stack required for GoC runtime graph tests",
)

from ai_stack.tests.test_langgraph_runtime import _build_graph


def test_semantic_resolution_required_uses_thin_path_not_short_path(tmp_path: Path) -> None:
    """Unresolved free action requires AI semantics and still keeps the Director thin path."""
    result = _build_graph(tmp_path).run(
        session_id="s-interact-reg",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I am furious and attack your accusation right now.",
        trace_id="trace-interact-reg",
    )
    frame = result.get("player_action_frame") or {}
    assert frame.get("verb") == "semantic_resolution_required"
    assert frame.get("action_kind") == "semantic_resolution_required"
    assert frame.get("target_resolution_source") == "semantic_ai_resolution_required"
    assert frame.get("action_commit_policy") == "needs_clarification"

    nodes = (result.get("graph_diagnostics") or {}).get("nodes_executed") or result.get("nodes_executed") or []
    for required in (
        "resolve_player_action",
        "director_compose_realization",
        "realize_via_capabilities",
        "route_model",
        "invoke_model",
        "validate_seam",
        "commit_seam",
        "package_output",
    ):
        assert required in nodes
    assert "authoritative_action_resolution" not in nodes
    assert "goc_resolve_canonical_content" not in nodes
    assert "director_assess_scene" not in nodes

    repro = (result.get("graph_diagnostics") or {}).get("repro_metadata") or {}
    assert repro.get("action_resolution_short_path") is False
    assert repro.get("synthetic_short_path") is False
    assert repro.get("graph_path_summary") == "primary_invoke_langchain_only"
