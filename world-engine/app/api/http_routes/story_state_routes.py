from __future__ import annotations

from .common import *
from .models import *

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


@router.get("/story/sessions/{session_id}/w5/snapshot", dependencies=[Depends(_require_internal_api_key)])
def get_story_w5_snapshot(session_id: str, manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    try:
        return manager.get_w5_admin_snapshot(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc


@router.get("/story/sessions/{session_id}/w5/actor/{actor_id}", dependencies=[Depends(_require_internal_api_key)])
def get_story_w5_actor(session_id: str, actor_id: str, manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    try:
        return manager.get_w5_admin_actor(session_id, actor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc


@router.get("/story/sessions/{session_id}/w5/conflicts", dependencies=[Depends(_require_internal_api_key)])
def get_story_w5_conflicts(session_id: str, manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    try:
        return manager.get_w5_admin_conflicts(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc


@router.get("/story/sessions/{session_id}/w5/narrator-projection", dependencies=[Depends(_require_internal_api_key)])
def get_story_w5_narrator_projection(
    session_id: str,
    actor_id: str | None = None,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        return manager.get_w5_admin_narrator_projection(session_id, actor_id=actor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc


@router.get("/story/sessions/{session_id}/w5/npc-projection/{actor_id}", dependencies=[Depends(_require_internal_api_key)])
def get_story_w5_npc_projection(session_id: str, actor_id: str, manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    try:
        return manager.get_w5_admin_npc_projection(session_id, actor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc


@router.get("/story/sessions/{session_id}/w5/validation", dependencies=[Depends(_require_internal_api_key)])
def get_story_w5_validation(session_id: str, manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    try:
        return manager.get_w5_admin_validation(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc


@router.get(
    "/story/sessions/{session_id}/thin-path-summary",
    dependencies=[Depends(_require_internal_api_key)],
)
def get_story_thin_path_summary(
    session_id: str,
    limit: int = 20,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    """Per-turn Resolver → Director → Narrator evidence for narrative_systems UI."""
    try:
        return manager.get_thin_path_summary(session_id, limit=limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc


@router.get(
    "/story/sessions/{session_id}/runtime-diagnostic-snapshot",
    dependencies=[Depends(_require_internal_api_key)],
)
def get_story_runtime_diagnostic_snapshot(
    session_id: str,
    turn_number: int | None = None,
    thin_path_limit: int = 20,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    """Aggregated ``runtime_diagnostic_snapshot.v1`` (read-only; no graph execution)."""
    try:
        return manager.get_runtime_diagnostic_snapshot(
            session_id,
            turn_number=turn_number,
            thin_path_limit=thin_path_limit,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
