"""Hard validation: NPC spoken/action lane row cap (configurable via story_runtime_experience)."""

from ai_stack.story_runtime.turn.goc_turn_seams import (
    GOC_NPC_LANE_TEXT_CHAR_CAP_DEFAULT,
    run_validation_seam,
)


def _minimal_proposed(description: str) -> list[dict]:
    return [{"effect_type": "narrative_projection", "description": description}]


def test_rejects_single_spoken_line_over_default_cap() -> None:
    cap = GOC_NPC_LANE_TEXT_CHAR_CAP_DEFAULT
    blob = "W" * (cap + 50)
    generation = {
        "success": True,
        "metadata": {
            "structured_output": {
                "schema_version": "runtime_actor_turn_v1",
                "narration_summary": "Short.",
                "spoken_lines": [{"speaker_id": "veronique_vallon", "text": blob}],
            }
        },
    }
    out = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=_minimal_proposed("Short."),
        generation=generation,
        actor_lane_summary={
            "spoken_line_count": 1,
            "action_line_count": 0,
            "initiative_event_count": 0,
            "actor_lane_status": "approved",
        },
    )
    assert out["status"] == "rejected"
    assert out["reason"] == "actor_lane_text_exceeds_transcript_beat"
    assert out.get("transcript_shell_validation", {}).get("rule") == "npc_lane_blob_cap"
    assert out.get("transcript_shell_validation", {}).get("cap") == cap


def test_allows_spoken_blob_when_cap_raised_via_experience() -> None:
    cap = 3000
    blob = "W" * 2000
    assert len(blob) < cap
    generation = {
        "success": True,
        "metadata": {
            "structured_output": {
                "schema_version": "runtime_actor_turn_v1",
                "narration_summary": "Narrator may be long independently of this check.",
                "spoken_lines": [{"speaker_id": "veronique_vallon", "text": blob}],
            }
        },
    }
    out = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=_minimal_proposed("x"),
        generation=generation,
        actor_lane_summary={
            "spoken_line_count": 1,
            "action_line_count": 0,
            "initiative_event_count": 0,
            "actor_lane_status": "approved",
        },
        story_runtime_experience={"npc_spoken_action_text_char_cap": cap},
    )
    assert out["status"] == "approved"


def test_long_narration_with_single_npc_lane_does_not_reject() -> None:
    """Narrator prose is not capped by NPC lane validation."""
    narr = "N" * 5000
    generation = {
        "success": True,
        "metadata": {
            "structured_output": {
                "schema_version": "runtime_actor_turn_v1",
                "narration_summary": narr,
                "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "One line."}],
            }
        },
    }
    out = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=_minimal_proposed(narr),
        generation=generation,
        actor_lane_summary={
            "spoken_line_count": 1,
            "action_line_count": 0,
            "initiative_event_count": 0,
            "actor_lane_status": "approved",
        },
    )
    assert out["status"] == "approved"
