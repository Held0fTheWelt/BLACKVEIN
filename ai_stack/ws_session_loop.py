"""Phase 2 — WebSocket Session Loop helpers.

Pure helpers for the live block-stream session loop (ADR-0058 §"Real-time"):

* ``is_ws_session_loop_enabled()`` — server-side feature flag
* ``WSSessionLoopState`` — per-connection runtime state (active block, cut counts)
* ``apply_cut_in()`` — translate an inbound cut-in into a ``player_cut_in_event.v1``
  plus the resulting cut semantics (which blocks to drop / flush)
* Message builders for the WS protocol (``stream_started``, ``block_started``,
  ``block_completed``, ``block_cut``, ``stream_idle``, ``stream_error``)

This module is intentionally I/O-free. No FastAPI, no asyncio, no socket
handling. The WS endpoint in ``world-engine/app/api/story_ws.py`` orchestrates
the transport; this module owns the semantics.

Hard guarantees (ADR-0058):
* No commit/readiness mutation.
* No ``validation_outcome`` change.
* No Pi/Π keys.
* No hardcoded actor/room IDs.
* Cut semantics are block-type driven via
  ``resolve_cut_kind_for_block_type()``.
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from ai_stack.director.director_pulse_contracts import (
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

# ── Replanning schemas ───────────────────────────────────────────────────────

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

# ── Stage M — composition modes & safety gate vocabulary (closed enums) ──────
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

# Feature flag: semantic generation is opt-in even when a provider is supplied.
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

# ── Feature flag ──────────────────────────────────────────────────────────────

PHASE2_WS_SESSION_LOOP_ENABLED = "PHASE2_WS_SESSION_LOOP_ENABLED"

_TRUE_VALUES = frozenset(("1", "true", "yes", "on"))


def is_ws_session_loop_enabled() -> bool:
    """Return True when the Phase-2 WS session loop is enabled server-side.

    Fail-closed: any unset / unparseable value is treated as disabled.
    """
    raw = os.environ.get(PHASE2_WS_SESSION_LOOP_ENABLED, "false")
    return str(raw or "").strip().lower() in _TRUE_VALUES


def is_follow_up_semantic_composition_enabled() -> bool:
    """Return True iff Stage M semantic NPC follow-up composition is enabled.

    Fail-closed: when the env var is unset/unparseable the dispatcher stays on
    the deterministic template path. A provider is *additionally* required —
    enabling this flag alone does not trigger semantic generation.
    """
    raw = os.environ.get(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "false")
    return str(raw or "").strip().lower() in _TRUE_VALUES


# ── WS message kinds (closed enum) ────────────────────────────────────────────

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


# ── Per-connection state ──────────────────────────────────────────────────────


@dataclass
class WSSessionLoopState:
    """Mutable state for one WS connection's streaming pass.

    A new state is created per ``start_turn`` and discarded when the stream
    ends (or is cut). Persistence across turns lives in the StoryRuntime
    session, not here.
    """

    session_id: str
    active_block_id: str | None = None
    active_block_type: str | None = None
    last_event_id: str | None = None
    cut_in_count: int = 0
    last_player_cut_in_event: dict[str, Any] | None = None
    last_player_cut_in_handoff: dict[str, Any] | None = None
    last_cut_outcome: dict[str, Any] | None = None
    last_cut_kind: str | None = None
    queued_player_inputs: list[dict[str, Any]] = field(default_factory=list)
    completed_event_ids: list[str] = field(default_factory=list)
    started_event_ids: list[str] = field(default_factory=list)
    stream_finished: bool = False

    def mark_block_started(self, event: dict[str, Any]) -> None:
        self.active_block_id = str(event.get("event_id") or "") or None
        block_payload = event.get("block_payload") or {}
        # Prefer payload block_type (LDSS-truth) over the event-level normalised type
        # so the cut semantics match what the player actually sees being rendered.
        bt = (
            block_payload.get("block_type")
            if isinstance(block_payload, dict) and block_payload.get("block_type")
            else event.get("block_type")
        )
        self.active_block_type = str(bt) if bt else None
        self.last_event_id = self.active_block_id
        if self.active_block_id and self.active_block_id not in self.started_event_ids:
            self.started_event_ids.append(self.active_block_id)

    def mark_block_completed(self) -> None:
        if self.active_block_id and self.active_block_id not in self.completed_event_ids:
            self.completed_event_ids.append(self.active_block_id)
        self.active_block_id = None
        self.active_block_type = None

    def mark_stream_idle(self) -> None:
        self.active_block_id = None
        self.active_block_type = None
        self.stream_finished = True


# ── Replanning readiness contracts ───────────────────────────────────────────


def _event_ids(events: list[dict[str, Any]] | None) -> list[str]:
    ids: list[str] = []
    for event in events or []:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("event_id") or "").strip()
        if event_id:
            ids.append(event_id)
    return ids


def build_replanning_request(
    *,
    state: WSSessionLoopState,
    tick_id: str,
    cut_outcome: dict[str, Any],
    pending_events: list[dict[str, Any]] | None = None,
    canceled_autonomous_ticks: int = 0,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a diagnostic request for post-cut future-event replanning.

    The request documents the delivery boundary only. It does not mutate graph
    state, turn validation, readiness, canonical path, mandatory beats, or
    already completed delivery events.
    """
    active_id = str(cut_outcome.get("interrupted_block_id") or "").strip()
    streamed_but_not_committed = (
        [active_id]
        if active_id and active_id not in state.completed_event_ids
        else []
    )
    canceled_ticks = max(0, int(canceled_autonomous_ticks or 0))
    return {
        "schema_version": SCHEMA_REPLANNING_REQUEST,
        "request_id": request_id or str(uuid.uuid4()),
        "tick_id": tick_id,
        "replanning_reason": REPLANNING_REASON_PLAYER_CUT_IN,
        "cut_kind": cut_outcome.get("cut_kind"),
        "player_cut_in_event_id": (
            (cut_outcome.get("player_cut_in_event") or {}).get("cut_in_id")
            if isinstance(cut_outcome.get("player_cut_in_event"), dict)
            else None
        ),
        "interrupted_block_id": cut_outcome.get("interrupted_block_id"),
        "interrupted_block_type": cut_outcome.get("interrupted_block_type"),
        "committed_event_ids": list(state.completed_event_ids),
        "streamed_but_not_committed_event_ids": streamed_but_not_committed,
        "not_yet_started_event_ids": _event_ids(pending_events),
        "canceled_ticks": canceled_ticks,
        "replanning_scope": REPLANNING_SCOPE_FUTURE_EVENTS_ONLY,
        "historical_events_mutated": False,
        "graph_state_mutated_mid_turn": False,
        "validation_outcome_changed": False,
        "commit_or_readiness_changed": False,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": PROOF_LEVEL_LOCAL_ONLY,
    }


def build_replanned_event_after_cut_in(
    *,
    request: dict[str, Any],
    player_input_payload: dict[str, Any] | None,
    tick_id: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Build one replacement event for future-only controlled replanning.

    The event is diagnostic and player-priority oriented. It carries no new
    plot fact and consumes no beat; the queued player input remains the next
    authoritative action source.
    """
    resolved_tick_id = tick_id or str(uuid.uuid4())
    director_decision = build_director_tick_decision(
        trigger_kind=TRIGGER_PLAYER_INPUT,
        triggering_actor_id=None,
        chosen_action_kind=ACTION_SILENCE,
        chosen_actor_id=None,
        composition_inputs=[],
        since_last_tick_ms=None,
        silence_reason=REPLANNED_SILENCE_REASON_PLAYER_INPUT_PRIORITY,
        tick_id=resolved_tick_id,
    )
    replaces_event_ids = list(request.get("not_yet_started_event_ids") or [])
    payload = {
        "id": str(uuid.uuid4()),
        "block_type": BLOCK_TYPE_NARRATOR,
        "text": "",
        "originator": "director_replanning",
        "event_generation": EVENT_GENERATION_REPLANNED_AFTER_CUT_IN,
        "replanning_reason": request.get("replanning_reason"),
        "replanning_request_id": request.get("request_id"),
        "next_action_source": NEXT_ACTION_SOURCE_PLAYER_INPUT,
        "replaces_event_ids": replaces_event_ids,
        "diagnostic_only": True,
        "director_tick_decision": director_decision,
        "player_input_present": bool(player_input_payload),
    }
    event = build_block_stream_event(
        tick_id=resolved_tick_id,
        block_type=BLOCK_TYPE_NARRATOR,
        block_payload=payload,
        cut_in_state=CUT_IN_UNINTERRUPTED,
        lane=LANE_VISIBLE_SCENE_OUTPUT,
        source="director_replanning",
        event_id=event_id,
    )
    event["event_generation"] = EVENT_GENERATION_REPLANNED_AFTER_CUT_IN
    event["replanning_reason"] = request.get("replanning_reason")
    event["next_action_source"] = NEXT_ACTION_SOURCE_PLAYER_INPUT
    event["replaces_event_ids"] = replaces_event_ids
    event["director_tick_decision"] = director_decision
    return event


def build_replanning_decision(
    *,
    request: dict[str, Any],
    player_input_queued: bool = True,
    player_input_payload: dict[str, Any] | None = None,
    replanned_events: list[dict[str, Any]] | None = None,
    decision_id: str | None = None,
) -> dict[str, Any]:
    """Decide the safe Stage-I action for a replanning request.

    Stage I readiness never rewrites existing output and never performs graph
    mutation. The only live decision is to cancel future, not-yet-started
    events/ticks and let the queued player input drive the next turn.
    """
    next_action_source = (
        NEXT_ACTION_SOURCE_PLAYER_INPUT if player_input_queued else NEXT_ACTION_SOURCE_IDLE
    )
    resolved_replanned_events = (
        list(replanned_events)
        if replanned_events is not None
        else (
            [
                build_replanned_event_after_cut_in(
                    request=request,
                    player_input_payload=player_input_payload,
                )
            ]
            if player_input_queued
            else []
        )
    )
    replanned_event_ids = _event_ids(resolved_replanned_events)
    replanned_director_tick_decision = None
    if resolved_replanned_events:
        first_event = resolved_replanned_events[0]
        if isinstance(first_event.get("director_tick_decision"), dict):
            replanned_director_tick_decision = first_event["director_tick_decision"]
        else:
            payload = first_event.get("block_payload")
            if isinstance(payload, dict) and isinstance(payload.get("director_tick_decision"), dict):
                replanned_director_tick_decision = payload["director_tick_decision"]
    return {
        "schema_version": SCHEMA_REPLANNING_DECISION,
        "decision_id": decision_id or str(uuid.uuid4()),
        "request_id": request.get("request_id"),
        "replanning_reason": request.get("replanning_reason"),
        "decision": REPLANNING_DECISION_PRIORITIZE_PLAYER_INPUT,
        "next_action_source": next_action_source,
        "canceled_event_ids": list(request.get("not_yet_started_event_ids") or []),
        "canceled_ticks": int(request.get("canceled_ticks") or 0),
        "replanning_scope": REPLANNING_SCOPE_FUTURE_EVENTS_ONLY,
        "event_generation": EVENT_GENERATION_REPLANNED_AFTER_CUT_IN
        if resolved_replanned_events
        else None,
        "replanned_event_ids": replanned_event_ids,
        "replanned_block_stream_events": resolved_replanned_events,
        "replanned_director_tick_decision": replanned_director_tick_decision,
        "mutates_committed_events": False,
        "graph_state_mutated_mid_turn": False,
        "validation_outcome_changed": False,
        "commit_or_readiness_changed": False,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": PROOF_LEVEL_LOCAL_ONLY,
    }


# ── Player cut-in handoff contracts ─────────────────────────────────────────


def _player_input_text(player_input_payload: dict[str, Any] | None) -> str:
    if not isinstance(player_input_payload, dict):
        return ""
    for key in ("player_input", "text", "utterance"):
        value = player_input_payload.get(key)
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _compact_one_line(text: str, *, limit: int) -> str:
    compact = " ".join(str(text or "").split())
    if limit <= 0 or len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _promoted_player_input_id(player_input_payload: dict[str, Any] | None) -> str:
    if isinstance(player_input_payload, dict):
        for key in ("player_input_id", "input_id", "message_id"):
            value = str(player_input_payload.get(key) or "").strip()
            if value:
                return value
    return str(uuid.uuid4())


def _profile_actor_ids(profile: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for key in ("runtime_actor_id", "actor_id", "character_key", "character_id"):
        value = str(profile.get(key) or "").strip()
        if value:
            ids.add(value)
    return ids


def _voice_profiles_by_actor(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_profiles: Any = None
    for key in ("actor_voice_profiles", "character_voice_profiles", "voice_profiles"):
        candidate = context.get(key)
        if candidate:
            raw_profiles = candidate
            break

    indexed: dict[str, dict[str, Any]] = {}
    if isinstance(raw_profiles, dict):
        for actor_id, profile in raw_profiles.items():
            if not isinstance(profile, dict):
                continue
            profile_copy = dict(profile)
            profile_copy.setdefault("runtime_actor_id", str(actor_id))
            for pid in _profile_actor_ids(profile_copy) or {str(actor_id)}:
                indexed[pid] = profile_copy
    elif isinstance(raw_profiles, list):
        for profile in raw_profiles:
            if not isinstance(profile, dict):
                continue
            for pid in _profile_actor_ids(profile):
                indexed[pid] = dict(profile)
    return indexed


def _string_from_profile_container(
    container: dict[str, Any],
    *,
    prefix: str,
) -> tuple[str, str] | None:
    for key in _FOLLOW_UP_PROFILE_TEMPLATE_KEYS:
        value = container.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip(), f"{prefix}.{key}"
    return None


def _follow_up_template_from_profile(profile: dict[str, Any]) -> tuple[str, str] | None:
    profile_composition = (
        profile.get("follow_up_composition")
        if isinstance(profile.get("follow_up_composition"), dict)
        else {}
    )
    selected = _string_from_profile_container(
        profile_composition,
        prefix="follow_up_composition",
    )
    if selected:
        return selected
    speech_patterns = (
        profile.get("speech_patterns")
        if isinstance(profile.get("speech_patterns"), dict)
        else {}
    )
    selected = _string_from_profile_container(
        speech_patterns,
        prefix="speech_patterns",
    )
    if selected:
        return selected
    return _string_from_profile_container(profile, prefix="voice_profile")


def _motivation_score_for_actor(
    *,
    context: dict[str, Any],
    actor_id: str,
) -> float | None:
    raw_scores = context.get("motivation_scores")
    if not isinstance(raw_scores, dict):
        return None
    raw_score = raw_scores.get(actor_id)
    if isinstance(raw_score, (int, float)):
        return float(raw_score)
    if isinstance(raw_score, dict):
        score = raw_score.get("score")
        if isinstance(score, (int, float)):
            return float(score)
    return None


def _render_follow_up_template(
    *,
    template: str,
    replanning: dict[str, Any],
    profile: dict[str, Any],
    actor_id: str,
    motivation_score: float | None,
) -> tuple[str, list[str], str | None]:
    placeholders = _PLACEHOLDER_RE.findall(template)
    unknown = sorted({
        name for name in placeholders if name not in _FOLLOW_UP_ALLOWED_PLACEHOLDERS
    })
    if unknown:
        return "", [], "unsupported_follow_up_template_placeholder"
    if "{" in _PLACEHOLDER_RE.sub("", template) or "}" in _PLACEHOLDER_RE.sub("", template):
        return "", [], "malformed_follow_up_template"

    promoted_input = (
        replanning.get("promoted_input")
        if isinstance(replanning.get("promoted_input"), dict)
        else {}
    )
    promoted_text = str(promoted_input.get("text_excerpt") or "").strip()
    values = {
        "actor_id": actor_id,
        "baseline_tone": str(profile.get("baseline_tone") or "").strip(),
        "current_phase_voice_hint": str(
            profile.get("current_phase_voice_hint") or ""
        ).strip(),
        "interrupted_block_id": str(replanning.get("interrupted_block_id") or "").strip(),
        "interrupted_block_type": str(
            replanning.get("interrupted_block_type") or ""
        ).strip(),
        "motivation_score": (
            f"{motivation_score:.2f}" if motivation_score is not None else ""
        ),
        "player_input": promoted_text,
        "promoted_player_input": promoted_text,
        "promoted_player_input_id": str(
            promoted_input.get("promoted_player_input_id")
            or replanning.get("promoted_player_input_id")
            or ""
        ).strip(),
        "voice_hint": str(profile.get("current_phase_voice_hint") or "").strip(),
    }
    rendered = template
    for name in sorted(set(placeholders), key=len, reverse=True):
        rendered = rendered.replace("{" + name + "}", values.get(name, ""))
    rendered = _compact_one_line(rendered, limit=MAX_COMPOSED_FOLLOW_UP_CHARS)
    if not rendered:
        return "", sorted(set(placeholders)), "empty_composed_follow_up"
    return rendered, sorted(set(placeholders)), None


# ── Stage M — safety gates, source-context derivation, semantic dispatch ─────


# Provider contract (callable injected by host). The dispatcher passes a fully
# structured request dict; the provider returns either a non-empty ``text``
# under ``success: True``, or an ``error_code`` under ``success: False``. The
# provider is *never* the safety oracle — it produces text only; gates are run
# by this module on the returned text regardless of provider claims.
FollowUpSemanticProvider = Callable[[dict[str, Any]], dict[str, Any]]


def _profile_forbidden_language_markers(profile: dict[str, Any]) -> list[str]:
    """Return the closed-enum list of forbidden language markers for the actor.

    Authored content owns the list (``voice_consistency.forbidden_language_markers``).
    Empty list → gate is ``not_applicable`` (no claim about output content).
    """
    raw = profile.get("forbidden_language_markers") if isinstance(profile, dict) else None
    if isinstance(raw, dict):
        out: list[str] = []
        for value in raw.values():
            if isinstance(value, str) and value.strip():
                out.append(value.strip())
            elif isinstance(value, list):
                out.extend(str(v).strip() for v in value if isinstance(v, str) and v.strip())
        return out
    if isinstance(raw, list):
        return [str(v).strip() for v in raw if isinstance(v, str) and v.strip()]
    return []


def _closed_enum_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if isinstance(v, str) and v.strip()]
    return []


def _context_known_actor_ids(context: dict[str, Any]) -> set[str]:
    return {
        s
        for s in _closed_enum_str_list(context.get("known_actor_ids"))
    }


def _context_ai_forbidden_actor_ids(context: dict[str, Any]) -> set[str]:
    lane_ctx = (
        context.get("actor_lane_context")
        if isinstance(context.get("actor_lane_context"), dict)
        else {}
    )
    direct = _closed_enum_str_list(context.get("ai_forbidden_actor_ids"))
    nested = _closed_enum_str_list(lane_ctx.get("ai_forbidden_actor_ids"))
    forbidden: set[str] = {*direct, *nested}
    human = str(lane_ctx.get("human_actor_id") or context.get("human_actor_id") or "").strip()
    if human:
        forbidden.add(human)
    return forbidden


def _gate_voice_forbidden_markers(text: str, profile: dict[str, Any]) -> tuple[str, str | None]:
    markers = _profile_forbidden_language_markers(profile)
    if not markers:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    lower = text.lower()
    for marker in markers:
        if marker.lower() in lower:
            return SAFETY_GATE_RESULT_REJECT, f"voice_forbidden_marker:{marker}"
    return SAFETY_GATE_RESULT_PASS, None


def _gate_actor_lane(actor_id: str, context: dict[str, Any]) -> tuple[str, str | None]:
    forbidden = _context_ai_forbidden_actor_ids(context)
    if not forbidden:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    if actor_id in forbidden:
        return SAFETY_GATE_RESULT_REJECT, f"actor_lane_forbidden_speaker:{actor_id}"
    return SAFETY_GATE_RESULT_PASS, None


def _gate_length(text: str) -> tuple[str, str | None]:
    if not text:
        return SAFETY_GATE_RESULT_REJECT, "empty_composed_follow_up"
    if len(text) > MAX_COMPOSED_FOLLOW_UP_CHARS:
        return SAFETY_GATE_RESULT_REJECT, "composed_follow_up_exceeds_length_cap"
    return SAFETY_GATE_RESULT_PASS, None


def _contains_any_token(text: str, tokens: list[str]) -> str | None:
    """Closed-enum substring containment, case-insensitive. Returns the first hit."""
    if not tokens:
        return None
    lower = text.lower()
    for token in tokens:
        candidate = token.lower().strip()
        if candidate and candidate in lower:
            return token
    return None


def _gate_no_new_people(
    text: str, context: dict[str, Any], actor_id: str
) -> tuple[str, str | None]:
    forbidden = _closed_enum_str_list(context.get("forbidden_new_person_tokens"))
    if not forbidden:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    hit = _contains_any_token(text, forbidden)
    if hit:
        return SAFETY_GATE_RESULT_REJECT, f"new_person_mentioned:{hit}"
    return SAFETY_GATE_RESULT_PASS, None


def _gate_no_new_rooms(text: str, context: dict[str, Any]) -> tuple[str, str | None]:
    forbidden = _closed_enum_str_list(context.get("forbidden_new_room_tokens"))
    if not forbidden:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    hit = _contains_any_token(text, forbidden)
    if hit:
        return SAFETY_GATE_RESULT_REJECT, f"new_room_mentioned:{hit}"
    return SAFETY_GATE_RESULT_PASS, None


def _gate_no_forbidden_plot_facts(
    text: str, context: dict[str, Any]
) -> tuple[str, str | None]:
    forbidden = _closed_enum_str_list(context.get("forbidden_plot_fact_tokens"))
    if not forbidden:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    hit = _contains_any_token(text, forbidden)
    if hit:
        return SAFETY_GATE_RESULT_REJECT, f"forbidden_plot_fact_mentioned:{hit}"
    return SAFETY_GATE_RESULT_PASS, None


def _gate_information_disclosure(
    text: str, context: dict[str, Any]
) -> tuple[str, str | None]:
    target = (
        context.get("information_disclosure_target")
        if isinstance(context.get("information_disclosure_target"), dict)
        else {}
    )
    if not target:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    withheld_tokens: list[str] = []
    for unit in target.get("withheld_units") or []:
        if isinstance(unit, dict):
            tokens = _closed_enum_str_list(unit.get("forbidden_disclosure_tokens"))
            withheld_tokens.extend(tokens)
    if not withheld_tokens:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    hit = _contains_any_token(text, withheld_tokens)
    if hit:
        return SAFETY_GATE_RESULT_REJECT, f"forbidden_disclosure:{hit}"
    return SAFETY_GATE_RESULT_PASS, None


def _run_safety_gates(
    *,
    text: str,
    actor_id: str,
    profile: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Run every closed-enum safety gate on a candidate follow-up text.

    Each gate returns ``pass`` / ``reject`` / ``not_applicable`` deterministically.
    The whole composition is rejected if *any* gate returns ``reject``.
    """
    gate_calls: list[tuple[str, tuple[str, str | None]]] = [
        (SAFETY_GATE_LENGTH, _gate_length(text)),
        (SAFETY_GATE_ACTOR_LANE, _gate_actor_lane(actor_id, context)),
        (SAFETY_GATE_VOICE_FORBIDDEN_MARKERS, _gate_voice_forbidden_markers(text, profile)),
        (SAFETY_GATE_NO_NEW_PEOPLE, _gate_no_new_people(text, context, actor_id)),
        (SAFETY_GATE_NO_NEW_ROOMS, _gate_no_new_rooms(text, context)),
        (
            SAFETY_GATE_NO_FORBIDDEN_PLOT_FACTS,
            _gate_no_forbidden_plot_facts(text, context),
        ),
        (
            SAFETY_GATE_INFORMATION_DISCLOSURE,
            _gate_information_disclosure(text, context),
        ),
    ]
    decisions: dict[str, str] = {}
    rejected_reason: str | None = None
    for name, (result, reason) in gate_calls:
        decisions[name] = result
        if result == SAFETY_GATE_RESULT_REJECT and rejected_reason is None:
            rejected_reason = reason or f"{name}_rejected"
    return {
        "all_pass": rejected_reason is None,
        "decisions": decisions,
        "rejected_reason": rejected_reason,
    }


def _derive_source_contexts(
    *,
    replanning: dict[str, Any],
    context: dict[str, Any],
    profile_used: bool,
    motivation_score: float | None,
    placeholders_used: list[str] | None = None,
) -> list[str]:
    contexts: set[str] = set()
    placeholders_used = placeholders_used or []
    if profile_used:
        contexts.add(SOURCE_CONTEXT_VOICE_PROFILE)
    promoted = (
        replanning.get("promoted_input")
        if isinstance(replanning.get("promoted_input"), dict)
        else {}
    )
    if str(promoted.get("text_excerpt") or "").strip() or any(
        p in placeholders_used
        for p in ("promoted_player_input", "player_input", "promoted_player_input_id")
    ):
        contexts.add(SOURCE_CONTEXT_PROMOTED_PLAYER_INPUT)
    if str(replanning.get("interrupted_block_id") or "").strip() or any(
        p in placeholders_used
        for p in ("interrupted_block_id", "interrupted_block_type")
    ):
        contexts.add(SOURCE_CONTEXT_INTERRUPTED_BLOCK)
    if motivation_score is not None or "motivation_score" in placeholders_used:
        contexts.add(SOURCE_CONTEXT_MOTIVATION_SCORE)
    if isinstance(context.get("relationship_state_output"), dict) and context.get(
        "relationship_state_output"
    ):
        contexts.add(SOURCE_CONTEXT_RELATIONSHIP_STATE)
    if isinstance(context.get("scene_energy_output"), dict) and context.get(
        "scene_energy_output"
    ):
        contexts.add(SOURCE_CONTEXT_SCENE_ENERGY)
    if isinstance(context.get("social_pressure_output"), dict) and context.get(
        "social_pressure_output"
    ):
        contexts.add(SOURCE_CONTEXT_SOCIAL_PRESSURE)
    if isinstance(context.get("recent_visible_blocks"), list) and context.get(
        "recent_visible_blocks"
    ):
        contexts.add(SOURCE_CONTEXT_RECENT_VISIBLE_CONTEXT)
    if isinstance(context.get("information_disclosure_target"), dict) and context.get(
        "information_disclosure_target"
    ):
        contexts.add(SOURCE_CONTEXT_INFORMATION_DISCLOSURE_TARGET)
    return sorted(contexts)


def _voice_profile_actor_id(profile: dict[str, Any]) -> str | None:
    return (
        profile.get("runtime_actor_id")
        or profile.get("actor_id")
        or profile.get("character_key")
    )


def _compose_template_render_follow_up(
    *,
    replanning: dict[str, Any],
    context: dict[str, Any],
    actor_id: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic template path. Renders an authored template from the
    voice profile and runs every safety gate on the rendered text.
    """
    selected_template = _follow_up_template_from_profile(profile)
    motivation_score = _motivation_score_for_actor(context=context, actor_id=actor_id)
    if selected_template is None:
        return {
            "attempted": True,
            "composed": False,
            "composition_kind": NEXT_ACTION_SOURCE_NPC_RESPONSE,
            "composition_mode": COMPOSITION_MODE_TEMPLATE_RENDER,
            "reason": "voice_profile_follow_up_material_unavailable",
            "voice_profile_used": True,
            "voice_profile_actor_id": _voice_profile_actor_id(profile),
            "voice_profile_source_field": None,
            "input_fields_used": [],
            "motivation_score": motivation_score,
            "source_contexts": _derive_source_contexts(
                replanning=replanning,
                context=context,
                profile_used=True,
                motivation_score=motivation_score,
            ),
            "safety_gate_result": "reject",
            "safety_gate_decisions": {},
            "rejected_reason": "voice_profile_follow_up_material_unavailable",
            "new_people_introduced": False,
            "new_rooms_introduced": False,
            "plot_facts_introduced": False,
            "provider_metadata": None,
        }

    template, source_field = selected_template
    text, placeholders, reason = _render_follow_up_template(
        template=template,
        replanning=replanning,
        profile=profile,
        actor_id=actor_id,
        motivation_score=motivation_score,
    )
    if reason:
        return {
            "attempted": True,
            "composed": False,
            "composition_kind": NEXT_ACTION_SOURCE_NPC_RESPONSE,
            "composition_mode": COMPOSITION_MODE_TEMPLATE_RENDER,
            "reason": reason,
            "voice_profile_used": True,
            "voice_profile_actor_id": _voice_profile_actor_id(profile),
            "voice_profile_source_field": source_field,
            "input_fields_used": placeholders,
            "motivation_score": motivation_score,
            "source_contexts": _derive_source_contexts(
                replanning=replanning,
                context=context,
                profile_used=True,
                motivation_score=motivation_score,
                placeholders_used=placeholders,
            ),
            "safety_gate_result": "reject",
            "safety_gate_decisions": {},
            "rejected_reason": reason,
            "new_people_introduced": False,
            "new_rooms_introduced": False,
            "plot_facts_introduced": False,
            "provider_metadata": None,
        }

    gate_result = _run_safety_gates(
        text=text,
        actor_id=actor_id,
        profile=profile,
        context=context,
    )
    if not gate_result["all_pass"]:
        return {
            "attempted": True,
            "composed": False,
            "composition_kind": NEXT_ACTION_SOURCE_NPC_RESPONSE,
            "composition_mode": COMPOSITION_MODE_TEMPLATE_RENDER,
            "reason": gate_result["rejected_reason"] or "safety_gate_rejected",
            "voice_profile_used": True,
            "voice_profile_actor_id": _voice_profile_actor_id(profile),
            "voice_profile_source_field": source_field,
            "input_fields_used": placeholders,
            "motivation_score": motivation_score,
            "source_contexts": _derive_source_contexts(
                replanning=replanning,
                context=context,
                profile_used=True,
                motivation_score=motivation_score,
                placeholders_used=placeholders,
            ),
            "safety_gate_result": "reject",
            "safety_gate_decisions": gate_result["decisions"],
            "rejected_reason": gate_result["rejected_reason"],
            "new_people_introduced": False,
            "new_rooms_introduced": False,
            "plot_facts_introduced": False,
            "provider_metadata": None,
        }
    return {
        "attempted": True,
        "composed": True,
        "composition_kind": NEXT_ACTION_SOURCE_NPC_RESPONSE,
        "composition_mode": COMPOSITION_MODE_TEMPLATE_RENDER,
        "reason": "composed_from_voice_profile",
        "text": text,
        "voice_profile_used": True,
        "voice_profile_actor_id": _voice_profile_actor_id(profile),
        "voice_profile_source_field": source_field,
        "input_fields_used": placeholders,
        "motivation_score": motivation_score,
        "source_contexts": _derive_source_contexts(
            replanning=replanning,
            context=context,
            profile_used=True,
            motivation_score=motivation_score,
            placeholders_used=placeholders,
        ),
        "safety_gate_result": "pass",
        "safety_gate_decisions": gate_result["decisions"],
        "rejected_reason": None,
        "new_people_introduced": False,
        "new_rooms_introduced": False,
        "plot_facts_introduced": False,
        "provider_metadata": None,
    }


def _build_follow_up_composition_request(
    *,
    replanning: dict[str, Any],
    context: dict[str, Any],
    actor_id: str,
    profile: dict[str, Any],
    motivation_score: float | None,
) -> dict[str, Any]:
    """Structured input handed to the semantic composition provider.

    The provider sees a *projection* of the runtime — never the canonical
    graph. It receives no mutators and no commit handles. The only writable
    thing the provider influences is its returned ``text``.
    """
    promoted = (
        replanning.get("promoted_input")
        if isinstance(replanning.get("promoted_input"), dict)
        else {}
    )
    return {
        "schema_version": "follow_up_composition_request.v1",
        "actor_id": actor_id,
        "voice_profile": dict(profile),
        "promoted_player_input": {
            "text": str(promoted.get("text_excerpt") or "").strip(),
            "promoted_player_input_id": str(
                promoted.get("promoted_player_input_id")
                or replanning.get("promoted_player_input_id")
                or ""
            ).strip(),
        },
        "interrupted_block": {
            "interrupted_block_id": str(replanning.get("interrupted_block_id") or "").strip(),
            "interrupted_block_type": str(
                replanning.get("interrupted_block_type") or ""
            ).strip(),
        },
        "motivation_score": motivation_score,
        "relationship_state": (
            context.get("relationship_state_output")
            if isinstance(context.get("relationship_state_output"), dict)
            else None
        ),
        "scene_energy": (
            context.get("scene_energy_output")
            if isinstance(context.get("scene_energy_output"), dict)
            else None
        ),
        "social_pressure": (
            context.get("social_pressure_output")
            if isinstance(context.get("social_pressure_output"), dict)
            else None
        ),
        "recent_visible_context": (
            list(context.get("recent_visible_blocks"))
            if isinstance(context.get("recent_visible_blocks"), list)
            else []
        ),
        "information_disclosure_target": (
            context.get("information_disclosure_target")
            if isinstance(context.get("information_disclosure_target"), dict)
            else None
        ),
        "max_text_chars": MAX_COMPOSED_FOLLOW_UP_CHARS,
        "voice_forbidden_markers": _profile_forbidden_language_markers(profile),
    }


def _compose_semantic_npc_follow_up(
    *,
    replanning: dict[str, Any],
    context: dict[str, Any],
    actor_id: str,
    profile: dict[str, Any],
    provider: FollowUpSemanticProvider,
) -> dict[str, Any]:
    """Semantic path. Calls the injected provider, then runs every safety gate.

    The provider's claim of success is *advisory*; the gates own the final
    pass/reject decision. The provider never touches state — it just returns
    text or an error code.
    """
    motivation_score = _motivation_score_for_actor(context=context, actor_id=actor_id)
    request = _build_follow_up_composition_request(
        replanning=replanning,
        context=context,
        actor_id=actor_id,
        profile=profile,
        motivation_score=motivation_score,
    )
    source_contexts = _derive_source_contexts(
        replanning=replanning,
        context=context,
        profile_used=True,
        motivation_score=motivation_score,
    )
    try:
        response = provider(request) or {}
    except Exception as exc:  # noqa: BLE001 — provider faults must not crash the loop
        return {
            "attempted": True,
            "composed": False,
            "composition_kind": NEXT_ACTION_SOURCE_NPC_RESPONSE,
            "composition_mode": COMPOSITION_MODE_SEMANTIC_GENERATION,
            "reason": "semantic_provider_exception",
            "voice_profile_used": True,
            "voice_profile_actor_id": _voice_profile_actor_id(profile),
            "voice_profile_source_field": None,
            "input_fields_used": [],
            "motivation_score": motivation_score,
            "source_contexts": source_contexts,
            "safety_gate_result": "not_applicable",
            "safety_gate_decisions": {},
            "rejected_reason": "semantic_provider_exception",
            "new_people_introduced": False,
            "new_rooms_introduced": False,
            "plot_facts_introduced": False,
            "provider_metadata": {"exception_type": type(exc).__name__},
        }
    if not isinstance(response, dict):
        response = {}
    provider_metadata = (
        response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
    )
    if not response.get("success") or not isinstance(response.get("text"), str):
        error_code = str(response.get("error_code") or "semantic_provider_returned_no_text")
        return {
            "attempted": True,
            "composed": False,
            "composition_kind": NEXT_ACTION_SOURCE_NPC_RESPONSE,
            "composition_mode": COMPOSITION_MODE_SEMANTIC_GENERATION,
            "reason": error_code,
            "voice_profile_used": True,
            "voice_profile_actor_id": _voice_profile_actor_id(profile),
            "voice_profile_source_field": None,
            "input_fields_used": [],
            "motivation_score": motivation_score,
            "source_contexts": source_contexts,
            "safety_gate_result": "not_applicable",
            "safety_gate_decisions": {},
            "rejected_reason": error_code,
            "new_people_introduced": False,
            "new_rooms_introduced": False,
            "plot_facts_introduced": False,
            "provider_metadata": dict(provider_metadata),
        }
    candidate_text = _compact_one_line(
        str(response.get("text") or ""), limit=MAX_COMPOSED_FOLLOW_UP_CHARS
    )
    gate_result = _run_safety_gates(
        text=candidate_text,
        actor_id=actor_id,
        profile=profile,
        context=context,
    )
    if not gate_result["all_pass"]:
        return {
            "attempted": True,
            "composed": False,
            "composition_kind": NEXT_ACTION_SOURCE_NPC_RESPONSE,
            "composition_mode": COMPOSITION_MODE_SEMANTIC_GENERATION,
            "reason": gate_result["rejected_reason"] or "semantic_output_safety_gate_rejected",
            "voice_profile_used": True,
            "voice_profile_actor_id": _voice_profile_actor_id(profile),
            "voice_profile_source_field": None,
            "input_fields_used": [],
            "motivation_score": motivation_score,
            "source_contexts": source_contexts,
            "safety_gate_result": "reject",
            "safety_gate_decisions": gate_result["decisions"],
            "rejected_reason": gate_result["rejected_reason"],
            "new_people_introduced": False,
            "new_rooms_introduced": False,
            "plot_facts_introduced": False,
            "provider_metadata": dict(provider_metadata),
        }
    return {
        "attempted": True,
        "composed": True,
        "composition_kind": NEXT_ACTION_SOURCE_NPC_RESPONSE,
        "composition_mode": COMPOSITION_MODE_SEMANTIC_GENERATION,
        "reason": "composed_from_semantic_provider",
        "text": candidate_text,
        "voice_profile_used": True,
        "voice_profile_actor_id": _voice_profile_actor_id(profile),
        "voice_profile_source_field": None,
        "input_fields_used": [],
        "motivation_score": motivation_score,
        "source_contexts": source_contexts,
        "safety_gate_result": "pass",
        "safety_gate_decisions": gate_result["decisions"],
        "rejected_reason": None,
        "new_people_introduced": False,
        "new_rooms_introduced": False,
        "plot_facts_introduced": False,
        "provider_metadata": dict(provider_metadata),
    }


def _compose_npc_follow_up(
    *,
    replanning: dict[str, Any],
    context: dict[str, Any],
    actor_id: str,
    composition_provider: FollowUpSemanticProvider | None = None,
) -> dict[str, Any]:
    """Dispatcher: tries semantic first when enabled + provider available, then
    falls back to the deterministic template path. The voice profile gate is
    the *first* hard prerequisite — without a profile the dispatcher never
    invokes a provider.
    """
    profiles_by_actor = _voice_profiles_by_actor(context)
    profile = profiles_by_actor.get(actor_id)
    if not isinstance(profile, dict):
        return {
            "attempted": True,
            "composed": False,
            "composition_kind": NEXT_ACTION_SOURCE_NPC_RESPONSE,
            "composition_mode": COMPOSITION_MODE_NOT_APPLICABLE,
            "reason": "voice_profile_unavailable",
            "voice_profile_used": False,
            "voice_profile_actor_id": None,
            "voice_profile_source_field": None,
            "input_fields_used": [],
            "motivation_score": None,
            "source_contexts": [],
            "safety_gate_result": "reject",
            "safety_gate_decisions": {},
            "rejected_reason": "voice_profile_unavailable",
            "new_people_introduced": False,
            "new_rooms_introduced": False,
            "plot_facts_introduced": False,
            "provider_metadata": None,
        }

    semantic_enabled = is_follow_up_semantic_composition_enabled()
    semantic_attempted = False
    semantic_result: dict[str, Any] | None = None
    if semantic_enabled and composition_provider is not None:
        semantic_attempted = True
        semantic_result = _compose_semantic_npc_follow_up(
            replanning=replanning,
            context=context,
            actor_id=actor_id,
            profile=profile,
            provider=composition_provider,
        )
        if semantic_result.get("composed"):
            return semantic_result

    template_result = _compose_template_render_follow_up(
        replanning=replanning,
        context=context,
        actor_id=actor_id,
        profile=profile,
    )
    if semantic_attempted:
        # Tag mode so observers can tell "template-was-direct" from
        # "template-after-semantic-failure".
        template_result = dict(template_result)
        template_result["composition_mode"] = (
            COMPOSITION_MODE_TEMPLATE_FALLBACK_AFTER_SEMANTIC_FAILURE
        )
        template_result["semantic_attempt_metadata"] = {
            "composition_mode": COMPOSITION_MODE_SEMANTIC_GENERATION,
            "rejected_reason": (semantic_result or {}).get("rejected_reason"),
            "provider_metadata": (semantic_result or {}).get("provider_metadata"),
            "safety_gate_decisions": (semantic_result or {}).get("safety_gate_decisions") or {},
        }
    return template_result


def _non_composed_result(
    *,
    composition_kind: str,
    reason: str,
    attempted: bool = False,
) -> dict[str, Any]:
    return {
        "attempted": attempted,
        "composed": False,
        "composition_kind": composition_kind,
        "composition_mode": COMPOSITION_MODE_NOT_APPLICABLE,
        "reason": reason,
        "voice_profile_used": False,
        "voice_profile_actor_id": None,
        "voice_profile_source_field": None,
        "input_fields_used": [],
        "motivation_score": None,
        "source_contexts": [],
        "safety_gate_result": "not_applicable" if not attempted else "reject",
        "safety_gate_decisions": {},
        "rejected_reason": None if not attempted else reason,
        "new_people_introduced": False,
        "new_rooms_introduced": False,
        "plot_facts_introduced": False,
        "provider_metadata": None,
    }


def build_player_cut_in_handoff(
    *,
    cut_outcome: dict[str, Any],
    replanning_decision: dict[str, Any] | None = None,
    player_input_payload: dict[str, Any] | None = None,
    handoff_id: str | None = None,
    autonomous_loop_paused: bool = True,
) -> dict[str, Any]:
    """Build the Stage-K immediate handoff diagnostic.

    The handoff is the bridge from a cut/replanning artifact into the next
    Director evaluation. It carries only IDs and invariants; the actual player
    text stays in the existing queued cut-in payload.
    """
    cut_event = (
        cut_outcome.get("player_cut_in_event")
        if isinstance(cut_outcome.get("player_cut_in_event"), dict)
        else {}
    )
    payload = (
        dict(player_input_payload)
        if isinstance(player_input_payload, dict)
        else (
            dict(cut_event.get("player_input_payload"))
            if isinstance(cut_event.get("player_input_payload"), dict)
            else {}
        )
    )
    decision = replanning_decision if isinstance(replanning_decision, dict) else {}
    has_player_input = bool(_player_input_text(payload))
    status = HANDOFF_STATUS_PROMOTED if has_player_input else HANDOFF_STATUS_NOT_APPLICABLE
    return {
        "schema_version": SCHEMA_PLAYER_CUT_IN_HANDOFF,
        "handoff_id": handoff_id or str(uuid.uuid4()),
        "cut_in_id": cut_event.get("cut_in_id"),
        "promoted_player_input_id": (
            _promoted_player_input_id(payload) if has_player_input else None
        ),
        "source_replanning_decision_id": decision.get("decision_id"),
        "next_turn_trigger": NEXT_TURN_TRIGGER_PLAYER_CUT_IN_HANDOFF
        if has_player_input
        else None,
        "autonomous_loop_paused": bool(autonomous_loop_paused and has_player_input),
        "canceled_event_ids": list(decision.get("canceled_event_ids") or []),
        "canceled_ticks": int(decision.get("canceled_ticks") or 0),
        "handoff_status": status,
        "non_handoff_reason": None
        if status == HANDOFF_STATUS_PROMOTED
        else NON_HANDOFF_REASON_NO_PLAYER_INPUT,
        "historical_events_mutated": False,
        "graph_state_mutated_mid_turn": False,
        "validation_outcome_changed": False,
        "commit_or_readiness_changed": False,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": PROOF_LEVEL_LOCAL_ONLY,
    }


def build_post_cut_in_replanning_decision(
    *,
    source_handoff: dict[str, Any],
    cut_outcome: dict[str, Any] | None = None,
    new_director_context: dict[str, Any] | None = None,
    selected_next_action_source: str | None = None,
    selected_next_actor_id: str | None = None,
    selected_next_action_kind: str | None = None,
    candidate_actions: list[dict[str, Any]] | None = None,
    rejected_candidates: list[dict[str, Any]] | None = None,
    silence_reason: str | None = None,
    replanning_id: str | None = None,
) -> dict[str, Any]:
    """Build the Stage-L post-handoff Director reevaluation artifact.

    This is an audit record for a fresh Director read after promoted input.
    It can cancel prior future plans and choose a next action source, but it
    never rewrites committed output or mutates validation/readiness state.
    """
    handoff = source_handoff if isinstance(source_handoff, dict) else {}
    outcome = cut_outcome if isinstance(cut_outcome, dict) else {}
    cut_event = (
        outcome.get("player_cut_in_event")
        if isinstance(outcome.get("player_cut_in_event"), dict)
        else {}
    )
    player_input_payload = (
        cut_event.get("player_input_payload")
        if isinstance(cut_event.get("player_input_payload"), dict)
        else {}
    )
    promoted_text = _player_input_text(player_input_payload)
    request = (
        outcome.get("replanning_request")
        if isinstance(outcome.get("replanning_request"), dict)
        else {}
    )
    canceled_event_ids = list(handoff.get("canceled_event_ids") or [])
    canceled_ticks = int(handoff.get("canceled_ticks") or 0)
    candidates = [
        dict(candidate)
        for candidate in (candidate_actions or [])
        if isinstance(candidate, dict)
    ]
    rejected = [
        dict(candidate)
        for candidate in (rejected_candidates or [])
        if isinstance(candidate, dict)
    ]
    return {
        "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
        "replanning_id": replanning_id or str(uuid.uuid4()),
        "source_handoff_id": handoff.get("handoff_id"),
        "promoted_player_input_id": handoff.get("promoted_player_input_id"),
        "interrupted_block_id": outcome.get("interrupted_block_id"),
        "interrupted_block_type": outcome.get("interrupted_block_type"),
        "cut_kind": outcome.get("cut_kind") or cut_event.get("cut_kind"),
        "prior_plan_canceled": bool(canceled_event_ids or canceled_ticks),
        "canceled_event_ids": canceled_event_ids,
        "canceled_ticks": canceled_ticks,
        "new_director_context": dict(new_director_context or {}),
        "selected_next_action_source": selected_next_action_source or NEXT_ACTION_SOURCE_SILENCE,
        "selected_next_actor_id": selected_next_actor_id,
        "selected_next_action_kind": selected_next_action_kind or ACTION_SILENCE,
        "candidate_actions": candidates,
        "rejected_candidates": rejected,
        "silence_reason": silence_reason,
        "interrupted_context": {
            "interrupted_block_id": outcome.get("interrupted_block_id"),
            "interrupted_block_type": outcome.get("interrupted_block_type"),
            "cut_kind": outcome.get("cut_kind") or cut_event.get("cut_kind"),
            "committed_event_ids": list(request.get("committed_event_ids") or []),
            "streamed_but_not_committed_event_ids": list(
                request.get("streamed_but_not_committed_event_ids") or []
            ),
            "not_yet_started_event_ids": list(
                request.get("not_yet_started_event_ids") or []
            ),
        },
        "promoted_input": {
            "promoted_player_input_id": handoff.get("promoted_player_input_id"),
            "source_handoff_id": handoff.get("handoff_id"),
            "text_present": bool(handoff.get("promoted_player_input_id")),
            "text_excerpt": _compact_one_line(
                promoted_text,
                limit=MAX_PROMOTED_INPUT_EXCERPT_CHARS,
            ),
            "text_length": len(promoted_text),
        },
        "canceled_prior_plan": {
            "prior_plan_canceled": bool(canceled_event_ids or canceled_ticks),
            "canceled_event_ids": canceled_event_ids,
            "canceled_ticks": canceled_ticks,
        },
        "historical_events_mutated": False,
        "graph_state_mutated_mid_turn": False,
        "validation_outcome_changed": False,
        "commit_or_readiness_changed": False,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": PROOF_LEVEL_LOCAL_ONLY,
    }


def build_post_cut_in_follow_up_event(
    *,
    decision: dict[str, Any],
    follow_up_id: str | None = None,
    composition_provider: FollowUpSemanticProvider | None = None,
) -> dict[str, Any]:
    """Build an executable future-only follow-up artifact for Stage L+M.

    A safe NPC response produces a ``block_stream_event.v1`` to append after
    already-planned promoted-input output. Silence produces an explicit
    diagnostic silence event. Unsupported or unsafe selections produce a
    no-follow-up diagnostic with no emitted block.

    Stage M (semantic composition): when ``composition_provider`` is supplied
    and ``PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED`` is on, the dispatcher
    invokes the provider for an NPC reply, runs every safety gate, and either
    accepts the semantic output or falls back to the deterministic template
    path. The composition_mode field on the returned ``composition_result``
    records which path produced the emitted text.
    """
    replanning = decision if isinstance(decision, dict) else {}
    resolved_follow_up_id = follow_up_id or str(uuid.uuid4())
    source = str(replanning.get("selected_next_action_source") or "").strip()
    actor_id = str(replanning.get("selected_next_actor_id") or "").strip() or None
    action_kind = str(replanning.get("selected_next_action_kind") or ACTION_SILENCE).strip()
    context = (
        replanning.get("new_director_context")
        if isinstance(replanning.get("new_director_context"), dict)
        else {}
    )
    known_actor_ids = {
        str(raw)
        for raw in context.get("known_actor_ids") or []
        if isinstance(raw, str) and raw
    }
    block_event: dict[str, Any] | None = None
    silence_reason = replanning.get("silence_reason")
    no_follow_up_reason: str | None = None
    composition_result = _non_composed_result(
        composition_kind=source or "unknown",
        reason="composition_not_attempted",
    )

    if source == NEXT_ACTION_SOURCE_NPC_RESPONSE:
        if not actor_id:
            no_follow_up_reason = "missing_selected_actor_id"
            composition_result = _non_composed_result(
                composition_kind=NEXT_ACTION_SOURCE_NPC_RESPONSE,
                reason=no_follow_up_reason,
                attempted=True,
            )
        elif known_actor_ids and actor_id not in known_actor_ids:
            no_follow_up_reason = "unsafe_unknown_actor"
            composition_result = _non_composed_result(
                composition_kind=NEXT_ACTION_SOURCE_NPC_RESPONSE,
                reason=no_follow_up_reason,
                attempted=True,
            )
        elif action_kind != ACTION_SPEAK:
            no_follow_up_reason = "unsupported_next_action_kind"
            composition_result = _non_composed_result(
                composition_kind=NEXT_ACTION_SOURCE_NPC_RESPONSE,
                reason=no_follow_up_reason,
                attempted=True,
            )
        else:
            composition_result = _compose_npc_follow_up(
                replanning=replanning,
                context=context,
                actor_id=actor_id,
                composition_provider=composition_provider,
            )
            if not composition_result.get("composed"):
                no_follow_up_reason = str(
                    composition_result.get("reason") or "follow_up_composition_rejected"
                )
            else:
                composed_text = str(composition_result.get("text") or "")
                voice_profile_actor_id = composition_result.get("voice_profile_actor_id")
                source_field = composition_result.get("voice_profile_source_field")
                input_fields_used = list(composition_result.get("input_fields_used") or [])
                motivation_score = composition_result.get("motivation_score")
                composition_mode = composition_result.get("composition_mode")
                source_contexts = list(composition_result.get("source_contexts") or [])
                safety_gate_decisions = dict(
                    composition_result.get("safety_gate_decisions") or {}
                )
                provider_metadata = composition_result.get("provider_metadata")
                payload = {
                    "id": str(uuid.uuid4()),
                    "block_type": BLOCK_TYPE_ACTOR_LINE,
                    "actor_id": actor_id,
                    "text": composed_text,
                    "originator": POST_CUT_IN_FOLLOW_UP_GENERATION,
                    "post_cut_in_replanning_id": replanning.get("replanning_id"),
                    "post_cut_in_follow_up_id": resolved_follow_up_id,
                    "selected_next_action_source": source,
                    "selected_next_action_kind": action_kind,
                    "composition_mode": composition_mode,
                    "source_contexts": source_contexts,
                    "safety_gate_decisions": safety_gate_decisions,
                    "provider_metadata": provider_metadata,
                    "voice_profile_used": True,
                    "voice_profile_actor_id": voice_profile_actor_id,
                    "voice_profile_source_field": source_field,
                    "composition_inputs_used": input_fields_used,
                    "motivation_score": motivation_score,
                    "new_people_introduced": False,
                    "new_rooms_introduced": False,
                    "plot_facts_introduced": False,
                }
                block_event = build_block_stream_event(
                    tick_id=str(uuid.uuid4()),
                    block_type=BLOCK_TYPE_ACTOR_LINE,
                    block_payload=payload,
                    cut_in_state=CUT_IN_UNINTERRUPTED,
                    lane=LANE_VISIBLE_SCENE_OUTPUT,
                    source=actor_id,
                )
                block_event["event_generation"] = POST_CUT_IN_FOLLOW_UP_GENERATION
                block_event["post_cut_in_replanning_id"] = replanning.get("replanning_id")
                block_event["post_cut_in_follow_up_id"] = resolved_follow_up_id
    elif source == NEXT_ACTION_SOURCE_SILENCE or action_kind == ACTION_SILENCE:
        silence_reason = silence_reason or "director_chose_silence"
        composition_result = _non_composed_result(
            composition_kind=NEXT_ACTION_SOURCE_SILENCE,
            reason=str(silence_reason),
            attempted=False,
        )
        composition_result["safety_gate_result"] = "pass"
    else:
        no_follow_up_reason = "unsupported_next_action_source"
        composition_result = _non_composed_result(
            composition_kind=source or "unknown",
            reason=no_follow_up_reason,
            attempted=True,
        )

    return {
        "schema_version": SCHEMA_POST_CUT_IN_FOLLOW_UP_EVENT,
        "follow_up_id": resolved_follow_up_id,
        "source_replanning_id": replanning.get("replanning_id"),
        "selected_next_action_source": source or None,
        "selected_next_actor_id": actor_id,
        "selected_next_action_kind": action_kind,
        "emitted_event_id": block_event.get("event_id") if block_event else None,
        "silence_reason": silence_reason if block_event is None else None,
        "no_follow_up_reason": no_follow_up_reason,
        "composition_result": composition_result,
        "block_stream_event": block_event,
        "historical_events_mutated": False,
        "graph_state_mutated_mid_turn": False,
        "validation_outcome_changed": False,
        "commit_or_readiness_changed": False,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": PROOF_LEVEL_LOCAL_ONLY,
    }


# ── Cut-in application ───────────────────────────────────────────────────────


def apply_cut_in(
    state: WSSessionLoopState,
    *,
    tick_id: str,
    player_input_payload: dict[str, Any],
    pending_events: list[dict[str, Any]] | None = None,
    canceled_autonomous_ticks: int = 0,
) -> dict[str, Any]:
    """Apply a player cut-in to the current stream state.

    Returns a dict describing the outcome:

        ``cut_kind``            — one of CUT_KIND_* (em_dash / skip_to_end / no_active_block)
        ``player_cut_in_event`` — a ``player_cut_in_event.v1`` record
        ``interrupted_block_id``    — the active block's event_id (or None)
        ``interrupted_block_type``  — the active block's block_type (or None)
        ``drop_remaining_blocks``   — True when the cut should clear the queue
        ``flush_active_block``      — True when remaining text of active block
                                       should be flushed before stopping
        ``queue_input_for_next_turn``— True when the player input should be
                                       carried into the next Director turn

    Semantics (ADR-0058 §6):

    * ``actor_line`` → ``em_dash``: append "—" to active line, drop the rest
      of the stream, queue input for next turn.
    * ``narrator`` / ``actor_action`` / ``souffleuse`` / ``environment_interaction``
      → ``skip_to_end``: complete active block immediately, drop the rest of
      the stream, queue input for next turn.
    * No active block → ``no_active_block``: queue input for next turn; do
      not touch the (empty) stream.

    Mutates ``state.cut_in_count`` and records ``last_player_cut_in_event``.
    """
    cut_kind = resolve_cut_kind_for_block_type(state.active_block_type)

    cut_event = build_player_cut_in_event(
        tick_id=tick_id,
        interrupted_block_id=state.active_block_id,
        interrupted_block_type=state.active_block_type,
        cut_kind=cut_kind,
        player_input_payload=dict(player_input_payload or {}),
    )

    state.cut_in_count += 1
    state.last_player_cut_in_event = cut_event
    state.last_cut_kind = cut_kind
    if player_input_payload:
        state.queued_player_inputs.append(dict(player_input_payload))

    if cut_kind == CUT_KIND_EM_DASH:
        outcome = {
            "cut_kind": cut_kind,
            "player_cut_in_event": cut_event,
            "interrupted_block_id": state.active_block_id,
            "interrupted_block_type": state.active_block_type,
            "drop_remaining_blocks": True,
            "flush_active_block": False,
            "queue_input_for_next_turn": True,
        }
    elif cut_kind == CUT_KIND_SKIP_TO_END:
        outcome = {
            "cut_kind": cut_kind,
            "player_cut_in_event": cut_event,
            "interrupted_block_id": state.active_block_id,
            "interrupted_block_type": state.active_block_type,
            "drop_remaining_blocks": True,
            "flush_active_block": True,
            "queue_input_for_next_turn": True,
        }
    else:
        # no_active_block: input queues for next turn, no stream impact
        outcome = {
            "cut_kind": CUT_KIND_NO_ACTIVE_BLOCK,
            "player_cut_in_event": cut_event,
            "interrupted_block_id": None,
            "interrupted_block_type": None,
            "drop_remaining_blocks": False,
            "flush_active_block": False,
            "queue_input_for_next_turn": True,
        }

    replanning_request = build_replanning_request(
        state=state,
        tick_id=tick_id,
        cut_outcome=outcome,
        pending_events=pending_events,
        canceled_autonomous_ticks=canceled_autonomous_ticks,
    )
    replanning_decision = build_replanning_decision(
        request=replanning_request,
        player_input_queued=bool(player_input_payload),
        player_input_payload=player_input_payload,
    )
    handoff = build_player_cut_in_handoff(
        cut_outcome=outcome,
        replanning_decision=replanning_decision,
        player_input_payload=player_input_payload,
    )
    outcome["replanning_request"] = replanning_request
    outcome["replanning_decision"] = replanning_decision
    outcome["player_cut_in_handoff"] = handoff
    state.last_player_cut_in_handoff = handoff
    state.last_cut_outcome = outcome

    return outcome


# ── Server → client message builders ─────────────────────────────────────────


def _new_id() -> str:
    return str(uuid.uuid4())


def msg_stream_started(*, session_id: str, turn_id: str | None = None) -> dict[str, Any]:
    return {
        "kind": MSG_STREAM_STARTED,
        "message_id": _new_id(),
        "session_id": session_id,
        "turn_id": turn_id,
    }


def msg_block_started(*, event: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": MSG_BLOCK_STARTED,
        "message_id": _new_id(),
        "event_id": event.get("event_id"),
        "block_type": event.get("block_type"),
        "block_stream_event": event,
    }


def msg_block_completed(*, event_id: str | None) -> dict[str, Any]:
    return {
        "kind": MSG_BLOCK_COMPLETED,
        "message_id": _new_id(),
        "event_id": event_id,
    }


def msg_block_cut(*, cut_outcome: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": MSG_BLOCK_CUT,
        "message_id": _new_id(),
        "event_id": cut_outcome.get("interrupted_block_id"),
        "block_type": cut_outcome.get("interrupted_block_type"),
        "cut_kind": cut_outcome.get("cut_kind"),
        "player_cut_in_event": cut_outcome.get("player_cut_in_event"),
        "drop_remaining_blocks": bool(cut_outcome.get("drop_remaining_blocks")),
        "flush_active_block": bool(cut_outcome.get("flush_active_block")),
        "replanning_request": cut_outcome.get("replanning_request"),
        "replanning_decision": cut_outcome.get("replanning_decision"),
        "player_cut_in_handoff": cut_outcome.get("player_cut_in_handoff"),
    }


def msg_stream_idle(*, reason: str = "completed") -> dict[str, Any]:
    return {
        "kind": MSG_STREAM_IDLE,
        "message_id": _new_id(),
        "reason": reason,
    }


def msg_stream_error(*, reason: str, detail: str | None = None) -> dict[str, Any]:
    return {
        "kind": MSG_STREAM_ERROR,
        "message_id": _new_id(),
        "reason": reason,
        "detail": detail,
    }


def msg_autonomous_tick_evaluated(*, summary: dict[str, Any]) -> dict[str, Any]:
    """One per Director autonomous-tick evaluation (Stage E).

    Always emitted when the autonomous-tick path runs, even when the outcome
    is silence or a suppression. Carries the full diagnostic ``summary``
    block so the client can record motivation scores, cooldown state, and
    the chosen action without parsing the subsequent block_started/idle
    messages.
    """
    return {
        "kind": MSG_AUTONOMOUS_TICK_EVALUATED,
        "message_id": _new_id(),
        "summary": dict(summary or {}),
    }


def msg_replanning_decision(
    *,
    request: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": MSG_REPLANNING_DECISION,
        "message_id": _new_id(),
        "replanning_request": dict(request or {}),
        "replanning_decision": dict(decision or {}),
    }


def msg_player_cut_in_handoff(*, handoff: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": MSG_PLAYER_CUT_IN_HANDOFF,
        "message_id": _new_id(),
        "player_cut_in_handoff": dict(handoff or {}),
    }


def msg_post_cut_in_replanning_decision(*, decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": MSG_POST_CUT_IN_REPLANNING_DECISION,
        "message_id": _new_id(),
        "post_cut_in_replanning_decision": dict(decision or {}),
    }


def msg_post_cut_in_follow_up_event(*, follow_up: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": MSG_POST_CUT_IN_FOLLOW_UP_EVENT,
        "message_id": _new_id(),
        "post_cut_in_follow_up_event": dict(follow_up or {}),
    }


# ── Cut-in-state mapping for block_stream_event annotation ───────────────────


def cut_in_state_for_kind(cut_kind: str) -> str:
    """Map a player cut_kind to the block_stream_event cut_in_state enum."""
    if cut_kind == CUT_KIND_EM_DASH:
        return CUT_IN_CUT_EM_DASH
    if cut_kind == CUT_KIND_SKIP_TO_END:
        return CUT_IN_CUT_SKIP_TO_END
    # no_active_block — block is not actually interrupted
    return "uninterrupted"


__all__ = [
    "PHASE2_WS_SESSION_LOOP_ENABLED",
    "SCHEMA_REPLANNING_REQUEST",
    "SCHEMA_REPLANNING_DECISION",
    "SCHEMA_PLAYER_CUT_IN_HANDOFF",
    "SCHEMA_POST_CUT_IN_REPLANNING_DECISION",
    "SCHEMA_POST_CUT_IN_FOLLOW_UP_EVENT",
    "REPLANNING_REASON_PLAYER_CUT_IN",
    "REPLANNING_DECISION_PRIORITIZE_PLAYER_INPUT",
    "REPLANNING_SCOPE_FUTURE_EVENTS_ONLY",
    "NEXT_ACTION_SOURCE_PLAYER_INPUT",
    "NEXT_ACTION_SOURCE_IDLE",
    "NEXT_ACTION_SOURCE_NPC_RESPONSE",
    "NEXT_ACTION_SOURCE_SILENCE",
    "NEXT_TURN_TRIGGER_PLAYER_CUT_IN_HANDOFF",
    "EVENT_GENERATION_REPLANNED_AFTER_CUT_IN",
    "REPLANNED_SILENCE_REASON_PLAYER_INPUT_PRIORITY",
    "PROOF_LEVEL_LOCAL_ONLY",
    "HANDOFF_STATUS_PROMOTED",
    "HANDOFF_STATUS_NOT_APPLICABLE",
    "NON_HANDOFF_REASON_NO_PLAYER_INPUT",
    "is_ws_session_loop_enabled",
    "MSG_STREAM_STARTED",
    "MSG_BLOCK_STARTED",
    "MSG_BLOCK_COMPLETED",
    "MSG_BLOCK_CUT",
    "MSG_STREAM_IDLE",
    "MSG_STREAM_ERROR",
    "MSG_AUTONOMOUS_TICK_EVALUATED",
    "MSG_REPLANNING_DECISION",
    "MSG_PLAYER_CUT_IN_HANDOFF",
    "MSG_POST_CUT_IN_REPLANNING_DECISION",
    "MSG_POST_CUT_IN_FOLLOW_UP_EVENT",
    "SERVER_MSG_KINDS",
    "CLIENT_MSG_START_TURN",
    "CLIENT_MSG_CUT_IN",
    "CLIENT_MSG_PING",
    "CLIENT_MSG_KINDS",
    "WSSessionLoopState",
    "build_replanning_request",
    "build_replanned_event_after_cut_in",
    "build_replanning_decision",
    "build_player_cut_in_handoff",
    "build_post_cut_in_replanning_decision",
    "build_post_cut_in_follow_up_event",
    "apply_cut_in",
    "msg_stream_started",
    "msg_block_started",
    "msg_block_completed",
    "msg_block_cut",
    "msg_stream_idle",
    "msg_stream_error",
    "msg_autonomous_tick_evaluated",
    "msg_replanning_decision",
    "msg_player_cut_in_handoff",
    "msg_post_cut_in_replanning_decision",
    "msg_post_cut_in_follow_up_event",
    "cut_in_state_for_kind",
]
