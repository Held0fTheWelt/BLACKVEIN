"""Outcome status checks shared by failure application modules."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild


def _outcome_is_approved(ctx: _RuntimeAspectBuild) -> bool:
    return str(ctx.outcome.get("status") or "").strip().lower() == "approved"
