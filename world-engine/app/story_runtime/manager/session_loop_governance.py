from __future__ import annotations

from ._deps import *

class _SessionLoopGovernanceMixin:
    def _log_session_loop_event(self, *, event: str, session: StorySession, trace_id: str | None = None) -> None:
        policy = self._session_loop_log_policy()
        if not policy.get("enabled"):
            return
        level = SESSION_LOOP_LOG_LEVELS.get(str(policy.get("level") or "info"), logging.INFO)
        if not logger.isEnabledFor(level):
            return

        payload: dict[str, Any] = {
            "contract": SESSION_LOOP_LOG_EVENT_VERSION,
            "event": event,
            "session_id": session.session_id,
            "module_id": session.module_id,
            "trace_id": trace_id,
            "turn_counter": session.turn_counter,
            "current_scene_id": session.current_scene_id,
            "history_len": len(session.history),
            "diagnostics_len": len(session.diagnostics),
            "authority_version": self._authority_version,
            "authority_applied_at_iso": self._authority_applied_at_iso,
        }
        if policy.get("include_runtime_world_summary"):
            payload["runtime_world"] = self._runtime_world_summary(session.runtime_world)
        if policy.get("include_projection_summary"):
            payload["runtime_projection"] = self._runtime_projection_summary(session.runtime_projection)
        if policy.get("include_diagnostic_summary"):
            latest_diag = session.diagnostics[-1] if session.diagnostics else None
            payload["latest_diagnostic"] = {
                "event_type": latest_diag.get("event_type") if isinstance(latest_diag, dict) else None,
                "turn_kind": latest_diag.get("turn_kind") if isinstance(latest_diag, dict) else None,
                "status": latest_diag.get("status") if isinstance(latest_diag, dict) else None,
            }
        logger.log(level, "story_session_loop_event %s", json.dumps(payload, sort_keys=True, default=str))

    def _compose_runtime_truth_surface(self, *, governed: bool) -> dict[str, Any]:
        """Describe the *active* runtime lane for operator diagnostics.

        Unlike the top-level governance fields on ``runtime_config_status()``,
        which describe the governed configuration state, this block describes
        what is actually running: the authority source, the generation and
        graph modes, the active route family, the live validator lane, and
        the commit / schema contract versions. Each key answers one operator
        question directly; nothing here reports loaded or preview state.
        """
        langgraph_available = True
        langgraph_import_error: str | None = None
        try:
            from ai_stack.langgraph.langgraph_runtime import LANGGRAPH_IMPORT_ERROR

            if LANGGRAPH_IMPORT_ERROR is not None:
                langgraph_available = False
                langgraph_import_error = type(LANGGRAPH_IMPORT_ERROR).__name__
        except Exception as exc:  # pragma: no cover — defensive
            langgraph_available = False
            langgraph_import_error = type(exc).__name__

        graph = self.turn_graph
        graph_executor_class = type(graph).__name__ if graph is not None else None
        runtime_graph_mode = (
            "langgraph_runtime_turn_graph" if graph_executor_class == "RuntimeTurnGraphExecutor" else
            "injected_test_graph" if graph is not None else
            "no_graph"
        )

        cfg = self._governed_runtime_config if isinstance(self._governed_runtime_config, dict) else {}
        raw_gen_mode = str(cfg.get("generation_execution_mode") or "").strip().lower()
        generation_execution_mode = raw_gen_mode or ("governed_default_mock_only" if governed else "unknown")
        expected_live_route_family = "narrative_live_generation_global"
        routes = cfg.get("routes") if isinstance(cfg.get("routes"), list) else []
        active_route_ids = sorted(
            {
                str(r.get("route_id") or "").strip()
                for r in routes
                if isinstance(r, dict) and str(r.get("route_id") or "").strip()
            }
        )
        expected_route_available = expected_live_route_family in active_route_ids

        authority_source = (
            "governed_resolved_runtime_config" if governed else
            ("blocked_no_authoritative_config" if self._runtime_config_status.get("live_execution_blocked") else "injected_test_components")
        )

        # Prompt-template source — which catalog produced the live prompt.
        prompt_template_source = "unknown"
        prompt_template_fallback = False
        try:
            from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog  # noqa: F401

            prompt_template_source = "canonical_prompt_catalog"
        except Exception:
            prompt_template_source = "hardcoded_bridges_fallback"
            prompt_template_fallback = True

        return {
            "authority_source": authority_source,
            "authority_version": self._authority_version,
            "authority_applied_at_iso": self._authority_applied_at_iso,
            "runtime_graph_mode": runtime_graph_mode,
            "graph_executor_class": graph_executor_class,
            "langgraph_available": langgraph_available,
            "langgraph_import_error_class": langgraph_import_error,
            "generation_execution_mode": generation_execution_mode,
            "expected_live_route_family": expected_live_route_family,
            "expected_live_route_available": expected_route_available,
            "active_route_ids": active_route_ids,
            "prompt_template_source": prompt_template_source,
            "prompt_template_fallback_in_effect": prompt_template_fallback,
            "commit_contract_version": "story_narrative_commit_record.v4",
            "runtime_output_schema_version": "runtime_turn_structured_output_v2",
            "live_player_governance_enforced": self._live_governance_enforced_for_player_paths(),
            "module_scope_advertised": f"module_specific_{GOD_OF_CARNAGE_MODULE_ID}_only",
            "module_scope_truth": _module_scope_truth(),
            # The canonical live validator lane. The operator endpoint
            # POST /internal/narrative/runtime/validate-and-recover is a
            # separate introspection lane (it reports
            # validator_lane="operator_introspection_validate_and_recover")
            # and is deliberately not part of the live player-turn path.
            "live_validator_lane": "goc_rule_engine_v1",
            "live_validator_stages": [
                "run_validation_seam",
                "dramatic_effect_gate",
                "decide_playability_recovery",
                "self_correction_loop",
            ],
            "operator_introspection_validator_endpoint": "/api/internal/narrative/runtime/validate-and-recover",
            "truth_surface_note": (
                "These fields describe the active live runtime lane. Loaded package "
                "or preview state is not live authority; see "
                "/api/internal/narrative/runtime/state for loader state."
            ),
        }

    def _live_governance_enforced_for_player_paths(self) -> bool:
        # Escape hatch removed: governance always enforced except for test injection paths
        src = str(self._runtime_config_status.get("source") or "")
        if (
            os.getenv("FLASK_ENV") == "test"
            and self.turn_graph is not None
            and not isinstance(self.turn_graph, RuntimeTurnGraphExecutor)
        ):
            return False
        return not src.startswith("injected")

    def _assert_live_player_governance(self) -> None:
        if not self._live_governance_enforced_for_player_paths():
            return
        st = self._runtime_config_status
        src = str(st.get("source") or "")
        governed = src in {"governed_runtime_config", "governed_runtime_config_with_injected_adapters"}
        if st.get("live_execution_blocked") or not governed:
            raise LiveStoryGovernanceError(
                f"LIVE_STORY_RUNTIME_BLOCKED: runtime_source={src!r} live_execution_blocked={st.get('live_execution_blocked')!r}"
            )
        if not str(st.get("config_version") or "").strip():
            raise LiveStoryGovernanceError("LIVE_STORY_RUNTIME_BLOCKED: config_version is missing on governed runtime surface.")

    @staticmethod
    def _extract_actor_lane_context(session: StorySession) -> dict[str, Any] | None:
        """Extract MVP2 actor-lane enforcement context from session runtime_projection.

        Returns a dict with human_actor_id and ai_forbidden_actor_ids when the
        session's runtime_projection includes actor ownership (set by the backend
        when creating a solo story session with a selected_player_role).
        Returns None when actor ownership is absent (non-solo or legacy sessions).
        """
        proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
        human_actor_id = str(proj.get("human_actor_id") or "").strip()
        if not human_actor_id:
            return None
        npc_actor_ids = proj.get("npc_actor_ids")
        ai_forbidden = sorted(expand_goc_actor_id_aliases(human_actor_id))
        ai_allowed_set: set[str] = set()
        for actor_id in (npc_actor_ids or []):
            if isinstance(actor_id, str) and actor_id.strip():
                ai_allowed_set.update(expand_goc_actor_id_aliases(actor_id))
        ai_allowed = sorted(ai_allowed_set)
        npc_ids = [str(x).strip() for x in (npc_actor_ids or []) if isinstance(x, str) and str(x).strip()]
        return {
            "human_actor_id": human_actor_id,
            "ai_forbidden_actor_ids": ai_forbidden,
            "ai_allowed_actor_ids": ai_allowed,
            "npc_actor_ids": npc_ids,
            "selected_player_role": str(proj.get("selected_player_role") or "").strip(),
            "actor_lanes": proj.get("actor_lanes") or {},
        }


__all__ = ["_SessionLoopGovernanceMixin"]
