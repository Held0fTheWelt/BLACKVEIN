"""
MVP4 Contract 3: Frontend Playability

Verifies that `can_execute` matches `story_window.entry_count`:
- Empty session (no opening) → can_execute=False
- Session with opening → can_execute=True
"""

import pytest


@pytest.mark.mvp4
def test_mvp4_can_execute_false_without_opening():
    """Contract 3.1: can_execute should be False when no opening exists."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    # Simulate state with no story entries (no opening turn)
    state = {
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "source": "world_engine_story_runtime",
            "entries": [],  # Empty: no opening
            "entry_count": 0,
            "latest_entry": None,
        },
        "last_committed_turn": None,
    }

    bundle = _player_session_bundle(
        run_id="test_run",
        template_id="god_of_carnage",
        module_id="god_of_carnage",
        runtime_session_id="test_session",
        state=state,
        created=None,
    )

    assert bundle.get("can_execute") is False, \
        "can_execute should be False when story_window has no entries"


@pytest.mark.mvp4
def test_mvp4_can_execute_true_with_opening():
    """Contract 3.2: can_execute should be True when opening exists."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    # Simulate state with opening entry (Turn 0)
    state = {
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "source": "world_engine_story_runtime",
            "entries": [
                {
                    "turn_number": 0,
                    "kind": "opening",
                    "role": "runtime",
                    "text": "The room is tense.",
                }
            ],
            "entry_count": 1,
            "latest_entry": {
                "turn_number": 0,
                "kind": "opening",
                "role": "runtime",
                "text": "The room is tense.",
            },
        },
        "last_committed_turn": None,
    }

    bundle = _player_session_bundle(
        run_id="test_run",
        template_id="god_of_carnage",
        module_id="god_of_carnage",
        runtime_session_id="test_session",
        state=state,
        created=None,
    )

    assert bundle.get("can_execute") is True, \
        "can_execute should be True when story_window has entries (opening)"


@pytest.mark.mvp4
def test_mvp4_can_execute_true_with_multiple_entries():
    """Contract 3.3: can_execute should be True with multiple entries."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    # Simulate state with opening + player turn
    state = {
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "source": "world_engine_story_runtime",
            "entries": [
                {
                    "turn_number": 0,
                    "kind": "opening",
                    "role": "runtime",
                    "text": "The room is tense.",
                },
                {
                    "turn_number": 1,
                    "kind": "player",
                    "role": "player",
                    "text": "I break the silence.",
                },
                {
                    "turn_number": 1,
                    "kind": "runtime",
                    "role": "runtime",
                    "text": "Annette leans forward.",
                },
            ],
            "entry_count": 3,
            "latest_entry": {
                "turn_number": 1,
                "kind": "runtime",
                "role": "runtime",
                "text": "Annette leans forward.",
            },
        },
        "last_committed_turn": {
            "turn_number": 1,
            "visible_output_bundle": {"gm_narration": ["Annette leans forward."]},
        },
    }

    bundle = _player_session_bundle(
        run_id="test_run",
        template_id="god_of_carnage",
        module_id="god_of_carnage",
        runtime_session_id="test_session",
        state=state,
        created=None,
    )

    assert bundle.get("can_execute") is True, \
        "can_execute should be True when story_window has entries"


@pytest.mark.mvp4
def test_mvp4_story_entries_match_story_window():
    """Contract 3.4: story_entries in bundle should match story_window.entries."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    entries = [
        {
            "turn_number": 0,
            "kind": "opening",
            "role": "runtime",
            "text": "The room is tense.",
        }
    ]
    state = {
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "source": "world_engine_story_runtime",
            "entries": entries,
            "entry_count": 1,
            "latest_entry": entries[0],
        },
        "last_committed_turn": None,
    }

    bundle = _player_session_bundle(
        run_id="test_run",
        template_id="god_of_carnage",
        module_id="god_of_carnage",
        runtime_session_id="test_session",
        state=state,
        created=None,
    )

    assert bundle.get("story_entries") == entries, \
        "story_entries should match story_window.entries"
    assert bundle.get("story_window", {}).get("entry_count") == len(entries), \
        "story_window.entry_count should match number of entries"


@pytest.mark.mvp4
def test_mvp4_narrator_streaming_promoted_to_player_bundle():
    """Contract 3.5: narrator_streaming must be available top-level for the frontend contract."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    state = {
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "source": "world_engine_story_runtime",
            "entries": [{"turn_number": 0, "kind": "opening", "role": "runtime", "text": "The room is tense."}],
            "entry_count": 1,
            "latest_entry": {"turn_number": 0, "kind": "opening", "role": "runtime", "text": "The room is tense."},
        },
        "last_committed_turn": {
            "turn_number": 1,
            "narrator_streaming": {"status": "streaming", "session_id": "test_session"},
        },
    }

    bundle = _player_session_bundle(
        run_id="test_run",
        template_id="god_of_carnage",
        module_id="god_of_carnage",
        runtime_session_id="test_session",
        state=state,
        created=None,
    )

    assert bundle.get("narrator_streaming") == {
        "status": "streaming",
        "session_id": "test_session",
    }
