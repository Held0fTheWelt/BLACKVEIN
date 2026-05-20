"""Phase-2 Pulse-MVP runtime contracts.

Four bounded contracts for the Director-Pulse shadow path:

* ``director_tick_decision.v1`` — one per tick (silence ticks included)
* ``block_stream_event.v1`` — one block = one event, never a bundle
* ``npc_motivation_score.v1`` — one per NPC per tick evaluation
* ``player_cut_in_event.v1`` — one per player cut-in event

Governance:
* ADR-0058 — Director-Driven Pulse and Block-Stream-Bus
* ADR-0059 — Semantic NPC Motivation Score
* ADR-0060 — Souffleuse Inner Voice Composition
* ADR-0039 — Gate tests: no hardcoded oracle bypass; no Pi/Π runtime keys

Vocabulary discipline (ADR-0039):
* Closed enums for all discriminated-union fields.
* ``composition_inputs`` uses semantic runtime names only; no Pi/Π-numbered keys.
* No actor ID, room ID, verb, or action whitelists.
* All builder functions are pure — no I/O, no mutation, no LLM call.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

# ── Schema versions ───────────────────────────────────────────────────────────

SCHEMA_DIRECTOR_TICK_DECISION: Final[str] = "director_tick_decision.v1"
SCHEMA_BLOCK_STREAM_EVENT: Final[str] = "block_stream_event.v1"
SCHEMA_NPC_MOTIVATION_SCORE: Final[str] = "npc_motivation_score.v1"
SCHEMA_PLAYER_CUT_IN_EVENT: Final[str] = "player_cut_in_event.v1"

# ── Trigger kinds (director_tick_decision.trigger_kind) ───────────────────────

TRIGGER_PLAYER_INPUT: Final[str] = "player_input"
TRIGGER_MOTIVATION_THRESHOLD_CROSSED: Final[str] = "motivation_threshold_crossed"
TRIGGER_STATE_CHANGE: Final[str] = "state_change"
TRIGGER_COOLDOWN_CHECK: Final[str] = "cooldown_check"

TRIGGER_KINDS: Final[frozenset[str]] = frozenset({
    TRIGGER_PLAYER_INPUT,
    TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
    TRIGGER_STATE_CHANGE,
    TRIGGER_COOLDOWN_CHECK,
})

# ── Action kinds (director_tick_decision.chosen_action_kind) ──────────────────

ACTION_SPEAK: Final[str] = "speak"
ACTION_GESTURE: Final[str] = "gesture"
ACTION_LOCAL_MUNDANE_ACTION: Final[str] = "local_mundane_action"
ACTION_FOLLOW: Final[str] = "follow"
ACTION_REACT_LOCALLY: Final[str] = "react_locally"
ACTION_SILENCE: Final[str] = "silence"

ACTION_KINDS: Final[frozenset[str]] = frozenset({
    ACTION_SPEAK,
    ACTION_GESTURE,
    ACTION_LOCAL_MUNDANE_ACTION,
    ACTION_FOLLOW,
    ACTION_REACT_LOCALLY,
    ACTION_SILENCE,
})

# ── Block types (block_stream_event.block_type) ───────────────────────────────

BLOCK_TYPE_NARRATOR: Final[str] = "narrator"
BLOCK_TYPE_ACTOR_LINE: Final[str] = "actor_line"
BLOCK_TYPE_ACTOR_ACTION: Final[str] = "actor_action"
BLOCK_TYPE_ENVIRONMENT_INTERACTION: Final[str] = "environment_interaction"
BLOCK_TYPE_SOUFFLEUSE: Final[str] = "souffleuse"

BLOCK_STREAM_TYPES: Final[frozenset[str]] = frozenset({
    BLOCK_TYPE_NARRATOR,
    BLOCK_TYPE_ACTOR_LINE,
    BLOCK_TYPE_ACTOR_ACTION,
    BLOCK_TYPE_ENVIRONMENT_INTERACTION,
    BLOCK_TYPE_SOUFFLEUSE,
})

# ── Cut-in states (block_stream_event.cut_in_state) ───────────────────────────

CUT_IN_UNINTERRUPTED: Final[str] = "uninterrupted"
CUT_IN_CUT_EM_DASH: Final[str] = "cut_em_dash"
CUT_IN_CUT_SKIP_TO_END: Final[str] = "cut_skip_to_end"

CUT_IN_STATES: Final[frozenset[str]] = frozenset({
    CUT_IN_UNINTERRUPTED,
    CUT_IN_CUT_EM_DASH,
    CUT_IN_CUT_SKIP_TO_END,
})

# ── Lanes (block_stream_event.lane) ──────────────────────────────────────────

LANE_VISIBLE_SCENE_OUTPUT: Final[str] = "visible_scene_output"
LANE_PLAYER_HINT: Final[str] = "player_hint"

LANES: Final[frozenset[str]] = frozenset({
    LANE_VISIBLE_SCENE_OUTPUT,
    LANE_PLAYER_HINT,
})

# ── Cut kinds (player_cut_in_event.cut_kind) ──────────────────────────────────

CUT_KIND_EM_DASH: Final[str] = "em_dash"
CUT_KIND_SKIP_TO_END: Final[str] = "skip_to_end"
CUT_KIND_NO_ACTIVE_BLOCK: Final[str] = "no_active_block"

CUT_KINDS: Final[frozenset[str]] = frozenset({
    CUT_KIND_EM_DASH,
    CUT_KIND_SKIP_TO_END,
    CUT_KIND_NO_ACTIVE_BLOCK,
})

# ── Cut-in semantics per block type (ADR-0058 §6) ────────────────────────────
# actor_line  → em_dash      (append "—" to current line; player takes next)
# narrator    → skip_to_end  (block finishes; player takes next)
# actor_action → skip_to_end
# souffleuse  → skip_to_end
# environment_interaction → skip_to_end
# None (no active block) → no_active_block

CUT_IN_SEMANTICS_BY_BLOCK_TYPE: Final[dict[str | None, str]] = {
    BLOCK_TYPE_ACTOR_LINE: CUT_KIND_EM_DASH,
    BLOCK_TYPE_NARRATOR: CUT_KIND_SKIP_TO_END,
    BLOCK_TYPE_ACTOR_ACTION: CUT_KIND_SKIP_TO_END,
    BLOCK_TYPE_SOUFFLEUSE: CUT_KIND_SKIP_TO_END,
    BLOCK_TYPE_ENVIRONMENT_INTERACTION: CUT_KIND_SKIP_TO_END,
    None: CUT_KIND_NO_ACTIVE_BLOCK,
}

# ── Semantic capability names used in composition_inputs ─────────────────────
# These are the runtime-level semantic names that appear in director_tick_decision.
# No Pi/Π-numbered runtime keys. ADR-0039 enforced by tests.

CAPABILITY_NAME_SCENE_ENERGY: Final[str] = "scene_energy"
CAPABILITY_NAME_SOCIAL_PRESSURE: Final[str] = "social_pressure"
CAPABILITY_NAME_RELATIONSHIP_DYNAMICS: Final[str] = "relationship_dynamics"
CAPABILITY_NAME_NARRATIVE_MOMENTUM: Final[str] = "narrative_momentum"
CAPABILITY_NAME_ACTOR_PRESSURE_PROFILES: Final[str] = "actor_pressure_profiles"
CAPABILITY_NAME_INTERACTION_PATTERNS: Final[str] = "interaction_patterns"
CAPABILITY_NAME_PACING_RHYTHM: Final[str] = "pacing_rhythm"

PULSE_COMPOSITION_INPUTS: Final[frozenset[str]] = frozenset({
    CAPABILITY_NAME_SCENE_ENERGY,
    CAPABILITY_NAME_SOCIAL_PRESSURE,
    CAPABILITY_NAME_RELATIONSHIP_DYNAMICS,
    CAPABILITY_NAME_NARRATIVE_MOMENTUM,
    CAPABILITY_NAME_ACTOR_PRESSURE_PROFILES,
    CAPABILITY_NAME_INTERACTION_PATTERNS,
    CAPABILITY_NAME_PACING_RHYTHM,
})


def _new_id() -> str:
    return str(uuid.uuid4())


def resolve_cut_kind_for_block_type(block_type: str | None) -> str:
    """Return the cut kind for the given active block type.

    Semantics are block-type-dependent (ADR-0058 §6). No actor, room, or
    verb influences this decision.
    """
    return CUT_IN_SEMANTICS_BY_BLOCK_TYPE.get(block_type, CUT_KIND_SKIP_TO_END)


def build_director_tick_decision(
    *,
    trigger_kind: str,
    triggering_actor_id: str | None,
    chosen_action_kind: str,
    chosen_actor_id: str | None,
    composition_inputs: list[str],
    since_last_tick_ms: float | None,
    silence_reason: str | None = None,
    tick_id: str | None = None,
) -> dict[str, Any]:
    """Build a ``director_tick_decision.v1`` snapshot.

    Pure function. One snapshot per tick. Silence ticks also produce a record
    with ``chosen_actor_id: null`` and ``silence_reason`` populated.
    """
    if trigger_kind not in TRIGGER_KINDS:
        raise ValueError(
            f"Invalid trigger_kind: {trigger_kind!r}. "
            f"Must be one of {sorted(TRIGGER_KINDS)}"
        )
    if chosen_action_kind not in ACTION_KINDS:
        raise ValueError(
            f"Invalid chosen_action_kind: {chosen_action_kind!r}. "
            f"Must be one of {sorted(ACTION_KINDS)}"
        )
    resolved_id = tick_id or _new_id()
    record: dict[str, Any] = {
        "schema_version": SCHEMA_DIRECTOR_TICK_DECISION,
        "tick_id": resolved_id,
        "trigger_kind": trigger_kind,
        "triggering_actor_id": triggering_actor_id,
        "chosen_action_kind": chosen_action_kind,
        "chosen_actor_id": chosen_actor_id,
        "composition_inputs": list(composition_inputs),
        "since_last_tick_ms": since_last_tick_ms,
        "silence_reason": silence_reason,
    }
    return record


def build_block_stream_event(
    *,
    tick_id: str,
    block_type: str,
    block_payload: dict[str, Any],
    cut_in_state: str,
    lane: str,
    source: str,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Build a ``block_stream_event.v1`` record.

    One block = one event. Never emitted in a bundle.
    ``block_payload`` is a single block dict, not a list.
    """
    if block_type not in BLOCK_STREAM_TYPES:
        raise ValueError(
            f"Invalid block_type: {block_type!r}. "
            f"Must be one of {sorted(BLOCK_STREAM_TYPES)}"
        )
    if cut_in_state not in CUT_IN_STATES:
        raise ValueError(
            f"Invalid cut_in_state: {cut_in_state!r}. "
            f"Must be one of {sorted(CUT_IN_STATES)}"
        )
    if lane not in LANES:
        raise ValueError(
            f"Invalid lane: {lane!r}. "
            f"Must be one of {sorted(LANES)}"
        )
    return {
        "schema_version": SCHEMA_BLOCK_STREAM_EVENT,
        "event_id": event_id or _new_id(),
        "tick_id": tick_id,
        "block_type": block_type,
        "block_payload": dict(block_payload),
        "cut_in_state": cut_in_state,
        "lane": lane,
        "source": source,
    }


def build_npc_motivation_score(
    *,
    npc_id: str,
    tick_id: str,
    score: float,
    score_components: dict[str, float],
    threshold: float,
    crossed_threshold: bool,
    source_capabilities: list[str],
) -> dict[str, Any]:
    """Build an ``npc_motivation_score.v1`` record for one NPC per tick.

    ``score`` is normalized 0..1. ``score_components`` uses semantic capability
    names only (no Pi/Π IDs). ``source_capabilities`` lists the semantic names
    of runtime capability outputs consulted.
    """
    return {
        "schema_version": SCHEMA_NPC_MOTIVATION_SCORE,
        "npc_id": npc_id,
        "tick_id": tick_id,
        "score": float(score),
        "score_components": {str(k): float(v) for k, v in score_components.items()},
        "threshold": float(threshold),
        "crossed_threshold": bool(crossed_threshold),
        "source_capabilities": list(source_capabilities),
    }


def build_player_cut_in_event(
    *,
    tick_id: str,
    interrupted_block_id: str | None,
    interrupted_block_type: str | None,
    cut_kind: str,
    player_input_payload: dict[str, Any],
    cut_in_id: str | None = None,
) -> dict[str, Any]:
    """Build a ``player_cut_in_event.v1`` record.

    Player initiative is a first-class event equal to NPC initiative.
    ``cut_kind`` is determined by ``resolve_cut_kind_for_block_type()``.
    """
    if cut_kind not in CUT_KINDS:
        raise ValueError(
            f"Invalid cut_kind: {cut_kind!r}. "
            f"Must be one of {sorted(CUT_KINDS)}"
        )
    return {
        "schema_version": SCHEMA_PLAYER_CUT_IN_EVENT,
        "cut_in_id": cut_in_id or _new_id(),
        "tick_id": tick_id,
        "interrupted_block_id": interrupted_block_id,
        "interrupted_block_type": interrupted_block_type,
        "cut_kind": cut_kind,
        "player_input_payload": dict(player_input_payload),
    }


__all__ = [
    # Schema versions
    "SCHEMA_DIRECTOR_TICK_DECISION",
    "SCHEMA_BLOCK_STREAM_EVENT",
    "SCHEMA_NPC_MOTIVATION_SCORE",
    "SCHEMA_PLAYER_CUT_IN_EVENT",
    # Trigger kinds
    "TRIGGER_PLAYER_INPUT",
    "TRIGGER_MOTIVATION_THRESHOLD_CROSSED",
    "TRIGGER_STATE_CHANGE",
    "TRIGGER_COOLDOWN_CHECK",
    "TRIGGER_KINDS",
    # Action kinds
    "ACTION_SPEAK",
    "ACTION_GESTURE",
    "ACTION_LOCAL_MUNDANE_ACTION",
    "ACTION_FOLLOW",
    "ACTION_REACT_LOCALLY",
    "ACTION_SILENCE",
    "ACTION_KINDS",
    # Block types
    "BLOCK_TYPE_NARRATOR",
    "BLOCK_TYPE_ACTOR_LINE",
    "BLOCK_TYPE_ACTOR_ACTION",
    "BLOCK_TYPE_ENVIRONMENT_INTERACTION",
    "BLOCK_TYPE_SOUFFLEUSE",
    "BLOCK_STREAM_TYPES",
    # Cut-in states
    "CUT_IN_UNINTERRUPTED",
    "CUT_IN_CUT_EM_DASH",
    "CUT_IN_CUT_SKIP_TO_END",
    "CUT_IN_STATES",
    # Lanes
    "LANE_VISIBLE_SCENE_OUTPUT",
    "LANE_PLAYER_HINT",
    "LANES",
    # Cut kinds
    "CUT_KIND_EM_DASH",
    "CUT_KIND_SKIP_TO_END",
    "CUT_KIND_NO_ACTIVE_BLOCK",
    "CUT_KINDS",
    # Cut semantics
    "CUT_IN_SEMANTICS_BY_BLOCK_TYPE",
    "resolve_cut_kind_for_block_type",
    # Composition input names
    "CAPABILITY_NAME_SCENE_ENERGY",
    "CAPABILITY_NAME_SOCIAL_PRESSURE",
    "CAPABILITY_NAME_RELATIONSHIP_DYNAMICS",
    "CAPABILITY_NAME_NARRATIVE_MOMENTUM",
    "CAPABILITY_NAME_ACTOR_PRESSURE_PROFILES",
    "CAPABILITY_NAME_INTERACTION_PATTERNS",
    "CAPABILITY_NAME_PACING_RHYTHM",
    "PULSE_COMPOSITION_INPUTS",
    # Builders
    "build_director_tick_decision",
    "build_block_stream_event",
    "build_npc_motivation_score",
    "build_player_cut_in_event",
]
