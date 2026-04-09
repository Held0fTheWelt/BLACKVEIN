"""Semantic move interpretation: deterministic pipeline and paraphrase stability."""

from __future__ import annotations

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.semantic_move_interpretation_goc import interpret_goc_semantic_move


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
