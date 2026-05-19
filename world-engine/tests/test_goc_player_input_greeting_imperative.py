"""Greeting-like player input is preserved as player-owned transcript blocks."""

from __future__ import annotations

from app.story_runtime.manager import (
    _goc_player_attributed_visible_text,
    _player_input_scene_blocks_for_story_window,
)


def _blocks_greet(*, raw: str, kind: str = "speech") -> list[dict]:
    return _player_input_scene_blocks_for_story_window(
        session_id="sid",
        turn_number=1,
        raw_input=raw,
        session_output_language="de",
        human_actor_id="annette_reille",
        interpreted_input={"kind": kind, "input_kind": kind},
    )


def _assert_player_owned_echo_and_outcome(blocks: list[dict], *, raw: str) -> None:
    assert len(blocks) == 2
    assert blocks[0]["block_type"] == "player_input"
    assert blocks[1]["block_type"] == "player_input_outcome"
    for block in blocks:
        assert block["speaker_label"] == "Annette"
        assert block["actor_id"] == "annette_reille"
        assert block["actual_owner"] == "player"
        assert block["authority_owner"] == "player"
    assert blocks[0]["text"] == raw
    assert blocks[1]["text"] == raw
    assert "sagt:" not in blocks[1]["text"]
    assert "says:" not in blocks[1]["text"]


def test_greeting_imperative_de_two_scene_blocks_echo_and_outcome() -> None:
    _assert_player_owned_echo_and_outcome(
        _blocks_greet(raw="Begrüße Veronique"),
        raw="Begrüße Veronique",
    )


def test_ich_begrüße_de_same_two_blocks() -> None:
    _assert_player_owned_echo_and_outcome(
        _blocks_greet(raw="Ich begrüße Veronique"),
        raw="Ich begrüße Veronique",
    )


def test_direct_address_hallo_echo_and_attributed_outcome_two_blocks() -> None:
    speaker, line = _goc_player_attributed_visible_text(
        raw_input="Hallo Veronique",
        human_actor_id="annette_reille",
        session_output_language="de",
        interpreted_input={"kind": "speech"},
    )
    assert speaker == "Annette"
    assert line.startswith("Annette:")
    assert "Hallo Veronique" in line
    assert "sagt:" not in line
    assert "„" not in line and "“" not in line

    blocks = _player_input_scene_blocks_for_story_window(
        session_id="sid",
        turn_number=1,
        raw_input="Hallo Veronique",
        session_output_language="de",
        human_actor_id="annette_reille",
        interpreted_input={"kind": "speech"},
    )
    assert len(blocks) == 2
    assert blocks[0]["block_type"] == "player_input"
    assert blocks[0]["text"] == "Hallo Veronique"
    assert blocks[1]["block_type"] == "player_input_outcome"
    assert blocks[1]["speaker_label"] == "Annette"
    assert blocks[1]["actor_id"] == "annette_reille"
    assert blocks[1]["text"] == "Hallo Veronique"
    assert not blocks[1]["text"].startswith("Annette:")
    assert "sagt:" not in blocks[1]["text"]


def test_greeting_imperative_en_two_blocks() -> None:
    blocks = _player_input_scene_blocks_for_story_window(
        session_id="sid",
        turn_number=1,
        raw_input="Greet Veronique",
        session_output_language="en",
        human_actor_id="annette_reille",
        interpreted_input={"kind": "speech"},
    )
    _assert_player_owned_echo_and_outcome(blocks, raw="Greet Veronique")


def test_action_kind_greeting_still_two_diegetic_blocks() -> None:
    _assert_player_owned_echo_and_outcome(
        _blocks_greet(raw="Begrüße Veronique", kind="action"),
        raw="Begrüße Veronique",
    )
