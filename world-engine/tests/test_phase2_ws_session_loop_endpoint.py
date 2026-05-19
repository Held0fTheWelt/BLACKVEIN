"""Phase 2 — WS Session Loop endpoint tests.

Exercises the WebSocket endpoint mounted at
``/api/story/sessions/{session_id}/stream`` with a FastAPI TestClient.

Tests target the WS protocol layer (the orchestration between socket I/O
and ai_stack/phase2_ws_session_loop helpers). The turn-execution layer is
a thin patch on ``StoryRuntimeManager.execute_turn`` because the WS layer's
job is the streaming/cut-in protocol, not turn business logic — that is
covered by the integration suite under tests/smoke.

What is NOT mocked here:
* ai_stack helpers (real pure functions)
* the WS endpoint itself
* the message protocol

Governance:
* ADR-0058 — Director-Driven Pulse and Block-Stream-Bus
* ADR-0039 — No Pi/Π keys
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_stack.director_pulse_contracts import (
    BLOCK_TYPE_ACTOR_LINE,
    BLOCK_TYPE_NARRATOR,
    CUT_IN_UNINTERRUPTED,
    build_block_stream_event,
)
from ai_stack.phase2_ws_session_loop import (
    PHASE2_WS_SESSION_LOOP_ENABLED,
    is_ws_session_loop_enabled,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


class _ManagerStub:
    """Minimal StoryRuntimeManager stub that returns a canned envelope.

    The WS endpoint only consumes the turn's
    ``envelope.visible_scene_output.block_stream_events`` list — anything
    extra is irrelevant to the protocol-layer tests.

    Stage E hook: ``autonomous_envelope_extras`` is merged into the
    returned envelope so the autonomous-tick coordinator can read
    ``npc_actor_ids`` and ``diagnostics.director_pulse.*`` for live emission.
    """

    def __init__(
        self,
        *,
        events: list[dict[str, Any]] | None = None,
        known_sessions: set | None = None,
        autonomous_envelope_extras: dict[str, Any] | None = None,
    ):
        self.events = events or []
        self.known_sessions = known_sessions if known_sessions is not None else {"sess-1"}
        self.execute_calls: list[dict[str, Any]] = []
        self.autonomous_envelope_extras = autonomous_envelope_extras or {}

    def execute_turn(self, *, session_id: str, player_input: str, trace_id=None):
        self.execute_calls.append({
            "session_id": session_id,
            "player_input": player_input,
            "trace_id": trace_id,
        })
        if session_id not in self.known_sessions:
            raise KeyError(session_id)
        envelope: dict[str, Any] = {
            "visible_scene_output": {
                "blocks": [e.get("block_payload", {}) for e in self.events],
                "block_stream_events": self.events,
            },
        }
        envelope.update(self.autonomous_envelope_extras)
        return {
            "session_id": session_id,
            "turn_number": len(self.execute_calls),
            "canonical_turn_id": f"turn-{len(self.execute_calls)}",
            "envelope": envelope,
        }


def _stream_event(block_type: str, *, text: str = "Hello") -> dict[str, Any]:
    return build_block_stream_event(
        tick_id=str(uuid.uuid4()),
        block_type=block_type,
        block_payload={
            "id": str(uuid.uuid4()),
            "block_type": block_type,
            "text": text,
        },
        cut_in_state=CUT_IN_UNINTERRUPTED,
        lane="visible_scene_output",
        source="director",
    )


def _make_app(
    *,
    events: list[dict[str, Any]] | None = None,
    known_sessions: set | None = None,
    autonomous_envelope_extras: dict[str, Any] | None = None,
) -> FastAPI:
    from app.api.story_ws import story_ws_router, story_ws_support_router

    app = FastAPI()
    app.include_router(story_ws_router)
    app.include_router(story_ws_support_router)
    app.state.story_manager = _ManagerStub(
        events=events,
        known_sessions=known_sessions,
        autonomous_envelope_extras=autonomous_envelope_extras,
    )
    return app


def _autonomous_envelope_extras(
    *,
    npc_ids: list[str],
    high_motivation: bool = True,
    gathering_paused: bool = False,
    pacing_min_ms: float | None = None,
    max_ticks_per_pause: int | None = None,
    visible_npc_ids: list[str] | None = None,
    known_actor_ids: list[str] | None = None,
    known_room_ids: list[str] | None = None,
    marker_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build the envelope additions the WS loop needs for Stage E/F emission.

    When ``high_motivation`` is True the capability outputs are calibrated
    so each NPC easily crosses the configured policy threshold. Stage F
    surfaces (``visible_npc_ids`` / ``known_actor_ids`` / ``known_room_ids``)
    are optional and default to the supplied ``npc_ids`` set so existing
    Stage E tests retain identical semantics.
    """
    profiles = {
        "profiles": {
            npc_id: {
                "pressure_markers": [
                    {"t": str(i)}
                    for i in range((marker_counts or {}).get(npc_id, 10))
                ]
            }
            for npc_id in npc_ids
        }
    }
    cap_outputs = {
        "scene_energy_output": {"energy_level": "volatile" if high_motivation else "collapsed"},
        "social_pressure_output": {"band": "high" if high_motivation else "low"},
        "relationship_state_output": None,
        "narrative_momentum_output": {"state": "cresting" if high_motivation else "stalled"},
    }
    policy = {
        "base_threshold": 0.10 if high_motivation else 0.99,
        "score_weights": {
            "scene_energy": 0.25,
            "social_pressure": 0.30,
            "relationship_axis_pressure": 0.25,
            "narrative_momentum": 0.20,
        },
    }
    director_pulse: dict[str, Any] = {
        "capability_outputs": cap_outputs,
        "actor_pressure_profiles": profiles,
        "npc_motivation_score_policy": policy,
    }
    if pacing_min_ms is not None or max_ticks_per_pause is not None:
        pacing_policy: dict[str, Any] = {}
        if pacing_min_ms is not None:
            pacing_policy["min_tick_interval_ms"] = pacing_min_ms
        if max_ticks_per_pause is not None:
            pacing_policy["max_ticks_per_pause"] = max_ticks_per_pause
        director_pulse["pacing_rhythm_policy"] = pacing_policy
    diagnostics: dict[str, Any] = {"director_pulse": director_pulse}
    if gathering_paused:
        diagnostics["director_gathering_state"] = {"paused": True}
    extras: dict[str, Any] = {
        "npc_actor_ids": list(npc_ids),
        "diagnostics": diagnostics,
    }
    if visible_npc_ids is not None:
        extras["visible_npc_actor_ids"] = list(visible_npc_ids)
    if known_actor_ids is not None:
        extras["known_actor_ids"] = list(known_actor_ids)
    if known_room_ids is not None:
        extras["known_room_ids"] = list(known_room_ids)
    return extras


@pytest.fixture
def env_test_mode(monkeypatch):
    """Test-mode bypasses internal-API-key requirement (matches HTTP convention)."""
    monkeypatch.setenv("FLASK_ENV", "test")
    monkeypatch.delenv("PLAY_SERVICE_INTERNAL_API_KEY", raising=False)
    monkeypatch.delenv("ENV", raising=False)


@pytest.fixture
def ws_enabled(monkeypatch):
    monkeypatch.setenv(PHASE2_WS_SESSION_LOOP_ENABLED, "true")


@pytest.fixture
def ws_disabled(monkeypatch):
    monkeypatch.setenv(PHASE2_WS_SESSION_LOOP_ENABLED, "false")


# ── Feature flag tests ────────────────────────────────────────────────────────


class TestFeatureFlagGate:
    def test_endpoint_rejects_when_disabled(self, ws_disabled, env_test_mode):
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)])
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/api/story/sessions/sess-1/stream"):
                pass

    def test_support_endpoint_reports_disabled(self, ws_disabled, env_test_mode):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/api/story/runtime/ws-session-loop-support")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ws_session_loop_supported"] is False
        assert data["live_interruption_supported"] is False
        assert data["endpoint"] == "/api/story/sessions/{session_id}/stream"

    def test_support_endpoint_reports_enabled(self, ws_enabled, env_test_mode):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/api/story/runtime/ws-session-loop-support")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ws_session_loop_supported"] is True
        assert data["live_interruption_supported"] is True

    def test_support_endpoint_lists_cut_kind_semantics(self, ws_enabled, env_test_mode):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/api/story/runtime/ws-session-loop-support")
        sem = resp.json()["cut_kind_semantics"]
        assert sem["actor_line"] == "em_dash"
        assert sem["narrator"] == "skip_to_end"
        assert sem["souffleuse"] == "skip_to_end"
        assert sem["actor_action"] == "skip_to_end"
        assert sem["no_active_block"] == "no_active_block"


# ── Connection lifecycle ──────────────────────────────────────────────────────


class TestConnectionLifecycle:
    def test_connection_accepted_when_enabled(self, ws_enabled, env_test_mode):
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)])
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            first = ws.receive_json()
            assert first["kind"] == "stream_started"
            assert first["session_id"] == "sess-1"

    def test_ping_pong(self, ws_enabled, env_test_mode):
        app = _make_app()
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # stream_started
            ws.send_json({"kind": "ping"})
            pong = ws.receive_json()
            assert pong["kind"] == "pong"

    def test_unknown_kind_returns_stream_error(self, ws_enabled, env_test_mode):
        app = _make_app()
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # stream_started
            ws.send_json({"kind": "bogus"})
            err = ws.receive_json()
            assert err["kind"] == "stream_error"
            assert err["reason"] == "unknown_kind"

    def test_start_turn_missing_input_emits_stream_error(self, ws_enabled, env_test_mode):
        app = _make_app()
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # stream_started
            ws.send_json({"kind": "start_turn", "player_input": ""})
            err = ws.receive_json()
            assert err["kind"] == "stream_error"
            assert err["reason"] == "missing_player_input"


# ── Streaming behavior ────────────────────────────────────────────────────────


class TestStreaming:
    def test_one_event_emitted_at_a_time(self, ws_enabled, env_test_mode):
        events = [
            _stream_event(BLOCK_TYPE_NARRATOR, text="first"),
            _stream_event(BLOCK_TYPE_ACTOR_LINE, text="second"),
        ]
        app = _make_app(events=events)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # stream_started (handshake)
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            seq = []
            for _ in range(8):
                m = ws.receive_json()
                seq.append(m["kind"])
                if m["kind"] == "stream_idle":
                    break

            # Protocol: stream_started, block_started, block_completed,
            #          block_started, block_completed, stream_idle
            assert seq[0] == "stream_started"
            assert seq[1] == "block_started"
            assert seq[2] == "block_completed"
            assert seq[3] == "block_started"
            assert seq[4] == "block_completed"
            assert seq[-1] == "stream_idle"

    def test_stream_idle_when_no_events(self, ws_enabled, env_test_mode):
        app = _make_app(events=[])
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # initial stream_started
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            second_started = ws.receive_json()
            assert second_started["kind"] == "stream_started"
            idle = ws.receive_json()
            assert idle["kind"] == "stream_idle"
            assert idle["reason"] == "no_events"

    def test_block_started_carries_block_stream_event(self, ws_enabled, env_test_mode):
        ev = _stream_event(BLOCK_TYPE_ACTOR_LINE, text="Bonjour")
        app = _make_app(events=[ev])
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # initial stream_started
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            ws.receive_json()  # turn stream_started
            block_started = ws.receive_json()
            assert block_started["kind"] == "block_started"
            assert block_started["event_id"] == ev["event_id"]
            assert block_started["block_stream_event"]["block_payload"]["text"] == "Bonjour"

    def test_session_not_found(self, ws_enabled, env_test_mode):
        app = _make_app(events=[], known_sessions=set())
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/missing/stream") as ws:
            ws.receive_json()  # stream_started
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            err = ws.receive_json()
            assert err["kind"] == "stream_error"
            assert err["reason"] == "session_not_found"


# ── Cut-in semantics over WS ──────────────────────────────────────────────────


class TestCutInOverWs:
    def test_no_active_block_cut(self, ws_enabled, env_test_mode):
        """Cut-in sent before any block streamed → no_active_block."""
        app = _make_app(events=[])
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # stream_started
            ws.send_json({"kind": "cut_in", "player_input": "Hello"})
            cut = ws.receive_json()
            assert cut["kind"] == "block_cut"
            assert cut["cut_kind"] == "no_active_block"
            assert cut["player_cut_in_event"]["cut_kind"] == "no_active_block"

    def test_carryover_replayed_into_next_start_turn(self, ws_enabled, env_test_mode):
        """A no_active_block cut-in queues input; the next start_turn replays it."""
        manager_events = [_stream_event(BLOCK_TYPE_NARRATOR)]
        app = _make_app(events=manager_events)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # stream_started
            ws.send_json({"kind": "cut_in", "player_input": "look around"})
            ws.receive_json()  # block_cut (no_active_block)
            # Empty player_input on start_turn → server replays the carryover.
            ws.send_json({"kind": "start_turn", "player_input": ""})
            # Drain until stream_idle.
            seen_kinds = []
            for _ in range(8):
                m = ws.receive_json()
                seen_kinds.append(m["kind"])
                if m["kind"] == "stream_idle":
                    break
            assert "stream_started" in seen_kinds
            # Manager should have executed exactly one turn with the carryover input.
            manager = app.state.story_manager
            assert len(manager.execute_calls) == 1
            assert manager.execute_calls[0]["player_input"] == "look around"

    def test_cut_in_during_actor_line_returns_em_dash(self, ws_enabled, env_test_mode, monkeypatch):
        """When a cut-in arrives during an actor_line block, cut_kind=em_dash."""
        # Force pacing so the actor_line block stays "active" between started/completed,
        # giving the cut-in queue a chance to fire before completion.
        monkeypatch.setenv("PHASE2_WS_BLOCK_PACING_SECONDS", "0.3")
        ev = _stream_event(BLOCK_TYPE_ACTOR_LINE, text="Je suis—")
        app = _make_app(events=[ev])
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # initial stream_started
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            ws.receive_json()  # turn stream_started
            block_started = ws.receive_json()
            assert block_started["kind"] == "block_started"
            # Cut in while pacing window is open
            ws.send_json({"kind": "cut_in", "player_input": "Stop!"})
            cut = ws.receive_json()
            assert cut["kind"] == "block_cut"
            assert cut["cut_kind"] == "em_dash"
            assert cut["block_type"] == BLOCK_TYPE_ACTOR_LINE
            assert cut["drop_remaining_blocks"] is True
            assert cut["flush_active_block"] is False

    def test_cut_in_during_narrator_returns_skip_to_end(self, ws_enabled, env_test_mode, monkeypatch):
        monkeypatch.setenv("PHASE2_WS_BLOCK_PACING_SECONDS", "0.3")
        ev = _stream_event(BLOCK_TYPE_NARRATOR, text="The door creaks open...")
        app = _make_app(events=[ev])
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # initial stream_started
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            ws.receive_json()  # turn stream_started
            ws.receive_json()  # block_started
            ws.send_json({"kind": "cut_in", "player_input": "I leave"})
            cut = ws.receive_json()
            assert cut["kind"] == "block_cut"
            assert cut["cut_kind"] == "skip_to_end"
            assert cut["drop_remaining_blocks"] is True
            assert cut["flush_active_block"] is True


# ── REST/bundle fallback discipline ───────────────────────────────────────────


class TestRestFallbackDiscipline:
    def test_disabling_flag_does_not_touch_rest_endpoint_modules(self, ws_disabled, env_test_mode):
        """When WS is disabled the REST module is still importable and untouched."""
        from app.api import http as http_module
        from app.api import story_ws as ws_module

        # WS module is importable but reports disabled.
        assert is_ws_session_loop_enabled() is False
        # REST module exports unchanged: still has the canonical execute_story_turn route.
        assert any(
            getattr(r, "path", None) == "/api/story/sessions/{session_id}/turns"
            for r in http_module.router.routes
        )
        # And the WS endpoint path is registered on its own router, not on http_router.
        ws_paths = [getattr(r, "path", None) for r in ws_module.story_ws_router.routes]
        assert "/api/story/sessions/{session_id}/stream" in ws_paths


# ── Player-input preservation ─────────────────────────────────────────────────


class TestPlayerInputPreservation:
    def test_player_input_never_swallowed_on_cut_in(self, ws_enabled, env_test_mode):
        """A cut-in payload is always carried in the player_cut_in_event."""
        app = _make_app(events=[])
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # stream_started
            ws.send_json({"kind": "cut_in", "player_input": "Hi there"})
            cut = ws.receive_json()
            payload = cut["player_cut_in_event"]["player_input_payload"]
            assert payload.get("player_input") == "Hi there"

    def test_malformed_message_does_not_crash_stream(self, ws_enabled, env_test_mode):
        app = _make_app()
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # stream_started
            # FastAPI receive_json rejects non-JSON; we test our handling of a
            # dict that isn't a recognised kind — which we already cover with
            # unknown_kind. Here we send a list-shaped payload via send_text.
            ws.send_text("[1,2,3]")
            err = ws.receive_json()
            assert err["kind"] == "stream_error"


# ── Stage E: Autonomous Director Tick over WS ────────────────────────────────


@pytest.fixture
def autonomous_enabled(monkeypatch):
    from ai_stack.phase2_autonomous_tick import PHASE2_AUTONOMOUS_TICK_ENABLED
    monkeypatch.setenv(PHASE2_AUTONOMOUS_TICK_ENABLED, "true")


@pytest.fixture
def autonomous_disabled(monkeypatch):
    from ai_stack.phase2_autonomous_tick import PHASE2_AUTONOMOUS_TICK_ENABLED
    monkeypatch.setenv(PHASE2_AUTONOMOUS_TICK_ENABLED, "false")


@pytest.fixture
def autonomous_pause_loop_enabled(monkeypatch):
    from ai_stack.phase2_autonomous_tick import PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED
    monkeypatch.setenv(PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED, "true")


@pytest.fixture
def autonomous_pause_loop_disabled(monkeypatch):
    from ai_stack.phase2_autonomous_tick import PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED
    monkeypatch.setenv(PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED, "false")


class TestAutonomousTickSupportFlag:
    def test_support_endpoint_reports_autonomous_enabled(
        self, ws_enabled, autonomous_enabled, autonomous_pause_loop_enabled, env_test_mode,
    ):
        app = _make_app()
        client = TestClient(app)
        data = client.get("/api/story/runtime/ws-session-loop-support").json()
        assert data["autonomous_tick_enabled"] is True
        assert data["autonomous_pause_loop_enabled"] is True
        assert "user_pause" in data["autonomous_pause_loop_trigger_kinds"]
        assert "motivation_threshold_crossed" in data["autonomous_tick_trigger_kinds"]

    def test_support_endpoint_reports_autonomous_disabled(
        self, ws_enabled, autonomous_disabled, autonomous_pause_loop_disabled, env_test_mode,
    ):
        app = _make_app()
        client = TestClient(app)
        data = client.get("/api/story/runtime/ws-session-loop-support").json()
        assert data["autonomous_tick_enabled"] is False
        assert data["autonomous_pause_loop_enabled"] is False

    def test_no_autonomous_message_when_flag_disabled(self, ws_enabled, autonomous_disabled, env_test_mode):
        """Flag off → no autonomous_tick_evaluated message after a user turn."""
        extras = _autonomous_envelope_extras(npc_ids=["npc_a"])
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # stream_started
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            seen = []
            for _ in range(10):
                m = ws.receive_json()
                seen.append(m["kind"])
                if m["kind"] == "stream_idle":
                    break
            assert "autonomous_tick_evaluated" not in seen


class TestAutonomousTickEmission:
    def test_autonomous_block_emitted_after_user_turn(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        """When motivation crosses threshold an autonomous actor_line is streamed."""
        extras = _autonomous_envelope_extras(npc_ids=["npc_a"], high_motivation=True)
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # stream_started
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            seen: list[dict[str, Any]] = []
            for _ in range(12):
                m = ws.receive_json()
                seen.append(m)
                if m["kind"] == "stream_idle" and m.get("reason") == "autonomous_tick_completed":
                    break
            kinds = [m["kind"] for m in seen]
            # User-turn delivery (stream_started/block_started/block_completed),
            # then autonomous_tick_evaluated, then one block_started/completed,
            # then stream_idle(autonomous_tick_completed).
            assert "autonomous_tick_evaluated" in kinds
            evaluated_index = kinds.index("autonomous_tick_evaluated")
            # The autonomous block_started must follow evaluation.
            assert "block_started" in kinds[evaluated_index + 1 :]
            # The final message is the autonomous-tick-completed idle.
            assert seen[-1]["kind"] == "stream_idle"
            assert seen[-1]["reason"] == "autonomous_tick_completed"

    def test_autonomous_summary_carries_required_fields(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(npc_ids=["npc_a"], high_motivation=True)
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            summary = None
            for _ in range(10):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    summary = m["summary"]
                    break
            assert summary is not None
            for required in (
                "tick_id",
                "tick_trigger_kind",
                "chosen_actor_id",
                "chosen_action_kind",
                "silence_reason",
                "cooldown_state",
                "motivation_scores",
                "block_emitted",
                "canonical_path_advanced",
                "mandatory_beat_consumed",
            ):
                assert required in summary, f"missing diagnostic field: {required}"
            assert summary["canonical_path_advanced"] is False
            assert summary["mandatory_beat_consumed"] is False

    def test_silence_when_no_npc_above_threshold(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(npc_ids=["npc_a"], high_motivation=False)
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            summary = None
            final_idle = None
            for _ in range(10):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    summary = m["summary"]
                if m["kind"] == "stream_idle":
                    final_idle = m
                    break
            assert summary is not None
            assert summary["block_emitted"] is False
            assert summary["silence_reason"]  # populated
            assert summary["chosen_actor_id"] is None
            # Silence → no autonomous block → idle with reason "completed".
            assert final_idle is not None
            assert final_idle["reason"] == "completed"

    def test_no_autonomous_tick_when_no_npc_actor_ids(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        """If the envelope provides no npc_actor_ids the coordinator suppresses."""
        # No envelope extras → no npc_actor_ids → suppression.
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)])
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            summary = None
            for _ in range(10):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    summary = m["summary"]
                if m["kind"] == "stream_idle":
                    break
            assert summary is not None
            assert summary["autonomous_tick_suppressed_reason"] == "no_npcs_present"
            assert summary["block_emitted"] is False


class TestAutonomousCutIn:
    def test_player_cut_in_interrupts_autonomous_actor_line_with_em_dash(
        self, ws_enabled, autonomous_enabled, env_test_mode, monkeypatch,
    ):
        """A cut-in while an autonomous actor_line streams → em_dash + carryover."""
        monkeypatch.setenv("PHASE2_WS_BLOCK_PACING_SECONDS", "0.3")
        extras = _autonomous_envelope_extras(npc_ids=["npc_a"], high_motivation=True)
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()  # initial stream_started
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            # Drain through the user-turn delivery and stop on the autonomous
            # block_started so we can cut into it.
            autonomous_block_started = None
            for _ in range(20):
                m = ws.receive_json()
                if m["kind"] == "block_started":
                    bp = (m.get("block_stream_event") or {}).get("block_payload") or {}
                    if bp.get("originator") == "autonomous_tick":
                        autonomous_block_started = m
                        break
            assert autonomous_block_started is not None, "no autonomous block_started seen"
            # Now cut into the autonomous actor_line.
            ws.send_json({"kind": "cut_in", "player_input": "Stop talking!"})
            cut = None
            for _ in range(10):
                m = ws.receive_json()
                if m["kind"] == "block_cut":
                    cut = m
                    break
            assert cut is not None
            assert cut["cut_kind"] == "em_dash"
            assert cut["block_type"] == BLOCK_TYPE_ACTOR_LINE

    def test_cut_in_carryover_replayed_on_next_start_turn(
        self, ws_enabled, autonomous_enabled, env_test_mode, monkeypatch,
    ):
        """A cut into an autonomous block queues input for the next user turn."""
        monkeypatch.setenv("PHASE2_WS_BLOCK_PACING_SECONDS", "0.3")
        extras = _autonomous_envelope_extras(npc_ids=["npc_a"], high_motivation=True)
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "first"})
            for _ in range(20):
                m = ws.receive_json()
                if m["kind"] == "block_started":
                    bp = (m.get("block_stream_event") or {}).get("block_payload") or {}
                    if bp.get("originator") == "autonomous_tick":
                        break
            ws.send_json({"kind": "cut_in", "player_input": "second"})
            for _ in range(5):
                m = ws.receive_json()
                if m["kind"] == "block_cut":
                    break
            ws.send_json({"kind": "start_turn", "player_input": ""})
            # Drain to the next stream_idle.
            for _ in range(12):
                m = ws.receive_json()
                if m["kind"] == "stream_idle":
                    break
            manager = app.state.story_manager
            # The carried-over "second" input must have been replayed.
            assert any(call["player_input"] == "second" for call in manager.execute_calls)


class TestAutonomousGatheringPaused:
    def test_gathering_paused_does_not_consume_beats_or_advance_path(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(
            npc_ids=["npc_a"], high_motivation=False, gathering_paused=True,
        )
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            summary = None
            for _ in range(10):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    summary = m["summary"]
                if m["kind"] == "stream_idle":
                    break
            assert summary is not None
            assert summary["gathering_paused"] is True
            assert summary["canonical_path_advanced"] is False
            assert summary["mandatory_beat_consumed"] is False


class TestAutonomousPauseLoop:
    def test_loop_disabled_by_default_keeps_single_tick_behavior(
        self, ws_enabled, autonomous_enabled, autonomous_pause_loop_disabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(
            npc_ids=["npc_a"],
            high_motivation=True,
            pacing_min_ms=0,
            max_ticks_per_pause=3,
        )
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            seen: list[dict[str, Any]] = []
            for _ in range(20):
                m = ws.receive_json()
                seen.append(m)
                if m["kind"] == "stream_idle":
                    break
            evaluated = [m for m in seen if m["kind"] == "autonomous_tick_evaluated"]
            assert len(evaluated) == 1
            assert evaluated[0]["summary"]["autonomous_pause_loop"]["enabled"] is False
            assert seen[-1]["reason"] == "autonomous_tick_completed"

    def test_loop_enabled_streams_multiple_autonomous_blocks_until_max(
        self, ws_enabled, autonomous_enabled, autonomous_pause_loop_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(
            npc_ids=["npc_a"],
            high_motivation=True,
            pacing_min_ms=0,
            max_ticks_per_pause=2,
        )
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            seen: list[dict[str, Any]] = []
            for _ in range(30):
                m = ws.receive_json()
                seen.append(m)
                if m["kind"] == "stream_idle":
                    break
            evaluated = [m for m in seen if m["kind"] == "autonomous_tick_evaluated"]
            autonomous_blocks = [
                m for m in seen
                if m["kind"] == "block_started"
                and ((m.get("block_stream_event") or {}).get("block_payload") or {}).get("originator")
                == "autonomous_tick"
            ]
            assert len(evaluated) == 2
            assert len(autonomous_blocks) == 2
            assert evaluated[-1]["summary"]["autonomous_pause_loop"]["stop_reason"] == "max_ticks_per_pause"
            assert seen[-1]["reason"] == "autonomous_pause_loop_completed"

    def test_loop_silence_tick_is_diagnostic_and_stops(
        self, ws_enabled, autonomous_enabled, autonomous_pause_loop_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(
            npc_ids=["npc_a"],
            high_motivation=False,
            pacing_min_ms=0,
            max_ticks_per_pause=3,
        )
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            seen: list[dict[str, Any]] = []
            for _ in range(15):
                m = ws.receive_json()
                seen.append(m)
                if m["kind"] == "stream_idle":
                    break
            evaluated = [m for m in seen if m["kind"] == "autonomous_tick_evaluated"]
            assert len(evaluated) == 1
            summary = evaluated[0]["summary"]
            assert summary["block_emitted"] is False
            assert summary["autonomous_pause_loop"]["stop_reason"] == "no_motivation_threshold_crossed"
            assert summary["canonical_path_advanced"] is False
            assert summary["mandatory_beat_consumed"] is False

    def test_highest_motivated_npc_wins_loop_tick(
        self, ws_enabled, autonomous_enabled, autonomous_pause_loop_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(
            npc_ids=["npc_low", "npc_high"],
            high_motivation=True,
            pacing_min_ms=0,
            max_ticks_per_pause=1,
            marker_counts={"npc_low": 1, "npc_high": 10},
        )
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            summary = None
            for _ in range(15):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    summary = m["summary"]
                    break
            assert summary is not None
            assert summary["chosen_actor_id"] == "npc_high"

    def test_cut_in_between_autonomous_ticks_stops_loop(
        self, ws_enabled, autonomous_enabled, autonomous_pause_loop_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(
            npc_ids=["npc_a"],
            high_motivation=True,
            pacing_min_ms=300,
            max_ticks_per_pause=3,
        )
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            evaluated_count = 0
            saw_first_autonomous_completed = False
            for _ in range(20):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    evaluated_count += 1
                if m["kind"] == "block_completed" and evaluated_count == 1:
                    saw_first_autonomous_completed = True
                    break
            assert saw_first_autonomous_completed is True
            ws.send_json({"kind": "cut_in", "player_input": "I interrupt the pause."})
            cut = None
            for _ in range(10):
                m = ws.receive_json()
                if m["kind"] == "block_cut":
                    cut = m
                    break
            assert cut is not None
            assert cut["cut_kind"] == "no_active_block"
            assert evaluated_count == 1

    def test_off_stage_commits_remain_gated_inside_loop(
        self, ws_enabled, autonomous_enabled, autonomous_pause_loop_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(
            npc_ids=["npc_a"],
            high_motivation=True,
            pacing_min_ms=0,
            max_ticks_per_pause=1,
            visible_npc_ids=[],
            known_actor_ids=["npc_a"],
            known_room_ids=["room_a"],
        )
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            summary = None
            for _ in range(15):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    summary = m["summary"]
                    break
            assert summary is not None
            assert summary["off_stage_update_candidate"]["off_stage_safety_gate_result"] == "pass"
            commit = summary["off_stage_commit_result"]
            assert commit["attempted"] is True
            assert commit["committed"] is False
            assert commit["reason"] == "auto_commit_disabled"


class TestRESTAndBundlePreserved:
    """Stage E must not touch the REST/bundle fallback path."""

    def test_rest_endpoint_still_registered(self, ws_enabled, autonomous_enabled, env_test_mode):
        from app.api import http as http_module
        assert any(
            getattr(r, "path", None) == "/api/story/sessions/{session_id}/turns"
            for r in http_module.router.routes
        )

    def test_envelope_blocks_unchanged_by_autonomous_path(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        """The user-turn ``visible_scene_output.blocks`` is delivered intact regardless
        of whether autonomous ticking is on. Stage E only adds *additional* messages
        after the bundle is delivered; it never rewrites the bundle.
        """
        narrator_event = _stream_event(BLOCK_TYPE_NARRATOR, text="The room hushes.")
        extras = _autonomous_envelope_extras(npc_ids=["npc_a"], high_motivation=True)
        app = _make_app(events=[narrator_event], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            user_started = None
            for _ in range(15):
                m = ws.receive_json()
                if m["kind"] == "block_started":
                    user_started = m
                    break
            assert user_started is not None
            payload = user_started["block_stream_event"]["block_payload"]
            assert payload["text"] == "The room hushes."


# ── Stage F: capability feeding + source classification + off-stage scaffold ─


class TestStageFAutonomousSummaryFields:
    def test_summary_carries_capability_outputs_used_and_missing(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(npc_ids=["npc_a"], high_motivation=True)
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            summary = None
            for _ in range(12):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    summary = m["summary"]
                    break
            assert summary is not None
            assert "capability_outputs_used" in summary
            assert "capability_outputs_missing" in summary
            # scene_energy_output / social_pressure_output were supplied via the
            # canned envelope extras — they must show up as used.
            assert "scene_energy_output" in summary["capability_outputs_used"]
            assert "social_pressure_output" in summary["capability_outputs_used"]

    def test_summary_carries_component_sources_three_tier_vocab(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(npc_ids=["npc_a"], high_motivation=True)
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            sources = None
            for _ in range(12):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    sources = m["summary"].get("motivation_score_component_sources")
                    break
            assert isinstance(sources, dict) and sources
            allowed = {"real_runtime_signal", "module_policy_default", "missing_signal"}
            for value in sources.values():
                assert value in allowed

    def test_summary_off_stage_candidate_present(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(npc_ids=["npc_a"], high_motivation=True)
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            cand = None
            for _ in range(12):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    cand = m["summary"].get("off_stage_update_candidate")
                    break
            assert isinstance(cand, dict)
            assert cand.get("canonical_path_advanced") is False
            assert cand.get("mandatory_beat_consumed") is False
            assert cand.get("off_stage_safety_gate_result") in {
                "pass", "blocked", "not_applicable",
            }
            commit = m["summary"].get("off_stage_commit_result")
            assert isinstance(commit, dict)
            assert commit.get("canonical_path_advanced") is False
            assert commit.get("mandatory_beat_consumed") is False

    def test_off_stage_pass_when_chosen_actor_not_visible(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        """If only the visible set is empty but the chosen actor is in
        known_actor_ids, the off-stage candidate gate passes.
        """
        extras = _autonomous_envelope_extras(
            npc_ids=["npc_a"],
            high_motivation=True,
            visible_npc_ids=[],
            known_actor_ids=["npc_a", "npc_b"],
        )
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            cand = None
            for _ in range(15):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    cand = m["summary"].get("off_stage_update_candidate")
                    break
            assert cand is not None
            assert cand["off_stage_safety_gate_result"] == "pass"
            assert cand["off_stage_update_candidate"] is True
            assert isinstance(cand.get("relationship_update_candidate"), dict)
            assert isinstance(cand.get("memory_update_candidate"), dict)

    def test_off_stage_not_applicable_when_chosen_actor_visible(
        self, ws_enabled, autonomous_enabled, env_test_mode,
    ):
        extras = _autonomous_envelope_extras(
            npc_ids=["npc_a"],
            high_motivation=True,
            visible_npc_ids=["npc_a"],
            known_actor_ids=["npc_a"],
        )
        app = _make_app(events=[_stream_event(BLOCK_TYPE_NARRATOR)], autonomous_envelope_extras=extras)
        client = TestClient(app)
        with client.websocket_connect("/api/story/sessions/sess-1/stream") as ws:
            ws.receive_json()
            ws.send_json({"kind": "start_turn", "player_input": "go"})
            cand = None
            for _ in range(15):
                m = ws.receive_json()
                if m["kind"] == "autonomous_tick_evaluated":
                    cand = m["summary"].get("off_stage_update_candidate")
                    break
            assert cand is not None
            assert cand["off_stage_safety_gate_result"] == "not_applicable"
            assert cand["off_stage_update_candidate"] is False
