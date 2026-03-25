from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import PLAY_SERVICE_INTERNAL_API_KEY
from app.runtime.manager import RuntimeManager

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



def _require_internal_api_key(x_play_service_key: str | None = Header(default=None)) -> None:
    expected = (PLAY_SERVICE_INTERNAL_API_KEY or "").strip()
    if expected and x_play_service_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid internal API key")


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
