"""Shared runtime status semantics for operator-facing surfaces."""

from __future__ import annotations

STATUS_SEMANTICS = {
    "healthy": "Runtime behavior is within expected governed posture.",
    "degraded": "Runtime is available but with reduced quality, fallback behavior, or elevated error signals.",
    "blocked": "Runtime path cannot satisfy its primary purpose until blockers are resolved.",
    "configured_disabled": "Behavior is intentionally disabled by governed configuration.",
    "unknown": "Insufficient runtime signal was available for a trustworthy classification.",
}

