"""Regression: ontology ``interact`` fallback must not take the deterministic short path."""

from __future__ import annotations

from pathlib import Path

pytest_plugins = ("ai_stack.tests.goc_yaml_cache_fixtures",)

import pytest

pytest.importorskip(
    "ai_stack.langgraph_runtime",
    reason="LangGraph/LangChain stack required for GoC runtime graph tests",
)

from ai_stack.tests.test_goc_mvp_breadth_playability_regression import (
    HOST_OK,
    JsonAdapter,
    _executor,
)


def test_interact_fallback_uses_full_dramatic_pipeline_not_short_path(tmp_path: Path) -> None:
    """Unknown ontology verb resolves to ``interact`` — must keep director + model path."""
    narrative = (
        "Michel raises his voice, attacks your accusation, and threatens another fight "
        "if you continue under rising pressure in the room."
    )
    result = _executor(tmp_path, adapter=JsonAdapter(narrative)).run(
        session_id="s-interact-reg",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I am furious and attack your accusation right now.",
        trace_id="trace-interact-reg",
        host_experience_template=HOST_OK,
    )
    frame = result.get("player_action_frame") or {}
    assert frame.get("verb") == "interact"

    nodes = (result.get("graph_diagnostics") or {}).get("nodes_executed") or result.get("nodes_executed") or []
    assert "authoritative_action_resolution" not in nodes
    assert "invoke_model" in nodes
    assert result.get("selected_scene_function")

    repro = (result.get("graph_diagnostics") or {}).get("repro_metadata") or {}
    assert repro.get("action_resolution_short_path") is False
    assert repro.get("synthetic_short_path") is False
    assert repro.get("graph_path_summary") == "primary_invoke_langchain_only"
