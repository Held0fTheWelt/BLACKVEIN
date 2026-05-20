from __future__ import annotations

from ._deps import *
from .actor_tracking.session_state_w5_view import _maybe_build_w5_player_view_for_session


class _SessionStateApiMixin:
    def get_state(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        last_narrative_commit: dict[str, Any] | None = None
        last_committed_turn_authority: dict[str, Any] | None = None
        last_dramatic_context_summary: dict[str, Any] | None = None
        last_actor_turn_summary: dict[str, Any] | None = None
        last_branching_forecast: dict[str, Any] | None = None
        last_committed_turn = session.history[-1] if session.history else None
        if isinstance(last_committed_turn, dict):
            nc = last_committed_turn.get("narrative_commit")
            if isinstance(nc, dict):
                last_narrative_commit = nc
            authority = last_committed_turn.get("committed_turn_authority")
            if isinstance(authority, dict):
                last_committed_turn_authority = authority
            dramatic_context = last_committed_turn.get("dramatic_context_summary")
            if isinstance(dramatic_context, dict):
                last_dramatic_context_summary = dramatic_context
            actor_summary = last_committed_turn.get("actor_turn_summary")
            if isinstance(actor_summary, dict):
                last_actor_turn_summary = actor_summary
            branching = last_committed_turn.get("branching_forecast")
            if not isinstance(branching, dict):
                ledger = last_committed_turn.get("turn_aspect_ledger")
                if isinstance(ledger, dict):
                    branching = ledger.get("branching_forecast")
            if isinstance(branching, dict):
                last_branching_forecast = branching

        summary: dict[str, Any] | None = None
        if isinstance(last_narrative_commit, dict):
            planner_truth = (
                last_narrative_commit.get("planner_truth")
                if isinstance(last_narrative_commit.get("planner_truth"), dict)
                else {}
            )
            if not last_actor_turn_summary and planner_truth:
                last_actor_turn_summary = {
                    "contract": "actor_turn_summary.v1",
                    "primary_responder_id": planner_truth.get("primary_responder_id")
                    or planner_truth.get("responder_id"),
                    "secondary_responder_ids": planner_truth.get("secondary_responder_ids") or [],
                    "spoken_line_count": planner_truth.get("spoken_line_count") or 0,
                    "action_line_count": planner_truth.get("action_line_count") or 0,
                    "initiative_summary": planner_truth.get("initiative_summary") or {},
                    "last_actor_outcome_summary": planner_truth.get("last_actor_outcome_summary"),
                }
            summary = {
                "situation_status": last_narrative_commit.get("situation_status"),
                "allowed": last_narrative_commit.get("allowed"),
                "commit_reason_code": last_narrative_commit.get("commit_reason_code"),
                "committed_scene_id": last_narrative_commit.get("committed_scene_id"),
                "proposed_scene_id": last_narrative_commit.get("proposed_scene_id"),
                "selected_candidate_source": last_narrative_commit.get("selected_candidate_source"),
                "is_terminal": last_narrative_commit.get("is_terminal"),
                "primary_responder_id": (
                    (last_actor_turn_summary or {}).get("primary_responder_id")
                    if isinstance(last_actor_turn_summary, dict)
                    else None
                ),
                "spoken_line_count": (
                    (last_actor_turn_summary or {}).get("spoken_line_count")
                    if isinstance(last_actor_turn_summary, dict)
                    else 0
                ),
                "action_line_count": (
                    (last_actor_turn_summary or {}).get("action_line_count")
                    if isinstance(last_actor_turn_summary, dict)
                    else 0
                ),
                "initiative_summary": (
                    (last_actor_turn_summary or {}).get("initiative_summary")
                    if isinstance(last_actor_turn_summary, dict)
                    else {}
                ),
                "last_actor_outcome_summary": (
                    (last_actor_turn_summary or {}).get("last_actor_outcome_summary")
                    if isinstance(last_actor_turn_summary, dict)
                    else None
                ),
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
        module_scope_truth = _module_scope_truth(session.module_id)
        _, memory_policy = _load_module_memory_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        hierarchical_memory_context = project_hierarchical_memory_context(
            snapshot=session.hierarchical_memory
            if isinstance(session.hierarchical_memory, dict)
            else None,
            memory_policy=memory_policy,
        )
        last_thread_summary: str | None = None
        if session.last_thread_update_trace is not None:
            last_thread_summary = session.last_thread_update_trace.summary or None

        story_entries = _story_window_entries_for_session(session)
        runtime_world = session.runtime_world if isinstance(session.runtime_world, dict) else {}
        runtime_world_summary = self._runtime_world_summary(runtime_world)
        session_loop = {
            "status": "runtime_engine_initialized" if runtime_world.get("status") == "initialized" else "runtime_engine_uninitialized",
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "current_scene_id": session.current_scene_id,
            "history_len": len(session.history),
            "diagnostics_len": len(session.diagnostics),
            "runtime_world": runtime_world_summary,
        }
        player_shell_context = _player_shell_context_from_dramatic_context(
            last_dramatic_context_summary,
            session=session,
        )
        w5_player_view, w5_player_view_diagnostics = _maybe_build_w5_player_view_for_session(session)
        history_rows = session.history or []
        committed_canonical_turn_count = len(history_rows)
        opening_committed = any(
            isinstance(h, dict) and str(h.get("turn_kind") or "") == "opening" for h in history_rows
        )
        player_committed_turns = sum(
            1
            for h in history_rows
            if isinstance(h, dict) and str(h.get("turn_kind") or "") != "opening"
        )
        total_canonical_turns = committed_canonical_turn_count
        last_hist = history_rows[-1] if history_rows else None
        latest_canonical_turn_id: str | None = None
        if isinstance(last_hist, dict):
            lid = str(last_hist.get("canonical_turn_id") or "").strip()
            latest_canonical_turn_id = lid or None
        callback_web_snapshot: dict[str, Any] | None = None
        try:
            callback_web = self.get_callback_web(session_id=session.session_id)
            snapshot = callback_web.get("snapshot") if isinstance(callback_web.get("snapshot"), dict) else {}
            callback_web_snapshot = copy.deepcopy(snapshot)
        except Exception:
            callback_web_snapshot = None
        consequence_cascade_snapshot: dict[str, Any] | None = None
        try:
            cascade = self.get_consequence_cascade(session_id=session.session_id)
            snapshot = cascade.get("snapshot") if isinstance(cascade.get("snapshot"), dict) else {}
            consequence_cascade_snapshot = copy.deepcopy(snapshot)
        except Exception:
            consequence_cascade_snapshot = None

        return {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "committed_canonical_turn_count": committed_canonical_turn_count,
            "opening_committed": opening_committed,
            "player_committed_turns": player_committed_turns,
            "total_canonical_turns": total_canonical_turns,
            "canonical_turn_count": total_canonical_turns,
            "latest_canonical_turn_id": latest_canonical_turn_id,
            "current_scene_id": session.current_scene_id,
            "content_provenance": session.content_provenance,
            "runtime_projection": session.runtime_projection,
            "runtime_world": runtime_world,
            "session_loop": session_loop,
            **(
                {
                    "w5_player_view": w5_player_view,
                    "w5_player_view_diagnostics": w5_player_view_diagnostics,
                    "feature_flags": {
                        "W5_AST_FRONTEND_PLAYER_VIEW_ENABLED": True,
                    },
                }
                if w5_player_view_diagnostics is not None
                else {}
            ),
            "history_count": len(history_rows),
            "committed_state": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "environment_state": session.environment_state
                if isinstance(session.environment_state, dict)
                else {},
                "last_narrative_commit": last_narrative_commit,
                "last_committed_turn_authority": last_committed_turn_authority,
                "last_dramatic_context_summary": last_dramatic_context_summary,
                "last_actor_turn_summary": last_actor_turn_summary,
                "last_branching_forecast": last_branching_forecast,
                "callback_web": callback_web_snapshot,
                "callback_web_continuity": callback_web_snapshot,
                "consequence_cascade": consequence_cascade_snapshot,
                "last_actor_outcome_summary": (
                    last_actor_turn_summary.get("last_actor_outcome_summary")
                    if isinstance(last_actor_turn_summary, dict)
                    else None
                ),
                "player_shell_context": player_shell_context,
                "module_scope_truth": module_scope_truth,
                **(
                    {
                        "w5_player_view": w5_player_view,
                        "w5_player_view_diagnostics": w5_player_view_diagnostics,
                    }
                    if w5_player_view_diagnostics is not None
                    else {}
                ),
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
                "hierarchical_memory": {
                    "snapshot": session.hierarchical_memory,
                    "context": hierarchical_memory_context,
                },
            },
            "module_scope_truth": module_scope_truth,
            "player_shell_context": player_shell_context,
            "branching_forecast": last_branching_forecast,
            "callback_web": callback_web_snapshot,
            "consequence_cascade": consequence_cascade_snapshot,
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


__all__ = ["_SessionStateApiMixin"]
