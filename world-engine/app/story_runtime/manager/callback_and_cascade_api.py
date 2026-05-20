from __future__ import annotations

from ._deps import *

class _CallbackAndCascadeApiMixin:
    def get_callback_web(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        callback_web_id = stable_callback_web_id(story_session_id=session.session_id)
        existing = self._callback_webs.get(callback_web_id)
        if isinstance(existing, dict):
            return copy.deepcopy(existing)
        return self.rebuild_callback_web(session_id=session_id)

    def list_callback_web_edges(self, *, session_id: str) -> list[dict[str, Any]]:
        record = self.get_callback_web(session_id=session_id)
        edges = record.get("edges") if isinstance(record.get("edges"), list) else []
        return [copy.deepcopy(edge) for edge in edges if isinstance(edge, dict)]

    def rebuild_callback_web(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        branch_timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=self._branching_session_fingerprint(session),
        )
        existing = self._callback_webs.get(stable_callback_web_id(story_session_id=session.session_id))
        callback_policy = _load_module_callback_web_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        record = build_callback_web_record(
            story_session_id=session.session_id,
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
            history=[dict(row) for row in session.history if isinstance(row, dict)],
            narrative_threads=session.narrative_threads.model_dump(mode="json")
            if hasattr(session.narrative_threads, "model_dump")
            else session.narrative_threads,
            branch_timeline=branch_timeline,
            current_session_fingerprint=self._branching_session_fingerprint(session),
            bounds=callback_web_bounds_from_policy(callback_policy),
            created_at=existing.get("created_at") if isinstance(existing, dict) else None,
        )
        return self._persist_callback_web_record(record)

    def _prior_callback_web_state_for_graph(self, session: StorySession) -> dict[str, Any] | None:
        policy = _load_module_callback_web_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        if not policy.get("enabled"):
            return None
        try:
            record = self.get_callback_web(session_id=session.session_id)
        except Exception:
            return None
        return build_graph_callback_web_export(
            record,
            max_edges=int(policy.get("max_graph_edges") or 4),
        )

    def _refresh_callback_web_after_commit(
        self,
        *,
        session: StorySession,
        event: dict[str, Any],
        graph_state: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        gs = graph_state if isinstance(graph_state, dict) else {}
        policy = _load_module_callback_web_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        try:
            record = self.rebuild_callback_web(session_id=session.session_id)
        except Exception:
            logger.debug("Callback web refresh failed", exc_info=True)
            return None
        snapshot = copy.deepcopy(record.get("snapshot") if isinstance(record.get("snapshot"), dict) else {})
        event["callback_web"] = snapshot
        graph_export = build_graph_callback_web_export(
            record,
            max_edges=int(policy.get("max_graph_edges") or 4),
        )
        validation = validate_callback_web_record(record, policy=policy)
        event["callback_web_feedback"] = graph_export
        event["callback_web_validation"] = validation
        gov = event.get("runtime_governance_surface")
        if isinstance(gov, dict):
            gov["callback_web"] = {
                "status": validation.get("status"),
                "contract_pass": validation.get("contract_pass"),
                "failure_codes": validation.get("failure_codes") or [],
                "edge_count": snapshot.get("edge_count"),
                "observation_count": snapshot.get("observation_count"),
                "selected_callback_kind": (
                    graph_export.get("selected_callback_kind")
                    if isinstance(graph_export, dict)
                    else None
                ),
            }
        if gs:
            _record_callback_web_aspect(
                session=session,
                graph_state=gs,
                event=event,
                record=record,
                graph_export=graph_export,
                validation=validation,
                policy=policy,
            )
        if isinstance(event.get("diagnostics"), dict):
            event["diagnostics"]["turn_aspect_ledger"] = event.get("turn_aspect_ledger")
            event["diagnostics"]["callback_web"] = snapshot
            event["diagnostics"]["callback_web_validation"] = validation
        if session.history and isinstance(session.history[-1], dict):
            session.history[-1]["callback_web_summary"] = snapshot
            session.history[-1]["callback_web_feedback"] = graph_export
            session.history[-1]["callback_web_validation"] = validation
            if isinstance(event.get("turn_aspect_ledger"), dict):
                session.history[-1]["turn_aspect_ledger"] = event["turn_aspect_ledger"]
        return record

    def get_consequence_cascade(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        cascade_id = stable_consequence_cascade_id(story_session_id=session.session_id)
        existing = self._consequence_cascades.get(cascade_id)
        if isinstance(existing, dict):
            return copy.deepcopy(existing)
        return self.rebuild_consequence_cascade(session_id=session_id)

    def list_consequence_cascade_edges(self, *, session_id: str) -> list[dict[str, Any]]:
        record = self.get_consequence_cascade(session_id=session_id)
        edges = record.get("edges") if isinstance(record.get("edges"), list) else []
        return [copy.deepcopy(edge) for edge in edges if isinstance(edge, dict)]

    def rebuild_consequence_cascade(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        branch_timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=self._branching_session_fingerprint(session),
        )
        existing = self._consequence_cascades.get(
            stable_consequence_cascade_id(story_session_id=session.session_id)
        )
        runtime_profile_id = _runtime_profile_id_from_projection(
            session.runtime_projection if isinstance(session.runtime_projection, dict) else None
        )
        cascade_policy = _load_module_consequence_cascade_policy(
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
        )
        callback_web: dict[str, Any] | None = None
        try:
            callback_web = self.get_callback_web(session_id=session.session_id)
        except Exception:
            callback_web = None
        record = build_consequence_cascade_record(
            story_session_id=session.session_id,
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
            history=[dict(row) for row in session.history if isinstance(row, dict)],
            narrative_threads=session.narrative_threads.model_dump(mode="json")
            if hasattr(session.narrative_threads, "model_dump")
            else session.narrative_threads,
            branch_timeline=branch_timeline,
            callback_web=callback_web,
            bounds=consequence_cascade_bounds_from_policy(cascade_policy),
            created_at=existing.get("created_at") if isinstance(existing, dict) else None,
        )
        return self._persist_consequence_cascade_record(record)

    def _prior_consequence_cascade_state_for_graph(self, session: StorySession) -> dict[str, Any] | None:
        policy = _load_module_consequence_cascade_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        if not policy.get("enabled"):
            return None
        try:
            record = self.get_consequence_cascade(session_id=session.session_id)
        except Exception:
            return None
        return build_graph_consequence_cascade_export(
            record,
            max_items=int(policy.get("max_graph_items") or 5),
        )


__all__ = ["_CallbackAndCascadeApiMixin"]
