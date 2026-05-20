"""Phase-2 Director Pulse tests.

Tests for the four Pulse-MVP contracts, motivation score engine, shadow path,
cut-in semantics, and ADR-0039 vocabulary guardrails.

Contracts under test:
  director_tick_decision.v1
  block_stream_event.v1
  npc_motivation_score.v1
  player_cut_in_event.v1

Governance: ADR-0058, ADR-0059, ADR-0060, ADR-0039.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

import pytest

from ai_stack.director.director_pulse_contracts import (
    ACTION_KINDS,
    ACTION_SILENCE,
    ACTION_SPEAK,
    BLOCK_STREAM_TYPES,
    BLOCK_TYPE_ACTOR_ACTION,
    BLOCK_TYPE_ACTOR_LINE,
    BLOCK_TYPE_ENVIRONMENT_INTERACTION,
    BLOCK_TYPE_NARRATOR,
    BLOCK_TYPE_SOUFFLEUSE,
    CUT_IN_STATES,
    CUT_KIND_EM_DASH,
    CUT_KIND_NO_ACTIVE_BLOCK,
    CUT_KIND_SKIP_TO_END,
    CUT_KINDS,
    LANES,
    SCHEMA_BLOCK_STREAM_EVENT,
    SCHEMA_DIRECTOR_TICK_DECISION,
    SCHEMA_NPC_MOTIVATION_SCORE,
    SCHEMA_PLAYER_CUT_IN_EVENT,
    TRIGGER_KINDS,
    TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
    TRIGGER_PLAYER_INPUT,
    TRIGGER_STATE_CHANGE,
    build_block_stream_event,
    build_director_tick_decision,
    build_npc_motivation_score,
    build_player_cut_in_event,
    resolve_cut_kind_for_block_type,
)
from ai_stack.director.director_pulse_shadow import evaluate_director_tick
from ai_stack.npc_agency.npc_motivation_score_engine import (
    compute_npc_motivation_scores,
    select_initiative_actor,
)


# ── Test fixtures ─────────────────────────────────────────────────────────────


def _tid() -> str:
    return str(uuid.uuid4())


def _scene_energy_high() -> dict[str, Any]:
    return {"energy_level": "volatile", "score": 0.85}


def _scene_energy_low() -> dict[str, Any]:
    return {"energy_level": "collapsed", "score": 0.10}


def _social_pressure_high() -> dict[str, Any]:
    return {"score": 0.80, "band": "high"}


def _social_pressure_low() -> dict[str, Any]:
    return {"score": 0.20, "band": "low"}


def _narrative_momentum_high() -> dict[str, Any]:
    return {"score": 0.75, "state": "driving"}


def _narrative_momentum_low() -> dict[str, Any]:
    return {"score": 0.20, "state": "resting"}


def _relationship_state_with_tension(npc_id: str, tension: float = 0.70) -> dict[str, Any]:
    return {
        "pair_states": {
            f"{npc_id}|player": {
                "actor_a": npc_id,
                "actor_b": "player",
                "tension_score": tension,
            }
        }
    }


def _actor_profiles() -> dict[str, Any]:
    return {
        "profiles": {
            "character_a": {"pressure_markers": ["m1", "m2", "m3", "m4"]},
            "character_b": {"pressure_markers": ["m1", "m2", "m3"]},
            "character_c": {"pressure_markers": ["m1", "m2", "m3", "m4", "m5"]},
        }
    }


def _policy_low_threshold() -> dict[str, Any]:
    return {
        "score_weights": {
            "scene_energy": 0.25,
            "social_pressure": 0.30,
            "relationship_axis_pressure": 0.25,
            "narrative_momentum": 0.20,
        },
        "base_threshold": 0.10,
        "actor_pressure_modifiers": {"character_a": 0.90, "character_b": 1.10},
        "silence_when_no_threshold_crossed": True,
    }


def _policy_high_threshold() -> dict[str, Any]:
    return {"base_threshold": 0.99}


# ── director_tick_decision.v1 shape ───────────────────────────────────────────


class TestDirectorTickDecisionShape:

    def test_schema_version(self):
        record = build_director_tick_decision(
            trigger_kind=TRIGGER_PLAYER_INPUT,
            triggering_actor_id="player",
            chosen_action_kind=ACTION_SPEAK,
            chosen_actor_id="npc_a",
            composition_inputs=["scene_energy", "social_pressure"],
            since_last_tick_ms=1200.0,
        )
        assert record["schema_version"] == SCHEMA_DIRECTOR_TICK_DECISION

    def test_required_fields_all_present(self):
        record = build_director_tick_decision(
            trigger_kind=TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
            triggering_actor_id=None,
            chosen_action_kind=ACTION_SILENCE,
            chosen_actor_id=None,
            composition_inputs=["scene_energy"],
            since_last_tick_ms=None,
        )
        required = {
            "schema_version", "tick_id", "trigger_kind", "triggering_actor_id",
            "chosen_action_kind", "chosen_actor_id", "composition_inputs",
            "since_last_tick_ms", "silence_reason",
        }
        assert required.issubset(record.keys())

    def test_all_trigger_kinds_accepted(self):
        for kind in TRIGGER_KINDS:
            record = build_director_tick_decision(
                trigger_kind=kind,
                triggering_actor_id=None,
                chosen_action_kind=ACTION_SILENCE,
                chosen_actor_id=None,
                composition_inputs=[],
                since_last_tick_ms=None,
            )
            assert record["trigger_kind"] == kind

    def test_invalid_trigger_kind_raises(self):
        with pytest.raises(ValueError, match="trigger_kind"):
            build_director_tick_decision(
                trigger_kind="BOGUS_TRIGGER",
                triggering_actor_id=None,
                chosen_action_kind=ACTION_SILENCE,
                chosen_actor_id=None,
                composition_inputs=[],
                since_last_tick_ms=None,
            )

    def test_all_action_kinds_accepted(self):
        for kind in ACTION_KINDS:
            record = build_director_tick_decision(
                trigger_kind=TRIGGER_PLAYER_INPUT,
                triggering_actor_id=None,
                chosen_action_kind=kind,
                chosen_actor_id=None,
                composition_inputs=[],
                since_last_tick_ms=0.0,
            )
            assert record["chosen_action_kind"] == kind

    def test_invalid_action_kind_raises(self):
        with pytest.raises(ValueError, match="chosen_action_kind"):
            build_director_tick_decision(
                trigger_kind=TRIGGER_PLAYER_INPUT,
                triggering_actor_id=None,
                chosen_action_kind="BOGUS_ACTION",
                chosen_actor_id=None,
                composition_inputs=[],
                since_last_tick_ms=None,
            )

    def test_silence_tick_has_null_actor_and_silence_reason(self):
        record = build_director_tick_decision(
            trigger_kind=TRIGGER_STATE_CHANGE,
            triggering_actor_id=None,
            chosen_action_kind=ACTION_SILENCE,
            chosen_actor_id=None,
            composition_inputs=["pacing_rhythm"],
            since_last_tick_ms=800.0,
            silence_reason="no_npc_above_motivation_threshold",
        )
        assert record["chosen_actor_id"] is None
        assert record["silence_reason"] == "no_npc_above_motivation_threshold"

    def test_autogenerated_tick_ids_are_unique(self):
        r1 = build_director_tick_decision(
            trigger_kind=TRIGGER_PLAYER_INPUT, triggering_actor_id=None,
            chosen_action_kind=ACTION_SILENCE, chosen_actor_id=None,
            composition_inputs=[], since_last_tick_ms=None,
        )
        r2 = build_director_tick_decision(
            trigger_kind=TRIGGER_PLAYER_INPUT, triggering_actor_id=None,
            chosen_action_kind=ACTION_SILENCE, chosen_actor_id=None,
            composition_inputs=[], since_last_tick_ms=None,
        )
        assert r1["tick_id"] != r2["tick_id"]

    def test_explicit_tick_id_preserved(self):
        tid = _tid()
        record = build_director_tick_decision(
            trigger_kind=TRIGGER_PLAYER_INPUT, triggering_actor_id=None,
            chosen_action_kind=ACTION_SILENCE, chosen_actor_id=None,
            composition_inputs=[], since_last_tick_ms=None,
            tick_id=tid,
        )
        assert record["tick_id"] == tid


# ── block_stream_event.v1 shape ───────────────────────────────────────────────


class TestBlockStreamEventShape:

    def test_schema_version(self):
        ev = build_block_stream_event(
            tick_id=_tid(),
            block_type=BLOCK_TYPE_NARRATOR,
            block_payload={"id": "b1", "text": "The room shifts."},
            cut_in_state="uninterrupted",
            lane="visible_scene_output",
            source="director",
        )
        assert ev["schema_version"] == SCHEMA_BLOCK_STREAM_EVENT

    def test_required_fields_all_present(self):
        ev = build_block_stream_event(
            tick_id=_tid(),
            block_type=BLOCK_TYPE_ACTOR_LINE,
            block_payload={"id": "b2", "text": "hello"},
            cut_in_state="uninterrupted",
            lane="visible_scene_output",
            source="npc_a",
        )
        required = {
            "schema_version", "event_id", "tick_id", "block_type",
            "block_payload", "cut_in_state", "lane", "source",
        }
        assert required.issubset(ev.keys())

    def test_one_block_per_event_payload_is_dict_not_list(self):
        ev = build_block_stream_event(
            tick_id=_tid(),
            block_type=BLOCK_TYPE_NARRATOR,
            block_payload={"id": "single"},
            cut_in_state="uninterrupted",
            lane="visible_scene_output",
            source="director",
        )
        assert isinstance(ev["block_payload"], dict)
        assert not isinstance(ev["block_payload"], list)

    def test_all_block_types_accepted(self):
        for bt in BLOCK_STREAM_TYPES:
            lane = "player_hint" if bt == BLOCK_TYPE_SOUFFLEUSE else "visible_scene_output"
            ev = build_block_stream_event(
                tick_id=_tid(),
                block_type=bt,
                block_payload={"id": bt},
                cut_in_state="uninterrupted",
                lane=lane,
                source="director",
            )
            assert ev["block_type"] == bt

    def test_invalid_block_type_raises(self):
        with pytest.raises(ValueError):
            build_block_stream_event(
                tick_id=_tid(),
                block_type="INVALID",
                block_payload={},
                cut_in_state="uninterrupted",
                lane="visible_scene_output",
                source="director",
            )

    def test_invalid_cut_in_state_raises(self):
        with pytest.raises(ValueError):
            build_block_stream_event(
                tick_id=_tid(),
                block_type=BLOCK_TYPE_NARRATOR,
                block_payload={},
                cut_in_state="INVALID",
                lane="visible_scene_output",
                source="director",
            )

    def test_invalid_lane_raises(self):
        with pytest.raises(ValueError):
            build_block_stream_event(
                tick_id=_tid(),
                block_type=BLOCK_TYPE_NARRATOR,
                block_payload={},
                cut_in_state="uninterrupted",
                lane="INVALID_LANE",
                source="director",
            )

    def test_all_cut_in_states_accepted(self):
        for state in CUT_IN_STATES:
            ev = build_block_stream_event(
                tick_id=_tid(),
                block_type=BLOCK_TYPE_NARRATOR,
                block_payload={"id": "x"},
                cut_in_state=state,
                lane="visible_scene_output",
                source="director",
            )
            assert ev["cut_in_state"] == state

    def test_all_lanes_accepted(self):
        for lane in LANES:
            bt = BLOCK_TYPE_SOUFFLEUSE if lane == "player_hint" else BLOCK_TYPE_NARRATOR
            ev = build_block_stream_event(
                tick_id=_tid(),
                block_type=bt,
                block_payload={},
                cut_in_state="uninterrupted",
                lane=lane,
                source="director",
            )
            assert ev["lane"] == lane


# ── npc_motivation_score.v1 shape ────────────────────────────────────────────


class TestNpcMotivationScoreShape:

    def test_schema_version(self):
        record = build_npc_motivation_score(
            npc_id="npc_a",
            tick_id=_tid(),
            score=0.65,
            score_components={"scene_energy": 0.8},
            threshold=0.55,
            crossed_threshold=True,
            source_capabilities=["scene_energy"],
        )
        assert record["schema_version"] == SCHEMA_NPC_MOTIVATION_SCORE

    def test_required_fields_all_present(self):
        record = build_npc_motivation_score(
            npc_id="npc_b",
            tick_id=_tid(),
            score=0.30,
            score_components={"scene_energy": 0.3},
            threshold=0.55,
            crossed_threshold=False,
            source_capabilities=["scene_energy"],
        )
        required = {
            "schema_version", "npc_id", "tick_id", "score",
            "score_components", "threshold", "crossed_threshold", "source_capabilities",
        }
        assert required.issubset(record.keys())

    def test_score_components_use_semantic_names_only(self):
        record = build_npc_motivation_score(
            npc_id="npc_c",
            tick_id=_tid(),
            score=0.50,
            score_components={
                "scene_energy": 0.5,
                "social_pressure": 0.6,
                "relationship_axis_pressure": 0.4,
                "narrative_momentum": 0.45,
                "pressure_baseline": 0.55,
            },
            threshold=0.55,
            crossed_threshold=False,
            source_capabilities=[
                "scene_energy", "social_pressure", "relationship_dynamics",
                "narrative_momentum", "actor_pressure_profiles",
            ],
        )
        pi_pattern = re.compile(r"\b(Pi|Π|pi_)\d+\b")
        for key in record["score_components"]:
            assert not pi_pattern.search(key), f"Pi/Π key in score_components: {key}"
        for cap in record["source_capabilities"]:
            assert not pi_pattern.search(cap), f"Pi/Π key in source_capabilities: {cap}"


# ── player_cut_in_event.v1 shape ──────────────────────────────────────────────


class TestPlayerCutInEventShape:

    def test_schema_version(self):
        ev = build_player_cut_in_event(
            tick_id=_tid(),
            interrupted_block_id="block-123",
            interrupted_block_type=BLOCK_TYPE_ACTOR_LINE,
            cut_kind=CUT_KIND_EM_DASH,
            player_input_payload={"text": "Stop!"},
        )
        assert ev["schema_version"] == SCHEMA_PLAYER_CUT_IN_EVENT

    def test_required_fields_all_present(self):
        ev = build_player_cut_in_event(
            tick_id=_tid(),
            interrupted_block_id=None,
            interrupted_block_type=None,
            cut_kind=CUT_KIND_NO_ACTIVE_BLOCK,
            player_input_payload={"text": "Hello"},
        )
        required = {
            "schema_version", "cut_in_id", "tick_id",
            "interrupted_block_id", "interrupted_block_type",
            "cut_kind", "player_input_payload",
        }
        assert required.issubset(ev.keys())

    def test_all_cut_kinds_accepted(self):
        for kind in CUT_KINDS:
            ev = build_player_cut_in_event(
                tick_id=_tid(),
                interrupted_block_id=None,
                interrupted_block_type=None,
                cut_kind=kind,
                player_input_payload={},
            )
            assert ev["cut_kind"] == kind

    def test_invalid_cut_kind_raises(self):
        with pytest.raises(ValueError):
            build_player_cut_in_event(
                tick_id=_tid(),
                interrupted_block_id=None,
                interrupted_block_type=None,
                cut_kind="INVALID",
                player_input_payload={},
            )


# ── Cut-in semantics by block type ────────────────────────────────────────────


class TestCutInSemantics:
    """Cut-in kind is block-type-dependent. No actor, room, or verb influences it."""

    def test_actor_line_gives_em_dash(self):
        assert resolve_cut_kind_for_block_type(BLOCK_TYPE_ACTOR_LINE) == CUT_KIND_EM_DASH

    def test_narrator_gives_skip_to_end(self):
        assert resolve_cut_kind_for_block_type(BLOCK_TYPE_NARRATOR) == CUT_KIND_SKIP_TO_END

    def test_actor_action_gives_skip_to_end(self):
        assert resolve_cut_kind_for_block_type(BLOCK_TYPE_ACTOR_ACTION) == CUT_KIND_SKIP_TO_END

    def test_souffleuse_gives_skip_to_end(self):
        assert resolve_cut_kind_for_block_type(BLOCK_TYPE_SOUFFLEUSE) == CUT_KIND_SKIP_TO_END

    def test_environment_interaction_gives_skip_to_end(self):
        assert resolve_cut_kind_for_block_type(BLOCK_TYPE_ENVIRONMENT_INTERACTION) == CUT_KIND_SKIP_TO_END

    def test_no_active_block_gives_no_active_block(self):
        assert resolve_cut_kind_for_block_type(None) == CUT_KIND_NO_ACTIVE_BLOCK

    def test_unknown_block_type_gives_skip_to_end(self):
        assert resolve_cut_kind_for_block_type("some_future_type") == CUT_KIND_SKIP_TO_END


# ── NPC Motivation Score engine ───────────────────────────────────────────────


class TestNpcMotivationScoreEngine:

    def test_returns_one_record_per_npc(self):
        npc_ids = ["npc_a", "npc_b", "npc_c"]
        scores = compute_npc_motivation_scores(
            npc_ids=npc_ids,
            tick_id=_tid(),
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_pressure_high(),
        )
        assert len(scores) == 3
        assert {s["npc_id"] for s in scores} == set(npc_ids)

    def test_scores_are_normalized_0_to_1(self):
        scores = compute_npc_motivation_scores(
            npc_ids=["npc_a", "npc_b"],
            tick_id=_tid(),
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_pressure_high(),
        )
        for s in scores:
            assert 0.0 <= s["score"] <= 1.0, f"Score out of range for {s['npc_id']}: {s['score']}"

    def test_score_components_include_required_semantic_keys(self):
        required = {
            "scene_energy", "social_pressure", "relationship_axis_pressure",
            "narrative_momentum", "pressure_baseline",
        }
        scores = compute_npc_motivation_scores(
            npc_ids=["npc_a"],
            tick_id=_tid(),
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_pressure_high(),
        )
        assert required.issubset(scores[0]["score_components"].keys())

    def test_no_pi_keys_in_score_components_or_source_capabilities(self):
        scores = compute_npc_motivation_scores(npc_ids=["npc_a"], tick_id=_tid())
        pi_pattern = re.compile(r"\b(Pi|Π|pi_)\d+\b")
        for s in scores:
            for key in s["score_components"]:
                assert not pi_pattern.search(key)
            for cap in s["source_capabilities"]:
                assert not pi_pattern.search(cap)

    def test_threshold_and_crossed_threshold_present(self):
        scores = compute_npc_motivation_scores(npc_ids=["npc_a"], tick_id=_tid())
        assert "threshold" in scores[0]
        assert isinstance(scores[0]["threshold"], float)
        assert isinstance(scores[0]["crossed_threshold"], bool)

    def test_high_pressure_raises_score_vs_low_pressure(self):
        high = compute_npc_motivation_scores(
            npc_ids=["npc_a"],
            tick_id=_tid(),
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_pressure_high(),
            narrative_momentum_output=_narrative_momentum_high(),
        )
        low = compute_npc_motivation_scores(
            npc_ids=["npc_a"],
            tick_id=_tid(),
            scene_energy_output=_scene_energy_low(),
            social_pressure_output=_social_pressure_low(),
            narrative_momentum_output=_narrative_momentum_low(),
        )
        assert high[0]["score"] > low[0]["score"]

    def test_below_threshold_npcs_still_recorded(self):
        """All NPCs recorded even when nobody crosses threshold (diagnostic completeness)."""
        scores = compute_npc_motivation_scores(
            npc_ids=["npc_a", "npc_b"],
            tick_id=_tid(),
            scene_energy_output=_scene_energy_low(),
            social_pressure_output=_social_pressure_low(),
            npc_motivation_score_policy=_policy_high_threshold(),
        )
        assert len(scores) == 2
        for s in scores:
            assert s["crossed_threshold"] is False

    def test_per_npc_relationship_pressure_gives_different_scores(self):
        """NPCs present in relationship tension pairs get different scores."""
        npc_a = "npc_a"
        npc_b = "npc_b"
        scores = compute_npc_motivation_scores(
            npc_ids=[npc_a, npc_b],
            tick_id=_tid(),
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_pressure_high(),
            relationship_state_output=_relationship_state_with_tension(npc_a, 0.95),
        )
        score_a = next(s["score"] for s in scores if s["npc_id"] == npc_a)
        score_b = next(s["score"] for s in scores if s["npc_id"] == npc_b)
        # npc_a has high relationship tension; npc_b has only the fallback
        assert score_a != score_b

    def test_score_is_pure_function_same_inputs_same_output(self):
        kwargs: dict[str, Any] = dict(
            npc_ids=["npc_a"],
            tick_id="fixed-tick-id",
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_pressure_high(),
        )
        s1 = compute_npc_motivation_scores(**kwargs)
        s2 = compute_npc_motivation_scores(**kwargs)
        assert s1[0]["score"] == s2[0]["score"]

    def test_actor_pressure_profiles_content_influences_baseline(self):
        """More pressure_markers → higher pressure_baseline → higher score."""
        rich_profile = {
            "profiles": {"npc_x": {"pressure_markers": ["a", "b", "c", "d", "e", "f"]}}
        }
        lean_profile = {
            "profiles": {"npc_x": {"pressure_markers": ["a"]}}
        }
        rich = compute_npc_motivation_scores(
            npc_ids=["npc_x"], tick_id=_tid(),
            scene_energy_output=_scene_energy_high(),
            actor_pressure_profiles=rich_profile,
        )
        lean = compute_npc_motivation_scores(
            npc_ids=["npc_x"], tick_id=_tid(),
            scene_energy_output=_scene_energy_high(),
            actor_pressure_profiles=lean_profile,
        )
        assert rich[0]["score"] >= lean[0]["score"]

    def test_empty_npc_list_returns_empty(self):
        scores = compute_npc_motivation_scores(npc_ids=[], tick_id=_tid())
        assert scores == []


# ── Initiative selection ──────────────────────────────────────────────────────


class TestInitiativeSelection:

    def test_highest_score_above_threshold_wins(self):
        tid = _tid()
        scores = [
            build_npc_motivation_score(
                npc_id="npc_b", tick_id=tid, score=0.60,
                score_components={}, threshold=0.55, crossed_threshold=True,
                source_capabilities=[],
            ),
            build_npc_motivation_score(
                npc_id="npc_a", tick_id=tid, score=0.80,
                score_components={}, threshold=0.55, crossed_threshold=True,
                source_capabilities=[],
            ),
        ]
        assert select_initiative_actor(scores) == "npc_a"

    def test_nobody_above_threshold_returns_none(self):
        tid = _tid()
        scores = [
            build_npc_motivation_score(
                npc_id="npc_a", tick_id=tid, score=0.30,
                score_components={}, threshold=0.55, crossed_threshold=False,
                source_capabilities=[],
            ),
        ]
        assert select_initiative_actor(scores) is None

    def test_empty_scores_returns_none(self):
        assert select_initiative_actor([]) is None

    def test_winner_changes_when_scores_change(self):
        """No fixed speaker queue: different scores → different winner."""
        tid = _tid()
        scores_a = [
            build_npc_motivation_score(
                npc_id="npc_x", tick_id=tid, score=0.90,
                score_components={}, threshold=0.55, crossed_threshold=True,
                source_capabilities=[],
            ),
            build_npc_motivation_score(
                npc_id="npc_y", tick_id=tid, score=0.60,
                score_components={}, threshold=0.55, crossed_threshold=True,
                source_capabilities=[],
            ),
        ]
        scores_b = [
            build_npc_motivation_score(
                npc_id="npc_x", tick_id=tid, score=0.60,
                score_components={}, threshold=0.55, crossed_threshold=True,
                source_capabilities=[],
            ),
            build_npc_motivation_score(
                npc_id="npc_y", tick_id=tid, score=0.90,
                score_components={}, threshold=0.55, crossed_threshold=True,
                source_capabilities=[],
            ),
        ]
        assert select_initiative_actor(scores_a) == "npc_x"
        assert select_initiative_actor(scores_b) == "npc_y"

    def test_single_npc_above_threshold_wins(self):
        tid = _tid()
        scores = [
            build_npc_motivation_score(
                npc_id="winner", tick_id=tid, score=0.75,
                score_components={}, threshold=0.55, crossed_threshold=True,
                source_capabilities=[],
            ),
        ]
        assert select_initiative_actor(scores) == "winner"


# ── Director Pulse shadow path ────────────────────────────────────────────────


class TestDirectorPulseShadow:

    def test_returns_all_four_keys_in_result(self):
        result = evaluate_director_tick(npc_ids=[], tick_id=_tid())
        assert "director_tick_decision" in result
        assert "npc_motivation_scores" in result
        assert "block_stream_event" in result
        assert "player_cut_in_event" in result

    def test_shadow_only_is_always_true(self):
        result = evaluate_director_tick(npc_ids=[], tick_id=_tid())
        assert result["shadow_only"] is True

    def test_silence_when_no_npc_above_threshold(self):
        result = evaluate_director_tick(
            npc_ids=["npc_a", "npc_b"],
            tick_id=_tid(),
            scene_energy_output=_scene_energy_low(),
            social_pressure_output=_social_pressure_low(),
            npc_motivation_score_policy=_policy_high_threshold(),
        )
        tick = result["director_tick_decision"]
        assert tick["chosen_action_kind"] == ACTION_SILENCE
        assert tick["chosen_actor_id"] is None

    def test_speak_when_npc_crosses_threshold(self):
        result = evaluate_director_tick(
            npc_ids=["npc_a"],
            tick_id=_tid(),
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_pressure_high(),
            narrative_momentum_output=_narrative_momentum_high(),
            actor_pressure_profiles=_actor_profiles(),
            npc_motivation_score_policy=_policy_low_threshold(),
        )
        tick = result["director_tick_decision"]
        assert tick["chosen_action_kind"] == ACTION_SPEAK
        assert tick["chosen_actor_id"] == "npc_a"

    def test_no_motivation_scores_for_empty_npc_list(self):
        result = evaluate_director_tick(npc_ids=[], tick_id=_tid())
        assert result["npc_motivation_scores"] == []

    def test_motivation_scores_count_matches_npc_ids(self):
        npc_ids = ["npc_a", "npc_b", "npc_c"]
        result = evaluate_director_tick(npc_ids=npc_ids, tick_id=_tid())
        assert len(result["npc_motivation_scores"]) == 3

    def test_block_stream_event_emitted_when_block_payload_provided(self):
        result = evaluate_director_tick(
            npc_ids=[],
            tick_id=_tid(),
            current_block_type=BLOCK_TYPE_ACTOR_LINE,
            block_payload={"id": "b-1", "text": "Hello."},
        )
        assert result["block_stream_event"] is not None
        assert result["block_stream_event"]["schema_version"] == SCHEMA_BLOCK_STREAM_EVENT

    def test_no_block_stream_event_without_block_payload(self):
        result = evaluate_director_tick(npc_ids=[], tick_id=_tid())
        assert result["block_stream_event"] is None

    def test_player_cut_in_event_emitted_with_player_input(self):
        result = evaluate_director_tick(
            npc_ids=[],
            tick_id=_tid(),
            current_block_type=BLOCK_TYPE_ACTOR_LINE,
            current_block_id="block-xyz",
            block_payload={"id": "block-xyz", "text": "..."},
            player_input_payload={"text": "Excuse me!"},
        )
        assert result["player_cut_in_event"] is not None
        ev = result["player_cut_in_event"]
        assert ev["schema_version"] == SCHEMA_PLAYER_CUT_IN_EVENT
        assert ev["cut_kind"] == CUT_KIND_EM_DASH

    def test_player_cut_in_on_narrator_gives_skip_to_end(self):
        result = evaluate_director_tick(
            npc_ids=[],
            tick_id=_tid(),
            current_block_type=BLOCK_TYPE_NARRATOR,
            current_block_id="narr-1",
            block_payload={"id": "narr-1", "text": "The silence grows."},
            player_input_payload={"text": "I speak now."},
        )
        assert result["player_cut_in_event"]["cut_kind"] == CUT_KIND_SKIP_TO_END

    def test_no_player_cut_in_event_without_player_input(self):
        result = evaluate_director_tick(npc_ids=[], tick_id=_tid())
        assert result["player_cut_in_event"] is None

    def test_gathering_paused_passes_through_and_shadow_still_evaluates(self):
        result = evaluate_director_tick(
            npc_ids=["npc_a"],
            tick_id=_tid(),
            gathering_paused=True,
            npc_motivation_score_policy=_policy_low_threshold(),
            scene_energy_output=_scene_energy_high(),
        )
        assert result["gathering_paused"] is True
        # Shadow diagnostics still computed even during pause
        assert len(result["npc_motivation_scores"]) == 1

    def test_canonical_path_not_touched(self):
        """Shadow path result must not contain canonical-path mutation keys."""
        result = evaluate_director_tick(npc_ids=["npc_a"], tick_id=_tid())
        mutation_keys = {
            "step_pointer", "canonical_step_advance", "mandatory_beat_consumed",
            "state_changes_committed", "_mutate", "_set_state", "_control",
        }
        assert not mutation_keys.intersection(result.keys())

    def test_all_events_share_same_tick_id(self):
        tid = _tid()
        result = evaluate_director_tick(
            npc_ids=["npc_a"],
            tick_id=tid,
            current_block_type=BLOCK_TYPE_NARRATOR,
            block_payload={"id": "n-1", "text": "The air is still."},
        )
        assert result["director_tick_decision"]["tick_id"] == tid
        for score in result["npc_motivation_scores"]:
            assert score["tick_id"] == tid
        if result["block_stream_event"]:
            assert result["block_stream_event"]["tick_id"] == tid

    def test_composition_inputs_use_semantic_names_only(self):
        result = evaluate_director_tick(npc_ids=[], tick_id=_tid())
        pi_pattern = re.compile(r"\b(Pi|Π|pi_)\d+\b")
        for cap in result["director_tick_decision"]["composition_inputs"]:
            assert not pi_pattern.search(cap), f"Pi/Π key in composition_inputs: {cap}"


# ── ADR-0039 Vocabulary Guardrails ────────────────────────────────────────────


class TestADR0039Guardrails:
    """No Pi/Π runtime keys; no hardcoded NPC IDs; no whitelists; no speaker queue."""

    _PI = [
        re.compile(r"\bPi\d+\b"),
        re.compile(r"\bΠ\d+\b"),
        re.compile(r"\bpi_\d+\b"),
    ]

    def _source(self, module_name: str) -> str:
        import importlib
        mod = importlib.import_module(module_name)
        return open(mod.__file__, "r", encoding="utf-8").read()

    def _assert_no_pi(self, module_name: str) -> None:
        source = self._source(module_name)
        for pattern in self._PI:
            assert not pattern.search(source), (
                f"Pi/Π runtime key found in {module_name}: pattern {pattern.pattern!r}"
            )

    def test_no_pi_keys_in_director_pulse_contracts(self):
        self._assert_no_pi("ai_stack.director.director_pulse_contracts")

    def test_no_pi_keys_in_npc_motivation_score_engine(self):
        self._assert_no_pi("ai_stack.npc_agency.npc_motivation_score_engine")

    def test_no_pi_keys_in_director_pulse_shadow(self):
        self._assert_no_pi("ai_stack.director.director_pulse_shadow")

    def test_no_hardcoded_npc_ids_in_contracts_module(self):
        source = self._source("ai_stack.director.director_pulse_contracts")
        for literal in ("veronique", "michel", "annette", "alain"):
            assert literal not in source, f"Hardcoded NPC ID '{literal}' in contracts module"

    def test_no_hardcoded_npc_ids_in_engine_module(self):
        source = self._source("ai_stack.npc_agency.npc_motivation_score_engine")
        for literal in ("veronique", "michel", "annette", "alain"):
            assert literal not in source, f"Hardcoded NPC ID '{literal}' in engine module"

    def test_no_hardcoded_npc_ids_in_shadow_module(self):
        source = self._source("ai_stack.director.director_pulse_shadow")
        for literal in ("veronique", "michel", "annette", "alain"):
            assert literal not in source, f"Hardcoded NPC ID '{literal}' in shadow module"

    def test_no_verb_or_room_whitelist_in_contracts(self):
        source = self._source("ai_stack.director.director_pulse_contracts")
        for term in ("verb_whitelist", "action_whitelist", "room_whitelist"):
            assert term not in source.lower()

    def test_no_fixed_speaker_queue_in_contracts(self):
        source = self._source("ai_stack.director.director_pulse_contracts")
        for term in ("speaker_queue", "roundtable", "turn_order", "fixed_roster"):
            assert term not in source.lower()

    def test_no_speaker_queue_in_engine(self):
        source = self._source("ai_stack.npc_agency.npc_motivation_score_engine")
        for term in ("speaker_queue", "roundtable", "turn_order", "fixed_roster"):
            assert term not in source.lower()

    def test_block_payload_is_dict_not_list_by_design(self):
        """Block-stream-event: block_payload is always a single dict (no bundle)."""
        ev = build_block_stream_event(
            tick_id=_tid(),
            block_type=BLOCK_TYPE_NARRATOR,
            block_payload={"id": "only"},
            cut_in_state="uninterrupted",
            lane="visible_scene_output",
            source="director",
        )
        assert isinstance(ev["block_payload"], dict)
        assert "blocks" not in ev, "No nested 'blocks' list — one block per event"

    def test_gathering_state_contracts_unchanged(self):
        """Phase-2 concepts must not appear in the PR-C director_gathering_state_contracts module."""
        import ai_stack.director.director_gathering_state_contracts as mod
        source = open(mod.__file__, "r", encoding="utf-8").read()
        for term in ("npc_pulse", "pulse_tick", "motivation_score",
                     "block_stream_bus", "event_stream"):
            assert term not in source.lower(), (
                f"Phase-2 concept '{term}' found in director_gathering_state_contracts"
            )
