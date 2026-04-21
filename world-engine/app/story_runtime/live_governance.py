"""Live story-runtime governance: fail-closed semantics without silent default-registry fallback."""

from __future__ import annotations

from typing import Any

from story_runtime_core import ModelRegistry

from app.config import allow_ungoverned_story_runtime
from app.story_runtime.governed_runtime import build_governed_story_runtime_components


PREVIEW_STAGING_PLACEHOLDER = "(Preview staging — no committed world-state change.)"


class LiveStoryGovernanceError(RuntimeError):
    """Raised when a live player story operation is blocked by runtime governance policy."""


def is_governed_resolved_config_operational(resolved: dict[str, Any] | None) -> bool:
    """True when resolved backend config builds governed registry, routing, and adapters."""
    if not isinstance(resolved, dict):
        return False
    if not str(resolved.get("config_version") or "").strip():
        return False
    return build_governed_story_runtime_components(resolved) is not None


class BlockedLiveStoryRoutingPolicy:
    """Placeholder routing when governed config is missing; ``choose`` always fails for live graph execution."""

    registry: ModelRegistry

    def __init__(self) -> None:
        self.registry = ModelRegistry()

    def choose(self, *, task_type: str):
        raise LiveStoryGovernanceError(
            "LIVE_STORY_RUNTIME_BLOCKED: governed runtime configuration is missing, invalid, or could not be "
            "applied. Ensure Administration Center has rebuilt resolved runtime config, set "
            "BACKEND_RUNTIME_CONFIG_URL and INTERNAL_RUNTIME_CONFIG_TOKEN on the play service, then call "
            "POST /api/internal/story/runtime/reload-config (or restart the play service after the backend is up)."
        )


def opening_text_contains_preview_placeholder(text: str) -> bool:
    return PREVIEW_STAGING_PLACEHOLDER in (text or "")
