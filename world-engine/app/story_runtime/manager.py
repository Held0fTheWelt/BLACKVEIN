from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import re

from story_runtime_core import ModelRegistry, RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, build_default_model_adapters
from story_runtime_core.model_registry import build_default_registry
from wos_ai_stack import (
    RuntimeTurnGraphExecutor,
    build_runtime_retriever,
    create_default_capability_registry,
)

from app.config import APP_VERSION
from app.observability.audit_log import log_story_runtime_failure, log_story_turn_event


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
        self.capability_registry = create_default_capability_registry(
            retriever=self.retriever,
            assembler=self.context_assembler,
            repo_root=self.repo_root,
        )
        self.turn_graph = RuntimeTurnGraphExecutor(
            interpreter=interpret_player_input,
            routing=self.routing,
            registry=self.registry,
            adapters=self.adapters,
            retriever=self.retriever,
            assembler=self.context_assembler,
            capability_registry=self.capability_registry,
        )

    @staticmethod
    def _scene_ids(runtime_projection: dict[str, Any]) -> set[str]:
        scenes = runtime_projection.get("scenes", [])
        scene_ids: set[str] = set()
        if isinstance(scenes, list):
            for scene in scenes:
                if isinstance(scene, dict):
                    scene_id = scene.get("id")
                    if isinstance(scene_id, str) and scene_id.strip():
                        scene_ids.add(scene_id.strip())
        return scene_ids

    @staticmethod
    def _transition_map(runtime_projection: dict[str, Any]) -> dict[str, set[str]]:
        hints = runtime_projection.get("transition_hints", [])
        mapping: dict[str, set[str]] = {}
        if isinstance(hints, list):
            for hint in hints:
                if not isinstance(hint, dict):
                    continue
                from_scene = hint.get("from")
                to_scene = hint.get("to")
                if not isinstance(from_scene, str) or not from_scene.strip():
                    continue
                if not isinstance(to_scene, str) or not to_scene.strip():
                    continue
                key = from_scene.strip()
                mapping.setdefault(key, set()).add(to_scene.strip())
        return mapping

    @staticmethod
    def _extract_scene_candidate(
        *,
        player_input: str,
        interpreted_input: dict[str, Any],
        known_scene_ids: set[str],
    ) -> str | None:
        kind = str(interpreted_input.get("kind") or "").strip().lower()
        command_name = str(interpreted_input.get("command_name") or "").strip().lower()
        command_args = interpreted_input.get("command_args")
        if kind == "explicit_command" and command_name in {"move", "goto", "go", "scene", "travel"}:
            if isinstance(command_args, list):
                for raw_arg in command_args:
                    arg = str(raw_arg).strip()
                    if arg in known_scene_ids:
                        return arg
            return None

        tokens = re.split(r"[^a-zA-Z0-9_\\-]+", player_input or "")
        for token in tokens:
            candidate = token.strip()
            if candidate and candidate in known_scene_ids:
                return candidate
        return None

    def _commit_progression(
        self,
        *,
        session: StorySession,
        player_input: str,
        interpreted_input: dict[str, Any],
    ) -> dict[str, Any]:
        known_scene_ids = self._scene_ids(session.runtime_projection)
        if session.current_scene_id:
            known_scene_ids.add(session.current_scene_id)
        transition_map = self._transition_map(session.runtime_projection)
        has_transition_rules = bool(transition_map)
        proposed_scene_id = self._extract_scene_candidate(
            player_input=player_input,
            interpreted_input=interpreted_input,
            known_scene_ids=known_scene_ids,
        )
        commit = {
            "from_scene_id": session.current_scene_id,
            "proposed_scene_id": proposed_scene_id,
            "committed_scene_id": session.current_scene_id,
            "allowed": False,
            "reason": "no_scene_proposal",
            "rule_source": "runtime_projection_transition_hints_v1",
        }
        if not proposed_scene_id:
            return commit
        if proposed_scene_id == session.current_scene_id:
            commit["reason"] = "already_in_scene"
            return commit
        if known_scene_ids and proposed_scene_id not in known_scene_ids:
            commit["reason"] = "unknown_target_scene"
            return commit
        if not has_transition_rules:
            commit["reason"] = "transition_hints_missing"
            return commit
        allowed_targets = transition_map.get(session.current_scene_id, set())
        if proposed_scene_id not in allowed_targets:
            commit["reason"] = "illegal_transition_not_allowed"
            return commit
        session.current_scene_id = proposed_scene_id
        commit["committed_scene_id"] = proposed_scene_id
        commit["allowed"] = True
        commit["reason"] = "committed"
        return commit

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

    def execute_turn(self, *, session_id: str, player_input: str, trace_id: str | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        session.turn_counter += 1
        session.updated_at = datetime.now(timezone.utc)
        try:
            graph_state = self.turn_graph.run(
                session_id=session.session_id,
                module_id=session.module_id,
                current_scene_id=session.current_scene_id,
                player_input=player_input,
                trace_id=trace_id,
                host_versions={"world_engine_app_version": APP_VERSION},
            )
        except Exception as exc:
            log_story_runtime_failure(
                trace_id=trace_id,
                story_session_id=session_id,
                operation="execute_turn",
                message=str(exc),
                failure_class="graph_execution_exception",
            )
            raise

        graph_diag = graph_state.get("graph_diagnostics", {}) if isinstance(graph_state.get("graph_diagnostics"), dict) else {}
        errors = graph_diag.get("errors", []) if isinstance(graph_diag.get("errors"), list) else []
        gen = graph_state.get("generation", {}) if isinstance(graph_state.get("generation"), dict) else {}
        interpreted_input = graph_state.get("interpreted_input", {})
        if not isinstance(interpreted_input, dict):
            interpreted_input = {}
        progression_commit = self._commit_progression(
            session=session,
            player_input=player_input,
            interpreted_input=interpreted_input,
        )
        model_ok = gen.get("success") is True
        outcome = "ok" if model_ok and not errors else "degraded"
        log_story_turn_event(
            trace_id=trace_id,
            story_session_id=session.session_id,
            module_id=session.module_id,
            turn_number=session.turn_counter,
            player_input=player_input,
            outcome=outcome,
            graph_error_count=len(errors),
        )

        event = {
            "turn_number": session.turn_counter,
            "trace_id": trace_id or "",
            "raw_input": player_input,
            "interpreted_input": interpreted_input,
            "progression_commit": progression_commit,
            "retrieval": graph_state.get("retrieval", {}),
            "model_route": {
                **graph_state.get("routing", {}),
                "generation": graph_state.get("generation", {}),
            },
            "graph": graph_state.get("graph_diagnostics", {}),
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
        last_progression_commit = None
        if session.history:
            tail = session.history[-1]
            if isinstance(tail, dict):
                maybe_progression = tail.get("progression_commit")
                if isinstance(maybe_progression, dict):
                    last_progression_commit = maybe_progression
        return {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "current_scene_id": session.current_scene_id,
            "runtime_projection": session.runtime_projection,
            "history_count": len(session.history),
            "committed_state": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "last_progression_commit": last_progression_commit,
            },
            "updated_at": session.updated_at.isoformat(),
        }

    def get_diagnostics(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        committed_state = {
            "current_scene_id": session.current_scene_id,
            "turn_counter": session.turn_counter,
        }
        return {
            "session_id": session.session_id,
            "turn_counter": session.turn_counter,
            "committed_state": committed_state,
            "diagnostics": session.diagnostics[-20:],
            "warnings": [
                "story_runtime_hosted_in_world_engine",
                "ai_proposals_require_authoritative_runtime_commit",
            ],
        }
