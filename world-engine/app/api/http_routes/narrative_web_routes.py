from __future__ import annotations

from .common import *
from .models import *

@router.get("/story/sessions/{session_id}/callback-web", dependencies=[Depends(_require_internal_api_key)])
def get_story_callback_web(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        callback_web = manager.get_callback_web(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "callback_web": callback_web}


@router.get("/story/sessions/{session_id}/callback-web/edges", dependencies=[Depends(_require_internal_api_key)])
def list_story_callback_web_edges(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        edges = manager.list_callback_web_edges(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "callback_web_edges": edges}


@router.post("/story/sessions/{session_id}/callback-web/rebuild", dependencies=[Depends(_require_internal_api_key)])
def rebuild_story_callback_web(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        callback_web = manager.rebuild_callback_web(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "callback_web": callback_web}


@router.get("/story/sessions/{session_id}/consequence-cascade", dependencies=[Depends(_require_internal_api_key)])
def get_story_consequence_cascade(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        cascade = manager.get_consequence_cascade(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "consequence_cascade": cascade}


@router.get("/story/sessions/{session_id}/consequence-cascade/edges", dependencies=[Depends(_require_internal_api_key)])
def list_story_consequence_cascade_edges(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        edges = manager.list_consequence_cascade_edges(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "consequence_cascade_edges": edges}


@router.post("/story/sessions/{session_id}/consequence-cascade/rebuild", dependencies=[Depends(_require_internal_api_key)])
def rebuild_story_consequence_cascade(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        cascade = manager.rebuild_consequence_cascade(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "consequence_cascade": cascade}


@router.get("/story/sessions/{session_id}/diagnostics-envelope", dependencies=[Depends(_require_internal_api_key)])
def get_story_diagnostics_envelope(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    """Return the last diagnostics envelope for a story session."""
    try:
        envelope = manager.get_last_diagnostics_envelope(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    if envelope is None:
        return {"session_id": session_id, "diagnostics_envelope": None, "warning": "no_turns_yet"}
    envelope_dict = envelope_dict_to_response(envelope, context="operator")
    return {"session_id": session_id, "diagnostics_envelope": envelope_dict}


@router.get("/story/runtime/narrative-gov-summary", dependencies=[Depends(_require_internal_api_key)])
def get_narrative_gov_summary(
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    """Return operator health evidence for narrative governance."""
    return manager.get_narrative_gov_summary()


@router.get("/story/sessions/{session_id}/stream-narrator")
def stream_narrator_blocks(session_id: str, manager: StoryRuntimeManager = Depends(get_story_manager)) -> StreamingResponse:
    """Stream narrator blocks as Server-Sent Events (SSE) while narrator is generating.

    Returns a streaming response that emits NarrativeRuntimeAgentEvent objects as JSON.
    Client receives events until ruhepunkt_signal is received, then input can be queued.

    Returns:
        StreamingResponse: SSE stream of narrator block events

    Status codes:
        - 404: Session not found or no narrator streaming active
        - 200: Streaming started (event stream)
    """
    def generate() -> Generator[str, None, None]:
        """Generate SSE events from narrator agent stream."""
        try:
            agent = manager.narrative_agents.get(session_id)

            if not agent:
                yield f"data: {json.dumps({'error': 'no_narrator_streaming', 'session_id': session_id})}\n\n"
                return

            # Stream narrator events
            for event in agent.stream_narrator_blocks(agent.current_input):
                yield f"data: {event.to_json()}\n\n"

        except Exception as exc:
            error_event = {
                "error": "streaming_failed",
                "message": str(exc),
                "session_id": session_id,
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
