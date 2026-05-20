"""PR-C — Director Pause Mode tests.

Tests for ``director_gathering_state.v1``, ``compute_gathering_state``,
the beat-consumption gate, narrator transition reaction hooks, diagnostic
exposure, and guardrails.

Authoritative governance:

* ADR-0061 — Director-Pause Mode for Gathering Interruption.
* ADR-0039 — No hardcoded oracle bypass; semantic names only.
* NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md §3.4.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from ai_stack.director.director_gathering_state_contracts import (
    PAUSE_REASON_ACTOR_NOT_AT_SCENE,
    PAUSE_REASON_PARTICIPATION_BROKEN,
    PAUSE_REASON_VISIBILITY_LOST,
    PAUSE_REASONS,
    PAUSE_SOURCE_RESOLVER_EVIDENCE,
    PAUSE_SOURCE_TOPOLOGY,
    PAUSE_SOURCES,
    SCHEMA_VERSION,
    compute_gathering_state,
    gathering_pause_is_transition,
    should_suppress_mandatory_beat_consumption,
)


class TestComputeGatheringStateSchema:
    """Schema and version tests."""

    def test_schema_version_constant(self):
        assert SCHEMA_VERSION == "director_gathering_state.v1"

    def test_pause_reasons_are_closed_enum(self):
        assert len(PAUSE_REASONS) == 3
        assert PAUSE_REASON_ACTOR_NOT_AT_SCENE in PAUSE_REASONS
        assert PAUSE_REASON_PARTICIPATION_BROKEN in PAUSE_REASONS
        assert PAUSE_REASON_VISIBILITY_LOST in PAUSE_REASONS

    def test_pause_sources_are_closed_enum(self):
        assert len(PAUSE_SOURCES) == 2
        assert PAUSE_SOURCE_RESOLVER_EVIDENCE in PAUSE_SOURCES
        assert PAUSE_SOURCE_TOPOLOGY in PAUSE_SOURCES


class TestComputeGatheringStatePaused:
    """Tests that compute_gathering_state produces paused=True correctly."""

    def test_paused_when_required_actor_missing_from_scene(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=12,
        )
        assert result["schema_version"] == SCHEMA_VERSION
        assert result["paused"] is True
        assert "alain" in result["missing_actor_ids"]
        assert result["since_turn"] == 12
        assert result["presence_required_for_step"] == ["veronique", "michel", "annette", "alain"]
        assert result["reason"] in PAUSE_REASONS

    def test_paused_when_multiple_actors_missing(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "kitchen"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=5,
        )
        assert result["paused"] is True
        assert sorted(result["missing_actor_ids"]) == ["alain", "annette", "michel"]

    def test_paused_when_actor_location_unknown(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=3,
        )
        assert result["paused"] is True
        assert "alain" in result["missing_actor_ids"]

    def test_participation_break_within_same_location_can_pause(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "study"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            participation_relevance="broken",
            subject_actor_id="annette",
            current_turn_number=7,
        )
        assert result["paused"] is True
        assert result["reason"] == PAUSE_REASON_PARTICIPATION_BROKEN
        assert "annette" in result["missing_actor_ids"]

    def test_visibility_audibility_lost_causes_pause(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "study"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            visibility_audibility="not_audible",
            subject_actor_id="annette",
            current_turn_number=9,
        )
        assert result["paused"] is True
        assert result["reason"] == PAUSE_REASON_VISIBILITY_LOST
        assert "annette" in result["missing_actor_ids"]

    def test_missing_actor_ids_are_stable_and_sorted(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "annette": "kitchen"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=1,
        )
        assert result["missing_actor_ids"] == sorted(result["missing_actor_ids"])
        assert result["missing_actor_ids"] == ["alain", "annette", "michel"]


class TestComputeGatheringStateNotPaused:
    """Tests that compute_gathering_state produces paused=False correctly."""

    def test_not_paused_when_all_required_actors_present(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "study"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=5,
        )
        assert result["schema_version"] == SCHEMA_VERSION
        assert result["paused"] is False
        assert result["missing_actor_ids"] == []
        assert "step_id" not in result
        assert "since_turn" not in result

    def test_not_paused_when_no_named_characters(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study"},
            current_step_named_characters=[],
            current_step_scene_id="study",
            current_turn_number=1,
        )
        assert result["paused"] is False

    def test_not_paused_when_no_scene_id(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study"},
            current_step_named_characters=["veronique", "michel"],
            current_step_scene_id=None,
            current_turn_number=1,
        )
        assert result["paused"] is False

    def test_visibility_audibility_does_not_pause_when_still_present(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "study"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            visibility_audibility="still_audible",
            current_turn_number=4,
        )
        assert result["paused"] is False


class TestComputeGatheringStatePersistence:
    """Tests for pause persistence and return-clears-pause."""

    def test_previous_pause_persists_when_still_missing(self):
        prev = {
            "schema_version": SCHEMA_VERSION,
            "paused": True,
            "step_id": "study",
            "missing_actor_ids": ["alain"],
            "since_turn": 10,
            "presence_required_for_step": ["veronique", "michel", "annette", "alain"],
            "reason": PAUSE_REASON_ACTOR_NOT_AT_SCENE,
            "source": PAUSE_SOURCE_TOPOLOGY,
        }
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=14,
            previous_state=prev,
        )
        assert result["paused"] is True
        assert result["since_turn"] == 10  # preserved from entry

    def test_return_clears_pause(self):
        prev = {
            "schema_version": SCHEMA_VERSION,
            "paused": True,
            "step_id": "study",
            "missing_actor_ids": ["alain"],
            "since_turn": 10,
            "presence_required_for_step": ["veronique", "michel", "annette", "alain"],
            "reason": PAUSE_REASON_ACTOR_NOT_AT_SCENE,
            "source": PAUSE_SOURCE_TOPOLOGY,
        }
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "study"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=15,
            previous_state=prev,
        )
        assert result["paused"] is False
        assert result["missing_actor_ids"] == []

    def test_mandatory_beats_can_resume_after_pause_clears(self):
        state_paused = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=12,
        )
        assert should_suppress_mandatory_beat_consumption(state_paused) is True

        state_returned = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "study"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=15,
            previous_state=state_paused,
        )
        assert should_suppress_mandatory_beat_consumption(state_returned) is False


class TestBeatConsumptionGate:
    """Tests for mandatory-beat consumption suppression."""

    def test_suppressed_when_paused(self):
        state = {"schema_version": SCHEMA_VERSION, "paused": True}
        assert should_suppress_mandatory_beat_consumption(state) is True

    def test_not_suppressed_when_not_paused(self):
        state = {"schema_version": SCHEMA_VERSION, "paused": False}
        assert should_suppress_mandatory_beat_consumption(state) is False

    def test_not_suppressed_when_none(self):
        assert should_suppress_mandatory_beat_consumption(None) is False

    def test_not_suppressed_when_empty_dict(self):
        assert should_suppress_mandatory_beat_consumption({}) is False


class TestGatheringPauseTransition:
    """Tests for pause transition detection."""

    def test_transition_entered(self):
        prev = {"paused": False}
        curr = {"paused": True}
        assert gathering_pause_is_transition(previous_state=prev, current_state=curr) == "entered"

    def test_transition_cleared(self):
        prev = {"paused": True}
        curr = {"paused": False}
        assert gathering_pause_is_transition(previous_state=prev, current_state=curr) == "cleared"

    def test_no_transition_both_paused(self):
        prev = {"paused": True}
        curr = {"paused": True}
        assert gathering_pause_is_transition(previous_state=prev, current_state=curr) is None

    def test_no_transition_both_not_paused(self):
        prev = {"paused": False}
        curr = {"paused": False}
        assert gathering_pause_is_transition(previous_state=prev, current_state=curr) is None

    def test_no_transition_when_no_previous(self):
        curr = {"paused": True}
        assert gathering_pause_is_transition(previous_state=None, current_state=curr) == "entered"


class TestNarratorTransitionReaction:
    """Tests for narrator transition reaction on pause entry."""

    def test_transition_false_to_true_can_emit_narrator_reaction(self):
        prev = {"paused": False}
        curr = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=12,
            previous_state=prev,
        )
        transition = gathering_pause_is_transition(previous_state=prev, current_state=curr)
        assert transition == "entered"

    def test_no_hardcoded_text_in_contract_output(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=12,
        )
        for value in result.values():
            if isinstance(value, str):
                assert len(value) < 80, "No prose text should appear in contract output"


class TestDiagnosticExposure:
    """Tests that Director-Pause state is diagnostic-exposable."""

    def test_gathering_state_has_required_diagnostic_fields_when_paused(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=12,
        )
        assert "schema_version" in result
        assert "paused" in result
        assert "missing_actor_ids" in result
        assert "presence_required_for_step" in result
        assert "step_id" in result
        assert "since_turn" in result
        assert "reason" in result
        assert "source" in result

    def test_gathering_state_has_required_diagnostic_fields_when_not_paused(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "study"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=5,
        )
        assert "schema_version" in result
        assert "paused" in result
        assert "missing_actor_ids" in result
        assert "presence_required_for_step" in result

    def test_no_mutation_control_fields_exposed(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=12,
        )
        forbidden_keys = {"_mutate", "_set_state", "_control", "_command", "action"}
        assert not forbidden_keys.intersection(result.keys())


class TestGuardrails:
    """Guardrail tests — PR-C must not introduce prohibited patterns."""

    def test_no_npc_pulse_in_module(self):
        import ai_stack.director.director_gathering_state_contracts as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        assert "npc_pulse" not in source.lower()
        assert "pulse_tick" not in source.lower()
        assert "motivation_score" not in source.lower()

    def test_no_block_stream_bus_in_module(self):
        import ai_stack.director.director_gathering_state_contracts as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        assert "block_stream_bus" not in source.lower()
        assert "event_stream" not in source.lower()

    def test_no_step_mode_switch_in_module(self):
        import ai_stack.director.director_gathering_state_contracts as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        assert "step.mode" not in source
        assert "step_mode" not in source.lower()

    def test_no_active_pi_keys_in_module(self):
        import ai_stack.director.director_gathering_state_contracts as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        pi_patterns = [
            re.compile(r"\bPi\d+\b"),
            re.compile(r"\bΠ\d+\b"),
            re.compile(r"\bpi_\d+\b"),
        ]
        for pattern in pi_patterns:
            assert not pattern.search(source), f"Found Pi/Π runtime key: {pattern.pattern}"

    def test_no_verb_room_action_whitelist(self):
        import ai_stack.director.director_gathering_state_contracts as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        whitelist_patterns = [
            re.compile(r"verb_whitelist|action_whitelist|room_whitelist", re.IGNORECASE),
            re.compile(r'\["go",\s*"move"', re.IGNORECASE),
            re.compile(r'\["kitchen",\s*"hallway"', re.IGNORECASE),
        ]
        for pattern in whitelist_patterns:
            assert not pattern.search(source), f"Found whitelist pattern: {pattern.pattern}"

    def test_compute_gathering_state_is_pure_function(self):
        inputs = dict(
            actor_locations={"veronique": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "alain"],
            current_step_scene_id="study",
            current_turn_number=5,
        )
        result1 = compute_gathering_state(**inputs)
        result2 = compute_gathering_state(**inputs)
        assert result1 == result2

    def test_no_player_blocking(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=12,
        )
        assert "player_blocked" not in result
        assert "block_player" not in result
        assert "coerce_return" not in result


class TestSourceField:
    """Tests that the source field correctly identifies evidence provenance."""

    def test_source_is_resolver_when_participation_evidence_present(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "study"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            participation_relevance="broken",
            current_turn_number=7,
        )
        assert result["source"] == PAUSE_SOURCE_RESOLVER_EVIDENCE

    def test_source_is_topology_when_only_location_mismatch(self):
        result = compute_gathering_state(
            actor_locations={"veronique": "study", "michel": "study", "annette": "study", "alain": "hallway"},
            current_step_named_characters=["veronique", "michel", "annette", "alain"],
            current_step_scene_id="study",
            current_turn_number=7,
        )
        assert result["source"] == PAUSE_SOURCE_TOPOLOGY
