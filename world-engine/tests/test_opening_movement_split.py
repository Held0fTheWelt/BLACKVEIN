"""ADR-0035: split double-paragraph narrator opening into two scene blocks."""

from app.story_runtime.manager import _maybe_split_goc_opening_into_two_movements


def test_split_keeps_already_multi_block_output():
    blocks = [
        {"id": "a", "block_type": "narrator", "text": "One"},
        {"id": "b", "block_type": "actor_line", "text": "Hi"},
    ]
    assert _maybe_split_goc_opening_into_two_movements(blocks, commit_turn_number=0) == blocks


def test_split_skipped_after_opening_turn():
    blocks = [{"id": "a", "block_type": "narrator", "text": "One.\n\nTwo."}]
    assert _maybe_split_goc_opening_into_two_movements(blocks, commit_turn_number=1) == blocks


def test_split_double_paragraph_narrator_into_two_blocks():
    blocks = [
        {
            "id": "turn-0-live-block-1",
            "block_type": "narrator",
            "text": "First movement.\n\nSecond movement.",
            "source": "live_runtime_graph",
        }
    ]
    out = _maybe_split_goc_opening_into_two_movements(blocks, commit_turn_number=0)
    assert len(out) == 2
    assert out[0]["text"] == "First movement."
    assert out[1]["text"] == "Second movement."
    assert out[0]["id"] == "turn-0-live-block-1"
    assert out[1]["id"] == "turn-0-live-block-2"
