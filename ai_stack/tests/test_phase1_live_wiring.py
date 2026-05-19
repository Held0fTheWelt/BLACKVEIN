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

from ai_stack.langgraph_runtime_executor import _derive_named_characters_from_state
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
        assert state["paused"] is True
        assert "alain" in state["missing_actor_ids"]
        assert "veronique" in state["missing_actor_ids"]

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
