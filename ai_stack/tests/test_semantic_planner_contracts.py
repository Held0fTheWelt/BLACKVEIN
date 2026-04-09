"""Contract serialization and schema bounds for semantic planner records."""

from __future__ import annotations

from ai_stack.character_mind_contract import CharacterMindRecord, FieldProvenance
from ai_stack.scene_plan_contract import ScenePlanRecord
from ai_stack.semantic_move_contract import InterpretationTraceItem, SemanticMoveRecord
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
    )
    d = r.to_runtime_dict()
    r2 = SemanticMoveRecord.model_validate(d)
    assert r2.move_type == "direct_accusation"


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
