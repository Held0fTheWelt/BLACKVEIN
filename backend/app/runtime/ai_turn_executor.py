"""Transitional: AI-backed turn execution inside the backend ``SessionState`` loop.

Bridges adapters into ``execute_turn`` for **in-process** flows only — not a second
live runtime alongside the World Engine.

Core functions:
1. build_adapter_request / decision_from_parsed / process_role_structured_decision — Re-exported from ``ai_turn_adapter_bridge`` (stable import path: this module).
2. Decision-log test seams — Re-exported from ``ai_turn_decision_helpers`` / ``ai_turn_recovery_paths``.
3. Recovery helpers — Delegated to ai_turn_recovery_paths
4. execute_turn_with_ai — Integration entry: delegiert an ``ai_turn_execute_integration``.
"""

from __future__ import annotations

from typing import Any

from app.content.module_models import ContentModule
from app.runtime.ai_adapter import StoryAIAdapter
from app.runtime.ai_turn_decision_helpers import (
    convert_proposed_delta_to_state_delta as _convert_proposed_delta_to_state_delta,
    create_decision_log as _create_decision_log,
)
from app.runtime.ai_turn_adapter_bridge import (
    build_adapter_request,
    decision_from_parsed,
    process_role_structured_decision,
)
from app.runtime.ai_turn_execute_integration import run_execute_turn_with_ai_integration
from app.runtime.ai_turn_recovery_paths import (
    _create_error_decision_log,
    _make_parse_failure_result,
)
from app.runtime.turn_executor import TurnExecutionResult
from app.runtime.runtime_models import SessionState

# Set only after successful parse in post-parse pipeline (reserved; log bundle reads this slot).
_PREVIEW_DIAGNOSTICS_BEFORE_PARSE: dict[str, Any] | None = None


async def execute_turn_with_ai(
    session: SessionState,
    current_turn: int,
    adapter: StoryAIAdapter,
    module: ContentModule,
    *,
    operator_input: str = "",
    recent_events: list[dict[str, Any]] | None = None,
) -> TurnExecutionResult:
    """Execute a turn with AI-generated decision.

    Full integration pipeline:
    1. Build adapter request from session/module
    2. Call adapter.generate()
    3. Parse adapter response
    4. If parse fails, return system_error result with unchanged state
    5. Bridge parsed decision to MockDecision
    6. Delegate to execute_turn for validation/execution

    Args:
        session: Current session state
        current_turn: Current turn number
        adapter: StoryAIAdapter implementation
        module: Loaded content module
        operator_input: Optional operator context (empty string → None)
        recent_events: Optional list of recent events

    Returns:
        TurnExecutionResult with execution status, deltas, state, and events
    """
    return await run_execute_turn_with_ai_integration(
        session,
        current_turn,
        adapter,
        module,
        operator_input=operator_input,
        recent_events=recent_events,
        preview_diagnostics_before_parse=_PREVIEW_DIAGNOSTICS_BEFORE_PARSE,
    )
