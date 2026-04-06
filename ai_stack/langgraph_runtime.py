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
from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.goc_yaml_authority import (
    detect_builtin_yaml_title_conflict,
    goc_character_profile_snippet,
    load_goc_canonical_module_yaml,
    load_goc_yaml_slice_bundle,
    scene_guidance_snippets,
)
from ai_stack.scene_director_goc import (
    build_pacing_and_silence,
    build_responder_and_function,
    build_scene_assessment,
)
from ai_stack.goc_dramatic_alignment import extract_proposed_narrative_text
from ai_stack.goc_turn_seams import (
    build_diagnostics_refs,
    build_goc_continuity_impacts_on_commit,
    repro_metadata_complete,
    run_commit_seam,
    run_validation_seam,
    run_visible_render,
    strip_director_overwrites_from_structured_output,
    structured_output_to_proposed_effects,
)


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
    host_experience_template: dict[str, Any]
    force_experiment_preview: bool
    # Bounded prior-thread snapshot from story runtime (no evidence lists / no history blobs).
    active_narrative_threads: list[dict[str, Any]]
    thread_pressure_summary: str
    interpreted_input: dict[str, Any]
    interpreted_move: dict[str, Any]
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
    # Canonical turn field groups (CANONICAL_TURN_CONTRACT_GOC.md §4–§5).
    goc_slice_active: bool
    goc_canonical_yaml: dict[str, Any]
    goc_yaml_slice: dict[str, Any]
    prior_continuity_impacts: list[dict[str, Any]]
    prior_dramatic_signature: dict[str, str]
    scene_assessment: dict[str, Any]
    selected_responder_set: list[dict[str, Any]]
    selected_scene_function: str
    pacing_mode: str
    silence_brevity_decision: dict[str, Any]
    proposed_state_effects: list[dict[str, Any]]
    validation_outcome: dict[str, Any]
    committed_result: dict[str, Any]
    visible_output_bundle: dict[str, Any]
    continuity_impacts: list[dict[str, Any]]
    visibility_class_markers: list[str]
    failure_markers: list[dict[str, Any]]
    fallback_markers: list[dict[str, Any]]
    diagnostics_refs: list[dict[str, Any]]
    experiment_preview: bool
    transition_pattern: str


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
        graph.add_node("goc_resolve_canonical_content", self._goc_resolve_canonical_content)
        graph.add_node("director_assess_scene", self._director_assess_scene)
        graph.add_node("director_select_dramatic_parameters", self._director_select_dramatic_parameters)
        graph.add_node("route_model", self._route_model)
        graph.add_node("invoke_model", self._invoke_model)
        graph.add_node("fallback_model", self._fallback_model)
        graph.add_node("proposal_normalize", self._proposal_normalize)
        graph.add_node("validate_seam", self._validate_seam)
        graph.add_node("commit_seam", self._commit_seam)
        graph.add_node("render_visible", self._render_visible)
        graph.add_node("package_output", self._package_output)
        graph.set_entry_point("interpret_input")
        graph.add_edge("interpret_input", "retrieve_context")
        graph.add_edge("retrieve_context", "goc_resolve_canonical_content")
        graph.add_edge("goc_resolve_canonical_content", "director_assess_scene")
        graph.add_edge("director_assess_scene", "director_select_dramatic_parameters")
        graph.add_edge("director_select_dramatic_parameters", "route_model")
        graph.add_edge("route_model", "invoke_model")
        graph.add_conditional_edges(
            "invoke_model",
            self._next_step_after_invoke,
            {"fallback_model": "fallback_model", "proposal_normalize": "proposal_normalize"},
        )
        graph.add_edge("fallback_model", "proposal_normalize")
        graph.add_edge("proposal_normalize", "validate_seam")
        graph.add_edge("validate_seam", "commit_seam")
        graph.add_edge("commit_seam", "render_visible")
        graph.add_edge("render_visible", "package_output")
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
        host_experience_template: dict[str, Any] | None = None,
        force_experiment_preview: bool | None = None,
        prior_continuity_impacts: list[dict[str, Any]] | None = None,
        prior_dramatic_signature: dict[str, str] | None = None,
    ) -> RuntimeTurnState:
        initial_state: RuntimeTurnState = {
            "session_id": session_id,
            "module_id": module_id,
            "current_scene_id": current_scene_id,
            "player_input": player_input,
            "trace_id": trace_id or "",
            "host_versions": host_versions or {},
            "host_experience_template": host_experience_template or {},
            "nodes_executed": [],
            "node_outcomes": {},
            "graph_errors": [],
            "failure_markers": [],
            "fallback_markers": [],
        }
        if force_experiment_preview is not None:
            initial_state["force_experiment_preview"] = force_experiment_preview
        if active_narrative_threads:
            initial_state["active_narrative_threads"] = active_narrative_threads
        if thread_pressure_summary:
            # Keep in sync with world-engine story_runtime narrative_threads.THREAD_PRESSURE_SUMMARY_MAX (128).
            initial_state["thread_pressure_summary"] = thread_pressure_summary[:128]
        if prior_continuity_impacts:
            initial_state["prior_continuity_impacts"] = list(prior_continuity_impacts)
        if prior_dramatic_signature:
            initial_state["prior_dramatic_signature"] = dict(prior_dramatic_signature)
        return self._graph.invoke(initial_state)

    def _interpret_input(self, state: RuntimeTurnState) -> RuntimeTurnState:
        interpretation = self.interpreter(state["player_input"])
        task_type = "classification" if interpretation.kind.value in {"explicit_command", "meta"} else "narrative_generation"
        interp_dict = interpretation.model_dump(mode="json")
        update = _track(state, node_name="interpret_input")
        update["interpreted_input"] = interp_dict
        update["interpreted_move"] = {
            "player_intent": str(interp_dict.get("intent") or "unspecified"),
            "move_class": str(interp_dict.get("kind") or "unknown"),
        }
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

    def _goc_resolve_canonical_content(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="goc_resolve_canonical_content")
        failure_markers = list(state.get("failure_markers") or [])
        module_id = state.get("module_id") or ""
        if module_id == GOC_MODULE_ID:
            try:
                yaml_mod = load_goc_canonical_module_yaml()
                update["goc_canonical_yaml"] = yaml_mod
                update["goc_yaml_slice"] = load_goc_yaml_slice_bundle()
                update["goc_slice_active"] = True
                host = state.get("host_experience_template")
                if isinstance(host, dict):
                    conflict = detect_builtin_yaml_title_conflict(
                        host_template_id=host.get("template_id") if isinstance(host.get("template_id"), str) else None,
                        host_template_title=host.get("title") if isinstance(host.get("title"), str) else None,
                    )
                    if conflict:
                        failure_markers.append(conflict)
            except Exception as exc:  # pragma: no cover - exercised when yaml missing in broken checkout
                failure_markers.append({"failure_class": "graph_error", "note": f"goc_yaml_load_failed:{exc}"})
                update["goc_slice_active"] = True
        else:
            update["goc_slice_active"] = False
        update["failure_markers"] = failure_markers
        return update

    def _director_assess_scene(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="director_assess_scene")
        module_id = state.get("module_id") or ""
        yaml_blob = state.get("goc_canonical_yaml") if isinstance(state.get("goc_canonical_yaml"), dict) else None
        if module_id != GOC_MODULE_ID:
            update["scene_assessment"] = {
                "scene_core": "non_goc_placeholder",
                "pressure_state": "unknown",
                "module_slice": module_id,
            }
            return update
        if not yaml_blob:
            markers = list(state.get("failure_markers") or [])
            markers.append({"failure_class": "missing_scene_director", "note": "goc_canonical_yaml_missing"})
            update["failure_markers"] = markers
            update["scene_assessment"] = {
                "scene_core": "goc_unresolved",
                "pressure_state": "unknown",
                "module_slice": module_id,
            }
            return update
        prior = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else None
        yslice = state.get("goc_yaml_slice") if isinstance(state.get("goc_yaml_slice"), dict) else None
        update["scene_assessment"] = build_scene_assessment(
            module_id=module_id,
            current_scene_id=state.get("current_scene_id") or "",
            canonical_yaml=yaml_blob,
            prior_continuity_impacts=prior,
            yaml_slice=yslice,
        )
        return update

    def _director_select_dramatic_parameters(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="director_select_dramatic_parameters")
        module_id = state.get("module_id") or ""
        interpreted_move = state.get("interpreted_move") if isinstance(state.get("interpreted_move"), dict) else {}
        player_input = state.get("player_input") or ""
        pacing, silence = build_pacing_and_silence(
            player_input=player_input,
            interpreted_move=interpreted_move,
            module_id=module_id,
        )
        if module_id != GOC_MODULE_ID:
            update["selected_responder_set"] = []
            update["selected_scene_function"] = "establish_pressure"
            update["pacing_mode"] = pacing
            update["silence_brevity_decision"] = silence
            return update
        prior = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else None
        yslice = state.get("goc_yaml_slice") if isinstance(state.get("goc_yaml_slice"), dict) else None
        base_sa = state.get("scene_assessment") if isinstance(state.get("scene_assessment"), dict) else {}
        responders, scene_fn, _implied, resolution = build_responder_and_function(
            player_input=player_input,
            interpreted_move=interpreted_move,
            pacing_mode=pacing,
            prior_continuity_impacts=prior,
            yaml_slice=yslice,
            current_scene_id=state.get("current_scene_id") or "",
        )
        merged_sa = {**base_sa, "multi_pressure_resolution": resolution}
        update["scene_assessment"] = merged_sa
        update["selected_responder_set"] = responders
        update["selected_scene_function"] = scene_fn
        update["pacing_mode"] = pacing
        update["silence_brevity_decision"] = silence
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
            generation["model_raw_text"] = call.content
            structured = None
            if runtime_result.parsed_output:
                structured = runtime_result.parsed_output.model_dump(mode="json")
            generation["metadata"] = {
                **call.metadata,
                "langchain_prompt_used": True,
                "langchain_parser_error": runtime_result.parser_error,
                "structured_output": structured,
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
        return "fallback_model" if state.get("fallback_needed") else "proposal_normalize"

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
            fallback_generation["model_raw_text"] = call.content
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

    def _proposal_normalize(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="proposal_normalize")
        generation = dict(state.get("generation") or {})
        meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
        structured = meta.get("structured_output")
        structured_dict = structured if isinstance(structured, dict) else None
        cleaned, strip_markers = strip_director_overwrites_from_structured_output(structured_dict)
        if cleaned is not None:
            meta = dict(meta)
            meta["structured_output"] = cleaned
            generation["metadata"] = meta
        proposed = structured_output_to_proposed_effects(cleaned)
        fallback_markers = list(state.get("fallback_markers") or [])
        fallback_markers.extend(strip_markers)
        update["generation"] = generation
        update["proposed_state_effects"] = proposed
        update["fallback_markers"] = fallback_markers
        return update

    def _validate_seam(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="validate_seam")
        generation = state.get("generation") or {}
        proposed = list(state.get("proposed_state_effects") or [])
        silence = state.get("silence_brevity_decision") if isinstance(state.get("silence_brevity_decision"), dict) else {}
        outcome = run_validation_seam(
            module_id=state.get("module_id") or "",
            proposed_state_effects=proposed,
            generation=generation if isinstance(generation, dict) else {},
            director_context={
                "selected_scene_function": state.get("selected_scene_function") or "",
                "pacing_mode": state.get("pacing_mode") or "",
                "silence_brevity_decision": silence,
            },
        )
        update["validation_outcome"] = outcome
        return update

    def _commit_seam(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="commit_seam")
        validation = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
        proposed = list(state.get("proposed_state_effects") or [])
        committed = run_commit_seam(
            module_id=state.get("module_id") or "",
            validation_outcome=validation,
            proposed_state_effects=proposed,
        )
        continuity: list[dict[str, Any]] = []
        if (
            state.get("module_id") == GOC_MODULE_ID
            and validation.get("status") == "approved"
            and committed.get("commit_applied")
        ):
            continuity = build_goc_continuity_impacts_on_commit(
                module_id=GOC_MODULE_ID,
                selected_scene_function=str(state.get("selected_scene_function") or ""),
                proposed_state_effects=proposed,
            )
        update["committed_result"] = committed
        update["continuity_impacts"] = continuity
        return update

    def _render_visible(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="render_visible")
        generation = dict(state.get("generation") or {})
        if "content" not in generation and generation.get("model_raw_text"):
            generation["content"] = generation["model_raw_text"]
        committed = state.get("committed_result") if isinstance(state.get("committed_result"), dict) else {}
        validation = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
        tp = "diagnostics_only"
        if state.get("graph_errors"):
            tp = "diagnostics_only"
        elif "fallback_model" in (state.get("nodes_executed") or []):
            tp = "diagnostics_only"
        elif committed.get("commit_applied"):
            tp = "hard"
        elif validation.get("status") == "approved":
            tp = "soft"
        yslice = state.get("goc_yaml_slice") if isinstance(state.get("goc_yaml_slice"), dict) else {}
        sg = yslice.get("scene_guidance") if isinstance(yslice.get("scene_guidance"), dict) else {}
        responders = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []
        primary = responders[0] if responders and isinstance(responders[0], dict) else {}
        actor_id = str(primary.get("actor_id") or "")
        actor_reason = str(primary.get("reason") or "")
        char_snippet = goc_character_profile_snippet(
            actor_id=actor_id,
            yaml_slice=yslice,
            scene_id=state.get("current_scene_id") or "",
        )
        guidance_snip = scene_guidance_snippets(
            scene_guidance=sg,
            scene_id=state.get("current_scene_id") or "",
        )
        proposed_fx = list(state.get("proposed_state_effects") or [])
        prop_narr = extract_proposed_narrative_text(proposed_fx)
        bundle, vis_markers = run_visible_render(
            module_id=state.get("module_id") or "",
            committed_result=committed,
            validation_outcome=validation,
            generation=generation,
            transition_pattern=tp,
            render_context={
                "pacing_mode": state.get("pacing_mode") or "",
                "silence_brevity_decision": state.get("silence_brevity_decision")
                if isinstance(state.get("silence_brevity_decision"), dict)
                else {},
                "current_scene_id": state.get("current_scene_id") or "",
                "scene_guidance": sg,
                "proposed_narrative_excerpt": prop_narr,
                "responder_actor_id": actor_id,
                "responder_reason": actor_reason,
                "character_profile_snippet": char_snippet,
                "scene_guidance_snippets": guidance_snip,
            },
        )
        update["generation"] = generation
        update["visible_output_bundle"] = bundle
        update["visibility_class_markers"] = vis_markers
        update["transition_pattern"] = tp
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
        repro_ok = repro_metadata_complete(repro_metadata)
        repro_metadata["repro_complete"] = repro_ok

        failure_markers = list(state.get("failure_markers") or [])
        module_id = state.get("module_id") or ""
        validation = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
        committed = state.get("committed_result") if isinstance(state.get("committed_result"), dict) else {}

        experiment_preview = True
        if state.get("force_experiment_preview"):
            experiment_preview = True
        elif module_id != GOC_MODULE_ID:
            experiment_preview = True
        elif validation.get("status") == "waived":
            experiment_preview = True
        elif validation.get("status") != "approved":
            experiment_preview = True
        elif not state.get("goc_slice_active"):
            experiment_preview = True
        else:
            # GoC slice: full seams executed; allow non-preview when validation approved.
            experiment_preview = False

        if module_id == GOC_MODULE_ID and validation.get("status") == "approved" and not committed.get("commit_applied"):
            # Empty commit is still a valid committed_result shell; keep non-preview for dry policy clarity.
            pass

        for fm in failure_markers:
            fc = fm.get("failure_class") if isinstance(fm, dict) else None
            if fc in ("scope_breach", "graph_error"):
                experiment_preview = True

        cost_hints = build_operational_cost_hints_for_runtime_graph(
            retrieval=retrieval if isinstance(retrieval, dict) else {},
            generation=generation if isinstance(generation, dict) else {},
            graph_execution_health=execution_health,
            model_prompt=state.get("model_prompt") if isinstance(state.get("model_prompt"), str) else None,
            fallback_path_taken=fallback_taken,
        )
        vo = validation
        alignment_note = "alignment_ok"
        if vo.get("status") == "rejected" and str(vo.get("reason", "")).startswith("dramatic_alignment"):
            alignment_note = f"alignment_reject:{vo.get('reason')}"
        prior_ci = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else []
        sa = state.get("scene_assessment") if isinstance(state.get("scene_assessment"), dict) else {}
        mpr = sa.get("multi_pressure_resolution") if isinstance(sa.get("multi_pressure_resolution"), dict) else {}
        responders = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []
        primary = responders[0] if responders and isinstance(responders[0], dict) else {}
        silence = state.get("silence_brevity_decision") if isinstance(state.get("silence_brevity_decision"), dict) else {}
        dramatic_signature = {
            "scene_function": str(state.get("selected_scene_function") or ""),
            "responder": str(primary.get("actor_id") or ""),
            "pacing_mode": str(state.get("pacing_mode") or ""),
            "silence_mode": str(silence.get("mode") or ""),
        }
        current_continuity = [
            x.get("class")
            for x in (state.get("continuity_impacts") or [])
            if isinstance(x, dict) and x.get("class")
        ]
        prior_sig = state.get("prior_dramatic_signature") if isinstance(state.get("prior_dramatic_signature"), dict) else {}
        similar_move = False
        interp = state.get("interpreted_move") if isinstance(state.get("interpreted_move"), dict) else {}
        prior_intent = str(prior_sig.get("player_intent") or "")
        curr_intent = str(interp.get("player_intent") or "")
        if prior_intent and curr_intent and prior_intent == curr_intent:
            similar_move = True
        stale_pattern = bool(
            prior_sig
            and prior_sig.get("scene_function") == dramatic_signature.get("scene_function")
            and prior_sig.get("responder") == dramatic_signature.get("responder")
            and similar_move
        )
        quality_status = "pass"
        if vo.get("status") == "rejected" and str(vo.get("reason", "")).startswith("dramatic_alignment"):
            quality_status = "fail"
        elif vo.get("status") != "approved" or "truth_aligned" not in (state.get("visibility_class_markers") or []):
            quality_status = "degraded_explainable"
        alliance_shift_detected = "alliance_shift" in current_continuity
        dignity_injury_detected = "dignity_injury" in current_continuity
        pressure_shift_detected = bool(
            set(current_continuity)
            and set(current_continuity) != set(
                x.get("class")
                for x in prior_ci
                if isinstance(x, dict) and x.get("class")
            )
        )
        run_classification = quality_status
        if quality_status == "pass":
            run_classification = "pass"
        elif quality_status == "fail":
            run_classification = "fail"
        else:
            run_classification = "degraded_explainable"
        weak_run_explanation = "none"
        if run_classification != "pass":
            weak_run_explanation = (
                f"validation_status={vo.get('status')} reason={vo.get('reason')} "
                f"alignment={alignment_note} visibility={state.get('visibility_class_markers') or []}"
            )
        gd = {
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
            "dramatic_review": {
                "selected_scene_function": state.get("selected_scene_function"),
                "selected_responder": primary,
                "pacing_mode": state.get("pacing_mode"),
                "silence_brevity_decision": state.get("silence_brevity_decision"),
                "prior_continuity_classes": [
                    x.get("class") for x in prior_ci if isinstance(x, dict) and x.get("class")
                ],
                "multi_pressure_chosen": mpr.get("chosen_scene_function"),
                "multi_pressure_candidates": mpr.get("candidates"),
                "multi_pressure_rationale": mpr.get("rationale"),
                "validation_reason": vo.get("reason"),
                "dramatic_alignment_summary": alignment_note,
                "dramatic_signature": dramatic_signature,
                "pattern_repetition_risk": stale_pattern,
                "pattern_repetition_note": (
                    "same_scene_function_and_responder_under_similar_intent"
                    if stale_pattern
                    else "pattern_variation_or_intent_shift_detected"
                ),
                "dramatic_quality_status": quality_status,
                "run_classification": run_classification,
                "current_continuity_classes": current_continuity,
                "alliance_shift_detected": alliance_shift_detected,
                "dignity_injury_detected": dignity_injury_detected,
                "pressure_shift_detected": pressure_shift_detected,
                "pressure_shift_explanation": (
                    "continuity_classes_changed_from_prior_run"
                    if pressure_shift_detected
                    else "continuity_classes_stable_or_empty"
                ),
                "weak_run_explanation": weak_run_explanation,
                "review_explanations": {
                    "responder": f"selected_responder_reason:{primary.get('reason')}",
                    "scene_function": str(mpr.get("rationale") or "single_path_rule"),
                    "pacing": f"pacing_mode={state.get('pacing_mode')} silence_reason={silence.get('reason')}",
                    "continuity": (
                        "carry_forward_classes="
                        + ",".join(str(x.get("class")) for x in prior_ci if isinstance(x, dict) and x.get("class"))
                    )
                    if prior_ci
                    else "carry_forward_classes=none",
                    "dramatic_quality": f"{quality_status}:{alignment_note}",
                    "pressure_shift": (
                        "current_continuity="
                        + ",".join(str(x) for x in current_continuity)
                        + ";prior_continuity="
                        + ",".join(str(x.get("class")) for x in prior_ci if isinstance(x, dict) and x.get("class"))
                    ),
                },
            },
        }
        update["graph_diagnostics"] = gd
        update["experiment_preview"] = experiment_preview
        tp = state.get("transition_pattern") or "diagnostics_only"
        refs = build_diagnostics_refs(
            graph_diagnostics=gd,
            experiment_preview=experiment_preview,
            transition_pattern=str(tp),
            gate_hints={
                "turn_integrity": "seams_materialized_in_graph",
                "diagnostic_sufficiency": "repro_complete" if repro_ok else "repro_incomplete",
                "dramatic_quality": alignment_note,
                "slice_boundary": "no_scope_breach_marker"
                if not any(
                    isinstance(m, dict) and m.get("failure_class") == "scope_breach"
                    for m in (failure_markers or [])
                )
                else "scope_breach_recorded",
            },
        )
        update["diagnostics_refs"] = refs
        update["failure_markers"] = failure_markers
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
