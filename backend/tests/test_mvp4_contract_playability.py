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


@pytest.mark.mvp4
def test_mvp4_visible_scene_output_survives_resume_state():
    """Resume bundles should promote persisted committed scene blocks for MVP5 rendering."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    scene_blocks = [
        {
            "id": "turn-0-block-1",
            "block_type": "narrator",
            "speaker_label": "World of Shadows",
            "text": "The room is tense.",
        }
    ]
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
                    "scene_blocks": scene_blocks,
                }
            ],
            "entry_count": 1,
            "latest_entry": {
                "turn_number": 0,
                "kind": "opening",
                "role": "runtime",
                "text": "The room is tense.",
                "scene_blocks": scene_blocks,
            },
        },
        "last_committed_turn": {
            "turn_number": 0,
            "turn_kind": "opening",
            "visible_output_bundle": {
                "gm_narration": ["The room is tense."],
                "scene_blocks": scene_blocks,
            },
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

    assert bundle["opening_turn"] is None
    vso = bundle["visible_scene_output"]
    assert vso["typewriter_slice_start_index"] == 0
    assert "player_shell_narrative_card_diagnostics" in vso
    assert len(vso["blocks"]) == len(scene_blocks)
    for got, exp in zip(vso["blocks"], scene_blocks):
        assert got["id"] == exp["id"]
        assert got["block_type"] == exp["block_type"]
        assert got.get("text") == exp.get("text")


@pytest.mark.mvp4
def test_mvp4_visible_scene_output_is_cumulative_for_mvp5_transcript():
    """MVP5 loadTurn clears the transcript; JSON must carry every committed scene block in order."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    opening_blocks = [
        {"id": "turn-0-block-1", "block_type": "narrator", "text": "Opening line."},
    ]
    turn1_blocks = [
        {"id": "turn-1-block-1", "block_type": "actor_line", "text": "Follow-up."},
    ]
    state = {
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "entries": [
                {
                    "turn_number": 0,
                    "kind": "opening",
                    "role": "runtime",
                    "scene_blocks": opening_blocks,
                },
                {
                    "turn_number": 1,
                    "kind": "runtime_response",
                    "role": "runtime",
                    "scene_blocks": turn1_blocks,
                },
            ],
            "entry_count": 2,
            "latest_entry": {"turn_number": 1, "role": "runtime", "scene_blocks": turn1_blocks},
        },
        "last_committed_turn": {
            "turn_number": 1,
            "turn_kind": "player",
            "visible_output_bundle": {"scene_blocks": turn1_blocks},
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
    vso = bundle["visible_scene_output"]
    assert vso["typewriter_slice_start_index"] == 1
    assert "player_shell_narrative_card_diagnostics" in vso
    merged = opening_blocks + turn1_blocks
    assert len(vso["blocks"]) == len(merged)
    for got, exp in zip(vso["blocks"], merged):
        assert got["id"] == exp["id"]
        assert got["block_type"] == exp["block_type"]
        assert got.get("text") == exp.get("text")


@pytest.mark.mvp4
def test_mvp4_visible_scene_output_cumulative_includes_player_input_blocks():
    """Player story-window entries carry scene_blocks so MVP5 transcript shows player lines."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    opening_blocks = [{"id": "turn-0-block-1", "block_type": "narrator", "text": "Opening line."}]
    player_blocks = [
        {
            "id": "sid-turn-1-player-input",
            "block_type": "player_input",
            "speaker_label": "Du",
            "text": "I speak.",
        }
    ]
    turn1_blocks = [{"id": "turn-1-block-1", "block_type": "actor_line", "text": "Follow-up."}]
    state = {
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "entries": [
                {"turn_number": 0, "kind": "opening", "role": "runtime", "scene_blocks": opening_blocks},
                {"turn_number": 1, "kind": "player_turn", "role": "player", "scene_blocks": player_blocks},
                {"turn_number": 1, "kind": "runtime_response", "role": "runtime", "scene_blocks": turn1_blocks},
            ],
            "entry_count": 3,
            "latest_entry": {"turn_number": 1, "role": "runtime", "scene_blocks": turn1_blocks},
        },
        "last_committed_turn": {
            "turn_number": 1,
            "visible_output_bundle": {"scene_blocks": turn1_blocks},
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
    expected_blocks = opening_blocks + player_blocks + turn1_blocks
    vso = bundle["visible_scene_output"]
    assert vso["typewriter_slice_start_index"] == 2
    assert "player_shell_narrative_card_diagnostics" in vso
    assert len(vso["blocks"]) == len(expected_blocks)
    for got, exp in zip(vso["blocks"], expected_blocks):
        assert got["id"] == exp["id"]
        assert got["block_type"] == exp["block_type"]
        assert got.get("text") == exp.get("text")


@pytest.mark.mvp4
def test_mvp4_player_bundle_polishes_goc_colon_stutter_and_redundant_actor_action():
    """GoC cumulative blocks from persisted story_window are re-polished for the shell (ADR-0034)."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    raw_line = (
        'Veronique: "Welcome." Veronique: Veronique smiles warmly '
        "and offers Annette her hand in greeting."
    )
    dup_action = "Veronique smiles warmly and offers Annette her hand in greeting."
    opening_blocks = [{"id": "turn-0-block-1", "block_type": "narrator", "text": "Opening line."}]
    turn1_blocks = [
        {
            "id": "turn-1-block-1",
            "block_type": "actor_line",
            "actor_id": "veronique_vallon",
            "speaker_label": "Veronique",
            "text": raw_line,
        },
        {
            "id": "turn-1-block-2",
            "block_type": "actor_action",
            "actor_id": "veronique_vallon",
            "speaker_label": "Veronique",
            "text": dup_action,
        },
    ]
    state = {
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "entries": [
                {"turn_number": 0, "kind": "opening", "role": "runtime", "scene_blocks": opening_blocks},
                {"turn_number": 1, "kind": "runtime_response", "role": "runtime", "scene_blocks": turn1_blocks},
            ],
            "entry_count": 2,
            "latest_entry": {"turn_number": 1, "role": "runtime", "scene_blocks": turn1_blocks},
        },
        "last_committed_turn": {"turn_number": 1, "visible_output_bundle": {"scene_blocks": turn1_blocks}},
    }
    bundle = _player_session_bundle(
        run_id="test_run",
        template_id="god_of_carnage",
        module_id="god_of_carnage",
        runtime_session_id="test_session",
        state=state,
        created=None,
    )
    blocks = bundle["visible_scene_output"]["blocks"]
    assert len(blocks) == 2
    assert blocks[0]["block_type"] == opening_blocks[0]["block_type"]
    assert blocks[0].get("text") == opening_blocks[0].get("text")
    assert blocks[1]["block_type"] == "actor_line"
    merged_visible = blocks[1].get("player_display_text") or blocks[1].get("text") or ""
    assert "Veronique: Véronique" not in merged_visible
    assert "Veronique smiles warmly" in merged_visible


@pytest.mark.mvp4
def test_mvp4_player_bundle_removes_direct_narrator_adjacent_redundant_actor_action():
    """Presentation-layer cleanup: narrator-adjacent redundant actor_action may be removed."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    opening_blocks = [
        {"id": "turn-0-block-1", "block_type": "narrator", "text": "Opening line."},
    ]
    turn1_blocks = [
        {
            "id": "turn-1-block-1",
            "block_type": "narrator",
            "text": "Veronique smiles warmly and offers Annette her hand.",
        },
        {
            "id": "turn-1-block-2",
            "block_type": "actor_action",
            "actor_id": "veronique_vallon",
            "speaker_label": "Véronique",
            "text": "Veronique smiles warmly and offers Annette her hand.",
        },
    ]
    state = {
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "entries": [
                {"turn_number": 0, "kind": "opening", "role": "runtime", "scene_blocks": opening_blocks},
                {"turn_number": 1, "kind": "runtime_response", "role": "runtime", "scene_blocks": turn1_blocks},
            ],
            "entry_count": 2,
            "latest_entry": {"turn_number": 1, "role": "runtime", "scene_blocks": turn1_blocks},
        },
        "last_committed_turn": {"turn_number": 1, "visible_output_bundle": {"scene_blocks": turn1_blocks}},
    }
    bundle = _player_session_bundle(
        run_id="test_run",
        template_id="god_of_carnage",
        module_id="god_of_carnage",
        runtime_session_id="test_session",
        state=state,
        created=None,
    )
    vso = bundle["visible_scene_output"]
    blocks = vso["blocks"]
    assert len(blocks) == 2
    assert blocks[0]["id"] == opening_blocks[0]["id"]
    assert blocks[1]["block_type"] == "narrator"
    diag = vso.get("player_shell_narrative_card_diagnostics") or {}
    assert diag.get("narrator_adjacent_redundant_story_card_removed", 0) >= 1
    assert diag.get("narrator_adjacent_redundant_actor_action_removed", 0) >= 1
    assert diag.get("narrator_adjacent_redundant_actor_line_removed", 0) == 0


@pytest.mark.mvp4
def test_mvp4_typewriter_slice_start_index_non_cumulative_is_zero():
    """Fallback bundle (no entry-level scene_blocks) animates the whole slice from index 0."""
    from backend.app.api.v1.game_routes import _player_session_bundle

    turn_blocks = [{"id": "t1", "block_type": "narrator", "text": "Only latest turn."}]
    state = {
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "entries": [],
            "entry_count": 0,
            "latest_entry": None,
        },
        "last_committed_turn": {
            "turn_number": 1,
            "visible_output_bundle": {"scene_blocks": turn_blocks},
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
    vso = bundle["visible_scene_output"]
    assert vso["typewriter_slice_start_index"] == 0
    assert "player_shell_narrative_card_diagnostics" in vso
    assert len(vso["blocks"]) == len(turn_blocks)
    for got, exp in zip(vso["blocks"], turn_blocks):
        assert got["id"] == exp["id"]
        assert got["block_type"] == exp["block_type"]
        assert got.get("text") == exp.get("text")
