from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from ai_stack.capabilities import CapabilityRegistry
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RetrievalDomain, RetrievalRequest
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import ModelRegistry, RoutingPolicy


MINIMAL_PRIMARY_ADAPTER_INVOCATION_MODE = "raw_adapter_primary_minimal_runtime"
MINIMAL_PRIMARY_GRAPH_PATH_SUMMARY = "primary_invoke_raw_adapter_minimal_runtime"
RAW_FALLBACK_ADAPTER_INVOCATION_MODE = "raw_adapter_graph_managed_fallback"
RAW_FALLBACK_GRAPH_PATH_SUMMARY = "used_fallback_model_node_raw_adapter"


class MinimalRuntimeTurnGraphExecutor:
    """Dependency-thin fallback for story-runtime turn execution.

    This executor intentionally preserves the authoritative host contract shape when the
    full ai_stack LangGraph runtime is unavailable. It does not pretend to be the same
    path; repro metadata marks the execution mode explicitly.
    """

    def __init__(
        self,
        *,
        interpreter: Any,
        routing: RoutingPolicy,
        registry: ModelRegistry,
        adapters: dict[str, BaseModelAdapter],
        retriever: ContextRetriever,
        assembler: ContextPackAssembler,
        capability_registry: CapabilityRegistry | None = None,
    ) -> None:
        self.interpreter = interpreter
        self.routing = routing
        self.registry = registry
        self.adapters = adapters
        self.retriever = retriever
        self.assembler = assembler
        self.capability_registry = capability_registry
        self.graph_name = "wos_runtime_turn_graph"
        self.graph_version = "minimal_runtime_fallback_v1"

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
    ) -> dict[str, Any]:
        interpreted = self._as_dict(self.interpreter(player_input))
        retrieval, context_text, capability_audit = self._retrieve(
            module_id=module_id,
            scene_id=current_scene_id,
            player_input=player_input,
            trace_id=trace_id,
        )
        route = self.routing.choose(task_type="narrative_generation")
        route_info = {
            "selected_model": route.selected_model,
            "selected_provider": route.selected_provider,
            "route_reason": route.route_reason,
            "fallback_model": route.fallback_model,
        }

        nodes_executed = ["interpret_input", "retrieve_context", "route_model", "invoke_model"]
        errors: list[str] = []

        primary_result, primary_provider = self._invoke_provider(
            provider=route.selected_provider,
            prompt=self._build_prompt(
                module_id=module_id,
                current_scene_id=current_scene_id,
                player_input=player_input,
                interpreted_input=interpreted,
                context_text=context_text,
            ),
            context_text=context_text,
        )

        model_result = primary_result
        provider_used = primary_provider
        fallback_used = False
        adapter_invocation_mode = MINIMAL_PRIMARY_ADAPTER_INVOCATION_MODE
        graph_path_summary = MINIMAL_PRIMARY_GRAPH_PATH_SUMMARY
        execution_health = "healthy" if model_result.success else "degraded_generation"

        if not model_result.success:
            errors.append(str(model_result.metadata.get("error") or f"primary_provider_failed:{route.selected_provider}"))
            fallback_candidates = self._fallback_candidates(route.fallback_model, excluding={route.selected_provider})
            if fallback_candidates:
                nodes_executed.append("fallback_model")
            for fallback_provider in fallback_candidates:
                fallback_result, fallback_provider_used = self._invoke_provider(
                    provider=fallback_provider,
                    prompt=self._build_prompt(
                        module_id=module_id,
                        current_scene_id=current_scene_id,
                        player_input=player_input,
                        interpreted_input=interpreted,
                        context_text=context_text,
                    ),
                    context_text=context_text,
                )
                if fallback_result.success:
                    model_result = fallback_result
                    provider_used = fallback_provider_used
                    fallback_used = True
                    adapter_invocation_mode = RAW_FALLBACK_ADAPTER_INVOCATION_MODE
                    graph_path_summary = RAW_FALLBACK_GRAPH_PATH_SUMMARY
                    execution_health = "model_fallback"
                    break
                errors.append(
                    str(
                        fallback_result.metadata.get("error")
                        or f"fallback_provider_failed:{fallback_provider}"
                    )
                )

        structured_output = self._structured_output_from_result(model_result, interpreted)
        generation_metadata = dict(model_result.metadata)
        generation_metadata.setdefault("structured_output", structured_output)
        generation_metadata["provider_used"] = provider_used
        generation_metadata["runtime_mode"] = "minimal_runtime_fallback"
        generation_metadata["retrieval_context_attached"] = bool(context_text)

        visible_output_bundle = {
            "gm_narration": [structured_output.get("narrative_response") or model_result.content or "The room holds."],
            "spoken_lines": [],
        }

        graph_diagnostics = {
            "graph_name": self.graph_name,
            "graph_version": self.graph_version,
            "nodes_executed": nodes_executed,
            "capability_audit": capability_audit,
            "errors": [] if (model_result.success or fallback_used) else errors,
            "fallback_path_taken": fallback_used,
            "execution_health": execution_health,
            "repro_metadata": {
                "trace_id": trace_id or "",
                "module_id": module_id,
                "session_id": session_id,
                "adapter_invocation_mode": adapter_invocation_mode,
                "graph_path_summary": graph_path_summary,
                "provider_used": provider_used,
                "world_engine_minimal_runtime_fallback": True,
            },
        }

        return {
            "interpreted_input": interpreted,
            "retrieval": retrieval,
            "routing": route_info,
            "generation": {
                "success": model_result.success,
                "content": model_result.content,
                "metadata": generation_metadata,
                "retrieval_context_attached": bool(context_text),
                "fallback_used": fallback_used,
            },
            "graph_diagnostics": graph_diagnostics,
            "visible_output_bundle": visible_output_bundle,
            "selected_scene_function": "minimal_runtime_turn_response",
            "selected_responder_set": [{"actor_id": provider_used or "mock", "selection_mode": "minimal_runtime_fallback"}],
            "social_state_record": {
                "mode": "minimal_runtime_fallback",
                "thread_pressure_summary": thread_pressure_summary or "",
                "active_narrative_thread_count": len(active_narrative_threads or []),
            },
            "diagnostics_refs": [],
            "experiment_preview": bool(force_experiment_preview),
            "validation_outcome": {"status": "not_run_minimal_runtime_fallback"},
            "committed_result": {"status": "authoritative_commit_host_managed"},
            "continuity_impacts": list(prior_continuity_impacts or []),
        }

    def _retrieve(
        self,
        *,
        module_id: str,
        scene_id: str,
        player_input: str,
        trace_id: str | None,
    ) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
        if self.capability_registry is not None:
            before = len(self.capability_registry.recent_audit(limit=2000))
            result = self.capability_registry.invoke(
                name="wos.context_pack.build",
                mode="runtime",
                actor="world_engine.story_runtime.minimal_runtime_fallback",
                payload={
                    "domain": RetrievalDomain.RUNTIME.value,
                    "profile": "runtime_turn_support",
                    "query": player_input,
                    "module_id": module_id,
                    "scene_id": scene_id,
                    "max_chunks": 4,
                },
                trace_id=trace_id,
            )
            audit = self.capability_registry.recent_audit(limit=2000)[before:]
            return dict(result.get("retrieval", {})), str(result.get("context_text", "")), audit

        retrieval_result = self.retriever.retrieve(
            RetrievalRequest(
                domain=RetrievalDomain.RUNTIME,
                profile="runtime_turn_support",
                query=player_input,
                module_id=module_id,
                scene_id=scene_id,
                max_chunks=4,
            )
        )
        context_pack = self.assembler.assemble(retrieval_result)
        retrieval = {
            "domain": context_pack.domain,
            "profile": context_pack.profile,
            "status": context_pack.status,
            "hit_count": context_pack.hit_count,
            "sources": context_pack.sources,
            "ranking_notes": context_pack.ranking_notes,
        }
        return retrieval, context_pack.compact_context, []

    def _fallback_candidates(self, fallback_model: str | None, *, excluding: set[str]) -> list[str]:
        candidates: list[str] = []
        if fallback_model:
            spec = self.registry.get(fallback_model)
            if spec is not None and spec.provider not in candidates:
                candidates.append(spec.provider)
        if "mock" in self.adapters and "mock" not in candidates:
            candidates.append("mock")
        return [provider for provider in candidates if provider not in excluding and provider in self.adapters]

    def _invoke_provider(self, *, provider: str, prompt: str, context_text: str) -> tuple[ModelCallResult, str]:
        adapter = self.adapters.get(provider)
        if adapter is None:
            return ModelCallResult(content="", success=False, metadata={"error": f"missing_provider_adapter:{provider}"}), provider
        result = adapter.generate(prompt, retrieval_context=context_text or None)
        return result, provider

    @staticmethod
    def _build_prompt(
        *,
        module_id: str,
        current_scene_id: str,
        player_input: str,
        interpreted_input: dict[str, Any],
        context_text: str,
    ) -> str:
        lines = [
            f"Module: {module_id}",
            f"Current scene: {current_scene_id or 'unknown'}",
            f"Player input: {player_input}",
            f"Interpreted kind: {interpreted_input.get('kind', 'unknown')}",
        ]
        if context_text:
            lines.append("Use the attached retrieval context when responding.")
        lines.append("Return a short in-world continuation.")
        return "\n".join(lines)

    @staticmethod
    def _structured_output_from_result(result: ModelCallResult, interpreted_input: dict[str, Any]) -> dict[str, Any]:
        metadata = result.metadata if isinstance(result.metadata, dict) else {}
        structured = metadata.get("structured_output")
        if isinstance(structured, dict):
            return dict(structured)
        text = (result.content or "").strip() or "The room holds for a beat."
        return {
            "narrative_response": text,
            "proposed_scene_id": None,
            "intent_summary": str(interpreted_input.get("intent") or ""),
        }

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            dumped = value.model_dump(mode="json")
            if isinstance(dumped, dict):
                return dumped
        if is_dataclass(value):
            dumped = asdict(value)
            if isinstance(dumped, dict):
                return dumped
        if hasattr(value, "__dict__"):
            return {
                key: val
                for key, val in vars(value).items()
                if not key.startswith("_")
            }
        return {"value": value}
