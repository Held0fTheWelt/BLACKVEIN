from __future__ import annotations

from .common import *
from .models import *

@router.post("/internal/narrative/packages/reload-active", dependencies=[Depends(_require_internal_api_key)])
def narrative_reload_active(payload: NarrativeReloadRequest, request: Request) -> dict[str, Any]:
    loader = _get_narrative_loader(request)
    try:
        result = loader.reload_active(module_id=payload.module_id, expected_active_version=payload.expected_active_version)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="module_not_found") from exc
    return {"ok": True, "data": result}


@router.post("/internal/narrative/packages/load-preview", dependencies=[Depends(_require_internal_api_key)])
def narrative_load_preview(payload: NarrativePreviewLoadRequest, request: Request) -> dict[str, Any]:
    loader = _get_narrative_loader(request)
    registry = _get_preview_registry(request)
    try:
        result = loader.load_preview(module_id=payload.module_id, preview_id=payload.preview_id)
        registry.load_preview(module_id=payload.module_id, preview_id=payload.preview_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="preview_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "data": result}


@router.post("/internal/narrative/packages/unload-preview", dependencies=[Depends(_require_internal_api_key)])
def narrative_unload_preview(payload: NarrativePreviewUnloadRequest, request: Request) -> dict[str, Any]:
    loader = _get_narrative_loader(request)
    registry = _get_preview_registry(request)
    try:
        result = loader.unload_preview(module_id=payload.module_id, preview_id=payload.preview_id)
        registry.unload_preview(module_id=payload.module_id, preview_id=payload.preview_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="preview_not_loaded") from exc
    return {"ok": True, "data": result}


@router.post("/internal/narrative/preview/start-session", dependencies=[Depends(_require_internal_api_key)])
def narrative_preview_start_session(payload: NarrativePreviewSessionStartRequest, request: Request) -> dict[str, Any]:
    registry = _get_preview_registry(request)
    try:
        session = registry.start_session(
            module_id=payload.module_id,
            preview_id=payload.preview_id,
            session_seed=payload.session_seed,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="preview_not_loaded") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "data": {"preview_session_id": session.preview_session_id, "namespace": session.namespace}}


@router.post("/internal/narrative/preview/end-session", dependencies=[Depends(_require_internal_api_key)])
def narrative_preview_end_session(payload: NarrativePreviewSessionEndRequest, request: Request) -> dict[str, Any]:
    registry = _get_preview_registry(request)
    try:
        registry.end_session(payload.preview_session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="preview_session_not_found") from exc
    return {"ok": True, "data": {"preview_session_id": payload.preview_session_id, "ended": True}}
