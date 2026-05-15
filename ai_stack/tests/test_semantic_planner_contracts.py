"""Contract serialization and schema bounds for semantic planner records."""

from __future__ import annotations

import pytest

from ai_stack.character_mind_contract import CharacterMindRecord, FieldProvenance
from ai_stack.scene_plan_contract import ScenePlanRecord
from ai_stack.semantic_move_contract import (
    InterpretationTraceItem,
    RankedMoveCandidate,
    SemanticMoveRecord,
    SubtextRecord,
    SUBTEXT_FUNCTIONS,
    SUBTEXT_HIDDEN_INTENT_HYPOTHESES,
    SUBTEXT_SURFACE_MODES,
)
from ai_stack.social_state_contract import SocialStateRecord


def test_semantic_move_record_roundtrip_json() -> None:
    r = SemanticMoveRecord(
        move_type="direct_accusation",
        social_move_family="attack",
        target_actor_hint="michel_longstreet",
        directness="direct",
        pressure_tactic="blame_assignment",
        scene_risk_band="high",
        interpretation_trace=[
            InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:x"),
        ],
        interpreter_kind="narrative",
        feature_snapshot={"syn_accusation": True},
        ranked_move_candidates=[
            RankedMoveCandidate(
                move_type="direct_accusation",
                social_move_family="attack",
                directness="direct",
                pressure_tactic="blame_assignment",
                scene_risk_band="high",
                rank=1,
                confidence=0.91,
                trace_detail="rule:accusation_synset",
            )
        ],
        secondary_move_type=None,
        secondary_dramatic_features=["carry_forward_blame_pressure"],
        subtext=SubtextRecord(
            surface_mode="accusation",
            explicit_intent="accuse",
            hidden_intent_hypothesis="force_accountability",
            subtext_function="force_accountability",
            sincerity_band="high",
            evidence_codes=["rule:accusation_synset"],
            policy_rule_id="direct_accusation",
        ),
    )
    d = r.to_runtime_dict()
    r2 = SemanticMoveRecord.model_validate(d)
    assert r2.move_type == "direct_accusation"
    assert r2.ranked_move_candidates
    assert r2.subtext is not None
    assert r2.subtext.subtext_function in SUBTEXT_FUNCTIONS


def test_subtext_record_roundtrip_and_contract_sets() -> None:
    surface_mode = sorted(SUBTEXT_SURFACE_MODES)[0]
    hidden_intent = sorted(SUBTEXT_HIDDEN_INTENT_HYPOTHESES)[0]
    subtext_function = sorted(SUBTEXT_FUNCTIONS)[0]
    record = SubtextRecord(
        surface_mode=surface_mode,
        explicit_intent="contract_probe",
        hidden_intent_hypothesis=hidden_intent,
        subtext_function=subtext_function,
        sincerity_band="unknown",
        evidence_codes=["contract:set_member"],
    )
    roundtrip = SubtextRecord.model_validate(record.model_dump(mode="json"))
    assert roundtrip.surface_mode == surface_mode
    assert roundtrip.hidden_intent_hypothesis == hidden_intent
    assert roundtrip.subtext_function == subtext_function


def test_semantic_move_record_rejects_unknown_move_type() -> None:
    invalid_move_type = f"invalid_{sorted(SUBTEXT_FUNCTIONS)[0]}"
    with pytest.raises(ValueError):
        SemanticMoveRecord(
            move_type=invalid_move_type,
            social_move_family="neutral",
            directness="ambiguous",
            scene_risk_band="low",
        )


def test_social_state_record_roundtrip() -> None:
    s = SocialStateRecord(
        prior_continuity_classes=["blame_pressure"],
        scene_pressure_state="high_blame",
        active_thread_count=2,
        thread_pressure_summary_present=True,
        guidance_phase_key="phase_2_moral_negotiation",
        responder_asymmetry_code="blame_on_host_spouse_axis",
        social_risk_band="high",
    )
    SocialStateRecord.model_validate(s.to_runtime_dict())


def test_character_mind_record_provenance() -> None:
    m = CharacterMindRecord(
        character_key="veronique",
        runtime_actor_id="veronique_vallon",
        formal_role_label="Host",
        tactical_posture="defend_civility_principles",
        pressure_response_bias="civility_first",
        provenance={
            "formal_role_label": FieldProvenance(source="authored"),
            "tactical_posture": FieldProvenance(source="authored_derived", derivation_key="map_formal_role_to_tactical"),
        },
    )
    CharacterMindRecord.model_validate(m.to_runtime_dict())


def test_scene_plan_record_roundtrip() -> None:
    p = ScenePlanRecord(
        selected_scene_function="probe_motive",
        selected_responder_set=[{"actor_id": "annette_reille", "reason": "yaml"}],
        pacing_mode="standard",
        silence_brevity_decision={"mode": "normal", "reason": "default"},
        planner_rationale_codes=["semantic_pipeline_v1"],
        semantic_move_fingerprint="abc123",
        social_state_fingerprint="def456",
        selection_source="semantic_pipeline_v1",
    )
    ScenePlanRecord.model_validate(p.to_runtime_dict())
