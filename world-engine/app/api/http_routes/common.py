from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any, Generator
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from ai_stack.telemetry.diagnostics_envelope import envelope_dict_to_response
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
from story_runtime_core.langfuse_tracing_environment import resolve_langfuse_environment

router = APIRouter(prefix="/api", tags=["api"])

def _flush_langfuse_background(adapter: Any, *, context: str) -> None:
    """Optionally flush Langfuse without making HTTP responses depend on it.

    Request handlers must not force Langfuse/OTLP export. The SDK keeps its own
    queue, and forced flushes can block on network timeouts after a successful
    runtime result was already built. Operators can opt into request-time flushes
    for local evidence runs with ``WOS_LANGFUSE_REQUEST_FLUSH=1``.
    """
    if not adapter or not getattr(adapter, "is_enabled", lambda: False)():
        return
    if (os.getenv("WOS_LANGFUSE_REQUEST_FLUSH") or "").strip().lower() not in {"1", "true", "yes", "on"}:
        return

    def _run() -> None:
        try:
            adapter.flush()
        except Exception:
            logger.warning("Langfuse background flush failed during %s", context, exc_info=True)

    try:
        threading.Thread(
            target=_run,
            name=f"langfuse-flush-{context}",
            daemon=True,
        ).start()
    except Exception:
        logger.warning("Could not schedule Langfuse background flush during %s", context, exc_info=True)

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


def _trace_classification_from_request(
    request: Request,
    *,
    runtime_projection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    projection = runtime_projection if isinstance(runtime_projection, dict) else {}
    header_origin = str(request.headers.get("X-WoS-Trace-Origin") or "").strip()
    header_tier = str(request.headers.get("X-WoS-Execution-Tier") or "").strip()
    header_canonical = str(request.headers.get("X-WoS-Canonical-Player-Flow") or "").strip().lower()
    header_test_case = str(request.headers.get("X-WoS-Test-Case-Id") or "").strip() or None
    header_runtime_mode = str(request.headers.get("X-WoS-Runtime-Mode") or "").strip()
    header_generation_mode = str(request.headers.get("X-WoS-Generation-Mode") or "").strip()

    if header_origin:
        trace_origin = header_origin
    elif os.environ.get("PYTEST_CURRENT_TEST"):
        trace_origin = "pytest"
    else:
        trace_origin = "unknown"

    if header_tier:
        execution_tier = header_tier
    elif trace_origin == "pytest":
        current = str(os.environ.get("PYTEST_CURRENT_TEST") or "").lower()
        execution_tier = "integration_test" if "integration" in current else "contract_test"
    else:
        execution_tier = "diagnostic"

    canonical = (
        header_canonical in {"1", "true", "yes"}
        if header_canonical
        else trace_origin == "live_ui"
    )
    runtime_mode = header_runtime_mode or str(projection.get("runtime_mode") or "solo_story")

    return {
        "trace_origin": trace_origin,
        "execution_tier": execution_tier,
        "canonical_player_flow": bool(canonical),
        "test_case_id": header_test_case,
        "runtime_mode": runtime_mode,
        "generation_mode": header_generation_mode or None,
    }


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



def _configured_internal_api_key() -> str | None:
    import sys

    facade = sys.modules.get("app.api.http")
    if facade is not None and hasattr(facade, "PLAY_SERVICE_INTERNAL_API_KEY"):
        return getattr(facade, "PLAY_SERVICE_INTERNAL_API_KEY")
    return PLAY_SERVICE_INTERNAL_API_KEY


def _require_internal_api_key(x_play_service_key: str | None = Header(default=None)) -> None:
    """Require valid internal API key for protected endpoints.

    Behavior:
    - If PLAY_SERVICE_INTERNAL_API_KEY is configured: key must match exactly (fail-fast)
    - If PLAY_SERVICE_INTERNAL_API_KEY is not configured: only explicit test mode is lenient
    - Empty/blank key values always rejected when configured

    Raises:
        HTTPException: 401 Unauthorized if key missing, invalid, or blank
    """
    expected = (_configured_internal_api_key() or "").strip()

    if expected:
        # API key is configured - enforce it
        provided = (x_play_service_key or "").strip()
        if not provided or provided != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid internal API key"
            )
        return

    test_mode = os.getenv("FLASK_ENV") in {"test", "testing"} or os.getenv("ENV") in {"test", "testing"}
    if test_mode:
        return

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="PLAY_SERVICE_INTERNAL_API_KEY is not configured",
    )


__all__ = [name for name in globals() if not name.startswith("__")]
