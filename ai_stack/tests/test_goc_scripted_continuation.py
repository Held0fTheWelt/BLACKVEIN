"""Tests for the scripted canon continuation path (Steps 005+).

Validates that ``build_goc_scripted_continuation`` correctly:
- Iterates through scripted steps after the opening
- Detects player_status boundaries and stops at the first player window
- Extracts npc_speak directives and produces actor_line blocks
- Renders narrator_perception_only lines as narrator blocks
- Advances through beats in order
"""

from __future__ import annotations

from ai_stack.goc_narrator_path import (
    PLAYER_STATUS_BLOCKED,
    SCRIPTED_CONTINUATION_CONTRACT,
    SCRIPTED_STEP_MODES,
    _beat_player_status,
    _extract_npc_speak,
    _is_player_blocked,
    _step_order_after,
    build_goc_scripted_continuation,
)


def test_scripted_continuation_stops_at_player_window() -> None:
    result = build_goc_scripted_continuation(
        after_step_id="opening_004_den_arrival_positioning",
        session_output_language="en",
    )
    assert result["contract"] == SCRIPTED_CONTINUATION_CONTRACT
    assert result["stopped_at_player_window"] is True
    assert result["stopped_at_beat_id"] == "silence_after_reading"
    assert "opening_005_statement_reading" in result["canonical_step_ids"]


def test_scripted_continuation_produces_npc_speak_blocks() -> None:
    result = build_goc_scripted_continuation(
        after_step_id="opening_004_den_arrival_positioning",
        session_output_language="en",
    )
    npc_speak_blocks = [
        b for b in result["scene_blocks"]
        if b.get("block_type") == "actor_line"
    ]
    assert len(npc_speak_blocks) >= 3
    for block in npc_speak_blocks:
        assert block.get("requires_llm_realization") is True
        assert block.get("actor_id") == "veronique"
        assert "npc_speak_directive" in block
        directive = block["npc_speak_directive"]
        assert directive.get("actor") == "veronique"
        assert directive.get("intent")
        assert directive.get("paraphrase_policy")


def test_scripted_continuation_produces_narrator_blocks() -> None:
    result = build_goc_scripted_continuation(
        after_step_id="opening_004_den_arrival_positioning",
        session_output_language="en",
    )
    narrator_blocks = [
        b for b in result["scene_blocks"]
        if b.get("block_type") == "narrator"
    ]
    assert len(narrator_blocks) >= 1
    for block in narrator_blocks:
        assert block.get("text")
        assert block.get("source") == "narrator_path_scripted_perception"


def test_scripted_continuation_realized_beat_ids() -> None:
    result = build_goc_scripted_continuation(
        after_step_id="opening_004_den_arrival_positioning",
        session_output_language="en",
    )
    assert "veronique_glance_back_before_reading" in result["realized_beat_ids"]
    assert "veronique_reads_date_and_aggression" in result["realized_beat_ids"]
    assert "veronique_reads_injury_detail" in result["realized_beat_ids"]
    assert "silence_after_reading" not in result["realized_beat_ids"]


def test_scripted_continuation_last_step_id() -> None:
    result = build_goc_scripted_continuation(
        after_step_id="opening_004_den_arrival_positioning",
        session_output_language="en",
    )
    assert result["last_step_id"] == "opening_005_statement_reading"


def test_beat_player_status_detection() -> None:
    blocked_beat = {
        "director_instruction": {"player_status": "spectator_blocked"}
    }
    assert _beat_player_status(blocked_beat) == "spectator_blocked"
    assert _is_player_blocked(blocked_beat) is True

    open_beat = {
        "player_status": "observer_window_open"
    }
    assert _beat_player_status(open_beat) == "observer_window_open"
    assert _is_player_blocked(open_beat) is False

    empty_beat: dict = {}
    assert _is_player_blocked(empty_beat) is True


def test_extract_npc_speak() -> None:
    beat_with_speak = {
        "director_instruction": {
            "npc_speak": {
                "actor": "veronique",
                "intent": "read_statement",
            }
        }
    }
    result = _extract_npc_speak(beat_with_speak)
    assert result is not None
    assert result["actor"] == "veronique"

    beat_without_speak = {
        "director_instruction": {
            "narrator_perception_only": ["text"]
        }
    }
    assert _extract_npc_speak(beat_without_speak) is None


def test_step_order_after() -> None:
    remaining = _step_order_after("opening_004_den_arrival_positioning")
    assert len(remaining) > 0
    assert remaining[0] == "opening_005_statement_reading"


def test_player_status_blocked_set() -> None:
    assert "spectator_blocked" in PLAYER_STATUS_BLOCKED
    assert "observer_no_initiative" in PLAYER_STATUS_BLOCKED
    assert "observer_window_open" not in PLAYER_STATUS_BLOCKED


def test_scripted_step_modes() -> None:
    assert "scripted_mandatory_dialog" in SCRIPTED_STEP_MODES
    assert "scripted_with_player_window" in SCRIPTED_STEP_MODES
    assert "narrator_opening_transition" not in SCRIPTED_STEP_MODES


def test_continuation_block_index_start() -> None:
    result = build_goc_scripted_continuation(
        after_step_id="opening_004_den_arrival_positioning",
        session_output_language="en",
        block_index_start=100,
    )
    for block in result["scene_blocks"]:
        assert block["id"].startswith("scripted-continuation-")
        idx = int(block["id"].split("-")[-1])
        assert idx >= 100


def test_continuation_director_plan() -> None:
    result = build_goc_scripted_continuation(
        after_step_id="opening_004_den_arrival_positioning",
        session_output_language="en",
    )
    plan = result["director_plan"]
    assert plan["contract"] == "director_narrator_path_plan.v1"
    assert plan["speech_allowed"] is True
    assert "narrator.scripted_npc_speech.realize" in plan["selected_capabilities"]
    assert "opening_005_statement_reading" in plan["canonical_step_ids"]
