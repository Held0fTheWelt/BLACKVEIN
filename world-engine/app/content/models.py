from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ExperienceKind(str, Enum):
    SOLO_STORY = "solo_story"
    GROUP_STORY = "group_story"
    OPEN_WORLD = "open_world"


class JoinPolicy(str, Enum):
    OWNER_ONLY = "owner_only"
    INVITED_PARTY = "invited_party"
    PUBLIC = "public"


class ParticipantMode(str, Enum):
    HUMAN = "human"
    NPC = "npc"


class ConditionType(str, Enum):
    FLAG_PRESENT = "flag_present"
    FLAG_ABSENT = "flag_absent"
    PROP_STATE_EQUALS = "prop_state_equals"
    BEAT_EQUALS = "beat_equals"
    ACTOR_ROLE_EQUALS = "actor_role_equals"
    CURRENT_ROOM_EQUALS = "current_room_equals"


class EffectType(str, Enum):
    SET_FLAG = "set_flag"
    CLEAR_FLAG = "clear_flag"
    SET_PROP_STATE = "set_prop_state"
    ADVANCE_BEAT = "advance_beat"
    ADD_TENSION = "add_tension"
    MOVE_ACTOR = "move_actor"
    TRANSCRIPT = "transcript"


class Effect(BaseModel):
    type: EffectType
    key: str | None = None
    value: str | int | float | None = None
    target_id: str | None = None
    text: str | None = None


class Condition(BaseModel):
    type: ConditionType
    key: str | None = None
    value: str | None = None


class ActionTemplate(BaseModel):
    id: str
    label: str
    description: str
    scope: Literal["room", "prop", "role", "global"] = "room"
    target_id: str | None = None
    available_if: list[Condition] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    cooldown: int = 0
    single_use: bool = False


class ExitTemplate(BaseModel):
    direction: str
    target_room_id: str
    label: str


class PropTemplate(BaseModel):
    id: str
    name: str
    description: str
    initial_state: str = "default"
    action_ids: list[str] = Field(default_factory=list)


class RoomTemplate(BaseModel):
    id: str
    name: str
    description: str
    exits: list[ExitTemplate] = Field(default_factory=list)
    prop_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    artwork_prompt: str | None = None


class RoleTemplate(BaseModel):
    id: str
    display_name: str
    description: str
    mode: ParticipantMode
    initial_room_id: str
    can_join: bool = False
    npc_voice: str | None = None


class BeatTemplate(BaseModel):
    id: str
    name: str
    description: str
    summary: str


class ExperienceTemplate(BaseModel):
    id: str
    title: str
    kind: ExperienceKind
    join_policy: JoinPolicy
    summary: str
    max_humans: int
    min_humans_to_start: int = 1
    persistent: bool = False
    initial_beat_id: str
    roles: list[RoleTemplate]
    rooms: list[RoomTemplate]
    props: list[PropTemplate]
    actions: list[ActionTemplate]
    beats: list[BeatTemplate]
    tags: list[str] = Field(default_factory=list)
    style_profile: str = "retro_pulp"

    def room_map(self) -> dict[str, RoomTemplate]:
        return {room.id: room for room in self.rooms}

    def role_map(self) -> dict[str, RoleTemplate]:
        return {role.id: role for role in self.roles}

    def prop_map(self) -> dict[str, PropTemplate]:
        return {prop.id: prop for prop in self.props}

    def action_map(self) -> dict[str, ActionTemplate]:
        return {action.id: action for action in self.actions}
