"""Phase 2 — WebSocket Session Loop pure-helper tests.

Tests for ai_stack/ws_session_loop.py:
* feature-flag is_ws_session_loop_enabled (fail-closed)
* WSSessionLoopState transitions
* apply_cut_in semantics per block type (em_dash / skip_to_end / no_active_block)
* server → client message builders
* cut_in_state_for_kind mapping

No WebSocket transport in these tests — that lives in
world-engine/tests/test_ws_session_loop_endpoint.py.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest

from ai_stack.story_runtime.director.director_pulse_contracts import (
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
    SCHEMA_DIRECTOR_TICK_DECISION,
    SCHEMA_BLOCK_STREAM_EVENT,
    SCHEMA_PLAYER_CUT_IN_EVENT,
    build_block_stream_event,
)
from ai_stack.ws_session_loop import (
    CLIENT_MSG_CUT_IN,
    CLIENT_MSG_PING,
    CLIENT_MSG_START_TURN,
    COMPOSITION_MODE_NOT_APPLICABLE,
    COMPOSITION_MODE_SEMANTIC_GENERATION,
    COMPOSITION_MODE_TEMPLATE_FALLBACK_AFTER_SEMANTIC_FAILURE,
    COMPOSITION_MODE_TEMPLATE_RENDER,
    COMPOSITION_MODES,
    HANDOFF_STATUS_PROMOTED,
    MSG_PLAYER_CUT_IN_HANDOFF,
    MSG_POST_CUT_IN_FOLLOW_UP_EVENT,
    MSG_POST_CUT_IN_REPLANNING_DECISION,
    MSG_REPLANNING_DECISION,
    MSG_AUTONOMOUS_TICK_EVALUATED,
    MSG_BLOCK_COMPLETED,
    MSG_BLOCK_CUT,
    MSG_BLOCK_STARTED,
    MSG_STREAM_ERROR,
    MSG_STREAM_IDLE,
    MSG_STREAM_STARTED,
    PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED,
    PHASE2_WS_SESSION_LOOP_ENABLED,
    EVENT_GENERATION_REPLANNED_AFTER_CUT_IN,
    NEXT_TURN_TRIGGER_PLAYER_CUT_IN_HANDOFF,
    SAFETY_GATES,
    SAFETY_GATE_ACTOR_LANE,
    SAFETY_GATE_INFORMATION_DISCLOSURE,
    SAFETY_GATE_LENGTH,
    SAFETY_GATE_NO_FORBIDDEN_PLOT_FACTS,
    SAFETY_GATE_NO_NEW_PEOPLE,
    SAFETY_GATE_NO_NEW_ROOMS,
    SAFETY_GATE_RESULT_NOT_APPLICABLE,
    SAFETY_GATE_RESULT_PASS,
    SAFETY_GATE_RESULT_REJECT,
    SAFETY_GATE_VOICE_FORBIDDEN_MARKERS,
    SCHEMA_POST_CUT_IN_FOLLOW_UP_EVENT,
    SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
    SOURCE_CONTEXT_MOTIVATION_SCORE,
    SOURCE_CONTEXT_PROMOTED_PLAYER_INPUT,
    SOURCE_CONTEXT_RELATIONSHIP_STATE,
    SOURCE_CONTEXT_SCENE_ENERGY,
    SOURCE_CONTEXT_SOCIAL_PRESSURE,
    SOURCE_CONTEXT_VOICE_PROFILE,
    SOURCE_CONTEXTS,
    REPLANNED_SILENCE_REASON_PLAYER_INPUT_PRIORITY,
    SCHEMA_PLAYER_CUT_IN_HANDOFF,
    SCHEMA_REPLANNING_DECISION,
    SCHEMA_REPLANNING_REQUEST,
    SERVER_MSG_KINDS,
    WSSessionLoopState,
    apply_cut_in,
    build_replanned_event_after_cut_in,
    build_replanning_decision,
    build_replanning_request,
    build_player_cut_in_handoff,
    build_post_cut_in_follow_up_event,
    build_post_cut_in_replanning_decision,
    cut_in_state_for_kind,
    is_follow_up_semantic_composition_enabled,
    is_ws_session_loop_enabled,
    msg_autonomous_tick_evaluated,
    msg_block_completed,
    msg_block_cut,
    msg_player_cut_in_handoff,
    msg_post_cut_in_follow_up_event,
    msg_post_cut_in_replanning_decision,
    msg_replanning_decision,
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
        assert state.last_player_cut_in_handoff is None
        assert state.last_cut_outcome is None
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


# ── Stage I replanning readiness ─────────────────────────────────────────────


class TestReplanningReadiness:
    def test_cut_in_builds_replanning_request_and_decision(self):
        state = WSSessionLoopState(session_id="s1")
        active = _stream_event(BLOCK_TYPE_ACTOR_LINE)
        future = _stream_event(BLOCK_TYPE_NARRATOR)
        state.mark_block_started(active)

        outcome = apply_cut_in(
            state,
            tick_id=active["tick_id"],
            player_input_payload={"text": "Stop!"},
            pending_events=[future],
            canceled_autonomous_ticks=2,
        )

        request = outcome["replanning_request"]
        decision = outcome["replanning_decision"]
        assert request["schema_version"] == SCHEMA_REPLANNING_REQUEST
        assert decision["schema_version"] == SCHEMA_REPLANNING_DECISION
        assert request["replanning_reason"] == "player_cut_in"
        assert request["streamed_but_not_committed_event_ids"] == [active["event_id"]]
        assert request["not_yet_started_event_ids"] == [future["event_id"]]
        assert request["canceled_ticks"] == 2
        assert decision["next_action_source"] == "player_input_priority"
        assert decision["canceled_event_ids"] == [future["event_id"]]
        assert decision["canceled_ticks"] == 2
        assert decision["event_generation"] == EVENT_GENERATION_REPLANNED_AFTER_CUT_IN
        assert len(decision["replanned_event_ids"]) == 1
        replanned = decision["replanned_block_stream_events"][0]
        assert replanned["schema_version"] == SCHEMA_BLOCK_STREAM_EVENT
        assert replanned["event_generation"] == EVENT_GENERATION_REPLANNED_AFTER_CUT_IN
        assert replanned["event_id"] in decision["replanned_event_ids"]
        assert replanned["event_id"] != future["event_id"]
        assert replanned["replaces_event_ids"] == [future["event_id"]]
        tick_decision = decision["replanned_director_tick_decision"]
        assert tick_decision["schema_version"] == SCHEMA_DIRECTOR_TICK_DECISION
        assert tick_decision["trigger_kind"] == "player_input"
        assert tick_decision["silence_reason"] == REPLANNED_SILENCE_REASON_PLAYER_INPUT_PRIORITY

    def test_committed_delivery_events_remain_outside_replanning_scope(self):
        state = WSSessionLoopState(session_id="s1")
        committed = _stream_event(BLOCK_TYPE_NARRATOR)
        active = _stream_event(BLOCK_TYPE_ACTOR_LINE)
        future = _stream_event(BLOCK_TYPE_NARRATOR)

        state.mark_block_started(committed)
        state.mark_block_completed()
        state.mark_block_started(active)
        outcome = apply_cut_in(
            state,
            tick_id=active["tick_id"],
            player_input_payload={"text": "Wait."},
            pending_events=[future],
        )
        request = outcome["replanning_request"]
        decision = outcome["replanning_decision"]

        assert request["committed_event_ids"] == [committed["event_id"]]
        assert request["streamed_but_not_committed_event_ids"] == [active["event_id"]]
        assert request["historical_events_mutated"] is False
        assert decision["mutates_committed_events"] is False
        assert decision["replanning_scope"] == "future_events_only"
        assert decision["canceled_event_ids"] == [future["event_id"]]
        assert decision["replanned_block_stream_events"][0]["replaces_event_ids"] == [
            future["event_id"]
        ]

    def test_replanning_never_changes_validation_commit_readiness_or_beats(self):
        state = WSSessionLoopState(session_id="s1")
        event = _stream_event(BLOCK_TYPE_NARRATOR)
        state.mark_block_started(event)
        outcome = apply_cut_in(
            state,
            tick_id=event["tick_id"],
            player_input_payload={"text": "No."},
        )
        for artifact in (
            outcome["replanning_request"],
            outcome["replanning_decision"],
        ):
            assert artifact["validation_outcome_changed"] is False
            assert artifact["commit_or_readiness_changed"] is False
            assert artifact["canonical_path_advanced"] is False
            assert artifact["mandatory_beat_consumed"] is False
            assert artifact["graph_state_mutated_mid_turn"] is False

    def test_replanning_builders_can_be_called_directly(self):
        state = WSSessionLoopState(session_id="s1")
        active = _stream_event(BLOCK_TYPE_ACTOR_LINE)
        state.mark_block_started(active)
        cut_outcome = {
            "cut_kind": CUT_KIND_EM_DASH,
            "player_cut_in_event": {"cut_in_id": "cut-1"},
            "interrupted_block_id": active["event_id"],
            "interrupted_block_type": BLOCK_TYPE_ACTOR_LINE,
        }
        request = build_replanning_request(
            state=state,
            tick_id=active["tick_id"],
            cut_outcome=cut_outcome,
            pending_events=[],
        )
        decision = build_replanning_decision(request=request)
        assert request["schema_version"] == SCHEMA_REPLANNING_REQUEST
        assert decision["request_id"] == request["request_id"]
        assert len(decision["replanned_event_ids"]) == 1

    def test_replanned_event_builder_marks_generation_and_player_priority(self):
        state = WSSessionLoopState(session_id="s1")
        active = _stream_event(BLOCK_TYPE_ACTOR_LINE)
        state.mark_block_started(active)
        request = build_replanning_request(
            state=state,
            tick_id=active["tick_id"],
            cut_outcome={
                "cut_kind": CUT_KIND_EM_DASH,
                "player_cut_in_event": {"cut_in_id": "cut-1"},
                "interrupted_block_id": active["event_id"],
                "interrupted_block_type": BLOCK_TYPE_ACTOR_LINE,
            },
            pending_events=[],
        )
        replanned = build_replanned_event_after_cut_in(
            request=request,
            player_input_payload={"text": "Stop"},
        )
        assert replanned["event_generation"] == EVENT_GENERATION_REPLANNED_AFTER_CUT_IN
        assert replanned["next_action_source"] == "player_input_priority"
        assert replanned["block_payload"]["text"] == ""
        assert replanned["block_payload"]["diagnostic_only"] is True
        assert replanned["director_tick_decision"]["trigger_kind"] == "player_input"


# ── Stage K cut-in handoff ───────────────────────────────────────────────────


class TestPlayerCutInHandoff:
    def test_cut_in_builds_handoff_artifact(self):
        state = WSSessionLoopState(session_id="s1")
        active = _stream_event(BLOCK_TYPE_ACTOR_LINE)
        future = _stream_event(BLOCK_TYPE_NARRATOR)
        state.mark_block_started(active)

        outcome = apply_cut_in(
            state,
            tick_id=active["tick_id"],
            player_input_payload={"player_input": "Change course."},
            pending_events=[future],
            canceled_autonomous_ticks=2,
        )

        handoff = outcome["player_cut_in_handoff"]
        assert handoff["schema_version"] == SCHEMA_PLAYER_CUT_IN_HANDOFF
        assert handoff["handoff_status"] == HANDOFF_STATUS_PROMOTED
        assert handoff["cut_in_id"] == outcome["player_cut_in_event"]["cut_in_id"]
        assert handoff["promoted_player_input_id"]
        assert handoff["source_replanning_decision_id"] == outcome["replanning_decision"]["decision_id"]
        assert handoff["next_turn_trigger"] == NEXT_TURN_TRIGGER_PLAYER_CUT_IN_HANDOFF
        assert handoff["autonomous_loop_paused"] is True
        assert handoff["canceled_event_ids"] == [future["event_id"]]
        assert handoff["canceled_ticks"] == 2
        assert handoff["non_handoff_reason"] is None
        assert handoff["historical_events_mutated"] is False
        assert handoff["validation_outcome_changed"] is False
        assert handoff["commit_or_readiness_changed"] is False
        assert handoff["canonical_path_advanced"] is False
        assert handoff["mandatory_beat_consumed"] is False
        assert state.last_player_cut_in_handoff == handoff
        assert state.last_cut_outcome == outcome

    def test_handoff_preserves_existing_player_input_id(self):
        state = WSSessionLoopState(session_id="s1")
        outcome = apply_cut_in(
            state,
            tick_id=_tid(),
            player_input_payload={
                "player_input": "I step in.",
                "player_input_id": "input-123",
            },
        )

        assert outcome["player_cut_in_handoff"]["promoted_player_input_id"] == "input-123"

    def test_handoff_builder_rejects_empty_player_input(self):
        handoff = build_player_cut_in_handoff(
            cut_outcome={
                "player_cut_in_event": {
                    "cut_in_id": "cut-1",
                    "player_input_payload": {"player_input": "   "},
                },
            },
            replanning_decision={
                "decision_id": "decision-1",
                "canceled_event_ids": ["evt-1"],
                "canceled_ticks": 1,
            },
        )

        assert handoff["schema_version"] == SCHEMA_PLAYER_CUT_IN_HANDOFF
        assert handoff["handoff_status"] == "not_applicable"
        assert handoff["promoted_player_input_id"] is None
        assert handoff["next_turn_trigger"] is None
        assert handoff["non_handoff_reason"] == "no_promotable_player_input"
        assert handoff["autonomous_loop_paused"] is False


class TestPostCutInReplanningDecision:
    def test_builder_carries_required_fields_and_invariants(self):
        cut_outcome = {
            "cut_kind": CUT_KIND_EM_DASH,
            "interrupted_block_id": "evt-active",
            "interrupted_block_type": BLOCK_TYPE_ACTOR_LINE,
            "player_cut_in_event": {"cut_in_id": "cut-1", "cut_kind": CUT_KIND_EM_DASH},
            "replanning_request": {
                "committed_event_ids": ["evt-done"],
                "streamed_but_not_committed_event_ids": ["evt-active"],
                "not_yet_started_event_ids": ["evt-future"],
            },
        }
        handoff = {
            "handoff_id": "handoff-1",
            "promoted_player_input_id": "input-1",
            "canceled_event_ids": ["evt-future"],
            "canceled_ticks": 2,
            "handoff_status": HANDOFF_STATUS_PROMOTED,
        }

        decision = build_post_cut_in_replanning_decision(
            source_handoff=handoff,
            cut_outcome=cut_outcome,
            new_director_context={
                "capability_outputs_used": ["scene_energy"],
                "director_tick_context": {"trigger_kind": "player_input"},
            },
            selected_next_action_source="npc_response",
            selected_next_actor_id="npc_a",
            selected_next_action_kind="speak",
            candidate_actions=[
                {"candidate_id": "npc_response:npc_a", "actor_id": "npc_a", "action_kind": "speak"},
                {"candidate_id": "silence", "actor_id": None, "action_kind": "silence"},
            ],
            rejected_candidates=[
                {"candidate_id": "silence", "rejection_reason": "lower_priority_after_cut_in"},
            ],
            silence_reason=None,
            replanning_id="post-1",
        )

        assert decision["schema_version"] == SCHEMA_POST_CUT_IN_REPLANNING_DECISION
        assert decision["replanning_id"] == "post-1"
        assert decision["source_handoff_id"] == "handoff-1"
        assert decision["promoted_player_input_id"] == "input-1"
        assert decision["interrupted_block_id"] == "evt-active"
        assert decision["interrupted_block_type"] == BLOCK_TYPE_ACTOR_LINE
        assert decision["cut_kind"] == CUT_KIND_EM_DASH
        assert decision["prior_plan_canceled"] is True
        assert decision["canceled_event_ids"] == ["evt-future"]
        assert decision["canceled_ticks"] == 2
        assert decision["selected_next_action_source"] == "npc_response"
        assert decision["selected_next_actor_id"] == "npc_a"
        assert decision["selected_next_action_kind"] == "speak"
        assert len(decision["candidate_actions"]) == 2
        assert decision["rejected_candidates"][0]["candidate_id"] == "silence"
        assert decision["interrupted_context"]["committed_event_ids"] == ["evt-done"]
        assert decision["historical_events_mutated"] is False
        assert decision["validation_outcome_changed"] is False
        assert decision["commit_or_readiness_changed"] is False
        assert decision["canonical_path_advanced"] is False
        assert decision["mandatory_beat_consumed"] is False

    def test_builder_supports_silence_decision(self):
        decision = build_post_cut_in_replanning_decision(
            source_handoff={
                "handoff_id": "handoff-2",
                "promoted_player_input_id": "input-2",
            },
            selected_next_action_source="silence",
            selected_next_actor_id=None,
            selected_next_action_kind="silence",
            candidate_actions=[{"candidate_id": "silence", "action_kind": "silence"}],
            rejected_candidates=[],
            silence_reason="no_npc_above_motivation_threshold",
        )

        assert decision["schema_version"] == SCHEMA_POST_CUT_IN_REPLANNING_DECISION
        assert decision["selected_next_action_source"] == "silence"
        assert decision["selected_next_actor_id"] is None
        assert decision["selected_next_action_kind"] == "silence"
        assert decision["silence_reason"] == "no_npc_above_motivation_threshold"
        assert decision["prior_plan_canceled"] is False


_VOICE_PROFILE_NPC_A: dict[str, Any] = {
    "runtime_actor_id": "npc_a",
    "character_key": "npc_a",
    "baseline_tone": "controlled fury",
    "current_phase_voice_hint": "answer the interruption head-on",
    "speech_patterns": {
        "follow_up_reply": "{actor_id}: {promoted_player_input}",
    },
}


def _decision_with_voice_profile(
    *,
    replanning_id: str = "post-1",
    actor_id: str = "npc_a",
    extra_context: dict[str, Any] | None = None,
    promoted_input: dict[str, Any] | None = None,
    interrupted_block_id: str = "evt-active",
    interrupted_block_type: str = BLOCK_TYPE_ACTOR_LINE,
) -> dict[str, Any]:
    """Build a minimal post_cut_in decision that supplies a voice profile."""
    context = {
        "known_actor_ids": [actor_id],
        "actor_voice_profiles": [dict(_VOICE_PROFILE_NPC_A)],
        "motivation_scores": {actor_id: 0.72},
    }
    if extra_context:
        context.update(extra_context)
    return {
        "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
        "replanning_id": replanning_id,
        "selected_next_action_source": "npc_response",
        "selected_next_actor_id": actor_id,
        "selected_next_action_kind": "speak",
        "new_director_context": context,
        "interrupted_block_id": interrupted_block_id,
        "interrupted_block_type": interrupted_block_type,
        "promoted_player_input_id": "input-1",
        "promoted_input": promoted_input or {
            "promoted_player_input_id": "input-1",
            "text_excerpt": "Why are you doing this?",
            "text_length": 22,
            "text_present": True,
        },
    }


class TestPostCutInFollowUpEvent:
    def test_npc_response_builds_block_stream_event(self):
        decision = _decision_with_voice_profile(replanning_id="post-1")

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision,
            follow_up_id="follow-1",
        )

        assert follow_up["schema_version"] == SCHEMA_POST_CUT_IN_FOLLOW_UP_EVENT
        assert follow_up["follow_up_id"] == "follow-1"
        assert follow_up["source_replanning_id"] == "post-1"
        assert follow_up["selected_next_action_source"] == "npc_response"
        assert follow_up["selected_next_actor_id"] == "npc_a"
        assert follow_up["selected_next_action_kind"] == "speak"
        assert follow_up["emitted_event_id"]
        assert follow_up["silence_reason"] is None
        assert follow_up["no_follow_up_reason"] is None
        event = follow_up["block_stream_event"]
        assert event["schema_version"] == SCHEMA_BLOCK_STREAM_EVENT
        assert event["event_id"] == follow_up["emitted_event_id"]
        assert event["block_type"] == BLOCK_TYPE_ACTOR_LINE
        assert event["block_payload"]["actor_id"] == "npc_a"
        assert event["block_payload"]["originator"] == "post_cut_in_follow_up"
        assert follow_up["historical_events_mutated"] is False
        assert follow_up["validation_outcome_changed"] is False
        assert follow_up["commit_or_readiness_changed"] is False
        assert follow_up["canonical_path_advanced"] is False
        assert follow_up["mandatory_beat_consumed"] is False

    def test_npc_response_composes_from_voice_profile_template(self):
        decision = _decision_with_voice_profile()
        follow_up = build_post_cut_in_follow_up_event(decision=decision)
        payload = follow_up["block_stream_event"]["block_payload"]
        composition = follow_up["composition_result"]

        assert payload["voice_profile_used"] is True
        assert payload["voice_profile_actor_id"] == "npc_a"
        assert payload["voice_profile_source_field"] == "speech_patterns.follow_up_reply"
        assert payload["text"] == "npc_a: Why are you doing this?"
        assert payload["motivation_score"] == 0.72
        assert composition["composed"] is True
        assert composition["reason"] == "composed_from_voice_profile"
        assert composition["voice_profile_used"] is True
        assert composition["safety_gate_result"] == "pass"
        assert "promoted_player_input" in composition["input_fields_used"]
        assert "actor_id" in composition["input_fields_used"]

    def test_npc_follow_up_introduces_no_new_people_rooms_or_plot_facts(self):
        decision = _decision_with_voice_profile()
        follow_up = build_post_cut_in_follow_up_event(decision=decision)
        composition = follow_up["composition_result"]
        payload = follow_up["block_stream_event"]["block_payload"]

        assert composition["new_people_introduced"] is False
        assert composition["new_rooms_introduced"] is False
        assert composition["plot_facts_introduced"] is False
        assert payload["new_people_introduced"] is False
        assert payload["new_rooms_introduced"] is False
        assert payload["plot_facts_introduced"] is False

    def test_npc_follow_up_does_not_mutate_history_or_commit_state(self):
        decision = _decision_with_voice_profile()
        follow_up = build_post_cut_in_follow_up_event(decision=decision)

        assert follow_up["historical_events_mutated"] is False
        assert follow_up["graph_state_mutated_mid_turn"] is False
        assert follow_up["validation_outcome_changed"] is False
        assert follow_up["commit_or_readiness_changed"] is False
        assert follow_up["canonical_path_advanced"] is False
        assert follow_up["mandatory_beat_consumed"] is False

    def test_missing_voice_profile_yields_no_follow_up_reason(self):
        decision = {
            "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
            "replanning_id": "post-no-vp",
            "selected_next_action_source": "npc_response",
            "selected_next_actor_id": "npc_a",
            "selected_next_action_kind": "speak",
            "new_director_context": {"known_actor_ids": ["npc_a"]},
        }

        follow_up = build_post_cut_in_follow_up_event(decision=decision)

        assert follow_up["emitted_event_id"] is None
        assert follow_up["block_stream_event"] is None
        assert follow_up["no_follow_up_reason"] == "voice_profile_unavailable"
        composition = follow_up["composition_result"]
        assert composition["composed"] is False
        assert composition["voice_profile_used"] is False
        assert composition["safety_gate_result"] == "reject"

    def test_voice_profile_without_follow_up_material_yields_no_follow_up(self):
        decision = {
            "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
            "replanning_id": "post-no-material",
            "selected_next_action_source": "npc_response",
            "selected_next_actor_id": "npc_a",
            "selected_next_action_kind": "speak",
            "new_director_context": {
                "known_actor_ids": ["npc_a"],
                "actor_voice_profiles": [{
                    "runtime_actor_id": "npc_a",
                    "baseline_tone": "anger",
                    # no follow-up template keys at any nesting level
                }],
            },
        }

        follow_up = build_post_cut_in_follow_up_event(decision=decision)

        assert follow_up["emitted_event_id"] is None
        assert follow_up["no_follow_up_reason"] == "voice_profile_follow_up_material_unavailable"
        composition = follow_up["composition_result"]
        assert composition["voice_profile_used"] is True
        assert composition["composed"] is False

    def test_unknown_placeholder_in_template_is_rejected(self):
        decision = _decision_with_voice_profile(
            extra_context={
                "actor_voice_profiles": [{
                    "runtime_actor_id": "npc_a",
                    "speech_patterns": {"follow_up_reply": "{not_a_real_field}"},
                }],
            },
        )

        follow_up = build_post_cut_in_follow_up_event(decision=decision)

        assert follow_up["emitted_event_id"] is None
        assert follow_up["no_follow_up_reason"] == "unsupported_follow_up_template_placeholder"
        composition = follow_up["composition_result"]
        assert composition["composed"] is False
        assert composition["safety_gate_result"] == "reject"

    def test_silence_composition_result_is_attempted_false_and_passes_gate(self):
        follow_up = build_post_cut_in_follow_up_event(
            decision={
                "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
                "replanning_id": "post-silence",
                "selected_next_action_source": "silence",
                "selected_next_actor_id": None,
                "selected_next_action_kind": "silence",
                "silence_reason": "no_npc_above_motivation_threshold",
            },
        )

        composition = follow_up["composition_result"]
        assert composition["attempted"] is False
        assert composition["composed"] is False
        assert composition["composition_kind"] == "silence"
        assert composition["safety_gate_result"] == "pass"
        assert follow_up["silence_reason"] == "no_npc_above_motivation_threshold"

    def test_unsafe_actor_composition_result_marks_attempted_and_rejected(self):
        follow_up = build_post_cut_in_follow_up_event(
            decision={
                "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
                "replanning_id": "post-unsafe",
                "selected_next_action_source": "npc_response",
                "selected_next_actor_id": "npc_unknown",
                "selected_next_action_kind": "speak",
                "new_director_context": {"known_actor_ids": ["npc_a"]},
            },
        )

        composition = follow_up["composition_result"]
        assert follow_up["no_follow_up_reason"] == "unsafe_unknown_actor"
        assert composition["attempted"] is True
        assert composition["composed"] is False
        assert composition["safety_gate_result"] == "reject"
        assert composition["new_people_introduced"] is False
        assert composition["new_rooms_introduced"] is False
        assert composition["plot_facts_introduced"] is False

    def test_silence_builds_explicit_silence_event(self):
        follow_up = build_post_cut_in_follow_up_event(
            decision={
                "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
                "replanning_id": "post-2",
                "selected_next_action_source": "silence",
                "selected_next_actor_id": None,
                "selected_next_action_kind": "silence",
                "silence_reason": "no_npc_above_motivation_threshold",
            },
        )

        assert follow_up["schema_version"] == SCHEMA_POST_CUT_IN_FOLLOW_UP_EVENT
        assert follow_up["source_replanning_id"] == "post-2"
        assert follow_up["selected_next_action_source"] == "silence"
        assert follow_up["emitted_event_id"] is None
        assert follow_up["block_stream_event"] is None
        assert follow_up["silence_reason"] == "no_npc_above_motivation_threshold"
        assert follow_up["no_follow_up_reason"] is None

    def test_unsafe_npc_response_becomes_no_follow_up(self):
        follow_up = build_post_cut_in_follow_up_event(
            decision={
                "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
                "replanning_id": "post-3",
                "selected_next_action_source": "npc_response",
                "selected_next_actor_id": "npc_unknown",
                "selected_next_action_kind": "speak",
                "new_director_context": {"known_actor_ids": ["npc_a"]},
            },
        )

        assert follow_up["schema_version"] == SCHEMA_POST_CUT_IN_FOLLOW_UP_EVENT
        assert follow_up["emitted_event_id"] is None
        assert follow_up["block_stream_event"] is None
        assert follow_up["no_follow_up_reason"] == "unsafe_unknown_actor"
        assert follow_up["historical_events_mutated"] is False


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
        assert m["replanning_request"]["schema_version"] == SCHEMA_REPLANNING_REQUEST
        assert m["replanning_decision"]["schema_version"] == SCHEMA_REPLANNING_DECISION
        assert m["player_cut_in_handoff"]["schema_version"] == SCHEMA_PLAYER_CUT_IN_HANDOFF
        assert m["player_cut_in_handoff"]["handoff_status"] == HANDOFF_STATUS_PROMOTED

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

    def test_msg_replanning_decision_carries_request_and_decision(self):
        request = {"schema_version": SCHEMA_REPLANNING_REQUEST, "request_id": "r1"}
        decision = {
            "schema_version": SCHEMA_REPLANNING_DECISION,
            "request_id": "r1",
            "next_action_source": "player_input_priority",
        }
        m = msg_replanning_decision(request=request, decision=decision)
        assert m["kind"] == MSG_REPLANNING_DECISION
        assert m["replanning_request"] == request
        assert m["replanning_decision"] == decision

    def test_msg_replanning_decision_kind_in_server_message_set(self):
        assert MSG_REPLANNING_DECISION in SERVER_MSG_KINDS

    def test_msg_player_cut_in_handoff_carries_handoff(self):
        handoff = {
            "schema_version": SCHEMA_PLAYER_CUT_IN_HANDOFF,
            "handoff_id": "h1",
            "handoff_status": HANDOFF_STATUS_PROMOTED,
        }
        m = msg_player_cut_in_handoff(handoff=handoff)
        assert m["kind"] == MSG_PLAYER_CUT_IN_HANDOFF
        assert m["player_cut_in_handoff"] == handoff

    def test_msg_player_cut_in_handoff_kind_in_server_message_set(self):
        assert MSG_PLAYER_CUT_IN_HANDOFF in SERVER_MSG_KINDS

    def test_msg_post_cut_in_replanning_decision_carries_decision(self):
        decision = {
            "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
            "replanning_id": "post-1",
            "selected_next_action_source": "silence",
        }
        m = msg_post_cut_in_replanning_decision(decision=decision)
        assert m["kind"] == MSG_POST_CUT_IN_REPLANNING_DECISION
        assert m["post_cut_in_replanning_decision"] == decision

    def test_msg_post_cut_in_replanning_decision_kind_in_server_message_set(self):
        assert MSG_POST_CUT_IN_REPLANNING_DECISION in SERVER_MSG_KINDS

    def test_msg_post_cut_in_follow_up_event_carries_follow_up(self):
        follow_up = {
            "schema_version": SCHEMA_POST_CUT_IN_FOLLOW_UP_EVENT,
            "follow_up_id": "follow-1",
        }
        m = msg_post_cut_in_follow_up_event(follow_up=follow_up)
        assert m["kind"] == MSG_POST_CUT_IN_FOLLOW_UP_EVENT
        assert m["post_cut_in_follow_up_event"] == follow_up

    def test_msg_post_cut_in_follow_up_event_kind_in_server_message_set(self):
        assert MSG_POST_CUT_IN_FOLLOW_UP_EVENT in SERVER_MSG_KINDS


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

    def test_no_fixed_speaker_routing_terms_in_module_source(self):
        from ai_stack import ws_session_loop

        with open(ws_session_loop.__file__, "r", encoding="utf-8") as fh:
            source = fh.read().lower()
        for term in ("speaker_queue", "round_robin", "turn_order", "fixed_roster"):
            assert term not in source


# ── Stage M — semantic composition modes & safety gates ─────────────────────


class _FakeSemanticProvider:
    """Deterministic test double for the semantic composition provider.

    Records every request and replays canned responses. Never imports the
    real OpenAI adapter — this lets us assert dispatch + safety semantics in
    isolation from any model SDK.
    """

    def __init__(self, response: dict[str, Any], *, raise_exception: bool = False):
        self._response = response
        self._raise = raise_exception
        self.calls: list[dict[str, Any]] = []

    def __call__(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(request)
        if self._raise:
            raise RuntimeError("provider blew up")
        return dict(self._response)


def _decision_with_full_context(
    *,
    actor_id: str = "npc_a",
    follow_up_template: str = "{actor_id}: replying about {promoted_player_input}",
    extra_profile: dict[str, Any] | None = None,
    extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = {
        "runtime_actor_id": actor_id,
        "character_key": actor_id,
        "baseline_tone": "controlled fury",
        "current_phase_voice_hint": "answer the interruption head-on",
        "speech_patterns": {"follow_up_reply": follow_up_template},
    }
    if extra_profile:
        profile.update(extra_profile)
    context: dict[str, Any] = {
        "known_actor_ids": [actor_id],
        "actor_voice_profiles": [profile],
        "motivation_scores": {actor_id: 0.72},
        "scene_energy_output": {"energy_level": "volatile"},
        "social_pressure_output": {"band": "high"},
        "relationship_state_output": {"pair_states": {}},
    }
    if extra_context:
        context.update(extra_context)
    return {
        "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
        "replanning_id": "post-m-1",
        "selected_next_action_source": "npc_response",
        "selected_next_actor_id": actor_id,
        "selected_next_action_kind": "speak",
        "new_director_context": context,
        "interrupted_block_id": "evt-active",
        "interrupted_block_type": BLOCK_TYPE_ACTOR_LINE,
        "promoted_player_input_id": "input-1",
        "promoted_input": {
            "promoted_player_input_id": "input-1",
            "text_excerpt": "Why are you doing this?",
            "text_length": 22,
            "text_present": True,
        },
    }


class TestSemanticCompositionFeatureFlag:
    def test_flag_name_constant(self):
        assert (
            PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED
            == "PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED"
        )

    def test_default_is_off(self, monkeypatch):
        monkeypatch.delenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, raising=False)
        assert is_follow_up_semantic_composition_enabled() is False

    def test_truthy_values_enable(self, monkeypatch):
        for raw in ("1", "true", "TRUE", "yes", "on"):
            monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, raw)
            assert is_follow_up_semantic_composition_enabled() is True

    def test_unparseable_stays_off(self, monkeypatch):
        for raw in ("", "maybe", "0", "false", "off", "no"):
            monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, raw)
            assert is_follow_up_semantic_composition_enabled() is False


class TestCompositionModesClosedEnums:
    def test_modes_are_strings_in_closed_set(self):
        assert COMPOSITION_MODE_TEMPLATE_RENDER in COMPOSITION_MODES
        assert COMPOSITION_MODE_SEMANTIC_GENERATION in COMPOSITION_MODES
        assert COMPOSITION_MODE_TEMPLATE_FALLBACK_AFTER_SEMANTIC_FAILURE in COMPOSITION_MODES
        assert COMPOSITION_MODE_NOT_APPLICABLE in COMPOSITION_MODES
        assert len(COMPOSITION_MODES) == 4

    def test_source_contexts_are_strings_in_closed_set(self):
        for value in (
            SOURCE_CONTEXT_VOICE_PROFILE,
            SOURCE_CONTEXT_PROMOTED_PLAYER_INPUT,
            SOURCE_CONTEXT_MOTIVATION_SCORE,
            SOURCE_CONTEXT_RELATIONSHIP_STATE,
            SOURCE_CONTEXT_SCENE_ENERGY,
            SOURCE_CONTEXT_SOCIAL_PRESSURE,
        ):
            assert value in SOURCE_CONTEXTS

    def test_safety_gate_results_are_three_valued(self):
        assert SAFETY_GATE_RESULT_PASS == "pass"
        assert SAFETY_GATE_RESULT_REJECT == "reject"
        assert SAFETY_GATE_RESULT_NOT_APPLICABLE == "not_applicable"


class TestSemanticCompositionDispatch:
    def test_template_render_when_no_provider_and_flag_off(self, monkeypatch):
        monkeypatch.delenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, raising=False)
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(decision=decision)

        composition = follow_up["composition_result"]
        assert composition["composed"] is True
        assert composition["composition_mode"] == COMPOSITION_MODE_TEMPLATE_RENDER
        payload = follow_up["block_stream_event"]["block_payload"]
        assert payload["composition_mode"] == COMPOSITION_MODE_TEMPLATE_RENDER
        assert payload["provider_metadata"] is None

    def test_template_render_when_flag_on_but_no_provider(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(decision=decision)

        composition = follow_up["composition_result"]
        assert composition["composition_mode"] == COMPOSITION_MODE_TEMPLATE_RENDER
        assert composition["composed"] is True

    def test_template_render_when_provider_supplied_but_flag_off(self, monkeypatch):
        monkeypatch.delenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, raising=False)
        provider = _FakeSemanticProvider(
            {"text": "semantic text", "success": True, "metadata": {"model": "x"}}
        )
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        assert provider.calls == []
        assert follow_up["composition_result"]["composition_mode"] == COMPOSITION_MODE_TEMPLATE_RENDER

    def test_semantic_generation_when_flag_on_and_provider_returns_safe_text(
        self, monkeypatch
    ):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "text": "I will not let you decide for me.",
            "success": True,
            "metadata": {"model": "fake-model", "tokens": 42},
        })
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        assert len(provider.calls) == 1
        request = provider.calls[0]
        assert request["schema_version"] == "follow_up_composition_request.v1"
        assert request["actor_id"] == "npc_a"
        assert request["promoted_player_input"]["text"] == "Why are you doing this?"
        assert request["motivation_score"] == 0.72
        assert request["scene_energy"] == {"energy_level": "volatile"}
        assert request["social_pressure"] == {"band": "high"}
        assert request["relationship_state"] == {"pair_states": {}}
        assert request["voice_profile"]["baseline_tone"] == "controlled fury"

        composition = follow_up["composition_result"]
        assert composition["composed"] is True
        assert composition["composition_mode"] == COMPOSITION_MODE_SEMANTIC_GENERATION
        assert composition["text"] == "I will not let you decide for me."
        assert composition["provider_metadata"] == {"model": "fake-model", "tokens": 42}
        assert SOURCE_CONTEXT_VOICE_PROFILE in composition["source_contexts"]
        assert SOURCE_CONTEXT_PROMOTED_PLAYER_INPUT in composition["source_contexts"]
        assert SOURCE_CONTEXT_MOTIVATION_SCORE in composition["source_contexts"]
        assert SOURCE_CONTEXT_SCENE_ENERGY in composition["source_contexts"]
        assert SOURCE_CONTEXT_SOCIAL_PRESSURE in composition["source_contexts"]

        payload = follow_up["block_stream_event"]["block_payload"]
        assert payload["composition_mode"] == COMPOSITION_MODE_SEMANTIC_GENERATION
        assert payload["provider_metadata"] == {"model": "fake-model", "tokens": 42}
        assert payload["text"] == "I will not let you decide for me."

    def test_semantic_falls_back_to_template_when_provider_returns_failure(
        self, monkeypatch
    ):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "success": False,
            "error_code": "model_timeout",
            "metadata": {"http_status": 504},
        })
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        composition = follow_up["composition_result"]
        assert composition["composed"] is True
        assert (
            composition["composition_mode"]
            == COMPOSITION_MODE_TEMPLATE_FALLBACK_AFTER_SEMANTIC_FAILURE
        )
        # The fallback carries metadata about why semantic failed.
        assert composition["semantic_attempt_metadata"]["rejected_reason"] == "model_timeout"
        assert composition["semantic_attempt_metadata"]["provider_metadata"] == {
            "http_status": 504
        }

    def test_semantic_falls_back_to_template_when_provider_exception(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({}, raise_exception=True)
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        composition = follow_up["composition_result"]
        assert composition["composed"] is True
        assert (
            composition["composition_mode"]
            == COMPOSITION_MODE_TEMPLATE_FALLBACK_AFTER_SEMANTIC_FAILURE
        )
        assert (
            composition["semantic_attempt_metadata"]["rejected_reason"]
            == "semantic_provider_exception"
        )

    def test_semantic_disabled_when_voice_profile_missing(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({"text": "x", "success": True})
        decision = {
            "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
            "replanning_id": "post-no-vp",
            "selected_next_action_source": "npc_response",
            "selected_next_actor_id": "npc_a",
            "selected_next_action_kind": "speak",
            "new_director_context": {"known_actor_ids": ["npc_a"]},
        }

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        assert provider.calls == []  # voice profile gate runs first
        assert follow_up["no_follow_up_reason"] == "voice_profile_unavailable"
        composition = follow_up["composition_result"]
        assert composition["composition_mode"] == COMPOSITION_MODE_NOT_APPLICABLE


class TestSemanticCompositionSafetyGates:
    def test_voice_forbidden_marker_in_semantic_text_falls_back_to_template(
        self, monkeypatch
    ):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "text": "I disagree, and frankly NEVERMIND about this.",
            "success": True,
            "metadata": {},
        })
        decision = _decision_with_full_context(
            extra_profile={"forbidden_language_markers": ["NEVERMIND"]},
        )

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        composition = follow_up["composition_result"]
        # Semantic text rejected by voice marker gate → fallback used.
        assert composition["composed"] is True
        assert (
            composition["composition_mode"]
            == COMPOSITION_MODE_TEMPLATE_FALLBACK_AFTER_SEMANTIC_FAILURE
        )
        rejected_reason = composition["semantic_attempt_metadata"]["rejected_reason"]
        assert rejected_reason is not None and "NEVERMIND" in rejected_reason
        gates = composition["semantic_attempt_metadata"]["safety_gate_decisions"]
        assert gates[SAFETY_GATE_VOICE_FORBIDDEN_MARKERS] == SAFETY_GATE_RESULT_REJECT

    def test_actor_lane_gate_rejects_when_speaker_is_ai_forbidden(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "text": "I refuse to apologize.",
            "success": True,
            "metadata": {},
        })
        # Speaker actor is also flagged as ai_forbidden in the lane context.
        # The check is fully closed-enum: no whitelists, just the actor-lane
        # context we were given.
        decision = _decision_with_full_context(
            extra_context={
                "actor_lane_context": {
                    "ai_forbidden_actor_ids": ["npc_a"],
                    "human_actor_id": "human_b",
                },
            },
        )

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        composition = follow_up["composition_result"]
        # Both semantic and template paths reject (gate runs on both texts);
        # final result is no_follow_up with an actor_lane reason.
        assert follow_up["no_follow_up_reason"] is not None
        assert "actor_lane_forbidden_speaker" in follow_up["no_follow_up_reason"]
        # Composition mode reflects the last (template) attempt, tagged as fallback.
        assert (
            composition["composition_mode"]
            == COMPOSITION_MODE_TEMPLATE_FALLBACK_AFTER_SEMANTIC_FAILURE
        )

    def test_no_new_people_gate_rejects_semantic_text_with_forbidden_token(
        self, monkeypatch
    ):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "text": "Maybe Sergeant Hawthorne can settle this.",
            "success": True,
            "metadata": {},
        })
        decision = _decision_with_full_context(
            extra_context={"forbidden_new_person_tokens": ["Sergeant Hawthorne"]},
        )

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        composition = follow_up["composition_result"]
        gates = composition["semantic_attempt_metadata"]["safety_gate_decisions"]
        assert gates[SAFETY_GATE_NO_NEW_PEOPLE] == SAFETY_GATE_RESULT_REJECT
        # Fell back to template (which doesn't mention Hawthorne).
        assert composition["composed"] is True
        assert (
            composition["composition_mode"]
            == COMPOSITION_MODE_TEMPLATE_FALLBACK_AFTER_SEMANTIC_FAILURE
        )

    def test_no_new_rooms_gate_rejects_semantic_text_with_forbidden_room(
        self, monkeypatch
    ):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "text": "Let's continue this in the rooftop terrace.",
            "success": True,
            "metadata": {},
        })
        decision = _decision_with_full_context(
            extra_context={"forbidden_new_room_tokens": ["rooftop terrace"]},
        )

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        composition = follow_up["composition_result"]
        gates = composition["semantic_attempt_metadata"]["safety_gate_decisions"]
        assert gates[SAFETY_GATE_NO_NEW_ROOMS] == SAFETY_GATE_RESULT_REJECT

    def test_no_forbidden_plot_facts_gate_rejects_semantic_text(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "text": "You know I poisoned him last Christmas.",
            "success": True,
            "metadata": {},
        })
        decision = _decision_with_full_context(
            extra_context={"forbidden_plot_fact_tokens": ["poisoned him"]},
        )

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        composition = follow_up["composition_result"]
        gates = composition["semantic_attempt_metadata"]["safety_gate_decisions"]
        assert gates[SAFETY_GATE_NO_FORBIDDEN_PLOT_FACTS] == SAFETY_GATE_RESULT_REJECT

    def test_information_disclosure_gate_rejects_withheld_unit_token(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "text": "The combination is 4729.",
            "success": True,
            "metadata": {},
        })
        decision = _decision_with_full_context(
            extra_context={
                "information_disclosure_target": {
                    "withheld_units": [
                        {"unit_id": "safe_code", "forbidden_disclosure_tokens": ["4729"]}
                    ],
                }
            },
        )

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        composition = follow_up["composition_result"]
        gates = composition["semantic_attempt_metadata"]["safety_gate_decisions"]
        assert gates[SAFETY_GATE_INFORMATION_DISCLOSURE] == SAFETY_GATE_RESULT_REJECT

    def test_length_gate_rejects_oversize_semantic_output(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        # Even after the compact-one-line cap, the dispatcher truncates to
        # MAX_COMPOSED_FOLLOW_UP_CHARS *before* gating. So we exercise the
        # empty-text branch instead, which the length gate also catches.
        provider = _FakeSemanticProvider({
            "text": "",
            "success": True,
            "metadata": {},
        })
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        composition = follow_up["composition_result"]
        gates = composition["semantic_attempt_metadata"]["safety_gate_decisions"]
        assert gates[SAFETY_GATE_LENGTH] == SAFETY_GATE_RESULT_REJECT

    def test_safety_gates_are_not_applicable_when_no_policy_provided(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "text": "A plain reply that mentions nothing special.",
            "success": True,
            "metadata": {},
        })
        decision = _decision_with_full_context()  # no forbidden tokens or markers

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        composition = follow_up["composition_result"]
        assert composition["composed"] is True
        gates = composition["safety_gate_decisions"]
        assert gates[SAFETY_GATE_VOICE_FORBIDDEN_MARKERS] == SAFETY_GATE_RESULT_NOT_APPLICABLE
        assert gates[SAFETY_GATE_NO_NEW_PEOPLE] == SAFETY_GATE_RESULT_NOT_APPLICABLE
        assert gates[SAFETY_GATE_NO_NEW_ROOMS] == SAFETY_GATE_RESULT_NOT_APPLICABLE
        assert gates[SAFETY_GATE_NO_FORBIDDEN_PLOT_FACTS] == SAFETY_GATE_RESULT_NOT_APPLICABLE
        assert gates[SAFETY_GATE_INFORMATION_DISCLOSURE] == SAFETY_GATE_RESULT_NOT_APPLICABLE
        assert gates[SAFETY_GATE_LENGTH] == SAFETY_GATE_RESULT_PASS


class TestSemanticCompositionInvariants:
    def test_semantic_mode_preserves_history_and_commit_invariants(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "text": "Reasonable in-character response.",
            "success": True,
            "metadata": {"model": "fake"},
        })
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        assert follow_up["historical_events_mutated"] is False
        assert follow_up["graph_state_mutated_mid_turn"] is False
        assert follow_up["validation_outcome_changed"] is False
        assert follow_up["commit_or_readiness_changed"] is False
        assert follow_up["canonical_path_advanced"] is False
        assert follow_up["mandatory_beat_consumed"] is False
        composition = follow_up["composition_result"]
        assert composition["new_people_introduced"] is False
        assert composition["new_rooms_introduced"] is False
        assert composition["plot_facts_introduced"] is False
        payload = follow_up["block_stream_event"]["block_payload"]
        assert payload["new_people_introduced"] is False
        assert payload["new_rooms_introduced"] is False
        assert payload["plot_facts_introduced"] is False

    def test_fallback_mode_preserves_history_and_commit_invariants(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({"success": False, "error_code": "x"})
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        assert follow_up["historical_events_mutated"] is False
        assert follow_up["validation_outcome_changed"] is False
        assert follow_up["commit_or_readiness_changed"] is False

    def test_no_provider_call_for_silence_source(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({"text": "x", "success": True})

        follow_up = build_post_cut_in_follow_up_event(
            decision={
                "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
                "replanning_id": "post-silence",
                "selected_next_action_source": "silence",
                "selected_next_actor_id": None,
                "selected_next_action_kind": "silence",
                "silence_reason": "no_npc_above_motivation_threshold",
            },
            composition_provider=provider,
        )

        assert provider.calls == []
        assert follow_up["composition_result"]["composition_mode"] == COMPOSITION_MODE_NOT_APPLICABLE


class TestSemanticCompositionDiagnostics:
    def test_source_contexts_listed_for_template_render(self, monkeypatch):
        monkeypatch.delenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, raising=False)
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(decision=decision)

        composition = follow_up["composition_result"]
        assert SOURCE_CONTEXT_VOICE_PROFILE in composition["source_contexts"]
        assert SOURCE_CONTEXT_PROMOTED_PLAYER_INPUT in composition["source_contexts"]
        # Template uses motivation_score placeholder? Only if template references it.
        # Our test template doesn't, so motivation_score is *available* but not
        # listed unless either the placeholder or context-side surface exists.
        # The score is in context, so the derivation includes it.
        assert SOURCE_CONTEXT_MOTIVATION_SCORE in composition["source_contexts"]
        # Scene-energy / social-pressure live in context only when configured.
        assert SOURCE_CONTEXT_SCENE_ENERGY in composition["source_contexts"]
        assert SOURCE_CONTEXT_SOCIAL_PRESSURE in composition["source_contexts"]
        assert SOURCE_CONTEXT_RELATIONSHIP_STATE in composition["source_contexts"]

    def test_safety_gate_decisions_propagate_to_payload(self, monkeypatch):
        monkeypatch.delenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, raising=False)
        decision = _decision_with_full_context(
            extra_profile={"forbidden_language_markers": ["foobar"]},
        )

        follow_up = build_post_cut_in_follow_up_event(decision=decision)

        payload = follow_up["block_stream_event"]["block_payload"]
        assert payload["safety_gate_decisions"][SAFETY_GATE_VOICE_FORBIDDEN_MARKERS] == "pass"
        assert SAFETY_GATE_LENGTH in payload["safety_gate_decisions"]

    def test_composition_mode_in_payload_matches_result(self, monkeypatch):
        monkeypatch.setenv(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "true")
        provider = _FakeSemanticProvider({
            "text": "Direct semantic reply.",
            "success": True,
            "metadata": {"model": "fake"},
        })
        decision = _decision_with_full_context()

        follow_up = build_post_cut_in_follow_up_event(
            decision=decision, composition_provider=provider
        )

        payload = follow_up["block_stream_event"]["block_payload"]
        assert (
            payload["composition_mode"]
            == follow_up["composition_result"]["composition_mode"]
            == COMPOSITION_MODE_SEMANTIC_GENERATION
        )
