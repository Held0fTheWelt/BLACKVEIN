"""Greeting-imperative player input becomes two transcript blocks (echo + diegetic)."""

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


def test_greeting_imperative_de_two_scene_blocks_echo_and_outcome() -> None:
    blocks = _blocks_greet(raw="Begrüße Veronique")
    assert len(blocks) == 2
    assert blocks[0]["block_type"] == "player_input"
    assert blocks[0]["text"] == "Begrüße Veronique"
    assert blocks[1]["block_type"] == "player_input_outcome"
    assert "Annette sagt:" in str(blocks[1].get("text") or "")
    assert "Hallo Véronique" in str(blocks[1].get("text") or "")


def test_ich_begrüße_de_same_two_blocks() -> None:
    blocks = _blocks_greet(raw="Ich begrüße Veronique")
    assert len(blocks) == 2
    assert blocks[0]["text"] == "Ich begrüße Veronique"
    assert "Véronique" in str(blocks[1].get("text") or "")


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
    assert len(blocks) == 2
    assert blocks[0]["text"] == "Greet Veronique"
    assert "Annette says:" in str(blocks[1].get("text") or "")
    assert "Hello Véronique" in str(blocks[1].get("text") or "")


def test_action_kind_greeting_still_two_diegetic_blocks() -> None:
    blocks = _blocks_greet(raw="Begrüße Veronique", kind="action")
    assert len(blocks) == 2
    assert blocks[1]["block_type"] == "player_input_outcome"
