from __future__ import annotations

from pathlib import Path

from story_runtime_core import RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import build_default_registry
from wos_ai_stack import (
    ContextPackAssembler,
    ContextRetriever,
    RagIngestionPipeline,
    RuntimeTurnGraphExecutor,
    build_seed_improvement_graph,
    build_seed_writers_room_graph,
)


class SuccessAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(content="ok", success=True, metadata={"adapter": self.adapter_name})


def _build_graph(tmp_path: Path) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage graph integration sample.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"mock": SuccessAdapter(), "openai": SuccessAdapter(), "ollama": SuccessAdapter()},
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )


def test_runtime_turn_graph_propagates_trace_and_host_versions(tmp_path: Path) -> None:
    graph = _build_graph(tmp_path)
    result = graph.run(
        session_id="session_1",
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        player_input="I open the door",
        trace_id="trace-goc-1",
        host_versions={"world_engine_app_version": "test-9.9.9"},
    )
    repro = result["graph_diagnostics"].get("repro_metadata") or {}
    assert repro.get("trace_id") == "trace-goc-1"
    assert repro.get("host_versions", {}).get("world_engine_app_version") == "test-9.9.9"


def test_runtime_turn_graph_executes_nodes_and_emits_trace(tmp_path: Path) -> None:
    graph = _build_graph(tmp_path)
    result = graph.run(
        session_id="session_1",
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        player_input="I open the door",
    )

    assert result["graph_diagnostics"]["graph_name"] == "wos_runtime_turn_graph"
    assert result["graph_diagnostics"]["graph_version"] == "m11_v1"
    repro = result["graph_diagnostics"].get("repro_metadata") or {}
    assert repro.get("ai_stack_semantic_version")
    assert repro.get("runtime_turn_graph_version") == "m11_v1"
    assert repro.get("retrieval_profile") == "runtime_turn_support"
    assert "interpret_input" in result["graph_diagnostics"]["nodes_executed"]
    assert "route_model" in result["graph_diagnostics"]["nodes_executed"]
    assert "generation" in result
    assert isinstance(result["generation"]["success"], bool)
    assert result["generation"]["metadata"]["langchain_prompt_used"] is True


def test_seed_graphs_for_writers_room_and_improvement_are_operational() -> None:
    writers_graph = build_seed_writers_room_graph()
    improvement_graph = build_seed_improvement_graph()

    writers_result = writers_graph.invoke({"module_id": "god_of_carnage"})
    improvement_result = improvement_graph.invoke({"baseline_id": "base_1"})

    assert writers_result["workflow"] == "writers_room_review_seed"
    assert writers_result["status"] == "ready"
    assert improvement_result["workflow"] == "improvement_eval_seed"
    assert improvement_result["status"] == "ready"
