"""Closed enums, schema ids, feature flags, and Director Pulse imports."""

from __future__ import annotations

import re
from typing import Any, Callable

from ai_stack.contracts.director_pulse_contracts import (
    ACTION_SILENCE,
    ACTION_SPEAK,
    BLOCK_TYPE_ACTOR_LINE,
    BLOCK_TYPE_NARRATOR,
    CUT_IN_CUT_EM_DASH,
    CUT_IN_CUT_SKIP_TO_END,
    CUT_IN_UNINTERRUPTED,
    CUT_KIND_EM_DASH,
    CUT_KIND_NO_ACTIVE_BLOCK,
    CUT_KIND_SKIP_TO_END,
    CUT_KINDS,
    LANE_VISIBLE_SCENE_OUTPUT,
    TRIGGER_PLAYER_INPUT,
    build_block_stream_event,
    build_director_tick_decision,
    build_player_cut_in_event,
    resolve_cut_kind_for_block_type,
)


SCHEMA_REPLANNING_REQUEST = "replanning_request.v1"


SCHEMA_REPLANNING_DECISION = "replanning_decision.v1"


SCHEMA_PLAYER_CUT_IN_HANDOFF = "player_cut_in_handoff.v1"


SCHEMA_POST_CUT_IN_REPLANNING_DECISION = "post_cut_in_replanning_decision.v1"


SCHEMA_POST_CUT_IN_FOLLOW_UP_EVENT = "post_cut_in_follow_up_event.v1"


REPLANNING_REASON_PLAYER_CUT_IN = "player_cut_in"


REPLANNING_DECISION_PRIORITIZE_PLAYER_INPUT = "prioritize_player_input"


REPLANNING_SCOPE_FUTURE_EVENTS_ONLY = "future_events_only"


NEXT_ACTION_SOURCE_PLAYER_INPUT = "player_input_priority"


NEXT_ACTION_SOURCE_IDLE = "idle"


NEXT_ACTION_SOURCE_NPC_RESPONSE = "npc_response"


NEXT_ACTION_SOURCE_SILENCE = "silence"


NEXT_TURN_TRIGGER_PLAYER_CUT_IN_HANDOFF = "player_cut_in_handoff"


EVENT_GENERATION_REPLANNED_AFTER_CUT_IN = "replanned_after_cut_in"


REPLANNED_SILENCE_REASON_PLAYER_INPUT_PRIORITY = "player_input_priority_replan"


PROOF_LEVEL_LOCAL_ONLY = "local_only"


HANDOFF_STATUS_PROMOTED = "promoted"


HANDOFF_STATUS_NOT_APPLICABLE = "not_applicable"


NON_HANDOFF_REASON_NO_PLAYER_INPUT = "no_promotable_player_input"


POST_CUT_IN_FOLLOW_UP_GENERATION = "post_cut_in_follow_up"


MAX_PROMOTED_INPUT_EXCERPT_CHARS = 240


MAX_COMPOSED_FOLLOW_UP_CHARS = 280


COMPOSITION_MODE_TEMPLATE_RENDER = "template_render"


COMPOSITION_MODE_SEMANTIC_GENERATION = "semantic_generation"


COMPOSITION_MODE_TEMPLATE_FALLBACK_AFTER_SEMANTIC_FAILURE = (
    "template_fallback_after_semantic_failure"
)


COMPOSITION_MODE_NOT_APPLICABLE = "not_applicable"


COMPOSITION_MODES = frozenset({
    COMPOSITION_MODE_TEMPLATE_RENDER,
    COMPOSITION_MODE_SEMANTIC_GENERATION,
    COMPOSITION_MODE_TEMPLATE_FALLBACK_AFTER_SEMANTIC_FAILURE,
    COMPOSITION_MODE_NOT_APPLICABLE,
})


SOURCE_CONTEXT_VOICE_PROFILE = "voice_profile"


SOURCE_CONTEXT_PROMOTED_PLAYER_INPUT = "promoted_player_input"


SOURCE_CONTEXT_INTERRUPTED_BLOCK = "interrupted_block"


SOURCE_CONTEXT_MOTIVATION_SCORE = "motivation_score"


SOURCE_CONTEXT_RELATIONSHIP_STATE = "relationship_state"


SOURCE_CONTEXT_SCENE_ENERGY = "scene_energy"


SOURCE_CONTEXT_SOCIAL_PRESSURE = "social_pressure"


SOURCE_CONTEXT_RECENT_VISIBLE_CONTEXT = "recent_visible_context"


SOURCE_CONTEXT_INFORMATION_DISCLOSURE_TARGET = "information_disclosure_target"


SOURCE_CONTEXTS = frozenset({
    SOURCE_CONTEXT_VOICE_PROFILE,
    SOURCE_CONTEXT_PROMOTED_PLAYER_INPUT,
    SOURCE_CONTEXT_INTERRUPTED_BLOCK,
    SOURCE_CONTEXT_MOTIVATION_SCORE,
    SOURCE_CONTEXT_RELATIONSHIP_STATE,
    SOURCE_CONTEXT_SCENE_ENERGY,
    SOURCE_CONTEXT_SOCIAL_PRESSURE,
    SOURCE_CONTEXT_RECENT_VISIBLE_CONTEXT,
    SOURCE_CONTEXT_INFORMATION_DISCLOSURE_TARGET,
})


SAFETY_GATE_VOICE_FORBIDDEN_MARKERS = "voice_forbidden_markers"


SAFETY_GATE_ACTOR_LANE = "actor_lane"


SAFETY_GATE_LENGTH = "length"


SAFETY_GATE_NO_NEW_PEOPLE = "no_new_people"


SAFETY_GATE_NO_NEW_ROOMS = "no_new_rooms"


SAFETY_GATE_NO_FORBIDDEN_PLOT_FACTS = "no_forbidden_plot_facts"


SAFETY_GATE_INFORMATION_DISCLOSURE = "information_disclosure"


SAFETY_GATES = frozenset({
    SAFETY_GATE_VOICE_FORBIDDEN_MARKERS,
    SAFETY_GATE_ACTOR_LANE,
    SAFETY_GATE_LENGTH,
    SAFETY_GATE_NO_NEW_PEOPLE,
    SAFETY_GATE_NO_NEW_ROOMS,
    SAFETY_GATE_NO_FORBIDDEN_PLOT_FACTS,
    SAFETY_GATE_INFORMATION_DISCLOSURE,
})


SAFETY_GATE_RESULT_PASS = "pass"


SAFETY_GATE_RESULT_REJECT = "reject"


SAFETY_GATE_RESULT_NOT_APPLICABLE = "not_applicable"


PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED = (
    "PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED"
)


_FOLLOW_UP_PROFILE_TEMPLATE_KEYS = (
    "post_cut_in_reply",
    "post_cut_in_response",
    "post_cut_in_response_template",
    "follow_up_reply",
    "follow_up_response",
    "follow_up_response_template",
    "cut_in_reply",
    "cut_in_response",
    "short_reaction",
    "subtext",
)


_FOLLOW_UP_ALLOWED_PLACEHOLDERS = frozenset({
    "actor_id",
    "baseline_tone",
    "current_phase_voice_hint",
    "interrupted_block_id",
    "interrupted_block_type",
    "motivation_score",
    "player_input",
    "promoted_player_input",
    "promoted_player_input_id",
    "voice_hint",
})


_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


PHASE2_WS_SESSION_LOOP_ENABLED = "PHASE2_WS_SESSION_LOOP_ENABLED"


_TRUE_VALUES = frozenset(("1", "true", "yes", "on"))


MSG_STREAM_STARTED = "stream_started"


MSG_BLOCK_STARTED = "block_started"


MSG_BLOCK_COMPLETED = "block_completed"


MSG_BLOCK_CUT = "block_cut"


MSG_STREAM_IDLE = "stream_idle"


MSG_STREAM_ERROR = "stream_error"


MSG_AUTONOMOUS_TICK_EVALUATED = "autonomous_tick_evaluated"


MSG_REPLANNING_DECISION = "replanning_decision"


MSG_PLAYER_CUT_IN_HANDOFF = "player_cut_in_handoff"


MSG_POST_CUT_IN_REPLANNING_DECISION = "post_cut_in_replanning_decision"


MSG_POST_CUT_IN_FOLLOW_UP_EVENT = "post_cut_in_follow_up_event"


SERVER_MSG_KINDS = frozenset({
    MSG_STREAM_STARTED,
    MSG_BLOCK_STARTED,
    MSG_BLOCK_COMPLETED,
    MSG_BLOCK_CUT,
    MSG_STREAM_IDLE,
    MSG_STREAM_ERROR,
    MSG_AUTONOMOUS_TICK_EVALUATED,
    MSG_REPLANNING_DECISION,
    MSG_PLAYER_CUT_IN_HANDOFF,
    MSG_POST_CUT_IN_REPLANNING_DECISION,
    MSG_POST_CUT_IN_FOLLOW_UP_EVENT,
})


CLIENT_MSG_START_TURN = "start_turn"


CLIENT_MSG_CUT_IN = "cut_in"


CLIENT_MSG_PING = "ping"


CLIENT_MSG_KINDS = frozenset({
    CLIENT_MSG_START_TURN,
    CLIENT_MSG_CUT_IN,
    CLIENT_MSG_PING,
})


FollowUpSemanticProvider = Callable[[dict[str, Any]], dict[str, Any]]
