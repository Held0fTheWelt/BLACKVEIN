"""Π14 silence / negative-space contract coverage.

These tests follow ADR-0039: assertions target contracts, enums, flags, and
reason codes instead of treating generated prose as the oracle.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_stack.god_of_carnage_dramatic_alignment import (
    _COMMENTARY_META_PHRASES,
    _FUNCTION_SUBSTRING_TOKENS,
    dramatic_alignment_legacy_fallback_only,
)
from ai_stack.god_of_carnage_frozen_vocabulary import GOC_MODULE_ID, SILENCE_BREVITY_MODES
from ai_stack.story_runtime.director.god_of_carnage_scene_director import build_pacing_and_silence
from ai_stack.contracts.semantic_move_contract import SEMANTIC_MOVE_TYPES, SemanticMoveRecord
from ai_stack.story_runtime.semantic_planner.god_of_carnage_semantic_move_interpretation import interpret_goc_semantic_move
from ai_stack.contracts.silence_negative_space_contract import (
    SILENCE_NEGATIVE_SPACE_CONTRACT_VERSION,
    SILENCE_NEGATIVE_SPACE_SOURCES,
    build_silence_negative_space_decision,
)


def _semantic_silence_record() -> dict[str, object]:
    return {
        "move_type": "silence_withdrawal",
        "social_move_family": "withdraw",
        "directness": "ambiguous",
        "scene_risk_band": "moderate",
    }


def test_pi14_contract_normalizes_semantic_silence_decision() -> None:
    decision = build_silence_negative_space_decision(
        mode="withheld",
        reason="silence_withdrawal",
        source="semantic_move",
        silence_kind="empty_input",
        dramatic_function="withhold_response",
        semantic_move_type="silence_withdrawal",
    )

    assert decision["contract"] == SILENCE_NEGATIVE_SPACE_CONTRACT_VERSION
    assert decision["mode"] in SILENCE_BREVITY_MODES
    assert decision["source"] in SILENCE_NEGATIVE_SPACE_SOURCES
    assert decision["semantic_move_type"] in SEMANTIC_MOVE_TYPES
    assert decision["requires_visible_beat"] is True
    assert decision["blocks_forced_speech"] is True


def test_semantic_move_contract_rejects_unknown_move_type() -> None:
    with pytest.raises(ValidationError):
        SemanticMoveRecord(
            move_type="unregistered_negative_space",
            social_move_family="withdraw",
            directness="ambiguous",
            scene_risk_band="moderate",
        )


def test_semantic_move_uses_interpreted_empty_silence_signal() -> None:
    rec = interpret_goc_semantic_move(
        module_id=GOC_MODULE_ID,
        player_input="",
        interpreted_input={
            "kind": "ambiguous",
            "intent": "withheld_response_or_silence",
            "confidence": 0.5,
            "ambiguity": "empty_input",
        },
        interpreted_move={
            "player_intent": "withheld_response_or_silence",
            "move_class": "action",
        },
        prior_continuity_classes=[],
    )

    assert rec.move_type == "silence_withdrawal"
    assert rec.move_type in SEMANTIC_MOVE_TYPES
    assert rec.feature_snapshot.get("interpreted_silence_signal") is True
    assert rec.feature_snapshot.get("non_lexical_silence_signal") is True


def test_director_semantic_silence_is_withheld_negative_space() -> None:
    pacing, silence = build_pacing_and_silence(
        player_input="",
        interpreted_move={
            "player_intent": "withheld_response_or_silence",
            "move_class": "action",
        },
        module_id=GOC_MODULE_ID,
        semantic_move_record=_semantic_silence_record(),
    )

    assert pacing == "thin_edge"
    assert silence["contract"] == SILENCE_NEGATIVE_SPACE_CONTRACT_VERSION
    assert silence["mode"] == "withheld"
    assert silence["reason"] == "silence_withdrawal"
    assert silence["source"] == "semantic_move"
    assert silence["silence_kind"] == "empty_input"
    assert silence["requires_visible_beat"] is True
    assert silence["blocks_forced_speech"] is True


def test_director_prior_tension_keeps_forced_speech_block() -> None:
    pacing, silence = build_pacing_and_silence(
        player_input="...",
        interpreted_move={
            "player_intent": "withheld_response_or_silence",
            "move_class": "action",
        },
        module_id=GOC_MODULE_ID,
        semantic_move_record=_semantic_silence_record(),
        prior_planner_truth={"carry_forward_tension_notes": "open"},
    )

    assert pacing == "compressed"
    assert silence["mode"] == "brief"
    assert silence["reason"] == "silence_withdrawal_upgraded_by_prior_tension"
    assert silence["silence_kind"] == "charged_after_tension"
    assert silence["blocks_forced_speech"] is True


def test_alignment_uses_negative_space_contract_even_when_mode_brief() -> None:
    decision = build_silence_negative_space_decision(
        mode="brief",
        reason="silence_withdrawal_upgraded_by_prior_tension",
        source="semantic_move",
        silence_kind="charged_after_tension",
        dramatic_function="carry_tension",
        semantic_move_type="silence_withdrawal",
    )
    proposed_narrative = " ".join(
        (
            _COMMENTARY_META_PHRASES[0],
            *_FUNCTION_SUBSTRING_TOKENS["withhold_or_evade"][:2],
        )
    )

    result = dramatic_alignment_legacy_fallback_only(
        selected_scene_function="withhold_or_evade",
        pacing_mode="compressed",
        silence_brevity_decision=decision,
        proposed_narrative=proposed_narrative,
    )

    assert result == "dramatic_alignment_meta_commentary"
