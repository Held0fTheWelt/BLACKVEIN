"""Roster-driven GoC transcript segmentation and diagnostics."""

from __future__ import annotations

from ai_stack.goc_npc_transcript_projection import (
    compile_goc_line_speaker_prefix_pattern,
    goc_spoken_line_row_suspects_multiple_speakers,
    goc_spoken_lines_multi_speaker_row_markers,
    goc_transcript_policy_flags,
    split_merged_goc_actor_line_segments,
)


def test_split_two_speakers_default_roster() -> None:
    segs = split_merged_goc_actor_line_segments('Veronique: "Hallo." Alain: "Ja."')
    assert len(segs) == 2
    assert segs[0][0] == "veronique_vallon"
    assert segs[1][0] == "alain_reille"


def test_merge_consecutive_same_actor_default_policy() -> None:
    segs = split_merged_goc_actor_line_segments(
        'Veronique: "A." Veronique: lächelt. Alain: nickt.',
    )
    assert len(segs) == 2
    assert segs[0][0] == "veronique_vallon"
    assert '"A."' in segs[0][2] and "lächelt" in segs[0][2]
    assert segs[1][0] == "alain_reille"


def test_split_speech_stage_policy_splits_same_actor() -> None:
    segs = split_merged_goc_actor_line_segments(
        'Veronique: "A." Veronique: lächelt. Alain: nickt.',
        story_runtime_experience={"goc_transcript_split_speech_stage_same_actor": True},
    )
    assert len(segs) == 3
    assert [s[0] for s in segs] == ["veronique_vallon", "veronique_vallon", "alain_reille"]


def test_merge_disabled_no_combine_same_actor() -> None:
    segs = split_merged_goc_actor_line_segments(
        'Veronique: "A." Veronique: B. Alain: nickt.',
        story_runtime_experience={"goc_transcript_merge_consecutive_same_actor": False},
    )
    assert len(segs) == 3


def test_roster_subset_excludes_speaker_not_in_npc_list() -> None:
    proj = {"npc_actor_ids": ["michel_longstreet", "alain_reille"], "human_actor_id": "annette_reille"}
    segs = split_merged_goc_actor_line_segments(
        'Michel: "Hi." Alain: "Ho."',
        runtime_projection=proj,
    )
    assert len(segs) == 2
    pat = compile_goc_line_speaker_prefix_pattern(
        ("michel_longstreet", "alain_reille"),
    )
    assert pat is not None
    jam = goc_spoken_line_row_suspects_multiple_speakers(
        'Veronique: "x" Michel: "y"',
        runtime_projection=proj,
    )
    assert jam is False


def test_multi_speaker_row_marker() -> None:
    structured = {
        "spoken_lines": [
            {"speaker_id": "veronique_vallon", "text": 'Veronique: "Hi." Alain: "Da."'},
        ]
    }
    m = goc_spoken_lines_multi_speaker_row_markers(structured, runtime_projection=None)
    assert m == ["goc_multi_speaker_merged_into_single_spoken_line_row"]


def test_transcript_policy_flags_defaults() -> None:
    f = goc_transcript_policy_flags(None)
    assert f["merge_consecutive_same_actor"] is True
    assert f["split_speech_stage_same_actor"] is False
    assert f["map_action_lines_to_actor_line_lane"] is False
