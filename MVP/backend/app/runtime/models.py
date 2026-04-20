"""Reusable DTOs for experience templates and ``RuntimeInstance`` (JSON-serializable run state).

Shared schema for built-in templates and the **deprecated transitional** in-process
``RuntimeManager`` tests. Live play authority and persistence belong to the **World
Engine**; import these types for shape validation, not as proof execution happens here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.content.models import ExperienceKind, JoinPolicy, ParticipantMode


class RunStatus(str, Enum):
    LOBBY = "lobby"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class ParticipantState(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    display_name: str
    role_id: str
    mode: ParticipantMode
    current_room_id: str
    connected: bool = False
    account_id: str | None = None
    character_id: str | None = None
    seat_owner_account_id: str | None = None
    seat_owner_display_name: str | None = None
    seat_owner: str | None = None
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context: Any) -> None:
        if self.seat_owner_account_id is None and self.account_id is not None:
            if self.seat_owner == self.account_id or self.seat_owner is None:
                self.seat_owner_account_id = self.account_id
        if self.seat_owner_display_name is None:
            if self.seat_owner and self.seat_owner != self.account_id:
                self.seat_owner_display_name = self.seat_owner
            elif self.mode == ParticipantMode.HUMAN:
                self.seat_owner_display_name = self.display_name
        if self.seat_owner is None:
            self.seat_owner = self.seat_owner_account_id or self.seat_owner_display_name


class LobbySeatState(BaseModel):
    role_id: str
    role_display_name: str
    reserved_for_account_id: str | None = None
    reserved_for_display_name: str | None = None
    participant_id: str | None = None
    occupant_display_name: str | None = None
    connected: bool = False
    ready: bool = False
    joined_at: datetime | None = None


class PropState(BaseModel):
    id: str
    name: str
    room_id: str
    description: str
    state: str = "default"


class TranscriptEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    kind: str
    actor: str | None = None
    text: str
    room_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: str
    run_id: str
    payload: dict[str, Any]


class RuntimeInstance(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    template_id: str
    template_title: str
    kind: ExperienceKind
    join_policy: JoinPolicy
    owner_player_name: str | None = None
    owner_account_id: str | None = None
    owner_character_id: str | None = None
    status: RunStatus = RunStatus.LOBBY
    beat_id: str
    tension: int = 0
    flags: set[str] = Field(default_factory=set)
    participants: dict[str, ParticipantState] = Field(default_factory=dict)
    lobby_seats: dict[str, LobbySeatState] = Field(default_factory=dict)
    props: dict[str, PropState] = Field(default_factory=dict)
    transcript: list[TranscriptEntry] = Field(default_factory=list)
    event_log: list[RuntimeEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    persistent: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublicRunSummary(BaseModel):
    id: str
    template_id: str
    template_title: str
    kind: ExperienceKind
    join_policy: JoinPolicy
    persistent: bool
    status: RunStatus
    connected_humans: int
    total_humans: int
    open_human_seats: int = 0
    ready_human_seats: int = 0
    tension: int
    beat_id: str
    owner_player_name: str | None = None


class RuntimeSnapshot(BaseModel):
    run_id: str
    template_id: str
    template_title: str
    kind: ExperienceKind
    join_policy: JoinPolicy
    status: RunStatus
    beat_id: str
    tension: int
    flags: list[str] = Field(default_factory=list)
    viewer_participant_id: str
    viewer_account_id: str | None = None
    viewer_character_id: str | None = None
    viewer_room_id: str
    viewer_role_id: str
    viewer_display_name: str
    current_room: dict[str, Any] | None = None
    visible_occupants: list[dict[str, Any]] = Field(default_factory=list)
    rooms: list[dict[str, Any]] = Field(default_factory=list)
    room_occupants: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    available_actions: list[dict[str, Any]]
    transcript_tail: list[TranscriptEntry]
    lobby: dict[str, Any] | None = None
    metadata: dict[str, Any]


class CommandResult(BaseModel):
    accepted: bool
    reason: str | None = None
    events: list[RuntimeEvent] = Field(default_factory=list)
