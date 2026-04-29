# Agency Capability Matrix

This document describes the agency capabilities of the World of Shadows AI stack,
with telemetry field references and proving test citations.

## Capability: Actor Vitality Response

Tracks whether actor responses are present, initiative is exercised, and multiple
actors are realized in a single turn.

- Telemetry fields: `response_present`, `initiative_present`, `multi_actor_realized`
- `ai_stack/tests/test_vitality_telemetry_v1.py::test_vitality_telemetry_v1_contains_required_fields`
- Support level: production

## Capability: Selected and Realized Actor Semantics

Tracks the distinction between selected, realized, and rendered actors across
generation, validation, and rendering pipeline stages.

- Telemetry fields: `selected_primary_responder_id`, `realized_actor_ids`, `rendered_actor_ids`
- `ai_stack/tests/test_vitality_telemetry_v1.py::test_selected_realized_rendered_semantics_distinct_and_initiative_only_not_realized`
- Support level: production

## Capability: Stage Count Separation

Tracks generated, validated, and rendered line counts independently so that
quality distinctions remain visible across pipeline stages.

- Telemetry fields: `generated_spoken_line_count`, `validated_spoken_line_count`, `rendered_spoken_line_count`, `quality_class`
- `ai_stack/tests/test_vitality_telemetry_v1.py::test_stage_counts_do_not_mix_and_quality_distinction_is_visible`
- Support level: production

## Capability: Sparse Input Recovery

Detects and records when sparse input still produces a valid response through
recovery pathways.

- Telemetry fields: `sparse_input_recovery_applied`, `degradation_signals`, `fallback_used`
- `ai_stack/tests/test_vitality_telemetry_v1.py::test_sparse_input_recovery_applied_when_sparse_input_still_gets_response`
- Support level: production

## Capability: Initiative Tracking

Records initiative seizure, loss, pressure label, and preservation counts
so that dramatic pacing can be audited across turns.

- Telemetry fields: `initiative_seizer_id`, `initiative_loser_id`, `initiative_pressure_label`, `initiative_generated_count`, `initiative_preserved_count`
- `ai_stack/tests/test_wave3_multi_actor_vitality.py::test_secondary_responder_has_preferred_reaction_order_sequence`
- Support level: production

## Capability: Degradation and Fallback Tracking

Records degradation signals, fallback usage, degraded commit, and retry
exhaustion to support operational honesty in adverse conditions.

- Telemetry fields: `degraded_commit`, `retry_exhausted`, `degradation_signals`, `fallback_used`
- `ai_stack/tests/test_actor_lane_absence_governance.py::test_run_visible_render_survives_vitality_warning_and_reaction_order_divergence`
- Support level: production
