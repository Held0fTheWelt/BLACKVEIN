from __future__ import annotations

import json
from pathlib import Path

import pytest
from story_runtime_core import RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import RoutingDecision, build_default_registry

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
    ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
    EXECUTION_HEALTH_GRAPH_ERROR,
    EXECUTION_HEALTH_HEALTHY,
    EXECUTION_HEALTH_MODEL_FALLBACK,
    EXECUTION_HEALTH_VALUES,
)


class SuccessAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(
        self,
        prompt: str,
        *,
        timeout_seconds: float = 10.0,
        retrieval_context: str | None = None,
        model_name: str | None = None,
    ) -> ModelCallResult:
        return ModelCallResult(content="ok", success=True, metadata={"adapter": self.adapter_name})


class PromptCaptureAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(
        self,
        prompt: str,
        *,
        timeout_seconds: float = 10.0,
        retrieval_context: str | None = None,
        model_name: str | None = None,
    ) -> ModelCallResult:
        self.prompts.append(prompt)
        payload = {
            "narrative_response": (
                "Annette lets the accusation hang at the table, then answers with enough force "
                "to make the social pressure visible."
            ),
            "proposed_scene_id": None,
            "intent_summary": "director_context_probe",
        }
        return ModelCallResult(content=json.dumps(payload), success=True, metadata={"adapter": self.adapter_name})


class FailingPrimaryAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def generate(
        self,
        prompt: str,
        *,
        timeout_seconds: float = 10.0,
        retrieval_context: str | None = None,
        model_name: str | None = None,
    ) -> ModelCallResult:
        return ModelCallResult(content="", success=False, metadata={"error": "forced_primary_failure"})


class StructuredFallbackAdapter(BaseModelAdapter):
    adapter_name = "ollama"

    def generate(
        self,
        prompt: str,
        *,
        timeout_seconds: float = 10.0,
        retrieval_context: str | None = None,
        model_name: str | None = None,
    ) -> ModelCallResult:
        payload = {
            "schema_version": "runtime_actor_turn_v1",
            "narration_summary": "Fallback model keeps the scene moving without using mock output.",
            "narrative_response": "Fallback model keeps the scene moving without using mock output.",
            "primary_responder_id": "annette_reille",
            "spoken_lines": [
                {
                    "speaker_id": "annette_reille",
                    "text": "No. We are not going to pretend this is settled.",
                }
            ],
            "action_lines": [],
            "state_effects": [],
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self.adapter_name, "model_name": model_name},
        )


class DramaAwareRoutingCapture:
    """Routing test-double that records dramatic requirements passed by the graph."""

    def __init__(self, registry) -> None:
        self.registry = registry
        self.last_requirements = None

    def choose(self, *, task_type: str, dramatic_requirements=None):
        self.last_requirements = dramatic_requirements
        return RoutingDecision(
            selected_model="openai:gpt-4o-mini",
            selected_provider="openai",
            route_reason="role_matrix_primary",
            fallback_model="ollama:llama3.2",
        )


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
        adapters={"openai": FailingPrimaryAdapter(), "mock": SuccessAdapter(), "ollama": StructuredFallbackAdapter()},
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
        adapters={"openai": FailingPrimaryAdapter()},
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


def test_runtime_turn_graph_delivers_director_context_to_model_prompt(tmp_path: Path) -> None:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage director context sample.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    adapter = PromptCaptureAdapter()
    graph = RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"mock": adapter, "openai": adapter, "ollama": adapter},
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )
    result = graph.run(
        session_id="session_1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I press Annette to reveal the truth.",
    )
    prompt = result.get("model_prompt") or ""
    assert "assemble_model_context" in result["graph_diagnostics"]["nodes_executed"]
    assert "Director runtime state (authoritative, model-visible):" in prompt
    assert "Scene Assessment:" in prompt
    assert "Selected Scene Function:" in prompt
    assert "selected_scene_function:" in prompt
    assert "Pacing Directive:" in prompt
    assert "Eligible Responders:" in prompt
    assert "Canonical GoC Phase Law:" in prompt
    assert "Dramatic Generation Packet (authoritative JSON):" in prompt
    assert '"selected_scene_function"' in prompt
    assert '"selected_responder_set"' in prompt
    assert adapter.prompts
    assert "Director runtime state (authoritative, model-visible):" in adapter.prompts[-1]
    assert "Dramatic Generation Packet (authoritative JSON):" in adapter.prompts[-1]
    gen_meta = (result.get("generation") or {}).get("metadata") or {}
    assert gen_meta.get("dramatic_generation_packet_included") is True
    assert gen_meta.get("dramatic_generation_packet_scene_function")
    packet = result.get("dramatic_generation_packet") or {}
    semantic_packet = packet.get("semantic_interpretation") or {}
    assert semantic_packet.get("primary_move_type")
    assert "ranked_move_candidates" in semantic_packet


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


def test_runtime_turn_graph_passes_drama_aware_routing_requirements(tmp_path: Path) -> None:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("Drama-aware routing capture sample.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = DramaAwareRoutingCapture(registry)
    graph = RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"mock": SuccessAdapter(), "openai": SuccessAdapter(), "ollama": SuccessAdapter()},
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )
    result = graph.run(
        session_id="session_1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="No, and don't dodge this.",
    )
    assert isinstance(routing.last_requirements, dict)
    assert routing.last_requirements.get("dialogue_complexity")
    route = result.get("routing") or {}
    req = route.get("drama_aware_requirements") or {}
    assert req.get("contract") == "dramatic_routing_requirements.v1"
    assert req.get("actor_count") >= 1


def test_runtime_turn_graph_fallback_uses_configured_model_before_mock(tmp_path: Path) -> None:
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
    outcomes = result["graph_diagnostics"].get("node_outcomes") or {}
    assert outcomes.get("fallback_model") == "ok"
    assert result["generation"].get("fallback_used") is True
    meta = result["generation"].get("metadata") or {}
    assert meta.get("adapter") == "ollama"
    assert meta.get("adapter_invocation_mode") == ADAPTER_INVOCATION_LANGCHAIN_PRIMARY
    assert meta.get("fallback_model_id") == "ollama:llama3.2"
    assert meta.get("langchain_prompt_used") is True
    repro = result["graph_diagnostics"].get("repro_metadata") or {}
    assert repro.get("graph_path_summary") == "used_fallback_model_node_langchain_adapter"
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
    assert "fallback_adapter_missing:ollama" in result["graph_diagnostics"]["errors"]
    assert result["graph_diagnostics"]["execution_health"] == EXECUTION_HEALTH_GRAPH_ERROR
    outcomes = result["graph_diagnostics"].get("node_outcomes") or {}
    assert outcomes.get("fallback_model") == "error"
    assert outcomes.get("invoke_model") == "error"


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
