"""Tests for operator turn-history vitality/passivity diagnostics."""

from __future__ import annotations

from ai_stack.npc_agency_contracts import NPC_AGENCY_CLAIM_BOUNDED_RUNTIME_STATUS
from app.services.operator_turn_history_service import (
    build_turn_history_summary_for_session,
    operator_diagnostics_surface,
)


def _event(
    turn_number: int,
    *,
    quality_class: str,
    degraded_signals: list[str],
    response_present: bool,
    fallback_used: bool,
    observability_path_summary: dict | None = None,
) -> dict:
    return {
        "turn_number": turn_number,
        "turn_kind": "player",
        "trace_id": f"trace-{turn_number}",
        "runtime_governance_surface": {
            "quality_class": quality_class,
            "degradation_signals": degraded_signals,
        },
        "actor_survival_telemetry": {
            "vitality_telemetry_v1": {
                "schema_version": "vitality_telemetry_v1",
                "selected_primary_responder_id": "annette_reille",
                "selected_secondary_responder_ids": ["michel_longstreet"],
                "realized_actor_ids": ["annette_reille"] if response_present else [],
                "realized_secondary_responder_ids": [],
                "rendered_actor_ids": ["annette_reille"] if response_present else [],
                "generated_spoken_line_count": 1,
                "validated_spoken_line_count": 1,
                "rendered_spoken_line_count": 1 if response_present else 0,
                "generated_action_line_count": 0,
                "validated_action_line_count": 0,
                "rendered_action_line_count": 0,
                "initiative_generated_count": 1,
                "initiative_preserved_count": 1,
                "initiative_seizer_id": "annette_reille",
                "initiative_loser_id": "veronique_vallon",
                "initiative_pressure_label": "contested",
                "quality_class": quality_class,
                "degradation_signals": degraded_signals,
                "fallback_used": fallback_used,
                "degraded_commit": False,
                "retry_exhausted": "retry_exhausted" in degraded_signals,
                "response_present": response_present,
                "initiative_present": True,
                "multi_actor_realized": False,
                "thin_edge_applied": True,
                "withheld_applied": True,
                "compressed_applied": False,
                "prior_tension_present": True,
                "sparse_input_detected": True,
                "sparse_input_recovery_applied": response_present,
                "generated_ok": True,
                "validation_ok": True,
                "commit_applied": True,
            },
            "operator_diagnostic_hints": {
                "hints": ["No visible actor-lane response reached render output."] if not response_present else [],
                "actor_agency_level": "narration_only" if not response_present else "full_actor_agency",
                "why_turn_felt_passive": ["single_actor_only", "thin_edge_withheld"] if not response_present else [],
                "primary_passivity_factors": ["single_actor_only"] if not response_present else [],
            },
        },
        "observability_path_summary": observability_path_summary or {},
    }


def test_turn_history_row_contains_passivity_explainability_fields():
    summary = build_turn_history_summary_for_session(
        [
            _event(1, quality_class="degraded", degraded_signals=["fallback_used"], response_present=False, fallback_used=True)
        ]
    )
    assert summary["turn_history_version"] == "2.0"
    row = summary["rows"][0]
    assert row["schema_version"] == "vitality_telemetry_v1"
    assert row["quality_class"] == "degraded"
    assert row["degradation_signals"] == ["fallback_used"]
    assert isinstance(row["why_turn_felt_passive"], list)
    assert isinstance(row["primary_passivity_factors"], list)
    assert isinstance(row["vitality_breakdown"], dict)
    assert row["npc_agency_breakdown"]["claim_readiness"]["claim_status"] == NPC_AGENCY_CLAIM_BOUNDED_RUNTIME_STATUS


def test_turn_history_row_includes_read_only_adr0041_readiness_echo():
    event = _event(
        1,
        quality_class="healthy",
        degraded_signals=[],
        response_present=True,
        fallback_used=False,
    )
    event["turn_aspect_ledger"] = {
        "runtime_intelligence_projection": {
            "readiness_policy_input": {"readiness_input": "allow"},
            "readiness_aggregation_decision": {"aggregated_readiness": "allow"},
            "readiness_co_authority_enforcement": {"readiness_input": "no_decision"},
        }
    }
    summary = build_turn_history_summary_for_session([event])
    row = summary["rows"][0]
    echo = row["adr0041_readiness_projection_echo"]
    assert echo["read_only"] is True
    assert echo["readiness_aggregation_decision"]["aggregated_readiness"] == "allow"
    diagnostics = []
    for turn in range(1, 11):
        degraded = turn > 5
        diagnostics.append(
            _event(
                turn,
                quality_class="degraded" if degraded else "healthy",
                degraded_signals=["fallback_used"] if degraded else [],
                response_present=degraded,
                fallback_used=degraded,
            )
        )
    summary = build_turn_history_summary_for_session(diagnostics)
    assert summary["rising_degraded_posture"] is True


def test_operator_surface_exposes_top_passivity_factors_and_actions():
    surface = operator_diagnostics_surface(
        [
            _event(1, quality_class="degraded", degraded_signals=["fallback_used", "retry_exhausted"], response_present=False, fallback_used=True),
            _event(2, quality_class="healthy", degraded_signals=[], response_present=True, fallback_used=False),
        ]
    )
    assert surface["diagnostics_version"] == "2.0"
    assert "top_passivity_factors" in surface
    assert isinstance(surface["top_passivity_factors"], list)
    assert "operator_actions" in surface
    assert isinstance(surface["operator_actions"], list)
    assert "vitality_breakdown" in surface


def test_turn_history_row_surfaces_intent_surface_evidence_from_path_summary():
    from ai_stack.goc_subtext_policy import rule_spec_for_subtext

    rule = rule_spec_for_subtext("direct_accusation")
    summary = build_turn_history_summary_for_session(
        [
            _event(
                1,
                quality_class="healthy",
                degraded_signals=[],
                response_present=True,
                fallback_used=False,
                observability_path_summary={
                    "player_input_kind": "action",
                    "narrator_response_expected": True,
                    "npc_response_expected": False,
                    "semantic_move_kind": "move_to_room",
                    "scene_director_selection_source": "intent_surface",
                    "planner_rationale_codes": ["player_action_requires_spatial_consequence"],
                    "subtext_surface_mode": rule["surface_mode"],
                    "subtext_hidden_intent_hypothesis": rule["hidden_intent_hypothesis"],
                    "subtext_function": rule["subtext_function"],
                    "subtext_sincerity_band": rule["sincerity_band"],
                    "subtext_policy_rule_id": "direct_accusation",
                    "intent_surface_contract_pass": 1,
                    "subtext_contract_pass": 1,
                    "player_input_attribution_pass": 1,
                    "semantic_move_alignment_pass": 1,
                    "npc_action_narration_boundary_pass": 1,
                },
            )
        ]
    )
    row = summary["rows"][0]
    intent = row["intent_surface_evidence"]
    assert intent["player_input_kind"] == "action"
    assert intent["semantic_move_kind"] == "move_to_room"
    assert intent["scene_director_selection_source"] == "intent_surface"
    assert intent["planner_rationale_codes"] == ["player_action_requires_spatial_consequence"]
    assert intent["subtext_surface_mode"] == rule["surface_mode"]
    assert intent["subtext_hidden_intent_hypothesis"] == rule["hidden_intent_hypothesis"]
    assert intent["subtext_function"] == rule["subtext_function"]
    assert intent["subtext_sincerity_band"] == rule["sincerity_band"]
    assert intent["subtext_policy_rule_id"] == "direct_accusation"
    assert intent["intent_surface_contract_pass"] == 1
    assert intent["subtext_contract_pass"] == 1
