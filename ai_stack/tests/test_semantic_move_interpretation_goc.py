"""Semantic move interpretation: AI semantic payloads, no phrase maps."""

from __future__ import annotations

import pytest

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.goc_subtext_policy import rule_spec_for_subtext, subtext_policy_values
from ai_stack.semantic_move_contract import (
    SUBTEXT_FUNCTIONS,
    SUBTEXT_HIDDEN_INTENT_HYPOTHESES,
    SUBTEXT_SURFACE_MODES,
)
from ai_stack.semantic_move_interpretation_goc import interpret_goc_semantic_move
from story_runtime_core.player_input_intent_contract import (
    FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES,
    QUESTION_PUNCTUATION_PROBE_GUARDED_KINDS,
    default_commit_flags_for_player_input_kind,
    player_input_kind_family,
)


def _base_interp() -> dict:
    return {"kind": "narrative", "intent": "pressure", "confidence": 0.5, "ambiguity": "low"}


def _semantic_move_payload(**overrides: object) -> dict:
    payload = {
        "move_type": "direct_accusation",
        "social_move_family": "attack",
        "directness": "direct",
        "pressure_tactic": "blame_assignment",
        "scene_risk_band": "high",
        "confidence": 0.91,
        "trace_detail": "ai_semantic_move:direct_accusation",
    }
    payload.update(overrides)
    return payload


def test_ai_payload_direct_accusation_is_used_without_phrase_rules() -> None:
    rec = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="Du bist verantwortlich.",
        interpreted_input={**_base_interp(), "semantic_move": _semantic_move_payload()},
        interpreted_move={"player_intent": "accuse", "move_class": "dialogue"},
        prior_continuity_classes=[],
    )

    assert rec.move_type == "direct_accusation"
    assert rec.social_move_family == "attack"
    assert rec.feature_snapshot["semantic_move_ai_present"] is True
    assert rec.feature_snapshot["semantic_move_ai_required"] is False
    assert [step.step_id for step in rec.interpretation_trace] == [
        "normalize_input",
        "read_interpreted_signals",
        "read_ai_semantic_move",
        "emit_record",
    ]


def test_missing_ai_payload_returns_neutral_semantic_required_record() -> None:
    rec = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="Du bist verantwortlich.",
        interpreted_input=_base_interp(),
        interpreted_move={"player_intent": "accuse", "move_class": "dialogue"},
        prior_continuity_classes=[],
    )

    assert rec.move_type == "establish_situational_pressure"
    assert rec.feature_snapshot["semantic_move_ai_present"] is False
    assert rec.feature_snapshot["semantic_move_ai_required"] is True
    assert rec.ranked_move_candidates[0].trace_detail == "semantic_move_ai_required"


def test_explicit_silence_signal_still_has_runtime_fallback() -> None:
    rec = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="",
        interpreted_input={**_base_interp(), "ambiguity": "empty_input"},
        interpreted_move={"player_intent": "silence", "move_class": "dialogue"},
        prior_continuity_classes=[],
    )

    assert rec.move_type == "silence_withdrawal"
    assert rec.feature_snapshot["interpreted_silence_signal"] is True
    assert rec.feature_snapshot["non_lexical_silence_signal"] is True


def test_ranked_semantic_candidates_preserve_primary_and_secondary() -> None:
    rec = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="I'm sorry, but the truth still matters.",
        interpreted_input={
            **_base_interp(),
            "semantic_move": _semantic_move_payload(
                move_type="competing_repair_and_reveal",
                social_move_family="repair",
                directness="ambiguous",
                scene_risk_band="high",
                ranked_move_candidates=[
                    {
                        "move_type": "repair_attempt",
                        "social_move_family": "repair",
                        "directness": "direct",
                        "scene_risk_band": "moderate",
                        "confidence": 0.64,
                        "trace_detail": "ai_semantic_move_candidate:repair",
                    }
                ],
            ),
        },
        interpreted_move={"player_intent": "mixed", "move_class": "dialogue"},
        prior_continuity_classes=["blame_pressure"],
    )

    assert rec.move_type == "competing_repair_and_reveal"
    assert rec.ranked_move_candidates[0].move_type == rec.move_type
    assert rec.secondary_move_type == "repair_attempt"
    assert rec.secondary_dramatic_features == ["secondary_move:repair_attempt"]
    assert rec.subtext is not None
    policy_rule = rule_spec_for_subtext(rec.subtext.policy_rule_id)
    assert rec.subtext.surface_mode == policy_rule["surface_mode"]
    assert rec.subtext.subtext_function == policy_rule["subtext_function"]


def test_perception_question_without_ai_move_is_not_forced_into_probe_inquiry() -> None:
    rec = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="Was sehe ich, wenn ich aus dem Fenster schaue?",
        interpreted_input={
            **_base_interp(),
            "player_input_kind": "perception",
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        },
        interpreted_move={"player_intent": "observe", "move_class": "action"},
        prior_continuity_classes=[],
    )

    assert rec.move_type == "establish_situational_pressure"
    assert rec.feature_snapshot["player_input_kind_is_perception"] is True


@pytest.mark.parametrize("player_input_kind", sorted(QUESTION_PUNCTUATION_PROBE_GUARDED_KINDS))
def test_contract_guarded_question_shapes_do_not_become_npc_probe(player_input_kind: str) -> None:
    flags = default_commit_flags_for_player_input_kind(player_input_kind)
    rec = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="contract-shaped input?",
        interpreted_input={
            **_base_interp(),
            "player_input_kind": player_input_kind,
            **flags,
        },
        interpreted_move={"player_intent": "contract_invariant", "move_class": "action"},
        prior_continuity_classes=[],
    )

    assert rec.move_type not in FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES
    assert rec.feature_snapshot["player_input_kind_question_shape_guarded"] is True
    assert rec.feature_snapshot["player_input_kind_family"] == player_input_kind_family(player_input_kind)


def test_target_actor_hint_comes_from_ai_semantic_payload() -> None:
    rec = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="Begruesse Veronique.",
        interpreted_input={
            **_base_interp(),
            "player_input_kind": "social_nonverbal_action",
            **default_commit_flags_for_player_input_kind("social_nonverbal_action"),
            "semantic_move": _semantic_move_payload(
                move_type="establish_situational_pressure",
                social_move_family="neutral",
                directness="ambiguous",
                scene_risk_band="low",
                target_actor_hint="veronique_vallon",
            ),
        },
        interpreted_move={"player_intent": "social_action", "move_class": "action"},
        prior_continuity_classes=[],
    )

    assert rec.target_actor_hint == "veronique_vallon"


def test_subtext_policy_values_match_contract_sets() -> None:
    assert subtext_policy_values("surface_modes") == SUBTEXT_SURFACE_MODES
    assert subtext_policy_values("hidden_intent_hypotheses") == SUBTEXT_HIDDEN_INTENT_HYPOTHESES
    assert subtext_policy_values("subtext_functions") == SUBTEXT_FUNCTIONS


def test_interpreter_emits_bounded_subtext_record_from_policy() -> None:
    rec = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="I avoid the question and change the subject.",
        interpreted_input={
            **_base_interp(),
            "player_input_kind": "speech",
            "player_action_committed": False,
            "player_speech_committed": True,
            "narrator_response_expected": False,
            "npc_response_expected": True,
            "semantic_move": _semantic_move_payload(
                move_type="evasive_deflection",
                social_move_family="deflect",
                directness="indirect",
                scene_risk_band="moderate",
                trace_detail="ai_semantic_move:evasive_deflection",
            ),
        },
        interpreted_move={"player_intent": "deflect", "move_class": "dialogue"},
        prior_continuity_classes=[],
    )

    assert rec.subtext is not None
    policy_rule = rule_spec_for_subtext(rec.subtext.policy_rule_id)
    assert rec.subtext.surface_mode == policy_rule["surface_mode"]
    assert rec.subtext.subtext_function == policy_rule["subtext_function"]
    assert rec.subtext.policy_source.endswith("subtext_policy.yaml")
    assert rec.subtext.evidence_codes
