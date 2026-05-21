from __future__ import annotations

from .common import *
from .models import *

@router.get("/story/sessions", dependencies=[Depends(_require_internal_api_key)])
def list_story_sessions(manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    items = manager.list_session_summaries()
    return {"items": items, "total": len(items)}


@router.post("/story/sessions", dependencies=[Depends(_require_internal_api_key)])
def create_story_session(
    payload: CreateStorySessionRequest,
    request: Request,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    trace_id = getattr(request.state, "trace_id", None)
    langfuse_trace_id = getattr(request.state, "langfuse_trace_id", None)
    adapter = None
    root_span = None
    previous_active_span = None
    story_session_id = uuid4().hex

    try:
        trace_classification = _trace_classification_from_request(
            request,
            runtime_projection=payload.runtime_projection,
        )
        try:
            from app.observability.langfuse_adapter import LangfuseAdapter
            adapter = LangfuseAdapter.get_instance()
            if hasattr(adapter, "refresh_backend_config"):
                adapter.refresh_backend_config(force=True)
            previous_active_span = adapter.get_active_span()
            adapter.set_active_span(None)
            logger.info(f"[HTTP] Adapter loaded for session create: is_ready={adapter.is_ready}, is_enabled={adapter.is_enabled()}")
        except Exception as exc:
            logger.error(f"[HTTP] ERROR: Failed to load Langfuse adapter for session create: {type(exc).__name__}: {exc}", exc_info=True)
            adapter = None

        default_lf = os.getenv("LANGFUSE_ENVIRONMENT", "development")
        if adapter and adapter.is_enabled():
            default_lf = str(adapter.config.environment or default_lf)
        lf_tracing_env = resolve_langfuse_environment(
            trace_classification.get("trace_origin"),
            trace_classification.get("execution_tier"),
            default=default_lf,
        )

        if adapter and adapter.is_enabled():
            if langfuse_trace_id:
                root_span = adapter.start_span_in_trace(
                    trace_id=langfuse_trace_id,
                    name="world-engine.session.create",
                    input={"module_id": payload.module_id, "session_id": story_session_id},
                    metadata={
                        "stage": "world_engine_session_loop_create",
                        "turn_kind": "session_loop",
                        "session_loop_status": "runtime_engine_initializing",
                        "session_id": story_session_id,
                        "environment": lf_tracing_env,
                        **trace_classification,
                    },
                )
            else:
                root_span = adapter.start_trace(
                    name="world-engine.session.create",
                    session_id=story_session_id,
                    input={"module_id": payload.module_id, "session_id": story_session_id},
                    metadata={
                        "module_id": payload.module_id,
                        "turn_kind": "session_loop",
                        "session_loop_status": "runtime_engine_initializing",
                        "session_id": story_session_id,
                        "environment": lf_tracing_env,
                        **trace_classification,
                    },
                )
            if root_span:
                adapter.set_active_span(root_span)

        session_scope = (
            adapter.session_scope(
                root_span=root_span,
                session_id=story_session_id,
                metadata={"module_id": payload.module_id, "turn_kind": "session_loop"},
                trace_name="world-engine.session.create",
                user_id=payload.user_id,
            )
            if root_span and adapter and hasattr(adapter, "session_scope")
            else nullcontext()
        )
        with session_scope:
            session = manager.create_session(
                module_id=payload.module_id,
                runtime_projection=payload.runtime_projection,
                session_input_language=payload.session_input_language,
                session_output_language=payload.session_output_language,
                content_provenance={
                    **(payload.content_provenance if isinstance(payload.content_provenance, dict) else {}),
                    "trace_classification": trace_classification,
                },
                trace_id=trace_id if isinstance(trace_id, str) else None,
                session_id=story_session_id,
                skip_graph_opening_on_create=payload.skip_graph_opening_on_create,
            )
            opening_turn = next(
                (
                    row
                    for row in reversed(session.diagnostics)
                    if isinstance(row, dict) and row.get("turn_kind") == "opening"
                ),
                None,
            )
            runtime_world = session.runtime_world if isinstance(session.runtime_world, dict) else {}
            runtime_world_summary = {
                "schema_version": runtime_world.get("schema_version"),
                "status": runtime_world.get("status"),
                "mode": runtime_world.get("mode"),
                "current_room_id": runtime_world.get("current_room_id"),
                "room_count": len(runtime_world.get("rooms") if isinstance(runtime_world.get("rooms"), dict) else {}),
                "prop_count": len(runtime_world.get("props") if isinstance(runtime_world.get("props"), dict) else {}),
                "exit_count": len(runtime_world.get("exits") if isinstance(runtime_world.get("exits"), dict) else {}),
                "actor_count": len(runtime_world.get("actors") if isinstance(runtime_world.get("actors"), dict) else {}),
                "diagnostic_summary": runtime_world.get("diagnostic_summary"),
            }
            session_loop = {
                "status": "runtime_engine_initialized",
                "session_id": session.session_id,
                "module_id": session.module_id,
                "turn_counter": session.turn_counter,
                "current_scene_id": session.current_scene_id,
                "history_len": len(session.history),
                "diagnostics_len": len(session.diagnostics),
                "runtime_world": runtime_world_summary,
            }
            if root_span:
                root_span.update(
                    output={
                        "session_id": session.session_id,
                        "turn_counter": session.turn_counter,
                        "success": True,
                        "session_loop": session_loop,
                        "path_summary": None,
                    },
                    metadata={
                        "session_id": session.session_id,
                        "turn_counter": session.turn_counter,
                        "environment": lf_tracing_env,
                        **trace_classification,
                        "session_loop_status": "runtime_engine_initialized",
                        "opening_turn_committed": isinstance(opening_turn, dict),
                        "runtime_world": runtime_world_summary,
                    },
                    level="DEFAULT",
                    status_message="runtime_engine_initialized",
                )
        return {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "current_scene_id": session.current_scene_id,
            "content_provenance": session.content_provenance,
            "opening_turn": opening_turn,
            "opening_generation_status": "ready_with_opening" if isinstance(opening_turn, dict) else "pending",
            "session_loop": session_loop,
            "runtime_config_status": manager.runtime_config_status(),
            "warnings": [
                "world_engine_authoritative_story_runtime",
                "session_loop_runtime_engine_initialized",
            ],
        }
    except LiveStoryGovernanceError as exc:
        if root_span:
            root_span.update(output={"error": str(exc)}, metadata={"error": "governance_error"})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except StorySessionContractError as exc:
        if root_span:
            root_span.update(output={"error": str(exc)}, metadata={"error": "session_contract_error"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        if root_span:
            root_span.update(output={"error": str(exc)}, metadata={"error": "unknown_error"})
        raise
    finally:
        if root_span:
            try:
                root_span.end()
            except Exception:
                logger.warning("Langfuse root span end failed during session create", exc_info=True)
        if adapter and adapter.is_enabled():
            _flush_langfuse_background(adapter, context="session-create")
            try:
                adapter.set_active_span(previous_active_span)
            except Exception:
                logger.warning("Langfuse active span restore failed during session create", exc_info=True)


@router.post("/story/sessions/{session_id}/opening", dependencies=[Depends(_require_internal_api_key)])
def generate_story_session_opening(
    session_id: str,
    request: Request,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    trace_id = getattr(request.state, "trace_id", None)
    try:
        turn = manager.execute_opening(
            session_id=session_id,
            trace_id=trace_id if isinstance(trace_id, str) else None,
        )
        return {
            "session_id": session_id,
            "turn": turn,
            "opening_generation_status": "ready_with_opening",
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
