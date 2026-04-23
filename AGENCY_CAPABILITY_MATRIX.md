# Runtime Agency Capability Matrix (Evidence-Backed)

This matrix describes implemented runtime agency behavior using only committed telemetry fields and executable test evidence.

## Capability: Actor-Level Generation
- Support level: Supported
- Telemetry fields: `selected_primary_responder_id`, `generated_spoken_line_count`, `generated_action_line_count`, `generated_actor_ids`
- Proving tests:
  - `ai_stack/tests/test_vitality_telemetry_v1.py::test_vitality_telemetry_v1_contains_required_fields`
  - `ai_stack/tests/test_wave1_closure_actor_contract.py::test_telemetry_reads_speaker_id_not_responder_id`
- Known limits:
  - Model fallback path may reduce dramatic richness even when actor lanes are present.

## Capability: Actor-Level Commit Truth
- Support level: Supported
- Telemetry fields: `commit_applied`, `quality_class`, `degradation_signals`, `initiative_preserved_count`
- Proving tests:
  - `world-engine/tests/test_story_runtime_narrative_commit.py::test_get_state_exposes_actor_turn_summary_fields`
  - `world-engine/tests/test_story_runtime_narrative_commit.py::test_execute_turn_propagates_vitality_telemetry_to_event_and_governance`
- Known limits:
  - Commit truth remains bounded to canonical committed payloads; non-authoritative diagnostics are excluded from commit authority.

## Capability: Selected vs Realized vs Rendered Actor Truth
- Support level: Supported
- Telemetry fields: `selected_secondary_responder_ids`, `realized_actor_ids`, `realized_secondary_responder_ids`, `rendered_actor_ids`
- Proving tests:
  - `ai_stack/tests/test_vitality_telemetry_v1.py::test_selected_realized_rendered_semantics_distinct_and_initiative_only_not_realized`
  - `world-engine/tests/test_story_window_projection.py::test_story_window_projection_includes_vitality_and_passivity_fields`
- Known limits:
  - Initiative-only mention does not count as realized actor unless actor appears in spoken/action lanes.

## Capability: Multi-Actor Realization
- Support level: Supported
- Telemetry fields: `multi_actor_realized`, `realized_actor_ids`, `realized_secondary_responder_ids`
- Proving tests:
  - `ai_stack/tests/test_wave3_multi_actor_vitality.py::test_multi_actor_realized_marker_when_two_actors_in_spoken`
  - `ai_stack/tests/test_wave3_multi_actor_vitality.py::test_multi_actor_render_bundle_carries_realized_actor_ids`
- Known limits:
  - Realization depends on scene pressure and legal validation; nomination is not guaranteed realization.
  - `multi_actor_realized` and the `multi_actor_render` bundle are emitted only on the **committed + approved** primary render branch in `ai_stack/goc_turn_seams.py` (not on live-truth-surface or other staging-only paths).

## Capability: Interruption + Initiative Persistence
- Support level: Supported
- Telemetry fields: `initiative_generated_count`, `initiative_preserved_count`, `initiative_seizer_id`, `initiative_loser_id`, `initiative_pressure_label`
- Proving tests:
  - `ai_stack/tests/test_wave3_multi_actor_vitality.py::test_initiative_pressure_label_contested_on_interrupt`
  - `ai_stack/tests/test_wave3_multi_actor_vitality.py::test_initiative_precedents_line_in_continuity_signal_when_seizer_present`
- Known limits:
  - Initiative persistence is bounded to canonical planner/continuity truth; no free-running scene simulation outside turn boundaries.

## Capability: Sparse-Input Vitality Recovery
- Support level: Supported
- Telemetry fields: `sparse_input_detected`, `sparse_input_recovery_applied`, `response_present`, `thin_edge_applied`, `withheld_applied`
- Proving tests:
  - `ai_stack/tests/test_vitality_telemetry_v1.py::test_sparse_input_recovery_applied_when_sparse_input_still_gets_response`
  - `ai_stack/tests/test_wave3_multi_actor_vitality.py::test_thin_edge_silence_withdrawal_with_prior_tension_upgrades_to_probe_motive`
- Known limits:
  - Some sparse turns can remain intentionally quiet when legality/pacing policy requires restraint.

## Capability: Degraded Path Transparency
- Support level: Supported
- Telemetry fields: `quality_class`, `degradation_signals`, `fallback_used`, `degraded_commit`, `retry_exhausted`
- Proving tests:
  - `frontend/tests/test_routes_extended.py::test_routes_play_normalizes_story_entries_and_runtime_status_view`
  - `backend/tests/services/test_operator_turn_history_service.py::test_turn_history_row_contains_passivity_explainability_fields`
  - `backend/tests/test_operator_diagnostics_routes.py::test_operator_diagnostics_session_surface_shape`
- Known limits:
  - Weak-but-legal turns are non-degraded but still may feel low-energy; this is surfaced explicitly via passivity factors.

## Capability: Passivity Explainability (Operator)
- Support level: Supported
- Telemetry fields: `why_turn_felt_passive`, `primary_passivity_factors`, `vitality_breakdown`
- Proving tests:
  - `backend/tests/services/test_operator_turn_history_service.py::test_operator_surface_exposes_top_passivity_factors_and_actions`
  - `backend/tests/test_operator_diagnostics_routes.py::test_operator_turn_history_endpoint_shape`
- Known limits:
  - Explanations are structured factors, not free-form narrative explanations.
  - Full operator explainability includes `vitality_breakdown` and related structured fields on operator/history APIs; world-engine JSON audit lines intentionally carry **canonical subsets** only (see `world-engine/app/observability/audit_log.py` projections from `VITALITY_TELEMETRY_REQUIRED_FIELDS` and `PASSIVITY_DIAGNOSIS_REQUIRED_FIELDS`).

## Contract Rules
- `vitality_telemetry_v1` is versioned and canonical.
- Stage counts are never mixed: only `generated_*`, `validated_*`, and `rendered_*` are used.
- Capability claims in this matrix must reference existing telemetry fields and executable tests.
- **Operator vs audit:** Operator surfaces are the contract for rich passivity explainability (including `vitality_breakdown` where exposed). Audit logs remain bounded for volume and hygiene; do not assume audit JSON mirrors the full operator payload.
