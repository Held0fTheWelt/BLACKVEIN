"""Orchestrate runtime aspect validation from context to result payload."""

from __future__ import annotations

from .contracts import RuntimeAspectValidationHooks
from .dependencies import *
from .apply_outcome_failures import _apply_authority_failure, _apply_outcome_failures
from .apply_specific_failures import (
    _apply_capability_failure, _apply_generic_failure,
    _apply_npc_agency_failure, _apply_voice_failure,
)
from .capability_plan import _capture_capability_selection
from .capture_runtime_aspects import _capture_runtime_validations
from .context import _initial_context
from .failure_records import _collect_failure_records
from .result import _result
from .validation_aspect import _capture_validation_aspect

def build_runtime_aspect_validation(
    *,
    state: Any,
    generation: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
    outcome: dict[str, Any],
    hooks: RuntimeAspectValidationHooks,
) -> dict[str, Any]:
    """Evaluate runtime authority/capability aspects as validation inputs."""
    ctx = _initial_context(
        state=state,
        generation=generation,
        proposed_state_effects=proposed_state_effects,
        outcome=outcome,
        hooks=hooks,
    )
    _capture_runtime_validations(ctx)
    _capture_capability_selection(ctx)
    _collect_failure_records(ctx)
    _apply_outcome_failures(ctx)
    _capture_validation_aspect(ctx)
    return _result(ctx)
