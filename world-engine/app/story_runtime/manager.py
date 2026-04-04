from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from story_runtime_core import ModelRegistry, RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, build_default_model_adapters
from story_runtime_core.model_registry import build_default_registry
from wos_ai_stack import RetrievalDomain, RetrievalRequest, build_runtime_retriever


@dataclass
class StorySession:
    session_id: str
    module_id: str
    runtime_projection: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    turn_counter: int = 0
    current_scene_id: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)


class StoryRuntimeManager:
    def __init__(
        self,
        *,
        registry: ModelRegistry | None = None,
        adapters: dict[str, BaseModelAdapter] | None = None,
        retriever: Any | None = None,
        context_assembler: Any | None = None,
    ) -> None:
        self.sessions: dict[str, StorySession] = {}
        self.registry = registry or build_default_registry()
        self.routing = RoutingPolicy(self.registry)
        self.adapters: dict[str, BaseModelAdapter] = adapters or build_default_model_adapters()
        self.repo_root = Path(__file__).resolve().parents[3]
        if retriever is None or context_assembler is None:
            default_retriever, default_assembler, corpus = build_runtime_retriever(self.repo_root)
            self.retriever = retriever or default_retriever
            self.context_assembler = context_assembler or default_assembler
            self.retrieval_corpus = corpus
        else:
            self.retriever = retriever
            self.context_assembler = context_assembler
            self.retrieval_corpus = None

    def create_session(self, *, module_id: str, runtime_projection: dict[str, Any]) -> StorySession:
        session_id = uuid4().hex
        current_scene_id = str(runtime_projection.get("start_scene_id") or "")
        session = StorySession(
            session_id=session_id,
            module_id=module_id,
            runtime_projection=runtime_projection,
            current_scene_id=current_scene_id,
        )
        self.sessions[session_id] = session
        return session

    def execute_turn(self, *, session_id: str, player_input: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        interpretation = interpret_player_input(player_input)
        task_type = "classification" if interpretation.kind.value in {"explicit_command", "meta"} else "narrative_generation"
        routing = self.routing.choose(task_type=task_type)
        selected = self.registry.get(routing.selected_model)
        adapter = self.adapters.get(routing.selected_provider or "")
        retrieval_request = RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query=f"{player_input}\nscene:{session.current_scene_id}\nmodule:{session.module_id}",
            module_id=session.module_id,
            scene_id=session.current_scene_id,
            max_chunks=4,
        )
        retrieval_result = self.retriever.retrieve(retrieval_request)
        context_pack = self.context_assembler.assemble(retrieval_result)
        model_prompt = player_input if not context_pack.compact_context else f"{player_input}\n\n{context_pack.compact_context}"

        session.turn_counter += 1
        session.updated_at = datetime.now(timezone.utc)

        generation: dict[str, object] = {
            "attempted": False,
            "success": None,
            "error": None,
            "retrieval_context_attached": bool(context_pack.compact_context),
            "prompt_length": len(model_prompt),
        }
        if adapter and selected:
            generation["attempted"] = True
            timeout = float(selected.timeout_seconds)
            call = adapter.generate(
                model_prompt,
                timeout_seconds=timeout,
                retrieval_context=context_pack.compact_context,
            )
            generation["success"] = call.success
            generation["error"] = call.metadata.get("error") if not call.success else None

        event = {
            "turn_number": session.turn_counter,
            "raw_input": player_input,
            "interpreted_input": interpretation.model_dump(mode="json"),
            "retrieval": {
                "domain": context_pack.domain,
                "profile": context_pack.profile,
                "status": context_pack.status,
                "hit_count": context_pack.hit_count,
                "sources": context_pack.sources,
                "ranking_notes": context_pack.ranking_notes,
            },
            "model_route": {
                "selected_model": routing.selected_model,
                "selected_provider": routing.selected_provider,
                "reason": routing.route_reason,
                "fallback_model": routing.fallback_model,
                "timeout_seconds": selected.timeout_seconds if selected else None,
                "structured_output_success": bool(selected.structured_output_capable) if selected else False,
                "registered_adapter_providers": sorted(self.adapters.keys()),
                "generation": generation,
            },
        }
        session.history.append(event)
        session.diagnostics.append(event)
        return event

    def get_session(self, session_id: str) -> StorySession:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def get_state(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "current_scene_id": session.current_scene_id,
            "runtime_projection": session.runtime_projection,
            "history_count": len(session.history),
            "updated_at": session.updated_at.isoformat(),
        }

    def get_diagnostics(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return {
            "session_id": session.session_id,
            "turn_counter": session.turn_counter,
            "diagnostics": session.diagnostics[-20:],
            "warnings": [
                "story_runtime_hosted_in_world_engine",
                "ai_proposals_are_non_authoritative",
            ],
        }
