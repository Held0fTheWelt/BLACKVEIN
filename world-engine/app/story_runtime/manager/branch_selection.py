from __future__ import annotations

from ._deps import *

class _BranchSelectionMixin:
    def select_branching_tree_node(
        self,
        *,
        session_id: str,
        tree_id: str,
        node_id: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Replay a selected simulated path through the authoritative commit path."""

        with self._session_turn_lock(session_id):
            session = self.get_session(session_id)
            record = self._branching_trees.get(tree_id)
            if not isinstance(record, dict) or record.get("story_session_id") != session_id:
                raise KeyError(tree_id)
            status = str(record.get("status") or "")
            if status in {BRANCHING_TREE_STATUS_EXPIRED, BRANCHING_TREE_STATUS_COMMITTED}:
                raise ValueError(f"branching_tree_not_selectable:{status}")
            current_fingerprint = self._branching_session_fingerprint(session)
            if not branch_tree_is_fresh(record, current_fingerprint):
                stale = mark_branch_tree_stale(
                    record,
                    reason="session_changed_since_tree_creation",
                    current_session_fingerprint=current_fingerprint,
                )
                self._persist_branching_tree_record(stale)
                self._append_branch_timeline_event(
                    session=session,
                    event_type=BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
                    tree_id=tree_id,
                    session_fingerprint=current_fingerprint,
                    details={
                        "reason": "session_changed_since_tree_creation",
                        **self._branch_timeline_tree_details(stale),
                    },
                )
                raise ValueError("branching_tree_stale")
            if status not in {BRANCHING_TREE_STATUS_SIMULATED, BRANCHING_TREE_STATUS_NOT_APPLICABLE}:
                raise ValueError(f"branching_tree_not_selectable:{status}")
            node = find_branch_tree_node(record, node_id)
            if not isinstance(node, dict):
                raise KeyError(node_id)
            selectable = set(str(item) for item in (record.get("selectable_node_ids") or []))
            if node_id not in selectable:
                raise ValueError("branching_node_not_selectable")
            path_nodes = branch_tree_path_nodes(record, node_id)
            if not path_nodes:
                raise ValueError("branching_node_path_empty")

            selection_trace_id = trace_id or f"branching-tree-select-{uuid4().hex}"
            selected_path_node_ids = [str(item.get("node_id")) for item in path_nodes if item.get("node_id")]
            self._append_branch_timeline_event(
                session=session,
                event_type=BRANCHING_TIMELINE_EVENT_NODE_SELECTED,
                tree_id=tree_id,
                node_id=node_id,
                session_fingerprint=current_fingerprint,
                details={
                    "selected_path_node_ids": selected_path_node_ids,
                    "selected_path_option_ids": list(node.get("path_option_ids") or []),
                    "uses_normal_commit_path": True,
                    "adopts_simulated_snapshot": False,
                },
            )
            self._append_branch_timeline_event(
                session=session,
                event_type=BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_STARTED,
                tree_id=tree_id,
                node_id=node_id,
                session_fingerprint=current_fingerprint,
                details={
                    "selected_path_node_ids": selected_path_node_ids,
                    "trace_id": selection_trace_id,
                },
            )
            replayed_turns: list[dict[str, Any]] = []
            committed_events: list[dict[str, Any]] = []
            replay_conflicts: list[dict[str, Any]] = []
            try:
                for path_node in path_nodes:
                    simulated_input = str(path_node.get("simulated_input") or "").strip()
                    if not simulated_input:
                        raise ValueError("branching_node_missing_simulated_input")
                    event = self._execute_turn_locked(
                        session_id=session_id,
                        player_input=simulated_input,
                        trace_id=selection_trace_id,
                    )
                    committed_events.append(copy.deepcopy(event))
                    matched, mismatch_fields = self._branching_replay_matches_node(
                        event=event,
                        simulation_node=path_node,
                    )
                    replay_row = {
                        "node_id": path_node.get("node_id"),
                        "path_option_ids": list(path_node.get("path_option_ids") or []),
                        "simulated_turn_id": path_node.get("simulated_turn_id"),
                        "committed_canonical_turn_id": event.get("canonical_turn_id"),
                        "committed_turn_number": event.get("turn_number"),
                        "simulated_input": simulated_input,
                        "matched_simulation_preview": matched,
                        "mismatch_fields": mismatch_fields,
                    }
                    replayed_turns.append(replay_row)
                    if not matched:
                        replay_conflicts.append(replay_row)
                        break
            except Exception as exc:
                failure_fingerprint = self._branching_session_fingerprint(session)
                self._append_branch_timeline_event(
                    session=session,
                    event_type=BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT,
                    tree_id=tree_id,
                    node_id=node_id,
                    canonical_turn_id=(
                        str(committed_events[-1].get("canonical_turn_id"))
                        if committed_events and isinstance(committed_events[-1], dict)
                        else None
                    ),
                    session_fingerprint=failure_fingerprint,
                    details={
                        "selection_status": "branch_replay_exception",
                        "replayed_turn_count": len(replayed_turns),
                        "replay_conflict_count": len(replay_conflicts),
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc)[:240],
                        "uses_normal_commit_path": True,
                        "adopts_simulated_snapshot": False,
                    },
                )
                raise

            after_fingerprint = self._branching_session_fingerprint(session)
            selection_status = "branch_replay_conflict" if replay_conflicts else "committed"
            selection = {
                "schema_version": "branching_tree_selection.v1",
                "status": selection_status,
                "tree_id": tree_id,
                "selected_node_id": node_id,
                "selected_path_node_ids": selected_path_node_ids,
                "selected_path_option_ids": list(node.get("path_option_ids") or []),
                "trace_id": selection_trace_id,
                "replayed_turn_count": len(replayed_turns),
                "replayed_turns": replayed_turns,
                "replay_conflicts": replay_conflicts,
                "uses_normal_commit_path": True,
                "adopts_simulated_snapshot": False,
            }
            committed_record = mark_branch_tree_committed(
                record,
                node_id=node_id,
                selection=selection,
                current_session_fingerprint=after_fingerprint,
            )
            self._persist_branching_tree_record(committed_record)
            final_event_type = (
                BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT
                if replay_conflicts
                else BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED
            )
            last_committed_event = committed_events[-1] if committed_events else {}
            self._append_branch_timeline_event(
                session=session,
                event_type=final_event_type,
                tree_id=tree_id,
                node_id=node_id,
                canonical_turn_id=(
                    str(last_committed_event.get("canonical_turn_id"))
                    if isinstance(last_committed_event, dict) and last_committed_event.get("canonical_turn_id")
                    else None
                ),
                session_fingerprint=after_fingerprint,
                details={
                    "selection_status": selection_status,
                    "replayed_turn_count": len(replayed_turns),
                    "replay_conflict_count": len(replay_conflicts),
                    "committed_canonical_turn_ids": [
                        str(event.get("canonical_turn_id"))
                        for event in committed_events
                        if isinstance(event, dict) and event.get("canonical_turn_id")
                    ],
                    "uses_normal_commit_path": True,
                    "adopts_simulated_snapshot": False,
                },
            )
            self._mark_branching_trees_stale_for_session(
                session_id=session_id,
                except_tree_id=tree_id,
                current_session_fingerprint=after_fingerprint,
                reason="session_advanced_by_branch_selection",
            )
            return {
                "session_id": session_id,
                "tree_id": tree_id,
                "selection": selection,
                "committed_events": committed_events,
                "branching_tree": copy.deepcopy(committed_record),
            }

    def _branch_timeline_for_session(
        self,
        *,
        session: StorySession,
        current_session_fingerprint: dict[str, Any],
        scope: str = BRANCHING_TIMELINE_SCOPE_ACTIVE,
        preview: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        timeline_id = stable_branch_timeline_id(
            story_session_id=session.session_id,
            scope=scope,
            preview=preview,
        )
        existing = self._branch_timelines.get(timeline_id)
        if isinstance(existing, dict):
            updated = copy.deepcopy(existing)
            updated["current_session_fingerprint"] = copy.deepcopy(current_session_fingerprint)
            if not updated.get("module_id"):
                updated["module_id"] = session.module_id
            if not updated.get("runtime_profile_id"):
                updated["runtime_profile_id"] = _runtime_profile_id_from_projection(
                    session.runtime_projection if isinstance(session.runtime_projection, dict) else None
                )
            return self._persist_branch_timeline_record(updated)
        record = make_branch_timeline_record(
            story_session_id=session.session_id,
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
            scope=scope,
            root_session_fingerprint=current_session_fingerprint,
            preview=preview,
        )
        return self._persist_branch_timeline_record(record)


__all__ = ["_BranchSelectionMixin"]
