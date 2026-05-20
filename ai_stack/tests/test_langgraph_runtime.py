from __future__ import annotations

import json
from pathlib import Path

import pytest
from story_runtime_core import RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import RoutingDecision, build_default_registry

langgraph_runtime = pytest.importorskip(
    "ai_stack.langgraph.langgraph_runtime",
    reason="LangGraph/LangChain stack required for langgraph runtime tests",
)
from ai_stack.langgraph.langgraph_runtime import (
    RuntimeTurnGraphExecutor,
    build_seed_improvement_graph,
    build_seed_writers_room_graph,
)
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RagIngestionPipeline
from ai_stack.version import RUNTIME_TURN_GRAPH_VERSION
from ai_stack.runtime_turn_contracts import (
    ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
    ADAPTER_INVOCATION_META_CONTROL,
    EXECUTION_HEALTH_GRAPH_ERROR,
    EXECUTION_HEALTH_HEALTHY,
    EXECUTION_HEALTH_MODEL_FALLBACK,
    EXECUTION_HEALTH_VALUES,
)
from ai_stack.runtime_aspect_ledger import (
    ASPECT_ACTION_RESOLUTION,
    ASPECT_BEAT,
    ASPECT_BROAD_NLU_LISTENING,
    ASPECT_CONVERSATIONAL_MEMORY,
    ASPECT_META_NARRATIVE_AWARENESS,
    ASPECT_PROMPT_AUTHORITY,
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


class SemanticTranslationAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def __init__(self, semantic_action: dict, semantic_move: dict | None = None) -> None:
        self.semantic_action = dict(semantic_action)
        self.semantic_move = dict(semantic_move or {})
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
        if "Resolve the player input before any story turn processing." in prompt:
            payload = {"semantic_action": dict(self.semantic_action)}
            if self.semantic_move:
                payload["semantic_move"] = dict(self.semantic_move)
            return ModelCallResult(
                content=json.dumps(payload),
                success=True,
                metadata={"adapter": self.adapter_name, "model_name": model_name},
            )
        return ModelCallResult(content="ok", success=True, metadata={"adapter": self.adapter_name})


class SemanticTranslationNarrationAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def __init__(self, semantic_action: dict, narrative_response: str) -> None:
        self.semantic_action = dict(semantic_action)
        self.narrative_response = narrative_response
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
        if "Resolve the player input before any story turn processing." in prompt:
            return ModelCallResult(
                content=json.dumps({"semantic_action": dict(self.semantic_action)}),
                success=True,
                metadata={"adapter": self.adapter_name, "model_name": model_name},
            )
        assert "narrator_consequence_plan" in prompt
        assert "player_freedom_policy" in prompt
        assert "canonical_path_effect" in prompt
        payload = {
            "schema_version": "runtime_actor_turn_v1",
            "narration_summary": self.narrative_response,
            "narrative_response": self.narrative_response,
            "spoken_lines": [],
            "action_lines": [],
            "state_effects": [],
            "function_type": "local_action_consequence",
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self.adapter_name, "model_name": model_name},
        )


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


def _build_graph_with_semantic_translation(tmp_path: Path, semantic_action: dict) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage graph semantic translation sample.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    translator = SemanticTranslationAdapter(semantic_action)
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"mock": SuccessAdapter(), "openai": translator, "ollama": translator},
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )


def _build_graph_with_semantic_translation_and_narration(
    tmp_path: Path,
    semantic_action: dict,
    narrative_response: str,
) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage graph semantic narration sample.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    adapter = SemanticTranslationNarrationAdapter(semantic_action, narrative_response)
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"mock": SuccessAdapter(), "openai": adapter, "ollama": adapter},
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


def test_runtime_turn_graph_uses_thin_path_for_player_turn(tmp_path: Path) -> None:
    """Thin-path invariant: a player turn flows through resolver -> director
    composer -> realize_via_capabilities -> route_model -> invoke_model and the
    obsolete LDSS-style nodes (synthesize_context, derive_*, assemble_model_context,
    authoritative_action_resolution) are not visited."""
    graph = _build_graph(tmp_path)
    result = graph.run(
        session_id="session_thinpath_1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Gehe in die Kueche",
    )
    nodes = result["graph_diagnostics"]["nodes_executed"]
    expected_thin_path = [
        "translate_player_input",
        "interpret_input",
        "resolve_player_action",
        "director_compose_realization",
        "realize_via_capabilities",
        "route_model",
        "invoke_model",
    ]
    for name in expected_thin_path:
        assert name in nodes, f"missing thin-path node: {name}"
    obsolete = {
        "synthesize_context",
        "assemble_model_context",
        "derive_scene_energy",
        "derive_pacing_rhythm",
        "derive_dramatic_irony",
        "derive_meta_narrative_awareness",
        "authoritative_action_resolution",
    }
    for name in obsolete:
        assert name not in nodes, f"obsolete node should not run for player turn: {name}"
    assert nodes.index("resolve_player_action") < nodes.index("director_compose_realization")
    assert nodes.index("director_compose_realization") < nodes.index("realize_via_capabilities")
    assert nodes.index("realize_via_capabilities") < nodes.index("route_model")
    assert nodes.index("route_model") < nodes.index("invoke_model")


def test_runtime_turn_graph_emits_realization_plan_for_movement(tmp_path: Path) -> None:
    """Thin-path invariant: the Director composer publishes a realization_plan
    on the turn state when the player commits a movement to a known location."""
    graph = _build_graph_with_semantic_translation(
        tmp_path,
        {
            "normalized_english_text": "Go to the kitchen.",
            "player_input_kind": "physical_action",
            "action_kind": "go_to",
            "verb": "go_to",
            "target_query_english": "the kitchen",
            "resolved_target_id": "kitchen",
            "resolved_target_type": "location",
            "commit_policy": "commit_action",
            "confidence": "high",
        },
    )
    result = graph.run(
        session_id="session_thinpath_movement",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Gehe in die Kueche",
        turn_number=1,
        actor_lane_context={
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette_reille",
            "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
            "actor_lanes": {
                "annette_reille": "human",
                "alain_reille": "npc",
                "veronique_vallon": "npc",
                "michel_longstreet": "npc",
            },
        },
    )
    plan = result.get("realization_plan") or {}
    assert plan.get("schema_version") == "realization_plan.v1"
    assert plan.get("realization_owner") == "narrator"
    assert plan.get("capabilities_selected") == ["narrator.location_transition.describe"]
    assert plan.get("outcome_disposition", {}).get("outcome") == "success"
    assert result.get("realize_via_capabilities_used_capability") == "narrator.location_transition.describe"
    plc = result.get("player_local_context") or {}
    assert plc.get("current_location_id") == "kitchen" or plc.get("current_area") == "kitchen"


def test_runtime_turn_graph_unknown_target_yields_clarification_plan(tmp_path: Path) -> None:
    """Thin-path invariant: an unknown movement target produces a clarification
    realization_plan (outcome=partial) rather than a hard refusal or a silent fail."""
    graph = _build_graph_with_semantic_translation(
        tmp_path,
        {
            "normalized_english_text": "Go to Mordor.",
            "player_input_kind": "movement_action",
            "action_kind": "movement",
            "verb": "move_to",
            "target_query_english": "Mordor",
            "commit_policy": "needs_clarification",
            "confidence": "low",
        },
    )
    result = graph.run(
        session_id="session_thinpath_unknown",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Gehe nach Mordor",
        turn_number=1,
        actor_lane_context={
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette_reille",
            "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
            "actor_lanes": {
                "annette_reille": "human",
                "alain_reille": "npc",
                "veronique_vallon": "npc",
                "michel_longstreet": "npc",
            },
        },
    )
    plan = result.get("realization_plan") or {}
    assert plan.get("realization_owner") == "narrator"
    assert plan.get("capabilities_selected") == ["narrator.clarification.describe"]
    assert plan.get("outcome_disposition", {}).get("outcome") == "partial"


def test_runtime_turn_graph_meta_input_uses_non_story_control_path(tmp_path: Path) -> None:
    graph = _build_graph(tmp_path)
    result = graph.run(
        session_id="session-meta-1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="ooc: pause",
        trace_id="trace-meta-1",
        turn_number=1,
    )
    interp = result.get("interpreted_input") or {}
    assert interp.get("kind") == "meta"
    assert interp.get("selected_handling_path") == "meta"
    assert interp.get("player_input_kind") == "meta"
    assert interp.get("player_action_committed") is False
    assert interp.get("player_speech_committed") is False
    assert interp.get("narrator_response_expected") is False
    assert interp.get("npc_response_expected") is False

    nodes = result.get("graph_diagnostics", {}).get("nodes_executed") or []
    assert "meta_control_turn" in nodes
    assert "resolve_player_action" not in nodes
    assert "retrieve_context" not in nodes
    assert "invoke_model" not in nodes

    generation = result.get("generation") or {}
    meta = generation.get("metadata") or {}
    assert generation.get("attempted") is False
    assert generation.get("success") is True
    assert meta.get("adapter_invocation_mode") == ADAPTER_INVOCATION_META_CONTROL
    assert result.get("routing", {}).get("generation_required") is False
    assert (result.get("committed_result") or {}).get("commit_not_applicable") is True

    repro = (result.get("graph_diagnostics") or {}).get("repro_metadata") or {}
    assert repro.get("adapter_invocation_mode") == ADAPTER_INVOCATION_META_CONTROL
    assert repro.get("graph_path_summary") == "meta_control_deterministic"
    assert repro.get("generation_required") is False
    assert repro.get("meta_control_path") is True
    assert repro.get("repro_complete") is True


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
