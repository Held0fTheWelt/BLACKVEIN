"""Manager initialization and persistence.

Initializes runtime manager storage, session indexes, and persistence surfaces used across turn execution.
"""
from __future__ import annotations

from .._deps import *

class _ManagerInitAndPersistenceMixin:
    def __init__(
        self,
        *,
        registry: ModelRegistry | None = None,
        adapters: dict[str, BaseModelAdapter] | None = None,
        retriever: Any | None = None,
        context_assembler: Any | None = None,
        session_store: JsonStorySessionStore | None = None,
        branching_tree_store: JsonBranchingTreeStore | None = None,
        branch_timeline_store: JsonBranchTimelineStore | None = None,
        callback_web_store: JsonCallbackWebStore | None = None,
        consequence_cascade_store: JsonConsequenceCascadeStore | None = None,
        governed_runtime_config: dict[str, Any] | None = None,
        metrics: StoryRuntimeMetrics | None = None,
    ) -> None:
        self.sessions: dict[str, StorySession] = {}
        self._session_store = session_store
        self._branching_tree_store = branching_tree_store
        self._branch_timeline_store = branch_timeline_store
        self._callback_web_store = callback_web_store
        self._consequence_cascade_store = consequence_cascade_store
        self._branching_trees: dict[str, dict[str, Any]] = {}
        self._branch_timelines: dict[str, dict[str, Any]] = {}
        self._callback_webs: dict[str, dict[str, Any]] = {}
        self._consequence_cascades: dict[str, dict[str, Any]] = {}
        self._branching_simulation_session_ids: set[str] = set()
        self._session_turn_locks: dict[str, threading.Lock] = {}
        self._session_locks_guard = threading.Lock()
        self.repo_root = resolve_wos_repo_root(start=Path(__file__).resolve().parent)
        self.metrics = metrics or StoryRuntimeMetrics()
        self._governed_runtime_config: dict[str, Any] | None = None
        # ``_authority_version`` increments every time runtime components are
        # (re)applied — on initial construction and on ``reload_runtime_config``.
        # Each committed turn records the authority version it ran under, so
        # operators can prove that reload / promotion / rollback actually
        # reached the live turn path rather than merely refreshing loader state.
        self._authority_version: int = 0
        self._authority_applied_at_iso: str | None = None
        self._runtime_config_status: dict[str, Any] = {
            "source": "default_registry",
            "config_version": None,
            "last_reload_ok": None,
            "route_count": 0,
            "model_count": 0,
            "live_execution_blocked": False,
        }
        self.turn_graph: RuntimeTurnGraphExecutor | None = None
        configure_prompt_bundle(
            (governed_runtime_config or {}).get("prompt_store")
            if isinstance(governed_runtime_config, dict)
            else None
        )
        # MVP3: Narrative agent orchestration (streaming narrator blocks)
        self.narrative_agents: dict[str, NarrativeRuntimeAgent] = {}
        self.input_queues: dict[str, list[str]] = {}  # session_id -> list of queued player inputs
        self._narrative_streaming_active: dict[str, bool] = {}  # session_id -> is narrator streaming?
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
            elif governed_runtime_config is None:
                self.registry = build_default_registry()
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
            else:
                self._governed_runtime_config = (
                    dict(governed_runtime_config) if isinstance(governed_runtime_config, dict) else None
                )
                # Escape hatch removed: always fail-closed when config is invalid/missing
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
        # Record the initial authority binding that will shape the first live turn.
        self._bump_authority_version()
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
        # Injected adapters imply an isolated test or custom stack that expects
        # the full retrieve→model path (e.g. RAG + CaptureAdapter). Production
        # sessions use governed components only (adapters parameter None).
        self._action_resolution_short_path_enabled = adapters is None
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
        if self._branching_tree_store is not None:
            for tree_id, raw in self._branching_tree_store.load_all_raw().items():
                if isinstance(raw, dict):
                    self._branching_trees[tree_id] = raw
        if self._branch_timeline_store is not None:
            for timeline_id, raw in self._branch_timeline_store.load_all_raw().items():
                if isinstance(raw, dict):
                    self._branch_timelines[timeline_id] = raw
        if self._callback_web_store is not None:
            for callback_web_id, raw in self._callback_web_store.load_all_raw().items():
                if isinstance(raw, dict):
                    self._callback_webs[callback_web_id] = raw
        if self._consequence_cascade_store is not None:
            for cascade_id, raw in self._consequence_cascade_store.load_all_raw().items():
                if isinstance(raw, dict):
                    self._consequence_cascades[cascade_id] = raw

    def _session_turn_lock(self, session_id: str) -> threading.Lock:
        with self._session_locks_guard:
            return self._session_turn_locks.setdefault(session_id, threading.Lock())

    def _persist_session(self, session: StorySession) -> None:
        if session.session_id in self._branching_simulation_session_ids:
            return
        if self._session_store is None:
            return
        self._session_store.save(session.session_id, story_session_to_payload(session))

    def _persist_branching_tree_record(self, record: dict[str, Any]) -> dict[str, Any]:
        tree_id = str(record.get("tree_id") or "").strip()
        if not tree_id:
            raise ValueError("branching_tree_missing_id")
        self._branching_trees[tree_id] = copy.deepcopy(record)
        if self._branching_tree_store is not None:
            self._branching_tree_store.save(tree_id, record)
        return copy.deepcopy(record)

    def _persist_branch_timeline_record(self, record: dict[str, Any]) -> dict[str, Any]:
        timeline_id = str(record.get("timeline_id") or "").strip()
        if not timeline_id:
            raise ValueError("branch_timeline_missing_id")
        self._branch_timelines[timeline_id] = copy.deepcopy(record)
        if self._branch_timeline_store is not None:
            self._branch_timeline_store.save(timeline_id, record)
        return copy.deepcopy(record)

    def _persist_callback_web_record(self, record: dict[str, Any]) -> dict[str, Any]:
        callback_web_id = str(record.get("callback_web_id") or "").strip()
        if not callback_web_id:
            raise ValueError("callback_web_missing_id")
        self._callback_webs[callback_web_id] = copy.deepcopy(record)
        if self._callback_web_store is not None:
            self._callback_web_store.save(callback_web_id, record)
        return copy.deepcopy(record)

    def _persist_consequence_cascade_record(self, record: dict[str, Any]) -> dict[str, Any]:
        cascade_id = str(record.get("cascade_id") or "").strip()
        if not cascade_id:
            raise ValueError("consequence_cascade_missing_id")
        self._consequence_cascades[cascade_id] = copy.deepcopy(record)
        sid = str(record.get("story_session_id") or "").strip()
        if sid in self._branching_simulation_session_ids:
            return copy.deepcopy(record)
        if self._consequence_cascade_store is not None:
            self._consequence_cascade_store.save(cascade_id, record)
        return copy.deepcopy(record)

    def _get_tracing_config(self, session_id: str) -> bool:
        """Get Langfuse tracing readiness from the runtime adapter."""
        try:
            return LangfuseAdapter.get_instance().is_enabled()
        except Exception:
            logger.debug("Langfuse tracing config unavailable for session %s", session_id, exc_info=True)
            return False

    def queue_player_input(self, session_id: str, player_input: str) -> None:
        """Queue player input while narrator is streaming."""
        if session_id not in self.input_queues:
            self.input_queues[session_id] = []
        self.input_queues[session_id].append(player_input)

    def get_queued_inputs(self, session_id: str) -> list[str]:
        """Get and clear queued player inputs after ruhepunkt signal."""
        queue = self.input_queues.get(session_id, [])
        if queue:
            self.input_queues[session_id] = []
        return queue

    def is_narrative_streaming(self, session_id: str) -> bool:
        """Check if narrator is currently streaming for session."""
        return self._narrative_streaming_active.get(session_id, False)

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


__all__ = ["_ManagerInitAndPersistenceMixin"]
