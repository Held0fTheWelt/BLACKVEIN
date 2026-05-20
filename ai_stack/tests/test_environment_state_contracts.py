from __future__ import annotations

from ai_stack.contracts.environment_state_contracts import (
    apply_action_to_environment_state,
    build_environment_generation_context,
    build_environment_model,
    initial_environment_state,
)


MODULE_ID = "god_of_carnage"


def _first_non_anchor_location_id(model: dict) -> str:
    anchor = str(model.get("anchor_room_id") or "")
    for location_id in (model.get("locations") or {}).keys():
        if str(location_id) != anchor:
            return str(location_id)
    raise AssertionError("canonical environment model did not expose a non-anchor location")


def _first_object_id(model: dict) -> str:
    for object_id in (model.get("objects") or {}).keys():
        return str(object_id)
    raise AssertionError("canonical environment model did not expose objects")


def test_environment_model_derives_rooms_and_objects_from_canonical_policy() -> None:
    model = build_environment_model(module_id=MODULE_ID)
    location_ids = set((model.get("locations") or {}).keys())
    object_ids = set((model.get("objects") or {}).keys())

    assert model.get("schema_version") == "environment_model.v1"
    assert model.get("anchor_room_id") in location_ids
    assert object_ids
    for object_id in object_ids:
        obj = (model.get("objects") or {})[object_id]
        assert obj.get("placement_room_id") in location_ids


def test_initial_environment_state_uses_anchor_room_and_actor_lane_context() -> None:
    model = build_environment_model(module_id=MODULE_ID)
    actor_lane_context = {
        "human_actor_id": "annette_reille",
        "npc_actor_ids": ["alain_reille"],
        "actor_lanes": {"annette_reille": "human", "alain_reille": "npc"},
    }

    state = initial_environment_state(
        module_id=MODULE_ID,
        environment_model=model,
        actor_lane_context=actor_lane_context,
    )

    assert state.get("schema_version") == "environment_state.v1"
    assert state.get("current_room_id") == model.get("anchor_room_id")
    assert set(state.get("actor_locations") or {}).issuperset(actor_lane_context["actor_lanes"].keys())
    assert set(state.get("visible_room_ids") or {}).issubset(set((model.get("locations") or {}).keys()))


def test_committed_movement_updates_environment_state_from_resolved_target() -> None:
    model = build_environment_model(module_id=MODULE_ID)
    initial = initial_environment_state(module_id=MODULE_ID, environment_model=model)
    target_location_id = _first_non_anchor_location_id(model)

    updated = apply_action_to_environment_state(
        environment_state=initial,
        environment_model=model,
        player_action_frame={
            "verb": "move_to",
            "action_kind": "movement",
            "selected_actor_id": "annette_reille",
            "resolved_target": {
                "target_id": target_location_id,
                "target_type": "location",
            },
        },
        affordance_resolution={
            "affordance_status": "allowed",
            "action_commit_policy": "commit_action",
            "resolved_target_id": target_location_id,
            "resolved_target_type": "location",
        },
        turn_number=3,
    )

    assert updated.get("current_room_id") == target_location_id
    assert updated.get("previous_room_id") == initial.get("current_room_id")
    assert (updated.get("actor_locations") or {}).get("annette_reille") == target_location_id
    last_event = (updated.get("last_environment_events") or [])[-1]
    assert last_event.get("target_id") == target_location_id
    assert last_event.get("event_type") == "movement"


def test_committed_object_interaction_updates_prop_state_and_generation_context() -> None:
    model = build_environment_model(module_id=MODULE_ID)
    initial = initial_environment_state(module_id=MODULE_ID, environment_model=model)
    object_id = _first_object_id(model)

    updated = apply_action_to_environment_state(
        environment_state=initial,
        environment_model=model,
        player_action_frame={
            "verb": "activate",
            "action_kind": "object_interaction",
            "resolved_target": {
                "target_id": object_id,
                "target_type": "object",
            },
        },
        affordance_resolution={
            "affordance_status": "allowed",
            "action_commit_policy": "commit_action",
            "resolved_target_id": object_id,
            "resolved_target_type": "object",
        },
        turn_number=4,
    )
    context = build_environment_generation_context(
        environment_state=updated,
        environment_model=model,
    )

    prop_state = (updated.get("prop_states") or {}).get(object_id) or {}
    assert prop_state.get("interaction_state") == "activate"
    assert object_id in (updated.get("salient_object_ids") or [])
    assert context.get("current_room_id") == updated.get("current_room_id")
    assert any(row.get("object_id") == object_id for row in context.get("prop_state_summary") or [])
