from __future__ import annotations

import hashlib
import json
import logging
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any, Generator
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_stack.diagnostics_envelope import envelope_dict_to_response
from app.config import PLAY_SERVICE_INTERNAL_API_KEY
from app.repo_root import resolve_wos_repo_root
from app.narrative.corrective_retry import apply_corrective_retry
from app.narrative.fallback_generator import build_safe_fallback_output
from app.narrative.output_validator import validate_runtime_output
from app.narrative.package_loader import NarrativePackageLoader
from app.narrative.preview_isolation import PreviewIsolationRegistry
from app.narrative.runtime_health import RuntimeHealthCounters
from app.narrative.runtime_output_models import RuntimeTurnStructuredOutputV2
from app.narrative.validation_feedback import ValidationFeedback
from app.narrative.validator_strategies import OutputValidatorConfig
from app.runtime.manager import RuntimeManager
from app.story_runtime import StoryRuntimeManager
from app.story_runtime.live_governance import LiveStoryGovernanceError
from app.story_runtime.manager import StorySessionContractError

router = APIRouter(prefix="/api", tags=["api"])


class IdentityPayload(BaseModel):
    account_id: str | None = None
    character_id: str | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    player_name: str | None = Field(default=None, min_length=1, max_length=80)

    def resolved_display_name(self) -> str:
        return (self.display_name or self.player_name or "Guest").strip()


class CreateRunRequest(IdentityPayload):
    template_id: str | None = None
    runtime_profile_id: str | None = None
    selected_player_role: str | None = None


class TicketRequest(IdentityPayload):
    run_id: str
    preferred_role_id: str | None = None


class JoinContextRequest(TicketRequest):
    pass


def get_manager(request: Request) -> RuntimeManager:
    return request.app.state.manager


def get_story_manager(request: Request) -> StoryRuntimeManager:
    return request.app.state.story_manager


def _langfuse_root_status(path_summary: dict[str, Any] | None) -> tuple[str, str]:
    if not path_summary:
        return "DEFAULT", "path_summary=missing"
    has_error = bool(path_summary.get("generation_error") or path_summary.get("parser_error"))
    fallback_used = bool(path_summary.get("generation_fallback_used"))
    degraded = path_summary.get("quality_class") == "degraded"
    level = "ERROR" if has_error else "WARNING" if fallback_used or degraded else "DEFAULT"
    status_message = (
        f"route={path_summary.get('route_model_called')} invoke={path_summary.get('invoke_model_called')} "
        f"fallback_used={fallback_used} model={path_summary.get('selected_model') or 'unknown'} "
        f"adapter={path_summary.get('adapter') or 'unknown'} quality={path_summary.get('quality_class') or 'unknown'} "
        f"degradation={path_summary.get('degradation_summary') or 'none'}"
    )
    return level, status_message


def _get_narrative_loader(request: Request) -> NarrativePackageLoader:
    loader = getattr(request.app.state, "narrative_package_loader", None)
    if loader is None:
        repo_root = resolve_wos_repo_root(start=Path(__file__).resolve().parent)
        loader = NarrativePackageLoader(repo_root=repo_root)
        request.app.state.narrative_package_loader = loader
    return loader


def _get_preview_registry(request: Request) -> PreviewIsolationRegistry:
    registry = getattr(request.app.state, "preview_isolation_registry", None)
    if registry is None:
        registry = PreviewIsolationRegistry()
        request.app.state.preview_isolation_registry = registry
    return registry


def _get_runtime_health(request: Request) -> RuntimeHealthCounters:
    counters = getattr(request.app.state, "narrative_runtime_health", None)
    if counters is None:
        counters = RuntimeHealthCounters()
        request.app.state.narrative_runtime_health = counters
    return counters


def _get_validator_config(request: Request) -> OutputValidatorConfig:
    config = getattr(request.app.state, "narrative_validator_config", None)
    if config is None:
        from app.narrative.validator_strategies import ValidationStrategy

        config = OutputValidatorConfig(
            strategy=ValidationStrategy.SCHEMA_PLUS_SEMANTIC,
            semantic_policy_check=True,
            enable_corrective_feedback=True,
            max_retry_attempts=1,
            fast_feedback_mode=True,
        )
        request.app.state.narrative_validator_config = config
    return config



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


class TerminateRunRequest(BaseModel):
    """Audit fields for internal terminate; both optional (empty strings default)."""

    actor_display_name: str = ""
    reason: str = ""


class CreateStorySessionRequest(BaseModel):
    module_id: str
    runtime_projection: dict[str, Any]
    session_output_language: str = "de"
    content_provenance: dict[str, Any] | None = None


class ExecuteStoryTurnRequest(BaseModel):
    player_input: str = Field(min_length=1)


class NarrativeReloadRequest(BaseModel):
    module_id: str
    expected_active_version: str


class NarrativePreviewLoadRequest(BaseModel):
    module_id: str
    preview_id: str
    isolation_mode: str = "session_namespace"


class NarrativePreviewUnloadRequest(BaseModel):
    module_id: str
    preview_id: str


class NarrativePreviewSessionStartRequest(BaseModel):
    module_id: str
    preview_id: str
    isolation_mode: str = "session_namespace"
    session_seed: str


class NarrativePreviewSessionEndRequest(BaseModel):
    preview_session_id: str


class NarrativeTurnValidationRequest(BaseModel):
    packet: dict[str, Any]
    output: dict[str, Any]


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


@router.get("/internal/story/runtime/config-status", dependencies=[Depends(_require_internal_api_key)])
def story_runtime_config_status(manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    """Machine-readable governed-runtime posture for readiness probes (no config fetch)."""
    return {"ok": True, "runtime_config_status": manager.runtime_config_status()}


@router.post("/internal/story/runtime/reload-config", dependencies=[Depends(_require_internal_api_key)])
def reload_story_runtime_governed_config(
    request: Request,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    """Re-fetch governed runtime config from the backend and rebuild story-runtime routing/graph."""
    from app.config import (
        BACKEND_RUNTIME_CONFIG_URL,
        INTERNAL_RUNTIME_CONFIG_TOKEN,
        RUNTIME_CONFIG_FETCH_TIMEOUT_SECONDS,
    )
    from app.runtime.runtime_config_client import fetch_resolved_runtime_config

    cfg = fetch_resolved_runtime_config(
        base_url=BACKEND_RUNTIME_CONFIG_URL,
        token=INTERNAL_RUNTIME_CONFIG_TOKEN,
        timeout_seconds=RUNTIME_CONFIG_FETCH_TIMEOUT_SECONDS,
    )
    request.app.state.resolved_runtime_config = cfg
    status = manager.reload_runtime_config(cfg)
    governed_ok = bool(status.get("governed_runtime_active")) and not bool(status.get("live_execution_blocked"))
    return {
        "ok": governed_ok,
        "runtime_config_status": status,
        "reload_notes": None if governed_ok else "Governed components could not be built from fetched config; live story execution remains blocked.",
    }


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
        try:
            from app.observability.langfuse_adapter import LangfuseAdapter
            adapter = LangfuseAdapter.get_instance()
            previous_active_span = adapter.get_active_span()
            adapter.set_active_span(None)
            logger.info(f"[HTTP] Adapter loaded for session create: is_ready={adapter.is_ready}, is_enabled={adapter.is_enabled()}")
        except Exception as exc:
            logger.error(f"[HTTP] ERROR: Failed to load Langfuse adapter for session create: {type(exc).__name__}: {exc}", exc_info=True)
            adapter = None

        if adapter and adapter.is_ready and adapter.is_enabled():
            if langfuse_trace_id:
                root_span = adapter.start_span_in_trace(
                    trace_id=langfuse_trace_id,
                    name="world-engine.session.create",
                    input={"module_id": payload.module_id, "session_id": story_session_id},
                    metadata={
                        "stage": "world_engine_session_create",
                        "turn_kind": "opening",
                        "session_id": story_session_id,
                    },
                )
            else:
                root_span = adapter.start_trace(
                    name="world-engine.session.create",
                    session_id=story_session_id,
                    input={"module_id": payload.module_id, "session_id": story_session_id},
                    metadata={
                        "module_id": payload.module_id,
                        "turn_kind": "opening",
                        "session_id": story_session_id,
                        "environment": adapter.config.environment,
                    },
                )
            if root_span:
                adapter.set_active_span(root_span)

        session_scope = (
            adapter.session_scope(
                root_span=root_span,
                session_id=story_session_id,
                metadata={"module_id": payload.module_id, "turn_kind": "opening"},
                trace_name="world-engine.session.create",
            )
            if root_span and adapter and hasattr(adapter, "session_scope")
            else nullcontext()
        )
        with session_scope:
            session = manager.create_session(
                module_id=payload.module_id,
                runtime_projection=payload.runtime_projection,
                session_output_language=payload.session_output_language,
                content_provenance=payload.content_provenance,
                trace_id=trace_id if isinstance(trace_id, str) else None,
                session_id=story_session_id,
            )
            opening_turn = session.diagnostics[-1] if session.diagnostics else None
            if root_span:
                cost_summary = (
                    opening_turn.get("diagnostics_envelope", {}).get("cost_summary")
                    if isinstance(opening_turn, dict) and isinstance(opening_turn.get("diagnostics_envelope"), dict)
                    else None
                )
                path_summary = (
                    opening_turn.get("observability_path_summary")
                    if isinstance(opening_turn, dict) and isinstance(opening_turn.get("observability_path_summary"), dict)
                    else None
                )
                level, status_message = _langfuse_root_status(path_summary)
                root_span.update(
                    output={
                        "session_id": session.session_id,
                        "turn_counter": session.turn_counter,
                        "success": True,
                        "path_summary": path_summary,
                    },
                    metadata={
                        "session_id": session.session_id,
                        "turn_counter": session.turn_counter,
                        "environment": adapter.config.environment if adapter else "unknown",
                        "cost_summary": cost_summary,
                        "path_quality": path_summary.get("quality_class") if path_summary else None,
                        "path_degradation": path_summary.get("degradation_summary") if path_summary else None,
                        "path_selected_model": path_summary.get("selected_model") if path_summary else None,
                        "path_adapter": path_summary.get("adapter") if path_summary else None,
                        "path_fallback_used": path_summary.get("generation_fallback_used") if path_summary else None,
                    },
                    level=level,
                    status_message=status_message,
                )
        return {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "current_scene_id": session.current_scene_id,
            "content_provenance": session.content_provenance,
            "opening_turn": opening_turn,
            "runtime_config_status": manager.runtime_config_status(),
            "warnings": ["world_engine_authoritative_story_runtime", "session_includes_committed_turn_0_opening"],
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
            root_span.end()
        if adapter and adapter.is_enabled():
            adapter.flush()
            adapter.set_active_span(previous_active_span)


@router.post("/story/sessions/{session_id}/turns", dependencies=[Depends(_require_internal_api_key)])
def execute_story_turn(
    session_id: str,
    payload: ExecuteStoryTurnRequest,
    request: Request,
    manager: StoryRuntimeManager = Depends(get_story_manager),
) -> dict[str, Any]:
    print(f">>> execute_story_turn CALLED for session {session_id}", flush=True)
    player_line = str(payload.player_input).strip()
    player_input_sha256 = hashlib.sha256(player_line.encode("utf-8")).hexdigest()
    player_input_length = len(player_line)
    # Extract trace_id from Backend (via X-WoS-Trace-Id header)
    trace_id = getattr(request.state, "trace_id", None)
    langfuse_trace_id = getattr(request.state, "langfuse_trace_id", None)
    adapter = None
    root_span = None
    previous_active_span = None

    try:
        from app.observability.langfuse_adapter import LangfuseAdapter
        adapter = LangfuseAdapter.get_instance()
        previous_active_span = adapter.get_active_span()
        adapter.set_active_span(None)
        logger.info(f"[HTTP] Adapter loaded: is_ready={adapter.is_ready}, is_enabled={adapter.is_enabled()}")
    except Exception as e:
        logger.error(f"[HTTP] ERROR: Failed to load Langfuse adapter: {type(e).__name__}: {e}", exc_info=True)
        adapter = None

    if adapter and adapter.is_ready and adapter.is_enabled():
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
                    "environment": adapter.config.environment,
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

            # Update root span with turn results
            if root_span and turn:
                turn_number = turn.get("turn_number", 0)
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
                root_span.update(
                    output={
                        "turn_number": turn_number,
                        "session_id": session_id,
                        "success": True,
                        "path_summary": path_summary,
                        "player_input_length": player_input_length,
                        "player_input_sha256": player_input_sha256,
                    },
                    metadata={
                        "turn_number": turn_number,
                        "environment": adapter.config.environment if adapter else "unknown",
                        "cost_summary": cost_summary,
                        "path_quality": path_summary.get("quality_class") if path_summary else None,
                        "path_degradation": path_summary.get("degradation_summary") if path_summary else None,
                        "path_selected_model": path_summary.get("selected_model") if path_summary else None,
                        "path_adapter": path_summary.get("adapter") if path_summary else None,
                        "path_fallback_used": path_summary.get("generation_fallback_used") if path_summary else None,
                        "player_input_length": player_input_length,
                        "player_input_sha256": player_input_sha256,
                    },
                    level=level,
                    status_message=status_message,
                )
                logger.info(f"[HTTP] Root span updated")

        return {"session_id": session_id, "turn": turn}

    except KeyError as exc:
        if root_span:
            root_span.update(output={"error": str(exc)}, metadata={"error": "session_not_found"})
        raise HTTPException(status_code=404, detail="Story session not found") from exc

    except LiveStoryGovernanceError as exc:
        if root_span:
            root_span.update(output={"error": str(exc)}, metadata={"error": "governance_error"})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    except Exception as exc:
        if root_span:
            root_span.update(output={"error": str(exc)}, metadata={"error": "unknown_error"})
        raise

    finally:
        # End root span and flush Langfuse
        if root_span:
            logger.info(f"[HTTP] Ending root span")
            root_span.end()
            logger.info(f"[HTTP] Root span ended")
        if adapter and adapter.is_enabled():
            logger.info(f"[HTTP] Flushing Langfuse adapter")
            adapter.flush()
            adapter.set_active_span(previous_active_span)
            logger.info(f"[HTTP] Langfuse flush complete")
        else:
            logger.info(f"[HTTP] Adapter not enabled or not initialized, skipping flush")


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


@router.get("/story/sessions/{session_id}/diagnostics-envelope", dependencies=[Depends(_require_internal_api_key)])
def get_story_diagnostics_envelope(session_id: str, manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    """Return the last DiagnosticsEnvelope (MVP4) for a story session."""
    try:
        envelope = manager.get_last_diagnostics_envelope(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Story session not found") from exc
    if envelope is None:
        return {"session_id": session_id, "diagnostics_envelope": None, "warning": "no_turns_yet"}
    envelope_dict = envelope_dict_to_response(envelope, context="operator")
    return {"session_id": session_id, "diagnostics_envelope": envelope_dict}


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


@router.get("/story/runtime/narrative-gov-summary", dependencies=[Depends(_require_internal_api_key)])
def get_narrative_gov_summary(manager: StoryRuntimeManager = Depends(get_story_manager)) -> dict[str, Any]:
    """Return NarrativeGovSummary (MVP4) — operator health evidence for Narrative Gov."""
    return manager.get_narrative_gov_summary()


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


@router.get("/internal/narrative/runtime/state", dependencies=[Depends(_require_internal_api_key)])
def narrative_runtime_state(module_id: str, request: Request) -> dict[str, Any]:
    loader = _get_narrative_loader(request)
    state = loader.state(module_id)
    return {"ok": True, "data": state}


@router.get("/internal/narrative/runtime/validator-config", dependencies=[Depends(_require_internal_api_key)])
def narrative_runtime_validator_config(request: Request) -> dict[str, Any]:
    config = _get_validator_config(request)
    return {"ok": True, "data": config.model_dump(mode="json")}


@router.get("/internal/narrative/runtime/health", dependencies=[Depends(_require_internal_api_key)])
def narrative_runtime_health(request: Request) -> dict[str, Any]:
    counters = _get_runtime_health(request)
    return {"ok": True, "data": counters.summary()}


@router.post("/internal/narrative/runtime/validate-and-recover", dependencies=[Depends(_require_internal_api_key)])
def narrative_runtime_validate_and_recover(payload: NarrativeTurnValidationRequest, request: Request) -> dict[str, Any]:
    """Operator-introspection validator endpoint.

    Exposes the deterministic narrative validator
    (``validate_runtime_output``) and its corrective-retry helper for
    packet / output pairs supplied directly by an operator. This is **not**
    the live player-turn validator lane — live turns validate through
    ``run_validation_seam`` inside ``RuntimeTurnGraphExecutor``, which
    records ``validator_lane="goc_rule_engine_v1"`` on each committed turn's
    ``runtime_governance_surface``. Callers of this endpoint should treat the
    ``validator_lane`` field in the response as evidence that the
    operator-introspection lane ran, distinct from the canonical live lane.
    """
    config = _get_validator_config(request)
    counters = _get_runtime_health(request)
    from app.narrative.package_models import NarrativeDirectorScenePacket, SceneFallbackBundle

    packet = NarrativeDirectorScenePacket.model_validate(payload.packet)
    output = RuntimeTurnStructuredOutputV2.model_validate(payload.output)
    feedback = validate_runtime_output(packet=packet, output=output, config=config)
    validator_lane = "operator_introspection_validate_and_recover"
    if feedback.passed:
        counters.record_first_pass_success(packet.module_id, packet.scene_id)
        return {
            "ok": True,
            "data": {
                "mode": "first_pass",
                "validator_lane": validator_lane,
                "output": output.model_dump(mode="json"),
            },
        }
    if config.enable_corrective_feedback and config.max_retry_attempts > 0:
        retried = apply_corrective_retry(original_output=output, feedback=feedback)
        retry_feedback: ValidationFeedback = validate_runtime_output(packet=packet, output=retried, config=config)
        if retry_feedback.passed:
            counters.record_corrective_retry(packet.module_id, packet.scene_id)
            return {
                "ok": True,
                "data": {
                    "mode": "corrective_retry",
                    "validator_lane": validator_lane,
                    "validation_feedback": feedback.model_dump(mode="json"),
                    "output": retried.model_dump(mode="json"),
                },
            }
    fallback = build_safe_fallback_output(
        fallback_bundle=SceneFallbackBundle(),
        reason="validation_failed_after_retry",
    )
    counters.record_safe_fallback(packet.module_id, packet.scene_id)
    return {
        "ok": True,
        "data": {
            "mode": "safe_fallback",
            "validator_lane": validator_lane,
            "validation_feedback": feedback.model_dump(mode="json"),
            "output": fallback.model_dump(mode="json"),
        },
    }
