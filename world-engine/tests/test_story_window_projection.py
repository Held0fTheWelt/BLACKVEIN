from __future__ import annotations

from app.story_runtime.manager import StorySession, _story_window_entries_for_session


def test_story_window_projection_uses_committed_opening_and_player_turn() -> None:
    session = StorySession(
        session_id="story-1",
        module_id="god_of_carnage",
        runtime_projection={"start_scene_id": "scene_1"},
        current_scene_id="scene_1",
    )
    session.diagnostics = [
        {
            "turn_number": 0,
            "turn_kind": "opening",
            "raw_input": "internal opening prompt hidden from players",
            "visible_output_bundle": {"gm_narration": ["The room is already tense."]},
            "narrative_commit": {"committed_consequences": ["opening_committed"]},
            "runtime_governance_surface": {"governed_runtime_active": True},
        },
        {
            "turn_number": 1,
            "turn_kind": "player",
            "raw_input": "I say that is enough.",
            "visible_output_bundle": {
                "gm_narration": ["The answer lands hard."],
                "spoken_lines": ["Annette: Enough?"],
            },
            "narrative_commit": {"committed_consequences": ["tension_escalates"]},
        },
    ]

    entries = _story_window_entries_for_session(session)

    assert [entry["role"] for entry in entries] == ["runtime", "player", "runtime"]
    assert entries[0]["kind"] == "opening"
    assert entries[0]["text"] == "The room is already tense."
    assert "internal opening prompt" not in entries[0]["text"]
    assert entries[1]["text"] == "I say that is enough."
    assert entries[2]["text"] == "The answer lands hard."
    assert entries[2]["spoken_lines"] == ["Annette: Enough?"]
    assert entries[2]["committed_consequences"] == ["tension_escalates"]
