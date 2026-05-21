"""Feature-flag readers for the session loop."""

from __future__ import annotations

import os

from .constants import (
    PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED,
    PHASE2_WS_SESSION_LOOP_ENABLED,
    _TRUE_VALUES,
)


def is_ws_session_loop_enabled() -> bool:
    """Return True when the Phase-2 WS session loop is enabled server-side.

    Fail-closed: any unset / unparseable value is treated as disabled.
    """
    raw = os.environ.get(PHASE2_WS_SESSION_LOOP_ENABLED, "false")
    return str(raw or "").strip().lower() in _TRUE_VALUES


def is_follow_up_semantic_composition_enabled() -> bool:
    """Return True iff Stage M semantic NPC follow-up composition is enabled.

    Fail-closed: when the env var is unset/unparseable the dispatcher stays on
    the deterministic template path. A provider is *additionally* required —
    enabling this flag alone does not trigger semantic generation.
    """
    raw = os.environ.get(PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED, "false")
    return str(raw or "").strip().lower() in _TRUE_VALUES
