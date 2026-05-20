"""Opening fallback observability.

Records diagnostics for fallback opening output so startup failures remain inspectable and player-safe.
"""
from __future__ import annotations

from ._deps import *

class _OpeningFallbackObservabilityMixin:
    def _ldss_opening_fallback_state(
        self,
        graph_state: dict[str, Any],
        *,
        reason: str,
    ) -> dict[str, Any]:
        fallback = dict(graph_state)
        generation = dict(fallback.get("generation") if isinstance(fallback.get("generation"), dict) else {})
        metadata = dict(generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {})
        # Capture primary attempt before LDSS overwrites adapter metadata so operators can
        # tell from trace metadata: primary live route was attempted (e.g. openai
        # gpt-5-mini), it failed (dramatic-effect rejection / no visible narration),
        # the FINAL committed adapter is ldss_fallback. ADR-0033 §13.10.
        prior_adapter = str(metadata.get("adapter") or "").strip()
        primary_metadata: dict[str, Any] = {}
        if prior_adapter and prior_adapter not in {"ldss_fallback", "ldss_deterministic", ""}:
            primary_metadata["primary_attempt_adapter"] = prior_adapter
            prior_model = metadata.get("model")
            if prior_model:
                primary_metadata["primary_attempt_model"] = prior_model
            prior_mode = metadata.get("adapter_invocation_mode")
            if prior_mode:
                primary_metadata["primary_attempt_invocation_mode"] = prior_mode
        routing_state = (
            graph_state.get("routing")
            if isinstance(graph_state.get("routing"), dict)
            else {}
        )
        prior_provider = routing_state.get("selected_provider")
        if prior_provider and "primary_attempt_provider" not in primary_metadata:
            primary_metadata["primary_attempt_provider"] = prior_provider
        prior_selected_model = routing_state.get("selected_model")
        if prior_selected_model and "primary_attempt_selected_model" not in primary_metadata:
            primary_metadata["primary_attempt_selected_model"] = prior_selected_model
        # PRIMARY-PARSER-EVIDENCE-01: pull parser/raw-output evidence from the state key
        # captured in _invoke_model. This survives self-correction overwriting generation.
        pae = graph_state.get("primary_attempt_evidence")
        if isinstance(pae, dict):
            for _k in (
                "primary_attempt_api_success",
                "primary_attempt_parser_error_present",
                "primary_attempt_parser_error",
                "primary_attempt_structured_output_present",
                "primary_attempt_raw_output_sha256",
                "primary_attempt_raw_output_excerpt",
            ):
                if _k in pae:
                    primary_metadata[_k] = pae[_k]
        # Self-correction evidence: attempt_count / final model tried.
        sc = graph_state.get("self_correction")
        if isinstance(sc, dict):
            sc_attempts = sc.get("attempts") or []
            primary_metadata["self_correction_attempted"] = bool(sc_attempts)
            primary_metadata["self_correction_attempt_count"] = len(sc_attempts)
            if sc_attempts:
                first_sc = sc_attempts[0] if isinstance(sc_attempts[0], dict) else {}
                last_sc = sc_attempts[-1] if isinstance(sc_attempts[-1], dict) else {}
                primary_metadata["self_correction_trigger_source"] = first_sc.get("trigger_source")
                primary_metadata["runtime_aspect_failure_before_retry"] = first_sc.get(
                    "runtime_aspect_failure_before_retry"
                )
                primary_metadata["capability_failure_before_retry"] = first_sc.get(
                    "capability_failure_before_retry"
                )
                primary_metadata["self_correction_resolved_failure"] = any(
                    bool(item.get("resolved_failure"))
                    for item in sc_attempts
                    if isinstance(item, dict)
                )
                primary_metadata["self_correction_model"] = last_sc.get("candidate_model")
                primary_metadata["self_correction_success"] = (
                    bool(last_sc.get("success")) and not last_sc.get("parser_error")
                )
            else:
                primary_metadata["self_correction_resolved_failure"] = False
                primary_metadata["self_correction_success"] = False
        fallback["force_ldss_scene_fallback"] = True
        fallback["generation"] = {
            **generation,
            "success": True,
            "error": None,
            "fallback_used": True,
            "metadata": {
                **metadata,
                **primary_metadata,
                "adapter": "ldss_fallback",
                "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
                "final_adapter": "ldss_fallback",
                "final_adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
                "fallback_reason": reason,
                "ldss_fallback_after_live_opening_failure": True,
                "structured_output": None,
                "live_opening_failure_reason": reason,
            },
        }
        prior_val = (
            graph_state.get("validation_outcome")
            if isinstance(graph_state.get("validation_outcome"), dict)
            else {}
        )
        prior_lane: dict[str, Any] = {}
        nested_lane = prior_val.get("actor_lane_validation")
        if isinstance(nested_lane, dict) and nested_lane:
            prior_lane = dict(nested_lane)
        elif isinstance(graph_state.get("actor_lane_validation"), dict) and graph_state.get(
            "actor_lane_validation"
        ):
            # Graph may publish actor lane on state root as well as under validation_outcome.
            top_lane = graph_state.get("actor_lane_validation")
            if isinstance(top_lane, dict) and top_lane:
                prior_lane = dict(top_lane)
        opening_fallback_validation: dict[str, Any] = {
            "status": "approved",
            "reason": "ldss_fallback_after_live_opening_failure",
            "validator_lane": "opening_fallback_policy_v1",
            "live_opening_failure_reason": reason,
        }
        if prior_lane:
            opening_fallback_validation["actor_lane_validation"] = prior_lane
        fallback["validation_outcome"] = opening_fallback_validation
        fallback["committed_result"] = {
            "commit_applied": True,
            "committed_effects": [
                {
                    "effect_type": "opening_fallback",
                    "description": "LDSS fallback opening used after live opening failed validation.",
                }
            ],
            "reason": "ldss_fallback_after_live_opening_failure",
        }
        fallback_ledger = initialize_runtime_aspect_ledger(
            session_id=str(graph_state.get("session_id") or ""),
            module_id=str(graph_state.get("module_id") or GOD_OF_CARNAGE_MODULE_ID),
            turn_number=int(graph_state.get("turn_number") or 0),
            turn_kind=str(graph_state.get("turn_input_class") or "opening"),
            raw_player_input=None,
            input_kind="opening_fallback",
            trace_id=str(graph_state.get("trace_id") or "") or None,
            runtime_profile_id=str(graph_state.get("runtime_profile_id") or "") or None,
        )
        fallback_ledger = set_aspect_record(
            fallback_ledger,
            ASPECT_VALIDATION,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={"ldss_opening_fallback_policy": True},
                actual={
                    "validation_status": "approved",
                    "reason": "ldss_fallback_after_live_opening_failure",
                    "live_opening_failure_reason": reason,
                },
                reasons=["ldss_fallback_after_live_opening_failure"],
                source="opening_fallback_policy",
            ),
        )
        fallback_ledger = set_aspect_record(
            fallback_ledger,
            ASPECT_COMMIT,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={"commit_allowed_after_opening_fallback": True},
                actual={
                    "commit_applied": True,
                    "reason": "ldss_fallback_after_live_opening_failure",
                },
                reasons=["ldss_fallback_after_live_opening_failure"],
                source="opening_fallback_policy",
            ),
        )
        fallback["turn_aspect_ledger"] = fallback_ledger
        fallback["visible_output_bundle"] = {}
        fallback["quality_class"] = QUALITY_CLASS_DEGRADED
        signals = list(fallback.get("degradation_signals") or [])
        if "ldss_fallback_after_live_opening_failure" not in signals:
            signals.append("ldss_fallback_after_live_opening_failure")
        fallback["degradation_signals"] = signals
        fallback["degradation_summary"] = reason
        return fallback

    def _emit_observability_path_for_event(
        self,
        *,
        session: StorySession,
        graph_state: dict[str, Any],
        event: dict[str, Any],
    ) -> None:
        """Langfuse path summary and evidence hooks for any turn-shaped event (ADR-0038 Phase C)."""
        path_summary = _build_langfuse_path_summary(
            session=session,
            graph_state=graph_state,
            event=event,
        )
        # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P4: build public
        # action/local-context diagnostics so degraded/fallback paths still expose numeric
        # values rather than silent None.
        diag = _compute_action_consequence_diagnostics(path_summary)
        path_summary["action_consequence_diagnostics"] = diag
        event["observability_path_summary"] = path_summary
        event["action_consequence_diagnostics"] = diag
        event["knowledge_runtime_gates"] = {
            "contract": path_summary.get("knowledge_runtime_gates_contract"),
            "opening_scene_sequence_id": path_summary.get("opening_scene_sequence_id"),
            "opening_event_coverage_pass": path_summary.get("opening_event_coverage_pass"),
            "opening_missing_event_ids": path_summary.get("opening_missing_event_ids"),
            "opening_missing_must_establish": path_summary.get("opening_missing_must_establish"),
            "hard_forbidden_absent": path_summary.get("hard_forbidden_absent"),
            "opening_summary_only_absent": path_summary.get("opening_summary_only_absent"),
            "hard_forbidden_detection": path_summary.get("hard_forbidden_detection"),
        }
        _emit_langfuse_path_spans(path_summary)
        _emit_langfuse_runtime_aspect_observability(path_summary)
        _emit_langfuse_evidence_observations(
            path_summary=path_summary,
            graph_state=graph_state,
            event=event,
        )

    @staticmethod
    def _w5_ast_narrator_projection_enabled() -> bool:
        """ADR-0063 narrator-projection flag (default-on as of Phase 6B-1).

        Returns True when unset/empty: narrator composition consumes the
        typed W5 projection as a primary actor-situation input while the
        legacy ``transition_from_previous`` block remains as fallback.
        Explicit opt-out is preserved — setting the env var to
        ``0/false/no/off`` restores Phase 1 behavior (no ``w5_projection`` in
        narrator ``source_facts``).
        """

        raw = (os.environ.get("W5_AST_NARRATOR_PROJECTION_ENABLED") or "").strip().lower()
        if raw in {"0", "false", "no", "off"}:
            return False
        return True


__all__ = ["_OpeningFallbackObservabilityMixin"]
