from __future__ import annotations

from ._deps import *

class _BranchTimelineMixin:
    def _append_branch_timeline_event_for_session(
        self,
        *,
        session_id: str,
        event_type: str,
        tree_id: str | None = None,
        node_id: str | None = None,
        canonical_turn_id: str | None = None,
        session_fingerprint: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self.get_session(session_id)
        return self._append_branch_timeline_event(
            session=session,
            event_type=event_type,
            tree_id=tree_id,
            node_id=node_id,
            canonical_turn_id=canonical_turn_id,
            session_fingerprint=session_fingerprint,
            details=details,
        )

    def _append_branch_timeline_event(
        self,
        *,
        session: StorySession,
        event_type: str,
        tree_id: str | None = None,
        node_id: str | None = None,
        canonical_turn_id: str | None = None,
        session_fingerprint: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fingerprint = session_fingerprint or self._branching_session_fingerprint(session)
        timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=fingerprint,
        )
        event = make_branch_timeline_event(
            event_type=event_type,
            story_session_id=session.session_id,
            timeline_id=str(timeline.get("timeline_id") or ""),
            scope=str(timeline.get("scope") or BRANCHING_TIMELINE_SCOPE_ACTIVE),
            tree_id=tree_id,
            node_id=node_id,
            canonical_turn_id=canonical_turn_id,
            session_fingerprint=fingerprint,
            details=details,
        )
        updated = append_branch_timeline_event(timeline, event)
        updated["current_session_fingerprint"] = copy.deepcopy(fingerprint)
        return self._persist_branch_timeline_record(updated)

    def _branch_timeline_tree_details(self, record: dict[str, Any]) -> dict[str, Any]:
        summary = record.get("summary") if isinstance(record.get("summary"), dict) else {}
        return {
            "tree_status": record.get("status"),
            "schema_version": record.get("schema_version"),
            "root_canonical_turn_id": record.get("root_canonical_turn_id"),
            "root_turn_number": record.get("root_turn_number"),
            "selectable_node_count": int(summary.get("selectable_node_count") or 0),
            "simulated_turn_count": int(summary.get("simulated_turn_count") or 0),
            "max_depth_observed": int(summary.get("max_depth_observed") or 0),
            "selection_required_to_commit": bool(record.get("selection_required_to_commit")),
            "selection_replays_normal_commit_path": bool(record.get("selection_replays_normal_commit_path")),
            "adopts_simulated_snapshot": bool(record.get("adopts_simulated_snapshot")),
        }

    def _enforce_branch_timeline_tree_bounds(
        self,
        *,
        session_id: str,
        current_session_fingerprint: dict[str, Any],
    ) -> None:
        active_records = [
            record
            for record in self._branching_trees.values()
            if record.get("story_session_id") == session_id
            and str(record.get("status") or "")
            in {
                BRANCHING_TREE_STATUS_SIMULATED,
                BRANCHING_TREE_STATUS_NOT_APPLICABLE,
            }
        ]
        if len(active_records) <= BRANCHING_TIMELINE_DEFAULT_MAX_ACTIVE_TREES:
            return
        active_records.sort(key=lambda row: str(row.get("created_at") or row.get("updated_at") or ""))
        overflow = active_records[: max(0, len(active_records) - BRANCHING_TIMELINE_DEFAULT_MAX_ACTIVE_TREES)]
        session = self.get_session(session_id)
        for record in overflow:
            tree_id = str(record.get("tree_id") or "")
            stale = mark_branch_tree_stale(
                record,
                reason="branch_timeline_active_tree_bound",
                current_session_fingerprint=current_session_fingerprint,
            )
            self._persist_branching_tree_record(stale)
            self._append_branch_timeline_event(
                session=session,
                event_type=BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
                tree_id=tree_id,
                session_fingerprint=current_session_fingerprint,
                details={
                    "reason": "branch_timeline_active_tree_bound",
                    **self._branch_timeline_tree_details(stale),
                },
            )

    def _branching_session_fingerprint(self, session: StorySession) -> dict[str, Any]:
        last_turn = session.history[-1] if session.history else {}
        last_canonical_turn_id = (
            last_turn.get("canonical_turn_id") if isinstance(last_turn, dict) else None
        )
        runtime_profile_id = _runtime_profile_id_from_projection(
            session.runtime_projection if isinstance(session.runtime_projection, dict) else None
        )
        payload = {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "runtime_profile_id": runtime_profile_id,
            "turn_counter": session.turn_counter,
            "history_count": len(session.history or []),
            "current_scene_id": session.current_scene_id,
            "last_canonical_turn_id": last_canonical_turn_id,
            "content_provenance": session.content_provenance,
            "runtime_projection": session.runtime_projection,
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:24]
        return {
            **payload,
            "fingerprint": fingerprint,
            "content_provenance_hash": hashlib.sha256(
                json.dumps(session.content_provenance, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()[:16],
            "runtime_projection_hash": hashlib.sha256(
                json.dumps(session.runtime_projection, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()[:16],
        }

    def _refresh_branching_tree_freshness(self, record: dict[str, Any]) -> dict[str, Any]:
        status = str(record.get("status") or "")
        if status in {
            BRANCHING_TREE_STATUS_STALE,
            BRANCHING_TREE_STATUS_EXPIRED,
            BRANCHING_TREE_STATUS_COMMITTED,
        }:
            return record
        session_id = str(record.get("story_session_id") or "")
        try:
            current_fingerprint = self._branching_session_fingerprint(self.get_session(session_id))
        except KeyError:
            return record
        if branch_tree_is_fresh(record, current_fingerprint):
            return record
        stale = mark_branch_tree_stale(
            record,
            reason="session_changed_since_tree_creation",
            current_session_fingerprint=current_fingerprint,
        )
        persisted = self._persist_branching_tree_record(stale)
        try:
            self._append_branch_timeline_event_for_session(
                session_id=session_id,
                event_type=BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
                tree_id=str(persisted.get("tree_id") or ""),
                session_fingerprint=current_fingerprint,
                details={
                    "reason": "session_changed_since_tree_creation",
                    **self._branch_timeline_tree_details(persisted),
                },
            )
        except KeyError:
            pass
        return persisted

    def _mark_branching_trees_stale_for_session(
        self,
        *,
        session_id: str,
        except_tree_id: str | None,
        current_session_fingerprint: dict[str, Any],
        reason: str,
    ) -> None:
        for tree_id, record in list(self._branching_trees.items()):
            if tree_id == except_tree_id:
                continue
            if record.get("story_session_id") != session_id:
                continue
            if str(record.get("status") or "") not in {
                BRANCHING_TREE_STATUS_SIMULATED,
                BRANCHING_TREE_STATUS_NOT_APPLICABLE,
            }:
                continue
            stale = mark_branch_tree_stale(
                record,
                reason=reason,
                current_session_fingerprint=current_session_fingerprint,
            )
            persisted = self._persist_branching_tree_record(stale)
            try:
                self._append_branch_timeline_event_for_session(
                    session_id=session_id,
                    event_type=BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
                    tree_id=str(persisted.get("tree_id") or ""),
                    session_fingerprint=current_session_fingerprint,
                    details={"reason": reason, **self._branch_timeline_tree_details(persisted)},
                )
            except KeyError:
                continue

    def _branching_replay_matches_node(
        self,
        *,
        event: dict[str, Any],
        simulation_node: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        preview_commit = (
            simulation_node.get("narrative_commit_preview")
            if isinstance(simulation_node.get("narrative_commit_preview"), dict)
            else {}
        )
        actual_commit = event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {}
        mismatch_fields: list[str] = []
        for field_name in ("committed_scene_id", "situation_status", "commit_reason_code"):
            if preview_commit.get(field_name) != actual_commit.get(field_name):
                mismatch_fields.append(f"narrative_commit.{field_name}")
        preview_validation_status = simulation_node.get("validation_status")
        actual_validation = event.get("validation_outcome") if isinstance(event.get("validation_outcome"), dict) else {}
        if preview_validation_status and preview_validation_status != actual_validation.get("status"):
            mismatch_fields.append("validation_outcome.status")
        return not mismatch_fields, mismatch_fields

    def _latest_branching_forecast_from_session(self, session: StorySession) -> dict[str, Any]:
        for row in reversed(session.history or []):
            if not isinstance(row, dict):
                continue
            forecast = row.get("branching_forecast")
            if not isinstance(forecast, dict):
                ledger = row.get("turn_aspect_ledger")
                if isinstance(ledger, dict):
                    forecast = ledger.get("branching_forecast")
            if isinstance(forecast, dict):
                return copy.deepcopy(forecast)
        return {}


__all__ = ["_BranchTimelineMixin"]
