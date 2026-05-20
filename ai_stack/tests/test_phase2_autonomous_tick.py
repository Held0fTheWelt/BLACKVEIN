"""Phase 2 Stage E — Autonomous Director Tick Coordinator tests.

Covers ``ai_stack/autonomous_tick.py``:

* Feature flag fail-closed semantics
* Pre-check (``should_emit_autonomous_tick``) enumerates each suppression
  reason with a deterministic trigger.
* Live evaluation (``evaluate_autonomous_tick``):
    - emits exactly one block_stream_event when an NPC crosses threshold
    - emits silence when no NPC crosses threshold
    - highest motivation score wins (no rotation, no fixed roster)
    - gathering_paused → off-stage-only silence reason
    - cooldown blocks emission but still records diagnostics
    - never advances canonical path
    - never consumes mandatory beats
    - shadow_only is False (live path)
    - all required diagnostic fields are present
    - no Pi/Π keys, no hardcoded actor IDs in module source

No mocks of contract builders — the test asserts real outputs.

Governance:
* ADR-0058 — Director-Driven Pulse and Block-Stream-Bus / Stage E
* ADR-0059 — Semantic NPC Motivation Score
* ADR-0061 — Director Gathering State (gathering_paused)
* ADR-0039 — No Pi/Π runtime keys; semantic names only
"""

from __future__ import annotations

import re
import uuid
from typing import Any

import pytest

from ai_stack.contracts.director_pulse_contracts import (
    ACTION_SILENCE,
    ACTION_SPEAK,
    BLOCK_TYPE_ACTOR_LINE,
    LANE_VISIBLE_SCENE_OUTPUT,
    SCHEMA_BLOCK_STREAM_EVENT,
    SCHEMA_DIRECTOR_TICK_DECISION,
    TRIGGER_COOLDOWN_CHECK,
    TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
    TRIGGER_PLAYER_INPUT,
    TRIGGER_STATE_CHANGE,
)
from ai_stack.autonomous_tick import (
    LOOP_STOP_COOLDOWN_ACTIVE,
    LOOP_STOP_DISABLED,
    LOOP_STOP_ELAPSED_INPUT_MISSING,
    LOOP_STOP_MAX_TICKS,
    LOOP_STOP_NO_MOTIVATION_THRESHOLD,
    LOOP_STOP_PLAYER_CUT_IN,
    LOOP_STOP_UNSAFE_CANDIDATE,
    LOOP_TRIGGER_USER_PAUSE,
    PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED,
    PHASE2_AUTONOMOUS_TICK_ENABLED,
    SILENCE_GATHERING_PAUSED_OFF_STAGE,
    SILENCE_NO_NPC_ABOVE_THRESHOLD,
    SUPPRESS_ALREADY_EMITTING,
    SUPPRESS_COOLDOWN_ACTIVE,
    SUPPRESS_FLAG_DISABLED,
    SUPPRESS_INVALID_TRIGGER,
    SUPPRESS_NO_NPCS_PRESENT,
    SUPPRESS_PENDING_PLAYER_INPUT,
    AutonomousPauseLoopInputs,
    AutonomousTickInputs,
    AutonomousTickOutcome,
    evaluate_autonomous_pause_loop,
    evaluate_autonomous_tick,
    is_autonomous_pause_loop_enabled,
    is_autonomous_tick_enabled,
    should_emit_autonomous_tick,
)


def _tid() -> str:
    return str(uuid.uuid4())


def _scene_energy_high() -> dict[str, Any]:
    return {"energy_level": "volatile"}


def _scene_energy_low() -> dict[str, Any]:
    return {"energy_level": "collapsed"}


def _social_pressure_high() -> dict[str, Any]:
    return {"band": "high"}


def _social_pressure_low() -> dict[str, Any]:
    return {"band": "low"}


def _narrative_momentum_high() -> dict[str, Any]:
    return {"state": "cresting"}


def _actor_profiles(npc_id: str = "npc_a", marker_count: int = 5) -> dict[str, Any]:
    return {
        "profiles": {
            npc_id: {
                "pressure_markers": [{"text": f"marker_{i}"} for i in range(marker_count)]
            }
        }
    }


def _policy_low_threshold() -> dict[str, Any]:
    return {
        "base_threshold": 0.10,
        "score_weights": {
            "scene_energy": 0.25,
            "social_pressure": 0.30,
            "relationship_axis_pressure": 0.25,
            "narrative_momentum": 0.20,
        },
    }


def _policy_high_threshold() -> dict[str, Any]:
    return {
        "base_threshold": 0.99,
        "score_weights": {
            "scene_energy": 0.25,
            "social_pressure": 0.30,
            "relationship_axis_pressure": 0.25,
            "narrative_momentum": 0.20,
        },
    }


def _ready_inputs(**overrides: Any) -> AutonomousTickInputs:
    defaults: dict[str, Any] = dict(
        trigger_kind=TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
        npc_ids=["npc_a"],
        scene_energy_output=_scene_energy_high(),
        social_pressure_output=_social_pressure_high(),
        narrative_momentum_output=_narrative_momentum_high(),
        actor_pressure_profiles=_actor_profiles("npc_a"),
        npc_motivation_score_policy=_policy_low_threshold(),
        since_last_tick_ms=None,
        visible_npc_ids=["npc_a"],
        known_actor_ids=["npc_a"],
    )
    defaults.update(overrides)
    return AutonomousTickInputs(**defaults)


# ── Feature flag ──────────────────────────────────────────────────────────────


class TestFeatureFlag:
    def test_default_off(self, monkeypatch):
        monkeypatch.delenv(PHASE2_AUTONOMOUS_TICK_ENABLED, raising=False)
        assert is_autonomous_tick_enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " 1 "])
    def test_true_values_enable(self, monkeypatch, value):
        monkeypatch.setenv(PHASE2_AUTONOMOUS_TICK_ENABLED, value)
        assert is_autonomous_tick_enabled() is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "garbage"])
    def test_false_values_disable(self, monkeypatch, value):
        monkeypatch.setenv(PHASE2_AUTONOMOUS_TICK_ENABLED, value)
        assert is_autonomous_tick_enabled() is False


# ── should_emit_autonomous_tick ───────────────────────────────────────────────


class TestShouldEmit:
    def test_flag_disabled_blocks(self):
        ok, reason = should_emit_autonomous_tick(inputs=_ready_inputs(), enabled=False)
        assert ok is False
        assert reason == SUPPRESS_FLAG_DISABLED

    def test_no_npcs_present_blocks(self):
        ok, reason = should_emit_autonomous_tick(inputs=_ready_inputs(npc_ids=[]), enabled=True)
        assert ok is False
        assert reason == SUPPRESS_NO_NPCS_PRESENT

    def test_cooldown_active_blocks(self):
        ok, reason = should_emit_autonomous_tick(
            inputs=_ready_inputs(
                since_last_tick_ms=100.0,
                min_tick_interval_ms_override=2000.0,
            ),
            enabled=True,
        )
        assert ok is False
        assert reason == SUPPRESS_COOLDOWN_ACTIVE

    def test_first_tick_is_free(self):
        ok, reason = should_emit_autonomous_tick(
            inputs=_ready_inputs(since_last_tick_ms=None, min_tick_interval_ms_override=2000.0),
            enabled=True,
        )
        assert ok is True
        assert reason is None

    def test_pending_player_input_blocks(self):
        ok, reason = should_emit_autonomous_tick(
            inputs=_ready_inputs(pending_player_input=True), enabled=True
        )
        assert ok is False
        assert reason == SUPPRESS_PENDING_PLAYER_INPUT

    def test_already_streaming_block_blocks(self):
        ok, reason = should_emit_autonomous_tick(
            inputs=_ready_inputs(already_streaming_block=True), enabled=True
        )
        assert ok is False
        assert reason == SUPPRESS_ALREADY_EMITTING

    def test_invalid_trigger_blocks(self):
        ok, reason = should_emit_autonomous_tick(
            inputs=_ready_inputs(trigger_kind="wall_clock_polling"),
            enabled=True,
        )
        assert ok is False
        assert reason == SUPPRESS_INVALID_TRIGGER

    def test_all_required_trigger_kinds_pass_validation(self):
        for trigger in (
            TRIGGER_PLAYER_INPUT,
            TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
            TRIGGER_STATE_CHANGE,
            TRIGGER_COOLDOWN_CHECK,
        ):
            ok, reason = should_emit_autonomous_tick(
                inputs=_ready_inputs(trigger_kind=trigger),
                enabled=True,
            )
            assert ok is True, f"trigger {trigger} should be valid; reason={reason}"


# ── evaluate_autonomous_tick: emission path ──────────────────────────────────


class TestEmissionPath:
    def test_emits_block_stream_event_when_npc_crosses_threshold(self):
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=True)
        assert outcome.block_stream_event is not None
        assert outcome.block_stream_event["schema_version"] == SCHEMA_BLOCK_STREAM_EVENT
        assert outcome.chosen_actor_id == "npc_a"
        assert outcome.chosen_action_kind == ACTION_SPEAK
        assert outcome.silence_reason is None

    def test_block_stream_event_carries_actor_id_in_payload(self):
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=True)
        payload = outcome.block_stream_event["block_payload"]
        assert payload["actor_id"] == "npc_a"
        assert payload["originator"] == "autonomous_tick"
        assert payload["block_type"] == BLOCK_TYPE_ACTOR_LINE

    def test_only_one_event_per_tick(self):
        outcome = evaluate_autonomous_tick(
            _ready_inputs(npc_ids=["npc_a", "npc_b"]), enabled=True
        )
        # At most one block event ever, regardless of how many NPCs were scored.
        assert outcome.block_stream_event is not None
        # And exactly one chosen actor.
        assert isinstance(outcome.chosen_actor_id, str)

    def test_lane_is_visible_scene_output(self):
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=True)
        assert outcome.block_stream_event["lane"] == LANE_VISIBLE_SCENE_OUTPUT

    def test_block_event_tick_id_matches_outcome_tick_id(self):
        tid = _tid()
        outcome = evaluate_autonomous_tick(_ready_inputs(tick_id=tid), enabled=True)
        assert outcome.tick_id == tid
        assert outcome.block_stream_event["tick_id"] == tid


# ── evaluate_autonomous_tick: silence path ───────────────────────────────────


class TestSilencePath:
    def test_silence_when_no_npc_above_threshold(self):
        outcome = evaluate_autonomous_tick(
            _ready_inputs(
                scene_energy_output=_scene_energy_low(),
                social_pressure_output=_social_pressure_low(),
                npc_motivation_score_policy=_policy_high_threshold(),
            ),
            enabled=True,
        )
        assert outcome.block_stream_event is None
        assert outcome.chosen_actor_id is None
        assert outcome.chosen_action_kind == ACTION_SILENCE
        assert outcome.silence_reason == SILENCE_NO_NPC_ABOVE_THRESHOLD

    def test_silence_records_director_tick_decision(self):
        outcome = evaluate_autonomous_tick(
            _ready_inputs(
                scene_energy_output=_scene_energy_low(),
                npc_motivation_score_policy=_policy_high_threshold(),
            ),
            enabled=True,
        )
        decision = outcome.director_tick_decision
        assert decision["schema_version"] == SCHEMA_DIRECTOR_TICK_DECISION
        assert decision["chosen_action_kind"] == ACTION_SILENCE
        assert decision["silence_reason"] == SILENCE_NO_NPC_ABOVE_THRESHOLD

    def test_silence_is_first_class_not_a_fallback(self):
        outcome = evaluate_autonomous_tick(
            _ready_inputs(
                scene_energy_output=_scene_energy_low(),
                npc_motivation_score_policy=_policy_high_threshold(),
            ),
            enabled=True,
        )
        # Even on silence the motivation scores are emitted for diagnostics.
        assert len(outcome.npc_motivation_scores) == 1
        assert outcome.motivation_scores  # non-empty mapping


# ── Initiative selection — highest score wins ────────────────────────────────


class TestInitiativeSelection:
    def test_highest_score_wins_no_rotation(self):
        # Two NPCs, both eligible to cross threshold via different profiles.
        # The one with the larger pressure baseline (more pressure_markers)
        # gets the bump in their score and wins initiative.
        profiles = {
            "profiles": {
                "npc_low": {"pressure_markers": [{"t": "x"}]},
                "npc_high": {"pressure_markers": [{"t": str(i)} for i in range(10)]},
            }
        }
        outcome = evaluate_autonomous_tick(
            _ready_inputs(
                npc_ids=["npc_low", "npc_high"],
                actor_pressure_profiles=profiles,
                npc_motivation_score_policy=_policy_low_threshold(),
            ),
            enabled=True,
        )
        assert outcome.chosen_actor_id == "npc_high"

    def test_initiative_does_not_depend_on_input_order(self):
        profiles = {
            "profiles": {
                "winner": {"pressure_markers": [{"t": str(i)} for i in range(10)]},
                "loser": {"pressure_markers": [{"t": "x"}]},
            }
        }
        for order in (["winner", "loser"], ["loser", "winner"]):
            outcome = evaluate_autonomous_tick(
                _ready_inputs(
                    npc_ids=order,
                    actor_pressure_profiles=profiles,
                    npc_motivation_score_policy=_policy_low_threshold(),
                ),
                enabled=True,
            )
            assert outcome.chosen_actor_id == "winner", (
                f"order-dependent selection detected for {order}; "
                "this would be a fixed-rotation regression"
            )


# ── gathering_paused ─────────────────────────────────────────────────────────


class TestGatheringPaused:
    def test_paused_does_not_consume_beats_or_advance_path(self):
        outcome = evaluate_autonomous_tick(
            _ready_inputs(gathering_paused=True), enabled=True
        )
        # Hard contract: the coordinator never touches the canonical path / beats.
        assert outcome.canonical_path_advanced is False
        assert outcome.mandatory_beat_consumed is False

    def test_paused_with_no_eligible_npc_uses_off_stage_silence_reason(self):
        outcome = evaluate_autonomous_tick(
            _ready_inputs(
                gathering_paused=True,
                scene_energy_output=_scene_energy_low(),
                npc_motivation_score_policy=_policy_high_threshold(),
            ),
            enabled=True,
        )
        assert outcome.silence_reason == SILENCE_GATHERING_PAUSED_OFF_STAGE

    def test_paused_diagnostics_still_emitted(self):
        outcome = evaluate_autonomous_tick(
            _ready_inputs(gathering_paused=True), enabled=True
        )
        assert outcome.npc_motivation_scores  # always computed for diagnostic record


# ── Cooldown ──────────────────────────────────────────────────────────────────


class TestCooldown:
    def test_cooldown_active_returns_silence_with_suppressed_reason(self):
        outcome = evaluate_autonomous_tick(
            _ready_inputs(
                since_last_tick_ms=200.0,
                min_tick_interval_ms_override=1500.0,
            ),
            enabled=True,
        )
        assert outcome.block_stream_event is None
        assert outcome.autonomous_tick_suppressed_reason == SUPPRESS_COOLDOWN_ACTIVE
        assert outcome.cooldown_state["cooldown_active"] is True
        assert outcome.cooldown_state["min_tick_interval_ms"] == 1500.0

    def test_cooldown_state_reported_even_on_emission(self):
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=True)
        assert "min_tick_interval_ms" in outcome.cooldown_state
        assert "since_last_tick_ms" in outcome.cooldown_state
        assert "cooldown_active" in outcome.cooldown_state

    def test_pacing_rhythm_policy_drives_cooldown(self):
        outcome = evaluate_autonomous_tick(
            _ready_inputs(
                pacing_rhythm_policy={"min_tick_interval_ms": 5000.0},
                since_last_tick_ms=1000.0,
            ),
            enabled=True,
        )
        assert outcome.cooldown_state["min_tick_interval_ms"] == 5000.0
        assert outcome.cooldown_state["cooldown_active"] is True
        assert outcome.autonomous_tick_suppressed_reason == SUPPRESS_COOLDOWN_ACTIVE


# ── Stage H — bounded autonomous pause loop ──────────────────────────────────


class TestAutonomousPauseLoop:
    def test_loop_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv(PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED, raising=False)
        assert is_autonomous_pause_loop_enabled() is False

        outcome = evaluate_autonomous_pause_loop(
            AutonomousPauseLoopInputs(tick_inputs=_ready_inputs()),
            tick_enabled=True,
        )
        assert outcome.loop_enabled is False
        assert outcome.stop_reason == LOOP_STOP_DISABLED
        assert outcome.tick_outcomes == []

    def test_loop_enabled_by_flag(self, monkeypatch):
        monkeypatch.setenv(PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED, "true")
        assert is_autonomous_pause_loop_enabled() is True

    def test_max_ticks_per_pause_enforced(self):
        outcome = evaluate_autonomous_pause_loop(
            AutonomousPauseLoopInputs(
                tick_inputs=_ready_inputs(
                    pacing_rhythm_policy={
                        "min_tick_interval_ms": 0,
                        "max_ticks_per_pause": 2,
                    },
                ),
                elapsed_ms_between_ticks=[0],
            ),
            enabled=True,
            tick_enabled=True,
        )
        assert outcome.loop_enabled is True
        assert outcome.stop_reason == LOOP_STOP_MAX_TICKS
        assert len(outcome.tick_outcomes) == 2
        assert all(t.block_stream_event is not None for t in outcome.tick_outcomes)

    def test_cooldown_enforced_between_ticks(self):
        outcome = evaluate_autonomous_pause_loop(
            AutonomousPauseLoopInputs(
                tick_inputs=_ready_inputs(
                    pacing_rhythm_policy={
                        "min_tick_interval_ms": 5000,
                        "max_ticks_per_pause": 2,
                    },
                ),
                elapsed_ms_between_ticks=[100],
            ),
            enabled=True,
            tick_enabled=True,
        )
        assert outcome.stop_reason == LOOP_STOP_COOLDOWN_ACTIVE
        assert len(outcome.tick_outcomes) == 2
        assert outcome.tick_outcomes[1].autonomous_tick_suppressed_reason == SUPPRESS_COOLDOWN_ACTIVE

    def test_additional_tick_requires_elapsed_evidence(self):
        outcome = evaluate_autonomous_pause_loop(
            AutonomousPauseLoopInputs(
                tick_inputs=_ready_inputs(
                    pacing_rhythm_policy={
                        "min_tick_interval_ms": 1000,
                        "max_ticks_per_pause": 2,
                    },
                ),
                elapsed_ms_between_ticks=[],
            ),
            enabled=True,
            tick_enabled=True,
        )
        assert outcome.stop_reason == LOOP_STOP_ELAPSED_INPUT_MISSING
        assert len(outcome.tick_outcomes) == 1

    def test_no_npc_above_threshold_yields_silence_then_stops(self):
        outcome = evaluate_autonomous_pause_loop(
            AutonomousPauseLoopInputs(
                tick_inputs=_ready_inputs(
                    scene_energy_output=_scene_energy_low(),
                    social_pressure_output=_social_pressure_low(),
                    npc_motivation_score_policy=_policy_high_threshold(),
                    pacing_rhythm_policy={
                        "min_tick_interval_ms": 0,
                        "max_ticks_per_pause": 3,
                    },
                ),
                elapsed_ms_between_ticks=[0, 0],
            ),
            enabled=True,
            tick_enabled=True,
        )
        assert outcome.stop_reason == LOOP_STOP_NO_MOTIVATION_THRESHOLD
        assert len(outcome.tick_outcomes) == 1
        assert outcome.tick_outcomes[0].silence_reason == SILENCE_NO_NPC_ABOVE_THRESHOLD

    def test_highest_motivated_npc_wins_each_tick(self):
        profiles = {
            "profiles": {
                "npc_low": {"pressure_markers": [{"t": "x"}]},
                "npc_high": {"pressure_markers": [{"t": str(i)} for i in range(10)]},
            }
        }
        outcome = evaluate_autonomous_pause_loop(
            AutonomousPauseLoopInputs(
                tick_inputs=_ready_inputs(
                    npc_ids=["npc_low", "npc_high"],
                    actor_pressure_profiles=profiles,
                    visible_npc_ids=["npc_low", "npc_high"],
                    known_actor_ids=["npc_low", "npc_high"],
                    pacing_rhythm_policy={
                        "min_tick_interval_ms": 0,
                        "max_ticks_per_pause": 2,
                    },
                ),
                elapsed_ms_between_ticks=[0],
            ),
            enabled=True,
            tick_enabled=True,
        )
        assert [tick.chosen_actor_id for tick in outcome.tick_outcomes] == [
            "npc_high",
            "npc_high",
        ]

    def test_cut_in_stops_loop(self):
        outcome = evaluate_autonomous_pause_loop(
            AutonomousPauseLoopInputs(
                tick_inputs=_ready_inputs(
                    pacing_rhythm_policy={
                        "min_tick_interval_ms": 0,
                        "max_ticks_per_pause": 3,
                    },
                ),
                elapsed_ms_between_ticks=[0, 0],
                player_cut_in_after_tick_index=0,
            ),
            enabled=True,
            tick_enabled=True,
        )
        assert outcome.stop_reason == LOOP_STOP_PLAYER_CUT_IN
        assert outcome.stopped_on_player_cut_in is True
        assert len(outcome.tick_outcomes) == 1

    def test_unsafe_off_stage_candidate_stops_loop(self):
        outcome = evaluate_autonomous_pause_loop(
            AutonomousPauseLoopInputs(
                tick_inputs=_ready_inputs(
                    visible_npc_ids=[],
                    known_actor_ids=["npc_b"],
                    pacing_rhythm_policy={
                        "min_tick_interval_ms": 0,
                        "max_ticks_per_pause": 3,
                    },
                ),
                elapsed_ms_between_ticks=[0, 0],
            ),
            enabled=True,
            tick_enabled=True,
        )
        assert outcome.stop_reason == LOOP_STOP_UNSAFE_CANDIDATE
        assert outcome.stopped_on_unsafe_candidate is True
        assert len(outcome.tick_outcomes) == 1

    def test_off_stage_commits_remain_stage_g_gated(self):
        outcome = evaluate_autonomous_pause_loop(
            AutonomousPauseLoopInputs(
                tick_inputs=_ready_inputs(
                    visible_npc_ids=[],
                    known_actor_ids=["npc_a"],
                    known_room_ids=["room_a"],
                    pacing_rhythm_policy={
                        "min_tick_interval_ms": 0,
                        "max_ticks_per_pause": 1,
                    },
                ),
            ),
            enabled=True,
            tick_enabled=True,
        )
        commit = outcome.tick_outcomes[0].off_stage_commit_result
        assert commit["attempted"] is True
        assert commit["committed"] is False
        assert commit["reason"] == "auto_commit_disabled"

    def test_loop_invariants_never_advance_path_or_consume_beats(self):
        outcome = evaluate_autonomous_pause_loop(
            AutonomousPauseLoopInputs(
                tick_inputs=_ready_inputs(
                    pacing_rhythm_policy={
                        "min_tick_interval_ms": 0,
                        "max_ticks_per_pause": 2,
                    },
                ),
                elapsed_ms_between_ticks=[0],
            ),
            enabled=True,
            tick_enabled=True,
        )
        assert outcome.canonical_path_advanced is False
        assert outcome.mandatory_beat_consumed is False
        assert all(t.canonical_path_advanced is False for t in outcome.tick_outcomes)
        assert all(t.mandatory_beat_consumed is False for t in outcome.tick_outcomes)


# ── Hard boundaries (Stage E) ────────────────────────────────────────────────


class TestHardBoundaries:
    def test_disabled_by_default_emits_nothing(self):
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=False)
        assert outcome.block_stream_event is None
        assert outcome.autonomous_tick_suppressed_reason == SUPPRESS_FLAG_DISABLED

    def test_canonical_path_never_advances(self):
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=True)
        assert outcome.canonical_path_advanced is False

    def test_mandatory_beat_never_consumed(self):
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=True)
        assert outcome.mandatory_beat_consumed is False

    def test_shadow_only_is_false_live_path(self):
        # Stage E is the LIVE emission path. The shadow path's contract has
        # shadow_only=True; the autonomous tick coordinator does not.
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=True)
        assert outcome.shadow_only is False

    def test_to_dict_exposes_required_diagnostic_fields(self):
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=True)
        d = outcome.to_dict()
        for key in (
            "autonomous_tick_enabled",
            "tick_trigger_kind",
            "chosen_actor_id",
            "chosen_action_kind",
            "motivation_scores",
            "silence_reason",
            "cooldown_state",
            "autonomous_tick_suppressed_reason",
            "block_stream_event",
        ):
            assert key in d, f"missing diagnostic field: {key}"

    def test_motivation_scores_are_a_mapping_of_actor_to_float(self):
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=True)
        for actor, score in outcome.motivation_scores.items():
            assert isinstance(actor, str) and actor
            assert isinstance(score, float)


# ── ADR-0039 vocabulary discipline ────────────────────────────────────────────


class TestADR0039Discipline:
    """No Pi/Π keys, no hardcoded actor IDs, no fixed speaker rotation."""

    _PI_PATTERNS = [
        re.compile(r"\bPi\d+\b"),
        re.compile(r"\bΠ\d+\b"),
        re.compile(r"\bpi_\d+\b"),
    ]
    _FORBIDDEN_NPC_LITERALS = ("veronique", "michel", "annette", "alain")
    _FIXED_ROTATION_TERMS = (
        "speaker_queue",
        "round_robin",
        "turn_order",
        "fixed_roster",
        "wall_clock_polling",
        "background_scheduler",
    )

    def _source(self) -> str:
        from ai_stack import autonomous_tick

        with open(autonomous_tick.__file__, "r", encoding="utf-8") as fh:
            return fh.read()

    def test_no_pi_keys_in_module_source(self):
        source = self._source()
        for pattern in self._PI_PATTERNS:
            assert not pattern.search(source), f"Pi/Π key in module: {pattern.pattern}"

    def test_no_hardcoded_npc_ids_in_module_source(self):
        source = self._source().lower()
        for literal in self._FORBIDDEN_NPC_LITERALS:
            assert literal not in source, f"hardcoded NPC id '{literal}' in module"

    def test_no_fixed_rotation_terms_in_module_source(self):
        source = self._source().lower()
        for term in self._FIXED_ROTATION_TERMS:
            assert term not in source, f"forbidden term '{term}' in module"

    def test_no_pi_keys_in_outcome_dict(self):
        outcome = evaluate_autonomous_tick(_ready_inputs(), enabled=True)
        flat = repr(outcome.to_dict())
        for pattern in self._PI_PATTERNS:
            assert not pattern.search(flat), f"Pi/Π key in outcome dict: {pattern.pattern}"
