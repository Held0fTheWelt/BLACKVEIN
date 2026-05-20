"""Branch simulation helpers.

Runs bounded branch simulation for alternate story paths without mutating the authoritative session state.
"""
from __future__ import annotations

from ._deps import *

class _BranchSimulationMixin:
    def _branching_simulation_clone_session_id(
        self,
        *,
        root_session_id: str,
        path_option_ids: list[str],
    ) -> str:
        seed = "|".join([root_session_id, *path_option_ids])
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        return f"{root_session_id}:branch-sim:{digest}"

    def _branching_simulation_session_clone(
        self,
        *,
        base_session_snapshot: StorySession,
        clone_session_id: str,
        path_option_ids: list[str],
    ) -> StorySession:
        clone = story_session_from_payload(story_session_to_payload(base_session_snapshot))
        clone.session_id = clone_session_id
        clone.content_provenance = copy.deepcopy(clone.content_provenance)
        trace_classification = (
            clone.content_provenance.get("trace_classification")
            if isinstance(clone.content_provenance.get("trace_classification"), dict)
            else {}
        )
        trace_classification = {
            **trace_classification,
            "trace_origin": "branching_simulation",
            "execution_tier": "diagnostic",
            "canonical_player_flow": False,
        }
        clone.content_provenance["trace_classification"] = trace_classification
        clone.content_provenance["branching_simulation"] = {
            "source_session_id": base_session_snapshot.session_id,
            "path_option_ids": list(path_option_ids),
            "simulation_only": True,
            "mutates_active_session": False,
        }
        return clone

    def _execute_branching_simulation_turn_on_clone(
        self,
        *,
        base_session_snapshot: StorySession,
        clone_session_id: str,
        simulated_input: str,
        trace_id: str,
        path_option_ids: list[str],
    ) -> tuple[dict[str, Any] | None, StorySession | None, str | None]:
        clone = self._branching_simulation_session_clone(
            base_session_snapshot=base_session_snapshot,
            clone_session_id=clone_session_id,
            path_option_ids=path_option_ids,
        )
        had_session = clone_session_id in self.sessions
        prior_session = self.sessions.get(clone_session_id)
        with self._session_locks_guard:
            had_lock = clone_session_id in self._session_turn_locks
            prior_lock = self._session_turn_locks.get(clone_session_id)
            self._session_turn_locks[clone_session_id] = threading.Lock()
        try:
            self._branching_simulation_session_ids.add(clone_session_id)
            self.sessions[clone_session_id] = clone
            event = self._execute_turn_locked(
                session_id=clone_session_id,
                player_input=simulated_input,
                trace_id=trace_id,
            )
            simulated_snapshot = story_session_from_payload(
                story_session_to_payload(self.sessions[clone_session_id])
            )
            return event, simulated_snapshot, None
        except Exception as exc:
            logger.debug("Branching simulation clone turn failed", exc_info=True)
            return None, clone, str(exc)
        finally:
            self._branching_simulation_session_ids.discard(clone_session_id)
            if had_session and prior_session is not None:
                self.sessions[clone_session_id] = prior_session
            else:
                self.sessions.pop(clone_session_id, None)
            with self._session_locks_guard:
                if had_lock and prior_lock is not None:
                    self._session_turn_locks[clone_session_id] = prior_lock
                else:
                    self._session_turn_locks.pop(clone_session_id, None)

    def _branching_simulation_stop_reason(
        self,
        *,
        depth: int,
        max_depth: int,
        simulated_event: dict[str, Any] | None,
        child_forecast: dict[str, Any],
        error: str | None,
    ) -> str | None:
        if error:
            return "simulation_error"
        event = simulated_event if isinstance(simulated_event, dict) else {}
        narrative_commit = (
            event.get("narrative_commit")
            if isinstance(event.get("narrative_commit"), dict)
            else {}
        )
        if bool(narrative_commit.get("is_terminal")) or str(narrative_commit.get("situation_status") or "") == "terminal":
            return "terminal_turn"
        if depth >= max_depth:
            return "max_depth"
        if not forecast_has_options(child_forecast):
            return "no_branching_options"
        return None


__all__ = ["_BranchSimulationMixin"]
