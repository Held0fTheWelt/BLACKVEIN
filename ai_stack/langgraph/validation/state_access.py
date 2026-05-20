"""Small accessors for validation state and captured results."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *

def _state_dict(ctx: _RuntimeAspectBuild, key: str) -> dict[str, Any] | None:
    value = ctx.state.get(key)
    return value if isinstance(value, dict) else None
def _state_dict_or_empty(ctx: _RuntimeAspectBuild, key: str) -> dict[str, Any]:
    return _state_dict(ctx, key) or {}
def _record_validation(
    ctx: _RuntimeAspectBuild,
    key: str,
    aspect_id: str,
    validation: Any,
    aspect_record: dict[str, Any],
    *,
    outcome_key: str | None = None,
) -> None:
    ctx.validations[key] = validation
    ctx.ledger = set_aspect_record(ctx.ledger, aspect_id, aspect_record)
    ctx.outcome = {**ctx.outcome, outcome_key or f"{key}_validation": validation}
