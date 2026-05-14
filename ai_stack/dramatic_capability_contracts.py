"""Generic dramatic capability contracts and selection helpers.

Dramatic capabilities are runtime permissions and obligations, not model/tool
capabilities. Concrete module policy can enable, require, or forbid them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


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

NPC_SOCIAL_REACTION_OPTIONAL = "npc.social_reaction.optional"
NPC_DIRECT_ANSWER_ALLOWED = "npc.direct_answer.allowed"
NPC_OFFSCREEN_BACKGROUND_ALLOWED = "npc.offscreen_background.allowed"
NPC_ACTION_GESTURE_OPTIONAL = "npc.action_gesture.optional"

NPC_EXECUTE_PLAYER_ACTION_FORBIDDEN = "npc.execute_player_action.forbidden"
NPC_NARRATE_PLAYER_PERCEPTION_FORBIDDEN = "npc.narrate_player_perception.forbidden"
NPC_FORCE_PLAYER_SPEECH_FORBIDDEN = "npc.force_player_speech.forbidden"
NPC_EXPLAIN_ENVIRONMENT_AS_NARRATOR_FORBIDDEN = "npc.explain_environment_as_narrator.forbidden"


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
    if kind == "perception" or action_kind == "perception":
        return PLAYER_PERCEPTION_REQUEST
    if kind in {"speech", "question", "social_speech_action"}:
        return PLAYER_SPEECH_REQUEST
    if action_kind == "movement":
        return PLAYER_MOVEMENT_REQUEST
    if action_kind == "object_interaction":
        return PLAYER_OBJECT_INTERACTION_REQUEST
    if kind in {"action", "mixed", "movement_action", "physical_action", "environment_interaction"}:
        return PLAYER_ACTION_REQUEST
    return None


def narrator_capability_for_frame(frame: dict[str, Any], player_input_kind: str) -> str:
    verb = str(frame.get("verb") or "").strip().lower()
    action_kind = str(frame.get("action_kind") or "").strip().lower()
    kind = str(player_input_kind or "").strip().lower()
    if kind == "perception" or verb in {"look_at", "listen_to"} or action_kind == "perception":
        return NARRATOR_PERCEPTION_RESULT_DESCRIBE
    if action_kind == "movement" or verb in {"move_to", "return_to"}:
        return NARRATOR_LOCATION_TRANSITION_DESCRIBE
    if action_kind == "object_interaction":
        return NARRATOR_OBJECT_STATE_DESCRIBE
    return NARRATOR_ACTION_CONSEQUENCE_DESCRIBE


def forbidden_capability_for_reason(reason: str | None) -> str | None:
    value = str(reason or "").strip()
    if value == "npc_executed_player_action":
        return NPC_EXECUTE_PLAYER_ACTION_FORBIDDEN
    if value == "npc_narrated_player_perception":
        return NPC_NARRATE_PLAYER_PERCEPTION_FORBIDDEN
    if value == "ai_controlled_human_actor":
        return NPC_FORCE_PLAYER_SPEECH_FORBIDDEN
    if value == "npc_explained_environment_as_narrator":
        return NPC_EXPLAIN_ENVIRONMENT_AS_NARRATOR_FORBIDDEN
    return None
