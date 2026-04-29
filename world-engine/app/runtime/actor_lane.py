"""MVP2 actor lane context builder.

Builds ActorLaneContext, RuntimeState, and StorySessionState from the
MVP1 build_actor_ownership() handoff. Validation enforcement (Wave 2.2)
and coercion rejection (Wave 2.3) extend this foundation.
"""

from __future__ import annotations

from typing import Any

from app.runtime.models import (
    ActorLaneContext,
    ActorLaneValidationResult,
    RuntimeState,
    StorySessionState,
)


def build_actor_lane_context(
    actor_ownership: dict[str, Any],
    *,
    selected_player_role: str,
    runtime_profile_id: str,
    content_module_id: str,
) -> ActorLaneContext:
    """Build ActorLaneContext from MVP1 build_actor_ownership() output."""
    human_actor_id: str = actor_ownership["human_actor_id"]
    actor_lanes: dict[str, str] = dict(actor_ownership["actor_lanes"])

    ai_allowed = sorted(aid for aid, lane in actor_lanes.items() if lane == "npc")
    ai_forbidden = [human_actor_id]

    return ActorLaneContext(
        content_module_id=content_module_id,
        runtime_profile_id=runtime_profile_id,
        selected_player_role=selected_player_role,
        human_actor_id=human_actor_id,
        actor_lanes=actor_lanes,
        ai_allowed_actor_ids=ai_allowed,
        ai_forbidden_actor_ids=ai_forbidden,
    )


def build_runtime_state(
    actor_ownership: dict[str, Any],
    *,
    run_id: str,
    story_session_id: str,
    selected_player_role: str,
    runtime_profile_id: str,
    content_module_id: str,
    runtime_module_id: str,
    content_hash: str,
    runtime_profile_hash: str = "sha256:not-computed",
    runtime_module_hash: str = "sha256:not-computed",
    current_scene_id: str = "phase_1",
) -> RuntimeState:
    """Build RuntimeState with source provenance from MVP1 actor ownership."""
    return RuntimeState(
        story_session_id=story_session_id,
        run_id=run_id,
        content_module_id=content_module_id,
        content_hash=content_hash,
        runtime_profile_id=runtime_profile_id,
        runtime_profile_hash=runtime_profile_hash,
        runtime_module_id=runtime_module_id,
        runtime_module_hash=runtime_module_hash,
        current_scene_id=current_scene_id,
        selected_player_role=selected_player_role,
        human_actor_id=actor_ownership["human_actor_id"],
        actor_lanes=dict(actor_ownership["actor_lanes"]),
    )


def build_story_session_state(
    actor_ownership: dict[str, Any],
    *,
    run_id: str,
    story_session_id: str,
    selected_player_role: str,
    runtime_profile_id: str,
    content_module_id: str,
    runtime_module_id: str,
    current_scene_id: str = "phase_1",
    turn_number: int = 0,
) -> StorySessionState:
    """Build StorySessionState from MVP1 actor ownership."""
    return StorySessionState(
        story_session_id=story_session_id,
        run_id=run_id,
        turn_number=turn_number,
        content_module_id=content_module_id,
        runtime_profile_id=runtime_profile_id,
        runtime_module_id=runtime_module_id,
        current_scene_id=current_scene_id,
        selected_player_role=selected_player_role,
        human_actor_id=actor_ownership["human_actor_id"],
        npc_actor_ids=list(actor_ownership["npc_actor_ids"]),
        visitor_present=bool(actor_ownership.get("visitor_present", False)),
    )


def approved_result(actor_lane_context: ActorLaneContext) -> ActorLaneValidationResult:
    """Return an approved validation result."""
    return ActorLaneValidationResult(
        status="approved",
        human_actor_id=actor_lane_context.human_actor_id,
    )


def rejected_result(
    *,
    error_code: str,
    actor_id: str | None = None,
    block_kind: str | None = None,
    human_actor_id: str,
    message: str | None = None,
) -> ActorLaneValidationResult:
    """Return a rejected validation result."""
    return ActorLaneValidationResult(
        status="rejected",
        error_code=error_code,
        actor_id=actor_id,
        block_kind=block_kind,
        human_actor_id=human_actor_id,
        message=message,
    )


# ---------------------------------------------------------------------------
# Wave 2.2: Human Actor Protection & Responder Validation
# ---------------------------------------------------------------------------

def validate_actor_lane_output(
    candidate: dict[str, Any],
    actor_lane_context: ActorLaneContext,
    *,
    validation_location: str = "actor_lane_seam",
) -> ActorLaneValidationResult:
    """Reject AI-generated lines, actions, emotional assignments, or decisions
    for the selected human actor.

    Must run before final response packaging and before commit.

    Error codes:
      ai_controlled_human_actor  — AI output targets the human actor
      actor_lane_validation_too_late — called after commit (detected via flag)
    """
    if candidate.get("_already_committed"):
        return rejected_result(
            error_code="actor_lane_validation_too_late",
            human_actor_id=actor_lane_context.human_actor_id,
            message="Actor lane validation must run before commit, not after.",
        )

    actor_id = (
        str(candidate.get("actor_id") or candidate.get("speaker_id") or "").strip()
    )
    block_kind = str(
        candidate.get("block_type") or candidate.get("block_kind") or "unknown"
    ).strip()

    if not actor_id:
        return approved_result(actor_lane_context)

    if actor_lane_context.is_ai_forbidden(actor_id):
        return rejected_result(
            error_code="ai_controlled_human_actor",
            actor_id=actor_id,
            block_kind=block_kind,
            human_actor_id=actor_lane_context.human_actor_id,
            message=(
                f"AI output cannot speak, act, emote, or decide for the selected "
                f"human actor {actor_id!r}. "
                f"Validation location: {validation_location}."
            ),
        )

    return approved_result(actor_lane_context)


# ---------------------------------------------------------------------------
# Wave 2.3: NPC Coercion Validation
# ---------------------------------------------------------------------------

# Action types that constitute NPC control of human actor outcome.
# These are structured classification labels, not free-text keywords.
_COERCIVE_ACTION_TYPES: frozenset[str] = frozenset({
    "force_speech",
    "compel_speech",
    "control_speech",
    "force_action",
    "compel_action",
    "control_action",
    "force_movement",
    "control_movement",
    "assign_emotion",
    "force_emotion",
    "control_emotion",
    "force_decision",
    "control_decision",
    "assign_belief",
    "control_belief",
    "force_consent",
    "assign_physical_state",
    "control_outcome",
})

# Verbs whose presence in action text indicates control when target is human actor.
# Used as secondary evidence only when combined with structural target signal.
_COERCIVE_CONTROL_VERBS: frozenset[str] = frozenset({
    "forces", "force", "forced",
    "makes", "made",
    "compels", "compel", "compelled",
    "causes", "cause", "caused",
    "commands", "command", "commanded",
    "orders", "order", "ordered",
    "decides", "decided",
    "controls", "controlled",
    "dictates", "dictate", "dictated",
    "puppets", "puppet",
})

# Social-pressure verbs that are allowed even when targeting the human actor.
_ALLOWED_PRESSURE_VERBS: frozenset[str] = frozenset({
    "pressures", "pressure",
    "challenges", "challenge",
    "confronts", "confront",
    "addresses", "address",
    "accuses", "accuse",
    "taunts", "taunt",
    "provokes", "provoke",
    "interrupts", "interrupt",
    "appeals", "appeal",
    "asks", "ask",
    "questions", "question",
    "suggests", "suggest",
})


def _text_contains_coercive_control(text: str, human_actor_id: str) -> bool:
    """Return True if the text describes NPC coercive control of the human actor.

    Uses word-level token matching against _COERCIVE_CONTROL_VERBS with an
    allowlist check against _ALLOWED_PRESSURE_VERBS to avoid false positives.
    Only returns True when a coercive verb is present AND an allowed pressure
    verb is absent (which would dominate the action classification).
    """
    if not text:
        return False
    tokens = set(text.lower().replace(",", " ").replace(".", " ").split())
    has_coercive = bool(tokens & _COERCIVE_CONTROL_VERBS)
    has_pressure = bool(tokens & _ALLOWED_PRESSURE_VERBS)
    # Pressure framing takes precedence over ambiguous coercive tokens
    if has_pressure:
        return False
    return has_coercive


def validate_npc_action_coercion(
    candidate: dict[str, Any],
    actor_lane_context: ActorLaneContext,
) -> ActorLaneValidationResult:
    """Reject NPC actions that control (not merely influence) the human actor.

    NPCs may pressure, challenge, address, interrupt, accuse, or provoke the
    human actor. NPCs may NOT decide, force, compel, or assign the human
    actor's speech, action, movement, emotion, belief, decision, consent, or
    physical state.

    Classification uses structured fields (coercion_type, action_type) first,
    with text-level analysis as supplementary evidence when the target is the
    human actor. This is NOT a pure string match.

    Error code: npc_action_controls_human_actor
    """
    actor_id = str(candidate.get("actor_id") or "").strip()
    target_actor_id = str(candidate.get("target_actor_id") or "").strip()

    # Only applies when the acting NPC targets the human actor
    if not target_actor_id:
        return approved_result(actor_lane_context)
    if not actor_lane_context.is_human_actor(target_actor_id):
        return approved_result(actor_lane_context)

    # Structural check: explicit coercion_type field (most reliable)
    coercion_type = str(candidate.get("coercion_type") or "").strip().lower()
    if coercion_type and coercion_type in {c.lower() for c in _COERCIVE_ACTION_TYPES}:
        return rejected_result(
            error_code="npc_action_controls_human_actor",
            actor_id=actor_id,
            block_kind="actor_action",
            human_actor_id=actor_lane_context.human_actor_id,
            message=(
                f"NPC {actor_id!r} coercion_type={coercion_type!r} controls "
                f"human actor {target_actor_id!r}. NPCs may pressure but not control."
            ),
        )

    # Structural check: action_type field
    action_type = str(candidate.get("action_type") or "").strip().lower()
    if action_type and action_type in {c.lower() for c in _COERCIVE_ACTION_TYPES}:
        return rejected_result(
            error_code="npc_action_controls_human_actor",
            actor_id=actor_id,
            block_kind="actor_action",
            human_actor_id=actor_lane_context.human_actor_id,
            message=(
                f"NPC {actor_id!r} action_type={action_type!r} controls "
                f"human actor {target_actor_id!r}. NPCs may pressure but not control."
            ),
        )

    # Text-based analysis (supplementary, only when target is structurally confirmed)
    text = str(candidate.get("text") or candidate.get("action") or "").strip()
    if text and _text_contains_coercive_control(text, actor_lane_context.human_actor_id):
        return rejected_result(
            error_code="npc_action_controls_human_actor",
            actor_id=actor_id,
            block_kind="actor_action",
            human_actor_id=actor_lane_context.human_actor_id,
            message=(
                f"NPC {actor_id!r} action targets human actor {target_actor_id!r} "
                f"with coercive control language. NPCs may pressure but not control."
            ),
        )

    return approved_result(actor_lane_context)


def validate_responder_plan(
    responder_plan: dict[str, Any],
    actor_lane_context: ActorLaneContext,
) -> ActorLaneValidationResult:
    """Reject responder nominations that select the human actor as primary or secondary.

    Error codes:
      human_actor_selected_as_responder — human actor nominated as responder
    """
    primary = str(
        responder_plan.get("primary_responder_id")
        or responder_plan.get("responder_id")
        or ""
    ).strip()

    if primary:
        if actor_lane_context.is_ai_forbidden(primary):
            return rejected_result(
                error_code="human_actor_selected_as_responder",
                actor_id=primary,
                block_kind="responder_nomination",
                human_actor_id=actor_lane_context.human_actor_id,
                message=(
                    f"Human actor {primary!r} cannot be selected as primary responder."
                ),
            )

    secondary_ids = responder_plan.get("secondary_responder_ids") or []
    for sid in secondary_ids:
        if not isinstance(sid, str):
            continue
        sid = sid.strip()
        if not sid:
            continue
        if actor_lane_context.is_ai_forbidden(sid):
            return rejected_result(
                error_code="human_actor_selected_as_responder",
                actor_id=sid,
                block_kind="responder_nomination",
                human_actor_id=actor_lane_context.human_actor_id,
                message=(
                    f"Human actor {sid!r} cannot be selected as secondary responder."
                ),
            )

    return approved_result(actor_lane_context)
