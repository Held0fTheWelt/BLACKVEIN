from ai_stack.story_runtime.narrator import goc_narrator_path
from ai_stack.story_runtime.narrator.goc_narrator_path import NARRATOR_PATH_ADAPTER, NARRATOR_PATH_INVOCATION_MODE


def test_goc_narrator_path_opening_is_speech_free_and_canonical() -> None:
    out = goc_narrator_path.build_goc_narrator_path_opening(session_output_language="de")

    assert out["path_mode"] == "narrator_path"
    assert out["adapter"] == NARRATOR_PATH_ADAPTER
    assert out["adapter_invocation_mode"] == NARRATOR_PATH_INVOCATION_MODE
    assert out["canonical_step_ids"][:3] == [
        "opening_001_parc_montsouris_edge",
        "opening_002_argument_stick_blow",
        "opening_003_bicycle_disappearance",
    ]
    assert out["authoring_language"] == "en"
    assert out["requires_output_realization"] is True

    blocks = out["scene_blocks"]
    assert len(blocks) >= 6
    assert {block["block_type"] for block in blocks} == {"narrator"}
    assert all(not block.get("actor_id") for block in blocks)
    assert all("source_refs" in block and block["source_refs"] for block in blocks)
    assert all("source_facts" in block and block["source_facts"] for block in blocks)
    assert blocks[0]["canonical_mandatory_beat_id"] == "park_edge_establishing_image"
    assert blocks[0]["source_facts"]["semantic_input_language"] == "en"
    assert blocks[0]["source_facts"]["module_context"]["setting"]
    assert blocks[0]["source_facts"]["location"]["id"] == "park_edge"
    assert blocks[0]["source_facts"]["mandatory_beat"]["coverage_cues"]
    assert blocks[0]["source_facts"]["transition_from_previous"]["kind"] == "opening_start"
    assert "Winter afternoon" in blocks[0]["text"]
    assert any("home office" in block["text"] for block in blocks)
    assert any("Parc Mont Sourire" in str(block["source_facts"]) for block in blocks)
    transition_blocks = [
        block
        for block in blocks
        if (block["source_facts"].get("transition_from_previous") or {}).get("location_changed")
    ]
    assert transition_blocks
    assert transition_blocks[0]["source_facts"]["transition_from_previous"]["current_location"]["id"]
    hard_cut_blocks = [
        block
        for block in blocks
        if (block["source_facts"].get("transition_from_previous") or {})
        .get("directed_transition", {})
        .get("kind")
        == "hard_cut"
    ]
    assert [block["canonical_mandatory_beat_id"] for block in hard_cut_blocks] == ["room_perception_winter_light"]
    emphasis_blocks = [block for block in blocks if block.get("visual_emphasis")]
    assert emphasis_blocks
    assert emphasis_blocks[0]["visual_emphasis"]["kind"] == "dramatic_moment"
    assert out["source_input_mode"] == "semantic_frames_with_fallback_blocks"
    assert out["narrative_source_frames"][0]["id"] == "opening_001_parc_montsouris_edge"


def test_goc_narrator_path_director_plan_skips_actor_lanes() -> None:
    out = goc_narrator_path.build_goc_narrator_path_opening(session_output_language="en")
    plan = out["director_plan"]

    assert plan["speech_allowed"] is False
    assert plan["npc_agency_required"] is False
    assert plan["player_action_resolution_required"] is False
    assert plan["selected_capabilities"] == ["narrator.opening_event.realize"]
    assert "npc_agency" in plan["skipped_capability_groups"]
    assert "player_action_resolution" in plan["skipped_capability_groups"]


def test_goc_narrator_path_projects_mandatory_beat_content(monkeypatch) -> None:
    synthetic_path = {
        "authoring_language": "en",
        "paths": {
            "opening": {
                "first_step_id": "opening_001_synthetic",
                "first_playable_step_id": "opening_001_synthetic",
            }
        },
        "step_order": ["opening_001_synthetic"],
        "steps": [
            {
                "sequence": 1,
                "id": "opening_001_synthetic",
                "mode": "narrator_only_prologue",
                "mandatory_beats": [
                    {
                        "id": "synthetic_visible_beat",
                        "order": 1,
                        "beat_pattern_params": {
                            "perception_lines": ["Authored line one.", "Authored line two."],
                        },
                    }
                ],
            }
        ],
    }
    monkeypatch.setattr(goc_narrator_path, "load_goc_canonical_path_yaml", lambda: synthetic_path)

    out = goc_narrator_path.build_goc_narrator_path_opening(session_output_language="de")

    assert [block["text"] for block in out["scene_blocks"]] == [
        "Authored line one. Authored line two."
    ]
    assert out["scene_blocks"][0]["canonical_mandatory_beat_id"] == "synthetic_visible_beat"
    assert out["scene_blocks"][0]["source_facts"]["mandatory_beat"]["coverage_cues"] == [
        "Authored line one.",
        "Authored line two.",
    ]
    assert out["requires_output_realization"] is True
