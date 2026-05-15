"""Semantic move interpretation: deterministic pipeline and paraphrase stability."""

from __future__ import annotations

import pytest

from ai_stack.goc_actor_aliases import GOC_ACTOR_ALIASES
from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.semantic_move_interpretation_goc import interpret_goc_semantic_move
from story_runtime_core.player_input_intent_contract import (
    FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES,
    QUESTION_PUNCTUATION_PROBE_GUARDED_KINDS,
    default_commit_flags_for_player_input_kind,
    player_input_kind_family,
)


def _base_interp():
    return {"kind": "narrative", "intent": "pressure", "confidence": 0.5, "ambiguity": "low"}


def test_direct_accusation_stable_under_paraphrase_not_keyword_only() -> None:
    """Same move_type when blame is expressed without the literal words 'blame' or 'fault'."""
    a = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="I hold you responsible for what happened at the school.",
        interpreted_input=_base_interp(),
        interpreted_move={"player_intent": "accuse", "move_class": "statement"},
        prior_continuity_classes=[],
    )
    b = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="You are accountable for this incident; that is on you.",
        interpreted_input=_base_interp(),
        interpreted_move={"player_intent": "accuse", "move_class": "statement"},
        prior_continuity_classes=[],
    )
    assert a.move_type == "direct_accusation"
    assert b.move_type == "direct_accusation"
    assert "responsible" in str(a.feature_snapshot) or a.feature_snapshot.get("syn_accusation")
    assert "accountable" in str(b.feature_snapshot) or b.feature_snapshot.get("syn_accusation")


def test_repair_attempt_vs_competing_repair_reveal() -> None:
    r = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="I am sorry",
        interpreted_input=_base_interp(),
        interpreted_move={"player_intent": "repair", "move_class": "dialogue"},
        prior_continuity_classes=[],
    )
    assert r.move_type == "repair_attempt"
    m = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="I'm sorry but you must reveal the truth now",
        interpreted_input=_base_interp(),
        interpreted_move={"player_intent": "mixed", "move_class": "dialogue"},
        prior_continuity_classes=[],
    )
    assert m.move_type == "competing_repair_and_reveal"


def test_silence_withdrawal() -> None:
    s = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="I say nothing and hold an awkward pause.",
        interpreted_input=_base_interp(),
        interpreted_move={"player_intent": "silence", "move_class": "dialogue"},
        prior_continuity_classes=[],
    )
    assert s.move_type == "silence_withdrawal"


def test_alliance_reposition_synset() -> None:
    s = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="I stand with Annette against your husband tonight.",
        interpreted_input=_base_interp(),
        interpreted_move={"player_intent": "alliance", "move_class": "dialogue"},
        prior_continuity_classes=[],
    )
    assert s.move_type == "alliance_reposition"


def test_ranked_semantic_candidates_preserve_primary_and_secondary() -> None:
    r = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="I'm sorry but reveal the truth now.",
        interpreted_input=_base_interp(),
        interpreted_move={"player_intent": "mixed", "move_class": "dialogue"},
        prior_continuity_classes=["blame_pressure"],
    )
    assert r.move_type == "competing_repair_and_reveal"
    assert r.ranked_move_candidates
    assert r.ranked_move_candidates[0].move_type == r.move_type
    assert r.secondary_move_type in {None, r.ranked_move_candidates[1].move_type if len(r.ranked_move_candidates) > 1 else None}
    assert isinstance(r.secondary_dramatic_features, list)
    assert any("secondary_move:" in tag for tag in r.secondary_dramatic_features)


def test_perception_question_not_forced_into_probe_inquiry() -> None:
    """Wave A: physical/perception question shape should not demand NPC answer semantics."""
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
    assert rec.move_type != "probe_inquiry"
    assert rec.feature_snapshot.get("player_input_kind_is_perception") is True


@pytest.mark.parametrize("player_input_kind", sorted(QUESTION_PUNCTUATION_PROBE_GUARDED_KINDS))
def test_contract_guarded_question_shapes_do_not_become_npc_probe(player_input_kind: str) -> None:
    """ADR-0039: guarded kinds come from the shared intent contract, not a copied oracle list."""
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
    assert rec.feature_snapshot.get("player_input_kind_question_shape_guarded") is True
    assert rec.feature_snapshot.get("player_input_kind_family") == player_input_kind_family(player_input_kind)


def test_actor_target_aliases_are_accent_folded_from_canonical_alias_map() -> None:
    """Actor oracle is the canonical alias map; the input phrase is incidental test data."""
    actor_id = "veronique_vallon"
    assert actor_id in GOC_ACTOR_ALIASES
    rec = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="Begrüße Véronique.",
        interpreted_input={
            **_base_interp(),
            "player_input_kind": "social_nonverbal_action",
            **default_commit_flags_for_player_input_kind("social_nonverbal_action"),
        },
        interpreted_move={"player_intent": "social_action", "move_class": "action"},
        prior_continuity_classes=[],
    )
    assert rec.target_actor_hint == actor_id
