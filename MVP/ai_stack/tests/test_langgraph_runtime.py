from __future__ import annotations

from pathlib import Path

import pytest
from story_runtime_core import RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import build_default_registry

langgraph_runtime = pytest.importorskip(
    "ai_stack.langgraph_runtime",
    reason="LangGraph/LangChain stack required for langgraph runtime tests",
)
from ai_stack.langgraph_runtime import (
    RuntimeTurnGraphExecutor,
    build_seed_improvement_graph,
    build_seed_writers_room_graph,
)
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RagIngestionPipeline
from ai_stack.version import RUNTIME_TURN_GRAPH_VERSION
from ai_stack.runtime_turn_contracts import (
    ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK,
    ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
    ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK,
    EXECUTION_HEALTH_GRAPH_ERROR,
    EXECUTION_HEALTH_HEALTHY,
    EXECUTION_HEALTH_MODEL_FALLBACK,
    EXECUTION_HEALTH_VALUES,
)


class SuccessAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(content="ok", success=True, metadata={"adapter": self.adapter_name})


class FailingPrimaryAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(content="", success=False, metadata={"error": "forced_primary_failure"})


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


def _build_graph_failing_primary(tmp_path: Path) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage graph fallback sample.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"openai": FailingPrimaryAdapter(), "mock": SuccessAdapter(), "ollama": SuccessAdapter()},
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )


def _build_graph_no_mock_fallback(tmp_path: Path) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage degraded path sample.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"openai": FailingPrimaryAdapter(), "ollama": SuccessAdapter()},
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


def test_runtime_turn_graph_appends_interpretation_summary_to_model_prompt(tmp_path: Path) -> None:
    graph = _build_graph(tmp_path)
    result = graph.run(
        session_id="session_1",
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        player_input="open door wow",
    )
    prompt = result.get("model_prompt") or ""
    assert "Runtime interpretation (structured):" in prompt
    assert "- kind: mixed" in prompt
    assert "- ambiguity: conflicting_action_reaction" in prompt
    assert "- runtime_delivery_hint:" in prompt
    interp = result.get("interpreted_input") or {}
    assert interp.get("kind") == "mixed"
    assert interp.get("ambiguity") == "conflicting_action_reaction"


def test_runtime_turn_graph_executes_nodes_and_emits_trace(tmp_path: Path) -> None:
    graph = _build_graph(tmp_path)
    result = graph.run(
        session_id="session_1",
        module_id="other_module",
        current_scene_id="scene_1",
        player_input="I open the door",
        trace_id="trace-langgraph-1",
    )

    assert result["graph_diagnostics"]["graph_name"] == "wos_runtime_turn_graph"
    assert result["graph_diagnostics"]["graph_version"] == RUNTIME_TURN_GRAPH_VERSION
    repro = result["graph_diagnostics"].get("repro_metadata") or {}
    assert repro.get("ai_stack_semantic_version")
    assert repro.get("runtime_turn_graph_version") == RUNTIME_TURN_GRAPH_VERSION
    assert repro.get("repro_complete") is True
    assert repro.get("retrieval_profile") == "runtime_turn_support"
    assert "interpret_input" in result["graph_diagnostics"]["nodes_executed"]
    assert "route_model" in result["graph_diagnostics"]["nodes_executed"]
    assert result["graph_diagnostics"].get("execution_health") == EXECUTION_HEALTH_HEALTHY
    assert "generation" in result
    assert isinstance(result["generation"]["success"], bool)
    assert result["generation"]["metadata"]["langchain_prompt_used"] is True
    assert result["generation"]["metadata"]["adapter_invocation_mode"] == ADAPTER_INVOCATION_LANGCHAIN_PRIMARY
    assert repro.get("adapter_invocation_mode") == ADAPTER_INVOCATION_LANGCHAIN_PRIMARY
    assert repro.get("graph_path_summary") == "primary_invoke_langchain_only"
    hints = result["graph_diagnostics"].get("operational_cost_hints") or {}
    assert hints.get("disclaimer") == "coarse_operational_signals_not_financial_estimates"
    assert hints.get("graph_execution_health") == EXECUTION_HEALTH_HEALTHY
    assert hints.get("prompt_length_bucket") in {"small", "medium", "large"}
    assert hints.get("adapter_invocation_mode") == ADAPTER_INVOCATION_LANGCHAIN_PRIMARY
    assert hints.get("model_fallback_used") is False


def test_runtime_turn_graph_fallback_uses_raw_adapter_and_marks_invocation_mode(tmp_path: Path) -> None:
    graph = _build_graph_failing_primary(tmp_path)
    result = graph.run(
        session_id="session_1",
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        player_input="I open the door",
    )
    assert result["graph_diagnostics"]["fallback_path_taken"] is True
    assert result["graph_diagnostics"]["execution_health"] == EXECUTION_HEALTH_MODEL_FALLBACK
    assert "fallback_model" in result["graph_diagnostics"]["nodes_executed"]
    meta = result["generation"].get("metadata") or {}
    assert meta.get("adapter_invocation_mode") == ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK
    assert meta.get("langchain_prompt_used") is False
    assert meta.get("bypass_note")
    repro = result["graph_diagnostics"].get("repro_metadata") or {}
    assert repro.get("adapter_invocation_mode") == ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK
    assert repro.get("graph_path_summary") == "used_fallback_model_node_raw_adapter"
    hints = result["graph_diagnostics"].get("operational_cost_hints") or {}
    assert hints.get("fallback_path_taken") is True
    assert hints.get("model_fallback_used") is True
    assert hints.get("graph_execution_health") == EXECUTION_HEALTH_MODEL_FALLBACK


def test_runtime_turn_graph_missing_mock_fallback_is_explicit_degraded(tmp_path: Path) -> None:
    graph = _build_graph_no_mock_fallback(tmp_path)
    result = graph.run(
        session_id="session_1",
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        player_input="I open the door",
    )
    assert "fallback_adapter_missing:mock" in result["graph_diagnostics"]["errors"]
    assert result["graph_diagnostics"]["execution_health"] == EXECUTION_HEALTH_GRAPH_ERROR
    meta = result["generation"].get("metadata") or {}
    assert meta.get("adapter_invocation_mode") == ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK


def test_execution_health_constants_are_stable_set() -> None:
    assert set(EXECUTION_HEALTH_VALUES) == {"healthy", "graph_error", "model_fallback", "degraded_generation"}


def test_seed_graphs_for_writers_room_and_improvement_are_operational() -> None:
    writers_graph = build_seed_writers_room_graph()
    improvement_graph = build_seed_improvement_graph()

    writers_result = writers_graph.invoke({"module_id": "god_of_carnage"})
    improvement_result = improvement_graph.invoke({"baseline_id": "base_1"})

    assert writers_result["workflow"] == "writers_room_review_seed"
    assert writers_result["status"] == "ready"
    assert improvement_result["workflow"] == "improvement_eval_seed"
    assert improvement_result["status"] == "ready"


def test_seed_writers_room_graph_is_minimal_stub() -> None:
    """Documents truthful stub status: writers-room seed graph has no real workflow stage outputs."""
    writers_graph = build_seed_writers_room_graph()
    result = writers_graph.invoke({"module_id": "god_of_carnage"})

    assert result["workflow"] == "writers_room_review_seed"
    assert result["status"] == "ready"
    # Confirm absence of real multi-stage workflow outputs — this is a single-node stub
    assert "retrieval" not in result, "stub should not produce retrieval stage output"
    assert "generation" not in result, "stub should not produce generation stage output"
    assert "review" not in result, "stub should not produce review stage output"
    assert "revision" not in result, "stub should not produce revision stage output"


def test_seed_improvement_graph_is_minimal_stub() -> None:
    """Documents truthful stub status: improvement seed graph has no real workflow stage outputs."""
    improvement_graph = build_seed_improvement_graph()
    result = improvement_graph.invoke({"baseline_id": "base_1"})

    assert result["workflow"] == "improvement_eval_seed"
    assert result["status"] == "ready"
    # Confirm absence of real multi-stage workflow outputs — this is a single-node stub
    assert "retrieval" not in result, "stub should not produce retrieval stage output"
    assert "generation" not in result, "stub should not produce generation stage output"
    assert "evaluation" not in result, "stub should not produce evaluation stage output"
    assert "recommendation" not in result, "stub should not produce recommendation stage output"


def test_langgraph_missing_dependency_raises_honest_runtime_error(monkeypatch) -> None:
    monkeypatch.setattr(langgraph_runtime, "LANGGRAPH_IMPORT_ERROR", ModuleNotFoundError("langgraph"), raising=False)
    with pytest.raises(RuntimeError, match="LangGraph runtime dependency is unavailable"):
        langgraph_runtime.ensure_langgraph_available()
