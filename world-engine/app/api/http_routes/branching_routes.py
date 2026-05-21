from __future__ import annotations

from .common import *
from .models import *

@router.post("/story/sessions/{session_id}/branching/simulation-tree", dependencies=[Depends(_require_internal_api_key)])
def build_story_branching_simulation_tree(
    session_id: str,
    payload: BranchingSimulationTreeRequest,
    request: Request,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    """Return an isolated, non-authoritative multi-turn branch simulation tree."""
    trace_id = getattr(request.state, "trace_id", None)
    try:
        tree = manager.build_branching_simulation_tree(
            session_id=session_id,
            max_depth=payload.max_depth,
            max_branching=payload.max_branching,
            trace_id=trace_id if isinstance(trace_id, str) else None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "branching_simulation_tree": tree}


@router.post("/story/sessions/{session_id}/branching/trees", dependencies=[Depends(_require_internal_api_key)])
def create_story_branching_tree(
    session_id: str,
    payload: BranchingTreeCreateRequest,
    request: Request,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    """Create and persist a selectable bounded branch tree."""
    trace_id = getattr(request.state, "trace_id", None)
    try:
        tree = manager.create_branching_tree(
            session_id=session_id,
            max_depth=payload.max_depth,
            max_branching=payload.max_branching,
            trace_id=trace_id if isinstance(trace_id, str) else None,
            scope=payload.scope,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    timeline = manager.get_branch_timeline(session_id=session_id)
    return {"session_id": session_id, "branching_tree": tree, "branch_timeline": timeline}


@router.get("/story/sessions/{session_id}/branching/trees", dependencies=[Depends(_require_internal_api_key)])
def list_story_branching_trees(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        rows = manager.list_branching_trees(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "branching_trees": rows}


@router.get("/story/sessions/{session_id}/branching/timeline", dependencies=[Depends(_require_internal_api_key)])
def get_story_branch_timeline(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        timeline = manager.get_branch_timeline(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "branch_timeline": timeline}


@router.get("/story/sessions/{session_id}/branching/timeline/events", dependencies=[Depends(_require_internal_api_key)])
def list_story_branch_timeline_events(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        events = manager.list_branch_timeline_events(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "branch_timeline_events": events}


@router.post("/story/sessions/{session_id}/branching/timeline/compact", dependencies=[Depends(_require_internal_api_key)])
def compact_story_branch_timeline(
    session_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        timeline = manager.compact_branch_timeline(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "branch_timeline": timeline}


@router.post("/story/sessions/{session_id}/branching/timeline/archive", dependencies=[Depends(_require_internal_api_key)])
def archive_story_branch_timeline(
    session_id: str,
    payload: BranchTimelineArchiveRequest,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        timeline = manager.archive_branch_timeline(session_id=session_id, reason=payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    return {"session_id": session_id, "branch_timeline": timeline}


@router.get("/story/sessions/{session_id}/branching/trees/{tree_id}", dependencies=[Depends(_require_internal_api_key)])
def get_story_branching_tree(
    session_id: str,
    tree_id: str,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        tree = manager.get_branching_tree(session_id=session_id, tree_id=tree_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Branching tree not found") from exc
    return {"session_id": session_id, "branching_tree": tree}


@router.post("/story/sessions/{session_id}/branching/trees/{tree_id}/select", dependencies=[Depends(_require_internal_api_key)])
def select_story_branching_tree_node(
    session_id: str,
    tree_id: str,
    payload: BranchingTreeSelectRequest,
    request: Request,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    trace_id = getattr(request.state, "trace_id", None)
    try:
        result = manager.select_branching_tree_node(
            session_id=session_id,
            tree_id=tree_id,
            node_id=payload.node_id,
            trace_id=trace_id if isinstance(trace_id, str) else None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Branching tree or node not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    result["branch_timeline"] = manager.get_branch_timeline(session_id=session_id)
    return result


@router.post("/story/sessions/{session_id}/branching/trees/{tree_id}/expire", dependencies=[Depends(_require_internal_api_key)])
def expire_story_branching_tree(
    session_id: str,
    tree_id: str,
    payload: BranchingTreeExpireRequest,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    try:
        tree = manager.expire_branching_tree(
            session_id=session_id,
            tree_id=tree_id,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Branching tree not found") from exc
    timeline = manager.get_branch_timeline(session_id=session_id)
    return {"session_id": session_id, "branching_tree": tree, "branch_timeline": timeline}
