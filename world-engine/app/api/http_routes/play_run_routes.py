from __future__ import annotations

from .common import *
from .models import *

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
    from app.runtime.profiles import (
        RuntimeProfileError,
        build_actor_ownership,
        resolve_runtime_profile,
        validate_selected_player_role,
    )

    runtime_profile = None
    selected_role: str | None = None
    actor_ownership: dict[str, Any] = {}

    if payload.runtime_profile_id:
        try:
            runtime_profile = resolve_runtime_profile(payload.runtime_profile_id)
            selected_role = validate_selected_player_role(payload.selected_player_role, runtime_profile)
            actor_ownership = build_actor_ownership(selected_role, runtime_profile)
        except RuntimeProfileError as exc:
            raise HTTPException(status_code=400, detail=exc.to_dict()) from exc
        template_id = payload.runtime_profile_id
    else:
        if not payload.template_id:
            raise HTTPException(status_code=400, detail="template_id or runtime_profile_id is required.")
        # FIX-004: god_of_carnage_solo must use runtime_profile_id + selected_player_role — template_id bypass rejected.
        _PROFILE_ONLY_TEMPLATES = {"god_of_carnage_solo"}
        if payload.template_id in _PROFILE_ONLY_TEMPLATES:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "runtime_profile_required",
                    "message": (
                        f"{payload.template_id!r} must be started via runtime_profile_id "
                        "with a selected_player_role, not via template_id directly."
                    ),
                    "hint": f"Set runtime_profile_id={payload.template_id!r} and selected_player_role=annette|alain.",
                },
            )
        template_id = payload.template_id

    try:
        instance = manager.create_run(
            template_id,
            display_name=payload.resolved_display_name(),
            account_id=payload.account_id,
            character_id=payload.character_id,
            preferred_role_id=selected_role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown template id") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response: dict[str, Any] = {
        "run": manager.get_instance(instance.id).model_dump(mode="json"),
        "store": manager.store.describe(),
        "hint": "Use POST /api/tickets, POST /api/internal/join-context, or the integrated backend launcher to join the run over WebSocket.",
    }

    if runtime_profile and selected_role:
        runtime_profile_handoff = {
            "contract": "create_run_response.v1",
            "content_module_id": runtime_profile.content_module_id,
            "runtime_profile_id": runtime_profile.runtime_profile_id,
            "runtime_module_id": runtime_profile.runtime_module_id,
            "runtime_mode": runtime_profile.runtime_mode,
            "selected_player_role": selected_role,
            **actor_ownership,
        }
        instance.metadata["runtime_profile_handoff"] = runtime_profile_handoff
        instance.updated_at = datetime.now(timezone.utc)
        manager.store.save(instance)
        response.update(runtime_profile_handoff)

    return response


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
