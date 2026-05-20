"""Einzelschritte für Non-Finalizer-Agenten in der Supervisor-Orchestrierung (DS-014)."""

from __future__ import annotations

from typing import Any

from app.runtime.ai_adapter import AdapterRequest, StoryAIAdapter
from app.runtime.cache.orchestration_cache import OrchestrationTurnCache
from app.runtime.supervisor.supervisor_orchestrate_non_finalizer_budget_and_invoke import (
    non_finalizer_invoke_and_accumulate_counters,
    non_finalizer_resolve_budget_gate,
    non_finalizer_should_break_after_invocation,
)
from app.runtime.supervisor.supervisor_orchestrate_working_state import SupervisorOrchestrateWorkingState


def orchestrate_non_finalizer_single_agent_step(
    orchestrator: Any,
    *,
    agent_id: str,
    policy: Any,
    base_request: AdapterRequest,
    adapter: StoryAIAdapter,
    session: Any,
    module: Any,
    current_turn: int,
    recent_events: list[dict[str, Any]] | None,
    tool_registry: dict[str, Any] | None,
    turn_cache: OrchestrationTurnCache,
    started: float,
    state: SupervisorOrchestrateWorkingState,
) -> bool:
    """Führt einen Nicht-Finalizer-Agenten aus. Rückgabe **True** = äußere Schleife abbrechen."""
    agent = orchestrator.registry.require_enabled(agent_id)
    sequence_index = len(state.invocations) + 1
    gate = non_finalizer_resolve_budget_gate(
        orchestrator,
        agent=agent,
        policy=policy,
        base_request=base_request,
        sequence_index=sequence_index,
        started=started,
        state=state,
    )
    if gate == "break_loop":
        return True
    if gate == "skip_iteration":
        return False

    invocation, result, parsed = non_finalizer_invoke_and_accumulate_counters(
        orchestrator,
        agent=agent,
        sequence_index=sequence_index,
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=module,
        current_turn=current_turn,
        recent_events=recent_events,
        tool_registry=tool_registry,
        turn_cache=turn_cache,
        policy=policy,
        state=state,
    )
    return non_finalizer_should_break_after_invocation(
        agent=agent,
        policy=policy,
        invocation=invocation,
        state=state,
    )
