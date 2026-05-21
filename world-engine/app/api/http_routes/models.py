from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

class IdentityPayload(BaseModel):
    account_id: str | None = None
    character_id: str | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    player_name: str | None = Field(default=None, min_length=1, max_length=80)

    def resolved_display_name(self) -> str:
        return (self.display_name or self.player_name or "Guest").strip()


class CreateRunRequest(IdentityPayload):
    template_id: str | None = None
    runtime_profile_id: str | None = None
    selected_player_role: str | None = None


class TicketRequest(IdentityPayload):
    run_id: str
    preferred_role_id: str | None = None


class JoinContextRequest(TicketRequest):
    pass

class TerminateRunRequest(BaseModel):
    """Audit fields for internal terminate; both optional (empty strings default)."""

    actor_display_name: str = ""
    reason: str = ""


class CreateStorySessionRequest(BaseModel):
    module_id: str
    runtime_projection: dict[str, Any]
    session_input_language: str | None = None
    session_output_language: str | None = None
    user_id: str | None = None
    content_provenance: dict[str, Any] | None = None
    skip_graph_opening_on_create: bool = False


class ExecuteStoryTurnRequest(BaseModel):
    player_input: str = Field(min_length=1)


class BranchingSimulationTreeRequest(BaseModel):
    max_depth: int = Field(default=2, ge=0, le=3)
    max_branching: int = Field(default=2, ge=0, le=3)


class BranchingTreeCreateRequest(BaseModel):
    max_depth: int = Field(default=2, ge=0, le=3)
    max_branching: int = Field(default=2, ge=0, le=3)
    scope: str = "active"


class BranchingTreeSelectRequest(BaseModel):
    node_id: str = Field(min_length=1)


class BranchingTreeExpireRequest(BaseModel):
    reason: str = "operator_expired"


class BranchTimelineArchiveRequest(BaseModel):
    reason: str = "operator_archived"


class NarrativeReloadRequest(BaseModel):
    module_id: str
    expected_active_version: str


class NarrativePreviewLoadRequest(BaseModel):
    module_id: str
    preview_id: str
    isolation_mode: str = "session_namespace"


class NarrativePreviewUnloadRequest(BaseModel):
    module_id: str
    preview_id: str


class NarrativePreviewSessionStartRequest(BaseModel):
    module_id: str
    preview_id: str
    isolation_mode: str = "session_namespace"
    session_seed: str


class NarrativePreviewSessionEndRequest(BaseModel):
    preview_session_id: str


class NarrativeTurnValidationRequest(BaseModel):
    packet: dict[str, Any]
    output: dict[str, Any]
