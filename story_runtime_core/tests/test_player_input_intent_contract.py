"""Exercises shared player-input intent taxonomy helpers."""

from __future__ import annotations

import pytest

from story_runtime_core import player_input_intent_contract as pic


@pytest.mark.parametrize(
    "kind,expected_family",
    [
        ("perception", "perception"),
        ("PERCEPTION_ACTION", "perception"),
        ("social_nonverbal_action", "social_nonverbal_action"),
        ("social_speech_action", "social_speech_action"),
        ("mixed", "mixed"),
        ("mixed_action_speech", "mixed"),
        ("movement_action", "action"),
        ("speech", "speech"),
        ("question", "speech"),
        ("wait_or_observe", "wait_or_observe"),
        ("meta", "meta"),
        ("explicit_command", "explicit_command"),
        ("unclear", "unclear"),
        ("ambiguous", "ambiguous"),
        ("not_a_real_kind", "unknown"),
    ],
)
def test_player_input_kind_family(kind: str, expected_family: str):
    assert pic.player_input_kind_family(kind) == expected_family


@pytest.mark.parametrize(
    "kind,fn,expected",
    [
        ("speech", pic.is_known_player_input_kind, True),
        (" bogus ", pic.is_known_player_input_kind, False),
        ("movement_action", pic.is_action_like_player_input_kind, True),
        ("speech", pic.is_action_like_player_input_kind, False),
        ("perception", pic.is_perception_like_player_input_kind, True),
        ("action", pic.is_perception_like_player_input_kind, False),
        ("reaction", pic.is_speech_like_player_input_kind, True),
        ("action", pic.is_speech_like_player_input_kind, False),
        ("meta", pic.is_non_story_control_player_input_kind, True),
        ("action", pic.is_non_story_control_player_input_kind, False),
        ("mixed", pic.is_mixed_player_input_kind, True),
        ("speech", pic.is_mixed_player_input_kind, False),
        ("question", pic.question_shape_may_probe, True),
        ("action", pic.question_shape_may_probe, False),
        ("action", pic.is_question_punctuation_probe_guarded, True),
        ("question", pic.is_question_punctuation_probe_guarded, False),
        ("ambiguous", pic.is_narrator_only_player_input_kind, True),
        ("question", pic.is_narrator_only_player_input_kind, False),
    ],
)
def test_intent_predicates(kind: str, fn, expected: bool):
    assert fn(kind) is expected


def test_normalize_player_input_kind_trims():
    assert pic.normalize_player_input_kind("  SpEech ") == "speech"


def test_normalize_for_intent_matching_folds_accents():
    assert pic.normalize_for_intent_matching("  Été  Café  ") == "ete cafe"


@pytest.mark.parametrize(
    "kind,keys",
    [
        (
            "meta",
            {
                "player_action_committed": False,
                "player_speech_committed": False,
                "narrator_response_expected": False,
                "npc_response_expected": False,
            },
        ),
        (
            "movement_action",
            {
                "player_action_committed": True,
                "player_speech_committed": False,
                "narrator_response_expected": True,
                "npc_response_expected": False,
            },
        ),
        (
            "mixed_action_speech",
            {
                "player_action_committed": True,
                "player_speech_committed": True,
                "narrator_response_expected": True,
                "npc_response_expected": True,
            },
        ),
        (
            "question",
            {
                "player_action_committed": False,
                "player_speech_committed": True,
                "narrator_response_expected": False,
                "npc_response_expected": True,
            },
        ),
        (
            "social_speech_action",
            {
                "player_action_committed": True,
                "player_speech_committed": True,
                "narrator_response_expected": False,
                "npc_response_expected": True,
            },
        ),
        (
            "social_nonverbal_action",
            {
                "player_action_committed": True,
                "player_speech_committed": False,
                "narrator_response_expected": False,
                "npc_response_expected": True,
            },
        ),
        (
            "object_interaction",
            {
                "player_action_committed": True,
                "player_speech_committed": False,
                "narrator_response_expected": True,
                "npc_response_expected": False,
            },
        ),
        (
            "hostile_action",
            {
                "player_action_committed": True,
                "player_speech_committed": False,
                "narrator_response_expected": True,
                "npc_response_expected": False,
            },
        ),
        (
            "wait_or_observe",
            {
                "player_action_committed": False,
                "player_speech_committed": False,
                "narrator_response_expected": True,
                "npc_response_expected": False,
            },
        ),
    ],
)
def test_default_commit_flags_for_player_input_kind(kind: str, keys: dict[str, bool]):
    assert pic.default_commit_flags_for_player_input_kind(kind) == keys


def test_default_commit_flags_unknown_kind_falls_back_to_both_responses_expected():
    flags = pic.default_commit_flags_for_player_input_kind("totally_unknown_label_xy")
    assert flags["narrator_response_expected"] is True
    assert flags["npc_response_expected"] is True
