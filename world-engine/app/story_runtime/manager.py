from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from story_runtime_core import ModelRegistry, RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, build_default_model_adapters
from story_runtime_core.model_registry import build_default_registry
from ai_stack import (
    RuntimeTurnGraphExecutor,
    build_runtime_retriever,
    create_default_capability_registry,
)
from ai_stack.story_runtime_playability import is_hard_boundary_failure

from app.config import APP_VERSION, allow_ungoverned_story_runtime
from app.repo_root import resolve_wos_repo_root
from app.observability.audit_log import log_story_runtime_failure, log_story_turn_event
from app.observability.runtime_metrics import StoryRuntimeMetrics
from app.story_runtime.governed_runtime import build_governed_story_runtime_components
from app.story_runtime.live_governance import (
    BlockedLiveStoryRoutingPolicy,
    LiveStoryGovernanceError,
    is_governed_resolved_config_operational,
    opening_text_contains_preview_placeholder,
)
from app.story_runtime.commit_models import resolve_narrative_commit
from app.story_runtime.story_session_store import JsonStorySessionStore
from app.story_runtime.module_turn_hooks import (
    goc_append_continuity_impacts,
    goc_host_experience_template,
    goc_prior_continuity_for_graph,
)
from app.story_runtime.narrative_threads import (
    NARRATIVE_COMMIT_HISTORY_TAIL,
    StoryNarrativeThreadSet,
    ThreadUpdateTrace,
    build_graph_thread_export,
    thread_continuity_metrics,
    update_narrative_threads,
)


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
    narrative_threads: StoryNarrativeThreadSet = field(default_factory=StoryNarrativeThreadSet)
    last_thread_update_trace: ThreadUpdateTrace | None = None
    # Bounded carry-forward of committed GoC continuity classes (not a second memory surface).
    prior_continuity_impacts: list[dict[str, Any]] = field(default_factory=list)
    # Immutable-ish snapshot of published content identity at session birth (audit F-M3).
    content_provenance: dict[str, Any] = field(default_factory=dict)


def _parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def story_session_to_payload(session: StorySession) -> dict[str, Any]:
    trace = session.last_thread_update_trace
    return {
        "format_version": 1,
        "session_id": session.session_id,
        "module_id": session.module_id,
        "runtime_projection": session.runtime_projection,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "turn_counter": session.turn_counter,
        "current_scene_id": session.current_scene_id,
        "history": session.history,
        "diagnostics": session.diagnostics,
        "narrative_threads": session.narrative_threads.model_dump(mode="json"),
        "last_thread_update_trace": trace.model_dump(mode="json") if trace is not None else None,
        "prior_continuity_impacts": session.prior_continuity_impacts,
        "content_provenance": session.content_provenance,
    }


def story_session_from_payload(data: dict[str, Any]) -> StorySession:
    fv = data.get("format_version", 1)
    if fv != 1:
        raise ValueError(f"Unsupported story session snapshot format_version: {fv!r}")

    raw_trace = data.get("last_thread_update_trace")
    trace: ThreadUpdateTrace | None = None
    if isinstance(raw_trace, dict):
        trace = ThreadUpdateTrace.model_validate(raw_trace)

    threads_raw = data.get("narrative_threads") or {}
    threads = StoryNarrativeThreadSet.model_validate(threads_raw)

    created_at = _parse_iso_datetime(str(data["created_at"]))
    updated_at = _parse_iso_datetime(str(data["updated_at"]))

    provenance = data.get("content_provenance")
    if not isinstance(provenance, dict):
        provenance = {}

    return StorySession(
        session_id=str(data["session_id"]),
        module_id=str(data["module_id"]),
        runtime_projection=dict(data["runtime_projection"]),
        created_at=created_at,
        updated_at=updated_at,
        turn_counter=int(data.get("turn_counter", 0)),
        current_scene_id=str(data.get("current_scene_id") or ""),
        history=list(data.get("history") or []),
        diagnostics=list(data.get("diagnostics") or []),
        narrative_threads=threads,
        last_thread_update_trace=trace,
        prior_continuity_impacts=list(data.get("prior_continuity_impacts") or []),
        content_provenance=provenance,
    )


def _coerce_visible_text_lines(value: Any) -> list[str]:
    if isinstance(value, str):
        line = value.strip()
        return [line] if line else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _visible_lines_from_turn_event(event: dict[str, Any]) -> list[str]:
    bundle = event.get("visible_output_bundle") if isinstance(event.get("visible_output_bundle"), dict) else {}
    lines = _coerce_visible_text_lines(bundle.get("gm_narration"))
    if lines:
        return lines

    generation = ((event.get("model_route") or {}).get("generation") or {}) if isinstance(event.get("model_route"), dict) else {}
    lines = _coerce_visible_text_lines(generation.get("content") or generation.get("model_raw_text"))
    if lines:
        return lines

    commit = event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {}
    status = str(commit.get("situation_status") or "").strip()
    return [status] if status else []


def _story_window_entries_for_session(session: StorySession) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for event in session.diagnostics:
        if not isinstance(event, dict):
            continue
        turn_number = event.get("turn_number")
        turn_kind = str(event.get("turn_kind") or "player").strip() or "player"
        commit = event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {}
        consequences = commit.get("committed_consequences")
        consequence_lines = [str(item) for item in consequences] if isinstance(consequences, list) else []
        bundle = event.get("visible_output_bundle") if isinstance(event.get("visible_output_bundle"), dict) else {}
        spoken_lines = _coerce_visible_text_lines(bundle.get("spoken_lines"))

        if turn_kind != "opening":
            raw_input = str(event.get("raw_input") or "").strip()
            if raw_input:
                entries.append(
                    {
                        "entry_id": f"{session.session_id}:{turn_number}:player",
                        "kind": "player_turn",
                        "role": "player",
                        "speaker": "You",
                        "turn_number": turn_number,
                        "text": raw_input,
                        "source": "player_input",
                    }
                )

        visible_lines = _visible_lines_from_turn_event(event)
        if not visible_lines and not spoken_lines and not consequence_lines:
            continue
        entries.append(
            {
                "entry_id": f"{session.session_id}:{turn_number}:{turn_kind}",
                "kind": "opening" if turn_kind == "opening" else "runtime_response",
                "role": "runtime",
                "speaker": "World of Shadows",
                "turn_number": turn_number,
                "text": "\n\n".join(visible_lines),
                "spoken_lines": spoken_lines,
                "committed_consequences": consequence_lines,
                "source": "authoritative_story_runtime",
                "runtime_governance_surface": event.get("runtime_governance_surface"),
            }
        )
    return entries


class StoryRuntimeManager:
    def __init__(
        self,
        *,
        registry: ModelRegistry | None = None,
        adapters: dict[str, BaseModelAdapter] | None = None,
        retriever: Any | None = None,
        context_assembler: Any | None = None,
        session_store: JsonStorySessionStore | None = None,
        governed_runtime_config: dict[str, Any] | None = None,
        metrics: StoryRuntimeMetrics | None = None,
    ) -> None:
        self.sessions: dict[str, StorySession] = {}
        self._session_store = session_store
        self._session_turn_locks: dict[str, threading.Lock] = {}
        self._session_locks_guard = threading.Lock()
        self.repo_root = resolve_wos_repo_root(start=Path(__file__).resolve().parent)
        self.metrics = metrics or StoryRuntimeMetrics()
        self._governed_runtime_config: dict[str, Any] | None = None
        self._runtime_config_status: dict[str, Any] = {
            "source": "default_registry",
            "config_version": None,
            "last_reload_ok": None,
            "route_count": 0,
            "model_count": 0,
            "live_execution_blocked": False,
        }
        self.turn_graph: RuntimeTurnGraphExecutor | None = None
        # Isolated tests inject custom adapters/registry; skip Turn-0 graph opening there (fixtures are not
        # full GoC-shaped). Production and API tests construct the manager without injected adapters.
        self._skip_graph_opening_on_create = registry is not None or adapters is not None
        if registry is not None and adapters is not None:
            self.registry = registry
            self.routing = RoutingPolicy(self.registry)
            self.adapters = adapters
            self._runtime_config_status = {
                "source": "injected_test_components",
                "config_version": None,
                "last_reload_ok": True,
                "route_count": 0,
                "model_count": len(self.registry.all()),
                "live_execution_blocked": False,
            }
        elif adapters is not None:
            # Tests often pass custom adapters without a registry; do not let
            # ``_apply_runtime_components`` overwrite them with defaults.
            components = build_governed_story_runtime_components(governed_runtime_config)
            if components is not None:
                reg, rout, _ = components
                self.registry = reg
                self.routing = rout
                self.adapters = adapters
                self._governed_runtime_config = dict(governed_runtime_config or {})
                self._runtime_config_status = {
                    "source": "governed_runtime_config_with_injected_adapters",
                    "config_version": (governed_runtime_config or {}).get("config_version"),
                    "last_reload_ok": True,
                    "route_count": len((governed_runtime_config or {}).get("routes") or []),
                    "model_count": len(self.registry.all()),
                    "live_execution_blocked": False,
                }
            else:
                self._governed_runtime_config = (
                    dict(governed_runtime_config) if isinstance(governed_runtime_config, dict) else None
                )
                if allow_ungoverned_story_runtime():
                    self.registry = build_default_registry()
                    self.routing = RoutingPolicy(self.registry)
                    self.adapters = adapters
                    self._runtime_config_status = {
                        "source": "injected_adapters_default_registry",
                        "config_version": self._governed_runtime_config.get("config_version")
                        if isinstance(self._governed_runtime_config, dict)
                        else None,
                        "last_reload_ok": True,
                        "route_count": 0,
                        "model_count": len(self.registry.all()),
                        "live_execution_blocked": False,
                    }
                else:
                    self.registry = ModelRegistry()
                    self.routing = BlockedLiveStoryRoutingPolicy()
                    self.adapters = adapters
                    self._runtime_config_status = {
                        "source": "governed_config_invalid_or_missing",
                        "config_version": self._governed_runtime_config.get("config_version")
                        if isinstance(self._governed_runtime_config, dict)
                        else None,
                        "last_reload_ok": False,
                        "route_count": 0,
                        "model_count": 0,
                        "live_execution_blocked": True,
                        "live_execution_block_reason": "injected_adapters_without_governed_config",
                    }
        else:
            self._apply_runtime_components(governed_runtime_config)
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
        self._rebuild_turn_graph()
        if self._session_store is not None:
            for _sid, raw in self._session_store.load_all_raw().items():
                try:
                    loaded = story_session_from_payload(raw)
                    self.sessions[loaded.session_id] = loaded
                    with self._session_locks_guard:
                        self._session_turn_locks.setdefault(loaded.session_id, threading.Lock())
                except Exception:
                    continue

    def _session_turn_lock(self, session_id: str) -> threading.Lock:
        with self._session_locks_guard:
            return self._session_turn_locks.setdefault(session_id, threading.Lock())

    def _persist_session(self, session: StorySession) -> None:
        if self._session_store is None:
            return
        self._session_store.save(session.session_id, story_session_to_payload(session))

    def _max_self_correction_attempts(self) -> int:
        settings = (
            (self._governed_runtime_config or {}).get("world_engine_settings") or {}
            if isinstance(self._governed_runtime_config, dict)
            else {}
        )
        try:
            v = int(settings.get("max_self_correction_attempts", settings.get("max_retry_attempts", 3)))
            return max(0, v)
        except Exception:
            return 3

    def _allow_degraded_commit_after_retries(self) -> bool:
        settings = (
            (self._governed_runtime_config or {}).get("world_engine_settings") or {}
            if isinstance(self._governed_runtime_config, dict)
            else {}
        )
        return bool(settings.get("allow_degraded_commit_after_retries", True))

    def _opening_retry_count(self) -> int:
        settings = (
            (self._governed_runtime_config or {}).get("world_engine_settings") or {}
            if isinstance(self._governed_runtime_config, dict)
            else {}
        )
        try:
            return max(0, int(settings.get("opening_retry_attempts", 2)))
        except Exception:
            return 2

    def _apply_runtime_components(self, governed_runtime_config: dict[str, Any] | None) -> None:
        components = build_governed_story_runtime_components(governed_runtime_config)
        if components is not None:
            reg, rout, adp = components
            self.registry = reg
            self.routing = rout
            self.adapters = adp
            self._governed_runtime_config = dict(governed_runtime_config or {})
            self._runtime_config_status = {
                "source": "governed_runtime_config",
                "config_version": (governed_runtime_config or {}).get("config_version"),
                "last_reload_ok": True,
                "route_count": len((governed_runtime_config or {}).get("routes") or []),
                "model_count": len((governed_runtime_config or {}).get("models") or []),
                "live_execution_blocked": False,
            }
            self.metrics.incr(
                "runtime_config_apply_success",
                source="governed_runtime_config",
                config_version=(governed_runtime_config or {}).get("config_version"),
            )
            return
        if allow_ungoverned_story_runtime():
            self._governed_runtime_config = (
                dict(governed_runtime_config) if isinstance(governed_runtime_config, dict) else None
            )
            self.registry = build_default_registry()
            self.routing = RoutingPolicy(self.registry)
            self.adapters = build_default_model_adapters()
            self._runtime_config_status = {
                "source": "default_registry",
                "config_version": (governed_runtime_config or {}).get("config_version")
                if isinstance(governed_runtime_config, dict)
                else None,
                "last_reload_ok": False if isinstance(governed_runtime_config, dict) else None,
                "route_count": 0,
                "model_count": 0,
                "live_execution_blocked": False,
            }
            self.metrics.incr(
                "runtime_config_apply_fallback_default",
                source="default_registry",
                config_version=self._runtime_config_status.get("config_version"),
            )
            return
        reason = "resolved_config_unusable"
        if not isinstance(governed_runtime_config, dict):
            reason = "resolved_config_missing"
        elif not is_governed_resolved_config_operational(governed_runtime_config):
            reason = "resolved_config_incomplete_or_invalid"
        self._apply_blocked_runtime_components(governed_runtime_config, reason_code=reason)

    def _apply_blocked_runtime_components(
        self, governed_runtime_config: dict[str, Any] | None, *, reason_code: str
    ) -> None:
        """Fail-closed posture: no default registry, no hidden live-capable adapters."""
        self._governed_runtime_config = dict(governed_runtime_config) if isinstance(governed_runtime_config, dict) else None
        self.registry = ModelRegistry()
        self.routing = BlockedLiveStoryRoutingPolicy()
        self.adapters = {}
        self._runtime_config_status = {
            "source": "governed_config_invalid_or_missing",
            "config_version": (governed_runtime_config or {}).get("config_version")
            if isinstance(governed_runtime_config, dict)
            else None,
            "last_reload_ok": False,
            "route_count": 0,
            "model_count": 0,
            "live_execution_blocked": True,
            "live_execution_block_reason": reason_code,
        }
        self.metrics.incr(
            "runtime_config_apply_blocked",
            source="governed_config_invalid_or_missing",
            reason=reason_code,
            config_version=self._runtime_config_status.get("config_version"),
        )

    def _rebuild_turn_graph(self) -> None:
        gen_mode = None
        if isinstance(self._governed_runtime_config, dict):
            gen_mode = str(self._governed_runtime_config.get("generation_execution_mode") or "").strip() or None
        self.turn_graph = RuntimeTurnGraphExecutor(
            interpreter=interpret_player_input,
            routing=self.routing,
            registry=self.registry,
            adapters=self.adapters,
            retriever=self.retriever,
            assembler=self.context_assembler,
            capability_registry=self.capability_registry,
            max_self_correction_attempts=self._max_self_correction_attempts(),
            allow_degraded_commit_after_retries=self._allow_degraded_commit_after_retries(),
            generation_execution_mode=gen_mode,
        )

    def reload_runtime_config(self, governed_runtime_config: dict[str, Any] | None) -> dict[str, Any]:
        self._apply_runtime_components(governed_runtime_config)
        self._rebuild_turn_graph()
        return self.runtime_config_status()

    def runtime_config_status(self) -> dict[str, Any]:
        src = str(self._runtime_config_status.get("source") or "")
        governed = src in {"governed_runtime_config", "governed_runtime_config_with_injected_adapters"}
        return {
            **self._runtime_config_status,
            "governed_runtime_active": governed and not bool(self._runtime_config_status.get("live_execution_blocked")),
            "legacy_default_registry_path": src == "default_registry",
            "max_self_correction_attempts": self._max_self_correction_attempts(),
            "allow_degraded_commit_after_retries": self._allow_degraded_commit_after_retries(),
            "metrics": self.metrics.summary(),
        }

    def _live_governance_enforced_for_player_paths(self) -> bool:
        if allow_ungoverned_story_runtime():
            return False
        src = str(self._runtime_config_status.get("source") or "")
        return not src.startswith("injected")

    def _assert_live_player_governance(self) -> None:
        if not self._live_governance_enforced_for_player_paths():
            return
        st = self._runtime_config_status
        src = str(st.get("source") or "")
        governed = src in {"governed_runtime_config", "governed_runtime_config_with_injected_adapters"}
        if st.get("live_execution_blocked") or not governed:
            raise LiveStoryGovernanceError(
                f"LIVE_STORY_RUNTIME_BLOCKED: runtime_source={src!r} live_execution_blocked={st.get('live_execution_blocked')!r}"
            )
        if not str(st.get("config_version") or "").strip():
            raise LiveStoryGovernanceError("LIVE_STORY_RUNTIME_BLOCKED: config_version is missing on governed runtime surface.")

    def _build_opening_prompt(self, session: StorySession) -> str:
        projection = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
        scene_id = str(projection.get("start_scene_id") or session.current_scene_id or "opening")
        scenes = projection.get("scenes") if isinstance(projection.get("scenes"), list) else []
        scene_row = next(
            (
                row
                for row in scenes
                if isinstance(row, dict) and str(row.get("scene_id") or row.get("id") or "") == scene_id
            ),
            {},
        )
        scene_name = str(scene_row.get("name") or scene_id)
        scene_desc = str(scene_row.get("description") or "")
        chars = projection.get("character_ids") if isinstance(projection.get("character_ids"), list) else []
        cast = ", ".join(str(c) for c in chars[:8]) if chars else "unknown"
        return (
            f"Opening turn for module {session.module_id}. "
            f"Establish the starting situation in scene {scene_name} ({scene_id}). "
            f"Scene description: {scene_desc or 'n/a'}. Cast: {cast}. "
            "Write vivid but grounded opening narration within canonical module boundaries. "
            "Set initial dramatic pressure, social posture, and opening narrative threads."
        )

    def _opening_commit_acceptable(self, graph_state: dict[str, Any]) -> bool:
        val = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
        if val.get("status") != "approved":
            return False
        module_id = str(graph_state.get("module_id") or "")
        committed = graph_state.get("committed_result") if isinstance(graph_state.get("committed_result"), dict) else {}
        # GoC uses an explicit commit seam; non-GoC vertical slices may approve without the same commit envelope.
        if module_id == "god_of_carnage" and not committed.get("commit_applied"):
            return False
        bundle = graph_state.get("visible_output_bundle") if isinstance(graph_state.get("visible_output_bundle"), dict) else {}
        gm = bundle.get("gm_narration")
        if isinstance(gm, list):
            joined = "\n".join(str(x) for x in gm)
            if opening_text_contains_preview_placeholder(joined):
                return False
        return True

    def _visible_narration_present(self, graph_state: dict[str, Any]) -> bool:
        gen = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
        raw = str(gen.get("content") or gen.get("model_raw_text") or "").strip()
        if raw:
            return True
        bundle = graph_state.get("visible_output_bundle") if isinstance(graph_state.get("visible_output_bundle"), dict) else {}
        gm = bundle.get("gm_narration")
        if isinstance(gm, list) and any(str(x).strip() for x in gm):
            return True
        return False

    def _finalize_committed_turn(
        self,
        *,
        session: StorySession,
        graph_state: dict[str, Any],
        trace_id: str | None,
        commit_turn_number: int,
        player_input: str,
        turn_kind: str | None,
        prior_scene_id: str,
        history_tail: list,
        graph_threads: list[dict[str, Any]] | None,
        graph_summary: str | None,
        host_experience_template: dict[str, Any] | None,
        prior_ci: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        goc_append_continuity_impacts(session.module_id, session.prior_continuity_impacts, graph_state)
        graph_diag = graph_state.get("graph_diagnostics", {}) if isinstance(graph_state.get("graph_diagnostics"), dict) else {}
        errors = graph_diag.get("errors", []) if isinstance(graph_diag.get("errors"), list) else []
        gen = graph_state.get("generation", {}) if isinstance(graph_state.get("generation"), dict) else {}
        interpreted_input = graph_state.get("interpreted_input", {})
        if not isinstance(interpreted_input, dict):
            interpreted_input = {}
        narrative_commit = resolve_narrative_commit(
            turn_number=commit_turn_number,
            prior_scene_id=prior_scene_id,
            player_input=player_input,
            interpreted_input=interpreted_input,
            generation=gen,
            runtime_projection=session.runtime_projection,
        )
        session.current_scene_id = narrative_commit.committed_scene_id
        session.narrative_threads, session.last_thread_update_trace = update_narrative_threads(
            prior=session.narrative_threads,
            latest_commit=narrative_commit,
            history_tail=history_tail,
            committed_scene_id=narrative_commit.committed_scene_id,
            turn_number=commit_turn_number,
        )
        model_ok = gen.get("success") is True
        outcome = "ok" if model_ok and not errors else "degraded"
        log_story_turn_event(
            trace_id=trace_id,
            story_session_id=session.session_id,
            module_id=session.module_id,
            turn_number=commit_turn_number,
            player_input=player_input,
            outcome=outcome,
            graph_error_count=len(errors),
        )
        narrative_commit_payload = narrative_commit.model_dump(mode="json")
        r_src = str(self._runtime_config_status.get("source") or "")
        governed_active = r_src in {"governed_runtime_config", "governed_runtime_config_with_injected_adapters"} and not bool(
            self._runtime_config_status.get("live_execution_blocked")
        )
        gov: dict[str, Any] = {
            "source": self._runtime_config_status.get("source"),
            "config_version": self._runtime_config_status.get("config_version"),
            "governed_runtime_active": governed_active,
            "legacy_default_registry_path": r_src == "default_registry",
            "live_execution_blocked": bool(self._runtime_config_status.get("live_execution_blocked")),
        }
        routing = graph_state.get("routing") if isinstance(graph_state.get("routing"), dict) else {}
        gov["primary_route_selection"] = {
            "selected_model_id": routing.get("selected_model"),
            "selected_provider_id": routing.get("selected_provider"),
            "route_reason_code": routing.get("route_reason_code"),
            "fallback_chain": routing.get("fallback_chain"),
        }
        gov["fallback_stage_reached"] = routing.get("fallback_stage_reached") or (
            "graph_fallback_executed" if "fallback_model" in (graph_state.get("nodes_executed") or []) else "primary_only"
        )
        gen_meta = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
        gov["final_model_invocation"] = {
            "adapter": gen_meta.get("adapter"),
            "api_model": gen_meta.get("model"),
            "adapter_invocation_mode": gen_meta.get("adapter_invocation_mode"),
        }
        gov["route_selected_model"] = routing.get("selected_model")
        gov["route_selected_provider"] = routing.get("selected_provider")
        gov["route_reason_code"] = routing.get("route_reason_code")
        gov["adapter"] = gen_meta.get("adapter")
        gov["api_model"] = gen_meta.get("model")
        self_correction = graph_state.get("self_correction") if isinstance(graph_state.get("self_correction"), dict) else {}
        gov["self_correction_attempt_count"] = self_correction.get("attempt_count")
        val = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
        gov["validation_reason"] = val.get("reason")
        gov["mock_output_flag"] = bool(str(gen.get("content") or "").strip().startswith("[mock]"))
        event: dict[str, Any] = {
            "turn_number": commit_turn_number,
            "turn_kind": turn_kind or "player",
            "trace_id": trace_id or "",
            "raw_input": player_input,
            "interpreted_input": interpreted_input,
            "narrative_commit": narrative_commit_payload,
            "retrieval": graph_state.get("retrieval", {}),
            "model_route": {**routing, "generation": gen},
            "graph": graph_diag,
            "visible_output_bundle": graph_state.get("visible_output_bundle"),
            "diagnostics_refs": graph_state.get("diagnostics_refs"),
            "experiment_preview": graph_state.get("experiment_preview"),
            "validation_outcome": val,
            "committed_result": graph_state.get("committed_result"),
            "selected_scene_function": graph_state.get("selected_scene_function"),
            "self_correction": self_correction,
            "runtime_governance_surface": gov,
        }
        committed_record = {
            "turn_number": commit_turn_number,
            "turn_kind": turn_kind or "player",
            "trace_id": trace_id or "",
            "turn_outcome": outcome,
            "narrative_commit": narrative_commit_payload,
            "committed_state_after": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
            },
        }
        session.history.append(committed_record)
        session.diagnostics.append(event)
        self._persist_session(session)
        return event

    def _execute_opening_locked(self, session_id: str, trace_id: str | None) -> dict[str, Any]:
        session = self.get_session(session_id)
        prompt = self._build_opening_prompt(session)
        prior_scene_id = session.current_scene_id
        history_tail = session.history[-(NARRATIVE_COMMIT_HISTORY_TAIL - 1) :]
        graph_threads, graph_summary = build_graph_thread_export(session.narrative_threads)
        host_experience_template = (
            goc_host_experience_template(session.runtime_projection)
            if session.module_id == "god_of_carnage"
            else None
        )
        prior_ci = goc_prior_continuity_for_graph(session.module_id, session.prior_continuity_impacts)
        try:
            graph_state = self.turn_graph.run(
                session_id=session.session_id,
                module_id=session.module_id,
                current_scene_id=session.current_scene_id,
                player_input=prompt,
                trace_id=trace_id,
                host_versions={"world_engine_app_version": APP_VERSION},
                active_narrative_threads=graph_threads or None,
                thread_pressure_summary=graph_summary,
                host_experience_template=host_experience_template,
                prior_continuity_impacts=prior_ci if prior_ci else None,
                turn_number=0,
                turn_initiator_type="engine",
                turn_input_class="opening",
                live_player_truth_surface=True,
            )
        except Exception as exc:
            log_story_runtime_failure(
                trace_id=trace_id,
                story_session_id=session_id,
                operation="execute_opening",
                message=str(exc),
                failure_class="graph_execution_exception",
            )
            raise
        if not self._opening_commit_acceptable(graph_state):
            if is_hard_boundary_failure(graph_state.get("validation_outcome")):
                raise RuntimeError("Opening blocked by hard narrative boundary")
            raise RuntimeError("Opening validation did not approve committed narration")
        if not self._visible_narration_present(graph_state):
            raise RuntimeError("Opening produced no visible narration")
        session.updated_at = datetime.now(timezone.utc)
        return self._finalize_committed_turn(
            session=session,
            graph_state=graph_state,
            trace_id=trace_id,
            commit_turn_number=0,
            player_input=prompt,
            turn_kind="opening",
            prior_scene_id=prior_scene_id,
            history_tail=history_tail,
            graph_threads=graph_threads,
            graph_summary=graph_summary,
            host_experience_template=host_experience_template,
            prior_ci=prior_ci,
        )

    def create_session(
        self,
        *,
        module_id: str,
        runtime_projection: dict[str, Any],
        content_provenance: dict[str, Any] | None = None,
    ) -> StorySession:
        session_id = uuid4().hex
        current_scene_id = str(runtime_projection.get("start_scene_id") or "")
        prov = dict(content_provenance) if isinstance(content_provenance, dict) else {}
        if not prov:
            mid = runtime_projection.get("module_id")
            ver = runtime_projection.get("module_version")
            if isinstance(mid, str) and mid.strip():
                prov.setdefault("runtime_projection_module_id", mid.strip())
            if isinstance(ver, str) and ver.strip():
                prov.setdefault("runtime_projection_module_version", ver.strip())
        session = StorySession(
            session_id=session_id,
            module_id=module_id,
            runtime_projection=runtime_projection,
            current_scene_id=current_scene_id,
            content_provenance=prov,
        )
        self.sessions[session_id] = session
        with self._session_locks_guard:
            self._session_turn_locks.setdefault(session_id, threading.Lock())
        self._persist_session(session)
        if self._skip_graph_opening_on_create:
            return session
        self._assert_live_player_governance()
        attempts = self._opening_retry_count() + 1
        last_exc: BaseException | None = None
        for attempt in range(1, attempts + 1):
            try:
                with self._session_turn_lock(session_id):
                    self._execute_opening_locked(session_id, trace_id=None)
                self.metrics.incr("story_opening_success", module_id=module_id, session_id=session_id, attempt=attempt)
                return session
            except BaseException as exc:
                last_exc = exc
                self.metrics.incr(
                    "story_opening_retry",
                    module_id=module_id,
                    session_id=session_id,
                    attempt=attempt,
                    error=str(exc)[:300],
                )
        self.sessions.pop(session_id, None)
        if self._session_store is not None:
            try:
                self._session_store.delete(session_id)
            except Exception:
                pass
        log_story_runtime_failure(
            trace_id=None,
            story_session_id=session_id,
            operation="create_session_opening",
            message=str(last_exc)[:500] if last_exc else "opening_failed",
            failure_class="opening_generation_failed",
        )
        raise RuntimeError(f"Opening generation failed for module {module_id}: {last_exc}") from last_exc

    def execute_turn(self, *, session_id: str, player_input: str, trace_id: str | None = None) -> dict[str, Any]:
        with self._session_turn_lock(session_id):
            return self._execute_turn_locked(
                session_id=session_id, player_input=player_input, trace_id=trace_id
            )

    def _execute_turn_locked(self, *, session_id: str, player_input: str, trace_id: str | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        self._assert_live_player_governance()
        session.turn_counter += 1
        session.updated_at = datetime.now(timezone.utc)
        commit_turn_number = session.turn_counter
        prior_scene_id = session.current_scene_id
        history_tail = session.history[-(NARRATIVE_COMMIT_HISTORY_TAIL - 1) :]
        graph_threads, graph_summary = build_graph_thread_export(session.narrative_threads)
        host_experience_template = (
            goc_host_experience_template(session.runtime_projection)
            if session.module_id == "god_of_carnage"
            else None
        )
        try:
            prior_ci = goc_prior_continuity_for_graph(session.module_id, session.prior_continuity_impacts)
            graph_state = self.turn_graph.run(
                session_id=session.session_id,
                module_id=session.module_id,
                current_scene_id=session.current_scene_id,
                player_input=player_input,
                trace_id=trace_id,
                host_versions={"world_engine_app_version": APP_VERSION},
                active_narrative_threads=graph_threads or None,
                thread_pressure_summary=graph_summary,
                host_experience_template=host_experience_template,
                prior_continuity_impacts=prior_ci if prior_ci else None,
                turn_number=commit_turn_number,
                turn_initiator_type="player",
                live_player_truth_surface=True,
            )
        except Exception as exc:
            session.turn_counter -= 1
            log_story_runtime_failure(
                trace_id=trace_id,
                story_session_id=session_id,
                operation="execute_turn",
                message=str(exc),
                failure_class="graph_execution_exception",
            )
            raise

        val = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
        if val.get("status") != "approved":
            session.turn_counter -= 1
            if is_hard_boundary_failure(val):
                raise RuntimeError(f"Hard narrative boundary: {val.get('reason') or 'rejected'}")
            raise RuntimeError(f"Turn rejected after bounded recovery: {val.get('reason') or 'rejected'}")
        return self._finalize_committed_turn(
            session=session,
            graph_state=graph_state,
            trace_id=trace_id,
            commit_turn_number=commit_turn_number,
            player_input=player_input,
            turn_kind="player",
            prior_scene_id=prior_scene_id,
            history_tail=history_tail,
            graph_threads=graph_threads,
            graph_summary=graph_summary,
            host_experience_template=host_experience_template,
            prior_ci=prior_ci,
        )

    def get_session(self, session_id: str) -> StorySession:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def list_session_summaries(self) -> list[dict[str, Any]]:
        """Lightweight rows for admin/ops consoles (no full history or diagnostics)."""
        rows: list[dict[str, Any]] = []
        for sid, session in self.sessions.items():
            rows.append(
                {
                    "session_id": sid,
                    "module_id": session.module_id,
                    "turn_counter": session.turn_counter,
                    "current_scene_id": session.current_scene_id,
                    "content_provenance": session.content_provenance,
                    "updated_at": session.updated_at.isoformat(),
                    "created_at": session.created_at.isoformat(),
                }
            )
        rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
        return rows

    def get_state(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        last_narrative_commit: dict[str, Any] | None = None
        last_committed_turn = session.history[-1] if session.history else None
        if isinstance(last_committed_turn, dict):
            nc = last_committed_turn.get("narrative_commit")
            if isinstance(nc, dict):
                last_narrative_commit = nc

        summary: dict[str, Any] | None = None
        if isinstance(last_narrative_commit, dict):
            summary = {
                "situation_status": last_narrative_commit.get("situation_status"),
                "allowed": last_narrative_commit.get("allowed"),
                "commit_reason_code": last_narrative_commit.get("commit_reason_code"),
                "committed_scene_id": last_narrative_commit.get("committed_scene_id"),
                "proposed_scene_id": last_narrative_commit.get("proposed_scene_id"),
                "selected_candidate_source": last_narrative_commit.get("selected_candidate_source"),
                "is_terminal": last_narrative_commit.get("is_terminal"),
            }

        last_consequences: list[str] = []
        last_open_pressures: list[str] = []
        if isinstance(last_narrative_commit, dict):
            lc = last_narrative_commit.get("committed_consequences")
            if isinstance(lc, list):
                last_consequences = [str(x) for x in lc]
            op = last_narrative_commit.get("open_pressures")
            if isinstance(op, list):
                last_open_pressures = [str(x) for x in op]

        thread_metrics = thread_continuity_metrics(session.narrative_threads)
        last_thread_summary: str | None = None
        if session.last_thread_update_trace is not None:
            last_thread_summary = session.last_thread_update_trace.summary or None

        story_entries = _story_window_entries_for_session(session)

        return {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "current_scene_id": session.current_scene_id,
            "content_provenance": session.content_provenance,
            "runtime_projection": session.runtime_projection,
            "history_count": len(session.history),
            "committed_state": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "last_narrative_commit": last_narrative_commit,
                "last_narrative_commit_summary": summary,
                "last_committed_consequences": last_consequences,
                "last_open_pressures": last_open_pressures,
                "narrative_thread_continuity": {
                    "narrative_threads": session.narrative_threads.model_dump(mode="json"),
                    "active_narrative_threads": [
                        t.model_dump(mode="json")
                        for t in session.narrative_threads.active
                        if t.status != "resolved"
                    ],
                    "thread_count": thread_metrics["thread_count"],
                    "dominant_thread_kind": thread_metrics["dominant_thread_kind"],
                    "thread_pressure_level": thread_metrics["thread_pressure_level"],
                    "last_narrative_thread_update_summary": last_thread_summary,
                },
            },
            "story_window": {
                "contract": "authoritative_story_window_v1",
                "source": "world_engine_story_runtime",
                "entries": story_entries,
                "entry_count": len(story_entries),
                "latest_entry": story_entries[-1] if story_entries else None,
            },
            "last_committed_turn": last_committed_turn,
            "updated_at": session.updated_at.isoformat(),
        }

    def get_diagnostics(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        committed_state = {
            "current_scene_id": session.current_scene_id,
            "turn_counter": session.turn_counter,
        }
        trace_payload: dict[str, Any] | None = None
        if session.last_thread_update_trace is not None:
            trace_payload = session.last_thread_update_trace.model_dump(mode="json")

        return {
            "session_id": session.session_id,
            "turn_counter": session.turn_counter,
            "runtime_config_status": self.runtime_config_status(),
            "committed_state": committed_state,
            "diagnostics": session.diagnostics[-20:],
            "envelope_kind": "full_turn_orchestration_includes_graph_retrieval_and_interpreted_input",
            "committed_truth_vs_diagnostics": (
                "Each diagnostics[] entry is a full orchestration envelope (graph, retrieval, model_route, "
                "interpreted_input). Authoritative committed story-runtime truth is session fields, "
                "history, and the bounded narrative_commit object (also embedded in each envelope for correlation). "
                "Narrative thread continuity lives in session.narrative_threads and get_state committed_state "
                "narrative_thread_continuity; narrative_thread_diagnostics.last_update_trace is bounded operator "
                "reasoning only and is not an authority source."
            ),
            "authoritative_history_tail": session.history[-5:] if session.history else [],
            "narrative_thread_diagnostics": {
                "last_update_trace": trace_payload,
                "note": (
                    "Diagnostic trace for the latest thread update only; authoritative continuity is "
                    "get_state.committed_state.narrative_thread_continuity and session.narrative_threads."
                ),
            },
            "warnings": [
                "story_runtime_hosted_in_world_engine",
                "ai_proposals_require_authoritative_runtime_commit",
                "orchestration_lives_in_diagnostics_bounded_truth_lives_in_narrative_commit_and_history",
            ],
        }
