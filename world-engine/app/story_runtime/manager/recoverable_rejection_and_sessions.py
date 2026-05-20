"""Recoverable rejection and session helpers.

Handles recoverable validation rejections while preserving session history and playable continuation state.
"""
from __future__ import annotations

from ._deps import *

class _RecoverableRejectionAndSessionsMixin:
    def _build_recoverable_rejection_turn(
        self,
        *,
        session: StorySession,
        graph_state: dict[str, Any],
        trace_id: str | None,
        attempted_turn_number: int,
        player_input: str,
        prior_scene_id: str,
        validation_outcome: dict[str, Any],
    ) -> dict[str, Any]:
        reason = str(validation_outcome.get("reason") or "rejected")
        interpreted_input = (
            graph_state.get("interpreted_input")
            if isinstance(graph_state.get("interpreted_input"), dict)
            else {}
        )
        message = _recoverable_turn_message(session=session, reason=reason)
        turn_aspect_ledger = _recoverable_runtime_aspect_ledger(
            session_id=session.session_id,
            module_id=session.module_id,
            turn_number=attempted_turn_number,
            turn_kind="player_rejected_recoverable",
            player_input=player_input,
            trace_id=trace_id,
            reason=reason,
            validation_status=str(validation_outcome.get("status") or "rejected"),
            existing_ledger=graph_state.get("turn_aspect_ledger")
            if isinstance(graph_state.get("turn_aspect_ledger"), dict)
            else None,
            visible_output_present=True,
        )
        val_merged: dict[str, Any] = {
            **validation_outcome,
            "recoverable_rejection": True,
            "hard_boundary_failure": False,
        }
        event = _recoverable_playable_turn_envelope(
            session=session,
            commit_turn_number=attempted_turn_number,
            player_input=player_input,
            trace_id=trace_id,
            turn_kind="player_rejected_recoverable",
            interpreted_input=interpreted_input,
            narrative_commit={
                "situation_status": "continue",
                "allowed": False,
                "commit_reason_code": "recoverable_rejection",
                "committed_scene_id": prior_scene_id,
                "proposed_scene_id": prior_scene_id,
                "selected_candidate_source": "validation_gate",
                "is_terminal": False,
            },
            validation_outcome=val_merged,
            message=message,
            turn_aspect_ledger=turn_aspect_ledger,
            reason=reason,
        )
        graph_state["turn_aspect_ledger"] = event.get("turn_aspect_ledger")
        graph_state["visible_output_bundle"] = event["visible_output_bundle"]
        graph_state["validation_outcome"] = event["validation_outcome"]
        return self._persist_player_visible_turn_event(
            session=session,
            graph_state=graph_state,
            event=event,
            trace_id=trace_id,
            commit_turn_number=attempted_turn_number,
            player_input=player_input,
            turn_outcome="recoverable_rejection",
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


__all__ = ["_RecoverableRejectionAndSessionsMixin"]
