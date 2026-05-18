from ai_stack.goc_narrator_path import build_goc_narrator_path_opening
from ai_stack.goc_souffleuse import (
    SOUFFLEUSE_INTERNAL_LANGUAGE,
    SOUFFLEUSE_OPENING_ROLE_ORIENTATION,
    build_goc_opening_souffleuse_projection,
)


def test_goc_souffleuse_uses_content_cue_and_prompt_store_for_opening_orientation() -> None:
    narrator_path = build_goc_narrator_path_opening(session_output_language="de")
    projection = build_goc_opening_souffleuse_projection(
        session_output_language="de",
        runtime_projection={
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette_reille",
        },
        narrator_path=narrator_path,
        scene_blocks=narrator_path["scene_blocks"],
    )

    assert projection["diagnostics"]["selected"] is True
    assert projection["diagnostics"]["internal_resolution_language"] == SOUFFLEUSE_INTERNAL_LANGUAGE
    blocks = projection["blocks"]
    assert len(blocks) == 1
    block = blocks[0]
    assert block["block_type"] == "souffleuse"
    assert block["visible_lane"] == "player_hint"
    assert block["card_style"] == "director_notice"
    assert block["voice_mode"] == "second_person_inner"
    assert block["commit_impact"] == "ui_guidance_only"
    assert block["origin_capability"] == SOUFFLEUSE_OPENING_ROLE_ORIENTATION
    assert block["internal_resolution_language"] == "en"
    assert block["source_language"] == "en"
    assert block["session_output_language"] == "de"
    assert block["visible_output_language"] == "en"
    assert block["requires_output_realization"] is True
    assert "Annette Reille" not in block["text"]
    assert "Study" not in block["text"]
    assert "Souffleuse:" not in block["text"]
    assert "Stay close to yourself" not in block["text"]
    assert "Arbeitszimmer" not in block["text"]
    assert block["text"] == "Do not let them turn Ferdinand into a case."
    assert "source_facts" in block and block["source_facts"]["character_public_identity"]
    assert block["source_facts"]["character_souffleuse_guidance"]
    assert all("scene" not in str(ref).lower() for ref in block["source_refs"])


def test_goc_souffleuse_opening_orientation_is_character_specific() -> None:
    narrator_path = build_goc_narrator_path_opening(session_output_language="de")

    annette = build_goc_opening_souffleuse_projection(
        session_output_language="de",
        runtime_projection={
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette_reille",
        },
        narrator_path=narrator_path,
        scene_blocks=narrator_path["scene_blocks"],
    )["blocks"][0]
    alain = build_goc_opening_souffleuse_projection(
        session_output_language="de",
        runtime_projection={
            "human_actor_id": "alain_reille",
            "selected_player_role": "alain_reille",
        },
        narrator_path=narrator_path,
        scene_blocks=narrator_path["scene_blocks"],
    )["blocks"][0]

    assert annette["target_actor_id"] == "annette_reille"
    assert alain["target_actor_id"] == "alain_reille"
    assert annette["text"] != alain["text"]
    assert annette["text"] == "Do not let them turn Ferdinand into a case."
    assert alain["text"] == "Keep it procedural. One loaded word is enough."
    assert annette["source_facts"]["character_statement_pressure"] != alain["source_facts"]["character_statement_pressure"]
    assert annette["source_facts"]["character_souffleuse_guidance"] != alain["source_facts"]["character_souffleuse_guidance"]
