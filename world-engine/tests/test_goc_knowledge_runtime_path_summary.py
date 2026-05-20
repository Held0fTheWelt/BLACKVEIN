"""Path-summary diagnostics for GoC knowledge runtime gates."""

from __future__ import annotations

import sys
from pathlib import Path

from ai_stack.god_of_carnage_yaml_authority import (
    load_goc_hard_forbidden_rules_yaml,
    load_goc_opening_scene_sequence_yaml,
)

WORLD_ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(WORLD_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORLD_ENGINE_ROOT))
loaded_app = sys.modules.get("app")
loaded_app_file = str(getattr(loaded_app, "__file__", "") or "")
if loaded_app is not None and not loaded_app_file.startswith(str(WORLD_ENGINE_ROOT)):
    for name in [key for key in sys.modules if key == "app" or key.startswith("app.")]:
        sys.modules.pop(name, None)

from app.story_runtime.manager import StorySession, _build_langfuse_path_summary


def test_path_summary_exposes_opening_and_forbidden_gate_scores() -> None:
    opening = load_goc_opening_scene_sequence_yaml()
    hard = load_goc_hard_forbidden_rules_yaml()
    session = StorySession(
        session_id="knowledge-path-summary-test",
        module_id="god_of_carnage",
        runtime_projection={
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette_reille",
            "npc_actor_ids": ["michel_longstreet", "veronique_vallon", "alain_reille"],
            "actor_lanes": {"annette_reille": "human", "michel_longstreet": "npc"},
        },
        current_scene_id="scene_1_opening",
    )
    blocks = [
        {
            "block_type": "narrator",
            "opening_event_id": "event_01_triggering_incident",
            "text": (
                "Auf dem Schulhof ist der Streit zwischen den Jungen ernst geworden: "
                "ein Stock, ein verletzter Zahn, ein Moment, den Erwachsene nicht ignorieren koennen."
            ),
        },
        {
            "block_type": "narrator",
            "opening_event_id": "event_02_adult_consequence",
            "text": "Darum treffen sich die Eltern in der Wohnung der Vallons und halten die Hoeflichkeit fest.",
        },
        {
            "block_type": "narrator",
            "opening_event_id": "event_03_arrival_threshold",
            "text": "An der Tuer wird aus Besuch eine Pflicht; Gaeste und Gastgeber treten ueber dieselbe Schwelle.",
        },
        {
            "block_type": "narrator",
            "opening_event_id": "event_04_apartment_as_stage",
            "text": "Im Wohnzimmer ordnen Stuehle, Couchtisch, Kunstbaende und Tulpen die Spannung wie eine Buehne.",
        },
        {
            "block_type": "narrator",
            "opening_event_id": "event_05_role_anchor",
            "text": "Annette Reille ist als Gast im Raum, mit Platz zu sprechen oder zu beobachten.",
        },
        {
            "block_type": "narrator",
            "opening_event_id": "event_06_first_playable_moment",
            "text": "Jetzt wartet ein erster spielbarer Moment, und die naechste Handlung bleibt offen.",
        },
        {
            "block_type": "actor_line",
            "actor_id": "michel_longstreet",
            "speaker_label": "Michel",
            "text": "Vielleicht beginnen wir ruhig.",
        },
    ]
    event = {
        "turn_number": 0,
        "turn_kind": "opening",
        "visible_output_bundle": {"scene_blocks": blocks},
        "validation_outcome": {"status": "approved", "reason": "goc_default_validator_pass"},
    }
    graph_state = {
        "opening_scene_sequence": opening,
        "hard_forbidden_rules": hard,
        "turn_input_class": "opening",
        "scene_plan_record": {"opening_first_playable_scene_phase": "phase_1"},
        "current_scene_id": "scene_1_opening",
        "nodes_executed": ["retrieve_context", "validate_seam", "render_visible"],
        "validation_outcome": event["validation_outcome"],
        "visible_output_bundle": event["visible_output_bundle"],
    }

    summary = _build_langfuse_path_summary(session=session, graph_state=graph_state, event=event)

    assert summary["opening_scene_sequence_id"] == "goc_opening_sequence_v1"
    assert summary["opening_event_coverage_pass"] is True
    assert summary["hard_forbidden_absent"] is True
    assert summary["opening_summary_only_absent"] is True
