from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from story_runtime_core import ModelRegistry, RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, build_default_model_adapters
from story_runtime_core.model_registry import build_default_registry
from ai_stack import build_runtime_retriever, create_default_capability_registry

try:
    from ai_stack import RuntimeTurnGraphExecutor
except ImportError:  # pragma: no cover - exercised indirectly in minimal test environments
    RuntimeTurnGraphExecutor = None  # type: ignore[assignment]

from app.config import APP_VERSION
from app.observability.audit_log import log_story_runtime_failure, log_story_turn_event
from app.story_runtime.commit_models import resolve_narrative_commit
from app.story_runtime.narrative_threads import (
    NARRATIVE_COMMIT_HISTORY_TAIL,
    StoryNarrativeThreadSet,
    ThreadUpdateTrace,
    build_graph_thread_export,
    thread_continuity_metrics,
    update_narrative_threads,
)
from app.story_runtime_shell_readout import build_story_runtime_shell_readout, frame_story_runtime_visible_output_bundle



class _UnavailableRuntimeTurnGraphExecutor:
    def run(self, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError(
            "RuntimeTurnGraphExecutor is unavailable because optional ai_stack runtime dependencies are missing. "
            "Inject a test double or install the full ai_stack runtime dependencies."
        )


def _extract_first_addressed_line(bundle: dict[str, Any] | None) -> str | None:
    if not isinstance(bundle, dict):
        return None
    for key in ("gm_narration", "spoken_lines"):
        lines = bundle.get(key)
        if isinstance(lines, list):
            for item in lines:
                if isinstance(item, str) and item.strip():
                    return item.strip()
    return None


def _reply_continuity_context_from_turn(turn_record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(turn_record, dict):
        return None
    after = turn_record.get("committed_state_after")
    if isinstance(after, dict):
        ctx = after.get("reply_continuity_context")
        if isinstance(ctx, dict):
            return ctx
    return None


def _stored_previous_reply_context_from_turn(turn_record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(turn_record, dict):
        return None
    after = turn_record.get("committed_state_after")
    if isinstance(after, dict):
        ctx = after.get("previous_reply_continuity_context")
        if isinstance(ctx, dict):
            return ctx
    return None


def _stored_earlier_reply_context_from_turn(turn_record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(turn_record, dict):
        return None
    after = turn_record.get("committed_state_after")
    if isinstance(after, dict):
        ctx = after.get("earlier_reply_continuity_context")
        if isinstance(ctx, dict):
            return ctx
    return None


def _first_responder_actor_for_event(selected_responder_set: Any) -> str | None:
    if isinstance(selected_responder_set, list) and selected_responder_set and isinstance(selected_responder_set[0], dict):
        actor = selected_responder_set[0].get("actor_id")
        if isinstance(actor, str) and actor.strip():
            return actor.strip()
    return None


def _surface_token_from_projection(projection: dict[str, Any]) -> str:
    live_surface = str(projection.get("live_surface_now") or "").lower()
    if "doorway" in live_surface or "threshold" in live_surface:
        return "doorway"
    if "bathroom edge" in live_surface:
        return "bathroom edge"
    if "books" in live_surface:
        return "books"
    if "flowers" in live_surface:
        return "flowers"
    if "phone" in live_surface:
        return "phone"
    if "hosting surface" in live_surface:
        return "hosting surface"
    return "room"


def _build_reply_continuity_context(*, shell_readout_projection: dict[str, Any] | None, addressed_visible_output_bundle: dict[str, Any] | None, responder_actor: str | None) -> dict[str, Any]:
    projection = shell_readout_projection if isinstance(shell_readout_projection, dict) else {}
    return {
        "exchange_label": str(projection.get("response_exchange_label_now") or "").strip(),
        "surface_token": _surface_token_from_projection(projection),
        "response_line_prefix": str(projection.get("response_line_prefix_now") or "").strip(),
        "response_recentering": str(projection.get("response_recentering_now") or "").strip(),
        "responder_actor": (responder_actor or "").strip().lower(),
        "addressed_line": _extract_first_addressed_line(addressed_visible_output_bundle) or "",
    }


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
        if RuntimeTurnGraphExecutor is None:
            self.turn_graph = _UnavailableRuntimeTurnGraphExecutor()
        else:
            self.turn_graph = RuntimeTurnGraphExecutor(
                interpreter=interpret_player_input,
                routing=self.routing,
                registry=self.registry,
                adapters=self.adapters,
                retriever=self.retriever,
                assembler=self.context_assembler,
                capability_registry=self.capability_registry,
            )

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
        prior_scene_id = session.current_scene_id
        history_tail = session.history[-(NARRATIVE_COMMIT_HISTORY_TAIL - 1) :]
        prior_reply_context = _reply_continuity_context_from_turn(session.history[-1] if session.history else None)
        earlier_reply_context = _stored_previous_reply_context_from_turn(session.history[-1] if session.history else None)
        graph_threads, graph_summary = build_graph_thread_export(session.narrative_threads)
        host_experience_template: dict[str, Any] | None = None
        if session.module_id == "god_of_carnage":
            rp = session.runtime_projection
            if isinstance(rp, dict):
                tid = rp.get("experience_template_id") or rp.get("seed_template_id")
                tit = rp.get("experience_template_title")
                if tid is not None or tit is not None:
                    host_experience_template = {
                        "template_id": str(tid) if tid is not None else None,
                        "title": str(tit) if tit is not None else None,
                    }
        try:
            prior_ci = session.prior_continuity_impacts if session.module_id == "god_of_carnage" else None
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

        if session.module_id == "god_of_carnage":
            ci = graph_state.get("continuity_impacts")
            if isinstance(ci, list):
                for item in ci:
                    if isinstance(item, dict):
                        session.prior_continuity_impacts.append(item)
                session.prior_continuity_impacts = session.prior_continuity_impacts[-12:]

        graph_diag = graph_state.get("graph_diagnostics", {}) if isinstance(graph_state.get("graph_diagnostics"), dict) else {}
        errors = graph_diag.get("errors", []) if isinstance(graph_diag.get("errors"), list) else []
        gen = graph_state.get("generation", {}) if isinstance(graph_state.get("generation"), dict) else {}
        interpreted_input = graph_state.get("interpreted_input", {})
        if not isinstance(interpreted_input, dict):
            interpreted_input = {}

        narrative_commit = resolve_narrative_commit(
            turn_number=session.turn_counter,
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
            turn_number=session.turn_counter,
        )

        thread_metrics = thread_continuity_metrics(session.narrative_threads)
        last_thread_summary: str | None = None
        if session.last_thread_update_trace is not None:
            last_thread_summary = session.last_thread_update_trace.summary or None

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

        narrative_commit_payload = narrative_commit.model_dump(mode="json")
        preview_state = {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "current_scene_id": session.current_scene_id,
            "runtime_projection": session.runtime_projection,
            "history_count": len(session.history),
            "committed_state": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "last_narrative_commit": narrative_commit_payload,
                "last_narrative_commit_summary": {
                    "situation_status": narrative_commit_payload.get("situation_status"),
                    "allowed": narrative_commit_payload.get("allowed"),
                    "commit_reason_code": narrative_commit_payload.get("commit_reason_code"),
                    "committed_scene_id": narrative_commit_payload.get("committed_scene_id"),
                    "proposed_scene_id": narrative_commit_payload.get("proposed_scene_id"),
                    "selected_candidate_source": narrative_commit_payload.get("selected_candidate_source"),
                    "is_terminal": narrative_commit_payload.get("is_terminal"),
                },
                "last_committed_consequences": [str(x) for x in (narrative_commit_payload.get("committed_consequences") or [])],
                "last_open_pressures": [str(x) for x in (narrative_commit_payload.get("open_pressures") or [])],
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
                "previous_reply_continuity_context": prior_reply_context,
                "earlier_reply_continuity_context": earlier_reply_context,
            },
            "updated_at": session.updated_at.isoformat(),
        }
        shell_readout_projection = build_story_runtime_shell_readout(
            state=preview_state,
            last_diagnostic={
                "selected_scene_function": graph_state.get("selected_scene_function"),
                "selected_responder_set": graph_state.get("selected_responder_set"),
                "social_state_record": graph_state.get("social_state_record"),
            },
        )
        addressed_visible_output_bundle = frame_story_runtime_visible_output_bundle(
            visible_output_bundle=graph_state.get("visible_output_bundle") if isinstance(graph_state.get("visible_output_bundle"), dict) else None,
            shell_readout_projection=shell_readout_projection,
        )
        reply_continuity_context = _build_reply_continuity_context(
            shell_readout_projection=shell_readout_projection,
            addressed_visible_output_bundle=addressed_visible_output_bundle,
            responder_actor=_first_responder_actor_for_event(graph_state.get("selected_responder_set")),
        )
        event = {
            "turn_number": session.turn_counter,
            "trace_id": trace_id or "",
            "raw_input": player_input,
            "interpreted_input": interpreted_input,
            "narrative_commit": narrative_commit_payload,
            "retrieval": graph_state.get("retrieval", {}),
            "model_route": {
                **graph_state.get("routing", {}),
                "generation": graph_state.get("generation", {}),
            },
            "graph": graph_state.get("graph_diagnostics", {}),
            "visible_output_bundle": graph_state.get("visible_output_bundle"),
            "visible_output_bundle_addressed": addressed_visible_output_bundle,
            "shell_readout_projection": shell_readout_projection,
            "diagnostics_refs": graph_state.get("diagnostics_refs"),
            "experiment_preview": graph_state.get("experiment_preview"),
            "validation_outcome": graph_state.get("validation_outcome"),
            "committed_result": graph_state.get("committed_result"),
            "selected_scene_function": graph_state.get("selected_scene_function"),
            "selected_responder_set": graph_state.get("selected_responder_set"),
            "social_state_record": graph_state.get("social_state_record"),
        }
        committed_record = {
            "turn_number": session.turn_counter,
            "trace_id": trace_id or "",
            "turn_outcome": outcome,
            "narrative_commit": narrative_commit_payload,
            "committed_state_after": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "previous_reply_continuity_context": prior_reply_context,
                "earlier_reply_continuity_context": earlier_reply_context,
                "reply_continuity_context": reply_continuity_context,
            },
        }
        session.history.append(committed_record)
        session.diagnostics.append(event)
        return event

    def get_session(self, session_id: str) -> StorySession:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

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

        state_payload = {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "current_scene_id": session.current_scene_id,
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
                "previous_reply_continuity_context": _stored_previous_reply_context_from_turn(last_committed_turn),
                "earlier_reply_continuity_context": _stored_earlier_reply_context_from_turn(last_committed_turn),
                "reply_continuity_context": (last_committed_turn.get("committed_state_after", {}) or {}).get("reply_continuity_context") if isinstance(last_committed_turn, dict) else None,
            },
            "last_committed_turn": last_committed_turn,
            "updated_at": session.updated_at.isoformat(),
        }
        last_diagnostic = session.diagnostics[-1] if session.diagnostics else None
        shell_readout_projection = build_story_runtime_shell_readout(state=state_payload, last_diagnostic=last_diagnostic if isinstance(last_diagnostic, dict) else None)
        state_payload["committed_state"]["shell_readout_projection"] = shell_readout_projection
        state_payload["shell_readout_projection"] = shell_readout_projection
        return state_payload

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
