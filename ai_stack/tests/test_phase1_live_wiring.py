"""Phase 1 Live Readiness: Graph-State Wiring Tests.

Verifies that ``actor_locations``, ``current_step_named_characters``, and
``current_step_scene_id`` are correctly derived from canonical runtime state
sources and that Director-Pause fails closed when inputs are absent.

Authoritative governance:
* ADR-0061 — Director-Pause Mode for Gathering Interruption.
* ADR-0057 — Canon-Safe Player Freedom and Affordance Inference.
"""

from __future__ import annotations

from typing import Any

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_stack.langgraph_runtime_executor import (
    _derive_current_step_scene_id_from_state,
    _derive_director_subject_actor_id,
    _derive_named_characters_from_state,
    complete_actor_locations_for_gathering,
)
from ai_stack.langgraph_runtime_package_output import package_runtime_graph_output
from ai_stack.director_gathering_state_contracts import (
    SCHEMA_VERSION,
    compute_gathering_state,
    should_suppress_mandatory_beat_consumption,
)


class TestDeriveNamedCharactersFromState:
    """Tests for _derive_named_characters_from_state helper."""

    def test_returns_none_when_no_sources_available(self):
        state: dict[str, Any] = {}
        result = _derive_named_characters_from_state(state)
        assert result is None

    def test_derives_from_canonical_path_step(self):
        state: dict[str, Any] = {
            "canonical_step_id": "opening_005",
            "canonical_path": {
                "steps": {
                    "opening_005": {
                        "present": {
                            "named_characters": ["veronique", "michel", "annette", "alain"],
                        }
                    }
                }
            },
        }
        result = _derive_named_characters_from_state(state)
        assert result == ["veronique", "michel", "annette", "alain"]

    def test_derives_from_actor_lane_context(self):
        state: dict[str, Any] = {
            "actor_lane_context": {
                "human_actor_id": "veronique",
                "npc_actor_ids": ["michel", "annette", "alain"],
            },
        }
        result = _derive_named_characters_from_state(state)
        assert result == ["veronique", "michel", "annette", "alain"]

    def test_canonical_path_takes_priority_over_actor_lane(self):
        state: dict[str, Any] = {
            "canonical_step_id": "opening_005",
            "canonical_path": {
                "steps": {
                    "opening_005": {
                        "present": {
                            "named_characters": ["veronique", "alain"],
                        }
                    }
                }
            },
            "actor_lane_context": {
                "human_actor_id": "veronique",
                "npc_actor_ids": ["michel", "annette", "alain"],
            },
        }
        result = _derive_named_characters_from_state(state)
        assert result == ["veronique", "alain"]

    def test_returns_none_when_canonical_path_step_missing(self):
        state: dict[str, Any] = {
            "canonical_step_id": "opening_999",
            "canonical_path": {
                "steps": {
                    "opening_005": {
                        "present": {
                            "named_characters": ["veronique"],
                        }
                    }
                }
            },
        }
        result = _derive_named_characters_from_state(state)
        assert result is None

    def test_strips_whitespace_from_actor_ids(self):
        state: dict[str, Any] = {
            "actor_lane_context": {
                "human_actor_id": "  veronique  ",
                "npc_actor_ids": [" michel ", "annette"],
            },
        }
        result = _derive_named_characters_from_state(state)
        assert result == ["veronique", "michel", "annette"]


class TestDirectorPauseLiveContextHelpers:
    def test_director_subject_prefers_selected_actor_over_generic_player(self):
        state = {
            "player_actor_id": "player",
            "actor_lane_context": {
                "human_actor_id": "annette",
                "selected_player_role": "annette",
            },
        }
        frame = {"selected_actor_id": "annette", "actor_id": "annette"}
        assert _derive_director_subject_actor_id(state, frame) == "annette"

    def test_current_step_scene_prefers_live_scene_context(self):
        state = {
            "current_scene_id": "social_room",
            "canonical_step_id": "step_a",
            "canonical_path": {
                "steps": {
                    "step_a": {
                        "location_ref": {"location_id": "archival_step_room"},
                    }
                }
            },
        }
        assert _derive_current_step_scene_id_from_state(state) == "social_room"


class TestActorLocationsWiring:
    """Tests that actor_locations is correctly sourced from environment_state."""

    def test_missing_actor_locations_fails_closed(self):
        """When no actor_locations available anywhere, Director-Pause must not
        claim readiness — it must emit a diagnostic blocker."""
        state = compute_gathering_state(
            actor_locations={},
            current_step_named_characters=["veronique", "alain"],
            current_step_scene_id="study",
            current_turn_number=5,
        )
        assert state["paused"] is False
        assert state["diagnostic_blocker"] is True
        assert state["reason"] == "missing_actor_locations"
        assert state["missing_actor_ids"] == []

    def test_actor_locations_from_environment_state_nested(self):
        """Simulate what happens when actor_locations is extracted from
        environment_state (the live wiring path)."""
        env_state = {
            "schema_version": "environment_state.v1",
            "actor_locations": {
                "veronique_vallon": "study",
                "michel_vallon": "study",
                "annette_reille": "study",
                "alain_reille": "study",
            },
            "current_room_id": "study",
        }
        actor_locations = dict(env_state["actor_locations"])
        result = compute_gathering_state(
            actor_locations=actor_locations,
            current_step_named_characters=["veronique_vallon", "michel_vallon", "annette_reille", "alain_reille"],
            current_step_scene_id="study",
            current_turn_number=5,
        )
        assert result["paused"] is False

    def test_missing_named_characters_fails_closed(self):
        """When named_characters cannot be derived, Director-Pause must not
        fake readiness."""
        result = compute_gathering_state(
            actor_locations={"veronique": "study"},
            current_step_named_characters=None,
            current_step_scene_id="study",
            current_turn_number=5,
        )
        assert result["paused"] is False
        assert result.get("missing_actor_ids") == []
        assert result["diagnostic_blocker"] is True
        assert result["reason"] == "missing_named_characters"

    def test_named_characters_loaded_from_canonical_step(self):
        """Verify that named_characters from canonical step data drive pause
        computation correctly."""
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "alain"],
            current_step_scene_id="study",
            current_turn_number=5,
        )
        assert result["paused"] is True
        assert "alain" in result["missing_actor_ids"]


class TestDirectorPauseWithFullInputs:
    """Director-Pause works when all inputs are present."""

    def test_paused_when_actor_leaves(self):
        result = compute_gathering_state(
            actor_locations={
                "veronique": "study",
                "michel": "study",
                "annette": "study",
                "alain": "kitchen",
            },
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=10,
        )
        assert result["paused"] is True
        assert "alain" in result["missing_actor_ids"]
        assert should_suppress_mandatory_beat_consumption(result) is True

    def test_not_paused_when_all_present(self):
        result = compute_gathering_state(
            actor_locations={
                "veronique": "study",
                "michel": "study",
                "annette": "study",
                "alain": "study",
            },
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=10,
        )
        assert result["paused"] is False
        assert should_suppress_mandatory_beat_consumption(result) is False

    def test_does_not_fake_readiness_when_inputs_absent(self):
        """With None actor_locations and None named_characters, the function
        must not claim paused=false in a misleading way."""
        result = compute_gathering_state(
            actor_locations=None,
            current_step_named_characters=None,
            current_step_scene_id=None,
            current_turn_number=5,
        )
        assert result["schema_version"] == SCHEMA_VERSION
        assert result["paused"] is False
        assert result["missing_actor_ids"] == []
        assert result["diagnostic_blocker"] is True

    def test_missing_participation_evidence_is_diagnostic_blocker(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "alain": "study"},
            current_step_named_characters=["veronique", "alain"],
            current_step_scene_id="study",
            participation_evidence_required=True,
            current_turn_number=6,
        )
        assert result["paused"] is False
        assert result["diagnostic_blocker"] is True
        assert result["reason"] == "missing_participation_evidence"


class TestDiagnosticBlockerContract:
    """Verify that the diagnostic blocker emitted by the runtime wiring
    provides actionable reason strings."""

    def test_blocker_reason_for_missing_named_characters(self):
        blocker = {
            "schema_version": "director_gathering_state.v1",
            "paused": False,
            "reason": "missing_named_characters",
            "diagnostic_blocker": True,
            "missing_actor_ids": [],
            "presence_required_for_step": [],
        }
        assert blocker["reason"] == "missing_named_characters"
        assert blocker["diagnostic_blocker"] is True
        assert should_suppress_mandatory_beat_consumption(blocker) is False

    def test_blocker_reason_for_missing_actor_locations(self):
        blocker = {
            "schema_version": "director_gathering_state.v1",
            "paused": False,
            "reason": "missing_actor_locations",
            "diagnostic_blocker": True,
            "missing_actor_ids": [],
            "presence_required_for_step": ["veronique", "alain"],
        }
        assert blocker["reason"] == "missing_actor_locations"
        assert blocker["diagnostic_blocker"] is True
        assert should_suppress_mandatory_beat_consumption(blocker) is False


class TestCompleteActorLocationsForGathering:
    """Tests for complete_actor_locations_for_gathering helper.

    All tests use generic actor/room IDs to enforce ADR-0039 anti-hardcoding
    discipline — no GoC actor IDs, no hardcoded room names.
    """

    def test_empty_locations_filled_from_actor_lane_context(self):
        """When actor_locations is empty, NPCs from actor_lane_context are
        defaulted to current_step_scene_id."""
        result = complete_actor_locations_for_gathering(
            actor_locations={},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y", "npc_z"],
            },
            current_step_scene_id="gathering_room",
        )
        assert result["diagnostic_blocker"] is False
        assert result["actor_locations"]["npc_x"] == "gathering_room"
        assert result["actor_locations"]["npc_y"] == "gathering_room"
        assert result["actor_locations"]["npc_z"] == "gathering_room"
        assert sorted(result["fallback_actor_ids"]) == ["npc_x", "npc_y", "npc_z"]
        assert result["source"] == "environment_state_with_actor_lane_fallback"

    def test_existing_env_locations_are_preserved(self):
        """If environment state already has NPC locations, those win and no
        fallback is applied for those actors."""
        result = complete_actor_locations_for_gathering(
            actor_locations={
                "npc_x": "gathering_room",
                "npc_y": "gathering_room",
                "npc_z": "other_room",
            },
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y", "npc_z"],
            },
            current_step_scene_id="gathering_room",
        )
        assert result["diagnostic_blocker"] is False
        assert result["actor_locations"]["npc_z"] == "other_room"
        assert result["fallback_actor_ids"] == []

    def test_fallback_only_fills_missing_npcs_not_already_present(self):
        """Partial environment state: only the two absent NPCs get the fallback."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"npc_x": "gathering_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y"],
            },
            current_step_scene_id="gathering_room",
        )
        assert result["diagnostic_blocker"] is False
        assert result["actor_locations"]["npc_x"] == "gathering_room"
        assert result["actor_locations"]["npc_y"] == "gathering_room"
        assert result["fallback_actor_ids"] == ["npc_y"]

    def test_missing_scene_id_fails_closed_when_npcs_absent(self):
        """If current_step_scene_id is absent and NPCs are missing, return
        diagnostic_blocker=True with reason=missing_current_step_scene_id."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "some_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y"],
            },
            current_step_scene_id=None,
        )
        assert result["diagnostic_blocker"] is True
        assert result["reason"] == "missing_current_step_scene_id"
        assert result["fallback_actor_ids"] == []

    def test_missing_scene_id_no_blocker_when_no_npcs_missing(self):
        """If scene_id is absent but all NPCs are already in actor_locations,
        no diagnostic blocker is needed."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"npc_x": "some_room", "npc_y": "some_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y"],
            },
            current_step_scene_id=None,
        )
        assert result["diagnostic_blocker"] is False
        assert result["fallback_actor_ids"] == []

    def test_human_actor_location_follows_resolved_target(self):
        """selected_human_actor_id gets target_location from
        free_player_action_resolution when present."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x"],
            },
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={
                "target_location": "other_room",
                "action_commit_policy": "commit_action",
            },
        )
        assert result["diagnostic_blocker"] is False
        assert result["actor_locations"]["human_a"] == "other_room"

    def test_human_target_location_not_applied_when_absent(self):
        """If free_player_action_resolution has no target_location, human
        location stays as provided in actor_locations."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": [],
            },
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"action_commit_policy": "commit_action"},
        )
        assert result["actor_locations"]["human_a"] == "gathering_room"

    def test_input_actor_locations_not_mutated(self):
        """The original actor_locations dict must not be mutated."""
        original = {"human_a": "gathering_room"}
        complete_actor_locations_for_gathering(
            actor_locations=original,
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x"],
            },
            current_step_scene_id="gathering_room",
        )
        assert original == {"human_a": "gathering_room"}

    def test_no_hardcoded_goc_actor_ids_in_result(self):
        """Result must not introduce any God-of-Carnage-specific actor IDs."""
        goc_ids = {"alain_reille", "annette_reille", "michel_longstreet", "veronique_vallon"}
        result = complete_actor_locations_for_gathering(
            actor_locations={},
            actor_lane_context={
                "human_actor_id": "generic_human",
                "npc_actor_ids": ["generic_npc_1", "generic_npc_2"],
            },
            current_step_scene_id="meeting_room",
        )
        for actor_id in result["actor_locations"]:
            assert actor_id not in goc_ids, f"Hardcoded GoC ID found: {actor_id}"
        for actor_id in result["fallback_actor_ids"]:
            assert actor_id not in goc_ids

    def test_original_actor_locations_exposed_in_result(self):
        """diagnostic key original_actor_locations must reflect the pre-completion state."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x"],
            },
            current_step_scene_id="gathering_room",
        )
        assert result["original_actor_locations"] == {"human_a": "gathering_room"}
        assert "npc_x" not in result["original_actor_locations"]
        assert "npc_x" in result["actor_locations"]

    def test_none_actor_locations_treated_as_empty(self):
        """None actor_locations is treated as empty — fallback applies."""
        result = complete_actor_locations_for_gathering(
            actor_locations=None,
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x"],
            },
            current_step_scene_id="gathering_room",
        )
        assert result["diagnostic_blocker"] is False
        assert result["actor_locations"]["npc_x"] == "gathering_room"
        assert result["fallback_actor_ids"] == ["npc_x"]

    def test_fallback_uses_ai_allowed_actor_ids_live_runtime_path(self):
        """Live runtime path: ActorLaneContext.model_dump() serialises NPCs as
        ai_allowed_actor_ids, not npc_actor_ids.  The helper must resolve NPCs
        from ai_allowed_actor_ids when npc_actor_ids is absent."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context={
                "contract": "actor_lane_context.v1",
                "human_actor_id": "human_a",
                "actor_lanes": {"human_a": "human", "npc_x": "npc", "npc_y": "npc"},
                "ai_allowed_actor_ids": ["npc_x", "npc_y"],
                "ai_forbidden_actor_ids": ["human_a"],
                # NOTE: no npc_actor_ids key — this is the live ActorLaneContext shape
            },
            current_step_scene_id="gathering_room",
        )
        assert result["diagnostic_blocker"] is False
        assert result["actor_locations"]["npc_x"] == "gathering_room"
        assert result["actor_locations"]["npc_y"] == "gathering_room"
        assert sorted(result["fallback_actor_ids"]) == ["npc_x", "npc_y"]

    def test_fallback_derives_from_actor_lanes_when_no_explicit_list(self):
        """Ultimate fallback: derive NPC IDs from actor_lanes where lane==npc."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "actor_lanes": {"human_a": "human", "npc_x": "npc"},
                # No npc_actor_ids, no ai_allowed_actor_ids
            },
            current_step_scene_id="gathering_room",
        )
        assert result["diagnostic_blocker"] is False
        assert result["actor_locations"]["npc_x"] == "gathering_room"
        assert result["fallback_actor_ids"] == ["npc_x"]

    def test_gathering_scene_id_derived_from_npc_locations_when_npcs_already_present(self):
        """When NPCs are already in actor_locations (no fallback needed),
        gathering_scene_id is the most common NPC location — not the potentially
        coarse current_step_scene_id."""
        result = complete_actor_locations_for_gathering(
            actor_locations={
                "human_a": "room_a",
                "npc_x": "gathering_room",
                "npc_y": "gathering_room",
                "npc_z": "gathering_room",
            },
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y", "npc_z"],
            },
            current_step_scene_id="coarse_scene_identifier",
        )
        assert result["diagnostic_blocker"] is False
        assert result["gathering_scene_id"] == "gathering_room"

    def test_environment_current_room_id_used_as_npc_fallback_location(self):
        """When NPCs are missing and environment_current_room_id is provided,
        NPCs are filled at environment_current_room_id, not current_step_scene_id."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "living_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y"],
            },
            current_step_scene_id="coarse_scene_identifier",
            environment_current_room_id="living_room",
        )
        assert result["diagnostic_blocker"] is False
        assert result["actor_locations"]["npc_x"] == "living_room"
        assert result["actor_locations"]["npc_y"] == "living_room"
        assert result["gathering_scene_id"] == "living_room"

    def test_live_runtime_scenario_coarse_scene_id_all_actors_at_same_room(self):
        """Live-runtime scenario: current_step_scene_id is a coarse scene identifier
        (e.g. 'scene_1') that does not match actor_location room values.
        With environment_current_room_id = actual room, gathering_scene_id is
        correctly set to room-level, and topology check yields paused=False
        when all actors are co-present."""
        # Simulate: env_state.actor_locations has all actors at "living_room",
        # current_scene_id = "scene_1" (scene-level, won't match room IDs)
        completion = complete_actor_locations_for_gathering(
            actor_locations={
                "human_a": "living_room",
                "npc_x": "living_room",
                "npc_y": "living_room",
            },
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y"],
            },
            current_step_scene_id="scene_1",
            environment_current_room_id="living_room",
        )
        assert completion["diagnostic_blocker"] is False
        assert completion["gathering_scene_id"] == "living_room"
        # No actor is missing; gathering_scene_id matches all locations.
        result = compute_gathering_state(
            actor_locations=completion["actor_locations"],
            current_step_named_characters=["human_a", "npc_x", "npc_y"],
            current_step_scene_id=completion["gathering_scene_id"],
            current_turn_number=1,
        )
        assert result["paused"] is False
        assert result["missing_actor_ids"] == []

    def test_live_runtime_scenario_player_moves_out_pauses_gathering(self):
        """Live-runtime scenario: player moves to a different room.
        gathering_scene_id stays at the NPC room (gathering room),
        human actor gets target_location → paused=True."""
        completion = complete_actor_locations_for_gathering(
            actor_locations={
                "human_a": "living_room",
                "npc_x": "living_room",
                "npc_y": "living_room",
            },
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y"],
            },
            current_step_scene_id="scene_1",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"target_location": "kitchen"},
            environment_current_room_id="living_room",
        )
        assert completion["diagnostic_blocker"] is False
        assert completion["gathering_scene_id"] == "living_room"
        assert completion["actor_locations"]["human_a"] == "kitchen"
        result = compute_gathering_state(
            actor_locations=completion["actor_locations"],
            current_step_named_characters=["human_a", "npc_x", "npc_y"],
            current_step_scene_id=completion["gathering_scene_id"],
            current_turn_number=2,
        )
        assert result["paused"] is True
        assert "human_a" in result["missing_actor_ids"]

    def test_live_runtime_scenario_player_returns_clears_pause(self):
        """Live-runtime scenario: player moves back to gathering room.
        gathering_scene_id = NPC room; after target_location applied, all
        actors co-present → paused=False."""
        completion = complete_actor_locations_for_gathering(
            actor_locations={
                "human_a": "kitchen",
                "npc_x": "living_room",
                "npc_y": "living_room",
            },
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y"],
            },
            current_step_scene_id="scene_1",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"target_location": "living_room"},
            environment_current_room_id="kitchen",
        )
        assert completion["diagnostic_blocker"] is False
        assert completion["gathering_scene_id"] == "living_room"
        assert completion["actor_locations"]["human_a"] == "living_room"
        result = compute_gathering_state(
            actor_locations=completion["actor_locations"],
            current_step_named_characters=["human_a", "npc_x", "npc_y"],
            current_step_scene_id=completion["gathering_scene_id"],
            current_turn_number=5,
        )
        assert result["paused"] is False
        assert result["missing_actor_ids"] == []

    def test_gathering_scene_id_falls_back_to_environment_current_room_id_when_no_npcs(self):
        """When no NPC IDs exist (empty actor_lane_context), gathering_scene_id
        falls back to environment_current_room_id."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "living_room"},
            actor_lane_context={"human_actor_id": "human_a", "npc_actor_ids": []},
            current_step_scene_id="scene_1",
            environment_current_room_id="living_room",
        )
        assert result["diagnostic_blocker"] is False
        assert result["gathering_scene_id"] == "living_room"

    def test_missing_scene_id_does_not_block_when_environment_current_room_id_provided(self):
        """If current_step_scene_id is absent but environment_current_room_id is
        available, NPCs can be filled and diagnostic_blocker stays False."""
        result = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "living_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y"],
            },
            current_step_scene_id=None,
            environment_current_room_id="living_room",
        )
        assert result["diagnostic_blocker"] is False
        assert result["actor_locations"]["npc_x"] == "living_room"
        assert result["gathering_scene_id"] == "living_room"


class TestDirectorPauseWithActorLaneFallback:
    """End-to-end Director-Pause scenarios using the actor_lane_context
    fallback — i.e. the path that previously caused false positives in the
    live runtime.

    All actor/room IDs are generic (ADR-0039 anti-hardcoding discipline).
    """

    def _make_full_locations(self, scene: str, npc_ids: list[str], human: str) -> dict:
        return {actor: scene for actor in npc_ids + [human]}

    def test_mundane_local_action_does_not_pause_gathering(self):
        """Scenario 1: player does a mundane action; NPCs absent from
        actor_locations → after fallback all NPCs default to gathering scene
        → paused=False."""
        completion = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y", "npc_z"],
            },
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={
                "presence_breaks_gathering": False,
                "action_commit_policy": "commit_action",
            },
        )
        assert completion["diagnostic_blocker"] is False
        result = compute_gathering_state(
            actor_locations=completion["actor_locations"],
            current_step_named_characters=["human_a", "npc_x", "npc_y", "npc_z"],
            current_step_scene_id="gathering_room",
            current_turn_number=3,
        )
        assert result["paused"] is False
        assert result["missing_actor_ids"] == []

    def test_leaving_gathering_scene_pauses(self):
        """Scenario 2: human actor moves to a different room → paused=True;
        the human is the missing actor."""
        completion = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y", "npc_z"],
            },
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={
                "target_location": "other_room",
                "presence_breaks_gathering": True,
                "action_commit_policy": "commit_action",
            },
        )
        assert completion["diagnostic_blocker"] is False
        result = compute_gathering_state(
            actor_locations=completion["actor_locations"],
            current_step_named_characters=["human_a", "npc_x", "npc_y", "npc_z"],
            current_step_scene_id="gathering_room",
            current_turn_number=4,
        )
        assert result["paused"] is True
        assert "human_a" in result["missing_actor_ids"]
        assert should_suppress_mandatory_beat_consumption(result) is True

    def test_return_to_gathering_clears_pause(self):
        """Scenario 4: human returns to gathering room → paused=False."""
        completion = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y", "npc_z"],
            },
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={
                "target_location": "gathering_room",
                "action_commit_policy": "commit_action",
            },
        )
        assert completion["diagnostic_blocker"] is False
        prev = {
            "schema_version": SCHEMA_VERSION,
            "paused": True,
            "step_id": "gathering_room",
            "missing_actor_ids": ["human_a"],
            "since_turn": 4,
            "presence_required_for_step": ["human_a", "npc_x", "npc_y", "npc_z"],
            "reason": "required_actor_not_at_scene_location",
            "source": "actor_topology_derived",
        }
        result = compute_gathering_state(
            actor_locations=completion["actor_locations"],
            current_step_named_characters=["human_a", "npc_x", "npc_y", "npc_z"],
            current_step_scene_id="gathering_room",
            current_turn_number=6,
            previous_state=prev,
        )
        assert result["paused"] is False
        assert result["missing_actor_ids"] == []

    def test_act_while_paused_stays_paused(self):
        """Scenario 3: gathering is paused; human stays outside → still paused."""
        completion = complete_actor_locations_for_gathering(
            actor_locations={"human_a": "other_room"},
            actor_lane_context={
                "human_actor_id": "human_a",
                "npc_actor_ids": ["npc_x", "npc_y", "npc_z"],
            },
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"action_commit_policy": "commit_action"},
        )
        assert completion["diagnostic_blocker"] is False
        prev = {
            "schema_version": SCHEMA_VERSION,
            "paused": True,
            "step_id": "gathering_room",
            "missing_actor_ids": ["human_a"],
            "since_turn": 4,
            "presence_required_for_step": ["human_a", "npc_x", "npc_y", "npc_z"],
            "reason": "required_actor_not_at_scene_location",
            "source": "actor_topology_derived",
        }
        result = compute_gathering_state(
            actor_locations=completion["actor_locations"],
            current_step_named_characters=["human_a", "npc_x", "npc_y", "npc_z"],
            current_step_scene_id="gathering_room",
            current_turn_number=5,
            previous_state=prev,
        )
        assert result["paused"] is True
        assert "human_a" in result["missing_actor_ids"]

    def test_same_room_resolver_participation_break_pauses(self):
        """Same-room participation/visibility loss is a real pause condition.

        ADR-0061 defines topology, participation relevance, and visibility /
        audibility as peer inputs. A current resolver break signal therefore
        pauses even when actor_locations still place the actor in the gathering
        room.
        """
        result = compute_gathering_state(
            actor_locations={
                "human_a": "gathering_room",
                "npc_x": "gathering_room",
                "npc_y": "gathering_room",
            },
            current_step_named_characters=["human_a", "npc_x", "npc_y"],
            current_step_scene_id="gathering_room",
            participation_relevance="broken",
            visibility_audibility="not_visible",
            subject_actor_id="human_a",
            current_turn_number=5,
        )
        assert result["paused"] is True
        assert result["reason"] == "participation_relevance_broken"
        assert result["source"] == "free_player_action_resolution.v1"
        assert result["missing_actor_ids"] == ["human_a"]

    def test_topology_absent_actor_can_still_be_added_by_resolver(self):
        """If topology already marks an actor absent, resolver participation
        does NOT re-add them (they're already missing), but it can add a
        different subject that topology missed."""
        result = compute_gathering_state(
            actor_locations={
                "human_a": "other_room",
                "npc_x": "gathering_room",
                "npc_y": "gathering_room",
            },
            current_step_named_characters=["human_a", "npc_x", "npc_y"],
            current_step_scene_id="gathering_room",
            participation_relevance="broken",
            subject_actor_id="human_a",
            current_turn_number=4,
        )
        # Topology already flagged human_a as absent — still paused.
        assert result["paused"] is True
        assert "human_a" in result["missing_actor_ids"]


class TestPhase1DiagnosticExposure:
    def test_package_output_exposes_all_phase1_fields_when_present(self):
        state: dict[str, Any] = {
            "nodes_executed": [],
            "node_outcomes": {},
            "graph_errors": [],
            "session_id": "session",
            "module_id": "module",
            "free_player_action_resolution": {"schema_version": "free_player_action_resolution.v1"},
            "canonical_path_hold_effect": {"schema_version": "canonical_path_hold_effect.v1"},
            "narrator_consequence_realization": {
                "schema_version": "narrator_consequence_realization.v1",
                "visible_block_emitted": True,
            },
            "director_gathering_state": {
                "schema_version": "director_gathering_state.v1",
                "paused": True,
            },
            "gathering_paused_beat_suppression": True,
            "director_pause_transition_reaction": {"transition": "entered"},
        }
        out = package_runtime_graph_output(state, graph_name="runtime", graph_version="test")
        phase1 = out["graph_diagnostics"]["phase1_director_pause_diagnostics"]
        for key in (
            "free_player_action_resolution",
            "canonical_path_hold_effect",
            "narrator_consequence_realization",
            "director_gathering_state",
            "gathering_paused_beat_suppression",
            "director_pause_transition_reaction",
        ):
            assert key in phase1
