"""Main supervisor orchestration loop (extracted from SupervisorOrchestrator.orchestrate)."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.runtime.ai_adapter import AdapterRequest, StoryAIAdapter
from app.runtime.orchestration_cache import OrchestrationTurnCache
from app.runtime.supervisor_execution_types import SupervisorExecutionResult
from app.runtime.supervisor_orchestrate_execute_sections import (
    SupervisorOrchestrateWorkingState,
    orchestrate_merge_finalize_and_package,
    orchestrate_run_non_finalizer_agents,
)


def execute_supervisor_orchestration(
    orchestrator: Any,
    *,
    base_request: AdapterRequest,
    adapter: StoryAIAdapter,
    session: Any,
    module: Any,
    current_turn: int,
    recent_events: list[dict[str, Any]] | None,
    tool_registry: dict[str, Any] | None = None,
) -> SupervisorExecutionResult:
    policy = orchestrator.registry.supervisor_policy
    plan = orchestrator.plan_agents(operator_input=base_request.operator_input)
    state = SupervisorOrchestrateWorkingState()
    turn_cache = OrchestrationTurnCache(max_entries=24)
    started = perf_counter()
    orchestrate_run_non_finalizer_agents(
        orchestrator,
        plan=plan,
        policy=policy,
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=module,
        current_turn=current_turn,
        recent_events=recent_events,
        tool_registry=tool_registry,
        turn_cache=turn_cache,
        started=started,
        state=state,
    )
    return orchestrate_merge_finalize_and_package(
        orchestrator,
        plan=plan,
        policy=policy,
        base_request=base_request,
        adapter=adapter,
        turn_cache=turn_cache,
        started=started,
        state=state,
    )
