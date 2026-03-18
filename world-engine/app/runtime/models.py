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
    seat_owner: str | None = None
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    status: RunStatus = RunStatus.LOBBY
    beat_id: str
    tension: int = 0
    flags: set[str] = Field(default_factory=set)
    participants: dict[str, ParticipantState] = Field(default_factory=dict)
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
    flags: list[str]
    viewer_participant_id: str
    viewer_room_id: str
    viewer_role_id: str
    viewer_display_name: str
    rooms: list[dict[str, Any]]
    room_occupants: dict[str, list[dict[str, Any]]]
    available_actions: list[dict[str, Any]]
    transcript_tail: list[TranscriptEntry]
    metadata: dict[str, Any]


class CommandResult(BaseModel):
    accepted: bool
    reason: str | None = None
    events: list[RuntimeEvent] = Field(default_factory=list)
