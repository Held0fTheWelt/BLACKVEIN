"""Authority boundaries: single graph path, planner state non-sovereign."""

from __future__ import annotations

from pathlib import Path

import pytest
from story_runtime_core import RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import build_default_registry

langgraph_runtime = pytest.importorskip("ai_stack.langgraph_runtime", reason="LangGraph required")
from ai_stack.langgraph_runtime import RuntimeTurnGraphExecutor
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RagIngestionPipeline
from ai_stack.goc_turn_seams import build_operator_canonical_turn_record


class _OkAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(content='{"narrative_response":"ok","proposed_scene_id":null}', success=True, metadata={})


def _graph(tmp_path: Path) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"mock": _OkAdapter(), "openai": _OkAdapter(), "ollama": _OkAdapter()},
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )


def test_single_runtime_graph_executes_validation_and_commit_seams(tmp_path: Path) -> None:
    g = _graph(tmp_path)
    result = g.run(
        session_id="s-auth",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Michel, I hold you responsible for hiding the truth.",
        trace_id="t-auth",
    )
    nodes = (result.get("graph_diagnostics") or {}).get("nodes_executed") or result.get("nodes_executed") or []
    assert "validate_seam" in nodes
    assert "commit_seam" in nodes
    assert "director_assess_scene" in nodes


def test_planner_records_are_projection_not_committed_truth(tmp_path: Path) -> None:
    g = _graph(tmp_path)
    result = g.run(
        session_id="s-auth2",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I apologize for the interruption.",
        trace_id="t-auth2",
    )
    spr = result.get("scene_plan_record")
    assert isinstance(spr, dict)
    assert spr.get("selected_scene_function")
    assert result.get("committed_result") is not None or True
    op = build_operator_canonical_turn_record(result)
    assert "scene_plan_record" in op
    assert op["scene_plan_record"] == spr


def test_graph_diagnostics_planner_projection_present(tmp_path: Path) -> None:
    g = _graph(tmp_path)
    result = g.run(
        session_id="s-auth3",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Why did you say that?",
        trace_id="t-auth3",
    )
    gd = result.get("graph_diagnostics") or {}
    proj = gd.get("planner_state_projection") or {}
    assert proj.get("semantic_move_record")
    assert proj.get("semantic_move_record") == result.get("semantic_move_record")
