from __future__ import annotations

from .common import *
from .models import *

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
    from ai_stack.prompt_store import configure_prompt_bundle

    cfg = fetch_resolved_runtime_config(
        base_url=BACKEND_RUNTIME_CONFIG_URL,
        token=INTERNAL_RUNTIME_CONFIG_TOKEN,
        timeout_seconds=RUNTIME_CONFIG_FETCH_TIMEOUT_SECONDS,
    )
    configure_prompt_bundle((cfg or {}).get("prompt_store"))
    request.app.state.resolved_runtime_config = cfg
    status = manager.reload_runtime_config(cfg)
    governed_ok = bool(status.get("governed_runtime_active")) and not bool(status.get("live_execution_blocked"))
    return {
        "ok": governed_ok,
        "runtime_config_status": status,
        "reload_notes": None if governed_ok else "Governed components could not be built from fetched config; live story execution remains blocked.",
    }
