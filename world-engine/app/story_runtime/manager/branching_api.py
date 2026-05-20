from __future__ import annotations

from ._deps import *

class _BranchingApiMixin:
    def build_branching_simulation_tree(
        self,
        *,
        session_id: str,
        max_depth: int | None = None,
        max_branching: int | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Run a bounded multi-turn branching simulation on isolated clones.

        The active story session is copied once under its turn lock. Every
        simulated future turn runs through the normal manager turn pipeline on
        a temporary clone session id, with durable persistence disabled and the
        clone removed afterwards. The returned tree is diagnostic evidence only.
        """

        depth_limit, branching_limit, node_limit = clamp_simulation_limits(
            max_depth=max_depth,
            max_branching=max_branching,
        )
        with self._session_turn_lock(session_id):
            active_session = self.get_session(session_id)
            root_snapshot = story_session_from_payload(story_session_to_payload(active_session))

        root_session_fingerprint = self._branching_session_fingerprint(root_snapshot)
        root_forecast = self._latest_branching_forecast_from_session(root_snapshot)
        root_turn = root_snapshot.history[-1] if root_snapshot.history else {}
        root_canonical_turn_id = (
            root_turn.get("canonical_turn_id") if isinstance(root_turn, dict) else None
        )
        root_turn_number = (
            int(root_turn.get("turn_number"))
            if isinstance(root_turn, dict) and root_turn.get("turn_number") is not None
            else root_snapshot.turn_counter
        )
        runtime_profile_id = _runtime_profile_id_from_projection(
            root_snapshot.runtime_projection if isinstance(root_snapshot.runtime_projection, dict) else None
        )
        sim_trace_id = trace_id or f"branching-simulation-{uuid4().hex}"
        tree = make_simulation_tree(
            story_session_id=root_snapshot.session_id,
            module_id=root_snapshot.module_id,
            runtime_profile_id=runtime_profile_id,
            root_canonical_turn_id=root_canonical_turn_id,
            root_turn_number=root_turn_number,
            root_branching_forecast=root_forecast,
            max_depth=depth_limit,
            max_branching=branching_limit,
            max_nodes=node_limit,
            trace_id=sim_trace_id,
        )
        tree["root_session_fingerprint"] = root_session_fingerprint
        tree["scope"] = "active"
        if depth_limit <= 0 or branching_limit <= 0 or not forecast_has_options(root_forecast):
            return finalize_simulation_tree(tree)

        root_node_id = str(tree.get("root_node_id") or "")
        queue: list[tuple[StorySession, dict[str, Any], str, int, list[str]]] = [
            (root_snapshot, root_forecast, root_node_id, 1, [])
        ]
        while queue:
            base_snapshot, forecast, parent_node_id, depth, path_option_ids = queue.pop(0)
            options = (
                forecast.get("options")
                if isinstance(forecast.get("options"), list)
                else []
            )
            for option_index, option_raw in enumerate(options[:branching_limit]):
                if len(tree.get("nodes") or []) >= node_limit:
                    tree["truncated"] = True
                    tree["truncation_reason"] = "max_nodes"
                    return finalize_simulation_tree(tree)
                option = option_raw if isinstance(option_raw, dict) else {}
                option_id = str(option.get("option_id") or f"option_{option_index}").strip()
                next_path = [*path_option_ids, option_id]
                simulated_input = simulated_input_for_branch_option(option, depth=depth)
                clone_session_id = self._branching_simulation_clone_session_id(
                    root_session_id=root_snapshot.session_id,
                    path_option_ids=next_path,
                )
                simulated_event, simulated_snapshot, error = self._execute_branching_simulation_turn_on_clone(
                    base_session_snapshot=base_snapshot,
                    clone_session_id=clone_session_id,
                    simulated_input=simulated_input,
                    trace_id=sim_trace_id,
                    path_option_ids=next_path,
                )
                child_forecast = (
                    simulated_event.get("branching_forecast")
                    if isinstance(simulated_event, dict)
                    and isinstance(simulated_event.get("branching_forecast"), dict)
                    else {}
                )
                stop_reason = self._branching_simulation_stop_reason(
                    depth=depth,
                    max_depth=depth_limit,
                    simulated_event=simulated_event,
                    child_forecast=child_forecast,
                    error=error,
                )
                node = make_simulated_turn_node(
                    tree=tree,
                    parent_node_id=parent_node_id,
                    depth=depth,
                    option=option,
                    option_index=option_index,
                    path_option_ids=next_path,
                    simulated_input=simulated_input,
                    simulated_event=simulated_event,
                    stop_reason=stop_reason,
                    error=error,
                )
                append_simulation_node(tree, node)
                if stop_reason is None and simulated_snapshot is not None:
                    queue.append((simulated_snapshot, child_forecast, str(node.get("node_id")), depth + 1, next_path))
        return finalize_simulation_tree(tree)

    def create_branching_tree(
        self,
        *,
        session_id: str,
        max_depth: int | None = None,
        max_branching: int | None = None,
        trace_id: str | None = None,
        scope: str = "active",
        preview: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create and persist a selectable bounded branch tree record."""

        if scope != "active":
            raise ValueError("branching_preview_scope_not_implemented")
        simulation_tree = self.build_branching_simulation_tree(
            session_id=session_id,
            max_depth=max_depth,
            max_branching=max_branching,
            trace_id=trace_id,
        )
        with self._session_turn_lock(session_id):
            session = self.get_session(session_id)
            current_fingerprint = self._branching_session_fingerprint(session)
        root_fingerprint = (
            simulation_tree.get("root_session_fingerprint")
            if isinstance(simulation_tree.get("root_session_fingerprint"), dict)
            else current_fingerprint
        )
        record = make_branch_tree_record(
            simulation_tree=simulation_tree,
            root_session_fingerprint=root_fingerprint,
            current_session_fingerprint=current_fingerprint,
            trace_id=trace_id,
            scope=scope,
            preview=preview,
        )
        if not branch_tree_is_fresh(record, current_fingerprint):
            record = mark_branch_tree_stale(
                record,
                reason="session_changed_during_simulation",
                current_session_fingerprint=current_fingerprint,
            )
        persisted = self._persist_branching_tree_record(record)
        self._append_branch_timeline_event_for_session(
            session_id=session_id,
            event_type=BRANCHING_TIMELINE_EVENT_TREE_CREATED,
            tree_id=str(persisted.get("tree_id") or ""),
            session_fingerprint=current_fingerprint,
            details=self._branch_timeline_tree_details(persisted),
        )
        self._enforce_branch_timeline_tree_bounds(
            session_id=session_id,
            current_session_fingerprint=current_fingerprint,
        )
        return persisted

    def list_branching_trees(self, *, session_id: str) -> list[dict[str, Any]]:
        self.get_session(session_id)
        rows = [
            self._refresh_branching_tree_freshness(record)
            for record in self._branching_trees.values()
            if record.get("story_session_id") == session_id
        ]
        rows.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)
        return [copy.deepcopy(row) for row in rows]

    def get_branching_tree(self, *, session_id: str, tree_id: str) -> dict[str, Any]:
        self.get_session(session_id)
        record = self._branching_trees.get(tree_id)
        if not isinstance(record, dict) or record.get("story_session_id") != session_id:
            raise KeyError(tree_id)
        return copy.deepcopy(self._refresh_branching_tree_freshness(record))

    def expire_branching_tree(
        self,
        *,
        session_id: str,
        tree_id: str,
        reason: str = "operator_expired",
    ) -> dict[str, Any]:
        self.get_session(session_id)
        record = self._branching_trees.get(tree_id)
        if not isinstance(record, dict) or record.get("story_session_id") != session_id:
            raise KeyError(tree_id)
        expired = mark_branch_tree_expired(record, reason=reason)
        persisted = self._persist_branching_tree_record(expired)
        session = self.get_session(session_id)
        self._append_branch_timeline_event(
            session=session,
            event_type=BRANCHING_TIMELINE_EVENT_TREE_EXPIRED,
            tree_id=tree_id,
            session_fingerprint=self._branching_session_fingerprint(session),
            details={"reason": reason, **self._branch_timeline_tree_details(persisted)},
        )
        return persisted

    def get_branch_timeline(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=self._branching_session_fingerprint(session),
        )
        return copy.deepcopy(timeline)

    def list_branch_timeline_events(self, *, session_id: str) -> list[dict[str, Any]]:
        timeline = self.get_branch_timeline(session_id=session_id)
        events = timeline.get("events") if isinstance(timeline.get("events"), list) else []
        return [copy.deepcopy(event) for event in events if isinstance(event, dict)]

    def compact_branch_timeline(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=self._branching_session_fingerprint(session),
        )
        compacted = compact_branch_timeline(timeline)
        return self._persist_branch_timeline_record(compacted)

    def archive_branch_timeline(
        self,
        *,
        session_id: str,
        reason: str = "operator_archived",
    ) -> dict[str, Any]:
        session = self.get_session(session_id)
        timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=self._branching_session_fingerprint(session),
        )
        archived = archive_branch_timeline(timeline, reason=reason)
        return self._persist_branch_timeline_record(archived)


__all__ = ["_BranchingApiMixin"]
