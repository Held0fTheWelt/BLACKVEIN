from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as pkg_version
from typing import Any
from typing_extensions import TypedDict

LANGGRAPH_IMPORT_ERROR: Exception | None = None
try:  # pragma: no cover - exercised by dedicated missing-dependency test via sentinel override
    from langgraph.graph import END, StateGraph
except Exception as exc:  # pragma: no cover
    END = None
    StateGraph = None
    LANGGRAPH_IMPORT_ERROR = exc

from story_runtime_core.adapters import BaseModelAdapter
from story_runtime_core.model_registry import ModelRegistry, RoutingPolicy
from ai_stack.capabilities import CapabilityRegistry
from ai_stack.langchain_integration import invoke_runtime_adapter_with_langchain
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RetrievalDomain, RetrievalRequest
from ai_stack.operational_profile import build_operational_cost_hints_for_runtime_graph
from ai_stack.runtime_turn_contracts import (
    ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK,
    ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
    ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK,
    EXECUTION_HEALTH_DEGRADED_GENERATION,
    EXECUTION_HEALTH_GRAPH_ERROR,
    EXECUTION_HEALTH_HEALTHY,
    EXECUTION_HEALTH_MODEL_FALLBACK,
    RAW_FALLBACK_BYPASS_NOTE,
)
from ai_stack.version import AI_STACK_SEMANTIC_VERSION, RUNTIME_TURN_GRAPH_VERSION


def _dist_version(name: str) -> str:
    try:
        return pkg_version(name)
    except PackageNotFoundError:
        return "unknown"


def ensure_langgraph_available() -> None:
    if LANGGRAPH_IMPORT_ERROR is not None:
        raise RuntimeError(
            "LangGraph runtime dependency is unavailable. Install 'langgraph' in the runtime environment "
            "and verify requirements are up to date."
        ) from LANGGRAPH_IMPORT_ERROR


class RuntimeTurnState(TypedDict, total=False):
    session_id: str
    module_id: str
    current_scene_id: str
    player_input: str
    trace_id: str
    host_versions: dict[str, Any]
    # Bounded prior-thread snapshot from story runtime (no evidence lists / no history blobs).
    active_narrative_threads: list[dict[str, Any]]
    thread_pressure_summary: str
    interpreted_input: dict[str, Any]
    task_type: str
    routing: dict[str, Any]
    selected_provider: str
    selected_timeout: float
    retrieval: dict[str, Any]
    context_text: str
    model_prompt: str
    generation: dict[str, Any]
    fallback_needed: bool
    graph_diagnostics: dict[str, Any]
    nodes_executed: list[str]
    node_outcomes: dict[str, str]
    graph_errors: list[str]
    capability_audit: list[dict[str, Any]]


def _track(state: RuntimeTurnState, *, node_name: str, outcome: str = "ok") -> RuntimeTurnState:
    nodes = list(state.get("nodes_executed", []))
    outcomes = dict(state.get("node_outcomes", {}))
    nodes.append(node_name)
    outcomes[node_name] = outcome
    return {"nodes_executed": nodes, "node_outcomes": outcomes}


@dataclass
class RuntimeTurnGraphExecutor:
    interpreter: Any
    routing: RoutingPolicy
    registry: ModelRegistry
    adapters: dict[str, BaseModelAdapter]
    retriever: ContextRetriever
    assembler: ContextPackAssembler
    capability_registry: CapabilityRegistry | None = None
    graph_name: str = "wos_runtime_turn_graph"
    graph_version: str = RUNTIME_TURN_GRAPH_VERSION

    def __post_init__(self) -> None:
        ensure_langgraph_available()
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(RuntimeTurnState)
        graph.add_node("interpret_input", self._interpret_input)
        graph.add_node("retrieve_context", self._retrieve_context)
        graph.add_node("route_model", self._route_model)
        graph.add_node("invoke_model", self._invoke_model)
        graph.add_node("fallback_model", self._fallback_model)
        graph.add_node("package_output", self._package_output)
        graph.set_entry_point("interpret_input")
        graph.add_edge("interpret_input", "retrieve_context")
        graph.add_edge("retrieve_context", "route_model")
        graph.add_edge("route_model", "invoke_model")
        graph.add_conditional_edges(
            "invoke_model",
            self._next_step_after_invoke,
            {"fallback_model": "fallback_model", "package_output": "package_output"},
        )
        graph.add_edge("fallback_model", "package_output")
        graph.add_edge("package_output", END)
        return graph.compile()

    def run(
        self,
        *,
        session_id: str,
        module_id: str,
        current_scene_id: str,
        player_input: str,
        trace_id: str | None = None,
        host_versions: dict[str, Any] | None = None,
        active_narrative_threads: list[dict[str, Any]] | None = None,
        thread_pressure_summary: str | None = None,
    ) -> RuntimeTurnState:
        initial_state: RuntimeTurnState = {
            "session_id": session_id,
            "module_id": module_id,
            "current_scene_id": current_scene_id,
            "player_input": player_input,
            "trace_id": trace_id or "",
            "host_versions": host_versions or {},
            "nodes_executed": [],
            "node_outcomes": {},
            "graph_errors": [],
        }
        if active_narrative_threads:
            initial_state["active_narrative_threads"] = active_narrative_threads
        if thread_pressure_summary:
            # Keep in sync with world-engine story_runtime narrative_threads.THREAD_PRESSURE_SUMMARY_MAX (128).
            initial_state["thread_pressure_summary"] = thread_pressure_summary[:128]
        return self._graph.invoke(initial_state)

    def _interpret_input(self, state: RuntimeTurnState) -> RuntimeTurnState:
        interpretation = self.interpreter(state["player_input"])
        task_type = "classification" if interpretation.kind.value in {"explicit_command", "meta"} else "narrative_generation"
        update = _track(state, node_name="interpret_input")
        update["interpreted_input"] = interpretation.model_dump(mode="json")
        update["task_type"] = task_type
        return update

    def _retrieve_context(self, state: RuntimeTurnState) -> RuntimeTurnState:
        payload = {
            "domain": RetrievalDomain.RUNTIME.value,
            "profile": "runtime_turn_support",
            "query": f"{state['player_input']}\nscene:{state['current_scene_id']}\nmodule:{state['module_id']}",
            "module_id": state["module_id"],
            "scene_id": state["current_scene_id"],
            "max_chunks": 4,
        }
        capability_audit: list[dict[str, Any]] = []
        if self.capability_registry is not None:
            result = self.capability_registry.invoke(
                name="wos.context_pack.build",
                mode="runtime",
                actor="runtime_turn_graph",
                payload=payload,
            )
            retrieval = result["retrieval"]
            context_text = result["context_text"]
            capability_audit = self.capability_registry.recent_audit(limit=3)
        else:
            request = RetrievalRequest(
                domain=RetrievalDomain.RUNTIME,
                profile="runtime_turn_support",
                query=payload["query"],
                module_id=state["module_id"],
                scene_id=state["current_scene_id"],
                max_chunks=4,
            )
            retrieval_result = self.retriever.retrieve(request)
            pack = self.assembler.assemble(retrieval_result)
            top_score = ""
            if pack.sources:
                top_score = str(pack.sources[0].get("score", ""))
            retrieval = {
                "domain": pack.domain,
                "profile": pack.profile,
                "status": pack.status,
                "hit_count": pack.hit_count,
                "sources": pack.sources,
                "ranking_notes": pack.ranking_notes,
                "index_version": pack.index_version,
                "corpus_fingerprint": pack.corpus_fingerprint,
                "storage_path": pack.storage_path,
                "retrieval_route": pack.retrieval_route,
                "embedding_model_id": pack.embedding_model_id,
                "top_hit_score": top_score,
            }
            context_text = pack.compact_context
        interp = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        interpretation_block = (
            "Runtime interpretation (structured):\n"
            f"- kind: {interp.get('kind')}\n"
            f"- confidence: {interp.get('confidence')}\n"
            f"- ambiguity: {interp.get('ambiguity')}\n"
            f"- intent: {interp.get('intent')}\n"
            f"- selected_handling_path: {interp.get('selected_handling_path')}\n"
            f"- runtime_delivery_hint: {interp.get('runtime_delivery_hint')}\n"
        )
        base = state["player_input"]
        if context_text:
            base = f"{base}\n\n{context_text}"
        prompt = f"{base}\n\n{interpretation_block}"
        threads = state.get("active_narrative_threads")
        if isinstance(threads, list) and threads:
            lines = ["Prior narrative threads (bounded snapshot, not authoritative diagnostics):"]
            for item in threads:
                if not isinstance(item, dict):
                    continue
                rid = item.get("thread_id")
                kind = item.get("thread_kind")
                st = item.get("status")
                intens = item.get("intensity")
                ent = item.get("related_entities")
                if not isinstance(ent, list):
                    ent = []
                lines.append(
                    f"- id={rid} kind={kind} status={st} intensity={intens} related_entities={ent[:4]}"
                )
            tsum = state.get("thread_pressure_summary")
            if isinstance(tsum, str) and tsum.strip():
                lines.append(f"thread_pressure_summary: {tsum.strip()[:128]}")
            prompt = f"{prompt}\n\n" + "\n".join(lines)
        update = _track(state, node_name="retrieve_context")
        update["retrieval"] = retrieval
        update["context_text"] = context_text
        update["model_prompt"] = prompt
        if capability_audit:
            update["capability_audit"] = capability_audit
        return update

    def _route_model(self, state: RuntimeTurnState) -> RuntimeTurnState:
        decision = self.routing.choose(task_type=state["task_type"])
        selected = self.registry.get(decision.selected_model)
        update = _track(state, node_name="route_model")
        update["routing"] = {
            "selected_model": decision.selected_model,
            "selected_provider": decision.selected_provider,
            "reason": decision.route_reason,
            "fallback_model": decision.fallback_model,
            "timeout_seconds": selected.timeout_seconds if selected else None,
            "structured_output_success": bool(selected.structured_output_capable) if selected else False,
            "registered_adapter_providers": sorted(self.adapters.keys()),
        }
        update["selected_provider"] = decision.selected_provider or ""
        update["selected_timeout"] = float(selected.timeout_seconds) if selected else 10.0
        return update

    def _invoke_model(self, state: RuntimeTurnState) -> RuntimeTurnState:
        provider = state.get("selected_provider") or ""
        adapter = self.adapters.get(provider)
        generation: dict[str, Any] = {
            "attempted": False,
            "success": None,
            "error": None,
            "retrieval_context_attached": bool(state.get("context_text")),
            "prompt_length": len(state.get("model_prompt", "")),
            "fallback_used": False,
        }
        outcome = "ok"
        if adapter:
            generation["attempted"] = True
            runtime_result = invoke_runtime_adapter_with_langchain(
                adapter=adapter,
                player_input=state["player_input"],
                interpreted_input=state.get("interpreted_input", {}) if isinstance(state.get("interpreted_input"), dict) else {},
                retrieval_context=state.get("context_text"),
                timeout_seconds=float(state.get("selected_timeout", 10.0)),
            )
            call = runtime_result.call
            generation["success"] = call.success
            generation["error"] = call.metadata.get("error") if not call.success else None
            generation["metadata"] = {
                **call.metadata,
                "langchain_prompt_used": True,
                "langchain_parser_error": runtime_result.parser_error,
                "structured_output": runtime_result.parsed_output.model_dump(mode="json")
                if runtime_result.parsed_output
                else None,
                "adapter_invocation_mode": ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
            }
            if not call.success:
                outcome = "error"
        else:
            generation["error"] = f"adapter_not_registered:{provider}"
            generation["metadata"] = {
                "adapter_invocation_mode": ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK,
                "langchain_prompt_used": False,
                "langchain_parser_error": None,
                "structured_output": None,
                "note": "No adapter registered for routed provider; invoke_model did not call LangChain.",
            }
            outcome = "error"
        update = _track(state, node_name="invoke_model", outcome=outcome)
        update["generation"] = generation
        update["fallback_needed"] = bool(generation["error"] or generation["success"] is False)
        return update

    def _next_step_after_invoke(self, state: RuntimeTurnState) -> str:
        return "fallback_model" if state.get("fallback_needed") else "package_output"

    def _fallback_model(self, state: RuntimeTurnState) -> RuntimeTurnState:
        fallback_generation = dict(state.get("generation", {}))
        fallback_adapter = self.adapters.get("mock")
        if fallback_adapter:
            call = fallback_adapter.generate(
                state.get("model_prompt", state["player_input"]),
                timeout_seconds=5.0,
                retrieval_context=state.get("context_text"),
            )
            fallback_generation["attempted"] = True
            fallback_generation["success"] = call.success
            fallback_generation["error"] = call.metadata.get("error") if not call.success else None
            fallback_generation["metadata"] = {
                **call.metadata,
                "langchain_prompt_used": False,
                "langchain_parser_error": None,
                "structured_output": None,
                "adapter_invocation_mode": ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK,
                "bypass_note": RAW_FALLBACK_BYPASS_NOTE,
            }
            fallback_generation["fallback_used"] = True
            update = _track(state, node_name="fallback_model")
            update["generation"] = fallback_generation
            return update
        errors = list(state.get("graph_errors", []))
        errors.append("fallback_adapter_missing:mock")
        prior_meta = fallback_generation.get("metadata") if isinstance(fallback_generation.get("metadata"), dict) else {}
        fallback_generation["metadata"] = {
            **prior_meta,
            "adapter_invocation_mode": ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK,
            "langchain_prompt_used": False,
            "note": "fallback_adapter_missing:mock — graph could not run graph-managed raw fallback.",
        }
        update = _track(state, node_name="fallback_model", outcome="error")
        update["graph_errors"] = errors
        update["generation"] = fallback_generation
        return update

    def _package_output(self, state: RuntimeTurnState) -> RuntimeTurnState:
        fallback_taken = "fallback_model" in state.get("nodes_executed", [])
        update = _track(state, node_name="package_output")
        routing = state.get("routing") or {}
        retrieval = state.get("retrieval") or {}
        generation = state.get("generation") or {}
        host_versions = dict(state.get("host_versions") or {})
        repro_metadata = {
            "ai_stack_semantic_version": AI_STACK_SEMANTIC_VERSION,
            "runtime_turn_graph_version": self.graph_version,
            "graph_name": self.graph_name,
            "trace_id": state.get("trace_id") or "",
            "story_runtime_core_version": _dist_version("story_runtime_core"),
            "routing_policy": "story_runtime_core.RoutingPolicy",
            "routing_policy_version": "registry_default_v1",
            "selected_model": routing.get("selected_model"),
            "selected_provider": routing.get("selected_provider"),
            "retrieval_domain": retrieval.get("domain"),
            "retrieval_profile": retrieval.get("profile"),
            "retrieval_status": retrieval.get("status"),
            "retrieval_hit_count": retrieval.get("hit_count"),
            "model_attempted": generation.get("attempted"),
            "model_success": generation.get("success"),
            "model_fallback_used": generation.get("fallback_used"),
            "module_id": state.get("module_id"),
            "session_id": state.get("session_id"),
            "host_versions": host_versions,
        }
        graph_errors = list(state.get("graph_errors", []))
        execution_health = EXECUTION_HEALTH_HEALTHY
        if graph_errors:
            execution_health = EXECUTION_HEALTH_GRAPH_ERROR
        elif fallback_taken:
            execution_health = EXECUTION_HEALTH_MODEL_FALLBACK
        elif generation.get("success") is False:
            execution_health = EXECUTION_HEALTH_DEGRADED_GENERATION

        gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
        adapter_mode = gen_meta.get("adapter_invocation_mode")
        if fallback_taken:
            graph_path_summary = "used_fallback_model_node_raw_adapter"
        elif adapter_mode == ADAPTER_INVOCATION_LANGCHAIN_PRIMARY:
            graph_path_summary = "primary_invoke_langchain_only"
        elif adapter_mode == ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK:
            graph_path_summary = "degraded_adapter_or_fallback_missing"
        else:
            graph_path_summary = "primary_path_unknown_adapter_mode"

        repro_metadata["adapter_invocation_mode"] = adapter_mode
        repro_metadata["graph_path_summary"] = graph_path_summary

        cost_hints = build_operational_cost_hints_for_runtime_graph(
            retrieval=retrieval if isinstance(retrieval, dict) else {},
            generation=generation if isinstance(generation, dict) else {},
            graph_execution_health=execution_health,
            model_prompt=state.get("model_prompt") if isinstance(state.get("model_prompt"), str) else None,
            fallback_path_taken=fallback_taken,
        )
        update["graph_diagnostics"] = {
            "graph_name": self.graph_name,
            "graph_version": self.graph_version,
            "nodes_executed": update["nodes_executed"],
            "node_outcomes": update["node_outcomes"],
            "fallback_path_taken": fallback_taken,
            "execution_health": execution_health,
            "errors": graph_errors,
            "capability_audit": state.get("capability_audit", []),
            "repro_metadata": repro_metadata,
            "operational_cost_hints": cost_hints,
        }
        return update


def build_seed_writers_room_graph():
    ensure_langgraph_available()
    class WritersRoomSeedState(TypedDict, total=False):
        module_id: str
        workflow: str
        status: str

    graph = StateGraph(WritersRoomSeedState)

    def seed_node(state: WritersRoomSeedState) -> WritersRoomSeedState:
        return {"module_id": state.get("module_id", ""), "workflow": "writers_room_review_seed", "status": "ready"}

    graph.add_node("seed_node", seed_node)
    graph.set_entry_point("seed_node")
    graph.add_edge("seed_node", END)
    return graph.compile()


def build_seed_improvement_graph():
    ensure_langgraph_available()
    class ImprovementSeedState(TypedDict, total=False):
        baseline_id: str
        workflow: str
        status: str

    graph = StateGraph(ImprovementSeedState)

    def seed_node(state: ImprovementSeedState) -> ImprovementSeedState:
        return {"baseline_id": state.get("baseline_id", ""), "workflow": "improvement_eval_seed", "status": "ready"}

    graph.add_node("seed_node", seed_node)
    graph.set_entry_point("seed_node")
    graph.add_edge("seed_node", END)
    return graph.compile()
