"""Generic dramatic capability contracts and selection helpers.

Dramatic capabilities are runtime permissions and obligations, not model/tool
capabilities. Concrete module policy can enable, require, or forbid them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from story_runtime_core.player_input_intent_contract import (
    is_action_like_player_input_kind,
    is_mixed_player_input_kind,
    is_perception_like_player_input_kind,
    is_speech_like_player_input_kind,
)

DRAMATIC_CAPABILITY_SCHEMA_VERSION = "dramatic_capability.v1"

PLAYER_MOVEMENT_REQUEST = "player.movement.request"
PLAYER_PERCEPTION_REQUEST = "player.perception.request"
PLAYER_OBJECT_INTERACTION_REQUEST = "player.object_interaction.request"
PLAYER_SPEECH_REQUEST = "player.speech.request"
PLAYER_ACTION_REQUEST = "player.action.request"

NARRATOR_LOCATION_TRANSITION_DESCRIBE = "narrator.location_transition.describe"
NARRATOR_PERCEPTION_RESULT_DESCRIBE = "narrator.perception_result.describe"
NARRATOR_OBJECT_STATE_DESCRIBE = "narrator.object_state.describe"
NARRATOR_SCENE_CONTEXT_ESTABLISH = "narrator.scene_context.establish"
NARRATOR_OPENING_EVENT_REALIZE = "narrator.opening_event.realize"
NARRATOR_ACTION_CONSEQUENCE_DESCRIBE = "narrator.action_consequence.describe"

SOUFFLEUSE_ROLE_ORIENTATION = "souffleuse.role_orientation"
SOUFFLEUSE_ROLE_PRESSURE = "souffleuse.role_pressure"

NPC_SOCIAL_REACTION_OPTIONAL = "npc.social_reaction.optional"
NPC_DIRECT_ANSWER_ALLOWED = "npc.direct_answer.allowed"
NPC_OFFSCREEN_BACKGROUND_ALLOWED = "npc.offscreen_background.allowed"
NPC_ACTION_GESTURE_OPTIONAL = "npc.action_gesture.optional"

NPC_EXECUTE_PLAYER_ACTION_FORBIDDEN = "npc.execute_player_action.forbidden"
NPC_NARRATE_PLAYER_PERCEPTION_FORBIDDEN = "npc.narrate_player_perception.forbidden"
NPC_FORCE_PLAYER_SPEECH_FORBIDDEN = "npc.force_player_speech.forbidden"
NPC_EXPLAIN_ENVIRONMENT_AS_NARRATOR_FORBIDDEN = "npc.explain_environment_as_narrator.forbidden"

NPC_EXECUTED_PLAYER_ACTION_REASON = "npc_executed_player_action"
NPC_NARRATED_PLAYER_PERCEPTION_REASON = "npc_narrated_player_perception"
AI_CONTROLLED_HUMAN_ACTOR_REASON = "ai_controlled_human_actor"
NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON = "npc_action_controls_human_actor"
NPC_EXPLAINED_ENVIRONMENT_AS_NARRATOR_REASON = "npc_explained_environment_as_narrator"

NPC_COERCIVE_ACTION_TYPES: frozenset[str] = frozenset(
    {
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
    }
)

NPC_COERCIVE_CONTROL_VERBS: frozenset[str] = frozenset(
    {
        "forces",
        "force",
        "forced",
        "makes",
        "made",
        "compels",
        "compel",
        "compelled",
        "causes",
        "cause",
        "caused",
        "commands",
        "command",
        "commanded",
        "orders",
        "order",
        "ordered",
        "decides",
        "decided",
        "controls",
        "controlled",
        "dictates",
        "dictate",
        "dictated",
        "puppets",
        "puppet",
    }
)

NPC_ALLOWED_PRESSURE_VERBS: frozenset[str] = frozenset(
    {
        "pressures",
        "pressure",
        "challenges",
        "challenge",
        "confronts",
        "confront",
        "addresses",
        "address",
        "accuses",
        "accuse",
        "taunts",
        "taunt",
        "provokes",
        "provoke",
        "interrupts",
        "interrupt",
        "appeals",
        "appeal",
        "asks",
        "ask",
        "questions",
        "question",
        "suggests",
        "suggest",
    }
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@dataclass(frozen=True)
class DramaticCapabilitySelection:
    schema_version: str = DRAMATIC_CAPABILITY_SCHEMA_VERSION
    requested_capabilities: list[str] = field(default_factory=list)
    selected_capabilities: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    blocked_capabilities: list[str] = field(default_factory=list)
    source: str = "runtime"

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class DramaticCapabilityRealization:
    schema_version: str = DRAMATIC_CAPABILITY_SCHEMA_VERSION
    realized_capabilities: list[str] = field(default_factory=list)
    violated_capabilities: list[str] = field(default_factory=list)
    missing_required_capabilities: list[str] = field(default_factory=list)
    status: str = "not_applicable"
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def default_capability_policy() -> dict[str, Any]:
    return {
        "schema_version": DRAMATIC_CAPABILITY_SCHEMA_VERSION,
        "enabled": [
            PLAYER_MOVEMENT_REQUEST,
            PLAYER_PERCEPTION_REQUEST,
            PLAYER_OBJECT_INTERACTION_REQUEST,
            PLAYER_SPEECH_REQUEST,
            PLAYER_ACTION_REQUEST,
            NARRATOR_LOCATION_TRANSITION_DESCRIBE,
            NARRATOR_PERCEPTION_RESULT_DESCRIBE,
            NARRATOR_OBJECT_STATE_DESCRIBE,
            NARRATOR_SCENE_CONTEXT_ESTABLISH,
            NARRATOR_OPENING_EVENT_REALIZE,
            NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
            SOUFFLEUSE_ROLE_ORIENTATION,
            SOUFFLEUSE_ROLE_PRESSURE,
            NPC_SOCIAL_REACTION_OPTIONAL,
            NPC_DIRECT_ANSWER_ALLOWED,
            NPC_OFFSCREEN_BACKGROUND_ALLOWED,
            NPC_ACTION_GESTURE_OPTIONAL,
        ],
        "forbidden": [
            NPC_EXECUTE_PLAYER_ACTION_FORBIDDEN,
            NPC_NARRATE_PLAYER_PERCEPTION_FORBIDDEN,
            NPC_FORCE_PLAYER_SPEECH_FORBIDDEN,
            NPC_EXPLAIN_ENVIRONMENT_AS_NARRATOR_FORBIDDEN,
        ],
        "required_when": {
            NARRATOR_LOCATION_TRANSITION_DESCRIBE: ["player.movement.request"],
            NARRATOR_PERCEPTION_RESULT_DESCRIBE: ["player.perception.request"],
            NARRATOR_OBJECT_STATE_DESCRIBE: ["player.object_interaction.request"],
            NARRATOR_ACTION_CONSEQUENCE_DESCRIBE: ["player.action.request"],
        },
    }


def add_unique(items: list[str], value: str | None) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def player_capability_for_frame(frame: dict[str, Any], player_input_kind: str) -> str | None:
    kind = str(player_input_kind or "").strip().lower()
    action_kind = str(frame.get("action_kind") or "").strip().lower()
    if is_perception_like_player_input_kind(kind) or action_kind == "perception":
        return PLAYER_PERCEPTION_REQUEST
    if is_speech_like_player_input_kind(kind):
        return PLAYER_SPEECH_REQUEST
    if action_kind == "movement":
        return PLAYER_MOVEMENT_REQUEST
    if action_kind == "object_interaction":
        return PLAYER_OBJECT_INTERACTION_REQUEST
    if is_action_like_player_input_kind(kind) or is_mixed_player_input_kind(kind):
        return PLAYER_ACTION_REQUEST
    return None


def narrator_capability_for_frame(frame: dict[str, Any], player_input_kind: str) -> str:
    verb = str(frame.get("verb") or "").strip().lower()
    action_kind = str(frame.get("action_kind") or "").strip().lower()
    kind = str(player_input_kind or "").strip().lower()
    if is_perception_like_player_input_kind(kind) or verb in {"look_at", "listen_to"} or action_kind == "perception":
        return NARRATOR_PERCEPTION_RESULT_DESCRIBE
    if action_kind == "movement" or verb in {"move_to", "return_to"}:
        return NARRATOR_LOCATION_TRANSITION_DESCRIBE
    if action_kind == "object_interaction":
        return NARRATOR_OBJECT_STATE_DESCRIBE
    return NARRATOR_ACTION_CONSEQUENCE_DESCRIBE


def forbidden_capability_for_reason(reason: str | None) -> str | None:
    value = str(reason or "").strip()
    if value == NPC_EXECUTED_PLAYER_ACTION_REASON:
        return NPC_EXECUTE_PLAYER_ACTION_FORBIDDEN
    if value == NPC_NARRATED_PLAYER_PERCEPTION_REASON:
        return NPC_NARRATE_PLAYER_PERCEPTION_FORBIDDEN
    if value in {AI_CONTROLLED_HUMAN_ACTOR_REASON, NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON}:
        return NPC_FORCE_PLAYER_SPEECH_FORBIDDEN
    if value == NPC_EXPLAINED_ENVIRONMENT_AS_NARRATOR_REASON:
        return NPC_EXPLAIN_ENVIRONMENT_AS_NARRATOR_FORBIDDEN
    return None
