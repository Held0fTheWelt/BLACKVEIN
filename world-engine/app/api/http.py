from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import PLAY_SERVICE_INTERNAL_API_KEY
from app.runtime.manager import RuntimeManager
from app.story_runtime import StoryRuntimeManager

router = APIRouter(prefix="/api", tags=["api"])


class IdentityPayload(BaseModel):
    account_id: str | None = None
    character_id: str | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    player_name: str | None = Field(default=None, min_length=1, max_length=80)

    def resolved_display_name(self) -> str:
        return (self.display_name or self.player_name or "Guest").strip()


class CreateRunRequest(IdentityPayload):
    template_id: str


class TicketRequest(IdentityPayload):
    run_id: str
    preferred_role_id: str | None = None


class JoinContextRequest(TicketRequest):
    pass


def get_manager(request: Request) -> RuntimeManager:
    return request.app.state.manager


def get_story_manager(request: Request) -> StoryRuntimeManager:
    return request.app.state.story_manager



def _require_internal_api_key(x_play_service_key: str | None = Header(default=None)) -> None:
    """Require valid internal API key for protected endpoints.

    Behavior:
    - If PLAY_SERVICE_INTERNAL_API_KEY is configured: key must match exactly (fail-fast)
    - If PLAY_SERVICE_INTERNAL_API_KEY is not configured: no enforcement (lenient test mode)
    - Empty/blank key values always rejected when configured

    Raises:
        HTTPException: 401 Unauthorized if key missing, invalid, or blank
    """
    expected = (PLAY_SERVICE_INTERNAL_API_KEY or "").strip()

    if expected:
        # API key is configured - enforce it
        provided = (x_play_service_key or "").strip()
        if not provided or provided != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid internal API key"
            )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(request: Request, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    return {
        "status": "ready",
        "app": request.app.title,
        "store": manager.store.describe(),
        "template_count": len(manager.list_templates()),
        "run_count": len(manager.list_runs()),
    }


@router.get("/templates")
def list_templates(manager: RuntimeManager = Depends(get_manager)) -> list[dict[str, Any]]:
    return [template.model_dump(mode="json") for template in manager.list_templates()]


@router.get("/runs")
def list_runs(manager: RuntimeManager = Depends(get_manager)) -> list[dict[str, Any]]:
    return [run.model_dump(mode="json") for run in manager.list_runs()]


@router.get("/runs/{run_id}")
def get_run_details(run_id: str, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    try:
        return manager.get_run_details(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@router.post("/runs")
def create_run(payload: CreateRunRequest, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    try:
        instance = manager.create_run(
            payload.template_id,
            display_name=payload.resolved_display_name(),
            account_id=payload.account_id,
            character_id=payload.character_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown template id") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "run": manager.get_instance(instance.id).model_dump(mode="json"),
        "store": manager.store.describe(),
        "hint": "Use POST /api/tickets, POST /api/internal/join-context, or the integrated backend launcher to join the run over WebSocket.",
    }


@router.post("/tickets")
def create_ticket(payload: TicketRequest, request: Request, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    try:
        participant = manager.find_or_join_run(
            payload.run_id,
            display_name=payload.resolved_display_name(),
            account_id=payload.account_id,
            character_id=payload.character_id,
            preferred_role_id=payload.preferred_role_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    ticket = request.app.state.ticket_manager.issue(
        {
            "run_id": payload.run_id,
            "participant_id": participant.id,
            "account_id": participant.account_id,
            "character_id": participant.character_id,
            "display_name": participant.display_name,
            "role_id": participant.role_id,
        }
    )
    return {
        "ticket": ticket,
        "run_id": payload.run_id,
        "participant_id": participant.id,
        "role_id": participant.role_id,
        "display_name": participant.display_name,
    }


@router.post("/internal/join-context", dependencies=[Depends(_require_internal_api_key)])
def create_join_context(payload: JoinContextRequest, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    try:
        participant = manager.find_or_join_run(
            payload.run_id,
            display_name=payload.resolved_display_name(),
            account_id=payload.account_id,
            character_id=payload.character_id,
            preferred_role_id=payload.preferred_role_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "run_id": payload.run_id,
        "participant_id": participant.id,
        "role_id": participant.role_id,
        "display_name": participant.display_name,
        "account_id": participant.account_id,
        "character_id": participant.character_id,
    }


@router.get("/internal/runs/{run_id}", dependencies=[Depends(_require_internal_api_key)])
def get_internal_run_details(run_id: str, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    try:
        return manager.get_run_details(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@router.get("/internal/runs/{run_id}/transcript", dependencies=[Depends(_require_internal_api_key)])
def get_internal_transcript(run_id: str, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    try:
        instance = manager.get_instance(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return {
        "run_id": run_id,
        "entries": [entry.model_dump(mode="json") for entry in instance.transcript],
    }


class TerminateRunRequest(BaseModel):
    """Audit fields for internal terminate; both optional (empty strings default)."""

    actor_display_name: str = ""
    reason: str = ""


class CreateStorySessionRequest(BaseModel):
    module_id: str
    runtime_projection: dict[str, Any]


class ExecuteStoryTurnRequest(BaseModel):
    player_input: str = Field(min_length=1)


@router.post("/internal/runs/{run_id}/terminate", dependencies=[Depends(_require_internal_api_key)])
def terminate_run_internal(run_id: str, payload: TerminateRunRequest, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    try:
        return manager.terminate_run(
            run_id,
            actor_display_name=payload.actor_display_name,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@router.delete("/runs/{run_id}", dependencies=[Depends(_require_internal_api_key)])
def delete_run(run_id: str, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    try:
        return manager.terminate_run(run_id, actor_display_name="internal_delete", reason="DELETE /api/runs")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc

@router.get("/runs/{run_id}/snapshot/{participant_id}")
def get_snapshot(run_id: str, participant_id: str, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    try:
        snapshot = manager.build_snapshot(run_id, participant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run or participant not found") from exc
    return snapshot.model_dump(mode="json")


@router.get("/runs/{run_id}/transcript")
def get_transcript(run_id: str, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    try:
        instance = manager.get_instance(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return {
        "run_id": run_id,
        "entries": [entry.model_dump(mode="json") for entry in instance.transcript],
    }


@router.get("/story/sessions", dependencies=[Depends(_require_internal_api_key)])
def list_story_sessions(manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    items = manager.list_session_summaries()
    return {"items": items, "total": len(items)}


@router.post("/story/sessions", dependencies=[Depends(_require_internal_api_key)])
def create_story_session(payload: CreateStorySessionRequest, manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    session = manager.create_session(module_id=payload.module_id, runtime_projection=payload.runtime_projection)
    return {
        "session_id": session.session_id,
        "module_id": session.module_id,
        "turn_counter": session.turn_counter,
        "current_scene_id": session.current_scene_id,
        "warnings": ["world_engine_authoritative_story_runtime"],
    }


@router.post("/story/sessions/{session_id}/turns", dependencies=[Depends(_require_internal_api_key)])
def execute_story_turn(
    session_id: str,
    payload: ExecuteStoryTurnRequest,
    request: Request,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    trace_id = getattr(request.state, "trace_id", None)
    try:
        turn = manager.execute_turn(
            session_id=session_id,
            player_input=payload.player_input,
            trace_id=trace_id if isinstance(trace_id, str) else None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "turn": turn}


@router.get("/story/sessions/{session_id}/state", dependencies=[Depends(_require_internal_api_key)])
def get_story_state(session_id: str, manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    try:
        return manager.get_state(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc


@router.get("/story/sessions/{session_id}/diagnostics", dependencies=[Depends(_require_internal_api_key)])
def get_story_diagnostics(session_id: str, manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    try:
        return manager.get_diagnostics(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
