from ai_stack.goc_narrator_path import (
    NARRATOR_PATH_ADAPTER,
    NARRATOR_PATH_INVOCATION_MODE,
    build_goc_narrator_path_opening,
)


def test_goc_narrator_path_opening_is_speech_free_and_canonical() -> None:
    out = build_goc_narrator_path_opening(session_output_language="de")

    assert out["path_mode"] == "narrator_path"
    assert out["adapter"] == NARRATOR_PATH_ADAPTER
    assert out["adapter_invocation_mode"] == NARRATOR_PATH_INVOCATION_MODE
    assert out["canonical_step_ids"][:3] == [
        "opening_001_parc_montsouris_edge",
        "opening_002_argument_stick_blow",
        "opening_003_bicycle_disappearance",
    ]

    blocks = out["scene_blocks"]
    assert len(blocks) >= 5
    assert {block["block_type"] for block in blocks} == {"narrator"}
    assert all(not block.get("actor_id") for block in blocks)
    assert all("source_refs" in block and block["source_refs"] for block in blocks)
    assert "Parc Montsouris" in blocks[0]["text"]
    assert "Arbeitszimmer" in blocks[-1]["text"]


def test_goc_narrator_path_director_plan_skips_actor_lanes() -> None:
    out = build_goc_narrator_path_opening(session_output_language="en")
    plan = out["director_plan"]

    assert plan["speech_allowed"] is False
    assert plan["npc_agency_required"] is False
    assert plan["player_action_resolution_required"] is False
    assert plan["selected_capabilities"] == ["narrator.opening_event.realize"]
    assert "npc_agency" in plan["skipped_capability_groups"]
    assert "player_action_resolution" in plan["skipped_capability_groups"]
