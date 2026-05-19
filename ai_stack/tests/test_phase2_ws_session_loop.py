"""Phase 2 — WebSocket Session Loop pure-helper tests.

Tests for ai_stack/phase2_ws_session_loop.py:
* feature-flag is_ws_session_loop_enabled (fail-closed)
* WSSessionLoopState transitions
* apply_cut_in semantics per block type (em_dash / skip_to_end / no_active_block)
* server → client message builders
* cut_in_state_for_kind mapping

No WebSocket transport in these tests — that lives in
world-engine/tests/test_phase2_ws_session_loop_endpoint.py.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest

from ai_stack.director_pulse_contracts import (
    BLOCK_TYPE_ACTOR_ACTION,
    BLOCK_TYPE_ACTOR_LINE,
    BLOCK_TYPE_ENVIRONMENT_INTERACTION,
    BLOCK_TYPE_NARRATOR,
    BLOCK_TYPE_SOUFFLEUSE,
    CUT_IN_CUT_EM_DASH,
    CUT_IN_CUT_SKIP_TO_END,
    CUT_IN_UNINTERRUPTED,
    CUT_KIND_EM_DASH,
    CUT_KIND_NO_ACTIVE_BLOCK,
    CUT_KIND_SKIP_TO_END,
    SCHEMA_BLOCK_STREAM_EVENT,
    SCHEMA_PLAYER_CUT_IN_EVENT,
    build_block_stream_event,
)
from ai_stack.phase2_ws_session_loop import (
    CLIENT_MSG_CUT_IN,
    CLIENT_MSG_PING,
    CLIENT_MSG_START_TURN,
    MSG_AUTONOMOUS_TICK_EVALUATED,
    MSG_BLOCK_COMPLETED,
    MSG_BLOCK_CUT,
    MSG_BLOCK_STARTED,
    MSG_STREAM_ERROR,
    MSG_STREAM_IDLE,
    MSG_STREAM_STARTED,
    PHASE2_WS_SESSION_LOOP_ENABLED,
    SERVER_MSG_KINDS,
    WSSessionLoopState,
    apply_cut_in,
    cut_in_state_for_kind,
    is_ws_session_loop_enabled,
    msg_autonomous_tick_evaluated,
    msg_block_completed,
    msg_block_cut,
    msg_block_started,
    msg_stream_error,
    msg_stream_idle,
    msg_stream_started,
)


def _tid() -> str:
    return str(uuid.uuid4())


def _stream_event(block_type: str, *, text: str = "Hello") -> dict[str, Any]:
    return build_block_stream_event(
        tick_id=_tid(),
        block_type=block_type,
        block_payload={"id": _tid(), "block_type": block_type, "text": text},
        cut_in_state=CUT_IN_UNINTERRUPTED,
        lane="visible_scene_output",
        source="director",
    )


# ── is_ws_session_loop_enabled ────────────────────────────────────────────────


class TestFeatureFlag:
    def test_flag_name_constant(self):
        assert PHASE2_WS_SESSION_LOOP_ENABLED == "PHASE2_WS_SESSION_LOOP_ENABLED"

    def test_default_off(self, monkeypatch):
        monkeypatch.delenv(PHASE2_WS_SESSION_LOOP_ENABLED, raising=False)
        assert is_ws_session_loop_enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE", " 1 "])
    def test_true_values_enable(self, monkeypatch, value):
        monkeypatch.setenv(PHASE2_WS_SESSION_LOOP_ENABLED, value)
        assert is_ws_session_loop_enabled() is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "garbage"])
    def test_false_values_disable(self, monkeypatch, value):
        monkeypatch.setenv(PHASE2_WS_SESSION_LOOP_ENABLED, value)
        assert is_ws_session_loop_enabled() is False


# ── WSSessionLoopState ────────────────────────────────────────────────────────


class TestWSSessionLoopState:
    def test_initial_state(self):
        state = WSSessionLoopState(session_id="s1")
        assert state.session_id == "s1"
        assert state.active_block_id is None
        assert state.active_block_type is None
        assert state.cut_in_count == 0
        assert state.last_player_cut_in_event is None
        assert state.queued_player_inputs == []
        assert state.stream_finished is False

    def test_mark_block_started_uses_payload_block_type(self):
        state = WSSessionLoopState(session_id="s1")
        event = _stream_event(BLOCK_TYPE_ACTOR_LINE)
        state.mark_block_started(event)
        assert state.active_block_id == event["event_id"]
        assert state.active_block_type == BLOCK_TYPE_ACTOR_LINE

    def test_mark_block_completed_clears_active(self):
        state = WSSessionLoopState(session_id="s1")
        state.mark_block_started(_stream_event(BLOCK_TYPE_NARRATOR))
        state.mark_block_completed()
        assert state.active_block_id is None
        assert state.active_block_type is None

    def test_mark_stream_idle_finalizes(self):
        state = WSSessionLoopState(session_id="s1")
        state.mark_block_started(_stream_event(BLOCK_TYPE_NARRATOR))
        state.mark_stream_idle()
        assert state.stream_finished is True
        assert state.active_block_id is None


# ── apply_cut_in semantics by block type ──────────────────────────────────────


class TestApplyCutInActorLine:
    def test_em_dash(self):
        state = WSSessionLoopState(session_id="s1")
        ev = _stream_event(BLOCK_TYPE_ACTOR_LINE)
        state.mark_block_started(ev)
        outcome = apply_cut_in(state, tick_id=ev["tick_id"], player_input_payload={"text": "Stop!"})
        assert outcome["cut_kind"] == CUT_KIND_EM_DASH
        assert outcome["drop_remaining_blocks"] is True
        assert outcome["flush_active_block"] is False
        assert outcome["queue_input_for_next_turn"] is True

    def test_player_cut_in_event_built(self):
        state = WSSessionLoopState(session_id="s1")
        ev = _stream_event(BLOCK_TYPE_ACTOR_LINE)
        state.mark_block_started(ev)
        outcome = apply_cut_in(state, tick_id=ev["tick_id"], player_input_payload={"text": "Stop!"})
        cut_ev = outcome["player_cut_in_event"]
        assert cut_ev["schema_version"] == SCHEMA_PLAYER_CUT_IN_EVENT
        assert cut_ev["cut_kind"] == CUT_KIND_EM_DASH
        assert cut_ev["interrupted_block_type"] == BLOCK_TYPE_ACTOR_LINE
        assert cut_ev["interrupted_block_id"] == ev["event_id"]
        assert cut_ev["player_input_payload"] == {"text": "Stop!"}

    def test_increments_cut_in_count(self):
        state = WSSessionLoopState(session_id="s1")
        state.mark_block_started(_stream_event(BLOCK_TYPE_ACTOR_LINE))
        apply_cut_in(state, tick_id=_tid(), player_input_payload={"text": "a"})
        apply_cut_in(state, tick_id=_tid(), player_input_payload={"text": "b"})
        assert state.cut_in_count == 2

    def test_queues_player_input(self):
        state = WSSessionLoopState(session_id="s1")
        state.mark_block_started(_stream_event(BLOCK_TYPE_ACTOR_LINE))
        apply_cut_in(state, tick_id=_tid(), player_input_payload={"text": "a"})
        assert state.queued_player_inputs == [{"text": "a"}]


class TestApplyCutInSkipToEnd:
    @pytest.mark.parametrize("block_type", [
        BLOCK_TYPE_NARRATOR,
        BLOCK_TYPE_SOUFFLEUSE,
        BLOCK_TYPE_ACTOR_ACTION,
        BLOCK_TYPE_ENVIRONMENT_INTERACTION,
    ])
    def test_skip_to_end_for_non_actor_line(self, block_type):
        state = WSSessionLoopState(session_id="s1")
        ev = _stream_event(block_type)
        state.mark_block_started(ev)
        outcome = apply_cut_in(state, tick_id=ev["tick_id"], player_input_payload={"text": "x"})
        assert outcome["cut_kind"] == CUT_KIND_SKIP_TO_END
        assert outcome["drop_remaining_blocks"] is True
        assert outcome["flush_active_block"] is True


class TestApplyCutInNoActiveBlock:
    def test_no_active_block_when_state_empty(self):
        state = WSSessionLoopState(session_id="s1")
        outcome = apply_cut_in(state, tick_id=_tid(), player_input_payload={"text": "hi"})
        assert outcome["cut_kind"] == CUT_KIND_NO_ACTIVE_BLOCK
        assert outcome["interrupted_block_id"] is None
        assert outcome["interrupted_block_type"] is None
        assert outcome["drop_remaining_blocks"] is False
        assert outcome["flush_active_block"] is False
        assert outcome["queue_input_for_next_turn"] is True


# ── cut_in_state_for_kind mapping ─────────────────────────────────────────────


class TestCutInStateForKind:
    def test_em_dash_maps(self):
        assert cut_in_state_for_kind(CUT_KIND_EM_DASH) == CUT_IN_CUT_EM_DASH

    def test_skip_to_end_maps(self):
        assert cut_in_state_for_kind(CUT_KIND_SKIP_TO_END) == CUT_IN_CUT_SKIP_TO_END

    def test_no_active_block_maps_uninterrupted(self):
        assert cut_in_state_for_kind(CUT_KIND_NO_ACTIVE_BLOCK) == CUT_IN_UNINTERRUPTED


# ── Server → client message builders ──────────────────────────────────────────


class TestMessageBuilders:
    def test_msg_stream_started(self):
        m = msg_stream_started(session_id="s1", turn_id="t1")
        assert m["kind"] == MSG_STREAM_STARTED
        assert m["session_id"] == "s1"
        assert m["turn_id"] == "t1"
        assert "message_id" in m

    def test_msg_block_started_carries_event(self):
        ev = _stream_event(BLOCK_TYPE_NARRATOR)
        m = msg_block_started(event=ev)
        assert m["kind"] == MSG_BLOCK_STARTED
        assert m["event_id"] == ev["event_id"]
        assert m["block_type"] == ev["block_type"]
        assert m["block_stream_event"] is ev

    def test_msg_block_completed(self):
        m = msg_block_completed(event_id="evt-1")
        assert m["kind"] == MSG_BLOCK_COMPLETED
        assert m["event_id"] == "evt-1"

    def test_msg_block_cut_carries_outcome(self):
        state = WSSessionLoopState(session_id="s1")
        ev = _stream_event(BLOCK_TYPE_ACTOR_LINE)
        state.mark_block_started(ev)
        outcome = apply_cut_in(state, tick_id=ev["tick_id"], player_input_payload={"text": "Stop"})
        m = msg_block_cut(cut_outcome=outcome)
        assert m["kind"] == MSG_BLOCK_CUT
        assert m["cut_kind"] == CUT_KIND_EM_DASH
        assert m["drop_remaining_blocks"] is True
        assert m["flush_active_block"] is False
        assert m["player_cut_in_event"]["schema_version"] == SCHEMA_PLAYER_CUT_IN_EVENT

    def test_msg_stream_idle(self):
        m = msg_stream_idle(reason="completed")
        assert m["kind"] == MSG_STREAM_IDLE
        assert m["reason"] == "completed"

    def test_msg_stream_error(self):
        m = msg_stream_error(reason="auth_required", detail="missing key")
        assert m["kind"] == MSG_STREAM_ERROR
        assert m["reason"] == "auth_required"
        assert m["detail"] == "missing key"

    def test_msg_autonomous_tick_evaluated_carries_summary(self):
        m = msg_autonomous_tick_evaluated(
            summary={
                "tick_id": "t-1",
                "chosen_actor_id": "npc_a",
                "block_emitted": True,
            }
        )
        assert m["kind"] == MSG_AUTONOMOUS_TICK_EVALUATED
        assert m["summary"]["tick_id"] == "t-1"
        assert m["summary"]["chosen_actor_id"] == "npc_a"
        assert m["summary"]["block_emitted"] is True

    def test_msg_autonomous_tick_evaluated_kind_in_server_message_set(self):
        assert MSG_AUTONOMOUS_TICK_EVALUATED in SERVER_MSG_KINDS


# ── Anti-hardcoding spot-checks (ADR-0039) ────────────────────────────────────


class TestAdr0039Discipline:
    """Cut semantics are block-type-driven only. No actor/room IDs leak in."""

    def test_apply_cut_in_does_not_reference_specific_actor_ids(self):
        state = WSSessionLoopState(session_id="s1")
        ev = _stream_event(BLOCK_TYPE_ACTOR_LINE)
        state.mark_block_started(ev)
        outcome = apply_cut_in(state, tick_id=ev["tick_id"], player_input_payload={"text": "x"})
        # The outcome encodes block_type, not actor IDs.
        assert "actor_id" not in outcome["player_cut_in_event"]
        # cut_kind is determined by block_type alone.
        assert outcome["cut_kind"] == CUT_KIND_EM_DASH

    def test_no_pi_keys_in_outcome(self):
        state = WSSessionLoopState(session_id="s1")
        state.mark_block_started(_stream_event(BLOCK_TYPE_NARRATOR))
        outcome = apply_cut_in(state, tick_id=_tid(), player_input_payload={"text": "x"})
        flat = repr(outcome).lower()
        # No legacy Pi/Π runtime keys.
        assert "pi_" not in flat
        # Greek Π
        assert "Π" not in flat
