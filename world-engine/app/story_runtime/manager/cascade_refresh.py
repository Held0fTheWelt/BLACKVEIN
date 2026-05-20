from __future__ import annotations

from ._deps import *

class _CascadeRefreshMixin:
    def _refresh_consequence_cascade_after_commit(
        self,
        *,
        session: StorySession,
        event: dict[str, Any],
        graph_state: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        gs = graph_state if isinstance(graph_state, dict) else {}
        policy = _load_module_consequence_cascade_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        try:
            record = self.rebuild_consequence_cascade(session_id=session.session_id)
        except Exception:
            logger.debug("Consequence cascade refresh failed", exc_info=True)
            return None
        snapshot = copy.deepcopy(record.get("snapshot") if isinstance(record.get("snapshot"), dict) else {})
        event["consequence_cascade"] = snapshot
        graph_export = build_graph_consequence_cascade_export(
            record,
            max_items=int(policy.get("max_graph_items") or 5),
        )
        validation = validate_consequence_cascade_record(record, policy=policy)
        event["consequence_cascade_feedback"] = graph_export
        event["consequence_cascade_validation"] = validation
        gov = event.get("runtime_governance_surface")
        if isinstance(gov, dict):
            gov["consequence_cascade"] = {
                "status": validation.get("status"),
                "contract_pass": validation.get("contract_pass"),
                "failure_codes": validation.get("failure_codes") or [],
                "atom_count": snapshot.get("atom_count"),
                "edge_count": snapshot.get("edge_count"),
                "active_atom_count": snapshot.get("active_atom_count"),
                "selected_continuity_classes": (
                    graph_export.get("selected_continuity_classes")
                    if isinstance(graph_export, dict)
                    else []
                ),
            }
        if gs:
            _record_consequence_cascade_aspect(
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
            event["diagnostics"]["consequence_cascade"] = snapshot
            event["diagnostics"]["consequence_cascade_validation"] = validation
        if session.history and isinstance(session.history[-1], dict):
            session.history[-1]["consequence_cascade_summary"] = snapshot
            session.history[-1]["consequence_cascade_feedback"] = graph_export
            session.history[-1]["consequence_cascade_validation"] = validation
            if isinstance(event.get("turn_aspect_ledger"), dict):
                session.history[-1]["turn_aspect_ledger"] = event["turn_aspect_ledger"]
        return record


__all__ = ["_CascadeRefreshMixin"]
