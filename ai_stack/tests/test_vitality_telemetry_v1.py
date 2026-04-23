"""Phase 5 vitality telemetry schema and semantics tests."""

from __future__ import annotations

from ai_stack.actor_survival_telemetry import build_actor_survival_telemetry
from ai_stack.runtime_turn_contracts import VITALITY_TELEMETRY_REQUIRED_FIELDS, VITALITY_TELEMETRY_SCHEMA_VERSION


def _base_state() -> dict:
    return {
        "turn_number": 7,
        "trace_id": "trace-v1",
        "raw_input": "...",
        "selected_responder_set": [
            {"actor_id": "veronique_vallon", "role": "primary_responder", "preferred_reaction_order": 0},
            {"actor_id": "michel_longstreet", "role": "secondary_reactor", "preferred_reaction_order": 1},
        ],
        "responder_id": "veronique_vallon",
        "secondary_responder_ids": ["michel_longstreet"],
        "spoken_lines": [
            {"speaker_id": "veronique_vallon", "text": "No."},
            {"speaker_id": "michel_longstreet", "text": "Listen."},
        ],
        "action_lines": [{"actor_id": "veronique_vallon", "text": "leans forward"}],
        "initiative_events": [{"actor_id": "michel_longstreet", "type": "interrupt", "target_id": "veronique_vallon"}],
        "generation": {
            "metadata": {
                "structured_output": {
                    "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "No."}],
                    "action_lines": [{"actor_id": "veronique_vallon", "text": "leans forward"}],
                    "initiative_events": [{"actor_id": "michel_longstreet", "type": "interrupt", "target_id": "veronique_vallon"}],
                }
            }
        },
        "visible_output_bundle": {
            "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "No."}],
            "action_lines": [{"actor_id": "veronique_vallon", "text": "leans forward"}],
        },
        "pacing_mode": "thin_edge",
        "silence_brevity_decision": {"mode": "withheld"},
        "prior_planner_truth": {"carry_forward_tension_notes": "unresolved accusation"},
        "quality_class": "degraded",
        "degradation_signals": ["fallback_used", "retry_exhausted"],
    }


def test_vitality_telemetry_v1_contains_required_fields():
    telemetry = build_actor_survival_telemetry(
        _base_state(),
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=True,
    )
    vitality = telemetry["vitality_telemetry_v1"]
    assert vitality["schema_version"] == VITALITY_TELEMETRY_SCHEMA_VERSION
    missing = [field for field in VITALITY_TELEMETRY_REQUIRED_FIELDS if field not in vitality]
    assert not missing, f"Missing required vitality telemetry fields: {missing}"


def test_selected_realized_rendered_semantics_distinct_and_initiative_only_not_realized():
    state = _base_state()
    # Make secondary appear only in initiative; it should not be counted as realized actor.
    state["generation"]["metadata"]["structured_output"]["spoken_lines"] = [
        {"speaker_id": "veronique_vallon", "text": "No."}
    ]
    state["generation"]["metadata"]["structured_output"]["action_lines"] = [
        {"actor_id": "veronique_vallon", "text": "leans forward"}
    ]
    state["visible_output_bundle"]["spoken_lines"] = [{"speaker_id": "veronique_vallon", "text": "No."}]
    state["visible_output_bundle"]["action_lines"] = [{"actor_id": "veronique_vallon", "text": "leans forward"}]

    telemetry = build_actor_survival_telemetry(
        state,
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=False,
    )
    vitality = telemetry["vitality_telemetry_v1"]

    assert vitality["selected_secondary_responder_ids"] == ["michel_longstreet"]
    assert "michel_longstreet" not in vitality["realized_actor_ids"]
    assert vitality["realized_secondary_responder_ids"] == []
    assert vitality["rendered_actor_ids"] == ["veronique_vallon"]
    assert vitality["preferred_reaction_order_ids"] == ["veronique_vallon", "michel_longstreet"]
    assert vitality["reaction_order_divergence"] == "secondary_responder_nominated_not_realized_in_output"


def test_stage_counts_do_not_mix_and_quality_distinction_is_visible():
    state = _base_state()
    state["quality_class"] = "weak_but_legal"
    state["degradation_signals"] = ["weak_signal_accepted"]
    state["visible_output_bundle"]["spoken_lines"] = []

    telemetry = build_actor_survival_telemetry(
        state,
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=False,
    )
    vitality = telemetry["vitality_telemetry_v1"]

    assert vitality["generated_spoken_line_count"] >= vitality["validated_spoken_line_count"]
    assert vitality["rendered_spoken_line_count"] <= vitality["validated_spoken_line_count"]
    assert vitality["quality_class"] == "weak_but_legal"
    assert "weak_signal_accepted" in vitality["degradation_signals"]
    assert vitality["fallback_used"] is False


def test_sparse_input_recovery_applied_when_sparse_input_still_gets_response():
    state = _base_state()
    state["raw_input"] = "no"
    state["visible_output_bundle"]["spoken_lines"] = [{"speaker_id": "veronique_vallon", "text": "No."}]

    telemetry = build_actor_survival_telemetry(
        state,
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=False,
    )
    vitality = telemetry["vitality_telemetry_v1"]

    assert vitality["sparse_input_detected"] is True
    assert vitality["response_present"] is True
    assert vitality["sparse_input_recovery_applied"] is True
