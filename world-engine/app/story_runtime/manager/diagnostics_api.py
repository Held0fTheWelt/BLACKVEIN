from __future__ import annotations

from ._deps import *

class _DiagnosticsApiMixin:
    @staticmethod
    def _latest_w5_validation_outcome(session: StorySession) -> dict[str, Any] | None:
        for event in reversed(session.diagnostics):
            if not isinstance(event, dict):
                continue
            validation = (
                event.get("validation_outcome")
                if isinstance(event.get("validation_outcome"), dict)
                else None
            )
            if isinstance(validation, dict) and isinstance(validation.get("w5_validation"), dict):
                return validation
        return None

    def get_w5_admin_snapshot(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return build_w5_admin_snapshot_view(session.w5_latest_snapshot)

    def get_w5_admin_actor(self, session_id: str, actor_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return build_w5_admin_actor_view(session.w5_latest_snapshot, actor_id=actor_id)

    def get_w5_admin_conflicts(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return build_w5_admin_conflicts_view(session.w5_latest_snapshot)

    def get_w5_admin_narrator_projection(
        self,
        session_id: str,
        *,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        session = self.get_session(session_id)
        if actor_id is None:
            candidates = StoryRuntimeManager._w5_narrator_projection_actor_candidates(session)
            actor_id = candidates[0] if candidates else None
        return build_w5_admin_narrator_projection_preview(
            session.w5_latest_snapshot,
            actor_id=actor_id,
        )

    def get_w5_admin_npc_projection(self, session_id: str, actor_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return build_w5_admin_npc_projection_preview(
            session.w5_latest_snapshot,
            actor_id=actor_id,
        )

    def get_w5_admin_validation(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return build_w5_admin_validation_view(
            session.w5_latest_snapshot,
            latest_validation_outcome=self._latest_w5_validation_outcome(session),
        )

    def get_w5_runtime_metadata(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return build_w5_runtime_metadata(
            session.w5_latest_snapshot,
            latest_validation_outcome=self._latest_w5_validation_outcome(session),
        )

    def get_w5_langfuse_metadata(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        location_changed = False
        if isinstance(session.w5_history, list) and len(session.w5_history) >= 2:
            try:
                previous = build_w5_admin_snapshot_view(session.w5_history[-2])
                current = build_w5_admin_snapshot_view(session.w5_history[-1])
                previous_locations = {
                    aid: ((row.get("where") or {}).get("value"))
                    for aid, row in (previous.get("actor_summaries") or {}).items()
                    if isinstance(row, dict)
                }
                current_locations = {
                    aid: ((row.get("where") or {}).get("value"))
                    for aid, row in (current.get("actor_summaries") or {}).items()
                    if isinstance(row, dict)
                }
                location_changed = any(
                    aid in previous_locations and previous_locations[aid] != location
                    for aid, location in current_locations.items()
                )
            except Exception:
                location_changed = False
        return build_w5_langfuse_metadata(
            session.w5_latest_snapshot,
            latest_validation_outcome=self._latest_w5_validation_outcome(session),
            location_changed_this_turn=location_changed,
        )

    def get_diagnostics(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        committed_state = {
            "current_scene_id": session.current_scene_id,
            "turn_counter": session.turn_counter,
            "environment_state": session.environment_state
            if isinstance(session.environment_state, dict)
            else {},
        }
        trace_payload: dict[str, Any] | None = None
        if session.last_thread_update_trace is not None:
            trace_payload = session.last_thread_update_trace.model_dump(mode="json")
        callback_web_snapshot: dict[str, Any] | None = None
        try:
            callback_web = self.get_callback_web(session_id=session.session_id)
            if isinstance(callback_web.get("snapshot"), dict):
                callback_web_snapshot = copy.deepcopy(callback_web["snapshot"])
        except Exception:
            callback_web_snapshot = None
        consequence_cascade_snapshot: dict[str, Any] | None = None
        try:
            cascade = self.get_consequence_cascade(session_id=session.session_id)
            if isinstance(cascade.get("snapshot"), dict):
                consequence_cascade_snapshot = copy.deepcopy(cascade["snapshot"])
        except Exception:
            consequence_cascade_snapshot = None

        return {
            "session_id": session.session_id,
            "turn_counter": session.turn_counter,
            "runtime_config_status": self.runtime_config_status(),
            "committed_state": committed_state,
            "diagnostics": session.diagnostics[-20:],
            "w5_runtime_metadata": self.get_w5_runtime_metadata(session_id),
            "hierarchical_memory": session.hierarchical_memory,
            "callback_web": callback_web_snapshot,
            "consequence_cascade": consequence_cascade_snapshot,
            "envelope_kind": "full_turn_orchestration_includes_graph_retrieval_and_interpreted_input",
            "committed_truth_vs_diagnostics": (
                "Each diagnostics[] entry is a full orchestration envelope (graph, retrieval, model_route, "
                "interpreted_input). Authoritative committed story-runtime truth is session fields, "
                "history, and the bounded narrative_commit object (also embedded in each envelope for correlation). "
                "Narrative thread continuity lives in session.narrative_threads and get_state committed_state "
                "narrative_thread_continuity. Callback-web continuity is derived from committed history, "
                "narrative threads, and branch timelines; callback_web is bounded operator evidence, not a "
                "canonical-state mutation. Consequence-cascade continuity is also derived from committed history "
                "and branch timelines; consequence_cascade is bounded feedback, not a canonical-state mutation. "
                "Narrative_thread_diagnostics.last_update_trace is bounded operator "
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

    def get_last_diagnostics_envelope(self, session_id: str) -> dict[str, Any] | None:
        """Return the last DiagnosticsEnvelope for a session, or None."""
        session = self.get_session(session_id)
        for event in reversed(session.diagnostics):
            if isinstance(event, dict) and "diagnostics_envelope" in event:
                return event["diagnostics_envelope"]
        return None

    def get_narrative_gov_summary(self) -> dict[str, Any]:
        """Return a NarrativeGovSummary across all active GoC sessions."""
        last_session_id = ""
        last_turn = 0
        last_trace_id = ""
        last_ldss_status = "not_invoked"
        last_block_count = 0
        last_legacy_blob = False
        last_human_actor = ""
        last_npc_actors: list[str] = []
        last_quality = ""
        last_signals: list[str] = []

        for sid, session in self.sessions.items():
            if session.module_id != GOD_OF_CARNAGE_MODULE_ID:
                continue
            if session.turn_counter > last_turn:
                last_session_id = sid
                last_turn = session.turn_counter
                proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
                last_human_actor = str(proj.get("human_actor_id") or "").strip()
                last_npc_actors = [
                    str(a) for a in (proj.get("npc_actor_ids") or [])
                    if str(a).strip()
                ]
                for event in reversed(session.diagnostics):
                    if not isinstance(event, dict):
                        continue
                    envelope = event.get("diagnostics_envelope")
                    if isinstance(envelope, dict):
                        last_trace_id = str(envelope.get("trace_id") or "").strip()
                        last_ldss = envelope.get("live_dramatic_scene_simulator") or {}
                        last_ldss_status = str(last_ldss.get("status") or "not_invoked")
                        fc = envelope.get("frontend_render_contract") or {}
                        last_block_count = int(fc.get("scene_block_count") or 0)
                        last_legacy_blob = bool(fc.get("legacy_blob_used"))
                        last_quality = str(envelope.get("quality_class") or "")
                        last_signals = list(envelope.get("degradation_signals") or [])
                        break

        summary = build_narrative_gov_summary(
            last_story_session_id=last_session_id,
            last_turn_number=last_turn,
            last_trace_id=last_trace_id,
            ldss_status=last_ldss_status,
            scene_block_count=last_block_count,
            legacy_blob_used=last_legacy_blob,
            human_actor_id=last_human_actor,
            npc_actor_ids=last_npc_actors,
            quality_class=last_quality,
            degradation_signals=last_signals,
        )
        return summary.to_dict()


__all__ = ["_DiagnosticsApiMixin"]
