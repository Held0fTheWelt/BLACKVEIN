from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.runtime.manager import RuntimeManager

router = APIRouter(prefix="/api", tags=["api"])


def get_manager(request: Request) -> RuntimeManager:
    return request.app.state.manager


class CreateRunRequest(BaseModel):
    template_id: str
    player_name: str = Field(min_length=1, max_length=50)


class TicketRequest(BaseModel):
    run_id: str
    player_name: str = Field(min_length=1, max_length=50)
    preferred_role_id: str | None = None


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/templates")
def list_templates(manager: RuntimeManager = Depends(get_manager)) -> list[dict]:
    return [template.model_dump(mode="json") for template in manager.list_templates()]


@router.get("/runs")
def list_runs(manager: RuntimeManager = Depends(get_manager)) -> list[dict]:
    return [run.model_dump(mode="json") for run in manager.list_runs()]


@router.post("/runs")
def create_run(payload: CreateRunRequest, manager: RuntimeManager = Depends(get_manager)) -> dict:
    try:
        instance = manager.create_run(payload.template_id, payload.player_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown template id") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "run": manager.get_instance(instance.id).model_dump(mode="json"),
        "hint": "Use POST /api/tickets or the browser client to join the run over WebSocket.",
    }


@router.post("/tickets")
def create_ticket(payload: TicketRequest, request: Request, manager: RuntimeManager = Depends(get_manager)) -> dict:
    try:
        participant = manager.find_or_join_run(payload.run_id, payload.player_name, payload.preferred_role_id)
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
            "player_name": payload.player_name,
            "role_id": participant.role_id,
        }
    )
    return {
        "ticket": ticket,
        "run_id": payload.run_id,
        "participant_id": participant.id,
        "role_id": participant.role_id,
    }


@router.get("/runs/{run_id}/snapshot/{participant_id}")
def get_snapshot(run_id: str, participant_id: str, manager: RuntimeManager = Depends(get_manager)) -> dict:
    try:
        snapshot = manager.build_snapshot(run_id, participant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run or participant not found") from exc
    return snapshot.model_dump(mode="json")


@router.get("/runs/{run_id}/transcript")
def get_transcript(run_id: str, manager: RuntimeManager = Depends(get_manager)) -> dict:
    try:
        instance = manager.get_instance(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return {
        "run_id": run_id,
        "entries": [entry.model_dump(mode="json") for entry in instance.transcript],
    }
