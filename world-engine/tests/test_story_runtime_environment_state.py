from __future__ import annotations

from ai_stack.environment_state_contracts import (
    build_environment_model,
    initial_environment_state,
)
from app.story_runtime.manager import (
    StorySession,
    story_session_from_payload,
    story_session_to_payload,
)
from app.story_runtime_shell_readout import build_story_runtime_shell_readout


MODULE_ID = "god_of_carnage"


def test_story_session_payload_round_trips_environment_state() -> None:
    model = build_environment_model(module_id=MODULE_ID)
    environment_state = initial_environment_state(
        module_id=MODULE_ID,
        environment_model=model,
        actor_lane_context={
            "human_actor_id": "annette_reille",
            "npc_actor_ids": ["alain_reille"],
            "actor_lanes": {"annette_reille": "human", "alain_reille": "npc"},
        },
    )
    session = StorySession(
        session_id="session-environment-state",
        module_id=MODULE_ID,
        runtime_projection={"module_id": MODULE_ID},
        current_scene_id="scene_1",
        environment_state=environment_state,
    )

    restored = story_session_from_payload(story_session_to_payload(session))

    assert restored.environment_state == environment_state
    assert restored.environment_state.get("current_room_id") == environment_state.get("current_room_id")
    assert set(restored.environment_state.get("actor_locations") or {}) == set(environment_state.get("actor_locations") or {})


def test_shell_readout_projects_environment_state_fields() -> None:
    model = build_environment_model(module_id=MODULE_ID)
    environment_state = initial_environment_state(
        module_id=MODULE_ID,
        environment_model=model,
    )

    projection = build_story_runtime_shell_readout(
        state={
            "current_scene_id": "scene_1",
            "committed_state": {
                "current_scene_id": "scene_1",
                "environment_state": environment_state,
            },
        },
        last_diagnostic={},
    )

    environment_projection = projection.get("environment_state_now") or {}
    assert environment_projection.get("current_room_id") == environment_state.get("current_room_id")
    assert environment_projection.get("visible_room_ids") == environment_state.get("visible_room_ids")
    assert environment_projection.get("salient_object_ids") == environment_state.get("salient_object_ids")
