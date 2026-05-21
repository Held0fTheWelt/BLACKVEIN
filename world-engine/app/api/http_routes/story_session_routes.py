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


@router.post("/story/sessions/{session_id}/turns", dependencies=[Depends(_require_internal_api_key)])
def execute_story_turn(
    session_id: str,
    payload: ExecuteStoryTurnRequest,
    request: Request,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    player_line = str(payload.player_input).strip()
    player_input_sha256 = hashlib.sha256(player_line.encode("utf-8")).hexdigest()
    player_input_length = len(player_line)
    # Extract trace_id from Backend (via X-WoS-Trace-Id header)
    trace_id = getattr(request.state, "trace_id", None)
    langfuse_trace_id = getattr(request.state, "langfuse_trace_id", None)
    adapter = None
    root_span = None
    previous_active_span = None
    trace_classification = _trace_classification_from_request(request)

    try:
        from app.observability.langfuse_adapter import LangfuseAdapter
        adapter = LangfuseAdapter.get_instance()
        if hasattr(adapter, "refresh_backend_config"):
            adapter.refresh_backend_config(force=True)
        previous_active_span = adapter.get_active_span()
        adapter.set_active_span(None)
        logger.info(f"[HTTP] Adapter loaded: is_ready={adapter.is_ready}, is_enabled={adapter.is_enabled()}")
    except Exception as e:
        logger.error(f"[HTTP] ERROR: Failed to load Langfuse adapter: {type(e).__name__}: {e}", exc_info=True)
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
            logger.info(f"[HTTP] Received Langfuse trace_id from Backend: {langfuse_trace_id}")
            try:
                root_span = adapter.start_span_in_trace(
                    trace_id=langfuse_trace_id,
                    name="world-engine.turn.execute",
                    input={
                        "session_id": session_id,
                        "player_input_length": player_input_length,
                        "player_input_sha256": player_input_sha256,
                    },
                    metadata={
                        "stage": "world_engine_turn_execution",
                        "session_id": session_id,
                        "player_input_length": player_input_length,
                        "player_input_sha256": player_input_sha256,
                        "environment": lf_tracing_env,
                        **trace_classification,
                    },
                )
                logger.info(f"[HTTP] Created world-engine span in Langfuse trace {langfuse_trace_id}")
                adapter.set_active_span(root_span)
            except Exception as e:
                logger.error(f"[HTTP] Failed to create span under existing Langfuse trace: {e}", exc_info=True)
                root_span = None
        else:
            # No trace_id from Backend: create new root span (direct world-engine call)
            logger.info(f"[HTTP] No Langfuse trace_id from Backend - creating new root span")
            root_span = adapter.start_trace(
                name="world-engine.turn.execute",
                session_id=session_id,
                input={
                    "session_id": session_id,
                    "player_input_length": player_input_length,
                    "player_input_sha256": player_input_sha256,
                },
                metadata={
                    "turn_number": 0,  # Will be updated after execution
                    "player_input_length": player_input_length,
                    "player_input_sha256": player_input_sha256,
                    "session_id": session_id,
                    "environment": lf_tracing_env,
                    **trace_classification,
                }
            )
            if root_span:
                logger.info(f"[HTTP] Root span created, setting as active context")
                adapter.set_active_span(root_span)
                # Use Langfuse trace_id as the authoritative trace_id
                if hasattr(root_span, "trace_id"):
                    trace_id = root_span.trace_id
                    logger.info(f"[HTTP] Langfuse trace_id: {trace_id}")
            else:
                logger.warning(f"[HTTP] Failed to create root span for session {session_id}")

    try:
        session_scope = (
            adapter.session_scope(
                root_span=root_span,
                session_id=session_id,
                metadata={"stage": "world_engine_turn_execution"},
                trace_name="world-engine.turn.execute",
            )
            if root_span and adapter and hasattr(adapter, "session_scope")
            else nullcontext()
        )
        with session_scope:
            turn = manager.execute_turn(
                session_id=session_id,
                player_input=player_line,
                trace_id=trace_id if isinstance(trace_id, str) else None,
            )
            try:
                w5_trace_metadata = manager.get_w5_langfuse_metadata(session_id)
            except Exception:
                w5_trace_metadata = {}

            # Update root span with turn results
            if root_span and turn:
                turn_number = turn.get("turn_number", 0)
                turn_ok = bool(turn.get("ok", True))
                cost_summary = (
                    turn.get("diagnostics_envelope", {}).get("cost_summary")
                    if isinstance(turn.get("diagnostics_envelope"), dict)
                    else None
                )
                path_summary = (
                    turn.get("observability_path_summary")
                    if isinstance(turn.get("observability_path_summary"), dict)
                    else None
                )
                level, status_message = _langfuse_root_status(path_summary)
                logger.info(f"[HTTP] Updating root span with turn_number={turn_number}")
                raw_player_input = str(turn.get("raw_input") or player_line or "").strip()
                p0_evidence = None
                if isinstance(path_summary, dict):
                    p0_evidence = path_summary.get("p0_action_resolution_evidence")
                root_span.update(
                    output={
                        "turn_number": turn_number,
                        "session_id": session_id,
                        "success": turn_ok,
                        "turn_status": turn.get("turn_status"),
                        "turn_reason": turn.get("reason"),
                        "path_summary": path_summary,
                        "raw_player_input": raw_player_input,
                        "player_input_length": player_input_length,
                        "player_input_sha256": player_input_sha256,
                    },
                    metadata={
                        "turn_number": turn_number,
                        "environment": lf_tracing_env,
                        **trace_classification,
                        "cost_summary": cost_summary,
                        "path_quality": path_summary.get("quality_class") if path_summary else None,
                        "path_degradation": path_summary.get("degradation_summary") if path_summary else None,
                        "path_selected_model": path_summary.get("selected_model") if path_summary else None,
                        "path_adapter": path_summary.get("adapter") if path_summary else None,
                        "path_fallback_used": path_summary.get("generation_fallback_used") if path_summary else None,
                        "player_input_length": player_input_length,
                        "player_input_sha256": player_input_sha256,
                        "p0_action_resolution_evidence": p0_evidence,
                        **w5_trace_metadata,
                    },
                    level=level,
                    status_message=status_message,
                )
                logger.info(f"[HTTP] Root span updated")
            if adapter and adapter.is_enabled() and hasattr(adapter, "backfill_trace_metadata_after_commit"):
                turn_trace_ref = (
                    getattr(root_span, "trace_id", None)
                    or langfuse_trace_id
                )
                backfill_diag = adapter.backfill_trace_metadata_after_commit(
                    trace_id=turn_trace_ref,
                    canonical_turn_id=turn.get("canonical_turn_id") if isinstance(turn, dict) else None,
                    story_session_id=session_id,
                    turn_number=turn_number,
                    environment=lf_tracing_env,
                )
                logger.info("[HTTP] Langfuse trace metadata backfill (turn): %s", backfill_diag)

        return {"session_id": session_id, "turn": turn}

    except KeyError as exc:
        if root_span:
            root_span.update(output={"error": str(exc)}, metadata={"error": "session_not_found"})
        raise HTTPException(status_code=404, detail="Story session not found") from exc

    except LiveStoryGovernanceError as exc:
        if root_span:
            root_span.update(output={"error": str(exc)}, metadata={"error": "governance_error"})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    except RuntimeError as exc:
        msg = str(exc)
        if root_span:
            root_span.update(output={"error": msg}, metadata={"error": "runtime_error"})
        if msg.startswith("Hard narrative boundary:"):
            detail = msg.split(":", 1)[1].strip() or "hard_boundary_failure"
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail) from exc
        raise

    except Exception as exc:
        if root_span:
            root_span.update(output={"error": str(exc)}, metadata={"error": "unknown_error"})
        raise

    finally:
        # End root span and flush Langfuse
        if root_span:
            logger.info(f"[HTTP] Ending root span")
            try:
                root_span.end()
                logger.info(f"[HTTP] Root span ended")
            except Exception:
                logger.warning("[HTTP] Langfuse root span end failed during story turn", exc_info=True)
        if adapter and adapter.is_enabled():
            logger.info(f"[HTTP] Scheduling Langfuse adapter flush")
            _flush_langfuse_background(adapter, context="story-turn")
            try:
                adapter.set_active_span(previous_active_span)
            except Exception:
                logger.warning("[HTTP] Langfuse active span restore failed during story turn", exc_info=True)
        else:
            logger.info(f"[HTTP] Adapter not enabled or not initialized, skipping flush")
