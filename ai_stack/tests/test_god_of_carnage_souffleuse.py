import json

from ai_stack.story_runtime.narrator.god_of_carnage_narrator_path import build_goc_narrator_path_opening
from ai_stack.god_of_carnage_souffleuse import (
    SOUFFLEUSE_INTERNAL_LANGUAGE,
    SOUFFLEUSE_OPENING_ROLE_ORIENTATION,
    build_goc_opening_souffleuse_projection,
)


def test_god_of_carnage_souffleuse_uses_content_cue_and_prompt_store_for_opening_orientation() -> None:
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
    assert "Study" not in block["text"]
    assert "Souffleuse:" not in block["text"]
    assert "Stay close to yourself" not in block["text"]
    assert "Arbeitszimmer" not in block["text"]
    source_payload = json.loads(block["text"])
    assert source_payload["identity"]["name"] == "Annette Reille"
    assert source_payload["identity"]["professional_identity"] == "Investment broker"
    assert source_payload["identity"]["partner"]["name"] == "Alain Reille"
    assert "politeness_must_not_imply_consent" in source_payload["situational_stance"]["stance_atoms"]
    assert "andere Familie" not in block["text"]
    assert "another family's" not in block["text"]
    assert "armed" not in block["text"].lower()
    assert "source_facts" in block and block["source_facts"]["character_public_identity"]
    assert block["source_facts"]["character_souffleuse_guidance"]["use"] == "situational_stance"
    assert block["source_facts"]["character_situational_stance"]["stance_atoms"]
    assert block["source_facts"]["future_knowledge_policy"] == "infer_baseline_stance_only_no_future_event_disclosure"
    assert block["source_facts"]["character_name"] == "Annette Reille"
    voice_profile = block["source_facts"].get("character_voice_profile")
    assert isinstance(voice_profile, dict)
    assert voice_profile.get("speech_patterns") or voice_profile.get("opening_voice")
    assert block["source_facts"]["character_role"]
    assert block["source_facts"]["character_professional_identity"] == "Investment broker"
    assert block["source_facts"]["character_partner"]["name"] == "Alain Reille"
    assert block["source_facts"]["character_partner"]["professional_identity"] == "Attorney"
    assert block["source_facts"]["character_voice"]["register"] == "polite_compressed_precise"
    assert block["source_facts"]["current_location"]["id"]
    assert block["source_facts"]["incident_location"]["id"]
    assert block["source_facts"]["cue_surface_policy"]["output_shape"] == "inward_footing_not_character_sheet"
    assert "character_statement_pressure" not in block["source_facts"]
    assert "character_stance" in block["guidance_kinds"]
    assert "pre_action_inward_footing" in block["guidance_kinds"]
    assert "input_affordance" not in block["guidance_kinds"]
    assert all("scene" not in str(ref).lower() for ref in block["source_refs"])


def test_god_of_carnage_souffleuse_opening_orientation_is_character_specific() -> None:
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
    annette_payload = json.loads(annette["text"])
    alain_payload = json.loads(alain["text"])
    assert annette_payload["identity"]["professional_identity"] == "Investment broker"
    assert annette_payload["identity"]["partner"]["name"] == "Alain Reille"
    assert "ferdinand_remains_child_and_son" in annette_payload["situational_stance"]["stance_atoms"]
    assert alain_payload["identity"]["professional_identity"] == "Attorney"
    assert alain_payload["identity"]["partner"]["name"] == "Annette Reille"
    assert "clean_agreement_as_exit" in alain_payload["situational_stance"]["stance_atoms"]
    assert "loaded word" not in alain["text"].lower()
    assert "armed" not in alain["text"].lower()
    assert annette["source_facts"]["character_situational_stance"] != alain["source_facts"]["character_situational_stance"]
