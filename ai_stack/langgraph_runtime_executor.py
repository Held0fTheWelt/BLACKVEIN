from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:  # pragma: no cover - mirror facade LangGraph import; avoids import cycle with langgraph_runtime
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover
    END = None
    StateGraph = None

from story_runtime_core.adapters import BaseModelAdapter
from story_runtime_core.model_registry import ModelRegistry, RoutingPolicy
from ai_stack.capabilities import CapabilityRegistry
from ai_stack.langchain_integration import invoke_runtime_adapter_with_langchain
from ai_stack.rag import ContextPackAssembler, ContextRetriever
from ai_stack.rag_retrieval_dtos import RetrievalRequest
from ai_stack.rag_types import RetrievalDomain
from ai_stack.retrieval_governance_summary import attach_retrieval_governance_summary
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
from ai_stack.goc_roadmap_semantic_surface import ROUTING_LABELS
from ai_stack.goc_yaml_authority import (
    detect_builtin_yaml_title_conflict,
    goc_character_profile_snippet,
    load_goc_canonical_module_yaml,
    load_goc_yaml_slice_bundle,
    scene_guidance_snippets,
)
from ai_stack.character_mind_goc import build_character_mind_records_for_goc
from ai_stack.scene_director_goc import (
    build_pacing_and_silence,
    build_responder_and_function,
    build_scene_assessment,
    prior_continuity_classes,
)
from ai_stack.scene_plan_contract import ScenePlanRecord
from ai_stack.semantic_move_contract import SemanticMoveRecord
from ai_stack.semantic_move_interpretation_goc import interpret_goc_semantic_move, semantic_move_fingerprint
from ai_stack.social_state_contract import SocialStateRecord
from ai_stack.social_state_goc import build_social_state_record, social_state_fingerprint
from ai_stack.dramatic_effect_gate import build_evaluation_context_from_runtime_state
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
from ai_stack.langgraph_runtime_state import (
    STORY_RUNTIME_ROUTING_POLICY_ID,
    STORY_RUNTIME_ROUTING_POLICY_VERSION,
    RuntimeTurnState,
)
from ai_stack.langgraph_runtime_tracking import _dist_version, _track


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
        from ai_stack.langgraph_runtime import ensure_langgraph_available

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
        turn_number: int | None = None,
        turn_id: str | None = None,
        turn_timestamp_iso: str | None = None,
        turn_initiator_type: str | None = None,
        turn_input_class: str | None = None,
        turn_execution_mode: str | None = None,
    ) -> RuntimeTurnState:
        ts = turn_timestamp_iso
        if not ts:
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        tid = turn_id if turn_id is not None else (trace_id or "")
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
            "turn_timestamp_iso": ts,
            "turn_id": tid,
            "turn_initiator_type": turn_initiator_type or "player",
            "turn_execution_mode": turn_execution_mode or "langgraph_runtime_turn_graph",
        }
        if turn_number is not None:
            initial_state["turn_number"] = int(turn_number)
        if turn_input_class is not None:
            initial_state["turn_input_class"] = turn_input_class
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
        task_type = "classification" if interpretation.kind.value in {"explicit_command", "meta"} else "narrative_formulation"
        interp_dict = interpretation.model_dump(mode="json")
        update = _track(state, node_name="interpret_input")
        update["interpreted_input"] = interp_dict
        move_class = str(interp_dict.get("kind") or "unknown")
        update["interpreted_move"] = {
            "player_intent": str(interp_dict.get("intent") or "unspecified"),
            "move_class": move_class,
        }
        update["task_type"] = task_type
        if "turn_input_class" not in state or not state.get("turn_input_class"):
            update["turn_input_class"] = move_class
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
            if isinstance(retrieval, dict):
                attach_retrieval_governance_summary(retrieval)
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
            attach_retrieval_governance_summary(retrieval)
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
        interpreted_input = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        interpreted_move = state.get("interpreted_move") if isinstance(state.get("interpreted_move"), dict) else {}
        prior_early = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else None
        pc_early = prior_continuity_classes(prior_early)
        if module_id != GOC_MODULE_ID:
            placeholder = {
                "scene_core": "non_goc_placeholder",
                "pressure_state": "unknown",
                "module_slice": module_id,
            }
            update["scene_assessment"] = placeholder
            sem_e = interpret_goc_semantic_move(
                module_id=module_id,
                player_input=state.get("player_input") or "",
                interpreted_input=interpreted_input,
                interpreted_move=interpreted_move,
                prior_continuity_classes=pc_early,
            )
            soc_e = build_social_state_record(
                prior_continuity_impacts=prior_early,
                active_narrative_threads=state.get("active_narrative_threads")
                if isinstance(state.get("active_narrative_threads"), list)
                else None,
                thread_pressure_summary=state.get("thread_pressure_summary")
                if isinstance(state.get("thread_pressure_summary"), str)
                else None,
                scene_assessment=placeholder,
            )
            update["semantic_move_record"] = sem_e.to_runtime_dict()
            update["social_state_record"] = soc_e.to_runtime_dict()
            return update
        if not yaml_blob:
            markers = list(state.get("failure_markers") or [])
            markers.append({"failure_class": "missing_scene_director", "note": "goc_canonical_yaml_missing"})
            update["failure_markers"] = markers
            unresolved = {
                "scene_core": "goc_unresolved",
                "pressure_state": "unknown",
                "module_slice": module_id,
            }
            update["scene_assessment"] = unresolved
            sem_u = interpret_goc_semantic_move(
                module_id=module_id,
                player_input=state.get("player_input") or "",
                interpreted_input=interpreted_input,
                interpreted_move=interpreted_move,
                prior_continuity_classes=pc_early,
            )
            soc_u = build_social_state_record(
                prior_continuity_impacts=prior_early,
                active_narrative_threads=state.get("active_narrative_threads")
                if isinstance(state.get("active_narrative_threads"), list)
                else None,
                thread_pressure_summary=state.get("thread_pressure_summary")
                if isinstance(state.get("thread_pressure_summary"), str)
                else None,
                scene_assessment=unresolved,
            )
            update["semantic_move_record"] = sem_u.to_runtime_dict()
            update["social_state_record"] = soc_u.to_runtime_dict()
            return update
        prior = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else None
        yslice = state.get("goc_yaml_slice") if isinstance(state.get("goc_yaml_slice"), dict) else None
        interpreted_input = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        interpreted_move = state.get("interpreted_move") if isinstance(state.get("interpreted_move"), dict) else {}
        base_sa = build_scene_assessment(
            module_id=module_id,
            current_scene_id=state.get("current_scene_id") or "",
            canonical_yaml=yaml_blob,
            prior_continuity_impacts=prior,
            yaml_slice=yslice,
        )
        pc = prior_continuity_classes(prior)
        sem_model = interpret_goc_semantic_move(
            module_id=module_id,
            player_input=state.get("player_input") or "",
            interpreted_input=interpreted_input,
            interpreted_move=interpreted_move,
            prior_continuity_classes=pc,
        )
        sem_dict = sem_model.to_runtime_dict()
        soc_model = build_social_state_record(
            prior_continuity_impacts=prior,
            active_narrative_threads=state.get("active_narrative_threads")
            if isinstance(state.get("active_narrative_threads"), list)
            else None,
            thread_pressure_summary=state.get("thread_pressure_summary")
            if isinstance(state.get("thread_pressure_summary"), str)
            else None,
            scene_assessment=base_sa,
        )
        soc_dict = soc_model.to_runtime_dict()
        base_sa["semantic_move_fingerprint"] = semantic_move_fingerprint(sem_model)
        base_sa["social_state_fingerprint"] = social_state_fingerprint(soc_model)
        update["scene_assessment"] = base_sa
        update["semantic_move_record"] = sem_dict
        update["social_state_record"] = soc_dict
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
            update["character_mind_records"] = []
            update["scene_plan_record"] = ScenePlanRecord(
                selected_scene_function="establish_pressure",
                selected_responder_set=[],
                pacing_mode=pacing,
                silence_brevity_decision=dict(silence),
                planner_rationale_codes=["non_goc_slice"],
                selection_source="non_goc_slice",
            ).to_runtime_dict()
            return update
        prior = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else None
        yslice = state.get("goc_yaml_slice") if isinstance(state.get("goc_yaml_slice"), dict) else None
        base_sa = state.get("scene_assessment") if isinstance(state.get("scene_assessment"), dict) else {}
        sem_rec = state.get("semantic_move_record") if isinstance(state.get("semantic_move_record"), dict) else None
        soc_rec = state.get("social_state_record") if isinstance(state.get("social_state_record"), dict) else None
        responders, scene_fn, _implied, resolution = build_responder_and_function(
            player_input=player_input,
            interpreted_move=interpreted_move,
            pacing_mode=pacing,
            prior_continuity_impacts=prior,
            yaml_slice=yslice,
            current_scene_id=state.get("current_scene_id") or "",
            semantic_move_record=sem_rec,
            social_state_record=soc_rec,
        )
        merged_sa = {**base_sa, "multi_pressure_resolution": resolution}
        update["scene_assessment"] = merged_sa
        update["selected_responder_set"] = responders
        update["selected_scene_function"] = scene_fn
        update["pacing_mode"] = pacing
        update["silence_brevity_decision"] = silence
        primary = responders[0] if responders and isinstance(responders[0], dict) else {}
        active_keys = ["veronique", "michel", "annette", "alain"]
        if primary.get("actor_id"):
            aid = str(primary["actor_id"])
            if "veronique" in aid:
                active_keys = ["veronique", "michel", "annette", "alain"]
            elif "michel" in aid:
                active_keys = ["michel", "veronique", "annette", "alain"]
            elif "annette" in aid:
                active_keys = ["annette", "alain", "veronique", "michel"]
            elif "alain" in aid:
                active_keys = ["alain", "annette", "veronique", "michel"]
        mind_models = build_character_mind_records_for_goc(
            yaml_slice=yslice,
            active_character_keys=active_keys,
            current_scene_id=state.get("current_scene_id") or "",
        )
        mind_dicts = [m.to_runtime_dict() for m in mind_models]
        update["character_mind_records"] = mind_dicts
        sem_fp = ""
        soc_fp = ""
        if sem_rec:
            try:
                sem_fp = semantic_move_fingerprint(SemanticMoveRecord.model_validate(sem_rec))
            except Exception:
                sem_fp = str(sem_rec.get("move_type", ""))[:32]
        if soc_rec:
            try:
                soc_fp = social_state_fingerprint(SocialStateRecord.model_validate(soc_rec))
            except Exception:
                soc_fp = ""
        rationale_codes: list[str] = [
            str(resolution.get("selection_source") or "unknown"),
            f"scene_fn:{scene_fn}",
        ]
        scene_plan = ScenePlanRecord(
            selected_scene_function=scene_fn,
            selected_responder_set=list(responders),
            pacing_mode=pacing,
            silence_brevity_decision=dict(silence),
            planner_rationale_codes=rationale_codes,
            semantic_move_fingerprint=sem_fp,
            social_state_fingerprint=soc_fp,
            selection_source=str(resolution.get("selection_source") or "semantic_pipeline_v1"),
        )
        update["scene_plan_record"] = scene_plan.to_runtime_dict()
        return update

    def _route_model(self, state: RuntimeTurnState) -> RuntimeTurnState:
        decision = self.routing.choose(task_type=state["task_type"])
        selected = self.registry.get(decision.selected_model)
        update = _track(state, node_name="route_model")
        fallback_chain: list[str] = [decision.selected_model]
        if decision.fallback_model:
            fallback_chain.append(decision.fallback_model)
        code = decision.route_reason
        if code not in ROUTING_LABELS:
            code = "role_matrix_primary"
        update["routing"] = {
            "selected_model": decision.selected_model,
            "selected_provider": decision.selected_provider,
            "reason": decision.route_reason,
            "route_reason_code": code,
            "fallback_model": decision.fallback_model,
            "fallback_chain": fallback_chain,
            "route_mode": "primary_graph_route",
            "policy_id_used": STORY_RUNTIME_ROUTING_POLICY_ID,
            "policy_version_used": STORY_RUNTIME_ROUTING_POLICY_VERSION,
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
        if structured is None:
            raw = generation.get("content") if isinstance(generation.get("content"), str) else ""
            if not raw.strip():
                raw = generation.get("model_raw_text") if isinstance(generation.get("model_raw_text"), str) else ""
            if raw.strip().startswith("{"):
                try:
                    parsed = json.loads(raw)
                    if (
                        isinstance(parsed, dict)
                        and isinstance(parsed.get("narrative_response"), str)
                        and parsed["narrative_response"].strip()
                    ):
                        meta = dict(meta)
                        meta["structured_output"] = parsed
                        generation["metadata"] = meta
                        structured = parsed
                except json.JSONDecodeError:
                    pass
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
        narr = extract_proposed_narrative_text(proposed)
        eval_ctx = build_evaluation_context_from_runtime_state(
            module_id=str(state.get("module_id") or ""),
            proposed_narrative=narr,
            selected_scene_function=str(state.get("selected_scene_function") or "establish_pressure"),
            pacing_mode=str(state.get("pacing_mode") or "standard"),
            silence_brevity_decision=dict(silence),
            semantic_move_record=state.get("semantic_move_record") if isinstance(state.get("semantic_move_record"), dict) else None,
            social_state_record=state.get("social_state_record") if isinstance(state.get("social_state_record"), dict) else None,
            character_mind_records=list(state.get("character_mind_records") or [])
            if isinstance(state.get("character_mind_records"), list)
            else [],
            scene_plan_record=state.get("scene_plan_record") if isinstance(state.get("scene_plan_record"), dict) else None,
            prior_continuity_impacts=list(state.get("prior_continuity_impacts") or [])
            if isinstance(state.get("prior_continuity_impacts"), list)
            else [],
            selected_responder_set=list(state.get("selected_responder_set") or [])
            if isinstance(state.get("selected_responder_set"), list)
            else [],
        )
        outcome = run_validation_seam(
            module_id=state.get("module_id") or "",
            proposed_state_effects=proposed,
            generation=generation if isinstance(generation, dict) else {},
            evaluation_context=eval_ctx,
        )
        update["validation_outcome"] = outcome
        geo = outcome.get("dramatic_effect_gate_outcome")
        if isinstance(geo, dict):
            update["dramatic_effect_outcome"] = geo
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
        elif committed.get("commit_applied"):
            tp = "hard"
        elif validation.get("status") == "approved":
            tp = "soft"
        elif "fallback_model" in (state.get("nodes_executed") or []):
            tp = "diagnostics_only"
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
        from ai_stack.langgraph_runtime_package_output import package_runtime_graph_output

        return package_runtime_graph_output(
            state, graph_name=self.graph_name, graph_version=self.graph_version
        )

