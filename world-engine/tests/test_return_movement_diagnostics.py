"""Path summary and diagnostics for implicit return movement (engine package)."""

from __future__ import annotations

import sys
from pathlib import Path

WORLD_ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(WORLD_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORLD_ENGINE_ROOT))
loaded_app = sys.modules.get("app")
loaded_app_file = str(getattr(loaded_app, "__file__", "") or "")
if loaded_app is not None and not loaded_app_file.startswith(str(WORLD_ENGINE_ROOT)):
    for name in [key for key in sys.modules if key == "app" or key.startswith("app.")]:
        sys.modules.pop(name, None)

from app.story_runtime.manager import (  # noqa: E402
    StorySession,
    _build_langfuse_path_summary,
    _compute_action_consequence_diagnostics,
)


def test_return_movement_public_payload_contains_action_context_diagnostics() -> None:
    session = StorySession(
        session_id="return-movement-diag",
        module_id="god_of_carnage",
        runtime_projection={
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette_reille",
            "npc_actor_ids": ["michel_longstreet"],
            "actor_lanes": {"annette_reille": "human"},
        },
        current_scene_id="scene_apartment",
    )
    graph_state = {
        "player_input": "Ich gehe zurück.",
        "interpreted_input": {
            "player_input_kind": "movement_action",
            "movement_return_intent": True,
            "speech_projection_allowed": False,
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        },
        "affordance_resolution": {
            "affordance_status": "allowed",
            "action_commit_policy": "commit_action",
            "resolved_target_id": "living_room",
            "target_resolution_source": "player_local_context.previous_location_id",
        },
        "local_context_transition": {
            "transition_type": "movement",
            "new_area_established": True,
            "location_found": True,
        },
        "narrator_consequence_plan": {
            "consequence_text": "Der Salon empfängt die Anspannung zurück.",
            "consequence_type": "area_transition",
            "source": "scene_affordance_detail",
        },
        "player_local_context": {
            "current_location_id": "living_room",
            "previous_location_id": "bathroom",
        },
        "generation": {
            "success": True,
            "fallback_used": False,
            "metadata": {
                "adapter": "action_resolution_authoritative",
                "authoritative_action_resolution": True,
            },
        },
        "nodes_executed": ["authoritative_action_resolution"],
        "routing": {"action_resolution_short_path": True},
    }
    event = {
        "turn_number": 1,
        "turn_kind": "player",
        "raw_input": "Ich gehe zurück.",
    }
    summary = _build_langfuse_path_summary(session=session, graph_state=graph_state, event=event)
    assert summary.get("movement_return_intent") is True
    assert summary.get("resolved_target_id") == "living_room"
    diag = _compute_action_consequence_diagnostics(summary)
    assert diag["status"] == "evaluated"
    assert diag.get("movement_return_intent") is True
    assert diag.get("resolved_target_id") == "living_room"
