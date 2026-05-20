"""HUMAN-INPUT-ATTRIBUTION-01: visible render must not mis-attribute live player input."""

from __future__ import annotations

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.goc_turn_seams import run_visible_render


def test_run_visible_render_skips_reacts_immediately_when_player_input_present() -> None:
    bundle, markers = run_visible_render(
        module_id=GOC_MODULE_ID,
        committed_result={"committed_effects": ["x"], "commit_applied": True},
        validation_outcome={"status": "approved", "actor_lane_validation": {"status": "approved"}},
        generation={
            "content": "The air tightens.",
            "metadata": {
                "structured_output": {
                    "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "\"Bitte.\""}],
                    "action_lines": [],
                }
            },
        },
        transition_pattern="hard",
        live_player_truth_surface=True,
        render_context={
            "responder_actor_id": "veronique_vallon",
            "player_input": "Wieso sind wir hier?",
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette",
        },
    )
    gm = bundle.get("gm_narration") or []
    joined = "\n".join(str(x) for x in gm)
    assert "reacts immediately" not in joined.lower()


def test_run_visible_render_filters_human_lane_structured_rows() -> None:
    bundle, markers = run_visible_render(
        module_id=GOC_MODULE_ID,
        committed_result={"committed_effects": ["x"], "commit_applied": True},
        validation_outcome={"status": "approved", "actor_lane_validation": {"status": "approved"}},
        generation={
            "content": "Tension holds.",
            "metadata": {
                "structured_output": {
                    "spoken_lines": [
                        {"speaker_id": "annette_reille", "text": "\"Warum sind wir hier?\""},
                        {"speaker_id": "veronique_vallon", "text": "\"Das reicht.\""},
                    ],
                    "action_lines": [{"actor_id": "annette_reille", "text": "Annette lehnt sich vor."}],
                }
            },
        },
        transition_pattern="hard",
        live_player_truth_surface=True,
        render_context={
            "responder_actor_id": "veronique_vallon",
            "player_input": "Wieso sind wir hier?",
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette",
        },
    )
    spoken = bundle.get("spoken_lines") or []
    assert any("das reicht" in str(line).lower() for line in spoken)
    assert not any("annette" in str(line).lower() and "warum" in str(line).lower() for line in spoken)
    rs = bundle.get("render_support") or {}
    hf = rs.get("human_lane_structured_filters") or {}
    assert int(hf.get("spoken_lines_dropped") or 0) >= 1
    assert int(hf.get("action_lines_dropped") or 0) >= 1
    assert "generated_human_actor_output_filtered" in markers
