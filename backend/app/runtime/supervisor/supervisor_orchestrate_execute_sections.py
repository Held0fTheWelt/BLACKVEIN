"""Helfer für execute_supervisor_orchestration — DS-014."""

from __future__ import annotations

from typing import Any

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.cache.orchestration_cache import OrchestrationTurnCache
from app.runtime.supervisor.supervisor_execution_types import SupervisorExecutionResult
from app.runtime.supervisor.supervisor_orchestrate_non_finalizer_loop_phases import (
    orchestrate_non_finalizer_single_agent_step,
)
from app.runtime.supervisor.supervisor_orchestrate_working_state import SupervisorOrchestrateWorkingState


def orchestrate_run_non_finalizer_agents(
    orchestrator: Any,
    *,
    plan: Any,
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
) -> None:
    """Plant und führt alle Agenten bis finalizer aus (ohne Merge/Finalizer)."""
    for agent_id in plan.execution_order:
        if agent_id == "finalizer":
            continue
        if orchestrate_non_finalizer_single_agent_step(
            orchestrator,
            agent_id=agent_id,
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
        ):
            break


def orchestrate_merge_finalize_and_package(
    orchestrator: Any,
    *,
    plan: Any,
    policy: Any,
    base_request: AdapterRequest,
    adapter: StoryAIAdapter,
    turn_cache: OrchestrationTurnCache,
    started: float,
    state: SupervisorOrchestrateWorkingState,
) -> SupervisorExecutionResult:
    """Merge, Finalizer (inkl. Fallback), Budget-Summary und Ergebnisobjekt."""
    from app.runtime.supervisor.supervisor_orchestrate_merge_finalize_sections import (
        package_supervisor_execution_result,
        supervisor_merge_finalize_response_and_budget,
    )

    final_response, budget_summary, merge_record = supervisor_merge_finalize_response_and_budget(
        orchestrator,
        plan=plan,
        policy=policy,
        base_request=base_request,
        adapter=adapter,
        turn_cache=turn_cache,
        started=started,
        state=state,
    )
    return package_supervisor_execution_result(
        final_response=final_response,
        plan=plan,
        state=state,
        merge_record=merge_record,
        budget_summary=budget_summary,
        turn_cache=turn_cache,
    )
