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


def test_runtime_turn_graph_appends_interpretation_summary_to_model_prompt(tmp_path: Path) -> None:
    graph = _build_graph(tmp_path)
    result = graph.run(
        session_id="session_1",
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        player_input='"No, and do not dodge this."',
    )
    prompt = result.get("model_prompt") or ""
    assert "Runtime interpretation (structured):" in prompt
    assert "- kind: speech" in prompt
    assert "- ambiguity: None" in prompt
    assert "- runtime_delivery_hint:" in prompt
    interp = result.get("interpreted_input") or {}
    assert interp.get("kind") == "speech"
    assert interp.get("ambiguity") is None


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
    nodes_executed = result["graph_diagnostics"]["nodes_executed"]
    assert "synthesize_context" in nodes_executed
    assert "derive_meta_narrative_awareness" in nodes_executed
    assert "assemble_model_context" in nodes_executed
    synthesis_bundle = result.get("context_synthesis_bundle") or {}
    assert synthesis_bundle.get("authority") == "proposal_support_only"
    synthesis_diagnostics = result["graph_diagnostics"].get("context_synthesis") or {}
    assert synthesis_diagnostics.get("authority") == "proposal_support_only"
    assert synthesis_diagnostics.get("used_in_model_prompt") is True
    assert synthesis_diagnostics.get("evidence_item_count", 0) >= 1
    assert "Context Synthesis (proposal support, non-authoritative):" in prompt
    assert "Synthesis Obligations:" in prompt
    assert "Director runtime state (authoritative, model-visible):" in prompt
    assert "Scene Assessment:" in prompt
    assert "Selected Scene Function:" in prompt
    assert "selected_scene_function:" in prompt
    assert "Pacing Directive:" in prompt
    assert "Eligible Responders:" in prompt
    assert "Canonical GoC Phase Law:" in prompt
    assert "Broad NLU Listening (structured, source-bound):" in prompt
    assert "Prompt Authority (source-bound, no commit mutation):" in prompt
    assert "Dramatic Generation Packet (authoritative JSON):" in prompt
    assert '"selected_scene_function"' in prompt
    assert '"selected_responder_set"' in prompt
    assert '"broad_nlu_listening"' in prompt
    assert '"conversational_memory"' in prompt
    assert '"prompt_authority"' in prompt
    assert adapter.prompts
    assert "Director runtime state (authoritative, model-visible):" in adapter.prompts[-1]
    assert "Dramatic Generation Packet (authoritative JSON):" in adapter.prompts[-1]
    gen_meta = (result.get("generation") or {}).get("metadata") or {}
    assert gen_meta.get("dramatic_generation_packet_included") is True
    assert gen_meta.get("dramatic_generation_packet_scene_function")
    packet = result.get("dramatic_generation_packet") or {}
    assert "meta_narrative_awareness" in packet
    assert "broad_nlu_listening" in packet
    assert "conversational_memory" in packet
    assert "prompt_authority" in packet
    semantic_packet = packet.get("semantic_interpretation") or {}
    assert semantic_packet.get("primary_move_type")
    assert "ranked_move_candidates" in semantic_packet
    ledger = (result.get("turn_aspect_ledger") or {}).get("turn_aspect_ledger") or {}
    assert ASPECT_BROAD_NLU_LISTENING in ledger
    assert ASPECT_CONVERSATIONAL_MEMORY in ledger
    assert ASPECT_PROMPT_AUTHORITY in ledger
    assert ASPECT_META_NARRATIVE_AWARENESS in ledger


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


def test_runtime_turn_graph_emits_player_action_resolution_surface(tmp_path: Path) -> None:
    graph = _build_graph_with_semantic_translation(
        tmp_path,
        {
            "normalized_english_text": "Go to the bathroom.",
            "player_input_kind": "movement_action",
            "action_kind": "movement",
            "verb": "move_to",
            "target_query_english": "bathroom",
            "resolved_target_id": "bathroom",
            "resolved_target_type": "location",
            "commit_policy": "commit_action",
            "confidence": "high",
        },
    )
    result = graph.run(
        session_id="session-action-1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Gehe ins Bad",
        trace_id="trace-action-surface-1",
        turn_number=1,
        host_experience_template={
            "template_id": "god_of_carnage_solo",
            "title": "God of Carnage",
        },
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
    frame = result.get("player_action_frame") or {}
    aff = result.get("affordance_resolution") or {}
    translation = result.get("input_translation") or {}
    interpreted = result.get("interpreted_input") or {}
    assert translation.get("status") == "resolved"
    assert translation.get("normalized_english_text") == "Go to the bathroom."
    assert interpreted.get("normalized_english_text") == "Go to the bathroom."
    assert frame.get("verb") == "move_to"
    assert frame.get("player_input_kind") == "movement_action"
    assert frame.get("resolved_target_id") == "bathroom"
    assert frame.get("normalized_english_text") == "Go to the bathroom."
    assert aff.get("affordance_status") in {"allowed_offscreen", "allowed", "partial"}
    nodes = result.get("graph_diagnostics", {}).get("nodes_executed") or result.get("nodes_executed") or []
    assert nodes.index("translate_player_input") < nodes.index("interpret_input")
    assert nodes.index("interpret_input") < nodes.index("resolve_player_action")
    assert "resolve_player_action" in nodes
    assert "authoritative_action_resolution" in nodes
    meta = (result.get("generation") or {}).get("metadata") or {}
    assert meta.get("adapter") == "action_resolution_authoritative"
    repro = (result.get("graph_diagnostics") or {}).get("repro_metadata") or {}
    assert repro.get("action_resolution_short_path") is True
    assert repro.get("graph_path_summary") == "authoritative_action_resolution_deterministic"
    assert repro.get("repro_complete") is True
    assert repro.get("authoritative_action_resolution_reason") == "authoritative_action_resolution"
    assert repro.get("execution_tier") == "live"
    assert repro.get("fallback_used") is False
    assert repro.get("mock_used") is False
    assert repro.get("ldss_fallback") is False
    ledger = result.get("turn_aspect_ledger") or {}
    action_aspect = (ledger.get("turn_aspect_ledger") or {}).get(ASPECT_ACTION_RESOLUTION) or {}
    beat_aspect = (ledger.get("turn_aspect_ledger") or {}).get(ASPECT_BEAT) or {}
    assert action_aspect.get("status") == "passed"
    assert action_aspect.get("actual", {}).get("raw_player_input") == "Gehe ins Bad"
    assert action_aspect.get("actual", {}).get("player_input_kind") == "movement_action"
    assert action_aspect.get("actual", {}).get("action_commit_policy") == "commit_action"
    assert beat_aspect.get("status") == "partial"
    assert beat_aspect.get("selected", {}).get("selected_scene_function") == "deterministic_action_resolution"
    assert beat_aspect.get("actual", {}).get("deterministic_action_resolution") is True
    assert result.get("response_plan", {}).get("deterministic_action_resolution") is True
    environment_state = result.get("environment_state") or {}
    assert environment_state.get("current_room_id") == frame.get("resolved_target_id")
    assert (result.get("committed_result") or {}).get("environment_state_after") == environment_state
    render_support = (result.get("visible_output_bundle") or {}).get("render_support") or {}
    render_environment = render_support.get("environment") or {}
    assert render_environment.get("current_room_id") == environment_state.get("current_room_id")
    assert "environment_state_bound" in (result.get("visibility_class_markers") or [])


def test_runtime_turn_graph_trace_location_role_normalization_uses_short_path(tmp_path: Path) -> None:
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
        session_id="session-action-trace-kitchen",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Gehe in die Küche",
        trace_id="trace-action-trace-kitchen",
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

    nodes = result.get("graph_diagnostics", {}).get("nodes_executed") or result.get("nodes_executed") or []
    frame = result.get("player_action_frame") or {}
    repro = (result.get("graph_diagnostics") or {}).get("repro_metadata") or {}
    environment_state = result.get("environment_state") or {}
    visible_bundle = result.get("visible_output_bundle") or {}

    assert "translate_player_input" in nodes
    assert "resolve_player_action" in nodes
    assert "authoritative_action_resolution" in nodes
    assert "route_model" not in nodes
    assert "invoke_model" not in nodes
    assert frame.get("player_input_kind") == "physical_action"
    assert frame.get("action_kind") == "movement"
    assert frame.get("verb") == "move_to"
    assert frame.get("resolved_target_id") == "kitchen"
    assert frame.get("resolved_target_type") == "location"
    assert frame.get("target_resolution_source") == "ai_semantic_resolution.content_id"
    assert frame.get("canonical_path_effect") == "hold_current_step"
    assert environment_state.get("current_room_id") == "kitchen"
    assert visible_bundle.get("gm_narration")
    assert visible_bundle.get("spoken_lines") == []
    assert visible_bundle.get("action_lines") == []
    assert repro.get("action_resolution_short_path") is True
    assert repro.get("graph_path_summary") == "authoritative_action_resolution_deterministic"


def test_runtime_turn_graph_routes_inferred_mundane_action_to_narrator_model(tmp_path: Path) -> None:
    graph = _build_graph_with_semantic_translation(
        tmp_path,
        {
            "normalized_english_text": "Open the unlisted household container.",
            "player_input_kind": "action",
            "action_kind": "object_interaction",
            "verb": "open",
            "target_query_english": "unlisted household container",
            "resolved_target_type": "object",
            "inference_mode": "canon_safe_plausible_affordance",
            "inferred_target_id": "inferred_local_household_container",
            "canon_safety": "content_silent_mundane",
            "canonical_risk": "low",
            "inferred_affordance_summary": "A mundane local object implied by the current location.",
            "commit_policy": "commit_action",
            "confidence": "medium",
        },
    )

    result = graph.run(
        session_id="session-action-inferred",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Öffne den unbenannten Behälter",
        trace_id="trace-action-inferred-1",
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

    nodes = result.get("graph_diagnostics", {}).get("nodes_executed") or result.get("nodes_executed") or []
    frame = result.get("player_action_frame") or {}
    ncp = result.get("narrator_consequence_plan") or {}
    repro = (result.get("graph_diagnostics") or {}).get("repro_metadata") or {}
    gen_meta = (result.get("generation") or {}).get("metadata") or {}

    assert "resolve_player_action" in nodes
    assert "authoritative_action_resolution" not in nodes
    assert "route_model" in nodes
    assert "invoke_model" in nodes
    assert frame.get("target_resolution_source") == "ai_semantic_resolution.plausible_inference"
    assert frame.get("access_status") == "inferred_plausible"
    assert frame.get("canonical_path_effect") == "hold_current_step"
    assert ncp.get("source") == "ai_semantic_plausible_inference"
    assert ncp.get("requires_model_realization") is True
    assert repro.get("graph_path_summary") == "primary_invoke_langchain_only"
    assert gen_meta.get("dramatic_generation_packet_included") is True


def test_runtime_turn_graph_realizes_inferred_mundane_action_as_visible_narration(tmp_path: Path) -> None:
    visible_text = (
        "The small local action stays inside the room: the object opens, "
        "and nothing about the larger argument is spent by it."
    )
    graph = _build_graph_with_semantic_translation_and_narration(
        tmp_path,
        {
            "normalized_english_text": "Open the unlisted household container.",
            "player_input_kind": "action",
            "action_kind": "object_interaction",
            "verb": "open",
            "target_query_english": "unlisted household container",
            "resolved_target_type": "object",
            "inference_mode": "canon_safe_plausible_affordance",
            "inferred_target_id": "inferred_local_household_container",
            "canon_safety": "content_silent_mundane",
            "canonical_risk": "low",
            "inferred_affordance_summary": "A mundane local object implied by the current location.",
            "commit_policy": "commit_action",
            "confidence": "medium",
        },
        visible_text,
    )

    result = graph.run(
        session_id="session-action-inferred-visible",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Öffne den unbenannten Behälter",
        trace_id="trace-action-inferred-visible-1",
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

    bundle = result.get("visible_output_bundle") or {}
    structured = ((result.get("generation") or {}).get("metadata") or {}).get("structured_output") or {}

    assert visible_text in (bundle.get("gm_narration") or [])
    assert structured.get("function_type") == "local_action_consequence"
    assert structured.get("spoken_lines") == []
    assert structured.get("action_lines") == []
    assert (result.get("player_action_frame") or {}).get("canonical_path_effect") == "hold_current_step"


def test_runtime_turn_graph_commits_local_movement_while_holding_canonical_step(tmp_path: Path) -> None:
    graph = _build_graph_with_semantic_translation(
        tmp_path,
        {
            "normalized_english_text": "Move to the building hallway.",
            "player_input_kind": "movement_action",
            "action_kind": "movement",
            "verb": "move_to",
            "target_query_english": "building hallway",
            "resolved_target_id": "building_hallway",
            "resolved_target_type": "location",
            "commit_policy": "commit_action",
            "canonical_path_effect": "hold_current_step",
            "confidence": "high",
        },
    )

    result = graph.run(
        session_id="session-action-local-movement",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Ich verlasse die Wohnung",
        trace_id="trace-action-local-movement-1",
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

    frame = result.get("player_action_frame") or {}
    transition = result.get("local_context_transition") or {}
    environment = result.get("environment_state") or {}
    actor_locations = environment.get("actor_locations") or {}
    bundle = result.get("visible_output_bundle") or {}

    assert frame.get("canonical_path_effect") == "hold_current_step"
    assert frame.get("resolved_target_id") == "building_hallway"
    assert transition.get("to_area") == "building_hallway"
    assert transition.get("new_area_established") is True
    assert environment.get("current_room_id") == "building_hallway"
    assert actor_locations.get("annette_reille") == "building_hallway"
    assert actor_locations.get("alain_reille") == "living_room"
    assert bundle.get("spoken_lines") == []
    assert bundle.get("action_lines") == []


def test_runtime_turn_graph_unknown_target_remains_action_outcome_in_aspect_ledger(tmp_path: Path) -> None:
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
        session_id="session-action-unknown",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Gehe nach Mordor",
        trace_id="trace-action-unknown-1",
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
    ledger = result.get("turn_aspect_ledger") or {}
    action_aspect = (ledger.get("turn_aspect_ledger") or {}).get(ASPECT_ACTION_RESOLUTION) or {}
    actual = action_aspect.get("actual") or {}
    translation = result.get("input_translation") or {}
    assert translation.get("status") == "resolved"
    assert translation.get("normalized_english_text") == "Go to Mordor."
    assert action_aspect.get("status") == "passed"
    assert actual.get("player_input_kind") == "movement_action"
    assert actual.get("verb") == "move_to"
    assert actual.get("affordance_status") == "unknown_target"
    assert actual.get("action_commit_policy") == "needs_clarification"
    beat_aspect = (ledger.get("turn_aspect_ledger") or {}).get(ASPECT_BEAT) or {}
    assert beat_aspect.get("actual", {}).get("deterministic_action_resolution") is True
    interpreted = result.get("interpreted_input") or {}
    assert interpreted.get("player_speech_committed") is False


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
